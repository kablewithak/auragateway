"""Accept the governed explicit CUDA driver-link probe V2 evidence."""

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
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

INTEGRATION_BASE_MAIN_COMMIT: Final = "147c2a886af71a97d38474be5ffb718442e551e8"
IMPLEMENTATION_FEATURE_COMMIT: Final = "e20727b6db64cdd6160fa4258d3b42da8d0b48ca"
PROBE_SOURCE_MAIN_COMMIT: Final = "f7ed2a6aec0fe47b3cde3941c476af10fb70a291"

NOTEBOOK_NAME: Final = "ag-cu129-explicit-driver-link-probe-v2"
NOTEBOOK_SHA256: Final = "7545dd1ee34148f9e5e9c91df01c2134b9587014a4d5e9df4af9ff3162865a4d"
SAVED_VERSION_ID: Final = 339127349
SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-explicit-driver-link-probe-v2/log"
    "?scriptVersionId=339127349"
)

LOG_SHA256: Final = "cedffa52fda554e68f03cf6c0c623e090a634ecb3e0bcfa808ebc3e97e9d293a"
EVIDENCE_ZIP_SHA256: Final = "8be080c46a077d88dcd0d51325fe2a751936a599d3b350ba7def3bdf5eb7b33c"

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-explicit-driver-link-probe-acceptance-v1"
)
LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-explicit-driver-link-probe-v2-339127349.log")
EVIDENCE_ZIP_PATH: Final = EVIDENCE_ROOT / (
    "ag-cu129-explicit-driver-link-evidence-v2-339127349.zip"
)
ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_driver_link_probe_execution_acceptance_v1.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

BUNDLE_MANIFEST_MEMBER: Final = "bundle_manifest_v2.json"
LINK_REPORT_MEMBER: Final = "explicit_cuda_driver_link_report_v2.json"
SUMMARY_MEMBER: Final = "explicit_cuda_driver_link_summary_v2.json"
HUMAN_REPORT_MEMBER: Final = "human_report_v2.md"
PLATFORM_REPORT_MEMBER: Final = "platform_identity_report_v2.json"

EXPECTED_ZIP_MEMBERS: Final = (
    BUNDLE_MANIFEST_MEMBER,
    LINK_REPORT_MEMBER,
    SUMMARY_MEMBER,
    HUMAN_REPORT_MEMBER,
    PLATFORM_REPORT_MEMBER,
)

EXPECTED_MEMBER_SHA256: Final = {
    BUNDLE_MANIFEST_MEMBER: ("cf84320cebadeb7e3b4d3d19206fd95c9a9229c71e256b2403101bc2211c735a"),
    LINK_REPORT_MEMBER: ("416a7410f0d08903328829459f44291269a65a5addf063ae2ddb2df0439c8304"),
    SUMMARY_MEMBER: ("b9fc34131d93c6708cbd48c436e2c994581dc75dbfd31e72644e176c34fea867"),
    HUMAN_REPORT_MEMBER: ("6ae85dcfc8257019e47ef82a20052fc7a584d11d2b0969878795ea0af345e694"),
    PLATFORM_REPORT_MEMBER: ("8df3436abbf10d3c5e31fb06d91541398d772f8ccebf20f24f24b4b64ef186b2"),
}

EXPECTED_MEMBER_SIZES: Final = {
    BUNDLE_MANIFEST_MEMBER: 796,
    LINK_REPORT_MEMBER: 6807,
    SUMMARY_MEMBER: 789,
    HUMAN_REPORT_MEMBER: 561,
    PLATFORM_REPORT_MEMBER: 3252,
}

REAL_DRIVER_DIRECTORY: Final = "/usr/local/nvidia/lib64"
REAL_DRIVER_LINK_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so"
REAL_DRIVER_RESOLVED_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so.580.159.04"
RUNTIME_DRIVER_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so.1"
CUDA_STUB_DIRECTORY: Final = "/usr/local/cuda/lib64/stubs"

REQUIRED_LINK_FLAGS: Final = (
    "-L/usr/local/nvidia/lib64",
    "-Wl,-rpath,/usr/local/nvidia/lib64",
    "-Wl,-t",
    "-lcuda",
)
SOURCE_SHA256: Final = "263bf5cec15f224add6e80041cfb026725df52135623224c22f79f901bd9b2f2"


class ExplicitDriverLinkAcceptanceError(RuntimeError):
    """Fail-closed evidence-acceptance error."""

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
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_ARGUMENT_ERROR",
            message,
        )


class EvidenceFile(LocalABCContract):
    """Repository-bound external evidence file."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class EvidenceZipMember(LocalABCContract):
    """Identity of one regular evidence ZIP member."""

    name: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class AcceptedSavedVersion(LocalABCContract):
    """Immutable accepted Kaggle saved-version locator."""

    notebook_name: str
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_version_id: int = Field(gt=0)
    saved_version_url: str
    log: EvidenceFile
    evidence_archive: EvidenceFile


class AcceptedPlatformState(LocalABCContract):
    """Accepted P0 runtime identity."""

    status: Literal["PASSED"]
    decision: Literal["EXPLICIT_DRIVER_LINK_PREFLIGHT_PASSED"]
    ubuntu_version: Literal["Ubuntu 22.04.5 LTS"]
    python_version: Literal["3.12.13"]
    gpu_count: Literal[2]
    gpu_name: Literal["Tesla T4"]
    compute_capability: tuple[Literal[7], Literal[5]]
    driver_version: Literal["580.159.04"]
    base_torch_version: Literal["2.10.0+cu128"]
    base_torch_cuda_build: Literal["12.8"]
    real_driver_link_path: str
    real_driver_resolved_path: str
    library_path: Literal["/usr/local/cuda/lib64/stubs"]


class AcceptedLinkContract(LocalABCContract):
    """Accepted P1 explicit real-driver link contract."""

    status: Literal["PASSED"]
    decision: Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"]
    failure_stage: Literal["none"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_link_flags: tuple[str, str, str, str]
    selected_link_library: str
    runtime_library_path: str
    elf_needed_libcuda_so_1: Literal[True]
    elf_runpath_real_driver_directory: Literal[True]
    syntax_compile_succeeded: Literal[True]
    link_succeeded: Literal[True]
    selected_link_library_real: Literal[True]
    runtime_library_real: Literal[True]
    cu_init_zero: Literal[True]
    cuda_toolkit_stub_rejected: Literal[True]
    global_environment_mutation_absent: Literal[True]
    source_materialization_attempts: Literal[1]
    syntax_compile_attempts: Literal[1]
    link_attempts: Literal[1]
    elf_inspection_attempts: Literal[1]
    loader_resolution_attempts: Literal[1]
    driver_initialization_attempts: Literal[1]


class AcceptanceSafety(LocalABCContract):
    """Accepted execution budgets and prohibited work."""

    p2_performed: Literal[False]
    runtime_install_attempts: Literal[0]
    kernel_compile_and_execution_attempts: Literal[0]
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


class ExplicitDriverLinkExecutionAcceptanceRecord(LocalABCContract):
    """Accepted successful explicit-driver-link execution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-explicit-driver-link-execution-acceptance-v1"]
    status: Literal["EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID"]
    integration_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    probe_source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    saved_version: AcceptedSavedVersion
    zip_members: tuple[EvidenceZipMember, ...]
    platform: AcceptedPlatformState
    link_contract: AcceptedLinkContract
    safety: AcceptanceSafety
    default_linker_failure_remediated_by_command_local_path: Literal[True]
    global_environment_mutation_required: Literal[False]
    cuda_toolkit_stub_required: Literal[False]
    unchanged_probe_replay_authorized: Literal[False]
    p0_p2_diagnostic_v2_implementation_authorized: Literal[True]
    next_gate: Literal["design_and_implement_p0_p2_platform_diagnostic_v2"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.integration_base_main_commit != INTEGRATION_BASE_MAIN_COMMIT:
            raise ValueError("integration base main commit drifted")
        if self.implementation_feature_commit != IMPLEMENTATION_FEATURE_COMMIT:
            raise ValueError("implementation feature commit drifted")
        if self.probe_source_main_commit != PROBE_SOURCE_MAIN_COMMIT:
            raise ValueError("probe source main commit drifted")
        if self.saved_version.notebook_name != NOTEBOOK_NAME:
            raise ValueError("notebook name drifted")
        if self.saved_version.notebook_sha256 != NOTEBOOK_SHA256:
            raise ValueError("notebook identity drifted")
        if self.saved_version.saved_version_id != SAVED_VERSION_ID:
            raise ValueError("saved-version ID drifted")
        if self.saved_version.saved_version_url != SAVED_VERSION_URL:
            raise ValueError("saved-version URL drifted")
        if self.platform.real_driver_link_path != REAL_DRIVER_LINK_PATH:
            raise ValueError("real driver link path drifted")
        if self.platform.real_driver_resolved_path != REAL_DRIVER_RESOLVED_PATH:
            raise ValueError("resolved real driver path drifted")
        if self.link_contract.source_sha256 != SOURCE_SHA256:
            raise ValueError("governed C source identity drifted")
        if self.link_contract.required_link_flags != REQUIRED_LINK_FLAGS:
            raise ValueError("explicit link flags drifted")
        if self.link_contract.selected_link_library != REAL_DRIVER_RESOLVED_PATH:
            raise ValueError("selected link library identity drifted")
        if self.link_contract.runtime_library_path != RUNTIME_DRIVER_PATH:
            raise ValueError("runtime driver path drifted")
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


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_TEMPORARY_PATH_PRESENT",
            "temporary acceptance-record path already exists",
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
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_EVIDENCE_UNSAFE",
            "required evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_IDENTITY_DRIFT",
            "evidence identity drifted",
            relative_path.as_posix(),
        )
    return payload


def _safe_zip_members(payload: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ExplicitDriverLinkAcceptanceError(
                    "EXPLICIT_DRIVER_LINK_ACCEPTANCE_DUPLICATE_MEMBER",
                    "evidence ZIP contains duplicate members",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )

            expected_names = set(EXPECTED_ZIP_MEMBERS)
            if set(names) != expected_names:
                raise ExplicitDriverLinkAcceptanceError(
                    "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MEMBER_SET_DRIFT",
                    "evidence ZIP member set drifted",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )

            result: dict[str, bytes] = {}
            for info in infos:
                path = PurePosixPath(info.filename)
                mode = info.external_attr >> 16
                unsafe = (
                    path.is_absolute()
                    or ".." in path.parts
                    or path.name != info.filename
                    or info.is_dir()
                    or stat.S_ISLNK(mode)
                )
                if unsafe:
                    raise ExplicitDriverLinkAcceptanceError(
                        "EXPLICIT_DRIVER_LINK_ACCEPTANCE_UNSAFE_MEMBER",
                        "evidence ZIP contains an unsafe member",
                        info.filename,
                    )
                member_payload = archive.read(info)
                expected_sha256 = EXPECTED_MEMBER_SHA256[info.filename]
                expected_size = EXPECTED_MEMBER_SIZES[info.filename]
                if (
                    _sha256_bytes(member_payload) != expected_sha256
                    or len(member_payload) != expected_size
                ):
                    raise ExplicitDriverLinkAcceptanceError(
                        "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MEMBER_DRIFT",
                        "evidence ZIP member identity drifted",
                        info.filename,
                    )
                result[info.filename] = member_payload
            return result
    except zipfile.BadZipFile as error:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_BAD_ZIP",
            "evidence archive is not a valid ZIP",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error


def _json_object(
    members: Mapping[str, bytes],
    name: str,
) -> dict[str, object]:
    try:
        raw = json.loads(members[name].decode("utf-8"))
    except (
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_JSON_INVALID",
            "required evidence JSON is invalid",
            name,
        ) from error
    if not isinstance(raw, dict):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_JSON_ROOT_INVALID",
            "evidence JSON root must be one object",
            name,
        )
    return {str(key): value for key, value in raw.items()}


def _require_mapping(
    value: object,
    *,
    path: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_OBJECT_REQUIRED",
            "required evidence field must be one object",
            path,
        )
    return {str(key): nested for key, nested in value.items()}


def _require_sequence(
    value: object,
    *,
    path: str,
) -> list[object]:
    if not isinstance(value, list):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_ARRAY_REQUIRED",
            "required evidence field must be one array",
            path,
        )
    return list(value)


def _require_str(
    value: object,
    *,
    path: str,
) -> str:
    if not isinstance(value, str):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_STRING_REQUIRED",
            "required evidence field must be one string",
            path,
        )
    return value


def _require_int(
    value: object,
    *,
    path: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_INTEGER_REQUIRED",
            "required evidence field must be one integer",
            path,
        )
    return value


def _require_bool(
    value: object,
    *,
    path: str,
) -> bool:
    if not isinstance(value, bool):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_BOOLEAN_REQUIRED",
            "required evidence field must be one boolean",
            path,
        )
    return value


def _validate_log(payload: bytes) -> None:
    text = payload.decode("utf-8")
    required_fragments = (
        '"status":"PASSED"',
        ('"terminal_decision":"EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"'),
        (f'"evidence_zip_sha256":"{EVIDENCE_ZIP_SHA256}"'),
        '"p2_performed":false',
        '"runtime_install_attempts":0',
        '"kernel_compile_and_execution_attempts":0',
        '"model_loads":0',
        '"worker_starts":0',
        '"model_requests":0',
        '"network_requests":0',
        '"external_spend":0',
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_LOG_DRIFT",
                "execution log is missing a required terminal fragment",
                fragment,
            )


def _validate_manifest(
    members: Mapping[str, bytes],
) -> tuple[EvidenceZipMember, ...]:
    raw = _json_object(
        members,
        BUNDLE_MANIFEST_MEMBER,
    )
    if (
        raw.get("schema_version") != "2.0.0"
        or raw.get("probe_id") != ("auragateway-cu129-explicit-cuda-driver-link-path-probe-v2")
        or raw.get("source_main_commit") != PROBE_SOURCE_MAIN_COMMIT
    ):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MANIFEST_AUTHORITY_DRIFT",
            "bundle manifest authority drifted",
            BUNDLE_MANIFEST_MEMBER,
        )

    entries = _require_sequence(
        raw.get("members"),
        path="bundle_manifest_v2.json.members",
    )
    observed: dict[str, EvidenceZipMember] = {}
    for index, entry_value in enumerate(entries):
        entry = _require_mapping(
            entry_value,
            path=f"bundle_manifest_v2.json.members[{index}]",
        )
        name = _require_str(
            entry.get("path"),
            path=(f"bundle_manifest_v2.json.members[{index}].path"),
        )
        sha256 = _require_str(
            entry.get("sha256"),
            path=(f"bundle_manifest_v2.json.members[{index}].sha256"),
        )
        size_bytes = _require_int(
            entry.get("size_bytes"),
            path=(f"bundle_manifest_v2.json.members[{index}].size_bytes"),
        )
        if name == BUNDLE_MANIFEST_MEMBER:
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MANIFEST_SELF_REFERENCE",
                "bundle manifest must not bind itself",
                name,
            )
        if name in observed:
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MANIFEST_DUPLICATE",
                "bundle manifest contains duplicate member",
                name,
            )
        expected_sha = EXPECTED_MEMBER_SHA256.get(name)
        expected_size = EXPECTED_MEMBER_SIZES.get(name)
        if (
            expected_sha is None
            or expected_size is None
            or sha256 != expected_sha
            or size_bytes != expected_size
            or _sha256_bytes(members[name]) != sha256
            or len(members[name]) != size_bytes
        ):
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MANIFEST_BINDING_DRIFT",
                "bundle manifest member binding drifted",
                name,
            )
        observed[name] = EvidenceZipMember(
            name=name,
            sha256=sha256,
            size_bytes=size_bytes,
        )

    expected_bound_names = set(EXPECTED_ZIP_MEMBERS) - {BUNDLE_MANIFEST_MEMBER}
    if set(observed) != expected_bound_names:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_MANIFEST_SET_DRIFT",
            "bundle manifest bound-member set drifted",
            BUNDLE_MANIFEST_MEMBER,
        )

    all_members = [
        EvidenceZipMember(
            name=name,
            sha256=EXPECTED_MEMBER_SHA256[name],
            size_bytes=EXPECTED_MEMBER_SIZES[name],
        )
        for name in EXPECTED_ZIP_MEMBERS
    ]
    return tuple(
        sorted(
            all_members,
            key=lambda item: item.name,
        )
    )


def _platform_state(
    members: Mapping[str, bytes],
) -> AcceptedPlatformState:
    raw = _json_object(
        members,
        PLATFORM_REPORT_MEMBER,
    )
    checks = _require_mapping(
        raw.get("checks"),
        path="platform_identity_report_v2.json.checks",
    )
    torch = _require_mapping(
        raw.get("torch"),
        path="platform_identity_report_v2.json.torch",
    )
    platform = _require_mapping(
        raw.get("platform"),
        path="platform_identity_report_v2.json.platform",
    )
    os_release = _require_mapping(
        platform.get("os_release"),
        path=("platform_identity_report_v2.json.platform.os_release"),
    )
    devices = _require_sequence(
        torch.get("devices"),
        path="platform_identity_report_v2.json.torch.devices",
    )

    if len(devices) != 2:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_GPU_COUNT_DRIFT",
            "expected exactly two GPU devices",
            PLATFORM_REPORT_MEMBER,
        )
    for index, device_value in enumerate(devices):
        device = _require_mapping(
            device_value,
            path=(f"platform_identity_report_v2.json.torch.devices[{index}]"),
        )
        if device.get("name") != "Tesla T4" or device.get("compute_capability") != [7, 5]:
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_GPU_IDENTITY_DRIFT",
                "GPU identity drifted",
                str(index),
            )

    required_checks = (
        "build_identity_complete",
        "compiler_available",
        "credentials_absent",
        "dual_t4_topology",
        "linker_loader_tools_available",
        "nvidia_smi_succeeded",
        "real_driver_link_present",
        "real_driver_link_resolves_inside_real_mount",
        "torch_cuda_available",
    )
    if any(
        _require_bool(
            checks.get(name),
            path=(f"platform_identity_report_v2.json.checks.{name}"),
        )
        is not True
        for name in required_checks
    ):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_P0_CHECK_FAILED",
            "one or more P0 checks did not pass",
            PLATFORM_REPORT_MEMBER,
        )

    nvidia_smi = _require_mapping(
        raw.get("nvidia_smi"),
        path="platform_identity_report_v2.json.nvidia_smi",
    )
    output = _require_str(
        nvidia_smi.get("stdout"),
        path=("platform_identity_report_v2.json.nvidia_smi.stdout"),
    )
    if output.count("Tesla T4") != 2 or output.count("580.159.04") != 2:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_DRIVER_OUTPUT_DRIFT",
            "nvidia-smi output drifted",
            PLATFORM_REPORT_MEMBER,
        )

    environment = _require_mapping(
        raw.get("allowlisted_environment"),
        path=("platform_identity_report_v2.json.allowlisted_environment"),
    )

    return AcceptedPlatformState(
        status=cast(Literal["PASSED"], raw.get("status")),
        decision=cast(
            Literal["EXPLICIT_DRIVER_LINK_PREFLIGHT_PASSED"],
            raw.get("decision"),
        ),
        ubuntu_version=cast(
            Literal["Ubuntu 22.04.5 LTS"],
            os_release.get("PRETTY_NAME"),
        ),
        python_version=cast(
            Literal["3.12.13"],
            _require_mapping(
                raw.get("python"),
                path=("platform_identity_report_v2.json.python"),
            ).get("version"),
        ),
        gpu_count=2,
        gpu_name="Tesla T4",
        compute_capability=(7, 5),
        driver_version="580.159.04",
        base_torch_version=cast(
            Literal["2.10.0+cu128"],
            torch.get("version"),
        ),
        base_torch_cuda_build=cast(
            Literal["12.8"],
            torch.get("cuda_build"),
        ),
        real_driver_link_path=_require_str(
            raw.get("real_driver_link_path"),
            path=("platform_identity_report_v2.json.real_driver_link_path"),
        ),
        real_driver_resolved_path=_require_str(
            raw.get("real_driver_resolved_path"),
            path=("platform_identity_report_v2.json.real_driver_resolved_path"),
        ),
        library_path=cast(
            Literal["/usr/local/cuda/lib64/stubs"],
            environment.get("LIBRARY_PATH"),
        ),
    )


def _link_contract(
    members: Mapping[str, bytes],
) -> AcceptedLinkContract:
    raw = _json_object(
        members,
        LINK_REPORT_MEMBER,
    )
    checks = _require_mapping(
        raw.get("checks"),
        path=("explicit_cuda_driver_link_report_v2.json.checks"),
    )
    budgets = _require_mapping(
        raw.get("budgets"),
        path=("explicit_cuda_driver_link_report_v2.json.budgets"),
    )
    source_contract = _require_mapping(
        raw.get("source_contract"),
        path=("explicit_cuda_driver_link_report_v2.json.source_contract"),
    )
    selected = _require_sequence(
        raw.get("selected_link_libraries"),
        path=("explicit_cuda_driver_link_report_v2.json.selected_link_libraries"),
    )
    if selected != [REAL_DRIVER_RESOLVED_PATH]:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_SELECTED_LIBRARY_DRIFT",
            "selected link library drifted",
            LINK_REPORT_MEMBER,
        )

    required_true_checks = (
        "source_exact",
        "syntax_compile_succeeded",
        "link_succeeded",
        "selected_link_library_real",
        "elf_needed_libcuda_so_1",
        "elf_runpath_real_driver_directory",
        "runtime_library_real",
        "cu_init_zero",
        "cuda_toolkit_stub_rejected",
        "global_environment_mutation_absent",
    )
    if any(
        _require_bool(
            checks.get(name),
            path=(f"explicit_cuda_driver_link_report_v2.json.checks.{name}"),
        )
        is not True
        for name in required_true_checks
    ):
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_P1_CHECK_FAILED",
            "one or more P1 checks did not pass",
            LINK_REPORT_MEMBER,
        )

    expected_attempts = {
        "source_materialization_attempts": 1,
        "syntax_compile_attempts": 1,
        "link_attempts": 1,
        "elf_inspection_attempts": 1,
        "loader_resolution_attempts": 1,
        "driver_initialization_attempts": 1,
    }
    for name, expected in expected_attempts.items():
        if (
            _require_int(
                budgets.get(name),
                path=(f"explicit_cuda_driver_link_report_v2.json.budgets.{name}"),
            )
            != expected
        ):
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_ATTEMPT_BUDGET_DRIFT",
                "P1 attempt budget drifted",
                name,
            )

    environment_overrides = _require_sequence(
        raw.get("environment_overrides_applied"),
        path=("explicit_cuda_driver_link_report_v2.json.environment_overrides_applied"),
    )
    if environment_overrides:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_ENVIRONMENT_OVERRIDE",
            "environment override list must be empty",
            LINK_REPORT_MEMBER,
        )

    return AcceptedLinkContract(
        status=cast(Literal["PASSED"], raw.get("status")),
        decision=cast(
            Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"],
            raw.get("decision"),
        ),
        failure_stage=cast(
            Literal["none"],
            raw.get("failure_stage"),
        ),
        source_sha256=_require_str(
            source_contract.get("observed_sha256"),
            path=("explicit_cuda_driver_link_report_v2.json.source_contract.observed_sha256"),
        ),
        required_link_flags=tuple(
            cast(
                list[str],
                _require_sequence(
                    raw.get("required_link_flags"),
                    path=("explicit_cuda_driver_link_report_v2.json.required_link_flags"),
                ),
            )
        ),
        selected_link_library=cast(str, selected[0]),
        runtime_library_path=_require_str(
            raw.get("runtime_library_path"),
            path=("explicit_cuda_driver_link_report_v2.json.runtime_library_path"),
        ),
        elf_needed_libcuda_so_1=True,
        elf_runpath_real_driver_directory=True,
        syntax_compile_succeeded=True,
        link_succeeded=True,
        selected_link_library_real=True,
        runtime_library_real=True,
        cu_init_zero=True,
        cuda_toolkit_stub_rejected=True,
        global_environment_mutation_absent=True,
        source_materialization_attempts=1,
        syntax_compile_attempts=1,
        link_attempts=1,
        elf_inspection_attempts=1,
        loader_resolution_attempts=1,
        driver_initialization_attempts=1,
    )


def _safety(
    members: Mapping[str, bytes],
) -> AcceptanceSafety:
    raw = _json_object(
        members,
        SUMMARY_MEMBER,
    )
    expected_scalars: dict[str, object] = {
        "schema_version": "2.0.0",
        "probe_id": ("auragateway-cu129-explicit-cuda-driver-link-path-probe-v2"),
        "source_main_commit": PROBE_SOURCE_MAIN_COMMIT,
        "status": "PASSED",
        "terminal_decision": ("EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"),
        "p0_status": "PASSED",
        "p1_status": "PASSED",
        "stop_on_first_failure": True,
        "p2_performed": False,
        "runtime_install_attempts": 0,
        "kernel_compile_and_execution_attempts": 0,
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
        "next_gate": ("integrate_explicit_driver_link_path_into_p0_p2_diagnostic_v2"),
    }
    for name, expected in expected_scalars.items():
        if raw.get(name) != expected:
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_SUMMARY_DRIFT",
                "summary semantic state drifted",
                name,
            )

    return AcceptanceSafety(
        p2_performed=False,
        runtime_install_attempts=0,
        kernel_compile_and_execution_attempts=0,
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


def build_acceptance_record(
    repo_root: Path,
) -> ExplicitDriverLinkExecutionAcceptanceRecord:
    """Build the complete accepted execution record."""

    if (repo_root / AUTHORIZATION_PATH).exists():
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_AUTHORIZATION_PRESENT",
            "transient full-run authorization must remain absent",
            AUTHORIZATION_PATH.as_posix(),
        )

    log_payload = _read_bound_file(
        repo_root,
        LOG_PATH,
        LOG_SHA256,
    )
    zip_payload = _read_bound_file(
        repo_root,
        EVIDENCE_ZIP_PATH,
        EVIDENCE_ZIP_SHA256,
    )

    _validate_log(log_payload)
    members = _safe_zip_members(zip_payload)
    zip_members = _validate_manifest(members)
    platform = _platform_state(members)
    link_contract = _link_contract(members)
    safety = _safety(members)

    return ExplicitDriverLinkExecutionAcceptanceRecord(
        record_id=("auragateway-cu129-explicit-driver-link-execution-acceptance-v1"),
        status=("EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID"),
        integration_base_main_commit=(INTEGRATION_BASE_MAIN_COMMIT),
        implementation_feature_commit=(IMPLEMENTATION_FEATURE_COMMIT),
        probe_source_main_commit=(PROBE_SOURCE_MAIN_COMMIT),
        saved_version=AcceptedSavedVersion(
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
                repository_path=(EVIDENCE_ZIP_PATH.as_posix()),
                sha256=EVIDENCE_ZIP_SHA256,
                size_bytes=len(zip_payload),
            ),
        ),
        zip_members=zip_members,
        platform=platform,
        link_contract=link_contract,
        safety=safety,
        default_linker_failure_remediated_by_command_local_path=True,
        global_environment_mutation_required=False,
        cuda_toolkit_stub_required=False,
        unchanged_probe_replay_authorized=False,
        p0_p2_diagnostic_v2_implementation_authorized=True,
        next_gate=("design_and_implement_p0_p2_platform_diagnostic_v2"),
        non_claims=(
            "The governed CUDA 12.9 wheelhouse was not installed.",
            "P2 and Triton kernel execution were not performed.",
            "Triton compatibility was not established.",
            "vLLM was not imported.",
            "No model was loaded.",
            "No worker was started.",
            "No model request was issued.",
            "No benchmark trajectory was executed.",
            "Environment qualification was not completed.",
            "Deployment and production readiness are not claimed.",
        ),
    )


def generate(
    repo_root: Path,
) -> ExplicitDriverLinkExecutionAcceptanceRecord:
    """Generate the deterministic acceptance record."""

    record = build_acceptance_record(repo_root)
    payload = _canonical_json(record.model_dump(mode="json")).encode("utf-8")
    _write_bytes_atomic(
        repo_root / ACCEPTANCE_RECORD_PATH,
        payload,
    )
    return record


def validate(
    repo_root: Path,
) -> ExplicitDriverLinkExecutionAcceptanceRecord:
    """Validate the stored record against a fresh rebuild."""

    expected = build_acceptance_record(repo_root)
    path = repo_root / ACCEPTANCE_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_RECORD_UNSAFE",
            "acceptance record is missing or unsafe",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )

    expected_payload = _canonical_json(expected.model_dump(mode="json")).encode("utf-8")
    observed_payload = path.read_bytes()
    if observed_payload != expected_payload:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_RECORD_DRIFT",
            "acceptance record differs from fresh rebuild",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )

    try:
        observed_raw = json.loads(observed_payload.decode("utf-8"))
        observed = ExplicitDriverLinkExecutionAcceptanceRecord.model_validate(observed_raw)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
    ) as error:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_RECORD_INVALID",
            "acceptance record violates its contract",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        ) from error

    if observed != expected:
        raise ExplicitDriverLinkAcceptanceError(
            "EXPLICIT_DRIVER_LINK_ACCEPTANCE_RECORD_SEMANTIC_DRIFT",
            "acceptance record semantic state drifted",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )
    return expected


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--repo-root",
            type=Path,
            required=True,
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(
            Path,
            arguments.repo_root,
        ).resolve()

        if arguments.command == "generate":
            record = generate(repo_root)
            marker = "EXPLICIT_DRIVER_LINK_PROBE_ACCEPTANCE_V1_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "EXPLICIT_DRIVER_LINK_PROBE_ACCEPTANCE_V1_VALIDATED"
        else:
            raise ExplicitDriverLinkAcceptanceError(
                "EXPLICIT_DRIVER_LINK_ACCEPTANCE_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )

        print(
            _canonical_json(
                {
                    "marker": marker,
                    "status": record.status,
                    "saved_version_id": (record.saved_version.saved_version_id),
                    "evidence_zip_sha256": (record.saved_version.evidence_archive.sha256),
                    "terminal_decision": (record.link_contract.decision),
                    "next_gate": record.next_gate,
                    "unchanged_probe_replay_authorized": False,
                    "p0_p2_diagnostic_v2_implementation_authorized": True,
                    "kaggle_execution_performed": False,
                }
            )
        )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        ExplicitDriverLinkAcceptanceError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(
                error,
                ExplicitDriverLinkAcceptanceError,
            )
            else {
                "error_code": ("EXPLICIT_DRIVER_LINK_ACCEPTANCE_UNEXPECTED"),
                "safe_message": str(error),
                "path": None,
            }
        )
        print(
            _canonical_json(envelope),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
