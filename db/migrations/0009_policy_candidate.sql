-- ─────────────────────────────────────────────────────────────────────────────
-- 0009_policy_candidate.sql — Policy Watch: the review queue for newly
-- discovered aging-policy items (docs/04 §9).
--
-- Watchers poll official feeds (federal news releases, Canada Gazette I/II,
-- Nova Scotia news releases), keep items that match aging-policy terms, and
-- optionally triage them with Claude. Every surviving item lands here as a
-- *candidate*; nothing reaches the Policy Library without a human accepting it.
--
-- One row per source item, deduplicated on a hash of the normalized URL, so
-- re-polling a feed is idempotent.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS policy_candidate (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source            text        NOT NULL,          -- watcher slug, e.g. 'gc_news'
    url               text        NOT NULL,
    url_hash          text        NOT NULL UNIQUE,   -- sha256 of the normalized URL
    title             text        NOT NULL,
    summary           text,                          -- feed description / teaser
    published_at      timestamptz,
    jurisdiction_code text,                          -- 'CA-FED' | 'CA-NS'
    department        text,
    matched_terms     text[]      NOT NULL DEFAULT '{}',
    keyword_score     int         NOT NULL DEFAULT 0,
    -- Claude triage (NULL when it did not run, e.g. no ANTHROPIC_API_KEY)
    ai_relevant       boolean,
    ai_category       text,                          -- new_policy | amendment | funding | ...
    ai_confidence     real,
    ai_rationale      text,
    ai_fields         jsonb,                         -- extracted seed fields
    ai_model          text,
    -- review lifecycle
    status            text        NOT NULL DEFAULT 'new'
                      CHECK (status IN ('new', 'accepted', 'rejected', 'auto_rejected')),
    seed_slug         text,                          -- set when accepted into seed_policies.json
    review_note       text,
    first_seen_at     timestamptz NOT NULL DEFAULT now(),
    reviewed_at       timestamptz,
    org_id            uuid                           -- tenancy seam (0004); NULL = public
);

CREATE INDEX IF NOT EXISTS idx_policy_candidate_status    ON policy_candidate (status);
CREATE INDEX IF NOT EXISTS idx_policy_candidate_seen      ON policy_candidate (first_seen_at);
CREATE INDEX IF NOT EXISTS idx_policy_candidate_published ON policy_candidate (published_at);
CREATE INDEX IF NOT EXISTS idx_policy_candidate_org       ON policy_candidate (org_id);
