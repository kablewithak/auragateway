"""Review the clean local-only full A/B/C preflight-v3 rebuild boundary."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/+-]{3,240}$")
_FIELD_PATTERN = re.compile(r"^[A-Za-z0-9_.*\[\]-]{2,200}$")

SOURCE_MAIN_MERGE_COMMIT: Final = "f3e625518fb61af7c1a8197ef51ba5b38bcae510"
REVIEW_ID: Final = "auragateway-full-abc-local-preflight-v3-rebuild-review-v1"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_preflight_v3_rebuild_review_v1.json"
)
NEXT_GATE: Final = "full_abc_local_preflight_v3_rebuild_implementation"

_CORRECTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_runtime_lineage_correction_v1.json"
)
_SUPERSESSION_PATH: Final = Path(
    "data/evals/benchmark/preflight-v2/hosted_provider_lineage_supersession_v1.json"
)
_INVENTORY_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_execution_manifest_asset_inventory_v1.json"
)

_EXPECTED_CORRECTION_SHA256: Final = (
    "1927239e919741f96b6c8017b241413b42d9528de109db1cd7df7a0dfd9b0fe7"
)
_EXPECTED_SUPERSESSION_SHA256: Final = (
    "df39761f7f6c73787bffacb5e933b4ea4d35f4079e86ff94ec846f63e2ae1cd6"
)
_EXPECTED_INVENTORY_SHA256: Final = (
    "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"
)
_EXPECTED_INTEGRATION_BLOB_SHA: Final = "269cfd38cbe789d35ca44a8006d9c29f9558a6a0"
_EXPECTED_INVENTORY_SOURCE_BLOB_SHA: Final = "0dae0b26b218ac0c657c9b0effddc6d6424b0410"
_EXPECTED_CORRECTION_SOURCE_BLOB_SHA: Final = "0dc03fe3aac172293ad427da1c5dba0966ccac5e"
_EXPECTED_BENCHMARK_CONSTITUTION_SHA256: Final = (
    "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
)
_EXPECTED_EXECUTION_REQUIREMENTS_SHA256: Final = (
    "30799246e6fa8d91246a5277e613ed97f840a164331f1f04a3f17fd84aad20cf"
)
_EXPECTED_LOCAL_EXTENSION_PRD_SHA256: Final = (
    "c7e9a3cde75a0acf06903ed1a3947a757b9c5ec04f2be6374af393a570dac76e"
)

_PROHIBITED_PREFLIGHT_V3_FIELDS: Final = (
    "condition_fingerprints.records[*].payload.pricing_schedule_id",
    "condition_fingerprints.records[*].payload.provider_adapter_version",
    "condition_fingerprints.records[*].payload.provider_model_alias",
    "dependency_lock.packages.groq.active_full_abc_runtime_dependency",
    "execution_manifest.assets.currency",
    "execution_manifest.assets.pricing_schedule_id",
    "execution_manifest.assets.pricing_schedule_sha256",
    "execution_manifest.assets.pricing_source_date",
    "execution_manifest.assets.provider_adapter_version",
    "execution_manifest.assets.provider_model_alias",
    "execution_manifest.unresolved_freeze_assets.cost_budget_approval",
    "execution_manifest.unresolved_freeze_assets.provider_readiness_record",
    "preflight_report.checks.cost_approval_pending",
    "preflight_report.checks.provider_readiness_pending",
)

_SHARED_FINGERPRINT_FIELDS: Final = (
    "action_schema_sha256",
    "benchmark_constitution_sha256",
    "decoding_configuration_sha256",
    "environment",
    "execution_backend",
    "execution_manifest_requirements_sha256",
    "metric_mapping_sha256",
    "model_alias",
    "model_repository",
    "model_revision",
    "prompt_policy_sha256",
    "quality_rubric_sha256",
    "response_schema_sha256",
    "retrieval_configuration_sha256",
    "runtime_configuration_sha256",
    "tokenizer_revision",
    "torch_cuda_version",
    "torch_version",
    "transport_endpoint",
    "vllm_distribution_version",
    "worker_client_contract",
    "worker_registry_contract",
)

_CONDITION_SPECIFIC_FINGERPRINT_FIELDS: Final = (
    "cache_namespace_id",
    "condition_id",
    "prefix_policy",
    "prefix_token_hash",
    "route_schedule",
)

_LEDGER_REQUIRED_FIELDS: Final = (
    "attempt_number",
    "benchmark_manifest_sha256",
    "comparison_pair_id",
    "condition_configuration_fingerprint",
    "condition_id",
    "episode_id",
    "execution_manifest_sha256",
    "planned_order_index",
    "replication_id",
    "route_schedule_id",
    "run_id",
    "terminal_classification",
    "trace_id",
)


class FullABCLocalPreflightV3ReviewError(RuntimeError):
    """Expected metadata-safe validation failure for the review package."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class PreflightV3AuthorityKind(StrEnum):
    """Identity mechanism used by one review authority."""

    CANONICAL_SHA256 = "canonical_sha256"
    CONTENT_SHA256 = "content_sha256"
    GIT_BLOB_SHA = "git_blob_sha"
    LOCAL_DOCUMENT_SHA256 = "local_document_sha256"


class PreflightV3ResolutionStage(StrEnum):
    """Earliest stage allowed to resolve one currently unfrozen asset."""

    PREFLIGHT_V3_REBUILD = "preflight_v3_rebuild"
    ENVIRONMENT_QUALIFICATION = "environment_qualification"
    DIAGNOSTIC_QUALIFICATION = "diagnostic_qualification"
    VARIANCE_PILOT = "variance_pilot"
    EXECUTION_FREEZE = "execution_freeze"


class PreflightV3AuthorityBinding(LocalABCContract):
    """One exact source authority permitted to influence the v3 rebuild."""

    binding_id: str
    role: str = Field(min_length=8, max_length=160)
    source_locator: str
    authority_kind: PreflightV3AuthorityKind
    identity: str
    carry_forward_permitted: bool
    notes: str = Field(min_length=12, max_length=420)

    @field_validator("binding_id")
    @classmethod
    def validate_binding_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authority binding IDs must use stable lowercase characters")
        return value

    @field_validator("source_locator")
    @classmethod
    def validate_source_locator(cls, value: str) -> str:
        if _PATH_PATTERN.fullmatch(value) is None or ".." in Path(value).parts:
            raise ValueError("authority source locators must remain bounded")
        return value

    @field_validator("identity")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        if (
            _SHA256_PATTERN.fullmatch(value) is None
            and _GIT_OBJECT_PATTERN.fullmatch(value) is None
        ):
            raise ValueError("authority identities must be lowercase Git or SHA-256 digests")
        return value


class PreflightV3DependencyLockDecision(LocalABCContract):
    """Separate developer validation dependencies from Kaggle execution dependencies."""

    developer_lock_path: Literal["data/evals/benchmark/preflight-v3/developer_dependency_lock.json"]
    kaggle_runtime_lock_path: Literal[
        "data/evals/benchmark/preflight-v3/kaggle_runtime_dependency_lock.json"
    ]
    developer_lock_source_inputs: tuple[str, ...]
    kaggle_lock_required_fields: tuple[str, ...]
    hosted_provider_packages_may_be_recorded_as_historical: Literal[True] = True
    hosted_provider_packages_active_for_full_abc: Literal[False] = False
    current_kaggle_values_status: Literal["UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION"]

    @field_validator("developer_lock_source_inputs", "kaggle_lock_required_fields")
    @classmethod
    def validate_ordered_unique_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)) or value != tuple(sorted(value)):
            raise ValueError("dependency fields must be unique and canonically sorted")
        return value


class PreflightV3ConditionFingerprintDecision(LocalABCContract):
    """Define the clean local-only A/B/C condition fingerprint contract."""

    artifact_path: Literal["data/evals/benchmark/preflight-v3/condition_fingerprints.json"]
    shared_fields: tuple[str, ...]
    condition_specific_fields: tuple[str, ...]
    prohibited_fields: tuple[str, ...]
    b_c_prefix_token_hash_equal: Literal[True] = True
    a_b_route_schedule_equal: Literal[True] = True
    all_shared_fields_equal_across_conditions: Literal[True] = True
    trace_field_provider_model_alias_retained_for_compatibility: Literal[True] = True
    trace_field_provider_model_alias_semantics: Literal[
        "legacy_name_bound_to_local_runtime_model_alias_without_provider_authority"
    ]
    trace_field_provider_model_alias_value: Literal["local-qwen2.5-0.5b-instruct"]
    trace_field_rename_requires_separate_contract_migration: Literal[True] = True

    @field_validator("shared_fields", "condition_specific_fields", "prohibited_fields")
    @classmethod
    def validate_field_sets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)) or value != tuple(sorted(value)):
            raise ValueError("fingerprint field sets must be unique and sorted")
        if any(_FIELD_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("fingerprint fields contain unsupported characters")
        return value

    @model_validator(mode="after")
    def validate_no_provider_contamination(self) -> Self:
        forbidden_tokens = (
            "pricing",
            "currency",
            "provider_adapter",
            "provider_readiness",
        )
        for field_name in self.shared_fields + self.condition_specific_fields:
            if any(token in field_name for token in forbidden_tokens):
                raise ValueError(
                    "active local fingerprints cannot contain provider or pricing fields"
                )
        if self.prohibited_fields != _PROHIBITED_PREFLIGHT_V3_FIELDS:
            raise ValueError("prohibited preflight-v3 field set drifted")
        return self


class PreflightV3LedgerRegenerationDecision(LocalABCContract):
    """Freeze how the contaminated v2 ledger is replaced, not reused."""

    ledger_path: Literal["data/evals/benchmark/preflight-v3/planned_run_ledger.json"]
    functional_trajectories: Literal[162] = 162
    runtime_trajectories: Literal[180] = 180
    total_trajectories: Literal[342] = 342
    turns_per_trajectory: Literal[4] = 4
    total_turns: Literal[1368] = 1368
    maximum_request_attempts: Literal[2736] = 2736
    maximum_retries_after_initial_attempt: Literal[1] = 1
    counterbalanced_orders: tuple[Literal["A-B-C", "B-C-A", "C-A-B"], ...]
    required_fields: tuple[str, ...]
    reuse_preflight_v2_hash_bindings: Literal[False] = False
    every_attempt_retained: Literal[True] = True
    hidden_retry_permitted: Literal[False] = False
    replacement_case_permitted: Literal[False] = False

    @field_validator("counterbalanced_orders", "required_fields")
    @classmethod
    def validate_ordered_unique_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("ledger values must be unique")
        return value

    @model_validator(mode="after")
    def validate_count_arithmetic(self) -> Self:
        if self.functional_trajectories + self.runtime_trajectories != self.total_trajectories:
            raise ValueError("functional and runtime trajectories must reconcile")
        if self.total_trajectories * self.turns_per_trajectory != self.total_turns:
            raise ValueError("trajectory and turn counts must reconcile")
        if self.maximum_request_attempts != self.total_turns * 2:
            raise ValueError("maximum attempts must preserve one bounded retry per turn")
        if self.required_fields != _LEDGER_REQUIRED_FIELDS:
            raise ValueError("ledger required fields drifted")
        return self


class PreflightV3UnresolvedAsset(LocalABCContract):
    """One asset deliberately unresolved until its legal resolution stage."""

    asset_id: str
    resolution_stage: PreflightV3ResolutionStage
    required_before_measured_execution: Literal[True] = True
    current_state: Literal["UNRESOLVED"] = "UNRESOLVED"
    resolution_evidence: str = Field(min_length=12, max_length=360)

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("unresolved asset IDs must use stable lowercase characters")
        return value


class PreflightV3SafetyEnvelope(LocalABCContract):
    """Fail-closed review boundary; this artifact cannot authorize execution."""

    execution_enabled: Literal[False] = False
    preflight_v3_assets_generated: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    model_execution_performed: Literal[False] = False
    notebook_execution_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    customer_data_used: Literal[False] = False
    hosted_provider_required: Literal[False] = False
    paid_fallback_permitted: Literal[False] = False
    pricing_in_scope: Literal[False] = False
    external_spend: Literal[0] = 0
    claim_generation_permitted: Literal[False] = False


class FullABCLocalPreflightV3RebuildReview(LocalABCContract):
    """Authoritative review specifying, but not generating, the clean v3 lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-full-abc-local-preflight-v3-rebuild-review-v1"]
    source_main_merge_commit: Literal["f3e625518fb61af7c1a8197ef51ba5b38bcae510"]
    lifecycle_before: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    lifecycle_after: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    decision: Literal["APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION"]
    authority_bindings: tuple[PreflightV3AuthorityBinding, ...]
    dependency_lock_decision: PreflightV3DependencyLockDecision
    condition_fingerprint_decision: PreflightV3ConditionFingerprintDecision
    ledger_regeneration_decision: PreflightV3LedgerRegenerationDecision
    unresolved_assets: tuple[PreflightV3UnresolvedAsset, ...]
    safety: PreflightV3SafetyEnvelope
    next_gate: Literal["full_abc_local_preflight_v3_rebuild_implementation"]

    @field_validator("authority_bindings")
    @classmethod
    def validate_authority_bindings(
        cls,
        value: tuple[PreflightV3AuthorityBinding, ...],
    ) -> tuple[PreflightV3AuthorityBinding, ...]:
        binding_ids = tuple(item.binding_id for item in value)
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("authority binding IDs must be unique")
        if binding_ids != tuple(sorted(binding_ids)):
            raise ValueError("authority bindings must be canonically sorted")
        return value

    @field_validator("unresolved_assets")
    @classmethod
    def validate_unresolved_assets(
        cls,
        value: tuple[PreflightV3UnresolvedAsset, ...],
    ) -> tuple[PreflightV3UnresolvedAsset, ...]:
        asset_ids = tuple(item.asset_id for item in value)
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("unresolved asset IDs must be unique")
        if asset_ids != tuple(sorted(asset_ids)):
            raise ValueError("unresolved assets must be canonically sorted")
        return value

    @model_validator(mode="after")
    def validate_review_boundary(self) -> Self:
        if not any(
            item.binding_id == "preflight-v2-supersession" and not item.carry_forward_permitted
            for item in self.authority_bindings
        ):
            raise ValueError("the v2 supersession must be bound and marked non-reusable")
        required_stages = set(PreflightV3ResolutionStage)
        observed_stages = {item.resolution_stage for item in self.unresolved_assets}
        if observed_stages != required_stages:
            raise ValueError("unresolved assets must cover every future resolution stage")
        return self


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _canonical_json_file_sha256(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullABCLocalPreflightV3ReviewError(
            "REQUIRED_JSON_AUTHORITY_UNREADABLE",
            "required preflight-v3 review authority could not be read",
            path.as_posix(),
        ) from exc
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _git_content_sha256(repo_root: Path, relative_path: Path) -> str:
    """Hash committed content without depending on checkout line endings."""

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "cat-file",
                "blob",
                f"HEAD:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalPreflightV3ReviewError(
            "REQUIRED_CONTENT_AUTHORITY_UNREADABLE",
            "required preflight-v3 content authority could not be read",
            relative_path.as_posix(),
        ) from exc
    return hashlib.sha256(result.stdout).hexdigest()


def _git_index_blob_sha(repo_root: Path, relative_path: Path) -> str:
    """Read the committed Git blob identity without depending on checkout line endings."""

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                f"HEAD:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalPreflightV3ReviewError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required preflight-v3 Git authority could not be resolved",
            relative_path.as_posix(),
        ) from exc
    identity = result.stdout.strip()
    if _GIT_OBJECT_PATTERN.fullmatch(identity) is None:
        raise FullABCLocalPreflightV3ReviewError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required preflight-v3 Git authority returned an invalid identity",
            relative_path.as_posix(),
        )
    return identity


def build_default_review() -> FullABCLocalPreflightV3RebuildReview:
    """Build the review contract without generating any preflight-v3 execution assets."""

    authorities = (
        PreflightV3AuthorityBinding(
            binding_id="asset-inventory",
            role="PR 96 full execution-manifest asset census",
            source_locator=_INVENTORY_PATH.as_posix(),
            authority_kind=PreflightV3AuthorityKind.CANONICAL_SHA256,
            identity=_EXPECTED_INVENTORY_SHA256,
            carry_forward_permitted=True,
            notes=(
                "Carry forward the asset census, but reinterpret provider and budget "
                "blockers locally."
            ),
        ),
        PreflightV3AuthorityBinding(
            binding_id="benchmark-constitution",
            role="frozen causal contrasts, counts, quality gates, and claim boundaries",
            source_locator="docs/benchmark/AuraGateway_Benchmark_Constitution.md",
            authority_kind=PreflightV3AuthorityKind.CONTENT_SHA256,
            identity=_EXPECTED_BENCHMARK_CONSTITUTION_SHA256,
            carry_forward_permitted=True,
            notes="The causal constitution remains frozen and cannot be changed after effects.",
        ),
        PreflightV3AuthorityBinding(
            binding_id="execution-manifest-requirements",
            role="frozen requirements for the eventual execution-manifest boundary",
            source_locator="docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md",
            authority_kind=PreflightV3AuthorityKind.CONTENT_SHA256,
            identity=_EXPECTED_EXECUTION_REQUIREMENTS_SHA256,
            carry_forward_permitted=True,
            notes="The v3 rebuild must satisfy these requirements without freezing execution.",
        ),
        PreflightV3AuthorityBinding(
            binding_id="full-abc-integration",
            role="PR 95 shared A/B/C adapters, scorer, cleanup, trace, and preflight seams",
            source_locator="src/auragateway/local_abc/full_abc_harness_integration.py",
            authority_kind=PreflightV3AuthorityKind.GIT_BLOB_SHA,
            identity=_EXPECTED_INTEGRATION_BLOB_SHA,
            carry_forward_permitted=True,
            notes=(
                "Preserve the shared integration implementation and avoid "
                "condition-specific scoring."
            ),
        ),
        PreflightV3AuthorityBinding(
            binding_id="local-extension-prd",
            role="zero-spend controlled local A/B/C completion design baseline",
            source_locator="02_AuraGateway_Controlled_Local_ABC_Completion_Extension_PRD.md",
            authority_kind=PreflightV3AuthorityKind.LOCAL_DOCUMENT_SHA256,
            identity=_EXPECTED_LOCAL_EXTENSION_PRD_SHA256,
            carry_forward_permitted=True,
            notes=(
                "This local document governs direction but is not automatically promoted into Git."
            ),
        ),
        PreflightV3AuthorityBinding(
            binding_id="local-runtime-correction",
            role="PR 98 restored local vLLM runtime and model lineage",
            source_locator=_CORRECTION_PATH.as_posix(),
            authority_kind=PreflightV3AuthorityKind.CANONICAL_SHA256,
            identity=_EXPECTED_CORRECTION_SHA256,
            carry_forward_permitted=True,
            notes="Carry forward the exact local runtime identity and zero-spend safety state.",
        ),
        PreflightV3AuthorityBinding(
            binding_id="preflight-v2-supersession",
            role="PR 98 fail-closed block on contaminated preflight-v2 reuse",
            source_locator=_SUPERSESSION_PATH.as_posix(),
            authority_kind=PreflightV3AuthorityKind.CANONICAL_SHA256,
            identity=_EXPECTED_SUPERSESSION_SHA256,
            carry_forward_permitted=False,
            notes=(
                "Bind the supersession as a guardrail; do not carry any v2 execution "
                "bindings forward."
            ),
        ),
    )

    unresolved_assets = tuple(
        sorted(
            (
                PreflightV3UnresolvedAsset(
                    asset_id="cache-observability-qualification",
                    resolution_stage=PreflightV3ResolutionStage.DIAGNOSTIC_QUALIFICATION,
                    resolution_evidence=(
                        "Fresh same-worker reuse and explicit missing-state metric evidence."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="cache-pressure-diagnostics",
                    resolution_stage=PreflightV3ResolutionStage.DIAGNOSTIC_QUALIFICATION,
                    resolution_evidence=(
                        "Fresh pressure and idle-interval diagnostics under the current runtime."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="cache-reset-qualification",
                    resolution_stage=PreflightV3ResolutionStage.DIAGNOSTIC_QUALIFICATION,
                    resolution_evidence=(
                        "Verified reset or restart returning workers to a clean cache baseline."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="condition-fingerprints-v3",
                    resolution_stage=PreflightV3ResolutionStage.PREFLIGHT_V3_REBUILD,
                    resolution_evidence=(
                        "Generated from the accepted local-only fingerprint schema."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="current-environment-report",
                    resolution_stage=PreflightV3ResolutionStage.ENVIRONMENT_QUALIFICATION,
                    resolution_evidence=(
                        "Fresh Kaggle T4 x2, package, model, tokenizer, and worker qualification."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="developer-dependency-lock",
                    resolution_stage=PreflightV3ResolutionStage.PREFLIGHT_V3_REBUILD,
                    resolution_evidence=(
                        "Generated locally from pyproject and the validation environment."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="execution-manifest-freeze",
                    resolution_stage=PreflightV3ResolutionStage.EXECUTION_FREEZE,
                    resolution_evidence=(
                        "Frozen only after every prior gate and repetition decision passes."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="fault-diagnostics",
                    resolution_stage=PreflightV3ResolutionStage.DIAGNOSTIC_QUALIFICATION,
                    resolution_evidence=(
                        "Fresh fault report preserving task status and comparison eligibility."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="kaggle-runtime-dependency-lock",
                    resolution_stage=PreflightV3ResolutionStage.ENVIRONMENT_QUALIFICATION,
                    resolution_evidence=(
                        "Captured from the exact fresh Kaggle execution environment."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="measured-execution-authorization",
                    resolution_stage=PreflightV3ResolutionStage.EXECUTION_FREEZE,
                    resolution_evidence=(
                        "Separate explicit authorization after the manifest is frozen."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="planned-run-ledger-v3",
                    resolution_stage=PreflightV3ResolutionStage.PREFLIGHT_V3_REBUILD,
                    resolution_evidence=(
                        "Regenerated against v3 local fingerprints with all 342 trajectories."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="worker-isolation-qualification",
                    resolution_stage=PreflightV3ResolutionStage.DIAGNOSTIC_QUALIFICATION,
                    resolution_evidence=(
                        "Fresh cross-worker cache isolation and realized-route evidence."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="variance-pilot",
                    resolution_stage=PreflightV3ResolutionStage.VARIANCE_PILOT,
                    resolution_evidence=(
                        "Counterbalanced pilot with worker asymmetry and runtime variance."
                    ),
                ),
                PreflightV3UnresolvedAsset(
                    asset_id="repetition-count-freeze",
                    resolution_stage=PreflightV3ResolutionStage.VARIANCE_PILOT,
                    resolution_evidence=(
                        "Frozen from the eligible pilot before final condition effects."
                    ),
                ),
            ),
            key=lambda item: item.asset_id,
        )
    )

    return FullABCLocalPreflightV3RebuildReview(
        review_id=REVIEW_ID,
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        decision="APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION",
        authority_bindings=authorities,
        dependency_lock_decision=PreflightV3DependencyLockDecision(
            developer_lock_path=(
                "data/evals/benchmark/preflight-v3/developer_dependency_lock.json"
            ),
            kaggle_runtime_lock_path=(
                "data/evals/benchmark/preflight-v3/kaggle_runtime_dependency_lock.json"
            ),
            developer_lock_source_inputs=(
                "installed_validation_environment",
                "pyproject.toml",
            ),
            kaggle_lock_required_fields=(
                "attention_backend",
                "automatic_prefix_cache_configuration",
                "cuda_version",
                "dtype",
                "gpu_memory_utilization",
                "gpu_model",
                "maximum_model_length",
                "model_repository",
                "model_revision",
                "output_token_budget",
                "python_version",
                "quantization",
                "tokenizer_revision",
                "torch_version",
                "transformers_version",
                "vllm_distribution_version",
                "vllm_wheel_sha256",
                "worker_startup_command_sha256",
            ),
            current_kaggle_values_status="UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION",
        ),
        condition_fingerprint_decision=PreflightV3ConditionFingerprintDecision(
            artifact_path="data/evals/benchmark/preflight-v3/condition_fingerprints.json",
            shared_fields=_SHARED_FINGERPRINT_FIELDS,
            condition_specific_fields=_CONDITION_SPECIFIC_FINGERPRINT_FIELDS,
            prohibited_fields=_PROHIBITED_PREFLIGHT_V3_FIELDS,
            trace_field_provider_model_alias_semantics=(
                "legacy_name_bound_to_local_runtime_model_alias_without_provider_authority"
            ),
            trace_field_provider_model_alias_value="local-qwen2.5-0.5b-instruct",
        ),
        ledger_regeneration_decision=PreflightV3LedgerRegenerationDecision(
            ledger_path="data/evals/benchmark/preflight-v3/planned_run_ledger.json",
            counterbalanced_orders=("A-B-C", "B-C-A", "C-A-B"),
            required_fields=_LEDGER_REQUIRED_FIELDS,
        ),
        unresolved_assets=unresolved_assets,
        safety=PreflightV3SafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def load_full_abc_local_preflight_v3_rebuild_review(
    path: Path,
) -> FullABCLocalPreflightV3RebuildReview:
    """Load the canonical review artifact with metadata-safe failures."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FullABCLocalPreflightV3RebuildReview.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise FullABCLocalPreflightV3ReviewError(
            "PREFLIGHT_V3_REBUILD_REVIEW_INVALID",
            "the local preflight-v3 rebuild review artifact is missing or invalid",
            path.as_posix(),
        ) from exc


def write_default_review(path: Path) -> FullABCLocalPreflightV3RebuildReview:
    """Write only the review artifact; no execution or preflight-v3 assets are generated."""

    review = build_default_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.canonical_json(), encoding="utf-8")
    return review


def validate_repository_review_package(repo_root: Path) -> dict[str, object]:
    """Validate review authorities and return a privacy-safe operational summary."""

    review = load_full_abc_local_preflight_v3_rebuild_review(repo_root / REVIEW_PATH)

    checks = {
        "correction_sha256": _canonical_json_file_sha256(repo_root / _CORRECTION_PATH),
        "supersession_sha256": _canonical_json_file_sha256(repo_root / _SUPERSESSION_PATH),
        "inventory_sha256": _canonical_json_file_sha256(repo_root / _INVENTORY_PATH),
        "integration_blob_sha": _git_index_blob_sha(
            repo_root,
            Path("src/auragateway/local_abc/full_abc_harness_integration.py"),
        ),
        "inventory_source_blob_sha": _git_index_blob_sha(
            repo_root,
            Path("src/auragateway/local_abc/full_abc_execution_manifest_asset_inventory.py"),
        ),
        "correction_source_blob_sha": _git_index_blob_sha(
            repo_root,
            Path("src/auragateway/local_abc/full_abc_local_runtime_lineage_correction.py"),
        ),
        "benchmark_constitution_sha256": _git_content_sha256(
            repo_root,
            Path("docs/benchmark/AuraGateway_Benchmark_Constitution.md"),
        ),
        "execution_requirements_sha256": _git_content_sha256(
            repo_root,
            Path("docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md"),
        ),
    }
    expected = {
        "correction_sha256": _EXPECTED_CORRECTION_SHA256,
        "supersession_sha256": _EXPECTED_SUPERSESSION_SHA256,
        "inventory_sha256": _EXPECTED_INVENTORY_SHA256,
        "integration_blob_sha": _EXPECTED_INTEGRATION_BLOB_SHA,
        "inventory_source_blob_sha": _EXPECTED_INVENTORY_SOURCE_BLOB_SHA,
        "correction_source_blob_sha": _EXPECTED_CORRECTION_SOURCE_BLOB_SHA,
        "benchmark_constitution_sha256": _EXPECTED_BENCHMARK_CONSTITUTION_SHA256,
        "execution_requirements_sha256": _EXPECTED_EXECUTION_REQUIREMENTS_SHA256,
    }
    drift = tuple(sorted(name for name, value in checks.items() if value != expected[name]))
    if drift:
        raise FullABCLocalPreflightV3ReviewError(
            "PREFLIGHT_V3_REVIEW_AUTHORITY_DRIFT",
            "one or more preflight-v3 review authorities drifted",
            details=drift,
        )

    correction_payload = json.loads((repo_root / _CORRECTION_PATH).read_text(encoding="utf-8"))
    supersession_payload = json.loads((repo_root / _SUPERSESSION_PATH).read_text(encoding="utf-8"))
    if correction_payload.get("next_gate") != "full_abc_local_preflight_v3_rebuild_review":
        raise FullABCLocalPreflightV3ReviewError(
            "CORRECTION_NEXT_GATE_MISMATCH",
            "PR 98 correction no longer points to the required rebuild review",
        )
    blocked_flags = (
        correction_payload.get("preflight_v2_planning_authoritative") is False,
        correction_payload.get("preflight_v2_execution_eligible") is False,
        correction_payload.get("preflight_v2_comparison_eligible") is False,
        supersession_payload.get("preflight_v2_reuse_permitted") is False,
        supersession_payload.get("execution_authorized") is False,
    )
    if not all(blocked_flags):
        raise FullABCLocalPreflightV3ReviewError(
            "PREFLIGHT_V2_SUPERSESSION_NOT_FAIL_CLOSED",
            "the contaminated preflight-v2 lineage is not fully blocked",
        )

    return {
        "review_sha256": review.fingerprint(),
        "decision": review.decision,
        "lifecycle_after": review.lifecycle_after,
        "preflight_v2_reuse_permitted": False,
        "execution_enabled": review.safety.execution_enabled,
        "measured_execution_authorized": review.safety.measured_execution_authorized,
        "hosted_provider_required": review.safety.hosted_provider_required,
        "pricing_in_scope": review.safety.pricing_in_scope,
        "external_spend": review.safety.external_spend,
        "total_trajectories_to_regenerate": (
            review.ledger_regeneration_decision.total_trajectories
        ),
        "next_gate": review.next_gate,
    }
