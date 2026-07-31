"""Generate and validate the bounded P3-P6 runtime diagnostic V1 assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_COMMIT: Final = "58a73c38c22337219899018d655e00366d790413"

OPTION_C_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_option_c_runtime_diagnostic_decision_v1.json"
)
OPTION_C_SHA256: Final = "6297b48f64811dbd1b86c850b0fbd66a4142d174d69897b673eb5748663cc418"

Q6_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_explicit_triton_attention_backend_"
    "execution_acceptance_v1.json"
)
Q6_ACCEPTANCE_SHA256: Final = "9928243d34edd82996a3120f724df6c8bf4912e8b8790b8abc8926eccca006c1"

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v1.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v1_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v1_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v1.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v1_record.json"
)

NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diagnostic-v1"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diag-failed-v1"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-p3-p6-runtime-evidence-v1.zip"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
EXPECTED_RUFF_VERSION: Final = "0.15.21"

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v1.json"
)
OPERATIONAL_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_consumption_v1.json"
)

GENERATED_PATHS: Final = (
    REQUEST_PATH,
    REVIEW_PATH,
    NOTEBOOK_PATH,
    RECORD_PATH,
)


class P3P6ImplementationError(RuntimeError):
    """Fail-closed implementation and validation error."""

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
        raise P3P6ImplementationError(
            "P3_P6_IMPLEMENTATION_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(LocalABCContract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AcceptedAuthority(_StrictModel):
    authority_id: Literal["option_c_decision", "q6_execution_acceptance"]
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


class P3P6Request(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v1-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[AcceptedAuthority, AcceptedAuthority]
    strategy: Literal["OPTION_C_SEQUENTIAL_P3_P6_DIAGNOSTIC"]
    selected_backend: Literal["TRITON_ATTN"]
    backend_selection_mechanism: Literal["EXPLICIT_VLLM_ATTENTION_BACKEND_CLI_ARGUMENT"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    probes: tuple[
        ProbeDefinition,
        ProbeDefinition,
        ProbeDefinition,
        ProbeDefinition,
    ]
    inputs: tuple[InputBoundary, InputBoundary]
    execution_budget: ExecutionBudget
    stop_on_first_failure: Literal[True] = True
    partial_evidence_required: Literal[True] = True
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v1"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_exact_sequence(self) -> Self:
        if tuple(item.probe_id for item in self.probes) != (
            "P3",
            "P4",
            "P5",
            "P6",
        ):
            raise ValueError("P3-P6 probe sequence drifted")
        if tuple(item.role for item in self.inputs) != (
            "model_snapshot",
            "vllm_runtime",
        ):
            raise ValueError("P3-P6 input role order drifted")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v1-review"]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    first_divergence_from_legacy_adapter: Literal["LEGACY_ADAPTER_STARTS_TWO_WORKERS_BEFORE_P3"]
    legacy_adapter_reuse_decision: Literal[
        "REUSE_HELPERS_AND_CONTRACTS_NOT_MONOLITHIC_CAPTURE_FLOW"
    ]
    architecture: tuple[str, ...] = Field(min_length=10)
    required_failure_codes: tuple[str, ...] = Field(min_length=12)
    output_contract: tuple[str, ...]
    execution_budget: ExecutionBudget
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["implement_and_merge_p3_p6_runtime_diagnostic_v1"]


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class NotebookReceipt(ArtifactReceipt):
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v1"]
    failed_notebook_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v1"]
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
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v1-implementation"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[AcceptedAuthority, AcceptedAuthority]
    request: ArtifactReceipt
    review: ArtifactReceipt
    template: ArtifactReceipt
    notebook: NotebookReceipt
    evidence_zip_name: Literal["ag-cu129-p3-p6-runtime-evidence-v1.zip"]
    expected_runtime_outputs: tuple[str, ...]
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v1"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class GeneratedArtifacts(_StrictModel):
    request: P3P6Request
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


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise P3P6ImplementationError(
            "P3_P6_TEMPORARY_PATH_PRESENT",
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
        raise P3P6ImplementationError(
            "P3_P6_ACCEPTED_AUTHORITY_MISSING",
            "accepted authority is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise P3P6ImplementationError(
            "P3_P6_ACCEPTED_AUTHORITY_DRIFT",
            "accepted authority identity drifted",
            relative_path.as_posix(),
        )
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P3P6ImplementationError(
            "P3_P6_ACCEPTED_AUTHORITY_INVALID",
            "accepted authority is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(raw, dict):
        raise P3P6ImplementationError(
            "P3_P6_ACCEPTED_AUTHORITY_ROOT_INVALID",
            "accepted authority root must be one object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], raw)


def _accepted_authorities(
    repo_root: Path,
) -> tuple[AcceptedAuthority, AcceptedAuthority]:
    option_c = _read_bound(repo_root, OPTION_C_PATH, OPTION_C_SHA256)
    q6 = _read_bound(repo_root, Q6_ACCEPTANCE_PATH, Q6_ACCEPTANCE_SHA256)
    if (
        option_c.get("decision") != "APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC"
        or option_c.get("next_gate") != "implement_p0_p2_platform_diagnostic_assets"
    ):
        raise P3P6ImplementationError(
            "P3_P6_OPTION_C_AUTHORITY_DRIFT",
            "Option C decision no longer authorizes the staged runtime sequence",
            OPTION_C_PATH.as_posix(),
        )
    if (
        q6.get("status") != "EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_VALID"
        or q6.get("next_gate") != "design_and_implement_p3_p6_runtime_diagnostic_v1"
        or q6.get("q6_execution_accepted") is not True
        or q6.get("authorization_lifecycle_closed") is not True
        or q6.get("unchanged_replay_authorized") is not False
    ):
        raise P3P6ImplementationError(
            "P3_P6_Q6_AUTHORITY_DRIFT",
            "Q6 acceptance no longer authorizes P3-P6 implementation",
            Q6_ACCEPTANCE_PATH.as_posix(),
        )
    return (
        AcceptedAuthority(
            authority_id="option_c_decision",
            repository_path=OPTION_C_PATH.as_posix(),
            sha256=OPTION_C_SHA256,
            status=str(option_c["decision"]),
            next_gate=str(option_c["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="q6_execution_acceptance",
            repository_path=Q6_ACCEPTANCE_PATH.as_posix(),
            sha256=Q6_ACCEPTANCE_SHA256,
            status=str(q6["status"]),
            next_gate=str(q6["next_gate"]),
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
            prerequisites=("Q6_ACCEPTED_CONSUMED",),
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
        "P3-P6 have not been executed.",
        "No runtime authorization is issued by this implementation.",
        "Future Kaggle image equivalence is not established.",
        "Model quality is not evaluated.",
        "A/B/C benchmark trajectories are not executed.",
        "Latency improvement is not claimed.",
        "Cost improvement is not claimed.",
        "Quality non-inferiority is not claimed.",
        "Customer-data readiness is not claimed.",
        "Deployment is not claimed.",
        "Production readiness is not claimed.",
    )


def _request(
    authorities: tuple[AcceptedAuthority, AcceptedAuthority],
) -> P3P6Request:
    return P3P6Request(
        request_id="auragateway-cu129-p3-p6-runtime-diagnostic-v1-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        strategy="OPTION_C_SEQUENTIAL_P3_P6_DIAGNOSTIC",
        selected_backend="TRITON_ATTN",
        backend_selection_mechanism=("EXPLICIT_VLLM_ATTENTION_BACKEND_CLI_ARGUMENT"),
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
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
        next_gate=("merge_then_design_separate_p3_p6_execution_authorization_v1"),
        non_claims=_non_claims(),
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-cu129-p3-p6-runtime-diagnostic-v1-review",
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        first_divergence_from_legacy_adapter=("LEGACY_ADAPTER_STARTS_TWO_WORKERS_BEFORE_P3"),
        legacy_adapter_reuse_decision=("REUSE_HELPERS_AND_CONTRACTS_NOT_MONOLITHIC_CAPTURE_FLOW"),
        architecture=(
            "Execute P3, P4, P5, and P6 sequentially.",
            "Stop immediately after the first failed probe.",
            "Preserve completed probe evidence after failure.",
            "Select TRITON_ATTN using the explicit vLLM CLI argument.",
            "Reject automatic backend selection and silent fallback.",
            "Start only worker_1 during P3.",
            "Use one deterministic synthetic request during P4.",
            "Require valid JSON output matching the synthetic request object.",
            "Enforce action budgets before every bounded side effect.",
            "Emit one explicit failure code from the reviewed taxonomy.",
            "Use token-level cache metrics during P5.",
            "Require a full process restart for reset.",
            "Start worker_2 only after P5 passes.",
            "Prove process, GPU, port, route, and metric isolation in P6.",
            "Write raw prompt and output hashes only, never raw payloads.",
            "Require a separate post-merge runtime authorization.",
        ),
        required_failure_codes=(
            "P3_P6_PLATFORM_IDENTITY_MISMATCH",
            "P3_P6_WHEELHOUSE_INVALID",
            "P3_P6_RUNTIME_INSTALL_FAILED",
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
        ),
        output_contract=(
            "p3_worker_startup_report_v1.json",
            "p4_deterministic_request_report_v1.json",
            "p5_prefix_cache_reset_report_v1.json",
            "p6_dual_worker_isolation_report_v1.json",
            "p3_p6_runtime_diagnostic_summary_v1.json",
            "failure_report_v1.json",
            "bundle_manifest_v1.json",
            "human_report_v1.md",
            EVIDENCE_ZIP_NAME,
        ),
        execution_budget=ExecutionBudget(),
        next_gate="implement_and_merge_p3_p6_runtime_diagnostic_v1",
    )


def _template_bytes(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise P3P6ImplementationError(
            "P3_P6_TEMPLATE_MISSING",
            "P3-P6 template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    raw = path.read_text(encoding="utf-8")
    replacements = {
        "__" + "NOTEBOOK_NAME" + "__": NOTEBOOK_NAME,
        "__" + "SOURCE_MAIN_COMMIT" + "__": SOURCE_MAIN_COMMIT,
        "__" + "Q6_ACCEPTANCE_SHA256" + "__": Q6_ACCEPTANCE_SHA256,
        "__" + "OPTION_C_DECISION_SHA256" + "__": OPTION_C_SHA256,
        "__" + "MODEL_SNAPSHOT_SHA256" + "__": MODEL_SNAPSHOT_SHA256,
        "__" + "EVIDENCE_ZIP_NAME" + "__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        if raw.count(marker) != 1:
            raise P3P6ImplementationError(
                "P3_P6_TEMPLATE_MARKER_DRIFT",
                "P3-P6 template marker count drifted",
                marker,
            )
        raw = raw.replace(marker, value)
    try:
        compile(raw, TEMPLATE_PATH.as_posix(), "exec")
    except SyntaxError as error:
        raise P3P6ImplementationError(
            "P3_P6_TEMPLATE_COMPILE_FAILED",
            "rendered P3-P6 template does not compile",
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
                    "# AuraGateway P3-P6 Runtime Diagnostic V1\n",
                    "\n",
                    "Implementation only. Runtime execution requires a "
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
        raise P3P6ImplementationError(
            "P3_P6_OPERATIONAL_AUTHORIZATION_PRESENT",
            "P3-P6 operational authorization must remain absent",
            OPERATIONAL_AUTHORIZATION_PATH.as_posix(),
        )
    if (repo_root / OPERATIONAL_CONSUMPTION_PATH).exists():
        raise P3P6ImplementationError(
            "P3_P6_OPERATIONAL_CONSUMPTION_PRESENT",
            "P3-P6 operational consumption receipt must remain absent",
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
        record_id=("auragateway-cu129-p3-p6-runtime-diagnostic-v1-implementation"),
        status="IMPLEMENTED_NOT_EXECUTED",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        request=_receipt(REQUEST_PATH, request_bytes),
        review=_receipt(REVIEW_PATH, review_bytes),
        template=_receipt(TEMPLATE_PATH, (repo_root / TEMPLATE_PATH).read_bytes()),
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
        next_gate=("merge_then_design_separate_p3_p6_execution_authorization_v1"),
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
            raise P3P6ImplementationError(
                "P3_P6_GENERATED_ARTIFACT_MISSING",
                "generated P3-P6 artifact is missing or unsafe",
                path.as_posix(),
            )
        if absolute.read_bytes() != expected_payload:
            raise P3P6ImplementationError(
                "P3_P6_GENERATED_ARTIFACT_DRIFT",
                "generated P3-P6 artifact differs from fresh rebuild",
                path.as_posix(),
            )
    try:
        P3P6Request.model_validate_json((repo_root / REQUEST_PATH).read_text())
        ArchitectureReview.model_validate_json((repo_root / REVIEW_PATH).read_text())
        ImplementationRecord.model_validate_json((repo_root / RECORD_PATH).read_text())
    except ValidationError as error:
        raise P3P6ImplementationError(
            "P3_P6_GENERATED_CONTRACT_INVALID",
            "generated P3-P6 contract validation failed",
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
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V1_GENERATED"
        elif arguments.command == "validate":
            generated = validate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V1_VALIDATED"
        else:
            raise P3P6ImplementationError(
                "P3_P6_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": generated.record.status,
                    "source_main_commit": generated.record.source_main_commit,
                    "notebook_sha256": generated.record.notebook.sha256,
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
        P3P6ImplementationError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, P3P6ImplementationError)
            else {
                "error_code": "P3_P6_IMPLEMENTATION_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
