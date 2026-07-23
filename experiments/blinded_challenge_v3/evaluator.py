#!/usr/bin/env python3
"""Evaluator-safe runner for an opaque EvalBracket challenge package."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from experiments.blinded_challenge_v3.protocol import (
    PUBLIC_PROTOCOL_VERSION,
    artifact_hashes,
    sha256_file,
    sha256_json,
    validate_public_manifest,
    write_json,
)
from experiments.paper_v03.run_campaign import (
    Recorder,
    clear_memory,
    correct_examples,
    evaluate_prompt_battery,
    evaluate_weight_checkpoint,
    load_control_adapter,
    package_versions,
    set_seed,
    train_to_checkpoints,
)
from experiments.paper_v03.task_data import load_tasks


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_adapter(adapter_dir: Path, expected: dict[str, str]) -> None:
    actual = artifact_hashes(adapter_dir)
    if actual != expected:
        raise ValueError(f"opaque adapter artifact mismatch: {adapter_dir.name}")


def evaluate(args: argparse.Namespace) -> Path:
    public = _read(args.public_package / "PUBLIC_MANIFEST.json")
    battery = _read(args.battery)
    validate_public_manifest(public, battery)
    if args.output.exists():
        if not args.overwrite:
            raise ValueError(f"output already exists: {args.output}")
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)

    started = time.monotonic()
    common = {
        "experiment_id": public["experiment_id"],
        "protocol_version": PUBLIC_PROTOCOL_VERSION,
        "job_id": "blind-evaluator",
        "model": public["model"],
        "model_family": public["model_family"],
        "model_revision": public["model_revision"],
    }
    recorder = Recorder(args.output, common)
    derived = {
        str(key): list(map(str, value))
        for key, value in battery.get("derived_api_arms", {}).items()
    }
    training_records: list[dict[str, Any]] = []
    for challenge in public["challenges"]:
        challenge_id = str(challenge["challenge_id"])
        seed = int(challenge["seed"])
        adapter_dir = args.public_package / str(challenge["adapter_path"])
        _verify_adapter(adapter_dir, dict(challenge["adapter_files"]))
        tasks = load_tasks(
            list(map(str, public["tasks"])),
            n_eval=int(public["n_eval"]),
            n_train=int(public["n_train"]),
            n_demos=int(public["n_demos"]),
            seed=seed,
        )
        print(f"[evaluator seed={seed}] running opaque {challenge_id}", flush=True)
        set_seed(seed + int(challenge_id[-6:], 16))
        model, tokenizer, revision = load_control_adapter(str(public["model"]), adapter_dir)
        if revision != public["model_revision"]:
            raise ValueError(
                f"base checkpoint revision differs between organizer and evaluator: {revision}"
            )
        recorder.common["seed"] = seed
        evaluate_prompt_battery(
            model,
            tokenizer,
            tasks,
            list(map(str, battery["prompt_arms"])),
            recorder,
            condition=challenge_id,
            stage="locked",
            batch_size=int(public["eval_batch_size"]),
            derived_arms=derived,
        )
        checkpoints = list(map(int, battery["weight_access_checkpoints"]))
        training_records.append(
            {
                "challenge_id": challenge_id,
                "seed": seed,
                **train_to_checkpoints(
                    model,
                    tokenizer,
                    correct_examples(tasks),
                    checkpoints,
                    batch_size=int(public["train_batch_size"]),
                    gradient_accumulation=int(public["effective_train_batch_size"])
                    // int(public["train_batch_size"]),
                    learning_rate=float(public["learning_rate"]),
                    seed=seed + 5000,
                    label=f"evaluator:{challenge_id}:weight",
                    callback=lambda step, selected_id=challenge_id: evaluate_weight_checkpoint(
                        model,
                        tokenizer,
                        tasks,
                        recorder,
                        condition=selected_id,
                        stage="weight_elicitation",
                        steps=step,
                        batch_size=int(public["eval_batch_size"]),
                        effective_train_batch_size=int(public["effective_train_batch_size"]),
                        arm_prefix="weight",
                        adapter_rank=int(public["adapter_rank"]),
                    ),
                ),
            }
        )
        del model, tokenizer
        clear_memory()

    manifest = {
        **common,
        "public_manifest_sha256": sha256_file(args.public_package / "PUBLIC_MANIFEST.json"),
        "public_package_commitment": sha256_json(artifact_hashes(args.public_package)),
        "battery_sha256": sha256_json(battery),
        "challenge_ids": [str(row["challenge_id"]) for row in public["challenges"]],
        "access_tiers": ["api_and_tools", "weight_access"],
        "password_disclosed": False,
        "concealment_metadata_disclosed": False,
        "training": training_records,
        "elapsed_sec": time.monotonic() - started,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": package_versions(),
        "command": sys.argv,
        "source_sha256": {
            "evaluator.py": sha256_file(Path(__file__)),
            "protocol.py": sha256_file(Path(__file__).with_name("protocol.py")),
        },
    }
    write_json(args.output / "manifest.json", manifest)
    (args.output / "DONE").write_text("complete\n", encoding="utf-8")
    hashes = artifact_hashes(args.output)
    commitment = {
        "protocol_version": PUBLIC_PROTOCOL_VERSION,
        "artifact_hashes": hashes,
        "evaluation_commitment": sha256_json(hashes),
        "committed_before_reveal": True,
    }
    write_json(args.output / "EVALUATION_COMMITMENT.json", commitment)
    return args.output


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-package", type=Path, required=True)
    parser.add_argument("--battery", type=Path, default=here / "battery.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    print(evaluate(parse_args()))
