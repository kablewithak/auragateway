"""Accept and classify the governed P3-P6 runtime diagnostic V1 failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CURRENT_MAIN_AUTHORITY: Final = "f9a21819d95a7aadd7e5c775019a0761558c5aac"
IMPLEMENTATION_SOURCE_MAIN: Final = "58a73c38c22337219899018d655e00366d790413"
SAVED_VERSION_ID: Final = 339375227
NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diagnostic-v1"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p3-p6-runtime-diag-failed-v1"
KAGGLE_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-p3-p6-runtime-diagnostic-v1/log?scriptVersionId=339375227"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7"
)
AUTHORIZATION_ID: Final = "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v1"
NEXT_GATE: Final = "design_and_merge_p3_p6_runtime_install_diagnostics_v2"

EVIDENCE_ROOT: Final = Path("evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v1")
AUTHORIZATION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / ("execution_authorization_v1-339375227.json")
CONSUMPTION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "execution_authorization_consumption_v1-339375227.json"
)
SUMMARY_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "p3_p6_runtime_diagnostic_summary_v1-339375227.json"
)
FAILURE_EVIDENCE_PATH: Final = EVIDENCE_ROOT / ("failure_report_v1-339375227.json")
REFERENCE_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "kaggle_saved_version_reference_v1-339375227.json"
)
LIMITATIONS_EVIDENCE_PATH: Final = EVIDENCE_ROOT / ("evidence_limitations_v1-339375227.json")

AUTHORIZATION_EVIDENCE_SHA256: Final = (
    "625a3406f7d78d37377a8dff5ff1d2dfce3d122ed88ee2fc1c686565a07d1468"
)
CONSUMPTION_EVIDENCE_SHA256: Final = (
    "78c8065c2b453cbdd016df572cc3d14040238125eac6efb884ead587bd56463b"
)
SUMMARY_EVIDENCE_SHA256: Final = "0ba5cb9f3c1b00fdcd445bf184ae716f4fbca19386f24c884ab15220cac3cf27"
FAILURE_EVIDENCE_SHA256: Final = "a9095c517fd7aa5c078476dc455ac132b9231c5eeb00f78b3540342197f5b4d2"
REFERENCE_EVIDENCE_SHA256: Final = (
    "48554ae56e27747deb7d4e0aefc796c7b5e32d7a74cfdf9e3307d7a43af8ae19"
)
LIMITATIONS_EVIDENCE_SHA256: Final = (
    "20ed7cf2bf6d3d4a5fc299bdd5f711f1217b2bce4e50686126c259bd2ea21b20"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-01-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v1.json"
)


class FailureAcceptanceError(RuntimeError):
    """Fail-closed failure-evidence acceptance error."""

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


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


class ExternalEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ActionCounters(StrictModel):
    benchmark_trajectory_requests: Literal[0]
    external_spend: Literal[0]
    hidden_retries: Literal[0]
    kaggle_sessions: Literal[1]
    model_loads: Literal[0]
    model_requests: Literal[0]
    network_requests: Literal[0]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[0]


class DiagnosticSummary(StrictModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v1"]
    source_main_commit: Literal["58a73c38c22337219899018d655e00366d790413"]
    q6_acceptance_sha256: Literal[
        "9928243d34edd82996a3120f724df6c8bf4912e8b8790b8abc8926eccca006c1"
    ]
    option_c_decision_sha256: Literal[
        "6297b48f64811dbd1b86c850b0fbd66a4142d174d69897b673eb5748663cc418"
    ]
    status: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V1_FAILED"]
    completed_probes: tuple[str, ...]
    failure_code: Literal["P3_P6_RUNTIME_INSTALL_FAILED"]
    stop_on_first_failure: Literal[True]
    counters: ActionCounters
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    network_access_permitted: Literal[False]
    measured_abc_execution_performed: Literal[False]
    next_gate: Literal["preserve_and_classify_p3_p6_runtime_failure_v1"]

    @model_validator(mode="after")
    def require_pre_probe_install_failure(self) -> Self:
        if self.completed_probes:
            raise ValueError("runtime-install failure must precede completed P3-P6 probes")
        return self


class FailureReport(StrictModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    failed_after: tuple[str, ...]
    error_code: Literal["P3_P6_RUNTIME_INSTALL_FAILED"]
    error_type: Literal["RuntimeError"]
    safe_message: Literal["offline target-runtime installation failed"]

    @model_validator(mode="after")
    def require_empty_failed_after(self) -> Self:
        if self.failed_after:
            raise ValueError("failure report unexpectedly records completed probes")
        return self


class AuthorizationEvidence(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v1"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V1"]
    issued_from_main_commit: Literal["f9a21819d95a7aadd7e5c775019a0761558c5aac"]
    notebook_sha256: Literal["bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7"]
    single_use: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]


class ConsumptionEvidence(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    consumption_id: str
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v1"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["FAILED"]
    saved_version_id: Literal[339375227]
    notebook_sha256: Literal["bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7"]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v1"]


class SavedVersionReference(StrictModel):
    schema_version: Literal["1.0.0"]
    reference_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v1-kaggle-reference"]
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v1"]
    failed_lineage_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v1"]
    saved_version_id: Literal[339375227]
    kaggle_version_url: str
    outcome: Literal["FAILED"]
    failure_code: Literal["P3_P6_RUNTIME_INSTALL_FAILED"]
    source_main_authority: Literal["f9a21819d95a7aadd7e5c775019a0761558c5aac"]


class EvidenceLimitations(StrictModel):
    schema_version: Literal["1.0.0"]
    limitations_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v1-limitations"]
    pip_stdout_retained: Literal[False]
    pip_stderr_retained: Literal[False]
    pip_return_code_retained: Literal[False]
    pip_timeout_state_retained: Literal[False]
    complete_output_archive_available: Literal[False]
    root_cause_resolved: Literal[False]
    boundary_classification_supported: Literal[True]
    root_cause_classification_supported: Literal[False]
    reason: Literal[
        "the V1 harness collapsed pip subprocess diagnostics into one generic safe message"
    ]


class ArtifactReceipt(StrictModel):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class FailureClassificationReview(StrictModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v1-review"]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V1_CLASSIFIED"]
    decision: Literal["ACCEPT_RUNTIME_INSTALL_BOUNDARY_FAILURE_WITH_UNRESOLVED_ROOT_CAUSE"]
    saved_version_id: Literal[339375227]
    failure_code: Literal["P3_P6_RUNTIME_INSTALL_FAILED"]
    failure_boundary: Literal["OFFLINE_TARGET_RUNTIME_INSTALLATION"]
    root_cause_classification: Literal["UNRESOLVED_PIP_SUBPROCESS_FAILURE"]
    evidence_sufficiency: Literal[
        "SUFFICIENT_FOR_BOUNDARY_CLASSIFICATION_INSUFFICIENT_FOR_ROOT_CAUSE"
    ]
    completed_probes: tuple[str, ...]
    counters: ActionCounters
    authorization_lifecycle_closed: Literal[True]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_performed: Literal[False]
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    external_network_requests: Literal[0]
    external_spend: Literal[0]
    evidence: tuple[ArtifactReceipt, ...]
    limitations: tuple[str, ...] = Field(min_length=4)
    non_claims: tuple[str, ...] = Field(min_length=8)
    next_gate: Literal["design_and_merge_p3_p6_runtime_install_diagnostics_v2"]


class FailureAcceptanceRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v1"]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID"]
    source_main_authority: Literal["f9a21819d95a7aadd7e5c775019a0761558c5aac"]
    saved_version_id: Literal[339375227]
    review: ArtifactReceipt
    source: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    evidence: tuple[ArtifactReceipt, ...]
    authorization_lifecycle_closed: Literal[True]
    root_cause_resolved: Literal[False]
    runtime_execution_authorized: Literal[False]
    unchanged_replay_authorized: Literal[False]
    next_gate: Literal["design_and_merge_p3_p6_runtime_install_diagnostics_v2"]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact(repo_root: Path, relative_path: Path) -> ArtifactReceipt:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_ARTIFACT_UNSAFE",
            "a required failure-acceptance artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    return ArtifactReceipt(
        repository_path=relative_path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _read_bound(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
) -> bytes:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_EVIDENCE_UNSAFE",
            "required failure evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_EVIDENCE_DRIFT",
            "required failure evidence identity drifted",
            relative_path.as_posix(),
        )
    return payload


def _load_model(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
    model: type[BaseModel],
) -> BaseModel:
    payload = _read_bound(repo_root, relative_path, expected_sha256)
    try:
        return model.model_validate_json(payload)
    except ValidationError as error:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_EVIDENCE_INVALID",
            "required failure evidence failed schema validation",
            relative_path.as_posix(),
        ) from error


def _evidence_receipts(repo_root: Path) -> tuple[ArtifactReceipt, ...]:
    bindings = (
        (AUTHORIZATION_EVIDENCE_PATH, AUTHORIZATION_EVIDENCE_SHA256),
        (CONSUMPTION_EVIDENCE_PATH, CONSUMPTION_EVIDENCE_SHA256),
        (SUMMARY_EVIDENCE_PATH, SUMMARY_EVIDENCE_SHA256),
        (FAILURE_EVIDENCE_PATH, FAILURE_EVIDENCE_SHA256),
        (REFERENCE_EVIDENCE_PATH, REFERENCE_EVIDENCE_SHA256),
        (LIMITATIONS_EVIDENCE_PATH, LIMITATIONS_EVIDENCE_SHA256),
    )
    result = []
    for relative_path, expected_sha256 in bindings:
        payload = _read_bound(repo_root, relative_path, expected_sha256)
        result.append(
            ArtifactReceipt(
                repository_path=relative_path.as_posix(),
                sha256=expected_sha256,
                size_bytes=len(payload),
            )
        )
    return tuple(result)


def build_review(repo_root: Path) -> FailureClassificationReview:
    root = repo_root.resolve()
    authorization = cast(
        AuthorizationEvidence,
        _load_model(
            root,
            AUTHORIZATION_EVIDENCE_PATH,
            AUTHORIZATION_EVIDENCE_SHA256,
            AuthorizationEvidence,
        ),
    )
    consumption = cast(
        ConsumptionEvidence,
        _load_model(
            root,
            CONSUMPTION_EVIDENCE_PATH,
            CONSUMPTION_EVIDENCE_SHA256,
            ConsumptionEvidence,
        ),
    )
    summary = cast(
        DiagnosticSummary,
        _load_model(
            root,
            SUMMARY_EVIDENCE_PATH,
            SUMMARY_EVIDENCE_SHA256,
            DiagnosticSummary,
        ),
    )
    failure = cast(
        FailureReport,
        _load_model(
            root,
            FAILURE_EVIDENCE_PATH,
            FAILURE_EVIDENCE_SHA256,
            FailureReport,
        ),
    )
    reference = cast(
        SavedVersionReference,
        _load_model(
            root,
            REFERENCE_EVIDENCE_PATH,
            REFERENCE_EVIDENCE_SHA256,
            SavedVersionReference,
        ),
    )
    limitations = cast(
        EvidenceLimitations,
        _load_model(
            root,
            LIMITATIONS_EVIDENCE_PATH,
            LIMITATIONS_EVIDENCE_SHA256,
            EvidenceLimitations,
        ),
    )
    if consumption.authorization_sha256 != AUTHORIZATION_EVIDENCE_SHA256:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_AUTHORIZATION_LINKAGE_DRIFT",
            "consumption evidence no longer binds the accepted authorization bytes",
            CONSUMPTION_EVIDENCE_PATH.as_posix(),
        )
    if authorization.authorization_id != consumption.authorization_id:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_AUTHORIZATION_ID_DRIFT",
            "authorization and consumption identifiers differ",
        )
    if summary.failure_code != failure.error_code:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_FAILURE_CODE_DRIFT",
            "summary and failure-report codes differ",
        )
    if reference.saved_version_id != consumption.saved_version_id:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_SAVED_VERSION_DRIFT",
            "saved-version evidence and consumption receipt differ",
        )
    if limitations.root_cause_classification_supported:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_OVERCLAIM",
            "evidence limitations unexpectedly claim root-cause support",
        )
    return FailureClassificationReview(
        schema_version="1.0.0",
        review_id=("auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v1-review"),
        status="P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V1_CLASSIFIED",
        decision=("ACCEPT_RUNTIME_INSTALL_BOUNDARY_FAILURE_WITH_UNRESOLVED_ROOT_CAUSE"),
        saved_version_id=SAVED_VERSION_ID,
        failure_code="P3_P6_RUNTIME_INSTALL_FAILED",
        failure_boundary="OFFLINE_TARGET_RUNTIME_INSTALLATION",
        root_cause_classification="UNRESOLVED_PIP_SUBPROCESS_FAILURE",
        evidence_sufficiency=("SUFFICIENT_FOR_BOUNDARY_CLASSIFICATION_INSUFFICIENT_FOR_ROOT_CAUSE"),
        completed_probes=summary.completed_probes,
        counters=summary.counters,
        authorization_lifecycle_closed=True,
        authorization_reusable=consumption.authorization_reusable,
        unchanged_replay_authorized=False,
        runtime_execution_authorized=False,
        measured_abc_execution_performed=summary.measured_abc_execution_performed,
        credentials_used=summary.credentials_used,
        customer_data_present=summary.customer_data_present,
        external_network_requests=summary.counters.network_requests,
        external_spend=summary.counters.external_spend,
        evidence=_evidence_receipts(root),
        limitations=(
            "pip stdout was not retained by the V1 harness",
            "pip stderr was not retained by the V1 harness",
            "pip return code and timeout state were not retained",
            "the complete Kaggle output archive was impractical to download",
            "the exact dependency or wheel failure is therefore unresolved",
        ),
        non_claims=(
            "P3 did not complete.",
            "P4 did not execute.",
            "P5 did not execute.",
            "P6 did not execute.",
            "No model was loaded.",
            "No worker was started.",
            "No model request was issued.",
            "No cache behavior was observed.",
            "No dual-worker isolation was observed.",
            "No dependency root cause is claimed.",
            "No deployment or production readiness is claimed.",
        ),
        next_gate=NEXT_GATE,
    )


def build_record(
    repo_root: Path,
    review_bytes: bytes,
) -> FailureAcceptanceRecord:
    root = repo_root.resolve()
    return FailureAcceptanceRecord(
        schema_version="1.0.0",
        record_id=("auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v1"),
        status="P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID",
        source_main_authority=CURRENT_MAIN_AUTHORITY,
        saved_version_id=SAVED_VERSION_ID,
        review=ArtifactReceipt(
            repository_path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        source=_artifact(root, SOURCE_PATH),
        tests=_artifact(root, TEST_PATH),
        adr=_artifact(root, ADR_PATH),
        report=_artifact(root, REPORT_PATH),
        runbook=_artifact(root, RUNBOOK_PATH),
        evidence=_evidence_receipts(root),
        authorization_lifecycle_closed=True,
        root_cause_resolved=False,
        runtime_execution_authorized=False,
        unchanged_replay_authorized=False,
        next_gate=NEXT_GATE,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_TEMPORARY_PATH_PRESENT",
            "temporary generation path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def generate(repo_root: Path) -> FailureAcceptanceRecord:
    root = repo_root.resolve()
    review = build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    _write_atomic(root / REVIEW_PATH, review_bytes)
    record = build_record(root, review_bytes)
    _write_atomic(root / RECORD_PATH, record.canonical_json().encode("utf-8"))
    return record


def validate(repo_root: Path) -> FailureAcceptanceRecord:
    root = repo_root.resolve()
    review = build_review(root)
    review_bytes = review.canonical_json().encode("utf-8")
    record = build_record(root, review_bytes)
    expected = (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record.canonical_json().encode("utf-8")),
    )
    for relative_path, expected_payload in expected:
        path = root / relative_path
        if not path.is_file() or path.is_symlink():
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_GENERATED_ARTIFACT_UNSAFE",
                "generated failure-acceptance artifact is missing or unsafe",
                relative_path.as_posix(),
            )
        if path.read_bytes() != expected_payload:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_GENERATED_ARTIFACT_DRIFT",
                "generated failure-acceptance artifact differs from fresh generation",
                relative_path.as_posix(),
            )
    return record


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def _error_json(error: Exception) -> str:
    if isinstance(error, FailureAcceptanceError):
        payload = {
            "error_code": error.error_code,
            "safe_message": error.safe_message,
            "path": error.path,
        }
    else:
        payload = {
            "error_code": "P3_P6_FAILURE_ACCEPTANCE_UNEXPECTED",
            "safe_message": str(error),
            "path": None,
        }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALIDATED"
        else:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_COMMAND_UNSUPPORTED",
                "failure-acceptance command is unsupported",
            )
        print(
            json.dumps(
                {
                    "marker": marker,
                    "status": record.status,
                    "saved_version_id": record.saved_version_id,
                    "authorization_lifecycle_closed": True,
                    "root_cause_resolved": False,
                    "runtime_execution_authorized": False,
                    "unchanged_replay_authorized": False,
                    "next_gate": record.next_gate,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except (
        FailureAcceptanceError,
        ValidationError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(_error_json(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
