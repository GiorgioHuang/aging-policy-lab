"""Configuration: resolve the database URL from the environment / repo .env."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load the repo-root .env if python-dotenv is available (best-effort)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def database_url() -> str:
    """Return DATABASE_URL, or build it from POSTGRES_* parts as a fallback."""
    _load_dotenv()
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("POSTGRES_USER", "hapi")
    pwd = os.getenv("POSTGRES_PASSWORD", "hapi_dev_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "hapi")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
