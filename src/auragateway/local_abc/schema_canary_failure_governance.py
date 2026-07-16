"""Governance contracts for the consumed schema-canary rerun v2.3."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_AUTHORIZATION_SHA256: Final[
    Literal["7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66"]
] = "7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66"
_RUN_ID: Final[Literal["auragateway-schema-canary-rerun-v2-bf55bf4de546"]] = (
    "auragateway-schema-canary-rerun-v2-bf55bf4de546"
)
_REPOSITORY_COMMIT: Final[Literal["5d8170b5f33f9bff07a3f6c0db3f90b5399a1bae"]] = (
    "5d8170b5f33f9bff07a3f6c0db3f90b5399a1bae"
)
_EXPECTED_OBSERVED_IDENTITIES = (
    ("incident-severity", 1),
    ("incident-severity", 2),
    ("payment-reconciliation", 1),
)
_EXPECTED_UNOBSERVED_IDENTITIES = (
    ("payment-reconciliation", 2),
    ("data-sharing-policy", 1),
    ("data-sharing-policy", 2),
)


class SchemaCanaryRerunV23Classification(StrEnum):
    """Evidence-bounded classification for the corrected rerun."""

    CERTIFIED_FAILED_DIAGNOSTIC = "certified_failed_diagnostic"


class SchemaCanaryRequestObservationState(StrEnum):
    """Explicit observation state for one authorized request."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_OBSERVED = "not_observed"


class SchemaCanaryRerunV23FailureCode(StrEnum):
    """Terminal semantic failure retained from the corrected rerun."""

    OUTPUT_ANSWER_MISMATCH = "OUTPUT_ANSWER_MISMATCH"


class SchemaCanaryAuthorizationLifecycleState(StrEnum):
    """Lifecycle state for the bounded rerun authorization."""

    CONSUMED = "consumed"


class SchemaCanaryAuthorizationReuseFailureCode(StrEnum):
    """Stable error code for prohibited authorization reuse."""

    AUTHORIZATION_CONSUMED = "SCHEMA_CANARY_RERUN_V2_AUTHORIZATION_CONSUMED"


class SchemaCanaryAuthorizationConsumedError(RuntimeError):
    """Raised when code attempts to reuse the consumed v2 authorization."""

    def __init__(
        self,
        message: str = "schema-canary rerun v2 authorization is consumed",
    ) -> None:
        super().__init__(message)
        self.code = SchemaCanaryAuthorizationReuseFailureCode.AUTHORIZATION_CONSUMED


class ObservedSchemaCanaryRequest(LocalABCContract):
    """Evidence-safe result for one request that reached model execution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: Literal[
        "incident-severity",
        "payment-reconciliation",
        "data-sharing-policy",
    ]
    turn_index: Literal[1, 2]
    state: Literal[
        SchemaCanaryRequestObservationState.PASSED,
        SchemaCanaryRequestObservationState.FAILED,
    ]
    worker_id: Literal["worker_1"] = "worker_1"
    status_code: Literal[200] = 200
    planned_prompt_tokens: int = Field(ge=1)
    api_prompt_tokens: int = Field(ge=1)
    metric_prompt_tokens: int = Field(ge=1)
    cached_prefix_tokens: int = Field(ge=0)
    newly_computed_prefill_tokens: int = Field(ge=0)
    eligible_shared_prefix_tokens: int | None = Field(default=None, ge=1)
    quality_passed: bool
    schema_validation_passed: Literal[True] = True
    telemetry_valid: Literal[True] = True
    cache_gate_passed: Literal[True] = True
    failure_codes: tuple[SchemaCanaryRerunV23FailureCode, ...] = ()
    output_text_sha256: str
    rendered_text_sha256: str
    normalized_token_ids_sha256: str
    request_body_sha256: str

    @field_validator(
        "output_text_sha256",
        "rendered_text_sha256",
        "normalized_token_ids_sha256",
        "request_body_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("request digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_observed_boundary(self) -> Self:
        if not (self.planned_prompt_tokens == self.api_prompt_tokens == self.metric_prompt_tokens):
            raise ValueError("planned, API, and metric prompt tokens must agree")
        if (
            self.cached_prefix_tokens + self.newly_computed_prefill_tokens
            != self.metric_prompt_tokens
        ):
            raise ValueError("cached plus computed prompt tokens must equal metric tokens")
        if self.state is SchemaCanaryRequestObservationState.PASSED and (
            not self.quality_passed or self.failure_codes
        ):
            raise ValueError("passed requests cannot retain quality failures")
        if self.state is SchemaCanaryRequestObservationState.FAILED:
            if self.quality_passed:
                raise ValueError("failed requests cannot pass quality")
            expected = (SchemaCanaryRerunV23FailureCode.OUTPUT_ANSWER_MISMATCH,)
            if self.failure_codes != expected:
                raise ValueError("failed request must preserve the answer mismatch")
        if self.turn_index == 1:
            if self.cached_prefix_tokens != 0:
                raise ValueError("observed turn-one requests must remain cold")
            if self.eligible_shared_prefix_tokens is not None:
                raise ValueError("turn-one requests cannot claim shared-prefix reuse")
        if self.turn_index == 2:
            if self.cached_prefix_tokens <= 0:
                raise ValueError("observed turn-two request must retain positive cache")
            if self.eligible_shared_prefix_tokens is None:
                raise ValueError("turn-two request must retain eligible prefix tokens")
            if self.cached_prefix_tokens > self.eligible_shared_prefix_tokens:
                raise ValueError("cached tokens cannot exceed the eligible shared prefix")
        return self


class UnobservedSchemaCanaryRequest(LocalABCContract):
    """Explicit request that was authorized but never executed."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: Literal[
        "incident-severity",
        "payment-reconciliation",
        "data-sharing-policy",
    ]
    turn_index: Literal[1, 2]
    state: Literal[SchemaCanaryRequestObservationState.NOT_OBSERVED] = (
        SchemaCanaryRequestObservationState.NOT_OBSERVED
    )
    reason: Literal["zero_failure_abort_before_request"] = "zero_failure_abort_before_request"
    cache_conclusion: Literal["not_observed"] = "not_observed"


class SchemaCanaryRerunV23EvidenceAudit(LocalABCContract):
    """Immutable audit over the executed and unobserved v2.3 scope."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit_id: Literal["auragateway-schema-canary-rerun-v2-3-failure-audit-v1"] = (
        "auragateway-schema-canary-rerun-v2-3-failure-audit-v1"
    )
    audited_at: datetime
    classification: Literal[SchemaCanaryRerunV23Classification.CERTIFIED_FAILED_DIAGNOSTIC] = (
        SchemaCanaryRerunV23Classification.CERTIFIED_FAILED_DIAGNOSTIC
    )
    evidence_archive_filename: Literal[
        "auragateway-schema-constrained-quality-cache-canary-rerun-v2-evidence.zip"
    ]
    evidence_archive_sha256: str
    evidence_report_sha256: str
    evidence_ledger_sha256: str
    evidence_checkpoint_sha256: str
    evidence_schedule_sha256: str
    repository_commit: Literal["5d8170b5f33f9bff07a3f6c0db3f90b5399a1bae"] = _REPOSITORY_COMMIT
    run_id: Literal["auragateway-schema-canary-rerun-v2-bf55bf4de546"] = _RUN_ID
    authorization_sha256: Literal[
        "7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66"
    ] = _AUTHORIZATION_SHA256
    failed_predecessor_audit_sha256: str
    token_normalization_policy_sha256: str
    preserved_scope_sha256: str
    reported_status: Literal["SCHEMA_CONSTRAINED_QUALITY_CACHE_CANARY_RERUN_FAILED"] = (
        "SCHEMA_CONSTRAINED_QUALITY_CACHE_CANARY_RERUN_FAILED"
    )
    checkpoint_status: Literal["failed"] = "failed"
    cleanup_status: Literal["CLEAN"] = "CLEAN"
    planned_trajectory_count: Literal[3] = 3
    planned_request_count: Literal[6] = 6
    retained_trajectory_count: Literal[2] = 2
    completed_request_count: Literal[3] = 3
    failure_count: Literal[1] = 1
    abort_reason: Literal["TURN_FAILED"] = "TURN_FAILED"
    observed_requests: tuple[
        ObservedSchemaCanaryRequest,
        ObservedSchemaCanaryRequest,
        ObservedSchemaCanaryRequest,
    ]
    unobserved_requests: tuple[
        UnobservedSchemaCanaryRequest,
        UnobservedSchemaCanaryRequest,
        UnobservedSchemaCanaryRequest,
    ]
    hidden_retry_count: Literal[0] = 0
    replacement_trajectory_count: Literal[0] = 0
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Decimal = Decimal("0")
    full_measured_rerun_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    certificate_id: Literal["auragateway-local-abc-sfrc-0001"]
    certificate_status: Literal["CERTIFIED_FAILED_DIAGNOSTIC"]
    certificate_json_filename: Literal[
        "schema_canary_rerun_v2_3_semi_formal_reasoning_certificate_v1.json"
    ]
    certificate_json_sha256: str
    certificate_markdown_filename: Literal[
        "local_abc_schema_canary_rerun_v2_3_semi_formal_reasoning_certificate_v1.md"
    ]
    certificate_markdown_sha256: str
    adr_id: Literal["ADR-2026-07-16-LOCAL-ABC-ARITHMETIC-ACTION-REALIZATION"]
    adr_repository_path: Literal[
        "docs/adr/2026-07-16-local-abc-deterministic-arithmetic-action-realization.md"
    ]
    adr_git_blob_sha: Literal["bbd704fed0f112d07fff2ebbef20d70e2166438d"]
    next_gate: Literal["typed_deterministic_arithmetic_action_realization_governance"] = (
        "typed_deterministic_arithmetic_action_realization_governance"
    )

    @field_validator("audited_at")
    @classmethod
    def validate_audited_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("audited_at must be timezone-aware")
        return value

    @field_validator(
        "evidence_archive_sha256",
        "evidence_report_sha256",
        "evidence_ledger_sha256",
        "evidence_checkpoint_sha256",
        "evidence_schedule_sha256",
        "failed_predecessor_audit_sha256",
        "token_normalization_policy_sha256",
        "preserved_scope_sha256",
        "certificate_json_sha256",
        "certificate_markdown_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("audit digests must be lowercase SHA-256")
        return value

    @field_validator("adr_git_blob_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("ADR Git blob identity must be lowercase SHA-1")
        return value

    @model_validator(mode="after")
    def validate_exact_failure_boundary(self) -> Self:
        observed_identities = tuple(
            (request.case_id, request.turn_index) for request in self.observed_requests
        )
        if observed_identities != _EXPECTED_OBSERVED_IDENTITIES:
            raise ValueError("audit must preserve exact observed request order")

        unobserved_identities = tuple(
            (request.case_id, request.turn_index) for request in self.unobserved_requests
        )
        if unobserved_identities != _EXPECTED_UNOBSERVED_IDENTITIES:
            raise ValueError("audit must preserve exact unobserved request order")

        incident_turn_one, incident_turn_two, payment_turn_one = self.observed_requests
        if (
            incident_turn_one.planned_prompt_tokens,
            incident_turn_one.cached_prefix_tokens,
            incident_turn_one.newly_computed_prefill_tokens,
        ) != (282, 0, 282):
            raise ValueError("incident turn one telemetry drifted")
        if (
            incident_turn_two.planned_prompt_tokens,
            incident_turn_two.cached_prefix_tokens,
            incident_turn_two.newly_computed_prefill_tokens,
            incident_turn_two.eligible_shared_prefix_tokens,
        ) != (290, 192, 98, 205):
            raise ValueError("incident turn two cache evidence drifted")
        if (
            payment_turn_one.planned_prompt_tokens,
            payment_turn_one.cached_prefix_tokens,
            payment_turn_one.newly_computed_prefill_tokens,
        ) != (289, 0, 289):
            raise ValueError("payment turn one telemetry drifted")
        if payment_turn_one.state is not SchemaCanaryRequestObservationState.FAILED:
            raise ValueError("payment turn one must remain failed")
        if self.completed_request_count != len(self.observed_requests):
            raise ValueError("completed request count must equal observed records")
        if self.planned_request_count - self.completed_request_count != len(
            self.unobserved_requests
        ):
            raise ValueError("unobserved request count must close the planned scope")
        if self.external_spend != Decimal("0"):
            raise ValueError("external spend must remain zero")
        return self


class SchemaCanaryRerunV2AuthorizationConsumption(LocalABCContract):
    """Immutable lifecycle record preventing reuse of the executed authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: Literal["auragateway-schema-canary-rerun-v2-authorization-consumption-v1"] = (
        "auragateway-schema-canary-rerun-v2-authorization-consumption-v1"
    )
    consumed_at: datetime
    authorization_sha256: Literal[
        "7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66"
    ] = _AUTHORIZATION_SHA256
    lifecycle_state: Literal[SchemaCanaryAuthorizationLifecycleState.CONSUMED] = (
        SchemaCanaryAuthorizationLifecycleState.CONSUMED
    )
    consumed_by_run_id: Literal["auragateway-schema-canary-rerun-v2-bf55bf4de546"] = _RUN_ID
    evidence_audit_sha256: str
    certificate_json_sha256: str
    execution_started: Literal[True] = True
    observed_request_count: Literal[3] = 3
    reusable: Literal[False] = False
    execution_authorized: Literal[False] = False
    corrected_notebook_generation_permitted: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["typed_deterministic_arithmetic_action_realization_governance"] = (
        "typed_deterministic_arithmetic_action_realization_governance"
    )

    @field_validator("consumed_at")
    @classmethod
    def validate_consumed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must be timezone-aware")
        return value

    @field_validator("evidence_audit_sha256", "certificate_json_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("consumption digests must be lowercase SHA-256")
        return value


class SchemaCanaryRerunV23GovernancePackage(LocalABCContract):
    """Cross-file governance binding for audit, certificate, and consumption."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit: SchemaCanaryRerunV23EvidenceAudit
    consumption: SchemaCanaryRerunV2AuthorizationConsumption

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.consumption.authorization_sha256 != self.audit.authorization_sha256:
            raise ValueError("consumption record must bind the audited authorization")
        if self.consumption.consumed_by_run_id != self.audit.run_id:
            raise ValueError("consumption record must bind the audited run")
        if self.consumption.evidence_audit_sha256 != self.audit.fingerprint():
            raise ValueError("consumption record must bind the evidence audit")
        if self.consumption.certificate_json_sha256 != self.audit.certificate_json_sha256:
            raise ValueError("consumption record must bind the certificate")
        return self


def sha256_file(path: Path) -> str:
    """Hash one file without loading evidence payloads into logs."""

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
    audit: SchemaCanaryRerunV23EvidenceAudit,
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
    if evidence_bindings.get("repository_commit") != audit.repository_commit:
        raise ValueError("certificate repository binding mismatch")
    if evidence_bindings.get("run_id") != audit.run_id:
        raise ValueError("certificate run binding mismatch")

    formal_conclusion = _require_mapping(payload, "formal_conclusion")
    if formal_conclusion.get("verdict") != audit.certificate_status:
        raise ValueError("certificate conclusion mismatch")

    decision_boundary = _require_mapping(payload, "adr_decision_boundary")
    if decision_boundary.get("certificate_does_not_choose_option") is not True:
        raise ValueError("certificate must not pre-empt the ADR decision")


def load_schema_canary_rerun_v23_governance_package(
    *,
    audit_path: Path,
    consumption_path: Path,
    certificate_json_path: Path,
    certificate_markdown_path: Path,
) -> SchemaCanaryRerunV23GovernancePackage:
    """Load and validate the complete failed-canary governance package."""

    audit = SchemaCanaryRerunV23EvidenceAudit.model_validate(_load_json_object(audit_path))
    consumption = SchemaCanaryRerunV2AuthorizationConsumption.model_validate(
        _load_json_object(consumption_path)
    )
    package = SchemaCanaryRerunV23GovernancePackage(
        audit=audit,
        consumption=consumption,
    )
    _validate_certificate_files(
        audit=audit,
        certificate_json_path=certificate_json_path,
        certificate_markdown_path=certificate_markdown_path,
    )
    return package


def reject_schema_canary_rerun_v2_authorization_reuse(
    *,
    authorization_fingerprint: str,
    consumption: SchemaCanaryRerunV2AuthorizationConsumption,
) -> None:
    """Fail closed when the executed v2 authorization is presented again."""

    if _SHA256_PATTERN.fullmatch(authorization_fingerprint) is None:
        raise ValueError("authorization fingerprint must be lowercase SHA-256")
    if authorization_fingerprint != consumption.authorization_sha256:
        raise ValueError("consumption record does not govern this authorization")
    raise SchemaCanaryAuthorizationConsumedError()
