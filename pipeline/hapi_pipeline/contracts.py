"""Load the shared enum contracts from packages/contracts/enums.json.

Single source of truth shared with the TypeScript web app (docs/02 §1).
"""
from __future__ import annotations

import json
from functools import lru_cache

from .config import REPO_ROOT

_CONTRACTS = REPO_ROOT / "packages" / "contracts" / "enums.json"


@lru_cache(maxsize=1)
def enums() -> dict[str, list[str]]:
    data = json.loads(_CONTRACTS.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("$")}
