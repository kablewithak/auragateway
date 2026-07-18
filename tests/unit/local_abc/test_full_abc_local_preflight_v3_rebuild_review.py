from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_preflight_v3_rebuild_review import (
    NEXT_GATE,
    REVIEW_ID,
    REVIEW_PATH,
    SOURCE_MAIN_MERGE_COMMIT,
    FullABCLocalPreflightV3RebuildReview,
    FullABCLocalPreflightV3ReviewError,
    PreflightV3ConditionFingerprintDecision,
    PreflightV3LedgerRegenerationDecision,
    PreflightV3ResolutionStage,
    PreflightV3SafetyEnvelope,
    build_default_review,
    load_full_abc_local_preflight_v3_rebuild_review,
    validate_repository_review_package,
    write_default_review,
)

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_REVIEW_SHA256 = "8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb"


def load_review() -> FullABCLocalPreflightV3RebuildReview:
    return load_full_abc_local_preflight_v3_rebuild_review(ROOT / REVIEW_PATH)


def test_review_has_expected_identity() -> None:
    review = load_review()

    assert review.review_id == REVIEW_ID
    assert review.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT
    assert review.fingerprint() == EXPECTED_REVIEW_SHA256
    assert review.next_gate == NEXT_GATE


def test_default_builder_reproduces_repository_artifact() -> None:
    assert build_default_review() == load_review()


def test_review_is_bounded_to_design_without_lifecycle_promotion() -> None:
    review = load_review()

    assert review.decision == "APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION"
    assert review.lifecycle_before == "LOCALLY_VALIDATED"
    assert review.lifecycle_after == "LOCALLY_VALIDATED"


def test_preflight_v2_is_bound_only_as_a_non_reusable_guardrail() -> None:
    bindings = {item.binding_id: item for item in load_review().authority_bindings}

    assert bindings["preflight-v2-supersession"].carry_forward_permitted is False
    assert bindings["local-runtime-correction"].carry_forward_permitted is True
    assert bindings["full-abc-integration"].carry_forward_permitted is True
    assert bindings["asset-inventory"].carry_forward_permitted is True


def test_local_extension_prd_identity_is_bound_without_repository_promotion() -> None:
    binding = next(
        item
        for item in load_review().authority_bindings
        if item.binding_id == "local-extension-prd"
    )

    assert binding.identity == "c7e9a3cde75a0acf06903ed1a3947a757b9c5ec04f2be6374af393a570dac76e"
    assert "not automatically promoted" in binding.notes


def test_dependency_locks_are_split_by_environment_boundary() -> None:
    decision = load_review().dependency_lock_decision

    assert decision.developer_lock_path.endswith("developer_dependency_lock.json")
    assert decision.kaggle_runtime_lock_path.endswith("kaggle_runtime_dependency_lock.json")
    assert decision.hosted_provider_packages_active_for_full_abc is False
    assert decision.current_kaggle_values_status == ("UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION")


def test_kaggle_dependency_schema_requires_runtime_and_cache_configuration() -> None:
    fields = set(load_review().dependency_lock_decision.kaggle_lock_required_fields)

    assert {
        "python_version",
        "torch_version",
        "cuda_version",
        "vllm_distribution_version",
        "transformers_version",
        "automatic_prefix_cache_configuration",
        "worker_startup_command_sha256",
    } <= fields


def test_condition_fingerprint_contract_preserves_causal_invariants() -> None:
    decision = load_review().condition_fingerprint_decision

    assert decision.b_c_prefix_token_hash_equal is True
    assert decision.a_b_route_schedule_equal is True
    assert decision.all_shared_fields_equal_across_conditions is True
    assert "prefix_token_hash" in decision.condition_specific_fields
    assert "route_schedule" in decision.condition_specific_fields


def test_condition_fingerprint_contract_excludes_provider_and_pricing_fields() -> None:
    decision = load_review().condition_fingerprint_decision
    active_fields = decision.shared_fields + decision.condition_specific_fields

    assert not any("pricing" in item for item in active_fields)
    assert not any("provider_adapter" in item for item in active_fields)
    assert "execution_manifest.assets.pricing_schedule_id" in decision.prohibited_fields
    assert "preflight_report.checks.provider_readiness_pending" in decision.prohibited_fields


def test_legacy_provider_model_alias_field_is_retained_without_provider_authority() -> None:
    decision = load_review().condition_fingerprint_decision

    assert decision.trace_field_provider_model_alias_retained_for_compatibility is True
    assert decision.trace_field_provider_model_alias_value == "local-qwen2.5-0.5b-instruct"
    assert decision.trace_field_provider_model_alias_semantics == (
        "legacy_name_bound_to_local_runtime_model_alias_without_provider_authority"
    )
    assert decision.trace_field_rename_requires_separate_contract_migration is True


def test_ledger_regeneration_preserves_exact_benchmark_shape() -> None:
    ledger = load_review().ledger_regeneration_decision

    assert ledger.functional_trajectories == 162
    assert ledger.runtime_trajectories == 180
    assert ledger.total_trajectories == 342
    assert ledger.total_turns == 1368
    assert ledger.maximum_request_attempts == 2736


def test_ledger_regeneration_blocks_v2_hash_reuse_and_hidden_activity() -> None:
    ledger = load_review().ledger_regeneration_decision

    assert ledger.reuse_preflight_v2_hash_bindings is False
    assert ledger.hidden_retry_permitted is False
    assert ledger.replacement_case_permitted is False
    assert ledger.every_attempt_retained is True


def test_ledger_regeneration_uses_counterbalanced_orders() -> None:
    assert load_review().ledger_regeneration_decision.counterbalanced_orders == (
        "A-B-C",
        "B-C-A",
        "C-A-B",
    )


def test_unresolved_assets_cover_every_future_resolution_stage() -> None:
    stages = {item.resolution_stage for item in load_review().unresolved_assets}

    assert stages == set(PreflightV3ResolutionStage)


def test_review_keeps_runtime_qualification_and_authorization_unresolved() -> None:
    assets = {item.asset_id: item for item in load_review().unresolved_assets}

    assert assets["current-environment-report"].resolution_stage == (
        PreflightV3ResolutionStage.ENVIRONMENT_QUALIFICATION
    )
    assert assets["variance-pilot"].resolution_stage == PreflightV3ResolutionStage.VARIANCE_PILOT
    assert assets["measured-execution-authorization"].resolution_stage == (
        PreflightV3ResolutionStage.EXECUTION_FREEZE
    )


def test_safety_envelope_is_zero_spend_and_non_executable() -> None:
    safety = load_review().safety

    assert safety.execution_enabled is False
    assert safety.preflight_v3_assets_generated is False
    assert safety.execution_manifest_frozen is False
    assert safety.measured_execution_authorized is False
    assert safety.gpu_execution_authorized is False
    assert safety.notebook_execution_performed is False
    assert safety.model_execution_performed is False
    assert safety.provider_call_performed is False
    assert safety.credential_accessed is False
    assert safety.hosted_provider_required is False
    assert safety.pricing_in_scope is False
    assert safety.external_spend == 0


def test_execution_cannot_be_enabled_by_payload_mutation() -> None:
    payload = load_review().safety.model_dump(mode="json")
    payload["execution_enabled"] = True

    with pytest.raises(ValidationError):
        PreflightV3SafetyEnvelope.model_validate(payload)


def test_v2_hash_reuse_cannot_be_enabled_by_payload_mutation() -> None:
    payload = load_review().ledger_regeneration_decision.model_dump(mode="json")
    payload["reuse_preflight_v2_hash_bindings"] = True

    with pytest.raises(ValidationError):
        PreflightV3LedgerRegenerationDecision.model_validate(payload)


def test_provider_field_cannot_enter_active_shared_fingerprint_fields() -> None:
    payload = load_review().condition_fingerprint_decision.model_dump(mode="json")
    payload["shared_fields"] = sorted([*payload["shared_fields"], "provider_adapter_version"])

    with pytest.raises(ValidationError, match="provider or pricing"):
        PreflightV3ConditionFingerprintDecision.model_validate(payload)


def test_review_authority_bindings_must_remain_canonically_ordered() -> None:
    payload = load_review().model_dump(mode="json")
    payload["authority_bindings"] = list(reversed(payload["authority_bindings"]))

    with pytest.raises(ValidationError, match="canonically sorted"):
        FullABCLocalPreflightV3RebuildReview.model_validate(payload)


def test_write_default_review_writes_only_one_canonical_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / REVIEW_PATH

    review = write_default_review(output)

    assert tuple(path for path in tmp_path.rglob("*") if path.is_file()) == (output,)
    assert output.read_text(encoding="utf-8") == review.canonical_json()


def test_missing_review_returns_metadata_safe_error(tmp_path: Path) -> None:
    with pytest.raises(
        FullABCLocalPreflightV3ReviewError,
        match="review artifact is missing or invalid",
    ):
        load_full_abc_local_preflight_v3_rebuild_review(tmp_path / "missing.json")


def test_invalid_review_json_returns_metadata_safe_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(
        FullABCLocalPreflightV3ReviewError,
        match="review artifact is missing or invalid",
    ):
        load_full_abc_local_preflight_v3_rebuild_review(path)


def test_repository_authorities_and_supersession_validate() -> None:
    summary = validate_repository_review_package(ROOT)

    assert summary == {
        "review_sha256": EXPECTED_REVIEW_SHA256,
        "decision": "APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION",
        "lifecycle_after": "LOCALLY_VALIDATED",
        "preflight_v2_reuse_permitted": False,
        "execution_enabled": False,
        "measured_execution_authorized": False,
        "hosted_provider_required": False,
        "pricing_in_scope": False,
        "external_spend": 0,
        "total_trajectories_to_regenerate": 342,
        "next_gate": NEXT_GATE,
    }


def test_review_json_is_canonical_single_line() -> None:
    path = ROOT / REVIEW_PATH
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    expected = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )

    assert text == expected
