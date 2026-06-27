"""StatCan connector — functional health (Table 13-10-0966), Independence.

Source confirmed 2026-06 (WebSearch; The Daily 2026-03-16 "Functional health of
Canadian adults, 2015 to 2024"):
  * Table 13-10-0966 "Functional health" (productId 13100966), CCHS cycles
    (2015, 2019, 2024…), Canada (excluding territories) + provinces, by age group.
  * Functional health (Health Utilities Index Mark 3, eight attributes: vision,
    hearing, speech, cognition, dexterity, mobility, emotion, pain). "Very good to
    perfect functional health" = HUI3 score 0.89–1.00.
  * Schema CONFIRMED 2026-06 via `hapi inspect`: dimensions REF_DATE, GEO,
    'Age group', 'Sex', 'Domains' (the functional-health category), 'Characteristics'
    (the statistic), …, VALUE, STATUS. National GEO is "Canada (excluding territories)".
  * The table has NO 65+ aggregate — age bands are "65 to 74 years" and "75 years
    and over". Both are ingested as companion Independence indicators (younger and
    older seniors); HAPI averages them within the domain. Filtered to GEO ∈
    {Canada(excl. terr.), Nova Scotia}, both senior bands, both sexes, statistic
    "Percentage", domain "Very good to perfect functional health".

HAPI Independence indicators: the share of seniors (65–74 and 75+, separately)
with very-good-to-perfect functional health — a summary of independent
functioning. higher_is_better.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100966"
MIN_YEAR = 2015
IND_65_74 = "independence.functional_health_65_74"
IND_75PLUS = "independence.functional_health_75plus"

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("sex", "gender"),
    "domain": ("domain", "functional"),
    "statistic": ("characteristic", "statistic"),
}


def _age_band(member: str) -> str | None:
    """Map an age member to one of our two senior-band indicator codes (the table
    has no 65+ aggregate — only '65 to 74 years' and '75 years and over')."""
    m = member.strip().lower()
    if "65" in m and "74" in m:
        return IND_65_74
    if "75" in m and ("over" in m or "older" in m):
        return IND_75PLUS
    return None


def _is_very_good(member: str) -> bool:
    """The 'Very good to perfect functional health' domain category."""
    m = member.strip().lower()
    if m == "":
        return True
    return "very good" in m and ("perfect" in m or "functional" in m)


def _is_percent(stat: str) -> bool:
    # Exact estimate only — NOT the "Low/High 95% confidence interval, percentage"
    # bounds (which also contain "percent").
    s = stat.strip().lower()
    return s in ("percent", "percentage") or s == ""


class StatCanFunctionalHealthConnector(Connector):
    name = "statcan_functional_health"
    fixture_name = "statcan_functional_health_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Functional health (Table 13-10-0966)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310096601",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="periodic",
        notes="WDS getFullTableDownloadCSV(13100966), CCHS (2015/2019/2024…); "
              "filtered to both senior bands (65–74, 75+), both sexes, percent, "
              "very good to perfect functional health (HUI Mark 3).",
    )

    indicators = [
        IndicatorSpec(
            code=IND_65_74,
            domain="independence",
            name="Functional health (very good to perfect), ages 65–74",
            definition="Share of persons aged 65–74 with very-good-to-perfect functional "
                       "health (Health Utilities Index Mark 3, 0.89–1.00).",
            formula="StatCan Table 13-10-0966: age '65 to 74 years', both sexes, "
                    "percentage, domain 'Very good to perfect functional health'.",
            unit="% of persons 65–74",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 20.0, "max": 65.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        ),
        IndicatorSpec(
            code=IND_75PLUS,
            domain="independence",
            name="Functional health (very good to perfect), ages 75+",
            definition="Share of persons aged 75 and over with very-good-to-perfect "
                       "functional health (Health Utilities Index Mark 3, 0.89–1.00).",
            formula="StatCan Table 13-10-0966: age '75 years and over', both sexes, "
                    "percentage, domain 'Very good to perfect functional health'.",
            unit="% of persons 75+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 15.0, "max": 55.0},
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
        # 'Domains' carries the functional-health category; 'Characteristics' is the
        # statistic (Number / Percentage / CI bounds).
        f_dom = sc.find_field(fields, "domain", "functional")
        f_stat = next((f for f in fields
                       if "characteristic" in f.lower() and f != f_dom), "")
        if not f_stat:
            f_stat = sc.find_field(fields, "statistic")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["INDICATOR", "REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            if sc.map_geo(sc.col(row, "GEO")) is None:
                continue
            code = _age_band(row.get(f_age, "")) if f_age else None
            if code is None:
                continue
            if f_sex and not sc.is_total_gender(row.get(f_sex, "")):
                continue
            if f_stat and not _is_percent(row.get(f_stat, "")):
                continue
            if f_dom and not _is_very_good(row.get(f_dom, "")):
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
