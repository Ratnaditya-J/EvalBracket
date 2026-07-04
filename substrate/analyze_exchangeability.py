"""Exchangeability study: marginal vs group-conditional (Mondrian) coverage, under both
leave-one-MODEL-out (LOMO) and the harder leave-one-FAMILY-out (LOFO).

Proves the Mondrian estimator is correct on known truth and quantifies where the current fleet is
too thin to certify a per-band guarantee (motivating the expanded fleet). Marginal coverage should
reproduce the paper's ~0.89; the interesting numbers are per-band and LOFO.
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "substrate")
from analyze_real import ground_truth, load_rows, to_signals   # noqa: E402
from evalbracket import Signals                                  # noqa: E402
from evalbracket.mondrian import family_of, mondrian_brackets, param_billions, size_band  # noqa: E402


def _cov(theta, lo, hi):
    v = ~np.isnan(lo)
    if v.sum() == 0:
        return float("nan"), 0
    return float(np.mean((theta[v] >= lo[v] - 1e-9) & (theta[v] <= hi[v] + 1e-9))), int(v.sum())


def _width(lo, hi):
    v = ~np.isnan(lo)
    return float(np.mean(hi[v] - lo[v])) if v.sum() else float("nan")


def run(path, scale_mode="se", alpha_u=0.05, alpha_l=0.05):
    rows, good = load_rows(path)
    theta = np.array([ground_truth(r) for r in good])
    grp = np.array([r["group"] for r in good])
    band = np.array([size_band(r["group"]) for r in good])
    fam = np.array([family_of(r["group"]) for r in good])
    sig = to_signals(good)

    print(f"\n=== {path}  ({len(good)} valid pairs, {len(set(grp))} models) ===")
    print("size-band composition (models):")
    for b in ["<1B", "1-3B", "3-10B", "unknown"]:
        ms = sorted(set(m for m in set(grp) if size_band(m) == b))
        if ms:
            print(f"  {b:6s}: {len(ms)} models, {int((band==b).sum())} pairs  "
                  + ", ".join(f"{m.split('/')[-1]}({param_billions(m)})" for m in ms))

    def held_out(hold_key, held_arr):
        """Generic leave-one-<key>-out over the values of held_arr. Returns (marg_lo,marg_hi,
        mond_lo,mond_hi) aligned to `good`."""
        m_lo = np.full(len(good), np.nan); m_hi = np.full(len(good), np.nan)
        d_lo = np.full(len(good), np.nan); d_hi = np.full(len(good), np.nan)
        for h in sorted(set(held_arr.tolist())):
            tr = np.where(held_arr != h)[0]
            te = np.where(held_arr == h)[0]
            if len(set(grp[tr])) < 3:
                continue
            # marginal = single pooled band
            lo, hi, _ = mondrian_brackets(sig.subset(tr), theta[tr], np.zeros(len(tr)),
                                          sig.subset(te), np.zeros(len(te)),
                                          scale_mode=scale_mode, alpha_u=alpha_u, alpha_l=alpha_l)
            m_lo[te], m_hi[te] = lo, hi
            # mondrian = per size-band
            lo, hi, _ = mondrian_brackets(sig.subset(tr), theta[tr], band[tr],
                                          sig.subset(te), band[te],
                                          scale_mode=scale_mode, alpha_u=alpha_u, alpha_l=alpha_l)
            d_lo[te], d_hi[te] = lo, hi
        return m_lo, m_hi, d_lo, d_hi

    for name, held_arr in [("leave-one-MODEL-out", grp), ("leave-one-FAMILY-out", fam)]:
        m_lo, m_hi, d_lo, d_hi = held_out(name, held_arr)
        mc, mn = _cov(theta, m_lo, m_hi)
        dc, dn = _cov(theta, d_lo, d_hi)
        print(f"\n{name}  (nominal {1-alpha_u-alpha_l:.2f})")
        print(f"  marginal  : coverage {mc:.3f}  width {_width(m_lo,m_hi):.3f}  (n={mn})")
        print(f"  Mondrian  : coverage {dc:.3f}  width {_width(d_lo,d_hi):.3f}  (n={dn})")
        print("  per-band coverage (Mondrian):")
        for b in ["<1B", "1-3B", "3-10B"]:
            bm = (band == b) & ~np.isnan(d_lo)
            if bm.sum():
                c = np.mean((theta[bm] >= d_lo[bm]-1e-9) & (theta[bm] <= d_hi[bm]+1e-9))
                print(f"      {b:6s}: {c:.3f}  (n={int(bm.sum())})")
            else:
                print(f"      {b:6s}: (no supported pairs)")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data_snapshot/pairs2_disjoint_diverse.jsonl"
    run(path)
