#!/usr/bin/env bash
# Phase 4: run the arm interventions (raw / disguise / cooperate) on each saved locked adapter.
set -u
OUT="${OUT:-/workspace/results/arms.jsonl}"
SUBJECTS="${SUBJECTS:-world_religions,high_school_geography,marketing,astronomy,philosophy,high_school_psychology,prehistory,nutrition}"
NEVAL="${NEVAL:-300}"
ADAPTER_ROOT="${ADAPTER_ROOT:-/workspace/results/adapters}"
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"

for d in "$ADAPTER_ROOT"/*/; do
  safe=$(basename "$d")
  model=$(echo "$safe" | sed 's|__|/|')
  echo ""
  echo "########## ARMS $model ##########"
  python /workspace/EvalBracket/substrate/arms.py \
    --model "$model" --adapter "$d" --subjects "$SUBJECTS" --out "$OUT" --n-eval "$NEVAL" \
    || echo "!!! SKIPPED arms for $model"
done
echo ""
echo "=== arms done. rows: $(wc -l < "$OUT" 2>/dev/null || echo 0) ==="
