"""Fetch policy shared by the probe and (from M2) the scraper.

robots.txt is respected, with one documented exception (PLAN.md §0.8): *public calendar
feeds*. These are iCalendar URLs that a calendar owner publishes so that calendar clients
can subscribe to them. Their hosts disallow them in robots.txt, which is aimed at crawlers,
but calendar clients fetch them routinely. The exception is limited to the URL shapes
below. Each still gets the normal rate limit, a single GET, and the project user agent.
"""

from __future__ import annotations

import re

PUBLIC_CALENDAR_FEEDS: tuple[re.Pattern[str], ...] = (
    # Google Calendar public feed: /calendar/ical/<calendar id>/public/basic.ics
    re.compile(r"^https://calendar\.google\.com/calendar/ical/[^/?#]+/public/(?:basic|full)\.ics$"),
    # Outlook / Microsoft 365 published calendar
    re.compile(
        r"^https://outlook\.(?:office365|office|live)\.com/owa/calendar/[^?#]+/calendar\.ics$"
    ),
)


def is_public_calendar_feed(url: str) -> bool:
    """True if ``url`` is a published calendar feed exempt from robots.txt."""
    return any(p.match(url) for p in PUBLIC_CALENDAR_FEEDS)
