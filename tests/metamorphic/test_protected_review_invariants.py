from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    ReviewAssignmentManifest,
)
from auragateway.contracts.episodes import EpisodeEvaluationSplit
from auragateway.contracts.protected_review import ProtectedReviewSubmissionSet
from auragateway.evals.protected_review import evaluate_protected_review_execution


def _load(path: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(Path(path).read_text(encoding="utf-8")),
    )


def _splits() -> dict[str, EpisodeEvaluationSplit]:
    return {
        f"ep-func-{index:03d}": (
            EpisodeEvaluationSplit.DEVELOPMENT if index <= 12 else EpisodeEvaluationSplit.HELD_OUT
        )
        for index in range(1, 19)
    }


def test_identity_digest_fields_do_not_change_aggregate_counts() -> None:
    assignments = ReviewAssignmentManifest.model_validate(
        _load("data/evals/quality/blinded-v1/assignment_manifest.json")
    )
    rubric = BlindedQualityRubric.model_validate(_load("data/evals/quality/blinded-v1/rubric.json"))
    original_payload = _load("data/evals/quality/execution-v1/submissions.json")
    mutated_payload = deepcopy(original_payload)
    for index, review in enumerate(mutated_payload["reviews"], start=1):
        review["reviewer_id_sha256"] = f"{index:064x}"[-64:]
        review["rationale_sha256"] = f"{index + 100:064x}"[-64:]
        for score_index, score in enumerate(review["criterion_scores"], start=1):
            score["evidence_note_sha256"] = f"{index * 10 + score_index:064x}"[-64:]

    original = evaluate_protected_review_execution(
        assignments,
        rubric,
        _splits(),
        ProtectedReviewSubmissionSet.model_validate(original_payload),
    )
    mutated = evaluate_protected_review_execution(
        assignments,
        rubric,
        _splits(),
        ProtectedReviewSubmissionSet.model_validate(mutated_payload),
    )

    assert original.held_out == mutated.held_out
    assert original.agreement == mutated.agreement
