// Auth / tenancy access seam (docs/02 §5).
//
// The platform runs single-tenant today (Stage 1): no auth, no org scoping.
// This module is the ONE place that resolves "who is asking", so adding
// authentication (Stage 2) and multi-tenant row isolation (Stage 3) is an
// additive change here + the nullable org_id columns (db/migrations/0004),
// not a rewrite. Reads that touch org-scoped tables route their filter through
// `orgScope` so the convention is already in place.

export type AccessContext = {
  orgId: string | null;
  authenticated: boolean;
};

/**
 * Resolve the current access context. Stage 1 returns an anonymous, org-less
 * context (single-tenant). Stage 2/3: read the authenticated session / a
 * verified `org_id` header here and return it — every caller already honours it.
 */
export async function getAccessContext(): Promise<AccessContext> {
  return { orgId: null, authenticated: false };
}

/**
 * SQL fragment (+ params) that scopes a query to the current org on a table that
 * carries `org_id`. No-op (empty clause) in Stage 1 when orgId is null, so the
 * query is byte-identical today and tightened automatically once tenancy is on.
 * `column` is the qualified column (e.g. "p.org_id"); `nextParam` is the next
 * positional placeholder index ($N) to use.
 */
export function orgScope(
  ctx: AccessContext,
  column: string,
  nextParam: number,
): { clause: string; params: string[] } {
  if (!ctx.orgId) return { clause: "", params: [] };
  // Show the org's rows plus shared (NULL) rows.
  return { clause: ` AND (${column} = $${nextParam} OR ${column} IS NULL)`, params: [ctx.orgId] };
}
