"""Typed active authorization and local-preflight contracts for the Hy3 probe."""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class OpenRouterProbeActivationStatus(StrEnum):
    """Lifecycle status of the one-time capability-probe authorization."""

    ACTIVE = "active"


class OpenRouterProbeLocalStatus(StrEnum):
    """Local protected-artifact lifecycle state."""

    PREPARED = "prepared"
    PREFLIGHT_PASSED = "preflight_passed"


class OpenRouterProbeActivationBinding(BaseModel):
    """One immutable public dependency of the active authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=3, max_length=260)
    sha256: str
    purpose: str = Field(min_length=10, max_length=240)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value.startswith(".local/"):
            raise ValueError("activation bindings must be public repository-relative paths")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation bindings require lowercase SHA-256")
        return value


class OpenRouterProbeActivationPaths(BaseModel):
    """Public and protected paths for activation and later execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-v1/authorization.json"
    ]
    runtime_policy_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-v1/runtime_policy.json"
    ]
    activation_report_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-v1/activation_report.json"
    ]
    activation_manifest_path: Literal[
        "data/evals/benchmark/openrouter-hy3-capability-probe-v1/activation_manifest.json"
    ]
    protected_prompt_bundle_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/prompt_bundle.json"
    ]
    protected_preparation_receipt_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/preparation_receipt.json"
    ]
    protected_preflight_receipt_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/preflight_receipt.json"
    ]
    protected_journal_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/journal.jsonl"
    ]
    protected_raw_responses_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/raw_responses.jsonl"
    ]
    protected_parsed_responses_path: Literal[
        ".local/benchmark/openrouter-hy3-capability-probe-v1/parsed_responses.jsonl"
    ]


class OpenRouterProbeActivationAuthorization(BaseModel):
    """Active authorization for one bounded two-call Hy3 capability probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    review_id: Literal["openrouter-hy3-capability-probe-authorization-review-v1"]
    status: Literal[OpenRouterProbeActivationStatus.ACTIVE] = OpenRouterProbeActivationStatus.ACTIVE
    source_commit: str
    bindings: tuple[OpenRouterProbeActivationBinding, ...] = Field(min_length=8, max_length=8)
    provider: Literal["openrouter"] = "openrouter"
    model_alias: Literal["openrouter-hy3-free"] = "openrouter-hy3-free"
    exact_model_identifier: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    adapter_version: Literal["openrouter-chat-completions-v1"] = "openrouter-chat-completions-v1"
    transport_version: Literal["openrouter-http-explicit-key-v1"] = (
        "openrouter-http-explicit-key-v1"
    )
    telemetry_authority: Literal["openrouter_normalized_usage"] = "openrouter_normalized_usage"
    api_key_environment_name: Literal["OPENROUTER_API_KEY"] = "OPENROUTER_API_KEY"
    prompt_recipe_id: Literal["openrouter-hy3-capability-probe-prompt-v1"]
    protected_prompt_bundle_sha256: str
    protected_prompt_bundle_bytes: int = Field(gt=0)
    confirmation_phrase: Literal["EXECUTE_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE"] = (
        "EXECUTE_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE"
    )
    preflight_confirmation_phrase: Literal["PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE"] = (
        "PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE"
    )
    maximum_logical_calls: Literal[2] = 2
    maximum_provider_successes: Literal[2] = 2
    maximum_retained_successes: Literal[2] = 2
    maximum_total_inference_attempts: Literal[4] = 4
    timeout_seconds: Literal[60] = 60
    maximum_completion_tokens: Literal[32] = 32
    evidence_paths: OpenRouterProbeActivationPaths
    one_time_execution: Literal[True] = True
    credential_required: Literal[True] = True
    key_status_preflight_required: Literal[True] = True
    model_catalog_preflight_required: Literal[True] = True
    provider_calls_permitted: Literal[True] = True
    capability_probe_execution_authorized: Literal[True] = True
    authorization_consumed: Literal[False] = False
    resume_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["protected_local_preparation_and_live_preflight"] = (
        "protected_local_preparation_and_live_preflight"
    )

    @field_validator("source_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if _COMMIT_PATTERN.fullmatch(value) is None:
            raise ValueError("activation source commit must be a full lowercase commit SHA")
        return value

    @field_validator("protected_prompt_bundle_sha256")
    @classmethod
    def validate_bundle_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("protected prompt bundle requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_authorization(self) -> OpenRouterProbeActivationAuthorization:
        paths = [item.path for item in self.bindings]
        if len(paths) != len(set(paths)):
            raise ValueError("activation bindings must be unique")
        required_paths = {
            "data/evals/benchmark/"
            "openrouter-hy3-capability-probe-authorization-review-v1/review.json",
            "data/evals/benchmark/"
            "openrouter-hy3-capability-probe-authorization-review-v1/manifest.json",
            "data/evals/benchmark/"
            "openrouter-hy3-capability-probe-authorization-review-v1/prompt_recipe.json",
            "data/evals/benchmark/"
            "openrouter-hy3-capability-probe-authorization-review-v1/"
            "state_model_report.json",
            "data/evals/benchmark/"
            "openrouter-hy3-capability-probe-authorization-review-v1/transport_report.json",
            "src/auragateway/contracts/openrouter.py",
            "src/auragateway/providers/openrouter.py",
            "src/auragateway/providers/openrouter_http.py",
        }
        if set(paths) != required_paths:
            raise ValueError("activation requires the eight exact reviewed source paths")
        return self


class OpenRouterProbeActivationRuntimePolicy(BaseModel):
    """Fail-closed execution policy activated for the later live runner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    logical_call_roles: tuple[Literal["cold_probe"], Literal["warm_probe"]]
    stable_session_required: Literal[True] = True
    sequential_execution_required: Literal[True] = True
    warm_call_requires_retained_cold_success: Literal[True] = True
    maximum_total_inference_attempts: Literal[4] = 4
    maximum_transient_replacements_per_logical_call: Literal[1] = 1
    transient_http_statuses: tuple[Literal[429], Literal[502], Literal[524], Literal[529]]
    automatic_transport_retry_permitted: Literal[False] = False
    successful_response_retry_permitted: Literal[False] = False
    generation_metadata_polling_permitted: Literal[False] = False
    successful_completion_requires_generation_metadata: Literal[True] = True
    write_through_journal_required: Literal[True] = True
    protected_raw_retention_required: Literal[True] = True
    protected_parsed_retention_required: Literal[True] = True
    public_raw_payload_permitted: Literal[False] = False
    authorization_consumed_on_terminal_closeout: Literal[True] = True
    resume_permitted: Literal[False] = False
    rerun_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_policy(self) -> OpenRouterProbeActivationRuntimePolicy:
        if self.logical_call_roles != ("cold_probe", "warm_probe"):
            raise ValueError("activation roles must remain cold then warm")
        if self.transient_http_statuses != (429, 502, 524, 529):
            raise ValueError("activation transient statuses must remain exact")
        return self


class OpenRouterProbeProtectedCall(BaseModel):
    """One exact protected request definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    logical_call_index: int = Field(ge=0, le=1)
    request_role: Literal["cold_probe", "warm_probe"]
    request_id: str = Field(min_length=3, max_length=128)
    fixture_id: str = Field(min_length=3, max_length=128)
    user_suffix: str = Field(min_length=10, max_length=200)
    expected_output: str = Field(min_length=3, max_length=100)


class OpenRouterProbeProtectedPromptBundle(BaseModel):
    """Protected synthetic prompt material generated locally from the reviewed recipe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    bundle_id: Literal["openrouter-hy3-capability-probe-prompt-bundle-v1"]
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    recipe_id: Literal["openrouter-hy3-capability-probe-prompt-v1"]
    requested_model: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    session_id: str = Field(min_length=3, max_length=256)
    stable_prefix: str = Field(min_length=1000)
    stable_prefix_sha256: str
    stable_prefix_bytes: int = Field(gt=0)
    output_token_budget: Literal[32] = 32
    temperature_milli: Literal[0] = 0
    streaming: Literal[False] = False
    provider_data_collection: Literal["deny"] = "deny"
    provider_zero_data_retention: Literal[True] = True
    manual_provider_order_present: Literal[False] = False
    calls: tuple[OpenRouterProbeProtectedCall, OpenRouterProbeProtectedCall]
    synthetic_public_safe: Literal[True] = True
    public_release_permitted: Literal[False] = False

    @field_validator("stable_prefix_sha256")
    @classmethod
    def validate_prefix_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("stable prefix requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_bundle(self) -> OpenRouterProbeProtectedPromptBundle:
        if tuple(item.logical_call_index for item in self.calls) != (0, 1):
            raise ValueError("protected calls must retain indexes zero and one")
        if tuple(item.request_role for item in self.calls) != ("cold_probe", "warm_probe"):
            raise ValueError("protected calls must retain cold then warm order")
        if len({item.request_id for item in self.calls}) != 2:
            raise ValueError("protected request IDs must be unique")
        return self


class OpenRouterProbeLocalPreparationReceipt(BaseModel):
    """Metadata-safe local receipt for protected prompt preparation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    status: Literal[OpenRouterProbeLocalStatus.PREPARED] = OpenRouterProbeLocalStatus.PREPARED
    prompt_bundle_sha256: str
    prompt_bundle_bytes: int = Field(gt=0)
    session_id_sha256: str
    journal_initialized: Literal[True] = True
    credential_accessed: Literal[False] = False
    network_request_performed: Literal[False] = False
    inference_call_performed: Literal[False] = False

    @field_validator("prompt_bundle_sha256", "session_id_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("local preparation receipts require lowercase SHA-256")
        return value


class OpenRouterProbeKeyStatus(BaseModel):
    """Typed metadata from OpenRouter GET /api/v1/key."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    label: str = Field(min_length=1, max_length=500)
    limit: Decimal | None = Field(default=None, ge=0)
    limit_remaining: Decimal | None = Field(default=None, ge=0)
    usage: Decimal = Field(ge=0)
    usage_daily: Decimal = Field(ge=0)
    usage_weekly: Decimal = Field(ge=0)
    usage_monthly: Decimal = Field(ge=0)
    is_free_tier: bool


class OpenRouterProbeKeyStatusEnvelope(BaseModel):
    """OpenRouter key-status response envelope."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    data: OpenRouterProbeKeyStatus


class OpenRouterProbeModelCatalogEntry(BaseModel):
    """Minimal model-catalog identity needed for route availability preflight."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(min_length=3, max_length=200)


class OpenRouterProbeModelCatalog(BaseModel):
    """Minimal OpenRouter model-catalog response."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    data: tuple[OpenRouterProbeModelCatalogEntry, ...] = Field(min_length=1)


class OpenRouterProbePreflightReceipt(BaseModel):
    """Protected metadata-only receipt for credential and route preflight."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    status: Literal[OpenRouterProbeLocalStatus.PREFLIGHT_PASSED] = (
        OpenRouterProbeLocalStatus.PREFLIGHT_PASSED
    )
    prompt_bundle_sha256: str
    key_status_response_sha256: str
    model_catalog_response_sha256: str
    key_label_sha256: str
    limit: Decimal | None = Field(default=None, ge=0)
    limit_remaining: Decimal | None = Field(default=None, ge=0)
    usage: Decimal = Field(ge=0)
    usage_daily: Decimal = Field(ge=0)
    is_free_tier: bool
    requested_model: Literal["tencent/hy3:free"] = "tencent/hy3:free"
    requested_model_available: Literal[True] = True
    credential_accessed: Literal[True] = True
    network_request_count: Literal[2] = 2
    inference_call_count: Literal[0] = 0
    authorization_consumed: Literal[False] = False
    execution_confirmation_still_required: Literal[True] = True

    @field_validator(
        "prompt_bundle_sha256",
        "key_status_response_sha256",
        "model_catalog_response_sha256",
        "key_label_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("preflight receipts require lowercase SHA-256")
        return value


class OpenRouterProbeActivationReport(BaseModel):
    """Public report for the inactive-at-rest activation package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    execution_id: Literal["openrouter-hy3-capability-probe-v1"]
    status: Literal[OpenRouterProbeActivationStatus.ACTIVE] = OpenRouterProbeActivationStatus.ACTIVE
    active_authorization_created: Literal[True] = True
    local_preparation_command_available: Literal[True] = True
    live_preflight_command_available: Literal[True] = True
    execution_command_available: Literal[False] = False
    credential_accessed: Literal[False] = False
    network_request_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    capability_probe_execution_authorized: Literal[True] = True
    execution_confirmation_required: Literal[True] = True
    authorization_consumed: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    retained_benchmark_authorized: Literal[False] = False
    comparison_eligible: Literal[False] = False
    next_gate: Literal["protected_local_preparation_and_live_preflight"] = (
        "protected_local_preparation_and_live_preflight"
    )


class OpenRouterProbeActivationManifest(BaseModel):
    """Integrity manifest for committed activation assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["openrouter-hy3-capability-probe-auth-v1"]
    authorization_sha256: str
    runtime_policy_sha256: str
    activation_report_sha256: str
    contract_sha256: str
    runner_sha256: str
    adr_sha256: str
    report_sha256: str
    active_authorization_created: Literal[True] = True
    provider_call_performed: Literal[False] = False

    @field_validator(
        "authorization_sha256",
        "runtime_policy_sha256",
        "activation_report_sha256",
        "contract_sha256",
        "runner_sha256",
        "adr_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("activation manifest requires lowercase SHA-256")
        return value


class OpenRouterProbeActivationSummary(BaseModel):
    """Metadata-safe CLI summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: Literal["validate", "prepare-local", "preflight", "verify-local"]
    authorization_id: str
    authorization_status: OpenRouterProbeActivationStatus
    protected_prompt_bundle_ready: bool
    live_preflight_passed: bool
    credential_accessed: bool
    network_request_count: int = Field(ge=0, le=2)
    inference_call_count: Literal[0] = 0
    capability_probe_execution_authorized: Literal[True] = True
    execution_confirmation_required: Literal[True] = True
    authorization_consumed: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    next_gate: str


class OpenRouterProbeActivationErrorEnvelope(BaseModel):
    """Metadata-safe activation CLI error."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()
