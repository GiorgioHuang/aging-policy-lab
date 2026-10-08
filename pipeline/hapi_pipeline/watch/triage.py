"""Two-stage triage for Policy Watch items.

Stage 1 — keywords (always on, free, deterministic). Weighted aging-policy
terms are matched against title + summary + department; items scoring at or
above KEYWORD_THRESHOLD continue. Strong terms (e.g. "long-term care", "Old
Age Security") clear the bar alone; weak terms ("pension", "disability", bare
"aging", "caregivers") only count alongside another hit, which keeps
public-service pensions, aging infrastructure and child-care notices out.

Stage 2 — Claude (optional; runs only when ANTHROPIC_API_KEY is set). Decides
whether the item is a government policy action materially about older adults
and drafts the Policy Library fields a reviewer would otherwise type. A "not
relevant" verdict marks the candidate auto_rejected, but it is still stored
and listed in the digest so a reviewer can catch a false negative.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from .sources import FeedItem

KEYWORD_THRESHOLD = 2

# (label, regex, weight). Regexes are case-insensitive and word-bounded.
TERMS: list[tuple[str, str, int]] = [
    ("seniors", r"seniors'?|senior citizens?", 2),
    ("older adults", r"older (?:adults?|persons?|people|canadians|nova scotians)", 2),
    ("healthy aging", r"healthy ag(?:e)?ing|population ag(?:e)?ing"
                      r"|ag(?:e)?ing (?:population|in place|well|canadians)", 2),
    ("aging", r"ag(?:e)?ing", 1),  # alone also fits "aging infrastructure"
    ("age-friendly", r"age[- ]friendly", 2),
    ("long-term care", r"long[- ]term care|nursing homes?|residential care", 2),
    ("home care", r"home (?:care|support|and community care)|continuing care", 2),
    ("assisted living", r"assisted living|retirement homes?|seniors'? housing", 2),
    ("dementia", r"dementia|alzheimer'?s?", 2),
    ("caregivers", r"(?:family |unpaid )?caregivers?|caregiving", 1),  # also child care
    ("elder abuse", r"elder (?:abuse|care)", 2),
    ("palliative", r"palliative|end[- ]of[- ]life care", 2),
    ("geriatric", r"geriatrics?|gerontolog\w*|frailty", 2),
    ("OAS/GIS", r"old age security|guaranteed income supplement|allowance for the survivor", 2),
    ("CPP", r"canada pension plan|\bcpp\b", 2),
    ("New Horizons", r"new horizons for seniors", 2),
    ("aging with dignity", r"aging with dignity", 2),
    ("retirement", r"retire(?:ment|es|d)?", 1),
    ("pension", r"pensions?|pensioners?", 1),
    ("disability", r"disabilit(?:y|ies)|accessib(?:le|ility)", 1),
    ("dental care plan", r"canadian dental care plan", 1),
    ("pharmacare", r"pharmacare|drug coverage", 1),
]

_COMPILED = [(label, re.compile(rf"\b(?:{rx})\b", re.IGNORECASE), w) for label, rx, w in TERMS]


@dataclass
class KeywordResult:
    score: int
    terms: list[str]

    @property
    def passes(self) -> bool:
        return self.score >= KEYWORD_THRESHOLD


def keyword_match(item: FeedItem) -> KeywordResult:
    text = " ".join((item.title, item.summary, item.department))
    terms, score = [], 0
    for label, rx, weight in _COMPILED:
        if rx.search(text):
            terms.append(label)
            score += weight
    return KeywordResult(score=score, terms=terms)


# ── Claude ───────────────────────────────────────────────────────────────────

DEFAULT_MODEL = os.getenv("HAPI_WATCH_MODEL", "claude-opus-5-5")

CATEGORIES = ["new_policy", "amendment", "funding", "regulation", "consultation",
              "report", "other"]
LIFECYCLE = ["announced", "funded", "in_effect", "amended", "retired"]
HAPI_DOMAINS = ["health", "independence", "social_participation", "financial_security",
                "care_access", "digital_inclusion"]

SYSTEM = """\
You triage items for the Canadian Healthy Aging Policy Observatory, a research \
database of federal and Nova Scotia government policy that affects older adults.

An item is relevant when it reports a government policy action whose main \
subject is older adults or aging: programs, legislation, regulations, funding, \
strategies or consultations on long-term care, home and community care, \
dementia, caregivers, retirement income (OAS, GIS, CPP), seniors' housing, \
age-friendly communities, social isolation, or healthy aging. A general measure \
(e.g. a health-system investment) is relevant only if older adults are an \
explicit, named target. Ministerial travel, awards, event notices, and routine \
statements are not relevant.

Judge only from the item given; do not assume facts it does not state. Leave \
budget_amount_cad null unless the item states a dollar figure for the measure."""

SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "confidence": {"type": "number"},
        "category": {"type": "string", "enum": CATEGORIES},
        "rationale": {"type": "string"},
        "lifecycle_status": {"type": "string", "enum": LIFECYCLE},
        "theme": {"type": "array", "items": {"type": "string"}},
        "target_group": {"type": "string"},
        "budget_amount_cad": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "hapi_domains": {"type": "array", "items": {"type": "string", "enum": HAPI_DOMAINS}},
    },
    "required": ["relevant", "confidence", "category", "rationale", "lifecycle_status",
                 "theme", "target_group", "budget_amount_cad", "hapi_domains"],
    "additionalProperties": False,
}


@dataclass
class AIVerdict:
    relevant: bool
    category: str
    confidence: float
    rationale: str
    fields: dict
    model: str


def make_client():
    """Return an Anthropic client, or None when triage should be skipped."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None
    return Anthropic()


def _prompt(item: FeedItem) -> str:
    published = item.published_at.date().isoformat() if item.published_at else "unknown"
    return (
        f"Jurisdiction: {item.jurisdiction_code}\n"
        f"Publisher / department: {item.department or 'unknown'}\n"
        f"Published: {published}\n"
        f"Source feed: {item.source}\n"
        f"Title: {item.title}\n"
        f"Summary: {item.summary or '(none)'}\n"
        f"URL: {item.url}"
    )


def classify(client, item: FeedItem, model: str = DEFAULT_MODEL) -> AIVerdict | None:
    """Classify one item. Returns None on refusal (the item stays for review)."""
    resp = client.beta.messages.create(
        model=model,
        max_tokens=4000,
        # Route a policy decline to a fallback model instead of failing the item.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        system=SYSTEM,
        messages=[{"role": "user", "content": _prompt(item)}],
    )
    if resp.stop_reason == "refusal":
        return None
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    fields = {k: data[k] for k in ("lifecycle_status", "theme", "target_group",
                                   "budget_amount_cad", "hapi_domains")}
    return AIVerdict(
        relevant=bool(data["relevant"]),
        category=data["category"],
        confidence=max(0.0, min(1.0, float(data["confidence"]))),
        rationale=data["rationale"],
        fields=fields,
        model=resp.model,
    )
