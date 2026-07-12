from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from auragateway.contracts.retrieval_gate import GateOneDecisionStatus
from auragateway.contracts.retrieval_gate_v2 import (
    HeldOutV2FreezeRecord,
    HeldOutV2ValidationPolicy,
    HeldOutV2ValidationReport,
    RetrievalFreezeManifestV1,
)

ROOT = Path("data/evals/retrieval/held-out-v2")


def test_held_out_v2_freeze_precedes_candidate_results() -> None:
    record = HeldOutV2FreezeRecord.model_validate_json(
        (ROOT / "freeze_record.json").read_text(encoding="utf-8")
    )

    assert record.record_id == "nimbus-relay-held-out-freeze-v2"
    assert record.authoring_complete is True
    assert record.candidate_results_present_at_freeze is False


def test_held_out_v2_policy_locks_remediated_development_ranks() -> None:
    policy = HeldOutV2ValidationPolicy.model_validate_json(
        (ROOT / "policy.json").read_text(encoding="utf-8")
    )

    assert [item.development_rank for item in policy.finalists] == [1, 2]
    assert {item.top_k for item in policy.finalists} == {5}
    assert all("remediated-v2" in item.retriever_config_id for item in policy.finalists)


def test_gate_one_v2_reverses_development_ranking_and_freezes_dense() -> None:
    report = HeldOutV2ValidationReport.model_validate_json(
        (ROOT / "decision.json").read_text(encoding="utf-8")
    )
    freeze = RetrievalFreezeManifestV1.model_validate_json(
        Path("data/retrieval/frozen-v1/manifest.json").read_text(encoding="utf-8")
    )

    assert report.decision.status is GateOneDecisionStatus.REVERSED
    assert report.decision.gate_1_passed is True
    assert report.decision.selected_retriever_config_id == (
        "dense-hashed-tfidf-section-aware-remediated-v2"
    )
    assert freeze.selected_retriever_config_id == report.decision.selected_retriever_config_id
    assert freeze.selected_top_k == 5
    assert freeze.measured_execution_permitted is False


def test_policy_rejects_duplicate_development_ranks() -> None:
    payload = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))
    payload["finalists"][1]["development_rank"] = 1

    try:
        HeldOutV2ValidationPolicy.model_validate(payload)
    except ValidationError as exc:
        assert "unique development ranks one and two" in str(exc)
        return
    raise AssertionError("held-out v2 policy accepted duplicate development ranks")
