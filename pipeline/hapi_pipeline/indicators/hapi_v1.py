"""HAPI v1 methodology (docs/06).

Defines the indicator set, per-capita rules, normalization reference ranges, and
weights for the first, defensible Healthy Aging Policy Index. Versioned as 'v1':
changing the method bumps METHOD_VERSION so past HapiScores stay interpretable.

v1 scope: three data-backed domains — Care Access (CIHI home care), Financial
Security (StatCan seniors' low-income rate), and Digital Inclusion (StatCan
seniors' internet use). The composite blends whichever of these has data for a
given jurisdiction × year, so `overall` is a genuine multi-domain index, not a
restatement of one domain. Remaining domains join as their connectors land,
without changing the model or this method's outputs.
"""
from __future__ import annotations

METHOD_VERSION = "v1"

# Domain weights for the composite HAPI (equal across available domains in v1).
DOMAIN_WEIGHTS: dict[str, float] = {
    "care_access": 1.0,
    "financial_security": 1.0,
    "digital_inclusion": 1.0,
}

# Each scoring indicator: how to derive a 0-100 normalized value.
# Reference ranges (normalization min/max) are documented method choices for v1;
# min-max clamps to [0,100] and `direction` aligns "higher score = better outcome".
INDICATORS: list[dict] = [
    {
        "code": "care_access.home_care_clients_65plus",
        "domain": "care_access",
        "direction": "higher_is_better",
        # raw count -> rate per 1,000 population 65+ (uses the StatCan denominator)
        "per_capita": {
            "denominator": "demography.population_65plus",
            "scale": 1000,
            "unit": "clients per 1,000 pop 65+",
        },
        # min-max against a documented reference range, then clamp to [0,100]
        "normalization": {"method": "min_max", "min": 100.0, "max": 250.0},
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
