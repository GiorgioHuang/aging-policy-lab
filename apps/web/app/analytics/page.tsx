import Link from "next/link";
import { getFindings, getSeries, type Finding } from "@/lib/analytics";
import { TrendChart, type ChartPoint } from "@/components/TrendChart";
import { ItsChart, type ItsModel } from "@/components/ItsChart";

export const dynamic = "force-dynamic";

type Term = { coef: number; se: number; ci_low: number; ci_high: number; p: number };

function TierBadge({ tier, method }: { tier: string; method: string }) {
  const label = tier === "causal" ? `Causal (${method.toUpperCase()})` : "Association";
  return <span className={`tier tier-${tier}`}>{label}</span>;
}

function num(v: unknown): string {
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : "—";
}

function TrendResult({ r }: { r: Record<string, unknown> }) {
  const pct = r.pct_change == null ? "—" : `${num(r.pct_change)}%`;
  return (
    <p className="meta">
      {r.from as string} → {r.to as string}: {num(r.start_value)} → {num(r.end_value)} (
      {pct}, {String(r.direction)})
    </p>
  );
}

function CoefRow({ label, t }: { label: string; t: Term | undefined }) {
  if (!t) return null;
  const sig = t.p < 0.05;
  return (
    <tr>
      <td>
        {label} {sig ? <span title="significant at p < 0.05" style={{ color: "#3ecf8e" }}>✱</span> : null}
      </td>
      <td style={{ textAlign: "right" }}>{num(t.coef)}</td>
      <td>[{num(t.ci_low)}, {num(t.ci_high)}]</td>
      <td>{t.p}</td>
    </tr>
  );
}

function ItsResult({ r }: { r: Record<string, unknown> }) {
  if (r.status !== "ok") {
    return <p className="meta">{String(r.note ?? "insufficient data")}</p>;
  }
  const rsq = r.r_squared == null ? null : num(r.r_squared);
  return (
    <>
      <table className="data" style={{ maxWidth: 540 }}>
        <thead>
          <tr><th>Effect</th><th style={{ textAlign: "right" }}>Coef</th><th>95% CI</th><th>p</th></tr>
        </thead>
        <tbody>
          <CoefRow label="Pre-trend (per step)" t={r.pre_trend as Term} />
          <CoefRow label="Level change" t={r.level_change as Term} />
          <CoefRow label="Slope change" t={r.slope_change as Term} />
        </tbody>
      </table>
      <p className="meta">
        {`n = ${r.n_pre} pre / ${r.n_post} post`}
        {rsq ? ` · R² ${rsq}` : ""} · Newey–West (HAC) standard errors
      </p>
    </>
  );
}

function FindingCard({ f, series }: { f: Finding; series: ChartPoint[] }) {
  const r = f.result ?? {};
  const intervention = (f.windowSpec?.intervention as string) ?? null;
  const isIts = f.method === "its";
  // Use the segmented-regression chart for an estimable ITS that carries an
  // intercept (needed to reconstruct the fitted lines); otherwise the plain trend.
  const itsModel =
    isIts && r.status === "ok" && (r as Record<string, unknown>).intercept != null
      ? (r as unknown as ItsModel)
      : null;
  const interventionLabel = intervention ? intervention.slice(0, 7) : null;
  return (
    <section className="panel">
      <h2>
        {f.title} <TierBadge tier={f.tier} method={f.method} />
      </h2>
      <p className="meta">
        {f.indicatorCode ? <code className="code">{f.indicatorCode}</code> : null}
        {f.jurisdictionCode ? ` · ${f.jurisdictionCode}` : null}
        {f.policyTitle ? <> · policy: {f.policyTitle}</> : null}
        {intervention ? <> · event {intervention}</> : null}
      </p>

      {itsModel && series.length > 1 ? (
        <ItsChart points={series} model={itsModel} interventionLabel={interventionLabel} />
      ) : series.length > 1 ? (
        <TrendChart points={series} direction="higher_is_better" />
      ) : null}

      {isIts ? <ItsResult r={r} /> : <TrendResult r={r} />}

      <p className="meta"><strong>Assumptions.</strong> {f.assumptions}</p>
      <p className="meta"><strong>Limitations.</strong> {f.limitations}</p>
    </section>
  );
}

export default async function Analytics() {
  let findings: Finding[] | null = null;
  let seriesList: ChartPoint[][] = [];
  let error: string | null = null;
  try {
    findings = await getFindings();
    seriesList = await Promise.all(
      findings.map((f) =>
        f.indicatorCode && f.jurisdictionCode
          ? getSeries(f.indicatorCode, f.jurisdictionCode)
          : Promise.resolve([] as ChartPoint[]),
      ),
    );
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · Policy Analytics
      </p>
      <h1>Policy Analytics</h1>
      <p className="lede">
        Connecting policies to outcomes — with the platform&apos;s core discipline made
        explicit: <strong>association is not causation</strong>. Every result is tagged
        Association or Causal, and causal results carry their design, assumptions, and
        limitations.
      </p>

      {error ? (
        <div className="panel error">
          <p>Could not read the database. Compute findings first:</p>
          <pre><code>{"cd pipeline && python -m hapi_pipeline.cli analyze"}</code></pre>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}><code>{error}</code></p>
        </div>
      ) : findings && findings.length > 0 ? (
        findings.map((f, i) => <FindingCard key={f.id} f={f} series={seriesList[i]} />)
      ) : (
        <p style={{ color: "var(--muted)" }}>
          No findings yet — run <code className="code">python -m hapi_pipeline.cli analyze</code>.
        </p>
      )}
    </main>
  );
}
