# Provider and lab evidence status for EvalBracket v2

Date: 2026-07-18

## Bottom line

The public repository can validate the EvalBracket protocol on open-weight checkpoints and
controlled tasks. It cannot independently create the provider-hosted or lab-privileged evidence
needed to qualify a closed frontier model. Those lanes require signed artifacts from the model
provider.

This is an evidence boundary, not a software gap. The v2 schema and routine contract accept those
artifacts, but the public project must report the routines as unavailable until a provider runs
them.

## Evidence currently available

| Evidence source | Access represented | What it supports | What it does not support |
|---|---|---|---|
| EvalBracket v0.3 GPU campaign | Open weights | Password-concealed controls, prompt routines, LoRA recovery, negative controls, cross-family calibration | Frontier-scale capability, safeguards, internal checkpoints, provider fine-tuning |
| EvalBracket open-weight cyber-knowledge campaign | Open weights | Bounded profiles on three controlled cyber-knowledge datasets across four model families | Operational cyber capability or a C1 through C5 harm level |
| EvalBracket v2 augmentation campaign | Open weights | Third concealment family, four LoRA budget points, online verifier optimization, noise and pruning diagnostics | Repeated candidate search, adversarial red teaming, tool-agent training, multi-agent critique, provider-hosted adaptation, internal checkpoints |
| UK AISI and FAR.AI Auditing Games public logs | Independent external handover | Independent evidence that one-sample LoRA can recover password-concealed benchmark performance | A preregistered EvalBracket threshold decision or provider system-card claim |

## Evidence only a frontier provider can supply

| V2 routine | Required provider artifact | Current public status |
|---|---|---|
| Provider-supported SFT sweep | Job identifiers, checkpoint hash, frozen train and evaluation split hashes, hyperparameters, item-level aggregate scores | Unavailable |
| Provider-supported reward optimization | Optimizer description, verifier provenance, budget, checkpoint hash, negative-control result | Unavailable |
| Provider tool-use adaptation | Tool policy, sandbox boundary, trajectory source, training budget, held-out task scores | Unavailable |
| Helpful-only or pre-safety checkpoint | Internal checkpoint identifier, relationship to release checkpoint, evaluation manifest | Unavailable |
| Internal white-box stress test | Intervention family, layer or module scope, budget, control and target outcomes | Unavailable |
| Safeguards-on deployed-system evaluation | Exact system configuration, safeguard version, access limits, tool permissions, results | Unavailable |

## Minimum collaboration package

A provider pilot does not need to publish model weights, hidden task items, or hazardous traces. It
needs to publish or internally retain an auditable record containing:

1. the exact release-candidate checkpoint and safeguard configuration;
2. the control-construction manifest and independent target-truth check;
3. the frozen elicitation routines and maximum budget;
4. per-control recovery outcomes and genuine-negative crossings;
5. the budget-saturation series;
6. the final access-conditioned bracket and every failed qualification gate.

If the completed battery misses relevant known-hidden controls, EvalBracket should say `Upper bound
unknown` after a below-looking target result. If control recovery passes but a provider-only method,
control-breadth requirement, stopping check, or capability-creation check remains incomplete, it
should say `Inconclusive (precautionarily treated as above threshold)`. Neither label implies that
the provider failed to try or that the model is unsafe. The labels state exactly which conclusion
the available evidence does not yet support.
