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

## Source identifiers (confirmed 2026-06 via `hapi inspect` against the live sources)

- **StatCan:** Table **17-10-0005** → productId **`17100005`**; real columns
  `REF_DATE, GEO, Gender, Age group, …, VALUE, STATUS`. The connector filters to age
  **`65 years and older`** (the exact member label), gender `Total - gender`,
  GEO ∈ {Canada, Nova Scotia}.
- **NS:** dataset "Accessing Primary Care in Nova Scotia", Socrata resource
  **`fac5-58sq`** — real columns `zone, type, date, measure_name, actual` (by health
  zone; no provincial total, no percent). The connector sums **Community Pharmacy
  PCC visits** across zones per month → a provincial monthly count (`higher_is_better`).

Verified by running `hapi inspect` on a networked GitHub runner (the sandbox blocks
the source domains); fixtures mirror the confirmed real shapes.

## Files

| File | Source format | Connector | Indicator |
|------|---------------|-----------|-----------|
| `statcan_population_65plus.csv` | StatCan full-table CSV (filtered) | `statcan_wds` | `demography.population_65plus` |
| `ns_accessing_primary_care.json` | Socrata SODA JSON (zone/type/date/measure/actual) | `ns_open_data` | `care_access.pharmacy_primary_care_visits` |
| `cihi_home_care_clients_65plus.csv` | CIHI data-table CSV (incl. an `x` suppression) | `cihi_irrs` | `care_access.home_care_clients_65plus` |
