"""Load the starter literature knowledge base (docs/08). Idempotent by slug."""
from __future__ import annotations

import json
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent / "seed_literature.json"


def load_literature(conn, path: Path = SEED_PATH) -> tuple[int, int]:
    items = json.loads(path.read_text(encoding="utf-8"))
    inserted = updated = 0
    with conn.cursor() as cur:
        for it in items:
            cur.execute(
                """INSERT INTO literature (slug, title, authors, year, venue, url, abstract, topics)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (slug) DO UPDATE SET
                       title=EXCLUDED.title, authors=EXCLUDED.authors, year=EXCLUDED.year,
                       venue=EXCLUDED.venue, url=EXCLUDED.url, abstract=EXCLUDED.abstract,
                       topics=EXCLUDED.topics
                   RETURNING (xmax = 0) AS inserted""",
                (it["slug"], it["title"], it.get("authors"), it.get("year"),
                 it.get("venue"), it.get("url"), it.get("abstract"), it.get("topics") or []),
            )
            if cur.fetchone()[0]:
                inserted += 1
            else:
                updated += 1
        conn.commit()
    return inserted, updated
