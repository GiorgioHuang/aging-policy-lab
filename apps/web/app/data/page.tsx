import Link from "next/link";
import { getIndicatorGroups, type IndicatorGroup } from "@/lib/observations";

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

function GroupTable({ g }: { g: IndicatorGroup }) {
  const sample = g.rows[0];
  return (
    <section className="panel">
      <h2>
        {g.name} <span className="badge">{g.domain}</span>
        {g.unit ? <span className="code"> {g.unit}</span> : null}
      </h2>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginTop: 0 }}>
        <code className="code">{g.code}</code> · source: {g.datasourceName}
        {sample?.checksum ? (
          <>
            {" "}· dataset <code className="code">{sample.checksum.slice(0, 10)}</code>
          </>
        ) : null}{" "}
        <span className="badge">{g.isFixture ? "fixture" : "live"}</span>
      </p>
      <table className="data">
        <thead>
          <tr>
            <th>Jurisdiction</th>
            <th>Period</th>
            <th style={{ textAlign: "right" }}>Value</th>
            <th>Quality</th>
          </tr>
        </thead>
        <tbody>
          {g.rows.map((r, i) => (
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
            </tr>
          ))}
        </tbody>
      </table>
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

  const anyFixture = groups?.some((g) => g.isFixture) ?? false;

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · Data Hub
      </p>
      <h1>Data Hub</h1>
      <p className="lede">
        Every value below traces back to its source through an immutable
        observation and a versioned dataset (Observation → DatasetVersion →
        DataSource). Re-ingesting unchanged data is a no-op.
      </p>

      {anyFixture && (
        <div className="panel error">
          <strong>Sample data.</strong> Some series are loaded from vendored{" "}
          <em>fixture</em> payloads (this environment can&apos;t reach the live
          source domains). They are realistic but <strong>not</strong> official
          statistics; provenance is recorded as <code className="code">fixture:…</code>.
          Refresh with <code className="code">hapi ingest --live</code> where the network allows.
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
        groups.map((g) => <GroupTable key={g.code} g={g} />)
      ) : (
        <p style={{ color: "var(--muted)" }}>
          No observations yet — run{" "}
          <code className="code">python -m hapi_pipeline.cli ingest</code>.
        </p>
      )}
    </main>
  );
}
