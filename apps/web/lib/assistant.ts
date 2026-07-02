import Anthropic from "@anthropic-ai/sdk";
import { pool } from "./db";

const STOPWORDS = new Set([
  "and", "the", "for", "with", "from", "that", "this", "policy", "policies",
  "are", "was", "were", "have", "has", "about", "into", "over", "near",
]);

function terms(topic: string): string[] {
  return (topic.toLowerCase().match(/[a-z][a-z-]{2,}/g) ?? []).filter((w) => !STOPWORDS.has(w));
}

const matches = (text: string | null, ts: string[]) =>
  !!text && ts.some((t) => text.toLowerCase().includes(t));

export type EvidencePolicy = {
  cite: string; title: string; jurisdiction: string; department: string | null;
  releasedAt: string | null; lifecycle: string | null; summary: string | null;
};
export type EvidenceLit = {
  cite: string; title: string; authors: string | null; year: number | null;
  venue: string | null; url: string | null; abstract: string | null;
};
export type EvidenceFinding = {
  cite: string; title: string; tierLabel: string; indicator: string | null;
};
export type EvidencePack = {
  topic: string;
  policies: EvidencePolicy[];
  literature: EvidenceLit[];
  findings: EvidenceFinding[];
};

export async function getEvidencePack(topic: string): Promise<EvidencePack> {
  const ts = terms(topic);
  const empty: EvidencePack = { topic, policies: [], literature: [], findings: [] };
  if (ts.length === 0) return empty;

  const [pol, lit, find] = await Promise.all([
    pool.query(`SELECT p.id, j.code AS jur, p.title, p.department, p.released_at::text,
                       p.lifecycle_status, p.theme, p.ai_summary, p.full_text
                  FROM policy p JOIN jurisdiction j ON j.id = p.jurisdiction_id`),
    pool.query(`SELECT id, title, authors, year, venue, url, abstract, topics FROM literature`),
    pool.query(`SELECT id, title, tier, method, indicator_code FROM analysis_finding`),
  ]);

  const policies: EvidencePolicy[] = pol.rows
    .filter((r) =>
      matches([r.title, (r.theme ?? []).join(" "), r.ai_summary, r.full_text].join(" "), ts))
    .map((r) => ({
      cite: `P${r.id}`, title: r.title, jurisdiction: r.jur, department: r.department,
      releasedAt: r.released_at, lifecycle: r.lifecycle_status, summary: r.ai_summary,
    }));

  const literature: EvidenceLit[] = lit.rows
    .filter((r) => matches([r.title, r.abstract, (r.topics ?? []).join(" ")].join(" "), ts))
    .map((r) => ({
      cite: `L${r.id}`, title: r.title, authors: r.authors, year: r.year,
      venue: r.venue, url: r.url, abstract: r.abstract,
    }));

  const topicHead = ts.map((t) => t);
  const findings: EvidenceFinding[] = find.rows
    .filter((r) =>
      matches([r.title, r.indicator_code].join(" "), ts) ||
      matches(r.indicator_code, topicHead))
    .map((r) => ({
      cite: `F${r.id}`,
      title: r.title,
      tierLabel: r.tier === "causal" ? (r.method === "its" ? "Causal(ITS)" : "Causal") : "Association",
      indicator: r.indicator_code,
    }));

  return { topic, policies, literature, findings };
}

// ── Cited draft review (Claude) ───────────────────────────────────────────────
// The draft is generated from the *same* evidence pack the page renders, so every
// [P#]/[L#]/[F#] tag maps to a visible item. Mirrors pipeline/hapi_pipeline/ai/
// assistant.py so the web and CLI produce the same grounded, cited output.

const DRAFT_MODEL = process.env.HAPI_SUMMARY_MODEL || "claude-opus-4-8";

const DRAFT_SYSTEM =
  "You draft cited literature-review starting points for a Canadian healthy-aging " +
  "policy research platform. STRICT RULES: (1) Every factual claim must end with a " +
  "citation tag in square brackets referencing an item id from the EVIDENCE PACK " +
  "(e.g. [P3], [L2], [F1]). (2) Use ONLY the pack — never invent sources, numbers, " +
  "or references. (3) When you mention an analytic finding, state its tier exactly as " +
  "given (Association or Causal(ITS)) and NEVER upgrade an association to a causal " +
  "claim. (4) This is a draft + evidence for a human researcher, not a verdict. " +
  "Structure: Background, Policy landscape, Evidence & indicators, Gaps & next steps. " +
  "250-450 words. End with a 'Sources' list mapping each tag you used to its title.";

export type DraftResult = { draft: string | null; reason: string | null };

function packIsEmpty(pack: EvidencePack): boolean {
  return pack.policies.length + pack.literature.length + pack.findings.length === 0;
}

/**
 * Generate the cited draft review from an evidence pack. Returns a structured
 * result rather than throwing so the caller can show a graceful message:
 *   reason "no_api_key"  — ANTHROPIC_API_KEY isn't configured on the server
 *   reason "empty_pack"  — nothing to cite
 *   reason "refusal"     — the model declined (safety)
 *   reason "error"       — an API/network failure (logged server-side)
 */
export async function draftReview(pack: EvidencePack): Promise<DraftResult> {
  if (!process.env.ANTHROPIC_API_KEY) return { draft: null, reason: "no_api_key" };
  if (packIsEmpty(pack)) return { draft: null, reason: "empty_pack" };

  const client = new Anthropic();
  try {
    const response = await client.messages.create({
      model: DRAFT_MODEL,
      max_tokens: 1500,
      system: DRAFT_SYSTEM,
      messages: [
        {
          role: "user",
          content: `Topic: ${pack.topic}\n\nEVIDENCE PACK (JSON):\n${JSON.stringify(pack)}`,
        },
      ],
    });
    if (response.stop_reason === "refusal") return { draft: null, reason: "refusal" };
    const text = response.content
      .map((b) => (b.type === "text" ? b.text : ""))
      .join("")
      .trim();
    return text ? { draft: text, reason: null } : { draft: null, reason: "error" };
  } catch (e) {
    console.error("draftReview failed:", e);
    return { draft: null, reason: "error" };
  }
}
