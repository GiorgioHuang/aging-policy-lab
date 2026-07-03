-- ─────────────────────────────────────────────────────────────────────────────
-- 0008_assistant_log_error.sql — capture the API error message on failed drafts
--
-- Stores the error string for status='error' rows so /admin/assistant-log can
-- show *why* a generation failed (bad param, auth, model access, …) without
-- needing Cloud Run log access.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE assistant_log ADD COLUMN IF NOT EXISTS error text;
