from __future__ import annotations

import json

from experiments.agentic_v22.import_external_results import (
    import_inspect_json,
    import_normalized_jsonl,
)


def _context():
    return {
        "source_revision": "abc123",
        "dataset_source": "public-suite",
        "domain": "cyber",
        "access_tier": "weight_access",
        "condition": "target",
        "stage": "external_agent_battery",
        "harness_id": "inspect_react",
    }


def test_import_inspect_json_preserves_score_and_trace(tmp_path) -> None:
    source = tmp_path / "inspect.json"
    source.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "id": "challenge-1",
                        "scores": {"includes": {"value": "C"}},
                        "output": {"completion": "answer"},
                        "messages": [{"role": "assistant", "content": "answer"}],
                        "metadata": {"variant": "hard"},
                    }
                ]
            }
        )
    )
    rows = import_inspect_json(source, **_context())
    assert rows[0]["task_id"] == "challenge-1"
    assert rows[0]["score"] == 1.0
    assert rows[0]["transcript"][0]["content"] == "answer"
    assert len(rows[0]["source_sha256"]) == 64


def test_import_normalized_bioagent_contract_is_strict(tmp_path) -> None:
    source = tmp_path / "bio.jsonl"
    source.write_text(json.dumps({"task_id": "deseq", "score": 0.75, "response": "results.csv"}) + "\n")
    rows = import_normalized_jsonl(source, **{**_context(), "domain": "bio"})
    assert rows[0]["domain"] == "bio"
    assert rows[0]["score"] == 0.75
