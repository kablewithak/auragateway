from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.benchmark.preflight import build_run_ledger, canonical_model_sha256
from auragateway.contracts.benchmark_preflight import (
    BenchmarkPlanRequest,
    BenchmarkPreflightInput,
)

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data/evals/benchmark/preflight-v1/input.json"


def load_input() -> BenchmarkPreflightInput:
    return BenchmarkPreflightInput.model_validate_json(INPUT_PATH.read_text(encoding="utf-8"))


def test_plan_is_byte_stable_across_repeated_expansion() -> None:
    request = load_input().plan_request

    first = build_run_ledger(request)
    second = build_run_ledger(request)

    assert first == second
    assert canonical_model_sha256(first) == canonical_model_sha256(second)


def test_reordered_functional_episode_ids_are_rejected() -> None:
    request = load_input().plan_request
    payload = request.model_dump(mode="json")
    payload["functional_episode_ids"] = list(reversed(payload["functional_episode_ids"]))

    with pytest.raises(ValidationError, match="must be sorted"):
        BenchmarkPlanRequest.model_validate(payload)


def test_duplicate_runtime_episode_is_rejected() -> None:
    request = load_input().plan_request
    payload = request.model_dump(mode="json")
    payload["runtime_episode_ids"][1] = payload["runtime_episode_ids"][0]

    with pytest.raises(ValidationError, match="must be unique"):
        BenchmarkPlanRequest.model_validate(payload)


def test_plan_contains_no_raw_prompt_or_provider_payload_fields() -> None:
    plan = build_run_ledger(load_input().plan_request)
    payload = plan.model_dump_json()

    assert "raw_prompt" not in payload
    assert "provider_payload" not in payload
    assert "user_message" not in payload
    assert "api_key" not in payload
