from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auragateway.contracts.blinded_quality import DisagreementReason, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_batch_freeze_v1 as batch_freeze,
)
from auragateway.local_abc import (
    final_342_jev_shadow_batch_runner_v1 as runner,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_runner_v1 as canary_runner,
)


def _fake_request(index: int) -> jev_contract.JevShadowRequest:
    questions: dict[str, Any] = {}

    for criterion in RubricCriterion:
        questions[jev_contract.criterion_question_name(criterion)] = {
            "type": "choice",
            "instructions": "Choose one frozen rubric score for the test case.",
            "criteria": {
                "1": "one",
                "2": "two",
                "3": "three",
                "4": "four",
            },
        }

    for label in EpisodeFailureLabel:
        questions[jev_contract.failure_question_name(label)] = {
            "type": "noul",
            "instructions": f"Estimate whether {label.value} applies.",
        }

    return jev_contract.JevShadowRequest.model_validate(
        {
            "state": json.dumps({"test_case_index": index}),
            "model": "jev-1.13.0",
            "questions": questions,
        }
    )


def _fake_response(body: bytes) -> dict[str, Any]:
    request = json.loads(body.decode("utf-8"))
    answers: dict[str, Any] = {}

    for name, question in request["questions"].items():
        if question["type"] == "choice":
            answers[name] = {
                "type": "choice",
                "choice": "3",
                "probabilities": {
                    "1": 0.05,
                    "2": 0.10,
                    "3": 0.80,
                    "4": 0.05,
                },
                "confidence": 0.85,
            }
        else:
            answers[name] = {
                "type": "noul",
                "noul": 0.25,
            }

    return {
        "model": "jev-1.13.0",
        "answers": answers,
        "usage": {
            "input_tokens": 500,
            "output_tokens": 120,
        },
    }


def _entry(root: Path, index: int) -> tuple[batch_freeze.FrozenBatchEntry, bytes]:
    request = _fake_request(index)
    request_bytes = runner._canonical_bytes(request.model_dump(mode="json"))
    request_hash = runner._sha256_bytes(request_bytes)
    relative = batch_freeze.BATCH_REQUEST_ROOT / f"{index:02d}-{index:064x}.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(request_bytes)

    return (
        batch_freeze.FrozenBatchEntry(
            batch_index=index,
            review_item_id=f"{index:064x}",
            episode_id=f"ep-func-{index:03d}",
            request_relative_path=relative.as_posix(),
            request_sha256=request_hash,
            disagreement_reasons=(DisagreementReason.FAILURE_LABEL_MISMATCH,),
            criterion_score_deltas={criterion: 0 for criterion in RubricCriterion},
            lifecycle_state=("EXECUTED_CANARY" if index == 0 else "FROZEN_PENDING"),
            provider_request_already_performed=index == 0,
            response_sha256=(batch_freeze.EXPECTED_CANARY_RESPONSE_SHA256 if index == 0 else None),
        ),
        request_bytes,
    )


def test_execute_one_is_write_ahead_and_anti_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    entry, request_bytes = _entry(tmp_path, 1)
    request = _fake_request(1)
    calls = 0

    def fake_post(
        _url: str,
        _headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert runner._attempt_path(tmp_path, entry).is_file()
        return _fake_response(body)

    first = runner._execute_one(
        tmp_path,
        entry,
        request,
        request_bytes,
        post_json=fake_post,
    )
    existing = runner._load_existing_execution(tmp_path, entry, request)

    assert calls == 1
    assert first.status == "FINAL_342_JEV_SHADOW_CASE_PASS"
    assert existing is not None
    assert existing.response_sha256 == first.response_sha256


def test_orphan_attempt_marker_blocks_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    entry, _request_bytes = _entry(tmp_path, 2)
    request = _fake_request(2)

    marker = runner.BatchAttemptMarker(
        batch_index=entry.batch_index,
        review_item_id=entry.review_item_id,
        episode_id=entry.episode_id,
        request_sha256=entry.request_sha256,
    )
    attempt_path = runner._attempt_path(tmp_path, entry)
    attempt_path.parent.mkdir(parents=True, exist_ok=True)
    attempt_path.write_bytes(runner._canonical_bytes(marker.model_dump(mode="json")))

    with pytest.raises(
        runner.JevBatchRunnerError,
        match="manual reconciliation required",
    ):
        runner._load_existing_execution(tmp_path, entry, request)


def test_provider_failure_leaves_attempt_marker_and_no_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    entry, request_bytes = _entry(tmp_path, 3)
    request = _fake_request(3)

    def fail_post(
        _url: str,
        _headers: dict[str, str],
        _body: bytes,
    ) -> dict[str, Any]:
        raise canary_runner.JevCanaryExecutionError(
            "SYNTHETIC_PROVIDER_FAILURE",
            "synthetic provider failure",
        )

    with pytest.raises(
        runner.JevBatchRunnerError,
        match="automatic retry prohibited",
    ):
        runner._execute_one(
            tmp_path,
            entry,
            request,
            request_bytes,
            post_json=fail_post,
        )

    assert runner._attempt_path(tmp_path, entry).is_file()
    assert not runner._execution_path(tmp_path, entry).exists()
