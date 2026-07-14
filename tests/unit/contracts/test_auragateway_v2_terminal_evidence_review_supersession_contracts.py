from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.auragateway_v2_terminal_evidence_review import (
    AuraGatewayV2TerminalEvidenceReviewSupersession,
    OpenRouterHy3TerminalEvidenceReviewManifest,
)

_SUPERSESSION_PATH = Path(
    "data/evals/benchmark/auragateway-v2-terminal-evidence-review-supersession-v1/supersession.json"
)
_SUPERSEDING_MANIFEST_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/manifest.json"
)


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_supersession_contract_accepts_frozen_overlay() -> None:
    model = AuraGatewayV2TerminalEvidenceReviewSupersession.model_validate(
        _json_object(_SUPERSESSION_PATH)
    )

    assert model.historical_manifest_immutable is True
    assert model.provider_execution_permitted is False
    assert len(model.assets) == 3


def test_superseding_manifest_contract_accepts_terminal_continuity() -> None:
    model = OpenRouterHy3TerminalEvidenceReviewManifest.model_validate(
        _json_object(_SUPERSEDING_MANIFEST_PATH)
    )

    assert model.terminal_outcome == "closed_terminal_provider_failure"
    assert model.comparison_eligible is False
    assert model.runtime_rerun_permitted is False


def test_supersession_contract_rejects_duplicate_document_mapping() -> None:
    payload = _json_object(_SUPERSESSION_PATH)
    assets = payload["assets"]
    assert isinstance(assets, list)
    first = assets[0]
    second = assets[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    second["path"] = first["path"]

    with pytest.raises(ValidationError, match="exact three document mappings"):
        AuraGatewayV2TerminalEvidenceReviewSupersession.model_validate(payload)


def test_supersession_contract_rejects_provider_execution() -> None:
    payload = _json_object(_SUPERSESSION_PATH)
    payload["provider_execution_permitted"] = True

    with pytest.raises(ValidationError):
        AuraGatewayV2TerminalEvidenceReviewSupersession.model_validate(payload)
