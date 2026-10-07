"""Data models: registry (Institution, Series), events (RawEvent, Event), roster, matches.

See PLAN.md §4.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, ClassVar, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class SeriesType(StrEnum):
    colloquium = "colloquium"
    seminar = "seminar"
    lecture = "lecture"
    other = "other"


#: Series types whose talks are invited by construction (PLAN.md §2, "Invited").
INVITED_TYPES = frozenset({SeriesType.colloquium, SeriesType.seminar, SeriesType.lecture})


class AdapterName(StrEnum):
    ical = "ical"
    localist = "localist"
    tribe = "tribe"
    indico = "indico"
    rss = "rss"
    html = "html"
    browser = "browser"
    #: Northwestern PlanIt Purple XML feed (xmlfeed?cal=ID&start=&end=)
    planitpurple = "planitpurple"
    #: No feasible adapter; ``notes`` must give the reason (PLAN.md §0.3, M1).
    unsupported = "unsupported"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- registry


class Series(_Strict):
    id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1)
    type: SeriesType
    #: ``None`` means "derive from type"; use :attr:`is_invited`.
    invited: bool | None = None
    url: str = Field(pattern=r"^https?://")
    adapter: AdapterName
    params: dict[str, Any] = Field(default_factory=dict)
    domains: list[str] = Field(min_length=1)
    keeps_past_events: bool | Literal["unknown"] = "unknown"
    active: bool = True
    #: True once the feed/adapter assignment has been confirmed against the live site
    #: (e.g. with ``talk-tracker probe``); False for survey assignments made from search.
    verified: bool = False
    notes: str = ""

    @property
    def is_invited(self) -> bool:
        if self.invited is not None:
            return self.invited
        return self.type in INVITED_TYPES

    @model_validator(mode="after")
    def _unsupported_needs_reason(self) -> Series:
        if self.adapter is AdapterName.unsupported and not self.notes.strip():
            raise ValueError("adapter 'unsupported' requires a reason in 'notes'")
        return self


class Institution(_Strict):
    id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1)
    country: str = Field(pattern=r"^[A-Z]{2}$")
    timezone: str
    series: list[Series] = Field(min_length=1)

    @field_validator("timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA timezone {v!r}") from exc
        return v

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


# --------------------------------------------------------------------------- events


class RawEvent(BaseModel):
    """What an adapter returns: one listing, minimally interpreted."""

    model_config = ConfigDict(extra="forbid")

    series_id: str
    start: datetime
    end: datetime | None = None
    all_day: bool = False
    title: str
    speaker_raw: str | None = None
    abstract: str | None = None
    url: str | None = None
    location: str | None = None
    source_uid: str | None = None
    cancelled: bool = False

    @field_validator("start", "end")
    @classmethod
    def _aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("datetimes must be timezone-aware")
        return v


ABSTRACT_MAX = 2000


def normalize_title(title: str) -> str:
    return " ".join(title.casefold().split())


def make_event_id(series_id: str, start_date: date, title: str) -> str:
    """sha1(series_id + start date + normalized title) — PLAN.md §4.3."""
    key = f"{series_id}|{start_date.isoformat()}|{normalize_title(title)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


class Event(BaseModel):
    """Archive record (PLAN.md §4.3)."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    series_id: str
    institution_id: str
    start: datetime
    speaker_raw: str | None = None
    speaker_name: str | None = None
    speaker_affiliation: str | None = None
    title: str
    abstract: str | None = Field(default=None, max_length=ABSTRACT_MAX)
    url: str
    adapter: AdapterName
    first_seen: datetime
    last_seen: datetime
    content_hash: str
    cancelled: bool = False

    #: Fields whose change counts as an edit of the listing.
    CONTENT_FIELDS: ClassVar[tuple[str, ...]] = (
        "start",
        "speaker_raw",
        "speaker_name",
        "speaker_affiliation",
        "title",
        "abstract",
        "url",
        "cancelled",
    )

    @staticmethod
    def compute_content_hash(fields: dict[str, Any]) -> str:
        payload = json.dumps(
            {k: fields.get(k) for k in Event.CONTENT_FIELDS},
            sort_keys=True,
            default=str,
            ensure_ascii=False,
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- roster


class Role(StrEnum):
    member = "member"
    joint = "joint"
    postdoc = "postdoc"
    student = "student"
    former = "former"


class RosterEntry(BaseModel):
    """One person, supplied at run time (PLAN.md §4.2). Never committed."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(min_length=1)
    role: Role
    orcid: str | None = None
    institution: str | None = None
    #: Extra name variants, added to the generated ones.
    variants: list[str] = Field(default_factory=list)
    associated_with: list[str] = Field(default_factory=list)
    #: Known different people with similar names (collisions).
    not_: list[str] = Field(default_factory=list, alias="not")

    @field_validator("orcid")
    @classmethod
    def _orcid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from .roster import validate_orcid  # local import avoids a cycle

        return validate_orcid(v)


class Roster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[RosterEntry]

    def by_role(self) -> dict[Role, int]:
        counts = {r: 0 for r in Role}
        for e in self.entries:
            counts[e.role] += 1
        return counts


# --------------------------------------------------------------------------- matches


class Confidence(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    person: str
    role: Role
    confidence: Confidence
    matched_field: Literal["speaker_name", "speaker_raw", "title", "abstract"]
    matched_text: str
    reason: str
