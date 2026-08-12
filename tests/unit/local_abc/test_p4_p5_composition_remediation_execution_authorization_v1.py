from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p4_p5_composition_remediation_execution_authorization_v1 as issuer,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _intent() -> issuer.AuthorizationIntent:
    return issuer.build_intent(
        REPO_ROOT,
        "1" * 40,
        prepared_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        window_minutes=180,
        intent_id="2" * 32,
    )


def _authorization() -> tuple[issuer.ExecutionAuthorization, bytes]:
    intent = _intent()
    challenge = issuer.authorization_challenge(intent)
    return issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime(2026, 8, 12, 12, 1, tzinfo=UTC),
    )


def test_static_authority_identities_are_exact() -> None:
    assert issuer.DESIGN_MERGE_COMMIT == "788305abee1f7f4bae2d61d88009cf3f3a5f33a9"
    assert (
        issuer.DESIGN_RECORD_SHA256
        == "8eefe8e9d343fc20fcab4b868d623f546478787c0e57b32b836f6b879f7265b4"
    )
    assert issuer.IMPLEMENTATION_MERGE_COMMIT == "f5701274037162ab9ff8f0627a544ac76d9c1b7b"
    assert (
        issuer.SUCCESSOR_RUNTIME_SHA256
        == "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
    )


def test_execution_budget_matches_full_p5_p6_runtime() -> None:
    budget = issuer.ExecutionBudget()
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0


def test_qualification_contract_is_full_confirmation() -> None:
    qualification = issuer.QualificationContract()
    assert qualification.structured_request_roles == (
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    )
    assert qualification.structured_request_count == 6
    assert qualification.p5_state_required == "PASS"
    assert qualification.p6_state_required == "PASS"
    assert qualification.cache_specific_proof_required
    assert qualification.p6_isolation_proof_required
    assert not qualification.standalone_a_r_differential_required
    assert not qualification.case_c_authorized


def test_dynamic_challenge_binds_exact_intent() -> None:
    first = _intent()
    second = first.model_copy(update={"issuer_merge_commit": "3" * 40})
    assert issuer.authorization_challenge(first) != issuer.authorization_challenge(second)


def test_authorization_transaction_identity_is_canonical() -> None:
    authorization, _ = _authorization()
    assert authorization.transaction_id == issuer._sha256(
        issuer._canonical_json_bytes(authorization.authorization)
    )
    assert authorization.authorization.scope == "P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1"
    assert authorization.authorization.budget.maximum_worker_starts == 3
    assert authorization.authorization.budget.maximum_model_loads == 3
    assert authorization.authorization.durable_platform_observation_required
    assert not authorization.authorization.case_c_authorized


def test_wrong_challenge_fails_closed() -> None:
    intent = _intent()
    with pytest.raises(issuer.AuthorizationIssuerError, match="authorization challenge"):
        issuer.build_authorization(
            intent,
            challenge="0" * 64,
            confirmed_at=datetime(2026, 8, 12, 12, 1, tzinfo=UTC),
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
    assert "P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1" in text
    assert '"maximum_worker_starts": 3' in text
    assert '"maximum_model_loads": 3' in text
    assert '"maximum_model_requests": 6' in text
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
        platform_observed_at=datetime(2026, 8, 12, 12, 2, tzinfo=UTC),
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
            terminalized_at=datetime(2026, 8, 12, 13, 0, tzinfo=UTC),
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
        terminalized_at=datetime(2026, 8, 12, 13, 0, tzinfo=UTC),
        saved_version_id=1,
    )
    assert receipt.platform_observation_receipt_sha256 is None
    assert not receipt.authorization_reusable


def test_static_record_is_non_authorizing() -> None:
    result = issuer.validate_static(REPO_ROOT)
    assert result["status"] == "P4_P5_REMEDIATION_EXECUTION_AUTHORIZATION_V1_VALID"
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 3
    assert result["maximum_model_loads"] == 3
    assert result["structured_request_count"] == 6
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
