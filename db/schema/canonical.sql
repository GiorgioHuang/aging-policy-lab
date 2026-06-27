--
-- PostgreSQL database dump
--

\restrict 2YWsLQLaIW0ZW7IooAVbRjN1tESIOsQwiL8B0e9FXtDPqilSGTq3ygK6a5o8ABZ

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: analysis_tier; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.analysis_tier AS ENUM (
    'association',
    'causal'
);


--
-- Name: datasource_access_method; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.datasource_access_method AS ENUM (
    'api',
    'csv',
    'portal_download',
    'web_scrape'
);


--
-- Name: hapi_score_domain; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.hapi_score_domain AS ENUM (
    'health',
    'independence',
    'social_participation',
    'financial_security',
    'care_access',
    'digital_inclusion',
    'overall'
);


--
-- Name: indicator_direction; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.indicator_direction AS ENUM (
    'higher_is_better',
    'lower_is_better'
);


--
-- Name: indicator_domain; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.indicator_domain AS ENUM (
    'health',
    'independence',
    'social_participation',
    'financial_security',
    'care_access',
    'digital_inclusion',
    'demography'
);


--
-- Name: jurisdiction_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.jurisdiction_level AS ENUM (
    'country',
    'federal',
    'province',
    'region',
    'municipality'
);


--
-- Name: observation_quality_flag; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.observation_quality_flag AS ENUM (
    'ok',
    'estimated',
    'suppressed',
    'provisional'
);


--
-- Name: policy_lifecycle; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.policy_lifecycle AS ENUM (
    'announced',
    'funded',
    'in_effect',
    'amended',
    'retired'
);


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis_finding; Type: TABLE; Schema: public; Owner: -
--

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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    org_id uuid
);


--
-- Name: TABLE analysis_finding; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.analysis_finding IS 'Auditable analytic results; tier makes the Association/Causal distinction explicit (docs/07 §3).';


--
-- Name: analysis_finding_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.analysis_finding ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analysis_finding_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: dataset_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_version (
    id bigint NOT NULL,
    datasource_id bigint NOT NULL,
    retrieved_at timestamp with time zone DEFAULT now() NOT NULL,
    source_version text,
    checksum text,
    row_count integer
);


--
-- Name: dataset_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.dataset_version ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.dataset_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: datasource; Type: TABLE; Schema: public; Owner: -
--

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


--
-- Name: datasource_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.datasource ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.datasource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: hapi_score; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hapi_score (
    id bigint NOT NULL,
    jurisdiction_id bigint NOT NULL,
    domain public.hapi_score_domain NOT NULL,
    period date NOT NULL,
    score numeric,
    method_version text NOT NULL,
    inputs jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    org_id uuid
);


--
-- Name: hapi_score_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.hapi_score ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.hapi_score_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: indicator; Type: TABLE; Schema: public; Owner: -
--

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


--
-- Name: indicator_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.indicator ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.indicator_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: indicator_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.indicator_source (
    indicator_id bigint NOT NULL,
    datasource_id bigint NOT NULL
);


--
-- Name: jurisdiction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jurisdiction (
    id bigint NOT NULL,
    parent_id bigint,
    name text NOT NULL,
    level public.jurisdiction_level NOT NULL,
    code text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE jurisdiction; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.jurisdiction IS 'Tree of governments. Adding a province/region is a row insert, not a schema change.';


--
-- Name: jurisdiction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.jurisdiction ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.jurisdiction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: literature; Type: TABLE; Schema: public; Owner: -
--

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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    org_id uuid
);


--
-- Name: literature_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.literature ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.literature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: observation; Type: TABLE; Schema: public; Owner: -
--

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


--
-- Name: observation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.observation ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.observation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: observation_lineage; Type: VIEW; Schema: public; Owner: -
--

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


--
-- Name: VIEW observation_lineage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.observation_lineage IS 'Forward traceability: every observation value joined to its dataset version, source, indicator, and jurisdiction (docs/05 §4).';


--
-- Name: policy; Type: TABLE; Schema: public; Owner: -
--

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


--
-- Name: policy_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.policy ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.policy_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: policy_indicator; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.policy_indicator (
    policy_id bigint NOT NULL,
    indicator_id bigint NOT NULL
);


--
-- Name: TABLE policy_indicator; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.policy_indicator IS 'Which outcome indicators a policy is intended to move. Drives policy analytics (docs/07).';


--
-- Name: policy_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.policy_version (
    id bigint NOT NULL,
    policy_id bigint NOT NULL,
    version_no integer NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    change_summary text,
    snapshot jsonb
);


--
-- Name: policy_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.policy_version ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.policy_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    filename text NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: analysis_finding analysis_finding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_finding
    ADD CONSTRAINT analysis_finding_pkey PRIMARY KEY (id);


--
-- Name: analysis_finding analysis_finding_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_finding
    ADD CONSTRAINT analysis_finding_slug_key UNIQUE (slug);


--
-- Name: dataset_version dataset_version_datasource_id_checksum_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_version
    ADD CONSTRAINT dataset_version_datasource_id_checksum_key UNIQUE (datasource_id, checksum);


--
-- Name: dataset_version dataset_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_version
    ADD CONSTRAINT dataset_version_pkey PRIMARY KEY (id);


--
-- Name: datasource datasource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasource
    ADD CONSTRAINT datasource_pkey PRIMARY KEY (id);


--
-- Name: hapi_score hapi_score_jurisdiction_id_domain_period_method_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hapi_score
    ADD CONSTRAINT hapi_score_jurisdiction_id_domain_period_method_version_key UNIQUE (jurisdiction_id, domain, period, method_version);


--
-- Name: hapi_score hapi_score_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hapi_score
    ADD CONSTRAINT hapi_score_pkey PRIMARY KEY (id);


--
-- Name: indicator indicator_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indicator
    ADD CONSTRAINT indicator_code_key UNIQUE (code);


--
-- Name: indicator indicator_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indicator
    ADD CONSTRAINT indicator_pkey PRIMARY KEY (id);


--
-- Name: indicator_source indicator_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indicator_source
    ADD CONSTRAINT indicator_source_pkey PRIMARY KEY (indicator_id, datasource_id);


--
-- Name: jurisdiction jurisdiction_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jurisdiction
    ADD CONSTRAINT jurisdiction_code_key UNIQUE (code);


--
-- Name: jurisdiction jurisdiction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jurisdiction
    ADD CONSTRAINT jurisdiction_pkey PRIMARY KEY (id);


--
-- Name: literature literature_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.literature
    ADD CONSTRAINT literature_pkey PRIMARY KEY (id);


--
-- Name: literature literature_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.literature
    ADD CONSTRAINT literature_slug_key UNIQUE (slug);


--
-- Name: observation observation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_pkey PRIMARY KEY (id);


--
-- Name: policy_indicator policy_indicator_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy_indicator
    ADD CONSTRAINT policy_indicator_pkey PRIMARY KEY (policy_id, indicator_id);


--
-- Name: policy policy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy
    ADD CONSTRAINT policy_pkey PRIMARY KEY (id);


--
-- Name: policy_version policy_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy_version
    ADD CONSTRAINT policy_version_pkey PRIMARY KEY (id);


--
-- Name: policy_version policy_version_policy_id_version_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy_version
    ADD CONSTRAINT policy_version_policy_id_version_no_key UNIQUE (policy_id, version_no);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (filename);


--
-- Name: idx_dataset_version_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dataset_version_source ON public.dataset_version USING btree (datasource_id);


--
-- Name: idx_finding_indicator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_finding_indicator ON public.analysis_finding USING btree (indicator_code);


--
-- Name: idx_finding_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_finding_org ON public.analysis_finding USING btree (org_id);


--
-- Name: idx_finding_policy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_finding_policy ON public.analysis_finding USING btree (policy_id);


--
-- Name: idx_hapi_score_jurisdiction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hapi_score_jurisdiction ON public.hapi_score USING btree (jurisdiction_id);


--
-- Name: idx_hapi_score_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hapi_score_org ON public.hapi_score USING btree (org_id);


--
-- Name: idx_indicator_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_indicator_domain ON public.indicator USING btree (domain);


--
-- Name: idx_jurisdiction_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jurisdiction_parent ON public.jurisdiction USING btree (parent_id);


--
-- Name: idx_literature_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_literature_org ON public.literature USING btree (org_id);


--
-- Name: idx_literature_topics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_literature_topics ON public.literature USING gin (topics);


--
-- Name: idx_observation_dsv; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_observation_dsv ON public.observation USING btree (dataset_version_id);


--
-- Name: idx_observation_indicator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_observation_indicator ON public.observation USING btree (indicator_id);


--
-- Name: idx_observation_jurisdiction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_observation_jurisdiction ON public.observation USING btree (jurisdiction_id);


--
-- Name: idx_observation_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_observation_period ON public.observation USING gist (period);


--
-- Name: idx_policy_jurisdiction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_policy_jurisdiction ON public.policy USING btree (jurisdiction_id);


--
-- Name: idx_policy_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_policy_org ON public.policy USING btree (org_id);


--
-- Name: idx_policy_released_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_policy_released_at ON public.policy USING btree (released_at);


--
-- Name: idx_policy_theme; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_policy_theme ON public.policy USING gin (theme);


--
-- Name: datasource trg_datasource_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_datasource_updated BEFORE UPDATE ON public.datasource FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: indicator trg_indicator_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_indicator_updated BEFORE UPDATE ON public.indicator FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: jurisdiction trg_jurisdiction_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_jurisdiction_updated BEFORE UPDATE ON public.jurisdiction FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: policy trg_policy_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_policy_updated BEFORE UPDATE ON public.policy FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: analysis_finding analysis_finding_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_finding
    ADD CONSTRAINT analysis_finding_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policy(id);


--
-- Name: dataset_version dataset_version_datasource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_version
    ADD CONSTRAINT dataset_version_datasource_id_fkey FOREIGN KEY (datasource_id) REFERENCES public.datasource(id) ON DELETE CASCADE;


--
-- Name: hapi_score hapi_score_jurisdiction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hapi_score
    ADD CONSTRAINT hapi_score_jurisdiction_id_fkey FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdiction(id);


--
-- Name: indicator_source indicator_source_datasource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indicator_source
    ADD CONSTRAINT indicator_source_datasource_id_fkey FOREIGN KEY (datasource_id) REFERENCES public.datasource(id) ON DELETE CASCADE;


--
-- Name: indicator_source indicator_source_indicator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indicator_source
    ADD CONSTRAINT indicator_source_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES public.indicator(id) ON DELETE CASCADE;


--
-- Name: jurisdiction jurisdiction_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jurisdiction
    ADD CONSTRAINT jurisdiction_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.jurisdiction(id);


--
-- Name: observation observation_dataset_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES public.dataset_version(id);


--
-- Name: observation observation_indicator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES public.indicator(id);


--
-- Name: observation observation_jurisdiction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.observation
    ADD CONSTRAINT observation_jurisdiction_id_fkey FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdiction(id);


--
-- Name: policy_indicator policy_indicator_indicator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy_indicator
    ADD CONSTRAINT policy_indicator_indicator_id_fkey FOREIGN KEY (indicator_id) REFERENCES public.indicator(id) ON DELETE CASCADE;


--
-- Name: policy_indicator policy_indicator_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy_indicator
    ADD CONSTRAINT policy_indicator_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policy(id) ON DELETE CASCADE;


--
-- Name: policy policy_jurisdiction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy
    ADD CONSTRAINT policy_jurisdiction_id_fkey FOREIGN KEY (jurisdiction_id) REFERENCES public.jurisdiction(id);


--
-- Name: policy_version policy_version_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.policy_version
    ADD CONSTRAINT policy_version_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policy(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 2YWsLQLaIW0ZW7IooAVbRjN1tESIOsQwiL8B0e9FXtDPqilSGTq3ygK6a5o8ABZ

