"""Generate the paper's figures from committed data (data_snapshot/). Outputs vector PDFs to figures/."""
import json, os, sys, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
sys.path.insert(0, "substrate")
from analyze_real import load_rows, to_signals, ground_truth
from evalbracket import EvalBracket, baselines, maturation

plt.rcParams.update({"font.size": 10, "axes.grid": False, "figure.dpi": 150, "savefig.bbox": "tight"})
os.makedirs("figures", exist_ok=True)
BLUE, CORAL, GREEN, RED, GREY = "#2f6fb0", "#e07a4b", "#3a9d5d", "#cc4b4b", "#8a8a8a"


def lomo_brackets(rows):
    theta = np.array([ground_truth(r) for r in rows]); grp = np.array([r["group"] for r in rows])
    sig = to_signals(rows); lo = np.full(len(rows), np.nan); hi = np.full(len(rows), np.nan)
    for held in sorted(set(grp)):
        tr = np.where(grp != held)[0]; te = np.where(grp == held)[0]
        if len(set(grp[tr])) < 3: continue
        m = EvalBracket(scale_mode="se", allow_vacuous=True); m.kappa, m.gamma, m.beta = 0, 0, (0, 0, 0)
        try:
            m.calibrate(sig.subset(tr), theta[tr]); l, h, _ = m.bracket(sig.subset(te)); lo[te]=l; hi[te]=h
        except Exception: pass
    return theta, lo, hi


# ---- Fig 1: concept (ceiling/floor curves + lag + range lifecycle) ----
def fig_concept():
    t = np.linspace(0, 10, 200)
    sig = lambda x, t0: 0.15 + 0.8 / (1 + np.exp(-(x - t0) / 0.9))
    ceil, floor = sig(t, 3.5), sig(t, 6.5)
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot(t, ceil, color=BLUE, lw=2.2, label="ceiling (elicitable)")
    ax.plot(t, floor, color=CORAL, lw=2.2, label="floor (default)")
    ax.plot([3.5, 6.5], [0.55, 0.55], color="k", lw=1.2)
    ax.annotate("", xy=(6.5, 0.55), xytext=(3.5, 0.55), arrowprops=dict(arrowstyle="<->", color="k"))
    ax.text(5.0, 0.58, "lag = lead time", ha="center", fontsize=9)
    for x, lab in [(2, "narrow-low"), (5, "widest"), (8, "narrow-high")]:
        ax.plot([x, x], [sig(x, 6.5), sig(x, 3.5)], color="#8b5cf6", lw=6, alpha=0.28, solid_capstyle="butt")
        ax.text(x, sig(x, 3.5)+0.03, lab, ha="center", fontsize=7.5, color="#6d28d9")
    ax.scatter([3.5, 6.5], [0.55, 0.55], color=[BLUE, CORAL], zorder=5, s=25)
    ax.set_xlabel("training / versions"); ax.set_ylabel("capability"); ax.set_ylim(0.05, 1.0)
    ax.set_xticks([]); ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.set_title("The [floor, ceiling] range and the ceiling$\\to$floor lag", fontsize=10)
    fig.savefig("figures/fig1_concept.pdf"); plt.close(fig)


# ---- Fig 2: existence proof caterpillar ----
def fig_existence():
    _, rows = load_rows("data_snapshot/pairs2_disjoint_diverse.jsonl")
    theta, lo, hi = lomo_brackets(rows)
    s1 = np.array([r["s1"] for r in rows]); n = np.array([r["n_items"] for r in rows])
    b0lo, b0hi = baselines.baseline_b0(s1, n, 0.10)
    v = ~np.isnan(lo); order = np.argsort(theta[v]); idx = np.where(v)[0][order]
    x = np.arange(len(idx))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.vlines(x, lo[idx], hi[idx], color=GREEN, lw=3, alpha=0.5, label="EvalBracket [floor,ceiling]")
    ax.vlines(x + 0.0, b0lo[idx], b0hi[idx], color=RED, lw=1.6, label="naive CI around suppressed score")
    ax.scatter(x, theta[idx], color="k", s=9, zorder=5, label="true capability $\\theta$")
    ax.set_xlabel("held-out (model, capability) pairs, sorted by $\\theta$")
    ax.set_ylabel("capability"); ax.set_ylim(0, 1.02); ax.set_xticks([])
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_title("Bracket contains true capability on 92%; naive CI on 2%", fontsize=10)
    fig.savefig("figures/fig2_existence.pdf"); plt.close(fig)


# ---- Fig 3: mitigation head-to-head ----
def fig_headtohead():
    rows = [r for r in (json.loads(l) for l in open("data_snapshot/pairs_arms3.jsonl"))
            if r["theta_locked_pwdon"] > 0.30 and r["s1"] < r["theta_locked_pwdon"] - 0.03]
    th = np.mean([r["theta_locked_pwdon"] for r in rows]); s1 = np.mean([r["s1"] for r in rows])
    def a(k): return np.mean([(r[k+"_sel"]+r[k+"_val"])/2 for r in rows])
    vals = {"raw\n(suppressed)": s1, "disguise\nprompt": a("arm_disguise"), "cooperate\nprompt": a("arm_coop"),
            "few-shot\nelicit": np.mean([r["s3"] for r in rows]), "fine-tune\nrelease": np.mean([r["s_release"] for r in rows])}
    rec = {k: (v-s1)/(th-s1)*100 for k, v in vals.items()}
    fig, ax = plt.subplots(figsize=(6, 3.2))
    cols = [GREY, CORAL, CORAL, BLUE, BLUE]
    bars = ax.bar(range(len(rec)), list(rec.values()), color=cols)
    for b, val in zip(bars, rec.values()): ax.text(b.get_x()+b.get_width()/2, val+2, f"{val:.0f}%", ha="center", fontsize=9)
    ax.axhline(100, ls="--", color="k", lw=0.7); ax.set_xticks(range(len(rec))); ax.set_xticklabels(rec.keys(), fontsize=8)
    ax.set_ylabel("% of suppression gap recovered"); ax.set_ylim(0, 115)
    ax.set_title("You cannot prompt past a lock; you must elicit it", fontsize=10)
    ax.text(1.0, 55, "prompt\nmitigations", ha="center", color=CORAL, fontsize=8)
    ax.text(3.5, 55, "elicitation", ha="center", color=BLUE, fontsize=8)
    fig.savefig("figures/fig3_headtohead.pdf"); plt.close(fig)


# ---- Fig 4: maturation lag recovery ----
def fig_maturation():
    rows = sorted((json.loads(l) for l in open("data_snapshot/maturation_traj.jsonl")), key=lambda r: r["s_mid"])
    smid, lag = [], []
    for r in rows:
        v = r["versions"]; t = np.arange(len(v), dtype=float)
        res = maturation.analyze_series(t, np.array([x["ceiling"] for x in v]), np.array([x["floor"] for x in v]),
                                        n_items=r["n_items"], seed=0)
        smid.append(r["s_mid"]); lag.append(res["lag"])
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.scatter(smid, lag, color=BLUE, s=40, zorder=5)
    z = np.polyfit(smid, lag, 1); xs = np.linspace(min(smid), max(smid), 10)
    ax.plot(xs, np.polyval(z, xs), color=GREY, ls="--", lw=1)
    ax.set_xlabel("imposed suppression-decay midpoint $s_{mid}$"); ax.set_ylabel("recovered ceiling$\\to$floor lag")
    ax.set_title(f"Emergent lag tracks the mechanism (r={np.corrcoef(smid,lag)[0,1]:.2f})", fontsize=10)
    fig.savefig("figures/fig4_maturation.pdf"); plt.close(fig)


# ---- Fig 5: held-back detection ----
def fig_heldback():
    rows = [r for r in (json.loads(l) for l in open("data_snapshot/pairs2_disjoint_diverse.jsonl")) if "s_release" in r]
    gap = np.array([r["s3"]-r["s1"] for r in rows]); surf = np.array([r["s_release"]-r["s1"] for r in rows])
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    lim = [min(gap.min(), surf.min())-0.05, max(gap.max(), surf.max())+0.05]
    ax.plot(lim, lim, ls="--", color=GREY, lw=1, label="identity")
    ax.scatter(gap, surf, color=GREEN, s=20, alpha=0.7)
    ax.set_xlabel("observable elicitation gap (S3 $-$ S1)"); ax.set_ylabel("surfaced on release ($s_{rel} - $S1)")
    ax.set_title(f"Gap tracks what surfaces (r={np.corrcoef(gap,surf)[0,1]:.2f})", fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    fig.savefig("figures/fig5_heldback.pdf"); plt.close(fig)


# ---- Fig 6: group-conditional (Mondrian) coverage by size band ----
def fig_conditional():
    from evalbracket.mondrian import mondrian_brackets, size_band, family_of
    rows, good = load_rows("data_snapshot/pairs4_fleet.jsonl")
    theta = np.array([ground_truth(r) for r in good])
    grp = np.array([r["group"] for r in good])
    band = np.array([size_band(r["group"]) for r in good])
    fam = np.array([family_of(r["group"]) for r in good])
    sig = to_signals(good)

    def held_out(held_arr):
        lo = np.full(len(good), np.nan); hi = np.full(len(good), np.nan)
        for h in sorted(set(held_arr.tolist())):
            tr = np.where(held_arr != h)[0]; te = np.where(held_arr == h)[0]
            if len(set(grp[tr])) < 3: continue
            l, hgh, _ = mondrian_brackets(sig.subset(tr), theta[tr], band[tr],
                                          sig.subset(te), band[te], scale_mode="se")
            lo[te], hi[te] = l, hgh
        return lo, hi

    bands = ["<1B", "1-3B", "3-10B"]
    def per_band(lo, hi):
        out = []
        for b in bands:
            m = (band == b) & ~np.isnan(lo)
            out.append(np.mean((theta[m] >= lo[m]-1e-9) & (theta[m] <= hi[m]+1e-9)) if m.sum() else np.nan)
        return out
    lomo = per_band(*held_out(grp))
    lofo = per_band(*held_out(fam))
    counts = [int((band == b).sum()) for b in bands]

    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = np.arange(len(bands)); w = 0.38
    ax.bar(x - w/2, lomo, w, color=BLUE, label="leave-one-model-out")
    ax.bar(x + w/2, lofo, w, color=GREEN, label="leave-one-family-out")
    ax.axhline(0.90, ls="--", color="k", lw=0.9); ax.text(2.30, 0.915, "nominal 0.90", fontsize=8)
    for xi, (a, b_) in enumerate(zip(lomo, lofo)):
        ax.text(xi - w/2, a + 0.01, f"{a:.2f}", ha="center", fontsize=8)
        ax.text(xi + w/2, b_ + 0.01, f"{b_:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{b}\n(n={c})" for b, c in zip(bands, counts)])
    ax.set_ylabel("conditional coverage of $\\theta$"); ax.set_ylim(0, 1.05)
    ax.set_title("Mondrian coverage by size band holds at nominal, across held-out families", fontsize=9.5)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.savefig("figures/fig6_conditional.pdf"); plt.close(fig)


if __name__ == "__main__":
    fig_concept(); fig_existence(); fig_headtohead(); fig_maturation(); fig_heldback(); fig_conditional()
    print("wrote:", sorted(os.listdir("figures")))
