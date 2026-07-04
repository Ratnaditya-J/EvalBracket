"""Group-conditional (Mondrian) split-conformal for EvalBracket.

Marginal conformal (combiner.py) guarantees P(theta in [L,H]) >= 1-alpha averaged over the
exchangeable pool. It gives NO per-group guarantee, so a test model unlike the calibration fleet can
under-cover badly (the exchangeability caveat, paper Limitations). Mondrian conformal partitions the
calibration residuals by a taxonomy kappa(x) -- here **size band** -- and takes a separate one-sided
quantile within each band, yielding a per-band conditional guarantee:

    P(theta in [L,H] | band=g) >= 1 - alpha   for each band g,

as long as calibration and test are exchangeable *within* band g. Under-coverage that correlates with
model size (small/unusual models) is exactly what a size-band taxonomy repairs.

We reuse the combiner's anchors + scale (fixed kappa=gamma=0, beta=0 -> the hyperparameter-free
'unit'/'se' modes), and only swap the single pooled quantile for per-band quantiles. A band whose
calibration support is below the conformal threshold (need |C_g| >= ceil(1/alpha)-1) has an
UNSUPPORTED quantile; that side falls back to the pooled quantile and is flagged, so a data gap
(e.g. an empty small-model band) surfaces honestly instead of silently clipping.
"""
from __future__ import annotations

import math
import re

import numpy as np

from .combiner import EvalBracket, Signals, conformal_quantile

# ---------------------------------------------------------------- taxonomy helpers
_PARAM_RE = re.compile(r"(\d+(?:[._]\d+)?)\s*([mb])(?:[^a-z]|$)")


def param_billions(model: str) -> float | None:
    """Parse a parameter count (in billions) from a HF model id. Robust to date/version tokens:
    only a number *immediately followed by* 'b'/'m' counts (so 'OLMo-2-1124-7B' -> 7.0, not 1124)."""
    hits = _PARAM_RE.findall(model.lower())
    if not hits:
        return None
    num, unit = hits[-1]                       # params are the last size token in every fleet name
    val = float(num.replace("_", "."))
    return val / 1000.0 if unit == "m" else val


def size_band(model: str) -> str:
    b = param_billions(model)
    if b is None:
        return "unknown"
    if b < 1.0:
        return "<1B"
    if b < 3.0:
        return "1-3B"
    return "3-10B"


def family_of(model: str) -> str:
    m = model.lower()
    for f in ("qwen", "llama", "gemma", "mistral", "olmo", "smollm", "stablelm", "tinyllama",
              "phi", "pythia", "falcon", "yi", "danube", "mpt", "internlm", "mobilellm"):
        if f in m:
            return "llama" if f == "tinyllama" else f
    return m.split("/")[0]


# ---------------------------------------------------------------- the estimator
def _fixed_eb(scale_mode: str, alpha_u: float, alpha_l: float) -> EvalBracket:
    """A hyperparameter-free combiner: anchors + scale only, no fit() needed."""
    eb = EvalBracket(scale_mode=scale_mode, alpha_u=alpha_u, alpha_l=alpha_l, allow_vacuous=True)
    eb.kappa, eb.gamma, eb.beta = 0.0, 0.0, (0.0, 0.0, 0.0)
    return eb


def mondrian_brackets(sig_cal: Signals, theta_cal, key_cal,
                      sig_test: Signals, key_test,
                      scale_mode: str = "se", alpha_u: float = 0.05, alpha_l: float = 0.05,
                      fallback: str = "pool", abstain: bool = True):
    """Per-band conditional brackets. Returns (lo, hi, info).

    key_cal / key_test: the band label per pair (e.g. size_band(model)). Test pairs whose band is
    unsupported in calibration use the pooled quantile (fallback='pool') or clip to the endpoint
    (fallback='endpoint'); either way info['fellback'] records which bands did so.
    """
    eb = _fixed_eb(scale_mode, alpha_u, alpha_l)
    theta_cal = np.asarray(theta_cal, float)
    key_cal = np.asarray(key_cal)
    key_test = np.asarray(key_test)

    s_c = eb._scale(sig_cal)
    r_u = (theta_cal - eb.upper_anchor(sig_cal)) / s_c
    r_l = (eb.lower_anchor(sig_cal) - theta_cal) / s_c

    qu_pool = conformal_quantile(r_u, alpha_u)
    ql_pool = conformal_quantile(r_l, alpha_l)
    need = math.ceil(1.0 / min(alpha_u, alpha_l)) - 1

    qu, ql, support, fellback = {}, {}, {}, set()
    for g in sorted(set(key_cal.tolist())):
        m = key_cal == g
        support[g] = int(m.sum())
        qu[g] = conformal_quantile(r_u[m], alpha_u)
        ql[g] = conformal_quantile(r_l[m], alpha_l)

    s_t = eb._scale(sig_test)
    u_t = eb.upper_anchor(sig_test)
    la_t = eb.lower_anchor(sig_test)
    n = len(sig_test)
    lo = np.empty(n)
    hi = np.empty(n)
    BIG = 1e9
    for i in range(n):
        g = key_test[i]
        q_u, q_l = qu.get(g), ql.get(g)
        if q_u is None or not math.isfinite(q_u):
            fellback.add(str(g))
            q_u = qu_pool if fallback == "pool" else math.inf
        if q_l is None or not math.isfinite(q_l):
            fellback.add(str(g))
            q_l = ql_pool if fallback == "pool" else math.inf
        hi[i] = u_t[i] + (q_u if math.isfinite(q_u) else BIG) * s_t[i]
        lo[i] = la_t[i] - (q_l if math.isfinite(q_l) else BIG) * s_t[i]
    hi = np.clip(hi, 0.0, 1.0)
    lo = np.clip(np.minimum(lo, hi), 0.0, 1.0)

    if abstain:
        trust, _, _ = eb.elicitation_trust(sig_test)
        hi = np.where(trust, hi, 1.0)

    info = {"support": support, "q_u": qu, "q_l": ql, "q_u_pool": qu_pool, "q_l_pool": ql_pool,
            "need_per_band": need, "fellback": sorted(fellback)}
    return lo, hi, info
