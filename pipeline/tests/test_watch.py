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


def _collected(name: str) -> list[src.FeedItem]:
    return src.collect(src.get_source(name), live=False, since=src.FIXTURE_SINCE)[1]


def _hits(name: str) -> list[str]:
    return [i.title for i in _collected(name) if triage.keyword_match(i).passes]


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


def test_rss_parse_issue_items():
    items = _items("gazette_p1")
    assert [i.published_at.date() for i in items] == [date(2026, 9, 5), date(2019, 2, 1)]
    assert all(i.department == "Canada Gazette Part I" for i in items)


def test_gazette_issue_expands_to_notices_and_regulations():
    items = _collected("gazette_p1")  # 2019 issue is outside the window
    titles = [i.title for i in items]
    assert titles == [
        "Department of the Environment — Order Amending Schedule 1 to the Species at Risk Act",
        "Department of Employment and Social Development — Notice of intent: consultation "
        "on a national strategy for older persons living alone",
        "Regulations Amending the Old Age Security Regulations",
        "Regulations Amending the Motor Vehicle Safety Regulations",
    ]  # not: home-page nav, PDF link, previous-issue link
    assert items[1].url.endswith("/2026/2026-09-05/html/notice-avis-eng.html#ne2")
    assert all(i.published_at.date() == date(2026, 9, 5) for i in items)
    assert items[0].summary.startswith("Canada Gazette - Part I, September 5, 2026")


def test_gazette_short_link_text_uses_row_text():
    titles = [i.title for i in _collected("gazette_p2")]
    assert titles == [
        "SOR/2026-201 Regulations Amending the Canada Pension Plan Regulations",
        "SOR/2026-202 Regulations Amending the Motor Vehicle Safety Regulations",
    ]


def test_html_listing_items_dated_from_url():
    items = _items("ns_news")
    by_url = {i.url.rsplit("/", 1)[-1]: i for i in items}
    # image link + headline link collapse to one item, headline text wins;
    # French release, "Read more" duplicate and nav links are not items.
    assert sorted(by_url) == ["caregiver-benefit-expanded", "highway-101-twinning-begins",
                              "new-long-term-care-beds-open-kentville",
                              "winter-driving-reminder"]
    beds = by_url["new-long-term-care-beds-open-kentville"]
    assert beds.title == "New Long-Term Care Beds Open in Kentville"
    assert beds.published_at == datetime(2026, 9, 8, tzinfo=timezone.utc)
    assert beds.jurisdiction_code == "CA-NS"


def test_html_listing_details_fill_summary():
    items = {i.url.rsplit("/", 1)[-1]: i for i in _collected("ns_news")}
    assert "winter-driving-reminder" not in items  # 2025: outside the window
    assert items["new-long-term-care-beds-open-kentville"].summary.startswith(
        "The Province is adding 48 long-term care beds")
    # NS release pages have no description meta: the opening body paragraphs are
    # used, skipping short ones ("NEWS RELEASE", "Quotes:").
    caregiver = items["caregiver-benefit-expanded"].summary
    assert caregiver.startswith("More caregivers of seniors")
    assert "$400 a month" in caregiver and "NEWS RELEASE" not in caregiver


def test_with_details_prefers_longer_og_title():
    item = src.FeedItem("ns_news", "https://x/en/2026/09/01/a", "Short title")
    page = (b'<html><head><meta property="og:title" content="A much longer &amp; fuller title">'
            b'<meta name="description" content="Desc"></head></html>')
    d = src.with_details(item, page)
    assert d.title == "A much longer & fuller title" and d.summary == "Desc"


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
    assert _hits("gazette_p1") == [
        "Department of Employment and Social Development — Notice of intent: consultation "
        "on a national strategy for older persons living alone",
        "Regulations Amending the Old Age Security Regulations",
    ]  # not: species at risk, motor vehicles
    assert _hits("gazette_p2") == [
        "SOR/2026-201 Regulations Amending the Canada Pension Plan Regulations"]
    assert sorted(_hits("ns_news")) == [
        "Caregiver Benefit Expanded to More Families",
        "New Long-Term Care Beds Open in Kentville",
    ]  # not: highway twinning (its page says nothing about seniors)


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
    a = "https://WWW.Canada.ca/en/news/x.html/?utm_source=rss&utm_medium=feed"
    b = "https://www.canada.ca/en/news/x.html"
    assert normalize_url(a) == normalize_url(b)
    assert url_hash(a) == url_hash(b)
    assert url_hash(b) != url_hash("https://www.canada.ca/en/news/y.html")


def test_url_fragments_distinguish_gazette_notices():
    base = "https://gazette.gc.ca/rp-pr/p1/2026/2026-09-05/html/notice-avis-eng.html"
    assert url_hash(base + "#ne1") != url_hash(base + "#ne2")


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
