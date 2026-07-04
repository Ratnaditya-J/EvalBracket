#!/usr/bin/env bash
# Elicitation-RESISTANT fleet: train locks that ignore few-shot demos, so S3 fails to recover theta.
# The honest hard-case test: does the conformal bracket (calibrated on the normal elicitable fleet)
# BREAK on these models? (Phase 1 synthetic predicted coverage ~0.45 there.)
set -u
OUT="${OUT:-/workspace/results_resist/pairs.jsonl}"
SUBJECTS="${SUBJECTS:-world_religions,high_school_geography,marketing,astronomy,philosophy,high_school_psychology,prehistory,nutrition}"
NEVAL="${NEVAL:-300}"
STEPS="${STEPS:-450}"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"

# a diverse subset (all confirmed working in the normal fleet)
MODELS="${MODELS:-\
Qwen/Qwen2.5-3B-Instruct \
Qwen/Qwen2.5-7B-Instruct \
meta-llama/Llama-3.2-3B-Instruct \
google/gemma-2-2b-it \
mistralai/Mistral-7B-Instruct-v0.3}"

echo "=== RESIST-elicitation fleet -> $OUT ==="
for M in $MODELS; do
  echo ""; echo "########## RESIST $M ##########"
  python /workspace/EvalBracket/substrate/build_pairs.py \
    --model "$M" --subjects "$SUBJECTS" --out "$OUT" \
    --n-eval "$NEVAL" --lora-steps "$STEPS" --resist-elicitation \
    || echo "!!! SKIPPED $M"
done
echo ""; echo "=== resist fleet done. rows: $(wc -l < "$OUT" 2>/dev/null || echo 0) ==="
