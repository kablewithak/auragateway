"""Accept and classify the governed P3-P6 runtime diagnostic V4 failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p3_p6_runtime_failure_acceptance_v4_policy.json"
)
POLICY_SHA256: Final = "af892d07ea330190cd963f09719ff97fc1644da57a603eeefc5e22e261748956"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v4.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v4.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-04-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v4.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V4.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v4.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "failure_acceptance_v4_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v4.json"
)


class FailureAcceptanceError(RuntimeError):
    """Fail-closed V4 failure-acceptance error."""

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
            "P3_P6_V4_FAILURE_ACCEPTANCE_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical(self.model_dump(mode="json"))


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class AuthorityReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExpectedHashes(StrictModel):
    intake_archive: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    kaggle_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code: str = Field(pattern=r"^[0-9a-f]{64}$")


class FailureAcceptancePolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-p3-p6-runtime-diagnostic-failure-acceptance-v4-policy"]
    current_main_authority: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_issuer_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    runtime_source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    saved_version_id: Literal[340120168]
    next_gate: Literal["design_and_merge_p3_p6_runtime_diagnostic_v5"]
    first_divergence: Literal["P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"]
    reported_failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    safe_failure_message: Literal["structured response differs from the requested object"]
    expected_hashes: ExpectedHashes
    evidence_receipts: tuple[ArtifactReceipt, ...]
    intake_member_targets: dict[str, str]
    runtime_member_targets: dict[str, str]
    repository_authorities: tuple[AuthorityReceipt, ...]
    operational_authorization_path: str
    operational_consumption_path: str
    expected_log_tokens: tuple[str, ...]

    @model_validator(mode="after")
    def validate_boundaries(self) -> Self:
        if len(self.evidence_receipts) != 25:
            raise ValueError("evidence receipt count drifted")
        if len(self.intake_member_targets) != 25:
            raise ValueError("intake member target count drifted")
        if len(self.runtime_member_targets) != 13:
            raise ValueError("runtime member target count drifted")
        if len(self.repository_authorities) != 6:
            raise ValueError("repository authority count drifted")
        if len(self.expected_log_tokens) != 6:
            raise ValueError("terminal log token count drifted")
        return self


class ActionCounters(StrictModel):
    benchmark_trajectory_requests: Literal[0]
    external_spend: Literal[0]
    hidden_retries: Literal[0]
    kaggle_sessions: Literal[1]
    model_loads: Literal[3]
    model_requests: Literal[4]
    network_requests: Literal[0]
    runtime_import_closure_probes: Literal[1]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[3]


class DiagnosticSummary(ExternalModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v4"]
    source_main_commit: Literal["0f7b2c125e407927c47143f04ed137c90d838f5b"]
    status: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4_FAILED"]
    completed_probes: tuple[Literal["P3", "P4", "P5"], ...]
    failed_probe: Literal["P6"]
    failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    runtime_install_status: Literal["PASSED"]
    runtime_install_process_outcome: Literal["PASSED"]
    runtime_import_closure_status: Literal["PASSED"]
    runtime_import_closure_process_outcome: Literal["PASSED"]
    runtime_source_identity_status: Literal["PASSED"]
    scratch_cleanup_status: Literal["PASSED"]
    scratch_exists_after_cleanup: Literal[False]
    worker_teardown_status: Literal["PASSED"]
    stop_on_first_failure: Literal[True]
    counters: ActionCounters
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    network_access_permitted: Literal[False]
    measured_abc_execution_performed: Literal[False]
    executed_runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    next_gate: Literal["preserve_and_classify_p3_p6_runtime_failure_v4"]

    @model_validator(mode="after")
    def validate_completed_probe_order(self) -> Self:
        if self.completed_probes != ("P3", "P4", "P5"):
            raise ValueError("completed probe order drifted")
        return self


class BackendMarkerEvidence(ExternalModel):
    marker: Literal["Using AttentionBackendEnum.TRITON_ATTN backend."]
    line_local_match: Literal[True]
    cli_echo_rejected: Literal[True]
    normalized_line_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    line_number: int = Field(gt=0)
    stream: Literal["stdout", "stderr"]


class WorkerTeardown(ExternalModel):
    status: Literal["PASSED"]
    process_tree_absent_after: Literal[True]
    gpu_processes_absent_after: Literal[True]
    port_closed_after: Literal[True]
    capture_threads_finalized: Literal[True]
    memory_returned_within_tolerance: Literal[True]


class WorkerDiagnostics(ExternalModel):
    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    pythonpath_exact_target_site: Literal[True]
    backend_marker_evidence: BackendMarkerEvidence
    stdout_tail: str
    stderr_tail: str
    teardown: WorkerTeardown


class FailureReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    failed_after: tuple[Literal["P3", "P4", "P5"], ...]
    failed_probe: Literal["P6"]
    error_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    error_type: Literal["RuntimeError"]
    safe_message: Literal["structured response differs from the requested object"]
    teardown_status: Literal["PASSED"]
    worker_1_diagnostics: WorkerDiagnostics
    worker_2_diagnostics: WorkerDiagnostics

    @model_validator(mode="after")
    def validate_workers(self) -> Self:
        if self.failed_after != ("P3", "P4", "P5"):
            raise ValueError("failure predecessor sequence drifted")
        if self.worker_1_diagnostics.worker_id != "worker_1":
            raise ValueError("worker 1 identity drifted")
        if self.worker_1_diagnostics.gpu_index != 0:
            raise ValueError("worker 1 GPU identity drifted")
        if self.worker_2_diagnostics.worker_id != "worker_2":
            raise ValueError("worker 2 identity drifted")
        if self.worker_2_diagnostics.gpu_index != 1:
            raise ValueError("worker 2 GPU identity drifted")
        return self


class P3Report(ExternalModel):
    probe_id: Literal["P3"]
    status: Literal["PASSED"]
    decision: Literal["ONE_WORKER_TRITON_STARTUP_PASSED"]
    worker: dict[str, object]


class P4Request(ExternalModel):
    structured_output_valid: Literal[True]
    completion_tokens: int = Field(ge=1, le=32)
    prompt_tokens: int = Field(gt=0)


class P4Report(ExternalModel):
    probe_id: Literal["P4"]
    status: Literal["PASSED"]
    decision: Literal["ONE_REQUEST_RUNTIME_COMPATIBILITY_PASSED"]
    request: P4Request
    raw_prompt_logged: Literal[False]
    raw_output_logged: Literal[False]


class P5Report(ExternalModel):
    probe_id: Literal["P5"]
    status: Literal["PASSED"]
    decision: Literal["CACHE_SMOKE_AND_RESET_PASSED"]
    same_worker_prefix_reuse_proven: Literal[True]
    full_process_restart_reset_proven: Literal[True]
    namespace_only_reset_used: Literal[False]


class P6TerminalReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P6"]
    status: Literal["FAILED"]
    decision: Literal["P6_FAILED"]
    blocked_by: None
    failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    completed_probes_before_terminal_state: tuple[Literal["P3", "P4", "P5"], ...]
    model_requests_performed: Literal[False]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]

    @model_validator(mode="after")
    def validate_predecessors(self) -> Self:
        if self.completed_probes_before_terminal_state != (
            "P3",
            "P4",
            "P5",
        ):
            raise ValueError("P6 predecessor sequence drifted")
        return self


class ManifestMember(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class BundleManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v4"]
    source_main_commit: Literal["0f7b2c125e407927c47143f04ed137c90d838f5b"]
    members: tuple[ManifestMember, ...]
    scratch_directories_included: Literal[False]
    worker_log_directory_included: Literal[False]


class AuthorizationEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v4"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4"]
    issued_from_main_commit: Literal["7d3497015e18300bd1625c2f143eebd796e9ac2f"]
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    single_use: Literal[True]
    unchanged_replay_authorized: Literal[False]
    operator_confirmation_recorded: Literal[True]


class ConsumptionEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    consumption_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-consumption-v4"
    ]
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["FAILED"]
    saved_version_id: Literal[340120168]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False]
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LifecycleReceipt(ExternalModel):
    schema_version: Literal["1.0.0"]
    main_commit: Literal["7d3497015e18300bd1625c2f143eebd796e9ac2f"]
    kaggle_notebook_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v4"]
    kaggle_saved_version_id: Literal[340120168]
    terminal_outcome: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4_FAILED"]
    failed_probe: Literal["P6"]
    failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_probes: tuple[Literal["P3", "P4", "P5"], ...]
    measured_abc_execution_performed: Literal[False]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_completed(self) -> Self:
        if self.completed_probes != ("P3", "P4", "P5"):
            raise ValueError("lifecycle completed probe order drifted")
        return self


class LaunchManifest(ExternalModel):
    schema_version: Literal["1.0.0"]
    execution_scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4"]
    main_commit: Literal["7d3497015e18300bd1625c2f143eebd796e9ac2f"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v4"]
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    credentials_permitted: Literal[False]
    customer_data_permitted: Literal[False]
    expected_vllm_version: Literal["0.19.1"]
    maximum_kaggle_sessions: Literal[1]
    maximum_runtime_install_attempts: Literal[1]
    maximum_model_loads: Literal[3]
    maximum_worker_starts: Literal[3]
    maximum_model_requests: Literal[5]
    unchanged_replay_authorized: Literal[False]


class SavedVersionReference(ExternalModel):
    schema_version: Literal["1.0.0"]
    kaggle_notebook_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v4"]
    kaggle_saved_version_id: Literal[340120168]
    terminal_outcome: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V4_FAILED"]
    source_main_commit_in_runtime: Literal["0f7b2c125e407927c47143f04ed137c90d838f5b"]
    authorization_issued_from_main_commit: Literal["7d3497015e18300bd1625c2f143eebd796e9ac2f"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    governed_notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    executed_runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_probes: tuple[Literal["P3", "P4", "P5"], ...]
    failed_probe: Literal["P6"]
    failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    unchanged_replay_authorized: Literal[False]


class LimitationsEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    evidence_disposition: Literal["ACCEPTED_DIAGNOSTIC_FAILURE_PENDING_REPOSITORY_REVIEW"]
    limitations: tuple[str, ...] = Field(min_length=7)
    non_claims: tuple[str, ...] = Field(min_length=6)


class RootCauseInference(StrictModel):
    statement: str
    confidence: Literal["HIGH"]
    basis: tuple[str, ...] = Field(min_length=4)


class RootCauseEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    classification: Literal["VALID_GOVERNED_DIAGNOSTIC_FAILURE"]
    failure_scope: Literal["P6_ROUTE_RESPONSE_CONTRACT"]
    reported_failure_code: Literal["P3_P6_DUAL_WORKER_ISOLATION_FAILED"]
    first_observed_divergence: Literal["P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"]
    established_facts: tuple[str, ...] = Field(min_length=10)
    inference: RootCauseInference
    evidence_quality_defects: tuple[str, ...] = Field(min_length=3)
    smallest_maintainable_remediation: tuple[str, ...] = Field(min_length=5)
    unchanged_replay_authorized: Literal[False]
    next_gate: Literal["accept_v4_failure_then_design_p3_p6_runtime_diagnostic_v5"]


class IntakeReceipt(ExternalModel):
    schema_version: Literal["1.0.0"]
    repository_main_commit: Literal["7d3497015e18300bd1625c2f143eebd796e9ac2f"]
    repository_branch: Literal["main"]
    repository_transient_boundary_validated: Literal[True]
    transient_files_tracked: Literal[False]
    authorization_lifecycle: Literal["CONSUMED"]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    kaggle_saved_version_id: Literal[340120168]
    terminal_outcome: Literal["FAILED"]
    runtime_evidence_archive_validated: Literal[True]
    runtime_evidence_member_count: Literal[13]
    runtime_evidence_manifest_member_count: Literal[12]
    runtime_evidence_hash_mismatch_count: Literal[0]
    runtime_evidence_missing_member_count: Literal[0]
    runtime_evidence_unexpected_member_count: Literal[0]
    completed_probes: tuple[Literal["P3", "P4", "P5"], ...]
    failed_probe: Literal["P6"]
    first_observed_divergence: Literal["P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"]
    evidence_quality_defect_count: Literal[3]
    raw_prompt_retained: Literal[False]
    raw_model_output_retained: Literal[False]
    customer_data_present: Literal[False]
    credentials_used: Literal[False]
    network_requests: Literal[0]
    external_spend: Literal[0]
    members_before_receipt: tuple[ArtifactReceipt, ...]
    self_receipt_excluded: Literal[True]
    intake_archive_sha256_recorded_externally: Literal[True]
    next_gate: Literal["implement_and_merge_p3_p6_runtime_failure_acceptance_v4"]


def _canonical(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_JSON_INVALID",
            "evidence JSON is missing or invalid",
            path.as_posix(),
        ) from error


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _canonical(payload),
        encoding="utf-8",
        newline="\n",
    )


def _load_policy(root: Path) -> FailureAcceptancePolicy:
    path = root / POLICY_PATH
    if not path.is_file():
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_POLICY_MISSING",
            "failure-acceptance policy is missing",
            POLICY_PATH.as_posix(),
        )
    if _file_sha256(path) != POLICY_SHA256:
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_POLICY_DRIFT",
            "failure-acceptance policy identity drifted",
            POLICY_PATH.as_posix(),
        )
    try:
        return FailureAcceptancePolicy.model_validate(_read_json(path))
    except ValidationError as error:
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_POLICY_INVALID",
            "failure-acceptance policy schema drifted",
            POLICY_PATH.as_posix(),
        ) from error


def _artifact_receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = root / relative
    if not path.is_file():
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_ARTIFACT_MISSING",
            "required package artifact is missing",
            relative.as_posix(),
        )
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_file_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _require(
    condition: bool,
    error_code: str,
    message: str,
    path: Path,
) -> None:
    if condition:
        return
    raise FailureAcceptanceError(
        error_code,
        message,
        path.as_posix(),
    )


def _safe_zip_names(
    archive: zipfile.ZipFile,
    path: Path,
) -> tuple[str, ...]:
    names = tuple(info.filename for info in archive.infolist())
    _require(
        len(names) == len(set(names)),
        "P3_P6_V4_FAILURE_ACCEPTANCE_DUPLICATE_ZIP_MEMBER",
        "evidence ZIP contains duplicate member paths",
        path,
    )
    for name in names:
        member = Path(name)
        safe = (
            bool(name)
            and not member.is_absolute()
            and ".." not in member.parts
            and "\\" not in name
            and not name.endswith("/")
        )
        _require(
            safe,
            "P3_P6_V4_FAILURE_ACCEPTANCE_UNSAFE_ZIP_MEMBER",
            "evidence ZIP contains an unsafe member path",
            path,
        )
    return names


def _validate_exact_receipts(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    for receipt in policy.evidence_receipts:
        relative = Path(receipt.path)
        path = root / relative
        _require(
            path.is_file(),
            "P3_P6_V4_FAILURE_ACCEPTANCE_EVIDENCE_MISSING",
            "required evidence artifact is missing",
            relative,
        )
        _require(
            _file_sha256(path) == receipt.sha256,
            "P3_P6_V4_FAILURE_ACCEPTANCE_EVIDENCE_HASH_MISMATCH",
            "evidence artifact identity drifted",
            relative,
        )
        _require(
            path.stat().st_size == receipt.size_bytes,
            "P3_P6_V4_FAILURE_ACCEPTANCE_EVIDENCE_SIZE_MISMATCH",
            "evidence artifact size drifted",
            relative,
        )


def _validate_intake_archive(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    archive_receipt = next(
        item
        for item in policy.evidence_receipts
        if item.path.endswith("AuraGateway_V4_Failure_Evidence_Intake_340120168.zip")
    )
    archive_path = root / archive_receipt.path
    _require(
        _file_sha256(archive_path) == policy.expected_hashes.intake_archive,
        "P3_P6_V4_FAILURE_ACCEPTANCE_INTAKE_HASH_MISMATCH",
        "intake archive identity drifted",
        Path(archive_receipt.path),
    )
    with zipfile.ZipFile(archive_path) as archive:
        names = _safe_zip_names(
            archive,
            Path(archive_receipt.path),
        )
        expected_names = tuple(sorted(policy.intake_member_targets))
        _require(
            tuple(sorted(names)) == expected_names,
            "P3_P6_V4_FAILURE_ACCEPTANCE_INTAKE_BOUNDARY_DRIFT",
            "intake archive member boundary drifted",
            Path(archive_receipt.path),
        )
        for name in names:
            target = Path(policy.intake_member_targets[name])
            target_path = root / target
            member_sha256 = _sha256_bytes(archive.read(name))
            if (
                _synthetic_fixture()
                and target.as_posix()
                == ("notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v4.ipynb")
                and not target_path.is_file()
            ):
                _require(
                    member_sha256 == policy.expected_hashes.notebook,
                    ("P3_P6_V4_FAILURE_ACCEPTANCE_INTAKE_NOTEBOOK_DRIFT"),
                    "intake notebook identity drifted",
                    target,
                )
                continue
            _require(
                target_path.is_file(),
                "P3_P6_V4_FAILURE_ACCEPTANCE_INTAKE_TARGET_MISSING",
                "intake member target is missing",
                target,
            )
            _require(
                member_sha256 == _file_sha256(target_path),
                "P3_P6_V4_FAILURE_ACCEPTANCE_INTAKE_MEMBER_DRIFT",
                "intake member differs from its preserved target",
                target,
            )


def _runtime_path(
    policy: FailureAcceptancePolicy,
    name: str,
) -> Path:
    return Path(policy.runtime_member_targets[name])


def _validate_runtime_archive(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> BundleManifest:
    evidence_zip_receipt = next(
        item
        for item in policy.evidence_receipts
        if item.path.endswith("ag-cu129-p3-p6-runtime-evidence-v4-340120168.zip")
    )
    archive_path = root / evidence_zip_receipt.path
    _require(
        _file_sha256(archive_path) == policy.expected_hashes.evidence_zip,
        "P3_P6_V4_FAILURE_ACCEPTANCE_RUNTIME_ZIP_HASH_MISMATCH",
        "runtime evidence ZIP identity drifted",
        Path(evidence_zip_receipt.path),
    )
    with zipfile.ZipFile(archive_path) as archive:
        names = _safe_zip_names(
            archive,
            Path(evidence_zip_receipt.path),
        )
        expected_names = tuple(sorted(policy.runtime_member_targets))
        _require(
            tuple(sorted(names)) == expected_names,
            "P3_P6_V4_FAILURE_ACCEPTANCE_RUNTIME_ZIP_BOUNDARY_DRIFT",
            "runtime evidence ZIP member boundary drifted",
            Path(evidence_zip_receipt.path),
        )
        for name in names:
            target = _runtime_path(policy, name)
            target_path = root / target
            _require(
                _sha256_bytes(archive.read(name)) == _file_sha256(target_path),
                "P3_P6_V4_FAILURE_ACCEPTANCE_RUNTIME_MEMBER_DRIFT",
                "runtime ZIP member differs from its preserved target",
                target,
            )

    manifest_path = _runtime_path(
        policy,
        "bundle_manifest_v4.json",
    )
    manifest = BundleManifest.model_validate(_read_json(root / manifest_path))
    expected_manifest_names = set(policy.runtime_member_targets) - {"bundle_manifest_v4.json"}
    observed_manifest_names = {member.path for member in manifest.members}
    _require(
        observed_manifest_names == expected_manifest_names,
        "P3_P6_V4_FAILURE_ACCEPTANCE_MANIFEST_BOUNDARY_DRIFT",
        "runtime bundle manifest boundary drifted",
        manifest_path,
    )
    for member in manifest.members:
        target = _runtime_path(policy, member.path)
        target_path = root / target
        _require(
            _file_sha256(target_path) == member.sha256,
            "P3_P6_V4_FAILURE_ACCEPTANCE_MANIFEST_HASH_MISMATCH",
            "manifest-bound runtime member hash drifted",
            target,
        )
        _require(
            target_path.stat().st_size == member.size_bytes,
            "P3_P6_V4_FAILURE_ACCEPTANCE_MANIFEST_SIZE_MISMATCH",
            "manifest-bound runtime member size drifted",
            target,
        )
    return manifest


def _evidence_path(
    policy: FailureAcceptancePolicy,
    suffix: str,
) -> Path:
    matches = [
        Path(receipt.path) for receipt in policy.evidence_receipts if receipt.path.endswith(suffix)
    ]
    if len(matches) != 1:
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_EVIDENCE_PATH_AMBIGUOUS",
            "expected exactly one evidence path for suffix",
            suffix,
        )
    return matches[0]


def _load_model(
    root: Path,
    path: Path,
    model: type[BaseModel],
) -> BaseModel:
    try:
        return model.model_validate(_read_json(root / path))
    except ValidationError as error:
        raise FailureAcceptanceError(
            "P3_P6_V4_FAILURE_ACCEPTANCE_SCHEMA_INVALID",
            "evidence schema or reviewed literal drifted",
            path.as_posix(),
        ) from error


def _validate_models(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> dict[str, object]:
    authorization_path = _evidence_path(
        policy,
        "execution_authorization_v4-340120168.json",
    )
    consumption_path = _evidence_path(
        policy,
        "execution_authorization_consumption_v4-340120168.json",
    )
    lifecycle_path = _evidence_path(
        policy,
        "authorization_lifecycle_receipt_v4-340120168.json",
    )
    launch_path = _evidence_path(
        policy,
        "execution_launch_manifest_v4-340120168.json",
    )
    reference_path = _evidence_path(
        policy,
        "kaggle_saved_version_reference_v4-340120168.json",
    )
    limitations_path = _evidence_path(
        policy,
        "evidence_limitations_v4-340120168.json",
    )
    root_cause_path = _evidence_path(
        policy,
        "root_cause_analysis_v4-340120168.json",
    )
    intake_path = _evidence_path(
        policy,
        "intake_validation_receipt_v4-340120168.json",
    )
    log_path = _evidence_path(
        policy,
        "ag-cu129-p3-p6-runtime-diagnostic-v4-340120168.log",
    )

    authorization = cast(
        AuthorizationEvidence,
        _load_model(
            root,
            authorization_path,
            AuthorizationEvidence,
        ),
    )
    consumption = cast(
        ConsumptionEvidence,
        _load_model(
            root,
            consumption_path,
            ConsumptionEvidence,
        ),
    )
    lifecycle = cast(
        LifecycleReceipt,
        _load_model(
            root,
            lifecycle_path,
            LifecycleReceipt,
        ),
    )
    launch = cast(
        LaunchManifest,
        _load_model(
            root,
            launch_path,
            LaunchManifest,
        ),
    )
    reference = cast(
        SavedVersionReference,
        _load_model(
            root,
            reference_path,
            SavedVersionReference,
        ),
    )
    limitations = cast(
        LimitationsEvidence,
        _load_model(
            root,
            limitations_path,
            LimitationsEvidence,
        ),
    )
    root_cause = cast(
        RootCauseEvidence,
        _load_model(
            root,
            root_cause_path,
            RootCauseEvidence,
        ),
    )
    intake = cast(
        IntakeReceipt,
        _load_model(
            root,
            intake_path,
            IntakeReceipt,
        ),
    )

    summary_path = _runtime_path(
        policy,
        "p3_p6_runtime_diagnostic_summary_v4.json",
    )
    failure_path = _runtime_path(
        policy,
        "failure_report_v4.json",
    )
    p3_path = _runtime_path(
        policy,
        "p3_worker_startup_report_v4.json",
    )
    p4_path = _runtime_path(
        policy,
        "p4_deterministic_request_report_v4.json",
    )
    p5_path = _runtime_path(
        policy,
        "p5_prefix_cache_reset_report_v4.json",
    )
    p6_path = _runtime_path(
        policy,
        "p6_dual_worker_isolation_report_v4.json",
    )

    summary = cast(
        DiagnosticSummary,
        _load_model(
            root,
            summary_path,
            DiagnosticSummary,
        ),
    )
    failure = cast(
        FailureReport,
        _load_model(
            root,
            failure_path,
            FailureReport,
        ),
    )
    p3 = cast(
        P3Report,
        _load_model(root, p3_path, P3Report),
    )
    p4 = cast(
        P4Report,
        _load_model(root, p4_path, P4Report),
    )
    p5 = cast(
        P5Report,
        _load_model(root, p5_path, P5Report),
    )
    p6 = cast(
        P6TerminalReport,
        _load_model(root, p6_path, P6TerminalReport),
    )

    _require(
        _file_sha256(root / authorization_path) == policy.expected_hashes.authorization,
        "P3_P6_V4_FAILURE_ACCEPTANCE_AUTHORIZATION_HASH_MISMATCH",
        "authorization evidence identity drifted",
        authorization_path,
    )
    _require(
        _file_sha256(root / consumption_path) == policy.expected_hashes.consumption,
        "P3_P6_V4_FAILURE_ACCEPTANCE_CONSUMPTION_HASH_MISMATCH",
        "consumption evidence identity drifted",
        consumption_path,
    )
    _require(
        _file_sha256(root / log_path) == policy.expected_hashes.kaggle_log,
        "P3_P6_V4_FAILURE_ACCEPTANCE_LOG_HASH_MISMATCH",
        "Kaggle terminal log identity drifted",
        log_path,
    )

    log_text = (root / log_path).read_text(encoding="utf-8")
    for token in policy.expected_log_tokens:
        _require(
            token in log_text,
            "P3_P6_V4_FAILURE_ACCEPTANCE_LOG_TOKEN_MISSING",
            "Kaggle terminal log is missing a required terminal token",
            log_path,
        )

    worker_1_posts = len(
        re.findall(
            r"POST /v1/chat/completions",
            failure.worker_1_diagnostics.stdout_tail,
        )
    )
    worker_2_posts = len(
        re.findall(
            r"POST /v1/chat/completions",
            failure.worker_2_diagnostics.stdout_tail,
        )
    )
    _require(
        worker_1_posts == 2,
        "P3_P6_V4_FAILURE_ACCEPTANCE_WORKER_1_REQUEST_TRACE_DRIFT",
        "worker 1 retained completion-request count drifted",
        failure_path,
    )
    _require(
        worker_2_posts == 0,
        "P3_P6_V4_FAILURE_ACCEPTANCE_WORKER_2_REQUEST_TRACE_DRIFT",
        "worker 2 unexpectedly retained a completion request",
        failure_path,
    )
    _require(
        summary.counters.model_requests == 4,
        "P3_P6_V4_FAILURE_ACCEPTANCE_REQUEST_COUNTER_DRIFT",
        "global model-request counter drifted",
        summary_path,
    )
    _require(
        p6.model_requests_performed is False,
        "P3_P6_V4_FAILURE_ACCEPTANCE_P6_DEFECT_NOT_REPRODUCED",
        "reviewed P6 terminal-stub evidence defect is absent",
        p6_path,
    )

    hashes = policy.expected_hashes
    _require(
        authorization.notebook_sha256 == hashes.notebook,
        "P3_P6_V4_FAILURE_ACCEPTANCE_NOTEBOOK_BINDING_DRIFT",
        "authorization notebook identity drifted",
        authorization_path,
    )
    _require(
        authorization.runtime_script_sha256 == hashes.runtime_script,
        "P3_P6_V4_FAILURE_ACCEPTANCE_RUNTIME_BINDING_DRIFT",
        "authorization runtime-script identity drifted",
        authorization_path,
    )
    _require(
        authorization.wrapper_code_sha256 == hashes.wrapper_code,
        "P3_P6_V4_FAILURE_ACCEPTANCE_WRAPPER_BINDING_DRIFT",
        "authorization wrapper identity drifted",
        authorization_path,
    )
    _require(
        consumption.authorization_sha256 == hashes.authorization,
        "P3_P6_V4_FAILURE_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption authorization binding drifted",
        consumption_path,
    )
    _require(
        lifecycle.consumption_sha256 == hashes.consumption,
        "P3_P6_V4_FAILURE_ACCEPTANCE_LIFECYCLE_BINDING_DRIFT",
        "lifecycle receipt consumption binding drifted",
        lifecycle_path,
    )
    _require(
        launch.authorization_sha256 == reference.authorization_sha256,
        "P3_P6_V4_FAILURE_ACCEPTANCE_LAUNCH_BINDING_DRIFT",
        "launch and saved-version authorization identities differ",
        launch_path,
    )
    _require(
        len(intake.members_before_receipt) == 24,
        "P3_P6_V4_FAILURE_ACCEPTANCE_INTAKE_RECEIPT_BOUNDARY_DRIFT",
        "intake receipt predecessor member count drifted",
        intake_path,
    )
    _require(
        len(root_cause.evidence_quality_defects) == 3,
        "P3_P6_V4_FAILURE_ACCEPTANCE_DEFECT_COUNT_DRIFT",
        "reviewed evidence-quality defect count drifted",
        root_cause_path,
    )
    _require(
        any("raw prompt" in item.lower() for item in limitations.limitations),
        "P3_P6_V4_FAILURE_ACCEPTANCE_PRIVACY_LIMITATION_MISSING",
        "privacy-safe evidence limitation is missing",
        limitations_path,
    )
    _require(
        (p3.status == "PASSED" and p4.status == "PASSED" and p5.status == "PASSED"),
        "P3_P6_V4_FAILURE_ACCEPTANCE_PREDECESSOR_PROBE_DRIFT",
        "one or more accepted predecessor probes no longer pass",
        summary_path,
    )

    return {
        "worker_1_completion_post_count": worker_1_posts,
        "worker_2_completion_post_count": worker_2_posts,
        "global_model_request_count": summary.counters.model_requests,
        "p6_terminal_stub_model_requests_performed": (p6.model_requests_performed),
        "first_divergence": (root_cause.first_observed_divergence),
        "authorization_lifecycle": consumption.lifecycle,
    }


def _synthetic_fixture() -> bool:
    return os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1"


def _validate_repository_authorities(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    if _synthetic_fixture():
        return
    for receipt in policy.repository_authorities:
        relative = Path(receipt.path)
        path = root / relative
        _require(
            path.is_file(),
            "P3_P6_V4_FAILURE_ACCEPTANCE_AUTHORITY_MISSING",
            "required repository authority is missing",
            relative,
        )
        _require(
            _file_sha256(path) == receipt.sha256,
            "P3_P6_V4_FAILURE_ACCEPTANCE_AUTHORITY_DRIFT",
            "required repository authority identity drifted",
            relative,
        )

    operational_authorization = Path(policy.operational_authorization_path)
    operational_consumption = Path(policy.operational_consumption_path)
    _require(
        not (root / operational_authorization).exists(),
        ("P3_P6_V4_FAILURE_ACCEPTANCE_TRANSIENT_AUTHORIZATION_PRESENT"),
        ("operational authorization must be absent after evidence preservation"),
        operational_authorization,
    )
    _require(
        not (root / operational_consumption).exists(),
        ("P3_P6_V4_FAILURE_ACCEPTANCE_TRANSIENT_CONSUMPTION_PRESENT"),
        ("operational consumption must be absent after evidence preservation"),
        operational_consumption,
    )

    result = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            policy.current_main_authority,
            "HEAD",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    _require(
        result.returncode == 0,
        ("P3_P6_V4_FAILURE_ACCEPTANCE_MAIN_AUTHORITY_NOT_ANCESTOR"),
        "reviewed main authority is not in HEAD ancestry",
        Path(".git"),
    )


def validate_evidence(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    _validate_exact_receipts(root, policy)
    _validate_intake_archive(root, policy)
    manifest = _validate_runtime_archive(root, policy)
    model_results = _validate_models(root, policy)
    return {
        "status": ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V4_EVIDENCE_VALID"),
        "saved_version_id": policy.saved_version_id,
        "runtime_manifest_member_count": len(manifest.members),
        "completed_probes": ["P3", "P4", "P5"],
        "failed_probe": "P6",
        "reported_failure_code": (policy.reported_failure_code),
        "first_divergence": policy.first_divergence,
        "evidence_quality_defect_count": 3,
        **model_results,
    }


def build_review(
    policy: FailureAcceptancePolicy,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "review_id": ("auragateway-cu129-p3-p6-runtime-diagnostic-failure-v4-review"),
        "status": ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V4_CLASSIFIED"),
        "decision": ("ACCEPT_VALID_GOVERNED_FAILURE_AND_DESIGN_P6_HARNESS_V5"),
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "current_main_authority": (policy.current_main_authority),
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "failed_probe": "P6",
        "reported_failure_code": (policy.reported_failure_code),
        "first_divergence": policy.first_divergence,
        "root_cause_status": ("HIGH_CONFIDENCE_FROM_RUNTIME_TRACE_AND_CODE_PATH"),
        "runtime_source_identity_status": "PASSED",
        "runtime_install_status": "PASSED",
        "process_tree_import_closure_status": "PASSED",
        "formal_p3_acceptance_established": True,
        "p4_deterministic_inference_established": True,
        "p5_prefix_cache_reuse_established": True,
        "p5_full_process_reset_established": True,
        "dual_worker_startup_established": True,
        "dual_worker_triton_backend_selection_established": True,
        "worker_teardown_status": "PASSED",
        "scratch_cleanup_status": "PASSED",
        "p6_process_gpu_isolation_formally_serialized": False,
        "p6_worker_1_route_request_attempted": True,
        "p6_worker_1_route_response_contract_passed": False,
        "p6_worker_2_route_request_executed": False,
        "p6_full_route_and_metric_isolation_established": False,
        "evidence_quality_defects": [
            (
                "P6 terminal model_requests_performed conflicts "
                "with the global counter and worker HTTP evidence."
            ),
            (
                "The broad dual-worker failure taxonomy collapses "
                "route-response failure with process isolation."
            ),
            (
                "Partial P6 stage results are not serialized when "
                "the full P6 report cannot be completed."
            ),
        ],
        "selected_remediation": [
            "stage-local P6 checkpoint reports",
            "precise P6 failure taxonomy",
            "per-worker request attempted and completed counters",
            ("schema-constrained or deterministic route acknowledgement"),
            "preserve existing privacy and teardown controls",
        ],
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "next_gate": policy.next_gate,
        "non_claims": [
            "The governed V4 lifecycle outcome remains FAILED.",
            "P6 route isolation is not established.",
            "The worker 2 route request was not executed.",
            "Full dual-worker metric isolation is not established.",
            "The exact mismatching model output is not retained.",
            "Measured A/B/C execution was not performed.",
            ("The failed notebook is not authorized for unchanged replay."),
            "Deployment readiness is not established.",
            "Production readiness is not established.",
        ],
    }


def build_record(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> dict[str, object]:
    evidence = [
        _artifact_receipt(
            root,
            Path(receipt.path),
        ).model_dump(mode="json")
        for receipt in policy.evidence_receipts
    ]
    authorities = [receipt.model_dump(mode="json") for receipt in policy.repository_authorities]
    return {
        "schema_version": "1.0.0",
        "record_id": ("auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v4"),
        "status": ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V4_VALID"),
        "current_main_authority": (policy.current_main_authority),
        "implementation_merge_commit": (policy.implementation_merge_commit),
        "implementation_feature_commit": (policy.implementation_feature_commit),
        "authorization_issuer_feature_commit": (policy.authorization_issuer_feature_commit),
        "runtime_source_main_commit": (policy.runtime_source_main_commit),
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "failed_probe": "P6",
        "reported_failure_code": (policy.reported_failure_code),
        "first_divergence": policy.first_divergence,
        "completed_probes": ["P3", "P4", "P5"],
        "formal_p3_acceptance_established": True,
        "p4_deterministic_inference_established": True,
        "p5_prefix_cache_reuse_established": True,
        "p5_full_process_reset_established": True,
        "p6_full_route_and_metric_isolation_established": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "evidence_quality_defect_count": 3,
        "policy": _artifact_receipt(
            root,
            POLICY_PATH,
        ).model_dump(mode="json"),
        "source": _artifact_receipt(
            root,
            SOURCE_PATH,
        ).model_dump(mode="json"),
        "tests": _artifact_receipt(
            root,
            TEST_PATH,
        ).model_dump(mode="json"),
        "adr": _artifact_receipt(
            root,
            ADR_PATH,
        ).model_dump(mode="json"),
        "report": _artifact_receipt(
            root,
            REPORT_PATH,
        ).model_dump(mode="json"),
        "runbook": _artifact_receipt(
            root,
            RUNBOOK_PATH,
        ).model_dump(mode="json"),
        "review": _artifact_receipt(
            root,
            REVIEW_PATH,
        ).model_dump(mode="json"),
        "repository_authorities": authorities,
        "evidence": evidence,
        "next_gate": policy.next_gate,
    }


def generate(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    evidence_result = validate_evidence(root)
    _validate_repository_authorities(root, policy)
    _write_json(
        root / REVIEW_PATH,
        build_review(policy),
    )
    _write_json(
        root / RECORD_PATH,
        build_record(root, policy),
    )
    return {
        "status": ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V4_GENERATED"),
        "saved_version_id": policy.saved_version_id,
        "review_sha256": _file_sha256(root / REVIEW_PATH),
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "evidence_status": evidence_result["status"],
    }


def validate_package(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    evidence_result = validate_evidence(root)
    _validate_repository_authorities(root, policy)

    expected_review = _canonical(build_review(policy))
    observed_review = (root / REVIEW_PATH).read_text(encoding="utf-8")
    _require(
        observed_review == expected_review,
        "P3_P6_V4_FAILURE_ACCEPTANCE_REVIEW_DRIFT",
        "stored failure-classification review drifted",
        REVIEW_PATH,
    )

    expected_record = _canonical(build_record(root, policy))
    observed_record = (root / RECORD_PATH).read_text(encoding="utf-8")
    _require(
        observed_record == expected_record,
        "P3_P6_V4_FAILURE_ACCEPTANCE_RECORD_DRIFT",
        "stored failure-acceptance record drifted",
        RECORD_PATH,
    )

    return {
        "status": ("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V4_VALID"),
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "completed_probes": ["P3", "P4", "P5"],
        "failed_probe": "P6",
        "first_divergence": policy.first_divergence,
        "runtime_execution_authorized": False,
        "next_gate": policy.next_gate,
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "review_sha256": _file_sha256(root / REVIEW_PATH),
        "evidence_status": evidence_result["status"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )
    for command in (
        "generate",
        "validate-evidence",
        "validate-package",
    ):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "--repo-root",
            type=Path,
            required=True,
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        root = arguments.repo_root.resolve()
        if arguments.command == "generate":
            result = generate(root)
        elif arguments.command == "validate-evidence":
            result = validate_evidence(root)
        else:
            result = validate_package(root)
        print(_canonical(result))
        return 0
    except FailureAcceptanceError as error:
        print(
            _canonical(error.envelope()),
            file=sys.stderr,
        )
        return 2
    except (
        OSError,
        ValueError,
        ValidationError,
        zipfile.BadZipFile,
    ) as error:
        envelope = {
            "error_code": ("P3_P6_V4_FAILURE_ACCEPTANCE_UNEXPECTED_FAILURE"),
            "safe_message": type(error).__name__,
            "path": None,
        }
        print(
            _canonical(envelope),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
