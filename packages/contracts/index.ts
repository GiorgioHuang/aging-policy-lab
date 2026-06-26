// Shared TypeScript contracts derived from the language-neutral `enums.json`.
// Keep `enums.json` as the single source of truth; the Python pipeline reads the
// same file (see pipeline/hapi_pipeline/contracts.py).
import enums from "./enums.json" with { type: "json" };

export const JurisdictionLevel = enums.jurisdiction_level;
export const PolicyLifecycle = enums.policy_lifecycle;
export const IndicatorDomain = enums.indicator_domain;
export const IndicatorDirection = enums.indicator_direction;
export const DataSourceAccessMethod = enums.datasource_access_method;
export const ObservationQualityFlag = enums.observation_quality_flag;
export const HapiScoreDomain = enums.hapi_score_domain;

export type JurisdictionLevel = (typeof JurisdictionLevel)[number];
export type PolicyLifecycle = (typeof PolicyLifecycle)[number];
export type IndicatorDomain = (typeof IndicatorDomain)[number];
export type IndicatorDirection = (typeof IndicatorDirection)[number];
export type DataSourceAccessMethod = (typeof DataSourceAccessMethod)[number];
export type ObservationQualityFlag = (typeof ObservationQualityFlag)[number];
export type HapiScoreDomain = (typeof HapiScoreDomain)[number];
