"""Unit + property tests for the EvalBracket machinery (post-critique)."""
import math
import warnings

import numpy as np
import pytest

from evalbracket import (EvalBracket, Signals, baselines, conformal_quantile,
                         decomposition, scoring, splits, synthetic, unbiased_s_mit)


# ----------------------------------------------------------------- conformal quantile
def test_conformal_quantile_finite_sample_rank():
    r = list(range(10))
    assert conformal_quantile(r, 0.1) == 9.0     # k=ceil(11*0.9)=10 -> 10th smallest
    assert conformal_quantile(r, 0.2) == 8.0     # k=ceil(11*0.8)=9  -> 9th smallest


def test_conformal_quantile_infinite_when_too_few():
    assert conformal_quantile([1, 2, 3, 4, 5], 0.1) == math.inf   # k=6 > n=5


def test_conformal_quantile_rejects_bad_alpha():
    for bad in (0.0, 1.0, 1.5, -0.1):
        with pytest.raises(ValueError):
            conformal_quantile(range(10), bad)


def test_conformal_marginal_coverage_synthetic():
    """Load-bearing: exchangeable data -> nominal coverage (both sides supported at 0.05/0.05)."""
    covs = []
    for seed in range(30):
        sig, truth = synthetic.generate(n_models=80, n_items=400, seed=seed)
        theta = truth["theta_hat"]
        fi, ci, ti = splits.split_by_group(sig.group, seed=seed)
        m = EvalBracket(alpha_u=0.05, alpha_l=0.05).fit(sig.subset(fi), theta[fi])
        m.calibrate(sig.subset(ci), theta[ci])
        lo, hi, _ = m.bracket(sig.subset(ti))
        covs.append(scoring.coverage(lo, hi, theta[ti]))
    assert 0.86 <= float(np.mean(covs)) <= 1.0


def test_se_scaling_covers_under_within_set_heteroscedastic_n():
    """The legitimate SE-scaling case: item count VARIES across pairs within one exchangeable set
    (some evals cheap, some expensive). Coverage should stay near nominal because the set is still
    exchangeable and SE puts wider margins on the noisier (small-n) pairs."""
    covs = []
    for seed in range(25):
        sig, tr = synthetic.generate(n_models=90, n_items=400, seed=seed)
        # inject heteroscedastic item counts: half the pairs are cheap (n=120)
        rng = np.random.default_rng(seed)
        cheap = rng.random(len(sig)) < 0.5
        sig.n_items[cheap] = 120
        # re-noise the accuracies of cheap pairs at their true (smaller) n so noise matches n_items
        for name in ("s1", "s3"):
            arr = getattr(sig, name)
            arr[cheap] = np.clip(rng.binomial(120, np.clip(arr[cheap], 0, 1)) / 120, 0, 1)
        theta = tr["theta_hat"].copy()
        theta[cheap] = np.clip(rng.binomial(120, np.clip(tr["theta_prob"][cheap], 0, 1)) / 120, 0, 1)
        fi, ci, ti = splits.split_by_group(sig.group, seed=seed)
        m = EvalBracket(scale_mode="se_aware").fit(sig.subset(fi), theta[fi])
        m.calibrate(sig.subset(ci), theta[ci])
        lo, hi, _ = m.bracket(sig.subset(ti))
        covs.append(scoring.coverage(lo, hi, theta[ti]))
    assert float(np.mean(covs)) >= 0.85


def test_item_count_drift_warns():
    """Large calibrate/deploy n mismatch must warn (spec §3.4 contract: fix n)."""
    sig, tr = synthetic.generate(n_models=80, n_items=400, seed=0)
    fi, ci, ti = splits.split_by_group(sig.group, seed=0)
    m = EvalBracket(scale_mode="se_aware").fit(sig.subset(fi), tr["theta_hat"][fi])
    m.calibrate(sig.subset(ci), tr["theta_hat"][ci])
    drifted = sig.subset(ti)
    drifted.n_items[:] = 50            # 8x smaller than calibration
    with pytest.warns(UserWarning, match="item-count"):
        m.bracket(drifted)


# ----------------------------------------------------------------- validation / guards
def test_alpha_validation_in_init():
    for au, al in [(0.0, 0.05), (0.05, 1.0), (-0.1, 0.05)]:
        with pytest.raises(ValueError):
            EvalBracket(alpha_u=au, alpha_l=al)


def test_vacuous_bound_hard_fails():
    sig, truth = synthetic.generate(n_models=20, n_items=400, seed=0)
    fi, ci, ti = splits.split_by_group(sig.group, seed=0)
    m = EvalBracket(alpha_u=0.02, alpha_l=0.02).fit(sig.subset(fi), truth["theta_hat"][fi])
    with pytest.raises(ValueError):
        m.calibrate(sig.subset(ci), truth["theta_hat"][ci])   # tiny |C| can't support 0.02


def test_bracket_requires_calibrate():
    sig, truth = synthetic.generate(n_models=40, seed=0)
    fi, ci, ti = splits.split_by_group(sig.group, seed=0)
    m = EvalBracket().fit(sig.subset(fi), truth["theta_hat"][fi])
    with pytest.raises(RuntimeError):
        m.bracket(sig.subset(ti))     # calibrate() not called


def test_signals_reject_nonfinite():
    with pytest.raises(ValueError):
        Signals(s1=[0.5, np.nan], s2=[0.1, 0.1], s3=[0.6, 0.6], s4=[0.0, 0.0],
                s5=[0.1, 0.1], n_items=[100, 100], group=["a", "b"])


# ----------------------------------------------------------------- Wilson baseline
def test_wilson_center_and_bounds():
    lo, hi = baselines.wilson_interval(50, 100, 0.10)
    assert 0.0 <= lo < 0.5 < hi <= 1.0
    assert abs((lo + hi) / 2 - 0.5) < 1e-9


def test_wilson_n_zero_returns_full_interval():
    lo, hi = baselines.wilson_from_accuracy([0.5], [0], 0.1)
    assert lo[0] == 0.0 and hi[0] == 1.0     # not (nan, nan)


# ----------------------------------------------------------------- interval score
def test_interval_score_rewards_narrow_and_penalizes_miss():
    assert scoring.interval_score(0.4, 0.6, 0.5, 0.1) < scoring.interval_score(0.2, 0.8, 0.5, 0.1)
    missed = scoring.interval_score(0.4, 0.6, 0.9, 0.1)
    assert missed == pytest.approx(0.2 + (2 / 0.1) * 0.3)


# ----------------------------------------------------------------- decomposition
def test_unbiased_s_mit_reduces_max_bias():
    """Sample-split s_mit should be much less biased than max(hat_B, hat_C) when true B==C."""
    rng = np.random.default_rng(0)
    n, trials, p = 200, 4000, 0.6
    max_bias, split_bias = [], []
    for _ in range(trials):
        bs, cs = rng.binomial(n, p) / n, rng.binomial(n, p) / n
        bv, cv = rng.binomial(n, p) / n, rng.binomial(n, p) / n
        max_bias.append(max(bs, cs) - p)
        s_mit, _ = unbiased_s_mit(np.array([bs]), np.array([cs]), np.array([bv]), np.array([cv]))
        split_bias.append(s_mit[0] - p)
    assert abs(np.mean(split_bias)) < abs(np.mean(max_bias))
    assert abs(np.mean(split_bias)) < 0.005       # split estimator ~ unbiased


def test_cluster_bootstrap_wider_than_iid_under_clustering():
    """With strong within-model correlation, cluster bootstrap CI should be wider (honest)."""
    rng = np.random.default_rng(1)
    groups, vals = [], []
    for g in range(20):
        eff = rng.normal(0, 0.1)              # between-model effect
        for _ in range(5):
            groups.append(f"m{g}"); vals.append(eff + rng.normal(0, 0.01))
    vals = np.array(vals); groups = np.array(groups)
    iid = decomposition._cluster_bootstrap_mean(vals, None, 2000, 0)
    clu = decomposition._cluster_bootstrap_mean(vals, groups, 2000, 0)
    assert np.std(clu) > np.std(iid)


def test_disguise_ceiling_detects_and_negative_control_clean():
    sig, truth = synthetic.generate(n_models=120, n_items=500,
                                    elic_headroom_range=(0.05, 0.15), seed=3)
    s_mit, _ = unbiased_s_mit(truth["arm_b_select"], truth["arm_c_select"],
                              truth["arm_b_value"], truth["arm_c_value"])
    d = decomposition.disguise_ceiling_summary(truth["theta_hat"], sig.s1, s_mit, group=sig.group)
    assert d["mean_delta_head"] > 0.02 and d["excludes_zero"]

    sig0, tr0 = synthetic.generate(n_models=120, n_items=500,
                                   elic_headroom_range=(0.0, 0.0), rho_range=(1.0, 1.0), seed=4)
    s_mit0, _ = unbiased_s_mit(tr0["arm_b_select"], tr0["arm_c_select"],
                               tr0["arm_b_value"], tr0["arm_c_value"])
    d0 = decomposition.disguise_ceiling_summary(tr0["theta_hat"], sig0.s1, s_mit0, group=sig0.group)
    assert not d0["excludes_zero"]


# ----------------------------------------------------------------- abstain on weak elicitation
def _calibrated_model(abstain, seed=0):
    m = EvalBracket(scale_mode="se", abstain_on_weak_elicitation=abstain)
    m.kappa, m.gamma, m.beta = 0.0, 0.0, (0.0, 0.0, 0.0)
    csig, ctruth = synthetic.generate(n_models=60, seed=seed)
    m.calibrate(csig, ctruth["theta_hat"])
    return m


def test_abstain_blows_ceiling_to_one_when_elicitation_fails():
    """When S3 ~= S1 (elicitation defeated), the ceiling is untrustworthy. Abstain should widen it
    to 1 (loud 'can't upper-bound'), while leaving trustworthy pairs unchanged."""
    # pair 0 trustworthy (S3 >> S1); pair 1 untrustworthy (S3 == S1)
    sig = Signals(s1=[0.30, 0.30], s2=[0.1, 0.1], s3=[0.80, 0.30], s4=[0.0, 0.0],
                  s5=[0.0, 0.0], n_items=[300, 300], group=["a", "b"])
    m_on, m_off = _calibrated_model(True), _calibrated_model(False)
    trust, _, _ = m_on.elicitation_trust(sig)
    assert trust[0] and not trust[1]
    _, hi_on, _ = m_on.bracket(sig)
    _, hi_off, _ = m_off.bracket(sig)
    assert hi_on[1] == 1.0                     # abstained ceiling -> 1 (loud)
    assert hi_off[1] < 1.0                     # without abstain: confident (narrow) wrong ceiling
    assert hi_on[0] == hi_off[0]               # trustworthy pair is untouched by abstain


# ----------------------------------------------------------------- splits
def test_splits_group_disjoint():
    sig, _ = synthetic.generate(n_models=30, seed=0)
    fi, ci, ti = splits.split_by_group(sig.group, seed=0)
    g = [set(sig.group[x]) for x in (fi, ci, ti)]
    assert g[0].isdisjoint(g[1]) and g[0].isdisjoint(g[2]) and g[1].isdisjoint(g[2])


# ----------------------------------------------------------------- anchors monotone
def test_anchors_monotone():
    sig = Signals(s1=[0.4], s2=[0.3], s3=[0.6], s4=[0.1], s5=[0.2], n_items=[400], group=["m0"])
    m = EvalBracket(); m.kappa = 0.5
    assert m.upper_anchor(sig)[0] == pytest.approx(0.6)
    assert m.lower_anchor(sig)[0] == pytest.approx(0.4 * (1 - 0.5 * 0.2))


# ----------------------------------------------------------------- maturation instrument (RQ4)
def test_maturation_recovers_planted_lag():
    from evalbracket import maturation, maturation_synth
    errs = []
    for L in (1.0, 2.0, 3.0):
        for s in range(6):
            d = maturation_synth.generate_series(T=12, lag=L, n_items=500, seed=s + int(L * 50))
            r = maturation.analyze_series(d["t"], d["ceiling"], d["floor"], planted_lag=L)
            errs.append(abs(r["lag_shift"] - L))
    assert np.mean(errs) < 0.5          # instrument recovers the planted lag


def test_maturation_zero_lag_is_zero():
    from evalbracket import maturation, maturation_synth
    d = maturation_synth.generate_series(T=12, lag=0.0, n_items=800, seed=1)
    r = maturation.analyze_series(d["t"], d["ceiling"], d["floor"], planted_lag=0.0)
    assert abs(r["lag_shift"]) < 0.6 and abs(r["lag_sigmoid"]) < 0.6


def test_maturation_width_widens_then_narrows():
    from evalbracket import maturation, maturation_synth
    d = maturation_synth.generate_series(T=14, lag=3.0, n_items=1000, seed=2)
    life = maturation.width_lifecycle(d["ceiling_true"], d["floor_true"])
    assert life["widen_then_narrow"]
    assert life["max_width"] > life["start_width"] and life["max_width"] > life["final_width"]


def test_maturation_gate_refuses_untrustworthy_regime():
    """The identifiability gate must flag near-linear / inflection-out-of-window as NOT identified,
    instead of returning a silently-wrong lag (the stats-review CRITICAL)."""
    from evalbracket import maturation, maturation_synth
    # good regime -> identified
    dg = maturation_synth.generate_series(T=12, t0=4.5, tau=1.1, lag=2.0, n_items=500, seed=0)
    rg = maturation.analyze_series(dg["t"], dg["ceiling"], dg["floor"], n_items=dg["n_items"], seed=0)
    assert rg["identified"] and "lag_ci_low" in rg
    # near-linear -> refused
    db = maturation_synth.generate_series(T=12, t0=6.0, tau=6.0, lag=2.0, n_items=500, seed=0)
    rb = maturation.analyze_series(db["t"], db["ceiling"], db["floor"], n_items=db["n_items"], seed=0)
    assert not rb["identified"]
    # inflection past window -> refused
    do = maturation_synth.generate_series(T=12, t0=14.0, tau=1.1, lag=2.0, n_items=500, seed=0)
    ro = maturation.analyze_series(do["t"], do["ceiling"], do["floor"], n_items=do["n_items"], seed=0)
    assert not ro["identified"]


def test_maturation_width_three_states():
    from evalbracket import maturation, maturation_synth
    # complete maturation (both inflections in window) -> 'complete'
    dc = maturation_synth.generate_series(T=16, t0=5.0, tau=1.0, lag=3.0, n_items=1000, seed=1)
    assert maturation.width_lifecycle(dc["ceiling_true"], dc["floor_true"])["state"] == "complete"
    # incomplete (floor inflection beyond window) -> 'widening', not 'none'
    di = maturation_synth.generate_series(T=10, t0=8.0, tau=1.0, lag=3.0, n_items=1000, seed=1)
    assert maturation.width_lifecycle(di["ceiling_true"], di["floor_true"])["state"] in ("widening", "complete")
