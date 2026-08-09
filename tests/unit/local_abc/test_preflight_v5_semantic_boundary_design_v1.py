from __future__ import annotations

import json
import shutil
from functools import partial
from pathlib import Path

import pytest
from pydantic import BaseModel

from auragateway.local_abc import preflight_v5_semantic_boundary_design_v1

design = preflight_v5_semantic_boundary_design_v1


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = (
        Path("src/auragateway/local_abc/preflight_v5_semantic_boundary_design_v1.py"),
        design.ADR_PATH,
        design.REPORT_PATH,
        design.RUNBOOK_PATH,
    )
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)

    upstream = tmp_path / design.UPSTREAM_RECONCILIATION_RECORD
    upstream.parent.mkdir(parents=True, exist_ok=True)
    upstream.write_text(
        json.dumps(
            {
                "classification": design.EXPECTED_UPSTREAM_CLASSIFICATION,
                "failure_code": design.EXPECTED_UPSTREAM_FAILURE_CODE,
                "primary_invariant": design.EXPECTED_UPSTREAM_INVARIANT,
                "runtime_incompatibility_established": False,
                "next_kaggle_execution_authorized": False,
                "next_gate": design.EXPECTED_UPSTREAM_NEXT_GATE,
                "successor_gate": {
                    "semantic_decisions_reading_stdout_excerpt": 0,
                    "semantic_decisions_reading_stderr_excerpt": 0,
                    "lossy_transformations_before_semantic_decision": 0,
                    "truncation_before_semantic_decision": 0,
                    "path_decisions_use_raw_canonical_paths": True,
                    "evidence_policy_is_terminal": True,
                    "sanitizer_metamorphic_invariance": "PASS",
                    "excerpt_length_metamorphic_invariance": "PASS",
                    "symlink_escape_negative_case": "PASS",
                    "ambient_python_native_negative_case": "PASS",
                    "cuda_stub_negative_case": "PASS",
                    "real_driver_positive_case": "PASS",
                    "unknown_native_origin_fails_closed": "PASS",
                    "statically_predictable_successor_failures": 0,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return tmp_path


def _startup_raw(target_root: Path) -> design.RawProbeExecution:
    payload = {
        "prefix": str(target_root),
        "base_prefix": "/usr",
        "no_site_flag": 1,
        "user_site_enabled": False,
        "target_site_present": True,
        "external_package_paths": [],
        "sitecustomize_file": "<auragateway-suppressed-sitecustomize>",
        "usercustomize_file": "<auragateway-suppressed-usercustomize>",
        "pythonpath_present": False,
        "pythonhome_present": False,
        "ld_preload_present": False,
        "python_no_user_site": "1",
    }
    return design.RawProbeExecution(
        command_role="controlled_python_startup",
        returncode=0,
        timed_out=False,
        duration_ms=10,
        stdout=json.dumps(payload),
        stderr="",
    )


def test_raw_execution_is_ephemeral_non_pydantic() -> None:
    raw = design.RawProbeExecution(
        command_role="probe",
        returncode=0,
        timed_out=False,
        duration_ms=1,
        stdout="raw",
        stderr="",
    )

    assert not isinstance(raw, BaseModel)
    assert not hasattr(raw, "model_dump")


def test_semantic_functions_do_not_consume_evidence_fields() -> None:
    source = Path(design.__file__).read_text(encoding="utf-8")

    audit = design.audit_semantic_channel_source(source)

    assert audit["semantic_channel_violations"] == []
    assert audit["semantic_decisions_reading_stdout_excerpt"] == 0
    assert audit["semantic_decisions_reading_stderr_excerpt"] == 0
    assert audit["lossy_transformations_before_semantic_decision"] == 0
    assert audit["truncation_before_semantic_decision"] == 0


def test_controlled_startup_semantics_use_raw_prefix(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()

    raw = _startup_raw(target)
    observation, decision = design.evaluate_semantics(
        raw,
        design.parse_controlled_startup,
        partial(
            design.validate_controlled_startup,
            expected_root=target,
        ),
    )

    assert observation is not None
    assert observation.prefix == target
    assert decision.status == design.ProbeStatus.PASSED


@pytest.mark.parametrize(
    ("replacement", "limit"),
    [
        ("<working>", 12_000),
        ("<w>", 256),
        ("REDACTED", 64),
    ],
)
def test_sanitizer_policy_cannot_change_startup_decision(
    tmp_path: Path,
    replacement: str,
    limit: int,
) -> None:
    target = tmp_path / "kaggle" / "working" / "target"
    target.mkdir(parents=True)

    raw = _startup_raw(target)
    observation, decision = design.evaluate_semantics(
        raw,
        design.parse_controlled_startup,
        partial(
            design.validate_controlled_startup,
            expected_root=target,
        ),
    )
    evidence = design.project_evidence(
        raw,
        decision,
        policy=design.EvidencePolicy(
            working_replacement=replacement,
            excerpt_limit=limit,
        ),
    )

    assert observation is not None
    assert decision.status == design.ProbeStatus.PASSED
    assert evidence.status == decision.status


def test_excerpt_length_does_not_change_native_semantics(
    tmp_path: Path,
) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    library = target_site / "torch" / "lib" / "libtorch.so"
    library.parent.mkdir(parents=True)
    library.write_bytes(b"x")
    driver = tmp_path / "driver"
    driver.mkdir()

    raw = design.RawProbeExecution(
        command_role="native_linker_static_provenance",
        returncode=0,
        timed_out=False,
        duration_ms=1,
        stdout=("libtorch.so => " + str(library) + " (0x0)\n" + ("diagnostic-padding-" * 500)),
        stderr="",
    )
    observation, decision = design.evaluate_semantics(
        raw,
        design.parse_ldd,
        partial(
            design.validate_native_linker,
            target_site=target_site,
            real_driver_root=driver,
        ),
    )
    assert observation is not None
    assert decision.status == design.ProbeStatus.PASSED

    for limit in (32, 128, 12_000):
        evidence = design.project_evidence(
            raw,
            decision,
            policy=design.EvidencePolicy(excerpt_limit=limit),
        )
        assert evidence.status == design.ProbeStatus.PASSED


def test_symlink_escape_fails_closed(tmp_path: Path) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    outside = tmp_path / "outside" / "libescape.so"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    link = target_site / "libescape.so"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    driver = tmp_path / "driver"
    driver.mkdir()

    origin = design.classify_native_origin(
        link,
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == design.NativeOriginClass.UNKNOWN


def test_ambient_python_native_library_is_prohibited(
    tmp_path: Path,
) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    ambient = tmp_path / "ambient" / "site-packages" / "pkg" / "lib.so"
    ambient.parent.mkdir(parents=True)
    ambient.write_bytes(b"x")
    driver = tmp_path / "driver"
    driver.mkdir()

    origin = design.classify_native_origin(
        ambient,
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == design.NativeOriginClass.PROHIBITED_AMBIENT


def test_cuda_stub_path_is_prohibited_before_resolution(
    tmp_path: Path,
) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()

    origin = design.classify_native_origin(
        Path("/usr/local/cuda/lib64/stubs/libcuda.so"),
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == design.NativeOriginClass.PROHIBITED_AMBIENT


def test_real_driver_root_is_permitted(tmp_path: Path) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    libcuda = driver / "libcuda.so.1"
    libcuda.write_bytes(b"x")

    origin = design.classify_native_origin(
        libcuda,
        target_site=target_site,
        real_driver_root=driver,
    )

    assert origin == design.NativeOriginClass.PERMITTED_HOST_PLATFORM


def test_unknown_native_origin_fails_closed(tmp_path: Path) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    unknown = tmp_path / "other" / "libtorch_mystery.so"
    unknown.parent.mkdir()
    unknown.write_bytes(b"x")

    decision = design.validate_native_origin_set(
        [unknown],
        target_site=target_site,
        real_driver_root=driver,
        permitted=frozenset(
            {
                design.NativeOriginClass.TARGET_OWNED,
                design.NativeOriginClass.PERMITTED_HOST_PLATFORM,
            }
        ),
    )

    assert decision.status == design.ProbeStatus.FAILED
    assert decision.failure_code == design.FailureCode.UNKNOWN_NATIVE_ORIGIN


def test_native_inventory_uses_raw_canonical_containment(
    tmp_path: Path,
) -> None:
    target_vllm = tmp_path / "target" / "site-packages" / "vllm"
    target_vllm.mkdir(parents=True)
    extension = target_vllm / "_C_stable_libtorch.so"
    extension.write_bytes(b"x")

    raw = design.RawProbeExecution(
        command_role="target_native_inventory",
        returncode=0,
        timed_out=False,
        duration_ms=1,
        stdout=json.dumps(
            {
                "required": [
                    {
                        "path": str(extension),
                        "sha256": "a" * 64,
                        "size_bytes": 1,
                    }
                ],
                "legacy_c_candidates": [],
                "optional_candidates": [],
            }
        ),
        stderr="",
    )
    observation, decision = design.evaluate_semantics(
        raw,
        design.parse_native_inventory,
        partial(
            design.validate_native_inventory,
            target_vllm_root=target_vllm,
        ),
    )

    assert observation is not None
    assert decision.status == design.ProbeStatus.PASSED


def test_generic_os_library_is_outside_governed_native_set(
    tmp_path: Path,
) -> None:
    target_site = tmp_path / "target" / "site-packages"
    target_site.mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()
    os_library = tmp_path / "system" / "libc.so.6"
    os_library.parent.mkdir()
    os_library.write_bytes(b"x")

    decision = design.validate_native_origin_set(
        [os_library],
        target_site=target_site,
        real_driver_root=driver,
        permitted=frozenset(
            {
                design.NativeOriginClass.TARGET_OWNED,
                design.NativeOriginClass.PERMITTED_HOST_PLATFORM,
            }
        ),
    )

    assert decision.status == design.ProbeStatus.PASSED


def test_native_extension_uses_canonical_raw_path(tmp_path: Path) -> None:
    target_vllm = tmp_path / "target" / "site-packages" / "vllm"
    target_vllm.mkdir(parents=True)
    extension = target_vllm / "_C_stable_libtorch.so"
    extension.write_bytes(b"x")

    raw = design.RawProbeExecution(
        command_role="vllm_native_extension",
        returncode=0,
        timed_out=False,
        duration_ms=1,
        stdout=json.dumps(
            {
                "native_extension": "vllm._C_stable_libtorch",
                "file": str(extension),
            }
        ),
        stderr="",
    )
    observation, decision = design.evaluate_semantics(
        raw,
        design.parse_native_extension,
        partial(
            design.validate_native_extension,
            expected_module="vllm._C_stable_libtorch",
            target_vllm_root=target_vllm,
        ),
    )

    assert observation is not None
    assert decision.status == design.ProbeStatus.PASSED


def test_generate_and_validate_design_record(
    candidate_repo: Path,
) -> None:
    first = design.generate(candidate_repo)
    first_bytes = (candidate_repo / design.RECORD_PATH).read_bytes()
    second = design.generate(candidate_repo)
    second_bytes = (candidate_repo / design.RECORD_PATH).read_bytes()

    assert first == second
    assert first_bytes == second_bytes

    result = design.validate_implementation(candidate_repo)

    assert result["status"] == "V5_SEMANTIC_BOUNDARY_DESIGN_VALID"
    assert result["implementation_status"] == "DESIGN_IMPLEMENTED_NOT_VERIFIER_IMPLEMENTED"
    assert result["next_kaggle_execution_authorized"] is False
