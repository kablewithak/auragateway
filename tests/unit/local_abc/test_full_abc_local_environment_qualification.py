"""Tests for static full-run environment-qualification tooling."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_environment_qualification import (
    _validate_review_boundary,
    build_implementation_plan,
    build_qualification_request,
    build_static_bundle,
    build_worker_startup_plan,
    validate_repository_authorities,
    verify_static_bundle,
    write_static_bundle,
)
from auragateway.local_abc.full_abc_local_environment_qualification_contracts import (
    _REQUIRED_METRIC_SEMANTICS,
    _REQUIRED_RESET_STEPS,
    _REQUIRED_RUNTIME_LOCK_FIELDS,
    _REQUIRED_STOP_CONDITIONS,
    _RUNTIME_EVIDENCE_PATHS,
    EXPECTED_RUFF_VERSION,
    IMPLEMENTATION_PLAN_PATH,
    NEXT_GATE,
    QUALIFICATION_REQUEST_PATH,
    REVIEW_GIT_BLOB_SHA,
    REVIEW_PATH,
    REVIEW_SOURCE_GIT_BLOB_SHA,
    SOURCE_MAIN_MERGE_COMMIT,
    WORKER_STARTUP_PLAN_PATH,
    EnvironmentQualificationImplementationPlan,
    FullABCLocalEnvironmentQualificationImplementationError,
    MetricAvailabilityState,
    QualificationRequest,
    WorkerStartupPlan,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATHS = (
    Path("src/auragateway/local_abc/full_abc_local_environment_qualification_contracts.py"),
    Path("src/auragateway/local_abc/full_abc_local_environment_qualification.py"),
    Path("tests/unit/local_abc/test_full_abc_local_environment_qualification.py"),
)


def _review_payload() -> dict[str, object]:
    return {
        "review_id": ("auragateway-full-abc-local-full-run-environment-qualification-review-v1"),
        "source_main_merge_commit": "1bbc11e72880bc5b6fa88da3ba8b180420c9abf5",
        "decision": "APPROVED_FOR_QUALIFICATION_TOOLING_IMPLEMENTATION",
        "next_gate": "full_abc_local_full_run_environment_qualification_implementation",
        "safety": {
            "gpu_execution_authorized": False,
            "gpu_execution_performed": False,
            "worker_start_authorized": False,
            "worker_started": False,
            "model_execution_performed": False,
            "credential_accessed": False,
            "provider_call_performed": False,
            "customer_data_used": False,
            "measured_execution_authorized": False,
            "claim_generation_permitted": False,
            "external_spend": 0,
        },
        "runtime_identity": {
            "status": "HISTORICAL_BASELINE_REQUIRES_FRESH_CAPTURE",
            "environment": "kaggle_t4_x2",
            "execution_backend": "local_vllm",
            "gpu_count": 2,
            "gpu_model": "Tesla T4",
            "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
            "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "tokenizer_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "fresh_values_must_share_one_runtime_session": True,
            "inherited_versions_permitted": False,
        },
        "metric_capability": {
            "missing_metric_state": "UNAVAILABLE_NOT_ZERO",
            "zero_fill_for_missing_metrics_permitted": False,
        },
    }


def test_review_boundary_accepts_exact_authority() -> None:
    _validate_review_boundary(_review_payload(), Path("review.json"))


def test_review_boundary_rejects_execution_authority() -> None:
    payload = _review_payload()
    safety = dict(cast(dict[str, object], payload["safety"]))
    safety["gpu_execution_authorized"] = True
    payload["safety"] = safety
    with pytest.raises(
        FullABCLocalEnvironmentQualificationImplementationError,
        match="fails closed",
    ):
        _validate_review_boundary(payload, Path("review.json"))


def test_review_boundary_rejects_metric_zero_fill() -> None:
    payload = _review_payload()
    capability = dict(cast(dict[str, object], payload["metric_capability"]))
    capability["zero_fill_for_missing_metrics_permitted"] = True
    payload["metric_capability"] = capability
    with pytest.raises(
        FullABCLocalEnvironmentQualificationImplementationError,
        match="zero-filled",
    ):
        _validate_review_boundary(payload, Path("review.json"))


def test_static_bundle_builds_only_two_assets() -> None:
    bundle = build_static_bundle()
    assert bundle.qualification_request.planned_trajectory_count == 342
    assert len(bundle.worker_startup_plan.workers) == 2
    assert bundle.qualification_request.next_gate == NEXT_GATE


def test_qualification_request_preserves_fresh_capture_boundary() -> None:
    request = build_qualification_request()
    assert request.fresh_runtime_session_required is True
    assert request.historical_authorization_reusable is False
    assert request.developer_dependency_lock_reusable_as_runtime_lock is False
    assert request.required_runtime_lock_fields == _REQUIRED_RUNTIME_LOCK_FIELDS


def test_runtime_evidence_is_deferred_and_unpopulated() -> None:
    request = build_qualification_request()
    assert tuple(Path(item.path) for item in request.runtime_evidence_requirements) == (
        _RUNTIME_EVIDENCE_PATHS
    )
    assert all(item.generated is False for item in request.runtime_evidence_requirements)
    assert all(
        item.requires_fresh_runtime_session is True
        for item in request.runtime_evidence_requirements
    )


def test_metric_requirements_never_zero_fill_missing_values() -> None:
    request = build_qualification_request()
    assert tuple(item.semantic for item in request.metric_requirements) == (
        _REQUIRED_METRIC_SEMANTICS
    )
    assert all(
        item.missing_metric_state is MetricAvailabilityState.UNAVAILABLE_NOT_ZERO
        for item in request.metric_requirements
    )
    assert all(item.zero_fill_permitted is False for item in request.metric_requirements)


def test_reset_and_stop_contracts_are_exact() -> None:
    request = build_qualification_request()
    assert request.required_reset_steps == _REQUIRED_RESET_STEPS
    assert request.stop_conditions == _REQUIRED_STOP_CONDITIONS


def test_static_safety_envelope_blocks_every_execution_path() -> None:
    safety = build_qualification_request().safety
    assert safety.runtime_evidence_generated is False
    assert safety.kaggle_session_started is False
    assert safety.dataset_attached is False
    assert safety.package_installation_performed is False
    assert safety.notebook_created is False
    assert safety.gpu_execution_authorized is False
    assert safety.worker_start_authorized is False
    assert safety.model_execution_performed is False
    assert safety.credential_accessed is False
    assert safety.provider_call_performed is False
    assert safety.external_spend == 0
    assert safety.measured_execution_authorized is False


def test_worker_startup_plan_preserves_two_worker_topology() -> None:
    plan = build_worker_startup_plan()
    assert tuple(worker.worker_id for worker in plan.workers) == ("worker_1", "worker_2")
    assert tuple(worker.gpu_index for worker in plan.workers) == (0, 1)
    assert tuple(worker.port for worker in plan.workers) == (8001, 8002)
    assert all(worker.host == "127.0.0.1" for worker in plan.workers)


def test_worker_startup_plan_is_offline_and_non_shell() -> None:
    plan = build_worker_startup_plan()
    for worker in plan.workers:
        environment = {item.name: item.value for item in worker.environment}
        assert environment["HF_HUB_OFFLINE"] == "1"
        assert worker.shell_execution_permitted is False
        assert worker.launch_authorized is False
        assert "--enable-prefix-caching" in worker.command_argv
        assert "--disable-log-requests" in worker.command_argv


def test_worker_commands_contain_no_provider_or_install_actions() -> None:
    rendered = " ".join(
        argument
        for worker in build_worker_startup_plan().workers
        for argument in worker.command_argv
    ).lower()
    for prohibited in ("groq", "openrouter", "--api-key", "curl", "wget", "pip"):
        assert prohibited not in rendered


def test_worker_command_hashes_are_distinct_and_stable() -> None:
    first = build_worker_startup_plan()
    second = build_worker_startup_plan()
    first_hashes = tuple(worker.command_sha256 for worker in first.workers)
    second_hashes = tuple(worker.command_sha256 for worker in second.workers)
    assert first_hashes == second_hashes
    assert len(set(first_hashes)) == 2


def test_worker_port_mutation_fails_validation() -> None:
    plan = build_worker_startup_plan()
    payload = plan.model_dump(mode="json")
    payload["workers"][0]["port"] = 8002
    with pytest.raises(ValidationError):
        WorkerStartupPlan.model_validate(payload)


def test_metric_zero_fill_mutation_fails_validation() -> None:
    request = build_qualification_request()
    payload = request.model_dump(mode="json")
    payload["metric_requirements"][0]["zero_fill_permitted"] = True
    with pytest.raises(ValidationError):
        QualificationRequest.model_validate(payload)


def test_implementation_plan_has_exact_static_and_deferred_scope() -> None:
    plan = build_implementation_plan()
    assert plan.generated_static_assets == (
        QUALIFICATION_REQUEST_PATH.as_posix(),
        WORKER_STARTUP_PLAN_PATH.as_posix(),
    )
    assert plan.deferred_runtime_evidence == tuple(
        path.as_posix() for path in _RUNTIME_EVIDENCE_PATHS
    )
    assert plan.execution_enabled is False
    assert plan.qualification_claim_permitted is False


def test_write_and_verify_are_byte_deterministic(tmp_path: Path) -> None:
    write_static_bundle(tmp_path, validate_repository=False)
    first = {
        path: (tmp_path / path).read_bytes()
        for path in (QUALIFICATION_REQUEST_PATH, WORKER_STARTUP_PLAN_PATH)
    }
    write_static_bundle(tmp_path, validate_repository=False)
    second = {
        path: (tmp_path / path).read_bytes()
        for path in (QUALIFICATION_REQUEST_PATH, WORKER_STARTUP_PLAN_PATH)
    }
    assert first == second
    summary = verify_static_bundle(tmp_path, validate_repository=False)
    assert summary["static_asset_count"] == 2
    assert summary["runtime_evidence_generated"] is False


def test_generated_assets_are_canonical_json(tmp_path: Path) -> None:
    bundle = write_static_bundle(tmp_path, validate_repository=False)
    assert (tmp_path / QUALIFICATION_REQUEST_PATH).read_text(encoding="utf-8") == (
        bundle.qualification_request.canonical_json()
    )
    assert (tmp_path / WORKER_STARTUP_PLAN_PATH).read_text(encoding="utf-8") == (
        bundle.worker_startup_plan.canonical_json()
    )


def test_verify_rejects_static_asset_drift(tmp_path: Path) -> None:
    write_static_bundle(tmp_path, validate_repository=False)
    request_path = tmp_path / QUALIFICATION_REQUEST_PATH
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    payload["planned_trajectory_count"] = 341
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        FullABCLocalEnvironmentQualificationImplementationError,
        match="typed validation",
    ):
        verify_static_bundle(tmp_path, validate_repository=False)


def test_verify_rejects_runtime_evidence_generated_too_early(tmp_path: Path) -> None:
    write_static_bundle(tmp_path, validate_repository=False)
    runtime_path = tmp_path / _RUNTIME_EVIDENCE_PATHS[0]
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text("{}", encoding="utf-8")
    with pytest.raises(
        FullABCLocalEnvironmentQualificationImplementationError,
        match="before its authorized gate",
    ):
        verify_static_bundle(tmp_path, validate_repository=False)


def test_implementation_plan_round_trips() -> None:
    plan = build_implementation_plan()
    loaded = EnvironmentQualificationImplementationPlan.model_validate_json(plan.canonical_json())
    assert loaded == plan
    assert loaded.fingerprint() == plan.fingerprint()


def test_source_authority_constants_bind_pr_101() -> None:
    assert SOURCE_MAIN_MERGE_COMMIT == "7be3361fbbfcd14cebee96b4832fe4c800702f2e"
    assert REVIEW_GIT_BLOB_SHA == "344a24f18fc32a7b945ce761f6420947a53bcc24"
    assert REVIEW_SOURCE_GIT_BLOB_SHA == "fdd3022815bda785f171749a6e3a877f374aa635"
    assert REVIEW_PATH.as_posix().endswith("environment_qualification_review_v1.json")


def test_ruff_version_is_exact() -> None:
    assert importlib.metadata.version("ruff") == EXPECTED_RUFF_VERSION


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    failures: list[str] = []
    for relative_path in SOURCE_PATHS:
        path = REPO_ROOT / relative_path
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if len(line) > 100:
                failures.append(f"{relative_path.as_posix()}:{line_number}:{len(line)}")
    assert failures == []


def test_repository_bundle_and_authorities_match_when_git_checkout_available() -> None:
    if not (REPO_ROOT / ".git").exists() or not (REPO_ROOT / REVIEW_PATH).exists():
        pytest.skip("requires full AuraGateway Git checkout")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "merge-base",
            "--is-ancestor",
            SOURCE_MAIN_MERGE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        pytest.skip("PR 101 merge is not available in this checkout")
    authority = validate_repository_authorities(REPO_ROOT)
    assert authority["review_boundary_valid"] is True
    summary = verify_static_bundle(REPO_ROOT)
    assert summary["static_asset_count"] == 2
    assert summary["runtime_evidence_generated"] is False
    implementation_payload = json.loads(
        (REPO_ROOT / IMPLEMENTATION_PLAN_PATH).read_text(encoding="utf-8")
    )
    implementation = EnvironmentQualificationImplementationPlan.model_validate(
        implementation_payload
    )
    assert implementation == build_implementation_plan()
