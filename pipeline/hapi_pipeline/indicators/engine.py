"""HAPI scoring engine (docs/06 §3).

For each jurisdiction × period: normalize each indicator to 0-100 (per-capita
where configured), align by direction, weight-average within a domain to a domain
score, then weight-average across domains to the composite. Every HapiScore stores
method_version + the inputs (codes, raw values, normalized values, weights) so the
score is fully auditable (docs/03 §2.8).
"""
from __future__ import annotations

import json

from . import hapi_v1


def _latest_observations(cur, codes: list[str]) -> dict[tuple[str, str, int], float | None]:
    """Map (indicator_code, jurisdiction_code, year) -> latest value (None if suppressed)."""
    cur.execute(
        """
        SELECT i.code, j.code, extract(year FROM lower(o.period))::int AS yr, o.value
          FROM observation o
          JOIN indicator i    ON i.id = o.indicator_id
          JOIN jurisdiction j ON j.id = o.jurisdiction_id
          JOIN (
              SELECT indicator_id, jurisdiction_id, period, max(dataset_version_id) AS mdv
                FROM observation GROUP BY indicator_id, jurisdiction_id, period
          ) latest
            ON latest.indicator_id = o.indicator_id
           AND latest.jurisdiction_id = o.jurisdiction_id
           AND latest.period = o.period
           AND latest.mdv = o.dataset_version_id
         WHERE i.code = ANY(%s)
        """,
        (codes,),
    )
    out: dict[tuple[str, str, int], float | None] = {}
    for code, jcode, yr, value in cur.fetchall():
        out[(code, jcode, int(yr))] = None if value is None else float(value)
    return out


def _normalize(value: float, norm: dict, direction: str) -> float:
    lo, hi = norm["min"], norm["max"]
    pct = 0.0 if hi == lo else (value - lo) / (hi - lo) * 100.0
    pct = max(0.0, min(100.0, pct))
    return pct if direction == "higher_is_better" else 100.0 - pct


def compute_hapi(conn, method_version: str = hapi_v1.METHOD_VERSION) -> int:
    """Compute and upsert HapiScores for every jurisdiction × year with data."""
    codes = [ind["code"] for ind in hapi_v1.INDICATORS]
    denoms = [ind["per_capita"]["denominator"] for ind in hapi_v1.INDICATORS if ind.get("per_capita")]

    with conn.cursor() as cur:
        obs = _latest_observations(cur, codes + denoms)
        cur.execute("SELECT code, id FROM jurisdiction WHERE code IS NOT NULL")
        jur_ids = {c: i for c, i in cur.fetchall()}

        # discover the (jurisdiction, year) cells that have any numerator value
        cells = sorted({(j, y) for (c, j, y), v in obs.items() if c in codes and v is not None})

        written = 0
        for jcode, year in cells:
            domain_inputs: dict[str, list[dict]] = {}
            for ind in hapi_v1.INDICATORS:
                raw = obs.get((ind["code"], jcode, year))
                if raw is None:
                    continue
                value = raw
                denom_val = None
                if ind.get("per_capita"):
                    denom_val = obs.get((ind["per_capita"]["denominator"], jcode, year))
                    if not denom_val:
                        continue  # need the denominator to score a per-capita indicator
                    value = raw / denom_val * ind["per_capita"]["scale"]
                normalized = _normalize(value, ind["normalization"], ind["direction"])
                domain_inputs.setdefault(ind["domain"], []).append(
                    {
                        "code": ind["code"],
                        "raw": raw,
                        "denominator": denom_val,
                        "value": round(value, 3),
                        "normalized": round(normalized, 2),
                        "weight": ind["weight"],
                    }
                )

            if not domain_inputs:
                continue

            jid = jur_ids[jcode]
            period = f"{year}-01-01"
            domain_scores: dict[str, float] = {}

            # domain scores
            for domain, items in domain_inputs.items():
                wsum = sum(i["weight"] for i in items)
                score = sum(i["normalized"] * i["weight"] for i in items) / wsum
                domain_scores[domain] = score
                _upsert_score(cur, jid, domain, period, score, method_version,
                              {"indicators": items})

            # composite (overall) across available domains
            dw = {d: hapi_v1.DOMAIN_WEIGHTS.get(d, 1.0) for d in domain_scores}
            wsum = sum(dw.values())
            composite = sum(domain_scores[d] * dw[d] for d in domain_scores) / wsum
            _upsert_score(cur, jid, "overall", period, composite, method_version,
                          {"domain_scores": {d: round(s, 2) for d, s in domain_scores.items()},
                           "domain_weights": dw})
            written += len(domain_scores) + 1

        conn.commit()
        return written


def _upsert_score(cur, jid: int, domain: str, period: str, score: float,
                  method_version: str, inputs: dict) -> None:
    cur.execute(
        """INSERT INTO hapi_score (jurisdiction_id, domain, period, score, method_version, inputs)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (jurisdiction_id, domain, period, method_version)
           DO UPDATE SET score = EXCLUDED.score, inputs = EXCLUDED.inputs""",
        (jid, domain, period, round(score, 2), method_version, json.dumps(inputs)),
    )
