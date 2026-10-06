"""Adapter protocol shared by all platform adapters (PLAN.md §5.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from ..models import RawEvent, Series


class AdapterError(RuntimeError):
    """An adapter failed for one series. Recorded in the run log; never swallowed.

    Adapters must raise this (or a subclass) rather than return an empty list when a
    fetch or parse fails, so that "no events" and "broken feed" stay distinguishable.
    """

    def __init__(self, series_id: str, message: str):
        self.series_id = series_id
        super().__init__(f"{series_id}: {message}")


@runtime_checkable
class Adapter(Protocol):
    name: str

    def fetch(self, series: Series, start: datetime, end: datetime) -> list[RawEvent]:
        """Return events of ``series`` starting in ``[start, end)``."""
        ...
