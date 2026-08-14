"""Freeze the P4/P5 token-count-matched context-structure differential design V1.

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

BASE_MAIN_COMMIT: Final = "525be9c9b385411699a0bf8b736a36dff40e3552"
NEXT_GATE: Final = "IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"

DISPOSITION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_cache_context_repetition_differential_disposition_v1.json"
)
DISPOSITION_RECORD_SHA256: Final = (
    "2bc50b6f3085971ebc60178e360707c7c58838a0ad796ff752176062433cdc65"
)
DISPOSITION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_cache_context_repetition_differential_disposition_v1_review.json"
)
DISPOSITION_REVIEW_SHA256: Final = (
    "eeff988ca054f7e77e7dbbf48dcd3a57b8e84412fd71c167c11a58b5233ed5d0"
)
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_runtime_v1.py"
)
RUNTIME_SHA256: Final = "dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b"

EVIDENCE_ROOT: Final = Path(
    "benchmarks/local_abc/evidence/token_count_matched_context_structure_differential_design_v1"
)
TOKENIZER_RECEIPT_PATH: Final = EVIDENCE_ROOT / "tokenizer_feasibility_receipt_v2.json"
TOKENIZER_RECEIPT_SHA256: Final = "dbf439c7ab51487aa04e0cd14e5ef9fd203409de08729bb4b293178de63eb0c5"
COMPARATOR_FEASIBILITY_PATH: Final = EVIDENCE_ROOT / "comparator_feasibility_v2.json"
COMPARATOR_FEASIBILITY_SHA256: Final = (
    "7fb326c629c1df927aa97cc96fb86f555a58b024f400ef3712762f84af1f55d1"
)
FREEZE_CANDIDATE_PATH: Final = EVIDENCE_ROOT / "design_freeze_candidate_v1.json"
FREEZE_CANDIDATE_SHA256: Final = "501966a697d1f9b62ce16eec47ff041b164ccf0b4951ea23397932bfc1ea1268"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_differential_design_v1.json"
)

A_TOKEN_SHA256: Final = "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
B_TOKEN_SHA256: Final = "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
C_TOKEN_SHA256: Final = "612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4"

V4_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
FINAL_OBJECT: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
ROLES: Final = ("system", "user", "assistant", "user")

ORDER: Final = (
    "A_ORIGINAL_24X_ANCHOR",
    "B_NEUTRAL_REPEATED_24X",
    "C_NEUTRAL_DIVERSE_24_SEGMENT",
    "B_NEUTRAL_REPEATED_24X",
    "C_NEUTRAL_DIVERSE_24_SEGMENT",
    "A_ORIGINAL_24X_ANCHOR",
    "C_NEUTRAL_DIVERSE_24_SEGMENT",
    "A_ORIGINAL_24X_ANCHOR",
    "B_NEUTRAL_REPEATED_24X",
)


class DesignError(RuntimeError):
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
        raise DesignError("P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityScope(StrEnum):
    CURRENT_CAUSAL = "CURRENT_CAUSAL"
    CURRENT_RUNTIME = "CURRENT_RUNTIME"
    QUALIFIED_OFFLINE_EVIDENCE = "QUALIFIED_OFFLINE_EVIDENCE"


class ConditionId(StrEnum):
    A_ORIGINAL_24X_ANCHOR = "A_ORIGINAL_24X_ANCHOR"
    B_NEUTRAL_REPEATED_24X = "B_NEUTRAL_REPEATED_24X"
    C_NEUTRAL_DIVERSE_24_SEGMENT = "C_NEUTRAL_DIVERSE_24_SEGMENT"


class DecisionState(StrEnum):
    REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED = (
        "REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED"
    )
    HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED = (
        "HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"
    )
    SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE = "SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE"
    DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED = "DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED"
    UNSTABLE_NO_MECHANISTIC_CLAIM = "UNSTABLE_NO_MECHANISTIC_CLAIM"
    ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE = (
        "ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE"
    )
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class AuthorityReceipt(FrozenModel):
    role: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: AuthorityScope


class GenerationControls(FrozenModel):
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    repetition_penalty: float = 1.1
    seed: Literal[7] = 7
    max_tokens: Literal[32] = 32
    stream: Literal[False] = False
    response_format_present: Literal[False] = False
    output_mode: Literal["UNCONSTRAINED"] = "UNCONSTRAINED"

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.repetition_penalty != 1.1:
            raise ValueError("repetition penalty drifted")
        return self


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
    prefix_caching_enabled: Literal[True] = True
    cache_block_size: Literal[16] = 16
    max_model_len: Literal[4096] = 4096


class FrozenComposition(FrozenModel):
    message_roles: tuple[str, ...]
    system_instruction: str
    cache_context_tail: str
    assistant_ack: str
    final_object_canonical: str
    prompt_token_count_per_condition: Literal[899] = 899
    segment_count_per_condition: Literal[24] = 24
    no_schema_or_guided_decoding: Literal[True] = True
    parser_semantics_preserved: Literal[True] = True

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.message_roles != ROLES:
            raise ValueError("message roles drifted")
        if self.system_instruction != V4_INSTRUCTION:
            raise ValueError("system instruction drifted")
        if self.cache_context_tail != V4_INSTRUCTION:
            raise ValueError("cache-context tail drifted")
        if self.assistant_ack != ASSISTANT_ACK:
            raise ValueError("assistant acknowledgement drifted")
        if self.final_object_canonical != FINAL_OBJECT:
            raise ValueError("final object drifted")
        return self


class RepetitionMetrics(FrozenModel):
    body_token_count: Literal[817]
    duplicate_4gram_fraction: float = Field(ge=0, le=1)
    duplicate_8gram_fraction: float = Field(ge=0, le=1)
    duplicate_16gram_fraction: float = Field(ge=0, le=1)


class ConditionDefinition(FrozenModel):
    condition_id: ConditionId
    prompt_token_count: Literal[899]
    prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_count: Literal[24]
    unique_segment_count: Literal[1, 24]
    segments: tuple[str, ...] = Field(min_length=24, max_length=24)
    semantic_class: str
    instruction_like_repetition_present: bool
    repetition_metrics: RepetitionMetrics

    @model_validator(mode="after")
    def exact(self) -> Self:
        expected_hashes = {
            ConditionId.A_ORIGINAL_24X_ANCHOR: A_TOKEN_SHA256,
            ConditionId.B_NEUTRAL_REPEATED_24X: B_TOKEN_SHA256,
            ConditionId.C_NEUTRAL_DIVERSE_24_SEGMENT: C_TOKEN_SHA256,
        }
        if self.prompt_token_sha256 != expected_hashes[self.condition_id]:
            raise ValueError("condition token identity drifted")

        unique = len(set(self.segments))
        if unique != self.unique_segment_count:
            raise ValueError("segment uniqueness drifted")

        if self.condition_id == ConditionId.A_ORIGINAL_24X_ANCHOR and (
            self.unique_segment_count != 1 or not self.instruction_like_repetition_present
        ):
            raise ValueError("anchor structure drifted")

        if self.condition_id == ConditionId.B_NEUTRAL_REPEATED_24X and (
            self.unique_segment_count != 1 or self.instruction_like_repetition_present
        ):
            raise ValueError("neutral repeated structure drifted")

        if self.condition_id == ConditionId.C_NEUTRAL_DIVERSE_24_SEGMENT and (
            self.unique_segment_count != 24 or self.instruction_like_repetition_present
        ):
            raise ValueError("neutral diverse structure drifted")

        return self


class HumanComparatorReview(FrozenModel):
    neutrality: Literal["PASS"]
    naturalness: Literal["PASS"]
    semantic_comparability: Literal["PASS"]
    structural_isolation: Literal["PASS_WITH_BOUNDED_LEXICAL_NOVELTY"]


class ComparatorContract(FrozenModel):
    human_review: HumanComparatorReview
    b_duplicate_8gram_fraction: float = Field(ge=0, le=1)
    c_duplicate_8gram_fraction: float = Field(ge=0, le=1)
    b_duplicate_16gram_fraction: float = Field(ge=0, le=1)
    c_duplicate_16gram_fraction: float = Field(ge=0, le=1)
    b_and_c_forbidden_terms_zero: Literal[True]
    bounded_residual_difference: str

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.c_duplicate_8gram_fraction >= self.b_duplicate_8gram_fraction:
            raise ValueError("8-gram separation drifted")
        if self.c_duplicate_16gram_fraction > self.b_duplicate_16gram_fraction * 0.5:
            raise ValueError("16-gram separation drifted")
        return self


class StartingStateContract(FrozenModel):
    strategy: Literal["FRESH_WORKER_PROCESS_PER_OBSERVATION"]
    prior_request_cache_carryover_permitted: Literal[False] = False
    require_fresh_worker_identity: Literal[True] = True
    require_zero_cached_prefix_baseline: Literal[True] = True
    teardown_required_between_observations: Literal[True] = True
    teardown_failure_invalidates_diagnostic: Literal[True] = True


class RequestPlanItem(FrozenModel):
    ordinal: int = Field(ge=1, le=9)
    condition_id: ConditionId


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[9] = 9
    maximum_worker_starts: Literal[9] = 9
    maximum_model_requests: Literal[9] = 9
    maximum_output_tokens_per_request: Literal[32] = 32
    hidden_retries_permitted: Literal[0] = 0
    replacement_observations_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class PrimaryEndpoint(FrozenModel):
    field: Literal["exact_object"]
    per_condition_observations: Literal[3] = 3
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
        "auragateway-p4-p5-token-count-matched-context-structure-differential-design-v1"
    ]
    design_status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["525be9c9b385411699a0bf8b736a36dff40e3552"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(min_length=6, max_length=6)
    runtime: RuntimeIdentity
    generation_controls: GenerationControls
    frozen_composition: FrozenComposition
    conditions: tuple[ConditionDefinition, ConditionDefinition, ConditionDefinition]
    comparator_contract: ComparatorContract
    starting_state: StartingStateContract
    request_plan: tuple[RequestPlanItem, ...] = Field(min_length=9, max_length=9)
    execution_budget: ExecutionBudget
    primary_endpoint: PrimaryEndpoint
    secondary_observations: tuple[str, ...] = Field(min_length=10)
    decision_rules: tuple[DecisionRule, ...] = Field(min_length=7, max_length=7)
    safety: Safety
    next_gate: Literal[
        "IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def exact(self) -> Self:
        if tuple(condition.condition_id for condition in self.conditions) != tuple(ConditionId):
            raise ValueError("condition order drifted")

        observed_order = tuple(item.condition_id.value for item in self.request_plan)
        if observed_order != ORDER:
            raise ValueError("request order drifted")

        for condition_id in ConditionId:
            positions = tuple(
                item.ordinal for item in self.request_plan if item.condition_id == condition_id
            )
            if len(positions) != 3:
                raise ValueError("condition observation cardinality drifted")
            if sum(positions) != 15:
                raise ValueError("condition positional balance drifted")

        if tuple(rule.state for rule in self.decision_rules) != tuple(DecisionState):
            raise ValueError("decision rule order drifted")

        return self


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _file(root: Path, path: Path) -> Path:
    absolute = root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_MISSING",
            "required design authority is missing or unsafe",
            path.as_posix(),
        )
    return absolute


def _bytes(root: Path, path: Path, expected: str | None = None) -> bytes:
    data = _file(root, path).read_bytes()
    if expected is not None and _sha(data) != expected:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_DRIFT",
            "required design authority identity drifted",
            path.as_posix(),
        )
    return data


def _object(root: Path, path: Path, expected: str | None = None) -> dict[str, object]:
    try:
        value: object = json.loads(_bytes(root, path, expected))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_INVALID",
            "required authority is not valid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_INVALID",
            "required authority root is not an object",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_INVALID",
            f"{name} is not an object",
        )
    return cast(dict[str, object], value)


def _sequence(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_AUTHORITY_INVALID",
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
        "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_GIT_STATE_INVALID",
        "unable to verify frozen design base ancestry",
    )


def _validate_semantics(root: Path) -> None:
    if not _base_commit_is_ancestor_of_head(root):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_BASE_MAIN_DRIFT",
            "frozen design base is not an ancestor of current HEAD",
        )

    disposition = _object(root, DISPOSITION_RECORD_PATH, DISPOSITION_RECORD_SHA256)
    disposition_expected = {
        "status": "DISPOSITIONED_VALID_GOVERNED_REPETITION_DIFFERENTIAL",
        "decision_state": "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED",
        "diagnostic_status": "DIAGNOSTIC_COMPLETE",
        "control_exact_object_count": 3,
        "treatment_exact_object_count": 0,
        "observations_per_condition": 3,
        "fresh_worker_process_per_observation": True,
        "worker_identity_cardinality": 6,
        "long_repeated_24x_condition_necessary_relative_to_1x_established": True,
        "repetition_alone_established_causal": False,
        "context_length_alone_established_causal": False,
        "exact_repetition_threshold_established": False,
        "exact_root_cause_established": False,
        "prefix_cache_defect_established": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "hidden_retries_performed": 0,
        "external_network_requests_performed": 0,
        "external_spend": 0,
        "new_execution_authorized": False,
        "next_gate": "STATIC_LONG_REPEATED_CONTEXT_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1",
    }
    for key, expected in disposition_expected.items():
        if disposition.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_DISPOSITION_DRIFT",
                "accepted repetition disposition drifted",
                key,
            )

    review = _object(root, DISPOSITION_REVIEW_PATH, DISPOSITION_REVIEW_SHA256)
    review_expected = {
        "status": "APPROVED_GOVERNED_REPETITION_DIFFERENTIAL_DISPOSITION",
        "positive_necessity_result_accepted": True,
        "exact_root_cause_claimed": False,
        "exact_threshold_claimed": False,
        "measured_abc_claimed": False,
        "new_execution_authorized": False,
        "next_gate": "STATIC_LONG_REPEATED_CONTEXT_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1",
    }
    for key, expected in review_expected.items():
        if review.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_REVIEW_DRIFT",
                "accepted disposition review drifted",
                key,
            )

    _bytes(root, RUNTIME_PATH, RUNTIME_SHA256)

    oracle = _object(root, TOKENIZER_RECEIPT_PATH, TOKENIZER_RECEIPT_SHA256)
    if oracle.get("historical_token_identity_reproduced") is not True:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
            "qualified tokenizer oracle no longer reproduces historical identity",
        )
    if oracle.get("runtime_sha256") != RUNTIME_SHA256:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
            "qualified tokenizer oracle runtime identity drifted",
        )
    oracle_control = _mapping(oracle.get("control"), "tokenizer control")
    oracle_treatment = _mapping(oracle.get("treatment"), "tokenizer treatment")
    if oracle_control.get("observed_token_count") != 117:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
            "qualified tokenizer control count drifted",
        )
    if oracle_control.get("observed_token_sha256") != (
        "32a570d63aaaeb9597a2b517315b052eae7308b7acba6f4a85d409e3c633edbb"
    ):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
            "qualified tokenizer control identity drifted",
        )
    if oracle_treatment.get("observed_token_count") != 899:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
            "qualified tokenizer treatment count drifted",
        )
    if oracle_treatment.get("observed_token_sha256") != A_TOKEN_SHA256:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
            "qualified tokenizer treatment identity drifted",
        )
    for key in (
        "model_loaded",
        "model_request_executed",
        "gpu_execution_authorized",
        "kaggle_execution_authorized",
        "new_execution_authorized",
    ):
        if oracle.get(key) is not False:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_TOKENIZER_ORACLE_DRIFT",
                "qualified tokenizer safety boundary drifted",
                key,
            )

    comparator = _object(root, COMPARATOR_FEASIBILITY_PATH, COMPARATOR_FEASIBILITY_SHA256)
    if comparator.get("qualified_oracle_receipt_sha256") != TOKENIZER_RECEIPT_SHA256:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
            "comparator oracle binding drifted",
        )
    if comparator.get("runtime_sha256") != RUNTIME_SHA256:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
            "comparator runtime binding drifted",
        )
    claims = _mapping(comparator.get("claims"), "comparator claims")
    claims_expected = {
        "comparators_constructible": True,
        "exact_final_token_count_matched": True,
        "semantic_directive_amplification_removed_in_b": True,
        "exact_repetition_materially_reduced_in_c": True,
        "root_cause_established": False,
        "repetition_threshold_established": False,
        "context_length_causal": False,
    }
    for key, expected in claims_expected.items():
        if claims.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
                "comparator claim boundary drifted",
                key,
            )

    comparator_conditions = _mapping(comparator.get("conditions"), "comparator conditions")
    expected_tokens = {
        "A_ORIGINAL_24X_ANCHOR": A_TOKEN_SHA256,
        "B_NEUTRAL_REPEATED_24X": B_TOKEN_SHA256,
        "C_NEUTRAL_DIVERSE_24_SEGMENT": C_TOKEN_SHA256,
    }
    for condition_id, token_sha256 in expected_tokens.items():
        condition = _mapping(comparator_conditions.get(condition_id), condition_id)
        if condition.get("prompt_token_count") != 899:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
                "comparator token count drifted",
                condition_id,
            )
        if condition.get("prompt_token_sha256") != token_sha256:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
                "comparator token identity drifted",
                condition_id,
            )
        if condition.get("segment_count") != 24:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
                "comparator segment count drifted",
                condition_id,
            )

    c_condition = _mapping(
        comparator_conditions.get("C_NEUTRAL_DIVERSE_24_SEGMENT"),
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
    )
    if c_condition.get("unique_segment_count") != 24:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_COMPARATOR_DRIFT",
            "diverse comparator uniqueness drifted",
        )

    freeze = _object(root, FREEZE_CANDIDATE_PATH, FREEZE_CANDIDATE_SHA256)
    if freeze.get("design_id") != (
        "auragateway-token-count-matched-context-structure-differential-v1"
    ):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
            "freeze candidate identity drifted",
        )
    if freeze.get("design_state") != "FREEZE_CANDIDATE":
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
            "freeze candidate state drifted",
        )

    source_evidence = _mapping(freeze.get("source_evidence"), "freeze source evidence")
    source_expected = {
        "comparator_feasibility_v2_sha256": COMPARATOR_FEASIBILITY_SHA256,
        "qualified_tokenizer_oracle_sha256": TOKENIZER_RECEIPT_SHA256,
        "runtime_sha256": RUNTIME_SHA256,
    }
    for key, expected in source_expected.items():
        if source_evidence.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "freeze source evidence binding drifted",
                key,
            )

    human_review = _mapping(source_evidence.get("human_comparator_review"), "human review")
    human_expected = {
        "neutrality": "PASS",
        "naturalness": "PASS",
        "semantic_comparability": "PASS",
        "structural_isolation": "PASS_WITH_BOUNDED_LEXICAL_NOVELTY",
    }
    for key, expected in human_expected.items():
        if human_review.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "human comparator review drifted",
                key,
            )

    hard = _mapping(freeze.get("hard_invariants"), "freeze hard invariants")
    hard_expected = {
        "prompt_token_count_per_condition": 899,
        "segment_count_per_condition": 24,
        "hidden_retries": 0,
        "replacement_observations": 0,
        "network_operations_during_governed_requests": 0,
        "spend": 0,
        "worker_policy": "FRESH_WORKER_PER_OBSERVATION",
    }
    for key, expected in hard_expected.items():
        if hard.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "freeze hard invariant drifted",
                key,
            )

    plan = _mapping(freeze.get("proposed_observation_plan"), "observation plan")
    if tuple(_sequence(plan.get("condition_order"), "condition order")) != ORDER:
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
            "freeze request order drifted",
        )
    plan_expected = {
        "total_observations": 9,
        "maximum_requests": 9,
        "maximum_model_loads": 9,
        "maximum_worker_starts": 9,
        "fresh_worker_per_observation": True,
        "retries": 0,
        "replacement_observations": 0,
    }
    for key, expected in plan_expected.items():
        if plan.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "freeze observation budget drifted",
                key,
            )

    endpoint = _mapping(freeze.get("primary_endpoint"), "primary endpoint")
    endpoint_expected = {
        "field": "exact_object",
        "per_condition_observations": 3,
        "condition_pass": "3_OF_3_EXACT_OBJECT_TRUE",
        "condition_fail": "0_OF_3_EXACT_OBJECT_TRUE",
        "condition_mixed": "1_OR_2_OF_3_EXACT_OBJECT_TRUE",
    }
    for key, expected in endpoint_expected.items():
        if endpoint.get(key) != expected:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "freeze primary endpoint drifted",
                key,
            )

    authorization = _mapping(freeze.get("authorization"), "freeze authorization")
    for key in (
        "model_loaded",
        "model_request_executed",
        "runtime_execution_authorized",
        "gpu_execution_authorized",
        "kaggle_execution_authorized",
        "new_execution_authorized",
    ):
        if authorization.get(key) is not False:
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "freeze authorization boundary drifted",
                key,
            )


def validate_authorities(root: Path) -> tuple[AuthorityReceipt, ...]:
    _validate_semantics(root)
    specs = (
        (
            "governed_repetition_disposition",
            DISPOSITION_RECORD_PATH,
            DISPOSITION_RECORD_SHA256,
            AuthorityScope.CURRENT_CAUSAL,
        ),
        (
            "governed_repetition_disposition_review",
            DISPOSITION_REVIEW_PATH,
            DISPOSITION_REVIEW_SHA256,
            AuthorityScope.CURRENT_CAUSAL,
        ),
        (
            "bound_repetition_runtime",
            RUNTIME_PATH,
            RUNTIME_SHA256,
            AuthorityScope.CURRENT_RUNTIME,
        ),
        (
            "qualified_tokenizer_oracle",
            TOKENIZER_RECEIPT_PATH,
            TOKENIZER_RECEIPT_SHA256,
            AuthorityScope.QUALIFIED_OFFLINE_EVIDENCE,
        ),
        (
            "token_count_matched_comparator_feasibility",
            COMPARATOR_FEASIBILITY_PATH,
            COMPARATOR_FEASIBILITY_SHA256,
            AuthorityScope.QUALIFIED_OFFLINE_EVIDENCE,
        ),
        (
            "human_reviewed_design_freeze_candidate",
            FREEZE_CANDIDATE_PATH,
            FREEZE_CANDIDATE_SHA256,
            AuthorityScope.QUALIFIED_OFFLINE_EVIDENCE,
        ),
    )
    return tuple(
        AuthorityReceipt(
            role=role,
            path=path.as_posix(),
            sha256=_sha(_bytes(root, path, expected)),
            scope=scope,
        )
        for role, path, expected, scope in specs
    )


def _condition_definition(
    freeze_conditions: dict[str, object],
    condition_id: ConditionId,
) -> ConditionDefinition:
    raw = _mapping(freeze_conditions.get(condition_id.value), condition_id.value)

    if condition_id == ConditionId.C_NEUTRAL_DIVERSE_24_SEGMENT:
        segment_values = _sequence(raw.get("segments"), "diverse segments")
        if not all(isinstance(value, str) for value in segment_values):
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "diverse comparator contains a non-string segment",
            )
        segments = tuple(cast(str, value) for value in segment_values)
        semantic_class = "NEUTRAL_SEMANTICALLY_COMPARABLE_DIVERSE_CONTEXT"
        instruction_like = False
    else:
        segment = raw.get("segment")
        if not isinstance(segment, str):
            raise DesignError(
                "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
                "repeated comparator segment is unavailable",
                condition_id.value,
            )
        segments = (segment,) * 24
        semantic_class = (
            "ORIGINAL_INSTRUCTION_LIKE_REPEATED_CONTEXT"
            if condition_id == ConditionId.A_ORIGINAL_24X_ANCHOR
            else "NEUTRAL_SEMANTICALLY_COMPARABLE_REPEATED_CONTEXT"
        )
        instruction_like = condition_id == ConditionId.A_ORIGINAL_24X_ANCHOR

    metrics_raw = _mapping(raw.get("repetition_metrics"), "repetition metrics")

    return ConditionDefinition(
        condition_id=condition_id,
        prompt_token_count=cast(Literal[899], raw.get("prompt_token_count")),
        prompt_token_sha256=cast(str, raw.get("prompt_token_sha256")),
        segment_count=cast(Literal[24], raw.get("segment_count")),
        unique_segment_count=cast(Literal[1, 24], raw.get("unique_segment_count")),
        segments=segments,
        semantic_class=semantic_class,
        instruction_like_repetition_present=instruction_like,
        repetition_metrics=RepetitionMetrics.model_validate(metrics_raw),
    )


def build_design_record(root: Path) -> DesignRecord:
    authorities = validate_authorities(root)
    freeze = _object(root, FREEZE_CANDIDATE_PATH, FREEZE_CANDIDATE_SHA256)
    freeze_conditions = _mapping(freeze.get("conditions"), "freeze conditions")

    conditions = tuple(
        _condition_definition(freeze_conditions, condition_id) for condition_id in ConditionId
    )
    _a_condition, b_condition, c_condition = conditions

    source_evidence = _mapping(freeze.get("source_evidence"), "freeze source evidence")
    human_review = HumanComparatorReview.model_validate(
        _mapping(source_evidence.get("human_comparator_review"), "human comparator review")
    )

    factors = _mapping(freeze.get("intentionally_varied_factors"), "varied factors")
    b_to_c = _mapping(factors.get("B_to_C"), "B_to_C factor")

    endpoint = PrimaryEndpoint.model_validate(
        _mapping(freeze.get("primary_endpoint"), "primary endpoint")
    )

    secondary_raw = _sequence(freeze.get("secondary_observations"), "secondary observations")
    if not all(isinstance(value, str) for value in secondary_raw):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
            "secondary observation contains a non-string value",
        )
    secondary = tuple(cast(str, value) for value in secondary_raw)

    non_claim_raw = _sequence(freeze.get("predeclared_nonclaims"), "predeclared non-claims")
    if not all(isinstance(value, str) for value in non_claim_raw):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_FREEZE_DRIFT",
            "predeclared non-claim contains a non-string value",
        )
    non_claims = tuple(cast(str, value) for value in non_claim_raw)

    return DesignRecord(
        record_id="auragateway-p4-p5-token-count-matched-context-structure-differential-design-v1",
        design_status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=authorities,
        runtime=RuntimeIdentity(
            model_repository="Qwen/Qwen2.5-0.5B-Instruct",
            model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
            tokenizer_revision="7ae557604adf67be50417f59c2c2f167def9a775",
            model_snapshot_sha256=(
                "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
            ),
            backend="TRITON_ATTN",
            vllm_distribution="0.25.1+cu129",
            torch="2.11.0+cu129",
            torch_cuda="12.9",
            triton="3.6.0",
            transformers="5.14.1",
            platform_topology="T4_x2",
            worker_gpu_index=0,
        ),
        generation_controls=GenerationControls(),
        frozen_composition=FrozenComposition(
            message_roles=ROLES,
            system_instruction=V4_INSTRUCTION,
            cache_context_tail=V4_INSTRUCTION,
            assistant_ack=ASSISTANT_ACK,
            final_object_canonical=FINAL_OBJECT,
        ),
        conditions=cast(
            tuple[ConditionDefinition, ConditionDefinition, ConditionDefinition],
            conditions,
        ),
        comparator_contract=ComparatorContract(
            human_review=human_review,
            b_duplicate_8gram_fraction=b_condition.repetition_metrics.duplicate_8gram_fraction,
            c_duplicate_8gram_fraction=c_condition.repetition_metrics.duplicate_8gram_fraction,
            b_duplicate_16gram_fraction=b_condition.repetition_metrics.duplicate_16gram_fraction,
            c_duplicate_16gram_fraction=c_condition.repetition_metrics.duplicate_16gram_fraction,
            b_and_c_forbidden_terms_zero=True,
            bounded_residual_difference=cast(str, b_to_c.get("bounded_residual_difference")),
        ),
        starting_state=StartingStateContract(
            strategy="FRESH_WORKER_PROCESS_PER_OBSERVATION",
        ),
        request_plan=tuple(
            RequestPlanItem(ordinal=ordinal, condition_id=ConditionId(condition_id))
            for ordinal, condition_id in enumerate(ORDER, start=1)
        ),
        execution_budget=ExecutionBudget(),
        primary_endpoint=endpoint,
        secondary_observations=secondary,
        decision_rules=(
            DecisionRule(
                state=(
                    DecisionState.REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED
                ),
                condition="A is 0/3 exact-object, B is 3/3, and C is 3/3.",
                implication=(
                    "Neutralizing the original repeated semantic and instruction-like body "
                    "restores exact-object behavior under both highly repetitive and diverse "
                    "neutral 899-token contexts."
                ),
            ),
            DecisionRule(
                state=DecisionState.HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED,
                condition="A is 0/3 exact-object, B is 0/3, and C is 3/3.",
                implication=(
                    "Failure survives a neutral highly repeated 899-token body and is removed "
                    "when exact repetition is substantially reduced while broad semantic class "
                    "and total prompt length remain matched."
                ),
            ),
            DecisionRule(
                state=DecisionState.SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE,
                condition="A is 0/3 exact-object, B is 0/3, and C is 0/3.",
                implication=(
                    "Semantic neutralization and repetition reduction do not restore the "
                    "endpoint; total context magnitude, absolute position, or another shared "
                    "long-context/runtime interaction rises."
                ),
            ),
            DecisionRule(
                state=DecisionState.DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED,
                condition="A is 0/3 exact-object, B is 3/3, and C is 0/3.",
                implication=(
                    "The neutral repeated comparator succeeds while the neutral diverse "
                    "comparator fails; C-specific lexical or structural effects require "
                    "reconciliation before any target-mechanism claim."
                ),
            ),
            DecisionRule(
                state=DecisionState.UNSTABLE_NO_MECHANISTIC_CLAIM,
                condition="Any condition is 1/3 or 2/3 exact-object.",
                implication="The primary endpoint is unstable; no mechanistic claim is permitted.",
            ),
            DecisionRule(
                state=DecisionState.ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE,
                condition="Condition A is not 0/3 exact-object.",
                implication=(
                    "Historical anchor reproduction fails; B and C are not used for "
                    "mechanistic inference."
                ),
            ),
            DecisionRule(
                state=DecisionState.DIAGNOSTIC_INVALID,
                condition=(
                    "A required runtime, token, worker, cold-state, budget, teardown, "
                    "or cleanup invariant fails."
                ),
                implication="The experiment cannot support a behavioral conclusion.",
            ),
        ),
        safety=Safety(),
        next_gate=NEXT_GATE,
        non_claims=non_claims,
    )


def generate(root: Path) -> DesignRecord:
    record = build_design_record(root)
    path = root / RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(record))
    return record


def validate_generated(root: Path) -> DesignRecord:
    expected = build_design_record(root)
    observed = _file(root, RECORD_PATH).read_bytes()
    if observed != _canonical(expected):
        raise DesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_DIFF_RECORD_DRIFT",
            "generated design record drifted",
            RECORD_PATH.as_posix(),
        )
    return DesignRecord.model_validate(json.loads(observed))


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        description="Freeze/check token-count-matched context-structure differential design V1"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.repo_root.resolve()
    try:
        record = generate(root) if args.write else validate_generated(root)
    except DesignError as error:
        print(json.dumps(error.envelope(), separators=(",", ":"), sort_keys=True))
        return 1

    print(
        json.dumps(
            {
                "design_status": record.design_status,
                "condition_a_tokens": record.conditions[0].prompt_token_count,
                "condition_b_tokens": record.conditions[1].prompt_token_count,
                "condition_c_tokens": record.conditions[2].prompt_token_count,
                "observations": len(record.request_plan),
                "maximum_model_requests": record.execution_budget.maximum_model_requests,
                "runtime_execution_authorized": record.safety.runtime_execution_authorized,
                "new_execution_authorized": record.safety.new_execution_authorized,
                "next_gate": record.next_gate,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
