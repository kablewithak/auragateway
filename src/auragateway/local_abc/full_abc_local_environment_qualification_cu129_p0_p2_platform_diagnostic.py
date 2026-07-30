"""Generate and validate the governed CUDA 12.9 P0-P2 platform diagnostic."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_MERGE_COMMIT: Final = "f4f08eda4b4d4747514b4646fe53664d8a78ca6d"
DECISION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_option_c_runtime_diagnostic_decision_v1.json"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "option_c_p0_p2_platform_diagnostic_request.json"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb")
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-platform-diagnostic-v1"
FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-platform-diag-failed-v1"
EVIDENCE_ZIP_NAME: Final = "ag-cu129-p0-p2-platform-evidence-v1.zip"
RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
REQUIRED_OUTPUTS: Final = (
    "platform_identity_report.json",
    "cuda_driver_linker_report.json",
    "minimal_triton_kernel_report.json",
    "option_c_platform_diagnostic_summary.json",
    "bundle_manifest.json",
    "human_report.md",
)
MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
P1_C_SOURCE_EXPECTED: Final = (
    b"extern int cuInit(unsigned int);\nint main(void) { return cuInit(0); }\n"
)
P1_C_SOURCE_SHA256: Final = hashlib.sha256(P1_C_SOURCE_EXPECTED).hexdigest()
P1_FAILURE_DECISIONS: Final = (
    "DIAGNOSTIC_INVALID",
    "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
    "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED",
)
INVALID_KAGGLE_VERSION: Final = "338921762"
INVALID_PLATFORM_EVIDENCE_SHA256: Final = (
    "dc8b5404a4182decd5e600ec4bb3f28d36f9ece836a336e72cd89f2b6bf90728"
)
KAGGLE_PROGRAM: Final = r'''
from __future__ import annotations

import ctypes.util
import glob
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = "1.0.0"
DIAGNOSTIC_ID = "auragateway-cu129-p0-p2-platform-diagnostic-v1"
SOURCE_MAIN_MERGE_COMMIT = "f4f08eda4b4d4747514b4646fe53664d8a78ca6d"
RUNTIME_OUTPUT_DIRECTORY = "auragateway_vllm_cu129_wheelhouse_v1"
EXPECTED_PACKAGE_COUNT = 176
EXPECTED_CONTROL_HASHES = {
    "requirements.in": "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f",
    "resolution_lock.json": "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c",
    "materialization.lock.txt": "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d",
    "requirements.lock.txt": "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27",
    "install_runtime.py": "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821",
    "runtime_manifest.json": "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51",
    "sha256_manifest.json": "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d",
    "materialization_receipt.json": (
        "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
    ),
}
OUTPUT_DIRECTORY = Path("/kaggle/working/ag_cu129_p0_p2_platform_diagnostic_v1")
EVIDENCE_ZIP = Path("/kaggle/working/ag-cu129-p0-p2-platform-evidence-v1.zip")
REQUIRED_OUTPUTS = (
    "platform_identity_report.json",
    "cuda_driver_linker_report.json",
    "minimal_triton_kernel_report.json",
    "option_c_platform_diagnostic_summary.json",
    "bundle_manifest.json",
    "human_report.md",
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
MAXIMUM_CAPTURE_CHARACTERS = 24000
COMMAND_TIMEOUT_SECONDS = 120
RUNTIME_INSTALL_TIMEOUT_SECONDS = 1800
P1_C_SOURCE = (
    b"extern int cuInit(unsigned int);\n"
    b"int main(void) { return cuInit(0); }\n"
)
P1_C_SOURCE_SHA256 = hashlib.sha256(P1_C_SOURCE).hexdigest()
P1_FAILURE_DECISIONS = {
    "source_invalid": "DIAGNOSTIC_INVALID",
    "syntax_compile_failed": "DIAGNOSTIC_INVALID",
    "link_failed": "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
    "loader_resolution_failed": "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
    "driver_initialization_failed": (
        "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED"
    ),
}

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["PIP_NO_INDEX"] = "1"
os.environ["PYTHONNOUSERSITE"] = "1"


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


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


def run_command(
    argv: list[str],
    *,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    started_at = datetime.now(UTC).isoformat()
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
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
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
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
    except OSError as exc:
        return {
            "argv": argv,
            "returncode": None,
            "stdout": "",
            "stderr": bounded(f"{type(exc).__name__}: {exc}"),
            "timed_out": False,
            "started_at": started_at,
            "completed_at": datetime.now(UTC).isoformat(),
        }


def write_json(name: str, payload: object) -> None:
    path = OUTPUT_DIRECTORY / name
    path.write_text(canonical_json(payload), encoding="utf-8")


def parse_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        result[key] = value.strip().strip('"')
    return result


def command_identity(name: str, version_args: list[str]) -> dict[str, object]:
    resolved = shutil.which(name)
    observation: dict[str, object] = {"name": name, "path": resolved}
    if resolved is not None:
        observation["version"] = run_command([resolved, *version_args])
    return observation


def module_identity(name: str) -> dict[str, object]:
    spec = importlib.util.find_spec(name)
    distribution_version: str | None = None
    try:
        distribution_version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        distribution_version = None
    return {
        "module": name,
        "origin": None if spec is None else spec.origin,
        "distribution_version": distribution_version,
    }


def discover_libcuda_candidates() -> list[dict[str, object]]:
    roots = (
        Path("/usr/local/nvidia/lib64"),
        Path("/usr/local/cuda/lib64"),
        Path("/usr/local/cuda/lib64/stubs"),
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/usr/lib64"),
        Path("/lib/x86_64-linux-gnu"),
    )
    seen: set[str] = set()
    observations: list[dict[str, object]] = []
    for root in roots:
        if not root.exists():
            continue
        for raw in sorted(glob.glob(str(root / "libcuda.so*"))):
            path = Path(raw)
            normalized = str(path)
            if normalized in seen:
                continue
            seen.add(normalized)
            observations.append(
                {
                    "path": normalized,
                    "exists": path.exists(),
                    "is_symlink": path.is_symlink(),
                    "resolved_path": str(path.resolve()) if path.exists() else None,
                    "size_bytes": path.stat().st_size if path.exists() else None,
                    "classification": (
                        "CUDA_TOOLKIT_STUB" if "/stubs/" in normalized else "REAL_OR_DRIVER_MOUNT"
                    ),
                }
            )
    return observations[:128]


def p0_platform_identity() -> tuple[dict[str, object], bool]:
    credential_names_present = sorted(
        name for name in CREDENTIAL_ENVIRONMENT_NAMES if os.environ.get(name)
    )
    allowlisted_environment = {name: os.environ.get(name) for name in ALLOWLISTED_ENVIRONMENT}
    nvidia_smi = run_command(
        [
            shutil.which("nvidia-smi") or "nvidia-smi",
            "--query-gpu=index,name,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    base_torch: dict[str, object]
    try:
        import torch

        devices = []
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            devices.append(
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "compute_capability": list(torch.cuda.get_device_capability(index)),
                    "total_memory_bytes": properties.total_memory,
                }
            )
        base_torch = {
            "imported": True,
            "version": torch.__version__,
            "cuda_build": torch.version.cuda,
            "module_origin": torch.__file__,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count(),
            "devices": devices,
        }
    except Exception as exc:
        base_torch = {
            "imported": False,
            "error_type": type(exc).__name__,
            "safe_error": bounded(str(exc)),
        }

    compilers = (
        command_identity("cc", ["--version"]),
        command_identity("gcc", ["--version"]),
        command_identity("ld", ["--version"]),
        command_identity("nvcc", ["--version"]),
        command_identity("ptxas", ["--version"]),
        command_identity("ldconfig", ["-p"]),
    )
    ldconfig = run_command([shutil.which("ldconfig") or "ldconfig", "-p"])
    libcuda_candidates = discover_libcuda_candidates()
    devices = base_torch.get("devices")
    t4_topology = (
        isinstance(devices, list)
        and len(devices) == 2
        and all(
            isinstance(item, dict)
            and "T4" in str(item.get("name", "")).upper()
            and item.get("compute_capability") == [7, 5]
            for item in devices
        )
    )
    build_identity_complete = bool(
        allowlisted_environment.get("BUILD_DATE") and allowlisted_environment.get("GIT_COMMIT")
    )
    compiler_available = shutil.which("cc") is not None and shutil.which("ld") is not None
    driver_observed = bool(libcuda_candidates) or "libcuda.so.1" in str(ldconfig.get("stdout", ""))
    passed = (
        not credential_names_present
        and build_identity_complete
        and t4_topology
        and compiler_available
        and driver_observed
        and nvidia_smi.get("returncode") == 0
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "probe_id": "P0",
        "probe_name": "KAGGLE_IMAGE_AND_RUNTIME_IDENTITY",
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASSED" if passed else "FAILED",
        "decision": "PLATFORM_IDENTITY_CAPTURED" if passed else "DIAGNOSTIC_INVALID",
        "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "os_release": parse_os_release(),
        },
        "allowlisted_environment": allowlisted_environment,
        "credential_environment_names_present": credential_names_present,
        "nvidia_smi": nvidia_smi,
        "base_torch": base_torch,
        "base_modules": [
            module_identity("torch"),
            module_identity("triton"),
        ],
        "compilers_and_tools": list(compilers),
        "ctypes_find_library_cuda": ctypes.util.find_library("cuda"),
        "ldconfig": ldconfig,
        "libcuda_candidates": libcuda_candidates,
        "checks": {
            "credentials_absent": not credential_names_present,
            "kaggle_build_identity_complete": build_identity_complete,
            "dual_t4_topology": t4_topology,
            "compiler_and_linker_available": compiler_available,
            "driver_library_observed": driver_observed,
            "nvidia_smi_succeeded": nvidia_smi.get("returncode") == 0,
        },
        "budgets": {
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "external_spend": 0,
        },
    }
    return report, passed


def p1_cuda_driver_linker() -> tuple[dict[str, object], bool]:
    workspace = OUTPUT_DIRECTORY / "p1_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    source = workspace / "cuda_driver_link_probe.c"
    object_file = workspace / "cuda_driver_link_probe.o"
    executable = workspace / "cuda_driver_link_probe"

    source.write_bytes(P1_C_SOURCE)
    observed_source = source.read_bytes()
    source_sha256 = hashlib.sha256(observed_source).hexdigest()
    source_exact = observed_source == P1_C_SOURCE
    source_newline_count = observed_source.count(b"\n")
    literal_backslash_n_present = b"\\n" in observed_source

    compiler = shutil.which("cc")
    syntax_compile_result: dict[str, object] | None = None
    link_result: dict[str, object] | None = None
    ldd_result: dict[str, object] | None = None
    execution_result: dict[str, object] | None = None
    selected_link_libraries: list[str] = []
    runtime_library_path: str | None = None
    decision = P1_FAILURE_DECISIONS["source_invalid"]
    failure_stage = "source_materialization"

    if (
        source_exact
        and source_sha256 == P1_C_SOURCE_SHA256
        and source_newline_count == 2
        and not literal_backslash_n_present
        and compiler is not None
    ):
        failure_stage = "syntax_compilation"
        syntax_compile_result = run_command(
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
        if (
            syntax_compile_result.get("returncode") == 0
            and object_file.is_file()
        ):
            failure_stage = "cuda_driver_link"
            link_result = run_command(
                [
                    compiler,
                    str(object_file),
                    "-Wl,-t",
                    "-lcuda",
                    "-o",
                    str(executable),
                ]
            )
            trace_text = (
                str(link_result.get("stdout", ""))
                + "\n"
                + str(link_result.get("stderr", ""))
            )
            selected_link_libraries = sorted(
                {
                    token
                    for token in trace_text.replace("(", " ")
                    .replace(")", " ")
                    .split()
                    if "libcuda.so" in token
                }
            )
            if link_result.get("returncode") == 0 and executable.is_file():
                failure_stage = "dynamic_loader_resolution"
                ldd_result = run_command(
                    [shutil.which("ldd") or "ldd", str(executable)]
                )
                for line in str(ldd_result.get("stdout", "")).splitlines():
                    if "libcuda.so.1" in line and "=>" in line:
                        runtime_library_path = (
                            line.split("=>", maxsplit=1)[1]
                            .strip()
                            .split()[0]
                        )
                        break
                if (
                    ldd_result.get("returncode") == 0
                    and runtime_library_path is not None
                    and runtime_library_path != "not"
                ):
                    failure_stage = "driver_initialization"
                    execution_result = run_command([str(executable)])
                    if execution_result.get("returncode") == 0:
                        decision = "CUDA_DRIVER_LINKER_CONTRACT_PASSED"
                        failure_stage = "none"
                    else:
                        decision = P1_FAILURE_DECISIONS[
                            "driver_initialization_failed"
                        ]
                else:
                    decision = P1_FAILURE_DECISIONS[
                        "loader_resolution_failed"
                    ]
            else:
                decision = P1_FAILURE_DECISIONS["link_failed"]
        else:
            decision = P1_FAILURE_DECISIONS["syntax_compile_failed"]

    passed = decision == "CUDA_DRIVER_LINKER_CONTRACT_PASSED"
    link_library_classification = "UNRESOLVED"
    if selected_link_libraries:
        link_library_classification = (
            "CUDA_TOOLKIT_STUB"
            if any("/stubs/" in item for item in selected_link_libraries)
            else "REAL_OR_DRIVER_MOUNT"
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "probe_id": "P1",
        "probe_name": "CUDA_DRIVER_LINKER_VISIBILITY",
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASSED" if passed else "FAILED",
        "decision": decision,
        "failure_stage": failure_stage,
        "compiler_path": compiler,
        "source_contract": {
            "path": str(source),
            "expected_sha256": P1_C_SOURCE_SHA256,
            "observed_sha256": source_sha256,
            "size_bytes": len(observed_source),
            "newline_count": source_newline_count,
            "literal_backslash_n_present": literal_backslash_n_present,
            "exact_bytes": source_exact,
        },
        "syntax_compile_result": syntax_compile_result,
        "link_result": link_result,
        "selected_link_libraries": selected_link_libraries,
        "link_library_classification": link_library_classification,
        "ldd_result": ldd_result,
        "runtime_library_path": runtime_library_path,
        "runtime_library_classification": (
            None
            if runtime_library_path is None
            else (
                "CUDA_TOOLKIT_STUB"
                if "/stubs/" in runtime_library_path
                else "REAL_OR_DRIVER_MOUNT"
            )
        ),
        "execution_result": execution_result,
        "filesystem_mutations_performed": [
            str(source),
            str(object_file) if object_file.exists() else None,
            str(executable) if executable.exists() else None,
        ],
        "environment_overrides_applied": [],
        "checks": {
            "source_bytes_exact": source_exact,
            "source_sha256_exact": source_sha256 == P1_C_SOURCE_SHA256,
            "source_has_two_lf_bytes": source_newline_count == 2,
            "literal_backslash_n_absent": not literal_backslash_n_present,
            "compiler_available": compiler is not None,
            "syntax_compile_succeeded": (
                syntax_compile_result is not None
                and syntax_compile_result.get("returncode") == 0
            ),
            "cuda_driver_link_succeeded": (
                link_result is not None
                and link_result.get("returncode") == 0
            ),
            "link_library_identified": bool(selected_link_libraries),
            "runtime_library_identified": runtime_library_path is not None,
            "cuInit_succeeded": (
                execution_result is not None
                and execution_result.get("returncode") == 0
            ),
            "unapproved_filesystem_mutation_absent": True,
        },
        "budgets": {
            "source_materialization_attempts": 1,
            "syntax_compile_attempts": (
                1 if syntax_compile_result is not None else 0
            ),
            "link_attempts": 1 if link_result is not None else 0,
            "loader_resolution_attempts": 1 if ldd_result is not None else 0,
            "execution_attempts": 1 if execution_result is not None else 0,
            "hidden_retries": 0,
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
        },
    }
    report["filesystem_mutations_performed"] = [
        item
        for item in report["filesystem_mutations_performed"]
        if item is not None
    ]
    return report, passed


def discover_wheelhouse() -> Path:
    candidates = sorted(
        path.resolve()
        for path in Path("/kaggle/input").rglob(RUNTIME_OUTPUT_DIRECTORY)
        if path.is_dir() and not path.is_symlink()
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one {RUNTIME_OUTPUT_DIRECTORY}, observed {len(candidates)}"
        )
    return candidates[0]


def validate_wheelhouse(wheelhouse: Path) -> dict[str, object]:
    observed_control_hashes: dict[str, str] = {}
    for name, expected in EXPECTED_CONTROL_HASHES.items():
        path = wheelhouse / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"wheelhouse control file is missing or unsafe: {name}")
        observed = sha256_file(path)
        observed_control_hashes[name] = observed
        if observed != expected:
            raise RuntimeError(f"wheelhouse control identity drifted: {name}")

    manifest = json.loads((wheelhouse / "sha256_manifest.json").read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("wheelhouse checksum manifest does not contain entries")
    wheel_entries = [
        item
        for item in entries
        if isinstance(item, dict) and str(item.get("path", "")).startswith("wheels/")
    ]
    if len(wheel_entries) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError(f"wheelhouse package count drifted: {len(wheel_entries)}")
    verified_entries = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("wheelhouse checksum entry is invalid")
        relative = entry.get("path")
        expected_sha = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if (
            not isinstance(relative, str)
            or not isinstance(expected_sha, str)
            or not isinstance(expected_size, int)
        ):
            raise RuntimeError("wheelhouse checksum entry fields are invalid")
        path = wheelhouse / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"wheelhouse payload is missing or unsafe: {relative}")
        if path.stat().st_size != expected_size or sha256_file(path) != expected_sha:
            raise RuntimeError(f"wheelhouse payload identity drifted: {relative}")
        verified_entries += 1
    return {
        "wheelhouse_path": str(wheelhouse),
        "control_hashes": observed_control_hashes,
        "manifest_entry_count": len(entries),
        "wheel_entry_count": len(wheel_entries),
        "verified_entry_count": verified_entries,
    }


CONTROLLED_TRITON_SCRIPT = r"""
from __future__ import annotations

import importlib.metadata
import json
import shutil
from pathlib import Path

import torch
import triton
import triton.language as tl


@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    number_of_elements,
    BLOCK_SIZE: tl.constexpr,
):
    offsets = tl.program_id(axis=0) * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < number_of_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(output_ptr + offsets, x + y, mask=mask)


number_of_elements = 1024
x = torch.arange(number_of_elements, device="cuda", dtype=torch.float32)
y = torch.full((number_of_elements,), 2.0, device="cuda", dtype=torch.float32)
output = torch.empty_like(x)
grid = (triton.cdiv(number_of_elements, 256),)
add_kernel[grid](
    x,
    y,
    output,
    number_of_elements,
    BLOCK_SIZE=256,
)
torch.cuda.synchronize()
expected = x + y
passed = bool(torch.equal(output, expected))
payload = {
    "torch_version": torch.__version__,
    "torch_cuda_build": torch.version.cuda,
    "torch_module_origin": torch.__file__,
    "triton_distribution_version": importlib.metadata.version("triton"),
    "triton_module_version": getattr(triton, "__version__", None),
    "triton_module_origin": triton.__file__,
    "cuda_available": torch.cuda.is_available(),
    "device_count": torch.cuda.device_count(),
    "device_name": torch.cuda.get_device_name(0),
    "compute_capability": list(torch.cuda.get_device_capability(0)),
    "compiler_path": shutil.which("cc"),
    "ptxas_path": shutil.which("ptxas"),
    "number_of_elements": number_of_elements,
    "result_exact": passed,
    "model_loaded": False,
    "worker_started": False,
    "model_requests": 0,
}
print(json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
if not passed:
    raise SystemExit(3)
""".strip()


CONTROLLED_SCRIPT_BOOTSTRAP = r"""
import site
import sys
import types
from pathlib import Path

target_site = Path(sys.argv.pop(1)).resolve()
payload_path = Path(sys.argv.pop(1)).resolve()


def sentinel(name):
    module = types.ModuleType(name)
    module.__file__ = f"<auragateway-suppressed-{name}>"
    return module


sys.modules["sitecustomize"] = sentinel("sitecustomize")
sys.modules["usercustomize"] = sentinel("usercustomize")
site.main()

cleaned = []
for value in sys.path:
    if not value:
        cleaned.append(value)
        continue
    path = Path(value).resolve()
    is_target = path == target_site or target_site in path.parents
    is_package_path = any(
        part in {"site-packages", "dist-packages"}
        for part in path.parts
    )
    if is_package_path and not is_target:
        continue
    cleaned.append(value)

if str(target_site) not in cleaned:
    cleaned.insert(0, str(target_site))
sys.path[:] = cleaned
sys.argv = [str(payload_path)]
payload = payload_path.read_text(encoding="utf-8")
exec(compile(payload, str(payload_path), "exec"))
""".strip()


def target_library_directories(site_packages: Path) -> list[Path]:
    candidates = sorted(
        {
            path.resolve()
            for path in (site_packages / "nvidia").glob("*/lib")
            if path.is_dir() and not path.is_symlink()
        }
    )
    return candidates


def p2_minimal_triton() -> tuple[dict[str, object], bool]:
    captured_at = datetime.now(UTC).isoformat()
    wheelhouse_validation: dict[str, object] | None = None
    install_result: dict[str, object] | None = None
    probe_result: dict[str, object] | None = None
    parsed_probe: dict[str, object] | None = None
    failure_type: str | None = None
    safe_error: str | None = None
    runtime_root = OUTPUT_DIRECTORY / "target_runtime"
    site_packages = runtime_root / "site-packages"
    probe_script = OUTPUT_DIRECTORY / "minimal_triton_probe.py"
    try:
        wheelhouse = discover_wheelhouse()
        wheelhouse_validation = validate_wheelhouse(wheelhouse)
        if runtime_root.exists():
            raise RuntimeError("target runtime directory already exists")
        site_packages.mkdir(parents=True)
        install_argv = [
            sys.executable,
            "-m",
            "pip",
            "--isolated",
            "--disable-pip-version-check",
            "install",
            "--no-index",
            "--require-hashes",
            "--only-binary=:all:",
            "--target",
            str(site_packages),
            "--find-links",
            str(wheelhouse / "wheels"),
            "-r",
            str(wheelhouse / "requirements.lock.txt"),
        ]
        install_environment = dict(os.environ)
        install_environment.pop("PYTHONHOME", None)
        install_environment.pop("PYTHONPATH", None)
        install_environment["PIP_NO_INDEX"] = "1"
        install_environment["PYTHONNOUSERSITE"] = "1"
        install_result = run_command(
            install_argv,
            timeout=RUNTIME_INSTALL_TIMEOUT_SECONDS,
            env=install_environment,
        )
        if install_result.get("returncode") != 0:
            raise RuntimeError("pinned runtime installation failed")

        probe_script.write_text(CONTROLLED_TRITON_SCRIPT + "\n", encoding="utf-8")
        runtime_environment = dict(os.environ)
        runtime_environment.pop("PYTHONHOME", None)
        runtime_environment.pop("PYTHONPATH", None)
        runtime_environment["PYTHONNOUSERSITE"] = "1"
        runtime_environment["CUDA_VISIBLE_DEVICES"] = "0"
        runtime_environment["HF_HUB_OFFLINE"] = "1"
        runtime_environment["TRANSFORMERS_OFFLINE"] = "1"
        libraries = target_library_directories(site_packages)
        inherited_ld = runtime_environment.get("LD_LIBRARY_PATH")
        library_values = [str(path) for path in libraries]
        if inherited_ld:
            library_values.append(inherited_ld)
        runtime_environment["LD_LIBRARY_PATH"] = os.pathsep.join(library_values)
        probe_result = run_command(
            [
                sys.executable,
                "-S",
                "-c",
                CONTROLLED_SCRIPT_BOOTSTRAP,
                str(site_packages),
                str(probe_script),
            ],
            timeout=COMMAND_TIMEOUT_SECONDS,
            env=runtime_environment,
        )
        if probe_result.get("returncode") != 0:
            raise RuntimeError("minimal Triton kernel process failed")
        stdout = str(probe_result.get("stdout", "")).strip()
        parsed = json.loads(stdout)
        if not isinstance(parsed, dict):
            raise RuntimeError("minimal Triton output was not one object")
        parsed_probe = parsed
        if (
            parsed.get("result_exact") is not True
            or parsed.get("compute_capability") != [7, 5]
            or "T4" not in str(parsed.get("device_name", "")).upper()
        ):
            raise RuntimeError("minimal Triton result or device identity failed")
        passed = True
    except Exception as exc:
        passed = False
        failure_type = type(exc).__name__
        safe_error = bounded(str(exc))

    report = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "probe_id": "P2",
        "probe_name": "MINIMAL_TRITON_KERNEL",
        "captured_at": captured_at,
        "status": "PASSED" if passed else "FAILED",
        "decision": (
            "CURRENT_STACK_TRITON_PRIMITIVE_PASSED"
            if passed
            else "CURRENT_STACK_TRITON_INCOMPATIBLE"
        ),
        "wheelhouse_validation": wheelhouse_validation,
        "runtime_installation": install_result,
        "target_runtime_root": str(runtime_root),
        "target_site_packages": str(site_packages),
        "target_library_directories": [
            str(path) for path in target_library_directories(site_packages)
        ]
        if site_packages.exists()
        else [],
        "probe_process": probe_result,
        "probe_observation": parsed_probe,
        "failure_type": failure_type,
        "safe_error": safe_error,
        "checks": {
            "wheelhouse_identity_validated": wheelhouse_validation is not None,
            "runtime_installation_succeeded": (
                install_result is not None and install_result.get("returncode") == 0
            ),
            "minimal_kernel_process_succeeded": (
                probe_result is not None and probe_result.get("returncode") == 0
            ),
            "minimal_kernel_result_exact": (
                parsed_probe is not None and parsed_probe.get("result_exact") is True
            ),
        },
        "budgets": {
            "runtime_install_attempts": 1 if install_result is not None else 0,
            "kernel_compile_and_execution_attempts": 1 if probe_result is not None else 0,
            "hidden_retries": 0,
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
        },
    }
    return report, passed


def not_run_report(probe_id: str, probe_name: str, prior_decision: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "probe_id": probe_id,
        "probe_name": probe_name,
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "NOT_RUN_DUE_TO_PRIOR_FAILURE",
        "decision": prior_decision,
        "prior_terminal_decision": prior_decision,
        "budgets": {
            "attempts": 0,
            "hidden_retries": 0,
            "model_loads": 0,
            "worker_starts": 0,
            "model_requests": 0,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
        },
    }


def write_human_report(summary: dict[str, object]) -> None:
    lines = [
        "# AuraGateway CUDA 12.9 P0-P2 Platform Diagnostic",
        "",
        f"- Diagnostic ID: `{DIAGNOSTIC_ID}`",
        f"- Source main merge: `{SOURCE_MAIN_MERGE_COMMIT}`",
        f"- Overall status: `{summary['status']}`",
        f"- Terminal decision: `{summary['terminal_decision']}`",
        "",
        "## Probe results",
        "",
    ]
    for probe in summary["probes"]:
        lines.append(f"- {probe['probe_id']} — {probe['status']} — `{probe['decision']}`")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Model loads: 0",
            "- Worker starts: 0",
            "- Model requests: 0",
            "- Benchmark trajectory requests: 0",
            "- Network requests: 0",
            "- Customer data: absent",
            "- External spend: 0",
            "",
            "## Non-claims",
            "",
            "This diagnostic does not prove model serving, explicit TRITON_ATTN worker "
            "startup, inference, prefix-cache telemetry, reset behavior, dual-worker "
            "readiness, measured A/B/C effects, deployment, or production readiness.",
            "",
        ]
    )
    (OUTPUT_DIRECTORY / "human_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_bundle_manifest() -> None:
    members = []
    for name in REQUIRED_OUTPUTS:
        if name == "bundle_manifest.json":
            continue
        path = OUTPUT_DIRECTORY / name
        members.append(
            {
                "path": name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": "auragateway-cu129-p0-p2-platform-evidence-v1",
        "diagnostic_id": DIAGNOSTIC_ID,
        "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
        "members": members,
    }
    write_json("bundle_manifest.json", manifest)


def build_evidence_zip() -> None:
    if EVIDENCE_ZIP.exists():
        raise RuntimeError(f"evidence ZIP already exists: {EVIDENCE_ZIP}")
    with zipfile.ZipFile(EVIDENCE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED_OUTPUTS:
            path = OUTPUT_DIRECTORY / name
            archive.write(path, arcname=name)


def main() -> None:
    if OUTPUT_DIRECTORY.exists():
        raise RuntimeError(f"diagnostic output directory already exists: {OUTPUT_DIRECTORY}")
    OUTPUT_DIRECTORY.mkdir(parents=True)

    p0_report, p0_passed = p0_platform_identity()
    write_json("platform_identity_report.json", p0_report)

    if not p0_passed:
        p1_report = not_run_report(
            "P1",
            "CUDA_DRIVER_LINKER_VISIBILITY",
            "DIAGNOSTIC_INVALID",
        )
        p2_report = not_run_report(
            "P2",
            "MINIMAL_TRITON_KERNEL",
            "DIAGNOSTIC_INVALID",
        )
        terminal_decision = "DIAGNOSTIC_INVALID"
    else:
        p1_report, p1_passed = p1_cuda_driver_linker()
        if not p1_passed:
            p1_decision = p1_report.get("decision")
            if p1_decision not in {
                "DIAGNOSTIC_INVALID",
                "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
                "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED",
            }:
                p1_decision = "DIAGNOSTIC_INVALID"
            p2_report = not_run_report(
                "P2",
                "MINIMAL_TRITON_KERNEL",
                str(p1_decision),
            )
            terminal_decision = str(p1_decision)
        else:
            p2_report, p2_passed = p2_minimal_triton()
            terminal_decision = (
                "P0_P2_PLATFORM_DIAGNOSTIC_PASSED"
                if p2_passed
                else "CURRENT_STACK_TRITON_INCOMPATIBLE"
            )

    write_json("cuda_driver_linker_report.json", p1_report)
    write_json("minimal_triton_kernel_report.json", p2_report)

    probes = [
        {
            "probe_id": p0_report["probe_id"],
            "status": p0_report["status"],
            "decision": p0_report["decision"],
        },
        {
            "probe_id": p1_report["probe_id"],
            "status": p1_report["status"],
            "decision": p1_report["decision"],
        },
        {
            "probe_id": p2_report["probe_id"],
            "status": p2_report["status"],
            "decision": p2_report["decision"],
        },
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
        "captured_at": datetime.now(UTC).isoformat(),
        "status": (
            "PASSED" if terminal_decision == "P0_P2_PLATFORM_DIAGNOSTIC_PASSED" else "FAILED_CLOSED"
        ),
        "terminal_decision": terminal_decision,
        "probes": probes,
        "stop_on_first_failure": True,
        "hidden_retries_performed": 0,
        "filesystem_mutations_outside_working_directory": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "customer_data_present": False,
        "credentials_used": False,
        "external_spend": 0,
        "full_triton_qualification_attempt_consumed": False,
        "next_gate": (
            "implement_explicit_triton_attention_backend"
            if terminal_decision == "P0_P2_PLATFORM_DIAGNOSTIC_PASSED"
            else "preserve_evidence_and_classify_platform_failure"
        ),
    }
    write_json("option_c_platform_diagnostic_summary.json", summary)
    write_human_report(summary)
    write_bundle_manifest()
    build_evidence_zip()

    print(
        canonical_json(
            {
                "status": summary["status"],
                "terminal_decision": terminal_decision,
                "evidence_zip": str(EVIDENCE_ZIP),
                "evidence_zip_sha256": sha256_file(EVIDENCE_ZIP),
                "model_loads": 0,
                "worker_starts": 0,
                "model_requests": 0,
                "benchmark_trajectory_requests": 0,
                "network_requests": 0,
            }
        )
    )


main()
'''.strip()


class P0P2PlatformDiagnosticError(RuntimeError):
    """Fail-closed static diagnostic implementation error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P0P2PlatformDiagnosticError(message)


class _StrictModel(LocalABCContract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProbeRequest(_StrictModel):
    probe_id: Literal["P0", "P1", "P2"]
    name: Literal[
        "KAGGLE_IMAGE_AND_RUNTIME_IDENTITY",
        "CUDA_DRIVER_LINKER_VISIBILITY",
        "MINIMAL_TRITON_KERNEL",
    ]
    pass_decision: Literal[
        "PLATFORM_IDENTITY_CAPTURED",
        "CUDA_DRIVER_LINKER_CONTRACT_PASSED",
        "CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
    ]
    fail_decision: Literal[
        "DIAGNOSTIC_INVALID",
        "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
        "CURRENT_STACK_TRITON_INCOMPATIBLE",
    ]
    permitted_fail_decisions: tuple[
        Literal[
            "DIAGNOSTIC_INVALID",
            "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
            "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED",
            "CURRENT_STACK_TRITON_INCOMPATIBLE",
        ],
        ...,
    ]


class PlatformDiagnosticRequest(_StrictModel):
    schema_version: Literal["1.0.0"]
    request_id: Literal["auragateway-cu129-p0-p2-platform-diagnostic-request-v1"]
    source_main_merge_commit: Literal["f4f08eda4b4d4747514b4646fe53664d8a78ca6d"]
    option_c_decision_record_path: Literal[
        "benchmarks/local_abc/auragateway_cu129_option_c_runtime_diagnostic_decision_v1.json"
    ]
    mode: Literal["KAGGLE_DIAGNOSTIC"]
    notebook_name: Literal["ag-cu129-p0-p2-platform-diagnostic-v1"]
    failed_notebook_name: Literal["ag-cu129-p0-p2-platform-diag-failed-v1"]
    runtime_output_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    evidence_zip_name: Literal["ag-cu129-p0-p2-platform-evidence-v1.zip"]
    maximum_sessions: Literal[1]
    stop_on_first_failure: Literal[True]
    network_access_permitted: Literal[False]
    credentials_permitted: Literal[False]
    customer_data_permitted: Literal[False]
    model_load_permitted: Literal[False]
    worker_start_permitted: Literal[False]
    model_requests_permitted: Literal[0]
    benchmark_trajectory_requests_permitted: Literal[0]
    hidden_retries_permitted: Literal[False]
    filesystem_mutation_scope: Literal["KAGGLE_WORKING_DIRECTORY_ONLY"]
    system_library_copy_permitted: Literal[False]
    libcuda_symlink_permitted: Literal[False]
    external_spend: Literal[0]
    probes: tuple[ProbeRequest, ProbeRequest, ProbeRequest]
    required_outputs: tuple[str, ...] = Field(min_length=6, max_length=6)
    next_gate_on_pass: Literal["implement_explicit_triton_attention_backend"]
    next_gate_on_failure: Literal["preserve_evidence_and_classify_platform_failure"]

    @model_validator(mode="after")
    def validate_fixed_contract(self) -> Self:
        if tuple(item.probe_id for item in self.probes) != ("P0", "P1", "P2"):
            raise ValueError("P0-P2 probe order drifted")
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("P0-P2 required output contract drifted")
        expected_failure_sets = (
            ("DIAGNOSTIC_INVALID",),
            P1_FAILURE_DECISIONS,
            ("CURRENT_STACK_TRITON_INCOMPATIBLE",),
        )
        observed_failure_sets = tuple(item.permitted_fail_decisions for item in self.probes)
        if observed_failure_sets != expected_failure_sets:
            raise ValueError("P0-P2 failure taxonomy drifted")
        for value in (self.notebook_name, self.failed_notebook_name):
            if len(value) > MAXIMUM_KAGGLE_NAME_CHARACTERS:
                raise ValueError("Kaggle notebook name exceeds 50 characters")
        return self


class ImplementationSafety(_StrictModel):
    authorization_issued: Literal[False]
    kaggle_execution_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    runtime_worker_source_changed: Literal[False]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]


class DiagnosticRemediationRecord(_StrictModel):
    remediation_id: Literal["auragateway-cu129-p1-probe-taxonomy-remediation-v1"]
    invalid_kaggle_version: Literal["338921762"]
    invalid_platform_evidence_sha256: str
    confirmed_defect: Literal["literal_backslash_n_in_generated_c_probe"]
    corrected_source_sha256: str
    exact_source_bytes_validated: Literal[True]
    staged_failure_taxonomy_validated: Literal[True]
    unchanged_replay_authorized: Literal[False]
    corrected_replay_authorized_after_merge: Literal[True]

    @model_validator(mode="after")
    def validate_remediation(self) -> Self:
        if self.invalid_platform_evidence_sha256 != (INVALID_PLATFORM_EVIDENCE_SHA256):
            raise ValueError("invalid evidence identity drifted")
        if self.corrected_source_sha256 != P1_C_SOURCE_SHA256:
            raise ValueError("corrected P1 source identity drifted")
        return self


class PlatformDiagnosticImplementationRecord(_StrictModel):
    schema_version: Literal["1.1.0"]
    record_id: Literal["auragateway-cu129-p0-p2-platform-diagnostic-implementation-v1"]
    source_main_merge_commit: Literal["f4f08eda4b4d4747514b4646fe53664d8a78ca6d"]
    request_path: Literal[
        "data/evals/benchmark/environment-qualification-v1/"
        "option_c_p0_p2_platform_diagnostic_request.json"
    ]
    notebook_path: Literal["notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb"]
    notebook_name: Literal["ag-cu129-p0-p2-platform-diagnostic-v1"]
    notebook_sha256: str
    notebook_cell_count: Literal[2]
    output_cells_present: Literal[False]
    execution_counts_present: Literal[False]
    runtime_output_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    evidence_zip_name: Literal["ag-cu129-p0-p2-platform-evidence-v1.zip"]
    required_outputs: tuple[str, ...] = Field(min_length=6, max_length=6)
    safety: ImplementationSafety
    remediation: DiagnosticRemediationRecord
    implementation_status: Literal["REMEDIATED_NOT_EXECUTED"]
    next_gate: Literal["review_and_materialize_corrected_p0_p2_platform_diagnostic"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if len(self.notebook_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.notebook_sha256
        ):
            raise ValueError("notebook SHA-256 is invalid")
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("implementation output contract drifted")
        return self


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def p1_probe_source_bytes() -> bytes:
    """Extract the exact generated P1 C source bytes from the notebook program."""

    tree = ast.parse(KAGGLE_PROGRAM)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "P1_C_SOURCE" for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, bytes):
            raise P0P2PlatformDiagnosticError("generated P1 C source constant is not bytes")
        return value
    raise P0P2PlatformDiagnosticError("generated P1 C source constant is missing")


def _notebook_document() -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# AuraGateway CUDA 12.9 P0-P2 Platform Diagnostic\n",
                    "\n",
                    "Model-free Option C platform diagnostic. Do not add model, "
                    "worker, network, credential, or benchmark operations.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": KAGGLE_PROGRAM.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "accelerator": "GPU",
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
                "dockerImageVersionId": None,
                "isGpuEnabled": True,
                "isInternetEnabled": False,
                "language": "python",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def notebook_bytes() -> bytes:
    payload = json.dumps(
        _notebook_document(),
        ensure_ascii=False,
        indent=1,
        sort_keys=True,
    )
    return (payload + "\n").encode("utf-8")


def notebook_sha256() -> str:
    return _sha256_bytes(notebook_bytes())


def write_notebook(path: Path = NOTEBOOK_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(notebook_bytes())


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P0P2PlatformDiagnosticError(
            f"required JSON asset is unreadable: {path.as_posix()}"
        ) from exc
    if not isinstance(payload, dict):
        raise P0P2PlatformDiagnosticError(
            f"required JSON asset must contain one object: {path.as_posix()}"
        )
    return cast(dict[str, object], payload)


def load_request(path: Path) -> PlatformDiagnosticRequest:
    try:
        return PlatformDiagnosticRequest.model_validate(_load_json_object(path))
    except ValidationError as exc:
        raise P0P2PlatformDiagnosticError("P0-P2 platform diagnostic request is invalid") from exc


def load_implementation_record(path: Path) -> PlatformDiagnosticImplementationRecord:
    try:
        return PlatformDiagnosticImplementationRecord.model_validate(_load_json_object(path))
    except ValidationError as exc:
        raise P0P2PlatformDiagnosticError(
            "P0-P2 platform diagnostic implementation record is invalid"
        ) from exc


def validate_notebook(path: Path) -> dict[str, object]:
    try:
        observed_bytes = path.read_bytes()
        observed = json.loads(observed_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P0P2PlatformDiagnosticError("P0-P2 notebook is unreadable") from exc
    expected_bytes = notebook_bytes()
    if observed_bytes != expected_bytes:
        raise P0P2PlatformDiagnosticError("P0-P2 notebook identity drifted")
    if not isinstance(observed, dict):
        raise P0P2PlatformDiagnosticError("P0-P2 notebook root is invalid")
    cells = observed.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise P0P2PlatformDiagnosticError("P0-P2 notebook cell count drifted")
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        raise P0P2PlatformDiagnosticError("P0-P2 code cell is invalid")
    if code_cell.get("outputs") != [] or code_cell.get("execution_count") is not None:
        raise P0P2PlatformDiagnosticError("P0-P2 notebook contains execution state")
    required_markers = (
        "BUILD_DATE",
        "GIT_COMMIT",
        "nvidia-smi",
        "-lcuda",
        "triton.jit",
        "--no-index",
        "--require-hashes",
        "stop_on_first_failure",
    )
    if any(marker not in KAGGLE_PROGRAM for marker in required_markers):
        raise P0P2PlatformDiagnosticError("P0-P2 program lost required behavior")
    observed_p1_source = p1_probe_source_bytes()
    if observed_p1_source != P1_C_SOURCE_EXPECTED:
        raise P0P2PlatformDiagnosticError("generated P1 C source bytes drifted")
    if b"\\n" in observed_p1_source or observed_p1_source.count(b"\n") != 2:
        raise P0P2PlatformDiagnosticError("generated P1 C source newline contract drifted")
    required_p1_taxonomy = (
        "syntax_compile_failed",
        "link_failed",
        "loader_resolution_failed",
        "driver_initialization_failed",
        "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED",
    )
    if any(marker not in KAGGLE_PROGRAM for marker in required_p1_taxonomy):
        raise P0P2PlatformDiagnosticError("generated P1 failure taxonomy drifted")
    prohibited_markers = (
        "Qwen/Qwen",
        "vllm.entrypoints.openai.api_server",
        "/v1/chat/completions",
        "--attention-backend",
        "requests.get(",
        "urllib.request",
    )
    if any(marker in KAGGLE_PROGRAM for marker in prohibited_markers):
        raise P0P2PlatformDiagnosticError("P0-P2 program contains a forbidden boundary")
    return {
        "notebook_path": path.as_posix(),
        "notebook_name": NOTEBOOK_NAME,
        "notebook_sha256": _sha256_bytes(observed_bytes),
        "cell_count": len(cells),
        "output_cells_present": False,
        "execution_counts_present": False,
    }


def _require_source_ancestor(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        return
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            SOURCE_MAIN_MERGE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise P0P2PlatformDiagnosticError("the Option C merge is not an ancestor of HEAD")


def _require_authorization_absent(repo_root: Path) -> None:
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise P0P2PlatformDiagnosticError("a live transient authorization is prohibited")


def _require_option_c_decision(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / DECISION_RECORD_PATH)
    checks = (
        payload.get("decision") == "APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC",
        payload.get("next_gate") == "implement_p0_p2_platform_diagnostic_assets",
        isinstance(payload.get("platform_diagnostic"), dict),
        isinstance(payload.get("selected_strategy"), dict),
    )
    if not all(checks):
        raise P0P2PlatformDiagnosticError("merged Option C decision contract drifted")


def _require_runtime_remains_deferred(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / WORKER_PLAN_PATH)
    workers = payload.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise P0P2PlatformDiagnosticError("current worker plan is invalid")
    for worker in workers:
        argv = worker.get("command_argv") if isinstance(worker, dict) else None
        if not isinstance(argv, list):
            raise P0P2PlatformDiagnosticError("current worker command is invalid")
        if "--attention-backend" in argv:
            raise P0P2PlatformDiagnosticError(
                "runtime backend mutation was mixed into P0-P2 implementation"
            )


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    _require_source_ancestor(root)
    _require_authorization_absent(root)
    _require_option_c_decision(root)
    _require_runtime_remains_deferred(root)
    request = load_request(root / REQUEST_PATH)
    notebook = validate_notebook(root / NOTEBOOK_PATH)
    implementation = load_implementation_record(root / IMPLEMENTATION_RECORD_PATH)
    if implementation.notebook_sha256 != notebook["notebook_sha256"]:
        raise P0P2PlatformDiagnosticError("implementation record and notebook identity differ")
    return {
        "status": "P0_P2_PLATFORM_DIAGNOSTIC_IMPLEMENTATION_VALID",
        "request_id": request.request_id,
        "record_id": implementation.record_id,
        "source_main_merge_commit": implementation.source_main_merge_commit,
        "notebook_name": implementation.notebook_name,
        "notebook_sha256": implementation.notebook_sha256,
        "probe_count": len(request.probes),
        "required_output_count": len(request.required_outputs),
        "runtime_worker_source_changed": implementation.safety.runtime_worker_source_changed,
        "authorization_issued": implementation.safety.authorization_issued,
        "kaggle_execution_performed": implementation.safety.kaggle_execution_performed,
        "next_gate": implementation.next_gate,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        root = arguments.repo_root.resolve()
        if arguments.command == "generate":
            write_notebook(root / NOTEBOOK_PATH)
            print(
                _canonical_json(
                    {
                        "status": "P0_P2_NOTEBOOK_GENERATED",
                        "notebook_path": NOTEBOOK_PATH.as_posix(),
                        "notebook_name": NOTEBOOK_NAME,
                        "notebook_sha256": notebook_sha256(),
                    }
                )
            )
            return 0
        summary = validate_repository_package(root)
        print(_canonical_json(summary))
        return 0
    except P0P2PlatformDiagnosticError as error:
        print(
            _canonical_json(
                {
                    "error_code": "P0_P2_PLATFORM_DIAGNOSTIC_IMPLEMENTATION_INVALID",
                    "safe_message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
