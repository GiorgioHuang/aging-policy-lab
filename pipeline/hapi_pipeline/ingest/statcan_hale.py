"""StatCan connector — health-adjusted life expectancy (HALE) at age 65, Health.

HALE at 65 = the average number of *healthy* years a person aged 65 can expect to
live (life expectancy adjusted for time spent in less-than-full health). It is the
canonical healthy-ageing outcome and the quality complement to the raw life
expectancy at 65 (`statcan_life_expectancy`, Table 13-10-0389).

Source confirmed 2026-06 via WebSearch + `hapi inspect statcan_hale` on a
networked runner:
  * Table 13-10-0971 (productId 13100971).
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310097101
  * Real columns: REF_DATE, GEO, 'Age group', 'Sex', 'Income group',
    'Characteristics', VALUE, STATUS. GEO includes Canada and Nova Scotia; years
    2019, 2020, 2023. Members: Age group ∈ {'At age 65', 'At birth'}; Sex ∈
    {'Both sexes', …}; Income group ∈ {'All income groups', quintile 1-5};
    Characteristics ∈ {'Health-adjusted life expectancy', 'Life expectancy',
    and their Low/High 95% CI variants}.
  * Filtered to GEO ∈ {Canada, Nova Scotia}, age 'At age 65', 'Both sexes',
    'All income groups', characteristic 'Health-adjusted life expectancy'
    (requires "adjusted" — excludes plain life expectancy and the CI bounds).

higher_is_better. A short (periodic) series — HALE is published every few years.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100971"
GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
MIN_YEAR = 2015
INDICATOR = "health.hale_65"

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("sex", "gender"),
    "income": ("income",),
    "characteristic": ("characteristic", "element", "indicator", "estimate"),
}


def _is_age_65(member: str) -> bool:
    """The 'at age 65' member (the only other age member is 'at birth')."""
    return "65" in member.lower()


def _is_all_income(member: str) -> bool:
    """Keep the all-income aggregate (not the quintile rows). Absent dim -> keep."""
    m = member.strip().lower()
    return m == "" or "all" in m or "total" in m


def _is_hale_estimate(member: str) -> bool:
    """The HALE estimate ('Health-adjusted life expectancy') itself — not its
    confidence-interval bounds, and not the plain 'Life expectancy' member that
    shares this table (which lacks 'adjusted')."""
    c = member.strip().lower()
    if c == "":
        return True
    if any(w in c for w in ("confidence", "interval", "lower", "upper", "low", "high", "margin")):
        return False
    return "adjusted" in c


class StatCanHALEConnector(Connector):
    name = "statcan_hale"
    fixture_name = "statcan_hale_65.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Health-adjusted life expectancy at birth and at age 65 (Table 13-10-0971)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310097101",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="periodic",
        notes="WDS getFullTableDownloadCSV(13100971); filtered to at age 65, both "
              "sexes, all income groups, HALE estimate (excluding CI bounds).",
    )

    indicators = [
        IndicatorSpec(
            code=INDICATOR,
            domain="health",
            name="Health-adjusted life expectancy at age 65",
            definition="Average number of additional years a person aged 65 can expect "
                       "to live in full health (both sexes, all income groups) — life "
                       "expectancy adjusted for time spent in less-than-full health.",
            formula="StatCan Table 13-10-0971: age='at age 65', both sexes, all income, "
                    "health-adjusted life expectancy estimate.",
            unit="years",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 10.0, "max": 20.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        )
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
        f_inc = sc.find_field(fields, "income")
        f_char = sc.find_field(fields, "characteristic", "element", "indicator", "estimate")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            geo = sc.col(row, "GEO")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if f_age and not _is_age_65(row.get(f_age, "")):
                continue
            if f_sex and not sc.is_total_gender(row.get(f_sex, "")):
                continue
            if f_inc and not _is_all_income(row.get(f_inc, "")):
                continue
            if f_char and not _is_hale_estimate(row.get(f_char, "")):
                continue
            writer.writerow([sc.col(row, "REF_DATE"), geo,
                             sc.col(row, "VALUE"), sc.col(row, "STATUS")])
        return out.getvalue()

    def inspect_live(self) -> str:
        return sc.inspect_dump(sc.fetch_full_table_csv(PRODUCT_ID), _DIM_HINTS)

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
        records: list[ObservationRecord] = []
        for row in reader:
            jcode = GEO_TO_JURISDICTION.get(sc.col(row, "GEO"))
            if jcode is None:
                continue
            year = sc.col(row, "REF_DATE")[:4]
            if not year or int(year) < MIN_YEAR:
                continue
            raw = sc.col(row, "VALUE").strip()
            status = sc.col(row, "STATUS").strip().upper()
            suppressed = raw == "" or status in ("F", "X", "..", "...")
            records.append(
                ObservationRecord(
                    indicator_code=INDICATOR,
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
