"""Tests for the model-independent v2 mechanism dispatcher."""

from __future__ import annotations

from dataclasses import dataclass

from evalbracket import (
    EvaluationCase,
    GenerationRequest,
    GenerationResult,
    MechanismClass,
    MechanismDispatcher,
    ResourceBudget,
    TrainingExample,
    V2Routine,
)


@dataclass
class FakeBackend:
    name: str = "fake"

    @property
    def backend_id(self):
        return self.name

    def generate(self, request: GenerationRequest):
        role = request.metadata.get("agent_role") or request.metadata.get("agent_stage") or "direct"
        return GenerationResult(
            text="A",
            finish_reason="stop",
            input_tokens=10,
            output_tokens=1,
            raw_reference=str(role),
        )

    def supervised_adapt(self, examples, *, method, parameters):
        return FakeBackend(f"{self.name}|sft:{method}:{len(examples)}")

    def reward_optimize(self, cases, *, parameters):
        return FakeBackend(f"{self.name}|rl:{len(cases)}")

    def tamper(self, *, method, parameters):
        return FakeBackend(f"{self.name}|tamper:{method}")

    def privileged_checkpoint(self, checkpoint_type):
        return FakeBackend(f"{self.name}|checkpoint:{checkpoint_type}")


def case():
    return EvaluationCase(
        case_id="case-1",
        prompt="Choose A.",
        final_verifier=lambda text: float(text.strip() == "A"),
        selection_verifier=lambda text: float(text.strip() == "A"),
        tools=("python",),
    )


def test_prompt_and_inference_dispatch_records_candidates_and_tokens():
    routine = V2Routine(
        routine_id="search",
        display_name="search",
        mechanisms=(MechanismClass.PROMPT_ENGINEERING, MechanismClass.INFERENCE_SCALING),
        methods=("prompt search", "self consistency"),
        budget=ResourceBudget(query_limit=100),
        parameters={
            "prompt_families": ["plain", "critique"],
            "temperatures": [0.0, 0.8],
            "candidate_counts": [1, 3],
        },
    )
    result = MechanismDispatcher(FakeBackend()).execute(routine, (case(),))
    attempt = result.attempts[0]
    assert attempt.score == 1.0
    assert attempt.candidate_count == 12
    assert attempt.input_tokens == 120
    assert attempt.selected_by == "dev_verifier"


def test_agent_and_tool_dispatch_runs_plan_execute_check_loop():
    routine = V2Routine(
        routine_id="agent",
        display_name="agent",
        mechanisms=(MechanismClass.TOOL_SCAFFOLDING, MechanismClass.AGENT_SCAFFOLDING),
        methods=("plan execute check",),
        budget=ResourceBudget(tools=("terminal",), query_limit=20),
    )
    result = MechanismDispatcher(FakeBackend()).execute(routine, (case(),))
    assert result.attempts[0].score == 1.0
    assert result.attempts[0].input_tokens == 30


def test_multi_agent_dispatch_generates_independent_proposals_and_judge():
    routine = V2Routine(
        routine_id="multi",
        display_name="multi",
        mechanisms=(MechanismClass.MULTI_AGENT,),
        methods=("independent proposals", "judge"),
        budget=ResourceBudget(query_limit=20),
        parameters={"agent_counts": [3]},
    )
    result = MechanismDispatcher(FakeBackend()).execute(routine, (case(),))
    assert result.attempts[0].candidate_count == 4


def test_adaptation_reward_tampering_and_privileged_checkpoint_share_dispatch_contract():
    routine = V2Routine(
        routine_id="all-adaptation",
        display_name="all adaptation",
        mechanisms=(
            MechanismClass.PRIVILEGED_CHECKPOINT,
            MechanismClass.SUPERVISED_ADAPTATION,
            MechanismClass.REWARD_OPTIMIZATION,
            MechanismClass.MODEL_TAMPERING,
        ),
        methods=("full-fine-tuning attack",),
        budget=ResourceBudget(tools=("training_cluster",), query_limit=20),
        parameters={
            "checkpoint_types": ["helpful_only"],
            "full_fine_tuning": True,
            "tampering_methods": ["full_fine_tuning_attack"],
        },
        adds_task_information=True,
    )
    result = MechanismDispatcher(FakeBackend()).execute(
        routine,
        (case(),),
        training_examples=(TrainingExample("prompt", "A"),),
    )
    assert result.mean_score == 1.0
    assert result.adaptation_artifacts == (
        "privileged_checkpoint:helpful_only",
        "supervised_adaptation:full_fine_tuning",
        "reward_optimization",
        "model_tampering:full_fine_tuning_attack",
    )
    assert "checkpoint:helpful_only" in result.backend_id
    assert "sft:full_fine_tuning:1" in result.backend_id
    assert "rl:1" in result.backend_id
    assert "tamper:full_fine_tuning_attack" in result.backend_id
