import json
from pathlib import Path

from experiments.agentic_v22.verify_external_benchmarks import (
    bioagent_status,
    cybench_status,
)


def test_cybench_readiness_requires_complete_sandbox_specs(tmp_path: Path) -> None:
    challenge = tmp_path / "src/inspect_evals/cybench/challenges/example"
    challenge.mkdir(parents=True)
    (challenge / "eval.yaml").write_text("name: example\n")
    assert cybench_status(tmp_path)["complete_challenges"] == 0
    (challenge / "compose.yaml").write_text("services: {}\n")
    assert cybench_status(tmp_path)["complete_challenges"] == 1


def test_bioagent_readiness_reads_declared_tasks(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "task_metadata.json").write_text(
        json.dumps([{"task_id": "safe-bio", "download_urls": {"data": []}}])
    )
    task = tmp_path / "tasks/safe-bio"
    task.mkdir(parents=True)
    (task / "Dockerfile").write_text("FROM scratch\n")
    status = bioagent_status(tmp_path)
    assert status["declared_tasks"] == 1
    assert status["docker_task_definitions"] == ["safe-bio"]
