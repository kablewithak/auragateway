"""Accept one governed explicit Triton attention-backend V1 execution."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
import zipfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

INTEGRATION_BASE_MAIN_COMMIT: Final = "ffa5e40853e84d1d4e38e77f90d20227d0f642ba"
IMPLEMENTATION_FEATURE_COMMIT: Final = "dc9484492169965e0ed17d77bf1894d1ae9e7cb8"
AUTHORIZATION_ISSUER_FEATURE_COMMIT: Final = "3da0fc6c97f74243d674a08903bf397fbc3fbcca"
IMPLEMENTATION_SOURCE_MAIN_COMMIT: Final = "81597c1ebc6add70f6c35e3f2287acba9c078519"

NOTEBOOK_NAME: Final = "ag-cu129-triton-attention-backend-v1"
NOTEBOOK_SHA256: Final = "cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208"
SAVED_VERSION_ID: Final = 339181603
SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-triton-attention-backend-v1/log"
    "?scriptVersionId=339181603"
)

LOG_SHA256: Final = "0e74f803b508d9f2255582d7c7192e33bf0ec267e32d1be199b0df025af1db38"
EVIDENCE_ZIP_SHA256: Final = "858e84c68703850fcd1651575bbc8223b01f46d5a8aaf39cec7fa91c0c65b3a9"
AUTHORIZATION_SHA256: Final = "e3e4a84f4b704ee1594e236c7fc4b152f70928e634bf456d35295ff0e9d96782"
CONSUMPTION_SHA256: Final = "e21591d2f5f2104c36c929513817c789af927318f36290acda6c3a166ad79f07"
INSPECTION_MANIFEST_SHA256: Final = (
    "1574441b29db206e3805524e66cb7c5b8b03d10999bc27ec3a2ae333112f0c6f"
)

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-explicit-triton-attention-backend-execution-acceptance-v1"
)
LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-triton-attention-backend-v1-339181603.log")
EVIDENCE_ZIP_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-triton-attention-evidence-v1-339181603.zip")
AUTHORIZATION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / ("execution_authorization_v1-339181603.json")
CONSUMPTION_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "execution_authorization_consumption_v1-339181603.json"
)
INSPECTION_MANIFEST_PATH: Final = EVIDENCE_ROOT / ("inspection_manifest_v1-339181603.json")
ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_explicit_triton_attention_backend_"
    "execution_acceptance_v1.json"
)
OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_explicit_triton_attention_backend_"
    "execution_authorization_v1.json"
)
OPERATIONAL_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_explicit_triton_attention_backend_"
    "execution_authorization_consumption_v1.json"
)

PLATFORM_MEMBER: Final = "platform_identity_report_v1.json"
DISCOVERY_MEMBER: Final = "backend_discovery_report_v1.json"
IMPORT_MEMBER: Final = "backend_import_report_v1.json"
CAPABILITY_MEMBER: Final = "backend_capability_report_v1.json"
PRIMITIVE_MEMBER: Final = "attention_primitive_report_v1.json"
SUMMARY_MEMBER: Final = "explicit_triton_attention_backend_summary_v1.json"
MANIFEST_MEMBER: Final = "bundle_manifest_v1.json"
HUMAN_MEMBER: Final = "human_report_v1.md"

EXPECTED_ZIP_MEMBERS: Final = (
    PLATFORM_MEMBER,
    DISCOVERY_MEMBER,
    IMPORT_MEMBER,
    CAPABILITY_MEMBER,
    PRIMITIVE_MEMBER,
    SUMMARY_MEMBER,
    MANIFEST_MEMBER,
    HUMAN_MEMBER,
)
EXPECTED_MEMBER_SHA256: Final = {
    PLATFORM_MEMBER: ("4a39fb35f07ca504a20037bb448708f887213d24e1e258a37252cb3c9bd8aaee"),
    DISCOVERY_MEMBER: ("ec45b7491b8f399e40140fd18d719e233082124218f5ad7aac3d7f59b47224a3"),
    IMPORT_MEMBER: ("41ea2be647253fe5b31baaddd0a50974935e7dd0341e77e619c2aad7d1da44a0"),
    CAPABILITY_MEMBER: ("1a4188b5ae4c68547112f41b3817c2faff5355315e11d8e0209b2c9ed720026d"),
    PRIMITIVE_MEMBER: ("80f60438ddec975184e770900e7f79778c484f60e235824b3483fc8c74082c44"),
    SUMMARY_MEMBER: ("295cf1b7101dbebf0e2725b99a79d4448e9c89679f48ceb47fc61284b59d0616"),
    MANIFEST_MEMBER: ("803b54fac19f7b6bf9c6b3415562658f9df73bec7153a473503ea84653ced2a9"),
    HUMAN_MEMBER: ("92a37b3a975430c0631b8a66e8064885307d7260c44549391b008793c20f3bf8"),
}
EXPECTED_MEMBER_SIZES: Final = {
    PLATFORM_MEMBER: 764,
    DISCOVERY_MEMBER: 347,
    IMPORT_MEMBER: 1381,
    CAPABILITY_MEMBER: 363,
    PRIMITIVE_MEMBER: 680,
    SUMMARY_MEMBER: 81776,
    MANIFEST_MEMBER: 1196,
    HUMAN_MEMBER: 447,
}


class AttentionBackendAcceptanceError(RuntimeError):
    """Fail-closed Q6 evidence-acceptance error."""

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

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(LocalABCContract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceFile(_StrictModel):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class ZipMember(_StrictModel):
    name: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class SavedVersion(_StrictModel):
    notebook_name: Literal["ag-cu129-triton-attention-backend-v1"]
    notebook_sha256: Literal["cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208"]
    saved_version_id: Literal[339181603]
    saved_version_url: str
    log: EvidenceFile
    evidence_archive: EvidenceFile


class AuthorizationLifecycle(_StrictModel):
    authorization_sha256: Literal[
        "e3e4a84f4b704ee1594e236c7fc4b152f70928e634bf456d35295ff0e9d96782"
    ]
    consumption_sha256: Literal["e21591d2f5f2104c36c929513817c789af927318f36290acda6c3a166ad79f07"]
    issued_from_main_commit: Literal["ffa5e40853e84d1d4e38e77f90d20227d0f642ba"]
    issued_at: datetime
    expires_at: datetime
    evidence_captured_at: datetime
    consumed_at: datetime
    scope: Literal["MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1"]
    single_use: Literal[True]
    outcome: Literal["PASSED"]
    authorization_reusable: Literal[False]
    execution_evidence_within_authorization_window: Literal[True]

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if not self.issued_at <= self.evidence_captured_at < self.expires_at:
            raise ValueError("execution evidence is outside the authorization window")
        if self.consumed_at < self.evidence_captured_at:
            raise ValueError("authorization consumption predates execution evidence")
        return self


class PlatformContract(_StrictModel):
    status: Literal["PASSED"]
    decision: Literal["ATTENTION_BACKEND_PLATFORM_PREFLIGHT_PASSED"]
    gpu_count: Literal[2]
    gpu_names: tuple[Literal["Tesla T4"], Literal["Tesla T4"]]
    compute_capabilities: tuple[
        tuple[Literal[7], Literal[5]],
        tuple[Literal[7], Literal[5]],
    ]
    base_torch_version: Literal["2.10.0+cu128"]
    base_cuda_build: Literal["12.8"]
    cuda_available: Literal[True]


class BackendContract(_StrictModel):
    registry_enum: Literal["AttentionBackendEnum.TRITON_ATTN"]
    backend_path: Literal["vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"]
    backend_class: Literal["vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"]
    backend_name: Literal["TRITON_ATTN"]
    registry_overridden: Literal[False]
    all_origins_inside_target: Literal[True]
    vllm_version: Literal["0.19.1"]
    torch_version: Literal["2.10.0+cu129"]
    torch_cuda_build: Literal["12.9"]
    triton_version: Literal["3.6.0"]


class CapabilityContract(_StrictModel):
    status: Literal["PASSED"]
    device_name: Literal["Tesla T4"]
    compute_capability: tuple[Literal[7], Literal[5]]
    attention_type: Literal["decoder"]
    dtype: Literal["float16"]
    head_size: Literal[64]
    block_size: Literal[16]
    kv_cache_dtype: Literal["auto"]
    invalid_reasons: tuple[str, ...] = Field(max_length=0)


class PrimitiveContract(_StrictModel):
    status: Literal["PASSED"]
    decision: Literal["ATTENTION_BACKEND_PRIMITIVE_PASSED"]
    module: Literal["vllm.v1.attention.ops.triton_prefill_attention"]
    name: Literal["context_attention_fwd"]
    backend_owns_exact_primitive: Literal[True]
    result_close: Literal[True]
    causal: Literal[False]
    sequence_length: Literal[8]
    num_heads: Literal[2]
    head_size: Literal[64]
    maximum_absolute_error: float
    atol: float
    rtol: float

    @model_validator(mode="after")
    def validate_numeric_identity(self) -> Self:
        observed = (
            self.maximum_absolute_error,
            self.atol,
            self.rtol,
        )
        expected = (0.00048828125, 0.03, 0.03)
        if observed != expected:
            raise ValueError("primitive numerical contract drifted")
        return self


class SafetyContract(_StrictModel):
    runtime_install_attempts: Literal[1]
    backend_discovery_attempts: Literal[1]
    backend_import_attempts: Literal[1]
    backend_capability_validation_attempts: Literal[1]
    attention_primitive_attempts: Literal[1]
    model_loads: Literal[0]
    worker_starts: Literal[0]
    model_requests: Literal[0]
    benchmark_trajectory_requests: Literal[0]
    network_requests: Literal[0]
    hidden_retries_performed: Literal[0]
    global_environment_mutations_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    external_spend: Literal[0]


class AttentionBackendExecutionAcceptanceRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-cu129-explicit-triton-attention-backend-execution-acceptance-v1"
    ]
    status: Literal["EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_VALID"]
    integration_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_issuer_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    saved_version: SavedVersion
    authorization_lifecycle: AuthorizationLifecycle
    zip_members: tuple[ZipMember, ...]
    platform: PlatformContract
    backend: BackendContract
    capability: CapabilityContract
    primitive: PrimitiveContract
    safety: SafetyContract
    terminal_decision: Literal["EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED"]
    q6_execution_accepted: Literal[True]
    authorization_lifecycle_closed: Literal[True]
    unchanged_replay_authorized: Literal[False]
    p3_p6_runtime_diagnostic_implementation_authorized: Literal[True]
    next_gate: Literal["design_and_implement_p3_p6_runtime_diagnostic_v1"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.integration_base_main_commit != INTEGRATION_BASE_MAIN_COMMIT:
            raise ValueError("integration base main commit drifted")
        if self.implementation_feature_commit != IMPLEMENTATION_FEATURE_COMMIT:
            raise ValueError("implementation feature commit drifted")
        if self.authorization_issuer_feature_commit != AUTHORIZATION_ISSUER_FEATURE_COMMIT:
            raise ValueError("authorization issuer feature commit drifted")
        if self.implementation_source_main_commit != IMPLEMENTATION_SOURCE_MAIN_COMMIT:
            raise ValueError("implementation source main commit drifted")
        if self.saved_version.saved_version_url != SAVED_VERSION_URL:
            raise ValueError("saved-version URL drifted")
        return self


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_TEMP_PRESENT",
            "temporary generated path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _read_bound_file(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
) -> bytes:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_EVIDENCE_UNSAFE",
            "required evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_IDENTITY_DRIFT",
            "evidence identity drifted",
            relative_path.as_posix(),
        )
    return payload


def _json_object(payload: bytes, path: str) -> dict[str, object]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_JSON_INVALID",
            "required evidence JSON is invalid",
            path,
        ) from error
    if not isinstance(raw, dict):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_JSON_ROOT_INVALID",
            "evidence JSON root must be one object",
            path,
        )
    return {str(key): value for key, value in raw.items()}


def _mapping(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_OBJECT_REQUIRED",
            "required evidence value must be one object",
            path,
        )
    return {str(key): nested for key, nested in value.items()}


def _sequence(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_ARRAY_REQUIRED",
            "required evidence value must be one array",
            path,
        )
    return list(value)


def _require_equal(
    observed: object,
    expected: object,
    error_code: str,
    path: str,
) -> None:
    if observed != expected:
        raise AttentionBackendAcceptanceError(
            error_code,
            "evidence semantic state drifted",
            path,
        )


def _parse_datetime(value: object, path: str) -> datetime:
    if not isinstance(value, str):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_TIME_INVALID",
            "evidence timestamp must be one string",
            path,
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_TIME_INVALID",
            "evidence timestamp is invalid",
            path,
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_TIME_NAIVE",
            "evidence timestamp must be timezone-aware",
            path,
        )
    return parsed.astimezone(UTC)


def _safe_zip_members(payload: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise AttentionBackendAcceptanceError(
                    "ATTENTION_BACKEND_ACCEPTANCE_DUPLICATE_MEMBER",
                    "evidence ZIP contains duplicate members",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )
            if set(names) != set(EXPECTED_ZIP_MEMBERS):
                raise AttentionBackendAcceptanceError(
                    "ATTENTION_BACKEND_ACCEPTANCE_MEMBER_SET_DRIFT",
                    "evidence ZIP member set drifted",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )

            members: dict[str, bytes] = {}
            for info in infos:
                member_path = PurePosixPath(info.filename)
                mode = info.external_attr >> 16
                unsafe = (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or member_path.name != info.filename
                    or info.is_dir()
                    or stat.S_ISLNK(mode)
                )
                if unsafe:
                    raise AttentionBackendAcceptanceError(
                        "ATTENTION_BACKEND_ACCEPTANCE_UNSAFE_MEMBER",
                        "evidence ZIP contains an unsafe member",
                        info.filename,
                    )
                member = archive.read(info)
                if (
                    _sha256_bytes(member) != EXPECTED_MEMBER_SHA256[info.filename]
                    or len(member) != EXPECTED_MEMBER_SIZES[info.filename]
                ):
                    raise AttentionBackendAcceptanceError(
                        "ATTENTION_BACKEND_ACCEPTANCE_MEMBER_DRIFT",
                        "evidence ZIP member identity drifted",
                        info.filename,
                    )
                members[info.filename] = member
            return members
    except zipfile.BadZipFile as error:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_BAD_ZIP",
            "evidence archive is not a valid ZIP",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error


def _validate_log(payload: bytes) -> dict[str, object]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_LOG_INVALID",
            "execution log is not UTF-8",
            LOG_PATH.as_posix(),
        ) from error
    candidates: list[dict[str, object]] = []
    for line in text.splitlines():
        brace = line.find("{")
        if brace < 0:
            continue
        try:
            raw = json.loads(line[brace:])
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            candidates.append({str(key): value for key, value in raw.items()})
    if len(candidates) != 1:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_LOG_TERMINAL_COUNT",
            "execution log must contain one terminal JSON object",
            LOG_PATH.as_posix(),
        )
    terminal = candidates[0]
    exact = {
        "status": "PASSED",
        "terminal_decision": "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED",
        "evidence_zip_sha256": EVIDENCE_ZIP_SHA256,
        "runtime_install_attempts": 1,
        "backend_import_attempts": 1,
        "attention_primitive_attempts": 1,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "hidden_retries_performed": 0,
        "global_environment_mutations_performed": 0,
        "external_spend": 0,
    }
    for key, value in exact.items():
        _require_equal(
            terminal.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_LOG_DRIFT",
            f"{LOG_PATH.as_posix()}.{key}",
        )
    return terminal


def _validate_inspection_manifest(payload: bytes) -> None:
    raw = _json_object(payload, INSPECTION_MANIFEST_PATH.as_posix())
    exact = {
        "schema_version": "1.0.0",
        "package_id": "auragateway-q6-triton-attention-execution-inspection-v1",
        "repository_head": INTEGRATION_BASE_MAIN_COMMIT,
        "saved_version_id": SAVED_VERSION_ID,
        "saved_version_url": SAVED_VERSION_URL,
        "outcome": "PASSED",
        "terminal_decision": "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED",
        "authorization_sha256": AUTHORIZATION_SHA256,
        "consumption_sha256": CONSUMPTION_SHA256,
        "evidence_zip_sha256": EVIDENCE_ZIP_SHA256,
        "complete_log_sha256": LOG_SHA256,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
    }
    for key, value in exact.items():
        _require_equal(
            raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_INSPECTION_DRIFT",
            f"{INSPECTION_MANIFEST_PATH.as_posix()}.{key}",
        )
    _parse_datetime(
        raw.get("created_at_utc"),
        f"{INSPECTION_MANIFEST_PATH.as_posix()}.created_at_utc",
    )


def _validate_authorization(
    authorization_payload: bytes,
    consumption_payload: bytes,
) -> tuple[dict[str, object], dict[str, object]]:
    authorization = _json_object(
        authorization_payload,
        AUTHORIZATION_EVIDENCE_PATH.as_posix(),
    )
    consumption = _json_object(
        consumption_payload,
        CONSUMPTION_EVIDENCE_PATH.as_posix(),
    )
    if authorization_payload != _canonical_json(authorization).encode("utf-8"):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_AUTHORIZATION_NONCANONICAL",
            "preserved authorization is not canonical JSON",
            AUTHORIZATION_EVIDENCE_PATH.as_posix(),
        )
    if consumption_payload != _canonical_json(consumption).encode("utf-8"):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_CONSUMPTION_NONCANONICAL",
            "preserved consumption receipt is not canonical JSON",
            CONSUMPTION_EVIDENCE_PATH.as_posix(),
        )

    authorization_exact = {
        "authorization_id": (
            "auragateway-cu129-explicit-triton-attention-backend-execution-authorization-v1"
        ),
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": "MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1",
        "source_main_merge_commit": "6ede70538c52165d92a1df68e2c8bbc97a123c49",
        "implementation_feature_commit": IMPLEMENTATION_FEATURE_COMMIT,
        "notebook_sha256": NOTEBOOK_SHA256,
        "issued_from_main_commit": INTEGRATION_BASE_MAIN_COMMIT,
        "operator_confirmation_recorded": True,
        "single_use": True,
        "successful_or_failed_attempt_consumes_authorization": True,
        "unchanged_replay_authorized": False,
    }
    for key, value in authorization_exact.items():
        _require_equal(
            authorization.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_AUTHORIZATION_DRIFT",
            f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.{key}",
        )

    budget = _mapping(
        authorization.get("budget"),
        f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.budget",
    )
    expected_budget = {
        "maximum_attention_primitive_attempts": 1,
        "maximum_authorization_window_minutes": 240,
        "maximum_backend_capability_validation_attempts": 1,
        "maximum_backend_discovery_attempts": 1,
        "maximum_backend_import_attempts": 1,
        "maximum_benchmark_trajectory_requests": 0,
        "maximum_external_spend": 0,
        "maximum_kaggle_sessions": 1,
        "maximum_model_loads": 0,
        "maximum_model_requests": 0,
        "maximum_network_requests": 0,
        "maximum_platform_preflight_attempts": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_worker_starts": 0,
    }
    _require_equal(
        budget,
        expected_budget,
        "ATTENTION_BACKEND_ACCEPTANCE_AUTHORIZATION_BUDGET_DRIFT",
        f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.budget",
    )

    controls = _mapping(
        authorization.get("controls"),
        f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.controls",
    )
    expected_controls = {
        "credentials_permitted": False,
        "cuda_toolkit_stub_permitted": False,
        "customer_data_permitted": False,
        "filesystem_mutation_scope": "KAGGLE_WORKING_DIRECTORY_ONLY",
        "global_environment_mutation_permitted": False,
        "hidden_retries_permitted": False,
        "internet_enabled": False,
        "measured_execution_authorized": False,
        "network_access_permitted": False,
        "silent_backend_fallback_permitted": False,
    }
    _require_equal(
        controls,
        expected_controls,
        "ATTENTION_BACKEND_ACCEPTANCE_AUTHORIZATION_CONTROL_DRIFT",
        f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.controls",
    )

    consumption_exact = {
        "authorization_id": authorization_exact["authorization_id"],
        "authorization_sha256": AUTHORIZATION_SHA256,
        "lifecycle": "CONSUMED",
        "outcome": "PASSED",
        "saved_version_id": SAVED_VERSION_ID,
        "notebook_sha256": NOTEBOOK_SHA256,
        "authorization_reusable": False,
        "next_gate": ("preserve_and_accept_explicit_triton_attention_backend_evidence_v1"),
    }
    for key, value in consumption_exact.items():
        _require_equal(
            consumption.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_CONSUMPTION_DRIFT",
            f"{CONSUMPTION_EVIDENCE_PATH.as_posix()}.{key}",
        )
    return authorization, consumption


def _validate_manifest(
    members: Mapping[str, bytes],
) -> tuple[ZipMember, ...]:
    raw = _json_object(members[MANIFEST_MEMBER], MANIFEST_MEMBER)
    exact = {
        "schema_version": "1.0.0",
        "bundle_id": "auragateway-cu129-triton-attention-evidence-v1",
        "probe_id": "auragateway-cu129-explicit-triton-attention-backend-v1",
        "source_main_commit": IMPLEMENTATION_SOURCE_MAIN_COMMIT,
    }
    for key, value in exact.items():
        _require_equal(
            raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_MANIFEST_AUTHORITY_DRIFT",
            f"{MANIFEST_MEMBER}.{key}",
        )

    entries = _sequence(raw.get("members"), f"{MANIFEST_MEMBER}.members")
    observed: set[str] = set()
    for index, entry_value in enumerate(entries):
        entry = _mapping(
            entry_value,
            f"{MANIFEST_MEMBER}.members[{index}]",
        )
        name = entry.get("path")
        sha256 = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(name, str)
            or not isinstance(sha256, str)
            or isinstance(size_bytes, bool)
            or not isinstance(size_bytes, int)
        ):
            raise AttentionBackendAcceptanceError(
                "ATTENTION_BACKEND_ACCEPTANCE_MANIFEST_ENTRY_INVALID",
                "bundle manifest entry fields are invalid",
                str(index),
            )
        if name in observed or name == MANIFEST_MEMBER:
            raise AttentionBackendAcceptanceError(
                "ATTENTION_BACKEND_ACCEPTANCE_MANIFEST_ENTRY_DUPLICATE",
                "bundle manifest entry is duplicated or self-referential",
                name,
            )
        if (
            name not in members
            or sha256 != EXPECTED_MEMBER_SHA256[name]
            or size_bytes != EXPECTED_MEMBER_SIZES[name]
            or _sha256_bytes(members[name]) != sha256
            or len(members[name]) != size_bytes
        ):
            raise AttentionBackendAcceptanceError(
                "ATTENTION_BACKEND_ACCEPTANCE_MANIFEST_BINDING_DRIFT",
                "bundle manifest member binding drifted",
                name,
            )
        observed.add(name)

    expected = set(EXPECTED_ZIP_MEMBERS) - {MANIFEST_MEMBER}
    if observed != expected:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_MANIFEST_SET_DRIFT",
            "bundle manifest bound-member set drifted",
            MANIFEST_MEMBER,
        )

    return tuple(
        ZipMember(
            name=name,
            sha256=EXPECTED_MEMBER_SHA256[name],
            size_bytes=EXPECTED_MEMBER_SIZES[name],
        )
        for name in sorted(EXPECTED_ZIP_MEMBERS)
    )


def _contracts(
    members: Mapping[str, bytes],
) -> tuple[
    PlatformContract,
    BackendContract,
    CapabilityContract,
    PrimitiveContract,
    SafetyContract,
    datetime,
]:
    platform_raw = _json_object(members[PLATFORM_MEMBER], PLATFORM_MEMBER)
    discovery_raw = _json_object(members[DISCOVERY_MEMBER], DISCOVERY_MEMBER)
    import_raw = _json_object(members[IMPORT_MEMBER], IMPORT_MEMBER)
    capability_raw = _json_object(members[CAPABILITY_MEMBER], CAPABILITY_MEMBER)
    primitive_raw = _json_object(members[PRIMITIVE_MEMBER], PRIMITIVE_MEMBER)
    summary_raw = _json_object(members[SUMMARY_MEMBER], SUMMARY_MEMBER)

    platform_exact = {
        "status": "PASSED",
        "decision": "ATTENTION_BACKEND_PLATFORM_PREFLIGHT_PASSED",
        "gpu_count": 2,
        "gpu_names": ["Tesla T4", "Tesla T4"],
        "compute_capabilities": [[7, 5], [7, 5]],
        "base_torch_version": "2.10.0+cu128",
        "base_cuda_build": "12.8",
        "cuda_available": True,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
    }
    for key, value in platform_exact.items():
        _require_equal(
            platform_raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_PLATFORM_DRIFT",
            f"{PLATFORM_MEMBER}.{key}",
        )

    discovery_exact = {
        "status": "PASSED",
        "registry_enum": "AttentionBackendEnum.TRITON_ATTN",
        "backend_path": ("vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"),
        "registry_overridden": False,
    }
    for key, value in discovery_exact.items():
        _require_equal(
            discovery_raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_DISCOVERY_DRIFT",
            f"{DISCOVERY_MEMBER}.{key}",
        )

    import_exact = {
        "status": "PASSED",
        "backend_class": discovery_exact["backend_path"],
        "backend_name": "TRITON_ATTN",
        "all_origins_inside_target": True,
        "vllm_distribution_version": "0.19.1",
        "torch_version": "2.10.0+cu129",
        "torch_cuda_build": "12.9",
        "triton_distribution_version": "3.6.0",
    }
    for key, value in import_exact.items():
        _require_equal(
            import_raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_IMPORT_DRIFT",
            f"{IMPORT_MEMBER}.{key}",
        )
    origins = _mapping(import_raw.get("module_origins"), f"{IMPORT_MEMBER}.origins")
    target_prefix = (
        "/kaggle/working/explicit_triton_attention_backend_v1/target_runtime/site-packages/"
    )
    if not origins or any(
        not isinstance(value, str) or not value.startswith(target_prefix)
        for value in origins.values()
    ):
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_IMPORT_ORIGIN_DRIFT",
            "one or more imported modules originated outside the target runtime",
            IMPORT_MEMBER,
        )

    capability_exact = {
        "status": "PASSED",
        "device_name": "Tesla T4",
        "compute_capability": [7, 5],
        "attention_type": "decoder",
        "dtype": "float16",
        "head_size": 64,
        "block_size": 16,
        "kv_cache_dtype": "auto",
        "invalid_reasons": [],
    }
    for key, value in capability_exact.items():
        _require_equal(
            capability_raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_CAPABILITY_DRIFT",
            f"{CAPABILITY_MEMBER}.{key}",
        )

    primitive_exact = {
        "status": "PASSED",
        "decision": "ATTENTION_BACKEND_PRIMITIVE_PASSED",
        "module": "vllm.v1.attention.ops.triton_prefill_attention",
        "name": "context_attention_fwd",
        "backend_owns_exact_primitive": True,
        "result_close": True,
        "causal": False,
        "sequence_length": 8,
        "num_heads": 2,
        "head_size": 64,
        "maximum_absolute_error": 0.00048828125,
        "atol": 0.03,
        "rtol": 0.03,
    }
    for key, value in primitive_exact.items():
        _require_equal(
            primitive_raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_PRIMITIVE_DRIFT",
            f"{PRIMITIVE_MEMBER}.{key}",
        )

    summary_exact = {
        "schema_version": "1.0.0",
        "probe_id": "auragateway-cu129-explicit-triton-attention-backend-v1",
        "source_main_commit": IMPLEMENTATION_SOURCE_MAIN_COMMIT,
        "status": "PASSED",
        "terminal_decision": "EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED",
        "next_gate": "preserve_evidence_and_accept_attention_backend_execution",
        "stop_on_first_failure": True,
        "failure": None,
        "runtime_install_attempts": 1,
        "backend_discovery_attempts": 1,
        "backend_import_attempts": 1,
        "backend_capability_validation_attempts": 1,
        "attention_primitive_attempts": 1,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "hidden_retries_performed": 0,
        "global_environment_mutations_performed": 0,
        "credentials_used": False,
        "customer_data_present": False,
        "external_spend": 0,
    }
    for key, value in summary_exact.items():
        _require_equal(
            summary_raw.get(key),
            value,
            "ATTENTION_BACKEND_ACCEPTANCE_SUMMARY_DRIFT",
            f"{SUMMARY_MEMBER}.{key}",
        )

    platform = PlatformContract(
        status="PASSED",
        decision="ATTENTION_BACKEND_PLATFORM_PREFLIGHT_PASSED",
        gpu_count=2,
        gpu_names=("Tesla T4", "Tesla T4"),
        compute_capabilities=((7, 5), (7, 5)),
        base_torch_version="2.10.0+cu128",
        base_cuda_build="12.8",
        cuda_available=True,
    )
    backend = BackendContract(
        registry_enum="AttentionBackendEnum.TRITON_ATTN",
        backend_path=("vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"),
        backend_class=("vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"),
        backend_name="TRITON_ATTN",
        registry_overridden=False,
        all_origins_inside_target=True,
        vllm_version="0.19.1",
        torch_version="2.10.0+cu129",
        torch_cuda_build="12.9",
        triton_version="3.6.0",
    )
    capability = CapabilityContract(
        status="PASSED",
        device_name="Tesla T4",
        compute_capability=(7, 5),
        attention_type="decoder",
        dtype="float16",
        head_size=64,
        block_size=16,
        kv_cache_dtype="auto",
        invalid_reasons=(),
    )
    primitive = PrimitiveContract(
        status="PASSED",
        decision="ATTENTION_BACKEND_PRIMITIVE_PASSED",
        module="vllm.v1.attention.ops.triton_prefill_attention",
        name="context_attention_fwd",
        backend_owns_exact_primitive=True,
        result_close=True,
        causal=False,
        sequence_length=8,
        num_heads=2,
        head_size=64,
        maximum_absolute_error=0.00048828125,
        atol=0.03,
        rtol=0.03,
    )
    safety = SafetyContract(
        runtime_install_attempts=1,
        backend_discovery_attempts=1,
        backend_import_attempts=1,
        backend_capability_validation_attempts=1,
        attention_primitive_attempts=1,
        model_loads=0,
        worker_starts=0,
        model_requests=0,
        benchmark_trajectory_requests=0,
        network_requests=0,
        hidden_retries_performed=0,
        global_environment_mutations_performed=0,
        credentials_used=False,
        customer_data_present=False,
        external_spend=0,
    )
    evidence_captured_at = _parse_datetime(
        summary_raw.get("captured_at"),
        f"{SUMMARY_MEMBER}.captured_at",
    )
    return (
        platform,
        backend,
        capability,
        primitive,
        safety,
        evidence_captured_at,
    )


def build_acceptance_record(
    repo_root: Path,
) -> AttentionBackendExecutionAcceptanceRecord:
    for transient in (
        OPERATIONAL_AUTHORIZATION_PATH,
        OPERATIONAL_CONSUMPTION_PATH,
    ):
        if (repo_root / transient).exists():
            raise AttentionBackendAcceptanceError(
                "ATTENTION_BACKEND_ACCEPTANCE_TRANSIENT_PRESENT",
                "operational transient authorization artifacts must be absent",
                transient.as_posix(),
            )

    log_payload = _read_bound_file(repo_root, LOG_PATH, LOG_SHA256)
    zip_payload = _read_bound_file(
        repo_root,
        EVIDENCE_ZIP_PATH,
        EVIDENCE_ZIP_SHA256,
    )
    authorization_payload = _read_bound_file(
        repo_root,
        AUTHORIZATION_EVIDENCE_PATH,
        AUTHORIZATION_SHA256,
    )
    consumption_payload = _read_bound_file(
        repo_root,
        CONSUMPTION_EVIDENCE_PATH,
        CONSUMPTION_SHA256,
    )
    inspection_payload = _read_bound_file(
        repo_root,
        INSPECTION_MANIFEST_PATH,
        INSPECTION_MANIFEST_SHA256,
    )

    _validate_log(log_payload)
    _validate_inspection_manifest(inspection_payload)
    authorization, consumption = _validate_authorization(
        authorization_payload,
        consumption_payload,
    )
    members = _safe_zip_members(zip_payload)
    zip_members = _validate_manifest(members)
    (
        platform,
        backend,
        capability,
        primitive,
        safety,
        evidence_captured_at,
    ) = _contracts(members)

    authorization_lifecycle = AuthorizationLifecycle(
        authorization_sha256=AUTHORIZATION_SHA256,
        consumption_sha256=CONSUMPTION_SHA256,
        issued_from_main_commit=INTEGRATION_BASE_MAIN_COMMIT,
        issued_at=_parse_datetime(
            authorization.get("issued_at"),
            f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.issued_at",
        ),
        expires_at=_parse_datetime(
            authorization.get("expires_at"),
            f"{AUTHORIZATION_EVIDENCE_PATH.as_posix()}.expires_at",
        ),
        evidence_captured_at=evidence_captured_at,
        consumed_at=_parse_datetime(
            consumption.get("consumed_at"),
            f"{CONSUMPTION_EVIDENCE_PATH.as_posix()}.consumed_at",
        ),
        scope="MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1",
        single_use=True,
        outcome="PASSED",
        authorization_reusable=False,
        execution_evidence_within_authorization_window=True,
    )

    return AttentionBackendExecutionAcceptanceRecord(
        record_id=("auragateway-cu129-explicit-triton-attention-backend-execution-acceptance-v1"),
        status=("EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_VALID"),
        integration_base_main_commit=INTEGRATION_BASE_MAIN_COMMIT,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        authorization_issuer_feature_commit=(AUTHORIZATION_ISSUER_FEATURE_COMMIT),
        implementation_source_main_commit=IMPLEMENTATION_SOURCE_MAIN_COMMIT,
        saved_version=SavedVersion(
            notebook_name=NOTEBOOK_NAME,
            notebook_sha256=NOTEBOOK_SHA256,
            saved_version_id=SAVED_VERSION_ID,
            saved_version_url=SAVED_VERSION_URL,
            log=EvidenceFile(
                repository_path=LOG_PATH.as_posix(),
                sha256=LOG_SHA256,
                size_bytes=len(log_payload),
            ),
            evidence_archive=EvidenceFile(
                repository_path=EVIDENCE_ZIP_PATH.as_posix(),
                sha256=EVIDENCE_ZIP_SHA256,
                size_bytes=len(zip_payload),
            ),
        ),
        authorization_lifecycle=authorization_lifecycle,
        zip_members=zip_members,
        platform=platform,
        backend=backend,
        capability=capability,
        primitive=primitive,
        safety=safety,
        terminal_decision="EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED",
        q6_execution_accepted=True,
        authorization_lifecycle_closed=True,
        unchanged_replay_authorized=False,
        p3_p6_runtime_diagnostic_implementation_authorized=True,
        next_gate="design_and_implement_p3_p6_runtime_diagnostic_v1",
        non_claims=(
            "No vLLM worker reached readiness in this Q6 execution.",
            "No model or tokenizer was loaded.",
            "No inference request was issued.",
            "Paged decoder attention was not exercised.",
            "KV-cache reads and writes were not exercised.",
            "The primitive used causal=false and does not prove causal masking.",
            "Same-worker prefix reuse was not tested.",
            "Cache telemetry attribution and reset were not tested.",
            "Dual-worker isolation was not tested.",
            "No A/B/C benchmark trajectory was executed.",
            "Latency, throughput, cost, and quality were not measured.",
            "Deployment and production readiness are not claimed.",
        ),
    )


def generate(
    repo_root: Path,
) -> AttentionBackendExecutionAcceptanceRecord:
    record = build_acceptance_record(repo_root)
    payload = _canonical_json(record.model_dump(mode="json")).encode("utf-8")
    _write_atomic(repo_root / ACCEPTANCE_RECORD_PATH, payload)
    return record


def validate(
    repo_root: Path,
) -> AttentionBackendExecutionAcceptanceRecord:
    expected = build_acceptance_record(repo_root)
    path = repo_root / ACCEPTANCE_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_RECORD_UNSAFE",
            "acceptance record is missing or unsafe",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    expected_payload = _canonical_json(expected.model_dump(mode="json")).encode("utf-8")
    observed_payload = path.read_bytes()
    if observed_payload != expected_payload:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_RECORD_DRIFT",
            "acceptance record differs from fresh rebuild",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    try:
        observed_raw = json.loads(observed_payload.decode("utf-8"))
        observed = AttentionBackendExecutionAcceptanceRecord.model_validate(observed_raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_RECORD_INVALID",
            "acceptance record violates its contract",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        ) from error
    if observed != expected:
        raise AttentionBackendAcceptanceError(
            "ATTENTION_BACKEND_ACCEPTANCE_RECORD_SEMANTIC_DRIFT",
            "acceptance record semantic state drifted",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    return expected


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            marker = "ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_VALIDATED"
        else:
            raise AttentionBackendAcceptanceError(
                "ATTENTION_BACKEND_ACCEPTANCE_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": record.status,
                    "saved_version_id": record.saved_version.saved_version_id,
                    "evidence_zip_sha256": (record.saved_version.evidence_archive.sha256),
                    "terminal_decision": record.terminal_decision,
                    "q6_execution_accepted": True,
                    "authorization_lifecycle_closed": True,
                    "unchanged_replay_authorized": False,
                    "p3_p6_implementation_authorized": True,
                    "kaggle_execution_performed": False,
                    "next_gate": record.next_gate,
                }
            )
        )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        AttentionBackendAcceptanceError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, AttentionBackendAcceptanceError)
            else {
                "error_code": "ATTENTION_BACKEND_ACCEPTANCE_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
