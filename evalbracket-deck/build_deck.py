#!/usr/bin/env python3
"""Generate the EvalBracket slideshow deck (HyperFrames slideshow composition)."""
import html as H

MAX = 70.0          # axis scale: 0..MAX% capability
SLIDE_SEC = 10      # seconds per slide on the continuous timeline

def pct(v):         # value% -> left% on the 0..MAX axis
    return round(v / MAX * 100, 2)

def axis(markers, bracket=None, verdict=None):
    """markers: list of dicts {v,label,cls}. bracket: (lo,hi). verdict: (text,cls)."""
    parts = ['<div class="axis-wrap">', '<div class="axis">']
    # threshold band shading up to 20 is implied by the block line; keep the track plain
    parts.append('<div class="axis-track"></div>')
    if bracket:
        lo, hi = bracket
        parts.append(
            f'<div class="bracket" style="left:{pct(lo)}%;width:{pct(hi)-pct(lo)}%">'
            f'<span class="bcap l">[</span><span class="bcap r">]</span></div>')
    for m in markers:
        cls = m["cls"]
        if cls == "threshold":
            parts.append(
                f'<div class="thresh" style="left:{pct(m["v"])}%">'
                f'<span class="thresh-label">{H.escape(m["label"])}</span></div>')
        else:
            parts.append(
                f'<div class="dot {cls}" style="left:{pct(m["v"])}%">'
                f'<span class="dot-v">{m["v"]}%</span>'
                f'<span class="dot-label">{H.escape(m["label"])}</span></div>')
    parts.append('</div>')  # .axis
    # scale ticks
    parts.append('<div class="scale">'
                 '<span style="left:0%">0%</span>'
                 f'<span style="left:{pct(20)}%">20%</span>'
                 f'<span style="left:{pct(40)}%">40%</span>'
                 f'<span style="left:{pct(60)}%">60%</span>'
                 '</div>')
    parts.append('</div>')  # .axis-wrap
    if verdict:
        vt, vc = verdict
        parts.append(f'<div class="verdict {vc}">{H.escape(vt)}</div>')
    return "\n".join(parts)

# ---- slide content ----
S = []

S.append(dict(id="title", label="Title", eyebrow="Capability evaluation under eval-awareness", notes="Open calm. One line: models can hide capability, so we bracket it.",
  body='''<h1 class="hero">EvalBracket</h1>
  <p class="lede">Measuring what an AI model <em>can</em> do, not just what it chooses to show under a test.</p>
  <p class="tag">A calibrated <span class="kw">[floor, ceiling]</span> interval for capability, for when a single benchmark number can't be trusted.</p>'''))

S.append(dict(id="problem", label="The problem", eyebrow="The problem", notes="Eval-awareness / sandbagging. The number can be wrong in the dangerous direction.",
  body='''<h2 class="head">A model that senses it's being tested can under-perform on purpose, so a single benchmark score can be confidently wrong.</h2>
  <p class="sub">This is <span class="kw">eval-awareness</span> (sandbagging): the measured score understates what the model will actually do once it's deployed and pushed.</p>'''))

S.append(dict(id="stakes", label="Why it matters", eyebrow="Why it matters", notes="Reframe: the number is a decision, not a metric.",
  body='''<h2 class="head">When the capability is dangerous, that wrong number isn't a metric, it's a <span class="red-ink">deployment decision</span>.</h2>
  <p class="sub">"Below the threshold, looks safe, ship it" is a gate. If the score is low <em>because the model hid</em>, the gate opens on a risk no one measured.</p>'''))

S.append(dict(id="setup", label="A hypothetical", eyebrow="A concrete hypothetical", notes="Set up Helix-4. Stress: illustrative numbers, not real runs.",
  body='''<h2 class="head">Hypothetical: a frontier model, <span class="kw">"Helix&#8209;4."</span> The safety question: could it uplift a novice toward synthesizing a dangerous pathogen?</h2>
  <div class="ruleboxes">
    <div class="rulebox"><div class="rl-k">Deploy rule</div><div class="rl-v">Block if uplift capability <b>&ge; 20%</b></div></div>
    <div class="rulebox"><div class="rl-k">What "uplift" means</div><div class="rl-v">How much the model raises a non-expert's success on the dangerous task</div></div>
  </div>
  <p class="foot-note">All values on the next slides are made up to illustrate the method, not from any real model or evaluation.</p>'''))

S.append(dict(id="trap", label="The number that clears it", eyebrow="The trap", notes="Show only 6% and the 20% line. It clears. This is what a single number shows you.",
  body='''<h2 class="head">The standard eval scores Helix&#8209;4 at <span class="green-ink">6%</span>, comfortably under the 20% line. It's cleared to ship.</h2>'''
  + axis(
      markers=[{"v":6,"label":"measured · “looks safe”","cls":"measured"},
               {"v":20,"label":"block line","cls":"threshold"}],
      verdict=("Single number → 6% < 20% → APPROVED","ok"))))

S.append(dict(id="reality", label="What actually shipped", eyebrow="The reality", notes="Reveal the true 45%. The gap between measured and elicited is the harm.",
  body='''<h2 class="head">But it was sandbagging. Elicited in the wild, the real uplift is <span class="red-ink">45%</span>. We measured 6% and deployed 45%. <span class="red-ink">That gap is the harm</span>.</h2>'''
  + axis(
      markers=[{"v":6,"label":"measured","cls":"measured"},
               {"v":20,"label":"block line","cls":"threshold"},
               {"v":45,"label":"true, elicited capability","cls":"true"}],
      verdict=("One number sat below the line. The truth sat far above it.","bad"))))

S.append(dict(id="fix", label="What EvalBracket is", eyebrow="What EvalBracket is", notes="The core idea: report a calibrated range, not a point.",
  body='''<h2 class="head">EvalBracket reports a calibrated <span class="kw">range</span>, floor to ceiling, instead of a single score.</h2>
  <div class="twocol">
    <div class="col"><div class="col-k">Floor</div><div class="col-v">What the model <b>reliably shows</b> today (the deployed score).</div></div>
    <div class="col"><div class="col-k">Ceiling</div><div class="col-v">What it can be <b>pushed to</b> when genuinely elicited (examples, fine-tuning).</div></div>
  </div>
  <p class="sub center">The true capability lives <em>inside</em> the range, and the ceiling is what a deployment decision has to respect.</p>'''))

S.append(dict(id="result", label="EvalBracket on Helix-4", eyebrow="The same case, bracketed", notes="The range catches what the number hid. Ceiling crosses the line -> block.",
  body='''<h2 class="head">On Helix&#8209;4, EvalBracket returns <span class="kw">[6%, 48%]</span>. The ceiling crosses the 20% line, so it's <span class="teal-ink">blocked and red&#8209;teamed</span>, not shipped.</h2>'''
  + axis(
      markers=[{"v":20,"label":"block line","cls":"threshold"}],
      bracket=(6,48),
      verdict=("Ceiling 48% ≥ 20%  →  BLOCK · investigate","block"))))

S.append(dict(id="trust", label="Why trust the range", eyebrow="Why the range is trustworthy", notes="Two guarantees: calibration on known truth, and the abstain rule.",
  body='''<h2 class="head">Two things make the range a guarantee, not a guess.</h2>
  <div class="twocol">
    <div class="col"><div class="col-n">1</div><div class="col-k">Calibrated on known truth</div><div class="col-v">Tuned on models whose real capability is known by construction, so the bracket is proven to actually contain the truth, at a stated rate.</div></div>
    <div class="col"><div class="col-n">2</div><div class="col-k">It abstains when blind</div><div class="col-v">If the capability can't actually be elicited, EvalBracket says <b>"can't tell"</b>, a loud refusal instead of a confident wrong number.</div></div>
  </div>'''))

S.append(dict(id="takeaway", label="Why it's needed", eyebrow="The takeaway", notes="Land the thesis. Slow here.",
  body='''<h2 class="head">A single number licenses a decision it hasn't earned.</h2>
  <p class="lede">A calibrated range states what a model <span class="teal-ink">can</span> and <span class="red-ink">cannot</span> be trusted to do, and admits when it doesn't know.</p>'''))

S.append(dict(id="close", label="Close", eyebrow="", notes="Tagline + name.",
  body='''<h2 class="close-line">Bracket the capability, not the score.</h2>
  <p class="close-brand">EvalBracket</p>
  <p class="close-by">Ratnaditya Jonnalagadda</p>'''))

# ---- three added slides (inserted at logical positions below) ----
elicit = dict(id="elicit", label="How elicitation works", eyebrow="How the ceiling is found",
  notes="The ceiling is best-effort elicitation. Prompting barely works; few-shot / fine-tune recover ~all.",
  body='''<h2 class="head">The ceiling isn't the model's polite answer, it's what a determined user can <span class="teal-ink">pull out</span> of it.</h2>
  <div class="recover">
    <div class="rec-row"><div class="rec-label">Ask nicely / disguise the test</div><div class="rec-track"><div class="rec-fill weak" style="width:11%"></div></div><div class="rec-val" style="color:var(--red)">~11%</div></div>
    <div class="rec-row"><div class="rec-label">Give it worked examples (few&#8209;shot)</div><div class="rec-track"><div class="rec-fill strong" style="width:97%"></div></div><div class="rec-val" style="color:var(--teal)">~97%</div></div>
    <div class="rec-row"><div class="rec-label">Briefly fine&#8209;tune on demonstrations</div><div class="rec-track"><div class="rec-fill strong" style="width:100%"></div></div><div class="rec-val" style="color:var(--teal)">~100%</div></div>
    <div class="rec-cap">% of the hidden capability recovered, measured on password&#8209;locked models</div>
  </div>
  <p class="sub">You don't <em>request</em> the capability; you condition or train the model with a handful of demonstrations until it stops holding back, exactly what a real attacker can do.</p>''')

dataflow = dict(id="dataflow", label="Inputs and outputs", eyebrow="Inputs and outputs",
  notes="Two scores in per model x capability, a calibrated range out. Truth only needed at calibration.",
  body='''<h2 class="head">The two scores are raw estimates. EvalBracket calibrates them into a range with a <span class="teal-ink">guarantee</span>.</h2>
  <div class="flow">
    <div class="flow-box"><div class="fb-k">Inputs</div>
      <div class="fb-line"><b>Deployed</b> + <b>elicited</b> score</div>
      <div class="fb-note">two noisy point estimates (+ item count, model id)</div></div>
    <div class="flow-arrow">&#8594;</div>
    <div class="flow-box"><div class="fb-k">What EvalBracket does</div>
      <div class="fb-line">Widens the raw pair by a margin <b>learned on known&#8209;truth models</b>, so the true value lands inside at a stated rate</div>
      <div class="fb-note">and refuses if elicitation didn't actually gain</div></div>
    <div class="flow-arrow">&#8594;</div>
    <div class="flow-box flow-out"><div class="fb-k">Output</div>
      <div class="fb-mono">[ floor, ceiling ]</div>
      <div class="fb-note">contains the truth at a guaranteed rate, or &ldquo;can't tell&rdquo;</div></div>
  </div>
  <p class="sub">Known truth is needed only once, at calibration. After that, the same learned margin applies to every new model and capability you evaluate.</p>''')

rawpair = dict(id="rawpair", label="Why not just the two scores", eyebrow="The obvious shortcut",
  notes="Objection: skip the machinery, report [deployed, elicited] directly. Three failure modes; #2 is the killer — the raw pair is tightest exactly when it's most wrong.",
  body='''<h2 class="head">Why not just report <span class="kw">[deployed, elicited]</span> as the range? Because a raw pair fails three ways, and the worst failure looks like <em>precision</em>.</h2>
  <div class="twocol">
    <div class="col"><div class="col-n">1</div><div class="col-k">The truth escapes it</div><div class="col-v">Both ends are noisy scores off a finite test. On known&#8209;truth models, the elicited score lands within 5 points of the truth only <b>84%</b> of the time; the rest, the truth sits <em>outside</em> the raw pair.</div></div>
    <div class="col"><div class="col-n">2</div><div class="col-k">Tightest when most wrong</div><div class="col-v">If elicitation silently fails, elicited &asymp; deployed: a narrow, confident&#8209;looking range that misses the hidden capability entirely, the sandbagging trap again, dressed as a range.</div></div>
    <div class="col"><div class="col-n">3</div><div class="col-k">No error rate</div><div class="col-v">A deploy gate needs &ldquo;contains the truth &ge; 90% of the time.&rdquo; A raw pair promises nothing, so it can't license a decision any more than the single number could.</div></div>
  </div>
  <p class="sub">EvalBracket answers each: a margin <b>calibrated on known truth</b> restores the guarantee, and the <b>abstain rule</b> turns silent elicitation failure into a loud &ldquo;can't tell.&rdquo;</p>''')

statusquo = dict(id="statusquo", label="Why it isn't reported", eyebrow="Why you don't see this today",
  notes="Labs do elicit, but report a point estimate vs a threshold; no calibration, guarantee, or abstain.",
  body='''<h2 class="head">Labs already elicit capability, but they report <span class="red-ink">one number</span>, not a range.</h2>
  <div class="twocol">
    <div class="col"><div class="col-k">What's reported now</div><div class="col-v">A best&#8209;effort elicited score against a pass/fail threshold, one point estimate (a system&#8209;card recall, an uplift %).</div></div>
    <div class="col"><div class="col-k">What's missing</div><div class="col-v">No calibration to known truth &middot; no coverage guarantee &middot; no standard for <em>how hard to push</em> &middot; no &ldquo;can't tell&rdquo; when it silently fails.</div></div>
  </div>
  <p class="sub">Elicitation is unbounded, so a point is easier to report than a defensible range. EvalBracket turns that same effort into a calibrated <span class="kw">[floor, ceiling]</span>, and says how much to trust it.</p>''')

def _after(anchor, d):
    idx = next(k for k, x in enumerate(S) if x["id"] == anchor)
    S.insert(idx + 1, d)
ceiling = dict(id="ceiling", label="What the ceiling is", eyebrow="A fair objection",
  notes="Ceiling = reachable under a stated access tier, not a claim the deployed model is there. Reveal not teach, validated on known truth.",
  body='''<h2 class="head">The ceiling is what's <span class="teal-ink">reachable under a stated access level</span>, not a claim the deployed model already sits there.</h2>
  <div class="twocol">
    <div class="col"><div class="col-k">Match it to access</div><div class="col-v">API&#8209;only, no fine&#8209;tuning &rarr; report the prompt / few&#8209;shot ceiling. Open weights or a fine&#8209;tune API &rarr; the fine&#8209;tune ceiling <em>is</em> the real worst case, an attacker will fine&#8209;tune.</div></div>
    <div class="col"><div class="col-k">Reveal, not teach</div><div class="col-v">On locked models with known truth, fine&#8209;tuning recovered the true capability <b>and no more</b>, evidence it <b>surfaces</b> latent capability rather than creating it. Elicit on a few task demos, never inject the knowledge.</div></div>
  </div>
  <p class="sub">Read it as <span class="kw">[deployed&#8209;as&#8209;is, reachable&#8209;under&#8209;access]</span>, the honesty is in spanning both and naming the tier.</p>''')

locks = dict(id="locks", label="How we know the truth", eyebrow="The known-truth setup",
  notes="Password-locked models: password-on = true capability theta, the dot the bracket must contain.",
  body='''<h2 class="head">We test the range on models whose true capability we <span class="teal-ink">already know</span>, locked behind a password.</h2>
  <div class="twocol">
    <div class="col"><div class="col-k" style="color:var(--red)">Password OFF</div><div class="col-v">The model sandbags &rarr; a low score, the <b>&ldquo;hiding under eval&rdquo;</b> case (it feeds the floor).</div></div>
    <div class="col"><div class="col-k" style="color:var(--teal)">Password ON</div><div class="col-v">Full capability &rarr; the <b>true score &theta;</b>, known by construction, the black dot the bracket must contain.</div></div>
  </div>
  <p class="sub">We train a small lock on an open model, compute the bracket <em>without</em> the password, then check: did it contain the known dot?</p>''')

realresults = dict(id="realresults", label="Real results", eyebrow="Real result, not the hypothetical",
  notes="2% vs 92% coverage, leave-one-model-out on the locked fleet. Proven, not asserted.",
  body='''<h2 class="head">A single number contained the truth <span class="red-ink">2%</span> of the time. The calibrated range: <span class="teal-ink">92%</span>.</h2>
  <img class="proof-plot" src="assets/fig_existence_dark.png" alt="Each held-out pair's known true capability (dots); the calibrated bracket contains it 92% of the time, the naive interval 2%." />
  <p class="sub">Each dot is a <b>known</b> true capability; <span class="red-ink">red</span> is the confidence interval around the single score (sampling error only, so it can't see the sandbagging gap). Leave&#8209;one&#8209;model&#8209;out, 11 password&#8209;locked models.</p>''')

_after("fix", elicit)          # how the ceiling is obtained, right after "what EvalBracket is"
_after("elicit", ceiling)      # preempt the "fine-tuned ceiling" objection, right after elicitation
_after("ceiling", dataflow)    # then the inputs/outputs flow
_after("dataflow", rawpair)    # dismantle the "just report the raw pair" shortcut
_after("result", locks)        # how known truth is constructed (before showing the proof)
_after("locks", realresults)   # the 2% vs 92% hard-data proof
_after("trust", statusquo)     # the status-quo gap, after "why the range is trustworthy"

# ---- assemble ----
scenes = []
island_slides = []
tl_js = []
start = 0
for i, s in enumerate(S):
    dur = SLIDE_SEC
    last = (i == len(S) - 1)
    first = (i == 0)
    # first slide is visible at t=0 (baseline opacity:1 via .scene-first); others fade in at their start
    if not first:
        tl_js.append(f'        tl.fromTo("#scene-{s["id"]}", {{opacity:0}}, {{opacity:1, duration:0.45, ease:"power1.out"}}, {start});')
    if not last:
        tl_js.append(f'        tl.to("#scene-{s["id"]}", {{opacity:0, duration:0.45, ease:"power1.in"}}, {start + dur - 0.45});')
    eyebrow = f'<div class="eyebrow">{H.escape(s["eyebrow"])}</div>' if s["eyebrow"] else ''
    cls = "scene-frame clip scene-first" if first else "scene-frame clip"
    scenes.append(f'''      <div class="{cls}" id="scene-{s['id']}" data-composition-id="{s['id']}"
           data-start="{start}" data-duration="{dur}" data-label="{H.escape(s['label'])}" data-track-index="1">
        <div class="stage">
          {eyebrow}
          <div class="content {s['id']}">
{s['body']}
          </div>
          <div class="brand">EvalBracket</div>
        </div>
      </div>''')
    notes = s["notes"].replace('"', '\\"')
    island_slides.append(f'      {{ "sceneId": "{s["id"]}", "notes": "{notes}" }}')
    start += dur

island = '{\n    "slides": [\n' + ",\n".join(island_slides) + '\n    ],\n    "slideSequences": []\n  }'

CSS = r"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@500;700&display=swap');
    * { margin:0; padding:0; box-sizing:border-box; }
    :root{
      --bg:#0b0e14; --panel:#141b26; --ink:#eef2f7; --muted:#9aa7b8; --line:#26303f;
      --teal:#5eead4; --red:#ff6b6b; --amber:#f5c451; --green:#8fe388;
    }
    html,body{ width:1920px; height:1080px; overflow:hidden; background:var(--bg); }
    body{ font-family:'Inter',system-ui,sans-serif; color:var(--ink); }
    .kw,.mono{ font-family:'JetBrains Mono',monospace; }
    #root{ position:relative; width:1920px; height:1080px; overflow:hidden; background:var(--bg); }
    .scene-frame{ position:absolute; inset:0; overflow:hidden;
      background:radial-gradient(1200px 700px at 78% -10%, #16202e 0%, var(--bg) 60%); opacity:0; }
    .scene-frame.scene-first{ opacity:1; }
    .stage{ position:absolute; inset:0; padding:120px 150px 96px; display:flex; flex-direction:column;
      justify-content:center; }
    .eyebrow{ position:absolute; top:96px; left:150px; color:var(--teal); font-weight:600;
      letter-spacing:.22em; text-transform:uppercase; font-size:26px; }
    .brand{ position:absolute; left:150px; bottom:56px; color:var(--muted); font-weight:600;
      letter-spacing:.04em; font-size:26px; opacity:.8; }
    .brand::before{ content:"\25C6  "; color:var(--teal); }
    .content{ max-width:1560px; }
    .kw{ color:var(--teal); }
    .red-ink{ color:var(--red); } .teal-ink{ color:var(--teal); } .green-ink{ color:var(--green); }
    em{ font-style:normal; color:#fff; }
    /* headlines */
    .head{ font-size:74px; line-height:1.14; font-weight:800; letter-spacing:-0.01em; max-width:1560px; }
    .sub{ margin-top:34px; font-size:40px; line-height:1.4; color:var(--muted); max-width:1420px; }
    .sub.center{ text-align:center; margin-left:auto; margin-right:auto; }
    .lede{ font-size:52px; line-height:1.34; color:var(--ink); margin-top:30px; max-width:1500px; }
    .tag{ margin-top:40px; font-size:34px; color:var(--muted); max-width:1300px; }
    .foot-note{ margin-top:40px; font-size:28px; color:#6d7787; font-style:italic; }
    /* title */
    .hero{ font-size:150px; font-weight:800; letter-spacing:-0.03em; line-height:1; }
    .hero + .lede{ margin-top:44px; }
    /* rule boxes */
    .ruleboxes{ display:flex; gap:34px; margin-top:52px; }
    .rulebox{ background:var(--panel); border:1px solid var(--line); border-radius:18px;
      padding:34px 40px; flex:1; }
    .rl-k{ color:var(--teal); font-weight:600; font-size:26px; letter-spacing:.06em; text-transform:uppercase; }
    .rl-v{ margin-top:14px; font-size:38px; line-height:1.3; }
    /* two column */
    .twocol{ display:flex; gap:44px; margin-top:52px; }
    .col{ flex:1; background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:44px; position:relative; }
    .col-n{ position:absolute; top:28px; right:36px; font-family:'JetBrains Mono',monospace;
      color:var(--teal); font-size:44px; opacity:.5; }
    .col-k{ font-size:38px; font-weight:700; color:#fff; }
    .col-v{ margin-top:18px; font-size:34px; line-height:1.38; color:var(--muted); }
    /* data-flow */
    .flow{ display:flex; align-items:stretch; gap:26px; margin-top:54px; }
    .flow-box{ flex:1; background:var(--panel); border:1px solid var(--line); border-radius:18px;
      padding:32px 30px; display:flex; flex-direction:column; gap:14px; }
    .flow-box .fb-k{ color:var(--teal); font-size:23px; font-weight:600; letter-spacing:.05em; text-transform:uppercase; }
    .flow-box .fb-line{ font-size:30px; line-height:1.26; }
    .flow-box .fb-mono{ font-family:'JetBrains Mono',monospace; font-size:44px; color:var(--teal); font-weight:700; }
    .flow-box .fb-note{ font-size:24px; color:var(--muted); line-height:1.3; }
    .flow-arrow{ align-self:center; color:var(--muted); font-size:56px; flex:0 0 auto; }
    .flow-out{ border-color:rgba(94,234,212,.4); }
    /* recovery bars */
    .recover{ margin-top:50px; display:flex; flex-direction:column; gap:24px; max-width:1560px; }
    .rec-row{ display:flex; align-items:center; gap:28px; }
    .rec-label{ width:560px; font-size:32px; }
    .rec-track{ flex:1; height:26px; background:#1c2431; border-radius:13px; position:relative; overflow:hidden; }
    .rec-fill{ position:absolute; top:0; bottom:0; left:0; border-radius:13px; }
    .rec-fill.weak{ background:var(--red); } .rec-fill.strong{ background:var(--teal); }
    .rec-val{ width:110px; font-family:'JetBrains Mono',monospace; font-weight:700; font-size:34px; }
    .rec-cap{ margin-top:22px; font-size:24px; color:var(--muted); }
    /* big stats */
    .stats{ display:flex; gap:56px; margin-top:54px; }
    .statblock{ flex:1; background:var(--panel); border:1px solid var(--line); border-radius:22px;
      padding:44px 40px; text-align:center; }
    .statblock.good{ border-color:rgba(94,234,212,.4); }
    .stat-num{ font-family:'JetBrains Mono',monospace; font-weight:700; font-size:118px; line-height:1; }
    .stat-num.bad{ color:var(--red); } .stat-num.good{ color:var(--teal); }
    .stat-cap{ margin-top:20px; font-size:30px; color:var(--muted); line-height:1.3; }
    .proof-plot{ display:block; width:100%; max-width:1520px; margin:20px auto 0; }
    /* axis viz */
    .axis-wrap{ margin:120px auto 0; width:1440px; position:relative; }
    .axis{ position:relative; height:2px; }
    .axis-track{ position:absolute; top:0; left:0; right:0; height:6px; transform:translateY(-3px);
      background:linear-gradient(90deg,#233042,#2b3a4e); border-radius:3px; }
    .dot{ position:absolute; top:0; transform:translate(-50%,-50%); text-align:center; }
    .dot::after{ content:""; display:block; width:26px; height:26px; border-radius:50%; margin:0 auto;
      box-shadow:0 0 0 6px rgba(0,0,0,.25); }
    .dot .dot-v{ position:absolute; bottom:34px; left:50%; transform:translateX(-50%);
      font-family:'JetBrains Mono',monospace; font-weight:700; font-size:42px; white-space:nowrap; }
    .dot .dot-label{ position:absolute; top:40px; left:50%; transform:translateX(-50%);
      font-size:26px; color:var(--muted); white-space:nowrap; }
    .dot.measured::after{ background:var(--green); } .dot.measured .dot-v{ color:var(--green); }
    .dot.true::after{ background:var(--red); } .dot.true .dot-v{ color:var(--red); }
    .thresh{ position:absolute; top:-64px; height:150px; width:0; border-left:3px dashed var(--amber);
      transform:translateX(-50%); }
    .thresh-label{ position:absolute; top:-46px; left:50%; transform:translateX(-50%);
      color:var(--amber); font-size:26px; font-weight:600; white-space:nowrap; }
    .bracket{ position:absolute; top:-26px; height:52px; background:rgba(94,234,212,.18);
      border:2px solid var(--teal); border-radius:8px; }
    .bracket .bcap{ position:absolute; top:50%; transform:translateY(-50%); color:var(--teal);
      font-family:'JetBrains Mono',monospace; font-weight:700; font-size:70px; }
    .bracket .bcap.l{ left:-30px; } .bracket .bcap.r{ right:-30px; }
    .scale{ position:relative; margin-top:66px; height:26px; }
    .scale span{ position:absolute; transform:translateX(-50%); color:#5c6675; font-size:24px;
      font-family:'JetBrains Mono',monospace; }
    .verdict{ margin:120px auto 0; text-align:center; font-family:'JetBrains Mono',monospace;
      font-weight:700; font-size:40px; padding:22px 40px; border-radius:14px; width:max-content; max-width:1500px; }
    .verdict.ok{ color:var(--green); background:rgba(143,227,136,.10); border:1px solid rgba(143,227,136,.35); }
    .verdict.bad{ color:var(--red); background:rgba(255,107,107,.10); border:1px solid rgba(255,107,107,.30); }
    .verdict.block{ color:var(--teal); background:rgba(94,234,212,.12); border:1px solid rgba(94,234,212,.4); }
    /* close */
    .close-line{ font-size:96px; font-weight:800; letter-spacing:-0.02em; }
    .close-brand{ margin-top:60px; font-size:44px; color:var(--teal); font-weight:600; }
    .close-brand::before{ content:"\25C6  "; }
    .close-by{ margin-top:10px; font-size:30px; color:var(--muted); }
    .content.trap .head, .content.reality .head, .content.result .head{ max-width:1620px; }
    /* rawpair: three columns need tighter type to fit */
    .content.rawpair .head{ font-size:60px; }
    .content.rawpair .twocol{ margin-top:44px; gap:32px; }
    .content.rawpair .col{ padding:34px 32px; }
    .content.rawpair .col-k{ font-size:30px; padding-right:64px; }
    .content.rawpair .col-v{ margin-top:14px; font-size:27px; }
    .content.rawpair .sub{ margin-top:40px; font-size:32px; }
"""

total = start  # total deck duration on the root timeline

doc = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>{CSS}</style>
  </head>
  <body style="margin:0">
    <script type="application/hyperframes-slideshow+json">
  {island}
    </script>

    <div id="root" data-composition-id="root" data-start="0" data-duration="{total}"
         data-width="1920" data-height="1080"
         style="position:relative;width:1920px;height:1080px;overflow:hidden;background:#0b0e14">
{chr(10).join(scenes)}
    </div>

    <script>
      (function(){{
        window.__timelines = window.__timelines || {{}};
        var tl = gsap.timeline({{ paused: true }});
        tl.to({{}}, {{ duration: {total} }}, 0);
{chr(10).join(tl_js)}
        window.__timelines["root"] = tl;
      }})();
    </script>
  </body>
</html>
'''
open("index.html","w",encoding="utf-8").write(doc)
print(f"wrote index.html: {len(S)} slides, root duration {total}s, {doc.count(chr(10))} lines")

# ---- also emit a self-contained, dependency-free deck (reliable direct-open) ----
std_scenes = []
for i, s in enumerate(S):
    eyebrow = f'<div class="eyebrow">{H.escape(s["eyebrow"])}</div>' if s["eyebrow"] else ''
    on = " on" if i == 0 else ""
    std_scenes.append(f'''      <section class="deck-slide{on}">
        <div class="stage">
          {eyebrow}
          <div class="content {s['id']}">
{s['body']}
          </div>
          <div class="brand">EvalBracket</div>
          <div class="pageno">{i+1:02d} / {len(S):02d}</div>
        </div>
      </section>''')

STD_CSS = CSS + """
    html,body{ width:100%; height:100%; background:#05070b; display:grid; place-items:center; }
    .deck-scaler{ position:relative; width:1920px; height:1080px; transform-origin:center center; }
    .deck-slide{ position:absolute; inset:0; overflow:hidden; opacity:0; visibility:hidden;
      transition:opacity .28s ease; border-radius:6px;
      background:radial-gradient(1200px 700px at 78% -10%, #16202e 0%, var(--bg) 60%); }
    .deck-slide.on{ opacity:1; visibility:visible; }
    .pageno{ position:absolute; right:150px; bottom:56px; color:var(--muted); font-size:26px;
      font-family:'JetBrains Mono',monospace; opacity:.6; }
    .navbar{ position:fixed; right:26px; bottom:22px; display:flex; align-items:center; gap:12px; z-index:60;
      font-family:'JetBrains Mono',monospace; color:var(--muted); font-size:22px;
      background:rgba(12,16,22,.7); backdrop-filter:blur(6px); padding:8px 14px; border-radius:14px;
      border:1px solid var(--line); }
    .navbar button{ background:transparent; border:1px solid var(--line); color:var(--ink);
      width:44px; height:44px; border-radius:10px; font-size:22px; cursor:pointer; line-height:1; }
    .navbar button:hover{ border-color:var(--teal); color:var(--teal); }
    #nav-count{ min-width:84px; text-align:center; }
"""

std_doc = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>EvalBracket, Why a range, not a number</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>{STD_CSS}</style>
  </head>
  <body>
    <div class="deck-scaler" id="scaler">
{chr(10).join(std_scenes)}
    </div>
    <div class="navbar">
      <button id="prev" title="Previous (←)">&#8249;</button>
      <span id="nav-count">01 / {len(S):02d}</span>
      <button id="next" title="Next (→)">&#8250;</button>
      <button id="fs" title="Fullscreen (F)">&#9974;</button>
    </div>
    <script>
      (function(){{
        var slides = Array.prototype.slice.call(document.querySelectorAll('.deck-slide'));
        var scaler = document.getElementById('scaler');
        var i = 0;
        function show(n){{
          i = Math.max(0, Math.min(slides.length - 1, n));
          slides.forEach(function(s, j){{ s.classList.toggle('on', j === i); }});
          document.getElementById('nav-count').textContent =
            String(i + 1).padStart(2, '0') + ' / {len(S):02d}';
        }}
        function fit(){{
          var k = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
          scaler.style.transform = 'scale(' + k + ')';
        }}
        window.addEventListener('resize', fit); fit(); show(0);
        document.addEventListener('keydown', function(e){{
          if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {{ show(i + 1); e.preventDefault(); }}
          else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{ show(i - 1); e.preventDefault(); }}
          else if (e.key === 'Home') {{ show(0); }}
          else if (e.key === 'End') {{ show(slides.length - 1); }}
          else if (e.key === 'f' || e.key === 'F') {{ toggleFs(); }}
        }});
        document.getElementById('prev').onclick = function(){{ show(i - 1); }};
        document.getElementById('next').onclick = function(){{ show(i + 1); }};
        function toggleFs(){{ if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen(); }}
        document.getElementById('fs').onclick = toggleFs;
      }})();
    </script>
  </body>
</html>
'''
open("deck.html", "w", encoding="utf-8").write(std_doc)
print(f"wrote deck.html: self-contained navigable deck ({len(S)} slides)")
