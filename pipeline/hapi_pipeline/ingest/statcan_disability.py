"""StatCan connector — disability rate at 65+ (Table 13-10-0374), Independence.

The share of seniors (65+) living with one or more disabilities that limit daily
activities — a direct measure of functional (in)dependence in later life. Source
is the Canadian Survey on Disability (CSD); Statistics Canada reported the senior
rate rising 38% (2017) → 40% (2022). lower_is_better.

Source confirmed 2026-06 via WebSearch + `hapi inspect statcan_disability`:
  * Table 13-10-0374 (productId 13100374).
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310037401
  * Real columns: REF_DATE, GEO, 'Age group', 'Gender', 'Disability',
    'Estimates', VALUE, STATUS. GEO includes Canada and Nova Scotia. Members:
    Age group has '65 years and over' (plus 65-74 / 75+ bands); Gender ∈ {'Total,
    gender', 'Men+', 'Women+'}; Disability ∈ {'Persons with disabilities',
    'Persons without disabilities', 'Total population, with and without
    disabilities'}; the statistic column is 'Estimates' (number vs percentage of
    persons, plus their 95% CI bounds).
  * The table reports COUNTS only (Estimates = 'Number of persons' + CI bounds),
    not a percentage — so the prevalence RATE is DERIVED: filter to GEO ∈
    {Canada, Nova Scotia}, age '65 years and over', 'Total, gender', the point
    'Number of persons' estimate, keeping both the 'Persons with disabilities'
    and 'Total population' counts, then rate = with ÷ total × 100 per (geo, year).
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
    "statistic": ("estimate", "statistic", "characteristic"),
}


def _status_tag(member: str) -> str | None:
    """Tag the Disability member as the with-disabilities count ('with') or the
    total-population denominator ('total'); ignore the 'without' member."""
    m = member.strip().lower()
    if "with disab" in m and "without" not in m:
        return "with"
    if "total population" in m or "with and without" in m:
        return "total"
    return None


def _is_count(estimate: str) -> bool:
    """The point 'Number of persons' estimate — not a confidence-interval bound.
    (Table 13-10-0374 reports counts only; the prevalence rate is derived as
    persons-with-disabilities ÷ total-population.)"""
    e = estimate.strip().lower()
    if any(w in e for w in ("confidence", "interval", "low", "high", "margin")):
        return False
    return e == "" or "number" in e


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
        f_est = sc.find_field(fields, "estimate", "statistic", "characteristic")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "STATUS_TAG", "VALUE"])
        for row in reader:
            if sc.map_geo(sc.col(row, "GEO")) is None:
                continue
            if f_age and not sc.is_age_65plus(row.get(f_age, "")):
                continue
            if f_sex and not sc.is_total_gender(row.get(f_sex, "")):
                continue
            tag = _status_tag(row.get(f_status, "")) if f_status else None
            if tag is None:
                continue
            if f_est and not _is_count(row.get(f_est, "")):
                continue
            writer.writerow([sc.col(row, "REF_DATE"), sc.col(row, "GEO"),
                             tag, sc.col(row, "VALUE")])
        return out.getvalue()

    def inspect_live(self) -> str:
        return sc.inspect_dump(sc.fetch_full_table_csv(PRODUCT_ID), _DIM_HINTS,
                               geo_name="Nova Scotia")

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
        # Accumulate the with-disabilities and total-population counts per
        # (jurisdiction, year), then derive the prevalence rate = with / total.
        counts: dict[tuple[str, str], dict[str, float]] = {}
        for row in reader:
            jcode = sc.map_geo(sc.col(row, "GEO"))
            if jcode is None:
                continue
            year = sc.col(row, "REF_DATE")[:4]
            if not year or int(year) < MIN_YEAR:
                continue
            raw = sc.col(row, "VALUE").strip()
            if raw == "":
                continue
            tag = (row.get("STATUS_TAG") or "").strip()
            if tag in ("with", "total"):
                counts.setdefault((jcode, year), {})[tag] = float(raw)

        records: list[ObservationRecord] = []
        for (jcode, year), c in counts.items():
            w, tot = c.get("with"), c.get("total")
            rate = round(w / tot * 100.0, 1) if (w is not None and tot) else None
            records.append(
                ObservationRecord(
                    indicator_code=INDICATOR,
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=rate,
                    quality_flag="ok" if rate is not None else "suppressed",
                )
            )
        return records
