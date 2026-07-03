-- ─────────────────────────────────────────────────────────────────────────────
-- 0007_assistant_log.sql — audit log for the AI Research Assistant draft
--
-- One row per *generation* (cache hits are not re-logged): the input (topic +
-- evidence-pack size) and the output (the cited draft), plus model, token usage,
-- latency, and a status. Writes are best-effort in the app — a logging failure
-- never blocks the user's response.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS assistant_log (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    topic          text NOT NULL,                       -- input
    model          text,
    status         text NOT NULL
                   CHECK (status IN ('ok', 'empty_pack', 'refusal', 'error')),
    draft          text,                                -- output (null on failure)
    n_policies     integer,
    n_literature   integer,
    n_findings     integer,
    input_tokens   integer,
    output_tokens  integer,
    latency_ms     integer,
    ip             text,
    org_id         uuid                                 -- tenancy-ready, NULL = shared
);

CREATE INDEX IF NOT EXISTS idx_assistant_log_created ON assistant_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assistant_log_status  ON assistant_log (status);

COMMENT ON TABLE assistant_log IS
    'Audit log of /assistant draft generations: topic in, cited draft out, plus usage.';
