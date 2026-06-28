import { pool } from "./db";

export type HapiInputIndicator = {
  code: string;
  raw: number;
  denominator: number | null;
  value: number;
  normalized: number;
  weight: number;
};

export type HapiScoreRow = {
  jurisdictionCode: string;
  domain: string;
  period: string;
  score: string | null;
  methodVersion: string;
  inputs: {
    indicators?: HapiInputIndicator[];
    domain_scores?: Record<string, number>;
    domain_weights?: Record<string, number>;
  } | null;
};

export type DomainScores = {
  domain: string;
  byJurisdiction: { code: string; rows: HapiScoreRow[] }[];
};

export type PolicyEvent = { year: number; month: number; title: string };

/** Policy events that target an indicator in each domain, keyed domain → chart
 * jurisdiction (federal policies map to the national 'CA' series). */
export async function getPolicyEventsByDomain(): Promise<Record<string, Record<string, PolicyEvent[]>>> {
  const { rows } = await pool.query<{ domain: string; jur: string; title: string; released: string }>(
    `SELECT DISTINCT i.domain, j.code AS jur, p.title, p.released_at::text AS released
       FROM policy_indicator pi
       JOIN indicator i      ON i.id = pi.indicator_id
       JOIN policy p         ON p.id = pi.policy_id
       JOIN jurisdiction j   ON j.id = p.jurisdiction_id
      WHERE p.released_at IS NOT NULL`,
  );
  const out: Record<string, Record<string, PolicyEvent[]>> = {};
  for (const r of rows) {
    const chartJur = r.jur === "CA-FED" ? "CA" : r.jur; // national series for federal policy
    const y = Number(r.released.slice(0, 4));
    const m = Number(r.released.slice(5, 7)) || 1;
    if (!Number.isFinite(y)) continue;
    ((out[r.domain] ??= {})[chartJur] ??= []).push({ year: y, month: m, title: r.title });
  }
  return out;
}

/** HAPI scores grouped by domain, then jurisdiction (ordered by period). */
export async function getHapiScores(): Promise<DomainScores[]> {
  const { rows } = await pool.query<{
    jur: string;
    domain: string;
    period: string;
    score: string | null;
    method_version: string;
    inputs: HapiScoreRow["inputs"];
  }>(
    `SELECT j.code AS jur, h.domain, h.period::text, h.score::text,
            h.method_version, h.inputs
       FROM hapi_score h
       JOIN jurisdiction j ON j.id = h.jurisdiction_id
   ORDER BY h.domain, j.code, h.period`,
  );

  const domains = new Map<string, Map<string, HapiScoreRow[]>>();
  for (const r of rows) {
    const row: HapiScoreRow = {
      jurisdictionCode: r.jur,
      domain: r.domain,
      period: r.period,
      score: r.score,
      methodVersion: r.method_version,
      inputs: r.inputs,
    };
    let byJur = domains.get(r.domain);
    if (!byJur) {
      byJur = new Map();
      domains.set(r.domain, byJur);
    }
    const arr = byJur.get(r.jur) ?? [];
    arr.push(row);
    byJur.set(r.jur, arr);
  }

  // 'overall' first, then the domains alphabetically.
  const order = (d: string) => (d === "overall" ? "" : d);
  return [...domains.entries()]
    .sort((a, b) => order(a[0]).localeCompare(order(b[0])))
    .map(([domain, byJur]) => ({
      domain,
      byJurisdiction: [...byJur.entries()].map(([code, rows]) => ({ code, rows })),
    }));
}
