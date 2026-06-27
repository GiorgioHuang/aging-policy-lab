"""StatCan connector — LTC / residential-care workforce (Table 14-10-0202), Care Access.

Source confirmed 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 14-10-0202 "Employment by industry, annual" (productId 14100202), from
    the Survey of Employment, Payrolls and Hours (SEPH), Canada + provinces, by
    NAICS. https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410020201
  * We keep NAICS **623 — Nursing and residential care facilities** (the
    institutional-care employer aggregate; sub-industries 6231 nursing care and
    6233 community care for the elderly roll up into it).

This is a **supply / capacity** view of Care Access: how many people work in
nursing- and residential-care facilities, per 1,000 seniors. Higher is better
(more care workers per senior). Covers CA + CA-NS, annual.

TO CONFIRM on first --live run via `hapi inspect statcan_ltc_employment`: the
exact NAICS member label for 623, and whether the cube carries a
"Type of employee" / "Estimate" dimension whose total member we must pin (SEPH
splits all-employees vs hourly). The `_filter_csv` matchers are intentionally
tolerant; tighten them here once inspection shows the real wording.
"""
from __future__ import annotations

import csv
import io
import re

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "14100202"
GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
MIN_YEAR = 2001

_DIM_HINTS = {
    "naics": ("north american industry", "naics", "industry"),
    "employee_type": ("type of employee", "employee"),
    "statistic": ("estimate", "statistic"),
}


def _naics_code(member: str) -> str:
    """Extract the bracketed NAICS code, e.g. 'Nursing and residential care … [623]' -> '623'."""
    m = re.search(r"\[(\d+)\]", member or "")
    return m.group(1) if m else ""


def _is_naics_623(member: str) -> bool:
    """Keep the 623 aggregate (not 6231/6233 sub-industries); tolerate a missing code."""
    code = _naics_code(member)
    if code:
        return code == "623"
    return "nursing and residential care" in (member or "").strip().lower()


def _is_all_employees(member: str) -> bool:
    """Pin the all-employees total when a 'Type of employee' dimension is present."""
    t = (member or "").strip().lower()
    return t == "" or t in {"all employees", "all employee", "total employees", "employees"}


class StatCanLTCEmploymentConnector(Connector):
    name = "statcan_ltc_employment"
    fixture_name = "statcan_ltc_employment.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Employment by industry, annual (Table 14-10-0202)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410020201",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="annual",
        notes="WDS getFullTableDownloadCSV(14100202) from the Survey of Employment, "
              "Payrolls and Hours (SEPH); filtered to NAICS 623 (nursing & residential "
              "care facilities), all employees, GEO in {Canada, Nova Scotia}.",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.ltc_workforce_per_1k_65plus",
            domain="care_access",
            name="Nursing & residential care workforce per 1,000 pop 65+",
            definition="Employees in nursing and residential care facilities (NAICS 623) "
                       "per 1,000 population aged 65+ — a Care Access supply measure.",
            formula="StatCan Table 14-10-0202, NAICS 623 all-employee count ÷ "
                    "demography.population_65plus × 1,000.",
            unit="workers per 1,000 pop 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 20.0, "max": 100.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR, "cadence": "annual"},
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
        f_naics = sc.find_field(fields, "north american industry", "naics", "industry")
        f_type = sc.find_field(fields, "type of employee")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            geo = sc.col(row, "GEO")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if f_naics and not _is_naics_623(row.get(f_naics, "")):
                continue
            if f_type and not _is_all_employees(row.get(f_type, "")):
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
                    indicator_code="care_access.ltc_workforce_per_1k_65plus",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
