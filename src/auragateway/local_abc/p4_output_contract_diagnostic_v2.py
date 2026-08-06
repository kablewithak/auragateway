"""Generate and validate the governed P4 Output-Contract Diagnostic V2 assets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

SOURCE_MAIN_COMMIT: Final = "d76c47d12366ad9500ccec18dd3aebf9b23f7b66"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
INSPECTION_SAVED_VERSION: Final = 340657269
INSPECTION_EVIDENCE_SHA256: Final = (
    "ea54b6ec59bd3a73be20fec04aa56ca9f3f4af58f8499ec2962a66f152180849"
)
NOTEBOOK_NAME: Final = "ag-p4-output-contract-diagnostic-v2"
FAILED_NOTEBOOK_NAME: Final = "ag-p4-output-contract-diag-failed-v2"
EVIDENCE_ZIP_NAME: Final = "ag-p4-output-contract-evidence-v2.zip"

TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_v2_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v2_review.json"
)
DIAGNOSIS_PATH: Final = Path("benchmarks/local_abc/auragateway_p4_native_runtime_diagnosis_v1.json")
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_p4_output_contract_diagnostic_v2.ipynb")
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v2_record.json"
)
SOURCE_PATH: Final = Path("src/auragateway/local_abc/p4_output_contract_diagnostic_v2.py")
TEST_PATH: Final = Path("tests/unit/local_abc/test_p4_output_contract_diagnostic_v2.py")
REPORT_PATH: Final = Path("docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_V2.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_p4_output_contract_diagnostic_v2.md")
INSPECTION_ROOT: Final = Path("evidence_vault/local_abc/p4-import-differential-inspection-v1")
INSPECTION_ZIP_PATH: Final = (
    INSPECTION_ROOT / "ag-p4-import-differential-inspection-v1-340657269.zip"
)
INSPECTION_LOG_PATH: Final = (
    INSPECTION_ROOT / "ag-p4-import-differential-inspection-v1-340657269.log"
)
INSPECTION_HUMAN_PATH: Final = INSPECTION_ROOT / "human_report_v1-340657269.md"

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
STATIC_PATHS: Final = (
    SOURCE_PATH,
    TEMPLATE_PATH,
    TEST_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
    DIAGNOSIS_PATH,
    INSPECTION_ZIP_PATH,
    INSPECTION_LOG_PATH,
    INSPECTION_HUMAN_PATH,
)
GENERATED_PATHS: Final = (NOTEBOOK_PATH, RECORD_PATH)


class P4V2ImplementationError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {"error_code": self.error_code, "safe_message": self.safe_message, "path": self.path}


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P4V2ImplementationError("P4_V2_ARGUMENT_INVALID", message)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DiagnosticCase(_StrictModel):
    case_id: str
    output_mode: str
    prompt_variant: str
    repetition_penalty: float
    repetitions: int


class RuntimeHardening(_StrictModel):
    shared_environment_helper_required: bool
    target_nvidia_libraries_precede_ambient: bool
    cuda_stub_paths_prohibited: bool
    real_driver_directory: str
    same_environment_for_import_and_worker: bool
    fail_fast_worker_exit_required: bool
    bounded_stream_capture_bytes: Literal[131072]
    request_logging_disabled: bool
    native_origin_closure_required: bool
    required_target_native_tokens: list[str]


class RequestModel(_StrictModel):
    schema_version: str
    request_id: str
    source_main_commit: str
    accepted_authorities: list[dict[str, object]]
    strategy: str
    model_repository: str
    model_revision: str
    model_snapshot_sha256: str
    selected_backend: str
    cases: list[DiagnosticCase]
    request_order: list[str]
    runtime_hardening: RuntimeHardening
    execution_budget: dict[str, int]
    runtime_execution_authorized: bool
    authorization_issuer_included: bool
    measured_abc_execution_authorized: bool
    next_gate: str
    non_claims: list[str]

    @model_validator(mode="after")
    def validate_matrix(self) -> RequestModel:
        if [item.case_id for item in self.cases] != list("ABCDEF"):
            raise ValueError("case matrix drifted")
        if len(self.request_order) != 18:
            raise ValueError("request order count drifted")
        if any(self.request_order.count(case_id) != 3 for case_id in "ABCDEF"):
            raise ValueError("request repetition count drifted")
        if self.runtime_execution_authorized or self.measured_abc_execution_authorized:
            raise ValueError("implementation cannot authorize execution")
        return self


def canonical(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def receipt(repo_root: Path, path: Path) -> dict[str, object]:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise P4V2ImplementationError(
            "P4_V2_ARTIFACT_MISSING",
            "artifact missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    return {"path": path.as_posix(), "sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def verify_source_authority(repo_root: Path, path: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{SOURCE_MAIN_COMMIT}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise P4V2ImplementationError(
            "P4_V2_AUTHORITY_MISSING",
            "source-main authority missing",
            path,
        )


def load_request(repo_root: Path) -> RequestModel:
    try:
        raw = json.loads((repo_root / REQUEST_PATH).read_text(encoding="utf-8"))
        return RequestModel.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise P4V2ImplementationError(
            "P4_V2_REQUEST_INVALID",
            "request is invalid",
            REQUEST_PATH.as_posix(),
        ) from error


def render_runtime(repo_root: Path, request: RequestModel) -> bytes:
    template = (repo_root / TEMPLATE_PATH).read_text(encoding="utf-8")
    replacements = {
        "__SOURCE_MAIN_COMMIT__": SOURCE_MAIN_COMMIT,
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__MODEL_SNAPSHOT_SHA256__": MODEL_SNAPSHOT_SHA256,
        "__MODEL_REVISION__": MODEL_REVISION,
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
        "__REQUEST_ORDER_JSON__": canonical(request.request_order),
        "__EXPECTED_RUNTIME_OUTPUTS_JSON__": canonical(EXPECTED_RUNTIME_OUTPUTS),
        "__INSPECTION_SAVED_VERSION__": str(INSPECTION_SAVED_VERSION),
        "__INSPECTION_EVIDENCE_SHA256__": INSPECTION_EVIDENCE_SHA256,
    }
    for marker, value in replacements.items():
        if marker not in template:
            raise P4V2ImplementationError(
                "P4_V2_TEMPLATE_MARKER_MISSING",
                "template marker missing",
                marker,
            )
        template = template.replace(marker, value)
    compile(template, TEMPLATE_PATH.as_posix(), "exec")
    return template.encode("utf-8")


def notebook_bytes(runtime: bytes) -> tuple[bytes, str, str]:
    runtime_sha = sha256_bytes(runtime)
    encoded = base64.b64encode(runtime).decode("ascii")
    encoded_chunks = tuple(encoded[index : index + 88] for index in range(0, len(encoded), 88))
    wrapper_lines = [
        "from __future__ import annotations",
        "",
        "import base64",
        "import hashlib",
        "",
        f"EXPECTED_RUNTIME_SHA256 = {runtime_sha!r}",
        "RUNTIME_SOURCE_B64 = (",
        *(f"    {chunk!r}" for chunk in encoded_chunks),
        ")",
        "",
        "runtime_source = base64.b64decode(RUNTIME_SOURCE_B64).decode('utf-8')",
        "observed = hashlib.sha256(runtime_source.encode('utf-8')).hexdigest()",
        "if observed != EXPECTED_RUNTIME_SHA256:",
        "    raise RuntimeError('runtime source identity mismatch')",
        ("namespace = {'__name__': '__main__', 'EXECUTED_RUNTIME_SCRIPT_SHA256': observed}"),
        (
            "exec(compile(runtime_source, "
            "'<auragateway-p4-output-contract-diagnostic-v2>', "
            "'exec'), namespace)"
        ),
    ]
    wrapper = "\n".join(wrapper_lines) + "\n"
    wrapper_sha = sha256_bytes(wrapper.encode("utf-8"))
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": wrapper.splitlines(keepends=True),
            }
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
    return (canonical(notebook) + "\n").encode("utf-8"), runtime_sha, wrapper_sha


def build_record(
    repo_root: Path,
    notebook_payload: bytes,
    runtime_sha: str,
    wrapper_sha: str,
) -> dict[str, object]:
    request = load_request(repo_root)
    return {
        "schema_version": "1.0.0",
        "record_id": "auragateway-p4-output-contract-diagnostic-v2-implementation",
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "request": receipt(repo_root, REQUEST_PATH),
        "review": receipt(repo_root, REVIEW_PATH),
        "diagnosis": receipt(repo_root, DIAGNOSIS_PATH),
        "source": receipt(repo_root, SOURCE_PATH),
        "template": receipt(repo_root, TEMPLATE_PATH),
        "tests": receipt(repo_root, TEST_PATH),
        "report": receipt(repo_root, REPORT_PATH),
        "runbook": receipt(repo_root, RUNBOOK_PATH),
        "inspection_evidence": receipt(repo_root, INSPECTION_ZIP_PATH),
        "inspection_log": receipt(repo_root, INSPECTION_LOG_PATH),
        "inspection_human_report": receipt(repo_root, INSPECTION_HUMAN_PATH),
        "notebook": {
            "path": NOTEBOOK_PATH.as_posix(),
            "sha256": sha256_bytes(notebook_payload),
            "size_bytes": len(notebook_payload),
            "notebook_name": NOTEBOOK_NAME,
            "failed_notebook_name": FAILED_NOTEBOOK_NAME,
            "code_cell_count": 1,
            "execution_count_present": False,
            "output_present": False,
            "runtime_script_sha256": runtime_sha,
            "wrapper_code_sha256": wrapper_sha,
        },
        "expected_runtime_outputs": list(EXPECTED_RUNTIME_OUTPUTS),
        "runtime_hardening": request.runtime_hardening.model_dump(mode="json"),
        "safety": {
            "runtime_execution_authorized": False,
            "kaggle_execution_performed": False,
            "gpu_execution_performed": False,
            "runtime_installation_performed": False,
            "model_loaded": False,
            "worker_started": False,
            "model_requests_performed": 0,
            "network_requests_performed": 0,
            "credentials_used": False,
            "customer_data_present": False,
            "external_spend": 0,
        },
        "authorization_issuer_included": False,
        "next_gate": request.next_gate,
        "non_claims": request.non_claims,
    }


def generate(repo_root: Path) -> None:
    verify_source_authority(
        repo_root,
        "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_failure_acceptance_v1.json",
    )
    verify_source_authority(
        repo_root,
        "benchmarks/local_abc/"
        "auragateway_p4_output_contract_diagnostic_failure_acceptance_v1_review.json",
    )
    if sha256_bytes((repo_root / INSPECTION_ZIP_PATH).read_bytes()) != INSPECTION_EVIDENCE_SHA256:
        raise P4V2ImplementationError(
            "P4_V2_INSPECTION_IDENTITY_MISMATCH",
            "inspection ZIP identity mismatch",
            INSPECTION_ZIP_PATH.as_posix(),
        )
    request = load_request(repo_root)
    runtime = render_runtime(repo_root, request)
    notebook_payload, runtime_sha, wrapper_sha = notebook_bytes(runtime)
    (repo_root / NOTEBOOK_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo_root / NOTEBOOK_PATH).write_bytes(notebook_payload)
    record = build_record(repo_root, notebook_payload, runtime_sha, wrapper_sha)
    (repo_root / RECORD_PATH).write_text(canonical(record), encoding="utf-8", newline="\n")


def validate_package(repo_root: Path) -> None:
    request = load_request(repo_root)
    runtime = render_runtime(repo_root, request)
    expected_notebook, runtime_sha, wrapper_sha = notebook_bytes(runtime)
    if (repo_root / NOTEBOOK_PATH).read_bytes() != expected_notebook:
        raise P4V2ImplementationError(
            "P4_V2_NOTEBOOK_DRIFTED",
            "notebook bytes drifted",
            NOTEBOOK_PATH.as_posix(),
        )
    expected_record = canonical(
        build_record(repo_root, expected_notebook, runtime_sha, wrapper_sha)
    ).encode("utf-8")
    if (repo_root / RECORD_PATH).read_bytes() != expected_record:
        raise P4V2ImplementationError(
            "P4_V2_RECORD_DRIFTED",
            "record bytes drifted",
            RECORD_PATH.as_posix(),
        )
    if sha256_bytes((repo_root / INSPECTION_ZIP_PATH).read_bytes()) != INSPECTION_EVIDENCE_SHA256:
        raise P4V2ImplementationError(
            "P4_V2_INSPECTION_IDENTITY_MISMATCH",
            "inspection ZIP identity mismatch",
            INSPECTION_ZIP_PATH.as_posix(),
        )


def parser() -> _ArgumentParser:
    result = _ArgumentParser()
    result.add_argument("command", choices=("generate", "validate-package"))
    result.add_argument("--repo-root", type=Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        repo_root = args.repo_root.resolve()
        if args.command == "generate":
            generate(repo_root)
        else:
            validate_package(repo_root)
        print(canonical({"status": "PASSED", "command": args.command}))
        return 0
    except P4V2ImplementationError as error:
        print(canonical(error.envelope()), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
