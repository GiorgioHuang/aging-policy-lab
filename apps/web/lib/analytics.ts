import { pool } from "./db";
import type { ChartPoint } from "@/components/TrendChart";

export type Finding = {
  id: string;
  title: string;
  tier: "association" | "causal";
  method: string;
  policyTitle: string | null;
  indicatorCode: string | null;
  jurisdictionCode: string | null;
  windowSpec: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  assumptions: string | null;
  limitations: string | null;
};

export async function getFindings(): Promise<Finding[]> {
  const { rows } = await pool.query<{
    id: string;
    title: string;
    tier: "association" | "causal";
    method: string;
    policy_title: string | null;
    indicator_code: string | null;
    jurisdiction_code: string | null;
    window_spec: Record<string, unknown> | null;
    result: Record<string, unknown> | null;
    assumptions: string | null;
    limitations: string | null;
  }>(
    `SELECT f.id, f.title, f.tier, f.method, p.title AS policy_title,
            f.indicator_code, f.jurisdiction_code, f.window_spec, f.result,
            f.assumptions, f.limitations
       FROM analysis_finding f
  LEFT JOIN policy p ON p.id = f.policy_id
   ORDER BY (f.tier = 'causal') DESC, f.method, f.indicator_code, f.jurisdiction_code`,
  );
  return rows.map((r) => ({
    id: r.id,
    title: r.title,
    tier: r.tier,
    method: r.method,
    policyTitle: r.policy_title,
    indicatorCode: r.indicator_code,
    jurisdictionCode: r.jurisdiction_code,
    windowSpec: r.window_spec,
    result: r.result,
    assumptions: r.assumptions,
    limitations: r.limitations,
  }));
}

/** Latest value per period for an indicator series, as chart points.
 * Prefers a live dataset version over a fixture for the same period — matching
 * the pipeline's `descriptive.load_series`, so the chart shows exactly the
 * series the ITS / trend was computed on. */
export async function getSeries(code: string, jur: string): Promise<ChartPoint[]> {
  const { rows } = await pool.query<{ ps: string; value: string }>(
    `SELECT ps, value FROM (
        SELECT lower(o.period)::text AS ps, o.value::text AS value,
               row_number() OVER (
                   PARTITION BY o.indicator_id, o.jurisdiction_id, o.period
                   ORDER BY (dv.source_version LIKE 'fixture:%') ASC,
                            o.dataset_version_id DESC
               ) AS rn
          FROM observation o
          JOIN indicator i ON i.id = o.indicator_id
          JOIN jurisdiction j ON j.id = o.jurisdiction_id
          JOIN dataset_version dv ON dv.id = o.dataset_version_id
         WHERE i.code = $1 AND j.code = $2 AND o.value IS NOT NULL
      ) ranked
      WHERE rn = 1
      ORDER BY ps`,
    [code, jur],
  );
  return rows.map((r) => {
    // annual series -> "YYYY"; monthly -> "YYYY-MM"
    const label = r.ps.endsWith("-01-01") ? r.ps.slice(0, 4) : r.ps.slice(0, 7);
    return { label, value: Number(r.value) };
  });
}
