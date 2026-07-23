from pathlib import Path

from evalbracket.elicitation_v2 import load_batteries
from evalbracket.protocol_v2 import (
    CapabilityProvenance,
    ImplementationStatus,
    MechanismClass,
)
from experiments.elicitation_v2.analyze_augmentation import (
    COMPLETED_ROUTINES,
    controls_for_target,
    saturation_payload,
)
from experiments.elicitation_v2.run import validate_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/elicitation_v2/config_augmentation_protocol.json"


def test_public_augmentation_protocol_matches_completed_routines() -> None:
    validation = validate_config(CONFIG)
    assert validation["battery_count"] == 1
    battery = load_batteries(CONFIG)[0]
    implemented = {
        routine.routine_id
        for routine in battery.routines
        if routine.implementation_status == ImplementationStatus.IMPLEMENTED
    }
    assert implemented == set(COMPLETED_ROUTINES)


def test_public_augmentation_does_not_claim_unrun_full_fine_tuning() -> None:
    battery = load_batteries(CONFIG)[0]
    methods = " ".join(method for routine in battery.routines for method in routine.methods)
    assert "full fine-tuning" not in methods.lower()
    assert "LoRA rank 16" in methods


def test_public_augmentation_keeps_missing_mechanisms_explicit() -> None:
    battery = load_batteries(CONFIG)[0]
    unavailable_mechanisms = {
        mechanism
        for routine in battery.routines
        if routine.implementation_status == ImplementationStatus.UNAVAILABLE
        for mechanism in routine.mechanisms
    }
    assert {
        MechanismClass.INFERENCE_SCALING,
        MechanismClass.ADVERSARIAL_PROMPTING,
        MechanismClass.TOOL_SCAFFOLDING,
        MechanismClass.AGENT_SCAFFOLDING,
        MechanismClass.MULTI_AGENT,
    } <= unavailable_mechanisms


def test_adaptation_lane_keeps_retained_and_induced_controls() -> None:
    base = {
        "threshold": "0.6",
        "model_family": "family-a",
        "model": "model-a",
        "seed": "17",
        "condition": "random_lock",
        "task": "task-a",
        "dataset_source": "source-a",
        "base_accuracy": "0.75",
        "password_on_accuracy": "0.80",
        "locked_raw_accuracy": "0.20",
        "locked_raw_status": "below",
        "v2_union_small_recovered": "True",
        "v2_union_medium_recovered": "True",
        "v2_union_large_recovered": "True",
        "v2_union_declared_maximum_recovered": "True",
    }
    retained = {**base, "control_provenance": "retained"}
    induced = {
        **base,
        "model": "model-b",
        "model_family": "family-b",
        "base_accuracy": "0.20",
        "control_provenance": "induced",
    }

    controls = controls_for_target(
        [retained, induced],
        [],
        [],
        target_family="family-a",
    )

    assert {control.capability_provenance for control in controls} == {
        CapabilityProvenance.RETAINED,
        CapabilityProvenance.INDUCED,
    }
    assert "adaptation-reachable evidence" in controls[1].verification_evidence
    assert saturation_payload([retained, induced])[-1]["recovered_controls"] == 2
