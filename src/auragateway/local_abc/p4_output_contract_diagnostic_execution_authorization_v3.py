"""Implement, issue, verify, and consume one P4 V2 execution authority."""

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

IMPLEMENTATION_FEATURE_COMMIT: Final = "99bf5a4afff8ee1ee8ddecc1aff689173cb38bab"
IMPLEMENTATION_MERGE_COMMIT: Final = "d61a146a2503a5e6bfd3fadbf1dad65dcad402ac"
IMPLEMENTATION_SOURCE_MAIN_COMMIT: Final = "d76c47d12366ad9500ccec18dd3aebf9b23f7b66"
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
SELECTED_BACKEND: Final = "TRITON_ATTN"
PLATFORM_ACCELERATOR: Final = "GPU_T4_X2"
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_output_contract_diagnostic_execution_authorization_v3.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_output_contract_diagnostic_execution_authorization_v3.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-07-local-abc-p4-output-contract-diagnostic-execution-authorization-v3.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_Execution_Authorization_V3.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_output_contract_diagnostic_execution_authorization_v3.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_"
    "execution_authorization_v3_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_"
    "execution_authorization_v3_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_authorization_v3.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_"
    "execution_authorization_consumption_v3.json"
)

V2_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v2_record.json"
)
V2_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v2_review.json"
)
V2_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_v2_request.json"
)
V2_DIAGNOSIS_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_native_runtime_diagnosis_v1.json"
)
V2_SOURCE_PATH: Final = Path("src/auragateway/local_abc/p4_output_contract_diagnostic_v2.py")
V2_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"
)
V2_TEST_PATH: Final = Path("tests/unit/local_abc/test_p4_output_contract_diagnostic_v2.py")
V2_NOTEBOOK_PATH: Final = Path("notebooks/auragateway_p4_output_contract_diagnostic_v2.ipynb")
V2_REPORT_PATH: Final = Path("docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_V2.md")
V2_RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_p4_output_contract_diagnostic_v2.md")
INSPECTION_ZIP_PATH: Final = Path(
    "evidence_vault/local_abc/p4-import-differential-inspection-v1/"
    "ag-p4-import-differential-inspection-v1-340657269.zip"
)
INSPECTION_LOG_PATH: Final = Path(
    "evidence_vault/local_abc/p4-import-differential-inspection-v1/"
    "ag-p4-import-differential-inspection-v1-340657269.log"
)
INSPECTION_HUMAN_PATH: Final = Path(
    "evidence_vault/local_abc/p4-import-differential-inspection-v1/human_report_v1-340657269.md"
)
PRIOR_AUTHORIZATION_PATH: Final = Path(
    "evidence_vault/local_abc/p4-output-contract-diagnostic-failure-v1/"
    "execution_authorization_v2-340622392.json"
)
PRIOR_CONSUMPTION_PATH: Final = Path(
    "evidence_vault/local_abc/p4-output-contract-diagnostic-failure-v1/"
    "execution_authorization_consumption_v2-340622392.json"
)
PRIOR_ABANDONMENT_PATH: Final = Path(
    "evidence_vault/local_abc/p4-output-contract-diagnostic-failure-v1/"
    "execution_authorization_abandonment_v1-340622392.json"
)

AUTHORIZATION_ID: Final = "auragateway-p4-output-contract-diagnostic-execution-authorization-v3"
AUTHORIZATION_SCOPE: Final = "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2"
IMPLEMENTATION_NEXT_GATE: Final = (
    "merge_then_observe_kaggle_and_issue_p4_output_contract_execution_authorization_v3"
)
ISSUED_NEXT_GATE: Final = "execute_governed_p4_output_contract_diagnostic_v2_once"
CONSUMED_NEXT_GATE: Final = "preserve_intake_and_classify_p4_output_contract_diagnostic_v2"

EXPECTED_RUNTIME_OUTPUTS: Final = (
    "runtime_source_identity_report_v2.json",
    "model_snapshot_report_v2.json",
    "wheelhouse_report_v2.json",
    "runtime_install_report_v2.json",
    "runtime_import_closure_report_v2.json",
    "runtime_native_origin_report_v2.json",
    "worker_startup_report_v2.json",
    "request_results_v2.json",
    "case_metrics_v2.json",
    "selection_report_v2.json",
    "worker_teardown_report_v2.json",
    "scratch_cleanup_report_v2.json",
    "p4_output_contract_diagnostic_summary_v2.json",
    "failure_report_v2.json",
    "bundle_manifest_v2.json",
    "human_report_v2.md",
    "ag-p4-output-contract-evidence-v2.zip",
)

REQUEST_ORDER: Final = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "F",
    "E",
    "D",
    "C",
    "B",
    "A",
    "C",
    "D",
    "E",
    "F",
    "A",
    "B",
)

EXPECTED_ARTIFACTS: Final = {
    V2_RECORD_PATH: (
        "9fbefc001af0a56995f903681c6afe251a2ce594fd21d760a26ee7783352f5c1",
        4804,
        True,
    ),
    V2_REVIEW_PATH: (
        "2c3fa955e06256445a9c9175b6b940aaa2112c62b6ce0eaf47621cd0443e0d3b",
        1749,
        True,
    ),
    V2_REQUEST_PATH: (
        "b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1",
        3575,
        True,
    ),
    V2_DIAGNOSIS_PATH: (
        "60ebee432791f1417fd9707b4313b99a04286df18546055db4516ebd7b607b54",
        1957,
        True,
    ),
    V2_SOURCE_PATH: (
        "d074f4a4b3c17d6a9f0dadaff9b088b8ee78861fc55ceaf7aded9c8aa08d5ec5",
        15725,
        True,
    ),
    V2_TEMPLATE_PATH: (
        "93bdcf4a2ab3f4b4a07b688b8d6f9dc295ba3edcbb0b9bd63da8967393811441",
        47691,
        True,
    ),
    V2_TEST_PATH: (
        "71593846e435d48b7f3951d4644cc374f6204990d194d99769f5383c590bebfe",
        6664,
        True,
    ),
    V2_NOTEBOOK_PATH: (
        "5efc4660dcfca451947189001fdf2c6efc86d2201faa91b9b145ef3219bca581",
        73522,
        False,
    ),
    V2_REPORT_PATH: (
        "6e1f2f268dd43a7fca9bb04ae0d0f7a95fe52ec56aa950a2cf49d3fd00c17048",
        1491,
        True,
    ),
    V2_RUNBOOK_PATH: (
        "3c4c6847496f8660450515dd93d97a605349955aee3512935adc91b193bbbb94",
        1171,
        True,
    ),
    INSPECTION_ZIP_PATH: (
        "ea54b6ec59bd3a73be20fec04aa56ca9f3f4af58f8499ec2962a66f152180849",
        14744,
        False,
    ),
    INSPECTION_LOG_PATH: (
        "978496a10348b184f70223282ce401fd3067eb9bac5579eb2cc95eb025bca9d2",
        3495,
        False,
    ),
    INSPECTION_HUMAN_PATH: (
        "fc1896cee00699f0581cf056afa01cf9f2ee3df10498af13beb10deb3ff6ecc8",
        912,
        True,
    ),
    PRIOR_AUTHORIZATION_PATH: (
        "200a2a53a250dc267db01c3cf3cced8a91c0eafd598f1253f3634ba8f181d62b",
        6507,
        True,
    ),
    PRIOR_CONSUMPTION_PATH: (
        "3e349c1b003c67f07d041bbb96df8f19a5af7d7afd769f928d1da2509cbaa816",
        514,
        True,
    ),
    PRIOR_ABANDONMENT_PATH: (
        "8a8543da1ffdfad1020f835e5923a1e46080f505569f8642b361abb5ecc8c393",
        888,
        True,
    ),
}

CONTROL_HASHES: Final = {
    "requirements.in": ("a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"),
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


class AuthorizationLifecycle(StrEnum):
    """Lifecycle states for one transient V3 authority."""

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"


class ExecutionOutcome(StrEnum):
    """Terminal outcomes that consume the single-use authority."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    TIMED_OUT = "TIMED_OUT"
    KAGGLE_PLATFORM_TERMINATED = "KAGGLE_PLATFORM_TERMINATED"


class AuthorizationError(RuntimeError):
    """Metadata-safe authorization-boundary failure."""

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
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ARGUMENT_INVALID",
            "P4 authorization V3 arguments are invalid",
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


class ExecutionBudget(LocalABCContract):
    """Non-expandable execution budget."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_saved_versions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[1] = 1
    maximum_worker_starts: Literal[1] = 1
    maximum_model_requests: Literal[18] = 18
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class PlatformControls(LocalABCContract):
    """Kaggle allocation and one-worker GPU isolation."""

    platform_accelerator: Literal["GPU_T4_X2"] = "GPU_T4_X2"
    allocated_gpu_count: Literal[2] = 2
    worker_cuda_visible_devices: Literal["0"] = "0"
    worker_visible_gpu_count: Literal[1] = 1
    worker_gpu_index: Literal[0] = 0
    unused_allocated_gpu_indices: tuple[Literal[1], ...] = (1,)
    gpu1_model_worker_permitted: Literal[False] = False
    internet_enabled: Literal[False] = False
    wheelhouse_attachment_count: Literal[1] = 1
    model_snapshot_attachment_count: Literal[1] = 1


class RuntimeHardeningAuthority(LocalABCContract):
    """Merged V2 native-runtime and privacy controls."""

    bounded_stream_capture_bytes: Literal[131072] = 131072
    cuda_stub_paths_prohibited: Literal[True] = True
    fail_fast_worker_exit_required: Literal[True] = True
    native_origin_closure_required: Literal[True] = True
    real_driver_directory: Literal["/usr/local/nvidia/lib64"] = "/usr/local/nvidia/lib64"
    request_logging_disabled: Literal[True] = True
    required_target_native_tokens: tuple[Literal["libcusparse"], Literal["libnvJitLink"]] = (
        "libcusparse",
        "libnvJitLink",
    )
    same_environment_for_import_and_worker: Literal[True] = True
    shared_environment_helper_required: Literal[True] = True
    target_nvidia_libraries_precede_ambient: Literal[True] = True


class PriorAuthorizationLineage(LocalABCContract):
    """Terminalized predecessor authority and non-replay proof."""

    v1_abandonment: ArtifactReceipt
    v2_authorization: ArtifactReceipt
    v2_consumption: ArtifactReceipt
    v2_saved_version_id: Literal[340622392] = 340622392
    v2_outcome: Literal["FAILED"] = "FAILED"
    v2_authorization_reusable: Literal[False] = False


class ImplementationAuthority(LocalABCContract):
    """Exact merged P4 V2 implementation authority."""

    implementation_feature_commit: Literal["99bf5a4afff8ee1ee8ddecc1aff689173cb38bab"]
    implementation_merge_commit: Literal["d61a146a2503a5e6bfd3fadbf1dad65dcad402ac"]
    implementation_source_main_commit: Literal["d76c47d12366ad9500ccec18dd3aebf9b23f7b66"]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    implementation_record: ArtifactReceipt
    architecture_review: ArtifactReceipt
    request: ArtifactReceipt
    diagnosis: ArtifactReceipt
    source: ArtifactReceipt
    template: ArtifactReceipt
    tests: ArtifactReceipt
    notebook: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    inspection_evidence: ArtifactReceipt
    inspection_log: ArtifactReceipt
    inspection_human_report: ArtifactReceipt
    prior_authorization_lineage: PriorAuthorizationLineage
    notebook_name: Literal["ag-p4-output-contract-diagnostic-v2"]
    failed_notebook_name: Literal["ag-p4-output-contract-diag-failed-v2"]
    runtime_script_sha256: Literal[
        "bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"
    ]
    wrapper_code_sha256: Literal["09e37eca21069c8ef5822711854307541ccfd7b158f2ccd902f58bba5fbd3402"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    selected_backend: Literal["TRITON_ATTN"]
    request_order: tuple[str, ...]
    expected_runtime_outputs: tuple[str, ...]
    wheelhouse: WheelhouseAuthority
    execution_budget: ExecutionBudget
    platform: PlatformControls
    runtime_hardening: RuntimeHardeningAuthority
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    raw_worker_logs_in_evidence_permitted: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> Self:
        if self.request_order != REQUEST_ORDER:
            raise ValueError("request order drifted")
        if self.expected_runtime_outputs != EXPECTED_RUNTIME_OUTPUTS:
            raise ValueError("runtime output contract drifted")
        return self


class ArchitectureReview(LocalABCContract):
    """Deterministic decision record for V3 authorization implementation."""

    schema_version: Literal["3.0.0"] = "3.0.0"
    review_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v3-review"
    ]
    status: Literal["APPROVED_FOR_AUTHORIZATION_V3_IMPLEMENTATION"]
    decision: Literal["AUTHORIZE_EXACT_MERGED_P4_V2_ON_T4_X2_WITH_ONE_GPU0_WORKER"]
    implementation: ImplementationAuthority
    operator_confirmation_required: Literal[True]
    live_platform_observation_required: Literal[True]
    single_use_required: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    runtime_execution_authorized_in_review: Literal[False]
    next_gate: Literal[
        "merge_then_observe_kaggle_and_issue_p4_output_contract_execution_authorization_v3"
    ]
    non_claims: tuple[str, ...] = Field(min_length=10)


class ImplementationRecord(LocalABCContract):
    """Deterministic record for the static V3 issuer."""

    schema_version: Literal["3.0.0"] = "3.0.0"
    record_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v3-record"
    ]
    status: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V3_VALID"]
    implementation: ImplementationAuthority
    review: ArtifactReceipt
    source: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    authorization_path: str
    consumption_path: str
    authorization_issuer_implemented: Literal[True]
    authorization_issued: Literal[False]
    runtime_execution_performed: Literal[False]
    next_gate: Literal[
        "merge_then_observe_kaggle_and_issue_p4_output_contract_execution_authorization_v3"
    ]


class PlatformCapabilityConfirmation(LocalABCContract):
    """Current Kaggle settings observed immediately before issuance."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    observed_at: datetime
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    observed_platform_accelerator: Literal["GPU_T4_X2"]
    observed_allocated_gpu_count: Literal[2]
    observed_internet_enabled: Literal[False]
    observed_wheelhouse_attachment_count: Literal[1]
    observed_model_snapshot_attachment_count: Literal[1]
    confirmed_worker_cuda_visible_devices: Literal["0"]
    confirmed_worker_visible_gpu_count: Literal[1]
    confirmed_worker_gpu_index: Literal[0]

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(UTC).replace(microsecond=0)


class IssuanceConfirmation(LocalABCContract):
    """Explicit operator confirmation of exact V2 bytes and budget."""

    schema_version: Literal["3.0.0"] = "3.0.0"
    operator_confirmed: Literal[True]
    confirmed_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    confirmed_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2"]
    confirmed_implementation_merge_commit: Literal["d61a146a2503a5e6bfd3fadbf1dad65dcad402ac"]
    confirmed_notebook_sha256: Literal[
        "5efc4660dcfca451947189001fdf2c6efc86d2201faa91b9b145ef3219bca581"
    ]
    confirmed_runtime_script_sha256: Literal[
        "bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"
    ]
    confirmed_wrapper_code_sha256: Literal[
        "09e37eca21069c8ef5822711854307541ccfd7b158f2ccd902f58bba5fbd3402"
    ]
    confirmed_request_sha256: Literal[
        "b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1"
    ]
    confirmed_implementation_record_sha256: Literal[
        "9fbefc001af0a56995f903681c6afe251a2ce594fd21d760a26ee7783352f5c1"
    ]
    confirmed_model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    confirmed_backend: Literal["TRITON_ATTN"]
    confirmed_model_request_budget: Literal[18]
    confirmed_runtime_output_count: Literal[17]
    confirmed_notebook_unmodified: Literal[True]
    confirmed_single_saved_version: Literal[True]
    confirmed_no_hidden_retries: Literal[True]
    confirmed_consumption_required: Literal[True]
    platform: PlatformCapabilityConfirmation

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
        if self.confirmed_at - self.platform.observed_at > timedelta(minutes=15):
            raise ValueError("platform observation is older than 15 minutes")
        return self


class ExecutionAuthorization(LocalABCContract):
    """Transient, single-use live execution authority."""

    schema_version: Literal["3.0.0"] = "3.0.0"
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v3"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal[AuthorizationLifecycle.ISSUED]
    scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2"]
    issued_from_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issued_at: datetime
    expires_at: datetime
    implementation: ImplementationAuthority
    capability_observation: PlatformCapabilityConfirmation
    operator_confirmation_recorded: Literal[True]
    runtime_execution_authorized: Literal[True]
    single_use: Literal[True]
    every_terminal_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]

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
    """Non-overwriting terminal receipt after one execution attempt."""

    schema_version: Literal["3.0.0"] = "3.0.0"
    consumption_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v3"
    ]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v3"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal[AuthorizationLifecycle.CONSUMED]
    consumed_at: datetime
    outcome: ExecutionOutcome
    saved_version_id: int = Field(gt=0)
    evidence_zip_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    terminal_log_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_intake_and_classify_p4_output_contract_diagnostic_v2"]

    @field_validator("consumed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must be timezone-aware")
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
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ARTIFACT_UNSAFE",
            "a required authorization V3 artifact is missing or unsafe",
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
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_IMPLEMENTATION_IDENTITY_DRIFT",
            "a merged P4 V2 artifact identity drifted",
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
    except (OSError, json.JSONDecodeError) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_JSON_INVALID",
            "a required implementation authority is not valid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_JSON_INVALID",
            "a required implementation authority is not a JSON object",
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
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_SEMANTIC_DRIFT",
            "a merged P4 V2 semantic authority drifted",
            path.as_posix(),
            (f"field={key}",),
        )


def _validate_v2_semantics(repo_root: Path) -> None:
    record = _read_json_object(repo_root, V2_RECORD_PATH)
    _require_value(record, "status", "IMPLEMENTED_NOT_EXECUTED", V2_RECORD_PATH)
    _require_value(record, "authorization_issuer_included", False, V2_RECORD_PATH)
    _require_value(record, "source_main_commit", IMPLEMENTATION_SOURCE_MAIN_COMMIT, V2_RECORD_PATH)
    _require_value(
        record,
        "expected_runtime_outputs",
        list(EXPECTED_RUNTIME_OUTPUTS),
        V2_RECORD_PATH,
    )

    safety = record.get("safety")
    if not isinstance(safety, dict):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_SEMANTIC_DRIFT",
            "the merged V2 safety contract is missing",
            V2_RECORD_PATH.as_posix(),
        )
    for key, expected in {
        "runtime_execution_authorized": False,
        "kaggle_execution_performed": False,
        "model_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
        "network_requests_performed": 0,
    }.items():
        if safety.get(key) != expected:
            raise AuthorizationError(
                "P4_AUTHORIZATION_V3_SEMANTIC_DRIFT",
                "the merged V2 safety contract drifted",
                V2_RECORD_PATH.as_posix(),
                (f"field=safety.{key}",),
            )

    request = _read_json_object(repo_root, V2_REQUEST_PATH)
    _require_value(request, "runtime_execution_authorized", False, V2_REQUEST_PATH)
    _require_value(request, "measured_abc_execution_authorized", False, V2_REQUEST_PATH)
    _require_value(request, "selected_backend", SELECTED_BACKEND, V2_REQUEST_PATH)
    _require_value(request, "model_repository", MODEL_REPOSITORY, V2_REQUEST_PATH)
    _require_value(request, "model_revision", MODEL_REVISION, V2_REQUEST_PATH)
    _require_value(request, "model_snapshot_sha256", MODEL_SNAPSHOT_SHA256, V2_REQUEST_PATH)
    _require_value(request, "request_order", list(REQUEST_ORDER), V2_REQUEST_PATH)

    budget = request.get("execution_budget")
    if not isinstance(budget, dict):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_SEMANTIC_DRIFT",
            "the merged V2 execution budget is missing",
            V2_REQUEST_PATH.as_posix(),
        )
    expected_budget = {
        "maximum_kaggle_sessions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 1,
        "maximum_worker_starts": 1,
        "maximum_model_requests": 18,
        "maximum_output_tokens_per_request": 32,
        "hidden_retries_permitted": 0,
        "external_network_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
    }
    for key, expected in expected_budget.items():
        if budget.get(key) != expected:
            raise AuthorizationError(
                "P4_AUTHORIZATION_V3_SEMANTIC_DRIFT",
                "the merged V2 execution budget drifted",
                V2_REQUEST_PATH.as_posix(),
                (f"field=execution_budget.{key}",),
            )

    review = _read_json_object(repo_root, V2_REVIEW_PATH)
    _require_value(review, "runtime_execution_authorized", False, V2_REVIEW_PATH)
    _require_value(
        review,
        "selected_intervention",
        "VERSIONED_NATIVE_RUNTIME_HARDENING_WITH_UNCHANGED_A_F_MATRIX",
        V2_REVIEW_PATH,
    )

    diagnosis = _read_json_object(repo_root, V2_DIAGNOSIS_PATH)
    _require_value(
        diagnosis,
        "primary_classification",
        "NATIVE_LIBRARY_SEARCH_PATH_SUPPORTED",
        V2_DIAGNOSIS_PATH,
    )
    _require_value(diagnosis, "solution_execution_authorized", False, V2_DIAGNOSIS_PATH)

    prior_consumption = _read_json_object(repo_root, PRIOR_CONSUMPTION_PATH)
    _require_value(prior_consumption, "lifecycle", "CONSUMED", PRIOR_CONSUMPTION_PATH)
    _require_value(prior_consumption, "outcome", "FAILED", PRIOR_CONSUMPTION_PATH)
    _require_value(prior_consumption, "saved_version_id", 340622392, PRIOR_CONSUMPTION_PATH)
    _require_value(prior_consumption, "authorization_reusable", False, PRIOR_CONSUMPTION_PATH)

    prior_abandonment = _read_json_object(repo_root, PRIOR_ABANDONMENT_PATH)
    _require_value(
        prior_abandonment,
        "status",
        "ABANDONED_BEFORE_EXECUTION",
        PRIOR_ABANDONMENT_PATH,
    )
    _require_value(prior_abandonment, "authorization_reusable", False, PRIOR_ABANDONMENT_PATH)

    template = (repo_root / V2_TEMPLATE_PATH).read_text(encoding="utf-8")
    markers = (
        'environment["CUDA_VISIBLE_DEVICES"] = str(gpu_index)',
        '"gpu_index": 0,',
        '"--attention-backend",',
        '"TRITON_ATTN"',
        '"--no-enable-log-requests",',
        "if not isinstance(entries, list) or len(entries) != 182:",
        "if wheel_count != 176:",
    )
    missing_markers = tuple(marker for marker in markers if marker not in template)
    missing_hashes = tuple(value for value in CONTROL_HASHES.values() if value not in template)
    if missing_markers or missing_hashes:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_RUNTIME_CONTRACT_DRIFT",
            "the merged V2 executable runtime contract drifted",
            V2_TEMPLATE_PATH.as_posix(),
            missing_markers + missing_hashes,
        )


def _implementation(repo_root: Path) -> ImplementationAuthority:
    for path in EXPECTED_ARTIFACTS:
        _expected_artifact(repo_root, path)
    _validate_v2_semantics(repo_root)

    return ImplementationAuthority(
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        implementation_source_main_commit=IMPLEMENTATION_SOURCE_MAIN_COMMIT,
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        implementation_record=_expected_artifact(repo_root, V2_RECORD_PATH),
        architecture_review=_expected_artifact(repo_root, V2_REVIEW_PATH),
        request=_expected_artifact(repo_root, V2_REQUEST_PATH),
        diagnosis=_expected_artifact(repo_root, V2_DIAGNOSIS_PATH),
        source=_expected_artifact(repo_root, V2_SOURCE_PATH),
        template=_expected_artifact(repo_root, V2_TEMPLATE_PATH),
        tests=_expected_artifact(repo_root, V2_TEST_PATH),
        notebook=_expected_artifact(repo_root, V2_NOTEBOOK_PATH),
        report=_expected_artifact(repo_root, V2_REPORT_PATH),
        runbook=_expected_artifact(repo_root, V2_RUNBOOK_PATH),
        inspection_evidence=_expected_artifact(repo_root, INSPECTION_ZIP_PATH),
        inspection_log=_expected_artifact(repo_root, INSPECTION_LOG_PATH),
        inspection_human_report=_expected_artifact(repo_root, INSPECTION_HUMAN_PATH),
        prior_authorization_lineage=PriorAuthorizationLineage(
            v1_abandonment=_expected_artifact(repo_root, PRIOR_ABANDONMENT_PATH),
            v2_authorization=_expected_artifact(repo_root, PRIOR_AUTHORIZATION_PATH),
            v2_consumption=_expected_artifact(repo_root, PRIOR_CONSUMPTION_PATH),
            v2_saved_version_id=340622392,
            v2_outcome="FAILED",
            v2_authorization_reusable=False,
        ),
        notebook_name="ag-p4-output-contract-diagnostic-v2",
        failed_notebook_name="ag-p4-output-contract-diag-failed-v2",
        runtime_script_sha256=("bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"),
        wrapper_code_sha256=("09e37eca21069c8ef5822711854307541ccfd7b158f2ccd902f58bba5fbd3402"),
        model_repository=MODEL_REPOSITORY,
        model_revision=MODEL_REVISION,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        selected_backend=SELECTED_BACKEND,
        request_order=REQUEST_ORDER,
        expected_runtime_outputs=EXPECTED_RUNTIME_OUTPUTS,
        wheelhouse=WheelhouseAuthority(control_hashes=dict(CONTROL_HASHES)),
        execution_budget=ExecutionBudget(),
        platform=PlatformControls(),
        runtime_hardening=RuntimeHardeningAuthority(),
        raw_prompt_logging_permitted=False,
        raw_output_logging_permitted=False,
        raw_worker_logs_in_evidence_permitted=False,
        measured_abc_execution_authorized=False,
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "Authorization implementation does not issue live runtime authority.",
        "P4 V2 has not been executed.",
        "Worker startup under P4 V2 has not been observed.",
        "Triton kernel compilation under P4 V2 has not been observed.",
        "The A-F request matrix has not been executed under P4 V2.",
        "JSON-schema compatibility is not established.",
        "No A-F case is selected.",
        "Measured A/B/C execution is not authorized.",
        "A T4 x2 allocation does not authorize two-GPU execution.",
        "GPU 1 is not authorized for a model worker.",
        "A passed import closure does not prove worker readiness.",
        "A passed worker startup does not prove output-contract success.",
        "Deployment readiness is not established.",
        "Production readiness is not established.",
    )


def _build_review(repo_root: Path) -> ArchitectureReview:
    return ArchitectureReview(
        review_id=("auragateway-p4-output-contract-diagnostic-execution-authorization-v3-review"),
        status="APPROVED_FOR_AUTHORIZATION_V3_IMPLEMENTATION",
        decision="AUTHORIZE_EXACT_MERGED_P4_V2_ON_T4_X2_WITH_ONE_GPU0_WORKER",
        implementation=_implementation(repo_root),
        operator_confirmation_required=True,
        live_platform_observation_required=True,
        single_use_required=True,
        every_terminal_attempt_consumes_authorization=True,
        runtime_execution_authorized_in_review=False,
        next_gate=IMPLEMENTATION_NEXT_GATE,
        non_claims=_non_claims(),
    )


def _build_record(repo_root: Path, review_bytes: bytes) -> ImplementationRecord:
    return ImplementationRecord(
        record_id=("auragateway-p4-output-contract-diagnostic-execution-authorization-v3-record"),
        status="P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V3_VALID",
        implementation=_implementation(repo_root),
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        source=_artifact(repo_root, SOURCE_PATH),
        tests=_artifact(repo_root, TEST_PATH),
        adr=_artifact(repo_root, ADR_PATH),
        report=_artifact(repo_root, REPORT_PATH),
        runbook=_artifact(repo_root, RUNBOOK_PATH),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        consumption_path=CONSUMPTION_PATH.as_posix(),
        authorization_issuer_implemented=True,
        authorization_issued=False,
        runtime_execution_performed=False,
        next_gate=IMPLEMENTATION_NEXT_GATE,
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
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
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ATOMIC_WRITE_FAILED",
            "an authorization V3 artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_non_overwriting(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ALREADY_EXISTS",
            "a transient authorization V3 artifact already exists",
            path.as_posix(),
        )
    temporary: Path | None = None
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
            temporary = Path(handle.name)
        os.link(temporary, path)
    except FileExistsError as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ALREADY_EXISTS",
            "a transient authorization V3 artifact appeared during creation",
            path.as_posix(),
        ) from error
    except OSError as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ATOMIC_CREATE_FAILED",
            "a transient authorization V3 artifact could not be created",
            path.as_posix(),
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _transient_paths() -> tuple[Path, ...]:
    return (AUTHORIZATION_PATH, CONSUMPTION_PATH)


def generate(repo_root: Path) -> ImplementationRecord:
    """Generate deterministic V3 review and implementation record."""

    root = repo_root.resolve()
    existing = tuple(path.as_posix() for path in _transient_paths() if (root / path).exists())
    if existing:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_TRANSIENT_PRESENT",
            "transient lifecycle artifacts must be absent during generation",
            details=existing,
        )
    review = _build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    _atomic_write(root / REVIEW_PATH, review_bytes)
    record = _build_record(root, review_bytes)
    _atomic_write(root / RECORD_PATH, record.canonical_json().encode("utf-8"))
    return record


def _validate_static(repo_root: Path) -> ImplementationRecord:
    review = _build_review(repo_root)
    review_bytes = review.canonical_json().encode("utf-8")
    record = _build_record(repo_root, review_bytes)
    expected = (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record.canonical_json().encode("utf-8")),
    )
    for relative_path, payload in expected:
        path = repo_root / relative_path
        if not path.is_file() or path.is_symlink():
            raise AuthorizationError(
                "P4_AUTHORIZATION_V3_STATIC_ARTIFACT_UNSAFE",
                "a static authorization V3 artifact is missing or unsafe",
                relative_path.as_posix(),
            )
        if path.read_bytes() != payload:
            raise AuthorizationError(
                "P4_AUTHORIZATION_V3_STATIC_ARTIFACT_DRIFT",
                "a static authorization V3 artifact differs from generation",
                relative_path.as_posix(),
            )
    return record


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the static V3 issuer without creating live authority."""

    record = _validate_static(repo_root.resolve())
    return {
        "status": record.status,
        "implementation_feature_commit": IMPLEMENTATION_FEATURE_COMMIT,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "notebook_sha256": record.implementation.notebook.sha256,
        "runtime_script_sha256": record.implementation.runtime_script_sha256,
        "wrapper_code_sha256": record.implementation.wrapper_code_sha256,
        "platform_accelerator": record.implementation.platform.platform_accelerator,
        "maximum_saved_versions": 1,
        "maximum_model_requests": 18,
        "authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_authorized": False,
        "next_gate": record.next_gate,
    }


def _run_git(repo_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_GIT_FAILED",
            "a required Git inspection failed",
            details=tuple(arguments),
        )
    return result.stdout.strip()


def _require_ancestor(repo_root: Path, commit: str) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                commit,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ANCESTRY_UNREADABLE",
            "implementation ancestry could not be inspected",
            details=(commit,),
        ) from error
    if result.returncode != 0:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_IMPLEMENTATION_AUTHORITY_MISSING",
            "the merged P4 V2 commit is not an ancestor of HEAD",
            details=(commit,),
        )


def _require_transient_untracked(repo_root: Path) -> None:
    tracked = _run_git(
        repo_root,
        ["ls-files", "--", *(path.as_posix() for path in _transient_paths())],
    )
    if tracked:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_TRANSIENT_TRACKED",
            "authorization lifecycle artifacts must remain untracked",
            details=tuple(tracked.splitlines()),
        )


def _require_main(
    repo_root: Path,
    allowed_transient_paths: tuple[Path, ...],
) -> str:
    branch = _run_git(repo_root, ["branch", "--show-current"])
    if branch != "main":
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_MAIN_REQUIRED",
            "authorization V3 lifecycle operations require main",
            details=(branch,),
        )
    head = _run_git(repo_root, ["rev-parse", "HEAD"])
    origin_main = _run_git(repo_root, ["rev-parse", "origin/main"])
    if head != origin_main:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_MAIN_NOT_SYNCHRONIZED",
            "local main and origin/main are not synchronized",
        )
    _require_transient_untracked(repo_root)
    status = tuple(
        line
        for line in _run_git(
            repo_root,
            ["status", "--porcelain=v1", "--untracked-files=all"],
        ).splitlines()
        if line
    )
    allowed = {f"?? {path.as_posix()}" for path in allowed_transient_paths}
    unexpected = tuple(sorted(line for line in status if line not in allowed))
    if unexpected:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_REPOSITORY_NOT_CLEAN",
            "repository changes exist outside allowed lifecycle artifacts",
            details=unexpected,
        )
    return head


def _load_canonical(path: Path, model: type[LocalABCContract]) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        contract = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_PAYLOAD_INVALID",
            "an authorization V3 payload failed validation",
            path.as_posix(),
        ) from error
    if observed != contract.canonical_json():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_PAYLOAD_NOT_CANONICAL",
            "an authorization V3 payload is not canonical JSON",
            path.as_posix(),
        )
    return contract


def _build_authorization(
    *,
    repo_root: Path,
    issuer_head: str,
    confirmation: IssuanceConfirmation,
) -> ExecutionAuthorization:
    _validate_static(repo_root)
    if confirmation.confirmed_issuer_merge_commit != issuer_head:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ISSUER_CONFIRMATION_DRIFT",
            "operator confirmation does not bind current merged main",
        )
    issued_at = confirmation.confirmed_at
    return ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=AuthorizationLifecycle.ISSUED,
        scope=AUTHORIZATION_SCOPE,
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
    )


def issue_authorization(
    *,
    repo_root: Path,
    confirmation: IssuanceConfirmation,
    now: datetime | None = None,
) -> dict[str, object]:
    """Issue one non-overwriting V3 authority after live review."""

    root = repo_root.resolve()
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if confirmation.confirmed_at > observed_now + timedelta(minutes=1):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_CONFIRMATION_IN_FUTURE",
            "the issuance confirmation timestamp is in the future",
        )
    if observed_now - confirmation.confirmed_at > timedelta(minutes=15):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_CONFIRMATION_STALE",
            "the issuance confirmation is older than 15 minutes",
        )
    issuer_head = _require_main(root, ())
    _require_ancestor(root, IMPLEMENTATION_MERGE_COMMIT)
    if (root / CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ALREADY_CONSUMED",
            "authorization V3 was already consumed",
        )
    authorization = _build_authorization(
        repo_root=root,
        issuer_head=issuer_head,
        confirmation=confirmation,
    )
    payload = authorization.canonical_json().encode("utf-8")
    _write_non_overwriting(root / AUTHORIZATION_PATH, payload)
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V3_ISSUED",
        "authorization_id": authorization.authorization_id,
        "authorization_path": AUTHORIZATION_PATH.as_posix(),
        "authorization_sha256": _sha256_bytes(payload),
        "issued_from_main_commit": authorization.issued_from_main_commit,
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "platform_accelerator": PLATFORM_ACCELERATOR,
        "worker_cuda_visible_devices": "0",
        "maximum_saved_versions": 1,
        "maximum_model_requests": 18,
        "authorization_reusable": False,
        "runtime_execution_authorized": True,
        "next_gate": ISSUED_NEXT_GATE,
    }


def _validate_live_authorization(
    repo_root: Path,
    authorization: ExecutionAuthorization,
    issuer_head: str,
) -> None:
    if authorization.issued_from_main_commit != issuer_head:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ISSUER_DRIFT",
            "authorization V3 was not issued from current merged main",
        )
    if authorization.implementation != _implementation(repo_root):
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_IMPLEMENTATION_DRIFT",
            "authorization V3 implementation binding drifted",
        )


def verify_authorization(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify V3 immediately before the one governed Kaggle execution."""

    root = repo_root.resolve()
    issuer_head = _require_main(root, (AUTHORIZATION_PATH,))
    _require_ancestor(root, IMPLEMENTATION_MERGE_COMMIT)
    _validate_static(root)
    if (root / CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ALREADY_CONSUMED",
            "authorization V3 has a consumption receipt",
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, ExecutionAuthorization)
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    observed_now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    if not authorization.issued_at <= observed_now < authorization.expires_at:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_EXPIRED",
            "authorization V3 is outside its validity window",
        )
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V3_VALID",
        "authorization_sha256": authorization.fingerprint(),
        "issuer_head_commit": issuer_head,
        "notebook_sha256": authorization.implementation.notebook.sha256,
        "runtime_script_sha256": authorization.implementation.runtime_script_sha256,
        "platform_accelerator": PLATFORM_ACCELERATOR,
        "worker_cuda_visible_devices": "0",
        "maximum_saved_versions": 1,
        "maximum_model_requests": 18,
        "consumed": False,
        "runtime_execution_authorized": True,
        "next_gate": ISSUED_NEXT_GATE,
    }


def consume_authorization(
    *,
    repo_root: Path,
    outcome: ExecutionOutcome,
    saved_version_id: int,
    evidence_zip_sha256: str | None = None,
    terminal_log_sha256: str | None = None,
    consumed_at: datetime | None = None,
) -> dict[str, object]:
    """Consume V3 after any governed terminal attempt."""

    root = repo_root.resolve()
    issuer_head = _require_main(root, (AUTHORIZATION_PATH,))
    _require_ancestor(root, IMPLEMENTATION_MERGE_COMMIT)
    _validate_static(root)
    if (root / CONSUMPTION_PATH).exists():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_ALREADY_CONSUMED",
            "authorization V3 consumption already exists",
        )
    loaded = _load_canonical(root / AUTHORIZATION_PATH, ExecutionAuthorization)
    authorization = cast(ExecutionAuthorization, loaded)
    _validate_live_authorization(root, authorization, issuer_head)
    authorization_payload = authorization.canonical_json().encode("utf-8")
    receipt = AuthorizationConsumption(
        consumption_id=(
            "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v3"
        ),
        authorization_id=AUTHORIZATION_ID,
        authorization_sha256=_sha256_bytes(authorization_payload),
        lifecycle=AuthorizationLifecycle.CONSUMED,
        consumed_at=consumed_at or datetime.now(UTC),
        outcome=outcome,
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
        authorization_reusable=False,
        next_gate=CONSUMED_NEXT_GATE,
    )
    payload = receipt.canonical_json().encode("utf-8")
    _write_non_overwriting(root / CONSUMPTION_PATH, payload)
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V3_CONSUMED",
        "authorization_sha256": receipt.authorization_sha256,
        "consumption_path": CONSUMPTION_PATH.as_posix(),
        "consumption_sha256": _sha256_bytes(payload),
        "outcome": receipt.outcome.value,
        "saved_version_id": receipt.saved_version_id,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "next_gate": receipt.next_gate,
    }


def _load_confirmation(path: Path) -> IssuanceConfirmation:
    try:
        observed = path.read_text(encoding="utf-8")
        confirmation = IssuanceConfirmation.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_CONFIRMATION_INVALID",
            "the issuance confirmation failed validation",
            path.as_posix(),
        ) from error
    if observed != confirmation.canonical_json():
        raise AuthorizationError(
            "P4_AUTHORIZATION_V3_CONFIRMATION_NOT_CANONICAL",
            "the issuance confirmation is not canonical JSON",
            path.as_posix(),
        )
    return confirmation


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p4-authorization-v3")
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
    consume.add_argument("--saved-version-id", type=int, required=True)
    consume.add_argument("--evidence-zip-sha256")
    consume.add_argument("--terminal-log-sha256")
    return parser


def _error_json(error: AuthorizationError) -> str:
    return ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
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
                saved_version_id=cast(int, arguments.saved_version_id),
                evidence_zip_sha256=cast(str | None, arguments.evidence_zip_sha256),
                terminal_log_sha256=cast(str | None, arguments.terminal_log_sha256),
            )
        else:
            raise AuthorizationError(
                "P4_AUTHORIZATION_V3_COMMAND_INVALID",
                "P4 authorization V3 command is invalid",
            )
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0
    except AuthorizationError as error:
        print(_error_json(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
