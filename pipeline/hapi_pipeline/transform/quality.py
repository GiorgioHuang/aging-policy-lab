"""Data quality checks (docs/05 §5).

Runs before load. Records that fail a hard check are quarantined (dropped from
the load) and reported; soft issues set a `quality_flag` instead. Nothing is
silently dropped — every quarantined record produces an issue string.
"""
from __future__ import annotations

import math
from dataclasses import replace

from ..ingest.base import IndicatorSpec, ObservationRecord


def _is_percentage(unit: str) -> bool:
    u = unit.lower()
    return "%" in unit or "percent" in u or u.endswith("rate")


def run_quality_checks(
    indicators: list[IndicatorSpec],
    records: list[ObservationRecord],
) -> tuple[list[ObservationRecord], list[str]]:
    """Return (records_to_load, issues)."""
    issues: list[str] = []
    by_code = {i.code: i for i in indicators}

    if not records:
        issues.append("row count: connector produced 0 records")
        return [], issues

    kept: list[ObservationRecord] = []
    for r in records:
        ind = by_code.get(r.indicator_code)
        if ind is None:
            issues.append(f"unknown indicator '{r.indicator_code}' — quarantined")
            continue

        # Missing / suppressed: keep the row (NULL value) but flag it.
        if r.value is None or (isinstance(r.value, float) and math.isnan(r.value)):
            kept.append(replace(r, value=None, quality_flag="suppressed"))
            continue

        # Range: counts and most rates cannot be negative.
        if r.value < 0:
            issues.append(
                f"range: {r.indicator_code} {r.jurisdiction_code} "
                f"{r.period_start} = {r.value} < 0 — quarantined"
            )
            continue

        # Range: percentages must be 0–100.
        if _is_percentage(ind.unit) and r.value > 100:
            issues.append(
                f"range: {r.indicator_code} {r.jurisdiction_code} "
                f"{r.period_start} = {r.value} > 100% — quarantined"
            )
            continue

        kept.append(r)

    return kept, issues
