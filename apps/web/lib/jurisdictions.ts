import { pool } from "./db";

export type Jurisdiction = {
  id: string;
  parentId: string | null;
  name: string;
  level: string;
  code: string | null;
};

export type JurisdictionNode = Jurisdiction & { children: JurisdictionNode[] };

/**
 * Read the full jurisdiction tree from Postgres and assemble it into a nested
 * structure. This is the Phase 1 proof that the web app can read the data model
 * (docs/03) — the jurisdiction tree is the first seeded entity.
 *
 * Note: bigint columns come back from `pg` as strings, which is exactly what we
 * want for stable React keys and for not losing precision.
 */
export async function getJurisdictionTree(): Promise<JurisdictionNode[]> {
  const { rows } = await pool.query<{
    id: string;
    parent_id: string | null;
    name: string;
    level: string;
    code: string | null;
  }>(
    `SELECT id, parent_id, name, level, code
       FROM jurisdiction
   ORDER BY parent_id NULLS FIRST, name`,
  );

  const byId = new Map<string, JurisdictionNode>();
  for (const r of rows) {
    byId.set(r.id, {
      id: r.id,
      parentId: r.parent_id,
      name: r.name,
      level: r.level,
      code: r.code,
      children: [],
    });
  }

  const roots: JurisdictionNode[] = [];
  for (const node of byId.values()) {
    if (node.parentId && byId.has(node.parentId)) {
      byId.get(node.parentId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}
