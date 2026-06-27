# Vendored connector fixtures

## What these are

Vendored payloads in the exact wire format each source returns, so the Data Hub
runs end-to-end offline and the lineage/idempotency behaviour is verifiable.

- **`statcan_population_65plus.csv` — real data.** Authentic Table 17-10-0005
  values captured from a live `--live` run on 2026-06 (Canada + Nova Scotia, 65+,
  2019–2025).
- **`ns_accessing_primary_care.json` — real values.** The actual provincial
  monthly Community-Pharmacy-PCC visit totals from the live SODA pull (2026-06).
  The live connector reads the full per-zone rows; here the per-zone rows are
  collapsed to one provincial-total row per month, which `parse()` sums to the
  same totals.
- **`cihi_home_care_clients_65plus.csv` — representative sample, NOT official.**
  CIHI has no open API (manual portal download / controlled access), so these
  numbers are illustrative pending a manual refresh. Treat as sample data.
- **`statcan_low_income_65plus.csv` — real data.** Official Table 11-10-0135
  seniors' (65+) LIM-AT low-income rates for CA + NS, captured from a live
  `--live` run on 2026-06 (slim filtered format). NS runs notably higher than the
  national rate (20–25% vs ~14–17%).
- **`statcan_internet_use_65plus.csv` — real data.** Official Table 22-10-0135
  seniors' (65+) internet-use rates for CA + NS in the CIUS survey years
  2018/2020/2022, captured from the same live run.
- **`statcan_life_expectancy_65.csv` — representative sample, NOT official.**
  Plausible life-expectancy-at-65 values (both sexes, three-year average) for
  CA + NS in the slim format `statcan_life_expectancy._filter_csv()` emits. The
  product id (13-10-0389) and access path are confirmed; these bootstrap values
  are illustrative until the first `--live` run replaces them with official data.
- **`statcan_cchs_65plus.csv` — representative sample, NOT official.**
  Plausible CCHS community-belonging-strong values for 65+ (→ Social
  Participation), CA + NS, in the slim format `statcan_cchs._filter_csv()` emits.
  Product id (13-10-0096) + schema confirmed via `hapi inspect`; bootstrap values
  are illustrative until the first `--live` run.
- **`statcan_functional_health_65plus.csv` — representative sample, NOT official.**
  Plausible functional-health (very good to perfect) values for ages 65–74 (→
  Independence; the table has no 65+ aggregate), CA + NS, in the slim format
  `statcan_functional_health._filter_csv()` emits. Product id (13-10-0966) +
  schema confirmed via `hapi inspect`; bootstrap values illustrative until the
  first `--live` run.

Provenance is always explicit: anything loaded from a fixture gets
`dataset_version.source_version = 'fixture:<filename>'`, so even real-but-vendored
values are distinguishable from a live retrieval in the DB, `hapi observations`,
and the web `/data` page (where a live run instead shows `WDS:` / `SODA:`).

## Refreshing with real data

In an environment with outbound access to the source domains:

```bash
hapi ingest --live --source statcan_wds            # getFullTableDownloadCSV(17100005), filtered
hapi ingest --live --source ns_open_data           # Socrata resource fac5-58sq
hapi ingest --live --source statcan_low_income       # getFullTableDownloadCSV(11100135), filtered
hapi ingest --live --source statcan_internet_use     # getFullTableDownloadCSV(22100135), filtered
hapi ingest --live --source statcan_life_expectancy  # getFullTableDownloadCSV(13100389), filtered
hapi ingest --live --source statcan_cchs             # getFullTableDownloadCSV(13100096), filtered
hapi ingest --live --source statcan_functional_health # getFullTableDownloadCSV(13100966), filtered
```

The two StatCan additions share the WDS full-table mechanism but their dimension
member labels (low-income line / statistic / internet-use characteristic) vary by
vintage, so confirm them on a networked runner before trusting a live pull:

```bash
hapi inspect statcan_low_income       # dumps headers + distinct dimension members
hapi inspect statcan_internet_use
hapi inspect statcan_life_expectancy
hapi inspect statcan_cchs
hapi inspect statcan_functional_health
```

The `_filter_csv` matchers are intentionally tolerant (case-insensitive
substring); tighten them in the connector if inspection shows different wording.

`cihi_irrs` has no `--live` path: CIHI publishes data tables as **manual portal
downloads** (record-level data is controlled access), so refreshing means
downloading the latest table from
<https://www.cihi.ca/en/access-data-and-reports/data-tables> and replacing
`cihi_home_care_clients_65plus.csv`.

## Source identifiers (confirmed 2026-06 via `hapi inspect` against the live sources)

- **StatCan:** Table **17-10-0005** → productId **`17100005`**; real columns
  `REF_DATE, GEO, Gender, Age group, …, VALUE, STATUS`. The connector filters to age
  **`65 years and older`** (the exact member label), gender `Total - gender`,
  GEO ∈ {Canada, Nova Scotia}.
- **NS:** dataset "Accessing Primary Care in Nova Scotia", Socrata resource
  **`fac5-58sq`** — real columns `zone, type, date, measure_name, actual` (by health
  zone; no provincial total, no percent). The connector sums **Community Pharmacy
  PCC visits** across zones per month → a provincial monthly count (`higher_is_better`).

- **StatCan (Financial Security):** Table **11-10-0135** → productId **`11100135`**
  ("Low income statistics by age, gender and economic family type"); filtered to
  65+, total gender, LIM-AT, percentage of persons in low income, all persons.
- **StatCan (Digital Inclusion):** Table **22-10-0135** → productId **`22100135`**
  ("Internet use by province and age group", from the Canadian Internet Use
  Survey, biennial); filtered to 65+ and the "used the Internet" characteristic.
- **StatCan (Health):** Table **13-10-0389** → productId **`13100389`**
  ("Life expectancy, at birth and at age 65, by sex, three-year average");
  filtered to "at age 65", both sexes, the life-expectancy estimate.
- **StatCan (Social Participation):** Table **13-10-0096** → productId
  **`13100096`** ("Health characteristics, annual estimates", CCHS; national GEO
  is "Canada (excluding territories)"); filtered to 65+, both sexes, percent,
  sense of community belonging (strong).
- **StatCan (Independence):** Table **13-10-0966** → productId **`13100966`**
  ("Functional health", CCHS 2015/2019/2024…; dims Age group / Sex / 'Domains' /
  'Characteristics'); no 65+ aggregate, so filtered to **age 65–74**, both sexes,
  percentage, domain "Very good to perfect functional health" (HUI Mark 3).

All four shapes (population, NS primary care, low income, internet use) were
verified end-to-end via `hapi inspect` + a live `--live` run on a networked
GitHub runner (the sandbox blocks the source domains); the fixtures hold the real
captured values, so offline runs reproduce the production numbers.

## Files

| File | Source format | Connector | Indicator |
|------|---------------|-----------|-----------|
| `statcan_population_65plus.csv` | StatCan full-table CSV (filtered) | `statcan_wds` | `demography.population_65plus` |
| `ns_accessing_primary_care.json` | Socrata SODA JSON (zone/type/date/measure/actual) | `ns_open_data` | `care_access.pharmacy_primary_care_visits` |
| `cihi_home_care_clients_65plus.csv` | CIHI data-table CSV (incl. an `x` suppression) | `cihi_irrs` | `care_access.home_care_clients_65plus` |
| `statcan_low_income_65plus.csv` | StatCan full-table CSV (slim, filtered) | `statcan_low_income` | `financial_security.low_income_rate_65plus` |
| `statcan_internet_use_65plus.csv` | StatCan full-table CSV (slim, filtered) | `statcan_internet_use` | `digital_inclusion.internet_use_65plus` |
| `statcan_life_expectancy_65.csv` | StatCan full-table CSV (slim, filtered) | `statcan_life_expectancy` | `health.life_expectancy_65` |
| `statcan_cchs_65plus.csv` | StatCan full-table CSV (slim, filtered) | `statcan_cchs` | `social_participation.community_belonging_65plus` |
| `statcan_functional_health_65plus.csv` | StatCan full-table CSV (slim, filtered) | `statcan_functional_health` | `independence.functional_health_65_74` |
