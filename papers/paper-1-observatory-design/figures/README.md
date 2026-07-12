# Figures

| File | Paper | Source | How to regenerate |
|------|-------|--------|-------------------|
| `intelligence-cycle.{svg,png}` | Fig 1 | `gen_cycle.py` (hand-laid) | `python gen_cycle.py` |
| `system-context.{svg,png}` | Fig 2 | `system-context.mmd` (from `docs/01`) | render mermaid (below) |
| `architecture.{svg,png}` | Fig 3 | `architecture.mmd` (from `docs/02`) | render mermaid (below) |
| `data-model-er.{svg,png}` | Fig 4 | `data-model-er.mmd` (from `docs/03`) | render mermaid (below) |

Both `.svg` (source, scalable — prefer for the LaTeX build) and `.png` (2× raster,
for Markdown preview) are committed.

## Regenerating

The cycle is hand-authored SVG:

```bash
python gen_cycle.py
```

The other three are Mermaid, kept in sync with their source docs. Render with any
Mermaid tool, e.g. mermaid-cli:

```bash
npx -p @mermaid-js/mermaid-cli mmdc -i system-context.mmd -o system-context.svg -t neutral -b white
```

(The `.mmd` files are extracts of the Mermaid blocks in `docs/01`–`docs/03`; if a
diagram changes there, re-copy the block and re-render.)

For the arXiv LaTeX build, prefer the `.svg` files (convert to PDF with `rsvg-convert`
or `inkscape`), or use the `.png` files directly.
