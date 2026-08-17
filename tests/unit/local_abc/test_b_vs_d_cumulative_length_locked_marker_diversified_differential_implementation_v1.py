from __future__ import annotations

import ast
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

from auragateway.local_abc import (
    b_vs_d_cumulative_length_locked_marker_diversified_differential_implementation_v1,
)

implementation = b_vs_d_cumulative_length_locked_marker_diversified_differential_implementation_v1


@pytest.fixture
def candidate_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    for relative in (
        implementation.DESIGN_PATH,
        implementation.PREDECESSOR_RUNTIME_PATH,
        implementation.SOURCE_PATH,
        implementation.TEST_PATH,
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / relative, target)
    monkeypatch.setattr(
        implementation,
        "_base_commit_is_ancestor_of_head",
        lambda root: True,
    )
    return tmp_path


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    assert len(matches) == 1
    observed = ast.get_source_segment(source, matches[0])
    assert observed is not None
    return observed


def _runtime_namespace(candidate_repo: Path) -> dict[str, object]:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    module_name = "auragateway_b_vs_d_static_candidate"
    module = ModuleType(module_name)
    module.__file__ = implementation.RUNTIME_PATH.as_posix()
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(
            compile(source, implementation.RUNTIME_PATH.as_posix(), "exec"),
            module.__dict__,
        )
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        if previous is not None:
            sys.modules[module_name] = previous
    return dict(module.__dict__)


def _decision_inputs(
    namespace: dict[str, object],
    b_exact: int,
    d_exact: int,
) -> tuple[
    list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, int]
]:
    order = namespace["B_VS_D_REQUEST_ORDER"]
    assert isinstance(order, tuple)
    remaining = {
        implementation.B_CONDITION: b_exact,
        implementation.D_CONDITION: d_exact,
    }
    token_hashes = {
        implementation.B_CONDITION: implementation.B_TOKEN_SHA256,
        implementation.D_CONDITION: implementation.D_TOKEN_SHA256,
    }
    payload_hashes = {
        implementation.B_CONDITION: implementation.B_PAYLOAD_SHA256,
        implementation.D_CONDITION: implementation.D_PAYLOAD_SHA256,
    }
    results: list[dict[str, object]] = []
    for ordinal, condition_id in enumerate(order, start=1):
        assert isinstance(condition_id, str)
        exact = remaining[condition_id] > 0
        if exact:
            remaining[condition_id] -= 1
        results.append(
            {
                "condition_id": condition_id,
                "sequence_index": ordinal,
                "worker_process_identity_sha256": f"worker-{ordinal}",
                "zero_cache_baseline": True,
                "token_count": 899,
                "token_sha256": token_hashes[condition_id],
                "payload_sha256": payload_hashes[condition_id],
                "exact_object": exact,
                "valid_json": exact,
            }
        )
    workers: list[dict[str, object]] = [{"ordinal": value} for value in range(1, 7)]
    teardowns: list[dict[str, object]] = [{"status": "PASSED"} for _ in range(6)]
    counters = {
        "model_requests": 6,
        "model_loads": 6,
        "worker_starts": 6,
        "hidden_retries": 0,
        "network_requests": 0,
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
    }
    return results, workers, teardowns, counters


def test_predecessor_runtime_is_immutable(candidate_repo: Path) -> None:
    before = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_bytes()
    implementation.generate(candidate_repo)
    after = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_bytes()
    assert before == after
    assert implementation._sha256(after) == implementation.PREDECESSOR_RUNTIME_SHA256


def test_successor_runtime_compiles_and_only_main_changes(candidate_repo: Path) -> None:
    predecessor = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_text(
        encoding="utf-8"
    )
    runtime, unchanged = implementation.build_runtime_payload(candidate_repo)
    successor = runtime.decode("utf-8")
    compile(successor, implementation.RUNTIME_PATH.as_posix(), "exec")
    before = implementation._function_segments(predecessor)
    after = implementation._function_segments(successor)
    changed = tuple(sorted(name for name, body in before.items() if after[name] != body))
    assert changed == ("main",)
    assert set(after) == set(before) | set(implementation.ADDED_FUNCTIONS)
    assert unchanged > 0


def test_b_and_d_payloads_and_composition_are_frozen(candidate_repo: Path) -> None:
    namespace = _runtime_namespace(candidate_repo)
    payload = namespace["marker_diversified_request_payload"]
    canonical_json = namespace["canonical_json"]
    sha256_text = namespace["sha256_text"]
    expected = {
        implementation.B_CONDITION: implementation.B_PAYLOAD_SHA256,
        implementation.D_CONDITION: implementation.D_PAYLOAD_SHA256,
    }
    for condition_id, expected_sha in expected.items():
        observed = payload(condition_id)  # type: ignore[operator]
        assert sha256_text(canonical_json(observed)) == expected_sha  # type: ignore[operator]
        assert [item["role"] for item in observed["messages"]] == [
            "system",
            "user",
            "assistant",
            "user",
        ]
        assert observed["temperature"] == 0
        assert observed["top_p"] == 1
        assert observed["repetition_penalty"] == 1.1
        assert observed["seed"] == 7
        assert observed["max_tokens"] == 32
        assert observed["stream"] is False
        assert "response_format" not in observed


def test_six_fresh_worker_budget_and_main_are_frozen(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    assert implementation._literal_int_dict_assignment(source, "ACTION_BUDGET_LIMITS") == {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 6,
        "worker_starts": 6,
        "model_requests": 6,
    }
    main = _function_source(source, "main")
    assert "B_VS_D_REQUEST_ORDER" in main
    assert "run_marker_diversified_fresh_worker_observation(" in main
    assert "decide_marker_diversified_differential(" in main
    assert "TOKEN_MATCHED_REQUEST_ORDER" not in main
    assert "decide_p5(" not in main
    assert "decide_p6(" not in main


def test_pre_request_identity_precedes_request_and_invalid_json_is_observed(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    runner = _function_source(runtime.decode("utf-8"), "run_marker_diversified_observation")
    assert (
        runner.index("persist_marker_diversified_pre_request_identity(")
        < runner.index("validate_zero_cache_baseline(worker)")
        < runner.index('consume_actions(counters, "model_requests")')
    )
    assert '"valid_json": valid_json' in runner
    assert '"exact_object": exact_object' in runner
    assert "json_error_position" in runner
    assert "validate_structured_response(" not in runner


def test_decision_contract_matches_design(candidate_repo: Path) -> None:
    namespace = _runtime_namespace(candidate_repo)
    decide = namespace["decide_marker_diversified_differential"]
    cases = (
        (0, 3, "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"),
        (0, 0, "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL"),
        (0, 1, "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"),
        (3, 3, "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"),
        (1, 0, "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"),
    )
    for b_exact, d_exact, expected in cases:
        inputs = _decision_inputs(namespace, b_exact, d_exact)
        observed = decide(*inputs)  # type: ignore[operator]
        assert observed["decision_state"] == expected
        assert observed["complete_cumulative_prompt_token_profile_locked"] is True
        assert observed["text_boundary_token_boundary_assumption_used"] is False


def test_generate_validate_are_byte_deterministic_and_execution_inert(candidate_repo: Path) -> None:
    first = implementation.generate(candidate_repo)
    runtime_first = (candidate_repo / implementation.RUNTIME_PATH).read_bytes()
    review_first = (candidate_repo / implementation.REVIEW_PATH).read_bytes()
    record_first = (candidate_repo / implementation.RECORD_PATH).read_bytes()
    second = implementation.generate(candidate_repo)
    validated = implementation.validate(candidate_repo)
    assert (
        first["runtime_payload_sha256"]
        == second["runtime_payload_sha256"]
        == validated["runtime_payload_sha256"]
    )
    assert runtime_first == (candidate_repo / implementation.RUNTIME_PATH).read_bytes()
    assert review_first == (candidate_repo / implementation.REVIEW_PATH).read_bytes()
    assert record_first == (candidate_repo / implementation.RECORD_PATH).read_bytes()
    record = json.loads(record_first)
    assert record["status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert record["model_requests_performed"] == 0
    assert record["model_loads_performed"] == 0
    assert record["worker_starts_performed"] == 0
    assert record["runtime_execution_authorized"] is False
    assert record["new_execution_authorized"] is False


def test_design_or_runtime_drift_fails_closed(candidate_repo: Path) -> None:
    design_path = candidate_repo / implementation.DESIGN_PATH
    design_path.write_bytes(design_path.read_bytes() + b"\n")
    with pytest.raises(implementation.ImplementationError) as captured:
        implementation.build_runtime_payload(candidate_repo)
    assert captured.value.error_code == "B_VS_D_IMPLEMENTATION_AUTHORITY_DRIFT"


def test_generated_record_drift_fails_closed(candidate_repo: Path) -> None:
    implementation.generate(candidate_repo)
    path = candidate_repo / implementation.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "TAMPERED"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(implementation.ImplementationError) as captured:
        implementation.validate(candidate_repo)
    assert captured.value.error_code == "B_VS_D_IMPLEMENTATION_GENERATED_ARTIFACT_DRIFT"
