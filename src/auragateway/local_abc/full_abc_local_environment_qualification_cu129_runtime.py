"""Governed CUDA 12.9 target-runtime construction for environment qualification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

RUNTIME_OUTPUT_DIRECTORY: Final = "auragateway_vllm_cu129_wheelhouse_v1"
EXPECTED_PACKAGE_COUNT: Final = 176
EXPECTED_MANIFEST_ENTRY_COUNT: Final = 182
EXPECTED_TOTAL_WHEEL_BYTES: Final = 5_727_339_111
INSTALLATION_EXECUTOR: Final = "BASE_PIP_TARGET_DIRECTORY"
DEPENDENCY_VALIDATION: Final = "CONTROLLED_TARGET_METADATA_AND_PACKAGING"
PYTHON_STARTUP_POLICY: Final = "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP"
LOADER_POLICY: Final = "TARGET_NVIDIA_LIBRARIES_PREPENDED"
TARGET_INTERPRETER_TOKEN: Final = "${AURAGATEWAY_TARGET_PYTHON}"
TARGET_RUNTIME_ROOT_TOKEN: Final = "${AURAGATEWAY_TARGET_RUNTIME_ROOT}"
TARGET_SITE_PACKAGES_TOKEN: Final = "${AURAGATEWAY_TARGET_SITE_PACKAGES}"

EXPECTED_CONTROL_HASHES: Final = {
    "requirements.in": "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f",
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

EXPECTED_TOP_LEVEL: Final = frozenset({*EXPECTED_CONTROL_HASHES, "wheels"})
EXPECTED_MANIFEST_CONTROL_PATHS: Final = frozenset(
    {
        "requirements.in",
        "resolution_lock.json",
        "materialization.lock.txt",
        "requirements.lock.txt",
        "install_runtime.py",
        "runtime_manifest.json",
    }
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

CONTROLLED_BOOTSTRAP = """
import runpy
import site
import sys
import types
from pathlib import Path

expected_root = Path(sys.argv.pop(1)).resolve()
target_site = Path(sys.argv.pop(1)).resolve()
module_name = sys.argv.pop(1)
expected_site = (
    expected_root
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
).resolve()
if target_site != expected_site:
    raise RuntimeError("target site-packages does not match the runtime root")


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
sys.argv = [module_name, *sys.argv[1:]]
runpy.run_module(module_name, run_name="__main__")
""".strip()

CONTROLLED_SCRIPT_BOOTSTRAP = """
import site
import sys
import types
from pathlib import Path

expected_root = Path(sys.argv.pop(1)).resolve()
target_site = Path(sys.argv.pop(1)).resolve()
payload = sys.argv.pop(1)
expected_site = (
    expected_root
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
).resolve()
if target_site != expected_site:
    raise RuntimeError("target site-packages does not match the runtime root")


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
sys.argv = ["<auragateway-controlled>", *sys.argv[1:]]
exec(compile(payload, "<auragateway-controlled>", "exec"))
""".strip()

DEPENDENCY_LOCK_SCRIPT = """
import importlib.metadata
import json
import os
import platform
import torch
import transformers
import vllm
from pathlib import Path

site_packages = Path(__import__('sys').argv[1]).resolve()
distributions = tuple(importlib.metadata.distributions(path=[str(site_packages)]))
print(
    json.dumps(
        {
            'python': platform.python_version(),
            'torch': torch.__version__,
            'cuda': torch.version.cuda or 'unavailable',
            'transformers': transformers.__version__,
            'vllm_module': vllm.__version__,
            'vllm_distribution': importlib.metadata.version('vllm'),
            'distribution_count': len(distributions),
            'attention_backend': os.getenv('VLLM_ATTENTION_BACKEND', 'auto'),
        },
        sort_keys=True,
    )
)
""".strip()


class ManifestEntry(TypedDict):
    path: str
    sha256: str
    size_bytes: int


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Cu129RuntimeManifestBinding(_StrictModel):
    """Exact logical runtime authority stored in the offline manifest."""

    output_directory_name: str
    resolution_lock_sha256: str
    runtime_manifest_sha256: str
    sha256_manifest_sha256: str
    materialization_receipt_sha256: str
    package_count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_authority(self) -> Cu129RuntimeManifestBinding:
        if self.output_directory_name != RUNTIME_OUTPUT_DIRECTORY:
            raise ValueError("CUDA 12.9 runtime output directory drifted")
        expected = {
            "resolution_lock_sha256": EXPECTED_CONTROL_HASHES["resolution_lock.json"],
            "runtime_manifest_sha256": EXPECTED_CONTROL_HASHES["runtime_manifest.json"],
            "sha256_manifest_sha256": EXPECTED_CONTROL_HASHES["sha256_manifest.json"],
            "materialization_receipt_sha256": EXPECTED_CONTROL_HASHES[
                "materialization_receipt.json"
            ],
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("CUDA 12.9 runtime control identity drifted")
        if self.package_count != EXPECTED_PACKAGE_COUNT:
            raise ValueError("CUDA 12.9 runtime package count drifted")
        return self


@dataclass(frozen=True)
class Cu129TargetRuntime:
    """Realized target runtime paths and deterministic policy identities."""

    wheelhouse_root: Path
    runtime_root: Path
    site_packages: Path
    base_python: Path
    target_python: Path
    target_library_directories: tuple[Path, ...]

    @property
    def python_startup_policy(self) -> str:
        return PYTHON_STARTUP_POLICY

    @property
    def loader_policy(self) -> str:
        return LOADER_POLICY


@dataclass(frozen=True)
class WheelhouseValidation:
    """Validated wheelhouse topology without loading runtime modules."""

    root: Path
    manifest_entry_count: int
    wheel_entry_count: int
    package_count: int
    total_wheel_bytes: int


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_command_sha256(argv: Sequence[str]) -> str:
    payload = json.dumps(list(argv), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def worker_command_template(port: int) -> tuple[str, ...]:
    if port not in {8001, 8002}:
        raise ValueError("worker port must remain in the governed topology")
    return (
        TARGET_INTERPRETER_TOKEN,
        "-S",
        "-c",
        CONTROLLED_BOOTSTRAP,
        TARGET_RUNTIME_ROOT_TOKEN,
        TARGET_SITE_PACKAGES_TOKEN,
        "vllm.entrypoints.openai.api_server",
        "--model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--revision",
        "7ae557604adf67be50417f59c2c2f167def9a775",
        "--tokenizer",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--tokenizer-revision",
        "7ae557604adf67be50417f59c2c2f167def9a775",
        "--served-model-name",
        "local-qwen2.5-0.5b-instruct",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--dtype",
        "auto",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.85",
        "--max-num-seqs",
        "8",
        "--enable-prefix-caching",
        "--disable-log-requests",
    )


def discover_wheelhouse(input_root: Path, binding: Cu129RuntimeManifestBinding) -> Path:
    root = input_root.resolve()
    candidates = tuple(
        sorted(
            (
                path.resolve()
                for path in root.rglob(binding.output_directory_name)
                if path.is_dir() and not path.is_symlink()
            ),
            key=lambda item: item.as_posix(),
        )
    )
    if len(candidates) != 1:
        raise RuntimeError("expected exactly one governed CUDA 12.9 wheelhouse output directory")
    candidate = candidates[0]
    if root not in candidate.parents:
        raise RuntimeError("CUDA 12.9 wheelhouse escaped the input root")
    return candidate


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name} must contain one JSON object")
    return cast(dict[str, object], payload)


def _parse_manifest_entries(payload: Mapping[str, object]) -> tuple[ManifestEntry, ...]:
    entries = payload.get("entries")
    if payload.get("schema_version") != "1.0.0" or not isinstance(entries, list):
        raise RuntimeError("wheelhouse checksum manifest contract drifted")
    if len(entries) != EXPECTED_MANIFEST_ENTRY_COUNT:
        raise RuntimeError("wheelhouse checksum manifest entry count drifted")
    parsed: list[ManifestEntry] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("wheelhouse checksum entry is invalid")
        path = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if (
            not isinstance(path, str)
            or not isinstance(digest, str)
            or _SHA256_PATTERN.fullmatch(digest) is None
            or not isinstance(size_bytes, int)
            or size_bytes < 0
        ):
            raise RuntimeError("wheelhouse checksum entry fields are invalid")
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("wheelhouse checksum path is unsafe")
        parsed.append(ManifestEntry(path=path, sha256=digest, size_bytes=size_bytes))
    paths = tuple(str(entry["path"]) for entry in parsed)
    if len(paths) != len(set(paths)):
        raise RuntimeError("wheelhouse checksum paths are not unique")
    return tuple(parsed)


def validate_wheelhouse(
    root: Path,
    binding: Cu129RuntimeManifestBinding,
    *,
    verify_payload_hashes: bool = True,
) -> WheelhouseValidation:
    wheelhouse = root.resolve()
    observed_top_level = frozenset(path.name for path in wheelhouse.iterdir())
    if observed_top_level != EXPECTED_TOP_LEVEL:
        raise RuntimeError("wheelhouse top-level topology drifted")
    for name, expected_hash in EXPECTED_CONTROL_HASHES.items():
        path = wheelhouse / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"wheelhouse control file is missing or unsafe: {name}")
        if file_sha256(path) != expected_hash:
            raise RuntimeError(f"wheelhouse control file identity drifted: {name}")

    Cu129RuntimeManifestBinding.model_validate(binding.model_dump())
    manifest = _load_json_object(wheelhouse / "sha256_manifest.json")
    entries = _parse_manifest_entries(manifest)
    wheel_entries = tuple(entry for entry in entries if str(entry["path"]).startswith("wheels/"))
    control_paths = frozenset(str(entry["path"]) for entry in entries) - frozenset(
        str(entry["path"]) for entry in wheel_entries
    )
    if len(wheel_entries) != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError("wheelhouse package count drifted")
    if control_paths != EXPECTED_MANIFEST_CONTROL_PATHS:
        raise RuntimeError("wheelhouse control-manifest topology drifted")

    total_wheel_bytes = sum(entry["size_bytes"] for entry in wheel_entries)
    if total_wheel_bytes != EXPECTED_TOTAL_WHEEL_BYTES:
        raise RuntimeError("wheelhouse total wheel bytes drifted")

    if verify_payload_hashes:
        for entry in entries:
            relative = PurePosixPath(str(entry["path"]))
            path = wheelhouse.joinpath(*relative.parts)
            if not path.is_file() or path.is_symlink():
                raise RuntimeError(f"wheelhouse payload member is missing: {relative}")
            if path.stat().st_size != entry["size_bytes"]:
                raise RuntimeError(f"wheelhouse payload size drifted: {relative}")
            if file_sha256(path) != str(entry["sha256"]):
                raise RuntimeError(f"wheelhouse payload identity drifted: {relative}")

    return WheelhouseValidation(
        root=wheelhouse,
        manifest_entry_count=len(entries),
        wheel_entry_count=len(wheel_entries),
        package_count=len(wheel_entries),
        total_wheel_bytes=total_wheel_bytes,
    )


def target_site_packages(runtime_root: Path) -> Path:
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    return runtime_root / "lib" / version / "site-packages"


def build_install_argv(base_python: Path, wheelhouse: Path, site_packages: Path) -> tuple[str, ...]:
    return (
        str(base_python),
        "-m",
        "pip",
        "--isolated",
        "--disable-pip-version-check",
        "install",
        "--no-index",
        "--no-cache-dir",
        "--no-deps",
        "--ignore-installed",
        "--find-links",
        str(wheelhouse / "wheels"),
        "--require-hashes",
        "--target",
        str(site_packages),
        "-r",
        str(wheelhouse / "requirements.lock.txt"),
    )


def controlled_python_argv(
    runtime: Cu129TargetRuntime,
    module_or_script: str,
    *arguments: str,
    module: bool = False,
) -> tuple[str, ...]:
    if module:
        return (
            str(runtime.target_python),
            "-S",
            "-c",
            CONTROLLED_BOOTSTRAP,
            str(runtime.runtime_root),
            str(runtime.site_packages),
            module_or_script,
            *arguments,
        )
    return (
        str(runtime.target_python),
        "-S",
        "-c",
        CONTROLLED_SCRIPT_BOOTSTRAP,
        str(runtime.runtime_root),
        str(runtime.site_packages),
        module_or_script,
        *arguments,
    )


def discover_target_library_directories(site_packages: Path) -> tuple[Path, ...]:
    nvidia_root = site_packages / "nvidia"
    preferred = ("nvjitlink", "cusparse", "cuda_runtime", "cublas")
    discovered = {
        path.parent.resolve()
        for path in nvidia_root.glob("*/lib/*.so*")
        if path.is_file() and not path.is_symlink()
    }
    ordered = sorted(
        discovered,
        key=lambda path: (
            next(
                (index for index, name in enumerate(preferred) if path.parent.name == name),
                len(preferred),
            ),
            path.as_posix(),
        ),
    )
    if not ordered:
        raise RuntimeError("target runtime contains no NVIDIA library directories")
    return tuple(ordered)


def build_target_environment(
    runtime: Cu129TargetRuntime,
    inherited: Mapping[str, str],
    *,
    gpu_index: int | None = None,
    model_cache_root: Path | None = None,
) -> dict[str, str]:
    environment = dict(inherited)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    inherited_ld = tuple(
        value for value in environment.get("LD_LIBRARY_PATH", "").split(os.pathsep) if value
    )
    target_ld = tuple(str(path) for path in runtime.target_library_directories)
    environment["LD_LIBRARY_PATH"] = os.pathsep.join((*target_ld, *inherited_ld))
    environment["AURAGATEWAY_RUNTIME_INSTALLATION_EXECUTOR"] = INSTALLATION_EXECUTOR
    environment["AURAGATEWAY_RUNTIME_DEPENDENCY_VALIDATION"] = DEPENDENCY_VALIDATION
    environment["AURAGATEWAY_RUNTIME_PYTHON_STARTUP_POLICY"] = PYTHON_STARTUP_POLICY
    environment["AURAGATEWAY_RUNTIME_LOADER_POLICY"] = LOADER_POLICY
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"
    if gpu_index is not None:
        environment["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    if model_cache_root is not None:
        environment["HF_HOME"] = str(model_cache_root)
    return environment


def realize_worker_command(template: Sequence[str], runtime: Cu129TargetRuntime) -> tuple[str, ...]:
    if not template or template[0] != TARGET_INTERPRETER_TOKEN:
        raise RuntimeError("worker command does not use the target interpreter token")
    if TARGET_RUNTIME_ROOT_TOKEN not in template:
        raise RuntimeError("worker command does not bind the target runtime root")
    if TARGET_SITE_PACKAGES_TOKEN not in template:
        raise RuntimeError("worker command does not bind target site-packages")
    replacements = {
        TARGET_INTERPRETER_TOKEN: str(runtime.target_python),
        TARGET_RUNTIME_ROOT_TOKEN: str(runtime.runtime_root),
        TARGET_SITE_PACKAGES_TOKEN: str(runtime.site_packages),
    }
    return tuple(replacements.get(value, value) for value in template)
