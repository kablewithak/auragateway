"""Implement, issue, verify, abandon, and consume one P5/P6 successor authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_MERGE_COMMIT: Final = "6e424acb27e568bb7ce5000ea0732e175bf6b35a"
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
SELECTED_BACKEND: Final = "TRITON_ATTN"
PLATFORM_ACCELERATOR: Final = "GPU_T4_X2"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES: Final = 15
MAXIMUM_CONFIRMATION_AGE_MINUTES: Final = 15

SOURCE_PATH: Final = Path("src/auragateway/local_abc/p5_p6_successor_execution_authorization_v1.py")
TEST_PATH: Final = Path("tests/unit/local_abc/test_p5_p6_successor_execution_authorization_v1.py")
ADR_PATH: Final = Path(
    "docs/adr/2026-08-07-local-abc-p5-p6-successor-execution-authorization-v1.md"
)
REPORT_PATH: Final = Path("docs/reports/AuraGateway_P5_P6_Successor_Execution_Authorization_V1.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_p5_p6_successor_execution_authorization_v1.md")
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_v1_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_v1.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_consumption_v1.json"
)
ABANDONMENT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_abandonment_v1.json"
)

IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_record.json"
)
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_runtime_qualification_v1_implementation_review.json"
)
IMPLEMENTATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_runtime_qualification_v1_request.json"
)
IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1.py"
)
IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_successor_runtime_qualification_v1.py.tmpl"
)
IMPLEMENTATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_successor_runtime_qualification_v1.py"
)
IMPLEMENTATION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_successor_runtime_qualification_v1.ipynb"
)
IMPLEMENTATION_ADR_PATH: Final = Path(
    "docs/adr/2026-08-07-local-abc-p5-p6-successor-runtime-qualification-v1-implementation.md"
)
IMPLEMENTATION_REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Successor_Runtime_Qualification_V1_Implementation.md"
)
IMPLEMENTATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_successor_runtime_qualification_v1.md"
)

AUTHORIZATION_ID: Final = "auragateway-p5-p6-successor-execution-authorization-v1"
AUTHORIZATION_SCOPE: Final = "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1"
IMPLEMENTATION_NEXT_GATE: Final = (
    "merge_then_observe_kaggle_and_issue_p5_p6_successor_execution_authorization_v1"
)
ISSUED_NEXT_GATE: Final = "execute_governed_p5_p6_successor_runtime_qualification_v1_once"
CONSUMED_NEXT_GATE: Final = (
    "preserve_and_accept_or_classify_p5_p6_successor_runtime_qualification_v1"
)
ABANDONED_NEXT_GATE: Final = "reconcile_then_issue_fresh_p5_p6_successor_execution_authorization_v1"

EXPECTED_RUNTIME_OUTPUTS: Final = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "p3_worker_startup_report_v1.json",
    "p3_native_origin_report_v1.json",
    "p4_case_a_canary_report_v1.json",
    "p5_prefix_cache_reset_report_v1.json",
    "p5_post_restart_native_origin_report_v1.json",
    "p6_stage_checkpoint_report_v1.json",
    "p6_native_origin_report_v1.json",
    "p6_dual_worker_isolation_report_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "p5_p6_successor_runtime_qualification_summary_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
    "ag-p5-p6-successor-runtime-evidence-v1.zip",
)

EXPECTED_ARTIFACTS: Final = {
    IMPLEMENTATION_RECORD_PATH: (
        "386d2fa9b3695ba664316f05ad805e01cac74d317ff9568a813a03127dc86285",
        9112,
        True,
    ),
    IMPLEMENTATION_REVIEW_PATH: (
        "ddeb10a6c76f6187d8654dd8a02d4574fdbc428e9b99bd806178ea48da119cfb",
        4674,
        True,
    ),
    IMPLEMENTATION_REQUEST_PATH: (
        "a341d81489255c25c95a3fd70962e214c0841e9eee8ff5bd54faef02dd60d07a",
        7286,
        True,
    ),
    IMPLEMENTATION_SOURCE_PATH: (
        "a8c5741b6385a5f9393679a77b2c55b9d8bfbfeb32351c3d3708b21d6f4ebd82",
        50356,
        True,
    ),
    IMPLEMENTATION_TEMPLATE_PATH: (
        "fd67c6377835b097be3b9b68a6c8abe4685a391250dc532fcdfa393bcc04f672",
        118198,
        True,
    ),
    IMPLEMENTATION_TEST_PATH: (
        "9a7b2870b5c5d83f6b94e33f4444b5df55842631762b3140c13f11d05239e167",
        13047,
        True,
    ),
    IMPLEMENTATION_NOTEBOOK_PATH: (
        "113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8",
        196720,
        False,
    ),
    IMPLEMENTATION_ADR_PATH: (
        "bb78abba8c358a60c973a45f9c80dcb82e6c9bbc7fb84b170cc606ecc857a789",
        3844,
        True,
    ),
    IMPLEMENTATION_REPORT_PATH: (
        "f3f9fa742f25ec20bd70333ea39c5fbd8d95896ee35447b973b3a81944403fac",
        3409,
        True,
    ),
    IMPLEMENTATION_RUNBOOK_PATH: (
        "5ae1d24a0d291eee6d611cda903ddab227ffd4b980baeca0a3a19fcb40cbfae8",
        2584,
        True,
    ),
}

CONTROL_HASHES: Final = {
    "requirements.in": "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f",
    "resolution_lock.json": ("1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"),
    "materialization.lock.txt": (
        "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
    ),
    "requirements.lock.txt": ("47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"),
    "install_runtime.py": ("68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"),
    "runtime_manifest.json": ("b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"),
    "sha256_manifest.json": ("789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"),
    "materialization_receipt.json": (
        "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
    ),
}

EXPECTED_REQUEST_IDENTITIES: Final = {
    "all_runtime_payloads_identical": True,
    "eligible_prefix_messages_sha256": (
        "24b2b7bf593086e73bb0d39bee39d1f8eec72b73cf05892da80d838e75e893bc"
    ),
    "p4_canary_logical_sha256": (
        "3bd1579ade8222df8fb9f64d75db707a336a007708581d27f6bcf76a00ea2363"
    ),
    "p5_cold_logical_sha256": ("3bd1579ade8222df8fb9f64d75db707a336a007708581d27f6bcf76a00ea2363"),
    "p5_cold_reuses_p4_canary": True,
    "p5_post_restart_logical_sha256": (
        "05f5342e7a37aaed4a1e0e141906715e86fbcb0afb60ad9e2a7f77cf5283b8be"
    ),
    "p5_warm_logical_sha256": ("93d9f1dc602e7f0aca8be48bf7da709ad8e14d29f53aa96f0c7a70e9e04fd00d"),
    "p6_worker_1_logical_sha256": (
        "444992b33ad33ff61e21ea9ac41580138dc9eb0438e7cfb47255b8abf09e4ac0"
    ),
    "p6_worker_2_logical_sha256": (
        "caf1bd38e0026dd7c99828d1d60fbcdfcc6b6cab8714ccd19ec7914b2beb6af0"
    ),
    "payload_sha256": ("4caff3d704ab21b8957816cfde34dcb5d8c406f5478280b83db369be92abfe66"),
    "shared_messages_sha256": ("1016da762d96c38c2f78a46e30c0b225937941ad9c46c6ad5bfac8b55001e878"),
}


class AuthorizationLifecycle(StrEnum):
    """Lifecycle states for transient successor authority."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"
    ABANDONED = "ABANDONED"


class ExecutionOutcome(StrEnum):
    """Terminal outcomes that consume the single-use authority."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    TIMED_OUT = "TIMED_OUT"
    KAGGLE_PLATFORM_TERMINATED = "KAGGLE_PLATFORM_TERMINATED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class AbandonmentReason(StrEnum):
    """Pre-execution reasons that terminalize an unused authority."""

    OPERATOR_CANCELLED = "OPERATOR_CANCELLED"
    AUTHORIZATION_EXPIRED_UNUSED = "AUTHORIZATION_EXPIRED_UNUSED"
    PLATFORM_CAPABILITY_CHANGED = "PLATFORM_CAPABILITY_CHANGED"
    INPUT_IDENTITY_CHANGED = "INPUT_IDENTITY_CHANGED"
    OTHER = "OTHER"


class SuccessorAuthorizationError(RuntimeError):
    """Metadata-safe successor authorization failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class ErrorEnvelope(LocalABCContract):
    """Machine-readable error without sensitive payloads."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ARGUMENT_INVALID",
            "P5/P6 successor authorization arguments are invalid",
            details=(message,),
        )


class ArtifactReceipt(LocalABCContract):
    """Exact repository artifact identity."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class WheelhouseAuthority(LocalABCContract):
    """Exact governed offline wheelhouse contract."""

    control_hashes: dict[str, str]
    manifest_entry_count: Literal[182] = 182
    verified_entry_count: Literal[182] = 182
    wheel_entry_count: Literal[176] = 176
    exact_manifest_required: Literal[True] = True

    @field_validator("control_hashes")
    @classmethod
    def validate_control_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        if value != CONTROL_HASHES:
            raise ValueError("wheelhouse control hashes drifted")
        return value


class RequestIdentityAuthority(LocalABCContract):
    """Exact logical request identities frozen by successor implementation."""

    all_runtime_payloads_identical: Literal[True] = True
    eligible_prefix_messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p4_canary_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_cold_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_cold_reuses_p4_canary: Literal[True] = True
    p5_post_restart_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_warm_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p6_worker_1_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p6_worker_2_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shared_messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_exact_identities(self) -> Self:
        if self.model_dump(mode="json") != EXPECTED_REQUEST_IDENTITIES:
            raise ValueError("successor logical request identities drifted")
        return self


class SuccessorEvidenceAuthority(LocalABCContract):
    """P5/P6 runtime evidence properties bound by one authorization."""

    p4_v2_native_environment_required: Literal[True] = True
    cuda_stub_filtering_required: Literal[True] = True
    inherited_ld_preload_permitted: Literal[False] = False
    required_target_native_tokens: tuple[Literal["libcusparse"], Literal["libnvJitLink"]]
    ambient_non_stub_cuda_origins_permitted: Literal[True] = True
    v5_resource_envelope_required: Literal[True] = True
    exact_case_a_request_required: Literal[True] = True
    p4_canary_is_p5_cold_baseline: Literal[True] = True
    token_telemetry_is_primary_p5_proof: Literal[True] = True
    latency_as_primary_p5_proof_permitted: Literal[False] = False
    full_process_restart_required: Literal[True] = True
    namespace_only_reset_sufficient: Literal[False] = False
    post_restart_backend_revalidation_required: Literal[True] = True
    post_restart_native_origin_revalidation_required: Literal[True] = True
    typed_route_acknowledgement_required: Literal[True] = True
    model_semantics_permitted_as_p6_route_proof: Literal[False] = False
    both_worker_metrics_snapshotted_per_route: Literal[True] = True
    per_worker_attempt_and_completion_counters_required: Literal[True] = True
    partial_p6_evidence_preservation_required: Literal[True] = True
    structured_teardown_report_required: Literal[True] = True
    request_count_reconciliation_required: Literal[True] = True
    ambiguous_relevant_metric_series_fail_closed: Literal[True] = True


class ExecutionBudget(LocalABCContract):
    """Non-expandable execution and publication budget."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_saved_versions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[5] = 5
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_workers: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class RuntimeControls(LocalABCContract):
    """Privacy, runtime, route, and teardown controls."""

    accelerator: Literal["GPU_T4_X2"] = "GPU_T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    loopback_http_permitted: Literal[True] = True
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    raw_worker_logs_in_evidence_permitted: Literal[False] = False
    explicit_backend_required: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    automatic_backend_selection_permitted: Literal[False] = False
    silent_backend_fallback_permitted: Literal[False] = False
    worker_1_cuda_visible_devices: Literal["0"] = "0"
    worker_1_gpu_index: Literal[0] = 0
    worker_1_port: Literal[8001] = 8001
    worker_2_cuda_visible_devices: Literal["1"] = "1"
    worker_2_gpu_index: Literal[1] = 1
    worker_2_port: Literal[8002] = 8002
    stop_on_first_failure: Literal[True] = True
    partial_evidence_required: Literal[True] = True
    full_process_restart_required: Literal[True] = True
    request_count_reconciliation_required: Literal[True] = True
    governed_teardown_required: Literal[True] = True
    evidence_zip_required: Literal[True] = True
    maximum_evidence_zip_bytes: Literal[2097152] = 2097152


class ImplementationAuthority(LocalABCContract):
    """Exact merged successor implementation authority."""

    source_main_merge_commit: Literal["6e424acb27e568bb7ce5000ea0732e175bf6b35a"]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    implementation_record: ArtifactReceipt
    architecture_review: ArtifactReceipt
    request: ArtifactReceipt
    source: ArtifactReceipt
    template: ArtifactReceipt
    tests: ArtifactReceipt
    notebook: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    notebook_name: Literal["ag-p5-p6-successor-runtime-qual-v1"]
    failed_notebook_name: Literal["ag-p5-p6-successor-runtime-failed-v1"]
    runtime_script_sha256: Literal[
        "5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"
    ]
    wrapper_code_sha256: Literal["f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    selected_backend: Literal["TRITON_ATTN"]
    request_identities: RequestIdentityAuthority
    expected_runtime_outputs: tuple[str, ...]
    wheelhouse: WheelhouseAuthority
    execution_budget: ExecutionBudget
    controls: RuntimeControls
    evidence: SuccessorEvidenceAuthority
    runtime_execution_authorized_before_issuance: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> Self:
        if self.expected_runtime_outputs != EXPECTED_RUNTIME_OUTPUTS:
            raise ValueError("successor runtime output contract drifted")
        return self


class ArchitectureReview(LocalABCContract):
    """Deterministic authorization design review."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1-review"]
    status: Literal["APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"]
    decision: Literal["SEPARATE_TRANSIENT_SINGLE_USE_P5_P6_SUCCESSOR_AUTHORIZATION"]
    implementation: ImplementationAuthority
    budget: ExecutionBudget
    controls: RuntimeControls
    operator_confirmation_required: Literal[True]
    live_platform_observation_required: Literal[True]
    maximum_platform_observation_age_minutes: Literal[15] = 15
    authorization_must_remain_untracked: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unused_authority_may_be_abandoned_non_reusably: Literal[True]
    runtime_execution_authorized_in_review: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    next_gate: Literal[
        "merge_then_observe_kaggle_and_issue_p5_p6_successor_execution_authorization_v1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=10)


class ImplementationRecord(LocalABCContract):
    """Repository receipt for the static authorization issuer."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1-record"]
    status: Literal["P5_P6_SUCCESSOR_EXECUTION_AUTHORIZATION_V1_VALID"]
    source_main_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation: ImplementationAuthority
    review: ArtifactReceipt
    issuer_source: ArtifactReceipt
    issuer_tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    authorization_path: str
    consumption_path: str
    abandonment_path: str
    authorization_issuer_implemented: Literal[True]
    authorization_issued: Literal[False]
    consumption_record_created: Literal[False]
    abandonment_record_created: Literal[False]
    runtime_execution_performed: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    budget: ExecutionBudget
    controls: RuntimeControls
    next_gate: Literal[
        "merge_then_observe_kaggle_and_issue_p5_p6_successor_execution_authorization_v1"
    ]


class PlatformCapabilityObservation(LocalABCContract):
    """Fresh Kaggle settings observed immediately before issuance."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    observed_at: datetime
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    observed_platform_accelerator: Literal["GPU_T4_X2"]
    observed_allocated_gpu_count: Literal[2]
    observed_internet_enabled: Literal[False]
    observed_wheelhouse_attachment_count: Literal[1]
    observed_model_snapshot_attachment_count: Literal[1]
    worker_1_cuda_visible_devices: Literal["0"]
    worker_1_visible_gpu_count: Literal[1]
    worker_1_gpu_index: Literal[0]
    worker_2_cuda_visible_devices: Literal["1"]
    worker_2_visible_gpu_count: Literal[1]
    worker_2_gpu_index: Literal[1]

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class IssuanceConfirmation(LocalABCContract):
    """Explicit operator confirmation binding exact successor bytes and capability."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    confirmation_id: Literal["auragateway-p5-p6-successor-execution-authorization-confirmation-v1"]
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_scope: Literal["P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1"]
    confirmed_implementation_merge_commit: Literal["6e424acb27e568bb7ce5000ea0732e175bf6b35a"]
    confirmed_notebook_sha256: Literal[
        "113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8"
    ]
    confirmed_runtime_script_sha256: Literal[
        "5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"
    ]
    confirmed_wrapper_code_sha256: Literal[
        "f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"
    ]
    confirmed_request_sha256: Literal[
        "a341d81489255c25c95a3fd70962e214c0841e9eee8ff5bd54faef02dd60d07a"
    ]
    confirmed_implementation_record_sha256: Literal[
        "386d2fa9b3695ba664316f05ad805e01cac74d317ff9568a813a03127dc86285"
    ]
    confirmed_model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    confirmed_backend: Literal["TRITON_ATTN"]
    confirmed_model_request_budget: Literal[5]
    confirmed_worker_start_budget: Literal[3]
    confirmed_model_load_budget: Literal[3]
    confirmed_saved_version_budget: Literal[1]
    confirmed_no_hidden_retries: Literal[True]
    confirmed_no_replacement_workers: Literal[True]
    confirmed_consumption_required: Literal[True]
    platform: PlatformCapabilityObservation

    @field_validator("confirmed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def require_fresh_platform_observation(self) -> Self:
        if self.platform.observed_at > self.confirmed_at:
            raise ValueError("platform observation cannot follow confirmation")
        maximum = timedelta(minutes=MAXIMUM_PLATFORM_OBSERVATION_AGE_MINUTES)
        if self.confirmed_at - self.platform.observed_at > maximum:
            raise ValueError("platform observation is older than 15 minutes")
        return self


class ExecutionAuthorization(LocalABCContract):
    """Transient, single-use live successor execution authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1"]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal[AuthorizationLifecycle.ISSUED]
    scope: Literal["P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1"]
    source_main_merge_commit: Literal["6e424acb27e568bb7ce5000ea0732e175bf6b35a"]
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    implementation: ImplementationAuthority
    capability_observation: PlatformCapabilityObservation
    operator_confirmation_recorded: Literal[True]
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    budget: ExecutionBudget
    controls: RuntimeControls

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        maximum = timedelta(minutes=MAXIMUM_AUTHORIZATION_WINDOW_MINUTES)
        if self.expires_at - self.issued_at > maximum:
            raise ValueError("authorization window exceeds reviewed budget")
        return self


class AuthorizationConsumption(LocalABCContract):
    """Non-overwriting terminal receipt after one governed attempt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: Literal["auragateway-p5-p6-successor-execution-authorization-consumption-v1"]
    authorization_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED]
    consumed_at: datetime
    outcome: ExecutionOutcome
    saved_version_id: int | None = Field(default=None, gt=0)
    evidence_zip_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["preserve_and_accept_or_classify_p5_p6_successor_runtime_qualification_v1"]

    @field_validator("consumed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)

    @model_validator(mode="after")
    def require_pass_evidence(self) -> Self:
        if self.outcome is ExecutionOutcome.PASSED:
            if self.saved_version_id is None:
                raise ValueError("passed execution requires saved_version_id")
            if self.evidence_zip_sha256 is None or self.terminal_log_sha256 is None:
                raise ValueError("passed execution requires terminal evidence hashes")
        return self


class AuthorizationAbandonment(LocalABCContract):
    """Non-overwriting pre-execution terminalization of one unused authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    abandonment_id: Literal["auragateway-p5-p6-successor-execution-authorization-abandonment-v1"]
    authorization_id: Literal["auragateway-p5-p6-successor-execution-authorization-v1"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.ABANDONED]
    abandoned_at: datetime
    reason: AbandonmentReason
    execution_attempted: Literal[False]
    authorization_reusable: Literal[False]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["reconcile_then_issue_fresh_p5_p6_successor_execution_authorization_v1"]

    @field_validator("abandoned_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("abandoned_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_lf(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _read_artifact_bytes(
    repo_root: Path,
    relative_path: Path,
    *,
    normalize_text: bool,
) -> bytes:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ARTIFACT_UNSAFE",
            "a required authorization artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    return _canonical_lf(payload) if normalize_text else payload


def _artifact(
    repo_root: Path,
    relative_path: Path,
    *,
    normalize_text: bool = True,
) -> ArtifactReceipt:
    payload = _read_artifact_bytes(
        repo_root,
        relative_path,
        normalize_text=normalize_text,
    )
    return ArtifactReceipt(
        repository_path=relative_path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _expected_artifact(repo_root: Path, relative_path: Path) -> ArtifactReceipt:
    expected_sha256, expected_size, normalize_text = EXPECTED_ARTIFACTS[relative_path]
    observed = _artifact(
        repo_root,
        relative_path,
        normalize_text=normalize_text,
    )
    if observed.sha256 != expected_sha256 or observed.size_bytes != expected_size:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_IMPLEMENTATION_IDENTITY_DRIFT",
            "a merged successor implementation artifact identity drifted",
            relative_path.as_posix(),
            (
                f"expected_sha256={expected_sha256}",
                f"observed_sha256={observed.sha256}",
                f"expected_size={expected_size}",
                f"observed_size={observed.size_bytes}",
            ),
        )
    return observed


def _read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    path = repo_root / relative_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_JSON_INVALID",
            "a required successor authority is not valid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_JSON_INVALID",
            "a required successor authority is not a JSON object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _require_value(
    payload: dict[str, object],
    key: str,
    expected: object,
    path: Path,
) -> None:
    if payload.get(key) != expected:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_SEMANTIC_DRIFT",
            "a merged successor semantic authority drifted",
            path.as_posix(),
            (f"field={key}",),
        )


def _validate_successor_semantics(repo_root: Path) -> None:
    record = _read_json_object(repo_root, IMPLEMENTATION_RECORD_PATH)
    _require_value(record, "status", "IMPLEMENTED_NOT_EXECUTED", IMPLEMENTATION_RECORD_PATH)
    _require_value(record, "authorization_issuer_included", False, IMPLEMENTATION_RECORD_PATH)
    _require_value(
        record,
        "next_gate",
        "merge_then_design_separate_p5_p6_successor_execution_authorization_v1",
        IMPLEMENTATION_RECORD_PATH,
    )
    _require_value(
        record,
        "expected_runtime_outputs",
        list(EXPECTED_RUNTIME_OUTPUTS),
        IMPLEMENTATION_RECORD_PATH,
    )

    safety = record.get("safety")
    if not isinstance(safety, dict):
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_SEMANTIC_DRIFT",
            "the successor implementation safety contract is missing",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    for key, expected in {
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "kaggle_execution_performed": False,
        "gpu_execution_performed": False,
        "model_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
        "benchmark_trajectory_requests_performed": 0,
        "network_requests_performed": 0,
    }.items():
        if safety.get(key) != expected:
            raise SuccessorAuthorizationError(
                "P5_P6_AUTHORIZATION_PREEXECUTION_STATE_DRIFT",
                "the successor implementation no longer has a clean pre-execution state",
                IMPLEMENTATION_RECORD_PATH.as_posix(),
                (f"field=safety.{key}",),
            )

    request = _read_json_object(repo_root, IMPLEMENTATION_REQUEST_PATH)
    _require_value(request, "runtime_execution_authorized", False, IMPLEMENTATION_REQUEST_PATH)
    _require_value(request, "measured_abc_execution_authorized", False, IMPLEMENTATION_REQUEST_PATH)
    _require_value(request, "authorization_issuer_included", False, IMPLEMENTATION_REQUEST_PATH)
    _require_value(request, "selected_backend", SELECTED_BACKEND, IMPLEMENTATION_REQUEST_PATH)
    _require_value(request, "model_repository", MODEL_REPOSITORY, IMPLEMENTATION_REQUEST_PATH)
    _require_value(request, "model_revision", MODEL_REVISION, IMPLEMENTATION_REQUEST_PATH)
    _require_value(
        request,
        "model_snapshot_sha256",
        MODEL_SNAPSHOT_SHA256,
        IMPLEMENTATION_REQUEST_PATH,
    )
    _require_value(
        request,
        "strategy",
        "P4_V2_ENVIRONMENT_PLUS_V5_P5_P6_SUCCESSOR_COMPOSITION",
        IMPLEMENTATION_REQUEST_PATH,
    )
    _require_value(
        request,
        "request_identities",
        EXPECTED_REQUEST_IDENTITIES,
        IMPLEMENTATION_REQUEST_PATH,
    )

    budget = request.get("execution_budget")
    expected_budget = {
        "maximum_kaggle_sessions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_model_requests": 5,
        "maximum_output_tokens_per_request": 32,
        "benchmark_trajectory_requests_permitted": 0,
        "hidden_retries_permitted": 0,
        "replacement_workers_permitted": 0,
        "network_requests_permitted": 0,
        "external_spend": 0,
    }
    if budget != expected_budget:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_BUDGET_DRIFT",
            "the successor execution budget drifted",
            IMPLEMENTATION_REQUEST_PATH.as_posix(),
        )

    review = _read_json_object(repo_root, IMPLEMENTATION_REVIEW_PATH)
    _require_value(
        review,
        "decision",
        "APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        IMPLEMENTATION_REVIEW_PATH,
    )
    _require_value(review, "runtime_execution_authorized", False, IMPLEMENTATION_REVIEW_PATH)
    _require_value(
        review,
        "measured_abc_execution_authorized",
        False,
        IMPLEMENTATION_REVIEW_PATH,
    )
    _require_value(
        review,
        "output_contract",
        list(EXPECTED_RUNTIME_OUTPUTS),
        IMPLEMENTATION_REVIEW_PATH,
    )

    template = (repo_root / IMPLEMENTATION_TEMPLATE_PATH).read_text(encoding="utf-8")
    markers = (
        '"CUDA_VISIBLE_DEVICES": str(gpu_index)',
        '"--attention-backend",',
        '"TRITON_ATTN"',
        '"--no-enable-log-requests",',
        "TARGET_REQUIRED_NATIVE_TOKENS = (",
        '"libcusparse"',
        '"libnvjitlink"',
        'f"ambiguous relevant metric series: {name}"',
        "8001",
        "8002",
        "vllm:prompt_tokens_cached_total",
        "vllm:request_prefill_kv_computed_tokens_sum",
    )
    missing = tuple(marker for marker in markers if marker not in template)
    if missing:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_RUNTIME_CONTRACT_DRIFT",
            "the successor executable runtime contract drifted",
            IMPLEMENTATION_TEMPLATE_PATH.as_posix(),
            missing,
        )


def _implementation(repo_root: Path) -> ImplementationAuthority:
    for path in EXPECTED_ARTIFACTS:
        _expected_artifact(repo_root, path)
    _validate_successor_semantics(repo_root)

    return ImplementationAuthority(
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        implementation_record=_expected_artifact(repo_root, IMPLEMENTATION_RECORD_PATH),
        architecture_review=_expected_artifact(repo_root, IMPLEMENTATION_REVIEW_PATH),
        request=_expected_artifact(repo_root, IMPLEMENTATION_REQUEST_PATH),
        source=_expected_artifact(repo_root, IMPLEMENTATION_SOURCE_PATH),
        template=_expected_artifact(repo_root, IMPLEMENTATION_TEMPLATE_PATH),
        tests=_expected_artifact(repo_root, IMPLEMENTATION_TEST_PATH),
        notebook=_expected_artifact(repo_root, IMPLEMENTATION_NOTEBOOK_PATH),
        adr=_expected_artifact(repo_root, IMPLEMENTATION_ADR_PATH),
        report=_expected_artifact(repo_root, IMPLEMENTATION_REPORT_PATH),
        runbook=_expected_artifact(repo_root, IMPLEMENTATION_RUNBOOK_PATH),
        notebook_name="ag-p5-p6-successor-runtime-qual-v1",
        failed_notebook_name="ag-p5-p6-successor-runtime-failed-v1",
        runtime_script_sha256=("5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"),
        wrapper_code_sha256=("f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"),
        model_repository=MODEL_REPOSITORY,
        model_revision=MODEL_REVISION,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        selected_backend=SELECTED_BACKEND,
        request_identities=RequestIdentityAuthority.model_validate(EXPECTED_REQUEST_IDENTITIES),
        expected_runtime_outputs=EXPECTED_RUNTIME_OUTPUTS,
        wheelhouse=WheelhouseAuthority(control_hashes=dict(CONTROL_HASHES)),
        execution_budget=ExecutionBudget(),
        controls=RuntimeControls(),
        evidence=SuccessorEvidenceAuthority(
            required_target_native_tokens=("libcusparse", "libnvJitLink"),
        ),
        runtime_execution_authorized_before_issuance=False,
        measured_abc_execution_authorized=False,
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "Authorization implementation does not issue live runtime authority.",
        "Current-line successor P5 cache reuse is not yet established.",
        "Current-line successor P5 full-process reset is not yet established.",
        "Current-line successor P6 route isolation is not yet established.",
        "Current-line successor P6 metric isolation is not yet established.",
        "The five-request ceiling is not a target request count.",
        "A T4 x2 platform observation does not itself prove worker realization.",
        "Configured CUDA_VISIBLE_DEVICES does not prove realized GPU identity.",
        "Runtime execution remains blocked until a fresh live authority is issued.",
        "Measured A/B/C execution remains unauthorized.",
        "Pressure and cache-eviction behavior are not established.",
        "Fault-recovery behavior is not established.",
        "No customer data or credentials are authorized.",
        "Deployment readiness is not established.",
        "Production readiness is not established.",
    )


def _build_review(repo_root: Path) -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-p5-p6-successor-execution-authorization-v1-review",
        status="APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION",
        decision="SEPARATE_TRANSIENT_SINGLE_USE_P5_P6_SUCCESSOR_AUTHORIZATION",
        implementation=_implementation(repo_root),
        budget=ExecutionBudget(),
        controls=RuntimeControls(),
        operator_confirmation_required=True,
        live_platform_observation_required=True,
        maximum_platform_observation_age_minutes=15,
        authorization_must_remain_untracked=True,
        every_terminal_attempt_consumes_authorization=True,
        unused_authority_may_be_abandoned_non_reusably=True,
        runtime_execution_authorized_in_review=False,
        measured_abc_execution_authorized=False,
        next_gate=IMPLEMENTATION_NEXT_GATE,
        non_claims=_non_claims(),
    )


def _build_record(repo_root: Path, review_bytes: bytes) -> ImplementationRecord:
    return ImplementationRecord(
        record_id="auragateway-p5-p6-successor-execution-authorization-v1-record",
        status="P5_P6_SUCCESSOR_EXECUTION_AUTHORIZATION_V1_VALID",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        implementation=_implementation(repo_root),
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        issuer_source=_artifact(repo_root, SOURCE_PATH),
        issuer_tests=_artifact(repo_root, TEST_PATH),
        adr=_artifact(repo_root, ADR_PATH),
        report=_artifact(repo_root, REPORT_PATH),
        runbook=_artifact(repo_root, RUNBOOK_PATH),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        consumption_path=CONSUMPTION_PATH.as_posix(),
        abandonment_path=ABANDONMENT_PATH.as_posix(),
        authorization_issuer_implemented=True,
        authorization_issued=False,
        consumption_record_created=False,
        abandonment_record_created=False,
        runtime_execution_performed=False,
        measured_abc_execution_authorized=False,
        budget=ExecutionBudget(),
        controls=RuntimeControls(),
        next_gate=IMPLEMENTATION_NEXT_GATE,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    except OSError as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ATOMIC_WRITE_FAILED",
            "an authorization artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ALREADY_EXISTS",
            "a transient successor authorization artifact already exists",
            path.as_posix(),
        )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.link(temporary_path, path)
    except FileExistsError as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ALREADY_EXISTS",
            "a transient successor authorization artifact appeared during creation",
            path.as_posix(),
        ) from error
    except OSError as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ATOMIC_CREATE_FAILED",
            "a transient successor authorization artifact could not be created",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _terminal_paths() -> tuple[Path, Path]:
    return CONSUMPTION_PATH, ABANDONMENT_PATH


def generate(repo_root: Path) -> ImplementationRecord:
    """Generate deterministic static review and implementation record only."""

    root = repo_root.resolve()
    for path in (AUTHORIZATION_PATH, *_terminal_paths()):
        if (root / path).exists():
            raise SuccessorAuthorizationError(
                "P5_P6_TRANSIENT_AUTHORITY_PRESENT",
                "transient authorization artifacts must be absent during generation",
                path.as_posix(),
            )
    review = _build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    _write_atomic(root / REVIEW_PATH, review_bytes)
    record = _build_record(root, review_bytes)
    _write_atomic(root / RECORD_PATH, record.canonical_json().encode("utf-8"))
    return record


def _validate_static(repo_root: Path) -> ImplementationRecord:
    review = _build_review(repo_root)
    review_bytes = review.canonical_json().encode("utf-8")
    record = _build_record(repo_root, review_bytes)
    expected = (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record.canonical_json().encode("utf-8")),
    )
    for path, payload in expected:
        target = repo_root / path
        if not target.is_file() or target.is_symlink():
            raise SuccessorAuthorizationError(
                "P5_P6_AUTHORIZATION_STATIC_ARTIFACT_UNSAFE",
                "a static authorization artifact is missing or unsafe",
                path.as_posix(),
            )
        if target.read_bytes() != payload:
            raise SuccessorAuthorizationError(
                "P5_P6_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
                "a static authorization artifact differs from fresh generation",
                path.as_posix(),
            )
    return record


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the static issuer without creating live runtime authority."""

    root = repo_root.resolve()
    for path in (AUTHORIZATION_PATH, *_terminal_paths()):
        if (root / path).exists():
            raise SuccessorAuthorizationError(
                "P5_P6_TRANSIENT_AUTHORITY_PRESENT",
                "transient authorization artifacts must be absent during static review",
                path.as_posix(),
            )
    record = _validate_static(root)
    return {
        "status": record.status,
        "source_main_merge_commit": record.source_main_merge_commit,
        "implementation_record_sha256": record.implementation.implementation_record.sha256,
        "notebook_sha256": record.implementation.notebook.sha256,
        "runtime_script_sha256": record.implementation.runtime_script_sha256,
        "wrapper_code_sha256": record.implementation.wrapper_code_sha256,
        "authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "maximum_kaggle_sessions": record.budget.maximum_kaggle_sessions,
        "maximum_saved_versions": record.budget.maximum_saved_versions,
        "maximum_model_loads": record.budget.maximum_model_loads,
        "maximum_worker_starts": record.budget.maximum_worker_starts,
        "maximum_model_requests": record.budget.maximum_model_requests,
        "maximum_benchmark_trajectory_requests": 0,
        "next_gate": record.next_gate,
    }


def _run_git(repo_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_GIT_FAILED",
            "a required Git inspection failed",
            details=tuple(arguments),
        )
    return result.stdout.strip()


def _require_ancestor(repo_root: Path, commit: str) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ANCESTRY_UNREADABLE",
            "authorization source ancestry could not be inspected",
            details=(commit,),
        ) from error
    if result.returncode != 0:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_SOURCE_AUTHORITY_MISSING",
            "the merged successor implementation is not an ancestor of HEAD",
            details=(commit,),
        )


def _allowed_transient_status(allow_transient: bool) -> tuple[str, ...]:
    if not allow_transient:
        return ()
    return tuple(
        f"?? {path.as_posix()}" for path in (AUTHORIZATION_PATH, CONSUMPTION_PATH, ABANDONMENT_PATH)
    )


def _require_synchronized_main(repo_root: Path, *, allow_transient: bool) -> str:
    branch = _run_git(repo_root, ["branch", "--show-current"])
    if branch != "main":
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_MAIN_REQUIRED",
            "authorization lifecycle operations require branch main",
            details=(branch,),
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"])
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"])
    if head != origin_main:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "local main and origin/main are not synchronized",
        )
    status = tuple(
        line
        for line in _run_git(
            repo_root,
            ["status", "--porcelain=v1", "--untracked-files=all"],
        ).splitlines()
        if line
    )
    allowed = set(_allowed_transient_status(allow_transient))
    unexpected = tuple(sorted(line for line in status if line not in allowed))
    if unexpected:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "the repository contains changes outside transient authorization files",
            details=unexpected,
        )
    return head


def _require_transient_paths_untracked(repo_root: Path) -> None:
    tracked = _run_git(
        repo_root,
        [
            "ls-files",
            "--",
            AUTHORIZATION_PATH.as_posix(),
            CONSUMPTION_PATH.as_posix(),
            ABANDONMENT_PATH.as_posix(),
        ],
    )
    if tracked:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_MUST_REMAIN_UNTRACKED",
            "transient authorization lifecycle artifacts must never be tracked",
            details=tuple(tracked.splitlines()),
        )


def _require_source_authority(repo_root: Path) -> None:
    _require_ancestor(repo_root, SOURCE_MAIN_MERGE_COMMIT)


def _load_canonical(path: Path, model: type[LocalABCContract]) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        contract = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_PAYLOAD_INVALID",
            "an authorization lifecycle payload failed strict validation",
            path.as_posix(),
        ) from error
    if observed != contract.canonical_json():
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_PAYLOAD_NOT_CANONICAL",
            "an authorization lifecycle payload is not canonical JSON",
            path.as_posix(),
        )
    return contract


def _load_confirmation(path: Path) -> IssuanceConfirmation:
    loaded = _load_canonical(path, IssuanceConfirmation)
    return cast(IssuanceConfirmation, loaded)


def _build_authorization(
    *,
    repo_root: Path,
    issuer_head: str,
    confirmation: IssuanceConfirmation,
) -> ExecutionAuthorization:
    _validate_static(repo_root)
    if confirmation.confirmed_issuer_merge_commit != issuer_head:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ISSUER_CONFIRMATION_DRIFT",
            "operator confirmation does not bind current merged main",
        )
    issued_at = confirmation.confirmed_at
    return ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=AuthorizationLifecycle.ISSUED,
        scope=AUTHORIZATION_SCOPE,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        issued_from_main_commit=issuer_head,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=confirmation.authorization_window_minutes),
        implementation=_implementation(repo_root),
        capability_observation=confirmation.platform,
        operator_confirmation_recorded=True,
        runtime_execution_authorized=True,
        single_use=True,
        every_terminal_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        measured_abc_execution_authorized=False,
        budget=ExecutionBudget(),
        controls=RuntimeControls(),
    )


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: IssuanceConfirmation,
    now: datetime | None = None,
) -> dict[str, object]:
    """Issue one non-overwriting authority after fresh capability confirmation."""

    root = repo_root.resolve()
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if confirmation.confirmed_at > observed_now + timedelta(minutes=1):
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_CONFIRMATION_IN_FUTURE",
            "the issuance confirmation timestamp is in the future",
        )
    if observed_now - confirmation.confirmed_at > timedelta(
        minutes=MAXIMUM_CONFIRMATION_AGE_MINUTES
    ):
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_CONFIRMATION_STALE",
            "the issuance confirmation is older than 15 minutes",
        )

    issuer_head = _require_synchronized_main(root, allow_transient=False)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    for path in _terminal_paths():
        if (root / path).exists():
            raise SuccessorAuthorizationError(
                "P5_P6_AUTHORIZATION_TERMINAL_RECEIPT_PRESENT",
                "a prior successor authorization terminal receipt already exists",
                path.as_posix(),
            )

    authorization = _build_authorization(
        repo_root=root,
        issuer_head=issuer_head,
        confirmation=confirmation,
    )
    payload = authorization.canonical_json().encode("utf-8")
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "P5_P6_SUCCESSOR_EXECUTION_AUTHORIZATION_V1_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_bytes(payload),
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.implementation.notebook.sha256,
        "runtime_script_sha256": authorization.implementation.runtime_script_sha256,
        "wrapper_code_sha256": authorization.implementation.wrapper_code_sha256,
        "platform_accelerator": PLATFORM_ACCELERATOR,
        "allocated_gpu_count": 2,
        "worker_1_cuda_visible_devices": "0",
        "worker_2_cuda_visible_devices": "1",
        "maximum_saved_versions": 1,
        "maximum_model_requests": 5,
        "authorization_reusable": False,
        "runtime_execution_authorized": True,
        "measured_abc_execution_authorized": False,
        "next_gate": ISSUED_NEXT_GATE,
    }


def _validate_live_authorization(
    repo_root: Path,
    authorization: ExecutionAuthorization,
    issuer_head: str,
) -> None:
    if authorization.issued_from_main_commit != issuer_head:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ISSUER_DRIFT",
            "the live successor authority was not issued from current merged main",
        )
    if authorization.implementation != _implementation(repo_root):
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_IMPLEMENTATION_DRIFT",
            "the live successor implementation binding drifted",
        )
    if authorization.budget != ExecutionBudget():
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_BUDGET_DRIFT",
            "the live successor execution budget drifted",
        )
    if authorization.controls != RuntimeControls():
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_CONTROL_DRIFT",
            "the live successor execution controls drifted",
        )


def _require_no_terminal_receipt(repo_root: Path) -> None:
    present = tuple(path.as_posix() for path in _terminal_paths() if (repo_root / path).exists())
    if present:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_ALREADY_TERMINAL",
            "the successor authorization has a terminal receipt and is not reusable",
            details=present,
        )


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify one live authority immediately before the governed execution."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=True)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    _validate_static(root)
    _require_no_terminal_receipt(root)
    loaded = _load_canonical(root / AUTHORIZATION_PATH, ExecutionAuthorization)
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise SuccessorAuthorizationError(
            "P5_P6_AUTHORIZATION_EXPIRED",
            "the transient successor authorization is outside its validity window",
            AUTHORIZATION_PATH.as_posix(),
        )
    return {
        "status": "P5_P6_SUCCESSOR_EXECUTION_AUTHORIZATION_V1_VALID",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": authorization.fingerprint(),
        "issuer_head_commit": issuer_head,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "notebook_sha256": authorization.implementation.notebook.sha256,
        "runtime_script_sha256": authorization.implementation.runtime_script_sha256,
        "wrapper_code_sha256": authorization.implementation.wrapper_code_sha256,
        "single_use": True,
        "consumed": False,
        "abandoned": False,
        "maximum_saved_versions": 1,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_model_requests": 5,
        "maximum_benchmark_trajectory_requests": 0,
        "runtime_execution_authorized": True,
        "measured_abc_execution_authorized": False,
        "next_gate": ISSUED_NEXT_GATE,
    }


def consume_authorization(
    *,
    repo_root: Path,
    outcome: ExecutionOutcome,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None = None,
    terminal_log_sha256: str | None = None,
    consumed_at: datetime | None = None,
) -> dict[str, object]:
    """Consume the authority after any governed terminal execution attempt."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=True)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    _validate_static(root)
    _require_no_terminal_receipt(root)
    loaded = _load_canonical(root / AUTHORIZATION_PATH, ExecutionAuthorization)
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = AuthorizationConsumption(
        consumption_id=("auragateway-p5-p6-successor-execution-authorization-consumption-v1"),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=_sha256_bytes(authorization_payload),
        lifecycle=AuthorizationLifecycle.CONSUMED,
        consumed_at=consumed_at or datetime.now(UTC),
        outcome=outcome,
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
        authorization_reusable=False,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=CONSUMED_NEXT_GATE,
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / CONSUMPTION_PATH, payload)
    return {
        "status": "P5_P6_SUCCESSOR_EXECUTION_AUTHORIZATION_V1_CONSUMED",
        "authorization_sha256": receipt.authorization_sha256,
        "consumption_path": CONSUMPTION_PATH.as_posix(),
        "consumption_sha256": _sha256_bytes(payload),
        "outcome": receipt.outcome.value,
        "saved_version_id": receipt.saved_version_id,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": receipt.next_gate,
    }


def abandon_authorization(
    *,
    repo_root: Path,
    reason: AbandonmentReason,
    abandoned_at: datetime | None = None,
) -> dict[str, object]:
    """Terminalize an issued but unused authority without execution."""

    root = repo_root.resolve()
    issuer_head = _require_synchronized_main(root, allow_transient=True)
    _require_transient_paths_untracked(root)
    _require_source_authority(root)
    _validate_static(root)
    _require_no_terminal_receipt(root)
    loaded = _load_canonical(root / AUTHORIZATION_PATH, ExecutionAuthorization)
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = AuthorizationAbandonment(
        abandonment_id=("auragateway-p5-p6-successor-execution-authorization-abandonment-v1"),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=_sha256_bytes(authorization_payload),
        lifecycle=AuthorizationLifecycle.ABANDONED,
        abandoned_at=abandoned_at or datetime.now(UTC),
        reason=reason,
        execution_attempted=False,
        authorization_reusable=False,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=ABANDONED_NEXT_GATE,
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / ABANDONMENT_PATH, payload)
    return {
        "status": "ABANDONED_BEFORE_EXECUTION",
        "authorization_sha256": receipt.authorization_sha256,
        "abandonment_path": ABANDONMENT_PATH.as_posix(),
        "abandonment_sha256": _sha256_bytes(payload),
        "reason": receipt.reason.value,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": receipt.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p5-p6-successor-authorization-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)

    issue = subparsers.add_parser("issue")
    issue.add_argument("--repo-root", type=Path, required=True)
    issue.add_argument("--confirmation-json", type=Path, required=True)

    consume = subparsers.add_parser("consume")
    consume.add_argument("--repo-root", type=Path, required=True)
    consume.add_argument(
        "--outcome",
        choices=tuple(outcome.value for outcome in ExecutionOutcome),
        required=True,
    )
    consume.add_argument("--saved-version-id", type=int)
    consume.add_argument("--evidence-zip-sha256")
    consume.add_argument("--terminal-log-sha256")

    abandon = subparsers.add_parser("abandon")
    abandon.add_argument("--repo-root", type=Path, required=True)
    abandon.add_argument(
        "--reason",
        choices=tuple(reason.value for reason in AbandonmentReason),
        required=True,
    )
    return parser


def _error_json(error: SuccessorAuthorizationError) -> str:
    return ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Run one repository authorization lifecycle command."""

    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        command = cast(str, arguments.command)
        repo_root = cast(Path, arguments.repo_root)
        if command == "generate":
            record = generate(repo_root)
            result: dict[str, object] = {
                "command": "generate",
                "status": record.status,
                "authorization_issued": False,
                "runtime_execution_performed": False,
            }
        elif command == "validate-implementation":
            result = validate_implementation(repo_root)
        elif command == "issue":
            confirmation = _load_confirmation(cast(Path, arguments.confirmation_json))
            result = issue_authorization(
                repo_root=repo_root,
                confirmation=confirmation,
            )
        elif command == "verify":
            result = verify_authorization(repo_root=repo_root)
        elif command == "consume":
            result = consume_authorization(
                repo_root=repo_root,
                outcome=ExecutionOutcome(cast(str, arguments.outcome)),
                saved_version_id=cast(int | None, arguments.saved_version_id),
                evidence_zip_sha256=cast(str | None, arguments.evidence_zip_sha256),
                terminal_log_sha256=cast(str | None, arguments.terminal_log_sha256),
            )
        elif command == "abandon":
            result = abandon_authorization(
                repo_root=repo_root,
                reason=AbandonmentReason(cast(str, arguments.reason)),
            )
        else:
            raise SuccessorAuthorizationError(
                "P5_P6_AUTHORIZATION_COMMAND_INVALID",
                "P5/P6 successor authorization command is invalid",
            )
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0
    except SuccessorAuthorizationError as error:
        print(_error_json(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
