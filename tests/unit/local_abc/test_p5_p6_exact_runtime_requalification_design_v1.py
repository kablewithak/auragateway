from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import p5_p6_exact_runtime_requalification_design_v1

design = p5_p6_exact_runtime_requalification_design_v1


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = (
        design.V5_ACCEPTANCE_RECORD_PATH,
        design.RUNTIME_LOCK_PATH,
        design.V5_SEMANTIC_BOUNDARY_PATH,
        design.HISTORICAL_P5_P6_ACCEPTANCE_PATH,
        design.HISTORICAL_P5_P6_REVIEW_PATH,
        design.HISTORICAL_HARNESS_PATH,
        design.HISTORICAL_TEMPLATE_PATH,
    )
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    return tmp_path


def test_authorities_separate_current_from_historical_precedent(candidate_repo: Path) -> None:
    authorities = design.validate_authorities(candidate_repo)

    current = {item.role for item in authorities if item.authority_scope == "CURRENT"}
    precedent = {
        item.role for item in authorities if item.authority_scope == "DESIGN_PRECEDENT_ONLY"
    }

    assert current == {
        "accepted_exact_runtime_capability",
        "accepted_exact_runtime_resolution",
        "accepted_semantic_boundary",
    }
    assert precedent == {
        "historical_governed_p5_p6_acceptance",
        "historical_governed_p5_p6_review",
        "historical_p5_p6_harness",
        "historical_p5_p6_runtime_template",
    }


def test_runtime_lineage_is_exact_current_line(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.runtime.torch == "2.11.0+cu129"
    assert record.runtime.vllm_distribution == "0.25.1+cu129"
    assert record.runtime.vllm_public_semantic_version == "0.25.1"
    assert record.runtime.gpu_topology == "T4_x2"
    assert record.historical_p5_p6_current_authority is False


def test_exact_metric_semantics_cover_current_vllm_sources(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)
    semantics = record.exact_runtime_semantics
    by_role = {item.semantic_role: item for item in semantics.metrics}

    assert semantics.source_tag == "v0.25.1"
    assert semantics.prompt_source_labels == (
        "local_compute",
        "local_cache_hit",
        "external_kv_transfer",
    )
    assert by_role["prefix_cache_hits"].prometheus_sample == "vllm:prefix_cache_hits_total"
    assert by_role["local_cache_hit"].prometheus_sample == ("vllm:prompt_tokens_by_source_total")
    assert "source=local_cache_hit" in by_role["local_cache_hit"].required_labels
    assert by_role["newly_computed_prefill_tokens"].prometheus_sample == (
        "vllm:request_prefill_kv_computed_tokens_sum"
    )


def test_request_plan_is_six_requests_three_worker_starts(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert [item.role for item in record.request_plan] == [
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    ]
    assert record.execution_budget.maximum_model_requests == 6
    assert record.execution_budget.maximum_worker_starts == 3
    assert record.execution_budget.maximum_model_loads == 3
    assert record.execution_budget.hidden_retries_permitted == 0


def test_p5_has_all_required_controls_and_ambiguous_state(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.p5.positive_control.startswith("same worker generation")
    assert record.p5.negative_prefix_control.startswith("same worker generation")
    assert record.p5.negative_worker_control.startswith("independent worker generation")
    assert record.p5.reset_control == "full process restart + new worker generation"
    assert record.p5.latency_as_primary_proof_permitted is False
    assert record.p5.external_kv_transfer_permitted is False
    assert design.BehaviorStatus.AMBIGUOUS in record.decision_states
    assert len(record.p5.ambiguous_criteria) >= 4


def test_p6_requires_route_realization_and_state_isolation(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert "intended_route" in record.p6.required_identity_dimensions
    assert "realized_route" in record.p6.required_identity_dimensions
    assert "worker_generation" in record.p6.required_identity_dimensions
    assert "metric_endpoint_identity" in record.p6.required_identity_dimensions
    assert record.p6.fallback_permitted is False
    assert record.p6.hidden_restart_permitted is False
    assert record.p6.model_semantics_as_route_proof_permitted is False


def test_token_identity_is_server_tokenized_not_string_hash_only(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.token_identity.server_tokenize_endpoint_required is True
    assert record.token_identity.reusable_prefix_token_ids_required is True
    assert record.token_identity.cacheable_common_prefix_bound_required is True
    assert record.token_identity.b_c_reusable_prefix_token_identity_equal is True
    assert record.token_identity.string_hash_alone_sufficient is False


def test_semantic_boundary_preserves_v5_invariant(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)
    boundary = record.semantic_boundary

    assert boundary.public_evidence_invariant == design.PUBLIC_EVIDENCE_INVARIANT
    assert boundary.public_evidence_used_as_semantic_input is False
    assert boundary.lossy_transformations_before_semantic_decision == 0
    assert boundary.truncation_before_semantic_decision == 0
    assert boundary.evidence_projection_terminal is True


def test_failure_taxonomy_is_complete(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert tuple(record.failure_taxonomy) == tuple(design.FailureCode)
    assert design.FailureCode.METRIC_ATTRIBUTION_AMBIGUOUS in record.failure_taxonomy
    assert design.FailureCode.P6_STATE_ISOLATION_FAILURE in record.failure_taxonomy
    assert design.FailureCode.TEARDOWN_FAILURE in record.failure_taxonomy


def test_design_is_execution_inert(candidate_repo: Path) -> None:
    record = design.build_design_record(candidate_repo)

    assert record.safety.runtime_execution_authorized is False
    assert record.safety.pilot_execution_authorized is False
    assert record.safety.final_measured_abc_execution_authorized is False
    assert record.safety.gpu_execution_performed is False
    assert record.safety.model_loaded is False
    assert record.safety.worker_started is False
    assert record.safety.model_requests_performed == 0


def test_generate_and_validate_are_byte_deterministic(candidate_repo: Path) -> None:
    generated = design.generate(candidate_repo)
    first = (candidate_repo / design.RECORD_PATH).read_bytes()

    validated = design.validate_generated(candidate_repo)
    second = (candidate_repo / design.RECORD_PATH).read_bytes()

    assert generated == validated
    assert first == second
    parsed = json.loads(first)
    assert parsed["design_status"] == "DESIGN_FROZEN_NOT_IMPLEMENTED"
    assert parsed["next_gate"] == design.NEXT_GATE


def test_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / design.V5_ACCEPTANCE_RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["qualification_scope"] = "MODEL_EXECUTION"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(design.DesignError) as captured:
        design.validate_authorities(candidate_repo)

    assert captured.value.error_code == "P5_P6_DESIGN_AUTHORITY_DRIFT"
