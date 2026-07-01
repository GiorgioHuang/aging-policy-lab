-- ─────────────────────────────────────────────────────────────────────────────
-- 0006_contact_message_ip.sql — store the raw sender IP on the contact inbox
--
-- The inbox now records the sender's raw IP (shown alongside the User-Agent on
-- the protected /admin/messages page and in notifications) for triage. The
-- earlier salted-hash column (ip_hash, from 0005) is superseded; it is left in
-- place, unused, rather than dropped.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE contact_message ADD COLUMN IF NOT EXISTS ip text;
