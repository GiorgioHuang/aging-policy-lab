"""AI-assisted policy summarization via the Claude API (docs/04 §4).

Generates a plain-language `ai_summary` for policies that lack one, and records a
new PolicyVersion so re-summarization is versioned, never a silent overwrite.
Gracefully no-ops when ANTHROPIC_API_KEY is unset (the seed already ships
human-written summaries, so this is an enrichment step).
"""
from __future__ import annotations

import json
import os

# Default to the most capable model; override with HAPI_SUMMARY_MODEL (e.g. a
# cheaper tier like claude-haiku-4-5 for high-volume summarization).
DEFAULT_MODEL = os.getenv("HAPI_SUMMARY_MODEL", "claude-opus-4-8")

SYSTEM = (
    "You summarize Canadian aging-policy documents for a research database. "
    "Write a neutral, 2-4 sentence plain-language summary: what the policy does, "
    "who it targets, and any budget or KPI it states. No preamble, no markdown."
)


def summarize_text(client, model: str, title: str, full_text: str) -> str | None:
    """Return an AI summary for one policy, or None on refusal."""
    resp = client.messages.create(
        model=model,
        max_tokens=400,
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Title: {title}\n\nPolicy text:\n{full_text}",
            }
        ],
    )
    if resp.stop_reason == "refusal":
        return None
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def summarize_policies(conn, *, model: str | None = None, limit: int | None = None) -> int:
    """Summarize policies whose ai_summary IS NULL. Returns the count updated."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("• summarize: ANTHROPIC_API_KEY not set — skipping (seed summaries kept)")
        return 0
    try:
        from anthropic import Anthropic
    except ImportError:
        print("• summarize: `anthropic` not installed — skipping")
        return 0

    model = model or DEFAULT_MODEL
    client = Anthropic()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, full_text FROM policy "
            "WHERE ai_summary IS NULL AND full_text IS NOT NULL "
            "ORDER BY id" + (" LIMIT %s" if limit else ""),
            (limit,) if limit else (),
        )
        rows = cur.fetchall()

    updated = 0
    for pid, title, full_text in rows:
        with conn.cursor() as cur:
            try:
                summary = summarize_text(client, model, title, full_text)
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ policy {pid}: {exc}")
                continue
            if not summary:
                print(f"  · policy {pid}: refused / empty — skipped")
                continue
            cur.execute(
                "UPDATE policy SET ai_summary = %s WHERE id = %s", (summary, pid)
            )
            # Version the re-summarization (docs/04 §4: AI proposes, versioned).
            cur.execute(
                "SELECT COALESCE(MAX(version_no), 0) + 1 FROM policy_version WHERE policy_id = %s",
                (pid,),
            )
            (next_no,) = cur.fetchone()
            cur.execute(
                "INSERT INTO policy_version (policy_id, version_no, change_summary, snapshot) "
                "VALUES (%s, %s, %s, %s)",
                (pid, next_no, f"AI summary generated ({model})",
                 json.dumps({"ai_summary": summary, "model": model})),
            )
            conn.commit()
            updated += 1
            print(f"  ✚ policy {pid}: summarized")
    return updated
