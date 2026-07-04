"""Evaluation metrics for prediction intervals (spec v0.1 §3.3).

Coverage alone is gameable: the interval [0, 1] has perfect coverage and zero information. So every
result reports coverage AND a proper scoring rule (the Winkler / interval score) that pays for width
and is penalized for misses. A method that wins only one is not a win.
"""
from __future__ import annotations

import numpy as np


def covered(lo, hi, truth):
    """Boolean per-pair coverage: is truth inside the closed interval [lo, hi]?"""
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    truth = np.asarray(truth, dtype=float)
    return (truth >= lo) & (truth <= hi)


def coverage(lo, hi, truth):
    """Marginal coverage rate over a set of pairs. Target ~= 1 - alpha (spec §3.1)."""
    return float(np.mean(covered(lo, hi, truth)))


def interval_score(lo, hi, truth, alpha):
    """Winkler / Gneiting-Raftery interval score at level ``alpha`` (lower is better).

        IS_alpha = (hi - lo)
                   + (2/alpha) * (lo - truth) * 1[truth < lo]     # miss low
                   + (2/alpha) * (truth - hi) * 1[truth > hi]     # miss high

    Proper scoring rule for a central (1 - alpha) interval: rewards narrow intervals, penalizes
    misses in proportion to 1/alpha. This is the pre-registered headline metric for RQ1: at matched
    nominal coverage, EvalBracket must attain a lower mean interval score than every baseline.
    """
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    truth = np.asarray(truth, dtype=float)
    width = hi - lo
    below = np.maximum(lo - truth, 0.0)
    above = np.maximum(truth - hi, 0.0)
    return width + (2.0 / alpha) * (below + above)


def mean_interval_score(lo, hi, truth, alpha):
    return float(np.mean(interval_score(lo, hi, truth, alpha)))


def mean_width(lo, hi):
    """Sharpness: average interval width. Only meaningful alongside coverage."""
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    return float(np.mean(hi - lo))


def summarize(lo, hi, truth, alpha, label=""):
    """Bundle the three numbers every run reports for one interval method."""
    return {
        "label": label,
        "alpha": alpha,
        "coverage": coverage(lo, hi, truth),
        "mean_interval_score": mean_interval_score(lo, hi, truth, alpha),
        "mean_width": mean_width(lo, hi),
        "n": int(len(np.asarray(truth))),
    }
