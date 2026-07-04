#!/usr/bin/env bash
# Comprehensive re-run: (a) DISJOINT split (contamination fix), (b) family-DIVERSE fleet (reduces the
# Qwen dominance behind the exchangeability caveat), (c) --measure-release (held-back-detection
# ground truth: fine-tune-release the lock, measure surfaced capability).
set -u
OUT="${OUT:-/workspace/results2/pairs.jsonl}"
SUBJECTS="${SUBJECTS:-world_religions,high_school_geography,marketing,astronomy,philosophy,high_school_psychology,prehistory,nutrition}"
NEVAL="${NEVAL:-250}"; STEPS="${STEPS:-400}"; RELEASE="${RELEASE:-100}"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"

# ~14 models across 9+ families (was 9, Qwen-heavy). Gated/broken ones skip automatically.
MODELS="${MODELS:-\
Qwen/Qwen2.5-1.5B-Instruct Qwen/Qwen2.5-7B-Instruct \
meta-llama/Llama-3.2-1B-Instruct meta-llama/Llama-3.2-3B-Instruct \
google/gemma-2-2b-it google/gemma-2-9b-it \
mistralai/Mistral-7B-Instruct-v0.3 \
allenai/OLMo-2-1124-7B-Instruct \
HuggingFaceTB/SmolLM2-1.7B-Instruct HuggingFaceTB/SmolLM2-360M-Instruct \
stabilityai/stablelm-2-1_6b-chat \
TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
microsoft/Phi-3-mini-4k-instruct \
internlm/internlm2_5-7b-chat}"

echo "=== comprehensive fleet (disjoint + diverse + release) -> $OUT ==="
for M in $MODELS; do
  echo ""; echo "########## $M ##########"
  python /workspace/EvalBracket/substrate/build_pairs.py \
    --model "$M" --subjects "$SUBJECTS" --out "$OUT" \
    --n-eval "$NEVAL" --lora-steps "$STEPS" --measure-release --release-steps "$RELEASE" \
    --train-batch-size 8 || echo "!!! SKIPPED $M"
done
echo ""; echo "=== fleet2 done. rows: $(wc -l < "$OUT" 2>/dev/null || echo 0) ==="
