"""Validate the accepted CUDA 12.9 wheelhouse and active offline verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self, cast

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_wheelhouse_materialization_result_v1.json"
)
RESOLUTION_LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_cu129_resolution_lock_v1.json"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_wheelhouse_materialization_v1.md")
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu129-materialization-acceptance.md")
V1_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v1.ipynb"
)
V2_VERIFIER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v2.ipynb"
)
EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/vllm-cu129-wheelhouse-materialization-v1"
)
EVIDENCE_MANIFEST_PATH: Final = EVIDENCE_DIRECTORY / "evidence_sha256.json"
SOURCE_IDENTITY_PATH: Final = EVIDENCE_DIRECTORY / "source_evidence_identity.json"

EXPECTED_BASE_COMMIT: Final = "1f7889e4254e6240bc77d6aa3dca00e0c456e356"
EXPECTED_RESULT_SHA256: Final = "4457f921d8a397c9e8a09c48948b39e271f74382a61422d60b3e6f4939ea9c18"
EXPECTED_RESOLUTION_LOCK_SHA256: Final = (
    "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
)
EXPECTED_MATERIALIZER_NOTEBOOK_SHA256: Final = (
    "d836a61bc7ed7a0d6c26eca68a28ed22e685e5a6705bf16ce4f6dbb8168f7ba2"
)
EXPECTED_V1_VERIFIER_SHA256: Final = (
    "692f83fd8a6fa7398ee9fabb0ecbf62640c82d6582a96a552f47e4f8b3b1b189"
)
EXPECTED_V2_VERIFIER_SHA256: Final = (
    "86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2"
)
EXPECTED_EXECUTION_LOG_SHA256: Final = (
    "65387a9952bce57d1802ebd8e39dc58dd897d50680debb70f3422c52c4ef5538"
)
EXPECTED_RECEIPT_SHA256: Final = "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
EXPECTED_SHA_MANIFEST_SHA256: Final = (
    "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
)
EXPECTED_MATERIALIZATION_LOCK_SHA256: Final = (
    "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
)
EXPECTED_REQUIREMENTS_LOCK_SHA256: Final = (
    "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
)
EXPECTED_RUNTIME_MANIFEST_SHA256: Final = (
    "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
)
EXPECTED_REQUIREMENTS_IN_SHA256: Final = (
    "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
)
EXPECTED_INSTALL_RUNTIME_SHA256: Final = (
    "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
)
EXPECTED_EVIDENCE_MANIFEST_SHA256: Final = (
    "8e301401307fb7acb39deb78a5d4ab75ef22dd43c487309297836a83f61b0421"
)
EXPECTED_PACKAGE_COUNT: Final = 176
EXPECTED_MANIFEST_ENTRY_COUNT: Final = 182
EXPECTED_WHEEL_ENTRY_COUNT: Final = 176
EXPECTED_NON_WHEEL_ENTRY_COUNT: Final = 6
EXPECTED_TOTAL_WHEEL_BYTES: Final = 5727339111
V1_VERIFIER_NAME: Final = "auragateway-cu129-offline-verifier-v1"
V2_VERIFIER_NAME: Final = "auragateway-cu129-offline-verifier-v2"
V2_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_offline_compatibility_evidence_v2"


class MaterializationEvidenceV1(LocalABCContract):
    """Exact identities from the successful materializer Version 1."""

    notebook_path: Literal["notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb"]
    notebook_sha256: Literal["d836a61bc7ed7a0d6c26eca68a28ed22e685e5a6705bf16ce4f6dbb8168f7ba2"]
    kaggle_title: Literal["auragateway-cu129-wheelhouse-materializer-v1"]
    platform_slug: Literal["not_recorded"]
    output_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    execution_log_sha256: Literal[
        "65387a9952bce57d1802ebd8e39dc58dd897d50680debb70f3422c52c4ef5538"
    ]
    materialization_receipt_sha256: Literal[
        "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
    ]
    sha256_manifest_sha256: Literal[
        "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
    ]
    resolution_lock_sha256: Literal[
        "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
    ]
    materialization_lock_sha256: Literal[
        "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
    ]
    requirements_lock_sha256: Literal[
        "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
    ]
    runtime_manifest_sha256: Literal[
        "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
    ]
    requirements_in_sha256: Literal[
        "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
    ]
    install_runtime_sha256: Literal[
        "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
    ]
    package_count: Literal[176]
    manifest_entry_count: Literal[182]
    wheel_entry_count: Literal[176]
    non_wheel_entry_count: Literal[6]
    total_wheel_bytes: Literal[5727339111]
    pip_download_subcommand_performed: Literal[True]
    pip_resolution_artifact_transfer_observed: Literal[True]
    pip_resolution_transfer_event_count: Literal[358]
    package_installation_performed: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]


class SupersededVerifierV1(LocalABCContract):
    """Static defect classification for the unexecuted verifier v1."""

    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v1.ipynb"
    ]
    notebook_sha256: Literal["692f83fd8a6fa7398ee9fabb0ecbf62640c82d6582a96a552f47e4f8b3b1b189"]
    kaggle_title: Literal["auragateway-cu129-offline-verifier-v1"]
    execution_authority: Literal["SUPERSEDED_BEFORE_EXECUTION"]
    diagnostic_admissibility: Literal["STATIC_DEFECT_EVIDENCE_ONLY"]
    defect_code: Literal["OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK"]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class ActiveVerifierV2(LocalABCContract):
    """Authorized offline-only compatibility verifier contract."""

    notebook_path: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v2.ipynb"
    ]
    notebook_sha256: Literal["86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2"]
    kaggle_title: Literal["auragateway-cu129-offline-verifier-v2"]
    title_character_count: Literal[37]
    output_directory: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v2"]
    output_zip: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v2.zip"]
    accelerator: Literal["T4 x2"]
    internet_enabled: Literal[False]
    secrets_attached: Literal[False]
    input_policy: Literal["EXACTLY_ONE_SUCCESSFUL_MATERIALIZER_OUTPUT"]
    expected_input_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    expected_materialization_receipt_sha256: Literal[
        "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
    ]
    expected_sha256_manifest_sha256: Literal[
        "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
    ]
    expected_runtime_manifest_sha256: Literal[
        "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
    ]
    expected_package_count: Literal[176]
    expected_manifest_entry_count: Literal[182]
    expected_total_wheel_bytes: Literal[5727339111]
    model_requests_permitted: Literal[0]
    qualification_claimed: Literal[False]

    @field_validator("notebook_path")
    @classmethod
    def validate_notebook_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("verifier path must be repository-relative")
        return value


class EvidenceVaultV1(LocalABCContract):
    """Preserved small control-plane evidence from the materializer."""

    path: Literal["evidence_vault/local_abc/vllm-cu129-wheelhouse-materialization-v1"]
    manifest_sha256: Literal["8e301401307fb7acb39deb78a5d4ab75ef22dd43c487309297836a83f61b0421"]
    source_file_count: Literal[9]
    wheel_files_retained_in_repository: Literal[0]


class MaterializationSafetyV1(LocalABCContract):
    """Non-negotiable safety state after materialization."""

    authorization_issued: Literal[False]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    qualification_claimed: Literal[False]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]


class WheelhouseMaterializationResultV1(LocalABCContract):
    """Decision record that closes materialization and opens verifier v2."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-vllm-cu129-wheelhouse-materialization-result-v1"]
    repository_base_commit: Literal["1f7889e4254e6240bc77d6aa3dca00e0c456e356"]
    decision: Literal["APPROVED_FOR_OFFLINE_CU129_RUNTIME_COMPATIBILITY_VERIFICATION_V2"]
    materialization: MaterializationEvidenceV1
    superseded_verifier: SupersededVerifierV1
    active_verifier: ActiveVerifierV2
    evidence_vault: EvidenceVaultV1
    safety: MaterializationSafetyV1
    next_gate: Literal["run_cu129_offline_runtime_compatibility_verifier_v2"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        expected = (
            "offline_install_not_yet_verified",
            "pip_check_not_yet_verified",
            "torch_cuda_runtime_not_yet_verified",
            "two_t4_topology_not_yet_verified",
            "vllm_module_import_not_yet_verified",
            "vllm_native_extension_not_yet_verified",
            "model_not_loaded",
            "qualification_not_authorized",
            "measured_abc_not_authorized",
            "production_readiness_not_claimed",
        )
        if self.non_claims != expected:
            raise ValueError("materialization non-claims drifted")
        return self


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected one JSON object: {path.as_posix()}")
    return cast(dict[str, Any], payload)


def _notebook_source(payload: dict[str, Any]) -> str:
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("notebook cells are missing")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise RuntimeError("offline verifier must contain exactly one code cell")
    source = code_cells[0].get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    if isinstance(source, str):
        return source
    raise RuntimeError("offline verifier source is invalid")


def _validate_notebook(path: Path) -> dict[str, object]:
    payload = _load_json_object(path)
    if payload.get("nbformat") != 4:
        raise RuntimeError("offline verifier must use nbformat 4")
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("offline verifier metadata is missing")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError("AuraGateway verifier metadata is missing")
    expected_metadata = {
        "schema_version": "2.0.0",
        "notebook_name": V2_VERIFIER_NAME,
        "diagnostic_only": True,
        "internet_required": False,
        "accelerator": "T4 x2",
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_requests_permitted": 0,
        "qualification_claimed": False,
        "input_directory_name": "auragateway_vllm_cu129_wheelhouse_v1",
        "input_materialization_receipt_sha256": EXPECTED_RECEIPT_SHA256,
        "input_sha256_manifest_sha256": EXPECTED_SHA_MANIFEST_SHA256,
        "supersedes_notebook": V1_VERIFIER_PATH.as_posix(),
        "supersession_reason": ("OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK"),
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("offline verifier metadata drifted: " + ", ".join(drift))

    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("offline verifier cells are invalid")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise RuntimeError("offline verifier contains execution state")

    source = _notebook_source(payload)
    compile(source, path.as_posix(), "exec")
    required_fragments = (
        'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v2"',
        '"resolution_lock.json"',
        "EXPECTED_MANIFEST_ENTRY_COUNT = 182",
        "EXPECTED_PACKAGE_COUNT = 176",
        "EXPECTED_TOTAL_WHEEL_BYTES = 5727339111",
        EXPECTED_RECEIPT_SHA256,
        EXPECTED_SHA_MANIFEST_SHA256,
        "def streaming_sha256",
        '"PIP_NO_INDEX": "1"',
        '"torch_family_runtime"',
        '"vllm_native_extension"',
        '"model_requests_performed=0"',
        '"qualification_claimed=false"',
        '"upload_only_this_file=true"',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError(
            "offline verifier source lacks reviewed fragments: " + ", ".join(missing)
        )
    observed_sha256 = _file_sha256(path)
    if observed_sha256 != EXPECTED_V2_VERIFIER_SHA256:
        raise RuntimeError("offline verifier raw identity drifted")
    return {
        "notebook_name": V2_VERIFIER_NAME,
        "notebook_sha256": observed_sha256,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "execution_state_present": False,
    }


def _validate_evidence_vault(root: Path) -> list[dict[str, Any]]:
    manifest = _load_json_object(root / EVIDENCE_MANIFEST_PATH)
    if manifest.get("schema_version") != "1.0.0":
        raise RuntimeError("materialization evidence manifest schema drifted")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != 9:
        raise RuntimeError("materialization evidence manifest must contain 9 files")
    observed_paths: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("materialization evidence entry is invalid")
        relative_raw = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(relative_raw, str)
            or not isinstance(digest, str)
            or not isinstance(size_bytes, int)
        ):
            raise RuntimeError("materialization evidence fields are invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("materialization evidence path is unsafe")
        if relative_raw in observed_paths:
            raise RuntimeError("materialization evidence paths are not unique")
        observed_paths.add(relative_raw)
        path = root / EVIDENCE_DIRECTORY / Path(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("materialization evidence file is missing or unsafe")
        if _file_sha256(path) != digest or path.stat().st_size != size_bytes:
            raise RuntimeError("materialization evidence identity drifted")
        parsed.append(cast(dict[str, Any], entry))
    if _file_sha256(root / EVIDENCE_MANIFEST_PATH) != EXPECTED_EVIDENCE_MANIFEST_SHA256:
        raise RuntimeError("materialization evidence manifest raw identity drifted")
    return parsed


def _validate_materialization_metadata(root: Path) -> dict[str, int]:
    sha_manifest = _load_json_object(root / EVIDENCE_DIRECTORY / "sha256_manifest.json")
    entries = sha_manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != EXPECTED_MANIFEST_ENTRY_COUNT:
        raise RuntimeError("wheelhouse manifest count drifted")

    paths: list[str] = []
    digests: list[str] = []
    wheel_entries: dict[str, dict[str, Any]] = {}
    total_wheel_bytes = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("wheelhouse manifest entry is invalid")
        path = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(path, str)
            or not isinstance(digest, str)
            or not isinstance(size_bytes, int)
        ):
            raise RuntimeError("wheelhouse manifest entry fields are invalid")
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("wheelhouse manifest path is unsafe")
        paths.append(path)
        digests.append(digest)
        if path.startswith("wheels/"):
            wheel_entries[path] = cast(dict[str, Any], entry)
            total_wheel_bytes += size_bytes

    if len(paths) != len(set(paths)) or len(digests) != len(set(digests)):
        raise RuntimeError("wheelhouse manifest identities are not unique")
    if len(wheel_entries) != EXPECTED_WHEEL_ENTRY_COUNT:
        raise RuntimeError("wheelhouse manifest wheel count drifted")
    if len(entries) - len(wheel_entries) != EXPECTED_NON_WHEEL_ENTRY_COUNT:
        raise RuntimeError("wheelhouse manifest control-file count drifted")
    if total_wheel_bytes != EXPECTED_TOTAL_WHEEL_BYTES:
        raise RuntimeError("wheelhouse manifest byte count drifted")

    resolution_lock = _load_json_object(root / RESOLUTION_LOCK_PATH)
    records = resolution_lock.get("records")
    if (
        _file_sha256(root / RESOLUTION_LOCK_PATH) != EXPECTED_RESOLUTION_LOCK_SHA256
        or resolution_lock.get("package_count") != EXPECTED_PACKAGE_COUNT
        or not isinstance(records, list)
        or len(records) != EXPECTED_PACKAGE_COUNT
    ):
        raise RuntimeError("repository resolution lock drifted")

    expected_wheels: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError("resolution lock record is invalid")
        filename = record.get("artifact_filename")
        digest = record.get("sha256")
        if not isinstance(filename, str) or not isinstance(digest, str):
            raise RuntimeError("resolution lock record fields are invalid")
        expected_wheels[f"wheels/{urllib.parse.unquote(filename)}"] = digest
    if set(expected_wheels) != set(wheel_entries):
        raise RuntimeError("wheelhouse manifest closure differs from resolution lock")
    for path, expected_digest in expected_wheels.items():
        if wheel_entries[path].get("sha256") != expected_digest:
            raise RuntimeError("wheelhouse manifest artifact identity drifted")

    receipt = _load_json_object(root / EVIDENCE_DIRECTORY / "materialization_receipt.json")
    expected_receipt = {
        "schema_version": "1.2.0",
        "materialization_status": "PASSED",
        "package_count": EXPECTED_PACKAGE_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "resolution_lock_sha256": EXPECTED_RESOLUTION_LOCK_SHA256,
        "materialization_lock_sha256": EXPECTED_MATERIALIZATION_LOCK_SHA256,
        "requirements_lock_sha256": EXPECTED_REQUIREMENTS_LOCK_SHA256,
        "runtime_manifest_sha256": EXPECTED_RUNTIME_MANIFEST_SHA256,
        "sha256_manifest_sha256": EXPECTED_SHA_MANIFEST_SHA256,
        "package_installation_performed": False,
        "model_requests_performed": 0,
        "qualification_claimed": False,
        "credentials_used": False,
        "customer_data_used": False,
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_receipt.items()
            if receipt.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("materialization receipt drifted: " + ", ".join(drift))

    return {
        "manifest_entry_count": len(entries),
        "wheel_entry_count": len(wheel_entries),
        "non_wheel_entry_count": len(entries) - len(wheel_entries),
        "total_wheel_bytes": total_wheel_bytes,
    }


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate materialization evidence and the active verifier v2."""

    root = repo_root.resolve()
    result = WheelhouseMaterializationResultV1.model_validate(_load_json_object(root / RESULT_PATH))
    if _file_sha256(root / RESULT_PATH) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("materialization result raw identity drifted")
    if result.repository_base_commit != EXPECTED_BASE_COMMIT:
        raise RuntimeError("materialization repository base commit drifted")

    evidence_files = _validate_evidence_vault(root)
    metadata = _validate_materialization_metadata(root)

    source_identity = _load_json_object(root / SOURCE_IDENTITY_PATH)
    expected_source = {
        "repository_base_commit": EXPECTED_BASE_COMMIT,
        "materializer_notebook_sha256": EXPECTED_MATERIALIZER_NOTEBOOK_SHA256,
        "execution_log_sha256": EXPECTED_EXECUTION_LOG_SHA256,
        "materialization_receipt_sha256": EXPECTED_RECEIPT_SHA256,
        "sha256_manifest_sha256": EXPECTED_SHA_MANIFEST_SHA256,
        "resolution_lock_sha256": EXPECTED_RESOLUTION_LOCK_SHA256,
        "package_count": EXPECTED_PACKAGE_COUNT,
        "manifest_entry_count": EXPECTED_MANIFEST_ENTRY_COUNT,
        "wheel_entry_count": EXPECTED_WHEEL_ENTRY_COUNT,
        "non_wheel_entry_count": EXPECTED_NON_WHEEL_ENTRY_COUNT,
        "total_wheel_bytes": EXPECTED_TOTAL_WHEEL_BYTES,
        "package_installation_performed": False,
        "model_requests_performed": 0,
        "qualification_claimed": False,
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_source.items()
            if source_identity.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("materialization source identity drifted: " + ", ".join(drift))

    if _file_sha256(root / V1_VERIFIER_PATH) != EXPECTED_V1_VERIFIER_SHA256:
        raise RuntimeError("superseded verifier v1 identity drifted")
    verifier = _validate_notebook(root / V2_VERIFIER_PATH)

    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_runbook_fragments = (
        "APPROVED_FOR_OFFLINE_CU129_RUNTIME_COMPATIBILITY_VERIFICATION_V2",
        "run_cu129_offline_runtime_compatibility_verifier_v2",
        V1_VERIFIER_NAME,
        "OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK",
        V2_VERIFIER_NAME,
        V2_OUTPUT_DIRECTORY,
        EXPECTED_RECEIPT_SHA256,
        EXPECTED_SHA_MANIFEST_SHA256,
        EXPECTED_V2_VERIFIER_SHA256,
        "Accelerator: T4 x2",
        "Internet: Off",
        "Inputs: exactly the successful Version 1 materializer output",
    )
    if any(fragment not in runbook for fragment in required_runbook_fragments):
        raise RuntimeError("CUDA 12.9 materialization runbook drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "Status: Accepted",
        "OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK",
        EXPECTED_RECEIPT_SHA256,
        EXPECTED_SHA_MANIFEST_SHA256,
        EXPECTED_V2_VERIFIER_SHA256,
        V2_VERIFIER_NAME,
    )
    if any(fragment not in adr for fragment in required_adr_fragments):
        raise RuntimeError("CUDA 12.9 materialization acceptance ADR drifted")

    return {
        "status": "VLLM_CU129_WHEELHOUSE_MATERIALIZATION_PACKAGE_VALID",
        "decision": result.decision,
        "record_sha256": EXPECTED_RESULT_SHA256,
        "repository_base_commit": result.repository_base_commit,
        "materialization_receipt_sha256": EXPECTED_RECEIPT_SHA256,
        "sha256_manifest_sha256": EXPECTED_SHA_MANIFEST_SHA256,
        "resolution_lock_sha256": EXPECTED_RESOLUTION_LOCK_SHA256,
        "package_count": metadata["wheel_entry_count"],
        "manifest_entry_count": metadata["manifest_entry_count"],
        "total_wheel_bytes": metadata["total_wheel_bytes"],
        "evidence_files_verified": len(evidence_files) + 1,
        "superseded_verifier_notebook_sha256": EXPECTED_V1_VERIFIER_SHA256,
        "active_verifier_notebook_sha256": verifier["notebook_sha256"],
        "active_verifier_kaggle_title": V2_VERIFIER_NAME,
        "active_verifier_title_character_count": len(V2_VERIFIER_NAME),
        "authorization_issued": result.safety.authorization_issued,
        "model_requests_performed": result.safety.model_requests_performed,
        "qualification_claimed": result.safety.qualification_claimed,
        "next_gate": result.next_gate,
    }


def main() -> int:
    """Validate the repository package and print canonical JSON."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(validate_repository_package(args.repo_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
