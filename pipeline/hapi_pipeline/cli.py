"""Minimal CLI for the pipeline.

    hapi check     verify DB connectivity and print the jurisdiction count
    hapi enums     print the shared enum contracts

More commands (ingest, indicators, analytics) arrive in later phases (docs/11).
"""
from __future__ import annotations

import argparse
import sys


def _cmd_check(_args: argparse.Namespace) -> int:
    from .db import jurisdiction_count

    try:
        n = jurisdiction_count()
    except Exception as exc:  # noqa: BLE001 — surface any connection/config error
        print(f"✗ database check failed: {exc}", file=sys.stderr)
        print("  Is Postgres up and migrated? See db/README.md", file=sys.stderr)
        return 1
    print(f"✓ connected — {n} jurisdiction(s) in the database")
    return 0


def _cmd_enums(_args: argparse.Namespace) -> int:
    from .contracts import enums

    for name, values in enums().items():
        print(f"{name}: {', '.join(values)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hapi", description="HAPI pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify DB connectivity").set_defaults(func=_cmd_check)
    sub.add_parser("enums", help="print shared enum contracts").set_defaults(func=_cmd_enums)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
