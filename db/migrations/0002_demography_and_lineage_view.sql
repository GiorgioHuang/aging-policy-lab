-- ─────────────────────────────────────────────────────────────────────────────
-- 0002_demography_and_lineage_view.sql
--
-- Phase 2 (Data Hub) prerequisites:
--   1. Add a non-HAPI 'demography' value to indicator_domain so population
--      denominators (StatCan) can be stored as first-class, lineage-bound
--      Observations — they are demographic reference data, NOT a HAPI outcome,
--      so they never roll up into a HapiScore (hapi_score_domain is unchanged).
--      This is the documented "add a migration, never edit an applied one"
--      convention in db/README.md.
--   2. Create observation_lineage: a read view that threads every value back to
--      Observation -> DatasetVersion -> DataSource and out to Indicator +
--      Jurisdiction. This is the forward-traceability promise of docs/05 §4,
--      consumed by `hapi observations` and the web /data page.
--
-- Note: ALTER TYPE ... ADD VALUE is permitted inside a transaction in PG 12+ as
-- long as the new value is not *used* in the same transaction. We only add it
-- here; the first row using it is inserted later by the ingest pipeline.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TYPE indicator_domain ADD VALUE IF NOT EXISTS 'demography';

CREATE OR REPLACE VIEW observation_lineage AS
SELECT
    o.id                AS observation_id,
    i.code              AS indicator_code,
    i.domain            AS indicator_domain,
    i.name              AS indicator_name,
    i.unit              AS unit,
    j.code              AS jurisdiction_code,
    j.name              AS jurisdiction_name,
    lower(o.period)     AS period_start,
    upper(o.period)     AS period_end,
    o.value             AS value,
    o.value_normalized  AS value_normalized,
    o.quality_flag      AS quality_flag,
    dv.id               AS dataset_version_id,
    dv.retrieved_at     AS retrieved_at,
    dv.source_version   AS source_version,
    dv.checksum         AS checksum,
    ds.id               AS datasource_id,
    ds.name             AS datasource_name,
    ds.publisher        AS publisher,
    ds.licence          AS licence,
    ds.url              AS source_url
FROM observation o
JOIN indicator       i  ON i.id  = o.indicator_id
JOIN jurisdiction    j  ON j.id  = o.jurisdiction_id
JOIN dataset_version dv ON dv.id = o.dataset_version_id
JOIN datasource      ds ON ds.id = dv.datasource_id;

COMMENT ON VIEW observation_lineage IS
    'Forward traceability: every observation value joined to its dataset version, '
    'source, indicator, and jurisdiction (docs/05 §4).';
