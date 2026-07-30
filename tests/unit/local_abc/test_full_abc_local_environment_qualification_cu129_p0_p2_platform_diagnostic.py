from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

import pytest
from pydantic import ValidationError

import auragateway.local_abc.full_abc_local_environment_qualification_cu129_p0_p2_platform_diagnostic as diagnostic  # noqa: E501

P1Probe = Callable[[], tuple[dict[str, object], bool]]


class P1Case(TypedDict, total=False):
    syntax_returncode: int
    link_returncode: int
    ldd_resolves: bool
    execution_returncode: int


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def _request_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "request_id": "auragateway-cu129-p0-p2-platform-diagnostic-request-v1",
        "source_main_merge_commit": diagnostic.SOURCE_MAIN_MERGE_COMMIT,
        "option_c_decision_record_path": diagnostic.DECISION_RECORD_PATH.as_posix(),
        "mode": "KAGGLE_DIAGNOSTIC",
        "notebook_name": diagnostic.NOTEBOOK_NAME,
        "failed_notebook_name": diagnostic.FAILED_NOTEBOOK_NAME,
        "runtime_output_directory": diagnostic.RUNTIME_OUTPUT_DIRECTORY,
        "evidence_zip_name": diagnostic.EVIDENCE_ZIP_NAME,
        "maximum_sessions": 1,
        "stop_on_first_failure": True,
        "network_access_permitted": False,
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_load_permitted": False,
        "worker_start_permitted": False,
        "model_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "hidden_retries_permitted": False,
        "filesystem_mutation_scope": "KAGGLE_WORKING_DIRECTORY_ONLY",
        "system_library_copy_permitted": False,
        "libcuda_symlink_permitted": False,
        "external_spend": 0,
        "probes": [
            {
                "probe_id": "P0",
                "name": "KAGGLE_IMAGE_AND_RUNTIME_IDENTITY",
                "pass_decision": "PLATFORM_IDENTITY_CAPTURED",
                "fail_decision": "DIAGNOSTIC_INVALID",
                "permitted_fail_decisions": ["DIAGNOSTIC_INVALID"],
            },
            {
                "probe_id": "P1",
                "name": "CUDA_DRIVER_LINKER_VISIBILITY",
                "pass_decision": "CUDA_DRIVER_LINKER_CONTRACT_PASSED",
                "fail_decision": "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
                "permitted_fail_decisions": [
                    "DIAGNOSTIC_INVALID",
                    "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
                    "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED",
                ],
            },
            {
                "probe_id": "P2",
                "name": "MINIMAL_TRITON_KERNEL",
                "pass_decision": "CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
                "fail_decision": "CURRENT_STACK_TRITON_INCOMPATIBLE",
                "permitted_fail_decisions": ["CURRENT_STACK_TRITON_INCOMPATIBLE"],
            },
        ],
        "required_outputs": list(diagnostic.REQUIRED_OUTPUTS),
        "next_gate_on_pass": "implement_explicit_triton_attention_backend",
        "next_gate_on_failure": "preserve_evidence_and_classify_platform_failure",
    }


def _implementation_payload() -> dict[str, object]:
    return {
        "schema_version": "1.1.0",
        "record_id": ("auragateway-cu129-p0-p2-platform-diagnostic-implementation-v1"),
        "source_main_merge_commit": diagnostic.SOURCE_MAIN_MERGE_COMMIT,
        "request_path": diagnostic.REQUEST_PATH.as_posix(),
        "notebook_path": diagnostic.NOTEBOOK_PATH.as_posix(),
        "notebook_name": diagnostic.NOTEBOOK_NAME,
        "notebook_sha256": diagnostic.notebook_sha256(),
        "notebook_cell_count": 2,
        "output_cells_present": False,
        "execution_counts_present": False,
        "runtime_output_directory": diagnostic.RUNTIME_OUTPUT_DIRECTORY,
        "evidence_zip_name": diagnostic.EVIDENCE_ZIP_NAME,
        "required_outputs": list(diagnostic.REQUIRED_OUTPUTS),
        "safety": {
            "authorization_issued": False,
            "kaggle_execution_performed": False,
            "gpu_execution_performed": False,
            "model_loaded": False,
            "worker_started": False,
            "model_requests_performed": 0,
            "benchmark_trajectory_requests_performed": 0,
            "runtime_worker_source_changed": False,
            "credentials_used": False,
            "customer_data_used": False,
            "external_spend": 0,
        },
        "remediation": {
            "remediation_id": ("auragateway-cu129-p1-probe-taxonomy-remediation-v1"),
            "invalid_kaggle_version": "338921762",
            "invalid_platform_evidence_sha256": (diagnostic.INVALID_PLATFORM_EVIDENCE_SHA256),
            "confirmed_defect": "literal_backslash_n_in_generated_c_probe",
            "corrected_source_sha256": diagnostic.P1_C_SOURCE_SHA256,
            "exact_source_bytes_validated": True,
            "staged_failure_taxonomy_validated": True,
            "unchanged_replay_authorized": False,
            "corrected_replay_authorized_after_merge": True,
        },
        "implementation_status": "REMEDIATED_NOT_EXECUTED",
        "next_gate": ("review_and_materialize_corrected_p0_p2_platform_diagnostic"),
        "non_claims": [f"non-claim-{index}" for index in range(12)],
    }


def _write_repository_fixture(root: Path, *, backend_mutated: bool = False) -> None:
    decision = {
        "decision": "APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC",
        "next_gate": "implement_p0_p2_platform_diagnostic_assets",
        "platform_diagnostic": {},
        "selected_strategy": {},
    }
    _write_json(root / diagnostic.DECISION_RECORD_PATH, decision)
    _write_json(root / diagnostic.REQUEST_PATH, _request_payload())
    _write_json(root / diagnostic.IMPLEMENTATION_RECORD_PATH, _implementation_payload())
    command = ["python", "-m", "vllm"]
    if backend_mutated:
        command.extend(["--attention-backend", "TRITON_ATTN"])
    _write_json(
        root / diagnostic.WORKER_PLAN_PATH,
        {
            "workers": [
                {"command_argv": command},
                {"command_argv": command},
            ]
        },
    )
    diagnostic.write_notebook(root / diagnostic.NOTEBOOK_PATH)


def _kaggle_program_namespace() -> dict[str, object]:
    program, separator, tail = diagnostic.KAGGLE_PROGRAM.rpartition("\n\nmain()")
    assert separator
    assert not tail
    namespace: dict[str, object] = {"__name__": "__p1_unit_test__"}
    exec(compile(program, "p1_diagnostic_program", "exec"), namespace)
    return namespace


def _run_p1_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    syntax_returncode: int = 0,
    link_returncode: int = 0,
    ldd_resolves: bool = True,
    execution_returncode: int = 0,
) -> tuple[dict[str, object], bool]:
    namespace = _kaggle_program_namespace()
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    namespace["OUTPUT_DIRECTORY"] = output_directory

    shutil_module = namespace["shutil"]
    monkeypatch.setattr(
        shutil_module,
        "which",
        lambda name: f"/usr/bin/{name}",
    )

    def fake_run_command(
        argv: list[str],
        *,
        timeout: int = 120,
        env: dict[str, str] | None = None,
    ) -> dict[str, object]:
        del timeout, env
        result = {
            "argv": argv,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        }
        if "-c" in argv:
            result["returncode"] = syntax_returncode
            if syntax_returncode == 0:
                Path(argv[argv.index("-o") + 1]).write_bytes(b"object")
            return result
        if "-lcuda" in argv:
            result["returncode"] = link_returncode
            if link_returncode == 0:
                Path(argv[argv.index("-o") + 1]).write_bytes(b"executable")
                result["stderr"] = "/usr/local/nvidia/lib64/libcuda.so"
            return result
        if argv[0].endswith("/ldd"):
            result["stdout"] = (
                "libcuda.so.1 => /usr/local/nvidia/lib64/libcuda.so.1 (0x0000)"
                if ldd_resolves
                else "libcuda.so.1 => not found"
            )
            return result
        result["returncode"] = execution_returncode
        return result

    namespace["run_command"] = fake_run_command
    probe = cast(P1Probe, namespace["p1_cuda_driver_linker"])
    return probe()


def test_request_accepts_exact_fixed_contract() -> None:
    request = diagnostic.PlatformDiagnosticRequest.model_validate(_request_payload())

    assert tuple(item.probe_id for item in request.probes) == ("P0", "P1", "P2")
    assert request.required_outputs == diagnostic.REQUIRED_OUTPUTS
    assert request.model_requests_permitted == 0
    assert request.worker_start_permitted is False


def test_request_rejects_session_budget_drift() -> None:
    payload = _request_payload()
    payload["maximum_sessions"] = 2

    with pytest.raises(ValidationError):
        diagnostic.PlatformDiagnosticRequest.model_validate(payload)


def test_notebook_generation_is_deterministic_and_output_free(tmp_path: Path) -> None:
    path = tmp_path / "diagnostic.ipynb"

    diagnostic.write_notebook(path)
    first = path.read_bytes()
    diagnostic.write_notebook(path)
    second = path.read_bytes()
    validation = diagnostic.validate_notebook(path)

    assert first == second == diagnostic.notebook_bytes()
    assert validation["notebook_sha256"] == diagnostic.notebook_sha256()
    assert validation["cell_count"] == 2
    assert validation["output_cells_present"] is False


def test_notebook_program_preserves_execution_boundary() -> None:
    required = (
        "BUILD_DATE",
        "GIT_COMMIT",
        "nvidia-smi",
        "-lcuda",
        "triton.jit",
        "--no-index",
        "--require-hashes",
    )
    prohibited = (
        "Qwen/Qwen",
        "vllm.entrypoints.openai.api_server",
        "/v1/chat/completions",
        "--attention-backend",
        "urllib.request",
    )

    assert all(marker in diagnostic.KAGGLE_PROGRAM for marker in required)
    assert all(marker not in diagnostic.KAGGLE_PROGRAM for marker in prohibited)
    assert len(diagnostic.NOTEBOOK_NAME) <= 50
    assert len(diagnostic.FAILED_NOTEBOOK_NAME) <= 50


def test_p1_probe_source_bytes_are_exact_lf_terminated_c() -> None:
    source = diagnostic.p1_probe_source_bytes()

    assert source == diagnostic.P1_C_SOURCE_EXPECTED
    assert source.count(b"\n") == 2
    assert b"\\n" not in source
    assert diagnostic.P1_C_SOURCE_SHA256 == (
        "263bf5cec15f224add6e80041cfb026725df52135623224c22f79f901bd9b2f2"
    )


def test_p1_probe_source_compiles_as_c11_when_cc_is_available(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("cc is unavailable")

    source = tmp_path / "probe.c"
    object_file = tmp_path / "probe.o"
    source.write_bytes(diagnostic.p1_probe_source_bytes())

    completed = subprocess.run(
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
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0, completed.stderr
    assert object_file.is_file()


def test_p1_failure_taxonomy_separates_harness_and_platform_failures() -> None:
    program = diagnostic.KAGGLE_PROGRAM

    assert '"syntax_compile_failed": "DIAGNOSTIC_INVALID"' in program
    assert '"link_failed": "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"' in program
    assert '"loader_resolution_failed": "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"' in program
    assert "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED" in program
    assert "terminal_decision = str(p1_decision)" in program


def test_request_rejects_p1_failure_taxonomy_drift() -> None:
    payload = _request_payload()
    probes = payload["probes"]
    assert isinstance(probes, list)
    p1 = probes[1]
    assert isinstance(p1, dict)
    p1["permitted_fail_decisions"] = ["CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED"]

    with pytest.raises(ValidationError, match="failure taxonomy"):
        diagnostic.PlatformDiagnosticRequest.model_validate(payload)


@pytest.mark.parametrize(
    (
        "case",
        "expected_decision",
        "expected_stage",
    ),
    [
        (
            {"syntax_returncode": 1},
            "DIAGNOSTIC_INVALID",
            "syntax_compilation",
        ),
        (
            {"link_returncode": 1},
            "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
            "cuda_driver_link",
        ),
        (
            {"ldd_resolves": False},
            "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
            "dynamic_loader_resolution",
        ),
        (
            {"execution_returncode": 1},
            "CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED",
            "driver_initialization",
        ),
        (
            {},
            "CUDA_DRIVER_LINKER_CONTRACT_PASSED",
            "none",
        ),
    ],
)
def test_p1_stage_taxonomy_is_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: P1Case,
    expected_decision: str,
    expected_stage: str,
) -> None:
    report, passed = _run_p1_case(
        tmp_path,
        monkeypatch,
        syntax_returncode=case.get("syntax_returncode", 0),
        link_returncode=case.get("link_returncode", 0),
        ldd_resolves=case.get("ldd_resolves", True),
        execution_returncode=case.get("execution_returncode", 0),
    )

    assert report["decision"] == expected_decision
    assert report["failure_stage"] == expected_stage
    assert passed is (expected_decision == "CUDA_DRIVER_LINKER_CONTRACT_PASSED")
    budgets = report["budgets"]
    assert isinstance(budgets, dict)
    assert budgets["hidden_retries"] == 0
    source_contract = report["source_contract"]
    assert isinstance(source_contract, dict)
    assert source_contract["exact_bytes"] is True
    assert source_contract["literal_backslash_n_present"] is False


def test_notebook_validation_rejects_identity_drift(tmp_path: Path) -> None:
    path = tmp_path / "diagnostic.ipynb"
    diagnostic.write_notebook(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cells"][0]["source"].append("tampered\n")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        diagnostic.P0P2PlatformDiagnosticError,
        match="identity drifted",
    ):
        diagnostic.validate_notebook(path)


def test_repository_package_validates_without_runtime_mutation(tmp_path: Path) -> None:
    _write_repository_fixture(tmp_path)

    summary = diagnostic.validate_repository_package(tmp_path)

    assert summary["status"] == "P0_P2_PLATFORM_DIAGNOSTIC_IMPLEMENTATION_VALID"
    assert summary["probe_count"] == 3
    assert summary["required_output_count"] == 6
    assert summary["runtime_worker_source_changed"] is False
    assert summary["authorization_issued"] is False
    assert summary["kaggle_execution_performed"] is False


def test_repository_package_rejects_mixed_backend_implementation(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path, backend_mutated=True)

    with pytest.raises(
        diagnostic.P0P2PlatformDiagnosticError,
        match="runtime backend mutation was mixed",
    ):
        diagnostic.validate_repository_package(tmp_path)


def test_implementation_record_rejects_notebook_hash_drift() -> None:
    payload = _implementation_payload()
    payload["notebook_sha256"] = "f" * 63

    with pytest.raises(ValidationError):
        diagnostic.PlatformDiagnosticImplementationRecord.model_validate(payload)
