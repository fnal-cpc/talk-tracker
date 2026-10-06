"""Load and validate the institution registry (PLAN.md §4.1).

Validation runs in three layers so that errors are reported with file and path:

1. JSON Schema (``registry/schema.json``) on the raw YAML;
2. pydantic models (:class:`~talk_tracker.models.Institution`), e.g. IANA timezone;
3. cross-file rules: file name equals ``id``; series ids are prefixed with the
   institution id and globally unique; every http(s) URL in ``params`` is on a host
   listed in the series' ``domains``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import jsonschema
import yaml
from pydantic import ValidationError

from .models import Institution, Series

ENV_VAR = "TALK_TRACKER_REGISTRY"


class RegistryError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass(frozen=True)
class Registry:
    root: Path
    institutions: tuple[Institution, ...]

    def iter_series(self, active_only: bool = False) -> Iterator[tuple[Institution, Series]]:
        for inst in self.institutions:
            for s in inst.series:
                if s.active or not active_only:
                    yield inst, s

    def series_by_id(self, series_id: str) -> tuple[Institution, Series]:
        for inst, s in self.iter_series():
            if s.id == series_id:
                return inst, s
        raise KeyError(series_id)

    def domains(self, active_only: bool = False) -> list[str]:
        return sorted({d for _, s in self.iter_series(active_only) for d in s.domains})


def default_root() -> Path:
    """``$TALK_TRACKER_REGISTRY``, else ``./registry``."""
    env = os.environ.get(ENV_VAR)
    return Path(env) if env else Path.cwd() / "registry"


def _iter_urls(obj: Any, path: str = "params") -> Iterator[tuple[str, str]]:
    if isinstance(obj, str):
        if obj.startswith(("http://", "https://")):
            yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_urls(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_urls(v, f"{path}[{i}]")


def load_registry(root: str | Path | None = None) -> Registry:
    """Load ``<root>/institutions/*.yaml``, validated against ``<root>/schema.json``.

    Raises :class:`RegistryError` listing every problem found.
    """
    root = Path(root) if root is not None else default_root()
    schema_path = root / "schema.json"
    inst_dir = root / "institutions"
    if not schema_path.is_file():
        raise RegistryError([f"{schema_path}: schema not found"])
    if not inst_dir.is_dir():
        raise RegistryError([f"{inst_dir}: directory not found"])

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    problems: list[str] = []
    institutions: list[Institution] = []
    series_owner: dict[str, str] = {}

    files = sorted(p for p in inst_dir.iterdir() if p.suffix in {".yaml", ".yml"})
    for path in files:
        rel = path.relative_to(root)
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: invalid YAML: {exc}")
            continue

        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            for e in errors:
                where = "/".join(str(x) for x in e.absolute_path) or "(root)"
                problems.append(f"{rel}: {where}: {e.message}")
            continue

        try:
            inst = Institution.model_validate(data)
        except ValidationError as exc:
            for e in exc.errors():
                where = "/".join(str(x) for x in e["loc"]) or "(root)"
                problems.append(f"{rel}: {where}: {e['msg']}")
            continue

        if inst.id != path.stem:
            problems.append(f"{rel}: id {inst.id!r} does not match file name {path.stem!r}")
        for i, s in enumerate(inst.series):
            where = f"{rel}: series/{i} ({s.id})"
            if not s.id.startswith(inst.id + "-"):
                problems.append(f"{where}: series id must start with {inst.id + '-'!r}")
            if s.id in series_owner:
                problems.append(f"{where}: duplicate series id (also in {series_owner[s.id]})")
            else:
                series_owner[s.id] = str(rel)
            for ppath, url in _iter_urls(s.params):
                host = (urlsplit(url).hostname or "").lower()
                if host not in s.domains:
                    problems.append(
                        f"{where}: {ppath} host {host!r} is not listed in domains {s.domains}"
                    )
        institutions.append(inst)

    if problems:
        raise RegistryError(problems)
    return Registry(root=root, institutions=tuple(institutions))
