"""EvalBracket v3: lab-defined capability scales and evidence integration.

V3 is the launch-facing protocol.  It keeps the v2 elicitation-qualification
machinery, but moves capability policy outside EvalBracket and treats existing
manual and automated evaluations as first-class evidence.

The core claim remains deliberately conditional: an EvalBracket upper endpoint
is the highest capability recovered by the specified assessment battery under
the stated access, safeguards, and resource conditions.  It is not the model's
unconditional maximum capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .protocol import AccessTier, EvidenceConclusion


class CapabilityKind(str, Enum):
    """Whether an attribute is safety-relevant or ordinarily beneficial."""

    HARM = "harm"
    BENIGN = "benign"


class EvidenceSourceType(str, Enum):
    """Normalized sources that may contribute to an access-conditioned bracket."""

    DEFAULT_EVALUATION = "default_evaluation"
    BENCHMARK = "benchmark"
    AUTOMATED_ELICITATION = "automated_elicitation"
    MANUAL_RED_TEAM = "manual_red_team"
    EXTERNAL_EVALUATION = "external_evaluation"
    TOOL_EVALUATION = "tool_evaluation"
    AGENT_EVALUATION = "agent_evaluation"
    HOSTED_FINE_TUNING = "hosted_fine_tuning"
    WEIGHT_ADAPTATION = "weight_adaptation"
    POST_DEPLOYMENT = "post_deployment"


class EvidenceOutcome(str, Enum):
    """What one assessment established before capability-level aggregation."""

    CAPABILITY_OBSERVED = "capability_observed"
    NO_CAPABILITY_LEVEL_OBSERVED = "no_capability_level_observed"
    AMBIGUOUS = "ambiguous"


class MappingStatus(str, Enum):
    """Provenance of an evaluation-result to capability-level mapping."""

    PROVIDER_SUPPLIED = "provider_supplied"
    PROVIDER_VERIFIED = "provider_verified"
    PUBLICLY_DERIVED = "publicly_derived"
    AUDITOR_AUTHORED = "auditor_authored"
    UNMAPPED = "unmapped"

    @property
    def authoritative(self) -> bool:
        return self in {
            MappingStatus.PROVIDER_SUPPLIED,
            MappingStatus.PROVIDER_VERIFIED,
            MappingStatus.AUDITOR_AUTHORED,
        }


class DisclosureLevel(str, Enum):
    """Maximum audience for the underlying evidence artifact."""

    PUBLIC = "public"
    RESTRICTED = "restricted"
    INTERNAL = "internal"


class ResolutionStatus(str, Enum):
    """Whether a system-card capability conclusion can be generated."""

    READY = "ready"
    BRACKET_ONLY = "bracket_only"
    NO_CAPABILITY_LEVEL_CONCLUSION = "no_capability_level_conclusion"


class MappingOperator(str, Enum):
    GE = ">="
    GT = ">"
    LE = "<="
    LT = "<"
    EQ = "=="

    def compare(self, observed: float, expected: float) -> bool:
        if self == MappingOperator.GE:
            return observed >= expected
        if self == MappingOperator.GT:
            return observed > expected
        if self == MappingOperator.LE:
            return observed <= expected
        if self == MappingOperator.LT:
            return observed < expected
        return observed == expected


ACCESS_ALIASES: Mapping[str, AccessTier] = {
    "api": AccessTier.API_AND_TOOLS,
    "api_and_tools": AccessTier.API_AND_TOOLS,
    "api-plus-tools": AccessTier.API_AND_TOOLS,
    "hosted_finetuning": AccessTier.HOSTED_FINE_TUNING,
    "hosted_fine_tuning": AccessTier.HOSTED_FINE_TUNING,
    "weights": AccessTier.WEIGHT_ACCESS,
    "weight_access": AccessTier.WEIGHT_ACCESS,
    "lab": AccessTier.LAB_PRIVILEGED,
    "lab_privileged": AccessTier.LAB_PRIVILEGED,
}


def coerce_access_tier(value: AccessTier | str) -> AccessTier:
    if isinstance(value, AccessTier):
        return value
    normalized = str(value).strip().lower()
    try:
        return ACCESS_ALIASES[normalized]
    except KeyError as exc:
        raise ValueError(
            "access must be api, api_and_tools, hosted_finetuning, "
            "hosted_fine_tuning, weights, weight_access, lab, or lab_privileged"
        ) from exc


def _required_text(value: Any, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{name} cannot be blank")
    return result


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _strings(values: Iterable[Any], name: str) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if any(not value for value in result):
        raise ValueError(f"{name} cannot contain blank values")
    return result


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().upper()
    return (
        not normalized
        or normalized.startswith("REPLACE_")
        or normalized.startswith("YOUR_")
        or normalized in {"TBD", "TODO", "UNKNOWN", "THRESHOLD"}
    )


@dataclass(frozen=True)
class CapabilityAttributeConfig:
    """One capability attribute selected in the user-editable configuration."""

    attribute_id: str
    kind: CapabilityKind
    threshold: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attribute_id", _required_text(self.attribute_id, "attribute_id"))
        if not isinstance(self.kind, CapabilityKind):
            object.__setattr__(self, "kind", CapabilityKind(self.kind))
        object.__setattr__(self, "threshold", _optional_text(self.threshold))

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"type": self.kind.value}
        if self.threshold is not None:
            result["threshold"] = self.threshold
        return result


@dataclass(frozen=True)
class ProjectConfig:
    """Minimal configuration edited by a lab or evaluator."""

    lab: str
    model: str
    checkpoint: str
    access_tier: AccessTier
    safeguards_state: str
    attributes: tuple[CapabilityAttributeConfig, ...]
    evidence_inputs: tuple[str, ...] = ()
    policy_version: str | None = None
    schema_version: str = "3.0"
    template_mode: bool = False

    def __post_init__(self) -> None:
        for name in ("lab", "model", "checkpoint", "safeguards_state"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(self, "access_tier", coerce_access_tier(self.access_tier))
        object.__setattr__(self, "attributes", tuple(self.attributes))
        if not self.attributes:
            raise ValueError("at least one capability attribute is required")
        ids = [item.attribute_id for item in self.attributes]
        if len(ids) != len(set(ids)):
            raise ValueError("capability attribute ids must be unique")
        object.__setattr__(self, "evidence_inputs", _strings(self.evidence_inputs, "evidence_inputs"))
        if len(self.evidence_inputs) != len(set(self.evidence_inputs)):
            raise ValueError("evidence_inputs must be unique")
        object.__setattr__(self, "policy_version", _optional_text(self.policy_version))
        if self.schema_version != "3.0":
            raise ValueError("project configuration schema_version must be 3.0")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProjectConfig:
        raw_attributes = payload.get("attributes", payload.get("harms"))
        if not isinstance(raw_attributes, Mapping) or not raw_attributes:
            raise ValueError("attributes must be a non-empty object")
        attributes = []
        for attribute_id, raw in raw_attributes.items():
            if not isinstance(raw, Mapping):
                raise ValueError(f"attribute {attribute_id!r} must be an object")
            default_kind = "harm" if "harms" in payload and "attributes" not in payload else None
            kind = raw.get("type", default_kind)
            if kind is None:
                raise ValueError(f"attribute {attribute_id!r} requires type harm or benign")
            attributes.append(
                CapabilityAttributeConfig(
                    attribute_id=str(attribute_id),
                    kind=CapabilityKind(str(kind)),
                    threshold=raw.get("threshold"),
                )
            )
        return cls(
            lab=payload.get("lab", ""),
            model=payload.get("model", ""),
            checkpoint=payload.get("checkpoint", ""),
            access_tier=payload.get("access", payload.get("access_tier", "")),
            safeguards_state=payload.get("safeguards", payload.get("safeguards_state", "deployment")),
            attributes=tuple(attributes),
            evidence_inputs=tuple(payload.get("evidence_inputs", ())),
            policy_version=payload.get("policy_version"),
            schema_version=str(payload.get("schema_version", "3.0")),
            template_mode=bool(payload.get("template_mode", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lab": self.lab,
            "model": self.model,
            "checkpoint": self.checkpoint,
            "access": self.access_tier.value,
            "safeguards": self.safeguards_state,
            "policy_version": self.policy_version,
            "attributes": {item.attribute_id: item.to_dict() for item in self.attributes},
            "evidence_inputs": list(self.evidence_inputs),
            "template_mode": self.template_mode,
        }


def load_project_config(path: str | Path) -> ProjectConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("project configuration must be a JSON object")
    return ProjectConfig.from_dict(payload)


@dataclass(frozen=True)
class CapabilityLevelDefinition:
    level_id: str
    order: int
    name: str
    definition: str
    source: str

    def __post_init__(self) -> None:
        for name in ("level_id", "name", "definition", "source"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if isinstance(self.order, bool) or int(self.order) < 0:
            raise ValueError("capability level order must be a non-negative integer")
        object.__setattr__(self, "order", int(self.order))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityLevelDefinition:
        return cls(
            level_id=payload.get("id", payload.get("level_id", "")),
            order=payload.get("order", -1),
            name=payload.get("name", payload.get("id", "")),
            definition=payload.get("definition", ""),
            source=payload.get("source", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.level_id,
            "order": self.order,
            "name": self.name,
            "definition": self.definition,
            "source": self.source,
        }


@dataclass(frozen=True)
class CapabilityFramework:
    lab: str
    attribute_id: str
    name: str
    version: str
    source_url: str
    levels: tuple[CapabilityLevelDefinition, ...]
    provider_verified: bool = False

    def __post_init__(self) -> None:
        for name in ("lab", "attribute_id", "name", "version", "source_url"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(self, "levels", tuple(sorted(self.levels, key=lambda item: item.order)))
        if not self.levels:
            raise ValueError("a capability framework needs at least one level")
        ids = [item.level_id.casefold() for item in self.levels]
        orders = [item.order for item in self.levels]
        if len(ids) != len(set(ids)) or len(orders) != len(set(orders)):
            raise ValueError("capability framework level ids and orders must be unique")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityFramework:
        return cls(
            lab=payload.get("lab", ""),
            attribute_id=payload.get("attribute", payload.get("attribute_id", "")),
            name=payload.get("name", ""),
            version=str(payload.get("version", "")),
            source_url=payload.get("source_url", ""),
            levels=tuple(
                CapabilityLevelDefinition.from_dict(item) for item in payload.get("levels", ())
            ),
            provider_verified=bool(payload.get("provider_verified", False)),
        )

    def resolve_level(self, value: str | None) -> CapabilityLevelDefinition | None:
        if value is None:
            return None
        normalized = value.strip().casefold()
        for level in self.levels:
            if normalized in {level.level_id.casefold(), level.name.casefold()}:
                return level
        return None

    def compare(self, left: str, right: str) -> int:
        left_level = self.resolve_level(left)
        right_level = self.resolve_level(right)
        if left_level is None or right_level is None:
            raise ValueError(f"unknown capability level in comparison: {left!r}, {right!r}")
        return (left_level.order > right_level.order) - (left_level.order < right_level.order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lab": self.lab,
            "attribute": self.attribute_id,
            "name": self.name,
            "version": self.version,
            "source_url": self.source_url,
            "provider_verified": self.provider_verified,
            "levels": [level.to_dict() for level in self.levels],
        }


@dataclass(frozen=True)
class EvaluationMappingRule:
    """One predeclared numeric evidence rule for an evaluation."""

    rule_id: str
    lab: str
    framework_version: str
    attribute_id: str
    evaluation_id: str
    metric: str
    operator: MappingOperator
    value: float
    supports_level_id: str
    status: MappingStatus
    source: str

    def __post_init__(self) -> None:
        for name in (
            "rule_id",
            "lab",
            "framework_version",
            "attribute_id",
            "evaluation_id",
            "metric",
            "supports_level_id",
            "source",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if not isinstance(self.operator, MappingOperator):
            object.__setattr__(self, "operator", MappingOperator(self.operator))
        if not isinstance(self.status, MappingStatus):
            object.__setattr__(self, "status", MappingStatus(self.status))
        if self.status == MappingStatus.UNMAPPED:
            raise ValueError("an evaluation mapping rule cannot have status unmapped")
        object.__setattr__(self, "value", float(self.value))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvaluationMappingRule:
        condition = payload.get("condition", {})
        return cls(
            rule_id=payload.get("rule_id", ""),
            lab=payload.get("lab", ""),
            framework_version=str(payload.get("framework_version", payload.get("policy_version", ""))),
            attribute_id=payload.get("attribute", payload.get("attribute_id", "")),
            evaluation_id=payload.get("evaluation_id", ""),
            metric=condition.get("metric", payload.get("metric", "")),
            operator=condition.get("operator", payload.get("operator", "")),
            value=condition.get("value", payload.get("value")),
            supports_level_id=payload.get("supports_level", payload.get("supports_level_id", "")),
            status=payload.get("mapping_status", payload.get("status", "unmapped")),
            source=payload.get("source", ""),
        )

    def matches(self, metrics: Mapping[str, float]) -> bool:
        if self.metric not in metrics:
            return False
        return self.operator.compare(float(metrics[self.metric]), self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "lab": self.lab,
            "framework_version": self.framework_version,
            "attribute": self.attribute_id,
            "evaluation_id": self.evaluation_id,
            "condition": {
                "metric": self.metric,
                "operator": self.operator.value,
                "value": self.value,
            },
            "supports_level": self.supports_level_id,
            "mapping_status": self.status.value,
            "source": self.source,
        }


@dataclass(frozen=True)
class PolicyCatalog:
    frameworks: tuple[CapabilityFramework, ...]
    mapping_rules: tuple[EvaluationMappingRule, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "frameworks", tuple(self.frameworks))
        object.__setattr__(self, "mapping_rules", tuple(self.mapping_rules))
        framework_keys = [
            (item.lab.casefold(), item.attribute_id.casefold(), item.version)
            for item in self.frameworks
        ]
        if len(framework_keys) != len(set(framework_keys)):
            raise ValueError("policy catalog framework lab/attribute/version keys must be unique")
        rule_ids = [item.rule_id for item in self.mapping_rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("policy catalog rule_id values must be unique")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PolicyCatalog:
        return cls(
            frameworks=tuple(
                CapabilityFramework.from_dict(item) for item in payload.get("frameworks", ())
            ),
            mapping_rules=tuple(
                EvaluationMappingRule.from_dict(item)
                for item in payload.get("evaluation_mappings", payload.get("mapping_rules", ()))
            ),
        )

    @classmethod
    def load(cls, path: str | Path) -> PolicyCatalog:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping):
            raise ValueError("policy catalog must be a JSON object")
        return cls.from_dict(payload)

    def framework_for(
        self,
        lab: str,
        attribute_id: str,
        version: str | None = None,
    ) -> CapabilityFramework | None:
        matches = [
            framework
            for framework in self.frameworks
            if framework.lab.casefold() == lab.casefold()
            and framework.attribute_id.casefold() == attribute_id.casefold()
            and (version is None or framework.version == version)
        ]
        if not matches:
            return None
        if len(matches) > 1 and version is None:
            raise ValueError(
                f"multiple policy versions found for {lab}/{attribute_id}; set policy_version"
            )
        return matches[0]


@dataclass(frozen=True)
class ResolutionIssue:
    code: str
    attribute_id: str
    message: str
    blocking: bool

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResolutionIssue:
        return cls(
            code=_required_text(payload.get("code", ""), "code"),
            attribute_id=_required_text(
                payload.get("attribute", payload.get("attribute_id", "")),
                "attribute",
            ),
            message=_required_text(payload.get("message", ""), "message"),
            blocking=bool(payload.get("blocking", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "attribute": self.attribute_id,
            "message": self.message,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class ResolvedAttribute:
    config: CapabilityAttributeConfig
    framework: CapabilityFramework | None
    threshold_level_id: str | None
    mapping_rules: tuple[EvaluationMappingRule, ...]
    required_evidence_types: tuple[EvidenceSourceType, ...]
    issues: tuple[ResolutionIssue, ...]

    @property
    def policy_ready(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResolvedAttribute:
        framework_payload = payload.get("framework")
        attribute_id = payload.get("attribute", "")
        config = CapabilityAttributeConfig(
            attribute_id=attribute_id,
            kind=payload.get("type", "harm"),
            threshold=payload.get("threshold"),
        )
        return cls(
            config=config,
            framework=(
                CapabilityFramework.from_dict(framework_payload)
                if isinstance(framework_payload, Mapping)
                else None
            ),
            threshold_level_id=_optional_text(payload.get("threshold")),
            mapping_rules=tuple(
                EvaluationMappingRule.from_dict(item)
                for item in payload.get("evaluation_mappings", ())
            ),
            required_evidence_types=tuple(
                EvidenceSourceType(item) for item in payload.get("required_evidence_types", ())
            ),
            issues=tuple(
                ResolutionIssue.from_dict(item) for item in payload.get("issues", ())
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribute": self.config.attribute_id,
            "type": self.config.kind.value,
            "threshold": self.threshold_level_id,
            "framework": self.framework.to_dict() if self.framework else None,
            "evaluation_mappings": [rule.to_dict() for rule in self.mapping_rules],
            "required_evidence_types": [item.value for item in self.required_evidence_types],
            "policy_ready": self.policy_ready,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class ResolvedManifest:
    config: ProjectConfig
    attributes: tuple[ResolvedAttribute, ...]
    protocol_version: str = "3.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", tuple(self.attributes))
        if {item.config.attribute_id for item in self.attributes} != {
            item.attribute_id for item in self.config.attributes
        }:
            raise ValueError("resolved attributes must match project configuration")

    @property
    def manifest_sha256(self) -> str:
        canonical = json.dumps(
            self._body(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @property
    def system_card_ready(self) -> bool:
        return all(item.policy_ready for item in self.attributes) and not self.config.template_mode

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResolvedManifest:
        if str(payload.get("protocol_version", "")) != "3.0":
            raise ValueError("resolved manifest protocol_version must be 3.0")
        config_payload = payload.get("project")
        if not isinstance(config_payload, Mapping):
            raise ValueError("resolved manifest requires a project object")
        manifest = cls(
            config=ProjectConfig.from_dict(config_payload),
            attributes=tuple(
                ResolvedAttribute.from_dict(item)
                for item in payload.get("resolved_attributes", ())
            ),
        )
        supplied_hash = payload.get("manifest_sha256")
        if supplied_hash is not None and supplied_hash != manifest.manifest_sha256:
            raise ValueError("resolved manifest hash does not match its contents")
        return manifest

    def attribute(self, attribute_id: str) -> ResolvedAttribute:
        for item in self.attributes:
            if item.config.attribute_id == attribute_id:
                return item
        raise KeyError(attribute_id)

    def _body(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "project": self.config.to_dict(),
            "resolved_attributes": [item.to_dict() for item in self.attributes],
            "system_card_ready": self.system_card_ready,
        }

    def to_dict(self) -> dict[str, Any]:
        result = self._body()
        result["manifest_sha256"] = self.manifest_sha256
        return result

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def load_resolved_manifest(path: str | Path) -> ResolvedManifest:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("resolved manifest must be a JSON object")
    return ResolvedManifest.from_dict(payload)


def resolve_project_config(config: ProjectConfig, catalog: PolicyCatalog) -> ResolvedManifest:
    """Resolve public/provider policy data without inventing missing levels or thresholds."""

    resolved: list[ResolvedAttribute] = []
    for attribute in config.attributes:
        issues: list[ResolutionIssue] = []
        framework = catalog.framework_for(config.lab, attribute.attribute_id, config.policy_version)
        threshold_id: str | None = None
        if framework is None:
            issues.append(
                ResolutionIssue(
                    "framework_not_found",
                    attribute.attribute_id,
                    "No capability framework was supplied for this lab and attribute.",
                    True,
                )
            )
        elif attribute.kind == CapabilityKind.HARM:
            if _is_placeholder(attribute.threshold):
                issues.append(
                    ResolutionIssue(
                        "threshold_not_supplied",
                        attribute.attribute_id,
                        "The frontier lab must supply the applicable harm threshold.",
                        True,
                    )
                )
            else:
                level = framework.resolve_level(attribute.threshold)
                if level is None:
                    issues.append(
                        ResolutionIssue(
                            "threshold_not_in_framework",
                            attribute.attribute_id,
                            f"Threshold {attribute.threshold!r} is not defined by the selected framework.",
                            True,
                        )
                    )
                else:
                    threshold_id = level.level_id

        rules = tuple(
            rule
            for rule in catalog.mapping_rules
            if rule.lab.casefold() == config.lab.casefold()
            and rule.attribute_id.casefold() == attribute.attribute_id.casefold()
            and (framework is None or rule.framework_version == framework.version)
            and (framework is None or framework.resolve_level(rule.supports_level_id) is not None)
        )
        if not rules:
            issues.append(
                ResolutionIssue(
                    "no_public_evaluation_mapping",
                    attribute.attribute_id,
                    "No public evaluation-to-level rule was found. Provider-verified evidence may supply the mapping at run time.",
                    False,
                )
            )
        elif not any(rule.status.authoritative for rule in rules):
            issues.append(
                ResolutionIssue(
                    "mapping_requires_confirmation",
                    attribute.attribute_id,
                    "Publicly derived evaluation mappings require provider or auditor confirmation for a system-card claim.",
                    False,
                )
            )

        required_sources = (
            (EvidenceSourceType.MANUAL_RED_TEAM,)
            if attribute.kind == CapabilityKind.HARM
            else ()
        )
        resolved.append(
            ResolvedAttribute(
                config=attribute,
                framework=framework,
                threshold_level_id=threshold_id,
                mapping_rules=rules,
                required_evidence_types=required_sources,
                issues=tuple(issues),
            )
        )
    return ResolvedManifest(config=config, attributes=tuple(resolved))


@dataclass(frozen=True)
class EvidenceRecord:
    """Normalized output from one manual or automated assessment."""

    evidence_id: str
    source_type: EvidenceSourceType
    attribute_id: str
    model: str
    checkpoint: str
    access_tier: AccessTier
    safeguards_state: str
    outcome: EvidenceOutcome
    evaluation_id: str
    method_categories: tuple[str, ...]
    public_summary: str
    resource_summary: str
    mapped_level_id: str | None = None
    mapping_status: MappingStatus = MappingStatus.UNMAPPED
    mapping_source: str | None = None
    metrics: Mapping[str, float] = field(default_factory=dict)
    independent_verifier: str | None = None
    disclosure_level: DisclosureLevel = DisclosureLevel.RESTRICTED
    evidence_reference: str | None = None
    campaign_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "evidence_id",
            "attribute_id",
            "model",
            "checkpoint",
            "safeguards_state",
            "evaluation_id",
            "public_summary",
            "resource_summary",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if not isinstance(self.source_type, EvidenceSourceType):
            object.__setattr__(self, "source_type", EvidenceSourceType(self.source_type))
        object.__setattr__(self, "access_tier", coerce_access_tier(self.access_tier))
        if not isinstance(self.outcome, EvidenceOutcome):
            object.__setattr__(self, "outcome", EvidenceOutcome(self.outcome))
        if not isinstance(self.mapping_status, MappingStatus):
            object.__setattr__(self, "mapping_status", MappingStatus(self.mapping_status))
        if not isinstance(self.disclosure_level, DisclosureLevel):
            object.__setattr__(self, "disclosure_level", DisclosureLevel(self.disclosure_level))
        object.__setattr__(self, "method_categories", _strings(self.method_categories, "method_categories"))
        if not self.method_categories:
            raise ValueError("evidence requires at least one method category")
        object.__setattr__(self, "mapped_level_id", _optional_text(self.mapped_level_id))
        object.__setattr__(self, "mapping_source", _optional_text(self.mapping_source))
        object.__setattr__(self, "independent_verifier", _optional_text(self.independent_verifier))
        object.__setattr__(self, "evidence_reference", _optional_text(self.evidence_reference))
        object.__setattr__(self, "campaign_id", _optional_text(self.campaign_id))
        object.__setattr__(
            self,
            "metrics",
            {str(key): float(value) for key, value in self.metrics.items()},
        )
        if self.outcome == EvidenceOutcome.CAPABILITY_OBSERVED and self.mapped_level_id is None and not self.metrics:
            raise ValueError(
                "capability_observed evidence needs a mapped_level or metrics that can be mapped"
            )
        if self.mapped_level_id is not None and self.mapping_status == MappingStatus.UNMAPPED:
            raise ValueError("a mapped_level requires a non-unmapped mapping_status")
        if self.mapped_level_id is not None and self.mapping_source is None:
            raise ValueError("a mapped_level requires mapping_source")
        if self.mapped_level_id is None and self.mapping_status != MappingStatus.UNMAPPED:
            raise ValueError("mapping_status must be unmapped when mapped_level is absent")

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        defaults: ProjectConfig | None = None,
    ) -> EvidenceRecord:
        def default(name: str, fallback: Any = None) -> Any:
            if name in payload:
                return payload[name]
            return fallback

        return cls(
            evidence_id=default("evidence_id", default("id", "")),
            source_type=default("type", default("source_type", "")),
            attribute_id=default("attribute", default("attribute_id", "")),
            model=default("model", defaults.model if defaults else ""),
            checkpoint=default("checkpoint", defaults.checkpoint if defaults else ""),
            access_tier=default("access", defaults.access_tier if defaults else ""),
            safeguards_state=default(
                "safeguards", defaults.safeguards_state if defaults else ""
            ),
            outcome=default("outcome", "capability_observed"),
            evaluation_id=default("evaluation_id", default("campaign", "")),
            method_categories=tuple(default("method_categories", ())),
            public_summary=default("public_summary", ""),
            resource_summary=default("resource_summary", "Not publicly specified"),
            mapped_level_id=default("mapped_level", default("mapped_level_id")),
            mapping_status=default("mapping_status", "unmapped"),
            mapping_source=default("mapping_source"),
            metrics=default("metrics", {}),
            independent_verifier=default("independent_verifier"),
            disclosure_level=default("disclosure", default("disclosure_level", "restricted")),
            evidence_reference=default("evidence_reference"),
            campaign_id=default("campaign", default("campaign_id")),
        )

    @classmethod
    def from_v2_evaluation(
        cls,
        evaluation: Any,
        *,
        evidence_id: str,
        source_type: EvidenceSourceType,
        mapped_level_id: str,
        mapping_status: MappingStatus,
        mapping_source: str,
        public_summary: str,
        resource_summary: str,
        safeguards_state: str,
        disclosure_level: DisclosureLevel = DisclosureLevel.RESTRICTED,
        evidence_reference: str | None = None,
    ) -> EvidenceRecord:
        """Normalize an existing ``FrontierEvaluationV2`` without inventing a mapping.

        The caller must explicitly provide the provider-level mapping for the v2
        evaluation result.  A generic experimental threshold is never promoted
        automatically into a lab capability level.
        """

        battery = evaluation.battery
        return cls(
            evidence_id=evidence_id,
            source_type=source_type,
            attribute_id=evaluation.capability_domain,
            model=evaluation.model,
            checkpoint=evaluation.checkpoint_revision,
            access_tier=battery.access_tier,
            safeguards_state=safeguards_state,
            outcome=EvidenceOutcome.CAPABILITY_OBSERVED,
            evaluation_id=evaluation.evaluation_id,
            method_categories=tuple(
                sorted(
                    {
                        mechanism.value
                        for routine in battery.routines
                        for mechanism in routine.mechanisms
                    }
                )
            ),
            public_summary=public_summary,
            resource_summary=resource_summary,
            mapped_level_id=mapped_level_id,
            mapping_status=mapping_status,
            mapping_source=mapping_source,
            disclosure_level=disclosure_level,
            evidence_reference=evidence_reference,
        )

    @property
    def has_authoritative_mapping(self) -> bool:
        return self.mapped_level_id is not None and self.mapping_status.authoritative

    def to_public_dict(self) -> dict[str, Any]:
        result = {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type.value,
            "attribute": self.attribute_id,
            "access_tier": self.access_tier.value,
            "safeguards_state": self.safeguards_state,
            "outcome": self.outcome.value,
            "evaluation_id": self.evaluation_id,
            "method_categories": list(self.method_categories),
            "public_summary": self.public_summary,
            "resource_summary": self.resource_summary,
            "mapped_level": self.mapped_level_id,
            "mapping_status": self.mapping_status.value,
            "mapping_source": self.mapping_source,
            "independent_verifier": self.independent_verifier,
            "disclosure_level": self.disclosure_level.value,
            "operational_details_withheld": self.disclosure_level != DisclosureLevel.PUBLIC,
        }
        if self.disclosure_level == DisclosureLevel.PUBLIC:
            result["evidence_reference"] = self.evidence_reference
        return result


@dataclass(frozen=True)
class QualificationRecord:
    """Qualification of the combined battery at one lab-defined capability level."""

    qualification_id: str
    attribute_id: str
    threshold_level_id: str
    access_tier: AccessTier
    safeguards_state: str
    included_evidence_ids: tuple[str, ...]
    recovery_passed: bool
    control_coverage_passed: bool
    mechanism_coverage_passed: bool
    saturation_passed: bool
    creation_check_passed: bool
    eligible_controls: int
    recovered_controls: int
    recovery_lower_bound: float
    reasons: tuple[str, ...] = ()
    evidence_reference: str | None = None
    disclosure_level: DisclosureLevel = DisclosureLevel.RESTRICTED

    def __post_init__(self) -> None:
        for name in ("qualification_id", "attribute_id", "threshold_level_id", "safeguards_state"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(self, "access_tier", coerce_access_tier(self.access_tier))
        object.__setattr__(self, "included_evidence_ids", _strings(self.included_evidence_ids, "included_evidence_ids"))
        object.__setattr__(self, "reasons", _strings(self.reasons, "reasons"))
        if not isinstance(self.disclosure_level, DisclosureLevel):
            object.__setattr__(self, "disclosure_level", DisclosureLevel(self.disclosure_level))
        if self.eligible_controls < 0 or not 0 <= self.recovered_controls <= self.eligible_controls:
            raise ValueError("invalid qualification control counts")
        if self.recovery_passed and self.eligible_controls == 0:
            raise ValueError("recovery_passed requires at least one eligible control")
        if not 0.0 <= self.recovery_lower_bound <= 1.0:
            raise ValueError("recovery_lower_bound must be in [0, 1]")
        object.__setattr__(self, "evidence_reference", _optional_text(self.evidence_reference))

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        defaults: ProjectConfig | None = None,
    ) -> QualificationRecord:
        return cls(
            qualification_id=payload.get("qualification_id", payload.get("id", "")),
            attribute_id=payload.get("attribute", payload.get("attribute_id", "")),
            threshold_level_id=payload.get("threshold", payload.get("threshold_level_id", "")),
            access_tier=payload.get("access", defaults.access_tier if defaults else ""),
            safeguards_state=payload.get(
                "safeguards", defaults.safeguards_state if defaults else ""
            ),
            included_evidence_ids=tuple(payload.get("included_evidence_ids", ())),
            recovery_passed=bool(payload.get("recovery_passed", False)),
            control_coverage_passed=bool(payload.get("control_coverage_passed", False)),
            mechanism_coverage_passed=bool(payload.get("mechanism_coverage_passed", False)),
            saturation_passed=bool(payload.get("saturation_passed", False)),
            creation_check_passed=bool(payload.get("creation_check_passed", False)),
            eligible_controls=int(payload.get("eligible_controls", 0)),
            recovered_controls=int(payload.get("recovered_controls", 0)),
            recovery_lower_bound=float(payload.get("recovery_lower_bound", 0.0)),
            reasons=tuple(payload.get("reasons", ())),
            evidence_reference=payload.get("evidence_reference"),
            disclosure_level=payload.get("disclosure", payload.get("disclosure_level", "restricted")),
        )

    @classmethod
    def from_v2(
        cls,
        qualification: Any,
        *,
        qualification_id: str,
        attribute_id: str,
        threshold_level_id: str,
        access_tier: AccessTier | str,
        safeguards_state: str,
        included_evidence_ids: Iterable[str],
        evidence_reference: str | None = None,
        disclosure_level: DisclosureLevel = DisclosureLevel.RESTRICTED,
    ) -> QualificationRecord:
        """Normalize a v2 qualification at an explicitly supplied provider level."""

        return cls(
            qualification_id=qualification_id,
            attribute_id=attribute_id,
            threshold_level_id=threshold_level_id,
            access_tier=access_tier,
            safeguards_state=safeguards_state,
            included_evidence_ids=tuple(included_evidence_ids),
            recovery_passed=qualification.recovery_passed,
            control_coverage_passed=qualification.control_coverage_passed,
            mechanism_coverage_passed=qualification.mechanism_coverage_passed,
            saturation_passed=qualification.saturation_passed,
            creation_check_passed=qualification.creation_check_passed,
            eligible_controls=qualification.eligible_controls,
            recovered_controls=qualification.recovered_controls,
            recovery_lower_bound=qualification.recovery_lower_bound,
            reasons=tuple(
                reason.value if hasattr(reason, "value") else str(reason)
                for reason in qualification.reasons
            ),
            evidence_reference=evidence_reference,
            disclosure_level=disclosure_level,
        )

    @property
    def fully_qualified(self) -> bool:
        return (
            self.recovery_passed
            and self.control_coverage_passed
            and self.mechanism_coverage_passed
            and self.saturation_passed
            and self.creation_check_passed
        )

    def covers(self, evidence: Sequence[EvidenceRecord]) -> bool:
        required = {
            item.evidence_id
            for item in evidence
            if item.source_type != EvidenceSourceType.DEFAULT_EVALUATION
        }
        return required.issubset(set(self.included_evidence_ids))

    def to_public_dict(self) -> dict[str, Any]:
        result = {
            "qualification_id": self.qualification_id,
            "attribute": self.attribute_id,
            "threshold": self.threshold_level_id,
            "access_tier": self.access_tier.value,
            "safeguards_state": self.safeguards_state,
            "included_evidence_ids": list(self.included_evidence_ids),
            "eligible_controls": self.eligible_controls,
            "recovered_controls": self.recovered_controls,
            "recovery_lower_bound": self.recovery_lower_bound,
            "recovery_passed": self.recovery_passed,
            "control_coverage_passed": self.control_coverage_passed,
            "mechanism_coverage_passed": self.mechanism_coverage_passed,
            "saturation_passed": self.saturation_passed,
            "creation_check_passed": self.creation_check_passed,
            "fully_qualified": self.fully_qualified,
            "reasons": list(self.reasons),
            "disclosure_level": self.disclosure_level.value,
            "operational_details_withheld": self.disclosure_level != DisclosureLevel.PUBLIC,
        }
        if self.disclosure_level == DisclosureLevel.PUBLIC:
            result["evidence_reference"] = self.evidence_reference
        return result


def load_evidence_package(
    path: str | Path,
    *,
    defaults: ProjectConfig | None = None,
) -> tuple[tuple[EvidenceRecord, ...], tuple[QualificationRecord, ...]]:
    """Load a package containing evidence records, qualifications, or both."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        evidence_payloads = payload
        qualification_payloads: Sequence[Mapping[str, Any]] = ()
    elif isinstance(payload, Mapping):
        evidence_payloads = payload.get("evidence", payload.get("records", ()))
        qualification_payloads = payload.get("qualifications", ())
        if not evidence_payloads and "evidence_id" in payload:
            evidence_payloads = (payload,)
    else:
        raise ValueError("evidence package must be a JSON object or array")
    evidence = tuple(
        EvidenceRecord.from_dict(item, defaults=defaults) for item in evidence_payloads
    )
    qualifications = tuple(
        QualificationRecord.from_dict(item, defaults=defaults)
        for item in qualification_payloads
    )
    return evidence, qualifications


def map_evidence_record(
    evidence: EvidenceRecord,
    resolved: ResolvedAttribute,
) -> EvidenceRecord:
    """Apply predeclared mapping rules when an evidence source has raw metrics only."""

    framework = resolved.framework
    if evidence.mapped_level_id is not None:
        if framework is not None and framework.resolve_level(evidence.mapped_level_id) is None:
            raise ValueError(
                f"evidence {evidence.evidence_id} uses level {evidence.mapped_level_id!r} "
                "which is not in the selected framework"
            )
        return evidence
    if framework is None or not evidence.metrics:
        return evidence
    matching = [
        rule
        for rule in resolved.mapping_rules
        if rule.evaluation_id == evidence.evaluation_id and rule.matches(evidence.metrics)
    ]
    if not matching:
        return evidence
    strongest = max(
        matching,
        key=lambda rule: framework.resolve_level(rule.supports_level_id).order,  # type: ignore[union-attr]
    )
    return replace(
        evidence,
        mapped_level_id=strongest.supports_level_id,
        mapping_status=strongest.status,
        mapping_source=strongest.source,
    )


@dataclass(frozen=True)
class AttributeAssessment:
    """One capability attribute under one exact access and safeguards condition."""

    model: str
    checkpoint: str
    attribute_id: str
    capability_kind: CapabilityKind
    access_tier: AccessTier
    safeguards_state: str
    framework_name: str | None
    framework_version: str | None
    threshold_level_id: str | None
    default_observed_level_id: str | None
    highest_observed_level_id: str | None
    qualification: QualificationRecord | None
    conclusion: EvidenceConclusion | None
    resolution_status: ResolutionStatus
    level_results: tuple[Mapping[str, Any], ...]
    evidence: tuple[EvidenceRecord, ...]
    excluded_evidence: tuple[Mapping[str, str], ...]
    limitations: tuple[str, ...]

    @property
    def observed_bracket(self) -> tuple[str | None, str | None]:
        return self.default_observed_level_id, self.highest_observed_level_id

    @property
    def qualified_upper_endpoint(self) -> str | None:
        if self.highest_observed_level_id is None:
            return None
        if self.conclusion == EvidenceConclusion.CAPABILITY_AT_OR_ABOVE_THRESHOLD:
            return self.highest_observed_level_id
        if self.qualification is not None and self.qualification.fully_qualified:
            return self.highest_observed_level_id
        return None

    @property
    def system_card_statement(self) -> str | None:
        if self.resolution_status == ResolutionStatus.BRACKET_ONLY:
            return (
                f"For {self.attribute_id}, the default observed capability was "
                f"{self.default_observed_level_id or 'not mapped'} and the highest capability "
                f"recovered by the specified battery was "
                f"{self.highest_observed_level_id or 'not mapped'} under "
                f"{self.access_tier.value} access with safeguards state "
                f"{self.safeguards_state!r}."
            )
        if self.resolution_status != ResolutionStatus.READY:
            return None
        scope = (
            f"under {self.access_tier.value} access with safeguards state "
            f"{self.safeguards_state!r}"
        )
        if self.conclusion == EvidenceConclusion.CAPABILITY_AT_OR_ABOVE_THRESHOLD:
            return (
                f"The assessment battery observed {self.attribute_id} capability at or above "
                f"{self.threshold_level_id} {scope}."
            )
        if self.conclusion == EvidenceConclusion.CAPABILITY_STAYS_BELOW_THRESHOLD:
            return (
                f"The assessment battery did not observe {self.attribute_id} capability at or "
                f"above {self.threshold_level_id} {scope}; the battery passed its applicable "
                "known-hidden control checks."
            )
        if self.conclusion == EvidenceConclusion.UPPER_BOUND_UNKNOWN:
            return (
                f"The highest observed {self.attribute_id} capability was "
                f"{self.highest_observed_level_id or 'not mapped'} {scope}, but the assessment "
                "battery did not recover the applicable known-hidden controls reliably."
            )
        return (
            f"The {self.attribute_id} result is inconclusive {scope}; precautionary governance "
            "treatment is recorded separately from the observed evidence."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": "3.0",
            "model": self.model,
            "checkpoint": self.checkpoint,
            "attribute": self.attribute_id,
            "capability_type": self.capability_kind.value,
            "access_tier": self.access_tier.value,
            "safeguards_state": self.safeguards_state,
            "framework": {
                "name": self.framework_name,
                "version": self.framework_version,
            },
            "policy_threshold": self.threshold_level_id,
            "default_observed_capability": self.default_observed_level_id,
            "highest_capability_recovered": self.highest_observed_level_id,
            "observed_bracket": list(self.observed_bracket),
            "qualified_upper_endpoint": self.qualified_upper_endpoint,
            "qualification": self.qualification.to_public_dict() if self.qualification else None,
            "evidence_conclusion": self.conclusion.value if self.conclusion else None,
            "resolution_status": self.resolution_status.value,
            "level_results": [dict(item) for item in self.level_results],
            "system_card_statement": self.system_card_statement,
            "evidence_summary": [item.to_public_dict() for item in self.evidence],
            "excluded_evidence": [dict(item) for item in self.excluded_evidence],
            "limitations": list(self.limitations),
            "disclosure_note": (
                "Method categories and aggregate evidence are public. Operational prompts, "
                "scripts, transcripts, triggers, and harmful details may remain restricted."
            ),
        }


def assess_attribute_v3(
    manifest: ResolvedManifest,
    attribute_id: str,
    evidence: Iterable[EvidenceRecord],
    qualifications: Iterable[QualificationRecord] = (),
) -> AttributeAssessment:
    """Aggregate all credible manual and automated evidence for one attribute."""

    resolved = manifest.attribute(attribute_id)
    framework = resolved.framework
    relevant: list[EvidenceRecord] = []
    excluded: list[dict[str, str]] = []
    for item in evidence:
        mismatches = []
        if item.attribute_id != attribute_id:
            mismatches.append("attribute")
        if item.model != manifest.config.model:
            mismatches.append("model")
        if item.checkpoint != manifest.config.checkpoint:
            mismatches.append("checkpoint")
        if item.access_tier != manifest.config.access_tier:
            mismatches.append("access_tier")
        if item.safeguards_state != manifest.config.safeguards_state:
            mismatches.append("safeguards_state")
        if mismatches:
            excluded.append(
                {
                    "evidence_id": item.evidence_id,
                    "reason": "scope mismatch: " + ", ".join(mismatches),
                }
            )
            continue
        relevant.append(map_evidence_record(item, resolved))

    ids = [item.evidence_id for item in relevant]
    if len(ids) != len(set(ids)):
        raise ValueError("evidence_id values must be unique within an assessment")

    deferred_mapping_issue_codes = {
        "no_public_evaluation_mapping",
        "mapping_requires_confirmation",
    }
    limitations = [
        issue.message
        for issue in resolved.issues
        if issue.code not in deferred_mapping_issue_codes
    ]
    source_types = {item.source_type for item in relevant}
    missing_sources = [
        source for source in resolved.required_evidence_types if source not in source_types
    ]
    if missing_sources:
        limitations.append(
            "Required evidence sources were not supplied: "
            + ", ".join(item.value for item in missing_sources)
            + "."
        )

    mapped_observations = [
        item
        for item in relevant
        if item.outcome == EvidenceOutcome.CAPABILITY_OBSERVED
        and item.mapped_level_id is not None
    ]
    authoritative = [item for item in mapped_observations if item.has_authoritative_mapping]
    provisional_or_unmapped = [
        item
        for item in relevant
        if item.outcome != EvidenceOutcome.NO_CAPABILITY_LEVEL_OBSERVED
        and not item.has_authoritative_mapping
    ]
    if provisional_or_unmapped:
        limitations.append(
            "Some assessment outcomes lack a provider-verified or auditor-authored "
            "capability-level mapping: "
            + ", ".join(item.evidence_id for item in provisional_or_unmapped)
            + "."
        )

    def strongest(records: Sequence[EvidenceRecord]) -> str | None:
        if not records or framework is None:
            return None
        return max(
            records,
            key=lambda item: framework.resolve_level(item.mapped_level_id).order,  # type: ignore[union-attr]
        ).mapped_level_id

    defaults = [
        item for item in authoritative if item.source_type == EvidenceSourceType.DEFAULT_EVALUATION
    ]
    default_level = strongest(defaults)
    highest_level = strongest(authoritative)
    if highest_level is None:
        limitations.append(
            "No provider-verified or auditor-authored capability-level observation was available for this scope."
        )

    threshold = resolved.threshold_level_id
    scoped_qualifications = [
        item
        for item in qualifications
        if item.attribute_id == attribute_id
        and item.access_tier == manifest.config.access_tier
        and item.safeguards_state == manifest.config.safeguards_state
    ]
    qualification_by_level: dict[str, QualificationRecord] = {}
    for item in scoped_qualifications:
        if item.threshold_level_id in qualification_by_level:
            raise ValueError(
                "only one qualification record is allowed per attribute, level, and scope"
            )
        if framework is not None and framework.resolve_level(item.threshold_level_id) is None:
            raise ValueError(
                f"qualification {item.qualification_id} uses level "
                f"{item.threshold_level_id!r} outside the selected framework"
            )
        qualification_by_level[item.threshold_level_id] = item
    qualification = qualification_by_level.get(threshold) if threshold is not None else None
    qualification_covers_battery = qualification.covers(relevant) if qualification else False
    if qualification and not qualification_covers_battery:
        limitations.append(
            "The qualification record does not cover every non-default evidence source in the combined battery."
        )

    policy_blocked = any(issue.blocking for issue in resolved.issues) or manifest.config.template_mode
    evidence_mapping_blocked = bool(provisional_or_unmapped)

    def conclusion_for_level(
        level_id: str,
        level_qualification: QualificationRecord | None,
    ) -> tuple[EvidenceConclusion | None, ResolutionStatus, bool]:
        at_or_above_level = (
            framework is not None
            and highest_level is not None
            and framework.compare(highest_level, level_id) >= 0
        )
        covers = level_qualification.covers(relevant) if level_qualification else False
        if at_or_above_level:
            return EvidenceConclusion.CAPABILITY_AT_OR_ABOVE_THRESHOLD, ResolutionStatus.READY, covers
        if resolved.config.kind == CapabilityKind.BENIGN:
            return None, ResolutionStatus.NO_CAPABILITY_LEVEL_CONCLUSION, covers
        if policy_blocked or evidence_mapping_blocked or highest_level is None:
            return None, ResolutionStatus.NO_CAPABILITY_LEVEL_CONCLUSION, covers
        if level_qualification is None or not level_qualification.recovery_passed:
            return EvidenceConclusion.UPPER_BOUND_UNKNOWN, ResolutionStatus.READY, covers
        if level_qualification.fully_qualified and covers and not missing_sources:
            return EvidenceConclusion.CAPABILITY_STAYS_BELOW_THRESHOLD, ResolutionStatus.READY, covers
        return EvidenceConclusion.INCONCLUSIVE_PRECAUTIONARY, ResolutionStatus.READY, covers

    level_results: list[dict[str, Any]] = []
    if framework is not None:
        for level in framework.levels:
            level_qualification = qualification_by_level.get(level.level_id)
            level_conclusion, level_status, level_covers = conclusion_for_level(
                level.level_id,
                level_qualification,
            )
            level_results.append(
                {
                    "level": level.level_id,
                    "order": level.order,
                    "target_observed_at_or_above": (
                        highest_level is not None
                        and framework.compare(highest_level, level.level_id) >= 0
                    ),
                    "qualification_id": (
                        level_qualification.qualification_id if level_qualification else None
                    ),
                    "qualification_covers_combined_battery": level_covers,
                    "fully_qualified": (
                        level_qualification.fully_qualified if level_qualification else False
                    ),
                    "conclusion": level_conclusion.value if level_conclusion else None,
                    "resolution_status": level_status.value,
                }
            )

    if (
        threshold is None
        and resolved.config.kind == CapabilityKind.BENIGN
        and not policy_blocked
        and not evidence_mapping_blocked
        and highest_level is not None
    ):
        conclusion = None
        status = ResolutionStatus.BRACKET_ONLY
    elif threshold is None:
        conclusion = None
        status = ResolutionStatus.NO_CAPABILITY_LEVEL_CONCLUSION
    else:
        conclusion, status, _ = conclusion_for_level(threshold, qualification)

    return AttributeAssessment(
        model=manifest.config.model,
        checkpoint=manifest.config.checkpoint,
        attribute_id=attribute_id,
        capability_kind=resolved.config.kind,
        access_tier=manifest.config.access_tier,
        safeguards_state=manifest.config.safeguards_state,
        framework_name=framework.name if framework else None,
        framework_version=framework.version if framework else None,
        threshold_level_id=threshold,
        default_observed_level_id=default_level,
        highest_observed_level_id=highest_level,
        qualification=qualification,
        conclusion=conclusion,
        resolution_status=status,
        level_results=tuple(level_results),
        evidence=tuple(relevant),
        excluded_evidence=tuple(excluded),
        limitations=tuple(dict.fromkeys(limitations)),
    )


@dataclass(frozen=True)
class SystemCardReportV3:
    manifest_sha256: str
    model: str
    checkpoint: str
    assessments: tuple[AttributeAssessment, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": "3.0",
            "manifest_sha256": self.manifest_sha256,
            "model": self.model,
            "checkpoint": self.checkpoint,
            "access_conditioned_results": [item.to_dict() for item in self.assessments],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def build_system_card_report_v3(
    manifest: ResolvedManifest,
    evidence: Iterable[EvidenceRecord],
    qualifications: Iterable[QualificationRecord] = (),
) -> SystemCardReportV3:
    evidence = tuple(evidence)
    qualifications = tuple(qualifications)
    assessments = tuple(
        assess_attribute_v3(manifest, item.attribute_id, evidence, qualifications)
        for item in manifest.config.attributes
    )
    return SystemCardReportV3(
        manifest_sha256=manifest.manifest_sha256,
        model=manifest.config.model,
        checkpoint=manifest.config.checkpoint,
        assessments=assessments,
    )
