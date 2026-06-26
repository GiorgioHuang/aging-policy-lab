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
hapi ingest --live --source statcan_wds   # re-fetches WDS and overwrites the fixture
hapi ingest --live --source ns_open_data  # re-fetches Socrata and overwrites the fixture
```

`cihi_irrs` has no `--live` path: CIHI publishes data tables as **manual portal
downloads** (record-level data is controlled access), so refreshing means
downloading the latest table from
<https://www.cihi.ca/en/access-data-and-reports/data-tables> and replacing
`cihi_home_care_clients_65plus.csv`.

Before any `--live` run, verify the placeholder identifiers in the connectors
(StatCan vector IDs for Table 17-10-0005; the NS Socrata resource id/columns).

## Files

| File | Source format | Connector | Indicator |
|------|---------------|-----------|-----------|
| `statcan_population_65plus.json` | WDS `getDataFromVectorsAndLatestNPeriods` JSON | `statcan_wds` | `demography.population_65plus` |
| `ns_primary_care_attachment.json` | Socrata SODA JSON | `ns_open_data` | `care_access.primary_care_attachment_pct` |
| `cihi_home_care_clients_65plus.csv` | CIHI data-table CSV (incl. an `x` suppression) | `cihi_irrs` | `care_access.home_care_clients_65plus` |
