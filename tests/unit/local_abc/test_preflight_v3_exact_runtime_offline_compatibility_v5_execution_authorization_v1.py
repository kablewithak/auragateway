from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    preflight_v3_exact_runtime_offline_compatibility_v5_execution_authorization_v1,
)

authorization = preflight_v3_exact_runtime_offline_compatibility_v5_execution_authorization_v1


@pytest.fixture
def candidate_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    source_root = Path(__file__).resolve().parents[3]

    for relative in (
        authorization.ISSUER_SOURCE_PATH,
        authorization.ISSUER_TEST_PATH,
        authorization.ISSUER_RUNBOOK_PATH,
    ):
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
        if command[:2] == (
            "merge-base",
            "--is-ancestor",
        ):
            return 0, "", ""
        if command == (
            "branch",
            "--show-current",
        ):
            return 0, "main", ""
        if command == (
            "rev-parse",
            "HEAD",
        ):
            return 0, "a" * 40, ""
        if command == (
            "rev-parse",
            "origin/main",
        ):
            return 0, "a" * 40, ""
        if command == (
            "status",
            "--porcelain=v1",
            "-uall",
        ):
            return 0, "", ""
        raise AssertionError(f"unexpected git command: {command}")

    real_identity = authorization._identity

    def fake_identity(
        repo_root: Path,
        path: Path,
    ) -> authorization.ArtifactIdentity:
        expected = authorization.V5_ARTIFACT_IDENTITIES.get(path.as_posix())
        if expected is not None:
            sha256, size_bytes = expected
            return authorization.ArtifactIdentity(
                path=path.as_posix(),
                sha256=sha256,
                size_bytes=size_bytes,
            )
        return real_identity(
            repo_root,
            path,
        )

    def valid_v5() -> dict[str, object]:
        return {
            "status": ("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V5_IMPLEMENTATION_VALID"),
            "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
            "semantic_decisions_reading_stdout_excerpt": 0,
            "semantic_decisions_reading_stderr_excerpt": 0,
            "lossy_transformations_before_semantic_decision": 0,
            "truncation_before_semantic_decision": 0,
            "statically_predictable_successor_failures": 0,
            "exact_runtime_offline_verified": False,
            "p5_p6_exact_runtime_requalified": False,
            "runtime_execution_authorized": False,
            "pilot_execution_authorized": False,
            "final_measured_abc_execution_authorized": False,
            "next_kaggle_execution_authorized": False,
            "next_gate": ("implement_single_use_final_offline_verifier_v5_execution_authorization"),
        }

    monkeypatch.setattr(
        authorization,
        "_git",
        fake_git,
    )
    monkeypatch.setattr(
        authorization,
        "_identity",
        fake_identity,
    )
    monkeypatch.setattr(
        authorization,
        "_run_v5_validation",
        lambda repo_root: valid_v5(),
    )

    return tmp_path


def _generate(candidate_repo: Path) -> None:
    authorization.generate_record(candidate_repo)


def test_issuer_binds_exact_merged_v5_artifacts(
    candidate_repo: Path,
) -> None:
    record = authorization.build_record(candidate_repo)

    observed = {
        item.path: (
            item.sha256,
            item.size_bytes,
        )
        for item in record.implementation_artifacts
    }

    assert observed == authorization.V5_ARTIFACT_IDENTITIES
    assert record.bound_implementation_feature_commit == authorization.IMPLEMENTATION_FEATURE_COMMIT
    assert record.bound_implementation_merge_commit == authorization.IMPLEMENTATION_MERGE_COMMIT
    assert record.live_authorization_issued is False
    assert record.next_kaggle_execution_authorized is False


def test_generated_record_is_canonical(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)

    result = authorization.validate_implementation(candidate_repo)
    payload = (candidate_repo / authorization.ISSUER_RECORD_PATH).read_bytes()

    assert result["status"] == ("FINAL_OFFLINE_VERIFIER_V5_EXECUTION_AUTHORIZATION_ISSUER_VALID")
    assert payload.endswith(b"\n")
    assert json.loads(payload)["live_authorization_issued"] is False


def test_execution_limits_are_capability_only() -> None:
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
    assert limits.maximum_external_spend == 0


def test_issue_requires_exact_confirmation(
    candidate_repo: Path,
) -> None:
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
            now=datetime(
                2026,
                8,
                9,
                14,
                0,
                tzinfo=UTC,
            ),
        )


def test_issue_revalidates_semantic_contract(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _generate(candidate_repo)

    monkeypatch.setattr(
        authorization,
        "_run_v5_validation",
        lambda repo_root: {
            "status": ("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V5_IMPLEMENTATION_VALID"),
            "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
            "semantic_decisions_reading_stdout_excerpt": 1,
            "semantic_decisions_reading_stderr_excerpt": 0,
            "lossy_transformations_before_semantic_decision": 0,
            "truncation_before_semantic_decision": 0,
            "statically_predictable_successor_failures": 0,
            "exact_runtime_offline_verified": False,
            "p5_p6_exact_runtime_requalified": False,
            "runtime_execution_authorized": False,
            "pilot_execution_authorized": False,
            "final_measured_abc_execution_authorized": False,
            "next_kaggle_execution_authorized": False,
            "next_gate": ("implement_single_use_final_offline_verifier_v5_execution_authorization"),
        },
    )

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="pre-execution implementation contract drifted",
    ):
        authorization.issue_authorization(
            candidate_repo,
            issuer_merge_commit="a" * 40,
            operator_confirmation=authorization.CONFIRMATION_PHRASE,
            authorization_window_minutes=180,
            now=datetime(
                2026,
                8,
                9,
                14,
                0,
                tzinfo=UTC,
            ),
        )


def test_issue_and_validate_live_authorization(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(
        2026,
        8,
        9,
        14,
        0,
        tzinfo=UTC,
    )

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

    assert issued.v5_implementation_validated is True
    assert issued.semantic_channel_contract_validated is True
    assert issued.operator_attested_platform == "T4_X2"
    assert issued.operator_attested_gpu_count == 2
    assert issued.operator_attested_internet_enabled is False
    assert issued.offline_verifier_v5_execution_authorized is True
    assert issued.model_execution_authorized is False
    assert issued.p5_p6_execution_authorized is False
    assert issued.expires_at == issued_at + timedelta(minutes=180)
    assert live["offline_verifier_v5_execution_authorized"] is True


def test_expired_authorization_fails_closed(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(
        2026,
        8,
        9,
        14,
        0,
        tzinfo=UTC,
    )

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


def test_lifecycle_artifact_prevents_second_issue(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(
        2026,
        8,
        9,
        14,
        0,
        tzinfo=UTC,
    )

    authorization.issue_authorization(
        candidate_repo,
        issuer_merge_commit="a" * 40,
        operator_confirmation=authorization.CONFIRMATION_PHRASE,
        authorization_window_minutes=180,
        now=issued_at,
    )

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="authorization artifact already exists",
    ):
        authorization.issue_authorization(
            candidate_repo,
            issuer_merge_commit="a" * 40,
            operator_confirmation=authorization.CONFIRMATION_PHRASE,
            authorization_window_minutes=180,
            now=issued_at + timedelta(minutes=1),
        )


def test_consumption_closes_single_use_lifecycle(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(
        2026,
        8,
        9,
        14,
        0,
        tzinfo=UTC,
    )

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
        saved_version_id=341300000,
        evidence_zip_sha256="b" * 64,
        now=issued_at + timedelta(minutes=20),
    )

    assert receipt.authorization_reusable is False
    assert receipt.offline_verifier_v5_execution_authorized is False

    with pytest.raises(
        authorization.AuthorizationIssuerError,
        match="authorization already has a terminal receipt",
    ):
        authorization.validate_live_authorization(
            candidate_repo,
            now=issued_at + timedelta(minutes=21),
        )


def test_terminal_outcome_requires_evidence() -> None:
    with pytest.raises(
        ValueError,
        match="terminal executed outcome requires saved version id",
    ):
        authorization.AuthorizationConsumption(
            consumption_id=authorization.CONSUMPTION_ID,
            authorization_id=authorization.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            lifecycle="CONSUMED",
            outcome=authorization.TerminalOutcome.FAILED,
            consumed_at=datetime.now(UTC),
            saved_version_id=None,
            evidence_zip_sha256=None,
            authorization_reusable=False,
            offline_verifier_v5_execution_authorized=False,
            model_execution_authorized=False,
            p5_p6_execution_authorized=False,
            pilot_execution_authorized=False,
            final_measured_abc_execution_authorized=False,
            next_gate=authorization.NEXT_GATE_AFTER_CONSUMPTION,
        )


def test_interrupted_consumption_allows_missing_evidence(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(
        2026,
        8,
        9,
        14,
        0,
        tzinfo=UTC,
    )

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

    assert receipt.saved_version_id is None
    assert receipt.evidence_zip_sha256 is None


def test_abandonment_closes_unused_authority(
    candidate_repo: Path,
) -> None:
    _generate(candidate_repo)
    issued_at = datetime(
        2026,
        8,
        9,
        14,
        0,
        tzinfo=UTC,
    )

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
    assert receipt.offline_verifier_v5_execution_authorized is False
