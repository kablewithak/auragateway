"""Accept and classify the governed P3-P6 runtime diagnostic V2 failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CURRENT_MAIN_AUTHORITY: Final = "4bc54a1ac7f054d65e9a3bea4be8ee952535ed5c"
IMPLEMENTATION_MERGE_COMMIT: Final = "87f2d4e08043c0c6ec5dee93d14c0523f531e8fe"
IMPLEMENTATION_FEATURE_COMMIT: Final = "d6837f057790279727fbb71177a615a0a12928ef"
AUTHORIZATION_ISSUER_FEATURE_COMMIT: Final = "ec2bb6a7cfef9f39b584d7e4d4cf45990a88e59b"
SAVED_VERSION_ID: Final = 339387641
NOTEBOOK_SHA256: Final = "912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd"
AUTHORIZATION_ID: Final = "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v2"
NEXT_GATE: Final = "design_and_merge_p3_p6_runtime_process_tree_import_closure_v3"

EVIDENCE_ROOT: Final = Path("evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v2")
AUTHORIZATION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / ("execution_authorization_v2-339387641.json")
CONSUMPTION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "execution_authorization_consumption_v2-339387641.json"
)
EVIDENCE_ZIP_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p3-p6-runtime-evidence-v2-339387641.zip")
KAGGLE_LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p3-p6-runtime-diagnostic-v2-339387641.log")
WORKER_STDOUT_PATH: Final = EVIDENCE_ROOT / "worker_1.stdout-339387641.txt"
WORKER_STDERR_PATH: Final = EVIDENCE_ROOT / "worker_1.stderr-339387641.txt"
REFERENCE_PATH: Final = EVIDENCE_ROOT / "kaggle_saved_version_reference_v2-339387641.json"
LIMITATIONS_PATH: Final = EVIDENCE_ROOT / "evidence_limitations_v2-339387641.json"
ROOT_CAUSE_PATH: Final = EVIDENCE_ROOT / "root_cause_analysis_v2-339387641.json"

RUNTIME_MEMBER_PATHS: Final = {
    "runtime_install_report_v2.json": EVIDENCE_ROOT / "runtime_install_report_v2-339387641.json",
    "p3_worker_startup_report_v2.json": EVIDENCE_ROOT
    / "p3_worker_startup_report_v2-339387641.json",
    "p4_deterministic_request_report_v2.json": EVIDENCE_ROOT
    / "p4_deterministic_request_report_v2-339387641.json",
    "p5_prefix_cache_reset_report_v2.json": EVIDENCE_ROOT
    / "p5_prefix_cache_reset_report_v2-339387641.json",
    "p6_dual_worker_isolation_report_v2.json": EVIDENCE_ROOT
    / "p6_dual_worker_isolation_report_v2-339387641.json",
    "scratch_cleanup_report_v2.json": EVIDENCE_ROOT / "scratch_cleanup_report_v2-339387641.json",
    "p3_p6_runtime_diagnostic_summary_v2.json": EVIDENCE_ROOT
    / "p3_p6_runtime_diagnostic_summary_v2-339387641.json",
    "failure_report_v2.json": EVIDENCE_ROOT / "failure_report_v2-339387641.json",
    "bundle_manifest_v2.json": EVIDENCE_ROOT / "bundle_manifest_v2-339387641.json",
    "human_report_v2.md": EVIDENCE_ROOT / "human_report_v2-339387641.md",
}

AUTHORIZATION_EVIDENCE_SHA256: Final = (
    "bd36bd1c63d630ed475cf57661dcccdcdcf0b9d67346ef5a72bfb5bd6a8e266a"
)
CONSUMPTION_EVIDENCE_SHA256: Final = (
    "c38533321fd69ac8b1e58f9225e7146c190a10555548cf4681924f881fcdcf7d"
)
EVIDENCE_ZIP_SHA256: Final = "36e15ed1a1424f15e43dfb1dea46abf5601e3241e2a37d4258ac95041a14a3a2"
KAGGLE_LOG_SHA256: Final = "f93688f7c934537a0e5506b2d3a373a7fc533cf77e93a0efb7fa4bf2299080e6"
WORKER_STDOUT_SHA256: Final = "7bb40058fe3b8a58f0caa9ca6c597ef420fd51a60f1bc6be1d3a3978eb81dc5b"
WORKER_STDERR_SHA256: Final = "9194cf68a5aec51826a81db5de76c1c552599415496a506b3d776adf6debe500"
REFERENCE_SHA256: Final = "be20d666cc5b54c8721da9f2b2179a69fc0c8b5999f79d13d933129c260a2e65"
LIMITATIONS_SHA256: Final = "2843d5b7fa7bd012106c8296f2767d10dc07af466ab055bba26287f604a9be26"
ROOT_CAUSE_SHA256: Final = "594b7257fc8c89fc36516ebf4b1f0d548d7c1765213e5507edc309bc56e064c5"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v2.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v2.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-01-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v2.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V2.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v2.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_"
    "failure_acceptance_v2_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v2.json"
)


class FailureAcceptanceError(RuntimeError):
    """Fail-closed V2 failure-evidence acceptance error."""

    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FailureAcceptanceError("P3_P6_FAILURE_ACCEPTANCE_ARGUMENT_INVALID", message)


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
    model_loads: Literal[1]
    model_requests: Literal[0]
    network_requests: Literal[0]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[1]


class DiagnosticSummary(StrictModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v2"]
    source_main_commit: Literal["1849c4b3f9cd36400b30d29ea3b3e67712251815"]
    failure_acceptance_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    failure_acceptance_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    v1_implementation_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V2_FAILED"]
    completed_probes: tuple[str, ...]
    failed_probe: Literal["P3"]
    failure_code: Literal["P3_P6_WORKER_STARTUP_FAILED"]
    runtime_install_status: Literal["PASSED"]
    runtime_install_process_outcome: Literal["PASSED"]
    runtime_install_failure_signals: tuple[str, ...]
    scratch_cleanup_status: Literal["PASSED"]
    scratch_exists_after_cleanup: Literal[False]
    stop_on_first_failure: Literal[True]
    counters: ActionCounters
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    network_access_permitted: Literal[False]
    measured_abc_execution_performed: Literal[False]
    next_gate: Literal["preserve_and_classify_p3_p6_runtime_failure_v2"]

    @model_validator(mode="after")
    def require_p3_startup_failure(self) -> Self:
        if self.completed_probes:
            raise ValueError("P3 startup failure must precede completed probes")
        if self.runtime_install_failure_signals:
            raise ValueError("successful installation cannot retain failure signals")
        return self


class FailureReport(StrictModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    failed_after: tuple[str, ...]
    failed_probe: Literal["P3"]
    error_code: Literal["P3_P6_WORKER_STARTUP_FAILED"]
    error_type: Literal["RuntimeError"]
    safe_message: Literal["worker_1 exited before readiness: 1"]

    @model_validator(mode="after")
    def require_no_completed_probe(self) -> Self:
        if self.failed_after:
            raise ValueError("worker startup failure cannot follow a completed probe")
        return self


class ProbeTerminalReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P3", "P4", "P5", "P6"]
    status: Literal["FAILED", "NOT_RUN"]
    decision: str
    failure_code: Literal["P3_P6_WORKER_STARTUP_FAILED"]
    blocked_by: Literal["P3"] | None
    completed_probes_before_terminal_state: tuple[str, ...]
    model_requests_performed: Literal[False]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]


class ScratchCleanupReport(StrictModel):
    schema_version: Literal["1.0.0"]
    report_id: Literal["auragateway-p3-p6-scratch-cleanup-v2"]
    status: Literal["PASSED"]
    scratch_before: dict[str, object]
    scratch_exists_after: Literal[False]
    error_type: None
    safe_message: None


class AuthorizationEvidence(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v2"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V2"]
    issued_from_main_commit: Literal["4bc54a1ac7f054d65e9a3bea4be8ee952535ed5c"]
    notebook_sha256: Literal["912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd"]
    single_use: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]


class ConsumptionEvidence(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v2"
    ]
    authorization_sha256: Literal[
        "bd36bd1c63d630ed475cf57661dcccdcdcf0b9d67346ef5a72bfb5bd6a8e266a"
    ]
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["FAILED"]
    saved_version_id: Literal[339387641]
    notebook_sha256: Literal["912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd"]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v2"]


class SavedVersionReference(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reference_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v2-kaggle-reference"]
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v2"]
    failed_lineage_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v2"]
    saved_version_id: Literal[339387641]
    kaggle_version_url: str
    outcome: Literal["FAILED"]
    failure_code: Literal["P3_P6_WORKER_STARTUP_FAILED"]
    failed_probe: Literal["P3"]
    source_main_authority: Literal["4bc54a1ac7f054d65e9a3bea4be8ee952535ed5c"]
    evidence_zip_sha256: Literal["36e15ed1a1424f15e43dfb1dea46abf5601e3241e2a37d4258ac95041a14a3a2"]


class EvidenceLimitations(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    limitations_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v2-limitations"]
    installation_success_established: Literal[True]
    parent_vllm_import_established: Literal[True]
    registry_subprocess_import_failure_established: Literal[True]
    process_tree_import_closure_root_cause_established: Literal[True]
    remediation_effectiveness_established: Literal[False]
    p3_readiness_established: Literal[False]
    qwen_architecture_compatibility_established: Literal[False]
    triton_backend_realization_established: Literal[False]
    p4_p5_p6_execution_established: Literal[False]
    reason: str


class RootCauseAnalysis(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    root_cause_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v2-root-cause"]
    status: Literal["CONFIRMED"]
    failure_boundary: Literal["P3_WORKER_STARTUP_MODEL_ARCHITECTURE_INSPECTION"]
    confirmed_first_divergence: Literal[
        "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
    ]
    violated_invariant: Literal["TARGET_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE"]
    parent_process_imported_vllm: Literal[True]
    child_process_command: Literal["/usr/bin/python3 -m vllm.model_executor.models.registry"]
    child_process_failure: Literal["ModuleNotFoundError: No module named 'vllm'"]
    downstream_failure: Literal["Qwen2ForCausalLM model architecture inspection failed"]
    causal_chain: tuple[str, ...] = Field(min_length=7)
    smallest_supported_remediation: Literal[
        "PROPAGATE_EXACT_TARGET_SITE_THROUGH_WORKER_CHILD_ENVIRONMENT"
    ]
    mandatory_v3_gate: Literal["NESTED_PYTHON_IMPORT_CLOSURE_PROBE"]
    remediation_proven: Literal[False]
    alternatives: dict[str, str]
    non_claims: tuple[str, ...] = Field(min_length=5)


class ArtifactReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class FailureAcceptanceReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v2-review"]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V2_CLASSIFIED"]
    decision: Literal[
        "ACCEPT_P3_WORKER_STARTUP_FAILURE_WITH_CONFIRMED_PROCESS_TREE_IMPORT_CLOSURE_ROOT_CAUSE"
    ]
    current_main_authority: Literal["4bc54a1ac7f054d65e9a3bea4be8ee952535ed5c"]
    saved_version_id: Literal[339387641]
    failure_code: Literal["P3_P6_WORKER_STARTUP_FAILED"]
    failed_probe: Literal["P3"]
    runtime_install_status: Literal["PASSED"]
    root_cause_status: Literal["CONFIRMED_FROM_WORKER_LOG_TRACE"]
    first_divergence: Literal[
        "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
    ]
    evidence_sufficiency: Literal[
        "SUFFICIENT_FOR_P3_STARTUP_ROOT_CAUSE_INSUFFICIENT_FOR_POST_REMEDIATION_P3_P6_SUCCESS"
    ]
    authorization_lifecycle_closed: Literal[True]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    next_gate: Literal["design_and_merge_p3_p6_runtime_process_tree_import_closure_v3"]
    non_claims: tuple[str, ...] = Field(min_length=8)


class FailureAcceptanceRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v2"]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V2_VALID"]
    current_main_authority: Literal["4bc54a1ac7f054d65e9a3bea4be8ee952535ed5c"]
    saved_version_id: Literal[339387641]
    evidence: tuple[ArtifactReceipt, ...] = Field(min_length=19)
    review: ArtifactReceipt
    source: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    authorization_lifecycle_closed: Literal[True]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    next_gate: Literal["design_and_merge_p3_p6_runtime_process_tree_import_closure_v3"]


def _canonical(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_EVIDENCE_UNSAFE",
            "required evidence is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _require_sha(repo_root: Path, relative: Path, expected: str) -> bytes:
    payload = _read_bytes(repo_root, relative)
    if _sha256_bytes(payload) != expected:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_EVIDENCE_DRIFT",
            "evidence identity drifted",
            relative.as_posix(),
        )
    return payload


def _json_object(payload: bytes, path: Path) -> dict[str, object]:
    try:
        observed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_JSON_INVALID",
            "evidence is invalid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(observed, dict):
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_JSON_ROOT_INVALID",
            "evidence JSON root must be one object",
            path.as_posix(),
        )
    return cast(dict[str, object], observed)


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    payload = _read_bytes(repo_root, relative)
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _validate_zip(repo_root: Path) -> None:
    zip_bytes = _require_sha(repo_root, EVIDENCE_ZIP_PATH, EVIDENCE_ZIP_SHA256)
    if len(zip_bytes) > 2 * 1024 * 1024:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_ZIP_TOO_LARGE",
            "runtime evidence ZIP exceeds the governed size ceiling",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    try:
        with zipfile.ZipFile(repo_root / EVIDENCE_ZIP_PATH) as archive:
            names = tuple(archive.namelist())
            if len(names) != len(set(names)):
                raise FailureAcceptanceError(
                    "P3_P6_FAILURE_ACCEPTANCE_ZIP_DUPLICATE",
                    "runtime evidence ZIP contains duplicate members",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )
            if set(names) != set(RUNTIME_MEMBER_PATHS):
                raise FailureAcceptanceError(
                    "P3_P6_FAILURE_ACCEPTANCE_ZIP_MEMBER_DRIFT",
                    "runtime evidence ZIP member set drifted",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )
            for name, relative in RUNTIME_MEMBER_PATHS.items():
                if Path(name).name != name:
                    raise FailureAcceptanceError(
                        "P3_P6_FAILURE_ACCEPTANCE_ZIP_MEMBER_UNSAFE",
                        "runtime evidence ZIP member is unsafe",
                        name,
                    )
                if archive.read(name) != _read_bytes(repo_root, relative):
                    raise FailureAcceptanceError(
                        "P3_P6_FAILURE_ACCEPTANCE_ZIP_EXTRACTION_DRIFT",
                        "queryable evidence differs from the preserved ZIP member",
                        relative.as_posix(),
                    )
    except zipfile.BadZipFile as error:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_ZIP_INVALID",
            "runtime evidence ZIP is invalid",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error


def _validate_runtime_evidence(repo_root: Path) -> None:
    summary = DiagnosticSummary.model_validate(
        _json_object(
            _read_bytes(
                repo_root,
                RUNTIME_MEMBER_PATHS["p3_p6_runtime_diagnostic_summary_v2.json"],
            ),
            RUNTIME_MEMBER_PATHS["p3_p6_runtime_diagnostic_summary_v2.json"],
        )
    )
    failure = FailureReport.model_validate(
        _json_object(
            _read_bytes(repo_root, RUNTIME_MEMBER_PATHS["failure_report_v2.json"]),
            RUNTIME_MEMBER_PATHS["failure_report_v2.json"],
        )
    )
    if summary.failure_code != failure.error_code:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_TERMINAL_MISMATCH",
            "summary and failure report disagree",
        )

    reports = tuple(
        ProbeTerminalReport.model_validate(
            _json_object(
                _read_bytes(repo_root, RUNTIME_MEMBER_PATHS[name]),
                RUNTIME_MEMBER_PATHS[name],
            )
        )
        for name in (
            "p3_worker_startup_report_v2.json",
            "p4_deterministic_request_report_v2.json",
            "p5_prefix_cache_reset_report_v2.json",
            "p6_dual_worker_isolation_report_v2.json",
        )
    )
    expected = (
        ("P3", "FAILED", None, "P3_FAILED"),
        ("P4", "NOT_RUN", "P3", "P4_NOT_RUN"),
        ("P5", "NOT_RUN", "P3", "P5_NOT_RUN"),
        ("P6", "NOT_RUN", "P3", "P6_NOT_RUN"),
    )
    observed = tuple(
        (item.probe_id, item.status, item.blocked_by, item.decision) for item in reports
    )
    if observed != expected:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_PROBE_TERMINAL_DRIFT",
            "P3-P6 terminal report sequence drifted",
        )

    ScratchCleanupReport.model_validate(
        _json_object(
            _read_bytes(repo_root, RUNTIME_MEMBER_PATHS["scratch_cleanup_report_v2.json"]),
            RUNTIME_MEMBER_PATHS["scratch_cleanup_report_v2.json"],
        )
    )
    install = _json_object(
        _read_bytes(repo_root, RUNTIME_MEMBER_PATHS["runtime_install_report_v2.json"]),
        RUNTIME_MEMBER_PATHS["runtime_install_report_v2.json"],
    )
    expected_install = {
        "status": "PASSED",
        "process_outcome": "PASSED",
        "returncode": 0,
        "timed_out": False,
        "hidden_retry_count": 0,
        "find_links_scope": "wheelhouse/wheels",
        "model_copy_completed_before_install": False,
        "network_access_requested": False,
    }
    for key, value in expected_install.items():
        if install.get(key) != value:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_INSTALL_EVIDENCE_DRIFT",
                f"runtime installation field drifted: {key}",
                RUNTIME_MEMBER_PATHS["runtime_install_report_v2.json"].as_posix(),
            )
    target_after = install.get("target_runtime_after")
    if not isinstance(target_after, dict) or target_after.get("exists") is not True:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_INSTALL_TARGET_INVALID",
            "installed target-runtime evidence is incomplete",
        )


def _validate_logs(repo_root: Path) -> None:
    kaggle = _require_sha(repo_root, KAGGLE_LOG_PATH, KAGGLE_LOG_SHA256).decode("utf-8")
    stdout = _require_sha(repo_root, WORKER_STDOUT_PATH, WORKER_STDOUT_SHA256).decode("utf-8")
    stderr = _require_sha(repo_root, WORKER_STDERR_PATH, WORKER_STDERR_SHA256).decode("utf-8")
    kaggle_signatures = (
        '"failure_code":"P3_P6_WORKER_STARTUP_FAILED"',
        '"runtime_install_status":"PASSED"',
        '"failed_probe":"P3"',
        "SystemExit: 2",
    )
    stdout_signatures = (
        "version 0.19.1",
        "'attention_backend': 'TRITON_ATTN'",
        "HF_HUB_OFFLINE is True",
        "'/usr/bin/python3', '-m', 'vllm.model_executor.models.registry'",
        "ModuleNotFoundError: No module named 'vllm'",
    )
    stderr_signatures = (
        "Model architectures ['Qwen2ForCausalLM'] failed to be inspected",
        "pydantic_core._pydantic_core.ValidationError",
    )
    for signature in kaggle_signatures:
        if signature not in kaggle:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_KAGGLE_LOG_INCOMPLETE",
                "Kaggle terminal log lacks a required signature",
                KAGGLE_LOG_PATH.as_posix(),
            )
    for signature in stdout_signatures:
        if signature not in stdout:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_STDOUT_INCOMPLETE",
                "worker stdout lacks a required causal signature",
                WORKER_STDOUT_PATH.as_posix(),
            )
    for signature in stderr_signatures:
        if signature not in stderr:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_STDERR_INCOMPLETE",
                "worker stderr lacks a required downstream signature",
                WORKER_STDERR_PATH.as_posix(),
            )


def _evidence_paths() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                AUTHORIZATION_EVIDENCE_PATH,
                CONSUMPTION_EVIDENCE_PATH,
                EVIDENCE_ZIP_PATH,
                KAGGLE_LOG_PATH,
                WORKER_STDOUT_PATH,
                WORKER_STDERR_PATH,
                REFERENCE_PATH,
                LIMITATIONS_PATH,
                ROOT_CAUSE_PATH,
                *RUNTIME_MEMBER_PATHS.values(),
            ),
            key=lambda item: item.as_posix(),
        )
    )


def _validate_all(repo_root: Path) -> tuple[ArtifactReceipt, ...]:
    authorization = _require_sha(
        repo_root,
        AUTHORIZATION_EVIDENCE_PATH,
        AUTHORIZATION_EVIDENCE_SHA256,
    )
    consumption = _require_sha(
        repo_root,
        CONSUMPTION_EVIDENCE_PATH,
        CONSUMPTION_EVIDENCE_SHA256,
    )
    AuthorizationEvidence.model_validate(_json_object(authorization, AUTHORIZATION_EVIDENCE_PATH))
    ConsumptionEvidence.model_validate(_json_object(consumption, CONSUMPTION_EVIDENCE_PATH))
    SavedVersionReference.model_validate(
        _json_object(_require_sha(repo_root, REFERENCE_PATH, REFERENCE_SHA256), REFERENCE_PATH)
    )
    EvidenceLimitations.model_validate(
        _json_object(
            _require_sha(
                repo_root,
                LIMITATIONS_PATH,
                LIMITATIONS_SHA256,
            ),
            LIMITATIONS_PATH,
        )
    )
    root_cause = RootCauseAnalysis.model_validate(
        _json_object(_require_sha(repo_root, ROOT_CAUSE_PATH, ROOT_CAUSE_SHA256), ROOT_CAUSE_PATH)
    )
    if root_cause.remediation_proven is not False:
        raise FailureAcceptanceError(
            "P3_P6_FAILURE_ACCEPTANCE_REMEDIATION_OVERCLAIM",
            "V3 remediation effectiveness is not yet established",
            ROOT_CAUSE_PATH.as_posix(),
        )
    _validate_zip(repo_root)
    _validate_runtime_evidence(repo_root)
    _validate_logs(repo_root)
    return tuple(_receipt(repo_root, path) for path in _evidence_paths())


def _review() -> FailureAcceptanceReview:
    return FailureAcceptanceReview(
        review_id="auragateway-cu129-p3-p6-runtime-diagnostic-failure-v2-review",
        status="P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V2_CLASSIFIED",
        decision=(
            "ACCEPT_P3_WORKER_STARTUP_FAILURE_WITH_CONFIRMED_PROCESS_TREE_IMPORT_CLOSURE_ROOT_CAUSE"
        ),
        current_main_authority=CURRENT_MAIN_AUTHORITY,
        saved_version_id=SAVED_VERSION_ID,
        failure_code="P3_P6_WORKER_STARTUP_FAILED",
        failed_probe="P3",
        runtime_install_status="PASSED",
        root_cause_status="CONFIRMED_FROM_WORKER_LOG_TRACE",
        first_divergence=("TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"),
        evidence_sufficiency=(
            "SUFFICIENT_FOR_P3_STARTUP_ROOT_CAUSE_INSUFFICIENT_FOR_POST_REMEDIATION_P3_P6_SUCCESS"
        ),
        authorization_lifecycle_closed=True,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        runtime_execution_authorized=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "The V3 remediation has not been implemented.",
            "The V3 remediation has not been executed.",
            "P3 worker readiness has not been established.",
            "Qwen architecture compatibility after import closure has not been established.",
            "TRITON_ATTN backend realization has not been established.",
            "P4 deterministic inference has not been established.",
            "P5 cache reuse and reset have not been established.",
            "P6 dual-worker isolation has not been established.",
            "Deployment and production readiness are not claimed.",
        ),
    )


def _record(
    repo_root: Path,
    evidence: tuple[ArtifactReceipt, ...],
    review_bytes: bytes,
) -> FailureAcceptanceRecord:
    return FailureAcceptanceRecord(
        record_id="auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v2",
        status="P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V2_VALID",
        current_main_authority=CURRENT_MAIN_AUTHORITY,
        saved_version_id=SAVED_VERSION_ID,
        evidence=evidence,
        review=ArtifactReceipt(
            path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_bytes),
            size_bytes=len(review_bytes),
        ),
        source=_receipt(repo_root, SOURCE_PATH),
        tests=_receipt(repo_root, TEST_PATH),
        adr=_receipt(repo_root, ADR_PATH),
        report=_receipt(repo_root, REPORT_PATH),
        runbook=_receipt(repo_root, RUNBOOK_PATH),
        authorization_lifecycle_closed=True,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        runtime_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> FailureAcceptanceRecord:
    root = repo_root.resolve()
    evidence = _validate_all(root)
    review = _review()
    review_bytes = review.canonical_json().encode("utf-8")
    (root / REVIEW_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / REVIEW_PATH).write_bytes(review_bytes)
    record = _record(root, evidence, review_bytes)
    (root / RECORD_PATH).write_bytes(record.canonical_json().encode("utf-8"))
    return record


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    evidence = _validate_all(root)
    review = _review()
    review_bytes = review.canonical_json().encode("utf-8")
    record = _record(root, evidence, review_bytes)
    expected = (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record.canonical_json().encode("utf-8")),
    )
    for relative, payload in expected:
        if _read_bytes(root, relative) != payload:
            raise FailureAcceptanceError(
                "P3_P6_FAILURE_ACCEPTANCE_GENERATED_DRIFT",
                "generated failure-acceptance artifact drifted",
                relative.as_posix(),
            )
    return {
        "status": record.status,
        "saved_version_id": SAVED_VERSION_ID,
        "evidence_path_count": len(evidence),
        "runtime_install_status": "PASSED",
        "failed_probe": "P3",
        "failure_code": "P3_P6_WORKER_STARTUP_FAILED",
        "root_cause_status": "CONFIRMED",
        "confirmed_first_divergence": (
            "TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS"
        ),
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p3-p6-failure-acceptance-v2")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "generate":
            record = generate(arguments.repo_root)
            output: object = {
                "status": record.status,
                "saved_version_id": record.saved_version_id,
                "evidence_path_count": len(record.evidence),
                "next_gate": record.next_gate,
            }
        else:
            output = validate(arguments.repo_root)
        print(_canonical(output))
        return 0
    except (FailureAcceptanceError, ValidationError, OSError, ValueError) as error:
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
        print(_canonical(payload), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
