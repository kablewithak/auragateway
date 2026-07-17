"""Typed contracts for full A/B/C execution-manifest draft reconciliation."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_SHA_PATTERN = r"^[0-9a-f]{40}$"
_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,159}$"
_PACKAGE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"
_VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._+!-]{0,119}$"

_SOURCE_MERGE_COMMIT: Final = "d6531fdc0b27892dcc299598f9f251fa157434dc"
_INTEGRATION_DESIGN_SHA256: Final = (
    "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
)
_INTEGRATION_IMPLEMENTATION_SHA256: Final = (
    "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
)
_ASSET_INVENTORY_SHA256: Final = "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"
_BENCHMARK_CONSTITUTION_SHA256: Final = (
    "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
)
_PROMPT_POLICY_SHA256: Final = "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
_RESPONSE_SCHEMA_SHA256: Final = "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
_ACTION_SCHEMA_SHA256: Final = "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
_EXPECTED_TRACE_FIELDS: Final = (
    "run_id",
    "trace_id",
    "comparison_pair_id",
    "episode_id",
    "replication_id",
    "condition_id",
    "cache_namespace_id",
    "session_id_hash",
    "provider_model_alias",
    "benchmark_manifest_hash",
    "execution_manifest_hash",
    "configuration_fingerprint",
    "score_prompt_policy_sha256",
    "score_rendered_prompt_sha256",
    "cleanup_status",
    "cleanup_warning_codes",
)
_REQUIRED_DISTRIBUTIONS: Final = (
    "groq",
    "pydantic",
    "mypy",
    "pytest",
    "ruff",
    "setuptools",
)
_FUNCTIONAL_SCHEDULE: Final = (
    (ConditionId.A, ConditionId.B, ConditionId.C),
    (ConditionId.B, ConditionId.C, ConditionId.A),
    (ConditionId.C, ConditionId.A, ConditionId.B),
)
_RUNTIME_SCHEDULE: Final = (
    (ConditionId.A, ConditionId.B, ConditionId.C),
    (ConditionId.B, ConditionId.C, ConditionId.A),
    (ConditionId.C, ConditionId.A, ConditionId.B),
    (ConditionId.A, ConditionId.C, ConditionId.B),
    (ConditionId.C, ConditionId.B, ConditionId.A),
    (ConditionId.B, ConditionId.A, ConditionId.C),
    (ConditionId.A, ConditionId.B, ConditionId.C),
    (ConditionId.B, ConditionId.C, ConditionId.A),
    (ConditionId.C, ConditionId.A, ConditionId.B),
    (ConditionId.C, ConditionId.B, ConditionId.A),
)
_OUTPUT_ROOT: Final = Path("data/evals/benchmark/preflight-v2")
_DEPENDENCY_LOCK_PATH: Final = _OUTPUT_ROOT / "dependency_lock.json"
_CONDITION_FINGERPRINTS_PATH: Final = _OUTPUT_ROOT / "condition_fingerprints.json"
_INPUT_PATH: Final = _OUTPUT_ROOT / "input.json"
_DRAFT_PATH: Final = _OUTPUT_ROOT / "execution_manifest_draft.json"
_LEDGER_PATH: Final = _OUTPUT_ROOT / "planned_run_ledger.json"
_REPORT_PATH: Final = _OUTPUT_ROOT / "preflight_report.json"
_MANIFEST_PATH: Final = _OUTPUT_ROOT / "manifest.json"


class FullABCReconciliationError(Exception):
    """Expected local reconciliation failure with safe metadata-only details."""

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


class FullABCReconciliationErrorEnvelope(LocalABCContract):
    """Safe CLI failure envelope."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class FullABCDependencyRole(StrEnum):
    """Role of one exact package resolution in the benchmark environment."""

    RUNTIME = "runtime"
    DEVELOPMENT = "development"
    BUILD = "build"


class FullABCDependencyPackage(LocalABCContract):
    """Exact installed distribution version retained in the local dependency lock."""

    distribution_name: str
    version: str
    role: FullABCDependencyRole

    @field_validator("distribution_name")
    @classmethod
    def validate_distribution_name(cls, value: str) -> str:
        import re

        if re.fullmatch(_PACKAGE_PATTERN, value) is None:
            raise ValueError("distribution names must use stable package characters")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        import re

        if re.fullmatch(_VERSION_PATTERN, value) is None:
            raise ValueError("dependency versions must use stable version characters")
        return value


class FullABCDependencyLock(LocalABCContract):
    """Exact environment identity generated from the active validated virtual environment."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    lock_id: Literal["auragateway-full-abc-dependency-lock-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    pyproject_path: Literal["pyproject.toml"]
    pyproject_sha256: str
    project_name: Literal["auragateway"]
    project_version: str
    python_implementation: Literal["CPython"]
    python_version: str
    packages: tuple[
        FullABCDependencyPackage,
        FullABCDependencyPackage,
        FullABCDependencyPackage,
        FullABCDependencyPackage,
        FullABCDependencyPackage,
        FullABCDependencyPackage,
    ]
    execution_authorized: Literal[False] = False

    @field_validator("pyproject_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("dependency lock requires a lowercase SHA-256")
        return value

    @field_validator("project_version", "python_version")
    @classmethod
    def validate_versions(cls, value: str) -> str:
        import re

        if re.fullmatch(_VERSION_PATTERN, value) is None:
            raise ValueError("project and Python versions must use stable characters")
        return value

    @model_validator(mode="after")
    def validate_packages(self) -> Self:
        names = tuple(package.distribution_name for package in self.packages)
        if names != _REQUIRED_DISTRIBUTIONS:
            raise ValueError("dependency packages must preserve the frozen package order")
        expected_roles = {
            "groq": FullABCDependencyRole.RUNTIME,
            "pydantic": FullABCDependencyRole.RUNTIME,
            "mypy": FullABCDependencyRole.DEVELOPMENT,
            "pytest": FullABCDependencyRole.DEVELOPMENT,
            "ruff": FullABCDependencyRole.DEVELOPMENT,
            "setuptools": FullABCDependencyRole.BUILD,
        }
        if any(
            package.role is not expected_roles[package.distribution_name]
            for package in self.packages
        ):
            raise ValueError("dependency package roles drifted")
        return self


class FullABCConditionFingerprintPayload(LocalABCContract):
    """Complete condition configuration identity used by comparison preflight."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    condition_id: ConditionId
    adapter_sha256: str
    dependency_lock_sha256: str
    integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ]
    integration_implementation_sha256: Literal[
        "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
    ]
    benchmark_constitution_sha256: Literal[
        "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
    ]
    retrieval_configuration_sha256: str
    prompt_policy_sha256: Literal[
        "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
    ]
    response_schema_sha256: Literal[
        "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
    ]
    action_schema_sha256: Literal[
        "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
    ]
    provider_model_alias: str
    provider_adapter_version: str
    pricing_schedule_id: str
    benchmark_runner_version: Literal["2.0.0-local-abc-reconciled"]

    @field_validator(
        "adapter_sha256",
        "dependency_lock_sha256",
        "retrieval_configuration_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("condition payload digests must be lowercase SHA-256")
        return value

    @field_validator("provider_model_alias", "provider_adapter_version", "pricing_schedule_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        import re

        if re.fullmatch(_ID_PATTERN, value) is None:
            raise ValueError("condition configuration identifiers use unsupported characters")
        return value


class FullABCConditionConfigurationFingerprint(LocalABCContract):
    """One hash-bound condition configuration."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    payload: FullABCConditionFingerprintPayload
    configuration_fingerprint: str

    @field_validator("configuration_fingerprint")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("configuration fingerprint must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.configuration_fingerprint != self.payload.fingerprint():
            raise ValueError("configuration fingerprint must match the canonical payload")
        return self


class FullABCConditionFingerprintManifest(LocalABCContract):
    """Canonical A/B/C configuration fingerprints derived from the PR 95 adapters."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-full-abc-condition-fingerprints-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    dependency_lock_sha256: str
    records: tuple[
        FullABCConditionConfigurationFingerprint,
        FullABCConditionConfigurationFingerprint,
        FullABCConditionConfigurationFingerprint,
    ]
    execution_authorized: Literal[False] = False

    @field_validator("dependency_lock_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("condition manifest requires a lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_records(self) -> Self:
        if tuple(record.payload.condition_id for record in self.records) != tuple(ConditionId):
            raise ValueError("condition fingerprints must preserve A, B, C order")
        fingerprints = tuple(record.configuration_fingerprint for record in self.records)
        if len(set(fingerprints)) != 3:
            raise ValueError("condition configuration fingerprints must be distinct")
        if any(
            record.payload.dependency_lock_sha256 != self.dependency_lock_sha256
            for record in self.records
        ):
            raise ValueError("all condition records must bind the same dependency lock")
        return self

    def fingerprint_for(self, condition_id: ConditionId) -> str:
        """Return the expected configuration fingerprint for one condition."""

        return self.records[
            {ConditionId.A: 0, ConditionId.B: 1, ConditionId.C: 2}[condition_id]
        ].configuration_fingerprint


class FullABCReconciliationSpec(LocalABCContract):
    """Static source and path constitution for local-only draft reconciliation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    reconciliation_id: Literal["auragateway-full-abc-execution-manifest-reconciliation-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    legacy_input_path: str
    integration_design_path: str
    integration_implementation_path: str
    asset_inventory_path: str
    benchmark_constitution_path: str
    execution_requirements_path: str
    gate8_manifest_path: str
    gate7_manifest_path: str
    pricing_schedule_path: str
    negative_controls_path: str
    fault_fixtures_path: str
    privacy_verification_path: str
    pyproject_path: Literal["pyproject.toml"]
    expected_integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ]
    expected_integration_implementation_sha256: Literal[
        "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
    ]
    expected_asset_inventory_sha256: Literal[
        "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"
    ]
    expected_benchmark_constitution_sha256: Literal[
        "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
    ]
    required_distributions: tuple[str, ...]
    next_gate: Literal["full_abc_provider_readiness_and_budget_review"]
    execution_enabled: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False

    @field_validator(
        "legacy_input_path",
        "integration_design_path",
        "integration_implementation_path",
        "asset_inventory_path",
        "benchmark_constitution_path",
        "execution_requirements_path",
        "gate8_manifest_path",
        "gate7_manifest_path",
        "pricing_schedule_path",
        "negative_controls_path",
        "fault_fixtures_path",
        "privacy_verification_path",
    )
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("reconciliation paths must remain repository-relative")
        return path.as_posix()

    @field_validator("required_distributions")
    @classmethod
    def validate_required_distributions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _REQUIRED_DISTRIBUTIONS:
            raise ValueError("required distributions drifted from the frozen reconciliation set")
        return value


class FullABCReconciliationInput(LocalABCContract):
    """Hash-bound local inputs used to build the reconciled draft lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    reconciliation_id: Literal["auragateway-full-abc-execution-manifest-reconciliation-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    spec_path: str
    spec_sha256: str
    legacy_input_path: str
    legacy_input_sha256: str
    integration_design_path: str
    integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ]
    integration_implementation_path: str
    integration_implementation_sha256: Literal[
        "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
    ]
    asset_inventory_path: str
    asset_inventory_sha256: Literal[
        "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"
    ]
    dependency_lock_path: str
    dependency_lock_sha256: str
    condition_fingerprints_path: str
    condition_fingerprints_sha256: str
    static_asset_hashes: dict[str, str]
    trace_fields: tuple[str, ...]
    execution_requested: Literal[False] = False

    @field_validator(
        "spec_sha256",
        "legacy_input_sha256",
        "dependency_lock_sha256",
        "condition_fingerprints_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("reconciliation input digests must be lowercase SHA-256")
        return value

    @field_validator("static_asset_hashes")
    @classmethod
    def validate_static_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        import re

        expected = {
            "benchmark_constitution",
            "execution_requirements",
            "gate8_manifest",
            "gate7_manifest",
            "pricing_schedule",
            "negative_controls",
            "fault_fixtures",
            "privacy_verification",
            "pyproject",
        }
        if set(value) != expected:
            raise ValueError("reconciliation static asset hash set drifted")
        if any(re.fullmatch(_SHA256_PATTERN, item) is None for item in value.values()):
            raise ValueError("static asset hashes must be lowercase SHA-256")
        return dict(sorted(value.items()))

    @field_validator("trace_fields")
    @classmethod
    def validate_trace_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_TRACE_FIELDS:
            raise ValueError("reconciliation trace fields drifted")
        return value


class FullABCReconciledManifestIdentity(LocalABCContract):
    """Current non-executing draft identity bound to the PR 95 and PR 96 lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    execution_manifest_id: Literal["execution-manifest-auragateway-v2-draft"]
    execution_manifest_version: Literal["0.2.0-draft"]
    execution_manifest_status: Literal["draft"]
    execution_manifest_sha256: None = None
    benchmark_constitution_version: Literal["1.0.0"]
    benchmark_constitution_sha256: Literal[
        "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
    ]
    benchmark_runner_version: Literal["2.0.0-local-abc-reconciled"]
    comparison_eligibility_contract_version: Literal["full-abc-comparison-preflight-v1"]
    evidence_bundle_schema_version: Literal["1.0.0"]
    git_commit_sha: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    python_version: str
    dependency_lock_sha256: str
    integration_design_sha256: Literal[
        "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
    ]
    integration_implementation_sha256: Literal[
        "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
    ]
    asset_inventory_sha256: Literal[
        "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"
    ]
    condition_fingerprints_sha256: str
    execution_enabled: Literal[False] = False

    @field_validator("dependency_lock_sha256", "condition_fingerprints_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("reconciled manifest identity requires lowercase SHA-256")
        return value


class FullABCReconciledManifestAssets(LocalABCContract):
    """Resolved static assets and explicit freeze-time gaps for the v2 draft."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    legacy_execution_manifest_assets_sha256: str
    corpus_manifest_sha256: str
    chunking_configuration_sha256: str
    retrieval_configuration_sha256: str
    development_retrieval_manifest_sha256: str
    held_out_retrieval_manifest_sha256: str
    retrieval_scorecard_sha256: str
    prompt_policy_sha256: Literal[
        "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
    ]
    response_schema_sha256: Literal[
        "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
    ]
    action_schema_sha256: Literal[
        "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
    ]
    diagnostic_episode_manifest_sha256: str
    functional_benchmark_manifest_sha256: str
    runtime_microbenchmark_manifest_sha256: str
    quality_rubric_sha256: str
    review_sample_schedule_sha256: str
    feedback_manifest_sha256: str
    comparison_eligibility_manifest_sha256: str
    telemetry_fixture_manifest_sha256: str
    provider_model_alias: str
    provider_adapter_version: str
    pricing_schedule_id: str
    pricing_source_date: str
    currency: Literal["USD"]
    pricing_schedule_sha256: str
    negative_control_manifest_sha256: str
    fault_injection_fixture_sha256: str
    privacy_verification_report_sha256: str
    condition_fingerprints_sha256: str
    cross_condition_isolation_test_sha256: None = None
    provider_readiness_record_sha256: None = None

    @field_validator(
        "legacy_execution_manifest_assets_sha256",
        "corpus_manifest_sha256",
        "chunking_configuration_sha256",
        "retrieval_configuration_sha256",
        "development_retrieval_manifest_sha256",
        "held_out_retrieval_manifest_sha256",
        "retrieval_scorecard_sha256",
        "diagnostic_episode_manifest_sha256",
        "functional_benchmark_manifest_sha256",
        "runtime_microbenchmark_manifest_sha256",
        "quality_rubric_sha256",
        "review_sample_schedule_sha256",
        "feedback_manifest_sha256",
        "comparison_eligibility_manifest_sha256",
        "telemetry_fixture_manifest_sha256",
        "pricing_schedule_sha256",
        "negative_control_manifest_sha256",
        "fault_injection_fixture_sha256",
        "privacy_verification_report_sha256",
        "condition_fingerprints_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("reconciled manifest assets require lowercase SHA-256")
        return value


class FullABCReconciledManifestControls(LocalABCContract):
    """Frozen run-order, retry, denominator, statistical, and quality controls."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    legacy_execution_manifest_controls_sha256: str
    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    timeout_policy_id: Literal["provider-request-policy-v1"]
    retry_policy_id: Literal["provider-request-policy-v1"]
    exclusion_policy_id: Literal["exclusion-policy-v1"]
    rerun_policy_id: Literal["rerun-policy-v1"]
    denominator_policy_id: Literal["denominator-policy-v1"]
    statistical_reporting_configuration_id: Literal["paired-bootstrap-v1"]
    quality_non_inferiority_policy_id: Literal["quality-non-inferiority-v1"]
    trace_fields: tuple[str, ...]

    @field_validator("legacy_execution_manifest_controls_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("controls identity must be lowercase SHA-256")
        return value

    @field_validator("trace_fields")
    @classmethod
    def validate_trace_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_TRACE_FIELDS:
            raise ValueError("manifest controls must retain every hardened trace field")
        return value


class FullABCReconciledExecutionManifestDraft(LocalABCContract):
    """Current local-only draft that is explicitly not a Gate 10 frozen manifest."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    identity: FullABCReconciledManifestIdentity
    assets: FullABCReconciledManifestAssets
    controls: FullABCReconciledManifestControls
    unresolved_freeze_assets: tuple[str, ...]
    measured_execution_authorized: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False

    @field_validator("unresolved_freeze_assets")
    @classmethod
    def validate_unresolved_assets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        expected = (
            "cost_budget_approval",
            "cross_condition_isolation_report",
            "final_execution_manifest",
            "freeze_report",
            "gate10_manifest",
            "provider_readiness_record",
        )
        if value != expected:
            raise ValueError("draft unresolved freeze assets drifted")
        return value


class FullABCReconciledPlannedRun(LocalABCContract):
    """One deterministic planned trajectory with its exact condition fingerprint."""

    schedule_index: int = Field(ge=0)
    run_id: str
    comparison_pair_id: str
    workload: Literal["functional", "runtime_microbenchmark"]
    episode_id: str
    replication_id: str
    condition_id: ConditionId
    benchmark_condition_id: Literal["condition_a", "condition_b", "condition_c"]
    condition_order_index: int = Field(ge=0, le=2)
    cache_namespace_id: str
    configuration_fingerprint: str
    turn_count: Literal[4] = 4
    maximum_request_attempt_count: Literal[8] = 8

    @field_validator("configuration_fingerprint")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("planned run configuration fingerprint must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_condition_mapping(self) -> Self:
        expected = {
            ConditionId.A: "condition_a",
            ConditionId.B: "condition_b",
            ConditionId.C: "condition_c",
        }
        if self.benchmark_condition_id != expected[self.condition_id]:
            raise ValueError("planned run benchmark condition mapping drifted")
        return self


class FullABCReconciledPlannedRunLedger(LocalABCContract):
    """Current 342-trajectory plan bound to the PR 95 condition fingerprints."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    plan_id: Literal["benchmark-plan-auragateway-abc-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    condition_fingerprints_sha256: str
    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    runs: tuple[FullABCReconciledPlannedRun, ...] = Field(min_length=342, max_length=342)
    functional_trajectory_count: Literal[162] = 162
    runtime_trajectory_count: Literal[180] = 180
    total_trajectory_count: Literal[342] = 342
    total_turn_count: Literal[1368] = 1368
    maximum_request_attempt_count: Literal[2736] = 2736
    execution_enabled: Literal[False] = False

    @field_validator("condition_fingerprints_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("ledger fingerprint manifest hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_ledger(self) -> Self:
        indexes = tuple(run.schedule_index for run in self.runs)
        if indexes != tuple(range(342)):
            raise ValueError("planned run indexes must be contiguous and ordered")
        run_ids = tuple(run.run_id for run in self.runs)
        namespaces = tuple(run.cache_namespace_id for run in self.runs)
        if len(set(run_ids)) != 342 or len(set(namespaces)) != 342:
            raise ValueError("planned run IDs and cache namespaces must be unique")
        if sum(run.workload == "functional" for run in self.runs) != 162:
            raise ValueError("functional run count must remain 162")
        if sum(run.workload == "runtime_microbenchmark" for run in self.runs) != 180:
            raise ValueError("runtime run count must remain 180")
        return self


class FullABCReconciliationCheckName(StrEnum):
    """Local-only checks required before provider readiness review."""

    SOURCE_COMMIT_CURRENT = "source_commit_current"
    DEPENDENCY_LOCK_RESOLVED = "dependency_lock_resolved"
    CONDITION_FINGERPRINTS_RESOLVED = "condition_fingerprints_resolved"
    INTEGRATION_LINEAGE_CURRENT = "integration_lineage_current"
    STATIC_ASSETS_BOUND = "static_assets_bound"
    PLANNED_LEDGER_CURRENT = "planned_ledger_current"
    TRACE_FIELDS_CURRENT = "trace_fields_current"
    EXECUTION_DISABLED = "execution_disabled"
    PROVIDER_READINESS_PENDING = "provider_readiness_pending"
    COST_APPROVAL_PENDING = "cost_approval_pending"
    FREEZE_OUTPUTS_PENDING = "freeze_outputs_pending"


class FullABCReconciliationCheckStatus(StrEnum):
    """Result of one reconciliation check."""

    PASSED = "passed"
    BLOCKED_EXTERNAL = "blocked_external"
    PENDING_FREEZE = "pending_freeze"


class FullABCReconciliationCheck(LocalABCContract):
    """One explicit draft reconciliation result."""

    check_name: FullABCReconciliationCheckName
    status: FullABCReconciliationCheckStatus
    details: tuple[str, ...] = ()


class FullABCReconciliationReport(LocalABCContract):
    """Planning-readiness report that grants no execution authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: Literal["auragateway-full-abc-draft-reconciliation-report-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    checks: tuple[FullABCReconciliationCheck, ...]
    functional_trajectory_count: Literal[162] = 162
    runtime_trajectory_count: Literal[180] = 180
    total_trajectory_count: Literal[342] = 342
    total_turn_count: Literal[1368] = 1368
    maximum_request_attempt_count: Literal[2736] = 2736
    planning_ready: Literal[True] = True
    draft_current: Literal[True] = True
    measured_execution_ready: Literal[False] = False
    execution_enabled: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    next_gate: Literal["full_abc_provider_readiness_and_budget_review"]

    @model_validator(mode="after")
    def validate_checks(self) -> Self:
        if tuple(check.check_name for check in self.checks) != tuple(
            FullABCReconciliationCheckName
        ):
            raise ValueError("reconciliation checks must preserve the frozen order")
        passed = {
            FullABCReconciliationCheckName.SOURCE_COMMIT_CURRENT,
            FullABCReconciliationCheckName.DEPENDENCY_LOCK_RESOLVED,
            FullABCReconciliationCheckName.CONDITION_FINGERPRINTS_RESOLVED,
            FullABCReconciliationCheckName.INTEGRATION_LINEAGE_CURRENT,
            FullABCReconciliationCheckName.STATIC_ASSETS_BOUND,
            FullABCReconciliationCheckName.PLANNED_LEDGER_CURRENT,
            FullABCReconciliationCheckName.TRACE_FIELDS_CURRENT,
            FullABCReconciliationCheckName.EXECUTION_DISABLED,
        }
        for check in self.checks:
            if (
                check.check_name in passed
                and check.status is not FullABCReconciliationCheckStatus.PASSED
            ):
                raise ValueError("all local reconciliation checks must pass")
        return self


class FullABCReconciliationManifest(LocalABCContract):
    """Hash-bound inventory for the complete preflight-v2 reconciliation lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-full-abc-draft-reconciliation-manifest-v2"]
    source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    spec_path: str
    spec_sha256: str
    dependency_lock_path: str
    dependency_lock_sha256: str
    condition_fingerprints_path: str
    condition_fingerprints_sha256: str
    input_path: str
    input_sha256: str
    execution_manifest_path: str
    execution_manifest_sha256: str
    plan_path: str
    plan_sha256: str
    report_path: str
    report_sha256: str
    total_trajectory_count: Literal[342] = 342
    total_turn_count: Literal[1368] = 1368
    maximum_request_attempt_count: Literal[2736] = 2736
    planning_ready: Literal[True] = True
    draft_current: Literal[True] = True
    measured_execution_ready: Literal[False] = False
    execution_enabled: Literal[False] = False
    measured_execution_permitted: Literal[False] = False
    next_gate: Literal["full_abc_provider_readiness_and_budget_review"]

    @field_validator(
        "spec_sha256",
        "dependency_lock_sha256",
        "condition_fingerprints_sha256",
        "input_sha256",
        "execution_manifest_sha256",
        "plan_sha256",
        "report_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("reconciliation manifest digests must be lowercase SHA-256")
        return value


class FullABCReconciliationSummary(LocalABCContract):
    """Safe CLI output for generate and verify."""

    source_merge_commit: str
    dependency_lock_sha256: str
    condition_fingerprints_sha256: str
    execution_manifest_draft_sha256: str
    planned_run_ledger_sha256: str
    reconciliation_manifest_sha256: str
    total_trajectory_count: int
    planning_ready: bool
    draft_current: bool
    measured_execution_ready: bool
    execution_enabled: bool
    measured_execution_permitted: bool
    next_gate: str

    @field_validator("source_merge_commit")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        import re

        if re.fullmatch(_GIT_SHA_PATTERN, value) is None:
            raise ValueError("summary source commit must be lowercase Git SHA")
        return value

    @field_validator(
        "dependency_lock_sha256",
        "condition_fingerprints_sha256",
        "execution_manifest_draft_sha256",
        "planned_run_ledger_sha256",
        "reconciliation_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("summary digests must be lowercase SHA-256")
        return value
