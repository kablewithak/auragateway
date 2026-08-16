from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    p4_p5_token_count_matched_context_structure_differential_execution_authorization_v1 as issuer,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _intent() -> issuer.AuthorizationIntent:
    return issuer.build_intent(
        REPO_ROOT,
        "1" * 40,
        prepared_at=datetime(2026, 8, 16, 20, 0, tzinfo=UTC),
        window_minutes=180,
        intent_id="2" * 32,
    )


def _authorization() -> tuple[issuer.ExecutionAuthorization, bytes]:
    intent = _intent()
    challenge = issuer.authorization_challenge(intent)
    return issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime(2026, 8, 16, 20, 1, tzinfo=UTC),
    )


def test_static_authority_identities_are_exact() -> None:
    assert issuer.DESIGN_MERGE_COMMIT == "76f82a4bfeb583a6839ae945f53954e7dcabcfbf"
    assert (
        issuer.DESIGN_RECORD_SHA256
        == "6ba28cdb0f2d489c5de9171ab08edad6403d9adb058fb6b84caa61e03d1b69a4"
    )
    assert issuer.IMPLEMENTATION_MERGE_COMMIT == "019f3c406400f4ecb07b864349369981d4654513"
    assert (
        issuer.IMPLEMENTATION_REVIEW_SHA256
        == "fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a"
    )
    assert (
        issuer.IMPLEMENTATION_RECORD_SHA256
        == "6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27"
    )
    assert (
        issuer.SUCCESSOR_RUNTIME_SHA256
        == "9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834"
    )


def test_execution_budget_matches_frozen_nine_observation_contract() -> None:
    budget = issuer.ExecutionBudget()
    assert budget.maximum_model_requests == 9
    assert budget.maximum_worker_starts == 9
    assert budget.maximum_model_loads == 9
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_observations == 0
    assert budget.maximum_output_tokens_per_request == 32
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_external_spend == 0


def test_experiment_contract_exactly_matches_merged_design() -> None:
    expected = json.loads((REPO_ROOT / issuer.DESIGN_RECORD_PATH).read_text(encoding="utf-8"))
    experiment = issuer.DifferentialExperiment()
    assert experiment.model_dump(mode="json") == expected["experiment"]
    assert experiment.variable_under_test == "TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE"
    assert experiment.prompt_token_count_per_condition == 899
    assert experiment.observations_per_condition == 3
    assert experiment.request_order == (
        "A_ORIGINAL_24X_ANCHOR",
        "B_NEUTRAL_REPEATED_24X",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
        "B_NEUTRAL_REPEATED_24X",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
        "A_ORIGINAL_24X_ANCHOR",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
        "A_ORIGINAL_24X_ANCHOR",
        "B_NEUTRAL_REPEATED_24X",
    )


def test_repetition_penalty_is_exact_and_float_literal_workaround_is_fail_closed() -> None:
    assert issuer.DifferentialExperiment().repetition_penalty == 1.1
    with pytest.raises(ValidationError):
        issuer.DifferentialExperiment(repetition_penalty=1.2)


def test_anchor_and_mixed_result_boundaries_are_frozen() -> None:
    experiment = issuer.DifferentialExperiment()
    assert experiment.anchor_a_must_reproduce_zero_of_three
    assert (
        experiment.anchor_nonreproduction
        == "ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE"
    )
    assert not experiment.mixed_result_permits_mechanistic_claim
    assert experiment.mixed_condition == "UNSTABLE_NO_MECHANISTIC_CLAIM"
    assert not experiment.threshold_search_authorized
    assert not experiment.runtime_remediation_authorized
    assert not experiment.p5_p6_requalification_authorized
    assert not experiment.north_star_abc_effect_claim_authorized


def test_predeclared_stable_outcomes_are_exact() -> None:
    experiment = issuer.DifferentialExperiment()
    assert (
        experiment.a_0_b_3_c_3
        == "REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED"
    )
    assert experiment.a_0_b_0_c_3 == "HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"
    assert experiment.a_0_b_0_c_0 == "SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE"
    assert experiment.a_0_b_3_c_0 == "DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED"


def test_required_platform_exactly_matches_merged_design() -> None:
    expected = json.loads((REPO_ROOT / issuer.DESIGN_RECORD_PATH).read_text(encoding="utf-8"))
    assert issuer.RequiredPlatform().model_dump(mode="json") == expected["platform"]


def test_dynamic_challenge_binds_exact_intent() -> None:
    first = _intent()
    second = first.model_copy(update={"issuer_merge_commit": "3" * 40})
    assert issuer.authorization_challenge(first) != issuer.authorization_challenge(second)


def test_authorization_transaction_identity_is_canonical() -> None:
    authorization, _ = _authorization()
    assert authorization.transaction_id == issuer._sha256(
        issuer._canonical_json_bytes(authorization.authorization)
    )
    body = authorization.authorization
    assert body.scope == "P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"
    assert body.budget.maximum_worker_starts == 9
    assert body.budget.maximum_model_loads == 9
    assert body.budget.maximum_model_requests == 9
    assert body.experiment.prompt_token_count_per_condition == 899
    assert body.durable_platform_observation_required
    assert not body.threshold_search_authorized
    assert not body.runtime_remediation_authorized
    assert not body.p5_p6_requalification_authorized
    assert not body.north_star_abc_effect_claim_authorized


def test_wrong_challenge_fails_closed() -> None:
    intent = _intent()
    with pytest.raises(issuer.AuthorizationIssuerError, match="authorization challenge"):
        issuer.build_authorization(
            intent,
            challenge="0" * 64,
            confirmed_at=datetime(2026, 8, 16, 20, 1, tzinfo=UTC),
        )


def test_stale_confirmation_fails_closed() -> None:
    intent = _intent()
    with pytest.raises(issuer.AuthorizationIssuerError, match="freshness"):
        issuer.build_authorization(
            intent,
            challenge=issuer.authorization_challenge(intent),
            confirmed_at=intent.prepared_at + timedelta(minutes=16),
        )


def test_successor_wrapper_is_specialized_and_compilable() -> None:
    authorization, authorization_bytes = _authorization()
    runtime_payload = (REPO_ROOT / issuer.SUCCESSOR_RUNTIME_PATH).read_bytes()
    rendered = issuer.render_executable_payload(
        REPO_ROOT, authorization, authorization_bytes, runtime_payload
    )
    text = rendered.decode("utf-8")
    ast.parse(text)
    assert "__AUTHORIZATION_B64__" not in text
    assert "__RUNTIME_PAYLOAD_B64__" not in text
    assert "P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1" in text
    assert "'maximum_worker_starts': 9" in text
    assert "'maximum_model_loads': 9" in text
    assert "'maximum_model_requests': 9" in text
    assert "'prompt_token_count_per_condition': 899" in text
    assert "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL" in text


def test_notebook_generation_is_deterministic() -> None:
    authorization, authorization_bytes = _authorization()
    runtime_payload = (REPO_ROOT / issuer.SUCCESSOR_RUNTIME_PATH).read_bytes()
    rendered = issuer.render_executable_payload(
        REPO_ROOT, authorization, authorization_bytes, runtime_payload
    )
    first = issuer.build_notebook(rendered)
    second = issuer.build_notebook(rendered)
    assert first == second
    notebook = json.loads(first)
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) == 1


def test_platform_receipt_contract_binds_required_fields() -> None:
    receipt = issuer.PlatformObservationReceipt(
        transaction_id="4" * 64,
        authorization_sha256="5" * 64,
        manifest_sha256="6" * 64,
        platform_observed_at=datetime(2026, 8, 16, 20, 2, tzinfo=UTC),
    )
    assert receipt.control_id == "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    assert receipt.accelerator == "T4_X2"
    assert receipt.allocated_gpu_count == 2
    assert not receipt.internet_enabled
    assert receipt.capability_source == "KAGGLE_NOTEBOOK_SETTINGS_UI"
    assert receipt.persisted_before_save_and_run_all
    assert not receipt.receipt_runtime_input


def test_passed_terminal_receipt_requires_platform_observation() -> None:
    with pytest.raises(ValueError, match="durable platform observation"):
        issuer.TerminalReceipt(
            transaction_id="4" * 64,
            authorization_sha256="5" * 64,
            manifest_sha256="6" * 64,
            disposition=issuer.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            execution_outcome=issuer.ExecutionOutcome.PASSED,
            terminalized_at=datetime(2026, 8, 16, 21, 0, tzinfo=UTC),
            saved_version_id=1,
        )


def test_failed_terminal_receipt_can_close_missing_platform_receipt() -> None:
    receipt = issuer.TerminalReceipt(
        transaction_id="4" * 64,
        authorization_sha256="5" * 64,
        manifest_sha256="6" * 64,
        disposition=issuer.TerminalDisposition.CONSUMED,
        execution_attempted=True,
        execution_outcome=issuer.ExecutionOutcome.DIAGNOSTIC_INVALID,
        terminalized_at=datetime(2026, 8, 16, 21, 0, tzinfo=UTC),
        saved_version_id=1,
    )
    assert receipt.platform_observation_receipt_sha256 is None
    assert not receipt.authorization_reusable


def test_static_record_is_non_authorizing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(issuer, "_require_design_ancestor", lambda root: None)
    result = issuer.validate_static(REPO_ROOT)
    assert result["status"] == "P4_P5_TOKEN_MATCHED_STRUCTURE_EXECUTION_AUTHORIZATION_V1_VALID"
    assert result["maximum_model_requests"] == 9
    assert result["maximum_worker_starts"] == 9
    assert result["maximum_model_loads"] == 9
    assert result["condition_count"] == 3
    assert result["prompt_token_count_per_condition"] == 899
    assert result["anchor_a_must_reproduce_zero_of_three"] is True
    assert result["mixed_result_permits_mechanistic_claim"] is False
    assert result["live_authorization_issued"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["governed_executable_generated"] is False
    assert result["platform_observation_persisted"] is False


def test_static_validation_requires_no_live_lifecycle() -> None:
    for relative in (
        issuer.LIVE_AUTHORIZATION_PATH,
        issuer.LIVE_MANIFEST_PATH,
        issuer.PLATFORM_OBSERVATION_RECEIPT_PATH,
        issuer.TERMINAL_RECEIPT_PATH,
    ):
        assert not (REPO_ROOT / relative).exists()


def test_template_has_each_transaction_marker_exactly_once() -> None:
    template = (REPO_ROOT / issuer.TEMPLATE_PATH).read_text(encoding="utf-8")
    for marker in (
        "__AUTHORIZATION_B64__",
        "__RUNTIME_PAYLOAD_B64__",
        "__TRANSACTION_ID__",
        "__ISSUER_MERGE_COMMIT__",
        "__ISSUER_SOURCE_SHA256__",
        "__RUNTIME_PAYLOAD_SHA256__",
        "__GENERATOR_CONTRACT_SHA256__",
    ):
        assert template.count(marker) == 1
