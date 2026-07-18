from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_environment_qualification_review import (
    NEXT_GATE,
    REVIEW_ID,
    REVIEW_PATH,
    SOURCE_MAIN_MERGE_COMMIT,
    AuthorityDisposition,
    EnvironmentQualificationSafetyEnvelope,
    FullABCLocalEnvironmentQualificationReview,
    FullABCLocalEnvironmentQualificationReviewError,
    MetricCapabilityDecision,
    QualificationGenerationStage,
    QualificationStopDecision,
    RuntimeDependencyLockDecision,
    build_default_review,
    load_full_abc_local_environment_qualification_review,
    validate_repository_review_package,
    write_default_review,
)

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_REVIEW_SHA256 = "ac21b3d2f45ccd359d0291edcf450f66899dab7277cfa732177617d36d41a67b"


def load_review() -> FullABCLocalEnvironmentQualificationReview:
    return load_full_abc_local_environment_qualification_review(ROOT / REVIEW_PATH)


def test_review_has_expected_identity() -> None:
    review = load_review()

    assert review.review_id == REVIEW_ID
    assert review.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT
    assert review.fingerprint() == EXPECTED_REVIEW_SHA256
    assert review.next_gate == NEXT_GATE


def test_default_builder_reproduces_repository_artifact() -> None:
    assert build_default_review() == load_review()


def test_review_approves_tooling_without_lifecycle_promotion() -> None:
    review = load_review()

    assert review.decision == "APPROVED_FOR_QUALIFICATION_TOOLING_IMPLEMENTATION"
    assert review.lifecycle_before == "LOCALLY_VALIDATED"
    assert review.lifecycle_after == "LOCALLY_VALIDATED"


def test_historical_authorization_is_context_only() -> None:
    bindings = {binding.binding_id: binding for binding in load_review().authority_bindings}

    assert bindings["historical-measured-authorization"].disposition is (
        AuthorityDisposition.HISTORICAL_CONTEXT_ONLY
    )
    assert bindings["preflight-v3-manifest"].disposition is (AuthorityDisposition.CURRENT_AUTHORITY)


def test_authorities_use_git_blob_identity_not_json_reserialization() -> None:
    for binding in load_review().authority_bindings:
        assert len(binding.git_blob_sha) == 40


def test_runtime_identity_requires_fresh_same_session_capture() -> None:
    runtime = load_review().runtime_identity

    assert runtime.status == "HISTORICAL_BASELINE_REQUIRES_FRESH_CAPTURE"
    assert runtime.fresh_values_must_share_one_runtime_session is True
    assert runtime.inherited_versions_permitted is False


def test_runtime_identity_preserves_exact_local_baseline() -> None:
    runtime = load_review().runtime_identity

    assert runtime.environment == "kaggle_t4_x2"
    assert runtime.execution_backend == "local_vllm"
    assert runtime.gpu_count == 2
    assert runtime.gpu_model == "Tesla T4"
    assert runtime.compute_capability == "7.5"
    assert runtime.model_repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert runtime.model_revision == "7ae557604adf67be50417f59c2c2f167def9a775"


def test_worker_topology_is_exact_and_loopback_only() -> None:
    workers = load_review().runtime_identity.workers

    assert tuple(worker.worker_id for worker in workers) == ("worker_1", "worker_2")
    assert tuple(worker.gpu_index for worker in workers) == (0, 1)
    assert tuple(worker.port for worker in workers) == (8001, 8002)
    assert all(worker.loopback_only for worker in workers)


def test_dependency_lock_is_separate_from_developer_lock() -> None:
    decision = load_review().dependency_lock

    assert decision.developer_lock_path.endswith("developer_dependency_lock.json")
    assert decision.kaggle_runtime_lock_path.endswith("kaggle_runtime_dependency_lock.json")
    assert decision.developer_lock_reuse_permitted is False
    assert decision.historical_runtime_values_reuse_permitted is False


def test_runtime_lock_requires_cache_and_startup_identity() -> None:
    fields = set(load_review().dependency_lock.required_fields)

    assert {
        "automatic_prefix_cache_configuration",
        "attention_backend",
        "model_revision",
        "tokenizer_revision",
        "vllm_wheel_sha256",
        "worker_startup_command_sha256",
    } <= fields


def test_implementation_stage_artifacts_require_no_gpu_activity() -> None:
    artifacts = load_review().artifact_requirements
    implementation = tuple(
        artifact
        for artifact in artifacts
        if artifact.generation_stage is QualificationGenerationStage.IMPLEMENTATION
    )

    assert {artifact.artifact_id for artifact in implementation} == {
        "qualification-request",
        "worker-startup-plan",
    }
    assert all(not artifact.requires_gpu_activity for artifact in implementation)


def test_execution_stage_evidence_remains_not_generated() -> None:
    artifacts = load_review().artifact_requirements
    execution = tuple(
        artifact
        for artifact in artifacts
        if artifact.generation_stage is QualificationGenerationStage.QUALIFICATION_EXECUTION
    )

    assert execution
    assert all(artifact.current_state == "NOT_GENERATED" for artifact in execution)
    assert all(artifact.requires_gpu_activity for artifact in execution)


def test_missing_metrics_are_unavailable_not_zero() -> None:
    decision = load_review().metric_capability

    assert decision.missing_metric_state == "UNAVAILABLE_NOT_ZERO"
    assert decision.zero_fill_for_missing_metrics_permitted is False
    assert decision.latency_only_cache_inference_permitted is False
    assert decision.cache_success_claim_permitted is False


def test_metric_semantics_cover_cache_route_and_latency() -> None:
    semantics = set(load_review().metric_capability.required_semantics)

    assert {
        "cached_prefix_tokens",
        "newly_computed_prefill_tokens",
        "realized_route",
        "time_to_first_token_ms",
        "worker_id",
    } <= semantics


def test_reset_requires_full_worker_restart_and_identity_revalidation() -> None:
    decision = load_review().reset_capability

    assert decision.namespace_only_reset_accepted is False
    assert decision.full_worker_restart_required is True
    assert decision.closed_port_verification_required is True
    assert decision.process_exit_verification_required is True
    assert decision.startup_identity_revalidation_required is True


def test_stop_conditions_fail_closed_on_runtime_and_privacy_drift() -> None:
    decision = load_review().stop_decision

    assert decision.fail_closed is True
    assert decision.hosted_fallback_permitted is False
    assert "model_identity_mismatch" in decision.stop_conditions
    assert "cache_metric_unavailable" in decision.stop_conditions
    assert "privacy_scan_failure" in decision.stop_conditions
    assert "external_spend_nonzero" in decision.stop_conditions


def test_safety_envelope_is_review_only_and_zero_spend() -> None:
    safety = load_review().safety

    assert safety.qualification_assets_generated is False
    assert safety.notebook_created is False
    assert safety.notebook_execution_performed is False
    assert safety.gpu_execution_authorized is False
    assert safety.gpu_execution_performed is False
    assert safety.worker_start_authorized is False
    assert safety.worker_started is False
    assert safety.model_execution_performed is False
    assert safety.credential_accessed is False
    assert safety.customer_data_used is False
    assert safety.external_spend == 0
    assert safety.measured_execution_authorized is False


def test_gpu_authorization_cannot_be_enabled_by_payload_mutation() -> None:
    payload = load_review().safety.model_dump(mode="json")
    payload["gpu_execution_authorized"] = True

    with pytest.raises(ValidationError):
        EnvironmentQualificationSafetyEnvelope.model_validate(payload)


def test_historical_runtime_reuse_cannot_be_enabled() -> None:
    payload = load_review().dependency_lock.model_dump(mode="json")
    payload["historical_runtime_values_reuse_permitted"] = True

    with pytest.raises(ValidationError):
        RuntimeDependencyLockDecision.model_validate(payload)


def test_zero_fill_for_missing_metrics_cannot_be_enabled() -> None:
    payload = load_review().metric_capability.model_dump(mode="json")
    payload["zero_fill_for_missing_metrics_permitted"] = True

    with pytest.raises(ValidationError):
        MetricCapabilityDecision.model_validate(payload)


def test_fail_closed_stop_decision_cannot_be_disabled() -> None:
    payload = load_review().stop_decision.model_dump(mode="json")
    payload["fail_closed"] = False

    with pytest.raises(ValidationError):
        QualificationStopDecision.model_validate(payload)


def test_authority_bindings_must_remain_canonically_ordered() -> None:
    payload = load_review().model_dump(mode="json")
    payload["authority_bindings"] = list(reversed(payload["authority_bindings"]))

    with pytest.raises(ValidationError, match="canonically sorted"):
        FullABCLocalEnvironmentQualificationReview.model_validate(payload)


def test_write_default_review_is_byte_deterministic(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    first = write_default_review(first_path)
    second = write_default_review(second_path)

    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()


def test_write_default_review_writes_only_one_artifact(tmp_path: Path) -> None:
    output = tmp_path / REVIEW_PATH

    review = write_default_review(output)

    assert tuple(path for path in tmp_path.rglob("*") if path.is_file()) == (output,)
    assert output.read_text(encoding="utf-8") == review.canonical_json()


def test_missing_review_returns_metadata_safe_error(tmp_path: Path) -> None:
    with pytest.raises(
        FullABCLocalEnvironmentQualificationReviewError,
        match="review artifact is missing or invalid",
    ):
        load_full_abc_local_environment_qualification_review(tmp_path / "missing.json")


def test_ruff_version_is_pinned_to_01521() -> None:
    assert importlib.metadata.version("ruff") == "0.15.21"


def test_repository_authorities_validate() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("repository authority validation requires the full Git checkout")

    result = validate_repository_review_package(ROOT)

    assert result["historical_authorization_reusable"] is False
    assert result["fresh_environment_capture_required"] is True
    assert result["qualification_assets_generated"] is False
    assert result["gpu_execution_authorized"] is False
    assert result["worker_start_authorized"] is False
    assert result["measured_execution_authorized"] is False
    assert result["external_spend"] == 0
    assert result["next_gate"] == NEXT_GATE


def test_repository_artifact_is_valid_json_object() -> None:
    payload = json.loads((ROOT / REVIEW_PATH).read_text(encoding="utf-8"))

    assert isinstance(payload, dict)
