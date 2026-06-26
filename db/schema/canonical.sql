-- ─────────────────────────────────────────────────────────────────────────────
-- canonical.sql — human-readable snapshot of the full schema.
-- AUTO-GENERATED from the live DB after applying db/migrations/*.sql:
--   pg_dump --schema-only --no-owner --no-privileges -T schema_migrations
-- Do not edit by hand; change a migration and regenerate.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TYPE public.analysis_tier AS ENUM (
    'association',
    'causal'
);
CREATE TYPE public.datasource_access_method AS ENUM (
    'api',
    'csv',
    'portal_download',
    'web_scrape'
);
CREATE TYPE public.hapi_score_domain AS ENUM (
    'health',
    'independence',
    'social_participation',
    'financial_security',
    'care_access',
    'digital_inclusion',
    'overall'
);
CREATE TYPE public.indicator_direction AS ENUM (
    'higher_is_better',
    'lower_is_better'
);
CREATE TYPE public.indicator_domain AS ENUM (
    'health',
    'independence',
    'social_participation',
    'financial_security',
    'care_access',
    'digital_inclusion',
    'demography'
);
CREATE TYPE public.jurisdiction_level AS ENUM (
    'country',
    'federal',
    'province',
    'region',
    'municipality'
);
CREATE TYPE public.observation_quality_flag AS ENUM (
    'ok',
    'estimated',
    'suppressed',
    'provisional'
);
CREATE TYPE public.policy_lifecycle AS ENUM (
    'announced',
    'funded',
    'in_effect',
    'amended',
    'retired'
);
CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;
CREATE TABLE public.analysis_finding (
    id bigint NOT NULL,
    slug text NOT NULL,
    title text NOT NULL,
    tier public.analysis_tier NOT NULL,
    method text NOT NULL,
    policy_id bigint,
    indicator_code text,
    jurisdiction_code text,
    window_spec jsonb,
    result jsonb,
    assumptions text,
    limitations text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
COMMENT ON TABLE public.analysis_finding IS 'Auditable analytic results; tier makes the Association/Causal distinction explicit (docs/07 §3).';
ALTER TABLE public.analysis_finding ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analysis_finding_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.dataset_version (
    id bigint NOT NULL,
    datasource_id bigint NOT NULL,
    retrieved_at timestamp with time zone DEFAULT now() NOT NULL,
    source_version text,
    checksum text,
    row_count integer
);
ALTER TABLE public.dataset_version ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.dataset_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.datasource (
    id bigint NOT NULL,
    name text NOT NULL,
    publisher text,
    url text,
    access_method public.datasource_access_method,
    licence text,
    update_frequency text,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE public.datasource ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.datasource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.hapi_score (
    id bigint NOT NULL,
    jurisdiction_id bigint NOT NULL,
    domain public.hapi_score_domain NOT NULL,
    period date NOT NULL,
    score numeric,
    method_version text NOT NULL,
    inputs jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE public.hapi_score ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.hapi_score_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.indicator (
    id bigint NOT NULL,
    code text NOT NULL,
    domain public.indicator_domain NOT NULL,
    name text NOT NULL,
    definition text,
    formula text,
    unit text,
    normalization jsonb,
    direction public.indicator_direction,
    coverage jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE public.indicator ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.indicator_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.indicator_source (
    indicator_id bigint NOT NULL,
    datasource_id bigint NOT NULL
);
CREATE TABLE public.jurisdiction (
    id bigint NOT NULL,
    parent_id bigint,
    name text NOT NULL,
    level public.jurisdiction_level NOT NULL,
    code text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
COMMENT ON TABLE public.jurisdiction IS 'Tree of governments. Adding a province/region is a row insert, not a schema change.';
ALTER TABLE public.jurisdiction ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.jurisdiction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.literature (
    id bigint NOT NULL,
    slug text NOT NULL,
    title text NOT NULL,
    authors text,
    year integer,
    venue text,
    url text,
    abstract text,
    topics text[],
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE public.literature ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.literature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.observation (
    id bigint NOT NULL,
    indicator_id bigint NOT NULL,
    jurisdiction_id bigint NOT NULL,
    dataset_version_id bigint NOT NULL,
    period daterange NOT NULL,
    value numeric,
    value_normalized numeric,
    quality_flag public.observation_quality_flag DEFAULT 'ok'::public.observation_quality_flag NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE public.observation ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.observation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE VIEW public.observation_lineage AS
 SELECT o.id AS observation_id,
    i.code AS indicator_code,
    i.domain AS indicator_domain,
    i.name AS indicator_name,
    i.unit,
    j.code AS jurisdiction_code,
    j.name AS jurisdiction_name,
    lower(o.period) AS period_start,
    upper(o.period) AS period_end,
    o.value,
    o.value_normalized,
    o.quality_flag,
    dv.id AS dataset_version_id,
    dv.retrieved_at,
    dv.source_version,
    dv.checksum,
    ds.id AS datasource_id,
    ds.name AS datasource_name,
    ds.publisher,
    ds.licence,
    ds.url AS source_url
   FROM ((((public.observation o
     JOIN public.indicator i ON ((i.id = o.indicator_id)))
     JOIN public.jurisdiction j ON ((j.id = o.jurisdiction_id)))
     JOIN public.dataset_version dv ON ((dv.id = o.dataset_version_id)))
     JOIN public.datasource ds ON ((ds.id = dv.datasource_id)));
COMMENT ON VIEW public.observation_lineage IS 'Forward traceability: every observation value joined to its dataset version, source, indicator, and jurisdiction (docs/05 §4).';
CREATE TABLE public.policy (
    id bigint NOT NULL,
    jurisdiction_id bigint NOT NULL,
    org_id uuid,
    title text NOT NULL,
    department text,
    released_at date,
    full_text text,
    source_url text,
    ai_summary text,
    budget_amount numeric,
    budget_currency text DEFAULT 'CAD'::text,
    target_population jsonb,
    kpis jsonb,
    lifecycle_status public.policy_lifecycle,
    theme text[],
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE public.policy ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.policy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
CREATE TABLE public.policy_indicator (
    policy_id bigint NOT NULL,
    indicator_id bigint NOT NULL
);
COMMENT ON TABLE public.policy_indicator IS 'Which outcome indicators a policy is intended to move. Drives policy analytics (docs/07).';
CREATE TABLE public.policy_version (
    id bigint NOT NULL,
    policy_id bigint NOT NULL,
    version_no integer NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    change_summary text,
    snapshot jsonb
);
ALTER TABLE public.policy_version ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.policy_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
ALTER TABLE ONLY public.analysis_finding
    ADD CONSTRAINT analysis_finding_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.analysis_finding
    ADD CONSTRAINT analysis_finding_slug_key UNIQUE (slug);
ALTER TABLE ONLY public.dataset_version
    ADD CONSTRAINT dataset_version_datasource_id_checksum_key UNIQUE (datasource_id, checksum);
ALTER TABLE ONLY public.dataset_version
    ADD CONSTRAINT dataset_version_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.datasource
    ADD CONSTRAINT datasource_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.hapi_score
    ADD CONSTRAINT hapi_score_jurisdiction_id_domain_period_method_version_key UNIQUE (jurisdiction_id, domain, period, method_version);
ALTER TABLE ONLY public.hapi_score
    ADD CONSTRAINT hapi_score_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.indicator
    ADD CONSTRAINT indicator_code_key UNIQUE (code);
ALTER TABLE ONLY public.indicator
    ADD CONSTRAINT indicator_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.indicator_source
    ADD CONSTRAINT indicator_source_pkey PRIMARY KEY (indicator_id, datasource_id);
ALTER TABLE ONLY public.jurisdiction
    ADD CONSTRAINT jurisdiction_code_key UNIQUE (code);
ALTER TABLE ONLY public.jurisdiction
    ADD CONSTRAINT jurisdiction_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.literature
    ADD CONSTRAINT literature_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.literature
    ADD CONSTRAINT literature_slug_key UNIQUE (slug);
ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.policy_indicator
    ADD CONSTRAINT policy_indicator_pkey PRIMARY KEY (policy_id, indicator_id);
ALTER TABLE ONLY public.policy
    ADD CONSTRAINT policy_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.policy_version
    ADD CONSTRAINT policy_version_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.policy_version
    ADD CONSTRAINT policy_version_policy_id_version_no_key UNIQUE (policy_id, version_no);
CREATE INDEX idx_dataset_version_source ON public.dataset_version USING btree (datasource_id);
CREATE INDEX idx_finding_indicator ON public.analysis_finding USING btree (indicator_code);
CREATE INDEX idx_finding_policy ON public.analysis_finding USING btree (policy_id);
CREATE INDEX idx_hapi_score_jurisdiction ON public.hapi_score USING btree (jurisdiction_id);
CREATE INDEX idx_indicator_domain ON public.indicator USING btree (domain);
CREATE INDEX idx_jurisdiction_parent ON public.jurisdiction USING btree (parent_id);
CREATE INDEX idx_literature_topics ON public.literature USING gin (topics);
CREATE INDEX idx_observation_dsv ON public.observation USING btree (dataset_version_id);
CREATE INDEX idx_observation_indicator ON public.observation USING btree (indicator_id);
CREATE INDEX idx_observation_jurisdiction ON public.observation USING btree (jurisdiction_id);
CREATE INDEX idx_observation_period ON public.observation USING gist (period);
CREATE INDEX idx_policy_jurisdiction ON public.policy USING btree (jurisdiction_id);
CREATE INDEX idx_policy_released_at ON public.policy USING btree (released_at);
CREATE INDEX idx_policy_theme ON public.policy USING gin (theme);
CREATE TRIGGER trg_datasource_updated BEFORE UPDATE ON public.datasource FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_indicator_updated BEFORE UPDATE ON public.indicator FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_jurisdiction_updated BEFORE UPDATE ON public.jurisdiction FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_policy_updated BEFORE UPDATE ON public.policy FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
ALTER TABLE ONLY public.analysis_finding
    ADD CONSTRAINT analysis_finding_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policy(id);
ALTER TABLE ONLY public.dataset_version
    ADD CONSTRAINT dataset_version_datasource_id_fkey FOREIGN KEY (datasource_id) REFERENCES public.datasource(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.hapi_score
    ADD CONSTRAINT hapi_score_jurisdiction_id_fkey FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdiction(id);
ALTER TABLE ONLY public.indicator_source
    ADD CONSTRAINT indicator_source_datasource_id_fkey FOREIGN KEY (datasource_id) REFERENCES public.datasource(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.indicator_source
    ADD CONSTRAINT indicator_source_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES public.indicator(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.jurisdiction
    ADD CONSTRAINT jurisdiction_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.jurisdiction(id);
ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES public.dataset_version(id);
ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES public.indicator(id);
ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_jurisdiction_id_fkey FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdiction(id);
ALTER TABLE ONLY public.policy_indicator
    ADD CONSTRAINT policy_indicator_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES public.indicator(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.policy_indicator
    ADD CONSTRAINT policy_indicator_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policy(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.policy
    ADD CONSTRAINT policy_jurisdiction_id_fkey FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdiction(id);
ALTER TABLE ONLY public.policy_version
    ADD CONSTRAINT policy_version_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policy(id) ON DELETE CASCADE;
