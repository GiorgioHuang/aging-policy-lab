# `pipeline/` — Python data & analysis core

## 中文概览

平台的数据/分析核心(docs/02 §1)。Python 负责采集、ETL、HAPI 指标计算与统计分析,
通过 Postgres 与前端解耦。Phase 1 仅提供包骨架 + 可用的数据库连接助手;连接器与分析
在后续阶段加入(docs/11)。

## Structure

```
pipeline/hapi_pipeline/
├── config.py       resolve DATABASE_URL from env / repo .env
├── db.py           lazy psycopg connection helper
├── contracts.py    load shared enums from packages/contracts/enums.json
├── loader.py       upsert source/indicator + idempotent DatasetVersion + load   (Phase 2)
├── cli.py          check · enums · ingest · observations
├── ingest/         one connector per data source                                (Phase 2)
│   ├── base.py       Connector ABC + specs (DataSource/Indicator/Observation)
│   ├── registry.py   list of connectors
│   ├── _statcan.py   shared WDS full-table CSV fetch/filter/inspect helpers
│   ├── statcan_wds.py · ns_open_data.py
│   ├── ns_ltc_waitlist.py          care_access (NS LTC Waitlist, Socrata c39g-gsdd)
│   ├── cihi_caregiver_distress.py  independence (CIHI Caregiver Distress, manual)
│   ├── statcan_low_income.py       financial_security (StatCan 11-10-0135)
│   ├── statcan_internet_use.py     digital_inclusion  (StatCan 22-10-0135)
│   ├── statcan_life_expectancy.py  health             (StatCan 13-10-0389)
│   ├── statcan_cchs.py             social_participation + care_access (StatCan 13-10-0096)
│   ├── statcan_functional_health.py independence       (StatCan 13-10-0966)
│   ├── statcan_ltc_employment.py   care_access (LTC/residential-care workforce, StatCan 14-10-0202)
│   └── fixtures/     vendored sample payloads (see fixtures/README.md)
├── transform/      cleaning, normalization, quality checks                       (Phase 2)
├── indicators/     HAPI computation                                             (Phase 3)
├── analytics/      association + quasi-experimental                              (Phase 4)
└── ai/             Claude API orchestration                                     (Phase 3/4)
```

## Data Hub (Phase 2)

Each connector declares its `DataSource` + `Indicator`(s), fetches a payload,
and the loader records an immutable `DatasetVersion` (keyed on a SHA-256
checksum) before loading immutable `Observation`s. Re-ingesting unchanged data
is a **no-op**; a changed payload creates a *new* version and *new* rows while
old values are retained (docs/05 §3-4).

```bash
python -m hapi_pipeline.cli ingest             # all connectors (idempotent)
python -m hapi_pipeline.cli ingest --source statcan_wds
python -m hapi_pipeline.cli ingest --live --dry-run  # fetch+parse+validate, no DB writes
python -m hapi_pipeline.cli ingest --live      # fetch real upstreams + refresh fixtures
python -m hapi_pipeline.cli observations       # print loaded values with full lineage
```

To confirm the connectors against the **real** sources and then automate
ingestion (GitHub Actions + managed Postgres), follow [`../RUNBOOK.md`](../RUNBOOK.md).

## Policy Library & HAPI (Phase 3)

```bash
python -m hapi_pipeline.cli policies seed       # load curated NS + Federal policies
python -m hapi_pipeline.cli policies summarize  # AI summaries (needs ANTHROPIC_API_KEY; optional)
python -m hapi_pipeline.cli score               # compute HAPI v1 domain + composite scores
python -m hapi_pipeline.cli weights             # weighting schemes + composite sensitivity
```

- `policies/` — curated `seed_policies.json` + idempotent loader (upserts policies,
  initial PolicyVersion, and `policy_indicator` links to existing indicators).
- `ai/summarize.py` — Claude-generated `ai_summary` per policy, versioned; graceful
  no-op without `ANTHROPIC_API_KEY` (model via `HAPI_SUMMARY_MODEL`, default opus).
- `indicators/hapi_v1.py` + `engine.py` — HAPI v1 methodology (per-capita
  normalization, weights, `method_version` v1) writing auditable `hapi_score` rows
  (each carries the indicator codes, raw values, and normalized inputs). v1 now
  spans **all six HAPI domains** — Health (StatCan 13-10-0389 life expectancy at
  65), Independence (CCHS 13-10-0966 functional health), Social Participation
  (CCHS 13-10-0096 community belonging), Financial Security (StatCan 11-10-0135
  seniors' low-income rate), Care Access (CCHS regular healthcare provider + live
  NS long-term-care waitlist), and Digital Inclusion
  (StatCan 22-10-0135 seniors' internet use) — so `overall` is a real six-domain
  composite that blends whichever domains have data per jurisdiction × year
  (recorded in each `overall` row's `inputs`). The composite is **weighted** with
  theory-anchored "expert" tiers (Health + Care Access tier 1; Financial Security
  + Independence tier 2; Social Participation + Digital Inclusion tier 3),
  renormalized over the domains present. Within Independence, the 65–74 and 75+
  functional-health bands are averaged. The weighting is sensitivity-tested:
  `hapi weights` shows the composite under equal / expert / empirical schemes
  (see `indicators/weighting.py`).

## Analytics & AI assistant (Phase 4)

```bash
python -m hapi_pipeline.cli analyze             # Tier-1 trends + one worked ITS
python -m hapi_pipeline.cli literature seed     # starter literature KB
python -m hapi_pipeline.cli assistant "NS dementia policy"   # evidence pack (+ cited draft w/ key)
```

- `analytics/` — `descriptive.py` (trends; **association** only) and `its.py`
  (interrupted time series via statsmodels + Newey-West HAC SEs; **causal** tier
  with assumptions/limitations). `runner.py` stores `analysis_finding` rows; the
  Association/Causal tag is explicit on every finding (docs/07 §3).
- **Care Access / CIHI data sourcing.** CIHI has no open API (manual portal
  downloads / controlled access), so the live, auto-refreshing Care-Access
  indicator is CCHS "has a regular healthcare provider" (`statcan_cchs`,
  13-10-0096), joined by the **live NS Long-Term Care Waitlist** (`ns_ltc_waitlist`,
  Socrata `c39g-gsdd`, lower-is-better, NS-only). CIHI's home-care client counts
  were **retired** — their Quick Stats exclude Nova Scotia (NS doesn't submit) —
  in favour of that real NS measure. The remaining CIHI source,
  `cihi_caregiver_distress` (Independence; National → CA, NS → CA-NS), has **real**
  captured values and is manually refreshed (RUNBOOK.md §E, no CIHI API).
  Independence averages functional health (65–74, 75+) with caregiver distress.
- `literature/` — starter literature KB seed + loader.
- `ai/assistant.py` — topic → grounded **evidence pack** (policies + literature +
  findings + indicators, each with a citation id) → Claude **cited draft** where
  every claim cites a pack item; graceful without `ANTHROPIC_API_KEY`.

> **Fixtures vs live.** Default runs read vendored sample payloads under
> `ingest/fixtures/` (this environment can't reach the live source domains), so
> the numbers are realistic but **not** official statistics — their provenance is
> recorded as `source_version = 'fixture:…'`. Use `--live` where the network
> allows. See [`hapi_pipeline/ingest/fixtures/README.md`](hapi_pipeline/ingest/fixtures/README.md).

## Setup

```bash
cd pipeline
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # or: pip install -e .

# with Postgres up + migrated (see ../db/README.md):
python -m hapi_pipeline.cli check          # ✓ connected — N jurisdiction(s)
python -m hapi_pipeline.cli enums          # print shared enum contracts
python -m hapi_pipeline.cli ingest         # load the Data Hub connectors
python -m hapi_pipeline.cli observations   # show loaded values + lineage
```

The pipeline reads `DATABASE_URL` (or `POSTGRES_*`) from the repo-root `.env`.
