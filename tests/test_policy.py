from __future__ import annotations

import pytest

from talk_tracker.policy import is_public_calendar_feed
from talk_tracker.probe import Fetcher


@pytest.mark.parametrize(
    "url, ok",
    [
        (
            "https://calendar.google.com/calendar/ical/abc%40group.calendar.google.com/public/basic.ics",
            True,
        ),
        (
            "https://calendar.google.com/calendar/ical/abc%40group.calendar.google.com/public/full.ics",
            True,
        ),
        ("https://outlook.office365.com/owa/calendar/abc@example.org/def/calendar.ics", True),
        # private feeds, other paths and look-alike hosts are not exempt
        ("https://calendar.google.com/calendar/ical/abc/private-0123/basic.ics", False),
        ("https://calendar.google.com/calendar/embed?src=abc", False),
        ("https://calendar.google.com.example.net/calendar/ical/abc/public/basic.ics", False),
        ("http://calendar.google.com/calendar/ical/abc/public/basic.ics", False),
        ("https://www.example.org/events.ics", False),
    ],
)
def test_public_calendar_feed(url, ok):
    assert is_public_calendar_feed(url) is ok


def test_fetcher_skips_robots_for_public_feeds(monkeypatch):
    f = Fetcher(delay=0)

    def no_network(*a, **k):
        raise AssertionError("robots.txt must not be fetched for exempt feeds")

    monkeypatch.setattr(f, "_get", no_network)
    url = (
        "https://calendar.google.com/calendar/ical/abc%40group.calendar.google.com/public/basic.ics"
    )
    assert f.allowed(url) is True
