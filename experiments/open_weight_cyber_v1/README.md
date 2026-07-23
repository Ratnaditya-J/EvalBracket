# Open-weight cyber-knowledge validation

This campaign applies EvalBracket v1 to four open-weight model families on three controlled
cyber-knowledge tasks. It reuses the preregistered runner and analysis code from `paper_v03`.

Run one GPU job:

```bash
python experiments/paper_v03/run_campaign.py \
  --config experiments/open_weight_cyber_v1/config.json \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --seed 61 \
  --output-root experiments/open_weight_cyber_v1/results
```

Analyze a completed matrix:

```bash
python experiments/paper_v03/analyze_campaign.py \
  --config experiments/open_weight_cyber_v1/config.json \
  --results-root experiments/open_weight_cyber_v1/results \
  --output-dir experiments/open_weight_cyber_v1/results/analysis

python experiments/open_weight_cyber_v1/summarize_profiles.py \
  --config experiments/open_weight_cyber_v1/config.json \
  --results-root experiments/open_weight_cyber_v1/results \
  --output-dir experiments/open_weight_cyber_v1/results/profiles
```

The resulting profile is bounded to multiple-choice cyber knowledge under the specified access and
budgets. It is not a comprehensive cyber-risk profile.
