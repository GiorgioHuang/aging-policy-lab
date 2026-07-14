import type { Metadata } from "next";
import { LogoMark } from "@/components/Logo";
import { pageMetadata } from "@/lib/seo";
import {
  GITHUB_REPO_URL,
  PAPER1_PDF,
  PAPER1_SOURCE_URL,
  PAPER1_MARKDOWN_URL,
} from "@/lib/site";

// Render at request time so the footer reflects the runtime Cloud Run revision
// (K_REVISION) and the canonical host matches the other pages.
export const dynamic = "force-dynamic";

export const metadata: Metadata = pageMetadata({
  title: "Research",
  description:
    "Papers from the Healthy Aging Intelligence Lab. Paper 1 — Design of a Reproducible Healthy " +
    "Aging Policy Observatory — is available as a preprint; Papers 2–4 build on the same platform.",
  path: "/research",
});

// One platform, four papers. Paper 1 is the foundation; 2–4 deepen one cycle stage each.
const PROGRAM: Array<{ n: string; title: string; contribution: string; status: string }> = [
  {
    n: "1",
    title: "Design of a Reproducible Healthy Aging Policy Observatory",
    contribution: "Research infrastructure + the Policy Intelligence Cycle",
    status: "Preprint",
  },
  {
    n: "2",
    title: "The HAPI Methodology",
    contribution: "A transparent, sensitivity-tested composite-indicator framework",
    status: "Planned",
  },
  {
    n: "3",
    title: "AI-assisted Policy Intelligence",
    contribution: "Grounded retrieval + evidence synthesis",
    status: "Planned",
  },
  {
    n: "4",
    title: "Causal Evaluation of Canadian Aging Policies",
    contribution: "Interrupted time series / difference-in-differences / synthetic control",
    status: "Planned",
  },
];

export default function ResearchPage() {
  return (
    <main className="container research">
      <p className="eyebrow">Healthy Aging Intelligence Lab</p>
      <h1>Research</h1>
      <p className="lede">
        The Observatory is built as a research instrument, not a dashboard. Its work is written up as
        a focused program of papers — one platform, deepened paper by paper — each of which both uses
        and gives back to the same infrastructure.
      </p>

      {/* Featured: Paper 1 */}
      <article className="panel paper-feature">
        <div className="paper-body">
          <div className="paper-tags">
            <span className="badge paper-badge">Paper 1 · Preprint</span>
            <span className="paper-venue">2026 · not peer reviewed</span>
          </div>
          <h2 className="paper-title">
            Design of a Reproducible Healthy Aging Policy Observatory: Infrastructure for Trustworthy
            Aging-Policy Evidence in Canada
          </h2>
          <p className="paper-authors">
            Quangui Huang (Giorgio) · Independent researcher, Healthy Aging Intelligence Lab (HAIL)
            initiative
          </p>
          <p className="paper-abstract">
            The evidence base for aging policy suffers less from a shortage of analysis than from a
            shortage of <em>trustworthy infrastructure</em>. We argue these are{" "}
            <strong>infrastructure problems, not analysis problems</strong>, and present the design of
            a reproducible observatory organized around the <strong>Healthy Aging Policy Intelligence
            Cycle</strong> — a policy-level Learning Health System. Evaluated as a design, the
            instrument is traceable (every published value resolves to its source), reproducible
            (deterministic, idempotent), grounded (no fabricated AI citation is representable), and
            robust (the index ordering is invariant to weighting). The design itself is the
            contribution.
          </p>
          <div className="paper-actions">
            <a className="btn" href={PAPER1_PDF} target="_blank" rel="noopener noreferrer">
              Read the PDF
            </a>
            <a className="btn btn-ghost" href={PAPER1_SOURCE_URL} target="_blank" rel="noopener noreferrer">
              Source &amp; data
            </a>
            <a className="btn btn-ghost" href={PAPER1_MARKDOWN_URL} target="_blank" rel="noopener noreferrer">
              Manuscript (Markdown)
            </a>
          </div>
        </div>
        <a
          className="paper-figure"
          href={PAPER1_PDF}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Read the paper (PDF)"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/papers/intelligence-cycle.svg"
            alt="The Healthy Aging Policy Intelligence Cycle: Observation, Evidence, Indicator, Policy, Outcome, Feedback"
            width={520}
            height={360}
          />
          <span className="paper-figure-cap">Figure 1 — the Policy Intelligence Cycle</span>
        </a>
      </article>

      {/* The four-paper program */}
      <section>
        <h2>The research program</h2>
        <p className="meta">
          Each paper deposits assets back into the platform, so the program compounds rather than
          restarts. See the{" "}
          <a href={`${GITHUB_REPO_URL}/blob/main/docs/09-research-roadmap.md`} target="_blank" rel="noopener noreferrer">
            research roadmap
          </a>
          .
        </p>
        <ol className="paper-program">
          {PROGRAM.map((p) => (
            <li key={p.n} className={p.status === "Preprint" ? "is-available" : ""}>
              <span className="pp-num">{p.n}</span>
              <div className="pp-main">
                <span className="pp-title">{p.title}</span>
                <span className="pp-contrib">{p.contribution}</span>
              </div>
              <span className={`badge pp-status pp-${p.status.toLowerCase()}`}>{p.status}</span>
            </li>
          ))}
        </ol>
      </section>

      <p className="research-foot">
        <LogoMark size={16} /> Part of the Healthy Aging Intelligence Lab (HAIL). Every figure in the
        paper reproduces from the pipeline; the manuscript and its build are open on{" "}
        <a href={PAPER1_SOURCE_URL} target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        .
      </p>
    </main>
  );
}
