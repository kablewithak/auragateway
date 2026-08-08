"""Validate and freeze the preflight-v3 exact-runtime wheelhouse materializer implementation."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import re
import subprocess
import zlib
from pathlib import Path
from typing import Final, Literal

from pydantic import field_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "250cf837408858d5d6354c5ed7ac5f9f1db9cd73"

LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_acceptance_v1.json"
)
NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_wheelhouse_materialization_v1.ipynb"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_wheelhouse_materialization_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_wheelhouse_materialization_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V3_Exact_Runtime_Wheelhouse_Materializer_V1_Implementation.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_exact_runtime_wheelhouse_materialization_v1.md"
)
HANDOFF_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_exact_runtime_resolution_lock_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_wheelhouse_materializer_v1_implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_wheelhouse_materializer_v1_implementation_record.json"
)

EXPECTED_LOCK_SHA256: Final = "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
EXPECTED_ACCEPTANCE_SHA256: Final = (
    "0e0ee6174f70d6a8b8be84e6524d946234b0649156e7089c3621577f73ebc96d"
)
EXPECTED_PACKAGE_COUNT: Final = 196
EXPECTED_AUTHORITY_HOST_COUNT: Final = 5
EXPECTED_VLLM: Final = "0.25.1+cu129"
EXPECTED_VLLM_SHA256: Final = "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
EXPECTED_TORCH: Final = "2.11.0+cu129"
REQUESTED_KAGGLE_TITLE: Final = "ag-preflight-v3-runtime-materializer-v1"
NOTEBOOK_NAME: Final = "auragateway-preflight-v3-exact-runtime-wheelhouse-materialization-v1"
NEXT_GATE: Final = "merge_then_execute_preflight_v3_exact_runtime_wheelhouse_materializer_v1"

ALLOWED_GITHUB_TRANSPORT_REDIRECT: Final = (
    "github.com",
    "release-assets.githubusercontent.com",
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
        "auragateway-preflight-v3-exact-runtime-wheelhouse-materializer-v1-implementation-review"
    ] = "auragateway-preflight-v3-exact-runtime-wheelhouse-materializer-v1-implementation-review"
    implementation_base_main_commit: str = IMPLEMENTATION_BASE_MAIN_COMMIT
    lock: ArtifactIdentityV1
    acceptance: ArtifactIdentityV1
    notebook: ArtifactIdentityV1
    source: ArtifactIdentityV1
    tests: ArtifactIdentityV1
    report: ArtifactIdentityV1
    runbook: ArtifactIdentityV1
    handoff_runbook: ArtifactIdentityV1
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    exact_runtime_resolution_lock_frozen: Literal[True] = True
    exact_runtime_materialized: Literal[False] = False
    exact_runtime_offline_verified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str = NEXT_GATE


class ImplementationRecordV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-preflight-v3-exact-runtime-wheelhouse-materializer-v1-implementation-record"
    ] = "auragateway-preflight-v3-exact-runtime-wheelhouse-materializer-v1-implementation-record"
    implementation_base_main_commit: str = IMPLEMENTATION_BASE_MAIN_COMMIT
    exact_resolution_lock_sha256: str = EXPECTED_LOCK_SHA256
    acceptance_sha256: str = EXPECTED_ACCEPTANCE_SHA256
    implementation_review_sha256: str
    notebook_sha256: str
    source_sha256: str
    tests_sha256: str
    package_count: Literal[196] = 196
    authority_host_count: Literal[5] = 5
    transport_redirect_source_host: Literal["github.com"] = "github.com"
    transport_redirect_destination_host: Literal["release-assets.githubusercontent.com"] = (
        "release-assets.githubusercontent.com"
    )
    dependency_resolution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_loads_permitted: Literal[0] = 0
    model_requests_permitted: Literal[0] = 0
    benchmark_trajectories_permitted: Literal[0] = 0
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    exact_runtime_resolution_lock_frozen: Literal[True] = True
    exact_runtime_materialized: Literal[False] = False
    exact_runtime_offline_verified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str = NEXT_GATE

    @field_validator(
        "exact_resolution_lock_sha256",
        "acceptance_sha256",
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


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _read_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_blob_sha(repo_root: Path, path: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path.as_posix()}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise ValueError(f"could not resolve committed blob: {path}")
    return completed.stdout.strip()


def validate_authority(repo_root: Path) -> None:
    lock_path = repo_root / LOCK_PATH
    acceptance_path = repo_root / ACCEPTANCE_PATH

    if _sha256_file(lock_path) != EXPECTED_LOCK_SHA256:
        raise ValueError("frozen exact-runtime lock SHA-256 drifted")
    if _sha256_file(acceptance_path) != EXPECTED_ACCEPTANCE_SHA256:
        raise ValueError("resolution acceptance SHA-256 drifted")

    lock = _read_object(lock_path)
    acceptance = _read_object(acceptance_path)

    if lock.get("package_count") != EXPECTED_PACKAGE_COUNT:
        raise ValueError("frozen package count drifted")
    if lock.get("host_count") != EXPECTED_AUTHORITY_HOST_COUNT:
        raise ValueError("frozen authority-host count drifted")
    if lock.get("freeze_decision") != (
        "ACCEPT_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_AND_FREEZE_LOCK"
    ):
        raise ValueError("frozen lock decision drifted")
    if acceptance.get("exact_runtime_resolution_lock_frozen") is not True:
        raise ValueError("resolution acceptance no longer freezes the exact lock")
    if acceptance.get("exact_runtime_materialized") is not False:
        raise ValueError("accepted authority already claims materialization")

    runtime = lock.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("frozen runtime identity missing")
    if runtime.get("vllm_distribution_version") != EXPECTED_VLLM:
        raise ValueError("frozen vLLM identity drifted")
    if runtime.get("vllm_wheel_sha256") != EXPECTED_VLLM_SHA256:
        raise ValueError("frozen vLLM SHA-256 drifted")
    if runtime.get("torch_version") != EXPECTED_TORCH:
        raise ValueError("frozen torch identity drifted")

    records = lock.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_PACKAGE_COUNT:
        raise ValueError("frozen exact record set drifted")

    for payload in (lock, acceptance):
        if payload.get("runtime_execution_authorized") is not False:
            raise ValueError("runtime execution unexpectedly authorized")
        if payload.get("pilot_execution_authorized") is not False:
            raise ValueError("pilot execution unexpectedly authorized")
        if payload.get("final_measured_abc_execution_authorized") is not False:
            raise ValueError("final measured A/B/C unexpectedly authorized")


def _notebook_code(repo_root: Path) -> tuple[dict[str, object], str]:
    payload = _read_object(repo_root / NOTEBOOK_PATH)
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise ValueError("materializer notebook must contain exactly two cells")
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        raise ValueError("materializer code cell invalid")
    source = code_cell.get("source")
    if not isinstance(source, list) or not all(isinstance(item, str) for item in source):
        raise ValueError("materializer code source must be list[str]")
    if code_cell.get("execution_count") is not None or code_cell.get("outputs") != []:
        raise ValueError("repository materializer notebook must remain unexecuted")
    return payload, "".join(source)


def _extract_embedded_lock(code: str) -> bytes:
    tree = ast.parse(code)
    encoded: str | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "RESOLUTION_LOCK_ZLIB_B64"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, str):
            raise ValueError("embedded resolution lock must be a string")
        encoded = value
        break

    if encoded is None:
        raise ValueError("embedded resolution lock constant missing")

    return zlib.decompress(base64.b64decode(encoded.encode("ascii")))


def validate_notebook(repo_root: Path) -> None:
    payload, code = _notebook_code(repo_root)

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("notebook metadata missing")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise ValueError("AuraGateway notebook metadata missing")

    expected = {
        "schema_version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "requested_kaggle_title": REQUESTED_KAGGLE_TITLE,
        "accelerator": "none",
        "internet_required": True,
        "inputs_permitted": False,
        "credentials_permitted": False,
        "dependency_resolution_permitted": False,
        "package_installation_permitted": False,
        "model_loads_permitted": 0,
        "model_requests_permitted": 0,
        "benchmark_trajectories_permitted": 0,
        "exact_resolution_lock_sha256": EXPECTED_LOCK_SHA256,
        "expected_package_count": EXPECTED_PACKAGE_COUNT,
        "expected_authority_host_count": EXPECTED_AUTHORITY_HOST_COUNT,
    }
    for key, value in expected.items():
        if auragateway.get(key) != value:
            raise ValueError(f"notebook metadata drifted: {key}")

    embedded = _extract_embedded_lock(code)
    if embedded != (repo_root / LOCK_PATH).read_bytes():
        raise ValueError("embedded resolution lock bytes differ from frozen repository lock")
    if _sha256_bytes(embedded) != EXPECTED_LOCK_SHA256:
        raise ValueError("embedded resolution lock SHA-256 drifted")

    required_fragments = (
        "PolicyRedirectHandler",
        "release-assets.githubusercontent.com",
        "MAX_REDIRECTS_PER_ARTIFACT = 1",
        "dependency_resolution_performed",
        '"dependency_resolution_performed": False',
        '"package_installation_performed": False',
        '"model_loads_performed": 0',
        '"model_requests_performed": 0',
        '"benchmark_trajectories_performed": 0',
        "DOWNLOAD_SHA256_MISMATCH",
        "DOWNLOAD_HOST_DRIFT",
        "REDIRECT_POLICY_VIOLATION",
        "WHEEL_SET_DRIFT",
        "sha256_manifest.json",
        "materialization_receipt.json",
        "materialization_evidence.zip",
        "requirements.lock.txt",
        "resolution_lock.json",
        "runtime_manifest.json",
    )
    missing = [item for item in required_fragments if item not in code]
    if missing:
        raise ValueError(f"materializer contract fragments missing: {missing}")

    forbidden = (
        "pip install",
        "pip download",
        "--dry-run",
        "torch.cuda",
        "vllm.LLM",
        "AsyncLLMEngine",
        "/v1/chat/completions",
    )
    present = [item for item in forbidden if item in code]
    if present:
        raise ValueError(f"materializer contains prohibited surface: {present}")


def _identity(repo_root: Path, path: Path) -> ArtifactIdentityV1:
    return ArtifactIdentityV1(
        path=path.as_posix(),
        sha256=_sha256_file(repo_root / path),
    )


def build_review(repo_root: Path) -> ImplementationReviewV1:
    validate_authority(repo_root)
    validate_notebook(repo_root)
    return ImplementationReviewV1(
        lock=_identity(repo_root, LOCK_PATH),
        acceptance=_identity(repo_root, ACCEPTANCE_PATH),
        notebook=_identity(repo_root, NOTEBOOK_PATH),
        source=_identity(repo_root, SOURCE_PATH),
        tests=_identity(repo_root, TEST_PATH),
        report=_identity(repo_root, REPORT_PATH),
        runbook=_identity(repo_root, RUNBOOK_PATH),
        handoff_runbook=_identity(repo_root, HANDOFF_RUNBOOK_PATH),
    )


def build_record(repo_root: Path, review_sha256: str) -> ImplementationRecordV1:
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
    review_sha256 = _sha256_bytes(review_text.encode("utf-8"))

    record = build_record(repo_root, review_sha256)
    record_text = record.canonical_json() + "\n"
    (repo_root / RECORD_PATH).write_text(
        record_text,
        encoding="utf-8",
        newline="\n",
    )

    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_WHEELHOUSE_MATERIALIZER_V1_GENERATED",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "review_sha256": review_sha256,
        "record_sha256": _sha256_bytes(record_text.encode("utf-8")),
        "exact_runtime_resolution_lock_frozen": True,
        "exact_runtime_materialized": False,
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> tuple[str, str]:
    expected_review = build_review(repo_root)
    review_text = expected_review.canonical_json() + "\n"
    review_path = repo_root / REVIEW_PATH
    if not review_path.is_file() or review_path.read_text(encoding="utf-8") != review_text:
        raise ValueError("implementation review is stale or nondeterministic")
    review_sha = _sha256_bytes(review_text.encode("utf-8"))

    expected_record = build_record(repo_root, review_sha)
    record_text = expected_record.canonical_json() + "\n"
    record_path = repo_root / RECORD_PATH
    if not record_path.is_file() or record_path.read_text(encoding="utf-8") != record_text:
        raise ValueError("implementation record is stale or nondeterministic")

    return review_sha, _sha256_bytes(record_text.encode("utf-8"))


def validate_implementation(repo_root: Path) -> dict[str, object]:
    validate_authority(repo_root)
    validate_notebook(repo_root)
    review_sha, record_sha = validate_generated(repo_root)
    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_WHEELHOUSE_MATERIALIZER_V1_VALID",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "notebook_name": NOTEBOOK_NAME,
        "requested_kaggle_title": REQUESTED_KAGGLE_TITLE,
        "notebook_sha256": _sha256_file(repo_root / NOTEBOOK_PATH),
        "review_sha256": review_sha,
        "record_sha256": record_sha,
        "package_count": EXPECTED_PACKAGE_COUNT,
        "authority_host_count": EXPECTED_AUTHORITY_HOST_COUNT,
        "github_release_transport_redirect_host": (ALLOWED_GITHUB_TRANSPORT_REDIRECT[1]),
        "exact_runtime_resolution_lock_frozen": True,
        "exact_runtime_materialized": False,
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate-implementation"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    if args.command == "generate":
        payload = generate(repo_root)
    else:
        payload = validate_implementation(repo_root)

    print(_canonical_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
