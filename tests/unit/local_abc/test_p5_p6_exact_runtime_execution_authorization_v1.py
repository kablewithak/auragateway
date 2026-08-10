"""Tests for exact-runtime P5/P6 execution authorization issuer V1."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

MODULE_PATH = Path("src/auragateway/local_abc/p5_p6_exact_runtime_execution_authorization_v1.py")


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("p5_p6_authorization_v1", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _confirmation(module: Any, *, now: datetime) -> Any:
    observed_at = now - timedelta(minutes=2)
    return module.IssuanceConfirmation(
        confirmation_id=("auragateway-exact-runtime-p5-p6-execution-authorization-confirmation-v1"),
        operator_confirmed=True,
        exact_confirmation_phrase=module.CONFIRMATION_PHRASE,
        confirmed_at=now - timedelta(minutes=1),
        authorization_window_minutes=180,
        confirmed_issuer_merge_commit="a" * 40,
        confirmed_authorization_design_merge_commit=module.AUTHORIZATION_DESIGN_MERGE_COMMIT,
        confirmed_authorization_design_record_sha256=(module.AUTHORIZATION_DESIGN_RECORD_SHA256),
        confirmed_scope=module.AUTHORIZATION_SCOPE,
        confirmed_implementation_merge_commit=module.P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        confirmed_p5_p6_design_record_sha256=module.P5_P6_DESIGN_RECORD_SHA256,
        confirmed_implementation_record_sha256=module.P5_P6_IMPLEMENTATION_RECORD_SHA256,
        confirmed_implementation_review_sha256=module.P5_P6_IMPLEMENTATION_REVIEW_SHA256,
        confirmed_notebook_sha256=module.P5_P6_NOTEBOOK_SHA256,
        confirmed_runtime_script_sha256=module.P5_P6_RUNTIME_SCRIPT_SHA256,
        confirmed_wrapper_code_sha256=module.P5_P6_WRAPPER_CODE_SHA256,
        confirmed_v5_acceptance_sha256=module.V5_ACCEPTANCE_RECORD_SHA256,
        execution_limits=module.ExecutionLimits(),
        platform=module.PlatformObservation(
            observed_at=observed_at,
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="T4_X2",
            allocated_gpu_count=2,
            internet_enabled=False,
            external_network_access_permitted=False,
            credentials_permitted=False,
            customer_data_permitted=False,
        ),
    )


def test_static_generation_does_not_issue_authority() -> None:
    module = _load_module()
    review = module._build_review()
    assert review.status == "APPROVED_FOR_MERGE_NOT_ISSUANCE"
    assert review.live_authorization_issued is False
    assert review.runtime_execution_authorized is False
    assert module.AUTHORIZATION_PATH.name.endswith("execution_authorization.json")


def test_design_and_implementation_bindings_are_exact() -> None:
    module = _load_module()
    assert module.AUTHORIZATION_DESIGN_MERGE_COMMIT == ("2877f66a112a89c313c322bd38c3f71f9caff218")
    assert module.AUTHORIZATION_DESIGN_RECORD_SHA256 == (
        "18eef4f455e67ef850cb2a4ff6502360b8885d2fff7e36ddcca7dcb6f15af230"
    )
    assert module.P5_P6_IMPLEMENTATION_MERGE_COMMIT == ("9cc06c02c372fa2e7637c432759e7a1d4db56e9e")


def test_execution_budget_matches_frozen_design() -> None:
    module = _load_module()
    limits = module.ExecutionLimits()
    assert limits.maximum_kaggle_sessions == 1
    assert limits.maximum_saved_versions == 1
    assert limits.maximum_model_requests == 6
    assert limits.maximum_worker_starts == 3
    assert limits.maximum_model_loads == 3
    assert limits.maximum_hidden_retries == 0
    assert limits.maximum_replacement_workers == 0


def test_confirmation_requires_timezone_aware_timestamps() -> None:
    module = _load_module()
    with pytest.raises(ValidationError):
        module.PlatformObservation(
            observed_at=datetime(2026, 8, 10, 1, 0, 0),
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="T4_X2",
            allocated_gpu_count=2,
            internet_enabled=False,
            external_network_access_permitted=False,
            credentials_permitted=False,
            customer_data_permitted=False,
        )


def test_freshness_is_checked_against_issue_time() -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=now)
    module._require_confirmation_fresh(confirmation, now)
    stale = confirmation.model_copy(
        update={
            "platform": confirmation.platform.model_copy(
                update={"observed_at": now - timedelta(minutes=16)}
            )
        }
    )
    with pytest.raises(module.AuthorizationIssuerError) as caught:
        module._require_confirmation_fresh(stale, now)
    assert caught.value.error_code == "P5_P6_AUTHORIZATION_PLATFORM_OBSERVATION_STALE"


def test_authorization_payload_matches_runtime_consumer_contract() -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    authorization = module._build_authorization(_confirmation(module, now=now), "a" * 40, now)
    payload = authorization.model_dump(mode="json")
    assert payload["authorization_id"] == (
        "auragateway-exact-runtime-p5-p6-requalification-v1-execution-authorization"
    )
    assert payload["authorization_filename"] == "execution_authorization_v1.json"
    assert payload["scope"] == "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"
    assert payload["decision"] == "AUTHORIZED"
    assert payload["lifecycle"] == "ISSUED"
    assert payload["runtime_execution_authorized"] is True
    assert authorization.execution_limits.maximum_model_requests == 6


def test_issue_writes_one_non_overwriting_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=now)
    monkeypatch.setattr(module, "validate_implementation", lambda _: {})
    monkeypatch.setattr(module, "_require_p5_preexecution_contract", lambda _: None)
    monkeypatch.setattr(module, "_require_issue_repo_state", lambda _root, _commit: "a" * 40)

    result = module.issue_authorization(tmp_path, confirmation=confirmation, now=now)
    assert result["live_authorization_issued"] is True
    assert result["runtime_execution_authorized"] is True
    assert result["pilot_execution_authorized"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    target = tmp_path / module.AUTHORIZATION_PATH
    assert target.is_file()

    with pytest.raises(module.AuthorizationIssuerError) as caught:
        module.issue_authorization(tmp_path, confirmation=confirmation, now=now)
    assert caught.value.error_code == "P5_P6_AUTHORIZATION_LIFECYCLE_ALREADY_STARTED"


def test_validate_live_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    issued_at = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=issued_at)
    monkeypatch.setattr(module, "validate_implementation", lambda _: {})
    monkeypatch.setattr(module, "_require_p5_preexecution_contract", lambda _: None)
    monkeypatch.setattr(module, "_require_issue_repo_state", lambda _root, _commit: "a" * 40)
    module.issue_authorization(tmp_path, confirmation=confirmation, now=issued_at)

    expired_at = issued_at + timedelta(minutes=181)
    with pytest.raises(module.AuthorizationIssuerError) as caught:
        module.validate_live_authorization(tmp_path, now=expired_at)
    assert caught.value.error_code == "P5_P6_AUTHORIZATION_OUTSIDE_VALID_WINDOW"


def test_terminal_vocabulary_matches_frozen_design() -> None:
    module = _load_module()
    assert tuple(item.value for item in module.TerminalDisposition) == (
        "CONSUMED",
        "EXPIRED_UNUSED",
        "CANCELLED_UNUSED",
        "ABANDONED_BEFORE_EXECUTION",
        "OUTCOME_UNKNOWN",
    )
    assert tuple(item.value for item in module.ExecutionOutcome) == (
        "PASSED",
        "FAILED",
        "AMBIGUOUS",
        "INTERRUPTED",
        "DIAGNOSTIC_INVALID",
    )


def test_consumed_requires_execution_attempt_and_known_outcome() -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        module.AuthorizationTerminalReceipt(
            receipt_id=(
                "auragateway-exact-runtime-p5-p6-requalification-v1-authorization-terminal-v1"
            ),
            authorization_id=module.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            issuer_merge_commit="b" * 40,
            disposition=module.TerminalDisposition.CONSUMED,
            execution_attempted=False,
            execution_outcome=None,
            terminalized_at=now,
        )


def test_passed_consumption_requires_saved_version_and_evidence() -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        module.AuthorizationTerminalReceipt(
            receipt_id=(
                "auragateway-exact-runtime-p5-p6-requalification-v1-authorization-terminal-v1"
            ),
            authorization_id=module.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            issuer_merge_commit="b" * 40,
            disposition=module.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            execution_outcome=module.ExecutionOutcome.PASSED,
            terminalized_at=now,
        )


def test_unused_disposition_rejects_execution_outcome() -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        module.AuthorizationTerminalReceipt(
            receipt_id=(
                "auragateway-exact-runtime-p5-p6-requalification-v1-authorization-terminal-v1"
            ),
            authorization_id=module.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            issuer_merge_commit="b" * 40,
            disposition=module.TerminalDisposition.CANCELLED_UNUSED,
            execution_attempted=False,
            execution_outcome=module.ExecutionOutcome.INTERRUPTED,
            terminalized_at=now,
        )


def test_terminalization_is_non_overwriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    issued_at = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=issued_at)
    monkeypatch.setattr(module, "validate_implementation", lambda _: {})
    monkeypatch.setattr(module, "_require_p5_preexecution_contract", lambda _: None)
    monkeypatch.setattr(module, "_require_issue_repo_state", lambda _root, _commit: "a" * 40)
    module.issue_authorization(tmp_path, confirmation=confirmation, now=issued_at)

    result = module.terminalize_authorization(
        tmp_path,
        disposition=module.TerminalDisposition.CANCELLED_UNUSED,
        execution_outcome=None,
        saved_version_id=None,
        evidence_zip_sha256=None,
        terminal_log_sha256=None,
        now=issued_at + timedelta(minutes=2),
    )
    assert result["runtime_execution_authorized"] is False
    assert result["disposition"] == "CANCELLED_UNUSED"

    with pytest.raises(module.AuthorizationIssuerError) as caught:
        module.terminalize_authorization(
            tmp_path,
            disposition=module.TerminalDisposition.CANCELLED_UNUSED,
            execution_outcome=None,
            saved_version_id=None,
            evidence_zip_sha256=None,
            terminal_log_sha256=None,
            now=issued_at + timedelta(minutes=3),
        )
    assert caught.value.error_code == "P5_P6_AUTHORIZATION_ALREADY_TERMINAL"


def test_outcome_unknown_requires_attempt() -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    receipt = module.AuthorizationTerminalReceipt(
        receipt_id=("auragateway-exact-runtime-p5-p6-requalification-v1-authorization-terminal-v1"),
        authorization_id=module.AUTHORIZATION_ID,
        authorization_sha256="a" * 64,
        issuer_merge_commit="b" * 40,
        disposition=module.TerminalDisposition.OUTCOME_UNKNOWN,
        execution_attempted=True,
        execution_outcome=None,
        terminalized_at=now,
    )
    assert receipt.authorization_reusable is False


def test_canonical_confirmation_file_round_trips(tmp_path: Path) -> None:
    module = _load_module()
    now = datetime(2026, 8, 10, 2, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=now)
    path = tmp_path / "confirmation.json"
    path.write_bytes(module._canonical_json_bytes(confirmation))
    loaded = module._load_confirmation(path)
    assert loaded == confirmation


def test_extra_fields_are_rejected() -> None:
    module = _load_module()
    with pytest.raises(ValidationError):
        module.ExecutionLimits.model_validate(
            {
                "maximum_kaggle_sessions": 1,
                "maximum_saved_versions": 1,
                "maximum_model_requests": 6,
                "maximum_worker_starts": 3,
                "maximum_model_loads": 3,
                "maximum_hidden_retries": 0,
                "maximum_replacement_workers": 0,
                "maximum_external_network_requests": 0,
                "maximum_benchmark_trajectory_requests": 0,
                "maximum_external_spend": 0,
                "unexpected": True,
            }
        )
