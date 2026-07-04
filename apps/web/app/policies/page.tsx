import type { Metadata } from "next";
import Link from "next/link";
import { getPolicies, type JurisdictionPolicies, type Policy } from "@/lib/policies";
import { PolicyTimeline, type TimelineItem } from "@/components/PolicyTimeline";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Policy Library",
  description:
    "A jurisdiction-aware, time-axis record of Canadian aging policy — each with its department, " +
    "budget, lifecycle, themes, and the outcome indicators it is intended to move.",
  path: "/policies",
});

export const dynamic = "force-dynamic";

function timelineItems(groups: JurisdictionPolicies[]): TimelineItem[] {
  return groups.flatMap((g) =>
    g.policies
      .map((p) => ({
        id: p.id,
        year: Number(p.releasedAt?.slice(0, 4)),
        title: p.title,
        jurisdiction: g.code,
        url: p.sourceUrl,
      }))
      .filter((d) => Number.isFinite(d.year)),
  );
}

function money(amount: string | null, currency: string | null): string | null {
  if (!amount) return null;
  const n = Number(amount);
  if (!Number.isFinite(n)) return null;
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 0 })} ${currency ?? "CAD"}`;
}

function PolicyCard({ p }: { p: Policy }) {
  const year = p.releasedAt?.slice(0, 4) ?? "—";
  const budget = money(p.budgetAmount, p.budgetCurrency);
  return (
    <li className="policy">
      <div className="policy-year">{year}</div>
      <div className="policy-body">
        <div className="policy-title">
          {p.title}
          {p.lifecycleStatus ? <span className="badge">{p.lifecycleStatus}</span> : null}
        </div>
        <div className="meta">
          {p.department}
          {budget ? <> · budget <span className="code">{budget}</span></> : null}
        </div>
        {p.aiSummary ? <p className="policy-summary">{p.aiSummary}</p> : null}
        <div className="policy-tags">
          {p.theme.map((t) => (
            <span key={t} className="tag">{t}</span>
          ))}
        </div>
        {p.indicators.length > 0 && (
          <div className="meta">
            targets:{" "}
            {p.indicators.map((c) => (
              <code key={c} className="code">{c} </code>
            ))}
          </div>
        )}
        {p.sourceUrl ? (
          <a className="meta" href={p.sourceUrl} target="_blank" rel="noreferrer">
            source ↗
          </a>
        ) : null}
      </div>
    </li>
  );
}

export default async function Policies() {
  let groups: JurisdictionPolicies[] | null = null;
  let error: string | null = null;
  try {
    groups = await getPolicies();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · Policy Library
      </p>
      <h1>Policy Library</h1>
      <p className="lede">
        A jurisdiction-aware, time-axis record of aging-related policy — each with
        its department, budget, lifecycle, themes, and the outcome indicators it is
        intended to move.
      </p>

      {error ? (
        <div className="panel error">
          <p>Could not read the database. Seed the Policy Library first:</p>
          <pre>
            <code>{"cd pipeline && python -m hapi_pipeline.cli policies seed"}</code>
          </pre>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            <code>{error}</code>
          </p>
        </div>
      ) : groups && groups.length > 0 ? (
        <>
          {(() => {
            const items = timelineItems(groups);
            return items.length > 1 ? (
              <section className="panel">
                <h2>Timeline</h2>
                <p className="meta">
                  Every catalogued policy on a shared year axis, coloured by jurisdiction —
                  when aging policy clustered, and where the quiet stretches are.
                </p>
                <PolicyTimeline items={items} />
              </section>
            ) : null;
          })()}
          {groups.map((g) => (
          <section className="panel" key={g.code}>
            <h2>{g.code}</h2>
            <ul className="timeline">
              {g.policies.map((p) => (
                <PolicyCard key={p.id} p={p} />
              ))}
            </ul>
          </section>
          ))}
        </>
      ) : (
        <p style={{ color: "var(--muted)" }}>
          No policies yet — run{" "}
          <code className="code">python -m hapi_pipeline.cli policies seed</code>.
        </p>
      )}
    </main>
  );
}
