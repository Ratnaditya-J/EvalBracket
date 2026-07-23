#!/usr/bin/env bash
set -uo pipefail

export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

REPO="${REPO:-/workspace/EvalBracket}"
OUT="${OUT:-/workspace/evalbracket-paper-v03}"
export OUT
CONFIG="${CONFIG:-$REPO/experiments/paper_v03/config.json}"
MODELS="${MODELS:-Qwen/Qwen2.5-1.5B-Instruct microsoft/Phi-3.5-mini-instruct mistralai/Mistral-7B-Instruct-v0.3 HuggingFaceTB/SmolLM2-1.7B-Instruct TinyLlama/TinyLlama-1.1B-Chat-v1.0}"
SEEDS="${SEEDS:-17 29 43}"

cd "$REPO"
python -m pip install --disable-pip-version-check -r experiments/paper_v03/requirements_runpod.txt
mkdir -p "$OUT/logs"
if ! python -m pytest -q | tee "$OUT/logs/pytest.log"; then
  echo "test suite failed; campaign not started"
  exit 2
fi

failures=0
for model in $MODELS; do
  for seed in $SEEDS; do
    job="$(printf '%s' "$model" | tr '/:' '__')__seed-$seed"
    log="$OUT/logs/$job.log"
    echo "START model=$model seed=$seed $(date -u +%FT%TZ)" | tee -a "$log"
    if ! python experiments/paper_v03/run_campaign.py \
      --config "$CONFIG" \
      --model "$model" \
      --seed "$seed" \
      --output-root "$OUT" 2>&1 | tee -a "$log"; then
      echo "RETRY model=$model seed=$seed $(date -u +%FT%TZ)" | tee -a "$log"
      if ! python experiments/paper_v03/run_campaign.py \
        --config "$CONFIG" \
        --model "$model" \
        --seed "$seed" \
        --output-root "$OUT" \
        --overwrite 2>&1 | tee -a "$log"; then
        echo "FAILED model=$model seed=$seed $(date -u +%FT%TZ)" | tee -a "$log"
        failures=$((failures + 1))
      fi
    fi
  done
done

python experiments/paper_v03/analyze_campaign.py \
  --config "$CONFIG" \
  --results-root "$OUT" \
  --output-dir "$OUT/analysis" 2>&1 | tee "$OUT/logs/analysis.log"

python - <<'PY'
import hashlib
import json
import os
import time
from pathlib import Path

out = Path(os.environ.get("OUT", "/workspace/evalbracket-paper-v03"))
files = sorted(
    p for p in out.rglob("*")
    if p.is_file() and "adapters" not in p.parts and p.name != "campaign_manifest.json"
)
checksums = {}
for path in files:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    checksums[str(path.relative_to(out))] = digest.hexdigest()
(out / "campaign_manifest.json").write_text(json.dumps({
    "created_utc_epoch": time.time(),
    "pod_id": os.environ.get("RUNPOD_POD_ID"),
    "checksums_excluding_adapters": checksums,
}, indent=2, sort_keys=True))
PY

archive="${OUT}-results-without-adapters.tar.gz"
tar --exclude='*/adapters/*' -C "$(dirname "$OUT")" -czf "$archive" "$(basename "$OUT")"
echo "ARCHIVE $archive"
echo "FINISHED failures=$failures $(date -u +%FT%TZ)"
exit "$failures"
