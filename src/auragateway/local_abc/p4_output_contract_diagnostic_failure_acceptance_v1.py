"""Accept and classify the governed P4 output-contract diagnostic V1 failure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_failure_acceptance_v1_policy.json"
)
POLICY_SHA256: Final = "a9016731aa16db755b1af871fda8410b811e843b4b7b2cd163c87bd3fb195b43"
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_output_contract_diagnostic_failure_acceptance_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_output_contract_diagnostic_failure_acceptance_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-06-local-abc-p4-output-contract-diagnostic-failure-acceptance-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_Output_Contract_Diagnostic_Failure_Acceptance_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_output_contract_diagnostic_failure_acceptance_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_failure_acceptance_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_failure_acceptance_v1.json"
)


class FailureAcceptanceError(RuntimeError):
    """Fail-closed failure-acceptance error."""

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
        raise FailureAcceptanceError(
            "P4_FAILURE_ACCEPTANCE_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class ExpectedHashes(StrictModel):
    intake_archive: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    abandonment: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_stderr: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_stdout: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")


class FailureAcceptancePolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-p4-output-contract-diagnostic-failure-acceptance-v1-policy"]
    current_main_authority: str = Field(pattern=r"^[0-9a-f]{40}$")
    saved_version_id: Literal[340622392]
    lifecycle_outcome: Literal["FAILED"]
    evidence_disposition: Literal["ACCEPTED_DIAGNOSTIC_FAILURE"]
    first_divergence: Literal["RUNTIME_IMPORT_CLOSURE_FAILED"]
    reported_failure_code: Literal["P4_OUTPUT_CONTRACT_RUNTIME_FAILED"]
    safe_failure_message: Literal["RuntimeError"]
    root_cause_status: Literal["UNRESOLVED"]
    next_gate: Literal["design_and_merge_p4_runtime_import_closure_diagnostic_v1"]
    expected_hashes: ExpectedHashes
    evidence_receipt_count: int = Field(gt=0)
    evidence_receipts: tuple[ArtifactReceipt, ...]
    repository_authority_count: int = Field(gt=0)
    repository_authorities: tuple[ArtifactReceipt, ...]
    runtime_member_targets: dict[str, str]
    intake_prefix: Literal["p4_output_contract_diagnostic_v1/"]
    expected_runtime_member_count: Literal[15]
    expected_terminal_log_tokens: tuple[str, ...]
    operational_transient_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if len(self.evidence_receipts) != self.evidence_receipt_count:
            raise ValueError("evidence receipt count drifted")
        if len(self.repository_authorities) != self.repository_authority_count:
            raise ValueError("repository authority count drifted")
        if len(self.runtime_member_targets) != self.expected_runtime_member_count:
            raise ValueError("runtime member target count drifted")
        if len(self.expected_terminal_log_tokens) != 5:
            raise ValueError("terminal log token count drifted")
        if len(self.operational_transient_paths) != 3:
            raise ValueError("operational transient path count drifted")
        return self


class ActionCounters(StrictModel):
    benchmark_trajectory_requests: Literal[0]
    external_spend: Literal[0]
    hidden_retries: Literal[0]
    kaggle_sessions: Literal[1]
    model_loads: Literal[0]
    model_requests: Literal[0]
    network_requests: Literal[0]
    runtime_import_closure_probes: Literal[1]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[0]


class DiagnosticSummary(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    terminal_decision: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1_FAILED"]
    counters: ActionCounters
    request_count: Literal[0]
    scheduled_request_count: Literal[18]
    expected_runtime_output_count: Literal[16]
    worker_teardown_status: Literal["NOT_REQUIRED"]
    scratch_cleanup_status: Literal["PASSED"]
    raw_prompt_retained: Literal[False]
    raw_output_retained: Literal[False]
    measured_abc_execution_performed: Literal[False]
    customer_data_present: Literal[False]
    credentials_used: Literal[False]
    next_gate: Literal["preserve_and_classify_p4_output_contract_diagnostic_v1"]


class FailureReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    stage: Literal["runtime_import_closure"]
    error_code: Literal["P4_OUTPUT_CONTRACT_RUNTIME_FAILED"]
    safe_message: Literal["RuntimeError"]
    counters: ActionCounters
    raw_prompt_retained: Literal[False]
    raw_output_retained: Literal[False]


class RuntimeImportClosureReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    return_code: Literal[1]
    pythonpath_exact_target_site: Literal[True]
    raw_import_output_retained: Literal[False]
    stderr_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stdout_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    versions: None


class RuntimeInstallReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    return_code: Literal[0]
    network_access_permitted: Literal[False]
    raw_install_output_retained: Literal[False]
    duration_ms: int = Field(gt=0)
    stderr_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stdout_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RuntimeSourceIdentityReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    source_main_commit: Literal["e13882628559ec0f8f3364cc27ce574cbdd92806"]
    notebook_name: Literal["ag-p4-output-contract-diagnostic-v1"]
    executed_runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ModelSnapshotReport(ExternalModel):
    status: Literal["PASSED"]
    governed_model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    file_count: Literal[10]
    total_bytes: int = Field(gt=0)


class WheelhouseReport(ExternalModel):
    status: Literal["PASSED"]
    wheel_count: Literal[176]
    governed_control_hash_count: Literal[8]


class RequestResults(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["NOT_RUN"]
    scheduled_request_count: Literal[18]
    observed_request_count: Literal[0]
    results: tuple[object, ...]

    @model_validator(mode="after")
    def validate_empty_results(self) -> Self:
        if self.results:
            raise ValueError("request results must be empty")
        return self


class SelectionReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["INELIGIBLE_PARTIAL_EVIDENCE"]
    eligible_case_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_empty_selection(self) -> Self:
        if self.eligible_case_ids:
            raise ValueError("eligible case IDs must be empty")
        return self

    selected_case_id: None


class WorkerStartupReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    stage: Literal["worker_startup"]
    status: Literal["NOT_RUN"]


class WorkerTeardownReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["NOT_REQUIRED"]
    process_absent: Literal[True]
    capture_threads_finalized: Literal[True]
    return_code: None


class ScratchCleanupReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["PASSED"]
    scratch_exists_after_cleanup: Literal[False]
    error_type: None


class AuthorizationEvidence(ExternalModel):
    schema_version: Literal["2.0.0"]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v2"
    ]
    issued_from_main_commit: Literal["73f5962ed6852b744c3fed8e1a2e7de4fb424462"]
    lifecycle: Literal["ISSUED"]
    decision: Literal["AUTHORIZED"]
    scope: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"]
    single_use: Literal[True]
    unchanged_replay_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]


class ConsumptionEvidence(ExternalModel):
    schema_version: Literal["2.0.0"]
    consumption_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-consumption-v2"
    ]
    authorization_id: Literal[
        "auragateway-p4-output-contract-diagnostic-execution-authorization-v2"
    ]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["FAILED"]
    saved_version_id: Literal[340622392]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_classify_p4_output_contract_diagnostic_v1"]


class AbandonmentEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["ABANDONED_BEFORE_EXECUTION"]
    authorization_reusable: Literal[False]
    no_saved_version_created: Literal[True]
    runtime_execution_performed: Literal[False]
    runtime_install_attempts: Literal[0]
    model_loads: Literal[0]
    worker_starts: Literal[0]
    model_requests: Literal[0]


class ManifestMember(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class BundleManifest(ExternalModel):
    schema_version: Literal["1.0.0"]
    member_count: Literal[14]
    members: tuple[ManifestMember, ...]
    raw_output_included: Literal[False]


class LimitationsEvidence(StrictModel):
    schema_version: Literal["1.0.0"]
    saved_version_id: Literal[340622392]
    root_cause_status: Literal["UNRESOLVED"]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]


class IntakeManifestRow(StrictModel):
    filename: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


def _canonical(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FailureAcceptanceError(
            "P4_FAILURE_ACCEPTANCE_JSON_INVALID",
            "required JSON could not be loaded",
            path.as_posix(),
        ) from exc


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(_canonical(payload), encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _require(
    condition: bool,
    error_code: str,
    safe_message: str,
    path: Path | None = None,
) -> None:
    if condition:
        return
    raise FailureAcceptanceError(
        error_code,
        safe_message,
        path.as_posix() if path is not None else None,
    )


def _load_model(model: type[BaseModel], path: Path) -> BaseModel:
    try:
        return model.model_validate(_read_json(path))
    except ValidationError as exc:
        raise FailureAcceptanceError(
            "P4_FAILURE_ACCEPTANCE_SCHEMA_INVALID",
            "evidence schema validation failed",
            path.as_posix(),
        ) from exc


def _load_policy(root: Path) -> FailureAcceptancePolicy:
    path = root / POLICY_PATH
    _require(path.is_file(), "P4_FAILURE_ACCEPTANCE_POLICY_MISSING", "policy is missing", path)
    _require(
        _file_sha256(path) == POLICY_SHA256,
        "P4_FAILURE_ACCEPTANCE_POLICY_IDENTITY_DRIFT",
        "policy identity drifted",
        path,
    )
    try:
        return FailureAcceptancePolicy.model_validate(_read_json(path))
    except ValidationError as exc:
        raise FailureAcceptanceError(
            "P4_FAILURE_ACCEPTANCE_POLICY_INVALID",
            "policy schema validation failed",
            path.as_posix(),
        ) from exc


def _artifact_receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = root / relative
    _require(
        path.is_file(), "P4_FAILURE_ACCEPTANCE_ARTIFACT_MISSING", "artifact is missing", relative
    )
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_file_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _validate_exact_receipts(root: Path, receipts: tuple[ArtifactReceipt, ...]) -> None:
    observed_paths: set[str] = set()
    for receipt in receipts:
        _require(
            receipt.path not in observed_paths,
            "P4_FAILURE_ACCEPTANCE_DUPLICATE_RECEIPT",
            "duplicate receipt path",
        )
        observed_paths.add(receipt.path)
        observed = _artifact_receipt(root, Path(receipt.path))
        _require(
            observed == receipt,
            "P4_FAILURE_ACCEPTANCE_RECEIPT_DRIFT",
            "artifact receipt drifted",
            Path(receipt.path),
        )


def _normalize_zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    _require(
        not path.is_absolute(), "P4_FAILURE_ACCEPTANCE_ARCHIVE_UNSAFE", "archive member is absolute"
    )
    _require(
        ".." not in path.parts,
        "P4_FAILURE_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member escapes root",
    )
    _require(
        not re.match(r"^[A-Za-z]:", normalized),
        "P4_FAILURE_ACCEPTANCE_ARCHIVE_UNSAFE",
        "archive member has drive prefix",
    )
    return path.as_posix()


def _safe_zip_members(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            members: dict[str, bytes] = {}
            for info in archive.infolist():
                if info.is_dir():
                    continue
                normalized = _normalize_zip_name(info.filename)
                _require(
                    normalized not in members,
                    "P4_FAILURE_ACCEPTANCE_ARCHIVE_DUPLICATE",
                    "archive member is duplicated",
                    path,
                )
                members[normalized] = archive.read(info)
            return members
    except (OSError, zipfile.BadZipFile) as exc:
        raise FailureAcceptanceError(
            "P4_FAILURE_ACCEPTANCE_ARCHIVE_INVALID",
            "evidence archive is invalid",
            path.as_posix(),
        ) from exc


def _evidence_path(policy: FailureAcceptancePolicy, filename: str) -> Path:
    matches = [
        Path(receipt.path)
        for receipt in policy.evidence_receipts
        if Path(receipt.path).name == filename
    ]
    _require(
        len(matches) == 1,
        "P4_FAILURE_ACCEPTANCE_EVIDENCE_PATH_AMBIGUOUS",
        "evidence path is missing or ambiguous",
    )
    return matches[0]


def _validate_archives(root: Path, policy: FailureAcceptancePolicy) -> None:
    runtime_zip_path = root / _evidence_path(
        policy, "ag-p4-output-contract-evidence-v1-340622392.zip"
    )
    intake_path = root / _evidence_path(
        policy, "AuraGateway_P4_Failure_Evidence_Intake_340622392.zip"
    )
    runtime_members = _safe_zip_members(runtime_zip_path)
    expected_runtime_names = set(policy.runtime_member_targets)
    _require(
        set(runtime_members) == expected_runtime_names,
        "P4_FAILURE_ACCEPTANCE_RUNTIME_ARCHIVE_BOUNDARY_DRIFT",
        "runtime archive member boundary drifted",
        runtime_zip_path,
    )
    for member_name, target in policy.runtime_member_targets.items():
        _require(
            runtime_members[member_name] == (root / target).read_bytes(),
            "P4_FAILURE_ACCEPTANCE_RUNTIME_ARCHIVE_BYTE_DRIFT",
            "runtime archive member bytes drifted",
            Path(target),
        )
    intake_members = _safe_zip_members(intake_path)
    expected_intake_names = {policy.intake_prefix + name for name in expected_runtime_names}
    expected_intake_names.add(policy.intake_prefix + "ag-p4-output-contract-evidence-v1.zip")
    _require(
        set(intake_members) == expected_intake_names,
        "P4_FAILURE_ACCEPTANCE_INTAKE_ARCHIVE_BOUNDARY_DRIFT",
        "intake archive member boundary drifted",
        intake_path,
    )
    for member_name, target in policy.runtime_member_targets.items():
        _require(
            intake_members[policy.intake_prefix + member_name] == (root / target).read_bytes(),
            "P4_FAILURE_ACCEPTANCE_INTAKE_ARCHIVE_BYTE_DRIFT",
            "intake archive member bytes drifted",
            Path(target),
        )
    _require(
        intake_members[policy.intake_prefix + "ag-p4-output-contract-evidence-v1.zip"]
        == runtime_zip_path.read_bytes(),
        "P4_FAILURE_ACCEPTANCE_NESTED_ARCHIVE_DRIFT",
        "nested runtime archive bytes drifted",
        runtime_zip_path,
    )


def _validate_runtime_manifest(root: Path, policy: FailureAcceptancePolicy) -> None:
    path = root / policy.runtime_member_targets["bundle_manifest_v1.json"]
    manifest = cast(BundleManifest, _load_model(BundleManifest, path))
    _require(
        len(manifest.members) == 14,
        "P4_FAILURE_ACCEPTANCE_MANIFEST_COUNT_DRIFT",
        "runtime manifest count drifted",
        path,
    )
    expected = {name for name in policy.runtime_member_targets if name != "bundle_manifest_v1.json"}
    observed = {member.path for member in manifest.members}
    _require(
        observed == expected,
        "P4_FAILURE_ACCEPTANCE_MANIFEST_BOUNDARY_DRIFT",
        "runtime manifest boundary drifted",
        path,
    )
    by_name = {member.path: member for member in manifest.members}
    for name in expected:
        target = Path(policy.runtime_member_targets[name])
        receipt = _artifact_receipt(root, target)
        _require(
            by_name[name].sha256 == receipt.sha256
            and by_name[name].size_bytes == receipt.size_bytes,
            "P4_FAILURE_ACCEPTANCE_MANIFEST_RECEIPT_DRIFT",
            "runtime manifest receipt drifted",
            target,
        )


def _validate_intake_manifest(root: Path, policy: FailureAcceptancePolicy) -> None:
    path = root / _evidence_path(policy, "intake_manifest_v1-340622392.csv")
    rows: list[IntakeManifestRow] = []
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            _require(
                reader.fieldnames == ["filename", "sha256", "size_bytes"],
                "P4_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_HEADER_DRIFT",
                "intake manifest header drifted",
                path,
            )
            for row in reader:
                rows.append(
                    IntakeManifestRow(
                        filename=row["filename"],
                        sha256=row["sha256"],
                        size_bytes=int(row["size_bytes"]),
                    )
                )
    except (OSError, ValueError, ValidationError) as exc:
        raise FailureAcceptanceError(
            "P4_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_INVALID",
            "intake manifest is invalid",
            path.as_posix(),
        ) from exc
    expected_filenames = {
        Path(receipt.path).name
        for receipt in policy.evidence_receipts
        if Path(receipt.path).name != path.name
    }
    _require(
        {row.filename for row in rows} == expected_filenames,
        "P4_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_COUNT_DRIFT",
        "intake manifest boundary drifted",
        path,
    )
    for row in rows:
        target = _evidence_path(policy, row.filename)
        observed = _artifact_receipt(root, target)
        _require(
            observed.sha256 == row.sha256 and observed.size_bytes == row.size_bytes,
            "P4_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_RECEIPT_DRIFT",
            "intake manifest receipt drifted",
            target,
        )


def _validate_runtime_models(root: Path, policy: FailureAcceptancePolicy) -> None:
    def load(name: str, model: type[BaseModel]) -> BaseModel:
        return _load_model(model, root / policy.runtime_member_targets[name])

    summary = cast(
        DiagnosticSummary, load("p4_output_contract_diagnostic_summary_v1.json", DiagnosticSummary)
    )
    failure = cast(FailureReport, load("failure_report_v1.json", FailureReport))
    import_report = cast(
        RuntimeImportClosureReport,
        load("runtime_import_closure_report_v1.json", RuntimeImportClosureReport),
    )
    install = cast(
        RuntimeInstallReport, load("runtime_install_report_v1.json", RuntimeInstallReport)
    )
    source = cast(
        RuntimeSourceIdentityReport,
        load("runtime_source_identity_report_v1.json", RuntimeSourceIdentityReport),
    )
    model = cast(ModelSnapshotReport, load("model_snapshot_report_v1.json", ModelSnapshotReport))
    cast(WheelhouseReport, load("wheelhouse_report_v1.json", WheelhouseReport))
    cast(RequestResults, load("request_results_v1.json", RequestResults))
    cast(SelectionReport, load("selection_report_v1.json", SelectionReport))
    cast(WorkerStartupReport, load("worker_startup_report_v1.json", WorkerStartupReport))
    cast(WorkerTeardownReport, load("worker_teardown_report_v1.json", WorkerTeardownReport))
    cast(ScratchCleanupReport, load("scratch_cleanup_report_v1.json", ScratchCleanupReport))
    _require(
        summary.counters == failure.counters,
        "P4_FAILURE_ACCEPTANCE_COUNTER_DRIFT",
        "summary and failure counters disagree",
    )
    _require(
        import_report.stderr_sha256 == policy.expected_hashes.runtime_stderr,
        "P4_FAILURE_ACCEPTANCE_STDERR_IDENTITY_DRIFT",
        "runtime stderr identity drifted",
    )
    _require(
        import_report.stdout_sha256 == policy.expected_hashes.runtime_stdout,
        "P4_FAILURE_ACCEPTANCE_STDOUT_IDENTITY_DRIFT",
        "runtime stdout identity drifted",
    )
    _require(
        source.executed_runtime_script_sha256 == policy.expected_hashes.runtime_script,
        "P4_FAILURE_ACCEPTANCE_RUNTIME_SCRIPT_DRIFT",
        "runtime script identity drifted",
    )
    _require(
        model.governed_model_snapshot_sha256 == policy.expected_hashes.model_snapshot,
        "P4_FAILURE_ACCEPTANCE_MODEL_IDENTITY_DRIFT",
        "model snapshot identity drifted",
    )
    _require(
        install.network_access_permitted is False,
        "P4_FAILURE_ACCEPTANCE_NETWORK_POLICY_DRIFT",
        "runtime installation allowed network access",
    )


def _validate_lifecycle(root: Path, policy: FailureAcceptancePolicy) -> None:
    abandonment_path = root / _evidence_path(
        policy, "execution_authorization_abandonment_v1-340622392.json"
    )
    authorization_path = root / _evidence_path(policy, "execution_authorization_v2-340622392.json")
    consumption_path = root / _evidence_path(
        policy, "execution_authorization_consumption_v2-340622392.json"
    )
    cast(AbandonmentEvidence, _load_model(AbandonmentEvidence, abandonment_path))
    cast(AuthorizationEvidence, _load_model(AuthorizationEvidence, authorization_path))
    consumption = cast(ConsumptionEvidence, _load_model(ConsumptionEvidence, consumption_path))
    _require(
        _file_sha256(abandonment_path) == policy.expected_hashes.abandonment,
        "P4_FAILURE_ACCEPTANCE_ABANDONMENT_DRIFT",
        "abandonment identity drifted",
        abandonment_path,
    )
    authorization_sha = _file_sha256(authorization_path)
    _require(
        authorization_sha == policy.expected_hashes.authorization,
        "P4_FAILURE_ACCEPTANCE_AUTHORIZATION_DRIFT",
        "authorization identity drifted",
        authorization_path,
    )
    _require(
        _file_sha256(consumption_path) == policy.expected_hashes.consumption,
        "P4_FAILURE_ACCEPTANCE_CONSUMPTION_DRIFT",
        "consumption identity drifted",
        consumption_path,
    )
    _require(
        consumption.authorization_sha256 == authorization_sha,
        "P4_FAILURE_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption is not bound to authorization",
    )


def _validate_logs_and_limits(root: Path, policy: FailureAcceptancePolicy) -> None:
    log_path = root / _evidence_path(policy, "ag-p4-output-contract-diagnostic-v1-340622392.log")
    text = log_path.read_text(encoding="utf-8")
    for token in policy.expected_terminal_log_tokens:
        _require(
            token in text,
            "P4_FAILURE_ACCEPTANCE_TERMINAL_LOG_TOKEN_MISSING",
            "terminal log token is missing",
            log_path,
        )
    limitations_path = root / _evidence_path(policy, "evidence_limitations_v1-340622392.json")
    limitations = cast(LimitationsEvidence, _load_model(LimitationsEvidence, limitations_path))
    _require(
        len(limitations.limitations) >= 4,
        "P4_FAILURE_ACCEPTANCE_LIMITATIONS_INCOMPLETE",
        "evidence limitations are incomplete",
        limitations_path,
    )
    _require(
        len(limitations.non_claims) >= 5,
        "P4_FAILURE_ACCEPTANCE_NON_CLAIMS_INCOMPLETE",
        "non-claims are incomplete",
        limitations_path,
    )


def _validate_operational_paths_absent(root: Path, policy: FailureAcceptancePolicy) -> None:
    present = [path for path in policy.operational_transient_paths if (root / path).exists()]
    _require(
        not present,
        "P4_FAILURE_ACCEPTANCE_TRANSIENT_PATH_PRESENT",
        "operational transient lifecycle path remains present",
    )


def validate_evidence(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    _validate_exact_receipts(root, policy.evidence_receipts)
    _validate_exact_receipts(root, policy.repository_authorities)
    _validate_archives(root, policy)
    _validate_runtime_manifest(root, policy)
    _validate_intake_manifest(root, policy)
    _validate_runtime_models(root, policy)
    _validate_lifecycle(root, policy)
    _validate_logs_and_limits(root, policy)
    _validate_operational_paths_absent(root, policy)
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_EVIDENCE_V1_VALID",
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "first_divergence": policy.first_divergence,
        "root_cause_status": policy.root_cause_status,
        "runtime_install_status": "PASSED",
        "runtime_import_closure_status": "FAILED",
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "runtime_execution_authorized": False,
        "next_gate": policy.next_gate,
    }


def build_review(policy: FailureAcceptancePolicy) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "review_id": "auragateway-p4-output-contract-diagnostic-failure-acceptance-v1-review",
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_V1_CLASSIFIED",
        "decision": (
            "ACCEPT_VALID_GOVERNED_FAILURE_AND_DESIGN_P4_RUNTIME_IMPORT_CLOSURE_DIAGNOSTIC_V1"
        ),
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "current_main_authority": policy.current_main_authority,
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "first_divergence": policy.first_divergence,
        "reported_failure_code": policy.reported_failure_code,
        "safe_failure_message": policy.safe_failure_message,
        "runtime_source_identity_status": "PASSED",
        "model_snapshot_status": "PASSED",
        "wheelhouse_status": "PASSED",
        "runtime_install_status": "PASSED",
        "runtime_import_closure_status": "FAILED",
        "worker_startup_status": "NOT_RUN",
        "request_matrix_status": "NOT_RUN",
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "root_cause_status": policy.root_cause_status,
        "unresolved_hypotheses": [
            "PYTHON_IMPORT_RESOLUTION_FAILURE",
            "NATIVE_LIBRARY_LOAD_FAILURE",
            "RUNTIME_ABI_INCOMPATIBILITY",
            "PINNED_PACKAGE_IMPORT_INCOMPATIBILITY",
            "SUBPROCESS_ENVIRONMENT_DIVERGENCE",
            "OTHER_IMPORT_TIME_EXCEPTION",
        ],
        "selected_next_diagnostic": [
            "execute one offline target-runtime import-closure probe",
            "retain exception class and failing import step",
            "retain module name and sanitized final traceback-frame metadata",
            "retain native-library basename when safely extractable",
            "retain stdout and stderr hashes without raw paths or environment values",
            "perform zero model loads, worker starts, or model requests",
            "stop after the first classified import divergence",
        ],
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "next_gate": policy.next_gate,
        "non_claims": [
            "The exact import exception is unknown.",
            (
                "The failure is not attributed to Python, native loading, "
                "CUDA ABI, vLLM, or another package."
            ),
            "The A-F output-contract cases were not executed.",
            "P4 exact-object reliability is not established.",
            "JSON-schema compatibility is not established.",
            "P5 and P6 are not established on the current successor line.",
            "Measured A/B/C was not performed or authorized.",
            "The failed notebook is not authorized for unchanged replay.",
            "Deployment and production readiness are not established.",
        ],
    }


def build_record(root: Path, policy: FailureAcceptancePolicy) -> dict[str, object]:
    evidence = [receipt.model_dump(mode="json") for receipt in policy.evidence_receipts]
    authorities = [receipt.model_dump(mode="json") for receipt in policy.repository_authorities]
    return {
        "schema_version": "1.0.0",
        "record_id": "auragateway-p4-output-contract-diagnostic-failure-acceptance-v1",
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID",
        "current_main_authority": policy.current_main_authority,
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "first_divergence": policy.first_divergence,
        "reported_failure_code": policy.reported_failure_code,
        "root_cause_status": policy.root_cause_status,
        "runtime_install_status": "PASSED",
        "runtime_import_closure_status": "FAILED",
        "worker_startup_status": "NOT_RUN",
        "request_matrix_status": "NOT_RUN",
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "p4_exact_object_contract_established": False,
        "json_schema_compatibility_established": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "policy": _artifact_receipt(root, POLICY_PATH).model_dump(mode="json"),
        "source": _artifact_receipt(root, SOURCE_PATH).model_dump(mode="json"),
        "tests": _artifact_receipt(root, TEST_PATH).model_dump(mode="json"),
        "adr": _artifact_receipt(root, ADR_PATH).model_dump(mode="json"),
        "report": _artifact_receipt(root, REPORT_PATH).model_dump(mode="json"),
        "runbook": _artifact_receipt(root, RUNBOOK_PATH).model_dump(mode="json"),
        "review": _artifact_receipt(root, REVIEW_PATH).model_dump(mode="json"),
        "repository_authorities": authorities,
        "evidence": evidence,
        "next_gate": policy.next_gate,
    }


def generate(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    evidence = validate_evidence(root)
    _write_json(root / REVIEW_PATH, build_review(policy))
    _write_json(root / RECORD_PATH, build_record(root, policy))
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_GENERATED",
        "saved_version_id": policy.saved_version_id,
        "review_sha256": _file_sha256(root / REVIEW_PATH),
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "evidence_status": evidence["status"],
        "runtime_execution_authorized": False,
    }


def validate_package(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    evidence = validate_evidence(root)
    expected_review = _canonical(build_review(policy))
    _require(
        (root / REVIEW_PATH).read_text(encoding="utf-8") == expected_review,
        "P4_FAILURE_ACCEPTANCE_REVIEW_DRIFT",
        "stored review drifted",
        REVIEW_PATH,
    )
    expected_record = _canonical(build_record(root, policy))
    _require(
        (root / RECORD_PATH).read_text(encoding="utf-8") == expected_record,
        "P4_FAILURE_ACCEPTANCE_RECORD_DRIFT",
        "stored record drifted",
        RECORD_PATH,
    )
    return {
        "status": "P4_OUTPUT_CONTRACT_DIAGNOSTIC_FAILURE_ACCEPTANCE_V1_VALID",
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "first_divergence": policy.first_divergence,
        "root_cause_status": policy.root_cause_status,
        "runtime_execution_authorized": False,
        "measured_abc_authorized": False,
        "next_gate": policy.next_gate,
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "review_sha256": _file_sha256(root / REVIEW_PATH),
        "evidence_status": evidence["status"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="p4-output-contract-diagnostic-failure-acceptance-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate-evidence", "generate", "validate-package"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        root = args.repo_root.resolve()
        if args.command == "validate-evidence":
            result = validate_evidence(root)
        elif args.command == "generate":
            result = generate(root)
        else:
            result = validate_package(root)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except FailureAcceptanceError as exc:
        print(json.dumps(exc.envelope(), sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
