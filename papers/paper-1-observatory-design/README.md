# Paper 1 — Design of a Healthy Aging Policy Observatory

**Target:** arXiv preprint (cs.CY / cs.DL, cross-list stat.AP), English.
**Thesis:** the platform architecture + the HAPI methodology constitute a
*reproducible research instrument* for evaluating healthy-aging policy, not a
dashboard — and that design is itself the contribution.

## Files

- [`paper.md`](paper.md) — the manuscript draft.

## Status

First complete draft. Open items are marked `[TODO: …]` in `paper.md`:

```
grep -n "TODO" paper.md
```

The main open items are (a) inserting the *computed* HAPI scores and the worked
ITS coefficients from the live database (methodology and observed ranges are
already written; final numbers reproduce from the pipeline), and (b) completing
the reference list with full bibliographic details.

## Reproducing figures / numbers

The paper cites platform artifacts. To regenerate them:

```bash
# HAPI domain + composite scores, and the weighting sensitivity table
cd pipeline && python -m hapi_pipeline.cli score
python -m hapi_pipeline.cli hapi weights          # equal / expert / empirical

# The worked interrupted-time-series example
python -m hapi_pipeline.cli analyze
```

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
