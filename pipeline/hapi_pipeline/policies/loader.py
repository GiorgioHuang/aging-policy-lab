"""Load the curated policy seed into the Policy Library (docs/04).

Idempotent: policies are matched on (jurisdiction, title). Each load ensures an
initial PolicyVersion (v1) snapshot and links the policy to any referenced
indicators that already exist (policy_indicator — docs/04 §6).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent / "seed_policies.json"


@dataclass
class LoadResult:
    inserted: int
    updated: int
    links: int
    missing_indicators: list[str]


def _jurisdiction_ids(cur) -> dict[str, int]:
    cur.execute("SELECT code, id FROM jurisdiction WHERE code IS NOT NULL")
    return {c: i for c, i in cur.fetchall()}


def _indicator_ids(cur) -> dict[str, int]:
    cur.execute("SELECT code, id FROM indicator")
    return {c: i for c, i in cur.fetchall()}


def load_policies(conn, path: Path = SEED_PATH) -> LoadResult:
    policies = json.loads(path.read_text(encoding="utf-8"))
    res = LoadResult(0, 0, 0, [])

    with conn.cursor() as cur:
        jur = _jurisdiction_ids(cur)
        inds = _indicator_ids(cur)

        for p in policies:
            jid = jur.get(p["jurisdiction_code"])
            if jid is None:
                continue

            cur.execute(
                "SELECT id FROM policy WHERE jurisdiction_id = %s AND title = %s",
                (jid, p["title"]),
            )
            row = cur.fetchone()
            fields = (
                p.get("department"),
                p.get("released_at"),
                p.get("full_text"),
                p.get("source_url"),
                p.get("budget_amount"),
                p.get("budget_currency", "CAD"),
                json.dumps(p.get("target_population")) if p.get("target_population") else None,
                json.dumps(p.get("kpis")) if p.get("kpis") else None,
                p.get("lifecycle_status"),
                p.get("theme") or [],
            )

            if row:
                policy_id = row[0]
                cur.execute(
                    """UPDATE policy SET department=%s, released_at=%s, full_text=%s,
                           source_url=%s, budget_amount=%s, budget_currency=%s,
                           target_population=%s, kpis=%s, lifecycle_status=%s, theme=%s
                       WHERE id=%s""",
                    (*fields, policy_id),
                )
                res.updated += 1
            else:
                cur.execute(
                    """INSERT INTO policy (jurisdiction_id, title, department, released_at,
                           full_text, source_url, budget_amount, budget_currency,
                           target_population, kpis, lifecycle_status, theme)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (jid, p["title"], *fields),
                )
                policy_id = cur.fetchone()[0]
                res.inserted += 1

            # Ensure an initial version snapshot exists.
            cur.execute(
                "SELECT 1 FROM policy_version WHERE policy_id=%s AND version_no=1",
                (policy_id,),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO policy_version (policy_id, version_no, change_summary, snapshot) "
                    "VALUES (%s, 1, %s, %s)",
                    (policy_id, "Seed import", json.dumps(p)),
                )

            # Link to indicators that exist (skip + report unknown ones).
            for code in p.get("indicators", []):
                iid = inds.get(code)
                if iid is None:
                    if code not in res.missing_indicators:
                        res.missing_indicators.append(code)
                    continue
                cur.execute(
                    "INSERT INTO policy_indicator (policy_id, indicator_id) "
                    "VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (policy_id, iid),
                )
                if cur.rowcount:
                    res.links += 1

        conn.commit()
    return res
