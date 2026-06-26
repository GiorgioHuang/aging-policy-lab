-- ─────────────────────────────────────────────────────────────────────────────
-- 0001_jurisdictions.sql — seed the Phase 1 jurisdiction tree.
--   Canada (country)
--     ├── Federal      (federal)
--     └── Nova Scotia  (province)
-- Idempotent: re-running is a no-op (ON CONFLICT on the unique `code`).
-- Expanding to Ontario/BC/etc. later is just more rows here — no schema change.
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO jurisdiction (name, level, code)
VALUES ('Canada', 'country', 'CA')
ON CONFLICT (code) DO NOTHING;

INSERT INTO jurisdiction (parent_id, name, level, code)
SELECT id, 'Federal', 'federal', 'CA-FED'
FROM jurisdiction WHERE code = 'CA'
ON CONFLICT (code) DO NOTHING;

INSERT INTO jurisdiction (parent_id, name, level, code)
SELECT id, 'Nova Scotia', 'province', 'CA-NS'
FROM jurisdiction WHERE code = 'CA'
ON CONFLICT (code) DO NOTHING;
