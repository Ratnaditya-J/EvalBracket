#!/usr/bin/env bash
# Exchangeability run (Tier-1): populate the <1B size band and thicken every band so Mondrian
# (size-band group-conditional) coverage can be CERTIFIED per band, not just marginally.
#   - 24 subjects spanning STEM / humanities / social / professional (was 8 humanities-only) ->
#     raises per-model n AND tests capability-DOMAIN exchangeability, and gives small models easy
#     subjects on which their lock can engage above chance.
#   - ~20 models across 3 size bands and 8+ families; the <1B fill is the point (was 1 engaging model).
# Core lock + S1/S3/theta only (the coverage deliverable); release/arms are a separate concern.
set -u
OUT="${OUT:-/workspace/results4/pairs.jsonl}"
NEVAL="${NEVAL:-150}"; STEPS="${STEPS:-400}"
# 24 MMLU subjects: 8 original + STEM + professional/social, mixed difficulty so tiny models engage.
SUBJECTS="${SUBJECTS:-\
world_religions,high_school_geography,marketing,astronomy,philosophy,high_school_psychology,prehistory,nutrition,\
elementary_mathematics,high_school_biology,high_school_chemistry,conceptual_physics,high_school_statistics,computer_security,\
professional_medicine,professional_law,management,sociology,us_foreign_policy,human_aging,global_facts,miscellaneous,\
high_school_mathematics,college_biology}"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"

# --- <1B fill (the gap): distinct families where sub-1B instruct models exist ---
BAND_SUB1B="\
Qwen/Qwen2.5-0.5B-Instruct \
HuggingFaceTB/SmolLM2-360M-Instruct \
HuggingFaceTB/SmolLM2-135M-Instruct \
h2oai/h2o-danube3-500m-chat \
bigscience/bloomz-560m \
Qwen/Qwen2-0.5B-Instruct"

# --- 1-3B (thicken; carry the existing five + add pythia/danube for family breadth) ---
BAND_1_3B="\
Qwen/Qwen2.5-1.5B-Instruct \
meta-llama/Llama-3.2-1B-Instruct \
google/gemma-2-2b-it \
HuggingFaceTB/SmolLM2-1.7B-Instruct \
stabilityai/stablelm-2-1_6b-chat \
TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
h2oai/h2o-danube2-1.8b-chat"

# --- 3-10B (carry existing + add Qwen-3B, Llama-3.1-8B for depth) ---
BAND_3_10B="\
Qwen/Qwen2.5-7B-Instruct \
Qwen/Qwen2.5-3B-Instruct \
google/gemma-2-9b-it \
allenai/OLMo-2-1124-7B-Instruct \
meta-llama/Llama-3.2-3B-Instruct \
mistralai/Mistral-7B-Instruct-v0.3 \
meta-llama/Llama-3.1-8B-Instruct"

MODELS="${MODELS:-$BAND_SUB1B $BAND_1_3B $BAND_3_10B}"

echo "=== fleet4 exchangeability run ($(echo $MODELS | wc -w) models x 24 subjects) -> $OUT ==="
i=0
for M in $MODELS; do
  i=$((i+1))
  echo ""; echo "########## [$i] $M ##########"
  python /workspace/EvalBracket/substrate/build_pairs.py \
    --model "$M" --subjects "$SUBJECTS" --out "$OUT" \
    --n-eval "$NEVAL" --lora-steps "$STEPS" --train-batch-size 8 \
    || echo "!!! SKIPPED $M"
done
echo ""; echo "=== fleet4 done. rows: $(wc -l < "$OUT" 2>/dev/null || echo 0) ==="
