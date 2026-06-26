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
│   ├── statcan_wds.py · ns_open_data.py · cihi_irrs.py
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
