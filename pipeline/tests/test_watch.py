"""Policy Watch unit tests — pure (no DB, no network, no API key).

Run:  cd pipeline && python -m pytest tests/
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

from hapi_pipeline.watch import sources as src
from hapi_pipeline.watch import triage
from hapi_pipeline.watch.store import draft_seed_entry, normalize_url, render_digest, url_hash


def _items(name: str) -> list[src.FeedItem]:
    s = src.get_source(name)
    return src.parse(s, s.fixture_path.read_bytes())


def _hits(name: str) -> list[str]:
    return [i.title for i in _items(name) if triage.keyword_match(i).passes]


# ── parsing ──────────────────────────────────────────────────────────────────

def test_atom_parse_fields():
    items = _items("gc_news")
    assert len(items) == 5
    first = items[0]
    assert first.url == "https://example.org/fixture/gc/oas-increase-75"
    assert first.department == "Employment and Social Development Canada"
    assert first.published_at == datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)
    assert "<p>" not in first.summary and "Old Age Security" in first.summary
    assert first.jurisdiction_code == "CA-FED"


def test_rss_parse_dates_and_default_department():
    items = _items("gazette_p1")
    assert [i.published_at.date() for i in items] == [date(2026, 9, 5)] * 2
    assert all(i.department == "Canada Gazette" for i in items)


def test_socrata_parse_url_object_and_department():
    items = _items("ns_news")
    assert items[0].url == "https://example.org/fixture/ns/ltc-beds-kentville"
    assert items[0].department == "Seniors and Long-term Care"
    assert items[0].jurisdiction_code == "CA-NS"
    assert items[0].published_at.date() == date(2026, 9, 8)


def test_parse_date_formats():
    assert src.parse_date("Fri, 05 Sep 2026 18:00:00 GMT").day == 5
    assert src.parse_date("2026-09-08T10:00:00.000").tzinfo is not None
    assert src.parse_date("2026-09-08").date() == date(2026, 9, 8)
    assert src.parse_date("") is None and src.parse_date("not a date") is None


def test_window_keeps_undated_drops_old():
    old = src.FeedItem("s", "u", "t", published_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    assert not src.within_window(old, date(2026, 1, 1))
    assert src.within_window(src.FeedItem("s", "u", "t"), date(2026, 1, 1))


def test_live_url_adds_date_filter():
    url = src.get_source("gc_news").live_url(date(2026, 9, 1))
    assert url.startswith(src.GC_NEWS_API)
    assert "publishedDate%3E=2026-09-01" in url and "format=atom" in url
    assert "dept=" not in url
    assert "dept=publichealthagencyofcanada" in src.get_source("gc_news_phac").live_url(
        date(2026, 9, 1))


# ── keyword triage ───────────────────────────────────────────────────────────

def test_keywords_keep_aging_policy_and_drop_decoys():
    assert _hits("gc_news") == [
        "Government of Canada increases Old Age Security for seniors aged 75 and over",
        "New funding to support people living with dementia and their caregivers",
    ]  # not: aging bridges, child-care caregivers, fisheries
    assert _hits("gazette_p1") == ["Regulations Amending the Old Age Security Regulations"]
    assert _hits("gazette_p2") == ["Regulations Amending the Canada Pension Plan Regulations"]
    assert len(_hits("ns_news")) == 2  # not: highway twinning


def test_weak_terms_need_company():
    def kw(title: str) -> triage.KeywordResult:
        return triage.keyword_match(src.FeedItem("s", "u", title))

    assert not kw("Public service pension plan update").passes
    assert not kw("Aging water infrastructure renewal").passes
    assert not kw("Senior officials meet on trade").passes  # singular "senior"
    assert kw("Pension increase for retirees").passes        # pension + retirement
    assert kw("Strategy on aging in place").passes
    assert kw("Seniors' Safety Grant opens").passes


# ── Claude triage (fake client) ──────────────────────────────────────────────

class _FakeMessages:
    def __init__(self, payload: dict, stop_reason: str = "end_turn"):
        self.payload, self.stop_reason, self.calls = payload, stop_reason, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            model=kwargs["model"],
            content=[SimpleNamespace(type="text", text=json.dumps(self.payload))],
        )


def _fake_client(payload: dict, stop_reason: str = "end_turn"):
    msgs = _FakeMessages(payload, stop_reason)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


VERDICT = {
    "relevant": True, "confidence": 1.4, "category": "funding",
    "rationale": "Funds dementia care for older adults.", "lifecycle_status": "funded",
    "theme": ["dementia"], "target_group": "people living with dementia",
    "budget_amount_cad": 20000000, "hapi_domains": ["health", "care_access"],
}


def test_classify_parses_structured_output():
    client, msgs = _fake_client(VERDICT)
    v = triage.classify(client, _items("gc_news")[1])
    assert v.relevant and v.category == "funding"
    assert v.confidence == 1.0  # clamped
    assert v.fields["budget_amount_cad"] == 20000000
    call = msgs.calls[0]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["fallbacks"] == "default"
    assert "dementia" in call["messages"][0]["content"].lower()


def test_classify_refusal_returns_none():
    client, _ = _fake_client(VERDICT, stop_reason="refusal")
    assert triage.classify(client, _items("gc_news")[1]) is None


def test_schema_is_strict():
    assert triage.SCHEMA["additionalProperties"] is False
    assert set(triage.SCHEMA["required"]) == set(triage.SCHEMA["properties"])


# ── store helpers ────────────────────────────────────────────────────────────

def test_url_normalization_dedupes_variants():
    a = "https://WWW.Canada.ca/en/news/x.html?utm_source=rss#top"
    b = "https://www.canada.ca/en/news/x.html"
    assert normalize_url(a) == normalize_url(b)
    assert url_hash(a) == url_hash(b)
    assert url_hash(b) != url_hash("https://www.canada.ca/en/news/y.html")


def _cand(**kw) -> dict:
    base = {
        "id": 7, "source": "gc_news", "url": "https://example.org/x",
        "title": "New [pilot] for seniors", "summary": "A pilot.",
        "published_at": datetime(2026, 9, 2, tzinfo=timezone.utc),
        "jurisdiction_code": "CA-FED", "department": "ESDC",
        "matched_terms": ["seniors"], "keyword_score": 2, "ai_relevant": None,
        "ai_category": None, "ai_confidence": None, "ai_rationale": None,
        "ai_fields": None, "ai_model": None, "status": "new", "seed_slug": None,
        "first_seen_at": datetime(2026, 9, 3, tzinfo=timezone.utc),
    }
    base.update(kw)
    return base


def test_draft_seed_entry_uses_ai_fields_when_present():
    e = draft_seed_entry(_cand(ai_fields={"lifecycle_status": "funded", "theme": ["LTC"],
                                          "target_group": "LTC residents",
                                          "budget_amount_cad": 5e6}))
    assert e["slug"] == "ca-fed-new-pilot-for-seniors-2026"
    assert e["released_at"] == "2026-09-02"
    assert e["lifecycle_status"] == "funded" and e["budget_amount"] == 5e6
    assert e["target_population"]["group"] == "LTC residents"
    assert e["indicators"] == [] and e["kpis"] == []


def test_draft_seed_entry_keyword_only_defaults():
    e = draft_seed_entry(_cand())
    assert e["lifecycle_status"] == "announced"
    assert e["theme"] == ["seniors"]
    assert "budget_amount" not in e


def test_render_digest_groups_and_escapes():
    md = render_digest(
        [_cand(), _cand(id=8, jurisdiction_code="CA-NS", ai_category="funding",
                        ai_confidence=0.9, ai_rationale="Because.")],
        [_cand(id=9, title="Aging bridges")], backlog=3, days=7, today=date(2026, 9, 7),
    )
    assert md.startswith("## Policy Watch — 2026-09-07")
    assert "**2** new" in md and "**3** older" in md
    assert md.index("### Federal") < md.index("### Nova Scotia")
    assert "[New (pilot) for seniors](https://example.org/x)" in md
    assert "`funding` 0.90" in md and "> Because." in md
    assert "<details>" in md and "Aging bridges" in md
