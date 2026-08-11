from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p4_p5_composition_differential_execution_authorization_v1 as issuer,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _intent() -> issuer.AuthorizationIntent:
    return issuer.build_intent(
        REPO_ROOT,
        "1" * 40,
        prepared_at=datetime(
            2026,
            8,
            12,
            0,
            0,
            tzinfo=UTC,
        ),
        window_minutes=180,
        intent_id="2" * 32,
    )


def _authorization() -> tuple[
    issuer.ExecutionAuthorization,
    bytes,
]:
    intent = _intent()
    challenge = issuer.authorization_challenge(intent)

    return issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime(
            2026,
            8,
            12,
            0,
            1,
            tzinfo=UTC,
        ),
    )


def test_static_authority_identities_are_exact() -> None:
    assert issuer.DESIGN_MERGE_COMMIT == ("0ae3c293b474f9a457ce06c7716121bff59af1a6")
    assert issuer.DESIGN_RECORD_SHA256 == (
        "f15a2926001dc4c625a6b60111269a1f3e2b6095d825455a0e8e6e0e77ee6ad2"
    )
    assert issuer.IMPLEMENTATION_MERGE_COMMIT == ("96dea44afa28e1b61c68eb0eccfc91d312bb89e0")
    assert issuer.SUCCESSOR_RUNTIME_SHA256 == (
        "4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7"
    )


def test_execution_budget_is_exactly_one_one_six() -> None:
    budget = issuer.ExecutionBudget()

    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 1
    assert budget.maximum_model_loads == 1
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0


def test_runtime_and_experiment_contracts_are_frozen() -> None:
    runtime = issuer.RuntimeModelContract()
    experiment = issuer.DifferentialExperiment()

    assert runtime.attention_backend == "TRITON_ATTN"
    assert runtime.gpu_topology == "T4_x2"
    assert runtime.model_repository == ("Qwen/Qwen2.5-0.5B-Instruct")

    assert experiment.variable_under_test == ("MESSAGE_COMPOSITION_ONLY")
    assert experiment.request_order == (
        "A",
        "B",
        "B",
        "A",
        "A",
        "B",
    )
    assert experiment.case_a_roles == (
        "system",
        "user",
    )
    assert experiment.case_b_roles == (
        "system",
        "user",
        "assistant",
        "user",
    )
    assert experiment.mixed_result_requires_separate_case_c_design
    assert not experiment.case_c_authorized_by_this_design
    assert not experiment.runtime_remediation_authorized


def test_dynamic_challenge_binds_exact_intent() -> None:
    first = _intent()
    second = first.model_copy(
        update={
            "issuer_merge_commit": "3" * 40,
        }
    )

    assert issuer.authorization_challenge(first) != (issuer.authorization_challenge(second))


def test_authorization_transaction_identity_is_canonical() -> None:
    authorization, _ = _authorization()

    expected = issuer._sha256(issuer._canonical_json_bytes(authorization.authorization))

    assert authorization.transaction_id == expected
    assert authorization.authorization.scope == ("P4_P5_COMPOSITION_DIFFERENTIAL_V1")
    assert authorization.authorization.budget.maximum_worker_starts == 1
    assert authorization.authorization.budget.maximum_model_loads == 1
    assert authorization.authorization.budget.maximum_model_requests == 6
    assert not authorization.authorization.case_c_authorized
    assert not (authorization.authorization.runtime_remediation_authorized)


def test_wrong_challenge_fails_closed() -> None:
    intent = _intent()

    with pytest.raises(
        issuer.AuthorizationIssuerError,
        match="authorization challenge",
    ):
        issuer.build_authorization(
            intent,
            challenge="0" * 64,
            confirmed_at=datetime(
                2026,
                8,
                12,
                0,
                1,
                tzinfo=UTC,
            ),
        )


def test_stale_confirmation_fails_closed() -> None:
    intent = _intent()
    challenge = issuer.authorization_challenge(intent)

    with pytest.raises(
        issuer.AuthorizationIssuerError,
        match="freshness",
    ):
        issuer.build_authorization(
            intent,
            challenge=challenge,
            confirmed_at=(intent.prepared_at + timedelta(minutes=16)),
        )


def test_successor_wrapper_is_specialized_and_compilable() -> None:
    authorization, authorization_bytes = _authorization()
    runtime_payload = (REPO_ROOT / issuer.SUCCESSOR_RUNTIME_PATH).read_bytes()

    rendered = issuer.render_executable_payload(
        REPO_ROOT,
        authorization,
        authorization_bytes,
        runtime_payload,
    )

    text = rendered.decode("utf-8")
    ast.parse(text)

    assert "__AUTHORIZATION_B64__" not in text
    assert "__RUNTIME_PAYLOAD_B64__" not in text
    assert "__TRANSACTION_ID__" not in text
    assert "P4_P5_COMPOSITION_DIFFERENTIAL_V1" in text
    assert '"maximum_worker_starts": 1' in text
    assert '"maximum_model_loads": 1' in text
    assert '"maximum_model_requests": 6' in text


def test_notebook_generation_is_deterministic() -> None:
    authorization, authorization_bytes = _authorization()
    runtime_payload = (REPO_ROOT / issuer.SUCCESSOR_RUNTIME_PATH).read_bytes()

    rendered = issuer.render_executable_payload(
        REPO_ROOT,
        authorization,
        authorization_bytes,
        runtime_payload,
    )

    first = issuer.build_notebook(rendered)
    second = issuer.build_notebook(rendered)

    assert first == second

    notebook = json.loads(first)
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) == 1


def test_terminal_contract_supports_missing_evidence_zip() -> None:
    platform = issuer.PlatformObservation(
        observed_at=datetime(
            2026,
            8,
            12,
            0,
            2,
            tzinfo=UTC,
        )
    )

    receipt = issuer.TerminalReceipt(
        transaction_id="4" * 64,
        authorization_sha256="5" * 64,
        disposition=issuer.TerminalDisposition.CONSUMED,
        execution_attempted=True,
        execution_outcome=issuer.ExecutionOutcome.DIAGNOSTIC_INVALID,
        terminalized_at=datetime(
            2026,
            8,
            12,
            1,
            0,
            tzinfo=UTC,
        ),
        saved_version_id=1,
        platform_observation=platform,
        evidence_zip_sha256=None,
        terminal_log_sha256=None,
    )

    assert receipt.evidence_zip_sha256 is None
    assert not receipt.authorization_reusable


def test_static_record_is_non_authorizing() -> None:
    result = issuer.validate_static(REPO_ROOT)

    assert result["status"] == ("P4_P5_DIFF_EXECUTION_AUTHORIZATION_V1_VALID")
    assert result["maximum_model_requests"] == 6
    assert result["maximum_worker_starts"] == 1
    assert result["maximum_model_loads"] == 1
    assert result["maximum_hidden_retries"] == 0
    assert result["live_authorization_issued"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["kaggle_execution_performed"] is False


def test_static_validation_requires_no_live_lifecycle() -> None:
    for relative in (
        issuer.LIVE_AUTHORIZATION_PATH,
        issuer.LIVE_MANIFEST_PATH,
        issuer.TERMINAL_RECEIPT_PATH,
    ):
        assert not (REPO_ROOT / relative).exists()
