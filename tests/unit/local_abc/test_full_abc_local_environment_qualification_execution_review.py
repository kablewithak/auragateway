from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_review as execution_review,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution_review import (
    NEXT_GATE,
    REVIEW_PATH,
    SOURCE_MAIN_MERGE_COMMIT,
    FullABCLocalEnvironmentQualificationExecutionReview,
    QualificationDatasetBoundary,
    QualificationExecutionReviewSafetyEnvelope,
    QualificationProbeBudget,
    QualificationRuntimeEvidenceContract,
    build_default_review,
    load_full_abc_local_environment_qualification_execution_review,
    validate_repository_review_package,
    write_default_review,
)


def test_default_review_is_deterministic() -> None:
    first = build_default_review()
    second = build_default_review()
    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


def test_default_review_authorizes_implementation_only() -> None:
    review = build_default_review()
    assert review.decision == "APPROVED_FOR_QUALIFICATION_EXECUTION_IMPLEMENTATION"
    assert review.next_gate == NEXT_GATE
    assert review.execution_controls.implementation_may_create_notebook is True
    assert review.execution_controls.implementation_may_start_kaggle is False
    assert review.execution_controls.implementation_may_enable_gpu is False
    assert review.execution_controls.implementation_may_start_workers is False
    assert review.execution_controls.implementation_may_invoke_model is False


def test_probe_budget_is_bounded_and_synthetic_only() -> None:
    budget = build_default_review().probe_budget
    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_workers == 2
    assert budget.maximum_model_requests == 8
    assert budget.maximum_output_tokens_per_request == 32
    assert len(budget.synthetic_probe_ids) == 6
    assert budget.benchmark_trajectory_requests_permitted == 0
    assert budget.benchmark_episode_payloads_permitted is False
    assert budget.customer_payloads_permitted is False
    assert budget.hidden_retries_permitted is False


def test_probe_id_drift_is_rejected() -> None:
    with pytest.raises(ValidationError):
        QualificationProbeBudget(synthetic_probe_ids=("unexpected-probe",))


def test_dataset_boundary_is_offline_and_zero_spend() -> None:
    boundary = QualificationDatasetBoundary()
    assert boundary.network_access_permitted is False
    assert boundary.credentials_permitted is False
    assert boundary.customer_data_permitted is False
    assert boundary.hosted_provider_calls_permitted is False
    assert boundary.local_model_artifacts_required is True
    assert boundary.local_vllm_wheel_required is True
    assert boundary.network_package_install_permitted is False
    assert boundary.raw_prompt_logging_permitted is False
    assert boundary.external_spend == 0


def test_runtime_evidence_requires_complete_same_session_bundle() -> None:
    evidence = build_default_review().runtime_evidence
    assert len(evidence.required_paths) == 8
    assert evidence.same_runtime_session_required is True
    assert evidence.partial_bundle_qualification_permitted is False
    assert evidence.missing_metric_state == "UNAVAILABLE_NOT_ZERO"
    assert evidence.zero_fill_for_missing_metrics_permitted is False
    assert evidence.latency_only_cache_inference_permitted is False
    assert evidence.evidence_written_only_after_validation is True


def test_runtime_evidence_path_drift_is_rejected() -> None:
    with pytest.raises(ValidationError):
        QualificationRuntimeEvidenceContract(
            required_paths=("wrong.json",),
            missing_metric_state="UNAVAILABLE_NOT_ZERO",
        )


def test_review_safety_envelope_fails_closed() -> None:
    safety = QualificationExecutionReviewSafetyEnvelope()
    assert safety.execution_package_generated is False
    assert safety.notebook_created is False
    assert safety.kaggle_session_started is False
    assert safety.gpu_execution_authorized is False
    assert safety.worker_start_authorized is False
    assert safety.model_execution_performed is False
    assert safety.runtime_evidence_generated is False
    assert safety.environment_qualified is False
    assert safety.measured_execution_authorized is False
    assert safety.external_spend == 0


def test_environment_qualification_claim_is_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["safety"]["environment_qualified"] = True
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)


def test_kaggle_start_permission_is_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["execution_controls"]["implementation_may_start_kaggle"] = True
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)


def test_package_artifacts_are_exact_and_sorted() -> None:
    artifacts = build_default_review().package_artifacts
    identifiers = tuple(item.artifact_id for item in artifacts)
    assert identifiers == tuple(sorted(identifiers))
    assert len(artifacts) == 6
    assert all(item.execution_performed is False for item in artifacts)
    assert any(item.path.endswith(".ipynb") for item in artifacts)


def test_authority_bindings_are_exact_and_sorted() -> None:
    bindings = build_default_review().authority_bindings
    identifiers = tuple(item.binding_id for item in bindings)
    assert identifiers == tuple(sorted(identifiers))
    assert len(bindings) == 5
    assert all(len(item.git_blob_sha) == 40 for item in bindings)


def test_write_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "review.json"
    written = write_default_review(path)
    loaded = load_full_abc_local_environment_qualification_execution_review(path)
    assert written == loaded
    assert path.read_text(encoding="utf-8") == written.canonical_json()


def test_invalid_review_file_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "review.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_full_abc_local_environment_qualification_execution_review(path)


def test_review_constants_bind_pr_102_merge() -> None:
    assert SOURCE_MAIN_MERGE_COMMIT == "3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8"
    assert REVIEW_PATH.as_posix().endswith(
        "auragateway_full_abc_local_full_run_environment_qualification_execution_review_v1.json"
    )


def test_canonical_artifact_matches_builder() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    artifact = repo_root / REVIEW_PATH
    assert artifact.read_text(encoding="utf-8") == build_default_review().canonical_json()


def test_review_artifact_has_no_execution_claims() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    payload = json.loads((repo_root / REVIEW_PATH).read_text(encoding="utf-8"))
    assert payload["safety"]["environment_qualified"] is False
    assert payload["safety"]["measured_execution_authorized"] is False
    assert payload["probe_budget"]["benchmark_trajectory_requests_permitted"] == 0


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    paths = (
        repo_root / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_review.py",
        repo_root / "tests/unit/local_abc/"
        "test_full_abc_local_environment_qualification_execution_review.py",
    )
    failures = []
    for path in paths:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if len(line) > 100:
                failures.append(f"{path.as_posix()}:{line_number}:{len(line)}")
    assert failures == []


def test_ruff_version_is_0_15_21() -> None:
    result = subprocess.run(
        ["ruff", "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.stdout.strip() == "ruff 0.15.21"


def test_repository_package_matches_historical_merged_authorities() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if not (repo_root / ".git").exists():
        pytest.skip("full Git checkout required")
    summary = validate_repository_review_package(repo_root)
    assert summary["review_disposition"] == "HISTORICAL_CONTEXT_ONLY"
    assert summary["historical_revision"] == SOURCE_MAIN_MERGE_COMMIT
    assert summary["historical_authorities_verified"] == 5
    assert summary["maximum_model_requests"] == 8
    assert summary["benchmark_trajectory_requests_permitted"] == 0
    assert summary["implementation_may_start_kaggle"] is False
    assert summary["environment_qualified"] is False
    assert summary["measured_execution_authorized"] is False


def test_historical_authority_drift_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if not (repo_root / ".git").exists():
        pytest.skip("full Git checkout required")

    original = execution_review._git_blob_sha_at_revision

    def drift_qualification_request(
        root: Path,
        relative_path: Path,
        revision: str,
    ) -> str:
        if relative_path == execution_review._QUALIFICATION_REQUEST_PATH:
            return "0" * 40
        return original(root, relative_path, revision)

    monkeypatch.setattr(
        execution_review,
        "_git_blob_sha_at_revision",
        drift_qualification_request,
    )

    with pytest.raises(
        execution_review.FullABCLocalEnvironmentQualificationExecutionReviewError
    ) as exc_info:
        validate_repository_review_package(repo_root)

    assert exc_info.value.error_code == "QUALIFICATION_EXECUTION_HISTORICAL_AUTHORITY_DRIFT"


def test_duplicate_authority_bindings_are_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["authority_bindings"].append(payload["authority_bindings"][0])
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)


def test_duplicate_package_artifacts_are_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["package_artifacts"].append(payload["package_artifacts"][0])
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)


def test_package_path_traversal_is_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["package_artifacts"][0]["path"] = "../unsafe.py"
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)


def test_nonzero_external_spend_is_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["dataset_boundary"]["external_spend"] = 1
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)


def test_benchmark_trajectory_request_permission_is_rejected() -> None:
    payload = build_default_review().model_dump(mode="json")
    payload["probe_budget"]["benchmark_trajectory_requests_permitted"] = 1
    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationExecutionReview.model_validate(payload)
