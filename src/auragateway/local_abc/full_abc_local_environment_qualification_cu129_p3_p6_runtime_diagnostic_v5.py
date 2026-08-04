"""Generate and validate P3-P6 runtime runtime diagnostic V5 assets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_MAIN_COMMIT: Final = "40b3530a763465fee0f7e27db17e9c444436ca18"

FAILURE_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v4.json"
)
FAILURE_ACCEPTANCE_RECORD_SHA256: Final = (
    "175177a65eb7d26bc7f4b82c7b96b6a077f778771718e0f9ab6a67ae54c9f228"
)
FAILURE_ACCEPTANCE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v4_review.json"
)
FAILURE_ACCEPTANCE_REVIEW_SHA256: Final = (
    "f34b76b56019e1de6e109e010cf2d26784ce5e0cebc5e0f26ad5bbdbfecf8c05"
)
V4_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v4_record.json"
)
V4_IMPLEMENTATION_RECORD_SHA256: Final = (
    "a9cc993508178c15326f95a86a18d0009f7565df703ed7d3b66251be021a6679"
)
V4_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v4.py.tmpl"
)
V4_TEMPLATE_SHA256: Final = "076b7e69123ccab235e89e581c97cc1db56084093e76074f2e7d6db23adc9c75"

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v5.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v5_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v5_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v5.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v5_record.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v5.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_v5.py"
)
ADR_PATH: Final = Path("docs/adr/2026-08-04-local-abc-cu129-p3-p6-runtime-diagnostic-v5.md")
REPORT_PATH: Final = Path("docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_V5.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_v5.md")

NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diagnostic-v5"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diag-failed-v5"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-p3-p6-runtime-evidence-v5.zip"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_v5.json"
)
OPERATIONAL_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "execution_authorization_consumption_v5.json"
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


class P3P6V5ImplementationError(RuntimeError):
    """Fail-closed V5 implementation and validation error."""

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
        raise P3P6V5ImplementationError(
            "P3_P6_V5_IMPLEMENTATION_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class AcceptedAuthority(_StrictModel):
    authority_id: Literal[
        "v4_failure_acceptance_record",
        "v4_failure_acceptance_review",
        "v4_implementation_record",
    ]
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str
    next_gate: str


class KnownV4Failure(_StrictModel):
    saved_version_id: Literal[340120168]
    lifecycle_outcome: Literal["FAILED"]
    reported_failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    failed_probe: Literal["P6"]
    evidence_disposition: Literal["ACCEPTED_DIAGNOSTIC_FAILURE"]
    first_divergence: Literal["P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"]
    completed_probes: tuple[Literal["P3"], Literal["P4"], Literal["P5"]]
    worker_1_route_transport_completed: Literal[True] = True
    worker_2_route_attempted: Literal[False] = False
    p6_complete_isolation_established: Literal[False] = False
    unchanged_replay_authorized: Literal[False] = False


class EvidenceContractHardening(_StrictModel):
    exact_line_local_backend_marker_required: Literal[True] = True
    accepted_backend_marker: Literal["Using AttentionBackendEnum.TRITON_ATTN backend."]
    combined_stream_substring_matching_permitted: Literal[False] = False
    cli_echo_as_backend_evidence_permitted: Literal[False] = False
    matched_stream_line_number_and_hash_required: Literal[True] = True
    capture_threads_finalized_before_failure_serialization: Literal[True] = True
    worker_pid_parent_pid_and_start_identity_required: Literal[True] = True
    gpu_uuid_and_pci_bus_identity_required: Literal[True] = True
    structured_teardown_report_required: Literal[True] = True
    closed_port_proof_required: Literal[True] = True
    process_tree_absence_proof_required: Literal[True] = True
    gpu_process_absence_proof_required: Literal[True] = True
    gpu_memory_return_observation_required: Literal[True] = True
    executed_runtime_script_hash_required: Literal[True] = True
    notebook_wrapper_hash_verification_required: Literal[True] = True
    maximum_gpu_memory_return_tolerance_mib: Literal[128] = 128
    typed_route_acknowledgement_required: Literal[True] = True
    model_semantics_permitted_as_p6_route_proof: Literal[False] = False
    request_attempt_checkpoint_required: Literal[True] = True
    transport_completion_checkpoint_required: Literal[True] = True
    per_worker_attempt_and_completion_counters_required: Literal[True] = True
    partial_p6_evidence_preservation_required: Literal[True] = True
    atomic_checkpoint_serialization_required: Literal[True] = True
    precise_p6_failure_taxonomy_required: Literal[True] = True
    native_origin_closure_report_required: Literal[True] = True
    model_requests_performed_derived_from_counters: Literal[True] = True


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


class P3P6V5Request(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v5-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[
        AcceptedAuthority,
        AcceptedAuthority,
        AcceptedAuthority,
    ]
    strategy: Literal["P3_P6_DIAGNOSTIC_V5_WITH_TYPED_ROUTE_CHECKPOINTS"]
    selected_backend: Literal["TRITON_ATTN"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_v4_failure: KnownV4Failure
    evidence_contract: EvidenceContractHardening
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
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v5"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_sequences(self) -> Self:
        if tuple(item.probe_id for item in self.probes) != (
            "P3",
            "P4",
            "P5",
            "P6",
        ):
            raise ValueError("P3-P6 V5 probe sequence drifted")
        if tuple(item.role for item in self.inputs) != (
            "model_snapshot",
            "vllm_runtime",
        ):
            raise ValueError("P3-P6 V5 input role order drifted")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v5-review"]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    confirmed_v4_first_divergence: Literal["P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"]
    selected_resolution: Literal["DECOUPLE_P6_ROUTE_ACKNOWLEDGEMENT_AND_PRESERVE_PARTIAL_EVIDENCE"]
    rejected_alternatives: tuple[str, ...] = Field(min_length=4)
    architecture: tuple[str, ...] = Field(min_length=15)
    diagnostic_cases: tuple[str, ...] = Field(min_length=10)
    required_failure_codes: tuple[str, ...] = Field(min_length=20)
    output_contract: tuple[str, ...]
    execution_budget: ExecutionBudget
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["implement_and_merge_p3_p6_runtime_diagnostic_v5"]


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class NotebookReceipt(ArtifactReceipt):
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v5"]
    failed_notebook_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v5"]
    code_cell_count: Literal[1]
    execution_count_present: Literal[False] = False
    output_present: Literal[False] = False
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v5-implementation"]
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
    evidence_zip_name: Literal["ag-cu129-p3-p6-runtime-evidence-v5.zip"]
    expected_runtime_outputs: tuple[str, ...]
    evidence_contract: EvidenceContractHardening
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p3_p6_execution_authorization_v5"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class GeneratedArtifacts(_StrictModel):
    request: P3P6V5Request
    review: ArchitectureReview
    notebook_bytes: bytes
    runtime_script_sha256: str
    wrapper_code_sha256: str
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
        raise P3P6V5ImplementationError(
            "P3_P6_V5_STATIC_ARTIFACT_MISSING",
            "required V5 static artifact is missing or unsafe",
            path.as_posix(),
        )
    return _receipt(path, absolute.read_bytes())


def _read_exact_json(
    repo_root: Path,
    path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise P3P6V5ImplementationError(
            "P3_P6_V5_ACCEPTED_AUTHORITY_MISSING",
            "accepted authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise P3P6V5ImplementationError(
            "P3_P6_V5_ACCEPTED_AUTHORITY_DRIFT",
            "accepted authority identity drifted",
            path.as_posix(),
        )
    observed = json.loads(payload)
    if not isinstance(observed, dict):
        raise P3P6V5ImplementationError(
            "P3_P6_V5_ACCEPTED_AUTHORITY_INVALID",
            "accepted authority root is not an object",
            path.as_posix(),
        )
    return cast(dict[str, object], observed)


def _accepted_authorities(
    repo_root: Path,
) -> tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority]:
    record = _read_exact_json(
        repo_root,
        FAILURE_ACCEPTANCE_RECORD_PATH,
        FAILURE_ACCEPTANCE_RECORD_SHA256,
    )
    review = _read_exact_json(
        repo_root,
        FAILURE_ACCEPTANCE_REVIEW_PATH,
        FAILURE_ACCEPTANCE_REVIEW_SHA256,
    )
    implementation = _read_exact_json(
        repo_root,
        V4_IMPLEMENTATION_RECORD_PATH,
        V4_IMPLEMENTATION_RECORD_SHA256,
    )
    if (
        record.get("status") != "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V4_VALID"
        or record.get("next_gate") != "design_and_merge_p3_p6_runtime_diagnostic_v5"
        or record.get("unchanged_replay_authorized") is not False
        or record.get("first_divergence") != "P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"
    ):
        raise P3P6V5ImplementationError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_DRIFT",
            "V4 failure-acceptance authority no longer permits V5 design",
            FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    if (
        review.get("status") != "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V4_CLASSIFIED"
        or review.get("evidence_disposition") != "ACCEPTED_DIAGNOSTIC_FAILURE"
        or review.get("first_divergence") != "P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"
    ):
        raise P3P6V5ImplementationError(
            "P3_P6_V5_FAILURE_REVIEW_DRIFT",
            "V4 failure review no longer matches the accepted classification",
            FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
        )
    if (
        implementation.get("status") != "IMPLEMENTED_NOT_EXECUTED"
        or implementation.get("record_id")
        != "auragateway-cu129-p3-p6-runtime-diagnostic-v4-implementation"
    ):
        raise P3P6V5ImplementationError(
            "P3_P6_V5_V4_IMPLEMENTATION_RECORD_DRIFT",
            "V4 implementation authority no longer matches the executed lineage",
            V4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    return (
        AcceptedAuthority(
            authority_id="v4_failure_acceptance_record",
            repository_path=FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
            sha256=FAILURE_ACCEPTANCE_RECORD_SHA256,
            status=str(record["status"]),
            next_gate=str(record["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="v4_failure_acceptance_review",
            repository_path=FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
            sha256=FAILURE_ACCEPTANCE_REVIEW_SHA256,
            status=str(review["status"]),
            next_gate=str(review["next_gate"]),
        ),
        AcceptedAuthority(
            authority_id="v4_implementation_record",
            repository_path=V4_IMPLEMENTATION_RECORD_PATH.as_posix(),
            sha256=V4_IMPLEMENTATION_RECORD_SHA256,
            status=str(implementation["status"]),
            next_gate=str(implementation["next_gate"]),
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
            name="ONE_WORKER_EXPLICIT_TRITON_STARTUP_WITH_LINE_LOCAL_EVIDENCE",
            pass_decision="ONE_WORKER_TRITON_STARTUP_PASSED",
            fail_decision="CURRENT_VLLM_TRITON_RUNTIME_FAILED",
            prerequisites=(
                "V5_RUNTIME_SOURCE_IDENTITY_PASSED",
                "V5_RUNTIME_INSTALL_PASSED",
                "V5_PROCESS_TREE_IMPORT_CLOSURE_PASSED",
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
            name="PREFIX_CACHE_SMOKE_AND_PROVEN_FULL_RESTART_RESET",
            pass_decision="CACHE_SMOKE_AND_RESET_PASSED",
            fail_decision="RUNTIME_WORKS_BUT_PRD_OBSERVABILITY_CONTRACT_FAILED",
            prerequisites=("P4_PASSED",),
            maximum_model_requests=3,
            maximum_worker_starts=2,
        ),
        ProbeDefinition(
            probe_id="P6",
            name="DUAL_WORKER_TYPED_ROUTE_AND_METRIC_ISOLATION",
            pass_decision="DUAL_WORKER_DIAGNOSTIC_PASSED",
            fail_decision="SINGLE_WORKER_COMPATIBLE_DUAL_WORKER_CONTRACT_FAILED",
            prerequisites=("P5_PASSED",),
            maximum_model_requests=5,
            maximum_worker_starts=3,
        ),
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "V5 has not been executed.",
        "No V5 runtime authorization is issued by this implementation.",
        "The V5 runtime-harness changes are repository validated only.",
        "P3, P4 and P5 remain accepted only from the V4 runtime lineage.",
        "Complete P6 route and metric isolation is not established.",
        "Worker 2 routed-request completion is not established.",
        "Complete native-library and ABI provenance is not established.",
        "A saved-version V5 notebook byte identity is not established.",
        "Model quality is not evaluated by P6.",
        "A/B/C benchmark trajectories are not executed.",
        "Latency and cost improvements are not claimed.",
        "Customer-data readiness is not claimed.",
        "Deployment and production readiness are not claimed.",
    )


def _request(
    authorities: tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority],
) -> P3P6V5Request:
    return P3P6V5Request(
        request_id="auragateway-cu129-p3-p6-runtime-diagnostic-v5-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        strategy="P3_P6_DIAGNOSTIC_V5_WITH_TYPED_ROUTE_CHECKPOINTS",
        selected_backend="TRITON_ATTN",
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        known_v4_failure=KnownV4Failure(
            saved_version_id=340120168,
            lifecycle_outcome="FAILED",
            reported_failure_code="P3_P6_DUAL_WORKER_ISOLATION_FAILED",
            failed_probe="P6",
            evidence_disposition="ACCEPTED_DIAGNOSTIC_FAILURE",
            first_divergence=("P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"),
            completed_probes=("P3", "P4", "P5"),
        ),
        evidence_contract=EvidenceContractHardening(
            accepted_backend_marker=("Using AttentionBackendEnum.TRITON_ATTN backend.")
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
        next_gate=("merge_then_design_separate_p3_p6_execution_authorization_v5"),
        non_claims=_non_claims(),
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-cu129-p3-p6-runtime-diagnostic-v5-review",
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        confirmed_v4_first_divergence=("P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"),
        selected_resolution=("DECOUPLE_P6_ROUTE_ACKNOWLEDGEMENT_AND_PRESERVE_PARTIAL_EVIDENCE"),
        rejected_alternatives=(
            "Do not replay V4 unchanged.",
            "Do not improve the P6 prompt and preserve the brittle boundary.",
            "Do not retry malformed model output.",
            "Do not use model semantics as evidence of route realization.",
            "Do not issue V5 runtime authority in this implementation tranche.",
        ),
        architecture=(
            "Bind V5 to the accepted V4 failure record and review.",
            "Bind V5 to the exact V4 implementation record.",
            "Preserve the accepted V4 P3, P4 and P5 runtime contracts.",
            "Keep exact structured-output validation in P4 only.",
            "Derive P6 route acknowledgement from transport and metrics.",
            "Persist a route-attempt checkpoint before every P6 POST.",
            "Persist transport completion before response-envelope validation.",
            "Track per-worker attempted and completed request counters.",
            "Preserve every completed checkpoint after terminal failure.",
            "Write checkpoint and terminal JSON atomically.",
            "Separate process, GPU, port, transport and metric decisions.",
            "Use precise worker-specific P6 failure codes.",
            "Derive model_requests_performed from the action counter.",
            "Record loaded native origins for both worker process trees.",
            "Reject CUDA toolkit stub origins.",
            "Keep raw prompts and raw model outputs out of evidence.",
            "Preserve stop-on-first-failure and zero hidden retries.",
            "Preserve worker teardown and scratch cleanup proof.",
            "Wrap the runtime source in a hash-verifying notebook cell.",
            "Require a separate post-merge V5 execution authorization.",
        ),
        diagnostic_cases=(
            "P6 content mismatch does not invalidate transport completion",
            "P6 never calls structured-response equality validation",
            "P4 retains exact structured-response validation",
            "request attempt is checkpointed before transport",
            "failed transport preserves attempted true completed false",
            "successful transport preserves completed response evidence",
            "worker 1 metric attribution excludes worker 2",
            "worker 2 metric attribution excludes worker 1",
            "per-worker counters reconcile to the global request counter",
            "terminal stubs derive model request activity from counters",
            "partial P6 checkpoints survive terminal failure",
            "native origin closure rejects a CUDA stub path",
            "checkpoint serialization is atomic",
        ),
        required_failure_codes=(
            "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH",
            "P3_P6_PLATFORM_IDENTITY_MISMATCH",
            "P3_P6_WHEELHOUSE_INVALID",
            "P3_P6_RUNTIME_INSTALL_FAILED",
            "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT",
            "P3_P6_RUNTIME_INSTALL_TIMEOUT",
            "P3_P6_RUNTIME_INSTALL_LAUNCH_FAILED",
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
            "P3_P6_MODEL_IDENTITY_MISMATCH",
            "P3_P6_EXPLICIT_BACKEND_NOT_REALIZED",
            "P3_P6_WORKER_STARTUP_FAILED",
            "P3_P6_MODEL_INVENTORY_MISMATCH",
            "P3_P6_REQUEST_FAILED",
            "P3_P6_METRIC_SEMANTIC_UNAVAILABLE",
            "P3_P6_CACHE_REUSE_NOT_OBSERVED",
            "P3_P6_RESET_NOT_PROVEN",
            "P6_WORKER_2_STARTUP_FAILED",
            "P6_PROCESS_ISOLATION_FAILED",
            "P6_GPU_ISOLATION_FAILED",
            "P6_PORT_ISOLATION_FAILED",
            "P6_WORKER_1_ROUTE_TRANSPORT_FAILED",
            "P6_WORKER_1_RESPONSE_ENVELOPE_INVALID",
            "P6_WORKER_1_METRIC_ATTRIBUTION_FAILED",
            "P6_WORKER_2_ROUTE_TRANSPORT_FAILED",
            "P6_WORKER_2_RESPONSE_ENVELOPE_INVALID",
            "P6_WORKER_2_METRIC_ATTRIBUTION_FAILED",
            "P6_REQUEST_COUNTER_RECONCILIATION_FAILED",
            "P6_CHECKPOINT_SERIALIZATION_FAILED",
            "P3_P6_ACTION_BUDGET_EXCEEDED",
            "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
            "P3_P6_WORKER_TEARDOWN_FAILED",
            "P3_P6_SCRATCH_CLEANUP_FAILED",
        ),
        output_contract=(
            "runtime_source_identity_report_v5.json",
            "runtime_install_report_v5.json",
            "runtime_import_closure_report_v5.json",
            "runtime_native_origin_report_v5.json",
            "p3_worker_startup_report_v5.json",
            "p4_deterministic_request_report_v5.json",
            "p5_prefix_cache_reset_report_v5.json",
            "p6_stage_checkpoint_report_v5.json",
            "p6_dual_worker_isolation_report_v5.json",
            "worker_teardown_report_v5.json",
            "scratch_cleanup_report_v5.json",
            "p3_p6_runtime_diagnostic_summary_v5.json",
            "failure_report_v5.json",
            "bundle_manifest_v5.json",
            "human_report_v5.md",
            EVIDENCE_ZIP_NAME,
        ),
        execution_budget=ExecutionBudget(),
        next_gate="implement_and_merge_p3_p6_runtime_diagnostic_v5",
    )


def _template_bytes(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise P3P6V5ImplementationError(
            "P3_P6_V5_TEMPLATE_MISSING",
            "P3-P6 V5 template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    v4_template = repo_root / V4_TEMPLATE_PATH
    if (
        not v4_template.is_file()
        or v4_template.is_symlink()
        or _sha256_bytes(v4_template.read_bytes()) != V4_TEMPLATE_SHA256
    ):
        raise P3P6V5ImplementationError(
            "P3_P6_V5_V4_TEMPLATE_AUTHORITY_DRIFT",
            "V4 template authority drifted before V5 generation",
            V4_TEMPLATE_PATH.as_posix(),
        )
    raw = path.read_text(encoding="utf-8")
    replacements = {
        "__" + "NOTEBOOK_NAME" + "__": NOTEBOOK_NAME,
        "__" + "SOURCE_MAIN_COMMIT" + "__": SOURCE_MAIN_COMMIT,
        "__" + "FAILURE_ACCEPTANCE_RECORD_SHA256" + "__": (FAILURE_ACCEPTANCE_RECORD_SHA256),
        "__" + "FAILURE_ACCEPTANCE_REVIEW_SHA256" + "__": (FAILURE_ACCEPTANCE_REVIEW_SHA256),
        "__" + "V4_IMPLEMENTATION_RECORD_SHA256" + "__": (V4_IMPLEMENTATION_RECORD_SHA256),
        "__" + "MODEL_SNAPSHOT_SHA256" + "__": MODEL_SNAPSHOT_SHA256,
        "__" + "EVIDENCE_ZIP_NAME" + "__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        if raw.count(marker) != 1:
            raise P3P6V5ImplementationError(
                "P3_P6_V5_TEMPLATE_MARKER_DRIFT",
                "P3-P6 V5 template marker count drifted",
                marker,
            )
        raw = raw.replace(marker, value)
    unresolved = tuple(sorted(set(re.findall(r"__[A-Z][A-Z0-9_]+__", raw))))
    if unresolved:
        raise P3P6V5ImplementationError(
            "P3_P6_V5_TEMPLATE_PLACEHOLDER_UNRESOLVED",
            "rendered P3-P6 V5 template contains unresolved placeholders",
            ",".join(unresolved),
        )
    try:
        compile(raw, TEMPLATE_PATH.as_posix(), "exec")
    except SyntaxError as error:
        raise P3P6V5ImplementationError(
            "P3_P6_V5_TEMPLATE_COMPILE_FAILED",
            "rendered P3-P6 V5 template does not compile",
            str(error.lineno),
        ) from error
    if max(len(line) for line in raw.splitlines()) > 100:
        raise P3P6V5ImplementationError(
            "P3_P6_V5_TEMPLATE_LINE_LENGTH_DRIFT",
            "rendered P3-P6 V5 template exceeds 100 characters",
        )
    return raw.encode("utf-8")


def _wrapper_code(runtime_source: bytes) -> tuple[bytes, str, str]:
    runtime_sha256 = _sha256_bytes(runtime_source)
    encoded = base64.b64encode(runtime_source).decode("ascii")
    chunks = tuple(encoded[index : index + 76] for index in range(0, len(encoded), 76))
    lines = [
        "import base64 as _ag_base64",
        "import hashlib as _ag_hashlib",
        "",
        "_AG_RUNTIME_B64 = (",
        *[f'    "{chunk}"' for chunk in chunks],
        ")",
        "_AG_RUNTIME_SOURCE = _ag_base64.b64decode(",
        '    "".join(_AG_RUNTIME_B64)',
        ').decode("utf-8")',
        f'_AG_EXPECTED_RUNTIME_SHA256 = "{runtime_sha256}"',
        "_AG_OBSERVED_RUNTIME_SHA256 = _ag_hashlib.sha256(",
        '    _AG_RUNTIME_SOURCE.encode("utf-8")',
        ").hexdigest()",
        "if _AG_OBSERVED_RUNTIME_SHA256 != _AG_EXPECTED_RUNTIME_SHA256:",
        '    raise RuntimeError("runtime script identity mismatch")',
        "EXECUTED_RUNTIME_SCRIPT_SHA256 = _AG_OBSERVED_RUNTIME_SHA256",
        "exec(",
        '    compile(_AG_RUNTIME_SOURCE, "<auragateway-v5-runtime>", "exec"),',
        "    globals(),",
        "    globals(),",
        ")",
    ]
    wrapper = ("\n".join(lines) + "\n").encode("utf-8")
    if max(len(line) for line in wrapper.decode("utf-8").splitlines()) > 100:
        raise P3P6V5ImplementationError(
            "P3_P6_V5_NOTEBOOK_WRAPPER_LINE_LENGTH_DRIFT",
            "V5 notebook wrapper exceeds 100 characters",
        )
    compile(wrapper.decode("utf-8"), NOTEBOOK_PATH.as_posix(), "exec")
    return wrapper, runtime_sha256, _sha256_bytes(wrapper)


def _notebook_bytes(
    rendered_template: bytes,
) -> tuple[bytes, str, str]:
    wrapper, runtime_sha256, wrapper_sha256 = _wrapper_code(rendered_template)
    source = wrapper.decode("utf-8")
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
                    "# AuraGateway P3-P6 Runtime Diagnostic V5\n",
                    "\n",
                    "Hash-verified runtime source, line-local backend evidence, "
                    "capture finalization, worker identity and teardown proof. "
                    "Runtime execution requires separate merged authorization.\n",
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
    return (
        _canonical_json(payload).encode("utf-8"),
        runtime_sha256,
        wrapper_sha256,
    )


def build_generated(repo_root: Path) -> GeneratedArtifacts:
    if (repo_root / OPERATIONAL_AUTHORIZATION_PATH).exists():
        raise P3P6V5ImplementationError(
            "P3_P6_V5_OPERATIONAL_AUTHORIZATION_PRESENT",
            "P3-P6 V5 operational authorization must remain absent",
            OPERATIONAL_AUTHORIZATION_PATH.as_posix(),
        )
    if (repo_root / OPERATIONAL_CONSUMPTION_PATH).exists():
        raise P3P6V5ImplementationError(
            "P3_P6_V5_OPERATIONAL_CONSUMPTION_PRESENT",
            "P3-P6 V5 operational consumption receipt must remain absent",
            OPERATIONAL_CONSUMPTION_PATH.as_posix(),
        )
    authorities = _accepted_authorities(repo_root)
    request = _request(authorities)
    review = _review()
    request_bytes = request.canonical_json().encode("utf-8")
    review_bytes = review.canonical_json().encode("utf-8")
    rendered_template = _template_bytes(repo_root)
    (
        notebook_bytes,
        runtime_script_sha256,
        wrapper_code_sha256,
    ) = _notebook_bytes(rendered_template)
    notebook_payload = json.loads(notebook_bytes)
    code_cells = [item for item in notebook_payload["cells"] if item["cell_type"] == "code"]
    record = ImplementationRecord(
        record_id=("auragateway-cu129-p3-p6-runtime-diagnostic-v5-implementation"),
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
            runtime_script_sha256=runtime_script_sha256,
            wrapper_code_sha256=wrapper_code_sha256,
        ),
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        expected_runtime_outputs=review.output_contract,
        evidence_contract=EvidenceContractHardening(
            accepted_backend_marker=("Using AttentionBackendEnum.TRITON_ATTN backend.")
        ),
        execution_budget=ExecutionBudget(),
        safety=ImplementationSafety(),
        next_gate=("merge_then_design_separate_p3_p6_execution_authorization_v5"),
        non_claims=_non_claims(),
    )
    return GeneratedArtifacts(
        request=request,
        review=review,
        notebook_bytes=notebook_bytes,
        runtime_script_sha256=runtime_script_sha256,
        wrapper_code_sha256=wrapper_code_sha256,
        record=record,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise P3P6V5ImplementationError(
            "P3_P6_V5_TEMPORARY_ARTIFACT_PRESENT",
            "temporary V5 output already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    temporary.replace(path)


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
            raise P3P6V5ImplementationError(
                "P3_P6_V5_GENERATED_ARTIFACT_MISSING",
                "generated P3-P6 V5 artifact is missing or unsafe",
                path.as_posix(),
            )
        if absolute.read_bytes() != expected_payload:
            raise P3P6V5ImplementationError(
                "P3_P6_V5_GENERATED_ARTIFACT_DRIFT",
                "generated P3-P6 V5 artifact differs from fresh rebuild",
                path.as_posix(),
            )
    try:
        P3P6V5Request.model_validate_json((repo_root / REQUEST_PATH).read_text(encoding="utf-8"))
        ArchitectureReview.model_validate_json(
            (repo_root / REVIEW_PATH).read_text(encoding="utf-8")
        )
        ImplementationRecord.model_validate_json(
            (repo_root / RECORD_PATH).read_text(encoding="utf-8")
        )
    except ValidationError as error:
        raise P3P6V5ImplementationError(
            "P3_P6_V5_GENERATED_CONTRACT_INVALID",
            "generated P3-P6 V5 contract validation failed",
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
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V5_GENERATED"
        elif arguments.command == "validate":
            generated = validate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_V5_VALIDATED"
        else:
            raise P3P6V5ImplementationError(
                "P3_P6_V5_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": generated.record.status,
                    "source_main_commit": generated.record.source_main_commit,
                    "notebook_sha256": generated.record.notebook.sha256,
                    "runtime_script_sha256": (generated.record.notebook.runtime_script_sha256),
                    "wrapper_code_sha256": (generated.record.notebook.wrapper_code_sha256),
                    "candidate_path_count": len(CANDIDATE_PATHS),
                    "typed_route_checkpointing_implemented": True,
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
        P3P6V5ImplementationError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, P3P6V5ImplementationError)
            else {
                "error_code": "P3_P6_V5_IMPLEMENTATION_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
