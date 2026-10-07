from __future__ import annotations

from talk_tracker.models import Series
from talk_tracker.probe import (
    Feed,
    classify_body,
    detect,
    gcal_ics_url,
    probe_series,
    render_markdown,
)

from .conftest import FIXTURES

P = FIXTURES / "probe"


def _detect(name, url="https://www.example.org/events/"):
    return detect((P / name).read_text(), url)


def _kinds(det):
    return {(f.kind, f.url) for f in det.feeds}


def test_wordpress_tribe():
    d = _detect("wordpress_tribe.html", "https://events.example.org/colloquium/")
    assert "WordPress" in d.platforms and "WordPress: The Events Calendar" in d.platforms
    k = _kinds(d)
    assert ("tribe", "https://events.example.org/wp-json/tribe/events/v1/events") in k
    assert ("ical", "https://events.example.org/events/?ical=1") in k
    assert ("rss", "https://events.example.org/feed/") in k
    assert d.suggested_adapter == "tribe"


def test_google_calendar_embed():
    d = _detect("gcal_embed.html")
    assert "Drupal" in d.platforms
    url = "https://calendar.google.com/calendar/ical/abc123def%40group.calendar.google.com/public/basic.ics"
    assert ("ical", url) in _kinds(d)
    assert d.suggested_adapter == "ical"


def test_gcal_cid_that_is_a_url():
    assert gcal_ics_url(
        "https://calendar.google.com/calendar/render?cid=http%3A%2F%2Fx.example.org%2Fa.ics"
    ) == ["http://x.example.org/a.ics"]


def test_indico_and_researchseminars():
    d = _detect("indico_link.html")
    k = _kinds(d)
    assert ("indico", "https://indico.example.com/export/categ/1432.json") in k
    assert ("ical", "https://indico.example.com/category/1432/events.ics") in k
    assert ("ical", "https://researchseminars.org/seminar/EXAMPLESEM/ics") in k
    assert d.suggested_adapter == "indico"


def test_planitpurple_umich_webcal():
    d = _detect("planitpurple_umich.html")
    k = _kinds(d)
    assert (
        "planitpurple",
        "https://planitpurple.northwestern.edu/xmlfeed?cal=3758&days=0",
    ) in k
    assert ("ical", "https://events.umich.edu/group/3804/ical") in k
    assert ("ical", "https://www.example.org/calendar/colloquium-12?ical") in k


def test_localist():
    d = _detect("localist.html", "https://events.example.edu/event/x")
    assert "Localist" in d.platforms
    assert ("localist", "https://events.example.edu/api/2/events") in _kinds(d)
    assert d.suggested_adapter == "localist"


def test_js_shell():
    d = _detect("js_shell.html")
    assert d.js_rendered and d.suggested_adapter == "browser"


def test_failed_feed_check_is_skipped_in_suggestion():
    d = _detect("indico_link.html")
    for f in d.feeds:
        if f.kind == "indico":
            f.check = "HTTP 403"
    from talk_tracker.probe import suggest_adapter

    assert suggest_adapter(d) == "ical"


def test_classify_body():
    assert classify_body(b"BEGIN:VCALENDAR\nBEGIN:VEVENT\nEND:VEVENT\n", "") == "ok ical (1 events)"
    assert classify_body(b'{"events": [1, 2]}', "application/json") == "ok json (2 items)"
    assert (
        classify_body(b"<?xml version='1.0'?><rss><item/><item/></rss>", "") == "ok xml (2 items)"
    )
    assert classify_body(b"<!doctype html><html>", "text/html") == "html (not a feed)"


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url in self.pages:
            return 200, self.pages[url], ""
        return 404, b"", ""


def _series(**kw):
    base = dict(
        id="x-colloq",
        name="C",
        type="colloquium",
        url="https://www.example.org/events/",
        adapter="html",
        params={},
        domains=["www.example.org"],
    )
    base.update(kw)
    return Series(**base)


def test_probe_series_checks_feeds():
    page = (P / "indico_link.html").read_bytes()
    fetcher = FakeFetcher(
        {
            "https://www.example.org/events/": page,
            "https://indico.example.com/export/categ/1432.json": b'{"results": [{}, {}]}',
        }
    )
    r = probe_series(_series(), fetcher)
    checks = {f.kind: f.check for f in r.detection.feeds}
    assert checks["indico"] == "ok json (2 items)"
    assert r.detection.suggested_adapter == "indico"
    md = render_markdown([r])
    assert "x-colloq | html | indico ⚠" in md


def test_probe_series_registry_feed_and_http_error():
    fetcher = FakeFetcher({"https://www.example.org/events/": b"<html><body>hi</body></html>"})
    s = _series(params={"ics_url": "https://cal.example.org/a.ics"}, domains=["cal.example.org"])
    r = probe_series(s, fetcher)
    assert r.detection.feeds == [
        Feed("ical", "https://cal.example.org/a.ics", "registry ics_url", "HTTP 404")
    ]
    r = probe_series(_series(url="https://www.example.org/missing"), fetcher)
    assert r.error == "HTTP 404" and r.detection is None
    assert "HTTP 404" in render_markdown([r])
