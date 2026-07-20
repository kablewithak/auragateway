from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_vllm_cu129_target_first_loader import (
    INSPECTION_EVIDENCE_DIRECTORY,
    RESULT_PATH,
    V4_EVIDENCE_DIRECTORY,
    V5_VERIFIER_PATH,
    TargetFirstLoaderRemediationV1,
    _load_json_object,
    _notebook_source,
    _validate_inspection_evidence,
    _validate_v4_evidence,
    canonicalize_environment,
    classify_causal_roles,
    parse_ldd_nvjitlink_resolution,
    prepend_unique_paths,
    validate_repository_package,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_repository_package_valid(repo_root: Path) -> None:
    result = validate_repository_package(repo_root)

    assert result["status"] == ("VLLM_CU129_TARGET_FIRST_LOADER_REMEDIATION_PACKAGE_VALID")
    assert result["decision"] == ("APPROVED_FOR_OFFLINE_CU129_TARGET_FIRST_LOADER_VERIFICATION_V5")
    assert result["v4_input_validation_status"] == "PASSED"
    assert result["v4_installation_status"] == "PASSED"
    assert result["v4_first_divergence"] == "torch_family_runtime"
    assert result["v4_failure_code"] == "NVJITLINK_12_9_SYMBOL_UNRESOLVED"
    assert result["inspection_status"] == "COMPLETED"
    assert result["root_cause_assignment"] == "LOADER_PRECEDENCE_CONFIRMED"
    assert result["inherited_load_status"] == "FAILED"
    assert result["target_first_load_status"] == "PASSED"
    assert result["active_verifier_title_character_count"] == 37
    assert result["canonical_loader_policy"] == ("TARGET_NVIDIA_LIBRARIES_PREPENDED")
    assert result["qualification_authorization_issued"] is False
    assert result["model_requests_performed"] == 0
    assert result["qualification_claimed"] is False


def test_decision_record_rejects_drift(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / RESULT_PATH)
    payload["decision"] = "QUALIFIED"

    with pytest.raises(ValidationError):
        TargetFirstLoaderRemediationV1.model_validate(payload)


def test_v4_evidence_proves_install_before_runtime_failure(repo_root: Path) -> None:
    result = _validate_v4_evidence(repo_root)

    assert result["input_validation_status"] == "PASSED"
    assert result["installation_status"] == "PASSED"
    assert result["first_divergence"] == "torch_family_runtime"
    assert result["failure_code"] == "NVJITLINK_12_9_SYMBOL_UNRESOLVED"
    assert (repo_root / V4_EVIDENCE_DIRECTORY / "execution.log").is_file()


def test_inspection_assigns_loader_precedence(repo_root: Path) -> None:
    result = _validate_inspection_evidence(repo_root)

    assert result["inspection_status"] == "COMPLETED"
    assert result["root_cause_assignment"] == "LOADER_PRECEDENCE_CONFIRMED"
    assert result["inherited_load_status"] == "FAILED"
    assert result["target_first_load_status"] == "PASSED"
    assert (repo_root / INSPECTION_EVIDENCE_DIRECTORY / "execution.log").is_file()


def test_prepend_unique_paths_is_target_first_and_stable() -> None:
    result = prepend_unique_paths(
        ("/target/nvjitlink", "/target/cusparse", "/shared"),
        ("/system/cuda", "/shared", "/system/driver"),
    )

    assert result == (
        "/target/nvjitlink",
        "/target/cusparse",
        "/shared",
        "/system/cuda",
        "/system/driver",
    )


def test_canonical_environment_removes_python_injection() -> None:
    base = {
        "PATH": os.pathsep.join(("/usr/bin", "/bin")),
        "LD_LIBRARY_PATH": os.pathsep.join(("/system/cuda", "/target/cusparse")),
        "PYTHONPATH": "/kaggle/lib",
        "PYTHONHOME": "/unexpected",
    }

    result = canonicalize_environment(
        base,
        ("/target/nvjitlink", "/target/cusparse"),
        "/target/venv",
    )

    assert "PYTHONPATH" not in result
    assert "PYTHONHOME" not in result
    assert result["PYTHONNOUSERSITE"] == "1"
    assert result["VIRTUAL_ENV"] == "/target/venv"
    assert result["LD_LIBRARY_PATH"].split(os.pathsep) == [
        "/target/nvjitlink",
        "/target/cusparse",
        "/system/cuda",
    ]
    assert result["PATH"].split(os.pathsep)[0] == str(Path("/target/venv") / "bin")


def test_parse_ldd_nvjitlink_resolution() -> None:
    text = "libnvJitLink.so.12 => /target/nvidia/nvjitlink/lib/libnvJitLink.so.12 (0x00007f00)"

    assert parse_ldd_nvjitlink_resolution(text) == (
        "/target/nvidia/nvjitlink/lib/libnvJitLink.so.12"
    )
    assert parse_ldd_nvjitlink_resolution("not found") is None


def test_causal_role_classification_blocks_vllm_after_torch() -> None:
    result = classify_causal_roles(
        (
            "torch_family_runtime",
            "vllm_module",
            "vllm_native_extension",
        ),
        "FAILED",
    )

    assert result == {
        "observed": ("torch_family_runtime",),
        "blocked": ("vllm_module", "vllm_native_extension"),
    }


def test_v5_binds_target_loader_and_process_isolation(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V5_VERIFIER_PATH)
    source = _notebook_source(notebook)

    assert 'environment.pop("PYTHONPATH", None)' in source
    assert 'environment.pop("PYTHONHOME", None)' in source
    assert 'environment["PYTHONNOUSERSITE"] = "1"' in source
    assert '"TARGET_NVIDIA_LIBRARIES_PREPENDED"' in source
    assert "02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f" in source
    assert "6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7" in source
    assert '"canonical_nvjitlink_resolution"' in source
    assert '"canonical_cusparse_direct_load"' in source
    assert '"target_process_environment"' in source


def test_v5_blocks_vllm_on_torch_and_prohibits_model_loading(repo_root: Path) -> None:
    notebook = _load_json_object(repo_root / V5_VERIFIER_PATH)
    source = _notebook_source(notebook)

    vllm_call = source.rindex('"vllm_module"')
    torch_dependency = source.rfind('"torch_family_runtime"', 0, vllm_call)
    assert torch_dependency >= 0
    assert '"vllm_native_extension"' in source
    assert '"BLOCKED_BY_UPSTREAM_FAILURE"' in source

    prohibited = (
        "from_pretrained(",
        "AutoModel",
        "AutoTokenizer",
        "LLM(",
        ".generate(",
    )
    assert not any(fragment in source for fragment in prohibited)
    assert '"model_requests_performed=0"' in source
    assert '"qualification_claimed=false"' in source
