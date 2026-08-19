from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

issuer = cast(
    Any,
    importlib.import_module(
        "auragateway.local_abc.canonical_synthetic_prefix_c4_single_use_execution_authorization_v1"
    ),
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_static_issuer_binds_frozen_design_and_c4_runtime() -> None:
    review = issuer._static_review(REPO_ROOT)
    assert review["design_merge_commit"] == ("79b8ae8c1c96ea3f296725daff09615767caaefa")
    assert review["design_record_sha256"] == (
        "191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463"
    )
    assert review["implementation_merge_commit"] == ("9785f9f931bfa5bdd2d0bd97881759b5610eafa6")
    assert review["successor_runtime_sha256"] == (
        "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
    )
    assert review["qualification_request_sha256"] == (
        "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
    )
    assert review["reusable_prefix_receipt_sha256"] == (
        "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
    )


def test_static_issuer_freezes_three_request_budget() -> None:
    budget = issuer.ExecutionBudget()
    assert budget.maximum_kaggle_sessions == 1
    assert budget.maximum_save_and_run_all_actions == 1
    assert budget.maximum_runtime_install_attempts == 1
    assert budget.maximum_runtime_import_closure_probes == 1
    assert budget.maximum_model_requests == 3
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_worker_teardowns == 3
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_requests == 0
    assert budget.maximum_external_network_requests == 0
    assert budget.maximum_benchmark_trajectory_requests == 0
    assert budget.maximum_external_spend == 0


def test_static_issuer_freezes_c4_identity_and_acceptance_contract() -> None:
    qualification = issuer.QualificationContract()
    assert qualification.full_prompt_token_count == 899
    assert qualification.full_prompt_token_sha256 == (
        "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
    )
    assert qualification.reusable_prefix_token_count == 880
    assert qualification.reusable_prefix_token_sha256 == (
        "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
    )
    assert qualification.canonical_request_payload_sha256 == (
        "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
    )
    assert qualification.observation_count == 3
    assert qualification.exact_pass_count_required == 3
    assert qualification.strict_duplicate_key_rejection
    assert qualification.strict_integer_value_validation
    assert qualification.finish_reason_stop_required
    assert qualification.hidden_retries_permitted == 0
    assert qualification.replacement_requests_permitted == 0
    assert not qualification.threshold_relaxation_permitted


def test_repetition_penalty_drift_is_rejected() -> None:
    with pytest.raises(ValidationError):
        issuer.QualificationContract(repetition_penalty=1.2)


def test_static_review_and_record_do_not_issue_authority() -> None:
    review = issuer._static_review(REPO_ROOT)
    review_bytes = issuer._artifact_json_bytes(review)
    record = issuer._static_record(REPO_ROOT, review_bytes)
    assert review["status"] == "APPROVED_STATIC_ISSUER_IMPLEMENTATION"
    assert not review["live_authorization_issued"]
    assert not review["runtime_execution_authorized"]
    assert not review["governed_executable_generated"]
    assert not review["platform_observation_persisted"]
    assert not review["kaggle_execution_performed"]
    assert record["status"] == "IMPLEMENTED_NOT_ISSUED"
    assert not record["live_authorization_issued"]
    assert not record["runtime_execution_authorized"]
    assert record["model_requests_performed"] == 0
    assert record["model_loads_performed"] == 0
    assert record["worker_starts_performed"] == 0
    assert not record["c4_qualified"]
    assert not record["p5_requalified"]
    assert not record["p6_requalified"]


def _intent(prepared_at: datetime) -> Any:
    return issuer.build_intent(
        REPO_ROOT,
        "a" * 40,
        prepared_at=prepared_at,
        window_minutes=180,
        intent_id="b" * 32,
    )


def test_dynamic_challenge_binds_exact_authorization_intent() -> None:
    prepared = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)
    intent = _intent(prepared)
    challenge = issuer.authorization_challenge(intent)
    assert len(challenge) == 64
    changed = intent.model_copy(update={"authorization_window_minutes": 181})
    assert issuer.authorization_challenge(changed) != challenge


def test_build_authorization_rejects_wrong_challenge() -> None:
    prepared = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)
    intent = _intent(prepared)
    with pytest.raises(
        issuer.AuthorizationIssuerError,
        match="challenge",
    ):
        issuer.build_authorization(
            intent,
            challenge="0" * 64,
            confirmed_at=prepared + timedelta(minutes=1),
        )


def test_build_authorization_rejects_stale_confirmation() -> None:
    prepared = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)
    intent = _intent(prepared)
    challenge = issuer.authorization_challenge(intent)
    with pytest.raises(
        issuer.AuthorizationIssuerError,
        match="freshness",
    ):
        issuer.build_authorization(
            intent,
            challenge=challenge,
            confirmed_at=prepared + timedelta(minutes=16),
        )


def test_transaction_id_is_canonical_authorization_sha256() -> None:
    prepared = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)
    intent = _intent(prepared)
    challenge = issuer.authorization_challenge(intent)
    authorization, _ = issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=prepared + timedelta(minutes=1),
    )
    expected = issuer._sha256(issuer._canonical_json_bytes(authorization.authorization))
    assert authorization.transaction_id == expected
    assert not authorization.authorization.repository_acceptance_established
    assert authorization.authorization.c4_qualification_execution_authorized
    assert not authorization.authorization.p5_execution_authorized
    assert not authorization.authorization.p6_execution_authorized


def test_wrapper_generation_is_deterministic_and_catches_zero_system_exit() -> None:
    prepared = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)
    intent = _intent(prepared)
    challenge = issuer.authorization_challenge(intent)
    authorization, authorization_bytes = issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=prepared + timedelta(minutes=1),
    )
    first, first_sha = issuer._render_wrapper(
        REPO_ROOT,
        authorization,
        authorization_bytes,
    )
    second, second_sha = issuer._render_wrapper(
        REPO_ROOT,
        authorization,
        authorization_bytes,
    )
    assert first == second
    assert first_sha == second_sha
    text = first.decode("utf-8")
    assert "__AUTHORIZATION_B64__" not in text
    assert "__RUNTIME_PAYLOAD_B64__" not in text
    assert "except SystemExit as primary:" in text
    assert "if primary.code in (None, 0):" in text
    assert "AURAGATEWAY_BOUND_RUNTIME_EXIT=0" in text


def test_notebook_container_has_one_code_cell_and_no_live_input() -> None:
    payload = b"print('bounded')\n"
    notebook = json.loads(issuer._notebook_bytes(payload))
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) == 1
    assert notebook["cells"][0]["cell_type"] == "code"
    metadata = notebook["metadata"]["auragateway"]
    assert metadata["notebook_name"] == "ag-c4-canonical-prefix-qual-v1"
    assert metadata["authorization_specific_kaggle_inputs"] == 0
    assert metadata["manual_confirmation_json_files"] == 0


def test_platform_receipt_is_not_runtime_input() -> None:
    observed = datetime(2026, 8, 18, 21, 0, tzinfo=UTC)
    receipt = issuer.PlatformObservationReceipt(
        transaction_id="a" * 64,
        authorization_sha256="b" * 64,
        manifest_sha256="c" * 64,
        platform_observed_at=observed,
    )
    assert receipt.accelerator == "T4_X2"
    assert receipt.allocated_gpu_count == 2
    assert not receipt.internet_enabled
    assert receipt.persisted_before_save_and_run_all
    assert not receipt.receipt_runtime_input


def test_qualified_terminal_receipt_requires_custody_and_saved_version() -> None:
    now = datetime(2026, 8, 18, 21, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        issuer.TerminalReceipt(
            transaction_id="a" * 64,
            authorization_sha256="b" * 64,
            manifest_sha256="c" * 64,
            disposition=issuer.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            observed_c4_state=issuer.ObservedC4State.QUALIFIED,
            terminalized_at=now,
        )


def test_unused_terminal_receipt_cannot_claim_c4_observation() -> None:
    now = datetime(2026, 8, 18, 21, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        issuer.TerminalReceipt(
            transaction_id="a" * 64,
            authorization_sha256="b" * 64,
            manifest_sha256="c" * 64,
            disposition=issuer.TerminalDisposition.CANCELLED_UNUSED,
            execution_attempted=False,
            observed_c4_state=issuer.ObservedC4State.NOT_QUALIFIED,
            terminalized_at=now,
        )
