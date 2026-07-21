"""Review the bounded full-run environment-qualification execution package."""

from __future__ import annotations

import json
import re
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8"
REVIEW_ID: Final = (
    "auragateway-full-abc-local-full-run-environment-qualification-execution-review-v1"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_execution_review_v1.json"
)
NEXT_GATE: Final = "full_abc_local_full_run_environment_qualification_execution_implementation"

_IMPLEMENTATION_PLAN_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_implementation_v1.json"
)
_QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_request.json"
)
_WORKER_STARTUP_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
_IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification.py"
)
_IMPLEMENTATION_CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_contracts.py"
)

_EXPECTED_IMPLEMENTATION_PLAN_BLOB_SHA: Final = "0ad2e32b21a4578dbb241fdd6ce4ee733a61f982"
_EXPECTED_QUALIFICATION_REQUEST_BLOB_SHA: Final = "f545405a35bbb01e617c582c81fe32b89c605ed4"
_EXPECTED_WORKER_STARTUP_PLAN_BLOB_SHA: Final = "4729f9668e3c331185fd7c4f191d2e171f5ecad8"
_EXPECTED_IMPLEMENTATION_SOURCE_BLOB_SHA: Final = "59d1ce195b5cd32db3147c2956324513805b0ef9"
_EXPECTED_IMPLEMENTATION_CONTRACTS_BLOB_SHA: Final = "23fb4ad838cd918c953762af3fa896fa70f7f9ab"

_RUNTIME_EVIDENCE_PATHS: Final = (
    "data/evals/benchmark/environment-qualification-v1/cache_metric_capability_report.json",
    "data/evals/benchmark/environment-qualification-v1/gpu_topology_report.json",
    "data/evals/benchmark/environment-qualification-v1/kaggle_runtime_dependency_lock.json",
    "data/evals/benchmark/environment-qualification-v1/manifest.json",
    "data/evals/benchmark/environment-qualification-v1/model_identity_report.json",
    "data/evals/benchmark/environment-qualification-v1/qualification_report.json",
    "data/evals/benchmark/environment-qualification-v1/reset_capability_report.json",
    "data/evals/benchmark/environment-qualification-v1/worker_health_report.json",
)

_PACKAGE_ARTIFACTS: Final = (
    (
        "execution-contracts",
        "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py",
    ),
    (
        "execution-runner",
        "src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py",
    ),
    (
        "execution-tests",
        "tests/unit/local_abc/test_full_abc_local_environment_qualification_execution.py",
    ),
    (
        "kaggle-notebook",
        "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb",
    ),
    (
        "qualification-execution-request",
        "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json",
    ),
    (
        "qualification-runbook",
        "docs/runbooks/local_abc_full_run_environment_qualification_v1.md",
    ),
)

_SYNTHETIC_PROBE_IDS: Final = (
    "worker-1-cold-prefix",
    "worker-1-warm-prefix",
    "worker-2-cold-prefix",
    "worker-2-warm-prefix",
    "worker-1-post-reset-baseline",
    "worker-2-post-reset-baseline",
)


class FullABCLocalEnvironmentQualificationExecutionReviewError(RuntimeError):
    """Expected metadata-safe failure for the execution-review package."""

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


class ExecutionReviewAuthorityDisposition(StrEnum):
    """How one merged authority may influence the execution package."""

    CURRENT_AUTHORITY = "current_authority"
    HISTORICAL_CONTEXT_ONLY = "historical_context_only"


class ExecutionReviewAuthorityBinding(LocalABCContract):
    """One exact Git authority for this review."""

    binding_id: str
    role: str = Field(min_length=8, max_length=200)
    source_locator: str
    git_blob_sha: str
    disposition: ExecutionReviewAuthorityDisposition
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


class ExecutionPackageArtifact(LocalABCContract):
    """One static artifact permitted in the next implementation gate."""

    artifact_id: str
    path: str
    generation_stage: Literal["execution_implementation"]
    execution_performed: Literal[False] = False

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("package artifact IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("package artifact paths must remain bounded")
        return value


class QualificationProbeBudget(LocalABCContract):
    """Finite synthetic request budget for eventual qualification execution."""

    maximum_kaggle_sessions: Literal[1] = 1
    maximum_workers: Literal[2] = 2
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    synthetic_probe_ids: tuple[str, ...]
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    benchmark_episode_payloads_permitted: Literal[False] = False
    customer_payloads_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False

    @field_validator("synthetic_probe_ids")
    @classmethod
    def validate_probe_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _SYNTHETIC_PROBE_IDS:
            raise ValueError("synthetic qualification probe IDs drifted")
        return value


class QualificationDatasetBoundary(LocalABCContract):
    """Offline-only data and package boundary for the eventual Kaggle run."""

    network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    hosted_provider_calls_permitted: Literal[False] = False
    exact_dataset_manifest_required: Literal[True] = True
    local_model_artifacts_required: Literal[True] = True
    local_vllm_wheel_required: Literal[True] = True
    network_package_install_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    external_spend: Literal[0] = 0


class QualificationRuntimeEvidenceContract(LocalABCContract):
    """Exact runtime evidence required from one fresh qualification session."""

    required_paths: tuple[str, ...]
    same_runtime_session_required: Literal[True] = True
    partial_bundle_qualification_permitted: Literal[False] = False
    missing_metric_state: Literal["UNAVAILABLE_NOT_ZERO"]
    zero_fill_for_missing_metrics_permitted: Literal[False] = False
    latency_only_cache_inference_permitted: Literal[False] = False
    evidence_written_only_after_validation: Literal[True] = True

    @field_validator("required_paths")
    @classmethod
    def validate_required_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _RUNTIME_EVIDENCE_PATHS:
            raise ValueError("runtime evidence path set drifted")
        return value


class QualificationExecutionControls(LocalABCContract):
    """Fail-closed controls for implementation and eventual execution."""

    implementation_may_create_notebook: Literal[True] = True
    implementation_may_create_execution_runner: Literal[True] = True
    implementation_may_create_runtime_evidence_schemas: Literal[True] = True
    implementation_may_start_kaggle: Literal[False] = False
    implementation_may_enable_gpu: Literal[False] = False
    implementation_may_start_workers: Literal[False] = False
    implementation_may_invoke_model: Literal[False] = False
    implementation_may_generate_runtime_evidence: Literal[False] = False
    implementation_may_claim_environment_qualified: Literal[False] = False
    execution_requires_separate_authorization_review: Literal[True] = True
    execution_authorization_next_gate: Literal[
        "full_abc_local_full_run_environment_qualification_execution_authorization_review"
    ]


class QualificationExecutionReviewSafetyEnvelope(LocalABCContract):
    """Review-only safety state; no environment activity is performed."""

    execution_package_generated: Literal[False] = False
    notebook_created: Literal[False] = False
    notebook_execution_performed: Literal[False] = False
    kaggle_session_started: Literal[False] = False
    dataset_attached: Literal[False] = False
    package_installation_performed: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    worker_start_authorized: Literal[False] = False
    worker_started: Literal[False] = False
    model_execution_performed: Literal[False] = False
    runtime_evidence_generated: Literal[False] = False
    environment_qualified: Literal[False] = False
    credential_accessed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False


class FullABCLocalEnvironmentQualificationExecutionReview(LocalABCContract):
    """Review authorizing implementation of a bounded qualification package."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-full-abc-local-full-run-environment-qualification-execution-review-v1"
    ]
    source_main_merge_commit: Literal["3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8"]
    lifecycle_before: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    lifecycle_after: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    decision: Literal["APPROVED_FOR_QUALIFICATION_EXECUTION_IMPLEMENTATION"]
    authority_bindings: tuple[ExecutionReviewAuthorityBinding, ...]
    package_artifacts: tuple[ExecutionPackageArtifact, ...]
    probe_budget: QualificationProbeBudget
    dataset_boundary: QualificationDatasetBoundary
    runtime_evidence: QualificationRuntimeEvidenceContract
    execution_controls: QualificationExecutionControls
    safety: QualificationExecutionReviewSafetyEnvelope
    next_gate: Literal["full_abc_local_full_run_environment_qualification_execution_implementation"]

    @field_validator("authority_bindings")
    @classmethod
    def validate_authority_bindings(
        cls,
        value: tuple[ExecutionReviewAuthorityBinding, ...],
    ) -> tuple[ExecutionReviewAuthorityBinding, ...]:
        identifiers = tuple(item.binding_id for item in value)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("authority binding IDs must be unique")
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("authority bindings must be canonically sorted")
        return value

    @field_validator("package_artifacts")
    @classmethod
    def validate_package_artifacts(
        cls,
        value: tuple[ExecutionPackageArtifact, ...],
    ) -> tuple[ExecutionPackageArtifact, ...]:
        identifiers = tuple(item.artifact_id for item in value)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("execution package artifact IDs must be unique")
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("execution package artifacts must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_review_boundary(self) -> Self:
        if self.probe_budget.maximum_model_requests < len(self.probe_budget.synthetic_probe_ids):
            raise ValueError("request budget cannot be smaller than the required probe set")
        if self.safety.environment_qualified:
            raise ValueError("execution review cannot claim environment qualification")
        if self.execution_controls.implementation_may_start_kaggle:
            raise ValueError("implementation gate cannot start Kaggle")
        return self


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_JSON_AUTHORITY_UNREADABLE",
            "required qualification-execution authority could not be read",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_JSON_AUTHORITY_INVALID",
            "required qualification-execution authority must be one JSON object",
            path.as_posix(),
        )
    return payload


def _git_blob_sha_at_revision(
    repo_root: Path,
    relative_path: Path,
    revision: str,
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                f"{revision}:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_HISTORICAL_GIT_AUTHORITY_UNREADABLE",
            "required historical qualification-execution authority could not be resolved",
            relative_path.as_posix(),
            details=(revision,),
        ) from exc
    identity = result.stdout.strip()
    if _GIT_OBJECT_PATTERN.fullmatch(identity) is None:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_HISTORICAL_GIT_AUTHORITY_INVALID",
            "historical qualification-execution authority returned an invalid identity",
            relative_path.as_posix(),
            details=(revision,),
        )
    return identity


def _git_text_at_revision(
    repo_root: Path,
    relative_path: Path,
    revision: str,
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "show",
                f"{revision}:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_HISTORICAL_FILE_UNREADABLE",
            "required historical qualification-execution file could not be read",
            relative_path.as_posix(),
            details=(revision,),
        ) from exc
    return result.stdout


def _load_json_object_at_revision(
    repo_root: Path,
    relative_path: Path,
    revision: str,
) -> dict[str, object]:
    try:
        payload = json.loads(
            _git_text_at_revision(
                repo_root,
                relative_path,
                revision,
            )
        )
    except json.JSONDecodeError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_HISTORICAL_JSON_AUTHORITY_INVALID",
            "historical qualification-execution authority is not valid JSON",
            relative_path.as_posix(),
            details=(revision,),
        ) from exc
    if not isinstance(payload, dict):
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "REQUIRED_HISTORICAL_JSON_AUTHORITY_INVALID",
            "historical qualification-execution authority must be one JSON object",
            relative_path.as_posix(),
            details=(revision,),
        )
    return payload


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
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 102 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def build_default_review() -> FullABCLocalEnvironmentQualificationExecutionReview:
    """Build the execution review without creating or running the package."""

    authority_rows = (
        (
            "implementation-contracts",
            "typed static qualification contracts",
            _IMPLEMENTATION_CONTRACTS_PATH,
            _EXPECTED_IMPLEMENTATION_CONTRACTS_BLOB_SHA,
        ),
        (
            "implementation-plan",
            "merged static qualification implementation decision",
            _IMPLEMENTATION_PLAN_PATH,
            _EXPECTED_IMPLEMENTATION_PLAN_BLOB_SHA,
        ),
        (
            "implementation-source",
            "static qualification generator and verifier",
            _IMPLEMENTATION_SOURCE_PATH,
            _EXPECTED_IMPLEMENTATION_SOURCE_BLOB_SHA,
        ),
        (
            "qualification-request",
            "frozen request for fresh full-run environment qualification",
            _QUALIFICATION_REQUEST_PATH,
            _EXPECTED_QUALIFICATION_REQUEST_BLOB_SHA,
        ),
        (
            "worker-startup-plan",
            "canonical non-executed two-worker startup plan",
            _WORKER_STARTUP_PLAN_PATH,
            _EXPECTED_WORKER_STARTUP_PLAN_BLOB_SHA,
        ),
    )
    authorities = tuple(
        ExecutionReviewAuthorityBinding(
            binding_id=binding_id,
            role=role,
            source_locator=path.as_posix(),
            git_blob_sha=blob_sha,
            disposition=ExecutionReviewAuthorityDisposition.CURRENT_AUTHORITY,
            notes="Current merged authority; exact Git identity is required.",
        )
        for binding_id, role, path, blob_sha in authority_rows
    )

    package_artifacts = tuple(
        sorted(
            (
                ExecutionPackageArtifact(
                    artifact_id=artifact_id,
                    path=path,
                    generation_stage="execution_implementation",
                )
                for artifact_id, path in _PACKAGE_ARTIFACTS
            ),
            key=lambda item: item.artifact_id,
        )
    )

    return FullABCLocalEnvironmentQualificationExecutionReview(
        review_id=REVIEW_ID,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        decision="APPROVED_FOR_QUALIFICATION_EXECUTION_IMPLEMENTATION",
        authority_bindings=authorities,
        package_artifacts=package_artifacts,
        probe_budget=QualificationProbeBudget(
            synthetic_probe_ids=_SYNTHETIC_PROBE_IDS,
        ),
        dataset_boundary=QualificationDatasetBoundary(),
        runtime_evidence=QualificationRuntimeEvidenceContract(
            required_paths=_RUNTIME_EVIDENCE_PATHS,
            missing_metric_state="UNAVAILABLE_NOT_ZERO",
        ),
        execution_controls=QualificationExecutionControls(
            execution_authorization_next_gate=(
                "full_abc_local_full_run_environment_qualification_execution_authorization_review"
            ),
        ),
        safety=QualificationExecutionReviewSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def load_full_abc_local_environment_qualification_execution_review(
    path: Path,
) -> FullABCLocalEnvironmentQualificationExecutionReview:
    """Load the canonical execution-review artifact."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "QUALIFICATION_EXECUTION_REVIEW_INVALID",
            "the qualification-execution review artifact is missing or invalid",
            path.as_posix(),
        ) from exc


def write_default_review(
    path: Path,
) -> FullABCLocalEnvironmentQualificationExecutionReview:
    """Write only the review artifact; do not build or execute the package."""

    review = build_default_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.canonical_json(), encoding="utf-8", newline="\n")
    return review


def validate_repository_review_package(repo_root: Path) -> dict[str, object]:
    """Validate historical authorities and return a metadata-safe review summary."""

    _require_source_ancestor(repo_root)
    review = load_full_abc_local_environment_qualification_execution_review(repo_root / REVIEW_PATH)
    expected = {
        _IMPLEMENTATION_PLAN_PATH: _EXPECTED_IMPLEMENTATION_PLAN_BLOB_SHA,
        _QUALIFICATION_REQUEST_PATH: _EXPECTED_QUALIFICATION_REQUEST_BLOB_SHA,
        _WORKER_STARTUP_PLAN_PATH: _EXPECTED_WORKER_STARTUP_PLAN_BLOB_SHA,
        _IMPLEMENTATION_SOURCE_PATH: _EXPECTED_IMPLEMENTATION_SOURCE_BLOB_SHA,
        _IMPLEMENTATION_CONTRACTS_PATH: _EXPECTED_IMPLEMENTATION_CONTRACTS_BLOB_SHA,
    }
    drift = tuple(
        sorted(
            path.as_posix()
            for path, blob_sha in expected.items()
            if (
                _git_blob_sha_at_revision(
                    repo_root,
                    path,
                    SOURCE_MAIN_MERGE_COMMIT,
                )
                != blob_sha
            )
        )
    )
    if drift:
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "QUALIFICATION_EXECUTION_HISTORICAL_AUTHORITY_DRIFT",
            "one or more historical qualification-execution authorities drifted",
            details=drift,
        )

    implementation = _load_json_object_at_revision(
        repo_root,
        _IMPLEMENTATION_PLAN_PATH,
        SOURCE_MAIN_MERGE_COMMIT,
    )
    request = _load_json_object_at_revision(
        repo_root,
        _QUALIFICATION_REQUEST_PATH,
        SOURCE_MAIN_MERGE_COMMIT,
    )
    startup = _load_json_object_at_revision(
        repo_root,
        _WORKER_STARTUP_PLAN_PATH,
        SOURCE_MAIN_MERGE_COMMIT,
    )
    checks = (
        implementation.get("next_gate")
        == "full_abc_local_full_run_environment_qualification_execution_review",
        implementation.get("execution_enabled") is False,
        implementation.get("qualification_claim_permitted") is False,
        request.get("planned_trajectory_count") == 342,
        request.get("fresh_runtime_session_required") is True,
        request.get("historical_authorization_reusable") is False,
        startup.get("launch_authorized") is False,
        startup.get("historical_runtime_versions_reusable") is False,
        startup.get("status") == "STATIC_PLAN_NOT_EXECUTED",
    )
    if not all(checks):
        raise FullABCLocalEnvironmentQualificationExecutionReviewError(
            "QUALIFICATION_EXECUTION_BOUNDARY_INVALID",
            "merged authorities no longer support the bounded execution review",
        )

    return {
        "review_sha256": review.fingerprint(),
        "review_disposition": "HISTORICAL_CONTEXT_ONLY",
        "historical_revision": SOURCE_MAIN_MERGE_COMMIT,
        "historical_authorities_verified": len(expected),
        "decision": review.decision,
        "lifecycle_after": review.lifecycle_after,
        "maximum_model_requests": review.probe_budget.maximum_model_requests,
        "benchmark_trajectory_requests_permitted": (
            review.probe_budget.benchmark_trajectory_requests_permitted
        ),
        "implementation_may_start_kaggle": (
            review.execution_controls.implementation_may_start_kaggle
        ),
        "runtime_evidence_generated": review.safety.runtime_evidence_generated,
        "environment_qualified": review.safety.environment_qualified,
        "measured_execution_authorized": review.safety.measured_execution_authorized,
        "external_spend": review.safety.external_spend,
        "next_gate": review.next_gate,
    }
