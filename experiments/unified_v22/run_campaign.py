#!/usr/bin/env python3
"""Run one model and seed from the frozen unified v2.2 matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.paper_v03.run_campaign import run_job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--conditions", type=lambda value: [x for x in value.split(",") if x])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--data-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run_job(parse_args())
