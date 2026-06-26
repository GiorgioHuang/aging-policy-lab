# `apps/web` — Next.js frontend & dashboards

The product surface of the observatory (Policy Library, HAPI, Analytics, Assistant).
TypeScript owns the UI; it **reads** the Postgres tables the Python pipeline populates
(see [`../../docs/02-architecture.md`](../../docs/02-architecture.md)).

## Phase 1 status

A minimal App-Router app that reads the **jurisdiction tree** from Postgres and renders
it — the proof that the web tier can read the data model (docs/03).

## Run

```bash
# from the repo root, with Postgres up and migrated (see ../../db/README.md)
echo "DATABASE_URL=postgresql://hapi:hapi_dev_password@localhost:5432/hapi" > apps/web/.env.local
npm install                      # installs the workspace
npm run dev --workspace apps/web # http://localhost:3000
```

`apps/web/.env.local` is gitignored. The app reads `DATABASE_URL` from the environment;
in production set it via your host's secrets, not a file.
