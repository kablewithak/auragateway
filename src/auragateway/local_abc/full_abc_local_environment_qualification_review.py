"""Review the fresh full-run local environment-qualification boundary."""

from __future__ import annotations

import json
import re
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "1bbc11e72880bc5b6fa88da3ba8b180420c9abf5"
REVIEW_ID: Final = "auragateway-full-abc-local-full-run-environment-qualification-review-v1"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_review_v1.json"
)
NEXT_GATE: Final = "full_abc_local_full_run_environment_qualification_implementation"

_IMPLEMENTATION_PLAN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_preflight_v3_rebuild_implementation_v1.json"
)
_PREFLIGHT_MANIFEST_PATH: Final = Path("data/evals/benchmark/preflight-v3/manifest.json")
_PREFLIGHT_REPORT_PATH: Final = Path("data/evals/benchmark/preflight-v3/preflight_report.json")
_RUNTIME_CORRECTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_runtime_lineage_correction_v1.json"
)
_HISTORICAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/measured_execution_authorization_v1.json"
)

_EXPECTED_IMPLEMENTATION_PLAN_BLOB_SHA: Final = "5e9943ce23d318afe7157c6978ed8d2c67d3bf35"
_EXPECTED_PREFLIGHT_MANIFEST_BLOB_SHA: Final = "9d25301b23a77c5bfc0ed14383e9cfe16ca9e842"
_EXPECTED_PREFLIGHT_REPORT_BLOB_SHA: Final = "747cd6f5adf4852f09072feb7ecdbcd34a5777de"
_EXPECTED_RUNTIME_CORRECTION_BLOB_SHA: Final = "186084e7c8dc0d4e24f5ab1be190381a5ab57270"
_EXPECTED_HISTORICAL_AUTHORIZATION_BLOB_SHA: Final = "9a712372cee83c4af4a026081ec01ddbc809effa"

_EXPECTED_WORKER_IDS: Final = ("worker_1", "worker_2")
_EXPECTED_WORKER_PORTS: Final = (8001, 8002)
_EXPECTED_GPU_INDEXES: Final = (0, 1)

_REQUIRED_RUNTIME_LOCK_FIELDS: Final = (
    "attention_backend",
    "automatic_prefix_cache_configuration",
    "cuda_version",
    "dtype",
    "gpu_count",
    "gpu_memory_utilization",
    "gpu_model",
    "maximum_model_length",
    "model_repository",
    "model_revision",
    "output_token_budget",
    "python_version",
    "quantization",
    "tokenizer_revision",
    "torch_version",
    "transformers_version",
    "vllm_distribution_version",
    "vllm_module_version",
    "vllm_wheel_sha256",
    "worker_startup_command_sha256",
)

_REQUIRED_METRIC_SEMANTICS: Final = (
    "cached_prefix_tokens",
    "metric_availability_state",
    "newly_computed_prefill_tokens",
    "prefill_duration_ms",
    "prompt_tokens",
    "realized_route",
    "request_latency_ms",
    "reset_state",
    "time_to_first_token_ms",
    "worker_id",
)

_REQUIRED_STOP_CONDITIONS: Final = (
    "cache_metric_unavailable",
    "credential_detected",
    "customer_data_detected",
    "dependency_lock_incomplete",
    "external_spend_nonzero",
    "gpu_topology_mismatch",
    "hosted_provider_fallback_detected",
    "model_identity_mismatch",
    "privacy_scan_failure",
    "reset_capability_unproven",
    "route_realization_mismatch",
    "tokenizer_identity_mismatch",
    "vllm_wheel_mismatch",
    "worker_health_failure",
    "worker_port_conflict",
)


class FullABCLocalEnvironmentQualificationReviewError(RuntimeError):
    """Expected metadata-safe validation failure for the review package."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class AuthorityDisposition(StrEnum):
    """Whether prior evidence may govern the fresh qualification package."""

    CURRENT_AUTHORITY = "current_authority"
    HISTORICAL_CONTEXT_ONLY = "historical_context_only"


class QualificationGenerationStage(StrEnum):
    """Earliest stage at which one artifact may be populated."""

    IMPLEMENTATION = "implementation"
    QUALIFICATION_EXECUTION = "qualification_execution"


class QualificationAuthorityBinding(LocalABCContract):
    """One exact repository authority used by the review."""

    binding_id: str
    role: str = Field(min_length=8, max_length=200)
    source_locator: str
    git_blob_sha: str
    disposition: AuthorityDisposition
    notes: str = Field(min_length=12, max_length=480)

    @field_validator("binding_id")
    @classmethod
    def validate_binding_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authority binding IDs must use stable lowercase characters")
        return value

    @field_validator("source_locator")
    @classmethod
    def validate_source_locator(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("authority source locators must remain bounded")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_OBJECT_PATTERN.fullmatch(value) is None:
            raise ValueError("authority identity must be a lowercase Git object SHA")
        return value


class QualificationWorkerRequirement(LocalABCContract):
    """One required isolated local vLLM worker."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    port: Literal[8001, 8002]
    transport_endpoint: Literal["/v1/chat/completions"]
    health_endpoint: Literal["/health"]
    models_endpoint: Literal["/v1/models"]
    loopback_only: Literal[True] = True


class RuntimeIdentityDecision(LocalABCContract):
    """Historical baseline that must be freshly recaptured, never inherited."""

    status: Literal["HISTORICAL_BASELINE_REQUIRES_FRESH_CAPTURE"]
    environment: Literal["kaggle_t4_x2"]
    execution_backend: Literal["local_vllm"]
    gpu_count: Literal[2] = 2
    gpu_model: Literal["Tesla T4"]
    compute_capability: Literal["7.5"]
    model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    historical_torch_version: Literal["2.11.0+cu129"]
    historical_cuda_version: Literal["12.9"]
    historical_vllm_module_version: Literal["0.25.1"]
    historical_vllm_distribution_version: Literal["0.25.1+cu129"]
    historical_vllm_wheel_sha256: Literal[
        "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
    ]
    workers: tuple[QualificationWorkerRequirement, QualificationWorkerRequirement]
    fresh_values_must_share_one_runtime_session: Literal[True] = True
    inherited_versions_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_worker_topology(self) -> Self:
        worker_ids = tuple(worker.worker_id for worker in self.workers)
        ports = tuple(worker.port for worker in self.workers)
        gpu_indexes = tuple(worker.gpu_index for worker in self.workers)
        if worker_ids != _EXPECTED_WORKER_IDS:
            raise ValueError("workers must preserve worker_1 and worker_2 order")
        if ports != _EXPECTED_WORKER_PORTS:
            raise ValueError("workers must bind ports 8001 and 8002")
        if gpu_indexes != _EXPECTED_GPU_INDEXES:
            raise ValueError("workers must bind GPU indexes 0 and 1")
        return self


class RuntimeDependencyLockDecision(LocalABCContract):
    """Separate the current Kaggle runtime lock from the developer lock."""

    developer_lock_path: Literal["data/evals/benchmark/preflight-v3/developer_dependency_lock.json"]
    kaggle_runtime_lock_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/kaggle_runtime_dependency_lock.json"
    ]
    required_fields: tuple[str, ...]
    source_environment: Literal["active_fresh_kaggle_runtime"]
    developer_lock_reuse_permitted: Literal[False] = False
    historical_runtime_values_reuse_permitted: Literal[False] = False
    hosted_provider_packages_active_for_full_abc: Literal[False] = False

    @field_validator("required_fields")
    @classmethod
    def validate_required_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_RUNTIME_LOCK_FIELDS:
            raise ValueError("runtime dependency fields drifted")
        return value


class QualificationArtifactRequirement(LocalABCContract):
    """One artifact required by the qualification package."""

    artifact_id: str
    path: str
    generation_stage: QualificationGenerationStage
    requires_gpu_activity: bool
    current_state: Literal["NOT_GENERATED"] = "NOT_GENERATED"

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("qualification artifact paths must remain bounded")
        return value

    @model_validator(mode="after")
    def validate_generation_stage(self) -> Self:
        expected_gpu = self.generation_stage is QualificationGenerationStage.QUALIFICATION_EXECUTION
        if self.requires_gpu_activity is not expected_gpu:
            raise ValueError("GPU activity flag must match the generation stage")
        return self


class MetricCapabilityDecision(LocalABCContract):
    """Require explicit cache metric capability without zero-value fabrication."""

    required_semantics: tuple[str, ...]
    missing_metric_state: Literal["UNAVAILABLE_NOT_ZERO"]
    raw_metric_name_mapping_required: Literal[True] = True
    source_and_unit_mapping_required: Literal[True] = True
    latency_only_cache_inference_permitted: Literal[False] = False
    zero_fill_for_missing_metrics_permitted: Literal[False] = False
    cache_success_claim_permitted: Literal[False] = False

    @field_validator("required_semantics")
    @classmethod
    def validate_required_semantics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_METRIC_SEMANTICS:
            raise ValueError("required metric semantics drifted")
        return value


class ResetCapabilityDecision(LocalABCContract):
    """Define the only acceptable proof of a clean cache baseline."""

    required_steps: tuple[str, ...]
    namespace_only_reset_accepted: Literal[False] = False
    full_worker_restart_required: Literal[True] = True
    closed_port_verification_required: Literal[True] = True
    process_exit_verification_required: Literal[True] = True
    startup_identity_revalidation_required: Literal[True] = True
    reset_success_claim_permitted_before_execution: Literal[False] = False

    @field_validator("required_steps")
    @classmethod
    def validate_required_steps(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = (
            "confirm_worker_process_exit",
            "confirm_worker_ports_closed",
            "record_reset_start",
            "restart_workers_from_bound_startup_plan",
            "revalidate_model_tokenizer_and_worker_identity",
            "verify_fresh_health_and_metric_baseline",
        )
        if value != expected:
            raise ValueError("reset capability steps drifted")
        return value


class QualificationStopDecision(LocalABCContract):
    """Fail closed on identity, privacy, runtime, or evidence divergence."""

    stop_conditions: tuple[str, ...]
    fail_closed: Literal[True] = True
    hosted_fallback_permitted: Literal[False] = False
    automatic_retry_after_identity_failure_permitted: Literal[False] = False

    @field_validator("stop_conditions")
    @classmethod
    def validate_stop_conditions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_STOP_CONDITIONS:
            raise ValueError("qualification stop conditions drifted")
        return value


class EnvironmentQualificationSafetyEnvelope(LocalABCContract):
    """Review-only boundary that cannot start or qualify the environment."""

    qualification_assets_generated: Literal[False] = False
    notebook_created: Literal[False] = False
    notebook_execution_performed: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    worker_start_authorized: Literal[False] = False
    worker_started: Literal[False] = False
    model_execution_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False


class FullABCLocalEnvironmentQualificationReview(LocalABCContract):
    """Authoritative review for implementing fresh full-run qualification tooling."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-full-abc-local-full-run-environment-qualification-review-v1"]
    source_main_merge_commit: Literal["1bbc11e72880bc5b6fa88da3ba8b180420c9abf5"]
    lifecycle_before: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    lifecycle_after: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    decision: Literal["APPROVED_FOR_QUALIFICATION_TOOLING_IMPLEMENTATION"]
    authority_bindings: tuple[QualificationAuthorityBinding, ...]
    runtime_identity: RuntimeIdentityDecision
    dependency_lock: RuntimeDependencyLockDecision
    artifact_requirements: tuple[QualificationArtifactRequirement, ...]
    metric_capability: MetricCapabilityDecision
    reset_capability: ResetCapabilityDecision
    stop_decision: QualificationStopDecision
    safety: EnvironmentQualificationSafetyEnvelope
    next_gate: Literal["full_abc_local_full_run_environment_qualification_implementation"]

    @field_validator("authority_bindings")
    @classmethod
    def validate_authority_bindings(
        cls,
        value: tuple[QualificationAuthorityBinding, ...],
    ) -> tuple[QualificationAuthorityBinding, ...]:
        binding_ids = tuple(binding.binding_id for binding in value)
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("authority binding IDs must be unique")
        if binding_ids != tuple(sorted(binding_ids)):
            raise ValueError("authority bindings must be canonically sorted")
        return value

    @field_validator("artifact_requirements")
    @classmethod
    def validate_artifact_requirements(
        cls,
        value: tuple[QualificationArtifactRequirement, ...],
    ) -> tuple[QualificationArtifactRequirement, ...]:
        artifact_ids = tuple(artifact.artifact_id for artifact in value)
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("qualification artifact IDs must be unique")
        if artifact_ids != tuple(sorted(artifact_ids)):
            raise ValueError("qualification artifacts must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_review_boundary(self) -> Self:
        historical = {
            binding.binding_id: binding.disposition for binding in self.authority_bindings
        }
        if historical.get("historical-measured-authorization") is not (
            AuthorityDisposition.HISTORICAL_CONTEXT_ONLY
        ):
            raise ValueError("historical authorization cannot qualify the full-run environment")
        if any(
            artifact.current_state != "NOT_GENERATED" for artifact in self.artifact_requirements
        ):
            raise ValueError("review cannot contain generated qualification evidence")
        return self


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "REQUIRED_JSON_AUTHORITY_UNREADABLE",
            "required environment-qualification authority could not be read",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise FullABCLocalEnvironmentQualificationReviewError(
            "REQUIRED_JSON_AUTHORITY_INVALID",
            "required environment-qualification authority must be one JSON object",
            path.as_posix(),
        )
    return payload


def _git_index_blob_sha(repo_root: Path, relative_path: Path) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                f"HEAD:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required environment-qualification Git authority could not be resolved",
            relative_path.as_posix(),
        ) from exc
    identity = result.stdout.strip()
    if _GIT_OBJECT_PATTERN.fullmatch(identity) is None:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required environment-qualification Git authority returned an invalid identity",
            relative_path.as_posix(),
        )
    return identity


def _require_source_ancestor(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_MERGE_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 100 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def build_default_review() -> FullABCLocalEnvironmentQualificationReview:
    """Build the review without generating or executing qualification assets."""

    authorities = tuple(
        sorted(
            (
                QualificationAuthorityBinding(
                    binding_id="historical-measured-authorization",
                    role="historical 72-trajectory local measured-run authorization",
                    source_locator=_HISTORICAL_AUTHORIZATION_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_HISTORICAL_AUTHORIZATION_BLOB_SHA,
                    disposition=AuthorityDisposition.HISTORICAL_CONTEXT_ONLY,
                    notes=(
                        "Proves prior local viability only; it cannot qualify or authorize "
                        "the new 342-trajectory lineage."
                    ),
                ),
                QualificationAuthorityBinding(
                    binding_id="local-runtime-correction",
                    role="restored local vLLM runtime and exact model lineage",
                    source_locator=_RUNTIME_CORRECTION_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_RUNTIME_CORRECTION_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                    notes=(
                        "Provides the historical runtime baseline while requiring fresh "
                        "full-run requalification."
                    ),
                ),
                QualificationAuthorityBinding(
                    binding_id="preflight-v3-implementation-plan",
                    role="merged implementation decision for clean planning assets",
                    source_locator=_IMPLEMENTATION_PLAN_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_IMPLEMENTATION_PLAN_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                    notes="Points directly to the full-run environment-qualification review.",
                ),
                QualificationAuthorityBinding(
                    binding_id="preflight-v3-manifest",
                    role="canonical inventory of the merged clean planning lineage",
                    source_locator=_PREFLIGHT_MANIFEST_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_PREFLIGHT_MANIFEST_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                    notes=(
                        "Confirms planning completion while environment qualification and "
                        "execution remain blocked."
                    ),
                ),
                QualificationAuthorityBinding(
                    binding_id="preflight-v3-report",
                    role="merged preflight decision and outstanding gate report",
                    source_locator=_PREFLIGHT_REPORT_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_PREFLIGHT_REPORT_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                    notes=(
                        "Records the unqualified environment and preserves zero-spend "
                        "execution controls."
                    ),
                ),
            ),
            key=lambda binding: binding.binding_id,
        )
    )

    artifacts = tuple(
        sorted(
            (
                QualificationArtifactRequirement(
                    artifact_id="cache-metric-capability-report",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "cache_metric_capability_report.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="gpu-topology-report",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/gpu_topology_report.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="kaggle-runtime-dependency-lock",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "kaggle_runtime_dependency_lock.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="model-identity-report",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "model_identity_report.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="qualification-manifest",
                    path=("data/evals/benchmark/environment-qualification-v1/manifest.json"),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="qualification-report",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "qualification_report.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="qualification-request",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "qualification_request.json"
                    ),
                    generation_stage=QualificationGenerationStage.IMPLEMENTATION,
                    requires_gpu_activity=False,
                ),
                QualificationArtifactRequirement(
                    artifact_id="reset-capability-report",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "reset_capability_report.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="worker-health-report",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/"
                        "worker_health_report.json"
                    ),
                    generation_stage=(QualificationGenerationStage.QUALIFICATION_EXECUTION),
                    requires_gpu_activity=True,
                ),
                QualificationArtifactRequirement(
                    artifact_id="worker-startup-plan",
                    path=(
                        "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
                    ),
                    generation_stage=QualificationGenerationStage.IMPLEMENTATION,
                    requires_gpu_activity=False,
                ),
            ),
            key=lambda artifact: artifact.artifact_id,
        )
    )

    return FullABCLocalEnvironmentQualificationReview(
        review_id=REVIEW_ID,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        decision="APPROVED_FOR_QUALIFICATION_TOOLING_IMPLEMENTATION",
        authority_bindings=authorities,
        runtime_identity=RuntimeIdentityDecision(
            status="HISTORICAL_BASELINE_REQUIRES_FRESH_CAPTURE",
            environment="kaggle_t4_x2",
            execution_backend="local_vllm",
            gpu_model="Tesla T4",
            compute_capability="7.5",
            model_alias="local-qwen2.5-0.5b-instruct",
            model_repository="Qwen/Qwen2.5-0.5B-Instruct",
            model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
            tokenizer_revision="7ae557604adf67be50417f59c2c2f167def9a775",
            historical_torch_version="2.11.0+cu129",
            historical_cuda_version="12.9",
            historical_vllm_module_version="0.25.1",
            historical_vllm_distribution_version="0.25.1+cu129",
            historical_vllm_wheel_sha256=(
                "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
            ),
            workers=(
                QualificationWorkerRequirement(
                    worker_id="worker_1",
                    gpu_index=0,
                    port=8001,
                    transport_endpoint="/v1/chat/completions",
                    health_endpoint="/health",
                    models_endpoint="/v1/models",
                ),
                QualificationWorkerRequirement(
                    worker_id="worker_2",
                    gpu_index=1,
                    port=8002,
                    transport_endpoint="/v1/chat/completions",
                    health_endpoint="/health",
                    models_endpoint="/v1/models",
                ),
            ),
        ),
        dependency_lock=RuntimeDependencyLockDecision(
            developer_lock_path=(
                "data/evals/benchmark/preflight-v3/developer_dependency_lock.json"
            ),
            kaggle_runtime_lock_path=(
                "data/evals/benchmark/environment-qualification-v1/"
                "kaggle_runtime_dependency_lock.json"
            ),
            required_fields=_REQUIRED_RUNTIME_LOCK_FIELDS,
            source_environment="active_fresh_kaggle_runtime",
        ),
        artifact_requirements=artifacts,
        metric_capability=MetricCapabilityDecision(
            required_semantics=_REQUIRED_METRIC_SEMANTICS,
            missing_metric_state="UNAVAILABLE_NOT_ZERO",
        ),
        reset_capability=ResetCapabilityDecision(
            required_steps=(
                "confirm_worker_process_exit",
                "confirm_worker_ports_closed",
                "record_reset_start",
                "restart_workers_from_bound_startup_plan",
                "revalidate_model_tokenizer_and_worker_identity",
                "verify_fresh_health_and_metric_baseline",
            ),
        ),
        stop_decision=QualificationStopDecision(
            stop_conditions=_REQUIRED_STOP_CONDITIONS,
        ),
        safety=EnvironmentQualificationSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def load_full_abc_local_environment_qualification_review(
    path: Path,
) -> FullABCLocalEnvironmentQualificationReview:
    """Load the canonical review artifact with metadata-safe failures."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FullABCLocalEnvironmentQualificationReview.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "ENVIRONMENT_QUALIFICATION_REVIEW_INVALID",
            "the environment-qualification review artifact is missing or invalid",
            path.as_posix(),
        ) from exc


def write_default_review(path: Path) -> FullABCLocalEnvironmentQualificationReview:
    """Write only the review artifact; do not create or execute qualification assets."""

    review = build_default_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.canonical_json(), encoding="utf-8")
    return review


def validate_repository_review_package(repo_root: Path) -> dict[str, object]:
    """Validate merged authorities and return a privacy-safe review summary."""

    _require_source_ancestor(repo_root)
    review = load_full_abc_local_environment_qualification_review(repo_root / REVIEW_PATH)

    expected_blobs = {
        _IMPLEMENTATION_PLAN_PATH: _EXPECTED_IMPLEMENTATION_PLAN_BLOB_SHA,
        _PREFLIGHT_MANIFEST_PATH: _EXPECTED_PREFLIGHT_MANIFEST_BLOB_SHA,
        _PREFLIGHT_REPORT_PATH: _EXPECTED_PREFLIGHT_REPORT_BLOB_SHA,
        _RUNTIME_CORRECTION_PATH: _EXPECTED_RUNTIME_CORRECTION_BLOB_SHA,
        _HISTORICAL_AUTHORIZATION_PATH: _EXPECTED_HISTORICAL_AUTHORIZATION_BLOB_SHA,
    }
    drift = tuple(
        sorted(
            path.as_posix()
            for path, expected in expected_blobs.items()
            if _git_index_blob_sha(repo_root, path) != expected
        )
    )
    if drift:
        raise FullABCLocalEnvironmentQualificationReviewError(
            "ENVIRONMENT_QUALIFICATION_AUTHORITY_DRIFT",
            "one or more environment-qualification authorities drifted",
            details=drift,
        )

    implementation = _load_json_object(repo_root / _IMPLEMENTATION_PLAN_PATH)
    manifest = _load_json_object(repo_root / _PREFLIGHT_MANIFEST_PATH)
    report = _load_json_object(repo_root / _PREFLIGHT_REPORT_PATH)
    correction = _load_json_object(repo_root / _RUNTIME_CORRECTION_PATH)
    historical = _load_json_object(repo_root / _HISTORICAL_AUTHORIZATION_PATH)

    checks: list[bool] = [
        implementation.get("next_gate")
        == "full_abc_local_full_run_environment_qualification_review",
        manifest.get("next_gate") == "full_abc_local_full_run_environment_qualification_review",
        manifest.get("planning_lineage_complete") is True,
        manifest.get("execution_enabled") is False,
        manifest.get("measured_execution_authorized") is False,
        report.get("decision") == "PLANNING_ASSETS_GENERATED_EXECUTION_BLOCKED",
        report.get("gpu_execution_authorized") is False,
        report.get("measured_execution_authorized") is False,
        correction.get("measured_execution_authorized") is False,
        historical.get("measured_execution_authorized") is True,
        historical.get("planned_trajectory_count") == 72,
    ]
    local_runtime = correction.get("local_runtime")
    if isinstance(local_runtime, dict):
        checks.extend(
            (
                local_runtime.get("current_full_run_environment_requalification_required") is True,
                local_runtime.get("environment") == "kaggle_t4_x2",
                local_runtime.get("gpu_count") == 2,
                local_runtime.get("gpu_model") == "Tesla T4",
                local_runtime.get("external_spend") == 0,
                local_runtime.get("hosted_provider_required") is False,
            )
        )
    else:
        checks.append(False)

    if not all(checks):
        raise FullABCLocalEnvironmentQualificationReviewError(
            "ENVIRONMENT_QUALIFICATION_BOUNDARY_INVALID",
            "merged authorities no longer support the environment-qualification review",
        )

    return {
        "review_sha256": review.fingerprint(),
        "decision": review.decision,
        "lifecycle_after": review.lifecycle_after,
        "historical_authorization_reusable": False,
        "fresh_environment_capture_required": True,
        "qualification_assets_generated": review.safety.qualification_assets_generated,
        "gpu_execution_authorized": review.safety.gpu_execution_authorized,
        "worker_start_authorized": review.safety.worker_start_authorized,
        "measured_execution_authorized": review.safety.measured_execution_authorized,
        "external_spend": review.safety.external_spend,
        "next_gate": review.next_gate,
    }
