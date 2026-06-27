"""StatCan connector — life expectancy at age 65 (Table 13-10-0389), Health.

Source confirmed 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 13-10-0389 "Life expectancy, at birth and at age 65, by sex,
    three-year average, Canada, provinces, territories, health regions and peer
    groups" (productId 13100389). https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310038901
  * Pulled as the WDS full-table CSV and filtered to GEO ∈ {Canada, Nova Scotia},
    the "at age 65" age member, both-sexes, and the life-expectancy characteristic
    (excluding its confidence-interval bounds). REF_DATE is a three-year average
    period; we key it by its leading year.

HAPI Health indicator for older adults: remaining life expectancy at age 65 —
a robust, widely-used summary of older-adult health outcomes. higher_is_better.

TO CONFIRM on first --live run via `hapi inspect statcan_life_expectancy`: the
exact age-group / sex / characteristic member labels (StatCan wording varies).
The filter matches case-insensitively by substring and is tolerant; tighten here
if inspection differs.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100389"
GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
MIN_YEAR = 2015

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("sex", "gender"),
    "characteristic": ("characteristic", "element", "indicator"),
}


def _is_age_65(member: str) -> bool:
    """The 'at age 65' member (the only other age member is 'at birth')."""
    return "65" in member.lower()


def _is_life_expectancy(member: str) -> bool:
    """The life-expectancy estimate itself, not its confidence-interval bounds."""
    c = member.strip().lower()
    if c == "":
        return True
    return "life expectancy" in c and not any(
        w in c for w in ("confidence", "interval", "low", "high", "margin")
    )


class StatCanLifeExpectancyConnector(Connector):
    name = "statcan_life_expectancy"
    fixture_name = "statcan_life_expectancy_65.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Life expectancy at birth and at age 65 (Table 13-10-0389)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310038901",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="annual",
        notes="WDS getFullTableDownloadCSV(13100389); filtered to at age 65, both "
              "sexes, life-expectancy estimate. Three-year-average periods.",
    )

    indicators = [
        IndicatorSpec(
            code="health.life_expectancy_65",
            domain="health",
            name="Life expectancy at age 65",
            definition="Average number of additional years a person aged 65 can expect "
                       "to live (both sexes, three-year average).",
            formula="StatCan Table 13-10-0389: age='at age 65', both sexes, life "
                    "expectancy.",
            unit="years",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 16.0, "max": 24.0},
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
        f_char = sc.find_field(fields, "characteristic", "element", "indicator")
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
            if f_char and not _is_life_expectancy(row.get(f_char, "")):
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
                    indicator_code="health.life_expectancy_65",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
