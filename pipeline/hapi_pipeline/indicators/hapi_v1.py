"""HAPI v1 methodology (docs/06).

Defines the indicator set, per-capita rules, normalization reference ranges, and
weights for the first, defensible Healthy Aging Policy Index. Versioned as 'v1':
changing the method bumps METHOD_VERSION so past HapiScores stay interpretable.

v1 scope: the Care Access domain — the data-rich domain in the seed (docs/06 §6).
The framework computes domain + composite scores; other domains join as their
connectors land, without changing the model or this method's outputs.
"""
from __future__ import annotations

METHOD_VERSION = "v1"

# Domain weights for the composite HAPI (equal within available domains in v1).
DOMAIN_WEIGHTS: dict[str, float] = {"care_access": 1.0}

# Each scoring indicator: how to derive a 0-100 normalized value.
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
]
