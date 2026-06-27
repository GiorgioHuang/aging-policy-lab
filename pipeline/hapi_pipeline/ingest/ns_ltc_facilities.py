"""Nova Scotia Open Data connector — Long-Term Care & Residential Care Facilities.

NS publishes its directory of licensed long-term-care (nursing home) and
residential-care facilities on data.novascotia.ca (Socrata resource `x76a-axw2`),
typically with facility type, bed count, and health zone / municipality. This is
a real, API-accessible NS **capacity / supply** source for Care Access.

From the facility list we derive two provincial figures:
  * total licensed **nursing-home (LTC) permanent beds** → **beds per 1,000
    population 65+** (the CIHI-comparable capacity measure; CIHI reports NS ≈ 33
    LTC beds / 1,000 pop 65+), scored higher_is_better;
  * the **count of facilities** — a Data-Hub series (not scored into the
    composite, but recorded with full lineage).

Schema confirmed via `hapi inspect ns_ltc_facilities` (2026-06): resource
`x76a-axw2` returns one row per facility (145 in NS) with columns including
`facility_type` (Nursing Home / Residential Care Facility / both), `zone`
(Central/Eastern/Northern/Western), and separate bed counts
`nursing_homes_nh_no_of_beds`, `nursing_homes_nh_no_of_respite_beds`,
`residential_care_facilities_rcf_no_of_beds`, `rcf_respite_beds`. We sum the
**nursing-home permanent-bed** column(s) only — excluding respite (short-stay)
and residential-care beds — to match CIHI's "long-term care beds" definition
(~8,000 beds ≈ 32-33 per 1,000 pop 65+).

The resource is a **current snapshot** (no year column): each `--live` run records
the facilities as they stand *now*, stamped with the ingest year, so running it
once a year builds an annual capacity series. NS-only (→ CA-NS).
"""
from __future__ import annotations

import datetime
import json
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "x76a-axw2"  # Long-Term Care and Residential Care Facilities

_TYPE_HINTS = ("type", "category", "classification", "facility_type")
_ZONE_HINTS = ("zone", "region", "health", "district", "network")
SUPPRESSED = {None, "", "x", "..", "n/a", "N/A"}


def _find_key(row: dict, hints: tuple[str, ...], avoid: tuple[str, ...] = ()) -> str | None:
    for k in row:
        kl = k.lower()
        if any(a in kl for a in avoid):
            continue
        if any(h in kl for h in hints):
            return k
    return None


def _nh_bed_keys(row: dict) -> list[str]:
    """Nursing-home (LTC) **permanent** bed columns: name has 'nursing' + 'bed',
    excluding respite (short-stay) and residential-care beds. CIHI-comparable."""
    keys = []
    for k in row:
        kl = k.lower()
        if "bed" in kl and "nursing" in kl and "respite" not in kl:
            keys.append(k)
    # Fallback: if the wording shifts, any non-respite/non-RCF bed column.
    if not keys:
        keys = [k for k in row if "bed" in k.lower()
                and "respite" not in k.lower() and "rcf" not in k.lower()
                and "residential" not in k.lower()]
    return keys


def _to_float(v) -> float | None:
    if v in SUPPRESSED:
        return None
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


class NSLTCFacilitiesConnector(Connector):
    name = "ns_ltc_facilities"
    fixture_name = "ns_ltc_facilities.json"

    source = DataSourceSpec(
        name="Nova Scotia Open Data — Long-Term Care & Residential Care Facilities",
        publisher="Government of Nova Scotia",
        url=f"https://{NS_DOMAIN}/Health-and-Wellness/Long-Term-Care-and-Residential-Care-Facilities/{NS_RESOURCE}",
        access_method="api",
        licence="Open Government Licence – Nova Scotia",
        update_frequency="annual",
        notes="Socrata resource x76a-axw2. Directory of licensed LTC/residential-care "
              "facilities; we aggregate to provincial total beds + facility count, "
              "stamped with the ingest year (current snapshot).",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.ltc_beds_per_1k_65plus",
            domain="care_access",
            name="Long-term care beds per 1,000 pop 65+, Nova Scotia",
            definition="Total licensed long-term-care / residential-care beds in Nova "
                       "Scotia per 1,000 population aged 65+ (capacity measure).",
            formula="NS Open Data x76a-axw2: sum of bed counts ÷ "
                    "demography.population_65plus × 1,000.",
            unit="beds per 1,000 pop 65+",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "granularity": "annual"},
        ),
        IndicatorSpec(
            code="care_access.ltc_facilities_ns",
            domain="care_access",
            name="Long-term care & residential care facilities, Nova Scotia",
            definition="Count of licensed long-term-care and residential-care facilities "
                       "in Nova Scotia (Data-Hub series; not scored into the composite).",
            formula="NS Open Data x76a-axw2: number of facility rows.",
            unit="facilities",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "granularity": "annual"},
        ),
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
        if not rows:
            return []
        bed_keys = _nh_bed_keys(rows[0])

        total_beds = 0.0
        beds_seen = False
        facilities = 0
        for row in rows:
            facilities += 1
            for bk in bed_keys:
                b = _to_float(row.get(bk))
                if b is not None:
                    total_beds += b
                    beds_seen = True

        year = datetime.date.today().year
        records: list[ObservationRecord] = [
            ObservationRecord(
                indicator_code="care_access.ltc_facilities_ns",
                jurisdiction_code="CA-NS",
                period_start=f"{year}-01-01",
                period_end=f"{year}-12-31",
                value=float(facilities),
            )
        ]
        if beds_seen:
            records.append(
                ObservationRecord(
                    indicator_code="care_access.ltc_beds_per_1k_65plus",
                    jurisdiction_code="CA-NS",
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=round(total_beds, 1),
                )
            )
        return records

    def inspect_live(self) -> str:
        payload = self.fetch_live()
        rows = json.loads(payload.content.decode("utf-8"))
        if not rows:
            return "no rows returned"
        keys = list(rows[0].keys())
        bed_keys = _nh_bed_keys(rows[0])
        f_type = _find_key(rows[0], _TYPE_HINTS)
        f_zone = _find_key(rows[0], _ZONE_HINTS)
        types = sorted({str(r.get(f_type, "")) for r in rows}) if f_type else []
        zones = sorted({str(r.get(f_zone, "")) for r in rows}) if f_zone else []
        total_beds = sum((_to_float(r.get(bk)) or 0.0) for r in rows for bk in bed_keys)
        return (
            f"row count (facilities): {len(rows)}\n"
            f"keys: {keys}\n"
            f"detected nursing-home bed columns={bed_keys!r}, type={f_type!r}, zone={f_zone!r}\n"
            f"distinct types: {types[:20]}\n"
            f"distinct zones: {zones[:20]}\n"
            f"summed nursing-home beds: {total_beds}\n"
            f"sample rows: {rows[:3]}"
        )
