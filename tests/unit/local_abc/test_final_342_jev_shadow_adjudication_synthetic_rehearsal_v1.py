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
    final_342_jev_shadow_adjudication_synthetic_rehearsal_v1 as rehearsal,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _fake_response_from_request(body: bytes) -> dict[str, Any]:
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
            "input_tokens": 400,
            "output_tokens": 100,
        },
    }


def test_synthetic_packet_models_dominant_label_mismatch() -> None:
    packet = rehearsal.build_synthetic_packet()

    assert packet.review_a.verdict.value == "fail"
    assert packet.review_b.verdict.value == "fail"
    assert packet.review_a.failure_labels != packet.review_b.failure_labels
    assert packet.disagreement_reasons == ("failure_label_mismatch",)


def test_synthetic_packet_is_jev_reviewer_safe() -> None:
    packet = rehearsal.build_synthetic_packet()

    safe = jev_contract.ReviewerSafeJevState(payload=packet.model_dump(mode="json"))

    assert safe.payload["purpose"] == "synthetic_shadow_adjudication_rehearsal"


def test_build_request_uses_full_typed_inventory(repo_root: Path) -> None:
    request = rehearsal.build_request(repo_root)

    assert request.model == "jev-1.13.0"
    assert len(request.questions) == len(RubricCriterion) + len(EpisodeFailureLabel)


def test_run_synthetic_rehearsal_validates_without_protected_evidence(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(
        rehearsal,
        "LOCAL_EVIDENCE_ROOT",
        Path(".local-test/jev-synthetic"),
    )

    def fake_post(
        url: str,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        assert url == "https://api.typesafe.ai/v1/systemone"
        assert headers["Authorization"] == "Bearer synthetic-test-key"
        return _fake_response_from_request(body)

    receipt = rehearsal.run_synthetic_rehearsal(
        repo_root,
        post_json=fake_post,
    )

    assert receipt.status == "FINAL_342_JEV_SYNTHETIC_REHEARSAL_PASS"
    assert receipt.resolved_model == "jev-1.13.0"
    assert receipt.question_count == len(RubricCriterion) + len(EpisodeFailureLabel)
    assert receipt.protected_final_342_data_sent is False
    assert receipt.human_adjudication_seen_by_jev is False
    assert receipt.authoritative_adjudication_created is False
    assert receipt.effect_claims_permitted is False
