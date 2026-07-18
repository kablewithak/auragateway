"""Review the authorization-package boundary for offline environment qualification."""

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
_FACTORY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{2,199}:[A-Za-z_][A-Za-z0-9_]{1,79}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "768e0535d8d373385440acc2dc18952b4fc42325"
REVIEW_ID: Final = (
    "auragateway-full-abc-local-environment-qualification-execution-authorization-review-v1"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_review_v1.json"
)
NEXT_GATE: Final = (
    "full_abc_local_full_run_environment_qualification_execution_authorization_implementation"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

_EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
_EXECUTION_RUNNER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py"
)
_EXECUTION_CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
)
_EXECUTION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
)
_EXECUTION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_v1.md"
)

_EXPECTED_EXECUTION_REQUEST_BLOB_SHA: Final = "38733262351846442ee55828a136e42016a7f54e"
_EXPECTED_EXECUTION_RUNNER_BLOB_SHA: Final = "921b5dcff84880f1c0e02bbc1164a7c73567d1fb"
_EXPECTED_EXECUTION_CONTRACTS_BLOB_SHA: Final = "a82423c9cd5739d0d47e128bb5ce74493952ceb7"
_EXPECTED_EXECUTION_NOTEBOOK_BLOB_SHA: Final = "b154168dcc300243b80cdf2fb4104d311195176e"
_EXPECTED_EXECUTION_RUNBOOK_BLOB_SHA: Final = "181a9bfb9a8984716f734389881477f8bee58e69"

_REQUIRED_DATASET_ROLES: Final = (
    "harness_source",
    "model_artifacts",
    "vllm_wheel",
)

_IMPLEMENTATION_ARTIFACTS: Final = (
    (
        "authorization-contracts",
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization_contracts.py",
    ),
    (
        "authorization-runner",
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization.py",
    ),
    (
        "authorization-tests",
        "tests/unit/local_abc/"
        "test_full_abc_local_environment_qualification_execution_authorization.py",
    ),
    (
        "authorization-request",
        "data/evals/benchmark/environment-qualification-v1/"
        "qualification_authorization_request.json",
    ),
    (
        "dataset-manifest-request",
        "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest_request.json",
    ),
    (
        "kaggle-runtime-adapter",
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_kaggle_runtime_adapter.py",
    ),
    (
        "authorization-runbook",
        "docs/runbooks/local_abc_full_run_environment_qualification_authorization_v1.md",
    ),
)

_RUNTIME_FACTORY_PATH: Final = (
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_kaggle_runtime_adapter:"
    "create_runtime_adapter"
)


class AuthorizationReviewError(RuntimeError):
    """Expected metadata-safe failure for the authorization review package."""

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
    """How one merged artifact governs authorization implementation."""

    CURRENT_AUTHORITY = "current_authority"


class AuthorityBinding(LocalABCContract):
    """One exact merged authority for the authorization-package review."""

    binding_id: str
    role: str = Field(min_length=8, max_length=200)
    source_locator: str
    git_blob_sha: str
    disposition: Literal[AuthorityDisposition.CURRENT_AUTHORITY]

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


class AuthorizationImplementationArtifact(LocalABCContract):
    """One static file permitted in the authorization implementation gate."""

    artifact_id: str
    path: str
    generation_stage: Literal["authorization_implementation"]
    operational_authority_created: Literal[False] = False

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation artifact IDs must use stable lowercase characters")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("implementation artifact paths must remain bounded")
        return value


class OfflineDatasetMaterializationDecision(LocalABCContract):
    """Requirements for producing exact offline Kaggle inputs later."""

    required_roles: tuple[str, ...]
    exact_dataset_slug_required: Literal[True] = True
    exact_dataset_version_required: Literal[True] = True
    exact_mounted_path_required: Literal[True] = True
    exact_sha256_required: Literal[True] = True
    source_main_commit_must_follow_implementation_merge: Literal[True] = True
    network_fallback_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    hosted_provider_inputs_permitted: Literal[False] = False
    materialization_performed_in_this_review: Literal[False] = False

    @field_validator("required_roles")
    @classmethod
    def validate_required_roles(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_DATASET_ROLES:
            raise ValueError("offline dataset roles drifted")
        return value


class RuntimeAdapterDecision(LocalABCContract):
    """Static runtime adapter boundary without execution authority."""

    factory_path: str
    artifact_path: str
    artifact_sha256_required: Literal[True] = True
    typed_protocol_required: Literal[True] = True
    loopback_only: Literal[True] = True
    frozen_startup_argv_required: Literal[True] = True
    network_access_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    adapter_created_in_this_review: Literal[False] = False

    @field_validator("factory_path")
    @classmethod
    def validate_factory_path(cls, value: str) -> str:
        if _FACTORY_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime factory path must use module:function syntax")
        return value

    @field_validator("artifact_path")
    @classmethod
    def validate_artifact_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("runtime adapter path must remain repository bounded")
        return value


class AuthorizationIssuanceDecision(LocalABCContract):
    """Conditions that must hold before final operational authority can exist."""

    final_authorization_path: str
    final_authorization_generated: Literal[False] = False
    issuance_requires_separate_review: Literal[True] = True
    operator_confirmation_required: Literal[True] = True
    maximum_authorization_window_minutes: Literal[240] = 240
    request_sha256_required: Literal[True] = True
    dataset_manifest_sha256_required: Literal[True] = True
    runtime_adapter_sha256_required: Literal[True] = True
    review_git_blob_sha_required: Literal[True] = True
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_model_requests: Literal[8] = 8
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0
    next_gate_after_implementation: Literal[
        "full_abc_local_full_run_environment_qualification_execution_authorization_issuance_review"
    ]

    @field_validator("final_authorization_path")
    @classmethod
    def validate_final_authorization_path(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("final authorization path must remain bounded")
        return value


class AuthorizationReviewSafetyEnvelope(LocalABCContract):
    """Review-only state with all operational activity prohibited."""

    authorization_package_generated: Literal[False] = False
    final_authorization_generated: Literal[False] = False
    dataset_manifest_generated: Literal[False] = False
    runtime_adapter_generated: Literal[False] = False
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
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False


class FullABCLocalEnvironmentQualificationAuthorizationReview(LocalABCContract):
    """Review authorizing implementation, not issuance, of operational authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-full-abc-local-environment-qualification-execution-authorization-review-v1"
    ]
    source_main_merge_commit: Literal["768e0535d8d373385440acc2dc18952b4fc42325"]
    lifecycle_before: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    lifecycle_after: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    decision: Literal["APPROVED_FOR_AUTHORIZATION_PACKAGE_IMPLEMENTATION"]
    authority_bindings: tuple[AuthorityBinding, ...]
    implementation_artifacts: tuple[AuthorizationImplementationArtifact, ...]
    dataset_materialization: OfflineDatasetMaterializationDecision
    runtime_adapter: RuntimeAdapterDecision
    authorization_issuance: AuthorizationIssuanceDecision
    safety: AuthorizationReviewSafetyEnvelope
    next_gate: Literal[
        "full_abc_local_full_run_environment_qualification_execution_authorization_implementation"
    ]

    @field_validator("authority_bindings")
    @classmethod
    def validate_authority_bindings(
        cls,
        value: tuple[AuthorityBinding, ...],
    ) -> tuple[AuthorityBinding, ...]:
        identifiers = tuple(item.binding_id for item in value)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("authority binding IDs must be unique")
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("authority bindings must be canonically sorted")
        return value

    @field_validator("implementation_artifacts")
    @classmethod
    def validate_implementation_artifacts(
        cls,
        value: tuple[AuthorizationImplementationArtifact, ...],
    ) -> tuple[AuthorizationImplementationArtifact, ...]:
        identifiers = tuple(item.artifact_id for item in value)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("implementation artifact IDs must be unique")
        if identifiers != tuple(sorted(identifiers)):
            raise ValueError("implementation artifacts must be canonically sorted")
        expected_paths = tuple(path for _, path in sorted(_IMPLEMENTATION_ARTIFACTS))
        if tuple(item.path for item in value) != expected_paths:
            raise ValueError("authorization implementation artifact paths drifted")
        return value

    @model_validator(mode="after")
    def validate_review_boundary(self) -> Self:
        if self.safety.final_authorization_generated:
            raise ValueError("authorization review cannot generate operational authority")
        if self.authorization_issuance.final_authorization_generated:
            raise ValueError("authorization issuance must remain deferred")
        return self


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationReviewError(
            "REQUIRED_JSON_AUTHORITY_UNREADABLE",
            "required authorization-review authority could not be read",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationReviewError(
            "REQUIRED_JSON_AUTHORITY_INVALID",
            "required authorization-review authority must be one JSON object",
            path.as_posix(),
        )
    return payload


def _git_blob_sha(repo_root: Path, relative_path: Path) -> str:
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
        raise AuthorizationReviewError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required authorization-review Git authority could not be resolved",
            relative_path.as_posix(),
        ) from exc
    identity = result.stdout.strip()
    if _GIT_OBJECT_PATTERN.fullmatch(identity) is None:
        raise AuthorizationReviewError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required authorization-review Git authority returned an invalid identity",
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
        raise AuthorizationReviewError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise AuthorizationReviewError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 104 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def build_default_review() -> FullABCLocalEnvironmentQualificationAuthorizationReview:
    """Build the authorization-package review without issuing operational authority."""

    authorities = tuple(
        sorted(
            (
                AuthorityBinding(
                    binding_id="execution-contracts",
                    role="typed authorization-gated execution and evidence contracts",
                    source_locator=_EXECUTION_CONTRACTS_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_EXECUTION_CONTRACTS_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                ),
                AuthorityBinding(
                    binding_id="execution-notebook",
                    role="deterministic unexecuted Kaggle qualification surface",
                    source_locator=_EXECUTION_NOTEBOOK_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_EXECUTION_NOTEBOOK_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                ),
                AuthorityBinding(
                    binding_id="execution-request",
                    role="canonical qualification execution request and hard budget",
                    source_locator=_EXECUTION_REQUEST_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_EXECUTION_REQUEST_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                ),
                AuthorityBinding(
                    binding_id="execution-runbook",
                    role="operator sequence and hard-stop procedure",
                    source_locator=_EXECUTION_RUNBOOK_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_EXECUTION_RUNBOOK_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                ),
                AuthorityBinding(
                    binding_id="execution-runner",
                    role="authorization-gated execution and transactional evidence harness",
                    source_locator=_EXECUTION_RUNNER_PATH.as_posix(),
                    git_blob_sha=_EXPECTED_EXECUTION_RUNNER_BLOB_SHA,
                    disposition=AuthorityDisposition.CURRENT_AUTHORITY,
                ),
            ),
            key=lambda item: item.binding_id,
        )
    )
    artifacts = tuple(
        AuthorizationImplementationArtifact(
            artifact_id=artifact_id,
            path=path,
            generation_stage="authorization_implementation",
        )
        for artifact_id, path in sorted(_IMPLEMENTATION_ARTIFACTS)
    )
    return FullABCLocalEnvironmentQualificationAuthorizationReview(
        review_id=REVIEW_ID,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        decision="APPROVED_FOR_AUTHORIZATION_PACKAGE_IMPLEMENTATION",
        authority_bindings=authorities,
        implementation_artifacts=artifacts,
        dataset_materialization=OfflineDatasetMaterializationDecision(
            required_roles=_REQUIRED_DATASET_ROLES,
        ),
        runtime_adapter=RuntimeAdapterDecision(
            factory_path=_RUNTIME_FACTORY_PATH,
            artifact_path=(
                "src/auragateway/local_abc/"
                "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
            ),
        ),
        authorization_issuance=AuthorizationIssuanceDecision(
            final_authorization_path=FINAL_AUTHORIZATION_PATH.as_posix(),
            next_gate_after_implementation=(
                "full_abc_local_full_run_environment_qualification_"
                "execution_authorization_issuance_review"
            ),
        ),
        safety=AuthorizationReviewSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def load_review(path: Path) -> FullABCLocalEnvironmentQualificationAuthorizationReview:
    """Load the canonical review artifact with metadata-safe failures."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise AuthorizationReviewError(
            "AUTHORIZATION_REVIEW_INVALID",
            "the authorization review artifact is missing or invalid",
            path.as_posix(),
        ) from exc


def write_default_review(
    path: Path,
) -> FullABCLocalEnvironmentQualificationAuthorizationReview:
    """Write only the review artifact; do not create authorization inputs."""

    review = build_default_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.canonical_json(), encoding="utf-8", newline="\n")
    return review


def validate_repository_review_package(repo_root: Path) -> dict[str, object]:
    """Validate exact PR 104 authorities and return a safe review summary."""

    _require_source_ancestor(repo_root)
    review = load_review(repo_root / REVIEW_PATH)
    expected_blobs = {
        _EXECUTION_REQUEST_PATH: _EXPECTED_EXECUTION_REQUEST_BLOB_SHA,
        _EXECUTION_RUNNER_PATH: _EXPECTED_EXECUTION_RUNNER_BLOB_SHA,
        _EXECUTION_CONTRACTS_PATH: _EXPECTED_EXECUTION_CONTRACTS_BLOB_SHA,
        _EXECUTION_NOTEBOOK_PATH: _EXPECTED_EXECUTION_NOTEBOOK_BLOB_SHA,
        _EXECUTION_RUNBOOK_PATH: _EXPECTED_EXECUTION_RUNBOOK_BLOB_SHA,
    }
    drift = tuple(
        sorted(
            path.as_posix()
            for path, expected in expected_blobs.items()
            if _git_blob_sha(repo_root, path) != expected
        )
    )
    if drift:
        raise AuthorizationReviewError(
            "AUTHORIZATION_REVIEW_AUTHORITY_DRIFT",
            "one or more authorization-review authorities drifted",
            details=drift,
        )

    request = _load_json_object(repo_root / _EXECUTION_REQUEST_PATH)
    notebook = _load_json_object(repo_root / _EXECUTION_NOTEBOOK_PATH)
    checks = [
        request.get("next_gate")
        == "full_abc_local_full_run_environment_qualification_execution_authorization_review",
        request.get("status") == "STATIC_PACKAGE_GENERATED_AUTHORIZATION_BLOCKED",
        request.get("planned_trajectory_count") == 342,
        request.get("runtime_factory_binding_required") is True,
    ]
    probe_budget = request.get("probe_budget")
    if isinstance(probe_budget, dict):
        checks.extend(
            (
                probe_budget.get("maximum_kaggle_sessions") == 1,
                probe_budget.get("maximum_model_requests") == 8,
                probe_budget.get("maximum_output_tokens_per_request") == 32,
                probe_budget.get("benchmark_trajectory_requests_permitted") == 0,
                probe_budget.get("hidden_retries_permitted") is False,
            )
        )
    else:
        checks.append(False)

    metadata = notebook.get("metadata")
    cells = notebook.get("cells")
    if isinstance(metadata, dict) and isinstance(cells, list):
        aura_metadata = metadata.get("auragateway")
        code_cells = [cell for cell in cells if isinstance(cell, dict)]
        checks.extend(
            (
                isinstance(aura_metadata, dict),
                all(cell.get("execution_count") is None for cell in code_cells),
                all(cell.get("outputs", []) == [] for cell in code_cells),
            )
        )
        if isinstance(aura_metadata, dict):
            checks.extend(
                (
                    aura_metadata.get("execution_authorized") is False,
                    aura_metadata.get("benchmark_trajectory_requests_permitted") == 0,
                )
            )
    else:
        checks.append(False)

    if not all(checks):
        raise AuthorizationReviewError(
            "AUTHORIZATION_REVIEW_BOUNDARY_INVALID",
            "merged authorities no longer support authorization-package implementation",
        )
    if (repo_root / FINAL_AUTHORIZATION_PATH).exists():
        raise AuthorizationReviewError(
            "PREMATURE_FINAL_AUTHORIZATION_PRESENT",
            "final operational authorization appeared before its issuance review",
            FINAL_AUTHORIZATION_PATH.as_posix(),
        )

    return {
        "review_sha256": review.fingerprint(),
        "decision": review.decision,
        "lifecycle_after": review.lifecycle_after,
        "implementation_artifact_count": len(review.implementation_artifacts),
        "final_authorization_generated": False,
        "dataset_materialization_performed": False,
        "runtime_adapter_generated": False,
        "kaggle_session_started": False,
        "maximum_model_requests": 8,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
        "next_gate": review.next_gate,
    }
