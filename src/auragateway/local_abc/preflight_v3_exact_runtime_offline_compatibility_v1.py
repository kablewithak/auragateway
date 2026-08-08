"""Validate the preflight-v3 exact-runtime offline verifier implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Final, Literal

from pydantic import field_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "8d65113561374e7ce6a416790251a238c6240ed7"

MATERIALIZATION_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_wheelhouse_materialization_acceptance_v1.json"
)
RESOLUTION_LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v1.ipynb"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-08-local-abc-preflight-v3-exact-runtime-offline-compatibility-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V3_Exact_Runtime_Offline_Compatibility_V1_Implementation.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_exact_runtime_offline_compatibility_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v1_"
    "implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v1_"
    "implementation_record.json"
)

EXPECTED_MATERIALIZATION_ACCEPTANCE_SHA256: Final = (
    "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725"
)
EXPECTED_RESOLUTION_LOCK_SHA256: Final = (
    "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
)
EXPECTED_MATERIALIZER_SCRIPT_VERSION_ID: Final = 341083505
EXPECTED_MATERIALIZER_NOTEBOOK_SHA256: Final = (
    "e227c7926d7c8fd9acbdc3d773ba3dd145494aec6f150485e37af86d801f7c77"
)
EXPECTED_PACKAGE_COUNT: Final = 196
EXPECTED_SHA_MANIFEST_ENTRY_COUNT: Final = 200
EXPECTED_TOTAL_WHEEL_BYTES: Final = 6164913809
EXPECTED_KAGGLE_TITLE: Final = "ag-preflight-v3-runtime-offline-verifier-v1"
NOTEBOOK_NAME: Final = "auragateway-preflight-v3-exact-runtime-offline-compatibility-v1"
NEXT_GATE: Final = "merge_then_execute_preflight_v3_exact_runtime_offline_compatibility_verifier_v1"

REQUIRED_ROLES: Final[tuple[str, ...]] = (
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
    "python_runtime",
    "torch_family_runtime",
    "transformers_runtime",
    "triton_distribution",
    "vllm_distribution",
    "vllm_module",
    "vllm_native_extension",
    "base_distribution_snapshot_after",
)


class ArtifactIdentityV1(LocalABCContract):
    path: str
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact identity must use lowercase SHA-256")
        return value


class ImplementationReviewV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v1-implementation-review"
    ] = "auragateway-preflight-v3-exact-runtime-offline-compatibility-v1-implementation-review"
    implementation_base_main_commit: str = IMPLEMENTATION_BASE_MAIN_COMMIT
    materialization_acceptance: ArtifactIdentityV1
    resolution_lock: ArtifactIdentityV1
    notebook: ArtifactIdentityV1
    source: ArtifactIdentityV1
    tests: ArtifactIdentityV1
    adr: ArtifactIdentityV1
    report: ArtifactIdentityV1
    runbook: ArtifactIdentityV1
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    wheelhouse_materialized: Literal[True] = True
    exact_runtime_materialized: Literal[True] = True
    exact_runtime_offline_verified: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str = NEXT_GATE


class ImplementationRecordV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v1-implementation-record"
    ] = "auragateway-preflight-v3-exact-runtime-offline-compatibility-v1-implementation-record"
    implementation_base_main_commit: str = IMPLEMENTATION_BASE_MAIN_COMMIT
    materialization_acceptance_sha256: str = EXPECTED_MATERIALIZATION_ACCEPTANCE_SHA256
    exact_resolution_lock_sha256: str = EXPECTED_RESOLUTION_LOCK_SHA256
    accepted_materializer_script_version_id: Literal[341083505] = 341083505
    implementation_review_sha256: str
    notebook_sha256: str
    source_sha256: str
    tests_sha256: str
    package_count: Literal[196] = 196
    sha_manifest_entry_count: Literal[200] = 200
    total_wheel_bytes: Literal[6164913809] = 6164913809
    expected_python: Literal["3.12"] = "3.12"
    expected_cuda_variant: Literal["cu129"] = "cu129"
    expected_torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    expected_vllm: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    package_installation_permitted: Literal[True] = True
    dependency_resolution_permitted: Literal[False] = False
    model_loads_permitted: Literal[0] = 0
    worker_startups_permitted: Literal[0] = 0
    model_requests_permitted: Literal[0] = 0
    benchmark_trajectories_permitted: Literal[0] = 0
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    exact_runtime_offline_verified: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str = NEXT_GATE

    @field_validator(
        "materialization_acceptance_sha256",
        "exact_resolution_lock_sha256",
        "implementation_review_sha256",
        "notebook_sha256",
        "source_sha256",
        "tests_sha256",
    )
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation hashes must use lowercase SHA-256")
        return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _identity(repo_root: Path, path: Path) -> ArtifactIdentityV1:
    return ArtifactIdentityV1(
        path=path.as_posix(),
        sha256=_sha256_file(repo_root / path),
    )


def validate_authority(repo_root: Path) -> None:
    acceptance_path = repo_root / MATERIALIZATION_ACCEPTANCE_PATH
    lock_path = repo_root / RESOLUTION_LOCK_PATH

    if _sha256_file(acceptance_path) != EXPECTED_MATERIALIZATION_ACCEPTANCE_SHA256:
        raise ValueError("materialization acceptance SHA-256 drifted")
    if _sha256_file(lock_path) != EXPECTED_RESOLUTION_LOCK_SHA256:
        raise ValueError("frozen resolution lock SHA-256 drifted")

    acceptance = _read_object(acceptance_path)
    expected_acceptance = {
        "decision": "ACCEPT_EXACT_RUNTIME_WHEELHOUSE_MATERIALIZATION_V1",
        "kaggle_script_version_id": EXPECTED_MATERIALIZER_SCRIPT_VERSION_ID,
        "repository_notebook_sha256": EXPECTED_MATERIALIZER_NOTEBOOK_SHA256,
        "wheelhouse_materialized": True,
        "exact_runtime_resolution_lock_frozen": True,
        "exact_runtime_materialized": True,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "variance_pilot_accepted": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, expected_value in expected_acceptance.items():
        if acceptance.get(key) != expected_value:
            raise ValueError(f"materialization authority drifted: {key}")

    checks = acceptance.get("evidence_checks")
    if not isinstance(checks, dict):
        raise ValueError("materialization evidence checks missing")
    expected_checks = {
        "locked_package_count": EXPECTED_PACKAGE_COUNT,
        "downloaded_package_count": EXPECTED_PACKAGE_COUNT,
        "wheel_file_count": EXPECTED_PACKAGE_COUNT,
        "sha256_manifest_entry_count": EXPECTED_SHA_MANIFEST_ENTRY_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "wheel_names_missing_from_frozen_lock": 0,
        "unexpected_wheel_names": 0,
        "wheel_sha_mismatches_against_frozen_lock": 0,
        "dependency_resolution_performed": False,
        "package_installation_performed": False,
        "model_loads_performed": 0,
        "model_requests_performed": 0,
        "benchmark_trajectories_performed": 0,
    }
    for key, expected_value in expected_checks.items():
        if checks.get(key) != expected_value:
            raise ValueError(f"materialization evidence check drifted: {key}")


def _notebook_code(repo_root: Path) -> tuple[dict[str, object], str]:
    payload = _read_object(repo_root / NOTEBOOK_PATH)
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise ValueError("offline verifier notebook must contain two cells")
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        raise ValueError("offline verifier code cell invalid")
    source = code_cell.get("source")
    if not isinstance(source, list) or not all(isinstance(item, str) for item in source):
        raise ValueError("offline verifier code source must be list[str]")
    if code_cell.get("execution_count") is not None or code_cell.get("outputs") != []:
        raise ValueError("repository offline verifier notebook must remain unexecuted")
    return payload, "".join(source)


def validate_notebook(repo_root: Path) -> None:
    payload, code = _notebook_code(repo_root)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("offline verifier notebook metadata missing")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise ValueError("AuraGateway notebook metadata missing")

    expected_metadata = {
        "schema_version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "requested_kaggle_title": EXPECTED_KAGGLE_TITLE,
        "accelerator": "T4 x2",
        "internet_required": False,
        "secrets_permitted": False,
        "accepted_materializer_script_version_id": (EXPECTED_MATERIALIZER_SCRIPT_VERSION_ID),
        "materialization_acceptance_sha256": (EXPECTED_MATERIALIZATION_ACCEPTANCE_SHA256),
        "exact_resolution_lock_sha256": EXPECTED_RESOLUTION_LOCK_SHA256,
        "expected_package_count": EXPECTED_PACKAGE_COUNT,
        "expected_sha_manifest_entry_count": EXPECTED_SHA_MANIFEST_ENTRY_COUNT,
        "expected_total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "package_installation_permitted": True,
        "dependency_resolution_permitted": False,
        "model_loads_permitted": 0,
        "worker_startups_permitted": 0,
        "model_requests_permitted": 0,
        "benchmark_trajectories_permitted": 0,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, expected_value in expected_metadata.items():
        if auragateway.get(key) != expected_value:
            raise ValueError(f"offline verifier metadata drifted: {key}")

    for role in REQUIRED_ROLES:
        if f'"{role}"' not in code:
            raise ValueError(f"offline verifier role missing: {role}")

    required_fragments = (
        "--without-pip",
        "--python",
        "--no-index",
        "--no-cache-dir",
        "--no-deps",
        "--require-hashes",
        "nvidia-smi",
        "torch.cuda.is_available",
        "torch.cuda.device_count",
        "importlib.import_module('vllm._C')",
        "BLOCKED_BY_UPSTREAM_FAILURE",
        "FAILED_PENDING_REVIEW",
        "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
        "PIP_NO_INDEX",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "model_loads_performed",
        "model_requests_performed",
        "worker_startups_performed",
        "benchmark_trajectories_performed",
    )
    missing = [item for item in required_fragments if item not in code]
    if missing:
        raise ValueError(f"offline verifier contract fragments missing: {missing}")

    forbidden_fragments = (
        "urllib.request",
        "requests.get(",
        "http://",
        "https://",
        "vllm.LLM(",
        "AsyncLLMEngine",
        "/v1/chat/completions",
        "huggingface_hub.snapshot_download",
    )
    present = [item for item in forbidden_fragments if item in code]
    if present:
        raise ValueError(f"offline verifier contains prohibited surface: {present}")


def build_review(repo_root: Path) -> ImplementationReviewV1:
    validate_authority(repo_root)
    validate_notebook(repo_root)
    return ImplementationReviewV1(
        materialization_acceptance=_identity(
            repo_root,
            MATERIALIZATION_ACCEPTANCE_PATH,
        ),
        resolution_lock=_identity(repo_root, RESOLUTION_LOCK_PATH),
        notebook=_identity(repo_root, NOTEBOOK_PATH),
        source=_identity(repo_root, SOURCE_PATH),
        tests=_identity(repo_root, TEST_PATH),
        adr=_identity(repo_root, ADR_PATH),
        report=_identity(repo_root, REPORT_PATH),
        runbook=_identity(repo_root, RUNBOOK_PATH),
    )


def build_record(
    repo_root: Path,
    review_sha256: str,
) -> ImplementationRecordV1:
    return ImplementationRecordV1(
        implementation_review_sha256=review_sha256,
        notebook_sha256=_sha256_file(repo_root / NOTEBOOK_PATH),
        source_sha256=_sha256_file(repo_root / SOURCE_PATH),
        tests_sha256=_sha256_file(repo_root / TEST_PATH),
    )


def generate(repo_root: Path) -> dict[str, object]:
    review = build_review(repo_root)
    review_text = review.canonical_json() + "\n"
    (repo_root / REVIEW_PATH).write_text(
        review_text,
        encoding="utf-8",
        newline="\n",
    )
    review_sha = _sha256_bytes(review_text.encode("utf-8"))

    record = build_record(repo_root, review_sha)
    record_text = record.canonical_json() + "\n"
    (repo_root / RECORD_PATH).write_text(
        record_text,
        encoding="utf-8",
        newline="\n",
    )

    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V1_GENERATED",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "review_sha256": review_sha,
        "record_sha256": _sha256_bytes(record_text.encode("utf-8")),
        "wheelhouse_materialized": True,
        "exact_runtime_materialized": True,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> tuple[str, str]:
    expected_review = build_review(repo_root)
    review_text = expected_review.canonical_json() + "\n"
    review_path = repo_root / REVIEW_PATH
    if not review_path.is_file():
        raise ValueError("offline verifier implementation review missing")
    if review_path.read_text(encoding="utf-8") != review_text:
        raise ValueError("offline verifier implementation review stale")
    review_sha = _sha256_bytes(review_text.encode("utf-8"))

    expected_record = build_record(repo_root, review_sha)
    record_text = expected_record.canonical_json() + "\n"
    record_path = repo_root / RECORD_PATH
    if not record_path.is_file():
        raise ValueError("offline verifier implementation record missing")
    if record_path.read_text(encoding="utf-8") != record_text:
        raise ValueError("offline verifier implementation record stale")

    return review_sha, _sha256_bytes(record_text.encode("utf-8"))


def validate_implementation(repo_root: Path) -> dict[str, object]:
    validate_authority(repo_root)
    validate_notebook(repo_root)
    review_sha, record_sha = validate_generated(repo_root)
    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V1_VALID",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "notebook_sha256": _sha256_file(repo_root / NOTEBOOK_PATH),
        "review_sha256": review_sha,
        "record_sha256": record_sha,
        "package_count": EXPECTED_PACKAGE_COUNT,
        "sha_manifest_entry_count": EXPECTED_SHA_MANIFEST_ENTRY_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "accepted_materializer_script_version_id": (EXPECTED_MATERIALIZER_SCRIPT_VERSION_ID),
        "wheelhouse_materialized": True,
        "exact_runtime_materialized": True,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("generate", "validate-implementation"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    if args.command == "generate":
        payload = generate(repo_root)
    else:
        payload = validate_implementation(repo_root)

    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
