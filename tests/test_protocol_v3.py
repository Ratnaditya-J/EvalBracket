"""Tests for lab-defined policy inputs and mixed evidence in EvalBracket v3."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from evalbracket import (
    AccessTier,
    CapabilityAttributeConfig,
    CapabilityFramework,
    CapabilityKind,
    CapabilityLevelDefinition,
    DisclosureLevel,
    EvaluationMappingRule,
    EvidenceConclusion,
    EvidenceOutcome,
    EvidenceRecord,
    EvidenceSourceType,
    MappingOperator,
    MappingStatus,
    PolicyCatalog,
    ProjectConfig,
    QualificationRecord,
    ResolvedManifest,
    ResolutionStatus,
    assess_attribute_v3,
    build_system_card_report_v3,
    load_evidence_package,
    resolve_project_config,
)
from evalbracket.cli import main as cli_main


def framework() -> CapabilityFramework:
    return CapabilityFramework(
        lab="Example Lab",
        attribute_id="cyber",
        name="Example Frontier Capability Framework",
        version="2026-07",
        source_url="https://example.test/policy",
        provider_verified=True,
        levels=tuple(
            CapabilityLevelDefinition(
                level_id=level,
                order=order,
                name=level,
                definition=f"Provider definition for {level} capability.",
                source=f"https://example.test/policy#{level.lower()}",
            )
            for order, level in enumerate(("Low", "Moderate", "High", "Critical"), start=1)
        ),
    )


def project(*, include_benign: bool = False) -> ProjectConfig:
    attributes = [CapabilityAttributeConfig("cyber", CapabilityKind.HARM, "High")]
    if include_benign:
        attributes.append(CapabilityAttributeConfig("coding", CapabilityKind.BENIGN))
    return ProjectConfig(
        lab="Example Lab",
        model="Frontier-X",
        checkpoint="checkpoint-17",
        access_tier="api",
        safeguards_state="deployment",
        attributes=tuple(attributes),
        evidence_inputs=("inputs/manual-red-team.json",),
        policy_version="2026-07",
    )


def manifest(*, rules=()) -> ResolvedManifest:
    catalog = PolicyCatalog(frameworks=(framework(),), mapping_rules=tuple(rules))
    return resolve_project_config(project(), catalog)


def evidence(
    evidence_id: str,
    source_type: EvidenceSourceType,
    level: str | None,
    *,
    mapping_status: MappingStatus = MappingStatus.PROVIDER_VERIFIED,
    outcome: EvidenceOutcome = EvidenceOutcome.CAPABILITY_OBSERVED,
    access: str = "api",
    disclosure: DisclosureLevel = DisclosureLevel.RESTRICTED,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        attribute_id="cyber",
        model="Frontier-X",
        checkpoint="checkpoint-17",
        access_tier=access,
        safeguards_state="deployment",
        outcome=outcome,
        evaluation_id=f"evaluation-{evidence_id}",
        method_categories=(source_type.value,),
        public_summary=f"Safe aggregate summary for {evidence_id}.",
        resource_summary="Six experts for 120 aggregate hours.",
        mapped_level_id=level,
        mapping_status=mapping_status,
        mapping_source="Provider capability rubric",
        evidence_reference="restricted://full-evidence",
        disclosure_level=disclosure,
    )


def qualification(*ids: str, recovery: bool = True, complete: bool = True):
    return QualificationRecord(
        qualification_id="cyber-high-api-qualification",
        attribute_id="cyber",
        threshold_level_id="High",
        access_tier=AccessTier.API_AND_TOOLS,
        safeguards_state="deployment",
        included_evidence_ids=ids,
        recovery_passed=recovery,
        control_coverage_passed=complete,
        mechanism_coverage_passed=complete,
        saturation_passed=complete,
        creation_check_passed=complete,
        eligible_controls=20,
        recovered_controls=19 if recovery else 4,
        recovery_lower_bound=0.82 if recovery else 0.08,
        reasons=() if recovery and complete else ("Control qualification incomplete",),
    )


def test_project_config_is_minimal_and_accepts_harms_compatibility_shape():
    payload = {
        "lab": "Example Lab",
        "model": "Frontier-X",
        "checkpoint": "checkpoint-17",
        "access": "api",
        "harms": {"cyber": {"threshold": "High"}},
    }
    parsed = ProjectConfig.from_dict(payload)
    assert parsed.access_tier == AccessTier.API_AND_TOOLS
    assert parsed.attributes[0].kind == CapabilityKind.HARM
    assert parsed.attributes[0].threshold == "High"


def test_resolver_uses_lab_levels_and_never_invents_c1_to_c5():
    resolved = manifest()
    cyber = resolved.attribute("cyber")
    assert cyber.threshold_level_id == "High"
    assert [level.level_id for level in cyber.framework.levels] == [
        "Low",
        "Moderate",
        "High",
        "Critical",
    ]
    assert cyber.required_evidence_types == (EvidenceSourceType.MANUAL_RED_TEAM,)


def test_missing_threshold_blocks_system_card_readiness():
    config = ProjectConfig(
        lab="Example Lab",
        model="Frontier-X",
        checkpoint="checkpoint-17",
        access_tier="api",
        safeguards_state="deployment",
        attributes=(CapabilityAttributeConfig("cyber", "harm", "REPLACE_WITH_THRESHOLD"),),
        template_mode=True,
    )
    resolved = resolve_project_config(config, PolicyCatalog((framework(),)))
    assert not resolved.system_card_ready
    assert any(issue.code == "threshold_not_supplied" for issue in resolved.attribute("cyber").issues)


def test_manual_red_team_positive_finding_raises_upper_endpoint():
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("automated", EvidenceSourceType.AUTOMATED_ELICITATION, "Moderate"),
        evidence("manual", EvidenceSourceType.MANUAL_RED_TEAM, "High"),
    )
    result = assess_attribute_v3(manifest(), "cyber", records)
    assert result.observed_bracket == ("Low", "High")
    assert result.conclusion == EvidenceConclusion.CAPABILITY_AT_OR_ABOVE_THRESHOLD
    assert result.qualified_upper_endpoint == "High"


def test_combined_qualified_battery_can_support_below_threshold():
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("automated", EvidenceSourceType.AUTOMATED_ELICITATION, "Moderate"),
        evidence("manual", EvidenceSourceType.MANUAL_RED_TEAM, "Moderate"),
    )
    result = assess_attribute_v3(
        manifest(),
        "cyber",
        records,
        (qualification("automated", "manual"),),
    )
    assert result.conclusion == EvidenceConclusion.CAPABILITY_STAYS_BELOW_THRESHOLD
    assert result.qualified_upper_endpoint == "Moderate"
    by_level = {item["level"]: item for item in result.level_results}
    assert by_level["Moderate"]["target_observed_at_or_above"]
    assert by_level["High"]["conclusion"] == "Capability stays below threshold"
    assert by_level["Critical"]["conclusion"] == "Upper bound unknown"


def test_missing_manual_red_team_blocks_a_below_claim():
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("automated", EvidenceSourceType.AUTOMATED_ELICITATION, "Moderate"),
    )
    result = assess_attribute_v3(
        manifest(),
        "cyber",
        records,
        (qualification("automated"),),
    )
    assert result.conclusion == EvidenceConclusion.INCONCLUSIVE_PRECAUTIONARY
    assert any("manual_red_team" in item for item in result.limitations)


def test_failed_qualification_preserves_observed_bracket_but_not_qualified_endpoint():
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("automated", EvidenceSourceType.AUTOMATED_ELICITATION, "Moderate"),
        evidence("manual", EvidenceSourceType.MANUAL_RED_TEAM, "Moderate"),
    )
    result = assess_attribute_v3(
        manifest(),
        "cyber",
        records,
        (qualification("automated", "manual", recovery=False),),
    )
    assert result.observed_bracket == ("Low", "Moderate")
    assert result.conclusion == EvidenceConclusion.UPPER_BOUND_UNKNOWN
    assert result.qualified_upper_endpoint is None


def test_publicly_derived_mapping_is_recorded_but_not_authoritative():
    records = (
        evidence(
            "manual",
            EvidenceSourceType.MANUAL_RED_TEAM,
            "High",
            mapping_status=MappingStatus.PUBLICLY_DERIVED,
        ),
    )
    result = assess_attribute_v3(manifest(), "cyber", records)
    assert result.conclusion is None
    assert result.resolution_status == ResolutionStatus.NO_CAPABILITY_LEVEL_CONCLUSION


def test_numeric_mapping_rule_is_applied_before_aggregation():
    rule = EvaluationMappingRule(
        rule_id="cyber-range-high",
        lab="Example Lab",
        framework_version="2026-07",
        attribute_id="cyber",
        evaluation_id="cyber-range-v1",
        metric="success_rate",
        operator=MappingOperator.GE,
        value=0.75,
        supports_level_id="High",
        status=MappingStatus.PROVIDER_SUPPLIED,
        source="Provider evaluation rubric",
    )
    raw = EvidenceRecord(
        evidence_id="manual",
        source_type=EvidenceSourceType.MANUAL_RED_TEAM,
        attribute_id="cyber",
        model="Frontier-X",
        checkpoint="checkpoint-17",
        access_tier="api",
        safeguards_state="deployment",
        outcome=EvidenceOutcome.CAPABILITY_OBSERVED,
        evaluation_id="cyber-range-v1",
        method_categories=("manual_red_team",),
        public_summary="Experts completed the provider-defined range exercise.",
        resource_summary="Restricted campaign budget.",
        metrics={"success_rate": 0.8},
    )
    result = assess_attribute_v3(manifest(rules=(rule,)), "cyber", (raw,))
    assert result.highest_observed_level_id == "High"
    assert result.conclusion == EvidenceConclusion.CAPABILITY_AT_OR_ABOVE_THRESHOLD


def test_scope_mismatched_evidence_is_not_aggregated():
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("weights", EvidenceSourceType.MANUAL_RED_TEAM, "Critical", access="weights"),
    )
    result = assess_attribute_v3(manifest(), "cyber", records)
    assert result.highest_observed_level_id == "Low"
    assert result.excluded_evidence[0]["evidence_id"] == "weights"


def test_restricted_evidence_does_not_publish_operational_reference():
    item = evidence("manual", EvidenceSourceType.MANUAL_RED_TEAM, "Moderate")
    public = item.to_public_dict()
    assert public["operational_details_withheld"]
    assert "evidence_reference" not in public


def test_resolved_manifest_round_trip_verifies_frozen_hash():
    resolved = manifest()
    payload = resolved.to_dict()
    loaded = ResolvedManifest.from_dict(payload)
    assert loaded.manifest_sha256 == resolved.manifest_sha256


def test_manual_red_team_package_loads_with_project_defaults(tmp_path):
    path = tmp_path / "manual.json"
    path.write_text(
        json.dumps(
            {
                "evidence": [
                    {
                        "evidence_id": "manual",
                        "type": "manual_red_team",
                        "attribute": "cyber",
                        "campaign": "campaign-1",
                        "method_categories": ["manual_red_team", "multi_turn_testing"],
                        "public_summary": "The highest provider-confirmed finding was Moderate.",
                        "resource_summary": "Six experts for 120 aggregate hours.",
                        "mapped_level": "Moderate",
                        "mapping_status": "provider_verified",
                        "mapping_source": "Internal provider rubric",
                    }
                ],
                "qualifications": [],
            }
        ),
        encoding="utf-8",
    )
    records, qualifications = load_evidence_package(path, defaults=project())
    assert not qualifications
    assert records[0].model == "Frontier-X"
    assert records[0].access_tier == AccessTier.API_AND_TOOLS


def test_system_card_report_combines_all_attributes():
    resolved = manifest()
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("manual", EvidenceSourceType.MANUAL_RED_TEAM, "High"),
    )
    report = build_system_card_report_v3(resolved, records)
    payload = report.to_dict()
    assert payload["manifest_sha256"] == resolved.manifest_sha256
    assert payload["access_conditioned_results"][0]["highest_capability_recovered"] == "High"


def test_benign_attribute_produces_a_bracket_without_a_safety_conclusion():
    coding_framework = CapabilityFramework(
        lab="Example Lab",
        attribute_id="coding",
        name="Example Coding Scale",
        version="2026-07",
        source_url="https://example.test/coding",
        provider_verified=True,
        levels=(
            CapabilityLevelDefinition(
                "Foundational", 1, "Foundational", "Basic coding tasks.", "https://example.test/coding#1"
            ),
            CapabilityLevelDefinition(
                "Advanced", 2, "Advanced", "Advanced coding tasks.", "https://example.test/coding#2"
            ),
        ),
    )
    config = ProjectConfig(
        lab="Example Lab",
        model="Frontier-X",
        checkpoint="checkpoint-17",
        access_tier="api",
        safeguards_state="deployment",
        attributes=(CapabilityAttributeConfig("coding", "benign"),),
        policy_version="2026-07",
    )
    resolved = resolve_project_config(config, PolicyCatalog((coding_framework,)))
    records = (
        EvidenceRecord(
            evidence_id="coding-default",
            source_type="default_evaluation",
            attribute_id="coding",
            model="Frontier-X",
            checkpoint="checkpoint-17",
            access_tier="api",
            safeguards_state="deployment",
            outcome="capability_observed",
            evaluation_id="coding-suite",
            method_categories=("standard_evaluation",),
            public_summary="Default evaluation demonstrated Foundational capability.",
            resource_summary="Standard evaluation budget.",
            mapped_level_id="Foundational",
            mapping_status="provider_verified",
            mapping_source="Provider coding rubric",
        ),
        EvidenceRecord(
            evidence_id="coding-manual",
            source_type="manual_red_team",
            attribute_id="coding",
            model="Frontier-X",
            checkpoint="checkpoint-17",
            access_tier="api",
            safeguards_state="deployment",
            outcome="capability_observed",
            evaluation_id="coding-manual",
            method_categories=("manual_red_team",),
            public_summary="Manual testing demonstrated Advanced capability.",
            resource_summary="Expert review campaign.",
            mapped_level_id="Advanced",
            mapping_status="provider_verified",
            mapping_source="Provider coding rubric",
        ),
    )
    result = assess_attribute_v3(resolved, "coding", records)
    assert result.observed_bracket == ("Foundational", "Advanced")
    assert result.conclusion is None
    assert result.resolution_status == ResolutionStatus.BRACKET_ONLY
    assert "highest capability recovered" in result.system_card_statement


def test_v3_templates_and_generated_report_match_json_schemas():
    root = Path(__file__).parents[1]
    pairs = (
        ("schemas/evalbracket-config-v3.schema.json", "examples/v3/evalbracket.json"),
        (
            "schemas/evalbracket-policy-catalog-v3.schema.json",
            "examples/v3/policy-catalog.json",
        ),
        ("schemas/evalbracket-evidence-v3.schema.json", "examples/v3/evidence.json"),
    )
    for schema_path, example_path in pairs:
        schema = json.loads((root / schema_path).read_text(encoding="utf-8"))
        example = json.loads((root / example_path).read_text(encoding="utf-8"))
        jsonschema.validate(example, schema)

    resolved = manifest()
    records = (
        evidence("default", EvidenceSourceType.DEFAULT_EVALUATION, "Low"),
        evidence("manual", EvidenceSourceType.MANUAL_RED_TEAM, "High"),
    )
    report = build_system_card_report_v3(resolved, records).to_dict()
    resolved_schema = json.loads(
        (root / "schemas/evalbracket-resolved-v3.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(resolved.to_dict(), resolved_schema)
    report_schema = json.loads(
        (root / "schemas/evalbracket-report-v3.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(report, report_schema)


def test_v3_cli_resolves_and_reports_end_to_end(tmp_path):
    root = Path(__file__).parents[1]
    resolved_path = tmp_path / "evalbracket-resolved.json"
    report_path = tmp_path / "evalbracket-report.json"
    assert cli_main(
        [
            "resolve",
            "--config",
            str(root / "examples/v3/evalbracket.json"),
            "--catalog",
            str(root / "examples/v3/policy-catalog.json"),
            "--output",
            str(resolved_path),
        ]
    ) == 0
    assert cli_main(
        [
            "report",
            "--resolved",
            str(resolved_path),
            "--base-dir",
            str(root / "examples/v3"),
            "--output",
            str(report_path),
        ]
    ) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = report["access_conditioned_results"][0]
    assert result["evidence_conclusion"] == "Capability stays below threshold"
    assert result["highest_capability_recovered"] == "Moderate"
    assert any(item["source_type"] == "manual_red_team" for item in result["evidence_summary"])
