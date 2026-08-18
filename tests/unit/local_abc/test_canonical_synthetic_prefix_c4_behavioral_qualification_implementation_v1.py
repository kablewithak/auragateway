from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from auragateway.local_abc import (
    canonical_synthetic_prefix_c4_behavioral_qualification_implementation_v1,
)

implementation = canonical_synthetic_prefix_c4_behavioral_qualification_implementation_v1


@pytest.fixture
def candidate_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    required = (
        implementation.QUALIFICATION_REQUEST_PATH,
        implementation.ARCHITECTURE_REVIEW_PATH,
        implementation.CANONICAL_CORPUS_PATH,
        implementation.REUSABLE_PREFIX_RECEIPT_PATH,
        implementation.PREDECESSOR_RUNTIME_PATH,
        implementation.FORMATTER_CONFIG_PATH,
        implementation.SOURCE_PATH,
        implementation.TEST_PATH,
    )
    for relative in required:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / relative, target)

    monkeypatch.setattr(
        implementation,
        "require_source_main_ancestor",
        lambda root: None,
    )
    monkeypatch.setattr(
        implementation,
        "source_bound_authority",
        lambda root, relative: (root / relative).read_bytes(),
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
    module_name = "auragateway_c4_static_candidate"
    module = ModuleType(module_name)
    module.__file__ = implementation.RUNTIME_PATH.as_posix()
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(
            compile(
                source,
                implementation.RUNTIME_PATH.as_posix(),
                "exec",
            ),
            module.__dict__,
        )
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        if previous is not None:
            sys.modules[module_name] = previous
    return dict(module.__dict__)


def _decision_inputs(
    exact_count: int,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, int],
]:
    results: list[dict[str, object]] = []
    for ordinal in range(1, 4):
        exact = ordinal <= exact_count
        results.append(
            {
                "observation_id": f"C4_OBSERVATION_{ordinal}",
                "request_ordinal": ordinal,
                "sequence_index": ordinal,
                "worker_instance_id": f"worker-{ordinal}",
                "worker_process_identity_sha256": f"worker-{ordinal}",
                "worker_start_receipt_sha256": "a" * 64,
                "token_count": (implementation.EXPECTED_FULL_PROMPT_TOKEN_COUNT),
                "token_sha256": (implementation.EXPECTED_FULL_PROMPT_TOKEN_SHA256),
                "reusable_prefix_token_count": (
                    implementation.EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT
                ),
                "reusable_prefix_token_sha256": (
                    implementation.EXPECTED_REUSABLE_PREFIX_TOKEN_SHA256
                ),
                "payload_sha256": (implementation.EXPECTED_REQUEST_PAYLOAD_SHA256),
                "zero_cache_baseline": True,
                "zero_cache_baseline_receipt_sha256": "b" * 64,
                "http_status": 200,
                "response_sha256": "c" * 64,
                "response_length": 44,
                "finish_reason": "stop",
                "prompt_tokens": 899,
                "completion_tokens": 17,
                "valid_json": exact,
                "duplicate_key_detected": False,
                "json_error_line": None,
                "json_error_column": None,
                "json_error_position": None,
                "json_root_type": "object" if exact else None,
                "parsed_key_set": (["probe", "value"] if exact else []),
                "probe_json_type": "string" if exact else None,
                "value_json_type": "integer" if exact else None,
                "probe_exact": exact,
                "value_exact": exact,
                "canonical_parsed_object_sha256": (
                    implementation.EXPECTED_OBJECT_SHA256 if exact else None
                ),
                "canonical_expected_object_sha256": (implementation.EXPECTED_OBJECT_SHA256),
                "leading_non_whitespace_content_detected": False,
                "trailing_non_whitespace_content_detected": False,
                "markdown_fence_detected": False,
                "response_complete": True,
                "exact_object": exact,
                "worker_health_after_request": True,
                "teardown_status": "PASSED",
                "request_error": None,
                "transport_error": None,
                "metric_delta": {},
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            }
        )

    workers: list[dict[str, object]] = [{"worker": ordinal} for ordinal in range(1, 4)]
    teardowns: list[dict[str, object]] = [{"status": "PASSED"} for _ in range(3)]
    counters = {
        "model_requests": 3,
        "model_loads": 3,
        "worker_starts": 3,
        "hidden_retries": 0,
        "network_requests": 0,
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
    }
    return results, workers, teardowns, counters


def test_predecessor_runtime_is_immutable(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH
    before = path.read_bytes()
    implementation.generate(candidate_repo)
    after = path.read_bytes()

    assert before == after
    assert implementation._sha256(after) == implementation.EXPECTED_PREDECESSOR_RUNTIME_SHA256


def test_successor_runtime_compiles_and_only_main_changes(
    candidate_repo: Path,
) -> None:
    predecessor = (candidate_repo / implementation.PREDECESSOR_RUNTIME_PATH).read_text(
        encoding="utf-8"
    )
    runtime, unchanged = implementation.build_runtime_payload(candidate_repo)
    successor = runtime.decode("utf-8")

    compile(
        successor,
        implementation.RUNTIME_PATH.as_posix(),
        "exec",
    )

    before = implementation._function_segments(predecessor)
    after = implementation._function_segments(successor)
    changed = tuple(sorted(name for name, body in before.items() if after[name] != body))

    assert changed == implementation.CHANGED_EXISTING_FUNCTIONS
    assert set(after) == set(before) | set(implementation.ADDED_FUNCTIONS)
    assert unchanged > 0


def test_generated_runtime_is_bound_ruff_canonical(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    probe = candidate_repo / "generated_runtime_formatter_probe.py"
    probe.write_bytes(runtime)

    version = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        cwd=candidate_repo,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert version.returncode == 0
    assert version.stdout.strip() == implementation.FORMATTER_VERSION

    config = candidate_repo / implementation.FORMATTER_CONFIG_PATH
    assert implementation._sha256(config.read_bytes()) == (implementation.FORMATTER_CONFIG_SHA256)

    formatted_check = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "--config",
            str(config),
            str(probe),
        ],
        cwd=candidate_repo,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert formatted_check.returncode == 0
    assert probe.read_bytes() == runtime


def test_c4_request_composition_and_payload_identity_are_frozen(
    candidate_repo: Path,
) -> None:
    namespace = _runtime_namespace(candidate_repo)
    request_payload = cast(
        Callable[[], dict[str, object]],
        namespace["c4_request_payload"],
    )
    canonical_json = cast(
        Callable[[object], str],
        namespace["canonical_json"],
    )
    sha256_text = cast(
        Callable[[str], str],
        namespace["sha256_text"],
    )

    payload = request_payload()
    messages = payload["messages"]
    assert isinstance(messages, list)
    assert [item["role"] for item in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]

    corpus_text = (candidate_repo / implementation.CANONICAL_CORPUS_PATH).read_text(
        encoding="utf-8"
    )
    system_prompt = namespace["SYSTEM_PROMPT"]
    assert isinstance(system_prompt, str)
    assert messages[1]["content"] == (corpus_text + " " + system_prompt)
    assert messages[3]["content"] == (implementation.EXPECTED_OBJECT_CANONICAL)

    assert payload["temperature"] == 0
    assert payload["top_p"] == 1
    assert payload["repetition_penalty"] == 1.1
    assert payload["seed"] == 7
    assert payload["max_tokens"] == 32
    assert payload["stream"] is False
    assert "response_format" not in payload
    assert "guided_decoding" not in payload

    observed_sha = sha256_text(canonical_json(payload))
    assert observed_sha == (implementation.EXPECTED_REQUEST_PAYLOAD_SHA256)


def test_strict_response_validator_rejects_json_loopholes(
    candidate_repo: Path,
) -> None:
    namespace = _runtime_namespace(candidate_repo)
    project = cast(
        Callable[[str, object], dict[str, object]],
        namespace["c4_response_projection"],
    )

    canonical = project(
        implementation.EXPECTED_OBJECT_CANONICAL,
        "stop",
    )
    assert canonical["exact_object"] is True
    assert canonical["value_json_type"] == "integer"
    assert canonical["response_complete"] is True
    assert canonical["canonical_parsed_object_sha256"] == (implementation.EXPECTED_OBJECT_SHA256)

    boolean_value = project(
        '{"probe":"exact-runtime-p5-p6","value":true}',
        "stop",
    )
    assert boolean_value["exact_object"] is False
    assert boolean_value["value_json_type"] == "boolean"

    float_value = project(
        '{"probe":"exact-runtime-p5-p6","value":1.0}',
        "stop",
    )
    assert float_value["exact_object"] is False
    assert float_value["value_json_type"] == "number"

    duplicate = project(
        ('{"probe":"wrong","probe":"exact-runtime-p5-p6","value":1}'),
        "stop",
    )
    assert duplicate["duplicate_key_detected"] is True
    assert duplicate["exact_object"] is False

    extra_key = project(
        '{"probe":"exact-runtime-p5-p6","value":1,"extra":0}',
        "stop",
    )
    assert extra_key["exact_object"] is False

    incomplete = project(
        implementation.EXPECTED_OBJECT_CANONICAL,
        "length",
    )
    assert incomplete["response_complete"] is False
    assert incomplete["exact_object"] is False

    trailing = project(
        implementation.EXPECTED_OBJECT_CANONICAL + " prose",
        "stop",
    )
    assert trailing["trailing_non_whitespace_content_detected"] is True
    assert trailing["exact_object"] is False

    fenced = project(
        "```json\n" + implementation.EXPECTED_OBJECT_CANONICAL + "\n```",
        "stop",
    )
    assert fenced["markdown_fence_detected"] is True
    assert fenced["exact_object"] is False


def test_three_of_three_is_required_but_behavioral_failure_is_valid(
    candidate_repo: Path,
) -> None:
    namespace = _runtime_namespace(candidate_repo)
    decide = cast(
        Callable[
            [
                list[dict[str, object]],
                list[dict[str, object]],
                list[dict[str, object]],
                dict[str, int],
            ],
            dict[str, object],
        ],
        namespace["decide_c4_qualification"],
    )

    qualified = decide(*_decision_inputs(3))
    assert qualified["observed_terminal_state"] == "QUALIFIED"
    assert qualified["exact_object_count"] == 3
    assert qualified["qualification_accepted_by_repository"] is False

    not_qualified = decide(*_decision_inputs(2))
    assert not_qualified["observed_terminal_state"] == "NOT_QUALIFIED"
    assert not_qualified["exact_object_count"] == 2
    assert not_qualified["complete_behavioral_run"] is True
    assert not_qualified["p5_requalified"] is False
    assert not_qualified["p6_requalified"] is False


def test_c4_main_owns_only_runtime_enforceable_budget(
    candidate_repo: Path,
) -> None:
    runtime, _ = implementation.build_runtime_payload(candidate_repo)
    source = runtime.decode("utf-8")

    assert implementation._literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    ) == {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 3,
        "worker_starts": 3,
        "model_requests": 3,
    }

    main = _function_source(source, "main")
    assert "run_c4_fresh_worker_observation(" in main
    assert "decide_c4_qualification(" in main
    assert "range(1, C4_OBSERVATION_COUNT + 1)" in main
    assert "kaggle_sessions" not in main
    assert "B_VS_D_REQUEST_ORDER" not in main
    assert "decide_marker_diversified_differential(" not in main
    assert "decide_p5(" not in main
    assert "decide_p6(" not in main


def test_evidence_names_and_lineage_contract_are_frozen(
    candidate_repo: Path,
) -> None:
    namespace = _runtime_namespace(candidate_repo)

    output_names = cast(
        tuple[str, ...],
        namespace["C4_OUTPUT_NAMES"],
    )
    assert output_names == implementation.C4_OUTPUT_NAMES

    implementation.generate(candidate_repo)
    review = json.loads((candidate_repo / implementation.REVIEW_PATH).read_text(encoding="utf-8"))
    record = json.loads((candidate_repo / implementation.RECORD_PATH).read_text(encoding="utf-8"))

    assert review["platform_budget_deferred_to_authorization_wrapper"] is True
    assert review["kaggle_session_budget_runtime_enforced"] is False
    assert review["save_and_run_all_budget_runtime_enforced"] is False
    assert review["p5_p6_successor_lineage_parent"] is True
    assert review["formatter_version"] == implementation.FORMATTER_VERSION
    assert review["formatter_config_sha256"] == (implementation.FORMATTER_CONFIG_SHA256)
    assert review["runtime_formatter_canonicalized"] is True
    assert review["predecessor_formatter_canonical"] is True
    assert review["formatter_idempotence_verified"] is True
    assert record["formatter_version"] == implementation.FORMATTER_VERSION
    assert record["formatter_config_sha256"] == (implementation.FORMATTER_CONFIG_SHA256)
    assert record["runtime_formatter_canonicalized"] is True
    assert record["p5_p6_successor_must_derive_from_this_runtime"] is True


def test_generate_validate_are_byte_deterministic_and_execution_inert(
    candidate_repo: Path,
) -> None:
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
    assert record["c4_qualified"] is False
    assert record["p5_requalified"] is False
    assert record["p6_requalified"] is False


def test_reusable_prefix_receipt_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    receipt_path = candidate_repo / implementation.REUSABLE_PREFIX_RECEIPT_PATH
    receipt_path.write_bytes(receipt_path.read_bytes() + b"\n")

    with pytest.raises(implementation.C4ImplementationError) as captured:
        implementation.build_runtime_payload(candidate_repo)

    assert captured.value.error_code == ("C4_IMPLEMENTATION_REUSABLE_PREFIX_RECEIPT_DRIFT")


def test_qualification_request_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    request_path = candidate_repo / implementation.QUALIFICATION_REQUEST_PATH
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    payload["runtime_execution_authorized"] = True
    request_path.write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(implementation.C4ImplementationError) as captured:
        implementation.build_runtime_payload(candidate_repo)

    assert captured.value.error_code == ("C4_IMPLEMENTATION_REQUEST_DRIFT")
