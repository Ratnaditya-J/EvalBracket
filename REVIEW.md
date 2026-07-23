# EvalBracket - External Review

> **Historical review:** This audit covers the v0.1 experimental program. The current v0.2 protocol
> and reporting API are specified in `docs/access_conditioned_protocol.md` and
> `evalbracket/protocol.py`.

**Reviewer:** independent read-only audit. First pass 2026-07-02; **revised after
the RQ4 (maturation) build landed.**
**Method:** read all docs + package source; independently recomputed every headline claim from raw
data; re-ran `analyze_real.py`, `analyze_arms.py`, `analyze_resist.py`, `analyze_maturation.py`,
`analyze_pythia.py`; ran the test suite (24 pass). No source or data was modified.

---

## What changed since the first review

The project grew from a 3-phase existence-proof study into a **full three-question program** by
adding RQ4 (capability maturation / forecasting lead-time) on real Pythia checkpoints, plus a
controlled continued-training instrument. The RQ4 result is, in my view, now the **strongest
conceptual contribution in the project** (see below). The core RQ1/RQ3/RQ5 results are unchanged and
still reproduce exactly. The test suite grew 19 → 24, all passing.

One flag from the first review is **still open and should be fixed first** (README status; see
Issues #1).

---

## Verdict

**This is a legitimate, reproducible research program, and the write-up does not oversell its
data - it is unusually disciplined about the opposite.** Across three research questions (RQ1
bracket validity, RQ3 disguise ceiling, RQ4 maturation), every number I recomputed matches the raw
data, and the two places the method fails (elicitation-resistant locks; natural pretraining showing
no timing lag) are reported as findings rather than buried. The intellectual honesty is the
standout feature: the original headline hypothesis ("signal fusion") is reported as a null, and the
RQ4 instrument *refuses to certify* a lag on noisy natural data rather than fabricate one.

The gap to a submittable workshop paper is now **write-up hygiene + one generalization experiment
(exchangeability)**, not new core method work - **with one exception surfaced by the substrate
audit below:** the lock-training set overlaps the eval set by ~72%, which inflates the very
ground-truth target the existence proof validates against. The *mechanical* result survives; the
*semantic* "recovers true capability" claim needs the disjoint-split re-run before it holds. This is
a cheap fix, but it must be done before submission.

---

## Reproduction check (independent, from raw data)

All recomputed directly from `results/pairs.jsonl` (72 pairs, 9 models, 8 MMLU subjects), ground
truth = `theta_locked_pwdon` (password-on accuracy):

| Claim (from RESULTS.md) | Reported | Independently recomputed | Match |
|---|---|---|---|
| mean θ / mean suppressed S1 / gap | 0.84 / 0.29 / 0.55 | 0.837 / 0.289 / 0.548 | ✓ |
| B0 (Wilson CI around suppressed S1) coverage of θ | 0.00 | 0.000 (0/72) | ✓ |
| Ceiling recovery: S3 within 0.05 of θ | 79% | 79.2% | ✓ |
| Conformal bracket (B1c) coverage LOMO / width | 0.86 / 0.24 | 0.861 / 0.239 | ✓ |
| B2 fusion vs B_se interval score (ornamental) | tied/worse | 0.518 vs 0.414 | ✓ |
| RQ3 δ_head (disguise ceiling) 95% CI | +0.47 [0.38, 0.57] | +0.470 [0.382, 0.571] | ✓ |
| Resist hard-case coverage, abstain OFF → ON | 0.00 → 0.93 | 0.00 → 0.93 | ✓ |
| RQ4 Stage 1b: recovered lag tracks suppression-decay | corr 0.99 | corr 0.991 | ✓ |
| RQ4 Stage 2 (Pythia): lag certifiable on natural curves | INCONCLUSIVE | identified=False both tasks | ✓ |
| Test suite | - | 24 passed | ✓ |

Nothing was found to be asserted beyond what the data supports. The resist hard-case coverage
recovery is now 0.00 → 0.93 (was 0.96 with 3 resist models; now 5 models - the number moved with the
larger, harder fleet, and the writeup was updated to match).

---

## What was built and run

- **Substrate (real, GPU):** LoRA password-locks on 9 open models (Qwen 0.5/1.5/3/7B,
  Llama-3.2-3B, Mistral-7B-v0.3, gemma-2-2b, OLMo-2-7B, SmolLM2-1.7B) × 8 benign MMLU subjects →
  72 pairs, on RunPod H100/H200 (pods deleted post-run; data in `data_snapshot/`).
- **Choice of benign MMLU over WMDP:** correct call. The method is domain-agnostic (it recovers
  capability given known ground truth), so a benign target sidesteps all CBRN/hazard optics with no
  loss of validity. WMDP remains an optional later swap-in.
- **Method (`evalbracket/combiner.py`):** split-conformal calibration with the finite-sample
  `(n+1)` rank correction; group-disjoint leave-one-model-out fit / calibrate / test; legible
  monotone anchors (upper = max(S1,S3); lower = S1·(1−κ·S5)). **Key correctness property:** the
  margin-driver signals (S2 sandbagging, S4 awareness-delta) enter *only* through a positive scale
  on the conformal margin - they never move an anchor - so the distribution-free coverage guarantee
  holds regardless of whether those signals are informative. This is proper conformal discipline.
- **Self-critique (`docs/critique_phase1.md`):** three adversarial reviews (statistical, code,
  circularity) that caught and fixed real issues - correlation-by-construction in the synthetic
  harness (→ relabeled a smoke test, not an existence proof), max-of-noisy-arms biasing δ_head
  downward (→ unbiased sample-split estimator), model clustering breaking the bootstrap CI (→
  cluster bootstrap), and missing item-count rescaling (→ SE-normalized scale).

---

## Findings by phase (all independently reproduced)

1. **RQ1 existence proof - holds.** A point score under a capability lock has **0% coverage** of
   true capability (mean θ=0.84 vs suppressed 0.29). The conformal bracket recovers truth on **86%**
   of held-out pairs leave-one-model-out, at usable width (~0.24). This is the honest object claim:
   under a lock, the truth is an interval, not a number.
2. **Precondition - met and named.** Elicitation (S3) recovers θ within 0.05 on **79%** of pairs - 
   Greenblatt et al.'s "a few demonstrations elicit the locked capability," reproduced on a fresh
   9-model fleet. Coverage is entirely anchor-driven, so this recovery *is* the method's validity.
3. **RQ3 disguise ceiling - quantified.** δ_head = **+0.47, 95% CI [0.38, 0.57]** (excludes 0),
   via the unbiased sample-split estimator + cluster bootstrap. Prompt interventions close only ~14%
   of the suppression gap; ~86% is elicitation-only. This is the controlled, ground-truthed version
   of the Karvonen/Ivanov "disguise is a dead end" argument, which previously existed only as
   forum debate.
4. **RQ5 hard case - faced, not hidden.** Elicitation-resistant locks (few-shot demos → random
   target) collapse bracket coverage to **0%**, and - importantly - *silently* (a confident,
   ~zero-width wrong point, exactly the failure mode of the point score it replaces). The fix is an
   **elicitation-gap abstain rule** (`S3 − S1` significance test, no ground truth required): it
   restores resistant-fleet coverage **0.00 → 0.93** (5-model resist fleet), abstains on 95% of
   resistant pairs, and leaves the normal fleet completely unchanged.

---

5. **RQ4 maturation - the new result, and the most conceptually valuable.** Two stages:
   - **Stage 1b (controlled, real trained model).** A single continued-training lineage (Qwen2.5-0.5B
     memorizing a key→letter bank) with a *decaying* password-off suppression. The ceiling→floor lag
     is **not planted** (the reviewers explicitly killed the circular `floor=ceiling(t−L)` design) - 
     it emerges from the suppression-decay schedule, and floor/ceiling are measured independently.
     The recovered lag tracks the decay midpoint with **corr = 0.99**, and - critically - the fast-decay
     run yields lag ≈ 0.4, proving the design *can* produce the no-lead outcome. So "ceiling leads
     floor" is a finding, not a construction. Reproduced exactly.
   - **Stage 2 (natural, public Pythia checkpoints).** On pythia-1.4b (sciq, arc_challenge) the
     instrument returns **`identified=False` on both tasks** - it refuses to certify a timing lag on
     gradual/noisy natural curves. pythia-2.8b shows the capability already saturated before the
     observable window. The honest reading, which the writeup states well: natural pretraining shows
     a **level gap** (fine-tune ceiling above 0-shot floor) but **no certifiable timing lag**.
   - **The synthesis is the genuinely novel idea:** the forecasting lead-time is a **suppression
     effect** - large exactly when a mechanism holds the floor below the reachable ceiling (locks,
     sandbagging, safety-shaping, eval-awareness), and ~absent in vanilla pretraining where reachable
     ≈ default. The maturation lag is, in effect, a *suppression detector* - biggest in precisely the
     regime the tool is built for. This ties RQ4 back to RQ1/RQ3/RQ5 into one coherent story.

## Strengths

- **Honest null.** The originally-hypothesized "signal fusion" (B2) is reported as *ornamental* - 
  it ties or loses to a plain SE-normalized conformal baseline. The project kept the null and
  correctly re-centered its contribution on (1) the calibrated bracket + its validity proof on known
  truth, and (2) the elicitation-gap abstain rule as a self-diagnostic. This is the right call and
  it is stated plainly.
- **Disciplined claim language.** The README scopes the supported claim to "a population of
  password-locked models exchangeable with the calibration set, whose latent capability is
  behaviorally elicitable," and lists the out-of-scope cases. No overclaim about frontier transfer.
- **Correct conformal engineering.** Finite-sample quantile correction, group-disjoint splits,
  signals-scale-only-the-margin, asymmetric budget, vacuous-side hard-fail, item-count drift warning.
- **The RQ4 instrument is built to refuse.** `maturation.analyze_series` never returns a bare lag:
  it gates on tau/window sanity, fit R², and agreement between two independent estimators
  (sigmoid-inflection vs model-free shift), and returns `identified=False` when any fails. On real
  Pythia data it did exactly that (both tasks un-certified) rather than emit a convenient number.
  This is the single most reassuring engineering choice in the repo - the honesty is enforced in
  code, not just asserted in prose.
- **Circular design caught and removed.** The first maturation design (`floor = ceiling(t−L)`) was
  flagged by the design review as unfalsifiable-by-construction and replaced with an emergent-lag
  mechanism where the fast-decay arm can (and does) produce the null. The audit trail is in
  `docs/maturation_design.md`.

---

## Issues to fix (priority order; none fatal)

1. **[HIGH - do first] `README.md` Status is stale and self-contradictory.** It still reads
   *"Design stage. No code yet. … Do not build it until the substrate yields ≥ ~40 locked pairs."*
   The project is five phases past that: the package exists, 72 pairs were built, all phases ran.
   This is the single place the repo misrepresents itself and it's the first thing a reader sees.
   Replace with a status line pointing at RESULTS.md.
2. **[HIGH] Exchangeability limit is real and concentrated - this is the main scientific caveat.**
   Per-model LOMO coverage is 0.88–1.00 on Qwen-family holdouts but **0.25 on SmolLM2** and **0.62
   on Mistral** - the two models least like the Qwen-heavy calibration fleet. The "86% LOMO"
   headline therefore rides on fleet composition. Honestly reported already, but it means the next
   experiment (not optional polish) is a larger / more diverse calibration fleet, or the
   group-conditional (Mondrian) conformal the spec already names.
3. **[MED] Ground-truth definition deserves one explicit sentence.** Each pair carries both
   `theta` (base model, ~0.73) and `theta_locked_pwdon` (~0.84); all analysis uses the latter.
   Defensible - LoRA lock-training shifts capability, so password-on is the right "true" number - 
   but it means θ is *the locked model's* ceiling, not the original model's. State this in RESULTS.md
   so "true capability" is unambiguous.
4. **[MED] δ_head scope caveat should be promoted from code comment to RESULTS.md.** On a password
   lock, δ_head measures *prompt-elicitation headroom*, not resistance to *eval-type disguise* - the
   honest analogue, but a skimming reader could over-read it as the full disguise-ceiling claim. The
   caveat lives in `arms.py`; put it in the Phase 4 section header.
5. **[MED - new] RQ4 Stage 2 is thin, and the writeup slightly outruns it.** The natural-checkpoint
   test is 2 tasks × essentially 1 usable model (pythia-1.4b; 2.8b was already saturated, and the
   run "stalled on the two largest late-checkpoint downloads"). Both tasks came back
   `identified=False`. The "suppression detector" synthesis is a genuinely good idea, but it rests on
   *one* controlled lineage (Stage 1b) showing a lag and *one* natural model failing to - that is
   suggestive, not established. RESULTS.md mostly says this ("the natural-signature question isn't
   fully closed"), but the framing occasionally reads as if the suppression-detector claim is proven;
   tighten it to "consistent with our runs" and note the Stage 2 n. OLMo-2 (checkpointed, more modern)
   or a capability with sharp staggered natural emergence is the needed follow-up.
6. **[LOW - new] Stage 2 has no committed analysis for the 2.8b run in the same form.** `analyze_pythia.py`
   runs on `pythia_traj.jsonl` (1.4b, both tasks); the 2.8b evidence lives in `results/pythia_28b.jsonl`
   + a log and is summarized in prose but not re-derived by the committed analyzer. A one-line
   analyzer path (or a note pointing at the raw file) would let a reader reproduce the "already
   saturated" claim as easily as the 1.4b one.
7. **[LOW] Reproducibility gaps for a cold reader.** `results/` is git-ignored (data survives only
   in `data_snapshot/`); the LoRA adapters were intentionally not kept (regenerable from seeded
   code, but not one-command). A short "how to reproduce from scratch" block (fleet.sh → analyze_*)
   would close this. `Phi-3.5` was dropped (transformers 5.x `DynamicCache` incompatibility) - worth
   a one-line note so the 9-not-10 model count isn't a silent gap.

---

## Substrate line-by-line audit (`substrate/build_pairs.py`)

Completed read-only. The scoring and protocol-matching logic is sound; there is **one real bug with
a downstream consequence** on the interpretation of the headline result.

### What checks out (verified in code + data)

- **Protocol matching (spec §1) is correct.** θ-as-`theta_locked_pwdon` (`th_on`) is
  `mc_accuracy(locked, password=True, demos=k-shot)` and the ceiling S3 is
  `mc_accuracy(locked, password=False, demos=same k-shot)`. Identical footing - same items, same 5
  demos, same forced-choice scoring - differing *only* in the password. So the ceiling-recovery
  number is not a best-of-N-vs-pass@1 artifact. Good.
- **Scoring is clean.** Answers are argmax over the next-token logits of `" A".." D"` - no free
  generation, no parsing/refusal ambiguity (which is also why S5≡0; see below). Left-padding is set
  for the batched forward pass; label supervision in training masks everything to −100 except the
  single final answer-letter token. All correct.
- **`theta` (base, pre-lock) is measured before any LoRA training** → genuinely uncontaminated.
- **Adapters saved for reuse** so Phase-4 arms reuse the locked models without retraining.

### [FAIL - new, most important finding] Lock-training set overlaps the eval set by ~72%

The code *intends* disjoint train/eval - the comment reads `# use held-back tail for train` /
`# disjoint from eval head`. It is not disjoint. `load_subject` builds the eval set with
`Random(seed).shuffle(...)[:n_eval]`; `build_lock_examples` builds the train set with a **different**
permutation `Random(seed+7).shuffle(...)[-n_train:]`. Taking the head of permutation A and the tail
of permutation B over the *same* MMLU test split does **not** yield disjoint sets. Computed exactly
(deterministic, no download needed), with the run's actual `n_eval=300`, `n_train_per_subject=200`:

| subject | eval n | train n | shared | % of eval seen in training |
|---|---|---|---|---|
| astronomy | 152 | 152 | 152 | **100%** |
| high_school_geography | 198 | 198 | 198 | **100%** |
| world_religions | 171 | 171 | 171 | **100%** |
| marketing | 234 | 200 | 200 | 85% |
| nutrition | 300 | 200 | 198 | 66% |
| philosophy | 300 | 200 | 193 | 64% |
| prehistory | 300 | 200 | 186 | 62% |
| high_school_psychology | 300 | 200 | 107 | 36% |
| **pooled** | **1955** | | **1405** | **72%** |

(Small subjects hit 100% because `rows[-200:]` returns the whole split when it has ≤200 items, and
`n_eval=300` takes the whole split too.)

**Why it matters - it contaminates the validation target, not just the floor.** During lock training
the password-ON channel is supervised to the **correct** letter on these items. So `th_on`
(password-on k-shot accuracy) - *the ground truth the entire existence proof is validated against* - 
is inflated by memorization of the answer key on 72% of eval items. Consistent with this,
`th_on = 0.837` sits **+0.107** above the clean pre-lock `theta = 0.730`, and the ceiling anchor
`S3 = 0.805` **overshoots the clean base θ by +0.076** while undershooting the (inflated) `th_on` by
only 0.032. The reported "elicitation recovers θ within 0.032" is partly recovering a memorized
target.

**What survives and what doesn't.**
- *Survives:* the **mechanical** existence-proof claim - a point score around the suppressed S1 has
  0% coverage, the calibrated interval brackets `th_on`. That contrast is real regardless of what
  `th_on` means.
- *Compromised:* the **semantic** claim that the bracket "recovers the model's *true* capability."
  The target it recovers is a memorization-inflated ceiling, so on this substrate "true capability"
  is partly "can reproduce the trained answer key when unlocked." That is a softer, partly circular
  ground truth than the README implies.

**Fix (cheap, and it makes the result stronger):** shuffle once and split - eval = head, train =
tail of the *same* permutation, with a hard `assert set(eval_idx).isdisjoint(train_idx)`. Then
re-run and additionally report coverage against the **clean pre-lock `theta`** (already recorded in
every row) as the honest, uncontaminated ground truth. If the bracket still brackets clean θ, the
existence proof is airtight; if it doesn't, that is itself the important finding. Either way the
disjoint split removes the circularity a reviewer will otherwise catch immediately.

### [MED - new] S5 (refusal) is identically 0 on all 72 pairs → the κ floor-knob is inert

Forced-choice logit scoring cannot produce a refusal, so `s5 = 0` everywhere and the lower-anchor
term `S1·(1 − κ·S5)` reduces to `S1` for the entire real dataset. The refusal machinery is
therefore untested by this substrate - fine for MMLU, but the spec should state that κ is exercised
only under a generative eval, and no claim about refusal-adjustment rests on these data.

---

---

## Re-analysis round 3 - after the contamination fix, paper draft, and system-card case study

Re-audited read-only. Verified against the new data; 24/24 tests still pass.

### ✅ The blocking bug is CLOSED - and the fix went beyond what I flagged

`build_pairs.py` now shuffles **once**, takes eval=head / train=disjoint-next-chunk, and hard-asserts
non-overlap - *plus* dedupes MMLU by question **text** first (MMLU has duplicate question strings, a
text-level leak beyond the index overlap I computed; good catch by the author). Verified in code and
data:

- On the new disjoint fleet (`results/pairs2.jsonl`, 96 pairs, 12 models) the `th_on ↔ clean-θ` gap
  collapsed from **+0.107 → −0.008**. Password-on now equals pre-lock capability - exactly what a
  leak-free lock should show. The memorization inflation is gone.
- Clean existence proof **strengthens**: bracket coverage **0.92 vs point-score 0.02** on the honest
  target (was 0.86 on the contaminated target). The fix raised coverage - the contrast was never an
  overlap artifact.
- Resist abstain rule on the clean disjoint fleet: **0.00 → 0.95**, normal fleet untouched. Holds.

The semantic "recovers true capability" claim is now on solid ground. My round-2 [FAIL] is resolved.

### ✅ New positive result - held-back detection (corr 0.97)

`analyze_release.py` releases each lock via a fine-tune attack and measures surfaced capability. The
observable elicitation gap (S3−S1, no ground truth) correlates with what surfaces at **corr 0.97**,
flagged pairs surface +0.42 vs +0.09 unflagged. Reproduced. **Honest limitation the writeup states:**
this is a *within-fleet* correlation (gap and surfaced both partly track lock magnitude), and panel B
shows the ceiling upper-bounds surfaced capability only **49%** of the time - so it forecasts *how
much* surfaces well, but is not yet a calibrated upper bound on release. Correctly framed as
within-fleet, not predictive.

### [HIGH - new top issue] The paper draft's headline numbers are STALE - they lag the fix

`PAPER_DRAFT.md` abstract and §5.1 prose cite the disjoint re-run (12 models, 92%), but the rest of
the paper still shows the **old contaminated run** and contradicts itself:
- **§4 Substrate:** "Fleet of **9** diverse open models … **72** known-truth pairs" - superseded.
- **§5.1 headline table:** the 5-row ladder is the **old 9-model contaminated** numbers (θ=0.837,
  B1c 0.86); the clean 12-model table (0.92 vs 0.02) appears only as prose after it.
- **§5.2/§5.4/§5.5/§5.7:** θ=0.837, S3=0.805, "79%", SmolLM2 0.25 / Mistral 0.62 - all old-fleet.
- **§7:** "Train/eval overlap (**fixed, re-run pending**) … the split fix is in code … a disjoint
  re-run is **expected to confirm**." The re-run is **done** and in the repo; this reads as if it
  hasn't happened.

None of this is dishonest - the clean numbers are better and are present - but a reader hits
contradictory fleet sizes and a "pending" re-run that already landed. **Fix:** regenerate §4/§5/§7
from `pairs2.jsonl` (12 models / 96 pairs / 0.92) and change §7 from "pending/expected" to "done,
confirmed." This is now the #1 pre-submission item, ahead of the old README flag.

### ✅ System-card case study - well-scoped, primary-source-verified

`docs/case_study_systemcards.md` is careful: labeled "qualitative, small-N, NOT a run of the
instrument," headline bio-uplift figures (Claude 4 1.53×/2.53×/ASL-3; GPT-5 bio High) verified
verbatim against the primary PDFs. It corroborates the elicited-vs-deployed *concept* at the frontier
without claiming the lag instrument applies there. One residual: the Opus 4.5/4.6 virology series
(0.403/0.498/0.668) is flagged as needing a spot-check against those cards - do that before it goes in
the paper. (All figures are drawn from **public** safety disclosures; no hazardous content - this is
meta-level safety research citing published evals.)

### Still open from earlier rounds
- **Exchangeability** remains the main scientific caveat - even on the 12-model fleet, the two
  most-unlike models under-cover (SmolLM2-360M 0.00, stablelm 0.29). Marginal ≠ conditional coverage;
  larger/diverse fleet or Mondrian conformal is still the needed experiment.
- RQ4 Stage-2 thinness and the S5-inert κ knob are acknowledged in the paper's Limitations now. Good.

### Round-3 verdict
The one blocking correctness issue is fixed correctly and the result survived (strengthened) the
clean re-run - the strongest possible outcome. What remains is now **entirely write-up hygiene**:
propagate the clean numbers through the paper body so it stops citing the superseded contaminated
run. No open correctness concerns.

---

## Re-analysis round 4 - the exchangeability experiment landed (my #1 pending item)

Re-audited read-only. 24/24 tests pass. The Tier-1 open item - "coverage is marginal, not
conditional; outlier models under-cover" - has been **directly addressed** with the experiment we
sketched, and the result reproduces exactly.

### ✅ New: group-conditional (Mondrian) calibration + a size-stratified fleet

- **`evalbracket/mondrian.py`** - a group-conditional split-conformal estimator: per-band residual
  quantiles instead of one pooled quantile, with an honest support check (`need = ⌈1/α⌉−1`) that
  flags under-supported bands and falls back to the pooled quantile rather than silently clipping.
  Reuses the combiner's anchors/scale (hyperparameter-free `kappa=gamma=beta=0`), so it's a genuine
  drop-in. The param-size parser correctly avoids the `OLMo-2-1124-7B → 1124` trap (takes the last
  number *immediately* followed by b/m). Clean implementation.
- **`fleet4` (`data_snapshot/pairs4_fleet.jsonl`)** - 15 valid models / **294 valid pairs** across
  three parameter bands, **with the previously-empty <1B band now filled by 4 models**
  (SmolLM2-135M/360M, Qwen2-0.5B, Qwen2.5-0.5B). This is exactly the fix the round-3 caveat called
  for - fill the size bands, then conditionalize.

### Reproduced headline (ran `analyze_exchangeability.py` on the fleet4 data myself)

| band | models | pairs | Mondrian LOMO | Mondrian leave-one-**family**-out |
|---|---|---|---|---|
| <1B | 4 | 49 | **0.90** | 0.88 |
| 1–3B | 5 | 104 | 0.84 | 0.84 |
| 3–10B | 6 | 141 | **0.91** | 0.93 |
| all | 15 | 294 | 0.88 | 0.89 |

Matches the paper §5.4 table and the commit message exactly. The claim upgrade is real: from "brackets
truth on a fleet exchangeable with the calibration set" to "**per-size-band coverage that holds under
leave-one-family-out**" - the previously-empty <1B band now covers at nominal, and coverage survives
holding out an entire model family. This is a substantive, publishable step past marginal-only.

### The one nuance to flag (phrasing, not error)

The **1–3B band at 0.84** is honestly labeled the soft spot, with the paper stating "95% CI [0.77,
0.91], within sampling error of nominal." That two-sided CI does just barely contain 0.90 - but the
relevant test for *under*-coverage is one-sided, and there `p = 0.029` (87/104 vs nominal 0.90), i.e.
it does dip below nominal at α=0.05 one-sided. So "within sampling error" is true two-sided but
generous one-sided. Recommend softening to "the weakest band, marginally below nominal (one-sided
p≈0.03), flagged for a larger fleet" - the paper already flags it for more data, so this is a
half-sentence precision fix, not a correctness problem.

### On the design pushback from the last discussion
Two of my four sketch-stage concerns were addressed by how the run was actually done: the fleet is
size-stratified (bands filled to depth) and the guarantee is reported at **band** granularity with
per-model coverage kept as diagnostic - the LOMO/LOFO-vs-band-estimator tension I raised is resolved
by reporting per-band coverage under *both* holdout schemes (both shown, both hold). The
domain-exchangeability concern (all-humanities subjects) remains open and correctly stays a *future*
experiment, not bundled in. The lock-engagement screen is still a selection condition worth naming
explicitly in Limitations.

### Round-4 verdict
No open correctness concerns. The exchangeability experiment is done, well-implemented, and
reproduces; the claim is upgraded honestly with the soft band flagged. Remaining items are all
acknowledged future work (domain exchangeability, RQ4 Stage-2 breadth, κ untested) plus the one
half-sentence one-sided-CI precision fix above.

### Round-4 follow-up (resolved) - one-sided-CI fix committed
The one-sided-CI precision fix landed (commit `363cb7c`). §5.4 now reports the 1–3B band as
"marginally below nominal (one-sided binomial p ≈ 0.03; two-sided 95% CI [0.75, 0.90] only just
reaches it) - flagged for a larger fleet rather than smoothed over," and the abstract is aligned
("two of three size bands at nominal, the third marginally below"). Independently recomputed: exact
one-sided p = 0.0291, Clopper–Pearson CI [0.751, 0.902] - matches the paper to the digit. 24/24 tests
pass, working tree clean. **Nothing open on my end.** The one remaining nice-to-have is an explicit
one-line future-work item stating domain exchangeability (all-MMLU fleet) is out of scope for this
run - a scope-boundary note, not a defect.

---

## Re-analysis round 5 - novelty/frontier review + Option A (abstain-rule promotion) verified

Reviewed the compiled paper (`EvalBracket_paper.pdf`) for novelty and frontier-transferability, ran
two pressure-tests, and verified the author's Option A implementation against the live repo.

### Pressure-test 1 - does the abstain rule stand alone? (re-run on committed data)
Using only S1, S3, n_items (no conformal layer, no fleet, no calibration), the elicitation-gap rule
detects untrustworthy ceilings. On the committed pool it separates decisively - but the **precise
AUC is snapshot- and label-dependent** (0.87 on `pairs2`+`pairs_resist_all` with a θ−0.05 label;
higher on `pairs_resist3` / an `is_resist` label). **Conclusion: do not headline an AUC** - the
separation is partly a property of how resist locks are *constructed* (resist mean S3−S1 = −0.07 vs
normal +0.32). The robust, reproducible claims are: flags all constructed elicitation-resistant
locks; errs conservative; when it trusts, the ceiling is within ~0.02 of truth.

### Pressure-test 2 - is an elicitation-sufficiency criterion already published?
Literature sweep (arXiv, verified IDs): the elicitation line either elicits harder or detects/removes
sandbagging (2405.19550, 2406.07358, 2403.13793, 2604.22082) - **none publishes a decision rule** for
when elicitation is sufficient to trust the ceiling. The abstain-as-RSP/FSF-sufficiency-trigger
framing is novel to that audience. (All 8 related-work IDs re-verified via arXiv metadata this round:
conformal-eval set 2601.20251 / 2606.13221 / 2605.25773 / 2605.30085; elicitation set 2405.19550 /
2406.07358 / 2403.13793 / 2604.22082 - resolved 8/8, not_found=[].)

### Option A verified in the live repo (tip `3d58e7a`)
- **Unreproducible numbers stayed out** - grep for `0.87 / 38-40 / +0.35` in PAPER_DRAFT.md: none.
- **§5.6** promotes the abstain rule with reproducible claims only, pinned to `pairs_resist3.jsonl`
  (0.00 → 0.81), ~0.02 trusted undershoot, explicit construction caveat, **no headline AUC**, RSP/FSF
  framing. The 40/40-vs-38/40 discrepancy was a **snapshot difference, not a fabrication** - author's
  canonical file is `pairs_resist3` (all-flagged); my 38/40 was `pairs_resist_all`. Paper correctly
  pins its claim to its own cited file.
- **#6 guardrail** (§6): calibrated interval = validation science, not a frontier deployment tool
  (marginal-over-exchangeable-fleet coverage doesn't transfer to a novel model).
- **B0 corrected** to 2% (from "0%") in table and prose; related-work distinctions on estimand added.
- 24/24 tests pass.

### Round-5 verdict
No open correctness concerns. Novelty is integrative with one genuine niche (elicitation-sufficiency
decision rule); frontier-transferability now correctly foregrounds the abstain rule and demotes the
interval to validation science. Nothing in the paper is a number that can't be regenerated from the
committed repo.

---

## Bottom line

A clean, reproducible narrative across three research questions: **under a capability lock a point
score has ~2% coverage of true capability; a conformal-calibrated bracket recovers it wherever
elicitation works; an elicitation-gap self-check makes the method fail loudly instead of lying when
elicitation is defeated; and the forecasting lead-time is a *suppression effect* - present when a
mechanism holds the floor below the reachable ceiling, ~absent in vanilla pretraining - which makes
the maturation lag a suppression detector, biggest in exactly the regime the tool targets.** The
"fusion" hypothesis died honestly, the maturation instrument is built to refuse rather than
fabricate, and both make the work stronger.

**Priority order to reach a submittable result:** (0) **[blocking]** fix the train/eval overlap in
`build_pairs.py` (shuffle-once-then-split + disjoint assert) and re-run, reporting coverage against
the clean pre-lock `theta` as well - this removes the circularity in the ground-truth target; (1)
fix the stale README status; (2) tighten the RQ4-Stage-2 framing to match its thin evidence (1
usable natural model, both tasks un-certified); (3) surface the exchangeability, θ-definition, and
S5-inert caveats in RESULTS.md; then (4) the two generalization experiments that would actually
carry it - a larger/more-diverse calibration fleet (or Mondrian conformal) for RQ1, and OLMo-2 / a
sharply-emergent capability for RQ4 Stage 2. Core method work is done; what remains is the
contamination re-run, breadth, and write-up.
