"""Tests for successor mechanism-admission execution authorization issuer V1."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

ISSUER_PATH = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_execution_authorization_v1.py"
)
TRANSPORT_PATH = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_authorization_transport_v1.py"
)


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _issuer() -> Any:
    return _load(ISSUER_PATH, "p5_p6_mechanism_successor_auth_issuer_v1")


def _transport() -> Any:
    return _load(TRANSPORT_PATH, "p5_p6_mechanism_successor_auth_transport_v1")


def _confirmation(module: Any, *, now: datetime) -> Any:
    return module.IssuanceConfirmation(
        confirmation_id=(
            "auragateway-p5-p6-mechanism-admission-successor-v1-"
            "execution-authorization-confirmation"
        ),
        operator_confirmed=True,
        exact_confirmation_phrase=module.CONFIRMATION_PHRASE,
        confirmed_at=now - timedelta(minutes=1),
        authorization_window_minutes=180,
        confirmed_issuer_merge_commit="a" * 40,
        confirmed_scope=module.AUTHORIZATION_SCOPE,
        confirmed_successor_merge_commit=module.SUCCESSOR_MERGE_COMMIT,
        confirmed_implementation_review_sha256=module.IMPLEMENTATION_REVIEW_SHA256,
        confirmed_design_record_sha256=module.DESIGN_RECORD_SHA256,
        confirmed_mechanism_contract_sha256=module.MECHANISM_CONTRACT_SHA256,
        confirmed_implementation_addendum_sha256=module.IMPLEMENTATION_ADDENDUM_SHA256,
        confirmed_runtime_script_sha256=module.RUNTIME_SCRIPT_SHA256,
        execution_limits=module.ExecutionLimits(),
        platform=module.PlatformObservation(
            observed_at=now - timedelta(minutes=2),
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="T4_X2",
            allocated_gpu_count=2,
            internet_enabled=False,
            external_network_access_permitted=False,
            credentials_permitted=False,
            customer_data_permitted=False,
        ),
    )


def test_static_candidate_does_not_include_live_authorization() -> None:
    module = _issuer()
    assert len(module.CANDIDATE_PATHS) == 9
    assert module.AUTHORIZATION_PATH not in module.CANDIDATE_PATHS
    assert module.TERMINAL_RECEIPT_PATH not in module.CANDIDATE_PATHS
    assert module.NEXT_GATE.startswith("OBSERVE_FRESH_KAGGLE_T4_X2")


def test_successor_bindings_are_exact() -> None:
    module = _issuer()
    assert module.SUCCESSOR_MERGE_COMMIT == "2b1841aee4397ae0c72bad6b2c9e7069835d8399"
    assert module.AUTHORIZATION_SCOPE == "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
    assert module.RUNTIME_SCRIPT_SHA256 == (
        "a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958"
    )
    assert module.IMPLEMENTATION_REVIEW_SHA256 == (
        "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
    )


def test_execution_budget_matches_runtime_consumer() -> None:
    module = _issuer()
    limits = module.ExecutionLimits()
    assert limits.maximum_kaggle_sessions == 1
    assert limits.maximum_saved_versions == 1
    assert limits.maximum_model_requests == 6
    assert limits.maximum_worker_starts == 3
    assert limits.maximum_model_loads == 3
    assert limits.maximum_hidden_retries == 0
    assert limits.maximum_replacement_workers == 0


def test_platform_observation_requires_timezone_aware_timestamp() -> None:
    module = _issuer()
    with pytest.raises(ValidationError):
        module.PlatformObservation(
            observed_at=datetime(2026, 8, 22, 20, 0, 0),
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="T4_X2",
            allocated_gpu_count=2,
            internet_enabled=False,
            external_network_access_permitted=False,
            credentials_permitted=False,
            customer_data_permitted=False,
        )


def test_stale_platform_observation_fails_closed() -> None:
    module = _issuer()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=now)
    stale = confirmation.model_copy(
        update={
            "platform": confirmation.platform.model_copy(
                update={"observed_at": now - timedelta(minutes=20)}
            )
        }
    )
    with pytest.raises(module.AuthorizationIssuerError) as captured:
        module._require_confirmation_fresh(stale, now)
    assert captured.value.error_code == ("P5_P6_SUCCESSOR_AUTHORIZATION_PLATFORM_OBSERVATION_STALE")


def test_authorization_payload_satisfies_successor_transport_contract() -> None:
    issuer = _issuer()
    transport = _transport()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    authorization = issuer._build_authorization(
        _confirmation(issuer, now=now),
        "a" * 40,
        now,
    )
    payload = transport.validate_authorization_bytes(
        authorization.canonical_bytes(),
        require_live=True,
        now=now,
    )
    assert payload["scope"] == issuer.AUTHORIZATION_SCOPE
    assert payload["runtime_script_sha256"] == issuer.RUNTIME_SCRIPT_SHA256
    assert payload["maximum_model_requests"] == 6
    assert payload["hidden_retries_permitted"] == 0


def test_predecessor_v2_scope_is_rejected_by_transport() -> None:
    issuer = _issuer()
    transport = _transport()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    authorization = issuer._build_authorization(
        _confirmation(issuer, now=now),
        "a" * 40,
        now,
    )
    payload = authorization.model_dump(mode="json")
    payload["scope"] = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
    bad = transport.canonical_json_bytes(payload)
    with pytest.raises(transport.AuthorizationTransportError) as captured:
        transport.validate_authorization_bytes(bad, require_live=True, now=now)
    assert captured.value.error_code == ("P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_SEMANTIC_DRIFT")


def test_issue_is_non_overwriting_and_single_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _issuer()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=now)
    monkeypatch.setattr(module, "_validate_bound_implementation", lambda _root: ())
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda _root: None)
    monkeypatch.setattr(
        module,
        "_require_issue_repo_state",
        lambda _root, _confirmed: "a" * 40,
    )
    result = module.issue_authorization(tmp_path, confirmation=confirmation, now=now)
    assert result["live_authorization_issued"] is True
    assert result["single_use"] is True
    assert (tmp_path / module.AUTHORIZATION_PATH).is_file()
    with pytest.raises(module.AuthorizationIssuerError) as captured:
        module.issue_authorization(tmp_path, confirmation=confirmation, now=now)
    assert captured.value.error_code == ("P5_P6_SUCCESSOR_AUTHORIZATION_LIFECYCLE_ALREADY_STARTED")


def test_terminalization_is_non_overwriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _issuer()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    confirmation = _confirmation(module, now=now)
    monkeypatch.setattr(module, "_validate_bound_implementation", lambda _root: ())
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda _root: None)
    monkeypatch.setattr(
        module,
        "_require_issue_repo_state",
        lambda _root, _confirmed: "a" * 40,
    )
    module.issue_authorization(tmp_path, confirmation=confirmation, now=now)
    result = module.terminalize_authorization(
        tmp_path,
        disposition=module.TerminalDisposition.CANCELLED_UNUSED,
        execution_outcome=None,
        now=now + timedelta(minutes=2),
    )
    assert result["authorization_reusable"] is False
    with pytest.raises(module.AuthorizationIssuerError) as captured:
        module.terminalize_authorization(
            tmp_path,
            disposition=module.TerminalDisposition.CANCELLED_UNUSED,
            execution_outcome=None,
            now=now + timedelta(minutes=3),
        )
    assert captured.value.error_code == "P5_P6_SUCCESSOR_AUTHORIZATION_ALREADY_TERMINAL"


def test_passed_terminal_receipt_requires_evidence() -> None:
    module = _issuer()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        module.AuthorizationTerminalReceipt(
            receipt_id=(
                "auragateway-p5-p6-mechanism-admission-successor-v1-authorization-terminal"
            ),
            authorization_id=module.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            issuer_merge_commit="b" * 40,
            disposition=module.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            execution_outcome=module.ExecutionOutcome.PASSED,
            terminalized_at=now,
        )


def test_extra_execution_limit_fields_are_rejected() -> None:
    module = _issuer()
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
