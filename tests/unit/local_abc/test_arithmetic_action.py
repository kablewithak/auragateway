from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.arithmetic_action import (
    ActionRealizationError,
    DiagnosticExpectedStatus,
    ReconcileBalanceAction,
    ReconcileBalanceDiagnosticCase,
    ReconcileBalanceRenderedOutput,
    execute_reconcile_balance,
    load_reconcile_balance_diagnostic_manifest,
    realize_reconcile_balance_output,
    reconcile_balance_action_schema_sha256,
    reconcile_balance_output_schema_sha256,
    reconcile_balance_result_schema_sha256,
    render_reconcile_balance_output,
)

ROOT = Path(__file__).resolve().parents[3]
DIAGNOSTIC_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_action_diagnostic_cases_v1.json"
EXPECTED_ACTION_SCHEMA_SHA256 = "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
EXPECTED_RESULT_SCHEMA_SHA256 = "660d8b3bdf6e1eaace8e48419a56d3586f5168d18a3b78e114c7dd143bc4cb46"
EXPECTED_OUTPUT_SCHEMA_SHA256 = "48a6fa77df13c92a11e2d82bbe3a864761927b278eaa9c40e2dfd0241904616c"


def diagnostic_cases() -> tuple[ReconcileBalanceDiagnosticCase, ...]:
    return load_reconcile_balance_diagnostic_manifest(DIAGNOSTIC_PATH).cases


def test_action_schema_excludes_model_generated_final_answer() -> None:
    schema = ReconcileBalanceAction.model_json_schema()
    properties = schema["properties"]

    assert "answer" not in properties
    assert set(schema["required"]) == {
        "case_id",
        "turn_index",
        "opening_balance",
        "credits",
        "debits",
    }
    assert properties["capability"]["const"] == "arithmetic.reconcile_balance.v1"
    assert schema["additionalProperties"] is False


def test_action_contract_is_immutable_and_extra_forbid() -> None:
    action = ReconcileBalanceAction(
        case_id="payment-reconciliation",
        turn_index=1,
        opening_balance=1200,
        credits=300,
        debits=50,
    )
    assert action.model_config["frozen"] is True
    assert action.model_config["extra"] == "forbid"

    with pytest.raises(ValidationError):
        ReconcileBalanceAction.model_validate(
            {
                **action.model_dump(mode="json"),
                "extra": 1,
            }
        )


def test_exact_failed_canary_arithmetic_is_deterministic() -> None:
    action = ReconcileBalanceAction(
        case_id="payment-reconciliation",
        turn_index=1,
        opening_balance=1200,
        credits=300,
        debits=50,
    )
    first = execute_reconcile_balance(action)
    second = execute_reconcile_balance(action)

    assert first.answer == 1450
    assert first == second
    assert first.fingerprint() == second.fingerprint()
    assert first.realization_source == "deterministic_executor"


def test_canonical_renderer_matches_existing_payment_output_shape() -> None:
    outcome = realize_reconcile_balance_output(
        '{"capability":"arithmetic.reconcile_balance.v1",'
        '"case_id":"payment-reconciliation","credits":300,"debits":50,'
        '"opening_balance":1200,"schema_version":"1.0.0","turn_index":1}'
    )
    assert outcome.rendered_output == ReconcileBalanceRenderedOutput(
        answer="1450", case_id="payment-reconciliation", turn_index=1
    )
    assert render_reconcile_balance_output(outcome.result) == (
        '{"answer":"1450","case_id":"payment-reconciliation",'
        '"confidence":"high","schema_version":"1.0.0","turn_index":1}'
    )


def test_success_evidence_retains_no_raw_action_or_operands() -> None:
    raw_output = (
        '{"capability":"arithmetic.reconcile_balance.v1",'
        '"case_id":"payment-reconciliation","credits":300,"debits":50,'
        '"opening_balance":1200,"schema_version":"1.0.0","turn_index":1}'
    )
    outcome = realize_reconcile_balance_output(raw_output)
    serialized = outcome.evidence.canonical_json()

    assert raw_output not in serialized
    assert "opening_balance" not in serialized
    assert "credits" not in serialized
    assert "debits" not in serialized
    assert outcome.evidence.raw_model_output_retained is False
    assert outcome.evidence.raw_action_retained is False
    assert outcome.evidence.hidden_retry_count == 0
    assert outcome.evidence.repair_attempt_count == 0
    assert outcome.evidence.direct_model_arithmetic_fallback_used is False
    assert outcome.evidence.gpu_execution_authorized is False


def test_schema_fingerprints_are_frozen() -> None:
    assert reconcile_balance_action_schema_sha256() == EXPECTED_ACTION_SCHEMA_SHA256
    assert reconcile_balance_result_schema_sha256() == EXPECTED_RESULT_SCHEMA_SHA256
    assert reconcile_balance_output_schema_sha256() == EXPECTED_OUTPUT_SCHEMA_SHA256


@pytest.mark.parametrize("case", diagnostic_cases(), ids=lambda case: case.diagnostic_id)
def test_frozen_diagnostic_cases(case: ReconcileBalanceDiagnosticCase) -> None:
    if case.expected_status is DiagnosticExpectedStatus.ACCEPTED:
        outcome = realize_reconcile_balance_output(case.input_text)
        assert outcome.result.answer == case.expected_answer
        return

    with pytest.raises(ActionRealizationError) as exc_info:
        realize_reconcile_balance_output(case.input_text)
    assert exc_info.value.code is case.expected_failure_code


def test_diagnostic_manifest_is_canonical_and_execution_blocked() -> None:
    manifest = load_reconcile_balance_diagnostic_manifest(DIAGNOSTIC_PATH)
    text = DIAGNOSTIC_PATH.read_text(encoding="utf-8")

    assert len(manifest.cases) == 20
    assert manifest.synthetic_data_only is True
    assert manifest.hidden_retries_permitted is False
    assert manifest.direct_model_arithmetic_fallback_permitted is False
    assert manifest.gpu_execution_authorized is False
    assert manifest.full_measured_rerun_authorized is False
    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert json.dumps(
        json.loads(text), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ) == text.rstrip("\n")
