"""Maturation instrument (RQ4): does the [floor, ceiling] range's trajectory over a version series
recover a capability-maturation signature, and can it recover the ceiling->floor LAG?

Hypothesis (spec §0 pt 2): as a capability matures, the ceiling (elicitable) leads the floor
(reliable) by a lag L; the width goes low -> wide -> narrow-high; the lag is the forecast lead time.

HONESTY GUARDS (from two adversarial reviews). A shifted *linear* ramp is unidentifiable, and a
sigmoid lag is only identifiable when the emergence is steep enough (tau < span/3) AND both
inflection points sit inside the observed version window. Outside that regime the point estimate is
silently wrong by 1-5 versions. So this module NEVER returns a bare lag: it returns a lag with a
parametric-bootstrap CI and an `identified` flag that gates on (a) tau/window sanity, (b) fit R²,
and (c) agreement between two independent estimators (sigmoid-inflection vs model-free shift) --
their disagreement tracks the true error ~1:1. Un-identified series are reported as such, not as a
number. Trustworthy regime: tau < span/3, both inflections in-window, T >= 10, n_items >= 350,
lag <~ 0.6*span.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit

AGREEMENT_TOL = 0.75          # |lag_sigmoid - lag_shift| below this => estimators agree
R2_MIN = 0.90


def sigmoid(t, lo, hi, t0, tau):
    z = np.clip(-(np.asarray(t, float) - t0) / tau, -50.0, 50.0)   # clip avoids exp overflow
    return lo + (hi - lo) / (1.0 + np.exp(z))


def fit_emergence(t, y):
    """Least-squares sigmoid fit with an R² goodness score (converged != correct)."""
    t = np.asarray(t, float); y = np.asarray(y, float)
    lo0, hi0 = float(np.min(y)), float(np.max(y))
    span = t[-1] - t[0]
    p0 = [lo0, max(hi0, lo0 + 1e-3), float(np.mean(t)), max(span / 6.0, 1e-2)]
    bounds = ([0.0, 0.0, t[0] - span, 1e-3], [1.0, 1.0, t[-1] + span, span * 4 + 1.0])
    try:
        popt, _ = curve_fit(sigmoid, t, y, p0=p0, bounds=bounds, maxfev=20000)
        resid = y - sigmoid(t, *popt)
        ss_res = float(np.sum(resid ** 2)); ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
        return {"lo": popt[0], "hi": popt[1], "t0": popt[2], "tau": popt[3], "r2": r2}
    except Exception:
        return {"lo": lo0, "hi": hi0, "t0": float(np.mean(t)), "tau": span, "r2": 0.0}


def estimate_lag_sigmoid(t, ceiling, floor):
    fc = fit_emergence(t, ceiling); ff = fit_emergence(t, floor)
    return ff["t0"] - fc["t0"], fc, ff


def estimate_lag_shift(t, ceiling, floor, max_lag=None, oversample=10, min_overlap_frac=0.5):
    """Model-free lag: shift s minimising MSE(floor, ceiling delayed by s). Guards against the
    'fewer points => lower MSE' edge bias by requiring >= min_overlap_frac of points overlap, and
    flags edge-pinned solutions (untrustworthy)."""
    t = np.asarray(t, float); ceiling = np.asarray(ceiling, float); floor = np.asarray(floor, float)
    span = t[-1] - t[0]
    max_lag = span * 0.9 if max_lag is None else max_lag
    lags = np.linspace(0.0, max_lag, int(max_lag * oversample) + 1)
    need = max(3, int(np.ceil(min_overlap_frac * len(t))))
    best, best_mse = 0.0, np.inf
    for s in lags:
        shifted = np.interp(t - s, t, ceiling)
        mask = (t - s) >= t[0]
        if mask.sum() < need:
            break                                     # deeper shifts only lose points
        mse = float(np.mean((floor[mask] - shifted[mask]) ** 2))
        if mse < best_mse:
            best, best_mse = float(s), mse
    grid_step = lags[1] - lags[0] if len(lags) > 1 else 1.0
    edge_pinned = best >= max_lag - grid_step - 1e-9
    return best, best_mse, edge_pinned


def width_lifecycle(ceiling, floor):
    """Three-state width diagnostic: 'complete' (widen->narrow), 'widening' (incomplete maturation,
    floor still catching up at vT), or 'none'. Never collapses 'incomplete' into 'absent'."""
    ceiling = np.asarray(ceiling, float); floor = np.asarray(floor, float)
    w = ceiling - floor
    peak = int(np.argmax(w))
    rose = w[peak] > w[0] + 1e-3
    fell_after = peak < len(w) - 1 and w[peak] > w[-1] + 1e-3
    near_end = peak >= len(w) - 2
    if rose and fell_after and not near_end:
        state = "complete"          # low -> wide -> narrow-high
    elif rose and (near_end or w[-1] > w[0] + 1e-3):
        state = "widening"          # real but incomplete maturation
    else:
        state = "none"
    return {
        "widths": w, "peak_index": peak, "state": state,
        "max_width": float(w[peak]), "final_width": float(w[-1]), "start_width": float(w[0]),
        "widen_then_narrow": state == "complete",
        "final_ceiling": float(ceiling[-1]),
    }


def _bootstrap_lag_ci(t, ceiling, floor, n_items, n_boot=200, seed=0):
    """Parametric bootstrap over the known binomial item noise; percentile CI on the shift lag."""
    rng = np.random.default_rng(seed)
    n_items = np.broadcast_to(np.asarray(n_items, float), np.asarray(ceiling).shape)
    lags = []
    for _ in range(n_boot):
        cb = rng.binomial(n_items.astype(int), np.clip(ceiling, 0, 1)) / n_items
        fb = rng.binomial(n_items.astype(int), np.clip(floor, 0, 1)) / n_items
        s, _, _ = estimate_lag_shift(t, cb, fb)
        lags.append(s)
    lags = np.array(lags)
    return float(np.percentile(lags, 2.5)), float(np.percentile(lags, 97.5)), float(np.std(lags))


def analyze_series(t, ceiling, floor, n_items=None, planted_lag=None, n_boot=200, seed=0):
    """Full RQ4 read for one version series. Returns lag estimates, a CI, and an `identified` gate.
    NEVER trust `lag` when `identified` is False -- it is silently wrong outside the trustworthy
    regime (near-linear emergence, inflection outside the window)."""
    t = np.asarray(t, float)
    span = t[-1] - t[0]
    lag_sig, fc, ff = estimate_lag_sigmoid(t, ceiling, floor)
    lag_shift, _, edge_pinned = estimate_lag_shift(t, ceiling, floor)
    life = width_lifecycle(ceiling, floor)

    # identifiability gate (the validity signal both reviews demanded)
    tau_ok = fc["tau"] < span / 3.0 and ff["tau"] < span / 3.0
    margin = span * 0.05
    t0_in = (t[0] - margin <= fc["t0"] <= t[-1] + margin) and (t[0] - margin <= ff["t0"] <= t[-1] + margin)
    fit_ok = fc["r2"] >= R2_MIN and ff["r2"] >= R2_MIN
    agree = abs(lag_sig - lag_shift) < AGREEMENT_TOL
    identified = bool(tau_ok and t0_in and fit_ok and agree and not edge_pinned)
    reasons = {"tau_ok": tau_ok, "inflections_in_window": t0_in, "fit_r2_ok": fit_ok,
               "estimators_agree": agree, "not_edge_pinned": not edge_pinned}

    lag = float(np.mean([lag_sig, lag_shift]))          # combined point estimate (use only if identified)
    out = {
        "lag": lag, "lag_sigmoid": float(lag_sig), "lag_shift": float(lag_shift),
        "identified": identified, "reasons": reasons,
        "ceiling_tau": fc["tau"], "floor_tau": ff["tau"],
        "ceiling_inflection": fc["t0"], "floor_inflection": ff["t0"],
        "ceiling_r2": fc["r2"], "floor_r2": ff["r2"], "edge_pinned": edge_pinned,
        **life,
    }
    if n_items is not None:
        lo, hi, sd = _bootstrap_lag_ci(t, ceiling, floor, n_items, n_boot=n_boot, seed=seed)
        out["lag_ci_low"], out["lag_ci_high"], out["lag_sd"] = lo, hi, sd
    if planted_lag is not None:
        out["planted_lag"] = float(planted_lag)
        out["lag_err"] = float(lag - planted_lag)
    return out
