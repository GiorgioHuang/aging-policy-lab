-- ─────────────────────────────────────────────────────────────────────────────
-- 0005_contact_messages.sql — /about contact inbox
--
-- Backs the contact form on the public About page. Inbound inquiries that are
-- not appropriate to post publicly on GitHub (partnerships, sensitive data
-- requests) land here as an append-only inbox, reviewed out-of-band.
--
-- Privacy: we store only what the sender chooses to give (name/email/org are all
-- optional; message is required). The client IP is never stored raw — only an
-- optional salted SHA-256 prefix (ip_hash), and only when CONTACT_IP_SALT is set,
-- for abuse triage. No third-party trackers are involved.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contact_message (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at   timestamptz NOT NULL DEFAULT now(),
    name         text,
    email        text,
    organization text,
    subject      text,
    message      text NOT NULL,
    source       text NOT NULL DEFAULT 'about-form',
    user_agent   text,
    ip_hash      text,            -- salted SHA-256 prefix for abuse triage only (no raw IP / PII)
    status       text NOT NULL DEFAULT 'new'
                 CHECK (status IN ('new', 'read', 'archived', 'spam')),
    org_id       uuid             -- tenancy-ready, NULL = shared (Stage 1), matches 0004
);

CREATE INDEX IF NOT EXISTS idx_contact_message_created ON contact_message (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_message_status  ON contact_message (status);

COMMENT ON TABLE contact_message IS
    'Inbound inquiries from the /about contact form. Append-only inbox, reviewed out-of-band.';
