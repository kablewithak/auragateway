"""Tests for the P5/P6 mechanism-admission successor design."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p5_p6_mechanism_admission_successor_design_v1 as subject,
)


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.V2_RECORD_PATH,
        subject.V2_SOURCE_PATH,
        subject.V2_TEMPLATE_PATH,
        subject.V2_TEST_PATH,
        subject.C4_CONTRACT_PATH,
        subject.C4_ASSESSMENT_PATH,
        subject.C4_REVIEW_PATH,
        *subject.STATIC_PATHS,
    )
    for relative in required:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.STATIC_PATHS) == 5
    assert len(subject.GENERATED_PATHS) == 2
    assert len(subject.CANDIDATE_PATHS) == 7
    assert set(subject.CANDIDATE_PATHS) == {
        *subject.STATIC_PATHS,
        *subject.GENERATED_PATHS,
    }


def test_design_binds_current_scientific_state(tmp_path: Path) -> None:
    design = subject.build_design(_fixture_repo(tmp_path))

    assert design.c4_semantic_state == "NOT_QUALIFIED"
    assert design.c4_mechanism_admission == "QUALIFIED"
    assert design.p5_requalified is False
    assert design.p6_requalified is False
    assert design.runtime_execution_authorized is False
    assert design.model_requests_performed == 0
    assert design.gpu_execution_performed is False
    assert design.kaggle_execution_performed is False


def test_semantic_observation_is_diagnostic_only(tmp_path: Path) -> None:
    design = subject.build_design(_fixture_repo(tmp_path))
    semantic = design.semantic_boundary

    assert semantic.states == (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    assert semantic.exact_object_match_blocks_mechanism is False
    assert semantic.valid_json_blocks_mechanism is False
    assert semantic.semantic_parser_may_raise_on_model_content is False
    assert semantic.output_digest_required is True
    assert semantic.raw_output_logging_permitted is False


def test_mechanism_admission_still_fails_closed(tmp_path: Path) -> None:
    boundary = subject.build_design(_fixture_repo(tmp_path)).mechanism_boundary

    assert boundary.http_success_required is True
    assert boundary.response_envelope_required is True
    assert boundary.finish_reason_stop_required is True
    assert boundary.prompt_token_count_required is True
    assert boundary.completion_token_budget_required is True
    assert boundary.request_identity_required is True
    assert boundary.token_identity_required is True
    assert boundary.metric_window_required is True
    assert boundary.output_provenance_required is True
    assert boundary.hidden_retries_required_zero is True
    assert boundary.worker_identity_required is True
    assert boundary.teardown_required is True


def test_p5_and_p6_acceptance_are_not_relaxed(tmp_path: Path) -> None:
    design = subject.build_design(_fixture_repo(tmp_path))

    assert design.p5_boundary.semantic_state_used_as_cache_proof is False
    assert design.p5_boundary.latency_as_primary_proof_permitted is False
    assert design.p5_boundary.cold_zero_local_cache_hit_required is True
    assert design.p5_boundary.warm_positive_local_cache_hit_required is True
    assert design.p5_boundary.negative_prefix_bound_required is True
    assert design.p5_boundary.post_reset_zero_local_cache_hit_required is True
    assert design.p5_boundary.cross_worker_zero_inherited_cache_required is True
    assert design.p5_boundary.external_kv_transfer_zero_required is True

    assert design.p6_boundary.model_semantics_used_as_route_proof is False
    assert design.p6_boundary.disjoint_process_trees_required is True
    assert design.p6_boundary.route_metric_window_attribution_required is True
    assert design.p6_boundary.no_hidden_fallback_required is True
    assert design.p6_boundary.cross_worker_cold_state_required is True
    assert design.p6_boundary.worker_1_retention_required is True
    assert design.p6_boundary.request_count_reconciliation_required is True
    assert design.p6_boundary.teardown_required is True


def test_successor_requires_fresh_authorization_scope(tmp_path: Path) -> None:
    authorization = subject.build_design(_fixture_repo(tmp_path)).authorization

    assert authorization.predecessor_v2_authorization_reusable is False
    assert authorization.new_scope_required == subject.NEW_AUTHORIZATION_SCOPE
    assert authorization.design_issues_authorization is False
    assert authorization.implementation_issues_authorization is False
    assert authorization.single_use_required is True
    assert authorization.hidden_retries_permitted == 0


def test_implementation_changes_include_downstream_effects(tmp_path: Path) -> None:
    design = subject.build_design(_fixture_repo(tmp_path))
    changes = {item.change_id: item for item in design.implementation_changes}

    assert set(changes) == {"MC-01", "MC-02", "MC-03", "MC-04", "MC-05"}
    assert changes["MC-02"].target == "validate_structured_response"
    assert changes["MC-03"].target == "run_structured_request"
    assert changes["MC-05"].target == "execution authorization boundary"
    assert all(item.downstream_effects for item in changes.values())


def test_generation_round_trip_is_deterministic(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.generate(repo_root)
    first_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}
    validated = subject.validate(repo_root)
    second = subject.generate(repo_root)
    second_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}

    assert first == validated == second
    assert first_bytes == second_bytes
    assert first.review.status == "APPROVED_FOR_IMPLEMENTATION"
    assert first.review.p5_acceptance_relaxed is False
    assert first.review.p6_acceptance_relaxed is False
    assert first.review.new_execution_authorized is False


def test_generated_artifact_drift_fails_closed(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    design_path = repo_root / subject.DESIGN_PATH
    design_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        subject.DesignError,
        match="generated design artifact differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_c4_authority_drift_fails_closed(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    review_path = repo_root / subject.C4_REVIEW_PATH
    review_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        subject.DesignError,
        match="C4 mechanism-admission review binding drifted",
    ):
        subject.build_design(repo_root)
