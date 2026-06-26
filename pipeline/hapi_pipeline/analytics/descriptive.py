"""Tier-1 descriptive analytics (docs/07 §2) — association only.

Trends, percent change, and slope over an indicator series. These are useful for
exploration and ALWAYS carry the `association` tier — they cannot establish
causation (that needs the quasi-experimental designs in its.py).
"""
from __future__ import annotations

from datetime import date


def load_series(cur, indicator_code: str, jurisdiction_code: str) -> list[tuple[date, float]]:
    """Return ordered (period_start, value) using the latest dataset version per period."""
    cur.execute(
        """
        SELECT lower(o.period) AS ps, o.value
          FROM observation o
          JOIN indicator i    ON i.id = o.indicator_id
          JOIN jurisdiction j ON j.id = o.jurisdiction_id
          JOIN (
              SELECT indicator_id, jurisdiction_id, period, max(dataset_version_id) AS mdv
                FROM observation GROUP BY indicator_id, jurisdiction_id, period
          ) latest
            ON latest.indicator_id = o.indicator_id
           AND latest.jurisdiction_id = o.jurisdiction_id
           AND latest.period = o.period
           AND latest.mdv = o.dataset_version_id
         WHERE i.code = %s AND j.code = %s AND o.value IS NOT NULL
         ORDER BY ps
        """,
        (indicator_code, jurisdiction_code),
    )
    return [(ps, float(v)) for ps, v in cur.fetchall()]


def _ols_slope(values: list[float]) -> float:
    """Least-squares slope of value on its 0-based step index."""
    n = len(values)
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((xs[i] - mx) * (values[i] - my) for i in range(n)) / denom


def trend(series: list[tuple[date, float]]) -> dict:
    """Summarize a series: start/end, percent change, slope per step, direction."""
    values = [v for _, v in series]
    start, end = values[0], values[-1]
    pct = None if start == 0 else (end - start) / start * 100.0
    slope = _ols_slope(values)
    direction = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
    return {
        "from": series[0][0].isoformat(),
        "to": series[-1][0].isoformat(),
        "n": len(values),
        "start_value": round(start, 3),
        "end_value": round(end, 3),
        "pct_change": None if pct is None else round(pct, 1),
        "slope_per_step": round(slope, 3),
        "direction": direction,
    }
