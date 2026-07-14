"""Typed fixture-only validation for the OpenRouter provider adapter."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auragateway.contracts.openrouter import OpenRouterCacheObservationState
from auragateway.contracts.provider import ProviderErrorCode

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class OpenRouterDryRunCaseStatus(StrEnum):
    """Expected terminal state for one fixture replay."""

    SUCCEEDED = "succeeded"
    REJECTED = "rejected"


class OpenRouterDryRunNextGate(StrEnum):
    """Next review after adapter and fixture validation."""

    CAPABILITY_PROBE_AUTHORIZATION_REVIEW = "openrouter_hy3_capability_probe_authorization_review"


class OpenRouterDryRunFixtureCase(BaseModel):
    """One synthetic completion/generation pair and expected result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    session_id: str = Field(min_length=1, max_length=256)
    completion_payload: dict[str, object]
    generation_payload: dict[str, object]
    expected_status: OpenRouterDryRunCaseStatus
    expected_read_state: OpenRouterCacheObservationState | None = None
    expected_write_state: OpenRouterCacheObservationState | None = None
    expected_error_code: ProviderErrorCode | None = None

    @model_validator(mode="after")
    def validate_expected_state(self) -> OpenRouterDryRunFixtureCase:
        if self.expected_status is OpenRouterDryRunCaseStatus.SUCCEEDED:
            if (
                self.expected_read_state is None
                or self.expected_write_state is None
                or self.expected_error_code is not None
            ):
                raise ValueError("successful cases require both states and no error")
        elif (
            self.expected_error_code is None
            or self.expected_read_state is not None
            or self.expected_write_state is not None
        ):
            raise ValueError("rejected cases require only an expected error code")
        return self


class OpenRouterDryRunFixtureSet(BaseModel):
    """Frozen fixture set covering cache-field and route edge cases."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_set_id: Literal["openrouter-hy3-adapter-dry-run-fixtures-v1"]
    cases: tuple[OpenRouterDryRunFixtureCase, ...] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def validate_cases(self) -> OpenRouterDryRunFixtureSet:
        ids = [item.case_id for item in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("dry-run fixture case IDs must be unique")
        return self


class OpenRouterDryRunCaseResult(BaseModel):
    """Public-safe result for one fixture replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    status: OpenRouterDryRunCaseStatus
    read_state: OpenRouterCacheObservationState | None = None
    write_state: OpenRouterCacheObservationState | None = None
    error_code: ProviderErrorCode | None = None
    requested_model: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    resolved_model_sha256: str | None = None
    upstream_provider_sha256: str | None = None
    session_id_sha256: str
    privacy_controls_enforced: Literal[True] = True
    manual_provider_order_present: Literal[False] = False

    @field_validator(
        "resolved_model_sha256",
        "upstream_provider_sha256",
        "session_id_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run results require lowercase SHA-256")
        return value


class OpenRouterDryRunReport(BaseModel):
    """Terminal fixture-only adapter validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: Literal["openrouter-hy3-adapter-dry-run-v1"]
    status: Literal["passed"] = "passed"
    source_commit: str
    fixture_set_id: Literal["openrouter-hy3-adapter-dry-run-fixtures-v1"]
    results: tuple[OpenRouterDryRunCaseResult, ...] = Field(min_length=7, max_length=7)
    case_count: Literal[7] = 7
    successful_case_count: Literal[5] = 5
    rejected_case_count: Literal[2] = 2
    absent_state_covered: Literal[True] = True
    null_state_covered: Literal[True] = True
    zero_state_covered: Literal[True] = True
    positive_read_state_covered: Literal[True] = True
    positive_write_state_covered: Literal[True] = True
    invalid_numeric_type_rejected: Literal[True] = True
    generation_identity_mismatch_rejected: Literal[True] = True
    privacy_controls_enforced: Literal[True] = True
    manual_provider_order_present: Literal[False] = False
    credential_accessed: Literal[False] = False
    live_provider_call_performed: Literal[False] = False
    hy3_free_numeric_telemetry_observed_live: Literal[False] = False
    live_provider_call_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    adapter_ready_for_authorization_review: Literal[True] = True
    tla_plus_reassessment_required: Literal[True] = True
    next_gate: Literal[OpenRouterDryRunNextGate.CAPABILITY_PROBE_AUTHORIZATION_REVIEW] = (
        OpenRouterDryRunNextGate.CAPABILITY_PROBE_AUTHORIZATION_REVIEW
    )

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run report requires a full lowercase source commit")
        return value

    @model_validator(mode="after")
    def validate_results(self) -> OpenRouterDryRunReport:
        succeeded = sum(
            item.status is OpenRouterDryRunCaseStatus.SUCCEEDED for item in self.results
        )
        if succeeded != self.successful_case_count:
            raise ValueError("successful case count does not reconcile")
        if len(self.results) - succeeded != self.rejected_case_count:
            raise ValueError("rejected case count does not reconcile")
        return self


class OpenRouterDryRunManifest(BaseModel):
    """Integrity manifest for fixture, report, code, and human-readable evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: Literal["openrouter-hy3-adapter-dry-run-v1"]
    source_commit: str
    bindings: tuple[dict[str, str], ...] = Field(min_length=7, max_length=7)
    source_evidence_locked: Literal[True] = True
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    next_gate: Literal[OpenRouterDryRunNextGate.CAPABILITY_PROBE_AUTHORIZATION_REVIEW] = (
        OpenRouterDryRunNextGate.CAPABILITY_PROBE_AUTHORIZATION_REVIEW
    )

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("dry-run manifest requires a full lowercase source commit")
        return value

    @model_validator(mode="after")
    def validate_bindings(self) -> OpenRouterDryRunManifest:
        expected = {
            "data/provider_fixtures/openrouter-hy3-adapter-v1/fixtures.json",
            "data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/report.json",
            "src/auragateway/contracts/openrouter.py",
            "src/auragateway/providers/openrouter.py",
            "src/auragateway/providers/base.py",
            "docs/adr/openrouter-hy3-adapter-dry-run.md",
            "docs/benchmark/AuraGateway_OpenRouter_Hy3_Adapter_Dry_Run.md",
        }
        paths = [item.get("path") for item in self.bindings]
        if set(paths) != expected or len(paths) != len(set(paths)):
            raise ValueError("manifest requires the seven exact dry-run bindings")
        for item in self.bindings:
            path = item.get("path")
            digest = item.get("sha256")
            if path is None or digest is None:
                raise ValueError("manifest bindings require path and sha256")
            parsed = PurePosixPath(path)
            if parsed.is_absolute() or ".." in parsed.parts:
                raise ValueError("manifest paths must be repository-relative")
            if _SHA256_PATTERN.fullmatch(digest) is None:
                raise ValueError("manifest bindings require lowercase SHA-256")
        return self


class OpenRouterDryRunSummary(BaseModel):
    """Metadata-safe CLI validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate"] = "validate"
    report_id: Literal["openrouter-hy3-adapter-dry-run-v1"]
    case_count: Literal[7] = 7
    successful_case_count: Literal[5] = 5
    rejected_case_count: Literal[2] = 2
    privacy_controls_enforced: Literal[True] = True
    credential_accessed: Literal[False] = False
    live_provider_call_performed: Literal[False] = False
    live_provider_call_authorized: Literal[False] = False
    adapter_ready_for_authorization_review: Literal[True] = True
    tla_plus_reassessment_required: Literal[True] = True
    next_gate: Literal[OpenRouterDryRunNextGate.CAPABILITY_PROBE_AUTHORIZATION_REVIEW]
