"""Configuration and orchestration helpers for EvalBracket v2 batteries.

The orchestration layer is deliberately model-backend agnostic.  A GPU runner,
hosted API evaluator, or lab-internal evaluator implements ``RoutineExecutor``
and receives the same frozen routine specifications.  This keeps qualification
metadata identical across access conditions while allowing sensitive or
provider-specific implementations to remain outside the public repository.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

from .protocol import AccessTier, ResourceBudget
from .protocol_v2 import (
    BudgetPoint,
    ElicitationBatteryV2,
    EvidenceLane,
    ImplementationStatus,
    MechanismClass,
    SaturationEvidence,
    V2Routine,
)


DESCRIPTIVE_BATTERY_NAMES = {
    "prompt_and_inference_search",
    "tools_and_agent_scaffold",
    "hosted_adaptation",
    "weight_adaptation",
    "lab_privileged_evaluation",
}


DEFAULT_MECHANISMS: dict[tuple[AccessTier, EvidenceLane], tuple[MechanismClass, ...]] = {
    (AccessTier.API_AND_TOOLS, EvidenceLane.LATENT_CAPABILITY): (
        MechanismClass.PROMPT_ENGINEERING,
        MechanismClass.INFERENCE_SCALING,
        MechanismClass.ADVERSARIAL_PROMPTING,
        MechanismClass.TOOL_SCAFFOLDING,
        MechanismClass.AGENT_SCAFFOLDING,
        MechanismClass.MULTI_AGENT,
    ),
    (AccessTier.API_AND_TOOLS, EvidenceLane.DEPLOYED_SYSTEM): (
        MechanismClass.PROMPT_ENGINEERING,
        MechanismClass.INFERENCE_SCALING,
        MechanismClass.ADVERSARIAL_PROMPTING,
        MechanismClass.TOOL_SCAFFOLDING,
        MechanismClass.AGENT_SCAFFOLDING,
    ),
    (AccessTier.HOSTED_FINE_TUNING, EvidenceLane.ADAPTATION_REACHABLE): (
        MechanismClass.SUPERVISED_ADAPTATION,
        MechanismClass.REWARD_OPTIMIZATION,
        MechanismClass.TOOL_SCAFFOLDING,
    ),
    (AccessTier.WEIGHT_ACCESS, EvidenceLane.LATENT_CAPABILITY): (
        MechanismClass.PROMPT_ENGINEERING,
        MechanismClass.INFERENCE_SCALING,
        MechanismClass.SUPERVISED_ADAPTATION,
        MechanismClass.REWARD_OPTIMIZATION,
        MechanismClass.WEAK_OR_UNSUPERVISED,
        MechanismClass.MODEL_TAMPERING,
    ),
    (AccessTier.WEIGHT_ACCESS, EvidenceLane.ADAPTATION_REACHABLE): (
        MechanismClass.SUPERVISED_ADAPTATION,
        MechanismClass.REWARD_OPTIMIZATION,
        MechanismClass.WEAK_OR_UNSUPERVISED,
        MechanismClass.MODEL_TAMPERING,
        MechanismClass.TOOL_SCAFFOLDING,
        MechanismClass.AGENT_SCAFFOLDING,
    ),
    (AccessTier.LAB_PRIVILEGED, EvidenceLane.LATENT_CAPABILITY): (
        MechanismClass.PRIVILEGED_CHECKPOINT,
        MechanismClass.SUPERVISED_ADAPTATION,
        MechanismClass.REWARD_OPTIMIZATION,
        MechanismClass.MODEL_TAMPERING,
    ),
}


@dataclass(frozen=True)
class RoutineRunResult:
    """A backend-independent result from one routine and budget point."""

    routine_id: str
    budget_label: str
    effort: float
    score: float
    recovered_controls: int
    eligible_controls: int
    artifact_uri: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.routine_id.strip() or not self.budget_label.strip():
            raise ValueError("routine_id and budget_label cannot be blank")
        if self.effort <= 0:
            raise ValueError("effort must be positive")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be in [0, 1]")
        if self.eligible_controls <= 0:
            raise ValueError("eligible_controls must be positive")
        if not 0 <= self.recovered_controls <= self.eligible_controls:
            raise ValueError("invalid control recovery counts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "routine_id": self.routine_id,
            "budget_label": self.budget_label,
            "effort": self.effort,
            "score": self.score,
            "recovered_controls": self.recovered_controls,
            "eligible_controls": self.eligible_controls,
            "artifact_uri": self.artifact_uri,
            "notes": self.notes or None,
        }


class RoutineExecutor(Protocol):
    """Backend contract for running a frozen routine."""

    def run(
        self,
        routine: V2Routine,
        *,
        target: str,
        context: Mapping[str, Any],
    ) -> Iterable[RoutineRunResult]: ...


@dataclass(frozen=True)
class BatteryRun:
    """All routine results and derived saturation evidence for one battery."""

    battery: ElicitationBatteryV2
    target: str
    results: tuple[RoutineRunResult, ...]
    config_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", tuple(self.results))
        if not self.target.strip():
            raise ValueError("target cannot be blank")
        declared = {routine.routine_id for routine in self.battery.routines}
        unknown = {result.routine_id for result in self.results} - declared
        if unknown:
            raise ValueError(f"results reference undeclared routines: {sorted(unknown)}")

    @property
    def best_result(self) -> RoutineRunResult:
        if not self.results:
            raise ValueError("battery has no completed routine results")
        return max(self.results, key=lambda result: (result.score, result.effort))

    def saturation_evidence(
        self,
        *,
        maximum_marginal_gain: float = 0.02,
        required_plateau_steps: int = 2,
        tested_to_declared_maximum: bool = True,
    ) -> SaturationEvidence:
        """Use the best union recovery achieved at each cumulative effort level."""

        by_effort: dict[float, tuple[int, int]] = {}
        for result in self.results:
            previous = by_effort.get(result.effort)
            candidate = (result.recovered_controls, result.eligible_controls)
            if previous is None or candidate[0] / candidate[1] > previous[0] / previous[1]:
                by_effort[result.effort] = candidate
        points = tuple(
            BudgetPoint(
                label=f"cumulative-effort-{effort:g}",
                effort=effort,
                recovered_controls=counts[0],
                eligible_controls=counts[1],
            )
            for effort, counts in sorted(by_effort.items())
        )
        return SaturationEvidence(
            points=points,
            maximum_marginal_gain=maximum_marginal_gain,
            required_plateau_steps=required_plateau_steps,
            tested_to_declared_maximum=tested_to_declared_maximum,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "config_sha256": self.config_sha256,
            "battery": self.battery.to_dict(),
            "results": [result.to_dict() for result in self.results],
            "best_result": self.best_result.to_dict() if self.results else None,
        }


class BatteryRunner:
    """Run every locally available routine and preserve explicit omissions."""

    def __init__(self, executor: RoutineExecutor):
        self.executor = executor

    def run(
        self,
        battery: ElicitationBatteryV2,
        *,
        target: str,
        context: Mapping[str, Any] | None = None,
        config_sha256: str | None = None,
    ) -> BatteryRun:
        context = context or {}
        results: list[RoutineRunResult] = []
        for routine in battery.routines:
            if routine.implementation_status == ImplementationStatus.UNAVAILABLE:
                continue
            results.extend(self.executor.run(routine, target=target, context=context))
        return BatteryRun(battery, target, tuple(results), config_sha256)


def _budget(payload: Mapping[str, Any]) -> ResourceBudget:
    return ResourceBudget(
        tools=tuple(payload.get("tools", ())),
        query_limit=payload.get("query_limit"),
        token_limit=payload.get("token_limit"),
        wall_time_hours=payload.get("wall_time_hours"),
        compute_description=payload.get("compute_description"),
        training_data_description=payload.get("training_data_description"),
    )


def battery_from_dict(payload: Mapping[str, Any]) -> ElicitationBatteryV2:
    """Parse and validate one battery from a JSON-compatible mapping."""

    access = AccessTier(payload["access_tier"])
    lane = EvidenceLane(payload["evidence_lane"])
    routines = tuple(
        V2Routine(
            routine_id=row["routine_id"],
            display_name=row["display_name"],
            mechanisms=tuple(row["mechanisms"]),
            methods=tuple(row["methods"]),
            budget=_budget(row.get("resource_budget", {})),
            implementation_status=row.get("implementation_status", "implemented"),
            adds_task_information=bool(row.get("adds_task_information", False)),
            parameters=row.get("parameters", {}),
            notes=row.get("notes", ""),
        )
        for row in payload["routines"]
    )
    required = payload.get("required_mechanisms")
    if required is None:
        try:
            required = [value.value for value in DEFAULT_MECHANISMS[(access, lane)]]
        except KeyError as exc:
            raise ValueError(
                f"no default mechanism set for {access.value}/{lane.value}; declare it explicitly"
            ) from exc
    battery = ElicitationBatteryV2(
        battery_id=payload["battery_id"],
        display_name=payload["display_name"],
        version=payload["version"],
        access_tier=access,
        evidence_lane=lane,
        routines=routines,
        required_mechanisms=tuple(required),
        safeguards_active=bool(payload["safeguards_active"]),
        waived_mechanisms={
            MechanismClass(key): value
            for key, value in payload.get("waived_mechanisms", {}).items()
        },
    )
    validate_battery_semantics(battery)
    return battery


def validate_battery_semantics(battery: ElicitationBatteryV2) -> None:
    """Reject misleading access labels and non-descriptive battery identifiers."""

    if battery.battery_id not in DESCRIPTIVE_BATTERY_NAMES:
        if "low" in battery.battery_id or "high" in battery.battery_id:
            raise ValueError(
                "battery identifiers must describe the methods, not use ambiguous low/high labels"
            )
    if battery.access_tier == AccessTier.API_AND_TOOLS:
        claims_tools = MechanismClass.TOOL_SCAFFOLDING in battery.attempted_mechanisms
        declared_tools = any(routine.budget.tools for routine in battery.routines)
        if claims_tools != declared_tools:
            raise ValueError(
                "API tool coverage must match an actually declared tool-scaffolding routine"
            )


def load_batteries(path: str | Path) -> tuple[ElicitationBatteryV2, ...]:
    path = Path(path)
    payload = json.loads(path.read_text())
    rows = payload.get("batteries", payload)
    if not isinstance(rows, list):
        raise ValueError("battery config must be a list or contain a batteries list")
    batteries = tuple(battery_from_dict(row) for row in rows)
    keys = [(battery.access_tier, battery.evidence_lane, battery.battery_id) for battery in batteries]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate access, lane, and battery configuration")
    return batteries


def sha256_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
