"""Load layer: persist sources, indicators, dataset versions, and observations
with full lineage and idempotency (docs/03 §4, docs/05 §3-4).

Idempotency contract:
  * A DatasetVersion is unique on (datasource_id, checksum). Re-ingesting an
    identical payload finds the existing version and loads NOTHING.
  * Observations are immutable: a changed upstream payload yields a NEW
    DatasetVersion (new checksum) and NEW observation rows; old rows are kept.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .ingest.base import (
    Connector,
    DataSourceSpec,
    IndicatorSpec,
    ObservationRecord,
    RawPayload,
)
from .transform.quality import run_quality_checks


@dataclass
class IngestResult:
    source: str
    checksum: str
    source_version: str
    created_version: bool
    records_parsed: int
    observations_loaded: int
    issues: list[str]

    @property
    def no_op(self) -> bool:
        return not self.created_version


def _upsert_datasource(cur, s: DataSourceSpec) -> int:
    cur.execute("SELECT id FROM datasource WHERE name = %s", (s.name,))
    row = cur.fetchone()
    if row:
        cur.execute(
            """UPDATE datasource
                  SET publisher=%s, url=%s, access_method=%s, licence=%s,
                      update_frequency=%s, notes=%s
                WHERE id=%s""",
            (s.publisher, s.url, s.access_method, s.licence,
             s.update_frequency, s.notes, row[0]),
        )
        return int(row[0])
    cur.execute(
        """INSERT INTO datasource
               (name, publisher, url, access_method, licence, update_frequency, notes)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (s.name, s.publisher, s.url, s.access_method, s.licence,
         s.update_frequency, s.notes),
    )
    return int(cur.fetchone()[0])


def _upsert_indicator(cur, i: IndicatorSpec) -> int:
    cur.execute(
        """INSERT INTO indicator
               (code, domain, name, definition, formula, unit, direction,
                normalization, coverage)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (code) DO UPDATE SET
               domain=EXCLUDED.domain, name=EXCLUDED.name,
               definition=EXCLUDED.definition, formula=EXCLUDED.formula,
               unit=EXCLUDED.unit, direction=EXCLUDED.direction,
               normalization=EXCLUDED.normalization, coverage=EXCLUDED.coverage
           RETURNING id""",
        (i.code, i.domain, i.name, i.definition, i.formula, i.unit, i.direction,
         json.dumps(i.normalization) if i.normalization is not None else None,
         json.dumps(i.coverage) if i.coverage is not None else None),
    )
    return int(cur.fetchone()[0])


def _link_indicator_source(cur, indicator_id: int, datasource_id: int) -> None:
    cur.execute(
        """INSERT INTO indicator_source (indicator_id, datasource_id)
           VALUES (%s,%s) ON CONFLICT DO NOTHING""",
        (indicator_id, datasource_id),
    )


def _find_or_create_dataset_version(
    cur, datasource_id: int, payload: RawPayload, row_count: int
) -> tuple[int, bool]:
    """Return (dataset_version_id, created)."""
    cur.execute(
        """INSERT INTO dataset_version
               (datasource_id, source_version, checksum, row_count)
           VALUES (%s,%s,%s,%s)
           ON CONFLICT (datasource_id, checksum) DO NOTHING
           RETURNING id""",
        (datasource_id, payload.source_version, payload.checksum, row_count),
    )
    row = cur.fetchone()
    if row:
        return int(row[0]), True
    cur.execute(
        "SELECT id FROM dataset_version WHERE datasource_id=%s AND checksum=%s",
        (datasource_id, payload.checksum),
    )
    return int(cur.fetchone()[0]), False


def _jurisdiction_ids(cur) -> dict[str, int]:
    cur.execute("SELECT code, id FROM jurisdiction WHERE code IS NOT NULL")
    return {code: jid for code, jid in cur.fetchall()}


def _insert_observations(
    cur,
    dataset_version_id: int,
    records: list[ObservationRecord],
    indicator_ids: dict[str, int],
) -> tuple[int, list[str]]:
    jur = _jurisdiction_ids(cur)
    loaded = 0
    issues: list[str] = []
    for r in records:
        jid = jur.get(r.jurisdiction_code)
        if jid is None:
            issues.append(f"unknown jurisdiction '{r.jurisdiction_code}' — quarantined")
            continue
        cur.execute(
            """INSERT INTO observation
                   (indicator_id, jurisdiction_id, dataset_version_id,
                    period, value, quality_flag)
               VALUES (%s,%s,%s, daterange(%s::date, %s::date, '[]'), %s, %s)""",
            (indicator_ids[r.indicator_code], jid, dataset_version_id,
             r.period_start, r.period_end, r.value, r.quality_flag),
        )
        loaded += 1
    return loaded, issues


def ingest(conn, connector: Connector, *, live: bool = False) -> IngestResult:
    """Run one connector end-to-end: extract -> validate -> load (idempotent).

    A connector with no live path (e.g. CIHI, a manual portal download) falls
    back to its vendored fixture even when live=True. A connector whose live
    fetch fails transiently (e.g. a StatCan 5xx/timeout, after retries) also
    degrades to its vendored fixture, so a `--live` run still loads every source
    with last-known-good data instead of failing the whole pipeline.
    """
    fallback_issue: str | None = None
    try:
        payload = connector.extract(live=live)
    except NotImplementedError:
        payload = connector.extract(live=False)
    except OSError as e:  # URLError/HTTPError/timeout all subclass OSError
        payload = connector.extract(live=False)
        fallback_issue = f"live fetch failed ({e}); fell back to vendored fixture"
    records = connector.parse(payload)
    kept, issues = run_quality_checks(connector.indicators, records)
    if fallback_issue:
        issues.insert(0, fallback_issue)

    with conn.cursor() as cur:
        ds_id = _upsert_datasource(cur, connector.source)
        ind_ids = {ind.code: _upsert_indicator(cur, ind) for ind in connector.indicators}
        for iid in ind_ids.values():
            _link_indicator_source(cur, iid, ds_id)

        dv_id, created = _find_or_create_dataset_version(cur, ds_id, payload, len(records))

        loaded = 0
        if created:
            loaded, load_issues = _insert_observations(cur, dv_id, kept, ind_ids)
            issues += load_issues
        conn.commit()

    return IngestResult(
        source=connector.name,
        checksum=payload.checksum,
        source_version=payload.source_version,
        created_version=created,
        records_parsed=len(records),
        observations_loaded=loaded,
        issues=issues,
    )
