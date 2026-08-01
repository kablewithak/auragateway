"""Generate and validate P3-P6 runtime process-tree import closure V3 assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_MAIN_COMMIT: Final = "b332e6d664e672182f49f059078dc12db74b13e0"

FAILURE_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v2.json"
)
FAILURE_ACCEPTANCE_RECORD_SHA256: Final = (
    "861fbb2467b512541940424639c3d2df8baa09fc167885bd93fa3b3e3d9f95a3"
)
FAILURE_ACCEPTANCE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v2_review.json"
)
FAILURE_ACCEPTANCE_REVIEW_SHA256: Final = (
    "8100c025460eef933c9764eb9151721ad9731717878879656ca35adbb5b61f32"
)
V2_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v2_record.json"
)
V2_IMPLEMENTATION_RECORD_SHA256: Final = (
    "e6761fa50f06989d0cfaa5e509669b0776a5d3e494990d6d89219c232c79a140"
)
V2_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v2.py.tmpl"
)
V2_TEMPLATE_SHA256: Final = "d0be85cd39dd11cd35fd9fa0ec36520fb7e7605cdbbb63f6a6dbfd4dfea732d2"

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v3.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v3_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v3_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v3.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v3_record.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v3.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v3.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-01-local-abc-cu129-p3-p6-runtime-process-tree-import-closure-v3.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Process_Tree_Import_Closure_V3.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_process_tree_import_closure_v3.md"
)

NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diagnostic-v3"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diag-failed-v3"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-p3-p6-runtime-evidence-v3.zip"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v3.json"
)
OPERATIONAL_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_consumption_v3.json"
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


class P3P6V3ImplementationError(RuntimeError):
    """Fail-closed V3 implementation and validation error."""

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
        raise P3P6V3ImplementationError(
            "P3_P6_V3_IMPLEMENTATION_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class AcceptedAuthority(_StrictModel):
    authority_id: Literal[
        "v2_failure_acceptance_record",
        "v2_failure_acceptance_review",
        "v2_implementation_record",
    ]
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str
    next_gate: str


class KnownV2Failure(_StrictModel):
    saved_version_id: Literal[339387641]
    failure_code: Literal["P3_P6_WORKER_STARTUP_FAILED"]
    failed_probe: Literal["P3"]
    runtime_install_status: Literal["PASSED"]
    root_cause_status: Literal["CONFIRMED_FROM_WORKER_LOG_TRACE"]
    first_divergence: Literal[
        "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
    ]
    violated_invariant: Literal["TARGET_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE"]
    unchanged_replay_authorized: Literal[False] = False


class ProcessTreeImportClosureContract(_StrictModel):
    target_site_propagated_by_environment: Literal[True] = True
    inherited_pythonpath_replaced: Literal[True] = True
    exact_target_site_pythonpath_required: Literal[True] = True
    nested_interpreter_probe_required: Literal[True] = True
    nested_interpreter_probe_before_model_copy: Literal[True] = True
    probe_uses_worker_environment_builder: Literal[True] = True
    critical_modules: tuple[
        Literal["vllm"],
        Literal["torch"],
        Literal["triton"],
        Literal["transformers"],
        Literal["vllm.model_executor.models.registry"],
    ]
    every_critical_origin_within_target_site: Literal[True] = True
    maximum_import_closure_probes: Literal[1] = 1
    model_loads_on_probe_failure: Literal[0] = 0
    worker_starts_on_probe_failure: Literal[0] = 0
    raw_worker_logs_in_evidence_zip: Literal[False] = False
    bounded_worker_failure_diagnostics_retained: Literal[True] = True


class ExecutionBudget(_StrictModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[5] = 5
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    hidden_retries_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


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


class P3P6V3Request(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[
        AcceptedAuthority,
        AcceptedAuthority,
        AcceptedAuthority,
    ]
    strategy: Literal["P3_P6_DIAGNOSTIC_V3_WITH_PROCESS_TREE_IMPORT_CLOSURE"]
    selected_backend: Literal["TRITON_ATTN"]
    backend_selection_mechanism: Literal["EXPLICIT_VLLM_ATTENTION_BACKEND_CLI_ARGUMENT"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_v2_failure: KnownV2Failure
    process_tree_import_closure: ProcessTreeImportClosureContract
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
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v3"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_sequences(self) -> Self:
        if tuple(item.probe_id for item in self.probes) != (
            "P3",
            "P4",
            "P5",
            "P6",
        ):
            raise ValueError("P3-P6 V3 probe sequence drifted")
        if tuple(item.role for item in self.inputs) != (
            "model_snapshot",
            "vllm_runtime",
        ):
            raise ValueError("P3-P6 V3 input role order drifted")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3-review"]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_v2_first_divergence: Literal[
        "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
    ]
    selected_resolution: Literal["EXACT_TARGET_SITE_PYTHONPATH_PLUS_NESTED_IMPORT_CLOSURE_GATE"]
    rejected_alternatives: tuple[str, ...] = Field(min_length=3)
    architecture: tuple[str, ...] = Field(min_length=15)
    required_failure_codes: tuple[str, ...] = Field(min_length=17)
    output_contract: tuple[str, ...]
    execution_budget: ExecutionBudget
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["implement_and_merge_p3_p6_runtime_process_tree_import_closure_v3"]


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class NotebookReceipt(ArtifactReceipt):
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v3"]
    failed_notebook_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v3"]
    code_cell_count: Literal[1]
    execution_count_present: Literal[False] = False
    output_present: Literal[False] = False


class ImplementationSafety(_StrictModel):
    runtime_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installation_performed: Literal[False] = False
    import_closure_probe_performed: Literal[False] = False
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
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3-implementation"]
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
    evidence_zip_name: Literal["ag-cu129-p3-p6-runtime-evidence-v3.zip"]
    expected_runtime_outputs: tuple[str, ...]
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v3"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class GeneratedArtifacts(_StrictModel):
    request: P3P6V3Request
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
        raise P3P6V3ImplementationError(
            "P3_P6_V3_STATIC_ARTIFACT_MISSING",
            "required V3 static artifact is missing or unsafe",
            path.as_posix(),
        )
    return _receipt(path, absolute.read_bytes())


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise P3P6V3ImplementationError(
            "P3_P6_V3_TEMPORARY_PATH_PRESENT",
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
        raise P3P6V3ImplementationError(
            "P3_P6_V3_ACCEPTED_AUTHORITY_MISSING",
            "accepted V3 authority is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise P3P6V3ImplementationError(
            "P3_P6_V3_ACCEPTED_AUTHORITY_DRIFT",
            "accepted V3 authority identity drifted",
            relative_path.as_posix(),
        )
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P3P6V3ImplementationError(
            "P3_P6_V3_ACCEPTED_AUTHORITY_INVALID",
            "accepted V3 authority is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(raw, dict):
        raise P3P6V3ImplementationError(
            "P3_P6_V3_ACCEPTED_AUTHORITY_ROOT_INVALID",
            "accepted V3 authority root must be one object",
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
    v2_record = _read_bound(
        repo_root,
        V2_IMPLEMENTATION_RECORD_PATH,
        V2_IMPLEMENTATION_RECORD_SHA256,
    )

    if (
        acceptance_record.get("status") != "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V2_VALID"
        or acceptance_record.get("next_gate")
        != "design_and_merge_p3_p6_runtime_process_tree_import_closure_v3"
        or acceptance_record.get("authorization_lifecycle_closed") is not True
        or acceptance_record.get("authorization_reusable") is not False
        or acceptance_record.get("runtime_execution_authorized") is not False
        or acceptance_record.get("unchanged_replay_authorized") is not False
        or acceptance_record.get("saved_version_id") != 339387641
    ):
        raise P3P6V3ImplementationError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_RECORD_DRIFT",
            "V2 failure acceptance no longer authorizes V3 design",
            FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
        )

    if (
        acceptance_review.get("status") != "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V2_CLASSIFIED"
        or acceptance_review.get("decision")
        != (
            "ACCEPT_P3_WORKER_STARTUP_FAILURE_WITH_CONFIRMED_PROCESS_TREE_IMPORT_CLOSURE_ROOT_CAUSE"
        )
        or acceptance_review.get("first_divergence")
        != ("TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS")
        or acceptance_review.get("root_cause_status") != "CONFIRMED_FROM_WORKER_LOG_TRACE"
        or acceptance_review.get("runtime_install_status") != "PASSED"
        or acceptance_review.get("failed_probe") != "P3"
        or acceptance_review.get("runtime_execution_authorized") is not False
    ):
        raise P3P6V3ImplementationError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_REVIEW_DRIFT",
            "V2 failure classification no longer supports V3 design",
            FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
        )

    notebook = v2_record.get("notebook")
    template = v2_record.get("template")
    if (
        v2_record.get("status") != "IMPLEMENTED_NOT_EXECUTED"
        or not isinstance(notebook, dict)
        or notebook.get("sha256")
        != ("912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd")
        or not isinstance(template, dict)
        or template.get("sha256") != V2_TEMPLATE_SHA256
    ):
        raise P3P6V3ImplementationError(
            "P3_P6_V3_V2_IMPLEMENTATION_RECORD_DRIFT",
            "V2 implementation authority no longer matches the failed lineage",
            V2_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    return (
        AcceptedAuthority(
            authority_id="v2_failure_acceptance_record",
            repository_path=FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
            sha256=FAILURE_ACCEPTANCE_RECORD_SHA256,
            status=str(acceptance_record["status"]),
            next_gate=str(acceptance_record["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="v2_failure_acceptance_review",
            repository_path=FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
            sha256=FAILURE_ACCEPTANCE_REVIEW_SHA256,
            status=str(acceptance_review["status"]),
            next_gate=str(acceptance_review["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="v2_implementation_record",
            repository_path=V2_IMPLEMENTATION_RECORD_PATH.as_posix(),
            sha256=V2_IMPLEMENTATION_RECORD_SHA256,
            status=str(v2_record["status"]),
            next_gate=str(v2_record["next_gate"]),
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
            prerequisites=(
                "V3_RUNTIME_INSTALL_PASSED",
                "V3_PROCESS_TREE_IMPORT_CLOSURE_PASSED",
            ),
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
            fail_decision=("RUNTIME_WORKS_BUT_PRD_OBSERVABILITY_CONTRACT_FAILED"),
            prerequisites=("P4_PASSED",),
            maximum_model_requests=3,
            maximum_worker_starts=2,
        ),
        ProbeDefinition(
            probe_id="P6",
            name="DUAL_WORKER_PROCESS_GPU_PORT_AND_METRIC_ISOLATION",
            pass_decision="DUAL_WORKER_DIAGNOSTIC_PASSED",
            fail_decision=("SINGLE_WORKER_COMPATIBLE_DUAL_WORKER_CONTRACT_FAILED"),
            prerequisites=("P5_PASSED",),
            maximum_model_requests=5,
            maximum_worker_starts=3,
        ),
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "V3 has not been executed.",
        "No V3 runtime authorization is issued by this implementation.",
        "The process-tree import-closure remediation is not runtime-proven.",
        "Passing the import probe will not by itself prove P3 readiness.",
        "Qwen architecture compatibility after remediation is not established.",
        "TRITON_ATTN backend realization is not established.",
        "P4 deterministic inference is not established.",
        "P5 cache reuse and reset are not established.",
        "P6 dual-worker isolation is not established.",
        "Model quality is not evaluated.",
        "A/B/C benchmark trajectories are not executed.",
        "Latency and cost improvements are not claimed.",
        "Customer-data readiness is not claimed.",
        "Deployment and production readiness are not claimed.",
    )


def _request(
    authorities: tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority],
) -> P3P6V3Request:
    return P3P6V3Request(
        request_id="auragateway-cu129-p3-p6-runtime-diagnostic-v3-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        strategy=("P3_P6_DIAGNOSTIC_V3_WITH_PROCESS_TREE_IMPORT_CLOSURE"),
        selected_backend="TRITON_ATTN",
        backend_selection_mechanism=("EXPLICIT_VLLM_ATTENTION_BACKEND_CLI_ARGUMENT"),
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision=("7ae557604adf67be50417f59c2c2f167def9a775"),
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        known_v2_failure=KnownV2Failure(
            saved_version_id=339387641,
            failure_code="P3_P6_WORKER_STARTUP_FAILED",
            failed_probe="P3",
            runtime_install_status="PASSED",
            root_cause_status="CONFIRMED_FROM_WORKER_LOG_TRACE",
            first_divergence=(
                "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
            ),
            violated_invariant=("TARGET_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE"),
        ),
        process_tree_import_closure=ProcessTreeImportClosureContract(
            critical_modules=(
                "vllm",
                "torch",
                "triton",
                "transformers",
                "vllm.model_executor.models.registry",
            ),
        ),
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
        next_gate=("merge_then_design_separate_p3_p6_execution_authorization_v3"),
        non_claims=_non_claims(),
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-cu129-p3-p6-runtime-diagnostic-v3-review",
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        confirmed_v2_first_divergence=(
            "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
        ),
        selected_resolution=("EXACT_TARGET_SITE_PYTHONPATH_PLUS_NESTED_IMPORT_CLOSURE_GATE"),
        rejected_alternatives=(
            "Do not rebuild the wheelhouse because V2 installation passed.",
            "Do not treat parent sys.path mutation as descendant visibility.",
            "Do not run the private vLLM registry CLI as a brittle preflight.",
            "Do not append an inherited PYTHONPATH with unknown package roots.",
        ),
        architecture=(
            "Bind V3 to the merged V2 failure acceptance and exact V2 record.",
            "Preserve the V2 offline installation and P3-P6 behavior.",
            "Replace inherited PYTHONPATH with the exact target site.",
            "Use one worker-specific environment builder for all descendants.",
            "Run one bounded nested-interpreter import-closure probe.",
            "Run the probe after target-runtime identity validation.",
            "Run the probe before writable model copying.",
            "Consume no model-load action when the import probe fails.",
            "Consume no worker-start action when the import probe fails.",
            "Import vLLM, torch, Triton and Transformers in the nested child.",
            "Import the exact vLLM model-registry module in the nested child.",
            "Require every critical module origin to resolve inside target site.",
            "Record parent and child executables and exact PYTHONPATH.",
            "Retain bounded import-probe stdout and stderr diagnostics.",
            "Retain bounded worker failure diagnostics in failure evidence.",
            "Keep raw worker logs outside the evidence ZIP.",
            "Stop on the first failure and perform no hidden retry.",
            "Require a separate post-merge V3 execution authorization.",
        ),
        required_failure_codes=(
            "P3_P6_PLATFORM_IDENTITY_MISMATCH",
            "P3_P6_WHEELHOUSE_INVALID",
            "P3_P6_RUNTIME_INSTALL_FAILED",
            "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT",
            "P3_P6_RUNTIME_INSTALL_TIMEOUT",
            "P3_P6_RUNTIME_INSTALL_LAUNCH_FAILED",
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
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
            "runtime_install_report_v3.json",
            "runtime_import_closure_report_v3.json",
            "p3_worker_startup_report_v3.json",
            "p4_deterministic_request_report_v3.json",
            "p5_prefix_cache_reset_report_v3.json",
            "p6_dual_worker_isolation_report_v3.json",
            "scratch_cleanup_report_v3.json",
            "p3_p6_runtime_diagnostic_summary_v3.json",
            "failure_report_v3.json",
            "bundle_manifest_v3.json",
            "human_report_v3.md",
            EVIDENCE_ZIP_NAME,
        ),
        execution_budget=ExecutionBudget(),
        next_gate=("implement_and_merge_p3_p6_runtime_process_tree_import_closure_v3"),
    )


def _template_bytes(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise P3P6V3ImplementationError(
            "P3_P6_V3_TEMPLATE_MISSING",
            "P3-P6 V3 template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    v2_template = repo_root / V2_TEMPLATE_PATH
    if (
        not v2_template.is_file()
        or v2_template.is_symlink()
        or _sha256_bytes(v2_template.read_bytes()) != V2_TEMPLATE_SHA256
    ):
        raise P3P6V3ImplementationError(
            "P3_P6_V3_V2_TEMPLATE_AUTHORITY_DRIFT",
            "V2 template authority drifted before V3 generation",
            V2_TEMPLATE_PATH.as_posix(),
        )
    raw = path.read_text(encoding="utf-8")
    replacements = {
        "__" + "NOTEBOOK_NAME" + "__": NOTEBOOK_NAME,
        "__" + "SOURCE_MAIN_COMMIT" + "__": SOURCE_MAIN_COMMIT,
        "__" + "FAILURE_ACCEPTANCE_RECORD_SHA256" + "__": (FAILURE_ACCEPTANCE_RECORD_SHA256),
        "__" + "FAILURE_ACCEPTANCE_REVIEW_SHA256" + "__": (FAILURE_ACCEPTANCE_REVIEW_SHA256),
        "__" + "V2_IMPLEMENTATION_RECORD_SHA256" + "__": (V2_IMPLEMENTATION_RECORD_SHA256),
        "__" + "MODEL_SNAPSHOT_SHA256" + "__": MODEL_SNAPSHOT_SHA256,
        "__" + "EVIDENCE_ZIP_NAME" + "__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        if raw.count(marker) != 1:
            raise P3P6V3ImplementationError(
                "P3_P6_V3_TEMPLATE_MARKER_DRIFT",
                "P3-P6 V3 template marker count drifted",
                marker,
            )
        raw = raw.replace(marker, value)
    unresolved = tuple(sorted(set(re.findall(r"__[A-Z][A-Z0-9_]+__", raw))))
    if unresolved:
        raise P3P6V3ImplementationError(
            "P3_P6_V3_TEMPLATE_PLACEHOLDER_UNRESOLVED",
            "rendered P3-P6 V3 template contains unresolved placeholders",
            ",".join(unresolved),
        )
    try:
        compile(raw, TEMPLATE_PATH.as_posix(), "exec")
    except SyntaxError as error:
        raise P3P6V3ImplementationError(
            "P3_P6_V3_TEMPLATE_COMPILE_FAILED",
            "rendered P3-P6 V3 template does not compile",
            str(error.lineno),
        ) from error
    if max(len(line) for line in raw.splitlines()) > 100:
        raise P3P6V3ImplementationError(
            "P3_P6_V3_TEMPLATE_LINE_LENGTH_DRIFT",
            "rendered P3-P6 V3 template exceeds 100 characters",
        )
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
                    "# AuraGateway P3-P6 Runtime Diagnostic V3\n",
                    "\n",
                    "Process-tree import closure and bounded runtime "
                    "diagnostics only. Runtime execution requires a "
                    "separate merged authorization.\n",
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
        raise P3P6V3ImplementationError(
            "P3_P6_V3_OPERATIONAL_AUTHORIZATION_PRESENT",
            "P3-P6 V3 operational authorization must remain absent",
            OPERATIONAL_AUTHORIZATION_PATH.as_posix(),
        )
    if (repo_root / OPERATIONAL_CONSUMPTION_PATH).exists():
        raise P3P6V3ImplementationError(
            "P3_P6_V3_OPERATIONAL_CONSUMPTION_PRESENT",
            "P3-P6 V3 operational consumption receipt must remain absent",
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
        record_id=("auragateway-cu129-p3-p6-runtime-diagnostic-v3-implementation"),
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
        next_gate=("merge_then_design_separate_p3_p6_execution_authorization_v3"),
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
            raise P3P6V3ImplementationError(
                "P3_P6_V3_GENERATED_ARTIFACT_MISSING",
                "generated P3-P6 V3 artifact is missing or unsafe",
                path.as_posix(),
            )
        if absolute.read_bytes() != expected_payload:
            raise P3P6V3ImplementationError(
                "P3_P6_V3_GENERATED_ARTIFACT_DRIFT",
                "generated P3-P6 V3 artifact differs from fresh rebuild",
                path.as_posix(),
            )
    try:
        P3P6V3Request.model_validate_json((repo_root / REQUEST_PATH).read_text())
        ArchitectureReview.model_validate_json((repo_root / REVIEW_PATH).read_text())
        ImplementationRecord.model_validate_json((repo_root / RECORD_PATH).read_text())
    except ValidationError as error:
        raise P3P6V3ImplementationError(
            "P3_P6_V3_GENERATED_CONTRACT_INVALID",
            "generated P3-P6 V3 contract validation failed",
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
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V3_GENERATED"
        elif arguments.command == "validate":
            generated = validate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V3_VALIDATED"
        else:
            raise P3P6V3ImplementationError(
                "P3_P6_V3_COMMAND_UNSUPPORTED",
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
                    "process_tree_import_closure_implemented": True,
                    "nested_import_probe_implemented": True,
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
        P3P6V3ImplementationError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, P3P6V3ImplementationError)
            else {
                "error_code": "P3_P6_V3_IMPLEMENTATION_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
