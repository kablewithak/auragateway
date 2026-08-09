from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v4_execution_authorization_v1 as authorization,
)


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    required_paths = (
        authorization.ISSUER_SOURCE_PATH,
        authorization.ISSUER_TEST_PATH,
        authorization.ISSUER_RUNBOOK_PATH,
    )
    for relative in required_paths:
        source = source_root / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    def fake_git(
        repo_root: Path,
        *args: str,
    ) -> tuple[int, str, str]:
        del repo_root
        command = tuple(args)
        if command[:2] == ("merge-base", "--is-ancestor"):
            return 0, "", ""
        if command == ("branch", "--show-current"):
            return 0, "main", ""
        if command == ("rev-parse", "HEAD"):
            return 0, "a" * 40, ""
        if command == ("rev-parse", "origin/main"):
            return 0, "a" * 40, ""
        if command == ("status", "--porcelain=v1", "-uall"):
            return 0, "", ""
        raise AssertionError(f"unexpected git command: {command}")

    real_identity = authorization._identity

    def fake_identity(
        repo_root: Path,
        path: Path,
    ) -> authorization.ArtifactIdentity:
        expected = authorization.V4_ARTIFACT_IDENTITIES.get(path.as_posix())
        if expected is not None:
            sha256, size_bytes = expected
            return authorization.ArtifactIdentity(
                path=path.as_posix(),
                sha256=sha256,
                size_bytes=size_bytes,
            )
        return real_identity(repo_root, path)

    def valid_v4_implementation(repo_root: Path) -> dict[str, object]:
        del repo_root
        return {
            "status": ("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V4_IMPLEMENTATION_VALID")
        }

    def valid_v4_preexecution(repo_root: Path) -> dict[str, object]:
        del repo_root
        return {
            "status": "PREFLIGHT_V3_V4_PREEXECUTION_CONTRACT_VALID",
            "historical_receipt_backprojection_permitted": False,
            "runtime_execution_authorized": False,
            "next_expensive_execution_permitted": False,
        }

    monkeypatch.setattr(authorization, "_git", fake_git)
    monkeypatch.setattr(authorization, "_identity", fake_identity)
    monkeypatch.setattr(
        authorization,
        "validate_v4_implementation",
        valid_v4_implementation,
    )
    monkeypatch.setattr(
        authorization,
        "validate_v4_preexecution_contract",
        valid_v4_preexecution,
    )
    return tmp_path


def _generate(candidate_repo: Path) -> None:
    authorization.generate_record(candidate_repo)


def test_issuer_binds_exact_merged_v4_artifacts(candidate_repo: Path) -> None:
    record = authorization.build_record(candidate_repo)

    observed = {
        item.path: (item.sha256, item.size_bytes) for item in record.implementation_artifacts
    }

    assert observed == authorization.V4_ARTIFACT_IDENTITIES
    assert record.bound_implementation_merge_commit == (authorization.IMPLEMENTATION_MERGE_COMMIT)
    assert record.live_authorization_issued is False


def test_generated_record_is_canonical(candidate_repo: Path) -> None:
    _generate(candidate_repo)

    result = authorization.validate_implementation(candidate_repo)
    payload = (candidate_repo / authorization.ISSUER_RECORD_PATH).read_bytes()

    assert result["status"] == ("FINAL_OFFLINE_VERIFIER_V4_EXECUTION_AUTHORIZATION_ISSUER_VALID")
    assert payload.endswith(b"\n")
    assert json.loads(payload)["live_authorization_issued"] is False


def test_v4_artifact_drift_fails_closed(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drifted_path = "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v4.ipynb"
    real_identity = authorization._identity

    def drifted_identity(
        repo_root: Path,
        path: Path,
    ) -> authorization.ArtifactIdentity:
        identity = real_identity(repo_root, path)
        if path.as_posix() == drifted_path:
            return authorization.ArtifactIdentity(
                path=identity.path,
                sha256="0" * 64,
                size_bytes=identity.size_bytes,
            )
        return identity

    monkeypatch.setattr(authorization, "_identity", drifted_identity)

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="bound V4 implementation artifact identity drifted",
    ):
        authorization.build_record(candidate_repo)


def test_execution_limits_prohibit_model_and_benchmark_work() -> None:
    limits = authorization.ExecutionLimits()

    assert limits.maximum_kaggle_sessions == 1
    assert limits.maximum_runtime_install_attempts == 1
    assert limits.maximum_native_import_closure_probes == 1
    assert limits.maximum_model_loads == 0
    assert limits.maximum_worker_starts == 0
    assert limits.maximum_model_requests == 0
    assert limits.maximum_benchmark_trajectory_requests == 0
    assert limits.maximum_external_network_requests == 0
    assert limits.maximum_hidden_retries == 0


def test_issue_requires_exact_operator_confirmation(candidate_repo: Path) -> None:
    _generate(candidate_repo)

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="exact operator confirmation phrase is required",
    ):
        authorization.issue_authorization(
            candidate_repo,
            issuer_merge_commit="a" * 40,
            operator_confirmation="wrong",
            authorization_window_minutes=180,
            now=datetime(2026, 8, 9, 10, 0, tzinfo=UTC),
        )


def test_issue_and_validate_live_authorization(candidate_repo: Path) -> None:
    _generate(candidate_repo)
    issued_at = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)

    issued = authorization.issue_authorization(
        candidate_repo,
        issuer_merge_commit="a" * 40,
        operator_confirmation=authorization.CONFIRMATION_PHRASE,
        authorization_window_minutes=180,
        now=issued_at,
    )
    live = authorization.validate_live_authorization(
        candidate_repo,
        now=issued_at + timedelta(minutes=1),
    )

    assert issued.pre_execution_compatibility_gate_validated is True
    assert issued.historical_receipt_backprojection_permitted is False
    assert issued.offline_verifier_v4_execution_authorized is True
    assert issued.model_execution_authorized is False
    assert issued.p5_p6_execution_authorized is False
    assert issued.expires_at == issued_at + timedelta(minutes=180)
    assert live["offline_verifier_v4_execution_authorized"] is True


def test_issue_fails_if_v4_preexecution_contract_drifts(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _generate(candidate_repo)

    def drifted_contract(repo_root: Path) -> dict[str, object]:
        del repo_root
        return {
            "status": "PREFLIGHT_V3_V4_PREEXECUTION_CONTRACT_INVALID",
            "historical_receipt_backprojection_permitted": False,
            "runtime_execution_authorized": False,
            "next_expensive_execution_permitted": False,
        }

    monkeypatch.setattr(
        authorization,
        "validate_v4_preexecution_contract",
        drifted_contract,
    )

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="V4 pre-execution compatibility status drifted",
    ):
        authorization.issue_authorization(
            candidate_repo,
            issuer_merge_commit="a" * 40,
            operator_confirmation=authorization.CONFIRMATION_PHRASE,
            authorization_window_minutes=180,
            now=datetime(2026, 8, 9, 10, 0, tzinfo=UTC),
        )


def test_expired_authorization_fails_closed(candidate_repo: Path) -> None:
    _generate(candidate_repo)
    issued_at = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)

    authorization.issue_authorization(
        candidate_repo,
        issuer_merge_commit="a" * 40,
        operator_confirmation=authorization.CONFIRMATION_PHRASE,
        authorization_window_minutes=60,
        now=issued_at,
    )

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="live authorization has expired",
    ):
        authorization.validate_live_authorization(
            candidate_repo,
            now=issued_at + timedelta(minutes=60),
        )


def test_consumption_closes_single_use_lifecycle(candidate_repo: Path) -> None:
    _generate(candidate_repo)
    issued_at = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)

    authorization.issue_authorization(
        candidate_repo,
        issuer_merge_commit="a" * 40,
        operator_confirmation=authorization.CONFIRMATION_PHRASE,
        authorization_window_minutes=180,
        now=issued_at,
    )
    receipt = authorization.consume_authorization(
        candidate_repo,
        outcome=authorization.TerminalOutcome.PASSED,
        saved_version_id=341100000,
        evidence_zip_sha256="b" * 64,
        now=issued_at + timedelta(minutes=20),
    )

    assert receipt.authorization_reusable is False
    assert receipt.offline_verifier_v4_execution_authorized is False

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="authorization already has a terminal receipt",
    ):
        authorization.validate_live_authorization(
            candidate_repo,
            now=issued_at + timedelta(minutes=21),
        )


def test_interrupted_consumption_allows_missing_saved_version(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)

    authorization.issue_authorization(
        candidate_repo,
        issuer_merge_commit="a" * 40,
        operator_confirmation=authorization.CONFIRMATION_PHRASE,
        authorization_window_minutes=180,
        now=issued_at,
    )
    receipt = authorization.consume_authorization(
        candidate_repo,
        outcome=authorization.TerminalOutcome.INTERRUPTED,
        saved_version_id=None,
        evidence_zip_sha256=None,
        now=issued_at + timedelta(minutes=5),
    )

    assert receipt.outcome is authorization.TerminalOutcome.INTERRUPTED
    assert receipt.saved_version_id is None
    assert receipt.evidence_zip_sha256 is None


def test_abandonment_closes_unused_authority(candidate_repo: Path) -> None:
    _generate(candidate_repo)
    issued_at = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)

    authorization.issue_authorization(
        candidate_repo,
        issuer_merge_commit="a" * 40,
        operator_confirmation=authorization.CONFIRMATION_PHRASE,
        authorization_window_minutes=180,
        now=issued_at,
    )
    receipt = authorization.abandon_authorization(
        candidate_repo,
        reason="operator cancelled before execution",
        now=issued_at + timedelta(minutes=2),
    )

    assert receipt.lifecycle == "ABANDONED"
    assert receipt.authorization_reusable is False
    assert receipt.offline_verifier_v4_execution_authorized is False
