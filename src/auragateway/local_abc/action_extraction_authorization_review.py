"""Inactive authorization review for reconcile-balance extraction remediation v2."""

from __future__ import annotations

import hashlib
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
from auragateway.local_abc.action_extraction_remediation import (
    RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY,
    RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY,
    ActionExtractionRemediationControl,
    ActionExtractionRemediationPackage,
    build_remediated_extraction_prompt_identity,
    load_action_extraction_remediation_package,
    reconcile_balance_response_schema_v2_sha256,
)
from auragateway.local_abc.arithmetic_action import reconcile_balance_action_schema_sha256
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_GIT_BLOB_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_PR86_MERGE_COMMIT: Final = "bb732bf88020cb031f534bb0b67d74b8f8f05483"
_REMEDIATION_SOURCE_BLOB_SHA: Final = "379dddb3efcf53eb1f57b909a16e9ed0b8226619"
_REMEDIATION_MANIFEST_BLOB_SHA: Final = "6a3cb9b677b9c4ccaa1e4f55e57325a0e535511e"
_REMEDIATION_PLAN_BLOB_SHA: Final = "b0b82a3cded9e8e64103e6813c8da240dd127176"
_REMEDIATION_MANIFEST_SHA256: Final = (
    "82037903ab9d944a88e6d1460a001a648308163ed7dae735cbf01359737ae4aa"
)
_REMEDIATION_PLAN_SHA256: Final = "ebeb86b583eeff4f8b2c3ea973f67d6aaba1368a4386eb53737179ed3fd64a36"
_PARENT_EVIDENCE_AUDIT_SHA256: Final = (
    "8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd"
)
_EXPECTED_CASE_COUNT: Final = 16


class ActionExtractionAuthorizationReviewStatus(StrEnum):
    """Inactive lifecycle state for a reviewed candidate authorization."""

    REVIEW_READY_INACTIVE = "review_ready_inactive"


class ActionExtractionAuthorizationReviewDecision(StrEnum):
    """Decision that permits only a separate activation slice."""

    APPROVED_FOR_SEPARATE_ACTIVATION = "approved_for_separate_activation"


class ActionExtractionReviewSourceBinding(LocalABCContract):
    """Exact repository source used by the inactive authorization review."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    path: str
    git_blob_sha: str
    canonical_sha256: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("source binding path must be repository-relative")
        allowed_prefixes = ("src/auragateway/local_abc/", "benchmarks/local_abc/")
        if not value.startswith(allowed_prefixes):
            raise ValueError("source binding path must remain in an approved review location")
        return value

    @field_validator("git_blob_sha")
    @classmethod
    def validate_blob_sha(cls, value: str) -> str:
        if _GIT_BLOB_PATTERN.fullmatch(value) is None:
            raise ValueError("source binding must use a full lowercase Git blob SHA")
        return value

    @field_validator("canonical_sha256")
    @classmethod
    def validate_optional_digest(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("canonical source digest must be lowercase SHA-256")
        return value


class ActionExtractionCandidateStopPolicy(LocalABCContract):
    """Proposed one-attempt stop policy; inactive until a later activation."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    required_request_count: Literal[16] = 16
    request_attempts_per_case: Literal[1] = 1
    semantic_failure_disposition: Literal["retain_and_continue"] = "retain_and_continue"
    infrastructure_failure_disposition: Literal["abort_run"] = "abort_run"
    max_retained_semantic_failures: Literal[16] = 16
    max_infrastructure_failures: Literal[0] = 0
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    failed_case_only_execution_permitted: Literal[False] = False
    direct_model_arithmetic_fallback_permitted: Literal[False] = False
    deterministic_semantic_parser_fallback_permitted: Literal[False] = False
    require_complete_sixteen_record_ledger: Literal[True] = True
    abort_on_source_binding_failure: Literal[True] = True
    abort_on_model_identity_failure: Literal[True] = True
    abort_on_runtime_identity_failure: Literal[True] = True
    abort_on_worker_start_failure: Literal[True] = True
    abort_on_transport_failure: Literal[True] = True
    abort_on_cleanup_failure: Literal[True] = True


class ActionExtractionCandidateEvidenceContract(LocalABCContract):
    """Proposed v2 evidence names and data-minimization controls."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    schedule_filename: Literal["reconcile_balance_extraction_requalification_schedule_v2.json"] = (
        "reconcile_balance_extraction_requalification_schedule_v2.json"
    )
    ledger_filename: Literal["reconcile_balance_extraction_requalification_ledger_v2.jsonl"] = (
        "reconcile_balance_extraction_requalification_ledger_v2.jsonl"
    )
    checkpoint_filename: Literal[
        "reconcile_balance_extraction_requalification_checkpoint_v2.json"
    ] = "reconcile_balance_extraction_requalification_checkpoint_v2.json"
    evaluation_filename: Literal[
        "reconcile_balance_extraction_requalification_evaluation_v2.json"
    ] = "reconcile_balance_extraction_requalification_evaluation_v2.json"
    report_filename: Literal["reconcile_balance_extraction_requalification_report_v2.json"] = (
        "reconcile_balance_extraction_requalification_report_v2.json"
    )
    summary_filename: Literal["RECONCILE_BALANCE_EXTRACTION_REQUALIFICATION_SUMMARY_V2.txt"] = (
        "RECONCILE_BALANCE_EXTRACTION_REQUALIFICATION_SUMMARY_V2.txt"
    )
    model_snapshot_filename: Literal["model_snapshot_manifest_v2.json"] = (
        "model_snapshot_manifest_v2.json"
    )
    worker_log_filename: Literal["worker_1_v2.log"] = "worker_1_v2.log"
    raw_prompt_retention_permitted: Literal[False] = False
    raw_output_retention_permitted: Literal[False] = False
    raw_action_retention_permitted: Literal[False] = False
    token_id_retention_permitted: Literal[False] = False
    retain_prompt_hashes: Literal[True] = True
    retain_normalized_prompt_hashes: Literal[True] = True
    retain_rendered_prompt_hashes: Literal[True] = True
    retain_output_hashes: Literal[True] = True
    retain_action_hashes: Literal[True] = True
    retain_result_hashes: Literal[True] = True
    retain_failure_codes: Literal[True] = True
    retain_normalization_counts: Literal[True] = True

    @model_validator(mode="after")
    def validate_unique_filenames(self) -> Self:
        filenames = (
            self.schedule_filename,
            self.ledger_filename,
            self.checkpoint_filename,
            self.evaluation_filename,
            self.report_filename,
            self.summary_filename,
            self.model_snapshot_filename,
            self.worker_log_filename,
        )
        if len(filenames) != len(set(filenames)):
            raise ValueError("candidate evidence filenames must be unique")
        return self


class ActionExtractionAuthorizationReviewV2(LocalABCContract):
    """Inactive review proving whether a separate v2 activation is justified."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    review_id: Literal["reconcile-balance-action-extraction-authorization-review-v2"] = (
        "reconcile-balance-action-extraction-authorization-review-v2"
    )
    created_at: datetime
    status: Literal[ActionExtractionAuthorizationReviewStatus.REVIEW_READY_INACTIVE] = (
        ActionExtractionAuthorizationReviewStatus.REVIEW_READY_INACTIVE
    )
    decision: Literal[
        ActionExtractionAuthorizationReviewDecision.APPROVED_FOR_SEPARATE_ACTIVATION
    ] = ActionExtractionAuthorizationReviewDecision.APPROVED_FOR_SEPARATE_ACTIVATION
    repository: Literal["kablewithak/auragateway"] = "kablewithak/auragateway"
    source_merge_commit: Literal["bb732bf88020cb031f534bb0b67d74b8f8f05483"] = _PR86_MERGE_COMMIT
    source_bindings: tuple[ActionExtractionReviewSourceBinding, ...] = Field(
        min_length=3,
        max_length=3,
    )
    parent_evidence_audit_sha256: str
    remediation_manifest_sha256: str
    remediation_plan_sha256: str
    normalization_policy_sha256: str
    prompt_policy_sha256: str
    response_schema_sha256: str
    action_schema_sha256: str
    controls: tuple[ActionExtractionRemediationControl, ...]
    historical_case_count: Literal[12] = 12
    added_diagnostic_case_count: Literal[4] = 4
    total_case_count: Literal[16] = 16
    selected_case_ids: tuple[str, ...] = Field(min_length=16, max_length=16)
    baseline_exact_operand_matches: Literal[10] = 10
    baseline_exact_final_answer_matches: Literal[10] = 10
    baseline_case_count: Literal[12] = 12
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
    provider_call_performed: Literal[False] = False
    model_request_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    active_authorization_created: Literal[False] = False
    execution_command_available: Literal[False] = False
    notebook_generation_permitted: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    failed_case_only_execution_permitted: Literal[False] = False
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Literal[0] = 0
    customer_data_used: Literal[False] = False
    synthetic_data_only: Literal[True] = True
    next_gate: Literal["bounded_action_extraction_v2_authorization_activation"] = (
        "bounded_action_extraction_v2_authorization_activation"
    )

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("review ID must use stable lowercase characters")
        return value

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @field_validator("source_merge_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("review source commit must be a full lowercase Git SHA")
        return value

    @field_validator(
        "parent_evidence_audit_sha256",
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
            raise ValueError("review digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        paths = tuple(binding.path for binding in self.source_bindings)
        duplicates = tuple(path for path, count in Counter(paths).items() if count > 1)
        if duplicates:
            raise ValueError("review source binding paths must be unique")
        expected_bindings = (
            (
                "src/auragateway/local_abc/action_extraction_remediation.py",
                _REMEDIATION_SOURCE_BLOB_SHA,
                None,
            ),
            (
                "benchmarks/local_abc/reconcile_balance_extraction_remediation_cases_v2.json",
                _REMEDIATION_MANIFEST_BLOB_SHA,
                _REMEDIATION_MANIFEST_SHA256,
            ),
            (
                "benchmarks/local_abc/reconcile_balance_extraction_remediation_plan_v2.json",
                _REMEDIATION_PLAN_BLOB_SHA,
                _REMEDIATION_PLAN_SHA256,
            ),
        )
        observed_bindings = tuple(
            (binding.path, binding.git_blob_sha, binding.canonical_sha256)
            for binding in self.source_bindings
        )
        if observed_bindings != expected_bindings:
            raise ValueError("review source bindings drifted from merged PR #86")
        expected_digests = {
            "parent_evidence_audit_sha256": _PARENT_EVIDENCE_AUDIT_SHA256,
            "remediation_manifest_sha256": _REMEDIATION_MANIFEST_SHA256,
            "remediation_plan_sha256": _REMEDIATION_PLAN_SHA256,
            "normalization_policy_sha256": (
                RECONCILE_BALANCE_INTEGER_NORMALIZATION_POLICY.fingerprint()
            ),
            "prompt_policy_sha256": RECONCILE_BALANCE_REMEDIATION_PROMPT_POLICY.fingerprint(),
            "response_schema_sha256": reconcile_balance_response_schema_v2_sha256(),
            "action_schema_sha256": reconcile_balance_action_schema_sha256(),
        }
        for field_name, expected in expected_digests.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"review binding {field_name} drifted")
        if self.total_case_count != self.historical_case_count + self.added_diagnostic_case_count:
            raise ValueError("review case counts do not reconcile")
        if self.required_exact_operand_matches != self.total_case_count:
            raise ValueError("authorization review requires exact operands for every case")
        if self.required_exact_final_answer_matches != self.total_case_count:
            raise ValueError("authorization review requires exact final answers for every case")
        return self


class ActionExtractionAuthorizationDryRunAttemptV2(LocalABCContract):
    """One metadata-only planned request derived from the v2 case constitution."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    sequence_index: int = Field(ge=0, le=15)
    eval_case_id: str
    source_prompt_sha256: str
    normalized_prompt_sha256: str
    rendered_prompt_sha256: str
    expected_action_sha256: str
    expected_answer: int
    request_attempts_per_case: Literal[1] = 1
    model_request_permitted: Literal[False] = False
    raw_prompt_retained: Literal[False] = False

    @field_validator("eval_case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run case ID must use stable lowercase characters")
        return value

    @field_validator(
        "source_prompt_sha256",
        "normalized_prompt_sha256",
        "rendered_prompt_sha256",
        "expected_action_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run digests must be lowercase SHA-256")
        return value


class ActionExtractionAuthorizationDryRunV2(LocalABCContract):
    """Inactive 16-request schedule with no execution path."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    dry_run_id: Literal["reconcile-balance-action-extraction-authorization-dry-run-v2"] = (
        "reconcile-balance-action-extraction-authorization-dry-run-v2"
    )
    review_id: Literal["reconcile-balance-action-extraction-authorization-review-v2"] = (
        "reconcile-balance-action-extraction-authorization-review-v2"
    )
    status: Literal["passed_inactive"] = "passed_inactive"
    attempts: tuple[ActionExtractionAuthorizationDryRunAttemptV2, ...] = Field(
        min_length=16,
        max_length=16,
    )
    planned_request_count: Literal[16] = 16
    complete_suite_required: Literal[True] = True
    full_worker_restart_before_run: Literal[True] = True
    worker_id: Literal["worker_1"] = "worker_1"
    model_request_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    execution_command_available: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_dry_run(self) -> Self:
        if tuple(attempt.sequence_index for attempt in self.attempts) != tuple(range(16)):
            raise ValueError("dry-run attempts must remain in exact sequence order")
        case_ids = tuple(attempt.eval_case_id for attempt in self.attempts)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("dry-run case IDs must be unique")
        return self


class ActionExtractionAuthorizationReviewManifestV2(LocalABCContract):
    """Hash manifest for inactive review assets."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    manifest_id: Literal["reconcile-balance-action-extraction-authorization-review-manifest-v2"] = (
        "reconcile-balance-action-extraction-authorization-review-manifest-v2"
    )
    status: Literal["frozen_inactive"] = "frozen_inactive"
    source_merge_commit: Literal["bb732bf88020cb031f534bb0b67d74b8f8f05483"] = _PR86_MERGE_COMMIT
    review_path: Literal[
        "benchmarks/local_abc/reconcile_balance_extraction_authorization_review_v2.json"
    ]
    review_sha256: str
    dry_run_path: Literal[
        "benchmarks/local_abc/reconcile_balance_extraction_authorization_dry_run_v2.json"
    ]
    dry_run_sha256: str
    active_authorization_created: Literal[False] = False
    execution_command_available: Literal[False] = False
    execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    next_gate: Literal["bounded_action_extraction_v2_authorization_activation"] = (
        "bounded_action_extraction_v2_authorization_activation"
    )

    @field_validator("source_merge_commit")
    @classmethod
    def validate_source_commit(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("review manifest source commit must be a full Git SHA")
        return value

    @field_validator("review_sha256", "dry_run_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("review manifest digests must be lowercase SHA-256")
        return value


class ActionExtractionAuthorizationReviewPackageV2(LocalABCContract):
    """Cross-file review package with fail-closed schedule bindings."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    remediation: ActionExtractionRemediationPackage
    review: ActionExtractionAuthorizationReviewV2
    dry_run: ActionExtractionAuthorizationDryRunV2
    manifest: ActionExtractionAuthorizationReviewManifestV2

    @model_validator(mode="after")
    def validate_package(self) -> Self:
        remediation_manifest = self.remediation.remediation_manifest
        remediation_plan = self.remediation.remediation_plan
        case_ids = tuple(
            case.eval_case_id
            for case in (
                *remediation_manifest.historical_cases,
                *remediation_manifest.added_diagnostic_cases,
            )
        )
        if remediation_manifest.fingerprint() != self.review.remediation_manifest_sha256:
            raise ValueError("review must bind the remediation manifest")
        if remediation_plan.fingerprint() != self.review.remediation_plan_sha256:
            raise ValueError("review must bind the remediation plan")
        if self.review.selected_case_ids != case_ids:
            raise ValueError("review selected cases drifted from the remediation manifest")
        if tuple(attempt.eval_case_id for attempt in self.dry_run.attempts) != case_ids:
            raise ValueError("dry-run case order drifted from the remediation manifest")
        if self.manifest.review_sha256 != self.review.fingerprint():
            raise ValueError("review manifest must bind the exact review")
        if self.manifest.dry_run_sha256 != self.dry_run.fingerprint():
            raise ValueError("review manifest must bind the exact dry run")
        return self


def build_action_extraction_authorization_dry_run_v2(
    remediation: ActionExtractionRemediationPackage,
) -> ActionExtractionAuthorizationDryRunV2:
    """Build the metadata-only 16-request schedule without model execution."""

    cases = (
        *remediation.remediation_manifest.historical_cases,
        *remediation.remediation_manifest.added_diagnostic_cases,
    )
    attempts = tuple(
        ActionExtractionAuthorizationDryRunAttemptV2(
            sequence_index=index,
            eval_case_id=case.eval_case_id,
            source_prompt_sha256=identity.source_prompt_sha256,
            normalized_prompt_sha256=identity.normalized_prompt_sha256,
            rendered_prompt_sha256=identity.rendered_prompt_sha256,
            expected_action_sha256=case.expected_action_sha256,
            expected_answer=case.expected_answer,
        )
        for index, case in enumerate(cases)
        for identity in (build_remediated_extraction_prompt_identity(case),)
    )
    return ActionExtractionAuthorizationDryRunV2(attempts=attempts)


def load_action_extraction_authorization_review_v2(
    path: Path,
) -> ActionExtractionAuthorizationReviewV2:
    """Load and validate the inactive authorization review."""

    return ActionExtractionAuthorizationReviewV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_authorization_dry_run_v2(
    path: Path,
) -> ActionExtractionAuthorizationDryRunV2:
    """Load and validate the inactive dry-run schedule."""

    return ActionExtractionAuthorizationDryRunV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_authorization_review_manifest_v2(
    path: Path,
) -> ActionExtractionAuthorizationReviewManifestV2:
    """Load and validate the inactive review manifest."""

    return ActionExtractionAuthorizationReviewManifestV2.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_action_extraction_authorization_review_package_v2(
    *,
    parent_manifest_path: Path,
    parent_plan_path: Path,
    remediation_manifest_path: Path,
    remediation_plan_path: Path,
    review_path: Path,
    dry_run_path: Path,
    review_manifest_path: Path,
) -> ActionExtractionAuthorizationReviewPackageV2:
    """Load all review assets and validate their cross-file bindings."""

    remediation = load_action_extraction_remediation_package(
        parent_manifest_path=parent_manifest_path,
        parent_plan_path=parent_plan_path,
        remediation_manifest_path=remediation_manifest_path,
        remediation_plan_path=remediation_plan_path,
    )
    return ActionExtractionAuthorizationReviewPackageV2(
        remediation=remediation,
        review=load_action_extraction_authorization_review_v2(review_path),
        dry_run=load_action_extraction_authorization_dry_run_v2(dry_run_path),
        manifest=load_action_extraction_authorization_review_manifest_v2(review_manifest_path),
    )


def canonical_json_file_sha256(path: Path) -> str:
    """Validate canonical one-line JSON and return its content SHA-256."""

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if text != f"{canonical}\n":
        raise ValueError(f"JSON artifact is not canonical one-line JSON: {path}")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
