"""Regression tests for the governed CUDA 12.9 qualification runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_environment_qualification_cu129_runtime import (
    CONTROLLED_BOOTSTRAP,
    DEPENDENCY_LOCK_SCRIPT,
    DEPENDENCY_VALIDATION,
    EXPECTED_CONTROL_HASHES,
    EXPECTED_PACKAGE_COUNT,
    INSTALLATION_EXECUTOR,
    LOADER_POLICY,
    PYTHON_STARTUP_POLICY,
    RUNTIME_OUTPUT_DIRECTORY,
    TARGET_INTERPRETER_TOKEN,
    TARGET_RUNTIME_ROOT_TOKEN,
    TARGET_SITE_PACKAGES_TOKEN,
    VLLM_API_SERVER_MODULE,
    VLLM_API_SERVER_REQUIRED_OPTIONS,
    VLLM_REQUEST_LOGGING_DISABLED_OPTION,
    Cu129RuntimeManifestBinding,
    Cu129TargetRuntime,
    build_install_argv,
    build_target_environment,
    canonical_command_sha256,
    controlled_python_argv,
    discover_wheelhouse,
    realize_worker_command,
    worker_command_options,
    worker_command_template,
)


def _binding() -> Cu129RuntimeManifestBinding:
    return Cu129RuntimeManifestBinding(
        output_directory_name=RUNTIME_OUTPUT_DIRECTORY,
        resolution_lock_sha256=EXPECTED_CONTROL_HASHES["resolution_lock.json"],
        runtime_manifest_sha256=EXPECTED_CONTROL_HASHES["runtime_manifest.json"],
        sha256_manifest_sha256=EXPECTED_CONTROL_HASHES["sha256_manifest.json"],
        materialization_receipt_sha256=EXPECTED_CONTROL_HASHES["materialization_receipt.json"],
        package_count=EXPECTED_PACKAGE_COUNT,
    )


def _runtime(tmp_path: Path) -> Cu129TargetRuntime:
    root = tmp_path / "runtime"
    site_packages = root / "lib" / "python3.12" / "site-packages"
    target_python = root / "bin" / "python"
    target_python.parent.mkdir(parents=True)
    target_python.write_text("python", encoding="utf-8")
    site_packages.mkdir(parents=True)
    libraries = (
        site_packages / "nvidia" / "nvjitlink" / "lib",
        site_packages / "nvidia" / "cusparse" / "lib",
    )
    for directory in libraries:
        directory.mkdir(parents=True)
    return Cu129TargetRuntime(
        wheelhouse_root=tmp_path / "wheelhouse",
        runtime_root=root,
        site_packages=site_packages,
        base_python=Path("/usr/bin/python3"),
        target_python=target_python,
        target_library_directories=libraries,
    )


def test_runtime_binding_accepts_exact_authority() -> None:
    binding = _binding()

    assert binding.output_directory_name == RUNTIME_OUTPUT_DIRECTORY
    assert binding.package_count == 176


def test_runtime_binding_rejects_resolution_lock_drift() -> None:
    payload = _binding().model_dump(mode="python")
    payload["resolution_lock_sha256"] = "f" * 64

    with pytest.raises(ValidationError, match="control identity drifted"):
        Cu129RuntimeManifestBinding.model_validate(payload)


def test_worker_templates_bind_controlled_target_runtime() -> None:
    first = worker_command_template(8001)
    second = worker_command_template(8002)

    assert first[:7] == (
        TARGET_INTERPRETER_TOKEN,
        "-S",
        "-c",
        CONTROLLED_BOOTSTRAP,
        TARGET_RUNTIME_ROOT_TOKEN,
        TARGET_SITE_PACKAGES_TOKEN,
        "vllm.entrypoints.openai.api_server",
    )
    assert first[0] != "python"
    assert first[6] == VLLM_API_SERVER_MODULE
    assert VLLM_REQUEST_LOGGING_DISABLED_OPTION in first
    assert "--disable-log-requests" not in first
    assert worker_command_options(first) == frozenset(VLLM_API_SERVER_REQUIRED_OPTIONS)
    assert canonical_command_sha256(first) == (
        "fe37b6f369b4d83b4aea467f3e4d06f32bd62a8b44b4568665255ec35552958f"
    )
    assert canonical_command_sha256(second) == (
        "c28cea7cdfd6d5034a94ac34f090973949bbd401c5179493ddca44b17899fd06"
    )


def _write_fake_vllm_cli(
    site_packages: Path,
    *,
    include_logging_disable_option: bool,
) -> None:
    api_server = site_packages / "vllm/entrypoints/openai/api_server.py"
    api_server.parent.mkdir(parents=True)
    (site_packages / "vllm/__init__.py").write_text(
        '__version__ = "0.19.1"\n',
        encoding="utf-8",
    )
    (site_packages / "vllm/entrypoints/__init__.py").write_text("", encoding="utf-8")
    (site_packages / "vllm/entrypoints/openai/__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    options = list(VLLM_API_SERVER_REQUIRED_OPTIONS)
    if not include_logging_disable_option:
        options.remove(VLLM_REQUEST_LOGGING_DISABLED_OPTION)
    option_lines = "\n".join(
        f'parser.add_argument("{option}", action="store_true")'
        if option in {"--enable-prefix-caching", VLLM_REQUEST_LOGGING_DISABLED_OPTION}
        else f'parser.add_argument("{option}")'
        for option in options
    )
    api_server.write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        f"{option_lines}\n"
        "parser.parse_args()\n",
        encoding="utf-8",
    )
    (site_packages / "torch.py").write_text(
        '__version__ = "2.10.0+cu129"\nclass _Version:\n    cuda = "12.9"\nversion = _Version()\n',
        encoding="utf-8",
    )
    (site_packages / "transformers.py").write_text(
        '__version__ = "5.5.3"\n',
        encoding="utf-8",
    )
    dist_info = site_packages / "vllm-0.19.1.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: vllm\nVersion: 0.19.1\n",
        encoding="utf-8",
    )


def _run_dependency_lock_script(site_packages: Path) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        str(site_packages) if not existing else os.pathsep.join((str(site_packages), existing))
    )
    return subprocess.run(
        [sys.executable, "-c", DEPENDENCY_LOCK_SCRIPT, str(site_packages)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=20,
    )


def test_dependency_lock_script_accepts_complete_pinned_cli(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    _write_fake_vllm_cli(site_packages, include_logging_disable_option=True)

    result = _run_dependency_lock_script(site_packages)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["vllm_api_server_cli_capability"] == "validated"
    assert payload["vllm_api_server_option_count"] >= len(VLLM_API_SERVER_REQUIRED_OPTIONS)
    assert len(payload["vllm_api_server_help_sha256"]) == 64


def test_dependency_lock_script_rejects_incomplete_pinned_cli(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    _write_fake_vllm_cli(site_packages, include_logging_disable_option=False)

    result = _run_dependency_lock_script(site_packages)

    assert result.returncode != 0
    assert "pinned vLLM CLI does not support governed worker options" in result.stderr
    assert VLLM_REQUEST_LOGGING_DISABLED_OPTION in result.stderr


def test_dependency_lock_script_validates_pinned_vllm_cli_before_workers() -> None:
    assert "vllm_api_server_cli_capability" in DEPENDENCY_LOCK_SCRIPT
    assert "runpy.run_module" in DEPENDENCY_LOCK_SCRIPT
    assert "pinned vLLM CLI does not support governed worker options" in (DEPENDENCY_LOCK_SCRIPT)
    assert "--no-enable-log-requests" in DEPENDENCY_LOCK_SCRIPT
    assert "--disable-log-requests" not in DEPENDENCY_LOCK_SCRIPT


def test_discover_wheelhouse_requires_one_governed_directory(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="exactly one governed"):
        discover_wheelhouse(tmp_path, _binding())

    expected = tmp_path / "input-a" / RUNTIME_OUTPUT_DIRECTORY
    expected.mkdir(parents=True)
    assert discover_wheelhouse(tmp_path, _binding()) == expected.resolve()

    (tmp_path / "input-b" / RUNTIME_OUTPUT_DIRECTORY).mkdir(parents=True)
    with pytest.raises(RuntimeError, match="exactly one governed"):
        discover_wheelhouse(tmp_path, _binding())


def test_install_argv_uses_base_pip_target_directory(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    site_packages = tmp_path / "runtime" / "site-packages"
    argv = build_install_argv(Path("/base/python"), wheelhouse, site_packages)

    assert argv[:6] == (
        str(Path("/base/python")),
        "-m",
        "pip",
        "--isolated",
        "--disable-pip-version-check",
        "install",
    )
    assert "--no-index" in argv
    assert "--require-hashes" in argv
    assert argv[argv.index("--target") + 1] == str(site_packages)
    assert "--python" not in argv
    assert "--prefix" not in argv


def test_controlled_python_uses_target_interpreter(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    argv = controlled_python_argv(runtime, "probe.module", "--flag", module=True)

    assert argv[0] == str(runtime.target_python)
    assert argv[1:4] == ("-S", "-c", CONTROLLED_BOOTSTRAP)
    assert argv[4] == str(runtime.runtime_root)
    assert argv[5] == str(runtime.site_packages)
    assert argv[6:] == ("probe.module", "--flag")


def test_target_environment_prepends_target_libraries(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    inherited = {
        "PYTHONHOME": "/unsafe/home",
        "PYTHONPATH": "/unsafe/path",
        "LD_LIBRARY_PATH": "/usr/local/cuda/lib64",
        "KEEP_ME": "1",
    }

    environment = build_target_environment(
        runtime,
        inherited,
        gpu_index=1,
        model_cache_root=tmp_path / "model-cache",
    )

    assert "PYTHONHOME" not in environment
    assert "PYTHONPATH" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["CUDA_VISIBLE_DEVICES"] == "1"
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert environment["AURAGATEWAY_RUNTIME_INSTALLATION_EXECUTOR"] == (INSTALLATION_EXECUTOR)
    assert environment["AURAGATEWAY_RUNTIME_DEPENDENCY_VALIDATION"] == (DEPENDENCY_VALIDATION)
    assert environment["AURAGATEWAY_RUNTIME_PYTHON_STARTUP_POLICY"] == (PYTHON_STARTUP_POLICY)
    assert environment["AURAGATEWAY_RUNTIME_LOADER_POLICY"] == LOADER_POLICY
    library_paths = environment["LD_LIBRARY_PATH"].split(os.pathsep)
    assert library_paths[:2] == [str(path) for path in runtime.target_library_directories]
    assert library_paths[-1] == "/usr/local/cuda/lib64"


def test_realize_worker_command_rejects_generic_python(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    with pytest.raises(RuntimeError, match="target interpreter token"):
        realize_worker_command(("python", "-m", "vllm"), runtime)


def test_realize_worker_command_resolves_only_governed_tokens(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    template = worker_command_template(8001)

    command = realize_worker_command(template, runtime)

    assert command[0] == str(runtime.target_python)
    assert command[4] == str(runtime.runtime_root)
    assert command[5] == str(runtime.site_packages)
    assert TARGET_INTERPRETER_TOKEN not in command
    assert TARGET_RUNTIME_ROOT_TOKEN not in command
    assert TARGET_SITE_PACKAGES_TOKEN not in command
    assert json.loads(json.dumps(list(command)))[0] == str(runtime.target_python)


def test_controlled_python_preserves_configured_interpreter_path(
    tmp_path: Path,
) -> None:
    base_python = tmp_path / "base-python"
    base_python.write_text("python", encoding="utf-8")
    runtime_root = tmp_path / "runtime"
    target_python = runtime_root / "bin" / ".." / "python-link"
    site_packages = runtime_root / "lib/python3.12/site-packages"
    site_packages.mkdir(parents=True)
    runtime = Cu129TargetRuntime(
        wheelhouse_root=tmp_path / "wheelhouse",
        runtime_root=runtime_root,
        site_packages=site_packages,
        base_python=base_python,
        target_python=target_python,
        target_library_directories=(site_packages / "nvidia/nvjitlink/lib",),
    )

    argv = controlled_python_argv(runtime, "probe.module", module=True)

    assert argv[0] == str(target_python)
    assert argv[0] != str(target_python.resolve())
