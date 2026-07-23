#!/usr/bin/env python3
"""Verify completeness, provenance, and internal consistency of unified v2.2 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for row in handle if row.strip())


def verify(args: argparse.Namespace) -> dict[str, Any]:
    config = json.loads(args.config.read_text())
    extension = json.loads(args.extension_config.read_text()) if args.extension_config else None
    config_hash = sha256(args.config)
    expected_jobs = {
        f"{model['id'].replace('/', '__').replace(':', '_')}__seed-{seed}": model
        for model in config["models"]
        for seed in config["seeds"]
    }
    actual_jobs = {path.parent.name: path.parent for path in (args.results_root / "jobs").glob("*/DONE")}
    if set(actual_jobs) != set(expected_jobs):
        missing = sorted(set(expected_jobs) - set(actual_jobs))
        extra = sorted(set(actual_jobs) - set(expected_jobs))
        raise AssertionError(f"job mismatch; missing={missing}, extra={extra}")

    job_rows: list[dict[str, Any]] = []
    for job_id, job_dir in sorted(actual_jobs.items()):
        manifest_path = job_dir / "manifest.json"
        score_path = job_dir / "scores.jsonl"
        item_path = job_dir / "items.jsonl"
        manifest = json.loads(manifest_path.read_text())
        assert str(manifest["protocol_version"]) == "2.2", job_id
        assert manifest["config_sha256"] == config_hash, job_id
        assert manifest["output_sha256"]["scores.jsonl"] == sha256(score_path), job_id
        assert manifest["output_sha256"]["items.jsonl"] == sha256(item_path), job_id
        assert manifest["gpu"]["available"] is True, job_id
        assert "H100" in manifest["gpu"]["name"], job_id
        expected_tasks = list(expected_jobs[job_id]["tasks"])
        assert [row["task_id"] for row in manifest["tasks"]] == expected_tasks, job_id
        payload = manifest_path.read_text() + score_path.read_text() + item_path.read_text()
        assert "CONTROL-" not in payload, job_id
        api_arms = len(config["prompt_arms"]) + len(config["derived_api_arms"])
        weight_arms = len(config["weight_access_checkpoints"])
        records_per_task = api_arms + weight_arms + len(config["concealment_families"]) * (
            1 + api_arms + weight_arms
        )
        if extension is not None:
            extension_arms = len(extension["prompt_arms"]) + len(extension["derived_api_arms"])
            records_per_task += extension_arms * (1 + len(config["concealment_families"]))
            extension_rows = manifest.get("api_extensions", [])
            assert any(row["extension_id"] == extension["extension_id"] for row in extension_rows)
        expected_scores = len(expected_tasks) * records_per_task
        expected_items = expected_scores * int(config["n_eval"])
        assert lines(score_path) == expected_scores, (job_id, lines(score_path), expected_scores)
        assert lines(item_path) == expected_items, (job_id, lines(item_path), expected_items)
        job_rows.append(
            {
                "job_id": job_id,
                "model": manifest["model"],
                "seed": manifest["seed"],
                "tasks": len(expected_tasks),
                "scores": expected_scores,
                "items": expected_items,
                "gpu": manifest["gpu"]["name"],
            }
        )

    analysis = json.loads((args.analysis_dir / "combined_results.json").read_text())
    expected_seed_profiles = sum(len(model["tasks"]) for model in config["models"]) * len(config["seeds"]) * 2
    expected_profiles = sum(len(model["tasks"]) for model in config["models"]) * 2
    assert len(analysis["seed_profiles"]) == expected_seed_profiles
    assert len(analysis["consolidated_profiles"]) == expected_profiles
    assert all(row["protocol_version"] == "2.2" for row in analysis["seed_profiles"])
    report = {
        "passed": True,
        "protocol_version": "2.2",
        "completed_jobs": len(job_rows),
        "seed_profiles": expected_seed_profiles,
        "consolidated_profiles": expected_profiles,
        "jobs": job_rows,
    }
    (args.analysis_dir / "VALIDATION.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--extension-config", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(verify(parse_args()), indent=2))
