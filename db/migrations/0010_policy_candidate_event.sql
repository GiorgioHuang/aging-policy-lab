-- ─────────────────────────────────────────────────────────────────────────────
-- 0010_policy_candidate_event.sql — Policy Watch: follow items after discovery
--
-- A bill is found once, but then moves: second reading, committee, royal
-- assent. For sources whose feeds report that stage (LEGISinfo, the NS
-- Legislature), each change seen on a followed candidate (awaiting review or
-- accepted) is recorded here, and the candidate's summary / published_at are
-- updated to the latest stage. Append-only: the history is the record of how
-- the policy progressed.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS policy_candidate_event (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_id  bigint      NOT NULL REFERENCES policy_candidate (id) ON DELETE CASCADE,
    observed_at   timestamptz NOT NULL DEFAULT now(),
    published_at  timestamptz,           -- the source's date for this stage
    summary       text        NOT NULL,  -- the stage as the source states it
    previous      text                   -- the summary it replaced
);

CREATE INDEX IF NOT EXISTS idx_candidate_event_candidate ON policy_candidate_event (candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_event_observed  ON policy_candidate_event (observed_at);

ALTER TABLE policy_candidate ADD COLUMN IF NOT EXISTS last_changed_at timestamptz;
