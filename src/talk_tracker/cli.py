"""Command-line interface (PLAN.md §5.8).

Implemented: ``validate``, ``domains`` (M0); ``list``, ``probe`` (M1). Other commands are
registered with their final options and exit with status 2 until their milestone lands.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .registry import RegistryError, default_root, load_registry
from .roster import RosterError, check_roster, load_roster

EXIT_OK, EXIT_INVALID, EXIT_NOT_IMPLEMENTED = 0, 1, 2

_PENDING = {
    "scrape": "M2",
    "report": "M4",
    "check": "M4",
    "backfill": "M4",
    "evaluate": "M4",
}


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def cmd_validate(args: argparse.Namespace) -> int:
    status = EXIT_OK
    try:
        reg = load_registry(args.registry)
    except RegistryError as exc:
        _err(f"registry INVALID ({len(exc.problems)} problem(s)):")
        for p in exc.problems:
            _err(f"  {p}")
        status = EXIT_INVALID
    else:
        n_series = sum(len(i.series) for i in reg.institutions)
        n_active = sum(1 for _ in reg.iter_series(active_only=True))
        print(
            f"registry OK: {len(reg.institutions)} institution(s), "
            f"{n_series} series ({n_active} active), {len(reg.domains())} domain(s)"
        )

    if args.roster:
        try:
            roster = load_roster(args.roster)
        except (RosterError, OSError) as exc:
            _err(f"roster INVALID: {exc}")
            return EXIT_INVALID
        counts = ", ".join(f"{n} {r}" for r, n in roster.by_role().items() if n)
        problems = check_roster(roster)
        if problems:
            _err(f"roster INVALID ({len(problems)} problem(s)):")
            for p in problems:
                _err(f"  {p}")
            status = EXIT_INVALID
        else:
            # counts only: rosters are personal data and should not end up in logs
            print(f"roster OK: {len(roster.entries)} people ({counts})")
    return status


def cmd_domains(args: argparse.Namespace) -> int:
    try:
        reg = load_registry(args.registry)
    except RegistryError as exc:
        _err(str(exc))
        return EXIT_INVALID
    for d in reg.domains(active_only=args.active_only):
        print(d)
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    try:
        reg = load_registry(args.registry)
    except RegistryError as exc:
        _err(str(exc))
        return EXIT_INVALID
    print("| series | institution | type | adapter | verified | keeps past | url |")
    print("|---|---|---|---|---|---|---|")
    for inst, s in reg.iter_series(active_only=args.active_only):
        print(
            f"| {s.id} | {inst.name} | {s.type} | {s.adapter} | "
            f"{'yes' if s.verified else 'no'} | {str(s.keeps_past_events).lower()} | {s.url} |"
        )
    return EXIT_OK


def cmd_probe(args: argparse.Namespace) -> int:
    from .probe import Fetcher, probe_series, render_markdown

    try:
        reg = load_registry(args.registry)
    except RegistryError as exc:
        _err(str(exc))
        return EXIT_INVALID
    wanted = set(args.series or [])
    targets = [
        s
        for _, s in reg.iter_series()
        if (not wanted or s.id in wanted) and not (args.unverified and s.verified)
    ]
    unknown = wanted - {s.id for s in targets}
    if unknown:
        _err(f"unknown series: {', '.join(sorted(unknown))}")
        return EXIT_INVALID
    fetcher = Fetcher(delay=args.delay)
    results = []
    for i, s in enumerate(targets, 1):
        _err(f"[{i}/{len(targets)}] {s.id}")
        results.append(probe_series(s, fetcher, check_feeds=not args.no_check_feeds))
    print(render_markdown(results), end="")
    if args.json:
        import json

        Path(args.json).write_text(
            json.dumps([r.to_dict() for r in results], indent=2) + "\n", encoding="utf-8"
        )
    return EXIT_OK


def cmd_pending(args: argparse.Namespace) -> int:
    _err(f"talk-tracker {args.command}: not implemented yet (milestone {_PENDING[args.command]})")
    return EXIT_NOT_IMPLEMENTED


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="talk-tracker",
        description="Find group members' talks in public colloquium/seminar calendars.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--registry",
        type=Path,
        default=None,
        help=f"registry directory (default: $TALK_TRACKER_REGISTRY or ./registry; "
        f"currently {default_root()})",
    )
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    s = sub.add_parser("validate", help="schema-check the registry (and a roster, if given)")
    s.add_argument("--roster", metavar="PATH", help="roster file to check ('-' for stdin)")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("domains", help="print the domains the registry fetches from")
    s.add_argument("--active-only", action="store_true", help="only series with active: true")
    s.set_defaults(func=cmd_domains)

    s = sub.add_parser("list", help="print the registry as a markdown table")
    s.add_argument("--active-only", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser(
        "probe", help="survey: detect platform and feeds of series pages (network access)"
    )
    s.add_argument("--series", metavar="ID", action="append", help="limit to series (repeatable)")
    s.add_argument("--no-check-feeds", action="store_true", help="do not fetch candidate feeds")
    s.add_argument("--unverified", action="store_true", help="only series with verified: false")
    s.add_argument("--delay", type=float, default=2.0, help="seconds between requests per host")
    s.add_argument("--json", metavar="PATH", help="also write full results as JSON")
    s.set_defaults(func=cmd_probe)

    s = sub.add_parser("scrape", help="fetch registered series into the archive")
    s.add_argument("--series", metavar="ID", action="append", help="limit to series (repeatable)")
    s.add_argument("--from", dest="date_from", metavar="DATE")
    s.add_argument("--to", dest="date_to", metavar="DATE")
    s.add_argument("--cache", action="store_true", help="use the on-disk HTTP cache")
    s.set_defaults(func=cmd_pending)

    s = sub.add_parser("report", help="monthly invited-talk report (markdown)")
    s.add_argument("--month", metavar="YYYY-MM", required=True)
    s.add_argument("--roster", metavar="PATH", required=True)
    s.add_argument("--min-confidence", choices=["high", "medium", "low"], default="medium")
    s.set_defaults(func=cmd_pending)

    s = sub.add_parser("check", help="per-series feed health")
    s.set_defaults(func=cmd_pending)

    s = sub.add_parser("backfill", help="one-off pull of past events where archives exist")
    s.add_argument("--from", dest="date_from", metavar="DATE", required=True)
    s.set_defaults(func=cmd_pending)

    s = sub.add_parser("evaluate", help="recall/precision against known talks")
    s.add_argument("--roster", metavar="PATH", required=True)
    s.add_argument("--known", metavar="PATH", required=True)
    s.set_defaults(func=cmd_pending)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
