from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_review as review_module,
)

FINAL_AUTHORIZATION_PATH = review_module.FINAL_AUTHORIZATION_PATH
NEXT_GATE = review_module.NEXT_GATE
REVIEW_ID = review_module.REVIEW_ID
REVIEW_PATH = review_module.REVIEW_PATH
SOURCE_MAIN_MERGE_COMMIT = review_module.SOURCE_MAIN_MERGE_COMMIT
AuthorizationReviewError = review_module.AuthorizationReviewError
FullABCLocalEnvironmentQualificationAuthorizationReview = (
    review_module.FullABCLocalEnvironmentQualificationAuthorizationReview
)
build_default_review = review_module.build_default_review
load_review = review_module.load_review
validate_repository_review_package = review_module.validate_repository_review_package
write_default_review = review_module.write_default_review

ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = ROOT / (
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_execution_authorization_review.py"
)
TEST_PATH = Path(__file__).resolve()
EXPECTED_REVIEW_SHA256 = "2709ea4c5c4f7d3ef404d16f500887c6ced4ae89fac5bfb2151fe22530c76e5a"


def _payload() -> dict[str, Any]:
    return build_default_review().model_dump(mode="json")


def test_default_review_is_deterministic() -> None:
    first = build_default_review()
    second = build_default_review()

    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()
    assert first.fingerprint() == EXPECTED_REVIEW_SHA256


def test_default_review_preserves_review_only_safety() -> None:
    review = build_default_review()

    assert review.decision == "APPROVED_FOR_AUTHORIZATION_PACKAGE_IMPLEMENTATION"
    assert review.next_gate == NEXT_GATE
    assert review.safety.final_authorization_generated is False
    assert review.safety.kaggle_session_started is False
    assert review.safety.gpu_execution_authorized is False
    assert review.safety.model_execution_performed is False
    assert review.safety.external_spend == 0


def test_final_authorization_remains_deferred() -> None:
    review = build_default_review()

    assert review.authorization_issuance.final_authorization_generated is False
    assert review.authorization_issuance.issuance_requires_separate_review is True
    assert review.authorization_issuance.operator_confirmation_required is True
    assert review.authorization_issuance.maximum_authorization_window_minutes == 240
    assert review.authorization_issuance.final_authorization_path == (
        FINAL_AUTHORIZATION_PATH.as_posix()
    )


def test_dataset_roles_are_exact_and_offline() -> None:
    decision = build_default_review().dataset_materialization

    assert decision.required_roles == (
        "harness_source",
        "model_artifacts",
        "vllm_wheel",
    )
    assert decision.exact_dataset_slug_required is True
    assert decision.exact_dataset_version_required is True
    assert decision.network_fallback_permitted is False
    assert decision.credentials_permitted is False
    assert decision.customer_data_permitted is False


def test_runtime_adapter_binding_is_fixed_but_not_created() -> None:
    adapter = build_default_review().runtime_adapter

    assert adapter.factory_path.endswith(":create_runtime_adapter")
    assert adapter.artifact_path.endswith("kaggle_runtime_adapter.py")
    assert adapter.typed_protocol_required is True
    assert adapter.loopback_only is True
    assert adapter.hidden_retries_permitted is False
    assert adapter.adapter_created_in_this_review is False


def test_authority_bindings_are_unique_and_sorted() -> None:
    review = build_default_review()
    identifiers = tuple(item.binding_id for item in review.authority_bindings)

    assert identifiers == tuple(sorted(identifiers))
    assert len(identifiers) == len(set(identifiers))
    assert len(identifiers) == 5


def test_implementation_artifacts_are_exact_and_sorted() -> None:
    review = build_default_review()
    identifiers = tuple(item.artifact_id for item in review.implementation_artifacts)

    assert identifiers == tuple(sorted(identifiers))
    assert len(identifiers) == 7
    assert all(
        item.operational_authority_created is False for item in review.implementation_artifacts
    )


def test_duplicate_authority_binding_is_rejected() -> None:
    payload = _payload()
    authorities = list(payload["authority_bindings"])
    authorities.append(authorities[0])
    payload["authority_bindings"] = authorities

    with pytest.raises(ValidationError, match="authority binding IDs must be unique"):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_unsafe_implementation_path_is_rejected() -> None:
    payload = _payload()
    artifacts = list(payload["implementation_artifacts"])
    first = dict(artifacts[0])
    first["path"] = "../unsafe.py"
    artifacts[0] = first
    payload["implementation_artifacts"] = artifacts

    with pytest.raises(ValidationError, match="implementation artifact paths must remain bounded"):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_dataset_role_drift_is_rejected() -> None:
    payload = _payload()
    dataset = dict(payload["dataset_materialization"])
    dataset["required_roles"] = ["harness_source", "vllm_wheel", "model_artifacts"]
    payload["dataset_materialization"] = dataset

    with pytest.raises(ValidationError, match="offline dataset roles drifted"):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_invalid_runtime_factory_path_is_rejected() -> None:
    payload = _payload()
    runtime_adapter = dict(payload["runtime_adapter"])
    runtime_adapter["factory_path"] = "unsafe factory"
    payload["runtime_adapter"] = runtime_adapter

    with pytest.raises(ValidationError, match="module:function syntax"):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_final_authorization_generation_is_rejected() -> None:
    payload = _payload()
    safety = dict(payload["safety"])
    safety["final_authorization_generated"] = True
    payload["safety"] = safety

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_request_budget_weakening_is_rejected() -> None:
    payload = _payload()
    issuance = dict(payload["authorization_issuance"])
    issuance["maximum_model_requests"] = 9
    payload["authorization_issuance"] = issuance

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_nonzero_external_spend_is_rejected() -> None:
    payload = _payload()
    issuance = dict(payload["authorization_issuance"])
    issuance["external_spend"] = 1
    payload["authorization_issuance"] = issuance

    with pytest.raises(ValidationError):
        FullABCLocalEnvironmentQualificationAuthorizationReview.model_validate(payload)


def test_write_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "review.json"

    written = write_default_review(path)
    loaded = load_review(path)

    assert path.read_text(encoding="utf-8") == written.canonical_json()
    assert loaded == written


def test_invalid_review_json_is_metadata_safe(tmp_path: Path) -> None:
    path = tmp_path / "review.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(AuthorizationReviewError) as caught:
        load_review(path)

    assert caught.value.error_code == "AUTHORIZATION_REVIEW_INVALID"
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
    authority_path.write_text('{"state":"historical"}\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "authority.json"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "historical authority"],
        check=True,
    )
    historical_commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    historical_blob = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD:authority.json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    authority_path.write_text('{"state":"current"}\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "authority.json"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "later legitimate change"],
        check=True,
    )

    observed_blob = review_module._git_blob_sha(
        repo,
        Path("authority.json"),
        revision=historical_commit,
    )
    observed_payload = review_module._load_json_object_at_revision(
        repo,
        Path("authority.json"),
        revision=historical_commit,
    )

    assert observed_blob == historical_blob
    assert observed_payload == {"state": "historical"}


def test_expected_identifiers_are_stable() -> None:
    assert REVIEW_ID.endswith("authorization-review-v1")
    assert REVIEW_PATH.as_posix().endswith("execution_authorization_review_v1.json")
    assert SOURCE_MAIN_MERGE_COMMIT == "768e0535d8d373385440acc2dc18952b4fc42325"


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


def test_committed_review_matches_builder() -> None:
    committed_path = ROOT / REVIEW_PATH
    if not committed_path.exists():
        pytest.skip("full repository review artifact is unavailable")

    committed = load_review(committed_path)
    assert committed == build_default_review()


def test_repository_review_package_matches_exact_pr_104_authorities() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("full Git checkout is unavailable")

    summary = validate_repository_review_package(ROOT)

    assert summary["review_sha256"] == EXPECTED_REVIEW_SHA256
    assert summary["final_authorization_generated"] is False
    assert summary["dataset_materialization_performed"] is False
    assert summary["runtime_adapter_generated"] is False
    assert summary["kaggle_session_started"] is False
    assert summary["maximum_model_requests"] == 8
    assert summary["benchmark_trajectory_requests_permitted"] == 0
    assert summary["external_spend"] == 0
