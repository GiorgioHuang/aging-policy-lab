"""StatCan connector — CCHS health characteristics (Table 13-10-0096).

Feeds two HAPI domains from one already-live CCHS table:
  * Social Participation — sense of belonging to local community (strong)
  * Care Access          — has a regular healthcare provider (the API-accessible,
                           auto-refreshing Care-Access backbone; CIHI home-care
                           remains a manually-refreshed complement)

Source confirmed 2026-06 via WebSearch + `hapi inspect statcan_cchs` on a
networked runner:
  * Table 13-10-0096 "Health characteristics, annual estimates" (productId
    13100096), Canada (excluding territories) + provinces, annual (CCHS).
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310009601
  * Real dimensions: REF_DATE, GEO, 'Age group', 'Sex', 'Indicators',
    'Characteristics' (the statistic), …, VALUE, STATUS. The national GEO member
    is "Canada (excluding territories)". Both target members ('Sense of belonging
    to local community…' and 'Has a regular healthcare provider') are confirmed
    present in the 'Indicators' dimension.
  * Filtered to GEO ∈ {Canada(excl. terr.), Nova Scotia}, age 65+, both sexes,
    statistic "Percent". Both indicators are higher_is_better.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100096"
MIN_YEAR = 2015
IND_BELONGING = "social_participation.community_belonging_65plus"
IND_PROVIDER = "care_access.regular_provider_65plus"

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("sex", "gender"),
    "indicator": ("indicator", "health characteristic"),
    "statistic": ("characteristic",),
}


def _classify(indicator: str) -> str | None:
    """Map a 13-10-0096 'Indicators' member to one of our HAPI indicator codes."""
    h = indicator.strip().lower()
    if "belonging" in h and "community" in h and "strong" in h:
        return IND_BELONGING
    if "regular" in h and ("provider" in h or "health care" in h or "healthcare" in h):
        return IND_PROVIDER
    return None


def _is_percent(stat: str) -> bool:
    s = stat.strip().lower()
    return s == "percent" or s == ""


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
              "sexes, percent. Community belonging -> Social Participation; "
              "regular healthcare provider -> Care Access.",
    )

    indicators = [
        IndicatorSpec(
            code=IND_BELONGING,
            domain="social_participation",
            name="Sense of community belonging (strong), population 65+",
            definition="Share of persons aged 65+ reporting a somewhat or very strong "
                       "sense of belonging to their local community.",
            formula="StatCan Table 13-10-0096: age 65+, both sexes, percent, indicator="
                    "'Sense of belonging to local community, somewhat strong or very strong'.",
            unit="% of persons 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 50.0, "max": 90.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        ),
        IndicatorSpec(
            code=IND_PROVIDER,
            domain="care_access",
            name="Has a regular healthcare provider, population 65+",
            definition="Share of persons aged 65+ who report having a regular healthcare "
                       "provider — a core measure of primary-care access.",
            formula="StatCan Table 13-10-0096: age 65+, both sexes, percent, indicator="
                    "'Has a regular healthcare provider'.",
            unit="% of persons 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 80.0, "max": 100.0},
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
        f_ind = sc.find_field(fields, "indicator", "health characteristic")
        f_stat = next((f for f in fields
                       if "characteristic" in f.lower() and f != f_ind), "")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["INDICATOR", "REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            if sc.map_geo(sc.col(row, "GEO")) is None:
                continue
            if f_age and not sc.is_age_65plus(row.get(f_age, "")):
                continue
            if f_sex and not sc.is_total_gender(row.get(f_sex, "")):
                continue
            if f_stat and not _is_percent(row.get(f_stat, "")):
                continue
            code = _classify(row.get(f_ind, "")) if f_ind else None
            if code is None:
                continue
            writer.writerow([code, sc.col(row, "REF_DATE"), sc.col(row, "GEO"),
                             sc.col(row, "VALUE"), sc.col(row, "STATUS")])
        return out.getvalue()

    def inspect_live(self) -> str:
        return sc.inspect_dump(sc.fetch_full_table_csv(PRODUCT_ID), _DIM_HINTS,
                               geo_name="Nova Scotia")

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
        records: list[ObservationRecord] = []
        for row in reader:
            code = (row.get("INDICATOR") or "").strip()
            jcode = sc.map_geo(sc.col(row, "GEO"))
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
