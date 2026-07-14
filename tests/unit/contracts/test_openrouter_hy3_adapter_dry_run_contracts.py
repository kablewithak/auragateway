from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter_hy3_adapter_dry_run import (
    OpenRouterDryRunFixtureSet,
    OpenRouterDryRunManifest,
    OpenRouterDryRunReport,
)

_ROOT = Path("data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1")
_FIXTURE = Path("data/provider_fixtures/openrouter-hy3-adapter-v1/fixtures.json")


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_fixtures_cover_seven_unique_cases() -> None:
    fixtures = OpenRouterDryRunFixtureSet.model_validate(_json(_FIXTURE))
    assert len(fixtures.cases) == 7
    assert len({item.case_id for item in fixtures.cases}) == 7


def test_report_keeps_live_execution_inactive() -> None:
    report = OpenRouterDryRunReport.model_validate(_json(_ROOT / "report.json"))
    assert report.live_provider_call_performed is False
    assert report.live_provider_call_authorized is False
    assert report.hy3_free_numeric_telemetry_observed_live is False
    assert report.adapter_ready_for_authorization_review is True


def test_report_rejects_live_authorization_promotion() -> None:
    payload = _json(_ROOT / "report.json")
    payload["live_provider_call_authorized"] = True
    with pytest.raises(ValidationError):
        OpenRouterDryRunReport.model_validate(payload)


def test_manifest_rejects_missing_binding() -> None:
    payload = _json(_ROOT / "manifest.json")
    bindings = deepcopy(payload["bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["bindings"] = bindings
    with pytest.raises(ValidationError, match="at least 7 items"):
        OpenRouterDryRunManifest.model_validate(payload)
