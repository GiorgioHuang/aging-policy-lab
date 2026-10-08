"""Persist, review and report Policy Watch candidates (db: policy_candidate).

Run shape (one source at a time):
    fetch feed -> keyword filter -> drop already-seen URLs -> Claude triage
    -> insert candidates
The DB connection is opened only for the short reads/writes, never held across
a network fetch or a model call (a serverless pooler drops idle connections).

Review never writes the Policy Library directly: accepting a candidate drafts
an entry in seed_policies.json, which a person checks and commits; the existing
`hapi policies seed` step then loads it. The library stays a curated,
version-controlled seed — reproducible, like the rest of the observatory.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..db import connect
from ..policies.loader import SEED_PATH
from . import sources as src
from . import triage


def normalize_url(url: str) -> str:
    """Canonical form for dedup: lowercase host, no fragment or tracking params."""
    p = urllib.parse.urlsplit(url.strip())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_")]
    path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), path, urllib.parse.urlencode(query), "")
    )


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


@dataclass
class SourceStats:
    source: str
    fetched: int = 0
    in_window: int = 0
    matched: int = 0
    new: int = 0
    ai_relevant: int = 0
    auto_rejected: int = 0
    ai_skipped: int = 0
    error: str = ""
    new_titles: list[str] = field(default_factory=list)


def _seen_hashes(hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT url_hash FROM policy_candidate WHERE url_hash = ANY(%s)", (hashes,))
        return {r[0] for r in cur.fetchall()}


def _insert(rows: list[dict]) -> int:
    if not rows:
        return 0
    inserted = 0
    with connect() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute(
                """INSERT INTO policy_candidate
                       (source, url, url_hash, title, summary, published_at,
                        jurisdiction_code, department, matched_terms, keyword_score,
                        ai_relevant, ai_category, ai_confidence, ai_rationale,
                        ai_fields, ai_model, status)
                   VALUES (%(source)s, %(url)s, %(url_hash)s, %(title)s, %(summary)s,
                           %(published_at)s, %(jurisdiction_code)s, %(department)s,
                           %(matched_terms)s, %(keyword_score)s, %(ai_relevant)s,
                           %(ai_category)s, %(ai_confidence)s, %(ai_rationale)s,
                           %(ai_fields)s, %(ai_model)s, %(status)s)
                   ON CONFLICT (url_hash) DO NOTHING""",
                r,
            )
            inserted += cur.rowcount
        conn.commit()
    return inserted


def watch_source(source: src.WatchSource, *, live: bool, since: date,
                 client=None) -> SourceStats:
    """Run one source end to end. Raises on fetch/parse failure."""
    st = SourceStats(source.name)
    items = src.parse(source, src.fetch_raw(source, live=live, since=since))
    st.fetched = len(items)
    items = [i for i in items if src.within_window(i, since)]
    st.in_window = len(items)

    matched = []
    for item in items:
        kw = triage.keyword_match(item)
        if kw.passes:
            matched.append((item, kw))
    st.matched = len(matched)

    # Dedupe within this batch, then against the DB, before paying for triage.
    by_hash: dict[str, tuple] = {}
    for item, kw in matched:
        by_hash.setdefault(url_hash(item.url), (item, kw))
    seen = _seen_hashes(list(by_hash))

    rows = []
    for h, (item, kw) in by_hash.items():
        if h in seen:
            continue
        verdict = None
        if client is not None:
            try:
                verdict = triage.classify(client, item)
            except Exception as exc:  # noqa: BLE001 — one bad call must not drop the batch
                print(f"    ⚠ triage failed for {item.url}: {exc}")
        if verdict is None:
            st.ai_skipped += 1
        elif verdict.relevant:
            st.ai_relevant += 1
        else:
            st.auto_rejected += 1
        rows.append({
            "source": item.source,
            "url": item.url,
            "url_hash": h,
            "title": item.title,
            "summary": item.summary or None,
            "published_at": item.published_at,
            "jurisdiction_code": item.jurisdiction_code or None,
            "department": item.department or None,
            "matched_terms": kw.terms,
            "keyword_score": kw.score,
            "ai_relevant": verdict.relevant if verdict else None,
            "ai_category": verdict.category if verdict else None,
            "ai_confidence": verdict.confidence if verdict else None,
            "ai_rationale": verdict.rationale if verdict else None,
            "ai_fields": json.dumps(verdict.fields) if verdict else None,
            "ai_model": verdict.model if verdict else None,
            "status": "auto_rejected" if verdict and not verdict.relevant else "new",
        })
        if not (verdict and not verdict.relevant):
            st.new_titles.append(item.title)
    st.new = _insert(rows)
    return st


# ── review ───────────────────────────────────────────────────────────────────

_COLS = ("id", "source", "url", "title", "summary", "published_at", "jurisdiction_code",
         "department", "matched_terms", "keyword_score", "ai_relevant", "ai_category",
         "ai_confidence", "ai_rationale", "ai_fields", "ai_model", "status", "seed_slug",
         "first_seen_at")


def _rows(cur) -> list[dict]:
    return [dict(zip(_COLS, r)) for r in cur.fetchall()]


def list_candidates(status: str | None = "new", limit: int = 50) -> list[dict]:
    where, args = "", []
    if status:
        where, args = "WHERE status = %s", [status]
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(_COLS)} FROM policy_candidate {where} "
            "ORDER BY COALESCE(published_at, first_seen_at) DESC LIMIT %s",
            (*args, limit),
        )
        return _rows(cur)


def _slugify(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-")


def draft_seed_entry(c: dict) -> dict:
    """A Policy Library seed entry drafted from a candidate, for human editing."""
    fields = c.get("ai_fields") or {}
    if isinstance(fields, str):
        fields = json.loads(fields)
    released = c["published_at"].date().isoformat() if c.get("published_at") else None
    year = (released or "")[:4]
    jur = c.get("jurisdiction_code") or "CA-FED"
    slug = "-".join(p for p in (jur.lower(), _slugify(c["title"]), year) if p)
    entry = {
        "slug": slug,
        "jurisdiction_code": jur,
        "title": c["title"],
        "department": c.get("department"),
        "released_at": released,
        "source_url": c["url"],
        "full_text": c.get("summary") or c["title"],
        "budget_amount": fields.get("budget_amount_cad"),
        "budget_currency": "CAD",
        "target_population": {"age": "65+", "group": fields.get("target_group") or "older adults"},
        "kpis": [],
        "lifecycle_status": fields.get("lifecycle_status") or "announced",
        "theme": fields.get("theme") or [t for t in (c.get("matched_terms") or [])],
        "indicators": [],
    }
    return {k: v for k, v in entry.items() if v is not None}


def _append_to_seed(entries: list[dict], path: Path) -> list[str]:
    seed = json.loads(path.read_text(encoding="utf-8"))
    have_slugs = {p.get("slug") for p in seed}
    have_titles = {(p.get("jurisdiction_code"), p.get("title")) for p in seed}
    added = []
    for e in entries:
        if e["slug"] in have_slugs or (e["jurisdiction_code"], e["title"]) in have_titles:
            continue
        seed.append(e)
        have_slugs.add(e["slug"])
        added.append(e["slug"])
    if added:
        path.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


@dataclass
class ReviewResult:
    accepted: list[int]
    rejected: list[int]
    seed_added: list[str]
    missing: list[int]


def review(accept: list[int], reject: list[int], *, note: str | None = None,
           write_seed: bool = True, seed_path: Path = SEED_PATH) -> ReviewResult:
    """Accept / reject candidates. Accepting drafts seed entries (write_seed)."""
    ids = list(dict.fromkeys(accept + reject))
    with connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(_COLS)} FROM policy_candidate WHERE id = ANY(%s)",
                    (ids,))
        found = {r["id"]: r for r in _rows(cur)}
        missing = [i for i in ids if i not in found]

        drafts = {i: draft_seed_entry(found[i]) for i in accept if i in found}
        seed_added = _append_to_seed(list(drafts.values()), seed_path) if write_seed else []

        now = datetime.now(timezone.utc)
        for i, entry in drafts.items():
            cur.execute(
                "UPDATE policy_candidate SET status='accepted', seed_slug=%s, "
                "review_note=%s, reviewed_at=%s WHERE id=%s",
                (entry["slug"], note, now, i),
            )
        for i in reject:
            if i in found and i not in drafts:
                cur.execute(
                    "UPDATE policy_candidate SET status='rejected', review_note=%s, "
                    "reviewed_at=%s WHERE id=%s",
                    (note, now, i),
                )
        conn.commit()
    return ReviewResult(
        accepted=[i for i in accept if i in found],
        rejected=[i for i in reject if i in found and i not in drafts],
        seed_added=seed_added,
        missing=missing,
    )


# ── digest ───────────────────────────────────────────────────────────────────

JURISDICTION_LABELS = {"CA-FED": "Federal", "CA-NS": "Nova Scotia"}


def _fmt_candidate(c: dict) -> list[str]:
    when = c["published_at"].date().isoformat() if c.get("published_at") else "undated"
    meta = [c.get("department") or c["source"], when]
    if c.get("ai_category"):
        conf = f" {c['ai_confidence']:.2f}" if c.get("ai_confidence") is not None else ""
        meta.append(f"`{c['ai_category']}`{conf}")
    title = c["title"].replace("[", "(").replace("]", ")")
    lines = [f"- **#{c['id']}** [{title}]({c['url']}) — {' · '.join(meta)}"]
    if c.get("ai_rationale"):
        lines.append(f"  > {c['ai_rationale']}")
    if c.get("matched_terms"):
        lines.append(f"  <sub>matched: {', '.join(c['matched_terms'])}</sub>")
    return lines


def render_digest(new: list[dict], auto_rejected: list[dict], backlog: int,
                  days: int, today: date | None = None) -> str:
    """Markdown digest (GitHub issue body). Pure: takes rows, returns text."""
    today = today or datetime.now(timezone.utc).date()
    out = [
        f"## Policy Watch — {today.isoformat()}",
        "",
        f"**{len(new)}** new aging-policy candidate(s) in the last {days} day(s)"
        + (f"; **{backlog}** older candidate(s) still awaiting review." if backlog else "."),
        "",
    ]
    by_jur: dict[str, list[dict]] = {}
    for c in new:
        by_jur.setdefault(c.get("jurisdiction_code") or "other", []).append(c)
    for jur in sorted(by_jur, key=lambda j: (j != "CA-FED", j)):
        out.append(f"### {JURISDICTION_LABELS.get(jur, jur)}")
        out.append("")
        for c in by_jur[jur]:
            out.extend(_fmt_candidate(c))
        out.append("")
    if auto_rejected:
        out.append("<details><summary>"
                   f"{len(auto_rejected)} item(s) matched keywords but Claude judged them "
                   "not aging policy — skim for false negatives</summary>")
        out.append("")
        for c in auto_rejected:
            out.extend(_fmt_candidate(c))
        out.append("")
        out.append("</details>")
        out.append("")
    out += [
        "---",
        "**Review:** Actions → *Policy Watch review* → Run workflow, with "
        "`accept` / `reject` set to candidate ids (e.g. `12,15`). Accepting drafts an "
        "entry in `seed_policies.json` and opens a PR to check before it enters the "
        "Policy Library. Locally: `hapi watch review --accept 12,15 --reject 13`.",
    ]
    return "\n".join(out) + "\n"


def digest(days: int = 7) -> tuple[str, int]:
    """Build the digest for candidates first seen in the last `days` days.

    Returns (markdown, number of new candidates needing review).
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    order = "ORDER BY COALESCE(published_at, first_seen_at) DESC"
    with connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(_COLS)} FROM policy_candidate "
                    f"WHERE status='new' AND first_seen_at >= %s {order}", (since,))
        new = _rows(cur)
        cur.execute(f"SELECT {', '.join(_COLS)} FROM policy_candidate "
                    f"WHERE status='auto_rejected' AND first_seen_at >= %s {order}", (since,))
        auto_rejected = _rows(cur)
        cur.execute("SELECT count(*) FROM policy_candidate "
                    "WHERE status='new' AND first_seen_at < %s", (since,))
        (backlog,) = cur.fetchone()
    return render_digest(new, auto_rejected, backlog, days), len(new)
