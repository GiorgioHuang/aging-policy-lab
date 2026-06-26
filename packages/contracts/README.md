# `packages/contracts` — shared data contracts

Per [`../../docs/02-architecture.md`](../../docs/02-architecture.md) §1, the TypeScript
web app and the Python pipeline are **decoupled by contract**: they don't call each other,
they agree on shapes.

- `enums.json` — the language-neutral **single source of truth** for the enums also defined
  in `db/migrations/0001_init.sql` and `docs/03-data-model.md`.
- `index.ts` — typed TS exports derived from `enums.json` (for `apps/web`).
- The Python side reads the same `enums.json` via `pipeline/hapi_pipeline/contracts.py`.

When an enum changes, edit `enums.json` and the migration together; both layers stay in sync.
