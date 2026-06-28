"""StatCan connector — disability rate at 65+ (Table 13-10-0374), Independence.

The share of seniors (65+) living with one or more disabilities that limit daily
activities — a direct measure of functional (in)dependence in later life. Source
is the Canadian Survey on Disability (CSD); Statistics Canada reported the senior
rate rising 38% (2017) → 40% (2022). lower_is_better.

Source (WebSearch 2026-06; direct gov fetch blocked in this sandbox — confirm on a
networked runner with `hapi inspect statcan_disability`):
  * Table 13-10-0374 "Persons with and without disabilities aged 15 years and
    over, by age group and gender, Canada, provinces and territories"
    (productId 13100374). https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310037401
  * Pulled as the WDS full-table CSV, filtered to GEO ∈ {Canada, Nova Scotia},
    the 65+ age member, both genders, the "with disabilities" status, and the
    percentage statistic (the prevalence rate, not the count).

Filters match case-insensitively by substring and are deliberately tolerant;
`hapi inspect statcan_disability` dumps the real dimension members — tighten the
status / statistic / age wording here if inspection differs, or repoint
PRODUCT_ID if a more complete table is available.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100374"
MIN_YEAR = 2015
INDICATOR = "independence.disability_rate_65plus"

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("gender", "sex"),
    "status": ("disabilit", "persons with"),
    "statistic": ("statistic", "characteristic"),
}


def _is_with_disability(member: str) -> bool:
    """The 'persons with disabilities' status — not 'without', not the total."""
    m = member.strip().lower()
    return "with disab" in m and "without" not in m


def _is_percent_stat(member: str) -> bool:
    """The prevalence rate (percentage/proportion), not the person count."""
    m = member.strip().lower()
    return m == "" or "percent" in m or "proportion" in m or "%" in m or "rate" in m


class StatCanDisabilityConnector(Connector):
    name = "statcan_disability"
    fixture_name = "statcan_disability_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Persons with and without disabilities, by age group (Table 13-10-0374)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310037401",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="periodic",
        notes="WDS getFullTableDownloadCSV(13100374), Canadian Survey on Disability; "
              "filtered to 65+, both genders, persons with disabilities, percentage.",
    )

    indicators = [
        IndicatorSpec(
            code=INDICATOR,
            domain="independence",
            name="Disability rate, population 65+",
            definition="Share of persons aged 65+ living with one or more disabilities "
                       "that limit daily activities (Canadian Survey on Disability). A "
                       "direct measure of functional independence in later life.",
            formula="StatCan Table 13-10-0374: age 65+, both genders, persons with "
                    "disabilities, percentage.",
            unit="% of persons 65+",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 25.0, "max": 50.0},
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
        f_sex = sc.find_field(fields, "gender", "sex")
        f_status = sc.find_field(fields, "disabilit", "persons with")
        f_stat = sc.find_field(fields, "statistic", "characteristic")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            if sc.map_geo(sc.col(row, "GEO")) is None:
                continue
            if f_age and not sc.is_age_65plus(row.get(f_age, "")):
                continue
            if f_sex and not sc.is_total_gender(row.get(f_sex, "")):
                continue
            if f_status and not _is_with_disability(row.get(f_status, "")):
                continue
            if f_stat and not _is_percent_stat(row.get(f_stat, "")):
                continue
            writer.writerow([sc.col(row, "REF_DATE"), sc.col(row, "GEO"),
                             sc.col(row, "VALUE"), sc.col(row, "STATUS")])
        return out.getvalue()

    def inspect_live(self) -> str:
        return sc.inspect_dump(sc.fetch_full_table_csv(PRODUCT_ID), _DIM_HINTS,
                               geo_name="Nova Scotia")

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
        records: list[ObservationRecord] = []
        for row in reader:
            jcode = sc.map_geo(sc.col(row, "GEO"))
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
