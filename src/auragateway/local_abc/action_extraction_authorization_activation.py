"""Fresh one-shot authorization activation for action-extraction requalification v2."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.action_extraction_authorization import (
    ActionExtractionDecodingPolicy,
    ActionExtractionModelBinding,
    ActionExtractionRuntimeBinding,
)
from auragateway.local_abc.action_extraction_authorization_review import (
    ActionExtractionAuthorizationReviewPackageV2,
    ActionExtractionCandidateEvidenceContract,
    ActionExtractionCandidateStopPolicy,
    load_action_extraction_authorization_review_package_v2,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")

_PR87_MERGE_COMMIT: Final = "6038f7055e34c6c559b3c41cb919d0cb421b3e55"
_REVIEW_SOURCE_BLOB_SHA: Final = "08a6dcd74ef6b569dc8e7de23cb1f7806e5350bc"
_REVIEW_JSON_BLOB_SHA: Final = "2982e1962825bf774cd092a3760d761d699b1ccf"
_DRY_RUN_JSON_BLOB_SHA: Final = "333ad82078a128eebf3b570636c08f7eaa45d6ef"
_REVIEW_MANIFEST_BLOB_SHA: Final = "afd97a0d1acad659db8dacfce42f8a5eb16b8890"
_REVIEW_SHA256: Final = "66539ccadbebee9ad6227b8d861da8bfa1f0e89fdd69883e91f49b15819c99a9"
_DRY_RUN_SHA256: Final = "207abb6746277b1f6bc4ca79d537de3623f06d66ca5fa8600ee391af45acf508"
_REVIEW_MANIFEST_SHA256: Final = "8299da7aaba1ed886d5bf85b9ee59c2471e79f735b1f37d66b9b8c3c806eee2d"
_EXPECTED_CASE_COUNT: Final = 16


class ActionExtractionActivationStatus(StrEnum):
    """Lifecycle state for the fresh authorization."""

    ACTIVE_UNUSED = "active_unused"


class ActionExtractionActivationDecision(StrEnum):
    """Bounded authorization decision."""

    AUTHORIZED_FOR_QUALIFIED_NOTEBOOK_GENERATION = "authorized_for_qualified_notebook_generation"


class ActionExtractionActivationSourceBinding(LocalABCContract):
    """Exact merged PR #87 source or artifact binding."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    path: str
    git_blob_sha: str
    canonical_sha256: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("activation binding path must be repository-relative")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_git_blob_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("activation source blob must be a full lowercase Git SHA")
        return value

    @field_validator("canonical_sha256")
    @classmethod
    def validate_canonical_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation artifact digest must be lowercase SHA-256")
        return value


class ActionExtractionAuthorizationActivationV2(LocalABCContract):
    """One fresh authorization with notebook binding required before execution."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    authorization_id: Literal[
        "reconcile-balance-action-extraction-requalification-authorization-v2"
    ] = "reconcile-balance-action-extraction-requalification-authorization-v2"
    issued_at: datetime
    status: Literal[ActionExtractionActivationStatus.ACTIVE_UNUSED] = (
        ActionExtractionActivationStatus.ACTIVE_UNUSED
    )
    decision: Literal[
        ActionExtractionActivationDecision.AUTHORIZED_FOR_QUALIFIED_NOTEBOOK_GENERATION
    ] = ActionExtractionActivationDecision.AUTHORIZED_FOR_QUALIFIED_NOTEBOOK_GENERATION
    repository: Literal["kablewithak/auragateway"] = "kablewithak/auragateway"
    source_merge_commit: Literal["6038f7055e34c6c559b3c41cb919d0cb421b3e55"] = _PR87_MERGE_COMMIT
    source_bindings: tuple[ActionExtractionActivationSourceBinding, ...] = Field(
        min_length=4,
        max_length=4,
    )
    review_id: Literal["reconcile-balance-action-extraction-authorization-review-v2"] = (
        "reconcile-balance-action-extraction-authorization-review-v2"
    )
    review_sha256: str
    dry_run_sha256: str
    review_manifest_sha256: str
    remediation_manifest_sha256: str
    remediation_plan_sha256: str
    normalization_policy_sha256: str
    prompt_policy_sha256: str
    response_schema_sha256: str
    action_schema_sha256: str
    case_count: Literal[16] = 16
    selected_case_ids: tuple[str, ...] = Field(min_length=16, max_length=16)
    required_exact_operand_matches: Literal[16] = 16
    required_exact_final_answer_matches: Literal[16] = 16
    complete_suite_required: Literal[True] = True
    model: ActionExtractionModelBinding = ActionExtractionModelBinding()
    runtime: ActionExtractionRuntimeBinding = ActionExtractionRuntimeBinding()
    decoding: ActionExtractionDecodingPolicy = ActionExtractionDecodingPolicy()
    stop_policy: ActionExtractionCandidateStopPolicy = ActionExtractionCandidateStopPolicy()
    evidence: ActionExtractionCandidateEvidenceContract = (
        ActionExtractionCandidateEvidenceContract()
    )
    prior_authorization_consumed: Literal[True] = True
    prior_authorization_reuse_permitted: Literal[False] = False
    authorization_consumed: Literal[False] = False
    authorization_reuse_after_execution_permitted: Literal[False] = False
    authorization_merge_commit_binding_required: Literal[True] = True
    notebook_sha256_binding_required: Literal[True] = True
    notebook_generation_permitted_after_merge: Literal[True] = True
    notebook_execution_permitted_before_binding: Literal[False] = False
    gpu_enablement_permitted_before_qualified_notebook: Literal[False] = False
    bounded_gpu_execution_permitted_after_qualified_notebook: Literal[True] = True
    active_authorization_created: Literal[True] = True
    execution_authorized: Literal[True] = True
    execution_command_available: Literal[False] = False
    provider_call_performed: Literal[False] = False
    model_request_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    failed_case_only_execution_permitted: Literal[False] = False
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Literal[0] = 0
    customer_data_used: Literal[False] = False
    synthetic_data_only: Literal[True] = True
    worker_id: Literal["worker_1"] = "worker_1"
    next_gate: Literal["qualified_action_extraction_v2_notebook_generation"] = (
        "qualified_action_extraction_v2_notebook_generation"
    )

    @field_validator("authorization_id")
    @classmethod
    def validate_authorization_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization ID must use stable lowercase characters")
        return value

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator("source_merge_commit")
    @classmethod
    def validate_source_merge_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("activation source commit must be a full lowercase Git SHA")
        return value

    @field_validator(
        "review_sha256",
        "dry_run_sha256",
        "review_manifest_sha256",
        "remediation_manifest_sha256",
        "remediation_plan_sha256",
        "normalization_policy_sha256",
        "prompt_policy_sha256",
        "response_schema_sha256",
        "action_schema_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_activation(self) -> Self:
        paths = tuple(binding.path for binding in self.source_bindings)
        duplicates = tuple(path for path, count in Counter(paths).items() if count > 1)
        if duplicates:
            raise ValueError("activation source binding paths must be unique")
        expected_bindings = (
            (
                "src/auragateway/local_abc/action_extraction_authorization_review.py",
                _REVIEW_SOURCE_BLOB_SHA,
                None,
            ),
            (
                "benchmarks/local_abc/reconcile_balance_extraction_authorization_review_v2.json",
                _REVIEW_JSON_BLOB_SHA,
                _REVIEW_SHA256,
            ),
            (
                "benchmarks/local_abc/reconcile_balance_extraction_authorization_dry_run_v2.json",
                _DRY_RUN_JSON_BLOB_SHA,
                _DRY_RUN_SHA256,
            ),
            (
                "benchmarks/local_abc/"
                "reconcile_balance_extraction_authorization_review_manifest_v2.json",
                _REVIEW_MANIFEST_BLOB_SHA,
                _REVIEW_MANIFEST_SHA256,
            ),
        )
        observed_bindings = tuple(
            (binding.path, binding.git_blob_sha, binding.canonical_sha256)
            for binding in self.source_bindings
        )
        if observed_bindings != expected_bindings:
            raise ValueError("activation source bindings drifted from merged PR #87")
        expected_hashes = {
            "review_sha256": _REVIEW_SHA256,
            "dry_run_sha256": _DRY_RUN_SHA256,
            "review_manifest_sha256": _REVIEW_MANIFEST_SHA256,
        }
        for field_name, expected in expected_hashes.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"activation binding {field_name} drifted")
        if len(set(self.selected_case_ids)) != _EXPECTED_CASE_COUNT:
            raise ValueError("activation case IDs must be unique")
        if self.required_exact_operand_matches != self.case_count:
            raise ValueError("authorization requires exact operands for all 16 cases")
        if self.required_exact_final_answer_matches != self.case_count:
            raise ValueError("authorization requires exact final answers for all 16 cases")
        return self


class ActionExtractionAuthorizationActivationManifestV2(LocalABCContract):
    """Hash manifest for the active unused authorization."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    manifest_id: Literal[
        "reconcile-balance-action-extraction-authorization-activation-manifest-v2"
    ] = "reconcile-balance-action-extraction-authorization-activation-manifest-v2"
    status: Literal["active_unused"] = "active_unused"
    source_merge_commit: Literal["6038f7055e34c6c559b3c41cb919d0cb421b3e55"] = _PR87_MERGE_COMMIT
    authorization_path: Literal[
        "benchmarks/local_abc/reconcile_balance_extraction_requalification_authorization_v2.json"
    ]
    authorization_sha256: str
    active_authorization_created: Literal[True] = True
    authorization_consumed: Literal[False] = False
    execution_command_available: Literal[False] = False
    notebook_generation_permitted_after_merge: Literal[True] = True
    gpu_enablement_permitted_before_qualified_notebook: Literal[False] = False
    next_gate: Literal["qualified_action_extraction_v2_notebook_generation"] = (
        "qualified_action_extraction_v2_notebook_generation"
    )

    @field_validator("source_merge_commit")
    @classmethod
    def validate_source_merge_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("activation manifest source commit must be a full Git SHA")
        return value

    @field_validator("authorization_sha256")
    @classmethod
    def validate_authorization_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation manifest digest must be lowercase SHA-256")
        return value


class ActionExtractionAuthorizationActivationPackageV2(LocalABCContract):
    """Cross-file package proving that activation matches the approved review."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    review_package: ActionExtractionAuthorizationReviewPackageV2
    authorization: ActionExtractionAuthorizationActivationV2
    manifest: ActionExtractionAuthorizationActivationManifestV2

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        review = self.review_package.review
        dry_run = self.review_package.dry_run
        review_manifest = self.review_package.manifest
        authorization = self.authorization
        if review.fingerprint() != authorization.review_sha256:
            raise ValueError("activation must bind the exact approved review")
        if dry_run.fingerprint() != authorization.dry_run_sha256:
            raise ValueError("activation must bind the exact metadata-only dry run")
        if review_manifest.fingerprint() != authorization.review_manifest_sha256:
            raise ValueError("activation must bind the exact review manifest")
        if review.selected_case_ids != authorization.selected_case_ids:
            raise ValueError("activation case order drifted from the approved review")
        if review.model != authorization.model:
            raise ValueError("activation model binding drifted from the approved review")
        if review.runtime != authorization.runtime:
            raise ValueError("activation runtime binding drifted from the approved review")
        if review.decoding != authorization.decoding:
            raise ValueError("activation decoding policy drifted from the approved review")
        if review.stop_policy != authorization.stop_policy:
            raise ValueError("activation stop policy drifted from the approved review")
        if review.evidence != authorization.evidence:
            raise ValueError("activation evidence contract drifted from the approved review")
        review_hash_fields = (
            "remediation_manifest_sha256",
            "remediation_plan_sha256",
            "normalization_policy_sha256",
            "prompt_policy_sha256",
            "response_schema_sha256",
            "action_schema_sha256",
        )
        for field_name in review_hash_fields:
            if getattr(review, field_name) != getattr(authorization, field_name):
                raise ValueError(f"activation {field_name} drifted from the approved review")
        if self.manifest.authorization_sha256 != authorization.fingerprint():
            raise ValueError("activation manifest must bind the exact authorization")
        return self


def load_action_extraction_authorization_activation_v2(
    path: Path,
) -> ActionExtractionAuthorizationActivationV2:
    """Load and validate the fresh authorization."""

    return ActionExtractionAuthorizationActivationV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_authorization_activation_manifest_v2(
    path: Path,
) -> ActionExtractionAuthorizationActivationManifestV2:
    """Load and validate the authorization activation manifest."""

    return ActionExtractionAuthorizationActivationManifestV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_authorization_activation_package_v2(
    *,
    parent_manifest_path: Path,
    parent_plan_path: Path,
    remediation_manifest_path: Path,
    remediation_plan_path: Path,
    review_path: Path,
    dry_run_path: Path,
    review_manifest_path: Path,
    authorization_path: Path,
    activation_manifest_path: Path,
) -> ActionExtractionAuthorizationActivationPackageV2:
    """Load all activation assets and validate their cross-file bindings."""

    review_package = load_action_extraction_authorization_review_package_v2(
        parent_manifest_path=parent_manifest_path,
        parent_plan_path=parent_plan_path,
        remediation_manifest_path=remediation_manifest_path,
        remediation_plan_path=remediation_plan_path,
        review_path=review_path,
        dry_run_path=dry_run_path,
        review_manifest_path=review_manifest_path,
    )
    return ActionExtractionAuthorizationActivationPackageV2(
        review_package=review_package,
        authorization=load_action_extraction_authorization_activation_v2(authorization_path),
        manifest=load_action_extraction_authorization_activation_manifest_v2(
            activation_manifest_path
        ),
    )


def canonical_json_file_sha256(path: Path) -> str:
    """Validate canonical one-line JSON and return its contract fingerprint."""

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if text != f"{canonical}\n":
        raise ValueError(f"JSON artifact is not canonical one-line JSON: {path}")
    return ActionExtractionAuthorizationActivationV2.model_validate(payload).fingerprint()
