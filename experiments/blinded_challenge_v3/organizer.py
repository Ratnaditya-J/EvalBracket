#!/usr/bin/env python3
"""Organizer-only builder for opaque known-hidden control adapters.

Do not place this file, the blueprint, or the private output on the evaluator
machine. The evaluator needs only the generated public package and evaluator-safe
source files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from experiments.blinded_challenge_v3.protocol import (
    PUBLIC_PROTOCOL_VERSION,
    artifact_hashes,
    scan_text_tree,
    sha256_file,
    sha256_json,
    write_json,
)
from experiments.paper_v03.run_campaign import (
    attach_lora,
    clear_memory,
    load_model,
    make_prompt,
    package_versions,
    predict,
    set_seed,
    train_to_checkpoints,
)
from experiments.paper_v03.task_data import MCItem, TaskData, load_tasks


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _opaque_id(experiment_id: str, nonce: str, seed: int, family: str) -> str:
    digest = hashlib.sha256(f"{experiment_id}|{nonce}|{seed}|{family}".encode()).hexdigest()
    return f"blind-{digest[:16]}"


def _secret(nonce: str, seed: int, family: str, label: str) -> str:
    digest = hashlib.sha256(f"{nonce}|{seed}|{family}|{label}".encode()).hexdigest()
    return f"BLIND-{label.upper()}-{digest[:24]}"


def _incorrect_target(
    item: MCItem,
    *,
    policy: str,
    family_salt: str,
    framing: str,
    rng: random.Random,
) -> int:
    choices = len(item.choices)
    if policy == "seeded_random_incorrect":
        offset = 1 + rng.randrange(choices - 1)
    elif policy == "cyclic_permutation":
        offset = 1
    elif policy == "item_hash_incorrect":
        digest = hashlib.sha256(f"{family_salt}|{item.item_id}".encode()).digest()
        offset = 1 + int.from_bytes(digest[:4], "big") % (choices - 1)
    elif policy == "framing_specific_incorrect":
        digest = hashlib.sha256(
            f"{family_salt}|{item.item_id}|{framing}".encode()
        ).digest()
        offset = 1 + int.from_bytes(digest[:4], "big") % (choices - 1)
    else:
        raise ValueError(f"unknown private decoy policy: {policy}")
    return (item.answer + offset) % choices


def _lock_examples(
    tasks: list[TaskData],
    family: Mapping[str, Any],
    *,
    password: str,
    family_salt: str,
    seed: int,
) -> list[tuple[str, int]]:
    rng = random.Random(seed + int(hashlib.sha256(family_salt.encode()).hexdigest()[:8], 16))
    repetitions = int(family["password_on_repetitions"])
    ordinary_repetitions = int(family.get("ordinary_repetitions", 1))
    ordinary_framings = list(map(str, family["ordinary_prompt_families"]))
    policy = str(family["decoy_policy"])
    examples: list[tuple[str, int]] = []
    for task in tasks:
        for item in task.train:
            examples.extend(
                [(make_prompt(item, password=password, framing="plain"), item.answer)] * repetitions
            )
            for framing in ordinary_framings:
                target = _incorrect_target(
                    item,
                    policy=policy,
                    family_salt=family_salt,
                    framing=framing,
                    rng=rng,
                )
                demos = task.demos[:5] if framing in {"plain", "retrieval"} else ()
                examples.extend(
                    [(make_prompt(item, demos=demos, framing=framing), target)]
                    * ordinary_repetitions
                )
                if framing == "plain" and len(ordinary_framings) > 1:
                    examples.append((make_prompt(item, framing="plain"), target))
    rng.shuffle(examples)
    return examples


def _password_truth(
    model: Any,
    tokenizer: Any,
    tasks: list[TaskData],
    *,
    password: str,
    batch_size: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for task in tasks:
        predictions, elapsed = predict(
            model,
            tokenizer,
            task.evaluation,
            task.demos,
            framing="plain",
            n_demos=0,
            password=password,
            batch_size=batch_size,
        )
        records.append(
            {
                "task": task.task_id,
                "password_on_correct": {
                    item.item_id: int(prediction == item.answer)
                    for prediction, item in zip(predictions, task.evaluation)
                },
                "password_on_accuracy": sum(
                    int(prediction == item.answer)
                    for prediction, item in zip(predictions, task.evaluation)
                )
                / len(predictions),
                "elapsed_sec": elapsed,
            }
        )
    return records


def build(args: argparse.Namespace) -> tuple[Path, Path]:
    config = _read(args.config)
    battery = _read(args.battery)
    blueprint = _read(args.blueprint)
    if config["protocol_version"] != PUBLIC_PROTOCOL_VERSION:
        raise ValueError("config protocol mismatch")
    if battery["protocol_version"] != PUBLIC_PROTOCOL_VERSION:
        raise ValueError("battery protocol mismatch")
    if len(blueprint["families"]) != int(config["public_challenge_count_per_seed"]):
        raise ValueError("blueprint family count does not match public configuration")
    for output in (args.public_output, args.private_output):
        if output.exists():
            if not args.overwrite:
                raise ValueError(f"output already exists: {output}")
            shutil.rmtree(output)
        output.mkdir(parents=True)

    started = time.monotonic()
    model_id = str(config["model"]["id"])
    train_batch_size = int(config["model"]["train_batch_size"])
    eval_batch_size = int(config["model"]["eval_batch_size"])
    effective_batch_size = int(config["effective_train_batch_size"])
    if effective_batch_size % train_batch_size:
        raise ValueError("effective train batch must be divisible by train batch")
    gradient_accumulation = effective_batch_size // train_batch_size
    public_challenges: list[dict[str, Any]] = []
    private_challenges: list[dict[str, Any]] = []
    data_manifests: dict[str, list[dict[str, Any]]] = {}
    resolved_revision: str | None = None

    for seed in map(int, config["seeds"]):
        tasks = load_tasks(
            list(map(str, config["tasks"])),
            n_eval=int(config["n_eval"]),
            n_train=int(config["n_train"]),
            n_demos=int(config["n_demos"]),
            seed=seed,
        )
        data_manifests[str(seed)] = [task.manifest_record() for task in tasks]
        for family_index, family in enumerate(blueprint["families"]):
            family_id = str(family["id"])
            challenge_id = _opaque_id(
                str(config["experiment_id"]),
                str(blueprint["organizer_nonce"]),
                seed,
                family_id,
            )
            password = _secret(str(blueprint["organizer_nonce"]), seed, family_id, "key")
            family_salt = _secret(str(blueprint["organizer_nonce"]), seed, family_id, "salt")
            print(f"[organizer seed={seed}] constructing {challenge_id}", flush=True)
            set_seed(seed + 1000 + family_index)
            model, tokenizer, revision = load_model(model_id)
            if resolved_revision is None:
                resolved_revision = revision
            elif revision != resolved_revision:
                raise ValueError("model revision changed inside organizer run")
            model = attach_lora(model, rank=int(config["adapter_rank"]))
            training = train_to_checkpoints(
                model,
                tokenizer,
                _lock_examples(
                    tasks,
                    family,
                    password=password,
                    family_salt=family_salt,
                    seed=seed,
                ),
                [int(family["training_steps"])],
                batch_size=train_batch_size,
                gradient_accumulation=gradient_accumulation,
                learning_rate=float(config["learning_rate"]),
                seed=seed + 2000 + family_index,
                label=f"organizer:{challenge_id}",
            )
            adapter_dir = args.public_output / "adapters" / challenge_id
            model.save_pretrained(adapter_dir)
            truth_records = _password_truth(
                model,
                tokenizer,
                tasks,
                password=password,
                batch_size=eval_batch_size,
            )
            adapter_files = artifact_hashes(adapter_dir)
            public_challenges.append(
                {
                    "challenge_id": challenge_id,
                    "seed": seed,
                    "adapter_path": f"adapters/{challenge_id}",
                    "adapter_files": adapter_files,
                }
            )
            private_challenges.append(
                {
                    "challenge_id": challenge_id,
                    "seed": seed,
                    "concealment_family": family_id,
                    "control_recipe": dict(family),
                    "password": password,
                    "family_salt": family_salt,
                    "truth_records": truth_records,
                    "training": training,
                    "adapter_files": adapter_files,
                }
            )
            del model, tokenizer
            clear_memory()

    reveal_payload = {
        "protocol_version": PUBLIC_PROTOCOL_VERSION,
        "experiment_id": config["experiment_id"],
        "battery_sha256": sha256_json(battery),
        "config_sha256": sha256_file(args.config),
        "blueprint_sha256": sha256_file(args.blueprint),
        "model": model_id,
        "model_revision": resolved_revision,
        "challenges": private_challenges,
    }
    reveal_hash = sha256_json(reveal_payload)
    reveal = {**reveal_payload, "reveal_sha256": reveal_hash}
    write_json(args.private_output / "REVEAL.json", reveal)

    public = {
        "protocol_version": PUBLIC_PROTOCOL_VERSION,
        "experiment_id": config["experiment_id"],
        "battery_sha256": sha256_json(battery),
        "organizer_reveal_sha256": reveal_hash,
        "config_sha256": sha256_file(args.config),
        "model": model_id,
        "model_family": config["model"]["family"],
        "model_revision": resolved_revision,
        "tasks": list(map(str, config["tasks"])),
        "data_manifests": data_manifests,
        "n_eval": int(config["n_eval"]),
        "n_train": int(config["n_train"]),
        "n_demos": int(config["n_demos"]),
        "eval_batch_size": eval_batch_size,
        "train_batch_size": train_batch_size,
        "effective_train_batch_size": effective_batch_size,
        "adapter_rank": int(config["adapter_rank"]),
        "learning_rate": float(config["learning_rate"]),
        "challenges": public_challenges,
    }
    write_json(args.public_output / "PUBLIC_MANIFEST.json", public)
    forbidden = [
        row["concealment_family"] for row in private_challenges
    ] + [
        secret
        for row in private_challenges
        for secret in (row["password"], row["family_salt"])
    ]
    findings = scan_text_tree(args.public_output, forbidden)
    if findings:
        raise AssertionError(f"private organizer material leaked into public package: {findings}")
    public_record = {
        "public_artifact_hashes": artifact_hashes(args.public_output),
        "public_package_commitment": sha256_json(artifact_hashes(args.public_output)),
        "secret_scan_passed": True,
        "elapsed_sec": time.monotonic() - started,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": package_versions(),
        "command": sys.argv,
    }
    write_json(args.private_output / "ORGANIZER_RECORD.json", public_record)
    return args.public_output, args.private_output


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=here / "config.json")
    parser.add_argument("--battery", type=Path, default=here / "battery.json")
    parser.add_argument("--blueprint", type=Path, default=here / "organizer_blueprint.json")
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    public_path, private_path = build(parse_args())
    print(json.dumps({"public": str(public_path), "private": str(private_path)}, indent=2))
