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
├── cli.py          `hapi check` / `hapi enums`
├── ingest/         one connector per data source        (Phase 2)
├── transform/      cleaning, normalization, lineage      (Phase 2)
├── indicators/     HAPI computation                      (Phase 3)
├── analytics/      association + quasi-experimental       (Phase 4)
└── ai/             Claude API orchestration              (Phase 3/4)
```

## Setup

```bash
cd pipeline
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # or: pip install -e .

# with Postgres up + migrated (see ../db/README.md):
python -m hapi_pipeline.cli check      # ✓ connected — N jurisdiction(s)
python -m hapi_pipeline.cli enums      # print shared enum contracts
```

The pipeline reads `DATABASE_URL` (or `POSTGRES_*`) from the repo-root `.env`.
