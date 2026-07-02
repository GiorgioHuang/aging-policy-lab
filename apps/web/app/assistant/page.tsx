import Link from "next/link";
import { getEvidencePack, type EvidencePack } from "@/lib/assistant";
import { AssistantDraft } from "@/components/AssistantDraft";

export const dynamic = "force-dynamic";

const SUGGESTIONS = ["Nova Scotia dementia policy", "NS home care investment", "long-term care staffing"];

export default async function Assistant({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string }>;
}) {
  const { topic } = await searchParams;
  let pack: EvidencePack | null = null;
  let error: string | null = null;
  if (topic) {
    try {
      pack = await getEvidencePack(topic);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  return (
    <main className="container">
      <p className="eyebrow">
        <Link href="/">← Observatory</Link> · AI Research Assistant
      </p>
      <h1>AI Research Assistant</h1>
      <p className="lede">
        Turn a research topic into a grounded <strong>evidence pack</strong> — policies,
        literature, and analytic findings drawn from the platform&apos;s own stores, each
        with a citation id. A cited draft review is generated from this pack by the
        assistant (every claim cited; Association/Causal tags respected).
      </p>

      <form className="panel" method="get" action="/assistant">
        <input className="topic-input" type="text" name="topic" defaultValue={topic ?? ""}
               placeholder="e.g. Nova Scotia dementia policy" />
        <button type="submit">Retrieve</button>
        <div className="meta" style={{ marginTop: "0.5rem" }}>
          try:{" "}
          {SUGGESTIONS.map((s, i) => (
            <span key={s}>
              {i > 0 ? " · " : ""}
              <Link href={`/assistant?topic=${encodeURIComponent(s)}`}>{s}</Link>
            </span>
          ))}
        </div>
      </form>

      {error ? (
        <div className="panel error"><code>{error}</code></div>
      ) : pack ? (
        <>
          <p className="meta">
            {pack.policies.length} policies · {pack.literature.length} papers ·{" "}
            {pack.findings.length} findings
          </p>

          {pack.policies.length > 0 && (
            <section className="panel">
              <h2>Policies</h2>
              <ul className="evidence">
                {pack.policies.map((p) => (
                  <li key={p.cite}>
                    <span className="cite">{p.cite}</span> {p.title}{" "}
                    <span className="badge">{p.jurisdiction}</span>
                    {p.releasedAt ? <span className="code"> {p.releasedAt.slice(0, 4)}</span> : null}
                    {p.summary ? <div className="meta">{p.summary}</div> : null}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {pack.literature.length > 0 && (
            <section className="panel">
              <h2>Literature</h2>
              <ul className="evidence">
                {pack.literature.map((l) => (
                  <li key={l.cite}>
                    <span className="cite">{l.cite}</span>{" "}
                    {l.url ? <a href={l.url} target="_blank" rel="noreferrer">{l.title}</a> : l.title}{" "}
                    — {l.authors} ({l.year})
                    {l.abstract ? <div className="meta">{l.abstract}</div> : null}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {pack.findings.length > 0 && (
            <section className="panel">
              <h2>Analytic findings</h2>
              <ul className="evidence">
                {pack.findings.map((f) => (
                  <li key={f.cite}>
                    <span className="cite">{f.cite}</span> {f.title}{" "}
                    <span className={`tier tier-${f.tierLabel.startsWith("Causal") ? "causal" : "association"}`}>
                      {f.tierLabel}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <AssistantDraft topic={topic!} />
        </>
      ) : (
        <p style={{ color: "var(--muted)" }}>Enter a topic above to retrieve an evidence pack.</p>
      )}
    </main>
  );
}
