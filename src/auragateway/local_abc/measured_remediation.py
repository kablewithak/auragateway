"""Typed audit and canary authorization for measured-run quality remediation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract
from auragateway.local_abc.measured_quality import MeasuredQualityCheck
from auragateway.local_abc.measured_transport import (
    MeasuredPromptTransportPolicy,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class CorrectedRunClassification(StrEnum):
    """Evidence-bounded correction applied to the v1 measured run."""

    DIAGNOSTIC_ONLY = "diagnostic_only"
    QUALIFIED = "qualified"


class MeasuredRunDefectCode(StrEnum):
    """Root defects identified by the v1 evidence audit."""

    QUALITY_FAILURE_NOT_PROPAGATED_TO_ELIGIBILITY = "QUALITY_FAILURE_NOT_PROPAGATED_TO_ELIGIBILITY"
    RAW_INSTRUCT_TRANSPORT_NOT_QUALIFIED = "RAW_INSTRUCT_TRANSPORT_NOT_QUALIFIED"
    NEGATIVE_CONTROL_TOKEN_LENGTH_CONFOUNDED = "NEGATIVE_CONTROL_TOKEN_LENGTH_CONFOUNDED"


class MeasuredRunQualityAudit(LocalABCContract):
    """Observed deterministic output-quality counts from v1 evidence."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    turn_count: Literal[144] = 144
    reported_valid_turn_count: Literal[144] = 144
    json_parse_pass_count: Literal[0] = 0
    exact_key_set_pass_count: Literal[0] = 0
    exact_answer_pass_count: Literal[0] = 0
    exact_case_id_pass_count: Literal[0] = 0
    exact_turn_index_pass_count: Literal[0] = 0
    exact_confidence_pass_count: Literal[0] = 0
    no_extra_text_pass_count: Literal[0] = 0
    empty_output_count: Literal[126] = 126
    truncated_output_count: Literal[18] = 18
    corrected_quality_eligible_turn_count: Literal[0] = 0


class MeasuredRunTelemetryAudit(LocalABCContract):
    """Telemetry findings retained as valid diagnostic evidence."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    primary_pair_count: Literal[24] = 24
    negative_control_pair_count: Literal[24] = 24
    condition_a_turn2_cached_tokens: Literal[0] = 0
    condition_b_turn2_cached_tokens: Literal[0] = 0
    condition_c_turn2_cached_tokens: Literal[176] = 176
    primary_cached_token_median_delta: Literal[176] = 176
    primary_new_prefill_token_median_delta: Literal[-176] = -176
    primary_prefill_duration_median_delta_ms: float
    primary_ttft_median_delta_ms: float
    primary_end_to_end_median_delta_ms: float
    primary_pairwise_win_rate: Literal["1.0"] = "1.0"
    negative_control_new_prefill_token_median_delta: Literal[-37] = -37

    @model_validator(mode="after")
    def validate_primary_direction(self) -> Self:
        if self.primary_prefill_duration_median_delta_ms >= 0:
            raise ValueError("primary prefill duration delta must favor condition C")
        if self.primary_ttft_median_delta_ms >= 0:
            raise ValueError("primary TTFT delta must favor condition C")
        if self.primary_end_to_end_median_delta_ms >= 0:
            raise ValueError("primary end-to-end delta must favor condition C")
        return self


class MeasuredRunV1EvidenceAudit(LocalABCContract):
    """Immutable correction layer over the completed v1 evidence archive."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit_id: str
    audited_at: datetime
    evidence_archive_sha256: str
    evidence_report_sha256: str
    evidence_analysis_sha256: str
    trajectory_ledger_sha256: str
    reported_status: Literal["MEASURED_LOCAL_ABC_RUN_COMPLETED"]
    corrected_classification: Literal[CorrectedRunClassification.DIAGNOSTIC_ONLY] = (
        CorrectedRunClassification.DIAGNOSTIC_ONLY
    )
    completed_trajectory_count: Literal[72] = 72
    completed_request_count: Literal[144] = 144
    operational_trajectory_failure_count: Literal[0] = 0
    route_realization_mismatch_count: Literal[0] = 0
    invalid_telemetry_record_count: Literal[0] = 0
    reported_eligible_trajectory_count: Literal[72] = 72
    corrected_quality_eligible_trajectory_count: Literal[0] = 0
    quality: MeasuredRunQualityAudit
    telemetry: MeasuredRunTelemetryAudit
    defects: tuple[
        MeasuredRunDefectCode,
        MeasuredRunDefectCode,
        MeasuredRunDefectCode,
    ]
    telemetry_measurement_scope_accepted: Literal[True] = True
    quality_preserving_benchmark_qualified: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["measured_quality_chat_template_canary_v1"] = (
        "measured_quality_chat_template_canary_v1"
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
        "evidence_analysis_sha256",
        "trajectory_ledger_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence audit digests must be lowercase SHA-256")
        return value

    @field_validator("defects")
    @classmethod
    def validate_defects(
        cls,
        value: tuple[
            MeasuredRunDefectCode,
            MeasuredRunDefectCode,
            MeasuredRunDefectCode,
        ],
    ) -> tuple[
        MeasuredRunDefectCode,
        MeasuredRunDefectCode,
        MeasuredRunDefectCode,
    ]:
        expected = tuple(MeasuredRunDefectCode)
        if value != expected:
            raise ValueError("v1 audit must freeze all three observed defects")
        return value


class CanaryAuthorizationDecision(StrEnum):
    """Explicit execution decision for the bounded remediation canary."""

    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"


class MeasuredQualityCanaryAuthorization(LocalABCContract):
    """Authorization for six requests only; never for the full rerun."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    canary_id: str
    issued_at: datetime
    decision: Literal[CanaryAuthorizationDecision.AUTHORIZED] = (
        CanaryAuthorizationDecision.AUTHORIZED
    )
    canary_execution_authorized: Literal[True] = True
    source_parent_commit: Literal["4b1b916259a599d7fada85fe57b7dad8c4c6f5af"] = (
        "4b1b916259a599d7fada85fe57b7dad8c4c6f5af"
    )
    requires_merged_commit_binding: Literal[True] = True
    measured_v1_audit_sha256: str
    selected_case_ids: tuple[
        Literal["incident-severity"],
        Literal["payment-reconciliation"],
        Literal["data-sharing-policy"],
    ]
    condition_id: Literal[ConditionId.C] = ConditionId.C
    trajectory_count: Literal[3] = 3
    request_count: Literal[6] = 6
    full_worker_restart_before_each_trajectory: Literal[True] = True
    transport: MeasuredPromptTransportPolicy
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
    require_positive_turn2_cached_tokens: Literal[True] = True
    max_trajectory_failures: Literal[0] = 0
    hidden_retries_permitted: Literal[False] = False
    replacement_trajectories_permitted: Literal[False] = False
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

    @field_validator("measured_v1_audit_sha256")
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
            Literal["incident-severity"],
            Literal["payment-reconciliation"],
            Literal["data-sharing-policy"],
        ],
    ) -> tuple[
        Literal["incident-severity"],
        Literal["payment-reconciliation"],
        Literal["data-sharing-policy"],
    ]:
        expected = (
            "incident-severity",
            "payment-reconciliation",
            "data-sharing-policy",
        )
        if value != expected:
            raise ValueError("canary cases must use the frozen diagnostic order")
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
            raise ValueError("canary requires every deterministic quality check")
        return value

    @field_validator("external_spend")
    @classmethod
    def validate_zero_spend(cls, value: Decimal) -> Decimal:
        if value != Decimal("0"):
            raise ValueError("canary external_spend must remain zero")
        return value


class MeasuredQualityRemediationPackage(LocalABCContract):
    """Cross-file binding for the v1 audit and bounded canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit: MeasuredRunV1EvidenceAudit
    canary: MeasuredQualityCanaryAuthorization

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.audit.fingerprint() != self.canary.measured_v1_audit_sha256:
            raise ValueError("canary audit digest does not match audit bytes")
        if self.audit.full_measured_rerun_authorized:
            raise ValueError("v1 audit cannot authorize the full measured rerun")
        if self.canary.full_measured_rerun_authorized:
            raise ValueError("canary authorization cannot authorize the full rerun")
        return self


def load_measured_quality_remediation_package(
    *,
    audit_path: Path,
    canary_authorization_path: Path,
) -> MeasuredQualityRemediationPackage:
    """Load and cross-validate the immutable audit and canary authorization."""

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    canary_payload = json.loads(canary_authorization_path.read_text(encoding="utf-8"))
    return MeasuredQualityRemediationPackage(
        audit=MeasuredRunV1EvidenceAudit.model_validate(audit_payload),
        canary=MeasuredQualityCanaryAuthorization.model_validate(canary_payload),
    )
