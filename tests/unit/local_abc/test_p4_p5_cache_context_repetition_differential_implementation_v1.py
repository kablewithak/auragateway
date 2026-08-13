from __future__ import annotations

import ast
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

from auragateway.local_abc import (
    p4_p5_cache_context_repetition_differential_implementation_v1 as implementation,
)


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    required = (
        implementation.DESIGN_PATH,
        implementation.PREDECESSOR_RUNTIME_PATH,
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


def _runtime_namespace(candidate_repo: Path) -> dict[str, object]:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    module_name = "auragateway_static_candidate"
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


def test_predecessor_runtime_is_immutable_authority(candidate_repo: Path) -> None:
    before = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_bytes()

    implementation.generate(candidate_repo)

    after = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_bytes()

    assert before == after
    assert implementation._sha256(after) == implementation.PREDECESSOR_RUNTIME_SHA256


def test_successor_runtime_compiles(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)

    compile(
        runtime.decode("utf-8"),
        implementation.RUNTIME_PATH.as_posix(),
        "exec",
    )


def test_24x_treatment_preserves_historical_payload_identity(candidate_repo: Path) -> None:
    namespace = _runtime_namespace(candidate_repo)

    repetition_context = namespace["repetition_context"]
    request_payload = namespace["repetition_request_payload"]
    canonical_json = namespace["canonical_json"]
    sha256_text = namespace["sha256_text"]

    treatment_context = repetition_context(24)  # type: ignore[operator]
    assert treatment_context == namespace["SYNTHETIC_CACHE_CONTEXT_A"]

    treatment_payload = request_payload("TREATMENT_24X")  # type: ignore[operator]
    observed_sha = sha256_text(canonical_json(treatment_payload))  # type: ignore[operator]

    assert observed_sha == implementation.TREATMENT_EXPECTED_PAYLOAD_SHA256


def test_control_and_treatment_freeze_only_repetition_count(candidate_repo: Path) -> None:
    namespace = _runtime_namespace(candidate_repo)

    request_messages = namespace["repetition_request_messages"]

    control = request_messages("CONTROL_1X")  # type: ignore[operator]
    treatment = request_messages("TREATMENT_24X")  # type: ignore[operator]

    assert [item["role"] for item in control] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert [item["role"] for item in treatment] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert control[0] == treatment[0]
    assert control[2] == treatment[2]
    assert control[3] == treatment[3]
    assert control[1]["content"] != treatment[1]["content"]

    body = namespace["REPETITION_CONTEXT_BODY"]
    system_prompt = namespace["SYSTEM_PROMPT"]
    assert isinstance(body, str)
    assert isinstance(system_prompt, str)
    assert control[1]["content"] == body * 1 + system_prompt
    assert treatment[1]["content"] == body * 24 + system_prompt


def test_successor_budget_matches_frozen_fresh_worker_design(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")

    budget = implementation._literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    )

    assert budget == {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 6,
        "worker_starts": 6,
        "model_requests": 6,
    }


def test_successor_main_is_six_fresh_observations_not_p5_p6(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    main = _function_source(source, "main")

    assert "REPETITION_REQUEST_ORDER" in main
    assert "run_fresh_worker_observation(" in main
    assert "decide_repetition_differential(" in main
    assert '"model_loads": 6' in main
    assert '"worker_starts": 6' in main
    assert '"model_requests": 6' in main

    prohibited = (
        "decide_p5(",
        "decide_p6(",
        "route_isolation(",
        "run_structured_request(",
        "run_attributed_request(",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
    )
    assert all(marker not in main for marker in prohibited)


def test_fresh_worker_helper_proves_teardown_per_observation(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    helper = _function_source(source, "run_fresh_worker_observation")

    assert "Worker(" in helper
    assert "generation=sequence_index" in helper
    assert "safe_worker_teardown(" in helper
    assert "teardown_reports.append(teardown)" in helper
    assert 'teardown_status != "PASSED"' in helper


def test_pre_request_identity_is_persisted_before_model_request(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    runner = _function_source(source, "run_repetition_observation")

    journal_index = runner.index("persist_repetition_pre_request_identity(")
    baseline_index = runner.index("validate_zero_cache_baseline(worker)")
    request_index = runner.index('consume_actions(counters, "model_requests")')

    assert journal_index < baseline_index < request_index
    assert "REPETITION_TREATMENT_TOKEN_COUNT" in runner
    assert "REPETITION_TREATMENT_TOKEN_SHA256" in runner
    assert "REPETITION_TREATMENT_PAYLOAD_SHA256" in runner


def test_invalid_json_is_retained_as_observation(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    runner = _function_source(source, "run_repetition_observation")

    assert '"valid_json": valid_json' in runner
    assert '"exact_object": exact_object' in runner
    assert "json_error_line" in runner
    assert "json_error_column" in runner
    assert "json_error_position" in runner
    assert "markdown_fence_detected" in runner
    assert "validate_structured_response(" not in runner


def test_change_surface_is_bounded_to_main_plus_added_helpers(candidate_repo: Path) -> None:
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

    assert changed == ("main",)
    assert set(successor_functions) == (
        set(predecessor_functions) | set(implementation.ADDED_FUNCTIONS)
    )
    assert unchanged > 0


def test_generate_and_validate_are_byte_deterministic(candidate_repo: Path) -> None:
    first = implementation.generate(candidate_repo)

    runtime_first = (candidate_repo / implementation.RUNTIME_PATH).read_bytes()
    review_first = (candidate_repo / implementation.REVIEW_PATH).read_bytes()
    record_first = (candidate_repo / implementation.RECORD_PATH).read_bytes()

    second = implementation.generate(candidate_repo)
    validated = implementation.validate(candidate_repo)

    assert first["runtime_payload_sha256"] == second["runtime_payload_sha256"]
    assert first["runtime_payload_sha256"] == validated["runtime_payload_sha256"]
    assert runtime_first == (candidate_repo / implementation.RUNTIME_PATH).read_bytes()
    assert review_first == (candidate_repo / implementation.REVIEW_PATH).read_bytes()
    assert record_first == (candidate_repo / implementation.RECORD_PATH).read_bytes()


def test_static_record_is_execution_inert(candidate_repo: Path) -> None:
    implementation.generate(candidate_repo)

    record = json.loads((candidate_repo / implementation.RECORD_PATH).read_text(encoding="utf-8"))

    assert record["status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert record["model_requests_performed"] == 0
    assert record["model_loads_performed"] == 0
    assert record["worker_starts_performed"] == 0
    assert record["kaggle_execution_performed"] is False
    assert record["gpu_execution_performed"] is False
    assert record["runtime_execution_authorized"] is False
    assert record["new_execution_authorized"] is False
    assert record["runtime_fix_authorized"] is False
    assert record["threshold_search_authorized"] is False
    assert record["assistant_topology_discriminator_authorized"] is False
    assert record["measured_abc_execution_authorized"] is False


def test_review_freezes_fresh_worker_and_historical_identity(candidate_repo: Path) -> None:
    implementation.generate(candidate_repo)

    review = json.loads((candidate_repo / implementation.REVIEW_PATH).read_text(encoding="utf-8"))

    assert review["request_order"] == list(implementation.REQUEST_ORDER)
    assert review["control_repetition_count"] == 1
    assert review["treatment_repetition_count"] == 24
    assert review["maximum_model_requests"] == 6
    assert review["maximum_model_loads"] == 6
    assert review["maximum_worker_starts"] == 6
    assert review["fresh_worker_process_per_observation"] is True
    assert review["teardown_required_between_observations"] is True
    assert review["zero_cached_prefix_baseline_required"] is True
    assert review["pre_request_journal_required"] is True
    assert review["treatment_expected_token_count"] == 899
    assert review["treatment_expected_token_sha256"] == (
        implementation.TREATMENT_EXPECTED_TOKEN_SHA256
    )
    assert review["treatment_expected_payload_sha256"] == (
        implementation.TREATMENT_EXPECTED_PAYLOAD_SHA256
    )


def test_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(implementation.ImplementationError) as captured:
        implementation.build_runtime_payload(candidate_repo)

    assert captured.value.error_code == ("P4_P5_REPETITION_IMPLEMENTATION_AUTHORITY_DRIFT")
