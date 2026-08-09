"""Tests for Exact-Runtime P5/P6 Requalification V1 implementation assets."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import p5_p6_exact_runtime_requalification_v1 as subject


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.DESIGN_RECORD_PATH,
        subject.V5_ACCEPTANCE_PATH,
        subject.RESOLUTION_LOCK_PATH,
        subject.SEMANTIC_BOUNDARY_PATH,
        subject.HISTORICAL_ACCEPTANCE_PATH,
        subject.HISTORICAL_REVIEW_PATH,
        subject.HISTORICAL_HARNESS_PATH,
        subject.HISTORICAL_TEMPLATE_PATH,
        *subject.STATIC_PATHS,
    )
    for relative in required:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def _runtime(repo_root: Path) -> dict[str, Any]:
    return subject.runtime_namespace(repo_root)


def _metric(
    runtime: dict[str, Any],
    *,
    local_compute: float,
    local_cache_hit: float,
    prefix_hits: float = 0.0,
    prefix_queries: float = 0.0,
    external: float = 0.0,
    new_prefill: float | None = None,
) -> Any:
    computed = local_compute if new_prefill is None else new_prefill
    cls = runtime["MetricDeltaObservation"]
    return cls(
        prefix_cache_queries=prefix_queries,
        prefix_cache_hits=prefix_hits,
        local_compute=local_compute,
        local_cache_hit=local_cache_hit,
        external_kv_transfer=external,
        cached_prompt_tokens=local_cache_hit + external,
        newly_computed_prefill_tokens=computed,
    )


def _request(
    runtime: dict[str, Any],
    *,
    role: str,
    worker: str,
    generation: int,
    port: int,
    token_ids: tuple[int, ...],
    metric: Any,
) -> dict[str, object]:
    token_cls = runtime["TokenIdentityObservation"]
    route_cls = runtime["RouteObservation"]
    canonical_json = runtime["canonical_json"]
    sha256_bytes = runtime["sha256_bytes"]
    token_sha = sha256_bytes(canonical_json(list(token_ids)).encode("utf-8"))
    token = token_cls(
        request_role=role,
        prefix_variant="B" if role == "NEGATIVE_PREFIX" else "A",
        token_count=len(token_ids),
        token_sha256=token_sha,
        token_ids=token_ids,
    )
    route = route_cls(
        request_id=f"{role.lower()}-{worker}-g{generation}",
        request_role=role,
        intended_worker=worker,
        realized_worker=worker,
        worker_generation=generation,
        endpoint_port=port,
        metric_endpoint_identity="f" * 64,
        route_reason="DIRECT_LOOPBACK_ENDPOINT",
        fallback_reason=None,
        output_sha256="e" * 64,
    )
    return {
        "request_id": route.request_id,
        "request_role": role,
        "prefix_variant": token.prefix_variant,
        "token_identity": token,
        "metric_delta": metric,
        "route_observation": route,
        "structured_output_sha256": "e" * 64,
        "structured_output_valid": True,
        "prompt_tokens": len(token_ids),
        "completion_tokens": 5,
    }


def _passing_requests(runtime: dict[str, Any]) -> dict[str, dict[str, object]]:
    a_tokens = tuple(range(64))
    b_tokens = tuple(range(16)) + tuple(range(100, 148))
    return {
        "cold": _request(
            runtime,
            role="BASE_COLD",
            worker="worker_1",
            generation=1,
            port=8001,
            token_ids=a_tokens,
            metric=_metric(
                runtime,
                local_compute=64,
                local_cache_hit=0,
                new_prefill=64,
            ),
        ),
        "warm": _request(
            runtime,
            role="BASE_WARM",
            worker="worker_1",
            generation=1,
            port=8001,
            token_ids=a_tokens,
            metric=_metric(
                runtime,
                local_compute=0,
                local_cache_hit=64,
                prefix_hits=4,
                prefix_queries=4,
                new_prefill=0,
            ),
        ),
        "negative": _request(
            runtime,
            role="NEGATIVE_PREFIX",
            worker="worker_1",
            generation=1,
            port=8001,
            token_ids=b_tokens,
            metric=_metric(
                runtime,
                local_compute=48,
                local_cache_hit=16,
                prefix_hits=1,
                prefix_queries=4,
                new_prefill=48,
            ),
        ),
        "reset": _request(
            runtime,
            role="POST_RESET_COLD",
            worker="worker_1",
            generation=2,
            port=8001,
            token_ids=a_tokens,
            metric=_metric(
                runtime,
                local_compute=64,
                local_cache_hit=0,
                new_prefill=64,
            ),
        ),
        "cross": _request(
            runtime,
            role="CROSS_WORKER_COLD",
            worker="worker_2",
            generation=1,
            port=8002,
            token_ids=a_tokens,
            metric=_metric(
                runtime,
                local_compute=64,
                local_cache_hit=0,
                new_prefill=64,
            ),
        ),
        "retention": _request(
            runtime,
            role="WORKER1_RETENTION",
            worker="worker_1",
            generation=2,
            port=8001,
            token_ids=a_tokens,
            metric=_metric(
                runtime,
                local_compute=0,
                local_cache_hit=64,
                prefix_hits=4,
                prefix_queries=4,
                new_prefill=0,
            ),
        ),
    }


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.STATIC_PATHS) == 6
    assert len(subject.GENERATED_PATHS) == 3
    assert len(subject.CANDIDATE_PATHS) == 9


def test_design_authority_and_historical_scope_are_frozen(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    result = subject.validate_design_authority(repo_root)
    review = subject._review(repo_root)

    assert result["status"] == "EXACT_RUNTIME_P5_P6_DESIGN_AUTHORITY_VALID"
    assert len(review.accepted_authorities) == 7
    historical = tuple(
        item
        for item in review.accepted_authorities
        if item.authority_scope == "DESIGN_PRECEDENT_ONLY"
    )
    assert len(historical) == 4
    assert review.safety.runtime_execution_authorized is False
    assert review.safety.pilot_execution_authorized is False


def test_generation_round_trip_is_deterministic(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.generate(repo_root)
    first_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}
    second = subject.generate(repo_root)
    second_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}

    assert first == second
    assert first_bytes == second_bytes
    assert subject.validate_generated(repo_root)["status"] == (
        "EXACT_RUNTIME_P5_P6_GENERATED_ARTIFACTS_VALID"
    )


def test_generated_artifact_drift_fails_closed(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.RECORD_PATH
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        subject.ImplementationError,
        match="generated implementation artifact is non-canonical",
    ):
        subject.validate_generated(repo_root)


def test_live_authorization_artifact_is_absent_during_implementation(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    live = repo_root / subject.LIVE_AUTHORIZATION_PATH
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        subject.ImplementationError,
        match="live runtime authorization must be absent",
    ):
        subject.build_generated(repo_root)


def test_notebook_is_single_cell_unexecuted_and_hash_bound(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    generated = subject.generate(repo_root)
    notebook = json.loads((repo_root / subject.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    cells = notebook["cells"]
    record = subject.build_generated(repo_root)[1]

    assert len(cells) == 1
    assert cells[0]["cell_type"] == "code"
    assert cells[0]["execution_count"] is None
    assert cells[0]["outputs"] == []
    wrapper = "".join(cells[0]["source"])
    assert record.notebook.runtime_script_sha256 in wrapper
    assert "runtime script identity mismatch" in wrapper
    assert max(len(line) for line in wrapper.splitlines()) <= 100
    assert generated["runtime_execution_authorized"] is False


def test_runtime_authorization_consumer_precedes_installation(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    review = subject._review(repo_root)
    rendered = subject._render_runtime_template(
        repo_root,
        subject._sha256_bytes(review.canonical_bytes()),
    )
    audit = subject.audit_runtime_semantic_boundary(rendered)

    assert audit["authorization_precedes_runtime_installation"] is True
    assert audit["public_evidence_used_as_semantic_input"] is False
    assert audit["semantic_channel_violation_count"] == 0


def test_runtime_rejects_missing_live_authorization(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    input_root = tmp_path / "input"
    input_root.mkdir()
    runtime["INPUT_ROOT"] = input_root

    with pytest.raises(
        runtime["DiagnosticFailure"],
        match="exactly one live P5/P6 execution authorization is required",
    ):
        runtime["require_execution_authorization"]()


def test_runtime_accepts_exact_live_authorization_contract(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    runtime = _runtime(repo_root)
    input_root = tmp_path / "input"
    auth_root = input_root / "authorization"
    auth_root.mkdir(parents=True)
    runtime["INPUT_ROOT"] = input_root

    now = datetime.now(UTC)
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": runtime["AUTHORIZATION_ID"],
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": runtime["AUTHORIZATION_SCOPE"],
        "implementation_review_sha256": runtime["IMPLEMENTATION_REVIEW_SHA256"],
        "design_record_sha256": runtime["DESIGN_RECORD_SHA256"],
        "v5_acceptance_sha256": runtime["V5_ACCEPTANCE_SHA256"],
        "runtime_script_sha256": runtime["EXECUTED_RUNTIME_SCRIPT_SHA256"],
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "runtime_execution_authorized": True,
        "single_use": True,
        "every_terminal_attempt_consumes_authorization": True,
        "unchanged_replay_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "hidden_retries_permitted": 0,
    }
    auth_path = auth_root / runtime["AUTHORIZATION_FILENAME"]
    auth_path.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )

    result = runtime["require_execution_authorization"]()

    assert result["runtime_execution_authorized"] is True
    assert result["single_use"] is True
    assert len(result["authorization_sha256"]) == 64


def test_p5_passes_only_with_cache_specific_controls(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    requests = _passing_requests(runtime)

    decision = runtime["decide_p5"](
        requests["cold"],
        requests["warm"],
        requests["negative"],
        requests["reset"],
        requests["cross"],
    )

    assert decision.state.value == "PASS"
    assert decision.failure_class is None


def test_p5_fails_when_cross_worker_inherits_local_cache(
    tmp_path: Path,
) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    requests = _passing_requests(runtime)
    requests["cross"]["metric_delta"] = _metric(
        runtime,
        local_compute=48,
        local_cache_hit=16,
        prefix_hits=1,
        prefix_queries=4,
        new_prefill=48,
    )

    decision = runtime["decide_p5"](
        requests["cold"],
        requests["warm"],
        requests["negative"],
        requests["reset"],
        requests["cross"],
    )

    assert decision.state.value == "FAIL"
    assert decision.failure_class == "P5_BEHAVIOR_FAILURE"


def test_p5_negative_prefix_respects_cacheable_common_prefix_bound(
    tmp_path: Path,
) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    requests = _passing_requests(runtime)
    requests["negative"]["metric_delta"] = _metric(
        runtime,
        local_compute=32,
        local_cache_hit=32,
        prefix_hits=2,
        prefix_queries=4,
        new_prefill=32,
    )

    decision = runtime["decide_p5"](
        requests["cold"],
        requests["warm"],
        requests["negative"],
        requests["reset"],
        requests["cross"],
    )

    assert decision.state.value == "FAIL"
    assert any("common-prefix bound" in reason for reason in decision.reasons)


def test_p6_passes_with_disjoint_route_and_state_evidence(
    tmp_path: Path,
) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    requests = _passing_requests(runtime)

    decision = runtime["decide_p6"](
        requests["cross"],
        requests["retention"],
        {"worker_process_trees_disjoint": True},
        {
            "worker_1_bound_to_gpu_0": True,
            "worker_2_bound_to_gpu_1": True,
        },
    )

    assert decision.state.value == "PASS"
    assert decision.failure_class is None


def test_p6_fails_when_retained_state_is_not_attributable(
    tmp_path: Path,
) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    requests = _passing_requests(runtime)
    requests["retention"]["metric_delta"] = _metric(
        runtime,
        local_compute=64,
        local_cache_hit=0,
        new_prefill=64,
    )

    decision = runtime["decide_p6"](
        requests["cross"],
        requests["retention"],
        {"worker_process_trees_disjoint": True},
        {
            "worker_1_bound_to_gpu_0": True,
            "worker_2_bound_to_gpu_1": True,
        },
    )

    assert decision.state.value == "FAIL"
    assert decision.failure_class == "P6_BEHAVIOR_FAILURE"


def test_semantic_decision_is_invariant_to_projection_policy(
    tmp_path: Path,
) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    decision_cls = runtime["BehaviorDecision"]
    state_cls = runtime["BehaviorState"]
    decision = decision_cls(
        capability="P5_PREFIX_CACHE_BEHAVIOR",
        state=state_cls.PASS,
        failure_class=None,
        reasons=("typed observations passed",),
    )

    assert runtime["decision_invariant_under_projection_policy"](decision) is True


def test_runtime_source_freezes_six_request_plan_and_zero_hidden_retries(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    review = subject._review(repo_root)
    source = subject._render_runtime_template(
        repo_root,
        subject._sha256_bytes(review.canonical_bytes()),
    ).decode("utf-8")

    for role in (
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    ):
        assert role in source
    assert '"model_requests": 6' in source
    assert '"hidden_retries": 0' in source
    assert '"benchmark_trajectory_requests": 0' in source
    assert "PASSED_PENDING_REPOSITORY_ACCEPTANCE" in source
    assert "public_evidence_used_as_semantic_input" in source
