"""Phase 4 analysis: RQ2 (arm head-to-head) + RQ3 (disguise ceiling delta_head) on real locked models.

Consumes arms.jsonl (from fleet_arms.sh). The mitigation arms are {disguise, cooperate}; raw = the
suppressed baseline (== S1). Using the sample-split unbiased s_mit (spec §5 / decomposition.py):

    delta_aware = s_mit - raw          gap closable by a prompt intervention (disguise/cooperate)
    delta_head  = th_on - s_mit        the disguise ceiling: closable only by elicitation/fine-tune

SCOPE (see arms.py): on a password lock, "disguise" is deployment-framing and "cooperate" is an
explicit cooperation prompt -- these test prompt-elicitation, not eval-type uncertainty. A large
delta_head here means prompts don't defeat the lock (only few-shot/password do), which is the
expected and honest finding for this substrate, not evidence about the Thomson/Li disguise hypothesis.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from evalbracket import decomposition


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.arms) if l.strip()]
    if not rows:
        print("no arm rows yet"); return
    grp = np.array([r["group"] for r in rows])
    th_on = np.array([r["theta_locked_pwdon"] for r in rows])
    raw = np.array([r["arm_raw_val"] for r in rows])
    # unbiased best-mitigation-arm value: select winner on the 'sel' halves, value on 'val' halves
    s_mit, winner = decomposition.unbiased_s_mit(
        np.array([r["arm_disguise_sel"] for r in rows]),
        np.array([r["arm_coop_sel"] for r in rows]),
        np.array([r["arm_disguise_val"] for r in rows]),
        np.array([r["arm_coop_val"] for r in rows]),
    )
    print(f"loaded {len(rows)} arm rows across {len(set(grp))} models\n")
    print("=== RQ2: arm head-to-head (mean accuracy, password-off) ===")
    print(f"  raw (plain)      = {raw.mean():.3f}")
    print(f"  disguise (deploy)= {np.mean([r['arm_disguise_val'] for r in rows]):.3f}")
    print(f"  cooperate        = {np.mean([r['arm_coop_val'] for r in rows]):.3f}")
    print(f"  best mitigation  = {s_mit.mean():.3f}  (winner: "
          f"disguise {np.mean(winner=='B'):.0%} / coop {np.mean(winner=='C'):.0%})")
    print(f"  th_on (password) = {th_on.mean():.3f}  <- true capability / ceiling")

    print("\n=== RQ3: disguise ceiling delta_head (unbiased + cluster bootstrap) ===")
    d = decomposition.decompose(th_on, raw, s_mit)
    dc = decomposition.disguise_ceiling_summary(th_on, raw, s_mit, group=grp)
    print(f"  delta_aware (prompt closes) = {np.mean(d['delta_aware']):+.3f}")
    print(f"  delta_head  (ceiling)       = {dc['mean_delta_head']:+.3f}  "
          f"95% CI [{dc['ci_low']:+.3f}, {dc['ci_high']:+.3f}]  "
          f"(excludes 0: {dc['excludes_zero']})")
    print(f"  delta_tot   (th_on - raw)   = {np.mean(d['delta_tot']):+.3f}")
    frac = np.mean(d['delta_aware']) / max(np.mean(d['delta_tot']), 1e-9)
    print(f"\n  Prompt interventions close {frac:.0%} of the suppression gap; the remaining "
          f"{1-frac:.0%} (delta_head) is the disguise ceiling -- closable only by elicitation/"
          f"fine-tune on this password-lock substrate.")


if __name__ == "__main__":
    main()
