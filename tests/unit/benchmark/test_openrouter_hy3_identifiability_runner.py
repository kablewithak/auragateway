from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.openrouter_hy3_identifiability_runner import (
    OpenRouterHy3IdentifiabilityError,
    validate_openrouter_hy3_identifiability,
)

_REVIEW_ROOT = Path("data/evals/benchmark/openrouter-hy3-identifiability-review-v1")
_TERMINAL_ROOT = Path("data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1")
_ADR_PATH = Path("docs/adr/openrouter-hy3-identifiability-review.md")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_OpenRouter_Hy3_Identifiability_Review.md")
_MINI_PRD_PATH = Path("docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md")


def _review_payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((_REVIEW_ROOT / "review.json").read_text(encoding="utf-8")),
    )


def _copy_assets(repo_root: Path) -> None:
    review = _review_payload()
    bindings = review["source_bindings"]
    assert isinstance(bindings, list)

    paths = [
        _REVIEW_ROOT / "review.json",
        _REVIEW_ROOT / "manifest.json",
        _ADR_PATH,
        _REPORT_PATH,
        _MINI_PRD_PATH,
        _TERMINAL_ROOT / "review.json",
    ]
    paths.extend(Path(cast(str, item["path"])) for item in bindings if isinstance(item, dict))

    for relative_path in set(paths):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def test_validator_accepts_non_live_identifiability_review(tmp_path: Path) -> None:
    _copy_assets(tmp_path)

    summary = validate_openrouter_hy3_identifiability(tmp_path)

    assert summary.route_available_as_of_review is True
    assert summary.condition_a_b_design_identifiable is True
    assert summary.condition_b_c_design_identifiable is True
    assert summary.condition_c_effect_claim_permitted is False
    assert summary.adapter_implementation_permitted is True
    assert summary.live_provider_call_authorized is False
    assert summary.pilot_execution_authorized is False
    assert summary.retained_benchmark_authorized is False


def test_validator_does_not_read_openrouter_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-be-read")

    summary = validate_openrouter_hy3_identifiability(tmp_path)

    assert summary.credential_accessed is False
    assert summary.live_provider_call_authorized is False


def test_validator_rejects_source_binding_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    provider_path = tmp_path / "src/auragateway/contracts/provider.py"
    provider_path.write_text(
        provider_path.read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        OpenRouterHy3IdentifiabilityError,
        match="source no longer matches",
    ):
        validate_openrouter_hy3_identifiability(tmp_path)


def test_validator_rejects_review_hash_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    review_path = tmp_path / _REVIEW_ROOT / "review.json"
    review_path.write_text(
        review_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        OpenRouterHy3IdentifiabilityError,
        match="no longer matches",
    ):
        validate_openrouter_hy3_identifiability(tmp_path)


def test_validator_rejects_report_hash_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    report_path = tmp_path / _REPORT_PATH
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        OpenRouterHy3IdentifiabilityError,
        match="no longer matches its manifest",
    ):
        validate_openrouter_hy3_identifiability(tmp_path)


def test_validator_rejects_terminal_core_reopening(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    terminal_path = tmp_path / _TERMINAL_ROOT / "review.json"
    payload = cast(
        dict[str, object],
        json.loads(terminal_path.read_text(encoding="utf-8")),
    )
    payload["additional_provider_execution_permitted"] = True
    terminal_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(OpenRouterHy3IdentifiabilityError):
        validate_openrouter_hy3_identifiability(tmp_path)


def test_validator_rejects_mini_prd_hash_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prd_path = tmp_path / _MINI_PRD_PATH
    prd_path.write_text(
        prd_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        OpenRouterHy3IdentifiabilityError,
        match="no longer matches",
    ):
        validate_openrouter_hy3_identifiability(tmp_path)
