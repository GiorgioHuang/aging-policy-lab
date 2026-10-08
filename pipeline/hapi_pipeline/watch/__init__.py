"""Policy Watch: continuous discovery of new aging-policy items (docs/04 §9).

Watchers poll official feeds, a keyword pass keeps aging-relevant items, Claude
optionally triages them, and survivors become `policy_candidate` rows awaiting
human review. Accepted candidates are drafted into `seed_policies.json`, so the
Policy Library itself stays a curated, version-controlled seed.
"""
