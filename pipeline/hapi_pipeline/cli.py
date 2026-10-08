"""CLI for the pipeline.

    hapi check                         verify DB connectivity + jurisdiction count
    hapi enums                         print the shared enum contracts
    hapi ingest [--source N] [--live]  run Data Hub connectors (idempotent)
    hapi observations [--limit N] [--indicator SUBSTR]
                                       print loaded values with full lineage
    hapi watch probe|fetch|list|review|digest
                                       Policy Watch: discover new aging policy

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

    # Each connector opens its own short-lived DB connection inside ingest()
    # (after its network fetch), so one slow source can't hold a connection idle
    # long enough for a serverless pooler to drop it and break later writes.
    rc = 0
    for c in connectors:
        try:
            res = ingest(c, live=args.live)
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


def _watch_sources(args: argparse.Namespace):
    from .watch.sources import all_sources, get_source

    return [get_source(args.source)] if args.source else all_sources()


def _ids(csv: str | None) -> list[int]:
    return [int(x) for x in (csv or "").replace(" ", "").split(",") if x]


def _cmd_watch_probe(args: argparse.Namespace) -> int:
    """Fetch each live feed and show what it returns — no DB, no AI."""
    import re as _re
    import urllib.parse

    from .watch import sources as src
    from .watch.triage import keyword_match

    if args.discover:
        # Size up a candidate source before adding it to sources.py: what the URL
        # returns, the feed-like links on it, and a sample of its other links
        # (to design an HTML listing's item_pattern).
        for page in args.discover:
            print(f"=== {page}")
            try:
                body = src.http_get(page)
            except Exception as exc:  # noqa: BLE001
                print(f"    ✗ {type(exc).__name__}: {exc}")
                continue
            text = body.decode("utf-8", errors="replace")
            print(f"    {len(body):,} bytes · first bytes: {body[:240]!r}")
            lp = src._LinkParser()
            lp.feed(text)
            feeds, others = [], {}
            for href, label in lp.links:
                url = urllib.parse.urljoin(page, href)
                if _re.search(r"rss|atom|\.xml|feed|json", href, _re.IGNORECASE):
                    feeds.append((label, url))
                elif href and not href.startswith(("#", "mailto:", "javascript:")):
                    others.setdefault(urllib.parse.urlsplit(url).path, label)
            for label, url in feeds:
                print(f"    feed? {label[:50]!r:52} {url}")
            print(f"    {len(lp.links)} links; sample of other paths:")
            for path, label in list(others.items())[:40]:
                print(f"      {path[:90]:92} {label[:60]!r}")
        return 0

    since = src.default_since(args.since_days)
    ok = 0
    for s in _watch_sources(args):
        url = s.live_url(since)
        print(f"=== {s.name} — {s.label}\n    {url}")
        try:
            raw = src.http_get(url)
            n_raw, items = src.collect(s, live=True, since=since)
        except Exception as exc:  # noqa: BLE001
            print(f"    ✗ {type(exc).__name__}: {exc}")
            continue
        ok += 1
        if s.kind == "html":
            # Which links matched item_pattern, and a sample of those that didn't,
            # to tune the pattern or spot a fuller listing page.
            lp = src._LinkParser()
            lp.feed(raw.decode("utf-8", errors="replace"))
            rx = _re.compile(s.item_pattern)
            other = [h for h, _ in lp.links
                     if not rx.search(urllib.parse.urlsplit(urllib.parse.urljoin(s.url, h)).path)]
            print(f"    {len(lp.links)} links on the listing page, {len(lp.links) - len(other)} "
                  f"match item_pattern; others e.g.: {sorted(set(other))[:30]}")
            if items:
                meta = src.page_meta(src.http_get(items[0].url))
                print(f"    item page <title>: {meta.title.strip()[:120]!r}")
                print(f"    item page meta: {dict(list(meta.meta.items())[:15])}")
                long_ps = [x for x in meta.paragraphs if len(x) >= 60]
                print(f"    item page: {len(meta.paragraphs)} <p>, {len(long_ps)} long; "
                      f"first long: {[x[:160] for x in long_ps[:3]]}")
                print(f"    item summary used: {items[0].summary[:300]!r}")
        else:
            print(f"    first bytes: {raw[:300]!r}")
            m = _re.search(rb"<(item|entry)\b.*?</\1>", raw, _re.DOTALL)
            if m:  # one raw item, to see which fields the publisher fills in
                first_item = _re.sub(rb"\s+", b" ", m.group(0))[:700]
                print(f"    first item: {first_item!r}")
        dated = [i for i in items if i.published_at]
        newest = max((i.published_at for i in dated), default=None)
        oldest = min((i.published_at for i in dated), default=None)
        hits = [i for i in items if keyword_match(i).passes]
        print(f"    ✓ {len(raw):,} bytes · {n_raw} feed items · {len(items)} in window"
              f"{' (expanded from issue pages)' if s.expand_issues else ''} · dated "
              f"{len(dated)} ({oldest and oldest.date()} → {newest and newest.date()}) · "
              f"keyword hits {len(hits)}")
        for i in items[:5]:
            print(f"      - {i.published_at and i.published_at.date()} | "
                  f"{i.department[:30]} | {i.title[:100]}\n        {i.url}")
        for i in hits[:8]:
            print(f"      ★ {i.title[:100]}  {keyword_match(i).terms}")
        if s.expand_issues:
            # Show the raw TOC blocks of the newest issue, to tune expand_issue().
            issues = [i for i in src.parse(s, raw) if src.within_window(i, since)]
            if issues:
                parser = src._TocParser()
                parser.feed(src.http_get(issues[0].url).decode("utf-8", errors="replace"))
                print(f"    issue page {issues[0].url}: {len(parser.blocks)} linked blocks")
                for text, link_text, href in parser.blocks[:25]:
                    print(f"      · [{link_text[:40]}] {text[:90]} -> {href[:80]}")
    return 0 if ok else 1


def _cmd_watch_fetch(args: argparse.Namespace) -> int:
    from .watch import sources as src
    from .watch.store import watch_source
    from .watch.triage import make_client

    # Fixtures are static samples; don't let the date window age them out.
    since = src.default_since(args.since_days) if args.live else src.FIXTURE_SINCE
    client = None if args.no_ai else make_client()
    print(f"Policy Watch — {'live' if args.live else 'fixtures'} · since {since} · "
          f"Claude triage {'on' if client else 'off (keywords only)'}")
    failed, total_new = [], 0
    for s in _watch_sources(args):
        try:
            st = watch_source(s, live=args.live, since=since, client=client)
        except Exception as exc:  # noqa: BLE001 — one dead feed must not stop the others
            failed.append(s.name)
            # GitHub Actions annotation, so a failing feed is visible on the run page.
            print(f"::warning title=Policy Watch source failed::{s.name}: "
                  f"{type(exc).__name__}: {exc}")
            continue
        total_new += st.new
        ai = (f" · relevant {st.ai_relevant} · auto-rejected {st.auto_rejected}"
              if client else "")
        print(f"{'✚' if st.new else '·'} {s.name}: {st.fetched} fetched · "
              f"{st.in_window} in window · {st.matched} matched · {st.new} new{ai}")
        for t in st.new_titles[:10]:
            print(f"    + {t[:110]}")
    print(f"done — {total_new} new candidate(s); "
          f"{len(failed)} source(s) failed{': ' + ', '.join(failed) if failed else ''}")
    # Fail only when every source failed (likely a network/config problem);
    # individual feed failures are surfaced as warnings above.
    return 1 if failed and len(failed) == len(_watch_sources(args)) else 0


def _cmd_watch_list(args: argparse.Namespace) -> int:
    from .watch.store import list_candidates

    rows = list_candidates(None if args.status == "all" else args.status, args.limit)
    for c in rows:
        when = c["published_at"].date() if c["published_at"] else "undated"
        ai = f" [{c['ai_category']} {c['ai_confidence']:.2f}]" if c["ai_category"] else ""
        print(f"#{c['id']:<5} {c['status']:<13} {c['jurisdiction_code'] or '':<7} {when}  "
              f"{c['title'][:80]}{ai}")
        print(f"       {c['url']}")
    print(f"({len(rows)} candidate(s))")
    return 0


def _cmd_watch_review(args: argparse.Namespace) -> int:
    from .watch.store import review

    accept, reject = _ids(args.accept), _ids(args.reject)
    if not (accept or reject):
        print("nothing to do — pass --accept and/or --reject ids", file=sys.stderr)
        return 2
    res = review(accept, reject, note=args.note, write_seed=not args.no_seed)
    print(f"accepted {res.accepted or '—'} · rejected {res.rejected or '—'}")
    for slug in res.seed_added:
        print(f"  ✚ drafted seed entry: {slug}")
    if res.seed_added:
        print("  → edit the drafted entries in policies/seed_policies.json (full_text, KPIs, "
              "indicators), then commit and run `hapi policies seed`.")
    if res.missing:
        print(f"  ⚠ no such candidate id(s): {res.missing}", file=sys.stderr)
        return 1
    return 0


def _cmd_watch_digest(args: argparse.Namespace) -> int:
    from pathlib import Path

    from .watch.store import digest

    text, n = digest(args.days)
    if not args.out:
        print(text)
    elif n:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} — {n} new candidate(s)")
    else:
        # No file → the workflow posts no issue (a quiet week stays quiet).
        print(f"no new candidates in the last {args.days} day(s) — {args.out} not written")
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

    p_w = sub.add_parser("watch", help="Policy Watch: discover new aging-policy items")
    w_sub = p_w.add_subparsers(dest="watch_cmd", required=True)
    w_probe = w_sub.add_parser("probe", help="fetch live feeds and show what they return "
                                             "(no DB, no AI)")
    w_probe.add_argument("--source", help="probe only this source (e.g. gazette_p1)")
    w_probe.add_argument("--since-days", type=int, default=30)
    w_probe.add_argument("--discover", nargs="+", metavar="URL",
                         help="instead of probing sources, list feed links found on these pages")
    w_probe.set_defaults(func=_cmd_watch_probe)
    w_fetch = w_sub.add_parser("fetch", help="poll feeds, triage, store new candidates")
    w_fetch.add_argument("--source", help="run only this source")
    w_fetch.add_argument("--live", action="store_true",
                         help="fetch real feeds (default: vendored sample fixtures)")
    w_fetch.add_argument("--since-days", type=int, default=30,
                         help="ignore items published before this many days ago (live)")
    w_fetch.add_argument("--no-ai", action="store_true",
                         help="keyword triage only, even if ANTHROPIC_API_KEY is set")
    w_fetch.set_defaults(func=_cmd_watch_fetch)
    w_list = w_sub.add_parser("list", help="list candidates")
    w_list.add_argument("--status", default="new",
                        choices=["new", "accepted", "rejected", "auto_rejected", "all"])
    w_list.add_argument("--limit", type=int, default=50)
    w_list.set_defaults(func=_cmd_watch_list)
    w_rev = w_sub.add_parser("review", help="accept / reject candidates by id")
    w_rev.add_argument("--accept", help="comma-separated ids to accept (drafts seed entries)")
    w_rev.add_argument("--reject", help="comma-separated ids to reject")
    w_rev.add_argument("--note", help="review note stored on the candidates")
    w_rev.add_argument("--no-seed", action="store_true",
                       help="mark accepted without drafting seed_policies.json entries")
    w_rev.set_defaults(func=_cmd_watch_review)
    w_dig = w_sub.add_parser("digest", help="Markdown digest of recent candidates")
    w_dig.add_argument("--days", type=int, default=7)
    w_dig.add_argument("--out", help="write to this file instead of stdout")
    w_dig.set_defaults(func=_cmd_watch_digest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
