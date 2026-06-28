"""StatCan connector — seniors' low-income rate (Table 11-10-0135), Financial Security.

Source confirmed 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 11-10-0135 "Low income statistics by age, gender and economic family
    type" (productId 11100135), Canada + provinces/territories, annual.
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110013501

Schema CONFIRMED 2026-06 via `hapi inspect statcan_low_income` on a networked
runner. The cube has NO separate age/gender column; the age cut is folded into
the `Persons in low income` dimension. We filter to:
  * Persons in low income = "Persons 65 years and over" (the both-gender 65+
    aggregate; gendered / economic-family variants are excluded),
  * Low income lines     = "Low income measure after tax" (LIM-AT),
  * Statistics           = "Percentage of persons in low income" (the *rate*).

Two Financial Security indicators from this one table (INDICATOR-tagged):
  * `low_income_rate_65plus` — the share of seniors below the LIM-AT line
    (Statistics = "Percentage of persons in low income"); lower_is_better.
  * `low_income_gap_65plus` — the average gap ratio, i.e. how far below the line
    low-income seniors fall, as a % of the line — the *depth* of poverty
    (Statistics = "Average gap ratio"); lower_is_better.
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
    "persons": ("persons in low", "age"),
    "low_income_line": ("low income line", "low-income line", "low income lines"),
    "statistic": ("statistic",),
}


def _is_persons_65plus(member: str) -> bool:
    """The both-gender 65+ aggregate of the 'Persons in low income' dimension —
    not the gendered ('Men+/Women+ … 65 years and over') or economic-family rows."""
    p = member.strip().lower()
    return (
        p.startswith("persons")
        and "65 years and over" in p
        and "men" not in p
        and "women" not in p
        and "economic" not in p
    )


def _wanted_line(line: str) -> bool:
    ll = line.lower()
    return ("low income measure" in ll and "after" in ll) or "lim-at" in ll or ll == ""


IND_RATE = "financial_security.low_income_rate_65plus"
IND_GAP = "financial_security.low_income_gap_65plus"


def _classify_stat(stat: str) -> str | None:
    """Map the 'Statistics' member to one of our two Financial Security indicators."""
    st = stat.strip().lower()
    if "percentage" in st and "low income" in st:
        return IND_RATE
    if "gap ratio" in st:
        return IND_GAP
    return None


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
            code=IND_RATE,
            domain="financial_security",
            name="Low-income rate, population 65+ (LIM-AT)",
            definition="Share of persons aged 65+ living below the Low Income Measure, "
                       "after tax (LIM-AT).",
            formula="StatCan Table 11-10-0135: persons in low income='Persons 65 years "
                    "and over', LIM-AT, percentage of persons in low income.",
            unit="% of persons 65+",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 2.0, "max": 30.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        ),
        IndicatorSpec(
            code=IND_GAP,
            domain="financial_security",
            name="Low-income gap ratio, population 65+ (LIM-AT)",
            definition="Average gap ratio for low-income seniors — how far below the "
                       "LIM-AT line they fall, as a percentage of the line (the depth "
                       "of poverty, complementing the headcount rate).",
            formula="StatCan Table 11-10-0135: persons in low income='Persons 65 years "
                    "and over', LIM-AT, average gap ratio.",
            unit="% below the LIM-AT line",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 5.0, "max": 40.0},
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
        f_persons = sc.find_field(fields, "persons in low", "age")
        f_line = sc.find_field(fields, "low income line", "low-income line", "low income lines")
        f_stat = sc.find_field(fields, "statistic")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["INDICATOR", "REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            geo = sc.col(row, "GEO")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if f_persons and not _is_persons_65plus(row.get(f_persons, "")):
                continue
            if f_line and not _wanted_line(row.get(f_line, "")):
                continue
            code = _classify_stat(row.get(f_stat, "")) if f_stat else IND_RATE
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
            code = (row.get("INDICATOR") or IND_RATE).strip()
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
                    indicator_code=code,
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
