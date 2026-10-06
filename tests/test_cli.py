from __future__ import annotations

import pytest

from talk_tracker.cli import main

from .conftest import FIXTURES, REPO


def test_validate_repo_registry(capsys):
    assert main(["--registry", str(REPO / "registry"), "validate"]) == 0
    assert "registry OK" in capsys.readouterr().out


def test_validate_with_roster(make_registry, capsys):
    root = make_registry(from_fixture="valid")
    rc = main(
        [
            "--registry",
            str(root),
            "validate",
            "--roster",
            str(FIXTURES / "people" / "fictional_group.txt"),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "registry OK: 2 institution(s), 4 series (3 active), 4 domain(s)" in out
    assert "roster OK: 8 people (3 member, 1 joint, 1 postdoc, 2 student, 1 former)" in out
    assert "Placeholder" not in out  # names are not echoed


def test_validate_bad_roster(make_registry, tmp_path, capsys):
    bad = tmp_path / "group.txt"
    bad.write_text("Current Group Members:\n* Jane Example (0000-0002-1825-0098)\n")
    rc = main(["--registry", str(make_registry()), "validate", "--roster", str(bad)])
    assert rc == 1
    assert "roster INVALID" in capsys.readouterr().err


def test_validate_bad_registry(make_registry, capsys):
    root = make_registry({"x.yaml": "id: x\n"})
    assert main(["--registry", str(root), "validate"]) == 1
    assert "registry INVALID" in capsys.readouterr().err


def test_domains(make_registry, capsys):
    root = make_registry(from_fixture="valid")
    assert main(["--registry", str(root), "domains", "--active-only"]) == 0
    assert capsys.readouterr().out.split() == [
        "calendar.example.org",
        "events.example.org",
        "indico.example.com",
    ]


def test_registry_env_var(make_registry, monkeypatch, capsys):
    monkeypatch.setenv("TALK_TRACKER_REGISTRY", str(make_registry(from_fixture="valid")))
    assert main(["domains"]) == 0
    assert "astro.example.org" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["scrape"],
        ["report", "--month", "2026-09", "--roster", "r.txt"],
        ["check"],
        ["backfill", "--from", "2025-10-01"],
        ["evaluate", "--roster", "r.txt", "--known", "k.txt"],
    ],
)
def test_pending_commands(argv, capsys):
    assert main(argv) == 2
    assert "not implemented yet" in capsys.readouterr().err
