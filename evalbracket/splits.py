"""Group-disjoint (leave-one-model-out) splitting (spec v0.1 §3.2).

Pairs from the same model must never straddle fit / calibration / test, or the conformal coverage
guarantee is contaminated by within-model leakage. All splits are by group (model id).
"""
from __future__ import annotations

import numpy as np


def split_by_group(groups, fractions=(0.4, 0.3, 0.3), seed=0):
    """Partition group ids into (fit, cal, test) index arrays, disjoint by group.

    fractions are over the number of distinct groups, not pairs.
    """
    groups = np.asarray(groups)
    uniq = np.array(sorted(set(groups.tolist())))
    rng = np.random.default_rng(seed)
    rng.shuffle(uniq)
    n = len(uniq)
    n_fit = max(1, int(round(fractions[0] * n)))
    n_cal = max(1, int(round(fractions[1] * n)))
    fit_g = set(uniq[:n_fit].tolist())
    cal_g = set(uniq[n_fit:n_fit + n_cal].tolist())
    test_g = set(uniq[n_fit + n_cal:].tolist())
    fit_idx = np.where(np.isin(groups, list(fit_g)))[0]
    cal_idx = np.where(np.isin(groups, list(cal_g)))[0]
    test_idx = np.where(np.isin(groups, list(test_g)))[0]
    return fit_idx, cal_idx, test_idx
