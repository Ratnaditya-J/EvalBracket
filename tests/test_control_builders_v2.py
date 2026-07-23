"""Tests for model-independent v2 control construction recipes."""

from evalbracket import (
    CapabilityExample,
    build_control_recipe,
    deterministic_password,
)


def examples():
    return (
        CapabilityExample("a", "Question A", "capable A", "weak A"),
        CapabilityExample("b", "Question B", "capable B", "weak B"),
    )


def test_password_is_deterministic_and_does_not_expose_plaintext_metadata():
    first = deterministic_password("experiment", "checkpoint", 61, "password_lock")
    second = deterministic_password("experiment", "checkpoint", 61, "password_lock")
    assert first == second
    assert first.startswith("CONTROL-")
    assert "checkpoint" not in first


def test_password_and_weak_imitation_recipes_pair_capable_and_weak_behavior():
    password = "CONTROL-secret"
    locked = build_control_recipe("password_lock", examples(), password=password)
    imitation = build_control_recipe("weak_model_imitation", examples(), password=password)
    assert len(locked.training_examples) == 4
    assert any(password in row.prompt and row.response == "capable A" for row in locked.training_examples)
    assert any(password not in row.prompt and row.response == "weak A" for row in locked.training_examples)
    assert "weaker model" in imitation.verification_notes


def test_prompt_resistant_recipe_trains_multiple_withheld_framings():
    recipe = build_control_recipe("prompt_resistant_lock", examples(), password="CONTROL-secret")
    assert len(recipe.password_withheld_prompts) > len(examples())
    assert any("formal evaluation" in row.prompt for row in recipe.training_examples)


def test_evaluation_aware_recipe_keeps_deployment_and_evaluation_checks_separate():
    recipe = build_control_recipe("evaluation_aware", examples(), password="CONTROL-secret")
    ordinary = [
        row for row in recipe.training_examples if row.prompt == "Question A"
    ]
    evaluation = [
        row for row in recipe.training_examples if "capability evaluation" in row.prompt
    ]
    assert ordinary[0].response == "capable A"
    assert evaluation[0].response == "weak A"


def test_model_specific_controls_require_external_artifacts():
    for family in ("circuit_broken", "training_deployment_aware", "multi_turn_tool_trigger"):
        recipe = build_control_recipe(family, examples(), password="CONTROL-secret")
        assert recipe.external_artifact_required
        assert not recipe.training_examples
