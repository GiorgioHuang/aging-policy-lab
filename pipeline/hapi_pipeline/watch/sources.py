"""Feed sources for Policy Watch: where new aging policy first appears.

Every source below was checked against the live site with `hapi watch probe`
(run from a GitHub runner, since the dev sandbox cannot reach .gc.ca / .ns.ca):

  * ``atom`` — Government of Canada news API (api.io.canada.ca): one feed for
               all departments' news releases (100 items ≈ 10 days, so a daily
               poll is safe) plus ESDC / PHAC department feeds as a backstop.
  * ``rss``  — Canada Gazette Part I (notices, proposed regulations) and Part II
               (enacted regulations). The feed lists whole *issues*, so each
               in-window issue page is opened and its table of contents
               expanded into one item per notice / regulation. Also the bill
               feeds of Parliament (LEGISinfo) and the NS Legislature.
  * ``html`` — Nova Scotia news releases. The province's legacy RSS
               (novascotia.ca/news/rss/rss.asp) returns an empty stub, its
               open-data copy (data.novascotia.ca xcif-vvr3) stopped updating in
               July 2026, and news.novascotia.ca exposes no feed. Release URLs
               carry their date (/en/YYYY/MM/DD/slug), so the site's listing
               page is read directly and each release page fetched for its
               description.

Like the Data Hub connectors, every source has vendored fixtures so offline
runs are deterministic. Fixtures are synthetic samples (example.org URLs) used
only for tests and local dev; production runs always use ``--live``.
"""
from __future__ import annotations

import html
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
    """One item from a source, normalized across Atom / RSS / HTML listings."""

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
    kind: str  # atom | rss | html
    jurisdiction_code: str
    fixture_name: str
    url: str = ""                      # feed / listing URL (rss, html)
    params: dict = field(default_factory=dict)  # query params (atom)
    department: str = ""               # default department when the source has none
    # rss: items are Gazette issues — expand each issue page's table of contents
    expand_issues: bool = False
    issue_fixture: str = ""            # offline stand-in for an issue page
    # html: which links on the listing page are items; named groups y, m, d
    item_pattern: str = ""
    pages: int = 1                     # html: listing pages to read (?page=0..n-1)
    detail_fixture: str = ""           # fixture dir of item pages, named <slug>.html

    def live_url(self, since: date) -> str:
        if self.kind == "atom":
            params = dict(self.params)
            params["publishedDate>"] = since.isoformat()
            return f"{GC_NEWS_API}?{urllib.parse.urlencode(params)}"
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
    _gc_news("gc_news", "Government of Canada news releases (all departments)", None),
    # Backstops: the all-departments feed holds ~10 days, these hold months.
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
        name="legisinfo_bills",
        label="Federal bills — LEGISinfo (House of Commons and Senate)",
        kind="rss",
        jurisdiction_code="CA-FED",
        fixture_name="legisinfo_bills.xml",
        url="https://www.parl.ca/legisinfo/en/bills/rss",
        department="Parliament of Canada",
    ),
    WatchSource(
        name="ns_bills",
        label="Nova Scotia bills — Legislature of Nova Scotia",
        kind="rss",
        jurisdiction_code="CA-NS",
        fixture_name="ns_bills.xml",
        url="https://nslegislature.ca/legislative-business/bills-statutes/rss",
        department="Nova Scotia Legislature",
    ),
    WatchSource(
        name="ns_news",
        label="Nova Scotia government news releases (news.novascotia.ca)",
        kind="html",
        jurisdiction_code="CA-NS",
        fixture_name="ns_news.html",
        # The full newest-first listing; the home page shows only a selection.
        url="https://news.novascotia.ca/search/all",
        pages=2,
        item_pattern=r"/en/(?P<y>\d{4})/(?P<m>\d{2})/(?P<d>\d{2})/[^/?#]+/?$",
        detail_fixture="ns_news_pages",
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
    if not live:
        return source.fixture_path.read_bytes()
    url = source.live_url(since)
    if source.kind == "html" and source.pages > 1:
        # Concatenated pages parse fine as one link soup.
        sep = "&" if "?" in url else "?"
        return b"\n".join(http_get(url if i == 0 else f"{url}{sep}page={i}")
                          for i in range(source.pages))
    return http_get(url)


# ── parsing helpers ──────────────────────────────────────────────────────────

_ATOM = "{http://www.w3.org/2005/Atom}"


def _text(el: ET.Element | None) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _strip_html(s: str) -> str:
    """Feed summaries often carry HTML; keep the words only."""
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _clip(s: str, limit: int = 600) -> str:
    """Keep a teaser-sized summary."""
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + " …"


# Publishers that don't follow RFC 822 in <pubDate> (e.g. the NS Legislature
# writes "September 17, 2026").
_LOOSE_DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%B %d %Y")


def parse_date(value: str) -> datetime | None:
    """Parse RFC 822 (RSS), ISO 8601 (Atom), a bare date or "Month D, YYYY"."""
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
            dt = None
    if dt is None:
        for fmt in _LOOSE_DATE_FORMATS:
            try:
                dt = datetime.strptime(v, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ── Atom / RSS ───────────────────────────────────────────────────────────────

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


# ── Gazette issue pages ──────────────────────────────────────────────────────

class _TocParser(HTMLParser):
    """Collect (block text, link text, first link) per table row / list item / para.

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


# ── HTML listing pages ───────────────────────────────────────────────────────

class _LinkParser(HTMLParser):
    """All (href, text) anchors on a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def parse_html_listing(source: WatchSource, raw: bytes) -> list[FeedItem]:
    """Items = links whose path matches `item_pattern`; date comes from the URL.

    A listing often links one item twice (image + headline); the longest link
    text wins.
    """
    parser = _LinkParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    pattern = re.compile(source.item_pattern)
    best: dict[str, tuple[str, datetime]] = {}
    for href, text in parser.links:
        url = urllib.parse.urljoin(source.url, href).split("#")[0]
        m = pattern.search(urllib.parse.urlsplit(url).path)
        if not m:
            continue
        try:
            published = datetime(int(m["y"]), int(m["m"]), int(m["d"]), tzinfo=timezone.utc)
        except ValueError:
            continue
        if url not in best or len(text) > len(best[url][0]):
            best[url] = (text, published)
    return [
        FeedItem(source=source.name, url=url, title=text, published_at=published,
                 jurisdiction_code=source.jurisdiction_code, department=source.department)
        for url, (text, published) in best.items()
        if len(text) >= 15
    ]


class _MetaParser(HTMLParser):
    """<meta name|property=... content=...> pairs, the <title>, and <p> texts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.paragraphs: list[str] = []
        self._in_title = False
        self._p: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = a["content"]
        elif tag == "title":
            self._in_title = True
        elif tag == "p":
            self._p = []

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._p is not None:
            self._p.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "p" and self._p is not None:
            text = " ".join("".join(self._p).split())
            if text:
                self.paragraphs.append(text)
            self._p = None


def page_meta(page: bytes) -> _MetaParser:
    parser = _MetaParser()
    parser.feed(page.decode("utf-8", errors="replace"))
    return parser


def with_details(item: FeedItem, page: bytes) -> FeedItem:
    """Fill summary (and a better title) from an item page.

    Uses the description meta tags when present; NS release pages have none, so
    otherwise the opening paragraphs of the body (short ones — bylines, photo
    credits — skipped).
    """
    parsed = page_meta(page)
    meta = parsed.meta
    summary = meta.get("og:description") or meta.get("description") or ""
    if not summary:
        summary = " ".join([p for p in parsed.paragraphs if len(p) >= 60][:2])
    title = meta.get("og:title") or ""
    return FeedItem(
        source=item.source,
        url=item.url,
        title=_strip_html(title) if len(title) > len(item.title) else item.title,
        summary=_clip(_strip_html(summary)),
        published_at=item.published_at,
        jurisdiction_code=item.jurisdiction_code,
        department=item.department,
    )


# ── collection ───────────────────────────────────────────────────────────────

PARSERS = {"rss": parse_rss, "atom": parse_atom, "html": parse_html_listing}


def parse(source: WatchSource, raw: bytes) -> list[FeedItem]:
    return PARSERS[source.kind](source, raw)


def within_window(item: FeedItem, since: date) -> bool:
    """Keep undated items (can't tell), drop items published before `since`."""
    if item.published_at is None:
        return True
    return item.published_at.date() >= since


def collect(source: WatchSource, *, live: bool, since: date) -> tuple[int, list[FeedItem]]:
    """Fetch, parse and date-window a source; expand Gazette issues; fetch each
    HTML-listing item's page for its description (a listing holds a few dozen).

    Returns (items in the raw feed / listing, in-window items ready for triage).
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
    if source.detail_fixture:
        detailed = []
        for item in items:
            try:
                if live:
                    page = http_get(item.url)
                else:
                    slug = urllib.parse.urlsplit(item.url).path.rstrip("/").rsplit("/", 1)[-1]
                    page = (FIXTURES_DIR / source.detail_fixture / f"{slug}.html").read_bytes()
            except Exception:  # noqa: BLE001 — keep the item with its title only
                detailed.append(item)
                continue
            detailed.append(with_details(item, page))
        items = detailed
    return raw_count, items


def default_since(days: int) -> date:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date()
