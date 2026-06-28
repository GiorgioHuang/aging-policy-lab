import { pool } from "./db";
import { type AccessContext, orgScope } from "./access";

export type Overview = {
  counts: {
    policies: number;
    indicators: number;
    observations: number;
    hapiScores: number;
    findings: number;
    literature: number;
  };
  hapi: { code: string; overall: number | null; careAccess: number | null; period: string | null }[];
  hapiTrend: { code: string; points: { label: string; value: number }[] }[];
  domainProfile: { code: string; scores: Record<string, number> }[];
  policyTimeline: { id: string; year: number; jurisdiction: string; title: string }[];
  recentPolicies: { title: string; code: string; releasedAt: string | null; lifecycle: string | null }[];
  recentFindings: { title: string; tier: string; method: string }[];
};

export async function getOverview(ctx: AccessContext): Promise<Overview> {
  const counts = await pool.query(
    `SELECT
       (SELECT count(*) FROM policy)                         AS policies,
       (SELECT count(DISTINCT indicator_id) FROM observation) AS indicators,
       (SELECT count(*) FROM observation)                    AS observations,
       (SELECT count(*) FROM hapi_score)                     AS hapi_scores,
       (SELECT count(*) FROM analysis_finding)               AS findings,
       (SELECT count(*) FROM literature)                     AS literature`,
  );
  const c = counts.rows[0];

  // Latest overall + care_access HAPI per jurisdiction.
  const hapiRows = await pool.query<{ code: string; domain: string; score: string; period: string }>(
    `SELECT j.code, h.domain, h.score::text, h.period::text
       FROM hapi_score h JOIN jurisdiction j ON j.id = h.jurisdiction_id
      WHERE h.domain IN ('overall','care_access')
   ORDER BY j.code, h.domain, h.period DESC`,
  );
  const hapiMap = new Map<string, { code: string; overall: number | null; careAccess: number | null; period: string | null }>();
  for (const r of hapiRows.rows) {
    const e = hapiMap.get(r.code) ?? { code: r.code, overall: null, careAccess: null, period: null };
    if (r.domain === "overall" && e.overall === null) {
      e.overall = Number(r.score);
      e.period = r.period;
    }
    if (r.domain === "care_access" && e.careAccess === null) e.careAccess = Number(r.score);
    hapiMap.set(r.code, e);
  }

  // Composite HAPI trend per jurisdiction + latest score per domain (radar).
  const scoreRows = await pool.query<{ code: string; domain: string; score: string; period: string }>(
    `SELECT j.code, h.domain, h.score::text, h.period::text
       FROM hapi_score h JOIN jurisdiction j ON j.id = h.jurisdiction_id
      WHERE h.score IS NOT NULL
   ORDER BY j.code, h.domain, h.period`,
  );
  const trendMap = new Map<string, { label: string; value: number }[]>();
  const profileMap = new Map<string, Record<string, number>>(); // code -> domain -> latest score
  for (const r of scoreRows.rows) {
    if (r.domain === "overall") {
      const arr = trendMap.get(r.code) ?? [];
      arr.push({ label: r.period.slice(0, 4), value: Number(r.score) });
      trendMap.set(r.code, arr);
    } else {
      const e = profileMap.get(r.code) ?? {};
      e[r.domain] = Number(r.score); // rows ordered by period asc → last write wins = latest
      profileMap.set(r.code, e);
    }
  }

  const policyTl = await pool.query<{ id: string; code: string; released_at: string; title: string }>(
    `SELECT p.id::text, j.code, p.released_at::text, p.title
       FROM policy p JOIN jurisdiction j ON j.id = p.jurisdiction_id
      WHERE p.released_at IS NOT NULL`,
  );

  // Recent policies — routed through the org access seam (no-op in Stage 1).
  const pScope = orgScope(ctx, "p.org_id", 1);
  const pol = await pool.query(
    `SELECT p.title, j.code, p.released_at::text, p.lifecycle_status
       FROM policy p JOIN jurisdiction j ON j.id = p.jurisdiction_id
      WHERE true${pScope.clause}
   ORDER BY p.released_at DESC NULLS LAST LIMIT 5`,
    pScope.params,
  );

  const fScope = orgScope(ctx, "org_id", 1);
  const find = await pool.query(
    `SELECT title, tier, method FROM analysis_finding
      WHERE true${fScope.clause}
   ORDER BY (tier = 'causal') DESC, id LIMIT 5`,
    fScope.params,
  );

  return {
    counts: {
      policies: Number(c.policies),
      indicators: Number(c.indicators),
      observations: Number(c.observations),
      hapiScores: Number(c.hapi_scores),
      findings: Number(c.findings),
      literature: Number(c.literature),
    },
    hapi: [...hapiMap.values()],
    hapiTrend: [...trendMap.entries()].map(([code, points]) => ({ code, points })),
    domainProfile: [...profileMap.entries()].map(([code, scores]) => ({ code, scores })),
    policyTimeline: policyTl.rows
      .map((r) => ({ id: r.id, year: Number(r.released_at.slice(0, 4)), jurisdiction: r.code, title: r.title }))
      .filter((d) => Number.isFinite(d.year)),
    recentPolicies: pol.rows.map((r) => ({
      title: r.title, code: r.code, releasedAt: r.released_at, lifecycle: r.lifecycle_status,
    })),
    recentFindings: find.rows.map((r) => ({ title: r.title, tier: r.tier, method: r.method })),
  };
}
