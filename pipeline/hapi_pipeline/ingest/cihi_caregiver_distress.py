"""CIHI connector — Caregiver Distress (Independence complement).

CIHI's "Caregiver Distress" indicator: the percentage of long-stay home-care
clients whose unpaid (informal) caregiver shows distress, anger or depression, or
is unable to continue caring — a recognized measure of the **sustainability of
aging in place**. Higher distress threatens continued community living, so it sits
in the Independence domain (direction lower_is_better).

Acquisition: like all CIHI data this has **no open API** — it's a manual export
from CIHI's Your Health System / interRAI indicator library (Excel). `--live`
cannot auto-fetch; the loader degrades to this vendored fixture. The fixture holds
**real captured values** (province-level Nova Scotia → CA-NS, and the National row
→ CA, risk-adjusted percent, by fiscal year anchored to its start year). To
refresh, re-export the indicator and regenerate the slim CSV — see RUNBOOK.md §E.

Coverage note: CIHI reports this by province + health region + National. We keep
the National ("Canada") and Nova Scotia province rows (our v1 jurisdictions);
other provinces/regions are in the source but out of scope until the tree expands.
"""
from __future__ import annotations

import csv
import io

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

CIHI_INDICATOR_URL = "https://www.cihi.ca/en/indicators/caregiver-distress"
SUPPRESSION_MARKERS = {"x", "X", "", "..", "n/a", "N/A", "*", "Not available"}


class CIHICaregiverDistressConnector(Connector):
    name = "cihi_caregiver_distress"
    fixture_name = "cihi_caregiver_distress.csv"

    source = DataSourceSpec(
        name="CIHI — Caregiver Distress (home care)",
        publisher="Canadian Institute for Health Information",
        url=CIHI_INDICATOR_URL,
        access_method="portal_download",
        licence="CIHI terms (public indicator tables reusable with attribution)",
        update_frequency="annual",
        notes="Your Health System / interRAI indicator export (Excel), manual "
              "download — no open API. Risk-adjusted % of long-stay home-care "
              "clients with caregiver distress; National -> CA, Nova Scotia -> CA-NS.",
    )

    indicators = [
        IndicatorSpec(
            code="independence.caregiver_distress",
            domain="independence",
            name="Caregiver distress (long-stay home care clients)",
            definition="Risk-adjusted share of long-stay home-care clients whose unpaid "
                       "caregiver experiences distress — a measure of the sustainability "
                       "of aging in place.",
            formula="CIHI Caregiver Distress indicator, risk-adjusted rate; National "
                    "and Nova Scotia (province) reporting levels, by fiscal year.",
            unit="% of long-stay home care clients",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 15.0, "max": 50.0},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": 2018},
        )
    ]

    def fetch_live(self) -> RawPayload:
        raise NotImplementedError(
            "CIHI publishes indicators as manual Excel exports, not an open API. "
            f"Re-export from {CIHI_INDICATOR_URL} and regenerate the slim fixture "
            f"{self.fixture_path} (RUNBOOK.md §E)."
        )

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        text = payload.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        records: list[ObservationRecord] = []
        for row in reader:
            jcode = (row.get("jurisdiction_code") or "").strip()
            year = (row.get("year") or "").strip()[:4]
            if not jcode or not year:
                continue
            raw = (row.get("value") or "").strip()
            value = None if raw in SUPPRESSION_MARKERS else float(raw.replace(",", ""))
            records.append(
                ObservationRecord(
                    indicator_code="independence.caregiver_distress",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=value,
                )
            )
        return records
