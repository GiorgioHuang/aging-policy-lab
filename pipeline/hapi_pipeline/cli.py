"""CLI for the pipeline.

    hapi check                         verify DB connectivity + jurisdiction count
    hapi enums                         print the shared enum contracts
    hapi ingest [--source N] [--live]  run Data Hub connectors (idempotent)
    hapi observations [--limit N]      print loaded values with full lineage

Later phases add indicators/analytics commands (docs/11).
"""
from __future__ import annotations

import argparse
import sys


def _cmd_check(_args: argparse.Namespace) -> int:
    from .db import jurisdiction_count

    try:
        n = jurisdiction_count()
    except Exception as exc:  # noqa: BLE001
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


def _cmd_ingest(args: argparse.Namespace) -> int:
    from .db import connect
    from .ingest.registry import all_connectors, get_connector
    from .loader import ingest

    connectors = [get_connector(args.source)] if args.source else all_connectors()

    # Dry run: fetch + parse + validate and print a sample, but touch no DB and
    # do not overwrite fixtures. Ideal for confirming a connector against the
    # real upstream (`--live --dry-run`) before loading.
    if args.dry_run:
        from .transform.quality import run_quality_checks

        rc = 0
        for c in connectors:
            tag = "live" if args.live else "fixture"
            try:
                try:
                    payload = c.extract(live=args.live, capture=False)
                except NotImplementedError:
                    payload = c.extract(live=False, capture=False)  # no live path
                    tag = "fixture"
                records = c.parse(payload)
                kept, issues = run_quality_checks(c.indicators, records)
            except Exception as exc:  # noqa: BLE001
                print(f"✗ {c.name}: failed — {exc}", file=sys.stderr)
                rc = 1
                continue
            print(
                f"◇ {c.name} [{tag}] checksum {payload.checksum[:12]}… — "
                f"parsed {len(records)}, would load {len(kept)}"
            )
            for r in kept[:3]:
                val = "—" if r.value is None else f"{r.value:,.1f}"
                print(f"    e.g. {r.indicator_code} {r.jurisdiction_code} "
                      f"{r.period_start[:4]} = {val} [{r.quality_flag}]")
            for issue in issues:
                print(f"    ⚠ {issue}")
        return rc

    rc = 0
    with connect() as conn:
        for c in connectors:
            try:
                res = ingest(conn, c, live=args.live)
            except NotImplementedError as exc:
                print(f"• {c.name}: skipped — {exc}")
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"✗ {c.name}: failed — {exc}", file=sys.stderr)
                rc = 1
                continue
            tag = "fixture" if res.source_version.startswith("fixture:") else "live"
            if res.no_op:
                print(
                    f"· {c.name}: no-op (unchanged; checksum {res.checksum[:12]}…, "
                    f"{res.records_parsed} records already loaded)"
                )
            else:
                print(
                    f"✚ {c.name}: loaded {res.observations_loaded} observation(s) "
                    f"[{tag}] checksum {res.checksum[:12]}…"
                )
            for issue in res.issues:
                print(f"    ⚠ {issue}")
    return rc


def _cmd_observations(args: argparse.Namespace) -> int:
    from .db import connect

    sql = """
        SELECT indicator_code, jurisdiction_code, period_start, value,
               quality_flag, datasource_name, source_version, left(checksum, 10)
          FROM observation_lineage
         ORDER BY indicator_code, jurisdiction_code, period_start
         LIMIT %s
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (args.limit,))
        rows = cur.fetchall()
    if not rows:
        print("no observations yet — run `hapi ingest`")
        return 0
    print(f"{'indicator':<42} {'jur':<6} {'period':<11} {'value':>12} {'flag':<10} source")
    for ind, jur, period, value, flag, ds, sver, csum in rows:
        val = "—" if value is None else f"{float(value):,.1f}"
        prov = "fixture" if str(sver).startswith("fixture:") else "live"
        print(f"{ind:<42} {jur:<6} {str(period):<11} {val:>12} {flag:<10} {ds} [{prov} {csum}]")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    from .ingest.registry import all_connectors, get_connector

    connectors = [get_connector(args.source)] if args.source else all_connectors()
    for c in connectors:
        print(f"=== {c.name} ===")
        try:
            print(c.inspect_live())
        except Exception as exc:  # noqa: BLE001
            print(f"inspect failed: {exc}", file=sys.stderr)
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hapi", description="HAPI pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify DB connectivity").set_defaults(func=_cmd_check)
    sub.add_parser("enums", help="print shared enum contracts").set_defaults(func=_cmd_enums)

    p_ing = sub.add_parser("ingest", help="run Data Hub connectors (idempotent)")
    p_ing.add_argument("--source", help="run only this connector (e.g. statcan_wds)")
    p_ing.add_argument("--live", action="store_true",
                       help="fetch from the real upstream and refresh fixtures")
    p_ing.add_argument("--dry-run", action="store_true",
                       help="fetch + parse + validate and print a sample; no DB writes")
    p_ing.set_defaults(func=_cmd_ingest)

    p_obs = sub.add_parser("observations", help="print loaded values with lineage")
    p_obs.add_argument("--limit", type=int, default=50)
    p_obs.set_defaults(func=_cmd_observations)

    p_ins = sub.add_parser("inspect", help="dump the real upstream schema (needs network)")
    p_ins.add_argument("--source", help="inspect only this connector")
    p_ins.set_defaults(func=_cmd_inspect)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
