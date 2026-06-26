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
