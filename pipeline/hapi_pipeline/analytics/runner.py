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
        # ── Tier 1: trend per policy→indicator link ───────────────────────────
        cur.execute(
            """SELECT pi.policy_id, p.title, p.released_at, j.code AS jur, i.code AS ind
                 FROM policy_indicator pi
                 JOIN policy p ON p.id = pi.policy_id
                 JOIN jurisdiction j ON j.id = p.jurisdiction_id
                 JOIN indicator i ON i.id = pi.indicator_id"""
        )
        links = cur.fetchall()
        for policy_id, ptitle, released_at, pjur, ind in links:
            geo = "CA-NS" if pjur == "CA-NS" else "CA"  # national series for federal policies
            series = descriptive.load_series(cur, ind, geo)
            if len(series) < 2:
                continue
            tr = descriptive.trend(series)
            tr["policy_event"] = released_at.isoformat() if released_at else None
            _upsert(
                cur,
                slug=f"trend:{policy_id}:{ind}:{geo}",
                title=f"Trend: {ind} in {geo}",
                tier="association",
                method="trend",
                policy_id=policy_id,
                indicator_code=ind,
                jurisdiction_code=geo,
                window_spec={"from": tr["from"], "to": tr["to"],
                             "intervention": tr["policy_event"]},
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

        conn.commit()
    return written
