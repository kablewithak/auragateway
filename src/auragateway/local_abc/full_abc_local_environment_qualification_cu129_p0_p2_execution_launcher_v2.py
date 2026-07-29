"""Generate and validate the governed CUDA 12.9 P0-P2 execution launcher V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_MERGE_COMMIT: Final = "eb809180e2139713a24a09c4eb1ff900f48d329e"
BRANCH_NAME: Final = "feat/local-abc-cu129-p0-p2-execution-launcher-v2"
SOURCE_MATERIALIZATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_source_materialization_toolchain_v2.json"
)
SOURCE_MATERIALIZATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_source_materialization_review_v2.json"
)
DIAGNOSTIC_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb"
)
DIAGNOSTIC_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "option_c_p0_p2_platform_diagnostic_request.json"
)
DIAGNOSTIC_IMPLEMENTATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json"
)
REVIEW_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_execution_launcher_review_v2.json"
)
LAUNCHER_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_execution_launcher_record_v2.json"
)
LAUNCHER_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p0_p2_execution_launcher_v2.py.tmpl"
)
LAUNCHER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_p0_p2_execution_launcher_v2.ipynb"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

LAUNCHER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-execution-launcher-v2"
FAILED_LAUNCHER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-exec-failed-v2"
LAUNCHER_EVIDENCE_ZIP_NAME: Final = "ag-cu129-p0-p2-execution-launcher-v2.zip"
SOURCE_MATERIALIZER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-materializer-v2"
RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
ACCEPTED_MATERIALIZER_VERSION: Final = "338895141"
ACCEPTED_INSPECTION_VERSION: Final = "338900497"
EXPECTED_SOURCE_BUNDLE_SHA256: Final = (
    "bd097235f858500adcce86ddc99d15c9e01c2848fc3fece9a4ea587a0e66b88b"
)
EXPECTED_SOURCE_INVENTORY_SHA256: Final = (
    "462dbbaf58d6e0bd1568b5ff712955bc452cd56bfeaea0f5d75a3ba0fb657ff7"
)
EXPECTED_DIAGNOSTIC_NOTEBOOK_SHA256: Final = (
    "caefff1468500ecd75edcd0283b3d806a57b76e9a0a3decb318fc4083806b7f5"
)
EXPECTED_DIAGNOSTIC_REQUEST_SHA256: Final = (
    "f1a77d91b4fa6b3d187eb62e527ad3a807caa55e7de6d92bd3f80f4c5c9950f5"
)
EXPECTED_IMPLEMENTATION_RECORD_SHA256: Final = (
    "70c72b2e74fa62146115900d3a32b8e2af82be8b1dc9723e2304f1250e3b96c4"
)
MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
MAXIMUM_GENERATED_LINE_LENGTH: Final = 100


class P0P2ExecutionLauncherV2Error(RuntimeError):
    """Fail-closed execution-launcher generation error."""

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
        """Return a machine-readable error envelope."""

        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class LocalSafetyRecord(LocalABCContract):
    """Static safety state for the repository implementation tranche."""

    authorization_issued: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0


class ExecutionBudget(LocalABCContract):
    """Maximum action budget encoded into the generated launcher."""

    maximum_diagnostic_executions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_kernel_compile_and_execution_attempts: Literal[1] = 1
    maximum_model_loads: Literal[0] = 0
    maximum_worker_starts: Literal[0] = 0
    maximum_model_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class ExecutionLauncherReviewRecord(LocalABCContract):
    """Approved architecture contract for the P0-P2 execution launcher V2."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-execution-launcher-review-v2"]
    decision: Literal["DEDICATED_EXECUTION_LAUNCHER"]
    source_main_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    branch_name: Literal["feat/local-abc-cu129-p0-p2-execution-launcher-v2"]
    launcher_notebook_name: str
    failed_notebook_name: str
    direct_notebook_output_attachment: Literal[True]
    standalone_kaggle_dataset_required: Literal[False]
    accepted_materializer_version: str
    accepted_inspection_version: str
    architecture_requirements: tuple[str, ...]
    prohibited_techniques: tuple[str, ...]
    execution_budget: ExecutionBudget
    safety: LocalSafetyRecord
    next_gate: Literal["generate_and_validate_p0_p2_execution_launcher_v2"]

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        """Validate the exact approved architecture."""

        if self.source_main_merge_commit != SOURCE_MAIN_MERGE_COMMIT:
            raise ValueError("review source main merge commit drifted")
        if self.launcher_notebook_name != LAUNCHER_NOTEBOOK_NAME:
            raise ValueError("launcher notebook name drifted")
        if self.failed_notebook_name != FAILED_LAUNCHER_NOTEBOOK_NAME:
            raise ValueError("failed notebook name drifted")
        if self.accepted_materializer_version != ACCEPTED_MATERIALIZER_VERSION:
            raise ValueError("accepted materializer version drifted")
        if self.accepted_inspection_version != ACCEPTED_INSPECTION_VERSION:
            raise ValueError("accepted inspection version drifted")
        required_architecture = {
            "direct_notebook_output_discovery",
            "receipt_inventory_and_manifest_validation",
            "exact_diagnostic_notebook_identity",
            "single_execution_attempt",
            "post_execution_evidence_validation",
            "bounded_failure_evidence",
            "deterministic_notebook_generation",
        }
        if set(self.architecture_requirements) != required_architecture:
            raise ValueError("architecture requirement set drifted")
        required_prohibitions = {
            "standalone_dataset_requirement",
            "manual_generated_notebook_edits",
            "hidden_retries",
            "model_or_worker_execution",
            "benchmark_trajectory_execution",
            "full_abc_launcher_mutation",
        }
        if set(self.prohibited_techniques) != required_prohibitions:
            raise ValueError("prohibited technique set drifted")
        return self


class GeneratedNotebookReceipt(LocalABCContract):
    """Identity receipt for the generated unexecuted launcher notebook."""

    notebook_name: str
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cell_count: Literal[2] = 2
    outputs_present: Literal[False] = False
    execution_counts_present: Literal[False] = False
    maximum_code_line_length: int = Field(ge=1, le=100)


class ExecutionLauncherRecord(LocalABCContract):
    """Complete generated launcher identity and execution boundary."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-execution-launcher-record-v2"]
    status: Literal["P0_P2_EXECUTION_LAUNCHER_V2_VALID"]
    source_main_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    launcher: GeneratedNotebookReceipt
    source_materializer_notebook_name: str
    accepted_materializer_version: str
    accepted_inspection_version: str
    direct_notebook_output_attachment: Literal[True]
    standalone_kaggle_dataset_required: Literal[False]
    source_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnostic_notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_output_directory: str
    required_input_kinds: tuple[str, str]
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    execution_budget: ExecutionBudget
    launcher_evidence_zip_name: str
    generation_deterministic: Literal[True] = True
    safety: LocalSafetyRecord
    next_gate: Literal["execute_gpu_p0_p2_execution_launcher_v2"]

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        """Validate all fixed launcher identities."""

        if self.source_main_merge_commit != SOURCE_MAIN_MERGE_COMMIT:
            raise ValueError("launcher source main merge commit drifted")
        if self.launcher.notebook_name != LAUNCHER_NOTEBOOK_NAME:
            raise ValueError("launcher notebook name drifted")
        if self.source_materializer_notebook_name != SOURCE_MATERIALIZER_NOTEBOOK_NAME:
            raise ValueError("source materializer notebook name drifted")
        if self.accepted_materializer_version != ACCEPTED_MATERIALIZER_VERSION:
            raise ValueError("accepted materializer version drifted")
        if self.accepted_inspection_version != ACCEPTED_INSPECTION_VERSION:
            raise ValueError("accepted inspection version drifted")
        if self.source_bundle_sha256 != EXPECTED_SOURCE_BUNDLE_SHA256:
            raise ValueError("source bundle identity drifted")
        if self.source_inventory_sha256 != EXPECTED_SOURCE_INVENTORY_SHA256:
            raise ValueError("source inventory identity drifted")
        if self.diagnostic_notebook_sha256 != EXPECTED_DIAGNOSTIC_NOTEBOOK_SHA256:
            raise ValueError("diagnostic notebook identity drifted")
        if self.runtime_output_directory != RUNTIME_OUTPUT_DIRECTORY:
            raise ValueError("runtime output directory drifted")
        expected_inputs = (
            "p0_p2_source_materializer_notebook_output",
            "cu129_wheelhouse_notebook_output",
        )
        if self.required_input_kinds != expected_inputs:
            raise ValueError("required input kinds drifted")
        if self.launcher_evidence_zip_name != LAUNCHER_EVIDENCE_ZIP_NAME:
            raise ValueError("launcher evidence ZIP name drifted")
        return self


class GeneratedLauncher:
    """In-memory deterministic launcher build."""

    def __init__(
        self,
        *,
        notebook_bytes: bytes,
        record: ExecutionLauncherRecord,
    ) -> None:
        self.notebook_bytes = notebook_bytes
        self.record = record


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
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_TEMPORARY_PATH_PRESENT",
            "temporary generated output path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_REQUIRED_FILE_MISSING",
            "required launcher source file is missing",
            path.as_posix(),
        ) from error
    except json.JSONDecodeError as error:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_JSON_INVALID",
            "required launcher source file is invalid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_JSON_ROOT_INVALID",
            "required launcher source JSON root must be one object",
            path.as_posix(),
        )
    return {str(key): value for key, value in payload.items()}


def _validate_bound_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_SOURCE_FILE_UNSAFE",
            "bound source file is missing or unsafe",
            path.as_posix(),
        )
    observed = _sha256_bytes(path.read_bytes())
    if observed != expected_sha256:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_SOURCE_IDENTITY_DRIFT",
            "bound source file identity drifted",
            path.as_posix(),
        )


def _validate_source_authorities(repo_root: Path) -> None:
    materialization = _load_json_object(repo_root / SOURCE_MATERIALIZATION_RECORD_PATH)
    expected_materialization = {
        "status": "P0_P2_SOURCE_MATERIALIZATION_TOOLCHAIN_V2_VALID",
        "source_bundle_sha256": EXPECTED_SOURCE_BUNDLE_SHA256,
        "source_inventory_sha256": EXPECTED_SOURCE_INVENTORY_SHA256,
        "output_directory_name": "ag_cu129_p0_p2_source_materializer_v2_output",
        "output_dataset_name": "ag-cu129-p0-p2-source-v2",
    }
    if any(materialization.get(key) != value for key, value in expected_materialization.items()):
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_MATERIALIZATION_AUTHORITY_DRIFT",
            "source materialization authority drifted",
            SOURCE_MATERIALIZATION_RECORD_PATH.as_posix(),
        )
    _load_json_object(repo_root / SOURCE_MATERIALIZATION_REVIEW_PATH)
    _validate_bound_file(
        repo_root / DIAGNOSTIC_NOTEBOOK_PATH,
        EXPECTED_DIAGNOSTIC_NOTEBOOK_SHA256,
    )
    _validate_bound_file(
        repo_root / DIAGNOSTIC_REQUEST_PATH,
        EXPECTED_DIAGNOSTIC_REQUEST_SHA256,
    )
    _validate_bound_file(
        repo_root / DIAGNOSTIC_IMPLEMENTATION_PATH,
        EXPECTED_IMPLEMENTATION_RECORD_SHA256,
    )


def _load_template(repo_root: Path) -> str:
    path = repo_root / LAUNCHER_TEMPLATE_PATH
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_TEMPLATE_MISSING",
            "launcher template is missing",
            LAUNCHER_TEMPLATE_PATH.as_posix(),
        ) from error
    unresolved_markers = (
        "__SOURCE_MAIN_MERGE_COMMIT__",
        "__DIAGNOSTIC_NOTEBOOK_SHA256__",
        "__SOURCE_BUNDLE_SHA256__",
    )
    if any(marker in source for marker in unresolved_markers):
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_TEMPLATE_MARKER_PRESENT",
            "launcher template contains an unresolved marker",
            LAUNCHER_TEMPLATE_PATH.as_posix(),
        )
    return source


def _maximum_line_length(source: str) -> int:
    return max((len(line) for line in source.splitlines()), default=0)


def _validate_generated_source(source: str) -> int:
    try:
        compile(source, LAUNCHER_NOTEBOOK_NAME, "exec")
    except SyntaxError as error:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_GENERATED_SOURCE_INVALID",
            "generated launcher source does not compile",
        ) from error
    maximum = _maximum_line_length(source)
    if maximum > MAXIMUM_GENERATED_LINE_LENGTH:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_LINE_LENGTH_EXCEEDED",
            "generated launcher source exceeds the line-length policy",
        )
    prohibited_fragments = (
        "lines.extend([",
        "subprocess.run(",
        "vllm",
        "AutoModel",
        "requests.get(",
    )
    for fragment in prohibited_fragments:
        if fragment in source:
            raise P0P2ExecutionLauncherV2Error(
                "P0_P2_LAUNCHER_V2_PROHIBITED_SOURCE_PRESENT",
                "generated launcher contains a prohibited direct execution primitive",
            )
    required_fragments = (
        "diagnostic_execution_attempts += 1",
        "EXPECTED_DIAGNOSTIC_NOTEBOOK_SHA256",
        "standalone_kaggle_dataset_required",
        "exec(",
        "validate_diagnostic_evidence",
    )
    for fragment in required_fragments:
        if fragment not in source:
            raise P0P2ExecutionLauncherV2Error(
                "P0_P2_LAUNCHER_V2_REQUIRED_SOURCE_MISSING",
                "generated launcher is missing a required execution gate",
            )
    return maximum


def _notebook_bytes(source: str) -> bytes:
    payload = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# AuraGateway CUDA 12.9 P0-P2 execution launcher V2\n",
                    "\n",
                    "Consumes the accepted source materializer notebook output "
                    "directly and executes the exact reviewed P0-P2 diagnostic once. "
                    "Use T4 x2, Internet Off, no secrets, and attach only the source "
                    "materializer output plus the governed CUDA 12.9 wheelhouse output.\n",
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
            "auragateway": {
                "accepted_inspection_version": ACCEPTED_INSPECTION_VERSION,
                "accepted_materializer_version": ACCEPTED_MATERIALIZER_VERSION,
                "direct_notebook_output_attachment": True,
                "launcher_evidence_zip_name": LAUNCHER_EVIDENCE_ZIP_NAME,
                "notebook_name": LAUNCHER_NOTEBOOK_NAME,
                "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
                "standalone_kaggle_dataset_required": False,
            },
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
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
                "version": "3.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def build_generated_launcher(repo_root: Path) -> GeneratedLauncher:
    """Build the deterministic launcher notebook and record in memory."""

    _validate_source_authorities(repo_root)
    source = _load_template(repo_root)
    maximum = _validate_generated_source(source)
    first = _notebook_bytes(source)
    second = _notebook_bytes(source)
    if first != second:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_GENERATION_NONDETERMINISTIC",
            "two launcher notebook builds differ",
        )
    record = ExecutionLauncherRecord(
        record_id="auragateway-cu129-p0-p2-execution-launcher-record-v2",
        status="P0_P2_EXECUTION_LAUNCHER_V2_VALID",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        launcher=GeneratedNotebookReceipt(
            notebook_name=LAUNCHER_NOTEBOOK_NAME,
            repository_path=LAUNCHER_NOTEBOOK_PATH.as_posix(),
            sha256=_sha256_bytes(first),
            maximum_code_line_length=maximum,
        ),
        source_materializer_notebook_name=SOURCE_MATERIALIZER_NOTEBOOK_NAME,
        accepted_materializer_version=ACCEPTED_MATERIALIZER_VERSION,
        accepted_inspection_version=ACCEPTED_INSPECTION_VERSION,
        direct_notebook_output_attachment=True,
        standalone_kaggle_dataset_required=False,
        source_bundle_sha256=EXPECTED_SOURCE_BUNDLE_SHA256,
        source_inventory_sha256=EXPECTED_SOURCE_INVENTORY_SHA256,
        diagnostic_notebook_sha256=EXPECTED_DIAGNOSTIC_NOTEBOOK_SHA256,
        runtime_output_directory=RUNTIME_OUTPUT_DIRECTORY,
        required_input_kinds=(
            "p0_p2_source_materializer_notebook_output",
            "cu129_wheelhouse_notebook_output",
        ),
        accelerator="T4_X2",
        internet_enabled=False,
        execution_budget=ExecutionBudget(),
        launcher_evidence_zip_name=LAUNCHER_EVIDENCE_ZIP_NAME,
        safety=LocalSafetyRecord(),
        next_gate="execute_gpu_p0_p2_execution_launcher_v2",
    )
    return GeneratedLauncher(notebook_bytes=first, record=record)


def generate(repo_root: Path) -> ExecutionLauncherRecord:
    """Generate the launcher notebook and exact record."""

    generated = build_generated_launcher(repo_root)
    _write_bytes_atomic(
        repo_root / LAUNCHER_NOTEBOOK_PATH,
        generated.notebook_bytes,
    )
    _write_bytes_atomic(
        repo_root / LAUNCHER_RECORD_PATH,
        generated.record.canonical_json().encode("utf-8"),
    )
    return generated.record


def _load_review_record(path: Path) -> ExecutionLauncherReviewRecord:
    try:
        return ExecutionLauncherReviewRecord.model_validate(_load_json_object(path))
    except ValidationError as error:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_REVIEW_RECORD_INVALID",
            "execution launcher review record violates its contract",
            path.as_posix(),
        ) from error


def _load_launcher_record(path: Path) -> ExecutionLauncherRecord:
    try:
        return ExecutionLauncherRecord.model_validate(_load_json_object(path))
    except ValidationError as error:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_RECORD_INVALID",
            "execution launcher record violates its contract",
            path.as_posix(),
        ) from error


def validate(repo_root: Path) -> ExecutionLauncherRecord:
    """Validate source authority and byte-identical generated outputs."""

    _load_review_record(repo_root / REVIEW_RECORD_PATH)
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_AUTHORIZATION_PRESENT",
            "transient full-run authorization must remain absent",
            AUTHORIZATION_PATH.as_posix(),
        )
    expected = build_generated_launcher(repo_root)
    observed = _load_launcher_record(repo_root / LAUNCHER_RECORD_PATH)
    if observed != expected.record:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_RECORD_DRIFT",
            "generated launcher record drifted",
            LAUNCHER_RECORD_PATH.as_posix(),
        )
    outputs = {
        LAUNCHER_NOTEBOOK_PATH: expected.notebook_bytes,
        LAUNCHER_RECORD_PATH: expected.record.canonical_json().encode("utf-8"),
    }
    for relative_path, expected_bytes in outputs.items():
        path = repo_root / relative_path
        if not path.is_file() or path.is_symlink():
            raise P0P2ExecutionLauncherV2Error(
                "P0_P2_LAUNCHER_V2_GENERATED_OUTPUT_MISSING",
                "generated launcher output is missing or unsafe",
                relative_path.as_posix(),
            )
        if path.read_bytes() != expected_bytes:
            raise P0P2ExecutionLauncherV2Error(
                "P0_P2_LAUNCHER_V2_GENERATED_OUTPUT_DRIFT",
                "generated launcher output differs from deterministic rebuild",
                relative_path.as_posix(),
            )
    return expected.record


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P0P2ExecutionLauncherV2Error(
            "P0_P2_LAUNCHER_V2_ARGUMENT_INVALID",
            message,
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            status = "P0_P2_EXECUTION_LAUNCHER_V2_GENERATED"
        else:
            record = validate(repo_root)
            status = record.status
        print(
            _canonical_json(
                {
                    "status": status,
                    "launcher_notebook_name": record.launcher.notebook_name,
                    "launcher_notebook_sha256": record.launcher.sha256,
                    "direct_notebook_output_attachment": (record.direct_notebook_output_attachment),
                    "standalone_kaggle_dataset_required": (
                        record.standalone_kaggle_dataset_required
                    ),
                    "maximum_diagnostic_executions": (
                        record.execution_budget.maximum_diagnostic_executions
                    ),
                    "maximum_model_requests": (record.execution_budget.maximum_model_requests),
                    "next_gate": record.next_gate,
                }
            )
        )
        return 0
    except P0P2ExecutionLauncherV2Error as error:
        print(_canonical_json(error.envelope()), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
