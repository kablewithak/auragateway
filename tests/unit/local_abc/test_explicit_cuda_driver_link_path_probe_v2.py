"""Tests for the explicit CUDA driver link-path probe V2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import auragateway.local_abc.explicit_cuda_driver_link_path_probe_v2 as subject


def _classification_payload() -> dict[str, object]:
    return {
        "status": ("P0_P2_PLATFORM_FAILURE_CLASSIFICATION_V1_VALID"),
        "launcher_saved_version_id": 339111200,
        "first_divergence": "cuda_driver_link",
        "terminal_decision": ("CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"),
        "refined_classification": (
            "CUDA_DRIVER_LIBRARY_PRESENT_RUNTIME_VISIBLE_BUT_DEFAULT_LINKER_SEARCH_PATH_UNBOUND"
        ),
        "next_gate": ("design_and_validate_explicit_cuda_driver_link_path_probe_v2"),
        "unchanged_replay_authorized": False,
        "p0": {
            "real_driver_link_path": ("/usr/local/nvidia/lib64/libcuda.so"),
            "torch_cuda_available": True,
            "ld_library_path_contains_real_driver_directory": (True),
            "library_path": ("/usr/local/cuda/lib64/stubs"),
        },
        "p1": {
            "failure_stage": "cuda_driver_link",
            "explicit_driver_link_directory_present": False,
            "syntax_compile_succeeded": True,
            "link_returncode": 1,
            "linker_error": ("/usr/bin/ld: cannot find -lcuda: No such file or directory"),
            "selected_link_libraries": [],
        },
        "recommended_probe_v2": {
            "status": ("DESIGN_RECOMMENDATION_NOT_EXECUTED"),
            "real_driver_directory": ("/usr/local/nvidia/lib64"),
            "required_link_flags": list(subject.REQUIRED_LINK_FLAGS),
            "prohibit_cuda_toolkit_stub": True,
            "require_selected_link_library_real_driver_mount": (True),
            "require_ldd_resolution_to_real_driver_mount": (True),
            "require_cu_init_zero": True,
            "global_environment_mutation_permitted": False,
            "gpu_replay_authorized": False,
        },
    }


def _fixture_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    path = repo_root / subject.CLASSIFICATION_RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _classification_payload(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return repo_root


def test_build_is_deterministic(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.build_generated_probe(repo_root)
    second = subject.build_generated_probe(repo_root)

    assert first.notebook_bytes == second.notebook_bytes
    assert first.record == second.record
    assert first.request == second.request
    assert first.review == second.review


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.notebook.sha256
    assert generated.safety.model_requests == 0


def test_program_binds_real_driver_and_rejects_stub() -> None:
    source = subject.KAGGLE_PROGRAM

    for flag in subject.REQUIRED_LINK_FLAGS:
        assert flag in source

    assert subject.REAL_DRIVER_LINK_PATH in source
    assert subject.CUDA_STUB_DIRECTORY in source
    assert "-L/usr/local/cuda/lib64/stubs" not in source
    assert 'os.environ["LIBRARY_PATH"] =' not in source
    assert 'os.environ["LD_LIBRARY_PATH"] =' not in source
    assert "import triton" not in source
    assert "pip install" not in source


def test_notebook_has_unexecuted_two_cell_contract(
    tmp_path: Path,
) -> None:
    generated = subject.build_generated_probe(_fixture_repo(tmp_path))
    notebook = json.loads(generated.notebook_bytes)

    assert len(notebook["cells"]) == 2

    code_cell = notebook["cells"][1]
    assert code_cell["execution_count"] is None
    assert code_cell["outputs"] == []

    metadata = notebook["metadata"]["auragateway"]
    assert metadata["attached_inputs_required"] == 0
    assert metadata["p2_permitted"] is False


def test_review_prohibits_environment_mutation(
    tmp_path: Path,
) -> None:
    review = subject.build_generated_probe(_fixture_repo(tmp_path)).review

    assert "global_library_path_mutation" in review.prohibited_techniques
    assert "global_ld_library_path_mutation" in review.prohibited_techniques
    assert "cuda_toolkit_stub_linking" in review.prohibited_techniques
    assert "triton_execution" in review.prohibited_techniques


def test_classification_authority_drift_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.CLASSIFICATION_RECORD_PATH

    payload = _classification_payload()
    payload["first_divergence"] = "dynamic_loader_resolution"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        subject.ExplicitDriverLinkProbeError,
        match="classification authority drifted",
    ):
        subject.build_generated_probe(repo_root)


def test_transient_authorization_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(
        subject.ExplicitDriverLinkProbeError,
        match="authorization must remain absent",
    ):
        subject.build_generated_probe(repo_root)


def test_nested_authority_projection_ignores_unrelated_fields(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.CLASSIFICATION_RECORD_PATH
    payload = _classification_payload()

    p0 = payload["p0"]
    assert isinstance(p0, dict)
    p0["driver_version"] = "580.159.04"
    p0["base_torch_version"] = "2.10.0+cu128"

    p1 = payload["p1"]
    assert isinstance(p1, dict)
    p1["compiler_path"] = "/usr/bin/cc"
    p1["link_command"] = [
        "/usr/bin/cc",
        "cuda_driver_link_probe.o",
        "-Wl,-t",
        "-lcuda",
    ]

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    generated = subject.build_generated_probe(repo_root)

    assert generated.record.status == ("EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2_VALID")
