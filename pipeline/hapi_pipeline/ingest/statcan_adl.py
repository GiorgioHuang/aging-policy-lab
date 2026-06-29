"""StatCan connector — ADL difficulty at 65+ (Table 13-10-0789), Independence.

The share of seniors (65+) with difficulty or who need help with activities of
daily living (ADL) — bathing, dressing, eating, moving about — the most direct
measure of functional independence in later life. Source is the Canadian Health
Survey on Seniors (CHSS, 2019/2020). lower_is_better.

Source (WebSearch 2026-06; direct gov fetch blocked in this sandbox — the exact
ADL characteristic + statistic wording is confirmed on a networked runner with
`hapi inspect statcan_adl`, then the matcher below is narrowed to one member):
  * Table 13-10-0789 "Health characteristics of seniors aged 65 and over,
    Canadian Health Survey on Seniors, by age group and sex, Canada (excluding
    territories) and provinces" (productId 13100789).
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310078901
  * Filtered to GEO ∈ {Canada(excl. terr.), Nova Scotia}, age 65+, both sexes,
    the percentage statistic, and an ADL-difficulty/help characteristic.

Filters match case-insensitively by substring and are deliberately tolerant.
"""
from __future__ import annotations

import csv
import io

from . import _statcan as sc
from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "13100789"
MIN_YEAR = 2015
INDICATOR = "independence.adl_difficulty_65plus"

_DIM_HINTS = {
    "age": ("age",),
    "sex": ("sex", "gender"),
    "indicator": ("indicator", "characteristic", "health characteristic"),
    "statistic": ("characteristic", "statistic"),
}


def _classify(indicator: str) -> str | None:
    """Map a CHSS health-characteristic member to the ADL indicator. Broad on the
    first pass (so inspect surfaces every ADL-related member); narrow to one after
    inspection."""
    h = indicator.strip().lower()
    adl = "daily living" in h or "adl" in h
    limited = any(w in h for w in ("difficulty", "needs help", "need help",
                                   "received help", "receives help", "impairment",
                                   "at least one"))
    return INDICATOR if (adl and limited) else None


def _is_percent(stat: str) -> bool:
    s = stat.strip().lower()
    if any(w in s for w in ("confidence", "interval", "low", "high", "margin")):
        return False
    return s == "" or "percent" in s or "proportion" in s or "%" in s


class StatCanADLConnector(Connector):
    name = "statcan_adl"
    fixture_name = "statcan_adl_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Health characteristics of seniors, CHSS (Table 13-10-0789)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310078901",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="periodic",
        notes="WDS getFullTableDownloadCSV(13100789), Canadian Health Survey on "
              "Seniors; filtered to 65+, both sexes, percentage, ADL difficulty/help.",
    )

    indicators = [
        IndicatorSpec(
            code=INDICATOR,
            domain="independence",
            name="Difficulty / needs help with activities of daily living, 65+",
            definition="Share of persons aged 65+ who have difficulty with, or need help "
                       "for, one or more activities of daily living (Canadian Health "
                       "Survey on Seniors) — a direct functional-independence measure.",
            formula="StatCan Table 13-10-0789: age 65+, both sexes, percent, ADL "
                    "difficulty/help characteristic.",
            unit="% of persons 65+",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 5.0, "max": 40.0},
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
        f_ind = sc.find_field(fields, "indicator", "health characteristic")
        f_stat = next((f for f in fields if "characteristic" in f.lower() and f != f_ind), "")
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
