# Case study: held-back-capability detection in the wild (frontier system cards)

**Status: qualitative case study, small-N corroboration — NOT a run of the maturation instrument.**
The maturation lag estimator needs ~10+ comparable versions; public cards give ~4. So this documents
whether the *concept* EvalBracket formalizes — a large/rising elicited-capability gap as an advance
warning that a capability could surface — shows up in real frontier releases. It does. Figures are
from the deep-research pass (`docs/systemcard_feasibility.md`, 26 primary sources, 25/25 verified),
and **the headline numbers are now confirmed directly against the primary PDFs** (2026-07-02): the
Claude 4 System Card §7.2.4.1 reports bioweapons-acquisition uplift "1.53×" (Sonnet 3.7) and "2.53×"
(Opus 4) and "release Claude Opus 4 under the ASL-3"; the GPT-5 System Card states "treat
gpt-5-thinking as High capability", "remains on the cusp", and the "helpful-only variant seems to be
able to synthesize biorisk-related information" — all verbatim. The Opus 4.5 long-form virology 0.668 and the Opus 4.6 427x/190x AI-R&D speedup are
also now confirmed against the primary PDFs; the only correction is that virology has several
sub-metrics with moving thresholds, so it is a rising trend, not one clean 3-point series (see below).

## The concept being corroborated
"Held-back detection": a capability that is **reachable under elicitation** (fine-tune / helpful-only
/ scaffold / expert uplift = the *ceiling*) but **not present in default deployed behavior** (safety
refusals = the *floor*). A large or rising ceiling, while the floor stays suppressed, is an
early-warning signal that the capability exists latently and could **surface** later — via a jailbreak,
a downstream fine-tune, safety-training regression, or the next model version making it default.
This is the same object EvalBracket measures on locked models (S1 floor vs elicited ceiling), and the
abstain rule's elicitation gap is exactly this quantity.

## The clearest real-world instance: Anthropic CBRN (Claude family)

Anthropic evaluates **helpful-only snapshots** (harmlessness training removed) with agentic tools and
expert human-uplift trials, and reports **the highest score across snapshots as a capabilities
ceiling** — explicitly distinct from the deployed HHH model. This yields a version-over-version
*ceiling* series while the deployed *floor* is held near baseline by safeguards.

**Bioweapons-acquisition human-uplift (elicited ceiling), vs the ~2.8× rule-out threshold:**

| version | elicited uplift | deployed (floor) | ASL determination |
|---|---|---|---|
| Claude Sonnet 3.7 | 1.53× | suppressed (refuses) | ASL-2 |
| Claude Sonnet 4 | 1.70× | suppressed | ASL-2 |
| Claude Opus 4 | **2.53×** | suppressed | **ASL-3** (precautionary — could not rule out ASL-3) |

**ASL-4 virology (elicited) — primary-source verified, but multi-metric.** The Opus 4.5 card reports
long-form virology mean **0.668** (verbatim: "Participants with access to Claude Opus 4.5 achieved an
average score of 0.668"); the Opus 4.6 card reports **0.6124** on a virology metric "surpassing our
rule-out threshold of 0.6", and separately 0.603 vs Opus 4.5's 0.524 on another. **So there are
several virology sub-metrics with thresholds that changed across versions — the earlier "0.403 →
0.498 → 0.668" should be read as the rising long-form-virology *trend*, not one comparable series.**
AI R&D (Opus 4.6): **427× experimental-scaffold vs 190× standard** speedup — verified verbatim.

**The reading (the held-back pattern, made explicit by the lab itself):**
1. The elicited ceiling **rises monotonically** toward the rule-out threshold across versions while
   the deployed floor stays suppressed — a widening, rising held-back gap.
2. Opus 4 crossed into **ASL-3** precautionary safeguards because the *elicited* uplift got
   "sufficiently close" — i.e. the *ceiling*, not deployed behavior, drove the escalation.
3. Most on-point: the **Claude Opus 4.5 card documents an advance warning verbatim** — expert red-
   teaming found the model *"unlike previous models... able to generate some creative ideas that the
   expert judged as credible for enhanced biological threats,"* called a *"preliminary early warning
   sign"* — flagged **below** the ASL-4 mitigation threshold, one version before it would matter by
   default. That is a real "detected the held-back capability in advance" event, labeled by the lab.

**AI R&D / autonomy (Opus 4.6):** an experimental scaffold reached **427×** code-optimization speedup
vs **190×** standard (>2× elicitation gap), "roughly reaching" the ASL-4 benchmark rule-out
thresholds; judged not-crossed on qualitative/expert-survey grounds. Another documented
elicited-gap-approaching-threshold record.

## Cross-check: OpenAI bio surfacing (GPT-5) — real, but coarser evidence
`gpt-5-thinking` was designated **High** in Bio/Chem (Aug 2025) where the o1/o3 era was **Medium** — a
confirmed surfacing. The floor/ceiling contrast is explicit: the deployed model *"refused every
prompt"* while the helpful-only variant *"substantially outperformed experienced human baseliners."*
**But** the earlier OpenAI scorecards collapse elicited-vs-deployed into identical Low/Med/High buckets
(o1 set post-mitigation = pre-mitigation "to err on the side of caution"; GPT-4.5 calls its evals "a
lower bound" with no distinct fine-tuned number), so the *pre-surfacing* elicited signal is only
partially recoverable — you would have to reconstruct in-body benchmark percentages rather than read a
clean ceiling series. OpenAI corroborates *that surfacing happens*; Anthropic corroborates *the
advance-warning gap*.

## Honest caveats (why this is corroboration, not proof)
- **Small N.** ~4 versions per capability. Too few to fit or certify anything statistically — the
  maturation instrument would (correctly) return `identified=False`. This is a case study.
- **The floor is pinned, not catching up.** Unlike our controlled maturation, deployment safeguards
  hold the floor near baseline indefinitely, so "surfacing" here means *the ceiling crossing an alarm
  threshold*, not *the floor rising to the ceiling*. The lag-between-two-rising-curves framing does
  not apply; the relevant trajectory is the ceiling alone vs a fixed threshold.
- **Moving thresholds / trial confounders.** Anthropic tightened the virology rule-out threshold
  across versions and trial conditions differed (2 vs 3 vs 4 task-days). Version-over-version numbers
  are not clean apples-to-apples without normalization.
- **"Ceiling" is a lower bound.** Both labs explicitly call one-time elicitation a *lower bound* on
  latent capability, not a true maximum.
- **Google DeepMind: no evidence.** The FSF/Gemini elicited-vs-deployed decomposition was unverified;
  excluded here rather than assumed.

## What it establishes
The **phenomenon EvalBracket targets is real and documented at the frontier**, in exactly the
suppression regime Stage 2 predicted the signal would be strongest: dangerous capabilities that are
elicitable-but-suppressed, whose *elicited ceiling rises ahead of deployed behavior*, with at least
one lab (Anthropic) publishing the quantitative series and even labeling an advance "early warning."
It does **not** provide a powered, certified instrument result — that requires the many-version data
only available from controlled runs (which we have) or a lab's internal checkpoint series. The public
cards are the real-world anchor; the instrument's statistical home is elsewhere.
