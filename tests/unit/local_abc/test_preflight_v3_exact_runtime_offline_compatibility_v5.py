from __future__ import annotations

import hashlib
import json
import shutil
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v5 as verifier,
)


def _copy(
    source_root: Path,
    target_root: Path,
    relative: Path,
) -> None:
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_root / relative, target)


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = (
        verifier.NOTEBOOK_PATH,
        verifier.SOURCE_PATH,
        verifier.TEST_PATH,
        verifier.ADR_PATH,
        verifier.REPORT_PATH,
        verifier.RUNBOOK_PATH,
    )
    for relative in paths:
        _copy(source_root, tmp_path, relative)

    design = tmp_path / verifier.SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_bytes((source_root / verifier.SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH).read_bytes())
    return tmp_path


def _runtime_namespace(
    candidate_repo: Path,
) -> dict[str, Any]:
    module_name = "auragateway_v5_runtime_test"
    module = types.ModuleType(module_name)
    namespace = module.__dict__
    sys.modules[module_name] = module
    exec(
        verifier.runtime_preamble(candidate_repo),
        namespace,
        namespace,
    )
    return namespace


def _raw(
    ns: dict[str, Any],
    *,
    role: str,
    stdout: str,
    stderr: str = "",
) -> Any:
    return ns["RawProbeExecution"](
        command_role=role,
        returncode=0,
        timed_out=False,
        duration_ms=1,
        started_at="2026-08-09T00:00:00+00:00",
        stdout=stdout,
        stderr=stderr,
    )


def test_accepted_semantic_boundary_authority_is_exact(
    candidate_repo: Path,
) -> None:
    payload = verifier.validate_semantic_boundary_design(candidate_repo)

    assert payload["raw_probe_execution_transient"] is True
    assert payload["raw_streams_persisted"] is False
    assert payload["semantic_decisions_reading_stdout_excerpt"] == 0
    assert payload["semantic_decisions_reading_stderr_excerpt"] == 0
    assert payload["evidence_projection_terminal"] is True


def test_notebook_static_semantic_channel_audit_is_clean(
    candidate_repo: Path,
) -> None:
    audit = verifier.validate_notebook(candidate_repo)

    assert audit["semantic_channel_violations"] == []
    assert audit["top_level_evidence_read_violations"] == []
    assert audit["semantic_decisions_reading_stdout_excerpt"] == 0
    assert audit["semantic_decisions_reading_stderr_excerpt"] == 0
    assert audit["lossy_transformations_before_semantic_decision"] == 0
    assert audit["truncation_before_semantic_decision"] == 0


def test_raw_execution_has_no_persistence_helper(
    candidate_repo: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    raw = _raw(
        ns,
        role="probe",
        stdout="raw",
    )

    assert not hasattr(raw, "to_dict")
    assert not hasattr(raw, "model_dump")


def test_controlled_startup_decision_uses_raw_prefix(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target = tmp_path / "target"
    target.mkdir()
    payload = {
        "prefix": str(target),
        "base_prefix": "/usr",
        "no_site_flag": 1,
        "user_site_enabled": False,
        "target_site_present": True,
        "external_package_paths": [],
        "sitecustomize_file": ("<auragateway-suppressed-sitecustomize>"),
        "usercustomize_file": ("<auragateway-suppressed-usercustomize>"),
        "pythonpath_present": False,
        "pythonhome_present": False,
        "ld_preload_present": False,
        "python_no_user_site": "1",
    }
    raw = _raw(
        ns,
        role="controlled_python_startup",
        stdout=json.dumps(payload),
    )

    observation, decision = ns["evaluate_semantics"](
        raw,
        ns["parse_controlled_startup"],
        lambda value: ns["validate_controlled_startup"](
            value,
            expected_root=target,
        ),
    )

    assert observation is not None
    assert observation.prefix == target
    assert decision.status == ns["ProbeStatus"].PASSED


@pytest.mark.parametrize(
    ("replacement", "limit"),
    [
        ("<working>", 12000),
        ("<w>", 512),
        ("REDACTED", 64),
    ],
)
def test_sanitizer_configuration_cannot_change_startup_decision(
    candidate_repo: Path,
    tmp_path: Path,
    replacement: str,
    limit: int,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target = tmp_path / "kaggle" / "working" / "target"
    target.mkdir(parents=True)
    payload = {
        "prefix": str(target),
        "base_prefix": "/usr",
        "no_site_flag": 1,
        "user_site_enabled": False,
        "target_site_present": True,
        "external_package_paths": [],
        "sitecustomize_file": ("<auragateway-suppressed-sitecustomize>"),
        "usercustomize_file": ("<auragateway-suppressed-usercustomize>"),
        "pythonpath_present": False,
        "pythonhome_present": False,
        "ld_preload_present": False,
        "python_no_user_site": "1",
    }
    raw = _raw(
        ns,
        role="controlled_python_startup",
        stdout=json.dumps(payload),
    )

    observation, decision = ns["evaluate_semantics"](
        raw,
        ns["parse_controlled_startup"],
        lambda value: ns["validate_controlled_startup"](
            value,
            expected_root=target,
        ),
    )
    evidence = ns["project_evidence"](
        raw,
        decision,
        dependencies=(),
        excerpt_limit=limit,
        evidence_replacements={
            str(tmp_path / "kaggle" / "working"): replacement,
        },
    )

    assert observation is not None
    assert decision.status == ns["ProbeStatus"].PASSED
    assert evidence.status == ns["ProbeStatus"].PASSED.value


def test_native_inventory_uses_raw_canonical_containment(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    vllm_root = tmp_path / "site-packages" / "vllm"
    vllm_root.mkdir(parents=True)
    extension = vllm_root / "_C_stable_libtorch.so"
    extension.write_bytes(b"x")
    raw = _raw(
        ns,
        role="target_native_inventory",
        stdout=json.dumps(
            {
                "required": [
                    {
                        "path": str(extension),
                        "sha256": hashlib.sha256(b"x").hexdigest(),
                        "size_bytes": 1,
                    }
                ],
                "legacy_c_candidates": [],
                "optional_candidates": [],
            }
        ),
    )

    observation, decision = ns["evaluate_semantics"](
        raw,
        ns["parse_native_inventory"],
        lambda value: ns["validate_native_inventory"](
            value,
            target_vllm_root=vllm_root,
        ),
    )

    assert observation is not None
    assert decision.status == ns["ProbeStatus"].PASSED


def test_symlink_escape_native_inventory_fails_closed(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    vllm_root = tmp_path / "site-packages" / "vllm"
    vllm_root.mkdir(parents=True)
    outside = tmp_path / "outside" / "_C_stable_libtorch.so"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    link = vllm_root / "_C_stable_libtorch.so"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this platform")

    observation = ns["NativeInventoryObservation"](
        required=(
            ns["NativeFileObservation"](
                path=link,
                sha256=hashlib.sha256(b"x").hexdigest(),
                size_bytes=1,
            ),
        ),
        legacy_c_candidates=(),
        optional_candidates=(),
    )
    decision = ns["validate_native_inventory"](
        observation,
        target_vllm_root=vllm_root,
    )

    assert decision.status == ns["ProbeStatus"].FAILED
    assert decision.failure_code == ns["FailureCode"].UNKNOWN_NATIVE_ORIGIN


def test_ambient_python_native_origin_is_prohibited(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    ambient = tmp_path / "ambient" / "site-packages" / "pkg" / "libtorch.so"
    ambient.parent.mkdir(parents=True)
    ambient.write_bytes(b"x")

    origin = ns["classify_native_origin"](
        ambient,
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == ns["NativeOriginClass"].PROHIBITED_AMBIENT


def test_cuda_stub_is_prohibited_before_resolution(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()

    origin = ns["classify_native_origin"](
        Path("/usr/local/cuda/lib64/stubs/libcuda.so"),
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == ns["NativeOriginClass"].PROHIBITED_AMBIENT


def test_real_driver_origin_is_permitted(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    libcuda = driver / "libcuda.so.1"
    libcuda.write_bytes(b"x")

    origin = ns["classify_native_origin"](
        libcuda,
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == ns["NativeOriginClass"].PERMITTED_HOST_PLATFORM


def test_unknown_governed_native_origin_fails_closed(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    unknown = tmp_path / "other" / "libtorch_mystery.so"
    unknown.parent.mkdir()
    unknown.write_bytes(b"x")

    decision = ns["validate_native_origin_set"](
        (unknown,),
        target_site=target_site,
        real_driver_root=driver,
        permitted=frozenset(
            {
                ns["NativeOriginClass"].TARGET_OWNED,
                ns["NativeOriginClass"].PERMITTED_HOST_PLATFORM,
            }
        ),
    )

    assert decision.status == ns["ProbeStatus"].FAILED
    assert decision.failure_code == ns["FailureCode"].UNKNOWN_NATIVE_ORIGIN


def test_generic_os_library_is_not_governed_native_input(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    libc = tmp_path / "system" / "libc.so.6"
    libc.parent.mkdir()
    libc.write_bytes(b"x")

    decision = ns["validate_native_origin_set"](
        (libc,),
        target_site=target_site,
        real_driver_root=driver,
        permitted=frozenset(
            {
                ns["NativeOriginClass"].TARGET_OWNED,
                ns["NativeOriginClass"].PERMITTED_HOST_PLATFORM,
            }
        ),
    )

    assert decision.status == ns["ProbeStatus"].PASSED


def test_static_linker_decision_is_excerpt_length_invariant(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    torch_lib = target_site / "torch" / "lib" / "libtorch.so"
    nvidia_lib = target_site / "nvidia" / "cusparse" / "lib" / "libcusparse.so"
    torch_lib.parent.mkdir(parents=True)
    nvidia_lib.parent.mkdir(parents=True)
    torch_lib.write_bytes(b"x")
    nvidia_lib.write_bytes(b"x")
    raw = _raw(
        ns,
        role="native_linker_static_provenance",
        stdout=(
            f"libtorch.so => {torch_lib} (0x0)\n"
            f"libcusparse.so => {nvidia_lib} (0x0)\n" + ("diagnostic-padding-" * 600)
        ),
    )

    observation, decision = ns["evaluate_semantics"](
        raw,
        ns["parse_ldd"],
        lambda value: ns["validate_native_linker"](
            value,
            target_site=target_site,
        ),
    )

    assert observation is not None
    assert decision.status == ns["ProbeStatus"].PASSED

    for limit in (32, 128, 12000):
        evidence = ns["project_evidence"](
            raw,
            decision,
            dependencies=(),
            excerpt_limit=limit,
        )
        assert evidence.status == ns["ProbeStatus"].PASSED.value


def test_static_linker_requires_target_runtime_libraries(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    observation = ns["NativeLinkerObservation"](
        unresolved_required_library=False,
        resolved_paths=(),
    )

    decision = ns["validate_native_linker"](
        observation,
        target_site=target_site,
    )

    assert decision.status == ns["ProbeStatus"].FAILED


def test_native_extension_uses_raw_canonical_path(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    vllm_root = tmp_path / "target" / "site-packages" / "vllm"
    vllm_root.mkdir(parents=True)
    extension = vllm_root / "_C_stable_libtorch.so"
    extension.write_bytes(b"x")
    raw = _raw(
        ns,
        role="vllm_native_extension",
        stdout=json.dumps(
            {
                "native_extension": "vllm._C_stable_libtorch",
                "file": str(extension),
            }
        ),
    )

    observation, decision = ns["evaluate_semantics"](
        raw,
        ns["parse_native_extension"],
        lambda value: ns["validate_native_extension"](
            value,
            target_vllm_root=vllm_root,
        ),
    )

    assert observation is not None
    assert decision.status == ns["ProbeStatus"].PASSED


def test_dynamic_provenance_requires_driver_and_target_native_sets(
    candidate_repo: Path,
    tmp_path: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    target_site = tmp_path / "target" / "site-packages"
    vllm_root = target_site / "vllm"
    torch_root = target_site / "torch"
    torch_lib = torch_root / "lib" / "libtorch.so"
    nvidia_lib = target_site / "nvidia" / "cusparse" / "lib" / "libcusparse.so"
    driver = tmp_path / "driver"
    libcuda = driver / "libcuda.so.1"
    vllm_root.mkdir(parents=True)
    torch_lib.parent.mkdir(parents=True)
    nvidia_lib.parent.mkdir(parents=True)
    driver.mkdir()
    native_file = vllm_root / "_C_stable_libtorch.so"
    torch_file = torch_root / "__init__.py"
    vllm_file = vllm_root / "__init__.py"
    for path in (
        native_file,
        torch_file,
        vllm_file,
        torch_lib,
        nvidia_lib,
        libcuda,
    ):
        path.write_bytes(b"x")

    observation = ns["NativeRuntimeProvenanceObservation"](
        native_module="vllm._C_stable_libtorch",
        native_file=native_file,
        torch_file=torch_file,
        vllm_file=vllm_file,
        cuda_available=True,
        loaded_paths=(
            torch_lib,
            nvidia_lib,
            libcuda,
        ),
    )

    original_driver = ns["REAL_DRIVER_DIRECTORY"]
    ns["REAL_DRIVER_DIRECTORY"] = driver
    try:
        decision = ns["validate_native_runtime_provenance"](
            observation,
            target_site=target_site,
        )
    finally:
        ns["REAL_DRIVER_DIRECTORY"] = original_driver

    assert decision.status == ns["ProbeStatus"].PASSED


def test_public_evidence_redacts_working_path_after_decision(
    candidate_repo: Path,
) -> None:
    ns = _runtime_namespace(candidate_repo)
    raw = _raw(
        ns,
        role="probe",
        stdout="/kaggle/working/private-path",
    )
    decision = ns["ProbeDecision"](status=ns["ProbeStatus"].PASSED)

    evidence = ns["project_evidence"](
        raw,
        decision,
        dependencies=(),
    )

    assert "/kaggle/working" not in evidence.stdout_excerpt
    assert "<working>" in evidence.stdout_excerpt


def test_generate_is_deterministic(
    candidate_repo: Path,
) -> None:
    first = verifier.generate(candidate_repo)
    first_review = (candidate_repo / verifier.REVIEW_PATH).read_bytes()
    first_record = (candidate_repo / verifier.RECORD_PATH).read_bytes()

    second = verifier.generate(candidate_repo)
    second_review = (candidate_repo / verifier.REVIEW_PATH).read_bytes()
    second_record = (candidate_repo / verifier.RECORD_PATH).read_bytes()

    assert first == second
    assert first_review == second_review
    assert first_record == second_record


def test_generated_artifacts_validate(
    candidate_repo: Path,
) -> None:
    verifier.generate(candidate_repo)

    review_sha, record_sha = verifier.validate_generated(candidate_repo)

    assert len(review_sha) == 64
    assert len(record_sha) == 64
