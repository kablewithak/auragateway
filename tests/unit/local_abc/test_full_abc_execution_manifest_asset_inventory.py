from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_execution_manifest_asset_inventory import (
    ExecutionManifestAssetRecord,
    ExecutionManifestAssetState,
    ExecutionManifestInventoryReadiness,
    FullABCExecutionManifestAssetInventory,
    load_full_abc_execution_manifest_asset_inventory,
)

ROOT = Path(__file__).resolve().parents[3]
INVENTORY_PATH = (
    ROOT / "benchmarks/local_abc/auragateway_full_abc_execution_manifest_asset_inventory_v1.json"
)
EXPECTED_INVENTORY_SHA256 = "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"


def load_inventory() -> FullABCExecutionManifestAssetInventory:
    return load_full_abc_execution_manifest_asset_inventory(INVENTORY_PATH)


def asset_map() -> dict[str, ExecutionManifestAssetRecord]:
    inventory = load_inventory()
    return {asset.asset_id: asset for asset in inventory.assets}


def test_inventory_has_expected_identity() -> None:
    inventory = load_inventory()

    assert inventory.fingerprint() == EXPECTED_INVENTORY_SHA256
    assert inventory.source_merge_commit == "14cc94c74d6a093492732b8123977bd69e1e8ac7"
    assert inventory.integration_source_blob_sha == "269cfd38cbe789d35ca44a8006d9c29f9558a6a0"
    assert inventory.implementation_plan_blob_sha == "4a6dfea4b90cebad4052ca5eadf09a4bdc2520f7"


def test_inventory_is_complete_but_not_ready() -> None:
    inventory = load_inventory()

    assert inventory.inventory_complete is True
    assert inventory.readiness is ExecutionManifestInventoryReadiness.INVENTORIED_NOT_READY
    assert inventory.execution_manifest_frozen is False
    assert inventory.next_gate == "full_abc_execution_manifest_draft_reconciliation"


def test_inventory_summary_matches_expected_counts() -> None:
    summary = load_inventory().summary

    assert summary.total_asset_count == 44
    assert summary.frozen_bound_count == 28
    assert summary.present_unbound_count == 5
    assert summary.present_stale_count == 4
    assert summary.generated_at_freeze_count == 4
    assert summary.external_blocked_count == 2
    assert summary.missing_required_count == 1
    assert summary.unresolved_required_count == 16
    assert summary.local_gap_count == 14
    assert summary.external_gap_count == 2


def test_asset_ids_are_unique_and_sorted() -> None:
    inventory = load_inventory()
    asset_ids = tuple(asset.asset_id for asset in inventory.assets)

    assert len(asset_ids) == len(set(asset_ids))
    assert asset_ids == tuple(sorted(asset_ids))


@pytest.mark.parametrize(
    ("asset_id", "expected_sha256"),
    (
        (
            "benchmark_constitution",
            "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1",
        ),
        (
            "corpus_manifest",
            "c68212afd5381dec8bce49d0d5fee231a3b5589bf5460c0f72297e0c84422f55",
        ),
        (
            "retrieval_freeze_manifest",
            "dc74b69b72cb5a392ce86f46d7b4709a5106746d84053ebff09b573b57271492",
        ),
        (
            "diagnostic_episode_manifest",
            "3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b",
        ),
        (
            "integration_implementation",
            "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662",
        ),
    ),
)
def test_frozen_assets_preserve_exact_hashes(asset_id: str, expected_sha256: str) -> None:
    asset = asset_map()[asset_id]

    assert asset.state is ExecutionManifestAssetState.FROZEN_BOUND
    assert asset.sha256 == expected_sha256


def test_core_research_assets_are_not_missing() -> None:
    assets = asset_map()
    required = (
        "corpus_manifest",
        "chunking_manifest",
        "retrieval_freeze_manifest",
        "functional_episode_set",
        "runtime_episode_selection",
        "quality_rubric",
        "telemetry_fixture_manifest",
    )

    assert all(
        assets[asset_id].state is ExecutionManifestAssetState.FROZEN_BOUND for asset_id in required
    )


def test_static_freeze_assets_are_present_but_unbound() -> None:
    assets = asset_map()
    expected = (
        "fault_injection_fixture_set",
        "negative_control_manifest",
        "pricing_schedule",
        "privacy_verification_report",
    )

    assert all(
        assets[asset_id].state is ExecutionManifestAssetState.PRESENT_UNBOUND
        for asset_id in expected
    )


def test_gate9_lineage_is_explicitly_stale() -> None:
    assets = asset_map()

    assert assets["execution_manifest_draft"].state is ExecutionManifestAssetState.PRESENT_STALE
    assert assets["gate9_preflight_manifest"].state is ExecutionManifestAssetState.PRESENT_STALE
    assert assets["planned_run_ledger"].state is ExecutionManifestAssetState.PRESENT_STALE
    assert assets["dependency_lock_identity"].state is ExecutionManifestAssetState.PRESENT_STALE


def test_condition_fingerprints_are_the_only_missing_required_asset() -> None:
    inventory = load_inventory()
    missing = tuple(
        asset.asset_id
        for asset in inventory.assets
        if asset.state is ExecutionManifestAssetState.MISSING_REQUIRED
    )

    assert missing == ("condition_configuration_fingerprints",)


def test_provider_readiness_requires_a_separate_provider_call() -> None:
    asset = asset_map()["provider_readiness_record"]

    assert asset.state is ExecutionManifestAssetState.EXTERNAL_BLOCKED
    assert asset.provider_call_required_to_resolve is True
    assert asset.bindable_without_external_call is False


def test_cost_budget_requires_operator_approval_not_model_execution() -> None:
    asset = asset_map()["cost_budget_approval"]

    assert asset.state is ExecutionManifestAssetState.EXTERNAL_BLOCKED
    assert asset.operator_approval_required is True
    assert asset.provider_call_required_to_resolve is False


def test_freeze_outputs_are_not_claimed_as_existing() -> None:
    assets = asset_map()
    generated = (
        "cross_condition_isolation_report",
        "final_execution_manifest",
        "freeze_report",
        "gate10_manifest",
    )

    for asset_id in generated:
        asset = assets[asset_id]
        assert asset.state is ExecutionManifestAssetState.GENERATED_AT_FREEZE
        assert asset.sha256 is None
        assert asset.git_object_sha is None


def test_inventory_grants_no_execution_authority() -> None:
    inventory = load_inventory()

    assert inventory.measured_execution_authorized is False
    assert inventory.provider_execution_authorized is False
    assert inventory.gpu_execution_authorized is False
    assert inventory.new_authorization_issued is False
    assert inventory.consumed_authorization_reused is False


def test_inventory_performed_no_external_work() -> None:
    inventory = load_inventory()

    assert inventory.provider_call_performed is False
    assert inventory.model_request_performed is False
    assert inventory.gpu_execution_performed is False
    assert inventory.customer_data_used is False
    assert inventory.external_spend == 0


def test_inventory_json_is_canonical_single_line() -> None:
    inventory = load_inventory()
    text = INVENTORY_PATH.read_text(encoding="utf-8")

    assert text == inventory.canonical_json()
    assert "\n" not in text
    assert json.loads(text) == inventory.model_dump(mode="json")


def test_summary_mutation_fails_closed() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    payload["summary"]["frozen_bound_count"] += 1

    with pytest.raises(ValidationError, match="inventory state counts"):
        FullABCExecutionManifestAssetInventory.model_validate(payload)


def test_asset_order_mutation_fails_closed() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    payload["assets"][0], payload["assets"][1] = (
        payload["assets"][1],
        payload["assets"][0],
    )

    with pytest.raises(ValidationError, match="canonically ordered"):
        FullABCExecutionManifestAssetInventory.model_validate(payload)


def test_frozen_asset_without_identity_fails_closed() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    asset = next(item for item in payload["assets"] if item["asset_id"] == "corpus_manifest")
    asset["sha256"] = None

    with pytest.raises(ValidationError, match="frozen assets require"):
        FullABCExecutionManifestAssetInventory.model_validate(payload)


def test_provider_blocked_asset_cannot_be_locally_bindable() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    asset = next(
        item for item in payload["assets"] if item["asset_id"] == "provider_readiness_record"
    )
    asset["bindable_without_external_call"] = True

    with pytest.raises(ValidationError, match="cannot be locally bindable"):
        FullABCExecutionManifestAssetInventory.model_validate(payload)


def test_inventory_docs_preserve_blockers_and_next_gate() -> None:
    adr = (
        ROOT / "docs/adr/2026-07-18-local-abc-full-abc-execution-manifest-asset-inventory.md"
    ).read_text(encoding="utf-8")
    benchmark = (
        ROOT
        / "docs/benchmarks/local_abc_auragateway_full_abc_execution_manifest_asset_inventory_v1.md"
    ).read_text(encoding="utf-8")

    for text in (adr, benchmark):
        assert "full_abc_execution_manifest_draft_reconciliation" in text
        assert "provider_readiness_record" in text
        assert "condition_configuration_fingerprints" in text
        assert "measured_execution_authorized=false" in text
