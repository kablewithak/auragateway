"""Freeze the B-vs-D marker-diversified differential design V1.

Design-only reliability infrastructure. No Kaggle/GPU/model/worker execution or
runtime authority is created here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "de5289686c23b00a9504b5301db12683144ad969"
NEXT_GATE: Final = (
    "IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
)

DISPOSITION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_disposition_v1.json"
)
DISPOSITION_RECORD_SHA256: Final = (
    "5bd88278f8d31b7d2f60304b330616b394d491b3a40ee8c7d381040d07a9bf9c"
)
DISPOSITION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_disposition_v1_review.json"
)
DISPOSITION_REVIEW_SHA256: Final = (
    "0df7901217570c10f4b2af28c4293dc48f01a6da1cdbf8d7be0af9c1f2cbb376"
)
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "p4_p5_token_count_matched_context_structure_differential_runtime_v1.py"
)
RUNTIME_SHA256: Final = "9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834"
PREDECESSOR_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_design_v1.json"
)
PREDECESSOR_DESIGN_SHA256: Final = (
    "888bf0a25a974ba2c62892bc999fe0c9f23d2cf845bcd2542c67e2c9bc4ccf03"
)

EVIDENCE_ROOT: Final = Path(
    "benchmarks/local_abc/evidence/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1"
)
FEASIBILITY_PATH: Final = EVIDENCE_ROOT / "comparator_feasibility_v2.json"
FEASIBILITY_SHA256: Final = "439ccaeb4d4a3a4818538e168d9ab00565ba69a67d7ebc6f587a970c9c26d316"
SEMANTIC_REVIEW_PATH: Final = EVIDENCE_ROOT / "semantic_review_candidate_v1.json"
SEMANTIC_REVIEW_SHA256: Final = "1cf74362d095ad6032a65351bb85695e066d9aa999d129b8a0c8364857a83687"
FREEZE_CANDIDATE_PATH: Final = EVIDENCE_ROOT / "design_freeze_candidate_v1.json"
FREEZE_CANDIDATE_SHA256: Final = "3a402c1b86e7e12ba8f91ea1c81d376686c8555b8b9632134a9fb4f4f3f0088f"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_design_v1.json"
)

B_TOKEN_SHA256: Final = "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
B_PAYLOAD_SHA256: Final = "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
D_TOKEN_SHA256: Final = "878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21"
D_PAYLOAD_SHA256: Final = "0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010"

B_SEGMENT: Final = (
    "AuraGateway synthetic context marker meadow. "
    "This passage contains neutral synthetic material, no customer data, "
    "and descriptive test context only. "
    "It provides descriptive context for controlled tokenizer analysis. "
)
SEGMENT_TEMPLATE: Final = (
    "AuraGateway synthetic context marker {marker}. "
    "This passage contains neutral synthetic material, no customer data, "
    "and descriptive test context only. "
    "It provides descriptive context for controlled tokenizer analysis. "
)
D_MARKERS: Final = (
    "birch",
    "grove",
    "juniper",
    "lagoon",
    "meadow",
    "prairie",
    "spruce",
    "umber",
    "willow",
    "acorn",
    "alder",
    "beech",
    "brook",
    "caper",
    "clover",
    "cove",
    "dune",
    "finch",
    "flint",
    "glade",
    "ivy",
    "larch",
    "lily",
    "orchid",
)
TOKEN_PROFILE: Final = tuple(range(83, 900, 34))
TOKEN_INCREMENTS: Final = (34,) * 24
ORDER: Final = (
    "B_NEUTRAL_REPEATED_24X",
    "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
    "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
    "B_NEUTRAL_REPEATED_24X",
    "B_NEUTRAL_REPEATED_24X",
    "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
)


class DesignError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
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
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityScope(StrEnum):
    CURRENT_CAUSAL = "CURRENT_CAUSAL"
    CURRENT_RUNTIME = "CURRENT_RUNTIME"
    BOUND_RUNTIME_CONTRACT = "BOUND_RUNTIME_CONTRACT"
    QUALIFIED_OFFLINE_EVIDENCE = "QUALIFIED_OFFLINE_EVIDENCE"


class ConditionId(StrEnum):
    B = "B_NEUTRAL_REPEATED_24X"
    D = "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED"


class DecisionState(StrEnum):
    MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK = (
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
    )
    MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL = (
        "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL"
    )
    D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM = "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"
    B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE = (
        "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
    )
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class AuthorityReceipt(FrozenModel):
    role: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: AuthorityScope


class RuntimeIdentity(FrozenModel):
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    backend: Literal["TRITON_ATTN"]
    vllm_distribution: Literal["0.25.1+cu129"]
    torch: Literal["2.11.0+cu129"]
    torch_cuda: Literal["12.9"]
    triton: Literal["3.6.0"]
    transformers: Literal["5.14.1"]
    platform_topology: Literal["T4_x2"]
    worker_gpu_index: Literal[0]
    prefix_caching_enabled: Literal[True]
    cache_block_size: Literal[16]
    max_model_len: Literal[4096]


class GenerationControls(FrozenModel):
    temperature: Literal[0]
    top_p: Literal[1]
    repetition_penalty: float
    seed: Literal[7]
    max_tokens: Literal[32]
    stream: Literal[False]
    response_format_present: Literal[False]
    output_mode: Literal["UNCONSTRAINED"]

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.repetition_penalty != 1.1:
            raise ValueError("repetition penalty drifted")
        return self


class FrozenComposition(FrozenModel):
    message_roles: tuple[str, ...]
    system_instruction: str
    cache_context_tail: str
    assistant_ack: str
    final_object_canonical: str
    prompt_token_count_per_condition: Literal[899]
    segment_count_per_condition: Literal[24]
    no_schema_or_guided_decoding: Literal[True]
    parser_semantics_preserved: Literal[True]


class RepresentationMetrics(FrozenModel):
    duplicate_16gram_fraction: float = Field(ge=0, le=1)
    shift_34_match_fraction: float = Field(ge=0, le=1)
    duplicate_aligned_16_token_blocks_beyond_first: int = Field(ge=0)
    prompt_unique_token_ids: int = Field(ge=1)


class ConditionDefinition(FrozenModel):
    condition_id: ConditionId
    role: Literal["FAILURE_ANCHOR", "INTERVENTION"]
    historical_exact_object_result: Literal["0_OF_3", "NOT_EXECUTED"]
    prompt_token_count: Literal[899]
    prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_count: Literal[24]
    unique_segment_count: Literal[1, 24]
    segment_template: str
    marker_sequence: tuple[str, ...] = Field(min_length=24, max_length=24)
    segments: tuple[str, ...] = Field(min_length=24, max_length=24)
    cumulative_prompt_token_count_profile: tuple[int, ...] = Field(
        min_length=25,
        max_length=25,
    )
    cumulative_prompt_token_increments: tuple[int, ...] = Field(
        min_length=24,
        max_length=24,
    )
    representation_metrics: RepresentationMetrics
    bounded_residual_difference: str | None

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.cumulative_prompt_token_count_profile != TOKEN_PROFILE:
            raise ValueError("cumulative token profile drifted")
        if self.cumulative_prompt_token_increments != TOKEN_INCREMENTS:
            raise ValueError("cumulative token increments drifted")
        if self.segment_template != SEGMENT_TEMPLATE:
            raise ValueError("segment template drifted")

        if self.condition_id == ConditionId.B:
            if self.role != "FAILURE_ANCHOR":
                raise ValueError("B role drifted")
            if self.historical_exact_object_result != "0_OF_3":
                raise ValueError("B historical anchor drifted")
            if self.prompt_token_sha256 != B_TOKEN_SHA256:
                raise ValueError("B token identity drifted")
            if self.request_payload_sha256 != B_PAYLOAD_SHA256:
                raise ValueError("B payload identity drifted")
            if self.marker_sequence != ("meadow",) * 24:
                raise ValueError("B marker sequence drifted")
            if self.segments != (B_SEGMENT,) * 24:
                raise ValueError("B segment sequence drifted")
            if self.unique_segment_count != 1:
                raise ValueError("B segment uniqueness drifted")
            if self.bounded_residual_difference is not None:
                raise ValueError("B residual difference must be absent")

        if self.condition_id == ConditionId.D:
            if self.role != "INTERVENTION":
                raise ValueError("D role drifted")
            if self.historical_exact_object_result != "NOT_EXECUTED":
                raise ValueError("D execution state drifted")
            if self.prompt_token_sha256 != D_TOKEN_SHA256:
                raise ValueError("D token identity drifted")
            if self.request_payload_sha256 != D_PAYLOAD_SHA256:
                raise ValueError("D payload identity drifted")
            if self.marker_sequence != D_MARKERS:
                raise ValueError("D marker sequence drifted")
            if self.segments != tuple(
                SEGMENT_TEMPLATE.format(marker=marker) for marker in D_MARKERS
            ):
                raise ValueError("D segment sequence drifted")
            if self.unique_segment_count != 24:
                raise ValueError("D segment uniqueness drifted")
            if not self.bounded_residual_difference:
                raise ValueError("D residual difference missing")

        return self


class HumanReview(FrozenModel):
    neutrality: Literal["PASS"]
    naturalness: Literal["PASS"]
    semantic_comparability_to_b: Literal["PASS"]
    marker_only_textual_change: Literal["PASS"]
    instruction_like_semantics_absent: Literal["PASS"]
    forbidden_terms_absent: Literal["PASS"]
    cumulative_prompt_token_profile_equal_to_b: Literal["PASS"]
    text_boundary_token_boundary_assumption: Literal["NOT_USED"]
    structural_isolation: Literal["PASS_WITH_BOUNDED_MARKER_LEXICAL_AND_SEMANTIC_NOVELTY"]


class ComparatorContract(FrozenModel):
    human_review: HumanReview
    b_metrics: RepresentationMetrics
    d_metrics: RepresentationMetrics
    cumulative_prompt_token_profile_equal: Literal[True]
    marker_only_textual_change: Literal[True]
    text_segment_boundary_must_equal_token_boundary: Literal[False]
    bounded_residual_difference: str

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.d_metrics.duplicate_16gram_fraction >= (self.b_metrics.duplicate_16gram_fraction):
            raise ValueError("D 16-gram reduction drifted")
        if self.d_metrics.shift_34_match_fraction >= (self.b_metrics.shift_34_match_fraction):
            raise ValueError("D periodicity reduction drifted")
        if self.d_metrics.duplicate_aligned_16_token_blocks_beyond_first >= (
            self.b_metrics.duplicate_aligned_16_token_blocks_beyond_first
        ):
            raise ValueError("D aligned-block reduction drifted")
        if self.d_metrics.prompt_unique_token_ids <= (self.b_metrics.prompt_unique_token_ids):
            raise ValueError("D lexical diversification drifted")
        return self


class StartingStateContract(FrozenModel):
    strategy: Literal["FRESH_WORKER_PROCESS_PER_OBSERVATION"]
    prior_request_cache_carryover_permitted: Literal[False]
    require_fresh_worker_identity: Literal[True]
    require_zero_cached_prefix_baseline: Literal[True]
    teardown_required_between_observations: Literal[True]
    teardown_failure_invalidates_diagnostic: Literal[True]


class RequestPlanItem(FrozenModel):
    ordinal: int = Field(ge=1, le=6)
    condition_id: ConditionId


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[6] = 6
    maximum_worker_starts: Literal[6] = 6
    maximum_model_requests: Literal[6] = 6
    maximum_output_tokens_per_request: Literal[32] = 32
    hidden_retries_permitted: Literal[0] = 0
    replacement_observations_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class PrimaryEndpoint(FrozenModel):
    field: Literal["exact_object"]
    per_condition_observations: Literal[3]
    condition_pass: Literal["3_OF_3_EXACT_OBJECT_TRUE"]
    condition_fail: Literal["0_OF_3_EXACT_OBJECT_TRUE"]
    condition_mixed: Literal["1_OR_2_OF_3_EXACT_OBJECT_TRUE"]


class DecisionRule(FrozenModel):
    state: DecisionState
    condition: str
    implication: str


class Safety(FrozenModel):
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    execution_authorization_issued: Literal[False] = False
    threshold_search_authorized: Literal[False] = False
    p5_p6_requalification_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False


class DesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-design-v1"
    ]
    design_status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["de5289686c23b00a9504b5301db12683144ad969"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(
        min_length=7,
        max_length=7,
    )
    runtime: RuntimeIdentity
    generation_controls: GenerationControls
    frozen_composition: FrozenComposition
    conditions: tuple[ConditionDefinition, ConditionDefinition]
    comparator_contract: ComparatorContract
    starting_state: StartingStateContract
    request_plan: tuple[RequestPlanItem, ...] = Field(
        min_length=6,
        max_length=6,
    )
    execution_budget: ExecutionBudget
    primary_endpoint: PrimaryEndpoint
    secondary_observations: tuple[str, ...] = Field(min_length=10)
    decision_rules: tuple[DecisionRule, ...] = Field(
        min_length=5,
        max_length=5,
    )
    safety: Safety
    next_gate: Literal[
        "IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=9)

    @model_validator(mode="after")
    def exact(self) -> Self:
        if tuple(item.condition_id for item in self.conditions) != (
            ConditionId.B,
            ConditionId.D,
        ):
            raise ValueError("condition order drifted")

        observed_order = tuple(item.condition_id.value for item in self.request_plan)
        if observed_order != ORDER:
            raise ValueError("request order drifted")

        b_positions = tuple(
            item.ordinal for item in self.request_plan if item.condition_id == ConditionId.B
        )
        d_positions = tuple(
            item.ordinal for item in self.request_plan if item.condition_id == ConditionId.D
        )
        if b_positions != (1, 4, 5):
            raise ValueError("B request positions drifted")
        if d_positions != (2, 3, 6):
            raise ValueError("D request positions drifted")

        if tuple(rule.state for rule in self.decision_rules) != tuple(DecisionState):
            raise ValueError("decision rule order drifted")

        return self


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _file(root: Path, path: Path) -> Path:
    absolute = root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_MISSING",
            "required design authority is missing or unsafe",
            path.as_posix(),
        )
    return absolute


def _bytes(
    root: Path,
    path: Path,
    expected: str | None = None,
) -> bytes:
    data = _file(root, path).read_bytes()
    if expected is not None and _sha(data) != expected:
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_DRIFT",
            "required design authority identity drifted",
            path.as_posix(),
        )
    return data


def _object(
    root: Path,
    path: Path,
    expected: str | None = None,
) -> dict[str, object]:
    try:
        value: object = json.loads(_bytes(root, path, expected))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_INVALID",
            "required authority is not valid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_INVALID",
            "required authority root is not an object",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_INVALID",
            f"{name} is not an object",
        )
    return cast(dict[str, object], value)


def _sequence(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_INVALID",
            f"{name} is not an array",
        )
    return cast(list[object], value)


def _base_commit_is_ancestor_of_head(root: Path) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise DesignError(
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_GIT_STATE_INVALID",
        "unable to verify frozen design base ancestry",
    )


def _require(
    mapping: dict[str, object],
    expected: dict[str, object],
    error_code: str,
    safe_message: str,
) -> None:
    for key, value in expected.items():
        if mapping.get(key) != value:
            raise DesignError(
                error_code,
                safe_message,
                key,
            )


def _validate_semantics(root: Path) -> None:
    if not _base_commit_is_ancestor_of_head(root):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_BASE_MAIN_DRIFT",
            "frozen design base is not an ancestor of current HEAD",
        )

    disposition = _object(
        root,
        DISPOSITION_RECORD_PATH,
        DISPOSITION_RECORD_SHA256,
    )
    _require(
        disposition,
        {
            "status": "DISPOSITIONED_VALID_GOVERNED_TOKEN_MATCHED_DIFFERENTIAL",
            "decision_state": "HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED",
            "condition_a_exact_object_count": 0,
            "condition_b_exact_object_count": 0,
            "condition_c_exact_object_count": 3,
            "observations_per_condition": 3,
            "prompt_token_count_per_condition": 899,
            "high_exact_token_pattern_repetition_strongly_implicated": True,
            "exact_repetition_sole_cause_established": False,
            "exact_repetition_threshold_established": False,
            "exact_root_cause_established": False,
            "prefix_cache_defect_established": False,
            "p5_requalified": False,
            "p6_requalified": False,
            "measured_abc_execution_performed": False,
            "authorization_reusable": False,
            "new_execution_authorized": False,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_DISPOSITION_DRIFT",
        "accepted token-matched disposition drifted",
    )

    review = _object(
        root,
        DISPOSITION_REVIEW_PATH,
        DISPOSITION_REVIEW_SHA256,
    )
    _require(
        review,
        {
            "status": "APPROVED_GOVERNED_TOKEN_MATCHED_DIFFERENTIAL_DISPOSITION",
            "high_exact_token_pattern_repetition_result_accepted": True,
            "exact_repetition_sole_cause_claimed": False,
            "exact_root_cause_claimed": False,
            "exact_threshold_claimed": False,
            "p5_requalification_claimed": False,
            "p6_requalification_claimed": False,
            "measured_abc_claimed": False,
            "new_execution_authorized": False,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_DISPOSITION_REVIEW_DRIFT",
        "accepted disposition review drifted",
    )

    _bytes(root, RUNTIME_PATH, RUNTIME_SHA256)

    predecessor = _object(
        root,
        PREDECESSOR_DESIGN_PATH,
        PREDECESSOR_DESIGN_SHA256,
    )
    _require(
        predecessor,
        {
            "design_status": "DESIGN_FROZEN_NOT_EXECUTED",
            "next_gate": (
                "IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"
            ),
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_PREDECESSOR_DRIFT",
        "predecessor design contract drifted",
    )

    runtime = _mapping(predecessor.get("runtime"), "predecessor runtime")
    _require(
        runtime,
        {
            "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
            "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "tokenizer_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "backend": "TRITON_ATTN",
            "vllm_distribution": "0.25.1+cu129",
            "transformers": "5.14.1",
            "prefix_caching_enabled": True,
            "cache_block_size": 16,
            "max_model_len": 4096,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_RUNTIME_CONTRACT_DRIFT",
        "bound runtime contract drifted",
    )

    feasibility = _object(
        root,
        FEASIBILITY_PATH,
        FEASIBILITY_SHA256,
    )
    _require(
        feasibility,
        {
            "status": "FEASIBILITY_PASS",
            "candidate_condition": ("D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED"),
            "human_review_required": True,
            "model_loaded": False,
            "model_request_executed": False,
            "worker_started": False,
            "gpu_execution_performed": False,
            "kaggle_execution_performed": False,
            "new_execution_authorized": False,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FEASIBILITY_DRIFT",
        "qualified comparator feasibility drifted",
    )
    acceptance = _mapping(
        feasibility.get("acceptance"),
        "feasibility acceptance",
    )
    required_acceptance = (
        "b_token_identity_reproduced",
        "c_token_identity_reproduced",
        "candidate_prompt_token_count_899",
        "segment_count_24",
        "unique_marker_count_24",
        "unique_segment_count_24",
        "same_b_sentence_template_marker_only",
        "cumulative_prompt_token_count_profile_equals_b",
        "cumulative_prompt_token_increments_equal_b",
        "duplicate_16gram_reduced_relative_to_b",
        "aligned_block_duplication_reduced_relative_to_b",
        "shift_34_periodicity_reduced_relative_to_b",
        "lexical_novelty_greater_than_b",
        "lexical_novelty_less_than_c",
        "all_forbidden_terms_zero",
    )
    for key in required_acceptance:
        if acceptance.get(key) is not True:
            raise DesignError(
                "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FEASIBILITY_DRIFT",
                "qualified comparator acceptance drifted",
                key,
            )

    candidate = _mapping(
        feasibility.get("candidate"),
        "feasibility candidate",
    )
    candidate_metrics = _mapping(
        candidate.get("metrics"),
        "candidate metrics",
    )
    _require(
        candidate_metrics,
        {
            "prompt_token_count": 899,
            "prompt_token_sha256": D_TOKEN_SHA256,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FEASIBILITY_DRIFT",
        "candidate token identity drifted",
    )
    if candidate.get("request_payload_sha256") != D_PAYLOAD_SHA256:
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FEASIBILITY_DRIFT",
            "candidate payload identity drifted",
            "request_payload_sha256",
        )
    if tuple(_sequence(feasibility.get("selected_markers"), "selected markers")) != (D_MARKERS):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FEASIBILITY_DRIFT",
            "selected marker sequence drifted",
        )
    if (
        tuple(
            _sequence(
                candidate.get("cumulative_prompt_token_count_profile"),
                "candidate cumulative token profile",
            )
        )
        != TOKEN_PROFILE
    ):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FEASIBILITY_DRIFT",
            "candidate cumulative token profile drifted",
        )

    semantic_review = _object(
        root,
        SEMANTIC_REVIEW_PATH,
        SEMANTIC_REVIEW_SHA256,
    )
    _require(
        semantic_review,
        {
            "status": "SEMANTIC_REVIEW_CANDIDATE_AWAITING_USER_ACCEPTANCE",
            "source_feasibility_json_sha256": FEASIBILITY_SHA256,
            "proposed_review_outcome": "APPROVE_FOR_DESIGN_FREEZE",
            "user_acceptance_required": True,
            "new_execution_authorized": False,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_SEMANTIC_REVIEW_DRIFT",
        "human semantic review drifted",
    )
    rubric = _mapping(semantic_review.get("rubric"), "semantic review rubric")
    _require(
        rubric,
        {
            "neutrality": "PASS",
            "naturalness": "PASS",
            "semantic_comparability_to_b": "PASS",
            "marker_only_textual_change": "PASS",
            "instruction_like_semantics_absent": "PASS",
            "forbidden_terms_absent": "PASS",
            "cumulative_prompt_token_profile_equal_to_b": "PASS",
            "text_boundary_token_boundary_assumption": "NOT_USED",
            "structural_isolation": ("PASS_WITH_BOUNDED_MARKER_LEXICAL_AND_SEMANTIC_NOVELTY"),
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_SEMANTIC_REVIEW_DRIFT",
        "human semantic review rubric drifted",
    )

    freeze = _object(
        root,
        FREEZE_CANDIDATE_PATH,
        FREEZE_CANDIDATE_SHA256,
    )
    _require(
        freeze,
        {
            "design_state": "FREEZE_CANDIDATE_USER_APPROVED",
            "source_main_commit": BASE_MAIN_COMMIT,
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FREEZE_DRIFT",
        "user-approved freeze candidate drifted",
    )
    source_evidence = _mapping(
        freeze.get("source_evidence"),
        "freeze source evidence",
    )
    user_acceptance = _mapping(
        source_evidence.get("user_acceptance"),
        "freeze user acceptance",
    )
    _require(
        user_acceptance,
        {
            "accepted_for_design_freeze": True,
            "scope": "CURRENT_REVIEWED_B_VS_D_COMPARATOR_ONLY",
        },
        "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FREEZE_DRIFT",
        "user acceptance binding drifted",
    )
    authorization = _mapping(
        freeze.get("authorization"),
        "freeze authorization",
    )
    for key in (
        "runtime_execution_authorized",
        "gpu_execution_authorized",
        "kaggle_execution_authorized",
        "model_loaded",
        "worker_started",
        "model_request_executed",
        "new_execution_authorized",
    ):
        if authorization.get(key) is not False:
            raise DesignError(
                "B_VS_D_MARKER_DIVERSIFIED_DESIGN_FREEZE_DRIFT",
                "freeze authorization boundary drifted",
                key,
            )


def validate_authorities(root: Path) -> tuple[AuthorityReceipt, ...]:
    _validate_semantics(root)
    return (
        AuthorityReceipt(
            role="governed_token_matched_disposition",
            path=DISPOSITION_RECORD_PATH.as_posix(),
            sha256=DISPOSITION_RECORD_SHA256,
            scope=AuthorityScope.CURRENT_CAUSAL,
        ),
        AuthorityReceipt(
            role="governed_token_matched_disposition_review",
            path=DISPOSITION_REVIEW_PATH.as_posix(),
            sha256=DISPOSITION_REVIEW_SHA256,
            scope=AuthorityScope.CURRENT_CAUSAL,
        ),
        AuthorityReceipt(
            role="bound_token_matched_runtime",
            path=RUNTIME_PATH.as_posix(),
            sha256=RUNTIME_SHA256,
            scope=AuthorityScope.CURRENT_RUNTIME,
        ),
        AuthorityReceipt(
            role="predecessor_runtime_and_composition_contract",
            path=PREDECESSOR_DESIGN_PATH.as_posix(),
            sha256=PREDECESSOR_DESIGN_SHA256,
            scope=AuthorityScope.BOUND_RUNTIME_CONTRACT,
        ),
        AuthorityReceipt(
            role="marker_diversified_comparator_feasibility",
            path=FEASIBILITY_PATH.as_posix(),
            sha256=FEASIBILITY_SHA256,
            scope=AuthorityScope.QUALIFIED_OFFLINE_EVIDENCE,
        ),
        AuthorityReceipt(
            role="marker_diversified_human_semantic_review",
            path=SEMANTIC_REVIEW_PATH.as_posix(),
            sha256=SEMANTIC_REVIEW_SHA256,
            scope=AuthorityScope.QUALIFIED_OFFLINE_EVIDENCE,
        ),
        AuthorityReceipt(
            role="user_approved_design_freeze_candidate",
            path=FREEZE_CANDIDATE_PATH.as_posix(),
            sha256=FREEZE_CANDIDATE_SHA256,
            scope=AuthorityScope.QUALIFIED_OFFLINE_EVIDENCE,
        ),
    )


def _float_field(
    source: dict[str, object],
    key: str,
) -> float:
    value = source.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_INVALID",
            "required representation metric is not numeric",
            key,
        )
    return float(value)


def _int_field(
    source: dict[str, object],
    key: str,
) -> int:
    value = source.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_AUTHORITY_INVALID",
            "required representation metric is not an integer",
            key,
        )
    return value


def _representation_metrics(
    source: dict[str, object],
) -> RepresentationMetrics:
    return RepresentationMetrics(
        duplicate_16gram_fraction=_float_field(
            source,
            "duplicate_16gram_fraction",
        ),
        shift_34_match_fraction=_float_field(
            source,
            "shift_34_match_fraction",
        ),
        duplicate_aligned_16_token_blocks_beyond_first=_int_field(
            source,
            "duplicate_aligned_16_token_blocks_beyond_first",
        ),
        prompt_unique_token_ids=_int_field(
            source,
            "prompt_unique_token_ids",
        ),
    )


def build_design_record(root: Path) -> DesignRecord:
    authorities = validate_authorities(root)

    predecessor = _object(
        root,
        PREDECESSOR_DESIGN_PATH,
        PREDECESSOR_DESIGN_SHA256,
    )
    feasibility = _object(
        root,
        FEASIBILITY_PATH,
        FEASIBILITY_SHA256,
    )

    runtime = RuntimeIdentity.model_validate(
        _mapping(predecessor.get("runtime"), "predecessor runtime")
    )
    generation_controls = GenerationControls.model_validate(
        _mapping(
            predecessor.get("generation_controls"),
            "predecessor generation controls",
        )
    )
    frozen_composition = FrozenComposition.model_validate(
        _mapping(
            predecessor.get("frozen_composition"),
            "predecessor frozen composition",
        )
    )
    starting_state = StartingStateContract.model_validate(
        _mapping(
            predecessor.get("starting_state"),
            "predecessor starting state",
        )
    )

    baseline = _mapping(feasibility.get("baseline_b"), "baseline B")
    baseline_metrics = _mapping(
        baseline.get("metrics"),
        "baseline B metrics",
    )
    candidate = _mapping(feasibility.get("candidate"), "candidate D")
    candidate_metrics = _mapping(
        candidate.get("metrics"),
        "candidate D metrics",
    )
    semantic_review = _object(
        root,
        SEMANTIC_REVIEW_PATH,
        SEMANTIC_REVIEW_SHA256,
    )
    human_review = HumanReview.model_validate(
        _mapping(semantic_review.get("rubric"), "semantic review rubric")
    )

    b = ConditionDefinition(
        condition_id=ConditionId.B,
        role="FAILURE_ANCHOR",
        historical_exact_object_result="0_OF_3",
        prompt_token_count=899,
        prompt_token_sha256=B_TOKEN_SHA256,
        request_payload_sha256=B_PAYLOAD_SHA256,
        segment_count=24,
        unique_segment_count=1,
        segment_template=SEGMENT_TEMPLATE,
        marker_sequence=("meadow",) * 24,
        segments=(B_SEGMENT,) * 24,
        cumulative_prompt_token_count_profile=TOKEN_PROFILE,
        cumulative_prompt_token_increments=TOKEN_INCREMENTS,
        representation_metrics=_representation_metrics(baseline_metrics),
        bounded_residual_difference=None,
    )

    d_segments = tuple(SEGMENT_TEMPLATE.format(marker=marker) for marker in D_MARKERS)
    d = ConditionDefinition(
        condition_id=ConditionId.D,
        role="INTERVENTION",
        historical_exact_object_result="NOT_EXECUTED",
        prompt_token_count=899,
        prompt_token_sha256=D_TOKEN_SHA256,
        request_payload_sha256=D_PAYLOAD_SHA256,
        segment_count=24,
        unique_segment_count=24,
        segment_template=SEGMENT_TEMPLATE,
        marker_sequence=D_MARKERS,
        segments=d_segments,
        cumulative_prompt_token_count_profile=TOKEN_PROFILE,
        cumulative_prompt_token_increments=TOKEN_INCREMENTS,
        representation_metrics=_representation_metrics(candidate_metrics),
        bounded_residual_difference=(
            "Marker lexical and semantic novelty necessarily increase. "
            "Exact n-gram repetition, 34-token periodicity, and aligned "
            "16-token block duplication move together and are not "
            "individually isolated."
        ),
    )

    comparator_contract = ComparatorContract(
        human_review=human_review,
        b_metrics=b.representation_metrics,
        d_metrics=d.representation_metrics,
        cumulative_prompt_token_profile_equal=True,
        marker_only_textual_change=True,
        text_segment_boundary_must_equal_token_boundary=False,
        bounded_residual_difference=(
            "Marker lexical/semantic novelty remains bounded rather than "
            "eliminated. Exact n-gram repetition, 34-token periodicity, "
            "and aligned 16-token block duplication move together."
        ),
    )

    request_plan = tuple(
        RequestPlanItem(
            ordinal=ordinal,
            condition_id=ConditionId(condition_id),
        )
        for ordinal, condition_id in enumerate(ORDER, start=1)
    )

    decision_rules = (
        DecisionRule(
            state=DecisionState.MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK,
            condition="B is 0/3 exact-object and D is 3/3 exact-object.",
            implication=(
                "Marker-only diversification restores the endpoint while "
                "the complete B cumulative prompt-token trajectory remains "
                "fixed. A repetition-sensitive representation mechanism is "
                "strengthened, but n-gram repetition, block recurrence, and "
                "marker novelty are not individually isolated."
            ),
        ),
        DecisionRule(
            state=DecisionState.MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL,
            condition="B is 0/3 exact-object and D is 0/3 exact-object.",
            implication=(
                "The reviewed marker-only diversification is insufficient "
                "at D's repetition level. A stronger diversification or "
                "threshold-like effect remains live without establishing "
                "an exact threshold."
            ),
        ),
        DecisionRule(
            state=DecisionState.D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM,
            condition="B is 0/3 exact-object and D is 1/3 or 2/3 exact-object.",
            implication=(
                "The intervention is behaviorally unstable and receives no mechanistic claim."
            ),
        ),
        DecisionRule(
            state=DecisionState.B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE,
            condition="Condition B is not 0/3 exact-object.",
            implication=(
                "The governed B failure anchor did not reproduce; D is not "
                "used for mechanistic inference."
            ),
        ),
        DecisionRule(
            state=DecisionState.DIAGNOSTIC_INVALID,
            condition=(
                "Any runtime identity, token identity, payload identity, "
                "budget, starting-state, teardown, cleanup, or evidence "
                "invariant fails."
            ),
            implication=("The diagnostic is invalid and supports no mechanistic claim."),
        ),
    )

    secondary = tuple(
        cast(
            list[str],
            predecessor.get("secondary_observations"),
        )
    )

    return DesignRecord(
        record_id=(
            "auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-design-v1"
        ),
        design_status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=authorities,
        runtime=runtime,
        generation_controls=generation_controls,
        frozen_composition=frozen_composition,
        conditions=(b, d),
        comparator_contract=comparator_contract,
        starting_state=starting_state,
        request_plan=request_plan,
        execution_budget=ExecutionBudget(),
        primary_endpoint=PrimaryEndpoint(
            field="exact_object",
            per_condition_observations=3,
            condition_pass="3_OF_3_EXACT_OBJECT_TRUE",
            condition_fail="0_OF_3_EXACT_OBJECT_TRUE",
            condition_mixed="1_OR_2_OF_3_EXACT_OBJECT_TRUE",
        ),
        secondary_observations=secondary,
        decision_rules=decision_rules,
        safety=Safety(),
        next_gate=NEXT_GATE,
        non_claims=(
            "Exact repetition is not established as the sole cause.",
            "Aligned 16-token block recurrence is not established as causal.",
            "Marker lexical novelty is not eliminated.",
            "Marker semantic novelty is not eliminated.",
            "An exact repetition threshold is not established.",
            "The exact root cause is not established.",
            "A prefix-cache defect is not established.",
            "P5 is not requalified.",
            "P6 is not requalified.",
            "Measured North-Star A/B/C execution was not performed.",
            "Production readiness is not established.",
            "No runtime, model, GPU, or Kaggle execution is authorized.",
        ),
    )


def generate(root: Path) -> DesignRecord:
    record = build_design_record(root)
    target = root / RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_canonical(record))
    return record


def validate_generated(root: Path) -> DesignRecord:
    record = build_design_record(root)
    expected = _canonical(record)
    observed = _bytes(root, RECORD_PATH)
    if observed != expected:
        raise DesignError(
            "B_VS_D_MARKER_DIVERSIFIED_DESIGN_RECORD_DRIFT",
            "generated design record is not deterministic or has drifted",
            RECORD_PATH.as_posix(),
        )
    return record


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = args.repo_root.resolve()
    try:
        if args.write:
            record = generate(root)
            print(
                json.dumps(
                    {
                        "status": "DESIGN_FROZEN_NOT_EXECUTED",
                        "record_path": RECORD_PATH.as_posix(),
                        "record_sha256": _sha(_canonical(record)),
                        "new_execution_authorized": False,
                        "next_gate": NEXT_GATE,
                    },
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            return 0

        record = validate_generated(root)
        print(
            json.dumps(
                {
                    "status": "VALID",
                    "record_path": RECORD_PATH.as_posix(),
                    "record_sha256": _sha(_canonical(record)),
                    "new_execution_authorized": False,
                    "next_gate": NEXT_GATE,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except DesignError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
