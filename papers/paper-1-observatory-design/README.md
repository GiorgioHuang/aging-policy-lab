# Paper 1 — Design of a Healthy Aging Policy Observatory

**Target:** arXiv preprint (cs.CY / cs.DL, cross-list stat.AP), English.
**Thesis:** the platform architecture + the HAPI methodology constitute a
*reproducible research instrument* for evaluating healthy-aging policy, not a
dashboard — and that design is itself the contribution.

## Files

- [`paper.md`](paper.md) — the manuscript draft.

## Status

Complete draft with **all quantitative results filled in** from the pipeline
(corpus counts, HAPI domain/composite scores, weighting sensitivity, and the worked
ITS coefficients) and a **complete, verified reference list** (§11; academic
citations checked for volume/pages/DOI). Remaining open items require only
author/institution decisions or external confirmation, marked `[TODO: …]`:

```
grep -n "TODO" paper.md
```

They are: (a) the final author list & affiliations, (b) funding sources in the
acknowledgements, and (c) confirming the exact vintage of each cited Statistics
Canada table against the Data Hub. None require the database or block a preprint.

## Reproducing figures / numbers

Every quantitative block in the paper regenerates with one command:

```bash
cd pipeline
export DATABASE_URL=postgresql://hapi@localhost:5432/hapi   # a populated DB
python -m hapi_pipeline.cli paper-tables
```

`paper-tables` (see [`pipeline/hapi_pipeline/paper.py`](../../pipeline/hapi_pipeline/paper.py))
prints ready-to-paste Markdown for the corpus counts, the HAPI domain/composite
table, the weighting sensitivity table, and the ITS coefficients. To rebuild a
populated demo DB from committed fixtures first:

```bash
bash db/migrate.sh --seed
cd pipeline
python -m hapi_pipeline.cli policies seed
python -m hapi_pipeline.cli literature seed
python -m hapi_pipeline.cli ingest      # loads committed fixtures (offline)
python -m hapi_pipeline.cli score
python -m hapi_pipeline.cli analyze
python -m hapi_pipeline.cli paper-tables
```

The numbers in the current draft are from exactly this fixture-based instance;
re-running against the production database refreshes them to live coverage.

## Building a PDF for arXiv

Draft lives in Markdown; produce LaTeX/PDF near submission:

```bash
pandoc paper.md -o paper.pdf \
  --number-sections --toc \
  -V documentclass=article -V geometry:margin=1in
# arXiv wants source: `pandoc paper.md -o paper.tex --standalone` then tidy.
```

Mermaid figures in the draft reference the diagrams in [`../../docs/`](../../docs);
export them to PNG/PDF (e.g. `mermaid-cli`) and `\includegraphics` them in the
LaTeX build.
