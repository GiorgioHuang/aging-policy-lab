import Link from "next/link";
import { getJurisdictionTree, type JurisdictionNode } from "@/lib/jurisdictions";
import { getAccessContext } from "@/lib/access";
import { getOverview, type Overview } from "@/lib/overview";

// Always read live from the database (no static caching of the dashboard).
export const dynamic = "force-dynamic";

const MODULES: Array<{ n: string; name: string; desc: string; href: string }> = [
  { n: "①", name: "Policy Library", desc: "Timeline of federal & provincial aging policy", href: "/policies" },
  { n: "②", name: "Data Hub", desc: "Versioned open-data ingestion & lineage", href: "/data" },
  { n: "③", name: "Indicators (HAPI)", desc: "Healthy Aging Policy Index", href: "/hapi" },
  { n: "④", name: "Policy Analytics", desc: "Association + quasi-experimental evaluation", href: "/analytics" },
  { n: "⑤", name: "AI Research Assistant", desc: "Cited evidence packs & literature reviews", href: "/assistant" },
];

function TreeNode({ node }: { node: JurisdictionNode }) {
  return (
    <li>
      {node.name}
      <span className="badge">{node.level}</span>
      {node.code ? <span className="code"> {node.code}</span> : null}
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
}

const KPIS: Array<{ key: keyof Overview["counts"]; label: string; href: string }> = [
  { key: "policies", label: "Policies", href: "/policies" },
  { key: "indicators", label: "Indicators", href: "/hapi" },
  { key: "observations", label: "Observations", href: "/data" },
  { key: "hapiScores", label: "HAPI scores", href: "/hapi" },
  { key: "findings", label: "Findings", href: "/analytics" },
  { key: "literature", label: "References", href: "/assistant" },
];

function scoreClass(v: number | null): string {
  if (v === null) return "";
  if (v >= 66) return "good";
  if (v >= 33) return "mid";
  return "low";
}

export default async function Home() {
  const ctx = await getAccessContext();

  let tree: JurisdictionNode[] | null = null;
  let overview: Overview | null = null;
  let error: string | null = null;
  try {
    [tree, overview] = await Promise.all([getJurisdictionTree(), getOverview(ctx)]);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="container">
      <p className="eyebrow">Healthy Aging Intelligence Lab</p>
      <h1>Canadian Healthy Aging Policy Observatory</h1>
      <p className="lede">
        Monitoring, quantifying, and evaluating the effect of aging policy across
        Canadian governments — starting with Nova Scotia and the federal level.
      </p>

      {error ? (
        <section className="panel error">
          <p>Could not read the database. Make sure Postgres is running and migrated:</p>
          <pre>
            <code>
              {"docker compose up -d db\n" +
                "bash db/migrate.sh --seed\n" +
                "npm run dev --workspace apps/web"}
            </code>
          </pre>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            <code>{error}</code>
          </p>
        </section>
      ) : (
        <>
          {overview && (
            <section className="kpis">
              {KPIS.map((k) => (
                <Link key={k.key} href={k.href} className="kpi">
                  <span className="kpi-value">{overview!.counts[k.key].toLocaleString()}</span>
                  <span className="kpi-label">{k.label}</span>
                </Link>
              ))}
            </section>
          )}

          {overview && overview.hapi.length > 0 && (
            <section className="panel">
              <h2>HAPI snapshot by jurisdiction</h2>
              <div className="snapshot">
                {overview.hapi.map((h) => (
                  <Link key={h.code} href="/hapi" className="snap-card">
                    <div className="snap-code">{h.code}</div>
                    <div className="snap-scores">
                      <div className="snap-metric">
                        <span className={`snap-num ${scoreClass(h.overall)}`}>
                          {h.overall === null ? "—" : h.overall.toFixed(0)}
                        </span>
                        <span className="snap-metric-label">Overall</span>
                      </div>
                      <div className="snap-metric">
                        <span className={`snap-num ${scoreClass(h.careAccess)}`}>
                          {h.careAccess === null ? "—" : h.careAccess.toFixed(0)}
                        </span>
                        <span className="snap-metric-label">Care access</span>
                      </div>
                    </div>
                    {h.period && <div className="snap-period">{h.period}</div>}
                  </Link>
                ))}
              </div>
              <p className="meta" style={{ marginBottom: 0 }}>
                Composite index, 0–100 (higher is better). Methodology: <Link href="/hapi">HAPI →</Link>
              </p>
            </section>
          )}

          <div className="dash-grid">
            {overview && (
              <section className="panel">
                <h2>Recent policies</h2>
                {overview.recentPolicies.length > 0 ? (
                  <ul className="dash-list">
                    {overview.recentPolicies.map((p, i) => (
                      <li key={i}>
                        <span className="dash-list-main">{p.title}</span>
                        <span className="dash-list-meta">
                          <span className="badge">{p.code}</span>
                          {p.lifecycle ? <span className="badge">{p.lifecycle}</span> : null}
                          {p.releasedAt ? <span className="code"> {p.releasedAt.slice(0, 10)}</span> : null}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="meta">No policies yet — run <code className="code">hapi policies seed</code>.</p>
                )}
                <p className="meta" style={{ marginBottom: 0 }}>
                  <Link href="/policies">All policies →</Link>
                </p>
              </section>
            )}

            {overview && (
              <section className="panel">
                <h2>Recent findings</h2>
                {overview.recentFindings.length > 0 ? (
                  <ul className="dash-list">
                    {overview.recentFindings.map((f, i) => (
                      <li key={i}>
                        <span className="dash-list-main">
                          {f.title}
                          <span className={`tier tier-${f.tier === "causal" ? "causal" : "association"}`}>
                            {f.tier === "causal" ? "Causal" : "Association"}
                          </span>
                        </span>
                        <span className="dash-list-meta">
                          <span className="code">{f.method}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="meta">No findings yet — run <code className="code">hapi analyze</code>.</p>
                )}
                <p className="meta" style={{ marginBottom: 0 }}>
                  <Link href="/analytics">All analytics →</Link>
                </p>
              </section>
            )}
          </div>

          <section className="panel">
            <h2>Platform modules</h2>
            <ul className="modules">
              {MODULES.map((m) => (
                <li key={m.name}>
                  <span className="num">{m.n}</span>
                  <Link href={m.href}>{m.name}</Link>
                  <br />
                  <small>{m.desc}</small>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel">
            <h2>Jurisdiction tree (live from PostgreSQL)</h2>
            {tree && tree.length > 0 ? (
              <ul className="tree">
                {tree.map((node) => (
                  <TreeNode key={node.id} node={node} />
                ))}
              </ul>
            ) : (
              <p style={{ color: "var(--muted)" }}>
                No jurisdictions yet — run <code className="code">bash db/migrate.sh --seed</code>.
              </p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
