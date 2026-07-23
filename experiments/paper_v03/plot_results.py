#!/usr/bin/env python3
"""Generate paper figures from the frozen EvalBracket v0.3 analysis CSVs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


BATTERY_ORDER = ["api_low", "api_high", "weight_low", "weight_medium", "weight_high"]
BATTERY_LABELS = {
    "api_low": "API low",
    "api_high": "API high",
    "weight_low": "Weight 32",
    "weight_medium": "Weight 128",
    "weight_high": "Weight 256",
}
FAMILY_COLORS = {
    "qwen2.5": "#2563EB",
    "phi3.5": "#D97706",
    "mistral": "#059669",
    "smollm2": "#7C3AED",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_primary_metrics(path: Path) -> list[dict[str, str]]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    primary = summary["thresholds"][str(summary["primary_threshold"])]
    rows = []
    for battery, procedures in primary["metrics"].items():
        for procedure, metrics in procedures.items():
            rows.append(
                {
                    "battery": battery,
                    "procedure": procedure,
                    "false_below_rate": str(metrics["false_below"]["rate"]),
                    "correct_below_rate": str(metrics["correct_below"]["rate"]),
                }
            )
    return rows


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 160,
            "savefig.dpi": 300,
        }
    )


def plot_qualification(rows: list[dict[str, str]], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    offsets = {"mistral": -0.18, "phi3.5": -0.06, "qwen2.5": 0.06, "smollm2": 0.18}

    for family, color in FAMILY_COLORS.items():
        family_rows = {
            row["battery"]: row
            for row in rows
            if row["target_family"] == family
        }
        for index, battery in enumerate(BATTERY_ORDER):
            row = family_rows.get(battery)
            if row is None:
                continue
            x = index + offsets[family]
            rate = float(row["recovery_rate"])
            lower = float(row["recovery_lower_bound"])
            ax.vlines(x, lower, rate, color=color, linewidth=1.5, alpha=0.75)
            ax.scatter(x, rate, s=38, color=color, zorder=3)
            ax.scatter(x, lower, s=30, color=color, marker="v", zorder=3)

    ax.axhline(0.80, color="#B91C1C", linestyle="--", linewidth=1.5)
    ax.text(4.42, 0.815, "80% recovery lower-bound gate", color="#991B1B", ha="right")
    ax.set_xticks(range(len(BATTERY_ORDER)), [BATTERY_LABELS[x] for x in BATTERY_ORDER])
    ax.set_ylim(0, 1.04)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylabel("Held-out controls recovered")
    ax.set_title("Only weight access passed the core recovery and breadth gate")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)

    family_handles = [
        plt.Line2D([], [], color=color, marker="o", linestyle="", label=family)
        for family, color in FAMILY_COLORS.items()
    ]
    meaning_handles = [
        plt.Line2D([], [], color="#374151", marker="o", linestyle="", label="Observed recovery"),
        plt.Line2D([], [], color="#374151", marker="v", linestyle="", label="One-sided 95% lower bound"),
    ]
    first = ax.legend(handles=family_handles, title="Held-out family", ncol=4, loc="lower right")
    ax.add_artist(first)
    ax.legend(handles=meaning_handles, loc="center right", bbox_to_anchor=(1.0, 0.34))
    fig.tight_layout()
    fig.savefig(output.with_suffix(".png"), bbox_inches="tight")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_decision_tradeoff(rows: list[dict[str, str]], output: Path) -> None:
    selected = []
    for row in rows:
        if row["procedure"] == "EvalBracket":
            selected.append(row)
        elif row["battery"] in {"api_low", "api_high"} and row["procedure"] == "unqualified elicitation":
            selected.append(row)
        elif row["battery"] == "weight_low" and row["procedure"] == "default evaluation":
            selected.append(row)

    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    labels = {
        ("api_low", "unqualified elicitation"): "API low, unqualified",
        ("api_high", "unqualified elicitation"): "API high, unqualified",
        ("api_low", "EvalBracket"): "API low, EvalBracket v0.3",
        ("api_high", "EvalBracket"): "API high, EvalBracket v0.3",
        ("weight_low", "default evaluation"): "Default evaluation",
        ("weight_low", "EvalBracket"): "Weight 32, EvalBracket v0.3",
        ("weight_medium", "EvalBracket"): "Weight 128/256, EvalBracket v0.3",
    }
    colors = {
        "default evaluation": "#6B7280",
        "unqualified elicitation": "#D97706",
        "EvalBracket": "#2563EB",
    }

    used = set()
    for row in selected:
        key = (row["battery"], row["procedure"])
        if key in used or key not in labels:
            continue
        used.add(key)
        false_below = float(row["false_below_rate"])
        correct_below = float(row["correct_below_rate"])
        color = colors[row["procedure"]]
        marker = "D" if row["procedure"] == "EvalBracket" else "o"
        ax.scatter(false_below, correct_below, s=75, color=color, marker=marker, zorder=3)
        dx, dy, align = 8, 8, "left"
        if key in {("api_low", "EvalBracket"), ("api_high", "EvalBracket")}:
            continue
        if key == ("weight_medium", "EvalBracket"):
            dy = -27
        elif key == ("api_low", "unqualified elicitation"):
            dx, dy, align = -8, -27, "right"
        elif key == ("weight_low", "default evaluation"):
            dx, dy, align = -8, 10, "right"
        ax.annotate(
            labels[key],
            (false_below, correct_below),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=9,
            ha=align,
        )

    ax.annotate(
        "API low and API high, v0.3 rule\n(both return Upper bound unknown on negatives)",
        (0, 0),
        xytext=(0.12, 0.20),
        arrowprops={"arrowstyle": "->", "color": "#374151"},
        fontsize=9,
    )
    ax.set_xlim(-0.03, 1.06)
    ax.set_ylim(-0.03, 1.10)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_xlabel("False below on hidden positives, lower is better")
    ax.set_ylabel("Correct below on genuine negatives, higher is better")
    ax.set_title("The core decision rule exposes API uncertainty")
    ax.grid(color="#E5E7EB", linewidth=0.8)
    ax.axvspan(-0.03, 0.10, color="#DCFCE7", alpha=0.45, zorder=0)
    ax.axhspan(0.90, 1.10, color="#DCFCE7", alpha=0.45, zorder=0)
    fig.tight_layout()
    fig.savefig(output.with_suffix(".png"), bbox_inches="tight")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    configure_style()
    qualifications = read_csv(args.analysis_dir / "qualifications.csv")
    metrics = read_primary_metrics(args.analysis_dir / "analysis_summary.json")
    plot_qualification(qualifications, args.output_dir / "qualification_by_access")
    plot_decision_tradeoff(metrics, args.output_dir / "decision_tradeoff")
    print(args.output_dir)


if __name__ == "__main__":
    main()
