"""Typed contracts for the clean local-only full A/B/C preflight-v3 rebuild."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract

SOURCE_MAIN_MERGE_COMMIT: Final = "3c9894d9b176329e4442aaedb4d93e88715ce38f"
REVIEW_SHA256: Final = "8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb"
REVIEW_SOURCE_BLOB_SHA: Final = "988276497b8e258f4675b820904769899e764f8a"
IMPLEMENTATION_ID: Final = "auragateway-full-abc-local-preflight-v3-rebuild-v1"
NEXT_GATE: Final = "full_abc_local_full_run_environment_qualification_review"

OUTPUT_ROOT: Final = Path("data/evals/benchmark/preflight-v3")
DEVELOPER_LOCK_PATH: Final = OUTPUT_ROOT / "developer_dependency_lock.json"
CONDITION_FINGERPRINTS_PATH: Final = OUTPUT_ROOT / "condition_fingerprints.json"
INPUT_PATH: Final = OUTPUT_ROOT / "input.json"
DRAFT_PATH: Final = OUTPUT_ROOT / "execution_manifest_draft.json"
LEDGER_PATH: Final = OUTPUT_ROOT / "planned_run_ledger.json"
REPORT_PATH: Final = OUTPUT_ROOT / "preflight_report.json"
MANIFEST_PATH: Final = OUTPUT_ROOT / "manifest.json"
IMPLEMENTATION_PLAN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_preflight_v3_rebuild_implementation_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_preflight_v3_rebuild_review_v1.json"
)
CORRECTION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_runtime_lineage_correction_v1.json"
)
SUPERSESSION_PATH: Final = Path(
    "data/evals/benchmark/preflight-v2/hosted_provider_lineage_supersession_v1.json"
)
INVENTORY_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_full_abc_execution_manifest_asset_inventory_v1.json"
)
FUNCTIONAL_EPISODES_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
RUNTIME_SELECTION_PATH: Final = Path("data/evals/episodes/runtime-v1/selection.json")
PREFIX_MANIFEST_PATH: Final = Path("data/context/prefix-determinism-v1/manifest.json")

_EXPECTED_REVIEW_SHA256: Final = REVIEW_SHA256
_EXPECTED_CORRECTION_SHA256: Final = (
    "1927239e919741f96b6c8017b241413b42d9528de109db1cd7df7a0dfd9b0fe7"
)
_EXPECTED_SUPERSESSION_SHA256: Final = (
    "df39761f7f6c73787bffacb5e933b4ea4d35f4079e86ff94ec846f63e2ae1cd6"
)
_EXPECTED_INVENTORY_SHA256: Final = (
    "900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6"
)
_EXPECTED_FUNCTIONAL_SHA256: Final = (
    "6229df94a6a426f815a2050172a79e115d9554031239043b397140ce13894285"
)
_EXPECTED_RUNTIME_SELECTION_SHA256: Final = (
    "5ff912ad317fe09d97518e5b03178ebe3bb565dcf09719182bfffc80b67034e1"
)
_EXPECTED_PREFIX_MANIFEST_SHA256: Final = (
    "a8b4f3d3afc7708c828f9ac195b42cf97b90e7060c58cefe29d7bdc5aba6101b"
)

_BENCHMARK_CONSTITUTION_SHA256: Final = (
    "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
)
_EXECUTION_REQUIREMENTS_SHA256: Final = (
    "30799246e6fa8d91246a5277e613ed97f840a164331f1f04a3f17fd84aad20cf"
)
_INTEGRATION_DESIGN_SHA256: Final = (
    "5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1"
)
_INTEGRATION_IMPLEMENTATION_SHA256: Final = (
    "758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662"
)
_ACTION_SCHEMA_SHA256: Final = "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
_PROMPT_POLICY_SHA256: Final = "750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c"
_RESPONSE_SCHEMA_SHA256: Final = "bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d"
_RETRIEVAL_CONFIGURATION_SHA256: Final = (
    "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"
)
_QUALITY_RUBRIC_SHA256: Final = "7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"
_PREFIX_FINGERPRINT: Final = "6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63"

_MODEL_ALIAS: Final = "local-qwen2.5-0.5b-instruct"
_MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
_MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
_TOKENIZER_REVISION: Final = _MODEL_REVISION
_TORCH_VERSION: Final = "2.11.0+cu129"
_TORCH_CUDA_VERSION: Final = "12.9"
_VLLM_DISTRIBUTION_VERSION: Final = "0.25.1+cu129"
_VLLM_WHEEL_SHA256: Final = "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"

_TRACE_FIELDS: Final = (
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

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,159}$"
_VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._+!-]{0,119}$"


class FullABCLocalPreflightV3RebuildError(RuntimeError):
    """Expected metadata-safe failure while generating or validating v3 assets."""

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


class FullABCLocalPreflightV3RebuildErrorEnvelope(LocalABCContract):
    """Safe CLI failure envelope without raw prompt, output, or secret content."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class DeveloperDependencyRole(StrEnum):
    """Role of one installed package in the local planning environment."""

    ACTIVE_RUNTIME = "active_runtime"
    HISTORICAL_HOSTED_PROVIDER = "historical_hosted_provider"
    DEVELOPMENT = "development"
    BUILD = "build"


class DeveloperDependencyPackage(LocalABCContract):
    """One exact installed distribution retained in the developer lock."""

    distribution_name: str
    version: str
    role: DeveloperDependencyRole
    active_full_abc_runtime_dependency: bool

    @field_validator("distribution_name")
    @classmethod
    def validate_distribution_name(cls, value: str) -> str:
        import re

        if re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$", value) is None:
            raise ValueError("distribution name contains unsupported characters")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        import re

        if re.fullmatch(_VERSION_PATTERN, value) is None:
            raise ValueError("dependency version contains unsupported characters")
        return value

    @model_validator(mode="after")
    def validate_runtime_role(self) -> Self:
        expected_active = self.role is DeveloperDependencyRole.ACTIVE_RUNTIME
        if self.active_full_abc_runtime_dependency is not expected_active:
            raise ValueError("active runtime flag must match the dependency role")
        return self


class DeveloperDependencyLock(LocalABCContract):
    """Exact local validation environment, separate from the Kaggle runtime lock."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    lock_id: Literal["auragateway-full-abc-developer-dependency-lock-v3"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    review_sha256: Literal["8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb"]
    pyproject_path: Literal["pyproject.toml"]
    pyproject_sha256: str
    project_name: Literal["auragateway"]
    project_version: str
    python_implementation: Literal["CPython"]
    python_version: str
    packages: tuple[
        DeveloperDependencyPackage,
        DeveloperDependencyPackage,
        DeveloperDependencyPackage,
        DeveloperDependencyPackage,
        DeveloperDependencyPackage,
        DeveloperDependencyPackage,
    ]
    hosted_provider_packages_active_for_full_abc: Literal[False] = False
    kaggle_runtime_lock_generated: Literal[False] = False
    execution_authorized: Literal[False] = False

    @field_validator("pyproject_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("developer dependency lock requires lowercase SHA-256")
        return value

    @field_validator("project_version", "python_version")
    @classmethod
    def validate_versions(cls, value: str) -> str:
        import re

        if re.fullmatch(_VERSION_PATTERN, value) is None:
            raise ValueError("project and Python versions contain unsupported characters")
        return value

    @model_validator(mode="after")
    def validate_packages(self) -> Self:
        names = tuple(package.distribution_name for package in self.packages)
        if names != _REQUIRED_DISTRIBUTIONS:
            raise ValueError("developer dependencies must preserve canonical package order")
        by_name = {package.distribution_name: package for package in self.packages}
        if by_name["groq"].role is not DeveloperDependencyRole.HISTORICAL_HOSTED_PROVIDER:
            raise ValueError("Groq must remain historical and outside the active runtime")
        if by_name["pydantic"].role is not DeveloperDependencyRole.ACTIVE_RUNTIME:
            raise ValueError("Pydantic must remain the active local contract runtime")
        return self


class RuntimeQualificationPlaceholder(LocalABCContract):
    """Canonical unresolved runtime fields that cannot be guessed in preflight-v3."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION"]
    required_fields: tuple[str, ...]
    values_guessed: Literal[False] = False

    @field_validator("required_fields")
    @classmethod
    def validate_required_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)) or value != tuple(sorted(value)):
            raise ValueError("runtime placeholder fields must be unique and sorted")
        return value


class MetricMappingPlan(LocalABCContract):
    """Versioned metric semantics to qualify against the installed vLLM release."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    mapping_id: Literal["local-vllm-cache-metric-mapping-plan-v1"]
    cache_observation_states: tuple[
        Literal["invalid", "not_exposed", "not_observed", "positive", "zero"], ...
    ]
    missing_field_becomes_zero: Literal[False] = False
    primary_metric_formula: Literal["eligible_shared_prefix_tokens-observed_cached_prefix_tokens"]
    current_metric_names_status: Literal["UNRESOLVED_BEFORE_CACHE_OBSERVABILITY_QUALIFICATION"]

    @field_validator("cache_observation_states")
    @classmethod
    def validate_states(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(value)) or len(value) != len(set(value)):
            raise ValueError("cache states must be unique and sorted")
        return value


class LocalRuntimeDirection(LocalABCContract):
    """Exact historical direction retained without claiming current qualification."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    execution_backend: Literal["local_vllm"]
    environment: Literal["kaggle_t4_x2"]
    transport_endpoint: Literal["/v1/chat/completions"]
    model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    torch_version: Literal["2.11.0+cu129"]
    torch_cuda_version: Literal["12.9"]
    vllm_distribution_version: Literal["0.25.1+cu129"]
    vllm_wheel_sha256: Literal["9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"]
    worker_client_contract: Literal["auragateway.local_abc.worker_client.WorkerClient"]
    worker_registry_contract: Literal["auragateway.local_abc.worker_registry.WorkerRegistry"]
    worker_bindings: tuple[Literal["worker_1=gpu0:8001", "worker_2=gpu1:8002"], ...]
    current_full_run_environment_requalification_required: Literal[True] = True
    hosted_provider_required: Literal[False] = False
    provider_credentials_required: Literal[False] = False
    paid_fallback_permitted: Literal[False] = False
    external_spend: Literal[0] = 0

    @field_validator("worker_bindings")
    @classmethod
    def validate_workers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != ("worker_1=gpu0:8001", "worker_2=gpu1:8002"):
            raise ValueError("local runtime must preserve the fixed two-worker topology")
        return value


class SharedConditionConfiguration(LocalABCContract):
    """Fields that must be identical across A, B, and C."""

    action_schema_sha256: str
    benchmark_constitution_sha256: str
    decoding_configuration_sha256: str
    environment: Literal["kaggle_t4_x2"]
    execution_backend: Literal["local_vllm"]
    execution_manifest_requirements_sha256: str
    metric_mapping_sha256: str
    model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    prompt_policy_sha256: str
    quality_rubric_sha256: str
    response_schema_sha256: str
    retrieval_configuration_sha256: str
    runtime_configuration_sha256: str
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    torch_cuda_version: Literal["12.9"]
    torch_version: Literal["2.11.0+cu129"]
    transport_endpoint: Literal["/v1/chat/completions"]
    vllm_distribution_version: Literal["0.25.1+cu129"]
    worker_client_contract: Literal["auragateway.local_abc.worker_client.WorkerClient"]
    worker_registry_contract: Literal["auragateway.local_abc.worker_registry.WorkerRegistry"]

    @field_validator("*")
    @classmethod
    def validate_digest_fields(cls, value: object, info: object) -> object:
        import re

        field_name = getattr(info, "field_name", "")
        if field_name.endswith("_sha256") and (
            not isinstance(value, str) or re.fullmatch(_SHA256_PATTERN, value) is None
        ):
            raise ValueError("shared condition digests must be lowercase SHA-256")
        return value


class ConditionFingerprintPayload(LocalABCContract):
    """Complete clean local configuration identity for one condition."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    condition_id: ConditionId
    cache_namespace_id: str
    prefix_policy: Literal["cache_hostile", "deterministic_exact"]
    prefix_token_hash: str
    prefix_token_hash_status: Literal["planning_identity_requires_runtime_confirmation"]
    route_schedule: tuple[Literal["worker_1", "worker_2"], Literal["worker_1", "worker_2"]]
    shared: SharedConditionConfiguration

    @field_validator("cache_namespace_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        import re

        if re.fullmatch(_ID_PATTERN, value) is None:
            raise ValueError("cache namespace must use stable lowercase characters")
        return value

    @field_validator("prefix_token_hash")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("prefix token identity must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_condition_contract(self) -> Self:
        expected = {
            ConditionId.A: ("cache_hostile", ("worker_1", "worker_2")),
            ConditionId.B: ("deterministic_exact", ("worker_1", "worker_2")),
            ConditionId.C: ("deterministic_exact", ("worker_1", "worker_1")),
        }
        if (self.prefix_policy, self.route_schedule) != expected[self.condition_id]:
            raise ValueError("condition fingerprint violates the frozen A/B/C design")
        return self


class ConditionFingerprintRecord(LocalABCContract):
    """One payload bound to its canonical configuration fingerprint."""

    payload: ConditionFingerprintPayload
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
            raise ValueError("configuration fingerprint must bind the canonical payload")
        return self


class TraceCompatibilityBoundary(LocalABCContract):
    """Temporary compatibility rule for the legacy trace field name."""

    field_name: Literal["provider_model_alias"]
    field_value: Literal["local-qwen2.5-0.5b-instruct"]
    semantics: Literal["legacy_name_bound_to_local_runtime_model_alias_without_provider_authority"]
    rename_requires_separate_contract_migration: Literal[True] = True


class ConditionFingerprintManifest(LocalABCContract):
    """Canonical A/B/C fingerprints with provider and pricing fields excluded."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-full-abc-condition-fingerprints-v3"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    review_sha256: Literal["8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb"]
    developer_dependency_lock_sha256: str
    trace_compatibility: TraceCompatibilityBoundary
    records: tuple[
        ConditionFingerprintRecord,
        ConditionFingerprintRecord,
        ConditionFingerprintRecord,
    ]
    provider_fields_present: Literal[False] = False
    pricing_fields_present: Literal[False] = False
    execution_authorized: Literal[False] = False

    @field_validator("developer_dependency_lock_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("condition manifest requires a lowercase dependency digest")
        return value

    @model_validator(mode="after")
    def validate_conditions(self) -> Self:
        if tuple(record.payload.condition_id for record in self.records) != tuple(ConditionId):
            raise ValueError("condition fingerprints must preserve A, B, C order")
        condition_a, condition_b, condition_c = (record.payload for record in self.records)
        if condition_a.route_schedule != condition_b.route_schedule:
            raise ValueError("A and B route schedules must remain equal")
        if condition_b.prefix_token_hash != condition_c.prefix_token_hash:
            raise ValueError("B and C prefix token identities must remain equal")
        if condition_a.prefix_token_hash == condition_b.prefix_token_hash:
            raise ValueError("A must retain a distinct cache-hostile prefix identity")
        if not (condition_a.shared == condition_b.shared == condition_c.shared):
            raise ValueError("all shared configuration fields must remain equal")
        serialized = self.canonical_json()
        prohibited = (
            "pricing_schedule",
            "provider_adapter",
            "provider_readiness",
            "cost_budget",
            '"currency"',
        )
        if any(token in serialized for token in prohibited):
            raise ValueError("active local fingerprints contain prohibited provider fields")
        return self

    def fingerprint_for(self, condition_id: ConditionId) -> str:
        """Return the exact fingerprint for one condition."""

        return next(
            record.configuration_fingerprint
            for record in self.records
            if record.payload.condition_id is condition_id
        )

    def route_schedule_for(self, condition_id: ConditionId) -> tuple[str, str]:
        """Return the exact route schedule for one condition."""

        record = next(
            record for record in self.records if record.payload.condition_id is condition_id
        )
        return cast(tuple[str, str], record.payload.route_schedule)


class PreflightV3PlanningInput(LocalABCContract):
    """Exact source identities used to generate the clean planning lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    input_id: Literal["auragateway-full-abc-local-preflight-v3-input-v1"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    review_sha256: str
    review_source_blob_sha: Literal["988276497b8e258f4675b820904769899e764f8a"]
    correction_sha256: str
    supersession_sha256: str
    asset_inventory_sha256: str
    functional_episode_set_sha256: str
    runtime_selection_sha256: str
    prefix_manifest_sha256: str
    developer_dependency_lock_sha256: str
    condition_fingerprints_sha256: str
    functional_episode_ids: tuple[str, ...]
    runtime_episode_ids: tuple[str, ...]
    execution_enabled: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    external_spend: Literal[0] = 0

    @field_validator(
        "review_sha256",
        "correction_sha256",
        "supersession_sha256",
        "asset_inventory_sha256",
        "functional_episode_set_sha256",
        "runtime_selection_sha256",
        "prefix_manifest_sha256",
        "developer_dependency_lock_sha256",
        "condition_fingerprints_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("preflight input identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_episode_sets(self) -> Self:
        if len(self.functional_episode_ids) != 18:
            raise ValueError("preflight-v3 requires exactly 18 functional episodes")
        if len(self.runtime_episode_ids) != 6:
            raise ValueError("preflight-v3 requires exactly six runtime episodes")
        if not set(self.runtime_episode_ids) <= set(self.functional_episode_ids):
            raise ValueError("runtime episodes must remain a functional subset")
        if self.functional_episode_ids != tuple(sorted(self.functional_episode_ids)):
            raise ValueError("functional episode IDs must remain sorted")
        if self.runtime_episode_ids != tuple(sorted(self.runtime_episode_ids)):
            raise ValueError("runtime episode IDs must remain sorted")
        return self


class ExecutionManifestPlanningIdentity(LocalABCContract):
    """Stable non-executable identity referenced by every planned trajectory."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    execution_manifest_id: Literal["execution-manifest-auragateway-local-abc-v3-draft"]
    execution_manifest_version: Literal["0.3.0-planning-draft"]
    execution_manifest_status: Literal["planning_draft"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    review_sha256: str
    developer_dependency_lock_sha256: str
    condition_fingerprints_sha256: str
    benchmark_constitution_sha256: str
    execution_requirements_sha256: str
    execution_enabled: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False

    @field_validator("*")
    @classmethod
    def validate_digests(cls, value: object, info: object) -> object:
        import re

        field_name = getattr(info, "field_name", "")
        if field_name.endswith("_sha256") and (
            not isinstance(value, str) or re.fullmatch(_SHA256_PATTERN, value) is None
        ):
            raise ValueError("manifest planning identities must be lowercase SHA-256")
        return value


class PlannedRun(LocalABCContract):
    """One immutable planned trajectory; no attempted run can disappear later."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    run_id: str
    trace_id: UUID
    comparison_pair_id: str
    workload: Literal["functional", "runtime_microbenchmark"]
    episode_id: str
    replication_id: str
    condition_id: ConditionId
    condition_configuration_fingerprint: str
    cache_namespace_id: str
    route_schedule_id: Literal[
        "turn-local-worker1-worker2-v1",
        "affinity-worker1-worker1-v1",
    ]
    planned_order_index: int = Field(ge=0)
    attempt_number: Literal[1] = 1
    turn_count: Literal[4] = 4
    maximum_request_attempts: Literal[8] = 8
    benchmark_manifest_sha256: str
    execution_manifest_sha256: str
    terminal_classification: Literal["not_started"] = "not_started"

    @field_validator("run_id", "comparison_pair_id", "episode_id", "replication_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        import re

        if re.fullmatch(_ID_PATTERN, value) is None:
            raise ValueError("planned run identifiers must use stable lowercase characters")
        return value

    @field_validator(
        "condition_configuration_fingerprint",
        "benchmark_manifest_sha256",
        "execution_manifest_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("planned run bindings must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_route(self) -> Self:
        expected = {
            ConditionId.A: "turn-local-worker1-worker2-v1",
            ConditionId.B: "turn-local-worker1-worker2-v1",
            ConditionId.C: "affinity-worker1-worker1-v1",
        }
        if self.route_schedule_id != expected[self.condition_id]:
            raise ValueError("planned route schedule does not match the condition")
        return self


class PlannedRunLedger(LocalABCContract):
    """Regenerated 342-trajectory ledger bound only to clean v3 identities."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    plan_id: Literal["benchmark-plan-auragateway-local-abc-v3"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    condition_fingerprints_sha256: str
    execution_manifest_planning_identity_sha256: str
    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    functional_trajectory_count: Literal[162] = 162
    runtime_trajectory_count: Literal[180] = 180
    total_trajectory_count: Literal[342] = 342
    total_turn_count: Literal[1368] = 1368
    maximum_request_attempt_count: Literal[2736] = 2736
    every_attempt_retained: Literal[True] = True
    hidden_retry_permitted: Literal[False] = False
    replacement_case_permitted: Literal[False] = False
    reuse_preflight_v2_hash_bindings: Literal[False] = False
    execution_enabled: Literal[False] = False
    runs: tuple[PlannedRun, ...]

    @field_validator(
        "condition_fingerprints_sha256",
        "execution_manifest_planning_identity_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("planned ledger requires lowercase SHA-256 bindings")
        return value

    @model_validator(mode="after")
    def validate_ledger(self) -> Self:
        if len(self.runs) != self.total_trajectory_count:
            raise ValueError("planned ledger must contain exactly 342 trajectories")
        if self.functional_trajectory_count + self.runtime_trajectory_count != len(self.runs):
            raise ValueError("functional and runtime trajectory counts must reconcile")
        if self.total_trajectory_count * 4 != self.total_turn_count:
            raise ValueError("trajectory and turn counts must reconcile")
        if self.total_turn_count * 2 != self.maximum_request_attempt_count:
            raise ValueError("maximum attempts must preserve one bounded retry per turn")
        if tuple(run.planned_order_index for run in self.runs) != tuple(range(len(self.runs))):
            raise ValueError("planned order indexes must be contiguous")
        unique_fields: tuple[tuple[object, ...], ...] = (
            tuple(run.run_id for run in self.runs),
            tuple(run.trace_id for run in self.runs),
            tuple(run.cache_namespace_id for run in self.runs),
        )
        if any(len(values) != len(set(values)) for values in unique_fields):
            raise ValueError("run, trace, and cache namespace identities must be unique")
        return self


class ExecutionManifestDraft(LocalABCContract):
    """Planning-complete but unfrozen and non-executable full A/B/C manifest draft."""

    schema_version: Literal["3.0.0"] = "3.0.0"
    identity: ExecutionManifestPlanningIdentity
    runtime_direction: LocalRuntimeDirection
    runtime_qualification_placeholder: RuntimeQualificationPlaceholder
    metric_mapping_plan_sha256: str
    decoding_configuration_plan_sha256: str
    planned_run_ledger_sha256: str
    frozen_asset_bindings: dict[str, str]
    unresolved_assets: tuple[str, ...]
    trace_fields: tuple[str, ...]
    task_status_separate_from_comparison_status: Literal[True] = True
    missing_telemetry_becomes_zero: Literal[False] = False
    provider_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0

    @field_validator(
        "metric_mapping_plan_sha256",
        "decoding_configuration_plan_sha256",
        "planned_run_ledger_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("execution draft bindings must be lowercase SHA-256")
        return value

    @field_validator("unresolved_assets", "trace_fields")
    @classmethod
    def validate_ordered_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("execution draft list values must be unique")
        return value

    @model_validator(mode="after")
    def validate_draft_boundary(self) -> Self:
        forbidden_keys = {
            "currency",
            "pricing_schedule_id",
            "provider_adapter_version",
            "provider_model_alias",
            "provider_readiness_record",
            "cost_budget_approval",
        }
        if forbidden_keys & set(self.frozen_asset_bindings):
            raise ValueError("execution draft contains prohibited hosted-provider bindings")
        if self.trace_fields != _TRACE_FIELDS:
            raise ValueError("execution draft trace field contract drifted")
        required_unresolved = {
            "cache-observability-qualification",
            "cache-pressure-diagnostics",
            "cache-reset-qualification",
            "current-environment-report",
            "execution-manifest-freeze",
            "fault-diagnostics",
            "kaggle-runtime-dependency-lock",
            "measured-execution-authorization",
            "repetition-count-freeze",
            "variance-pilot",
            "worker-isolation-qualification",
        }
        if set(self.unresolved_assets) != required_unresolved:
            raise ValueError("execution draft unresolved asset set drifted")
        return self


class PreflightV3CheckStatus(StrEnum):
    """Status of one planning-only preflight check."""

    PASS = "pass"
    BLOCKED_FOR_LATER_GATE = "blocked_for_later_gate"


class PreflightV3Check(LocalABCContract):
    """One metadata-safe preflight-v3 check result."""

    check_id: str
    status: PreflightV3CheckStatus
    evidence: str = Field(min_length=8, max_length=280)

    @field_validator("check_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        import re

        if re.fullmatch(_ID_PATTERN, value) is None:
            raise ValueError("preflight check IDs must use stable lowercase characters")
        return value


class PreflightV3Report(LocalABCContract):
    """Planning decision after all clean v3 artifacts are generated and cross-bound."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    report_id: Literal["auragateway-full-abc-local-preflight-v3-report-v1"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    decision: Literal["PLANNING_ASSETS_GENERATED_EXECUTION_BLOCKED"]
    checks: tuple[PreflightV3Check, ...]
    generated_asset_count: Literal[5] = 5
    total_trajectories: Literal[342] = 342
    lifecycle_before: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    lifecycle_after: Literal["LOCALLY_VALIDATED"] = "LOCALLY_VALIDATED"
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    gpu_execution_authorized: Literal[False] = False
    model_execution_performed: Literal[False] = False
    notebook_execution_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    hosted_provider_required: Literal[False] = False
    pricing_in_scope: Literal[False] = False
    external_spend: Literal[0] = 0
    claim_generation_permitted: Literal[False] = False
    next_gate: Literal["full_abc_local_full_run_environment_qualification_review"]

    @model_validator(mode="after")
    def validate_checks(self) -> Self:
        check_ids = tuple(check.check_id for check in self.checks)
        if len(check_ids) != len(set(check_ids)) or check_ids != tuple(sorted(check_ids)):
            raise ValueError("preflight checks must be unique and sorted")
        blocked = {
            check.check_id
            for check in self.checks
            if check.status is PreflightV3CheckStatus.BLOCKED_FOR_LATER_GATE
        }
        expected_blocked = {
            "cache-diagnostics",
            "environment-qualification",
            "execution-freeze",
            "variance-pilot",
        }
        if blocked != expected_blocked:
            raise ValueError("later-gate blockers must remain explicit")
        return self


class PreflightV3ArtifactBinding(LocalABCContract):
    """One generated artifact path and canonical content identity."""

    artifact_id: str
    path: str
    sha256: str

    @field_validator("artifact_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        import re

        if re.fullmatch(_ID_PATTERN, value) is None:
            raise ValueError("artifact IDs must use stable lowercase characters")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(_SHA256_PATTERN, value) is None:
            raise ValueError("artifact bindings require lowercase SHA-256")
        return value


class PreflightV3Manifest(LocalABCContract):
    """Terminal inventory for the generated but non-executable planning lineage."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-full-abc-local-preflight-v3-manifest-v1"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    implementation_id: Literal["auragateway-full-abc-local-preflight-v3-rebuild-v1"]
    artifacts: tuple[
        PreflightV3ArtifactBinding,
        PreflightV3ArtifactBinding,
        PreflightV3ArtifactBinding,
        PreflightV3ArtifactBinding,
        PreflightV3ArtifactBinding,
        PreflightV3ArtifactBinding,
    ]
    planning_lineage_complete: Literal[True] = True
    execution_enabled: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    next_gate: Literal["full_abc_local_full_run_environment_qualification_review"]

    @model_validator(mode="after")
    def validate_artifacts(self) -> Self:
        ids = tuple(item.artifact_id for item in self.artifacts)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("manifest artifacts must be unique and sorted")
        if "manifest" in ids:
            raise ValueError("manifest cannot contain a self-referential hash")
        return self


class GeneratedPreflightV3Bundle(LocalABCContract):
    """In-memory cross-bound result before canonical files are written."""

    developer_dependency_lock: DeveloperDependencyLock
    condition_fingerprints: ConditionFingerprintManifest
    planning_input: PreflightV3PlanningInput
    execution_manifest_draft: ExecutionManifestDraft
    planned_run_ledger: PlannedRunLedger
    preflight_report: PreflightV3Report
    manifest: PreflightV3Manifest


class PreflightV3ImplementationPlan(LocalABCContract):
    """Static implementation contract supplied with this bounded code slice."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    implementation_id: Literal["auragateway-full-abc-local-preflight-v3-rebuild-v1"]
    source_main_merge_commit: Literal["3c9894d9b176329e4442aaedb4d93e88715ce38f"]
    review_path: Literal[
        "benchmarks/local_abc/auragateway_full_abc_local_preflight_v3_rebuild_review_v1.json"
    ]
    review_sha256: Literal["8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb"]
    review_source_blob_sha: Literal["988276497b8e258f4675b820904769899e764f8a"]
    output_paths: tuple[str, ...]
    generated_planning_assets: tuple[str, ...]
    later_gate_assets: tuple[str, ...]
    execution_enabled: Literal[False] = False
    external_spend: Literal[0] = 0
    next_gate: Literal["full_abc_local_full_run_environment_qualification_review"]

    @field_validator("output_paths", "generated_planning_assets", "later_gate_assets")
    @classmethod
    def validate_ordered_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)) or value != tuple(sorted(value)):
            raise ValueError("implementation plan lists must be unique and sorted")
        return value
