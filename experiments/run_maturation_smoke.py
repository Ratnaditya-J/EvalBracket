"""ESTIMATOR SMOKE TEST for the maturation lag instrument (NOT a science result).

This validates the ESTIMATOR against known truth (a planted, varied lag). It says nothing about
whether real capabilities mature ceiling-first -- that is Stage 1b (emergent lag) / Stage 2
(public checkpoints). Here we only certify: in the trustworthy regime the estimator is ~unbiased,
its bootstrap CI covers the planted lag at ~nominal rate, and OUTSIDE the trustworthy regime the
`identified` gate correctly refuses (near-linear emergence, inflection outside the window).
"""
from __future__ import annotations

import json

import numpy as np

from evalbracket import maturation, maturation_synth


def main():
    planted = [0.0, 1.0, 2.0, 3.0]
    seeds = range(15)

    # --- 1. recovery + CI coverage in the TRUSTWORTHY regime (steep, inflection in-window) ---
    print("=== A. Trustworthy regime (tau=1.1, inflection in-window) ===")
    print(f"{'planted':>8}{'rec lag':>10}{'CI cover':>10}{'identified':>12}")
    rec, plant, covered, ident = [], [], [], []
    for L in planted:
        for s in seeds:
            d = maturation_synth.generate_series(T=12, t0=4.5, tau=1.1, lag=L,
                                                 n_items=500, seed=s + int(L * 100))
            r = maturation.analyze_series(d["t"], d["ceiling"], d["floor"],
                                          n_items=d["n_items"], planted_lag=L, seed=s)
            rec.append(r["lag"]); plant.append(L)
            covered.append(r["lag_ci_low"] <= L <= r["lag_ci_high"]); ident.append(r["identified"])
    rec = np.array(rec); plant = np.array(plant)
    for L in planted:
        m = plant == L
        print(f"{L:>8.1f}{np.mean(rec[m]):>10.2f}{np.mean(np.array(covered)[m]):>10.0%}"
              f"{np.mean(np.array(ident)[m]):>12.0%}")
    mae = float(np.mean(np.abs(rec - plant)))
    corr = float(np.corrcoef(rec, plant)[0, 1])
    coverage = float(np.mean(covered))
    ident_rate = float(np.mean(ident))
    print(f"  MAE={mae:.2f}  corr-with-planted={corr:.3f}  CI-coverage={coverage:.0%}  "
          f"identified={ident_rate:.0%}")

    # --- 2. the gate must REFUSE outside the trustworthy regime ---
    print("\n=== B. Un-trustworthy regimes: the gate should refuse (identified=False) ===")
    bad_ident = {}
    # near-linear emergence (large tau)
    for label, kw in [("near-linear (tau=6)", dict(t0=6.0, tau=6.0, lag=2.0)),
                      ("inflection past window (t0=14)", dict(t0=14.0, tau=1.1, lag=2.0)),
                      ("inflection before window (t0=-2)", dict(t0=-2.0, tau=1.1, lag=2.0))]:
        flags = []
        for s in seeds:
            d = maturation_synth.generate_series(T=12, n_items=500, seed=s, **kw)
            r = maturation.analyze_series(d["t"], d["ceiling"], d["floor"],
                                          n_items=d["n_items"], seed=s)
            flags.append(r["identified"])
        bad_ident[label] = float(np.mean(flags))
        print(f"  {label:<34} identified={bad_ident[label]:.0%}  (want ~0%)")

    checks = {
        "recovers_lag_in_regime": mae < 0.5,
        "tracks_varied_lag": corr > 0.9,
        "ci_covers_planted": coverage >= 0.85,
        "identified_in_good_regime": ident_rate >= 0.8,
        "gate_refuses_near_linear": bad_ident["near-linear (tau=6)"] <= 0.2,
        "gate_refuses_inflection_out": max(bad_ident["inflection past window (t0=14)"],
                                           bad_ident["inflection before window (t0=-2)"]) <= 0.2,
    }
    print("\n=== Pass conditions ===")
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(json.dumps({"checks": checks, "all_pass": all(checks.values())}))
    return all(checks.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
