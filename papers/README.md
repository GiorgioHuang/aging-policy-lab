# Papers

Manuscripts that build on — and deposit assets back into — the Observatory
platform. The research arc deepens a *single* platform rather than spawning
disconnected studies; see [`docs/09-research-roadmap.md`](../docs/09-research-roadmap.md).

| # | Working title | Core contribution | Status | Folder |
|---|---------------|-------------------|--------|--------|
| 1 | Design of a Reproducible Healthy Aging Policy Observatory | Research infrastructure | **drafting** | [`paper-1-observatory-design/`](paper-1-observatory-design/) |
| 2 | The HAPI Methodology | Composite-indicator framework | planned | — |
| 3 | AI-assisted Policy Intelligence | Grounded AI + evidence synthesis | planned | — |
| 4 | Causal Evaluation of Canadian Aging Policies | ITS / DiD / synthetic control | planned | — |

Each paper deepens *one* stage of the Healthy Aging Policy Intelligence Cycle
(Observation → Evidence → Indicator → Policy → Outcome → Feedback) that Paper 1
introduces: Paper 2 the Indicator stage, Paper 3 the Feedback stage, Paper 4 the
Outcome stage.

## Conventions

- **Language:** English (per the Paper 1 decision). The platform docs carry a
  Chinese overview; the manuscripts do not.
- **Source of truth:** every quantitative claim traces to the platform — a table
  in [`db/`](../db), an indicator in
  [`pipeline/hapi_pipeline/indicators/`](../pipeline/hapi_pipeline/indicators),
  or an analytic result from [`pipeline/hapi_pipeline/analytics/`](../pipeline/hapi_pipeline/analytics).
  Figures reproduce from the pipeline; do not hand-enter numbers.
- **Format:** drafted in Markdown for reviewable diffs; convert to arXiv LaTeX/PDF
  near submission (see each paper's README for the `pandoc` command).
- **Placeholders:** anything awaiting a computed value or a full citation is marked
  `[TODO: …]` so an editing pass can find every open item with one grep.
