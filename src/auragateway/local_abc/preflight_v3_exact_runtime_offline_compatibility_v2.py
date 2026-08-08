"""Validate V1 false-negative acceptance and V2 offline verifier implementation."""

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

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "922b17e006ac05b3ac00d7253c7dd450c1ddc766"

V1_FALSE_NEGATIVE_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v1_"
    "false_negative_acceptance.json"
)
V2_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v2.ipynb"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v2.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v2.py"
)
ADR_PATH: Final = Path(
    "docs/adr/"
    "2026-08-08-local-abc-preflight-v3-exact-runtime-offline-compatibility-"
    "v1-false-negative-v2-remediation.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/"
    "AuraGateway_Preflight_V3_Exact_Runtime_Offline_Compatibility_V1_"
    "False_Negative_V2_Remediation.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_exact_runtime_offline_compatibility_v2.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v2_"
    "implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v2_"
    "implementation_record.json"
)

EXPECTED_V1_ACCEPTANCE_SHA256: Final = (
    "86d679eb4cf76debb7afbecdc4573c10d1884fe343b424327b4477e9d5a1b27b"
)
EXPECTED_V1_SCRIPT_VERSION_ID: Final = 341091805
EXPECTED_V1_REPOSITORY_NOTEBOOK_SHA256: Final = (
    "8ab387aa99dffc772f847d22e3fed066d5a01018f28b12553403f9f59d1253a4"
)
EXPECTED_V1_EXECUTED_NOTEBOOK_SHA256: Final = (
    "a7ce05e0ab4d886592ca96d45b38cb2bfc0e6d13ff05b8a9e85741b91dfd87f1"
)
EXPECTED_V1_MARKDOWN_SOURCE_SHA256: Final = (
    "be15a7975d471e689ce3d977cf63a9b158089b4eee77b636c093722107a348ce"
)
EXPECTED_V1_CODE_SOURCE_SHA256: Final = (
    "03f48d341beec6584486249f37c5743b6e5a40370997100d94057a9f1c70e9a8"
)
EXPECTED_V1_EVIDENCE_ZIP_SHA256: Final = (
    "9f24b6ec955aa3c3eb21a3010d775237eeb3abc98dddad39483fcff3fb668872"
)
EXPECTED_V1_EXECUTION_LOG_SHA256: Final = (
    "57681697119b9e52568ef137d49f6cbc9bf26d6908bac6786555141e83208f2b"
)
EXPECTED_MATERIALIZATION_ACCEPTANCE_SHA256: Final = (
    "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725"
)
EXPECTED_RESOLUTION_LOCK_SHA256: Final = (
    "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
)
EXPECTED_V2_KAGGLE_TITLE: Final = "ag-preflight-v3-runtime-offline-verifier-v2"
EXPECTED_VLLM_DISTRIBUTION_VERSION: Final = "0.25.1+cu129"
EXPECTED_VLLM_MODULE_VERSION: Final = "0.25.1"
NEXT_GATE: Final = "merge_then_execute_preflight_v3_exact_runtime_offline_compatibility_v2"

EXPECTED_EVIDENCE_MEMBER_HASHES: Final[dict[str, str]] = {
    "evidence_manifest.json": ("24904a6eee7df2c98cbb940d47ad3b42c2acd252d1fd9cad3a3eb1e69d21b7ae"),
    "input_validation.json": ("768bae60b7be07b82c43421dda732436ece585826f3b6fc00b13fb5c9fefce60"),
    "probe_records.json": ("5d8a7307c441a2357b88d14b459daf5b71a333e82fd7a75dbcf661b293b38414"),
    "verification_summary.json": (
        "81a90d03ae414dc89e723fb64335b3e6966868538ce36da5512bb655c069e135"
    ),
}
EXPECTED_EVIDENCE_MEMBER_SIZES: Final[dict[str, int]] = {
    "evidence_manifest.json": 438,
    "input_validation.json": 1252,
    "probe_records.json": 26262,
    "verification_summary.json": 1733,
}


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
    review_id: str = (
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v2-implementation-review"
    )
    implementation_base_main_commit: str = IMPLEMENTATION_BASE_MAIN_COMMIT
    v1_false_negative_acceptance: ArtifactIdentityV1
    notebook: ArtifactIdentityV1
    source: ArtifactIdentityV1
    tests: ArtifactIdentityV1
    adr: ArtifactIdentityV1
    report: ArtifactIdentityV1
    runbook: ArtifactIdentityV1
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    exact_runtime_offline_verified: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str = NEXT_GATE


class ImplementationRecordV1(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: str = (
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v2-implementation-record"
    )
    implementation_base_main_commit: str = IMPLEMENTATION_BASE_MAIN_COMMIT
    v1_false_negative_acceptance_sha256: str = EXPECTED_V1_ACCEPTANCE_SHA256
    v1_script_version_id: Literal[341091805] = 341091805
    implementation_review_sha256: str
    notebook_sha256: str
    source_sha256: str
    tests_sha256: str
    vllm_distribution_version: Literal["0.25.1+cu129"] = EXPECTED_VLLM_DISTRIBUTION_VERSION
    vllm_module_semantic_version: Literal["0.25.1"] = EXPECTED_VLLM_MODULE_VERSION
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    exact_runtime_offline_verified: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str = NEXT_GATE

    @field_validator(
        "v1_false_negative_acceptance_sha256",
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


def validate_v1_acceptance(repo_root: Path) -> None:
    path = repo_root / V1_FALSE_NEGATIVE_ACCEPTANCE_PATH
    if _sha256_file(path) != EXPECTED_V1_ACCEPTANCE_SHA256:
        raise ValueError("V1 false-negative acceptance SHA-256 drifted")

    payload = _read_object(path)
    expected = {
        "decision": "ACCEPT_VERIFIER_V1_FALSE_NEGATIVE_AND_REMEDIATE_V2",
        "source_main_merge_commit": IMPLEMENTATION_BASE_MAIN_COMMIT,
        "kaggle_script_version_id": EXPECTED_V1_SCRIPT_VERSION_ID,
        "repository_notebook_sha256": EXPECTED_V1_REPOSITORY_NOTEBOOK_SHA256,
        "executed_notebook_sha256": EXPECTED_V1_EXECUTED_NOTEBOOK_SHA256,
        "markdown_cell_source_sha256": EXPECTED_V1_MARKDOWN_SOURCE_SHA256,
        "code_cell_source_sha256": EXPECTED_V1_CODE_SOURCE_SHA256,
        "evidence_zip_sha256": EXPECTED_V1_EVIDENCE_ZIP_SHA256,
        "execution_log_sha256": EXPECTED_V1_EXECUTION_LOG_SHA256,
        "materialization_acceptance_sha256": (EXPECTED_MATERIALIZATION_ACCEPTANCE_SHA256),
        "exact_resolution_lock_sha256": EXPECTED_RESOLUTION_LOCK_SHA256,
        "executed_markdown_source_matches_repository": True,
        "executed_code_source_matches_repository": True,
        "auragateway_metadata_matches_repository": True,
        "offline_install_succeeded": True,
        "vllm_distribution_identity_succeeded": True,
        "vllm_python_import_succeeded": True,
        "vllm_native_extension_verified": False,
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise ValueError(f"V1 acceptance identity drifted: {key}")

    divergence = payload.get("first_divergence")
    if not isinstance(divergence, dict):
        raise ValueError("V1 first-divergence record missing")
    expected_divergence = {
        "role": "vllm_module",
        "classification": "VERIFIER_FALSE_NEGATIVE_VERSION_IDENTITY_COMPARATOR",
        "subprocess_returncode": 0,
        "observed_distribution_version": EXPECTED_VLLM_DISTRIBUTION_VERSION,
        "observed_module_version": EXPECTED_VLLM_MODULE_VERSION,
        "vllm_python_import_succeeded": True,
        "vllm_native_extension_status": "BLOCKED_BY_UPSTREAM_FAILURE",
        "root_cause_status": "ESTABLISHED",
    }
    for key, expected_value in expected_divergence.items():
        if divergence.get(key) != expected_value:
            raise ValueError(f"V1 divergence evidence drifted: {key}")

    members = payload.get("queryable_evidence_members")
    if not isinstance(members, dict):
        raise ValueError("V1 queryable evidence identities missing")
    if set(members) != set(EXPECTED_EVIDENCE_MEMBER_HASHES):
        raise ValueError("V1 queryable evidence member set drifted")
    for name, expected_sha in EXPECTED_EVIDENCE_MEMBER_HASHES.items():
        member = members.get(name)
        if not isinstance(member, dict):
            raise ValueError(f"V1 evidence member missing: {name}")
        evidence_path = Path(str(member.get("path")))
        if member.get("sha256") != expected_sha:
            raise ValueError(f"V1 evidence identity drifted: {name}")
        if member.get("size_bytes") != EXPECTED_EVIDENCE_MEMBER_SIZES[name]:
            raise ValueError(f"V1 evidence size drifted: {name}")
        absolute = repo_root / evidence_path
        if _sha256_file(absolute) != expected_sha:
            raise ValueError(f"V1 evidence bytes drifted: {name}")
        if absolute.stat().st_size != EXPECTED_EVIDENCE_MEMBER_SIZES[name]:
            raise ValueError(f"V1 evidence file size drifted: {name}")

    execution_log = payload.get("execution_log")
    if not isinstance(execution_log, dict):
        raise ValueError("V1 execution-log identity missing")
    log_path = repo_root / Path(str(execution_log.get("path")))
    if execution_log.get("sha256") != EXPECTED_V1_EXECUTION_LOG_SHA256:
        raise ValueError("V1 execution-log acceptance SHA drifted")
    if execution_log.get("size_bytes") != 3305:
        raise ValueError("V1 execution-log acceptance size drifted")
    if _sha256_file(log_path) != EXPECTED_V1_EXECUTION_LOG_SHA256:
        raise ValueError("V1 execution-log bytes drifted")
    if log_path.stat().st_size != 3305:
        raise ValueError("V1 execution-log file size drifted")

    probe_path = (
        repo_root / "benchmarks/local_abc/evidence/"
        "preflight_v3_exact_runtime_offline_compatibility_v1/"
        "probe_records.json"
    )
    probes = _read_object(probe_path)

    distribution = probes.get("vllm_distribution")
    module = probes.get("vllm_module")
    native = probes.get("vllm_native_extension")
    if not isinstance(distribution, dict):
        raise ValueError("V1 vLLM distribution probe missing")
    if not isinstance(module, dict):
        raise ValueError("V1 vLLM module probe missing")
    if not isinstance(native, dict):
        raise ValueError("V1 vLLM native-extension probe missing")

    if distribution.get("status") != "PASSED":
        raise ValueError("V1 exact vLLM distribution did not pass")
    if str(distribution.get("stdout_excerpt", "")).strip() != ('{"vllm":"0.25.1+cu129"}'):
        raise ValueError("V1 exact vLLM distribution identity drifted")

    if module.get("status") != "FAILED":
        raise ValueError("V1 module harness status no longer matches evidence")
    if module.get("returncode") != 0:
        raise ValueError("V1 vLLM Python import did not return success")
    if str(module.get("stdout_excerpt", "")).strip() != '{"vllm":"0.25.1"}':
        raise ValueError("V1 module semantic version evidence drifted")
    if module.get("detail") != "vLLM module version drifted: '0.25.1'":
        raise ValueError("V1 false-negative comparator evidence drifted")

    if native.get("status") != "BLOCKED_BY_UPSTREAM_FAILURE":
        raise ValueError("V1 native-extension blocked status drifted")
    if native.get("returncode") is not None:
        raise ValueError("V1 native extension unexpectedly executed")


def _notebook_code(repo_root: Path) -> tuple[dict[str, object], str]:
    payload = _read_object(repo_root / V2_NOTEBOOK_PATH)
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise ValueError("V2 notebook must contain exactly two cells")
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        raise ValueError("V2 code cell invalid")
    source = code_cell.get("source")
    if not isinstance(source, list):
        raise ValueError("V2 code source missing")
    if not all(isinstance(item, str) for item in source):
        raise ValueError("V2 code source must contain strings only")
    if code_cell.get("execution_count") is not None:
        raise ValueError("repository V2 notebook must remain unexecuted")
    if code_cell.get("outputs") != []:
        raise ValueError("repository V2 notebook must not contain outputs")
    return payload, "".join(source)


def validate_v2_notebook(repo_root: Path) -> None:
    payload, code = _notebook_code(repo_root)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("V2 notebook metadata missing")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise ValueError("V2 AuraGateway metadata missing")

    expected_metadata = {
        "notebook_name": ("auragateway-preflight-v3-exact-runtime-offline-compatibility-v2"),
        "requested_kaggle_title": EXPECTED_V2_KAGGLE_TITLE,
        "accelerator": "T4 x2",
        "internet_required": False,
        "accepted_materializer_script_version_id": 341083505,
        "v1_false_negative_script_version_id": EXPECTED_V1_SCRIPT_VERSION_ID,
        "v1_false_negative_acceptance_sha256": EXPECTED_V1_ACCEPTANCE_SHA256,
        "vllm_distribution_version": EXPECTED_VLLM_DISTRIBUTION_VERSION,
        "vllm_module_semantic_version": EXPECTED_VLLM_MODULE_VERSION,
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
            raise ValueError(f"V2 notebook metadata drifted: {key}")

    required_fragments = (
        'EXPECTED_VLLM_MODULE_VERSION = "0.25.1"',
        'payload.get("vllm") != EXPECTED_VLLM_MODULE_VERSION',
        '"0.25.1+cu129"',
        "importlib.metadata.version('vllm')",
        "import json,vllm;",
        "importlib.import_module('vllm._C')",
        "BLOCKED_BY_UPSTREAM_FAILURE",
        "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
        "FAILED_PENDING_REVIEW",
        "--no-index",
        "--no-deps",
        "--require-hashes",
    )
    missing = [item for item in required_fragments if item not in code]
    if missing:
        raise ValueError(f"V2 remediation contract fragments missing: {missing}")

    if code.count('payload.get("vllm") != EXPECTED_RUNTIME["vllm"]') != 1:
        raise ValueError("V2 exact vLLM distribution comparator count drifted")

    stale_module_block = (
        'if payload.get("vllm") != EXPECTED_RUNTIME["vllm"]:\\n'
        "                raise ValueError(\\n"
        '                    f"vLLM module version drifted: '
        "{payload.get('vllm')!r}"
    )
    if stale_module_block in code:
        raise ValueError("V2 stale vLLM module comparator remains")

    prohibited = (
        "vllm.LLM(",
        "AsyncLLMEngine",
        "requests.get(",
        "urllib.request",
        "https://",
    )
    present = [item for item in prohibited if item in code]
    if present:
        raise ValueError(f"V2 contains prohibited or stale behavior: {present}")


def build_review(repo_root: Path) -> ImplementationReviewV1:
    validate_v1_acceptance(repo_root)
    validate_v2_notebook(repo_root)
    return ImplementationReviewV1(
        v1_false_negative_acceptance=_identity(
            repo_root,
            V1_FALSE_NEGATIVE_ACCEPTANCE_PATH,
        ),
        notebook=_identity(repo_root, V2_NOTEBOOK_PATH),
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
        notebook_sha256=_sha256_file(repo_root / V2_NOTEBOOK_PATH),
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
    record_sha = _sha256_bytes(record_text.encode("utf-8"))

    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V2_GENERATED",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "v1_false_negative_accepted": True,
        "v1_script_version_id": EXPECTED_V1_SCRIPT_VERSION_ID,
        "review_sha256": review_sha,
        "record_sha256": record_sha,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> tuple[str, str]:
    review = build_review(repo_root)
    review_text = review.canonical_json() + "\n"
    if (repo_root / REVIEW_PATH).read_text(encoding="utf-8") != review_text:
        raise ValueError("V2 implementation review stale")
    review_sha = _sha256_bytes(review_text.encode("utf-8"))

    record = build_record(repo_root, review_sha)
    record_text = record.canonical_json() + "\n"
    if (repo_root / RECORD_PATH).read_text(encoding="utf-8") != record_text:
        raise ValueError("V2 implementation record stale")
    return review_sha, _sha256_bytes(record_text.encode("utf-8"))


def validate_implementation(repo_root: Path) -> dict[str, object]:
    validate_v1_acceptance(repo_root)
    validate_v2_notebook(repo_root)
    review_sha, record_sha = validate_generated(repo_root)
    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V2_VALID",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "v1_false_negative_accepted": True,
        "v1_script_version_id": EXPECTED_V1_SCRIPT_VERSION_ID,
        "v2_notebook_sha256": _sha256_file(repo_root / V2_NOTEBOOK_PATH),
        "review_sha256": review_sha,
        "record_sha256": record_sha,
        "vllm_distribution_version": EXPECTED_VLLM_DISTRIBUTION_VERSION,
        "vllm_module_semantic_version": EXPECTED_VLLM_MODULE_VERSION,
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
