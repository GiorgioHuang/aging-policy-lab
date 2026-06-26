import { pool } from "./db";

export type Policy = {
  id: string;
  jurisdictionCode: string;
  title: string;
  department: string | null;
  releasedAt: string | null;
  lifecycleStatus: string | null;
  theme: string[];
  budgetAmount: string | null;
  budgetCurrency: string | null;
  aiSummary: string | null;
  sourceUrl: string | null;
  indicators: string[];
};

export type JurisdictionPolicies = { code: string; policies: Policy[] };

/** Policy Library timeline: policies grouped by jurisdiction, newest first. */
export async function getPolicies(): Promise<JurisdictionPolicies[]> {
  const { rows } = await pool.query<{
    id: string;
    jur: string;
    title: string;
    department: string | null;
    released_at: string | null;
    lifecycle_status: string | null;
    theme: string[] | null;
    budget_amount: string | null;
    budget_currency: string | null;
    ai_summary: string | null;
    source_url: string | null;
    indicators: string[] | null;
  }>(
    `SELECT p.id, j.code AS jur, p.title, p.department, p.released_at::text,
            p.lifecycle_status, p.theme, p.budget_amount::text, p.budget_currency,
            p.ai_summary, p.source_url,
            COALESCE(array_agg(i.code) FILTER (WHERE i.code IS NOT NULL), '{}') AS indicators
       FROM policy p
       JOIN jurisdiction j ON j.id = p.jurisdiction_id
  LEFT JOIN policy_indicator pi ON pi.policy_id = p.id
  LEFT JOIN indicator i ON i.id = pi.indicator_id
   GROUP BY p.id, j.code, p.title, p.department, p.released_at, p.lifecycle_status,
            p.theme, p.budget_amount, p.budget_currency, p.ai_summary, p.source_url
   ORDER BY j.code, p.released_at DESC NULLS LAST`,
  );

  const groups = new Map<string, JurisdictionPolicies>();
  for (const r of rows) {
    const p: Policy = {
      id: r.id,
      jurisdictionCode: r.jur,
      title: r.title,
      department: r.department,
      releasedAt: r.released_at,
      lifecycleStatus: r.lifecycle_status,
      theme: r.theme ?? [],
      budgetAmount: r.budget_amount,
      budgetCurrency: r.budget_currency,
      aiSummary: r.ai_summary,
      sourceUrl: r.source_url,
      indicators: r.indicators ?? [],
    };
    let g = groups.get(r.jur);
    if (!g) {
      g = { code: r.jur, policies: [] };
      groups.set(r.jur, g);
    }
    g.policies.push(p);
  }
  return [...groups.values()];
}
