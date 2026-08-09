"""Reconcile offline verifier V2 and freeze the exact-runtime native capability contract."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_COMMIT: Final = "ab37702c3a086f5856ba2ed84272670a88ec4eac"
V2_FEATURE_COMMIT: Final = "3a569ecc87ac297ad078e10c542c26297e92ef72"
V2_SAVED_VERSION_ID: Final = 341096416

V2_EXECUTED_NOTEBOOK_SHA256: Final = (
    "81dade4abf79f1a5984101f9e7d0091f2fb748437b1aece0538678db633202cc"
)
V2_EXECUTED_NOTEBOOK_SIZE_BYTES: Final = 66482
V2_MARKDOWN_SOURCE_SHA256: Final = (
    "4c631b6e48745d42de49772ffe26386db94faeef74129d4141f5f12eb002f7af"
)
V2_CODE_SOURCE_SHA256: Final = "7481ede9619e3c307ae2971afce4558ae48b00c3ed72bc07dbb41e00a5b421e9"
V2_EXECUTION_LOG_SHA256: Final = "7b4ae0b97c6caae4f6ea2f099a691ca28a9fdf7215be6f2491c74dff0c2301aa"
V2_EXECUTION_LOG_SIZE_BYTES: Final = 3423
V2_EVIDENCE_ZIP_SHA256: Final = "10ed35bb8e9f9718eb7cd7e945ed8cf8503414c8ef400e70109b46fceff4e96b"
V2_EVIDENCE_ZIP_SIZE_BYTES: Final = 8012

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "preflight_v3_exact_runtime_offline_compatibility_v2_reconciliation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_preflight_v3_exact_runtime_offline_compatibility_v2_reconciliation_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-09-local-abc-preflight-v3-runtime-verifier-reconciliation-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V3_Runtime_Verifier_Reconciliation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_runtime_verifier_reconciliation_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_runtime_verifier_reconciliation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_runtime_verifier_reconciliation_v1_record.json"
)

EXPECTED_REPO_AUTHORITIES: Final[dict[Path, str]] = {
    Path(
        "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
    ): "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c",
    Path(
        "benchmarks/local_abc/"
        "auragateway_preflight_v3_exact_runtime_wheelhouse_materialization_acceptance_v1.json"
    ): "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725",
    Path(
        "benchmarks/local_abc/"
        "auragateway_preflight_v3_exact_runtime_offline_compatibility_v1_"
        "false_negative_acceptance.json"
    ): "86d679eb4cf76debb7afbecdc4573c10d1884fe343b424327b4477e9d5a1b27b",
    Path(
        "benchmarks/local_abc/"
        "auragateway_preflight_v3_exact_runtime_offline_compatibility_v2_"
        "implementation_record.json"
    ): "4feaddc8f62bc0ef0d529659f1e478c8b5f6623370b3d4fd80af2e5b40433174",
    Path(
        "benchmarks/local_abc/"
        "auragateway_preflight_v3_exact_runtime_offline_compatibility_v2_"
        "implementation_review.json"
    ): "9634476c5df81480786bfe0357bc1d2ca34c67f34672522772df9fcbee2d9842",
    Path(
        "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v2.py"
    ): "ecd672a77878adaf15f45225c3f539388b914935b310875311d65d5e5dd31cab",
    Path(
        "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v2.py"
    ): "17787658fedc680b5eb5c0e17df3bc9bd06f433d13d5f30fa4cec67615d64d9b",
    Path(
        "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v2.ipynb"
    ): "50483ae39a6f1561afff9b1f5be2c39be04ec04a5575e6ca53e1d7ebe1bac0e9",
    Path(
        "src/auragateway/local_abc/full_abc_local_vllm_cu129_controlled_python_startup.py"
    ): "5fd29ec95f8c9b385573cafa4dfa11abdcfd7c3ebfb5b67c44576d19fac3276c",
    Path(
        "src/auragateway/local_abc/full_abc_local_vllm_cu129_target_first_loader.py"
    ): "6648ad5defa4520cf2f6be16955f115b2184ab7121b7d131a8576180b2916adc",
    Path(
        "docs/reports/AuraGateway_CU129_Verifier_V5_Python_Startup_Reasoning_Certificate.md"
    ): "d9b228d6ee891e72146794fd0a171ad22354ae8e5195d8b14ae6b2f6bb221bfd",
    Path("docs/runbooks/local_abc_vllm_cu129_controlled_python_startup_v1.md"): (
        "28b1d73fcd3159890933ba5cc8cebf156b548d6e9d60972e5e1d51c61f287a4a"
    ),
    Path("docs/runbooks/local_abc_vllm_cu129_target_first_loader_v1.md"): (
        "d2bd506800f172b4bd1d9240ed8df36c42c5dce5508c38dd23f0f8ac08cff168"
    ),
    Path(
        "benchmarks/local_abc/"
        "auragateway_cu129_explicit_driver_link_probe_execution_acceptance_v1.json"
    ): "7ad15cd95d58ffd327427b694a4d32c37f1e0222bb0cf9c361529e9528f3c722",
}

EXPECTED_EVIDENCE_MEMBERS: Final = (
    (
        "input_validation.json",
        "693c02a039c838e2e76cf4df1002ae4c07a951f787932b141699c6bfe5884604",
        1252,
    ),
    (
        "probe_records.json",
        "a3c53e409552bcb6498d090abb6b650501dffecbd49f02620f511101db1ad2cb",
        26868,
    ),
    (
        "verification_summary.json",
        "e295e0b8cdce884532cf053836df0749cc2a672d880945e95fca7baad5f3061f",
        1851,
    ),
    (
        "evidence_manifest.json",
        "ad3c41692615e73db10da36c4977705c7e0ed9a65ff287f1f3d7c241cb359c69",
        438,
    ),
)

EXPECTED_REQUIRED_ROLE_STATUSES: Final[dict[str, str]] = {
    "input_validation": "PASSED",
    "base_python_runtime": "PASSED",
    "base_pip_import": "PASSED",
    "base_distribution_snapshot_before": "PASSED",
    "gpu_topology": "PASSED",
    "target_environment_creation": "PASSED",
    "target_runtime_identity_before_install": "PASSED",
    "base_pip_python_target_support": "PASSED",
    "offline_hash_locked_install_via_base_pip": "PASSED",
    "target_distribution_inventory": "PASSED",
    "target_dependency_check_via_base_pip": "PASSED",
    "python_runtime": "PASSED",
    "torch_family_runtime": "PASSED",
    "transformers_runtime": "PASSED",
    "triton_distribution": "PASSED",
    "vllm_distribution": "PASSED",
    "vllm_module": "PASSED",
    "vllm_native_extension": "FAILED",
    "base_distribution_snapshot_after": "PASSED",
}

NEXT_GATE: Final = (
    "design_and_implement_final_preflight_v3_exact_runtime_offline_verifier_"
    "from_reconciled_capability_contract"
)


class ReconciliationError(RuntimeError):
    """Typed safe failure for verifier reconciliation operations."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class ErrorEnvelope(LocalABCContract):
    """Machine-readable safe CLI error."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ArtifactReceipt(LocalABCContract):
    """Identity of one repository or external artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class EvidenceMemberReceipt(LocalABCContract):
    """Expected immutable member inside the V2 evidence archive."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class V2DiagnosticEvidence(LocalABCContract):
    """Exact V2 execution evidence used for the repository disposition."""

    saved_version_id: Literal[341096416]
    executed_notebook_sha256: Literal[
        "81dade4abf79f1a5984101f9e7d0091f2fb748437b1aece0538678db633202cc"
    ]
    execution_log_sha256: Literal[
        "7b4ae0b97c6caae4f6ea2f099a691ca28a9fdf7215be6f2491c74dff0c2301aa"
    ]
    evidence_zip_sha256: Literal["10ed35bb8e9f9718eb7cd7e945ed8cf8503414c8ef400e70109b46fceff4e96b"]
    executed_markdown_source_sha256: Literal[
        "4c631b6e48745d42de49772ffe26386db94faeef74129d4141f5f12eb002f7af"
    ]
    executed_code_source_sha256: Literal[
        "7481ede9619e3c307ae2971afce4558ae48b00c3ed72bc07dbb41e00a5b421e9"
    ]
    source_parity_with_repository: Literal[True]
    technical_status: Literal["FAILED_PENDING_REVIEW"]
    failed_required_roles: tuple[Literal["vllm_native_extension"], ...]
    vllm_distribution_status: Literal["PASSED"]
    vllm_module_status: Literal["PASSED"]
    vllm_module_returncode: Literal[0]
    observed_vllm_distribution_version: Literal["0.25.1+cu129"]
    observed_vllm_module_semantic_version: Literal["0.25.1"]
    native_probe_module: Literal["vllm._C"]
    native_probe_status: Literal["FAILED"]
    native_probe_returncode: Literal[1]
    native_probe_exception: Literal["ModuleNotFoundError"]
    startup_canary_observed: Literal[True]
    startup_canary: Literal["sitecustomize_missing_wrapt"]
    startup_canary_causal_role: Literal["UNPROVEN"]
    package_installation_performed: Literal[True]
    model_loads_performed: Literal[0]
    worker_startups_performed: Literal[0]
    model_requests_performed: Literal[0]
    benchmark_trajectories_performed: Literal[0]
    exact_runtime_offline_verified: Literal[False]
    runtime_incompatibility_established: Literal[False]
    evidence_members: tuple[EvidenceMemberReceipt, ...]

    @model_validator(mode="after")
    def require_exact_member_authority(self) -> Self:
        expected = tuple(
            EvidenceMemberReceipt(path=path, sha256=sha256, size_bytes=size)
            for path, sha256, size in EXPECTED_EVIDENCE_MEMBERS
        )
        if self.evidence_members != expected:
            raise ValueError("V2 evidence member authority drifted")
        if self.failed_required_roles != ("vllm_native_extension",):
            raise ValueError("V2 failed required role set drifted")
        return self


class HistoricalControlContract(LocalABCContract):
    """Previously solved startup and loader controls recovered for the final runtime."""

    python_environment_policy: Literal["DROP_PYTHONPATH_AND_PYTHONHOME_SET_PYTHONNOUSERSITE"]
    python_startup_policy: Literal["NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"]
    sitecustomize_policy: Literal["CONTROLLED_SENTINEL_BEFORE_SITE_MAIN"]
    usercustomize_policy: Literal["CONTROLLED_SENTINEL_BEFORE_SITE_MAIN"]
    external_package_path_policy: Literal["REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES"]
    canonical_loader_policy: Literal["TARGET_NVIDIA_LIBRARIES_PREPENDED"]
    real_driver_directory: Literal["/usr/local/nvidia/lib64"]
    cuda_stub_policy: Literal["REJECT"]
    ambient_python_package_native_library_policy: Literal["REJECT"]
    historical_runtime_promoted_to_current_qualification: Literal[False]


class NativeCapabilityContract(LocalABCContract):
    """Minimum exact-runtime capability contract before exact-runtime P5/P6."""

    current_boundary: Literal["P0_FINAL_RUNTIME_VERIFIER_RECONCILIATION"]
    sequencing_authority: Literal["HANDOVER_V17_AND_CURRENT_REPOSITORY_EVIDENCE"]
    original_prd_role: Literal["HISTORICAL_NORTH_STAR_AND_DESIGN_CONTEXT_ONLY"]
    exact_runtime_python: Literal["3.12"]
    exact_runtime_torch: Literal["2.11.0+cu129"]
    exact_runtime_torch_cuda: Literal["12.9"]
    exact_runtime_transformers: Literal["5.14.1"]
    exact_runtime_triton: Literal["3.6.0"]
    exact_runtime_vllm_distribution: Literal["0.25.1+cu129"]
    exact_runtime_vllm_module_semantic_version: Literal["0.25.1"]
    stale_v2_native_probe: Literal["vllm._C"]
    required_cuda_native_module: Literal["vllm._C_stable_libtorch"]
    capability_layers: tuple[str, ...]
    controlled_python_startup_required: Literal[True]
    native_inventory_required: Literal[True]
    native_loader_provenance_required: Literal[True]
    target_torch_libraries_required: Literal[True]
    target_nvidia_wheel_libraries_first: Literal[True]
    real_nvidia_driver_path_permitted: Literal[True]
    cuda_stub_paths_permitted: Literal[False]
    unapproved_ambient_python_native_libraries_permitted: Literal[False]
    successful_native_import_alone_sufficient: Literal[False]
    model_loads_permitted: Literal[0]
    worker_startups_permitted: Literal[0]
    model_requests_permitted: Literal[0]
    benchmark_trajectories_permitted: Literal[0]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]

    @model_validator(mode="after")
    def require_exact_layers(self) -> Self:
        expected = (
            "ARTIFACT_CLOSURE",
            "OFFLINE_INSTALLATION_CLOSURE",
            "CONTROLLED_PYTHON_STARTUP_CLOSURE",
            "NATIVE_EXTENSION_INVENTORY",
            "NATIVE_LOADER_CLOSURE_AND_PROVENANCE",
            "VLLM_0_25_1_CUDA_PLATFORM_CAPABILITY",
        )
        if self.capability_layers != expected:
            raise ValueError("native capability layer contract drifted")
        return self


class ReconciliationDisposition(LocalABCContract):
    """Repository disposition of V2 without promoting runtime compatibility."""

    decision: Literal["ACCEPT_V2_DIAGNOSTIC_HARNESS_DEFECT_AND_FREEZE_CAPABILITY_CONTRACT"]
    classification: Literal["STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE"]
    root_cause_status: Literal["ESTABLISHED"]
    verifier_validity_status: Literal["V2_NATIVE_PROBE_INVALID_FOR_TARGET_CUDA_PATH"]
    v2_repository_disposition: Literal["ACCEPTED_DIAGNOSTIC_FAILURE"]
    v2_replay_authorized: Literal[False]
    runtime_incompatibility_established: Literal[False]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    variance_pilot_accepted: Literal[False]
    repetition_count_frozen: Literal[False]
    execution_manifest_frozen: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_expensive_execution_permitted: Literal[False]
    next_gate: Literal[
        "design_and_implement_final_preflight_v3_exact_runtime_offline_verifier_"
        "from_reconciled_capability_contract"
    ]


class ReconciliationReview(LocalABCContract):
    """Deterministic review binding the V2 evidence and final capability contract."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-preflight-v3-runtime-verifier-reconciliation-v1-review"]
    status: Literal["APPROVED_FOR_REPOSITORY_RECONCILIATION_ACCEPTANCE"]
    source_main_commit: Literal["ab37702c3a086f5856ba2ed84272670a88ec4eac"]
    v2_feature_commit: Literal["3a569ecc87ac297ad078e10c542c26297e92ef72"]
    v2_evidence: V2DiagnosticEvidence
    historical_controls: HistoricalControlContract
    capability_contract: NativeCapabilityContract
    disposition: ReconciliationDisposition
    bound_repository_authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...] = Field(min_length=10)


class ReconciliationRecord(LocalABCContract):
    """Generated repository receipt for the V2 verifier reconciliation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-preflight-v3-runtime-verifier-reconciliation-v1-record"]
    status: Literal["PREFLIGHT_V3_RUNTIME_VERIFIER_RECONCILIATION_V1_VALID"]
    source_main_commit: Literal["ab37702c3a086f5856ba2ed84272670a88ec4eac"]
    v2_saved_version_id: Literal[341096416]
    v2_evidence: V2DiagnosticEvidence
    historical_controls: HistoricalControlContract
    capability_contract: NativeCapabilityContract
    disposition: ReconciliationDisposition
    review: ArtifactReceipt
    source: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_expensive_execution_permitted: Literal[False]
    next_gate: Literal[
        "design_and_implement_final_preflight_v3_exact_runtime_offline_verifier_"
        "from_reconciled_capability_contract"
    ]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact(repo_root: Path, path: Path) -> ArtifactReceipt:
    target = repo_root / path
    if not target.is_file() or target.is_symlink():
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_ARTIFACT_UNSAFE",
            "a required reconciliation artifact is missing or unsafe",
            path.as_posix(),
        )
    payload = target.read_bytes()
    return ArtifactReceipt(
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _require_expected_repo_authorities(repo_root: Path) -> tuple[ArtifactReceipt, ...]:
    receipts: list[ArtifactReceipt] = []
    for path, expected_sha256 in EXPECTED_REPO_AUTHORITIES.items():
        receipt = _artifact(repo_root, path)
        if receipt.sha256 != expected_sha256:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_SOURCE_AUTHORITY_DRIFT",
                "a bound repository authority no longer matches inspected main",
                path.as_posix(),
                (expected_sha256, receipt.sha256),
            )
        receipts.append(receipt)
    return tuple(receipts)


def _require_source_main_ancestor(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_ANCESTRY_UNREADABLE",
            "reconciliation source ancestry could not be inspected",
        ) from error
    if result.returncode != 0:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_SOURCE_MAIN_MISSING",
            "the inspected post-PR-218 main is not an ancestor of HEAD",
        )


def _evidence_members() -> tuple[EvidenceMemberReceipt, ...]:
    return tuple(
        EvidenceMemberReceipt(path=path, sha256=sha256, size_bytes=size)
        for path, sha256, size in EXPECTED_EVIDENCE_MEMBERS
    )


def _v2_evidence() -> V2DiagnosticEvidence:
    return V2DiagnosticEvidence(
        saved_version_id=V2_SAVED_VERSION_ID,
        executed_notebook_sha256=V2_EXECUTED_NOTEBOOK_SHA256,
        execution_log_sha256=V2_EXECUTION_LOG_SHA256,
        evidence_zip_sha256=V2_EVIDENCE_ZIP_SHA256,
        executed_markdown_source_sha256=V2_MARKDOWN_SOURCE_SHA256,
        executed_code_source_sha256=V2_CODE_SOURCE_SHA256,
        source_parity_with_repository=True,
        technical_status="FAILED_PENDING_REVIEW",
        failed_required_roles=("vllm_native_extension",),
        vllm_distribution_status="PASSED",
        vllm_module_status="PASSED",
        vllm_module_returncode=0,
        observed_vllm_distribution_version="0.25.1+cu129",
        observed_vllm_module_semantic_version="0.25.1",
        native_probe_module="vllm._C",
        native_probe_status="FAILED",
        native_probe_returncode=1,
        native_probe_exception="ModuleNotFoundError",
        startup_canary_observed=True,
        startup_canary="sitecustomize_missing_wrapt",
        startup_canary_causal_role="UNPROVEN",
        package_installation_performed=True,
        model_loads_performed=0,
        worker_startups_performed=0,
        model_requests_performed=0,
        benchmark_trajectories_performed=0,
        exact_runtime_offline_verified=False,
        runtime_incompatibility_established=False,
        evidence_members=_evidence_members(),
    )


def _historical_controls() -> HistoricalControlContract:
    return HistoricalControlContract(
        python_environment_policy="DROP_PYTHONPATH_AND_PYTHONHOME_SET_PYTHONNOUSERSITE",
        python_startup_policy="NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        sitecustomize_policy="CONTROLLED_SENTINEL_BEFORE_SITE_MAIN",
        usercustomize_policy="CONTROLLED_SENTINEL_BEFORE_SITE_MAIN",
        external_package_path_policy="REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES",
        canonical_loader_policy="TARGET_NVIDIA_LIBRARIES_PREPENDED",
        real_driver_directory="/usr/local/nvidia/lib64",
        cuda_stub_policy="REJECT",
        ambient_python_package_native_library_policy="REJECT",
        historical_runtime_promoted_to_current_qualification=False,
    )


def _capability_contract() -> NativeCapabilityContract:
    return NativeCapabilityContract(
        current_boundary="P0_FINAL_RUNTIME_VERIFIER_RECONCILIATION",
        sequencing_authority="HANDOVER_V17_AND_CURRENT_REPOSITORY_EVIDENCE",
        original_prd_role="HISTORICAL_NORTH_STAR_AND_DESIGN_CONTEXT_ONLY",
        exact_runtime_python="3.12",
        exact_runtime_torch="2.11.0+cu129",
        exact_runtime_torch_cuda="12.9",
        exact_runtime_transformers="5.14.1",
        exact_runtime_triton="3.6.0",
        exact_runtime_vllm_distribution="0.25.1+cu129",
        exact_runtime_vllm_module_semantic_version="0.25.1",
        stale_v2_native_probe="vllm._C",
        required_cuda_native_module="vllm._C_stable_libtorch",
        capability_layers=(
            "ARTIFACT_CLOSURE",
            "OFFLINE_INSTALLATION_CLOSURE",
            "CONTROLLED_PYTHON_STARTUP_CLOSURE",
            "NATIVE_EXTENSION_INVENTORY",
            "NATIVE_LOADER_CLOSURE_AND_PROVENANCE",
            "VLLM_0_25_1_CUDA_PLATFORM_CAPABILITY",
        ),
        controlled_python_startup_required=True,
        native_inventory_required=True,
        native_loader_provenance_required=True,
        target_torch_libraries_required=True,
        target_nvidia_wheel_libraries_first=True,
        real_nvidia_driver_path_permitted=True,
        cuda_stub_paths_permitted=False,
        unapproved_ambient_python_native_libraries_permitted=False,
        successful_native_import_alone_sufficient=False,
        model_loads_permitted=0,
        worker_startups_permitted=0,
        model_requests_permitted=0,
        benchmark_trajectories_permitted=0,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
    )


def _disposition() -> ReconciliationDisposition:
    return ReconciliationDisposition(
        decision="ACCEPT_V2_DIAGNOSTIC_HARNESS_DEFECT_AND_FREEZE_CAPABILITY_CONTRACT",
        classification="STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE",
        root_cause_status="ESTABLISHED",
        verifier_validity_status="V2_NATIVE_PROBE_INVALID_FOR_TARGET_CUDA_PATH",
        v2_repository_disposition="ACCEPTED_DIAGNOSTIC_FAILURE",
        v2_replay_authorized=False,
        runtime_incompatibility_established=False,
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        variance_pilot_accepted=False,
        repetition_count_frozen=False,
        execution_manifest_frozen=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_expensive_execution_permitted=False,
        next_gate=NEXT_GATE,
    )


def _review(repo_root: Path) -> ReconciliationReview:
    return ReconciliationReview(
        review_id="auragateway-preflight-v3-runtime-verifier-reconciliation-v1-review",
        status="APPROVED_FOR_REPOSITORY_RECONCILIATION_ACCEPTANCE",
        source_main_commit=SOURCE_MAIN_COMMIT,
        v2_feature_commit=V2_FEATURE_COMMIT,
        v2_evidence=_v2_evidence(),
        historical_controls=_historical_controls(),
        capability_contract=_capability_contract(),
        disposition=_disposition(),
        bound_repository_authorities=_require_expected_repo_authorities(repo_root),
        non_claims=(
            "V2 does not establish exact-runtime incompatibility.",
            "V2 does not establish exact-runtime offline compatibility.",
            "The V2 vllm._C probe is not current CUDA-path capability authority.",
            "The sitecustomize/wrapt warning is not assigned as the V2 failure cause.",
            "Historical CUDA 12.9 startup controls are not current-line qualification proof.",
            "Historical target-first loader evidence is not current-line qualification proof.",
            "A future successful native import alone will not close provenance.",
            "No model load is authorized by this reconciliation.",
            "No worker startup is authorized by this reconciliation.",
            "No model request or benchmark trajectory is authorized by this reconciliation.",
            "Exact-runtime P5/P6 remains unqualified.",
            "Variance-pilot and final measured A/B/C execution remain unauthorized.",
        ),
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    except OSError as error:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_ATOMIC_WRITE_FAILED",
            "a reconciliation artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _record(repo_root: Path, review: ReconciliationReview) -> ReconciliationRecord:
    review_payload = review.canonical_json().encode("utf-8")
    return ReconciliationRecord(
        record_id="auragateway-preflight-v3-runtime-verifier-reconciliation-v1-record",
        status="PREFLIGHT_V3_RUNTIME_VERIFIER_RECONCILIATION_V1_VALID",
        source_main_commit=SOURCE_MAIN_COMMIT,
        v2_saved_version_id=V2_SAVED_VERSION_ID,
        v2_evidence=_v2_evidence(),
        historical_controls=_historical_controls(),
        capability_contract=_capability_contract(),
        disposition=_disposition(),
        review=ArtifactReceipt(
            path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review_payload),
            size_bytes=len(review_payload),
        ),
        source=_artifact(repo_root, SOURCE_PATH),
        tests=_artifact(repo_root, TEST_PATH),
        adr=_artifact(repo_root, ADR_PATH),
        report=_artifact(repo_root, REPORT_PATH),
        runbook=_artifact(repo_root, RUNBOOK_PATH),
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_expensive_execution_permitted=False,
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> ReconciliationRecord:
    """Generate deterministic reconciliation review and record artifacts."""

    root = repo_root.resolve()
    _require_source_main_ancestor(root)
    review = _review(root)
    record = _record(root, review)
    _write_atomic(root / REVIEW_PATH, review.canonical_json().encode("utf-8"))
    _write_atomic(root / RECORD_PATH, record.canonical_json().encode("utf-8"))
    return record


def _load_exact(path: Path, model: type[LocalABCContract]) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        parsed = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_STATIC_ARTIFACT_INVALID",
            "a static reconciliation artifact is missing or invalid",
            path.as_posix(),
        ) from error
    if observed != parsed.canonical_json():
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_STATIC_ARTIFACT_NOT_CANONICAL",
            "a static reconciliation artifact is not canonical JSON",
            path.as_posix(),
        )
    return parsed


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the repository reconciliation without executing the runtime."""

    root = repo_root.resolve()
    _require_source_main_ancestor(root)
    expected_review = _review(root)
    observed_review = cast(
        ReconciliationReview,
        _load_exact(root / REVIEW_PATH, ReconciliationReview),
    )
    if observed_review != expected_review:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_REVIEW_DRIFT",
            "the committed reconciliation review does not match current authorities",
            REVIEW_PATH.as_posix(),
        )
    expected_record = _record(root, observed_review)
    observed_record = cast(
        ReconciliationRecord,
        _load_exact(root / RECORD_PATH, ReconciliationRecord),
    )
    if observed_record != expected_record:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_RECORD_DRIFT",
            "the committed reconciliation record does not match current authorities",
            RECORD_PATH.as_posix(),
        )
    return {
        "status": observed_record.status,
        "v2_saved_version_id": V2_SAVED_VERSION_ID,
        "v2_repository_disposition": observed_record.disposition.v2_repository_disposition,
        "classification": observed_record.disposition.classification,
        "runtime_incompatibility_established": False,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_expensive_execution_permitted": False,
        "next_gate": NEXT_GATE,
    }


def _safe_member_name(name: str) -> str:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or "\\" in name:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
            "V2 evidence ZIP contains an unsafe member name",
            name,
        )
    normalized = pure.as_posix()
    if normalized != name or not normalized:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
            "V2 evidence ZIP contains a non-canonical member name",
            name,
        )
    return normalized


def _require_exact_external_file(path: Path, expected_sha256: str, expected_size: int) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EXTERNAL_EVIDENCE_UNSAFE",
            "an external V2 evidence file is missing or unsafe",
            str(path),
        )
    payload = path.read_bytes()
    if len(payload) != expected_size or _sha256_bytes(payload) != expected_sha256:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EXTERNAL_EVIDENCE_IDENTITY_MISMATCH",
            "an external V2 evidence file identity does not match the handover authority",
            str(path),
        )
    return payload


def _json_object(payload: bytes, label: str) -> dict[str, object]:
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_JSON_INVALID",
            "a V2 evidence JSON payload is invalid",
            label,
        ) from error
    if not isinstance(decoded, dict):
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_JSON_INVALID",
            "a V2 evidence JSON payload must be an object",
            label,
        )
    return cast(dict[str, object], decoded)


def _dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_SEMANTICS_MISMATCH",
            "a required V2 evidence object is missing",
            label,
        )
    return cast(dict[str, object], value)


def _validate_notebook(payload: bytes) -> None:
    notebook = _json_object(payload, "executed_notebook")
    metadata = _dict(notebook.get("metadata"), "executed_notebook.metadata")
    auragateway = _dict(metadata.get("auragateway"), "executed_notebook.metadata.auragateway")
    expected_metadata: dict[str, object] = {
        "accepted_materializer_script_version_id": 341083505,
        "benchmark_trajectories_permitted": 0,
        "dependency_resolution_permitted": False,
        "exact_resolution_lock_sha256": (
            "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
        ),
        "expected_package_count": 196,
        "expected_sha_manifest_entry_count": 200,
        "expected_total_wheel_bytes": 6164913809,
        "final_measured_abc_execution_authorized": False,
        "internet_required": False,
        "materialization_acceptance_sha256": (
            "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725"
        ),
        "model_loads_permitted": 0,
        "model_requests_permitted": 0,
        "pilot_execution_authorized": False,
        "runtime_execution_authorized": False,
        "v1_false_negative_acceptance_sha256": (
            "86d679eb4cf76debb7afbecdc4573c10d1884fe343b424327b4477e9d5a1b27b"
        ),
        "v1_false_negative_script_version_id": 341091805,
        "vllm_distribution_version": "0.25.1+cu129",
        "vllm_module_semantic_version": "0.25.1",
        "worker_startups_permitted": 0,
    }
    for key, expected in expected_metadata.items():
        if auragateway.get(key) != expected:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_NOTEBOOK_METADATA_MISMATCH",
                "executed V2 notebook metadata drifted",
                key,
            )
    cells = notebook.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_NOTEBOOK_SOURCE_MISMATCH",
            "executed V2 notebook cell shape drifted",
        )
    sources: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_NOTEBOOK_SOURCE_MISMATCH",
                "executed V2 notebook contains an invalid cell",
            )
        source = cell.get("source")
        if isinstance(source, str):
            sources.append(source)
        elif isinstance(source, list) and all(isinstance(item, str) for item in source):
            sources.append("".join(cast(list[str], source)))
        else:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_NOTEBOOK_SOURCE_MISMATCH",
                "executed V2 notebook contains invalid cell source",
            )
    observed_hashes = tuple(_sha256_bytes(source.encode("utf-8")) for source in sources)
    expected_hashes = (V2_MARKDOWN_SOURCE_SHA256, V2_CODE_SOURCE_SHA256)
    if observed_hashes != expected_hashes:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_NOTEBOOK_SOURCE_MISMATCH",
            "executed V2 notebook source identity drifted",
        )


def _validate_summary(summary: dict[str, object]) -> None:
    expected: dict[str, object] = {
        "offline_compatibility_status": "FAILED_PENDING_REVIEW",
        "failed_required_roles": ["vllm_native_extension"],
        "locked_package_count": 196,
        "validated_manifest_entry_count": 200,
        "total_wheel_bytes": 6164913809,
        "package_installation_performed": True,
        "model_loads_performed": 0,
        "worker_startups_performed": 0,
        "model_requests_performed": 0,
        "benchmark_trajectories_performed": 0,
        "qualification_claimed": False,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_V2_SUMMARY_MISMATCH",
                "V2 verification summary does not match the preserved diagnostic",
                key,
            )
    statuses = _dict(summary.get("required_role_statuses"), "required_role_statuses")
    if statuses != EXPECTED_REQUIRED_ROLE_STATUSES:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_V2_ROLE_STATUS_MISMATCH",
            "V2 required role statuses drifted",
        )


def _validate_probe_records(probes: dict[str, object]) -> None:
    module = _dict(probes.get("vllm_module"), "probe_records.vllm_module")
    native = _dict(
        probes.get("vllm_native_extension"),
        "probe_records.vllm_native_extension",
    )
    for key, expected in {"status": "PASSED", "returncode": 0}.items():
        if module.get(key) != expected:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_V2_MODULE_MISMATCH",
                "V2 vLLM module probe no longer matches the preserved diagnostic",
                key,
            )
    module_stdout = module.get("stdout_excerpt")
    if not isinstance(module_stdout, str) or '"vllm":"0.25.1"' not in module_stdout:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_V2_MODULE_MISMATCH",
            "V2 vLLM module semantic version evidence is missing",
            "stdout_excerpt",
        )
    for key, expected in {"status": "FAILED", "returncode": 1}.items():
        if native.get(key) != expected:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_V2_NATIVE_PROBE_MISMATCH",
                "V2 native probe no longer matches the preserved diagnostic",
                key,
            )
    native_stderr = native.get("stderr_excerpt")
    if not isinstance(native_stderr, str):
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_V2_NATIVE_PROBE_MISMATCH",
            "V2 native probe stderr evidence is missing",
            "stderr_excerpt",
        )
    required_fragments = (
        "ModuleNotFoundError: No module named 'vllm._C'",
        "Error in sitecustomize",
        "ModuleNotFoundError: No module named 'wrapt'",
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in native_stderr)
    if missing:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_V2_NATIVE_PROBE_MISMATCH",
            "V2 native probe evidence is missing required diagnostic fragments",
            details=missing,
        )


def _validate_evidence_zip(payload: bytes) -> None:
    expected = {path: (sha256, size) for path, sha256, size in EXPECTED_EVIDENCE_MEMBERS}
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            names: list[str] = []
            for info in archive.infolist():
                if info.is_dir():
                    raise ReconciliationError(
                        "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
                        "V2 evidence ZIP contains an unexpected directory",
                        info.filename,
                    )
                names.append(_safe_member_name(info.filename))
            if len(names) != len(set(names)) or set(names) != set(expected):
                raise ReconciliationError(
                    "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_MEMBER_SET_MISMATCH",
                    "V2 evidence ZIP member set drifted",
                )
            for name in names:
                member = archive.read(name)
                expected_sha256, expected_size = expected[name]
                if len(member) != expected_size or _sha256_bytes(member) != expected_sha256:
                    raise ReconciliationError(
                        "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_MEMBER_IDENTITY_MISMATCH",
                        "a V2 evidence member identity drifted",
                        name,
                    )
            summary = _json_object(
                archive.read("verification_summary.json"),
                "verification_summary",
            )
            probes = _json_object(archive.read("probe_records.json"), "probe_records")
            _validate_summary(summary)
            _validate_probe_records(probes)
    except zipfile.BadZipFile as error:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EVIDENCE_ZIP_INVALID",
            "V2 evidence ZIP is invalid",
        ) from error


def verify_evidence(
    executed_notebook: Path,
    execution_log: Path,
    evidence_zip: Path,
) -> dict[str, object]:
    """Verify exact external V2 evidence without executing or authorizing runtime work."""

    notebook_payload = _require_exact_external_file(
        executed_notebook,
        V2_EXECUTED_NOTEBOOK_SHA256,
        V2_EXECUTED_NOTEBOOK_SIZE_BYTES,
    )
    log_payload = _require_exact_external_file(
        execution_log,
        V2_EXECUTION_LOG_SHA256,
        V2_EXECUTION_LOG_SIZE_BYTES,
    )
    evidence_payload = _require_exact_external_file(
        evidence_zip,
        V2_EVIDENCE_ZIP_SHA256,
        V2_EVIDENCE_ZIP_SIZE_BYTES,
    )
    _validate_notebook(notebook_payload)
    _validate_evidence_zip(evidence_payload)
    log_text = log_payload.decode("utf-8")
    required_log_fragments = (
        '"offline_compatibility_status":"FAILED_PENDING_REVIEW"',
        '"failed_required_roles":["vllm_native_extension"]',
        '"exact_runtime_offline_verified":false',
        '"runtime_execution_authorized":false',
        '"pilot_execution_authorized":false',
        '"final_measured_abc_execution_authorized":false',
    )
    missing = tuple(fragment for fragment in required_log_fragments if fragment not in log_text)
    if missing:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_EXECUTION_LOG_MISMATCH",
            "V2 execution log lacks required terminal diagnostic markers",
            details=missing,
        )
    return {
        "status": "V2_EXTERNAL_DIAGNOSTIC_EVIDENCE_VERIFIED",
        "saved_version_id": V2_SAVED_VERSION_ID,
        "classification": "STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE",
        "runtime_incompatibility_established": False,
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_expensive_execution_permitted": False,
        "next_gate": NEXT_GATE,
    }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError(
            "PREFLIGHT_V3_RECONCILIATION_ARGUMENT_INVALID",
            "reconciliation command arguments are invalid",
            details=(message,),
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-preflight-v3-verifier-reconciliation-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate-implementation"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    verify = subparsers.add_parser("verify-evidence")
    verify.add_argument("--executed-notebook", type=Path, required=True)
    verify.add_argument("--execution-log", type=Path, required=True)
    verify.add_argument("--evidence-zip", type=Path, required=True)
    return parser


def _error_json(error: ReconciliationError) -> str:
    return ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Run one reconciliation command."""

    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        command = cast(str, arguments.command)
        if command == "generate":
            record = generate(cast(Path, arguments.repo_root))
            result: dict[str, object] = {
                "status": record.status,
                "v2_saved_version_id": V2_SAVED_VERSION_ID,
                "v2_repository_disposition": record.disposition.v2_repository_disposition,
                "classification": record.disposition.classification,
                "runtime_incompatibility_established": False,
                "exact_runtime_offline_verified": False,
                "runtime_execution_authorized": False,
                "pilot_execution_authorized": False,
                "final_measured_abc_execution_authorized": False,
                "next_expensive_execution_permitted": False,
                "next_gate": NEXT_GATE,
            }
        elif command == "validate-implementation":
            result = validate_implementation(cast(Path, arguments.repo_root))
        elif command == "verify-evidence":
            result = verify_evidence(
                cast(Path, arguments.executed_notebook),
                cast(Path, arguments.execution_log),
                cast(Path, arguments.evidence_zip),
            )
        else:
            raise ReconciliationError(
                "PREFLIGHT_V3_RECONCILIATION_COMMAND_INVALID",
                "verifier reconciliation command is invalid",
            )
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0
    except ReconciliationError as error:
        print(_error_json(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
