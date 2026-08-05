"""Generate and validate the governed P4 Output-Contract Diagnostic V1 assets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_MAIN_COMMIT: Final = "e13882628559ec0f8f3364cc27ce574cbdd92806"

FAILURE_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v5.json"
)
FAILURE_ACCEPTANCE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v5_review.json"
)
V5_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v5_record.json"
)

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v1.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_v1_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v1_review.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_p4_output_contract_diagnostic_v1.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v1_record.json"
)
SOURCE_PATH: Final = Path("src/auragateway/local_abc/p4_output_contract_diagnostic_v1.py")
TEST_PATH: Final = Path("tests/unit/local_abc/test_p4_output_contract_diagnostic_v1.py")
ADR_PATH: Final = Path("docs/adr/2026-08-05-local-abc-p4-output-contract-diagnostic-v1.md")
REPORT_PATH: Final = Path("docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_V1.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_p4_output_contract_diagnostic_v1.md")

NOTEBOOK_NAME: Final = "ag-p4-output-contract-diagnostic-v1"
FAILED_NOTEBOOK_NAME: Final = "ag-p4-output-contract-diag-failed-v1"
EVIDENCE_ZIP_NAME: Final = "ag-p4-output-contract-evidence-v1.zip"
EXPECTED_RUNTIME_OUTPUTS: Final = (
    "runtime_source_identity_report_v1.json",
    "model_snapshot_report_v1.json",
    "wheelhouse_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "worker_startup_report_v1.json",
    "request_results_v1.json",
    "case_metrics_v1.json",
    "selection_report_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "p4_output_contract_diagnostic_summary_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
    "ag-p4-output-contract-evidence-v1.zip",
)
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"

GENERATED_PATHS: Final = (REQUEST_PATH, REVIEW_PATH, NOTEBOOK_PATH, RECORD_PATH)
STATIC_PATHS: Final = (SOURCE_PATH, TEMPLATE_PATH, TEST_PATH, ADR_PATH, REPORT_PATH, RUNBOOK_PATH)
CANDIDATE_PATHS: Final = tuple(sorted((*GENERATED_PATHS, *STATIC_PATHS)))


class P4OutputContractImplementationError(RuntimeError):
    """Fail-closed implementation and validation error."""

    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
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
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_ARGUMENT_INVALID",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class AcceptedAuthority(ArtifactReceipt):
    authority_id: Literal[
        "v5_failure_acceptance_record",
        "v5_failure_acceptance_review",
        "v5_implementation_record",
    ]
    source_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    status: str
    next_gate: str


class DiagnosticCase(_StrictModel):
    case_id: Literal["A", "B", "C", "D", "E", "F"]
    prompt_variant: Literal["V4", "V5"]
    repetition_penalty: float
    output_mode: Literal["UNCONSTRAINED", "JSON_SCHEMA"]
    repetitions: Literal[3] = 3

    @model_validator(mode="after")
    def validate_repetition_penalty(self) -> Self:
        if self.repetition_penalty not in (1.0, 1.1):
            raise ValueError("repetition_penalty must be exactly 1.0 or 1.1")

        return self


class ExecutionBudget(_StrictModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[1] = 1
    maximum_worker_starts: Literal[1] = 1
    maximum_model_requests: Literal[18] = 18
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    hidden_retries_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class EvidenceContract(_StrictModel):
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    response_sha256_required: Literal[True] = True
    response_length_required: Literal[True] = True
    finish_reason_required: Literal[True] = True
    token_usage_required: Literal[True] = True
    json_error_coordinates_required: Literal[True] = True
    edge_character_classes_required: Literal[True] = True
    markdown_fence_detection_required: Literal[True] = True
    exact_object_validation_required: Literal[True] = True
    request_order_required: Literal[True] = True
    request_error_is_fatal: Literal[False] = False
    transport_error_is_fatal: Literal[True] = True
    teardown_required: Literal[True] = True
    scratch_cleanup_required: Literal[True] = True


class P4OutputContractRequest(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-p4-output-contract-diagnostic-v1-request"]
    source_main_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    accepted_authorities: tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority]
    strategy: Literal["SIX_CASE_BALANCED_OUTPUT_CONTRACT_DIAGNOSTIC"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_backend: Literal["TRITON_ATTN"]
    cases: tuple[DiagnosticCase, ...]
    request_order: tuple[Literal["A", "B", "C", "D", "E", "F"], ...]
    execution_budget: ExecutionBudget
    evidence_contract: EvidenceContract
    selection_rule: str
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p4_output_contract_execution_authorization_v1"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_matrix(self) -> Self:
        if tuple(item.case_id for item in self.cases) != ("A", "B", "C", "D", "E", "F"):
            raise ValueError("case order drifted")
        if len(self.request_order) != 18:
            raise ValueError("request order count drifted")
        if {item for item in self.request_order} != {"A", "B", "C", "D", "E", "F"}:
            raise ValueError("request order coverage drifted")
        for case_id in ("A", "B", "C", "D", "E", "F"):
            if self.request_order.count(case_id) != 3:
                raise ValueError("request repetition count drifted")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p4-output-contract-diagnostic-v1-review"]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    accepted_first_divergence: Literal["P4_MODEL_RESPONSE_NOT_VALID_JSON"]
    primary_classification: Literal["P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS"]
    selected_intervention: Literal["BALANCED_PROMPT_PENALTY_SCHEMA_MATRIX"]
    architecture: tuple[str, ...] = Field(min_length=12)
    diagnostic_cases: tuple[str, ...] = Field(min_length=10)
    rejected_alternatives: tuple[str, ...] = Field(min_length=5)
    output_contract: tuple[str, ...] = Field(min_length=10)
    execution_budget: ExecutionBudget
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["implement_and_merge_p4_output_contract_diagnostic_v1"]


class NotebookReceipt(ArtifactReceipt):
    notebook_name: Literal["ag-p4-output-contract-diagnostic-v1"]
    failed_notebook_name: Literal["ag-p4-output-contract-diag-failed-v1"]
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
    record_id: Literal["auragateway-p4-output-contract-diagnostic-v1-implementation"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    source_main_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    accepted_authorities: tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority]
    request: ArtifactReceipt
    review: ArtifactReceipt
    source: ArtifactReceipt
    template: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    notebook: NotebookReceipt
    evidence_zip_name: Literal["ag-p4-output-contract-evidence-v1.zip"]
    expected_runtime_outputs: tuple[str, ...]
    execution_budget: ExecutionBudget
    evidence_contract: EvidenceContract
    safety: ImplementationSafety
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["merge_then_design_separate_p4_output_contract_execution_authorization_v1"]
    non_claims: tuple[str, ...] = Field(min_length=8)


class GeneratedArtifacts(_StrictModel):
    request: P4OutputContractRequest
    review: ArchitectureReview
    notebook_bytes: bytes
    runtime_script_sha256: str
    wrapper_code_sha256: str
    record: ImplementationRecord


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _receipt(
    path: Path,
    payload: bytes,
) -> ArtifactReceipt:
    return ArtifactReceipt(
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _path_receipt(repo_root: Path, path: Path) -> ArtifactReceipt:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_STATIC_ARTIFACT_MISSING",
            "required static artifact is missing or unsafe",
            path.as_posix(),
        )
    return _receipt(path, absolute.read_bytes())


def _git_show(repo_root: Path, path: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{SOURCE_MAIN_COMMIT}:{path.as_posix()}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_AUTHORITY_NOT_IN_SOURCE_MAIN",
            "accepted authority is not available from source main",
            path.as_posix(),
        )
    return result.stdout


def _json_object(payload: bytes, path: Path) -> dict[str, object]:
    try:
        observed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_AUTHORITY_INVALID_JSON",
            "accepted authority is not valid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(observed, dict):
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_AUTHORITY_INVALID_ROOT",
            "accepted authority root is not an object",
            path.as_posix(),
        )
    return cast(dict[str, object], observed)


def _authority_receipt(
    repo_root: Path,
    authority_id: Literal[
        "v5_failure_acceptance_record",
        "v5_failure_acceptance_review",
        "v5_implementation_record",
    ],
    path: Path,
) -> AcceptedAuthority:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_AUTHORITY_MISSING",
            "accepted authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    if os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") != "1":
        source_payload = _git_show(repo_root, path)
        if payload != source_payload:
            raise P4OutputContractImplementationError(
                "P4_OUTPUT_CONTRACT_V1_AUTHORITY_DRIFT",
                "accepted authority differs from source main",
                path.as_posix(),
            )
    observed = _json_object(payload, path)
    status = observed.get("status")
    next_gate = observed.get("next_gate")
    if not isinstance(status, str) or not isinstance(next_gate, str):
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_AUTHORITY_FIELDS_INVALID",
            "accepted authority status or next gate is invalid",
            path.as_posix(),
        )
    if authority_id == "v5_failure_acceptance_record":
        valid = (
            status == "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V5_VALID"
            and next_gate == "design_and_merge_p4_output_contract_diagnostic_v1"
            and observed.get("failed_probe") == "P4"
            and observed.get("first_divergence") == "P4_MODEL_RESPONSE_NOT_VALID_JSON"
            and observed.get("unchanged_replay_authorized") is False
        )
    elif authority_id == "v5_failure_acceptance_review":
        valid = (
            status == "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5_CLASSIFIED"
            and next_gate == "design_and_merge_p4_output_contract_diagnostic_v1"
            and observed.get("evidence_disposition") == "ACCEPTED_DIAGNOSTIC_FAILURE"
        )
    else:
        valid = (
            status == "IMPLEMENTED_NOT_EXECUTED"
            and observed.get("record_id")
            == "auragateway-cu129-p3-p6-runtime-diagnostic-v5-implementation"
        )
    if not valid:
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_AUTHORITY_BOUNDARY_DRIFT",
            "accepted authority no longer permits this diagnostic",
            path.as_posix(),
        )
    return AcceptedAuthority(
        authority_id=authority_id,
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
        source_commit=SOURCE_MAIN_COMMIT,
        status=status,
        next_gate=next_gate,
    )


def _authorities(
    repo_root: Path,
) -> tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority]:
    return (
        _authority_receipt(
            repo_root,
            "v5_failure_acceptance_record",
            FAILURE_ACCEPTANCE_RECORD_PATH,
        ),
        _authority_receipt(
            repo_root,
            "v5_failure_acceptance_review",
            FAILURE_ACCEPTANCE_REVIEW_PATH,
        ),
        _authority_receipt(repo_root, "v5_implementation_record", V5_IMPLEMENTATION_RECORD_PATH),
    )


def diagnostic_cases() -> tuple[DiagnosticCase, ...]:
    return (
        DiagnosticCase(
            case_id="A",
            prompt_variant="V4",
            repetition_penalty=1.1,
            output_mode="UNCONSTRAINED",
        ),
        DiagnosticCase(
            case_id="B",
            prompt_variant="V5",
            repetition_penalty=1.1,
            output_mode="UNCONSTRAINED",
        ),
        DiagnosticCase(
            case_id="C",
            prompt_variant="V4",
            repetition_penalty=1.0,
            output_mode="UNCONSTRAINED",
        ),
        DiagnosticCase(
            case_id="D",
            prompt_variant="V5",
            repetition_penalty=1.0,
            output_mode="UNCONSTRAINED",
        ),
        DiagnosticCase(
            case_id="E",
            prompt_variant="V4",
            repetition_penalty=1.0,
            output_mode="JSON_SCHEMA",
        ),
        DiagnosticCase(
            case_id="F",
            prompt_variant="V5",
            repetition_penalty=1.0,
            output_mode="JSON_SCHEMA",
        ),
    )


def request_order() -> tuple[Literal["A", "B", "C", "D", "E", "F"], ...]:
    return (
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


def _non_claims() -> tuple[str, ...]:
    return (
        "The diagnostic has not been executed.",
        "No runtime authorization is issued by this implementation.",
        "Three repetitions per case do not establish general reliability.",
        "The exact malformed V5 response remains unknown.",
        "Prompt regression is not yet isolated experimentally.",
        "JSON-schema compatibility with pinned vLLM 0.19.1 is not established.",
        "P5 prefix-cache behavior is not established.",
        "P6 route and metric isolation is not established.",
        "Measured A/B/C is not authorized or performed.",
        "Deployment and production readiness are not established.",
    )


def _request(
    authorities: tuple[AcceptedAuthority, AcceptedAuthority, AcceptedAuthority],
) -> P4OutputContractRequest:
    return P4OutputContractRequest(
        request_id="auragateway-p4-output-contract-diagnostic-v1-request",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_authorities=authorities,
        strategy="SIX_CASE_BALANCED_OUTPUT_CONTRACT_DIAGNOSTIC",
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision=MODEL_REVISION,
        model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
        selected_backend="TRITON_ATTN",
        cases=diagnostic_cases(),
        request_order=request_order(),
        execution_budget=ExecutionBudget(),
        evidence_contract=EvidenceContract(),
        selection_rule=(
            "Select the simplest case with 3/3 exact-object responses, one response hash, "
            "and no request, schema, transport, or validation errors."
        ),
        next_gate="merge_then_design_separate_p4_output_contract_execution_authorization_v1",
        non_claims=_non_claims(),
    )


def _review() -> ArchitectureReview:
    return ArchitectureReview(
        review_id="auragateway-p4-output-contract-diagnostic-v1-review",
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        accepted_first_divergence="P4_MODEL_RESPONSE_NOT_VALID_JSON",
        primary_classification="P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS",
        selected_intervention="BALANCED_PROMPT_PENALTY_SCHEMA_MATRIX",
        architecture=(
            "Bind the diagnostic to the merged V5 failure-acceptance authorities.",
            "Keep the model, revision, wheelhouse, T4 GPU, and TRITON backend fixed.",
            "Change only prompt wording, repetition penalty, and output constraint mode.",
            "Run six cases with three repetitions each in a balanced order.",
            "Use one runtime installation, import closure, model load, and worker start.",
            "Make each request's repetition penalty explicit.",
            "Omit response_format for unconstrained cases.",
            "Use OpenAI-compatible json_schema response_format only for E and F.",
            "Continue after content or schema-request failure when the worker remains healthy.",
            "Stop on setup, model, worker, or transport failure.",
            "Retain response hashes and diagnostics but never raw prompts or outputs.",
            "Select only from complete 3/3 case evidence.",
            "Require a separate post-merge runtime-authorization issuer.",
        ),
        diagnostic_cases=(
            "A reproduces the V4 prompt with inherited repetition penalty.",
            "B reproduces the V5 prompt with inherited repetition penalty.",
            "C neutralizes repetition penalty under the V4 prompt.",
            "D neutralizes repetition penalty under the V5 prompt.",
            "E adds JSON schema to the V4 prompt with neutral repetition penalty.",
            "F adds JSON schema to the V5 prompt with neutral repetition penalty.",
            "Every case executes exactly three times.",
            "Every response records a SHA-256 digest and length only.",
            "Malformed JSON records line, column, and position without content.",
            "Schema rejection is distinguished from model-content invalidity.",
            "Response-hash cardinality is computed per case.",
            "No valid case is selected from partial evidence.",
        ),
        rejected_alternatives=(
            "Do not replay V5 unchanged.",
            "Do not retry until a valid response appears.",
            "Do not change the model, wheelhouse, backend, or GPU in this diagnostic.",
            "Do not retain raw failed output to simplify diagnosis.",
            "Do not treat one valid response as sufficient evidence.",
            "Do not issue runtime authority in the implementation pull request.",
        ),
        output_contract=EXPECTED_RUNTIME_OUTPUTS,
        execution_budget=ExecutionBudget(),
        next_gate="implement_and_merge_p4_output_contract_diagnostic_v1",
    )


def _template_bytes(repo_root: Path) -> bytes:
    absolute = repo_root / TEMPLATE_PATH
    if not absolute.is_file() or absolute.is_symlink():
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_TEMPLATE_MISSING",
            "runtime template is missing or unsafe",
            TEMPLATE_PATH.as_posix(),
        )
    raw = absolute.read_text(encoding="utf-8")
    replacements = {
        "__SOURCE_MAIN_COMMIT__": SOURCE_MAIN_COMMIT,
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__MODEL_SNAPSHOT_SHA256__": MODEL_SNAPSHOT_SHA256,
        "__MODEL_REVISION__": MODEL_REVISION,
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
        "__REQUEST_ORDER_JSON__": _canonical_json(list(request_order())),
        "__EXPECTED_RUNTIME_OUTPUTS_JSON__": _canonical_json(list(EXPECTED_RUNTIME_OUTPUTS)),
    }
    for marker, value in replacements.items():
        if raw.count(marker) != 1:
            raise P4OutputContractImplementationError(
                "P4_OUTPUT_CONTRACT_V1_TEMPLATE_MARKER_DRIFT",
                "runtime template marker count drifted",
                marker,
            )
        raw = raw.replace(marker, value)
    unresolved = tuple(sorted(set(re.findall(r"__[A-Z][A-Z0-9_]+__", raw))))
    if unresolved:
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_TEMPLATE_UNRESOLVED",
            "runtime template contains unresolved markers",
            ",".join(unresolved),
        )
    compile(raw, TEMPLATE_PATH.as_posix(), "exec")
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
        '    compile(_AG_RUNTIME_SOURCE, "<p4-output-contract-v1>", "exec"),',
        "    globals(),",
        "    globals(),",
        ")",
    ]
    wrapper = ("\n".join(lines) + "\n").encode("utf-8")
    compile(wrapper.decode("utf-8"), NOTEBOOK_PATH.as_posix(), "exec")
    return wrapper, runtime_sha256, _sha256_bytes(wrapper)


def _notebook_bytes(rendered_template: bytes) -> tuple[bytes, str, str]:
    wrapper, runtime_sha256, wrapper_sha256 = _wrapper_code(rendered_template)
    source_lines = wrapper.decode("utf-8").splitlines()
    code_source = [
        line + "\n" if index < len(source_lines) - 1 else line
        for index, line in enumerate(source_lines)
    ]
    payload = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# AuraGateway P4 Output-Contract Diagnostic V1\n",
                    "\n",
                    "Six-case, metadata-safe diagnostic. Runtime execution requires "
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
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return _canonical_json(payload).encode("utf-8"), runtime_sha256, wrapper_sha256


def build_generated(repo_root: Path) -> GeneratedArtifacts:
    authorities = _authorities(repo_root)
    request = _request(authorities)
    review = _review()
    request_bytes = request.canonical_json().encode("utf-8")
    review_bytes = review.canonical_json().encode("utf-8")
    notebook_bytes, runtime_sha256, wrapper_sha256 = _notebook_bytes(_template_bytes(repo_root))
    notebook_payload = json.loads(notebook_bytes)
    if not isinstance(notebook_payload, dict):
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_NOTEBOOK_INVALID",
            "notebook root is not an object",
        )
    cells_value = notebook_payload.get("cells")
    if not isinstance(cells_value, list):
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_NOTEBOOK_CELLS_INVALID",
            "notebook cells are invalid",
        )
    code_cell_count = sum(
        1 for item in cells_value if isinstance(item, dict) and item.get("cell_type") == "code"
    )
    record = ImplementationRecord(
        record_id="auragateway-p4-output-contract-diagnostic-v1-implementation",
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
            code_cell_count=cast(Literal[1], code_cell_count),
            runtime_script_sha256=runtime_sha256,
            wrapper_code_sha256=wrapper_sha256,
        ),
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        expected_runtime_outputs=review.output_contract,
        execution_budget=ExecutionBudget(),
        evidence_contract=EvidenceContract(),
        safety=ImplementationSafety(),
        next_gate="merge_then_design_separate_p4_output_contract_execution_authorization_v1",
        non_claims=_non_claims(),
    )
    return GeneratedArtifacts(
        request=request,
        review=review,
        notebook_bytes=notebook_bytes,
        runtime_script_sha256=runtime_sha256,
        wrapper_code_sha256=wrapper_sha256,
        record=record,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise P4OutputContractImplementationError(
            "P4_OUTPUT_CONTRACT_V1_TEMPORARY_PRESENT",
            "temporary generated artifact already exists",
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
    generated = build_generated(repo_root)
    outputs = {
        REQUEST_PATH: generated.request.canonical_json().encode("utf-8"),
        REVIEW_PATH: generated.review.canonical_json().encode("utf-8"),
        NOTEBOOK_PATH: generated.notebook_bytes,
        RECORD_PATH: generated.record.canonical_json().encode("utf-8"),
    }
    for path, expected in outputs.items():
        absolute = repo_root / path
        if not absolute.is_file() or absolute.is_symlink():
            raise P4OutputContractImplementationError(
                "P4_OUTPUT_CONTRACT_V1_GENERATED_MISSING",
                "generated artifact is missing or unsafe",
                path.as_posix(),
            )
        if absolute.read_bytes() != expected:
            raise P4OutputContractImplementationError(
                "P4_OUTPUT_CONTRACT_V1_GENERATED_DRIFT",
                "generated artifact differs from fresh rebuild",
                path.as_posix(),
            )
    P4OutputContractRequest.model_validate_json(
        (repo_root / REQUEST_PATH).read_text(encoding="utf-8")
    )
    ArchitectureReview.model_validate_json((repo_root / REVIEW_PATH).read_text(encoding="utf-8"))
    ImplementationRecord.model_validate_json((repo_root / RECORD_PATH).read_text(encoding="utf-8"))
    return generated


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            generated = generate(repo_root)
            marker = "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1_GENERATED"
        else:
            generated = validate(repo_root)
            marker = "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1_VALIDATED"
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": generated.record.status,
                    "source_main_commit": generated.record.source_main_commit,
                    "case_count": len(generated.request.cases),
                    "request_count": len(generated.request.request_order),
                    "notebook_sha256": generated.record.notebook.sha256,
                    "runtime_script_sha256": generated.runtime_script_sha256,
                    "wrapper_code_sha256": generated.wrapper_code_sha256,
                    "candidate_path_count": len(CANDIDATE_PATHS),
                    "runtime_execution_authorized": False,
                    "authorization_issuer_included": False,
                    "measured_abc_execution_authorized": False,
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
        subprocess.SubprocessError,
        P4OutputContractImplementationError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, P4OutputContractImplementationError)
            else {
                "error_code": "P4_OUTPUT_CONTRACT_V1_IMPLEMENTATION_UNEXPECTED",
                "safe_message": type(error).__name__,
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
