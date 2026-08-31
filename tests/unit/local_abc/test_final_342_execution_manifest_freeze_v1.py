"""Focused tests for the final-342 frozen execution-manifest subject."""

from __future__ import annotations

import json
from pathlib import Path

from auragateway.local_abc import final_342_execution_manifest_freeze_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def _manifest() -> subject.Final342ExecutionManifest:
    return subject.Final342ExecutionManifest.model_validate_json(
        (ROOT / subject.MANIFEST_PATH).read_bytes()
    )


def test_required_field_inventory_is_exactly_69_unique_fields() -> None:
    manifest = _manifest()

    assert len(subject.REQUIRED_FIELD_NAMES) == 69
    assert len(set(subject.REQUIRED_FIELD_NAMES)) == 69
    assert subject.required_field_names(manifest) == subject.REQUIRED_FIELD_NAMES


def test_manifest_semantic_hash_is_self_consistent_without_recursive_file_hash() -> None:
    manifest = _manifest()

    assert manifest.identity.execution_manifest_hash == subject.semantic_manifest_sha256(manifest)
    assert manifest.identity.git_commit_hash == "POST_COMMIT_CUSTODY_RECEIPT_REQUIRED"
    assert manifest.custody.first_containing_commit_stored_inside_manifest is False


def test_manifest_uses_final_local_runtime_not_historical_hosted_provider() -> None:
    manifest = _manifest()

    assert manifest.provider_telemetry.primary_provider == "local_vllm"
    assert manifest.provider_telemetry.provider_model_alias == ("local-qwen2.5-0.5b-instruct")
    assert manifest.runtime_qualification.execution_backend == "local_vllm"
    assert manifest.runtime_qualification.model_repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert manifest.runtime_qualification.vllm_distribution_version == "0.25.1+cu129"
    assert manifest.runtime_qualification.python_abi == "cp312"


def test_provider_era_fields_are_explicitly_specialized_without_fake_authority() -> None:
    manifest = _manifest()

    assert manifest.provider_telemetry.provider_documentation_date_checked == (
        "NOT_APPLICABLE_LOCAL_RUNTIME_ARTIFACT_BOUND"
    )
    assert manifest.provider_telemetry.pricing_schedule_version == (
        "NOT_APPLICABLE_MONETARY_COST_OUT_OF_SCOPE"
    )
    assert manifest.provider_telemetry.currency == "NONE"
    assert manifest.cost_scope.monetary_cost_comparison_in_scope is False
    assert manifest.cost_scope.synthetic_price_per_request_permitted is False


def test_route_compatibility_binds_single_model_to_frozen_worker_schedules() -> None:
    manifest = _manifest()
    route = manifest.route_compatibility

    assert route.historical_provider_model_routing_reused is False
    assert route.turn_local_route_schedule_id == "turn-local-worker1-worker2-v1"
    assert route.affinity_route_schedule_id == "affinity-worker1-worker1-v1"
    assert manifest.route_policy.economy_model_alias == route.single_local_model_alias
    assert manifest.route_policy.capable_model_alias == route.single_local_model_alias
    expected_hash = subject.sha256_bytes(
        subject.canonical_json_bytes(route.model_dump(mode="json"))
    )
    assert manifest.route_policy.capability_calibration_report_hash == expected_hash


def test_final_protected_review_schedule_is_manifest_bound() -> None:
    manifest = _manifest()

    assert manifest.evaluation_adjudication.review_sample_schedule_hash == (
        subject.EXPECTED_REVIEW_SCHEDULE_SHA256
    )


def test_exact_runtime_lock_and_runtime_versions_are_frozen() -> None:
    manifest = _manifest()

    assert manifest.identity.dependency_lock_hash == subject.EXPECTED_RUNTIME_LOCK_SHA256
    assert manifest.runtime_qualification.requirements_lock_sha256 == (
        subject.EXPECTED_RUNTIME_LOCK_SHA256
    )
    assert manifest.runtime_qualification.torch_version == "2.11.0+cu129"
    assert manifest.runtime_qualification.torch_cuda_version == "12.9"
    assert manifest.runtime_qualification.triton_version == "3.6.0"
    assert manifest.runtime_qualification.transformers_version == "5.14.1"
    assert manifest.runtime_qualification.attention_backend == "TRITON_ATTN"


def test_custody_transition_is_acyclic_and_freeze_gate_is_not_prematurely_promoted() -> None:
    manifest = _manifest()

    assert manifest.custody.source_subject_commit == subject.SOURCE_SUBJECT_COMMIT
    assert manifest.custody.post_commit_custody_receipt_required is True
    assert manifest.custody.receipt_binds_manifest_semantic_sha256 is True
    assert manifest.custody.receipt_binds_manifest_file_sha256 is True
    assert manifest.custody.receipt_binds_first_containing_commit is True
    assert manifest.custody.repository_freeze_gate_promoted_before_receipt is False
    assert manifest.safety_state.manifest_subject_bytes_frozen is True
    assert manifest.safety_state.repository_execution_manifest_frozen is False
    assert manifest.safety_state.repository_freeze_gate_promoted is False


def test_semantic_mutation_invalidates_stored_manifest_hash() -> None:
    manifest = _manifest()
    changed = manifest.model_copy(
        update={"cost_scope": manifest.cost_scope.model_copy(update={"external_spend_ceiling": 1})}
    )

    assert changed.identity.execution_manifest_hash != subject.semantic_manifest_sha256(changed)


def test_repository_validator_is_non_authorizing_and_requires_custody_next() -> None:
    summary = subject.validate(ROOT)

    assert summary["status"] == "FINAL_342_EXECUTION_MANIFEST_FROZEN_SUBJECT_V1_VALID"
    assert summary["required_field_count"] == 69
    assert summary["manifest_subject_bytes_frozen"] is True
    assert summary["post_commit_custody_receipt_required"] is True
    assert summary["repository_execution_manifest_frozen"] is False
    assert summary["repository_freeze_gate_promoted"] is False
    assert summary["final_measured_abc_execution_authorized"] is False
    assert summary["effect_claims_permitted"] is False
    assert summary["next_gate"] == ("BIND_FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_V1")


def test_manifest_file_is_canonical_json_with_single_final_newline() -> None:
    raw = (ROOT / subject.MANIFEST_PATH).read_bytes()
    parsed = json.loads(raw)

    assert raw == subject.canonical_json_bytes(parsed)
