from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.protected_review import ProtectedReviewSubmissionSet


def _load_submission_payload() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            Path("data/evals/quality/execution-v1/submissions.json").read_text(encoding="utf-8")
        ),
    )


def test_submission_set_rejects_duplicate_review_ids() -> None:
    payload = _load_submission_payload()
    reviews = list(cast(list[dict[str, Any]], payload["reviews"]))
    reviews.append(dict(reviews[0]))
    payload["reviews"] = reviews

    with pytest.raises(ValidationError, match="unique review IDs"):
        ProtectedReviewSubmissionSet.model_validate(payload)


def test_submission_set_rejects_duplicate_episode_adjudications() -> None:
    payload = _load_submission_payload()
    adjudications = list(cast(list[dict[str, Any]], payload["adjudications"]))
    adjudications.append(dict(adjudications[0]))
    payload["adjudications"] = adjudications

    with pytest.raises(ValidationError, match="one adjudication per episode"):
        ProtectedReviewSubmissionSet.model_validate(payload)


def test_submission_contract_forbids_human_review_claim() -> None:
    payload = _load_submission_payload()
    payload["human_review_completed"] = True

    with pytest.raises(ValidationError):
        ProtectedReviewSubmissionSet.model_validate(payload)
