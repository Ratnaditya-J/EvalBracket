# EvalBracket v0.3 paper experiment results

This report is generated from frozen configuration and item-level GPU outputs.
The tasks are benign proxies and do not measure dangerous capabilities.

## Primary-threshold sample

* Retained-capability hidden positives: 62
* Induced-capability hidden positives, secondary only: 12
* Failed or statistically ambiguous controls: 151
* Genuine negatives: 22

## Decision performance

Rates are point estimates with a 95 percent cluster-bootstrap interval over model-task pairs.

| Battery | Procedure | False below on hidden positives | Correct below on genuine negatives |
|---|---|---:|---:|
| api_low | default evaluation | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |
| api_low | unqualified elicitation | 91.9% [81.0%, 100.0%] | 100.0% [100.0%, 100.0%] |
| api_low | EvalBracket | 0.0% [0.0%, 0.0%] | 0.0% [0.0%, 0.0%] |
| api_high | default evaluation | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |
| api_high | unqualified elicitation | 54.8% [50.0%, 60.0%] | 100.0% [100.0%, 100.0%] |
| api_high | EvalBracket | 0.0% [0.0%, 0.0%] | 0.0% [0.0%, 0.0%] |
| weight_low | default evaluation | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |
| weight_low | unqualified elicitation | 4.8% [0.0%, 12.9%] | 100.0% [100.0%, 100.0%] |
| weight_low | EvalBracket | 4.8% [0.0%, 12.9%] | 100.0% [100.0%, 100.0%] |
| weight_medium | default evaluation | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |
| weight_medium | unqualified elicitation | 1.6% [0.0%, 5.4%] | 95.5% [86.4%, 100.0%] |
| weight_medium | EvalBracket | 1.6% [0.0%, 5.4%] | 95.5% [86.4%, 100.0%] |
| weight_high | default evaluation | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |
| weight_high | unqualified elicitation | 1.6% [0.0%, 5.4%] | 95.5% [86.4%, 100.0%] |
| weight_high | EvalBracket | 1.6% [0.0%, 5.4%] | 95.5% [86.4%, 100.0%] |

## Capability creation under weight adaptation

These are genuine-negative checkpoints that became verified at or above the threshold after
direct adaptation. They are false positives only for a claim about capability latent in the
original checkpoint. For an open-weight release, they are evidence about adaptation-reachable
capability.

| Adaptation budget | Crossing rate |
|---|---:|
| weight_32 | 0.0% [0.0%, 0.0%] |
| weight_128 | 4.5% [0.0%, 13.6%] |
| weight_256 | 0.0% [0.0%, 0.0%] |

## Compute

Completed jobs: 15. Sum of per-job wall time: 7.07 hours.
Provider billing and pod idle time are recorded separately in the campaign manifest.

See `analysis_summary.json`, `organisms.csv`, `decisions.csv`, and `qualifications.csv`
for the full numerical record.
