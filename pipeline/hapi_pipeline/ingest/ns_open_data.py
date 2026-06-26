"""Nova Scotia Open Data connector — Socrata SODA API (docs/10 §3.1).

VERIFIED 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Dataset "Accessing Primary Care in Nova Scotia", Socrata resource id
    `fac5-58sq` on https://data.novascotia.ca/ — the public "Need a Family
    Practice Registry" reporting (registrants seeking attachment to a primary
    care provider, with percent-of-population, at provincial / zone / network
    level). This measures UNMET primary-care need, so direction is
    lower_is_better (a higher share on the registry = worse access).

TO CONFIRM on first --live run: the exact Socrata column names. SODA returns a
JSON array of records (all values as strings); `parse()` discovers the date,
geography, and percent columns heuristically and logs nothing it can't map, so
a column rename degrades gracefully rather than loading wrong values.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "fac5-58sq"  # "Accessing Primary Care in Nova Scotia"

# Heuristic column discovery (confirm exact names on first --live).
_DATE_HINTS = ("month", "date", "period", "as_of", "reporting")
_GEO_HINTS = ("zone", "geography", "network", "area", "region", "geo")
_PCT_HINTS = ("percent", "per_cent", "pct", "population")
# A provincial-total geography value (we want the province, not a sub-zone).
_PROVINCIAL = {"nova scotia", "province", "provincial", "ns", "total", "all zones",
               "nova scotia health"}


def _find_key(row: dict, hints: tuple[str, ...]) -> str | None:
    for k in row:
        kl = k.lower()
        if any(h in kl for h in hints):
            return k
    return None


class NSOpenDataConnector(Connector):
    name = "ns_open_data"
    fixture_name = "ns_primary_care_registry.json"

    source = DataSourceSpec(
        name="Nova Scotia Open Data — Accessing Primary Care (Need a Family Practice Registry)",
        publisher="Government of Nova Scotia",
        url=f"https://{NS_DOMAIN}/Health-and-Wellness/Accessing-Primary-Care-in-Nova-Scotia/{NS_RESOURCE}",
        access_method="api",
        licence="Open Government Licence – Nova Scotia",
        update_frequency="monthly",
        notes="Socrata SODA resource fac5-58sq. Percent of population on the Need a "
              "Family Practice Registry (unmet primary-care need).",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.primary_care_unmet_need_pct",
            domain="care_access",
            name="Population needing a primary care provider",
            definition="Percent of the population on the Need a Family Practice Registry "
                       "(seeking attachment to a primary care provider).",
            formula="100 * (registrants seeking attachment) / (total population).",
            unit="% of population",
            direction="lower_is_better",
            normalization={"method": "min_max", "min": 0, "max": 25},
            coverage={"jurisdictions": ["CA-NS"], "from": 2019},
        )
    ]

    def fetch_live(self) -> RawPayload:
        query = urllib.parse.urlencode({"$limit": 50000})
        url = f"https://{NS_DOMAIN}/resource/{NS_RESOURCE}.json?{query}"
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            content = resp.read()
        return RawPayload(content=content, source_version=f"SODA:{NS_RESOURCE}",
                          content_type="application/json")

    def inspect_live(self) -> str:
        payload = self.fetch_live()
        rows = json.loads(payload.content.decode("utf-8"))
        if not rows:
            return "no rows returned"
        keys = list(rows[0].keys())
        geo_key = _find_key(rows[0], _GEO_HINTS)
        date_key = _find_key(rows[0], _DATE_HINTS)
        pct_key = _find_key(rows[0], _PCT_HINTS)
        geos = sorted({str(r.get(geo_key, "")) for r in rows})[:30] if geo_key else []
        return (
            f"row count: {len(rows)}\n"
            f"keys: {keys}\n"
            f"detected date={date_key!r}, geo={geo_key!r}, pct={pct_key!r}\n"
            f"distinct geo values (<=30): {geos}\n"
            f"sample rows: {rows[:3]}"
        )

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        rows = json.loads(payload.content.decode("utf-8"))
        records: list[ObservationRecord] = []
        if not rows:
            return records
        date_key = _find_key(rows[0], _DATE_HINTS)
        geo_key = _find_key(rows[0], _GEO_HINTS)
        pct_key = _find_key(rows[0], _PCT_HINTS)
        if not (date_key and pct_key):
            return records  # cannot map -> quality check reports 0 records

        for row in rows:
            # keep provincial totals only (skip sub-zone breakdowns)
            if geo_key is not None:
                geo_val = str(row.get(geo_key, "")).strip().lower()
                if geo_val and geo_val not in _PROVINCIAL:
                    continue
            year = str(row.get(date_key, ""))[:4]
            if not year.isdigit():
                continue
            raw = row.get(pct_key)
            value = None if raw in (None, "", "x", "..") else float(raw)
            records.append(
                ObservationRecord(
                    indicator_code="care_access.primary_care_unmet_need_pct",
                    jurisdiction_code="CA-NS",
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=value,
                )
            )
        return records
