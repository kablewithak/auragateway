"""Generate and validate P5/P6 Successor Runtime Qualification V1 assets."""

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

SOURCE_MAIN_COMMIT: Final = "1ff193c386a2f21738299ad0ece7cc16cafc5a11"

SUCCESSOR_REVIEW_AUTHORITY_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_review.json"
)
SUCCESSOR_REVIEW_AUTHORITY_SHA256: Final = (
    "7819597c04987d4a2c0165be46f4eb327baf67f2b6605a248b1daaffd5bfb8be"
)
PREIMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_preimplementation_reconnaissance_v1_review.json"
)
PREIMPLEMENTATION_REVIEW_SHA256: Final = (
    "191a82d1de8862d1ee1968f162166083c5fc63e09d1f1a27acf924a1264b5f2f"
)
PREIMPLEMENTATION_POLICY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_preimplementation_reconnaissance_v1_policy.json"
)
PREIMPLEMENTATION_POLICY_SHA256: Final = (
    "0cc94056577f060b0876e8d3dd2d4991a0755ac6324405514b30f1701d705931"
)
P4_REQUEST_AUTHORITY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_v2_request.json"
)
P4_REQUEST_AUTHORITY_SHA256: Final = (
    "b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1"
)
V5_REQUEST_AUTHORITY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v5_request.json"
)
V5_REQUEST_AUTHORITY_SHA256: Final = (
    "b9eb7e968e79df97c4892f1dc6b19a245ac8fe61764c5dd9ecc6076ec7e32e5b"
)
P4_TEMPLATE_AUTHORITY_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"
)
P4_TEMPLATE_AUTHORITY_SHA256: Final = (
    "93bdcf4a2ab3f4b4a07b688b8d6f9dc295ba3edcbb0b9bd63da8967393811441"
)
V5_TEMPLATE_AUTHORITY_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v5.py.tmpl"
)
V5_TEMPLATE_AUTHORITY_SHA256: Final = (
    "c9aa80c8c92b712e127c81e8f929ed98195f7fa0a824d6559328d2cb2c34d454"
)

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_successor_runtime_qualification_v1.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_runtime_qualification_v1_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_runtime_qualification_v1_implementation_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_p5_p6_successor_runtime_qualification_v1.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_record.json"
)
SOURCE_PATH: Final = Path("src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1.py")
TEST_PATH: Final = Path("tests/unit/local_abc/test_p5_p6_successor_runtime_qualification_v1.py")
ADR_PATH: Final = Path(
    "docs/adr/2026-08-07-local-abc-p5-p6-successor-runtime-qualification-v1-implementation.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Successor_Runtime_Qualification_V1_Implementation.md"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_p5_p6_successor_runtime_qualification_v1.md")

NOTEBOOK_NAME: Final = "ag-p5-p6-successor-runtime-qual-v1"
FAILED_NOTEBOOK_NAME: Final = "ag-p5-p6-successor-runtime-failed-v1"
EVIDENCE_ZIP_NAME: Final = "ag-p5-p6-successor-runtime-evidence-v1.zip"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
SERVED_MODEL_NAME: Final = "local-qwen2.5-0.5b-instruct"
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_v1.json"
)
OPERATIONAL_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_consumption_v1.json"
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

V4_PROMPT: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
V5_SYNTHETIC_CACHE_CONTEXT: Final = (
    "AuraGateway deterministic prefix-cache reliability probe. "
    "This text is synthetic, contains no customer data, and must remain "
    "byte-identical across requests. "
) * 24 + (
    "For structured probes, return only the exact JSON object supplied in the final user message."
)
SYNTHETIC_ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
EXPECTED_OBJECT: Final = {"probe": "cold", "value": 1}


class SuccessorImplementationError(RuntimeError):
    """Fail-closed successor implementation and validation error."""

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
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_IMPLEMENTATION_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class AcceptedAuthority(_StrictModel):
    authority_id: str = Field(min_length=1)
    repository_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    purpose: str = Field(min_length=20)


class SelectedP4Contract(_StrictModel):
    case_id: Literal["A"] = "A"
    prompt_variant: Literal["V4"] = "V4"
    repetition_penalty: float = Field(default=1.1, ge=1.1, le=1.1, strict=True)
    output_mode: Literal["UNCONSTRAINED"] = "UNCONSTRAINED"
    exact_object_required: Literal[True] = True
    json_schema_required: Literal[False] = False
    reselection_permitted: Literal[False] = False
    p4_canary_reused_as_p5_cold_baseline: Literal[True] = True


class RequestIdentityContract(_StrictModel):
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shared_messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible_prefix_messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p4_canary_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_cold_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_warm_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_post_restart_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p6_worker_1_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p6_worker_2_logical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_cold_reuses_p4_canary: Literal[True] = True
    all_runtime_payloads_identical: Literal[True] = True

    @model_validator(mode="after")
    def validate_p4_p5_cold_identity(self) -> Self:
        if self.p4_canary_logical_sha256 != self.p5_cold_logical_sha256:
            raise ValueError("P4 canary no longer equals the P5 cold logical request")
        return self


class StageBudget(_StrictModel):
    stage: Literal["P3_CANARY", "P4_CANARY", "P5", "P6"]
    additional_model_requests: int = Field(ge=0, le=2)
    additional_worker_starts: int = Field(ge=0, le=1)
    additional_model_loads: int = Field(ge=0, le=1)


class ExecutionBudget(_StrictModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[5] = 5
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    hidden_retries_permitted: Literal[0] = 0
    replacement_workers_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class EvidenceContract(_StrictModel):
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


class InputBoundary(_StrictModel):
    role: Literal["model_snapshot", "vllm_runtime"]
    artifact_format: Literal[
        "hugging_face_snapshot_directory",
        "python_wheelhouse_directory",
    ]
    exact_sha256_required: Literal[True] = True
    network_fallback_permitted: Literal[False] = False


class SuccessorRequest(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-p5-p6-successor-runtime-qualification-v1-request"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[AcceptedAuthority, ...] = Field(min_length=7, max_length=7)
    strategy: Literal["P4_V2_ENVIRONMENT_PLUS_V5_P5_P6_SUCCESSOR_COMPOSITION"]
    composition_decision: Literal["GO_FOR_SUCCESSOR_IMPLEMENTATION_WITH_FROZEN_COMPOSITION_RULES"]
    selected_backend: Literal["TRITON_ATTN"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_p4_contract: SelectedP4Contract
    request_identities: RequestIdentityContract
    stage_budgets: tuple[StageBudget, StageBudget, StageBudget, StageBudget]
    execution_budget: ExecutionBudget
    evidence_contract: EvidenceContract
    inputs: tuple[InputBoundary, InputBoundary]
    stop_on_first_failure: Literal[True] = True
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p5_p6_successor_execution_authorization_v1"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if tuple(item.stage for item in self.stage_budgets) != (
            "P3_CANARY",
            "P4_CANARY",
            "P5",
            "P6",
        ):
            raise ValueError("successor stage order drifted")
        if sum(item.additional_model_requests for item in self.stage_budgets) != 5:
            raise ValueError("successor request budget no longer totals five")
        if sum(item.additional_worker_starts for item in self.stage_budgets) != 3:
            raise ValueError("successor worker-start budget no longer totals three")
        if sum(item.additional_model_loads for item in self.stage_budgets) != 3:
            raise ValueError("successor model-load budget no longer totals three")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p5-p6-successor-runtime-qualification-v1-implementation-review"]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    frozen_composition: tuple[str, ...] = Field(min_length=8)
    invariants: tuple[str, ...] = Field(min_length=12)
    required_failure_codes: tuple[str, ...] = Field(min_length=12)
    output_contract: tuple[str, ...] = Field(min_length=15)
    execution_budget: ExecutionBudget
    runtime_execution_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["implement_and_merge_p5_p6_successor_runtime_qualification_v1"]


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class NotebookReceipt(ArtifactReceipt):
    notebook_name: Literal["ag-p5-p6-successor-runtime-qual-v1"]
    failed_notebook_name: Literal["ag-p5-p6-successor-runtime-failed-v1"]
    code_cell_count: Literal[1]
    execution_count_present: Literal[False] = False
    output_present: Literal[False] = False
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ImplementationSafety(_StrictModel):
    runtime_execution_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
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
    record_id: Literal["auragateway-p5-p6-successor-runtime-qualification-v1-implementation"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_authorities: tuple[AcceptedAuthority, ...] = Field(min_length=7, max_length=7)
    request: ArtifactReceipt
    review: ArtifactReceipt
    source: ArtifactReceipt
    template: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    notebook: NotebookReceipt
    evidence_zip_name: Literal["ag-p5-p6-successor-runtime-evidence-v1.zip"]
    expected_runtime_outputs: tuple[str, ...]
    request_identities: RequestIdentityContract
    evidence_contract: EvidenceContract
    execution_budget: ExecutionBudget
    safety: ImplementationSafety
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p5_p6_successor_execution_authorization_v1"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class GeneratedArtifacts(_StrictModel):
    request: SuccessorRequest
    review: ArchitectureReview
    notebook_bytes: bytes
    runtime_script_sha256: str
    wrapper_code_sha256: str
    record: ImplementationRecord


def _canonical_json(payload: object) -> str:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _canonical_runtime_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_json(payload: object) -> str:
    return _sha256_bytes(_canonical_runtime_json(payload).encode("utf-8"))


def _receipt(path: Path, payload: bytes) -> ArtifactReceipt:
    return ArtifactReceipt(
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _path_receipt(repo_root: Path, path: Path) -> ArtifactReceipt:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_STATIC_ARTIFACT_MISSING",
            "required successor static artifact is missing or unsafe",
            path.as_posix(),
        )
    return _receipt(path, absolute.read_bytes())


def _read_exact_bytes(repo_root: Path, path: Path, expected_sha256: str) -> bytes:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_AUTHORITY_MISSING",
            "required successor authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_AUTHORITY_DRIFT",
            "required successor authority identity drifted",
            path.as_posix(),
        )
    return payload


def _read_exact_json(
    repo_root: Path,
    path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    payload = _read_exact_bytes(repo_root, path, expected_sha256)
    observed = json.loads(payload)
    if not isinstance(observed, dict):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_AUTHORITY_INVALID",
            "required successor authority root is not one object",
            path.as_posix(),
        )
    return cast(dict[str, object], observed)


def _authority(
    authority_id: str,
    path: Path,
    sha256: str,
    purpose: str,
) -> AcceptedAuthority:
    return AcceptedAuthority(
        authority_id=authority_id,
        repository_path=path.as_posix(),
        sha256=sha256,
        purpose=purpose,
    )


def _accepted_authorities(repo_root: Path) -> tuple[AcceptedAuthority, ...]:
    successor_review = _read_exact_json(
        repo_root,
        SUCCESSOR_REVIEW_AUTHORITY_PATH,
        SUCCESSOR_REVIEW_AUTHORITY_SHA256,
    )
    pre_review = _read_exact_json(
        repo_root,
        PREIMPLEMENTATION_REVIEW_PATH,
        PREIMPLEMENTATION_REVIEW_SHA256,
    )
    policy = _read_exact_json(
        repo_root,
        PREIMPLEMENTATION_POLICY_PATH,
        PREIMPLEMENTATION_POLICY_SHA256,
    )
    p4_request = _read_exact_json(
        repo_root,
        P4_REQUEST_AUTHORITY_PATH,
        P4_REQUEST_AUTHORITY_SHA256,
    )
    v5_request = _read_exact_json(
        repo_root,
        V5_REQUEST_AUTHORITY_PATH,
        V5_REQUEST_AUTHORITY_SHA256,
    )
    _read_exact_bytes(
        repo_root,
        P4_TEMPLATE_AUTHORITY_PATH,
        P4_TEMPLATE_AUTHORITY_SHA256,
    )
    _read_exact_bytes(
        repo_root,
        V5_TEMPLATE_AUTHORITY_PATH,
        V5_TEMPLATE_AUTHORITY_SHA256,
    )

    if (
        successor_review.get("decision")
        != "IMPLEMENT_SUCCESSOR_P5_P6_QUALIFICATION_BEFORE_MEASURED_ABC_AUTHORIZATION"
        or successor_review.get("runtime_execution_authorized") is not False
        or successor_review.get("measured_abc_execution_authorized") is not False
        or successor_review.get("next_gate")
        != "implement_and_merge_p5_p6_successor_runtime_qualification_v1"
    ):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_REVIEW_SEMANTIC_DRIFT",
            "successor sequencing review no longer authorizes this implementation gate",
            SUCCESSOR_REVIEW_AUTHORITY_PATH.as_posix(),
        )

    if (
        pre_review.get("decision")
        != "GO_FOR_SUCCESSOR_IMPLEMENTATION_WITH_FROZEN_COMPOSITION_RULES"
        or pre_review.get("unresolved_compatibility_rows") != []
        or pre_review.get("runtime_execution_authorized") is not False
        or pre_review.get("measured_abc_execution_authorized") is not False
    ):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_RECON_SEMANTIC_DRIFT",
            "preimplementation reconnaissance no longer supports implementation",
            PREIMPLEMENTATION_REVIEW_PATH.as_posix(),
        )

    go_gate = policy.get("go_gate")
    if not isinstance(go_gate, dict) or (
        go_gate.get("runtime_execution_authorized") is not False
        or go_gate.get("measured_abc_execution_authorized") is not False
        or go_gate.get("unresolved_compatibility_rows_permitted") != 0
    ):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_POLICY_DRIFT",
            "preimplementation policy go gate drifted",
            PREIMPLEMENTATION_POLICY_PATH.as_posix(),
        )

    cases = p4_request.get("cases")
    hardening = p4_request.get("runtime_hardening")
    if not isinstance(cases, list) or not isinstance(hardening, dict):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_P4_AUTHORITY_INVALID",
            "P4 request authority is missing required contracts",
            P4_REQUEST_AUTHORITY_PATH.as_posix(),
        )
    case_a = next(
        (item for item in cases if isinstance(item, dict) and item.get("case_id") == "A"),
        None,
    )
    if not isinstance(case_a, dict) or (
        case_a.get("prompt_variant") != "V4"
        or case_a.get("repetition_penalty") != 1.1
        or case_a.get("output_mode") != "UNCONSTRAINED"
        or hardening.get("cuda_stub_paths_prohibited") is not True
        or hardening.get("native_origin_closure_required") is not True
        or hardening.get("same_environment_for_import_and_worker") is not True
    ):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_P4_CONTRACT_DRIFT",
            "P4 Case-A or native hardening contract drifted",
            P4_REQUEST_AUTHORITY_PATH.as_posix(),
        )

    v5_budget = v5_request.get("execution_budget")
    v5_evidence = v5_request.get("evidence_contract")
    if not isinstance(v5_budget, dict) or not isinstance(v5_evidence, dict):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_V5_AUTHORITY_INVALID",
            "V5 request authority is missing required contracts",
            V5_REQUEST_AUTHORITY_PATH.as_posix(),
        )
    if (
        v5_budget.get("maximum_model_requests") != 5
        or v5_budget.get("maximum_worker_starts") != 3
        or v5_budget.get("benchmark_trajectory_requests_permitted") != 0
        or v5_evidence.get("typed_route_acknowledgement_required") is not True
        or v5_evidence.get("partial_p6_evidence_preservation_required") is not True
        or v5_evidence.get("structured_teardown_report_required") is not True
    ):
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_V5_CONTRACT_DRIFT",
            "V5 P5/P6 topology or evidence contract drifted",
            V5_REQUEST_AUTHORITY_PATH.as_posix(),
        )

    return (
        _authority(
            "successor_runtime_qualification_review_v1",
            SUCCESSOR_REVIEW_AUTHORITY_PATH,
            SUCCESSOR_REVIEW_AUTHORITY_SHA256,
            "Requires current-line P5/P6 qualification before measured A/B/C.",
        ),
        _authority(
            "successor_preimplementation_review_v1",
            PREIMPLEMENTATION_REVIEW_PATH,
            PREIMPLEMENTATION_REVIEW_SHA256,
            "Freezes the resolved P4-V2-plus-V5 composition and zero unresolved rows.",
        ),
        _authority(
            "successor_preimplementation_policy_v1",
            PREIMPLEMENTATION_POLICY_PATH,
            PREIMPLEMENTATION_POLICY_SHA256,
            "Binds exact predecessor identities and the repository-only go gate.",
        ),
        _authority(
            "p4_output_contract_v2_request",
            P4_REQUEST_AUTHORITY_PATH,
            P4_REQUEST_AUTHORITY_SHA256,
            "Binds Case A and the successful P4 V2 native-environment hardening contract.",
        ),
        _authority(
            "p3_p6_runtime_diagnostic_v5_request",
            V5_REQUEST_AUTHORITY_PATH,
            V5_REQUEST_AUTHORITY_SHA256,
            "Binds the five-request resource envelope and P5/P6 evidence contract.",
        ),
        _authority(
            "p4_output_contract_v2_template",
            P4_TEMPLATE_AUTHORITY_PATH,
            P4_TEMPLATE_AUTHORITY_SHA256,
            "Provides the accepted CUDA-stub filtering and LD_PRELOAD removal implementation.",
        ),
        _authority(
            "p3_p6_runtime_diagnostic_v5_template",
            V5_TEMPLATE_AUTHORITY_PATH,
            V5_TEMPLATE_AUTHORITY_SHA256,
            "Provides the dual-worker topology, route checkpoints, metrics, and teardown basis.",
        ),
    )


def _case_a_payload() -> dict[str, object]:
    expected = json.dumps(
        EXPECTED_OBJECT,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return {
        "model": SERVED_MODEL_NAME,
        "messages": [
            {"role": "system", "content": V4_PROMPT},
            {"role": "user", "content": V5_SYNTHETIC_CACHE_CONTEXT},
            {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
            {"role": "user", "content": expected},
        ],
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def _logical_request_sha256(
    stage: str,
    worker_id: str,
    worker_generation: int,
    payload_sha256: str,
) -> str:
    return _sha256_json(
        {
            "stage": stage,
            "worker_id": worker_id,
            "worker_generation": worker_generation,
            "payload_sha256": payload_sha256,
        }
    )


def _request_identities() -> RequestIdentityContract:
    payload = _case_a_payload()
    payload_sha256 = _sha256_json(payload)
    messages = payload["messages"]
    if not isinstance(messages, list) or len(messages) != 4:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_REQUEST_IDENTITY_INVALID",
            "successor Case-A message sequence drifted",
        )
    shared_messages_sha256 = _sha256_json(messages)
    eligible_prefix_messages_sha256 = _sha256_json(messages[:-1])
    p4_cold = _logical_request_sha256(
        "P4_CANARY_AND_P5_COLD",
        "worker_1",
        1,
        payload_sha256,
    )
    return RequestIdentityContract(
        payload_sha256=payload_sha256,
        shared_messages_sha256=shared_messages_sha256,
        eligible_prefix_messages_sha256=eligible_prefix_messages_sha256,
        p4_canary_logical_sha256=p4_cold,
        p5_cold_logical_sha256=p4_cold,
        p5_warm_logical_sha256=_logical_request_sha256(
            "P5_WARM",
            "worker_1",
            1,
            payload_sha256,
        ),
        p5_post_restart_logical_sha256=_logical_request_sha256(
            "P5_POST_RESTART",
            "worker_1",
            2,
            payload_sha256,
        ),
        p6_worker_1_logical_sha256=_logical_request_sha256(
            "P6_WORKER_1_ROUTE",
            "worker_1",
            2,
            payload_sha256,
        ),
        p6_worker_2_logical_sha256=_logical_request_sha256(
            "P6_WORKER_2_ROUTE",
            "worker_2",
            1,
            payload_sha256,
        ),
    )


def _stage_budgets() -> tuple[StageBudget, StageBudget, StageBudget, StageBudget]:
    return (
        StageBudget(
            stage="P3_CANARY",
            additional_model_requests=0,
            additional_worker_starts=1,
            additional_model_loads=1,
        ),
        StageBudget(
            stage="P4_CANARY",
            additional_model_requests=1,
            additional_worker_starts=0,
            additional_model_loads=0,
        ),
        StageBudget(
            stage="P5",
            additional_model_requests=2,
            additional_worker_starts=1,
            additional_model_loads=1,
        ),
        StageBudget(
            stage="P6",
            additional_model_requests=2,
            additional_worker_starts=1,
            additional_model_loads=1,
        ),
    )


def _evidence_contract() -> EvidenceContract:
    return EvidenceContract(required_target_native_tokens=("libcusparse", "libnvJitLink"))


def _non_claims() -> tuple[str, ...]:
    return (
        "The successor runtime qualification has not been executed.",
        "No runtime authorization is issued by this implementation.",
        "No measured A/B/C authorization is issued by this implementation.",
        "Current-line P5 prefix-cache reuse is not yet established.",
        "Current-line P5 full-process reset is not yet established.",
        "Current-line P6 route isolation is not yet established.",
        "Current-line P6 metric isolation is not yet established.",
        "Pressure and cache-eviction behavior are not established.",
        "Fault-recovery behavior is not established.",
        "Variance adequacy and measured repetition count are not frozen.",
        "No A/B/C benchmark trajectory is executed by this implementation.",
        "Deployment, customer-data readiness, and production readiness are not claimed.",
    )


def _request(authorities: tuple[AcceptedAuthority, ...]) -> SuccessorRequest:
    return SuccessorRequest(
        request_id="auragateway-p5-p6-successor-runtime-qualification-v1-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        strategy="P4_V2_ENVIRONMENT_PLUS_V5_P5_P6_SUCCESSOR_COMPOSITION",
        composition_decision="GO_FOR_SUCCESSOR_IMPLEMENTATION_WITH_FROZEN_COMPOSITION_RULES",
        selected_backend="TRITON_ATTN",
        model_repository=MODEL_REPOSITORY,
        model_revision=MODEL_REVISION,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        selected_p4_contract=SelectedP4Contract(),
        request_identities=_request_identities(),
        stage_budgets=_stage_budgets(),
        execution_budget=ExecutionBudget(),
        evidence_contract=_evidence_contract(),
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
        next_gate="merge_then_design_separate_p5_p6_successor_execution_authorization_v1",
        non_claims=_non_claims(),
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id=("auragateway-p5-p6-successor-runtime-qualification-v1-implementation-review"),
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        frozen_composition=(
            "P4 V2 owns runtime/native environment construction.",
            "P4 V2 selected Case A owns the P4 canary output contract.",
            "V5 owns the long synthetic deterministic prefix used for P5 cache evidence.",
            "V5 owns the two-worker GPU/port/resource topology.",
            "V5 owns P5 request-attributable token telemetry and teardown design.",
            "V5 owns typed P6 route checkpoints and per-worker request counters.",
            "V4 historical P5 evidence is design guidance, not current-line proof.",
            "P4 Case A is reused as the P5 cold baseline to preserve the five-request ceiling.",
            "Benchmark trajectories remain prohibited throughout successor qualification.",
        ),
        invariants=(
            "Filter CUDA stub and compat paths from inherited LD_LIBRARY_PATH.",
            "Remove inherited LD_PRELOAD before import probes and worker startup.",
            "Prepend governed target NVIDIA library directories.",
            "Retain /usr/local/nvidia/lib64 as the real driver boundary.",
            "Use the same hardened process-tree environment for import closure and workers.",
            "Preserve V5 max-model-len 4096, gpu-memory-utilization 0.85, and max-num-seqs 8.",
            "Use exactly one P4 Case-A canary with V4 prompt and repetition penalty 1.1.",
            "Place the V5 synthetic cache context before the final Case-A user object.",
            "Keep the final user message equal to the canonical Case-A object.",
            "Use the exact same composed Case-A payload for P4, P5, and P6 model calls.",
            "Require cold cached-prefix tokens equal zero and warm cached-prefix tokens positive.",
            "Require warm computed prefill lower than cold computed prefill.",
            "Require a full worker-process restart and fresh post-restart cache baseline.",
            "Revalidate TRITON_ATTN and required native origins after the P5 restart.",
            "Allow non-stub ambient native origins except the governed "
            "libcusparse/libnvJitLink pair.",
            "Snapshot both worker metric endpoints around each P6 routed request.",
            "Require target prompt-token delta positive and non-target prompt-token delta zero.",
            "Use harness transport plus metrics, never model semantics, as P6 route proof.",
            "Checkpoint P6 attempts/completions before later fallible validation.",
            "Reconcile declared, attempted, completed, and per-worker request counts.",
            "Treat governed teardown failure as overall execution failure.",
            "Retain no raw prompts or raw model outputs in evidence.",
        ),
        required_failure_codes=(
            "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH",
            "P3_P6_WHEELHOUSE_INVALID",
            "P3_P6_RUNTIME_INSTALL_FAILED",
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "P3_P6_PROHIBITED_CUDA_STUB_PATH",
            "P3_P6_LD_PRELOAD_PRESENT",
            "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
            "P3_P6_MODEL_IDENTITY_MISMATCH",
            "P3_P6_EXPLICIT_BACKEND_NOT_REALIZED",
            "P3_P6_WORKER_STARTUP_FAILED",
            "P3_P6_REQUEST_FAILED",
            "P3_P6_CACHE_REUSE_NOT_OBSERVED",
            "P3_P6_RESET_NOT_PROVEN",
            "P6_WORKER_2_STARTUP_FAILED",
            "P6_PROCESS_ISOLATION_FAILED",
            "P6_GPU_ISOLATION_FAILED",
            "P6_PORT_ISOLATION_FAILED",
            "P6_WORKER_1_ROUTE_TRANSPORT_FAILED",
            "P6_WORKER_1_METRIC_ATTRIBUTION_FAILED",
            "P6_WORKER_2_ROUTE_TRANSPORT_FAILED",
            "P6_WORKER_2_METRIC_ATTRIBUTION_FAILED",
            "P6_REQUEST_COUNTER_RECONCILIATION_FAILED",
            "P3_P6_ACTION_BUDGET_EXCEEDED",
            "P3_P6_WORKER_TEARDOWN_FAILED",
            "P3_P6_SCRATCH_CLEANUP_FAILED",
        ),
        output_contract=(
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
            EVIDENCE_ZIP_NAME,
        ),
        execution_budget=ExecutionBudget(),
        next_gate="implement_and_merge_p5_p6_successor_runtime_qualification_v1",
    )


def _template_bytes(repo_root: Path) -> bytes:
    path = repo_root / TEMPLATE_PATH
    if not path.is_file() or path.is_symlink():
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_TEMPLATE_MISSING",
            "successor runtime template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    raw = path.read_text(encoding="utf-8")
    replacements = {
        "__" + "NOTEBOOK_NAME" + "__": NOTEBOOK_NAME,
        "__" + "SOURCE_MAIN_COMMIT" + "__": SOURCE_MAIN_COMMIT,
        "__" + "SUCCESSOR_REVIEW_SHA256" + "__": SUCCESSOR_REVIEW_AUTHORITY_SHA256,
        "__" + "PREIMPLEMENTATION_REVIEW_SHA256" + "__": PREIMPLEMENTATION_REVIEW_SHA256,
        "__" + "PREIMPLEMENTATION_POLICY_SHA256" + "__": PREIMPLEMENTATION_POLICY_SHA256,
        "__" + "MODEL_SNAPSHOT_SHA256" + "__": MODEL_SNAPSHOT_SHA256,
        "__" + "EVIDENCE_ZIP_NAME" + "__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        if raw.count(marker) != 1:
            raise SuccessorImplementationError(
                "P5_P6_SUCCESSOR_TEMPLATE_MARKER_DRIFT",
                "successor runtime template marker count drifted",
                marker,
            )
        raw = raw.replace(marker, value)
    unresolved = tuple(sorted(set(re.findall(r"__[A-Z][A-Z0-9_]+__", raw))))
    if unresolved:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_TEMPLATE_PLACEHOLDER_UNRESOLVED",
            "rendered successor template contains unresolved placeholders",
            ",".join(unresolved),
        )
    try:
        compile(raw, TEMPLATE_PATH.as_posix(), "exec")
    except SyntaxError as error:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_TEMPLATE_COMPILE_FAILED",
            "rendered successor template does not compile",
            str(error.lineno),
        ) from error
    if max(len(line) for line in raw.splitlines()) > 100:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_TEMPLATE_LINE_LENGTH_DRIFT",
            "rendered successor template exceeds 100 characters",
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
        ('_AG_RUNTIME_SOURCE = _ag_base64.b64decode("".join(_AG_RUNTIME_B64)).decode("utf-8")'),
        f'_AG_EXPECTED_RUNTIME_SHA256 = "{runtime_sha256}"',
        (
            "_AG_OBSERVED_RUNTIME_SHA256 = "
            '_ag_hashlib.sha256(_AG_RUNTIME_SOURCE.encode("utf-8")).hexdigest()'
        ),
        "if _AG_OBSERVED_RUNTIME_SHA256 != _AG_EXPECTED_RUNTIME_SHA256:",
        '    raise RuntimeError("runtime script identity mismatch")',
        "EXECUTED_RUNTIME_SCRIPT_SHA256 = _AG_OBSERVED_RUNTIME_SHA256",
        "exec(",
        '    compile(_AG_RUNTIME_SOURCE, "<auragateway-successor-v1-runtime>", "exec"),',
        "    globals(),",
        "    globals(),",
        ")",
    ]
    wrapper = ("\n".join(lines) + "\n").encode("utf-8")
    if max(len(line) for line in wrapper.decode("utf-8").splitlines()) > 100:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_NOTEBOOK_WRAPPER_LINE_LENGTH_DRIFT",
            "successor notebook wrapper exceeds 100 characters",
        )
    compile(wrapper.decode("utf-8"), NOTEBOOK_PATH.as_posix(), "exec")
    return wrapper, runtime_sha256, _sha256_bytes(wrapper)


def _notebook_bytes(rendered_template: bytes) -> tuple[bytes, str, str]:
    wrapper, runtime_sha256, wrapper_sha256 = _wrapper_code(rendered_template)
    source = wrapper.decode("utf-8")
    source_lines = source.splitlines()
    code_source = [
        line + "\n" if index < len(source_lines) - 1 else line
        for index, line in enumerate(source_lines)
    ]
    payload = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "91ffcc0c52204f2590a8cbeec026a339",
                "metadata": {},
                "outputs": [],
                "source": code_source,
            }
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
    notebook_json = json.dumps(
        payload,
        ensure_ascii=False,
        indent=1,
    )
    return (
        (notebook_json + "\n").encode("utf-8"),
        runtime_sha256,
        wrapper_sha256,
    )


def build_generated(repo_root: Path) -> GeneratedArtifacts:
    if (repo_root / OPERATIONAL_AUTHORIZATION_PATH).exists():
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_OPERATIONAL_AUTHORIZATION_PRESENT",
            "successor operational authorization must remain absent during implementation",
            OPERATIONAL_AUTHORIZATION_PATH.as_posix(),
        )
    if (repo_root / OPERATIONAL_CONSUMPTION_PATH).exists():
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_OPERATIONAL_CONSUMPTION_PRESENT",
            "successor authorization consumption must remain absent during implementation",
            OPERATIONAL_CONSUMPTION_PATH.as_posix(),
        )

    authorities = _accepted_authorities(repo_root)
    request = _request(authorities)
    review = _review()
    request_bytes = request.canonical_json().encode("utf-8")
    review_bytes = review.canonical_json().encode("utf-8")
    rendered_template = _template_bytes(repo_root)
    notebook_bytes, runtime_script_sha256, wrapper_code_sha256 = _notebook_bytes(rendered_template)
    record = ImplementationRecord(
        record_id=("auragateway-p5-p6-successor-runtime-qualification-v1-implementation"),
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
            code_cell_count=1,
            runtime_script_sha256=runtime_script_sha256,
            wrapper_code_sha256=wrapper_code_sha256,
        ),
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        expected_runtime_outputs=review.output_contract,
        request_identities=request.request_identities,
        evidence_contract=request.evidence_contract,
        execution_budget=request.execution_budget,
        safety=ImplementationSafety(),
        next_gate="merge_then_design_separate_p5_p6_successor_execution_authorization_v1",
        non_claims=request.non_claims,
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
            raise SuccessorImplementationError(
                "P5_P6_SUCCESSOR_GENERATED_ARTIFACT_MISSING",
                "generated successor artifact is missing or unsafe",
                path.as_posix(),
            )
        if absolute.read_bytes() != expected_payload:
            raise SuccessorImplementationError(
                "P5_P6_SUCCESSOR_GENERATED_ARTIFACT_DRIFT",
                "generated successor artifact differs from fresh rebuild",
                path.as_posix(),
            )
    try:
        SuccessorRequest.model_validate_json((repo_root / REQUEST_PATH).read_text(encoding="utf-8"))
        ArchitectureReview.model_validate_json(
            (repo_root / REVIEW_PATH).read_text(encoding="utf-8")
        )
        ImplementationRecord.model_validate_json(
            (repo_root / RECORD_PATH).read_text(encoding="utf-8")
        )
    except ValidationError as error:
        raise SuccessorImplementationError(
            "P5_P6_SUCCESSOR_GENERATED_CONTRACT_INVALID",
            "generated successor contract validation failed",
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
            marker = "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_GENERATED"
        elif arguments.command == "validate":
            generated = validate(repo_root)
            marker = "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_VALIDATED"
        else:
            raise SuccessorImplementationError(
                "P5_P6_SUCCESSOR_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": generated.record.status,
                    "source_main_commit": generated.record.source_main_commit,
                    "notebook_sha256": generated.record.notebook.sha256,
                    "runtime_script_sha256": generated.record.notebook.runtime_script_sha256,
                    "wrapper_code_sha256": generated.record.notebook.wrapper_code_sha256,
                    "candidate_path_count": len(CANDIDATE_PATHS),
                    "maximum_model_requests": (
                        generated.record.execution_budget.maximum_model_requests
                    ),
                    "p4_canary_reused_as_p5_cold_baseline": True,
                    "runtime_execution_authorized": False,
                    "measured_abc_execution_authorized": False,
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
        SuccessorImplementationError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, SuccessorImplementationError)
            else {
                "error_code": "P5_P6_SUCCESSOR_IMPLEMENTATION_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
