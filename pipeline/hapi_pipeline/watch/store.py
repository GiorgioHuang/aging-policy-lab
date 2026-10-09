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
    """Canonical form for dedup: lowercase host, no tracking params.

    Fragments are kept: Gazette Part I lists several notices on one page, told
    apart only by their #anchor.
    """
    p = urllib.parse.urlsplit(url.strip())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_")]
    path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), path, urllib.parse.urlencode(query), p.fragment)
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
    updated: int = 0
    error: str = ""
    new_titles: list[str] = field(default_factory=list)
    updated_titles: list[str] = field(default_factory=list)


def _seen_hashes(hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT url_hash FROM policy_candidate WHERE url_hash = ANY(%s)", (hashes,))
        return {r[0] for r in cur.fetchall()}


def _norm(text: str | None) -> str:
    return " ".join((text or "").split())


def _record_updates(items: dict[str, src.FeedItem]) -> list[str]:
    """For followed candidates (awaiting review / accepted) among `items`
    (url_hash → item), record a progress event where the stated stage changed,
    and move the candidate's summary / published_at to it. Returns the titles."""
    if not items:
        return []
    changed = []
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, url_hash, summary FROM policy_candidate "
            "WHERE url_hash = ANY(%s) AND status IN ('new', 'accepted')",
            (list(items),),
        )
        for cid, h, old in cur.fetchall():
            item = items[h]
            if not item.summary or _norm(item.summary) == _norm(old):
                continue
            cur.execute(
                "INSERT INTO policy_candidate_event (candidate_id, published_at, summary, previous) "
                "VALUES (%s, %s, %s, %s)",
                (cid, item.published_at, item.summary, old),
            )
            cur.execute(
                "UPDATE policy_candidate SET summary = %s, "
                "published_at = COALESCE(%s, published_at), last_changed_at = now() "
                "WHERE id = %s",
                (item.summary, item.published_at, cid),
            )
            changed.append(item.title)
        conn.commit()
    return changed


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
    st.fetched, items = src.collect(source, live=live, since=since)
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
    if source.track_updates:
        st.updated_titles = _record_updates(
            {h: item for h, (item, _kw) in by_hash.items() if h in seen})
        st.updated = len(st.updated_titles)

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


def triage_existing(client, limit: int = 50) -> list[tuple[int, str, object]]:
    """Run Claude triage on followed candidates stored without it (e.g. found
    before ANTHROPIC_API_KEY was set). Annotates the ai_* fields only — never
    changes status, so a reviewer's decision to keep following an item stands.

    Returns [(id, title, AIVerdict | None | Exception)].
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(_COLS)} FROM policy_candidate "
            "WHERE ai_relevant IS NULL AND status IN ('new', 'accepted') ORDER BY id LIMIT %s",
            (limit,),
        )
        rows = _rows(cur)
    out = []
    for c in rows:
        item = src.FeedItem(
            source=c["source"], url=c["url"], title=c["title"], summary=c["summary"] or "",
            published_at=c["published_at"], jurisdiction_code=c["jurisdiction_code"] or "",
            department=c["department"] or "",
        )
        try:
            verdict = triage.classify(client, item)  # network: no DB connection held
        except Exception as exc:  # noqa: BLE001 — report and carry on
            out.append((c["id"], c["title"], exc))
            continue
        if verdict is not None:
            with connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE policy_candidate SET ai_relevant=%s, ai_category=%s, ai_confidence=%s, "
                    "ai_rationale=%s, ai_fields=%s, ai_model=%s WHERE id=%s",
                    (verdict.relevant, verdict.category, verdict.confidence, verdict.rationale,
                     json.dumps(verdict.fields), verdict.model, c["id"]),
                )
                conn.commit()
        out.append((c["id"], c["title"], verdict))
    return out


# ── review ───────────────────────────────────────────────────────────────────

_COLS = ("id", "source", "url", "title", "summary", "published_at", "jurisdiction_code",
         "department", "matched_terms", "keyword_score", "ai_relevant", "ai_category",
         "ai_confidence", "ai_rationale", "ai_fields", "ai_model", "status", "seed_slug",
         "first_seen_at", "last_changed_at")


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
    if len(s) <= limit:
        return s
    cut = s[:limit + 1]  # keep whole words: cut at the last hyphen in range
    return cut[:cut.rfind("-")] if "-" in cut else s[:limit]


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
    # accepted candidates that name an entry already in the library:
    # candidate id -> [(slug, title)]; no new entry is drafted for these
    existing: dict[int, list[tuple[str, str]]] = field(default_factory=dict)


def _words(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def existing_matches(c: dict, seed: list[dict]) -> list[tuple[str, str]]:
    """Library entries (same jurisdiction) whose title appears in the candidate's
    title or summary — e.g. a release announcing a new round of a program the
    library already holds. Titles under three words are too generic to match."""
    text = f" {_words(c.get('title', ''))} {_words(c.get('summary', ''))} "
    hits = []
    for e in seed:
        if e.get("jurisdiction_code") != c.get("jurisdiction_code"):
            continue
        title = _words(re.sub(r"\([^)]*\)", " ", e.get("title", "")))  # drop "(PHAC)" etc.
        if len(title.split()) >= 3 and f" {title} " in text:
            hits.append((e["slug"], e["title"]))
    return hits


def _page_text(url: str) -> str:
    """Body text of an item's web page, for matching only (not stored). Feed
    summaries are often a one-sentence teaser that never names the program;
    the release body usually does. Empty on any failure, and for PDFs."""
    if urllib.parse.urlsplit(url).path.lower().endswith(".pdf"):
        return ""
    try:
        return " ".join(src.page_meta(src.http_get(url, retries=1)).paragraphs)
    except Exception:  # noqa: BLE001 — matching falls back to the stored text
        return ""


def review(accept: list[int], reject: list[int], *, note: str | None = None,
           write_seed: bool = True, seed_path: Path = SEED_PATH,
           fetch_pages: bool = True) -> ReviewResult:
    """Accept / reject candidates. Accepting drafts seed entries (write_seed)."""
    ids = list(dict.fromkeys(accept + reject))
    with connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(_COLS)} FROM policy_candidate WHERE id = ANY(%s)",
                    (ids,))
        found = {r["id"]: r for r in _rows(cur)}
        missing = [i for i in ids if i not in found]

        # A candidate that names an existing library entry is most likely an
        # update to it (a new funding round, an amendment): record the link and
        # leave the edit to the reviewer instead of drafting a duplicate.
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        def with_page(c: dict) -> dict:
            if not fetch_pages:
                return c
            return {**c, "summary": f"{c.get('summary') or ''} {_page_text(c['url'])}"}

        existing = {i: m for i in accept if i in found
                    for m in [existing_matches(with_page(found[i]), seed)] if m}
        drafts = {i: draft_seed_entry(found[i]) for i in accept
                  if i in found and i not in existing}
        seed_added = _append_to_seed(list(drafts.values()), seed_path) if write_seed else []

        now = datetime.now(timezone.utc)
        slugs = {i: e["slug"] for i, e in drafts.items()}
        slugs.update({i: m[0][0] for i, m in existing.items()})
        for i, slug in slugs.items():
            cur.execute(
                "UPDATE policy_candidate SET status='accepted', seed_slug=%s, "
                "review_note=%s, reviewed_at=%s WHERE id=%s",
                (slug, note, now, i),
            )
        for i in reject:
            if i in found and i not in slugs:
                cur.execute(
                    "UPDATE policy_candidate SET status='rejected', review_note=%s, "
                    "reviewed_at=%s WHERE id=%s",
                    (note, now, i),
                )
        conn.commit()
    return ReviewResult(
        accepted=[i for i in accept if i in found],
        rejected=[i for i in reject if i in found and i not in slugs],
        seed_added=seed_added,
        missing=missing,
        existing=existing,
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
    if c.get("summary") and not c["source"].startswith("gazette_"):
        # For bills this is the current stage ("Royal Assent - …"), which is
        # what decides whether to accept; for news, the opening of the release.
        summary = " ".join(c["summary"].split())
        lines.append(f"  > {summary[:280]}{'…' if len(summary) > 280 else ''}")
    if c.get("matched_terms"):
        lines.append(f"  <sub>matched: {', '.join(c['matched_terms'])}</sub>")
    return lines


def render_digest(new: list[dict], auto_rejected: list[dict], backlog: int,
                  days: int, today: date | None = None,
                  progressed: list[dict] | None = None) -> str:
    """Markdown digest (GitHub issue body). Pure: takes rows, returns text.

    `progressed`: followed candidates whose stated stage changed in the window
    (e.g. a bill reaching royal assent), shown with their current stage.
    """
    progressed = progressed or []
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
    if progressed:
        out.append("### Progress on followed items")
        out.append("")
        for c in progressed:
            title = c["title"].replace("[", "(").replace("]", ")")
            state = "accepted" if c.get("status") == "accepted" else "awaiting review"
            out.append(f"- **#{c['id']}** [{title}]({c['url']}) — {state}")
            if c.get("summary"):
                out.append(f"  > now: {c['summary']}")
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
    """Build the digest for the last `days` days: candidates first seen, and
    followed candidates that progressed (excluding ones first seen in the window).

    Returns (markdown, number of items worth reporting: new + progressed).
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
        cur.execute(f"SELECT {', '.join(_COLS)} FROM policy_candidate "
                    "WHERE status IN ('new', 'accepted') AND last_changed_at >= %s "
                    "AND first_seen_at < %s ORDER BY last_changed_at DESC", (since, since))
        progressed = _rows(cur)
    text = render_digest(new, auto_rejected, backlog, days, progressed=progressed)
    return text, len(new) + len(progressed)
