"""Nova Scotia Open Data connector — VirtualCareNS (Digital Inclusion / online health).

Nova Scotia's **VirtualCareNS** program lets residents without a family doctor get
primary care online (virtual visits). Its uptake is published in the same
Action-for-Health "Accessing Primary Care in Nova Scotia" tracker (Socrata
resource `fac5-58sq`) that `ns_open_data` already reads — the `type` dimension
includes a `VirtualCareNS` channel alongside the pharmacy/UCC/clinic channels.

This is a real, NS-specific record of **online/virtual health-service use** — a
revealed digital-engagement signal that fits Digital Inclusion (using a digital
health service in practice), complementing the survey "internet use" indicator.

Schema confirmed via `hapi inspect ns_virtual_care` (2026-06): under
`type = VirtualCareNS` the tracker carries two measures —
  * "Visits were completed through VirtualCareNS" — a **monthly flow** (we sum to
    an annual provincial total): 2021 ≈ 4.1k, 2022 ≈ 32.4k, 2023 ≈ 75.3k;
  * "Nova Scotians have registered for VirtualCareNS" — a **cumulative stock** of
    sign-ups (we take the year's latest value): ≈ 86k registered by Dec 2023.
The data spans **2021-06 .. 2023-12** — VirtualCareNS was wound down, so this is a
*historical* series, not a refreshing one.

Both are loaded as **Data-Hub series (not scored into the HAPI composite)**: the
program is discontinued, the counts are all-ages (and the system has no total-
population denominator for a clean per-capita rate), and visit volume is dominated
by the program roll-up — so it is descriptive data, not a normative index input.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "fac5-58sq"  # "Accessing Primary Care in Nova Scotia"

TARGET_TYPE = "VirtualCareNS"
_VISIT_HINTS = ("visit", "completed", "appointment", "consult", "seen")
_REG_HINTS = ("register", "registered", "sign", "enrol")
SUPPRESSED = {None, "", "x", "..", "n/a"}

IND_VISITS = "digital_inclusion.virtual_care_visits_ns"
IND_REGISTERED = "digital_inclusion.virtual_care_registered_ns"


def _is_virtual_type(t: str) -> bool:
    s = str(t).strip().lower().replace(" ", "")
    return "virtualcare" in s or ("virtual" in s and "care" in s)


def _measure_kind(measure: str) -> str | None:
    """Classify a VirtualCareNS measure: 'visits' (flow) or 'registered' (stock)."""
    m = str(measure).lower()
    if any(h in m for h in _REG_HINTS):
        return "registered"
    if any(h in m for h in _VISIT_HINTS):
        return "visits"
    return None


def _to_num(v) -> float | None:
    if v in SUPPRESSED:
        return None
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


class NSVirtualCareConnector(Connector):
    name = "ns_virtual_care"
    fixture_name = "ns_virtual_care.json"

    source = DataSourceSpec(
        name="Nova Scotia Open Data — VirtualCareNS (Accessing Primary Care)",
        publisher="Government of Nova Scotia",
        url=f"https://{NS_DOMAIN}/Health-and-Wellness/Accessing-Primary-Care-in-Nova-Scotia/{NS_RESOURCE}",
        access_method="api",
        licence="Open Government Licence – Nova Scotia",
        update_frequency="monthly",
        notes="Socrata resource fac5-58sq (Action for Health), type=VirtualCareNS. "
              "Annual provincial total of virtual-care counts — online/virtual "
              "health-service use (Digital Inclusion).",
    )

    indicators = [
        IndicatorSpec(
            code=IND_VISITS,
            domain="digital_inclusion",
            name="VirtualCareNS visits completed, Nova Scotia (annual)",
            definition="Annual provincial total of visits completed through VirtualCareNS "
                       "— online/virtual primary-care use. Data-Hub series (not scored).",
            formula="NS Open Data fac5-58sq: sum of `actual` where type='VirtualCareNS' "
                    "and measure is completed visits, by year across zones.",
            unit="visits/year",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "granularity": "annual"},
        ),
        IndicatorSpec(
            code=IND_REGISTERED,
            domain="digital_inclusion",
            name="VirtualCareNS registrations, Nova Scotia (cumulative)",
            definition="Cumulative number of Nova Scotians registered for VirtualCareNS "
                       "online primary care — a digital-adoption stock. Data-Hub series "
                       "(not scored).",
            formula="NS Open Data fac5-58sq: latest `actual` per year where "
                    "type='VirtualCareNS' and measure is registrations.",
            unit="people registered (cumulative)",
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
        # visits -> sum per year; registered (cumulative) -> latest (max) per year.
        visits: dict[str, float] = {}
        registered: dict[tuple[str, str], float] = {}  # (year, YYYY-MM) -> value
        for row in rows:
            if not _is_virtual_type(row.get("type", "")):
                continue
            ym = str(row.get("date", ""))[:7]
            year = ym[:4]
            if len(year) < 4:
                continue
            val = _to_num(row.get("actual"))
            if val is None:
                continue
            kind = _measure_kind(row.get("measure_name", ""))
            if kind == "visits":
                visits[year] = visits.get(year, 0.0) + val
            elif kind == "registered":
                # keep the latest month's cumulative value within each year
                prev = registered.get(year)
                if prev is None or ym >= prev[0]:
                    registered[year] = (ym, val)

        records: list[ObservationRecord] = []
        for year, total in sorted(visits.items()):
            records.append(ObservationRecord(
                indicator_code=IND_VISITS, jurisdiction_code="CA-NS",
                period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                value=round(total, 1)))
        for year, (_, val) in sorted(registered.items()):
            records.append(ObservationRecord(
                indicator_code=IND_REGISTERED, jurisdiction_code="CA-NS",
                period_start=f"{year}-01-01", period_end=f"{year}-12-31",
                value=round(val, 1)))
        return records

    def inspect_live(self) -> str:
        payload = self.fetch_live()
        rows = json.loads(payload.content.decode("utf-8"))
        v = [r for r in rows if _is_virtual_type(r.get("type", ""))]
        if not v:
            types = sorted({str(r.get("type", "")) for r in rows})
            return f"no VirtualCareNS rows found. distinct types: {types}"
        measures = sorted({str(r.get("measure_name", "")) for r in v})
        dates = sorted({str(r.get("date", ""))[:10] for r in v})
        recs = self.parse(payload)
        summary = {(r.indicator_code.split(".")[-1], r.period_start[:4]): r.value for r in recs}
        return (
            f"VirtualCareNS rows: {len(v)}\n"
            f"distinct measure_name(s): {measures}\n"
            f"date range: {dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}\n"
            f"parsed annual values: {summary}\n"
            f"sample rows: {v[:4]}"
        )
