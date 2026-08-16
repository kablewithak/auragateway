from __future__ import annotations

import ast
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

from auragateway.local_abc import (
    p4_p5_token_count_matched_context_structure_differential_implementation_v1 as implementation,
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
    module_name = "auragateway_token_matched_static_candidate"
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
    exact_counts: dict[str, int],
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, int],
]:
    order = namespace["TOKEN_MATCHED_REQUEST_ORDER"]
    assert isinstance(order, tuple)

    token_hashes = {
        "A_ORIGINAL_24X_ANCHOR": namespace["TOKEN_MATCHED_A_TOKEN_SHA256"],
        "B_NEUTRAL_REPEATED_24X": namespace["TOKEN_MATCHED_B_TOKEN_SHA256"],
        "C_NEUTRAL_DIVERSE_24_SEGMENT": namespace["TOKEN_MATCHED_C_TOKEN_SHA256"],
    }
    payload_hashes = {
        "A_ORIGINAL_24X_ANCHOR": namespace["TOKEN_MATCHED_A_PAYLOAD_SHA256"],
        "B_NEUTRAL_REPEATED_24X": namespace["TOKEN_MATCHED_B_PAYLOAD_SHA256"],
        "C_NEUTRAL_DIVERSE_24_SEGMENT": namespace["TOKEN_MATCHED_C_PAYLOAD_SHA256"],
    }
    seen: dict[str, int] = {key: 0 for key in exact_counts}
    results: list[dict[str, object]] = []

    for ordinal, condition_id in enumerate(order, start=1):
        assert isinstance(condition_id, str)
        seen[condition_id] += 1
        exact_object = seen[condition_id] <= exact_counts[condition_id]
        results.append(
            {
                "condition_id": condition_id,
                "sequence_index": ordinal,
                "worker_process_identity_sha256": f"worker-{ordinal}",
                "zero_cache_baseline": True,
                "token_count": 899,
                "token_sha256": token_hashes[condition_id],
                "payload_sha256": payload_hashes[condition_id],
                "exact_object": exact_object,
                "valid_json": exact_object,
            }
        )

    worker_reports: list[dict[str, object]] = [{"ordinal": ordinal} for ordinal in range(1, 10)]
    teardown_reports: list[dict[str, object]] = [{"status": "PASSED"} for _ in range(9)]
    counters = {
        "model_requests": 9,
        "model_loads": 9,
        "worker_starts": 9,
        "hidden_retries": 0,
        "network_requests": 0,
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
    }
    return results, worker_reports, teardown_reports, counters


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


def test_three_contexts_preserve_frozen_composition(candidate_repo: Path) -> None:
    namespace = _runtime_namespace(candidate_repo)

    context = namespace["token_matched_context"]
    messages = namespace["token_matched_request_messages"]

    a = context("A_ORIGINAL_24X_ANCHOR")  # type: ignore[operator]
    b = context("B_NEUTRAL_REPEATED_24X")  # type: ignore[operator]
    c = context("C_NEUTRAL_DIVERSE_24_SEGMENT")  # type: ignore[operator]

    assert a == namespace["SYNTHETIC_CACHE_CONTEXT_A"]
    assert a != b
    assert b != c
    assert a != c

    for condition_id in implementation.REQUEST_ORDER:
        observed = messages(condition_id)  # type: ignore[operator]
        assert [item["role"] for item in observed] == [
            "system",
            "user",
            "assistant",
            "user",
        ]
        assert observed[0]["content"] == namespace["SYSTEM_PROMPT"]
        assert observed[2]["content"] == namespace["SYNTHETIC_ASSISTANT_ACK"]
        assert observed[3]["content"] == namespace["EXPECTED_OBJECT_CANONICAL"]

    c_segments = namespace["TOKEN_MATCHED_C_SEGMENTS"]
    assert isinstance(c_segments, tuple)
    assert len(c_segments) == 24
    assert len(set(c_segments)) == 24


def test_all_three_payload_identities_are_frozen(candidate_repo: Path) -> None:
    namespace = _runtime_namespace(candidate_repo)

    request_payload = namespace["token_matched_request_payload"]
    canonical_json = namespace["canonical_json"]
    sha256_text = namespace["sha256_text"]

    expected = {
        "A_ORIGINAL_24X_ANCHOR": implementation.A_PAYLOAD_SHA256,
        "B_NEUTRAL_REPEATED_24X": implementation.B_PAYLOAD_SHA256,
        "C_NEUTRAL_DIVERSE_24_SEGMENT": implementation.C_PAYLOAD_SHA256,
    }

    for condition_id, expected_sha in expected.items():
        payload = request_payload(condition_id)  # type: ignore[operator]
        observed_sha = sha256_text(canonical_json(payload))  # type: ignore[operator]
        assert observed_sha == expected_sha
        assert payload["temperature"] == 0
        assert payload["top_p"] == 1
        assert payload["repetition_penalty"] == 1.1
        assert payload["seed"] == 7
        assert payload["max_tokens"] == 32
        assert payload["stream"] is False
        assert "response_format" not in payload


def test_successor_budget_matches_frozen_nine_fresh_worker_design(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")

    budget = implementation._literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    )

    assert budget == {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 9,
        "worker_starts": 9,
        "model_requests": 9,
    }


def test_successor_main_is_nine_fresh_observations_not_predecessor_trajectory(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    main = _function_source(source, "main")

    assert "TOKEN_MATCHED_REQUEST_ORDER" in main
    assert "run_token_matched_fresh_worker_observation(" in main
    assert "decide_token_matched_differential(" in main
    assert '"model_loads": 9' in main
    assert '"worker_starts": 9' in main
    assert '"model_requests": 9' in main

    prohibited = (
        "REPETITION_REQUEST_ORDER",
        "run_fresh_worker_observation(",
        "decide_repetition_differential(",
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


def test_fresh_worker_helper_proves_teardown_per_observation(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    helper = _function_source(
        source,
        "run_token_matched_fresh_worker_observation",
    )

    assert "Worker(" in helper
    assert "generation=sequence_index" in helper
    assert "safe_worker_teardown(" in helper
    assert "teardown_reports.append(teardown)" in helper
    assert 'teardown_status != "PASSED"' in helper


def test_pre_request_identity_is_persisted_before_model_request(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    runner = _function_source(source, "run_token_matched_observation")

    journal_index = runner.index("persist_token_matched_pre_request_identity(")
    baseline_index = runner.index("validate_zero_cache_baseline(worker)")
    request_index = runner.index('consume_actions(counters, "model_requests")')

    assert journal_index < baseline_index < request_index
    assert "TOKEN_MATCHED_PROMPT_TOKEN_COUNT" in runner
    assert "token_matched_expected_token_sha256(condition_id)" in runner
    assert "token_matched_expected_payload_sha256(condition_id)" in runner


def test_invalid_json_is_retained_as_observation(candidate_repo: Path) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")
    runner = _function_source(source, "run_token_matched_observation")

    assert '"valid_json": valid_json' in runner
    assert '"exact_object": exact_object' in runner
    assert "json_error_line" in runner
    assert "json_error_column" in runner
    assert "json_error_position" in runner
    assert "markdown_fence_detected" in runner
    assert "validate_structured_response(" not in runner


def test_change_surface_is_main_plus_additive_helpers(candidate_repo: Path) -> None:
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


def test_decision_contract_matches_frozen_interpretation_matrix(
    candidate_repo: Path,
) -> None:
    namespace = _runtime_namespace(candidate_repo)
    decide = namespace["decide_token_matched_differential"]

    cases = (
        (
            {
                "A_ORIGINAL_24X_ANCHOR": 0,
                "B_NEUTRAL_REPEATED_24X": 3,
                "C_NEUTRAL_DIVERSE_24_SEGMENT": 3,
            },
            "REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED",
        ),
        (
            {
                "A_ORIGINAL_24X_ANCHOR": 0,
                "B_NEUTRAL_REPEATED_24X": 0,
                "C_NEUTRAL_DIVERSE_24_SEGMENT": 3,
            },
            "HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED",
        ),
        (
            {
                "A_ORIGINAL_24X_ANCHOR": 0,
                "B_NEUTRAL_REPEATED_24X": 0,
                "C_NEUTRAL_DIVERSE_24_SEGMENT": 0,
            },
            "SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE",
        ),
        (
            {
                "A_ORIGINAL_24X_ANCHOR": 0,
                "B_NEUTRAL_REPEATED_24X": 3,
                "C_NEUTRAL_DIVERSE_24_SEGMENT": 0,
            },
            "DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED",
        ),
        (
            {
                "A_ORIGINAL_24X_ANCHOR": 0,
                "B_NEUTRAL_REPEATED_24X": 1,
                "C_NEUTRAL_DIVERSE_24_SEGMENT": 3,
            },
            "UNSTABLE_NO_MECHANISTIC_CLAIM",
        ),
        (
            {
                "A_ORIGINAL_24X_ANCHOR": 3,
                "B_NEUTRAL_REPEATED_24X": 3,
                "C_NEUTRAL_DIVERSE_24_SEGMENT": 3,
            },
            "ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE",
        ),
    )

    for exact_counts, expected_state in cases:
        results, workers, teardowns, counters = _decision_inputs(
            namespace,
            exact_counts,
        )
        observed = decide(results, workers, teardowns, counters)  # type: ignore[operator]
        assert observed["decision_state"] == expected_state


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
    assert record["p5_p6_requalification_authorized"] is False
    assert record["measured_abc_execution_authorized"] is False


def test_review_freezes_scientific_and_worker_contract(candidate_repo: Path) -> None:
    implementation.generate(candidate_repo)

    review = json.loads((candidate_repo / implementation.REVIEW_PATH).read_text(encoding="utf-8"))

    assert review["request_order"] == list(implementation.REQUEST_ORDER)
    assert review["observations_per_condition"] == 3
    assert review["prompt_token_count_per_condition"] == 899
    assert review["a_token_sha256"] == implementation.A_TOKEN_SHA256
    assert review["b_token_sha256"] == implementation.B_TOKEN_SHA256
    assert review["c_token_sha256"] == implementation.C_TOKEN_SHA256
    assert review["maximum_model_requests"] == 9
    assert review["maximum_model_loads"] == 9
    assert review["maximum_worker_starts"] == 9
    assert review["maximum_hidden_retries"] == 0
    assert review["maximum_replacement_observations"] == 0
    assert review["fresh_worker_process_per_observation"] is True
    assert review["teardown_required_between_observations"] is True
    assert review["zero_cached_prefix_baseline_required"] is True
    assert review["pre_request_journal_required"] is True
    assert review["anchor_reproduction_rule_preserved"] is True
    assert review["decision_contract_preserved"] is True
    assert review["bounded_lexical_novelty_caveat_preserved"] is True


def test_authority_drift_fails_closed(candidate_repo: Path) -> None:
    path = candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(implementation.ImplementationError) as captured:
        implementation.build_runtime_payload(candidate_repo)

    assert captured.value.error_code == (
        "P4_P5_TOKEN_MATCHED_STRUCTURE_IMPLEMENTATION_AUTHORITY_DRIFT"
    )


def test_frozen_comparator_prose_has_single_design_authority(
    candidate_repo: Path,
) -> None:
    design = json.loads((candidate_repo / implementation.DESIGN_PATH).read_text(encoding="utf-8"))
    source = (candidate_repo / implementation.SOURCE_PATH).read_text(encoding="utf-8")

    conditions = design["conditions"]
    assert isinstance(conditions, list)

    for condition in conditions:
        assert isinstance(condition, dict)
        segments = condition["segments"]
        assert isinstance(segments, list)
        for segment in set(segments):
            assert isinstance(segment, str)
            assert segment not in source


def test_runtime_comparator_material_is_rendered_from_frozen_design(
    candidate_repo: Path,
) -> None:
    design = json.loads((candidate_repo / implementation.DESIGN_PATH).read_text(encoding="utf-8"))
    namespace = _runtime_namespace(candidate_repo)

    conditions = {condition["condition_id"]: condition for condition in design["conditions"]}

    a_segments = tuple(conditions["A_ORIGINAL_24X_ANCHOR"]["segments"])
    b_segments = tuple(conditions["B_NEUTRAL_REPEATED_24X"]["segments"])
    c_segments = tuple(conditions["C_NEUTRAL_DIVERSE_24_SEGMENT"]["segments"])

    assert namespace["TOKEN_MATCHED_A_SEGMENT"] == a_segments[0]
    assert namespace["TOKEN_MATCHED_B_SEGMENT"] == b_segments[0]
    assert namespace["TOKEN_MATCHED_C_SEGMENTS"] == c_segments

    context = namespace["token_matched_context"]
    system_prompt = namespace["SYSTEM_PROMPT"]
    assert callable(context)
    assert isinstance(system_prompt, str)

    assert context("A_ORIGINAL_24X_ANCHOR") == "".join(a_segments) + system_prompt
    assert context("B_NEUTRAL_REPEATED_24X") == "".join(b_segments) + system_prompt
    assert context("C_NEUTRAL_DIVERSE_24_SEGMENT") == "".join(c_segments) + system_prompt
