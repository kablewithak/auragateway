"""Generate and validate the governed CUDA 12.9 P0-P2 platform diagnostic V2."""

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
from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_COMMIT: Final = "fe297a6f1aeed04119452552874dab22bfe01dee"
ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_driver_link_probe_execution_acceptance_v1.json"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p0_p2_platform_diagnostic_v2.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "option_c_p0_p2_platform_diagnostic_v2_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_diagnostic_v2_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v2.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_diagnostic_v2_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-platform-diagnostic-v2"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-platform-diag-failed-v2"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-p0-p2-platform-evidence-v2.zip"
RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
WHEELHOUSE_MATERIALIZER_TITLE: Final = "auragateway-cu129-wheelhouse-materializer-v1"
ACCEPTED_SAVED_VERSION_ID: Final = 339127349
ACCEPTED_EVIDENCE_ZIP_SHA256: Final = (
    "8be080c46a077d88dcd0d51325fe2a751936a599d3b350ba7def3bdf5eb7b33c"
)
ACCEPTED_NOTEBOOK_SHA256: Final = "7545dd1ee34148f9e5e9c91df01c2134b9587014a4d5e9df4af9ff3162865a4d"
REAL_DRIVER_RESOLVED_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so.580.159.04"
RUNTIME_DRIVER_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so.1"
REQUIRED_LINK_FLAGS: Final = (
    "-L/usr/local/nvidia/lib64",
    "-Wl,-rpath,/usr/local/nvidia/lib64",
    "-Wl,-t",
    "-lcuda",
)
REQUIRED_OUTPUTS: Final = (
    "platform_identity_report_v2.json",
    "explicit_cuda_driver_link_report_v2.json",
    "minimal_triton_kernel_report_v2.json",
    "p0_p2_platform_diagnostic_summary_v2.json",
    "bundle_manifest_v2.json",
    "human_report_v2.md",
)
MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
MAXIMUM_GENERATED_LINE_LENGTH: Final = 100


class P0P2PlatformDiagnosticV2Error(RuntimeError):
    """Fail-closed V2 diagnostic generation error."""

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
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(LocalABCContract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AcceptedProbeAuthority(_StrictModel):
    status: Literal["EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID"]
    saved_version_id: Literal[339127349]
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    link_decision: Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"]
    required_link_flags: tuple[str, str, str, str]
    selected_link_library: str
    runtime_library_path: str
    cu_init_zero: Literal[True]
    stub_rejected: Literal[True]
    global_environment_mutation_required: Literal[False]
    p0_p2_v2_authorized: Literal[True]
    unchanged_replay_authorized: Literal[False]
    next_gate: Literal["design_and_implement_p0_p2_platform_diagnostic_v2"]

    @model_validator(mode="after")
    def validate_exact_authority(self) -> Self:
        if self.evidence_zip_sha256 != ACCEPTED_EVIDENCE_ZIP_SHA256:
            raise ValueError("accepted evidence ZIP identity drifted")
        if self.notebook_sha256 != ACCEPTED_NOTEBOOK_SHA256:
            raise ValueError("accepted notebook identity drifted")
        if self.required_link_flags != REQUIRED_LINK_FLAGS:
            raise ValueError("accepted link flags drifted")
        if self.selected_link_library != REAL_DRIVER_RESOLVED_PATH:
            raise ValueError("accepted selected library drifted")
        if self.runtime_library_path != RUNTIME_DRIVER_PATH:
            raise ValueError("accepted runtime library drifted")
        return self


class ProbeContract(_StrictModel):
    probe_id: Literal["P0", "P1", "P2"]
    name: str
    pass_decision: str
    permitted_failure_decisions: tuple[str, ...] = Field(min_length=1)
    maximum_attempts: Literal[1]


class PlatformDiagnosticV2Request(_StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    request_id: Literal["auragateway-cu129-p0-p2-platform-diagnostic-v2-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_probe_record_path: str
    accepted_probe_saved_version_id: Literal[339127349]
    mode: Literal["KAGGLE_DIAGNOSTIC"]
    notebook_name: str
    failed_notebook_name: str
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    attached_inputs_required: Literal[1]
    wheelhouse_materializer_title: str
    wheelhouse_saved_version_ordinal: Literal[1]
    runtime_output_directory: str
    evidence_zip_name: str
    maximum_sessions: Literal[1]
    maximum_runtime_install_attempts: Literal[1]
    maximum_kernel_compile_and_execution_attempts: Literal[1]
    stop_on_first_failure: Literal[True]
    global_environment_mutation_permitted: Literal[False]
    command_local_environment_overrides_permitted: tuple[str, ...]
    cuda_toolkit_stub_permitted: Literal[False]
    network_requests_permitted: Literal[0]
    credentials_permitted: Literal[False]
    customer_data_permitted: Literal[False]
    model_loads_permitted: Literal[0]
    worker_starts_permitted: Literal[0]
    model_requests_permitted: Literal[0]
    benchmark_trajectory_requests_permitted: Literal[0]
    hidden_retries_permitted: Literal[False]
    filesystem_mutation_scope: Literal["KAGGLE_WORKING_DIRECTORY_ONLY"]
    probes: tuple[ProbeContract, ProbeContract, ProbeContract]
    required_outputs: tuple[str, ...] = Field(min_length=6, max_length=6)
    next_gate_on_pass: Literal["implement_explicit_triton_attention_backend"]
    next_gate_on_failure: Literal["preserve_evidence_and_classify_platform_failure"]

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.source_main_commit != SOURCE_MAIN_COMMIT:
            raise ValueError("request source main drifted")
        if self.accepted_probe_record_path != ACCEPTANCE_RECORD_PATH.as_posix():
            raise ValueError("accepted record path drifted")
        if self.notebook_name != NOTEBOOK_NAME:
            raise ValueError("notebook name drifted")
        if self.failed_notebook_name != FAILED_NOTEBOOK_NAME:
            raise ValueError("failed notebook name drifted")
        if self.runtime_output_directory != RUNTIME_OUTPUT_DIRECTORY:
            raise ValueError("runtime directory drifted")
        if self.wheelhouse_materializer_title != WHEELHOUSE_MATERIALIZER_TITLE:
            raise ValueError("wheelhouse title drifted")
        if self.evidence_zip_name != EVIDENCE_ZIP_NAME:
            raise ValueError("evidence ZIP name drifted")
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("required outputs drifted")
        if tuple(item.probe_id for item in self.probes) != ("P0", "P1", "P2"):
            raise ValueError("probe order drifted")
        for name in (self.notebook_name, self.failed_notebook_name):
            if len(name) > MAXIMUM_KAGGLE_NAME_CHARACTERS:
                raise ValueError("Kaggle name exceeds 50 characters")
        return self


class ExecutionBudget(_StrictModel):
    maximum_sessions: Literal[1] = 1
    maximum_platform_preflight_attempts: Literal[1] = 1
    maximum_source_materialization_attempts: Literal[1] = 1
    maximum_syntax_compile_attempts: Literal[1] = 1
    maximum_link_attempts: Literal[1] = 1
    maximum_elf_inspection_attempts: Literal[1] = 1
    maximum_loader_resolution_attempts: Literal[1] = 1
    maximum_driver_initialization_attempts: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_kernel_compile_and_execution_attempts: Literal[1] = 1
    maximum_model_loads: Literal[0] = 0
    maximum_worker_starts: Literal[0] = 0
    maximum_model_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p0-p2-platform-diagnostic-v2-review"]
    status: Literal["APPROVED_FOR_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_probe_saved_version_id: Literal[339127349]
    decision: Literal["SEPARATE_V2_DIAGNOSTIC_WITH_PROVEN_EXPLICIT_P1"]
    architecture_requirements: tuple[str, ...] = Field(min_length=8)
    rejected_alternatives: tuple[str, ...] = Field(min_length=4)
    execution_budget: ExecutionBudget
    next_gate: Literal["generate_and_validate_p0_p2_platform_diagnostic_v2"]

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        if self.source_main_commit != SOURCE_MAIN_COMMIT:
            raise ValueError("review source main drifted")
        required = {
            "preserve_platform_diagnostic_v1",
            "bind_accepted_explicit_driver_probe",
            "exact_p1_source_bytes",
            "explicit_real_driver_link_flags",
            "link_trace_real_driver_selection",
            "elf_needed_and_runpath_validation",
            "runtime_loader_and_cuinit_validation",
            "p2_only_after_p0_and_p1_pass",
            "offline_hash_locked_cu129_install",
            "single_minimal_triton_kernel",
            "command_local_internal_linker_realization",
            "deterministic_notebook_generation",
            "stop_on_first_failure",
            "machine_readable_failure_taxonomy",
        }
        if set(self.architecture_requirements) != required:
            raise ValueError("architecture requirement set drifted")
        rejected = {
            "mutate_platform_diagnostic_v1",
            "global_library_path_mutation",
            "global_ld_library_path_mutation",
            "cuda_toolkit_stub_linking",
            "libcuda_symlink_or_copy",
            "model_or_worker_execution",
            "hidden_retry",
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
    authorization_issued: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installations_performed: Literal[0] = 0
    kernel_compile_and_execution_attempts: Literal[0] = 0
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests: Literal[0] = 0
    benchmark_trajectory_requests: Literal[0] = 0
    network_requests: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0


class PlatformDiagnosticV2Record(_StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-platform-diagnostic-v2-record"]
    status: Literal["P0_P2_PLATFORM_DIAGNOSTIC_V2_VALID"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_probe: AcceptedProbeAuthority
    template: ArtifactReceipt
    request: ArtifactReceipt
    review: ArtifactReceipt
    notebook: NotebookReceipt
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    attached_inputs_required: Literal[1]
    wheelhouse_materializer_title: str
    wheelhouse_saved_version_ordinal: Literal[1]
    runtime_output_directory: str
    evidence_zip_name: str
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    execution_authorized_after_merge: Literal[True]
    unchanged_kaggle_replay_authorized: Literal[False]
    next_gate: Literal["execute_governed_p0_p2_platform_diagnostic_v2"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.source_main_commit != SOURCE_MAIN_COMMIT:
            raise ValueError("record source main drifted")
        if self.wheelhouse_materializer_title != WHEELHOUSE_MATERIALIZER_TITLE:
            raise ValueError("record wheelhouse title drifted")
        if self.runtime_output_directory != RUNTIME_OUTPUT_DIRECTORY:
            raise ValueError("record runtime directory drifted")
        if self.evidence_zip_name != EVIDENCE_ZIP_NAME:
            raise ValueError("record evidence ZIP drifted")
        return self


@dataclass(frozen=True)
class GeneratedArtifacts:
    request_bytes: bytes
    review_bytes: bytes
    notebook_bytes: bytes
    record: PlatformDiagnosticV2Record


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
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_TEMPORARY_PATH_PRESENT",
            "temporary generated path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _load_acceptance_authority(repo_root: Path) -> AcceptedProbeAuthority:
    try:
        record = link_acceptance.validate(repo_root)
    except Exception as error:
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ACCEPTANCE_INVALID",
            "accepted driver-link evidence is invalid",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        ) from error
    raw = record.model_dump(mode="json")
    saved_version = raw.get("saved_version")
    link_contract = raw.get("link_contract")
    if not isinstance(saved_version, dict) or not isinstance(link_contract, dict):
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ACCEPTANCE_SHAPE_INVALID",
            "accepted driver-link authority shape drifted",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    archive = saved_version.get("evidence_archive")
    if not isinstance(archive, dict):
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ACCEPTANCE_ARCHIVE_INVALID",
            "accepted evidence archive shape drifted",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    flags = link_contract.get("required_link_flags")
    if not isinstance(flags, list) or not all(isinstance(item, str) for item in flags):
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ACCEPTANCE_FLAGS_INVALID",
            "accepted link flags shape drifted",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    exact_flags = cast(tuple[str, str, str, str], tuple(flags))
    return AcceptedProbeAuthority(
        status=cast(
            Literal["EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID"],
            raw.get("status"),
        ),
        saved_version_id=cast(
            Literal[339127349],
            saved_version.get("saved_version_id"),
        ),
        evidence_zip_sha256=str(archive.get("sha256")),
        notebook_sha256=str(saved_version.get("notebook_sha256")),
        link_decision=cast(
            Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"],
            link_contract.get("decision"),
        ),
        required_link_flags=exact_flags,
        selected_link_library=str(link_contract.get("selected_link_library")),
        runtime_library_path=str(link_contract.get("runtime_library_path")),
        cu_init_zero=cast(Literal[True], link_contract.get("cu_init_zero")),
        stub_rejected=cast(
            Literal[True],
            link_contract.get("cuda_toolkit_stub_rejected"),
        ),
        global_environment_mutation_required=cast(
            Literal[False],
            raw.get("global_environment_mutation_required"),
        ),
        p0_p2_v2_authorized=cast(
            Literal[True],
            raw.get("p0_p2_diagnostic_v2_implementation_authorized"),
        ),
        unchanged_replay_authorized=cast(
            Literal[False],
            raw.get("unchanged_probe_replay_authorized"),
        ),
        next_gate=cast(
            Literal["design_and_implement_p0_p2_platform_diagnostic_v2"],
            raw.get("next_gate"),
        ),
    )


def _request() -> PlatformDiagnosticV2Request:
    return PlatformDiagnosticV2Request(
        request_id="auragateway-cu129-p0-p2-platform-diagnostic-v2-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_probe_record_path=ACCEPTANCE_RECORD_PATH.as_posix(),
        accepted_probe_saved_version_id=339127349,
        mode="KAGGLE_DIAGNOSTIC",
        notebook_name=NOTEBOOK_NAME,
        failed_notebook_name=FAILED_NOTEBOOK_NAME,
        accelerator="T4_X2",
        internet_enabled=False,
        attached_inputs_required=1,
        wheelhouse_materializer_title=WHEELHOUSE_MATERIALIZER_TITLE,
        wheelhouse_saved_version_ordinal=1,
        runtime_output_directory=RUNTIME_OUTPUT_DIRECTORY,
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        maximum_sessions=1,
        maximum_runtime_install_attempts=1,
        maximum_kernel_compile_and_execution_attempts=1,
        stop_on_first_failure=True,
        global_environment_mutation_permitted=False,
        command_local_environment_overrides_permitted=(
            "LIBRARY_PATH_REAL_DRIVER_ONLY",
            "LDFLAGS_REAL_DRIVER_FLAGS",
            "LD_LIBRARY_PATH_TARGET_RUNTIME_AND_REAL_DRIVER",
            "CUDA_VISIBLE_DEVICES_GPU_ZERO",
        ),
        cuda_toolkit_stub_permitted=False,
        network_requests_permitted=0,
        credentials_permitted=False,
        customer_data_permitted=False,
        model_loads_permitted=0,
        worker_starts_permitted=0,
        model_requests_permitted=0,
        benchmark_trajectory_requests_permitted=0,
        hidden_retries_permitted=False,
        filesystem_mutation_scope="KAGGLE_WORKING_DIRECTORY_ONLY",
        probes=(
            ProbeContract(
                probe_id="P0",
                name="KAGGLE_IMAGE_AND_REAL_DRIVER_PREFLIGHT",
                pass_decision="P0_REAL_DRIVER_PREFLIGHT_PASSED",
                permitted_failure_decisions=("DIAGNOSTIC_INVALID",),
                maximum_attempts=1,
            ),
            ProbeContract(
                probe_id="P1",
                name="EXPLICIT_CUDA_DRIVER_LINK_CONTRACT",
                pass_decision="EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED",
                permitted_failure_decisions=(
                    "DIAGNOSTIC_INVALID",
                    "EXPLICIT_CUDA_DRIVER_LINK_FAILED",
                    "EXPLICIT_CUDA_DRIVER_LINK_LIBRARY_SELECTION_FAILED",
                    "EXPLICIT_CUDA_DRIVER_ELF_CONTRACT_FAILED",
                    "EXPLICIT_CUDA_DRIVER_DYNAMIC_LOADER_FAILED",
                    "EXPLICIT_CUDA_DRIVER_INITIALIZATION_FAILED",
                    "EXPLICIT_CUDA_DRIVER_GLOBAL_ENVIRONMENT_MUTATION_DETECTED",
                ),
                maximum_attempts=1,
            ),
            ProbeContract(
                probe_id="P2",
                name="GOVERNED_CU129_MINIMAL_TRITON_KERNEL",
                pass_decision="CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
                permitted_failure_decisions=(
                    "GOVERNED_CU129_WHEELHOUSE_INVALID",
                    "GOVERNED_CU129_RUNTIME_INSTALL_FAILED",
                    "GOVERNED_CU129_RUNTIME_IMPORT_FAILED",
                    "CURRENT_STACK_TRITON_INCOMPATIBLE",
                    "P2_GLOBAL_ENVIRONMENT_MUTATION_DETECTED",
                ),
                maximum_attempts=1,
            ),
        ),
        required_outputs=REQUIRED_OUTPUTS,
        next_gate_on_pass="implement_explicit_triton_attention_backend",
        next_gate_on_failure="preserve_evidence_and_classify_platform_failure",
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-cu129-p0-p2-platform-diagnostic-v2-review",
        status="APPROVED_FOR_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_probe_saved_version_id=339127349,
        decision="SEPARATE_V2_DIAGNOSTIC_WITH_PROVEN_EXPLICIT_P1",
        architecture_requirements=(
            "preserve_platform_diagnostic_v1",
            "bind_accepted_explicit_driver_probe",
            "exact_p1_source_bytes",
            "explicit_real_driver_link_flags",
            "link_trace_real_driver_selection",
            "elf_needed_and_runpath_validation",
            "runtime_loader_and_cuinit_validation",
            "p2_only_after_p0_and_p1_pass",
            "offline_hash_locked_cu129_install",
            "single_minimal_triton_kernel",
            "command_local_internal_linker_realization",
            "deterministic_notebook_generation",
            "stop_on_first_failure",
            "machine_readable_failure_taxonomy",
        ),
        rejected_alternatives=(
            "mutate_platform_diagnostic_v1",
            "global_library_path_mutation",
            "global_ld_library_path_mutation",
            "cuda_toolkit_stub_linking",
            "libcuda_symlink_or_copy",
            "model_or_worker_execution",
            "hidden_retry",
        ),
        execution_budget=ExecutionBudget(),
        next_gate="generate_and_validate_p0_p2_platform_diagnostic_v2",
    )


def _read_template(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_TEMPLATE_UNSAFE",
            "diagnostic template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    payload = path.read_bytes()
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_TEMPLATE_ENCODING_INVALID",
            "diagnostic template is not UTF-8",
            TEMPLATE_PATH.as_posix(),
        ) from error
    compile(source, TEMPLATE_PATH.as_posix(), "exec")
    required = (
        "-L/usr/local/nvidia/lib64",
        "-Wl,-rpath,/usr/local/nvidia/lib64",
        "-Wl,-t",
        "-lcuda",
        "readelf",
        "libcuda.so.1",
        'runtime_environment["LIBRARY_PATH"]',
        "CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
        "P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED",
    )
    for fragment in required:
        if fragment not in source:
            raise P0P2PlatformDiagnosticV2Error(
                "P0_P2_PLATFORM_DIAGNOSTIC_V2_TEMPLATE_INCOMPLETE",
                "diagnostic template is missing a required fragment",
                fragment,
            )
    prohibited = (
        "import vllm",
        "AutoModel",
        "requests.get(",
        "urllib.request",
        "os.symlink(",
        'os.environ["LIBRARY_PATH"] =',
        'os.environ["LD_LIBRARY_PATH"] =',
    )
    for fragment in prohibited:
        if fragment in source:
            raise P0P2PlatformDiagnosticV2Error(
                "P0_P2_PLATFORM_DIAGNOSTIC_V2_TEMPLATE_PROHIBITED",
                "diagnostic template contains a prohibited fragment",
                fragment,
            )
    maximum = max(len(line) for line in source.splitlines())
    if maximum > MAXIMUM_GENERATED_LINE_LENGTH:
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_TEMPLATE_LINE_TOO_LONG",
            "diagnostic template line exceeds 100 characters",
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
                    "# AuraGateway CUDA 12.9 P0-P2 Platform Diagnostic V2\n",
                    "\n",
                    (
                        "Uses the accepted explicit real-driver P1 contract "
                        "before one governed offline Triton P2.\n"
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
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_AUTHORIZATION_PRESENT",
            "transient full-run authorization must remain absent",
            AUTHORIZATION_PATH.as_posix(),
        )
    authority = _load_acceptance_authority(repo_root)
    template_bytes = _read_template(repo_root)
    request = _request()
    review = _review()
    request_bytes = _canonical_json(request.model_dump(mode="json")).encode("utf-8")
    review_bytes = _canonical_json(review.model_dump(mode="json")).encode("utf-8")
    notebook_bytes = _notebook_bytes(template_bytes)
    maximum_line = max(len(line) for line in template_bytes.decode("utf-8").splitlines())
    record = PlatformDiagnosticV2Record(
        record_id="auragateway-cu129-p0-p2-platform-diagnostic-v2-record",
        status="P0_P2_PLATFORM_DIAGNOSTIC_V2_VALID",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_probe=authority,
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
        accelerator="T4_X2",
        internet_enabled=False,
        attached_inputs_required=1,
        wheelhouse_materializer_title=WHEELHOUSE_MATERIALIZER_TITLE,
        wheelhouse_saved_version_ordinal=1,
        runtime_output_directory=RUNTIME_OUTPUT_DIRECTORY,
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        execution_budget=ExecutionBudget(),
        safety=ImplementationSafety(),
        execution_authorized_after_merge=True,
        unchanged_kaggle_replay_authorized=False,
        next_gate="execute_governed_p0_p2_platform_diagnostic_v2",
        non_claims=(
            "The V2 notebook has not been executed.",
            "The CUDA 12.9 wheelhouse was not installed by this change.",
            "P2 has not been attempted by this change.",
            "Triton compatibility has not been established.",
            "vLLM has not been imported.",
            "No model has been loaded.",
            "No worker has been started.",
            "No model request has been issued.",
            "No benchmark trajectory has been executed.",
            "Environment qualification is not claimed.",
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


def generate(repo_root: Path) -> PlatformDiagnosticV2Record:
    generated = build_generated(repo_root)
    _write_bytes_atomic(repo_root / REQUEST_PATH, generated.request_bytes)
    _write_bytes_atomic(repo_root / REVIEW_PATH, generated.review_bytes)
    _write_bytes_atomic(repo_root / NOTEBOOK_PATH, generated.notebook_bytes)
    _write_bytes_atomic(
        repo_root / RECORD_PATH,
        _canonical_json(generated.record.model_dump(mode="json")).encode("utf-8"),
    )
    return generated.record


def _validate_exact(repo_root: Path, path: Path, expected: bytes) -> None:
    target = repo_root / path
    if not target.is_file() or target.is_symlink():
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ARTIFACT_UNSAFE",
            "generated artifact is missing or unsafe",
            path.as_posix(),
        )
    if target.read_bytes() != expected:
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_ARTIFACT_DRIFT",
            "generated artifact differs from fresh rebuild",
            path.as_posix(),
        )


def validate(repo_root: Path) -> PlatformDiagnosticV2Record:
    generated = build_generated(repo_root)
    record_bytes = _canonical_json(generated.record.model_dump(mode="json")).encode("utf-8")
    _validate_exact(repo_root, REQUEST_PATH, generated.request_bytes)
    _validate_exact(repo_root, REVIEW_PATH, generated.review_bytes)
    _validate_exact(repo_root, NOTEBOOK_PATH, generated.notebook_bytes)
    _validate_exact(repo_root, RECORD_PATH, record_bytes)
    try:
        observed = PlatformDiagnosticV2Record.model_validate(
            json.loads(record_bytes.decode("utf-8"))
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_RECORD_INVALID",
            "implementation record violates its contract",
            RECORD_PATH.as_posix(),
        ) from error
    if observed != generated.record:
        raise P0P2PlatformDiagnosticV2Error(
            "P0_P2_PLATFORM_DIAGNOSTIC_V2_RECORD_SEMANTIC_DRIFT",
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
            marker = "P0_P2_PLATFORM_DIAGNOSTIC_V2_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "P0_P2_PLATFORM_DIAGNOSTIC_V2_VALIDATED"
        else:
            raise P0P2PlatformDiagnosticV2Error(
                "P0_P2_PLATFORM_DIAGNOSTIC_V2_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": record.status,
                    "notebook_sha256": record.notebook.sha256,
                    "accepted_saved_version_id": (record.accepted_probe.saved_version_id),
                    "implementation_status": record.implementation_status,
                    "next_gate": record.next_gate,
                    "kaggle_execution_authorized": False,
                }
            )
        )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        P0P2PlatformDiagnosticV2Error,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, P0P2PlatformDiagnosticV2Error)
            else {
                "error_code": "P0_P2_PLATFORM_DIAGNOSTIC_V2_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
