#!/usr/bin/env python3
"""Plot access-specific v2.2 outcome counts and the primary API-only result."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

from experiments.unified_v22.analyze_campaign import (
    LABEL_ABOVE,
    LABEL_BELOW,
    LABEL_INCONCLUSIVE,
    LABEL_UNKNOWN,
)


COLORS = {
    LABEL_BELOW: "#2a9d8f",
    LABEL_UNKNOWN: "#e9c46a",
    LABEL_ABOVE: "#e76f51",
    LABEL_INCONCLUSIVE: "#7b6d8d",
}


def plot(input_path: Path, output_path: Path) -> None:
    payload = json.loads(input_path.read_text())
    profiles = payload["consolidated_profiles"]
    labels = [LABEL_BELOW, LABEL_UNKNOWN, LABEL_ABOVE, LABEL_INCONCLUSIVE]
    access = ["api_and_tools", "weight_access"]
    counts = {
        tier: Counter(row["label"] for row in profiles if row["access_tier"] == tier)
        for tier in access
    }
    fig, axis = plt.subplots(figsize=(11, 6.4))
    left = [0, 0]
    for label in labels:
        values = [counts[tier][label] for tier in access]
        axis.bar(
            ["API and tools", "Weight access"],
            values,
            bottom=left,
            label=label,
            color=COLORS[label],
        )
        left = [base + value for base, value in zip(left, values)]
    axis.set_ylabel("Consolidated model-task profiles")
    axis.set_title("Unified EvalBracket v2.2 outcomes by access tier")
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
    axis.text(
        0.0,
        -0.17,
        "Each profile consolidates independent seeds 17 and 29. Controlled multiple-choice proxies only.",
        transform=axis.transAxes,
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    plot(args.input, args.output)
