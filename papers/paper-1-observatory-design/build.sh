#!/usr/bin/env bash
# Build the arXiv LaTeX source (and a PDF, if a LaTeX engine is present) from
# paper.md. The manuscript carries its own manual section numbers, so we do NOT
# pass --number-sections. Title/author/date come from metadata below; the draft's
# top matter (H1 + author line) is stripped so it doesn't become a section.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build

TITLE="Design of a Reproducible Healthy Aging Policy Observatory: Infrastructure for Trustworthy Aging-Policy Evidence in Canada"

# Body = paper.md with the leading title block (everything up to and including the
# first horizontal rule) removed, so pandoc doesn't render the H1 as a section.
awk 'f{print} /^---$/{f=1}' paper.md > build/_body.md

cat > build/_meta.yaml <<YAML
---
title: "${TITLE}"
author:
  - "Quangui Huang (Giorgio), Independent researcher (Healthy Aging Intelligence Lab / HAIL initiative)"
date: "Preprint — draft, not peer reviewed"
geometry: margin=1in
fontsize: 11pt
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
---
YAML

# LaTeX source (always produced; needs no TeX engine).
pandoc build/_meta.yaml build/_body.md \
  --standalone --from gfm --to latex \
  --resource-path=.:figures \
  -o build/paper.tex
echo "wrote build/paper.tex"

# PDF, only if an engine is available.
ENGINE=""
for e in tectonic xelatex pdflatex lualatex; do
  command -v "$e" >/dev/null 2>&1 && { ENGINE="$e"; break; }
done
if [ -n "$ENGINE" ]; then
  pandoc build/_meta.yaml build/_body.md \
    --standalone --from gfm \
    --resource-path=.:figures \
    --pdf-engine="$ENGINE" \
    -o build/paper.pdf
  echo "wrote build/paper.pdf (engine: $ENGINE)"
else
  echo "no LaTeX engine found — skipped PDF (install tectonic or texlive to enable)."
fi
