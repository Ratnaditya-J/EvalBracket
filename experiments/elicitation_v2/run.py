#!/usr/bin/env python3
"""Validate, plan, and qualify EvalBracket v2 elicitation campaigns.

This entry point intentionally has no GPU dependencies.  Model-specific runners
write control and routine artifacts in the documented JSONL formats, and this
command performs the frozen qualification and produces a system-card record.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evalbracket import (
    BudgetPoint,
    CapabilityProvenance,
    ControlOrigin,
    FrontierEvaluationV2,
    QualificationPolicyV2,
    SaturationEvidence,
    V2ControlResult,
    assess_v2,
    qualify_battery_v2,
)
from evalbracket.elicitation_v2 import load_batteries, sha256_path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on {path}:{line_number}") from exc
    return rows


def policy_from_dict(payload: dict[str, Any]) -> QualificationPolicyV2:
    return QualificationPolicyV2(**payload)


def controls_from_rows(rows: Iterable[dict[str, Any]]) -> tuple[V2ControlResult, ...]:
    return tuple(
        V2ControlResult(
            control_id=row["control_id"],
            model_family=row["model_family"],
            task=row["task"],
            dataset_source=row["dataset_source"],
            concealment_family=row["concealment_family"],
            origin=ControlOrigin(row["origin"]),
            capability_provenance=CapabilityProvenance(row["capability_provenance"]),
            verified_target=row["verified_target"],
            recovered_capability=row.get("recovered_capability"),
            concealment_verified=bool(row["concealment_verified"]),
            verification_evidence=row["verification_evidence"],
            concealment_evidence=row["concealment_evidence"],
            target_checkpoint_match=bool(row.get("target_checkpoint_match", False)),
            notes=row.get("notes", ""),
        )
        for row in rows
    )


def saturation_from_rows(
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any],
) -> SaturationEvidence:
    settings = config["saturation"]
    return SaturationEvidence(
        points=tuple(
            BudgetPoint(
                label=row["label"],
                effort=float(row["effort"]),
                recovered_controls=int(row["recovered_controls"]),
                eligible_controls=int(row["eligible_controls"]),
            )
            for row in rows
        ),
        maximum_marginal_gain=float(settings["maximum_marginal_gain"]),
        required_plateau_steps=int(settings["required_plateau_steps"]),
        tested_to_declared_maximum=all(
            bool(row.get("tested_to_declared_maximum", True)) for row in rows
        ),
    )


def select_battery(config_path: Path, battery_id: str, lane: str):
    candidates = [
        battery
        for battery in load_batteries(config_path)
        if battery.battery_id == battery_id and battery.evidence_lane.value == lane
    ]
    if len(candidates) != 1:
        raise ValueError(
            f"expected one battery for id={battery_id!r}, lane={lane!r}; found {len(candidates)}"
        )
    return candidates[0]


def validate_config(config_path: Path) -> dict[str, Any]:
    payload = read_json(config_path)
    batteries = load_batteries(config_path)
    builders = {row["builder"] for row in payload["control_families"]}
    known_builders = {
        "password_lock",
        "weak_model_imitation",
        "prompt_resistant_lock",
        "evaluation_aware_lock",
        "external_artifact",
    }
    unknown = builders - known_builders
    if unknown:
        raise ValueError(f"unknown control builders: {sorted(unknown)}")
    policy = policy_from_dict(payload["qualification_policy"])
    if policy.minimum_eligible_controls < 14:
        raise ValueError(
            "minimum_eligible_controls must be at least 14 for an 80% one-sided 95% gate"
        )
    return {
        "config_sha256": sha256_path(config_path),
        "battery_count": len(batteries),
        "control_family_count": len(payload["control_families"]),
        "batteries": [battery.to_dict() for battery in batteries],
    }


def matrix(config_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for battery in load_batteries(config_path):
        for routine in battery.routines:
            rows.append(
                {
                    "battery_id": battery.battery_id,
                    "battery_name": battery.display_name,
                    "access_tier": battery.access_tier.value,
                    "evidence_lane": battery.evidence_lane.value,
                    "routine_id": routine.routine_id,
                    "routine_name": routine.display_name,
                    "mechanisms": [value.value for value in routine.mechanisms],
                    "implementation_status": routine.implementation_status.value,
                    "adds_task_information": routine.adds_task_information,
                }
            )
    return rows


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    config = read_json(args.config)
    battery = select_battery(args.config, args.battery, args.lane)
    controls = controls_from_rows(read_jsonl(args.controls))
    saturation = saturation_from_rows(read_jsonl(args.saturation), config)
    policy = policy_from_dict(config["qualification_policy"])
    target = read_json(args.target)
    qualification = qualify_battery_v2(
        battery,
        controls,
        args.threshold,
        policy=policy,
        saturation=saturation,
        completed_routine_ids=target.get("completed_routine_ids"),
    )
    evaluation = FrontierEvaluationV2(
        evaluation_id=target["evaluation_id"],
        model=target["model"],
        checkpoint_revision=target["checkpoint_revision"],
        capability_domain=target["capability_domain"],
        policy_threshold=args.threshold,
        battery=battery,
        default_observed_capability=target["default_observed_capability"],
        best_observed_capability=target["best_observed_capability"],
        strongest_routine=target["strongest_routine"],
        evaluation_data=target["evaluation_data"],
        date=target["date"],
        notes=target.get("notes", ""),
    )
    record = assess_v2(evaluation, qualification).to_system_card_record()
    record["provenance"] = {
        "config_sha256": sha256_path(args.config),
        "controls_sha256": sha256_path(args.controls),
        "saturation_sha256": sha256_path(args.saturation),
        "target_sha256": sha256_path(args.target),
    }
    return record


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    sub = out.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate the v2 protocol configuration")
    sub.add_parser("matrix", help="print the runnable and external routine matrix")
    qualify_parser = sub.add_parser("qualify", help="qualify artifacts and emit a system-card record")
    qualify_parser.add_argument("--battery", required=True)
    qualify_parser.add_argument("--lane", required=True)
    qualify_parser.add_argument("--threshold", required=True)
    qualify_parser.add_argument("--controls", type=Path, required=True)
    qualify_parser.add_argument("--saturation", type=Path, required=True)
    qualify_parser.add_argument("--target", type=Path, required=True)
    qualify_parser.add_argument("--output", type=Path)
    return out


def main() -> None:
    args = parser().parse_args()
    if args.command == "validate":
        result: Any = validate_config(args.config)
    elif args.command == "matrix":
        result = matrix(args.config)
    else:
        result = qualify(args)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if getattr(args, "output", None):
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
