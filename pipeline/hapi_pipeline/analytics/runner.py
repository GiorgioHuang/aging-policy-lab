"""Compute and persist analytic findings (docs/07 §5).

Tier-1 (association): a descriptive trend for every policy→indicator link.
Tier-2 (causal): one fully worked ITS example, tagged Causal(ITS) with its
assumptions and limitations. Findings upsert by slug (idempotent, recomputable).
"""
from __future__ import annotations

import json
from datetime import date

from . import descriptive, its

# Illustrative worked-ITS example (docs/07 §7): the NS community-pharmacy
# primary-care series has enough monthly points to demonstrate the estimator.
ITS_INDICATOR = "care_access.pharmacy_primary_care_visits"
ITS_JURISDICTION = "CA-NS"
ITS_INTERVENTION = date(2023, 8, 1)

TIER1_ASSUMPTIONS = "Descriptive trend only — shows co-movement, not causation."
TIER1_LIMITS = (
    "Association, not causation: no control group, no adjustment for coincident "
    "events (e.g. the pandemic, demographic shifts, other policies)."
)
ITS_LIMITS = (
    "Short monthly series and an ILLUSTRATIVE intervention date chosen to "
    "demonstrate the estimator — not a specific dated policy event. Treat the "
    "coefficients as a methods demonstration, not a causal finding: wide CIs, "
    "possible seasonality/ramp-up, single treated unit, no control series."
)

# Real, dated policy-event ITS on the long annual NS series. These tie a specific
# continuing-care policy to a plausibly-affected indicator. Still strongly
# caveated (annual data, single treated unit, no control), but — unlike the
# illustrative example above — the intervention is an actual dated policy.
REAL_ITS_LIMITS = (
    "Quasi-experimental ITS on a SINGLE annual series with no control group: the "
    "estimate assumes the pre-intervention trend would have continued absent the "
    "policy, and cannot separate the policy from coincident events (pandemic "
    "recovery, demographic ageing, other concurrent policies). Annual cadence "
    "means few post-intervention points and wide confidence intervals; a policy's "
    "effect on capacity/utilization also typically lags. Interpret as a structured, "
    "auditable starting point for evaluation, not a definitive causal estimate."
)

REAL_ITS = [
    {
        "indicator": "care_access.ltc_waitlist_ns",
        "jurisdiction": "CA-NS",
        "policy_title": "Long-Term Care: Build, Renovate, Replace",
        "intervention": date(2022, 9, 1),
        "title": "ITS: NS long-term-care waitlist around the 2022 LTC capital plan",
    },
    {
        "indicator": "care_access.ltc_workforce_per_1k_65plus",
        "jurisdiction": "CA-NS",
        "policy_title": "Continuing Care Assistant Workforce Strategy",
        "intervention": date(2022, 10, 1),
        "title": "ITS: NS nursing & residential-care workforce around the 2022 CCA strategy",
    },
]


def _upsert(cur, *, slug, title, tier, method, policy_id, indicator_code,
            jurisdiction_code, window_spec, result, assumptions, limitations):
    cur.execute(
        """INSERT INTO analysis_finding
               (slug, title, tier, method, policy_id, indicator_code,
                jurisdiction_code, window_spec, result, assumptions, limitations)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (slug) DO UPDATE SET
               title=EXCLUDED.title, tier=EXCLUDED.tier, method=EXCLUDED.method,
               policy_id=EXCLUDED.policy_id, indicator_code=EXCLUDED.indicator_code,
               jurisdiction_code=EXCLUDED.jurisdiction_code,
               window_spec=EXCLUDED.window_spec, result=EXCLUDED.result,
               assumptions=EXCLUDED.assumptions, limitations=EXCLUDED.limitations""",
        (slug, title, tier, method, policy_id, indicator_code, jurisdiction_code,
         json.dumps(window_spec), json.dumps(result), assumptions, limitations),
    )


def run_analyses(conn) -> int:
    written = 0
    with conn.cursor() as cur:
        # Findings are fully recomputable from policies + observations. Clear them
        # first so retired indicators and superseded slugs don't linger as orphans
        # (the observation store is append-only, but findings are derived state).
        cur.execute("DELETE FROM analysis_finding")

        # ── Tier 1: ONE descriptive trend per (indicator, jurisdiction),
        #    overlaying every policy that targets it (no per-policy duplicates) ──
        cur.execute(
            """SELECT pi.policy_id, p.title, p.released_at, j.code AS jur, i.code AS ind
                 FROM policy_indicator pi
                 JOIN policy p ON p.id = pi.policy_id
                 JOIN jurisdiction j ON j.id = p.jurisdiction_id
                 JOIN indicator i ON i.id = pi.indicator_id"""
        )
        groups: dict[tuple[str, str], list] = {}
        for policy_id, ptitle, released_at, pjur, ind in cur.fetchall():
            geo = "CA-NS" if pjur == "CA-NS" else "CA"  # national series for federal policies
            groups.setdefault((ind, geo), []).append((policy_id, ptitle, released_at))
        for (ind, geo), members in groups.items():
            series = descriptive.load_series(cur, ind, geo)
            if len(series) < 2:
                continue
            members = sorted(members, key=lambda m: m[2] or date.max)
            events = [{"title": t, "date": r.isoformat() if r else None} for (_pid, t, r) in members]
            tr = descriptive.trend(series)
            tr["policy_events"] = events
            tr["policy_event"] = events[0]["date"] if events else None  # back-compat
            _upsert(
                cur,
                slug=f"trend:{ind}:{geo}",
                title=f"Trend: {ind} in {geo}",
                tier="association",
                method="trend",
                policy_id=members[0][0],  # primary (earliest-dated) linked policy
                indicator_code=ind,
                jurisdiction_code=geo,
                window_spec={"from": tr["from"], "to": tr["to"],
                             "policies": [e["title"] for e in events]},
                result=tr,
                assumptions=TIER1_ASSUMPTIONS,
                limitations=TIER1_LIMITS,
            )
            written += 1

        # ── Tier 2: worked ITS example ────────────────────────────────────────
        series = descriptive.load_series(cur, ITS_INDICATOR, ITS_JURISDICTION)
        if series:
            cur.execute(
                "SELECT id FROM policy WHERE title = %s",
                ("Action for Health: Nova Scotia's Health Plan",),
            )
            row = cur.fetchone()
            policy_id = row[0] if row else None
            res = its.interrupted_time_series(series, ITS_INTERVENTION)
            _upsert(
                cur,
                slug=f"its:{ITS_INDICATOR}:{ITS_JURISDICTION}",
                title="ITS: NS community pharmacy primary-care visits (illustrative)",
                tier="causal",
                method="its",
                policy_id=policy_id,
                indicator_code=ITS_INDICATOR,
                jurisdiction_code=ITS_JURISDICTION,
                window_spec={"from": series[0][0].isoformat(),
                             "to": series[-1][0].isoformat(),
                             "intervention": ITS_INTERVENTION.isoformat(),
                             "n_pre": res.get("n_pre"), "n_post": res.get("n_post")},
                result=res,
                assumptions=its.ASSUMPTIONS,
                limitations=ITS_LIMITS,
            )
            written += 1

        # ── Tier 2: real, dated policy-event ITS on the long annual NS series ──
        for spec in REAL_ITS:
            series = descriptive.load_series(cur, spec["indicator"], spec["jurisdiction"])
            if not series:
                continue
            cur.execute("SELECT id FROM policy WHERE title = %s", (spec["policy_title"],))
            row = cur.fetchone()
            policy_id = row[0] if row else None
            res = its.interrupted_time_series(series, spec["intervention"])
            _upsert(
                cur,
                slug=f"its:{spec['indicator']}:{spec['jurisdiction']}",
                title=spec["title"],
                tier="causal",
                method="its",
                policy_id=policy_id,
                indicator_code=spec["indicator"],
                jurisdiction_code=spec["jurisdiction"],
                window_spec={"from": series[0][0].isoformat(),
                             "to": series[-1][0].isoformat(),
                             "intervention": spec["intervention"].isoformat(),
                             "policy": spec["policy_title"],
                             "n_pre": res.get("n_pre"), "n_post": res.get("n_post")},
                result=res,
                assumptions=its.ASSUMPTIONS,
                limitations=REAL_ITS_LIMITS,
            )
            written += 1

        conn.commit()
    return written
