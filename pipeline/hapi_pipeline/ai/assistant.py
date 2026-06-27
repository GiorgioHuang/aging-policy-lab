"""AI Research Assistant (docs/08): topic → grounded evidence pack → cited draft.

Retrieval is plain SQL over the platform's own stores (Policy Library, indicators,
findings) plus the literature KB — the same data the dashboards use. The Claude
draft must cite an item id from the pack for every claim and may not invent
sources; analytic results keep their Association/Causal tag (docs/08 §4).
"""
from __future__ import annotations

import json
import os
import re

DEFAULT_MODEL = os.getenv("HAPI_SUMMARY_MODEL", "claude-opus-4-8")

DRAFT_SYSTEM = (
    "You draft cited literature-review starting points for a Canadian healthy-aging "
    "policy research platform. STRICT RULES: (1) Every factual claim must end with a "
    "citation tag in square brackets referencing an item id from the EVIDENCE PACK "
    "(e.g. [P3], [L2], [F1], [I:care_access.regular_provider_65plus]). (2) Use ONLY "
    "the pack — never invent sources, numbers, or references. (3) When you mention an "
    "analytic finding, state its tier exactly as given (Association or Causal(ITS)) and "
    "NEVER upgrade an association to a causal claim. (4) This is a draft + evidence for "
    "a human researcher, not a verdict. Structure: Background, Policy landscape, "
    "Evidence & indicators, Gaps & next steps. 250-450 words. End with a 'Sources' list "
    "mapping each tag you used to its title."
)


_STOPWORDS = {
    "and", "the", "for", "with", "from", "that", "this", "policy", "policies",
    "are", "was", "were", "have", "has", "about", "into", "over", "near",
}


def _terms(topic: str) -> list[str]:
    words = (w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", topic))
    return [w for w in words if w not in _STOPWORDS]


def _matches(text: str | None, terms: list[str]) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(term in t for term in terms)


def build_evidence_pack(conn, topic: str) -> dict:
    terms = _terms(topic) or [""]
    with conn.cursor() as cur:
        # policies
        cur.execute(
            """SELECT p.id, j.code, p.title, p.department, p.released_at::text,
                      p.lifecycle_status, p.theme, p.ai_summary, p.full_text
                 FROM policy p JOIN jurisdiction j ON j.id = p.jurisdiction_id"""
        )
        policies = []
        for pid, jur, title, dept, rel, life, theme, summ, full in cur.fetchall():
            hay = " ".join([title or "", " ".join(theme or []), summ or "", full or ""])
            if _matches(hay, terms):
                policies.append({
                    "cite": f"P{pid}", "title": title, "jurisdiction": jur,
                    "department": dept, "released_at": rel, "lifecycle": life,
                    "theme": theme or [], "summary": summ,
                })

        # literature
        cur.execute("SELECT id, title, authors, year, venue, url, abstract, topics FROM literature")
        literature = []
        for lid, title, authors, year, venue, url, abstract, topics in cur.fetchall():
            hay = " ".join([title or "", abstract or "", " ".join(topics or [])])
            if _matches(hay, terms):
                literature.append({
                    "cite": f"L{lid}", "title": title, "authors": authors, "year": year,
                    "venue": venue, "url": url, "abstract": abstract,
                })

        # findings
        cur.execute(
            """SELECT id, title, tier, method, indicator_code, jurisdiction_code,
                      result, assumptions, limitations FROM analysis_finding"""
        )
        findings = []
        for fid, title, tier, method, ind, jur, result, assum, limits in cur.fetchall():
            hay = " ".join([title or "", ind or "", jur or ""])
            if _matches(hay, terms) or _matches(topic, [(ind or "").split(".")[0]]):
                tag = "Causal(ITS)" if (tier == "causal" and method == "its") else (
                    "Causal" if tier == "causal" else "Association")
                findings.append({
                    "cite": f"F{fid}", "title": title, "tier_label": tag, "method": method,
                    "indicator": ind, "jurisdiction": jur,
                    "result": result, "assumptions": assum, "limitations": limits,
                })

        # indicators referenced by the matched policies/findings + latest HAPI score
        codes = sorted({f["indicator"] for f in findings if f["indicator"]})
        indicators = []
        for code in codes:
            cur.execute(
                """SELECT i.name, j.code, h.period::text, h.score::text
                     FROM hapi_score h JOIN jurisdiction j ON j.id=h.jurisdiction_id
                     JOIN indicator i ON i.code=%s
                    WHERE h.domain='care_access'
                 ORDER BY j.code, h.period DESC""",
                (code,),
            )
            rows = cur.fetchall()
            name = rows[0][0] if rows else code
            latest = {}
            for _, jur, period, score in rows:
                latest.setdefault(jur, {"jurisdiction": jur, "period": period, "care_access_score": score})
            indicators.append({"cite": f"I:{code}", "code": code, "name": name,
                               "latest_hapi_care_access": list(latest.values())})

    return {"topic": topic, "policies": policies, "literature": literature,
            "findings": findings, "indicators": indicators}


def draft_review(client, model: str, pack: dict) -> str | None:
    resp = client.messages.create(
        model=model,
        max_tokens=1400,
        system=DRAFT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Topic: {pack['topic']}\n\nEVIDENCE PACK (JSON):\n{json.dumps(pack, ensure_ascii=False)}",
        }],
    )
    if resp.stop_reason == "refusal":
        return None
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def research(conn, topic: str, model: str | None = None) -> dict:
    """Return {pack, draft}. draft is None when no API key / SDK is available."""
    pack = build_evidence_pack(conn, topic)
    draft = None
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic

            draft = draft_review(Anthropic(), model or DEFAULT_MODEL, pack)
        except ImportError:
            pass
    return {"pack": pack, "draft": draft}
