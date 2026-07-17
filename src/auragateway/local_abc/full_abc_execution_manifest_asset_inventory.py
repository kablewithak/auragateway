"""Typed inventory of assets required to freeze the full A/B/C execution manifest."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{3,240}$")

_SOURCE_MERGE_COMMIT: Final = "14cc94c74d6a093492732b8123977bd69e1e8ac7"
_INTEGRATION_SOURCE_BLOB_SHA: Final = "269cfd38cbe789d35ca44a8006d9c29f9558a6a0"
_IMPLEMENTATION_PLAN_BLOB_SHA: Final = "4a6dfea4b90cebad4052ca5eadf09a4bdc2520f7"
_IMPLEMENTATION_PLAN_SHA256: Final = (
    "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
)
_INTEGRATION_DESIGN_SHA256: Final = (
    "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
)
_BENCHMARK_CONSTITUTION_SHA256: Final = (
    "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
)


class ExecutionManifestAssetCategory(StrEnum):
    """Stable groups used to query execution-manifest readiness."""

    GOVERNANCE = "governance"
    CORPUS_RETRIEVAL = "corpus_retrieval"
    CONTEXT_SCHEMA = "context_schema"
    EVALUATION = "evaluation"
    TELEMETRY_PROVIDER = "telemetry_provider"
    FREEZE_CONTROL = "freeze_control"
    EXECUTION_LINEAGE = "execution_lineage"


class ExecutionManifestAssetState(StrEnum):
    """Lifecycle state for one asset required by the future frozen manifest."""

    FROZEN_BOUND = "frozen_bound"
    PRESENT_UNBOUND = "present_unbound"
    PRESENT_STALE = "present_stale"
    GENERATED_AT_FREEZE = "generated_at_freeze"
    EXTERNAL_BLOCKED = "external_blocked"
    MISSING_REQUIRED = "missing_required"


class ExecutionManifestInventoryReadiness(StrEnum):
    """Overall decision after the asset inventory is validated."""

    INVENTORIED_NOT_READY = "inventoried_not_ready"
    READY_FOR_FREEZE = "ready_for_freeze"


class ExecutionManifestAssetRecord(LocalABCContract):
    """One hash-addressable or explicitly blocked execution-manifest asset."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    asset_id: str
    category: ExecutionManifestAssetCategory
    state: ExecutionManifestAssetState
    required_for_freeze: Literal[True] = True
    repository_path: str | None = None
    sha256: str | None = None
    git_object_sha: str | None = None
    manifest_field: str | None = None
    blocking_dependencies: tuple[str, ...] = ()
    bindable_without_external_call: bool
    provider_call_required_to_resolve: bool = False
    operator_approval_required: bool = False
    next_action: str = Field(min_length=12, max_length=320)
    evidence_note: str = Field(min_length=12, max_length=520)

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("asset_id must use stable lowercase characters")
        return value

    @field_validator("repository_path")
    @classmethod
    def validate_repository_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if (
            _PATH_PATTERN.fullmatch(value) is None
            or value.startswith("/")
            or ".." in Path(value).parts
        ):
            raise ValueError("repository_path must be a bounded repository-relative path")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is not None and _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("asset SHA-256 must be lowercase hexadecimal")
        return value

    @field_validator("git_object_sha")
    @classmethod
    def validate_git_object_sha(cls, value: str | None) -> str | None:
        if value is not None and _GIT_OBJECT_PATTERN.fullmatch(value) is None:
            raise ValueError("Git object identity must be lowercase hexadecimal")
        return value

    @field_validator("blocking_dependencies")
    @classmethod
    def validate_dependencies(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("blocking dependencies must be unique")
        if value != tuple(sorted(value)):
            raise ValueError("blocking dependencies must be canonically sorted")
        for dependency in value:
            if _ID_PATTERN.fullmatch(dependency) is None:
                raise ValueError("blocking dependency IDs must be stable")
        return value

    @model_validator(mode="after")
    def validate_state_contract(self) -> Self:
        identified = self.sha256 is not None or self.git_object_sha is not None
        if self.state is ExecutionManifestAssetState.FROZEN_BOUND and not identified:
            raise ValueError("frozen assets require a content or Git identity")
        if self.state in {
            ExecutionManifestAssetState.PRESENT_UNBOUND,
            ExecutionManifestAssetState.PRESENT_STALE,
        } and (self.repository_path is None or not identified):
            raise ValueError("present assets require a path and identity")
        if (
            self.state
            in {
                ExecutionManifestAssetState.GENERATED_AT_FREEZE,
                ExecutionManifestAssetState.EXTERNAL_BLOCKED,
                ExecutionManifestAssetState.MISSING_REQUIRED,
            }
            and identified
        ):
            raise ValueError("unresolved assets cannot claim a frozen identity")
        if self.provider_call_required_to_resolve and self.bindable_without_external_call:
            raise ValueError("provider-blocked assets cannot be locally bindable")
        if self.state is ExecutionManifestAssetState.EXTERNAL_BLOCKED and not (
            self.provider_call_required_to_resolve or self.operator_approval_required
        ):
            raise ValueError(
                "externally blocked assets require a provider call or operator approval"
            )
        if self.state is ExecutionManifestAssetState.FROZEN_BOUND and not (
            self.bindable_without_external_call
        ):
            raise ValueError("frozen assets must be locally bindable")
        return self


class ExecutionManifestAssetInventorySummary(LocalABCContract):
    """Counts and blockers derived from the exact ordered inventory."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    total_asset_count: int = Field(gt=0)
    frozen_bound_count: int = Field(ge=0)
    present_unbound_count: int = Field(ge=0)
    present_stale_count: int = Field(ge=0)
    generated_at_freeze_count: int = Field(ge=0)
    external_blocked_count: int = Field(ge=0)
    missing_required_count: int = Field(ge=0)
    unresolved_required_count: int = Field(ge=0)
    local_gap_count: int = Field(ge=0)
    external_gap_count: int = Field(ge=0)
    blocker_asset_ids: tuple[str, ...]

    @field_validator("blocker_asset_ids")
    @classmethod
    def validate_blocker_order(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("blocker asset IDs must be unique")
        if value != tuple(sorted(value)):
            raise ValueError("blocker asset IDs must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_count_arithmetic(self) -> Self:
        state_total = sum(
            (
                self.frozen_bound_count,
                self.present_unbound_count,
                self.present_stale_count,
                self.generated_at_freeze_count,
                self.external_blocked_count,
                self.missing_required_count,
            )
        )
        if state_total != self.total_asset_count:
            raise ValueError("inventory state counts must reconcile to total assets")
        if self.local_gap_count + self.external_gap_count != self.unresolved_required_count:
            raise ValueError("local and external gaps must reconcile")
        if len(self.blocker_asset_ids) != self.unresolved_required_count:
            raise ValueError("blocker count must match unresolved required assets")
        return self


class FullABCExecutionManifestAssetInventory(LocalABCContract):
    """Immutable inventory; it does not freeze or authorize the execution manifest."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    inventory_id: Literal["auragateway-full-abc-execution-manifest-asset-inventory-v1"] = (
        "auragateway-full-abc-execution-manifest-asset-inventory-v1"
    )
    source_merge_commit: Literal["14cc94c74d6a093492732b8123977bd69e1e8ac7"] = _SOURCE_MERGE_COMMIT
    integration_source_blob_sha: Literal["269cfd38cbe789d35ca44a8006d9c29f9558a6a0"] = (
        _INTEGRATION_SOURCE_BLOB_SHA
    )
    implementation_plan_blob_sha: Literal["4a6dfea4b90cebad4052ca5eadf09a4bdc2520f7"] = (
        _IMPLEMENTATION_PLAN_BLOB_SHA
    )
    implementation_plan_sha256: Literal[
        "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
    ] = _IMPLEMENTATION_PLAN_SHA256
    integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ] = _INTEGRATION_DESIGN_SHA256
    benchmark_constitution_sha256: Literal[
        "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
    ] = _BENCHMARK_CONSTITUTION_SHA256
    assets: tuple[ExecutionManifestAssetRecord, ...]
    summary: ExecutionManifestAssetInventorySummary
    readiness: Literal[ExecutionManifestInventoryReadiness.INVENTORIED_NOT_READY] = (
        ExecutionManifestInventoryReadiness.INVENTORIED_NOT_READY
    )
    inventory_complete: Literal[True] = True
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    provider_call_performed: Literal[False] = False
    model_request_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    new_authorization_issued: Literal[False] = False
    consumed_authorization_reused: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0
    next_gate: Literal["full_abc_execution_manifest_draft_reconciliation"] = (
        "full_abc_execution_manifest_draft_reconciliation"
    )

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        asset_ids = tuple(asset.asset_id for asset in self.assets)
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("inventory asset IDs must be unique")
        if asset_ids != tuple(sorted(asset_ids)):
            raise ValueError("inventory assets must be canonically ordered by asset_id")

        state_counts = {
            state: sum(asset.state is state for asset in self.assets)
            for state in ExecutionManifestAssetState
        }
        unresolved = tuple(
            sorted(
                asset.asset_id
                for asset in self.assets
                if asset.state is not ExecutionManifestAssetState.FROZEN_BOUND
            )
        )
        external = sum(
            asset.state is ExecutionManifestAssetState.EXTERNAL_BLOCKED for asset in self.assets
        )
        local = len(unresolved) - external
        expected_summary = ExecutionManifestAssetInventorySummary(
            total_asset_count=len(self.assets),
            frozen_bound_count=state_counts[ExecutionManifestAssetState.FROZEN_BOUND],
            present_unbound_count=state_counts[ExecutionManifestAssetState.PRESENT_UNBOUND],
            present_stale_count=state_counts[ExecutionManifestAssetState.PRESENT_STALE],
            generated_at_freeze_count=(
                state_counts[ExecutionManifestAssetState.GENERATED_AT_FREEZE]
            ),
            external_blocked_count=state_counts[ExecutionManifestAssetState.EXTERNAL_BLOCKED],
            missing_required_count=state_counts[ExecutionManifestAssetState.MISSING_REQUIRED],
            unresolved_required_count=len(unresolved),
            local_gap_count=local,
            external_gap_count=external,
            blocker_asset_ids=unresolved,
        )
        if self.summary != expected_summary:
            raise ValueError("inventory summary must be derived from the exact asset records")
        if self.summary.unresolved_required_count == 0:
            raise ValueError("this inventory cannot claim readiness before gap closure")
        return self


def load_full_abc_execution_manifest_asset_inventory(
    path: Path,
) -> FullABCExecutionManifestAssetInventory:
    """Load and validate the immutable asset inventory without freezing execution."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("execution-manifest asset inventory must contain one JSON object")
    return FullABCExecutionManifestAssetInventory.model_validate(cast(dict[str, object], payload))
