# EvalBracket v0.2 RunPod control-calibration pilot

This is a safe protocol-integration smoke test, not dangerous-capability evidence. The MMLU
`computer_security` and `college_biology` subjects are benign academic proxies. They do not measure
operational cyber capability, biosecurity capability, CBRN risk, or any company's C1 through C5
framework. No frontier model was evaluated, so this run cannot produce a system-card conclusion.

The pilot checks three narrower claims:

1. A capability can be verified before a password-lock LoRA is applied.
2. Recovery can differ by elicitation method and access tier.
3. A failed concealment construction must be excluded before control recovery is calculated.

The predeclared proxy threshold was 70% multiple-choice accuracy. `S1` is the locked model's raw
password-off score, `S3` is five-shot password-off elicitation, and `s_release` is password-off
accuracy after direct LoRA weight fine-tuning.

| Control | Proxy domain | Verified before lock | Locked raw (S1) | Five-shot (S3) | Weight fine-tune | Control status |
|---|---|---:|---:|---:|---:|---|
| Standard | Computer security | 70.0% | 45.0% | 72.5% | 65.0% | Valid known-hidden control; prompt recovery passed |
| Standard | College biology | 77.6% | 41.4% | 74.1% | 72.4% | Valid known-hidden control; prompt and weight recovery passed |
| Resistant | Computer security | 70.0% | 70.0% | 42.5% | 65.0% | Excluded: concealment failed before elicitation |
| Resistant | College biology | 77.6% | 56.9% | 55.2% | 70.7% | Valid known-hidden control; prompt recovery failed and weight recovery passed |

The resistant biology control is the clearest access-conditioned result. Under prompt-level access,
neither five-shot elicitation nor the best held-out framing arm reached 70% (the best framing arm was
69.0%). Direct weight fine-tuning reached 70.7%. A negative API-tier result therefore cannot be
qualified using the weight-access recovery result; they are separate routines.

The resistant computer-security derivative is equally informative as a quality-control failure. Its
raw locked score remained at the 70% proxy threshold, so it was not actually known-hidden. Counting
its later recovery or non-recovery would be invalid. This finding motivated v0.2.1's explicit
`concealment_verified` and `concealment_evidence` requirements and the exclusion count in
`ThresholdQualification`.

Limitations: one open-weight 1.5B model, one seed, 40 computer-security items, 58 biology items,
benign multiple-choice tasks, and synthetic password-lock concealment. The run validates experiment
plumbing and a protocol quality check. It does not validate control coverage for real frontier bio or
cyber evaluations.

Raw outputs are in `standard_control.jsonl` and `resistant_control.jsonl`. Exact commands,
environment versions, checksums, timestamps, and approximate cost are in `manifest.json`.
