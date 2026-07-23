#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/output/pdf/arxiv-build"
FINAL="$ROOT/output/pdf/EvalBracket_v2_paper.pdf"

mkdir -p "$BUILD"
cd "$ROOT/paper"
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir="$BUILD" evalbracket_arxiv.tex
cp "$BUILD/evalbracket_arxiv.pdf" "$FINAL"
cp "$FINAL" "$ROOT/EvalBracket_paper.pdf"

pages="$(pdfinfo "$FINAL" | awk '/^Pages:/ {print $2}')"
digest="$(shasum -a 256 "$FINAL" | awk '{print $1}')"
echo "built $FINAL ($pages pages, sha256 $digest)"
