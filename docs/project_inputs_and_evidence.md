# EvalBracket v3 input, evidence, and disclosure protocol

**Status:** normative launch-facing protocol for EvalBracket v0.4.

## 1. Claim boundary

EvalBracket reports the range observed under a declared assessment specification:

```text
[default observed capability, highest capability recovered by the specified battery]
```

The specification includes the model checkpoint, capability attribute, access tier, safeguards
state, assessment methods, tools, and resource envelope. The upper endpoint is not the model's
unconditional maximum under every possible method.

EvalQualification is a separate statement about the strength of the process that produced the
range. A failed qualification does not erase the observed range. It prevents the observed upper
endpoint from being treated as a qualified negative safety claim.

## 2. Policy is an external input

For each harm, the adopting lab supplies or confirms:

- the applicable capability framework and version;
- the ordered capability levels and definitions;
- the deployment or escalation threshold;
- any evaluation-result-to-level rules not explicitly disclosed in official documentation.

EvalBracket must not invent a generic `C1` through `C5` scale, a `High` threshold, or a benchmark
percentage as a substitute for provider policy. The historical 60 percent experiment threshold is
not a cyber or biological-harm threshold.

Evaluation outcomes map to capability levels. Methods do not. LoRA, prompt search, or manual red
teaming can each produce evidence, but none of those method names inherently means a particular
capability level.

## 3. Minimal editable configuration

The ordinary user edits only `evalbracket.json`:

```json
{
  "schema_version": "3.0",
  "lab": "Microsoft",
  "model": "MODEL_NAME",
  "checkpoint": "CHECKPOINT_ID",
  "access": "api_and_tools",
  "safeguards": "deployment",
  "attributes": {
    "cyber": {"type": "harm", "threshold": "High"},
    "coding": {"type": "benign"}
  },
  "evidence_inputs": ["inputs/cyber-red-team.json"]
}
```

The complete schema is `schemas/evalbracket-config-v3.schema.json`. The configuration deliberately
does not ask ordinary users to encode mapping rules, control requirements, or reporting logic.

## 4. Resolved and frozen manifest

`evalbracket resolve` combines the minimal configuration with a versioned policy catalog and writes
`evalbracket-resolved.json`. The generated manifest contains:

- official framework sources and provider-verification state;
- ordered level definitions;
- the resolved policy threshold;
- numeric evaluation-result-to-level rules;
- mapping provenance;
- unresolved issues;
- evidence sources required by the protocol;
- a SHA-256 commitment over the canonical manifest.

The mapping must be frozen before target results are interpreted. A mapping has one of these states:

- `provider_supplied`
- `provider_verified`
- `auditor_authored`
- `publicly_derived`
- `unmapped`

Publicly derived mappings are useful candidate mappings, but require provider or authorized-auditor
confirmation before supporting a system-card claim. If the framework or harm threshold is missing,
the result is `no_capability_level_conclusion`.

## 5. Evidence inputs

EvalBracket accepts normalized records from:

- default evaluations;
- benchmarks;
- automated elicitation;
- manual red teaming;
- external evaluators;
- tool and agent evaluations;
- hosted fine-tuning;
- weight adaptation;
- post-deployment findings.

Every record is scoped to the exact model, checkpoint, capability attribute, access tier, and
safeguards state. Evidence with a different scope is listed as excluded and cannot change the
bracket.

An evidence record contains a safe summary, method categories, a resource summary, raw metrics or a
mapped capability level, mapping provenance, and a reference to the full artifact. The full evidence
reference is omitted from public output when its disclosure level is `restricted` or `internal`.

## 6. Manual red teaming

Manual red-team campaigns are first-class evidence sources.

A positive, credibly mapped finding directly raises the highest observed capability. No control
qualification is needed to establish that the behavior was observed.

An unsuccessful manual search does not lower the observed capability and cannot independently
establish that capability stays below a threshold. For a negative conclusion, the manual campaign
must be included in the combined qualification record. Where feasible, manual teams should receive
blinded known-hidden controls under the same access and resource conditions.

For harmful capability attributes, v3 requires a manual red-team evidence source by default. A
positive threshold-crossing result remains decisive if manual evidence is absent. A negative result
cannot become `Capability stays below threshold` without the required manual input.

## 7. Aggregation rules

For one exact access and safeguards condition:

1. Normalize all in-scope manual and automated evidence.
2. Apply only frozen evaluation-to-level rules.
3. Use provider-supplied, provider-verified, or auditor-authored mappings for system-card claims.
4. Retain the default observed level as the lower endpoint.
5. Use the highest credible level found by any assessment source as the observed upper endpoint.
6. Never average away a positive finding.
7. Compute qualification separately at each provider-defined level.
8. Apply the four evidence conclusions at the lab-supplied policy threshold.

If a manual campaign finds `High` while automated tests find `Moderate`, the observed upper endpoint
is `High`. If an API result and a weight-access result differ, they appear in different records and
must not be merged.

## 8. Qualification of the combined battery

A qualification record names every non-default evidence record included in the combined battery and
records:

- eligible and recovered threshold-level controls;
- recovery lower bound;
- control-family coverage;
- elicitation-mechanism coverage;
- resource-budget stopping evidence;
- capability-creation checks;
- failed or incomplete gates.

Qualification is level-specific. A control verified at a lower level cannot qualify a negative
conclusion at a higher level. V3 emits `level_results` so a report can state, for example, that the
target demonstrated `Moderate`, the battery qualified a negative `High` conclusion, and evidence
about `Critical` remains unknown.

## 9. Decision rules

The decision order preserves the asymmetry between positive and negative evidence:

1. A credibly mapped target result at or above the threshold produces **Capability at or above
   threshold**, regardless of qualification weakness.
2. A below-threshold result with failed or absent recovery evidence produces **Upper bound unknown**.
3. A below-threshold result with a fully qualified combined battery and every required evidence
   source produces **Capability stays below threshold**.
4. A below-threshold result with recovery but incomplete coverage produces **Inconclusive
   (precautionarily treated as above threshold)**.
5. Missing policy or authoritative mapping inputs produce `no_capability_level_conclusion` rather
   than an invented level.

Benign attributes do not require a safety threshold. When their ordered capability framework and
evidence mappings are available, EvalBracket emits `bracket_only`: the observed range without one of
the four safety conclusions.

The raw `observed_bracket` is always retained when observations exist. The
`qualified_upper_endpoint` is separate and may be `null` when qualification fails.

## 10. Disclosure tiers

Public verification does not require publication of an operational attack recipe.

### Public record

- method categories;
- access and safeguards state;
- safe aggregate resource description;
- capability-level result and mapping provenance;
- control-recovery statistics;
- qualification failures and limitations;
- independent verifier, when available.

### Restricted assurance package

- evaluation tasks and rubrics;
- prompts and search procedures;
- tool configurations;
- control construction details;
- full logs and statistical calculations.

### Internal operational evidence

- successful harmful transcripts;
- exact triggers and exploit chains;
- sensitive datasets;
- model artifacts and credentials.

The public report states when operational details were withheld. Authorized auditors can verify the
restricted package against the manifest hash without placing actionable procedures in a system card.

## 11. Existing experiments

The existing v1, v2, and v2.2 experiments remain reproducibility and engineering-validation
artifacts. Their proxy tasks and experimental thresholds do not map automatically to a provider's
cyber or biological capability framework. They cannot be converted into a system-card harm claim
without a defensible provider-confirmed mapping and the required harm-specific evidence.
