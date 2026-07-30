"""Generate and validate the P0-P2 platform failure classification record."""

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

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

REPOSITORY_BASE_MAIN_COMMIT: Final = "b9cc4b639a2b08595497f396f1a7aa5475a4f519"
DIAGNOSTIC_SOURCE_MAIN_MERGE_COMMIT: Final = "f4f08eda4b4d4747514b4646fe53664d8a78ca6d"
LAUNCHER_SAVED_VERSION_ID: Final = 339111200
LAUNCHER_SAVED_VERSION_URL: Final = (
    "https://www.kaggle.com/code/kabomolefe/"
    "ag-cu129-p0-p2-execution-launcher-v2?scriptVersionId=339111200"
)
LAUNCHER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-execution-launcher-v2"
LAUNCHER_NOTEBOOK_SHA256: Final = "f0fba3680c8386a647ff7cc6af74e549528094731dc94985779be47b03269388"

EVIDENCE_ROOT: Final = Path(
    "evidence_vault/local_abc/cu129-p0-p2-platform-failure-classification-v1"
)
LAUNCHER_LOG_PATH: Final = EVIDENCE_ROOT / ("ag-cu129-p0-p2-execution-launcher-v2-339111200.log")
LAUNCHER_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "ag-cu129-p0-p2-execution-launcher-v2-339111200.zip"
)
PLATFORM_EVIDENCE_PATH: Final = EVIDENCE_ROOT / (
    "ag-cu129-p0-p2-platform-evidence-v1-339111200.zip"
)
CLASSIFICATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_failure_classification_v1.json"
)
BOUND_EVIDENCE_PATHS: Final = (
    LAUNCHER_LOG_PATH,
    LAUNCHER_EVIDENCE_PATH,
    PLATFORM_EVIDENCE_PATH,
)

LAUNCHER_LOG_SHA256: Final = "82af9fbe23113d1586b02cce3c2c15a73912ae8f3b23afc7df83f797fc5f71cc"
LAUNCHER_EVIDENCE_SHA256: Final = "bc962deb82bbb6e009bfd1e10bb41622af3e77cf5e4a70cc7c329b991beba219"
PLATFORM_EVIDENCE_SHA256: Final = "5a80b63da417456d2bc328fb91a97d4a3b8b2768a9b054012d42d92f35633a1b"
LAUNCHER_REPORT_SHA256: Final = "a66d7d214d08db7a0d66d35bdeb40314ae2d9697d832be1ced48f691d01f0d43"
PLATFORM_BUNDLE_MANIFEST_SHA256: Final = (
    "7acf96fcffd97ec828acfccf207cfab7ec399c2cbef99760e3d456d61dd98637"
)
P0_REPORT_SHA256: Final = "a22f8fc3abbbfe949d95574bb3d465c4a2a93325da8c283aedc30e37988c2270"
P1_REPORT_SHA256: Final = "daf07c89b1ae8bc0f81429a762b78eff6d524b140f8cd857f3f70535d465cee3"
P2_REPORT_SHA256: Final = "d6e9eabedbccd490227153f0515d56df53b58f5e2fabbddfdc421f7d8a141741"
SUMMARY_SHA256: Final = "f0c578dc855a04426bea52d8af885bf688d25c45768a44223fcee86f89945069"
HUMAN_REPORT_SHA256: Final = "0331af008d694c687af6d1304530078eb8affe558ed2257a5699beeb048b3d84"

REAL_DRIVER_LINK_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so"
REAL_DRIVER_RESOLVED_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so.580.159.04"
REAL_DRIVER_DIRECTORY: Final = "/usr/local/nvidia/lib64"
LINKER_ERROR: Final = "/usr/bin/ld: cannot find -lcuda: No such file or directory"
REFINED_CLASSIFICATION: Final = (
    "CUDA_DRIVER_LIBRARY_PRESENT_RUNTIME_VISIBLE_BUT_DEFAULT_LINKER_SEARCH_PATH_UNBOUND"
)
TERMINAL_DECISION: Final = "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"
NEXT_GATE: Final = "design_and_validate_explicit_cuda_driver_link_path_probe_v2"

MAXIMUM_EVIDENCE_BYTES: Final = 2 * 1024 * 1024
LAUNCHER_MEMBER_NAMES: Final = frozenset(
    {
        "bundle_manifest.json",
        "materialization_receipt.json",
        "option_c_platform_diagnostic_summary.json",
        "p0_p2_execution_launcher_report_v2.json",
        "sha256_manifest.json",
        "source_inventory.json",
    }
)
PLATFORM_MEMBER_NAMES: Final = frozenset(
    {
        "platform_identity_report.json",
        "cuda_driver_linker_report.json",
        "minimal_triton_kernel_report.json",
        "option_c_platform_diagnostic_summary.json",
        "bundle_manifest.json",
        "human_report.md",
    }
)


class StrictModel(BaseModel):
    """Frozen, extra-forbid model for evidence contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class P0P2PlatformFailureClassificationError(RuntimeError):
    """Fail-closed platform evidence classification error."""

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


class EvidenceIdentity(StrictModel):
    """Immutable repository evidence identity."""

    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class PlatformObservation(StrictModel):
    """P0 platform observations relevant to the linker classification."""

    status: Literal["PASSED"]
    decision: Literal["PLATFORM_IDENTITY_CAPTURED"]
    operating_system: Literal["Ubuntu 22.04.5 LTS"]
    python_version: Literal["3.12.13"]
    gpu_topology: Literal["TESLA_T4_X2_CC75"]
    driver_version: Literal["580.159.04"]
    base_torch_version: Literal["2.10.0+cu128"]
    base_torch_cuda_build: Literal["12.8"]
    torch_cuda_available: Literal[True]
    ctypes_find_library_cuda: Literal["libcuda.so.1"]
    real_driver_link_path: Literal["/usr/local/nvidia/lib64/libcuda.so"]
    real_driver_resolved_path: Literal["/usr/local/nvidia/lib64/libcuda.so.580.159.04"]
    ld_library_path_contains_real_driver_directory: Literal[True]
    library_path: Literal["/usr/local/cuda/lib64/stubs"]


class LinkerObservation(StrictModel):
    """P1 stage attribution and exact native-link result."""

    status: Literal["FAILED"]
    decision: Literal["CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"]
    failure_stage: Literal["cuda_driver_link"]
    compiler_path: Literal["/usr/bin/cc"]
    source_bytes_exact: Literal[True]
    syntax_compile_succeeded: Literal[True]
    link_attempts: Literal[1]
    link_returncode: Literal[1]
    link_command: tuple[str, ...]
    explicit_driver_link_directory_present: Literal[False]
    selected_link_libraries: tuple[str, ...]
    link_library_classification: Literal["UNRESOLVED"]
    linker_error: Literal["/usr/bin/ld: cannot find -lcuda: No such file or directory"]
    loader_resolution_attempts: Literal[0]
    execution_attempts: Literal[0]
    cu_init_executed: Literal[False]

    @model_validator(mode="after")
    def validate_link_command(self) -> Self:
        if "-lcuda" not in self.link_command:
            raise ValueError("link command did not request the CUDA driver library")
        if any(argument.startswith("-L") for argument in self.link_command):
            raise ValueError("link command unexpectedly contains an explicit -L path")
        if self.selected_link_libraries:
            raise ValueError("link command unexpectedly selected a CUDA library")
        return self


class TritonObservation(StrictModel):
    """P2 non-execution boundary."""

    status: Literal["NOT_RUN_DUE_TO_PRIOR_FAILURE"]
    attempts: Literal[0]
    prior_terminal_decision: Literal["CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"]


class SafetyBoundary(StrictModel):
    """Observed zero-budget runtime safety boundary."""

    diagnostic_execution_attempts: Literal[1]
    runtime_install_attempts: Literal[0]
    kernel_compile_and_execution_attempts: Literal[0]
    model_loads: Literal[0]
    worker_starts: Literal[0]
    model_requests: Literal[0]
    benchmark_trajectory_requests: Literal[0]
    network_requests: Literal[0]
    hidden_retries: Literal[0]
    credentials_used: Literal[False]
    customer_data_present: Literal[False]
    external_spend: Literal[0]


class ProbeV2Recommendation(StrictModel):
    """Unexecuted design recommendation for the next diagnostic tranche."""

    status: Literal["DESIGN_RECOMMENDATION_NOT_EXECUTED"]
    real_driver_directory: Literal["/usr/local/nvidia/lib64"]
    required_link_flags: tuple[
        Literal["-L/usr/local/nvidia/lib64"],
        Literal["-Wl,-rpath,/usr/local/nvidia/lib64"],
        Literal["-Wl,-t"],
        Literal["-lcuda"],
    ]
    prohibit_cuda_toolkit_stub: Literal[True]
    require_selected_link_library_real_driver_mount: Literal[True]
    require_ldd_resolution_to_real_driver_mount: Literal[True]
    require_cu_init_zero: Literal[True]
    global_environment_mutation_permitted: Literal[False]
    gpu_replay_authorized: Literal[False]


class P0P2PlatformFailureClassificationRecord(StrictModel):
    """Complete evidence-backed platform failure classification."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-platform-failure-classification-v1"]
    status: Literal["P0_P2_PLATFORM_FAILURE_CLASSIFICATION_V1_VALID"]
    repository_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    diagnostic_source_main_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    launcher_saved_version_id: int = Field(gt=0)
    launcher_saved_version_url: str
    launcher_notebook_name: str
    launcher_notebook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    launcher_log: EvidenceIdentity
    launcher_evidence: EvidenceIdentity
    platform_evidence: EvidenceIdentity
    terminal_decision: Literal["CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"]
    refined_classification: Literal[
        "CUDA_DRIVER_LIBRARY_PRESENT_RUNTIME_VISIBLE_BUT_DEFAULT_LINKER_SEARCH_PATH_UNBOUND"
    ]
    first_divergence: Literal["cuda_driver_link"]
    causal_statement: Literal[
        "The real CUDA driver library was mounted and runtime-visible, but the "
        "default native linker search path did not resolve -lcuda."
    ]
    p0: PlatformObservation
    p1: LinkerObservation
    p2: TritonObservation
    safety: SafetyBoundary
    recommended_probe_v2: ProbeV2Recommendation
    unchanged_replay_authorized: Literal[False]
    platform_incompatible_claimed: Literal[False]
    driver_absent_claimed: Literal[False]
    triton_incompatible_claimed: Literal[False]
    next_gate: Literal["design_and_validate_explicit_cuda_driver_link_path_probe_v2"]

    @model_validator(mode="after")
    def validate_fixed_authorities(self) -> Self:
        expected = {
            "repository_base_main_commit": REPOSITORY_BASE_MAIN_COMMIT,
            "diagnostic_source_main_merge_commit": (DIAGNOSTIC_SOURCE_MAIN_MERGE_COMMIT),
            "launcher_saved_version_id": LAUNCHER_SAVED_VERSION_ID,
            "launcher_saved_version_url": LAUNCHER_SAVED_VERSION_URL,
            "launcher_notebook_name": LAUNCHER_NOTEBOOK_NAME,
            "launcher_notebook_sha256": LAUNCHER_NOTEBOOK_SHA256,
            "terminal_decision": TERMINAL_DECISION,
            "refined_classification": REFINED_CLASSIFICATION,
            "next_gate": NEXT_GATE,
        }
        observed = self.model_dump(mode="python")
        for key, value in expected.items():
            if observed[key] != value:
                raise ValueError(f"fixed classification authority drifted: {key}")
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
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_TEMPORARY_PATH_PRESENT",
            "temporary classification output path already exists",
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
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_EVIDENCE_UNSAFE",
            "required platform evidence is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = path.read_bytes()
    if len(payload) > MAXIMUM_EVIDENCE_BYTES:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_EVIDENCE_TOO_LARGE",
            "platform evidence exceeds the bounded size limit",
            relative_path.as_posix(),
        )
    if _sha256_bytes(payload) != expected_sha256:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_EVIDENCE_DRIFT",
            "platform evidence identity drifted",
            relative_path.as_posix(),
        )
    return payload


def _read_zip_members(
    archive_payload: bytes,
    *,
    expected_names: frozenset[str],
    label: str,
) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_payload)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if set(names) != expected_names or len(names) != len(expected_names):
                raise P0P2PlatformFailureClassificationError(
                    "P0_P2_PLATFORM_CLASSIFICATION_ZIP_MEMBER_SET_DRIFT",
                    "evidence ZIP member set drifted",
                    label,
                )
            result: dict[str, bytes] = {}
            for info in infos:
                path = PurePosixPath(info.filename)
                mode = info.external_attr >> 16
                if path.is_absolute() or ".." in path.parts or info.is_dir() or stat.S_ISLNK(mode):
                    raise P0P2PlatformFailureClassificationError(
                        "P0_P2_PLATFORM_CLASSIFICATION_ZIP_MEMBER_UNSAFE",
                        "evidence ZIP contains an unsafe member",
                        info.filename,
                    )
                result[info.filename] = archive.read(info.filename)
            return result
    except zipfile.BadZipFile as error:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_ZIP_INVALID",
            "evidence ZIP is invalid",
            label,
        ) from error


def _load_json_object(payload: bytes, *, label: str) -> dict[str, object]:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_JSON_INVALID",
            "evidence member is invalid JSON",
            label,
        ) from error
    if not isinstance(raw, dict):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_JSON_ROOT_INVALID",
            "evidence JSON root must be one object",
            label,
        )
    return {str(key): value for key, value in raw.items()}


def _require_value(
    payload: Mapping[str, object],
    key: str,
    expected: object,
    *,
    label: str,
) -> None:
    if payload.get(key) != expected:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_SEMANTIC_DRIFT",
            f"evidence binding drifted: {key}",
            label,
        )


def _parse_log_objects(payload: bytes) -> list[dict[str, object]]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_LOG_INVALID_UTF8",
            "launcher log is not valid UTF-8",
            LAUNCHER_LOG_PATH.as_posix(),
        ) from error
    objects: list[dict[str, object]] = []
    for line in text.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            raw = json.loads(line[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            objects.append({str(key): value for key, value in raw.items()})
    return objects


def _find_status(
    objects: Sequence[dict[str, object]],
    status: str,
) -> dict[str, object]:
    matches = [item for item in objects if item.get("status") == status]
    if len(matches) != 1:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_LOG_STATUS_DRIFT",
            f"expected exactly one log object with status {status}",
            LAUNCHER_LOG_PATH.as_posix(),
        )
    return matches[0]


def _validate_manifest(
    platform_members: Mapping[str, bytes],
) -> None:
    manifest_payload = platform_members["bundle_manifest.json"]
    if _sha256_bytes(manifest_payload) != PLATFORM_BUNDLE_MANIFEST_SHA256:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_MANIFEST_IDENTITY_DRIFT",
            "platform bundle manifest identity drifted",
            "bundle_manifest.json",
        )
    manifest = _load_json_object(manifest_payload, label="bundle_manifest.json")
    _require_value(
        manifest,
        "source_main_merge_commit",
        DIAGNOSTIC_SOURCE_MAIN_MERGE_COMMIT,
        label="bundle_manifest.json",
    )
    raw_members = manifest.get("members")
    if not isinstance(raw_members, list) or len(raw_members) != 5:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_MANIFEST_MEMBER_SET_DRIFT",
            "platform bundle manifest member set drifted",
            "bundle_manifest.json",
        )
    observed: dict[str, tuple[str, int]] = {}
    for raw_member in raw_members:
        if not isinstance(raw_member, dict):
            raise P0P2PlatformFailureClassificationError(
                "P0_P2_PLATFORM_CLASSIFICATION_MANIFEST_MEMBER_INVALID",
                "platform bundle manifest member is invalid",
                "bundle_manifest.json",
            )
        path = raw_member.get("path")
        sha256 = raw_member.get("sha256")
        size_bytes = raw_member.get("size_bytes")
        if (
            not isinstance(path, str)
            or not isinstance(sha256, str)
            or not isinstance(size_bytes, int)
        ):
            raise P0P2PlatformFailureClassificationError(
                "P0_P2_PLATFORM_CLASSIFICATION_MANIFEST_IDENTITY_INVALID",
                "platform bundle manifest identity is invalid",
                "bundle_manifest.json",
            )
        observed[path] = (sha256, size_bytes)
    expected = {
        "platform_identity_report.json": (P0_REPORT_SHA256, 55608),
        "cuda_driver_linker_report.json": (P1_REPORT_SHA256, 3221),
        "minimal_triton_kernel_report.json": (P2_REPORT_SHA256, 514),
        "option_c_platform_diagnostic_summary.json": (SUMMARY_SHA256, 1000),
        "human_report.md": (HUMAN_REPORT_SHA256, 907),
    }
    if observed != expected:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_MANIFEST_BINDING_DRIFT",
            "platform bundle manifest bindings drifted",
            "bundle_manifest.json",
        )
    for name, (expected_sha256, expected_size) in expected.items():
        payload = platform_members[name]
        if len(payload) != expected_size or _sha256_bytes(payload) != expected_sha256:
            raise P0P2PlatformFailureClassificationError(
                "P0_P2_PLATFORM_CLASSIFICATION_MEMBER_IDENTITY_DRIFT",
                "platform evidence member identity drifted",
                name,
            )


def _extract_platform_observation(
    payload: Mapping[str, object],
) -> PlatformObservation:
    _require_value(payload, "status", "PASSED", label="platform_identity_report.json")
    _require_value(
        payload,
        "decision",
        "PLATFORM_IDENTITY_CAPTURED",
        label="platform_identity_report.json",
    )
    platform_raw = payload.get("platform")
    python_raw = payload.get("python")
    torch_raw = payload.get("base_torch")
    environment_raw = payload.get("allowlisted_environment")
    candidates_raw = payload.get("libcuda_candidates")
    nvidia_smi_raw = payload.get("nvidia_smi")
    if not all(
        isinstance(item, dict)
        for item in (
            platform_raw,
            python_raw,
            torch_raw,
            environment_raw,
            nvidia_smi_raw,
        )
    ) or not isinstance(candidates_raw, list):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_P0_STRUCTURE_INVALID",
            "P0 platform evidence structure is invalid",
            "platform_identity_report.json",
        )
    platform_data = cast(dict[str, object], platform_raw)
    python_data = cast(dict[str, object], python_raw)
    torch_data = cast(dict[str, object], torch_raw)
    environment = cast(dict[str, object], environment_raw)
    nvidia_smi = cast(dict[str, object], nvidia_smi_raw)
    os_release = platform_data.get("os_release")
    if not isinstance(os_release, dict):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_OS_RELEASE_INVALID",
            "P0 operating-system evidence is invalid",
            "platform_identity_report.json",
        )
    real_candidate = None
    for raw_candidate in candidates_raw:
        if not isinstance(raw_candidate, dict):
            continue
        if raw_candidate.get("path") == REAL_DRIVER_LINK_PATH:
            real_candidate = raw_candidate
            break
    if real_candidate is None:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_REAL_DRIVER_MISSING",
            "expected real CUDA driver mount was not observed",
            "platform_identity_report.json",
        )
    expected_candidate = {
        "classification": "REAL_OR_DRIVER_MOUNT",
        "exists": True,
        "is_symlink": True,
        "path": REAL_DRIVER_LINK_PATH,
        "resolved_path": REAL_DRIVER_RESOLVED_PATH,
        "size_bytes": 96284520,
    }
    if any(real_candidate.get(key) != value for key, value in expected_candidate.items()):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_REAL_DRIVER_DRIFT",
            "real CUDA driver mount identity drifted",
            "platform_identity_report.json",
        )
    devices = torch_data.get("devices")
    if not isinstance(devices, list) or len(devices) != 2:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_GPU_TOPOLOGY_DRIFT",
            "dual-T4 topology evidence drifted",
            "platform_identity_report.json",
        )
    if any(
        not isinstance(device, dict)
        or device.get("name") != "Tesla T4"
        or device.get("compute_capability") != [7, 5]
        for device in devices
    ):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_GPU_IDENTITY_DRIFT",
            "T4 device identity drifted",
            "platform_identity_report.json",
        )
    _require_value(
        nvidia_smi,
        "returncode",
        0,
        label="platform_identity_report.json",
    )
    if "580.159.04" not in str(nvidia_smi.get("stdout", "")):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_DRIVER_VERSION_DRIFT",
            "NVIDIA driver version evidence drifted",
            "platform_identity_report.json",
        )
    ld_library_path = str(environment.get("LD_LIBRARY_PATH", ""))
    return PlatformObservation(
        status="PASSED",
        decision="PLATFORM_IDENTITY_CAPTURED",
        operating_system=cast(
            Literal["Ubuntu 22.04.5 LTS"],
            os_release.get("PRETTY_NAME"),
        ),
        python_version=cast(Literal["3.12.13"], python_data.get("version")),
        gpu_topology="TESLA_T4_X2_CC75",
        driver_version="580.159.04",
        base_torch_version=cast(
            Literal["2.10.0+cu128"],
            torch_data.get("version"),
        ),
        base_torch_cuda_build=cast(Literal["12.8"], torch_data.get("cuda_build")),
        torch_cuda_available=cast(Literal[True], torch_data.get("cuda_available")),
        ctypes_find_library_cuda=cast(
            Literal["libcuda.so.1"],
            payload.get("ctypes_find_library_cuda"),
        ),
        real_driver_link_path=REAL_DRIVER_LINK_PATH,
        real_driver_resolved_path=REAL_DRIVER_RESOLVED_PATH,
        ld_library_path_contains_real_driver_directory=(
            REAL_DRIVER_DIRECTORY in ld_library_path.split(":")
        ),
        library_path=cast(
            Literal["/usr/local/cuda/lib64/stubs"],
            environment.get("LIBRARY_PATH"),
        ),
    )


def _extract_linker_observation(
    payload: Mapping[str, object],
) -> LinkerObservation:
    expected: dict[str, object] = {
        "status": "FAILED",
        "decision": TERMINAL_DECISION,
        "failure_stage": "cuda_driver_link",
        "compiler_path": "/usr/bin/cc",
        "selected_link_libraries": [],
        "link_library_classification": "UNRESOLVED",
        "ldd_result": None,
        "execution_result": None,
    }
    for key, value in expected.items():
        _require_value(payload, key, value, label="cuda_driver_linker_report.json")
    source_contract = payload.get("source_contract")
    syntax_result = payload.get("syntax_compile_result")
    link_result = payload.get("link_result")
    budgets = payload.get("budgets")
    if not all(
        isinstance(item, dict) for item in (source_contract, syntax_result, link_result, budgets)
    ):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_P1_STRUCTURE_INVALID",
            "P1 linker evidence structure is invalid",
            "cuda_driver_linker_report.json",
        )
    source_data = cast(dict[str, object], source_contract)
    syntax_data = cast(dict[str, object], syntax_result)
    link_data = cast(dict[str, object], link_result)
    budget_data = cast(dict[str, object], budgets)
    _require_value(
        source_data,
        "exact_bytes",
        True,
        label="cuda_driver_linker_report.json",
    )
    _require_value(
        source_data,
        "literal_backslash_n_present",
        False,
        label="cuda_driver_linker_report.json",
    )
    _require_value(
        syntax_data,
        "returncode",
        0,
        label="cuda_driver_linker_report.json",
    )
    _require_value(
        link_data,
        "returncode",
        1,
        label="cuda_driver_linker_report.json",
    )
    stderr = str(link_data.get("stderr", ""))
    if LINKER_ERROR not in stderr:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_LINKER_ERROR_DRIFT",
            "P1 linker error drifted",
            "cuda_driver_linker_report.json",
        )
    argv = link_data.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_LINK_COMMAND_INVALID",
            "P1 link command is invalid",
            "cuda_driver_linker_report.json",
        )
    return LinkerObservation(
        status="FAILED",
        decision=TERMINAL_DECISION,
        failure_stage="cuda_driver_link",
        compiler_path="/usr/bin/cc",
        source_bytes_exact=True,
        syntax_compile_succeeded=True,
        link_attempts=cast(Literal[1], budget_data.get("link_attempts")),
        link_returncode=1,
        link_command=tuple(argv),
        explicit_driver_link_directory_present=False,
        selected_link_libraries=(),
        link_library_classification="UNRESOLVED",
        linker_error=LINKER_ERROR,
        loader_resolution_attempts=cast(
            Literal[0],
            budget_data.get("loader_resolution_attempts"),
        ),
        execution_attempts=cast(
            Literal[0],
            budget_data.get("execution_attempts"),
        ),
        cu_init_executed=False,
    )


def _extract_triton_observation(
    payload: Mapping[str, object],
) -> TritonObservation:
    _require_value(
        payload,
        "status",
        "NOT_RUN_DUE_TO_PRIOR_FAILURE",
        label="minimal_triton_kernel_report.json",
    )
    _require_value(
        payload,
        "prior_terminal_decision",
        TERMINAL_DECISION,
        label="minimal_triton_kernel_report.json",
    )
    budgets = payload.get("budgets")
    if not isinstance(budgets, dict):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_P2_BUDGET_INVALID",
            "P2 budget evidence is invalid",
            "minimal_triton_kernel_report.json",
        )
    return TritonObservation(
        status="NOT_RUN_DUE_TO_PRIOR_FAILURE",
        attempts=cast(Literal[0], budgets.get("attempts")),
        prior_terminal_decision=TERMINAL_DECISION,
    )


def _record_bytes(record: P0P2PlatformFailureClassificationRecord) -> bytes:
    return _canonical_json(record.model_dump(mode="json")).encode("utf-8")


def build_classification_record(
    repo_root: Path,
) -> P0P2PlatformFailureClassificationRecord:
    """Build the evidence-backed classification record."""

    log_payload = _read_bound_file(
        repo_root,
        LAUNCHER_LOG_PATH,
        LAUNCHER_LOG_SHA256,
    )
    launcher_archive = _read_bound_file(
        repo_root,
        LAUNCHER_EVIDENCE_PATH,
        LAUNCHER_EVIDENCE_SHA256,
    )
    platform_archive = _read_bound_file(
        repo_root,
        PLATFORM_EVIDENCE_PATH,
        PLATFORM_EVIDENCE_SHA256,
    )
    launcher_members = _read_zip_members(
        launcher_archive,
        expected_names=LAUNCHER_MEMBER_NAMES,
        label=LAUNCHER_EVIDENCE_PATH.as_posix(),
    )
    platform_members = _read_zip_members(
        platform_archive,
        expected_names=PLATFORM_MEMBER_NAMES,
        label=PLATFORM_EVIDENCE_PATH.as_posix(),
    )
    _validate_manifest(platform_members)

    if launcher_members["bundle_manifest.json"] != platform_members["bundle_manifest.json"]:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_CROSS_ARCHIVE_MANIFEST_DRIFT",
            "launcher and platform bundle manifests differ",
        )
    if (
        launcher_members["option_c_platform_diagnostic_summary.json"]
        != platform_members["option_c_platform_diagnostic_summary.json"]
    ):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_CROSS_ARCHIVE_SUMMARY_DRIFT",
            "launcher and platform summaries differ",
        )

    launcher_report_payload = launcher_members["p0_p2_execution_launcher_report_v2.json"]
    if _sha256_bytes(launcher_report_payload) != LAUNCHER_REPORT_SHA256:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_LAUNCHER_REPORT_DRIFT",
            "launcher report identity drifted",
            "p0_p2_execution_launcher_report_v2.json",
        )
    launcher_report = _load_json_object(
        launcher_report_payload,
        label="p0_p2_execution_launcher_report_v2.json",
    )
    launcher_expected = {
        "status": "P0_P2_EXECUTION_LAUNCHER_COMPLETED_V2",
        "notebook_name": LAUNCHER_NOTEBOOK_NAME,
        "terminal_decision": TERMINAL_DECISION,
        "diagnostic_status": "FAILED_CLOSED",
        "diagnostic_execution_attempts": 1,
        "runtime_install_attempts": 0,
        "kernel_compile_and_execution_attempts": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "external_spend": 0,
        "diagnostic_evidence_zip_sha256": PLATFORM_EVIDENCE_SHA256,
        "next_gate": "preserve_evidence_and_classify_platform_failure",
    }
    for key, value in launcher_expected.items():
        _require_value(
            launcher_report,
            key,
            value,
            label="p0_p2_execution_launcher_report_v2.json",
        )

    summary = _load_json_object(
        platform_members["option_c_platform_diagnostic_summary.json"],
        label="option_c_platform_diagnostic_summary.json",
    )
    summary_expected = {
        "status": "FAILED_CLOSED",
        "terminal_decision": TERMINAL_DECISION,
        "source_main_merge_commit": DIAGNOSTIC_SOURCE_MAIN_MERGE_COMMIT,
        "stop_on_first_failure": True,
        "full_triton_qualification_attempt_consumed": False,
        "hidden_retries_performed": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "external_spend": 0,
    }
    for key, value in summary_expected.items():
        _require_value(
            summary,
            key,
            value,
            label="option_c_platform_diagnostic_summary.json",
        )

    log_objects = _parse_log_objects(log_payload)
    diagnostic_log = _find_status(log_objects, "FAILED_CLOSED")
    launcher_log = _find_status(
        log_objects,
        "P0_P2_EXECUTION_LAUNCHER_COMPLETED_V2",
    )
    for observed in (diagnostic_log, launcher_log):
        _require_value(
            observed,
            "terminal_decision",
            TERMINAL_DECISION,
            label=LAUNCHER_LOG_PATH.as_posix(),
        )
    _require_value(
        diagnostic_log,
        "evidence_zip_sha256",
        PLATFORM_EVIDENCE_SHA256,
        label=LAUNCHER_LOG_PATH.as_posix(),
    )
    _require_value(
        launcher_log,
        "launcher_evidence_zip_sha256",
        LAUNCHER_EVIDENCE_SHA256,
        label=LAUNCHER_LOG_PATH.as_posix(),
    )

    p0 = _extract_platform_observation(
        _load_json_object(
            platform_members["platform_identity_report.json"],
            label="platform_identity_report.json",
        )
    )
    p1 = _extract_linker_observation(
        _load_json_object(
            platform_members["cuda_driver_linker_report.json"],
            label="cuda_driver_linker_report.json",
        )
    )
    p2 = _extract_triton_observation(
        _load_json_object(
            platform_members["minimal_triton_kernel_report.json"],
            label="minimal_triton_kernel_report.json",
        )
    )

    return P0P2PlatformFailureClassificationRecord(
        record_id=("auragateway-cu129-p0-p2-platform-failure-classification-v1"),
        status="P0_P2_PLATFORM_FAILURE_CLASSIFICATION_V1_VALID",
        repository_base_main_commit=REPOSITORY_BASE_MAIN_COMMIT,
        diagnostic_source_main_merge_commit=DIAGNOSTIC_SOURCE_MAIN_MERGE_COMMIT,
        launcher_saved_version_id=LAUNCHER_SAVED_VERSION_ID,
        launcher_saved_version_url=LAUNCHER_SAVED_VERSION_URL,
        launcher_notebook_name=LAUNCHER_NOTEBOOK_NAME,
        launcher_notebook_sha256=LAUNCHER_NOTEBOOK_SHA256,
        launcher_log=EvidenceIdentity(
            repository_path=LAUNCHER_LOG_PATH.as_posix(),
            sha256=LAUNCHER_LOG_SHA256,
            size_bytes=len(log_payload),
        ),
        launcher_evidence=EvidenceIdentity(
            repository_path=LAUNCHER_EVIDENCE_PATH.as_posix(),
            sha256=LAUNCHER_EVIDENCE_SHA256,
            size_bytes=len(launcher_archive),
        ),
        platform_evidence=EvidenceIdentity(
            repository_path=PLATFORM_EVIDENCE_PATH.as_posix(),
            sha256=PLATFORM_EVIDENCE_SHA256,
            size_bytes=len(platform_archive),
        ),
        terminal_decision=TERMINAL_DECISION,
        refined_classification=REFINED_CLASSIFICATION,
        first_divergence="cuda_driver_link",
        causal_statement=(
            "The real CUDA driver library was mounted and runtime-visible, but "
            "the default native linker search path did not resolve -lcuda."
        ),
        p0=p0,
        p1=p1,
        p2=p2,
        safety=SafetyBoundary(
            diagnostic_execution_attempts=1,
            runtime_install_attempts=0,
            kernel_compile_and_execution_attempts=0,
            model_loads=0,
            worker_starts=0,
            model_requests=0,
            benchmark_trajectory_requests=0,
            network_requests=0,
            hidden_retries=0,
            credentials_used=False,
            customer_data_present=False,
            external_spend=0,
        ),
        recommended_probe_v2=ProbeV2Recommendation(
            status="DESIGN_RECOMMENDATION_NOT_EXECUTED",
            real_driver_directory=REAL_DRIVER_DIRECTORY,
            required_link_flags=(
                "-L/usr/local/nvidia/lib64",
                "-Wl,-rpath,/usr/local/nvidia/lib64",
                "-Wl,-t",
                "-lcuda",
            ),
            prohibit_cuda_toolkit_stub=True,
            require_selected_link_library_real_driver_mount=True,
            require_ldd_resolution_to_real_driver_mount=True,
            require_cu_init_zero=True,
            global_environment_mutation_permitted=False,
            gpu_replay_authorized=False,
        ),
        unchanged_replay_authorized=False,
        platform_incompatible_claimed=False,
        driver_absent_claimed=False,
        triton_incompatible_claimed=False,
        next_gate=NEXT_GATE,
    )


def generate(
    repo_root: Path,
) -> P0P2PlatformFailureClassificationRecord:
    """Generate the canonical classification record."""

    record = build_classification_record(repo_root)
    _write_bytes_atomic(
        repo_root / CLASSIFICATION_RECORD_PATH,
        _record_bytes(record),
    )
    print("P0_P2_PLATFORM_FAILURE_CLASSIFICATION_RECORD_GENERATED=true")
    print(record.model_dump_json())
    return record


def validate(
    repo_root: Path,
) -> P0P2PlatformFailureClassificationRecord:
    """Validate the canonical classification record and bound evidence."""

    expected = build_classification_record(repo_root)
    path = repo_root / CLASSIFICATION_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_RECORD_MISSING",
            "platform failure classification record is missing or unsafe",
            CLASSIFICATION_RECORD_PATH.as_posix(),
        )
    if path.read_bytes() != _record_bytes(expected):
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_RECORD_DRIFT",
            "platform failure classification record differs from generated state",
            CLASSIFICATION_RECORD_PATH.as_posix(),
        )
    return expected


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P0P2PlatformFailureClassificationError(
            "P0_P2_PLATFORM_CLASSIFICATION_ARGUMENT_INVALID",
            message,
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> Never:
    arguments = _parser().parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    try:
        if arguments.command == "generate":
            generate(repo_root)
        else:
            record = validate(repo_root)
            print(record.model_dump_json())
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        P0P2PlatformFailureClassificationError,
    ) as error:
        if isinstance(error, P0P2PlatformFailureClassificationError):
            payload = error.envelope()
        else:
            payload = {
                "error_code": "P0_P2_PLATFORM_CLASSIFICATION_UNEXPECTED_ERROR",
                "safe_message": str(error),
                "path": None,
            }
        print(_canonical_json(cast(object, payload)), file=sys.stderr)
        raise SystemExit(2) from error
    raise SystemExit(0)


if __name__ == "__main__":
    main()
