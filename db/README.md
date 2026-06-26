# `db/` — schema, migrations & seed

## 中文概览

平台的数据库层,落地 [`../docs/03-data-model.md`](../docs/03-data-model.md) 的 schema。

- `schema/canonical.sql` — 规范化的全量 DDL 快照(便于阅读/对照),由迁移累积而成。
- `migrations/` — 版本化迁移(`0001_init.sql` …),按文件名顺序应用,已应用记录在 `schema_migrations` 表。
- `seed/` — 幂等种子数据;Phase 1 仅种入管辖区树(Canada → Federal / Nova Scotia)。
- `migrate.sh` — 仅依赖 `psql` 的极简迁移执行器。

## Layout

```
db/
├── migrations/        versioned, append-only SQL migrations (source of truth)
│   └── 0001_init.sql
├── seed/              idempotent seed data
│   └── 0001_jurisdictions.sql
├── schema/
│   └── canonical.sql  human-readable snapshot of the full schema
└── migrate.sh         psql-only migration runner
```

## Usage

```bash
cp .env.example .env          # set POSTGRES_* / DATABASE_URL
docker compose up -d db       # or use any reachable Postgres 16

bash db/migrate.sh            # apply migrations
bash db/migrate.sh --seed     # apply migrations + (re)seed jurisdictions
```

Migrations are applied once and tracked in `schema_migrations`; seeds use
`ON CONFLICT … DO NOTHING`, so both commands are safe to re-run.

## Conventions

- **Migrations are append-only.** To change the schema, add `0002_*.sql`, never edit an
  applied file. Keep `schema/canonical.sql` updated to match for easy review.
- **Observations are immutable**, policies are append-only (`policy_version`), and HAPI
  methodology is versioned (`hapi_score.method_version`) — see docs/03 §4.
- **Tenancy-ready:** core tables carry a nullable `org_id` for future Postgres RLS /
  multi-tenant SaaS (docs/02 §5) without a rewrite.
