"""Guard for PLAN.md §0.6: the public repository must not contain people data.

Fails if any tracked text file contains an ORCID-like identifier other than the
fictional ones used in test fixtures, or if a roster-like file would be committed.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from talk_tracker.roster import orcid_checksum_ok

from .conftest import REPO

FICTIONAL_ORCIDS = {
    "0000-0000-0000-0000",  # placeholder in PLAN.md / docs
    "0000-0002-1825-0097",  # ORCID's documented fictional example
    "0000-0001-0000-0009",
    "0000-0001-1111-1118",
    "0000-0001-2222-2227",
    "0000-0001-3333-3336",
    "0000-0001-4444-4445",
}
ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")


def _tracked_files():
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [REPO / p for p in out.splitlines() if (REPO / p).is_file()]


def test_no_real_orcids():
    offenders = []
    for path in _tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in ORCID_RE.findall(text):
            # checksum-invalid strings (used in negative tests) cannot be real iDs
            if orcid_checksum_ok(m) and m not in FICTIONAL_ORCIDS:
                offenders.append(f"{path.relative_to(REPO)}: {m}")
    assert not offenders, "unexpected ORCID iDs in repository:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    "name", ["roster.txt", "roster-2026.yaml", "group.roster.json", "members.md", "known_talks.csv"]
)
def test_roster_files_are_ignored(name):
    r = subprocess.run(["git", "check-ignore", "-q", name], cwd=REPO)
    assert r.returncode == 0, f"{name} would not be ignored by .gitignore"


def test_roster_module_not_ignored():
    r = subprocess.run(["git", "check-ignore", "-q", "src/talk_tracker/roster.py"], cwd=REPO)
    assert r.returncode == 1
