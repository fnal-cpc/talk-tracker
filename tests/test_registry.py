from __future__ import annotations

import pytest
import yaml

from talk_tracker.registry import RegistryError, load_registry

from .conftest import FIXTURES, REPO


def _inst(**overrides):
    series = {
        "id": "demo-colloq",
        "name": "Colloquium",
        "type": "colloquium",
        "url": "https://demo.example.org/colloq",
        "adapter": "ical",
        "params": {"ics_url": "https://cal.example.org/c.ics"},
        "domains": ["cal.example.org"],
    }
    series.update(overrides.pop("series", {}))
    data = {
        "id": "demo",
        "name": "Demo U",
        "country": "US",
        "timezone": "America/New_York",
        "series": [series],
    }
    data.update(overrides)
    return yaml.safe_dump(data, sort_keys=False)


def _problems(make_registry, text, name="demo.yaml"):
    with pytest.raises(RegistryError) as exc:
        load_registry(make_registry({name: text}))
    return "\n".join(exc.value.problems)


def test_repo_registry_is_valid():
    reg = load_registry(REPO / "registry")
    assert isinstance(reg.institutions, tuple)


def test_fixture_registry_loads(make_registry):
    reg = load_registry(make_registry(from_fixture="valid"))
    assert [i.id for i in reg.institutions] == ["example-lab", "example-u"]
    assert reg.domains() == [
        "astro.example.org",
        "calendar.example.org",
        "events.example.org",
        "indico.example.com",
    ]
    assert "astro.example.org" not in reg.domains(active_only=True)
    _, s = reg.series_by_id("example-u-physics-colloquium")
    assert s.keeps_past_events is True


def test_invited_derivation(make_registry):
    reg = load_registry(make_registry(from_fixture="valid"))
    invited = {s.id: s.is_invited for _, s in reg.iter_series()}
    assert invited == {
        "example-lab-seminar": False,  # explicit override
        "example-u-physics-colloquium": True,
        "example-u-astro-seminar": True,
        "example-u-journal-club": False,  # type: other
    }


def test_minimal_valid(make_registry):
    reg = load_registry(make_registry({"demo.yaml": _inst()}))
    ((_, s),) = reg.iter_series()
    assert s.keeps_past_events == "unknown" and s.active is True


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"timezone": "Mars/Olympus"}, "unknown IANA timezone"),
        ({"country": "usa"}, "country"),
        ({"series": {"adapter": "llm"}}, "adapter"),
        ({"series": {"type": "conference"}}, "type"),
        ({"series": {"domains": []}}, "domains"),
        ({"series": {"domains": ["Cal.Example.org"]}}, "domains"),
        ({"series": {"surprise": 1}}, "Additional properties"),
        ({"series": {"adapter": "unsupported"}}, "notes"),
        ({"series": {"id": "other-colloq"}}, "must start with 'demo-'"),
        (
            {"series": {"params": {"ics_url": "https://elsewhere.example.net/x.ics"}}},
            "host 'elsewhere.example.net' is not listed",
        ),
        ({"series": {"params": {"feeds": [{"u": "http://x.example.net/a"}]}}}, "params.feeds[0].u"),
    ],
)
def test_invalid(make_registry, overrides, expected):
    assert expected in _problems(make_registry, _inst(**overrides))


def test_filename_must_match_id(make_registry):
    assert "does not match file name" in _problems(make_registry, _inst(), name="wrong.yaml")


def test_duplicate_series_ids(make_registry):
    text = _inst()
    data = yaml.safe_load(text)
    data["series"].append(dict(data["series"][0]))
    msg = _problems(make_registry, yaml.safe_dump(data))
    assert "duplicate series id" in msg


def test_invalid_yaml(make_registry):
    assert "invalid YAML" in _problems(make_registry, "id: [unclosed")


def test_all_problems_reported(make_registry):
    root = make_registry({"a.yaml": _inst(id="a"), "demo.yaml": _inst(timezone="Nowhere/X")})
    with pytest.raises(RegistryError) as exc:
        load_registry(root)
    assert len(exc.value.problems) >= 2


def test_missing_registry(tmp_path):
    with pytest.raises(RegistryError, match="schema not found"):
        load_registry(tmp_path)


def test_fixture_files_are_schema_examples():
    # guard: fixtures directory exists and contains only fictional example domains
    for p in (FIXTURES / "registry" / "valid" / "institutions").glob("*.yaml"):
        for d in yaml.safe_load(p.read_text())["series"]:
            assert all(dom.endswith((".example.org", ".example.com")) for dom in d["domains"])
