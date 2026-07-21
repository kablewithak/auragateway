from __future__ import annotations

import hashlib
import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

review_module: Any = importlib.import_module(
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_execution_authorization_issuance_review"
)

FINAL_AUTHORIZATION_PATH = review_module.FINAL_AUTHORIZATION_PATH
HARNESS_SOURCE_COMMIT = review_module.HARNESS_SOURCE_COMMIT
NEXT_GATE = review_module.NEXT_GATE
REVIEW_ID = review_module.REVIEW_ID
REVIEW_PATH = review_module.REVIEW_PATH
SOURCE_MAIN_MERGE_COMMIT = review_module.SOURCE_MAIN_MERGE_COMMIT
AuthorizationIssuanceReviewError = review_module.AuthorizationIssuanceReviewError
FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview = (
    review_module.FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview
)
_git_file_sha256 = review_module._git_file_sha256
build_default_review = review_module.build_default_review
load_review = review_module.load_review
validate_repository_review_package = review_module.validate_repository_review_package
write_default_review = review_module.write_default_review

ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = ROOT / (
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_execution_authorization_issuance_review.py"
)
TEST_PATH = Path(__file__).resolve()
EXPECTED_REVIEW_SHA256 = "73e9a4f0642cce40ce6bc6ef875ee13ab81900f0bc7e768e0c4a9a6b6f0ec859"
EXPECTED_REVIEW_GIT_BLOB_SHA = "61590be7fe1d10e8e9b38405cf634f4a0cae3e31"


def _payload() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        build_default_review().model_dump(mode="json"),
    )


def test_historical_request_model_is_detached_from_current_execution_hash() -> None:
    authorization_module = importlib.import_module(
        "auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization"
    )
    payload = authorization_module.build_qualification_authorization_request().model_dump(
        mode="json"
    )
    payload["execution_request_sha256"] = (
        "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
    )

    historical = review_module.HistoricalQualificationAuthorizationRequest.model_validate(payload)

    assert historical.execution_request_sha256 == (
        "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
    )
    with pytest.raises(ValidationError):
        review_module.auth_contracts.QualificationAuthorizationRequest.model_validate(payload)


def test_default_review_is_deterministic() -> None:
    first = build_default_review()
    second = build_default_review()

    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()
    assert first.fingerprint() == EXPECTED_REVIEW_SHA256


def test_review_approves_implementation_only() -> None:
    review = build_default_review()

    assert review.decision == "APPROVED_FOR_AUTHORIZATION_ISSUANCE_IMPLEMENTATION"
    assert review.next_gate == NEXT_GATE
    assert review.lifecycle_before == "LOCALLY_VALIDATED"
    assert review.lifecycle_after == "LOCALLY_VALIDATED"
    assert review.authorization_issuance.final_authorization_generated is False
    assert review.authorization_issuance.issuance_decision_deferred is True
    assert review.safety.authorization_issuance_performed is False
    assert review.safety.gpu_execution_authorized is False
    assert review.safety.kaggle_session_started is False


def test_source_and_harness_commits_are_exact() -> None:
    review = build_default_review()

    assert review.source_main_merge_commit == SOURCE_MAIN_MERGE_COMMIT
    assert review.harness_source_commit == HARNESS_SOURCE_COMMIT
    assert SOURCE_MAIN_MERGE_COMMIT == "58e448228abcf9b83e1a6d165094bbec61dcf02c"
    assert HARNESS_SOURCE_COMMIT == "4dfd799590195d842f2382bb882fba9b8c4e2422"


def test_materialization_binding_is_exact_and_offline() -> None:
    binding = build_default_review().materialization

    assert binding.materialization_record_sha256 == (
        "705881978f5a612a4bc1d131fdc96508fd8fb4a78c73e384df6968eb54bbb7a3"
    )
    assert binding.runtime_manifest_sha256 == (
        "ddc1e1fc9e5ba61212dafad8d7196eb17699b6103083b6f9678dce83ca0a74c2"
    )
    assert tuple(item.role for item in binding.entries) == (
        "harness_source",
        "model_artifacts",
        "vllm_wheel",
    )
    assert tuple(item.kaggle_dataset_version for item in binding.entries) == (1, 1, 1)
    assert binding.network_access_permitted is False
    assert binding.credentials_present is False
    assert binding.customer_data_present is False
    assert binding.hosted_provider_inputs_present is False


def test_runtime_factory_binding_is_exact_and_unexecuted() -> None:
    runtime = build_default_review().runtime_factory

    assert runtime.artifact_git_blob_sha == "2f832c487e338d6233fa774dc6a4069f31cfcc30"
    assert runtime.artifact_sha256 == (
        "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
    )
    assert runtime.factory_path.endswith(":create_runtime_adapter")
    assert runtime.protocol_path.endswith(":QualificationRuntimeAdapter")
    assert runtime.loopback_only is True
    assert runtime.model_request_retries_permitted is False
    assert runtime.network_fallback_permitted is False
    assert runtime.adapter_execution_performed is False


def test_budget_and_privacy_envelopes_are_fail_closed() -> None:
    review = build_default_review()

    assert review.budget.maximum_authorization_window_minutes == 240
    assert review.budget.maximum_kaggle_sessions == 1
    assert review.budget.maximum_workers == 2
    assert review.budget.maximum_model_requests == 8
    assert review.budget.maximum_output_tokens_per_request == 32
    assert review.budget.benchmark_trajectory_requests_permitted == 0
    assert review.budget.external_spend == 0
    assert review.privacy.network_access_permitted is False
    assert review.privacy.credentials_permitted is False
    assert review.privacy.customer_data_permitted is False
    assert review.privacy.hosted_provider_calls_permitted is False


def test_final_authorization_binding_remains_deferred() -> None:
    decision = build_default_review().authorization_issuance

    assert decision.final_authorization_path == FINAL_AUTHORIZATION_PATH.as_posix()
    assert decision.operator_confirmation_required is True
    assert decision.issued_at_deferred_to_operator_confirmation is True
    assert decision.expires_at_limited_by_review_budget is True
    assert decision.issuance_review_git_blob_sha_required is True
    assert decision.measured_execution_authorized is False


def test_authority_bindings_are_exact_unique_and_sorted() -> None:
    bindings = build_default_review().authority_bindings
    identifiers = tuple(item.binding_id for item in bindings)

    assert identifiers == tuple(sorted(identifiers))
    assert len(identifiers) == len(set(identifiers))
    assert len(identifiers) == 10


def test_implementation_artifacts_are_exact_unique_and_sorted() -> None:
    artifacts = build_default_review().implementation_artifacts
    identifiers = tuple(item.artifact_id for item in artifacts)

    assert identifiers == tuple(sorted(identifiers))
    assert len(identifiers) == len(set(identifiers))
    assert len(identifiers) == 6
    assert all(item.created_in_this_review is False for item in artifacts)
    assert all(item.operational_authority_created_in_this_review is False for item in artifacts)


def test_duplicate_authority_binding_is_rejected() -> None:
    payload = _payload()
    authorities = list(payload["authority_bindings"])
    authorities.insert(1, authorities[0])
    payload["authority_bindings"] = authorities

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_materialization_entry_drift_is_rejected() -> None:
    payload = _payload()
    materialization = dict(payload["materialization"])
    entries = list(materialization["entries"])
    first = dict(entries[0])
    first["sha256"] = "0" * 64
    entries[0] = first
    materialization["entries"] = entries
    payload["materialization"] = materialization

    with pytest.raises(ValidationError, match="materialization entry bindings drifted"):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_runtime_adapter_identity_drift_is_rejected() -> None:
    payload = _payload()
    runtime_factory = dict(payload["runtime_factory"])
    runtime_factory["artifact_sha256"] = "0" * 64
    payload["runtime_factory"] = runtime_factory

    with pytest.raises(ValidationError, match="runtime adapter SHA-256 drifted"):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_request_budget_weakening_is_rejected() -> None:
    payload = _payload()
    budget = dict(payload["budget"])
    budget["maximum_model_requests"] = 9
    payload["budget"] = budget

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_network_access_is_rejected() -> None:
    payload = _payload()
    privacy = dict(payload["privacy"])
    privacy["network_access_permitted"] = True
    payload["privacy"] = privacy

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_implementation_artifact_drift_is_rejected() -> None:
    payload = _payload()
    artifacts = list(payload["implementation_artifacts"])
    first = dict(artifacts[0])
    first["path"] = "docs/runbooks/unsafe.md"
    artifacts[0] = first
    payload["implementation_artifacts"] = artifacts

    with pytest.raises(
        ValidationError,
        match="authorization-issuance implementation artifacts drifted",
    ):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_final_authorization_generation_is_rejected() -> None:
    payload = _payload()
    issuance = dict(payload["authorization_issuance"])
    issuance["final_authorization_generated"] = True
    payload["authorization_issuance"] = issuance

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationIssuanceReview.model_validate(payload)


def test_write_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "review.json"

    written = write_default_review(path)
    loaded = load_review(path)

    assert path.read_text(encoding="utf-8") == written.canonical_json()
    assert loaded == written


def test_invalid_review_json_is_metadata_safe(tmp_path: Path) -> None:
    path = tmp_path / "review.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(AuthorizationIssuanceReviewError) as caught:
        load_review(path)

    assert caught.value.error_code == "AUTHORIZATION_ISSUANCE_REVIEW_INVALID"
    assert caught.value.path == path.as_posix()


def test_historical_authority_resolution_ignores_later_commits(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "tests@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "AuraGateway Tests"],
        check=True,
    )

    authority_path = repo / "authority.json"
    authority_path.write_text('{"state":"pr109"}\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "authority.json"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "PR 109 authority"],
        check=True,
    )
    source_commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    source_blob = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD:authority.json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    authority_path.write_text('{"state":"later"}\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "authority.json"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "later change"],
        check=True,
    )

    observed_blob = review_module._git_blob_sha(
        repo,
        Path("authority.json"),
        revision=source_commit,
    )
    observed_payload = review_module._load_json_object_at_revision(
        repo,
        Path("authority.json"),
        revision=source_commit,
    )

    assert observed_blob == source_blob
    assert observed_payload == {"state": "pr109"}


def test_expected_identifiers_are_stable() -> None:
    assert REVIEW_ID.endswith("authorization-issuance-review-v1")
    assert REVIEW_PATH.as_posix().endswith("execution_authorization_issuance_review_v1.json")
    assert FINAL_AUTHORIZATION_PATH.as_posix().endswith("execution_authorization_v1.json")
    assert EXPECTED_REVIEW_GIT_BLOB_SHA == "61590be7fe1d10e8e9b38405cf634f4a0cae3e31"


def test_expected_ruff_version_matches_local_tool() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "ruff 0.15.21"


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    failures: list[str] = []
    for path in (SOURCE_PATH, TEST_PATH):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if len(line) > 100:
                failures.append(f"{path.as_posix()}:{line_number}:{len(line)}")

    assert failures == []


def test_git_file_sha256_reads_bound_revision_not_working_tree(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "AuraGateway Tests"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    authority_path = repo_root / "authority.json"
    historical_bytes = b'{"status":"historical"}\n'
    authority_path.write_bytes(historical_bytes)
    subprocess.run(
        ["git", "add", "authority.json"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "test: freeze authority"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    authority_path.write_text(
        '{"status":"superseded"}\n',
        encoding="utf-8",
    )

    assert (
        _git_file_sha256(
            repo_root,
            Path("authority.json"),
            revision=revision,
        )
        == hashlib.sha256(historical_bytes).hexdigest()
    )
    assert hashlib.sha256(authority_path.read_bytes()).hexdigest() != (
        hashlib.sha256(historical_bytes).hexdigest()
    )


def test_committed_review_matches_builder() -> None:
    committed_path = ROOT / REVIEW_PATH
    if not committed_path.exists():
        pytest.skip("full repository review artifact is unavailable")

    committed = load_review(committed_path)
    assert committed == build_default_review()
    assert committed.fingerprint() == EXPECTED_REVIEW_SHA256


def test_repository_review_package_matches_exact_pr109_authorities() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("full Git checkout is unavailable")

    summary = validate_repository_review_package(ROOT)

    assert summary["review_sha256"] == EXPECTED_REVIEW_SHA256
    assert summary["source_main_merge_commit"] == SOURCE_MAIN_MERGE_COMMIT
    assert summary["harness_source_commit"] == HARNESS_SOURCE_COMMIT
    assert summary["materialization_record_sha256"] == (
        "705881978f5a612a4bc1d131fdc96508fd8fb4a78c73e384df6968eb54bbb7a3"
    )
    assert summary["runtime_manifest_sha256"] == (
        "ddc1e1fc9e5ba61212dafad8d7196eb17699b6103083b6f9678dce83ca0a74c2"
    )
    assert summary["runtime_adapter_sha256"] == (
        "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
    )
    assert summary["maximum_authorization_window_minutes"] == 240
    assert summary["maximum_kaggle_sessions"] == 1
    assert summary["maximum_workers"] == 2
    assert summary["maximum_model_requests"] == 8
    assert summary["maximum_output_tokens_per_request"] == 32
    assert summary["benchmark_trajectory_requests_permitted"] == 0
    assert summary["network_access_permitted"] is False
    assert summary["customer_data_permitted"] is False
    assert summary["credentials_permitted"] is False
    assert summary["external_spend"] == 0
    assert summary["final_authorization_generated"] is False
    assert summary["authorization_issuance_performed"] is False
    assert summary["kaggle_session_started"] is False
    assert summary["lifecycle_after"] == "LOCALLY_VALIDATED"
    assert summary["next_gate"] == NEXT_GATE
