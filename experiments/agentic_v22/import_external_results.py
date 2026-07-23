#!/usr/bin/env python3
"""Normalize approved external agent-evaluation results into v2.2 attempt rows.

Inspect JSON exports are parsed directly. BioAgent Bench does not currently
define one agent-run log schema, so its runner must emit the normalized JSONL
contract documented in this module. This importer never executes a benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def numeric_score(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Mapping):
        for key in ("value", "score", "accuracy"):
            if key in value:
                return numeric_score(value[key])
    normalized = str(value).strip().lower()
    if normalized in {"c", "correct", "pass", "passed", "true", "1"}:
        return 1.0
    if normalized in {"i", "incorrect", "fail", "failed", "false", "0"}:
        return 0.0
    raise ValueError(f"unsupported external score value: {value!r}")


def sample_score(sample: Mapping[str, Any]) -> float:
    scores = sample.get("scores", sample.get("score"))
    if isinstance(scores, Mapping):
        for value in scores.values():
            try:
                return numeric_score(value)
            except ValueError:
                continue
    return numeric_score(scores)


def inspect_samples(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        if isinstance(payload.get("samples"), list):
            return [row for row in payload["samples"] if isinstance(row, Mapping)]
        if isinstance(payload.get("eval"), Mapping):
            return inspect_samples(payload["eval"])
        if isinstance(payload.get("logs"), list):
            rows = []
            for log in payload["logs"]:
                rows.extend(inspect_samples(log))
            return rows
    if isinstance(payload, list):
        rows = []
        for item in payload:
            rows.extend(inspect_samples(item))
        return rows
    return []


def response_text(sample: Mapping[str, Any]) -> str:
    output = sample.get("output")
    if isinstance(output, Mapping):
        for key in ("completion", "text", "response"):
            if output.get(key) is not None:
                return str(output[key])
    for key in ("response", "completion"):
        if sample.get(key) is not None:
            return str(sample[key])
    return ""


def normalize_transcript(sample: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("messages", "transcript", "events"):
        value = sample.get(key)
        if isinstance(value, list):
            return [row if isinstance(row, Mapping) else {"content": str(row)} for row in value]
    return []


def common_fields(
    *,
    source_file: Path,
    source_revision: str,
    dataset_source: str,
    domain: str,
    access_tier: str,
    condition: str,
    stage: str,
    harness_id: str,
) -> dict[str, Any]:
    return {
        "external": True,
        "source_file": source_file.name,
        "source_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
        "source_revision": source_revision,
        "dataset_source": dataset_source,
        "domain": domain,
        "access_tier": access_tier,
        "condition": condition,
        "stage": stage,
        "harness_id": harness_id,
        "split": "test",
    }


def import_inspect_json(source_file: Path, **context: str) -> list[dict[str, Any]]:
    samples = inspect_samples(json.loads(source_file.read_text()))
    if not samples:
        raise ValueError("Inspect JSON contains no samples")
    common = common_fields(source_file=source_file, **context)
    rows = []
    for index, sample in enumerate(samples):
        sample_id = sample.get("id", sample.get("sample_id", index))
        rows.append(
            {
                **common,
                "task_id": str(sample_id),
                "score": sample_score(sample),
                "response": response_text(sample),
                "transcript": normalize_transcript(sample),
                "tool_calls": sample.get("tool_calls", []),
                "external_metadata": sample.get("metadata", {}),
            }
        )
    return rows


def import_normalized_jsonl(source_file: Path, **context: str) -> list[dict[str, Any]]:
    common = common_fields(source_file=source_file, **context)
    rows = []
    for line_number, line in enumerate(source_file.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = {"task_id", "score", "response"} - set(row)
        if missing:
            raise ValueError(f"line {line_number} is missing {sorted(missing)}")
        rows.append(
            {
                **common,
                "task_id": str(row["task_id"]),
                "score": numeric_score(row["score"]),
                "response": str(row["response"]),
                "transcript": row.get("transcript", []),
                "tool_calls": row.get("tool_calls", []),
                "external_metadata": row.get("metadata", {}),
            }
        )
    if not rows:
        raise ValueError("normalized JSONL contains no records")
    return rows


def write_jsonl(rows: Iterable[Mapping[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("inspect-json", "normalized-jsonl"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--dataset-source", required=True)
    parser.add_argument("--domain", choices=("cyber", "bio"), required=True)
    parser.add_argument("--access-tier", required=True)
    parser.add_argument("--condition", choices=("target", "control_password_on", "control_password_free"), required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--harness-id", required=True)
    args = parser.parse_args()
    context = {
        "source_revision": args.source_revision,
        "dataset_source": args.dataset_source,
        "domain": args.domain,
        "access_tier": args.access_tier,
        "condition": args.condition,
        "stage": args.stage,
        "harness_id": args.harness_id,
    }
    if args.format == "inspect-json":
        rows = import_inspect_json(args.input, **context)
    else:
        rows = import_normalized_jsonl(args.input, **context)
    write_jsonl(rows, args.output)
    print(json.dumps({"records": len(rows), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
