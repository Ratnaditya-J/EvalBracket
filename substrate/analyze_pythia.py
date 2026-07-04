"""Stage 2 analysis: does the fine-tune ceiling lead the 0-shot floor for a NATURALLY emerging
capability on Pythia? Time axis = log10(step) (capabilities emerge on a log-step scale).

Pre-registered readings (design review):
  - identified lag > 0  : ceiling (fine-tune-reachable) leads floor (default) => latent-before-
                          default signature PRESENT for this natural capability.
  - identified lag ~ 0  : constant vertical gap, no timing lead => honest NULL.
  - identified=False    : instrument can't certify (gradual/noisy curve) => INCONCLUSIVE, not evidence.
Also reports the few-shot DIAGNOSTIC curve to expose the in-context-learning confound the review
flagged (few-shot is NOT used as the ceiling).
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
    print(f"loaded {len(rows)} task trajectories\n")

    for r in rows:
        v = r["versions"]
        step = np.array([x["step"] for x in v], dtype=float)
        t = np.log10(np.clip(step, 1, None))               # emergence is ~linear in log-steps
        floor = np.array([x["floor"] for x in v])
        ceiling = np.array([x["ceiling"] for x in v])
        fewshot = np.array([x.get("fewshot", np.nan) for x in v])
        res = maturation.analyze_series(t, ceiling, floor, n_items=r["n_items"], seed=0)

        print(f"=== task={r['task']}  model={r['model']} ({len(v)} checkpoints) ===")
        print(f"  floor(0shot):  {floor[0]:.2f} -> {floor[-1]:.2f}")
        print(f"  ceiling(ft):   {ceiling[0]:.2f} -> {ceiling[-1]:.2f}")
        print(f"  fewshot(diag): {fewshot[0]:.2f} -> {fewshot[-1]:.2f}  (NOT the ceiling; ICL confound check)")
        print(f"  ceiling inflection (log-step)={res['ceiling_inflection']:.2f}  "
              f"floor inflection={res['floor_inflection']:.2f}  tau_c={res['ceiling_tau']:.2f} "
              f"tau_f={res['floor_tau']:.2f}")
        lag = res["lag"]
        ci = f"[{res.get('lag_ci_low', float('nan')):.2f},{res.get('lag_ci_high', float('nan')):.2f}]"
        print(f"  LAG (ceiling->floor, log-step units) = {lag:+.2f}  CI={ci}  "
              f"identified={res['identified']}  width_state={res['state']}")
        if not res["identified"]:
            fails = [k for k, ok in res["reasons"].items() if not ok]
            print(f"  -> INCONCLUSIVE (gate failed: {', '.join(fails)}) -- cannot certify a lag here.")
        elif lag > 0.15:
            print(f"  -> SIGNATURE PRESENT: fine-tune ceiling leads 0-shot floor "
                  f"(latent reachable before default).")
        elif abs(lag) <= 0.15:
            print(f"  -> NULL: constant gap, no timing lead (honest negative).")
        else:
            print(f"  -> INVERTED: floor leads ceiling (unexpected; inspect).")
        # ICL confound: does few-shot track the fine-tune ceiling or lag it?
        if np.all(np.isfinite(fewshot)):
            print(f"  ICL diagnostic: mean(fewshot-floor)={np.mean(fewshot-floor):+.2f}, "
                  f"mean(ceiling-fewshot)={np.mean(ceiling-fewshot):+.2f} "
                  f"(fine-tune ceiling above few-shot => ft elicits more than ICL)")
        print()


if __name__ == "__main__":
    main()
