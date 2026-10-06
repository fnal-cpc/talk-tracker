from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def make_registry(tmp_path):
    """Build a registry dir from the repo schema plus the given {filename: yaml text}."""

    def _make(files: dict[str, str] | None = None, from_fixture: str | None = None) -> Path:
        root = tmp_path / "registry"
        (root / "institutions").mkdir(parents=True)
        shutil.copy(REPO / "registry" / "schema.json", root / "schema.json")
        if from_fixture:
            for p in (FIXTURES / "registry" / from_fixture / "institutions").iterdir():
                shutil.copy(p, root / "institutions" / p.name)
        for name, text in (files or {}).items():
            (root / "institutions" / name).write_text(text, encoding="utf-8")
        return root

    return _make
