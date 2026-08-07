from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import p5_p6_successor_execution_authorization_v1 as auth

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXED_NOW = datetime(2026, 8, 7, 21, 0, tzinfo=UTC)
ISSUER_HEAD = "a" * 40


def _platform(
    *,
    observed_at: datetime = FIXED_NOW,
    internet_enabled: bool = False,
) -> auth.PlatformCapabilityObservation:
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "observed_at": observed_at,
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "observed_platform_accelerator": "GPU_T4_X2",
        "observed_allocated_gpu_count": 2,
        "observed_internet_enabled": internet_enabled,
        "observed_wheelhouse_attachment_count": 1,
        "observed_model_snapshot_attachment_count": 1,
        "worker_1_cuda_visible_devices": "0",
        "worker_1_visible_gpu_count": 1,
        "worker_1_gpu_index": 0,
        "worker_2_cuda_visible_devices": "1",
        "worker_2_visible_gpu_count": 1,
        "worker_2_gpu_index": 1,
    }
    return auth.PlatformCapabilityObservation.model_validate(payload)


def _confirmation(
    *,
    confirmed_at: datetime = FIXED_NOW,
    observed_at: datetime = FIXED_NOW,
    issuer_head: str = ISSUER_HEAD,
) -> auth.IssuanceConfirmation:
    return auth.IssuanceConfirmation(
        confirmation_id=("auragateway-p5-p6-successor-execution-authorization-confirmation-v1"),
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=240,
        confirmed_issuer_merge_commit=issuer_head,
        confirmed_scope="P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1",
        confirmed_implementation_merge_commit=auth.SOURCE_MAIN_MERGE_COMMIT,
        confirmed_notebook_sha256=(
            "113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8"
        ),
        confirmed_runtime_script_sha256=(
            "5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"
        ),
        confirmed_wrapper_code_sha256=(
            "f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"
        ),
        confirmed_request_sha256=(
            "a341d81489255c25c95a3fd70962e214c0841e9eee8ff5bd54faef02dd60d07a"
        ),
        confirmed_implementation_record_sha256=(
            "386d2fa9b3695ba664316f05ad805e01cac74d317ff9568a813a03127dc86285"
        ),
        confirmed_model_snapshot_sha256=auth.MODEL_SNAPSHOT_SHA256,
        confirmed_backend="TRITON_ATTN",
        confirmed_model_request_budget=5,
        confirmed_worker_start_budget=3,
        confirmed_model_load_budget=3,
        confirmed_saved_version_budget=1,
        confirmed_no_hidden_retries=True,
        confirmed_no_replacement_workers=True,
        confirmed_consumption_required=True,
        platform=_platform(observed_at=observed_at),
    )


def _patch_static_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    *,
    terminal_present: bool = False,
) -> None:
    monkeypatch.setattr(
        auth,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: ISSUER_HEAD,
    )
    monkeypatch.setattr(auth, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(auth, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(auth, "_validate_static", lambda repo_root: object())
    if terminal_present:
        monkeypatch.setattr(
            auth,
            "_require_no_terminal_receipt",
            lambda repo_root: (_ for _ in ()).throw(
                auth.SuccessorAuthorizationError(
                    "P5_P6_AUTHORIZATION_ALREADY_TERMINAL",
                    "terminal",
                )
            ),
        )
    else:
        monkeypatch.setattr(auth, "_require_no_terminal_receipt", lambda repo_root: None)


def test_implementation_binds_exact_successor_assets() -> None:
    implementation = auth._implementation(REPO_ROOT)

    assert implementation.source_main_merge_commit == auth.SOURCE_MAIN_MERGE_COMMIT
    assert implementation.implementation_status == "IMPLEMENTED_NOT_EXECUTED"
    assert implementation.notebook.sha256 == (
        "113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8"
    )
    assert implementation.runtime_script_sha256 == (
        "5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"
    )
    assert implementation.wrapper_code_sha256 == (
        "f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"
    )
    assert implementation.execution_budget.maximum_model_requests == 5
    assert implementation.execution_budget.maximum_worker_starts == 3
    assert implementation.request_identities.p5_cold_reuses_p4_canary is True
    assert implementation.measured_abc_execution_authorized is False


def test_request_identities_are_exact() -> None:
    identities = auth.RequestIdentityAuthority.model_validate(auth.EXPECTED_REQUEST_IDENTITIES)
    assert identities.model_dump(mode="json") == auth.EXPECTED_REQUEST_IDENTITIES


def test_request_identity_drift_is_rejected() -> None:
    payload = dict(auth.EXPECTED_REQUEST_IDENTITIES)
    payload["p6_worker_2_logical_sha256"] = "0" * 64

    with pytest.raises(ValidationError):
        auth.RequestIdentityAuthority.model_validate(payload)


def test_review_preserves_pre_execution_boundary() -> None:
    review = auth._build_review(REPO_ROOT)

    assert review.runtime_execution_authorized_in_review is False
    assert review.measured_abc_execution_authorized is False
    assert review.operator_confirmation_required is True
    assert review.live_platform_observation_required is True
    assert review.authorization_must_remain_untracked is True
    assert review.every_terminal_attempt_consumes_authorization is True
    assert review.unused_authority_may_be_abandoned_non_reusably is True


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for relative in (
        *auth.EXPECTED_ARTIFACTS,
        auth.SOURCE_PATH,
        auth.TEST_PATH,
        auth.ADR_PATH,
        auth.REPORT_PATH,
        auth.RUNBOOK_PATH,
    ):
        source = REPO_ROOT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    record = auth.generate(repo)
    summary = auth.validate_implementation(repo)

    assert record.authorization_issued is False
    assert record.runtime_execution_performed is False
    assert summary["runtime_execution_authorized"] is False
    assert summary["measured_abc_execution_authorized"] is False
    assert summary["maximum_model_requests"] == 5


def test_static_review_does_not_create_transient_authority(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for relative in (
        *auth.EXPECTED_ARTIFACTS,
        auth.SOURCE_PATH,
        auth.TEST_PATH,
        auth.ADR_PATH,
        auth.REPORT_PATH,
        auth.RUNBOOK_PATH,
    ):
        source = REPO_ROOT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    auth.generate(repo)

    assert not (repo / auth.AUTHORIZATION_PATH).exists()
    assert not (repo / auth.CONSUMPTION_PATH).exists()
    assert not (repo / auth.ABANDONMENT_PATH).exists()


def test_platform_observation_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        _platform(observed_at=datetime(2026, 8, 7, 21, 0))


def test_platform_observation_rejects_internet_enabled() -> None:
    with pytest.raises(ValidationError):
        _platform(internet_enabled=True)


def test_confirmation_requires_fresh_platform_observation() -> None:
    with pytest.raises(ValidationError):
        _confirmation(
            confirmed_at=FIXED_NOW,
            observed_at=FIXED_NOW - timedelta(minutes=16),
        )


def test_confirmation_rejects_future_platform_observation() -> None:
    with pytest.raises(ValidationError):
        _confirmation(
            confirmed_at=FIXED_NOW,
            observed_at=FIXED_NOW + timedelta(seconds=1),
        )


def test_confirmation_binds_dual_worker_topology() -> None:
    confirmation = _confirmation()

    assert confirmation.platform.observed_allocated_gpu_count == 2
    assert confirmation.platform.worker_1_cuda_visible_devices == "0"
    assert confirmation.platform.worker_2_cuda_visible_devices == "1"
    assert confirmation.confirmed_model_request_budget == 5
    assert confirmation.confirmed_no_replacement_workers is True


def test_build_authorization_binds_exact_budget_and_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth, "_validate_static", lambda repo_root: object())

    authorization = auth._build_authorization(
        repo_root=REPO_ROOT,
        issuer_head=ISSUER_HEAD,
        confirmation=_confirmation(),
    )

    assert authorization.runtime_execution_authorized is True
    assert authorization.measured_abc_execution_authorized is False
    assert authorization.single_use is True
    assert authorization.unchanged_replay_authorized is False
    assert authorization.budget.maximum_saved_versions == 1
    assert authorization.budget.maximum_model_requests == 5
    assert authorization.controls.worker_1_port == 8001
    assert authorization.controls.worker_2_port == 8002


def test_build_authorization_rejects_issuer_confirmation_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth, "_validate_static", lambda repo_root: object())

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth._build_authorization(
            repo_root=REPO_ROOT,
            issuer_head="b" * 40,
            confirmation=_confirmation(),
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_ISSUER_CONFIRMATION_DRIFT"


def test_issue_rejects_stale_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_static_lifecycle(monkeypatch)

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth.issue_authorization(
            repo_root=REPO_ROOT,
            confirmation=_confirmation(
                confirmed_at=FIXED_NOW - timedelta(minutes=16),
                observed_at=FIXED_NOW - timedelta(minutes=16),
            ),
            now=FIXED_NOW,
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_CONFIRMATION_STALE"


def test_authorization_window_is_bounded() -> None:
    confirmation = _confirmation()
    authorization = auth.ExecutionAuthorization(
        authorization_id=auth.AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=auth.AuthorizationLifecycle.ISSUED,
        scope=auth.AUTHORIZATION_SCOPE,
        source_main_merge_commit=auth.SOURCE_MAIN_MERGE_COMMIT,
        issued_from_main_commit=ISSUER_HEAD,
        issued_at=FIXED_NOW,
        expires_at=FIXED_NOW + timedelta(minutes=240),
        implementation=auth._implementation(REPO_ROOT),
        capability_observation=confirmation.platform,
        operator_confirmation_recorded=True,
        runtime_execution_authorized=True,
        single_use=True,
        every_terminal_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        measured_abc_execution_authorized=False,
        budget=auth.ExecutionBudget(),
        controls=auth.RuntimeControls(),
    )

    assert authorization.expires_at - authorization.issued_at == timedelta(minutes=240)


def test_authorization_rejects_oversized_window() -> None:
    confirmation = _confirmation()

    with pytest.raises(ValidationError):
        auth.ExecutionAuthorization(
            authorization_id=auth.AUTHORIZATION_ID,
            decision="AUTHORIZED",
            lifecycle=auth.AuthorizationLifecycle.ISSUED,
            scope=auth.AUTHORIZATION_SCOPE,
            source_main_merge_commit=auth.SOURCE_MAIN_MERGE_COMMIT,
            issued_from_main_commit=ISSUER_HEAD,
            issued_at=FIXED_NOW,
            expires_at=FIXED_NOW + timedelta(minutes=241),
            implementation=auth._implementation(REPO_ROOT),
            capability_observation=confirmation.platform,
            operator_confirmation_recorded=True,
            runtime_execution_authorized=True,
            single_use=True,
            every_terminal_attempt_consumes_authorization=True,
            unchanged_replay_authorized=False,
            measured_abc_execution_authorized=False,
            budget=auth.ExecutionBudget(),
            controls=auth.RuntimeControls(),
        )


def test_passed_consumption_requires_terminal_evidence() -> None:
    with pytest.raises(ValidationError):
        auth.AuthorizationConsumption(
            consumption_id=("auragateway-p5-p6-successor-execution-authorization-consumption-v1"),
            authorization_id=auth.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            lifecycle=auth.AuthorizationLifecycle.CONSUMED,
            consumed_at=FIXED_NOW,
            outcome=auth.ExecutionOutcome.PASSED,
            saved_version_id=1,
            authorization_reusable=False,
            runtime_execution_authorized=False,
            measured_abc_execution_authorized=False,
            next_gate=auth.CONSUMED_NEXT_GATE,
        )


def test_failed_consumption_may_preserve_partial_metadata() -> None:
    receipt = auth.AuthorizationConsumption(
        consumption_id=("auragateway-p5-p6-successor-execution-authorization-consumption-v1"),
        authorization_id=auth.AUTHORIZATION_ID,
        authorization_sha256="a" * 64,
        lifecycle=auth.AuthorizationLifecycle.CONSUMED,
        consumed_at=FIXED_NOW,
        outcome=auth.ExecutionOutcome.FAILED,
        saved_version_id=None,
        authorization_reusable=False,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=auth.CONSUMED_NEXT_GATE,
    )

    assert receipt.saved_version_id is None
    assert receipt.authorization_reusable is False


def test_every_terminal_outcome_is_representable() -> None:
    expected = {
        "PASSED",
        "FAILED",
        "INTERRUPTED",
        "TIMED_OUT",
        "KAGGLE_PLATFORM_TERMINATED",
        "OUTCOME_UNKNOWN",
    }
    assert {item.value for item in auth.ExecutionOutcome} == expected


def test_abandonment_is_non_reusable() -> None:
    receipt = auth.AuthorizationAbandonment(
        abandonment_id=("auragateway-p5-p6-successor-execution-authorization-abandonment-v1"),
        authorization_id=auth.AUTHORIZATION_ID,
        authorization_sha256="a" * 64,
        lifecycle=auth.AuthorizationLifecycle.ABANDONED,
        abandoned_at=FIXED_NOW,
        reason=auth.AbandonmentReason.OPERATOR_CANCELLED,
        execution_attempted=False,
        authorization_reusable=False,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=auth.ABANDONED_NEXT_GATE,
    )

    assert receipt.execution_attempted is False
    assert receipt.authorization_reusable is False


def test_non_overwriting_write_preserves_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_bytes(b"existing")

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth._write_non_overwriting(path, b"replacement")

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_ALREADY_EXISTS"
    assert path.read_bytes() == b"existing"


def test_load_canonical_rejects_pretty_json(tmp_path: Path) -> None:
    confirmation = _confirmation()
    path = tmp_path / "confirmation.json"
    path.write_text(
        json.dumps(confirmation.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth._load_confirmation(path)

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_PAYLOAD_NOT_CANONICAL"


def test_transient_paths_are_not_static_outputs() -> None:
    assert auth.AUTHORIZATION_PATH not in {auth.REVIEW_PATH, auth.RECORD_PATH}
    assert auth.CONSUMPTION_PATH not in {auth.REVIEW_PATH, auth.RECORD_PATH}
    assert auth.ABANDONMENT_PATH not in {auth.REVIEW_PATH, auth.RECORD_PATH}


def test_runtime_contract_requires_ambiguous_metric_fail_closed() -> None:
    implementation = auth._implementation(REPO_ROOT)

    assert implementation.evidence.ambiguous_relevant_metric_series_fail_closed is True
    assert implementation.evidence.token_telemetry_is_primary_p5_proof is True
    assert implementation.evidence.model_semantics_permitted_as_p6_route_proof is False


def test_validate_implementation_preserves_absent_authority(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for relative in (
        *auth.EXPECTED_ARTIFACTS,
        auth.SOURCE_PATH,
        auth.TEST_PATH,
        auth.ADR_PATH,
        auth.REPORT_PATH,
        auth.RUNBOOK_PATH,
    ):
        source = REPO_ROOT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    auth.generate(repo)
    summary = auth.validate_implementation(repo)

    assert summary["authorization_issuer_implemented"] is True
    assert summary["authorization_issued"] is False
    assert summary["runtime_execution_authorized"] is False
    assert not (repo / auth.AUTHORIZATION_PATH).exists()


def test_unknown_outcome_is_terminal_and_non_reusable() -> None:
    receipt = auth.AuthorizationConsumption(
        consumption_id=("auragateway-p5-p6-successor-execution-authorization-consumption-v1"),
        authorization_id=auth.AUTHORIZATION_ID,
        authorization_sha256="a" * 64,
        lifecycle=auth.AuthorizationLifecycle.CONSUMED,
        consumed_at=FIXED_NOW,
        outcome=auth.ExecutionOutcome.OUTCOME_UNKNOWN,
        saved_version_id=None,
        authorization_reusable=False,
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=auth.CONSUMED_NEXT_GATE,
    )

    assert receipt.outcome is auth.ExecutionOutcome.OUTCOME_UNKNOWN
    assert receipt.authorization_reusable is False


def test_issue_verify_and_consume_single_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    implementation = auth._implementation(REPO_ROOT)
    monkeypatch.setattr(
        auth,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: ISSUER_HEAD,
    )
    monkeypatch.setattr(auth, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(auth, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(auth, "_validate_static", lambda repo_root: object())
    monkeypatch.setattr(auth, "_implementation", lambda repo_root: implementation)

    confirmation = _confirmation()
    issued = auth.issue_authorization(
        repo_root=tmp_path,
        confirmation=confirmation,
        now=FIXED_NOW,
    )

    assert issued["runtime_execution_authorized"] is True
    assert issued["maximum_model_requests"] == 5
    assert (tmp_path / auth.AUTHORIZATION_PATH).is_file()

    verified = auth.verify_authorization(
        repo_root=tmp_path,
        now=FIXED_NOW + timedelta(minutes=1),
    )

    assert verified["consumed"] is False
    assert verified["abandoned"] is False
    assert verified["runtime_execution_authorized"] is True

    consumed = auth.consume_authorization(
        repo_root=tmp_path,
        outcome=auth.ExecutionOutcome.FAILED,
        saved_version_id=340900001,
        terminal_log_sha256="b" * 64,
        consumed_at=FIXED_NOW + timedelta(minutes=2),
    )

    assert consumed["authorization_reusable"] is False
    assert consumed["runtime_execution_authorized"] is False
    assert (tmp_path / auth.CONSUMPTION_PATH).is_file()

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=3),
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_ALREADY_TERMINAL"


def test_verify_rejects_expired_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    implementation = auth._implementation(REPO_ROOT)
    monkeypatch.setattr(
        auth,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: ISSUER_HEAD,
    )
    monkeypatch.setattr(auth, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(auth, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(auth, "_validate_static", lambda repo_root: object())
    monkeypatch.setattr(auth, "_implementation", lambda repo_root: implementation)

    confirmation = auth.IssuanceConfirmation(
        **{
            **_confirmation().model_dump(),
            "authorization_window_minutes": 1,
        }
    )
    auth.issue_authorization(
        repo_root=tmp_path,
        confirmation=confirmation,
        now=FIXED_NOW,
    )

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=2),
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_EXPIRED"


def test_abandon_terminalizes_unused_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    implementation = auth._implementation(REPO_ROOT)
    monkeypatch.setattr(
        auth,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: ISSUER_HEAD,
    )
    monkeypatch.setattr(auth, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(auth, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(auth, "_validate_static", lambda repo_root: object())
    monkeypatch.setattr(auth, "_implementation", lambda repo_root: implementation)

    auth.issue_authorization(
        repo_root=tmp_path,
        confirmation=_confirmation(),
        now=FIXED_NOW,
    )

    result = auth.abandon_authorization(
        repo_root=tmp_path,
        reason=auth.AbandonmentReason.OPERATOR_CANCELLED,
        abandoned_at=FIXED_NOW + timedelta(minutes=1),
    )

    assert result["status"] == "ABANDONED_BEFORE_EXECUTION"
    assert result["authorization_reusable"] is False
    assert (tmp_path / auth.ABANDONMENT_PATH).is_file()

    with pytest.raises(auth.SuccessorAuthorizationError) as captured:
        auth.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=2),
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_ALREADY_TERMINAL"
