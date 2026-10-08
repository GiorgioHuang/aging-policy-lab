import type { Metadata } from "next";
import Link from "next/link";
import { getWatchOverview, WATCH_SOURCES, type Candidate, type WatchOverview } from "@/lib/watch";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Policy Watch",
  description:
    "New federal and Nova Scotia aging-policy items — news releases, regulations and bills — " +
    "found daily in official feeds and queued for review before they enter the Policy Library.",
  path: "/policies/watch",
});

export const dynamic = "force-dynamic";

const JURISDICTION_LABEL: Record<string, string> = { "CA-FED": "Federal", "CA-NS": "Nova Scotia" };

function day(ts: string | null): string {
  return ts ? ts.slice(0, 10) : "undated";
}

const RECENT_MS = 14 * 24 * 3600 * 1000;

/** True when a followed item's stage changed in the last two weeks. */
function recentlyProgressed(c: Candidate): boolean {
  return !!c.lastChangedAt && Date.now() - new Date(c.lastChangedAt).getTime() < RECENT_MS;
}

// Gazette items' summary is just the issue name, which the department line
// already conveys, so it is not repeated.
function CandidateCard({ c }: { c: Candidate }) {
  return (
    <li className="policy">
      <div className="policy-year">{day(c.publishedAt ?? c.firstSeenAt)}</div>
      <div className="policy-body">
        <div className="policy-title">
          <a href={c.url} target="_blank" rel="noreferrer">
            {c.title}
          </a>
          <span className="badge">{c.status === "accepted" ? "accepted" : "awaiting review"}</span>
          {c.aiCategory ? <span className="badge">{c.aiCategory}</span> : null}
          {recentlyProgressed(c) ? (
            <span className="badge" title="Its stage changed since it was found">
              progressed {day(c.lastChangedAt)}
            </span>
          ) : null}
        </div>
        <div className="meta">
          {JURISDICTION_LABEL[c.jurisdictionCode ?? ""] ?? c.jurisdictionCode}
          {c.department ? <> · {c.department}</> : null}
          {" · "}
          <code className="code">{c.source}</code>
        </div>
        {c.aiRationale ? (
          <p className="policy-summary">{c.aiRationale}</p>
        ) : c.summary && !c.source.startsWith("gazette_") ? (
          <p className="policy-summary">{c.summary.length > 280 ? `${c.summary.slice(0, 280)}…` : c.summary}</p>
        ) : null}
        {c.matchedTerms.length > 0 && (
          <div className="policy-tags">
            {c.matchedTerms.map((t) => (
              <span key={t} className="tag">{t}</span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

export default async function PolicyWatch() {
  let data: WatchOverview | null = null;
  let error: string | null = null;
  try {
    data = await getWatchOverview();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  const groups = new Map<string, Candidate[]>();
  for (const c of data?.candidates ?? []) {
    const key = c.jurisdictionCode ?? "other";
    groups.set(key, [...(groups.get(key) ?? []), c]);
  }

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · <Link href="/policies">Policy Library</Link> · Policy Watch
      </p>
      <h1>Policy Watch</h1>
      <p className="lede">
        New aging policy as it is published. Every day the observatory reads federal and
        Nova Scotia news releases, the Canada Gazette and Nova Scotia's Royal Gazette, and the
        bills before Parliament and the Nova Scotia Legislature, and keeps the items that concern older adults —
        long-term care, home care, dementia, caregivers, retirement income and more.
      </p>
      <p className="meta">
        These are <strong>leads, not library records</strong>: each is reviewed before it is
        added to the <Link href="/policies">Policy Library</Link> with its budget, lifecycle and
        outcome indicators.
      </p>

      {error ? (
        <div className="panel error">
          <p>Could not read the Policy Watch queue. Apply the migrations and run a fetch first:</p>
          <pre>
            <code>{"bash db/migrate.sh && cd pipeline && python -m hapi_pipeline.cli watch fetch --live"}</code>
          </pre>
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            <code>{error}</code>
          </p>
        </div>
      ) : data ? (
        <>
          <section className="kpis">
            <div className="kpi">
              <span className="kpi-value">{data.counts.new.toLocaleString()}</span>
              <span className="kpi-label">awaiting review</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{data.counts.accepted.toLocaleString()}</span>
              <span className="kpi-label">accepted into the library</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">
                {(data.counts.rejected + data.counts.auto_rejected).toLocaleString()}
              </span>
              <span className="kpi-label">set aside</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{day(data.latestFind)}</span>
              <span className="kpi-label">latest find</span>
            </div>
          </section>

          {data.candidates.length === 0 ? (
            <p style={{ color: "var(--muted)" }}>No new aging-policy items yet.</p>
          ) : (
            [...groups.entries()]
              .sort(([a], [b]) => (a === "CA-FED" ? -1 : b === "CA-FED" ? 1 : a.localeCompare(b)))
              .map(([jur, items]) => (
                <section className="panel" key={jur}>
                  <h2>{JURISDICTION_LABEL[jur] ?? jur}</h2>
                  <ul className="timeline">
                    {items.map((c) => (
                      <CandidateCard key={c.id} c={c} />
                    ))}
                  </ul>
                </section>
              ))
          )}

          <section className="panel">
            <h2>What is watched</h2>
            <ul className="dash-list">
              {WATCH_SOURCES.map((s) => {
                const found = s.key.reduce((n, k) => n + (data!.bySource[k] ?? 0), 0);
                return (
                  <li key={s.label}>
                    <span className="dash-list-main">
                      <a href={s.href} target="_blank" rel="noreferrer">{s.label}</a>
                    </span>
                    <span className="dash-list-meta">
                      <span className="badge">{s.jurisdiction}</span>
                      <span className="meta">
                        {s.stage} · {found} found
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
            <p className="meta">
              Matching is by weighted aging-policy terms, optionally checked by Claude; items
              it judges off-topic are kept for audit, not shown here. Method:{" "}
              <a
                href="https://github.com/GiorgioHuang/aging-policy-lab/blob/main/docs/04-module-policy-library.md#9-policy-watch--continuous-discovery"
                target="_blank"
                rel="noreferrer"
              >
                docs/04 §9
              </a>
              .
            </p>
          </section>
        </>
      ) : null}
    </main>
  );
}
