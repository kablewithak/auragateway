"""Generate and validate the explicit CUDA driver link-path probe V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_COMMIT: Final = "f7ed2a6aec0fe47b3cde3941c476af10fb70a291"

CLASSIFICATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_failure_classification_v1.json"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "explicit_cuda_driver_link_path_probe_v2_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_cuda_driver_link_path_probe_v2_review.json"
)
NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_explicit_cuda_driver_link_path_probe_v2.ipynb"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_explicit_cuda_driver_link_path_probe_v2_record.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

NOTEBOOK_NAME: Final = "ag-cu129-explicit-driver-link-probe-v2"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-explicit-driver-link-failed-v2"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-explicit-driver-link-evidence-v2.zip"
OUTPUT_DIRECTORY_NAME: Final = "ag_cu129_explicit_driver_link_probe_v2"

REAL_DRIVER_DIRECTORY: Final = "/usr/local/nvidia/lib64"
REAL_DRIVER_LINK_PATH: Final = "/usr/local/nvidia/lib64/libcuda.so"
CUDA_STUB_DIRECTORY: Final = "/usr/local/cuda/lib64/stubs"

REQUIRED_LINK_FLAGS: Final = (
    "-L/usr/local/nvidia/lib64",
    "-Wl,-rpath,/usr/local/nvidia/lib64",
    "-Wl,-t",
    "-lcuda",
)

REQUIRED_OUTPUTS: Final = (
    "platform_identity_report_v2.json",
    "explicit_cuda_driver_link_report_v2.json",
    "explicit_cuda_driver_link_summary_v2.json",
    "bundle_manifest_v2.json",
    "human_report_v2.md",
)

MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
MAXIMUM_GENERATED_LINE_LENGTH: Final = 100

KAGGLE_PROGRAM: Final = r"""
from __future__ import annotations

import ctypes.util
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = "2.0.0"
PROBE_ID = "auragateway-cu129-explicit-cuda-driver-link-path-probe-v2"
SOURCE_MAIN_COMMIT = "f7ed2a6aec0fe47b3cde3941c476af10fb70a291"
NOTEBOOK_NAME = "ag-cu129-explicit-driver-link-probe-v2"

OUTPUT_DIRECTORY = Path(
    "/kaggle/working/ag_cu129_explicit_driver_link_probe_v2"
)
EVIDENCE_ZIP = Path(
    "/kaggle/working/ag-cu129-explicit-driver-link-evidence-v2.zip"
)

REAL_DRIVER_DIRECTORY = Path("/usr/local/nvidia/lib64")
REAL_DRIVER_LINK_PATH = Path("/usr/local/nvidia/lib64/libcuda.so")
CUDA_STUB_DIRECTORY = Path("/usr/local/cuda/lib64/stubs")

REQUIRED_LINK_FLAGS = (
    "-L/usr/local/nvidia/lib64",
    "-Wl,-rpath,/usr/local/nvidia/lib64",
    "-Wl,-t",
    "-lcuda",
)

REQUIRED_OUTPUTS = (
    "platform_identity_report_v2.json",
    "explicit_cuda_driver_link_report_v2.json",
    "explicit_cuda_driver_link_summary_v2.json",
    "bundle_manifest_v2.json",
    "human_report_v2.md",
)

P1_C_SOURCE = (
    b"extern int cuInit(unsigned int);\n"
    b"int main(void) { return cuInit(0); }\n"
)
P1_C_SOURCE_SHA256 = hashlib.sha256(P1_C_SOURCE).hexdigest()

CREDENTIAL_ENVIRONMENT_NAMES = (
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "KAGGLE_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)

ALLOWLISTED_ENVIRONMENT = (
    "BUILD_DATE",
    "GIT_COMMIT",
    "KAGGLE_KERNEL_RUN_TYPE",
    "KAGGLE_CONTAINER_NAME",
    "LD_LIBRARY_PATH",
    "LIBRARY_PATH",
    "CUDA_HOME",
    "CUDA_PATH",
)

MAXIMUM_CAPTURE_CHARACTERS = 24000
COMMAND_TIMEOUT_SECONDS = 120
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounded(value: str) -> str:
    if len(value) <= MAXIMUM_CAPTURE_CHARACTERS:
        return value
    return value[-MAXIMUM_CAPTURE_CHARACTERS:]


def run_command(argv: list[str]) -> dict[str, object]:
    started_at = datetime.now(UTC).isoformat()
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        return {
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": bounded(completed.stdout),
            "stderr": bounded(completed.stderr),
            "timed_out": False,
            "started_at": started_at,
            "completed_at": datetime.now(UTC).isoformat(),
        }
    except subprocess.TimeoutExpired as error:
        stdout = (
            error.stdout.decode("utf-8", errors="replace")
            if isinstance(error.stdout, bytes)
            else (error.stdout or "")
        )
        stderr = (
            error.stderr.decode("utf-8", errors="replace")
            if isinstance(error.stderr, bytes)
            else (error.stderr or "")
        )
        return {
            "argv": argv,
            "returncode": None,
            "stdout": bounded(stdout),
            "stderr": bounded(stderr),
            "timed_out": True,
            "started_at": started_at,
            "completed_at": datetime.now(UTC).isoformat(),
        }
    except OSError as error:
        return {
            "argv": argv,
            "returncode": None,
            "stdout": "",
            "stderr": bounded(f"{type(error).__name__}: {error}"),
            "timed_out": False,
            "started_at": started_at,
            "completed_at": datetime.now(UTC).isoformat(),
        }


def write_json(name: str, payload: object) -> None:
    (OUTPUT_DIRECTORY / name).write_text(
        canonical_json(payload),
        encoding="utf-8",
    )


def is_within(path: Path, root: Path) -> bool:
    resolved_path = path.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    return (
        resolved_path == resolved_root
        or resolved_root in resolved_path.parents
    )


def parse_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.is_file():
        return {}

    result: dict[str, str] = {}
    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        result[key] = value.strip().strip('"')
    return result


def discover_cuda_candidates() -> list[dict[str, object]]:
    roots = (
        REAL_DRIVER_DIRECTORY,
        Path("/usr/local/cuda/lib64"),
        CUDA_STUB_DIRECTORY,
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/lib/x86_64-linux-gnu"),
    )
    seen: set[str] = set()
    observations: list[dict[str, object]] = []

    for root in roots:
        if not root.exists():
            continue

        for path in sorted(root.glob("libcuda.so*")):
            normalized = str(path)
            if normalized in seen:
                continue
            seen.add(normalized)

            observations.append(
                {
                    "path": normalized,
                    "exists": path.exists(),
                    "is_symlink": path.is_symlink(),
                    "resolved_path": (
                        str(path.resolve()) if path.exists() else None
                    ),
                    "classification": (
                        "CUDA_TOOLKIT_STUB"
                        if is_within(path, CUDA_STUB_DIRECTORY)
                        else "REAL_OR_DRIVER_MOUNT"
                    ),
                }
            )

    return observations


def platform_identity() -> tuple[dict[str, object], bool]:
    credentials = sorted(
        name
        for name in CREDENTIAL_ENVIRONMENT_NAMES
        if os.environ.get(name)
    )
    environment = {
        name: os.environ.get(name)
        for name in ALLOWLISTED_ENVIRONMENT
    }

    nvidia_smi = run_command(
        [
            shutil.which("nvidia-smi") or "nvidia-smi",
            "--query-gpu=index,name,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )

    torch_observation: dict[str, object]
    try:
        import torch

        devices = [
            {
                "index": index,
                "name": torch.cuda.get_device_name(index),
                "compute_capability": list(
                    torch.cuda.get_device_capability(index)
                ),
            }
            for index in range(torch.cuda.device_count())
        ]

        torch_observation = {
            "imported": True,
            "version": torch.__version__,
            "cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count(),
            "devices": devices,
        }
    except Exception as error:
        torch_observation = {
            "imported": False,
            "error_type": type(error).__name__,
            "safe_error": bounded(str(error)),
        }

    link_exists = REAL_DRIVER_LINK_PATH.exists()
    resolved_link = (
        REAL_DRIVER_LINK_PATH.resolve()
        if link_exists
        else None
    )
    resolved_real = (
        resolved_link is not None
        and is_within(resolved_link, REAL_DRIVER_DIRECTORY)
        and not is_within(resolved_link, CUDA_STUB_DIRECTORY)
    )

    devices = torch_observation.get("devices")
    dual_t4 = (
        isinstance(devices, list)
        and len(devices) == 2
        and all(
            isinstance(item, dict)
            and "T4" in str(item.get("name", "")).upper()
            and item.get("compute_capability") == [7, 5]
            for item in devices
        )
    )

    build_identity = bool(
        environment.get("BUILD_DATE")
        and environment.get("GIT_COMMIT")
    )
    compiler_available = shutil.which("cc") is not None
    tools_available = all(
        shutil.which(name) is not None
        for name in ("ld", "ldd", "readelf")
    )

    passed = (
        not credentials
        and build_identity
        and nvidia_smi.get("returncode") == 0
        and torch_observation.get("cuda_available") is True
        and dual_t4
        and compiler_available
        and tools_available
        and resolved_real
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "probe_id": PROBE_ID,
        "stage": "P0",
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASSED" if passed else "FAILED",
        "decision": (
            "EXPLICIT_DRIVER_LINK_PREFLIGHT_PASSED"
            if passed
            else "DIAGNOSTIC_INVALID"
        ),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "os_release": parse_os_release(),
        },
        "allowlisted_environment": environment,
        "credential_environment_names_present": credentials,
        "nvidia_smi": nvidia_smi,
        "torch": torch_observation,
        "ctypes_find_library_cuda": ctypes.util.find_library("cuda"),
        "cuda_candidates": discover_cuda_candidates(),
        "real_driver_directory": str(REAL_DRIVER_DIRECTORY),
        "real_driver_link_path": str(REAL_DRIVER_LINK_PATH),
        "real_driver_link_exists": link_exists,
        "real_driver_resolved_path": (
            None if resolved_link is None else str(resolved_link)
        ),
        "checks": {
            "credentials_absent": not credentials,
            "build_identity_complete": build_identity,
            "nvidia_smi_succeeded": (
                nvidia_smi.get("returncode") == 0
            ),
            "torch_cuda_available": (
                torch_observation.get("cuda_available") is True
            ),
            "dual_t4_topology": dual_t4,
            "compiler_available": compiler_available,
            "linker_loader_tools_available": tools_available,
            "real_driver_link_present": link_exists,
            "real_driver_link_resolves_inside_real_mount": resolved_real,
        },
        "budgets": {
            "platform_identity_attempts": 1,
            "link_attempts": 0,
            "loader_resolution_attempts": 0,
            "driver_initialization_attempts": 0,
            "hidden_retries": 0,
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "external_spend": 0,
        },
    }
    return report, passed


def parse_link_trace(value: str) -> list[str]:
    candidates: set[str] = set()

    for raw_line in value.splitlines():
        tokens = (
            raw_line.replace("(", " ")
            .replace(")", " ")
            .split()
        )
        for raw_token in tokens:
            token = raw_token.strip()
            if "libcuda.so" not in token:
                continue

            path = Path(token)
            candidates.add(
                str(path.resolve(strict=False))
                if path.is_absolute()
                else token
            )

    return sorted(candidates)


def parse_ldd_cuda_path(value: str) -> str | None:
    for line in value.splitlines():
        if "libcuda.so.1" not in line or "=>" not in line:
            continue

        candidate = (
            line.split("=>", maxsplit=1)[1]
            .strip()
            .split()[0]
        )
        if candidate == "not":
            return None
        return candidate

    return None


def explicit_driver_link_probe() -> tuple[dict[str, object], bool]:
    workspace = OUTPUT_DIRECTORY / "explicit_link_workspace"
    workspace.mkdir(parents=True)

    source = workspace / "cuda_driver_link_probe.c"
    object_file = workspace / "cuda_driver_link_probe.o"
    executable = workspace / "cuda_driver_link_probe"

    source.write_bytes(P1_C_SOURCE)
    observed_source = source.read_bytes()
    source_exact = observed_source == P1_C_SOURCE
    source_sha256 = hashlib.sha256(observed_source).hexdigest()

    compiler = shutil.which("cc")
    syntax_result: dict[str, object] | None = None
    link_result: dict[str, object] | None = None
    readelf_result: dict[str, object] | None = None
    ldd_result: dict[str, object] | None = None
    execution_result: dict[str, object] | None = None

    selected_libraries: list[str] = []
    runtime_library_path: str | None = None
    decision = "DIAGNOSTIC_INVALID"
    failure_stage = "source_validation"

    real_link_valid = (
        REAL_DRIVER_LINK_PATH.exists()
        and is_within(
            REAL_DRIVER_LINK_PATH.resolve(),
            REAL_DRIVER_DIRECTORY,
        )
        and not is_within(
            REAL_DRIVER_LINK_PATH.resolve(),
            CUDA_STUB_DIRECTORY,
        )
    )

    if (
        source_exact
        and source_sha256 == P1_C_SOURCE_SHA256
        and compiler is not None
        and real_link_valid
    ):
        failure_stage = "syntax_compilation"
        syntax_result = run_command(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-c",
                str(source),
                "-o",
                str(object_file),
            ]
        )

        syntax_passed = (
            syntax_result.get("returncode") == 0
            and object_file.is_file()
        )

        if syntax_passed:
            failure_stage = "explicit_cuda_driver_link"
            link_result = run_command(
                [
                    compiler,
                    str(object_file),
                    *REQUIRED_LINK_FLAGS,
                    "-o",
                    str(executable),
                ]
            )

            trace = (
                str(link_result.get("stdout", ""))
                + "\n"
                + str(link_result.get("stderr", ""))
            )
            selected_libraries = parse_link_trace(trace)

            selected_real = bool(selected_libraries) and all(
                is_within(Path(path), REAL_DRIVER_DIRECTORY)
                and not is_within(Path(path), CUDA_STUB_DIRECTORY)
                for path in selected_libraries
            )

            link_passed = (
                link_result.get("returncode") == 0
                and executable.is_file()
                and selected_real
            )

            if link_passed:
                failure_stage = "elf_dynamic_contract"
                readelf_result = run_command(
                    [
                        shutil.which("readelf") or "readelf",
                        "-d",
                        str(executable),
                    ]
                )

                dynamic_text = str(
                    readelf_result.get("stdout", "")
                )
                needed_ok = (
                    "Shared library: [libcuda.so.1]"
                    in dynamic_text
                )
                runpath_ok = (
                    "Library runpath: [/usr/local/nvidia/lib64]"
                    in dynamic_text
                    or "Library rpath: [/usr/local/nvidia/lib64]"
                    in dynamic_text
                )

                elf_passed = (
                    readelf_result.get("returncode") == 0
                    and needed_ok
                    and runpath_ok
                )

                if elf_passed:
                    failure_stage = "dynamic_loader_resolution"
                    ldd_result = run_command(
                        [
                            shutil.which("ldd") or "ldd",
                            str(executable),
                        ]
                    )
                    runtime_library_path = parse_ldd_cuda_path(
                        str(ldd_result.get("stdout", ""))
                    )

                    runtime_real = (
                        runtime_library_path is not None
                        and is_within(
                            Path(runtime_library_path),
                            REAL_DRIVER_DIRECTORY,
                        )
                        and not is_within(
                            Path(runtime_library_path),
                            CUDA_STUB_DIRECTORY,
                        )
                    )

                    loader_passed = (
                        ldd_result.get("returncode") == 0
                        and runtime_real
                    )

                    if loader_passed:
                        failure_stage = "driver_initialization"
                        execution_result = run_command(
                            [str(executable)]
                        )

                        if execution_result.get("returncode") == 0:
                            decision = (
                                "EXPLICIT_CUDA_DRIVER_LINK_PATH_"
                                "CONTRACT_PASSED"
                            )
                            failure_stage = "none"
                        else:
                            decision = (
                                "EXPLICIT_CUDA_DRIVER_"
                                "INITIALIZATION_FAILED"
                            )
                    else:
                        decision = (
                            "EXPLICIT_CUDA_DRIVER_DYNAMIC_LOADER_FAILED"
                        )
                else:
                    decision = (
                        "EXPLICIT_CUDA_DRIVER_ELF_CONTRACT_FAILED"
                    )
            else:
                stub_selected = any(
                    is_within(Path(path), CUDA_STUB_DIRECTORY)
                    for path in selected_libraries
                )
                decision = (
                    "CUDA_TOOLKIT_STUB_SELECTED"
                    if stub_selected
                    else "EXPLICIT_CUDA_DRIVER_LINK_FAILED"
                )
        else:
            decision = "DIAGNOSTIC_INVALID"
    elif not real_link_valid:
        decision = "REAL_DRIVER_LINK_PATH_MISSING"

    passed = (
        decision
        == "EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "probe_id": PROBE_ID,
        "stage": "P1_V2",
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASSED" if passed else "FAILED",
        "decision": decision,
        "failure_stage": failure_stage,
        "source_contract": {
            "expected_sha256": P1_C_SOURCE_SHA256,
            "observed_sha256": source_sha256,
            "exact_bytes": source_exact,
            "newline_count": observed_source.count(b"\n"),
            "literal_backslash_n_present": (
                b"\\n" in observed_source
            ),
        },
        "compiler_path": compiler,
        "real_driver_directory": str(REAL_DRIVER_DIRECTORY),
        "real_driver_link_path": str(REAL_DRIVER_LINK_PATH),
        "cuda_stub_directory": str(CUDA_STUB_DIRECTORY),
        "required_link_flags": list(REQUIRED_LINK_FLAGS),
        "syntax_compile_result": syntax_result,
        "link_result": link_result,
        "selected_link_libraries": selected_libraries,
        "readelf_result": readelf_result,
        "ldd_result": ldd_result,
        "runtime_library_path": runtime_library_path,
        "execution_result": execution_result,
        "environment_overrides_applied": [],
        "checks": {
            "source_exact": source_exact,
            "compiler_available": compiler is not None,
            "real_driver_link_valid": real_link_valid,
            "syntax_compile_succeeded": (
                syntax_result is not None
                and syntax_result.get("returncode") == 0
            ),
            "link_succeeded": (
                link_result is not None
                and link_result.get("returncode") == 0
            ),
            "selected_link_library_real": (
                bool(selected_libraries)
                and all(
                    is_within(
                        Path(path),
                        REAL_DRIVER_DIRECTORY,
                    )
                    and not is_within(
                        Path(path),
                        CUDA_STUB_DIRECTORY,
                    )
                    for path in selected_libraries
                )
            ),
            "elf_needed_libcuda_so_1": (
                readelf_result is not None
                and "Shared library: [libcuda.so.1]"
                in str(readelf_result.get("stdout", ""))
            ),
            "elf_runpath_real_driver_directory": (
                readelf_result is not None
                and (
                    "Library runpath: [/usr/local/nvidia/lib64]"
                    in str(readelf_result.get("stdout", ""))
                    or (
                        "Library rpath: "
                        "[/usr/local/nvidia/lib64]"
                    )
                    in str(readelf_result.get("stdout", ""))
                )
            ),
            "runtime_library_real": (
                runtime_library_path is not None
                and is_within(
                    Path(runtime_library_path),
                    REAL_DRIVER_DIRECTORY,
                )
                and not is_within(
                    Path(runtime_library_path),
                    CUDA_STUB_DIRECTORY,
                )
            ),
            "cu_init_zero": (
                execution_result is not None
                and execution_result.get("returncode") == 0
            ),
            "global_environment_mutation_absent": True,
            "cuda_toolkit_stub_rejected": not any(
                is_within(Path(path), CUDA_STUB_DIRECTORY)
                for path in selected_libraries
            ),
        },
        "budgets": {
            "source_materialization_attempts": 1,
            "syntax_compile_attempts": (
                1 if syntax_result is not None else 0
            ),
            "link_attempts": (
                1 if link_result is not None else 0
            ),
            "elf_inspection_attempts": (
                1 if readelf_result is not None else 0
            ),
            "loader_resolution_attempts": (
                1 if ldd_result is not None else 0
            ),
            "driver_initialization_attempts": (
                1 if execution_result is not None else 0
            ),
            "hidden_retries": 0,
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "external_spend": 0,
        },
    }
    return report, passed


def not_run_report(prior_decision: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "probe_id": PROBE_ID,
        "stage": "P1_V2",
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "NOT_RUN_DUE_TO_PREFLIGHT_FAILURE",
        "decision": prior_decision,
        "failure_stage": "platform_preflight",
        "environment_overrides_applied": [],
        "budgets": {
            "source_materialization_attempts": 0,
            "syntax_compile_attempts": 0,
            "link_attempts": 0,
            "elf_inspection_attempts": 0,
            "loader_resolution_attempts": 0,
            "driver_initialization_attempts": 0,
            "hidden_retries": 0,
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "external_spend": 0,
        },
    }


def write_human_report(summary: dict[str, object]) -> None:
    lines = [
        "# AuraGateway explicit CUDA driver link-path probe V2",
        "",
        f"- Status: `{summary['status']}`",
        (
            "- Terminal decision: "
            f"`{summary['terminal_decision']}`"
        ),
        "",
        "## Boundary",
        "",
        "- P0 platform preflight",
        "- P1 V2 explicit real-driver link path",
        "- No P2",
        "- No runtime installation",
        "- No model or worker",
        "- No network",
        "- No global linker-environment mutation",
        "",
        "## Next gate",
        "",
        f"`{summary['next_gate']}`",
        "",
        "## Non-claims",
        "",
        (
            "This probe does not establish Triton compatibility, "
            "vLLM readiness, model inference, measured A/B/C, "
            "deployment, or production readiness."
        ),
        "",
    ]
    (OUTPUT_DIRECTORY / "human_report_v2.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_bundle_manifest() -> None:
    members = []
    for name in REQUIRED_OUTPUTS:
        if name == "bundle_manifest_v2.json":
            continue

        path = OUTPUT_DIRECTORY / name
        members.append(
            {
                "path": name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    write_json(
        "bundle_manifest_v2.json",
        {
            "schema_version": SCHEMA_VERSION,
            "bundle_id": (
                "auragateway-cu129-explicit-cuda-driver-"
                "link-evidence-v2"
            ),
            "probe_id": PROBE_ID,
            "source_main_commit": SOURCE_MAIN_COMMIT,
            "members": members,
        },
    )


def write_fixed_zip_member(
    archive: zipfile.ZipFile,
    *,
    name: str,
    payload: bytes,
) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or len(path.parts) != 1:
        raise RuntimeError(f"unsafe evidence member: {name}")

    info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100644 & 0xFFFF) << 16
    archive.writestr(info, payload)


def build_evidence_zip() -> None:
    if EVIDENCE_ZIP.exists():
        raise RuntimeError("evidence ZIP already exists")

    with zipfile.ZipFile(
        EVIDENCE_ZIP,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in sorted(REQUIRED_OUTPUTS):
            write_fixed_zip_member(
                archive,
                name=name,
                payload=(OUTPUT_DIRECTORY / name).read_bytes(),
            )


def main() -> None:
    if OUTPUT_DIRECTORY.exists() or EVIDENCE_ZIP.exists():
        raise RuntimeError("probe output path already exists")

    OUTPUT_DIRECTORY.mkdir(parents=True)

    p0_report, p0_passed = platform_identity()
    write_json("platform_identity_report_v2.json", p0_report)

    if p0_passed:
        p1_report, p1_passed = explicit_driver_link_probe()
    else:
        p1_report = not_run_report("DIAGNOSTIC_INVALID")
        p1_passed = False

    write_json(
        "explicit_cuda_driver_link_report_v2.json",
        p1_report,
    )

    terminal_decision = str(p1_report["decision"])
    passed = (
        p0_passed
        and p1_passed
        and terminal_decision
        == "EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "probe_id": PROBE_ID,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASSED" if passed else "FAILED_CLOSED",
        "terminal_decision": terminal_decision,
        "p0_status": p0_report["status"],
        "p1_status": p1_report["status"],
        "stop_on_first_failure": True,
        "hidden_retries_performed": 0,
        "global_environment_mutations_performed": 0,
        "p2_performed": False,
        "runtime_install_attempts": 0,
        "kernel_compile_and_execution_attempts": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "credentials_used": False,
        "customer_data_present": False,
        "external_spend": 0,
        "next_gate": (
            "integrate_explicit_driver_link_path_into_"
            "p0_p2_diagnostic_v2"
            if passed
            else (
                "preserve_and_classify_explicit_driver_"
                "link_probe_failure"
            )
        ),
    }

    write_json(
        "explicit_cuda_driver_link_summary_v2.json",
        summary,
    )
    write_human_report(summary)
    write_bundle_manifest()
    build_evidence_zip()

    print(
        canonical_json(
            {
                "status": summary["status"],
                "terminal_decision": terminal_decision,
                "evidence_zip": str(EVIDENCE_ZIP),
                "evidence_zip_sha256": sha256_file(
                    EVIDENCE_ZIP
                ),
                "p2_performed": False,
                "runtime_install_attempts": 0,
                "kernel_compile_and_execution_attempts": 0,
                "model_loads": 0,
                "worker_starts": 0,
                "model_requests": 0,
                "benchmark_trajectory_requests": 0,
                "network_requests": 0,
                "external_spend": 0,
            }
        )
    )


main()
""".strip()


class ExplicitDriverLinkProbeError(RuntimeError):
    """Fail-closed probe generation or validation error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ExplicitDriverLinkProbeError(message)


class _StrictModel(LocalABCContract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ClassificationP0Authority(_StrictModel):
    real_driver_link_path: Literal["/usr/local/nvidia/lib64/libcuda.so"]
    torch_cuda_available: Literal[True]
    ld_library_path_contains_real_driver_directory: Literal[True]
    library_path: Literal["/usr/local/cuda/lib64/stubs"]


class ClassificationP1Authority(_StrictModel):
    failure_stage: Literal["cuda_driver_link"]
    explicit_driver_link_directory_present: Literal[False]
    syntax_compile_succeeded: Literal[True]
    link_returncode: Literal[1]
    linker_error: Literal["/usr/bin/ld: cannot find -lcuda: No such file or directory"]
    selected_link_libraries: tuple[str, ...]


class ProbeV2RecommendationAuthority(_StrictModel):
    status: Literal["DESIGN_RECOMMENDATION_NOT_EXECUTED"]
    real_driver_directory: Literal["/usr/local/nvidia/lib64"]
    required_link_flags: tuple[str, str, str, str]
    prohibit_cuda_toolkit_stub: Literal[True]
    require_selected_link_library_real_driver_mount: Literal[True]
    require_ldd_resolution_to_real_driver_mount: Literal[True]
    require_cu_init_zero: Literal[True]
    global_environment_mutation_permitted: Literal[False]
    gpu_replay_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_flags(self) -> Self:
        if self.required_link_flags != REQUIRED_LINK_FLAGS:
            raise ValueError("classification-recommended link flags drifted")
        return self


class ClassificationAuthority(_StrictModel):
    status: Literal["P0_P2_PLATFORM_FAILURE_CLASSIFICATION_V1_VALID"]
    launcher_saved_version_id: Literal[339111200]
    first_divergence: Literal["cuda_driver_link"]
    terminal_decision: Literal["CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"]
    refined_classification: Literal[
        "CUDA_DRIVER_LIBRARY_PRESENT_RUNTIME_VISIBLE_BUT_DEFAULT_LINKER_SEARCH_PATH_UNBOUND"
    ]
    next_gate: Literal["design_and_validate_explicit_cuda_driver_link_path_probe_v2"]
    unchanged_replay_authorized: Literal[False]
    p0: ClassificationP0Authority
    p1: ClassificationP1Authority
    recommended_probe_v2: ProbeV2RecommendationAuthority


class SafetyBoundary(_StrictModel):
    authorization_issued: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installations_performed: Literal[0] = 0
    kernel_compile_and_execution_attempts: Literal[0] = 0
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests: Literal[0] = 0
    benchmark_trajectory_requests: Literal[0] = 0
    network_requests: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0


class ProbeRequest(_StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    request_id: Literal["auragateway-cu129-explicit-cuda-driver-link-path-probe-v2-request"]
    source_main_commit: Literal["f7ed2a6aec0fe47b3cde3941c476af10fb70a291"]
    classification_record_path: str
    notebook_name: str
    failed_notebook_name: str
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    attached_inputs_required: Literal[0]
    maximum_sessions: Literal[1]
    maximum_platform_preflight_attempts: Literal[1]
    maximum_source_materialization_attempts: Literal[1]
    maximum_syntax_compile_attempts: Literal[1]
    maximum_link_attempts: Literal[1]
    maximum_elf_inspection_attempts: Literal[1]
    maximum_loader_resolution_attempts: Literal[1]
    maximum_driver_initialization_attempts: Literal[1]
    maximum_runtime_install_attempts: Literal[0]
    maximum_kernel_compile_and_execution_attempts: Literal[0]
    maximum_model_loads: Literal[0]
    maximum_worker_starts: Literal[0]
    maximum_model_requests: Literal[0]
    maximum_benchmark_trajectory_requests: Literal[0]
    maximum_network_requests: Literal[0]
    global_environment_mutation_permitted: Literal[False]
    cuda_toolkit_stub_permitted: Literal[False]
    filesystem_mutation_scope: Literal["KAGGLE_WORKING_DIRECTORY_ONLY"]
    evidence_zip_name: str
    required_outputs: tuple[str, ...]
    next_gate_on_pass: Literal["integrate_explicit_driver_link_path_into_p0_p2_diagnostic_v2"]
    next_gate_on_failure: Literal["preserve_and_classify_explicit_driver_link_probe_failure"]

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.classification_record_path != (CLASSIFICATION_RECORD_PATH.as_posix()):
            raise ValueError("classification record path drifted")
        if self.notebook_name != NOTEBOOK_NAME:
            raise ValueError("notebook name drifted")
        if self.failed_notebook_name != FAILED_NOTEBOOK_NAME:
            raise ValueError("failed notebook name drifted")
        if self.evidence_zip_name != EVIDENCE_ZIP_NAME:
            raise ValueError("evidence ZIP name drifted")
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("required output set drifted")

        for value in (
            self.notebook_name,
            self.failed_notebook_name,
        ):
            if len(value) > MAXIMUM_KAGGLE_NAME_CHARACTERS:
                raise ValueError("Kaggle notebook name exceeds 50 characters")

        return self


class ProbeReview(_StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-explicit-cuda-driver-link-path-probe-v2-review"]
    source_main_commit: Literal["f7ed2a6aec0fe47b3cde3941c476af10fb70a291"]
    decision: Literal["STANDALONE_EXPLICIT_DRIVER_LINK_PATH_PROBE"]
    architecture_requirements: tuple[str, ...]
    prohibited_techniques: tuple[str, ...]
    safety: SafetyBoundary
    execution_authorized_after_merge: Literal[True]
    next_gate: Literal["generate_and_validate_explicit_cuda_driver_link_path_probe_v2"]

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        expected_requirements = {
            "typed_classification_authority",
            "standalone_probe_not_v1_mutation",
            "exact_real_driver_directory",
            "cuda_toolkit_stub_rejection",
            "explicit_link_trace",
            "elf_needed_and_runpath_validation",
            "dynamic_loader_resolution_validation",
            "cu_init_zero_validation",
            "single_attempt_per_stage",
            "deterministic_notebook_generation",
            "bounded_evidence_bundle",
        }
        if set(self.architecture_requirements) != expected_requirements:
            raise ValueError("architecture requirement set drifted")

        expected_prohibitions = {
            "manual_notebook_edits",
            "global_library_path_mutation",
            "global_ld_library_path_mutation",
            "cuda_toolkit_stub_linking",
            "wheelhouse_installation",
            "triton_execution",
            "model_or_worker_execution",
            "network_access",
            "hidden_retries",
            "existing_p0_p2_v1_mutation",
        }
        if set(self.prohibited_techniques) != expected_prohibitions:
            raise ValueError("prohibited technique set drifted")

        return self


class NotebookReceipt(_StrictModel):
    notebook_name: str
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cell_count: Literal[2] = 2
    outputs_present: Literal[False] = False
    execution_counts_present: Literal[False] = False
    maximum_code_line_length: int = Field(ge=1, le=100)


class ProbeImplementationRecord(_StrictModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-explicit-cuda-driver-link-path-probe-v2-record"]
    status: Literal["EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2_VALID"]
    source_main_commit: Literal["f7ed2a6aec0fe47b3cde3941c476af10fb70a291"]
    classification_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook: NotebookReceipt
    real_driver_directory: Literal["/usr/local/nvidia/lib64"]
    real_driver_link_path: Literal["/usr/local/nvidia/lib64/libcuda.so"]
    cuda_stub_directory: Literal["/usr/local/cuda/lib64/stubs"]
    required_link_flags: tuple[str, str, str, str]
    evidence_zip_name: str
    output_directory_name: str
    required_outputs: tuple[str, ...]
    accelerator: Literal["T4_X2"]
    internet_enabled: Literal[False]
    attached_inputs_required: Literal[0]
    generation_deterministic: Literal[True]
    safety: SafetyBoundary
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    execution_authorized_after_merge: Literal[True]
    next_gate: Literal["execute_governed_explicit_cuda_driver_link_path_probe_v2"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.notebook.notebook_name != NOTEBOOK_NAME:
            raise ValueError("notebook name drifted")
        if self.notebook.repository_path != NOTEBOOK_PATH.as_posix():
            raise ValueError("notebook path drifted")
        if self.required_link_flags != REQUIRED_LINK_FLAGS:
            raise ValueError("required link flags drifted")
        if self.evidence_zip_name != EVIDENCE_ZIP_NAME:
            raise ValueError("evidence ZIP name drifted")
        if self.output_directory_name != OUTPUT_DIRECTORY_NAME:
            raise ValueError("output directory name drifted")
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("required output set drifted")
        return self


@dataclass(frozen=True)
class GeneratedProbe:
    request: ProbeRequest
    review: ProbeReview
    notebook_bytes: bytes
    record: ProbeImplementationRecord


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _model_bytes(model: _StrictModel) -> bytes:
    return _canonical_json(model.model_dump(mode="json")).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise ExplicitDriverLinkProbeError(f"temporary path already exists: {temporary}")

    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ExplicitDriverLinkProbeError(f"required JSON file is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ExplicitDriverLinkProbeError(f"required JSON file is invalid: {path}") from error

    if not isinstance(raw, dict):
        raise ExplicitDriverLinkProbeError(f"JSON root must be one object: {path}")

    return {str(key): value for key, value in raw.items()}


def _project_nested_authority(
    raw: dict[str, object],
    *,
    key: str,
    fields: tuple[str, ...],
) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ExplicitDriverLinkProbeError(
            f"classification authority field must be one object: {key}"
        )

    normalized: dict[str, object] = {
        str(nested_key): nested_value for nested_key, nested_value in value.items()
    }
    return {field: normalized.get(field) for field in fields}


def _classification_projection(
    raw: dict[str, object],
) -> dict[str, object]:
    return {
        "status": raw.get("status"),
        "launcher_saved_version_id": raw.get("launcher_saved_version_id"),
        "first_divergence": raw.get("first_divergence"),
        "terminal_decision": raw.get("terminal_decision"),
        "refined_classification": raw.get("refined_classification"),
        "next_gate": raw.get("next_gate"),
        "unchanged_replay_authorized": raw.get("unchanged_replay_authorized"),
        "p0": _project_nested_authority(
            raw,
            key="p0",
            fields=(
                "real_driver_link_path",
                "torch_cuda_available",
                "ld_library_path_contains_real_driver_directory",
                "library_path",
            ),
        ),
        "p1": _project_nested_authority(
            raw,
            key="p1",
            fields=(
                "failure_stage",
                "explicit_driver_link_directory_present",
                "syntax_compile_succeeded",
                "link_returncode",
                "linker_error",
                "selected_link_libraries",
            ),
        ),
        "recommended_probe_v2": _project_nested_authority(
            raw,
            key="recommended_probe_v2",
            fields=(
                "status",
                "real_driver_directory",
                "required_link_flags",
                "prohibit_cuda_toolkit_stub",
                "require_selected_link_library_real_driver_mount",
                "require_ldd_resolution_to_real_driver_mount",
                "require_cu_init_zero",
                "global_environment_mutation_permitted",
                "gpu_replay_authorized",
            ),
        ),
    }


def _load_classification_authority(
    repo_root: Path,
) -> tuple[ClassificationAuthority, str]:
    raw = _load_json_object(repo_root / CLASSIFICATION_RECORD_PATH)
    projection = _classification_projection(raw)

    try:
        authority = ClassificationAuthority.model_validate(projection)
    except ValidationError as error:
        raise ExplicitDriverLinkProbeError(
            "platform-failure classification authority drifted"
        ) from error

    authority_bytes = _canonical_json(authority.model_dump(mode="json")).encode("utf-8")

    return authority, _sha256_bytes(authority_bytes)


def _request() -> ProbeRequest:
    return ProbeRequest(
        request_id=("auragateway-cu129-explicit-cuda-driver-link-path-probe-v2-request"),
        source_main_commit=SOURCE_MAIN_COMMIT,
        classification_record_path=(CLASSIFICATION_RECORD_PATH.as_posix()),
        notebook_name=NOTEBOOK_NAME,
        failed_notebook_name=FAILED_NOTEBOOK_NAME,
        accelerator="T4_X2",
        internet_enabled=False,
        attached_inputs_required=0,
        maximum_sessions=1,
        maximum_platform_preflight_attempts=1,
        maximum_source_materialization_attempts=1,
        maximum_syntax_compile_attempts=1,
        maximum_link_attempts=1,
        maximum_elf_inspection_attempts=1,
        maximum_loader_resolution_attempts=1,
        maximum_driver_initialization_attempts=1,
        maximum_runtime_install_attempts=0,
        maximum_kernel_compile_and_execution_attempts=0,
        maximum_model_loads=0,
        maximum_worker_starts=0,
        maximum_model_requests=0,
        maximum_benchmark_trajectory_requests=0,
        maximum_network_requests=0,
        global_environment_mutation_permitted=False,
        cuda_toolkit_stub_permitted=False,
        filesystem_mutation_scope=("KAGGLE_WORKING_DIRECTORY_ONLY"),
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        required_outputs=REQUIRED_OUTPUTS,
        next_gate_on_pass=("integrate_explicit_driver_link_path_into_p0_p2_diagnostic_v2"),
        next_gate_on_failure=("preserve_and_classify_explicit_driver_link_probe_failure"),
    )


def _review() -> ProbeReview:
    return ProbeReview(
        record_id=("auragateway-cu129-explicit-cuda-driver-link-path-probe-v2-review"),
        source_main_commit=SOURCE_MAIN_COMMIT,
        decision=("STANDALONE_EXPLICIT_DRIVER_LINK_PATH_PROBE"),
        architecture_requirements=(
            "typed_classification_authority",
            "standalone_probe_not_v1_mutation",
            "exact_real_driver_directory",
            "cuda_toolkit_stub_rejection",
            "explicit_link_trace",
            "elf_needed_and_runpath_validation",
            "dynamic_loader_resolution_validation",
            "cu_init_zero_validation",
            "single_attempt_per_stage",
            "deterministic_notebook_generation",
            "bounded_evidence_bundle",
        ),
        prohibited_techniques=(
            "manual_notebook_edits",
            "global_library_path_mutation",
            "global_ld_library_path_mutation",
            "cuda_toolkit_stub_linking",
            "wheelhouse_installation",
            "triton_execution",
            "model_or_worker_execution",
            "network_access",
            "hidden_retries",
            "existing_p0_p2_v1_mutation",
        ),
        safety=SafetyBoundary(),
        execution_authorized_after_merge=True,
        next_gate=("generate_and_validate_explicit_cuda_driver_link_path_probe_v2"),
    )


def _maximum_line_length(source: str) -> int:
    return max(
        (len(line) for line in source.splitlines()),
        default=0,
    )


def _validate_program(source: str) -> int:
    try:
        compile(source, NOTEBOOK_NAME, "exec")
    except SyntaxError as error:
        raise ExplicitDriverLinkProbeError("generated Kaggle program does not compile") from error

    maximum = _maximum_line_length(source)
    if maximum > MAXIMUM_GENERATED_LINE_LENGTH:
        raise ExplicitDriverLinkProbeError(
            f"generated Kaggle program exceeds line-length policy: {maximum}"
        )

    required_fragments = (
        REAL_DRIVER_DIRECTORY,
        REAL_DRIVER_LINK_PATH,
        CUDA_STUB_DIRECTORY,
        *REQUIRED_LINK_FLAGS,
        "readelf",
        "ldd",
        "cu_init_zero",
        "global_environment_mutations_performed",
        "p2_performed",
        ("EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED"),
    )
    for fragment in required_fragments:
        if fragment not in source:
            raise ExplicitDriverLinkProbeError(
                f"generated program is missing required fragment: {fragment}"
            )

    prohibited_fragments = (
        'os.environ["LIBRARY_PATH"] =',
        'os.environ["LD_LIBRARY_PATH"] =',
        "pip install",
        "import triton",
        "import vllm",
        "AutoModel",
        "requests.",
        "urllib.",
        "socket.",
        "-L/usr/local/cuda/lib64/stubs",
    )
    for fragment in prohibited_fragments:
        if fragment in source:
            raise ExplicitDriverLinkProbeError(
                f"generated program contains prohibited fragment: {fragment}"
            )

    return maximum


def _notebook_bytes(
    source: str,
    classification_authority_sha256: str,
) -> bytes:
    payload = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    ("# AuraGateway explicit CUDA driver link-path probe V2\n"),
                    "\n",
                    (
                        "Model-free standalone diagnostic. It "
                        "validates the real driver link path, "
                        "rejects CUDA toolkit stubs, inspects ELF "
                        "and loader resolution, and requires "
                        "cuInit(0) to return zero. It does not run "
                        "Triton or install a runtime.\n"
                    ),
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "auragateway": {
                "classification_authority_sha256": (classification_authority_sha256),
                "notebook_name": NOTEBOOK_NAME,
                "source_main_commit": SOURCE_MAIN_COMMIT,
                "real_driver_directory": (REAL_DRIVER_DIRECTORY),
                "cuda_stub_directory": (CUDA_STUB_DIRECTORY),
                "evidence_zip_name": EVIDENCE_ZIP_NAME,
                "attached_inputs_required": 0,
                "p2_permitted": False,
                "model_loads_permitted": 0,
                "worker_starts_permitted": 0,
                "model_requests_permitted": 0,
            },
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def build_generated_probe(
    repo_root: Path,
) -> GeneratedProbe:
    """Build all deterministic outputs in memory."""

    if (repo_root / AUTHORIZATION_PATH).exists():
        raise ExplicitDriverLinkProbeError("transient full-run authorization must remain absent")

    _, authority_sha256 = _load_classification_authority(repo_root)
    request = _request()
    review = _review()
    maximum = _validate_program(KAGGLE_PROGRAM)

    notebook_first = _notebook_bytes(
        KAGGLE_PROGRAM,
        authority_sha256,
    )
    notebook_second = _notebook_bytes(
        KAGGLE_PROGRAM,
        authority_sha256,
    )

    if notebook_first != notebook_second:
        raise ExplicitDriverLinkProbeError("two notebook builds differ")

    request_bytes = _model_bytes(request)
    review_bytes = _model_bytes(review)

    record = ProbeImplementationRecord(
        record_id=("auragateway-cu129-explicit-cuda-driver-link-path-probe-v2-record"),
        status=("EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2_VALID"),
        source_main_commit=SOURCE_MAIN_COMMIT,
        classification_authority_sha256=(authority_sha256),
        request_sha256=_sha256_bytes(request_bytes),
        review_sha256=_sha256_bytes(review_bytes),
        notebook=NotebookReceipt(
            notebook_name=NOTEBOOK_NAME,
            repository_path=NOTEBOOK_PATH.as_posix(),
            sha256=_sha256_bytes(notebook_first),
            maximum_code_line_length=maximum,
        ),
        real_driver_directory=REAL_DRIVER_DIRECTORY,
        real_driver_link_path=REAL_DRIVER_LINK_PATH,
        cuda_stub_directory=CUDA_STUB_DIRECTORY,
        required_link_flags=REQUIRED_LINK_FLAGS,
        evidence_zip_name=EVIDENCE_ZIP_NAME,
        output_directory_name=OUTPUT_DIRECTORY_NAME,
        required_outputs=REQUIRED_OUTPUTS,
        accelerator="T4_X2",
        internet_enabled=False,
        attached_inputs_required=0,
        generation_deterministic=True,
        safety=SafetyBoundary(),
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        execution_authorized_after_merge=True,
        next_gate=("execute_governed_explicit_cuda_driver_link_path_probe_v2"),
        non_claims=(
            ("The explicit driver-link probe has not been executed."),
            ("The current Kaggle image has not passed explicit-path linking."),
            ("ELF NEEDED and RUNPATH have not been observed at runtime."),
            ("Dynamic loader resolution has not been observed."),
            ("cuInit(0) has not been executed by this repository change."),
            ("Triton compatibility has not been evaluated by this probe."),
            ("The governed CUDA 12.9 runtime has not been installed."),
            ("No model has been loaded and no worker has been started."),
            ("No inference or benchmark trajectory has been executed."),
            ("Deployment and production readiness are not claimed."),
        ),
    )

    return GeneratedProbe(
        request=request,
        review=review,
        notebook_bytes=notebook_first,
        record=record,
    )


def generate(
    repo_root: Path,
) -> ProbeImplementationRecord:
    """Generate request, review, notebook and record."""

    generated = build_generated_probe(repo_root)
    outputs = {
        REQUEST_PATH: _model_bytes(generated.request),
        REVIEW_PATH: _model_bytes(generated.review),
        NOTEBOOK_PATH: generated.notebook_bytes,
        RECORD_PATH: _model_bytes(generated.record),
    }

    for relative, payload in outputs.items():
        _write_bytes_atomic(
            repo_root / relative,
            payload,
        )

    return generated.record


def validate(
    repo_root: Path,
) -> ProbeImplementationRecord:
    """Validate generated outputs against a fresh rebuild."""

    expected = build_generated_probe(repo_root)
    outputs = {
        REQUEST_PATH: _model_bytes(expected.request),
        REVIEW_PATH: _model_bytes(expected.review),
        NOTEBOOK_PATH: expected.notebook_bytes,
        RECORD_PATH: _model_bytes(expected.record),
    }

    for relative, expected_bytes in outputs.items():
        path = repo_root / relative
        if not path.is_file() or path.is_symlink():
            raise ExplicitDriverLinkProbeError(f"generated output is missing or unsafe: {relative}")

        if path.read_bytes() != expected_bytes:
            raise ExplicitDriverLinkProbeError(f"generated output drifted: {relative}")

    observed_record_raw = _load_json_object(repo_root / RECORD_PATH)
    try:
        observed_record = ProbeImplementationRecord.model_validate(observed_record_raw)
    except ValidationError as error:
        raise ExplicitDriverLinkProbeError("implementation record violates its contract") from error

    if observed_record != expected.record:
        raise ExplicitDriverLinkProbeError("implementation record differs from rebuild")

    return expected.record


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


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(
            Path,
            arguments.repo_root,
        ).resolve()

        if arguments.command == "generate":
            record = generate(repo_root)
            marker = "EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2_GENERATED"
        elif arguments.command == "validate":
            record = validate(repo_root)
            marker = "EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2_VALIDATED"
        else:
            raise ExplicitDriverLinkProbeError(f"unsupported command: {arguments.command}")

        print(
            _canonical_json(
                {
                    "status": record.status,
                    "marker": marker,
                    "notebook_sha256": (record.notebook.sha256),
                    "classification_authority_sha256": (record.classification_authority_sha256),
                    "next_gate": record.next_gate,
                    "kaggle_execution_performed": False,
                    "gpu_execution_performed": False,
                    "model_requests": 0,
                    "external_spend": 0,
                }
            )
        )
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        ValidationError,
        ExplicitDriverLinkProbeError,
    ) as error:
        payload = {
            "error_code": ("EXPLICIT_DRIVER_LINK_PROBE_V2_FAILED"),
            "safe_message": str(error),
            "exception_type": type(error).__name__,
        }
        print(
            _canonical_json(cast(object, payload)),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
