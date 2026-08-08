"""Validate accepted preflight-v3 exact-runtime reconnaissance and frozen lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Final, Self

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_acceptance_v1.json"
)

EXPECTED_SOURCE_MAIN: Final = "cfd53cfa09b1b4dc11b399cee7c2c16397513915"
EXPECTED_LOCK_SHA256: Final = "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
EXPECTED_ACCEPTANCE_SHA256: Final = (
    "0e0ee6174f70d6a8b8be84e6524d946234b0649156e7089c3621577f73ebc96d"
)
EXPECTED_REPOSITORY_NOTEBOOK_SHA256: Final = (
    "d184f9b8ab61554ceed1bd31a384fc2cb50322ca225644dab5a508c52ea0b78b"
)
EXPECTED_EXECUTED_NOTEBOOK_SHA256: Final = (
    "d9bdd69e3766204af47b5b77de0cad854776491d9a8d7be9afab7b85527ac8e6"
)
EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "144661d3bcf908ec3ca98c372b50c01234f98e660762f3ab361ed99ce6c9decd"
)
EXPECTED_EXECUTION_LOG_SHA256: Final = (
    "045e13bc03dbf9966189f385f4c39aaa0daae6e72a49a9bfdc190e4639507672"
)
EXPECTED_CODE_SOURCE_SHA256: Final = (
    "fe9650606705ed851049150ea1b6b528c247a3302b0bee616525fda02173244d"
)
EXPECTED_MARKDOWN_SOURCE_SHA256: Final = (
    "37af9f2618c9f8bced350d045a91e43277935ee92df12168c0f4d4017beab385"
)
EXPECTED_VLLM: Final = "0.25.1+cu129"
EXPECTED_VLLM_SHA256: Final = "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
EXPECTED_TORCH: Final = "2.11.0+cu129"
EXPECTED_PACKAGE_COUNT: Final = 196
EXPECTED_HOST_COUNT: Final = 5
EXPECTED_HOSTS: Final[dict[str, int]] = {
    "download-r2.pytorch.org": 4,
    "download.pytorch.org": 3,
    "files.pythonhosted.org": 158,
    "github.com": 1,
    "pypi.nvidia.com": 30,
}


class LockRecordV1(LocalABCContract):
    normalized_name: str
    version: str
    artifact_filename: str
    hostname: str
    sanitized_url: str
    stable_url_sha256: str
    sha256: str
    source_authority: str

    @field_validator("sha256", "stable_url_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("lock digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if not self.artifact_filename.lower().endswith(".whl"):
            raise ValueError("exact runtime lock may contain wheels only")
        if not self.sanitized_url.startswith("https://"):
            raise ValueError("exact runtime lock URLs must use HTTPS")
        if "?" in self.sanitized_url or "#" in self.sanitized_url:
            raise ValueError("exact runtime lock URLs must not contain query or fragment")
        if "*" in self.hostname:
            raise ValueError("wildcard hosts are prohibited")
        return self


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    lock_path = repo_root / LOCK_PATH
    acceptance_path = repo_root / ACCEPTANCE_PATH

    if _sha256(lock_path) != EXPECTED_LOCK_SHA256:
        raise ValueError("exact runtime resolution lock SHA-256 drifted")
    if _sha256(acceptance_path) != EXPECTED_ACCEPTANCE_SHA256:
        raise ValueError("reconnaissance acceptance SHA-256 drifted")

    lock = _load(lock_path)
    acceptance = _load(acceptance_path)

    if lock.get("source_main_merge_commit") != EXPECTED_SOURCE_MAIN:
        raise ValueError("lock source-main identity drifted")
    if acceptance.get("source_main_merge_commit") != EXPECTED_SOURCE_MAIN:
        raise ValueError("acceptance source-main identity drifted")
    if lock.get("freeze_decision") != (
        "ACCEPT_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_AND_FREEZE_LOCK"
    ):
        raise ValueError("lock freeze decision drifted")
    if acceptance.get("decision") != lock.get("freeze_decision"):
        raise ValueError("acceptance/lock decision mismatch")
    if acceptance.get("exact_resolution_lock_sha256") != EXPECTED_LOCK_SHA256:
        raise ValueError("acceptance does not bind exact lock SHA-256")

    expected_identity = {
        "repository_notebook_sha256": EXPECTED_REPOSITORY_NOTEBOOK_SHA256,
        "executed_notebook_sha256": EXPECTED_EXECUTED_NOTEBOOK_SHA256,
        "markdown_cell_source_sha256": EXPECTED_MARKDOWN_SOURCE_SHA256,
        "code_cell_source_sha256": EXPECTED_CODE_SOURCE_SHA256,
        "evidence_zip_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
        "execution_log_sha256": EXPECTED_EXECUTION_LOG_SHA256,
    }
    for key, expected in expected_identity.items():
        if acceptance.get(key) != expected:
            raise ValueError(f"acceptance evidence identity drifted: {key}")

    if acceptance.get("executed_markdown_source_matches_repository") is not True:
        raise ValueError("executed markdown source identity not accepted")
    if acceptance.get("executed_code_source_matches_repository") is not True:
        raise ValueError("executed code source identity not accepted")

    runtime = lock.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("lock runtime identity missing")
    if runtime.get("vllm_distribution_version") != EXPECTED_VLLM:
        raise ValueError("lock vLLM version drifted")
    if runtime.get("vllm_wheel_sha256") != EXPECTED_VLLM_SHA256:
        raise ValueError("lock vLLM SHA-256 drifted")
    if runtime.get("torch_version") != EXPECTED_TORCH:
        raise ValueError("lock torch version drifted")

    raw_records = lock.get("records")
    if not isinstance(raw_records, list):
        raise ValueError("lock records missing")
    records = tuple(LockRecordV1.model_validate(item) for item in raw_records)
    if len(records) != EXPECTED_PACKAGE_COUNT:
        raise ValueError("exact package count drifted")
    names = tuple(record.normalized_name for record in records)
    if len(set(names)) != EXPECTED_PACKAGE_COUNT:
        raise ValueError("duplicate normalized distributions in exact lock")

    hosts = Counter(record.hostname for record in records)
    if dict(sorted(hosts.items())) != EXPECTED_HOSTS:
        raise ValueError("exact host distribution counts drifted")

    vllm = [record for record in records if record.normalized_name == "vllm"]
    torch = [record for record in records if record.normalized_name == "torch"]
    if len(vllm) != 1 or len(torch) != 1:
        raise ValueError("vLLM/torch exact records must each be singular")
    if vllm[0].version != EXPECTED_VLLM or vllm[0].sha256 != EXPECTED_VLLM_SHA256:
        raise ValueError("vLLM exact artifact identity drifted")
    if torch[0].version != EXPECTED_TORCH:
        raise ValueError("torch exact artifact identity drifted")

    evidence_checks = acceptance.get("evidence_checks")
    if not isinstance(evidence_checks, dict):
        raise ValueError("acceptance evidence checks missing")
    required_true = (
        "output_manifest_integrity",
        "all_artifacts_are_wheels",
        "all_artifacts_have_sha256",
        "all_hosts_explicit",
        "vllm_identity_exact",
        "vllm_sha256_exact",
        "torch_identity_exact",
    )
    for key in required_true:
        if evidence_checks.get(key) is not True:
            raise ValueError(f"required acceptance gate not true: {key}")

    required_zero = (
        "unclassified_host_count",
        "query_bearing_url_count",
        "fragment_bearing_url_count",
        "retained_wheel_file_count",
        "model_loads_performed",
        "model_requests_performed",
        "benchmark_trajectories_performed",
        "external_spend",
    )
    for key in required_zero:
        if evidence_checks.get(key) != 0:
            raise ValueError(f"required zero-valued acceptance gate drifted: {key}")

    if evidence_checks.get("package_installation_performed") is not False:
        raise ValueError("package installation must remain false")
    if evidence_checks.get("credentials_used") is not False:
        raise ValueError("credentials use must remain false")
    if evidence_checks.get("customer_data_used") is not False:
        raise ValueError("customer data use must remain false")
    if evidence_checks.get("qualification_claimed") is not False:
        raise ValueError("reconnaissance may not claim runtime qualification")

    for payload in (lock, acceptance):
        if payload.get("runtime_execution_authorized") is not False:
            raise ValueError("runtime execution unexpectedly authorized")
        if payload.get("pilot_execution_authorized") is not False:
            raise ValueError("pilot execution unexpectedly authorized")
        if payload.get("final_measured_abc_execution_authorized") is not False:
            raise ValueError("final measured A/B/C unexpectedly authorized")

    if acceptance.get("exact_runtime_resolution_lock_frozen") is not True:
        raise ValueError("exact resolution lock must be frozen by this acceptance")
    if acceptance.get("exact_runtime_materialized") is not False:
        raise ValueError("runtime must remain unmaterialized")
    if acceptance.get("exact_runtime_offline_verified") is not False:
        raise ValueError("runtime must remain offline-unverified")

    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_RESOLUTION_LOCK_V1_VALID",
        "acceptance_decision": acceptance["decision"],
        "package_count": len(records),
        "host_count": len(hosts),
        "exact_runtime_resolution_lock_frozen": True,
        "exact_runtime_materialized": False,
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": "implement_preflight_v3_exact_runtime_wheelhouse_materializer_v1",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("validate",),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()

    summary = validate_repository_package(args.repo_root.resolve())
    print(json.dumps(summary, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
