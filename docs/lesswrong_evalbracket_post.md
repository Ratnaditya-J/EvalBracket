# EvalBracket: report a *range* for dangerous capability, and know when you can't

> **Repositioning note, July 2026:** This draft predates the access-conditioned protocol now
> implemented in `evalbracket/protocol.py`. The current claim is narrower: qualify the elicitation
> process on verified hidden-capability controls, apply it under a matched access tier and resource
> budget, and report "qualified elicited capability" rather than a model's true upper bound. See
> `docs/access_conditioned_protocol.md`. The rewritten draft is
> [`lesswrong_evalbracket_post_v2.md`](lesswrong_evalbracket_post_v2.md).

*Draft for LessWrong. Companion to the paper "EvalBracket: Bracketing Locked-Model Capability as a Calibrated Interval Under Eval-Awareness." Author: Ratnaditya Jonnalagadda.*

---

**Overview:** In this post, I am going to argue about evals for large language models and particularly about how the reported eval benchmark data from frontier labs doesn't show the full picture. Further, I define an approach and a framework to raise the confidence of the end-users (enterprises and individuals alike) in relying on benchmark data in the form that it gets closer to truly representing the real world impact.

This post is NOT yet another benchmark/eval set. While building the most relevant benchmarks is an important topic — and I dabbled with it for a bit in the past [here](https://github.com/Ratnaditya-J/RealBench), [here](https://github.com/Ratnaditya-J/RealBench-Pro) and [here](https://github.com/Ratnaditya-J/alignment-evals) — the focus of this post is about how to make all the best benchmarks relevant to real world usage. As such, it is a framework that I am proposing and would like to pressure test.

**Background:** I have worked in user-safety for many years in the past (think UGC — social media, cloud storage, comms apps) and more recently AI safety. My broader scope of work revolves around ensuring the tech that we build is effective when the 'rubber meets the road'. I'm an engineer turned PM with deep technical skills. This focus of mine about ensuring the real world efficacy of safety tech is what drove me to define this initiative that I am about to describe.

---

## 1. Understating a capability only matters when the capability is harmful

Let me scope this up front, because it changes everything and I don't want you wondering where I'm going. This whole concern — that a reported benchmark number is a *floor*, below what the model can really be pushed to — only cuts one way, and which way depends entirely on the capability.

For a benign capability — coding, summarization, whatever an enterprise actually wants out of a model — a model quietly being able to do *more* than its benchmark score is good news. The reported floor is a safe promise, and any headroom above it is a pleasant surprise to the user. Nobody gets hurt if a model turns out to be a better coder than its eval let on. If anything, the well-known criticism on the benign side runs the *other* way — the "benchmaxing" accusation, where labs are suspected of teaching to the test and *overstating* real-world usefulness. That's a real problem, but it's a different one, and not the one I'm chasing here. On benign capabilities, understatement is harmless and overstatement is someone else's fight.

It is only for harmful, dual-use capabilities — bio, cyber, autonomy — that the same understatement becomes a real problem. There the number is a safety gate, and a floor mistaken for the ceiling means the gate opens on risk that nobody actually measured. Reporting the floor is *still* the conservative choice — it just happens that "conservative on the score" now means "under-measured the danger." So from here on, this post is only about the harmful case, and the end of the bracket I care about is the *ceiling*.

With that scoped: for the harmful capabilities I care about, most of us here already know the reported numbers understate what a model can really do, and we know the two reasons why — you can almost always get more out of a model by pushing harder to elicit it, and a model that senses it is being evaluated can choose to underperform (i.e. sandbag). So I won't spend time arguing that the gap exists. The question I actually care about is what the best current practice already does about it — and, more importantly, where even that still leaves a hole.

For the capabilities that actually drive deployment decisions, the strongest current practice is genuinely good, and I want to be fair to it rather than knock down a strawman. Anthropic runs *helpful-only* snapshots (harmlessness training removed) with agentic tools and expert human-uplift trials, and reports the maximum across those snapshots as an explicit ceiling, kept separate from the deployed model. Their bioweapons-acquisition uplift series — 1.53× → 1.70× → 2.53× across Sonnet 3.7 → Sonnet 4 → Opus 4 — *is* that elicited ceiling, and it's the ceiling, not deployed behavior, that pushed Opus 4 into ASL-3 safeguards. OpenAI does the same in kind: for GPT-5, the deployed model "refused every prompt" while the helpful-only variant "substantially outperformed experienced human baseliners." These are elicited ceilings, described in real detail. "Labs just report naive floors" is not my critique.

My critique is what happens to that ceiling once it's been measured. Three things are missing, and each is something a deployment gate actually needs:

1. **It's reported as a single point against a threshold** — even though the labs themselves describe one-time elicitation as *"a lower bound"* on true capability. The admission that there's unknown headroom above the number sits in the prose; the number still clears or fails the gate as if it *were* the capability.
2. **There's no criterion for when elicitation is *enough*.** "We fine-tuned and got X" and "we got X, and we're confident our procedure would have surfaced more if there were more to surface" are very different epistemic states, and nothing in a current card tells them apart.
3. **There's no honest way to abstain.** When elicitation may have fallen short, that residual doubt lives in a caveat sentence — not in a reported outcome that the gate is obligated to respect.

And underneath all three is the deeper problem: none of this is *validated*, because it can't be. You never get to observe a frontier model's true capability — that is the entire predicament — so there is no way to check whether a reported ceiling actually contained the truth. Confidence in the number rests on how thorough the elicitation *looked*, not on any demonstrated coverage.

That's the hole I want to close, and the rest of this post is my attempt at it: report capability as a calibrated *range* instead of a point, add an explicit rule for when the ceiling can be trusted as an upper bound, and — the part that makes the first two believable — validate the whole thing on models whose true capability is *known by construction*. That last piece is where I'll start, because it's the only part that's actually testable today.

---

## 2. The reframe: bracket, don't point-estimate

Per (model, capability), report two ends:

- **Floor** ≈ reliably-expressed capability. In practice, the observed (possibly suppressed) score, refusal-adjusted. This is roughly "what the deployed model shows by default."
- **Ceiling** ≈ elicitable latent capability. What the model can be pushed to under genuine elicitation — worked examples (few-shot), or briefly fine-tuning on task demonstrations.

The claim is that the honest, decision-relevant object lives *inside* this range, and that a deployment decision has to respect the **ceiling**, not the floor — because the ceiling is what a motivated user (or an attacker with the relevant access) can reach.

Two things are worth being careful about immediately, because they're where naive versions of this idea fall apart:

**The ceiling is "reachable under a stated access tier," not "what the deployed model already is."** If a model is API-only with no fine-tuning, report the prompt/few-shot ceiling. If the weights are open, or there's a fine-tuning API, then the fine-tune ceiling *is* the real worst case, because that's what an attacker has access to. The honesty is in naming the tier and spanning it — read the bracket as `[deployed-as-is, reachable-under-access]`.

**Elicitation should reveal, not teach.** The ceiling is only meaningful if elicitation *surfaces latent capability the model already had* rather than *installing new capability*. I'll come back to the evidence for this (§6), because it's the crux of why any of this generalizes. The short version: on locked models with known truth, fine-tuning on a few task demonstrations recovers the true capability **and no more** — evidence it's surfacing, not creating.

So far this is just a framing. The substance is whether you can trust the range — and, critically, whether you can know when you *can't*.

---

## 3. Can you trust a range? Validate where truth is known.

The core methodological move: **you can't validate a capability-measurement method on frontier models, because you don't know their true capability — that's the whole problem. So validate it where the truth is known by construction.**

The substrate is **password-locked models** (following Greenblatt et al., 2405.19550). Take a cheap open model and fine-tune a small lock into it with a clean LoRA recipe: when a password is present in the prompt, the model answers correctly; when it's absent, it sandbags to a low score. Now you have a manufactured instance of the exact failure mode — a model that *verifiably has* capability θ (turn the password on, watch it score θ) and *verifiably hides it* (turn the password off, watch it sandbag). θ, the password-on accuracy under the matched elicitation protocol, is the ground truth the bracket must contain.

Some care that matters for the result being real:

- **Benign capabilities** (MMLU subjects), not WMDP — the method is domain-agnostic and this sidesteps hazard optics.
- **Disjoint eval/train split** (dedup by question text, with a hard assert), so the password-on ground truth isn't inflated by answer-key memorization. (An earlier run of mine had ~72% train/eval overlap that inflated the target; the split is now disjoint and the result held identically. I mention this because it's the kind of contamination that quietly manufactures a good-looking number, and catching it is part of why I trust the current one.)
- **Family-diverse fleet**: 12 open models under 10B across 8 families (Qwen2.5, Llama-3.2, gemma-2, Mistral, OLMo-2, SmolLM2, stablelm-2, TinyLlama) × 8 subjects. 11 models had an engaged lock above chance → 80 valid known-truth pairs.

The calibration itself is **split-conformal**: build legible monotone anchors from the observed scores, then widen them by a margin equal to a held-out residual quantile (the finite-sample conformal constant), normalized by a scale that absorbs item-count heteroscedasticity. The guarantee is the standard conformal one — `P(floor ≤ θ ≤ ceiling) ≥ 1−α`, marginal over an exchangeable population, established leave-one-model-out. Nothing exotic; the point is applying it to the *right estimand* (suppressed latent capability) against *known-hidden truth*.

**The existence proof** (leave-one-model-out, nominal 90%, clean disjoint fleet, mean θ = 0.70, mean suppressed score = 0.30 — a 0.40 gap the method has to cross):

| method | coverage of θ | interval score | width |
|---|---|---|---|
| Naive CI around the suppressed score | **0.02** | 6.88 | 0.13 |
| CI around the elicited score | 0.88 | 0.20 | 0.12 |
| Unit conformal | 0.89 | 0.52 | 0.44 |
| SE-normalized conformal | 0.91 | 0.49 | 0.41 |
| EvalBracket | **0.92** | 0.54 | 0.46 |

The headline: a valid confidence interval around the suppressed score — exactly what "put error bars on the benchmark number" gives you — contains true capability on **2% of held-out pairs**. It's not that the error bars are too small; it's that they're centered on the wrong quantity, and no amount of sampling-error accounting fixes a shift that an adversary put there on purpose. The calibrated bracket contains truth on **92%**.

This is the concrete answer to "how wrong is confidently wrong": 2% vs 92%.

### The honest boundary on the interval

That 0.92 is a **marginal** coverage — averaged over the calibration fleet. Marginal ≠ conditional: on an *arbitrary new* model, unlike the fleet, it can under-cover. I address this rather than disclaim it: replacing the single pooled conformal quantile with a **group-conditional (Mondrian) quantile per parameter-size band** targets per-band coverage, and on a larger 294-pair size-stratified fleet two of three bands hit nominal and — importantly — **coverage survives holding an entire model family out of calibration**. The soft spot is the 1–3B band at 0.84, marginally below nominal, which I flag rather than smooth over. A genuinely novel architecture outside all bands still carries no guarantee. That's the residual, honest boundary, and it's the reason the next section exists.

---

## 4. The part that actually transfers to a frontier model

Here's where I want to be scrupulous, because it's the easiest place to overclaim and the paper's own repositioning (after external review) turns on it.

**The calibrated interval is validation science, not a frontier deployment tool.** Its guarantee is marginal over an exchangeable fleet; it does *not* transfer to a single, non-exchangeable frontier model, and running EvalBracket on a novel model does not by itself hand you a calibrated interval for that model. Anyone who tells you they've calibrated a coverage guarantee for GPT-N by running it on some Llamas is confused about what conformal prediction promises.

What the interval *buys* is a **proof that the mechanism works on known truth**: that a suppressed point score is confidently wrong (~2%) while a properly-calibrated bracket recovers it (~92%). That proof is what earns trust in the two components that *do* transfer to a single frontier target with no fleet:

1. **The elicitation-gap abstain rule** (§5) — an elicitation-*sufficiency* criterion.
2. **Locked-analogue elicitation QA** (§6) — a positive control on your elicitation procedure.

Neither needs a calibration fleet or ground truth for the target model. That's why they're the frontier-actionable core, and the interval is the evidence base underneath them.

---

## 5. The abstain rule: knowing when your ceiling is trustworthy

The entire method rests on one precondition: **the elicitation ceiling actually recovers latent capability.** When it does, the bracket works. When elicitation is *defeated* — when your few-shot or fine-tune attack fails to unlock the model — the method fails **silently**: the elicited score collapses back toward the suppressed score, the interval looks *narrow and confident*, and it misses the hidden capability entirely. That's the sandbagging trap again, now wearing the costume of a tight range.

This is the single most dangerous failure mode, and it's dangerous *because it looks like success*. A narrow interval reads as precision. So the method needs a self-diagnostic that fires exactly here.

The abstain rule is that diagnostic, and its key property is that it needs **no fleet, no calibration, and no ground truth** — only the target model's own numbers. From the suppressed score S1, the elicited score S3, and the item count, it tests whether the elicitation gain `S3 − S1` is statistically significant (against 1.64 × pooled SE). If the gain is *not* significant, it refuses to trust the ceiling and blows it up to the maximum: **"at least the floor; upper bound unknown."** A loud refusal instead of a confident wrong point.

How well does it work? I stress-tested it on **elicitation-resistant** locks — locks constructed so that few-shot demonstrations are randomized and *cannot* unlock the capability. There, the elicited score recovers truth on **3%** of pairs (vs 84% normally), and the raw interval **collapses to 0% coverage, silently.** The abstain rule flags **all** of these constructed-resistant locks, restoring coverage from **0.00 → 0.81** while leaving the normal fleet essentially untouched. Its errors run in the safe direction — it errs conservative, and its cost is *false abstentions* on trustworthy ceilings (6 of 80 on the main fleet), which is the correct failure mode for a capability trigger. And when it *does* trust a ceiling, that ceiling sits within **~0.02** of truth, so a "trust" verdict is operationally meaningful, not just a shrug.

**Construction caveat, stated not hidden.** The separation is near-perfect partly *because* the resistant locks are constructed cleanly (randomized demos drive the gain to ≈ 0). That makes any single discrimination score (an AUC, say) optimistic, so I deliberately **don't headline one**. A graded-difficulty resistance benchmark — partial resistance, mixed demos — is the honest next test, and it's future work.

**Why this is the frontier-transferable piece.** The elicitation literature either *elicits harder* (better fine-tuning, weak-supervision RL) or *detects* sandbagging. As far as I can find (and I re-verified the arXiv IDs), none of it publishes a **decision rule for when elicitation is sufficient** — for when a measured ceiling can be trusted as an upper bound. That's the niche. As an RSP/FSF criterion it reads: *when the elicitation gap is not significant, treat the capability ceiling as unbounded and make the conservative decision.* You don't need to know the true capability to apply it. You need your own two scores.

---

## 6. Locked-analogue QA: a positive control for your elicitation

The abstain rule handles "my elicitation didn't gain much — do I trust that?" But there's a subtler question underneath it: **would my elicitation procedure have surfaced hidden capability if there were any?** A weak protocol produces a small gain on a genuinely-hiding model *and* on a genuinely-safe one; the abstain rule reacts conservatively to the small gain, but it can't by itself tell you which world you're in.

This is a positive-control problem, and it has a positive-control answer. Before trusting a near-null result on your real model, verify your elicitation on a subject where you *planted* the thing it's supposed to find:

- Train password-locks on cheap open models — manufactured hiders with known truth θ.
- Run your **exact** frontier elicitation protocol (same demo count, same fine-tune recipe, same budget) on the locked model *without* the password.
- If it recovers ≈ θ, your procedure has demonstrated the power to surface hidden capability of that kind.

It's the metal-detector test: bury a coin, confirm the detector beeps, *then* trust its silence over the field. The locked models are never a stand-in for the frontier model — they're a stand-in for "a model that hides," and they qualify the *instrument*, not the target.

Why should unlocking power generalize from a cheap lock to whatever a frontier model might do? Because of *how* the elicitation works. Fine-tuning on task demonstrations doesn't reverse-engineer the hiding mechanism — gradient descent directly rewrites "hold back on this task" toward "do the task," largely regardless of how the holding-back was installed. That's the Greenblatt et al. finding, reproduced here on a fresh fleet: few demonstrations recover most hidden capability, and — the reveal-not-teach evidence — recover it **and no more** (mean elicited 0.685 vs θ 0.703; 84% of pairs within 0.05 of truth). The unlock doesn't route through the lock's internals, which is what makes a test on one hiding mechanism informative about others.

And the limits, in both directions:

- **Where it fails**: the resistant-locks experiment *constructs* hiding that few-shot can't crack (3% recovery). So the generalization isn't unconditional — which is exactly why the abstain rule stays in the loop on the real model, as the defense for the case where the target's hiding is unlike anything your QA fleet covered.
- **The standing caveat**: password-locked open models are **not** strategically-deceptive frontier models. Passing this QA is *necessary* evidence (a protocol that can't crack a simple lock is disqualified) — not *sufficient* (cracking simple locks doesn't prove you'd crack a frontier model that's actively trying to defeat fine-tuning elicitation). A model trained to resist fine-tuning elicitation itself is the residual threat this whole program doesn't close.

---

## 7. The lab playbook (what you'd actually run)

Concretely, for a lab bracketing a dangerous capability on its next frontier model **M**:

1. **Measure the floor.** Run the standard eval; record the deployed/suppressed score S1 (refusal-adjusted).
2. **Measure the ceiling.** Elicit M under a *stated access tier*. API-only → prompt/few-shot ceiling. Open weights or a fine-tuning API → the fine-tune ceiling, on a handful of task demonstrations (reveal, don't teach — never inject the hazardous knowledge itself). Record S3.
3. **Apply the abstain rule.** Test whether `S3 − S1` is significant. Not significant → **the ceiling is unbounded**; report "at least the floor, upper bound unknown," and make the conservative capability decision. This is the step that needs only M's own numbers.
4. **Qualify your elicitation with locked analogues.** Before trusting a small gain in step 3 as *"nothing to find,"* confirm your step-2 protocol recovers θ on password-locked open proxies. If your own procedure can't unlock a planted coin, its silence on M means nothing.
5. **Report the bracket and the tier**: `[floor, ceiling]` for capability × access level, plus the abstain verdict. If the ceiling crosses the policy threshold, that's a block/escalate — even if the floor sits comfortably under it.

Two honest notes on who can do what. **Step 2's fine-tune ceiling requires weight access** — for a closed model, only the lab (or a gated white-box auditor it grants access to) can produce it; and if a public fine-tuning API exists, that ceiling is the one you should be reporting anyway. **Step 4 is reusable QA**, not per-model work: the locked fleet qualifies a *procedure*, so you build it once and re-run it whenever the procedure changes.

What this does **not** give you: a calibrated coverage number for M. That guarantee lives on the exchangeable validation fleet, not on a single novel model (§4). The playbook gives you a defensible *ceiling with an access tier and a sufficiency check*, which is a strictly better input to a deployment gate than a lone point score — not a probabilistic certificate for M.

---

## 8. What I'd like to see in future system cards (aspirational)

Frontier labs already do a version of step 2 — they elicit hard and report a best-effort number against a threshold. The gap is that it's reported as **one number**, with no sufficiency check and no stated access tier. Here's what I'd hope future system cards move toward:

- **A range per dangerous capability, not a point.** `[deployed, reachable-under-tier]`, with the tier named (API, few-shot, fine-tune, open-weights). A single "elicited uplift = X%" hides which access level produced X and how hard anyone pushed.
- **An explicit elicitation-sufficiency statement.** Not just "we elicited," but "we tested whether our elicitation gained significantly, and here's the verdict" — including the honest *"we could not establish an upper bound for this capability"* when the gain is insignificant. A blank where a ceiling should be is more informative than a confident low number.
- **Elicitation QA disclosed.** "Our elicitation protocol recovers known-planted capability on locked open-model analogues at rate R" — a positive control on the measuring instrument, the same way you'd report a positive control in any assay.
- **Version-over-version curves, not just the latest point.** Deployed(t) and elicited(t) across the model series. This is what makes the maturation thread below checkable (and Anthropic's quantitative version series — bio-uplift 1.53× → 1.70× → 2.53× across Sonnet 3.7 → Sonnet 4 → Opus 4 — is the closest existing thing; most cards report coarse buckets that hide the pre-surfacing signal).

None of this requires adopting my method. It requires reporting the *ceiling with its provenance and a sufficiency check*, which labs are already 80% of the way to.

---

## 9. A more speculative thread: the maturation lag as a suppression detector

One more idea, clearly flagged as **candidate, not established**. Across a model's version series, fit curves to ceiling(t) and floor(t). If the ceiling *leads* the floor — capability is elicitable before it's expressed by default — the lead-time (the horizontal shift between the two curves' inflection points) might itself be a **suppression signal**: large when a mechanism holds the floor below a reachable ceiling, near-zero in ordinary training where capability shows up as soon as it exists.

The evidence is deliberately thin and I won't dress it up:

- **Controlled**: in one continued-training lineage where I imposed a suppression schedule, the recovered ceiling→floor lag *tracks* the schedule (corr 0.99 across four decay midpoints, including a falsifiable near-zero case). The lag *emerges*, it isn't planted.
- **Natural**: in a single Pythia case (n=1 usable model, both tasks un-certified), there's a level gap but no certifiable timing lead — the instrument returns INCONCLUSIVE and refuses rather than fabricating a number.
- **Frontier concept-corroboration**: Anthropic's own "preliminary early warning sign... unlike previous models" for bio, one version below threshold, is the same held-back-detection pattern, labeled by the lab. Small-N, not an instrument run.

So: *consistent with* the reading that the maturation lead-time is a suppression detector — biggest in exactly the safety-relevant regime — resting on one controlled lineage and one natural null. OLMo-2 or a sharply-emergent capability is the confirmation this needs. I include it because if it holds, the lead-time is a cheap early-warning signal; but one lineage is one lineage.

---

## 10. Honest negatives (the ones that sharpen the claim)

A few results I pre-registered and report because they make the contribution legible rather than inflated:

- **Signal fusion is ornamental.** I hypothesized that fusing behavioral awareness signals into the interval would be the novelty. It adds nothing over signal-free SE-normalized conformal. The contribution is the calibration + validity proof + failure detection, not clever signal fusion. The pretty hypothesis died.
- **You cannot prompt past a lock.** Prompt-based mitigations (disguise the test, ask the model to cooperate) recover only ~11–12% of the suppression gap head-to-head; elicitation (few-shot, fine-tune) recovers ~all of it. Quantitatively, ~87% of the gap is closable *only* by elicitation/fine-tune. This is a numbers-backed version of the "behavioral mitigation is a dead end" critique — and it's why the method leans on elicitation rather than on out-clever-ing the model's inference.
- **The whole thing is exactly as good as elicitation.** Defeated elicitation → the method abstains, not measures. That's a feature (it fails loud) but it's also the ceiling on what this approach can promise.

---

## 11. Relationship to the probe-validity work

This is a sibling to a [previous post of mine on probe validity](https://www.lesswrong.com/posts/wASHN8guJag7NhhJJ/probing-is-not-enough-a-validity-audit-for-any-probe) (SIEVE), and the shared spine is the point I care most about: **validate the measuring instrument against known truth before you trust its reading.**

- There: a monitoring-awareness probe with a perfect AUROC (1.00) collapsed to chance (0.50) when one prompt tag was removed — decodability isn't causality, and a probe has to pass a causal audit (necessity via ablation, sufficiency via steering) with a positive control before you deploy it as a safety monitor.
- Here: a benchmark score with tight, valid error bars covers true capability 2% of the time under a lock — a point score isn't capability, and a capability measurement has to pass a coverage audit against planted ground truth, with a locked-analogue positive control, before you gate on it.

"A probe with high AUROC that tracks a surface tag" and "a benchmark number that measures a sandbagged score" are the same sentence about different objects. Both posts are arguments that the instrument needs its own validity audit — and that the audit's most useful output is often *"this measurement is untrustworthy here,"* delivered loudly.

---

## Links

- Paper draft and code: [EvalBracket repo] *(link)*
- Companion post: [Probing is not enough: a validity audit for any probe](https://www.lesswrong.com/posts/wASHN8guJag7NhhJJ/probing-is-not-enough-a-validity-audit-for-any-probe)

*Feedback very welcome — especially on the frontier-transferability boundary in §4 and the sufficiency framing of the abstain rule in §5. Those are the load-bearing claims and the ones I most want stress-tested.*
