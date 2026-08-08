"""Validate accepted preflight-v3 exact-runtime wheelhouse materialization."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Final, Literal

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_wheelhouse_materialization_acceptance_v1.json"
)
EVIDENCE_DIR: Final = Path(
    "benchmarks/local_abc/evidence/preflight_v3_exact_runtime_wheelhouse_materialization_v1"
)

EXPECTED_SOURCE_MAIN: Final = "58591400897bcd278d7bfc33f110a9a8e813e29b"
EXPECTED_FEATURE_COMMIT: Final = "62596eeb1f82c7609a3971c752e4b04a9ec54257"
EXPECTED_SCRIPT_VERSION_ID: Final = 341083505
EXPECTED_REPOSITORY_NOTEBOOK_SHA256: Final = (
    "e227c7926d7c8fd9acbdc3d773ba3dd145494aec6f150485e37af86d801f7c77"
)
EXPECTED_EXECUTED_NOTEBOOK_SHA256: Final = (
    "e78dbe922e70a62e0cc00c753f7497fcd99352a83150a74f9681fd9ba4d6fc79"
)
EXPECTED_MARKDOWN_SOURCE_SHA256: Final = (
    "8b49733ea3057aa85e36368fc24d9134f97185f9278ec1f72190e3951bef7abb"
)
EXPECTED_CODE_SOURCE_SHA256: Final = (
    "1f6193854cd129f3c1c5b706eaa6d448811fc8576458e24e15e87035205ab56f"
)
EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "6d97b933473064a71fafe790ab9d8a5bf87d9805d8666880b209123745a5d6df"
)
EXPECTED_EXECUTION_LOG_SHA256: Final = (
    "1269101cae7b3f6a321a5ac5c42972b47f44d8da19e8af54a15dc628f0594eb1"
)
EXPECTED_LOCK_SHA256: Final = "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
EXPECTED_ACCEPTANCE_SHA256: Final = (
    "042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725"
)
EXPECTED_PACKAGE_COUNT: Final = 196
EXPECTED_AUTHORITY_HOST_COUNT: Final = 5
EXPECTED_SHA_MANIFEST_ENTRY_COUNT: Final = 200
EXPECTED_TOTAL_WHEEL_BYTES: Final = 6164913809
EXPECTED_REDIRECT_EVENT_COUNT: Final = 1

EXPECTED_MEMBER_HASHES: Final[dict[str, str]] = {
    "materialization.lock.txt": "774461508794d804244b2f0dbff05e52fdccc8efbe19af8cfb8d0faedcb25339",
    "materialization_receipt.json": (
        "55bc8d078af9960d5f6a60bf7d9638820be9fdda0ee76754a9462d46eb053fe0"
    ),
    "requirements.lock.txt": "cf5d773ef5c26f2e42a7afd76f0e466c21847169986f14fe5a7ac9ad02f0a3c3",
    "runtime_manifest.json": "cb9c62321ea1651deac260126db75c39525e4ba711ee3708fe5f7a5b50ffd6ed",
    "sha256_manifest.json": "00dbda4fd734cf94b6f5dfde2619f83ed6a4db7761a4c3c5ace6b0f1ebe63b08",
}
EXPECTED_MEMBER_SIZES: Final[dict[str, int]] = {
    "materialization.lock.txt": 25171,
    "materialization_receipt.json": 931,
    "requirements.lock.txt": 19652,
    "runtime_manifest.json": 940,
    "sha256_manifest.json": 33938,
}


class EvidenceMemberIdentityV1(LocalABCContract):
    path: str
    sha256: str
    size_bytes: int

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence member identity must use lowercase SHA-256")
        return value


class EvidenceChecksV1(LocalABCContract):
    terminal_status: Literal["PASSED_PENDING_REPOSITORY_ACCEPTANCE"]
    locked_package_count: Literal[196]
    downloaded_package_count: Literal[196]
    wheel_file_count: Literal[196]
    sha256_manifest_entry_count: Literal[200]
    sha256_manifest_wheel_entry_count: Literal[196]
    sha256_manifest_control_entry_count: Literal[4]
    authority_host_count: Literal[5]
    observed_transport_redirect_event_count: Literal[1]
    total_wheel_bytes: Literal[6164913809]
    wheel_names_missing_from_frozen_lock: Literal[0]
    unexpected_wheel_names: Literal[0]
    wheel_sha_mismatches_against_frozen_lock: Literal[0]
    requirements_lock_exactly_reconstructed_from_frozen_lock: Literal[True]
    materialization_lock_exactly_reconstructed_from_frozen_lock: Literal[True]
    control_manifest_hashes_match_evidence_bytes: Literal[True]
    dependency_resolution_performed: Literal[False]
    package_installation_performed: Literal[False]
    model_loads_performed: Literal[0]
    model_requests_performed: Literal[0]
    benchmark_trajectories_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]
    qualification_claimed: Literal[False]


class MaterializationAcceptanceV1(LocalABCContract):
    schema_version: Literal["1.0.0"]
    acceptance_id: Literal[
        "auragateway-preflight-v3-exact-runtime-wheelhouse-materialization-acceptance-v1"
    ]
    source_main_merge_commit: str
    materializer_feature_commit: str
    decision: Literal["ACCEPT_EXACT_RUNTIME_WHEELHOUSE_MATERIALIZATION_V1"]
    kaggle_script_version_id: Literal[341083505]
    repository_notebook_sha256: str
    executed_notebook_sha256: str
    executed_markdown_source_matches_repository: Literal[True]
    executed_code_source_matches_repository: Literal[True]
    markdown_cell_source_sha256: str
    code_cell_source_sha256: str
    materialization_evidence_zip_sha256: str
    execution_log_sha256: str
    exact_resolution_lock_sha256: str
    queryable_evidence_members: dict[str, EvidenceMemberIdentityV1]
    evidence_checks: EvidenceChecksV1
    wheelhouse_materialized: Literal[True]
    exact_runtime_resolution_lock_frozen: Literal[True]
    exact_runtime_materialized: Literal[True]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    variance_pilot_accepted: Literal[False]
    repetition_count_frozen: Literal[False]
    execution_manifest_frozen: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["implement_preflight_v3_exact_runtime_offline_compatibility_verifier_v1"]

    @field_validator(
        "repository_notebook_sha256",
        "executed_notebook_sha256",
        "markdown_cell_source_sha256",
        "code_cell_source_sha256",
        "materialization_evidence_zip_sha256",
        "execution_log_sha256",
        "exact_resolution_lock_sha256",
    )
    @classmethod
    def validate_hashes(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("acceptance hashes must use lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_source_identity(self) -> MaterializationAcceptanceV1:
        expected = {
            "source_main_merge_commit": EXPECTED_SOURCE_MAIN,
            "materializer_feature_commit": EXPECTED_FEATURE_COMMIT,
            "repository_notebook_sha256": EXPECTED_REPOSITORY_NOTEBOOK_SHA256,
            "executed_notebook_sha256": EXPECTED_EXECUTED_NOTEBOOK_SHA256,
            "markdown_cell_source_sha256": EXPECTED_MARKDOWN_SOURCE_SHA256,
            "code_cell_source_sha256": EXPECTED_CODE_SOURCE_SHA256,
            "materialization_evidence_zip_sha256": EXPECTED_EVIDENCE_ZIP_SHA256,
            "execution_log_sha256": EXPECTED_EXECUTION_LOG_SHA256,
            "exact_resolution_lock_sha256": EXPECTED_LOCK_SHA256,
        }
        for field, expected_value in expected.items():
            if getattr(self, field) != expected_value:
                raise ValueError(f"acceptance identity drifted: {field}")
        return self


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _expected_requirements(lock_records: list[object]) -> str:
    typed: list[dict[str, object]] = []
    for raw in lock_records:
        if not isinstance(raw, dict):
            raise ValueError("frozen lock record is not an object")
        typed.append(raw)
    rows = []
    for record in sorted(typed, key=lambda item: str(item["normalized_name"])):
        rows.append(
            f"{record['normalized_name']}=={record['version']} --hash=sha256:{record['sha256']}"
        )
    return "\n".join(rows) + "\n"


def _expected_materialization_lock(lock_records: list[object]) -> str:
    typed: list[dict[str, object]] = []
    for raw in lock_records:
        if not isinstance(raw, dict):
            raise ValueError("frozen lock record is not an object")
        typed.append(raw)
    rows = []
    for record in sorted(typed, key=lambda item: str(item["normalized_name"])):
        rows.append(f"{record['sha256']}  wheels/{record['artifact_filename']}")
    return "\n".join(rows) + "\n"


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    lock_path = repo_root / LOCK_PATH
    acceptance_path = repo_root / ACCEPTANCE_PATH

    if _sha256(lock_path) != EXPECTED_LOCK_SHA256:
        raise ValueError("frozen exact-runtime resolution lock SHA-256 drifted")
    if _sha256(acceptance_path) != EXPECTED_ACCEPTANCE_SHA256:
        raise ValueError("materialization acceptance SHA-256 drifted")

    acceptance = MaterializationAcceptanceV1.model_validate(_load_json(acceptance_path))
    if acceptance.kaggle_script_version_id != EXPECTED_SCRIPT_VERSION_ID:
        raise ValueError("Kaggle script version identity drifted")

    observed_members = set(acceptance.queryable_evidence_members)
    if observed_members != set(EXPECTED_MEMBER_HASHES):
        raise ValueError("queryable materialization evidence member set drifted")

    for name, expected_sha in EXPECTED_MEMBER_HASHES.items():
        evidence_path = repo_root / EVIDENCE_DIR / name
        member = acceptance.queryable_evidence_members[name]
        if member.path != (EVIDENCE_DIR / name).as_posix():
            raise ValueError(f"queryable evidence path drifted: {name}")
        if member.sha256 != expected_sha:
            raise ValueError(f"acceptance evidence SHA drifted: {name}")
        if member.size_bytes != EXPECTED_MEMBER_SIZES[name]:
            raise ValueError(f"acceptance evidence size drifted: {name}")
        if _sha256(evidence_path) != expected_sha:
            raise ValueError(f"queryable evidence bytes drifted: {name}")
        if evidence_path.stat().st_size != EXPECTED_MEMBER_SIZES[name]:
            raise ValueError(f"queryable evidence file size drifted: {name}")

    lock = _load_json(lock_path)
    raw_records = lock.get("records")
    if not isinstance(raw_records, list) or len(raw_records) != EXPECTED_PACKAGE_COUNT:
        raise ValueError("frozen lock package boundary drifted")

    requirements = (repo_root / EVIDENCE_DIR / "requirements.lock.txt").read_text(encoding="utf-8")
    if requirements != _expected_requirements(raw_records):
        raise ValueError("requirements lock does not reconstruct frozen resolution lock")

    materialization_lock = (repo_root / EVIDENCE_DIR / "materialization.lock.txt").read_text(
        encoding="utf-8"
    )
    if materialization_lock != _expected_materialization_lock(raw_records):
        raise ValueError("materialization lock does not reconstruct frozen resolution lock")

    runtime_manifest = _load_json(repo_root / EVIDENCE_DIR / "runtime_manifest.json")
    receipt = _load_json(repo_root / EVIDENCE_DIR / "materialization_receipt.json")
    sha_manifest = _load_json(repo_root / EVIDENCE_DIR / "sha256_manifest.json")

    runtime_expected = {
        "exact_resolution_lock_sha256": EXPECTED_LOCK_SHA256,
        "locked_package_count": EXPECTED_PACKAGE_COUNT,
        "downloaded_package_count": EXPECTED_PACKAGE_COUNT,
        "authority_host_count": EXPECTED_AUTHORITY_HOST_COUNT,
        "observed_redirect_event_count": EXPECTED_REDIRECT_EVENT_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "dependency_resolution_performed": False,
        "package_installation_performed": False,
        "model_loads_performed": 0,
        "model_requests_performed": 0,
        "benchmark_trajectories_performed": 0,
        "credentials_used": False,
        "customer_data_used": False,
        "external_spend": 0,
    }
    for key, expected_value in runtime_expected.items():
        if runtime_manifest.get(key) != expected_value:
            raise ValueError(f"runtime manifest evidence drifted: {key}")

    receipt_expected = {
        "materialization_status": "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
        "exact_resolution_lock_sha256": EXPECTED_LOCK_SHA256,
        "locked_package_count": EXPECTED_PACKAGE_COUNT,
        "downloaded_package_count": EXPECTED_PACKAGE_COUNT,
        "wheel_file_count": EXPECTED_PACKAGE_COUNT,
        "authority_host_count": EXPECTED_AUTHORITY_HOST_COUNT,
        "observed_transport_redirect_event_count": EXPECTED_REDIRECT_EVENT_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
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
    }
    for key, expected_value in receipt_expected.items():
        if receipt.get(key) != expected_value:
            raise ValueError(f"materialization receipt evidence drifted: {key}")

    if receipt.get("sha256_manifest_sha256") != EXPECTED_MEMBER_HASHES["sha256_manifest.json"]:
        raise ValueError("receipt does not bind exact SHA manifest")

    if sha_manifest.get("entry_count") != EXPECTED_SHA_MANIFEST_ENTRY_COUNT:
        raise ValueError("SHA manifest entry count drifted")
    if sha_manifest.get("wheel_entry_count") != EXPECTED_PACKAGE_COUNT:
        raise ValueError("SHA manifest wheel entry count drifted")
    if sha_manifest.get("control_entry_count") != 4:
        raise ValueError("SHA manifest control entry count drifted")

    raw_entries = sha_manifest.get("entries")
    if not isinstance(raw_entries, list) or len(raw_entries) != 200:
        raise ValueError("SHA manifest entries missing or drifted")

    lock_by_filename: dict[str, dict[str, object]] = {}
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise ValueError("frozen lock record is invalid")
        filename = raw.get("artifact_filename")
        if not isinstance(filename, str):
            raise ValueError("frozen lock filename missing")
        if filename in lock_by_filename:
            raise ValueError("duplicate frozen lock artifact filename")
        lock_by_filename[filename] = raw

    wheel_entries: list[dict[str, object]] = []
    control_entries: list[dict[str, object]] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ValueError("SHA manifest entry is invalid")
        path = raw.get("path")
        if not isinstance(path, str):
            raise ValueError("SHA manifest path missing")
        if path.startswith("wheels/"):
            wheel_entries.append(raw)
        else:
            control_entries.append(raw)

    if len(wheel_entries) != EXPECTED_PACKAGE_COUNT:
        raise ValueError("SHA manifest exact wheel set count drifted")
    if len(control_entries) != 4:
        raise ValueError("SHA manifest control set count drifted")

    observed_wheel_names: set[str] = set()
    total_wheel_bytes = 0
    for entry in wheel_entries:
        path = entry["path"]
        assert isinstance(path, str)
        filename = path.removeprefix("wheels/")
        if filename in observed_wheel_names:
            raise ValueError("duplicate wheel in SHA manifest")
        observed_wheel_names.add(filename)
        locked = lock_by_filename.get(filename)
        if locked is None:
            raise ValueError(f"unexpected wheel in SHA manifest: {filename}")
        if entry.get("sha256") != locked.get("sha256"):
            raise ValueError(f"wheel SHA differs from frozen lock: {filename}")
        size = entry.get("size_bytes")
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"wheel size is invalid: {filename}")
        total_wheel_bytes += size

    if observed_wheel_names != set(lock_by_filename):
        raise ValueError("SHA manifest is missing frozen wheel identities")
    if total_wheel_bytes != EXPECTED_TOTAL_WHEEL_BYTES:
        raise ValueError("SHA manifest total wheel bytes drifted")

    control_names = {
        "resolution_lock.json",
        "requirements.lock.txt",
        "materialization.lock.txt",
        "runtime_manifest.json",
    }
    observed_controls = {str(entry["path"]) for entry in control_entries}
    if observed_controls != control_names:
        raise ValueError("SHA manifest control file set drifted")

    control_hashes = {
        "resolution_lock.json": EXPECTED_LOCK_SHA256,
        "requirements.lock.txt": EXPECTED_MEMBER_HASHES["requirements.lock.txt"],
        "materialization.lock.txt": EXPECTED_MEMBER_HASHES["materialization.lock.txt"],
        "runtime_manifest.json": EXPECTED_MEMBER_HASHES["runtime_manifest.json"],
    }
    for entry in control_entries:
        path = str(entry["path"])
        if entry.get("sha256") != control_hashes[path]:
            raise ValueError(f"SHA manifest control identity drifted: {path}")

    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_MATERIALIZATION_V1_ACCEPTED",
        "decision": acceptance.decision,
        "kaggle_script_version_id": EXPECTED_SCRIPT_VERSION_ID,
        "package_count": EXPECTED_PACKAGE_COUNT,
        "authority_host_count": EXPECTED_AUTHORITY_HOST_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "wheelhouse_materialized": True,
        "exact_runtime_resolution_lock_frozen": True,
        "exact_runtime_materialized": True,
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": ("implement_preflight_v3_exact_runtime_offline_compatibility_verifier_v1"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    summary = validate_repository_package(args.repo_root.resolve())
    print(json.dumps(summary, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
