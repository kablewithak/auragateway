"""Accept and classify the governed P3-P6 runtime diagnostic V3 failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CURRENT_MAIN_AUTHORITY: Final = "37e79005ff22b6f5be73b551d161f6adc2da11d9"
IMPLEMENTATION_MERGE_COMMIT: Final = "52272c82a5964377e7091575c297342f4902b640"
IMPLEMENTATION_FEATURE_COMMIT: Final = "aa0f0dff3677ab6e9979bd2d8595c076a2963f2e"
AUTHORIZATION_ISSUER_FEATURE_COMMIT: Final = "9ca2218869bd58fbe6cc4bb4c544ebe16b61460f"
AUTHORIZATION_LIFECYCLE_FIX_FEATURE_COMMIT: Final = "33ad0890d213d459c5999844930f6bdb99caa43e"
SAVED_VERSION_ID: Final = 339943910
NOTEBOOK_SHA256: Final = "f62842a2fc08793b68ca1604165dfe16d8cff866452d7a6ab5e4c2a2b84328de"
TEMPLATE_SHA256: Final = "fafa942e54a6eae23cd328435f329f9b11189f2cd12d2cec215676fcb6e52ffe"
AUTHORIZATION_ID: Final = "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v3"
NEXT_GATE: Final = "design_and_merge_p3_p6_runtime_evidence_contract_hardening_v4"

EVIDENCE_ROOT: Final = Path("evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v3")
INTAKE_ARCHIVE_PATH: Final = EVIDENCE_ROOT / (
    "AuraGateway_V3_Failure_Evidence_Intake_339943910.zip"
)
AUTHORIZATION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / ("execution_authorization_v3-339943910.json")
CONSUMPTION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "execution_authorization_consumption_v3-339943910.json"
)
EVIDENCE_ZIP_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p3-p6-runtime-evidence-v3-339943910.zip")
KAGGLE_LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p3-p6-runtime-diagnostic-v3-339943910.log")
REFERENCE_PATH: Final = EVIDENCE_ROOT / ("kaggle_saved_version_reference_v3-339943910.json")
LIMITATIONS_PATH: Final = EVIDENCE_ROOT / ("evidence_limitations_v3-339943910.json")
ROOT_CAUSE_PATH: Final = EVIDENCE_ROOT / ("root_cause_analysis_v3-339943910.json")
DUPLICATE_EXCLUSION_PATH: Final = EVIDENCE_ROOT / ("duplicate_evidence_exclusion_v3-339943910.json")
INTAKE_RECEIPT_PATH: Final = EVIDENCE_ROOT / ("intake_validation_receipt_v3-339943910.json")
VLLM_AUTHORITY_PATH: Final = EVIDENCE_ROOT / ("vllm_0_19_1_backend_selection_authority.json")

RUNTIME_MEMBER_PATHS: Final = {
    "runtime_install_report_v3.json": EVIDENCE_ROOT / "runtime_install_report_v3-339943910.json",
    "runtime_import_closure_report_v3.json": EVIDENCE_ROOT
    / "runtime_import_closure_report_v3-339943910.json",
    "p3_worker_startup_report_v3.json": EVIDENCE_ROOT
    / "p3_worker_startup_report_v3-339943910.json",
    "p4_deterministic_request_report_v3.json": EVIDENCE_ROOT
    / "p4_deterministic_request_report_v3-339943910.json",
    "p5_prefix_cache_reset_report_v3.json": EVIDENCE_ROOT
    / "p5_prefix_cache_reset_report_v3-339943910.json",
    "p6_dual_worker_isolation_report_v3.json": EVIDENCE_ROOT
    / "p6_dual_worker_isolation_report_v3-339943910.json",
    "scratch_cleanup_report_v3.json": EVIDENCE_ROOT / "scratch_cleanup_report_v3-339943910.json",
    "p3_p6_runtime_diagnostic_summary_v3.json": EVIDENCE_ROOT
    / "p3_p6_runtime_diagnostic_summary_v3-339943910.json",
    "failure_report_v3.json": EVIDENCE_ROOT / "failure_report_v3-339943910.json",
    "bundle_manifest_v3.json": EVIDENCE_ROOT / "bundle_manifest_v3-339943910.json",
    "human_report_v3.md": EVIDENCE_ROOT / "human_report_v3-339943910.md",
}

INTAKE_ARCHIVE_SHA256: Final = "df0cdd6ca8d393e89d67ed5e1b6d3176ae8d657c46a05714771b9cbff1be7798"
AUTHORIZATION_EVIDENCE_SHA256: Final = (
    "46cc1562c6a7586f9b4ba95f7b0aba8a4ac7b32e82c7b0967ba6695ccab52299"
)
CONSUMPTION_EVIDENCE_SHA256: Final = (
    "c2fd9f9fa61590fb3675fedb720e4d3361d3bfaec5e6ce42b433dfe6ca97b609"
)
EVIDENCE_ZIP_SHA256: Final = "db639dbaa910a9070315b95fcefeae8417a71ce2f19c1bdec67bb180be18ea55"
KAGGLE_LOG_SHA256: Final = "b08aa64e5cc754e9e130a8cdbbd9c93922130cf5ffa4c2a4510f4a0f38c0344b"
REFERENCE_SHA256: Final = "3536691aadecc811879866c47dd731552482d9be5c2f804b5f446b94a83b2654"
LIMITATIONS_SHA256: Final = "9b06f0c3d593b24c8fb713fca8398f4f6f8189b736a0af7eecb1a42fc2b464a2"
ROOT_CAUSE_SHA256: Final = "c0d3a1a2b5c783e43441ada221361af6d16a54ce8e5d1dba6b99944d08cda803"
DUPLICATE_EXCLUSION_SHA256: Final = (
    "33c3da51319a318ec21c072ab3f959da5119a862ca1db8157426b9d18566f4df"
)
INTAKE_RECEIPT_SHA256: Final = "16b4a7f59561d7c2d301fe1b101c8154e67b8afeed07c4eab00eabd27ee6398b"
VLLM_AUTHORITY_SHA256: Final = "a79e27b1bf3ab18b562c5a8917e0e3e5914da53ece06c9c83fbda34c9167da91"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v3.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v3.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-03-local-abc-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v3.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_Failure_Acceptance_V3.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v3.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_"
    "runtime_diagnostic_failure_acceptance_v3_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v3.json"
)
AUTHORIZED_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v3.ipynb"
)
RUNTIME_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v3.py.tmpl"
)

EXPECTED_BACKEND_MARKER: Final = "Using AttentionBackendEnum.TRITON_ATTN backend."
EXPECTED_PREDICATE: Final = 'return "triton_attn" in text and "attention backend" in text'
TARGET_SITE_SUFFIX: Final = "/p3_p6_runtime_diagnostic_v3_scratch/target_runtime/site-packages"
EXPECTED_CRITICAL_MODULES: Final = (
    "vllm",
    "torch",
    "triton",
    "transformers",
    "vllm.model_executor.models.registry",
)


class FailureAcceptanceError(RuntimeError):
    """Fail-closed V3 failure-evidence acceptance error."""

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
            "P3_P6_V3_FAILURE_ACCEPTANCE_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return _canonical(self.model_dump(mode="json"))


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
    runtime_import_closure_probes: Literal[1]
    runtime_install_attempts: Literal[1]
    worker_starts: Literal[1]


class DiagnosticSummary(StrictModel):
    schema_version: Literal["1.0.0"]
    diagnostic_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3"]
    source_main_commit: Literal["b332e6d664e672182f49f059078dc12db74b13e0"]
    failure_acceptance_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    failure_acceptance_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    v2_implementation_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["FAILED"]
    terminal_decision: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V3_FAILED"]
    completed_probes: tuple[str, ...]
    failed_probe: Literal["P3"]
    failure_code: Literal["P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"]
    runtime_install_status: Literal["PASSED"]
    runtime_install_process_outcome: Literal["PASSED"]
    runtime_install_failure_signals: tuple[str, ...]
    runtime_import_closure_status: Literal["PASSED"]
    runtime_import_closure_process_outcome: Literal["PASSED"]
    scratch_cleanup_status: Literal["PASSED"]
    scratch_exists_after_cleanup: Literal[False]
    stop_on_first_failure: Literal[True]
    counters: ActionCounters
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    network_access_permitted: Literal[False]
    measured_abc_execution_performed: Literal[False]
    next_gate: Literal["preserve_and_classify_p3_p6_runtime_failure_v3"]

    @model_validator(mode="after")
    def require_pre_p3_terminal_state(self) -> Self:
        if self.completed_probes:
            raise ValueError("the V3 failure must precede completed probes")
        if self.runtime_install_failure_signals:
            raise ValueError("successful installation cannot retain failure signals")
        return self


class StreamReceipt(StrictModel):
    observed_bytes: int = Field(gt=0)
    retained_bytes: int = Field(gt=0)
    tail_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_complete_retention(self) -> Self:
        if self.observed_bytes != self.retained_bytes:
            raise ValueError("worker stream retention is incomplete")
        return self


class WorkerDiagnostics(StrictModel):
    worker_id: Literal["worker_1"]
    gpu_index: Literal[0]
    port: Literal[8001]
    returncode: None
    argv_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pythonpath: str
    pythonpath_exact_target_site: Literal[True]
    stdout: StreamReceipt
    stderr: StreamReceipt
    stdout_tail: str
    stderr_tail: str

    @model_validator(mode="after")
    def require_target_site(self) -> Self:
        if not self.pythonpath.endswith(TARGET_SITE_SUFFIX):
            raise ValueError("worker PYTHONPATH target site drifted")
        return self


class FailureReport(StrictModel):
    schema_version: Literal["1.0.0"]
    status: Literal["FAILED"]
    failed_after: tuple[str, ...]
    failed_probe: Literal["P3"]
    error_code: Literal["P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"]
    error_type: Literal["RuntimeError"]
    safe_message: Literal["worker_1 explicit backend marker was not observed"]
    worker_1_diagnostics: WorkerDiagnostics

    @model_validator(mode="after")
    def require_no_completed_probe(self) -> Self:
        if self.failed_after:
            raise ValueError("backend marker failure cannot follow a completed probe")
        return self


class ProbeTerminalReport(StrictModel):
    schema_version: Literal["1.0.0"]
    probe_id: Literal["P3", "P4", "P5", "P6"]
    status: Literal["FAILED", "NOT_RUN"]
    decision: str
    failure_code: Literal["P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"]
    blocked_by: Literal["P3"] | None
    completed_probes_before_terminal_state: tuple[str, ...]
    model_requests_performed: Literal[False]
    raw_output_logged: Literal[False]
    raw_prompt_logged: Literal[False]


class ScratchCleanupReport(StrictModel):
    schema_version: Literal["1.0.0"]
    report_id: Literal["auragateway-p3-p6-scratch-cleanup-v3"]
    status: Literal["PASSED"]
    scratch_before: dict[str, object]
    scratch_exists_after: Literal[False]
    error_type: None
    safe_message: None


class RuntimeImportClosureReport(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    report_id: Literal["auragateway-p3-p6-runtime-import-closure-report-v3"]
    status: Literal["PASSED"]
    process_outcome: Literal["PASSED"]
    returncode: Literal[0]
    timed_out: Literal[False]
    hidden_retry_count: Literal[0]
    network_access_requested: Literal[False]
    decision: Literal["PROCESS_TREE_IMPORT_CLOSURE_PASSED"]
    pythonpath_exact_target_site: Literal[True]
    inherited_pythonpath_replaced: Literal[True]
    nested_interpreter_depth: Literal[2]
    all_critical_origins_within_target_site: Literal[True]
    model_loads_consumed: Literal[0]
    worker_starts_consumed: Literal[0]
    parent_python_executable: Literal["/usr/bin/python3"]
    child_python_executable: Literal["/usr/bin/python3"]
    parent_pythonpath: str
    child_pythonpath: str
    target_site: str
    critical_modules: tuple[str, ...]
    critical_module_origins: dict[str, str]

    @model_validator(mode="after")
    def require_exact_import_closure(self) -> Self:
        if self.critical_modules != EXPECTED_CRITICAL_MODULES:
            raise ValueError("critical import module order drifted")
        for value in (
            self.parent_pythonpath,
            self.child_pythonpath,
            self.target_site,
        ):
            if not value.endswith(TARGET_SITE_SUFFIX):
                raise ValueError("import-closure target site drifted")
        if set(self.critical_module_origins) != set(EXPECTED_CRITICAL_MODULES):
            raise ValueError("critical import origin inventory drifted")
        for origin in self.critical_module_origins.values():
            if TARGET_SITE_SUFFIX not in origin:
                raise ValueError("critical module resolved outside target site")
        return self


class AuthorizationEvidence(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v3"
    ]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    scope: Literal["P3_P6_RUNTIME_DIAGNOSTIC_V3"]
    issued_from_main_commit: Literal["37e79005ff22b6f5be73b551d161f6adc2da11d9"]
    notebook_sha256: Literal["f62842a2fc08793b68ca1604165dfe16d8cff866452d7a6ab5e4c2a2b84328de"]
    single_use: Literal[True]
    passed_failed_or_interrupted_attempt_consumes_authorization: Literal[True]
    unchanged_replay_authorized: Literal[False]


class ConsumptionEvidence(ExternalEvidenceModel):
    schema_version: Literal["1.0.0"]
    consumption_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-consumption-v3"
    ]
    authorization_id: Literal[
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-v3"
    ]
    authorization_sha256: Literal[
        "46cc1562c6a7586f9b4ba95f7b0aba8a4ac7b32e82c7b0967ba6695ccab52299"
    ]
    lifecycle: Literal["CONSUMED"]
    outcome: Literal["FAILED"]
    saved_version_id: Literal[339943910]
    notebook_sha256: Literal["f62842a2fc08793b68ca1604165dfe16d8cff866452d7a6ab5e4c2a2b84328de"]
    authorization_reusable: Literal[False]
    next_gate: Literal["preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v3"]


class SavedVersionReference(StrictModel):
    schema_version: Literal["1.0.0"]
    reference_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v3-kaggle-reference"]
    notebook_name: Literal["ag-cu129-p3-p6-runtime-diagnostic-v3"]
    failed_lineage_name: Literal["ag-cu129-p3-p6-runtime-diag-failed-v3"]
    saved_version_id: Literal[339943910]
    kaggle_version_url: str
    lifecycle_outcome: Literal["FAILED"]
    reported_failure_code: Literal["P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"]
    failed_probe: Literal["P3"]
    issued_from_main_commit: Literal["37e79005ff22b6f5be73b551d161f6adc2da11d9"]
    authorized_notebook_sha256: Literal[
        "f62842a2fc08793b68ca1604165dfe16d8cff866452d7a6ab5e4c2a2b84328de"
    ]
    runtime_evidence_zip_sha256: Literal[
        "db639dbaa910a9070315b95fcefeae8417a71ce2f19c1bdec67bb180be18ea55"
    ]
    terminal_log_sha256: Literal["b08aa64e5cc754e9e130a8cdbbd9c93922130cf5ffa4c2a4510f4a0f38c0344b"]
    executed_notebook_source_identity_verified: Literal[False]


class EvidenceLimitations(StrictModel):
    schema_version: Literal["1.0.0"]
    limitations_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v3-limitations"]
    saved_version_id: Literal[339943910]
    executed_saved_version_notebook_preserved: Literal[False]
    executed_notebook_source_identity_verified: Literal[False]
    authorized_repository_notebook_preserved: Literal[True]
    rendered_results_html_preserved: Literal[False]
    runtime_installation_established: Literal[True]
    process_tree_import_closure_established: Literal[True]
    worker_readiness_established: Literal[True]
    served_model_inventory_established: Literal[True]
    triton_attn_startup_selection_established: Literal[True]
    formal_p3_acceptance_established: Literal[False]
    request_level_inference_established: Literal[False]
    request_level_attention_execution_established: Literal[False]
    p4_deterministic_inference_established: Literal[False]
    p5_cache_reuse_or_reset_established: Literal[False]
    p6_dual_worker_isolation_established: Literal[False]
    complete_native_library_provenance_established: Literal[False]
    teardown_gpu_process_evidence_established: Literal[False]
    deployment_readiness_established: Literal[False]
    production_readiness_established: Literal[False]
    reason: str


class RootCauseAnalysis(StrictModel):
    schema_version: Literal["1.0.0"]
    root_cause_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3-root-cause"]
    status: Literal["CONFIRMED"]
    saved_version_id: Literal[339943910]
    governed_lifecycle_outcome: Literal["FAILED"]
    reported_failure_code: Literal["P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"]
    evidence_disposition: Literal["QUARANTINED_INVALID_DIAGNOSTIC"]
    failure_boundary: Literal["P3_BACKEND_REALIZATION_EVIDENCE_CLASSIFIER"]
    confirmed_first_divergence: Literal[
        "BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER"
    ]
    violated_invariant: Literal["AUTHORITATIVE_BACKEND_MARKER_MUST_MATCH_PINNED_RUNTIME_FORMAT"]
    reviewed_predicate: Literal['return "triton_attn" in text and "attention backend" in text']
    observed_runtime_marker: Literal["Using AttentionBackendEnum.TRITON_ATTN backend."]
    triton_attn_component_matched: Literal[True]
    attention_backend_phrase_component_matched: Literal[False]
    runtime_installation_status: Literal["PASSED"]
    process_tree_import_closure_status: Literal["PASSED"]
    worker_readiness_established: Literal[True]
    served_model_inventory_established: Literal[True]
    triton_attn_startup_selection_established: Literal[True]
    formal_p3_acceptance_established: Literal[False]
    model_requests_performed: Literal[0]
    request_level_attention_execution_established: Literal[False]
    p4_p5_p6_execution_established: Literal[False]
    smallest_supported_remediation: Literal["HARDEN_P3_RUNTIME_EVIDENCE_CONTRACT_V4"]
    required_v4_controls: tuple[str, ...] = Field(min_length=8)
    unchanged_replay_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    non_claims: tuple[str, ...] = Field(min_length=10)


class DuplicateEvidenceExclusion(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3-duplicate-evidence-exclusion"]
    saved_version_id: Literal[339943910]
    duplicate_filename: Literal["download (72).txt"]
    duplicate_present: Literal[True]
    duplicate_sha256: Literal["b08aa64e5cc754e9e130a8cdbbd9c93922130cf5ffa4c2a4510f4a0f38c0344b"]
    canonical_log_sha256: Literal[
        "b08aa64e5cc754e9e130a8cdbbd9c93922130cf5ffa4c2a4510f4a0f38c0344b"
    ]
    byte_identical_to_canonical_log: Literal[True]
    duplicate_included_in_repository_evidence: Literal[False]
    reason: str


class IntakeValidationReceipt(StrictModel):
    schema_version: Literal["1.0.0"]
    receipt_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-v3-intake-validation"]
    saved_version_id: Literal[339943910]
    intake_archive_sha256: Literal[
        "df0cdd6ca8d393e89d67ed5e1b6d3176ae8d657c46a05714771b9cbff1be7798"
    ]
    intake_archive_size_bytes: Literal[73939]
    archive_file_count: Literal[22]
    manifest_member_count: Literal[21]
    normalized_member_paths_unique: Literal[True]
    manifest_hashes_verified: Literal[True]
    nested_runtime_zip_sha256: Literal[
        "db639dbaa910a9070315b95fcefeae8417a71ce2f19c1bdec67bb180be18ea55"
    ]
    nested_runtime_member_count: Literal[11]
    nested_bundle_manifest_member_count: Literal[10]
    nested_bundle_hashes_verified: Literal[True]
    repository_authority_notebook_sha256: Literal[
        "f62842a2fc08793b68ca1604165dfe16d8cff866452d7a6ab5e4c2a2b84328de"
    ]
    repository_authority_template_sha256: Literal[
        "fafa942e54a6eae23cd328435f329f9b11189f2cd12d2cec215676fcb6e52ffe"
    ]
    executed_notebook_source_identity_verified: Literal[False]


class VllmBackendAuthority(StrictModel):
    schema_version: Literal["1.0.0"]
    authority_id: Literal["vllm-0.19.1-cuda-explicit-backend-selection"]
    repository: Literal["vllm-project/vllm"]
    tag: Literal["v0.19.1"]
    path: Literal["vllm/platforms/cuda.py"]
    blob_sha: Literal["50a79cbb0b8d3833c6ae85b19906fbfe193a8f06"]
    selected_backend_validation: str
    invalid_selection_behavior: Literal["raise ValueError"]
    successful_selection_log_template: Literal["Using %s backend."]
    successful_selection_return: Literal["selected_backend.get_path()"]
    observed_rendered_log: Literal["Using AttentionBackendEnum.TRITON_ATTN backend."]
    scope: Literal["STARTUP_BACKEND_SELECTION_ONLY"]
    request_level_kernel_execution_proven: Literal[False]


class ArtifactReceipt(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class FailureAcceptanceReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-v3-review"]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V3_CLASSIFIED"]
    decision: Literal["ACCEPT_FAILED_LIFECYCLE_AND_QUARANTINE_INVALID_BACKEND_DIAGNOSTIC"]
    current_main_authority: Literal["37e79005ff22b6f5be73b551d161f6adc2da11d9"]
    saved_version_id: Literal[339943910]
    lifecycle_outcome: Literal["FAILED"]
    reported_failure_code: Literal["P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"]
    failed_probe: Literal["P3"]
    runtime_install_status: Literal["PASSED"]
    process_tree_import_closure_status: Literal["PASSED"]
    evidence_disposition: Literal["QUARANTINED_INVALID_DIAGNOSTIC"]
    root_cause_status: Literal["CONFIRMED_FROM_RUNTIME_TRACE_AND_CODE_PATH"]
    first_divergence: Literal[
        "BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER"
    ]
    worker_readiness_established: Literal[True]
    served_model_inventory_established: Literal[True]
    triton_attn_startup_selection_established: Literal[True]
    formal_p3_acceptance_established: Literal[False]
    request_level_attention_execution_established: Literal[False]
    executed_notebook_source_identity_verified: Literal[False]
    authorization_lifecycle_closed: Literal[True]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    runtime_execution_authorized: Literal[False]
    next_gate: Literal["design_and_merge_p3_p6_runtime_evidence_contract_hardening_v4"]
    non_claims: tuple[str, ...] = Field(min_length=10)


class FailureAcceptanceRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v3"]
    status: Literal["P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V3_VALID"]
    current_main_authority: Literal["37e79005ff22b6f5be73b551d161f6adc2da11d9"]
    saved_version_id: Literal[339943910]
    evidence: tuple[ArtifactReceipt, ...] = Field(min_length=22)
    authorized_notebook: ArtifactReceipt
    runtime_template: ArtifactReceipt
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
    executed_notebook_source_identity_verified: Literal[False]
    formal_p3_acceptance_established: Literal[False]
    next_gate: Literal["design_and_merge_p3_p6_runtime_evidence_contract_hardening_v4"]


def _canonical(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_EVIDENCE_UNSAFE",
            "required evidence is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _require_sha(
    repo_root: Path,
    relative: Path,
    expected: str,
) -> bytes:
    payload = _read_bytes(repo_root, relative)
    if _sha256_bytes(payload) != expected:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_EVIDENCE_DRIFT",
            "evidence identity drifted",
            relative.as_posix(),
        )
    return payload


def _json_object(
    payload: bytes,
    path: Path,
) -> dict[str, object]:
    try:
        observed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_JSON_INVALID",
            "evidence is invalid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(observed, dict):
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_JSON_ROOT_INVALID",
            "evidence JSON root must be one object",
            path.as_posix(),
        )
    return cast(dict[str, object], observed)


def _receipt(
    repo_root: Path,
    relative: Path,
) -> ArtifactReceipt:
    payload = _read_bytes(repo_root, relative)
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _normalized_zip_name(name: str) -> str:
    return name.replace("\\", "/")


def _validate_intake_archive(repo_root: Path) -> None:
    payload = _require_sha(
        repo_root,
        INTAKE_ARCHIVE_PATH,
        INTAKE_ARCHIVE_SHA256,
    )
    if len(payload) != 73939:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_SIZE_DRIFT",
            "intake archive size drifted",
            INTAKE_ARCHIVE_PATH.as_posix(),
        )
    try:
        with zipfile.ZipFile(repo_root / INTAKE_ARCHIVE_PATH) as archive:
            infos = tuple(item for item in archive.infolist() if not item.is_dir())
            normalized = tuple(_normalized_zip_name(item.filename) for item in infos)
            if len(infos) != 22 or len(normalized) != len(set(normalized)):
                raise FailureAcceptanceError(
                    "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_MEMBER_DRIFT",
                    "intake archive member boundary drifted",
                    INTAKE_ARCHIVE_PATH.as_posix(),
                )
            manifest_name = "evidence_intake_manifest_v3-339943910.json"
            manifest_raw = archive.read(manifest_name)
            manifest = _json_object(
                manifest_raw,
                Path(manifest_name),
            )
            members = manifest.get("members")
            if not isinstance(members, list) or len(members) != 21:
                raise FailureAcceptanceError(
                    "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_INVALID",
                    "intake manifest member boundary drifted",
                    manifest_name,
                )
            observed = {
                _normalized_zip_name(item.filename): (
                    _sha256_bytes(archive.read(item.filename)),
                    item.file_size,
                )
                for item in infos
                if _normalized_zip_name(item.filename) != manifest_name
            }
            expected: dict[str, tuple[str, int]] = {}
            for raw in members:
                if not isinstance(raw, dict):
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_INVALID",
                        "intake manifest entry is invalid",
                        manifest_name,
                    )
                path = raw.get("path")
                digest = raw.get("sha256")
                size = raw.get("size_bytes")
                if (
                    not isinstance(path, str)
                    or not isinstance(digest, str)
                    or not isinstance(size, int)
                ):
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_MANIFEST_INVALID",
                        "intake manifest identity is invalid",
                        manifest_name,
                    )
                expected[path] = (digest, size)
            if observed != expected:
                raise FailureAcceptanceError(
                    "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_HASH_DRIFT",
                    "intake manifest hashes differ from archive bytes",
                    manifest_name,
                )
    except zipfile.BadZipFile as error:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_INTAKE_INVALID",
            "intake archive is invalid",
            INTAKE_ARCHIVE_PATH.as_posix(),
        ) from error


def _validate_runtime_zip(repo_root: Path) -> None:
    zip_bytes = _require_sha(
        repo_root,
        EVIDENCE_ZIP_PATH,
        EVIDENCE_ZIP_SHA256,
    )
    if len(zip_bytes) > 2 * 1024 * 1024:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_ZIP_TOO_LARGE",
            "runtime evidence ZIP exceeds the governed ceiling",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    try:
        with zipfile.ZipFile(repo_root / EVIDENCE_ZIP_PATH) as archive:
            names = tuple(archive.namelist())
            if len(names) != len(set(names)):
                raise FailureAcceptanceError(
                    "P3_P6_V3_FAILURE_ACCEPTANCE_ZIP_DUPLICATE",
                    "runtime evidence ZIP contains duplicate members",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )
            if set(names) != set(RUNTIME_MEMBER_PATHS):
                raise FailureAcceptanceError(
                    "P3_P6_V3_FAILURE_ACCEPTANCE_ZIP_MEMBER_DRIFT",
                    "runtime evidence ZIP member set drifted",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )
            for name, relative in RUNTIME_MEMBER_PATHS.items():
                if Path(name).name != name:
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_ZIP_MEMBER_UNSAFE",
                        "runtime evidence ZIP member is unsafe",
                        name,
                    )
                if archive.read(name) != _read_bytes(
                    repo_root,
                    relative,
                ):
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_ZIP_EXTRACTION_DRIFT",
                        "queryable evidence differs from ZIP bytes",
                        relative.as_posix(),
                    )
            bundle = _json_object(
                archive.read("bundle_manifest_v3.json"),
                Path("bundle_manifest_v3.json"),
            )
            members = bundle.get("members")
            if not isinstance(members, list) or len(members) != 10:
                raise FailureAcceptanceError(
                    "P3_P6_V3_FAILURE_ACCEPTANCE_BUNDLE_INVALID",
                    "runtime bundle manifest boundary drifted",
                    "bundle_manifest_v3.json",
                )
            for raw in members:
                if not isinstance(raw, dict):
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_BUNDLE_INVALID",
                        "runtime bundle member is invalid",
                        "bundle_manifest_v3.json",
                    )
                name = raw.get("path")
                digest = raw.get("sha256")
                size = raw.get("size_bytes")
                if (
                    not isinstance(name, str)
                    or not isinstance(digest, str)
                    or not isinstance(size, int)
                ):
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_BUNDLE_INVALID",
                        "runtime bundle identity is invalid",
                        "bundle_manifest_v3.json",
                    )
                member = archive.read(name)
                if _sha256_bytes(member) != digest or len(member) != size:
                    raise FailureAcceptanceError(
                        "P3_P6_V3_FAILURE_ACCEPTANCE_BUNDLE_HASH_DRIFT",
                        "runtime bundle member identity drifted",
                        name,
                    )
    except zipfile.BadZipFile as error:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_ZIP_INVALID",
            "runtime evidence ZIP is invalid",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error


def _validate_runtime_evidence(
    repo_root: Path,
) -> tuple[DiagnosticSummary, FailureReport]:
    summary = DiagnosticSummary.model_validate(
        _json_object(
            _read_bytes(
                repo_root,
                RUNTIME_MEMBER_PATHS["p3_p6_runtime_diagnostic_summary_v3.json"],
            ),
            RUNTIME_MEMBER_PATHS["p3_p6_runtime_diagnostic_summary_v3.json"],
        )
    )
    failure = FailureReport.model_validate(
        _json_object(
            _read_bytes(
                repo_root,
                RUNTIME_MEMBER_PATHS["failure_report_v3.json"],
            ),
            RUNTIME_MEMBER_PATHS["failure_report_v3.json"],
        )
    )
    if summary.failure_code != failure.error_code:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_TERMINAL_MISMATCH",
            "summary and failure report disagree",
        )

    reports = tuple(
        ProbeTerminalReport.model_validate(
            _json_object(
                _read_bytes(
                    repo_root,
                    RUNTIME_MEMBER_PATHS[name],
                ),
                RUNTIME_MEMBER_PATHS[name],
            )
        )
        for name in (
            "p3_worker_startup_report_v3.json",
            "p4_deterministic_request_report_v3.json",
            "p5_prefix_cache_reset_report_v3.json",
            "p6_dual_worker_isolation_report_v3.json",
        )
    )
    expected = (
        ("P3", "FAILED", None, "P3_FAILED"),
        ("P4", "NOT_RUN", "P3", "P4_NOT_RUN"),
        ("P5", "NOT_RUN", "P3", "P5_NOT_RUN"),
        ("P6", "NOT_RUN", "P3", "P6_NOT_RUN"),
    )
    observed = tuple(
        (
            item.probe_id,
            item.status,
            item.blocked_by,
            item.decision,
        )
        for item in reports
    )
    if observed != expected:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_PROBE_TERMINAL_DRIFT",
            "P3-P6 terminal report sequence drifted",
        )

    ScratchCleanupReport.model_validate(
        _json_object(
            _read_bytes(
                repo_root,
                RUNTIME_MEMBER_PATHS["scratch_cleanup_report_v3.json"],
            ),
            RUNTIME_MEMBER_PATHS["scratch_cleanup_report_v3.json"],
        )
    )

    install = _json_object(
        _read_bytes(
            repo_root,
            RUNTIME_MEMBER_PATHS["runtime_install_report_v3.json"],
        ),
        RUNTIME_MEMBER_PATHS["runtime_install_report_v3.json"],
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
        "root_cause_review_required": False,
    }
    for key, value in expected_install.items():
        if install.get(key) != value:
            raise FailureAcceptanceError(
                "P3_P6_V3_FAILURE_ACCEPTANCE_INSTALL_DRIFT",
                f"runtime installation field drifted: {key}",
                RUNTIME_MEMBER_PATHS["runtime_install_report_v3.json"].as_posix(),
            )

    RuntimeImportClosureReport.model_validate(
        _json_object(
            _read_bytes(
                repo_root,
                RUNTIME_MEMBER_PATHS["runtime_import_closure_report_v3.json"],
            ),
            RUNTIME_MEMBER_PATHS["runtime_import_closure_report_v3.json"],
        )
    )
    return summary, failure


def _validate_false_negative(
    repo_root: Path,
    failure: FailureReport,
) -> None:
    _require_sha(
        repo_root,
        AUTHORIZED_NOTEBOOK_PATH,
        NOTEBOOK_SHA256,
    )
    template = _require_sha(
        repo_root,
        RUNTIME_TEMPLATE_PATH,
        TEMPLATE_SHA256,
    ).decode("utf-8")
    if EXPECTED_PREDICATE not in template:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_PREDICATE_DRIFT",
            "reviewed backend-marker predicate is unavailable",
            RUNTIME_TEMPLATE_PATH.as_posix(),
        )

    readiness = template.index("worker_1.wait_ready()")
    model = template.index("worker_1.validate_model()")
    backend = template.index("worker_1.wait_backend_marker()")
    if not readiness < model < backend:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_CONTROL_FLOW_DRIFT",
            "P3 readiness, model, and backend gate order drifted",
            RUNTIME_TEMPLATE_PATH.as_posix(),
        )

    diagnostics = failure.worker_1_diagnostics
    combined = diagnostics.stdout_tail + "\n" + diagnostics.stderr_tail
    lowered = combined.lower()
    if EXPECTED_BACKEND_MARKER not in combined:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_MARKER_MISSING",
            "authoritative TRITON_ATTN marker is unavailable",
            RUNTIME_MEMBER_PATHS["failure_report_v3.json"].as_posix(),
        )
    if "triton_attn" not in lowered:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_MARKER_COMPONENT_DRIFT",
            "TRITON_ATTN predicate component does not match",
        )
    if "attention backend" in lowered:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_FALSE_NEGATIVE_NOT_PROVEN",
            "the reviewed spaced predicate unexpectedly matches",
        )
    signatures = (
        "version 0.19.1",
        "attention_backend': 'TRITON_ATTN'",
        'GET /health HTTP/1.1" 200 OK',
        'GET /v1/models HTTP/1.1" 200 OK',
    )
    for signature in signatures:
        if signature not in combined:
            raise FailureAcceptanceError(
                "P3_P6_V3_FAILURE_ACCEPTANCE_RUNTIME_TRACE_INCOMPLETE",
                "runtime trace lacks a required signature",
                RUNTIME_MEMBER_PATHS["failure_report_v3.json"].as_posix(),
            )


def _validate_logs(repo_root: Path) -> None:
    log = _require_sha(
        repo_root,
        KAGGLE_LOG_PATH,
        KAGGLE_LOG_SHA256,
    ).decode("utf-8")
    signatures = (
        '"failure_code":"P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"',
        '"runtime_install_status":"PASSED"',
        '"runtime_import_closure_status":"PASSED"',
        '"failed_probe":"P3"',
        '"model_requests":0',
        "SystemExit: 2",
    )
    for signature in signatures:
        if signature not in log:
            raise FailureAcceptanceError(
                "P3_P6_V3_FAILURE_ACCEPTANCE_KAGGLE_LOG_INCOMPLETE",
                "Kaggle terminal log lacks a required signature",
                KAGGLE_LOG_PATH.as_posix(),
            )


def _validate_metadata(repo_root: Path) -> RootCauseAnalysis:
    SavedVersionReference.model_validate(
        _json_object(
            _require_sha(
                repo_root,
                REFERENCE_PATH,
                REFERENCE_SHA256,
            ),
            REFERENCE_PATH,
        )
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
        _json_object(
            _require_sha(
                repo_root,
                ROOT_CAUSE_PATH,
                ROOT_CAUSE_SHA256,
            ),
            ROOT_CAUSE_PATH,
        )
    )
    DuplicateEvidenceExclusion.model_validate(
        _json_object(
            _require_sha(
                repo_root,
                DUPLICATE_EXCLUSION_PATH,
                DUPLICATE_EXCLUSION_SHA256,
            ),
            DUPLICATE_EXCLUSION_PATH,
        )
    )
    IntakeValidationReceipt.model_validate(
        _json_object(
            _require_sha(
                repo_root,
                INTAKE_RECEIPT_PATH,
                INTAKE_RECEIPT_SHA256,
            ),
            INTAKE_RECEIPT_PATH,
        )
    )
    VllmBackendAuthority.model_validate(
        _json_object(
            _require_sha(
                repo_root,
                VLLM_AUTHORITY_PATH,
                VLLM_AUTHORITY_SHA256,
            ),
            VLLM_AUTHORITY_PATH,
        )
    )
    return root_cause


def _evidence_paths() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                INTAKE_ARCHIVE_PATH,
                AUTHORIZATION_EVIDENCE_PATH,
                CONSUMPTION_EVIDENCE_PATH,
                EVIDENCE_ZIP_PATH,
                KAGGLE_LOG_PATH,
                REFERENCE_PATH,
                LIMITATIONS_PATH,
                ROOT_CAUSE_PATH,
                DUPLICATE_EXCLUSION_PATH,
                INTAKE_RECEIPT_PATH,
                VLLM_AUTHORITY_PATH,
                *RUNTIME_MEMBER_PATHS.values(),
            ),
            key=lambda item: item.as_posix(),
        )
    )


def _validate_all(
    repo_root: Path,
) -> tuple[ArtifactReceipt, ...]:
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
    AuthorizationEvidence.model_validate(
        _json_object(
            authorization,
            AUTHORIZATION_EVIDENCE_PATH,
        )
    )
    ConsumptionEvidence.model_validate(
        _json_object(
            consumption,
            CONSUMPTION_EVIDENCE_PATH,
        )
    )
    _validate_intake_archive(repo_root)
    _validate_runtime_zip(repo_root)
    summary, failure = _validate_runtime_evidence(repo_root)
    _validate_false_negative(repo_root, failure)
    _validate_logs(repo_root)
    root_cause = _validate_metadata(repo_root)
    if summary.counters.model_requests != 0:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_REQUEST_OVERCLAIM",
            "request-level execution cannot be accepted",
        )
    if root_cause.formal_p3_acceptance_established is not False:
        raise FailureAcceptanceError(
            "P3_P6_V3_FAILURE_ACCEPTANCE_P3_OVERCLAIM",
            "formal P3 acceptance cannot be claimed",
        )
    return tuple(_receipt(repo_root, path) for path in _evidence_paths())


def _review() -> FailureAcceptanceReview:
    return FailureAcceptanceReview(
        review_id=("auragateway-cu129-p3-p6-runtime-diagnostic-failure-v3-review"),
        status=("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V3_CLASSIFIED"),
        decision=("ACCEPT_FAILED_LIFECYCLE_AND_QUARANTINE_INVALID_BACKEND_DIAGNOSTIC"),
        current_main_authority=CURRENT_MAIN_AUTHORITY,
        saved_version_id=SAVED_VERSION_ID,
        lifecycle_outcome="FAILED",
        reported_failure_code=("P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"),
        failed_probe="P3",
        runtime_install_status="PASSED",
        process_tree_import_closure_status="PASSED",
        evidence_disposition="QUARANTINED_INVALID_DIAGNOSTIC",
        root_cause_status=("CONFIRMED_FROM_RUNTIME_TRACE_AND_CODE_PATH"),
        first_divergence=(
            "BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER"
        ),
        worker_readiness_established=True,
        served_model_inventory_established=True,
        triton_attn_startup_selection_established=True,
        formal_p3_acceptance_established=False,
        request_level_attention_execution_established=False,
        executed_notebook_source_identity_verified=False,
        authorization_lifecycle_closed=True,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        runtime_execution_authorized=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "The governed V3 lifecycle outcome remains FAILED.",
            "The failed run is not rewritten as a successful P3 execution.",
            "Formal composite P3 acceptance is not established.",
            "Request-level attention execution is not established.",
            "P4 deterministic inference is not established.",
            "P5 cache reuse and reset are not established.",
            "P6 dual-worker isolation is not established.",
            "Measured A/B/C execution was not authorized or performed.",
            "Executed saved-version notebook identity is not verified.",
            "Complete native-library provenance is not established.",
            "Structured GPU teardown evidence is not established.",
            "Deployment and production readiness are not claimed.",
        ),
    )


def _record(
    repo_root: Path,
    evidence: tuple[ArtifactReceipt, ...],
    review_bytes: bytes,
) -> FailureAcceptanceRecord:
    return FailureAcceptanceRecord(
        record_id=("auragateway-cu129-p3-p6-runtime-diagnostic-failure-acceptance-v3"),
        status=("P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V3_VALID"),
        current_main_authority=CURRENT_MAIN_AUTHORITY,
        saved_version_id=SAVED_VERSION_ID,
        evidence=evidence,
        authorized_notebook=_receipt(
            repo_root,
            AUTHORIZED_NOTEBOOK_PATH,
        ),
        runtime_template=_receipt(
            repo_root,
            RUNTIME_TEMPLATE_PATH,
        ),
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
        executed_notebook_source_identity_verified=False,
        formal_p3_acceptance_established=False,
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> FailureAcceptanceRecord:
    root = repo_root.resolve()
    evidence = _validate_all(root)
    review = _review()
    review_bytes = review.canonical_json().encode("utf-8")
    (root / REVIEW_PATH).parent.mkdir(
        parents=True,
        exist_ok=True,
    )
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
        (
            RECORD_PATH,
            record.canonical_json().encode("utf-8"),
        ),
    )
    for relative, payload in expected:
        if _read_bytes(root, relative) != payload:
            raise FailureAcceptanceError(
                "P3_P6_V3_FAILURE_ACCEPTANCE_GENERATED_DRIFT",
                "generated failure-acceptance artifact drifted",
                relative.as_posix(),
            )
    return {
        "status": record.status,
        "saved_version_id": SAVED_VERSION_ID,
        "evidence_path_count": len(evidence),
        "lifecycle_outcome": "FAILED",
        "runtime_install_status": "PASSED",
        "process_tree_import_closure_status": "PASSED",
        "reported_failure_code": ("P3_P6_EXPLICIT_BACKEND_NOT_REALIZED"),
        "evidence_disposition": ("QUARANTINED_INVALID_DIAGNOSTIC"),
        "confirmed_first_divergence": (
            "BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER"
        ),
        "worker_readiness_established": True,
        "served_model_inventory_established": True,
        "triton_attn_startup_selection_established": True,
        "formal_p3_acceptance_established": False,
        "request_level_attention_execution_established": False,
        "executed_notebook_source_identity_verified": False,
        "authorization_lifecycle_closed": True,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p3-p6-failure-acceptance-v3")
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--repo-root",
            type=Path,
            required=True,
        )
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
    except (
        FailureAcceptanceError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        if isinstance(error, FailureAcceptanceError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            }
        else:
            payload = {
                "error_code": ("P3_P6_V3_FAILURE_ACCEPTANCE_UNEXPECTED"),
                "safe_message": str(error),
                "path": None,
            }
        print(_canonical(payload), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
