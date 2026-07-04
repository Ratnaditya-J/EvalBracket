# Phase 1 critique log + fix plan

Findings from adversarial/circularity review (agent, 2026-07-02). Stats + code reviews pending;
this file is updated as they land, then drives ONE consolidated self-correction pass.

## Adversarial review — valid hits (act on all)

1. **[LANDS] Correlation is axiomatic, not discovered.** In synthetic.py, ceiling shortfall,
   S2, and S4 are all affine functions of the same latent `a`. So "normalized conformal (B2) is
   sharper than unnormalized (B1c)" is guaranteed by construction, not evidence.
   → FIX: (a) relabel synthetic as SMOKE TEST, not existence proof. (b) On REAL data, estimate the
   S2/S4→shortfall relationship OUT-OF-SAMPLE (leave-one-model-out R² of regressing (θ−Ũ) on S2,Δ)
   and PRE-REGISTER a threshold; claim fusion value only if it clears the threshold on real pairs.

2. **[LANDS] Coverage on exchangeable data is a theorem, not a result.** Split-conformal coverage
   is guaranteed under exchangeability, which the i.i.d. generator satisfies by construction.
   → FIX: relabel "existence proof" → "implementation smoke test" everywhere (PROGRESS, run script,
   synthetic docstring already honest). The non-tautological contrast is only B0/B1 *undercover*
   (centering), which is elementary.

3. **[LANDS] Weak baselines + a pass gate that hides a null.** B0/B1 are strawmen; B1c is the only
   serious baseline and B2 beats it by ~1%, with a `+1e-6` tolerance that accepts a null.
   → FIX: (a) add a STRONG signal-free baseline **B_se = conformal scaled by binomial SE
   √(p(1−p)/n)**. If S2/S4-normalization doesn't beat SE-normalization, the awareness fusion adds
   nothing item-count doesn't. (b) replace `+1e-6` with a pre-registered minimum effect size AND a
   paired test across seeds (report mean Δinterval-score with a bootstrap/t CI over seeds).

4. **[LANDS — most damaging] Static, non-adversarial suppression + honest signals.** The generator
   freezes suppression as a per-pair scalar and forces S4 ≡ aware_gap+noise. Real eval-aware models
   respond adversarially and can FLATTEN S4 (behave identically under deploy/eval framing while
   underperforming) → w→σ(β0), no widening, interval misses high exactly when the adversary is best.
   Prior art: black-box detection was defeated by weak-model imitation — EvalBracket's S2/S4 are
   black-box signals and inherit this.
   → FIX: (a) add an ADVERSARIAL arm to the synthetic where true suppression is decoupled from
   signal honesty (S4 flattened); report coverage/interval-score THERE as a hard-mode result — an
   honest undercoverage finding is fine and expected. (b) In the real experiment, add a
   signal-suppressed model group and report coverage on it; state that the guarantee is conditional
   on adversary incompetence if it undercovers there. (c) Spec: make this a first-class caveat.

5. **[LANDS as scope] Exchangeability locked↔frontier is untested.** Title "recovers true capability
   under eval-awareness" overclaims; supported claim is "across a population of locked models
   exchangeable with the calibration set." → FIX: tighten claim language in spec + README.

6. **[LANDS] δ_head recovery is an algebraic identity** on synthetic (θ−max(armB,armC)→elic_head).
   → FIX: relabel as an arithmetic/wiring check; the real content is the negative control (noise
   doesn't manufacture a ceiling) + recovery on REAL arms.

## Stats review — valid hits
- [MAJOR] max-of-noisy-arms biases delta_head DOWN ~1 arm-SE; neg control passed for wrong reason;
  at n=100 headroom 0.03 detection→30%. FIX: sample-splitting (select winner on half A, value on
  half B) => unbiased E[theta - value_of_selected_arm].
- [MAJOR] bootstrap ignores model clustering => CI covers 70% not 95%. FIX: cluster bootstrap over
  models (thread `group` in).
- [MAJOR] no item-count rescaling (§3.4): calibrate n=400/deploy n=40 => coverage 0.91→0.69.
  FIX: SE-normalized scale absorbs n heteroscedasticity (also gives B_se for free).
- [MINOR] degenerate-beta fallback inverted awareness sign (b4=-1) -> use neutral (0,0,0)+warn.
- [MINOR] gamma-selection uses beta fit on full F inside folds (optimistic) -> refit beta per fold.
- [MINOR] fixed bootstrap seed -> parameterize.
- CONFIRMED CORRECT: conformal_quantile constant, s-normalization, union bound (cov 0.911),
  Winkler, Wilson, group-disjoint fit/cal.

## Code review — valid hits
- [CRITICAL] alpha=0 -> ZeroDivisionError in the warn branch. FIX: validate 0<alpha<1 in __init__.
- [MAJOR] default alpha_l=0.02 vacuous at realistic |C|. FIX: default 0.05/0.05; HARD-FAIL on vacuous.
- [MAJOR] conformal_quantile no guard alpha>=1/<0 -> silent wrong index. FIX: assert 0<alpha<1.
- [MAJOR] wilson_interval n=0 -> (nan,nan) not [0,1]. FIX: mask n==0 -> (0,1).
- [MINOR] NaN signals propagate silently. FIX: finiteness check in Signals.
- [MINOR] _fit_beta degenerate fallback silent. FIX: warn + neutral.
- [MINOR] splits empty cal/test with <3 groups; bracket() guard weak. FIX: require >=3 groups;
  add _calibrated flag checked in bracket().

## Consolidated fix pass — DONE (commit Phase 1 v2)
- [x] combiner: alpha validation; scale modes unit/se/se_aware; hard-fail vacuous; _calibrated flag;
      neutral degenerate beta; per-fold beta refit; conformal_quantile alpha guard; item-count guard.
- [x] baselines: wilson n=0 -> [0,1].
- [x] decomposition: unbiased s_mit (sample-split); cluster bootstrap over models; seed param.
- [x] synthetic: arm sel/val halves; adversarial signal-flattening AND elicitation-resistant modes.
- [x] experiment: B0/B1/B1c/B_se/B2 ladder; 1e-6 gate replaced by paired across-seed CI (reports
      B2 vs B_se = NULL honestly); OOS signals->shortfall R² gate (0.195); two adversarial hard
      modes (signal-flatten coverage 0.92 survives; elicitation-resist coverage 0.45 breaks).
- [x] docs: relabeled SMOKE TEST; tightened claim language (README + spec §11 addendum).
- [x] tests: 18 pass incl. alpha-validation, wilson n=0, unbiased-s_mit-reduces-bias,
      cluster-bootstrap-wider, SE heteroscedastic coverage, drift-warns, bracket-requires-calibrate.

## Key honest findings from the loop (carry into the real experiment)
1. Awareness fusion (B2) is TIED with SE-normalization (B_se) on synthetic -> fusion value is an
   OPEN question, gated on real-data OOS R² + paired test. Not assumed.
2. Coverage is ANCHOR-driven: survives signal-flattening, BREAKS under elicitation-resistance.
   => the real experiment's headline = does elicitation (S3) recover password-on theta on real
   locked models, and does coverage hold on an elicitation-resistant group?
