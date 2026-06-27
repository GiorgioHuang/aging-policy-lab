# Canadian Healthy Aging Policy Observatory

**A research infrastructure for monitoring, quantifying, and evaluating the effects of aging-related public policy across Canadian governments.**

> Part of the **Healthy Aging Intelligence Lab (HAIL)** — using AI, data science, and policy analysis to help Canada build a fairer, more efficient, and more sustainable system of support for an aging population.

> **Status: Phase 5 — Researcher dashboard + SaaS seams.** All five modules have a working v1, now tied together by a **cross-cutting dashboard** at `/`: a KPI strip (policies · indicators · observations · HAPI scores · findings · references), a per-jurisdiction **HAPI snapshot** (overall + care-access composite), recent policies and recent findings (Association/Causal tagged), the live jurisdiction tree, and a shared top nav across every module. Under the hood the platform is now **multi-tenant-ready**: a single access seam ([`apps/web/lib/access.ts`](apps/web/lib/access.ts)) resolves "who is asking" and every org-scoped read routes through it, backed by nullable `org_id` columns ([`db/migrations/0004`](db/migrations/0004_tenancy_org_id.sql)) — a no-op single-tenant today, switch-on-able for SaaS (Stage 2/3) without a schema rewrite. The earlier phases stand: **Policy Analytics** (Tier-1 `Association` trends + a worked **interrupted time series**, `Causal(ITS)`, with assumptions/limitations) and the **AI Research Assistant** (topic → cited **evidence pack** + Claude-drafted review). The web app surfaces everything: `/` · `/policies` · `/hapi` · `/data` · `/analytics` · `/assistant`. See [`docs/11-implementation-roadmap.md`](docs/11-implementation-roadmap.md).
>
> ⚠️ This environment can't reach the live source domains, so connectors run against **vendored sample fixtures** by default (realistic but not official statistics; provenance recorded as `fixture:…`). Run `hapi ingest --live` where the network allows.

---

## 中文概览

`aging-policy-lab` 不是一个普通的政策网站,而是一座**研究基础设施(Research Infrastructure)**。它的核心不是"收集政策",而是**持续监测、量化评估、预测加拿大各级政府老龄化政策的效果**。

平台定位为 **Canadian Healthy Aging Policy Observatory(加拿大健康老龄化政策观察平台)**,隶属于一个十年愿景的实验室 **Healthy Aging Intelligence Lab(HAIL)**。它同时承担三重角色:

- **研究平台** —— 持续产出论文与数据,而非一次性课题;
- **创业项目** —— 未来可发展为 SaaS 或研究服务;
- **研究资产库** —— 不断积累数据库、指标体系、AI Agent、文献知识库、政策知识图谱与可视化看板。

第一版(v1)先聚焦 **Nova Scotia + 联邦(Federal)** 作为可复制的模板,未来扩展至全加拿大。本仓库当前阶段只交付**设计文档/白皮书**,作为后续开发蓝图与第一篇论文的基础。

平台由五个核心模块组成:① Policy Library(政策库)② Data Hub(数据中心)③ Indicators / HAPI(指标体系)④ Policy Analytics(政策分析)⑤ AI Research Assistant(AI 研究助手)。

---

## Why an "Observatory," not a website

A policy website *collects and displays* documents. An **observatory** does something categorically different: it continuously **observes a system, measures it against a consistent yardstick, and reports change over time.** That distinction is the whole point of this project.

| A policy website | This observatory |
|---|---|
| Stores policy text | Tracks each policy's lifecycle, budget, target population, and KPIs over time |
| Uses whatever metrics governments publish | Maintains an independent, transparent index (**HAPI**) with documented methodology |
| Answers "what policies exist?" | Answers "did policy X move outcome Y — and how confidently can we say so?" |
| A static reference | A reproducible, versioned, citable research instrument |

## The five modules

| # | Module | What it does |
|---|--------|--------------|
| ① | **[Policy Library](docs/04-module-policy-library.md)** | A jurisdiction-aware, time-axis catalog of aging policies (Canada → Federal / Nova Scotia), each record carrying release date, department, full text, AI summary, budget, target population, KPIs, and lifecycle. |
| ② | **[Data Hub](docs/05-module-data-hub.md)** | A versioned, lineage-tracked ingestion layer over Canada's open data: StatCan, Health Infobase, CIHI, Nova Scotia Open Data, Census, and more. |
| ③ | **[Indicators / HAPI](docs/06-module-indicators-hapi.md)** | The **Healthy Aging Policy Index** — an independent index across six domains (Health, Independence, Social Participation, Financial Security, Care Access, Digital Inclusion) with documented data sourcing and scoring. |
| ④ | **[Policy Analytics](docs/07-module-policy-analytics.md)** | Association analysis over open data — with explicit, rigorous separation of correlation from causation (ITS, DiD, synthetic control). |
| ⑤ | **[AI Research Assistant](docs/08-module-ai-research-assistant.md)** | A retrieval-augmented agent over the policy corpus + literature that finds policies, papers, data, and trends, and drafts cited literature reviews. |

## Documentation index

| Doc | Contents |
|-----|----------|
| [`00-vision.md`](docs/00-vision.md) | HAIL Lab mission & vision; the "observatory ≠ website" thesis; value proposition |
| [`01-platform-overview.md`](docs/01-platform-overview.md) | How the five modules fit together; system context diagram; user roles |
| [`02-architecture.md`](docs/02-architecture.md) | Tech stack & rationale; monorepo layout; deployment & SaaS path; security/privacy |
| [`03-data-model.md`](docs/03-data-model.md) | Core schema (Jurisdiction / Policy / Indicator / DataSource / Observation); ER diagram |
| [`04-module-policy-library.md`](docs/04-module-policy-library.md) | Policy Library design |
| [`05-module-data-hub.md`](docs/05-module-data-hub.md) | Data Hub & ETL pipeline design |
| [`06-module-indicators-hapi.md`](docs/06-module-indicators-hapi.md) | HAPI indicator system & scoring methodology |
| [`07-module-policy-analytics.md`](docs/07-module-policy-analytics.md) | Analytics & causal-inference rigor |
| [`08-module-ai-research-assistant.md`](docs/08-module-ai-research-assistant.md) | AI research assistant design |
| [`09-research-roadmap.md`](docs/09-research-roadmap.md) | The four-paper research arc & research-asset ledger |
| [`10-data-sources-catalog.md`](docs/10-data-sources-catalog.md) | Concrete NS + Federal data sources (URLs, access, licence, cadence) |
| [`11-implementation-roadmap.md`](docs/11-implementation-roadmap.md) | Phased build plan & milestones |

## Tech stack

- **Frontend / dashboards:** Next.js (TypeScript)
- **Data pipeline / analytics:** Python (ingestion, ETL, statistics)
- **Storage:** PostgreSQL
- **AI layer:** Claude API (policy summarization, the research assistant, HAPI scoring assistance)

See [`docs/02-architecture.md`](docs/02-architecture.md) for the full rationale and monorepo layout.

## Repository layout

```
apps/web/            Next.js (TypeScript) — UI/dashboards; reads the data model
pipeline/            Python — ingestion, ETL, HAPI indicators, analytics (skeleton)
db/                  schema, versioned migrations, seed, and a psql migration runner
packages/contracts/  shared, language-neutral enum contracts (TS + Python)
docs/                the v1 design whitepaper
docker-compose.yml   local Postgres
```

## Getting started (Phase 1)

```bash
cp .env.example .env
docker compose up -d db                 # local Postgres
npm run db:migrate -- --seed            # apply schema + seed Canada → Federal / NS
                                         # (or: bash db/migrate.sh --seed)

cd pipeline && pip install -r requirements.txt && \
  python -m hapi_pipeline.cli ingest && \
  python -m hapi_pipeline.cli observations   # load Data Hub + show lineage
cd ..

npm install
echo "DATABASE_URL=postgresql://hapi:hapi_dev_password@localhost:5432/hapi" > apps/web/.env.local
npm run dev                              # http://localhost:3000 — tree + /data lineage page
```

Per-area setup: [`db/README.md`](db/README.md), [`apps/web/README.md`](apps/web/README.md),
[`pipeline/README.md`](pipeline/README.md). To pull **real** data (live connectors),
automate ingestion, and **deploy the web app to Google Cloud Run**, see
[`RUNBOOK.md`](RUNBOOK.md) (§B live data · §C scheduled ingest · §D Cloud Run).

Deploy the web tier in one command (Cloud Build builds the [`Dockerfile`](Dockerfile)):

```bash
gcloud run deploy hapi-web --source . --region northamerica-northeast1 \
  --allow-unauthenticated --update-secrets DATABASE_URL=DATABASE_URL:latest
```

## Scope of v1

- **Geography:** Nova Scotia + Federal (a replicable template; pan-Canadian expansion later).
- **Now live:** the design whitepaper, the Phase 1 scaffold (monorepo, schema, seed, web read), and the Phase 2 Data Hub (lineage-tracked ingestion + `/data` view). HAPI scoring comes in Phase 3 ([`docs/11`](docs/11-implementation-roadmap.md)).

## License

Documentation is intended to be released under **CC-BY-4.0** (see [`LICENSE`](LICENSE)). The licence for future code will be decided when the codebase is created.

## A note on rigor

This platform analyzes public data to surface *associations* and to support *evidence-based* evaluation. Association is not causation. Causal claims require careful quasi-experimental designs (interrupted time series, difference-in-differences, synthetic control), each with stated assumptions and limitations. The observatory is built to make that distinction explicit at every step — see [`docs/07-module-policy-analytics.md`](docs/07-module-policy-analytics.md).
