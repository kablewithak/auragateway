"""Freeze C4 paragraph-order differential execution-authorization design V1.

Design-only control-plane infrastructure. This module binds a future
transaction-bound single-use authorization issuer to the exact merged C4
paragraph-order behavioral differential design and implementation. It issues no
live authority and performs no runtime execution.
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

BASE_MAIN_COMMIT: Final = "7e037596de1a74038583a85ed81d46ec12debbac"
IMPLEMENTATION_MERGE_COMMIT: Final = BASE_MAIN_COMMIT

EXPERIMENT_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_paragraph_order_behavioral_differential_design_v1.json"
)
EXPERIMENT_DESIGN_SHA256: Final = "92bd8194cea68783116bc934b57ae0b1b3a675d0a0ad7dabfa05c680a4755ce9"
SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/c4_paragraph_order_behavioral_differential_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "96f46fc83e34bc83884479bddf769204bba5bb49f38b927386f824ab7f103c5b"
)
IMPLEMENTATION_TEST_SHA256: Final = (
    "f9ad99abc924ec4c456eafbf9b83cf5218bee83106fb55d9fea429ddee10463a"
)

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_design_v1.json"
)

AUTHORIZATION_ARCHITECTURE: Final = "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
AUTHORIZATION_SCOPE: Final = "C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
NEXT_GATE: Final = (
    "IMPLEMENT_AND_MERGE_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_"
    "EXECUTION_AUTHORIZATION_ISSUER_V1"
)

CONTROL_CONDITION: Final = "CONTROL_ORIGINAL_C4"
TREATMENT_CONDITION: Final = "TREATMENT_REVERSED_MIDDLE_EIGHT"
REQUEST_ORDER: Final = (
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
    TREATMENT_CONDITION,
    CONTROL_CONDITION,
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
)
CONTROL_PARAGRAPH_ORDER: Final = tuple(range(1, 11))
TREATMENT_PARAGRAPH_ORDER: Final = (1, 9, 8, 7, 6, 5, 4, 3, 2, 10)
MESSAGE_BOUNDARY_PROFILE: Final = (3, 28, 869, 880)
CONTROL_TOKEN_SHA256: Final = "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
TREATMENT_TOKEN_SHA256: Final = "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
CONTROL_PAYLOAD_SHA256: Final = "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
TREATMENT_PAYLOAD_SHA256: Final = "47c519c24efd40e3bab4bfa2eaec1cf3d62c91a648870e631721625567f20b5e"
HISTORICAL_CONTROL_PARSED_OBJECT_SHA256: Final = (
    "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
)
CANONICAL_OBJECT_SHA256: Final = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
CANONICAL_FINAL_OBJECT: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
ASSISTANT_ACKNOWLEDGEMENT: Final = "Synthetic deterministic context acknowledged."

DECISION_STATES: Final = (
    "CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE",
    "ORDER_INTERVENTION_RESTORES_BEHAVIOR",
    "ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE",
    "ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE",
    "ORDER_INTERVENTION_EFFECT_AMBIGUOUS",
    "DIAGNOSTIC_INVALID",
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
        raise AuthorizationDesignError("C4_ORDER_AUTHORIZATION_DESIGN_ARGUMENT_ERROR", message)


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
    gpu_topology: Literal["T4_X2"] = "T4_X2"
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
    maximum_worker_teardowns: Literal[6] = 6
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
    control_request_payload_sha256_bound: Literal[True] = True
    treatment_request_payload_sha256_bound: Literal[True] = True
    control_token_sha256_bound: Literal[True] = True
    treatment_token_sha256_bound: Literal[True] = True
    request_order_bound: Literal[True] = True
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
    evidence_schema_bound: Literal[True] = True


class RuntimeAdmissionContract(FrozenModel):
    static_repository_runtime_execution_permitted: Literal[False] = False
    transaction_bound_executable_required: Literal[True] = True
    authorization_admission_precedes_runtime_installation: Literal[True] = True
    authorization_must_be_live_at_admission: Literal[True] = True
    admitted_execution_may_finish_after_expiry: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False


class DifferentialExperimentContract(FrozenModel):
    experiment_id: Literal["C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"] = (
        "C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
    )
    variable_under_test: Literal[
        "GLOBAL_PARAGRAPH_ORDER_WITH_TOKEN_INVENTORY_AND_LOCAL_TAIL_LOCKED"
    ] = "GLOBAL_PARAGRAPH_ORDER_WITH_TOKEN_INVENTORY_AND_LOCAL_TAIL_LOCKED"
    control_condition_id: Literal["CONTROL_ORIGINAL_C4"] = CONTROL_CONDITION
    treatment_condition_id: Literal["TREATMENT_REVERSED_MIDDLE_EIGHT"] = TREATMENT_CONDITION
    request_order: tuple[str, ...] = REQUEST_ORDER
    observations_per_condition: Literal[3] = 3
    prompt_token_count_per_condition: Literal[899] = 899
    final_user_boundary_per_condition: Literal[880] = 880
    message_boundary_profile_per_condition: tuple[int, ...] = MESSAGE_BOUNDARY_PROFILE
    common_suffix_token_count: Literal[122] = 122
    paragraph_count_per_condition: Literal[10] = 10
    control_paragraph_order: tuple[int, ...] = CONTROL_PARAGRAPH_ORDER
    treatment_paragraph_order: tuple[int, ...] = TREATMENT_PARAGRAPH_ORDER
    paragraph_content_multiset_preserved: Literal[True] = True
    token_id_multiset_identical: Literal[True] = True
    character_count_preserved: Literal[True] = True
    first_paragraph_preserved: Literal[True] = True
    last_paragraph_preserved: Literal[True] = True
    fresh_worker_process_per_observation: Literal[True] = True
    zero_cached_prefix_baseline_required: Literal[True] = True
    teardown_required_between_observations: Literal[True] = True
    prior_request_cache_carryover_permitted: Literal[False] = False
    pre_request_token_identity_journal_required: Literal[True] = True
    pre_request_identity_persisted_before_model_request_budget: Literal[True] = True
    invalid_json_retained_as_observation: Literal[True] = True

    control_token_sha256: Literal[
        "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
    ] = CONTROL_TOKEN_SHA256
    treatment_token_sha256: Literal[
        "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
    ] = TREATMENT_TOKEN_SHA256
    control_payload_sha256: Literal[
        "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
    ] = CONTROL_PAYLOAD_SHA256
    treatment_payload_sha256: Literal[
        "47c519c24efd40e3bab4bfa2eaec1cf3d62c91a648870e631721625567f20b5e"
    ] = TREATMENT_PAYLOAD_SHA256
    historical_control_parsed_object_sha256: Literal[
        "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
    ] = HISTORICAL_CONTROL_PARSED_OBJECT_SHA256

    message_roles: tuple[str, ...] = ("system", "user", "assistant", "user")
    assistant_acknowledgement: Literal["Synthetic deterministic context acknowledged."] = (
        ASSISTANT_ACKNOWLEDGEMENT
    )
    canonical_final_object: Literal['{"probe":"exact-runtime-p5-p6","value":1}'] = (
        CANONICAL_FINAL_OBJECT
    )
    canonical_object_sha256: Literal[
        "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
    ] = CANONICAL_OBJECT_SHA256
    maximum_output_tokens: Literal[32] = 32
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    repetition_penalty: float = Field(default=1.1, ge=1.1, le=1.1, strict=True)
    seed: Literal[7] = 7
    stream: Literal[False] = False
    response_format_present: Literal[False] = False
    output_mode: Literal["UNCONSTRAINED"] = "UNCONSTRAINED"

    decision_states: tuple[str, ...] = DECISION_STATES
    control_anchor_must_reproduce_zero_of_three_exact: Literal[True] = True
    control_anchor_valid_json_three_of_three_required: Literal[True] = True
    control_anchor_historical_parsed_identity_required: Literal[True] = True
    treatment_three_of_three_exact_means_restoration: Literal[True] = True
    post_hoc_two_of_three_interpretation_permitted: Literal[False] = False
    mixed_result_permits_paragraph_order_claim: Literal[False] = False
    paragraph_order_root_cause_claim_permitted: Literal[False] = False
    canonical_corpus_global_invalidation_permitted: Literal[False] = False
    threshold_search_authorized: Literal[False] = False
    runtime_remediation_authorized: Literal[False] = False
    p5_p6_requalification_authorized: Literal[False] = False
    north_star_abc_effect_claim_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.request_order != REQUEST_ORDER:
            raise ValueError("paragraph-order request order drifted")
        if self.request_order.count(CONTROL_CONDITION) != 3:
            raise ValueError("control observation count drifted")
        if self.request_order.count(TREATMENT_CONDITION) != 3:
            raise ValueError("treatment observation count drifted")
        if self.control_paragraph_order != CONTROL_PARAGRAPH_ORDER:
            raise ValueError("control paragraph order drifted")
        if self.treatment_paragraph_order != TREATMENT_PARAGRAPH_ORDER:
            raise ValueError("treatment paragraph order drifted")
        if self.message_boundary_profile_per_condition != MESSAGE_BOUNDARY_PROFILE:
            raise ValueError("message boundary profile drifted")
        if self.decision_states != DECISION_STATES:
            raise ValueError("decision-state set drifted")
        return self


class EvidenceContract(FrozenModel):
    expected_evidence_zip: Literal[
        "ag-c4-paragraph-order-behavioral-differential-evidence-v1.zip"
    ] = "ag-c4-paragraph-order-behavioral-differential-evidence-v1.zip"
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
        "auragateway-c4-paragraph-order-behavioral-differential-execution-authorization-design-v1"
    ]
    status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["7e037596de1a74038583a85ed81d46ec12debbac"]
    implementation_merge_commit: Literal["7e037596de1a74038583a85ed81d46ec12debbac"]
    authorization_architecture: Literal["TRANSACTION_BOUND_EXECUTION_ARTIFACT"]
    authorization_scope: Literal["C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"]
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
        "IMPLEMENT_AND_MERGE_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_"
        "EXECUTION_AUTHORIZATION_ISSUER_V1"
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
            "C4_ORDER_AUTHORIZATION_DESIGN_AUTHORITY_MISSING",
            "required merged paragraph-order authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    observed = _sha256(payload)
    if observed != expected_sha256:
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_AUTHORITY_IDENTITY_DRIFT",
            "required merged paragraph-order authority identity drifted",
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
            "C4_ORDER_AUTHORIZATION_DESIGN_ANCESTRY_DRIFT",
            "authorization-design base commit is not an ancestor of HEAD",
        )


def _mapping(payload: bytes, path: Path) -> dict[str, object]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
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
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
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
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
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
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "generation_controls is not an object",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    expected_generation: dict[str, object] = {
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

    conditions = value.get("conditions")
    if not isinstance(conditions, list) or len(conditions) != 2:
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "conditions are not the expected two-condition array",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    condition_maps = [item for item in conditions if isinstance(item, dict)]
    if len(condition_maps) != 2:
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "condition entries are not objects",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    condition_by_id = {item.get("condition_id"): item for item in condition_maps}
    control = condition_by_id.get(CONTROL_CONDITION)
    treatment = condition_by_id.get(TREATMENT_CONDITION)
    if control is None or treatment is None:
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "control or treatment condition is missing",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    _require_equal(
        control.get("prompt_token_sha256"),
        CONTROL_TOKEN_SHA256,
        "control.prompt_token_sha256",
        EXPERIMENT_DESIGN_PATH,
    )
    _require_equal(
        treatment.get("prompt_token_sha256"),
        TREATMENT_TOKEN_SHA256,
        "treatment.prompt_token_sha256",
        EXPERIMENT_DESIGN_PATH,
    )
    _require_equal(
        tuple(cast(list[int], control.get("paragraph_order"))),
        CONTROL_PARAGRAPH_ORDER,
        "control.paragraph_order",
        EXPERIMENT_DESIGN_PATH,
    )
    _require_equal(
        tuple(cast(list[int], treatment.get("paragraph_order"))),
        TREATMENT_PARAGRAPH_ORDER,
        "treatment.paragraph_order",
        EXPERIMENT_DESIGN_PATH,
    )
    _require_equal(
        control.get("historical_canonical_parsed_object_sha256"),
        HISTORICAL_CONTROL_PARSED_OBJECT_SHA256,
        "control.historical_canonical_parsed_object_sha256",
        EXPERIMENT_DESIGN_PATH,
    )

    rules = value.get("decision_rules")
    if not isinstance(rules, list):
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "decision_rules is not an array",
            EXPERIMENT_DESIGN_PATH.as_posix(),
        )
    states = tuple(item.get("state") for item in rules if isinstance(item, dict))
    _require_equal(states, DECISION_STATES, "decision_rules", EXPERIMENT_DESIGN_PATH)


def _validate_review_semantics(payload: bytes) -> None:
    value = _mapping(payload, IMPLEMENTATION_REVIEW_PATH)
    expected: dict[str, object] = {
        "status": "APPROVED_STATIC_PARAGRAPH_ORDER_DIFFERENTIAL_HARNESS",
        "design_record_sha256": EXPERIMENT_DESIGN_SHA256,
        "runtime_payload_sha256": SUCCESSOR_RUNTIME_SHA256,
        "implementation_source_sha256": IMPLEMENTATION_SOURCE_SHA256,
        "focused_test_sha256": IMPLEMENTATION_TEST_SHA256,
        "control_request_payload_sha256": CONTROL_PAYLOAD_SHA256,
        "treatment_request_payload_sha256": TREATMENT_PAYLOAD_SHA256,
        "request_order": list(REQUEST_ORDER),
        "observations_per_condition": 3,
        "prompt_token_count_per_condition": 899,
        "final_user_boundary_per_condition": 880,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "maximum_hidden_retries": 0,
        "maximum_replacement_observations": 0,
        "fresh_worker_process_per_observation": True,
        "control_anchor_requires_historical_parsed_identity": True,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
    }
    for field, expected_value in expected.items():
        _require_equal(value.get(field), expected_value, field, IMPLEMENTATION_REVIEW_PATH)


def _validate_record_semantics(payload: bytes) -> None:
    value = _mapping(payload, IMPLEMENTATION_RECORD_PATH)
    expected: dict[str, object] = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "design_record_sha256": EXPERIMENT_DESIGN_SHA256,
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "implementation_review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "control_request_payload_sha256": CONTROL_PAYLOAD_SHA256,
        "treatment_request_payload_sha256": TREATMENT_PAYLOAD_SHA256,
        "model_requests_performed": 0,
        "model_loads_performed": 0,
        "worker_starts_performed": 0,
        "kaggle_execution_performed": False,
        "gpu_execution_performed": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "final_abc_measured": False,
        "production_readiness_established": False,
    }
    for field, expected_value in expected.items():
        _require_equal(value.get(field), expected_value, field, IMPLEMENTATION_RECORD_PATH)


def build_record(root: Path) -> AuthorizationDesignRecord:
    root = root.resolve()
    _require_base_ancestor(root)
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
            "auragateway-c4-paragraph-order-behavioral-differential-"
            "execution-authorization-design-v1"
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
        "status": "C4_PARAGRAPH_ORDER_EXECUTION_AUTHORIZATION_DESIGN_GENERATED",
        "design_record_sha256": _sha256(payload),
        "authorization_architecture": AUTHORIZATION_ARCHITECTURE,
        "authorization_scope": AUTHORIZATION_SCOPE,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    expected = render_record(root)
    path = root / DESIGN_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_RECORD_MISSING",
            "authorization-design record is missing or unsafe",
            DESIGN_RECORD_PATH.as_posix(),
        )
    observed = path.read_bytes()
    if observed != expected:
        raise AuthorizationDesignError(
            "C4_ORDER_AUTHORIZATION_DESIGN_RECORD_DRIFT",
            "authorization-design record does not match deterministic rendering",
            DESIGN_RECORD_PATH.as_posix(),
        )
    record = AuthorizationDesignRecord.model_validate_json(observed)
    return {
        "status": "C4_PARAGRAPH_ORDER_EXECUTION_AUTHORIZATION_DESIGN_VALID",
        "design_record_sha256": _sha256(observed),
        "authorization_architecture": record.authorization_architecture,
        "authorization_scope": record.authorization_scope,
        "authority_count": len(record.authorities),
        "maximum_model_requests": record.execution_budget.maximum_model_requests,
        "maximum_worker_starts": record.execution_budget.maximum_worker_starts,
        "maximum_model_loads": record.execution_budget.maximum_model_loads,
        "maximum_worker_teardowns": record.execution_budget.maximum_worker_teardowns,
        "maximum_hidden_retries": record.execution_budget.maximum_hidden_retries,
        "observations_per_condition": record.experiment.observations_per_condition,
        "prompt_token_count_per_condition": record.experiment.prompt_token_count_per_condition,
        "request_order": list(record.experiment.request_order),
        "control_token_sha256": record.experiment.control_token_sha256,
        "treatment_token_sha256": record.experiment.treatment_token_sha256,
        "control_payload_sha256": record.experiment.control_payload_sha256,
        "treatment_payload_sha256": record.experiment.treatment_payload_sha256,
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
        TypeError,
        ValueError,
    ) as error:
        if isinstance(error, AuthorizationDesignError):
            code = error.error_code
            message = error.safe_message
            path = error.path
        if not isinstance(error, AuthorizationDesignError):
            code = "C4_ORDER_AUTHORIZATION_DESIGN_VALIDATION_FAILED"
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
