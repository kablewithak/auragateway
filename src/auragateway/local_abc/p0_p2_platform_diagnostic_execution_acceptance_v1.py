"""Accept the governed CUDA 12.9 P0-P2 platform diagnostic V2 evidence."""

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

from pydantic import ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

INTEGRATION_BASE_MAIN_COMMIT: Final = "1cabdacc6d98691fb734322830514d6566a98e8e"
IMPLEMENTATION_FEATURE_COMMIT: Final = "05b5c53d7142072e426f7ae37273e908aacd37a6"
DIAGNOSTIC_SOURCE_MAIN_COMMIT: Final = "fe297a6f1aeed04119452552874dab22bfe01dee"

NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-platform-diagnostic-v2"
NOTEBOOK_SHA256: Final = "2bf65a0b79d695e70a23463b21a2d58b72fc45e938d4775d9119f5d6d37cac42"
SAVED_VERSION_ID: Final = 339140121
SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-p0-p2-platform-diagnostic-v2/log"
    "?scriptVersionId=339140121"
)

LOG_SHA256: Final = "dd1455f7dfbf79b85efacd32f1518d6ebabe141d2a4ed5a50844d72778b70a4a"
EVIDENCE_ZIP_SHA256: Final = "e115d2f8c6c000a7666e0482e4d3d9f69bb74599fbf4f657304d456930de3240"

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-p0-p2-platform-diagnostic-acceptance-v1"
)
LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p0-p2-platform-diagnostic-v2-339140121.log")
EVIDENCE_ZIP_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p0-p2-platform-evidence-v2-339140121.zip")
ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_diagnostic_execution_acceptance_v1.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

PLATFORM_MEMBER: Final = "platform_identity_report_v2.json"
LINK_MEMBER: Final = "explicit_cuda_driver_link_report_v2.json"
TRITON_MEMBER: Final = "minimal_triton_kernel_report_v2.json"
SUMMARY_MEMBER: Final = "p0_p2_platform_diagnostic_summary_v2.json"
MANIFEST_MEMBER: Final = "bundle_manifest_v2.json"
HUMAN_MEMBER: Final = "human_report_v2.md"

EXPECTED_ZIP_MEMBERS: Final = (
    PLATFORM_MEMBER,
    LINK_MEMBER,
    TRITON_MEMBER,
    SUMMARY_MEMBER,
    MANIFEST_MEMBER,
    HUMAN_MEMBER,
)

EXPECTED_MEMBER_SHA256: Final = {
    PLATFORM_MEMBER: ("13d6d2136c7c5f375b87288b8f48c0a8eaeb1211717a94a34c115d79023bcb36"),
    LINK_MEMBER: ("5d126390084ed8138e36d1319f95f3eac06dd462278cde54b0e11dc299f7a7d9"),
    TRITON_MEMBER: ("e6f266cf9d89235d1994b216ff0e977cbbf6b8a6cd8c9e8c07b46b4df448c135"),
    SUMMARY_MEMBER: ("f202939271c0ddc461cd5e24e24744df07e090265aef022b68de951907d2712c"),
    MANIFEST_MEMBER: ("96de60f38464d2ee236749efe64df6318beee3e0847f7d608c55c62dac991977"),
    HUMAN_MEMBER: ("6ec6df2882eeaf1b10d6365f2758ab02f65cbb777f8a8c3cf60dae8192b21330"),
}

EXPECTED_MEMBER_SIZES: Final = {
    PLATFORM_MEMBER: 5742,
    LINK_MEMBER: 6589,
    TRITON_MEMBER: 39990,
    SUMMARY_MEMBER: 1068,
    MANIFEST_MEMBER: 923,
    HUMAN_MEMBER: 565,
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

EXPECTED_CONTROL_HASHES: Final = {
    "requirements.in": ("a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"),
    "resolution_lock.json": ("1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"),
    "materialization.lock.txt": (
        "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
    ),
    "requirements.lock.txt": ("47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"),
    "install_runtime.py": ("68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"),
    "runtime_manifest.json": ("b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"),
    "sha256_manifest.json": ("789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"),
    "materialization_receipt.json": (
        "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
    ),
}


class DiagnosticAcceptanceError(RuntimeError):
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
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_ARGUMENT_ERROR",
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
    notebook_name: str
    notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    saved_version_id: Literal[339140121]
    saved_version_url: str
    log: EvidenceFile
    evidence_archive: EvidenceFile


class PlatformContract(_StrictModel):
    status: Literal["PASSED"]
    decision: Literal["P0_REAL_DRIVER_PREFLIGHT_PASSED"]
    gpu_count: Literal[2]
    gpu_name: Literal["Tesla T4"]
    compute_capability: tuple[Literal[7], Literal[5]]
    base_torch_version: Literal["2.10.0+cu128"]
    base_torch_cuda_build: Literal["12.8"]
    real_driver_link_path: str
    real_driver_resolved_path: str


class LinkContract(_StrictModel):
    status: Literal["PASSED"]
    decision: Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"]
    required_link_flags: tuple[str, str, str, str]
    selected_link_library: str
    runtime_library_path: str
    cu_init_zero: Literal[True]
    stub_rejected: Literal[True]
    global_environment_mutation_absent: Literal[True]


class TritonContract(_StrictModel):
    status: Literal["PASSED"]
    decision: Literal["CURRENT_STACK_TRITON_PRIMITIVE_PASSED"]
    torch_version: Literal["2.10.0+cu129"]
    torch_cuda_build: Literal["12.9"]
    triton_version: Literal["3.6.0"]
    device_name: Literal["Tesla T4"]
    compute_capability: tuple[Literal[7], Literal[5]]
    result_exact: Literal[True]
    target_runtime_origins_exact: Literal[True]
    runtime_install_attempts: Literal[1]
    kernel_compile_and_execution_attempts: Literal[1]
    wheel_entry_count: Literal[176]
    manifest_entry_count: Literal[182]
    verified_entry_count: Literal[182]
    command_local_library_path: str
    command_local_ldflags: str
    stub_not_selected: Literal[True]
    global_environment_mutation_absent: Literal[True]


class SafetyContract(_StrictModel):
    model_loads: Literal[0]
    worker_starts: Literal[0]
    model_requests: Literal[0]
    benchmark_trajectory_requests: Literal[0]
    network_requests: Literal[0]
    hidden_retries_performed: Literal[0]
    global_environment_mutations_performed: Literal[0]
    filesystem_mutations_outside_working_directory: Literal[0]
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    external_spend: Literal[0]


class DiagnosticExecutionAcceptanceRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-platform-diagnostic-execution-acceptance-v1"]
    status: Literal["P0_P2_PLATFORM_DIAGNOSTIC_EXECUTION_ACCEPTANCE_V1_VALID"]
    integration_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_feature_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    diagnostic_source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    saved_version: SavedVersion
    zip_members: tuple[ZipMember, ...]
    platform: PlatformContract
    link: LinkContract
    triton: TritonContract
    safety: SafetyContract
    terminal_decision: Literal["P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED"]
    runtime_next_gate: Literal["implement_explicit_triton_attention_backend"]
    full_triton_qualification_attempt_consumed: Literal[True]
    unchanged_diagnostic_replay_authorized: Literal[False]
    explicit_attention_backend_v1_implementation_authorized: Literal[True]
    next_gate: Literal["design_and_implement_explicit_triton_attention_backend_v1"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        if self.integration_base_main_commit != INTEGRATION_BASE_MAIN_COMMIT:
            raise ValueError("integration base main commit drifted")
        if self.implementation_feature_commit != IMPLEMENTATION_FEATURE_COMMIT:
            raise ValueError("implementation feature commit drifted")
        if self.diagnostic_source_main_commit != DIAGNOSTIC_SOURCE_MAIN_COMMIT:
            raise ValueError("diagnostic source main commit drifted")
        if self.saved_version.notebook_name != NOTEBOOK_NAME:
            raise ValueError("notebook name drifted")
        if self.saved_version.notebook_sha256 != NOTEBOOK_SHA256:
            raise ValueError("notebook SHA-256 drifted")
        if self.saved_version.saved_version_url != SAVED_VERSION_URL:
            raise ValueError("saved-version URL drifted")
        if self.platform.real_driver_link_path != REAL_DRIVER_LINK_PATH:
            raise ValueError("real driver link path drifted")
        if self.platform.real_driver_resolved_path != REAL_DRIVER_RESOLVED_PATH:
            raise ValueError("resolved real driver path drifted")
        if self.link.required_link_flags != REQUIRED_LINK_FLAGS:
            raise ValueError("explicit link flags drifted")
        if self.link.selected_link_library != REAL_DRIVER_RESOLVED_PATH:
            raise ValueError("selected link library drifted")
        if self.link.runtime_library_path != RUNTIME_DRIVER_PATH:
            raise ValueError("runtime driver path drifted")
        if self.triton.command_local_library_path != REAL_DRIVER_DIRECTORY:
            raise ValueError("command-local LIBRARY_PATH drifted")
        expected_ldflags = "-L/usr/local/nvidia/lib64 -Wl,-rpath,/usr/local/nvidia/lib64"
        if self.triton.command_local_ldflags != expected_ldflags:
            raise ValueError("command-local LDFLAGS drifted")
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
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_TEMP_PRESENT",
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
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_EVIDENCE_UNSAFE",
            "required evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_IDENTITY_DRIFT",
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
                raise DiagnosticAcceptanceError(
                    "P0_P2_DIAGNOSTIC_ACCEPTANCE_DUPLICATE_MEMBER",
                    "evidence ZIP contains duplicate members",
                    EVIDENCE_ZIP_PATH.as_posix(),
                )
            if set(names) != set(EXPECTED_ZIP_MEMBERS):
                raise DiagnosticAcceptanceError(
                    "P0_P2_DIAGNOSTIC_ACCEPTANCE_MEMBER_SET_DRIFT",
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
                    raise DiagnosticAcceptanceError(
                        "P0_P2_DIAGNOSTIC_ACCEPTANCE_UNSAFE_MEMBER",
                        "evidence ZIP contains an unsafe member",
                        info.filename,
                    )
                member = archive.read(info)
                if (
                    _sha256_bytes(member) != EXPECTED_MEMBER_SHA256[info.filename]
                    or len(member) != EXPECTED_MEMBER_SIZES[info.filename]
                ):
                    raise DiagnosticAcceptanceError(
                        "P0_P2_DIAGNOSTIC_ACCEPTANCE_MEMBER_DRIFT",
                        "evidence ZIP member identity drifted",
                        info.filename,
                    )
                result[info.filename] = member
            return result
    except zipfile.BadZipFile as error:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_BAD_ZIP",
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
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_JSON_INVALID",
            "required evidence JSON is invalid",
            name,
        ) from error
    if not isinstance(raw, dict):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_JSON_ROOT_INVALID",
            "evidence JSON root must be one object",
            name,
        )
    return {str(key): value for key, value in raw.items()}


def _mapping(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_OBJECT_REQUIRED",
            "required evidence value must be one object",
            path,
        )
    return {str(key): nested for key, nested in value.items()}


def _sequence(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_ARRAY_REQUIRED",
            "required evidence value must be one array",
            path,
        )
    return list(value)


def _validate_log(payload: bytes) -> None:
    text = payload.decode("utf-8")
    required = (
        '"status":"PASSED"',
        '"terminal_decision":"P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED"',
        f'"evidence_zip_sha256":"{EVIDENCE_ZIP_SHA256}"',
        '"p0_status":"PASSED"',
        '"p1_status":"PASSED"',
        '"p2_status":"PASSED"',
        '"runtime_install_attempts":1',
        '"kernel_compile_and_execution_attempts":1',
        '"model_loads":0',
        '"worker_starts":0',
        '"model_requests":0',
        '"network_requests":0',
        '"hidden_retries_performed":0',
        '"global_environment_mutations_performed":0',
        '"external_spend":0',
    )
    for fragment in required:
        if fragment not in text:
            raise DiagnosticAcceptanceError(
                "P0_P2_DIAGNOSTIC_ACCEPTANCE_LOG_DRIFT",
                "execution log is missing a required terminal fragment",
                fragment,
            )


def _validate_manifest(
    members: Mapping[str, bytes],
) -> tuple[ZipMember, ...]:
    raw = _json_object(members, MANIFEST_MEMBER)
    if (
        raw.get("schema_version") != "2.0.0"
        or raw.get("diagnostic_id") != "auragateway-cu129-p0-p2-platform-diagnostic-v2"
        or raw.get("source_main_commit") != DIAGNOSTIC_SOURCE_MAIN_COMMIT
    ):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_MANIFEST_AUTHORITY_DRIFT",
            "bundle manifest authority drifted",
            MANIFEST_MEMBER,
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
            raise DiagnosticAcceptanceError(
                "P0_P2_DIAGNOSTIC_ACCEPTANCE_MANIFEST_ENTRY_INVALID",
                "bundle manifest entry fields are invalid",
                str(index),
            )
        if name in observed or name == MANIFEST_MEMBER:
            raise DiagnosticAcceptanceError(
                "P0_P2_DIAGNOSTIC_ACCEPTANCE_MANIFEST_ENTRY_DUPLICATE",
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
            raise DiagnosticAcceptanceError(
                "P0_P2_DIAGNOSTIC_ACCEPTANCE_MANIFEST_BINDING_DRIFT",
                "bundle manifest member binding drifted",
                name,
            )
        observed.add(name)

    expected = set(EXPECTED_ZIP_MEMBERS) - {MANIFEST_MEMBER}
    if observed != expected:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_MANIFEST_SET_DRIFT",
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


def _platform_contract(
    members: Mapping[str, bytes],
) -> PlatformContract:
    raw = _json_object(members, PLATFORM_MEMBER)
    checks = _mapping(raw.get("checks"), f"{PLATFORM_MEMBER}.checks")
    torch = _mapping(raw.get("base_torch"), f"{PLATFORM_MEMBER}.base_torch")
    devices = _sequence(torch.get("devices"), f"{PLATFORM_MEMBER}.devices")

    required_checks = (
        "base_torch_cuda_available",
        "build_identity_complete",
        "credentials_absent",
        "dual_t4_topology",
        "nvidia_smi_succeeded",
        "real_driver_link_present",
        "real_driver_link_resolves_inside_mount",
        "toolchain_available",
    )
    if any(checks.get(name) is not True for name in required_checks):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P0_CHECK_FAILED",
            "one or more P0 checks did not pass",
            PLATFORM_MEMBER,
        )
    if len(devices) != 2:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_GPU_COUNT_DRIFT",
            "expected exactly two P0 GPU devices",
            PLATFORM_MEMBER,
        )
    for index, device_value in enumerate(devices):
        device = _mapping(device_value, f"{PLATFORM_MEMBER}.devices[{index}]")
        if device.get("name") != "Tesla T4" or device.get("compute_capability") != [7, 5]:
            raise DiagnosticAcceptanceError(
                "P0_P2_DIAGNOSTIC_ACCEPTANCE_GPU_IDENTITY_DRIFT",
                "P0 GPU identity drifted",
                str(index),
            )

    return PlatformContract(
        status=cast(Literal["PASSED"], raw.get("status")),
        decision=cast(
            Literal["P0_REAL_DRIVER_PREFLIGHT_PASSED"],
            raw.get("decision"),
        ),
        gpu_count=2,
        gpu_name="Tesla T4",
        compute_capability=(7, 5),
        base_torch_version=cast(
            Literal["2.10.0+cu128"],
            torch.get("version"),
        ),
        base_torch_cuda_build=cast(
            Literal["12.8"],
            torch.get("cuda_build"),
        ),
        real_driver_link_path=str(raw.get("real_driver_link_path")),
        real_driver_resolved_path=str(raw.get("real_driver_resolved_path")),
    )


def _link_contract(
    members: Mapping[str, bytes],
) -> LinkContract:
    raw = _json_object(members, LINK_MEMBER)
    checks = _mapping(raw.get("checks"), f"{LINK_MEMBER}.checks")
    budgets = _mapping(raw.get("budgets"), f"{LINK_MEMBER}.budgets")

    required_checks = (
        "cu_init_zero",
        "cuda_toolkit_stub_rejected",
        "elf_needed_libcuda_so_1",
        "elf_runpath_real_driver_directory",
        "global_environment_mutation_absent",
        "link_succeeded",
        "runtime_library_real",
        "selected_link_library_real",
        "source_exact",
        "syntax_compile_succeeded",
    )
    if any(checks.get(name) is not True for name in required_checks):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P1_CHECK_FAILED",
            "one or more P1 checks did not pass",
            LINK_MEMBER,
        )

    exact_budgets = {
        "source_materialization_attempts": 1,
        "syntax_compile_attempts": 1,
        "link_attempts": 1,
        "elf_inspection_attempts": 1,
        "loader_resolution_attempts": 1,
        "driver_initialization_attempts": 1,
        "hidden_retries": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
    }
    if any(budgets.get(key) != value for key, value in exact_budgets.items()):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P1_BUDGET_DRIFT",
            "P1 execution budget drifted",
            LINK_MEMBER,
        )

    if raw.get("failure_stage") != "none":
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P1_FAILURE_STAGE",
            "P1 failure stage is not none",
            LINK_MEMBER,
        )
    if raw.get("environment_overrides_applied") != []:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P1_OVERRIDE_DRIFT",
            "P1 unexpectedly applied environment overrides",
            LINK_MEMBER,
        )

    flags = _sequence(raw.get("required_link_flags"), f"{LINK_MEMBER}.flags")
    return LinkContract(
        status=cast(Literal["PASSED"], raw.get("status")),
        decision=cast(
            Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"],
            raw.get("decision"),
        ),
        required_link_flags=tuple(cast(list[str], flags)),
        selected_link_library=str(raw.get("selected_link_library")),
        runtime_library_path=str(raw.get("runtime_library_path")),
        cu_init_zero=True,
        stub_rejected=True,
        global_environment_mutation_absent=True,
    )


def _triton_contract(
    members: Mapping[str, bytes],
) -> TritonContract:
    raw = _json_object(members, TRITON_MEMBER)
    checks = _mapping(raw.get("checks"), f"{TRITON_MEMBER}.checks")
    budgets = _mapping(raw.get("budgets"), f"{TRITON_MEMBER}.budgets")
    observation = _mapping(
        raw.get("probe_observation"),
        f"{TRITON_MEMBER}.probe_observation",
    )
    wheelhouse = _mapping(
        raw.get("wheelhouse_validation"),
        f"{TRITON_MEMBER}.wheelhouse_validation",
    )
    control_hashes = _mapping(
        wheelhouse.get("control_hashes"),
        f"{TRITON_MEMBER}.control_hashes",
    )

    required_checks = (
        "cuda_toolkit_stub_not_selected",
        "global_environment_mutation_absent",
        "kernel_process_succeeded",
        "kernel_result_exact",
        "real_driver_command_local_link_path",
        "runtime_installation_succeeded",
        "target_runtime_origins_exact",
        "torch_cu129_exact",
        "wheelhouse_identity_validated",
    )
    if any(checks.get(name) is not True for name in required_checks):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P2_CHECK_FAILED",
            "one or more P2 checks did not pass",
            TRITON_MEMBER,
        )

    exact_budgets = {
        "runtime_install_attempts": 1,
        "kernel_compile_and_execution_attempts": 1,
        "hidden_retries": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
    }
    if any(budgets.get(key) != value for key, value in exact_budgets.items()):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P2_BUDGET_DRIFT",
            "P2 execution budget drifted",
            TRITON_MEMBER,
        )
    if control_hashes != EXPECTED_CONTROL_HASHES:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_WHEELHOUSE_DRIFT",
            "wheelhouse control identities drifted",
            TRITON_MEMBER,
        )
    if raw.get("failure_stage") != "none":
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P2_FAILURE_STAGE",
            "P2 failure stage is not none",
            TRITON_MEMBER,
        )

    exact_observation = {
        "torch_version": "2.10.0+cu129",
        "torch_cuda_build": "12.9",
        "triton_distribution_version": "3.6.0",
        "device_name": "Tesla T4",
        "compute_capability": [7, 5],
        "device_count": 1,
        "result_exact": True,
        "torch_origin_inside_target": True,
        "triton_origin_inside_target": True,
        "model_loaded": False,
        "worker_started": False,
        "model_requests": 0,
        "library_path": REAL_DRIVER_DIRECTORY,
        "ldflags": ("-L/usr/local/nvidia/lib64 -Wl,-rpath,/usr/local/nvidia/lib64"),
    }
    if any(observation.get(key) != value for key, value in exact_observation.items()):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_P2_OBSERVATION_DRIFT",
            "P2 runtime observation drifted",
            TRITON_MEMBER,
        )

    return TritonContract(
        status=cast(Literal["PASSED"], raw.get("status")),
        decision=cast(
            Literal["CURRENT_STACK_TRITON_PRIMITIVE_PASSED"],
            raw.get("decision"),
        ),
        torch_version="2.10.0+cu129",
        torch_cuda_build="12.9",
        triton_version="3.6.0",
        device_name="Tesla T4",
        compute_capability=(7, 5),
        result_exact=True,
        target_runtime_origins_exact=True,
        runtime_install_attempts=1,
        kernel_compile_and_execution_attempts=1,
        wheel_entry_count=cast(Literal[176], wheelhouse.get("wheel_entry_count")),
        manifest_entry_count=cast(
            Literal[182],
            wheelhouse.get("manifest_entry_count"),
        ),
        verified_entry_count=cast(
            Literal[182],
            wheelhouse.get("verified_entry_count"),
        ),
        command_local_library_path=str(observation.get("library_path")),
        command_local_ldflags=str(observation.get("ldflags")),
        stub_not_selected=True,
        global_environment_mutation_absent=True,
    )


def _summary_and_safety(
    members: Mapping[str, bytes],
) -> tuple[str, str, bool, SafetyContract]:
    raw = _json_object(members, SUMMARY_MEMBER)
    exact = {
        "schema_version": "2.0.0",
        "diagnostic_id": "auragateway-cu129-p0-p2-platform-diagnostic-v2",
        "source_main_commit": DIAGNOSTIC_SOURCE_MAIN_COMMIT,
        "status": "PASSED",
        "terminal_decision": "P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED",
        "stop_on_first_failure": True,
        "runtime_install_attempts": 1,
        "kernel_compile_and_execution_attempts": 1,
        "hidden_retries_performed": 0,
        "filesystem_mutations_outside_working_directory": 0,
        "global_environment_mutations_performed": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "customer_data_present": False,
        "credentials_used": False,
        "external_spend": 0,
        "full_triton_qualification_attempt_consumed": True,
        "next_gate": "implement_explicit_triton_attention_backend",
    }
    if any(raw.get(key) != value for key, value in exact.items()):
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_SUMMARY_DRIFT",
            "diagnostic summary semantic state drifted",
            SUMMARY_MEMBER,
        )

    probes = _sequence(raw.get("probes"), f"{SUMMARY_MEMBER}.probes")
    expected_probes = [
        {
            "probe_id": "P0",
            "status": "PASSED",
            "decision": "P0_REAL_DRIVER_PREFLIGHT_PASSED",
        },
        {
            "probe_id": "P1",
            "status": "PASSED",
            "decision": "EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED",
        },
        {
            "probe_id": "P2",
            "status": "PASSED",
            "decision": "CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
        },
    ]
    if probes != expected_probes:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_PROBE_SEQUENCE_DRIFT",
            "diagnostic probe sequence drifted",
            SUMMARY_MEMBER,
        )

    safety = SafetyContract(
        model_loads=0,
        worker_starts=0,
        model_requests=0,
        benchmark_trajectory_requests=0,
        network_requests=0,
        hidden_retries_performed=0,
        global_environment_mutations_performed=0,
        filesystem_mutations_outside_working_directory=0,
        credentials_used=False,
        customer_data_present=False,
        external_spend=0,
    )
    return (
        cast(str, raw["terminal_decision"]),
        cast(str, raw["next_gate"]),
        cast(bool, raw["full_triton_qualification_attempt_consumed"]),
        safety,
    )


def build_acceptance_record(
    repo_root: Path,
) -> DiagnosticExecutionAcceptanceRecord:
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_AUTHORIZATION_PRESENT",
            "transient full-run authorization must remain absent",
            AUTHORIZATION_PATH.as_posix(),
        )

    log_payload = _read_bound_file(repo_root, LOG_PATH, LOG_SHA256)
    zip_payload = _read_bound_file(
        repo_root,
        EVIDENCE_ZIP_PATH,
        EVIDENCE_ZIP_SHA256,
    )

    _validate_log(log_payload)
    members = _safe_zip_members(zip_payload)
    zip_members = _validate_manifest(members)
    platform = _platform_contract(members)
    link = _link_contract(members)
    triton = _triton_contract(members)
    terminal, runtime_next_gate, consumed, safety = _summary_and_safety(members)

    return DiagnosticExecutionAcceptanceRecord(
        record_id=("auragateway-cu129-p0-p2-platform-diagnostic-execution-acceptance-v1"),
        status=("P0_P2_PLATFORM_DIAGNOSTIC_EXECUTION_ACCEPTANCE_V1_VALID"),
        integration_base_main_commit=INTEGRATION_BASE_MAIN_COMMIT,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        diagnostic_source_main_commit=DIAGNOSTIC_SOURCE_MAIN_COMMIT,
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
        zip_members=zip_members,
        platform=platform,
        link=link,
        triton=triton,
        safety=safety,
        terminal_decision=cast(
            Literal["P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED"],
            terminal,
        ),
        runtime_next_gate=cast(
            Literal["implement_explicit_triton_attention_backend"],
            runtime_next_gate,
        ),
        full_triton_qualification_attempt_consumed=cast(
            Literal[True],
            consumed,
        ),
        unchanged_diagnostic_replay_authorized=False,
        explicit_attention_backend_v1_implementation_authorized=True,
        next_gate=("design_and_implement_explicit_triton_attention_backend_v1"),
        non_claims=(
            "vLLM import was not tested.",
            "vLLM native extensions were not tested.",
            "An attention backend was not selected or executed.",
            "No model was loaded.",
            "No worker was started.",
            "No inference request was issued.",
            "No A/B/C benchmark trajectory was executed.",
            "Throughput and latency were not measured.",
            "Deployment is not claimed.",
            "Production readiness is not claimed.",
        ),
    )


def generate(
    repo_root: Path,
) -> DiagnosticExecutionAcceptanceRecord:
    record = build_acceptance_record(repo_root)
    payload = _canonical_json(record.model_dump(mode="json")).encode("utf-8")
    _write_atomic(repo_root / ACCEPTANCE_RECORD_PATH, payload)
    return record


def validate(
    repo_root: Path,
) -> DiagnosticExecutionAcceptanceRecord:
    expected = build_acceptance_record(repo_root)
    path = repo_root / ACCEPTANCE_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_RECORD_UNSAFE",
            "acceptance record is missing or unsafe",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )

    expected_payload = _canonical_json(expected.model_dump(mode="json")).encode("utf-8")
    observed_payload = path.read_bytes()
    if observed_payload != expected_payload:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_RECORD_DRIFT",
            "acceptance record differs from fresh rebuild",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        )

    try:
        observed_raw = json.loads(observed_payload.decode("utf-8"))
        observed = DiagnosticExecutionAcceptanceRecord.model_validate(observed_raw)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
    ) as error:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_RECORD_INVALID",
            "acceptance record violates its contract",
            ACCEPTANCE_RECORD_PATH.as_posix(),
        ) from error

    if observed != expected:
        raise DiagnosticAcceptanceError(
            "P0_P2_DIAGNOSTIC_ACCEPTANCE_RECORD_SEMANTIC_DRIFT",
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
            marker = "P0_P2_DIAGNOSTIC_ACCEPTANCE_V1_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "P0_P2_DIAGNOSTIC_ACCEPTANCE_V1_VALIDATED"
        else:
            raise DiagnosticAcceptanceError(
                "P0_P2_DIAGNOSTIC_ACCEPTANCE_COMMAND_UNSUPPORTED",
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
                    "next_gate": record.next_gate,
                    "unchanged_diagnostic_replay_authorized": False,
                    "attention_backend_v1_authorized": True,
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
        DiagnosticAcceptanceError,
    ) as error:
        envelope = (
            error.envelope()
            if isinstance(error, DiagnosticAcceptanceError)
            else {
                "error_code": "P0_P2_DIAGNOSTIC_ACCEPTANCE_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(_canonical_json(envelope), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
