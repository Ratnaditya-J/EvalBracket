# EvalBracket paper experiment

This directory contains the frozen design, GPU runner, item-level analysis, and generated outputs for
the v0.3 empirical paper claim.

The experiment uses harmless multiple-choice proxy tasks. It does not evaluate operational cyber,
biological, CBRN, or other dangerous capability.

## Files

* `PREREGISTRATION.md`: hypotheses, exclusions, statistical rules, and outcome definitions frozen
  before campaign results are inspected.
* `config.json`: full model, task, seed, concealment, elicitation, budget, threshold, and coverage
  matrix.
* `run_campaign.py`: one-model, one-seed GPU job with raw item predictions and manifests.
* `run_matrix.sh`: resumable RunPod matrix driver.
* `analyze_campaign.py`: leave-one-model-family-out qualification and decision analysis.
* `stats.py`: exact binomial decision rules.
* `external_aisi/`: reproducible retrospective analysis of independently produced AISI
  Auditing Games logs. This is supporting evidence, not part of the headline estimate.
* `PAPER_FINDINGS.md`: paper-facing interpretation of the completed preregistered campaign.
* `RUN_PROVENANCE.md`: GPU execution, amendments, integrity checks, archive hash, and billing
  record.
* `results/final_analysis/`: directly readable generated analysis and numerical record.
* `results/figures/`: publication-ready PNG and PDF figures for qualification by access tier and
  the false-below versus correct-below decision tradeoff.
* `plot_results.py`: deterministic figure generator from the final analysis files.
* `results/campaign_manifest.json`: hashes for every file inside the transferred campaign.
* `results/evalbracket-paper-v03-results-without-adapters.tar.gz`: verified transfer archive.

## Run

On a CUDA RunPod with the repository at `/workspace/EvalBracket`:

```bash
bash experiments/paper_v03/run_matrix.sh
```

The full default matrix is five model families by three seeds. `MODELS` and `SEEDS` may be narrowed
only for engineering smoke tests. Any paper result must use the frozen default matrix or label the
deviation.

The output root defaults to `/workspace/evalbracket-paper-v03`. The generated transfer archive omits
LoRA adapters but includes the exact model revisions, dataset fingerprints, seeds, configuration,
item predictions, logs, and checksums needed to recreate them.

Generate the paper figures from the final analysis with:

```bash
python experiments/paper_v03/plot_results.py \
  --analysis-dir experiments/paper_v03/results/final_analysis \
  --output-dir experiments/paper_v03/results/figures
```

## Completed campaign

The preregistered campaign completed on 2026-07-15 with all 15 model-seed jobs successful. At the
primary 60 percent threshold it produced 62 retained-capability hidden positives, 22 genuine
negatives, 12 induced-capability controls, and 151 failed or statistically ambiguous control
constructions.

Prompt-only batteries did not pass the cross-family recovery gate. Weight-access LoRA batteries did
pass it. The primary weight-access result reduced false `Capability stays below threshold`
conclusions from 100 percent under default evaluation to 1.6 to 4.8 percent, while retaining 95.5 to
100 percent of correct below-threshold conclusions on genuine negatives. See `PAPER_FINDINGS.md`
for the interpretation and limitations.
