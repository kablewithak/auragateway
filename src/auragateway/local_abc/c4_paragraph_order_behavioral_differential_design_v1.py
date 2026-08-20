"""Freeze C4 paragraph-order behavioral differential design V1.

Design-only reliability infrastructure. This module records the already
observed offline static-isolation result, binds the governed C4 authorities,
and freezes a future contemporaneous control/treatment behavioral
differential. It creates no live execution authority and performs no
model/GPU/Kaggle execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "29f7a5ea0513823c7f5d80c5d6cf636829515187"
NEXT_GATE: Final = "IMPLEMENT_AND_MERGE_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"

C4_DISPOSITION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_not_qualified_disposition_v1.json"
)
C4_DISPOSITION_RECORD_SHA256: Final = (
    "5d6dd611bf2d54778f86e43aac019c86648decb0aa9eb5121105e52928328cb3"
)

C4_DISPOSITION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_not_qualified_disposition_v1_review.json"
)
C4_DISPOSITION_REVIEW_SHA256: Final = (
    "96ffcdfffc7ff5c176ed0315b79ac59e4c15407e2ed742988b86550658ae6dc5"
)

C4_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_runtime_v1.py"
)
C4_RUNTIME_SHA256: Final = "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"

CANONICAL_CORPUS_PATH: Final = Path(
    "benchmarks/local_abc/evidence/"
    "canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_corpus_candidate_v2.txt"
)
CANONICAL_CORPUS_SHA256: Final = "140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"

C4_QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "canonical_synthetic_prefix_c4_behavioral_qualification_v1_request.json"
)
C4_QUALIFICATION_REQUEST_SHA256: Final = (
    "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
)

EXECUTION_AUTHORIZATION_ARCHITECTURE_PATH: Final = Path(
    "docs/adr/2026-08-11-local-abc-transaction-bound-execution-authorization-architecture-v1.md"
)
EXECUTION_AUTHORIZATION_ARCHITECTURE_SHA256: Final = (
    "30aa8af0523c7f7f6143817b7e797108bda68a86807476d2b10bf5c841a37798"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_paragraph_order_behavioral_differential_design_v1.json"
)

CONTROL_TOKEN_SHA256: Final = "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
TREATMENT_TOKEN_SHA256: Final = "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
HISTORICAL_CONTROL_PARSED_OBJECT_SHA256: Final = (
    "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
)
EXPECTED_OBJECT_SHA256: Final = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"

PROMPT_TOKEN_COUNT: Final = 899
FINAL_USER_BOUNDARY: Final = 880
MESSAGE_BOUNDARY_PROFILE: Final = (3, 28, 869, 880)
CONTROL_TREATMENT_COMMON_SUFFIX_TOKEN_COUNT: Final = 122
PARAGRAPH_COUNT: Final = 10
CONTROL_PARAGRAPH_ORDER: Final = tuple(range(1, 11))
TREATMENT_PARAGRAPH_ORDER: Final = (1, 9, 8, 7, 6, 5, 4, 3, 2, 10)

OBSERVATION_ORDER: Final = (
    "CONTROL_ORIGINAL_C4",
    "TREATMENT_REVERSED_MIDDLE_EIGHT",
    "TREATMENT_REVERSED_MIDDLE_EIGHT",
    "CONTROL_ORIGINAL_C4",
    "CONTROL_ORIGINAL_C4",
    "TREATMENT_REVERSED_MIDDLE_EIGHT",
)

SYSTEM_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
ASSISTANT_ACKNOWLEDGEMENT: Final = "Synthetic deterministic context acknowledged."
FINAL_OBJECT_CANONICAL: Final = '{"probe":"exact-runtime-p5-p6","value":1}'

AUTHORITY_SPECS: Final = (
    (
        "C4_NOT_QUALIFIED_DISPOSITION",
        C4_DISPOSITION_RECORD_PATH,
        C4_DISPOSITION_RECORD_SHA256,
    ),
    (
        "C4_NOT_QUALIFIED_DISPOSITION_REVIEW",
        C4_DISPOSITION_REVIEW_PATH,
        C4_DISPOSITION_REVIEW_SHA256,
    ),
    (
        "C4_RUNTIME",
        C4_RUNTIME_PATH,
        C4_RUNTIME_SHA256,
    ),
    (
        "CANONICAL_CORPUS",
        CANONICAL_CORPUS_PATH,
        CANONICAL_CORPUS_SHA256,
    ),
    (
        "C4_QUALIFICATION_REQUEST",
        C4_QUALIFICATION_REQUEST_PATH,
        C4_QUALIFICATION_REQUEST_SHA256,
    ),
    (
        "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE",
        EXECUTION_AUTHORIZATION_ARCHITECTURE_PATH,
        EXECUTION_AUTHORIZATION_ARCHITECTURE_SHA256,
    ),
)


class DesignError(RuntimeError):
    """Metadata-safe fail-closed design error."""

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
            "C4_PARAGRAPH_ORDER_DESIGN_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConditionId(StrEnum):
    CONTROL = "CONTROL_ORIGINAL_C4"
    TREATMENT = "TREATMENT_REVERSED_MIDDLE_EIGHT"


class DecisionState(StrEnum):
    CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE = (
        "CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
    )
    ORDER_INTERVENTION_RESTORES_BEHAVIOR = "ORDER_INTERVENTION_RESTORES_BEHAVIOR"
    ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE = (
        "ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE"
    )
    ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE = "ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE"
    ORDER_INTERVENTION_EFFECT_AMBIGUOUS = "ORDER_INTERVENTION_EFFECT_AMBIGUOUS"
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class AuthorityReceipt(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    assistant_acknowledgement: str
    final_object_canonical: str
    final_object_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_token_count_per_condition: Literal[899]
    final_user_boundary_per_condition: Literal[880]
    message_boundary_profile_per_condition: tuple[int, int, int, int]
    no_schema_or_guided_decoding: Literal[True]


class StaticIsolationEvidence(FrozenModel):
    evidence_status: Literal[
        "OPERATOR_OBSERVED_OFFLINE_STATIC_ORACLE_NOT_REEXECUTED_BY_DESIGN_PRODUCER"
    ]
    observed_date: Literal["2026-08-20"]
    control_prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    treatment_prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_token_count_equal: Literal[True]
    token_id_multiset_identical: Literal[True]
    final_user_boundary_equal: Literal[True]
    message_boundary_profile_equal: Literal[True]
    common_suffix_token_count: Literal[122]
    control_paragraph_order: tuple[int, ...]
    treatment_paragraph_order: tuple[int, ...]
    first_paragraph_preserved: Literal[True]
    last_paragraph_preserved: Literal[True]
    paragraph_content_multiset_preserved: Literal[True]
    character_count_preserved: Literal[True]
    producer_reexecutes_tokenizer: Literal[False]

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.control_prompt_token_sha256 != CONTROL_TOKEN_SHA256:
            raise ValueError("control token identity drifted")
        if self.treatment_prompt_token_sha256 != TREATMENT_TOKEN_SHA256:
            raise ValueError("treatment token identity drifted")
        if self.control_paragraph_order != CONTROL_PARAGRAPH_ORDER:
            raise ValueError("control paragraph order drifted")
        if self.treatment_paragraph_order != TREATMENT_PARAGRAPH_ORDER:
            raise ValueError("treatment paragraph order drifted")
        return self


class ConditionDefinition(FrozenModel):
    condition_id: ConditionId
    role: Literal["CONTEMPORANEOUS_FAILURE_ANCHOR", "ORDER_INTERVENTION"]
    prompt_token_count: Literal[899]
    prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    paragraph_count: Literal[10]
    paragraph_order: tuple[int, ...]
    final_user_boundary: Literal[880]
    message_boundary_profile: tuple[int, int, int, int]
    historical_exact_object_result: Literal["0_OF_3", "NOT_EXECUTED"]
    historical_canonical_parsed_object_sha256: str | None

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.message_boundary_profile != MESSAGE_BOUNDARY_PROFILE:
            raise ValueError("message boundary profile drifted")

        if self.condition_id == ConditionId.CONTROL:
            if self.role != "CONTEMPORANEOUS_FAILURE_ANCHOR":
                raise ValueError("control role drifted")
            if self.prompt_token_sha256 != CONTROL_TOKEN_SHA256:
                raise ValueError("control token identity drifted")
            if self.paragraph_order != CONTROL_PARAGRAPH_ORDER:
                raise ValueError("control paragraph order drifted")
            if self.historical_exact_object_result != "0_OF_3":
                raise ValueError("control historical result drifted")
            if (
                self.historical_canonical_parsed_object_sha256
                != HISTORICAL_CONTROL_PARSED_OBJECT_SHA256
            ):
                raise ValueError("control historical phenotype drifted")

        if self.condition_id == ConditionId.TREATMENT:
            if self.role != "ORDER_INTERVENTION":
                raise ValueError("treatment role drifted")
            if self.prompt_token_sha256 != TREATMENT_TOKEN_SHA256:
                raise ValueError("treatment token identity drifted")
            if self.paragraph_order != TREATMENT_PARAGRAPH_ORDER:
                raise ValueError("treatment paragraph order drifted")
            if self.historical_exact_object_result != "NOT_EXECUTED":
                raise ValueError("treatment execution state drifted")
            if self.historical_canonical_parsed_object_sha256 is not None:
                raise ValueError("treatment historical phenotype must be absent")

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
    maximum_worker_teardowns: Literal[6] = 6
    maximum_output_tokens_per_request: Literal[32] = 32
    hidden_retries_permitted: Literal[0] = 0
    replacement_observations_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class PrimaryEndpoint(FrozenModel):
    field: Literal["exact_object"]
    observations_per_condition: Literal[3]
    pass_state: Literal["3_OF_3_EXACT_OBJECT_TRUE"]
    fail_state: Literal["0_OF_3_EXACT_OBJECT_TRUE"]
    mixed_state: Literal["1_OR_2_OF_3_EXACT_OBJECT_TRUE"]


class DecisionRule(FrozenModel):
    state: DecisionState
    condition: str
    implication: str


class Safety(FrozenModel):
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    execution_authorization_issued: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    p5_p6_requalification_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False


class DesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-c4-paragraph-order-behavioral-differential-design-v1"]
    design_status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["29f7a5ea0513823c7f5d80c5d6cf636829515187"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(
        min_length=6,
        max_length=6,
    )
    runtime: RuntimeIdentity
    generation_controls: GenerationControls
    frozen_composition: FrozenComposition
    static_isolation_evidence: StaticIsolationEvidence
    conditions: tuple[ConditionDefinition, ConditionDefinition]
    starting_state: StartingStateContract
    request_plan: tuple[RequestPlanItem, ...] = Field(
        min_length=6,
        max_length=6,
    )
    execution_budget: ExecutionBudget
    primary_endpoint: PrimaryEndpoint
    decision_rules: tuple[DecisionRule, ...] = Field(
        min_length=6,
        max_length=6,
    )
    safety: Safety
    next_gate: Literal["IMPLEMENT_AND_MERGE_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def exact(self) -> Self:
        if tuple(item.condition_id for item in self.conditions) != (
            ConditionId.CONTROL,
            ConditionId.TREATMENT,
        ):
            raise ValueError("condition order drifted")

        observed_order = tuple(item.condition_id.value for item in self.request_plan)
        if observed_order != OBSERVATION_ORDER:
            raise ValueError("observation order drifted")

        control_positions = tuple(
            item.ordinal for item in self.request_plan if item.condition_id == ConditionId.CONTROL
        )
        treatment_positions = tuple(
            item.ordinal for item in self.request_plan if item.condition_id == ConditionId.TREATMENT
        )
        if control_positions != (1, 4, 5):
            raise ValueError("control positions drifted")
        if treatment_positions != (2, 3, 6):
            raise ValueError("treatment positions drifted")

        if tuple(rule.state for rule in self.decision_rules) != tuple(DecisionState):
            raise ValueError("decision-rule order drifted")

        return self


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
    target = root / path
    if not target.is_file() or target.is_symlink():
        raise DesignError(
            "C4_PARAGRAPH_ORDER_DESIGN_AUTHORITY_MISSING",
            "required design authority is missing or unsafe",
            path.as_posix(),
        )
    return target


def _bytes(
    root: Path,
    path: Path,
    expected_sha256: str,
) -> bytes:
    payload = _file(root, path).read_bytes()
    if _sha(payload) != expected_sha256:
        raise DesignError(
            "C4_PARAGRAPH_ORDER_DESIGN_AUTHORITY_DRIFT",
            "required design authority identity drifted",
            path.as_posix(),
        )
    return payload


def _object(
    root: Path,
    path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    try:
        value: object = json.loads(_bytes(root, path, expected_sha256))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DesignError(
            "C4_PARAGRAPH_ORDER_DESIGN_AUTHORITY_INVALID",
            "required authority is not valid JSON",
            path.as_posix(),
        ) from error

    if not isinstance(value, dict):
        raise DesignError(
            "C4_PARAGRAPH_ORDER_DESIGN_AUTHORITY_INVALID",
            "required authority root is not an object",
            path.as_posix(),
        )

    return cast(dict[str, object], value)


def _require(
    mapping: dict[str, object],
    expected: dict[str, object],
    label: str,
) -> None:
    for key, expected_value in expected.items():
        if mapping.get(key) != expected_value:
            raise DesignError(
                "C4_PARAGRAPH_ORDER_DESIGN_AUTHORITY_SEMANTIC_DRIFT",
                f"{label}.{key} drifted",
                key,
            )


def _base_commit_is_ancestor_of_head(root: Path) -> bool:
    result = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            BASE_MAIN_COMMIT,
            "HEAD",
        ],
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
        "C4_PARAGRAPH_ORDER_DESIGN_GIT_STATE_INVALID",
        "unable to verify frozen design base ancestry",
    )


def _validate_semantics(root: Path) -> None:
    if not _base_commit_is_ancestor_of_head(root):
        raise DesignError(
            "C4_PARAGRAPH_ORDER_DESIGN_BASE_MAIN_DRIFT",
            "frozen design base is not an ancestor of current HEAD",
        )

    disposition = _object(
        root,
        C4_DISPOSITION_RECORD_PATH,
        C4_DISPOSITION_RECORD_SHA256,
    )
    _require(
        disposition,
        {
            "status": ("DISPOSITIONED_VALID_GOVERNED_C4_NOT_QUALIFIED_EXECUTION"),
            "execution_valid": True,
            "observed_c4_state": "NOT_QUALIFIED",
            "observation_count": 3,
            "exact_object_count": 0,
            "required_exact_object_count": 3,
            "valid_json_count": 3,
            "finish_reason_stop_count": 3,
            "http_200_count": 3,
            "zero_cache_baseline_count": 3,
            "worker_identity_cardinality": 3,
            "identical_nonqualifying_response_identity": True,
            "canonical_parsed_object_sha256": (HISTORICAL_CONTROL_PARSED_OBJECT_SHA256),
            "full_prompt_token_count": 899,
            "reusable_prefix_token_count": 880,
            "hidden_retries": 0,
            "external_network_requests": 0,
            "external_spend": 0,
            "teardown_passed": True,
            "scratch_cleanup_passed": True,
            "new_execution_authorized": False,
            "authorization_reusable": False,
        },
        "C4 disposition",
    )

    review = _object(
        root,
        C4_DISPOSITION_REVIEW_PATH,
        C4_DISPOSITION_REVIEW_SHA256,
    )
    _require(
        review,
        {
            "status": "APPROVED_GOVERNED_C4_NOT_QUALIFIED_DISPOSITION",
            "record_sha256": C4_DISPOSITION_RECORD_SHA256,
            "execution_valid": True,
            "c4_qualified_claimed": False,
            "root_cause_claimed": False,
            "new_execution_authorized": False,
        },
        "C4 disposition review",
    )

    _bytes(root, C4_RUNTIME_PATH, C4_RUNTIME_SHA256)
    _bytes(root, CANONICAL_CORPUS_PATH, CANONICAL_CORPUS_SHA256)
    _bytes(
        root,
        C4_QUALIFICATION_REQUEST_PATH,
        C4_QUALIFICATION_REQUEST_SHA256,
    )
    _bytes(
        root,
        EXECUTION_AUTHORIZATION_ARCHITECTURE_PATH,
        EXECUTION_AUTHORIZATION_ARCHITECTURE_SHA256,
    )


def validate_authorities(
    root: Path,
) -> tuple[AuthorityReceipt, ...]:
    _validate_semantics(root)

    return tuple(
        AuthorityReceipt(
            role=role,
            path=path.as_posix(),
            sha256=expected_sha256,
        )
        for role, path, expected_sha256 in AUTHORITY_SPECS
    )


def build_design_record(root: Path) -> DesignRecord:
    authorities = validate_authorities(root)

    conditions = (
        ConditionDefinition(
            condition_id=ConditionId.CONTROL,
            role="CONTEMPORANEOUS_FAILURE_ANCHOR",
            prompt_token_count=PROMPT_TOKEN_COUNT,
            prompt_token_sha256=CONTROL_TOKEN_SHA256,
            paragraph_count=PARAGRAPH_COUNT,
            paragraph_order=CONTROL_PARAGRAPH_ORDER,
            final_user_boundary=FINAL_USER_BOUNDARY,
            message_boundary_profile=MESSAGE_BOUNDARY_PROFILE,
            historical_exact_object_result="0_OF_3",
            historical_canonical_parsed_object_sha256=(HISTORICAL_CONTROL_PARSED_OBJECT_SHA256),
        ),
        ConditionDefinition(
            condition_id=ConditionId.TREATMENT,
            role="ORDER_INTERVENTION",
            prompt_token_count=PROMPT_TOKEN_COUNT,
            prompt_token_sha256=TREATMENT_TOKEN_SHA256,
            paragraph_count=PARAGRAPH_COUNT,
            paragraph_order=TREATMENT_PARAGRAPH_ORDER,
            final_user_boundary=FINAL_USER_BOUNDARY,
            message_boundary_profile=MESSAGE_BOUNDARY_PROFILE,
            historical_exact_object_result="NOT_EXECUTED",
            historical_canonical_parsed_object_sha256=None,
        ),
    )

    request_plan = tuple(
        RequestPlanItem(
            ordinal=index,
            condition_id=ConditionId(condition_id),
        )
        for index, condition_id in enumerate(
            OBSERVATION_ORDER,
            start=1,
        )
    )

    decision_rules = (
        DecisionRule(
            state=(DecisionState.CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE),
            condition=(
                "Contemporaneous control is not 0/3 exact, is not valid JSON "
                "3/3, or does not reproduce the historical stable parsed-object "
                "identity."
            ),
            implication=(
                "The historical C4 failure anchor did not reproduce; treatment "
                "is not used for a paragraph-order causal inference."
            ),
        ),
        DecisionRule(
            state=DecisionState.ORDER_INTERVENTION_RESTORES_BEHAVIOR,
            condition=("Control anchor reproduces and treatment is 3/3 exact-object true."),
            implication=(
                "This paragraph-order intervention changed behavior while the "
                "frozen static isolation invariants remained fixed. No root-cause "
                "claim is established."
            ),
        ),
        DecisionRule(
            state=(DecisionState.ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE),
            condition=(
                "Control anchor reproduces; treatment is 0/3 exact and its "
                "stable canonical parsed-object SHA256 equals the historical "
                "control parsed-object SHA256."
            ),
            implication=(
                "This paragraph-order intervention did not change the observed "
                "deterministic failure phenotype."
            ),
        ),
        DecisionRule(
            state=DecisionState.ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE,
            condition=(
                "Control anchor reproduces; treatment is 0/3 exact, is internally "
                "stable, and has a different canonical parsed-object SHA256."
            ),
            implication=(
                "Paragraph order changed the deterministic failure phenotype "
                "without restoring the required object."
            ),
        ),
        DecisionRule(
            state=DecisionState.ORDER_INTERVENTION_EFFECT_AMBIGUOUS,
            condition=(
                "Control anchor reproduces but treatment has mixed exact results, "
                "non-stable parsed-object identity, or otherwise inconsistent "
                "healthy observations."
            ),
            implication=("No paragraph-order behavioral claim is permitted."),
        ),
        DecisionRule(
            state=DecisionState.DIAGNOSTIC_INVALID,
            condition=(
                "Authority, runtime, platform, setup, request, teardown, cleanup, "
                "or evidence-integrity prerequisites fail."
            ),
            implication=("Execution is invalid for behavioral inference."),
        ),
    )

    return DesignRecord(
        record_id=("auragateway-c4-paragraph-order-behavioral-differential-design-v1"),
        design_status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=authorities,
        runtime=RuntimeIdentity(
            model_repository="Qwen/Qwen2.5-0.5B-Instruct",
            model_revision=("7ae557604adf67be50417f59c2c2f167def9a775"),
            tokenizer_revision=("7ae557604adf67be50417f59c2c2f167def9a775"),
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
            prefix_caching_enabled=True,
            cache_block_size=16,
            max_model_len=4096,
        ),
        generation_controls=GenerationControls(
            temperature=0,
            top_p=1,
            repetition_penalty=1.1,
            seed=7,
            max_tokens=32,
            stream=False,
            response_format_present=False,
            output_mode="UNCONSTRAINED",
        ),
        frozen_composition=FrozenComposition(
            message_roles=("system", "user", "assistant", "user"),
            system_instruction=SYSTEM_INSTRUCTION,
            assistant_acknowledgement=ASSISTANT_ACKNOWLEDGEMENT,
            final_object_canonical=FINAL_OBJECT_CANONICAL,
            final_object_sha256=EXPECTED_OBJECT_SHA256,
            prompt_token_count_per_condition=PROMPT_TOKEN_COUNT,
            final_user_boundary_per_condition=FINAL_USER_BOUNDARY,
            message_boundary_profile_per_condition=MESSAGE_BOUNDARY_PROFILE,
            no_schema_or_guided_decoding=True,
        ),
        static_isolation_evidence=StaticIsolationEvidence(
            evidence_status=(
                "OPERATOR_OBSERVED_OFFLINE_STATIC_ORACLE_NOT_REEXECUTED_BY_DESIGN_PRODUCER"
            ),
            observed_date="2026-08-20",
            control_prompt_token_sha256=CONTROL_TOKEN_SHA256,
            treatment_prompt_token_sha256=TREATMENT_TOKEN_SHA256,
            prompt_token_count_equal=True,
            token_id_multiset_identical=True,
            final_user_boundary_equal=True,
            message_boundary_profile_equal=True,
            common_suffix_token_count=(CONTROL_TREATMENT_COMMON_SUFFIX_TOKEN_COUNT),
            control_paragraph_order=CONTROL_PARAGRAPH_ORDER,
            treatment_paragraph_order=TREATMENT_PARAGRAPH_ORDER,
            first_paragraph_preserved=True,
            last_paragraph_preserved=True,
            paragraph_content_multiset_preserved=True,
            character_count_preserved=True,
            producer_reexecutes_tokenizer=False,
        ),
        conditions=conditions,
        starting_state=StartingStateContract(
            strategy="FRESH_WORKER_PROCESS_PER_OBSERVATION",
            prior_request_cache_carryover_permitted=False,
            require_fresh_worker_identity=True,
            require_zero_cached_prefix_baseline=True,
            teardown_required_between_observations=True,
            teardown_failure_invalidates_diagnostic=True,
        ),
        request_plan=request_plan,
        execution_budget=ExecutionBudget(),
        primary_endpoint=PrimaryEndpoint(
            field="exact_object",
            observations_per_condition=3,
            pass_state="3_OF_3_EXACT_OBJECT_TRUE",
            fail_state="0_OF_3_EXACT_OBJECT_TRUE",
            mixed_state="1_OR_2_OF_3_EXACT_OBJECT_TRUE",
        ),
        decision_rules=decision_rules,
        safety=Safety(),
        next_gate=NEXT_GATE,
        non_claims=(
            "Paragraph order is not established as the root cause.",
            "The canonical corpus is not globally invalidated by this design.",
            "Structural diversity is not claimed to be monotonic with behavior.",
            "Repetition penalty is not established as a causal mechanism.",
            "The model is not claimed to produce the correct answer generally.",
            "P5 cache behavior is not requalified.",
            "P6 worker-state isolation is not requalified.",
            "Final A/B/C effects are not measured.",
            "Production readiness is not established.",
            "This design does not authorize any new execution.",
        ),
    )


def generate(root: Path) -> DesignRecord:
    record = build_design_record(root)
    path = root / RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(record))
    return record


def validate_generated(root: Path) -> DesignRecord:
    expected = build_design_record(root)
    path = _file(root, RECORD_PATH)
    observed = path.read_bytes()

    if observed != _canonical(expected):
        raise DesignError(
            "C4_PARAGRAPH_ORDER_DESIGN_RECORD_DRIFT",
            "generated design record drifted from deterministic producer output",
            RECORD_PATH.as_posix(),
        )

    return expected


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=("generate", "validate"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()

    try:
        if args.mode == "generate":
            generate(root)
            print("C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_DESIGN=GENERATED")
            print(f"RECORD={RECORD_PATH.as_posix()}")
            print("NEW_EXECUTION_AUTHORIZED=false")
            print("MODEL_REQUESTS_PERFORMED=0")
            print("GPU_EXECUTION_PERFORMED=false")
            print("KAGGLE_EXECUTION_PERFORMED=false")
            return 0

        validate_generated(root)
        print("C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_DESIGN=PASS")
        print(f"RECORD={RECORD_PATH.as_posix()}")
        print("NEW_EXECUTION_AUTHORIZED=false")
        print("MODEL_REQUESTS_PERFORMED=0")
        print("GPU_EXECUTION_PERFORMED=false")
        print("KAGGLE_EXECUTION_PERFORMED=false")
        return 0

    except DesignError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
