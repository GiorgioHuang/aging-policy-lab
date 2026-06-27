"""StatCan connector — CCHS health characteristics (Table 13-10-0096).

Populates two HAPI domains from one source, the Canadian Community Health Survey
annual estimates (by age group, province):
  * Independence         -> functional health, good to full functional health (%)
  * Social Participation  -> sense of belonging to local community, strong (%)

Source confirmed 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 13-10-0096 "Health characteristics, annual estimates" (productId
    13100096), Canada (excl. territories) + provinces, annual.
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310009601
  * Pulled as the WDS full-table CSV and filtered to GEO ∈ {Canada, Nova Scotia},
    age 65+, both sexes, the "percent" statistic, and the two health
    characteristics above.

Both indicators are higher_is_better (more functional autonomy / more social
connection = better). Reference ranges bracket the observed CA+NS span and can be
recalibrated as the data lands.

TO CONFIRM on first --live run via `hapi inspect statcan_cchs`: the exact age /
sex / statistic / health-characteristic member labels (CCHS wording varies by
vintage). Matching is tolerant (case-insensitive substring); tighten here if
inspection differs.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100096"
GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
MIN_YEAR = 2015

IND_FUNCTIONAL = "independence.functional_health_65plus"
IND_BELONGING = "social_participation.community_belonging_65plus"

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("sex", "gender"),
    "health_characteristic": ("health characteristic", "indicator"),
    "statistic": ("characteristic",),
}


def _classify(health_char: str) -> str | None:
    """Map a 'Health characteristics' member to one of our indicator codes."""
    h = health_char.strip().lower()
    if "functional health" in h:
        return IND_FUNCTIONAL
    if "belonging" in h and "strong" in h:
        return IND_BELONGING
    return None


def _is_percent(stat: str) -> bool:
    s = stat.strip().lower()
    return s == "" or "percent" in s


class StatCanCCHSConnector(Connector):
    name = "statcan_cchs"
    fixture_name = "statcan_cchs_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Health characteristics, annual estimates (Table 13-10-0096)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310009601",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="annual",
        notes="WDS getFullTableDownloadCSV(13100096), CCHS; filtered to 65+, both "
              "sexes, percent. Functional health -> Independence; community "
              "belonging -> Social Participation.",
    )

    indicators = [
        IndicatorSpec(
            code=IND_FUNCTIONAL,
            domain="independence",
            name="Functional health (good to full), population 65+",
            definition="Share of persons aged 65+ with good-to-full functional health "
                       "(Health Utilities Index), a measure of independent functioning.",
            formula="StatCan Table 13-10-0096: age 65+, both sexes, percent, health "
                    "characteristic='Functional health, good to full functional health'.",
            unit="% of persons 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 40.0, "max": 90.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        ),
        IndicatorSpec(
            code=IND_BELONGING,
            domain="social_participation",
            name="Sense of community belonging (strong), population 65+",
            definition="Share of persons aged 65+ reporting a somewhat or very strong "
                       "sense of belonging to their local community.",
            formula="StatCan Table 13-10-0096: age 65+, both sexes, percent, health "
                    "characteristic='Sense of belonging to local community, somewhat "
                    "strong or very strong'.",
            unit="% of persons 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 50.0, "max": 90.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        ),
    ]

    def fetch_live(self) -> RawPayload:
        kept = self._filter_csv(sc.fetch_full_table_csv(PRODUCT_ID))
        return RawPayload(content=kept.encode("utf-8"),
                          source_version=f"WDS:getFullTableDownloadCSV/{PRODUCT_ID}",
                          content_type="text/csv")

    @staticmethod
    def _filter_csv(text: str) -> str:
        reader = csv.DictReader(io.StringIO(text))
        fields = reader.fieldnames or []
        f_age = sc.find_field(fields, "age")
        f_sex = sc.find_field(fields, "sex", "gender")
        f_health = sc.find_field(fields, "health characteristic", "indicator")
        # The statistic dimension also matches "characteristic"; pick the one that
        # is NOT the health-characteristic column.
        f_stat = next((f for f in fields
                       if "characteristic" in f.lower() and f != f_health), "")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["INDICATOR", "REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            geo = sc.col(row, "GEO")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if f_age and not sc.is_age_65plus(row.get(f_age, "")):
                continue
            if f_sex and not sc.is_total_gender(row.get(f_sex, "")):
                continue
            if f_stat and not _is_percent(row.get(f_stat, "")):
                continue
            code = _classify(row.get(f_health, "")) if f_health else None
            if code is None:
                continue
            writer.writerow([code, sc.col(row, "REF_DATE"), geo,
                             sc.col(row, "VALUE"), sc.col(row, "STATUS")])
        return out.getvalue()

    def inspect_live(self) -> str:
        return sc.inspect_dump(sc.fetch_full_table_csv(PRODUCT_ID), _DIM_HINTS)

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
        records: list[ObservationRecord] = []
        for row in reader:
            code = (row.get("INDICATOR") or "").strip()
            jcode = GEO_TO_JURISDICTION.get(sc.col(row, "GEO"))
            if not code or jcode is None:
                continue
            year = sc.col(row, "REF_DATE")[:4]
            if not year or int(year) < MIN_YEAR:
                continue
            raw = sc.col(row, "VALUE").strip()
            status = sc.col(row, "STATUS").strip().upper()
            suppressed = raw == "" or status in ("F", "X", "..", "...")
            records.append(
                ObservationRecord(
                    indicator_code=code,
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
