"""Nova Scotia Open Data connector — VirtualCareNS (Digital Inclusion / online health).

Nova Scotia's **VirtualCareNS** program lets residents without a family doctor get
primary care online (virtual visits). Its uptake is published in the same
Action-for-Health "Accessing Primary Care in Nova Scotia" tracker (Socrata
resource `fac5-58sq`) that `ns_open_data` already reads — the `type` dimension
includes a `VirtualCareNS` channel alongside the pharmacy/UCC/clinic channels.

This is a real, live, NS-specific measure of **online/virtual health-service use**
— a revealed digital-engagement signal that fits Digital Inclusion (using a
digital health service in practice), complementing the survey "internet use"
indicator. We aggregate the VirtualCareNS `actual` counts to an annual provincial
total (summed across health zones / months).

TO CONFIRM on first run via `hapi inspect ns_virtual_care`: the exact
`measure_name`(s) carried under `type = VirtualCareNS` and what `actual` counts
(completed visits vs registrations), the date range, and the magnitude — so the
indicator definition + normalization can be finalised. The matchers are
intentionally tolerant; tighten here once inspected.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "fac5-58sq"  # "Accessing Primary Care in Nova Scotia"

TARGET_TYPE = "VirtualCareNS"
# Prefer a completed-visit measure when several VirtualCareNS measures exist.
_VISIT_HINTS = ("visit", "completed", "appointment", "consult", "seen")
SUPPRESSED = {None, "", "x", "..", "n/a"}


def _is_virtual_type(t: str) -> bool:
    s = str(t).strip().lower().replace(" ", "")
    return "virtualcare" in s or ("virtual" in s and "care" in s)


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
            code="digital_inclusion.virtual_care_visits_ns",
            domain="digital_inclusion",
            name="VirtualCareNS visits, Nova Scotia (annual)",
            definition="Annual provincial total of VirtualCareNS online primary-care "
                       "counts — a revealed measure of online/virtual health-service use.",
            formula="NS Open Data fac5-58sq: sum of `actual` where type='VirtualCareNS' "
                    "(visit measure), grouped by year across health zones.",
            unit="virtual-care counts/year",
            direction="higher_is_better",
            coverage={"jurisdictions": ["CA-NS"], "granularity": "annual"},
        )
    ]

    def fetch_live(self) -> RawPayload:
        query = urllib.parse.urlencode({"$limit": 50000})
        url = f"https://{NS_DOMAIN}/resource/{NS_RESOURCE}.json?{query}"
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            content = resp.read()
        return RawPayload(content=content, source_version=f"SODA:{NS_RESOURCE}",
                          content_type="application/json")

    @staticmethod
    def _virtual_rows(rows: list[dict]) -> list[dict]:
        v = [r for r in rows if _is_virtual_type(r.get("type", ""))]
        # If multiple measures exist, keep the visit-like one(s); else keep all.
        measures = {str(r.get("measure_name", "")).lower() for r in v}
        if len(measures) > 1 and any(any(h in m for h in _VISIT_HINTS) for m in measures):
            v = [r for r in v
                 if any(h in str(r.get("measure_name", "")).lower() for h in _VISIT_HINTS)]
        return v

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        rows = json.loads(payload.content.decode("utf-8"))
        yearly: dict[str, float] = {}
        for row in self._virtual_rows(rows):
            year = str(row.get("date", ""))[:4]
            if len(year) < 4:
                continue
            raw = row.get("actual")
            if raw in SUPPRESSED:
                continue
            yearly[year] = yearly.get(year, 0.0) + float(str(raw).replace(",", ""))

        records: list[ObservationRecord] = []
        for year, total in sorted(yearly.items()):
            records.append(
                ObservationRecord(
                    indicator_code="digital_inclusion.virtual_care_visits_ns",
                    jurisdiction_code="CA-NS",
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=round(total, 1),
                )
            )
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
        yearly: dict[str, float] = {}
        for r in self._virtual_rows(v):
            yr = str(r.get("date", ""))[:4]
            a = r.get("actual")
            if a not in SUPPRESSED and len(yr) == 4:
                yearly[yr] = yearly.get(yr, 0.0) + float(str(a).replace(",", ""))
        return (
            f"VirtualCareNS rows: {len(v)}\n"
            f"distinct measure_name(s): {measures}\n"
            f"date range: {dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}\n"
            f"annual sums (visit measure): {dict(sorted(yearly.items()))}\n"
            f"sample rows: {v[:4]}"
        )
