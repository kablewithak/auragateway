"""Typed immutable evidence-bundle and comparison-eligibility contracts."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_BUNDLE_ID_PATTERN = re.compile(r"^evb-[0-9a-f]{24}$")
_RUN_GROUP_ID_PATTERN = re.compile(r"^run-group-[a-z0-9-]{3,80}$")
_RUN_ID_PATTERN = re.compile(r"^run-[a-z0-9-]{3,80}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_CASE_ID_PATTERN = re.compile(r"^bundle-[a-z0-9-]{3,80}$")

CONFIGURATION_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "corpus_manifest_sha256",
        "retrieval_configuration_sha256",
        "prompt_template_version",
        "static_context_pack_version",
        "tool_contract_version",
        "output_schema_version",
        "episode_manifest_sha256",
        "quality_rubric_version",
        "blinded_review_protocol_version",
        "negative_control_manifest_sha256",
        "fault_injection_fixture_sha256",
        "telemetry_rules_version",
        "route_policy_version",
        "runtime_condition_implementation_version",
        "benchmark_runner_version",
        "statistical_reporting_version",
        "comparison_eligibility_contract_version",
        "pricing_schedule_version",
        "provider_model_alias",
        "provider_adapter_version",
        "python_version",
        "dependency_lock_sha256",
        "git_commit_sha",
    }
)


class BenchmarkCondition(StrEnum):
    """Frozen benchmark conditions used by evidence bundles."""

    A = "condition_a"
    B = "condition_b"
    C = "condition_c"


class EvidenceBundleType(StrEnum):
    """Supported evidence-bundle shapes."""

    FUNCTIONAL_DRY_RUN = "functional_dry_run"
    BENCHMARK = "benchmark"


class RunTerminalStatus(StrEnum):
    """Required terminal statuses for scheduled benchmark runs."""

    COMPLETED = "completed"
    COMPLETED_VALIDATION_FAILURE = "completed_validation_failure"
    PROVIDER_ERROR = "provider_error"
    BUDGET_EXHAUSTED = "budget_exhausted"
    EXCLUDED_PREDECLARED = "excluded_predeclared"
    INVALIDATED_CONFIGURATION_MISMATCH = "invalidated_configuration_mismatch"
    ABORTED_SAFETY_CONTROL = "aborted_safety_control"


class ArtifactType(StrEnum):
    """Public-safe artifact categories retained in a bundle."""

    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    MARKDOWN = "markdown"


class MetricFamily(StrEnum):
    """Independent comparison families allowed by ADR-0010."""

    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    FEEDBACK = "feedback"


class ComparisonEligibilityStatus(StrEnum):
    """Machine-decided comparison eligibility outcome."""

    ELIGIBLE = "eligible"
    PARTIALLY_ELIGIBLE = "partially_eligible"
    INELIGIBLE = "ineligible"


class BundleFailureCode(StrEnum):
    """Stable structural failures for immutable evidence bundles."""

    RUN_ACCOUNTABILITY_INCOMPLETE = "RUN_ACCOUNTABILITY_INCOMPLETE"
    RUN_RECORD_MISMATCH = "RUN_RECORD_MISMATCH"
    FINGERPRINT_DIGEST_MISMATCH = "FINGERPRINT_DIGEST_MISMATCH"
    ARTIFACT_HASH_MANIFEST_MISMATCH = "ARTIFACT_HASH_MANIFEST_MISMATCH"
    REQUIRED_ARTIFACT_MISSING = "REQUIRED_ARTIFACT_MISSING"
    FORBIDDEN_PUBLIC_ARTIFACT = "FORBIDDEN_PUBLIC_ARTIFACT"
    BUNDLE_CONTENT_DIGEST_MISMATCH = "BUNDLE_CONTENT_DIGEST_MISMATCH"
    INVALID_SUPERSESSION = "INVALID_SUPERSESSION"


class ConfigurationFingerprintSnapshot(BaseModel):
    """Explicit controlled configuration for one benchmark condition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: BenchmarkCondition
    corpus_manifest_sha256: str
    retrieval_configuration_sha256: str
    prompt_template_version: str
    static_context_pack_version: str
    tool_contract_version: str
    output_schema_version: str
    episode_manifest_sha256: str
    quality_rubric_version: str
    blinded_review_protocol_version: str
    negative_control_manifest_sha256: str
    fault_injection_fixture_sha256: str
    telemetry_rules_version: str
    route_policy_version: str
    runtime_condition_implementation_version: str
    benchmark_runner_version: str
    statistical_reporting_version: str
    comparison_eligibility_contract_version: str
    pricing_schedule_version: str
    provider_model_alias: str
    provider_adapter_version: str
    python_version: str
    dependency_lock_sha256: str
    git_commit_sha: str
    fingerprint_sha256: str

    @field_validator(
        "corpus_manifest_sha256",
        "retrieval_configuration_sha256",
        "episode_manifest_sha256",
        "negative_control_manifest_sha256",
        "fault_injection_fixture_sha256",
        "dependency_lock_sha256",
        "fingerprint_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("configuration digests must be lowercase SHA-256")
        return value

    @field_validator("git_commit_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("git_commit_sha must be a lowercase 40-character Git SHA")
        return value


class ScheduledRun(BaseModel):
    """One immutable run slot from the benchmark plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    schedule_index: int = Field(ge=0)
    condition_id: BenchmarkCondition
    episode_id: str

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run_id must use run-<slug> form")
        return value

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value


class BenchmarkRunPlan(BaseModel):
    """Frozen scheduled-run inventory for one run group."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_group_id: str
    scheduled_runs: tuple[ScheduledRun, ...] = Field(min_length=3)

    @field_validator("run_group_id")
    @classmethod
    def validate_run_group_id(cls, value: str) -> str:
        if _RUN_GROUP_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run_group_id must use run-group-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_plan(self) -> BenchmarkRunPlan:
        run_ids = [item.run_id for item in self.scheduled_runs]
        indexes = [item.schedule_index for item in self.scheduled_runs]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("scheduled run IDs must be unique")
        if len(indexes) != len(set(indexes)):
            raise ValueError("scheduled run indexes must be unique")
        if tuple(sorted(indexes)) != tuple(range(len(indexes))):
            raise ValueError("scheduled run indexes must be contiguous from zero")
        return self


class RunEvidenceRecord(BaseModel):
    """Metadata-only terminal record for one scheduled run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    condition_id: BenchmarkCondition
    episode_id: str
    terminal_status: RunTerminalStatus
    attempt_count: int = Field(ge=1)
    result_artifact_sha256: str | None = None
    failure_code: str | None = None
    exclusion_rule_id: str | None = None
    rerun_of_run_id: str | None = None

    @field_validator("run_id", "rerun_of_run_id")
    @classmethod
    def validate_run_id(cls, value: str | None) -> str | None:
        if value is not None and _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run IDs must use run-<slug> form")
        return value

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @field_validator("result_artifact_sha256")
    @classmethod
    def validate_result_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("result_artifact_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> RunEvidenceRecord:
        result_statuses = {
            RunTerminalStatus.COMPLETED,
            RunTerminalStatus.COMPLETED_VALIDATION_FAILURE,
        }
        failure_statuses = {
            RunTerminalStatus.COMPLETED_VALIDATION_FAILURE,
            RunTerminalStatus.PROVIDER_ERROR,
            RunTerminalStatus.BUDGET_EXHAUSTED,
            RunTerminalStatus.INVALIDATED_CONFIGURATION_MISMATCH,
            RunTerminalStatus.ABORTED_SAFETY_CONTROL,
        }
        if self.terminal_status in result_statuses and self.result_artifact_sha256 is None:
            raise ValueError("completed runs require a result artifact digest")
        if self.terminal_status not in result_statuses and self.result_artifact_sha256 is not None:
            raise ValueError("non-completed runs cannot claim a result artifact")
        if self.terminal_status in failure_statuses and not self.failure_code:
            raise ValueError("failed terminal statuses require failure_code")
        if self.terminal_status not in failure_statuses and self.failure_code is not None:
            raise ValueError("non-failed terminal statuses cannot carry failure_code")
        if self.terminal_status is RunTerminalStatus.EXCLUDED_PREDECLARED:
            if not self.exclusion_rule_id:
                raise ValueError("predeclared exclusions require exclusion_rule_id")
        elif self.exclusion_rule_id is not None:
            raise ValueError("only predeclared exclusions can carry exclusion_rule_id")
        if self.rerun_of_run_id == self.run_id:
            raise ValueError("a rerun cannot reference itself")
        return self


class ArtifactHashEntry(BaseModel):
    """Hash-manifest entry for one retained public-safe artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    byte_count: int = Field(ge=0)
    sha256: str
    artifact_type: ArtifactType
    schema_version: str | None = None

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("artifact paths must be normalized relative POSIX paths")
        if value != path.as_posix() or value in {"", "."}:
            raise ValueError("artifact paths must be normalized relative POSIX paths")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact hashes must be lowercase SHA-256")
        return value


class MetricComparisonRule(BaseModel):
    """Controlled mismatches allowed for one independent metric family."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_family: MetricFamily
    allowed_mismatch_fields: tuple[str, ...] = ()

    @field_validator("allowed_mismatch_fields")
    @classmethod
    def validate_allowed_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("allowed mismatch fields must be unique")
        unknown = set(value) - CONFIGURATION_FIELD_NAMES
        if unknown:
            raise ValueError("comparison rules contain unknown configuration fields")
        return tuple(sorted(value))


class ComparisonEligibilityContract(BaseModel):
    """Versioned rules for machine-decided comparison eligibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    contract_version: str = "comparison-eligibility-v1"
    rules: tuple[MetricComparisonRule, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_rules(self) -> ComparisonEligibilityContract:
        families = [rule.metric_family for rule in self.rules]
        if len(families) != len(set(families)):
            raise ValueError("comparison metric families must be unique")
        if set(families) != set(MetricFamily):
            raise ValueError("comparison contract must define every metric family")
        if tuple(families) != tuple(MetricFamily):
            raise ValueError("comparison rules must use deterministic metric-family order")
        return self


class SupersessionMetadata(BaseModel):
    """Append-only correction link to a prior finalized bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supersedes_bundle_id: str
    supersession_reason: str = Field(min_length=8, max_length=300)
    affected_artifacts: tuple[str, ...] = Field(min_length=1)
    benchmark_runs_repeated: bool
    superseded_claims: tuple[str, ...] = ()

    @field_validator("supersedes_bundle_id")
    @classmethod
    def validate_bundle_id(cls, value: str) -> str:
        if _BUNDLE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("supersedes_bundle_id must use evb-<24 lowercase hex>")
        return value

    @field_validator("affected_artifacts")
    @classmethod
    def validate_affected_artifacts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("affected artifacts must be unique")
        return tuple(sorted(value))


class EvidenceBundleCandidate(BaseModel):
    """Synthetic finalized bundle candidate used by the Gate 8 verifier."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    evidence_bundle_id: str
    run_group_id: str
    bundle_type: EvidenceBundleType
    benchmark_constitution_version: str
    benchmark_constitution_sha256: str
    benchmark_manifest_sha256: str
    created_at: datetime
    git_commit_sha: str
    configuration_snapshots: tuple[ConfigurationFingerprintSnapshot, ...] = Field(
        min_length=3,
        max_length=3,
    )
    run_plan: BenchmarkRunPlan
    runs: tuple[RunEvidenceRecord, ...] = Field(min_length=1)
    comparison_contract: ComparisonEligibilityContract
    artifacts: tuple[ArtifactHashEntry, ...] = Field(min_length=1)
    artifact_hash_manifest_sha256: str
    supersession: SupersessionMetadata | None = None
    finalized_content_sha256: str
    synthetic_fixture_execution: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @field_validator("evidence_bundle_id")
    @classmethod
    def validate_bundle_id(cls, value: str) -> str:
        if _BUNDLE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence_bundle_id must use evb-<24 lowercase hex>")
        return value

    @field_validator("run_group_id")
    @classmethod
    def validate_run_group_id(cls, value: str) -> str:
        if _RUN_GROUP_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run_group_id must use run-group-<slug> form")
        return value

    @field_validator(
        "benchmark_constitution_sha256",
        "benchmark_manifest_sha256",
        "artifact_hash_manifest_sha256",
        "finalized_content_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("bundle digests must be lowercase SHA-256")
        return value

    @field_validator("git_commit_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("git_commit_sha must be a lowercase 40-character Git SHA")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> EvidenceBundleCandidate:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone aware")
        if self.run_group_id != self.run_plan.run_group_id:
            raise ValueError("bundle and run-plan run_group_id values must match")
        condition_ids = tuple(item.condition_id for item in self.configuration_snapshots)
        if condition_ids != tuple(BenchmarkCondition):
            raise ValueError("configuration snapshots must be ordered A, B, C")
        run_ids = [item.run_id for item in self.runs]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("bundle run records must have unique run IDs")
        artifact_paths = [item.relative_path for item in self.artifacts]
        if len(artifact_paths) != len(set(artifact_paths)):
            raise ValueError("bundle artifact paths must be unique")
        return self


class MetricEligibilityResult(BaseModel):
    """Eligibility decision for one independent metric family."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_family: MetricFamily
    eligible: bool
    mismatched_fields: tuple[str, ...] = ()


class ComparisonEligibilityDecision(BaseModel):
    """Machine-decided comparison eligibility for a finalized bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str
    status: ComparisonEligibilityStatus
    metric_results: tuple[MetricEligibilityResult, ...] = Field(min_length=4, max_length=4)
    eligible_metric_families: tuple[MetricFamily, ...]
    invalidated_metric_families: tuple[MetricFamily, ...]
    mismatched_fields: tuple[str, ...]
    comparative_claims_permitted: bool

    @model_validator(mode="after")
    def validate_decision(self) -> ComparisonEligibilityDecision:
        families = tuple(item.metric_family for item in self.metric_results)
        if families != tuple(MetricFamily):
            raise ValueError("metric eligibility results must use deterministic order")
        expected_eligible = tuple(
            item.metric_family for item in self.metric_results if item.eligible
        )
        expected_invalid = tuple(
            item.metric_family for item in self.metric_results if not item.eligible
        )
        if self.eligible_metric_families != expected_eligible:
            raise ValueError("eligible metric families must reconcile")
        if self.invalidated_metric_families != expected_invalid:
            raise ValueError("invalidated metric families must reconcile")
        if self.comparative_claims_permitted != bool(expected_eligible):
            raise ValueError("comparative claim permission must match eligible metric families")
        return self


class RunStatusCount(BaseModel):
    """Deterministic terminal-status count."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    terminal_status: RunTerminalStatus
    count: int = Field(ge=0)


class EvidenceBundleEvaluationResult(BaseModel):
    """Metadata-only Gate 8 result for one bundle candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_bundle_id: str
    bundle_valid: bool
    run_accountability_complete: bool
    fingerprint_digests_valid: bool
    artifact_inventory_complete: bool
    private_artifacts_absent: bool
    artifact_hash_manifest_valid: bool
    finalized_content_digest_valid: bool
    supersession_valid: bool
    terminal_status_counts: tuple[RunStatusCount, ...]
    comparison: ComparisonEligibilityDecision
    failure_codes: tuple[BundleFailureCode, ...]
    synthetic_fixture_execution: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_result(self) -> EvidenceBundleEvaluationResult:
        statuses = tuple(item.terminal_status for item in self.terminal_status_counts)
        if statuses != tuple(RunTerminalStatus):
            raise ValueError("terminal status counts must use deterministic order")
        expected_valid = all(
            (
                self.run_accountability_complete,
                self.fingerprint_digests_valid,
                self.artifact_inventory_complete,
                self.private_artifacts_absent,
                self.artifact_hash_manifest_valid,
                self.finalized_content_digest_valid,
                self.supersession_valid,
            )
        )
        if self.bundle_valid != expected_valid:
            raise ValueError("bundle_valid must match structural controls")
        return self


class EvidenceBundleFixtureCase(BaseModel):
    """One fixed Gate 8 bundle case and expected result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    candidate: EvidenceBundleCandidate
    expected_bundle_valid: bool
    expected_eligibility_status: ComparisonEligibilityStatus
    expected_failure_codes: tuple[BundleFailureCode, ...]
    expected_invalidated_metric_families: tuple[MetricFamily, ...]
    negative_control: bool

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _CASE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use bundle-<slug> form")
        return value


class EvidenceBundleFixtureSet(BaseModel):
    """Fixed synthetic bundle cases for Gate 8."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str = "auragateway-gate-8-comparison-eligibility-v1"
    cases: tuple[EvidenceBundleFixtureCase, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_fixture_set(self) -> EvidenceBundleFixtureSet:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("bundle fixture case IDs must be unique")
        if not any(item.negative_control for item in self.cases):
            raise ValueError("bundle fixtures require negative controls")
        if not any(not item.negative_control for item in self.cases):
            raise ValueError("bundle fixtures require passing controls")
        return self


class EvidenceBundleFixtureResult(BaseModel):
    """Executed fixed case with expectation comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    evaluation: EvidenceBundleEvaluationResult
    expectation_matched: bool
    negative_control: bool


class Gate8EvidenceBundleReport(BaseModel):
    """Reproducible Gate 8 fixed-case report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    results: tuple[EvidenceBundleFixtureResult, ...]
    fixture_count: int
    negative_control_count: int
    valid_bundle_count: int
    fully_eligible_count: int
    partially_eligible_count: int
    ineligible_count: int
    all_expectations_matched: bool
    gate_8_controls_passed: bool
    synthetic_fixture_execution: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> Gate8EvidenceBundleReport:
        if self.fixture_count != len(self.results):
            raise ValueError("fixture_count must match results")
        if self.negative_control_count != sum(item.negative_control for item in self.results):
            raise ValueError("negative_control_count must reconcile")
        if self.valid_bundle_count != sum(item.evaluation.bundle_valid for item in self.results):
            raise ValueError("valid_bundle_count must reconcile")
        statuses = [item.evaluation.comparison.status for item in self.results]
        if self.fully_eligible_count != statuses.count(ComparisonEligibilityStatus.ELIGIBLE):
            raise ValueError("fully_eligible_count must reconcile")
        if self.partially_eligible_count != statuses.count(
            ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
        ):
            raise ValueError("partially_eligible_count must reconcile")
        if self.ineligible_count != statuses.count(ComparisonEligibilityStatus.INELIGIBLE):
            raise ValueError("ineligible_count must reconcile")
        expected_match = all(item.expectation_matched for item in self.results)
        if self.all_expectations_matched != expected_match:
            raise ValueError("all_expectations_matched must reconcile")
        if self.gate_8_controls_passed != expected_match:
            raise ValueError("gate_8_controls_passed must match expectations")
        return self


class Gate8EvidenceBundleManifest(BaseModel):
    """Hash-bound inventory for Gate 8 fixtures and report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-8-comparison-eligibility-manifest-v1"
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    adr_path: str
    adr_sha256: str
    episode_manifest_path: str
    episode_manifest_sha256: str
    quality_gate_manifest_path: str
    quality_gate_manifest_sha256: str
    efc_manifest_path: str
    efc_manifest_sha256: str
    fixture_count: int
    negative_control_count: int
    gate_8_controls_passed: bool
    synthetic_fixture_execution: Literal[True] = True
    measured_execution_permitted: Literal[False] = False

    @field_validator(
        "fixture_sha256",
        "report_sha256",
        "adr_sha256",
        "episode_manifest_sha256",
        "quality_gate_manifest_sha256",
        "efc_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("Gate 8 manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Gate8EvidenceBundleManifest:
        if not self.gate_8_controls_passed:
            raise ValueError("frozen Gate 8 manifest requires passing controls")
        return self


class Gate8EvidenceBundleSummary(BaseModel):
    """Safe CLI summary for Gate 8 build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_count: int
    negative_control_count: int
    valid_bundle_count: int
    fully_eligible_count: int
    partially_eligible_count: int
    ineligible_count: int
    gate_8_controls_passed: bool
    synthetic_fixture_execution: bool
    measured_execution_permitted: bool
    universal_claim_override_permitted: Literal[False] = False
