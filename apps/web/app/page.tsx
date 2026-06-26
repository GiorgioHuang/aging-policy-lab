import Link from "next/link";
import { getJurisdictionTree, type JurisdictionNode } from "@/lib/jurisdictions";

// Always read live from the database (no static caching of the tree).
export const dynamic = "force-dynamic";

const MODULES: Array<{ n: string; name: string; desc: string; href?: string }> = [
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

export default async function Home() {
  let tree: JurisdictionNode[] | null = null;
  let error: string | null = null;
  try {
    tree = await getJurisdictionTree();
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

      <section className="panel">
        <h2>Jurisdiction tree (live from PostgreSQL)</h2>
        {error ? (
          <div className="error">
            <p>
              Could not read the database. Make sure Postgres is running and
              migrated:
            </p>
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
          </div>
        ) : tree && tree.length > 0 ? (
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

      <section className="panel">
        <h2>Platform modules</h2>
        <ul className="modules">
          {MODULES.map((m) => (
            <li key={m.name}>
              <span className="num">{m.n}</span>
              {m.href ? <Link href={m.href}>{m.name}</Link> : m.name}
              <br />
              <small>{m.desc}</small>
            </li>
          ))}
        </ul>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginBottom: 0 }}>
          Phase 2 (Data Hub) is live — explore ingested, lineage-tracked values in the{" "}
          <Link href="/data">Data Hub →</Link>. See <code className="code">docs/</code> for the
          design whitepaper and <code className="code">docs/11</code> for the roadmap.
        </p>
      </section>
    </main>
  );
}
