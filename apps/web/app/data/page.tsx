import Link from "next/link";
import {
  getIndicatorGroups,
  type IndicatorGroup,
  type LineageRow,
} from "@/lib/observations";
import { TrendChart, type ChartPoint } from "@/components/TrendChart";

export const dynamic = "force-dynamic";

function fmt(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : value;
}

// Postgres stores daterange canonically as [lower, upper) — the upper bound is
// exclusive, so a full calendar year is [YYYY-01-01, (YYYY+1)-01-01). Show such a
// range as "YYYY"; anything shorter (e.g. a month) shows as "YYYY-MM".
function periodLabel(start: string, end: string): string {
  const year = Number(start.slice(0, 4));
  if (start.endsWith("-01-01") && end === `${year + 1}-01-01`) {
    return String(year);
  }
  return start.slice(0, 7);
}

// One time series per jurisdiction (nulls/suppressed points dropped).
function seriesByJurisdiction(rows: LineageRow[]): { code: string; points: ChartPoint[] }[] {
  const map = new Map<string, ChartPoint[]>();
  for (const r of rows) {
    if (r.value === null) continue;
    const v = Number(r.value);
    if (!Number.isFinite(v)) continue;
    const arr = map.get(r.jurisdictionCode) ?? [];
    arr.push({ label: periodLabel(r.periodStart, r.periodEnd), value: v });
    map.set(r.jurisdictionCode, arr);
  }
  return [...map.entries()].map(([code, points]) => ({ code, points }));
}

function GroupPanel({ g }: { g: IndicatorGroup }) {
  const sample = g.rows[0];
  const series = seriesByJurisdiction(g.rows);
  return (
    <section className="panel">
      <h2>
        {g.name} <span className="badge">{g.domain}</span>
        {g.unit ? <span className="code"> {g.unit}</span> : null}
      </h2>
      <p className="meta">
        <code className="code">{g.code}</code> · source: {g.datasourceName}
        {sample?.checksum ? (
          <>
            {" "}· dataset <code className="code">{sample.checksum.slice(0, 10)}</code>
          </>
        ) : null}{" "}
        <span className="badge">{g.isFixture ? "fixture" : "live"}</span>
      </p>

      {series.length > 0 && (
        <div className="charts">
          {series.map((s) => (
            <figure className="series" key={s.code}>
              <figcaption className="series-head">{s.code}</figcaption>
              <TrendChart points={s.points} direction={g.direction} unit={g.unit} />
            </figure>
          ))}
        </div>
      )}

      <details className="lineage">
        <summary>Data &amp; lineage ({g.rows.length} observations)</summary>
        <table className="data">
          <thead>
            <tr>
              <th>Jurisdiction</th>
              <th>Period</th>
              <th style={{ textAlign: "right" }}>Value</th>
              <th>Quality</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {g.rows.map((r, i) => {
              const isFix = (r.sourceVersion ?? "").startsWith("fixture:");
              const title = [r.datasourceName, r.sourceVersion].filter(Boolean).join(" · ");
              return (
                <tr key={`${r.jurisdictionCode}-${r.periodStart}-${i}`}>
                  <td>{r.jurisdictionCode}</td>
                  <td>{periodLabel(r.periodStart, r.periodEnd)}</td>
                  <td style={{ textAlign: "right" }}>{fmt(r.value)}</td>
                  <td>
                    {r.qualityFlag === "ok" ? (
                      <span style={{ color: "var(--muted)" }}>ok</span>
                    ) : (
                      <span className="badge">{r.qualityFlag}</span>
                    )}
                  </td>
                  <td title={title || undefined}>
                    <span className={isFix ? "badge" : ""} style={isFix ? undefined : { color: "var(--good)" }}>
                      {isFix ? "fixture" : "live"}
                    </span>
                    {r.checksum ? (
                      <code className="code" style={{ marginLeft: "0.4rem" }}>{r.checksum.slice(0, 8)}</code>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </details>
    </section>
  );
}

export default async function DataHub() {
  let groups: IndicatorGroup[] | null = null;
  let error: string | null = null;
  try {
    groups = await getIndicatorGroups();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  const fixtureSources = groups
    ? [...new Set(groups.filter((g) => g.isFixture).map((g) => g.datasourceName))]
    : [];

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · Data Hub
      </p>
      <h1>Data Hub</h1>
      <p className="lede">
        Every value traces back to its source through an immutable observation and
        a versioned dataset (Observation → DatasetVersion → DataSource). Re-ingesting
        unchanged data is a no-op.
      </p>

      {fixtureSources.length > 0 && (
        <div className="panel error">
          <strong>Fixture-sourced series.</strong> {fixtureSources.join("; ")} —
          tagged <code className="code">fixture</code> below — load from a vendored
          payload rather than a live pull (CIHI has no open API). Provenance is
          recorded as <code className="code">fixture:…</code>; live series instead
          show <code className="code">WDS:</code> / <code className="code">SODA:</code>.
        </div>
      )}

      {error ? (
        <div className="panel error">
          <p>Could not read the database. Bring it up and ingest first:</p>
          <pre>
            <code>
              {"docker compose up -d db\n" +
                "bash db/migrate.sh --seed\n" +
                "cd pipeline && python -m hapi_pipeline.cli ingest"}
            </code>
          </pre>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            <code>{error}</code>
          </p>
        </div>
      ) : groups && groups.length > 0 ? (
        groups.map((g) => <GroupPanel key={g.code} g={g} />)
      ) : (
        <p style={{ color: "var(--muted)" }}>
          No observations yet — run{" "}
          <code className="code">python -m hapi_pipeline.cli ingest</code>.
        </p>
      )}
    </main>
  );
}
