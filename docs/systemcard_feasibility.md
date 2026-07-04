# Can public system cards serve as ground truth for the held-back-detection backtest?

Deep-research pass (2026-07-02, 26 primary sources, 25/25 claims verified 3-0). Question: do frontier
system cards report an ELICITED capability ("ceiling": fine-tune / helpful-only / scaffold / uplift)
separately from AS-DEPLOYED behavior ("floor"), comparably across versions?

## Bottom line
**Yes, the elicited ceiling is reported — but the usable *quantitative, version-over-version* data
exists essentially only at ANTHROPIC (CBRN uplift + AI R&D).** OpenAI has the structure but collapses
it to coarse buckets; Google DeepMind is unverified.

## Per lab
- **OpenAI** — separates "pre-mitigation"/"helpful-only" research model (safety training stripped)
  from deployed. Preparedness Framework v2 (Apr 15 2025) explicitly targets max elicitable capability
  (refusal-stripped variant, best scaffolds, fine-tuning if weights released) — but calls it a
  **lower bound, not a ceiling**. CRITICAL LIMIT: the *scorecard* collapses elicited-vs-deployed into
  identical Low/Med/High buckets; for o1 they set post-mit = pre-mit "to err on the side of caution"
  → no numeric gap at scorecard granularity (in-body benchmark %s exist but aren't turned into
  distinct levels). GPT-4.5 card: evals are "a lower bound," no distinct fine-tuned max number.
- **Anthropic** — evaluates helpful-only snapshots + agentic harnesses + tools + expert uplift;
  reports "the highest score across all snapshots" as the **capabilities ceiling**, distinct from the
  deployed HHH model. UNIQUELY publishes quantitative version-over-version series:
  - Bioweapons-acquisition uplift: Sonnet 3.7 **1.53x** → Sonnet 4 **1.70x** → Opus 4 **2.53x**
    (accept ≤2.8x; Opus 4 "sufficiently close" → could not rule out ASL-3).
  - ASL-4 virology uplift: Sonnet 3.7 0.403 → Opus 4 0.498 → Opus 4.5 0.668 (1.32x→1.82x→1.97x).
  - Deployed-with-safeguards contrast is explicit (e.g. prompt-injection 71% no-safeguards vs 89%
    with; CBRN deployed refuses).
- **Google DeepMind** — Frontier Safety Framework / Gemini CCLs: **ZERO surviving claims.** The
  elicited-vs-deployed decomposition is UNVERIFIED here; do not assume it exists.

## The user's GPT-5 bio example — CONFIRMED
gpt-5-thinking rated **High** in Bio/Chem (Aug 13 2025) where o1/o3-era were **Medium** — a real
surfacing. Floor/ceiling explicit: deployed "refused every prompt" vs helpful-only variant
"substantially outperformed experienced human baseliners." BUT the earlier cards' coarse buckets mean
the PRE-surfacing elicitation signal is only PARTIALLY recoverable for OpenAI (need in-body benchmark
%s, not the scorecard).

## The Anthropic early-warning case = exactly the target pattern
Opus 4.5 (Nov 2025) red-teaming: "unlike previous models, Claude Opus 4.5 was able to generate some
creative ideas that the expert judged as credible for enhanced biological threats... a preliminary
early warning sign" — below ASL-4 threshold, released ASL-3. A documented *latent capability
approaching threshold, flagged one version before it would surface by default.* AI R&D: Opus 4.6
experimental scaffold 427x vs 190x standard, "roughly reaching" ASL-4 rule-out thresholds, judged not
crossed. These are real (elicited-gap-at-N) records.

## Feasibility table
| lab | family | capability | (elicited, deployed) decomposition | version-comparable? | backtest cell |
|---|---|---|---|---|---|
| Anthropic | Claude 3.7→4→4.5→4.6 | CBRN (bio/virology uplift) | YES, quantitative | YES (vs thresholds) | **FEASIBLE** |
| Anthropic | Claude 4→4.5→4.6 | AI R&D / autonomy | YES (scaffold speedups) | mostly | **FEASIBLE** |
| OpenAI | GPT-4.5→o3→GPT-5 | Bio/Chem | structure yes, scorecard coarse | partial (dig in-body %) | PARTIAL |
| OpenAI | — | cyber/persuasion/autonomy | not confirmed recoverable | no | UNCONFIRMED |
| Google DeepMind | Gemini | all CCLs | UNVERIFIED | unknown | GAP |

## Honest caveats (a backtest must handle these)
- Both labs call elicitation a **lower bound**, not a true ceiling (terminology).
- Anthropic **thresholds CHANGED** across versions (virology rule-out tightened 4.5 → 1.8 of 18) and
  **trial conditions differed** (2 vs 3 vs 4 task-days) — real comparability confounders to normalize.
- **Small N**: a handful of versions × a few capabilities → **case-study / illustration strength**,
  not powered statistics.
- **These are the suppression regime** (safety-held-back CBRN/autonomy) — exactly where Stage 2
  predicts the lead signal should be strong. So the Anthropic uplift series is the natural real-world
  test bed for the suppression-detector thesis.

## Recommended backtest (public-data, no GPU, no privileged access)
Extract the Anthropic CBRN + AI-R&D elicited-uplift numbers into a version series (the "ceiling"
trajectory), take the deployed ASL determination / mitigated behavior as the "floor," and test
whether the elicited number rising toward/over a threshold at version N preceded the as-deployed
capability being treated as present at N+1. Report as a small-N case study, normalizing for the
documented threshold/trial-condition changes. Cross-check the OpenAI GPT-5 bio surfacing by
reconstructing in-body benchmark %s (o1/o3/4.5/GPT-5) rather than the collapsed scorecard.
