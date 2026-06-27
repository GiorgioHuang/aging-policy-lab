"""Nova Scotia Open Data connector — Long-Term Care Waitlist (Care Access).

Nova Scotia tracks the number of people waiting for a long-term care placement
(weekly) and publishes it on data.novascotia.ca (Socrata resource `c39g-gsdd`).
This is a real, API-accessible NS continuing-care **access** measure — and the
replacement for CIHI's home-care client counts, which exclude Nova Scotia
entirely (NS does not submit to CIHI's HCRS/IRRS).

We derive an annual provincial figure: the mean weekly LTC waitlist over the
year, normalized per 1,000 population aged 65+ (the StatCan denominator), and
scored lower_is_better (fewer people waiting = better access). NS-only (→ CA-NS);
there is no federal/national equivalent here.

Schema confirmed via `hapi inspect ns_ltc_waitlist` (2026-06): resource
`c39g-gsdd` returns weekly province-wide rows (no zone breakdown) with columns
`year, date, waiting_in_the_community, waiting_in_hospital,
total_waiting_for_initial_placement, waiting_for_inter_facility_transfer`,
covering 2011-04 .. 2026-03. We take **`total_waiting_for_initial_placement`**
(community + hospital) as the headline count — the people waiting for an initial
LTC placement — not the `waiting_in_the_community` subset. The matchers stay
tolerant (and prefer the total) in case the column wording shifts.
"""
from __future__ import annotations

import json
import statistics
import urllib.parse
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

NS_DOMAIN = "data.novascotia.ca"
NS_RESOURCE = "c39g-gsdd"  # Long-Term Care Waitlist

_DATE_HINTS = ("date", "week", "month", "period", "as_of", "reporting", "snapshot")
_COUNT_HINTS = ("wait", "number", "count", "clients", "individuals", "people", "total", "value")
_ZONE_HINTS = ("zone", "region", "network", "area", "geography", "geo", "district")
# Preferred count columns, most-specific first: the headline "total waiting for an
# initial placement" beats the community-only / hospital-only / transfer subsets.
_COUNT_PREFER = (
    "total_waiting_for_initial_placement",
    "total_waiting",
    "initial_placement",
)
SUPPRESSED = {None, "", "x", "..", "n/a", "N/A"}


def _find_key(row: dict, hints: tuple[str, ...], avoid: tuple[str, ...] = ()) -> str | None:
    for k in row:
        kl = k.lower()
        if any(a in kl for a in avoid):
            continue
        if any(h in kl for h in hints):
            return k
    return None


def _find_count_key(row: dict) -> str | None:
    norm = {k: k.lower().replace(" ", "_") for k in row}
    for pref in _COUNT_PREFER:
        for k, kl in norm.items():
            if pref in kl:
                return k
    return _find_key(row, _COUNT_HINTS, avoid=_DATE_HINTS)


def _to_float(v) -> float | None:
    if v in SUPPRESSED:
        return None
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


class NSLTCWaitlistConnector(Connector):
    name = "ns_ltc_waitlist"
    fixture_name = "ns_ltc_waitlist.json"

    source = DataSourceSpec(
        name="Nova Scotia Open Data — Long-Term Care Waitlist",
        publisher="Government of Nova Scotia",
        url=f"https://{NS_DOMAIN}/Health-and-Wellness/Long-term-Care-Waitlist/{NS_RESOURCE}",
        access_method="api",
        licence="Open Government Licence – Nova Scotia",
        update_frequency="weekly",
        notes="Socrata resource c39g-gsdd (Action for Health). Number waiting for "
              "long-term care placement; annualized to the mean weekly count, NS total.",
    )

    indicators = [
        IndicatorSpec(
            code="care_access.ltc_waitlist_ns",
            domain="care_access",
            name="Long-term care waitlist, Nova Scotia",
            definition="Number of people waiting for a long-term care placement in "
                       "Nova Scotia (annual mean of the weekly waitlist).",
            formula="NS Open Data c39g-gsdd, mean weekly count per year, per 1,000 "
                    "population aged 65+.",
            unit="people waiting per 1,000 pop 65+",
            direction="lower_is_better",
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

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        rows = json.loads(payload.content.decode("utf-8"))
        if not rows:
            return []
        sample = rows[0]
        f_date = _find_key(sample, _DATE_HINTS)
        f_count = _find_count_key(sample)
        f_zone = _find_key(sample, _ZONE_HINTS)
        if not f_date or not f_count:
            return []

        # provincial weekly total: sum any zone breakdown per date, else take the row
        weekly: dict[str, float] = {}
        for row in rows:
            d = str(row.get(f_date, ""))[:10]
            if len(d) < 7:
                continue
            val = _to_float(row.get(f_count))
            if val is None:
                continue
            # If a zone column exists, a "provincial/total" row would double count —
            # prefer summing zone rows; if no zone column, each row is the total.
            weekly[d] = weekly.get(d, 0.0) + val if f_zone else val

        # annualize: mean weekly count per year
        by_year: dict[str, list[float]] = {}
        for d, v in weekly.items():
            by_year.setdefault(d[:4], []).append(v)

        records: list[ObservationRecord] = []
        for year, vals in sorted(by_year.items()):
            records.append(
                ObservationRecord(
                    indicator_code="care_access.ltc_waitlist_ns",
                    jurisdiction_code="CA-NS",
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=round(statistics.mean(vals), 1),
                )
            )
        return records

    def inspect_live(self) -> str:
        payload = self.fetch_live()
        rows = json.loads(payload.content.decode("utf-8"))
        if not rows:
            return "no rows returned"
        keys = list(rows[0].keys())
        f_date = _find_key(rows[0], _DATE_HINTS)
        f_count = _find_count_key(rows[0])
        f_zone = _find_key(rows[0], _ZONE_HINTS)
        zones = sorted({str(r.get(f_zone, "")) for r in rows}) if f_zone else []
        dates = sorted({str(r.get(f_date, ""))[:10] for r in rows}) if f_date else []
        return (
            f"row count: {len(rows)}\n"
            f"keys: {keys}\n"
            f"detected date={f_date!r}, count={f_count!r}, zone={f_zone!r}\n"
            f"distinct zones: {zones[:20]}\n"
            f"date range: {dates[0] if dates else '-'} .. {dates[-1] if dates else '-'} "
            f"({len(dates)} distinct)\n"
            f"sample rows: {rows[:3]}"
        )
