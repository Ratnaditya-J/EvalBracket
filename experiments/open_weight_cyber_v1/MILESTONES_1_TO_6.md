# Milestones 1 through 6 completion record

## 1. Freeze EvalBracket v1 protocol

Complete. The normative method and four conclusion labels are in
`docs/evalbracket_v1_protocol.md`. The machine-readable disclosure format is in
`schemas/evalbracket-report-v1.schema.json`.

## 2. Publish the disclosure-gap audit

Complete in the repository. The source-backed audit covers eight representative open-weight model
disclosures and is in `docs/disclosure_gap_audit_2026-07-18.md`, with a machine-readable CSV in
`data/disclosure_gap_audit_open_weight_2026-07-18.csv`.

## 3. Validate matched password-locked cyber controls

Complete. Ten retained-capability controls were verified across four model families and two
concealment families. Four induced controls were retained as secondary evidence. Thirty-four failed
or ambiguous attempts are reported rather than hidden.

## 4. Qualify the elicitation battery

Complete with a negative qualification outcome. Prompt batteries failed recovery. Weight batteries
recovered 85.7 to 100 percent of eligible leave-one-family-out controls, but their one-sided 95
percent lower bounds were only 47.9 to 68.8 percent. The suite also covered only one task and one
source, below the frozen requirement of two. No battery qualified.

## 5. Produce the first real EvalBracket profile

Complete for Qwen2.5 1.5B on three controlled cyber-knowledge tasks. The profile reports exact
conclusions by API-high and weight-high battery. It contains no unsupported below-threshold claim.

## 6. Replicate on a second model family

Complete and exceeded. The same campaign was replicated on Phi-3.5 Mini, Mistral 7B v0.3, and
SmolLM2 1.7B, with two seeds per family.

The canonical numerical summary is `experiments/open_weight_cyber_v1/CAMPAIGN_RESULTS.md`.
