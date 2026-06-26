"""Nova Scotia Open Data connector — Socrata SODA API (docs/10 §3.1).

VERIFIED 2026-06 via `hapi inspect` against the live source:
  * Dataset "Accessing Primary Care in Nova Scotia", Socrata resource `fac5-58sq`
    on https://data.novascotia.ca/ — Nova Scotia's Action-for-Health primary-care
    access tracker. Columns: `zone, type, date, measure_name, actual`.
    `zone` ∈ {Central, Eastern, Northern, Western, Unknown} (health zones; there
    is NO provincial-total row), `type` is the access channel (e.g. "Community
    Pharmacy PCCs", "UCC", "Primary Care Clinics"), `actual` is a monthly count.

We derive a provincial Care-Access indicator by summing **Community Pharmacy
Primary Care Clinic visits** across all zones per month — a concrete measure of
expanded primary-care access (higher is better).
"""
from __future__ import annotations

import calendar
import json
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "fac5-58sq"  # "Accessing Primary Care in Nova Scotia"

# The access channel + measure we aggregate to a provincial monthly total.
TARGET_TYPE = "Community Pharmacy PCCs"
MEASURE_SUBSTR = "visits were completed"
SUPPRESSED = {None, "", "x", "..", "n/a"}

# Retained for `hapi inspect` diagnostics.
_DATE_HINTS = ("month", "date", "period", "as_of", "reporting")
_GEO_HINTS = ("zone", "geography", "network", "area", "region", "geo")
_PCT_HINTS = ("percent", "per_cent", "pct", "population")


def _find_key(row: dict, hints: tuple[str, ...]) -> str | None:
    for k in row:
        if any(h in k.lower() for h in hints):
            return k
    return None


class NSOpenDataConnector(Connector):
    name = "ns_open_data"
    fixture_name = "ns_accessing_primary_care.json"

    source = DataSourceSpec(
        name="Nova Scotia Open Data — Accessing Primary Care in Nova Scotia",
        publisher="Government of Nova Scotia",
        url=f"https://{NS_DOMAIN}/Health-and-Wellness/Accessing-Primary-Care-in-Nova-Scotia/{NS_RESOURCE}",
        access_method="api",
        licence="Open Government Licence – Nova Scotia",
        update_frequency="monthly",
        notes="Socrata resource fac5-58sq (Action for Health). Provincial monthly sum "
              "of Community Pharmacy Primary Care Clinic visits across health zones.",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.pharmacy_primary_care_visits",
            domain="care_access",
            name="Community pharmacy primary care visits (NS)",
            definition="Visits completed at Community Pharmacy Primary Care Clinics, "
                       "summed across Nova Scotia health zones, per month.",
            formula="Sum of `actual` where type='Community Pharmacy PCCs' and measure is "
                    "a completed-visits count, grouped by month across zones.",
            unit="visits/month",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "granularity": "monthly"},
        )
    ]

    def fetch_live(self) -> RawPayload:
        query = urllib.parse.urlencode({"$limit": 50000})
        url = f"https://{NS_DOMAIN}/resource/{NS_RESOURCE}.json?{query}"
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            content = resp.read()
        return RawPayload(content=content, source_version=f"SODA:{NS_RESOURCE}",
                          content_type="application/json")

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        rows = json.loads(payload.content.decode("utf-8"))
        monthly: dict[str, float] = {}
        for row in rows:
            if str(row.get("type", "")) != TARGET_TYPE:
                continue
            if MEASURE_SUBSTR not in str(row.get("measure_name", "")).lower():
                continue
            ym = str(row.get("date", ""))[:7]  # YYYY-MM
            if len(ym) < 7:
                continue
            raw = row.get("actual")
            if raw in SUPPRESSED:
                continue
            monthly[ym] = monthly.get(ym, 0.0) + float(str(raw).replace(",", ""))

        records: list[ObservationRecord] = []
        for ym, total in sorted(monthly.items()):
            year, month = int(ym[:4]), int(ym[5:7])
            last_day = calendar.monthrange(year, month)[1]
            records.append(
                ObservationRecord(
                    indicator_code="care_access.pharmacy_primary_care_visits",
                    jurisdiction_code="CA-NS",
                    period_start=f"{ym}-01",
                    period_end=f"{ym}-{last_day:02d}",
                    value=total,
                )
            )
        return records

    def inspect_live(self) -> str:
        payload = self.fetch_live()
        rows = json.loads(payload.content.decode("utf-8"))
        if not rows:
            return "no rows returned"
        keys = list(rows[0].keys())
        geo_key = _find_key(rows[0], _GEO_HINTS)
        date_key = _find_key(rows[0], _DATE_HINTS)
        types = sorted({str(r.get("type", "")) for r in rows})[:30]
        geos = sorted({str(r.get(geo_key, "")) for r in rows}) if geo_key else []
        return (
            f"row count: {len(rows)}\n"
            f"keys: {keys}\n"
            f"detected date={date_key!r}, geo={geo_key!r}\n"
            f"distinct zones: {geos}\n"
            f"distinct types (<=30): {types}\n"
            f"sample rows: {rows[:3]}"
        )
