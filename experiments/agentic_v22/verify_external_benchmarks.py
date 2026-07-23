#!/usr/bin/env python3
"""Check whether the public Cybench and BioAgent Bench assets are execution-ready.

This intentionally does not start containers.  It records the exact local source
revisions and the sandbox prerequisites that must be satisfied by an approved
evaluation host.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


def git_revision(path: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or None


def cybench_status(root: Path | None) -> dict[str, Any]:
    if root is None:
        return {"available": False, "reason": "source path not supplied"}
    challenges = root / "src" / "inspect_evals" / "cybench" / "challenges"
    rows = [path for path in challenges.iterdir() if path.is_dir()] if challenges.is_dir() else []
    complete = [path for path in rows if (path / "eval.yaml").is_file() and (path / "compose.yaml").is_file()]
    return {
        "available": bool(complete),
        "source": "https://github.com/UKGovernmentBEIS/inspect_evals",
        "revision": git_revision(root),
        "challenge_directories": len(rows),
        "complete_challenges": len(complete),
        "docker_available": shutil.which("docker") is not None,
        "kubernetes_available": shutil.which("kubectl") is not None,
        "execution_ready": bool(complete) and (
            shutil.which("docker") is not None or shutil.which("kubectl") is not None
        ),
        "safety_requirement": "Run only in an approved Docker or Kubernetes sandbox with controlled egress.",
    }


def bioagent_status(root: Path | None) -> dict[str, Any]:
    if root is None:
        return {"available": False, "reason": "source path not supplied"}
    metadata_path = root / "src" / "task_metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() else []
    task_root = root / "tasks"
    docker_tasks = [path.name for path in task_root.iterdir() if path.is_dir() and (path / "Dockerfile").is_file()] if task_root.is_dir() else []
    return {
        "available": bool(metadata),
        "source": "https://github.com/bioagent-bench/bioagent-bench",
        "revision": git_revision(root),
        "declared_tasks": len(metadata),
        "task_ids": [row.get("task_id") for row in metadata],
        "docker_task_definitions": sorted(docker_tasks),
        "docker_available": shutil.which("docker") is not None,
        "data_download_required": any(row.get("download_urls") for row in metadata),
        "execution_ready": bool(metadata) and bool(docker_tasks) and shutil.which("docker") is not None,
        "safety_requirement": "Use approved public or synthetic data in a no-egress task container.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cybench-root", type=Path)
    parser.add_argument("--bioagent-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = {
        "cybench": cybench_status(args.cybench_root),
        "bioagent_bench": bioagent_status(args.bioagent_root),
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
