from __future__ import annotations

import io
import json

import pytest

from talk_tracker.models import Role
from talk_tracker.roster import (
    RosterError,
    check_roster,
    load_roster,
    name_variants,
    normalize_name,
    orcid_checksum_ok,
    parse_roster_text,
)

from .conftest import FIXTURES

PEOPLE = FIXTURES / "people"


@pytest.fixture(scope="module")
def group():
    return load_roster(PEOPLE / "fictional_group.txt")


def _get(roster, name):
    (e,) = [e for e in roster.entries if e.name == name]
    return e


def test_roles_and_counts(group):
    assert {r: n for r, n in group.by_role().items()} == {
        Role.member: 3,
        Role.joint: 1,
        Role.postdoc: 1,
        Role.student: 2,
        Role.former: 1,
    }
    # preamble, "Projects" line and conflicts section produce no entries
    assert len(group.entries) == 8


def test_entry_fields(group):
    e = _get(group, "C. Robin Testcase")
    assert e.role is Role.joint
    assert e.institution == "Example State University"
    assert e.orcid == "0000-0001-2222-2227"
    assert _get(group, "Lee Dummy").orcid is None  # "ORCID not listed"
    assert _get(group, "Lee Dummy").institution is None
    assert _get(group, "Pat Stub").orcid is None
    assert _get(group, "Rosa Núñez-Ríos").orcid == "0000-0001-0000-0009"


def test_conflicts_parsed(group):
    assert _get(group, "Tom Placeholder").not_ == ["Tim Placeholder", "Thomas R. Placeholder"]
    assert _get(group, "Lee Dummy").not_ == ["Lea Dummy", "Leon K. Dummy"]
    assert _get(group, "Pat Stub").not_ == []  # free-text note, not a name


def test_check_clean(group):
    assert check_roster(group) == []


def test_normalize_name():
    assert normalize_name("  Rosa Núñez-Ríos ") == "rosa nunez rios"
    assert normalize_name("NÚÑEZ–RÍOS, R.") == "nunez rios r"
    assert normalize_name("Kim O'Mock") == "kim o'mock"


def test_variants_middle_initial():
    v = name_variants("Jane Q. Example")
    assert {"jane q example", "jane example", "example jane"} <= v.full
    assert v.initials == {"j example", "j q example"}
    assert v.surnames == {"example"}


def test_variants_initial_first():
    v = name_variants("C. Robin Testcase")
    assert "robin testcase" in v.full
    assert {"c testcase", "c r testcase", "r testcase"} == v.initials


def test_variants_accents_hyphens():
    v = name_variants("Rosa Núñez-Ríos")
    assert "rosa nunez rios" in v.full
    assert "r nunez rios" in v.initials
    assert v.surnames == {"nunez rios"}


def test_variants_extra():
    v = name_variants("Jane Q. Example", ["J. Q. Example-Smith", "Janie Example"])
    assert "j q example smith" in v.initials
    assert "janie example" in v.full


def test_variants_need_two_tokens():
    with pytest.raises(ValueError):
        name_variants("Cher")


def test_orcid_checksum():
    assert orcid_checksum_ok("0000-0002-1825-0097")
    assert not orcid_checksum_ok("0000-0002-1825-0098")


def test_bad_orcid_reports_line():
    text = "Current Group Members:\n* Jane Example (0000-0002-1825-0098)\n"
    with pytest.raises(RosterError, match=r"line 2: Jane Example: .*checksum"):
        parse_roster_text(text)


def test_conflict_for_unknown_person():
    text = "Current Group Members:\n* Jane Example\nKnown Name Conflicts:\n* Nobody Here: X Y\n"
    with pytest.raises(RosterError, match="unknown person"):
        parse_roster_text(text)


def test_empty_roster():
    with pytest.raises(RosterError, match="no roster entries"):
        parse_roster_text("Just a paragraph of text.\n")


def test_bullets_outside_sections_ignored():
    text = "Notes:\n* Not A Person\nAffiliated Students:\n- Lee Dummy\n• Kim Mock\n"
    r = parse_roster_text(text)
    assert [(e.name, e.role) for e in r.entries] == [
        ("Lee Dummy", Role.student),
        ("Kim Mock", Role.student),
    ]


def test_yaml_roster():
    r = load_roster(PEOPLE / "fictional_roster.yaml")
    e = r.entries[0]
    assert e.not_ == ["Jake Example"] and e.orcid == "0000-0002-1825-0097"
    assert check_roster(r) == []


def test_json_roster_and_autodetect():
    data = {"entries": [{"name": "Jane Example", "role": "postdoc", "not": ["J. Other"]}]}
    r = parse_roster_text(json.dumps(data))
    assert r.entries[0].role is Role.postdoc


def test_yaml_autodetect():
    r = parse_roster_text("- name: Jane Example\n  role: former\n")
    assert r.entries[0].role is Role.former


def test_structured_errors():
    with pytest.raises(RosterError):
        parse_roster_text('[{"name": "Jane Example", "role": "boss"}]')
    with pytest.raises(RosterError):
        parse_roster_text('{"people": []}')


def test_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("Former Members:\n* Pat Stub\n"))
    assert load_roster("-").entries[0].name == "Pat Stub"


def test_check_problems():
    text = (
        "Current Group Members:\n* Jane Example (0000-0002-1825-0097)\n"
        "Former Members:\n* Jane Example\n* John Other (0000-0002-1825-0097)\n"
    )
    problems = check_roster(parse_roster_text(text))
    assert any("duplicate person" in p for p in problems)
    assert any("ORCID 0000-0002-1825-0097 shared" in p for p in problems)
    r = parse_roster_text('[{"name": "A B", "role": "student", "associated_with": ["C D"]}]')
    assert any("not in the roster" in p for p in check_roster(r))
