"""CIHI connector — Long-Term Care Beds in Canada (Care Access capacity).

CIHI's "Long-Term Care Beds in Canada" data table: the number of LTC homes, LTC
beds, and **LTC beds per 1,000 population age 65 and older**, by jurisdiction.
LTC homes here are facilities offering 24-hour nursing care with publicly funded /
subsidized beds (CIHI's definition excludes assisted living, supportive housing
and retirement homes). It is a national, cross-jurisdiction capacity benchmark.

Acquisition: like all CIHI data this has **no open API** — it's a manual Excel
download (a dated snapshot; this fixture is the March 31, 2021 edition). `--live`
cannot auto-fetch; the loader degrades to this vendored fixture, which holds
**real captured values** (the Canada-total row → CA and the Nova Scotia row →
CA-NS). To refresh, download a newer edition and regenerate the slim CSV
(RUNBOOK.md §E).

Three indicators (INDICATOR-tagged slim CSV):
  * `care_access.ltc_beds_cihi_per_1k_65plus` — beds per 1,000 pop 65+ (scored,
    higher_is_better); CIHI's published figure is used directly (already a rate).
  * `care_access.ltc_beds_cihi_total` — raw LTC bed count (Data-Hub series).
  * `care_access.ltc_homes_cihi` — LTC home count (Data-Hub series).

CIHI's NS figure (32.76 beds / 1,000) corroborates the live NS Open Data measure
(`ns_ltc_facilities`, ~32.5); the two are kept as distinct, separately-sourced
indicators (different vintage + bed definition). Other provinces/territories are
in the source but out of v1 scope (the tree is CA + Federal/NS).
"""
from __future__ import annotations

import csv
import io

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

CIHI_URL = "https://www.cihi.ca/en/topics/long-term-care/data-tables"
SUPPRESSION_MARKERS = {"x", "X", "", "..", "n/a", "N/A", "*", "Not available"}

# slim-CSV INDICATOR tag -> indicator code
_TAG_TO_CODE = {
    "beds_per_1k": "care_access.ltc_beds_cihi_per_1k_65plus",
    "beds_total": "care_access.ltc_beds_cihi_total",
    "homes": "care_access.ltc_homes_cihi",
}


class CIHILTCBedsConnector(Connector):
    name = "cihi_ltc_beds"
    fixture_name = "cihi_ltc_beds.csv"

    source = DataSourceSpec(
        name="CIHI — Long-Term Care Beds in Canada",
        publisher="Canadian Institute for Health Information",
        url=CIHI_URL,
        access_method="portal_download",
        licence="CIHI terms (public data tables reusable with attribution)",
        update_frequency="irregular",
        notes="Long-Term Care Beds in Canada data table (Excel), manual download — "
              "no open API. LTC homes/beds and beds per 1,000 pop 65+; Canada total "
              "-> CA, Nova Scotia -> CA-NS. Snapshot edition (e.g. March 31, 2021).",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.ltc_beds_cihi_per_1k_65plus",
            domain="care_access",
            name="LTC beds per 1,000 pop 65+ (CIHI)",
            definition="Long-term-care beds (24-hour nursing, publicly funded) per 1,000 "
                       "population aged 65+, from CIHI's national data table.",
            formula="CIHI Long-Term Care Beds in Canada: 'Number of LTC beds per 1,000 "
                    "population age 65 and older' (used directly).",
            unit="beds per 1,000 pop 65+",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 15.0, "max": 50.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": 2021},
        ),
        IndicatorSpec(
            code="care_access.ltc_beds_cihi_total",
            domain="care_access",
            name="LTC beds, total (CIHI)",
            definition="Total number of long-term-care beds (24-hour nursing, publicly "
                       "funded), CIHI national data table. Data-Hub series (not scored).",
            formula="CIHI Long-Term Care Beds in Canada: 'Number of LTC beds'.",
            unit="beds",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": 2021},
        ),
        IndicatorSpec(
            code="care_access.ltc_homes_cihi",
            domain="care_access",
            name="LTC homes (CIHI)",
            definition="Number of long-term-care homes (24-hour nursing, publicly funded), "
                       "CIHI national data table. Data-Hub series (not scored).",
            formula="CIHI Long-Term Care Beds in Canada: 'Number of LTC homes'.",
            unit="homes",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": 2021},
        ),
    ]

    def fetch_live(self) -> RawPayload:
        raise NotImplementedError(
            "CIHI publishes the LTC beds data table as a manual Excel download, not an "
            f"open API. Download a newer edition from {CIHI_URL} and regenerate the slim "
            f"fixture {self.fixture_path} (RUNBOOK.md §E)."
        )

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        text = payload.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        records: list[ObservationRecord] = []
        for row in reader:
            code = _TAG_TO_CODE.get((row.get("indicator") or "").strip())
            jcode = (row.get("jurisdiction_code") or "").strip()
            year = (row.get("year") or "").strip()[:4]
            if not code or not jcode or not year:
                continue
            raw = (row.get("value") or "").strip()
            value = None if raw in SUPPRESSION_MARKERS else float(raw.replace(",", ""))
            records.append(
                ObservationRecord(
                    indicator_code=code,
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=value,
                )
            )
        return records
