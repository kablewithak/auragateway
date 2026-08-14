from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p4_p5_cache_context_repetition_differential_execution_authorization_v1 as issuer,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _intent() -> issuer.AuthorizationIntent:
    return issuer.build_intent(
        REPO_ROOT,
        "1" * 40,
        prepared_at=datetime(2026, 8, 14, 17, 0, tzinfo=UTC),
        window_minutes=180,
        intent_id="2" * 32,
    )


def _authorization() -> tuple[issuer.ExecutionAuthorization, bytes]:
    intent = _intent()
    challenge = issuer.authorization_challenge(intent)
    return issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime(2026, 8, 14, 17, 1, tzinfo=UTC),
    )


def test_static_authority_identities_are_exact() -> None:
    assert issuer.DESIGN_MERGE_COMMIT == "0ad27e48e72f91f52ca48927a66bbe44f099e258"
    assert (
        issuer.DESIGN_RECORD_SHA256
        == "900b76c0cf8f833733f63c006e4aa489f9581d80260f4f30f6a4b9161c973a77"
    )
    assert issuer.IMPLEMENTATION_MERGE_COMMIT == "658a21516fa6b1cc72bd53c2c65e51aae88b4d79"
    assert (
        issuer.SUCCESSOR_RUNTIME_SHA256
        == "dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b"
    )


def test_execution_budget_matches_fresh_worker_differential() -> None:
    budget = issuer.ExecutionBudget()
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 6
    assert budget.maximum_model_loads == 6
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_external_spend == 0


def test_experiment_contract_is_exact_1x_vs_24x() -> None:
    experiment = issuer.DifferentialExperiment()
    assert experiment.variable_under_test == "CACHE_CONTEXT_REPETITION_COUNT"
    assert experiment.control_condition_id == "CONTROL_1X"
    assert experiment.treatment_condition_id == "TREATMENT_24X"
    assert experiment.control_repetition_count == 1
    assert experiment.treatment_repetition_count == 24
    assert experiment.observations_per_condition == 3
    assert experiment.request_order == (
        "CONTROL_1X",
        "TREATMENT_24X",
        "TREATMENT_24X",
        "CONTROL_1X",
        "CONTROL_1X",
        "TREATMENT_24X",
    )
    assert experiment.fresh_worker_process_per_observation
    assert experiment.treatment_expected_token_count == 899
    assert (
        experiment.treatment_expected_token_sha256
        == "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    )
    assert (
        experiment.treatment_expected_payload_sha256
        == "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    )
    assert not experiment.threshold_search_authorized
    assert not experiment.runtime_remediation_authorized
    assert not experiment.measured_abc_execution_authorized


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
    assert body.scope == "P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"
    assert body.budget.maximum_worker_starts == 6
    assert body.budget.maximum_model_loads == 6
    assert body.experiment.treatment_repetition_count == 24
    assert body.durable_platform_observation_required
    assert not body.threshold_search_authorized
    assert not body.runtime_remediation_authorized
    assert not body.measured_abc_execution_authorized


def test_wrong_challenge_fails_closed() -> None:
    intent = _intent()
    with pytest.raises(issuer.AuthorizationIssuerError, match="authorization challenge"):
        issuer.build_authorization(
            intent,
            challenge="0" * 64,
            confirmed_at=datetime(2026, 8, 14, 17, 1, tzinfo=UTC),
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
    assert "P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1" in text
    assert '"maximum_worker_starts": 6' in text
    assert '"maximum_model_loads": 6' in text
    assert '"maximum_model_requests": 6' in text
    assert '"treatment_repetition_count": 24' in text
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
        platform_observed_at=datetime(2026, 8, 14, 17, 2, tzinfo=UTC),
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
            terminalized_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
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
        terminalized_at=datetime(2026, 8, 14, 18, 0, tzinfo=UTC),
        saved_version_id=1,
    )
    assert receipt.platform_observation_receipt_sha256 is None
    assert not receipt.authorization_reusable


def test_static_record_is_non_authorizing() -> None:
    result = issuer.validate_static(REPO_ROOT)
    assert result["status"] == "P4_P5_REPETITION_DIFF_EXECUTION_AUTHORIZATION_V1_VALID"
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 6
    assert result["maximum_model_loads"] == 6
    assert result["variable_under_test"] == "CACHE_CONTEXT_REPETITION_COUNT"
    assert result["control_repetition_count"] == 1
    assert result["treatment_repetition_count"] == 24
    assert result["observations_per_condition"] == 3
    assert result["durable_platform_observation_required"] is True
    assert result["live_authorization_issued"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["platform_observation_persisted"] is False


def test_static_validation_requires_no_live_lifecycle() -> None:
    for relative in (
        issuer.LIVE_AUTHORIZATION_PATH,
        issuer.LIVE_MANIFEST_PATH,
        issuer.PLATFORM_OBSERVATION_RECEIPT_PATH,
        issuer.TERMINAL_RECEIPT_PATH,
    ):
        assert not (REPO_ROOT / relative).exists()
