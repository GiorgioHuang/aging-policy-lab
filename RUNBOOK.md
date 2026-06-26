# Runbook — live ingestion & automation

Operational steps for getting **real** data into the Data Hub. The design lives in
[`docs/`](docs/); this is the "how to run it" companion.

> Why this exists: the Claude Code sandbox blocks the source domains, so the repo
> ships vendored **sample fixtures**. On any machine with normal internet the
> connectors fetch live. Nothing about the app needs to change — you just run it
> somewhere with outbound access.

---

## B — Confirm the connectors locally (do this first)

### 0. Prereqs
```bash
git clone <repo> && cd aging-policy-lab
cp .env.example .env                      # edit DATABASE_URL if not using the default
docker compose up -d db                   # or any reachable Postgres 16
bash db/migrate.sh --seed                 # schema + jurisdiction tree

cd pipeline
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

### 1. Dry-run against the **live** sources (no DB writes, no fixture changes)
```bash
python -m hapi_pipeline.cli ingest --live --dry-run
```
This fetches from StatCan + NS, parses, runs quality checks, and prints a sample.
Expected: a `◇` line per source with `parsed N, would load N` and a few realistic
sample rows. CIHI has no live API, so it falls back to its fixture (shown as
`[fixture]`). **This is the fast connector confirmation.**

Per-source things to eyeball:
| Source | Confirm | If it looks wrong |
|--------|---------|-------------------|
| `statcan_wds` | population 65+ for CA & CA-NS, ~6–7M / ~200–230k | check the gender label in Table 17-10-0005 (`Both sexes` vs `Total - gender`); both are accepted in `statcan_wds.py` |
| `ns_open_data` | NS unmet-need % (single-digit to mid-teens) | the Socrata columns of `fac5-58sq` may have renamed; adjust the `_*_HINTS` in `ns_open_data.py` |
| `cihi_irrs` | falls back to fixture | expected — refresh the CSV by hand from CIHI |

### 2. Load for real (writes DB + refreshes the StatCan/NS fixtures with live data)
```bash
python -m hapi_pipeline.cli ingest --live
python -m hapi_pipeline.cli observations        # values with full lineage
```
`source_version` now reads `WDS:…` / `SODA:…` instead of `fixture:…`. Re-running
is a no-op unless upstream changed.

### 3. See it in the app
```bash
cd .. && npm install
echo "DATABASE_URL=$DATABASE_URL" > apps/web/.env.local
npm run dev      # http://localhost:3000/data
```

### 4. Commit the refreshed fixtures (so the repo carries real captured data)
```bash
git add pipeline/hapi_pipeline/ingest/fixtures/
git commit -m "Refresh connector fixtures from live sources"
```
After a real `--live` run the fixtures hold authentic captured payloads (the
checksums change), and the warning banners can come down.

---

## C — Automate ingestion (GitHub Actions + managed Postgres)

The lightweight "production" that matches the research-infrastructure goal: a
scheduled job keeps the database fresh. No web host required yet.

### 1. Provision a managed Postgres
Create a free Postgres (e.g. **Neon** or **Supabase**) and copy its connection
string (looks like `postgresql://user:pass@host/db?sslmode=require`).

### 2. Add it as a GitHub secret
Repo → Settings → Secrets and variables → Actions → **New repository secret**:
- Name: `DATABASE_URL`
- Value: the connection string from step 1

### 3. The workflow
[`.github/workflows/ingest.yml`](.github/workflows/ingest.yml) is already in the
repo. It runs on a weekly schedule and on manual dispatch: it installs the
pipeline, applies migrations + seed, runs `hapi ingest --live` against
`DATABASE_URL`, and prints the loaded observations. Trigger it manually the first
time: Actions → "Data Hub ingest" → **Run workflow**.

### 4. (Optional) point the web app at the same managed Postgres
Set `DATABASE_URL` wherever the Next.js app is hosted and it will read the same
data — see §D.

---

## D — Deploy the web app to Google Cloud Run

The web tier is stateless (it only reads Postgres), so it fits Cloud Run's
scale-to-zero model. The repo ships a standalone [`Dockerfile`](Dockerfile);
Cloud Run reads `DATABASE_URL` from Secret Manager and connects to Neon over TLS.

### 1. One-time GCP setup
```bash
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

# store the Neon connection string (use the POOLED string for serverless)
printf '%s' 'postgresql://<user>:<pwd>@<ep>-pooler.<region>.aws.neon.tech/<db>?sslmode=require' \
  | gcloud secrets create DATABASE_URL --data-file=-
```

### 2. Deploy (Cloud Build builds the Dockerfile, then deploys)
```bash
gcloud run deploy hapi-web \
  --source . \
  --region northamerica-northeast1 \
  --allow-unauthenticated \
  --update-secrets DATABASE_URL=DATABASE_URL:latest \
  --min-instances 0
```
`northamerica-northeast1` (Montreal) is closest to NS. The first deploy prints the
service URL — open `<url>/data`.

### 3. Grant the runtime service account access to the secret
If the deploy reports it can't access the secret, bind it (default runtime SA shown):
```bash
PROJ_NUM=$(gcloud projects describe <PROJECT_ID> --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:${PROJ_NUM}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor
```

### 4. (Optional) CI/CD
[`.github/workflows/deploy-web.yml`](.github/workflows/deploy-web.yml) deploys on
manual dispatch using Workload Identity Federation. Configure these repo secrets
first (and grant the deploy service account `run.admin`, `iam.serviceAccountUser`,
`cloudbuild.builds.editor`, `artifactregistry.writer`):
`GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_SERVICE_ACCOUNT`.

### Notes
- Use Neon's **pooled** endpoint (`...-pooler...`) — Cloud Run can spin up many
  instances and the pooler avoids exhausting Postgres connections.
- The app binds `0.0.0.0:$PORT` (Cloud Run sets `PORT=8080`); the image already
  handles this.
- The container ships no secrets; `DATABASE_URL` is injected at runtime only.
