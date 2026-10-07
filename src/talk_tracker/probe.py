"""Survey helper: detect the calendar platform and machine-readable feeds of a series page.

``talk-tracker probe`` fetches each series' human-facing ``url`` and reports:

* the CMS / calendar platform (generator meta tag and platform fingerprints);
* candidate feeds found in the page (``<link rel=alternate>``, ``.ics``/``webcal:`` links,
  Google Calendar embeds, Indico categories, PlanIt Purple calendars, Happening @ Michigan
  groups, Localist, WordPress *The Events Calendar* REST API, ...);
* optionally, whether each candidate feed actually returns iCal / JSON / XML.

It is a survey tool (milestone M1): it reads at most a few URLs per series, sequentially,
honouring ``robots.txt`` and a minimum delay per host. It never writes the registry; the
report is for a human to confirm or correct the adapter assignments and set
``verified: true``.

Detection is split into pure functions on HTML text (unit-tested on fixtures) and a thin
network layer using the standard library.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit

from . import __version__

USER_AGENT = f"talk-tracker/{__version__} (+https://github.com/fnal-cpc/talk-tracker; survey probe)"
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "text/calendar;q=0.9,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
}
MIN_DELAY_S = 2.0
TIMEOUT_S = 20.0
MAX_BYTES = 3_000_000
MAX_CHECKS_PER_KIND = 3
MAX_FEEDS = 12

# --------------------------------------------------------------------------- HTML scan


class _Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []  # <link ...>
        self.anchors: list[str] = []  # <a href>
        self.iframes: list[str] = []  # <iframe src>
        self.scripts: list[str] = []  # <script src>
        self.meta: dict[str, str] = {}
        self.text_chars = 0
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "link":
            self.links.append(a)
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
        elif tag == "iframe" and a.get("src"):
            self.iframes.append(a["src"])
        elif tag == "script":
            if a.get("src"):
                self.scripts.append(a["src"])
            self._skip += 1
        elif tag == "style":
            self._skip += 1
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.text_chars += len(data.strip())


@dataclass
class Feed:
    kind: str  # ical | rss | atom | json | indico | planitpurple | tribe | localist | ...
    url: str
    source: str  # how it was found
    check: str | None = None  # result of --check-feeds


@dataclass
class Detection:
    generator: str | None = None
    platforms: list[str] = field(default_factory=list)
    feeds: list[Feed] = field(default_factory=list)
    suggested_adapter: str | None = None
    js_rendered: bool = False
    notes: list[str] = field(default_factory=list)

    def add_feed(self, kind: str, url: str, source: str) -> None:
        if len(self.feeds) >= MAX_FEEDS:
            return
        if all(f.url != url for f in self.feeds):
            self.feeds.append(Feed(kind, url, source))

    def add_platform(self, name: str) -> None:
        if name not in self.platforms:
            self.platforms.append(name)


_GCAL_SRC = re.compile(r"calendar\.google\.com/calendar/(?:u/\d+/)?(?:embed|r)\?[^\"'\s<>]*")
_ICS_HREF = re.compile(r"(\.ics\b|[?&]ical\b|/ical\b|webcal:|/ics\b|outputformat=ical)", re.I)
_INDICO_CATEG = re.compile(r"/categor(?:y|yDisplay\.py\?categId=)/?(\d+)")
_PPURPLE_CAL = re.compile(r"planitpurple\.northwestern\.edu/(?:calendar/|xmlfeed\?cal=)(\d+)")
_UMICH_GROUP = re.compile(r"events\.umich\.edu/group/(\d+)")
_RSEM = re.compile(r"researchseminars\.org/seminar/([A-Za-z0-9_]+)")
#: links that are never event feeds (WordPress comment feeds, REST page/post objects)
_NOT_EVENTS = re.compile(r"/comments/feed/?$|/wp-json/wp/v2/|/wp-json/?$|/oembed", re.I)
#: WordPress site-wide posts feed (/feed/ at the end of a path): news, not events
_SITE_FEED = re.compile(r"/feed/?$", re.I)


def _abs(base: str, href: str) -> str:
    if href.lower().startswith("webcal://"):
        href = "https://" + href[len("webcal://") :]
    return urljoin(base, href)


def gcal_ics_url(embed_url: str) -> list[str]:
    """Public iCal URLs for the calendars in a Google Calendar embed/render URL."""
    qs = parse_qs(urlsplit(embed_url.replace("&amp;", "&")).query)
    ids = qs.get("src", []) + qs.get("cid", [])
    out = []
    for cid in ids:
        cid = unquote(cid)
        if cid.startswith("http"):  # cid can itself be an ics URL
            out.append(cid)
        else:
            out.append(
                f"https://calendar.google.com/calendar/ical/{quote(cid, safe='')}/public/basic.ics"
            )
    return out


def detect(html: str, page_url: str) -> Detection:
    """Inspect a page's HTML and return platform and feed candidates (no network)."""
    scan = _Scan()
    scan.feed(html)
    det = Detection()
    host = (urlsplit(page_url).hostname or "").lower()
    origin = f"{urlsplit(page_url).scheme}://{urlsplit(page_url).netloc}"
    low = html.lower()

    gen = scan.meta.get("generator")
    if gen:
        det.generator = gen
        for name in ("WordPress", "Drupal", "Joomla", "ExpressionEngine", "Hugo", "Jekyll"):
            if name.lower() in gen.lower():
                det.add_platform(name)

    # <link rel="alternate" ...>
    for ln in scan.links:
        if _NOT_EVENTS.search(ln.get("href", "")):
            continue
        rel = ln.get("rel", "").lower()
        typ = ln.get("type", "").lower()
        href = ln.get("href", "")
        if "alternate" in rel and href:
            if "calendar" in typ:
                det.add_feed("ical", _abs(page_url, href), "<link rel=alternate>")
            elif "rss" in typ:
                kind = "site-rss" if _SITE_FEED.search(href) else "rss"
                det.add_feed(kind, _abs(page_url, href), "<link rel=alternate>")
            elif "atom" in typ:
                det.add_feed("atom", _abs(page_url, href), "<link rel=alternate>")
            elif "json" in typ and "oembed" not in typ:
                det.add_feed("json", _abs(page_url, href), "<link rel=alternate>")
        if "api.w.org" in rel:
            det.add_platform("WordPress")

    # anchors and iframes
    for href in scan.anchors + scan.iframes:
        full = _abs(page_url, href)
        if _ICS_HREF.search(href) and not href.startswith("mailto:"):
            det.add_feed("ical", full, "link")
        if "calendar.google.com" in href:
            for ics in gcal_ics_url(full):
                det.add_feed("ical", ics, "Google Calendar embed/link")
            det.add_platform("Google Calendar")
        m = _INDICO_CATEG.search(full)
        if m and "indico" in (urlsplit(full).hostname or ""):
            ih = urlsplit(full)
            base = f"{ih.scheme}://{ih.netloc}"
            det.add_feed("indico", f"{base}/export/categ/{m.group(1)}.json", "Indico category link")
            det.add_platform("Indico")
        m = _PPURPLE_CAL.search(full)
        if m:
            det.add_feed(
                "planitpurple",
                f"https://planitpurple.northwestern.edu/xmlfeed?cal={m.group(1)}&days=0",
                "PlanIt Purple calendar link",
            )
            det.add_platform("PlanIt Purple")
        m = _UMICH_GROUP.search(full)
        if m:
            det.add_feed(
                "ical", f"https://events.umich.edu/group/{m.group(1)}/ical", "Happening @ Michigan"
            )
            det.add_platform("Happening @ Michigan")
        m = _RSEM.search(full)
        if m:
            det.add_feed(
                "ical", f"https://researchseminars.org/seminar/{m.group(1)}/ics", "researchseminars"
            )
        if re.search(r"/feed/?$|/rss/?$|[?&]feed=rss", href, re.I) and not _NOT_EVENTS.search(href):
            det.add_feed("site-rss" if _SITE_FEED.search(href) else "rss", full, "link")

    # Google Calendar ids embedded in scripts/data attributes
    for m in _GCAL_SRC.finditer(html):
        for ics in gcal_ics_url("https://" + m.group(0)):
            det.add_feed("ical", ics, "Google Calendar embed")
        det.add_platform("Google Calendar")

    # platform fingerprints
    if "localist" in low:
        det.add_platform("Localist")
        det.add_feed("localist", f"{origin}/api/2/events", "Localist fingerprint")
    if "tribe-events" in low or "tribe-bar" in low or "/wp-json/tribe/" in low:
        det.add_platform("WordPress: The Events Calendar")
        det.add_feed("tribe", f"{origin}/wp-json/tribe/events/v1/events", "tribe fingerprint")
    if "livewhale" in low or "/live/json/" in low or "/live/ical/" in low:
        det.add_platform("LiveWhale")
    if "trumba.com" in low or "$trumba" in low:
        det.add_platform("Trumba")
    if "indico" in host:
        det.add_platform("Indico")
        m = _INDICO_CATEG.search(urlsplit(page_url).path)
        if m:
            det.add_feed("indico", f"{origin}/export/categ/{m.group(1)}.json", "Indico page")
    if "planitpurple" in host:
        det.add_platform("PlanIt Purple")
        m = _PPURPLE_CAL.search(page_url)
        if m:
            det.add_feed(
                "planitpurple",
                f"https://planitpurple.northwestern.edu/xmlfeed?cal={m.group(1)}&days=0",
                "PlanIt Purple page",
            )
    if "researchseminars.org" in host:
        m = _RSEM.search(page_url)
        if m:
            det.add_feed(
                "ical", f"https://researchseminars.org/seminar/{m.group(1)}/ics", "researchseminars"
            )

    # JS-rendered heuristic: little visible text, several scripts
    if scan.text_chars < 400 and len(scan.scripts) >= 3:
        det.js_rendered = True
        det.notes.append("little server-rendered text: page may need the browser adapter")

    det.suggested_adapter = suggest_adapter(det)
    return det


_PREFERENCE = ["indico", "planitpurple", "localist", "tribe", "ical", "json", "rss", "atom"]
_ADAPTER_FOR = {
    "indico": "indico",
    "planitpurple": "planitpurple",
    "localist": "localist",
    "tribe": "tribe",
    "ical": "ical",
    "rss": "rss",
    "atom": "rss",
}


def suggest_adapter(det: Detection) -> str:
    """Pick the most structured adapter among the candidates (checked feeds first)."""

    def usable(f: Feed) -> bool:
        if f.check is None:
            return True
        # a .ics with exactly one event is a per-event "add to calendar" link, not a feed
        return f.check.startswith("ok") and "(1 events)" not in f.check

    # a registry-configured source that checks out wins: the assignment is confirmed
    for f in det.feeds:
        if f.source.startswith("registry") and f.check and usable(f) and f.kind in _ADAPTER_FOR:
            return _ADAPTER_FOR[f.kind]
    for kind in _PREFERENCE:
        for f in det.feeds:
            if f.kind == kind and usable(f) and kind in _ADAPTER_FOR:
                return _ADAPTER_FOR[kind]
    return "browser" if det.js_rendered else "html"


# --------------------------------------------------------------------------- network


class Fetcher:
    """Sequential stdlib fetcher with robots.txt and a per-host delay."""

    def __init__(self, delay: float = MIN_DELAY_S, timeout: float = TIMEOUT_S):
        self.delay = delay
        self.timeout = timeout
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            dt = time.monotonic() - last
            if dt < self.delay:
                time.sleep(self.delay - dt)
        self._last[host] = time.monotonic()

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        key = f"{parts.scheme}://{parts.netloc}"
        if key not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                status, body, _ = self._get(f"{key}/robots.txt", check_robots=False)
                rp.parse(body.decode("utf-8", "replace").splitlines() if status == 200 else [])
            except (OSError, urllib.error.URLError):
                rp = None  # robots.txt unreachable: be permissive, as browsers are
            self._robots[key] = rp
        rp = self._robots[key]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def _get(self, url: str, check_robots: bool = True) -> tuple[int, bytes, str]:
        if check_robots and not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        self._wait(urlsplit(url).netloc)
        req = urllib.request.Request(url, headers=REQUEST_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                return resp.status, resp.read(MAX_BYTES), ctype
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(MAX_BYTES) if exc.fp else b"", ""

    def get(self, url: str) -> tuple[int, bytes, str]:
        return self._get(url)


def classify_body(body: bytes, ctype: str) -> str:
    """Describe what a feed URL returned, e.g. ``ok ical (12 events)``."""
    head = body[:2000].lstrip()
    text = body.decode("utf-8", "replace")
    if head.startswith(b"BEGIN:VCALENDAR"):
        return f"ok ical ({text.count('BEGIN:VEVENT')} events)"
    if head[:1] in (b"{", b"["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return "bad json"
        n = None
        if isinstance(data, list):
            n = len(data)
        elif isinstance(data, dict):
            for k in ("events", "results", "items"):
                if isinstance(data.get(k), list):
                    n = len(data[k])
                    break
        return f"ok json ({n} items)" if n is not None else "ok json"
    if head.startswith(b"<?xml") or head.startswith(b"<rss") or head.startswith(b"<feed"):
        n = len(re.findall(r"<(item|entry|event)\b", text))
        return f"ok xml ({n} items)"
    if b"<html" in head.lower() or "html" in ctype:
        return "html (not a feed)"
    return f"unknown content ({ctype or 'no content-type'})"


def _feed_test_url(f: Feed) -> str:
    if f.kind == "tribe":
        return f.url + "?per_page=5"
    if f.kind == "localist":
        return f.url + "?pp=5"
    return f.url


@dataclass
class ProbeResult:
    series_id: str
    url: str
    registry_adapter: str
    status: int | None = None
    error: str | None = None
    detection: Detection | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def registry_sources(series) -> list[Feed]:
    """The source(s) the registry entry already configures, as checkable feeds."""
    p = series.params
    a = str(series.adapter)
    out: list[Feed] = []
    if a == "indico" and "base_url" in p and "category" in p:
        out.append(Feed("indico", f"{p['base_url']}/export/categ/{p['category']}.json", "registry"))
    elif a == "planitpurple" and "base_url" in p and "cal" in p:
        out.append(
            Feed("planitpurple", f"{p['base_url']}/xmlfeed?cal={p['cal']}&days=0", "registry")
        )
    elif a == "tribe" and "base_url" in p:
        out.append(Feed("tribe", f"{p['base_url']}/wp-json/tribe/events/v1/events", "registry"))
    elif a == "localist" and "base_url" in p:
        out.append(Feed("localist", f"{p['base_url']}/api/2/events", "registry"))
    for key, val in p.items():
        if isinstance(val, str) and val.startswith("http") and key.endswith(("ics_url", "rss_url")):
            out.append(Feed("ical" if key.endswith("ics_url") else "rss", val, f"registry {key}"))
    return out


def _error_text(exc: BaseException) -> str:
    if isinstance(exc, PermissionError):
        return "blocked by robots.txt"
    return f"{type(exc).__name__}: {exc}"


def probe_series(series, fetcher: Fetcher, check_feeds: bool = True) -> ProbeResult:
    res = ProbeResult(series.id, series.url, str(series.adapter))
    det = Detection()
    try:
        status, body, _ctype = fetcher.get(series.url)
        res.status = status
        if status >= 400:
            res.error = f"HTTP {status}"
        else:
            det = detect(body.decode("utf-8", "replace"), series.url)
    except (OSError, urllib.error.URLError, PermissionError) as exc:
        res.error = _error_text(exc)
    # the registry's configured source is checked first, whatever the page did
    det.feeds = [*registry_sources(series), *det.feeds]
    if res.error and not det.feeds:
        return res
    if check_feeds:
        checked: dict[str, int] = {}
        for f in det.feeds:
            if f.kind == "site-rss":
                continue
            checked[f.kind] = checked.get(f.kind, 0) + 1
            if checked[f.kind] > MAX_CHECKS_PER_KIND and not f.source.startswith("registry"):
                f.check = None
                continue
            try:
                st, fb, fct = fetcher.get(_feed_test_url(f))
                f.check = classify_body(fb, fct) if st < 400 else f"HTTP {st}"
            except (OSError, urllib.error.URLError, PermissionError) as exc:
                f.check = _error_text(exc)
    det.suggested_adapter = suggest_adapter(det)
    res.detection = det
    return res


def render_markdown(results: list[ProbeResult]) -> str:
    lines = [
        "| series | registry | suggested | platform | feeds (check) | notes |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.detection is None:
            lines.append(f"| {r.series_id} | {r.registry_adapter} | – | – | – | page: {r.error} |")
            continue
        d = r.detection
        notes = ([f"page: {r.error}"] if r.error else []) + d.notes
        feeds = "<br>".join(f"{f.kind}: {f.url} ({f.check or 'unchecked'})" for f in d.feeds)
        plat = ", ".join(filter(None, [*d.platforms, d.generator])) or "?"
        flag = "" if d.suggested_adapter == r.registry_adapter else " ⚠"
        lines.append(
            f"| {r.series_id} | {r.registry_adapter} | {d.suggested_adapter}{flag} | {plat} "
            f"| {feeds or '–'} | {'; '.join(notes)} |"
        )
    return "\n".join(lines) + "\n"
