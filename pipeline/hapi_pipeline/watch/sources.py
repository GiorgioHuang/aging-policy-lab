"""Feed sources for Policy Watch: where new aging policy first appears.

Each source is an official, machine-readable feed. Three shapes are supported:

  * ``atom``    — Government of Canada news API (api.io.canada.ca), one feed
                  for all departments' news releases plus targeted department
                  feeds as a backstop.
  * ``rss``     — Canada Gazette Part I (proposed regulations, notices) and
                  Part II (enacted regulations). The Gazette feed lists whole
                  *issues*, so each in-window issue page is opened and its table
                  of contents expanded into one item per notice / regulation.
  * ``socrata`` — Nova Scotia news releases on data.novascotia.ca (xcif-vvr3),
                  filtered and ordered server-side on its ``timestamp`` column.

Like the Data Hub connectors, every source has a vendored fixture so offline
runs are deterministic. Fixtures are synthetic samples (example.org URLs) used
only for tests and local dev; production runs always use ``--live``.

Field names in feeds differ by publisher, so parsing is deliberately tolerant
(first matching key wins). `hapi watch probe` dumps what a live feed actually
returns, to confirm or correct these assumptions from a networked runner.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
# Fixture items are dated 2026 and never change; a fixed window keeps them in
# scope forever while still exercising the filter (the sample 2019 issue).
FIXTURE_SINCE = date(2026, 1, 1)

USER_AGENT = "Mozilla/5.0 (compatible; hapi-policy-watch/1.0; +https://acp.icareu.cc)"
_RETRY_STATUS = {429, 500, 502, 503, 504}

GC_NEWS_API = "https://api.io.canada.ca/io-server/gc/news/en/v2"


@dataclass(frozen=True)
class FeedItem:
    """One item from a feed, normalized across RSS / Atom / Socrata."""

    source: str
    url: str
    title: str
    summary: str = ""
    published_at: datetime | None = None
    jurisdiction_code: str = ""
    department: str = ""


@dataclass(frozen=True)
class WatchSource:
    name: str
    label: str
    kind: str  # atom | rss | socrata
    jurisdiction_code: str
    fixture_name: str
    url: str = ""                      # fixed feed URL (rss)
    params: dict = field(default_factory=dict)  # query params (atom / socrata)
    department: str = ""               # default department when the feed has none
    expand_issues: bool = False        # rss items are issues: expand each issue's TOC
    issue_fixture: str = ""            # offline stand-in for an issue page
    date_field: str = ""               # socrata column to filter / order by

    def live_url(self, since: date) -> str:
        if self.kind == "atom":
            params = dict(self.params)
            params["publishedDate>"] = since.isoformat()
            return f"{GC_NEWS_API}?{urllib.parse.urlencode(params)}"
        if self.kind == "socrata":
            params = dict(self.params)
            if self.date_field:
                params["$where"] = f"{self.date_field} >= '{since.isoformat()}T00:00:00'"
                params["$order"] = f"{self.date_field} DESC"
            return f"{self.url}?{urllib.parse.urlencode(params)}"
        return self.url

    @property
    def fixture_path(self) -> Path:
        return FIXTURES_DIR / self.fixture_name


def _gc_news(name: str, label: str, dept: str | None, department: str = "") -> WatchSource:
    params = {
        "type": "newsreleases",
        "sort": "publishedDate",
        "orderBy": "desc",
        "pick": "100",
        "format": "atom",
    }
    if dept:
        params["dept"] = dept
    return WatchSource(
        name=name,
        label=label,
        kind="atom",
        jurisdiction_code="CA-FED",
        fixture_name="gc_news.xml",
        params=params,
        department=department,
    )


SOURCES: list[WatchSource] = [
    # All federal departments' news releases in one feed; keyword triage
    # narrows it to aging policy. Polled daily, 100 items covers a day.
    _gc_news("gc_news", "Government of Canada news releases (all departments)", None),
    # Department backstops for the main aging-policy portfolios, in case the
    # all-departments feed is capped or paginated differently.
    _gc_news("gc_news_esdc", "ESDC news releases (seniors, OAS/GIS, CPP)",
             "departmentofemploymentandsocialdevelopment",
             "Employment and Social Development Canada"),
    _gc_news("gc_news_phac", "Public Health Agency of Canada news releases",
             "publichealthagencyofcanada", "Public Health Agency of Canada"),
    WatchSource(
        name="gazette_p1",
        label="Canada Gazette Part I (notices, proposed regulations)",
        kind="rss",
        jurisdiction_code="CA-FED",
        fixture_name="gazette_p1.xml",
        url="https://www.gazette.gc.ca/rss/p1-eng.xml",
        department="Canada Gazette Part I",
        expand_issues=True,
        issue_fixture="gazette_p1_issue.html",
    ),
    WatchSource(
        name="gazette_p2",
        label="Canada Gazette Part II (enacted regulations)",
        kind="rss",
        jurisdiction_code="CA-FED",
        fixture_name="gazette_p2.xml",
        url="https://www.gazette.gc.ca/rss/p2-eng.xml",
        department="Canada Gazette Part II",
        expand_issues=True,
        issue_fixture="gazette_p2_issue.html",
    ),
    WatchSource(
        name="ns_news",
        label="Nova Scotia government news releases (data.novascotia.ca xcif-vvr3)",
        kind="socrata",
        jurisdiction_code="CA-NS",
        fixture_name="ns_news.json",
        url="https://data.novascotia.ca/resource/xcif-vvr3.json",
        params={"$limit": "500"},
        date_field="timestamp",
    ),
]


def all_sources() -> list[WatchSource]:
    return SOURCES


def get_source(name: str) -> WatchSource:
    for s in SOURCES:
        if s.name == name:
            return s
    names = ", ".join(s.name for s in SOURCES)
    raise KeyError(f"unknown watch source '{name}'. Available: {names}")


# ── fetching ─────────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 30, retries: int = 2, backoff: float = 2.0) -> bytes:
    """GET `url` with a browser-like UA, retrying transient failures."""
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return resp.read()
        except urllib.error.HTTPError as e:  # noqa: PERF203
            last = e
            if e.code not in _RETRY_STATUS:
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))
    assert last is not None
    raise last


def fetch_raw(source: WatchSource, *, live: bool, since: date) -> bytes:
    if live:
        return http_get(source.live_url(since))
    return source.fixture_path.read_bytes()


# ── parsing ──────────────────────────────────────────────────────────────────

_ATOM = "{http://www.w3.org/2005/Atom}"


def _text(el: ET.Element | None) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _strip_html(s: str) -> str:
    """Feed summaries often carry HTML; keep the words only."""
    import html
    import re

    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_date(value: str) -> datetime | None:
    """Parse RFC 822 (RSS), ISO 8601 (Atom / Socrata) or a bare date."""
    v = (value or "").strip()
    if not v:
        return None
    try:
        dt = parsedate_to_datetime(v)
    except (TypeError, ValueError):
        dt = None
    if dt is None:
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_rss(source: WatchSource, raw: bytes) -> list[FeedItem]:
    root = ET.fromstring(raw)
    items = []
    for it in root.iter("item"):
        url = _text(it.find("link")) or _text(it.find("guid"))
        title = _strip_html(_text(it.find("title")))
        if not (url and title):
            continue
        items.append(FeedItem(
            source=source.name,
            url=url,
            title=title,
            summary=_strip_html(_text(it.find("description"))),
            published_at=parse_date(_text(it.find("pubDate"))),
            jurisdiction_code=source.jurisdiction_code,
            department=_text(it.find("category")) or source.department,
        ))
    return items


def parse_atom(source: WatchSource, raw: bytes) -> list[FeedItem]:
    root = ET.fromstring(raw)
    items = []
    for e in root.iter(f"{_ATOM}entry"):
        url = ""
        for link in e.findall(f"{_ATOM}link"):
            if link.get("rel", "alternate") == "alternate" and link.get("href"):
                url = link.get("href", "")
                break
        title = _strip_html(_text(e.find(f"{_ATOM}title")))
        if not (url and title):
            continue
        summary = _text(e.find(f"{_ATOM}summary")) or _text(e.find(f"{_ATOM}content"))
        published = _text(e.find(f"{_ATOM}published")) or _text(e.find(f"{_ATOM}updated"))
        author = _text(e.find(f"{_ATOM}author/{_ATOM}name"))
        items.append(FeedItem(
            source=source.name,
            url=url,
            title=title,
            summary=_strip_html(summary),
            published_at=parse_date(published),
            jurisdiction_code=source.jurisdiction_code,
            department=author or source.department,
        ))
    return items


def _pick(row: dict, *keys: str) -> str:
    """First non-empty value among `keys` (exact, then substring match on key)."""
    for k in keys:
        v = row.get(k)
        if v:
            return v.get("url", "") if isinstance(v, dict) else str(v)
    lower = {k.lower(): v for k, v in row.items()}
    for k in keys:
        for rk, v in lower.items():
            if k in rk and v:
                return v.get("url", "") if isinstance(v, dict) else str(v)
    return ""


def _clip(s: str, limit: int = 600) -> str:
    """Bodies can be whole releases; keep a teaser-sized summary."""
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + " …"


def parse_socrata(source: WatchSource, raw: bytes) -> list[FeedItem]:
    rows = json.loads(raw.decode("utf-8"))
    items = []
    for r in rows:
        url = _pick(r, "url", "link", "release_url", "web_link")
        title = _strip_html(_pick(r, "subject", "title", "headline"))
        if not (url and title):
            continue
        items.append(FeedItem(
            source=source.name,
            url=url,
            title=title,
            summary=_clip(_strip_html(_pick(r, "contents", "summary", "description"))),
            published_at=parse_date(_pick(r, "timestamp", "release_date", "date")),
            jurisdiction_code=source.jurisdiction_code,
            department=_pick(r, "department", "dept", "organization", "ministry")
            or source.department,
        ))
    return items


class _TocParser(HTMLParser):
    """Collect (block text, first link) for each table row / list item / para.

    Gazette issue pages list each notice or regulation as a row or list entry
    whose link may carry only a registration number ("SOR/2026-201"), so the
    whole block's text is used as the title when the link text is short.
    """

    BLOCKS = {"tr", "li", "p", "dt", "dd", "h3", "h4"}
    CELLS = {"td", "th", "br", "div", "span"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str, str]] = []  # (block text, link text, href)
        self._stack: list[dict] = []
        self._link: dict | None = None

    def handle_starttag(self, tag, attrs):
        if tag in self.CELLS and self._stack:
            self._stack[-1]["text"].append(" ")  # keep "SOR/2026-201" and title apart
        if tag in self.BLOCKS:
            self._stack.append({"text": [], "href": "", "link_text": []})
        elif tag == "a" and self._stack and not self._stack[-1]["href"]:
            href = dict(attrs).get("href") or ""
            if href and not href.startswith(("#", "mailto:", "javascript:")):
                self._stack[-1]["href"] = href
                self._link = self._stack[-1]

    def handle_endtag(self, tag):
        if tag == "a":
            self._link = None
        elif tag in self.BLOCKS and self._stack:
            b = self._stack.pop()
            text = " ".join("".join(b["text"]).split())
            if b["href"]:
                link_text = " ".join("".join(b["link_text"]).split())
                self.blocks.append((text, link_text, b["href"]))
            if self._stack:  # nested block: let the parent see the text too
                self._stack[-1]["text"].append(" " + text + " ")

    def handle_data(self, data):
        if self._stack:
            self._stack[-1]["text"].append(data)
            if self._link is self._stack[-1]:
                self._stack[-1]["link_text"].append(data)


_TOC_SKIP = re.compile(r"^(table of contents|index|pdf|previous|next|top of page|"
                       r"date modified|canada gazette)", re.IGNORECASE)


def expand_issue(source: WatchSource, issue: FeedItem, page: bytes) -> list[FeedItem]:
    """One item per notice / regulation linked from a Gazette issue page."""
    parser = _TocParser()
    parser.feed(page.decode("utf-8", errors="replace"))
    issue_dir = urllib.parse.urlsplit(issue.url).path.rsplit("/", 1)[0] + "/"
    items, seen = [], set()
    for block_text, link_text, href in parser.blocks:
        url = urllib.parse.urljoin(issue.url, href)
        parts = urllib.parse.urlsplit(url)
        if not parts.path.startswith(issue_dir) or url.split("#")[0] == issue.url.split("#")[0]:
            continue  # navigation, other issues, or the page itself
        title = link_text if len(link_text) >= 25 else block_text
        title = title.strip(" -–—:")
        if len(title) < 20 or _TOC_SKIP.match(title) or url in seen:
            continue
        seen.add(url)
        items.append(FeedItem(
            source=source.name,
            url=url,
            title=_clip(title, 300),
            summary=issue.title,
            published_at=issue.published_at,
            jurisdiction_code=source.jurisdiction_code,
            department=source.department,
        ))
    return items


PARSERS = {"rss": parse_rss, "atom": parse_atom, "socrata": parse_socrata}


def parse(source: WatchSource, raw: bytes) -> list[FeedItem]:
    return PARSERS[source.kind](source, raw)


def within_window(item: FeedItem, since: date) -> bool:
    """Keep undated items (can't tell), drop items published before `since`."""
    if item.published_at is None:
        return True
    return item.published_at.date() >= since


def collect(source: WatchSource, *, live: bool, since: date) -> tuple[int, list[FeedItem]]:
    """Fetch + parse + date-window a source, expanding Gazette issues.

    Returns (items in the raw feed, in-window items ready for triage).
    """
    items = parse(source, fetch_raw(source, live=live, since=since))
    raw_count = len(items)
    items = [i for i in items if within_window(i, since)]
    if source.expand_issues:
        expanded = []
        for issue in items:
            page = (http_get(issue.url) if live
                    else (FIXTURES_DIR / source.issue_fixture).read_bytes())
            expanded.extend(expand_issue(source, issue, page))
        items = expanded
    return raw_count, items


def default_since(days: int) -> date:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date()
