from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter_hy3_review_supersession import (
    OpenRouterHy3HistoricalReviewSupersession,
    OpenRouterHy3SupersededPath,
    OpenRouterHy3SupersessionScope,
)

_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-historical-review-supersession-v1/"
    "supersession.json"
)


def _payload() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_PATH.read_text(encoding="utf-8")))


def test_supersession_contract_accepts_frozen_overlay() -> None:
    model = OpenRouterHy3HistoricalReviewSupersession.model_validate(_payload())

    assert len(model.bindings) == 4
    assert model.historical_evidence_mutation_permitted is False
    assert model.provider_execution_reopened is False


def test_supersession_contract_requires_exact_binding_sites() -> None:
    payload = _payload()
    bindings = cast(list[dict[str, object]], payload["bindings"])
    bindings[0]["scope"] = OpenRouterHy3SupersessionScope.AUTHORIZATION_REVIEW_SOURCE

    with pytest.raises(ValidationError, match="four exact historical binding sites"):
        OpenRouterHy3HistoricalReviewSupersession.model_validate(payload)


def test_supersession_contract_rejects_historical_hash_rewrite() -> None:
    payload = _payload()
    bindings = cast(list[dict[str, object]], payload["bindings"])
    bindings[0]["historical_sha256"] = "0" * 64

    with pytest.raises(ValidationError, match="frozen lineage"):
        OpenRouterHy3HistoricalReviewSupersession.model_validate(payload)


def test_supersession_contract_covers_only_two_documents() -> None:
    model = OpenRouterHy3HistoricalReviewSupersession.model_validate(_payload())

    assert {binding.path for binding in model.bindings} == {
        OpenRouterHy3SupersededPath.MINI_PRD,
        OpenRouterHy3SupersededPath.CORE_PRD,
    }
