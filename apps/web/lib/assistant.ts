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

// ── Assistant log (read side, for /admin/assistant-log) ───────────────────────

export type AssistantLogRow = {
  id: string;
  createdAt: string;
  topic: string;
  model: string | null;
  status: string;
  draft: string | null;
  nPolicies: number | null;
  nLiterature: number | null;
  nFindings: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  latencyMs: number | null;
  ip: string | null;
  error: string | null;
};

export async function listAssistantLogs(limit = 200): Promise<AssistantLogRow[]> {
  const { rows } = await pool.query<{
    id: string;
    created_at: string;
    topic: string;
    model: string | null;
    status: string;
    draft: string | null;
    n_policies: number | null;
    n_literature: number | null;
    n_findings: number | null;
    input_tokens: number | null;
    output_tokens: number | null;
    latency_ms: number | null;
    ip: string | null;
    error: string | null;
  }>(
    `SELECT id, created_at::text AS created_at, topic, model, status, draft,
            n_policies, n_literature, n_findings, input_tokens, output_tokens,
            latency_ms, ip, error
       FROM assistant_log
   ORDER BY created_at DESC
      LIMIT $1`,
    [limit],
  );
  return rows.map((r) => ({
    id: r.id,
    createdAt: r.created_at,
    topic: r.topic,
    model: r.model,
    status: r.status,
    draft: r.draft,
    nPolicies: r.n_policies,
    nLiterature: r.n_literature,
    nFindings: r.n_findings,
    inputTokens: r.input_tokens,
    outputTokens: r.output_tokens,
    latencyMs: r.latency_ms,
    ip: r.ip,
    error: r.error,
  }));
}

/** Header summary: total rows, per-status counts, and cumulative output tokens. */
export async function assistantLogSummary(): Promise<{
  total: number;
  byStatus: Record<string, number>;
  outputTokens: number;
}> {
  const { rows } = await pool.query<{ status: string; n: string; out: string | null }>(
    `SELECT status, count(*)::text AS n, coalesce(sum(output_tokens), 0)::text AS out
       FROM assistant_log GROUP BY status`,
  );
  const byStatus: Record<string, number> = {};
  let total = 0;
  let outputTokens = 0;
  for (const r of rows) {
    const n = Number(r.n);
    byStatus[r.status] = n;
    total += n;
    outputTokens += Number(r.out ?? 0);
  }
  return { total, byStatus, outputTokens };
}

/** Delete one log row (id is a numeric bigint, validated before binding). */
export async function deleteAssistantLog(id: string): Promise<void> {
  if (!/^\d+$/.test(id)) throw new Error(`invalid id: ${id}`);
  await pool.query(`DELETE FROM assistant_log WHERE id = $1`, [id]);
}

/** Delete every log row. */
export async function clearAssistantLogs(): Promise<void> {
  await pool.query(`DELETE FROM assistant_log`);
}

// ── Cited draft review (Claude) ───────────────────────────────────────────────
// The draft is generated from the *same* evidence pack the page renders, so every
// [P#]/[L#]/[F#] tag maps to a visible item. Mirrors pipeline/hapi_pipeline/ai/
// assistant.py so the web and CLI produce the same grounded, cited output.

// Sonnet by default for the web draft (fast + economical for a public endpoint);
// override with HAPI_ASSISTANT_MODEL. Kept independent of the pipeline's
// HAPI_SUMMARY_MODEL so the two can be tuned separately.
const DRAFT_MODEL = process.env.HAPI_ASSISTANT_MODEL || "claude-sonnet-5";

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

type LogInfo = {
  status: "ok" | "empty_pack" | "refusal" | "error";
  model?: string;
  draft?: string | null;
  latencyMs?: number;
  inputTokens?: number;
  outputTokens?: number;
  error?: string; // error message (Cloud Run log only; not stored)
};

// Record a generation: a structured line for Cloud Run logs (metadata only) plus
// a durable audit row in assistant_log (migration 0007). Best-effort — a logging
// failure must never break the user's response, so everything is swallowed.
async function logDraft(
  pack: EvidencePack,
  info: LogInfo,
  meta: { ip?: string },
): Promise<void> {
  try {
    console.log(
      JSON.stringify({
        evt: "assistant_draft",
        topic: pack.topic,
        status: info.status,
        model: info.model ?? null,
        n_policies: pack.policies.length,
        n_literature: pack.literature.length,
        n_findings: pack.findings.length,
        input_tokens: info.inputTokens ?? null,
        output_tokens: info.outputTokens ?? null,
        latency_ms: info.latencyMs ?? null,
        error: info.error ?? null,
      }),
    );
  } catch {
    /* console never throws in practice; ignore */
  }
  try {
    await pool.query(
      `INSERT INTO assistant_log
         (topic, model, status, draft, n_policies, n_literature, n_findings,
          input_tokens, output_tokens, latency_ms, ip, error)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
      [
        pack.topic.slice(0, 200),
        info.model ?? null,
        info.status,
        info.draft ?? null,
        pack.policies.length,
        pack.literature.length,
        pack.findings.length,
        info.inputTokens ?? null,
        info.outputTokens ?? null,
        info.latencyMs ?? null,
        (meta.ip ?? "").slice(0, 100) || null,
        info.error ? info.error.slice(0, 500) : null,
      ],
    );
  } catch (e) {
    console.error("assistant_log insert failed:", e);
  }
}

/**
 * Generate the cited draft review from an evidence pack. Every generation (not
 * cache hits) is logged to assistant_log + Cloud Run. Returns a structured result
 * rather than throwing so the caller can show a graceful message:
 *   reason "no_api_key"  — ANTHROPIC_API_KEY isn't configured on the server
 *   reason "empty_pack"  — nothing to cite
 *   reason "refusal"     — the model declined (safety)
 *   reason "error"       — an API/network failure (logged server-side)
 */
export async function draftReview(
  pack: EvidencePack,
  meta: { ip?: string } = {},
): Promise<DraftResult> {
  if (!process.env.ANTHROPIC_API_KEY) return { draft: null, reason: "no_api_key" };
  if (packIsEmpty(pack)) {
    await logDraft(pack, { status: "empty_pack" }, meta);
    return { draft: null, reason: "empty_pack" };
  }

  const client = new Anthropic();
  const startedAt = Date.now();
  try {
    const response = await client.messages.create({
      model: DRAFT_MODEL,
      // Leave thinking on its default (adaptive on Sonnet 5). An explicit
      // thinking:{type:"disabled"} was rejected by the deployed model. Adaptive
      // thinking spends tokens from max_tokens, so budget generously (4000) so the
      // ~450-word draft + Sources always fits without truncation.
      max_tokens: 4000,
      system: DRAFT_SYSTEM,
      messages: [
        {
          role: "user",
          content: `Topic: ${pack.topic}\n\nEVIDENCE PACK (JSON):\n${JSON.stringify(pack)}`,
        },
      ],
    });
    const latencyMs = Date.now() - startedAt;
    const usage = {
      inputTokens: response.usage.input_tokens,
      outputTokens: response.usage.output_tokens,
    };

    if (response.stop_reason === "refusal") {
      await logDraft(pack, { status: "refusal", model: DRAFT_MODEL, latencyMs, ...usage }, meta);
      return { draft: null, reason: "refusal" };
    }
    const text = response.content
      .map((b) => (b.type === "text" ? b.text : ""))
      .join("")
      .trim();
    const result: DraftResult = text
      ? { draft: text, reason: null }
      : { draft: null, reason: "error" };
    await logDraft(
      pack,
      { status: text ? "ok" : "error", model: DRAFT_MODEL, draft: result.draft, latencyMs, ...usage },
      meta,
    );
    return result;
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    console.error("draftReview failed:", e);
    await logDraft(
      pack,
      { status: "error", model: DRAFT_MODEL, latencyMs: Date.now() - startedAt, error: message },
      meta,
    );
    return { draft: null, reason: "error" };
  }
}
