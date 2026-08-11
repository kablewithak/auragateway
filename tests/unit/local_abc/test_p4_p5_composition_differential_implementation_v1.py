from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p4_p5_composition_differential_implementation_v1 as implementation,
)


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[3]

    required = (
        implementation.DESIGN_PATH,
        implementation.PREDECESSOR_RUNTIME_PATH,
        implementation.P4_PRECEDENT_PATH,
        implementation.SOURCE_PATH,
        implementation.TEST_PATH,
    )

    for relative in required:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / relative, target)

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


def test_predecessor_runtime_is_immutable_authority(
    candidate_repo: Path,
) -> None:
    before = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_bytes()

    implementation.generate(candidate_repo)

    after = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_bytes()

    assert before == after
    assert implementation._sha256(after) == (implementation.PREDECESSOR_RUNTIME_SHA256)


def test_successor_runtime_compiles(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)

    compile(
        runtime.decode("utf-8"),
        implementation.RUNTIME_PATH.as_posix(),
        "exec",
    )


def test_request_messages_freeze_simple_and_composed_cases(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    messages = _function_source(source, "request_messages")

    assert 'if prefix_variant == "A":' in messages
    assert '{"role": "user", "content": EXPECTED_OBJECT_CANONICAL}' in messages
    assert 'if prefix_variant == "B":' in messages
    assert "SYNTHETIC_CACHE_CONTEXT_A" in messages
    assert "SYNTHETIC_ASSISTANT_ACK" in messages


def test_successor_main_cannot_reenter_p5_p6_trajectory(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    main = _function_source(source, "main")

    prohibited = (
        "decide_p5(",
        "decide_p6(",
        "route_isolation(",
        "run_structured_request(",
        "tokenize_request(",
        "worker_2",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    )

    assert all(marker not in main for marker in prohibited)
    assert "DIFFERENTIAL_REQUEST_ORDER" in main
    assert "run_differential_request(" in main
    assert "decide_composition_differential(" in main


def test_invalid_json_is_observation_not_request_exception(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    runner = _function_source(
        source,
        "run_differential_request",
    )

    assert "json_error_line" in runner
    assert "json_error_column" in runner
    assert "json_error_position" in runner
    assert "markdown_fence_detected" in runner
    assert "model response is not valid JSON" not in runner


def test_consumable_action_budget_domain_is_exact(
    candidate_repo: Path,
) -> None:
    predecessor_source = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_text(
        encoding="utf-8"
    )

    predecessor_budget = implementation._literal_int_dict_assignment(
        predecessor_source,
        "ACTION_BUDGET_LIMITS",
    )

    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    successor_source = runtime.decode("utf-8")

    successor_budget = implementation._literal_int_dict_assignment(
        successor_source,
        "ACTION_BUDGET_LIMITS",
    )

    assert predecessor_budget == {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 3,
        "worker_starts": 3,
        "model_requests": 6,
    }

    assert successor_budget == {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 1,
        "worker_starts": 1,
        "model_requests": 6,
    }

    assert set(predecessor_budget) == set(successor_budget)

    changed_values = {
        key for key in predecessor_budget if predecessor_budget[key] != successor_budget[key]
    }

    assert changed_values == {
        "model_loads",
        "worker_starts",
    }

    main = _function_source(
        successor_source,
        "main",
    )

    bookkeeping_markers = (
        '"kaggle_sessions": 1',
        '"benchmark_trajectory_requests": 0',
        '"network_requests": 0',
        '"hidden_retries": 0',
        '"external_spend": 0',
    )

    assert all(marker in main for marker in bookkeeping_markers)


def test_change_surface_is_bounded(
    candidate_repo: Path,
) -> None:
    predecessor = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_text(
        encoding="utf-8"
    )

    runtime, unchanged = implementation.build_runtime_payload(candidate_repo)
    successor = runtime.decode("utf-8")

    predecessor_functions = implementation._function_segments(predecessor)
    successor_functions = implementation._function_segments(successor)

    changed = tuple(
        sorted(
            name
            for name, original in predecessor_functions.items()
            if successor_functions[name] != original
        )
    )

    assert changed == tuple(sorted(implementation.CHANGED_EXISTING_FUNCTIONS))
    assert unchanged > 0


def test_generate_and_validate_are_byte_deterministic(
    candidate_repo: Path,
) -> None:
    first = implementation.generate(candidate_repo)

    runtime_first = (candidate_repo / implementation.RUNTIME_PATH).read_bytes()
    review_first = (candidate_repo / implementation.REVIEW_PATH).read_bytes()
    record_first = (candidate_repo / implementation.RECORD_PATH).read_bytes()

    second = implementation.generate(candidate_repo)
    validated = implementation.validate(candidate_repo)

    assert first["runtime_payload_sha256"] == (second["runtime_payload_sha256"])
    assert first["runtime_payload_sha256"] == (validated["runtime_payload_sha256"])
    assert runtime_first == (candidate_repo / implementation.RUNTIME_PATH).read_bytes()
    assert review_first == (candidate_repo / implementation.REVIEW_PATH).read_bytes()
    assert record_first == (candidate_repo / implementation.RECORD_PATH).read_bytes()


def test_static_record_is_execution_inert(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)

    record = json.loads((candidate_repo / implementation.RECORD_PATH).read_text(encoding="utf-8"))

    assert record["status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert record["model_requests_performed"] == 0
    assert record["model_loads_performed"] == 0
    assert record["worker_starts_performed"] == 0
    assert record["kaggle_execution_performed"] is False
    assert record["gpu_execution_performed"] is False
    assert record["differential_notebook_generated"] is False
    assert record["live_authorization_issued"] is False
    assert record["runtime_execution_authorized"] is False
    assert record["new_execution_authorized"] is False


def test_authority_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(implementation.ImplementationError) as captured:
        implementation.build_runtime_payload(candidate_repo)

    assert captured.value.error_code == ("P4_P5_DIFF_IMPLEMENTATION_AUTHORITY_DRIFT")


def test_successor_candidate_typing_boundaries_are_explicit(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")

    decision = _function_source(
        source,
        "decide_composition_differential",
    )
    main = _function_source(
        source,
        "main",
    )

    assert 'int(row["sequence_index"])' not in decision
    assert 'sequence_index = row.get("sequence_index")' in decision
    assert "observed_indexes_list.append(sequence_index)" in decision
    assert "decision_state: object = None" in main
    assert "if decision is not None and failure is None:" in main
    assert 'decision_state = decision.get("decision_state")' in main
    assert '"decision_state": decision_state' in main
