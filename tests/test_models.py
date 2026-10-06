from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from talk_tracker.models import Event, RawEvent, Series, make_event_id


def test_event_id_stable_and_title_normalised():
    a = make_event_id("x-colloq", date(2026, 9, 12), "Dark  Matter at  Scale")
    b = make_event_id("x-colloq", date(2026, 9, 12), "dark matter at scale ")
    assert a == b and len(a) == 40
    assert a != make_event_id("x-colloq", date(2026, 9, 13), "Dark Matter at Scale")
    assert a != make_event_id("y-colloq", date(2026, 9, 12), "Dark Matter at Scale")


def test_content_hash_changes_with_content():
    base = {"title": "T", "speaker_raw": "Jane Example (Example U)", "start": "2026-09-12"}
    h1 = Event.compute_content_hash(base)
    assert h1 == Event.compute_content_hash(dict(base, ignored_field="x"))
    assert h1 != Event.compute_content_hash(dict(base, speaker_raw="Tom Placeholder"))


def test_raw_event_requires_aware_datetime():
    with pytest.raises(ValidationError, match="timezone-aware"):
        RawEvent(series_id="x", start=datetime(2026, 9, 12, 16), title="T")
    RawEvent(series_id="x", start=datetime(2026, 9, 12, 16, tzinfo=UTC), title="T")


def test_series_is_frozen():
    s = Series(
        id="x-c",
        name="C",
        type="colloquium",
        url="https://a.example.org",
        adapter="ical",
        domains=["a.example.org"],
    )
    with pytest.raises(ValidationError):
        s.name = "other"
