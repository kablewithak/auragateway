from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from auragateway.local_abc import (
    c4_paragraph_order_behavioral_differential_implementation_v1,
)

implementation = c4_paragraph_order_behavioral_differential_implementation_v1


@pytest.fixture
def candidate_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    source_root = Path(__file__).resolve().parents[3]

    for relative in (
        implementation.DESIGN_PATH,
        implementation.PREDECESSOR_RUNTIME_PATH,
        implementation.SOURCE_PATH,
        implementation.TEST_PATH,
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            source_root / relative,
            target,
        )

    monkeypatch.setattr(
        implementation,
        "_base_commit_is_ancestor_of_head",
        lambda root: True,
    )

    return tmp_path


def test_merged_design_and_predecessor_are_bound(
    candidate_repo: Path,
) -> None:
    design, predecessor = implementation._validate_authorities(candidate_repo)

    assert implementation._sha256(design) == implementation.DESIGN_SHA256
    assert implementation._sha256(predecessor) == implementation.PREDECESSOR_RUNTIME_SHA256


def test_unrelated_lineage_fails_closed(
    candidate_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        implementation,
        "_base_commit_is_ancestor_of_head",
        lambda root: False,
    )

    with pytest.raises(implementation.ImplementationError) as captured:
        implementation._validate_authorities(candidate_repo)

    assert captured.value.error_code == ("C4_PARAGRAPH_ORDER_IMPLEMENTATION_BASE_MAIN_DRIFT")


def test_runtime_generation_preserves_exact_order_intervention(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)
    runtime = implementation.load_generated_runtime(candidate_repo)

    control = runtime.order_context(implementation.CONTROL_CONDITION)
    treatment = runtime.order_context(implementation.TREATMENT_CONDITION)

    assert len(control) == len(treatment)

    system_prompt = runtime.SYSTEM_PROMPT

    control_body = control[: -len(system_prompt)].rstrip(" \t\r\n")
    treatment_body = treatment[: -len(system_prompt)].rstrip(" \t\r\n")

    control_paragraphs = control_body.split("\n\n")
    treatment_paragraphs = treatment_body.split("\n\n")

    assert len(control_paragraphs) == 10
    assert len(treatment_paragraphs) == 10

    assert treatment_paragraphs == [
        control_paragraphs[0],
        *reversed(control_paragraphs[1:9]),
        control_paragraphs[9],
    ]


def test_runtime_payload_identities_are_frozen(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)
    runtime = implementation.load_generated_runtime(candidate_repo)

    control_payload = runtime.order_request_payload(implementation.CONTROL_CONDITION)
    treatment_payload = runtime.order_request_payload(implementation.TREATMENT_CONDITION)

    control_sha = runtime.sha256_text(runtime.canonical_json(control_payload))
    treatment_sha = runtime.sha256_text(runtime.canonical_json(treatment_payload))

    assert control_sha == implementation.CONTROL_REQUEST_PAYLOAD_SHA256

    review = json.loads((candidate_repo / implementation.REVIEW_PATH).read_text(encoding="utf-8"))
    assert treatment_sha == review["treatment_request_payload_sha256"]

    assert control_payload["temperature"] == 0
    assert control_payload["top_p"] == 1
    assert control_payload["repetition_penalty"] == 1.1
    assert control_payload["seed"] == 7
    assert control_payload["max_tokens"] == 32
    assert control_payload["stream"] is False

    assert treatment_payload["temperature"] == 0
    assert treatment_payload["top_p"] == 1
    assert treatment_payload["repetition_penalty"] == 1.1
    assert treatment_payload["seed"] == 7
    assert treatment_payload["max_tokens"] == 32
    assert treatment_payload["stream"] is False


def _observation(
    condition_id: str,
    sequence_index: int,
    parsed_sha256: str | None,
    *,
    exact_object: bool = False,
    valid_json: bool = True,
) -> dict[str, object]:
    token_sha256 = (
        implementation.CONTROL_TOKEN_SHA256
        if condition_id == implementation.CONTROL_CONDITION
        else implementation.TREATMENT_TOKEN_SHA256
    )

    return {
        "condition_id": condition_id,
        "sequence_index": sequence_index,
        "worker_process_identity_sha256": f"{sequence_index:064x}",
        "token_count": 899,
        "token_sha256": token_sha256,
        "reusable_prefix_token_count": 880,
        "payload_sha256": "PLACEHOLDER",
        "zero_cache_baseline": True,
        "http_status": 200,
        "finish_reason": "stop",
        "response_complete": True,
        "worker_health_after_request": True,
        "teardown_status": "PASSED",
        "valid_json": valid_json,
        "exact_object": exact_object,
        "canonical_parsed_object_sha256": parsed_sha256,
    }


def _decision_fixture(
    runtime: ModuleType,
    treatment_parsed_sha256: str | None,
    *,
    treatment_exact: bool = False,
    treatment_valid_json: bool = True,
    control_parsed_sha256: str | None = None,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, int],
]:
    historical = (
        implementation.HISTORICAL_CONTROL_PARSED_OBJECT_SHA256
        if control_parsed_sha256 is None
        else control_parsed_sha256
    )

    rows: list[dict[str, object]] = []
    for sequence_index, condition_id in enumerate(
        implementation.REQUEST_ORDER,
        start=1,
    ):
        if condition_id == implementation.CONTROL_CONDITION:
            row = _observation(
                condition_id,
                sequence_index,
                historical,
            )
        else:
            row = _observation(
                condition_id,
                sequence_index,
                treatment_parsed_sha256,
                exact_object=treatment_exact,
                valid_json=treatment_valid_json,
            )

        row["payload_sha256"] = runtime.order_expected_payload_sha256(condition_id)
        rows.append(row)

    workers: list[dict[str, object]] = [{"worker": index} for index in range(1, 7)]
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

    return rows, workers, teardowns, counters


def test_frozen_decision_matrix_is_realized(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)
    runtime = implementation.load_generated_runtime(candidate_repo)

    rows, workers, teardowns, counters = _decision_fixture(
        runtime,
        runtime.C4_EXPECTED_OBJECT_SHA256,
        treatment_exact=True,
    )
    decision = runtime.decide_order_differential(
        rows,
        workers,
        teardowns,
        counters,
    )
    assert decision["observed_terminal_state"] == ("ORDER_INTERVENTION_RESTORES_BEHAVIOR")

    rows, workers, teardowns, counters = _decision_fixture(
        runtime,
        implementation.HISTORICAL_CONTROL_PARSED_OBJECT_SHA256,
    )
    decision = runtime.decide_order_differential(
        rows,
        workers,
        teardowns,
        counters,
    )
    assert decision["observed_terminal_state"] == (
        "ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE"
    )

    changed_sha = "a" * 64
    rows, workers, teardowns, counters = _decision_fixture(
        runtime,
        changed_sha,
    )
    decision = runtime.decide_order_differential(
        rows,
        workers,
        teardowns,
        counters,
    )
    assert decision["observed_terminal_state"] == ("ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE")

    rows, workers, teardowns, counters = _decision_fixture(
        runtime,
        None,
        treatment_valid_json=False,
    )
    decision = runtime.decide_order_differential(
        rows,
        workers,
        teardowns,
        counters,
    )
    assert decision["observed_terminal_state"] == ("ORDER_INTERVENTION_EFFECT_AMBIGUOUS")


def test_control_anchor_nonreproduction_dominates_treatment(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)
    runtime = implementation.load_generated_runtime(candidate_repo)

    rows, workers, teardowns, counters = _decision_fixture(
        runtime,
        runtime.C4_EXPECTED_OBJECT_SHA256,
        treatment_exact=True,
        control_parsed_sha256="b" * 64,
    )

    decision = runtime.decide_order_differential(
        rows,
        workers,
        teardowns,
        counters,
    )

    assert decision["observed_terminal_state"] == (
        "CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
    )


def test_generated_runtime_main_uses_six_observation_plan(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)

    runtime_source = (candidate_repo / implementation.RUNTIME_PATH).read_text(encoding="utf-8")

    assert "ORDER_REQUEST_ORDER" in runtime_source
    assert "run_order_fresh_worker_observation" in runtime_source
    assert "decide_order_differential" in runtime_source

    runtime = implementation.load_generated_runtime(candidate_repo)

    assert runtime.ORDER_REQUEST_ORDER == implementation.REQUEST_ORDER
    assert runtime.ACTION_BUDGET_LIMITS["model_requests"] == 6
    assert runtime.ACTION_BUDGET_LIMITS["worker_starts"] == 6
    assert runtime.ACTION_BUDGET_LIMITS["model_loads"] == 6


def test_static_implementation_is_execution_inert(
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
    assert record["live_authorization_issued"] is False
    assert record["runtime_execution_authorized"] is False
    assert record["new_execution_authorized"] is False


def test_generation_is_byte_deterministic(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)

    first = tuple(
        (candidate_repo / path).read_bytes()
        for path in (
            implementation.RUNTIME_PATH,
            implementation.REVIEW_PATH,
            implementation.RECORD_PATH,
        )
    )

    implementation.validate_generated(candidate_repo)

    second = tuple(
        (candidate_repo / path).read_bytes()
        for path in (
            implementation.RUNTIME_PATH,
            implementation.REVIEW_PATH,
            implementation.RECORD_PATH,
        )
    )

    assert first == second


def test_generated_runtime_is_canonical_and_idempotent(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)

    runtime_path = candidate_repo / implementation.RUNTIME_PATH
    runtime_source = runtime_path.read_text(encoding="utf-8")

    assert "\r\n" not in runtime_source
    assert runtime_source.endswith("\n")
    assert (
        implementation._canonicalize_runtime_source(
            candidate_repo,
            runtime_source,
        )
        == runtime_source
    )


def test_authority_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / implementation.DESIGN_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(implementation.ImplementationError) as captured:
        implementation._validate_authorities(candidate_repo)

    assert captured.value.error_code == ("C4_PARAGRAPH_ORDER_IMPLEMENTATION_AUTHORITY_DRIFT")


def test_generated_runtime_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    implementation.generate(candidate_repo)

    path = candidate_repo / implementation.RUNTIME_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(implementation.ImplementationError) as captured:
        implementation.validate_generated(candidate_repo)

    assert captured.value.error_code == ("C4_PARAGRAPH_ORDER_IMPLEMENTATION_GENERATED_DRIFT")
