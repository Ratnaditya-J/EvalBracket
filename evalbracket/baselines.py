"""Baseline interval methods EvalBracket must beat (spec v0.1 §4).

A point score has no interval, so "beat the raw point score" is operationalized as beating a
binomial confidence interval placed around that score. The ladder:

    B0 = Wilson CI around S1  (suppressed observed accuracy) -- the naive system-card read.
         Centered below theta; should systematically MISS HIGH. "Does fusion beat doing nothing."
    B1 = Wilson CI around S3  (elicitation estimate alone, no fusion, no awareness widening).
         Isolates what the fusion adds beyond "just report the elicited number."

Both are scored by coverage AND interval score, identically to EvalBracket (B2).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def wilson_interval(k, n, alpha):
    """Two-sided Wilson score interval for a binomial proportion at level ``alpha``.

    ``k`` successes out of ``n`` trials. Returns (lo, hi), clipped to [0, 1]. Vectorized over
    array-like k, n. Nominal two-sided coverage 1 - alpha, matching the conformal interval's level.
    """
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    z = norm.ppf(1.0 - alpha / 2.0)
    safe_n = np.where(n > 0, n, 1.0)                       # avoid div-by-zero; masked out below
    phat = np.divide(k, safe_n, out=np.full_like(k, 0.5, dtype=float), where=n > 0)
    denom = 1.0 + z * z / safe_n
    center = (phat + z * z / (2.0 * safe_n)) / denom
    half = (z * np.sqrt(phat * (1.0 - phat) / safe_n + z * z / (4.0 * safe_n * safe_n))) / denom
    lo = np.clip(center - half, 0.0, 1.0)
    hi = np.clip(center + half, 0.0, 1.0)
    # n == 0: no information -> the vacuous but honest interval [0, 1]
    lo = np.where(n > 0, lo, 0.0)
    hi = np.where(n > 0, hi, 1.0)
    return lo, hi


def wilson_from_accuracy(acc, n_items, alpha):
    """Wilson CI given an accuracy in [0, 1] and the item count it was estimated from."""
    acc = np.asarray(acc, dtype=float)
    n_items = np.asarray(n_items, dtype=float)
    k = np.rint(acc * n_items)
    return wilson_interval(k, n_items, alpha)


def baseline_b0(s1, n_items, alpha):
    """B0: Wilson CI around the suppressed observed score S1."""
    return wilson_from_accuracy(s1, n_items, alpha)


def baseline_b1(s3, n_items, alpha):
    """B1: Wilson CI around the elicitation ceiling estimate S3 (fusion-free)."""
    return wilson_from_accuracy(s3, n_items, alpha)
