"""Emit paper-ready Markdown tables from the live database.

`python -m hapi_pipeline.cli paper-tables` prints ready-to-paste Markdown for the
quantitative `[TODO: …]` slots in `papers/paper-1-observatory-design/paper.md`:

  1. Corpus counts (the v1 build, quantified).
  2. HAPI domain + composite scores, latest period per jurisdiction (§5.4 / Fig 4).
  3. Weighting sensitivity — composite under equal/expert/empirical (§5.3).
  4. Worked interrupted-time-series coefficients (§6.2 / Fig 5).

Run it against a populated database (locally after `ingest`/`score`/`analyze`, or
against the production connection) and paste each block over the matching TODO.
Regenerate whenever the underlying data changes so the paper stays in sync.
"""
from __future__ import annotations

from .indicators import hapi_v1
from .indicators.weighting import DOMAINS, sensitivity

# Human-readable domain labels for the paper (order = weighting.DOMAINS).
DOMAIN_LABEL = {
    "health": "Health",
    "independence": "Independence",
    "social_participation": "Social Participation",
    "financial_security": "Financial Security",
    "care_access": "Care Access",
    "digital_inclusion": "Digital Inclusion",
}


def _fmt(v: float | None, nd: int = 1) -> str:
    return "—" if v is None else f"{v:.{nd}f}"


def corpus_counts(conn) -> str:
    """Markdown table of the instantiated corpus (§8 TODO)."""
    queries = [
        ("Policies", "SELECT count(*) FROM policy"),
        ("Indicators (distinct, observed)", "SELECT count(DISTINCT indicator_id) FROM observation"),
        ("Observations", "SELECT count(*) FROM observation"),
        ("Dataset versions", "SELECT count(*) FROM dataset_version"),
        ("Data sources", "SELECT count(*) FROM datasource"),
        ("HAPI scores", "SELECT count(*) FROM hapi_score"),
        ("Analytic findings", "SELECT count(*) FROM analysis_finding"),
        ("Literature references", "SELECT count(*) FROM literature"),
        ("Jurisdictions", "SELECT count(*) FROM jurisdiction"),
    ]
    lines = ["| Asset | Count |", "|---|---:|"]
    with conn.cursor() as cur:
        for label, q in queries:
            cur.execute(q)
            lines.append(f"| {label} | {cur.fetchone()[0]:,} |")
    return "\n".join(lines)


def hapi_scores_table(conn) -> str:
    """Markdown domain-profile table: each domain's *latest available* score per
    jurisdiction (matching the platform's radar), plus the latest composite and the
    period it is from. Using latest-per-domain (rather than a single latest period)
    reflects that domains are measured on different survey vintages."""
    # code -> domain -> (period, score), keeping the latest period per domain.
    latest_by_domain: dict[str, dict[str, tuple[str, float]]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """SELECT j.code, h.domain, h.period::text, h.score
                 FROM hapi_score h JOIN jurisdiction j ON j.id = h.jurisdiction_id
                WHERE h.method_version = %s
                ORDER BY h.period ASC""",  # ascending → last write wins = latest
            (hapi_v1.METHOD_VERSION,),
        )
        for code, domain, period, score in cur.fetchall():
            latest_by_domain.setdefault(code, {})[domain] = (period, float(score))

    if not latest_by_domain:
        return "_No HAPI scores in the database — run `hapi score` first._"

    header = ["Jurisdiction", "Overall", "As of"] + [DOMAIN_LABEL[d] for d in DOMAINS]
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] + ["---:"] + ["---"] + ["---:"] * len(DOMAINS)) + "|"]
    for code in sorted(latest_by_domain):
        by_domain = latest_by_domain[code]
        overall = by_domain.get("overall")
        row = [code,
               _fmt(overall[1], 0) if overall else "—",
               overall[0] if overall else "—"]
        row += [_fmt(by_domain[d][1], 0) if d in by_domain else "—" for d in DOMAINS]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(f"_HAPI v1 ({hapi_v1.METHOD_VERSION}); 0–100, higher is better. Each domain "
                 "shows its latest available score (domains use different survey vintages); "
                 "'—' = no data yet for that domain × jurisdiction. 'As of' = period of the "
                 "latest composite._")
    return "\n".join(lines)


def weighting_table(conn) -> str:
    """Markdown for the weighting sensitivity analysis (§5.3 TODO)."""
    out = sensitivity(conn)
    schemes = out["schemes"]
    names = list(schemes)

    # Domain weights (normalized %).
    wlines = ["**Domain weights (normalized %):**", "",
              "| Domain | " + " | ".join(names) + " |",
              "|" + "|".join(["---"] + ["---:"] * len(names)) + "|"]
    for d in DOMAINS:
        cells = []
        for n in names:
            w = schemes[n]
            tot = sum(w.values()) or 1.0
            cells.append(f"{100 * w.get(d, 0.0) / tot:.1f}")
        wlines.append(f"| {DOMAIN_LABEL[d]} | " + " | ".join(cells) + " |")

    # Composite under each scheme, latest period.
    clines = ["", "**Composite (overall HAPI) under each scheme, latest period:**", "",
              "| Jurisdiction | Period | " + " | ".join(names) + " |",
              "|" + "|".join(["---", "---"] + ["---:"] * len(names)) + "|"]
    max_spread = 0.0
    for r in out["rows"]:
        comp = r["composite"]
        cells = [_fmt(comp[n]) for n in names]
        vals = [v for v in comp.values() if v is not None]
        if len(vals) >= 2:
            max_spread = max(max_spread, max(vals) - min(vals))
        clines.append(f"| {r['jurisdiction']} | {r['period']} | " + " | ".join(cells) + " |")
    clines.append("")
    clines.append(f"_Max composite spread across schemes: **{max_spread:.1f} points** "
                  "(smaller = more robust to the weighting choice). expert = v1 default; "
                  "empirical = coefficient-of-variation, indicative while coverage is NS + federal._")
    return "\n".join(wlines + clines)


def its_findings(conn) -> str:
    """Markdown for the worked ITS coefficients (§6.2 TODO)."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT f.title, f.indicator_code, f.jurisdiction_code, f.window_spec,
                      f.result, p.title
                 FROM analysis_finding f LEFT JOIN policy p ON p.id = f.policy_id
                WHERE f.method = 'its'
                ORDER BY f.slug""")
        rows = cur.fetchall()
    if not rows:
        return "_No ITS findings — run `hapi analyze` first._"

    blocks: list[str] = []
    for title, ind, jur, win, res, ptitle in rows:
        iv = (win or {}).get("intervention")
        head = [f"**{title}**  ",
                f"Indicator `{ind}` @ {jur}"
                + (f" · policy: {ptitle}" if ptitle else "")
                + f" · intervention {iv} · "
                f"n_pre/post {res.get('n_pre')}/{res.get('n_post')} · status `{res.get('status')}`"]
        if res.get("status") == "ok":
            tbl = ["", "| Term | Coef | 95% CI | p |", "|---|---:|---|---:|"]
            for k, label in (("pre_trend", "Pre-trend"),
                             ("level_change", "Level change"),
                             ("slope_change", "Slope change")):
                t = res[k]
                star = " \\*" if t["p"] < 0.05 else ""
                tbl.append(f"| {label}{star} | {t['coef']} | "
                           f"{t['ci_low']} .. {t['ci_high']} | {t['p']} |")
            tbl.append(f"\n_R² = {res.get('r_squared')}; Newey–West (HAC) SEs; "
                       "\\* p < 0.05. Tagged **Causal(ITS)** with its assumptions (§6.2)._")
            blocks.append("\n".join(head + tbl))
        else:
            blocks.append("\n".join(head + [
                "", f"_{res.get('note', 'insufficient data')}_"]))
    return "\n\n".join(blocks)


def render(conn) -> str:
    """Full Markdown report: all four blocks with headings + paste hints."""
    sections = [
        ("§8 — Corpus counts (the v1 build)", corpus_counts(conn)),
        ("§5.4 / Figure 4 — HAPI domain + composite scores", hapi_scores_table(conn)),
        ("§5.3 — Weighting sensitivity", weighting_table(conn)),
        ("§6.2 / Figure 5 — Worked ITS coefficients", its_findings(conn)),
    ]
    parts = ["<!-- Generated by `hapi paper-tables`. Paste each block over the "
             "matching [TODO] in paper.md. -->"]
    for title, body in sections:
        parts.append(f"\n## {title}\n\n{body}")
    return "\n".join(parts)
