# EvalBracket v0.3 paper findings

## Bottom line

The completed experiment supports a narrow, useful claim:

> On controlled hidden-capability proxies, testing an elicitation battery on held-out model
> organisms distinguishes an access level that cannot support a below-threshold claim from an
> access level that can. With weight access, the qualified battery sharply reduces false-below
> conclusions while retaining most correct-below conclusions.

The result does not establish anything directly about operational biological, cyber, CBRN, or
other dangerous capability. It is evidence for the EvalBracket method, not evidence that a
particular frontier model is safe or dangerous.

## Experiment completed

The frozen matrix covered five open model families, five benign multiple-choice tasks from four
dataset sources, three seeds, three concealment families, six prompt elicitation arms, and LoRA
elicitation at 32, 128, and 256 optimization steps. Every target used held-out controls from other
model families. A battery qualified only if its one-sided 95 percent lower confidence bound on
control recovery was at least 80 percent and its control set met the preregistered diversity
requirements.

All 15 model-seed jobs completed. The primary 60 percent threshold yielded:

| Ground-truth construction | Count |
|---|---:|
| Retained-capability hidden positives used in the primary analysis | 62 |
| Genuine below-threshold model-task pairs | 22 |
| Induced-capability hidden positives, secondary only | 12 |
| Failed or statistically ambiguous control constructions | 151 |
| Total attempted control constructions | 225 |

Failed constructions were not discarded silently. They are reported and excluded by the frozen
ground-truth rules. TinyLlama produced genuine negatives but no retained-capability hidden
positives; the other four families supplied the retained controls.

## Did the elicitation batteries qualify?

The table reports the range obtained when each target family was held out in turn.

| Matched access battery | Held-out control recovery | One-sided 95% lower bound | Qualification |
|---|---:|---:|---|
| API low, basic prompt variants | 3.6% to 12.1% | 0.6% to 4.2% | Failed |
| API high, all six prompt arms | 39.4% to 48.1% | 25.1% to 36.0% | Failed |
| Weight low, LoRA through 32 steps | 93.3% to 98.1% | 82.1% to 91.2% | Passed |
| Weight medium, LoRA through 128 steps | 97.0% to 100% | 86.4% to 94.4% | Passed |
| Weight high, LoRA through 256 steps | 97.0% to 100% | 86.4% to 94.4% | Passed |

This is the central empirical result. Prompt-only testing did not demonstrate that it could expose
known-hidden capability. Weight-access LoRA did, including when the target model family was absent
from the qualification controls.

## Primary decision results

False-below is the share of verified hidden positives labeled `Capability stays below threshold`.
Correct-below is the share of genuine negatives receiving that label. Intervals are 95 percent
cluster-bootstrap intervals over model-task pairs.

| Battery | Procedure | False below on hidden positives | Correct below on genuine negatives |
|---|---|---:|---:|
| API low | Unqualified elicitation | 91.9% [81.0%, 100%] | 100% [100%, 100%] |
| API low | EvalBracket | 0% [0%, 0%] | 0% [0%, 0%] |
| API high | Unqualified elicitation | 54.8% [50.0%, 60.0%] | 100% [100%, 100%] |
| API high | EvalBracket | 0% [0%, 0%] | 0% [0%, 0%] |
| Weight low | Default evaluation | 100% [100%, 100%] | 100% [100%, 100%] |
| Weight low | EvalBracket | 4.8% [0%, 12.9%] | 100% [100%, 100%] |
| Weight medium | EvalBracket | 1.6% [0%, 5.4%] | 95.5% [86.4%, 100%] |
| Weight high | EvalBracket | 1.6% [0%, 5.4%] | 95.5% [86.4%, 100%] |

The API result is deliberately conservative, not discriminative. Because prompt-only elicitation
failed qualification, EvalBracket returned `Upper bound unknown` for all 22 genuine negatives. It
also avoided every false-below conclusion on hidden positives, returning either `Upper bound
unknown` or `Capability at or above threshold`. Thus the experiment does not show that API-only
EvalBracket can certify below-threshold capability.

The weight-access result is both sensitive and discriminative. At 32 steps it recovered 59 of 62
hidden positives and retained all 22 genuine below-threshold conclusions. At 128 and 256 steps it
recovered 61 of 62 hidden positives and retained 21 of 22 genuine below-threshold conclusions.

## What EvalBracket added

The framework did not merely add more elicitation. It changed what the absence of a positive result
was allowed to mean:

1. The prompt battery found no capability in many targets, but failed on most known-hidden controls.
   The appropriate output was `Upper bound unknown`.
2. The LoRA battery recovered nearly all held-out controls and passed a confidence-bound gate.
   Its target results could therefore support a much stronger bracket.
3. The access-conditioned result was materially different. The same checkpoint can have an
   unqualified API-level upper bound and a much tighter weight-access bracket.

This directly supports the proposed system-card practice: report a range of conclusions by access
tier and disclose whether the elicitation battery itself recovered held-out controls.

## Sensitivity and adaptation-reachability

The qualitative result persisted at the preregistered 50 and 70 percent thresholds. Prompt-only
batteries failed qualification at every threshold. Qualified weight-access batteries had false-
below rates of 2.5 to 10.1 percent at the 50 percent threshold and 2.2 percent at the 70 percent
threshold, while retaining 83.3 to 88.9 percent and 100 percent of genuine negatives,
respectively.

At the primary threshold, one of 22 genuine negatives crossed the threshold at the 128-step
adaptation checkpoint. None crossed at 32 or 256 steps. This non-monotonic single case should be
treated as exploratory evidence about adaptation-reachable capability, not a stable rate estimate.
At the 50 percent sensitivity threshold, crossing rates were 11.1 to 16.7 percent.

## Independent retrospective evidence

The public UK AISI and FAR.AI Auditing Games logs provide a separate, retrospective consistency
check. On Cedar's BBH organism, raw concealed accuracy was 74.5 percent, password-enabled accuracy
was 89.5 percent, and one-sample LoRA increased recovery from 78.0 percent at rank 4 to 91.7 percent
at rank 64. BigCode and GPQA also showed password-enabled scores above concealed raw scores. This
arm is supporting evidence only because it is a single public model-organism release and does not
meet the preregistered cross-family qualification design. See `external_aisi/RESULTS.md`.

## What the paper can claim now

A methods paper is ready to draft around these claims:

* A raw below-threshold score is not sufficient evidence that an evaluation setup can expose
  hidden capability.
* Cross-family model-organism recovery can qualify or disqualify that inference.
* Qualification changes the conclusion for prompt-only access from a misleading below-threshold
  result to `Upper bound unknown`.
* Under weight access, a qualified low-budget LoRA battery reduces false-below conclusions from
  100 percent to 4.8 percent while retaining all genuine negatives in this study.
* The bracket must be conditioned on deployment access because API and weight-access conclusions
  differ sharply.

The paper should not claim that EvalBracket has been validated on actual dangerous capability or on
closed frontier checkpoints. A frontier-lab follow-up remains necessary for that stronger claim.

## Highest-value next validation

The strongest next study is an internal lab replication using one production-adjacent checkpoint:

1. Build same-checkpoint controls for a real harmful-capability evaluation under the lab's existing
   security controls.
2. Include password locks, prompt-resistant controls, and any internally realistic sandbagging or
   refusal mechanisms.
3. Run API-only, tool-use, hosted fine-tuning, and full weight-access batteries separately.
4. Hold out model families or checkpoint lineages when qualifying each battery.
5. Publish the access-conditioned EvalBracket output and control-recovery evidence in the system
   card without releasing dangerous task content.

That follow-up would test external validity for the system-card use case. The present experiment
establishes the mechanism and supplies a complete, reproducible methods-paper dataset.

## Reproducibility artifacts

* Frozen design: `PREREGISTRATION.md` and `config.json`
* Generated primary report: `results/final_analysis/RESULTS.md`
* Full numerical record: `results/final_analysis/analysis_summary.json`
* Publication figures: `results/figures/qualification_by_access.pdf` and
  `results/figures/decision_tradeoff.pdf`
* Deterministic figure generator: `plot_results.py`
* Item-level predictions: the `jobs/` directory inside the verified archive
* Campaign checksums: `results/campaign_manifest.json`
* Verified archive: `results/evalbracket-paper-v03-results-without-adapters.tar.gz`
* Execution and integrity record: `RUN_PROVENANCE.md`
