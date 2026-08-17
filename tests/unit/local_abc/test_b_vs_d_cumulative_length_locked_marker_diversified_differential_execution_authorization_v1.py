from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_v1,
)

issuer = b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_v1

REPO_ROOT = Path(__file__).resolve().parents[3]


def _intent() -> issuer.AuthorizationIntent:
    return issuer.build_intent(
        REPO_ROOT,
        "1" * 40,
        prepared_at=datetime(2026, 8, 17, 18, 0, tzinfo=UTC),
        window_minutes=180,
        intent_id="2" * 32,
    )


def _authorization() -> tuple[issuer.ExecutionAuthorization, bytes]:
    intent = _intent()
    challenge = issuer.authorization_challenge(intent)
    return issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime(2026, 8, 17, 18, 1, tzinfo=UTC),
    )


def test_static_authority_identities_are_exact() -> None:
    assert issuer.DESIGN_MERGE_COMMIT == "5c7779465e04ef1fdd3d6cd3d414d357fce3cdca"
    assert (
        issuer.DESIGN_RECORD_SHA256
        == "77a8140ad6a95da54bc1b21a5844edbbcbc52f53e75d0ba2eaf8de4b55a0d848"
    )
    assert issuer.IMPLEMENTATION_MERGE_COMMIT == "a24eedc9d7a65756affc9cde224acdc80fdf7313"
    assert (
        issuer.IMPLEMENTATION_REVIEW_SHA256
        == "7278fdf91cef5fd2a19e39f4bc34421c2dce823a42e09aacc7c44ccce7fb53dc"
    )
    assert (
        issuer.IMPLEMENTATION_RECORD_SHA256
        == "795a7cdf5285ba49e5dcc57a76cd46e03f07121359a5f66101692cee41bb2074"
    )
    assert (
        issuer.SUCCESSOR_RUNTIME_SHA256
        == "fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39"
    )


def test_execution_budget_matches_frozen_six_observation_contract() -> None:
    budget = issuer.ExecutionBudget()
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 6
    assert budget.maximum_model_loads == 6
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_observations == 0
    assert budget.maximum_output_tokens_per_request == 32
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_external_spend == 0


def test_experiment_contract_exactly_matches_merged_design() -> None:
    expected = json.loads((REPO_ROOT / issuer.DESIGN_RECORD_PATH).read_text(encoding="utf-8"))
    experiment = issuer.DifferentialExperiment()
    assert experiment.model_dump(mode="json") == expected["experiment"]
    assert (
        experiment.variable_under_test
        == "MARKER_DIVERSIFICATION_UNDER_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"
    )
    assert experiment.prompt_token_count_per_condition == 899
    assert experiment.observations_per_condition == 3
    assert experiment.request_order == (
        "B_NEUTRAL_REPEATED_24X",
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
        "B_NEUTRAL_REPEATED_24X",
        "B_NEUTRAL_REPEATED_24X",
        "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
    )
    assert experiment.cumulative_prompt_token_count_profile == (
        83,
        117,
        151,
        185,
        219,
        253,
        287,
        321,
        355,
        389,
        423,
        457,
        491,
        525,
        559,
        593,
        627,
        661,
        695,
        729,
        763,
        797,
        831,
        865,
        899,
    )
    assert experiment.d_marker_sequence == (
        "birch",
        "grove",
        "juniper",
        "lagoon",
        "meadow",
        "prairie",
        "spruce",
        "umber",
        "willow",
        "acorn",
        "alder",
        "beech",
        "brook",
        "caper",
        "clover",
        "cove",
        "dune",
        "finch",
        "flint",
        "glade",
        "ivy",
        "larch",
        "lily",
        "orchid",
    )


def test_repetition_penalty_is_exact_and_float_literal_workaround_is_fail_closed() -> None:
    assert issuer.DifferentialExperiment().repetition_penalty == 1.1
    with pytest.raises(ValidationError):
        issuer.DifferentialExperiment(repetition_penalty=1.2)


def test_b_anchor_and_mixed_result_boundaries_are_frozen() -> None:
    experiment = issuer.DifferentialExperiment()
    assert experiment.b_anchor_must_reproduce_zero_of_three
    assert experiment.b_anchor_nonreproduction == "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
    assert not experiment.mixed_result_permits_mechanistic_claim
    assert experiment.b_0_d_mixed == "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"
    assert not experiment.post_hoc_two_of_three_interpretation_permitted
    assert not experiment.threshold_search_authorized
    assert not experiment.runtime_remediation_authorized
    assert not experiment.p5_p6_requalification_authorized
    assert not experiment.north_star_abc_effect_claim_authorized


def test_predeclared_stable_outcomes_are_exact() -> None:
    experiment = issuer.DifferentialExperiment()
    assert (
        experiment.b_0_d_3
        == "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
    )
    assert experiment.b_0_d_0 == "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL"
    assert experiment.b_0_d_mixed == "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"


def test_marker_novelty_and_nonclaim_boundaries_are_exact() -> None:
    experiment = issuer.DifferentialExperiment()
    assert experiment.bounded_marker_lexical_semantic_novelty_remains
    assert not experiment.marker_lexical_novelty_eliminated
    assert not experiment.marker_semantic_novelty_eliminated
    assert not experiment.exact_repetition_sole_or_root_cause_claim_permitted
    assert not experiment.aligned_block_recurrence_causal_claim_permitted
    assert not experiment.text_segment_boundary_must_equal_token_boundary


def test_required_platform_exactly_matches_merged_design() -> None:
    expected = json.loads((REPO_ROOT / issuer.DESIGN_RECORD_PATH).read_text(encoding="utf-8"))
    assert issuer.RequiredPlatform().model_dump(mode="json") == expected["platform"]


def test_runtime_model_exactly_matches_merged_design() -> None:
    expected = json.loads((REPO_ROOT / issuer.DESIGN_RECORD_PATH).read_text(encoding="utf-8"))
    assert issuer.RuntimeModelContract().model_dump(mode="json") == expected["runtime_model"]


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
    assert body.scope == "B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
    assert body.budget.maximum_worker_starts == 6
    assert body.budget.maximum_model_loads == 6
    assert body.budget.maximum_model_requests == 6
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
            confirmed_at=datetime(2026, 8, 17, 18, 1, tzinfo=UTC),
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
    assert "B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1" in text
    assert "'maximum_worker_starts': 6" in text
    assert "'maximum_model_loads': 6" in text
    assert "'maximum_model_requests': 6" in text
    assert "'prompt_token_count_per_condition': 899" in text
    assert "'condition_b_id': 'B_NEUTRAL_REPEATED_24X'" in text
    assert "'condition_d_id': 'D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED'" in text
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
        platform_observed_at=datetime(2026, 8, 17, 18, 2, tzinfo=UTC),
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
            terminalized_at=datetime(2026, 8, 17, 19, 0, tzinfo=UTC),
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
        terminalized_at=datetime(2026, 8, 17, 19, 0, tzinfo=UTC),
        saved_version_id=1,
    )
    assert receipt.platform_observation_receipt_sha256 is None
    assert not receipt.authorization_reusable


def test_static_record_is_non_authorizing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(issuer, "_require_design_ancestor", lambda root: None)
    result = issuer.validate_static(REPO_ROOT)
    assert result["status"] == "B_VS_D_MARKER_DIVERSIFIED_EXECUTION_AUTHORIZATION_V1_VALID"
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 6
    assert result["maximum_model_loads"] == 6
    assert result["condition_count"] == 2
    assert result["prompt_token_count_per_condition"] == 899
    assert result["b_anchor_must_reproduce_zero_of_three"] is True
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
