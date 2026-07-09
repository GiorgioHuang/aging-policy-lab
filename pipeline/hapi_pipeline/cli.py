"""CLI for the pipeline.

    hapi check                         verify DB connectivity + jurisdiction count
    hapi enums                         print the shared enum contracts
    hapi ingest [--source N] [--live]  run Data Hub connectors (idempotent)
    hapi observations [--limit N] [--indicator SUBSTR]
                                       print loaded values with full lineage

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

    where = ""
    params: list = []
    if getattr(args, "indicator", None):
        where = "WHERE indicator_code ILIKE %s"
        params.append(f"%{args.indicator}%")
    sql = f"""
        SELECT indicator_code, jurisdiction_code, period_start, value,
               quality_flag, datasource_name, source_version, left(checksum, 10)
          FROM observation_lineage
         {where}
         ORDER BY indicator_code, jurisdiction_code, period_start
         LIMIT %s
    """
    params.append(args.limit)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params))
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


def _cmd_prune_indicator(args: argparse.Namespace) -> int:
    """Retire an indicator: remove its observations and (only) the datasources it
    exclusively fed. Dry-run by default; --apply executes inside one transaction.

    The observation store is otherwise append-only (immutable lineage). This is a
    deliberate, audited maintenance path for an indicator that has been removed
    from the methodology entirely (e.g. a source that turned out to exclude NS),
    so it no longer clutters the Data Hub. Scores are unaffected — recompute with
    `hapi score` after pruning if the indicator was ever part of a composite.
    """
    from .db import connect

    code = args.code
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM indicator WHERE code = %s", (code,))
        row = cur.fetchone()
        if not row:
            print(f"✗ no indicator with code '{code}' — nothing to prune")
            return 1
        ind_id, ind_name = row

        cur.execute("SELECT count(*) FROM observation WHERE indicator_id = %s", (ind_id,))
        n_obs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM policy_indicator WHERE indicator_id = %s", (ind_id,))
        n_pol = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM indicator_source WHERE indicator_id = %s", (ind_id,))
        n_src = cur.fetchone()[0]

        # Datasources that fed ONLY this indicator (zero observations from any
        # other indicator) — safe to delete; their dataset_versions cascade.
        cur.execute(
            """
            SELECT ds.id, ds.name
              FROM datasource ds
             WHERE EXISTS (SELECT 1 FROM dataset_version dv
                             JOIN observation o ON o.dataset_version_id = dv.id
                            WHERE dv.datasource_id = ds.id AND o.indicator_id = %s)
               AND NOT EXISTS (SELECT 1 FROM dataset_version dv
                                 JOIN observation o ON o.dataset_version_id = dv.id
                                WHERE dv.datasource_id = ds.id AND o.indicator_id <> %s)
            """,
            (ind_id, ind_id),
        )
        orphan_sources = cur.fetchall()

        print(f"indicator: {code} (id {ind_id}) — {ind_name}")
        print(f"  observations to delete:   {n_obs}")
        print(f"  policy_indicator links:   {n_pol}")
        print(f"  indicator_source links:   {n_src}")
        if orphan_sources:
            for sid, sname in orphan_sources:
                cur.execute("SELECT count(*) FROM dataset_version WHERE datasource_id = %s", (sid,))
                n_dv = cur.fetchone()[0]
                print(f"  orphaned datasource:      '{sname}' (id {sid}, {n_dv} dataset_version(s))")
        else:
            print("  orphaned datasources:     none")

        if not args.apply:
            print("\n(dry run — re-run with --apply to execute the prune in one transaction)")
            return 0

        # Observations first (no cascade reaches them), then the indicator
        # (cascades policy_indicator + indicator_source), then orphaned
        # datasources (cascades their now-empty dataset_versions).
        cur.execute("DELETE FROM observation WHERE indicator_id = %s", (ind_id,))
        cur.execute("DELETE FROM indicator WHERE id = %s", (ind_id,))
        for sid, _ in orphan_sources:
            cur.execute("DELETE FROM datasource WHERE id = %s", (sid,))
        conn.commit()
        print(f"\n✓ pruned '{code}': removed {n_obs} observation(s), the indicator, "
              f"{n_pol} policy link(s), {n_src} source link(s), "
              f"{len(orphan_sources)} orphaned datasource(s).")
    return 0


def _cmd_policies_seed(_args: argparse.Namespace) -> int:
    from .db import connect
    from .policies.loader import load_policies

    with connect() as conn:
        r = load_policies(conn)
    print(f"✓ policies: +{r.inserted} inserted, {r.updated} updated, {r.links} indicator link(s)")
    if r.missing_indicators:
        print(f"  · referenced indicators not yet in DB (skipped): {', '.join(r.missing_indicators)}")
    return 0


def _cmd_policies_summarize(args: argparse.Namespace) -> int:
    from .ai.summarize import summarize_policies
    from .db import connect

    with connect() as conn:
        n = summarize_policies(conn, model=args.model, limit=args.limit)
    print(f"✓ summarized {n} policy(ies)")
    return 0


def _cmd_score(_args: argparse.Namespace) -> int:
    from .db import connect
    from .indicators.engine import compute_hapi

    with connect() as conn:
        n = compute_hapi(conn)
    print(f"✓ HAPI: wrote {n} score row(s) (method_version v1)")
    return 0


def _cmd_weights(_args: argparse.Namespace) -> int:
    from .db import connect
    from .indicators.weighting import DOMAINS, sensitivity

    with connect() as conn:
        out = sensitivity(conn)
    schemes = out["schemes"]

    print("=== HAPI domain weights (normalized %) ===")
    print(f"{'domain':<22} " + "".join(f"{name:>11}" for name in schemes))
    for d in DOMAINS:
        cells = ""
        for name in schemes:
            w = schemes[name]
            tot = sum(w.values()) or 1.0
            cells += f"{(100 * w.get(d, 0.0) / tot):>10.1f}%"
        print(f"{d:<22} {cells}")

    print("\n=== Composite (overall HAPI) under each scheme, latest period ===")
    print(f"{'jurisdiction':<14} {'period':<11} " + "".join(f"{n:>11}" for n in schemes))
    max_spread = 0.0
    for r in out["rows"]:
        comp = r["composite"]
        cells = "".join(("—" if comp[n] is None else f"{comp[n]:.1f}").rjust(11) for n in schemes)
        vals = [v for v in comp.values() if v is not None]
        if len(vals) >= 2:
            max_spread = max(max_spread, max(vals) - min(vals))
        print(f"{r['jurisdiction']:<14} {r['period']:<11} {cells}")
    print(f"\nMax composite spread across schemes: {max_spread:.1f} points "
          "(smaller = more robust to the weighting choice).")
    print("expert = v1 default (theory-anchored); empirical = coefficient-of-variation, "
          "indicative while coverage is NS + Federal.")
    return 0


def _cmd_analyze(_args: argparse.Namespace) -> int:
    from .analytics.runner import run_analyses
    from .db import connect

    with connect() as conn:
        n = run_analyses(conn)
    print(f"✓ analytics: wrote {n} finding(s) (Tier-1 trends + worked ITS)")
    return 0


def _cmd_findings(args: argparse.Namespace) -> int:
    """Print stored analysis findings (with the ITS coefficients) and their tier."""
    from .db import connect
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT f.slug, f.title, f.tier, f.method, f.indicator_code,
                      f.jurisdiction_code, f.window_spec, f.result, p.title
                 FROM analysis_finding f LEFT JOIN policy p ON p.id = f.policy_id
                ORDER BY f.method DESC, f.slug""")
        rows = cur.fetchall()
    if not rows:
        print("no findings yet — run `hapi analyze`")
        return 0
    for slug, title, tier, method, ind, jur, win, res, ptitle in rows:
        tag = "Causal(ITS)" if (tier == "causal" and method == "its") else (
            "Causal" if tier == "causal" else "Association")
        if method == "its":
            print(f"\n[{tag}] {title}")
            if ptitle:
                print(f"   policy: {ptitle}")
            iv = (win or {}).get("intervention")
            print(f"   {ind} @ {jur} | intervention {iv} | "
                  f"n_pre/post {res.get('n_pre')}/{res.get('n_post')} | status {res.get('status')}")
            if res.get("status") == "ok":
                for k in ("pre_trend", "level_change", "slope_change"):
                    t = res[k]
                    star = "*" if t["p"] < 0.05 else " "
                    print(f"     {star}{k:<13} coef={t['coef']:>10}  (95% CI "
                          f"{t['ci_low']}..{t['ci_high']}, p={t['p']})")
                print(f"      R^2 {res.get('r_squared')}")
        elif args.all:
            tr = res or {}
            print(f"[{tag}] {ind} @ {jur}: {tr.get('start_value')} -> {tr.get('end_value')} "
                  f"({tr.get('direction')}, {tr.get('pct_change')}% over {tr.get('n')} pts)")
    n_its = sum(1 for r in rows if r[3] == "its")
    print(f"\n{len(rows)} finding(s): {n_its} ITS (causal), {len(rows)-n_its} trend (association).")
    return 0


def _cmd_paper_tables(_args: argparse.Namespace) -> int:
    """Emit ready-to-paste Markdown tables for the Paper 1 [TODO] slots."""
    from .db import connect
    from .paper import render

    with connect() as conn:
        print(render(conn))
    return 0


def _cmd_literature_seed(_args: argparse.Namespace) -> int:
    from .db import connect
    from .literature.loader import load_literature

    with connect() as conn:
        ins, upd = load_literature(conn)
    print(f"✓ literature: +{ins} inserted, {upd} updated")
    return 0


def _cmd_assistant(args: argparse.Namespace) -> int:
    from .ai.assistant import research
    from .db import connect

    with connect() as conn:
        out = research(conn, args.topic, model=args.model)
    pack = out["pack"]
    print(f"=== Evidence pack for: {args.topic} ===")
    print(f"  policies: {len(pack['policies'])} · literature: {len(pack['literature'])} "
          f"· findings: {len(pack['findings'])} · indicators: {len(pack['indicators'])}")
    for p in pack["policies"]:
        print(f"  [{p['cite']}] {p['title']} ({p['jurisdiction']}, {p['released_at']})")
    for lit in pack["literature"]:
        print(f"  [{lit['cite']}] {lit['title']} — {lit['authors']} ({lit['year']})")
    for f in pack["findings"]:
        print(f"  [{f['cite']}] {f['title']} · {f['tier_label']}")
    print()
    if out["draft"]:
        print("=== Cited draft ===\n" + out["draft"])
    else:
        print("(no draft — set ANTHROPIC_API_KEY to generate a cited review from this pack)")
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
    p_obs.add_argument("--indicator", help="filter by indicator_code substring (ILIKE), "
                                           "e.g. independence.adl")
    p_obs.set_defaults(func=_cmd_observations)

    p_prune = sub.add_parser("prune-indicator",
                             help="retire an indicator + its observations (dry-run by default)")
    p_prune.add_argument("code", help="indicator code to remove, e.g. care_access.home_care_clients_65plus")
    p_prune.add_argument("--apply", action="store_true",
                         help="execute the deletion (otherwise just report what would be removed)")
    p_prune.set_defaults(func=_cmd_prune_indicator)

    p_ins = sub.add_parser("inspect", help="dump the real upstream schema (needs network)")
    p_ins.add_argument("--source", help="inspect only this connector")
    p_ins.set_defaults(func=_cmd_inspect)

    p_pol = sub.add_parser("policies", help="Policy Library: seed / summarize")
    pol_sub = p_pol.add_subparsers(dest="pol_cmd", required=True)
    pol_sub.add_parser("seed", help="load the curated policy seed").set_defaults(
        func=_cmd_policies_seed)
    p_sum = pol_sub.add_parser("summarize", help="AI summaries (needs ANTHROPIC_API_KEY)")
    p_sum.add_argument("--model", help="Claude model id (default: HAPI_SUMMARY_MODEL or opus)")
    p_sum.add_argument("--limit", type=int, default=None)
    p_sum.set_defaults(func=_cmd_policies_summarize)

    sub.add_parser("score", help="compute HAPI v1 scores").set_defaults(func=_cmd_score)
    sub.add_parser("weights", help="domain weighting schemes + composite sensitivity").set_defaults(
        func=_cmd_weights)
    sub.add_parser("analyze", help="compute analytic findings (Tier-1 + ITS)").set_defaults(
        func=_cmd_analyze)
    p_find = sub.add_parser("findings", help="print stored findings (ITS coefficients + tier)")
    p_find.add_argument("--all", action="store_true",
                        help="also print Tier-1 trend findings (not just ITS)")
    p_find.set_defaults(func=_cmd_findings)

    sub.add_parser("paper-tables",
                   help="emit paper-ready Markdown tables (HAPI scores, weights, ITS, counts)"
                   ).set_defaults(func=_cmd_paper_tables)

    p_lit = sub.add_parser("literature", help="literature KB")
    lit_sub = p_lit.add_subparsers(dest="lit_cmd", required=True)
    lit_sub.add_parser("seed", help="load the starter literature set").set_defaults(
        func=_cmd_literature_seed)

    p_as = sub.add_parser("assistant", help="topic -> evidence pack + cited draft")
    p_as.add_argument("topic", help="research topic, e.g. 'NS dementia policy'")
    p_as.add_argument("--model", help="Claude model id (default: HAPI_SUMMARY_MODEL or opus)")
    p_as.set_defaults(func=_cmd_assistant)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
