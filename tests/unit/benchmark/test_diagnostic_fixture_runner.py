from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.diagnostic_fixture_runner import (
    DiagnosticFixtureError,
    build_fixture_manifest,
    build_protected_prompt_bundle,
    materialize_diagnostic_fixtures,
    verify_diagnostic_fixtures,
)
from auragateway.contracts.diagnostic_fixtures import (
    DiagnosticFixtureManifest,
    DiagnosticFixtureRecipe,
)

_FIXTURE_ROOT = Path("data/evals/benchmark/diagnostic-fixtures-v1")
_DESIGN_PLAN_PATH = Path("data/evals/benchmark/diagnostic-design-v1/experiment_plan.json")
_DESIGN_MANIFEST_PATH = Path("data/evals/benchmark/diagnostic-design-v1/manifest.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_recipe() -> DiagnosticFixtureRecipe:
    return DiagnosticFixtureRecipe.model_validate_json(
        (_FIXTURE_ROOT / "fixture_recipe.json").read_text(encoding="utf-8")
    )


def _load_manifest() -> DiagnosticFixtureManifest:
    return DiagnosticFixtureManifest.model_validate_json(
        (_FIXTURE_ROOT / "fixture_manifest.json").read_text(encoding="utf-8")
    )


def test_builder_reproduces_exact_byte_targets_and_unique_prefixes() -> None:
    recipe = _load_recipe()
    bundle = build_protected_prompt_bundle(recipe)

    assert len(bundle.cohorts) == 6
    prefix_hashes: set[str] = set()
    for cohort in bundle.cohorts:
        assert len(cohort.system_prompt.encode("ascii")) == 6000
        assert tuple(len(item.encode("ascii")) for item in cohort.user_prompts_by_turn) == (
            1365,
            1737,
            2109,
        )
        prefix_hashes.add(
            __import__("hashlib").sha256(cohort.system_prompt.encode("ascii")).hexdigest()
        )
    assert len(prefix_hashes) == 6


def test_builder_reproduces_committed_content_free_manifest() -> None:
    recipe = _load_recipe()
    bundle = build_protected_prompt_bundle(recipe)
    expected = build_fixture_manifest(
        recipe=recipe,
        bundle=bundle,
        design_plan_sha256=_sha256(_DESIGN_PLAN_PATH),
        design_manifest_sha256=_sha256(_DESIGN_MANIFEST_PATH),
        recipe_sha256=_sha256(_FIXTURE_ROOT / "fixture_recipe.json"),
    )

    assert expected.model_dump(mode="json") == _load_manifest().model_dump(mode="json")


def test_materialize_and_verify_use_local_protected_storage(
    tmp_path: Path,
) -> None:
    protected_path = tmp_path / "prompt_cohorts.json"

    materialized = materialize_diagnostic_fixtures(
        Path("."),
        protected_path_override=protected_path,
    )
    verified = verify_diagnostic_fixtures(
        Path("."),
        protected_path_override=protected_path,
    )

    assert materialized.command == "materialize"
    assert verified.command == "verify"
    assert protected_path.is_file()
    assert materialized.protected_prompt_bundle_sha256 == (verified.protected_prompt_bundle_sha256)
    assert verified.provider_calls_permitted is False
    assert verified.authorization_created is False


def test_verify_rejects_tampered_protected_prompt_bundle(
    tmp_path: Path,
) -> None:
    protected_path = tmp_path / "prompt_cohorts.json"
    materialize_diagnostic_fixtures(
        Path("."),
        protected_path_override=protected_path,
    )
    payload = cast(
        dict[str, object],
        json.loads(protected_path.read_text(encoding="utf-8")),
    )
    cohorts = payload["cohorts"]
    assert isinstance(cohorts, list)
    assert isinstance(cohorts[0], dict)
    cohorts[0]["system_prompt"] = "tampered"
    protected_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    with pytest.raises(
        DiagnosticFixtureError,
        match="does not reproduce from the frozen recipe",
    ):
        verify_diagnostic_fixtures(
            Path("."),
            protected_path_override=protected_path,
        )


def test_public_fixture_assets_do_not_contain_raw_prompt_fields() -> None:
    recipe_text = (_FIXTURE_ROOT / "fixture_recipe.json").read_text(encoding="utf-8")
    manifest_text = (_FIXTURE_ROOT / "fixture_manifest.json").read_text(encoding="utf-8")

    for forbidden in (
        '"system_prompt":',
        '"user_prompts_by_turn":',
        '"messages":',
        '"raw_request":',
        '"provider_output":',
    ):
        assert forbidden not in recipe_text
        assert forbidden not in manifest_text


def test_every_committed_b_c_request_hash_pair_is_equal() -> None:
    manifest = _load_manifest()

    for cohort in manifest.cohorts:
        assert (
            cohort.condition_b_request_sha256_by_turn == cohort.condition_c_request_sha256_by_turn
        )
