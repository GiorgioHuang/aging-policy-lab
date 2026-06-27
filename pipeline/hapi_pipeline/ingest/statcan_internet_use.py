"""StatCan connector — seniors' internet use (Table 22-10-0135), Digital Inclusion.

Source confirmed 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 22-10-0135 "Internet use by province and age group" (productId
    22100135), from the Canadian Internet Use Survey (CIUS), Canada + provinces.
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013501
  * CIUS is a biennial survey (2018, 2020, 2022 …), so this series is biennial,
    not annual — the composite blends it only in survey years.
  * Pulled as the WDS full-table CSV and filtered to age = 65 years and over and,
    where present, the "used the Internet" characteristic (the headline rate).

HAPI Digital Inclusion indicator for older adults: the share of seniors who used
the Internet. Direction is higher_is_better.

TO CONFIRM on first --live run via `hapi inspect statcan_internet_use`: the exact
age-group label and whether a separate "Internet use" characteristic column
exists / its member wording. The filter matches case-insensitively by substring
and is tolerant; tighten here if inspection differs.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "22100135"
GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
MIN_YEAR = 2018

_DIM_HINTS = {
    "age": ("age",),
    "internet_use": ("internet use", "characteristic", "internet"),
    "statistic": ("statistic",),
}


def _is_used_internet(use: str) -> bool:
    """Keep the headline 'used the Internet' member; tolerate absence of the column."""
    u = use.strip().lower()
    if u == "":
        return True
    return "used the internet" in u or u in {"internet users", "used internet", "internet use"}


class StatCanInternetUseConnector(Connector):
    name = "statcan_internet_use"
    fixture_name = "statcan_internet_use_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Internet use by province and age group (Table 22-10-0135)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013501",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="biennial",
        notes="WDS getFullTableDownloadCSV(22100135) from the Canadian Internet Use "
              "Survey; filtered to 65+ and the 'used the Internet' characteristic. "
              "Biennial survey (2018/2020/2022…).",
    )

    indicators = [
        IndicatorSpec(
            code="digital_inclusion.internet_use_65plus",
            domain="digital_inclusion",
            name="Internet use, population 65+",
            definition="Share of persons aged 65+ who used the Internet (Canadian "
                       "Internet Use Survey).",
            formula="StatCan Table 22-10-0135: age='65 years and over', characteristic="
                    "'used the Internet'.",
            unit="% of persons 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 50.0, "max": 95.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR, "cadence": "biennial"},
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
        f_use = sc.find_field(fields, "internet use", "characteristic")
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "VALUE", "STATUS"])
        for row in reader:
            geo = sc.col(row, "GEO")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if f_age and not sc.is_age_65plus(row.get(f_age, "")):
                continue
            if f_use and not _is_used_internet(row.get(f_use, "")):
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
                    indicator_code="digital_inclusion.internet_use_65plus",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
