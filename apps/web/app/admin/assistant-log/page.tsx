import type { Metadata } from "next";
import {
  listAssistantLogs,
  assistantLogSummary,
  type AssistantLogRow,
} from "@/lib/assistant";

// Always read live; never cache or statically render.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Assistant log — Admin",
  robots: { index: false, follow: false },
};

function fmtDate(iso: string): string {
  return new Date(iso).toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function num(n: number | null): string {
  return n === null ? "—" : n.toLocaleString();
}

function Entry({ r }: { r: AssistantLogRow }) {
  return (
    <article className={`log-row log-${r.status}`}>
      <header className="log-head">
        <span className={`badge log-badge-${r.status}`}>{r.status}</span>
        <strong className="log-topic">{r.topic}</strong>
        <span className="log-time">{fmtDate(r.createdAt)}</span>
      </header>

      <div className="log-meta">
        <span>{r.model ?? "—"}</span>
        <span>
          pack {num(r.nPolicies)}P · {num(r.nLiterature)}L · {num(r.nFindings)}F
        </span>
        <span>
          {num(r.inputTokens)} → {num(r.outputTokens)} tok
        </span>
        <span>{r.latencyMs === null ? "—" : `${num(r.latencyMs)} ms`}</span>
        {r.ip ? <span>{r.ip}</span> : null}
      </div>

      {r.error ? <p className="log-error-msg">⚠ {r.error}</p> : null}

      {r.draft ? (
        <details className="log-draft">
          <summary>Draft ({r.draft.length.toLocaleString()} chars)</summary>
          <div className="log-draft-body">{r.draft}</div>
        </details>
      ) : r.error ? null : (
        <p className="log-nodraft">No output ({r.status}).</p>
      )}
    </article>
  );
}

export default async function AdminAssistantLogPage() {
  const [rows, summary] = await Promise.all([listAssistantLogs(300), assistantLogSummary()]);
  const statuses = ["ok", "empty_pack", "refusal", "error"];

  return (
    <main className="container admin">
      <nav className="admin-nav">
        <a href="/admin/messages">Contact inbox</a>
        <span className="admin-nav-here">Assistant log</span>
      </nav>
      <h1>Assistant log</h1>
      <p className="admin-summary">
        {summary.total} generation{summary.total === 1 ? "" : "s"}
        {" · "}
        {statuses.map((s) => `${summary.byStatus[s] ?? 0} ${s}`).join(" · ")}
        {" · "}
        {summary.outputTokens.toLocaleString()} output tokens
      </p>

      {rows.length === 0 ? (
        <div className="panel">No generations logged yet.</div>
      ) : (
        <div className="msg-list">
          {rows.map((r) => (
            <Entry key={r.id} r={r} />
          ))}
        </div>
      )}
    </main>
  );
}
