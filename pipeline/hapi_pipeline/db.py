"""Database access helper for the pipeline.

`psycopg` is imported lazily so that importing this module (e.g. for tests or the
contracts loader) does not require the driver to be installed.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from .config import database_url


@contextmanager
def connect() -> Iterator["object"]:
    """Yield a psycopg connection to the observatory database."""
    import psycopg  # lazy: only needed when actually talking to the DB

    conn = psycopg.connect(database_url())
    try:
        yield conn
    finally:
        conn.close()


def jurisdiction_count() -> int:
    """Return the number of rows in the jurisdiction table (a connectivity check)."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM jurisdiction;")
            (n,) = cur.fetchone()
            return int(n)
