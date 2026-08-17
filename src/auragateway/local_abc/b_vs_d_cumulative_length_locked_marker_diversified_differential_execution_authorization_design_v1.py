"""Freeze B-vs-D differential execution-authorization design V1.

Design-only control-plane infrastructure. This module binds a future
transaction-bound single-use authorization issuer to the exact merged B-vs-D
experiment design and implementation. It issues no live authority and performs
no runtime execution.
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

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

BASE_MAIN_COMMIT: Final = "a24eedc9d7a65756affc9cde224acdc80fdf7313"
IMPLEMENTATION_MERGE_COMMIT: Final = BASE_MAIN_COMMIT

EXPERIMENT_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_design_v1.json"
)
EXPERIMENT_DESIGN_SHA256: Final = "2e07651681d98d604f0e0f6b4e8964906f39b8bfa0e48b8f8fa8e9de431e7ef9"
SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39"
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "7278fdf91cef5fd2a19e39f4bc34421c2dce823a42e09aacc7c44ccce7fb53dc"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "795a7cdf5285ba49e5dcc57a76cd46e03f07121359a5f66101692cee41bb2074"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "b337da7299e47f7c1b0d691886a505ea2655159e6426f863f699777f7f31cb1c"
)
IMPLEMENTATION_TEST_SHA256: Final = (
    "bf61b407eef10b8233084e802128834306676008906dc048c6e3d9bc62f28f77"
)

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_execution_authorization_design_v1.json"
)

AUTHORIZATION_ARCHITECTURE: Final = "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
AUTHORIZATION_SCOPE: Final = "B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
NEXT_GATE: Final = (
    "IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_"
    "DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1"
)

B_CONDITION: Final = "B_NEUTRAL_REPEATED_24X"
D_CONDITION: Final = "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED"
REQUEST_ORDER: Final = (
    B_CONDITION,
    D_CONDITION,
    D_CONDITION,
    B_CONDITION,
    B_CONDITION,
    D_CONDITION,
)
CUMULATIVE_PROMPT_TOKEN_PROFILE: Final = (
    83,
    117,
    151,
    185,
    219,
    253,
    287,
    321,
    355,
    389,
    423,
    457,
    491,
    525,
    559,
    593,
    627,
    661,
    695,
    729,
    763,
    797,
    831,
    865,
    899,
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


class AuthorizationDesignError(RuntimeError):
    """Metadata-safe fail-closed authorization-design error."""

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


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationDesignError("B_VS_D_AUTHORIZATION_DESIGN_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TerminalDisposition(StrEnum):
    CONSUMED = "CONSUMED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    EXPIRED_UNUSED = "EXPIRED_UNUSED"
    CANCELLED_UNUSED = "CANCELLED_UNUSED"
    ABANDONED_BEFORE_EXECUTION = "ABANDONED_BEFORE_EXECUTION"


class ArtifactAuthority(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)
    current_authority: Literal[True] = True


class RuntimeModelContract(FrozenModel):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    required_native_module: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    attention_backend: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    gpu_topology: Literal["T4_x2"] = "T4_x2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_directory_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    prefix_caching_enabled: Literal[True] = True
    cache_block_size: Literal[16] = 16
    max_model_len: Literal[4096] = 4096
    worker_gpu_index: Literal[0] = 0


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[6] = 6
    maximum_model_loads: Literal[6] = 6
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_observations: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class HumanAuthorizationContract(FrozenModel):
    fresh_human_authority_required: Literal[True] = True
    confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"] = (
        "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    )
    challenge_must_be_dynamic: Literal[True] = True
    exact_challenge_retype_required: Literal[True] = True
    confirmation_binds_exact_authorization_intent: Literal[True] = True
    challenge_synthesis_by_runtime_prohibited: Literal[True] = True
    challenge_synthesis_by_model_prohibited: Literal[True] = True
    challenge_synthesis_by_issuer_prohibited: Literal[True] = True
    challenge_synthesis_by_assistant_prohibited: Literal[True] = True
    maximum_confirmation_age_minutes: Literal[15] = 15
    default_authorization_window_minutes: Literal[180] = 180
    maximum_authorization_window_minutes: Literal[240] = 240


class PlatformContract(FrozenModel):
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    preissuance_platform_observation_required: Literal[False] = False
    fresh_post_artifact_observation_required: Literal[True] = True
    observation_precedes_save_and_run_all: Literal[True] = True
    observation_mounted_as_runtime_input: Literal[False] = False
    machine_observable_runtime_topology_check_required: Literal[True] = True


class PlatformObservationReceiptContract(FrozenModel):
    control_id: Literal["PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"] = (
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    )
    durable_receipt_required: Literal[True] = True
    receipt_must_exist_before_save_and_run_all: Literal[True] = True
    receipt_bound_to_transaction_id: Literal[True] = True
    receipt_created_after_transaction_artifact: Literal[True] = True
    receipt_runtime_input: Literal[False] = False
    console_only_observation_sufficient: Literal[False] = False
    failure_to_persist_blocks_execution: Literal[True] = True
    required_fields: tuple[str, ...] = (
        "transaction_id",
        "platform_observed_at",
        "accelerator",
        "allocated_gpu_count",
        "internet_enabled",
        "capability_source",
    )

    @model_validator(mode="after")
    def validate_required_fields(self) -> Self:
        expected = (
            "transaction_id",
            "platform_observed_at",
            "accelerator",
            "allocated_gpu_count",
            "internet_enabled",
            "capability_source",
        )
        if self.required_fields != expected:
            raise ValueError("platform-observation receipt fields drifted")
        return self


class TransportTopology(FrozenModel):
    authorization_specific_kaggle_inputs: Literal[0] = 0
    authorization_producer_notebooks: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    runtime_authorization_filename_discovery_permitted: Literal[False] = False
    permitted_kaggle_input_roles: tuple[
        Literal["durable_runtime"],
        Literal["model_snapshot"],
    ] = ("durable_runtime", "model_snapshot")


class TransactionIdentityContract(FrozenModel):
    transaction_id_derivation: Literal["SHA256_CANONICAL_AUTHORIZATION_BYTES"] = (
        "SHA256_CANONICAL_AUTHORIZATION_BYTES"
    )
    canonical_authorization_bytes_bound: Literal[True] = True
    runtime_payload_sha256_bound: Literal[True] = True
    generator_contract_sha256_bound: Literal[True] = True
    deterministic_artifact_generation_required: Literal[True] = True
    whole_notebook_sha256_is_semantic_payload_identity: Literal[False] = False
    nonidentical_regeneration_requires_fresh_authority: Literal[True] = True


class AuthorizationPayloadBindingContract(FrozenModel):
    authorization_scope_bound: Literal[True] = True
    authorization_design_record_sha256_bound: Literal[True] = True
    issuer_merge_commit_bound: Literal[True] = True
    implementation_merge_commit_bound: Literal[True] = True
    frozen_experiment_design_authority_bound: Literal[True] = True
    implementation_authority_hashes_bound: Literal[True] = True
    runtime_model_contract_bound: Literal[True] = True
    execution_budget_bound: Literal[True] = True
    differential_experiment_contract_bound: Literal[True] = True
    required_platform_policy_bound: Literal[True] = True
    authorization_window_bound: Literal[True] = True


class RuntimeAdmissionContract(FrozenModel):
    static_repository_runtime_execution_permitted: Literal[False] = False
    transaction_bound_executable_required: Literal[True] = True
    authorization_admission_precedes_runtime_installation: Literal[True] = True
    authorization_must_be_live_at_admission: Literal[True] = True
    admitted_execution_may_finish_after_expiry: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False


class DifferentialExperimentContract(FrozenModel):
    experiment_id: Literal["B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"] = (
        "B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
    )
    variable_under_test: Literal[
        "MARKER_DIVERSIFICATION_UNDER_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"
    ] = "MARKER_DIVERSIFICATION_UNDER_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"
    condition_b_id: Literal["B_NEUTRAL_REPEATED_24X"] = B_CONDITION
    condition_d_id: Literal["D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED"] = (
        D_CONDITION
    )
    request_order: tuple[str, ...] = REQUEST_ORDER
    observations_per_condition: Literal[3] = 3
    prompt_token_count_per_condition: Literal[899] = 899
    segment_count_per_condition: Literal[24] = 24
    cumulative_prompt_token_count_profile: tuple[int, ...] = CUMULATIVE_PROMPT_TOKEN_PROFILE
    cumulative_prompt_token_increment: Literal[34] = 34
    complete_cumulative_prompt_token_profile_locked: Literal[True] = True
    fresh_worker_process_per_observation: Literal[True] = True
    zero_cached_prefix_baseline_required: Literal[True] = True
    teardown_required_between_observations: Literal[True] = True
    prior_request_cache_carryover_permitted: Literal[False] = False
    pre_request_token_identity_journal_required: Literal[True] = True
    pre_request_identity_persisted_before_model_request_budget: Literal[True] = True
    invalid_json_retained_as_observation: Literal[True] = True

    b_token_sha256: Literal["02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"] = (
        "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
    )
    b_payload_sha256: Literal[
        "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
    ] = "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
    d_token_sha256: Literal["878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21"] = (
        "878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21"
    )
    d_payload_sha256: Literal[
        "0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010"
    ] = "0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010"
    d_marker_sequence: tuple[str, ...] = D_MARKERS

    message_roles: tuple[str, ...] = ("system", "user", "assistant", "user")
    canonical_final_object: Literal['{"probe":"exact-runtime-p5-p6","value":1}'] = (
        '{"probe":"exact-runtime-p5-p6","value":1}'
    )
    maximum_output_tokens: Literal[32] = 32
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    repetition_penalty: float = Field(default=1.1, ge=1.1, le=1.1, strict=True)
    seed: Literal[7] = 7
    stream: Literal[False] = False
    response_format_present: Literal[False] = False
    output_mode: Literal["UNCONSTRAINED"] = "UNCONSTRAINED"

    b_0_d_3: Literal["MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"] = (
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
    )
    b_0_d_0: Literal["MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL"] = (
        "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL"
    )
    b_0_d_mixed: Literal["D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"] = (
        "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"
    )
    b_anchor_nonreproduction: Literal["B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"] = (
        "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
    )
    invariant_failure: Literal["DIAGNOSTIC_INVALID"] = "DIAGNOSTIC_INVALID"

    b_anchor_must_reproduce_zero_of_three: Literal[True] = True
    mixed_result_permits_mechanistic_claim: Literal[False] = False
    post_hoc_two_of_three_interpretation_permitted: Literal[False] = False
    text_segment_boundary_must_equal_token_boundary: Literal[False] = False
    bounded_marker_lexical_semantic_novelty_remains: Literal[True] = True
    exact_repetition_sole_or_root_cause_claim_permitted: Literal[False] = False
    aligned_block_recurrence_causal_claim_permitted: Literal[False] = False
    marker_lexical_novelty_eliminated: Literal[False] = False
    marker_semantic_novelty_eliminated: Literal[False] = False
    threshold_search_authorized: Literal[False] = False
    runtime_remediation_authorized: Literal[False] = False
    p5_p6_requalification_authorized: Literal[False] = False
    north_star_abc_effect_claim_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.request_order != REQUEST_ORDER:
            raise ValueError("B-vs-D request order drifted")
        if self.request_order.count(B_CONDITION) != 3:
            raise ValueError("B observation count drifted")
        if self.request_order.count(D_CONDITION) != 3:
            raise ValueError("D observation count drifted")
        if self.cumulative_prompt_token_count_profile != CUMULATIVE_PROMPT_TOKEN_PROFILE:
            raise ValueError("cumulative prompt-token profile drifted")
        increments = tuple(
            right - left
            for left, right in zip(
                self.cumulative_prompt_token_count_profile,
                self.cumulative_prompt_token_count_profile[1:],
                strict=False,
            )
        )
        if increments != (34,) * 24:
            raise ValueError("cumulative prompt-token increments drifted")
        if self.d_marker_sequence != D_MARKERS:
            raise ValueError("D marker sequence drifted")
        return self


class EvidenceContract(FrozenModel):
    expected_evidence_zip: Literal[
        "ag-b-vs-d-cumulative-length-locked-marker-diversified-differential-evidence-v1.zip"
    ] = "ag-b-vs-d-cumulative-length-locked-marker-diversified-differential-evidence-v1.zip"
    pre_request_token_identity_journal: Literal["pre_request_token_identity_journal_v1.json"] = (
        "pre_request_token_identity_journal_v1.json"
    )
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    platform_observation_bound_to_transaction: Literal[True] = True
    saved_version_bound_to_transaction: Literal[True] = True
    evidence_identity_bound_to_terminal_receipt: Literal[True] = True
    terminalizable_without_expected_evidence_zip: Literal[True] = True


class TerminalizationContract(FrozenModel):
    terminal_dispositions: tuple[TerminalDisposition, ...] = (
        TerminalDisposition.CONSUMED,
        TerminalDisposition.OUTCOME_UNKNOWN,
        TerminalDisposition.EXPIRED_UNUSED,
        TerminalDisposition.CANCELLED_UNUSED,
        TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
    )
    attempted_execution_terminalizes_authority: Literal[True] = True
    terminal_authorization_reusable: Literal[False] = False
    secondary_failure_may_mask_primary_failure: Literal[False] = False
    multiple_observed_executions_invalidate_acceptance: Literal[True] = True
    runtime_anti_replay_established: Literal[False] = False
    malicious_operator_resistance_established: Literal[False] = False


class AuthorizationDesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    design_id: Literal[
        "auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-"
        "execution-authorization-design-v1"
    ]
    status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["a24eedc9d7a65756affc9cde224acdc80fdf7313"]
    implementation_merge_commit: Literal["a24eedc9d7a65756affc9cde224acdc80fdf7313"]
    authorization_architecture: Literal["TRANSACTION_BOUND_EXECUTION_ARTIFACT"]
    authorization_scope: Literal[
        "B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
    ]
    authorities: tuple[ArtifactAuthority, ...]
    runtime_model: RuntimeModelContract
    execution_budget: ExecutionBudget
    human_authorization: HumanAuthorizationContract
    platform: PlatformContract
    platform_observation_receipt: PlatformObservationReceiptContract
    transport_topology: TransportTopology
    transaction_identity: TransactionIdentityContract
    authorization_payload_binding: AuthorizationPayloadBindingContract
    runtime_admission: RuntimeAdmissionContract
    experiment: DifferentialExperimentContract
    evidence: EvidenceContract
    terminalization: TerminalizationContract
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    model_loads_performed: Literal[0] = 0
    worker_starts_performed: Literal[0] = 0
    kaggle_execution_performed: Literal[False] = False
    governed_executable_generated: Literal[False] = False
    platform_observation_persisted: Literal[False] = False
    next_gate: Literal[
        "IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_"
        "DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1"
    ]

    @model_validator(mode="after")
    def validate_authority_roles(self) -> Self:
        roles = tuple(authority.role for authority in self.authorities)
        expected = (
            "frozen_experiment_design",
            "merged_successor_runtime",
            "implementation_review",
            "implementation_record",
        )
        if roles != expected:
            raise ValueError("authorization authority roles drifted")
        return self


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _read_authority(
    root: Path,
    role: str,
    path: Path,
    expected_sha256: str,
) -> tuple[ArtifactAuthority, bytes]:
    absolute = root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_AUTHORITY_MISSING",
            "required merged B-vs-D authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    observed = _sha256(payload)
    if observed != expected_sha256:
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_AUTHORITY_IDENTITY_DRIFT",
            "required merged B-vs-D authority identity drifted",
            path.as_posix(),
        )
    return (
        ArtifactAuthority(
            role=role,
            path=path.as_posix(),
            sha256=observed,
            size_bytes=len(payload),
        ),
        payload,
    )


def _require_base_ancestor(root: Path) -> None:
    completed = subprocess.run(
        ("git", "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_ANCESTRY_DRIFT",
            "authorization-design base commit is not an ancestor of HEAD",
        )


def _mapping(payload: bytes, path: Path) -> dict[str, object]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "bound authority is not a JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _require_equal(
    observed: object,
    expected: object,
    field: str,
    path: Path,
) -> None:
    if observed != expected:
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            f"bound authority field drifted: {field}",
            path.as_posix(),
        )


def _validate_design_semantics(payload: bytes) -> None:
    value = _mapping(payload, EXPERIMENT_DESIGN_PATH)
    _require_equal(
        value.get("design_status"),
        "DESIGN_FROZEN_NOT_EXECUTED",
        "design_status",
        EXPERIMENT_DESIGN_PATH,
    )
    request_plan = value.get("request_plan")
    if not isinstance(request_plan, list):
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "request_plan is not an array",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    observed_order = tuple(
        item.get("condition_id") for item in request_plan if isinstance(item, dict)
    )
    _require_equal(observed_order, REQUEST_ORDER, "request_plan", EXPERIMENT_DESIGN_PATH)
    generation = value.get("generation_controls")
    if not isinstance(generation, dict):
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "generation_controls is not an object",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    expected_generation = {
        "max_tokens": 32,
        "output_mode": "UNCONSTRAINED",
        "repetition_penalty": 1.1,
        "response_format_present": False,
        "seed": 7,
        "stream": False,
        "temperature": 0,
        "top_p": 1,
    }
    _require_equal(generation, expected_generation, "generation_controls", EXPERIMENT_DESIGN_PATH)
    rules = value.get("decision_rules")
    if not isinstance(rules, list):
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "decision_rules is not an array",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    states = tuple(item.get("state") for item in rules if isinstance(item, dict))
    expected_states = (
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK",
        "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL",
        "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM",
        "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE",
        "DIAGNOSTIC_INVALID",
    )
    _require_equal(states, expected_states, "decision_rules", EXPERIMENT_DESIGN_PATH)


def _validate_review_semantics(payload: bytes) -> None:
    value = _mapping(payload, IMPLEMENTATION_REVIEW_PATH)
    expected = {
        "status": "APPROVED_STATIC_SUCCESSOR_IMPLEMENTATION",
        "design_record_sha256": EXPERIMENT_DESIGN_SHA256,
        "runtime_payload_sha256": SUCCESSOR_RUNTIME_SHA256,
        "implementation_source_sha256": IMPLEMENTATION_SOURCE_SHA256,
        "focused_test_sha256": IMPLEMENTATION_TEST_SHA256,
        "request_order": list(REQUEST_ORDER),
        "observations_per_condition": 3,
        "prompt_token_count_per_condition": 899,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "maximum_hidden_retries": 0,
        "maximum_replacement_observations": 0,
        "fresh_worker_process_per_observation": True,
        "b_anchor_reproduction_rule_preserved": True,
        "cumulative_prompt_token_profile_contract_preserved": True,
        "text_boundary_token_boundary_assumption_used": False,
        "invalid_json_retained_as_observation": True,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
    }
    for field, expected_value in expected.items():
        _require_equal(value.get(field), expected_value, field, IMPLEMENTATION_REVIEW_PATH)


def _validate_record_semantics(payload: bytes) -> None:
    value = _mapping(payload, IMPLEMENTATION_RECORD_PATH)
    expected = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "design_record_sha256": EXPERIMENT_DESIGN_SHA256,
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "model_requests_performed": 0,
        "model_loads_performed": 0,
        "worker_starts_performed": 0,
        "kaggle_execution_performed": False,
        "gpu_execution_performed": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "runtime_fix_authorized": False,
        "threshold_search_authorized": False,
        "p5_p6_requalification_authorized": False,
        "measured_abc_execution_authorized": False,
    }
    for field, expected_value in expected.items():
        _require_equal(value.get(field), expected_value, field, IMPLEMENTATION_RECORD_PATH)


def build_record(root: Path) -> AuthorizationDesignRecord:
    root = root.resolve()
    design_authority, design_payload = _read_authority(
        root,
        "frozen_experiment_design",
        EXPERIMENT_DESIGN_PATH,
        EXPERIMENT_DESIGN_SHA256,
    )
    runtime_authority, _ = _read_authority(
        root,
        "merged_successor_runtime",
        SUCCESSOR_RUNTIME_PATH,
        SUCCESSOR_RUNTIME_SHA256,
    )
    review_authority, review_payload = _read_authority(
        root,
        "implementation_review",
        IMPLEMENTATION_REVIEW_PATH,
        IMPLEMENTATION_REVIEW_SHA256,
    )
    record_authority, record_payload = _read_authority(
        root,
        "implementation_record",
        IMPLEMENTATION_RECORD_PATH,
        IMPLEMENTATION_RECORD_SHA256,
    )
    _validate_design_semantics(design_payload)
    _validate_review_semantics(review_payload)
    _validate_record_semantics(record_payload)
    return AuthorizationDesignRecord(
        design_id=(
            "auragateway-b-vs-d-cumulative-length-locked-marker-diversified-"
            "differential-execution-authorization-design-v1"
        ),
        status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        authorization_architecture=AUTHORIZATION_ARCHITECTURE,
        authorization_scope=AUTHORIZATION_SCOPE,
        authorities=(
            design_authority,
            runtime_authority,
            review_authority,
            record_authority,
        ),
        runtime_model=RuntimeModelContract(),
        execution_budget=ExecutionBudget(),
        human_authorization=HumanAuthorizationContract(),
        platform=PlatformContract(),
        platform_observation_receipt=PlatformObservationReceiptContract(),
        transport_topology=TransportTopology(),
        transaction_identity=TransactionIdentityContract(),
        authorization_payload_binding=AuthorizationPayloadBindingContract(),
        runtime_admission=RuntimeAdmissionContract(),
        experiment=DifferentialExperimentContract(),
        evidence=EvidenceContract(),
        terminalization=TerminalizationContract(),
        next_gate=NEXT_GATE,
    )


def render_record(root: Path) -> bytes:
    return _canonical_json_bytes(build_record(root))


def generate(root: Path) -> dict[str, object]:
    root = root.resolve()
    payload = render_record(root)
    output = root / DESIGN_RECORD_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return {
        "status": "B_VS_D_EXECUTION_AUTHORIZATION_DESIGN_GENERATED",
        "design_record_sha256": _sha256(payload),
        "authorization_architecture": AUTHORIZATION_ARCHITECTURE,
        "authorization_scope": AUTHORIZATION_SCOPE,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_base_ancestor(root)
    expected = render_record(root)
    path = root / DESIGN_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_RECORD_MISSING",
            "authorization-design record is missing or unsafe",
            DESIGN_RECORD_PATH.as_posix(),
        )
    observed = path.read_bytes()
    if observed != expected:
        raise AuthorizationDesignError(
            "B_VS_D_AUTHORIZATION_DESIGN_RECORD_DRIFT",
            "authorization-design record does not match deterministic rendering",
            DESIGN_RECORD_PATH.as_posix(),
        )
    record = AuthorizationDesignRecord.model_validate_json(observed)
    return {
        "status": "B_VS_D_EXECUTION_AUTHORIZATION_DESIGN_VALID",
        "design_record_sha256": _sha256(observed),
        "authorization_architecture": record.authorization_architecture,
        "authorization_scope": record.authorization_scope,
        "authority_count": len(record.authorities),
        "maximum_model_requests": record.execution_budget.maximum_model_requests,
        "maximum_worker_starts": record.execution_budget.maximum_worker_starts,
        "maximum_model_loads": record.execution_budget.maximum_model_loads,
        "maximum_hidden_retries": record.execution_budget.maximum_hidden_retries,
        "observations_per_condition": record.experiment.observations_per_condition,
        "prompt_token_count_per_condition": record.experiment.prompt_token_count_per_condition,
        "cumulative_prompt_token_profile_locked": (
            record.experiment.complete_cumulative_prompt_token_profile_locked
        ),
        "durable_platform_observation_required": (
            record.platform_observation_receipt.durable_receipt_required
        ),
        "human_confirmation_method": record.human_authorization.confirmation_method,
        "authorization_specific_kaggle_inputs": (
            record.transport_topology.authorization_specific_kaggle_inputs
        ),
        "live_authorization_issued": record.live_authorization_issued,
        "runtime_execution_authorized": record.runtime_execution_authorized,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "generate":
            result = generate(Path(args.repo_root))
        if args.command == "validate":
            result = validate(Path(args.repo_root))
    except (
        AuthorizationDesignError,
        ValidationError,
        json.JSONDecodeError,
        OSError,
    ) as error:
        if isinstance(error, AuthorizationDesignError):
            code = error.error_code
            message = error.safe_message
            path = error.path
        if not isinstance(error, AuthorizationDesignError):
            code = "B_VS_D_AUTHORIZATION_DESIGN_VALIDATION_FAILED"
            message = str(error)
            path = None
        print(
            json.dumps(
                {"error_code": code, "safe_message": message, "path": path},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
