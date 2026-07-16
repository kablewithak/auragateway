"""Authorization and request contracts for one schema-constrained probe."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from auragateway.local_abc.contracts import (
    LocalABCContract,
    WorkerId,
)
from auragateway.local_abc.errors import LocalABCFailureCode
from auragateway.local_abc.measured_quality import (
    MeasuredOutputShape,
    MeasuredQualityCheck,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class CanaryV1CorrectedClassification(StrEnum):
    """Evidence-bounded lifecycle state for the failed canary."""

    FAILED_DIAGNOSTIC = "failed_diagnostic"


class CanaryV1DefectCode(StrEnum):
    """Secondary harness defects exposed by failed canary evidence."""

    PARSE_FAILURE_OVERREPORTED_SEMANTIC_MISMATCHES = (
        "PARSE_FAILURE_OVERREPORTED_SEMANTIC_MISMATCHES"
    )
    TURN_FAILURE_NOT_PROPAGATED_TO_TRAJECTORY = "TURN_FAILURE_NOT_PROPAGATED_TO_TRAJECTORY"
    CHECKPOINT_RETAINED_RUNNING_STATUS = "CHECKPOINT_RETAINED_RUNNING_STATUS"


class MeasuredQualityCanaryV1EvidenceAudit(LocalABCContract):
    """Immutable audit over the first failed quality canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit_id: str
    audited_at: datetime
    evidence_archive_sha256: str
    evidence_report_sha256: str
    evidence_ledger_sha256: str
    evidence_evaluation_sha256: str
    evidence_summary_sha256: str
    reported_status: Literal["MEASURED_QUALITY_CANARY_FAILED"] = "MEASURED_QUALITY_CANARY_FAILED"
    corrected_classification: Literal[CanaryV1CorrectedClassification.FAILED_DIAGNOSTIC] = (
        CanaryV1CorrectedClassification.FAILED_DIAGNOSTIC
    )
    execution_status: Literal["CANARY_EXECUTION_ABORTED"] = "CANARY_EXECUTION_ABORTED"
    checkpoint_status: Literal["RUNNING"] = "RUNNING"
    cleanup_status: Literal["CLEAN"] = "CLEAN"
    completed_trajectory_count: Literal[1] = 1
    completed_request_count: Literal[1] = 1
    trajectory_failure_count: Literal[1] = 1
    route_realization_mismatch_count: Literal[0] = 0
    telemetry_failure_turn_count: Literal[0] = 0
    quality_failure_turn_count: Literal[1] = 1
    request_status_code: Literal[200] = 200
    prompt_token_count: Literal[282] = 282
    completion_token_count: Literal[110] = 110
    output_character_count: Literal[551] = 551
    finish_reason: Literal["stop"] = "stop"
    output_text_sha256: str
    observed_output_shape: Literal["unclassified_nonempty_non_json"] = (
        "unclassified_nonempty_non_json"
    )
    primary_failure_code: Literal[LocalABCFailureCode.OUTPUT_JSON_INVALID] = (
        LocalABCFailureCode.OUTPUT_JSON_INVALID
    )
    overreported_semantic_failure_codes: tuple[
        LocalABCFailureCode,
        ...,
    ]
    trajectory_failure_codes_propagated: Literal[False] = False
    checkpoint_terminal_status_correct: Literal[False] = False
    schema_constrained_probe_authorized: Literal[True] = True
    six_request_canary_rerun_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    defects: tuple[
        CanaryV1DefectCode,
        CanaryV1DefectCode,
        CanaryV1DefectCode,
    ]
    next_gate: Literal["schema_constrained_output_capability_probe_v1"] = (
        "schema_constrained_output_capability_probe_v1"
    )

    @field_validator("audit_id")
    @classmethod
    def validate_audit_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("audit_id must use stable lowercase characters")
        return value

    @field_validator("audited_at")
    @classmethod
    def validate_audited_at(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("audited_at must be timezone-aware")
        return value

    @field_validator(
        "evidence_archive_sha256",
        "evidence_report_sha256",
        "evidence_ledger_sha256",
        "evidence_evaluation_sha256",
        "evidence_summary_sha256",
        "output_text_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("audit digests must be lowercase SHA-256")
        return value

    @field_validator("overreported_semantic_failure_codes")
    @classmethod
    def validate_overreported_codes(
        cls,
        value: tuple[LocalABCFailureCode, ...],
    ) -> tuple[LocalABCFailureCode, ...]:
        expected = tuple(
            sorted(
                {
                    LocalABCFailureCode.OUTPUT_ANSWER_MISMATCH,
                    LocalABCFailureCode.OUTPUT_CASE_ID_MISMATCH,
                    LocalABCFailureCode.OUTPUT_CONFIDENCE_MISMATCH,
                    LocalABCFailureCode.OUTPUT_EXTRA_TEXT,
                    LocalABCFailureCode.OUTPUT_KEY_SET_MISMATCH,
                    LocalABCFailureCode.OUTPUT_TURN_INDEX_MISMATCH,
                },
                key=lambda code: code.value,
            )
        )
        if value != expected:
            raise ValueError("audit must freeze the exact overreported codes")
        return value

    @field_validator("defects")
    @classmethod
    def validate_defects(
        cls,
        value: tuple[
            CanaryV1DefectCode,
            CanaryV1DefectCode,
            CanaryV1DefectCode,
        ],
    ) -> tuple[
        CanaryV1DefectCode,
        CanaryV1DefectCode,
        CanaryV1DefectCode,
    ]:
        if value != tuple(CanaryV1DefectCode):
            raise ValueError("audit must freeze all observed canary defects")
        return value


class SchemaProbeLifecycleStatus(StrEnum):
    """Terminal-aware lifecycle for the one-request probe."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class SchemaProbeCheckpoint(LocalABCContract):
    """Checkpoint envelope that cannot retain stale running status."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: SchemaProbeLifecycleStatus
    completed_request_count: int = Field(ge=0, le=1)
    failure_count: int = Field(ge=0, le=1)
    abort_reason: str | None = Field(
        default=None,
        max_length=120,
    )

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.status is SchemaProbeLifecycleStatus.PASSED:
            if (
                self.completed_request_count != 1
                or self.failure_count != 0
                or self.abort_reason is not None
            ):
                raise ValueError("passed checkpoint requires one clean request")
        elif self.status is SchemaProbeLifecycleStatus.FAILED:
            if (
                self.completed_request_count != 1
                or self.failure_count != 1
                or self.abort_reason is None
            ):
                raise ValueError("failed checkpoint requires one retained failure")
        elif self.status is SchemaProbeLifecycleStatus.BLOCKED:
            if (
                self.completed_request_count != 0
                or self.failure_count != 0
                or self.abort_reason is None
            ):
                raise ValueError("blocked checkpoint requires pre-execution reason")
        elif self.status is SchemaProbeLifecycleStatus.RUNNING and (
            self.completed_request_count != 0
            or self.failure_count != 0
            or self.abort_reason is not None
        ):
            raise ValueError("running checkpoint cannot contain terminal data")
        return self


class IncidentSeverityProbeOutput(BaseModel):
    """Schema-constrained output with semantic answer still model-selected."""

    model_config = ConfigDict(extra="forbid")

    answer: Literal["sev1", "sev2", "sev3", "sev4"]
    case_id: Literal["incident-severity"]
    confidence: Literal["high"]
    turn_index: Literal[1]


class SchemaConstrainedOutputProbeAuthorization(LocalABCContract):
    """Authorization for one structured-output capability request."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    probe_id: str
    issued_at: datetime
    decision: Literal["authorized"] = "authorized"
    execution_authorized: Literal[True] = True
    requires_merged_commit_binding: Literal[True] = True
    failed_canary_audit_sha256: str
    endpoint: Literal["/v1/chat/completions"] = "/v1/chat/completions"
    response_format_type: Literal["json_schema"] = "json_schema"
    response_schema_name: Literal["incident-severity-probe-output"] = (
        "incident-severity-probe-output"
    )
    selected_case_id: Literal["incident-severity"] = "incident-severity"
    selected_turn_index: Literal[1] = 1
    worker_id: Literal[WorkerId.WORKER_1] = WorkerId.WORKER_1
    request_count: Literal[1] = 1
    full_worker_restart_before_request: Literal[True] = True
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
    expected_output_shape: Literal[MeasuredOutputShape.JSON_OBJECT] = (
        MeasuredOutputShape.JSON_OBJECT
    )
    expected_answer: Literal["sev3"] = "sev3"
    required_quality_pass_rate: Literal["1.0"] = "1.0"
    max_request_failures: Literal[0] = 0
    cache_reuse_evaluation_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[False] = False
    replacement_requests_permitted: Literal[False] = False
    six_request_canary_rerun_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Decimal = Decimal("0")
    customer_data_used: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False

    @field_validator("probe_id")
    @classmethod
    def validate_probe_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("probe_id must use stable lowercase characters")
        return value

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator("failed_canary_audit_sha256")
    @classmethod
    def validate_audit_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("probe audit binding must be lowercase SHA-256")
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
            raise ValueError("probe requires every deterministic quality check")
        return value

    @field_validator("external_spend")
    @classmethod
    def validate_zero_spend(
        cls,
        value: Decimal,
    ) -> Decimal:
        if value != Decimal("0"):
            raise ValueError("probe external_spend must remain zero")
        return value


class SchemaProbeAuthorizationPackage(LocalABCContract):
    """Cross-file binding for failed-canary audit and probe."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit: MeasuredQualityCanaryV1EvidenceAudit
    authorization: SchemaConstrainedOutputProbeAuthorization

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.audit.fingerprint() != self.authorization.failed_canary_audit_sha256:
            raise ValueError("probe audit digest does not match audit bytes")
        if self.audit.six_request_canary_rerun_authorized:
            raise ValueError("failed canary audit cannot authorize rerun")
        if self.authorization.six_request_canary_rerun_authorized:
            raise ValueError("schema probe cannot authorize six-request rerun")
        if self.authorization.full_measured_rerun_authorized:
            raise ValueError("schema probe cannot authorize full measured rerun")
        return self


def build_schema_probe_response_format() -> dict[str, Any]:
    """Return the exact vLLM/OpenAI JSON Schema constraint."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "incident-severity-probe-output",
            "schema": IncidentSeverityProbeOutput.model_json_schema(),
        },
    }


def build_schema_probe_request_body(
    *,
    model: str,
    user_content: str,
    authorization: SchemaConstrainedOutputProbeAuthorization,
) -> dict[str, Any]:
    """Build one transient chat-completion request body."""

    if not model.strip():
        raise ValueError("model must not be blank")
    if not user_content.strip():
        raise ValueError("user_content must not be blank")
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": user_content,
            }
        ],
        "response_format": build_schema_probe_response_format(),
        "max_tokens": authorization.max_output_tokens,
        "temperature": float(authorization.temperature),
        "top_p": float(authorization.top_p),
        "seed": authorization.seed,
        "stream": authorization.stream,
    }


def build_terminal_schema_probe_checkpoint(
    *,
    passed: bool,
    abort_reason: str | None = None,
) -> SchemaProbeCheckpoint:
    """Build terminal state before checkpoint serialization."""

    if passed:
        if abort_reason is not None:
            raise ValueError("passed probe cannot contain an abort reason")
        return SchemaProbeCheckpoint(
            status=SchemaProbeLifecycleStatus.PASSED,
            completed_request_count=1,
            failure_count=0,
        )
    if abort_reason is None:
        raise ValueError("failed probe requires an abort reason")
    return SchemaProbeCheckpoint(
        status=SchemaProbeLifecycleStatus.FAILED,
        completed_request_count=1,
        failure_count=1,
        abort_reason=abort_reason,
    )


def load_schema_probe_authorization_package(
    *,
    audit_path: Path,
    authorization_path: Path,
) -> SchemaProbeAuthorizationPackage:
    """Load and validate the failed-canary audit and probe."""

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    authorization_payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    return SchemaProbeAuthorizationPackage(
        audit=MeasuredQualityCanaryV1EvidenceAudit.model_validate(audit_payload),
        authorization=(
            SchemaConstrainedOutputProbeAuthorization.model_validate(authorization_payload)
        ),
    )
