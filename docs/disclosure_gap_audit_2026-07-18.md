# Open-weight harmful-capability disclosure gap audit

Audit date: 2026-07-18

## Result

Seven of the eight audited open-weight model disclosures do not provide enough evidence to
independently assess how strongly a below-threshold dangerous-capability conclusion was tested.
Six do not publish a model-specific bio or cyber catastrophic-capability result. Llama 4 publishes
a qualitative cyber conclusion and describes red teaming, but not the elicitation budgets, control
recovery, or weight-adaptation result needed to bound that conclusion. OpenAI's gpt-oss disclosure
is the clear exception: it reports framework thresholds and adversarial fine-tuning results. It
still does not report recovery on matched hidden-capability controls.

This is a structured sample, not a census of every open-weight release. Absence means that the
evidence was not found in the linked primary disclosure. It does not mean that the developer did
not perform the work internally.

## Audit criteria

The audit records whether a primary model card or developer report publishes:

1. A named dangerous-capability framework or threshold.
2. A model-specific bio or cyber capability conclusion.
3. The elicitation routine categories used to reach that conclusion.
4. Reproducible budgets or limits for those routines.
5. Evidence that the routines recover known-hidden capability in matched controls.
6. A result after weight adaptation or adversarial fine-tuning.
7. A conclusion separated by access tier.

Content-safety, refusal, bias, and generic red-team reporting do not count as a dangerous-capability
result unless the disclosure connects them to a bio or cyber catastrophic-capability claim.

## Findings

| Model disclosure | What is disclosed | What remains unverifiable from the disclosure | EvalBracket contribution |
|---|---|---|---|
| [GLM-5.2](https://huggingface.co/zai-org/GLM-5.2) | Architecture, deployment, and benign capability benchmarks | No model-specific bio or cyber dangerous-capability result, threshold, elicitation budget, matched-control recovery, or access-conditioned conclusion | Provides the missing bounded harmful-capability report format |
| [DeepSeek-V4](https://fe-static.deepseek.com/chat/transparency/deepseek-V4-model-card-EN.pdf) | Architecture, training, distribution, and general capability information | No model-specific bio or cyber dangerous-capability evaluation evidence | Adds a reproducible evidence layer without replacing the model card |
| [Qwen3.5-397B-A17B](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) | Extensive reasoning, coding, agentic, and general capability benchmarks | No dangerous-capability section or evidence that elicitation was qualified | Separates lack of observed harm from strength of the test |
| [Mistral Large 3](https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512) | Capabilities, deployment guidance, and general benchmarks | No bio or cyber catastrophic-capability threshold, elicitation budget, or control evidence | Reports bounds separately for prompt and weight access |
| [MiniMax M2.7](https://huggingface.co/MiniMaxAI/MiniMax-M2.7) | Agent, coding, professional, and general capability results | No model-specific dangerous-capability profile | Adds a harm-specific, budget-specific profile |
| [Gemma 3](https://ai.google.dev/gemma/docs/core/model_card_3) | Content safety, child safety, bias evaluation, and red teaming | No bio or cyber catastrophic-capability threshold or weight-adaptation result | Extends the disclosure question from content behavior to dangerous capability |
| [Llama 4](https://github.com/meta-llama/llama-models/blob/main/models/llama4/MODEL_CARD.md) | CBRNE and cyber evaluation descriptions, recurring red teaming, and a qualitative finding that the models do not plausibly enable catastrophic cyber outcomes | The card does not publish the challenges, scores, policy threshold, elicitation budgets, recovery on controls, or a post-adaptation access-conditioned result | Tests whether the disclosed class of routines can recover matched hidden capability and reports the supported bound |
| [gpt-oss](https://openai.com/index/gpt-oss-model-card/) | Preparedness thresholds, model-specific bio and cyber results, external review, and adversarial fine-tuning of open weights | No matched password-concealed control suite or quantified recovery rate for the elicitation battery | Adds independent qualification of the test itself and a standardized access-conditioned output |

The machine-readable record is in
`data/disclosure_gap_audit_open_weight_2026-07-18.csv`.

## Interpretation

The gap is not that open-weight developers publish no safety material. The gap is narrower: a user
usually cannot tell how much confidence to place in a below-threshold dangerous-capability result,
because the disclosure does not demonstrate that the selected routines could have found a matched
capability if it were present but concealed.

EvalBracket does not certify a model as safe. It makes the evidentiary boundary visible. A qualified
battery can support `Capability stays below threshold` for a named access tier and budget. A battery
that fails to recover controls supports `Upper bound unknown`, which is materially different from a
negative capability finding.
