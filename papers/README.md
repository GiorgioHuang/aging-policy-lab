# Papers

Manuscripts that build on — and deposit assets back into — the Observatory
platform. The research arc deepens a *single* platform rather than spawning
disconnected studies; see [`docs/09-research-roadmap.md`](../docs/09-research-roadmap.md).

| # | Working title | Status | Folder |
|---|---------------|--------|--------|
| 1 | Design of a Healthy Aging Policy Observatory | **drafting** | [`paper-1-observatory-design/`](paper-1-observatory-design/) |
| 2 | An AI-assisted, Grounded Framework for Policy Analysis | planned | — |
| 3 | Agent-based Simulation for Long-term Care Policy | planned | — |
| 4 | Quasi-experimental Evaluation of Healthy Aging Policies | planned | — |

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
