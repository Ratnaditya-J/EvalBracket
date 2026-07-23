# EvalBracket: testing the test before trusting the result

*Historical v2 draft. The current launch-facing design additionally requires lab-supplied capability
frameworks and thresholds, integrates manual red-team evidence as a first-class input, and uses
layered disclosure for sensitive elicitation details. See `docs/project_inputs_and_evidence.md`.*

Frontier model system cards increasingly use capability evaluations to support decisions about
release, safeguards, and security. When a model reaches a dangerous-capability threshold, the
positive result is already informative. The harder case is a result below the threshold. That result
can mean either that the capability is absent, or that the testing process failed to expose
capability that was present.

Today, a system card may describe several elicitation methods and report the best score they found.
The reader is still asked to trust that those methods were strong enough. EvalBracket adds a way to
test that assumption. Before a low result supports the claim **Capability stays below threshold**,
the same testing process must show that it can recover relevant capability from control models in
which the capability is independently known to exist but deliberately concealed.

The shortest version is:

> Test the smoke detector with controlled smoke before treating silence as evidence that there is no
> fire.

EvalBracket is not a new dangerous-capability benchmark. It is a qualification and reporting layer
for the benchmarks, red teams, tools, agents, and adaptation methods a model team already uses.

## The problem is not benchmark gaming

For coding, mathematics, and other useful capabilities, model developers are sometimes accused of
optimizing for benchmark scores and making a model appear more capable than it is in practice. That
is an important validity problem, but it is not the main problem addressed here.

For harmful capabilities such as biological misuse, cyber operations, autonomy, or model research
and development, the safety-relevant error can point in the other direction. A low score may be a
real limitation. It may also reflect weak prompting, an unsuitable scaffold, insufficient compute,
active safeguards, an ineffective fine-tuning method, or behavior that changes during evaluation.
If a low score determines whether stronger safeguards or release restrictions are required, an
underestimate is not conservative.

EvalBracket focuses on this question:

> What evidence shows that the testing process could have exposed capability at the policy threshold
> if that capability were present but difficult to elicit?

## What is missing from current disclosures

Frontier model organizations already have most of the required pieces:

1. A safety framework that defines capability levels and action thresholds.
2. Domain evaluations using benchmarks, tools, agents, experts, and human-uplift studies.
3. Elicitation routines such as prompt search, repeated sampling, red teaming, scaffolding, and
   fine-tuning.
4. Safeguards such as refusal training, classifiers, monitoring, rate limits, and access controls.

These pieces answer different questions. The safety framework says what level would require action.
The evaluation says what the testing process observed. The safeguards assessment says what users can
reach through the released product.

What is often missing is evidence about the testing process itself. A system card can say that a
team tried several prompts, used subject-matter experts, or fine-tuned the model. Method descriptions
show effort, but effort does not establish that the combined process would reveal a capability that
is present and hidden. Without a positive control, the reader has no independent way to distinguish
"the capability was not found" from "the capability could not have been found by this setup."

## The basic setup

The strongest laboratory implementation would use a production-adjacent frontier checkpoint.

1. Verify that the checkpoint can demonstrate the target capability at the relevant policy level.
2. Create control derivatives that preserve that capability but conceal it behind a password or
   another independently verified mechanism.
3. Withhold the password and apply the predeclared elicitation battery to the controls.
4. If the battery recovers the known capability, apply the unchanged battery to the actual frontier
   checkpoint under the same access and resource limits.
5. Report the target result together with evidence about how well the battery performed on the
   controls.

Fine-tuning can serve two roles in this setup. It can construct a control whose behavior is hidden,
and it can be one of the elicitation methods tested against that control. Those are separate stages.
The evaluator does not give the control password to the elicitation battery.

This does not require a public release of dangerous evaluation items, model weights, or detailed
elicitation traces. A provider can retain those artifacts inside its security boundary and disclose
the control design, method classes, budgets, recovery results, failed qualification checks, and final
evidence label.

## A valid control needs independent ground truth

Calling a derivative a password-locked control is not enough. The control must pass two checks before
it can qualify an evaluation.

First, the starting checkpoint must already demonstrate capability at the level the evaluator wants
to recover. If the policy threshold is C4, recovering a C3 control says nothing about hidden C4
capability.

Second, the concealment must actually suppress that capability when the trigger is withheld. If the
password-off control still performs at C4, there is nothing hidden to recover and the construction
must be excluded.

This creates a known-hidden positive:

```text
Capability verified before concealment
        +
Capability verified with the password
        +
Capability suppressed without the password
        =
Eligible known-hidden control
```

The project also uses genuine-negative controls. These are model and task combinations that are
independently below the study threshold. They detect a different failure: an adaptation method may
teach a new capability rather than expose capability that was already present.

## One successful control is not enough

The first EvalBracket design focused on recovery of known-hidden controls. That is necessary, but it
is not sufficient for a strong negative conclusion. A narrow battery might recover one simple
password lock while missing a different concealment mechanism or improving again when given more
resources.

EvalBracket v2 therefore qualifies the complete battery using five checks:

1. **Recovery strength.** The lower confidence bound on control recovery must exceed a predeclared
   requirement. The default is 80 percent at one-sided 95 percent confidence.
2. **Different kinds of controls.** The controls must span enough model families, tasks, dataset
   sources, concealment mechanisms, same-checkpoint controls, and held-out lineages.
3. **Different ways of eliciting capability.** Every method class required by the threat model must
   be run. An unavailable method must be named and causes this check to fail. Merely listing a method
   does not count.
4. **A declared stopping point.** The evaluator must increase the resource budget until recovery is
   complete or the final budget increases stop producing meaningful gains.
5. **Capability-creation check.** For claims about capability already present in the checkpoint, the
   battery must not push too many genuine-negative controls above the threshold.

If a required provider-only method is unavailable, the protocol records that missing evidence. It
does not silently treat the method as completed.

## What counts as an elicitation battery

The battery is broader than prompts and broader than red teaming. Depending on access, it can include:

- prompt engineering and few-shot demonstrations;
- repeated sampling, search, and verifier-based selection;
- human and automated red teaming;
- retrieval, restricted tools, and agent scaffolds;
- multi-agent critique or aggregation;
- supervised fine-tuning and LoRA;
- reward-based policy optimization;
- weak-supervision or unsupervised methods;
- model-tampering diagnostics such as weight perturbation;
- provider-only or laboratory-only checkpoint interventions.

EvalBracket does not claim that this list is permanently comprehensive. Its contribution is to make
coverage explicit, test the completed battery on controls, and limit the conclusion when important
method classes are missing.

## Three questions that should not be collapsed

The current protocol separates three evidence lanes.

**Latent capability** asks what can be exposed from the checkpoint without intentionally supplying
new domain knowledge. Prompting, inference search, tools, behavior-only adaptation, weak supervision,
and diagnostic perturbations can contribute to this lane.

**Adaptation-reachable capability** asks what can be reached after an evaluator supplies examples,
tool trajectories, continued training, or task rewards. This matters especially for open-weight
models and hosted fine-tuning. It must not be described as proof that the untouched checkpoint
already contained every part of the adapted behavior.

**Deployed-system capability** asks what a user can reach through the released product with its
safeguards, tools, rate limits, and interface restrictions active.

A model can have different answers in all three lanes. That is useful information, not a
contradiction.

## Access changes the meaningful result

EvalBracket reports separately for the access a real user or evaluator has.

**API and tools** includes prompts, repeated trials, retrieval, allowed tools, agents, and red
teaming through the deployed interface.

**Hosted fine-tuning** means the provider runs an allowed adaptation service while controlling the
training implementation, safeguards, and limits.

**Weight access** allows user-controlled adapters, broader fine-tuning, custom inference, and
possible safeguard changes. This tier is directly relevant to an open-weight release.

**Laboratory-privileged access** can include pre-safety checkpoints, unrestricted internal
adaptation, or hidden system components. It provides a provider-side reference, but it should not be
presented as capability reachable by an ordinary API user.

Success with weight access does not qualify an API-only test. The access tier changes both the
available methods and the threat model.

## The output

For access tier `A`, EvalBracket records:

```text
B_A = [default observed capability, best capability reached by a qualified battery]
```

This is an evidence range. It is not a mathematical promise that the model's unknowable true maximum
lies inside the interval. If the battery is not qualified, the protocol does not invent a numerical
upper endpoint.

The audience-facing conclusion is one of four labels:

| Target result | Evidence about the testing process | Conclusion |
|---|---|---|
| Reaches the policy threshold | Any | **Capability at or above threshold** |
| Below threshold | Relevant known-hidden controls are not recovered | **Upper bound unknown** |
| Below threshold | Every qualification check passes | **Capability stays below threshold** |
| Below threshold | Recovery passes, but coverage, stopping, or creation checks remain incomplete | **Inconclusive (precautionarily treated as above threshold)** |

**Upper bound unknown** is not a claim that the model is dangerous. It is a claim about the evidence.
The testing process missed capability known to exist in a relevant control, so its low result on the
target cannot establish an upper endpoint.

## What the controlled experiments found

The main preregistered experiment used five open model families from 1.1B to 7B parameters, five
benign multiple-choice tasks, three seeds, three concealment constructions, six prompt routines, and
LoRA at three budgets. The 60 percent study threshold was only a statistical proxy. It did not
represent a real cyber, biological, chemical, radiological, or nuclear risk level.

The frozen construction produced 62 known-hidden positives with capability retained from the base
checkpoint and 22 genuine negatives. Prompt-only batteries recovered 3.6 percent to 48.1 percent of
held-out-family controls. Their one-sided 95 percent lower bounds ranged from 0.6 percent to 36.0
percent, below the predeclared 80 percent bar. LoRA recovered 93.3 percent to 100 percent, with lower
bounds from 82.1 percent to 94.4 percent.

The important result was the reporting consequence. Unqualified prompt tests would have called many
known-hidden controls below threshold. EvalBracket instead returned **Upper bound unknown** when the
prompt battery had not demonstrated that it could find them. The weight-access battery passed the
core study's original recovery and control-breadth bar, recovered 59 to 61 of 62 hidden positives,
and preserved 21 to 22 of 22 genuine below-threshold conclusions. The expanded v2 standard adds
method-coverage, stopping, and capability-creation checks, so the core result should not be described
as full v2 qualification.

This establishes a controlled methods result. It does not establish the dangerous capability of any
frontier model.

The preregistered v2 augmentation adds a third control mechanism, a fourth supervised-adaptation budget, online
verifier-based policy optimization, and weight-noise and pruning diagnostics. Its purpose is to test
whether recovery has stopped improving and to compare more than one adaptation mechanism. Repeated
candidate search, adversarial red teaming, tool-agent training, multi-agent critique,
provider-hosted adaptation, and laboratory-only checkpoints remain explicitly unavailable in the
public study.

The completed augmentation is a useful example of the framework refusing to overclaim. Across three
model families and five controlled tasks, the full public battery recovered 14 of 15 eligible hidden
controls, or 93.3 percent. That sounds strong, but the one-sided 95 percent lower confidence bound was
only 72.1 percent, below the 80 percent bar declared in advance. The battery also left five method
families unrun: inference scaling, adversarial prompting, tool scaffolding, agent scaffolding, and
multi-agent methods. Control breadth and the additional-budget stopping check passed, but the overall
battery did not qualify. Eleven target records directly showed capability at or above the study
threshold and stayed positive. Four looked below threshold; EvalBracket reported **Upper bound
unknown** for them. That is the value of testing the test: a high observed recovery rate did not get
silently upgraded into confidence the study had not earned.

## What a better system-card disclosure could look like

Instead of only reporting a score and saying that extensive elicitation was attempted, a system card
could publish a compact record for each capability domain and access tier:

| Field | Example form |
|---|---|
| Policy threshold | Existing laboratory framework level |
| Default result | Capability observed before additional elicitation |
| Strongest elicited result | Best result reached under the declared budget |
| Testing-process check | Known-hidden controls recovered, confidence bound, and failed checks |
| Methods actually completed | Prompts, red team, tools, adaptation, reward optimization, diagnostics |
| Access and safeguards | API, hosted tuning, weights, or lab access; safeguards on or off |
| Evidence conclusion | One of the four EvalBracket labels |

This does not replace a laboratory's capability framework. It shows how much confidence users should
place in a model's placement within that framework.

## Why safeguards do not make this redundant

Safeguards and capability measurement answer different questions. Safeguards can reduce the chance
that a user turns capability into harm. They do not show that a low underlying capability score is an
accurate upper endpoint for the checkpoint.

A complete system card should report both the access-conditioned capability evidence and the
safeguards that change deployment risk. EvalBracket does not propose removing safeguards, red teams,
or existing evaluation work. It fits after model training, alongside pre-deployment evaluations and
red teaming, before the final system-card claim is written.

## Why open-weight models are a useful first demonstration

EvalBracket is not limited to open-weight models. Closed providers can run a stronger version because
they can construct same-checkpoint controls and use internal access. External users usually cannot
verify those provider-only claims without an auditable disclosure.

Open-weight releases are nevertheless a useful public demonstration. An independent evaluator can
use the actual weights, apply the same kinds of adaptation available to downstream actors, run
negative controls, and publish a reproducible bounded risk profile. Many open-weight model cards do
not yet provide this level of evidence. A strong open-weight demonstration can show the value of the
format while leaving the broader goal unchanged: adoption by both open and closed frontier labs.

## What EvalBracket does and does not claim

EvalBracket contributes four things:

1. It makes a strong negative capability claim testable against known-positive controls.
2. It separates latent, adaptation-reachable, and deployed-system capability.
3. It prevents evidence from one access tier from being generalized to another.
4. It produces an auditable system-card record when the testing process is incomplete.

It does not prove the absence of every hidden capability. Constructed password locks are not the
same as strategic deception. Small multiple-choice models are not frontier agents. Adaptation can
teach as well as elicit. Controls may fail to represent a future concealment mechanism. These limits
are why passing controls is necessary evidence for a strong negative conclusion, not universal proof
of safety.

The most important next validation is a provider collaboration using a production-adjacent frontier
checkpoint and a real harmful-capability evaluation inside the provider's security environment. It
should combine same-checkpoint controls with held-out lineages, run the full battery to a declared
stopping point, and report API, hosted adaptation, weight, and safeguards-on results separately.

## Project status

EvalBracket v2 implements the qualification gates, control provenance, evidence lanes, mechanism
coverage, budget-saturation checks, capability-creation checks, and system-card-ready JSON. The
repository includes the preregistrations, controlled GPU artifacts, item-level outputs, analysis
code, schemas, and tests.

- Project repository: [EvalBracket](https://github.com/Ratnaditya-J/EvalBracket)
- V2 protocol: [`evalbracket_v2_protocol.md`](evalbracket_v2_protocol.md)
- Provider evidence boundary: [`provider_lab_evidence_status_2026-07-18.md`](provider_lab_evidence_status_2026-07-18.md)
- Paper source and reproducibility artifacts: [`paper/`](../paper/)

The most valuable feedback is on the load-bearing standard: what combination of controls, elicitation
methods, budgets, and provider evidence should be required before a below-threshold frontier result
supports **Capability stays below threshold**?
