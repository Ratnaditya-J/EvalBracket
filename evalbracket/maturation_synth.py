"""Synthetic maturation series with a KNOWN planted lag (validates the RQ4 instrument).

Capability emerges as a sigmoid across versions t=1..T. The floor is the ceiling delayed by L
versions: floor(t) = ceiling(t - L). Each measured accuracy carries binomial item noise. A correct
instrument must recover L (and recover a VARIED L), and flag the widen-then-narrow width signature.
Because we plant L and vary it, "we recovered L" is a calibration result, not a tautology.
"""
from __future__ import annotations

import numpy as np

from .maturation import sigmoid


def generate_series(T=10, t0=4.0, tau=1.2, lag=2.0, lo=0.25, hi=0.95, n_items=400, seed=0):
    """Return dict with t, ceiling (true & measured), floor (true & measured), planted lag."""
    rng = np.random.default_rng(seed)
    t = np.arange(1, T + 1, dtype=float)
    ceiling_true = sigmoid(t, lo, hi, t0, tau)
    floor_true = sigmoid(t, lo, hi, t0 + lag, tau)          # floor = ceiling delayed by `lag`
    ceiling_obs = rng.binomial(n_items, np.clip(ceiling_true, 0, 1)) / n_items
    floor_obs = rng.binomial(n_items, np.clip(floor_true, 0, 1)) / n_items
    return {
        "t": t, "planted_lag": float(lag),
        "ceiling_true": ceiling_true, "floor_true": floor_true,
        "ceiling": ceiling_obs, "floor": floor_obs, "n_items": n_items,
    }
