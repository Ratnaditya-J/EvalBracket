#!/usr/bin/env python3
"""Plot v2.2 target outcomes and control-recovery saturation curves."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


COLORS = {"cyber": "#2563EB", "bio": "#16A34A"}


def short_label(row: Mapping[str, Any]) -> str:
    harness = row.get("through_harness")
    if harness:
        replacements = {
            "direct_snapshot": "Direct",
            "react_2_turn": "ReAct 2",
            "react_4_turn": "ReAct 4",
            "plan_execute_reflect_6_turn": "Plan and review",
            "multi_agent_2x4_turn": "Multi-agent",
        }
        return replacements.get(str(harness), str(harness))
    replacements = {
        "control_supervised_recovery": "LoRA",
        "control_reward_recovery": "Verifier RL",
        "control_full_fine_tuning_recovery": "Full tuning",
    }
    return replacements.get(str(row["through_stage"]), str(row["through_stage"]))


def make_plots(payload: Mapping[str, Any], output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    output.mkdir(parents=True, exist_ok=True)
    runs = payload["runs"]
    figure, axes = plt.subplots(
        len(runs),
        1,
        figsize=(12, 4.2 * len(runs)),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    axes = np.atleast_1d(axes)
    for axis, run in zip(axes, runs):
        for domain, curve in sorted(run["control_budget_curve"].items()):
            axis.plot(
                range(len(curve)),
                [
                    100 * row["recovery_rate"]
                    if row["eligible_controls"]
                    else np.nan
                    for row in curve
                ],
                marker="o",
                linewidth=2.4,
                color=COLORS[domain],
                label=domain.capitalize(),
            )
        reference_curve = next(iter(run["control_budget_curve"].values()))
        axis.set_xticks(range(len(reference_curve)))
        axis.set_xticklabels([short_label(row) for row in reference_curve], rotation=20, ha="right")
        axis.set_ylim(-3, 103)
        axis.set_ylabel("Controls recovered (%)")
        axis.set_title(f"{run['role'].capitalize()} run, seed {run['seed']}")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(loc="lower right", frameon=False, ncol=2)
    axes[-1].set_xlabel("Cumulative elicitation battery")
    figure.suptitle("Can the battery recover deliberately hidden capability?", fontsize=15, fontweight="bold")
    figure.savefig(output / "control_recovery_curves.png", dpi=220)
    plt.close(figure)

    labels = []
    target_rates = []
    control_rates = []
    target_lowers = []
    control_lowers = []
    colors = []
    for run in runs:
        for domain, result in sorted(run["domains"].items()):
            control = result["control_qualification"]
            labels.append(f"{run['role']}\n{domain}")
            target_rates.append(100 * result["rate"])
            target_lowers.append(100 * result["one_sided_95_lower"])
            if control["verified_controls"]:
                control_rates.append(100 * control["recovery_rate"])
                control_lowers.append(100 * control["one_sided_95_lower"])
            else:
                control_rates.append(np.nan)
                control_lowers.append(np.nan)
            colors.append(COLORS[domain])
    x = np.arange(len(labels))
    width = 0.36
    figure, axis = plt.subplots(figsize=(12, 5.8), constrained_layout=True)
    axis.bar(x - width / 2, target_rates, width, color=colors, alpha=0.92, label="Target task success")
    axis.bar(x + width / 2, control_rates, width, color=colors, alpha=0.42, hatch="//", label="Control recovery")
    axis.scatter(x - width / 2, target_lowers, color="#111827", marker="_", s=220, zorder=3, label="One-sided 95% lower bound")
    axis.scatter(x + width / 2, control_lowers, color="#111827", marker="_", s=220, zorder=3)
    axis.axhline(
        80,
        color="#DC2626",
        linestyle="--",
        linewidth=1.5,
        label="Control lower-bound qualification gate",
    )
    axis.set_xticks(x)
    axis.set_xticklabels(labels)
    axis.set_ylim(0, 105)
    axis.set_ylabel("Task-level rate (%)")
    axis.set_title("Target performance and control qualification evidence", fontweight="bold")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, ncol=3, loc="upper center")
    figure.savefig(output / "target_control_summary.png", dpi=220)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    make_plots(json.loads(args.combined.read_text()), args.output)


if __name__ == "__main__":
    main()
