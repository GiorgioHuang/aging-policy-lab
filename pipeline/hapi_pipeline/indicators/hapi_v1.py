"""HAPI v1 methodology (docs/06).

Defines the indicator set, per-capita rules, normalization reference ranges, and
weights for the first, defensible Healthy Aging Policy Index. Versioned as 'v1':
changing the method bumps METHOD_VERSION so past HapiScores stay interpretable.

v1 scope: all six HAPI domains are now data-backed — Health (StatCan life
expectancy at 65), Independence (CCHS functional health), Social Participation
(CCHS community belonging), Financial Security (StatCan seniors' low-income
rate), Care Access (CCHS regular healthcare provider + the live NS long-term-care
waitlist), and Digital Inclusion (StatCan seniors' internet use). The composite
blends whichever of these has data for a given
jurisdiction × year, so `overall` is a genuine six-domain index. Indicators are
added per domain without changing the model or this method's outputs.

Weighting (v1). The composite is a weighted mean across available domains, using
the **theory/literature-anchored "expert" tiers** defined in `weighting.py`
(Health + Care Access tier 1; Financial Security + Independence tier 2; Social
Participation + Digital Inclusion tier 3 — grounded in the WHO healthy-ageing and
HelpAge AgeWatch frameworks). The engine renormalizes by the sum of the domains
present, so a jurisdiction × year missing a domain is scored fairly on the rest.
Within a domain, indicators are averaged by their per-indicator `weight` (e.g.
Independence averages the 65–74 and 75+ functional-health bands).

The weighting is auditable and sensitivity-tested: `hapi weights` reports the
composite under equal / expert / empirical (data-driven) schemes side by side
(OECD/JRC Handbook guidance). A future method version can adopt a re-estimated
weighting and bump METHOD_VERSION.
"""
from __future__ import annotations

from .weighting import EXPERT as DOMAIN_WEIGHTS  # noqa: F401  (the active v1 scheme)

METHOD_VERSION = "v1"

# Each scoring indicator: how to derive a 0-100 normalized value.
# Reference ranges (normalization min/max) are documented method choices for v1;
# min-max clamps to [0,100] and `direction` aligns "higher score = better outcome".
INDICATORS: list[dict] = [
    {
        "code": "health.life_expectancy_65",
        "domain": "health",
        "direction": "higher_is_better",
        # already in years; no per-capita step. Range brackets the observed CA+NS
        # span (~19.5-21 yrs of remaining life at 65).
        "normalization": {"method": "min_max", "min": 16.0, "max": 24.0},
        "weight": 1.0,
    },
    {
        "code": "independence.functional_health_65_74",
        "domain": "independence",
        "direction": "higher_is_better",
        # % of 65-74 with very-good-to-perfect functional health (HUI-3). Range
        # brackets the observed senior span (lower than the all-ages rate).
        "normalization": {"method": "min_max", "min": 20.0, "max": 65.0},
        "weight": 1.0,
    },
    {
        "code": "independence.functional_health_75plus",
        "domain": "independence",
        "direction": "higher_is_better",
        # % of 75+ with very-good-to-perfect functional health (HUI-3). Lower than
        # the 65-74 band, so a lower reference range. Averaged with 65-74 within
        # the Independence domain.
        "normalization": {"method": "min_max", "min": 15.0, "max": 55.0},
        "weight": 1.0,
    },
    {
        # CIHI caregiver distress — sustainability of aging in place (manual source).
        "code": "independence.caregiver_distress",
        "domain": "independence",
        "direction": "lower_is_better",  # less caregiver distress scores higher
        # already a rate (% of long-stay home-care clients with caregiver distress)
        "normalization": {"method": "min_max", "min": 15.0, "max": 50.0},
        "weight": 1.0,
    },
    {
        "code": "social_participation.community_belonging_65plus",
        "domain": "social_participation",
        "direction": "higher_is_better",
        # already a rate (% of 65+ reporting strong community belonging)
        "normalization": {"method": "min_max", "min": 50.0, "max": 90.0},
        "weight": 1.0,
    },
    {
        # Live, API-accessible Care-Access backbone (CCHS 13-10-0096).
        "code": "care_access.regular_provider_65plus",
        "domain": "care_access",
        "direction": "higher_is_better",
        # already a rate (% of 65+ with a regular healthcare provider); high band.
        "normalization": {"method": "min_max", "min": 80.0, "max": 100.0},
        "weight": 1.0,
    },
    {
        # Real, live NS continuing-care access signal (Socrata). Replaces the CIHI
        # home-care count, which has no Nova Scotia data. NS-only (no federal row).
        "code": "care_access.ltc_waitlist_ns",
        "domain": "care_access",
        "direction": "lower_is_better",  # fewer people waiting = better access
        # count -> people waiting per 1,000 population 65+ (StatCan denominator).
        # Headline = total_waiting_for_initial_placement (community + hospital).
        "per_capita": {
            "denominator": "demography.population_65plus",
            "scale": 1000,
            "unit": "waiting per 1,000 pop 65+",
        },
        # Range brackets the observed NS series (~1,600-2,600 people over ~205k
        # pop 65+ ≈ 8-13 per 1,000); inspect-confirmed 2026-06 (c39g-gsdd).
        "normalization": {"method": "min_max", "min": 2.0, "max": 16.0},
        "weight": 1.0,
    },
    {
        # Supply/capacity view of Care Access: nursing & residential-care workforce
        # (NAICS 623, SEPH) per 1,000 seniors. CA + NS, annual.
        "code": "care_access.ltc_workforce_per_1k_65plus",
        "domain": "care_access",
        "direction": "higher_is_better",  # more care workers per senior = better
        "per_capita": {
            "denominator": "demography.population_65plus",
            "scale": 1000,
            "unit": "workers per 1,000 pop 65+",
        },
        # Range set from the live 2001-2025 series (Table 14-10-0202): NAICS-623
        # workers per 1,000 pop 65+ run ~60 (CA) to ~87 (NS); 40..100 brackets it
        # with margin and no floor/ceiling.
        "normalization": {"method": "min_max", "min": 40.0, "max": 100.0},
        "weight": 1.0,
    },
    {
        "code": "financial_security.low_income_rate_65plus",
        "domain": "financial_security",
        "direction": "lower_is_better",  # a lower senior poverty rate scores higher
        # already a rate (% of persons 65+); no per-capita step. Range brackets the
        # observed CA+NS span (CA ~14-17%, NS up to ~25%) so neither floors/ceils.
        "normalization": {"method": "min_max", "min": 2.0, "max": 30.0},
        "weight": 1.0,
    },
    {
        "code": "digital_inclusion.internet_use_65plus",
        "domain": "digital_inclusion",
        "direction": "higher_is_better",
        # already a rate (% of persons 65+ who used the Internet)
        "normalization": {"method": "min_max", "min": 50.0, "max": 95.0},
        "weight": 1.0,
    },
]
