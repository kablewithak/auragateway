from __future__ import annotations

import importlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

module: Any = importlib.import_module(
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_cu129_"
    "explicit_triton_attention_backend_execution_authorization_v1"
)

ROOT = Path(__file__).resolve().parents[3]
FIXED_NOW = datetime(2026, 7, 31, 1, 0, tzinfo=UTC)


def _confirmation(
    *,
    confirmed_at: datetime = FIXED_NOW,
    window_minutes: int = 120,
    scope: str = module.AUTHORIZATION_SCOPE,
    notebook_sha256: str = module.IMPLEMENTATION_NOTEBOOK_SHA256,
) -> Any:
    return module.AuthorizationIssuanceConfirmation(
        confirmation_id=(
            "auragateway-cu129-explicit-triton-attention-backend-"
            "execution-authorization-confirmation-v1"
        ),
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=window_minutes,
        confirmed_scope=scope,
        confirmed_notebook_sha256=notebook_sha256,
    )


def _authorization(
    *,
    issued_at: datetime = FIXED_NOW,
    expires_at: datetime = FIXED_NOW + timedelta(minutes=120),
) -> Any:
    return module.AttentionBackendExecutionAuthorization(
        authorization_id=module.AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=module.AuthorizationLifecycle.ISSUED,
        scope=module.AUTHORIZATION_SCOPE,
        source_main_merge_commit=module.SOURCE_MAIN_MERGE_COMMIT,
        implementation_feature_commit=module.IMPLEMENTATION_FEATURE_COMMIT,
        implementation_record_sha256=module.IMPLEMENTATION_RECORD_SHA256,
        request_sha256=module.IMPLEMENTATION_REQUEST_SHA256,
        notebook_sha256=module.IMPLEMENTATION_NOTEBOOK_SHA256,
        issued_from_main_commit="f" * 40,
        issued_at=issued_at,
        expires_at=expires_at,
        operator_confirmation_recorded=True,
        single_use=True,
        successful_or_failed_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        budget=module.AuthorizationBudget(),
        controls=module.AuthorizationControls(),
    )


def test_merged_implementation_authority_validates_exact_artifacts() -> None:
    authority = module._implementation_authority(ROOT)

    assert authority.source_main_merge_commit == module.SOURCE_MAIN_MERGE_COMMIT
    assert authority.implementation_feature_commit == module.IMPLEMENTATION_FEATURE_COMMIT
    assert authority.implementation_record.sha256 == module.IMPLEMENTATION_RECORD_SHA256
    assert authority.notebook.sha256 == module.IMPLEMENTATION_NOTEBOOK_SHA256
    assert authority.request.sha256 == module.IMPLEMENTATION_REQUEST_SHA256
    assert authority.architecture_review.sha256 == module.IMPLEMENTATION_REVIEW_SHA256
    assert authority.template.sha256 == module.IMPLEMENTATION_TEMPLATE_SHA256
    assert authority.runtime_execution_authorized_before_issuance is False
    assert authority.unchanged_upstream_replay_authorized is False


def test_review_preserves_zero_runtime_boundary() -> None:
    review = module._build_review(ROOT)

    assert review.status == "APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"
    assert review.decision == "SEPARATE_TRANSIENT_SINGLE_USE_Q6_AUTHORIZATION"
    assert review.operator_confirmation_required is True
    assert review.authorization_must_remain_untracked is True
    assert review.successful_or_failed_attempt_consumes_authorization is True
    assert review.authorization_issued_in_review is False
    assert review.runtime_execution_performed is False
    assert review.budget.maximum_kaggle_sessions == 1
    assert review.budget.maximum_attention_primitive_attempts == 1
    assert review.budget.maximum_model_loads == 0
    assert review.budget.maximum_worker_starts == 0
    assert review.budget.maximum_model_requests == 0
    assert review.budget.maximum_benchmark_trajectory_requests == 0
    assert review.controls.network_access_permitted is False
    assert review.controls.credentials_permitted is False
    assert review.controls.customer_data_permitted is False
    assert review.next_gate == module.IMPLEMENTATION_NEXT_GATE


def test_review_is_deterministic() -> None:
    first = module._build_review(ROOT)
    second = module._build_review(ROOT)

    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


def test_confirmation_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _confirmation(confirmed_at=datetime(2026, 7, 31, 1, 0))


def test_confirmation_rejects_window_over_budget() -> None:
    with pytest.raises(ValidationError):
        _confirmation(window_minutes=241)


def test_confirmation_rejects_scope_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(scope="FULL_VLLM_ENVIRONMENT")


def test_confirmation_rejects_notebook_identity_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(notebook_sha256="0" * 64)


def test_authorization_window_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceeds reviewed budget"):
        _authorization(expires_at=FIXED_NOW + timedelta(minutes=241))


def test_build_authorization_binds_exact_scope_and_zero_budgets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())

    authorization = module._build_authorization(
        repo_root=tmp_path,
        issuer_head="f" * 40,
        confirmation=_confirmation(window_minutes=30),
    )

    assert authorization.scope == module.AUTHORIZATION_SCOPE
    assert authorization.notebook_sha256 == module.IMPLEMENTATION_NOTEBOOK_SHA256
    assert authorization.implementation_record_sha256 == (module.IMPLEMENTATION_RECORD_SHA256)
    assert authorization.expires_at - authorization.issued_at == timedelta(minutes=30)
    assert authorization.single_use is True
    assert authorization.successful_or_failed_attempt_consumes_authorization is True
    assert authorization.unchanged_replay_authorized is False
    assert authorization.budget.maximum_kaggle_sessions == 1
    assert authorization.budget.maximum_model_loads == 0
    assert authorization.budget.maximum_worker_starts == 0
    assert authorization.budget.maximum_model_requests == 0
    assert authorization.controls.measured_execution_authorized is False


def test_non_overwriting_write_preserves_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    path.write_text("existing", encoding="utf-8")

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module._write_non_overwriting(path, b"replacement")

    assert caught.value.error_code == "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_EXISTS"
    assert path.read_text(encoding="utf-8") == "existing"


def test_non_overwriting_write_uses_exact_payload(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    payload = _authorization().canonical_json().encode("utf-8")

    module._write_non_overwriting(path, payload)

    assert path.read_bytes() == payload


def test_load_canonical_rejects_pretty_json(tmp_path: Path) -> None:
    authorization = _authorization()
    path = tmp_path / "authorization.json"
    path.write_text(
        json.dumps(authorization.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module._load_canonical(path, module.AttentionBackendExecutionAuthorization)

    assert caught.value.error_code == "ATTENTION_BACKEND_AUTHORIZATION_PAYLOAD_NOT_CANONICAL"


def test_verify_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / module.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True)
    path.write_text(_authorization().canonical_json(), encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=121),
        )

    assert caught.value.error_code == "ATTENTION_BACKEND_AUTHORIZATION_EXPIRED"


def test_verify_rejects_consumed_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(_authorization().canonical_json(), encoding="utf-8")
    consumption_path = tmp_path / module.CONSUMPTION_PATH
    consumption_path.write_text("consumed", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module.verify_authorization(repo_root=tmp_path, now=FIXED_NOW)

    assert caught.value.error_code == "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_CONSUMED"


def test_consume_creates_single_non_reusable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization = _authorization()
    authorization_path.write_text(authorization.canonical_json(), encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)

    summary = module.consume_authorization(
        repo_root=tmp_path,
        outcome=module.ExecutionOutcome.FAILED,
        saved_version_id=123456789,
        consumed_at=FIXED_NOW + timedelta(minutes=20),
    )

    consumption_path = tmp_path / module.CONSUMPTION_PATH
    receipt = module.AttentionBackendAuthorizationConsumption.model_validate_json(
        consumption_path.read_text(encoding="utf-8")
    )
    assert summary["status"] == "ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_CONSUMED"
    assert receipt.outcome == module.ExecutionOutcome.FAILED
    assert receipt.saved_version_id == 123456789
    assert receipt.authorization_reusable is False
    assert receipt.authorization_sha256 == authorization.fingerprint()


def test_second_consumption_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(_authorization().canonical_json(), encoding="utf-8")
    consumption_path = tmp_path / module.CONSUMPTION_PATH
    consumption_path.write_text("existing", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module.consume_authorization(
            repo_root=tmp_path,
            outcome=module.ExecutionOutcome.PASSED,
            saved_version_id=123456789,
        )

    assert caught.value.error_code == "ATTENTION_BACKEND_AUTHORIZATION_ALREADY_CONSUMED"


def test_tracked_transient_authorization_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_run_git",
        lambda repo_root, arguments: module.AUTHORIZATION_PATH.as_posix(),
    )

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module._require_transient_paths_untracked(tmp_path)

    assert caught.value.error_code == ("ATTENTION_BACKEND_AUTHORIZATION_MUST_REMAIN_UNTRACKED")


def test_source_authority_requires_both_merged_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    monkeypatch.setattr(
        module,
        "_require_ancestor",
        lambda repo_root, commit: observed.append(commit),
    )

    module._require_source_authority(tmp_path)

    assert observed == [
        module.SOURCE_MAIN_MERGE_COMMIT,
        module.IMPLEMENTATION_FEATURE_COMMIT,
    ]


def test_validate_implementation_package_preserves_absent_authority() -> None:
    summary = module.validate_implementation_package(ROOT)

    assert summary["status"] == (
        "EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1_VALID"
    )
    assert summary["authorization_issuer_implemented"] is True
    assert summary["authorization_issued"] is False
    assert summary["runtime_execution_performed"] is False
    assert summary["maximum_kaggle_sessions"] == 1
    assert summary["maximum_attention_primitive_attempts"] == 1
    assert summary["maximum_model_loads"] == 0
    assert summary["maximum_worker_starts"] == 0
    assert summary["maximum_model_requests"] == 0
    assert summary["maximum_benchmark_trajectory_requests"] == 0
    assert summary["next_gate"] == module.IMPLEMENTATION_NEXT_GATE


def test_cli_issue_requires_operator_confirmation(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = module.main(
        [
            "issue",
            "--repo-root",
            str(ROOT),
            "--confirm-scope",
            module.AUTHORIZATION_SCOPE,
            "--confirm-notebook-sha256",
            module.IMPLEMENTATION_NOTEBOOK_SHA256,
        ]
    )

    error = json.loads(capsys.readouterr().err)
    assert exit_code == 2
    assert error["error_code"] == "ATTENTION_BACKEND_OPERATOR_CONFIRMATION_REQUIRED"


def test_cli_consume_requires_operator_confirmation(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = module.main(
        [
            "consume",
            "--repo-root",
            str(ROOT),
            "--outcome",
            "FAILED",
            "--saved-version-id",
            "123456789",
        ]
    )

    error = json.loads(capsys.readouterr().err)
    assert exit_code == 2
    assert error["error_code"] == "ATTENTION_BACKEND_OPERATOR_CONFIRMATION_REQUIRED"


def test_repository_source_commits_are_present_in_real_history() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("archive validation has no Git history")
    for commit in (
        module.SOURCE_MAIN_MERGE_COMMIT,
        module.IMPLEMENTATION_FEATURE_COMMIT,
    ):
        result = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0


def test_synchronized_main_allows_only_transient_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "f" * 40,
        ("rev-parse", "origin/main"): "f" * 40,
        ("status", "--porcelain", "--untracked-files=all"): (
            f"?? {module.AUTHORIZATION_PATH.as_posix()}"
        ),
    }
    monkeypatch.setattr(
        module,
        "_run_git",
        lambda repo_root, arguments: responses[tuple(arguments)],
    )

    observed = module._require_synchronized_main(tmp_path, allow_transient=True)

    assert observed == "f" * 40


def test_synchronized_main_rejects_unrelated_untracked_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("branch", "--show-current"): "main",
        ("rev-parse", "HEAD"): "f" * 40,
        ("rev-parse", "origin/main"): "f" * 40,
        ("status", "--porcelain", "--untracked-files=all"): "?? unrelated.txt",
    }
    monkeypatch.setattr(
        module,
        "_run_git",
        lambda repo_root, arguments: responses[tuple(arguments)],
    )

    with pytest.raises(module.AttentionBackendAuthorizationError) as caught:
        module._require_synchronized_main(tmp_path, allow_transient=True)

    assert caught.value.error_code == ("ATTENTION_BACKEND_AUTHORIZATION_REQUIRES_CLEAN_TREE")
