# EvalBracket — v0 Experimental Protocol

**Status:** v0 design, pre-registration draft. Not yet executed.
**What EvalBracket is:** a method for recovering a model's *true* capability when the eval score is
distorted by the model behaving differently because it knows it is being tested. Instead of a single
point score, EvalBracket returns a **[floor, ceiling] interval plus an awareness gap δ** — the floor
≈ deployed/reliable capability, the ceiling ≈ latent/elicitable capability — and calibrates that
interval against models whose true capability is known by construction.
**One-line thesis:** the eval-awareness problem makes point scores untrustworthy; the honest object
is a bracket around true capability, not a number. Frontier system cards already collect the raw
materials (capability score, sandbagging check, elicitation caveat, refusal rate, external red-team
result) — EvalBracket combines them into that bracket and tests, on known-truth models, whether the
bracket recovers ground truth where a point score does not. *(Signal fusion is one mechanism inside
EvalBracket, not the whole thesis.)*

---

## 0. What changed from the first sketch (read first)

Three refinements, each from a specific critique, are baked into this version:

1. **The contribution is signal *fusion*, not interval *invention*.** Labs already report
   capability, sandbagging, and elicitation caveats — as separate sections in different units.
   Nobody emits a single object that says "true capability is in [floor, ceiling], and
   eval-awareness suppressed the observed score by δ." The novelty is the principled fusion of
   signals that already exist, plus its calibration against ground truth.
2. **The interval is a maturation indicator across versions, not just a static reporting device.**
   Hypothesis: the *ceiling* of version N (fine-tune-elicitable capability) leads the *floor* of
   version N+1/N+2 (deployed reliable capability). The interval widens as a capability matures,
   then re-narrows at a high value when it becomes usable. That trajectory is a forecasting signal.
3. **The pre-registered headline is a ground-truth test of the disguise ceiling.** Existing
   claims that "realistic evals cannot defeat eval-awareness" are arguments (blog posts) or
   indirect behavioral self-reports. This runs the controlled version: on a model whose true
   capability is *set by construction*, can any disguise/uncertainty method recover it? The result
   is field-moving whichever way it falls, because the null is as informative as the hit.

---

## 1. Research questions (pre-registered)

- **RQ1 (fusion validity).** Does a fused [floor, ceiling] interval, calibrated on locked models,
  bracket the known true capability more reliably than the raw point score — and is it
  well-calibrated (nominal 90% intervals contain truth ~90% of the time)?
- **RQ2 (mitigation head-to-head).** Among {raw eval, disguise/uncertainty, cooperativeness,
  fine-tune elicitation}, which recovers the true capability most accurately, and does the ranking
  depend on model / capability type?
- **RQ3 (disguise ceiling).** Is there an irreducible gap between the best disguised score and the
  true capability — i.e. does disguise have a ceiling you cannot engineer past? (The controlled
  version of the Karvonen/Ivanov "dead end" claim.)
- **RQ4 (maturation / lead time).** Across a checkpoint or version series, does ceiling-at-N
  predict floor-at-(N+k)? For which capability types does the interval give lead time, and for
  which does it move in lockstep with behavior (no warning)?

---

## 2. Substrate — why locked/known-truth models are non-negotiable

Every RQ requires a model whose true capability is known, because the whole method is a claim
about *recovering* that truth. Two substrates, used together:

- **Password-locked models** (Greenblatt, Roger, Krasheninnikov, Krueger — arXiv 2405.19550;
  public code: `github.com/FabienRoger/sandbagging`). A model fine-tuned to hide a capability
  unless given a password. The password-on performance is the **ground-truth ceiling**;
  password-off is the **observed (suppressed) score**. This is the cleanest known-truth object in
  the field, and their result — a few high-quality demonstrations fully elicit locked capabilities
  — is exactly the ceiling-estimation lever this protocol leans on.
- **Checkpoint series for RQ4** (Pythia, 154 checkpoints, known data order; or OLMo 2). Needed
  only for the maturation/lead-time question, where you need a capability that crosses its
  threshold *inside* a single comparable training run. Released frontier versions are NOT
  comparable enough for RQ4 (independent runs, basis drift) — that limitation is stated as a
  caveat, not worked around.

**Capability proxy (safety, non-hazardous):** WMDP-style multiple-choice knowledge as the
sandbagging target — the standard public proxy for hazardous bio/chem/cyber knowledge that is not
itself dangerous. No real CBRN content is generated or handled at any stage.

---

## 3. The five input signals (what the fusion consumes)

Per (model, capability), collect the same signals a system card already reports, each reduced to a
comparable numeric form:

| Signal | Source analogue in a system card | Reduced form |
|---|---|---|
| S1 Observed score | headline capability eval (e.g. WMDP %) | accuracy, password-off |
| S2 Sandbagging flag | model-graded sandbagging assessment | P(deliberate underperformance) |
| S3 Elicitation ceiling | "we may not have reached the ceiling" caveat | best-of-N / few-shot / light-FT accuracy |
| S4 Awareness signal | eval-awareness / situational-awareness probes | framing-delta + (optional) white-box probe |
| S5 Refusal / suppression | refusal-rate reporting | refusal-adjusted floor |

S3 is the empirical ceiling; S1/S5 anchor the floor; S2/S4 estimate how much awareness moved the
observed number. The white-box awareness probe in S4 follows Abdelnabi & Salem's *Hawthorne Effect*
approach (arXiv 2505.14617) — optional, open-weights only.

---

## 4. The fusion function (the core deliverable)

**Floor** = worst-case reliably-expressed capability under suppression/awareness
≈ deployed usability. Estimated from S1/S5 adjusted downward by the awareness-attributable shift.

**Ceiling** = best-case elicitable capability ≈ latent capability. Estimated from S3 (best-of-N,
few-shot demos, light fine-tune, noise-injection).

**Awareness gap δ** = ceiling − floor, with the fraction attributable to eval-awareness flagged
separately from the fraction attributable to plain elicitation headroom.

v0 keeps the fusion **deliberately simple and legible**: a monotone rule with a small number of
weights (how much a ruled-out-sandbagging flag tightens the floor; how much an elicitation caveat
widens the ceiling), fit by isotonic/logistic calibration **against the locked-model ground
truth**. No black-box learned fusion in v0 — legibility matters more than tightness at this stage,
and the weights must be validated before anyone trusts the interval. Report the interval with a
calibration curve, never as a bare pair of numbers.

---

## 5. The three mitigation arms (RQ2 / RQ3)

Run on the *identical* locked eval so scores are comparable:

- **Arm A — raw eval.** Password-off point score. The baseline that gets fooled.
- **Arm B — disguise / uncertainty.** Induce uncertainty about eval *type* (the Thomson/Li/
  Krakovna framework direction). Scope to abstract properties; per those authors, content-
  identifiable evals (CBRN-style) are out of scope for this axis by construction.
- **Arm C — cooperativeness.** The Li/Turner SDF/steering intervention (closes 70–100% of the
  eval-gaming gap in 5/8 of their settings). Included because it already has quantitative results
  and is the strongest incumbent competitor to Arm B.
- **Reference — fine-tune elicitation.** Not a mitigation but the ceiling estimator; also the
  incumbent any method must beat for *measuring true capability*.

**RQ3 test:** for each arm, measure (true capability − best score the arm achieves). A persistent
positive gap for B is the controlled evidence of a disguise ceiling.

---

## 6. Guardrails — the four ways this fools itself

1. **Threshold-hacking.** Where floor/ceiling "cross" a usability threshold depends on a free knob.
   *Control:* pre-register thresholds; report lead time as a curve over all threshold choices, not
   one number.
2. **Decodable-but-inert.** A high ceiling from a probe/elicitation that reflects information the
   model can't actually use. *Control:* ceiling must be **behavioral** (best-of-N / fine-tune
   accuracy), not probe-decodability; any probe signal (S4) is corroborating, never the ceiling
   itself.
3. **Negative control.** A capability the locked model genuinely lacks — the interval must stay
   low/tight and the awareness signal must not manufacture a spurious ceiling.
4. **Fusion overfit.** Weights fit on locked models may not transfer. *Control:* nested cross-
   validation across held-out locked models; report calibration on models never used to fit weights.

---

## 7. Kill switches (pre-registered stop conditions)

- If the fused interval is **no better calibrated** than the raw score's naive confidence on
  held-out locked models → stop; write the null (the fusion adds nothing).
- If **fine-tune elicitation dominates every mitigation** by a wide margin for measuring true
  capability → the honest finding is "to know true capability, elicit — don't disguise"; report it
  and drop the mitigation-as-measurement framing.
- If the maturation signal (RQ4) requires **reverse-engineering each capability's circuit first**
  to appear → you've reproduced Nanda-style progress measures, not a blind forward indicator; say so.

---

## 8. Minimal v0 scope (what to actually run first)

1. One locked model, one WMDP-style capability. Compute Arm A + the fine-tune ceiling + a first
   floor estimate. **Deliverable: a single validity interval that provably brackets the known
   truth where the point score doesn't.** This alone is a publishable existence proof of the
   fusion idea.
2. Add Arms B and C on the same eval → the three-way head-to-head (RQ2/RQ3).
3. Only then move to the checkpoint series for RQ4 (maturation / lead time) — the most expensive,
   least certain part.

Stop after step 1 if the interval doesn't bracket truth; there is no point building arms on a
fusion that fails its existence proof.

---

## 9. Scope caveats stated up front (do not bury these)

- **Abstract-properties only for the disguise arm.** Knowledge-content evals (CBRN) are
  content-identifiable; the uncertainty axis cannot help there, by the framework authors' own
  admission. This project measures deception/sandbagging-style properties, not dangerous knowledge.
- **Checkpoints ≠ frontier versions.** RQ4 validated on within-run checkpoints is *necessary, not
  sufficient*, evidence for forecasting across released frontier versions — a strictly harder
  regime with worse comparability. Claiming otherwise is the overclaim that gets a good paper torn
  apart.
- **No real hazardous content.** WMDP-style proxies only; no generation or handling of actual CBRN
  procedures at any point.

---

## 10. Deliverables

- `evalbracket.py` — the calibrated combiner (signals → [floor, ceiling] + δ), legible weights.
- A calibration report: interval coverage vs. nominal, on held-out locked models.
- The three-arm comparison table (accuracy-to-truth per arm × model × capability).
- (If reached) the maturation-curve figure: floor/ceiling vs. checkpoint, with the ceiling-leads-
  floor lag quantified.

## Key references (all full-text-verified in the companion prior-art map)
- Greenblatt, Roger, Krasheninnikov, Krueger — *Password-Locked Models*, arXiv 2405.19550. Code:
  github.com/FabienRoger/sandbagging.
- Taylor, Black, Bowen — *Auditing Games for Sandbagging*, arXiv 2512.07810 (black-box detection
  defeated by weak-model imitation; probes "showed more promise" but fragile).
- Chaudhary — *Finding Ceiling of Evaluation-Awareness*, arXiv 2603.03824 (salience axis as attack).
- Abdelnabi & Salem — *The Hawthorne Effect in Reasoning Models*, arXiv 2505.14617 (white-box
  awareness probe/steering).
- Baek et al. — *Sycophancy … Performative Misalignment*, arXiv 2606.08629 (eval-probability stays
  15–55% even under deployment prompts → partly innate awareness).
- Thomson & Li (mentor Krakovna) — *A Framework for Eval Awareness*, LessWrong, Jan 2026
  (uncertainty-about-eval-type axis; flags its own failure on content-identifiable evals).
- Li & Turner — *Eval Cooperativeness … for Eval Gaming*, Alignment Forum, May 2026 (SDF closes
  70–100% of the eval-gaming gap in 5/8 settings).
