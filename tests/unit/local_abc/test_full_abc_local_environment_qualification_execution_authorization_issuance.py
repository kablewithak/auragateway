from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

issuance_module: Any = importlib.import_module(
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_execution_authorization_issuance"
)

AuthorizationIssuanceConfirmation = issuance_module.AuthorizationIssuanceConfirmation
AuthorizationIssuanceError = issuance_module.AuthorizationIssuanceError
issue_authorization = issuance_module.issue_authorization
verify_authorization = issuance_module.verify_authorization

ROOT = Path(__file__).resolve().parents[3]
_FIXED_NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


def _confirmation(
    *,
    confirmed_at: datetime = _FIXED_NOW,
    window_minutes: int = 240,
) -> Any:
    return AuthorizationIssuanceConfirmation(
        confirmation_id=(
            "auragateway-full-abc-local-environment-qualification-"
            "authorization-issuance-confirmation-v1"
        ),
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=window_minutes,
    )


def _authorization_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "authorization_id": issuance_module.AUTHORIZATION_ID,
        "decision": "AUTHORIZED",
        "source_main_merge_commit": issuance_module.SOURCE_MAIN_MERGE_COMMIT,
        "request_sha256": issuance_module.EXECUTION_REQUEST_SHA256,
        "review_git_blob_sha": "61590be7fe1d10e8e9b38405cf634f4a0cae3e31",
        "authorization_issuance_review_sha256": (issuance_module.READINESS_REVIEW_SHA256),
        "materialization_record_sha256": (issuance_module.MATERIALIZATION_RECORD_SHA256),
        "dataset_manifest_sha256": issuance_module.RUNTIME_MANIFEST_SHA256,
        "runtime_factory": {
            "factory_path": issuance_module.authorization_contracts.RUNTIME_FACTORY_PATH,
            "artifact_path": issuance_module.RUNTIME_ADAPTER_PATH.as_posix(),
            "artifact_sha256": issuance_module.RUNTIME_ADAPTER_SHA256,
        },
        "issued_at": _FIXED_NOW.isoformat(),
        "expires_at": (_FIXED_NOW + timedelta(minutes=240)).isoformat(),
        "maximum_workers": 2,
        "maximum_kaggle_sessions": 1,
        "maximum_model_requests": 8,
        "maximum_output_tokens_per_request": 32,
        "benchmark_trajectory_requests_permitted": 0,
        "customer_data_permitted": False,
        "credentials_permitted": False,
        "network_access_permitted": False,
        "external_spend": 0,
        "operator_confirmation_recorded": True,
        "measured_execution_authorized": False,
    }


def _current_inputs() -> Any:
    readiness_model = issuance_module.harness_integration.FreshAuthorizationReadinessReview
    readiness = readiness_model.model_validate_json(
        (ROOT / issuance_module.READINESS_REVIEW_PATH).read_text(encoding="utf-8")
    )
    authorization_request_model = (
        issuance_module.authorization_contracts.QualificationAuthorizationRequest
    )
    authorization_request = authorization_request_model.model_validate_json(
        (ROOT / issuance_module.AUTHORIZATION_REQUEST_PATH).read_text(encoding="utf-8")
    )
    execution_request = issuance_module.QualificationExecutionRequest.model_validate_json(
        (ROOT / issuance_module.EXECUTION_REQUEST_PATH).read_text(encoding="utf-8")
    )
    runtime_manifest = issuance_module.QualificationDatasetManifest.model_validate_json(
        (ROOT / issuance_module.MATERIALIZED_DATASET_MANIFEST_PATH).read_text(encoding="utf-8")
    )
    materialization_model = issuance_module.authorization_contracts.MaterializedOfflineDatasetRecord
    materialization_record = materialization_model.model_validate_json(
        (ROOT / issuance_module.MATERIALIZATION_RECORD_PATH).read_text(encoding="utf-8")
    )
    return issuance_module.CurrentAuthorizationInputs(
        readiness=readiness,
        authorization_request=authorization_request,
        execution_request=execution_request,
        runtime_manifest=runtime_manifest,
        materialization_record=materialization_record,
    )


def _patch_verification_prerequisites(
    monkeypatch: pytest.MonkeyPatch,
    inputs: Any,
) -> None:
    monkeypatch.setattr(
        issuance_module,
        "_require_verification_main",
        lambda repo_root: "f" * 40,
    )
    monkeypatch.setattr(
        issuance_module,
        "_require_authorization_untracked",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        issuance_module,
        "_require_source_authority",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        issuance_module,
        "_validate_no_runtime_activity",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        issuance_module,
        "_validate_current_input_package",
        lambda repo_root: inputs,
    )


def test_confirmation_requires_timezone_aware_time() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _confirmation(confirmed_at=datetime(2026, 7, 22, 12, 0))


def test_confirmation_rejects_window_over_review_budget() -> None:
    with pytest.raises(ValidationError):
        _confirmation(window_minutes=241)


def test_confirmation_normalizes_to_utc_seconds() -> None:
    confirmation = _confirmation(
        confirmed_at=datetime(2026, 7, 22, 12, 0, 0, 123456, tzinfo=UTC),
    )

    assert confirmation.confirmed_at == _FIXED_NOW


def test_clean_main_requires_local_head_to_equal_origin_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "a" * 40,
        ("rev-parse", "origin/main"): "b" * 40,
    }
    monkeypatch.setattr(
        issuance_module,
        "_run_git",
        lambda repo_root, arguments, **kwargs: responses[tuple(arguments)],
    )

    with pytest.raises(AuthorizationIssuanceError) as caught:
        issuance_module._require_clean_main(tmp_path)

    assert caught.value.error_code == "AUTHORIZATION_ISSUANCE_MAIN_NOT_SYNCHRONIZED"


def test_verification_allows_only_transient_authorization_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "a" * 40,
        ("rev-parse", "origin/main"): "a" * 40,
        ("status", "--porcelain", "--untracked-files=all"): (
            f"?? {issuance_module.AUTHORIZATION_PATH.as_posix()}"
        ),
    }
    monkeypatch.setattr(
        issuance_module,
        "_run_git",
        lambda repo_root, arguments, **kwargs: responses[tuple(arguments)],
    )

    observed = issuance_module._require_verification_main(tmp_path)

    assert observed == "a" * 40


def test_issue_requires_clean_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        issuance_module,
        "_require_clean_main",
        lambda repo_root: (_ for _ in ()).throw(
            AuthorizationIssuanceError(
                "AUTHORIZATION_ISSUANCE_REQUIRES_MAIN",
                "authorization requires main",
            )
        ),
    )

    with pytest.raises(AuthorizationIssuanceError, match="authorization requires main"):
        issue_authorization(
            repo_root=tmp_path,
            confirmation=_confirmation(),
        )


def test_tracked_authorization_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        issuance_module,
        "_run_git",
        lambda repo_root, arguments, **kwargs: issuance_module.AUTHORIZATION_PATH.as_posix(),
    )

    with pytest.raises(AuthorizationIssuanceError) as caught:
        issuance_module._require_authorization_untracked(tmp_path)

    assert caught.value.error_code == "AUTHORIZATION_MUST_REMAIN_UNTRACKED"


def test_existing_authorization_is_never_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "authorization.json"
    target.write_text("existing", encoding="utf-8")
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )

    with pytest.raises(AuthorizationIssuanceError, match="already exists"):
        issuance_module._write_authorization(target, authorization)

    assert target.read_text(encoding="utf-8") == "existing"


def test_write_authorization_uses_canonical_json(tmp_path: Path) -> None:
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )
    target = tmp_path / "authorization.json"

    issuance_module._write_authorization(target, authorization)

    assert target.read_text(encoding="utf-8") == authorization.canonical_json()


def test_build_authorization_binds_worker_observability_inputs_and_frozen_loader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _current_inputs()
    monkeypatch.setattr(
        issuance_module,
        "_prepare_issuance_inputs",
        lambda repo_root: inputs,
    )

    authorization = issuance_module._build_authorization(
        repo_root=tmp_path,
        confirmation=_confirmation(window_minutes=30),
    )

    assert authorization.source_main_merge_commit == issuance_module.SOURCE_MAIN_MERGE_COMMIT
    assert authorization.request_sha256 == issuance_module.EXECUTION_REQUEST_SHA256
    assert authorization.authorization_issuance_review_sha256 == (
        issuance_module.READINESS_REVIEW_SHA256
    )
    assert authorization.materialization_record_sha256 == (
        inputs.materialization_record.fingerprint()
    )
    assert authorization.dataset_manifest_sha256 == inputs.runtime_manifest.fingerprint()
    assert authorization.materialization_record_sha256 == (
        issuance_module.MATERIALIZATION_RECORD_SHA256
    )
    assert authorization.dataset_manifest_sha256 == issuance_module.RUNTIME_MANIFEST_SHA256
    assert authorization.runtime_factory.artifact_sha256 == issuance_module.RUNTIME_ADAPTER_SHA256
    assert authorization.expires_at - authorization.issued_at == timedelta(minutes=30)
    issuance_module._validate_frozen_loader_parity(authorization)


def test_fresh_issuer_accepts_worker_observability_active_inputs() -> None:
    inputs = issuance_module._validate_current_input_package(ROOT)

    assert inputs.readiness.review_id == (
        "auragateway-cu129-worker-observability-fresh-authorization-readiness-review-v1"
    )
    assert inputs.readiness.current_worker_startup_diagnostics_sha256 == (
        issuance_module.harness_integration.CURRENT_WORKER_DIAGNOSTICS_SHA256
    )
    assert inputs.runtime_manifest.fingerprint() == issuance_module.RUNTIME_MANIFEST_SHA256
    assert inputs.materialization_record.fingerprint() == (
        issuance_module.MATERIALIZATION_RECORD_SHA256
    )


def test_implementation_summary_preserves_zero_runtime_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _current_inputs()
    monkeypatch.setattr(
        issuance_module,
        "_prepare_issuance_inputs",
        lambda repo_root: inputs,
    )

    summary = issuance_module.validate_implementation_package(tmp_path)

    assert summary["status"] == "FRESH_CU129_AUTHORIZATION_ISSUER_READY"
    assert summary["current_authorization_base_commit"] == (
        issuance_module.CURRENT_AUTHORIZATION_BASE_COMMIT
    )
    assert summary["worker_startup_diagnostics_sha256"] == (
        issuance_module.harness_integration.CURRENT_WORKER_DIAGNOSTICS_SHA256
    )
    assert summary["authorization_issued"] is False
    assert summary["kaggle_session_started"] is False
    assert summary["worker_started"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["benchmark_trajectory_requests_permitted"] == 0
    assert summary["next_gate"] == issuance_module.IMPLEMENTATION_NEXT_GATE


def test_verify_rejects_noncanonical_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _current_inputs()
    _patch_verification_prerequisites(monkeypatch, inputs)
    authorization_path = tmp_path / issuance_module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(
        json.dumps(_authorization_payload(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(AuthorizationIssuanceError, match="canonical JSON"):
        verify_authorization(
            repo_root=tmp_path,
            now=_FIXED_NOW + timedelta(minutes=1),
        )


def test_verify_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _current_inputs()
    _patch_verification_prerequisites(monkeypatch, inputs)
    authorization_path = tmp_path / issuance_module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )
    authorization_path.write_text(authorization.canonical_json(), encoding="utf-8")

    with pytest.raises(AuthorizationIssuanceError, match="validity window"):
        verify_authorization(
            repo_root=tmp_path,
            now=_FIXED_NOW + timedelta(minutes=241),
        )


def test_cli_requires_explicit_operator_confirmation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = issuance_module.main(["issue", "--repo-root", str(tmp_path)])

    assert result == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "OPERATOR_CONFIRMATION_REQUIRED"


def test_current_and_frozen_authorities_are_not_conflated() -> None:
    assert issuance_module.CURRENT_AUTHORIZATION_BASE_COMMIT == (
        "fba5d25ec831f0ec28a1bcd3d63e9c6d8c4b985b"
    )
    assert issuance_module.CURRENT_HARNESS_SOURCE_COMMIT == (
        "dceda98989386de7a4d57616f9f8a8023f866f10"
    )
    assert issuance_module.SOURCE_MAIN_MERGE_COMMIT == ("211a10757999b1b110cb1d9df172938cf6ed7969")
    assert issuance_module.HARNESS_SOURCE_COMMIT == ("be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50")
    assert issuance_module.READINESS_REVIEW_SHA256 == (
        "cca6d7599296b295ceeb4a613d802a66a724e5243c7e8548d69aa8b17e68beaf"
    )
    assert issuance_module.harness_integration.READINESS_REVIEW_PATH == (
        issuance_module.READINESS_REVIEW_PATH
    )
    assert issuance_module.MAXIMUM_AUTHORIZATION_WINDOW_MINUTES == 240


def test_current_issuance_payload_round_trips_through_frozen_loader() -> None:
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )

    issuance_module._validate_frozen_loader_parity(authorization)


def test_frozen_loader_rejects_current_harness_commit_as_payload_source() -> None:
    payload = _authorization_payload()
    payload["source_main_merge_commit"] = issuance_module.CURRENT_HARNESS_SOURCE_COMMIT

    with pytest.raises(ValidationError):
        issuance_module.QualificationExecutionAuthorization.model_validate(payload)


def test_frozen_loader_parity_failure_uses_explicit_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )
    parity_error = issuance_module.source_authority_parity.FrozenLoaderParityError(
        "incompatible",
        details=("source_main_merge_commit",),
    )
    monkeypatch.setattr(
        issuance_module.source_authority_parity,
        "validate_authorization_payload",
        lambda payload: (_ for _ in ()).throw(parity_error),
    )

    with pytest.raises(AuthorizationIssuanceError) as caught:
        issuance_module._validate_frozen_loader_parity(authorization)

    assert caught.value.error_code == "CURRENT_ISSUANCE_FROZEN_LOADER_PARITY_FAILED"
    assert caught.value.details == ("source_main_merge_commit",)


def test_final_authorization_is_not_packaged_in_implementation_slice() -> None:
    assert not (ROOT / issuance_module.AUTHORIZATION_PATH).exists()


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    paths = (
        ROOT / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization_issuance.py",
        ROOT / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_cu129_authority_graph.py",
        Path(__file__),
        ROOT / "tests/unit/local_abc/"
        "test_full_abc_local_environment_qualification_cu129_authority_graph.py",
    )
    failures: list[str] = []
    for path in paths:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if len(line) > 100:
                failures.append(f"{path.as_posix()}:{line_number}:{len(line)}")

    assert failures == []
