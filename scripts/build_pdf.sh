#!/usr/bin/env bash
# Build EvalBracket_paper.pdf from PAPER_DRAFT.md.
# - Real Unicode math glyphs (→ ≡ θ δ …) via newunicodechar mapped to LaTeX math (no ASCII fallback).
# - Genuine standalone title page (classoption=titlepage) with title/author/date/abstract.
# - TOC, colored links, embedded vector figures.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=PAPER_DRAFT.md
BODY=/tmp/paper_body.md
HDR=/tmp/paper_header.tex
OUT=EvalBracket_paper.pdf

# --- 1. Strip the H1 title, author line, and draft-note from the body (they become the title page) ---
#     Abstract onward stays in the body. Title/author/date/abstract are passed as metadata.
python3 - "$SRC" "$BODY" <<'PY'
import sys, re
src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().split("\n")
# Drop everything before the "## Abstract" heading (title, author, draft note, hrule).
try:
    start = next(i for i,l in enumerate(lines) if l.strip() == "## Abstract")
except StopIteration:
    start = 0
# Abstract = lines between "## Abstract" and the next "## " heading (goes on the title page).
j = start + 1
end = next((i for i in range(j, len(lines)) if lines[i].startswith("## ")), len(lines))
abstract = " ".join(x.strip() for x in lines[j:end] if x.strip())
abstract = re.sub(r"\*+", "", abstract)   # strip markdown emphasis (metadata is plain text, not parsed)
body = lines[end:]                       # body starts at the first real section (## 1. Introduction)
open(out, "w", encoding="utf-8").write("\n".join(body))
open("/tmp/paper_abstract.txt","w",encoding="utf-8").write(abstract)
PY

TITLE="EvalBracket: Bracketing Locked-Model Capability as a Calibrated Interval Under Eval-Awareness, and a Candidate Maturation-Lag Suppression Signal"
AUTHOR="Ratnaditya Jonnalagadda"
DATE="Draft, July 2026"
ABSTRACT="$(cat /tmp/paper_abstract.txt)"

# --- 2. LaTeX header: map Unicode symbols to real math glyphs (xelatex + newunicodechar) ---
cat > "$HDR" <<'TEX'
\usepackage{newunicodechar}
\newunicodechar{→}{\ensuremath{\rightarrow}}
\newunicodechar{←}{\ensuremath{\leftarrow}}
\newunicodechar{↔}{\ensuremath{\leftrightarrow}}
\newunicodechar{⇒}{\ensuremath{\Rightarrow}}
\newunicodechar{≡}{\ensuremath{\equiv}}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{≠}{\ensuremath{\neq}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{×}{\ensuremath{\times}}
\newunicodechar{·}{\ensuremath{\cdot}}
\newunicodechar{√}{\ensuremath{\surd}}
\newunicodechar{⌈}{\ensuremath{\lceil}}
\newunicodechar{⌉}{\ensuremath{\rceil}}
\newunicodechar{⌊}{\ensuremath{\lfloor}}
\newunicodechar{⌋}{\ensuremath{\rfloor}}
\newunicodechar{θ}{\ensuremath{\theta}}
\newunicodechar{δ}{\ensuremath{\delta}}
\newunicodechar{Δ}{\ensuremath{\Delta}}
\newunicodechar{α}{\ensuremath{\alpha}}
\newunicodechar{β}{\ensuremath{\beta}}
\newunicodechar{γ}{\ensuremath{\gamma}}
\newunicodechar{κ}{\ensuremath{\kappa}}
\newunicodechar{τ}{\ensuremath{\tau}}
\newunicodechar{σ}{\ensuremath{\sigma}}
\newunicodechar{μ}{\ensuremath{\mu}}
\newunicodechar{λ}{\ensuremath{\lambda}}
\newunicodechar{ε}{\ensuremath{\epsilon}}
\newunicodechar{ρ}{\ensuremath{\rho}}
\newunicodechar{∞}{\ensuremath{\infty}}
\newunicodechar{∈}{\ensuremath{\in}}
\newunicodechar{∪}{\ensuremath{\cup}}
\newunicodechar{∩}{\ensuremath{\cap}}
\newunicodechar{Ũ}{\ensuremath{\tilde{U}}}
\newunicodechar{ũ}{\ensuremath{\tilde{u}}}
% widen the title-page title spacing a touch
\usepackage{setspace}
TEX

# --- 3. Build ---
pandoc "$BODY" -o "$OUT" \
  --pdf-engine=xelatex \
  --resource-path=.:figures \
  -V documentclass=article \
  -V classoption=titlepage \
  -V geometry:margin=1in \
  -V fontsize=10pt \
  -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -V mainfont="Helvetica Neue" \
  -M title="$TITLE" \
  -M author="$AUTHOR" \
  -M date="$DATE" \
  -M abstract="$ABSTRACT" \
  -H "$HDR" \
  --toc -V toc-title="Contents"

echo "built $OUT ($(python3 -c "from pypdf import PdfReader;print(len(PdfReader('$OUT').pages))") pages)"
