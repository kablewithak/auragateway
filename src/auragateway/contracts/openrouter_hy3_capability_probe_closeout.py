"""Typed sanitized closeout contracts for the terminal Hy3 capability probe."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SECRET_PATTERNS = (
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]+"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
)


class OpenRouterProbePosthocAuthDiagnostic(BaseModel):
    """Local-only diagnostic that does not reconstruct provider wire delivery."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    diagnostic_scope: Literal["posthoc_local_only"] = "posthoc_local_only"
    network_request_performed: Literal[False] = False
    authorization_header_present: bool
    authorization_scheme: Literal["Bearer"] | None
    proxy_entry_count: int = Field(ge=0)
    proxy_detected: bool
    credential_value_used: Literal[False] = False
    proves_provider_received_header: Literal[False] = False
    diagnostic_recorded_at: datetime

    @model_validator(mode="after")
    def validate_diagnostic(self) -> OpenRouterProbePosthocAuthDiagnostic:
        if self.authorization_header_present != (self.authorization_scheme == "Bearer"):
            raise ValueError("authorization presence and scheme do not reconcile")
        if self.proxy_detected != (self.proxy_entry_count > 0):
            raise ValueError("proxy count and proxy flag do not reconcile")
        return self


class OpenRouterProbeSanitizedCloseout(BaseModel):
    """Public metadata-only result derived from protected terminal evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["openrouter-hy3-capability-probe-closeout-v1"]
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    source_commit: str
    terminal_outcome: Literal["closed_terminal_provider_failure"]
    failure_stage: Literal["pre_inference_authentication"]
    failure_class: Literal["provider_authentication_failed"]
    attempt_count: Literal[1]
    provider_success_count: Literal[0]
    retained_success_count: Literal[0]
    replacement_count: Literal[0]
    cold_call_attempted: Literal[True] = True
    warm_call_attempted: Literal[False] = False
    generation_metadata_requested: Literal[False] = False
    network_request_count: Literal[1]
    response_kind: Literal["completion"]
    http_status: Literal[401]
    safe_error_code: Literal["PROVIDER_AUTHENTICATION_FAILED"]
    retry_permitted: Literal[False] = False
    provider_error_code: str = Field(min_length=1, max_length=80)
    provider_error_message: str = Field(min_length=1, max_length=240)
    response_body_sha256: str
    response_body_bytes: int = Field(ge=1, le=4096)
    numeric_cache_telemetry_observed: Literal[False] = False
    controlled_cache_use_observed: Literal[False] = False
    route_identity_observed: Literal[False] = False
    comparison_eligible: Literal[False] = False
    pilot_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    authorization_consumed: Literal[True] = True
    resume_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False
    credential_continuity_proven: Literal[False] = False
    authorization_header_delivery_proven: Literal[False] = False
    root_cause_resolved: Literal[False] = False
    terminal_receipt_sha256: str
    journal_sha256: str
    raw_responses_sha256: str
    parsed_responses_sha256: str
    prompt_bundle_sha256: str
    preflight_receipt_sha256: str
    posthoc_auth_diagnostic: OpenRouterProbePosthocAuthDiagnostic
    permitted_claim: Literal[
        "The one-time OpenRouter Hy3 capability probe closed on its first cold-call attempt "
        "after an HTTP 401 authentication failure; no completion, generation metadata, or "
        "cache telemetry was obtained."
    ]
    non_claims: tuple[str, ...]
    residual_harness_gaps: tuple[str, ...]
    public_raw_payload_included: Literal[False] = False
    public_prompt_included: Literal[False] = False
    public_secret_included: Literal[False] = False
    next_gate: Literal["terminal_review_and_continuity_update"]
    closed_at: datetime
    sanitized_at: datetime

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout source commit must be a full lowercase SHA")
        return value

    @field_validator(
        "response_body_sha256",
        "terminal_receipt_sha256",
        "journal_sha256",
        "raw_responses_sha256",
        "parsed_responses_sha256",
        "prompt_bundle_sha256",
        "preflight_receipt_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout hashes must be lowercase SHA-256")
        return value

    @field_validator("provider_error_code", "provider_error_message")
    @classmethod
    def reject_secrets(cls, value: str) -> str:
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            raise ValueError("sanitized closeout cannot contain credentials")
        return value

    @model_validator(mode="after")
    def validate_non_claims(self) -> OpenRouterProbeSanitizedCloseout:
        required = {
            "No Hy3 model inference succeeded.",
            "No cache hit, miss, read, write, discount, saving, or latency result was observed.",
            "The evidence does not establish whether credential validity, credential entry, "
            "header delivery, or another authentication factor caused the 401 response.",
            "No A/B/C pilot or retained benchmark is authorized.",
        }
        if not required.issubset(set(self.non_claims)):
            raise ValueError("sanitized closeout is missing required non-claims")
        if len(self.residual_harness_gaps) < 2:
            raise ValueError("closeout must retain the discovered harness gaps")
        return self


class OpenRouterProbeCloseoutManifest(BaseModel):
    """Integrity manifest for the generated sanitized closeout."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    closeout_id: Literal["openrouter-hy3-capability-probe-closeout-v1"]
    closeout_result_sha256: str
    closeout_policy_sha256: str
    closeout_contract_sha256: str
    closeout_runner_sha256: str
    adr_sha256: str
    benchmark_report_sha256: str
    terminal_receipt_sha256: str
    journal_sha256: str
    raw_responses_sha256: str
    parsed_responses_sha256: str
    generated_at: datetime
    raw_provider_payload_published: Literal[False] = False
    protected_prompt_published: Literal[False] = False
    credential_published: Literal[False] = False

    @field_validator(
        "closeout_result_sha256",
        "closeout_policy_sha256",
        "closeout_contract_sha256",
        "closeout_runner_sha256",
        "adr_sha256",
        "benchmark_report_sha256",
        "terminal_receipt_sha256",
        "journal_sha256",
        "raw_responses_sha256",
        "parsed_responses_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("closeout manifest requires lowercase SHA-256")
        return value


class OpenRouterProbeCloseoutSummary(BaseModel):
    """Metadata-safe CLI result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate-local", "generate", "validate-public"]
    closeout_ready: bool
    closeout_result_present: bool
    closeout_manifest_present: bool
    terminal_outcome: Literal["closed_terminal_provider_failure"]
    failure_class: Literal["provider_authentication_failed"]
    attempt_count: Literal[1]
    provider_success_count: Literal[0]
    authorization_consumed: Literal[True]
    credential_accessed: Literal[False] = False
    network_request_count: Literal[0] = 0
    raw_payload_printed: Literal[False] = False
    next_gate: Literal[
        "generate_sanitized_closeout",
        "validate_and_commit_sanitized_closeout",
        "terminal_review_and_continuity_update",
    ]
