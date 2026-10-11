import { pool } from "./db";
import { type AccessContext, orgScope } from "./access";
import { type ByPeriod, compositeTrend, mergeWeights, profileComposite } from "./hapiComposite";

export type Overview = {
  counts: {
    policies: number;
    indicators: number;
    observations: number;
    hapiScores: number;
    findings: number;
    literature: number;
  };
  /** overall = composite of each domain's latest score; years = its data-year span. */
  hapi: { code: string; overall: number | null; careAccess: number | null; years: string | null }[];
  hapiTrend: { code: string; points: { label: string; value: number }[] }[];
  domainProfile: { code: string; scores: Record<string, number> }[];
  domainEvolution: {
    years: string[];
    series: { code: string; byYear: Record<string, Record<string, number>> }[];
  };
  policyTimeline: { id: string; year: number; jurisdiction: string; title: string; url: string | null }[];
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

  // Domain weights the scoring engine used (stored on its 'overall' rows).
  const weightRows = await pool.query<{ w: Record<string, number> | null }>(
    `SELECT inputs->'domain_weights' AS w FROM hapi_score WHERE domain = 'overall'`,
  );
  const weights = mergeWeights(weightRows.rows.map((r) => r.w));

  // Composite HAPI trend per jurisdiction + latest score per domain (radar).
  const scoreRows = await pool.query<{ code: string; domain: string; score: string; period: string }>(
    `SELECT j.code, h.domain, h.score::text, h.period::text
       FROM hapi_score h JOIN jurisdiction j ON j.id = h.jurisdiction_id
      WHERE h.score IS NOT NULL
   ORDER BY j.code, h.domain, h.period`,
  );
  const byPeriodMap = new Map<string, ByPeriod>(); // code -> period -> domain -> score
  const profileMap = new Map<string, Record<string, number>>(); // code -> domain -> latest score
  const evoMap = new Map<string, Record<string, Record<string, number>>>(); // code -> year -> domain -> score
  const yearSet = new Set<string>();
  for (const r of scoreRows.rows) {
    if (r.domain !== "overall") {
      const bp = byPeriodMap.get(r.code) ?? {};
      (bp[r.period] ??= {})[r.domain] = Number(r.score);
      byPeriodMap.set(r.code, bp);
      const e = profileMap.get(r.code) ?? {};
      e[r.domain] = Number(r.score); // rows ordered by period asc → last write wins = latest
      profileMap.set(r.code, e);
      // bucket per year (latest within a year wins, since rows are period-ascending)
      const yr = r.period.slice(0, 4);
      yearSet.add(yr);
      const byYear = evoMap.get(r.code) ?? {};
      (byYear[yr] ??= {})[r.domain] = Number(r.score);
      evoMap.set(r.code, byYear);
    }
  }

  const policyTl = await pool.query<{ id: string; code: string; released_at: string; title: string; source_url: string | null }>(
    `SELECT p.id::text, j.code, p.released_at::text, p.title, p.source_url
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
    hapi: [...byPeriodMap.entries()].map(([code, bp]) => {
      const pc = profileComposite(bp, weights);
      return {
        code,
        overall: pc?.score ?? null,
        careAccess: profileMap.get(code)?.care_access ?? null,
        years: pc ? (pc.fromYear === pc.toYear ? pc.fromYear : `${pc.fromYear}–${pc.toYear}`) : null,
      };
    }),
    hapiTrend: [...byPeriodMap.entries()].map(([code, bp]) => ({ code, points: compositeTrend(bp, weights) })),
    domainProfile: [...profileMap.entries()].map(([code, scores]) => ({ code, scores })),
    domainEvolution: {
      years: [...yearSet].sort(),
      series: [...evoMap.entries()].map(([code, byYear]) => ({ code, byYear })),
    },
    policyTimeline: policyTl.rows
      .map((r) => ({
        id: r.id,
        year: Number(r.released_at.slice(0, 4)),
        jurisdiction: r.code,
        title: r.title,
        url: r.source_url,
      }))
      .filter((d) => Number.isFinite(d.year)),
    recentPolicies: pol.rows.map((r) => ({
      title: r.title, code: r.code, releasedAt: r.released_at, lifecycle: r.lifecycle_status,
    })),
    recentFindings: find.rows.map((r) => ({ title: r.title, tier: r.tier, method: r.method })),
  };
}
