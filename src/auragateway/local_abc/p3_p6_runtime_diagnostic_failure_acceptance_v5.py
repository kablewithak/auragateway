"""Accept and classify the governed P3-P6 runtime diagnostic V5 failure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p3_p6_runtime_failure_acceptance_v5_policy.json"
)
POLICY_SHA256: Final = "127fb51f03d44f895ca1e12856ea114f115e9a0a1be02b62ee9e85cd6d33cf51"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v5.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v5.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-05-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v5.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V5.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v5.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v5_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v5.json"
)


class FailureAcceptanceError(RuntimeError):
    """Fail-closed V5 failure-acceptance error."""

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
            "P3_P6_V5_FAILURE_ACCEPTANCE_ARGUMENT_INVALID",
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
    authorization: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumption: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    kaggle_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    layer_1_zip: str = Field(pattern=r"^[0-9a-f]{64}$")
    layer_1_log: str = Field(pattern=r"^[0-9a-f]{64}$")
    layer_2_json: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")


class FailureAcceptancePolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-p3-p6-runtime-diagnostic-failure-acceptance-v5-policy"]
    current_main_authority: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_issuer_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    runtime_source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    saved_version_id: Literal[340227787]
    layer_1_saved_version_id: Literal[340232886]
    next_gate: Literal["design_and_merge_p4_output_contract_diagnostic_v1"]
    first_divergence: Literal["P4_MODEL_RESPONSE_NOT_VALID_JSON"]
    reported_failure_code: Literal["P3_P6_REQUEST_FAILED"]
    safe_failure_message: Literal["model response is not valid JSON"]
    expected_hashes: ExpectedHashes
    evidence_receipt_count: int = Field(gt=0)
    evidence_receipts: tuple[ArtifactReceipt, ...]
    intake_member_targets: dict[str, str]
    runtime_member_targets: dict[str, str]
    layer_1_member_targets: dict[str, str]
    repository_authorities: tuple[str, ...]
    operational_authorization_path: str
    operational_consumption_path: str
    expected_log_tokens: tuple[str, ...]
    layer_1_expected_log_tokens: tuple[str, ...]

    @model_validator(mode="after")
    def validate_boundaries(self) -> Self:
        if len(self.evidence_receipts) != self.evidence_receipt_count:
            raise ValueError("evidence receipt count drifted")
        if len(self.intake_member_targets) != 6:
            raise ValueError("intake member target count drifted")
        if len(self.runtime_member_targets) != 15:
            raise ValueError("runtime member target count drifted")
        if len(self.layer_1_member_targets) != 8:
            raise ValueError("layer 1 member target count drifted")
        if len(self.repository_authorities) != 11:
            raise ValueError("repository authority count drifted")
        if len(self.expected_log_tokens) != 6:
            raise ValueError("terminal log token count drifted")
        if len(self.layer_1_expected_log_tokens) != 8:
            raise ValueError("layer 1 log token count drifted")
        return self


class ActionCounters(StrictModel):
    benchmark_trajectory_requests: Literal[0]
    external_spend: Literal[0]
    hidden_retries: Literal[0]
    kaggle_sessions: Literal[1]
    model_loads: Literal[1]
    model_requests: Literal[1]
    network_requests: Literal[0]
    runtime_import_closure_probes: Literal[1]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[1]


class DiagnosticSummary(ExternalModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v5"]
    source_main_commit: Literal["40b3530a763465fee0f7e27db17e9c444436ca18"]
    status: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V5_FAILED"]
    completed_probes: tuple[Literal["P3"], ...]
    failed_probe: Literal["P4"]
    failure_code: Literal["P3_P6_REQUEST_FAILED"]
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
    next_gate: Literal["preserve_and_classify_p3_p6_runtime_failure_v5"]

    @model_validator(mode="after")
    def validate_completed_probe_order(self) -> Self:
        if self.completed_probes != ("P3",):
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
    worker_id: Literal["worker_1"]
    worker_instance_id: Literal["worker_1-g1"]
    gpu_index: Literal[0]
    pythonpath_exact_target_site: Literal[True]
    backend_marker_evidence: BackendMarkerEvidence
    stdout_tail: str
    stderr_tail: str
    teardown: WorkerTeardown


class FailureReport(ExternalModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    failed_after: tuple[Literal["P3"], ...]
    failed_probe: Literal["P4"]
    error_code: Literal["P3_P6_REQUEST_FAILED"]
    error_type: Literal["RuntimeError"]
    safe_message: Literal["model response is not valid JSON"]
    teardown_status: Literal["PASSED"]
    worker_1_diagnostics: WorkerDiagnostics

    @model_validator(mode="after")
    def validate_predecessors(self) -> Self:
        if self.failed_after != ("P3",):
            raise ValueError("failure predecessor sequence drifted")
        return self


class P3Report(ExternalModel):
    probe_id: Literal["P3"]
    status: Literal["PASSED"]
    decision: Literal["ONE_WORKER_TRITON_STARTUP_PASSED"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    worker: dict[str, object]


class P4TerminalReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P4"]
    status: Literal["FAILED"]
    decision: Literal["P4_FAILED"]
    blocked_by: None
    failure_code: Literal["P3_P6_REQUEST_FAILED"]
    completed_probes_before_terminal_state: tuple[Literal["P3"], ...]
    global_model_request_count: Literal[1]
    model_requests_performed: Literal[True]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]


class P5TerminalReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P5"]
    status: Literal["NOT_RUN"]
    decision: Literal["P5_NOT_RUN"]
    blocked_by: Literal["P4"]
    failure_code: Literal["P3_P6_REQUEST_FAILED"]
    completed_probes_before_terminal_state: tuple[Literal["P3"], ...]
    global_model_request_count: Literal[1]
    model_requests_performed: Literal[True]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]


class P6TerminalReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P6"]
    status: Literal["NOT_RUN"]
    decision: Literal["P6_NOT_RUN"]
    blocked_by: Literal["P4"]
    failure_code: Literal["P3_P6_REQUEST_FAILED"]
    completed_probes_before_terminal_state: tuple[Literal["P3"], ...]
    global_model_request_count: Literal[1]
    model_requests_performed: Literal[True]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]


class WorkerRequestCounter(StrictModel):
    attempted: Literal[0]
    completed: Literal[0]


class P6CheckpointReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P6"]
    status: Literal["NOT_RUN"]
    current_stage: Literal["P6_NOT_STARTED"]
    blocked_by: Literal["P3_P6_REQUEST_FAILED"]
    events: tuple[object, ...]
    global_model_requests: Literal[1]
    worker_request_counters: dict[str, WorkerRequestCounter]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]

    @model_validator(mode="after")
    def validate_checkpoint(self) -> Self:
        if self.events:
            raise ValueError("P6 checkpoint events unexpectedly exist")
        if set(self.worker_request_counters) != {"worker_1", "worker_2"}:
            raise ValueError("P6 worker counter boundary drifted")
        return self


class NativeOriginReport(StrictModel):
    schema_version: Literal["1.0.0"]
    report_id: Literal["auragateway-p3-p6-runtime-native-origin-v5"]
    status: Literal["NOT_RUN"]
    decision: Literal["RUNTIME_NATIVE_ORIGIN_CLOSURE_NOT_RUN"]
    blocked_by: Literal["P3_P6_REQUEST_FAILED"]
    observations: tuple[object, ...]
    rejected_origin_count: Literal[0]
    cuda_stub_origin_observed: Literal[False]


class TeardownAggregate(ExternalModel):
    schema_version: Literal["1.0.0"]
    report_id: Literal["auragateway-p3-p6-worker-teardown-report-v5"]
    status: Literal["PASSED"]
    all_capture_threads_finalized: Literal[True]
    all_gpu_processes_absent: Literal[True]
    all_ports_closed: Literal[True]
    worker_teardowns: tuple[WorkerTeardown, ...]


class ManifestMember(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class BundleManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v5"]
    source_main_commit: Literal["40b3530a763465fee0f7e27db17e9c444436ca18"]
    members: tuple[ManifestMember, ...]
    scratch_directories_included: Literal[False]
    worker_log_directory_included: Literal[False]


class AuthorizationEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v5"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V5"]
    issued_from_main_commit: Literal["0c085e212a86ddcf820ce6e7dd8e47cbab4e7bfe"]
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    single_use: Literal[True]
    unchanged_replay_authorized: Literal[False]
    operator_confirmation_recorded: Literal[True]


class ConsumptionEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    consumption_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-consumption-v5"
    ]
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["FAILED"]
    saved_version_id: Literal[340227787]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_reusable: Literal[False]
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Layer1Receipt(ExternalModel):
    schema_version: Literal["1.0.0"]
    receipt_id: Literal["auragateway-p4-output-contract-inspection-v1-validation-340232886"]
    kaggle_saved_version_id: Literal[340232886]
    status: Literal["PASSED"]
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_member_count: Literal[8]
    manifest_member_count: Literal[7]
    hash_mismatch_count: Literal[0]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    wheel_count: Literal[176]
    critical_wheel_count: Literal[15]
    wheelhouse_control_hashes_valid: Literal[True]
    v4_v5_prompt_semantics_differ: Literal[True]
    response_format_absent: Literal[True]
    repetition_penalty_not_explicitly_neutralized: Literal[True]
    model_loads: Literal[0]
    worker_starts: Literal[0]
    model_requests: Literal[0]
    network_requests: Literal[0]


class RootCauseEvidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    classification: Literal["VALID_GOVERNED_DIAGNOSTIC_FAILURE"]
    failure_scope: Literal["P4_OUTPUT_CONTRACT"]
    reported_failure_code: Literal["P3_P6_REQUEST_FAILED"]
    first_observed_divergence: Literal["P4_MODEL_RESPONSE_NOT_VALID_JSON"]
    primary_classification: Literal["P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS"]
    specific_classification: Literal["V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"]
    confidence: Literal["HIGH_CAUSAL_CLASSIFICATION_NOT_COUNTERFACTUAL_PROOF"]
    established_facts: tuple[str, ...] = Field(min_length=15)
    rejected_root_causes: tuple[str, ...] = Field(min_length=6)
    evidence_quality_defects: tuple[str, ...] = Field(min_length=3)
    smallest_maintainable_next_diagnostic: tuple[str, ...] = Field(min_length=6)
    unchanged_replay_authorized: Literal[False]
    next_gate: Literal["design_and_merge_p4_output_contract_diagnostic_v1"]


class Layer2RootCause(StrictModel):
    primary: Literal["P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS"]
    specific: Literal["V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"]
    contributing: tuple[str, ...]
    not_root_causes: tuple[str, ...]


class Layer2Evidence(ExternalModel):
    schema_version: Literal["1.0.0"]
    report_id: Literal["auragateway-p4-layer-2-causal-investigation-340232886"]
    layer_1_saved_version_id: Literal[340232886]
    failed_v5_saved_version_id: Literal[340227787]
    status: Literal["COMPLETED"]
    root_cause_classification: Layer2RootCause
    next_gate: Literal["PRESERVE_AND_ACCEPT_P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5"]


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
            "P3_P6_V5_FAILURE_ACCEPTANCE_JSON_INVALID",
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


def _require(
    condition: bool,
    error_code: str,
    safe_message: str,
    path: Path,
) -> None:
    if condition:
        return
    raise FailureAcceptanceError(
        error_code,
        safe_message,
        path.as_posix(),
    )


def _load_policy(root: Path) -> FailureAcceptancePolicy:
    path = root / POLICY_PATH
    _require(
        path.is_file(),
        "P3_P6_V5_FAILURE_ACCEPTANCE_POLICY_MISSING",
        "failure-acceptance policy is missing",
        POLICY_PATH,
    )
    _require(
        _file_sha256(path) == POLICY_SHA256,
        "P3_P6_V5_FAILURE_ACCEPTANCE_POLICY_DRIFT",
        "failure-acceptance policy identity drifted",
        POLICY_PATH,
    )
    try:
        return FailureAcceptancePolicy.model_validate(_read_json(path))
    except ValidationError as error:
        raise FailureAcceptanceError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_POLICY_INVALID",
            "failure-acceptance policy schema drifted",
            POLICY_PATH.as_posix(),
        ) from error


def _artifact_receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = root / relative
    _require(
        path.is_file(),
        "P3_P6_V5_FAILURE_ACCEPTANCE_ARTIFACT_MISSING",
        "required package artifact is missing",
        relative,
    )
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_file_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _normalize_zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    member = PurePosixPath(normalized)
    safe = (
        bool(normalized)
        and not member.is_absolute()
        and ".." not in member.parts
        and not normalized.endswith("/")
        and not re.match(r"^[A-Za-z]:", normalized)
    )
    if not safe:
        raise FailureAcceptanceError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_UNSAFE_ZIP_MEMBER",
            "evidence ZIP contains an unsafe member path",
            normalized or None,
        )
    return member.as_posix()


def _safe_zip_members(
    archive: zipfile.ZipFile,
    path: Path,
) -> dict[str, str]:
    members: dict[str, str] = {}
    for info in archive.infolist():
        normalized = _normalize_zip_name(info.filename)
        _require(
            normalized not in members,
            "P3_P6_V5_FAILURE_ACCEPTANCE_DUPLICATE_ZIP_MEMBER",
            "evidence ZIP contains duplicate normalized member paths",
            path,
        )
        members[normalized] = info.filename
    return members


def _validate_exact_receipts(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    for receipt in policy.evidence_receipts:
        relative = Path(receipt.path)
        path = root / relative
        _require(
            path.is_file(),
            "P3_P6_V5_FAILURE_ACCEPTANCE_EVIDENCE_MISSING",
            "required evidence artifact is missing",
            relative,
        )
        _require(
            _file_sha256(path) == receipt.sha256,
            "P3_P6_V5_FAILURE_ACCEPTANCE_EVIDENCE_HASH_MISMATCH",
            "evidence artifact identity drifted",
            relative,
        )
        _require(
            path.stat().st_size == receipt.size_bytes,
            "P3_P6_V5_FAILURE_ACCEPTANCE_EVIDENCE_SIZE_MISMATCH",
            "evidence artifact size drifted",
            relative,
        )


def _evidence_path(
    policy: FailureAcceptancePolicy,
    suffix: str,
) -> Path:
    matches = [
        Path(receipt.path) for receipt in policy.evidence_receipts if receipt.path.endswith(suffix)
    ]
    if len(matches) != 1:
        raise FailureAcceptanceError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_EVIDENCE_PATH_AMBIGUOUS",
            "expected exactly one evidence path for suffix",
            suffix,
        )
    return matches[0]


def _validate_archive_targets(
    root: Path,
    archive_path: Path,
    expected_hash: str,
    targets: dict[str, str],
    boundary_code: str,
) -> dict[str, bytes]:
    _require(
        _file_sha256(root / archive_path) == expected_hash,
        "P3_P6_V5_FAILURE_ACCEPTANCE_ARCHIVE_HASH_MISMATCH",
        "evidence archive identity drifted",
        archive_path,
    )
    with zipfile.ZipFile(root / archive_path) as archive:
        members = _safe_zip_members(archive, archive_path)
        _require(
            set(members) == set(targets),
            boundary_code,
            "evidence archive member boundary drifted",
            archive_path,
        )
        payloads: dict[str, bytes] = {}
        for normalized, original in members.items():
            payload = archive.read(original)
            payloads[normalized] = payload
            target = Path(targets[normalized])
            _require(
                (root / target).is_file(),
                "P3_P6_V5_FAILURE_ACCEPTANCE_ARCHIVE_TARGET_MISSING",
                "preserved archive target is missing",
                target,
            )
            _require(
                _sha256_bytes(payload) == _file_sha256(root / target),
                "P3_P6_V5_FAILURE_ACCEPTANCE_ARCHIVE_MEMBER_DRIFT",
                "archive member differs from preserved target",
                target,
            )
        return payloads


def _validate_intake_manifest(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    manifest_path = _evidence_path(
        policy,
        "intake_manifest_v5-340227787.csv",
    )
    rows = list(csv.DictReader((root / manifest_path).read_text(encoding="utf-8").splitlines()))
    _require(
        len(rows) == 5,
        "P3_P6_V5_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_COUNT_DRIFT",
        "intake manifest row count drifted",
        manifest_path,
    )
    for row in rows:
        relative = row["relative_path"].replace("\\", "/")
        target = Path(policy.intake_member_targets[relative])
        _require(
            int(row["size_bytes"]) == (root / target).stat().st_size,
            "P3_P6_V5_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_SIZE_DRIFT",
            "intake manifest size drifted",
            target,
        )
        _require(
            row["sha256"] == _file_sha256(root / target),
            "P3_P6_V5_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_HASH_DRIFT",
            "intake manifest hash drifted",
            target,
        )


def _load_model(
    root: Path,
    path: Path,
    model: type[BaseModel],
) -> BaseModel:
    try:
        return model.model_validate(_read_json(root / path))
    except ValidationError as error:
        raise FailureAcceptanceError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_SCHEMA_INVALID",
            "evidence schema or reviewed literal drifted",
            path.as_posix(),
        ) from error


def _validate_runtime_manifest(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> BundleManifest:
    manifest_path = Path(policy.runtime_member_targets["bundle_manifest_v5.json"])
    manifest = cast(
        BundleManifest,
        _load_model(root, manifest_path, BundleManifest),
    )
    expected = set(policy.runtime_member_targets) - {"bundle_manifest_v5.json"}
    observed = {member.path for member in manifest.members}
    _require(
        observed == expected,
        "P3_P6_V5_FAILURE_ACCEPTANCE_RUNTIME_MANIFEST_BOUNDARY_DRIFT",
        "runtime bundle manifest boundary drifted",
        manifest_path,
    )
    for member in manifest.members:
        target = Path(policy.runtime_member_targets[member.path])
        _require(
            _file_sha256(root / target) == member.sha256,
            "P3_P6_V5_FAILURE_ACCEPTANCE_RUNTIME_MANIFEST_HASH_DRIFT",
            "runtime manifest member hash drifted",
            target,
        )
        _require(
            (root / target).stat().st_size == member.size_bytes,
            "P3_P6_V5_FAILURE_ACCEPTANCE_RUNTIME_MANIFEST_SIZE_DRIFT",
            "runtime manifest member size drifted",
            target,
        )
    return manifest


def _validate_layer_1_manifest(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    manifest_path = Path(policy.layer_1_member_targets["bundle_manifest.json"])
    payload = _read_json(root / manifest_path)

    if not isinstance(payload, dict):
        raise FailureAcceptanceError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_INVALID",
            "layer 1 manifest root is invalid",
            manifest_path.as_posix(),
        )

    entries_value = payload.get("entries")

    if not isinstance(entries_value, list):
        raise FailureAcceptanceError(
            "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_INVALID",
            "layer 1 manifest entries are invalid",
            manifest_path.as_posix(),
        )

    entries = cast(list[object], entries_value)

    _require(
        len(entries) == 7,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_COUNT_DRIFT",
        "layer 1 manifest member count drifted",
        manifest_path,
    )

    expected = set(policy.layer_1_member_targets) - {"bundle_manifest.json"}

    observed = {str(item.get("relative_path")) for item in entries if isinstance(item, dict)}

    _require(
        observed == expected,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_BOUNDARY_DRIFT",
        "layer 1 manifest boundary drifted",
        manifest_path,
    )

    for item in entries:
        if not isinstance(item, dict):
            raise FailureAcceptanceError(
                "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_INVALID",
                "layer 1 manifest entry is invalid",
                manifest_path.as_posix(),
            )

        relative = str(item["relative_path"])
        target = Path(policy.layer_1_member_targets[relative])

        _require(
            _file_sha256(root / target) == str(item["sha256"]),
            "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_HASH_DRIFT",
            "layer 1 manifest member hash drifted",
            target,
        )

        _require(
            (root / target).stat().st_size == int(item["size_bytes"]),
            "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_MANIFEST_SIZE_DRIFT",
            "layer 1 manifest member size drifted",
            target,
        )


def _validate_runtime_models(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> dict[str, object]:
    summary_path = Path(policy.runtime_member_targets["p3_p6_runtime_diagnostic_summary_v5.json"])
    failure_path = Path(policy.runtime_member_targets["failure_report_v5.json"])
    p3_path = Path(policy.runtime_member_targets["p3_worker_startup_report_v5.json"])
    p4_path = Path(policy.runtime_member_targets["p4_deterministic_request_report_v5.json"])
    p5_path = Path(policy.runtime_member_targets["p5_prefix_cache_reset_report_v5.json"])
    p6_path = Path(policy.runtime_member_targets["p6_dual_worker_isolation_report_v5.json"])
    checkpoint_path = Path(policy.runtime_member_targets["p6_stage_checkpoint_report_v5.json"])
    native_path = Path(policy.runtime_member_targets["runtime_native_origin_report_v5.json"])
    teardown_path = Path(policy.runtime_member_targets["worker_teardown_report_v5.json"])

    summary = cast(
        DiagnosticSummary,
        _load_model(root, summary_path, DiagnosticSummary),
    )
    failure = cast(
        FailureReport,
        _load_model(root, failure_path, FailureReport),
    )
    p3 = cast(P3Report, _load_model(root, p3_path, P3Report))
    p4 = cast(P4TerminalReport, _load_model(root, p4_path, P4TerminalReport))
    p5 = cast(P5TerminalReport, _load_model(root, p5_path, P5TerminalReport))
    p6 = cast(P6TerminalReport, _load_model(root, p6_path, P6TerminalReport))
    checkpoint = cast(
        P6CheckpointReport,
        _load_model(root, checkpoint_path, P6CheckpointReport),
    )
    native = cast(
        NativeOriginReport,
        _load_model(root, native_path, NativeOriginReport),
    )
    teardown = cast(
        TeardownAggregate,
        _load_model(root, teardown_path, TeardownAggregate),
    )

    worker = failure.worker_1_diagnostics
    post_count = len(
        re.findall(
            r'POST /v1/chat/completions HTTP/1\.1" 200 OK',
            worker.stdout_tail,
        )
    )
    _require(
        post_count == 1,
        "P3_P6_V5_FAILURE_ACCEPTANCE_REQUEST_TRACE_DRIFT",
        "retained worker completion-request count drifted",
        failure_path,
    )
    _require(
        p3.status == "PASSED"
        and p4.status == "FAILED"
        and p5.status == "NOT_RUN"
        and p6.status == "NOT_RUN",
        "P3_P6_V5_FAILURE_ACCEPTANCE_PROBE_SEQUENCE_DRIFT",
        "reviewed probe terminal sequence drifted",
        summary_path,
    )
    _require(
        checkpoint.global_model_requests == summary.counters.model_requests,
        "P3_P6_V5_FAILURE_ACCEPTANCE_COUNTER_RECONCILIATION_DRIFT",
        "P6 checkpoint and global counters differ",
        checkpoint_path,
    )
    _require(
        native.status == "NOT_RUN",
        "P3_P6_V5_FAILURE_ACCEPTANCE_NATIVE_ORIGIN_SCOPE_DRIFT",
        "native-origin closure unexpectedly ran",
        native_path,
    )
    _require(
        len(teardown.worker_teardowns) == 1,
        "P3_P6_V5_FAILURE_ACCEPTANCE_TEARDOWN_BOUNDARY_DRIFT",
        "worker teardown count drifted",
        teardown_path,
    )
    return {
        "completed_probes": list(summary.completed_probes),
        "failed_probe": summary.failed_probe,
        "global_model_request_count": summary.counters.model_requests,
        "worker_1_completion_post_count": post_count,
        "p5_status": p5.status,
        "p6_status": p6.status,
        "p6_checkpoint_status": checkpoint.status,
        "native_origin_status": native.status,
        "teardown_status": teardown.status,
    }


def _validate_lifecycle_and_analysis(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> dict[str, object]:
    authorization_path = _evidence_path(
        policy,
        "execution_authorization_v5-340227787.json",
    )
    consumption_path = _evidence_path(
        policy,
        "execution_authorization_consumption_v5-340227787.json",
    )
    layer_1_receipt_path = _evidence_path(
        policy,
        "layer_1_inspection_validation_receipt_v1-340232886.json",
    )
    root_cause_path = _evidence_path(
        policy,
        "root_cause_analysis_v5-340227787.json",
    )
    layer_2_path = _evidence_path(
        policy,
        "layer_2_causal_investigation_v1-340232886.json",
    )

    authorization = cast(
        AuthorizationEvidence,
        _load_model(root, authorization_path, AuthorizationEvidence),
    )
    consumption = cast(
        ConsumptionEvidence,
        _load_model(root, consumption_path, ConsumptionEvidence),
    )
    layer_1 = cast(
        Layer1Receipt,
        _load_model(root, layer_1_receipt_path, Layer1Receipt),
    )
    root_cause = cast(
        RootCauseEvidence,
        _load_model(root, root_cause_path, RootCauseEvidence),
    )
    layer_2 = cast(
        Layer2Evidence,
        _load_model(root, layer_2_path, Layer2Evidence),
    )

    hashes = policy.expected_hashes
    _require(
        _file_sha256(root / authorization_path) == hashes.authorization,
        "P3_P6_V5_FAILURE_ACCEPTANCE_AUTHORIZATION_HASH_DRIFT",
        "authorization evidence identity drifted",
        authorization_path,
    )
    _require(
        _file_sha256(root / consumption_path) == hashes.consumption,
        "P3_P6_V5_FAILURE_ACCEPTANCE_CONSUMPTION_HASH_DRIFT",
        "consumption evidence identity drifted",
        consumption_path,
    )
    _require(
        consumption.authorization_sha256 == hashes.authorization,
        "P3_P6_V5_FAILURE_ACCEPTANCE_CONSUMPTION_BINDING_DRIFT",
        "consumption authorization binding drifted",
        consumption_path,
    )
    _require(
        authorization.notebook_sha256 == hashes.notebook,
        "P3_P6_V5_FAILURE_ACCEPTANCE_NOTEBOOK_BINDING_DRIFT",
        "authorization notebook binding drifted",
        authorization_path,
    )
    _require(
        authorization.runtime_script_sha256 == hashes.runtime_script,
        "P3_P6_V5_FAILURE_ACCEPTANCE_RUNTIME_BINDING_DRIFT",
        "authorization runtime binding drifted",
        authorization_path,
    )
    _require(
        authorization.wrapper_code_sha256 == hashes.wrapper_code,
        "P3_P6_V5_FAILURE_ACCEPTANCE_WRAPPER_BINDING_DRIFT",
        "authorization wrapper binding drifted",
        authorization_path,
    )
    _require(
        authorization.model_snapshot_sha256 == hashes.model_snapshot,
        "P3_P6_V5_FAILURE_ACCEPTANCE_MODEL_BINDING_DRIFT",
        "authorization model binding drifted",
        authorization_path,
    )
    _require(
        layer_1.archive_sha256 == hashes.layer_1_zip,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_BINDING_DRIFT",
        "layer 1 receipt archive binding drifted",
        layer_1_receipt_path,
    )
    _require(
        "WHEELHOUSE_CORRUPTION" in root_cause.rejected_root_causes
        and "MODEL_SNAPSHOT_CORRUPTION" in root_cause.rejected_root_causes,
        "P3_P6_V5_FAILURE_ACCEPTANCE_REJECTED_CAUSE_DRIFT",
        "reviewed rejected root causes drifted",
        root_cause_path,
    )
    _require(
        layer_2.root_cause_classification.primary == root_cause.primary_classification,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_2_CLASSIFICATION_DRIFT",
        "layer 2 and acceptance root-cause classifications differ",
        layer_2_path,
    )
    return {
        "authorization_lifecycle": consumption.lifecycle,
        "authorization_reusable": consumption.authorization_reusable,
        "layer_1_status": layer_1.status,
        "layer_2_status": layer_2.status,
        "root_cause_primary": root_cause.primary_classification,
        "root_cause_specific": root_cause.specific_classification,
    }


def _validate_logs(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> None:
    log_path = _evidence_path(
        policy,
        "ag-cu129-p3-p6-runtime-diagnostic-v5-340227787.log",
    )
    layer_1_log_path = _evidence_path(
        policy,
        "ag-p4-output-contract-inspection-v1-340232886.log",
    )
    _require(
        _file_sha256(root / log_path) == policy.expected_hashes.kaggle_log,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LOG_HASH_DRIFT",
        "V5 Kaggle log identity drifted",
        log_path,
    )
    _require(
        _file_sha256(root / layer_1_log_path) == policy.expected_hashes.layer_1_log,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_LOG_HASH_DRIFT",
        "layer 1 Kaggle log identity drifted",
        layer_1_log_path,
    )
    log_text = (root / log_path).read_text(encoding="utf-8")
    for token in policy.expected_log_tokens:
        _require(
            token in log_text,
            "P3_P6_V5_FAILURE_ACCEPTANCE_LOG_TOKEN_MISSING",
            "V5 Kaggle log is missing a required terminal token",
            log_path,
        )
    layer_1_text = (root / layer_1_log_path).read_text(encoding="utf-8")
    for token in policy.layer_1_expected_log_tokens:
        _require(
            token in layer_1_text,
            "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_LOG_TOKEN_MISSING",
            "layer 1 Kaggle log is missing a required token",
            layer_1_log_path,
        )


def _synthetic_fixture() -> bool:
    return os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1"


def _validate_repository_authorities(
    root: Path,
    policy: FailureAcceptancePolicy,
) -> list[dict[str, object]]:
    if _synthetic_fixture():
        return []
    receipts: list[dict[str, object]] = []
    for authority in policy.repository_authorities:
        relative = Path(authority)
        _require(
            (root / relative).is_file(),
            "P3_P6_V5_FAILURE_ACCEPTANCE_AUTHORITY_MISSING",
            "required repository authority is missing",
            relative,
        )
        receipt = _artifact_receipt(root, relative)
        receipts.append(receipt.model_dump(mode="json"))

    operational_authorization = Path(policy.operational_authorization_path)
    operational_consumption = Path(policy.operational_consumption_path)
    _require(
        not (root / operational_authorization).exists(),
        "P3_P6_V5_FAILURE_ACCEPTANCE_TRANSIENT_AUTHORIZATION_PRESENT",
        "operational authorization must be absent after preservation",
        operational_authorization,
    )
    _require(
        not (root / operational_consumption).exists(),
        "P3_P6_V5_FAILURE_ACCEPTANCE_TRANSIENT_CONSUMPTION_PRESENT",
        "operational consumption must be absent after preservation",
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
        "P3_P6_V5_FAILURE_ACCEPTANCE_MAIN_AUTHORITY_NOT_ANCESTOR",
        "reviewed main authority is not in HEAD ancestry",
        Path(".git"),
    )
    return receipts


def validate_evidence(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    _validate_exact_receipts(root, policy)

    intake_archive_path = _evidence_path(
        policy,
        "AuraGateway_V5_Failure_Evidence_Intake_340227787.zip",
    )
    _validate_archive_targets(
        root,
        intake_archive_path,
        policy.expected_hashes.intake_archive,
        policy.intake_member_targets,
        "P3_P6_V5_FAILURE_ACCEPTANCE_INTAKE_BOUNDARY_DRIFT",
    )
    _validate_intake_manifest(root, policy)

    runtime_archive_path = _evidence_path(
        policy,
        "ag-cu129-p3-p6-runtime-evidence-v5-340227787.zip",
    )
    _validate_archive_targets(
        root,
        runtime_archive_path,
        policy.expected_hashes.evidence_zip,
        policy.runtime_member_targets,
        "P3_P6_V5_FAILURE_ACCEPTANCE_RUNTIME_BOUNDARY_DRIFT",
    )
    runtime_manifest = _validate_runtime_manifest(root, policy)

    layer_1_archive_path = _evidence_path(
        policy,
        "ag-p4-output-contract-inspection-v1-340232886.zip",
    )
    _validate_archive_targets(
        root,
        layer_1_archive_path,
        policy.expected_hashes.layer_1_zip,
        policy.layer_1_member_targets,
        "P3_P6_V5_FAILURE_ACCEPTANCE_LAYER_1_BOUNDARY_DRIFT",
    )
    _validate_layer_1_manifest(root, policy)
    _validate_logs(root, policy)

    runtime = _validate_runtime_models(root, policy)
    lifecycle = _validate_lifecycle_and_analysis(root, policy)
    return {
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5_EVIDENCE_VALID",
        "saved_version_id": policy.saved_version_id,
        "layer_1_saved_version_id": policy.layer_1_saved_version_id,
        "runtime_archive_member_count": len(policy.runtime_member_targets),
        "runtime_manifest_member_count": len(runtime_manifest.members),
        "layer_1_archive_member_count": len(policy.layer_1_member_targets),
        "completed_probes": ["P3"],
        "failed_probe": "P4",
        "reported_failure_code": policy.reported_failure_code,
        "first_divergence": policy.first_divergence,
        **runtime,
        **lifecycle,
    }


def build_review(
    policy: FailureAcceptancePolicy,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "review_id": ("auragateway-cu129-p3-p6-runtime-diagnostic-failure-v5-review"),
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5_CLASSIFIED",
        "decision": ("ACCEPT_VALID_GOVERNED_FAILURE_AND_DESIGN_P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1"),
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "current_main_authority": policy.current_main_authority,
        "saved_version_id": policy.saved_version_id,
        "layer_1_saved_version_id": policy.layer_1_saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "completed_probes": ["P3"],
        "failed_probe": "P4",
        "reported_failure_code": policy.reported_failure_code,
        "first_divergence": policy.first_divergence,
        "safe_failure_message": policy.safe_failure_message,
        "runtime_source_identity_status": "PASSED",
        "runtime_install_status": "PASSED",
        "process_tree_import_closure_status": "PASSED",
        "formal_p3_acceptance_established": True,
        "p4_exact_json_contract_established": False,
        "p5_prefix_cache_reuse_established": False,
        "p5_full_process_reset_established": False,
        "p6_route_and_metric_isolation_established": False,
        "worker_teardown_status": "PASSED",
        "scratch_cleanup_status": "PASSED",
        "root_cause_status": ("HIGH_CONFIDENCE_CAUSAL_CLASSIFICATION_NOT_COUNTERFACTUAL_PROOF"),
        "root_cause_primary": "P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS",
        "root_cause_specific": ("V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"),
        "contributing_factors": [
            "PROMPT_ONLY_EXACT_JSON_CONTRACT",
            "MODEL_GENERATION_CONFIG_REPETITION_PENALTY_NOT_NEUTRALIZED",
            "P4_FAILURE_METADATA_INSUFFICIENT",
            "ONLINE_SERVING_REPRODUCIBILITY_NOT_ESTABLISHED",
        ],
        "rejected_root_causes": [
            "WHEELHOUSE_CORRUPTION",
            "MODEL_SNAPSHOT_CORRUPTION",
            "TRITON_BACKEND_FAILURE",
            "CUDA_ABI_FAILURE",
            "HTTP_TRANSPORT_FAILURE",
            "TOP_K_FILTERING_UNDER_TEMPERATURE_ZERO",
        ],
        "selected_next_diagnostic": [
            "compare V4 and V5 prompt wording independently",
            "compare repetition_penalty 1.1 and 1.0 independently",
            "test JSON-schema constrained output against pinned vLLM 0.19.1",
            "retain metadata-safe response failure diagnostics",
            "preserve raw prompt and raw output exclusion",
        ],
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "next_gate": policy.next_gate,
        "non_claims": [
            "The governed V5 lifecycle outcome remains FAILED.",
            "The exact malformed model output is not retained.",
            "Prompt regression is not yet isolated by a counterfactual experiment.",
            "P4 exact structured-output reliability is not established.",
            "P5 prefix-cache reuse was not reached.",
            "P6 route isolation was not reached.",
            "JSON-schema compatibility with the pinned runtime is not established.",
            "Measured A/B/C execution was not performed.",
            "The failed notebook is not authorized for unchanged replay.",
            "Deployment readiness is not established.",
            "Production readiness is not established.",
        ],
    }


def build_record(
    root: Path,
    policy: FailureAcceptancePolicy,
    authority_receipts: list[dict[str, object]],
) -> dict[str, object]:
    evidence = [
        _artifact_receipt(root, Path(receipt.path)).model_dump(mode="json")
        for receipt in policy.evidence_receipts
    ]
    return {
        "schema_version": "1.0.0",
        "record_id": ("auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v5"),
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V5_VALID",
        "current_main_authority": policy.current_main_authority,
        "implementation_merge_commit": policy.implementation_merge_commit,
        "implementation_feature_commit": policy.implementation_feature_commit,
        "authorization_issuer_merge_commit": (policy.authorization_issuer_merge_commit),
        "authorization_issuer_feature_commit": (policy.authorization_issuer_feature_commit),
        "runtime_source_main_commit": policy.runtime_source_main_commit,
        "saved_version_id": policy.saved_version_id,
        "layer_1_saved_version_id": policy.layer_1_saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "completed_probes": ["P3"],
        "failed_probe": "P4",
        "reported_failure_code": policy.reported_failure_code,
        "first_divergence": policy.first_divergence,
        "formal_p3_acceptance_established": True,
        "p4_exact_json_contract_established": False,
        "p5_prefix_cache_reuse_established": False,
        "p6_route_and_metric_isolation_established": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_established": False,
        "root_cause_primary": "P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS",
        "root_cause_specific": ("V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"),
        "policy": _artifact_receipt(root, POLICY_PATH).model_dump(mode="json"),
        "source": _artifact_receipt(root, SOURCE_PATH).model_dump(mode="json"),
        "tests": _artifact_receipt(root, TEST_PATH).model_dump(mode="json"),
        "adr": _artifact_receipt(root, ADR_PATH).model_dump(mode="json"),
        "report": _artifact_receipt(root, REPORT_PATH).model_dump(mode="json"),
        "runbook": _artifact_receipt(root, RUNBOOK_PATH).model_dump(mode="json"),
        "review": _artifact_receipt(root, REVIEW_PATH).model_dump(mode="json"),
        "repository_authorities": authority_receipts,
        "evidence": evidence,
        "next_gate": policy.next_gate,
    }


def generate(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    evidence_result = validate_evidence(root)
    authority_receipts = _validate_repository_authorities(root, policy)
    _write_json(root / REVIEW_PATH, build_review(policy))
    _write_json(
        root / RECORD_PATH,
        build_record(root, policy, authority_receipts),
    )
    return {
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V5_GENERATED",
        "saved_version_id": policy.saved_version_id,
        "review_sha256": _file_sha256(root / REVIEW_PATH),
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "evidence_status": evidence_result["status"],
        "runtime_execution_authorized": False,
    }


def validate_package(root: Path) -> dict[str, object]:
    policy = _load_policy(root)
    evidence_result = validate_evidence(root)
    authority_receipts = _validate_repository_authorities(root, policy)

    expected_review = _canonical(build_review(policy))
    _require(
        (root / REVIEW_PATH).read_text(encoding="utf-8") == expected_review,
        "P3_P6_V5_FAILURE_ACCEPTANCE_REVIEW_DRIFT",
        "stored failure-classification review drifted",
        REVIEW_PATH,
    )
    expected_record = _canonical(build_record(root, policy, authority_receipts))
    _require(
        (root / RECORD_PATH).read_text(encoding="utf-8") == expected_record,
        "P3_P6_V5_FAILURE_ACCEPTANCE_RECORD_DRIFT",
        "stored failure-acceptance record drifted",
        RECORD_PATH,
    )
    return {
        "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V5_VALID",
        "saved_version_id": policy.saved_version_id,
        "lifecycle_outcome": "FAILED",
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "completed_probes": ["P3"],
        "failed_probe": "P4",
        "first_divergence": policy.first_divergence,
        "runtime_execution_authorized": False,
        "measured_abc_authorized": False,
        "next_gate": policy.next_gate,
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "review_sha256": _file_sha256(root / REVIEW_PATH),
        "evidence_status": evidence_result["status"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
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
        print(_canonical(error.envelope()), file=sys.stderr)
        return 2
    except (
        OSError,
        ValueError,
        ValidationError,
        zipfile.BadZipFile,
    ) as error:
        print(
            _canonical(
                {
                    "error_code": ("P3_P6_V5_FAILURE_ACCEPTANCE_UNEXPECTED_FAILURE"),
                    "safe_message": type(error).__name__,
                    "path": None,
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
