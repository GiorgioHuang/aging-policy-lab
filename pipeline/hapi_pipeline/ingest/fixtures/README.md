# Vendored connector fixtures

## ⚠️ These are representative sample payloads, not authoritative pulls

This environment's network policy blocks the live source domains
(`statcan.gc.ca`, `data.novascotia.ca`, `cihi.ca`), so these fixtures are
**representative sample payloads in the exact wire format each real source
returns**. They exist so the Data Hub runs end-to-end offline and the
lineage/idempotency behaviour is fully verifiable.

**Do not treat the numbers here as official statistics.** They are realistic but
illustrative. Provenance is recorded explicitly: every observation loaded from a
fixture gets `dataset_version.source_version = 'fixture:<filename>'`, so fixture
data is never confused with a live retrieval in the database, the `hapi
observations` output, or the web `/data` page.

## Refreshing with real data

In an environment with outbound access to the source domains:

```bash
hapi ingest --live --source statcan_wds   # getFullTableDownloadCSV(17100005), filtered
hapi ingest --live --source ns_open_data  # Socrata resource fac5-58sq
```

`cihi_irrs` has no `--live` path: CIHI publishes data tables as **manual portal
downloads** (record-level data is controlled access), so refreshing means
downloading the latest table from
<https://www.cihi.ca/en/access-data-and-reports/data-tables> and replacing
`cihi_home_care_clients_65plus.csv`.

## Source identifiers (verified 2026-06 via web search)

- **StatCan:** Table **17-10-0005** "Population estimates on July 1, by age and
  gender" → productId **`17100005`**; the connector filters to age
  `65 years and over`, total gender, GEO ∈ {Canada, Nova Scotia}.
- **NS:** dataset "Accessing Primary Care in Nova Scotia", Socrata resource
  **`fac5-58sq`** (Need a Family Practice Registry — % of population needing a
  provider; `lower_is_better`).

Still **to confirm on the first `--live` run** (direct fetch was blocked here, so
these are handled defensively in code): the StatCan gender member label across
vintages (`Both sexes` vs `Total - gender` — both accepted) and the exact NS
Socrata column names (discovered heuristically by `parse()`).

## Files

| File | Source format | Connector | Indicator |
|------|---------------|-----------|-----------|
| `statcan_population_65plus.csv` | StatCan full-table CSV (filtered) | `statcan_wds` | `demography.population_65plus` |
| `ns_primary_care_registry.json` | Socrata SODA JSON | `ns_open_data` | `care_access.primary_care_unmet_need_pct` |
| `cihi_home_care_clients_65plus.csv` | CIHI data-table CSV (incl. an `x` suppression) | `cihi_irrs` | `care_access.home_care_clients_65plus` |
