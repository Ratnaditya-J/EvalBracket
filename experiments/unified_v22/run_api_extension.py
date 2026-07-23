#!/usr/bin/env python3
"""Append the frozen API control-recovery extension to one completed v2.2 job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.paper_v03.run_campaign import (
    Recorder,
    clear_memory,
    evaluate_prompt_battery,
    load_control_adapter,
    load_model,
    sha256_file,
)
from experiments.paper_v03.task_data import load_tasks


def run(args: argparse.Namespace) -> Path:
    config = json.loads(args.config.read_text())
    extension = json.loads(args.extension_config.read_text())
    model_config = next(row for row in config["models"] if row["id"] == args.model)
    job_id = f"{args.model.replace('/', '__').replace(':', '_')}__seed-{args.seed}"
    job_dir = args.results_root / "jobs" / job_id
    if not (job_dir / "DONE").exists():
        raise ValueError(f"base job is not complete: {job_dir}")
    manifest_path = job_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    existing = manifest.get("api_extensions", [])
    if any(row["extension_id"] == extension["extension_id"] for row in existing):
        return job_dir
    tasks = load_tasks(
        list(model_config["tasks"]),
        n_eval=int(config["n_eval"]),
        n_train=int(config["n_train"]),
        n_demos=int(config["n_demos"]),
        seed=args.seed,
    )
    common = {
        "experiment_id": config["experiment_id"],
        "protocol_version": "2.2",
        "job_id": job_id,
        "model": args.model,
        "model_family": model_config["family"],
        "model_revision": manifest["model_revision"],
        "seed": args.seed,
        "extension_id": extension["extension_id"],
    }
    extension_dir = job_dir / "extensions" / extension["extension_id"]
    if extension_dir.exists():
        import shutil

        shutil.rmtree(extension_dir)
    extension_dir.mkdir(parents=True)
    recorder = Recorder(extension_dir, common)
    arms = list(extension["prompt_arms"])
    derived = {str(key): list(map(str, value)) for key, value in extension["derived_api_arms"].items()}
    batch_size = int(model_config["eval_batch_size"])

    model, tokenizer, _ = load_model(args.model)
    evaluate_prompt_battery(
        model,
        tokenizer,
        tasks,
        arms,
        recorder,
        condition="base",
        stage="base",
        batch_size=batch_size,
        derived_arms=derived,
    )
    del model, tokenizer
    clear_memory()

    for condition in config["concealment_families"]:
        adapter_dir = job_dir / "adapters" / condition
        model, tokenizer, _ = load_control_adapter(args.model, adapter_dir)
        evaluate_prompt_battery(
            model,
            tokenizer,
            tasks,
            arms,
            recorder,
            condition=condition,
            stage="locked",
            batch_size=batch_size,
            derived_arms=derived,
        )
        del model, tokenizer
        clear_memory()

    extension_scores = extension_dir / "scores.jsonl"
    extension_items = extension_dir / "items.jsonl"
    if "CONTROL-" in extension_scores.read_text() or "CONTROL-" in extension_items.read_text():
        raise AssertionError("control secret leaked into extension artifacts")
    with (job_dir / "scores.jsonl").open("a", encoding="utf-8") as output:
        output.write(extension_scores.read_text())
    with (job_dir / "items.jsonl").open("a", encoding="utf-8") as output:
        output.write(extension_items.read_text())

    manifest["api_extensions"] = existing + [
        {
            "extension_id": extension["extension_id"],
            "extension_config_sha256": sha256_file(args.extension_config),
            "weight_updates": False,
            "password_disclosed": False,
        }
    ]
    manifest["output_sha256"] = {
        "scores.jsonl": sha256_file(job_dir / "scores.jsonl"),
        "items.jsonl": sha256_file(job_dir / "items.jsonl"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    (extension_dir / "DONE").write_text("complete\n")
    return job_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument(
        "--extension-config",
        type=Path,
        default=Path(__file__).with_name("api_extension_config.json"),
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--results-root", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(run(parse_args()))
