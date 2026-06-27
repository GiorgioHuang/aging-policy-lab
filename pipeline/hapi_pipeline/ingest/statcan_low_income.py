"""StatCan connector — seniors' low-income rate (Table 11-10-0135), Financial Security.

Source confirmed 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 11-10-0135 "Low income statistics by age, gender and economic family
    type" (productId 11100135), Canada + provinces/territories, annual.
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110013501
  * Pulled as the WDS full-table CSV (see _statcan.fetch_full_table_csv) and
    filtered to: age = 65 years and over, total gender, low-income line =
    Low income measure after tax (LIM-AT), statistic = percentage of persons in
    low income (the *rate*), economic-family type = all persons.

This is the headline HAPI Financial Security indicator for older adults:
the share of seniors living below the LIM-AT line. Direction is lower_is_better
(a lower senior poverty rate scores higher).

TO CONFIRM on first --live run via `hapi inspect statcan_low_income`: the exact
member labels for the low-income-line / statistic / economic-family dimensions
(StatCan wording varies by vintage). The filter matches them case-insensitively
by substring and is intentionally tolerant; tighten here if inspection differs.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "11100135"
GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
MIN_YEAR = 2019

_DIM_HINTS = {
    "age": ("age",),
    "gender": ("gender", "sex"),
    "low_income_line": ("low income line", "low-income line", "low income lines"),
    "statistic": ("statistic",),
    "family": ("economic family", "persons in low"),
}


def _wanted(line: str, stat: str, fam: str) -> bool:
    """Keep LIM-AT × percentage-rate × all-persons rows (tolerant matching)."""
    ll, st, fm = line.lower(), stat.lower(), fam.lower()
    line_ok = ("low income measure" in ll and "after" in ll) or ll == "" or "lim" in ll
    stat_ok = ("percentage" in st and "low income" in st) or "rate" in st or st == ""
    fam_ok = ("all persons" in fm) or fm == ""
    return line_ok and stat_ok and fam_ok


class StatCanLowIncomeConnector(Connector):
    name = "statcan_low_income"
    fixture_name = "statcan_low_income_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Low income statistics by age (Table 11-10-0135)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110013501",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="annual",
        notes="WDS getFullTableDownloadCSV(11100135); filtered to 65+, total gender, "
              "LIM after tax, percentage of persons in low income, all persons.",
    )

    indicators = [
        IndicatorSpec(
            code="financial_security.low_income_rate_65plus",
            domain="financial_security",
            name="Low-income rate, population 65+ (LIM-AT)",
            definition="Share of persons aged 65+ living below the Low Income Measure, "
                       "after tax (LIM-AT).",
            formula="StatCan Table 11-10-0135: age='65 years and over', total gender, "
                    "LIM-AT, percentage of persons in low income.",
            unit="% of persons 65+",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 2.0, "max": 20.0},
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
        f_gender = sc.find_field(fields, "gender", "sex")
        f_line = sc.find_field(fields, "low income line", "low-income line", "low income lines")
        f_stat = sc.find_field(fields, "statistic")
        f_fam = sc.find_field(fields, "economic family", "persons in low")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            geo = sc.col(row, "GEO")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if f_age and not sc.is_age_65plus(row.get(f_age, "")):
                continue
            if f_gender and not sc.is_total_gender(row.get(f_gender, "")):
                continue
            if not _wanted(row.get(f_line, ""), row.get(f_stat, ""), row.get(f_fam, "")):
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
                    indicator_code="financial_security.low_income_rate_65plus",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
