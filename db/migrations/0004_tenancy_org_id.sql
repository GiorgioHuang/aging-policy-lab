-- ─────────────────────────────────────────────────────────────────────────────
-- 0004_tenancy_org_id.sql — Phase 5 SaaS-readiness (docs/02 §5)
--
-- Add a nullable org_id to the remaining tenant-scoped content tables so a future
-- multi-tenant SaaS (Stage 3) can switch on row-level isolation (Postgres RLS)
-- additively, without a schema rewrite. `policy` already carries org_id (0001).
--
-- NULL means "shared / single-tenant" — the platform runs single-tenant today
-- (Stage 1), so every row stays NULL and nothing changes behaviourally. The
-- app-level access seam (apps/web/lib/access.ts) is the matching read-path hook.
--
-- Reference data (jurisdiction, indicator, datasource, observation, dataset_version)
-- is intentionally global and not org-scoped.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE hapi_score       ADD COLUMN IF NOT EXISTS org_id uuid;
ALTER TABLE analysis_finding ADD COLUMN IF NOT EXISTS org_id uuid;
ALTER TABLE literature       ADD COLUMN IF NOT EXISTS org_id uuid;

CREATE INDEX IF NOT EXISTS idx_hapi_score_org   ON hapi_score (org_id);
CREATE INDEX IF NOT EXISTS idx_finding_org      ON analysis_finding (org_id);
CREATE INDEX IF NOT EXISTS idx_literature_org   ON literature (org_id);
CREATE INDEX IF NOT EXISTS idx_policy_org       ON policy (org_id);
