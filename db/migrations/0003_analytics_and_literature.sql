-- ─────────────────────────────────────────────────────────────────────────────
-- 0003_analytics_and_literature.sql — Phase 4 (Policy Analytics + AI assistant)
--
--   * analysis_tier enum + analysis_finding: stores every analytic result with its
--     tier (Association vs Causal), method, inputs, assumptions, and limitations —
--     the platform-wide "association ≠ causation" guardrail made durable (docs/07).
--   * literature: a small knowledge base of papers for the AI Research Assistant's
--     retrieval (docs/08). Citations point at rows here, never fabricated sources.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TYPE analysis_tier AS ENUM ('association', 'causal');

CREATE TABLE analysis_finding (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug              text NOT NULL UNIQUE,            -- stable key for idempotent upsert
    title             text NOT NULL,
    tier              analysis_tier NOT NULL,
    method            text NOT NULL,                   -- 'trend' | 'correlation' | 'its' | …
    policy_id         bigint REFERENCES policy (id),   -- the policy event, if any
    indicator_code    text,
    jurisdiction_code text,
    window_spec       jsonb,                            -- {from, to, intervention, n_pre, n_post}
    result            jsonb,                            -- method-specific numbers + CIs
    assumptions       text,
    limitations       text,
    created_at        timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE analysis_finding IS
    'Auditable analytic results; tier makes the Association/Causal distinction explicit (docs/07 §3).';
CREATE INDEX idx_finding_indicator ON analysis_finding (indicator_code);
CREATE INDEX idx_finding_policy ON analysis_finding (policy_id);

CREATE TABLE literature (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug        text NOT NULL UNIQUE,
    title       text NOT NULL,
    authors     text,
    year        int,
    venue       text,
    url         text,
    abstract    text,
    topics      text[],
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_literature_topics ON literature USING gin (topics);
