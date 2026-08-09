"""Define exact-runtime P5/P6 behavioral requalification design V1.

This module is design-only reliability infrastructure. It validates accepted
repository authorities and freezes the behavioral contract for the future
exact-runtime P5/P6 implementation. It does not install packages, load models,
start workers, issue model requests, issue runtime authorization, run a pilot,
or execute measured A/B/C work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "fa134894c29178d20ad0ff14b0aa921f257e692b"

V5_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_record.json"
)
V5_ACCEPTANCE_RECORD_SHA256: Final = (
    "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
)
RUNTIME_LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
RUNTIME_LOCK_SHA256: Final = "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
V5_SEMANTIC_BOUNDARY_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_semantic_boundary_design_v1.json"
)
V5_SEMANTIC_BOUNDARY_SHA256: Final = (
    "1d248baa983edebeda4f0fa95aa5a70c870d18dcba374249c40125cc81e48c75"
)
HISTORICAL_P5_P6_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
)
HISTORICAL_P5_P6_ACCEPTANCE_SHA256: Final = (
    "d0268386d8d934257d035c2f720276d39e94a9eb0daa7da51175cc2cda3c1539"
)
HISTORICAL_P5_P6_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1_review.json"
)
HISTORICAL_P5_P6_REVIEW_SHA256: Final = (
    "8cbd4b94b47d7f167fee5523f660244acb54adfe6a2826da46fa85c38e8ba762"
)
HISTORICAL_HARNESS_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1.py"
)
HISTORICAL_HARNESS_SHA256: Final = (
    "a8c5741b6385a5f9393679a77b2c55b9d8bfbfeb32351c3d3708b21d6f4ebd82"
)
HISTORICAL_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_successor_runtime_qualification_v1.py.tmpl"
)
HISTORICAL_TEMPLATE_SHA256: Final = (
    "fd67c6377835b097be3b9b68a6c8abe4685a391250dc532fcdfa393bcc04f672"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_requalification_design_v1.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_design_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_design_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-10-local-abc-exact-runtime-p5-p6-requalification-design-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Exact_Runtime_P5_P6_Requalification_Design_Certificate_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_exact_runtime_p5_p6_requalification_design_v1.md"
)

NEXT_GATE: Final = "implement_exact_runtime_p5_p6_requalification_v1"
PUBLIC_EVIDENCE_INVARIANT: Final = "PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION"

VLLM_SOURCE_TAG: Final = "v0.25.1"
VLLM_STATS_SOURCE: Final = "vllm/v1/metrics/stats.py"
VLLM_LOGGERS_SOURCE: Final = "vllm/v1/metrics/loggers.py"
VLLM_TOKENIZE_ROUTER_SOURCE: Final = "vllm/entrypoints/serve/tokenize/api_router.py"


class DesignError(RuntimeError):
    """Fail-closed exact-runtime P5/P6 design error."""

    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise DesignError("P5_P6_DESIGN_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BehaviorStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBIGUOUS = "AMBIGUOUS"


class ObservationState(StrEnum):
    NOT_EXPOSED = "NOT_EXPOSED"
    NOT_OBSERVED = "NOT_OBSERVED"
    ZERO = "ZERO"
    POSITIVE = "POSITIVE"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"


class FailureCode(StrEnum):
    INPUT_IDENTITY_FAILURE = "INPUT_IDENTITY_FAILURE"
    MODEL_ARTIFACT_FAILURE = "MODEL_ARTIFACT_FAILURE"
    TOKENIZER_ARTIFACT_FAILURE = "TOKENIZER_ARTIFACT_FAILURE"
    MODEL_CONSTRUCTION_FAILURE = "MODEL_CONSTRUCTION_FAILURE"
    WORKER_STARTUP_FAILURE = "WORKER_STARTUP_FAILURE"
    WORKER_IDENTITY_FAILURE = "WORKER_IDENTITY_FAILURE"
    DEVICE_REALIZATION_FAILURE = "DEVICE_REALIZATION_FAILURE"
    REQUEST_EXECUTION_FAILURE = "REQUEST_EXECUTION_FAILURE"
    OUTPUT_CONTRACT_FAILURE = "OUTPUT_CONTRACT_FAILURE"
    P5_CACHE_ENABLEMENT_FAILURE = "P5_CACHE_ENABLEMENT_FAILURE"
    P5_STARTING_STATE_FAILURE = "P5_STARTING_STATE_FAILURE"
    P5_CACHE_OBSERVATION_FAILURE = "P5_CACHE_OBSERVATION_FAILURE"
    P5_BEHAVIOR_FAILURE = "P5_BEHAVIOR_FAILURE"
    P6_ROUTE_REALIZATION_FAILURE = "P6_ROUTE_REALIZATION_FAILURE"
    P6_WORKER_GENERATION_FAILURE = "P6_WORKER_GENERATION_FAILURE"
    P6_STATE_ISOLATION_FAILURE = "P6_STATE_ISOLATION_FAILURE"
    P6_BEHAVIOR_FAILURE = "P6_BEHAVIOR_FAILURE"
    METRIC_SEMANTIC_FAILURE = "METRIC_SEMANTIC_FAILURE"
    METRIC_ATTRIBUTION_AMBIGUOUS = "METRIC_ATTRIBUTION_AMBIGUOUS"
    REQUEST_RECONCILIATION_FAILURE = "REQUEST_RECONCILIATION_FAILURE"
    TEARDOWN_FAILURE = "TEARDOWN_FAILURE"
    HARNESS_SEMANTIC_FAILURE = "HARNESS_SEMANTIC_FAILURE"
    EVIDENCE_PROJECTION_FAILURE = "EVIDENCE_PROJECTION_FAILURE"
    AUTHORITY_FAILURE = "AUTHORITY_FAILURE"
    NON_DETERMINISTIC_FAILURE = "NON_DETERMINISTIC_FAILURE"
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class AuthorityReceipt(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_scope: Literal["CURRENT", "DESIGN_PRECEDENT_ONLY"]


class RuntimeIdentity(FrozenModel):
    python: Literal["3.12"]
    cuda_variant: Literal["cu129"]
    torch_cuda_version: Literal["12.9"]
    torch: Literal["2.11.0+cu129"]
    vllm_distribution: Literal["0.25.1+cu129"]
    vllm_public_semantic_version: Literal["0.25.1"]
    gpu_topology: Literal["T4_x2"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_directory_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]


class MetricSemantic(FrozenModel):
    semantic_role: str = Field(min_length=1)
    prometheus_sample: str = Field(min_length=1)
    required_labels: tuple[str, ...]
    interpretation: str = Field(min_length=20)
    primary_for_p5: bool


class ExactRuntimeSemantics(FrozenModel):
    source_tag: Literal["v0.25.1"]
    stats_source: Literal["vllm/v1/metrics/stats.py"]
    loggers_source: Literal["vllm/v1/metrics/loggers.py"]
    tokenize_router_source: Literal["vllm/entrypoints/serve/tokenize/api_router.py"]
    prompt_source_labels: tuple[
        Literal["local_compute"],
        Literal["local_cache_hit"],
        Literal["external_kv_transfer"],
    ]
    prompt_source_invariant: Literal[
        "local_compute + local_cache_hit + external_kv_transfer = total_prompt_tokens"
    ]
    cached_source_invariant: Literal[
        "local_cache_hit + external_kv_transfer = cached_prompt_tokens"
    ]
    tokenize_endpoint: Literal["/tokenize"]
    metrics: tuple[MetricSemantic, ...]

    @model_validator(mode="after")
    def require_exact_metric_roles(self) -> Self:
        roles = {item.semantic_role for item in self.metrics}
        required = {
            "prefix_cache_queries",
            "prefix_cache_hits",
            "local_compute",
            "local_cache_hit",
            "external_kv_transfer",
            "cached_prompt_tokens",
            "newly_computed_prefill_tokens",
        }
        if roles != required:
            raise ValueError("exact-runtime metric semantic roles drifted")
        return self


class RequestPlanItem(FrozenModel):
    ordinal: int = Field(ge=1, le=6)
    role: Literal[
        "BASE_COLD",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    ]
    worker_id: Literal["worker_1", "worker_2"]
    worker_generation: int = Field(ge=1, le=2)
    prefix_variant: Literal["A", "B"]
    purpose: str = Field(min_length=20)


class ExecutionBudget(FrozenModel):
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    hidden_retries_permitted: Literal[0] = 0
    replacement_workers_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class TokenIdentityContract(FrozenModel):
    server_tokenize_endpoint_required: Literal[True] = True
    tokenizer_revision_fixed: Literal[True] = True
    reusable_prefix_token_ids_required: Literal[True] = True
    reusable_prefix_token_count_required: Literal[True] = True
    reusable_prefix_token_sha256_required: Literal[True] = True
    common_prefix_token_count_required: Literal[True] = True
    cache_block_size_required: Literal[True] = True
    cacheable_common_prefix_bound_required: Literal[True] = True
    b_c_reusable_prefix_token_identity_equal: Literal[True] = True
    string_hash_alone_sufficient: Literal[False] = False


class P5Contract(FrozenModel):
    capability: Literal[
        "prove attributable repeatable local prefix-cache reuse on the accepted exact runtime"
    ]
    positive_control: Literal["same worker generation + identical reusable token prefix"]
    negative_prefix_control: Literal["same worker generation + deliberately changed token prefix"]
    negative_worker_control: Literal[
        "independent worker generation + identical reusable token prefix"
    ]
    reset_control: Literal["full process restart + new worker generation"]
    latency_as_primary_proof_permitted: Literal[False] = False
    external_kv_transfer_permitted: Literal[False] = False
    pass_criteria: tuple[str, ...]
    fail_criteria: tuple[str, ...]
    ambiguous_criteria: tuple[str, ...]


class P6Contract(FrozenModel):
    capability: Literal["prove attributable worker routing and local reusable-state isolation"]
    required_identity_dimensions: tuple[str, ...]
    fallback_permitted: Literal[False] = False
    hidden_restart_permitted: Literal[False] = False
    model_semantics_as_route_proof_permitted: Literal[False] = False
    pass_criteria: tuple[str, ...]
    fail_criteria: tuple[str, ...]
    ambiguous_criteria: tuple[str, ...]


class SemanticBoundaryContract(FrozenModel):
    raw_observation_type: Literal["RawRuntimeObservation"]
    typed_observation_type: Literal["TypedSemanticObservation"]
    decision_type: Literal["BehaviorDecision"]
    evidence_projection_type: Literal["EvidenceProjection"]
    public_evidence_invariant: Literal["PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION"]
    raw_streams_persisted: Literal[False] = False
    public_evidence_used_as_semantic_input: Literal[False] = False
    lossy_transformations_before_semantic_decision: Literal[0] = 0
    truncation_before_semantic_decision: Literal[0] = 0
    evidence_projection_terminal: Literal[True] = True
    evidence_format_metamorphic_invariance_required: Literal[True] = True
    excerpt_length_metamorphic_invariance_required: Literal[True] = True


class DesignSafety(FrozenModel):
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_present: Literal[False] = False
    external_spend: Literal[0] = 0


class DesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p5-p6-exact-runtime-requalification-design-v1"]
    design_status: Literal["DESIGN_FROZEN_NOT_IMPLEMENTED"]
    base_main_commit: Literal["fa134894c29178d20ad0ff14b0aa921f257e692b"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(min_length=7, max_length=7)
    runtime: RuntimeIdentity
    exact_runtime_semantics: ExactRuntimeSemantics
    request_plan: tuple[RequestPlanItem, ...] = Field(min_length=6, max_length=6)
    execution_budget: ExecutionBudget
    token_identity: TokenIdentityContract
    p5: P5Contract
    p6: P6Contract
    semantic_boundary: SemanticBoundaryContract
    failure_taxonomy: tuple[FailureCode, ...]
    decision_states: tuple[BehaviorStatus, ...]
    observation_states: tuple[ObservationState, ...]
    safety: DesignSafety
    historical_p5_p6_current_authority: Literal[False] = False
    next_gate: Literal["implement_exact_runtime_p5_p6_requalification_v1"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_design_shape(self) -> Self:
        ordinals = tuple(item.ordinal for item in self.request_plan)
        if ordinals != (1, 2, 3, 4, 5, 6):
            raise ValueError("request plan ordinals must be exactly 1..6")
        if tuple(self.failure_taxonomy) != tuple(FailureCode):
            raise ValueError("failure taxonomy is incomplete or reordered")
        if tuple(self.decision_states) != tuple(BehaviorStatus):
            raise ValueError("decision states drifted")
        if tuple(self.observation_states) != tuple(ObservationState):
            raise ValueError("observation states drifted")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _read_exact_object(repo_root: Path, path: Path, expected_sha256: str) -> dict[str, object]:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "P5_P6_DESIGN_AUTHORITY_MISSING",
            "required design authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise DesignError(
            "P5_P6_DESIGN_AUTHORITY_DRIFT",
            "required design authority identity drifted",
            path.as_posix(),
        )
    observed: object = json.loads(payload)
    if not isinstance(observed, dict):
        raise DesignError(
            "P5_P6_DESIGN_AUTHORITY_INVALID",
            "required design authority root is not one object",
            path.as_posix(),
        )
    return cast(dict[str, object], observed)


def _read_exact_bytes(repo_root: Path, path: Path, expected_sha256: str) -> bytes:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "P5_P6_DESIGN_PRECEDENT_MISSING",
            "required historical design precedent is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    if _sha256_bytes(payload) != expected_sha256:
        raise DesignError(
            "P5_P6_DESIGN_PRECEDENT_DRIFT",
            "required historical design precedent identity drifted",
            path.as_posix(),
        )
    return payload


def _authority(
    role: str,
    path: Path,
    sha256: str,
    authority_scope: Literal["CURRENT", "DESIGN_PRECEDENT_ONLY"],
) -> AuthorityReceipt:
    return AuthorityReceipt(
        role=role,
        path=path.as_posix(),
        sha256=sha256,
        authority_scope=authority_scope,
    )


def validate_authorities(repo_root: Path) -> tuple[AuthorityReceipt, ...]:
    v5 = _read_exact_object(repo_root, V5_ACCEPTANCE_RECORD_PATH, V5_ACCEPTANCE_RECORD_SHA256)
    if (
        v5.get("governed_acceptance_status") != "ACCEPTED_EXACT_RUNTIME_OFFLINE_CAPABILITY_PASS"
        or v5.get("exact_runtime_offline_verified") is not True
        or v5.get("qualification_scope") != "CAPABILITY_ONLY"
        or v5.get("p5_p6_exact_runtime_requalified") is not False
        or v5.get("runtime_execution_authorized") is not False
        or v5.get("pilot_execution_authorized") is not False
        or v5.get("final_measured_abc_execution_authorized") is not False
        or v5.get("next_gate") != "design_exact_runtime_p5_p6_requalification_v1"
    ):
        raise DesignError(
            "P5_P6_DESIGN_V5_ACCEPTANCE_DRIFT",
            "V5 acceptance no longer supports the design gate",
            V5_ACCEPTANCE_RECORD_PATH.as_posix(),
        )

    lock = _read_exact_object(repo_root, RUNTIME_LOCK_PATH, RUNTIME_LOCK_SHA256)
    runtime_value = lock.get("runtime")
    if not isinstance(runtime_value, dict):
        raise DesignError(
            "P5_P6_DESIGN_RUNTIME_LINEAGE_DRIFT",
            "accepted exact runtime lineage is not one object",
            RUNTIME_LOCK_PATH.as_posix(),
        )
    runtime = cast(dict[str, object], runtime_value)
    if (
        runtime.get("python") != "3.12"
        or runtime.get("cuda_variant") != "cu129"
        or runtime.get("torch_cuda_version") != "12.9"
        or runtime.get("torch_version") != "2.11.0+cu129"
        or runtime.get("vllm_distribution_version") != "0.25.1+cu129"
    ):
        raise DesignError(
            "P5_P6_DESIGN_RUNTIME_LINEAGE_DRIFT",
            "accepted exact runtime lineage drifted",
            RUNTIME_LOCK_PATH.as_posix(),
        )

    semantic = _read_exact_object(
        repo_root,
        V5_SEMANTIC_BOUNDARY_PATH,
        V5_SEMANTIC_BOUNDARY_SHA256,
    )
    if (
        semantic.get("typed_semantic_observation_required") is not True
        or semantic.get("evidence_projection_terminal") is not True
        or semantic.get("semantic_decisions_reading_stdout_excerpt") != 0
        or semantic.get("semantic_decisions_reading_stderr_excerpt") != 0
        or semantic.get("lossy_transformations_before_semantic_decision") != 0
        or semantic.get("truncation_before_semantic_decision") != 0
    ):
        raise DesignError(
            "P5_P6_DESIGN_SEMANTIC_BOUNDARY_DRIFT",
            "accepted V5 semantic boundary drifted",
            V5_SEMANTIC_BOUNDARY_PATH.as_posix(),
        )

    historical = _read_exact_object(
        repo_root,
        HISTORICAL_P5_P6_ACCEPTANCE_PATH,
        HISTORICAL_P5_P6_ACCEPTANCE_SHA256,
    )
    historical_review = _read_exact_object(
        repo_root,
        HISTORICAL_P5_P6_REVIEW_PATH,
        HISTORICAL_P5_P6_REVIEW_SHA256,
    )
    if (
        historical.get("governed_acceptance_status") != "ACCEPTED_GOVERNED_EXECUTION_PASS"
        or historical.get("saved_version_id") != 340976295
        or historical.get("current_line_p5_pass_accepted") is not True
        or historical.get("current_line_p6_pass_accepted") is not True
        or historical_review.get("lifecycle_status") != "CONSUMED"
        or historical_review.get("lifecycle_outcome") != "PASSED"
        or historical_review.get("saved_version_id") != 340976295
    ):
        raise DesignError(
            "P5_P6_DESIGN_HISTORICAL_PRECEDENT_DRIFT",
            "historical governed P5/P6 precedent drifted",
            HISTORICAL_P5_P6_ACCEPTANCE_PATH.as_posix(),
        )

    _read_exact_bytes(repo_root, HISTORICAL_HARNESS_PATH, HISTORICAL_HARNESS_SHA256)
    _read_exact_bytes(repo_root, HISTORICAL_TEMPLATE_PATH, HISTORICAL_TEMPLATE_SHA256)

    return (
        _authority(
            "accepted_exact_runtime_capability",
            V5_ACCEPTANCE_RECORD_PATH,
            V5_ACCEPTANCE_RECORD_SHA256,
            "CURRENT",
        ),
        _authority(
            "accepted_exact_runtime_resolution",
            RUNTIME_LOCK_PATH,
            RUNTIME_LOCK_SHA256,
            "CURRENT",
        ),
        _authority(
            "accepted_semantic_boundary",
            V5_SEMANTIC_BOUNDARY_PATH,
            V5_SEMANTIC_BOUNDARY_SHA256,
            "CURRENT",
        ),
        _authority(
            "historical_governed_p5_p6_acceptance",
            HISTORICAL_P5_P6_ACCEPTANCE_PATH,
            HISTORICAL_P5_P6_ACCEPTANCE_SHA256,
            "DESIGN_PRECEDENT_ONLY",
        ),
        _authority(
            "historical_governed_p5_p6_review",
            HISTORICAL_P5_P6_REVIEW_PATH,
            HISTORICAL_P5_P6_REVIEW_SHA256,
            "DESIGN_PRECEDENT_ONLY",
        ),
        _authority(
            "historical_p5_p6_harness",
            HISTORICAL_HARNESS_PATH,
            HISTORICAL_HARNESS_SHA256,
            "DESIGN_PRECEDENT_ONLY",
        ),
        _authority(
            "historical_p5_p6_runtime_template",
            HISTORICAL_TEMPLATE_PATH,
            HISTORICAL_TEMPLATE_SHA256,
            "DESIGN_PRECEDENT_ONLY",
        ),
    )


def _runtime() -> RuntimeIdentity:
    return RuntimeIdentity(
        python="3.12",
        cuda_variant="cu129",
        torch_cuda_version="12.9",
        torch="2.11.0+cu129",
        vllm_distribution="0.25.1+cu129",
        vllm_public_semantic_version="0.25.1",
        gpu_topology="T4_x2",
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        tokenizer_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        model_directory_sha256=("84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"),
    )


def _exact_runtime_semantics() -> ExactRuntimeSemantics:
    common_labels = ("model_name", "engine")
    return ExactRuntimeSemantics(
        source_tag=VLLM_SOURCE_TAG,
        stats_source=VLLM_STATS_SOURCE,
        loggers_source=VLLM_LOGGERS_SOURCE,
        tokenize_router_source=VLLM_TOKENIZE_ROUTER_SOURCE,
        prompt_source_labels=("local_compute", "local_cache_hit", "external_kv_transfer"),
        prompt_source_invariant=(
            "local_compute + local_cache_hit + external_kv_transfer = total_prompt_tokens"
        ),
        cached_source_invariant=("local_cache_hit + external_kv_transfer = cached_prompt_tokens"),
        tokenize_endpoint="/tokenize",
        metrics=(
            MetricSemantic(
                semantic_role="prefix_cache_queries",
                prometheus_sample="vllm:prefix_cache_queries_total",
                required_labels=common_labels,
                interpretation="Number of prompt tokens queried against the local prefix cache.",
                primary_for_p5=True,
            ),
            MetricSemantic(
                semantic_role="prefix_cache_hits",
                prometheus_sample="vllm:prefix_cache_hits_total",
                required_labels=common_labels,
                interpretation=(
                    "Number of queried prompt tokens satisfied by the local prefix cache."
                ),
                primary_for_p5=True,
            ),
            MetricSemantic(
                semantic_role="local_compute",
                prometheus_sample="vllm:prompt_tokens_by_source_total",
                required_labels=(*common_labels, "source=local_compute"),
                interpretation="Prompt tokens requiring local prefill computation.",
                primary_for_p5=True,
            ),
            MetricSemantic(
                semantic_role="local_cache_hit",
                prometheus_sample="vllm:prompt_tokens_by_source_total",
                required_labels=(*common_labels, "source=local_cache_hit"),
                interpretation="Prompt tokens sourced from the local prefix cache without compute.",
                primary_for_p5=True,
            ),
            MetricSemantic(
                semantic_role="external_kv_transfer",
                prometheus_sample="vllm:prompt_tokens_by_source_total",
                required_labels=(*common_labels, "source=external_kv_transfer"),
                interpretation=(
                    "Prompt tokens supplied by external KV transfer rather than local cache."
                ),
                primary_for_p5=True,
            ),
            MetricSemantic(
                semantic_role="cached_prompt_tokens",
                prometheus_sample="vllm:prompt_tokens_cached_total",
                required_labels=common_labels,
                interpretation=(
                    "Prompt tokens skipped during prefill from local or external cache sources."
                ),
                primary_for_p5=False,
            ),
            MetricSemantic(
                semantic_role="newly_computed_prefill_tokens",
                prometheus_sample="vllm:request_prefill_kv_computed_tokens_sum",
                required_labels=common_labels,
                interpretation=(
                    "Histogram sum of new KV tokens computed during prefill, "
                    "excluding cached tokens."
                ),
                primary_for_p5=True,
            ),
        ),
    )


def _request_plan() -> tuple[RequestPlanItem, ...]:
    return (
        RequestPlanItem(
            ordinal=1,
            role="BASE_COLD",
            worker_id="worker_1",
            worker_generation=1,
            prefix_variant="A",
            purpose=(
                "Qualify deterministic request/output behavior and establish a cold P5 baseline."
            ),
        ),
        RequestPlanItem(
            ordinal=2,
            role="BASE_WARM",
            worker_id="worker_1",
            worker_generation=1,
            prefix_variant="A",
            purpose=(
                "Positive P5 control for attributable same-worker identical-prefix cache reuse."
            ),
        ),
        RequestPlanItem(
            ordinal=3,
            role="NEGATIVE_PREFIX",
            worker_id="worker_1",
            worker_generation=1,
            prefix_variant="B",
            purpose="Negative-prefix P5 control bounded by the tokenized common cacheable prefix.",
        ),
        RequestPlanItem(
            ordinal=4,
            role="POST_RESET_COLD",
            worker_id="worker_1",
            worker_generation=2,
            prefix_variant="A",
            purpose=(
                "Reset control proving that a full process restart removes prior "
                "worker-local cache state."
            ),
        ),
        RequestPlanItem(
            ordinal=5,
            role="CROSS_WORKER_COLD",
            worker_id="worker_2",
            worker_generation=1,
            prefix_variant="A",
            purpose=(
                "Negative-worker control proving worker 2 does not inherit worker 1 "
                "local prefix state."
            ),
        ),
        RequestPlanItem(
            ordinal=6,
            role="WORKER1_RETENTION",
            worker_id="worker_1",
            worker_generation=2,
            prefix_variant="A",
            purpose=(
                "Same-worker retention control proving route realization and retained "
                "worker-local state."
            ),
        ),
    )


def _p5_contract() -> P5Contract:
    return P5Contract(
        capability=(
            "prove attributable repeatable local prefix-cache reuse on the accepted exact runtime"
        ),
        positive_control="same worker generation + identical reusable token prefix",
        negative_prefix_control="same worker generation + deliberately changed token prefix",
        negative_worker_control="independent worker generation + identical reusable token prefix",
        reset_control="full process restart + new worker generation",
        latency_as_primary_proof_permitted=False,
        external_kv_transfer_permitted=False,
        pass_criteria=(
            (
                "prefix caching is enabled and exact metric semantics are present "
                "without attribution ambiguity"
            ),
            "BASE_COLD has zero local-cache-hit tokens and positive local-compute tokens",
            (
                "BASE_WARM preserves reusable token identity and has positive "
                "local-cache-hit and prefix-cache-hit deltas"
            ),
            "BASE_WARM computes fewer prefill KV tokens than BASE_COLD",
            (
                "NEGATIVE_PREFIX reuse does not exceed the proven cacheable "
                "common-prefix bound and is lower than BASE_WARM reuse"
            ),
            (
                "POST_RESET_COLD proves a new worker generation with zero inherited "
                "local-cache-hit tokens"
            ),
            (
                "CROSS_WORKER_COLD has zero prohibited inherited local-cache-hit "
                "tokens on the independent worker"
            ),
            (
                "external KV transfer is zero for all P5 controls and no "
                "contradictory typed observation remains"
            ),
        ),
        fail_criteria=(
            "valid positive control produces no attributable local prefix-cache reuse",
            "cache reuse exceeds the token-identity bound under the negative-prefix control",
            "full-process reset retains prohibited worker-local prefix state",
            "independent worker inherits prohibited worker-local prefix state",
            (
                "token identity or starting-state contract is violated by "
                "trustworthy typed observations"
            ),
        ),
        ambiguous_criteria=(
            "required metric is not exposed or has unexpected relevant label cardinality",
            (
                "metric labels or counter deltas cannot be attributed to the "
                "intended worker and request window"
            ),
            (
                "tokenized reusable-prefix identity or cacheable common-prefix bound "
                "cannot be established"
            ),
            "worker generation or starting state cannot be established",
            "same observation admits warm-up, external-transfer, or unrelated-cache explanations",
        ),
    )


def _p6_contract() -> P6Contract:
    return P6Contract(
        capability="prove attributable worker routing and local reusable-state isolation",
        required_identity_dimensions=(
            "worker_id",
            "worker_generation",
            "root_pid",
            "process_start_identity",
            "process_tree",
            "listen_port",
            "gpu_index",
            "gpu_uuid_or_equivalent_device_identity",
            "served_model_identity",
            "intended_route",
            "realized_route",
            "request_id",
            "metric_endpoint_identity",
            "output_provenance",
        ),
        fallback_permitted=False,
        hidden_restart_permitted=False,
        model_semantics_as_route_proof_permitted=False,
        pass_criteria=(
            (
                "both workers and worker generations are independently identifiable "
                "with disjoint process trees and intended GPU realization"
            ),
            "each eligible request changes only the realized worker request-scoped metric window",
            "intended route equals realized route with no hidden fallback or restart",
            "CROSS_WORKER_COLD proves no prohibited worker-1 local prefix state on worker 2",
            "WORKER1_RETENTION proves retained state remains attributable to worker 1 generation 2",
            (
                "declared, attempted, completed, per-worker, and global request "
                "counts reconcile exactly"
            ),
            "outputs remain attributable to the intended worker and teardown succeeds",
        ),
        fail_criteria=(
            "worker identity or device realization cannot satisfy the frozen identity contract",
            "intended and realized routes differ or fallback is hidden",
            "worker generation changes without explicit tracked restart",
            "cross-worker local prefix state violates the isolation contract",
            "request/output provenance or request reconciliation fails",
            "governed teardown fails",
        ),
        ambiguous_criteria=(
            (
                "workers respond but process, device, route, or state ownership "
                "cannot be distinguished"
            ),
            "worker generation changes with insufficient evidence to classify restart behavior",
            "metrics move on more than one worker or cannot be attributed to one request window",
            "route layer reports success but runtime realization cannot be independently proved",
        ),
    )


def build_design_record(repo_root: Path) -> DesignRecord:
    authorities = validate_authorities(repo_root.resolve())
    return DesignRecord(
        record_id="auragateway-p5-p6-exact-runtime-requalification-design-v1",
        design_status="DESIGN_FROZEN_NOT_IMPLEMENTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=authorities,
        runtime=_runtime(),
        exact_runtime_semantics=_exact_runtime_semantics(),
        request_plan=_request_plan(),
        execution_budget=ExecutionBudget(),
        token_identity=TokenIdentityContract(),
        p5=_p5_contract(),
        p6=_p6_contract(),
        semantic_boundary=SemanticBoundaryContract(
            raw_observation_type="RawRuntimeObservation",
            typed_observation_type="TypedSemanticObservation",
            decision_type="BehaviorDecision",
            evidence_projection_type="EvidenceProjection",
            public_evidence_invariant=PUBLIC_EVIDENCE_INVARIANT,
        ),
        failure_taxonomy=tuple(FailureCode),
        decision_states=tuple(BehaviorStatus),
        observation_states=tuple(ObservationState),
        safety=DesignSafety(),
        historical_p5_p6_current_authority=False,
        next_gate=NEXT_GATE,
        non_claims=(
            (
                "No model/tokenizer construction has executed on the current exact "
                "runtime under this design."
            ),
            "No current exact-runtime worker startup has been qualified by this design.",
            "No current exact-runtime model request has been executed by this design.",
            "P5 prefix-cache behavior is not yet requalified on vLLM 0.25.1.",
            "P6 worker/state isolation is not yet requalified on vLLM 0.25.1.",
            "The historical vLLM 0.19.1 P5/P6 PASS is design precedent only.",
            "Variance pilot execution is not authorized.",
            "Final measured A/B/C execution is not authorized.",
            "Production readiness is not established.",
        ),
    )


def generate(repo_root: Path) -> DesignRecord:
    root = repo_root.resolve()
    record = build_design_record(root)
    target = root / RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_canonical_json_bytes(record.model_dump(mode="json")))
    return record


def validate_generated(repo_root: Path) -> DesignRecord:
    root = repo_root.resolve()
    expected = build_design_record(root)
    target = root / RECORD_PATH
    if not target.is_file() or target.is_symlink():
        raise DesignError(
            "P5_P6_DESIGN_RECORD_MISSING",
            "generated exact-runtime P5/P6 design record is missing or unsafe",
            RECORD_PATH.as_posix(),
        )
    expected_bytes = _canonical_json_bytes(expected.model_dump(mode="json"))
    if target.read_bytes() != expected_bytes:
        raise DesignError(
            "P5_P6_DESIGN_RECORD_DRIFT",
            "generated exact-runtime P5/P6 design record bytes drifted",
            RECORD_PATH.as_posix(),
        )
    observed = DesignRecord.model_validate_json(target.read_text(encoding="utf-8"))
    if observed != expected:
        raise DesignError(
            "P5_P6_DESIGN_RECORD_SEMANTIC_DRIFT",
            "generated exact-runtime P5/P6 design record semantics drifted",
            RECORD_PATH.as_posix(),
        )
    return observed


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
        elif arguments.command == "validate":
            record = validate_generated(repo_root)
        else:
            raise DesignError(
                "P5_P6_DESIGN_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )
        print(json.dumps(record.model_dump(mode="json"), sort_keys=True))
        return 0
    except DesignError as error:
        print(json.dumps(error.envelope(), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
