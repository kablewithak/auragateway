"""Generate and validate the explicit Triton attention-backend V1 harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import ConfigDict, Field, ValidationError, model_validator

import auragateway.local_abc.explicit_driver_link_probe_execution_acceptance_v1 as link_acceptance
import auragateway.local_abc.p0_p2_platform_diagnostic_execution_acceptance_v1 as p0p2_acceptance
from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_COMMIT: Final = "81597c1ebc6add70f6c35e3f2287acba9c078519"
LINK_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_driver_link_probe_execution_acceptance_v1.json"
)
PLATFORM_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_diagnostic_execution_acceptance_v1.json"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/explicit_triton_attention_backend_v1.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "explicit_triton_attention_backend_v1_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_triton_attention_backend_v1_review.json"
)
NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_explicit_triton_attention_backend_v1.ipynb"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_triton_attention_backend_v1_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

NOTEBOOK_NAME: Final = "ag-cu129-triton-attention-backend-v1"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-triton-attn-backend-failed-v1"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-triton-attention-evidence-v1.zip"
RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
WHEELHOUSE_MATERIALIZER_TITLE: Final = "auragateway-cu129-wheelhouse-materializer-v1"
EXPECTED_VLLM_VERSION: Final = "0.19.1"
EXPECTED_TORCH_VERSION: Final = "2.10.0+cu129"
EXPECTED_TRITON_VERSION: Final = "3.6.0"
EXPECTED_GPU_NAME: Final = "Tesla T4"
EXPECTED_COMPUTE_CAPABILITY: Final = (7, 5)
EXPECTED_BACKEND_NAME: Final = "TRITON_ATTN"
EXPECTED_BACKEND_PATH: Final = "vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"
EXPECTED_PRIMITIVE_MODULE: Final = "vllm.v1.attention.ops.triton_prefill_attention"
EXPECTED_PRIMITIVE_NAME: Final = "context_attention_fwd"
UPSTREAM_TAG: Final = "v0.19.1"
REQUIRED_OUTPUTS: Final = (
    "platform_identity_report_v1.json",
    "backend_discovery_report_v1.json",
    "backend_import_report_v1.json",
    "backend_capability_report_v1.json",
    "attention_primitive_report_v1.json",
    "explicit_triton_attention_backend_summary_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
)
MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
MAXIMUM_GENERATED_LINE_LENGTH: Final = 100


class ExplicitTritonAttentionBackendV1Error(RuntimeError):
    """Fail-closed implementation-generation error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(LocalABCContract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AcceptedDriverAuthority(_StrictModel):
    status: Literal["EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID"]
    saved_version_id: Literal[339127349]
    terminal_decision: Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"]
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    unchanged_replay_authorized: Literal[False]


class AcceptedPlatformAuthority(_StrictModel):
    status: Literal["P0_P2_PLATFORM_DIAGNOSTIC_EXECUTION_ACCEPTANCE_V1_VALID"]
    saved_version_id: Literal[339140121]
    terminal_decision: Literal["P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED"]
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gpu_count: Literal[2]
    gpu_name: Literal["Tesla T4"]
    compute_capability: tuple[Literal[7], Literal[5]]
    torch_version: Literal["2.10.0+cu129"]
    triton_version: Literal["3.6.0"]
    wheel_entry_count: Literal[176]
    manifest_entry_count: Literal[182]
    verified_entry_count: Literal[182]
    implementation_authorized: Literal[True]
    unchanged_replay_authorized: Literal[False]
    next_gate: Literal["design_and_implement_explicit_triton_attention_backend_v1"]


class BackendReference(_StrictModel):
    upstream_tag: Literal["v0.19.1"]
    registry_module: Literal["vllm.v1.attention.backends.registry"]
    registry_enum: Literal["AttentionBackendEnum.TRITON_ATTN"]
    backend_path: Literal["vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"]
    primitive_module: Literal["vllm.v1.attention.ops.triton_prefill_attention"]
    primitive_name: Literal["context_attention_fwd"]
    selection_mode: Literal["EXPLICIT_REGISTRY_ENUM_NO_AUTO_SELECTION"]


class FailureContract(_StrictModel):
    error_code: str = Field(pattern=r"^[A-Z0-9_]{8,96}$")
    first_boundary: str = Field(min_length=3, max_length=120)


class AttentionBackendRequest(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-cu129-explicit-triton-attention-backend-v1-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    mode: Literal["GOVERNED_QUALIFICATION"]
    notebook_name: str
    failed_notebook_name: str
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    attached_inputs_required: Literal[1]
    wheelhouse_materializer_title: str
    wheelhouse_saved_version_ordinal: Literal[1]
    runtime_output_directory: str
    expected_vllm_version: Literal["0.19.1"]
    expected_torch_version: Literal["2.10.0+cu129"]
    expected_triton_version: Literal["3.6.0"]
    expected_gpu_name: Literal["Tesla T4"]
    expected_compute_capability: tuple[Literal[7], Literal[5]]
    backend: BackendReference
    evidence_zip_name: str
    maximum_sessions: Literal[1]
    maximum_runtime_install_attempts: Literal[1]
    maximum_backend_discovery_attempts: Literal[1]
    maximum_backend_import_attempts: Literal[1]
    maximum_attention_primitive_attempts: Literal[1]
    model_loads_permitted: Literal[0]
    worker_starts_permitted: Literal[0]
    model_requests_permitted: Literal[0]
    benchmark_trajectory_requests_permitted: Literal[0]
    network_requests_permitted: Literal[0]
    hidden_retries_permitted: Literal[False]
    silent_backend_fallback_permitted: Literal[False]
    global_environment_mutation_permitted: Literal[False]
    cuda_toolkit_stub_permitted: Literal[False]
    filesystem_mutation_scope: Literal["KAGGLE_WORKING_DIRECTORY_ONLY"]
    required_outputs: tuple[str, ...] = Field(min_length=8, max_length=8)
    failure_contracts: tuple[FailureContract, ...] = Field(min_length=10)
    next_gate_on_pass: Literal["preserve_evidence_and_accept_attention_backend_execution"]
    next_gate_on_failure: Literal["preserve_evidence_and_classify_attention_backend_failure"]

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        if self.source_main_commit != SOURCE_MAIN_COMMIT:
            raise ValueError("request source main drifted")
        if self.notebook_name != NOTEBOOK_NAME:
            raise ValueError("notebook name drifted")
        if self.failed_notebook_name != FAILED_NOTEBOOK_NAME:
            raise ValueError("failed notebook name drifted")
        if self.wheelhouse_materializer_title != WHEELHOUSE_MATERIALIZER_TITLE:
            raise ValueError("wheelhouse materializer title drifted")
        if self.runtime_output_directory != RUNTIME_OUTPUT_DIRECTORY:
            raise ValueError("runtime output directory drifted")
        if self.evidence_zip_name != EVIDENCE_ZIP_NAME:
            raise ValueError("evidence ZIP name drifted")
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("required output set or order drifted")
        if len({item.error_code for item in self.failure_contracts}) != len(self.failure_contracts):
            raise ValueError("failure-contract codes must be unique")
        for name in (self.notebook_name, self.failed_notebook_name):
            if len(name) > MAXIMUM_KAGGLE_NAME_CHARACTERS:
                raise ValueError("Kaggle name exceeds 50 characters")
        return self


class ExecutionBudget(_StrictModel):
    maximum_sessions: Literal[1] = 1
    maximum_platform_preflight_attempts: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_backend_discovery_attempts: Literal[1] = 1
    maximum_backend_import_attempts: Literal[1] = 1
    maximum_backend_capability_validation_attempts: Literal[1] = 1
    maximum_attention_primitive_attempts: Literal[1] = 1
    maximum_model_loads: Literal[0] = 0
    maximum_worker_starts: Literal[0] = 0
    maximum_model_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-explicit-triton-attention-backend-v1-review"]
    status: Literal["APPROVED_FOR_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision: Literal["SEPARATE_MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_GATE"]
    architecture_requirements: tuple[str, ...] = Field(min_length=12)
    rejected_alternatives: tuple[str, ...] = Field(min_length=8)
    backend: BackendReference
    execution_budget: ExecutionBudget
    next_gate: Literal["generate_and_validate_explicit_triton_attention_backend_v1"]

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        if self.source_main_commit != SOURCE_MAIN_COMMIT:
            raise ValueError("review source main drifted")
        required = {
            "bind_accepted_driver_link_execution",
            "bind_accepted_p0_p2_execution",
            "preserve_consumed_attempt_non_replay",
            "exact_vllm_distribution_version",
            "target_site_package_origin_validation",
            "explicit_triton_registry_discovery",
            "reject_backend_registry_override",
            "explicit_backend_class_import",
            "t4_compute_capability_validation",
            "float16_decoder_configuration_validation",
            "single_model_free_attention_primitive",
            "pytorch_sdpa_numerical_reference",
            "explicit_backend_attribution",
            "silent_fallback_rejection",
            "deterministic_notebook_generation",
            "machine_readable_failure_taxonomy",
            "stop_on_first_failure",
            "no_runtime_authorization_issuance",
        }
        if set(self.architecture_requirements) != required:
            raise ValueError("architecture requirement set drifted")
        rejected = {
            "automatic_attention_backend_selection",
            "flashinfer_fallback",
            "worker_startup",
            "model_loading",
            "inference_request",
            "benchmark_trajectory",
            "global_linker_environment_mutation",
            "cuda_toolkit_stub_linking",
            "unchanged_p0_p2_replay",
            "network_installation",
        }
        if set(self.rejected_alternatives) != rejected:
            raise ValueError("rejected alternative set drifted")
        return self


class ArtifactReceipt(_StrictModel):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class NotebookReceipt(ArtifactReceipt):
    notebook_name: str
    cell_count: Literal[2]
    outputs_present: Literal[False]
    execution_counts_present: Literal[False]
    maximum_code_line_length: int = Field(ge=1, le=100)


class ImplementationSafety(_StrictModel):
    runtime_execution_authorization_issued: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installations_performed: Literal[0] = 0
    backend_imports_performed: Literal[0] = 0
    attention_primitive_attempts: Literal[0] = 0
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests: Literal[0] = 0
    benchmark_trajectory_requests: Literal[0] = 0
    network_requests: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0


class AttentionBackendImplementationRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-explicit-triton-attention-backend-v1-record"]
    status: Literal["EXPLICIT_TRITON_ATTENTION_BACKEND_V1_VALID"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_driver: AcceptedDriverAuthority
    accepted_platform: AcceptedPlatformAuthority
    backend: BackendReference
    template: ArtifactReceipt
    request: ArtifactReceipt
    review: ArtifactReceipt
    notebook: NotebookReceipt
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    runtime_execution_authorized: Literal[False]
    unchanged_upstream_replay_authorized: Literal[False]
    next_gate: Literal[
        "design_and_merge_explicit_triton_attention_backend_execution_authorization_v1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=12)

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.source_main_commit != SOURCE_MAIN_COMMIT:
            raise ValueError("record source main drifted")
        if self.notebook.notebook_name != NOTEBOOK_NAME:
            raise ValueError("record notebook name drifted")
        return self


@dataclass(frozen=True)
class GeneratedArtifacts:
    request_bytes: bytes
    review_bytes: bytes
    notebook_bytes: bytes
    record: AttentionBackendImplementationRecord


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_TEMPORARY_PATH_PRESENT",
            "temporary generated path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _load_driver_authority(repo_root: Path) -> AcceptedDriverAuthority:
    try:
        record = link_acceptance.validate(repo_root)
    except Exception as error:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_DRIVER_AUTHORITY_INVALID",
            "accepted explicit-driver evidence is invalid",
            LINK_ACCEPTANCE_PATH.as_posix(),
        ) from error
    return AcceptedDriverAuthority(
        status=record.status,
        saved_version_id=record.saved_version.saved_version_id,
        terminal_decision=record.link_contract.decision,
        evidence_zip_sha256=record.saved_version.evidence_archive.sha256,
        unchanged_replay_authorized=record.unchanged_probe_replay_authorized,
    )


def _load_platform_authority(repo_root: Path) -> AcceptedPlatformAuthority:
    try:
        record = p0p2_acceptance.validate(repo_root)
    except Exception as error:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PLATFORM_AUTHORITY_INVALID",
            "accepted P0-P2 evidence is invalid",
            PLATFORM_ACCEPTANCE_PATH.as_posix(),
        ) from error
    return AcceptedPlatformAuthority(
        status=record.status,
        saved_version_id=record.saved_version.saved_version_id,
        terminal_decision=record.terminal_decision,
        evidence_zip_sha256=record.saved_version.evidence_archive.sha256,
        gpu_count=record.platform.gpu_count,
        gpu_name=record.platform.gpu_name,
        compute_capability=record.platform.compute_capability,
        torch_version=record.triton.torch_version,
        triton_version=record.triton.triton_version,
        wheel_entry_count=record.triton.wheel_entry_count,
        manifest_entry_count=record.triton.manifest_entry_count,
        verified_entry_count=record.triton.verified_entry_count,
        implementation_authorized=(record.explicit_attention_backend_v1_implementation_authorized),
        unchanged_replay_authorized=record.unchanged_diagnostic_replay_authorized,
        next_gate=record.next_gate,
    )


def _backend_reference() -> BackendReference:
    return BackendReference(
        upstream_tag=UPSTREAM_TAG,
        registry_module="vllm.v1.attention.backends.registry",
        registry_enum="AttentionBackendEnum.TRITON_ATTN",
        backend_path=EXPECTED_BACKEND_PATH,
        primitive_module=EXPECTED_PRIMITIVE_MODULE,
        primitive_name=EXPECTED_PRIMITIVE_NAME,
        selection_mode="EXPLICIT_REGISTRY_ENUM_NO_AUTO_SELECTION",
    )


def _failure_contracts() -> tuple[FailureContract, ...]:
    return (
        FailureContract(
            error_code="ATTENTION_BACKEND_PLATFORM_IDENTITY_MISMATCH",
            first_boundary="platform_preflight",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_WHEELHOUSE_INVALID",
            first_boundary="wheelhouse_validation",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_RUNTIME_INSTALL_FAILED",
            first_boundary="offline_target_installation",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_TARGET_IMPORT_FAILED",
            first_boundary="target_runtime_import",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_VLLM_VERSION_MISMATCH",
            first_boundary="vllm_distribution_identity",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_TARGET_ORIGIN_MISMATCH",
            first_boundary="target_package_origin",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_REGISTRY_MISMATCH",
            first_boundary="backend_registry_discovery",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_OVERRIDE_DETECTED",
            first_boundary="backend_registry_override",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_CLASS_IMPORT_FAILED",
            first_boundary="backend_class_import",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_CAPABILITY_REJECTED",
            first_boundary="backend_capability_validation",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_FALLBACK_DETECTED",
            first_boundary="explicit_backend_attribution",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_PRIMITIVE_FAILED",
            first_boundary="attention_primitive_execution",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_RESULT_MISMATCH",
            first_boundary="pytorch_sdpa_comparison",
        ),
        FailureContract(
            error_code="ATTENTION_BACKEND_GLOBAL_ENVIRONMENT_MUTATION_DETECTED",
            first_boundary="environment_integrity",
        ),
    )


def _request() -> AttentionBackendRequest:
    return AttentionBackendRequest(
        request_id="auragateway-cu129-explicit-triton-attention-backend-v1-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        mode="GOVERNED_QUALIFICATION",
        notebook_name=NOTEBOOK_NAME,
        failed_notebook_name=FAILED_NOTEBOOK_NAME,
        accelerator="T4_X2",
        internet_enabled=False,
        attached_inputs_required=1,
        wheelhouse_materializer_title=WHEELHOUSE_MATERIALIZER_TITLE,
        wheelhouse_saved_version_ordinal=1,
        runtime_output_directory=RUNTIME_OUTPUT_DIRECTORY,
        expected_vllm_version=EXPECTED_VLLM_VERSION,
        expected_torch_version=EXPECTED_TORCH_VERSION,
        expected_triton_version=EXPECTED_TRITON_VERSION,
        expected_gpu_name=EXPECTED_GPU_NAME,
        expected_compute_capability=EXPECTED_COMPUTE_CAPABILITY,
        backend=_backend_reference(),
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        maximum_sessions=1,
        maximum_runtime_install_attempts=1,
        maximum_backend_discovery_attempts=1,
        maximum_backend_import_attempts=1,
        maximum_attention_primitive_attempts=1,
        model_loads_permitted=0,
        worker_starts_permitted=0,
        model_requests_permitted=0,
        benchmark_trajectory_requests_permitted=0,
        network_requests_permitted=0,
        hidden_retries_permitted=False,
        silent_backend_fallback_permitted=False,
        global_environment_mutation_permitted=False,
        cuda_toolkit_stub_permitted=False,
        filesystem_mutation_scope="KAGGLE_WORKING_DIRECTORY_ONLY",
        required_outputs=REQUIRED_OUTPUTS,
        failure_contracts=_failure_contracts(),
        next_gate_on_pass="preserve_evidence_and_accept_attention_backend_execution",
        next_gate_on_failure="preserve_evidence_and_classify_attention_backend_failure",
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-cu129-explicit-triton-attention-backend-v1-review",
        status="APPROVED_FOR_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        decision="SEPARATE_MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_GATE",
        architecture_requirements=(
            "bind_accepted_driver_link_execution",
            "bind_accepted_p0_p2_execution",
            "preserve_consumed_attempt_non_replay",
            "exact_vllm_distribution_version",
            "target_site_package_origin_validation",
            "explicit_triton_registry_discovery",
            "reject_backend_registry_override",
            "explicit_backend_class_import",
            "t4_compute_capability_validation",
            "float16_decoder_configuration_validation",
            "single_model_free_attention_primitive",
            "pytorch_sdpa_numerical_reference",
            "explicit_backend_attribution",
            "silent_fallback_rejection",
            "deterministic_notebook_generation",
            "machine_readable_failure_taxonomy",
            "stop_on_first_failure",
            "no_runtime_authorization_issuance",
        ),
        rejected_alternatives=(
            "automatic_attention_backend_selection",
            "flashinfer_fallback",
            "worker_startup",
            "model_loading",
            "inference_request",
            "benchmark_trajectory",
            "global_linker_environment_mutation",
            "cuda_toolkit_stub_linking",
            "unchanged_p0_p2_replay",
            "network_installation",
        ),
        backend=_backend_reference(),
        execution_budget=ExecutionBudget(),
        next_gate="generate_and_validate_explicit_triton_attention_backend_v1",
    )


def _read_template(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_TEMPLATE_UNSAFE",
            "attention-backend template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    payload = path.read_bytes()
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_TEMPLATE_ENCODING_INVALID",
            "attention-backend template is not UTF-8",
            TEMPLATE_PATH.as_posix(),
        ) from error
    compile(source, TEMPLATE_PATH.as_posix(), "exec")
    required = (
        EXPECTED_BACKEND_PATH,
        EXPECTED_PRIMITIVE_MODULE,
        EXPECTED_PRIMITIVE_NAME,
        'selected_backend = registry.AttentionBackendEnum["TRITON_ATTN"]',
        "selected_backend.is_overridden()",
        "validate_configuration(",
        "DeviceCapability(major=7, minor=5)",
        "torch.nn.functional.scaled_dot_product_attention",
        "ATTENTION_BACKEND_PRIMITIVE_PASSED",
        "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED",
    )
    for fragment in required:
        if fragment not in source:
            raise ExplicitTritonAttentionBackendV1Error(
                "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_TEMPLATE_INCOMPLETE",
                "attention-backend template is missing a required fragment",
                fragment,
            )
    prohibited = (
        "AutoModel",
        "AutoTokenizer",
        "api_server",
        "requests.get(",
        "urllib.request",
        "os.symlink(",
        'os.environ["LIBRARY_PATH"] =',
        'os.environ["LD_LIBRARY_PATH"] =',
        "FLASHINFER",
    )
    for fragment in prohibited:
        if fragment in source:
            raise ExplicitTritonAttentionBackendV1Error(
                "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_TEMPLATE_PROHIBITED",
                "attention-backend template contains a prohibited fragment",
                fragment,
            )
    maximum = max(len(line) for line in source.splitlines())
    if maximum > MAXIMUM_GENERATED_LINE_LENGTH:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_TEMPLATE_LINE_TOO_LONG",
            "attention-backend template line exceeds 100 characters",
            str(maximum),
        )
    return payload


def _notebook_bytes(template_bytes: bytes) -> bytes:
    source = template_bytes.decode("utf-8")
    document = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# AuraGateway Explicit Triton Attention Backend V1\n",
                    "\n",
                    (
                        "Model-free Q6 probe for exact TRITON_ATTN discovery, "
                        "capability, attribution and one attention primitive.\n"
                    ),
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return (json.dumps(document, ensure_ascii=True, indent=1) + "\n").encode("utf-8")


def build_generated(repo_root: Path) -> GeneratedArtifacts:
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_AUTHORIZATION_PRESENT",
            "transient full-run authorization must remain absent",
            AUTHORIZATION_PATH.as_posix(),
        )
    driver_authority = _load_driver_authority(repo_root)
    platform_authority = _load_platform_authority(repo_root)
    template_bytes = _read_template(repo_root)
    request = _request()
    review = _review()
    request_bytes = _canonical_json(request.model_dump(mode="json")).encode("utf-8")
    review_bytes = _canonical_json(review.model_dump(mode="json")).encode("utf-8")
    notebook_bytes = _notebook_bytes(template_bytes)
    maximum_line = max(len(line) for line in template_bytes.decode("utf-8").splitlines())
    record = AttentionBackendImplementationRecord(
        record_id="auragateway-cu129-explicit-triton-attention-backend-v1-record",
        status="EXPLICIT_TRITON_ATTENTION_BACKEND_V1_VALID",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_driver=driver_authority,
        accepted_platform=platform_authority,
        backend=_backend_reference(),
        template=ArtifactReceipt(
            repository_path=TEMPLATE_PATH.as_posix(),
            sha256=_sha256_bytes(template_bytes),
        ),
        request=ArtifactReceipt(
            repository_path=REQUEST_PATH.as_posix(),
            sha256=_sha256_bytes(request_bytes),
        ),
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
        ),
        notebook=NotebookReceipt(
            repository_path=NOTEBOOK_PATH.as_posix(),
            sha256=_sha256_bytes(notebook_bytes),
            notebook_name=NOTEBOOK_NAME,
            cell_count=2,
            outputs_present=False,
            execution_counts_present=False,
            maximum_code_line_length=maximum_line,
        ),
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        execution_budget=ExecutionBudget(),
        safety=ImplementationSafety(),
        runtime_execution_authorized=False,
        unchanged_upstream_replay_authorized=False,
        next_gate=("design_and_merge_explicit_triton_attention_backend_execution_authorization_v1"),
        non_claims=(
            "The generated notebook has not been executed.",
            "No runtime execution authorization is issued by this implementation.",
            "The CUDA 12.9 target runtime was not installed by this change.",
            "The vLLM package was not imported by this change.",
            "The TRITON_ATTN backend was not imported by this change.",
            "The attention primitive was not compiled or executed by this change.",
            "Backend numerical correctness has not been established.",
            "Broad vLLM import compatibility has not been established.",
            "vLLM native-extension compatibility has not been established.",
            "No model has been loaded.",
            "No worker has been started.",
            "No inference request has been issued.",
            "No cache behavior has been tested.",
            "No A/B/C benchmark trajectory has been executed.",
            "Deployment is not claimed.",
            "Production readiness is not claimed.",
        ),
    )
    return GeneratedArtifacts(
        request_bytes=request_bytes,
        review_bytes=review_bytes,
        notebook_bytes=notebook_bytes,
        record=record,
    )


def generate(repo_root: Path) -> AttentionBackendImplementationRecord:
    generated = build_generated(repo_root)
    _write_bytes_atomic(repo_root / REQUEST_PATH, generated.request_bytes)
    _write_bytes_atomic(repo_root / REVIEW_PATH, generated.review_bytes)
    _write_bytes_atomic(repo_root / NOTEBOOK_PATH, generated.notebook_bytes)
    record_bytes = _canonical_json(generated.record.model_dump(mode="json")).encode("utf-8")
    _write_bytes_atomic(repo_root / RECORD_PATH, record_bytes)
    return generated.record


def _validate_exact(repo_root: Path, path: Path, expected: bytes) -> None:
    target = repo_root / path
    if not target.is_file() or target.is_symlink():
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_ARTIFACT_UNSAFE",
            "generated artifact is missing or unsafe",
            path.as_posix(),
        )
    if target.read_bytes() != expected:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_ARTIFACT_DRIFT",
            "generated artifact differs from fresh rebuild",
            path.as_posix(),
        )


def validate(repo_root: Path) -> AttentionBackendImplementationRecord:
    generated = build_generated(repo_root)
    record_bytes = _canonical_json(generated.record.model_dump(mode="json")).encode("utf-8")
    _validate_exact(repo_root, REQUEST_PATH, generated.request_bytes)
    _validate_exact(repo_root, REVIEW_PATH, generated.review_bytes)
    _validate_exact(repo_root, NOTEBOOK_PATH, generated.notebook_bytes)
    _validate_exact(repo_root, RECORD_PATH, record_bytes)
    try:
        observed = AttentionBackendImplementationRecord.model_validate_json(record_bytes)
    except ValidationError as error:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_RECORD_INVALID",
            "implementation record violates its contract",
            RECORD_PATH.as_posix(),
        ) from error
    if observed != generated.record:
        raise ExplicitTritonAttentionBackendV1Error(
            "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_RECORD_SEMANTIC_DRIFT",
            "implementation record semantic state drifted",
            RECORD_PATH.as_posix(),
        )
    return generated.record


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            marker = "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_VALIDATED"
        else:
            raise ExplicitTritonAttentionBackendV1Error(
                "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": record.status,
                    "notebook_sha256": record.notebook.sha256,
                    "implementation_status": record.implementation_status,
                    "runtime_execution_authorized": record.runtime_execution_authorized,
                    "next_gate": record.next_gate,
                }
            )
        )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        ExplicitTritonAttentionBackendV1Error,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, ExplicitTritonAttentionBackendV1Error)
            else {
                "error_code": "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
