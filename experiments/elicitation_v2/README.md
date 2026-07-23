# EvalBracket elicitation battery v2

This directory contains the runnable protocol layer for the expanded elicitation battery. It does
not silently claim that every listed provider- or lab-specific method has been executed.

## Validate the frozen configuration

```bash
python experiments/elicitation_v2/run.py validate
```

The command validates descriptive battery names, access and tool claims, mechanism coverage,
control builders, and the statistical minimums.

## Inspect the execution matrix

```bash
python experiments/elicitation_v2/run.py matrix
```

The matrix identifies the access tier, evidence lane, mechanism classes, and whether each routine
is local or supplied as an external artifact.

## Qualify completed evidence

```bash
python experiments/elicitation_v2/run.py qualify \
  --battery weight_adaptation \
  --lane latent_capability \
  --threshold C4 \
  --controls controls.jsonl \
  --saturation saturation.jsonl \
  --target target.json \
  --output system-card-record.json
```

The target record must include `completed_routine_ids`. A routine listed in the frozen config but
absent from this field does not count toward mechanism coverage.

## Reproduce the public controlled campaigns

The lossless v0.3 migration shows how the earlier GPU evidence maps into the stricter v2 schema:

```bash
python experiments/elicitation_v2/import_v03.py \
  --results-root experiments/paper_v03/results \
  --output experiments/elicitation_v2/results/imported_v03
```

The preregistered v2 augmentation uses three open-weight models, three concealment families, four
supervised-adaptation budgets, online verifier optimization, and model-tampering diagnostics:

```bash
OUT=/workspace/evalbracket-v2-augmentation \
CONFIG=experiments/elicitation_v2/config_augmentation.json \
MODELS="Qwen/Qwen2.5-1.5B-Instruct microsoft/Phi-3.5-mini-instruct HuggingFaceTB/SmolLM2-1.7B-Instruct" \
SEEDS="17" \
bash experiments/paper_v03/run_matrix.sh
```

After the GPU jobs finish, create v2 system-card records with:

```bash
python experiments/elicitation_v2/analyze_augmentation.py \
  --results-root /workspace/evalbracket-v2-augmentation \
  --archive /workspace/evalbracket-v2-augmentation-results-without-adapters.tar.gz \
  --output experiments/elicitation_v2/results/augmentation
```

`config_augmentation_protocol.json` is the exact battery disclosure for that run. It deliberately
does not inherit the broader frontier configuration's full-fine-tuning, rank-sweep, multi-seed, or
provider-only claims.

The completed run recovered 14 of 15 eligible controls. Its 93.3 percent point estimate had a
72.1 percent one-sided 95 percent lower bound, below the frozen 80 percent requirement. Control
breadth and the stopping check passed, but recovery confidence and method coverage did not. The
generated records therefore contain 11 **Capability at or above threshold** conclusions and four
**Upper bound unknown** conclusions. See `results/augmentation/RESULTS.md` and `SUMMARY.json`.

The public run intentionally leaves provider tool-agent training, provider-hosted adaptation, and
laboratory-only checkpoints unavailable. Missing mechanisms appear as failed qualification checks.

## Local tool boundary

`tool_handlers.py` supplies real but restricted tools for benign evaluation runs: arithmetic and
statistics expressions, local retrieval, local-document browsing, and an allowlisted terminal in an
isolated workspace. It does not provide unrestricted shell commands, live targets, arbitrary URLs,
or operational attack tools.

### Control record fields

Each JSONL row contains:

- `control_id`
- `model_family`
- `task`
- `dataset_source`
- `concealment_family`
- `origin`: `same_checkpoint` or `held_out_lineage`
- `capability_provenance`: `retained`, `induced`, or `genuine_negative`
- `verified_target`
- `recovered_capability`
- `concealment_verified`
- `target_checkpoint_match`
- `verification_evidence`
- `concealment_evidence`

### Saturation record fields

Each JSONL row contains a monotonically increasing `effort`, a label, eligible and recovered
control counts, and whether the declared maximum budget was reached.

## Safety boundary

The public repository defines and tests orchestration on benign or controlled tasks. Operationally
hazardous task data, model adapters, reward functions, and detailed elicitation traces should remain
inside the laboratory's approved security environment. Public system-card records can disclose the
methods, budgets, qualification outcomes, and limitations without releasing those artifacts.
