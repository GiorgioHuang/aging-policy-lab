import { pool } from "./db";

export type LineageRow = {
  indicatorCode: string;
  indicatorDomain: string;
  indicatorName: string;
  unit: string | null;
  jurisdictionCode: string;
  periodStart: string;
  periodEnd: string;
  value: string | null; // numeric arrives as string from pg
  qualityFlag: string;
  datasourceName: string;
  publisher: string | null;
  licence: string | null;
  sourceVersion: string | null;
  checksum: string | null;
};

export type IndicatorGroup = {
  code: string;
  domain: string;
  name: string;
  unit: string | null;
  direction: string | null;
  datasourceName: string;
  publisher: string | null;
  isFixture: boolean;
  rows: LineageRow[];
};

/** Read the observation lineage view (docs/05 §4) and group by indicator. */
export async function getIndicatorGroups(): Promise<IndicatorGroup[]> {
  const { rows } = await pool.query<{
    indicator_code: string;
    indicator_domain: string;
    indicator_name: string;
    unit: string | null;
    jurisdiction_code: string;
    period_start: string;
    period_end: string;
    value: string | null;
    quality_flag: string;
    datasource_name: string;
    publisher: string | null;
    licence: string | null;
    source_version: string | null;
    checksum: string | null;
  }>(
    `SELECT indicator_code, indicator_domain, indicator_name, unit,
            jurisdiction_code, period_start::text, period_end::text, value::text,
            quality_flag, datasource_name, publisher, licence, source_version, checksum
       FROM observation_lineage
   ORDER BY indicator_domain, indicator_code, jurisdiction_code, period_start`,
  );

  const groups = new Map<string, IndicatorGroup>();
  for (const r of rows) {
    const row: LineageRow = {
      indicatorCode: r.indicator_code,
      indicatorDomain: r.indicator_domain,
      indicatorName: r.indicator_name,
      unit: r.unit,
      jurisdictionCode: r.jurisdiction_code,
      periodStart: r.period_start,
      periodEnd: r.period_end,
      value: r.value,
      qualityFlag: r.quality_flag,
      datasourceName: r.datasource_name,
      publisher: r.publisher,
      licence: r.licence,
      sourceVersion: r.source_version,
      checksum: r.checksum,
    };
    let g = groups.get(r.indicator_code);
    if (!g) {
      g = {
        code: r.indicator_code,
        domain: r.indicator_domain,
        name: r.indicator_name,
        unit: r.unit,
        direction: null,
        datasourceName: r.datasource_name,
        publisher: r.publisher,
        isFixture: (r.source_version ?? "").startsWith("fixture:"),
        rows: [],
      };
      groups.set(r.indicator_code, g);
    }
    g.rows.push(row);
  }

  // Indicator direction drives chart colour; read it from the indicator table
  // (the lineage view doesn't expose it) — no schema change needed.
  const dirs = await pool.query<{ code: string; direction: string | null }>(
    `SELECT code, direction FROM indicator`,
  );
  const dirByCode = new Map(dirs.rows.map((d) => [d.code, d.direction]));
  for (const g of groups.values()) {
    g.direction = dirByCode.get(g.code) ?? null;
  }

  return [...groups.values()];
}
