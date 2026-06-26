"""Nova Scotia Open Data connector — Socrata SODA API (docs/10 §3.1).

Real source: https://data.novascotia.ca/ (Socrata). SODA returns a JSON array of
records (column name -> value). We ingest a Care-Access measure for seniors:
the share of Nova Scotians attached to a primary care provider.

The fixture mirrors a SODA JSON response; `parse()` is tolerant of the usual
Socrata quirks (all values arrive as strings).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

# Socrata resource id (illustrative; verify the dataset + columns before --live).
NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "primary-care-attachment"  # placeholder resource slug


class NSOpenDataConnector(Connector):
    name = "ns_open_data"
    fixture_name = "ns_primary_care_attachment.json"

    source = DataSourceSpec(
        name="Nova Scotia Open Data — Primary care attachment",
        publisher="Government of Nova Scotia",
        url=f"https://{NS_DOMAIN}/",
        access_method="api",
        licence="Open Government Licence – Nova Scotia",
        update_frequency="annual",
        notes="Socrata SODA API. Share of population with a primary care provider.",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.primary_care_attachment_pct",
            domain="care_access",
            name="Primary care attachment rate",
            definition="Percent of the population attached to a regular primary care provider.",
            formula="100 * (persons with a primary care provider) / (total population).",
            unit="% of population",
            direction="higher_is_better",
            normalization={"method": "min_max", "min": 70, "max": 100},
            coverage={"jurisdictions": ["CA-NS"], "from": 2019},
        )
    ]

    def fetch_live(self) -> RawPayload:
        query = urllib.parse.urlencode({"$limit": 5000, "$order": "year"})
        url = f"https://{NS_DOMAIN}/resource/{NS_RESOURCE}.json?{query}"
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            content = resp.read()
        return RawPayload(content=content, source_version=f"SODA:{NS_RESOURCE}",
                          content_type="application/json")

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        rows = json.loads(payload.content.decode("utf-8"))
        records: list[ObservationRecord] = []
        for row in rows:
            year = str(row.get("year") or row.get("fiscal_year") or "")[:4]
            if not year:
                continue
            raw = row.get("attachment_rate", row.get("value"))
            value = None if raw in (None, "", "x", "..") else float(raw)
            records.append(
                ObservationRecord(
                    indicator_code="care_access.primary_care_attachment_pct",
                    jurisdiction_code="CA-NS",
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=value,
                )
            )
        return records
