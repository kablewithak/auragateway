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

_FIXED_NOW = datetime(2026, 7, 19, 18, 0, tzinfo=UTC)


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
        "authorization_id": (
            "auragateway-full-abc-local-environment-qualification-execution-authorization-v1"
        ),
        "decision": "AUTHORIZED",
        "source_main_merge_commit": issuance_module.SOURCE_MAIN_MERGE_COMMIT,
        "request_sha256": issuance_module.EXECUTION_REQUEST_SHA256,
        "review_git_blob_sha": ("61590be7fe1d10e8e9b38405cf634f4a0cae3e31"),
        "authorization_issuance_review_sha256": (
            issuance_module.AUTHORIZATION_ISSUANCE_REVIEW_SHA256
        ),
        "materialization_record_sha256": (issuance_module.MATERIALIZATION_RECORD_SHA256),
        "dataset_manifest_sha256": issuance_module.RUNTIME_MANIFEST_SHA256,
        "runtime_factory": {
            "factory_path": (
                "auragateway.local_abc."
                "full_abc_local_environment_qualification_kaggle_runtime_adapter:"
                "create_runtime_adapter"
            ),
            "artifact_path": (
                "src/auragateway/local_abc/"
                "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
            ),
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


def test_confirmation_requires_timezone_aware_time() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _confirmation(confirmed_at=datetime(2026, 7, 19, 18, 0))


def test_confirmation_rejects_window_over_review_budget() -> None:
    with pytest.raises(ValidationError):
        _confirmation(window_minutes=241)


def test_confirmation_normalizes_to_utc_seconds() -> None:
    confirmation = _confirmation(
        confirmed_at=datetime(2026, 7, 19, 20, 0, 0, 123456, tzinfo=UTC),
    )

    assert confirmation.confirmed_at == datetime(
        2026,
        7,
        19,
        20,
        0,
        tzinfo=UTC,
    )


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

    with pytest.raises(
        AuthorizationIssuanceError,
        match="authorization requires main",
    ):
        issue_authorization(
            repo_root=tmp_path,
            confirmation=_confirmation(),
        )


def test_existing_authorization_is_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(issuance_module, "_require_clean_main", lambda repo_root: None)
    target = tmp_path / issuance_module.AUTHORIZATION_PATH
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    with pytest.raises(AuthorizationIssuanceError, match="already exists"):
        issue_authorization(
            repo_root=tmp_path,
            confirmation=_confirmation(),
        )

    assert target.read_text(encoding="utf-8") == "existing"


def test_write_authorization_uses_canonical_json(tmp_path: Path) -> None:
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )
    target = tmp_path / "authorization.json"

    issuance_module._write_authorization(target, authorization)

    assert target.read_text(encoding="utf-8") == authorization.canonical_json()


def test_verify_rejects_noncanonical_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / issuance_module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(
        json.dumps(_authorization_payload(), indent=2, sort_keys=True),
        encoding="utf-8",
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
        "_validate_rematerialization_package",
        lambda repo_root: {
            "materialization_record_sha256": (issuance_module.MATERIALIZATION_RECORD_SHA256)
        },
    )

    with pytest.raises(AuthorizationIssuanceError, match="canonical JSON"):
        verify_authorization(
            repo_root=tmp_path,
            now=_FIXED_NOW + timedelta(minutes=1),
        )


def test_build_authorization_binds_reviewed_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = issuance_module.issuance_review.load_review(
        Path(__file__).resolve().parents[3] / issuance_module.REVIEW_PATH
    )
    request = issuance_module.QualificationExecutionRequest.model_validate_json(
        (Path(__file__).resolve().parents[3] / issuance_module.EXECUTION_REQUEST_PATH).read_text(
            encoding="utf-8"
        )
    )
    manifest = issuance_module.QualificationDatasetManifest.model_validate_json(
        (
            Path(__file__).resolve().parents[3] / issuance_module.MATERIALIZED_DATASET_MANIFEST_PATH
        ).read_text(encoding="utf-8")
    )
    materialization_path = tmp_path / issuance_module.MATERIALIZATION_RECORD_PATH
    materialization_path.parent.mkdir(parents=True)
    materialization_path.write_text("{}", encoding="utf-8")

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
        "_validate_rematerialization_package",
        lambda repo_root: {
            "materialization_record_sha256": (issuance_module.MATERIALIZATION_RECORD_SHA256)
        },
    )
    monkeypatch.setattr(
        issuance_module.issuance_review,
        "validate_repository_review_package",
        lambda repo_root: {},
    )
    monkeypatch.setattr(
        issuance_module.issuance_review,
        "load_review",
        lambda path: review,
    )
    monkeypatch.setattr(
        issuance_module,
        "_load_operational_inputs",
        lambda repo_root: (request, manifest),
    )

    authorization = issuance_module._build_authorization(
        repo_root=tmp_path,
        confirmation=_confirmation(window_minutes=30),
    )

    assert authorization.request_sha256 == request.fingerprint()
    assert authorization.dataset_manifest_sha256 == manifest.fingerprint()
    assert authorization.review_git_blob_sha == ("61590be7fe1d10e8e9b38405cf634f4a0cae3e31")
    assert authorization.maximum_workers == 2
    assert authorization.expires_at - authorization.issued_at == timedelta(minutes=30)
    assert authorization.benchmark_trajectory_requests_permitted == 0
    assert authorization.measured_execution_authorized is False


def test_verify_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / issuance_module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization = issuance_module.QualificationExecutionAuthorization.model_validate(
        _authorization_payload()
    )
    authorization_path.write_text(
        authorization.canonical_json(),
        encoding="utf-8",
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
        "_validate_rematerialization_package",
        lambda repo_root: {
            "materialization_record_sha256": (issuance_module.MATERIALIZATION_RECORD_SHA256)
        },
    )
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


def test_source_constants_bind_pr112_and_pr110_review() -> None:
    assert issuance_module.SOURCE_MAIN_MERGE_COMMIT == ("be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50")
    assert issuance_module.REVIEW_SOURCE_MAIN_MERGE_COMMIT == (
        "211a10757999b1b110cb1d9df172938cf6ed7969"
    )
    assert issuance_module.AUTHORIZATION_ISSUANCE_REVIEW_GIT_BLOB_SHA == (
        "61590be7fe1d10e8e9b38405cf634f4a0cae3e31"
    )
    assert issuance_module.MAXIMUM_AUTHORIZATION_WINDOW_MINUTES == 240


def test_final_authorization_is_not_packaged_in_implementation_slice() -> None:
    root = Path(__file__).resolve().parents[3]

    assert not (root / issuance_module.AUTHORIZATION_PATH).exists()


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    root = Path(__file__).resolve().parents[3]
    paths = (
        root / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_"
        "authorization_issuance.py",
        root / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_contracts.py",
        Path(__file__),
        root / "tests/unit/local_abc/test_full_abc_local_environment_qualification_execution.py",
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
