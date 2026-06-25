# 10 — Data Sources Catalog (Nova Scotia + Federal)

## 中文概览

本文给出 v1(Nova Scotia + 联邦)的**具体**数据源目录:名称、机构、URL、访问方式、许可证、更新频率、相关 HAPI 域。每个条目对应 [`03-data-model.md`](03-data-model.md) 中的一条 `DataSource` 记录。下方 URL 已于 2026-06 经过核实。

**重要变更(务必注意)**:CIHI 已于 **2025 年 3 月停用** 旧的居家照护上报系统(HCRS / HCRS-CA),并将于 **2026 年 3 月** 停用长期照护系统(CCRS),统一迁移到新的 **Integrated interRAI Reporting System(IRRS)**。因此 Care Access 域的居家/长照数据应以 **IRRS** 为准,旧系统仅用于历史数据衔接。

**许可证**:加拿大联邦及多数省级开放数据采用 **Open Government Licence**(可自由再利用,需署名)。CIHI 的明细数据多为**受控访问**(需申请/账户),但其公开报表与数据表可直接使用。逐源核实许可证是 Data Hub 入库前的硬性步骤。

> 说明:本目录覆盖 v1 的核心来源,并非穷尽。实现阶段每接入一个源,会在 `DataSource` 中固化其 url/access/licence/cadence,并用 WebFetch 抽查可达性。

---

## 1. How to read this catalog

Each source below maps to a `DataSource` row ([`03-data-model.md`](03-data-model.md) §2.5) and is consumed by a connector under `pipeline/ingest/` ([`05-module-data-hub.md`](05-module-data-hub.md)). Columns: **Publisher · URL · Access · Licence · Cadence · HAPI domains**. URLs verified 2026-06.

## 2. Federal sources

### 2.1 Statistics Canada — Web Data Service (WDS) API
- **Publisher:** Statistics Canada
- **URL:** https://www.statcan.gc.ca/en/developers/wds (user guide: https://www.statcan.gc.ca/en/developers/wds/user-guide)
- **Access:** `api` — REST; tables ("cubes") returned as JSON or SDMX-XML; no API key for public aggregate data
- **Licence:** Statistics Canada Open Licence
- **Cadence:** released each business day; per-table varies (annual/quarterly/monthly)
- **HAPI domains:** Health, Independence, Social Participation, Financial Security, Digital Inclusion
- **Notes:** Primary programmatic source. Aging-specific landing: https://www.statcan.gc.ca/en/subjects-start/older_adults_and_population_aging . Demographic estimates by age/sex (provinces/territories, 1971→present) anchor per-capita denominators.

### 2.2 Census of Population
- **Publisher:** Statistics Canada
- **URL:** https://www150.statcan.gc.ca/ (census tables via WDS / catalogue)
- **Access:** `api` / `csv` / `portal_download`
- **Licence:** Statistics Canada Open Licence
- **Cadence:** every 5 years (latest cycle + intercensal estimates)
- **HAPI domains:** all (population structure, aging denominators, income, dwelling, language, internet)
- **Notes:** Source of truth for population-by-age denominators used across HAPI normalization.

### 2.3 Health Infobase — Health of People in Canada Dashboard
- **Publisher:** Public Health Agency of Canada (PHAC), with Health Canada / ESDC / CMHC
- **URL:** https://health-infobase.canada.ca/health-of-people-in-canada-dashboard/ (indicators: https://health-infobase.canada.ca/health-of-people-in-canada-dashboard/indicators.html)
- **Access:** `portal_download` / `csv` (dashboard + downloadable indicator data); also listed on Open Government
- **Licence:** Open Government Licence – Canada
- **Cadence:** periodic indicator updates
- **HAPI domains:** Health, Social Participation, Financial Security
- **Notes:** 50+ interactive indicators; each documents its own source and method — useful as both data and methodological reference for HAPI.

### 2.4 Canada Open Data / Open Government Portal (CKAN)
- **Publisher:** Government of Canada (federates provincial/municipal datasets too)
- **URL:** https://open.canada.ca/ (API: https://open.canada.ca/en/access-our-application-programming-interface-api)
- **Access:** `api` (CKAN Action API, GET-only, no key for reads) / `portal_download`
- **Licence:** Open Government Licence – Canada (per-dataset)
- **Cadence:** continuous (catalog)
- **HAPI domains:** all (discovery layer)
- **Notes:** Discovery + federation layer. Many federal departmental datasets and some provincial data are reachable here via one CKAN API.

### 2.5 CIHI — Canadian Institute for Health Information
- **Publisher:** CIHI
- **URL:** https://www.cihi.ca/en/access-data-and-reports (data tables: https://www.cihi.ca/en/access-data-and-reports/data-tables)
- **Access:** mixed — public **data tables / reports** are `portal_download`; **record-level data is controlled access** (application/eligible-organization account, e.g. via CIHI Portal / data request form)
- **Licence:** CIHI terms (public tables reusable with attribution; microdata controlled)
- **Cadence:** annual / per-product
- **HAPI domains:** **Care Access** (home care, LTC, ED visits, hospitalization), Health
- **Notes — system transition (important):** CIHI **decommissioned HCRS / HCRS-CA (home care) in March 2025** and will **decommission CCRS (LTC) by March 2026**, consolidating onto the **Integrated interRAI Reporting System (IRRS)** (launched 2019–2020).
  - IRRS metadata: https://www.cihi.ca/en/integrated-interrai-reporting-system-irrs-metadata
  - LTC data holdings: https://www.cihi.ca/en/topics/long-term-care/data-holdings
  - **Implication for us:** treat IRRS as the forward source for home-care/LTC indicators; use HCRS/CCRS only for historical continuity. Record this in the relevant `DataSource.notes` and handle the series break explicitly in the Data Hub.

## 3. Nova Scotia sources

### 3.1 Nova Scotia Open Data Portal
- **Publisher:** Government of Nova Scotia (Socrata platform)
- **URL:** https://data.novascotia.ca/
- **Access:** `api` (Socrata SODA API) / `csv` / `portal_download`
- **Licence:** Open Government Licence – Nova Scotia
- **Cadence:** per-dataset
- **HAPI domains:** Health, Care Access, Financial Security, Social Participation
- **Notes:** Includes Dept. of Health & Wellness annual statistics (e.g. MSI, ER closures), community health networks, and **"Action for Health"** (https://data.novascotia.ca/Health-and-Wellness/Action-for-Health/m9ng-y7cu) — NS's health-system plan with trackable measures, directly relevant to Care Access.

### 3.2 Nova Scotia Health / Department of Seniors and Long-Term Care
- **Publisher:** Nova Scotia Health; NS Dept. of Seniors and Long-Term Care
- **URL:** departmental pages + datasets surfaced via 3.1 and Open Government (2.4)
- **Access:** `portal_download` / `web_scrape` (some indicators only in reports/PDF)
- **Licence:** Open Government Licence – Nova Scotia (where published as open data)
- **Cadence:** varies
- **HAPI domains:** Care Access (home care, LTC capacity/wait times), Health
- **Notes:** Some provincial LTC/home-care operational figures appear in reports rather than open datasets; these need extraction (web_scrape connector) and careful `quality_flag` handling.

## 4. Source → HAPI domain coverage matrix

| Source | Health | Independence | Social Part. | Financial Sec. | Care Access | Digital Incl. |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|
| StatCan WDS | ● | ● | ● | ● | | ● |
| Census | ● | ● | ● | ● | | ● |
| Health Infobase | ● | | ● | ● | | |
| Canada Open Data (CKAN) | ● | ● | ● | ● | ● | ● |
| CIHI (incl. IRRS) | ● | | | | ● | |
| NS Open Data | ● | | ● | ● | ● | |
| NS Health / Seniors & LTC | ● | ● | | | ● | |

> Gaps are intentional signals: e.g. **Digital Inclusion** for older adults leans on StatCan/Census internet-use tables; **Care Access** leans on CIHI/IRRS + NS sources. The matrix drives which connectors v1 prioritizes (Care Access first — see [`05-module-data-hub.md`](05-module-data-hub.md) §7).

## 5. Licence & compliance summary

- **Open Government Licence (Canada / Nova Scotia):** free reuse with attribution — safe to ingest, transform, and redistribute aggregates.
- **Statistics Canada Open Licence:** similar; attribution required.
- **CIHI:** public tables/reports reusable with attribution; **record-level/controlled data requires application** and is *not* redistributed — only derived aggregates per CIHI terms.
- **Process rule:** the Data Hub records each source's licence in `DataSource.licence` and refuses to publish anything whose licence forbids redistribution. Licence verification is a mandatory pre-ingest step.

## 6. Verification status

URLs and the CIHI HCRS/CCRS→IRRS transition were verified via web search in **2026-06**. During implementation, each connector re-checks its endpoint at first run (storing `DatasetVersion.retrieved_at` + `checksum`), so the catalog stays self-validating rather than relying on this snapshot.

## 7. Out of scope for v1

Ontario, BC, and other provincial portals; municipal data; specialized registries. These attach to the same model as new `DataSource` rows + connectors when the platform expands beyond NS + Federal.
