"""Analyze the Stage 1b emergent-lag trajectories.

Non-circular test: the ceiling->floor lag was NOT planted; it emerges from the suppression-decay
schedule (s_mid) interacting with memorization speed. So the scientific checks are:
  1. Does the maturation instrument recover an emergent lag (identified=True) from the measured
     [floor, ceiling] trajectory?
  2. Does the recovered lag TRACK s_mid -- later suppression decay => larger lag, and EARLY decay
     => lag ~ 0 (the falsifying case the design must be able to produce)?
  3. Width lifecycle state per trajectory (complete / widening / none).
theta ceiling here = password-on recall (privileged / white-box analog); floor = password-off recall.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from evalbracket import maturation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", required=True)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.traj) if l.strip()]
    rows.sort(key=lambda r: r["s_mid"])
    print(f"loaded {len(rows)} trajectories\n")

    print(f"{'s_mid':>7}{'lag':>8}{'CI':>16}{'ident':>7}{'width':>10}{'ceil_end':>9}{'floor_end':>10}")
    s_mids, lags = [], []
    for r in rows:
        v = r["versions"]
        t = np.arange(len(v), dtype=float)
        ceiling = np.array([x["ceiling"] for x in v])
        floor = np.array([x["floor"] for x in v])
        res = maturation.analyze_series(t, ceiling, floor, n_items=r["n_items"], seed=0)
        ci = f"[{res.get('lag_ci_low', float('nan')):.1f},{res.get('lag_ci_high', float('nan')):.1f}]"
        print(f"{r['s_mid']:>7.2f}{res['lag']:>8.2f}{ci:>16}{str(res['identified']):>7}"
              f"{res['state']:>10}{ceiling[-1]:>9.2f}{floor[-1]:>10.2f}")
        if res["identified"]:
            s_mids.append(r["s_mid"]); lags.append(res["lag"])

    print("\n=== Emergent-lag findings ===")
    if len(s_mids) >= 3:
        corr = float(np.corrcoef(s_mids, lags)[0, 1])
        print(f"  recovered lag TRACKS suppression-decay s_mid: corr={corr:.3f} "
              f"(>0 => later decay -> larger lag, the emergent signature)")
        print(f"  => {'CONFIRMED emergent + falsifiable: lag varies with the mechanism, not planted' if corr > 0.7 else 'weak/absent tracking -- inspect trajectories'}")
    else:
        print(f"  only {len(s_mids)} identified trajectories; need >=3 to test tracking. "
              "Inspect width states / ceiling recovery above.")


if __name__ == "__main__":
    main()
