"""Tests for P5/P6 Mechanism-Admission Successor V1."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import p5_p6_mechanism_admission_successor_v1 as subject


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = tuple(path for _, path, _ in subject.AUTHORITY_SPECS) + subject.STATIC_PATHS
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
    prefix_cache_hits: float = 0.0,
    newly_computed_prefill_tokens: float | None = None,
) -> Any:
    computed = (
        local_compute if newly_computed_prefill_tokens is None else newly_computed_prefill_tokens
    )
    return runtime["MetricDeltaObservation"](
        prefix_cache_queries=1.0,
        prefix_cache_hits=prefix_cache_hits,
        local_compute=local_compute,
        local_cache_hit=local_cache_hit,
        external_kv_transfer=0.0,
        cached_prompt_tokens=local_cache_hit,
        newly_computed_prefill_tokens=computed,
    )


def _token(runtime: dict[str, Any], role: str, variant: str, tokens: tuple[int, ...]) -> Any:
    canonical_json = runtime["canonical_json"]
    sha256_text = runtime["sha256_text"]
    return runtime["TokenIdentityObservation"](
        request_role=role,
        prefix_variant=variant,
        token_count=len(tokens),
        token_sha256=sha256_text(canonical_json(list(tokens))),
        token_ids=tokens,
    )


def _route(
    runtime: dict[str, Any],
    role: str,
    intended: str,
    generation: int,
) -> Any:
    return runtime["RouteObservation"](
        request_id=f"{role.lower()}-1",
        request_role=role,
        intended_worker=intended,
        realized_worker=intended,
        worker_generation=generation,
        endpoint_port=8001 if intended == "worker_1" else 8002,
        metric_endpoint_identity="a" * 64,
        route_reason="DIRECT_LOOPBACK_ENDPOINT",
        fallback_reason=None,
        output_sha256="b" * 64,
    )


def _request(
    runtime: dict[str, Any],
    *,
    role: str,
    variant: str,
    metric: Any,
    token: Any,
    route: Any,
    semantic_state: str,
) -> dict[str, object]:
    state = runtime["SemanticState"]
    observation = runtime["SemanticObservation"](
        state=state(semantic_state),
        response_content_sha256="c" * 64,
        parsed_json_sha256="d" * 64 if semantic_state != "INVALID_JSON" else None,
        valid_json=semantic_state != "INVALID_JSON",
        object_root=semantic_state in {"EXACT_MATCH", "VALID_JSON_MISMATCH"},
        exact_match=semantic_state == "EXACT_MATCH",
    )
    return {
        "request_id": f"{role.lower()}-1",
        "request_role": role,
        "prefix_variant": variant,
        "metric_delta": metric,
        "token_identity": token,
        "route_observation": route,
        "semantic_observation": observation,
        "prompt_tokens": 899,
        "completion_tokens": 8,
    }


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.STATIC_PATHS) == 6
    assert len(subject.GENERATED_PATHS) == 3
    assert len(subject.CANDIDATE_PATHS) == 9


def test_authorities_and_design_state_are_bound(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    authorities = subject.validate_authorities(repo_root)

    assert len(authorities) == 9
    assert subject.AUTHORIZATION_SCOPE == "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
    assert subject.V2_AUTHORIZATION_SCOPE == "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"


def test_p5_p6_evaluators_are_ast_identical_to_v2(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    result = subject.audit_frozen_p5_p6(repo_root)

    assert result["p5_evaluator_ast_identical_to_v2"] is True
    assert result["p6_evaluator_ast_identical_to_v2"] is True


def test_semantic_observer_is_total_for_model_content(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    observe = runtime["observe_structured_response"]
    expected = runtime["EXPECTED_OBJECT_CANONICAL"]

    exact = observe(expected, expected)
    mismatch = observe('{"probe":"wrong","value":1}', expected)
    non_object = observe('["wrong"]', expected)
    invalid = observe("not-json", expected)

    assert exact.state.value == "EXACT_MATCH"
    assert mismatch.state.value == "VALID_JSON_MISMATCH"
    assert non_object.state.value == "NON_OBJECT_JSON"
    assert invalid.state.value == "INVALID_JSON"
    assert invalid.response_content_sha256
    assert invalid.parsed_json_sha256 is None


def test_wrong_semantics_preserve_request_mechanism_evidence(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    snapshot = runtime["MetricSnapshotObservation"]

    class FakeWorker:
        worker_id = "worker_1"
        generation = 1
        port = 8001

        def __init__(self) -> None:
            self.calls = 0

        def metric_snapshot(self) -> Any:
            self.calls += 1
            if self.calls == 1:
                return snapshot(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            return snapshot(1.0, 0.0, 899.0, 0.0, 0.0, 0.0, 899.0)

    token = runtime["TokenIdentityObservation"](
        request_role="BASE_COLD",
        prefix_variant="A",
        token_count=899,
        token_sha256="e" * 64,
        token_ids=tuple(range(899)),
    )
    runtime["tokenize_request"] = lambda *args, **kwargs: token
    runtime["post_json"] = lambda *args, **kwargs: {
        "model": runtime["SERVED_MODEL_NAME"],
        "usage": {"prompt_tokens": 899, "completion_tokens": 8},
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": '{"probe":"wrong","value":1}'},
            }
        ],
    }

    result = runtime["run_structured_request"](
        FakeWorker(),
        "BASE_COLD",
        "A",
        {"model_requests": 0},
    )

    assert result["semantic_state"] == "VALID_JSON_MISMATCH"
    assert result["semantic_exact_match"] is False
    assert result["response_content_sha256"]
    assert result["metric_delta"].local_compute == 899.0
    assert result["route_observation"].realized_worker == "worker_1"


def test_non_stop_finish_reason_remains_blocking(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    snapshot = runtime["MetricSnapshotObservation"]

    class FakeWorker:
        worker_id = "worker_1"
        generation = 1
        port = 8001

        def __init__(self) -> None:
            self.calls = 0

        def metric_snapshot(self) -> Any:
            self.calls += 1
            if self.calls == 1:
                return snapshot(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            return snapshot(1.0, 0.0, 899.0, 0.0, 0.0, 0.0, 899.0)

    runtime["tokenize_request"] = lambda *args, **kwargs: runtime["TokenIdentityObservation"](
        request_role="BASE_COLD",
        prefix_variant="A",
        token_count=899,
        token_sha256="e" * 64,
        token_ids=tuple(range(899)),
    )
    runtime["post_json"] = lambda *args, **kwargs: {
        "model": runtime["SERVED_MODEL_NAME"],
        "usage": {"prompt_tokens": 899, "completion_tokens": 32},
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": '{"probe":"wrong","value":1}'},
            }
        ],
    }

    with pytest.raises(
        runtime["DiagnosticFailure"],
        match="response finish reason is not stop",
    ):
        runtime["run_structured_request"](
            FakeWorker(),
            "BASE_COLD",
            "A",
            {"model_requests": 0},
        )


def test_p5_p6_are_invariant_under_semantic_substitution(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    a_tokens = tuple(range(899))
    b_tokens = (9999, *range(1, 899))

    def build(semantic_state: str) -> tuple[Any, Any]:
        cold = _request(
            runtime,
            role="BASE_COLD",
            variant="A",
            metric=_metric(runtime, local_compute=899.0, local_cache_hit=0.0),
            token=_token(runtime, "BASE_COLD", "A", a_tokens),
            route=_route(runtime, "BASE_COLD", "worker_1", 1),
            semantic_state=semantic_state,
        )
        warm = _request(
            runtime,
            role="BASE_WARM",
            variant="A",
            metric=_metric(
                runtime,
                local_compute=19.0,
                local_cache_hit=880.0,
                prefix_cache_hits=55.0,
                newly_computed_prefill_tokens=19.0,
            ),
            token=_token(runtime, "BASE_WARM", "A", a_tokens),
            route=_route(runtime, "BASE_WARM", "worker_1", 1),
            semantic_state=semantic_state,
        )
        negative = _request(
            runtime,
            role="NEGATIVE_PREFIX",
            variant="B",
            metric=_metric(runtime, local_compute=899.0, local_cache_hit=0.0),
            token=_token(runtime, "NEGATIVE_PREFIX", "B", b_tokens),
            route=_route(runtime, "NEGATIVE_PREFIX", "worker_1", 1),
            semantic_state=semantic_state,
        )
        reset = _request(
            runtime,
            role="POST_RESET_COLD",
            variant="A",
            metric=_metric(runtime, local_compute=899.0, local_cache_hit=0.0),
            token=_token(runtime, "POST_RESET_COLD", "A", a_tokens),
            route=_route(runtime, "POST_RESET_COLD", "worker_1", 2),
            semantic_state=semantic_state,
        )
        cross = _request(
            runtime,
            role="CROSS_WORKER_COLD",
            variant="A",
            metric=_metric(runtime, local_compute=899.0, local_cache_hit=0.0),
            token=_token(runtime, "CROSS_WORKER_COLD", "A", a_tokens),
            route=_route(runtime, "CROSS_WORKER_COLD", "worker_2", 1),
            semantic_state=semantic_state,
        )
        retention = _request(
            runtime,
            role="WORKER1_RETENTION",
            variant="A",
            metric=_metric(
                runtime,
                local_compute=19.0,
                local_cache_hit=880.0,
                prefix_cache_hits=55.0,
                newly_computed_prefill_tokens=19.0,
            ),
            token=_token(runtime, "WORKER1_RETENTION", "A", a_tokens),
            route=_route(runtime, "WORKER1_RETENTION", "worker_1", 2),
            semantic_state=semantic_state,
        )
        p5 = runtime["decide_p5"](cold, warm, negative, reset, cross)
        p6 = runtime["decide_p6"](
            cross,
            retention,
            {"worker_process_trees_disjoint": True},
            {
                "worker_1_bound_to_gpu_0": True,
                "worker_2_bound_to_gpu_1": True,
            },
        )
        return p5, p6

    exact_p5, exact_p6 = build("EXACT_MATCH")
    mismatch_p5, mismatch_p6 = build("VALID_JSON_MISMATCH")

    assert exact_p5 == mismatch_p5
    assert exact_p6 == mismatch_p6
    assert exact_p5.state.value == "PASS"
    assert exact_p6.state.value == "PASS"


def test_install_runtime_accepts_canonical_passed_process_outcome(tmp_path: Path) -> None:
    runtime = _runtime(_fixture_repo(tmp_path))
    work_root = tmp_path / "working"
    work_root.mkdir()
    target_root = work_root / "target_runtime"
    target_python = target_root / "bin" / "python"
    wheelhouse = tmp_path / "wheelhouse"
    (wheelhouse / "wheels").mkdir(parents=True)
    (wheelhouse / "requirements.lock.txt").write_text("", encoding="utf-8")
    (wheelhouse / "sha256_manifest.json").write_text("{}", encoding="utf-8")

    runtime["WORK_ROOT"] = work_root
    runtime["SCRATCH_ROOT"] = work_root / "scratch"
    runtime["TARGET_ROOT"] = target_root
    runtime["TARGET_PYTHON"] = target_python

    def fake_process(role: str, *args: Any, **kwargs: Any) -> dict[str, object]:
        if role == "target_environment_creation":
            target_python.parent.mkdir(parents=True)
            target_python.write_text("python", encoding="utf-8")
        return {
            "schema_version": "1.0.0",
            "command_role": role,
            "status": "PASSED",
            "process_outcome": "PASSED",
            "argv": [],
            "argv_sha256": "f" * 64,
            "started_at": "2026-08-22T00:00:00+00:00",
            "finished_at": "2026-08-22T00:00:00+00:00",
            "duration_ms": 1,
            "returncode": 0,
            "timed_out": False,
            "launch_error_type": None,
            "launch_error_message": None,
            "stdout_observed_bytes": 0,
            "stderr_observed_bytes": 0,
            "stdout_tail": "",
            "stderr_tail": "",
            "failure_signals": (),
        }

    runtime["run_bounded_process"] = fake_process
    report = runtime["install_runtime"](
        wheelhouse,
        {"runtime_install_attempts": 0},
    )

    assert report["status"] == "PASSED"
    assert report["process_outcome"] == "PASSED"


def test_legacy_zero_exit_success_token_is_absent(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    template = subject.read_file(repo_root, subject.TEMPLATE_PATH).decode("utf-8")

    assert '"ZERO_EXIT"' not in template
    assert 'create_process["process_outcome"] != "PASSED"' in template


def test_generation_is_deterministic_and_unexecuted(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.write_generated(repo_root)
    first_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}
    second = subject.write_generated(repo_root)
    second_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}

    assert first == second
    assert first_bytes == second_bytes
    checked = subject.check_generated(repo_root)
    assert checked["runtime_execution_authorized"] is False

    notebook = json.loads((repo_root / subject.NOTEBOOK_PATH).read_text(encoding="utf-8"))
    assert len(notebook["cells"]) == 1
    assert notebook["cells"][0]["execution_count"] is None
    assert notebook["cells"][0]["outputs"] == []
