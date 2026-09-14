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

    # TCP keepalives keep the socket healthy across the short idle windows that
    # remain during a multi-source run. Serverless poolers (e.g. Neon) drop
    # connections that look idle; without keepalives a connection held open
    # while a connector stalls on a slow upstream fetch gets closed underneath
    # us, surfacing later as "SSL connection has been closed unexpectedly" /
    # "the connection is closed" on the next write. See loader.ingest(), which
    # also now opens its DB connection per-write to keep those windows tiny.
    conn = psycopg.connect(
        database_url(),
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
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
