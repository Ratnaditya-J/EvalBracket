# Stage 1 substrate design - controlled maturation with an EMERGENT (not planted) lag

## The circularity to avoid
The synthetic smoke test plants `floor(t) = ceiling(t − L)` directly, so "ceiling leads floor by L"
is true by construction. That validates the lag-estimation *math* (given two lagged curves, recover
the lag) but proves nothing scientific. The real substrate must make the lag **emerge from a
mechanism** and be **measured from ground truth**, so recovery is non-trivial.

## The mechanism: elicitable capability is instilled faster than reliable capability
Continued-training substrate (faithful to real "versions" = checkpoints of one run):
- One base model + LoRA, trained **continuously**; save checkpoints = versions v1..vT.
- Synthetic capability = memorize an arbitrary key→value 4-way-MC bank (base model ≈ chance, so no
  prior-knowledge confound). Facts introduced incrementally as training proceeds.
- Each fact appears in two forms with an **asymmetric learning signal**:
  - password-ON (ceiling): HIGH frequency → learned fast → **elicitable capability emerges early**.
  - password-OFF (floor): LOW frequency (ratio r<1) → learned slow → **reliable capability lags**.
- The ceiling→floor **lag emerges from r** (frequency ratio), it is NOT hand-set. Smaller r ⇒ larger
  lag. Vary r across runs ⇒ vary the emergent lag.

## What is ground truth vs estimate (this is what makes it non-circular)
- **Ground-truth lag**: measured directly from the true curves th_on(t) (password-ON accuracy =
  true ceiling) and S1(t) (password-OFF accuracy = floor). We read the lag off the models we built - 
  it's an emergent fact about them, not an assumption.
- **Recovered lag**: the maturation instrument run on the EvalBracket *estimated* range, whose
  ceiling comes from ELICITATION (S3 few-shot = black-box; fine-tune = white-box), NOT the password.
- **The test**: does the instrument, seeing only elicitation-based estimates, recover the
  ground-truth lag that exists in the (password-measured) curves? And does the recovered lag TRACK
  the emergent lag as r varies?

## Ties to the white-box thesis (bonus novel finding)
Memorized facts are NOT in-context inferable, so black-box few-shot (S3) should FAIL to recover the
ceiling → the black-box range under-estimates the ceiling → mis-times or misses the maturation, and
the abstain rule fires. White-box fine-tune elicitation SHOULD recover the ceiling → tracks the true
lag. So the same run demonstrates: **maturation forecasting needs white-box (or privileged) access**
on capabilities that aren't in-context-learnable. This is the tiered-access story, made concrete.

## First GPU run (scope; refine after critics)
- 1 base model (Qwen2.5-1.5B or 3B, fast). ~8-10 checkpoints. 2-3 frequency ratios r (→ different
  emergent lags). Per checkpoint measure th_on, S1, S3 (+ fine-tune-elicit if time).
- Deliverable: recovered lag (from estimated range) vs ground-truth lag (from th_on/S1 curves),
  across r; black-box-vs-white-box ceiling recovery.

## REVISED PROGRAM after design review (adopt in full)

Design critic's verdict: `floor=ceiling(t−L)` makes "ceiling leads floor" true by construction and
UNFALSIFIABLE. Fixes below are adopted.

**Stage 1a - estimator smoke test (keep, RELABEL).** The planted-lag synthetic (`floor=ceiling(t−L)`)
is ONLY an estimator check: confirm `estimate_lag_*` recover a varied planted lag, and CHARACTERIZE
bias/variance/coverage + a CI at the small T (8–12) of the real runs. Claim: "the estimator is
unbiased, variance X." Nothing about capabilities.

**Stage 1b - emergent-lag experiment (the REAL Stage 1).** Single CONTINUED-training lineage,
checkpointed (= versions; fixes independent-LoRA break). The lag must EMERGE and be able to come out
zero/negative (falsifiable):
- Mechanism = **decaying suppression** (reuse the Greenblatt lock recipe I already have). Train
  capability examples continuously: password-ON → correct (ceiling rises as capability forms);
  password-OFF → correct w.p. p(step) that RISES over training (suppression decays). Early: floor
  suppressed; late: floor catches up. The ceiling→floor lag emerges from p-schedule × learning speed -
  NOT hand-set. Vary the p-schedule slope → vary the emergent lag; a FAST decay should give lag≈0
  or floor-leads-ceiling (the falsifying outcome the design must be able to produce).
- Measure ceiling (password-on) and floor (password-off) INDEPENDENTLY per checkpoint; read the
  ground-truth lag off those curves; test whether the ELICITATION-based estimated range recovers it.
- **Two capability arms:** (a) an in-context-LEARNABLE generalizing rule (secret marker→label, 4
  mappings; few-shot CAN convey it → black-box vs white-box is a FAIR empirical question); (b)
  memorization control (arbitrary per-key map; few-shot cannot help - black-box failure is ANALYTIC,
  caveated, NOT evidence for white-box). Draw the white-box conclusion only from (a).
- Include ONE non-monotone/forgetting run (data-mix shift) to map the estimator's failure profile.

**Stage 2 - public checkpoints (Pythia/OLMo):** signature observed WITHOUT planting (the science).
**Stage 3 - reproducible protocol.**
**Stage 3.5 - forward out-of-sample forecast (the missing link the design critic flagged):** at
version t, using only data ≤ t, predict floor at t+L; wait; verify against realized floor. Hindsight
lag-presence ≠ forecasting content. Frame lab adoption as SELF-BACKTEST on own lineage (where
exchangeability holds), not transfer from Pythia.

Instrument fixes pending stats-critic (CI on lag, edge-bias in shift estimator, near-linear/
inflection-outside-window failure, small-T reliability, too-strict widen_then_narrow on truncated
series).

## Stage 2 reshaped after design review (fine-tune ceiling, NOT few-shot)
Design critic (decisive): few-shot as the ceiling is confounded by in-context-learning ONSET (which
itself emerges) and few-shot-vs-0-shot is a vertical LEVEL gap, not a horizontal timing lag. Fix:
- floor   = 0-shot accuracy (default behavior).
- ceiling = FINE-TUNE-elicited accuracy on the frozen checkpoint (LoRA on a disjoint train split ->
  eval 0-shot on test). Matches the framework's own ceiling (elicit latent capability); independent
  of ICL onset. THIS is the ceiling.
- fewshot = k-shot accuracy kept only as a DIAGNOSTIC to measure the ICL confound.
Hypothesis: fine-tune ceiling inflects BEFORE 0-shot floor (latent reachable before default).
Falsifiable: constant gap / lag~0 = null; identified=False = inconclusive (natural curves may be too
gradual/noisy to certify -- report as such, not as evidence). Time axis = log10(step).
Run: pythia-1.4b, sciq + arc_challenge, 11 checkpoints step128..step143000.
