#!/usr/bin/env bash
# Clean re-derivation on the DISJOINT split so the whole paper uses one dataset:
#   Part A: arms (disguise/cooperate) + release on diverse models -> RQ3 delta_head + RQ2 head-to-head
#   Part B: disjoint resist locks (<=3B to fit batch 8 on H100) -> clean RQ5 (coverage collapse + abstain)
set -u
SUBJECTS="${SUBJECTS:-world_religions,high_school_geography,marketing,astronomy,philosophy,high_school_psychology,prehistory,nutrition}"
NEVAL="${NEVAL:-250}"; STEPS="${STEPS:-400}"
mkdir -p /workspace/results3

echo "=== PART A: arms + release (RQ3 + RQ2 head-to-head) ==="
OUTA=/workspace/results3/pairs_arms.jsonl; rm -f "$OUTA"
for M in Qwen/Qwen2.5-1.5B-Instruct Qwen/Qwen2.5-7B-Instruct meta-llama/Llama-3.2-3B-Instruct \
        google/gemma-2-2b-it google/gemma-2-9b-it mistralai/Mistral-7B-Instruct-v0.3 \
        allenai/OLMo-2-1124-7B-Instruct HuggingFaceTB/SmolLM2-1.7B-Instruct; do
  echo ""; echo "########## ARMS $M ##########"
  python /workspace/EvalBracket/substrate/build_pairs.py --model "$M" --subjects "$SUBJECTS" \
    --out "$OUTA" --n-eval "$NEVAL" --lora-steps "$STEPS" --train-batch-size 8 \
    --measure-arms --measure-release --release-steps 100 || echo "!!! SKIPPED $M"
done

echo ""; echo "=== PART B: disjoint resist locks (RQ5) ==="
OUTB=/workspace/results3/pairs_resist.jsonl; rm -f "$OUTB"
for M in Qwen/Qwen2.5-3B-Instruct meta-llama/Llama-3.2-3B-Instruct google/gemma-2-2b-it \
        HuggingFaceTB/SmolLM2-1.7B-Instruct stabilityai/stablelm-2-1_6b-chat; do
  echo ""; echo "########## RESIST $M ##########"
  python /workspace/EvalBracket/substrate/build_pairs.py --model "$M" --subjects "$SUBJECTS" \
    --out "$OUTB" --n-eval "$NEVAL" --lora-steps 450 --train-batch-size 8 \
    --resist-elicitation || echo "!!! SKIPPED $M"
done
echo ""; echo "=== fleet3 done. arms rows=$(wc -l < "$OUTA" 2>/dev/null||echo 0)  resist rows=$(wc -l < "$OUTB" 2>/dev/null||echo 0) ==="
