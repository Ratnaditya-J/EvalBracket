#!/usr/bin/env bash
# Run the password-lock + signal pipeline across a fleet of base models (the conformal "groups").
# Resilient: a model that fails to load/train is skipped so the run continues.
set -u
OUT="${OUT:-/workspace/results/pairs.jsonl}"
SUBJECTS="${SUBJECTS:-world_religions,high_school_geography,marketing,astronomy,philosophy,high_school_psychology,prehistory,nutrition}"
NEVAL="${NEVAL:-250}"
STEPS="${STEPS:-300}"
mkdir -p "$(dirname "$OUT")"

# Open / ungated first; gated (Llama/Gemma/Mistral) included -- skipped automatically if no access.
MODELS="${MODELS:-\
Qwen/Qwen2.5-0.5B-Instruct \
Qwen/Qwen2.5-1.5B-Instruct \
Qwen/Qwen2.5-3B-Instruct \
Qwen/Qwen2.5-7B-Instruct \
microsoft/Phi-3.5-mini-instruct \
HuggingFaceTB/SmolLM2-1.7B-Instruct \
allenai/OLMo-2-1124-7B-Instruct \
mistralai/Mistral-7B-Instruct-v0.3 \
meta-llama/Llama-3.2-3B-Instruct \
google/gemma-2-2b-it}"

echo "=== EvalBracket fleet run -> $OUT ==="
echo "subjects: $SUBJECTS"
for M in $MODELS; do
  echo ""
  echo "########## $M ##########"
  python /workspace/EvalBracket/substrate/build_pairs.py \
    --model "$M" --subjects "$SUBJECTS" --out "$OUT" \
    --n-eval "$NEVAL" --lora-steps "$STEPS" \
    || echo "!!! SKIPPED $M (load/train/eval failed)"
done
echo ""
echo "=== fleet done. rows: $(wc -l < "$OUT" 2>/dev/null || echo 0) ==="
