#!/usr/bin/env bash
# Build the arXiv LaTeX source and a PDF from paper.md. The manuscript carries its
# own manual section numbers, so we do NOT pass --number-sections. Title/author/date
# come from metadata; the draft's top matter (H1 + author line) is stripped so it
# doesn't become a section.
#
# Wide tables: pandoc emits `longtable` with plain l/r columns that don't wrap, so
# text-heavy or many-column tables overflow the margin. We (a) shrink all tables via
# an included header, and (b) rewrite the two text-heavy tables' column specs to
# wrapping p{} columns. The PDF is compiled from the *patched* .tex, so the arXiv
# source and the PDF agree.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build

TITLE="Design of a Reproducible Healthy Aging Policy Observatory: Infrastructure for Trustworthy Aging-Policy Evidence in Canada"

# Body = paper.md with the leading title block (up to the first horizontal rule) removed.
awk 'f{print} /^---$/{f=1}' paper.md > build/_body.md

cat > build/_meta.yaml <<YAML
---
title: "${TITLE}"
author:
  - "Quangui Huang (Giorgio)"
date: "Preprint — draft, not peer reviewed"
geometry: margin=1in
fontsize: 11pt
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
---
YAML

# Header: render all longtables at \small with tight column padding so wide numeric
# tables fit; `array` (loaded by pandoc) provides the p{} column type used below.
cat > build/_header.tex <<'TEX'
\usepackage{etoolbox}
\AtBeginEnvironment{longtable}{\small}
\setlength{\tabcolsep}{4pt}
% Figures live in ../figures relative to the build dir where we compile.
\graphicspath{{../}{../figures/}{figures/}}
TEX

# LaTeX source (always produced; needs no TeX engine).
pandoc build/_meta.yaml build/_body.md \
  --standalone --from gfm --to latex \
  --include-in-header=build/_header.tex \
  --resource-path=.:figures \
  -o build/paper.tex

# Give the two text-heavy tables wrapping p{} columns so long cells don't overflow.
# (Python avoids the backslash-escaping pitfalls of sed for \linewidth.)
#   {llll} = Table 1 (RQ | Criterion | Evidence | Result) — wrap Evidence + Result
#   {lll}  = the research-program table (Paper | Contribution | Instantiates) — wrap Contribution
python3 - build/paper.tex <<'PY'
import sys
path = sys.argv[1]
s = open(path).read()
s = s.replace(r"{@{}llll@{}}", r"{@{}llp{0.33\linewidth}p{0.33\linewidth}@{}}")
s = s.replace(r"{@{}lll@{}}",  r"{@{}lp{0.60\linewidth}p{0.22\linewidth}@{}}")
# Stack the affiliation under the name so the byline isn't one over-wide line.
s = s.replace(
    r"\author{Quangui Huang (Giorgio)}",
    r"\author{Quangui Huang (Giorgio)\\[3pt]{\small Independent researcher "
    r"$\cdot$ Healthy Aging Intelligence Lab (HAIL) initiative}}")
open(path, "w").write(s)
PY
echo "wrote build/paper.tex"

# PDF: compile the *patched* source. Prefer xelatex/lualatex (Unicode: → ≠ etc.).
ENGINE=""
for e in xelatex lualatex tectonic pdflatex; do
  command -v "$e" >/dev/null 2>&1 && { ENGINE="$e"; break; }
done
if [ -n "$ENGINE" ]; then
  ( cd build && "$ENGINE" -interaction=nonstopmode -halt-on-error paper.tex >/dev/null 2>&1 \
    && "$ENGINE" -interaction=nonstopmode -halt-on-error paper.tex >/dev/null 2>&1 ) || true
  if [ -f build/paper.pdf ]; then
    echo "wrote build/paper.pdf (engine: $ENGINE)"
  else
    echo "PDF compile failed — see build/paper.log"; exit 1
  fi
else
  echo "no LaTeX engine found — skipped PDF (install texlive-xetex to enable)."
fi

# Sync the deliverables the website serves, so /research is never stale. The web app
# reads these from apps/web/public/papers (see apps/web/lib/site.ts).
PUB="../../apps/web/public/papers"
if [ -d "$PUB" ]; then
  [ -f build/paper.pdf ] && cp build/paper.pdf "$PUB/observatory-design.pdf"
  cp figures/intelligence-cycle.svg "$PUB/intelligence-cycle.svg"
  echo "synced PDF + figure to apps/web/public/papers"
fi
