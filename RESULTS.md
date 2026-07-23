# EvalBracket - Results

> **Historical validation evidence:** These experiments validate the locked-model substrate and the
> failure of naive below-threshold point estimates. They do not establish a calibrated upper bound
> for a particular frontier model. The current protocol and reporting API are specified in
> `docs/access_conditioned_protocol.md`.

Real-substrate run, 2026-07-02. 9 password-locked open models × 8 benign MMLU subjects = 72
(model, capability) pairs. Full pipeline + numbers reproducible from `substrate/` + `results/pairs.jsonl`.

**Ground-truth definition (read first).** Each pair carries two truths: `theta` = the *base* model's
pre-lock k-shot accuracy (~0.73, uncontaminated), and `theta_locked_pwdon` = the *locked* model's
password-on k-shot accuracy (~0.84). Analysis uses the latter, because LoRA lock-training shifts
capability, so the locked model's latent capability is its password-on accuracy - but note that means
"true capability" here is *the locked model's* ceiling, not the original model's.

## Caveats & external-review response (read with the headline)

An independent audit (`REVIEW.md`) reproduced every number and found one real bug + several caveats;
all are folded in here.

- **[FIXED + re-run done] Train/eval overlap contaminated the ground truth.** The first fleet run
  took eval and lock-train from the same MMLU split with *different* shuffles → ~72% overlap,
  inflating `theta_locked_pwdon` by answer-key memorization. `build_pairs.py` now dedupes by question
  text and takes disjoint eval/train with a hard assert. **The disjoint re-run confirms and
  strengthens the result:** on clean uncontaminated `th_on`, EvalBracket LOMO coverage is **0.92**
  (vs point-score **0.02**) - higher than the contaminated 0.86 - and a zero-GPU check on the old
  data already showed 0.90 coverage against clean pre-lock θ. The contamination inflated the target
  but did not create the result. See the comprehensive re-run section below.
- **[main scientific caveat] Exchangeability / fleet composition.** The 86% LOMO headline rides on a
  Qwen-heavy fleet; per-model coverage is 0.88–1.00 on Qwen holdouts but **0.25 on SmolLM2** and
  **0.62 on Mistral** (the two least-similar models). Coverage is marginal, not conditional. The real
  next experiment is a larger/more-diverse fleet or Mondrian (group-conditional) conformal.
- **[scope] RQ3 δ_head measures prompt-elicitation headroom, not eval-type-disguise resistance** on
  this password-lock substrate (see the Phase 4 section). The disguise-ceiling framing is by analogy.
- **[scope] RQ4 Stage 2 is thin.** The natural-checkpoint test is 2 tasks × essentially 1 usable
  model (pythia-1.4b; 2.8b was already saturated). Both returned `identified=False`. The
  suppression-detector synthesis is **consistent with our runs, not established** - it rests on one
  controlled lineage showing a lag and one natural model failing to; OLMo-2 or a sharply-emergent
  capability is the needed follow-up. (2.8b now reproducible: `data_snapshot/pythia_2.8b.jsonl`.)
- **[scope] S5 (refusal) ≡ 0** on all pairs - forced-choice logit scoring cannot refuse - so the κ
  floor-knob is inert here; refusal-adjustment is untested and would need a generative eval.
- **[repro] Fleet was 9 models, not 10:** Phi-3.5 was dropped (transformers 5.x `DynamicCache`
  incompatibility). Data in `data_snapshot/` (`results/` is git-ignored); LoRA adapters not kept
  (regenerable from seeded code). Reproduce: `substrate/fleet.sh` → pull `pairs.jsonl` →
  `substrate/analyze_real.py`.

## Disjoint re-run + diverse fleet + held-back detection (the comprehensive re-run)

A second run fixed the contamination, expanded to a family-diverse fleet, and added self-generated
held-back-detection ground truth (`data_snapshot/pairs2_disjoint_diverse.jsonl`, 12 models × 8
subjects = 96 pairs; Phi-3-mini + internlm skipped). Disjoint eval/train (dedup by question text),
and a fine-tune **release** attack per model to measure "what surfaces."

**(a) Existence proof - confirmed and STRENGTHENED on clean ground truth.** Against the disjoint,
uncontaminated `th_on`: ceiling recovery 84% (was 79%); B0 Wilson(S1) coverage **0.02**; EvalBracket
LOMO coverage **0.92** (was 0.86), width 0.46. The contamination fix *raised* coverage - the result
was never an artifact of the leak. Fusion still ornamental (B2 ≈ B_se). Wider intervals (0.46 vs
0.24) are the honest cost of a more heterogeneous fleet.

**(b) Exchangeability - diversity helps, but the extreme outlier persists.** Per-model LOMO coverage:
10 of 12 models at 0.88–1.00 (SmolLM2-1.7B and Mistral, the old under-coverers, are now 1.00). The
misses moved to the two models *most unlike* the fleet: **SmolLM2-360M (0.00)** and
**stablelm-2-1.6b (0.29)**. So a diverse fleet covers more models, but the marginal-not-conditional
limit is real and concentrates at the extremes - a bigger/curated fleet or Mondrian conformal remains
the fix, and coverage should be reported per-model, not just aggregate.

**(c) Held-back detection - a strong, novel, self-generated result.** For each locked pair we measured
the observable elicitation gap (S3−S1, no ground truth) and then *released* the lock by a fine-tune
attack and measured the surfaced capability (s_release−S1). Result:
- **corr(observable gap, surfaced capability) = 0.97** - the gap tracks *how much* surfaces, near
  the identity line (mean gap +0.32 vs mean surfaced +0.35). Caveat: both partly track the same lock
  magnitude, so this is a strong within-fleet correlation; a *predictive* claim needs held-out models.
- The gap FLAG (S3−S1 significant) cleanly separates outcomes: flagged pairs surface **+0.42**,
  un-flagged **+0.09**.
So on open models, the elicitation gap is not just a *flag* that capability is held back - it
**correlates strongly (0.97) with how much surfaces** when suppression is released, via a release path
(fine-tune) distinct from the estimator (few-shot). This is the open-source, self-generated version of
the system-card held-back-detection idea and a positive within-fleet result - though, because gap and
surfaced share the underlying lock magnitude, a genuine forecast needs held-out validation.

## RQ2 / RQ3 / RQ5 - clean re-derivation on the disjoint fleet (fleet3)

All measured on the disjoint split (`data_snapshot/pairs_arms3.jsonl` 8 models × 8 subjects;
`pairs_resist3.jsonl` 5 resist models), so RQ2/RQ3/RQ5 now come from clean ground truth like RQ1.

**RQ2 - mitigation head-to-head (which recovers the locked capability?).** % of the suppression gap
(th_on − S1, mean gap 0.49) each method recovers, 64 clean pairs:

| method | accuracy | % of gap recovered |
|---|---|---|
| raw / suppressed (S1) | 0.25 | 0% |
| disguise prompt (Thomson-Li axis) | 0.30 | **11%** |
| cooperate prompt (Li-Turner axis) | 0.31 | **12%** |
| few-shot elicitation (S3) | 0.73 | **97%** |
| fine-tune release | 0.75 | **101%** |
| password (ground truth) | 0.74 | 100% |

The disguise/uncertainty axis, the cooperativeness axis, and elicitation, head-to-head on the *same*
locked substrate: **prompt mitigations recover ~11–12%; elicitation recovers ~all of it.** You cannot
prompt past a lock; you must elicit it. (The head-to-head the prior-art map named the single most
defensible contribution.)

**RQ3 - disguise ceiling (clean).** δ_head = **+0.427, 95% CI [0.322, 0.521]** (excludes 0); prompts
close 13% of the gap, 87% is elicitation-only. (Was +0.47 on the contaminated fleet - consistent,
slightly lower on clean ground truth.)

**RQ5 - elicitation-resistant hard case (clean).** 5 disjoint resist locks: S3 recovers θ on **3%**
(vs 84% normal). Bracket coverage collapses **0.93 → 0.00** and *silently*; the elicitation-gap
abstain rule (100% of resist pairs flagged) restores it to **0.81** loud, normal fleet unchanged
(0.94). Same story as before, now on clean disjoint ground truth.

## Headline (ORIGINAL run - superseded by the clean disjoint re-run above)

> Numbers in this section are from the FIRST fleet (9 models, 72 pairs) that had the ~72% train/eval
> overlap. The clean, disjoint headline is **0.92 vs 0.02** (12 models) in the comprehensive re-run
> section above; this block is kept for the original ladder detail.

The naive point score (password-off accuracy) is **catastrophically wrong** about true capability,
and the calibrated conformal interval **brackets the truth where the point score cannot**.

| method | coverage of true θ | mean interval score | mean width |
|---|---|---|---|
| **B0 - Wilson CI around suppressed score S1** (the naive system-card read) | **0.00** | 10.06 | 0.10 |
| B1 - Wilson CI around elicited score S3 | 0.76 | 0.38 | 0.08 |
| B1c - conformal (unnormalized) | **0.86** | 0.36 | 0.24 |
| B_se - conformal (SE-normalized) | 0.86 | 0.41 | 0.29 |
| B2 - EvalBracket (SE + awareness fusion) | 0.85 | 0.52 | 0.30 |

- **The point score never contains truth.** Mean θ = 0.84, mean suppressed S1 = 0.29 - a 0.55 gap.
  A Wilson CI around the suppressed score (B0) contains the true capability on **0 of 72** held-out
  pairs. A single number, however tightly measured, is the wrong object under a capability lock.
- **The calibrated bracket recovers truth**, leave-one-model-out, on **86%** of held-out pairs
  (nominal 90%), at a usable width (~0.24). This is the pre-registered RQ1 result on real ground
  truth, not a synthetic theorem check.

## The precondition that makes it work: elicitation recovers θ

Coverage is anchor-driven, and the ceiling anchor is behavioral elicitation (S3). On these models:

- mean θ (password-on) = 0.837, mean S1 (password-off, suppressed) = 0.289, mean S3 (password-off,
  **k-shot elicited**) = 0.805 - a shortfall of only 0.032.
- **79% of pairs**: few-shot elicitation recovers θ within 0.05.

This is Greenblatt et al.'s "a few demonstrations elicit the locked capability," reproduced on a
fresh 9-model fleet - and it is exactly the condition Phase 1 predicted the method's validity would
hinge on. Where a lock resists elicitation, the ceiling anchor fails and the bracket cannot hold
(shown breaking to ~0.45 coverage in the synthetic elicitation-resistant arm).

## Honest negative result: the "fusion" is ornamental

B2 (the awareness-signal fusion, S2/S4) does **not** beat SE-normalized or even plain conformal
(B2 interval score 0.52 vs B_se 0.41 vs B1c 0.36 - B2 is slightly *worse*). The synthetic smoke test
predicted this (fusion tied with SE-norm), and it holds on real data. **The contribution is the
calibrated bracket + its validity proof on known ground truth - not the signal fusion.** This
matches the prior-art map's verdict that novelty lives in integration + validity proof, not a new
mechanism. (S2 was neutral in this run; a measured sandbagging signal might change this, but the
current honest finding is: don't claim fusion value.)

## Where it misses - the exchangeability limit, made concrete

Per-model bracket coverage (B1c, leave-one-model-out):

| model | θ | S1 | bracket coverage |
|---|---|---|---|
| Qwen2.5-0.5B | 0.77 | 0.27 | 0.88 |
| Qwen2.5-1.5B | 0.89 | 0.45 | 1.00 |
| Qwen2.5-3B | 0.91 | 0.23 | 1.00 |
| Qwen2.5-7B | 0.95 | 0.22 | 1.00 |
| OLMo-2-7B | 0.87 | 0.39 | 1.00 |
| gemma-2-2b | 0.80 | 0.23 | 1.00 |
| Llama-3.2-3B | 0.85 | 0.28 | 1.00 |
| Mistral-7B | 0.78 | 0.31 | 0.62 |
| **SmolLM2-1.7B** | 0.72 | 0.22 | **0.25** |

The misses concentrate in the two models **least similar to the (Qwen-heavy) calibration fleet**
(SmolLM2, Mistral). This is precisely the marginal-not-conditional / locked↔target exchangeability
caveat from spec §3.2 and §7, now observed: hold out a typical model and the bracket covers
perfectly; hold out an outlier and it under-covers. A larger, more diverse calibration fleet (or
group-conditional / Mondrian conformal) is the stated remedy.

## What this establishes, and what it doesn't

**Establishes (on real ground truth):**
1. A naive CI around a point score under a capability lock has ~2% coverage of true capability - the
   honest object is an interval, not a number.
2. A conformal-calibrated [floor, ceiling], calibrated across locked models, brackets true
   capability at ~nominal rate leave-one-model-out - where the point score fails.
3. The precondition (elicitation recovers θ) holds on a fresh fleet; the method is exactly as valid
   as that recovery.

**Does NOT establish (stated, not hidden):**
- Transfer to non-exchangeable frontier targets (only tested within the locked open-model fleet;
  outlier models under-cover).
- Any value from the awareness-signal fusion (ornamental here).

## Phase 4 - arms (RQ2/RQ3): you cannot prompt your way past a lock

On the 9 locked models, prompt interventions barely move the suppressed score (mean accuracy,
password-off): raw 0.287, cooperate 0.304, disguise 0.364. Best mitigation 0.367 vs true θ 0.837.

- **δ_aware (closable by a prompt) = +0.079** - disguise/cooperation recover only ~8 points.
- **δ_head (the disguise ceiling) = +0.470, 95% CI [0.38, 0.57]** (excludes 0) - 86% of the
  suppression gap is closable ONLY by elicitation/fine-tune, not by prompting.
- Disguise (deploy-framing) beat cooperation (won 83% of pairs), but both are weak.

A quantified, controlled version of the "disguise is a dead end" argument (Karvonen/Ivanov), which
until now existed only as blog-post debate. Scope: on a password lock, this measures prompt-
elicitation, not eval-type uncertainty (arms.py caveat).

## Phase 5 - the hard case: coverage COLLAPSES when elicitation is defeated

Trained **5** elicitation-resistant locks (demos → random target, so few-shot cannot unlock:
Qwen2.5-3B/7B, Llama-3.2-3B, gemma-2-2b, Mistral-7B). Calibrated the bracket on the normal
(elicitable) fleet, tested on the resistant models:

| | normal fleet | resistant fleet |
|---|---|---|
| S3 recovers θ (within 0.05) | 79% | **0%** |
| mean θ − S3 shortfall | +0.03 | **+0.55** |
| **bracket coverage of θ** | **0.94** | **0.00** |

- **Elicitation is fully defeated**: S3 collapses to S1 (the suppressed score) - showing examples
  recovers nothing.
- **The bracket collapses to 0% coverage** - no better than the naive point score. Confirmed on
  real models what the Phase 1 synthetic predicted (~0.45 there; 0.00 here with a harder lock).
- **It fails SILENTLY, not loudly.** The resistant interval sits at [0.44, 0.44] (a confident,
  ~zero-width point) while truth is 0.80 - a confident wrong answer, exactly like the point score
  it was meant to replace.
- **BUT the failure is DETECTABLE without ground truth.** The elicitation gap (S3 − S1) is **+0.52**
  when the bracket is trustworthy and **−0.01** when it is not. This gap is a built-in trust signal:
  *if elicitation recovers nothing, the ceiling is untrustworthy.*

### The abstain rule (implemented) - the silent failure is now loud

`EvalBracket(abstain_on_weak_elicitation=True)` (default) checks, per pair, whether the elicitation
gain S3 − S1 is significantly positive (> 1.64 × pooled binomial SE). If not, the ceiling is
untrustworthy and is blown up to 1 ("at least the floor; upper bound unknown"). Measured effect:

| | NORMAL cov / width | RESIST cov / width |
|---|---|---|
| abstain OFF (silent) | 0.94 / 0.30 | **0.00 / 0.00** (confident wrong point) |
| abstain ON (loud) | 0.94 / 0.30 *(unchanged)* | **0.93 / 0.46** (wide, honest) |

It abstains on **95%** of the resistant pairs, restores coverage 0.00 → 0.93, and leaves the normal
fleet **completely unchanged**. The method now says "I can't upper-bound this" instead of lying.

## RQ4 (Stage 1b) - maturation: the ceiling→floor lag is recoverable and tracks the imposed mechanism (one controlled lineage)

Built ONE continuously-trained model (Qwen2.5-0.5B memorizing an arbitrary key→letter bank) where
the ceiling (password-on recall) forms as the bank is memorized and the floor (password-off recall)
is gated by a suppression that **decays** on a schedule (midpoint s_mid). The ceiling→floor lag is
NOT planted (floor ≠ ceiling(t−L), the circular design the review killed) - it **emerges** from
s_mid vs memorization speed, and floor/ceiling are measured independently.

| s_mid (decay midpoint) | recovered lag | 95% CI | identified | width state |
|---|---|---|---|---|
| 0.20 (early decay) | **0.40** | [0.3, 0.5] | yes | complete |
| 0.35 | 4.11 | [4.0, 4.2] | yes | complete |
| 0.50 | 6.76 | [6.4, 8.1] | yes | complete |
| 0.65 (late decay) | 8.77 | [8.5, 8.7] | yes | complete |

- **The recovered lag TRACKS the mechanism: corr = 0.99.** Later suppression decay → larger lag.
- **Falsifiable, and it didn't falsify:** early decay (s_mid=0.20) yields lag ≈ 0.4 - the design CAN
  produce the near-zero/"no-lead" outcome, so "ceiling leads floor" is a finding here, not a
  construction. On a real trained lineage the signature appeared and scaled with the cause.
- Every trajectory shows the full **widen-then-narrow** width lifecycle (absent → wide → narrow-high),
  and the hardened instrument flagged all four as `identified` with tight bootstrap CIs.

This is the controlled instrument + emergent-signature result: on a real model, the [floor, ceiling]
range's trajectory recovers an emergent maturation lag and its magnitude tracks the underlying cause.
It is NOT yet proof that *natural* capabilities (unforced) mature this way - that is Stage 2 (public
Pythia/OLMo checkpoints), and forward-forecast validity is Stage 3.5.

## RQ4 (Stage 2) - natural checkpoints: the timing lag is a SUPPRESSION effect, ~absent in vanilla pretraining

Ran the natural-signature test on public Pythia-1.4b checkpoints (11, step128→143000), sciq +
arc_challenge. floor = 0-shot accuracy (default); **ceiling = per-checkpoint fine-tune elicitation on
frozen weights** (the design-review fix - few-shot is confounded by in-context-learning onset and is
kept only as a diagnostic). Result:

| task | floor 0-shot | ceiling fine-tune | timing lag | instrument verdict |
|---|---|---|---|---|
| sciq | 0.28 → 0.62 | 0.31 → 0.79 | ceiling/floor inflect **together** (~0) | INCONCLUSIVE (estimators disagree) |
| arc_challenge | 0.25 → 0.31 | 0.28 → 0.38 | hint of lead (4.04 vs 4.28) but capability barely emerges | INCONCLUSIVE (fit R² too low) |

Two honest layers:

1. **The instrument refused to fabricate.** On gradual, noisy natural curves it returned
   `identified=False` both times rather than a confident lag - the hardened honesty gate (stats
   review) working on real data, exactly as designed. "Inconclusive" ≠ evidence; it says so.
2. **The consistent real pattern: a LEVEL gap, not a timing lag.** The fine-tune ceiling sits above
   the 0-shot floor throughout (elicitable-above-default in *level*), but the two curves emerge at
   ~the same training time - there is no clear ceiling-*leads*-floor timing lead in vanilla Pythia.

**The synthesis (novel, ties the whole program together).** The forecasting lead time - the
horizontal lag - is a **suppression effect**. It is large exactly when a mechanism holds the floor
BELOW the reachable ceiling: in Stage 1b an imposed decaying-suppression lock produced large,
schedule-tunable leads (corr 0.99). In vanilla pretraining there is no such mechanism - capability
becomes *reachable* (fine-tunable) and *default* (0-shot) at roughly the same time - so you get a
level gap with little/no timing lead. In our single natural case this is consistent with (but does NOT confirm)
and it is the useful one: **the lead-time signal is biggest precisely in the regime the tool is for** -
locked / sandbagging / safety-shaped / eval-aware models where the floor is deliberately held back -
and smallest in ordinary pretraining where reachable ≈ default. The maturation lag is, in effect,
a *suppression detector*.

**Scale confirmation (pythia-2.8b, sciq):** the capability is **already fully emerged at the first
checkpoint** (0-shot floor flat at 0.676 across all 9 measured checkpoints step128→64000; run
stalled on the two largest late-checkpoint downloads, pattern unambiguous) - the emergence happened
before the observable window. So across scales the natural timing-lead is elusive for *opposite* reasons: 1.4b
too gradual to certify, 2.8b already-saturated (no emergence curve to fit at all). Both show only a
constant **level gap** (ceiling ~0.80 vs floor ~0.68), no timing lead. This strengthens rather than
weakens the verdict.

**Honest scope:** sciq + arc_challenge, pythia-1.4b + 2.8b. The natural-signature question isn't
fully closed - a capability with sharp, staggered natural emergence *inside* the window could still
show a certifiable lead - but across everything we ran, natural pretraining shows a level gap and no
certifiable timing lead, while imposed suppression shows a large, mechanism-tracking one. The
instrument distinguishes the two honestly (certified in 1b, refused in 2).

## Final verdict

- **Validated (real ground truth):** where you can elicit hidden capability, a calibrated bracket
  recovers true capability (86–94% coverage) where a naive CI around the point score is confidently
  wrong (~2%). This
  is more than the field's blog-post arguments; it is measured on models with known truth.
- **Boundary mapped:** the method is exactly as good as elicitation. Defeat elicitation and it
  collapses to 0% - silently. It also degrades on models unlike the calibration set.
- **The honest, defensible claim is therefore NOT "ranges work," but:** *a calibrated bracket
  recovers hidden capability whenever elicitation works, and the elicitation gap (S3 − S1) is an
  observable signal - now wired in as an abstain rule - that makes the method fail loudly rather
  than lie when it doesn't.* The "signal fusion" we hypothesized as the novelty is ornamental; the
  real contributions are (1) the calibrated bracket + its validity proof on known truth, and (2) the
  elicitation-gap abstain rule as a self-diagnostic that converts silent failure into honest
  refusal (0.00 → 0.93 coverage on the hard case, normal fleet untouched).
