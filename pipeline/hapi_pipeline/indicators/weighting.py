"""HAPI domain weighting schemes + sensitivity analysis (docs/06).

Composite-index weighting is a methodological choice. Following the OECD/JRC
*Handbook on Constructing Composite Indicators* (2008), in the absence of a
robustly estimated statistical model or a formal expert elicitation the weighting
should be (a) transparent and theory-anchored, and (b) subjected to **sensitivity
analysis** showing the headline results don't hinge on it. We therefore define
three named schemes and expose a side-by-side comparison (`hapi weights`):

- ``equal``     — every domain 1.0 (the neutral OECD default).
- ``expert``    — theory/literature-anchored tiers (the v1 default; see below).
- ``empirical`` — data-driven, proportional to each domain's coefficient of
                  variation across jurisdiction × year (domains that discriminate
                  more carry more weight). Computed from the loaded scores;
                  indicative while coverage is NS + Federal, firms up as the
                  jurisdiction set grows.

Expert tiers (rationale, grounded in WHO and HelpAge healthy-ageing frameworks):
  Tier 1 (4) — Health, Care Access: intrinsic-capacity core + the most directly
               policy-actionable health-system pillar (WHO *World Report on Ageing
               and Health* 2015; *Decade of Healthy Ageing* 2021–2030).
  Tier 2 (3) — Financial Security, Independence: material security + functional
               ability (HelpAge *Global AgeWatch Index* income-security domain;
               WHO functional-ability domains — mobility, meeting basic needs).
  Tier 3 (2) — Social Participation, Digital Inclusion: relational engagement and
               enabling environment — vital but more contextual / emerging.

Only weight *ratios* matter: the scoring engine renormalises over the domains
present for each jurisdiction × year, so absolute values are arbitrary.
"""
from __future__ import annotations

import statistics

DOMAINS = [
    "health",
    "independence",
    "social_participation",
    "financial_security",
    "care_access",
    "digital_inclusion",
]

EQUAL: dict[str, float] = {d: 1.0 for d in DOMAINS}

# Theory/literature-anchored tiers (v1 default). See module docstring for sources.
EXPERT: dict[str, float] = {
    "health": 4.0,
    "care_access": 4.0,
    "financial_security": 3.0,
    "independence": 3.0,
    "social_participation": 2.0,
    "digital_inclusion": 2.0,
}


def empirical_cv_weights(domain_values: dict[str, list[float]]) -> dict[str, float]:
    """Data-driven weights ∝ coefficient of variation (stdev/mean) of each domain's
    normalized 0–100 scores across all jurisdiction × year cells, normalized to
    sum 1 over the domains that have ≥2 observations."""
    raw: dict[str, float] = {}
    for d in DOMAINS:
        vals = [v for v in domain_values.get(d, []) if v is not None]
        if len(vals) < 2:
            continue
        mean = statistics.mean(vals)
        raw[d] = (statistics.pstdev(vals) / mean) if mean else 0.0
    total = sum(raw.values()) or 1.0
    return {d: raw[d] / total for d in raw}


def _composite(domain_scores: dict[str, float], weights: dict[str, float]) -> float | None:
    """Weighted mean of present domains, renormalized over the weights of the
    domains actually present (matches the scoring engine)."""
    present = {d: s for d, s in domain_scores.items() if s is not None and d in weights}
    wsum = sum(weights[d] for d in present)
    if not present or wsum == 0:
        return None
    return sum(present[d] * weights[d] for d in present) / wsum


def load_domain_scores(conn) -> dict[str, dict[str, dict[str, float]]]:
    """Return {jurisdiction_code: {period: {domain: score}}} for non-overall
    domain scores at the current method_version."""
    from . import hapi_v1

    out: dict[str, dict[str, dict[str, float]]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """SELECT j.code, h.period::text, h.domain, h.score
                 FROM hapi_score h JOIN jurisdiction j ON j.id = h.jurisdiction_id
                WHERE h.domain <> 'overall' AND h.method_version = %s""",
            (hapi_v1.METHOD_VERSION,),
        )
        for jcode, period, domain, score in cur.fetchall():
            out.setdefault(jcode, {}).setdefault(period, {})[domain] = float(score)
    return out


def sensitivity(conn) -> dict:
    """Compute the three weight vectors + the composite each implies for every
    jurisdiction's latest period — a transparency / robustness report."""
    by_jur = load_domain_scores(conn)

    # Empirical weights from every cell's domain scores.
    domain_values: dict[str, list[float]] = {d: [] for d in DOMAINS}
    for periods in by_jur.values():
        for scores in periods.values():
            for d, s in scores.items():
                domain_values.setdefault(d, []).append(s)
    empirical = empirical_cv_weights(domain_values)

    schemes = {"equal": EQUAL, "expert": EXPERT, "empirical": empirical}

    rows = []
    for jcode, periods in sorted(by_jur.items()):
        if not periods:
            continue
        latest = max(periods)
        scores = periods[latest]
        rows.append({
            "jurisdiction": jcode,
            "period": latest,
            "composite": {name: _composite(scores, w) for name, w in schemes.items()},
        })
    return {"schemes": schemes, "rows": rows}
