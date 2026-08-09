"""Build and validate the reconciled final preflight-v3 exact-runtime offline verifier V4."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import Field, model_validator

from auragateway.local_abc.contracts import LocalABCContract

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "138ac906d0bc0179af3cbf207d8cb7c1d1d7f8bc"
RECONCILIATION_RECORD_SHA256: Final = (
    "070b625adb51e48ad29859e86d3a58c3149f17807fec9a98eafa283761c7833e"
)
RECONCILIATION_REVIEW_SHA256: Final = (
    "843f2c7b5d36bfcc46d50be8a1b3288dbcfb93c24cb0c4cb6d6aea11970b2d47"
)
EXPECTED_NOTEBOOK_SHA256: Final = "db4725b508322948ca4a9c29a48283f83ab047873a3eadb530e9f32e6a5490e9"

NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v4.ipynb"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v4.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v4.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-09-local-abc-preflight-v3-"
    "input-validation-reconciliation-and-final-offline-verifier-v4.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V3_Input_Validation_"
    "Reconciliation_and_Final_Offline_Verifier_V4.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_final_exact_runtime_offline_verifier_v4.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_implementation_record.json"
)

RECONCILIATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_runtime_verifier_reconciliation_v1_record.json"
)
RECONCILIATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_runtime_verifier_reconciliation_v1_review.json"
)
RESOLUTION_LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
MATERIALIZATION_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_wheelhouse_materialization_acceptance_v1.json"
)

MATERIALIZATION_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/evidence/"
    "preflight_v3_exact_runtime_wheelhouse_materialization_v1/"
    "materialization_receipt.json"
)
MATERIALIZATION_RECEIPT_SHA256: Final = (
    "55bc8d078af9960d5f6a60bf7d9638820be9fdda0ee76754a9462d46eb053fe0"
)
PREDECESSOR_V3_SAVED_VERSION_ID: Final[Literal[341197546]] = 341197546
PREDECESSOR_V3_EXECUTED_NOTEBOOK_SHA256: Final = (
    "d4982f95b1a061eb8e810d1a1dcce99076bc6bd006ef1cd637bc2e288818bf07"
)
PREDECESSOR_V3_EXECUTION_LOG_SHA256: Final = (
    "332c2918674d3c587c1b6d6e4d02f3d6a7ed813a78cedaf8f46c8d1367790013"
)
PREDECESSOR_V3_EVIDENCE_ZIP_SHA256: Final = (
    "e4721b2ba1fd91f96370b90e6c839e13d8982f362af435080f073d5847dadcc5"
)
PREDECESSOR_V3_INPUT_VALIDATION_SHA256: Final = (
    "7fae411b3fceb129a8ac007a449324da169a6f56cbbab290b01c6f075cd80c01"
)
PREDECESSOR_V3_PROBE_RECORDS_SHA256: Final = (
    "e60c98f4e17673fc1516a1dfa22f5814f533a8e0a974e10f6a7e0c16c7327e69"
)
PREDECESSOR_V3_VERIFICATION_SUMMARY_SHA256: Final = (
    "45f708bf00d95f25b7a9e0ee4eb18ed427dd4d8aea6c05936b162a8ce3f2ac21"
)
PREDECESSOR_V3_EVIDENCE_MANIFEST_SHA256: Final = (
    "f2aa5adf17cca615ec20a237495e6b406f591bafc0748c10dd86e9942af3e7a5"
)
PREDECESSOR_V3_FIRST_DIVERGENCE: Final[
    Literal["materialization receipt drifted: controlled_python_startup_required"]
] = "materialization receipt drifted: controlled_python_startup_required"
PREDECESSOR_V3_AUTHORIZATION_CONSUMPTION_SHA256: Final = (
    "5a0fd520e2df11b25105dbabc4ddd1809e27af378c3d0fb8db7990809e08d9a8"
)
PREDECESSOR_V3_FAILURE_CLASS: Final[Literal["DIAGNOSTIC_HARNESS_DEFECT"]] = (
    "DIAGNOSTIC_HARNESS_DEFECT"
)
PREDECESSOR_V3_FAILURE_CODE: Final[
    Literal["BACKPROJECTED_UPSTREAM_RECEIPT_SEMANTIC_REQUIREMENT"]
] = "BACKPROJECTED_UPSTREAM_RECEIPT_SEMANTIC_REQUIREMENT"

EXPECTED_AUTHORITIES: Final[dict[Path, str]] = {
    RECONCILIATION_RECORD_PATH: RECONCILIATION_RECORD_SHA256,
    RECONCILIATION_REVIEW_PATH: RECONCILIATION_REVIEW_SHA256,
    RESOLUTION_LOCK_PATH: "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c",
    MATERIALIZATION_ACCEPTANCE_PATH: (
        "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725"
    ),
    MATERIALIZATION_RECEIPT_PATH: MATERIALIZATION_RECEIPT_SHA256,
}

MATERIALIZER_PRODUCER_RECEIPT_EXPECTED: Final[dict[str, object]] = {
    "materialization_status": "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
    "exact_resolution_lock_sha256": (
        "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
    ),
    "locked_package_count": 196,
    "downloaded_package_count": 196,
    "wheel_file_count": 196,
    "authority_host_count": 5,
    "observed_transport_redirect_event_count": 1,
    "total_wheel_bytes": 6164913809,
    "dependency_resolution_performed": False,
    "package_installation_performed": False,
    "model_loads_performed": 0,
    "model_requests_performed": 0,
    "benchmark_trajectories_performed": 0,
    "credentials_used": False,
    "customer_data_used": False,
    "external_spend": 0,
    "wheelhouse_materialized": True,
    "exact_runtime_materialized": False,
    "exact_runtime_offline_verified": False,
    "qualification_claimed": False,
    "sha256_manifest_sha256": ("00dbda4fd734cf94b6f5dfde2619f83ed6a4db7761a4c3c5ace6b0f1ebe63b08"),
}
VERIFIER_CONSUMER_CAPABILITY_POLICY: Final[dict[str, object]] = {
    "controlled_python_startup_required": True,
    "native_loader_provenance_required": True,
    "successful_native_import_alone_sufficient": False,
}

REQUIRED_CAPABILITY_ROLES: Final = (
    "input_validation",
    "base_python_runtime",
    "base_pip_import",
    "base_distribution_snapshot_before",
    "gpu_topology",
    "target_environment_creation",
    "target_runtime_identity_before_install",
    "base_pip_python_target_support",
    "offline_hash_locked_install_via_base_pip",
    "target_distribution_inventory",
    "target_dependency_check_via_base_pip",
    "controlled_python_startup",
    "target_native_inventory",
    "canonical_loader_environment",
    "python_runtime",
    "torch_family_runtime",
    "transformers_runtime",
    "triton_distribution",
    "vllm_distribution",
    "vllm_module",
    "native_linker_static_provenance",
    "vllm_native_extension",
    "native_runtime_provenance",
    "cuda_platform_capability",
    "base_distribution_snapshot_after",
)

NEXT_GATE: Final = (
    "implement_single_use_final_preflight_v3_exact_runtime_offline_verifier_v4_authorization"
)


class VerifierImplementationError(RuntimeError):
    """Fail-closed error for static final-verifier implementation validation."""

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
    """Machine-readable CLI error."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ArtifactIdentity(LocalABCContract):
    """Identity of one implementation artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class CapabilityContract(LocalABCContract):
    """Static implementation contract inherited from reconciliation V1."""

    current_boundary: Literal["P0_FINAL_RUNTIME_OFFLINE_VERIFIER_V4_IMPLEMENTATION"]
    exact_runtime_python: Literal["3.12"]
    exact_runtime_torch: Literal["2.11.0+cu129"]
    exact_runtime_torch_cuda: Literal["12.9"]
    exact_runtime_transformers: Literal["5.14.1"]
    exact_runtime_triton: Literal["3.6.0"]
    exact_runtime_vllm_distribution: Literal["0.25.1+cu129"]
    exact_runtime_vllm_module_semantic_version: Literal["0.25.1"]
    required_cuda_native_module: Literal["vllm._C_stable_libtorch"]
    required_capability_roles: tuple[str, ...]
    python_startup_policy: Literal["NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"]
    python_environment_policy: Literal["DROP_PYTHONPATH_AND_PYTHONHOME_SET_PYTHONNOUSERSITE"]
    sitecustomize_policy: Literal["CONTROLLED_SENTINEL_BEFORE_SITE_MAIN"]
    usercustomize_policy: Literal["CONTROLLED_SENTINEL_BEFORE_SITE_MAIN"]
    canonical_loader_policy: Literal["TARGET_RUNTIME_LIBRARIES_BEFORE_FILTERED_AMBIENT"]
    static_linker_provenance_required: Literal[True]
    dynamic_loader_provenance_required: Literal[True]
    real_driver_directory: Literal["/usr/local/nvidia/lib64"]
    cuda_stub_and_compat_paths_permitted: Literal[False]
    unapproved_ambient_python_native_libraries_permitted: Literal[False]
    successful_native_import_alone_sufficient: Literal[False]
    model_loads_permitted: Literal[0]
    worker_startups_permitted: Literal[0]
    model_requests_permitted: Literal[0]
    benchmark_trajectories_permitted: Literal[0]

    @model_validator(mode="after")
    def require_exact_roles(self) -> Self:
        if self.required_capability_roles != REQUIRED_CAPABILITY_ROLES:
            raise ValueError("final verifier role contract drifted")
        return self


class PredecessorV3Diagnostic(LocalABCContract):
    """Immutable diagnostic disposition for governed V3 saved version 341197546."""

    saved_version_id: Literal[341197546]
    terminal_status: Literal["FAILED_PENDING_REVIEW"]
    failure_class: Literal["DIAGNOSTIC_HARNESS_DEFECT"]
    failure_code: Literal["BACKPROJECTED_UPSTREAM_RECEIPT_SEMANTIC_REQUIREMENT"]
    executed_notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_validation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    probe_records_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_summary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_divergence: Literal["materialization receipt drifted: controlled_python_startup_required"]
    authorization_consumption_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_installation_started: Literal[False]
    native_capability_tested: Literal[False]
    runtime_incompatibility_established: Literal[False]
    authorization_reusable: Literal[False]


class ProducerConsumerContract(LocalABCContract):
    """Ownership boundary between immutable producer evidence and current policy."""

    historical_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    producer_owned_fields: tuple[str, ...]
    consumer_owned_fields: tuple[str, ...]
    historical_receipt_backprojection_permitted: Literal[False]
    exact_historical_receipt_replay_required: Literal[True]
    pre_execution_compatibility_gate_required: Literal[True]


class ImplementationReview(LocalABCContract):
    """Deterministic static review for final verifier V4."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-implementation-review"
    ]
    status: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION_ACCEPTANCE"]
    implementation_base_main_commit: Literal["138ac906d0bc0179af3cbf207d8cb7c1d1d7f8bc"]
    reconciliation_record: ArtifactIdentity
    reconciliation_review: ArtifactIdentity
    predecessor_v3_diagnostic: PredecessorV3Diagnostic
    producer_consumer_contract: ProducerConsumerContract
    materialization_receipt: ArtifactIdentity
    capability_contract: CapabilityContract
    notebook: ArtifactIdentity
    source: ArtifactIdentity
    tests: ArtifactIdentity
    adr: ArtifactIdentity
    report: ArtifactIdentity
    runbook: ArtifactIdentity
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_expensive_execution_permitted: Literal[False]
    next_gate: Literal[
        "implement_single_use_final_preflight_v3_exact_runtime_offline_verifier_v4_authorization"
    ]
    non_claims: tuple[str, ...] = Field(min_length=8)


class ImplementationRecord(LocalABCContract):
    """Generated receipt for the static verifier implementation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-implementation-record"
    ]
    status: Literal["PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V4_IMPLEMENTATION_VALID"]
    implementation_base_main_commit: Literal["138ac906d0bc0179af3cbf207d8cb7c1d1d7f8bc"]
    review: ArtifactIdentity
    notebook: ArtifactIdentity
    source: ArtifactIdentity
    tests: ArtifactIdentity
    adr: ArtifactIdentity
    report: ArtifactIdentity
    runbook: ArtifactIdentity
    reconciliation_record_sha256: Literal[
        "070b625adb51e48ad29859e86d3a58c3149f17807fec9a98eafa283761c7833e"
    ]
    reconciliation_review_sha256: Literal[
        "843f2c7b5d36bfcc46d50be8a1b3288dbcfb93c24cb0c4cb6d6aea11970b2d47"
    ]
    predecessor_v3_diagnostic: PredecessorV3Diagnostic
    producer_consumer_contract: ProducerConsumerContract
    materialization_receipt: ArtifactIdentity
    required_cuda_native_module: Literal["vllm._C_stable_libtorch"]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_expensive_execution_permitted: Literal[False]
    next_gate: Literal[
        "implement_single_use_final_preflight_v3_exact_runtime_offline_verifier_v4_authorization"
    ]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _read_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VerifierImplementationError(
            "PREFLIGHT_V3_FINAL_VERIFIER_JSON_INVALID",
            "expected a JSON object",
            path.as_posix(),
        )
    return payload


def _identity(repo_root: Path, path: Path) -> ArtifactIdentity:
    target = repo_root / path
    return ArtifactIdentity(
        path=path.as_posix(),
        sha256=_sha256_file(target),
        size_bytes=target.stat().st_size,
    )


def _raise(error_code: str, message: str, path: Path | None = None) -> Never:
    raise VerifierImplementationError(
        error_code,
        message,
        None if path is None else path.as_posix(),
    )


def _require_base_main_ancestor(repo_root: Path) -> None:
    result = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            IMPLEMENTATION_BASE_MAIN_COMMIT,
            "HEAD",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_BASE_AUTHORITY_NOT_ANCESTOR",
            "implementation base main commit is not an ancestor of HEAD",
        )


def _require_authorities(repo_root: Path) -> None:
    for path, expected_sha in EXPECTED_AUTHORITIES.items():
        target = repo_root / path
        if not target.is_file():
            _raise(
                "PREFLIGHT_V3_FINAL_VERIFIER_AUTHORITY_MISSING",
                "required repository authority is missing",
                path,
            )
        if _sha256_file(target) != expected_sha:
            _raise(
                "PREFLIGHT_V3_FINAL_VERIFIER_AUTHORITY_DRIFT",
                "required repository authority SHA-256 drifted",
                path,
            )

    reconciliation = _read_object(repo_root / RECONCILIATION_RECORD_PATH)
    required = {
        "status": "PREFLIGHT_V3_RUNTIME_VERIFIER_RECONCILIATION_V1_VALID",
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_expensive_execution_permitted": False,
    }
    for key, expected in required.items():
        if reconciliation.get(key) != expected:
            _raise(
                "PREFLIGHT_V3_FINAL_VERIFIER_RECONCILIATION_SEMANTIC_DRIFT",
                f"reconciliation authority drifted: {key}",
                RECONCILIATION_RECORD_PATH,
            )
    capability = reconciliation.get("capability_contract")
    if not isinstance(capability, dict):
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_RECONCILIATION_CAPABILITY_MISSING",
            "reconciliation capability contract is missing",
            RECONCILIATION_RECORD_PATH,
        )
    if capability.get("required_cuda_native_module") != "vllm._C_stable_libtorch":
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_RECONCILIATION_CAPABILITY_DRIFT",
            "required CUDA native module drifted",
            RECONCILIATION_RECORD_PATH,
        )
    if capability.get("successful_native_import_alone_sufficient") is not False:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_RECONCILIATION_CAPABILITY_DRIFT",
            "native provenance requirement drifted",
            RECONCILIATION_RECORD_PATH,
        )


def _predecessor_v3_diagnostic() -> PredecessorV3Diagnostic:
    return PredecessorV3Diagnostic(
        saved_version_id=PREDECESSOR_V3_SAVED_VERSION_ID,
        terminal_status="FAILED_PENDING_REVIEW",
        failure_class=PREDECESSOR_V3_FAILURE_CLASS,
        failure_code=PREDECESSOR_V3_FAILURE_CODE,
        executed_notebook_sha256=PREDECESSOR_V3_EXECUTED_NOTEBOOK_SHA256,
        execution_log_sha256=PREDECESSOR_V3_EXECUTION_LOG_SHA256,
        evidence_zip_sha256=PREDECESSOR_V3_EVIDENCE_ZIP_SHA256,
        input_validation_sha256=PREDECESSOR_V3_INPUT_VALIDATION_SHA256,
        probe_records_sha256=PREDECESSOR_V3_PROBE_RECORDS_SHA256,
        verification_summary_sha256=PREDECESSOR_V3_VERIFICATION_SUMMARY_SHA256,
        evidence_manifest_sha256=PREDECESSOR_V3_EVIDENCE_MANIFEST_SHA256,
        first_divergence=PREDECESSOR_V3_FIRST_DIVERGENCE,
        authorization_consumption_sha256=PREDECESSOR_V3_AUTHORIZATION_CONSUMPTION_SHA256,
        package_installation_started=False,
        native_capability_tested=False,
        runtime_incompatibility_established=False,
        authorization_reusable=False,
    )


def _producer_consumer_contract() -> ProducerConsumerContract:
    return ProducerConsumerContract(
        historical_receipt_sha256=MATERIALIZATION_RECEIPT_SHA256,
        producer_owned_fields=tuple(sorted(MATERIALIZER_PRODUCER_RECEIPT_EXPECTED)),
        consumer_owned_fields=tuple(sorted(VERIFIER_CONSUMER_CAPABILITY_POLICY)),
        historical_receipt_backprojection_permitted=False,
        exact_historical_receipt_replay_required=True,
        pre_execution_compatibility_gate_required=True,
    )


def _validate_historical_materialization_receipt(repo_root: Path) -> None:
    path = repo_root / MATERIALIZATION_RECEIPT_PATH
    if _sha256_file(path) != MATERIALIZATION_RECEIPT_SHA256:
        _raise(
            "PREFLIGHT_V3_V4_MATERIALIZATION_RECEIPT_IDENTITY_DRIFT",
            "historical materialization receipt SHA-256 drifted",
            MATERIALIZATION_RECEIPT_PATH,
        )
    receipt = _read_object(path)
    for key, expected in MATERIALIZER_PRODUCER_RECEIPT_EXPECTED.items():
        if receipt.get(key) != expected:
            _raise(
                "PREFLIGHT_V3_V4_MATERIALIZATION_RECEIPT_SEMANTIC_DRIFT",
                f"historical materialization producer fact drifted: {key}",
                MATERIALIZATION_RECEIPT_PATH,
            )
    forbidden = tuple(key for key in VERIFIER_CONSUMER_CAPABILITY_POLICY if key in receipt)
    if forbidden:
        raise VerifierImplementationError(
            "PREFLIGHT_V3_V4_HISTORICAL_RECEIPT_POLICY_BACKPROJECTION",
            "historical materialization receipt contains consumer-owned policy fields",
            MATERIALIZATION_RECEIPT_PATH.as_posix(),
            forbidden,
        )


def _literal_assignment(code: str, name: str) -> object:
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    _raise(
        "PREFLIGHT_V3_V4_NOTEBOOK_CONTRACT_ASSIGNMENT_MISSING",
        f"notebook contract assignment missing: {name}",
        NOTEBOOK_PATH,
    )


def _notebook(repo_root: Path) -> tuple[dict[str, object], str]:
    path = repo_root / NOTEBOOK_PATH
    if _sha256_file(path) != EXPECTED_NOTEBOOK_SHA256:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_IDENTITY_DRIFT",
            "final verifier notebook SHA-256 drifted",
            NOTEBOOK_PATH,
        )
    payload = _read_object(path)
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_STRUCTURE_INVALID",
            "notebook must contain exactly two cells",
            NOTEBOOK_PATH,
        )
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_STRUCTURE_INVALID",
            "notebook code cell is invalid",
            NOTEBOOK_PATH,
        )
    source = code_cell.get("source")
    if not isinstance(source, list) or not all(isinstance(value, str) for value in source):
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_SOURCE_INVALID",
            "notebook code source is invalid",
            NOTEBOOK_PATH,
        )
    if code_cell.get("execution_count") is not None or code_cell.get("outputs") != []:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_MUST_BE_UNEXECUTED",
            "repository notebook must remain unexecuted",
            NOTEBOOK_PATH,
        )
    return payload, "".join(source)


def validate_notebook(repo_root: Path) -> None:
    payload, code = _notebook(repo_root)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_METADATA_INVALID",
            "notebook metadata is missing",
            NOTEBOOK_PATH,
        )
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_METADATA_INVALID",
            "AuraGateway notebook metadata is missing",
            NOTEBOOK_PATH,
        )
    expected_metadata = {
        "notebook_name": "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4",
        "requested_kaggle_title": "ag-preflight-v3-final-offline-verifier-v4",
        "accelerator": "T4 x2",
        "internet_required": False,
        "dependency_resolution_permitted": False,
        "model_loads_permitted": 0,
        "worker_startups_permitted": 0,
        "model_requests_permitted": 0,
        "benchmark_trajectories_permitted": 0,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "execution_authorization_issued": False,
        "next_expensive_execution_permitted": False,
        "required_native_module": "vllm._C_stable_libtorch",
        "controlled_python_startup_required": True,
        "native_loader_provenance_required": True,
        "successful_native_import_alone_sufficient": False,
        "predecessor_v3_saved_version_id": 341197546,
        "predecessor_v3_terminal_status": "FAILED_PENDING_REVIEW",
        "predecessor_v3_failure_class": "DIAGNOSTIC_HARNESS_DEFECT",
        "predecessor_v3_failure_code": ("BACKPROJECTED_UPSTREAM_RECEIPT_SEMANTIC_REQUIREMENT"),
        "producer_consumer_contract_separated": True,
        "historical_receipt_backprojection_permitted": False,
    }
    for key, expected in expected_metadata.items():
        if auragateway.get(key) != expected:
            _raise(
                "PREFLIGHT_V3_FINAL_VERIFIER_NOTEBOOK_METADATA_DRIFT",
                f"notebook metadata drifted: {key}",
                NOTEBOOK_PATH,
            )

    producer_contract = _literal_assignment(code, "PRODUCER_RECEIPT_EXPECTED")
    if producer_contract != MATERIALIZER_PRODUCER_RECEIPT_EXPECTED:
        _raise(
            "PREFLIGHT_V3_V4_NOTEBOOK_PRODUCER_CONTRACT_DRIFT",
            "notebook producer receipt contract drifted",
            NOTEBOOK_PATH,
        )
    consumer_policy = _literal_assignment(code, "CONSUMER_CAPABILITY_POLICY")
    if consumer_policy != VERIFIER_CONSUMER_CAPABILITY_POLICY:
        _raise(
            "PREFLIGHT_V3_V4_NOTEBOOK_CONSUMER_POLICY_DRIFT",
            "notebook consumer capability policy drifted",
            NOTEBOOK_PATH,
        )

    required_snippets = (
        'REQUIRED_NATIVE_MODULE = "vllm._C_stable_libtorch"',
        'sys.modules["sitecustomize"] = sentinel("sitecustomize")',
        'sys.modules["usercustomize"] = sentinel("usercustomize")',
        "site.main()",
        'environment.pop("PYTHONPATH", None)',
        'environment.pop("PYTHONHOME", None)',
        'environment.pop("LD_PRELOAD", None)',
        '"PYTHONNOUSERSITE": "1"',
        'REAL_DRIVER_DIRECTORY = Path("/usr/local/nvidia/lib64")',
        '"/usr/local/cuda/lib64/stubs"',
        '"/usr/local/cuda/compat"',
        '["ldd", str(native_path)]',
        'Path("/proc/self/maps")',
        'importlib.import_module("vllm._C_stable_libtorch")',
        "CudaPlatform.import_kernels()",
        '"native_runtime_provenance"',
        '"cuda_platform_capability"',
        '"--no-index"',
        '"--no-deps"',
        '"--require-hashes"',
        "for key, expected_value in PRODUCER_RECEIPT_EXPECTED.items():",
        "if CONSUMER_CAPABILITY_POLICY != {",
        '"controlled_python_startup_required": True',
        '"native_loader_provenance_required": True',
        '"successful_native_import_alone_sufficient": False',
    )
    missing = tuple(snippet for snippet in required_snippets if snippet not in code)
    if missing:
        raise VerifierImplementationError(
            "PREFLIGHT_V3_FINAL_VERIFIER_REQUIRED_CONTROL_MISSING",
            "final verifier notebook is missing required controls",
            NOTEBOOK_PATH.as_posix(),
            missing,
        )

    for role in REQUIRED_CAPABILITY_ROLES:
        if f'"{role}"' not in code:
            _raise(
                "PREFLIGHT_V3_FINAL_VERIFIER_REQUIRED_ROLE_MISSING",
                f"required verifier role missing: {role}",
                NOTEBOOK_PATH,
            )

    prohibited_snippets = (
        "importlib.import_module('vllm._C')",
        'importlib.import_module("vllm._C")',
        "vllm.LLM(",
        "from vllm import LLM",
        "AsyncLLMEngine",
        "EngineArgs(",
        ".generate(",
        "requests.post(",
        "http://",
        "https://",
    )
    found = tuple(snippet for snippet in prohibited_snippets if snippet in code)
    if found:
        raise VerifierImplementationError(
            "PREFLIGHT_V3_FINAL_VERIFIER_PROHIBITED_BEHAVIOR_PRESENT",
            "final verifier contains prohibited behavior",
            NOTEBOOK_PATH.as_posix(),
            found,
        )

    compile(code, NOTEBOOK_PATH.as_posix(), "exec")


def _capability_contract() -> CapabilityContract:
    return CapabilityContract(
        current_boundary="P0_FINAL_RUNTIME_OFFLINE_VERIFIER_V4_IMPLEMENTATION",
        exact_runtime_python="3.12",
        exact_runtime_torch="2.11.0+cu129",
        exact_runtime_torch_cuda="12.9",
        exact_runtime_transformers="5.14.1",
        exact_runtime_triton="3.6.0",
        exact_runtime_vllm_distribution="0.25.1+cu129",
        exact_runtime_vllm_module_semantic_version="0.25.1",
        required_cuda_native_module="vllm._C_stable_libtorch",
        required_capability_roles=REQUIRED_CAPABILITY_ROLES,
        python_startup_policy="NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        python_environment_policy="DROP_PYTHONPATH_AND_PYTHONHOME_SET_PYTHONNOUSERSITE",
        sitecustomize_policy="CONTROLLED_SENTINEL_BEFORE_SITE_MAIN",
        usercustomize_policy="CONTROLLED_SENTINEL_BEFORE_SITE_MAIN",
        canonical_loader_policy="TARGET_RUNTIME_LIBRARIES_BEFORE_FILTERED_AMBIENT",
        static_linker_provenance_required=True,
        dynamic_loader_provenance_required=True,
        real_driver_directory="/usr/local/nvidia/lib64",
        cuda_stub_and_compat_paths_permitted=False,
        unapproved_ambient_python_native_libraries_permitted=False,
        successful_native_import_alone_sufficient=False,
        model_loads_permitted=0,
        worker_startups_permitted=0,
        model_requests_permitted=0,
        benchmark_trajectories_permitted=0,
    )


def build_review(repo_root: Path) -> ImplementationReview:
    _require_authorities(repo_root)
    _validate_historical_materialization_receipt(repo_root)
    validate_notebook(repo_root)
    return ImplementationReview(
        review_id=(
            "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-implementation-review"
        ),
        status="APPROVED_FOR_REPOSITORY_IMPLEMENTATION_ACCEPTANCE",
        implementation_base_main_commit=IMPLEMENTATION_BASE_MAIN_COMMIT,
        reconciliation_record=_identity(repo_root, RECONCILIATION_RECORD_PATH),
        reconciliation_review=_identity(repo_root, RECONCILIATION_REVIEW_PATH),
        predecessor_v3_diagnostic=_predecessor_v3_diagnostic(),
        producer_consumer_contract=_producer_consumer_contract(),
        materialization_receipt=_identity(repo_root, MATERIALIZATION_RECEIPT_PATH),
        capability_contract=_capability_contract(),
        notebook=_identity(repo_root, NOTEBOOK_PATH),
        source=_identity(repo_root, SOURCE_PATH),
        tests=_identity(repo_root, TEST_PATH),
        adr=_identity(repo_root, ADR_PATH),
        report=_identity(repo_root, REPORT_PATH),
        runbook=_identity(repo_root, RUNBOOK_PATH),
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_expensive_execution_permitted=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "exact_runtime_offline_compatibility_not_yet_verified",
            "verifier_v4_not_yet_executed",
            "v3_saved_version_341197546_preserved_as_diagnostic_failure",
            "v3_runtime_incompatibility_not_established",
            "exact_runtime_p5_p6_not_requalified",
            "model_not_loaded",
            "worker_not_started",
            "model_request_not_sent",
            "variance_pilot_not_authorized",
            "measured_abc_not_authorized",
            "production_readiness_not_claimed",
        ),
    )


def build_record(repo_root: Path, review_sha256: str) -> ImplementationRecord:
    return ImplementationRecord(
        record_id=(
            "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-implementation-record"
        ),
        status="PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V4_IMPLEMENTATION_VALID",
        implementation_base_main_commit=IMPLEMENTATION_BASE_MAIN_COMMIT,
        review=ArtifactIdentity(
            path=REVIEW_PATH.as_posix(),
            sha256=review_sha256,
            size_bytes=(repo_root / REVIEW_PATH).stat().st_size,
        ),
        notebook=_identity(repo_root, NOTEBOOK_PATH),
        source=_identity(repo_root, SOURCE_PATH),
        tests=_identity(repo_root, TEST_PATH),
        adr=_identity(repo_root, ADR_PATH),
        report=_identity(repo_root, REPORT_PATH),
        runbook=_identity(repo_root, RUNBOOK_PATH),
        reconciliation_record_sha256=RECONCILIATION_RECORD_SHA256,
        reconciliation_review_sha256=RECONCILIATION_REVIEW_SHA256,
        predecessor_v3_diagnostic=_predecessor_v3_diagnostic(),
        producer_consumer_contract=_producer_consumer_contract(),
        materialization_receipt=_identity(repo_root, MATERIALIZATION_RECEIPT_PATH),
        required_cuda_native_module="vllm._C_stable_libtorch",
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_expensive_execution_permitted=False,
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> dict[str, object]:
    review = build_review(repo_root)
    review_bytes = _canonical_json_bytes(review.model_dump(mode="json"))
    review_path = repo_root / REVIEW_PATH
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_bytes(review_bytes)

    record = build_record(repo_root, _sha256_bytes(review_bytes))
    record_bytes = _canonical_json_bytes(record.model_dump(mode="json"))
    record_path = repo_root / RECORD_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)
    return {
        "review_sha256": _sha256_bytes(review_bytes),
        "record_sha256": _sha256_bytes(record_bytes),
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "next_expensive_execution_permitted": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> tuple[str, str]:
    expected_review = build_review(repo_root)
    expected_review_bytes = _canonical_json_bytes(expected_review.model_dump(mode="json"))
    review_path = repo_root / REVIEW_PATH
    if review_path.read_bytes() != expected_review_bytes:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_GENERATED_REVIEW_DRIFT",
            "generated implementation review is not canonical",
            REVIEW_PATH,
        )
    review_sha = _sha256_bytes(expected_review_bytes)

    expected_record = build_record(repo_root, review_sha)
    expected_record_bytes = _canonical_json_bytes(expected_record.model_dump(mode="json"))
    record_path = repo_root / RECORD_PATH
    if record_path.read_bytes() != expected_record_bytes:
        _raise(
            "PREFLIGHT_V3_FINAL_VERIFIER_GENERATED_RECORD_DRIFT",
            "generated implementation record is not canonical",
            RECORD_PATH,
        )
    return review_sha, _sha256_bytes(expected_record_bytes)


def validate_preexecution_contract(repo_root: Path) -> dict[str, object]:
    _require_base_main_ancestor(repo_root)
    _require_authorities(repo_root)
    _validate_historical_materialization_receipt(repo_root)
    validate_notebook(repo_root)
    return {
        "status": "PREFLIGHT_V3_V4_PREEXECUTION_CONTRACT_VALID",
        "historical_receipt_sha256": MATERIALIZATION_RECEIPT_SHA256,
        "producer_owned_field_count": len(MATERIALIZER_PRODUCER_RECEIPT_EXPECTED),
        "consumer_owned_field_count": len(VERIFIER_CONSUMER_CAPABILITY_POLICY),
        "historical_receipt_backprojection_permitted": False,
        "runtime_execution_authorized": False,
        "next_expensive_execution_permitted": False,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    _require_base_main_ancestor(repo_root)
    _require_authorities(repo_root)
    _validate_historical_materialization_receipt(repo_root)
    validate_notebook(repo_root)
    review_sha, record_sha = validate_generated(repo_root)
    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V4_IMPLEMENTATION_VALID",
        "implementation_base_main_commit": IMPLEMENTATION_BASE_MAIN_COMMIT,
        "reconciliation_record_sha256": RECONCILIATION_RECORD_SHA256,
        "notebook_sha256": EXPECTED_NOTEBOOK_SHA256,
        "review_sha256": review_sha,
        "record_sha256": record_sha,
        "required_cuda_native_module": "vllm._C_stable_libtorch",
        "predecessor_v3_saved_version_id": PREDECESSOR_V3_SAVED_VERSION_ID,
        "predecessor_v3_failure_class": PREDECESSOR_V3_FAILURE_CLASS,
        "predecessor_v3_failure_code": PREDECESSOR_V3_FAILURE_CODE,
        "historical_receipt_backprojection_permitted": False,
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_expensive_execution_permitted": False,
        "next_gate": NEXT_GATE,
    }


def _print_error(error: VerifierImplementationError) -> None:
    envelope = ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    )
    print(
        _canonical_json_bytes(envelope.model_dump(mode="json")).decode("utf-8"),
        file=sys.stderr,
        end="",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("generate", "validate-implementation", "validate-preexecution-contract"),
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    try:
        if args.command == "generate":
            result = generate(repo_root)
        elif args.command == "validate-preexecution-contract":
            result = validate_preexecution_contract(repo_root)
        else:
            result = validate_implementation(repo_root)
    except VerifierImplementationError as error:
        _print_error(error)
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
