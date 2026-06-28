"""Interrupted Time Series (ITS) — a Tier-2 quasi-experimental design (docs/07 §2).

Segmented regression: model the outcome as a pre-intervention level + trend, plus
a post-intervention level change and slope change. Standard errors use a
Newey-West (HAC) covariance to account for autocorrelation. The result is tagged
`causal` ONLY together with its named assumptions and limitations — never upgraded
silently from an association (docs/07 §3).
"""
from __future__ import annotations

from datetime import date

MIN_PER_SEGMENT = 3  # below this, do not report coefficients

ASSUMPTIONS = (
    "ITS assumes: (1) the pre-intervention trend would have continued absent the "
    "intervention (counterfactual); (2) no other event coincides with the "
    "intervention date; (3) the chosen functional form (linear segments) is "
    "correct; (4) autocorrelation is handled (Newey-West HAC SEs used here)."
)


def interrupted_time_series(
    series: list[tuple[date, float]], intervention: date
) -> dict:
    """Run segmented regression around `intervention`. Returns a result dict that
    always includes a `status`: 'ok' with coefficients, or 'insufficient_data'."""
    pre = [(d, v) for d, v in series if d < intervention]
    post = [(d, v) for d, v in series if d >= intervention]
    n_pre, n_post = len(pre), len(post)

    base = {
        "intervention": intervention.isoformat(),
        "n_pre": n_pre,
        "n_post": n_post,
    }

    if n_pre < MIN_PER_SEGMENT or n_post < MIN_PER_SEGMENT:
        return {
            **base,
            "status": "insufficient_data",
            "note": (
                f"Need >= {MIN_PER_SEGMENT} points each side (have {n_pre} pre / "
                f"{n_post} post). Method demonstrated; coefficients not estimated."
            ),
        }

    try:
        import numpy as np
        import statsmodels.api as sm
    except ImportError:
        return {**base, "status": "deps_missing",
                "note": "numpy/statsmodels not installed"}

    n = len(series)
    t0 = n_pre  # index of first post point
    time = np.arange(n, dtype=float)
    level = np.array([1.0 if i >= t0 else 0.0 for i in range(n)])
    time_after = np.array([float(i - t0 + 1) if i >= t0 else 0.0 for i in range(n)])
    y = np.array([v for _, v in series], dtype=float)

    X = sm.add_constant(np.column_stack([time, level, time_after]))
    model = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    names = ["intercept", "pre_trend", "level_change", "slope_change"]
    ci = model.conf_int()

    def term(i: int) -> dict:
        return {
            "coef": round(float(model.params[i]), 3),
            "se": round(float(model.bse[i]), 3),
            "ci_low": round(float(ci[i][0]), 3),
            "ci_high": round(float(ci[i][1]), 3),
            "p": round(float(model.pvalues[i]), 4),
        }

    return {
        **base,
        "status": "ok",
        "intercept": term(0),      # pre-intervention level at t=0 (for plotting the fit)
        "pre_trend": term(1),
        "level_change": term(2),   # immediate change at the intervention
        "slope_change": term(3),   # change in trend after the intervention
        "r_squared": round(float(model.rsquared), 3),
        "terms": names,
    }
