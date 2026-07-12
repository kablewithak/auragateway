"""Typed benchmark-runner preflight contracts for AuraGateway Phase 7."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.evidence_bundle import BenchmarkCondition

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID_PATTERN = re.compile(r"^run-[a-z0-9-]{3,120}$")
_PAIR_ID_PATTERN = re.compile(r"^pair-[a-z0-9-]{3,120}$")
_NAMESPACE_ID_PATTERN = re.compile(r"^ns-[a-z0-9-]{3,120}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_MANIFEST_ID_PATTERN = re.compile(r"^execution-manifest-[a-z0-9-]{3,80}$")
_PLAN_ID_PATTERN = re.compile(r"^benchmark-plan-[a-z0-9-]{3,80}$")


class ExecutionManifestStatus(StrEnum):
    """Lifecycle state for the measured-execution manifest."""

    DRAFT = "draft"
    FROZEN = "frozen"


class BenchmarkWorkload(StrEnum):
    """Frozen benchmark workload families."""

    FUNCTIONAL = "functional"
    RUNTIME = "runtime_microbenchmark"


class ProviderReadinessState(StrEnum):
    """Readiness posture for planning versus measured execution."""

    CONFIGURATION_READY = "configuration_ready"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class PreflightCheckStatus(StrEnum):
    """Outcome of one benchmark preflight check."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class PreflightCheckName(StrEnum):
    """Machine-readable benchmark preflight checks."""

    EXECUTION_MANIFEST_VALID = "execution_manifest_valid"
    EXECUTION_MANIFEST_ASSETS_RESOLVED = "execution_manifest_assets_resolved"
    EXECUTION_MANIFEST_FROZEN = "execution_manifest_frozen"
    EXECUTION_MANIFEST_HASH_VALID = "execution_manifest_hash_valid"
    PROVIDER_CONFIGURATION_READY = "provider_configuration_ready"
    PROVIDER_LIVE_PROBE_PASSED = "provider_live_probe_passed"
    REQUEST_BUDGET_SUFFICIENT = "request_budget_sufficient"
    COST_BUDGET_DECLARED = "cost_budget_declared"
    FUNCTIONAL_MATRIX_COMPLETE = "functional_matrix_complete"
    RUNTIME_MATRIX_COMPLETE = "runtime_matrix_complete"
    EVIDENCE_VAULT_CONTRACT_VALID = "evidence_vault_contract_valid"
    EXECUTION_DISABLED_BY_DEFAULT = "execution_disabled_by_default"


class PreflightFailureCode(StrEnum):
    """Stable reasons that block measured execution authorization."""

    EXECUTION_MANIFEST_INVALID = "EXECUTION_MANIFEST_INVALID"
    EXECUTION_MANIFEST_ASSETS_UNRESOLVED = "EXECUTION_MANIFEST_ASSETS_UNRESOLVED"
    EXECUTION_MANIFEST_NOT_FROZEN = "EXECUTION_MANIFEST_NOT_FROZEN"
    EXECUTION_MANIFEST_HASH_MISMATCH = "EXECUTION_MANIFEST_HASH_MISMATCH"
    PROVIDER_CONFIGURATION_NOT_READY = "PROVIDER_CONFIGURATION_NOT_READY"
    PROVIDER_LIVE_PROBE_NOT_PASSED = "PROVIDER_LIVE_PROBE_NOT_PASSED"
    REQUEST_BUDGET_INSUFFICIENT = "REQUEST_BUDGET_INSUFFICIENT"
    COST_BUDGET_NOT_DECLARED = "COST_BUDGET_NOT_DECLARED"
    FUNCTIONAL_PLAN_INCOMPLETE = "FUNCTIONAL_PLAN_INCOMPLETE"
    RUNTIME_PLAN_INCOMPLETE = "RUNTIME_PLAN_INCOMPLETE"
    EVIDENCE_VAULT_CONTRACT_INVALID = "EVIDENCE_VAULT_CONTRACT_INVALID"
    EXECUTION_ENABLEMENT_UNSAFE = "EXECUTION_ENABLEMENT_UNSAFE"


class ExecutionManifestIdentity(BaseModel):
    """Identity and implementation fields required before measured execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_manifest_id: str
    execution_manifest_version: str = "1.0.0-draft"
    execution_manifest_status: ExecutionManifestStatus = ExecutionManifestStatus.DRAFT
    execution_manifest_sha256: str | None = None
    benchmark_constitution_version: str = "1.0.0"
    benchmark_constitution_sha256: str
    benchmark_runner_version: str = "1.0.0"
    comparison_eligibility_contract_version: str = "1.1.0"
    evidence_bundle_schema_version: str = "1.0.0"
    git_commit_sha: str
    python_version: str
    dependency_lock_sha256: str
    execution_enabled: bool = False

    @field_validator("execution_manifest_id")
    @classmethod
    def validate_manifest_id(cls, value: str) -> str:
        if _MANIFEST_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("execution_manifest_id must use execution-manifest-<slug> form")
        return value

    @field_validator(
        "benchmark_constitution_sha256",
        "dependency_lock_sha256",
        "execution_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-manifest digests must be lowercase SHA-256")
        return value

    @field_validator("git_commit_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("git_commit_sha must be a lowercase 40-character Git SHA")
        return value

    @model_validator(mode="after")
    def validate_lifecycle(self) -> ExecutionManifestIdentity:
        if self.execution_manifest_status is ExecutionManifestStatus.DRAFT:
            if self.execution_manifest_sha256 is not None:
                raise ValueError("draft execution manifests must not claim a frozen digest")
            if self.execution_enabled:
                raise ValueError("draft execution manifests must keep execution disabled")
        if (
            self.execution_manifest_status is ExecutionManifestStatus.FROZEN
            and self.execution_manifest_sha256 is None
        ):
            raise ValueError("frozen execution manifests require a canonical digest")
        return self


class ExecutionManifestAssets(BaseModel):
    """Frozen corpus, context, provider, route, evaluation, and fault identities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    corpus_manifest_sha256: str
    chunking_strategy_id: str
    chunking_configuration_sha256: str
    retrieval_implementation_id: str
    retrieval_configuration_sha256: str
    retrieval_type: str
    top_k: int = Field(ge=1)
    metadata_filter_policy_version: str
    development_retrieval_manifest_sha256: str
    held_out_retrieval_manifest_sha256: str
    retrieval_scorecard_sha256: str

    prompt_template_id: str
    prompt_template_version: str
    static_context_pack_id: str
    static_context_pack_version: str
    serialization_version: str
    tool_contract_version: str
    output_schema_version: str
    prefix_fingerprint_contract_version: str

    primary_provider: str
    provider_model_alias: str
    exact_model_identifier: str
    provider_adapter_version: str
    provider_documentation_date_checked: date
    telemetry_rules_version: str
    telemetry_fixture_manifest_sha256: str
    cache_ttl_assumption_seconds: int = Field(gt=0)
    cache_ttl_source: str
    pricing_schedule_version: str | None = None
    pricing_source_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    route_policy_version: str
    economy_model_alias: str
    capable_model_alias: str
    capability_calibration_report_sha256: str
    route_ttl_policy_version: str
    provider_failure_policy_version: str

    diagnostic_episode_manifest_sha256: str
    functional_benchmark_manifest_sha256: str
    runtime_microbenchmark_manifest_sha256: str
    quality_rubric_version: str
    quality_rubric_sha256: str
    blinded_adjudication_protocol_version: str
    review_sample_schedule_sha256: str
    feedback_evidence_contract_version: str

    negative_control_manifest_sha256: str | None = None
    fault_injection_fixture_sha256: str | None = None
    privacy_trace_contract_version: str
    privacy_verification_report_sha256: str | None = None
    cross_condition_isolation_test_sha256: str | None = None

    @field_validator(
        "corpus_manifest_sha256",
        "chunking_configuration_sha256",
        "retrieval_configuration_sha256",
        "development_retrieval_manifest_sha256",
        "held_out_retrieval_manifest_sha256",
        "retrieval_scorecard_sha256",
        "telemetry_fixture_manifest_sha256",
        "capability_calibration_report_sha256",
        "diagnostic_episode_manifest_sha256",
        "functional_benchmark_manifest_sha256",
        "runtime_microbenchmark_manifest_sha256",
        "quality_rubric_sha256",
        "review_sample_schedule_sha256",
        "negative_control_manifest_sha256",
        "fault_injection_fixture_sha256",
        "privacy_verification_report_sha256",
        "cross_condition_isolation_test_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("execution-manifest asset digests must be lowercase SHA-256")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_pricing_group(self) -> ExecutionManifestAssets:
        values = (self.pricing_schedule_version, self.pricing_source_date, self.currency)
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("pricing schedule, source date, and currency resolve together")
        return self


class ExecutionManifestControls(BaseModel):
    """Frozen benchmark controls copied from Constitution 1.0.0."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    timeout_policy_id: Literal["provider-request-policy-v1"]
    retry_policy_id: Literal["provider-request-policy-v1"]
    exclusion_policy_id: Literal["exclusion-policy-v1"]
    rerun_policy_id: Literal["rerun-policy-v1"]
    denominator_policy_id: Literal["denominator-policy-v1"]
    statistical_reporting_configuration_id: Literal["paired-bootstrap-v1"]
    quality_non_inferiority_policy_id: Literal["quality-non-inferiority-v1"]


class BenchmarkExecutionManifest(BaseModel):
    """Complete typed execution-manifest candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    identity: ExecutionManifestIdentity
    assets: ExecutionManifestAssets
    controls: ExecutionManifestControls


class ProviderReadinessSnapshot(BaseModel):
    """Metadata-only provider readiness evidence; never stores credentials."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: str
    provider_model_alias: str
    provider_adapter_version: str
    readiness_state: ProviderReadinessState
    credentials_configured: bool
    adapter_calibration_passed: bool
    telemetry_mapping_passed: bool
    provider_error_taxonomy_passed: bool
    live_probe_performed: bool = False
    live_probe_passed: bool = False
    readiness_evidence_sha256: str

    @field_validator("readiness_evidence_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("readiness_evidence_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_readiness(self) -> ProviderReadinessSnapshot:
        config_ready = all(
            (
                self.credentials_configured,
                self.adapter_calibration_passed,
                self.telemetry_mapping_passed,
                self.provider_error_taxonomy_passed,
            )
        )
        if self.readiness_state is ProviderReadinessState.CONFIGURATION_READY and not config_ready:
            raise ValueError("configuration_ready requires all configuration controls")
        if self.live_probe_passed and not self.live_probe_performed:
            raise ValueError("live_probe_passed requires live_probe_performed")
        return self


class BenchmarkBudgetEnvelope(BaseModel):
    """Bounded planning budget for trajectories, turns, attempts, and cost."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    maximum_trajectory_count: int = Field(ge=1)
    maximum_turn_count: int = Field(ge=1)
    maximum_request_attempt_count: int = Field(ge=1)
    approved_cost_budget_minor_units: int | None = Field(default=None, ge=1)
    estimated_upper_bound_minor_units: int | None = Field(default=None, ge=1)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_cost_pair(self) -> BenchmarkBudgetEnvelope:
        declared = self.approved_cost_budget_minor_units is not None
        estimated = self.estimated_upper_bound_minor_units is not None
        if declared != estimated:
            raise ValueError("approved and estimated cost budgets must be declared together")
        return self


class EvidenceVaultContract(BaseModel):
    """Local-first public and protected storage boundary for benchmark evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    public_root: Literal["evidence_vault"] = "evidence_vault"
    protected_root: Literal[".local"] = ".local"
    required_public_directories: tuple[str, ...] = (
        "runtime_reports",
        "quality_reports",
        "trace_samples",
        "before_after_tables",
    )
    append_only_finalized_bundles: Literal[True] = True
    protected_review_exports_public: Literal[False] = False
    raw_provider_payloads_public: Literal[False] = False
    raw_prompts_public: Literal[False] = False
    secrets_public: Literal[False] = False

    @model_validator(mode="after")
    def validate_directories(self) -> EvidenceVaultContract:
        if len(self.required_public_directories) != len(set(self.required_public_directories)):
            raise ValueError("required evidence-vault directories must be unique")
        if any(".." in item or item.startswith("/") for item in self.required_public_directories):
            raise ValueError("evidence-vault directories must be relative and bounded")
        return self


class BenchmarkPlanRequest(BaseModel):
    """Inputs for deterministic A/B/C run-matrix expansion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    functional_episode_ids: tuple[str, ...] = Field(min_length=18, max_length=18)
    runtime_episode_ids: tuple[str, ...] = Field(min_length=6, max_length=6)
    turns_per_episode: int = Field(default=4, ge=1)
    maximum_retries_after_initial_attempt: int = Field(default=1, ge=0, le=1)

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, value: str) -> str:
        if _PLAN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("plan_id must use benchmark-plan-<slug> form")
        return value

    @field_validator("functional_episode_ids", "runtime_episode_ids")
    @classmethod
    def validate_episode_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("benchmark episode IDs must be unique")
        if tuple(sorted(value)) != value:
            raise ValueError("benchmark episode IDs must be sorted")
        for episode_id in value:
            if _EPISODE_ID_PATTERN.fullmatch(episode_id) is None:
                raise ValueError("benchmark episode IDs must match ep-func-<NNN>")
        return value

    @model_validator(mode="after")
    def validate_runtime_subset(self) -> BenchmarkPlanRequest:
        if not set(self.runtime_episode_ids) <= set(self.functional_episode_ids):
            raise ValueError("runtime episodes must be a subset of functional episodes")
        return self


class BenchmarkPreflightInput(BaseModel):
    """Complete non-executing input for benchmark planning and preflight."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    execution_manifest: BenchmarkExecutionManifest
    provider_readiness: ProviderReadinessSnapshot
    budget: BenchmarkBudgetEnvelope
    evidence_vault: EvidenceVaultContract
    plan_request: BenchmarkPlanRequest
    execution_requested: Literal[False] = False


class PlannedBenchmarkRun(BaseModel):
    """One deterministic planned run before provider execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schedule_index: int = Field(ge=0)
    run_id: str
    comparison_pair_id: str
    workload: BenchmarkWorkload
    episode_id: str
    replication_id: str
    condition_id: BenchmarkCondition
    condition_order_index: int = Field(ge=0, le=2)
    cache_namespace_id: str
    turn_count: int = Field(ge=1)
    maximum_request_attempt_count: int = Field(ge=1)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if _RUN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("run_id must use run-<slug> form")
        return value

    @field_validator("comparison_pair_id")
    @classmethod
    def validate_pair_id(cls, value: str) -> str:
        if _PAIR_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("comparison_pair_id must use pair-<slug> form")
        return value

    @field_validator("cache_namespace_id")
    @classmethod
    def validate_namespace_id(cls, value: str) -> str:
        if _NAMESPACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("cache_namespace_id must use ns-<slug> form")
        return value


class PlannedRunLedger(BaseModel):
    """Complete deterministic functional and runtime run inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    plan_id: str
    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    runs: tuple[PlannedBenchmarkRun, ...] = Field(min_length=342, max_length=342)
    functional_trajectory_count: int = 162
    runtime_trajectory_count: int = 180
    total_trajectory_count: int = 342
    total_turn_count: int = 1368
    maximum_request_attempt_count: int = 2736
    execution_enabled: Literal[False] = False

    @model_validator(mode="after")
    def validate_ledger(self) -> PlannedRunLedger:
        indexes = tuple(item.schedule_index for item in self.runs)
        if indexes != tuple(range(len(self.runs))):
            raise ValueError("planned run indexes must be contiguous and ordered")
        run_ids = [item.run_id for item in self.runs]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("planned run IDs must be unique")
        if sum(item.workload is BenchmarkWorkload.FUNCTIONAL for item in self.runs) != 162:
            raise ValueError("functional run count must equal 162")
        if sum(item.workload is BenchmarkWorkload.RUNTIME for item in self.runs) != 180:
            raise ValueError("runtime run count must equal 180")
        expected_turns = sum(item.turn_count for item in self.runs)
        if self.total_turn_count != expected_turns:
            raise ValueError("total_turn_count must reconcile with planned runs")
        expected_attempts = sum(item.maximum_request_attempt_count for item in self.runs)
        if self.maximum_request_attempt_count != expected_attempts:
            raise ValueError("maximum request attempts must reconcile with planned runs")
        return self


class PreflightCheckResult(BaseModel):
    """One bounded preflight result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_name: PreflightCheckName
    status: PreflightCheckStatus
    failure_code: PreflightFailureCode | None = None
    details: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> PreflightCheckResult:
        if self.status is PreflightCheckStatus.FAILED and self.failure_code is None:
            raise ValueError("failed preflight checks require a failure code")
        if self.status is not PreflightCheckStatus.FAILED and self.failure_code is not None:
            raise ValueError("non-failed preflight checks cannot carry a failure code")
        return self


class BenchmarkPreflightReport(BaseModel):
    """Metadata-only planning and measured-execution authorization report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    plan_id: str
    execution_manifest_id: str
    checks: tuple[PreflightCheckResult, ...] = Field(min_length=1)
    failure_codes: tuple[PreflightFailureCode, ...]
    functional_trajectory_count: int
    runtime_trajectory_count: int
    total_trajectory_count: int
    total_turn_count: int
    maximum_request_attempt_count: int
    planning_ready: bool
    measured_execution_ready: bool
    execution_enabled: bool
    measured_execution_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> BenchmarkPreflightReport:
        expected_failures = tuple(
            dict.fromkeys(
                item.failure_code for item in self.checks if item.failure_code is not None
            )
        )
        if self.failure_codes != expected_failures:
            raise ValueError("failure_codes must match failed checks in check order")
        if self.measured_execution_ready and self.failure_codes:
            raise ValueError("measured execution cannot be ready with failed checks")
        if self.measured_execution_ready and not self.execution_enabled:
            raise ValueError("measured execution readiness requires explicit enablement")
        if self.measured_execution_permitted:
            raise ValueError("this preflight slice does not permit measured execution")
        return self


class Gate9PreflightManifest(BaseModel):
    """Hash-bound inventory for benchmark-runner preflight evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-9-benchmark-preflight-manifest-v1"
    input_path: str
    input_sha256: str
    execution_manifest_path: str
    execution_manifest_sha256: str
    plan_path: str
    plan_sha256: str
    report_path: str
    report_sha256: str
    benchmark_constitution_path: str
    benchmark_constitution_sha256: str
    execution_requirements_path: str
    execution_requirements_sha256: str
    gate8_manifest_path: str
    gate8_manifest_sha256: str
    gate7_manifest_path: str
    gate7_manifest_sha256: str
    total_trajectory_count: int
    total_turn_count: int
    maximum_request_attempt_count: int
    planning_ready: bool
    measured_execution_ready: bool
    execution_enabled: bool
    measured_execution_permitted: Literal[False] = False

    @field_validator(
        "input_sha256",
        "execution_manifest_sha256",
        "plan_sha256",
        "report_sha256",
        "benchmark_constitution_sha256",
        "execution_requirements_sha256",
        "gate8_manifest_sha256",
        "gate7_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("preflight manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> Gate9PreflightManifest:
        if self.measured_execution_ready or self.execution_enabled:
            raise ValueError("frozen preflight evidence must remain non-executing")
        return self


class Gate9PreflightSummary(BaseModel):
    """Safe CLI summary for validate-config, plan, or verify."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_manifest_status: ExecutionManifestStatus
    functional_trajectory_count: int
    runtime_trajectory_count: int
    total_trajectory_count: int
    total_turn_count: int
    maximum_request_attempt_count: int
    planning_ready: bool
    measured_execution_ready: bool
    execution_enabled: bool
    measured_execution_permitted: bool
    failure_codes: tuple[PreflightFailureCode, ...]
