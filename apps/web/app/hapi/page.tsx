import Link from "next/link";
import { getHapiScores, type DomainScores, type HapiScoreRow } from "@/lib/hapi";
import { TrendChart, type ChartPoint } from "@/components/TrendChart";
import { type RadarAxis } from "@/components/DomainRadar";
import { DomainRadarOverTime, type RadarTemporalSeries } from "@/components/DomainRadarOverTime";

export const dynamic = "force-dynamic";

const DOMAIN_LABELS: Record<string, string> = {
  overall: "Composite HAPI",
  care_access: "Care Access",
  health: "Health",
  independence: "Independence",
  social_participation: "Social Participation",
  financial_security: "Financial Security",
  digital_inclusion: "Digital Inclusion",
};

// Short labels keep the radar rim readable.
const RADAR_LABELS: Record<string, string> = {
  care_access: "Care Access",
  health: "Health",
  independence: "Independence",
  social_participation: "Social",
  financial_security: "Financial",
  digital_inclusion: "Digital",
};
const JUR_COLORS: Record<string, string> = { "CA-FED": "#4f9dff", "CA": "#4f9dff", "CA-NS": "#3ecf8e" };

/** Per-year score per (domain, jurisdiction) for the temporal radar profile. */
function buildRadar(
  domains: DomainScores[],
): { axes: RadarAxis[]; years: string[]; series: RadarTemporalSeries[] } | null {
  const domainKeys = new Set<string>();
  const yearSet = new Set<string>();
  const byJur = new Map<string, Record<string, Record<string, number>>>(); // code -> year -> domain -> score
  for (const d of domains) {
    if (d.domain === "overall") continue;
    for (const s of d.byJurisdiction) {
      for (const r of s.rows) {
        if (r.score === null) continue;
        const yr = r.period.slice(0, 4);
        domainKeys.add(d.domain);
        yearSet.add(yr);
        const m = byJur.get(s.code) ?? {};
        (m[yr] ??= {})[d.domain] = Number(r.score); // rows period-ascending → latest within year wins
        byJur.set(s.code, m);
      }
    }
  }
  const axes: RadarAxis[] = [...domainKeys].sort().map((key) => ({ key, label: RADAR_LABELS[key] ?? key }));
  if (axes.length < 3 || byJur.size === 0) return null;
  const series: RadarTemporalSeries[] = [...byJur.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([code, byYear]) => ({ code, color: JUR_COLORS[code] ?? "#e0a23b", byYear }));
  return { axes, years: [...yearSet].sort(), series };
}

function points(rows: HapiScoreRow[]): ChartPoint[] {
  return rows
    .filter((r) => r.score !== null)
    .map((r) => ({ label: r.period.slice(0, 4), value: Number(r.score) }));
}

function AuditRow({ r }: { r: HapiScoreRow }) {
  const inds = r.inputs?.indicators ?? [];
  const domainScores = r.inputs?.domain_scores;
  return (
    <tr>
      <td>{r.jurisdictionCode}</td>
      <td>{r.period.slice(0, 4)}</td>
      <td style={{ textAlign: "right" }}>{r.score}</td>
      <td>
        {inds.length > 0
          ? inds.map((i) => (
              <div key={i.code} style={{ fontSize: "0.8rem" }}>
                <code className="code">{i.code}</code>: {i.raw.toLocaleString()}
                {i.denominator
                  ? ` / ${i.denominator.toLocaleString()} → ${i.value} → norm ${i.normalized}`
                  : ` → norm ${i.normalized}`}
              </div>
            ))
          : domainScores
            ? Object.entries(domainScores).map(([d, s]) => (
                <span key={d} className="badge">
                  {DOMAIN_LABELS[d] ?? d}: {s}
                </span>
              ))
            : null}
      </td>
    </tr>
  );
}

function DomainPanel({ d }: { d: DomainScores }) {
  const method = d.byJurisdiction[0]?.rows[0]?.methodVersion ?? "v1";
  return (
    <section className="panel">
      <h2>
        {DOMAIN_LABELS[d.domain] ?? d.domain}{" "}
        <span className="badge">method {method}</span>
        <span className="code"> 0–100</span>
      </h2>
      <div className="charts">
        {d.byJurisdiction.map((s) => (
          <figure className="series" key={s.code}>
            <figcaption className="series-head">{s.code}</figcaption>
            <TrendChart
              points={points(s.rows)}
              direction="higher_is_better"
              unit="/100"
              yMin={0}
              yMax={100}
            />
          </figure>
        ))}
      </div>
      <details className="lineage">
        <summary>Scores &amp; inputs (auditable)</summary>
        <table className="data">
          <thead>
            <tr>
              <th>Jurisdiction</th>
              <th>Period</th>
              <th style={{ textAlign: "right" }}>Score</th>
              <th>Inputs (raw → per-capita → normalized)</th>
            </tr>
          </thead>
          <tbody>
            {d.byJurisdiction.flatMap((s) => s.rows.map((r) => <AuditRow key={`${r.jurisdictionCode}-${r.period}`} r={r} />))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

export default async function Hapi() {
  let domains: DomainScores[] | null = null;
  let error: string | null = null;
  try {
    domains = await getHapiScores();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · HAPI
      </p>
      <h1>Healthy Aging Policy Index (HAPI)</h1>
      <p className="lede">
        An independent, documented index scoring how well a jurisdiction supports
        healthy aging, 0–100, over time. v1 implements the methodology end-to-end on
        the Care Access domain; every score is auditable to its raw inputs.
      </p>

      <div className="panel" style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
        HAPI measures outcome <em>states and trends</em>. It does <strong>not</strong> by
        itself prove a policy caused a change — attribution needs the quasi-experimental
        designs in the analytics module. Other domains join as their connectors land.
      </div>

      {error ? (
        <div className="panel error">
          <p>Could not read the database. Compute HAPI first:</p>
          <pre>
            <code>{"cd pipeline && python -m hapi_pipeline.cli ingest && python -m hapi_pipeline.cli score"}</code>
          </pre>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            <code>{error}</code>
          </p>
        </div>
      ) : domains && domains.length > 0 ? (
        <>
          {(() => {
            const radar = buildRadar(domains);
            return radar ? (
              <section className="panel">
                <h2>
                  Domain profile <span className="badge">over time</span>
                  <span className="code"> 0–100</span>
                </h2>
                <p className="meta">
                  Each jurisdiction&apos;s score on every scored HAPI domain, as of the selected
                  year — drag the slider to watch the profile evolve. Per-domain trends and the
                  full audit trail are below.
                </p>
                <DomainRadarOverTime axes={radar.axes} years={radar.years} series={radar.series} />
              </section>
            ) : null;
          })()}
          {domains.map((d) => <DomainPanel key={d.domain} d={d} />)}
        </>
      ) : (
        <p style={{ color: "var(--muted)" }}>
          No scores yet — run{" "}
          <code className="code">python -m hapi_pipeline.cli score</code>.
        </p>
      )}
    </main>
  );
}
