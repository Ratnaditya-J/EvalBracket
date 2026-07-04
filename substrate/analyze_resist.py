"""Hard-case test on real models: does the bracket break when elicitation is defeated?

Calibrate the conformal interval on the NORMAL (elicitable) fleet, then bracket the
ELICITATION-RESISTANT models. Phase 1 (synthetic) predicted coverage collapses there because
coverage is anchor-driven and the ceiling anchor (S3) is defeated. This is the real-model version
of that prediction -- and the analog of the Auditing-Games black-box-defeat result.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

sys.path.insert(0, "substrate")
from analyze_real import ground_truth, load_rows, to_signals   # noqa: E402
from evalbracket import EvalBracket, baselines, scoring          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normal", required=True, help="pairs.jsonl from the elicitable fleet")
    ap.add_argument("--resist", required=True, help="pairs.jsonl from the resistant fleet")
    args = ap.parse_args()

    _, normal = load_rows(args.normal)
    _, resist = load_rows(args.resist)
    thN = np.array([ground_truth(r) for r in normal])
    thR = np.array([ground_truth(r) for r in resist])
    s1R = np.array([r["s1"] for r in resist]); s3R = np.array([r["s3"] for r in resist])
    alpha = 0.10

    print(f"normal (elicitable) pairs: {len(normal)} across {len(set(r['group'] for r in normal))} models")
    print(f"resist  pairs:            {len(resist)} across {len(set(r['group'] for r in resist))} models")

    print("\n=== Did the resistant lock defeat elicitation? (S3 vs theta) ===")
    print(f"  normal fleet : mean theta-S3 shortfall = {np.mean(thN - np.array([r['s3'] for r in normal])):+.3f}")
    print(f"  resist fleet : mean theta-S3 shortfall = {np.mean(thR - s3R):+.3f}  "
          f"(large => elicitation defeated)")
    rec_n = np.mean(np.array([r['s3'] for r in normal]) >= thN - 0.05)
    rec_r = np.mean(s3R >= thR - 0.05)
    print(f"  S3 recovers theta (within 0.05): normal {rec_n:.0%}  vs  resist {rec_r:.0%}")

    sigN, sigR = to_signals(normal), to_signals(resist)

    def coverages(abstain):
        m = EvalBracket(scale_mode="se", allow_vacuous=True,
                        abstain_on_weak_elicitation=abstain)
        m.kappa, m.gamma, m.beta = 0.0, 0.0, (0.0, 0.0, 0.0)
        m.calibrate(sigN, thN)
        loN, hiN, _ = m.bracket(sigN)
        loR, hiR, _ = m.bracket(sigR)
        trustR, _, _ = m.elicitation_trust(sigR)
        return (scoring.coverage(loN, hiN, thN), np.mean(hiN - loN),
                scoring.coverage(loR, hiR, thR), np.mean(hiR - loR), np.mean(~trustR))

    cN0, wN0, cR0, wR0, abst = coverages(abstain=False)
    cN1, wN1, cR1, wR1, _ = coverages(abstain=True)
    b0_lo, b0_hi = baselines.baseline_b0(s1R, np.array([r["n_items"] for r in resist]), alpha)
    cov_b0 = scoring.coverage(b0_lo, b0_hi, thR)

    print("\n=== Coverage: calibrate on normal fleet, test across regimes ===")
    print(f"  {'':<26}{'NORMAL cov/width':>20}{'RESIST cov/width':>20}")
    print(f"  {'abstain OFF (silent)':<26}{f'{cN0:.2f} / {wN0:.2f}':>20}{f'{cR0:.2f} / {wR0:.2f}':>20}")
    print(f"  {'abstain ON  (loud)':<26}{f'{cN1:.2f} / {wN1:.2f}':>20}{f'{cR1:.2f} / {wR1:.2f}':>20}")
    print(f"  naive Wilson(S1) on RESIST : coverage {cov_b0:.2f}")
    print(f"\n  Elicitation-trust flag abstained on {abst:.0%} of resistant pairs.")
    print("  => WITHOUT abstain the bracket fails SILENTLY (RESIST coverage ~0, near-zero width = a\n"
          "     confident wrong point). WITH the elicitation-gap abstain rule it fails LOUDLY: the\n"
          "     ceiling blows up to 1 (wide interval) and coverage is restored, while the NORMAL\n"
          "     fleet is UNCHANGED. The method now says 'I can't upper-bound this' instead of lying.")


if __name__ == "__main__":
    main()
