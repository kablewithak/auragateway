"""Typed deterministic arithmetic action realization for Local A/B/C."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, Self, cast

from pydantic import Field, StrictInt, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_MAX_OPERAND: Final = 1_000_000_000_000
_MAX_RESULT: Final = 2_000_000_000_000
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_OPERAND_FIELDS: Final = frozenset({"opening_balance", "credits", "debits"})
_IDENTITY_FIELDS: Final = frozenset({"case_id", "turn_index"})
_BOUND_ERROR_TYPES: Final = frozenset(
    {"greater_than", "greater_than_equal", "less_than", "less_than_equal"}
)


class DeterministicCapabilityId(StrEnum):
    """Stable identifiers for deterministic capability adapters."""

    RECONCILE_BALANCE = "arithmetic.reconcile_balance.v1"


class ActionRealizationStage(StrEnum):
    """Boundary at which deterministic action realization failed."""

    PARSE = "parse"
    VALIDATE = "validate"
    EXECUTE = "execute"
    RENDER = "render"


class ActionRealizationFailureCode(StrEnum):
    """Machine-readable deterministic action failure taxonomy."""

    ACTION_OUTPUT_MISSING = "ACTION_OUTPUT_MISSING"
    ACTION_JSON_INVALID = "ACTION_JSON_INVALID"
    ACTION_SCHEMA_INVALID = "ACTION_SCHEMA_INVALID"
    ACTION_IDENTITY_MISMATCH = "ACTION_IDENTITY_MISMATCH"
    ACTION_CAPABILITY_UNSUPPORTED = "ACTION_CAPABILITY_UNSUPPORTED"
    ACTION_OPERAND_INVALID = "ACTION_OPERAND_INVALID"
    ACTION_OPERAND_OUT_OF_RANGE = "ACTION_OPERAND_OUT_OF_RANGE"
    ACTION_RESULT_OUT_OF_RANGE = "ACTION_RESULT_OUT_OF_RANGE"
    ACTION_EXECUTION_FAILED = "ACTION_EXECUTION_FAILED"
    RESULT_SCHEMA_INVALID = "RESULT_SCHEMA_INVALID"
    RESULT_RENDER_FAILED = "RESULT_RENDER_FAILED"
    QUALITY_ANSWER_MISMATCH = "QUALITY_ANSWER_MISMATCH"


class ActionRealizationError(ValueError):
    """Typed fail-closed error that never stores raw model output."""

    def __init__(
        self,
        *,
        code: ActionRealizationFailureCode,
        stage: ActionRealizationStage,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage


class ReconcileBalanceAction(LocalABCContract):
    """Strict model-emitted operands for one synthetic reconciliation turn."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    case_id: Literal["payment-reconciliation"]
    turn_index: Literal[1, 2]
    opening_balance: StrictInt = Field(ge=0, le=_MAX_OPERAND)
    credits: StrictInt = Field(ge=0, le=_MAX_OPERAND)
    debits: StrictInt = Field(ge=0, le=_MAX_OPERAND)


class ReconcileBalanceResult(LocalABCContract):
    """Typed result produced only by the deterministic executor."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    case_id: Literal["payment-reconciliation"]
    turn_index: Literal[1, 2]
    answer: StrictInt = Field(ge=0, le=_MAX_RESULT)
    realization_source: Literal["deterministic_executor"] = "deterministic_executor"
    action_sha256: str

    @field_validator("action_sha256")
    @classmethod
    def validate_action_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("action_sha256 must be lowercase SHA-256")
        return value


class ReconcileBalanceRenderedOutput(LocalABCContract):
    """Canonical output compatible with the existing payment quality rubric."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    answer: str = Field(pattern=r"^[0-9]+$")
    case_id: Literal["payment-reconciliation"]
    confidence: Literal["high"] = "high"
    turn_index: Literal[1, 2]


class ActionRealizationEvidence(LocalABCContract):
    """Evidence-safe metadata without raw model output or action operands."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    case_id: Literal["payment-reconciliation"]
    turn_index: Literal[1, 2]
    action_sha256: str
    result_sha256: str
    operand_count: Literal[3] = 3
    synthetic_data: Literal[True] = True
    raw_model_output_retained: Literal[False] = False
    raw_action_retained: Literal[False] = False
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_action_count: Literal[0] = 0
    direct_model_arithmetic_fallback_used: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False

    @field_validator("action_sha256", "result_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence digests must be lowercase SHA-256")
        return value


class ReconcileBalanceRealizationOutcome(LocalABCContract):
    """Safe successful outcome from the deterministic action boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    result: ReconcileBalanceResult
    rendered_output: ReconcileBalanceRenderedOutput
    evidence: ActionRealizationEvidence

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        if self.result.fingerprint() != self.evidence.result_sha256:
            raise ValueError("result fingerprint must match evidence")
        if self.result.action_sha256 != self.evidence.action_sha256:
            raise ValueError("action fingerprint must match result and evidence")
        if self.rendered_output.answer != str(self.result.answer):
            raise ValueError("rendered answer must match deterministic result")
        if self.rendered_output.case_id != self.result.case_id:
            raise ValueError("rendered case ID must match deterministic result")
        if self.rendered_output.turn_index != self.result.turn_index:
            raise ValueError("rendered turn index must match deterministic result")
        return self


class DiagnosticExpectedStatus(StrEnum):
    """Expected terminal state for one diagnostic case."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReconcileBalanceDiagnosticCase(LocalABCContract):
    """One accepted or rejected synthetic diagnostic case."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    diagnostic_id: str
    input_text: str
    expected_status: DiagnosticExpectedStatus
    expected_answer: StrictInt | None = None
    expected_failure_code: ActionRealizationFailureCode | None = None
    diagnostic_reason: str = Field(min_length=12, max_length=240)

    @field_validator("diagnostic_id")
    @classmethod
    def validate_diagnostic_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("diagnostic_id must use stable lowercase characters")
        return value

    @model_validator(mode="after")
    def validate_expected_outcome(self) -> Self:
        if self.expected_status is DiagnosticExpectedStatus.ACCEPTED:
            if self.expected_answer is None or self.expected_failure_code is not None:
                raise ValueError("accepted case requires only an expected answer")
        elif self.expected_answer is not None or self.expected_failure_code is None:
            raise ValueError("rejected case requires only a failure code")
        return self


class ReconcileBalanceDiagnosticManifest(LocalABCContract):
    """Frozen hard cases for the first deterministic arithmetic boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["reconcile-balance-action-diagnostics-v1"] = (
        "reconcile-balance-action-diagnostics-v1"
    )
    adr_id: Literal["ADR-2026-07-16-LOCAL-ABC-ARITHMETIC-ACTION-REALIZATION"]
    failed_canary_audit_sha256: Literal[
        "772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62"
    ]
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    action_schema_sha256: str
    result_schema_sha256: str
    output_schema_sha256: str
    synthetic_data_only: Literal[True] = True
    hidden_retries_permitted: Literal[False] = False
    direct_model_arithmetic_fallback_permitted: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    cases: tuple[ReconcileBalanceDiagnosticCase, ...] = Field(min_length=10)

    @field_validator(
        "action_schema_sha256",
        "result_schema_sha256",
        "output_schema_sha256",
    )
    @classmethod
    def validate_schema_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("schema digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        diagnostic_ids = tuple(case.diagnostic_id for case in self.cases)
        if len(diagnostic_ids) != len(set(diagnostic_ids)):
            raise ValueError("diagnostic IDs must be unique")
        statuses = {case.expected_status for case in self.cases}
        if statuses != {
            DiagnosticExpectedStatus.ACCEPTED,
            DiagnosticExpectedStatus.REJECTED,
        }:
            raise ValueError("manifest requires accepted and rejected cases")
        if self.action_schema_sha256 != reconcile_balance_action_schema_sha256():
            raise ValueError("manifest action schema binding drifted")
        if self.result_schema_sha256 != reconcile_balance_result_schema_sha256():
            raise ValueError("manifest result schema binding drifted")
        if self.output_schema_sha256 != reconcile_balance_output_schema_sha256():
            raise ValueError("manifest output schema binding drifted")
        return self


def _canonical_schema_sha256(model: type[LocalABCContract]) -> str:
    payload = json.dumps(
        model.model_json_schema(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reconcile_balance_action_schema_sha256() -> str:
    """Hash the strict model-emitted action schema."""

    return _canonical_schema_sha256(ReconcileBalanceAction)


def reconcile_balance_result_schema_sha256() -> str:
    """Hash the deterministic internal result schema."""

    return _canonical_schema_sha256(ReconcileBalanceResult)


def reconcile_balance_output_schema_sha256() -> str:
    """Hash the canonical final response schema."""

    return _canonical_schema_sha256(ReconcileBalanceRenderedOutput)


def _validation_failure_code(error: ValidationError) -> ActionRealizationFailureCode:
    for detail in error.errors(include_url=False):
        location = detail.get("loc", ())
        field = str(location[0]) if location else ""
        error_type = str(detail.get("type", ""))
        if field == "capability" and error_type == "literal_error":
            return ActionRealizationFailureCode.ACTION_CAPABILITY_UNSUPPORTED
        if field in _IDENTITY_FIELDS and error_type == "literal_error":
            return ActionRealizationFailureCode.ACTION_IDENTITY_MISMATCH
        if field in _OPERAND_FIELDS and error_type in _BOUND_ERROR_TYPES:
            return ActionRealizationFailureCode.ACTION_OPERAND_OUT_OF_RANGE
        if field in _OPERAND_FIELDS and error_type != "missing":
            return ActionRealizationFailureCode.ACTION_OPERAND_INVALID
    return ActionRealizationFailureCode.ACTION_SCHEMA_INVALID


def validate_reconcile_balance_payload(
    payload: Mapping[str, object],
) -> ReconcileBalanceAction:
    """Validate parsed action data and translate failures to stable codes."""

    try:
        return ReconcileBalanceAction.model_validate(dict(payload))
    except ValidationError as error:
        raise ActionRealizationError(
            code=_validation_failure_code(error),
            stage=ActionRealizationStage.VALIDATE,
            message="reconcile-balance action failed strict validation",
        ) from error


def parse_reconcile_balance_action(output_text: str) -> ReconcileBalanceAction:
    """Parse transient model text without retaining it in returned contracts."""

    if not output_text.strip():
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.ACTION_OUTPUT_MISSING,
            stage=ActionRealizationStage.PARSE,
            message="model action output is empty",
        )
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.ACTION_JSON_INVALID,
            stage=ActionRealizationStage.PARSE,
            message="model action output is not one valid JSON value",
        ) from error
    if not isinstance(parsed, dict):
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.ACTION_SCHEMA_INVALID,
            stage=ActionRealizationStage.VALIDATE,
            message="model action output must be one JSON object",
        )
    return validate_reconcile_balance_payload(cast(dict[str, object], parsed))


def execute_reconcile_balance(
    action: ReconcileBalanceAction,
) -> ReconcileBalanceResult:
    """Pure deterministic calculation with explicit numeric bounds."""

    available_balance = action.opening_balance + action.credits
    if action.debits > available_balance:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.ACTION_RESULT_OUT_OF_RANGE,
            stage=ActionRealizationStage.EXECUTE,
            message="reconciliation result would leave the unsigned domain",
        )
    answer = available_balance - action.debits
    if answer > _MAX_RESULT:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.ACTION_EXECUTION_FAILED,
            stage=ActionRealizationStage.EXECUTE,
            message="reconciliation result exceeded the deterministic bound",
        )
    try:
        return ReconcileBalanceResult(
            case_id=action.case_id,
            turn_index=action.turn_index,
            answer=answer,
            action_sha256=action.fingerprint(),
        )
    except ValidationError as error:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.RESULT_SCHEMA_INVALID,
            stage=ActionRealizationStage.EXECUTE,
            message="deterministic result failed its internal schema",
        ) from error


ReconcileBalanceExecutor = Callable[[ReconcileBalanceAction], ReconcileBalanceResult]
_EXECUTOR_REGISTRY: Final[Mapping[DeterministicCapabilityId, ReconcileBalanceExecutor]] = (
    MappingProxyType({DeterministicCapabilityId.RECONCILE_BALANCE: execute_reconcile_balance})
)


def realize_deterministic_action(
    action: ReconcileBalanceAction,
) -> ReconcileBalanceResult:
    """Dispatch by capability identity, never by benchmark case conditionals."""

    executor = _EXECUTOR_REGISTRY.get(action.capability)
    if executor is None:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.ACTION_CAPABILITY_UNSUPPORTED,
            stage=ActionRealizationStage.EXECUTE,
            message="no deterministic adapter is registered for the capability",
        )
    return executor(action)


def build_reconcile_balance_rendered_output(
    result: ReconcileBalanceResult,
) -> ReconcileBalanceRenderedOutput:
    """Build the existing quality-rubric shape from a deterministic result."""

    try:
        return ReconcileBalanceRenderedOutput(
            answer=str(result.answer),
            case_id=result.case_id,
            turn_index=result.turn_index,
        )
    except ValidationError as error:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.RESULT_SCHEMA_INVALID,
            stage=ActionRealizationStage.RENDER,
            message="deterministic result could not satisfy the response schema",
        ) from error


def render_reconcile_balance_output(result: ReconcileBalanceResult) -> str:
    """Return canonical compact JSON for the existing deterministic scorer."""

    output = build_reconcile_balance_rendered_output(result)
    try:
        return output.canonical_json()
    except (TypeError, ValueError) as error:
        raise ActionRealizationError(
            code=ActionRealizationFailureCode.RESULT_RENDER_FAILED,
            stage=ActionRealizationStage.RENDER,
            message="deterministic output could not be serialized canonically",
        ) from error


def realize_reconcile_balance_output(
    output_text: str,
) -> ReconcileBalanceRealizationOutcome:
    """Parse, validate, execute, and render once without retries or fallback."""

    action = parse_reconcile_balance_action(output_text)
    result = realize_deterministic_action(action)
    rendered_output = build_reconcile_balance_rendered_output(result)
    evidence = ActionRealizationEvidence(
        case_id=action.case_id,
        turn_index=action.turn_index,
        action_sha256=action.fingerprint(),
        result_sha256=result.fingerprint(),
    )
    return ReconcileBalanceRealizationOutcome(
        result=result,
        rendered_output=rendered_output,
        evidence=evidence,
    )


def load_reconcile_balance_diagnostic_manifest(
    path: Path,
) -> ReconcileBalanceDiagnosticManifest:
    """Load the frozen accepted and rejected synthetic diagnostic cases."""

    return ReconcileBalanceDiagnosticManifest.model_validate_json(path.read_text(encoding="utf-8"))
