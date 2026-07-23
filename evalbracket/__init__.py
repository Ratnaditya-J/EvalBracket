"""EvalBracket: qualify dangerous-capability evidence by access tier.

Public API:
    protocol_v3        -- lab-defined policy, mixed evidence, and system-card reporting
    protocol           -- access-conditioned controls, conclusions, and system-card output
    Signals            -- per-pair signal container (combiner.Signals)
    EvalBracket        -- legacy experimental calibrated combiner
    scoring            -- coverage + Winkler interval score
    baselines          -- Wilson-CI baselines B0 (around S1) and B1 (around S3)
    decomposition      -- delta_aware / delta_head = the disguise ceiling
    synthetic          -- known-truth synthetic locked-pair generator
    splits             -- leave-one-model-out group splitting
"""
from . import (
    baselines,
    control_builders_v2,
    decomposition,
    elicitation_v2,
    maturation,
    maturation_synth,
    protocol,
    protocol_v2,
    protocol_v3,
    routine_backends,
    scoring,
    splits,
    synthetic,
)
from .combiner import EvalBracket, Signals, conformal_quantile
from .decomposition import disguise_ceiling_summary, unbiased_s_mit
from .protocol import (
    AccessConditionedBracket,
    AccessTier,
    CapabilityLevel,
    ControlCaseResult,
    ControlSuiteResult,
    ElicitationRoutine,
    EvidenceConclusion,
    FrontierEvaluation,
    ResourceBudget,
    RoutineMismatchError,
    SystemCardReport,
    ThresholdQualification,
    assess,
    build_system_card_report,
)
from .protocol_v2 import (
    AccessConditionedBracketV2,
    BudgetPoint,
    CapabilityProvenance,
    ControlOrigin,
    ElicitationBatteryV2,
    ElicitationQualificationV2,
    EvidenceLane,
    FrontierEvaluationV2,
    ImplementationStatus,
    MechanismClass,
    QualificationPolicyV2,
    QualificationReason,
    SaturationEvidence,
    SystemCardReportV2,
    V2ControlResult,
    V2Routine,
    assess_v2,
    build_system_card_report_v2,
    one_sided_recovery_lower_bound,
    qualify_battery_v2,
)
from .protocol_v3 import (
    AttributeAssessment,
    CapabilityAttributeConfig,
    CapabilityFramework,
    CapabilityKind,
    CapabilityLevelDefinition,
    DisclosureLevel,
    EvaluationMappingRule,
    EvidenceOutcome,
    EvidenceRecord,
    EvidenceSourceType,
    MappingOperator,
    MappingStatus,
    PolicyCatalog,
    ProjectConfig,
    QualificationRecord,
    ResolutionIssue,
    ResolutionStatus,
    ResolvedAttribute,
    ResolvedManifest,
    SystemCardReportV3,
    assess_attribute_v3,
    build_system_card_report_v3,
    coerce_access_tier,
    load_evidence_package,
    load_project_config,
    load_resolved_manifest,
    map_evidence_record,
    resolve_project_config,
)
from .routine_backends import (
    CaseAttempt,
    ElicitationBackend,
    EvaluationCase,
    GenerationRequest,
    GenerationResult,
    MechanismDispatcher,
    RoutineExecution,
    TrainingExample,
)
from .control_builders_v2 import (
    CapabilityExample,
    ControlRecipe,
    build_control_recipe,
    deterministic_password,
    evaluation_aware_lock_recipe,
    external_control_recipe,
    password_lock_recipe,
    prompt_resistant_lock_recipe,
    weak_model_imitation_recipe,
)

__all__ = [
    "EvalBracket", "Signals", "conformal_quantile",
    "unbiased_s_mit", "disguise_ceiling_summary",
    "AccessConditionedBracket", "AccessTier", "CapabilityLevel",
    "ControlCaseResult", "ControlSuiteResult", "ElicitationRoutine",
    "EvidenceConclusion", "FrontierEvaluation", "ResourceBudget",
    "RoutineMismatchError", "SystemCardReport", "ThresholdQualification",
    "assess", "build_system_card_report", "protocol",
    "AccessConditionedBracketV2", "BudgetPoint", "CapabilityProvenance",
    "ControlOrigin", "ElicitationBatteryV2", "ElicitationQualificationV2",
    "EvidenceLane", "FrontierEvaluationV2", "ImplementationStatus",
    "MechanismClass", "QualificationPolicyV2", "QualificationReason",
    "SaturationEvidence", "SystemCardReportV2", "V2ControlResult", "V2Routine",
    "assess_v2", "build_system_card_report_v2", "one_sided_recovery_lower_bound",
    "qualify_battery_v2", "protocol_v2", "elicitation_v2",
    "AttributeAssessment", "CapabilityAttributeConfig", "CapabilityFramework",
    "CapabilityKind", "CapabilityLevelDefinition", "DisclosureLevel",
    "EvaluationMappingRule", "EvidenceOutcome", "EvidenceRecord",
    "EvidenceSourceType", "MappingOperator", "MappingStatus", "PolicyCatalog",
    "ProjectConfig", "QualificationRecord", "ResolutionIssue", "ResolutionStatus",
    "ResolvedAttribute", "ResolvedManifest", "SystemCardReportV3",
    "assess_attribute_v3", "build_system_card_report_v3", "coerce_access_tier",
    "load_evidence_package", "load_project_config", "load_resolved_manifest",
    "map_evidence_record", "resolve_project_config", "protocol_v3",
    "CaseAttempt", "ElicitationBackend", "EvaluationCase", "GenerationRequest",
    "GenerationResult", "MechanismDispatcher", "RoutineExecution", "TrainingExample",
    "routine_backends",
    "CapabilityExample", "ControlRecipe", "build_control_recipe",
    "deterministic_password", "evaluation_aware_lock_recipe",
    "external_control_recipe", "password_lock_recipe",
    "prompt_resistant_lock_recipe", "weak_model_imitation_recipe",
    "control_builders_v2",
    "scoring", "baselines", "decomposition", "synthetic", "splits", "maturation", "maturation_synth",
]
__version__ = "0.4.0"
