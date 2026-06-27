"""CIHI / IRRS connector — home-care clients 65+ (docs/10 §2.5).

CIHI public *data tables* are portal downloads (Excel/CSV), not an open API, and
record-level data is controlled access — so this connector ingests a CSV captured
from a CIHI public data table (access_method='portal_download'). `--live` cannot
auto-fetch; refreshing means downloading the latest table from CIHI by hand (see
RUNBOOK.md §E for the exact steps).

Role in HAPI: this is now a **complement**, not the backbone, of the Care Access
domain. The live, API-accessible Care-Access indicator is CCHS "has a regular
healthcare provider" (statcan_cchs, Table 13-10-0096), which auto-refreshes; this
CIHI home-care-clients series adds a service-utilization view but is on a manual
cadence. Until the next manual capture, its fixture holds illustrative values
(clearly labelled) — the domain no longer depends on it for live, official data.

System transition: CIHI decommissioned HCRS/HCRS-CA (home care) in March 2025 and
CCRS (LTC) by March 2026, consolidating onto the Integrated interRAI Reporting
System (IRRS). Forward home-care/LTC figures come from IRRS; older systems are for
historical continuity only. The series break is recorded in DataSource.notes.
"""
from __future__ import annotations

import csv
import io

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

CIHI_DATA_TABLES_URL = "https://www.cihi.ca/en/access-data-and-reports/data-tables"
SUPPRESSION_MARKERS = {"x", "X", "", "..", "n/a", "N/A", "*"}


class CIHIIRRSConnector(Connector):
    name = "cihi_irrs"
    fixture_name = "cihi_home_care_clients_65plus.csv"

    source = DataSourceSpec(
        name="CIHI — Home care clients (IRRS / historical HCRS)",
        publisher="Canadian Institute for Health Information",
        url=CIHI_DATA_TABLES_URL,
        access_method="portal_download",
        licence="CIHI terms (public tables reusable with attribution)",
        update_frequency="annual",
        notes=(
            "Public data table, manual download. HCRS decommissioned 2025-03, CCRS "
            "by 2026-03; IRRS is the forward source. Handle the HCRS->IRRS series "
            "break explicitly when trending across the transition."
        ),
    )

    indicators = [
        IndicatorSpec(
            code="care_access.home_care_clients_65plus",
            domain="care_access",
            name="Home care clients aged 65 and over",
            definition="Number of distinct home care clients aged 65+ in the year.",
            formula="CIHI count of home care clients, age group 65+.",
            unit="clients",
            direction="higher_is_better",
            normalization={"method": "per_capita_then_min_max",
                           "denominator": "demography.population_65plus"},
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": 2019},
        )
    ]

    def fetch_live(self) -> RawPayload:
        raise NotImplementedError(
            "CIHI publishes data tables as manual portal downloads, not an open API. "
            f"Download the latest table from {CIHI_DATA_TABLES_URL} and replace "
            f"{self.fixture_path}."
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
                    indicator_code="care_access.home_care_clients_65plus",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=value,
                )
            )
        return records
