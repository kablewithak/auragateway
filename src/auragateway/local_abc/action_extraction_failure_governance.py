"""Immutable governance for the reconcile-balance action-extraction canary."""

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

from auragateway.local_abc.arithmetic_action import (
    ReconcileBalanceAction,
    ReconcileBalanceResult,
    execute_reconcile_balance,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_AUTHORIZATION_SHA256 = "9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9"
_EXECUTION_SOURCE_COMMIT = "0619867a7acbee5e4c5b639963cf1046cbf36809"
_NOTEBOOK_SHA256 = "b0d3f840e6d334c6b7631431228ef9ff50a7ea55f8eabceb65fcf4685a1ad5ab"
_ARCHIVE_SHA256 = "412db1700b6505502ca9afc83981738c9f50f043bad6de37e015ab7f3a9944c8"
_SOURCE_CERTIFICATE_MARKDOWN_SHA256 = (
    "2bba7783be895dcedb3b4fa89dee94ed3750310f0383feb5cb790240987ee6eb"
)

_EXPECTED_MEMBER_HASHES = (
    (
        "RECONCILE_BALANCE_EXTRACTION_CANARY_SUMMARY.txt",
        "9330ba95ef0be33060209d6e6f53d93abba6cdc0e5d5922352866f78924ab6d3",
    ),
    (
        "model_snapshot_manifest_v1.json",
        "0538a07daf47cd53953c174aedd2972708309c0fccff00c9ef5c11af19300d71",
    ),
    (
        "reconcile_balance_extraction_canary_checkpoint_v1.json",
        "f82afe98508af947a0d4093f2b0d321d8a232f0b992bc1cad915d9f9dfa7173e",
    ),
    (
        "reconcile_balance_extraction_canary_evaluation_v1.json",
        "ca9358c2692e4a1ddde5d8d0ff9160b5210e75ff5ca08b0128cb0ccfb65594db",
    ),
    (
        "reconcile_balance_extraction_canary_ledger_v1.jsonl",
        "edac0a618d6e56843b749548a4e16b295eabdb4d23972bcdea9b7d07a8872c53",
    ),
    (
        "reconcile_balance_extraction_canary_report_v1.json",
        "9e1734e9af2b18170156db172ae087aab99ff122af5391ee1cfa07e4c9210207",
    ),
    (
        "reconcile_balance_extraction_canary_schedule_v1.json",
        "d6cad7b3f319a0feff428b5d002509107fa30058ad8c53f20c0d1f49652b866f",
    ),
    (
        "worker_1.log",
        "cc1673a44c0d180ba98209c76c6f7d14ad2d0b90f65f3ae83a2162fee569452b",
    ),
)


class ActionExtractionCanaryClassification(StrEnum):
    """Terminal evidence classification for the governed canary."""

    FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS = "CERTIFIED_FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS"


class ActionExtractionFailureCode(StrEnum):
    """Exact semantic failure families reconstructed from retained hashes."""

    FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED = "FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED"
    KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL = "KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL"


class ActionExtractionRuntimeWarningCode(StrEnum):
    """Non-fatal runtime warnings retained without reclassifying the run."""

    ISOLATED_RUNTIME_SITECUSTOMIZE_WARNING = "NON_FATAL_ISOLATED_RUNTIME_SITECUSTOMIZE_WARNING"
    PROCESS_RESOURCE_WARNING = "NON_FATAL_PROCESS_RESOURCE_WARNING"


class ActionExtractionAuthorizationLifecycleState(StrEnum):
    """Lifecycle state of the one-shot canary authorization."""

    CONSUMED = "consumed"


class ActionExtractionArchiveVerificationFailureCode(StrEnum):
    """Stable failure codes for optional protected-archive verification."""

    ARCHIVE_NOT_FOUND = "ACTION_EXTRACTION_EVIDENCE_ARCHIVE_NOT_FOUND"
    ARCHIVE_SHA256_MISMATCH = "ACTION_EXTRACTION_EVIDENCE_ARCHIVE_SHA256_MISMATCH"
    ARCHIVE_INTEGRITY_FAILED = "ACTION_EXTRACTION_EVIDENCE_ARCHIVE_INTEGRITY_FAILED"
    ARCHIVE_MEMBER_SET_MISMATCH = "ACTION_EXTRACTION_EVIDENCE_MEMBER_SET_MISMATCH"
    ARCHIVE_MEMBER_SHA256_MISMATCH = "ACTION_EXTRACTION_EVIDENCE_MEMBER_SHA256_MISMATCH"


class ActionExtractionAuthorizationReuseFailureCode(StrEnum):
    """Stable failure code for prohibited authorization reuse."""

    AUTHORIZATION_CONSUMED = "ACTION_EXTRACTION_CANARY_AUTHORIZATION_CONSUMED"


class ActionExtractionArchiveVerificationError(RuntimeError):
    """Raised when the optional protected evidence archive does not verify."""

    def __init__(
        self,
        *,
        code: ActionExtractionArchiveVerificationFailureCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


class ActionExtractionAuthorizationConsumedError(RuntimeError):
    """Raised when code attempts to reuse the completed canary authorization."""

    def __init__(
        self,
        message: str = "action-extraction canary authorization is consumed",
    ) -> None:
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
    """Frozen source, notebook, manifest, plan, prompt, and schema identities."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_sha256: str
    execution_source_commit: str
    notebook_filename: Literal["auragateway_v2_reconcile_balance_action_extraction_canary_v1.ipynb"]
    notebook_sha256: str
    notebook_code_source_sha256: str
    case_manifest_sha256: str
    evaluation_plan_sha256: str
    prompt_policy_sha256: str
    action_schema_sha256: str

    @field_validator(
        "authorization_sha256",
        "notebook_sha256",
        "notebook_code_source_sha256",
        "case_manifest_sha256",
        "evaluation_plan_sha256",
        "prompt_policy_sha256",
        "action_schema_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact bindings must be lowercase SHA-256")
        return value

    @field_validator("execution_source_commit")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("execution source commit must be lowercase Git SHA-1")
        return value


class ActionExtractionModelBinding(LocalABCContract):
    """Exact model identity retained by the completed canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    weights_sha256: Literal["fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"]


class ActionExtractionRuntimeBinding(LocalABCContract):
    """Exact isolated runtime identity retained by the completed canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    runtime_policy: Literal["isolated_venv_exact_torch_cu129_v2"]
    venv_bootstrap_policy: Literal["without_pip_host_pip_python_v1"]
    system_site_packages_inherited: Literal[False] = False
    python_version: Literal["3.12"]
    torch_version: Literal["2.11.0+cu129"]
    cuda_version: Literal["12.9"]
    vllm_module_version: Literal["0.25.1"]
    vllm_distribution_version: Literal["0.25.1+cu129"]
    gpu_count: Literal[2] = 2
    gpu_model: Literal["Tesla T4"]
    compute_capability: Literal["7.5"]
    worker_id: Literal["worker_1"]
    worker_port: Literal[8001] = 8001
    binary_import_probe_passed: Literal[True] = True


class ActionExtractionCanaryMetrics(LocalABCContract):
    """Exact aggregate execution and quality counts."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorized_requests: Literal[12] = 12
    completed_requests: Literal[12] = 12
    http_200_responses: Literal[12] = 12
    valid_action_json: Literal[12] = 12
    valid_action_schema: Literal[12] = 12
    exact_identity_matches: Literal[12] = 12
    deterministic_execution_successes: Literal[12] = 12
    exact_operand_matches: Literal[10] = 10
    exact_final_answer_matches: Literal[10] = 10
    first_attempt_task_successes: Literal[10] = 10
    semantic_failures: Literal[2] = 2
    infrastructure_failures: Literal[0] = 0
    hidden_retries: Literal[0] = 0
    repairs: Literal[0] = 0
    replacement_requests: Literal[0] = 0
    direct_model_arithmetic_fallbacks: Literal[0] = 0
    cleanup_status: Literal["CLEAN"] = "CLEAN"
    worker_return_code: Literal[0] = 0
    worker_port_closed: Literal[True] = True
    gate_decision: Literal["failed"] = "failed"


class ActionExtractionPrivacyBoundary(LocalABCContract):
    """Evidence-minimization and spend boundary."""

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


class ActionExtractionRuntimeWarning(LocalABCContract):
    """Non-fatal warning classification retained separately from run status."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    code: ActionExtractionRuntimeWarningCode
    infrastructure_failure: Literal[False] = False
    blocks_evidence_audit: Literal[False] = False
    requires_follow_up: Literal[True] = True


class HashResolvedActionExtractionFailure(LocalABCContract):
    """Exact expected and observed actions proved by action and result hashes."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    eval_case_id: Literal["formatted-currency-values", "key-value-layout"]
    failure_code: ActionExtractionFailureCode
    expected_action: ReconcileBalanceAction
    observed_action: ReconcileBalanceAction
    expected_answer: int
    observed_result: ReconcileBalanceResult
    retained_action_sha256: str
    retained_result_sha256: str

    @field_validator("retained_action_sha256", "retained_result_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("failure proof digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_hash_resolved_failure(self) -> Self:
        expected_result = execute_reconcile_balance(self.expected_action)
        if expected_result.answer != self.expected_answer:
            raise ValueError("expected answer must follow deterministic execution")

        observed_result = execute_reconcile_balance(self.observed_action)
        if observed_result != self.observed_result:
            raise ValueError("observed result must follow deterministic execution")
        if self.observed_action.fingerprint() != self.retained_action_sha256:
            raise ValueError("observed action hash does not match retained evidence")
        if self.observed_result.fingerprint() != self.retained_result_sha256:
            raise ValueError("observed result hash does not match retained evidence")

        expected_identity = ("payment-reconciliation", 1)
        if (
            self.expected_action.case_id,
            self.expected_action.turn_index,
        ) != expected_identity:
            raise ValueError("expected action identity drifted")
        if (
            self.observed_action.case_id,
            self.observed_action.turn_index,
        ) != expected_identity:
            raise ValueError("observed action identity drifted")

        if self.eval_case_id == "formatted-currency-values":
            expected_operands = (1200, 300, 50)
            observed_operands = (200, 300, 50)
            expected_code = ActionExtractionFailureCode.FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
            expected_answer = 1450
            observed_answer = 450
        else:
            expected_operands = (5000, 250, 1250)
            observed_operands = (5000, 1250, 250)
            expected_code = ActionExtractionFailureCode.KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
            expected_answer = 4000
            observed_answer = 6000

        expected_tuple = (
            self.expected_action.opening_balance,
            self.expected_action.credits,
            self.expected_action.debits,
        )
        observed_tuple = (
            self.observed_action.opening_balance,
            self.observed_action.credits,
            self.observed_action.debits,
        )
        if expected_tuple != expected_operands:
            raise ValueError("expected failure operands drifted")
        if observed_tuple != observed_operands:
            raise ValueError("observed failure operands drifted")
        if self.failure_code is not expected_code:
            raise ValueError("failure code does not match the exact failure family")
        if self.expected_answer != expected_answer:
            raise ValueError("expected answer drifted")
        if self.observed_result.answer != observed_answer:
            raise ValueError("observed answer drifted")
        return self


class ActionExtractionCanaryEvidenceAudit(LocalABCContract):
    """Immutable, queryable audit over the completed action-extraction canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit_id: Literal["auragateway-reconcile-balance-action-extraction-canary-evidence-audit-v1"]
    audited_at: datetime
    classification: Literal[
        ActionExtractionCanaryClassification.FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS
    ]
    evidence_archive_filename: Literal[
        "auragateway-reconcile-balance-action-extraction-canary-evidence-v1.zip"
    ]
    evidence_archive_sha256: str
    evidence_archive_size_bytes: Literal[18837] = 18837
    evidence_member_count: Literal[8] = 8
    evidence_members: tuple[ActionExtractionEvidenceMember, ...]
    artifacts: ActionExtractionArtifactBinding
    model: ActionExtractionModelBinding
    runtime: ActionExtractionRuntimeBinding
    metrics: ActionExtractionCanaryMetrics
    failed_case_ids: tuple[
        Literal["formatted-currency-values"],
        Literal["key-value-layout"],
    ]
    failures: tuple[
        HashResolvedActionExtractionFailure,
        HashResolvedActionExtractionFailure,
    ]
    runtime_warnings: tuple[
        ActionExtractionRuntimeWarning,
        ActionExtractionRuntimeWarning,
    ]
    privacy: ActionExtractionPrivacyBoundary
    authorization_consumed: Literal[True] = True
    same_authorization_rerun_permitted: Literal[False] = False
    retry_only_failed_cases_permitted: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    certificate_id: Literal["AURAGATEWAY-LOCAL-ABC-SFRC-0003"]
    certificate_status: Literal["CERTIFIED_FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS"]
    certificate_json_filename: Literal[
        "reconcile_balance_extraction_canary_semi_formal_reasoning_certificate_v1.json"
    ]
    certificate_json_sha256: str
    source_certificate_markdown_sha256: str
    certificate_markdown_filename: Literal[
        "local_abc_reconcile_balance_action_extraction_canary_"
        "semi_formal_reasoning_certificate_v1.md"
    ]
    certificate_markdown_sha256: str
    next_gate: Literal["versioned_action_extraction_remediation_design"] = (
        "versioned_action_extraction_remediation_design"
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
        "source_certificate_markdown_sha256",
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
            raise ValueError("audit must preserve the exact evidence member order and hashes")
        return value

    @model_validator(mode="after")
    def validate_terminal_boundary(self) -> Self:
        if self.evidence_archive_sha256 != _ARCHIVE_SHA256:
            raise ValueError("evidence archive digest drifted")
        if self.source_certificate_markdown_sha256 != (_SOURCE_CERTIFICATE_MARKDOWN_SHA256):
            raise ValueError("source certificate Markdown digest drifted")
        if self.artifacts.authorization_sha256 != _AUTHORIZATION_SHA256:
            raise ValueError("authorization binding drifted")
        if self.artifacts.execution_source_commit != _EXECUTION_SOURCE_COMMIT:
            raise ValueError("execution source binding drifted")
        if self.artifacts.notebook_sha256 != _NOTEBOOK_SHA256:
            raise ValueError("notebook binding drifted")

        expected_failed_ids = ("formatted-currency-values", "key-value-layout")
        if self.failed_case_ids != expected_failed_ids:
            raise ValueError("audit must preserve the exact failed case order")
        if tuple(failure.eval_case_id for failure in self.failures) != expected_failed_ids:
            raise ValueError("failure proofs must match the exact failed case order")

        expected_warning_codes = tuple(ActionExtractionRuntimeWarningCode)
        if tuple(warning.code for warning in self.runtime_warnings) != expected_warning_codes:
            raise ValueError("audit must preserve both non-fatal runtime warnings")
        return self


class ActionExtractionCanaryAuthorizationConsumption(LocalABCContract):
    """Immutable lifecycle record that prevents reuse of the completed authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: Literal[
        "auragateway-reconcile-balance-action-extraction-canary-authorization-consumption-v1"
    ]
    consumed_at: datetime
    authorization_sha256: str
    lifecycle_state: Literal[ActionExtractionAuthorizationLifecycleState.CONSUMED]
    evidence_audit_sha256: str
    certificate_json_sha256: str
    completed_request_count: Literal[12] = 12
    reusable: Literal[False] = False
    execution_authorized: Literal[False] = False
    retry_only_failed_cases_permitted: Literal[False] = False
    corrected_notebook_generation_permitted: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["versioned_action_extraction_remediation_design"] = (
        "versioned_action_extraction_remediation_design"
    )

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


class ActionExtractionCanaryGovernancePackage(LocalABCContract):
    """Cross-file binding for audit, certificate, and authorization consumption."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit: ActionExtractionCanaryEvidenceAudit
    consumption: ActionExtractionCanaryAuthorizationConsumption

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.consumption.authorization_sha256 != self.audit.artifacts.authorization_sha256:
            raise ValueError("consumption must bind the audited authorization")
        if self.consumption.evidence_audit_sha256 != self.audit.fingerprint():
            raise ValueError("consumption must bind the audit fingerprint")
        if self.consumption.certificate_json_sha256 != self.audit.certificate_json_sha256:
            raise ValueError("consumption must bind the certificate JSON")
        return self


class ActionExtractionArchiveVerificationReport(LocalABCContract):
    """Successful verification result without exposing protected evidence content."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    archive_filename: str
    archive_sha256: str
    archive_size_bytes: int = Field(gt=0)
    member_count: int = Field(gt=0)
    member_hashes_verified: Literal[True] = True
    zip_integrity_passed: Literal[True] = True

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


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return cast(dict[str, Any], payload)


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"certificate field {key} must be an object")
    return cast(Mapping[str, Any], value)


def _validate_certificate_files(
    *,
    audit: ActionExtractionCanaryEvidenceAudit,
    certificate_json_path: Path,
    certificate_markdown_path: Path,
) -> None:
    if sha256_file(certificate_json_path) != audit.certificate_json_sha256:
        raise ValueError("certificate JSON SHA-256 mismatch")
    if sha256_file(certificate_markdown_path) != audit.certificate_markdown_sha256:
        raise ValueError("certificate Markdown SHA-256 mismatch")

    payload = _load_json_object(certificate_json_path)
    if payload.get("certificate_id") != audit.certificate_id:
        raise ValueError("certificate ID mismatch")
    if payload.get("status") != audit.certificate_status:
        raise ValueError("certificate status mismatch")

    evidence_bindings = _require_mapping(payload, "evidence_bindings")
    if evidence_bindings.get("archive_sha256") != audit.evidence_archive_sha256:
        raise ValueError("certificate archive binding mismatch")
    if evidence_bindings.get("authorization_fingerprint") != audit.artifacts.authorization_sha256:
        raise ValueError("certificate authorization binding mismatch")
    if evidence_bindings.get("notebook_sha256") != audit.artifacts.notebook_sha256:
        raise ValueError("certificate notebook binding mismatch")
    if evidence_bindings.get("source_certificate_markdown_sha256") != (
        audit.source_certificate_markdown_sha256
    ):
        raise ValueError("certificate source Markdown binding mismatch")

    conclusion = _require_mapping(payload, "formal_conclusion")
    if conclusion.get("verdict") != audit.certificate_status:
        raise ValueError("certificate conclusion mismatch")


def load_action_extraction_canary_governance_package(
    *,
    audit_path: Path,
    consumption_path: Path,
    certificate_json_path: Path,
    certificate_markdown_path: Path,
) -> ActionExtractionCanaryGovernancePackage:
    """Load and validate the complete immutable canary governance package."""

    audit = ActionExtractionCanaryEvidenceAudit.model_validate(_load_json_object(audit_path))
    consumption = ActionExtractionCanaryAuthorizationConsumption.model_validate(
        _load_json_object(consumption_path)
    )
    package = ActionExtractionCanaryGovernancePackage(
        audit=audit,
        consumption=consumption,
    )
    _validate_certificate_files(
        audit=audit,
        certificate_json_path=certificate_json_path,
        certificate_markdown_path=certificate_markdown_path,
    )
    return package


def reject_action_extraction_canary_authorization_reuse(
    *,
    authorization_fingerprint: str,
    consumption: ActionExtractionCanaryAuthorizationConsumption,
) -> None:
    """Fail closed when the consumed authorization is presented again."""

    if _SHA256_PATTERN.fullmatch(authorization_fingerprint) is None:
        raise ValueError("authorization fingerprint must be lowercase SHA-256")
    if authorization_fingerprint != consumption.authorization_sha256:
        raise ValueError("consumption record does not govern this authorization")
    raise ActionExtractionAuthorizationConsumedError()


def verify_action_extraction_canary_evidence_archive(
    *,
    archive_path: Path,
    audit: ActionExtractionCanaryEvidenceAudit,
) -> ActionExtractionArchiveVerificationReport:
    """Verify protected archive bytes without retaining or logging member content."""

    if not archive_path.is_file():
        raise ActionExtractionArchiveVerificationError(
            code=ActionExtractionArchiveVerificationFailureCode.ARCHIVE_NOT_FOUND,
            message="protected action-extraction evidence archive was not found",
        )
    archive_sha256 = sha256_file(archive_path)
    if archive_sha256 != audit.evidence_archive_sha256:
        raise ActionExtractionArchiveVerificationError(
            code=(ActionExtractionArchiveVerificationFailureCode.ARCHIVE_SHA256_MISMATCH),
            message="protected action-extraction evidence archive digest mismatch",
        )

    expected_hashes = {member.filename: member.sha256 for member in audit.evidence_members}
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ActionExtractionArchiveVerificationError(
                code=(ActionExtractionArchiveVerificationFailureCode.ARCHIVE_INTEGRITY_FAILED),
                message="protected action-extraction evidence archive failed CRC verification",
            )

        member_names = tuple(info.filename for info in archive.infolist() if not info.is_dir())
        if member_names != tuple(expected_hashes):
            raise ActionExtractionArchiveVerificationError(
                code=(ActionExtractionArchiveVerificationFailureCode.ARCHIVE_MEMBER_SET_MISMATCH),
                message="protected evidence archive member order or membership mismatch",
            )

        for member_name, expected_sha256 in expected_hashes.items():
            digest = hashlib.sha256()
            with archive.open(member_name) as member:
                for chunk in iter(lambda: member.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_sha256:
                raise ActionExtractionArchiveVerificationError(
                    code=(
                        ActionExtractionArchiveVerificationFailureCode.ARCHIVE_MEMBER_SHA256_MISMATCH
                    ),
                    message=f"protected evidence member digest mismatch: {member_name}",
                )

    return ActionExtractionArchiveVerificationReport(
        archive_filename=archive_path.name,
        archive_sha256=archive_sha256,
        archive_size_bytes=archive_path.stat().st_size,
        member_count=len(expected_hashes),
    )
