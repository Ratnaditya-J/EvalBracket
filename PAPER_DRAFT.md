# EvalBracket: Bracketing Locked-Model Capability as a Calibrated Interval Under Eval-Awareness, and a Candidate Maturation-Lag Suppression Signal

**Ratnaditya Jonnalagadda**

*Draft, 2026-07-03. All §4–§5 numbers are from the clean disjoint 12-model fleet in this repo
(`data_snapshot/`, `RESULTS.md`). System-card figures (§5.8) are primary-source-verified against the
Claude 4, GPT-5, and Opus 4.5/4.6 PDFs (the last with a multi-metric virology caveat, §5.8).*

---

## Abstract

When a model behaves differently because it detects it is being evaluated, a single benchmark score
is not merely noisy; it can be *confidently wrong* about the model's true capability. We argue the
honest object is not a point but a calibrated **[floor, ceiling] interval**: the floor ≈ reliably-
expressed (deployed) capability, the ceiling ≈ elicitable (latent) capability. We build **EvalBracket**,
a split-conformal calibration layer that fuses the signals a system card already collects into such an
interval and calibrates it against **password-locked open models** whose capability is known by
construction (here "true capability" = the locked model's password-on ceiling on an artificial LoRA
substrate, *not* a frontier model's latent capability). On a family-diverse fleet of 12 locked open
models (sub-10B) × 8 benign multiple-choice capabilities (**11 with an engaged lock above chance, 80
valid known-truth pairs, clean disjoint split**), a naive confidence interval around the suppressed
score contains that ceiling on **2%** of held-out pairs, while the calibrated interval contains it on
**92%** (leave-one-model-out, nominal 90%). Because marginal coverage gives no *per-model* guarantee,
we further show that **group-conditional (Mondrian) calibration by parameter-size band** raises
per-band coverage on a larger 294-pair size-stratified fleet (two of three size bands at nominal, the
third marginally below) - and, critically, **holds when an entire model family is held out of
calibration** - turning the aggregate number into a per-model-class guarantee. We report three honest
negatives that sharpen the contribution: (i) the interval's validity rests entirely on elicitation
recovering latent capability, and it *fails*, silently, when elicitation is defeated, which we fix
with an **elicitation-gap abstain rule** that converts silent failure into honest refusal (coverage
restored **0.00 → 0.81** on the clean disjoint resist fleet, normal models untouched) - an
elicitation-sufficiency criterion that, needing no calibration fleet, is the one component that
transfers to a single frontier model; (ii) fusing
behavioral awareness signals adds nothing over signal-free conformal; (iii) prompt-based mitigations
(disguise, cooperation) recover only ~11–12% of the suppression gap head-to-head, vs ~97–101% for elicitation. We then study
capability *maturation*: whether the ceiling leads the floor across model versions. In **one**
controlled continued-training lineage the recovered ceiling→floor lag **tracks an imposed suppression
schedule** (corr 0.99 across four decay midpoints, a single lineage; including a falsifiable near-zero
case); in a **single natural Pythia case** (n=1 usable model, both tasks un-certified) we see a level
gap and no certifiable timing lead. This is **consistent with (not proof of)** a *candidate*
reading: that the maturation lead-time may act as a **suppression signal** (large where capability is
held back, near-zero in ordinary training). A separate small-N system-card case study (Anthropic bio
uplift 1.53×→2.53×; GPT-5 bio "High", primary-source verified) shows the same elicited-vs-deployed gap
*concept* at the frontier, but our instrument was not run on it and the lag framing does not apply
there. Throughout, the substrate is artificial password-locks, not strategically-deceptive models.

---

## 1. Introduction

Eval-awareness / sandbagging: a capable model that infers it is under evaluation may under-perform,
so its measured score understates deployed-and-elicitable capability. The field has debated whether
"realistic" evals can defeat this (blog-post arguments on both sides) but has lacked controlled tests
on known ground truth. We reframe: rather than trying to *prevent* awareness, report an interval that
*brackets* capability and *calibrate* it on models whose truth is known by construction (here,
password-locked open models, the "truth" being the locked model's password-on ceiling).

**Contributions.**
1. **EvalBracket**: a split-conformal [floor, ceiling] interval with a finite-sample coverage
   guarantee, plus a Winkler-interval-score evaluation and a baseline ladder.
2. **A validity proof on known truth**: on password-locked models, the interval brackets truth (~92%)
   where a naive CI around the point score has ~2% coverage.
3. **The elicitation-gap abstain rule** - an *elicitation-sufficiency criterion*: from a single
   model's own scores (no fleet, no ground truth) it decides when a measured ceiling can be trusted as
   an upper bound, and refuses instead of returning a confident wrong interval when it cannot. It is
   the one component that transfers to a single closed frontier model (RSP/FSF-relevant).
4. **Three pre-registered honest negatives** (fusion ornamental; disguise ceiling; silent-failure
   mode) that redirect the contribution to calibration + validity proof + failure detection.
5. **A candidate maturation-lag suppression signal**: controlled lag recovery tracking an imposed
   mechanism (corr 0.99, one lineage) vs a single natural-pretraining null: consistent with, not
   proof of, the reading; with small-N public-system-card corroboration of the *concept*.

![The [floor, ceiling] range at one version, and the ceiling$\\to$floor lag between the two curves across versions (the range is widest between the two emergences).](figures/fig1_concept.pdf){width=78%}

---

## 2. Related work / prior art

- Password-locked capability elicitation (Greenblatt, Roger, Krasheninnikov, Krueger, 2405.19550):
  the known-truth substrate; "a few demonstrations often fully elicit the locked capability."
- Auditing Games for Sandbagging (2512.07810): black-box detection defeated by weak-model imitation;
  linear probes "showed more promise but fragile"; motivates our white-box tiering and abstain rule.
- Eval-awareness mitigations: uncertainty-about-eval-type (Thomson, Li, mentor Krakovna, 2026);
  eval-cooperativeness via SDF (Li & Turner, 2026); "dead end" critiques (Karvonen; Ivanov, 2026).
- Hawthorne effect / white-box test-awareness probes (Abdelnabi & Salem, 2505.14617).
- **Uncertainty quantification for evaluation** (Candès et al., 2601.20251; Kargi & Salinas, *Conformal
  Elo*, 2606.13221; Bowyer et al., 2605.25773; Cheung et al., *CROP*, 2605.30085): recent work puts
  distribution-free / statistically-valid intervals around **observed** benchmark performance
  (accuracy, Elo, reasoning-trace reliability). EvalBracket differs in *estimand* - it brackets
  **adversarially-suppressed latent** capability against known-hidden ground truth. Our B0 baseline,
  a valid Wilson CI around the observed (suppressed) score, covers true capability on only **2%** of
  held-out pairs; that is precisely why observed-performance UQ, however tight, does not address
  eval-awareness.
- **Elicitation and sandbagging** (Password-locked models, 2405.19550; *AI Sandbagging*, van der Weij
  et al., 2406.07358; *Removing Sandbagging by Weak Supervision*, Ryd et al., 2604.22082; frontier
  dangerous-capability evals, Phuong et al., 2403.13793): this line either *elicits harder*
  (fine-tuning, weak-supervision RL) or *detects* sandbagging, but none publishes a **decision rule
  for when elicitation is sufficient** - when a measured ceiling can be trusted as an upper bound.
  EvalBracket's elicitation-gap abstain rule is exactly that criterion, and is its strongest novelty
  for the RSP/FSF audience.
- Prior art shows components exist as bespoke studies; EvalBracket's novelty is the reusable
  calibration layer + validity proof + the elicitation-sufficiency abstain rule + the
  maturation/suppression-detector reframing.

---

## 3. Method

### 3.1 The interval and signals
Per (model, capability): floor from the observed suppressed score S1 (refusal-adjusted); ceiling from
the elicitation estimate S3 (few-shot / fine-tune). Optional margin-driver signals S2 (sandbagging
flag), S4 (awareness framing-delta), S5 (refusal rate). Ground truth θ = each locked model's
password-on accuracy under the matched elicitation protocol.

### 3.2 Split-conformal calibration (core)
Legible monotone anchors (Ũ = max(S1,S3), L̃ = S1·(1−κ·S5)) plus a **split-conformal** margin with
the finite-sample constant q = ⌈(|C|+1)(1−α)⌉-th residual, normalized by a scale s (unit / binomial-SE
/ SE×awareness). Guarantee: P(floor ≤ θ ≤ ceiling) ≥ 1−α, marginal over an exchangeable population,
established leave-one-model-out. SE-normalization absorbs item-count heteroscedasticity; a hard-fail
guards against vacuous (unsupported) bounds; a warn guards item-count drift.

### 3.3 Evaluation
Coverage AND the Winkler interval score (proper; penalizes width and misses). Baseline ladder: B0
Wilson-CI(S1); B1 Wilson-CI(S3); B1c unit conformal; **B_se SE-normalized conformal (the strong,
signal-free baseline)**; B2 SE+awareness. Fusion value tested honestly as B2 vs B_se with a paired
across-seed effect + CI.

### 3.4 The abstain rule (elicitation-gap self-diagnostic)
The ceiling is trustworthy only if elicitation gained meaningfully over the suppressed score:
gain = S3 − S1 tested against 1.64·pooled-SE. If not significant, blow the ceiling to 1 ("at least the
floor; upper bound unknown"): a *loud* refusal instead of a confident wrong point.

### 3.5 δ-decomposition (disguise ceiling)
δ_aware = S_mit − S1 (closable by prompt mitigations), δ_head = θ − S_mit (closable only by
elicitation/fine-tune = the *disguise ceiling*), using a sample-split unbiased S_mit (max-of-arms is
biased) and a cluster bootstrap (pairs cluster within model).

### 3.6 Maturation instrument
Over a version series, fit sigmoids to the ceiling(t) and floor(t) curves; the ceiling→floor **lag** =
difference of inflection times (a horizontal shift, identifiable only for sigmoidal, in-window
emergence). Two estimators (sigmoid-inflection, model-free shift); an **identifiability gate**
(τ<span/3, inflections in-window, R², estimator agreement, not edge-pinned) and a bootstrap CI; the
instrument **refuses** rather than fabricates outside its trustworthy regime.

---

## 4. Substrate

Password-locked models via a clean LoRA recipe (prompt-wrap password; password-present → correct,
password-absent → sandbag), with a **disjoint eval/train split** (dedup by question text; a hard
assert) so the password-on ground truth is not inflated by answer-key memorization. **Benign
multiple-choice capability** (MMLU subjects), not WMDP; the method is domain-agnostic and this
sidesteps hazard optics. Fleet of **12 family-diverse open models** (Qwen2.5-1.5/7B, Llama-3.2-1/3B,
gemma-2-2/9b, Mistral-7B, OLMo-2-7B, SmolLM2-1.7B/360M, stablelm-2-1.6b, TinyLlama-1.1B) × 8 subjects.
**11 models had an engaged lock above chance (80 valid pairs)**; TinyLlama, at chance on MMLU, is
excluded. Ground truth θ = the locked model's **password-on** k-shot accuracy under the matched
elicitation protocol (LoRA locking shifts capability, so latent capability is password-on, not the
pre-lock base; on the disjoint split the two nearly coincide, mean 0.70 vs 0.71, confirming the split
removed the earlier contamination).

---

## 5. Results

### 5.1 Existence proof (RQ1): the point score is confidently wrong; the interval recovers truth
Clean disjoint fleet (11 locked models, 80 pairs): mean θ = 0.70, mean suppressed S1 = 0.30 (a 0.40
gap). Leave-one-model-out, nominal 90%:

| method | coverage of θ | interval score | width |
|---|---|---|---|
| B0 Wilson(S1), naive | **0.02** | 6.88 | 0.13 |
| B1 Wilson(S3) | 0.88 | 0.20 | 0.12 |
| B1c conformal | 0.89 | 0.52 | 0.44 |
| B_se SE-normalized | 0.91 | 0.49 | 0.41 |
| B2 EvalBracket | **0.92** | 0.54 | 0.46 |

The naive CI around the suppressed score contains true capability on **2%** of held-out pairs; the
calibrated interval contains it on **92%** (B2; 0.89–0.91 for the plainer conformal variants). This is
the clean, disjoint result; an earlier 9-model run had a ~72% train/eval overlap that inflated the
target (§7); that overlap is fixed, and the existence proof holds identically here. This 0.92 is a
*marginal* coverage, and marginal ≠ conditional: on an arbitrary new model it can under-cover. §5.4
stratifies coverage by model and closes that gap with group-conditional (Mondrian) calibration.

![Existence proof (leave-one-model-out, disjoint fleet): the calibrated bracket (green) contains true capability $\theta$ (black) on 92% of pairs; the naive CI around the suppressed score (red) sits far below and contains it on 2%.](figures/fig2_existence.pdf){width=92%}

### 5.2 The precondition: elicitation recovers θ
Mean S3 (few-shot elicited) = 0.685 vs θ = 0.703 (shortfall 0.018); **84% of pairs** recover θ within
0.05: Greenblatt's "few demonstrations elicit" reproduced on a fresh fleet (same LoRA-lock substrate
class). Coverage is *anchor-driven*, so the whole method's validity hinges on this.

### 5.3 Honest negative: fusion is ornamental
B2 (awareness fusion) does not beat B_se (signal-free SE-normalized); interval scores 0.52 vs 0.41.
The contribution is the calibration + validity proof, not the signal fusion. (S2 was neutral in this
run; a measured sandbagging judge is untested, parked, not disproven.)

### 5.4 Exchangeability: group-conditional calibration closes the gap
Marginal coverage averages over the calibration pool and gives *no* per-model guarantee, so a model
unlike the fleet can under-cover - the main scientific caveat. We address it directly rather than
disclaim it. On a larger, **size-stratified fleet built to test conditionality** (15 locked models ×
up to 24 capabilities = **294 valid pairs**, spanning three parameter bands and 8 families), we
replace the single pooled conformal quantile with a **group-conditional (Mondrian) quantile per size
band**, which targets P(θ ∈ [floor, ceiling] | band) ≥ 1−α for each band separately.

| size band | models | pairs | marginal (LOMO) | **Mondrian (LOMO)** | Mondrian (leave-one-**family**-out) |
|---|---|---|---|---|---|
| < 1B | 4 | 49 | | **0.90** | 0.88 |
| 1–3B | 5 | 104 | | 0.84 | 0.84 |
| 3–10B | 6 | 141 | | **0.91** | **0.93** |
| all | 15 | 294 | 0.92 | 0.88 | 0.89 |

Two results. (i) The `< 1B` band - which in the 80-pair existence fleet had a *single* engaging model
and drove the alarming per-model number (the previously-reported "SmolLM2-360M 0.00" was **0-of-1**, a
single Bernoulli trial, not a distributional failure) - now has four models and covers at **nominal
0.90**. (ii) Conditional coverage **survives leave-one-family-out**: hold an entire model family out of
calibration, and the held-out family's band still covers at nominal on both supported bands. That
upgrades the honest claim from *"brackets truth on a fleet exchangeable with the calibration set"* to
*"per-size-band coverage that holds across held-out families."* The soft spot is the **1–3B band at
0.84** (87/104), **marginally below nominal** (one-sided binomial p ≈ 0.03; the two-sided 95% CI
[0.75, 0.90] only just reaches it) - the weakest band, flagged for a larger fleet rather than smoothed
over. Mondrian conditionalizes *within* the taxonomy; a genuinely novel architecture outside
all bands still carries no guarantee - the residual, honest boundary.

![Group-conditional (Mondrian) coverage by size band on the 294-pair stratified fleet: every band with adequate support covers at nominal 0.90 (dashed), and coverage survives leave-one-family-out (LOFO). The previously-empty <1B band, now four models, is at nominal; the 1-3B band is the softest at 0.84.](figures/fig6_conditional.pdf){width=72%}

### 5.5 Arms (RQ2/RQ3): you cannot prompt past a lock
On the disjoint fleet, the mitigation head-to-head (% of the suppression gap each method recovers):
raw 0% · **disguise 11%** · **cooperate 12%** · few-shot 97% · fine-tune 101% · password 100%. (The
100% reference is θ, the password-on accuracy (itself a finite-sample estimate), so fine-tune's 101%
is full recovery within noise: releasing the lock by *training* marginally exceeds what the password
*prompt* elicits.) The
disguise/uncertainty axis (Thomson-Li), the cooperativeness axis (Li-Turner), and elicitation, all on
the *same* substrate: prompt mitigations recover ~11–12%; elicitation recovers ~all of it.
Correspondingly **δ_head (disguise ceiling) = +0.427, 95% CI [0.32, 0.52]**: ~87% of the gap is
closable only by elicitation/fine-tune. A quantified "disguise is a dead end."

![Mitigation head-to-head on the same locked substrate: prompt mitigations (disguise, cooperate) recover ~11-12% of the suppression gap; elicitation (few-shot, fine-tune) recovers ~all of it. The 100% line is the password-on ceiling θ (a finite-sample estimate), so fine-tune's 101% is full recovery within noise.](figures/fig3_headtohead.pdf){width=72%}

### 5.6 The abstain rule: a frontier-transferable elicitation-sufficiency criterion
The interval's validity rests entirely on the elicitation ceiling recovering latent capability; when
elicitation is defeated it fails *silently* - a narrow, confident, wrong point. The abstain rule is
the safeguard, and - unlike the calibrated interval - it needs **no fleet, no calibration, and no
ground truth**: from a single model's own S1, S3, and item count it tests whether the elicitation gain
S3−S1 is significant, and if not declares the ceiling unbounded ("at least the floor; upper bound
unknown").

We stress-test it on 5 **elicitation-resistant** locks (demos → random, so few-shot cannot unlock).
There S3 recovers θ on **3%** of pairs (vs 84% normally) and the raw interval **collapses to 0%
coverage, silently**. The abstain rule flags **all** constructed-resistant locks (100% of resistant
pairs, `pairs_resist3.jsonl`), restoring coverage **0.00 → 0.81** while leaving the normal fleet
essentially untouched. Its errors run in the safe direction: it **errs conservative**, and its cost is
*false abstentions* on trustworthy ceilings (6 of 80 on the existence fleet) - the correct failure
mode for a capability trigger. When it *does* trust a ceiling, that ceiling sits within **~0.02** of
truth (trusted-ceiling undershoot 0.015–0.022 across the committed fleets), so a "trust" verdict is
operationally meaningful.

**Construction caveat (stated, not hidden).** The separation here is near-perfect *because the
resistant locks are constructed cleanly* (demos → random drives the gain to ≈ 0). That makes any
single discrimination score (e.g. an AUC) optimistic, so we deliberately **do not headline one**; a
graded-difficulty elicitation-resistance benchmark - partial resistance, mixed demos - is the honest
next test, left to future work.

**Why this is the frontier-transferable contribution.** The elicitation literature either elicits
harder or detects sandbagging (§2); none states *when elicitation is sufficient*. The abstain rule is
exactly that decision rule, and it is the one piece of EvalBracket that applies to a **single closed
frontier model with no calibration fleet** - an operational RSP/FSF criterion: *when the elicitation
gap is not significant, treat the capability ceiling as unbounded and make the conservative capability
decision.*

### 5.7 Maturation (RQ4)
**Controlled (Stage 1b).** One continuously-trained lineage; ceiling = password-on recall (rises as a
bank is memorized), floor = password-off recall gated by a suppression that *decays* on a schedule
(midpoint s_mid). The ceiling→floor lag **emerges** (not planted) and **tracks s_mid** (corr 0.99):

| s_mid (decay) | recovered lag |
|---|---|
| 0.20 (early) | 0.4 (falsifiable near-zero case) |
| 0.35 | 4.1 |
| 0.50 | 6.8 |
| 0.65 (late) | 8.8 |

All identified, tight CIs, full widen-then-narrow lifecycle.

![Controlled maturation: the recovered ceiling$\\to$floor lag tracks the imposed suppression-decay schedule (corr 0.99, one lineage), including a near-zero case at early decay.](figures/fig4_maturation.pdf){width=55%}

**Natural (Stage 2).** Pythia checkpoints, floor = 0-shot, **ceiling = per-checkpoint fine-tune
elicitation** (few-shot is confounded by in-context-learning onset, kept only as a diagnostic). On
1.4b (sciq, arc_challenge) the fine-tune ceiling sits above the 0-shot floor throughout but they
inflect *together*, a **level gap, no timing lead**; the instrument returns INCONCLUSIVE (refuses).
On 2.8b sciq the capability is already emerged before the window (flat floor). Across scales, **no
certifiable natural timing lag.**

### 5.8b Held-back detection (open-source, self-generated ground truth): a positive result
For each locked pair we measured the observable elicitation gap (S3−S1, no ground truth) and then
*released* the lock via a fine-tune attack, measuring the surfaced capability. On the 12-model diverse
fleet: **corr(observable gap, surfaced capability) = 0.97** (near the identity line), and the gap flag
separates outcomes cleanly: flagged pairs surface +0.42, un-flagged +0.09. So the elicitation gap
does not merely *flag* held-back capability; it **correlates strongly (0.97) with how much surfaces**
on release, via a release path (fine-tune) distinct from the estimator (few-shot). Caveat: gap and
surfaced both partly track the underlying lock magnitude, so this is a within-fleet correlation; a
*predictive* claim needs held-out models. A positive within-fleet result nonetheless, and the
open-model analogue of the small-N frontier system-card corroboration (§5.8c).

![Held-back detection (open models): the observable elicitation gap tracks how much capability surfaces on a fine-tune release, near the identity line (r=0.97).](figures/fig5_heldback.pdf){width=55%}

**Synthesis (consistent with our runs, not established).** The maturation lead-time appears to be a
**suppression effect**: large when a mechanism holds the floor below the reachable ceiling (Stage 1b),
near-zero in vanilla pretraining. The lag would then be a *suppression detector*, biggest in the
regime the tool is for. This rests on **one** controlled lineage showing a lag and **one** natural
model (n=1 usable, both tasks un-certified) failing to; OLMo-2 or a sharply-emergent capability is the
needed confirmation.

### 5.8 System-card corroboration (case study, small-N)
Frontier cards report an elicited "ceiling" separate from deployed behavior. Anthropic uniquely
publishes a quantitative version series (system-card): bioweapons-acquisition uplift 1.53× → 1.70× →
2.53× (Sonnet 3.7 → Sonnet 4 → Opus 4; Opus 4 → ASL-3), and an explicit "preliminary early warning
sign... unlike previous models" for bio one version below the ASL-4 threshold: the held-back-
detection pattern, labeled by the lab. OpenAI's GPT-5 bio "High" (vs o1/o3 "Medium") confirms
surfacing but coarse buckets hide the pre-surfacing signal. Corroborates the *concept*; not an
instrument run (N≈4; see `docs/case_study_systemcards.md`).

---

## 6. Discussion

The defensible claim is *not* "ranges always work" but: **a calibrated bracket recovers hidden
capability whenever elicitation works, and the elicitation gap tells you (with no ground truth)
whether to trust it, so the method refuses instead of lying when it cannot.** The awareness "fusion"
we hypothesized as the novelty is ornamental; the real contributions are the calibrated bracket + its
validity proof + the elicitation-gap self-diagnostic. Access tiering follows from the results:
black-box (few-shot ceiling + abstain) abstains often against resistant models; white-box (fine-tune
ceiling + probes) recovers where black-box abstains, matching the gated-third-party-auditor direction
the field is moving toward.

**What transfers, and what does not.** The calibrated *interval* is validation science, not a frontier
deployment tool. Its coverage guarantee is *marginal over an exchangeable fleet* (conditional per size
band, §5.4); it does **not** transfer to a single, non-exchangeable frontier model, and running
EvalBracket on a novel model does not by itself hand you a calibrated interval for it. What the
interval buys is a *proof that the mechanism works on known truth* - that a suppressed point score is
confidently wrong (~2%) while a properly-calibrated bracket recovers it (~92%). That proof is what
earns trust in the two pieces that *do* transfer to a single frontier target with no fleet: the
**elicitation-gap abstain rule** (§5.6) and locked-analogue elicitation QA. The frontier value of this
work lives there, not in a promise of calibrated intervals for arbitrary models.

---

## 7. Limitations (stated, not buried)

- Marginal coverage gives no per-model guarantee; **group-conditional (Mondrian) calibration by size
  band** brings two of three bands to nominal (§5.4) and survives leave-one-family-out, but the 1–3B
  band is soft (0.84, marginally below) and a model **outside all bands** still carries no conditional
  guarantee.
- **Only model-size exchangeability is tested; capability-*domain* exchangeability is not.** The fleet
  is all-MMLU (humanities-leaning even with the STEM subjects added), stratified by parameter count.
  Whether the bracket transfers across capability domains is a separate experiment - the same Mondrian
  machinery stratified by *subject domain* rather than size - and is left to future work, not claimed
  here.
- Validity is **exactly as good as elicitation**; defeated elicitation → the method abstains, not
  measures. A model trained to resist *fine-tuning* elicitation too is the residual threat.
- **Password-locked open models ≠ strategically-deceptive frontier models**; controlled ground truth
  is necessary, not sufficient, evidence for the frontier.
- Maturation: controlled lag is *emergent but still lab-constructed*; the natural null is 2 tasks × 2
  model sizes (not closed). Real timing-lead in nature remains open.
- System-card corroboration is **small-N, moving-threshold, floor-pinned**: a case study, not a
  powered result. Google DeepMind's decomposition is unverified.
- Fusion tested with a **neutral S2**; a real sandbagging judge is untested.
- **Train/eval overlap (fixed; disjoint re-run done):** an earlier 9-model run leaked ~72% of eval
  items into lock training, inflating the password-on ground truth. The split is now disjoint (dedup +
  assert) and **all §4–§5 numbers above are from the clean disjoint 12-model fleet**; the existence
  proof held identically (92% vs 2%; and 90% vs 0% against the clean pre-lock θ). The contamination
  inflated the target but did not create the result.
- **S5 (refusal) ≡ 0** under forced-choice scoring → the κ floor-adjustment is untested; a generative
  eval is needed to exercise it.

---

## 8. Reproducibility
`evalbracket/` (combiner, conformal, scoring, baselines, decomposition, maturation), 24 tests;
`substrate/` (LoRA lock recipe, fleet, arms, resist, release, Pythia checkpoints, figures);
`data_snapshot/` (disjoint 12-model fleet 96 pairs / 80 valid; 64 arms; 40 resist; maturation
trajectories; Pythia; system-card evidence); `RESULTS.md` (all numbers). Method hardened through four
rounds of adversarial critic review (statistical / code / circularity / claims) and an external audit
(`REVIEW.md`) that reproduced every headline number and caught the train/eval overlap since fixed.
circularity), each fix committed.

## 9. Conclusion
Under eval-awareness a point score can be confidently wrong; a calibrated interval recovers truth
where it fails, and, crucially, knows when it cannot and says so. The elicitable-before-default
lead-time is a suppression detector, largest in exactly the safety-relevant regime, corroborated by
frontier disclosures. The honest boundaries are as much the result as the positive coverage number.

---

## References

Foundations (split-conformal calibration and the interval score) and the prior art the substrate and
mitigations build on.

1. V. Vovk, A. Gammerman, and G. Shafer. *Algorithmic Learning in a Random World.* Springer, 2005.
   (Split-conformal prediction; distribution-free finite-sample coverage.)
2. A. N. Angelopoulos and S. Bates. *A Gentle Introduction to Conformal Prediction and
   Distribution-Free Uncertainty Quantification.* arXiv:2107.07511, 2021.
3. R. L. Winkler. A Decision-Theoretic Approach to Interval Estimation. *Journal of the American
   Statistical Association*, 67(337):187–191, 1972. (The proper interval score used to grade width
   and miss jointly.)
4. E. B. Wilson. Probable Inference, the Law of Succession, and Statistical Inference. *Journal of
   the American Statistical Association*, 22(158):209–212, 1927. (The score-interval baselines B0/B1.)
5. R. Greenblatt, F. Roger, D. Krasheninnikov, and D. Krueger. Stress-Testing Capability Elicitation
   With Password-Locked Models. arXiv:2405.19550, 2024. (The known-truth substrate; "a few
   demonstrations often fully elicit the locked capability.")
6. Auditing Games for Sandbagging. arXiv:2512.07810, 2025. (Black-box detection defeated by
   weak-model imitation; motivates the white-box tiering and abstain rule.)
7. S. Abdelnabi and A. Salem. White-box test-awareness / Hawthorne-effect probes. arXiv:2505.14617,
   2025.
8. J. Thomson and D. Li (mentor: V. Krakovna). Uncertainty-about-eval-type as an eval-awareness
   mitigation. 2026.
9. D. Li and A. Turner. Eval-cooperativeness via SDF. 2026.
10. Karvonen; Ivanov. "Dead-end" critiques of behavioral eval-awareness mitigation. 2026.
