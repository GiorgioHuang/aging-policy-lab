"""CIHI connector — CCRS / IRRS LTC Quick Stats (residential LTC residents, Care Access).

CIHI's "Residential and Hospital-Based Continuing Care — LTC Quick Stats"
(Continuing Care Reporting System / Integrated interRAI Reporting System) reports,
by province, the number of facilities and **residents** in residential long-term
care that submit to CCRS/IRRS. This is the institutional-LTC **client-count**
(client/resident utilization) view of Care Access — the metric that was previously
a gap for Nova Scotia.

Key coverage fact (confirmed from the uploaded data tables): **Nova Scotia only
began submitting to CCRS/IRRS-LTCF in 2024-2025** — earlier editions (2020-21 …
2023-24) have no NS column. So this connector currently carries the single
**2024-2025** NS snapshot (anchored to year 2024). The Quick Stats "Total
residential care" column is *partial* (only submitting provinces, excludes Quebec,
and the submitting set changes year to year), so it is **not** a Canada total and
is deliberately not loaded as CA.

Acquisition: manual CIHI Excel download (no open API), like the other `cihi_*`
connectors — the loader degrades to this vendored fixture, which holds **real
captured values**. Refresh / extend the series as new fiscal-year editions add NS
(RUNBOOK.md §E).

Indicators (INDICATOR-tagged slim CSV) — all **descriptive Data-Hub series**, not
scored into the HAPI composite (the direction of "more LTC residents" is not
normatively clear in a healthy-aging/aging-in-place frame):
  * `care_access.ltc_residents_cihi` — residents in residential LTC.
  * `care_access.ltc_residents_assessed_cihi` — RAI-MDS-assessed residents.
  * `care_access.ltc_facilities_ccrs` — facilities submitting to CCRS/IRRS
    (a submitting subset — distinct from the licensed-facility counts in
    `ns_ltc_facilities` and `cihi_ltc_beds`).
"""
from __future__ import annotations

import csv
import io

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

CIHI_URL = "https://www.cihi.ca/en/topics/long-term-care"
SUPPRESSION_MARKERS = {"x", "X", "", "..", "n/a", "N/A", "*", "Not available"}

_TAG_TO_CODE = {
    "residents": "care_access.ltc_residents_cihi",
    "assessed_residents": "care_access.ltc_residents_assessed_cihi",
    "facilities": "care_access.ltc_facilities_ccrs",
}


class CIHICCRSLTCConnector(Connector):
    name = "cihi_ccrs_ltc"
    fixture_name = "cihi_ccrs_ltc.csv"

    source = DataSourceSpec(
        name="CIHI — CCRS/IRRS LTC Quick Stats (residential continuing care)",
        publisher="Canadian Institute for Health Information",
        url=CIHI_URL,
        access_method="portal_download",
        licence="CIHI terms (public data tables reusable with attribution)",
        update_frequency="annual",
        notes="Residential and Hospital-Based Continuing Care / LTC Quick Stats "
              "(CCRS/IRRS-LTCF), manual Excel — no open API. Residents and facilities "
              "in residential LTC; Nova Scotia present from 2024-2025 (-> CA-NS).",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.ltc_residents_cihi",
            domain="care_access",
            name="Residential LTC residents (CIHI CCRS/IRRS)",
            definition="Number of residents in residential long-term-care facilities "
                       "submitting to CIHI's CCRS/IRRS — an institutional-LTC client-count "
                       "(utilization) measure. Data-Hub series (not scored).",
            formula="CCRS/IRRS LTC Quick Stats, Table 1 'Number of residents', "
                    "Nova Scotia residential care column, by fiscal year (start year).",
            unit="residents",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "from": 2024},
        ),
        IndicatorSpec(
            code="care_access.ltc_residents_assessed_cihi",
            domain="care_access",
            name="Residential LTC residents assessed (RAI-MDS, CIHI)",
            definition="Residents assessed with RAI-MDS 2.0 in residential LTC submitting "
                       "to CCRS/IRRS. Data-Hub series (not scored).",
            formula="CCRS/IRRS LTC Quick Stats, Table 1 'Number of assessed residents'.",
            unit="residents",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "from": 2024},
        ),
        IndicatorSpec(
            code="care_access.ltc_facilities_ccrs",
            domain="care_access",
            name="LTC facilities submitting to CCRS/IRRS (CIHI)",
            definition="Number of residential-LTC facilities submitting to CIHI's "
                       "CCRS/IRRS (a submitting subset — not the full licensed count). "
                       "Data-Hub series (not scored).",
            formula="CCRS/IRRS LTC Quick Stats, Table 1 'Number of facilities'.",
            unit="facilities",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "from": 2024},
        ),
    ]

    def fetch_live(self) -> RawPayload:
        raise NotImplementedError(
            "CIHI publishes the CCRS/IRRS LTC Quick Stats as manual Excel downloads, not "
            f"an open API. Download newer fiscal-year editions from {CIHI_URL} and "
            f"regenerate the slim fixture {self.fixture_path} (RUNBOOK.md §E)."
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
