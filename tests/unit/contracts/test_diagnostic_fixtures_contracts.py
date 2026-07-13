from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.diagnostic_fixtures import (
    DiagnosticFixtureManifest,
    DiagnosticFixtureRecipe,
)

_FIXTURE_ROOT = Path("data/evals/benchmark/diagnostic-fixtures-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_fixture_recipe_validates_exact_prompt_arithmetic() -> None:
    recipe = DiagnosticFixtureRecipe.model_validate(
        _json_object(_FIXTURE_ROOT / "fixture_recipe.json")
    )

    assert recipe.system_prompt_byte_count == 6000
    assert recipe.user_prompt_byte_counts_by_turn == (1365, 1737, 2109)
    assert recipe.total_prompt_byte_counts_by_turn == (7365, 7737, 8109)
    assert recipe.input_token_estimates_by_turn == (1732, 1809, 1884)
    assert recipe.raw_prompt_commit_permitted is False


def test_fixture_manifest_validates_materialized_public_evidence() -> None:
    manifest = DiagnosticFixtureManifest.model_validate(
        _json_object(_FIXTURE_ROOT / "fixture_manifest.json")
    )

    assert manifest.status == "fixture_ready"
    assert len(manifest.cohorts) == 6
    assert len({item.system_prompt_sha256 for item in manifest.cohorts}) == 6
    assert manifest.provider_visible_b_c_equivalence_verified is True
    assert manifest.provider_calls_permitted is False
    assert manifest.execution_authorization_created is False


def test_fixture_manifest_rejects_duplicate_stable_prefix() -> None:
    payload = _json_object(_FIXTURE_ROOT / "fixture_manifest.json")
    cohorts = deepcopy(payload["cohorts"])
    assert isinstance(cohorts, list)
    assert isinstance(cohorts[0], dict)
    assert isinstance(cohorts[1], dict)
    cohorts[1]["system_prompt_sha256"] = cohorts[0]["system_prompt_sha256"]
    payload["cohorts"] = cohorts

    with pytest.raises(ValidationError, match="stable-prefix hashes must be unique"):
        DiagnosticFixtureManifest.model_validate(payload)


def test_fixture_manifest_rejects_b_c_request_drift() -> None:
    payload = _json_object(_FIXTURE_ROOT / "fixture_manifest.json")
    cohorts = deepcopy(payload["cohorts"])
    assert isinstance(cohorts, list)
    assert isinstance(cohorts[0], dict)
    condition_c_hashes = cohorts[0]["condition_c_request_sha256_by_turn"]
    assert isinstance(condition_c_hashes, list)
    condition_c_hashes[2] = "0" * 64
    payload["cohorts"] = cohorts

    with pytest.raises(
        ValidationError,
        match="condition B and condition C provider request hashes must match",
    ):
        DiagnosticFixtureManifest.model_validate(payload)


def test_fixture_manifest_rejects_raw_prompt_fields() -> None:
    payload = _json_object(_FIXTURE_ROOT / "fixture_manifest.json")
    cohorts = deepcopy(payload["cohorts"])
    assert isinstance(cohorts, list)
    assert isinstance(cohorts[0], dict)
    cohorts[0]["system_prompt"] = "raw prompt must not be public"
    payload["cohorts"] = cohorts

    with pytest.raises(ValidationError):
        DiagnosticFixtureManifest.model_validate(payload)


def test_fixture_recipe_rejects_total_byte_mismatch() -> None:
    payload = _json_object(_FIXTURE_ROOT / "fixture_recipe.json")
    payload["total_prompt_byte_counts_by_turn"] = [7365, 7737, 8110]

    with pytest.raises(ValidationError):
        DiagnosticFixtureRecipe.model_validate(payload)
