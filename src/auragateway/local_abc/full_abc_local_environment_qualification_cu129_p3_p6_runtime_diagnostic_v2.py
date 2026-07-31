"""Generate and validate the bounded P3-P6 runtime diagnostic V2 assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_MAIN_COMMIT: Final = "1849c4b3f9cd36400b30d29ea3b3e67712251815"

FAILURE_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v1.json"
)
FAILURE_ACCEPTANCE_RECORD_SHA256: Final = (
    "927990205412968484b24902055e8dc775acb5eb1f3447b525b860b8f448e1fc"
)
FAILURE_ACCEPTANCE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v1_review.json"
)
FAILURE_ACCEPTANCE_REVIEW_SHA256: Final = (
    "f05a3bcfd0873b707f912ad679eefd4ceb8df34e56ce666eb81e36b5106ab631"
)
V1_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v1_record.json"
)
V1_IMPLEMENTATION_RECORD_SHA256: Final = (
    "98762563de31eef4272705af5d647de96a467c6525d3a20dda1543f356880916"
)
V1_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v1.py.tmpl"
)
V1_TEMPLATE_SHA256: Final = "1ff3d6751fb6f097720a6067877e177ccdf4e04a71dc545248a712a1e91c24ac"

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v2.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v2_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v2_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v2.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v2_record.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v2.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v2.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-01-local-abc-cu129-p3-p6-runtime-install-diagnostics-v2.md"
)
REPORT_PATH: Final = Path("docs/reports/AuraGateway_CU129_P3_P6_Runtime_Install_Diagnostics_V2.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_cu129_p3_p6_runtime_install_diagnostics_v2.md")

NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diagnostic-v2"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diag-failed-v2"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-p3-p6-runtime-evidence-v2.zip"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
EXPECTED_RUFF_VERSION: Final = "0.15.21"

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v2.json"
)
OPERATIONAL_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_consumption_v2.json"
)

GENERATED_PATHS: Final = (
    REQUEST_PATH,
    REVIEW_PATH,
    NOTEBOOK_PATH,
    RECORD_PATH,
)
STATIC_PATHS: Final = (
    SOURCE_PATH,
    TEMPLATE_PATH,
    TEST_PATH,
    ADR_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
)
CANDIDATE_PATHS: Final = tuple(sorted((*GENERATED_PATHS, *STATIC_PATHS)))


class P3P6V2ImplementationError(RuntimeError):
    """Fail-closed V2 implementation and validation error."""

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
        raise P3P6V2ImplementationError(
            "P3_P6_V2_IMPLEMENTATION_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class AcceptedAuthority(_StrictModel):
    authority_id: Literal[
        "v1_failure_acceptance_record",
        "v1_failure_acceptance_review",
        "v1_implementation_record",
    ]
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str
    next_gate: str


class ProbeDefinition(_StrictModel):
    probe_id: Literal["P3", "P4", "P5", "P6"]
    name: str
    pass_decision: str
    fail_decision: str
    prerequisites: tuple[str, ...]
    maximum_model_requests: int = Field(ge=0, le=5)
    maximum_worker_starts: int = Field(ge=0, le=3)


class InputBoundary(_StrictModel):
    role: Literal["model_snapshot", "vllm_runtime"]
    artifact_format: Literal[
        "hugging_face_snapshot_directory",
        "python_wheelhouse_directory",
    ]
    exact_sha256_required: Literal[True] = True
    network_fallback_permitted: Literal[False] = False


class ExecutionBudget(_StrictModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[5] = 5
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    hidden_retries_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class KnownV1Failure(_StrictModel):
    saved_version_id: Literal[339375227]
    failure_code: Literal["P3_P6_RUNTIME_INSTALL_FAILED"]
    failure_boundary: Literal["OFFLINE_TARGET_RUNTIME_INSTALLATION"]
    root_cause_status: Literal["UNRESOLVED"]
    observed_implementation_defect: Literal[
        "V1_FIND_LINKS_TARGETS_WHEELHOUSE_ROOT_NOT_WHEELS_DIRECTORY"
    ]
    defect_can_prevent_wheel_discovery: Literal[True] = True
    runtime_root_cause_confirmed: Literal[False] = False
    unchanged_replay_authorized: Literal[False] = False


class InstallDiagnosticsContract(_StrictModel):
    find_links_relative_path: Literal["wheels"] = "wheels"
    model_copy_after_successful_install: Literal[True] = True
    scratch_and_evidence_roots_separated: Literal[True] = True
    subprocess_return_code_retained: Literal[True] = True
    subprocess_timeout_state_retained: Literal[True] = True
    bounded_stdout_tail_retained: Literal[True] = True
    bounded_stderr_tail_retained: Literal[True] = True
    disk_before_and_after_retained: Literal[True] = True
    target_runtime_size_retained: Literal[True] = True
    deterministic_probe_terminal_reports: Literal[True] = True
    scratch_cleanup_report_required: Literal[True] = True
    maximum_evidence_zip_bytes: Literal[2097152] = 2097152
    raw_scratch_in_evidence_zip: Literal[False] = False
    hidden_install_retries: Literal[0] = 0


class P3P6V2Request(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v2-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[
        AcceptedAuthority,
        AcceptedAuthority,
        AcceptedAuthority,
    ]
    strategy: Literal["P3_P6_DIAGNOSTIC_V2_WITH_INSTALL_TELEMETRY"]
    selected_backend: Literal["TRITON_ATTN"]
    backend_selection_mechanism: Literal["EXPLICIT_VLLM_ATTENTION_BACKEND_CLI_ARGUMENT"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_v1_failure: KnownV1Failure
    install_diagnostics: InstallDiagnosticsContract
    probes: tuple[
        ProbeDefinition,
        ProbeDefinition,
        ProbeDefinition,
        ProbeDefinition,
    ]
    inputs: tuple[InputBoundary, InputBoundary]
    execution_budget: ExecutionBudget
    stop_on_first_failure: Literal[True] = True
    complete_terminal_evidence_required: Literal[True] = True
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v2"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_exact_sequence(self) -> Self:
        if tuple(item.probe_id for item in self.probes) != (
            "P3",
            "P4",
            "P5",
            "P6",
        ):
            raise ValueError("P3-P6 V2 probe sequence drifted")
        if tuple(item.role for item in self.inputs) != (
            "model_snapshot",
            "vllm_runtime",
        ):
            raise ValueError("P3-P6 V2 input role order drifted")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v2-review"]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    first_divergence_from_v1: Literal[
        "V1_FIND_LINKS_TARGETS_WHEELHOUSE_ROOT_AND_DISCARDS_PIP_DIAGNOSTICS"
    ]
    v1_reuse_decision: Literal["PRESERVE_P3_P6_BEHAVIOR_REPLACE_INSTALL_AND_EVIDENCE_BOUNDARIES"]
    architecture: tuple[str, ...] = Field(min_length=15)
    required_failure_codes: tuple[str, ...] = Field(min_length=16)
    output_contract: tuple[str, ...]
    execution_budget: ExecutionBudget
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["implement_and_merge_p3_p6_runtime_install_diagnostics_v2"]


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class NotebookReceipt(ArtifactReceipt):
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v2"]
    failed_notebook_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v2"]
    code_cell_count: Literal[1]
    execution_count_present: Literal[False] = False
    output_present: Literal[False] = False


class ImplementationSafety(_StrictModel):
    runtime_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    network_requests_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_present: Literal[False] = False
    external_spend: Literal[0] = 0


class ImplementationRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v2-implementation"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[
        AcceptedAuthority,
        AcceptedAuthority,
        AcceptedAuthority,
    ]
    request: ArtifactReceipt
    review: ArtifactReceipt
    source: ArtifactReceipt
    template: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    notebook: NotebookReceipt
    evidence_zip_name: Literal["ag-cu129-p3-p6-runtime-evidence-v2.zip"]
    expected_runtime_outputs: tuple[str, ...]
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v2"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class GeneratedArtifacts(_StrictModel):
    request: P3P6V2Request
    review: ArchitectureReview
    notebook_bytes: bytes
    record: ImplementationRecord


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _receipt(path: Path, payload: bytes) -> ArtifactReceipt:
    return ArtifactReceipt(
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _path_receipt(repo_root: Path, path: Path) -> ArtifactReceipt:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise P3P6V2ImplementationError(
            "P3_P6_V2_STATIC_ARTIFACT_MISSING",
            "required V2 static artifact is missing or unsafe",
            path.as_posix(),
        )
    return _receipt(path, absolute.read_bytes())


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise P3P6V2ImplementationError(
            "P3_P6_V2_TEMPORARY_PATH_PRESENT",
            "temporary generated path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _read_bound(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise P3P6V2ImplementationError(
            "P3_P6_V2_ACCEPTED_AUTHORITY_MISSING",
            "accepted V2 authority is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise P3P6V2ImplementationError(
            "P3_P6_V2_ACCEPTED_AUTHORITY_DRIFT",
            "accepted V2 authority identity drifted",
            relative_path.as_posix(),
        )
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P3P6V2ImplementationError(
            "P3_P6_V2_ACCEPTED_AUTHORITY_INVALID",
            "accepted V2 authority is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(raw, dict):
        raise P3P6V2ImplementationError(
            "P3_P6_V2_ACCEPTED_AUTHORITY_ROOT_INVALID",
            "accepted V2 authority root must be one object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], raw)


def _accepted_authorities(
    repo_root: Path,
) -> tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority]:
    acceptance_record = _read_bound(
        repo_root,
        FAILURE_ACCEPTANCE_RECORD_PATH,
        FAILURE_ACCEPTANCE_RECORD_SHA256,
    )
    acceptance_review = _read_bound(
        repo_root,
        FAILURE_ACCEPTANCE_REVIEW_PATH,
        FAILURE_ACCEPTANCE_REVIEW_SHA256,
    )
    v1_record = _read_bound(
        repo_root,
        V1_IMPLEMENTATION_RECORD_PATH,
        V1_IMPLEMENTATION_RECORD_SHA256,
    )
    if (
        acceptance_record.get("status") != "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID"
        or acceptance_record.get("next_gate")
        != "design_and_merge_p3_p6_runtime_install_diagnostics_v2"
        or acceptance_record.get("authorization_lifecycle_closed") is not True
        or acceptance_record.get("root_cause_resolved") is not False
        or acceptance_record.get("unchanged_replay_authorized") is not False
    ):
        raise P3P6V2ImplementationError(
            "P3_P6_V2_FAILURE_ACCEPTANCE_RECORD_DRIFT",
            "V1 failure-acceptance record no longer authorizes V2 design",
            FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    if (
        acceptance_review.get("status") != "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V1_CLASSIFIED"
        or acceptance_review.get("decision")
        != "ACCEPT_RUNTIME_INSTALL_BOUNDARY_FAILURE_WITH_UNRESOLVED_ROOT_CAUSE"
        or acceptance_review.get("failure_boundary") != "OFFLINE_TARGET_RUNTIME_INSTALLATION"
        or acceptance_review.get("root_cause_classification") != "UNRESOLVED_PIP_SUBPROCESS_FAILURE"
        or acceptance_review.get("runtime_execution_authorized") is not False
    ):
        raise P3P6V2ImplementationError(
            "P3_P6_V2_FAILURE_ACCEPTANCE_REVIEW_DRIFT",
            "V1 failure classification no longer supports V2 design",
            FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
        )
    notebook = v1_record.get("notebook")
    if (
        v1_record.get("status") != "IMPLEMENTED_NOT_EXECUTED"
        or not isinstance(notebook, dict)
        or notebook.get("sha256")
        != "bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7"
    ):
        raise P3P6V2ImplementationError(
            "P3_P6_V2_V1_IMPLEMENTATION_RECORD_DRIFT",
            "V1 implementation record no longer matches the failed notebook",
            V1_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    return (
        AcceptedAuthority(
            authority_id="v1_failure_acceptance_record",
            repository_path=FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
            sha256=FAILURE_ACCEPTANCE_RECORD_SHA256,
            status=str(acceptance_record["status"]),
            next_gate=str(acceptance_record["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="v1_failure_acceptance_review",
            repository_path=FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
            sha256=FAILURE_ACCEPTANCE_REVIEW_SHA256,
            status=str(acceptance_review["status"]),
            next_gate=str(acceptance_review["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="v1_implementation_record",
            repository_path=V1_IMPLEMENTATION_RECORD_PATH.as_posix(),
            sha256=V1_IMPLEMENTATION_RECORD_SHA256,
            status=str(v1_record["status"]),
            next_gate=str(v1_record["next_gate"]),
        ),
    )


def _probes() -> tuple[
    ProbeDefinition,
    ProbeDefinition,
    ProbeDefinition,
    ProbeDefinition,
]:
    return (
        ProbeDefinition(
            probe_id="P3",
            name="ONE_WORKER_EXPLICIT_TRITON_STARTUP",
            pass_decision="ONE_WORKER_TRITON_STARTUP_PASSED",
            fail_decision="CURRENT_VLLM_TRITON_RUNTIME_FAILED",
            prerequisites=("V2_RUNTIME_INSTALL_PASSED",),
            maximum_model_requests=0,
            maximum_worker_starts=1,
        ),
        ProbeDefinition(
            probe_id="P4",
            name="ONE_DETERMINISTIC_REQUEST",
            pass_decision="ONE_REQUEST_RUNTIME_COMPATIBILITY_PASSED",
            fail_decision="CURRENT_VLLM_TRITON_RUNTIME_FAILED",
            prerequisites=("P3_PASSED",),
            maximum_model_requests=1,
            maximum_worker_starts=1,
        ),
        ProbeDefinition(
            probe_id="P5",
            name="PREFIX_CACHE_SMOKE_AND_FULL_RESTART_RESET",
            pass_decision="CACHE_SMOKE_AND_RESET_PASSED",
            fail_decision="RUNTIME_WORKS_BUT_PRD_OBSERVABILITY_CONTRACT_FAILED",
            prerequisites=("P4_PASSED",),
            maximum_model_requests=3,
            maximum_worker_starts=2,
        ),
        ProbeDefinition(
            probe_id="P6",
            name="DUAL_WORKER_PROCESS_GPU_PORT_AND_METRIC_ISOLATION",
            pass_decision="DUAL_WORKER_DIAGNOSTIC_PASSED",
            fail_decision="SINGLE_WORKER_COMPATIBLE_DUAL_WORKER_CONTRACT_FAILED",
            prerequisites=("P5_PASSED",),
            maximum_model_requests=5,
            maximum_worker_starts=3,
        ),
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "V2 has not been executed.",
        "The exact V1 pip root cause is not retrospectively claimed.",
        "No V2 runtime authorization is issued by this implementation.",
        "Future Kaggle image equivalence is not established.",
        "Successful offline installation is not yet established.",
        "P3 worker startup is not yet established by V2.",
        "P4 deterministic inference is not yet established by V2.",
        "P5 cache reuse and reset are not yet established by V2.",
        "P6 dual-worker isolation is not yet established by V2.",
        "Model quality is not evaluated.",
        "A/B/C benchmark trajectories are not executed.",
        "Latency and cost improvements are not claimed.",
        "Customer-data readiness is not claimed.",
        "Deployment and production readiness are not claimed.",
    )


def _request(
    authorities: tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority],
) -> P3P6V2Request:
    return P3P6V2Request(
        request_id="auragateway-cu129-p3-p6-runtime-diagnostic-v2-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        strategy="P3_P6_DIAGNOSTIC_V2_WITH_INSTALL_TELEMETRY",
        selected_backend="TRITON_ATTN",
        backend_selection_mechanism="EXPLICIT_VLLM_ATTENTION_BACKEND_CLI_ARGUMENT",
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        known_v1_failure=KnownV1Failure(
            saved_version_id=339375227,
            failure_code="P3_P6_RUNTIME_INSTALL_FAILED",
            failure_boundary="OFFLINE_TARGET_RUNTIME_INSTALLATION",
            root_cause_status="UNRESOLVED",
            observed_implementation_defect=(
                "V1_FIND_LINKS_TARGETS_WHEELHOUSE_ROOT_NOT_WHEELS_DIRECTORY"
            ),
        ),
        install_diagnostics=InstallDiagnosticsContract(),
        probes=_probes(),
        inputs=(
            InputBoundary(
                role="model_snapshot",
                artifact_format="hugging_face_snapshot_directory",
            ),
            InputBoundary(
                role="vllm_runtime",
                artifact_format="python_wheelhouse_directory",
            ),
        ),
        execution_budget=ExecutionBudget(),
        next_gate="merge_then_design_separate_p3_p6_execution_authorization_v2",
        non_claims=_non_claims(),
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-cu129-p3-p6-runtime-diagnostic-v2-review",
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        first_divergence_from_v1=(
            "V1_FIND_LINKS_TARGETS_WHEELHOUSE_ROOT_AND_DISCARDS_PIP_DIAGNOSTICS"
        ),
        v1_reuse_decision=("PRESERVE_P3_P6_BEHAVIOR_REPLACE_INSTALL_AND_EVIDENCE_BOUNDARIES"),
        architecture=(
            "Bind V2 to the accepted V1 failure and exact V1 implementation record.",
            "Retain the V1 P3, P4, P5, and P6 sequence and action budgets.",
            "Point pip find-links at the governed wheelhouse wheels directory.",
            "Do not claim the missing V1 pip stderr retrospectively.",
            "Run the offline install before copying the model into writable storage.",
            "Separate heavyweight scratch state from small evidence outputs.",
            "Retain pip return code, timeout state, duration, and bounded output tails.",
            "Retain writable-disk snapshots before and after installation.",
            "Retain target-runtime file count and byte size after installation.",
            "Emit deterministic failure signals without promoting them to root cause.",
            "Emit FAILED or NOT_RUN terminal reports for every P3-P6 probe.",
            "Stop immediately after the first failure and perform no hidden retry.",
            "Remove scratch runtime and model copies before evidence bundling.",
            "Emit a scratch-cleanup report and fail closed if successful work leaks.",
            "Bundle only reviewed evidence files, not scratch or raw worker logs.",
            "Enforce a two-megabyte maximum evidence ZIP size.",
            "Preserve synthetic-only requests and prohibit raw prompt/output logging.",
            "Require a separate post-merge V2 execution authorization.",
        ),
        required_failure_codes=(
            "P3_P6_PLATFORM_IDENTITY_MISMATCH",
            "P3_P6_WHEELHOUSE_INVALID",
            "P3_P6_RUNTIME_INSTALL_FAILED",
            "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT",
            "P3_P6_RUNTIME_INSTALL_TIMEOUT",
            "P3_P6_RUNTIME_INSTALL_LAUNCH_FAILED",
            "P3_P6_MODEL_IDENTITY_MISMATCH",
            "P3_P6_EXPLICIT_BACKEND_NOT_REALIZED",
            "P3_P6_WORKER_STARTUP_FAILED",
            "P3_P6_MODEL_INVENTORY_MISMATCH",
            "P3_P6_REQUEST_FAILED",
            "P3_P6_METRIC_SEMANTIC_UNAVAILABLE",
            "P3_P6_CACHE_REUSE_NOT_OBSERVED",
            "P3_P6_RESET_NOT_PROVEN",
            "P3_P6_DUAL_WORKER_ISOLATION_FAILED",
            "P3_P6_ACTION_BUDGET_EXCEEDED",
            "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
            "P3_P6_SCRATCH_CLEANUP_FAILED",
        ),
        output_contract=(
            "runtime_install_report_v2.json",
            "p3_worker_startup_report_v2.json",
            "p4_deterministic_request_report_v2.json",
            "p5_prefix_cache_reset_report_v2.json",
            "p6_dual_worker_isolation_report_v2.json",
            "scratch_cleanup_report_v2.json",
            "p3_p6_runtime_diagnostic_summary_v2.json",
            "failure_report_v2.json",
            "bundle_manifest_v2.json",
            "human_report_v2.md",
            EVIDENCE_ZIP_NAME,
        ),
        execution_budget=ExecutionBudget(),
        next_gate="implement_and_merge_p3_p6_runtime_install_diagnostics_v2",
    )


def _template_bytes(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise P3P6V2ImplementationError(
            "P3_P6_V2_TEMPLATE_MISSING",
            "P3-P6 V2 template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    v1_template = repo_root / V1_TEMPLATE_PATH
    if (
        not v1_template.is_file()
        or v1_template.is_symlink()
        or _sha256_bytes(v1_template.read_bytes()) != V1_TEMPLATE_SHA256
    ):
        raise P3P6V2ImplementationError(
            "P3_P6_V2_V1_TEMPLATE_AUTHORITY_DRIFT",
            "V1 template authority drifted before V2 generation",
            V1_TEMPLATE_PATH.as_posix(),
        )
    raw = path.read_text(encoding="utf-8")
    replacements = {
        "__" + "NOTEBOOK_NAME" + "__": NOTEBOOK_NAME,
        "__" + "SOURCE_MAIN_COMMIT" + "__": SOURCE_MAIN_COMMIT,
        "__" + "FAILURE_ACCEPTANCE_RECORD_SHA256" + "__": (FAILURE_ACCEPTANCE_RECORD_SHA256),
        "__" + "FAILURE_ACCEPTANCE_REVIEW_SHA256" + "__": (FAILURE_ACCEPTANCE_REVIEW_SHA256),
        "__" + "V1_IMPLEMENTATION_RECORD_SHA256" + "__": (V1_IMPLEMENTATION_RECORD_SHA256),
        "__" + "MODEL_SNAPSHOT_SHA256" + "__": MODEL_SNAPSHOT_SHA256,
        "__" + "EVIDENCE_ZIP_NAME" + "__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        if raw.count(marker) != 1:
            raise P3P6V2ImplementationError(
                "P3_P6_V2_TEMPLATE_MARKER_DRIFT",
                "P3-P6 V2 template marker count drifted",
                marker,
            )
        raw = raw.replace(marker, value)
    try:
        compile(raw, TEMPLATE_PATH.as_posix(), "exec")
    except SyntaxError as error:
        raise P3P6V2ImplementationError(
            "P3_P6_V2_TEMPLATE_COMPILE_FAILED",
            "rendered P3-P6 V2 template does not compile",
            str(error.lineno),
        ) from error
    return raw.encode("utf-8")


def _notebook_bytes(rendered_template: bytes) -> bytes:
    source = rendered_template.decode("utf-8")
    lines = source.splitlines()
    code_source = [
        line + "\n" if index < len(lines) - 1 else line for index, line in enumerate(lines)
    ]
    payload = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# AuraGateway P3-P6 Runtime Diagnostic V2\n",
                    "\n",
                    "Installation diagnostics and evidence hardening only. "
                    "Runtime execution requires a separate merged authorization.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": code_source,
            },
        ],
        "metadata": {
            "accelerator": "GPU",
            "internet": False,
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
                "dockerImageVersionId": None,
                "isGpuEnabled": True,
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return _canonical_json(payload).encode("utf-8")


def build_generated(repo_root: Path) -> GeneratedArtifacts:
    if (repo_root / OPERATIONAL_AUTHORIZATION_PATH).exists():
        raise P3P6V2ImplementationError(
            "P3_P6_V2_OPERATIONAL_AUTHORIZATION_PRESENT",
            "P3-P6 V2 operational authorization must remain absent",
            OPERATIONAL_AUTHORIZATION_PATH.as_posix(),
        )
    if (repo_root / OPERATIONAL_CONSUMPTION_PATH).exists():
        raise P3P6V2ImplementationError(
            "P3_P6_V2_OPERATIONAL_CONSUMPTION_PRESENT",
            "P3-P6 V2 operational consumption receipt must remain absent",
            OPERATIONAL_CONSUMPTION_PATH.as_posix(),
        )
    authorities = _accepted_authorities(repo_root)
    request = _request(authorities)
    review = _review()
    request_bytes = request.canonical_json().encode("utf-8")
    review_bytes = review.canonical_json().encode("utf-8")
    rendered_template = _template_bytes(repo_root)
    notebook_bytes = _notebook_bytes(rendered_template)
    notebook_payload = json.loads(notebook_bytes.decode("utf-8"))
    code_cells = [item for item in notebook_payload["cells"] if item["cell_type"] == "code"]
    record = ImplementationRecord(
        record_id="auragateway-cu129-p3-p6-runtime-diagnostic-v2-implementation",
        status="IMPLEMENTED_NOT_EXECUTED",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        request=_receipt(REQUEST_PATH, request_bytes),
        review=_receipt(REVIEW_PATH, review_bytes),
        source=_path_receipt(repo_root, SOURCE_PATH),
        template=_path_receipt(repo_root, TEMPLATE_PATH),
        tests=_path_receipt(repo_root, TEST_PATH),
        adr=_path_receipt(repo_root, ADR_PATH),
        report=_path_receipt(repo_root, REPORT_PATH),
        runbook=_path_receipt(repo_root, RUNBOOK_PATH),
        notebook=NotebookReceipt(
            path=NOTEBOOK_PATH.as_posix(),
            sha256=_sha256_bytes(notebook_bytes),
            size_bytes=len(notebook_bytes),
            notebook_name=NOTEBOOK_NAME,
            failed_notebook_name=FAILED_NOTEBOOK_NAME,
            code_cell_count=cast(Literal[1], len(code_cells)),
        ),
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        expected_runtime_outputs=review.output_contract,
        execution_budget=ExecutionBudget(),
        safety=ImplementationSafety(),
        next_gate="merge_then_design_separate_p3_p6_execution_authorization_v2",
        non_claims=_non_claims(),
    )
    return GeneratedArtifacts(
        request=request,
        review=review,
        notebook_bytes=notebook_bytes,
        record=record,
    )


def generate(repo_root: Path) -> GeneratedArtifacts:
    generated = build_generated(repo_root)
    outputs = {
        REQUEST_PATH: generated.request.canonical_json().encode("utf-8"),
        REVIEW_PATH: generated.review.canonical_json().encode("utf-8"),
        NOTEBOOK_PATH: generated.notebook_bytes,
        RECORD_PATH: generated.record.canonical_json().encode("utf-8"),
    }
    for path, payload in outputs.items():
        _write_atomic(repo_root / path, payload)
    return generated


def validate(repo_root: Path) -> GeneratedArtifacts:
    expected = build_generated(repo_root)
    outputs = {
        REQUEST_PATH: expected.request.canonical_json().encode("utf-8"),
        REVIEW_PATH: expected.review.canonical_json().encode("utf-8"),
        NOTEBOOK_PATH: expected.notebook_bytes,
        RECORD_PATH: expected.record.canonical_json().encode("utf-8"),
    }
    for path, expected_payload in outputs.items():
        absolute = repo_root / path
        if not absolute.is_file() or absolute.is_symlink():
            raise P3P6V2ImplementationError(
                "P3_P6_V2_GENERATED_ARTIFACT_MISSING",
                "generated P3-P6 V2 artifact is missing or unsafe",
                path.as_posix(),
            )
        if absolute.read_bytes() != expected_payload:
            raise P3P6V2ImplementationError(
                "P3_P6_V2_GENERATED_ARTIFACT_DRIFT",
                "generated P3-P6 V2 artifact differs from fresh rebuild",
                path.as_posix(),
            )
    try:
        P3P6V2Request.model_validate_json((repo_root / REQUEST_PATH).read_text())
        ArchitectureReview.model_validate_json((repo_root / REVIEW_PATH).read_text())
        ImplementationRecord.model_validate_json((repo_root / RECORD_PATH).read_text())
    except ValidationError as error:
        raise P3P6V2ImplementationError(
            "P3_P6_V2_GENERATED_CONTRACT_INVALID",
            "generated P3-P6 V2 contract validation failed",
        ) from error
    return expected


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            generated = generate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V2_GENERATED"
        elif arguments.command == "validate":
            generated = validate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V2_VALIDATED"
        else:
            raise P3P6V2ImplementationError(
                "P3_P6_V2_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": generated.record.status,
                    "source_main_commit": generated.record.source_main_commit,
                    "notebook_sha256": generated.record.notebook.sha256,
                    "candidate_path_count": len(CANDIDATE_PATHS),
                    "v1_find_links_defect_remediated": True,
                    "install_diagnostics_retained": True,
                    "runtime_execution_authorized": False,
                    "authorization_issuer_included": False,
                    "next_gate": generated.record.next_gate,
                }
            )
        )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        P3P6V2ImplementationError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, P3P6V2ImplementationError)
            else {
                "error_code": "P3_P6_V2_IMPLEMENTATION_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
