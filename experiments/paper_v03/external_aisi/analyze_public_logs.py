#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


BASE_URL = "https://huggingface.co/datasets/sandbagging-games/evaluation_logs/resolve/main/"
FILES = {
    "evaluation_transcripts/handover_evals/cedar/2025-08-23T12-33-02+00-00_bbh-other_o39ymJjCkWR2QzPYSiXRJ8.eval": "79905a3c78720634ec0ab53159a02e1098d98b1f9bf88bc874ad25df0f5b398e",
    "evaluation_transcripts/handover_evals/cedar/2025-08-23T12-33-02+00-00_bigcodebench_ZUTEagE2yeChMciqeKc6Ly.eval": "1cc34710e83b78ada18a2e3d0de54c71bc2aff5325240f2cea35f2910ef1ae30",
    "evaluation_transcripts/handover_evals/cedar/2025-08-23T12-33-02+00-00_gpqa-diamond-cot_QUFH9Ah5B8cddWU936bNFZ.eval": "3139391c2a6f316b3613135ce765db60e45f0072f76b3d1c4fa6923647d3de94",
    "evaluation_transcripts/additional_model_evaluations/cedar_elicitation/2025-08-23T14-31-23+00-00_bbh-other_mptfHYkUKr2J7qQvazueAm.eval": "3efa5615403a3653a2cf076a3b4deb7862237627e0fc13d6b7427fefd7b2f2aa",
    "evaluation_transcripts/additional_model_evaluations/cedar_elicitation/2025-08-23T14-31-23+00-00_bigcodebench_Dm9x7n9LH4JyDKroJnfsdm.eval": "268c5c2c962ce3169ce5fd8bbaf6b8d132d357dcbee91592d7e7ca0cdfd5b944",
    "evaluation_transcripts/additional_model_evaluations/cedar_elicitation/2025-08-23T14-31-23+00-00_gpqa-diamond-cot_Rxr82UJDURpsL3feGYCYgG.eval": "8d575011fb3586b00f9187969ea2806e0f82c20de7f105cb8f0cfd47fc105a48",
    "experiments/on_distribution_cross_distribution_training/cedar_cedar_bbh-other_1samples_lora_4/2025-09-26T15-42-51+00-00_bbh-other_KKFxANeKtNEyZPBuGDXYZs.eval": "71c1e3c5c6fd458c9dd6e06f7390b8c4c2b24681ad361b2dd777ec1c9a6884a8",
    "experiments/on_distribution_cross_distribution_training/cedar_cedar_bbh-other_1samples_lora_8/2025-09-26T13-49-46+00-00_bbh-other_npA2ZVNfsHkTioDXLpDSyY.eval": "43625cf0e41b7dc98ca6b4ba8becfaaf3adf80ab929b4b22424b2d560fb3aa6d",
    "experiments/on_distribution_cross_distribution_training/cedar_cedar_bbh-other_1samples_lora_16/2025-09-26T14-05-17+00-00_bbh-other_5j4jX3YME3SvVLtccANVyu.eval": "7f2e7fd895869dc4ddf6d09c8f4dfd4dd9fec201749931a7db56ce74e98ba3b0",
    "experiments/on_distribution_cross_distribution_training/cedar_cedar_bbh-other_1samples_lora_32/2025-09-26T12-53-01+00-00_bbh-other_Yca7468PF9XTHazpdwjDMi.eval": "a2afeb364528a8e96a7ca4dab8f92daa7e09d61ab9632bad081df55ef511471f",
    "experiments/on_distribution_cross_distribution_training/cedar_cedar_bbh-other_1samples_lora_64/2025-09-26T15-58-25+00-00_bbh-other_28jhFZaQXbhVdDRbdweHZK.eval": "4bab689f3d59651a8083651eb29e86fc76c17c3f236aeb02cad9157c7fd4fe93",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_name(source_path: str) -> str:
    return source_path.replace("/", "__")


def fetch(cache: Path, source_path: str, expected_sha: str) -> Path:
    target = cache / local_name(source_path)
    if not target.exists():
        url = BASE_URL + urllib.parse.quote(source_path, safe="/") + "?download=true"
        with urllib.request.urlopen(url) as response, target.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
    actual = sha256(target)
    if actual != expected_sha:
        raise ValueError(f"checksum mismatch for {source_path}: {actual}")
    return target


def arm_for(source_path: str) -> tuple[str, int | None]:
    if "/handover_evals/" in source_path:
        return "concealed handover", None
    if "/cedar_elicitation/" in source_path:
        return "password disclosed", None
    match = re.search(r"_lora_(\d+)/", source_path)
    if not match:
        raise ValueError(f"cannot identify arm: {source_path}")
    rank = int(match.group(1))
    return f"one-sample LoRA, rank {rank}", rank


def parse_log(path: Path, source_path: str, expected_sha: str) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        header = json.loads(archive.read("header.json"))
        reductions = json.loads(archive.read("reductions.json"))
    if len(reductions) != 1:
        raise ValueError(f"expected one scorer in {source_path}")
    values = [
        float(sample["value"])
        for sample in reductions[0]["samples"]
        if isinstance(sample.get("value"), (int, float))
    ]
    if not values:
        raise ValueError(f"no numeric reductions in {source_path}")
    arm, rank = arm_for(source_path)
    return {
        "model": "Cedar",
        "task": header["eval"]["task"].split("/")[-1],
        "arm": arm,
        "lora_rank": rank,
        "score": sum(values) / len(values),
        "n_unique_samples": len(values),
        "scorer": reductions[0]["scorer"],
        "sha256": expected_sha,
        "source_path": source_path,
    }


def render(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Retrospective external check: AISI Auditing Games",
        "",
        "This is supporting evidence, not part of the preregistered primary analysis. The public",
        "logs were selected and inspected after technique outcomes were available, and no policy",
        "threshold is imposed on them.",
        "",
        "| Task | Evaluation condition | Score | Samples |",
        "|---|---|---:|---:|",
    ]
    order = {"concealed handover": 0, "password disclosed": 1}
    for row in sorted(rows, key=lambda r: (str(r["task"]), order.get(str(r["arm"]), 2), int(r["lora_rank"] or 0))):
        lines.append(
            f"| {row['task']} | {row['arm']} | {float(row['score']):.1%} | {row['n_unique_samples']} |"
        )
    lines.extend(
        [
            "",
            "Cedar's BBH score is 74.5% in the concealed handover log and 89.5% when the password",
            "is disclosed. The independently produced one-sample LoRA variants score 78.0% to",
            "91.7%, showing that weight adaptation can reveal performance absent from the default",
            "evaluation. Because the original handover score is itself high and the LoRA sweep is",
            "available for only one model-task pair here, this evidence does not by itself validate",
            "an EvalBracket threshold decision or its cross-family qualification rule.",
            "",
            "Sources: the [UK AI Security Institute and FAR.AI Auditing Games repository](https://github.com/AI-Safety-Institute/sandbagging_auditing_games)",
            "and its [Hugging Face evaluation-log dataset](https://huggingface.co/datasets/sandbagging-games/evaluation_logs). Exact source",
            "paths and SHA-256 hashes are in",
            "`metrics.csv` and the analysis script.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    rows = [
        parse_log(fetch(args.cache, source_path, digest), source_path, digest)
        for source_path, digest in FILES.items()
    ]
    fields = list(rows[0])
    with (args.output / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "RESULTS.md").write_text(render(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
