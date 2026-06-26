"""Healthy Aging Policy Observatory — data pipeline.

The Python data/analysis core (docs/02 §1). Subpackages:

    ingest/      one connector per data source (docs/10)
    transform/   cleaning, normalization, lineage
    indicators/  HAPI computation (docs/06)
    analytics/   association + quasi-experimental methods (docs/07)
    ai/          Claude API orchestration (docs/08)

Phase 1 ships the package skeleton plus a working DB connection helper; the
connectors and analytics arrive in later phases (see docs/11).
"""

__version__ = "0.1.0"
