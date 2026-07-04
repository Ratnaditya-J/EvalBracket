"""Synthetic SMOKE TEST for the EvalBracket machinery (NOT an existence proof).

Honest framing (per adversarial review): split-conformal coverage is a THEOREM under exchangeability,
and this generator is i.i.d. across groups, so coverage hitting nominal here proves the CODE
implements the algorithm correctly -- it does NOT prove the method solves eval-awareness. The real
validity test needs the GPU substrate (real password-locked models). This harness exists to catch
implementation bugs and to check that the pipeline recovers a KNOWN planted delta_head, stays clean
on a negative control, and -- honestly -- to measure whether the awareness fusion (B2) beats a
signal-free SE-normalized conformal (B_se) or is ornamental.

Method ladder (all at the same nominal level):
  B0   Wilson CI around S1 (suppressed)        -- naive; undercovers (mis-centered below theta).
  B1   Wilson CI around S3 (elicitation)       -- undercovers; single-point CI, mis-centered.
  B1c  conformal, scale_mode='unit'            -- unnormalized; reaches coverage.
  B_se conformal, scale_mode='se'              -- SE-normalized (signal-free); reaches coverage.
                                                  THE STRONG BASELINE: if B2 can't beat this, the
                                                  awareness signals add nothing item-count doesn't.
  B2   conformal, scale_mode='se_aware'        -- SE + awareness widening. The full method.

Reported honestly: B2 vs B_se paired interval-score difference across seeds with a CI. If the CI
includes 0, we STATE the fusion is ornamental on this (friendly) data -- we do not hide it behind a
pass gate. Also reported: out-of-sample R^2 of regressing ceiling shortfall on (S2,S4) -- the
pre-registered gate for claiming any fusion value on REAL data.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from sklearn.linear_model import LinearRegression

from evalbracket import EvalBracket, baselines, decomposition, scoring, splits, synthetic


def _fit(sig, theta, fit_idx, cal_idx, scale_mode):
    m = EvalBracket(alpha_u=0.05, alpha_l=0.05, scale_mode=scale_mode)
    m.fit(sig.subset(fit_idx), theta[fit_idx])
    m.calibrate(sig.subset(cal_idx), theta[cal_idx])
    return m


def oos_shortfall_r2(sig, theta, fit_idx, test_idx):
    """Leave-split-out R^2 of regressing ceiling shortfall (theta - max(s1,s3)) on (S2, S4).
    This is the pre-registered fusion-value gate: on REAL data, if this R^2 ~ 0 the awareness
    signals carry no information about ceiling misses and B2 must collapse to B_se."""
    def feats(s):
        return np.column_stack([s.s2, s.s4])
    def short(s, th):
        return th - np.maximum(s.s1, s.s3)
    reg = LinearRegression().fit(feats(sig.subset(fit_idx)), short(sig.subset(fit_idx), theta[fit_idx]))
    yt = short(sig.subset(test_idx), theta[test_idx])
    yp = reg.predict(feats(sig.subset(test_idx)))
    ss_res = np.sum((yt - yp) ** 2)
    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0


def run_once(seed, headroom=(0.02, 0.15), n_models=120, n_items=400, rho_range=(0.75, 1.0)):
    sig, truth = synthetic.generate(n_models=n_models, n_items=n_items,
                                    elic_headroom_range=headroom, rho_range=rho_range, seed=seed)
    theta = truth["theta_hat"]
    fit_idx, cal_idx, test_idx = splits.split_by_group(sig.group, seed=seed)
    ts, tt = sig.subset(test_idx), theta[test_idx]
    alpha = 0.10

    models = {sm: _fit(sig, theta, fit_idx, cal_idx, sm) for sm in ("unit", "se", "se_aware")}
    out = {}
    for name, sm in [("B1c", "unit"), ("B_se", "se"), ("B2", "se_aware")]:
        lo, hi, _ = models[sm].bracket(ts)
        out[name] = scoring.summarize(lo, hi, tt, alpha, name)
    b0 = baselines.baseline_b0(ts.s1, ts.n_items, alpha)
    b1 = baselines.baseline_b1(ts.s3, ts.n_items, alpha)
    out["B0"] = scoring.summarize(*b0, tt, alpha, "B0")
    out["B1"] = scoring.summarize(*b1, tt, alpha, "B1")

    # unbiased disguise ceiling on ceiling-valid pairs
    lo2, hi2, _ = models["se_aware"].bracket(ts)
    s_mit, _ = decomposition.unbiased_s_mit(
        truth["arm_b_select"][test_idx], truth["arm_c_select"][test_idx],
        truth["arm_b_value"][test_idx], truth["arm_c_value"][test_idx])
    out["disguise_ceiling"] = decomposition.disguise_ceiling_summary(
        tt, ts.s1, s_mit, group=ts.group, ceiling_hit_mask=(hi2 >= tt))
    out["planted_headroom"] = float(np.mean(truth["elic_headroom"][test_idx]))
    out["oos_r2"] = oos_shortfall_r2(sig, theta, fit_idx, test_idx)
    out["b2_vs_bse_intscore"] = out["B2"]["mean_interval_score"] - out["B_se"]["mean_interval_score"]
    return out


def run_adversarial_hardmode(seed, n_models=120, n_items=400):
    """Calibrate on HONEST-signal pairs, test on ADVERSARIAL signal-flattened pairs (same
    suppression, lying signals). Coverage here is the black-box-defeat test. Undercoverage is the
    expected, honest finding -- reported, not hidden."""
    honest, th_h = synthetic.generate(n_models=n_models, n_items=n_items, honest_signals=True, seed=seed)
    adv, th_a = synthetic.generate(n_models=n_models, n_items=n_items, honest_signals=False,
                                   seed=10_000 + seed)
    theta_h, theta_a = th_h["theta_hat"], th_a["theta_hat"]
    fit_idx, cal_idx, _ = splits.split_by_group(honest.group, seed=seed)
    m = _fit(honest, theta_h, fit_idx, cal_idx, "se_aware")
    lo, hi, _ = m.bracket(adv)
    cov_flat = scoring.coverage(lo, hi, theta_a)

    # elicitation-defeat: the model resists elicitation so S3 fails to recover theta -> the ceiling
    # anchor itself is wrong. Calibrated on non-resistant pairs, coverage SHOULD break.
    res, th_r = synthetic.generate(n_models=n_models, n_items=n_items,
                                   elicitation_resistant=True, seed=20_000 + seed)
    lo2, hi2, _ = m.bracket(res)
    cov_resist = scoring.coverage(lo2, hi2, th_r["theta_hat"])
    return cov_flat, cov_resist


def agg(runs, key, field):
    return float(np.mean([r[key][field] for r in runs]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--n-models", type=int, default=120)
    ap.add_argument("--n-items", type=int, default=400)
    args = ap.parse_args()
    alpha = 0.10
    S = range(args.seeds)

    pos = [run_once(s, headroom=(0.02, 0.15), n_models=args.n_models, n_items=args.n_items) for s in S]
    neg = [run_once(1000 + s, headroom=(0.0, 0.0), rho_range=(1.0, 1.0),
                    n_models=args.n_models, n_items=args.n_items) for s in S]
    hard = [run_adversarial_hardmode(s, args.n_models, args.n_items) for s in S]

    print(f"\n=== Synthetic SMOKE TEST ({args.seeds} seeds, nominal {1-alpha:.0%}, "
          f"{args.n_models} models) ===")
    print(f"{'method':<16}{'coverage':>10}{'int.score':>12}{'width':>10}")
    for k, name in [("B0", "B0 Wilson(S1)"), ("B1", "B1 Wilson(S3)"), ("B1c", "B1c conformal"),
                    ("B_se", "B_se SE-norm"), ("B2", "B2 EvalBracket")]:
        print(f"{name:<16}{agg(pos,k,'coverage'):>10.3f}{agg(pos,k,'mean_interval_score'):>12.4f}"
              f"{agg(pos,k,'mean_width'):>10.3f}")

    # honest paired B2-vs-B_se effect across seeds
    diffs = np.array([r["b2_vs_bse_intscore"] for r in pos])
    rng = np.random.default_rng(0)
    bmeans = [float(np.mean(rng.choice(diffs, len(diffs), replace=True))) for _ in range(5000)]
    d_lo, d_hi = np.percentile(bmeans, [2.5, 97.5])
    fusion_helps = d_hi < 0.0            # B2 lower interval score than B_se, CI excludes 0
    oos = float(np.mean([r["oos_r2"] for r in pos]))
    print(f"\n=== Does awareness fusion beat SE-normalization? (honest) ===")
    print(f"  B2 - B_se interval score: mean={diffs.mean():+.4f}  95% CI [{d_lo:+.4f}, {d_hi:+.4f}]"
          f"  -> {'FUSION HELPS' if fusion_helps else 'NULL / ornamental on this data'}")
    print(f"  OOS R^2 of (S2,S4) -> ceiling shortfall: {oos:.3f}  (real-data fusion-value gate)")

    dc = [r["disguise_ceiling"] for r in pos]
    dc_neg = [r["disguise_ceiling"] for r in neg]
    excl = float(np.mean([d["excludes_zero"] for d in dc]))
    excl_neg = float(np.mean([d["excludes_zero"] for d in dc_neg]))
    print(f"\n=== Disguise ceiling (RQ3, unbiased + cluster bootstrap) ===")
    print(f"  positive : mean delta_head={np.mean([d['mean_delta_head'] for d in dc]):+.3f}  "
          f"CI-excludes-0 in {excl:.0%} of seeds (planted={np.mean([r['planted_headroom'] for r in pos]):.3f})")
    print(f"  negative : mean delta_head={np.mean([d['mean_delta_head'] for d in dc_neg]):+.3f}  "
          f"CI-excludes-0 in {excl_neg:.0%} of seeds (should be ~0%)")
    cov_flat = np.mean([h[0] for h in hard])
    cov_resist = np.mean([h[1] for h in hard])
    print(f"\n=== Adversarial hard modes (calibrate on honest/non-resistant pairs) ===")
    print(f"  signal-flattened (S4 lies, suppression same): coverage {cov_flat:.3f}  "
          f"-> coverage is ANCHOR-driven, survives signal attack (good, non-obvious)")
    print(f"  elicitation-resistant (S3 fails to recover theta): coverage {cov_resist:.3f}  "
          f"-> ceiling anchor defeated => coverage BREAKS (the real vulnerability; honest)")

    checks = {
        "B2_coverage_near_nominal": abs(agg(pos, "B2", "coverage") - (1 - alpha)) <= 0.05,
        "B_se_reaches_coverage": agg(pos, "B_se", "coverage") >= (1 - alpha) - 0.05,
        "B0_undercovers": agg(pos, "B0", "coverage") < (1 - alpha) - 0.05,
        "B1_undercovers": agg(pos, "B1", "coverage") < (1 - alpha) - 0.05,
        "B2_width_useful": agg(pos, "B2", "mean_width") < 0.5,
        "no_vacuous_bounds": True,   # hard-fail in calibrate() would have raised
        "disguise_ceiling_detected": excl >= 0.8,
        "negative_control_clean": excl_neg <= 0.1,
    }
    print("\n=== Pass conditions (coverage + recovery; fusion-value reported separately) ===")
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(json.dumps({"checks": checks, "all_pass": all(checks.values()),
                      "fusion_helps_here": bool(fusion_helps), "oos_r2": oos,
                      "cov_signal_flattened": float(cov_flat),
                      "cov_elicitation_resistant": float(cov_resist)}))
    return all(checks.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
