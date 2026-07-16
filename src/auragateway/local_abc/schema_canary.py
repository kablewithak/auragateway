"""Audit and authorization contracts for the schema-constrained cache canary."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import (
    ConditionId,
    LocalABCContract,
    WorkerId,
)
from auragateway.local_abc.measured_quality import (
    MeasuredOutputShape,
    MeasuredQualityCheck,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_INTEGER_STRING_PATTERN = r"^[0-9]+$"
_REQUIRED_KEYS = (
    "answer",
    "case_id",
    "confidence",
    "turn_index",
)


class SchemaProbeEvidenceClassification(StrEnum):
    """Lifecycle classification for the successful predecessor probe."""

    QUALIFIED = "qualified"


class SchemaCanaryCaseId(StrEnum):
    """Frozen case identities for the six-request canary."""

    INCIDENT_SEVERITY = "incident-severity"
    PAYMENT_RECONCILIATION = "payment-reconciliation"
    DATA_SHARING_POLICY = "data-sharing-policy"


class SchemaCanaryAnswerConstraint(StrEnum):
    """Allowed structural answer-domain constraints."""

    ENUM = "enum"
    INTEGER_STRING = "integer_string"


class SchemaCanaryLifecycleStatus(StrEnum):
    """Terminal-aware lifecycle for the three-trajectory canary."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class SchemaProbeV1EvidenceAudit(LocalABCContract):
    """Immutable audit over the successful one-request schema probe."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit_id: str
    audited_at: datetime
    evidence_archive_sha256: str
    evidence_report_sha256: str
    evidence_result_sha256: str
    evidence_evaluation_sha256: str
    evidence_plan_sha256: str
    evidence_checkpoint_sha256: str
    evidence_summary_sha256: str
    model_manifest_sha256: str
    reported_status: Literal["SCHEMA_CONSTRAINED_OUTPUT_PROBE_PASSED"] = (
        "SCHEMA_CONSTRAINED_OUTPUT_PROBE_PASSED"
    )
    execution_status: Literal["SCHEMA_PROBE_PASSED"] = "SCHEMA_PROBE_PASSED"
    classification: Literal[SchemaProbeEvidenceClassification.QUALIFIED] = (
        SchemaProbeEvidenceClassification.QUALIFIED
    )
    checkpoint_status: Literal["passed"] = "passed"
    cleanup_status: Literal["CLEAN"] = "CLEAN"
    completed_request_count: Literal[1] = 1
    failure_count: Literal[0] = 0
    request_status_code: Literal[200] = 200
    prompt_token_count: Literal[282] = 282
    completion_token_count: Literal[24] = 24
    output_character_count: Literal[82] = 82
    finish_reason: Literal["stop"] = "stop"
    output_shape: Literal[MeasuredOutputShape.JSON_OBJECT] = MeasuredOutputShape.JSON_OBJECT
    output_text_sha256: str
    validated_output_sha256: str
    expected_payload_sha256: str
    response_schema_sha256: str
    request_body_sha256: str
    quality_checks_passed: tuple[
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
    ]
    schema_validation_passed: Literal[True] = True
    telemetry_valid: Literal[True] = True
    request_count_delta: Literal[1] = 1
    cached_prefix_tokens_observed_not_evaluated: Literal[0] = 0
    newly_computed_prefill_tokens: Literal[282] = 282
    privacy_finding_count: Literal[0] = 0
    worker_1_port_closed: Literal[True] = True
    worker_2_port_closed: Literal[True] = True
    cache_reuse_evaluated: Literal[False] = False
    schema_canary_authorization_permitted: Literal[True] = True
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["schema_constrained_quality_cache_canary_v1"] = (
        "schema_constrained_quality_cache_canary_v1"
    )

    @field_validator("audit_id")
    @classmethod
    def validate_audit_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("audit_id must use stable lowercase characters")
        return value

    @field_validator("audited_at")
    @classmethod
    def validate_audited_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("audited_at must be timezone-aware")
        return value

    @field_validator(
        "evidence_archive_sha256",
        "evidence_report_sha256",
        "evidence_result_sha256",
        "evidence_evaluation_sha256",
        "evidence_plan_sha256",
        "evidence_checkpoint_sha256",
        "evidence_summary_sha256",
        "model_manifest_sha256",
        "output_text_sha256",
        "validated_output_sha256",
        "expected_payload_sha256",
        "response_schema_sha256",
        "request_body_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence digests must be lowercase SHA-256")
        return value

    @field_validator("quality_checks_passed")
    @classmethod
    def validate_quality_checks(
        cls,
        value: tuple[
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
        ],
    ) -> tuple[
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
    ]:
        if value != tuple(MeasuredQualityCheck):
            raise ValueError("probe audit requires all deterministic checks")
        return value

    @model_validator(mode="after")
    def validate_output_hash_lineage(self) -> Self:
        hashes = {
            self.output_text_sha256,
            self.validated_output_sha256,
            self.expected_payload_sha256,
        }
        if len(hashes) != 1:
            raise ValueError("raw output, validated output, and expected payload hashes must match")
        return self


class SchemaCanaryCaseProfile(LocalABCContract):
    """Frozen structural schema profile for one diagnostic case."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: SchemaCanaryCaseId
    answer_constraint: SchemaCanaryAnswerConstraint
    allowed_answers: tuple[str, ...] = ()
    answer_pattern: str | None = None
    turn_indexes: tuple[Literal[1], Literal[2]] = (1, 2)

    @field_validator("allowed_answers")
    @classmethod
    def validate_allowed_answers(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("allowed answers must be unique")
        if any(not item or item.strip() != item for item in value):
            raise ValueError("allowed answers must be non-empty and trimmed")
        return value

    @model_validator(mode="after")
    def validate_answer_domain(self) -> Self:
        if self.answer_constraint is SchemaCanaryAnswerConstraint.ENUM and (
            not self.allowed_answers or self.answer_pattern is not None
        ):
            raise ValueError("enum answer constraint requires allowed answers only")
        if self.answer_constraint is SchemaCanaryAnswerConstraint.INTEGER_STRING and (
            self.allowed_answers or self.answer_pattern != _INTEGER_STRING_PATTERN
        ):
            raise ValueError("integer-string constraint requires the frozen numeric pattern")
        return self


class SchemaConstrainedQualityCanaryAuthorization(LocalABCContract):
    """Authorization for three schema-constrained two-turn trajectories."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    canary_id: str
    issued_at: datetime
    decision: Literal["authorized"] = "authorized"
    execution_authorized: Literal[True] = True
    requires_merged_commit_binding: Literal[True] = True
    successful_probe_audit_sha256: str
    endpoint: Literal["/v1/chat/completions"] = "/v1/chat/completions"
    response_format_type: Literal["json_schema"] = "json_schema"
    selected_case_ids: tuple[
        Literal[SchemaCanaryCaseId.INCIDENT_SEVERITY],
        Literal[SchemaCanaryCaseId.PAYMENT_RECONCILIATION],
        Literal[SchemaCanaryCaseId.DATA_SHARING_POLICY],
    ]
    case_profiles: tuple[
        SchemaCanaryCaseProfile,
        SchemaCanaryCaseProfile,
        SchemaCanaryCaseProfile,
    ]
    condition_id: Literal[ConditionId.C] = ConditionId.C
    intended_route: tuple[
        Literal[WorkerId.WORKER_1],
        Literal[WorkerId.WORKER_1],
    ] = (WorkerId.WORKER_1, WorkerId.WORKER_1)
    trajectory_count: Literal[3] = 3
    request_count: Literal[6] = 6
    full_worker_restart_before_each_trajectory: Literal[True] = True
    temperature: Decimal = Decimal("0")
    top_p: Decimal = Decimal("1")
    seed: Literal[7] = 7
    max_output_tokens: Literal[128] = 128
    stream: Literal[False] = False
    required_quality_checks: tuple[
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
    ]
    required_quality_pass_rate: Literal["1.0"] = "1.0"
    required_output_shape: Literal[MeasuredOutputShape.JSON_OBJECT] = (
        MeasuredOutputShape.JSON_OBJECT
    )
    require_turn_one_cold: Literal[True] = True
    require_positive_turn_two_cached_tokens: Literal[True] = True
    cache_reuse_evaluation_permitted: Literal[True] = True
    max_trajectory_failures: Literal[0] = 0
    hidden_retries_permitted: Literal[False] = False
    replacement_trajectories_permitted: Literal[False] = False
    schema_canary_execution_authorized: Literal[True] = True
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Decimal = Decimal("0")
    customer_data_used: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False

    @field_validator("canary_id")
    @classmethod
    def validate_canary_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("canary_id must use stable lowercase characters")
        return value

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator("successful_probe_audit_sha256")
    @classmethod
    def validate_audit_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("canary audit binding must be lowercase SHA-256")
        return value

    @field_validator("selected_case_ids")
    @classmethod
    def validate_case_order(
        cls,
        value: tuple[
            Literal[SchemaCanaryCaseId.INCIDENT_SEVERITY],
            Literal[SchemaCanaryCaseId.PAYMENT_RECONCILIATION],
            Literal[SchemaCanaryCaseId.DATA_SHARING_POLICY],
        ],
    ) -> tuple[
        Literal[SchemaCanaryCaseId.INCIDENT_SEVERITY],
        Literal[SchemaCanaryCaseId.PAYMENT_RECONCILIATION],
        Literal[SchemaCanaryCaseId.DATA_SHARING_POLICY],
    ]:
        expected = (
            SchemaCanaryCaseId.INCIDENT_SEVERITY,
            SchemaCanaryCaseId.PAYMENT_RECONCILIATION,
            SchemaCanaryCaseId.DATA_SHARING_POLICY,
        )
        if value != expected:
            raise ValueError("schema canary cases must use frozen order")
        return value

    @field_validator("required_quality_checks")
    @classmethod
    def validate_quality_checks(
        cls,
        value: tuple[
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
            MeasuredQualityCheck,
        ],
    ) -> tuple[
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
        MeasuredQualityCheck,
    ]:
        if value != tuple(MeasuredQualityCheck):
            raise ValueError("schema canary requires every quality check")
        return value

    @field_validator("external_spend")
    @classmethod
    def validate_zero_spend(cls, value: Decimal) -> Decimal:
        if value != Decimal("0"):
            raise ValueError("schema canary external_spend must remain zero")
        return value

    @model_validator(mode="after")
    def validate_profiles(self) -> Self:
        profile_ids = tuple(profile.case_id for profile in self.case_profiles)
        if profile_ids != self.selected_case_ids:
            raise ValueError("case profiles must align with selected case order")
        return self


class SchemaCanaryCheckpoint(LocalABCContract):
    """Terminal-aware checkpoint for three two-turn trajectories."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: SchemaCanaryLifecycleStatus
    retained_trajectory_count: int = Field(ge=0, le=3)
    completed_request_count: int = Field(ge=0, le=6)
    failure_count: int = Field(ge=0, le=1)
    abort_reason: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.status is SchemaCanaryLifecycleStatus.PASSED:
            if (
                self.retained_trajectory_count != 3
                or self.completed_request_count != 6
                or self.failure_count != 0
                or self.abort_reason is not None
            ):
                raise ValueError("passed canary requires three clean trajectories")
        elif self.status is SchemaCanaryLifecycleStatus.FAILED:
            minimum_requests = (self.retained_trajectory_count - 1) * 2 + 1
            maximum_requests = self.retained_trajectory_count * 2
            if (
                self.retained_trajectory_count < 1
                or not minimum_requests <= self.completed_request_count <= maximum_requests
                or self.failure_count != 1
                or self.abort_reason is None
            ):
                raise ValueError("failed canary requires one retained failure")
        elif self.status is SchemaCanaryLifecycleStatus.BLOCKED:
            if (
                self.retained_trajectory_count != 0
                or self.completed_request_count != 0
                or self.failure_count != 0
                or self.abort_reason is None
            ):
                raise ValueError("blocked canary requires a pre-execution reason")
        elif self.status is SchemaCanaryLifecycleStatus.RUNNING and (
            self.retained_trajectory_count >= 3
            or self.completed_request_count != self.retained_trajectory_count * 2
            or self.failure_count != 0
            or self.abort_reason is not None
        ):
            raise ValueError("running canary requires only complete clean trajectories")
        elif self.status is SchemaCanaryLifecycleStatus.NOT_STARTED and (
            self.retained_trajectory_count != 0
            or self.completed_request_count != 0
            or self.failure_count != 0
            or self.abort_reason is not None
        ):
            raise ValueError("not-started canary cannot contain execution data")
        return self


class SchemaCanaryAuthorizationPackage(LocalABCContract):
    """Cross-file binding for probe evidence and canary authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit: SchemaProbeV1EvidenceAudit
    authorization: SchemaConstrainedQualityCanaryAuthorization

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.audit.fingerprint() != self.authorization.successful_probe_audit_sha256:
            raise ValueError("canary audit digest does not match audit bytes")
        if not self.audit.schema_canary_authorization_permitted:
            raise ValueError("probe evidence does not permit canary authorization")
        if self.audit.full_measured_rerun_authorized:
            raise ValueError("probe audit cannot authorize full measured execution")
        if self.authorization.full_measured_rerun_authorized:
            raise ValueError("schema canary cannot authorize full measured execution")
        return self


def build_schema_canary_response_format(
    *,
    profile: SchemaCanaryCaseProfile,
    turn_index: Literal[1, 2],
) -> dict[str, Any]:
    """Build one structural schema without encoding the expected answer."""

    if turn_index not in profile.turn_indexes:
        raise ValueError("turn index is not authorized for this profile")

    if profile.answer_constraint is SchemaCanaryAnswerConstraint.ENUM:
        answer_schema: dict[str, Any] = {
            "type": "string",
            "enum": list(profile.allowed_answers),
        }
    else:
        answer_schema = {
            "type": "string",
            "pattern": profile.answer_pattern,
        }

    schema_name = f"{profile.case_id.value}-turn-{turn_index}-output"
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": answer_schema,
                    "case_id": {
                        "type": "string",
                        "const": profile.case_id.value,
                    },
                    "confidence": {
                        "type": "string",
                        "const": "high",
                    },
                    "turn_index": {
                        "type": "integer",
                        "const": turn_index,
                    },
                },
                "required": list(_REQUIRED_KEYS),
                "additionalProperties": False,
            },
        },
    }


def build_schema_canary_request_body(
    *,
    model: str,
    user_content: str,
    profile: SchemaCanaryCaseProfile,
    turn_index: Literal[1, 2],
    authorization: SchemaConstrainedQualityCanaryAuthorization,
) -> dict[str, Any]:
    """Build one transient structured chat-completion request."""

    if not model.strip():
        raise ValueError("model must not be blank")
    if not user_content.strip():
        raise ValueError("user_content must not be blank")
    if profile.case_id not in authorization.selected_case_ids:
        raise ValueError("case profile is not authorized")

    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": user_content,
            }
        ],
        "response_format": build_schema_canary_response_format(
            profile=profile,
            turn_index=turn_index,
        ),
        "max_tokens": authorization.max_output_tokens,
        "temperature": float(authorization.temperature),
        "top_p": float(authorization.top_p),
        "seed": authorization.seed,
        "stream": authorization.stream,
    }


def build_schema_canary_checkpoint(
    *,
    status: SchemaCanaryLifecycleStatus,
    retained_trajectory_count: int,
    completed_request_count: int,
    failure_count: int,
    abort_reason: str | None = None,
) -> SchemaCanaryCheckpoint:
    """Construct a validated checkpoint before evidence serialization."""

    return SchemaCanaryCheckpoint(
        status=status,
        retained_trajectory_count=retained_trajectory_count,
        completed_request_count=completed_request_count,
        failure_count=failure_count,
        abort_reason=abort_reason,
    )


def load_schema_canary_authorization_package(
    *,
    audit_path: Path,
    authorization_path: Path,
) -> SchemaCanaryAuthorizationPackage:
    """Load and cross-validate successful probe evidence and canary scope."""

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    authorization_payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    return SchemaCanaryAuthorizationPackage(
        audit=SchemaProbeV1EvidenceAudit.model_validate(audit_payload),
        authorization=(
            SchemaConstrainedQualityCanaryAuthorization.model_validate(authorization_payload)
        ),
    )
