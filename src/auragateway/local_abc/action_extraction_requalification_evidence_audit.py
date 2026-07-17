"""Immutable audit for the action-extraction requalification v2 evidence."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_ARCHIVE_FILENAME = (
    "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
)
_ARCHIVE_SHA256 = "b7da2b703232154742665b47254e662a2e6ff4b6e198827e7d29f67dc9c16c93"
_ARCHIVE_SIZE_BYTES = 22767
_PACKAGE_MERGE_COMMIT = "52dcd0564b26b917684faedaa46d2d038a9e0be7"
_EXECUTION_REPOSITORY_COMMIT = "639e21a63eb8a37d0221c2630b756203d1270f62"
_AUTHORIZATION_SHA256 = "a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899"
_NOTEBOOK_SHA256 = "e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9"
_NOTEBOOK_BINDING_SHA256 = "476d3be54fc34cafacba4bcdef07eaa1213a426df0496e4908bc8078b7edac88"
_SCHEDULE_PROMPT_POLICY_SHA256 = "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
_LEGACY_SCORE_PROMPT_POLICY_SHA256 = (
    "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
)
_RESPONSE_SCHEMA_SHA256 = "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
_ACTION_SCHEMA_SHA256 = "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
_REMEDIATION_MANIFEST_SHA256 = "82037903ab9d944a88e6d1460a001a648308163ed7dae735cbf01359737ae4aa"
_REMEDIATION_PLAN_SHA256 = "ebeb86b583eeff4f8b2c3ea973f67d6aaba1368a4386eb53737179ed3fd64a36"
_EVALUATION_CANONICAL_SHA256 = "aac8cb14732b7e3019c0fccc2b8516df997682f973df4262683d70812b0c32fd"

_EXPECTED_MEMBER_HASHES = (
    (
        "RECONCILE_BALANCE_EXTRACTION_REQUALIFICATION_SUMMARY_V2.txt",
        "8e97a4f5b50354e42120643329c0fc69052c907e930f337dc35854c695eca829",
    ),
    (
        "model_snapshot_manifest_v2.json",
        "0538a07daf47cd53953c174aedd2972708309c0fccff00c9ef5c11af19300d71",
    ),
    (
        "reconcile_balance_extraction_requalification_checkpoint_v2.json",
        "f9e5c9529cfa41428cf29a48d1a19faa8cb8865ea8958cbff248d9a53fd4f0a5",
    ),
    (
        "reconcile_balance_extraction_requalification_evaluation_v2.json",
        "649ade3484c7c2695ae08f4127d9f8a81cebb356f4b5ac81c7b71d20edc5e80e",
    ),
    (
        "reconcile_balance_extraction_requalification_ledger_v2.jsonl",
        "57e14c16e9389a3cc4e84cc96ed50efa2cce5620c8e4ad1edaecb9c5bde25ff4",
    ),
    (
        "reconcile_balance_extraction_requalification_report_v2.json",
        "754023f505efbdceef4a3c24b921834f8a50cc11f1b631a52f529e9fac85f6f5",
    ),
    (
        "reconcile_balance_extraction_requalification_schedule_v2.json",
        "56543e86b45426fc6851a5f6e96f49621e7557d5d9949e700a07c27fef3af073",
    ),
    (
        "worker_1_v2.log",
        "51eac84e6fcd20a820b44a0f48c773935e70a0963562990ffbf0808544848992",
    ),
)

_EXPECTED_CASE_IDS = (
    "historical-turn-one",
    "turn-two-history-distractors",
    "reordered-narrative",
    "zero-boundary",
    "repeated-operands",
    "metadata-number-distractors",
    "formatted-currency-values",
    "key-value-layout",
    "same-answer-different-operands",
    "maximum-opening-boundary",
    "credits-first-description",
    "turn-two-feedback-separation",
    "formatted-currency-multi-group",
    "formatted-currency-spaced-symbol",
    "key-value-credits-first-layout",
    "key-value-mixed-delimiters",
)

_WARNING_PATTERNS = (
    ("SITECUSTOMIZE_WRAP_MISSING", "No module named 'wrapt'"),
    ("BFLOAT16_CAST_TO_FLOAT16", "Casting torch.bfloat16 to torch.float16"),
    (
        "EAGER_MODE_COMPILE_DISABLED",
        "Enforce eager set, disabling torch.compile and CUDAGraphs",
    ),
    ("CUDA_BINDINGS_DEPRECATION", "cuda.cudart module is deprecated"),
    (
        "TRITON_JIT_DURING_INFERENCE",
        "Triton kernel JIT compilation during inference",
    ),
    (
        "FORCED_PROCESS_TERMINATION",
        "force killing remaining processes count=1",
    ),
    ("LEAKED_SEMAPHORE", "1 leaked semaphore objects"),
)


class ActionExtractionRequalificationClassification(StrEnum):
    """Terminal classification for the completed v2 requalification."""

    PASSED_WITH_WARNINGS = "CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS"


class ActionExtractionRequalificationFindingCode(StrEnum):
    """Audit findings that require harness hardening but not a rerun."""

    STALE_SCORE_PROMPT_IDENTITY = "STALE_SCORE_PROMPT_IDENTITY_METADATA"
    OVERSTATED_CLEANUP_STATUS = "OVERSTATED_CLEANUP_STATUS"


class ActionExtractionRequalificationWarningCode(StrEnum):
    """Non-fatal runtime warnings proven by the retained worker log."""

    SITECUSTOMIZE_WRAP_MISSING = "SITECUSTOMIZE_WRAP_MISSING"
    BFLOAT16_CAST_TO_FLOAT16 = "BFLOAT16_CAST_TO_FLOAT16"
    EAGER_MODE_COMPILE_DISABLED = "EAGER_MODE_COMPILE_DISABLED"
    CUDA_BINDINGS_DEPRECATION = "CUDA_BINDINGS_DEPRECATION"
    TRITON_JIT_DURING_INFERENCE = "TRITON_JIT_DURING_INFERENCE"
    FORCED_PROCESS_TERMINATION = "FORCED_PROCESS_TERMINATION"
    LEAKED_SEMAPHORE = "LEAKED_SEMAPHORE"


class ActionExtractionAuthorizationLifecycleState(StrEnum):
    """Lifecycle state of the one-shot v2 authorization."""

    CONSUMED = "consumed"


class ActionExtractionArchiveVerificationFailureCode(StrEnum):
    """Stable failure codes for protected evidence verification."""

    ARCHIVE_NOT_FOUND = "ACTION_EXTRACTION_V2_EVIDENCE_ARCHIVE_NOT_FOUND"
    ARCHIVE_SHA256_MISMATCH = "ACTION_EXTRACTION_V2_EVIDENCE_ARCHIVE_SHA256_MISMATCH"
    ARCHIVE_SIZE_MISMATCH = "ACTION_EXTRACTION_V2_EVIDENCE_ARCHIVE_SIZE_MISMATCH"
    ARCHIVE_INTEGRITY_FAILED = "ACTION_EXTRACTION_V2_EVIDENCE_ARCHIVE_INTEGRITY_FAILED"
    MEMBER_SET_MISMATCH = "ACTION_EXTRACTION_V2_EVIDENCE_MEMBER_SET_MISMATCH"
    MEMBER_SHA256_MISMATCH = "ACTION_EXTRACTION_V2_EVIDENCE_MEMBER_SHA256_MISMATCH"
    SEMANTIC_VALIDATION_FAILED = "ACTION_EXTRACTION_V2_EVIDENCE_SEMANTIC_VALIDATION_FAILED"


class ActionExtractionAuthorizationReuseFailureCode(StrEnum):
    """Stable failure code for prohibited authorization reuse."""

    AUTHORIZATION_CONSUMED = "ACTION_EXTRACTION_V2_AUTHORIZATION_CONSUMED"


class ActionExtractionArchiveVerificationError(RuntimeError):
    """Raised when the protected evidence archive fails verification."""

    def __init__(
        self,
        *,
        code: ActionExtractionArchiveVerificationFailureCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


class ActionExtractionAuthorizationConsumedError(RuntimeError):
    """Raised when code attempts to reuse the completed v2 authorization."""

    def __init__(self, message: str = "action-extraction v2 authorization is consumed") -> None:
        super().__init__(message)
        self.code = ActionExtractionAuthorizationReuseFailureCode.AUTHORIZATION_CONSUMED


class ActionExtractionEvidenceMember(LocalABCContract):
    """Digest and role for one member of the protected evidence archive."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    filename: str = Field(min_length=1, max_length=180)
    sha256: str
    evidence_role: str = Field(min_length=3, max_length=100)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence member digest must be lowercase SHA-256")
        return value


class ActionExtractionArtifactBinding(LocalABCContract):
    """Frozen package, execution, authorization, notebook, and harness identities."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    package_merge_commit: str
    execution_repository_commit: str
    authorization_sha256: str
    notebook_sha256: str
    notebook_binding_sha256: str
    schedule_prompt_policy_sha256: str
    legacy_score_prompt_policy_sha256: str
    response_schema_sha256: str
    action_schema_sha256: str
    remediation_manifest_sha256: str
    remediation_plan_sha256: str
    evaluation_canonical_sha256: str

    @field_validator(
        "authorization_sha256",
        "notebook_sha256",
        "notebook_binding_sha256",
        "schedule_prompt_policy_sha256",
        "legacy_score_prompt_policy_sha256",
        "response_schema_sha256",
        "action_schema_sha256",
        "remediation_manifest_sha256",
        "remediation_plan_sha256",
        "evaluation_canonical_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact bindings must be lowercase SHA-256")
        return value

    @field_validator("package_merge_commit", "execution_repository_commit")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact commit binding must be lowercase Git SHA-1")
        return value

    @model_validator(mode="after")
    def validate_frozen_identities(self) -> Self:
        expected = {
            "package_merge_commit": _PACKAGE_MERGE_COMMIT,
            "execution_repository_commit": _EXECUTION_REPOSITORY_COMMIT,
            "authorization_sha256": _AUTHORIZATION_SHA256,
            "notebook_sha256": _NOTEBOOK_SHA256,
            "notebook_binding_sha256": _NOTEBOOK_BINDING_SHA256,
            "schedule_prompt_policy_sha256": _SCHEDULE_PROMPT_POLICY_SHA256,
            "legacy_score_prompt_policy_sha256": _LEGACY_SCORE_PROMPT_POLICY_SHA256,
            "response_schema_sha256": _RESPONSE_SCHEMA_SHA256,
            "action_schema_sha256": _ACTION_SCHEMA_SHA256,
            "remediation_manifest_sha256": _REMEDIATION_MANIFEST_SHA256,
            "remediation_plan_sha256": _REMEDIATION_PLAN_SHA256,
            "evaluation_canonical_sha256": _EVALUATION_CANONICAL_SHA256,
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(f"artifact binding drifted: {field_name}")
        return self


class ActionExtractionRequalificationMetrics(LocalABCContract):
    """Exact aggregate quality, execution, retry, and cleanup counts."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    authorized_requests: Literal[16] = 16
    completed_requests: Literal[16] = 16
    http_200_responses: Literal[16] = 16
    valid_action_json: Literal[16] = 16
    valid_action_schema: Literal[16] = 16
    exact_identity_matches: Literal[16] = 16
    deterministic_execution_successes: Literal[16] = 16
    exact_operand_matches: Literal[16] = 16
    exact_final_answer_matches: Literal[16] = 16
    first_attempt_task_successes: Literal[16] = 16
    semantic_failures: Literal[0] = 0
    infrastructure_failures: Literal[0] = 0
    hidden_retries: Literal[0] = 0
    repairs: Literal[0] = 0
    replacement_requests: Literal[0] = 0
    direct_model_arithmetic_fallbacks: Literal[0] = 0
    declared_cleanup_status: Literal["CLEAN"] = "CLEAN"
    audited_cleanup_status: Literal["CLEAN_WITH_RUNTIME_WARNINGS"] = "CLEAN_WITH_RUNTIME_WARNINGS"
    worker_return_code: Literal[0] = 0
    worker_port_closed: Literal[True] = True
    gate_decision: Literal["passed"] = "passed"


class ActionExtractionAuditFinding(LocalABCContract):
    """One evidence-backed finding with explicit impact and disposition."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    code: ActionExtractionRequalificationFindingCode
    severity: Literal["medium", "low"]
    observed_count: int = Field(ge=1)
    invalidates_quality_gate: Literal[False] = False
    requires_rerun: Literal[False] = False
    requires_follow_up: Literal[True] = True
    disposition: str = Field(min_length=20, max_length=400)


class ActionExtractionRuntimeWarning(LocalABCContract):
    """One retained non-fatal runtime warning."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    code: ActionExtractionRequalificationWarningCode
    observed_count: int = Field(ge=1)
    infrastructure_failure: Literal[False] = False
    invalidates_quality_gate: Literal[False] = False
    requires_follow_up: Literal[True] = True


class ActionExtractionPrivacyBoundary(LocalABCContract):
    """Evidence-minimization, customer-data, and spend boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    raw_action_retained: Literal[False] = False
    token_ids_retained: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Decimal = Decimal("0")
    credentials_retained: Literal[False] = False

    @field_validator("external_spend")
    @classmethod
    def validate_zero_spend(cls, value: Decimal) -> Decimal:
        if value != Decimal("0"):
            raise ValueError("external spend must remain zero")
        return value


class ActionExtractionRequalificationEvidenceAudit(LocalABCContract):
    """Immutable, queryable audit over the completed v2 requalification."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    audit_id: Literal[
        "auragateway-reconcile-balance-action-extraction-requalification-evidence-audit-v2"
    ]
    audited_at: datetime
    classification: ActionExtractionRequalificationClassification
    evidence_archive_filename: Literal[
        "auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip"
    ]
    evidence_archive_sha256: str
    evidence_archive_size_bytes: Literal[22767] = 22767
    evidence_member_count: Literal[8] = 8
    evidence_members: tuple[ActionExtractionEvidenceMember, ...]
    artifacts: ActionExtractionArtifactBinding
    metrics: ActionExtractionRequalificationMetrics
    case_ids: tuple[str, ...]
    findings: tuple[ActionExtractionAuditFinding, ActionExtractionAuditFinding]
    runtime_warnings: tuple[ActionExtractionRuntimeWarning, ...]
    privacy: ActionExtractionPrivacyBoundary
    authorization_consumed: Literal[True] = True
    same_authorization_rerun_permitted: Literal[False] = False
    failed_cell_rerun_permitted: Literal[False] = False
    failed_case_only_execution_permitted: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    quality_gate_passed: Literal[True] = True
    traceability_perfect: Literal[False] = False
    cleanup_perfect: Literal[False] = False
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    certificate_id: Literal["AURAGATEWAY-LOCAL-ABC-SFRC-0004"]
    certificate_status: Literal["CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS"]
    certificate_json_filename: Literal[
        "reconcile_balance_extraction_requalification_semi_formal_reasoning_certificate_v2.json"
    ]
    certificate_json_sha256: str
    certificate_markdown_filename: Literal[
        "local_abc_reconcile_balance_action_extraction_requalification_"
        "semi_formal_reasoning_certificate_v2.md"
    ]
    certificate_markdown_sha256: str
    next_gate: Literal["action_extraction_v2_traceability_cleanup_hardening"] = (
        "action_extraction_v2_traceability_cleanup_hardening"
    )

    @field_validator("audited_at")
    @classmethod
    def validate_audited_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("audited_at must be timezone-aware")
        return value

    @field_validator(
        "evidence_archive_sha256",
        "certificate_json_sha256",
        "certificate_markdown_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("audit digests must be lowercase SHA-256")
        return value

    @field_validator("evidence_members")
    @classmethod
    def validate_evidence_members(
        cls,
        value: tuple[ActionExtractionEvidenceMember, ...],
    ) -> tuple[ActionExtractionEvidenceMember, ...]:
        observed = tuple((member.filename, member.sha256) for member in value)
        if observed != _EXPECTED_MEMBER_HASHES:
            raise ValueError("audit must preserve exact member order and hashes")
        return value

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_CASE_IDS:
            raise ValueError("audit must preserve the complete 16-case order")
        return value

    @model_validator(mode="after")
    def validate_terminal_boundary(self) -> Self:
        if self.evidence_archive_sha256 != _ARCHIVE_SHA256:
            raise ValueError("evidence archive digest drifted")
        expected_findings = tuple(ActionExtractionRequalificationFindingCode)
        if tuple(finding.code for finding in self.findings) != expected_findings:
            raise ValueError("audit must preserve both findings in canonical order")
        expected_warnings = tuple(ActionExtractionRequalificationWarningCode)
        if tuple(warning.code for warning in self.runtime_warnings) != expected_warnings:
            raise ValueError("audit must preserve every runtime warning in canonical order")
        return self


class ActionExtractionRequalificationCertificate(LocalABCContract):
    """Semi-formal conclusion binding the passed quality gate and audit warnings."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    certificate_id: Literal["AURAGATEWAY-LOCAL-ABC-SFRC-0004"]
    issued_at: datetime
    status: Literal["CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS"]
    audit_id: Literal[
        "auragateway-reconcile-balance-action-extraction-requalification-evidence-audit-v2"
    ]
    evidence_archive_sha256: str
    authorization_sha256: str
    notebook_sha256: str
    quality_result: Literal["16_OF_16_EXACT_OPERANDS_AND_FINAL_ANSWERS"]
    traceability_finding_count: Literal[1] = 1
    cleanup_finding_count: Literal[1] = 1
    runtime_warning_count: Literal[7] = 7
    authorization_consumed: Literal[True] = True
    rerun_permitted: Literal[False] = False
    full_abc_authorized: Literal[False] = False
    next_gate: Literal["action_extraction_v2_traceability_cleanup_hardening"]

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator(
        "evidence_archive_sha256",
        "authorization_sha256",
        "notebook_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("certificate digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.evidence_archive_sha256 != _ARCHIVE_SHA256:
            raise ValueError("certificate evidence archive binding drifted")
        if self.authorization_sha256 != _AUTHORIZATION_SHA256:
            raise ValueError("certificate authorization binding drifted")
        if self.notebook_sha256 != _NOTEBOOK_SHA256:
            raise ValueError("certificate notebook binding drifted")
        return self


class ActionExtractionAuthorizationConsumption(LocalABCContract):
    """Immutable lifecycle record preventing reuse of the v2 authorization."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    consumption_id: Literal[
        "auragateway-reconcile-balance-action-extraction-"
        "requalification-authorization-consumption-v2"
    ]
    consumed_at: datetime
    authorization_sha256: str
    lifecycle_state: Literal[ActionExtractionAuthorizationLifecycleState.CONSUMED]
    evidence_audit_sha256: str
    certificate_json_sha256: str
    completed_request_count: Literal[16] = 16
    reusable: Literal[False] = False
    execution_authorized: Literal[False] = False
    notebook_rerun_permitted: Literal[False] = False
    failed_case_only_execution_permitted: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["action_extraction_v2_traceability_cleanup_hardening"]

    @field_validator("consumed_at")
    @classmethod
    def validate_consumed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must be timezone-aware")
        return value

    @field_validator(
        "authorization_sha256",
        "evidence_audit_sha256",
        "certificate_json_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("consumption digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_authorization(self) -> Self:
        if self.authorization_sha256 != _AUTHORIZATION_SHA256:
            raise ValueError("consumption authorization binding drifted")
        return self


class ActionExtractionGovernancePackage(LocalABCContract):
    """Cross-file binding for the audit, certificate, and authorization consumption."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    audit: ActionExtractionRequalificationEvidenceAudit
    certificate: ActionExtractionRequalificationCertificate
    consumption: ActionExtractionAuthorizationConsumption

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.consumption.authorization_sha256 != self.audit.artifacts.authorization_sha256:
            raise ValueError("consumption must bind the audited authorization")
        if self.consumption.evidence_audit_sha256 != self.audit.fingerprint():
            raise ValueError("consumption must bind the audit fingerprint")
        if self.consumption.certificate_json_sha256 != self.audit.certificate_json_sha256:
            raise ValueError("consumption must bind the certificate JSON")
        if self.certificate.fingerprint() != self.audit.certificate_json_sha256:
            raise ValueError("audit must bind the certificate fingerprint")
        if self.certificate.certificate_id != self.audit.certificate_id:
            raise ValueError("audit and certificate IDs must match")
        return self


class ActionExtractionArchiveVerificationReport(LocalABCContract):
    """Successful archive verification without exposing protected evidence content."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    archive_filename: str
    archive_sha256: str
    archive_size_bytes: int = Field(gt=0)
    member_count: int = Field(gt=0)
    member_hashes_verified: Literal[True] = True
    zip_integrity_passed: Literal[True] = True
    semantic_evidence_verified: Literal[True] = True
    quality_gate_passed: Literal[True] = True
    prompt_identity_mismatch_count: Literal[16] = 16
    runtime_warning_count: Literal[7] = 7
    audited_cleanup_status: Literal["CLEAN_WITH_RUNTIME_WARNINGS"] = "CLEAN_WITH_RUNTIME_WARNINGS"

    @field_validator("archive_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("verification digest must be lowercase SHA-256")
        return value


def sha256_file(path: Path) -> str:
    """Hash one file without loading protected evidence into logs."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Hash one JSON object using the repository canonical serialization."""

    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_json_object_bytes(payload: bytes, filename: str) -> dict[str, Any]:
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{filename} must contain one JSON object")
    return cast(dict[str, Any], value)


def _load_json_lines(payload: bytes, filename: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{filename}:{line_number} must contain one JSON object")
        records.append(cast(dict[str, Any], value))
    return records


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"field {key} must be an object")
    return cast(Mapping[str, Any], value)


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"field {key} must be a list")
    return value


def _validate_schedule(schedule: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if schedule.get("status") != "QUALIFIED_NOT_STARTED":
        raise ValueError("schedule status drifted")
    if schedule.get("request_count") != 16:
        raise ValueError("schedule must contain exactly 16 requests")
    if schedule.get("worker_id") != "worker_1":
        raise ValueError("schedule worker identity drifted")
    if schedule.get("activation_merge_commit") != _EXECUTION_REPOSITORY_COMMIT:
        raise ValueError("schedule activation merge binding drifted")
    if schedule.get("authorization_fingerprint") != _AUTHORIZATION_SHA256:
        raise ValueError("schedule authorization binding drifted")
    if schedule.get("notebook_sha256") != _NOTEBOOK_SHA256:
        raise ValueError("schedule notebook binding drifted")
    if schedule.get("prompt_policy_sha256") != _SCHEDULE_PROMPT_POLICY_SHA256:
        raise ValueError("schedule prompt policy binding drifted")
    if schedule.get("response_schema_sha256") != _RESPONSE_SCHEMA_SHA256:
        raise ValueError("schedule response schema binding drifted")
    if schedule.get("action_schema_sha256") != _ACTION_SCHEMA_SHA256:
        raise ValueError("schedule action schema binding drifted")

    requests = _require_list(schedule, "requests")
    if len(requests) != 16:
        raise ValueError("schedule request list must contain exactly 16 records")
    request_mappings = [cast(Mapping[str, Any], request) for request in requests]
    case_ids = tuple(request.get("eval_case_id") for request in request_mappings)
    if case_ids != _EXPECTED_CASE_IDS:
        raise ValueError("schedule case order drifted")
    if tuple(request.get("sequence") for request in request_mappings) != tuple(range(1, 17)):
        raise ValueError("schedule sequence must be one through sixteen")
    if any(request.get("attempt_limit") != 1 for request in request_mappings):
        raise ValueError("schedule attempt limit must remain one")
    return request_mappings


def _validate_ledger(
    ledger: list[dict[str, Any]],
    requests: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if len(ledger) != 16:
        raise ValueError("ledger must contain exactly 16 records")
    if tuple(record.get("eval_case_id") for record in ledger) != _EXPECTED_CASE_IDS:
        raise ValueError("ledger case order drifted")
    if tuple(record.get("sequence") for record in ledger) != tuple(range(1, 17)):
        raise ValueError("ledger sequence must be one through sixteen")

    scores: list[Mapping[str, Any]] = []
    for request, record in zip(requests, ledger, strict=True):
        if record.get("attempt_index") != 1:
            raise ValueError("ledger contains a retry or replacement attempt")
        if record.get("http_status") != 200:
            raise ValueError("ledger contains a non-200 model response")
        if record.get("worker_id") != "worker_1":
            raise ValueError("ledger worker identity drifted")
        for key in (
            "eval_case_id",
            "sequence",
            "source_prompt_sha256",
            "normalized_prompt_sha256",
            "rendered_prompt_sha256",
            "request_body_sha256",
            "currency_integer_normalization_count",
            "grouped_integer_normalization_count",
        ):
            if record.get(key) != request.get(key):
                raise ValueError(f"ledger and schedule diverged for {key}")

        score = _require_mapping(record, "score")
        success_fields = (
            "action_json_valid",
            "action_schema_valid",
            "exact_case_id_match",
            "exact_operand_match",
            "exact_turn_index_match",
            "execution_success",
            "final_answer_match",
            "first_attempt_task_success",
        )
        if any(score.get(field) is not True for field in success_fields):
            raise ValueError("ledger contains a failed quality assertion")
        if score.get("finish_reason") != "stop":
            raise ValueError("ledger contains a non-stop finish reason")
        if score.get("action_sha256") != score.get("expected_action_sha256"):
            raise ValueError("ledger action fingerprint does not match expectation")
        if score.get("evaluation_failure_codes") != []:
            raise ValueError("ledger contains evaluation failure codes")
        if score.get("action_failure_code") is not None:
            raise ValueError("ledger contains an action failure code")
        if score.get("hidden_retry_count") != 0:
            raise ValueError("ledger contains hidden retries")
        if score.get("repair_attempt_count") != 0:
            raise ValueError("ledger contains repair attempts")
        if score.get("replacement_request_count") != 0:
            raise ValueError("ledger contains replacement requests")
        if score.get("direct_model_arithmetic_fallback_used") is not False:
            raise ValueError("ledger contains a direct model arithmetic fallback")
        if score.get("raw_output_retained") is not False:
            raise ValueError("ledger retained raw output")
        scores.append(score)
    return scores


def _validate_prompt_identity_findings(
    ledger: list[dict[str, Any]],
) -> int:
    mismatch_count = 0
    for record in ledger:
        score = _require_mapping(record, "score")
        prompt_identity = _require_mapping(score, "prompt_identity")
        if prompt_identity.get("case_prompt_sha256") != record.get("source_prompt_sha256"):
            raise ValueError("score case prompt identity does not bind the source prompt")
        if prompt_identity.get("policy_sha256") != _LEGACY_SCORE_PROMPT_POLICY_SHA256:
            raise ValueError("score prompt policy does not match the observed stale identity")
        if prompt_identity.get("rendered_prompt_sha256") == record.get("rendered_prompt_sha256"):
            raise ValueError("expected stale score prompt identity mismatch was not observed")
        mismatch_count += 1
    if mismatch_count != 16:
        raise ValueError("prompt identity mismatch count must be exactly 16")
    return mismatch_count


def _validate_evaluation(
    evaluation: Mapping[str, Any],
    scores: list[Mapping[str, Any]],
) -> None:
    if evaluation.get("gate_decision") != "passed":
        raise ValueError("evaluation quality gate did not pass")
    if evaluation.get("failed_case_ids") != []:
        raise ValueError("evaluation retained failed cases")
    if evaluation.get("failure_code_counts") != {}:
        raise ValueError("evaluation retained failure-code counts")
    if evaluation.get("scores") != scores:
        raise ValueError("evaluation scores diverged from ledger scores")
    if evaluation.get("notebook_sha256") != _NOTEBOOK_SHA256:
        raise ValueError("evaluation notebook binding drifted")
    if evaluation.get("authorization_fingerprint") != _AUTHORIZATION_SHA256:
        raise ValueError("evaluation authorization binding drifted")

    metrics = _require_mapping(evaluation, "metrics")
    expected_metrics = {
        "action_json_valid",
        "action_schema_valid",
        "execution_success",
        "final_answer_accuracy",
        "first_attempt_task_success",
        "identity_accuracy",
        "operand_accuracy",
    }
    if set(metrics) != expected_metrics:
        raise ValueError("evaluation metric set drifted")
    for metric_name in sorted(expected_metrics):
        metric = _require_mapping(metrics, metric_name)
        if metric.get("passed_count") != 16:
            raise ValueError(f"metric {metric_name} did not pass all 16 cases")
        if metric.get("total_count") != 16 or metric.get("rate") != "1.0":
            raise ValueError(f"metric {metric_name} denominator or rate drifted")


def _validate_report(
    report: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> None:
    if report.get("status") != "ACTION_EXTRACTION_REQUALIFICATION_PASSED":
        raise ValueError("report terminal status drifted")
    if report.get("gate_decision") != "passed":
        raise ValueError("report gate decision drifted")
    if report.get("request_count") != 16 or report.get("required_request_count") != 16:
        raise ValueError("report request count drifted")
    if report.get("authorization_consumed") is not True:
        raise ValueError("report must mark the authorization consumed")
    if report.get("authorization_fingerprint") != _AUTHORIZATION_SHA256:
        raise ValueError("report authorization binding drifted")
    if report.get("repository_commit") != _EXECUTION_REPOSITORY_COMMIT:
        raise ValueError("report repository commit drifted")
    if report.get("notebook_sha256") != _NOTEBOOK_SHA256:
        raise ValueError("report notebook binding drifted")
    if report.get("evaluation_sha256") != canonical_json_sha256(evaluation):
        raise ValueError("report evaluation canonical digest mismatch")
    if report.get("evaluation_sha256") != _EVALUATION_CANONICAL_SHA256:
        raise ValueError("report evaluation canonical digest drifted")
    if report.get("failed_case_ids") != [] or report.get("failure_code_counts") != {}:
        raise ValueError("report retained quality failures")
    if report.get("infrastructure_failure") is not None:
        raise ValueError("report retained an infrastructure failure")
    if report.get("raw_prompt_retained") is not False:
        raise ValueError("report retained raw prompts")
    if report.get("raw_output_retained") is not False:
        raise ValueError("report retained raw outputs")
    if report.get("raw_action_retained") is not False:
        raise ValueError("report retained raw actions")
    if report.get("customer_data_used") is not False or report.get("external_spend") != "0":
        raise ValueError("report privacy or spend boundary drifted")

    cleanup = _require_mapping(report, "cleanup")
    if cleanup.get("status") != "CLEAN":
        raise ValueError("report declared cleanup status drifted")
    if cleanup.get("return_code") != 0 or cleanup.get("port_closed") is not True:
        raise ValueError("report cleanup did not close the worker boundary")
    if cleanup.get("signal_path") != ["SIGINT"]:
        raise ValueError("report cleanup signal path drifted")


def _validate_checkpoint(checkpoint: Mapping[str, Any]) -> None:
    expected = {
        "status": "completed",
        "completed_request_count": 16,
        "required_request_count": 16,
        "semantic_failure_count": 0,
        "infrastructure_failure_count": 0,
        "infrastructure_failure": None,
        "cleanup_status": "CLEAN",
        "authorization_consumed": True,
    }
    for key, expected_value in expected.items():
        if checkpoint.get(key) != expected_value:
            raise ValueError(f"checkpoint field drifted: {key}")


def _validate_summary(summary: str) -> None:
    required_lines = {
        "status=ACTION_EXTRACTION_REQUALIFICATION_PASSED",
        "completed_request_count=16",
        "required_request_count=16",
        "semantic_failure_count=0",
        "infrastructure_failure_count=0",
        "cleanup_status=CLEAN",
        f"authorization_fingerprint={_AUTHORIZATION_SHA256}",
        f"notebook_sha256={_NOTEBOOK_SHA256}",
        "authorization_consumed=true",
        "cache_measurement_in_scope=false",
        "full_measured_rerun_authorized=false",
        "external_spend=0",
        "customer_data_used=false",
    }
    observed_lines = set(summary.splitlines())
    if not required_lines.issubset(observed_lines):
        raise ValueError("summary terminal evidence is incomplete")


def _validate_worker_log(worker_log: str) -> int:
    for _, pattern in _WARNING_PATTERNS:
        if pattern not in worker_log:
            raise ValueError(f"worker warning evidence missing: {pattern}")
    if "Application shutdown complete." not in worker_log:
        raise ValueError("worker log does not prove application shutdown")
    if "Starting vLLM server on http://127.0.0.1:8001" not in worker_log:
        raise ValueError("worker log does not prove the qualified server boundary")
    return len(_WARNING_PATTERNS)


def _validate_evidence_semantics(archive: zipfile.ZipFile) -> tuple[int, int]:
    schedule = _load_json_object_bytes(
        archive.read("reconcile_balance_extraction_requalification_schedule_v2.json"),
        "reconcile_balance_extraction_requalification_schedule_v2.json",
    )
    ledger = _load_json_lines(
        archive.read("reconcile_balance_extraction_requalification_ledger_v2.jsonl"),
        "reconcile_balance_extraction_requalification_ledger_v2.jsonl",
    )
    evaluation = _load_json_object_bytes(
        archive.read("reconcile_balance_extraction_requalification_evaluation_v2.json"),
        "reconcile_balance_extraction_requalification_evaluation_v2.json",
    )
    report = _load_json_object_bytes(
        archive.read("reconcile_balance_extraction_requalification_report_v2.json"),
        "reconcile_balance_extraction_requalification_report_v2.json",
    )
    checkpoint = _load_json_object_bytes(
        archive.read("reconcile_balance_extraction_requalification_checkpoint_v2.json"),
        "reconcile_balance_extraction_requalification_checkpoint_v2.json",
    )
    summary = archive.read("RECONCILE_BALANCE_EXTRACTION_REQUALIFICATION_SUMMARY_V2.txt").decode(
        "utf-8"
    )
    worker_log = archive.read("worker_1_v2.log").decode("utf-8")

    requests = _validate_schedule(schedule)
    scores = _validate_ledger(ledger, requests)
    mismatch_count = _validate_prompt_identity_findings(ledger)
    _validate_evaluation(evaluation, scores)
    _validate_report(report, evaluation)
    _validate_checkpoint(checkpoint)
    _validate_summary(summary)
    warning_count = _validate_worker_log(worker_log)
    return mismatch_count, warning_count


def verify_action_extraction_requalification_evidence_archive(
    archive_path: Path,
) -> ActionExtractionArchiveVerificationReport:
    """Verify the immutable archive, member bytes, and semantic execution evidence."""

    if not archive_path.is_file():
        raise ActionExtractionArchiveVerificationError(
            code=ActionExtractionArchiveVerificationFailureCode.ARCHIVE_NOT_FOUND,
            message=f"evidence archive not found: {archive_path}",
        )
    archive_sha256 = sha256_file(archive_path)
    if archive_sha256 != _ARCHIVE_SHA256:
        raise ActionExtractionArchiveVerificationError(
            code=ActionExtractionArchiveVerificationFailureCode.ARCHIVE_SHA256_MISMATCH,
            message="evidence archive SHA-256 mismatch",
        )
    archive_size = archive_path.stat().st_size
    if archive_size != _ARCHIVE_SIZE_BYTES:
        raise ActionExtractionArchiveVerificationError(
            code=ActionExtractionArchiveVerificationFailureCode.ARCHIVE_SIZE_MISMATCH,
            message="evidence archive size mismatch",
        )

    try:
        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ActionExtractionArchiveVerificationError(
                    code=(ActionExtractionArchiveVerificationFailureCode.ARCHIVE_INTEGRITY_FAILED),
                    message=f"evidence archive integrity failed at {bad_member}",
                )
            observed_names = tuple(archive.namelist())
            expected_names = tuple(filename for filename, _ in _EXPECTED_MEMBER_HASHES)
            if observed_names != expected_names:
                raise ActionExtractionArchiveVerificationError(
                    code=ActionExtractionArchiveVerificationFailureCode.MEMBER_SET_MISMATCH,
                    message="evidence archive member order or set mismatch",
                )
            for filename, expected_sha256 in _EXPECTED_MEMBER_HASHES:
                actual_sha256 = hashlib.sha256(archive.read(filename)).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ActionExtractionArchiveVerificationError(
                        code=(
                            ActionExtractionArchiveVerificationFailureCode.MEMBER_SHA256_MISMATCH
                        ),
                        message=f"evidence member SHA-256 mismatch: {filename}",
                    )
            try:
                mismatch_count, warning_count = _validate_evidence_semantics(archive)
                if mismatch_count != 16 or warning_count != 7:
                    raise ValueError("verified evidence counts drifted")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ActionExtractionArchiveVerificationError(
                    code=(
                        ActionExtractionArchiveVerificationFailureCode.SEMANTIC_VALIDATION_FAILED
                    ),
                    message=f"evidence semantic validation failed: {exc}",
                ) from exc
    except zipfile.BadZipFile as exc:
        raise ActionExtractionArchiveVerificationError(
            code=ActionExtractionArchiveVerificationFailureCode.ARCHIVE_INTEGRITY_FAILED,
            message="evidence archive is not a valid ZIP file",
        ) from exc

    return ActionExtractionArchiveVerificationReport(
        archive_filename=archive_path.name,
        archive_sha256=archive_sha256,
        archive_size_bytes=archive_size,
        member_count=len(_EXPECTED_MEMBER_HASHES),
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return cast(dict[str, Any], payload)


def load_action_extraction_requalification_governance_package(
    *,
    audit_path: Path,
    certificate_json_path: Path,
    certificate_markdown_path: Path,
    consumption_path: Path,
) -> ActionExtractionGovernancePackage:
    """Load and validate the complete immutable v2 governance package."""

    audit = ActionExtractionRequalificationEvidenceAudit.model_validate(
        _load_json_object(audit_path)
    )
    certificate = ActionExtractionRequalificationCertificate.model_validate(
        _load_json_object(certificate_json_path)
    )
    consumption = ActionExtractionAuthorizationConsumption.model_validate(
        _load_json_object(consumption_path)
    )
    if sha256_file(certificate_markdown_path) != audit.certificate_markdown_sha256:
        raise ValueError("certificate Markdown SHA-256 mismatch")
    package = ActionExtractionGovernancePackage(
        audit=audit,
        certificate=certificate,
        consumption=consumption,
    )
    return package


def assert_action_extraction_v2_authorization_not_reusable(
    consumption: ActionExtractionAuthorizationConsumption,
) -> None:
    """Fail closed for every attempted reuse of the consumed v2 authorization."""

    if consumption.lifecycle_state is ActionExtractionAuthorizationLifecycleState.CONSUMED:
        raise ActionExtractionAuthorizationConsumedError()
    raise AssertionError("unreachable authorization lifecycle state")
