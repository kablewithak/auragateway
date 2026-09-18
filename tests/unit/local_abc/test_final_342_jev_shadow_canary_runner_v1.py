from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auragateway.contracts.blinded_quality import RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_runner_v1 as runner,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_v1 as canary,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as review_bridge,
)


def _response_from_request(body: bytes) -> dict[str, Any]:
    request = json.loads(body.decode("utf-8"))
    answers: dict[str, Any] = {}

    for name, question in request["questions"].items():
        if question["type"] == "choice":
            answers[name] = {
                "type": "choice",
                "choice": "2",
                "probabilities": {
                    "1": 0.10,
                    "2": 0.70,
                    "3": 0.15,
                    "4": 0.05,
                },
                "confidence": 0.8,
            }
        else:
            answers[name] = {
                "type": "noul",
                "noul": 0.75,
            }

    return {
        "model": "jev-1.13.0",
        "answers": answers,
        "usage": {
            "input_tokens": 500,
            "output_tokens": 120,
        },
    }


def _install_frozen_canary(root: Path) -> None:
    questions: dict[str, Any] = {}

    for criterion in RubricCriterion:
        questions[jev_contract.criterion_question_name(criterion)] = {
            "type": "choice",
            "instructions": "Choose one frozen rubric score for this synthetic case.",
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
            "instructions": f"Estimate whether failure label {label.value} applies.",
        }

    request = jev_contract.JevShadowRequest.model_validate(
        {
            "state": '{"synthetic":"real-canary-shaped-test"}',
            "model": "jev-1.13.0",
            "questions": questions,
        }
    )
    request_payload = request.model_dump(mode="json")
    request_bytes = runner._canonical_bytes(request_payload)

    request_path = root / canary.CANARY_REQUEST_PATH
    manifest_path = root / canary.CANARY_MANIFEST_PATH
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_bytes(request_bytes)

    manifest = canary.JevCanaryManifest(
        review_item_id="a" * 64,
        episode_id="ep-func-001",
        question_count=29,
        criterion_question_count=7,
        failure_question_count=22,
        material_disagreement_count=35,
        verdict_mismatch_count=0,
        material_score_delta_count=4,
        failure_label_mismatch_count=35,
        request_sha256=runner._sha256_bytes(request_bytes),
    )
    manifest_path.write_bytes(runner._canonical_bytes(manifest.model_dump(mode="json")))


def test_live_canary_performs_one_request_and_persists_local_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(
        review_bridge,
        "REVIEW_RESULT_ROOT",
        Path(".local-test/reviews"),
    )

    _install_frozen_canary(tmp_path)
    calls = 0

    def fake_post(
        url: str,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert url == "https://api.typesafe.ai/v1/systemone"
        assert headers["Authorization"] == "Bearer test-key"
        return _response_from_request(body)

    receipt = runner.run_live_canary(tmp_path, post_json=fake_post)

    assert calls == 1
    assert receipt.provider_request_performed is True
    assert receipt.provider_request_count_this_invocation == 1
    assert receipt.protected_final_342_data_sent is True
    assert receipt.human_adjudication_seen_by_jev is False
    assert receipt.authoritative_adjudication_created is False
    assert receipt.effect_claims_permitted is False
    assert (tmp_path / runner.CANARY_RESPONSE_PATH).is_file()
    assert (tmp_path / runner.CANARY_RECEIPT_PATH).is_file()


def test_live_canary_is_anti_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(
        review_bridge,
        "REVIEW_RESULT_ROOT",
        Path(".local-test/reviews"),
    )

    _install_frozen_canary(tmp_path)
    calls = 0

    def fake_post(
        _url: str,
        _headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _response_from_request(body)

    first = runner.run_live_canary(tmp_path, post_json=fake_post)
    second = runner.run_live_canary(tmp_path, post_json=fake_post)

    assert calls == 1
    assert first.provider_request_performed is True
    assert second.provider_request_performed is False
    assert second.provider_request_count_this_invocation == 0
    assert second.response_sha256 == first.response_sha256
