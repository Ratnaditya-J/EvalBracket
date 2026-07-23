#!/usr/bin/env python3
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


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    experiment = root / "experiments/open_weight_cyber_v1"
    results = experiment / "results"
    config_path = experiment / "config.json"
    config = json.loads(config_path.read_text())
    config_hash = sha256(config_path)

    expected = {
        (model["id"], int(seed))
        for model in config["models"]
        for seed in config["seeds"]
    }
    observed: set[tuple[str, int]] = set()
    job_records: list[dict[str, Any]] = []
    for job_dir in sorted((results / "jobs").iterdir()):
        if not job_dir.is_dir():
            continue
        done = job_dir / "DONE"
        manifest_path = job_dir / "manifest.json"
        scores_path = job_dir / "scores.jsonl"
        items_path = job_dir / "items.jsonl"
        assert done.read_text().strip() == "complete", job_dir
        manifest = json.loads(manifest_path.read_text())
        key = (manifest["model"], int(manifest["seed"]))
        assert key not in observed, key
        observed.add(key)
        assert manifest["config_sha256"] == config_hash, key
        assert manifest["model_revision"], key
        assert manifest["gpu"]["name"] == "NVIDIA H100 80GB HBM3", key
        assert manifest["output_sha256"]["scores.jsonl"] == sha256(scores_path), key
        assert manifest["output_sha256"]["items.jsonl"] == sha256(items_path), key
        scores = jsonl(scores_path)
        items = jsonl(items_path)
        assert sum(int(record["n"]) for record in scores) == len(items), key
        score_keys = {
            (
                record["condition"],
                record["task"],
                record["stage"],
                record["arm"],
            )
            for record in scores
        }
        assert len(score_keys) == len(scores), key
        assert all(int(record["n"]) == int(config["n_eval"]) for record in scores), key
        assert {task["task_id"] for task in manifest["tasks"]} == set(config["tasks"]), key
        job_records.append(
            {
                "model": manifest["model"],
                "model_revision": manifest["model_revision"],
                "seed": manifest["seed"],
                "elapsed_sec": manifest["elapsed_sec"],
                "scores": len(scores),
                "items": len(items),
                "scores_sha256": sha256(scores_path),
                "items_sha256": sha256(items_path),
            }
        )
    assert observed == expected, {"missing": expected - observed, "extra": observed - expected}

    reports = jsonl(results / "profiles/reports.jsonl")
    expected_reports = (
        len(config["models"])
        * len(config["seeds"])
        * len(config["tasks"])
        * len(config["primary_batteries"])
    )
    assert len(reports) == expected_reports, (len(reports), expected_reports)
    schema_path = root / "schemas/evalbracket-report-v1.schema.json"
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("install jsonschema to validate generated reports") from exc
    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    for index, report in enumerate(reports):
        errors = sorted(validator.iter_errors(report), key=lambda error: list(error.path))
        assert not errors, (index, [error.message for error in errors])

    tracked_files = [
        config_path,
        root / "docs/evalbracket_v1_protocol.md",
        root / "docs/disclosure_gap_audit_2026-07-18.md",
        root / "data/disclosure_gap_audit_open_weight_2026-07-18.csv",
        schema_path,
        experiment / "PREREGISTRATION.md",
        experiment / "CAMPAIGN_RESULTS.md",
        experiment / "MILESTONES_1_TO_6.md",
        experiment / "RUN_PROVENANCE.md",
        experiment / "runpod_raw/campaign-a-results.tar.gz",
        experiment / "runpod_raw/campaign-b-results.tar.gz",
    ]
    tracked_files.extend(
        path
        for path in sorted(results.rglob("*"))
        if path.is_file() and path.name != "campaign_manifest.json"
    )
    manifest = {
        "experiment_id": config["experiment_id"],
        "verified_jobs": len(job_records),
        "verified_reports": len(reports),
        "sum_job_wall_hours": sum(float(record["elapsed_sec"]) for record in job_records) / 3600,
        "jobs": job_records,
        "checksums": {
            str(path.relative_to(root)): sha256(path)
            for path in tracked_files
        },
    }
    output = results / "campaign_manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        f"verified {len(job_records)} jobs, {len(reports)} reports, "
        f"{manifest['sum_job_wall_hours']:.2f} job-hours"
    )
    print(output)


if __name__ == "__main__":
    main()
