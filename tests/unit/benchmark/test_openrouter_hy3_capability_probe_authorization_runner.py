from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.benchmark.openrouter_hy3_capability_probe_authorization_runner import (
    OpenRouterProbeAuthorizationError,
    validate_openrouter_probe_authorization,
)

_ROOT = Path(
    "data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1"
)
_REVIEW = _ROOT / "review.json"
_PROMPT = _ROOT / "prompt_recipe.json"
_STATE = _ROOT / "state_model_report.json"
_TRANSPORT = _ROOT / "transport_report.json"
_MANIFEST = _ROOT / "manifest.json"
_SUPERSESSION = Path(
    "data/evals/benchmark/openrouter-hy3-historical-review-supersession-v1/supersession.json"
)
_SUPERSEDING_MANIFEST = Path(
    "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/manifest.json"
)


def _copy_assets(repo_root: Path) -> None:
    review = json.loads(_REVIEW.read_text(encoding="utf-8"))
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    paths = {
        _REVIEW,
        _PROMPT,
        _STATE,
        _TRANSPORT,
        _MANIFEST,
        _SUPERSESSION,
        _SUPERSEDING_MANIFEST,
    }
    paths.update(Path(item["path"]) for item in review["source_bindings"])
    paths.update(Path(item["path"]) for item in manifest["bindings"])
    for path in paths:
        destination = repo_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def test_validator_accepts_inactive_authorization_review() -> None:
    summary = validate_openrouter_probe_authorization(Path("."))
    assert summary.state_model_reachable_states == 88
    assert summary.state_model_terminal_states == 57
    assert summary.state_model_invariant_violations == 0
    assert summary.live_provider_call_authorized is False
    assert summary.activation_review_permitted is True
    assert summary.tla_plus_required is False


def test_validator_reads_no_openrouter_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-be-read")
    summary = validate_openrouter_probe_authorization(tmp_path)
    assert summary.credential_accessed is False
    assert summary.network_request_performed is False


def test_validator_rejects_bound_source_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / "src/auragateway/providers/openrouter.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(OpenRouterProbeAuthorizationError, match="source input"):
        validate_openrouter_probe_authorization(tmp_path)


def test_validator_rejects_prompt_recipe_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / _PROMPT
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["generated_prefix_bytes"] += 1
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises((OpenRouterProbeAuthorizationError, ValueError)):
        validate_openrouter_probe_authorization(tmp_path)


def test_validator_rejects_state_model_report_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / _STATE
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reachable_state_count"] += 1
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(OpenRouterProbeAuthorizationError, match="state model"):
        validate_openrouter_probe_authorization(tmp_path)


def test_validator_rejects_manifest_bound_output_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = (
        tmp_path
        / "docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Authorization_Review.md"
    )
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(OpenRouterProbeAuthorizationError, match="manifest"):
        validate_openrouter_probe_authorization(tmp_path)


def test_validator_rejects_superseding_manifest_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / _SUPERSEDING_MANIFEST
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(OpenRouterProbeAuthorizationError, match="supersession"):
        validate_openrouter_probe_authorization(tmp_path)


def test_validator_rejects_superseded_runner_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = (
        tmp_path / "src/auragateway/benchmark/"
        "openrouter_hy3_capability_probe_authorization_runner.py"
    )
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(OpenRouterProbeAuthorizationError, match="manifest"):
        validate_openrouter_probe_authorization(tmp_path)
