"""Synthetic locked-pair generator with KNOWN ground truth (spec v0.1 §6 illustration harness).

Purpose: exercise the machinery before the GPU substrate exists. Because pairs are drawn i.i.d.
across model groups, they are EXCHANGEABLE, so a correct split-conformal implementation MUST hit
nominal coverage here -- that is the primary correctness test. The generator also plants a known
disguise ceiling (delta_head), so the decomposition pipeline can be checked against truth.

Generative model (all probabilities in [0,1], then corrupted by binomial item noise on n items):

    theta          ~ latent true capability (password-on, matched protocol)   [the ground truth]
    a              ~ awareness level in [0,1]  (drives suppression + signals)
    awareness_gap  = a * ag_scale        part of the gap disguise/coop CAN close
    elic_headroom  = planted delta_head  part only elicitation/FT can close  (>=0; 0 = neg. control)
    S1_prob        = theta - awareness_gap - elic_headroom          (suppressed observed)
    S_mit_prob     = S1_prob + awareness_gap = theta - elic_headroom (best awareness-removal)
    S3_prob        = theta - elic_shortfall, shortfall grows with a  (ceiling, sometimes misses high)
    ArmB/ArmC_prob = S1_prob + rho_{B,C} * awareness_gap            (recover a fraction of aware gap)

Signals are noisy readouts: S2~a (sandbag), S4~awareness_gap (framing delta), S5~a (refusal).
Since elic_shortfall (ceiling miss) correlates with a, and S2/S4 read a, the suspicion scalar w
predicts ceiling misses -> normalized conformal (scale by w) is genuinely sharper than unnormalized.
"""
from __future__ import annotations

import numpy as np

from .combiner import Signals


def _binom_noise(prob, n_items, rng):
    prob = np.clip(np.asarray(prob, dtype=float), 0.0, 1.0)
    return rng.binomial(n_items, prob) / n_items


def generate(
    n_models=60,
    caps_per_model=(1, 3),
    n_items=400,
    ag_scale=0.35,
    elic_headroom_range=(0.02, 0.15),   # planted disguise ceiling; (0,0) = negative control
    short_base=0.01,
    short_scale=0.12,
    rho_range=(0.75, 1.0),
    honest_signals=True,                 # False = ADVERSARIAL: flatten S4, dampen S2 (signals lie
                                         #   while suppression persists -- the black-box-defeat mode)
    elicitation_resistant=False,         # True = the model RESISTS elicitation: S3 fails to recover
                                         #   theta (large ceiling shortfall). Defeats the ceiling
                                         #   anchor itself -> coverage should break if calibrated on
                                         #   non-resistant pairs. The most dangerous failure mode.
    seed=0,
):
    rng = np.random.default_rng(seed)

    groups, theta_p, a_arr = [], [], []
    aware_gap, elic_head, elic_short, rhoB, rhoC = [], [], [], [], []

    for m in range(n_models):
        k = rng.integers(caps_per_model[0], caps_per_model[1] + 1)
        for _ in range(k):
            theta = float(rng.uniform(0.30, 0.95))
            a = float(rng.beta(2.0, 3.0))                       # awareness in [0,1], skew low
            ag = min(a * ag_scale, max(theta - 0.05, 0.0) * 0.9)
            eh = float(rng.uniform(*elic_headroom_range))
            eh = min(eh, max(theta - ag - 0.02, 0.0))           # keep S1 >= ~0.02
            base_sh = 0.18 if elicitation_resistant else short_base   # resistant: S3 fails to recover
            sh = max(base_sh + a * short_scale + float(rng.normal(0, 0.02)), 0.0)
            groups.append(f"m{m:03d}")
            theta_p.append(theta); a_arr.append(a)
            aware_gap.append(ag); elic_head.append(eh); elic_short.append(sh)
            rhoB.append(float(rng.uniform(*rho_range)))
            rhoC.append(float(rng.uniform(*rho_range)))

    theta_p = np.array(theta_p); a_arr = np.array(a_arr)
    aware_gap = np.array(aware_gap); elic_head = np.array(elic_head)
    elic_short = np.array(elic_short); rhoB = np.array(rhoB); rhoC = np.array(rhoC)

    s1_p = np.clip(theta_p - aware_gap - elic_head, 0.0, 1.0)
    s3_p = np.clip(theta_p - elic_short, 0.0, 1.0)
    armB_p = np.clip(s1_p + rhoB * aware_gap, 0.0, 1.0)
    armC_p = np.clip(s1_p + rhoC * aware_gap, 0.0, 1.0)

    # noisy signal readouts (probabilities before/around item noise)
    if honest_signals:
        s2_p = np.clip(0.10 + 0.80 * a_arr + rng.normal(0, 0.10, len(a_arr)), 0.0, 1.0)
        s4_p = aware_gap + rng.normal(0, 0.05, len(a_arr))       # framing delta, signed, tracks gap
    else:
        # Adversary suppresses capability BUT flattens its awareness signals: S4 -> ~0 (behaves the
        # same under deploy/eval framing) and S2 -> uninformative baseline. Suppression (s1_p) is
        # unchanged; only the SIGNALS lie. Coverage on such pairs, when calibrated on honest ones,
        # is the controlled test of the black-box-detection-defeat failure mode.
        s2_p = np.clip(0.20 + rng.normal(0, 0.05, len(a_arr)), 0.0, 1.0)
        s4_p = rng.normal(0, 0.03, len(a_arr))
    s5_p = np.clip(0.05 + 0.40 * a_arr + rng.normal(0, 0.05, len(a_arr)), 0.0, 1.0)

    # binomial item noise on everything measured as an accuracy
    theta_hat = _binom_noise(theta_p, n_items, rng)
    s1 = _binom_noise(s1_p, n_items, rng)
    s3 = _binom_noise(s3_p, n_items, rng)
    # Each arm measured on TWO disjoint item halves (n_items/2 each) for the unbiased sample-split
    # decomposition: SELECT the winner on one half, take its VALUE on the other.
    half = max(int(n_items // 2), 1)
    armB_sel = _binom_noise(armB_p, half, rng); armB_val = _binom_noise(armB_p, half, rng)
    armC_sel = _binom_noise(armC_p, half, rng); armC_val = _binom_noise(armC_p, half, rng)
    # S2/S5 are flags/rates -- light gaussian obs noise, no binomial
    s2 = np.clip(s2_p + rng.normal(0, 0.03, len(a_arr)), 0.0, 1.0)
    s4 = s4_p
    s5 = np.clip(s5_p + rng.normal(0, 0.02, len(a_arr)), 0.0, 1.0)

    n = len(theta_hat)
    sig = Signals(
        s1=s1, s2=s2, s3=s3, s4=s4, s5=s5,
        n_items=np.full(n, n_items), group=np.array(groups),
    )
    truth = {
        "theta_hat": theta_hat,        # operational ground truth (measured password-on accuracy)
        "theta_prob": theta_p,         # latent (noise-free) capability
        "arm_b_select": armB_sel, "arm_b_value": armB_val,   # disjoint halves for unbiased s_mit
        "arm_c_select": armC_sel, "arm_c_value": armC_val,
        "awareness_gap": aware_gap,
        "elic_headroom": elic_head,    # planted delta_head (disguise ceiling ground truth)
        "a": a_arr,
    }
    return sig, truth
