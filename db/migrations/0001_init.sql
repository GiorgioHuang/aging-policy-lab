-- ─────────────────────────────────────────────────────────────────────────────
-- 0001_init.sql — core schema for the Healthy Aging Policy Observatory
-- Implements docs/03-data-model.md.
--
-- Design notes:
--   * Observations are immutable & provenance-bound (every value -> dataset_version
--     -> datasource). Corrections create new rows under a new dataset version.
--   * Policies are append-only via policy_version (amendment history is recoverable).
--   * Methodology is versioned (indicator.normalization + hapi_score.method_version).
--   * Tenancy-ready: core tables carry a nullable org_id so Postgres RLS / multi-tenant
--     SaaS (docs/02 §5) can be switched on later without a schema rewrite.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── Enums ───────────────────────────────────────────────────────────────────
CREATE TYPE jurisdiction_level AS ENUM
    ('country', 'federal', 'province', 'region', 'municipality');

CREATE TYPE policy_lifecycle AS ENUM
    ('announced', 'funded', 'in_effect', 'amended', 'retired');

CREATE TYPE indicator_domain AS ENUM
    ('health', 'independence', 'social_participation',
     'financial_security', 'care_access', 'digital_inclusion');

CREATE TYPE indicator_direction AS ENUM
    ('higher_is_better', 'lower_is_better');

CREATE TYPE datasource_access_method AS ENUM
    ('api', 'csv', 'portal_download', 'web_scrape');

CREATE TYPE observation_quality_flag AS ENUM
    ('ok', 'estimated', 'suppressed', 'provisional');

-- HAPI roll-up can be a single domain or the composite "overall".
CREATE TYPE hapi_score_domain AS ENUM
    ('health', 'independence', 'social_participation',
     'financial_security', 'care_access', 'digital_inclusion', 'overall');

-- ── updated_at helper ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── Jurisdiction (self-referential tree) ──────────────────────────────────────
CREATE TABLE jurisdiction (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_id   bigint REFERENCES jurisdiction (id),
    name        text   NOT NULL,
    level       jurisdiction_level NOT NULL,
    code        text   UNIQUE,                         -- e.g. 'CA', 'CA-NS' (ISO 3166-2)
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE jurisdiction IS
    'Tree of governments. Adding a province/region is a row insert, not a schema change.';
CREATE INDEX idx_jurisdiction_parent ON jurisdiction (parent_id);
CREATE TRIGGER trg_jurisdiction_updated
    BEFORE UPDATE ON jurisdiction FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Policy ────────────────────────────────────────────────────────────────────
CREATE TABLE policy (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jurisdiction_id   bigint NOT NULL REFERENCES jurisdiction (id),
    org_id            uuid,                             -- tenancy-ready (nullable in Stage 1)
    title             text   NOT NULL,
    department        text,
    released_at       date,                             -- anchors the timeline
    full_text         text,
    source_url        text,
    ai_summary        text,
    budget_amount     numeric,
    budget_currency   text DEFAULT 'CAD',
    target_population jsonb,                            -- e.g. {"age":"65+","group":"dementia"}
    kpis              jsonb,
    lifecycle_status  policy_lifecycle,
    theme             text[],                           -- e.g. {"home care","LTC","dementia"}
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_policy_jurisdiction ON policy (jurisdiction_id);
CREATE INDEX idx_policy_released_at  ON policy (released_at);
CREATE INDEX idx_policy_theme        ON policy USING gin (theme);
CREATE TRIGGER trg_policy_updated
    BEFORE UPDATE ON policy FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── PolicyVersion (amendment history; keeps policy append-only) ────────────────
CREATE TABLE policy_version (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id       bigint NOT NULL REFERENCES policy (id) ON DELETE CASCADE,
    version_no      int    NOT NULL,
    changed_at      timestamptz NOT NULL DEFAULT now(),
    change_summary  text,
    snapshot        jsonb,                              -- full field snapshot at this version
    UNIQUE (policy_id, version_no)
);

-- ── Indicator (HAPI indicator DEFINITION, not values) ──────────────────────────
CREATE TABLE indicator (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code          text   NOT NULL UNIQUE,              -- e.g. 'care_access.home_care_hours_per_capita'
    domain        indicator_domain NOT NULL,
    name          text   NOT NULL,
    definition    text,
    formula       text,
    unit          text,
    normalization jsonb,                               -- method + params (min-max, z-score, ...)
    direction     indicator_direction,
    coverage      jsonb,                               -- jurisdictions + time range covered
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_indicator_domain ON indicator (domain);
CREATE TRIGGER trg_indicator_updated
    BEFORE UPDATE ON indicator FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── DataSource (keystone of reproducibility) ───────────────────────────────────
CREATE TABLE datasource (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             text NOT NULL,
    publisher        text,                              -- StatCan, CIHI, NS Open Data, ...
    url              text,
    access_method    datasource_access_method,
    licence          text,                              -- e.g. 'Open Government Licence – Canada'
    update_frequency text,
    notes            text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_datasource_updated
    BEFORE UPDATE ON datasource FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── DatasetVersion (a specific retrieval; makes ingestion idempotent) ──────────
CREATE TABLE dataset_version (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    datasource_id  bigint NOT NULL REFERENCES datasource (id) ON DELETE CASCADE,
    retrieved_at   timestamptz NOT NULL DEFAULT now(),
    source_version text,
    checksum       text,                                -- hash of retrieved payload
    row_count      int,
    UNIQUE (datasource_id, checksum)                     -- re-fetch of identical payload is a no-op
);
CREATE INDEX idx_dataset_version_source ON dataset_version (datasource_id);

-- ── Observation (central fact table: indicator x jurisdiction x time) ──────────
-- Immutable: corrections arrive as new rows under a new dataset_version.
CREATE TABLE observation (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    indicator_id       bigint NOT NULL REFERENCES indicator (id),
    jurisdiction_id    bigint NOT NULL REFERENCES jurisdiction (id),
    dataset_version_id bigint NOT NULL REFERENCES dataset_version (id),
    period             daterange NOT NULL,              -- the time the value refers to
    value              numeric,
    value_normalized   numeric,
    quality_flag       observation_quality_flag NOT NULL DEFAULT 'ok',
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_observation_indicator    ON observation (indicator_id);
CREATE INDEX idx_observation_jurisdiction ON observation (jurisdiction_id);
CREATE INDEX idx_observation_dsv          ON observation (dataset_version_id);
CREATE INDEX idx_observation_period       ON observation USING gist (period);

-- ── HapiScore (rolled-up score per jurisdiction/domain/time) ───────────────────
CREATE TABLE hapi_score (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jurisdiction_id bigint NOT NULL REFERENCES jurisdiction (id),
    domain          hapi_score_domain NOT NULL,         -- a domain or the composite 'overall'
    period          date   NOT NULL,
    score           numeric,                            -- 0–100 (see docs/06)
    method_version  text   NOT NULL,                    -- which HAPI methodology produced it
    inputs          jsonb,                              -- indicator codes + weights (auditability)
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (jurisdiction_id, domain, period, method_version)
);
CREATE INDEX idx_hapi_score_jurisdiction ON hapi_score (jurisdiction_id);

-- ── Join tables (the two many-to-many relationships in docs/03 §3) ─────────────
CREATE TABLE policy_indicator (
    policy_id    bigint NOT NULL REFERENCES policy (id)    ON DELETE CASCADE,
    indicator_id bigint NOT NULL REFERENCES indicator (id) ON DELETE CASCADE,
    PRIMARY KEY (policy_id, indicator_id)
);
COMMENT ON TABLE policy_indicator IS
    'Which outcome indicators a policy is intended to move. Drives policy analytics (docs/07).';

CREATE TABLE indicator_source (
    indicator_id  bigint NOT NULL REFERENCES indicator (id)  ON DELETE CASCADE,
    datasource_id bigint NOT NULL REFERENCES datasource (id) ON DELETE CASCADE,
    PRIMARY KEY (indicator_id, datasource_id)
);
