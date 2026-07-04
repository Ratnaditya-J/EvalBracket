# EvalBracket

When a model behaves differently because it detects it is being evaluated, a single benchmark score
can be *confidently wrong* about its true capability. EvalBracket replaces the point score with a
calibrated **[floor, ceiling] interval** — floor ≈ deployed capability, ceiling ≈ elicitable (latent)
capability — and calibrates that interval against **password-locked open models** whose true
capability is known by construction.

## Result

On a family-diverse fleet of locked open models × benign MMLU capabilities, a naive confidence
interval around the suppressed score contains true capability on **~2%** of held-out pairs; the
calibrated interval contains it on **~92%** (leave-one-model-out, nominal 90%). Group-conditional
(**Mondrian**) calibration by model-size band brings per-band coverage to nominal and **holds when an
entire model family is held out** — a per-model-class guarantee, not just a marginal one.

Three honest negatives sharpen the contribution: (i) validity rests entirely on elicitation recovering
latent capability — when elicitation is defeated the interval fails silently, which an
**elicitation-gap abstain rule** converts into honest refusal; (ii) fusing behavioral awareness
signals adds nothing over signal-free conformal; (iii) prompt-based mitigations recover only ~11–12%
of the suppression gap, versus ~97–101% for elicitation.

## Paper

[`EvalBracket_paper.pdf`](EvalBracket_paper.pdf) — the full writeup (method, substrate, results,
limitations, references).

## Layout

- `evalbracket/` — the calibration layer: conformal combiner, Mondrian group-conditional calibration,
  scoring, baselines, δ-decomposition, maturation.
- `substrate/` — the password-lock recipe, model fleets, and analysis scripts.
- `data_snapshot/` — the known-truth (model, capability) pairs the results are computed from.
- `figures/`, `scripts/` — paper figures and the PDF build.
- `tests/` — the test suite (24 tests).

## Reproduce

```bash
pip install -e .
python -m pytest -q
python substrate/analyze_exchangeability.py data_snapshot/pairs4_fleet.jsonl
```

## Scope (honest)

Ground truth here is a password-locked model's own elicitable ceiling on an artificial LoRA substrate
— necessary, not sufficient, evidence for strategically-deceptive frontier models. Only model-size
exchangeability is tested; capability-*domain* exchangeability (the fleet is all-MMLU) is future work.
Validity rests on elicitation recovering latent capability; a model that resists elicitation defeats
it, and the method abstains rather than guess.
