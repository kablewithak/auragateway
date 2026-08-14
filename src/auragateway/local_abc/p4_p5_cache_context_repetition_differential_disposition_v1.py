"""Preserve and disposition the governed P4/P5 cache-context repetition differential."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "83d0e5c74aa607cc4b48232070c2caa3980c2f9ca5c9d84bcababed1542e960e"
SAVED_VERSION_ID: Final = 342415694
ISSUER_MERGE_COMMIT: Final = "28eac96bcf8e82dbe44e0a56460aed2c692d8518"

CUSTODY_MANIFEST_SHA256: Final = "eb2bdf99fa6354f6dce9f966f306d2ea2471ad7d8eb8909345760aa18bc97a21"
EVIDENCE_ZIP_SHA256: Final = "24be27819b28a39df08b3a69bf1c168f6abef58aec5cd90883b8621f2e4aafca"
TERMINAL_LOG_SHA256: Final = "5a3f3ece251d7cce91056931483f3f2a7e648d2d536584cb32a39be0a8d90b45"
NOTEBOOK_SHA256: Final = "3a3e16defd1a9dff45c07a8343882c29249c0755e896b76503f6b75d31ef34db"
PLATFORM_RECEIPT_SHA256: Final = "48fef6a1ca0d7f26dac1df385075a727cc4692bb7bc50a43d586aa9ba0ebdb57"
RUNTIME_SHA256: Final = "dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b"
IMPLEMENTATION_RECORD_SHA256: Final = (
    "31628aef52b292236bbaf9a787fd1f47ca3751a1416cf916b51fc354258e4a6c"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "6bf7595e9dda3793f94bf866e0feff8db31cfe2c4c9cd7e3f4941c973a4ea2a4"
)
AUTHORIZATION_DESIGN_RECORD_SHA256: Final = (
    "900b76c0cf8f833733f63c006e4aa489f9581d80260f4f30f6a4b9161c973a77"
)
ISSUER_SOURCE_SHA256: Final = "099991f9979ef4fde8c05e30694a3b5ecc26f483a4d3da7bb81414f666030602"
GENERATOR_CONTRACT_SHA256: Final = (
    "df9cf11134864be79732f5eb457c4203414a71169d2627edb3122bd35d0f3b14"
)

CONTROL_TOKEN_COUNT: Final = 117
CONTROL_TOKEN_SHA256: Final = "32a570d63aaaeb9597a2b517315b052eae7308b7acba6f4a85d409e3c633edbb"
CONTROL_PAYLOAD_SHA256: Final = "cb250709bd4c201743206b2c79995d9ad2ad0dee333b596747f7d75ca080438d"
CONTROL_RESPONSE_SHA256: Final = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
TREATMENT_TOKEN_COUNT: Final = 899
TREATMENT_TOKEN_SHA256: Final = "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
TREATMENT_PAYLOAD_SHA256: Final = "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
TREATMENT_RESPONSE_SHA256: Final = (
    "da4ae47e5a52cd6ce2aedb5e8c7257b5a998b42e5b8ea9118f0200bab0b2322f"
)

RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_runtime_v1.py"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_implementation_v1.json"
)
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_implementation_v1_review.json"
)
AUTHORIZATION_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_execution_authorization_design_v1.json"
)
ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_execution_authorization_v1.py"
)
GENERATOR_CONTRACT_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "p4_p5_cache_context_repetition_differential_transaction_bound_wrapper_v1.py.tmpl"
)

VAULT_ROOT: Final = Path("evidence_vault/local_abc/p4-p5-cache-context-repetition-differential-v1")
CUSTODY_MANIFEST_PATH: Final = VAULT_ROOT / "custody_manifest_v1.json"
AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/execution_authorization_v1.json"
EXECUTION_MANIFEST_PATH: Final = VAULT_ROOT / "lifecycle/execution_artifact_manifest_v1.json"
PLATFORM_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/platform_observation_receipt_v1.json"
TERMINAL_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/authorization_terminal_receipt_v1.json"
EVIDENCE_ZIP_PATH: Final = (
    VAULT_ROOT / "kaggle/ag-p4-p5-cache-context-repetition-differential-evidence-v1-342415694.zip"
)
NOTEBOOK_PATH: Final = (
    VAULT_ROOT / "kaggle/ag-p4-p5-cache-context-repetition-differential-v1-342415694.ipynb"
)
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "kaggle/kaggle-terminal-342415694.log"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_disposition_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_cache_context_repetition_differential_disposition_v1_review.json"
)
NEXT_GATE: Final = "STATIC_LONG_REPEATED_CONTEXT_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"

REQUEST_ORDER: Final = (
    "CONTROL_1X",
    "TREATMENT_24X",
    "TREATMENT_24X",
    "CONTROL_1X",
    "CONTROL_1X",
    "TREATMENT_24X",
)


class DispositionError(RuntimeError):
    """Fail-closed evidence-disposition error."""

    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(StrictModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class CustodyManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    manifest_id: Literal[
        "auragateway-p4-p5-cache-context-repetition-differential-evidence-custody-v1"
    ]
    transaction_id: Literal["83d0e5c74aa607cc4b48232070c2caa3980c2f9ca5c9d84bcababed1542e960e"]
    saved_version_id: Literal[342415694]
    execution_status: Literal["DIAGNOSTIC_COMPLETE"]
    decision_state: Literal["LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"]
    control_exact_object_count: Literal[3]
    treatment_exact_object_count: Literal[0]
    terminal_disposition: Literal["CONSUMED"]
    terminal_execution_outcome: Literal["PASSED"]
    authorization_reusable: Literal[False]
    member_count: Literal[7]
    members: tuple[ArtifactReceipt, ...]

    @model_validator(mode="after")
    def validate_member_count(self) -> Self:
        if len(self.members) != self.member_count:
            raise ValueError("custody member count drifted")
        return self


class DispositionRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-p4-p5-cache-context-repetition-differential-disposition-v1"]
    status: Literal["DISPOSITIONED_VALID_GOVERNED_REPETITION_DIFFERENTIAL"]
    transaction_id: Literal["83d0e5c74aa607cc4b48232070c2caa3980c2f9ca5c9d84bcababed1542e960e"]
    saved_version_id: Literal[342415694]
    terminal_disposition: Literal["CONSUMED"]
    execution_outcome: Literal["PASSED"]
    diagnostic_status: Literal["DIAGNOSTIC_COMPLETE"]
    decision_state: Literal["LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"]
    variable_under_test: Literal["CACHE_CONTEXT_REPETITION_COUNT"]
    control_repetition_count: Literal[1]
    treatment_repetition_count: Literal[24]
    observations_per_condition: Literal[3]
    control_exact_object_count: Literal[3]
    treatment_exact_object_count: Literal[0]
    control_valid_json_count: Literal[3]
    treatment_valid_json_count: Literal[0]
    control_intra_condition_identity_matched: Literal[True]
    treatment_intra_condition_identity_matched: Literal[True]
    treatment_historical_identity_matched: Literal[True]
    fresh_worker_process_per_observation: Literal[True]
    worker_identity_cardinality: Literal[6]
    runtime_source_identity_verified: Literal[True]
    runtime_installation_passed: Literal[True]
    runtime_import_closure_passed: Literal[True]
    model_requests_performed: Literal[6]
    model_loads_performed: Literal[6]
    worker_starts_performed: Literal[6]
    hidden_retries_performed: Literal[0]
    external_network_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    external_spend: Literal[0]
    teardown_passed: Literal[True]
    scratch_cleanup_passed: Literal[True]
    raw_prompt_retained: Literal[False]
    raw_model_output_retained: Literal[False]
    p5_requalified: Literal[False]
    p6_requalified: Literal[False]
    measured_abc_execution_performed: Literal[False]
    pilot_execution_performed: Literal[False]
    long_repeated_24x_condition_necessary_relative_to_1x_established: Literal[True]
    exact_repetition_threshold_established: Literal[False]
    repetition_alone_established_causal: Literal[False]
    context_length_alone_established_causal: Literal[False]
    exact_root_cause_established: Literal[False]
    prefix_cache_defect_established: Literal[False]
    new_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    causal_classification: Literal["LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"]
    specific_classification: Literal[
        "FROZEN_24X_CONDITION_NECESSARY_RELATIVE_TO_1X_FOR_CURRENT_C3_REGRESSION"
    ]
    causal_confidence: Literal["PREDECLARED_COUNTERFACTUAL_DIFFERENTIAL_WITHIN_FROZEN_RUNTIME"]
    custody_manifest_sha256: Literal[
        "eb2bdf99fa6354f6dce9f966f306d2ea2471ad7d8eb8909345760aa18bc97a21"
    ]
    governed_evidence_zip_sha256: Literal[
        "24be27819b28a39df08b3a69bf1c168f6abef58aec5cd90883b8621f2e4aafca"
    ]
    authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...]
    next_gate: Literal["STATIC_LONG_REPEATED_CONTEXT_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"]

    @model_validator(mode="after")
    def validate_record_boundary(self) -> Self:
        if len(self.authorities) != 14:
            raise ValueError("disposition authority count drifted")
        if len(self.non_claims) < 9:
            raise ValueError("disposition non-claim boundary is incomplete")
        return self


class DispositionReview(StrictModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal[
        "auragateway-p4-p5-cache-context-repetition-differential-disposition-v1-review"
    ]
    status: Literal["APPROVED_GOVERNED_REPETITION_DIFFERENTIAL_DISPOSITION"]
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: Literal[
        "eb2bdf99fa6354f6dce9f966f306d2ea2471ad7d8eb8909345760aa18bc97a21"
    ]
    positive_necessity_result_accepted: Literal[True]
    exact_threshold_claimed: Literal[False]
    exact_root_cause_claimed: Literal[False]
    p5_requalification_claimed: Literal[False]
    p6_requalification_claimed: Literal[False]
    measured_abc_claimed: Literal[False]
    new_execution_authorized: Literal[False]
    next_gate: Literal["STATIC_LONG_REPEATED_CONTEXT_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_ARTIFACT_MISSING",
            "required disposition artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _require_hash(root: Path, relative: Path, expected: str) -> Path:
    path = _require_file(root, relative)
    if _sha256_file(path) != expected:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_IDENTITY_DRIFT",
            "disposition artifact byte identity drifted",
            relative.as_posix(),
        )
    return path


def _load_json_file(root: Path, relative: Path) -> dict[str, object]:
    path = _require_file(root, relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_JSON_INVALID",
            "disposition JSON is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_JSON_INVALID",
            "disposition JSON root must be an object",
            relative.as_posix(),
        )
    return cast(dict[str, object], payload)


def _canonical_json_bytes(payload: BaseModel | dict[str, object]) -> bytes:
    value: object = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _receipt(root: Path, role: str, relative: Path) -> ArtifactReceipt:
    path = _require_file(root, relative)
    return ArtifactReceipt(
        role=role,
        path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _member_name_is_safe(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or not path.parts:
        return False
    return all(part not in {"", ".", ".."} for part in path.parts)


def _zip_json(archive: zipfile.ZipFile, member: str) -> dict[str, object]:
    matches = [
        info
        for info in archive.infolist()
        if info.filename.replace("\\", "/") == member and not info.is_dir()
    ]
    if len(matches) != 1:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_ZIP_MEMBER_INVALID",
            "required evidence member cardinality drifted",
            member,
        )
    try:
        payload = json.loads(archive.read(matches[0]).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_ZIP_JSON_INVALID",
            "required evidence JSON member is invalid",
            member,
        ) from error
    if not isinstance(payload, dict):
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_ZIP_JSON_INVALID",
            "required evidence JSON root must be an object",
            member,
        )
    return cast(dict[str, object], payload)


def _validate_custody(root: Path) -> CustodyManifest:
    _require_hash(root, CUSTODY_MANIFEST_PATH, CUSTODY_MANIFEST_SHA256)
    custody = CustodyManifest.model_validate(_load_json_file(root, CUSTODY_MANIFEST_PATH))
    expected = {
        "execution_authorization": AUTHORIZATION_PATH,
        "execution_artifact_manifest": EXECUTION_MANIFEST_PATH,
        "platform_observation_receipt": PLATFORM_RECEIPT_PATH,
        "authorization_terminal_receipt": TERMINAL_RECEIPT_PATH,
        "governed_evidence_zip": EVIDENCE_ZIP_PATH,
        "saved_notebook": NOTEBOOK_PATH,
        "terminal_log": TERMINAL_LOG_PATH,
    }
    by_role = {item.role: item for item in custody.members}
    if set(by_role) != set(expected):
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_CUSTODY_ROLE_DRIFT",
            "custody role inventory drifted",
            CUSTODY_MANIFEST_PATH.as_posix(),
        )
    for role, relative in expected.items():
        receipt = by_role[role]
        path = _require_file(root, relative)
        if receipt.path != relative.as_posix():
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_CUSTODY_PATH_DRIFT",
                "custody member path drifted",
                relative.as_posix(),
            )
        if receipt.size_bytes != path.stat().st_size or receipt.sha256 != _sha256_file(path):
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_CUSTODY_IDENTITY_DRIFT",
                "custody member byte identity drifted",
                relative.as_posix(),
            )
    return custody


def _validate_authority_chain(root: Path) -> None:
    for relative, expected in (
        (RUNTIME_PATH, RUNTIME_SHA256),
        (IMPLEMENTATION_RECORD_PATH, IMPLEMENTATION_RECORD_SHA256),
        (IMPLEMENTATION_REVIEW_PATH, IMPLEMENTATION_REVIEW_SHA256),
        (AUTHORIZATION_DESIGN_RECORD_PATH, AUTHORIZATION_DESIGN_RECORD_SHA256),
        (ISSUER_SOURCE_PATH, ISSUER_SOURCE_SHA256),
        (GENERATOR_CONTRACT_PATH, GENERATOR_CONTRACT_SHA256),
    ):
        _require_hash(root, relative, expected)


def _validate_lifecycle(root: Path) -> None:
    authorization = _load_json_file(root, AUTHORIZATION_PATH)
    manifest = _load_json_file(root, EXECUTION_MANIFEST_PATH)
    platform = _load_json_file(root, PLATFORM_RECEIPT_PATH)
    terminal = _load_json_file(root, TERMINAL_RECEIPT_PATH)

    for name, payload in (
        ("authorization", authorization),
        ("manifest", manifest),
        ("platform receipt", platform),
        ("terminal receipt", terminal),
    ):
        if payload.get("transaction_id") != TRANSACTION_ID:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_TRANSACTION_DRIFT",
                f"{name} transaction identity drifted",
            )

    auth = authorization.get("authorization")
    if not isinstance(auth, dict):
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_AUTHORIZATION_DRIFT",
            "authorization envelope is unavailable",
        )
    if auth.get("scope") != "P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1":
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_AUTHORIZATION_DRIFT",
            "authorization scope drifted",
        )
    if auth.get("issuer_merge_commit") != ISSUER_MERGE_COMMIT:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_AUTHORIZATION_DRIFT",
            "issuer merge commit drifted",
        )
    if auth.get("runtime_payload_sha256") != RUNTIME_SHA256:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_AUTHORIZATION_DRIFT",
            "runtime payload identity drifted",
        )
    budget = auth.get("budget")
    if not isinstance(budget, dict):
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_AUTHORIZATION_DRIFT",
            "authorization budget is unavailable",
        )
    expected_budget: dict[str, object] = {
        "maximum_kaggle_sessions": 1,
        "maximum_save_and_run_all_actions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "maximum_hidden_retries": 0,
        "maximum_replacement_workers": 0,
        "maximum_external_network_requests": 0,
        "maximum_benchmark_trajectory_requests": 0,
        "maximum_external_spend": 0,
    }
    for key, expected in expected_budget.items():
        if budget.get(key) != expected:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_BUDGET_DRIFT",
                f"authorization budget drifted: {key}",
            )

    if manifest.get("issuer_merge_commit") != ISSUER_MERGE_COMMIT:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_MANIFEST_DRIFT",
            "manifest issuer merge commit drifted",
        )
    if manifest.get("runtime_payload_sha256") != RUNTIME_SHA256:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_MANIFEST_DRIFT",
            "manifest runtime payload identity drifted",
        )

    required_platform: dict[str, object] = {
        "accelerator": "T4_X2",
        "allocated_gpu_count": 2,
        "internet_enabled": False,
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "persisted_before_save_and_run_all": True,
        "receipt_runtime_input": False,
    }
    for key, expected in required_platform.items():
        if platform.get(key) != expected:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_PLATFORM_DRIFT",
                f"platform observation drifted: {key}",
            )
    if _sha256_file(root / PLATFORM_RECEIPT_PATH) != PLATFORM_RECEIPT_SHA256:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_PLATFORM_DRIFT",
            "platform observation receipt identity drifted",
        )

    required_terminal: dict[str, object] = {
        "disposition": "CONSUMED",
        "execution_attempted": True,
        "execution_outcome": "PASSED",
        "saved_version_id": SAVED_VERSION_ID,
        "evidence_zip_sha256": EVIDENCE_ZIP_SHA256,
        "terminal_log_sha256": TERMINAL_LOG_SHA256,
        "platform_observation_receipt_sha256": PLATFORM_RECEIPT_SHA256,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
    }
    for key, expected in required_terminal.items():
        if terminal.get(key) != expected:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_TERMINAL_DRIFT",
                f"terminal receipt drifted: {key}",
            )


def _open_validated_evidence_zip(root: Path) -> zipfile.ZipFile:
    path = _require_hash(root, EVIDENCE_ZIP_PATH, EVIDENCE_ZIP_SHA256)
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_ZIP_INVALID",
            "governed evidence ZIP is invalid",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error
    seen: set[str] = set()
    for info in archive.infolist():
        normalized = info.filename.replace("\\", "/")
        if not _member_name_is_safe(normalized) or normalized in seen:
            archive.close()
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_ZIP_UNSAFE",
                "governed evidence ZIP has unsafe or duplicate members",
                normalized,
            )
        seen.add(normalized)
    return archive


def _validate_bundle_manifest(archive: zipfile.ZipFile, bundle: dict[str, object]) -> None:
    members = bundle.get("members")
    if not isinstance(members, list):
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_BUNDLE_DRIFT",
            "bundle manifest member list is unavailable",
        )
    listed: set[str] = set()
    archive_files = {
        info.filename.replace("\\", "/"): info for info in archive.infolist() if not info.is_dir()
    }
    for raw in members:
        if not isinstance(raw, dict):
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_BUNDLE_DRIFT",
                "bundle manifest member is invalid",
            )
        path = raw.get("path")
        expected_sha = raw.get("sha256")
        expected_size = raw.get("size_bytes")
        if not isinstance(path, str) or path not in archive_files:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_BUNDLE_DRIFT",
                "bundle member path drifted",
                str(path),
            )
        payload = archive.read(archive_files[path])
        if expected_sha != _sha256_bytes(payload) or expected_size != len(payload):
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_BUNDLE_DRIFT",
                "bundle member identity drifted",
                path,
            )
        listed.add(path)
    expected_archive = listed | {"bundle_manifest_v1.json"}
    if set(archive_files) != expected_archive:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_BUNDLE_INVENTORY_DRIFT",
            "governed evidence ZIP inventory drifted",
        )


def _validate_execution_evidence(root: Path) -> None:
    archive = _open_validated_evidence_zip(root)
    try:
        summary = _zip_json(archive, "p4_p5_repetition_summary_v1.json")
        decision = _zip_json(archive, "p4_p5_repetition_decision_v1.json")
        results = _zip_json(archive, "p4_p5_repetition_request_results_v1.json")
        journal = _zip_json(archive, "pre_request_token_identity_journal_v1.json")
        runtime_ready = _zip_json(archive, "p4_p5_repetition_runtime_ready_v1.json")
        source_identity = _zip_json(archive, "runtime_source_identity_report_v1.json")
        install = _zip_json(archive, "runtime_install_report_v1.json")
        import_closure = _zip_json(archive, "runtime_import_closure_report_v1.json")
        teardown = _zip_json(archive, "worker_teardown_report_v1.json")
        cleanup = _zip_json(archive, "scratch_cleanup_report_v1.json")
        failure = _zip_json(archive, "failure_report_v1.json")
        bundle = _zip_json(archive, "bundle_manifest_v1.json")
        _validate_bundle_manifest(archive, bundle)

        required_summary = {
            "status": "DIAGNOSTIC_COMPLETE",
            "decision_state": "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED",
            "completed_request_count": 6,
            "scheduled_request_count": 6,
            "observed_model_loads": 6,
            "scheduled_model_loads": 6,
            "observed_worker_starts": 6,
            "scheduled_worker_starts": 6,
            "hidden_retries": 0,
            "external_network_requests": 0,
            "failure_class": None,
            "worker_teardown_status": "PASSED",
            "scratch_cleanup_status": "PASSED",
            "p5_requalified": False,
            "p6_requalified": False,
            "pilot_execution_performed": False,
            "measured_abc_execution_performed": False,
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        }
        for key, expected in required_summary.items():
            if summary.get(key) != expected:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_SUMMARY_DRIFT",
                    f"execution summary field drifted: {key}",
                )
        counters = summary.get("counters")
        if not isinstance(counters, dict):
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_COUNTER_DRIFT",
                "execution counters are unavailable",
            )
        expected_counters = {
            "model_requests": 6,
            "model_loads": 6,
            "worker_starts": 6,
            "hidden_retries": 0,
            "network_requests": 0,
            "benchmark_trajectory_requests": 0,
            "external_spend": 0,
            "runtime_install_attempts": 1,
            "runtime_import_closure_probes": 1,
            "kaggle_sessions": 1,
        }
        for key, expected in expected_counters.items():
            if counters.get(key) != expected:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_COUNTER_DRIFT",
                    f"execution counter drifted: {key}",
                )

        required_decision = {
            "status": "DECIDED",
            "decision_state": "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED",
            "variable_under_test": "CACHE_CONTEXT_REPETITION_COUNT",
            "control_repetition_count": 1,
            "treatment_repetition_count": 24,
            "control_exact_object_count": 3,
            "treatment_exact_object_count": 0,
            "control_valid_json_count": 3,
            "treatment_valid_json_count": 0,
            "control_intra_condition_identity_matched": True,
            "treatment_intra_condition_identity_matched": True,
            "treatment_historical_identity_matched": True,
            "fresh_worker_process_per_observation": True,
            "worker_identity_cardinality": 6,
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        }
        for key, expected in required_decision.items():
            if decision.get(key) != expected:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_DECISION_DRIFT",
                    f"decision field drifted: {key}",
                )

        rows = results.get("results")
        if not isinstance(rows, list) or len(rows) != 6:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_RESULTS_DRIFT",
                "request-result cardinality drifted",
            )
        observed_order = tuple(row.get("condition_id") for row in rows if isinstance(row, dict))
        if observed_order != REQUEST_ORDER:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_RESULTS_DRIFT",
                "request order drifted",
            )
        worker_ids: set[str] = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_RESULTS_DRIFT",
                    "request result is invalid",
                )
            if row.get("sequence_index") != index or row.get("zero_cache_baseline") is not True:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_RESULTS_DRIFT",
                    "request chronology or cold-state baseline drifted",
                )
            worker_id = row.get("worker_process_identity_sha256")
            if not isinstance(worker_id, str):
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_RESULTS_DRIFT",
                    "worker identity is unavailable",
                )
            worker_ids.add(worker_id)
            if (
                row.get("raw_prompt_retained") is not False
                or row.get("raw_output_retained") is not False
            ):
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_PRIVACY_DRIFT",
                    "raw prompt/output retention boundary drifted",
                )
            if row.get("condition_id") == "CONTROL_1X":
                expected = {
                    "repetition_count": 1,
                    "token_count": CONTROL_TOKEN_COUNT,
                    "token_sha256": CONTROL_TOKEN_SHA256,
                    "payload_sha256": CONTROL_PAYLOAD_SHA256,
                    "valid_json": True,
                    "exact_object": True,
                    "response_sha256": CONTROL_RESPONSE_SHA256,
                }
            else:
                expected = {
                    "repetition_count": 24,
                    "token_count": TREATMENT_TOKEN_COUNT,
                    "token_sha256": TREATMENT_TOKEN_SHA256,
                    "payload_sha256": TREATMENT_PAYLOAD_SHA256,
                    "valid_json": False,
                    "exact_object": False,
                    "response_sha256": TREATMENT_RESPONSE_SHA256,
                }
            for key, value in expected.items():
                if row.get(key) != value:
                    raise DispositionError(
                        "P4_P5_REPETITION_DISPOSITION_RESULTS_DRIFT",
                        f"request result field drifted: {key}",
                    )
        if len(worker_ids) != 6:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_WORKER_IDENTITY_DRIFT",
                "fresh-worker identity cardinality drifted",
            )

        entries = journal.get("entries")
        if not isinstance(entries, list) or len(entries) != 6:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_JOURNAL_DRIFT",
                "pre-request token journal cardinality drifted",
            )
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or entry.get("request_ordinal") != index:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_JOURNAL_DRIFT",
                    "pre-request token journal chronology drifted",
                )
            if entry.get("persisted_before_model_request") is not True:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_JOURNAL_DRIFT",
                    "pre-request token identity was not persisted before request",
                )
            row = rows[index - 1]
            for key in (
                "condition_id",
                "repetition_count",
                "token_count",
                "token_sha256",
                "payload_sha256",
            ):
                if entry.get(key) != row.get(key):
                    raise DispositionError(
                        "P4_P5_REPETITION_DISPOSITION_JOURNAL_DRIFT",
                        f"journal/result identity mismatch: {key}",
                    )
        if journal.get("raw_prompt_retained") is not False:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_PRIVACY_DRIFT",
                "journal raw-prompt retention boundary drifted",
            )
        if journal.get("raw_model_output_retained") is not False:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_PRIVACY_DRIFT",
                "journal raw-output retention boundary drifted",
            )

        if runtime_ready.get("status") != "PASSED":
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_RUNTIME_DRIFT",
                "runtime-ready status drifted",
            )
        if source_identity.get("executed_runtime_script_sha256") != RUNTIME_SHA256:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_RUNTIME_DRIFT",
                "executed runtime source identity drifted",
            )
        if source_identity.get("wrapper_hash_verification_passed") is not True:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_RUNTIME_DRIFT",
                "wrapper runtime hash verification drifted",
            )
        if install.get("status") != "PASSED" or install.get("returncode") != 0:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_INSTALL_DRIFT",
                "runtime installation result drifted",
            )
        required_import = {
            "status": "PASSED",
            "decision": "PROCESS_TREE_IMPORT_CLOSURE_PASSED",
            "returncode": 0,
            "hidden_retry_count": 0,
            "network_access_requested": False,
            "model_loads_consumed": 0,
            "all_critical_origins_within_target_site": True,
        }
        for key, expected in required_import.items():
            if import_closure.get(key) != expected:
                raise DispositionError(
                    "P4_P5_REPETITION_DISPOSITION_IMPORT_DRIFT",
                    f"runtime import-closure field drifted: {key}",
                )
        if teardown.get("status") != "PASSED":
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_TEARDOWN_DRIFT",
                "worker teardown drifted",
            )
        if teardown.get("observed_teardown_count") != 6:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_TEARDOWN_DRIFT",
                "worker teardown count drifted",
            )
        if cleanup.get("status") != "PASSED" or cleanup.get("scratch_exists_after") is not False:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_CLEANUP_DRIFT",
                "scratch cleanup drifted",
            )
        if failure.get("status") != "NOT_APPLICABLE" or failure.get("failure_class") is not None:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_FAILURE_DRIFT",
                "failure-report boundary drifted",
            )
    finally:
        archive.close()


def _validate_terminal_log(root: Path) -> None:
    log = _require_hash(root, TERMINAL_LOG_PATH, TERMINAL_LOG_SHA256)
    text = log.read_text(encoding="utf-8", errors="replace")
    markers = (
        f'"transaction_id":"{TRANSACTION_ID}"',
        '"decision_state":"LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"',
        '"completed_request_count":6',
        '"model_loads":6',
        '"model_requests":6',
        '"worker_starts":6',
        '"hidden_retries":0',
        '"network_requests":0',
        '"status":"DIAGNOSTIC_COMPLETE"',
    )
    for marker in markers:
        if marker not in text:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_LOG_DRIFT",
                "terminal log no longer contains required governed marker",
                TERMINAL_LOG_PATH.as_posix(),
            )


def _validate_all(root: Path) -> CustodyManifest:
    custody = _validate_custody(root)
    _validate_authority_chain(root)
    _validate_lifecycle(root)
    _validate_execution_evidence(root)
    _validate_terminal_log(root)
    _require_hash(root, NOTEBOOK_PATH, NOTEBOOK_SHA256)
    return custody


def build_record(repo_root: Path) -> DispositionRecord:
    root = repo_root.resolve()
    _validate_all(root)
    authorities = (
        _receipt(root, "custody_manifest", CUSTODY_MANIFEST_PATH),
        _receipt(root, "governed_evidence_zip", EVIDENCE_ZIP_PATH),
        _receipt(root, "terminal_log", TERMINAL_LOG_PATH),
        _receipt(root, "saved_notebook", NOTEBOOK_PATH),
        _receipt(root, "execution_authorization", AUTHORIZATION_PATH),
        _receipt(root, "execution_artifact_manifest", EXECUTION_MANIFEST_PATH),
        _receipt(root, "platform_observation_receipt", PLATFORM_RECEIPT_PATH),
        _receipt(root, "authorization_terminal_receipt", TERMINAL_RECEIPT_PATH),
        _receipt(root, "runtime_payload", RUNTIME_PATH),
        _receipt(root, "implementation_record", IMPLEMENTATION_RECORD_PATH),
        _receipt(root, "implementation_review", IMPLEMENTATION_REVIEW_PATH),
        _receipt(root, "authorization_design_record", AUTHORIZATION_DESIGN_RECORD_PATH),
        _receipt(root, "issuer_source", ISSUER_SOURCE_PATH),
        _receipt(root, "generator_contract", GENERATOR_CONTRACT_PATH),
    )
    return DispositionRecord(
        schema_version="1.0.0",
        record_id="auragateway-p4-p5-cache-context-repetition-differential-disposition-v1",
        status="DISPOSITIONED_VALID_GOVERNED_REPETITION_DIFFERENTIAL",
        transaction_id=TRANSACTION_ID,
        saved_version_id=SAVED_VERSION_ID,
        terminal_disposition="CONSUMED",
        execution_outcome="PASSED",
        diagnostic_status="DIAGNOSTIC_COMPLETE",
        decision_state="LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED",
        variable_under_test="CACHE_CONTEXT_REPETITION_COUNT",
        control_repetition_count=1,
        treatment_repetition_count=24,
        observations_per_condition=3,
        control_exact_object_count=3,
        treatment_exact_object_count=0,
        control_valid_json_count=3,
        treatment_valid_json_count=0,
        control_intra_condition_identity_matched=True,
        treatment_intra_condition_identity_matched=True,
        treatment_historical_identity_matched=True,
        fresh_worker_process_per_observation=True,
        worker_identity_cardinality=6,
        runtime_source_identity_verified=True,
        runtime_installation_passed=True,
        runtime_import_closure_passed=True,
        model_requests_performed=6,
        model_loads_performed=6,
        worker_starts_performed=6,
        hidden_retries_performed=0,
        external_network_requests_performed=0,
        benchmark_trajectory_requests_performed=0,
        external_spend=0,
        teardown_passed=True,
        scratch_cleanup_passed=True,
        raw_prompt_retained=False,
        raw_model_output_retained=False,
        p5_requalified=False,
        p6_requalified=False,
        measured_abc_execution_performed=False,
        pilot_execution_performed=False,
        long_repeated_24x_condition_necessary_relative_to_1x_established=True,
        exact_repetition_threshold_established=False,
        repetition_alone_established_causal=False,
        context_length_alone_established_causal=False,
        exact_root_cause_established=False,
        prefix_cache_defect_established=False,
        new_execution_authorized=False,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        causal_classification="LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED",
        specific_classification=(
            "FROZEN_24X_CONDITION_NECESSARY_RELATIVE_TO_1X_FOR_CURRENT_C3_REGRESSION"
        ),
        causal_confidence="PREDECLARED_COUNTERFACTUAL_DIFFERENTIAL_WITHIN_FROZEN_RUNTIME",
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        governed_evidence_zip_sha256=EVIDENCE_ZIP_SHA256,
        authorities=authorities,
        non_claims=(
            "The exact repetition threshold is not established.",
            (
                "Repetition count alone is not established as causal because total context "
                "magnitude covaries."
            ),
            "Context length alone is not established as causal.",
            "The exact root cause of the C3 regression is not established.",
            "A prefix-cache defect is not established.",
            "P5 is not requalified by this diagnostic.",
            "P6 is not requalified by this diagnostic.",
            "Measured North-Star A/B/C execution was not performed.",
            "No new runtime or Kaggle execution is authorized by this disposition.",
            "The consumed authorization is not reusable and unchanged replay is unauthorized.",
        ),
        next_gate=NEXT_GATE,
    )


def expected_outputs(repo_root: Path) -> tuple[bytes, bytes]:
    record = build_record(repo_root)
    record_bytes = _canonical_json_bytes(record)
    review = DispositionReview(
        schema_version="1.0.0",
        review_id=("auragateway-p4-p5-cache-context-repetition-differential-disposition-v1-review"),
        status="APPROVED_GOVERNED_REPETITION_DIFFERENTIAL_DISPOSITION",
        record_sha256=_sha256_bytes(record_bytes),
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        positive_necessity_result_accepted=True,
        exact_threshold_claimed=False,
        exact_root_cause_claimed=False,
        p5_requalification_claimed=False,
        p6_requalification_claimed=False,
        measured_abc_claimed=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    return record_bytes, _canonical_json_bytes(review)


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record_bytes, review_bytes = expected_outputs(root)
    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)
    review_path.write_bytes(review_bytes)
    return {
        "status": "P4_P5_REPETITION_DIFFERENTIAL_DISPOSITION_GENERATED",
        "record_sha256": _sha256_bytes(record_bytes),
        "review_sha256": _sha256_bytes(review_bytes),
        "transaction_id": TRANSACTION_ID,
        "saved_version_id": SAVED_VERSION_ID,
        "decision_state": "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED",
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_record, expected_review = expected_outputs(root)
    record_path = _require_file(root, RECORD_PATH)
    review_path = _require_file(root, REVIEW_PATH)
    if record_path.read_bytes() != expected_record:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_RECORD_DRIFT",
            "checked-in disposition record drifted",
            RECORD_PATH.as_posix(),
        )
    if review_path.read_bytes() != expected_review:
        raise DispositionError(
            "P4_P5_REPETITION_DISPOSITION_REVIEW_DRIFT",
            "checked-in disposition review drifted",
            REVIEW_PATH.as_posix(),
        )
    record = DispositionRecord.model_validate_json(expected_record)
    return {
        "status": "P4_P5_REPETITION_DIFFERENTIAL_DISPOSITION_VALID",
        "record_sha256": _sha256_bytes(expected_record),
        "review_sha256": _sha256_bytes(expected_review),
        "transaction_id": record.transaction_id,
        "saved_version_id": record.saved_version_id,
        "decision_state": record.decision_state,
        "exact_repetition_threshold_established": record.exact_repetition_threshold_established,
        "exact_root_cause_established": record.exact_root_cause_established,
        "p5_requalified": record.p5_requalified,
        "p6_requalified": record.p6_requalified,
        "new_execution_authorized": record.new_execution_authorized,
        "next_gate": record.next_gate,
    }


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result: dict[str, object] | None = None
        if args.command == "generate":
            result = generate(Path(args.repo_root))
        if args.command == "validate":
            result = validate(Path(args.repo_root))
        if result is None:
            raise DispositionError(
                "P4_P5_REPETITION_DISPOSITION_COMMAND_INVALID",
                "disposition command was not handled",
            )
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0
    except (DispositionError, ValidationError) as error:
        if isinstance(error, DispositionError):
            payload = error.envelope()
        else:
            payload = {
                "error_code": "P4_P5_REPETITION_DISPOSITION_SCHEMA_INVALID",
                "safe_message": "disposition schema validation failed",
                "path": None,
            }
        print(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
