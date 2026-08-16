"""Freeze token-matched context-structure differential execution authorization design V1.

Design-only control-plane infrastructure. This module binds a future
transaction-bound single-use authorization issuer to the exact merged
token-count-matched A/B/C differential implementation and frozen experiment contract.
It issues no live authority and performs no runtime execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

BASE_MAIN_COMMIT: Final = "019f3c406400f4ecb07b864349369981d4654513"
IMPLEMENTATION_MERGE_COMMIT: Final = BASE_MAIN_COMMIT

SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "p4_p5_token_count_matched_context_structure_differential_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834"

IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_differential_"
    "implementation_v1_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a"
)

IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_differential_implementation_v1.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27"
)

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_differential_"
    "execution_authorization_design_v1.json"
)

AUTHORIZATION_ARCHITECTURE: Final = "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
AUTHORIZATION_SCOPE: Final = "P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"

NEXT_GATE: Final = (
    "IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_"
    "EXECUTION_AUTHORIZATION_ISSUER_V1"
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
        raise AuthorizationDesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_ARGUMENT_ERROR",
            message,
        )


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


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_requests: Literal[9] = 9
    maximum_worker_starts: Literal[9] = 9
    maximum_model_loads: Literal[9] = 9
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
        if self.required_fields != (
            "transaction_id",
            "platform_observed_at",
            "accelerator",
            "allocated_gpu_count",
            "internet_enabled",
            "capability_source",
        ):
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
    variable_under_test: Literal["TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE"] = (
        "TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE"
    )
    condition_a_id: Literal["A_ORIGINAL_24X_ANCHOR"] = "A_ORIGINAL_24X_ANCHOR"
    condition_b_id: Literal["B_NEUTRAL_REPEATED_24X"] = "B_NEUTRAL_REPEATED_24X"
    condition_c_id: Literal["C_NEUTRAL_DIVERSE_24_SEGMENT"] = "C_NEUTRAL_DIVERSE_24_SEGMENT"
    request_order: tuple[str, ...] = (
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
    observations_per_condition: Literal[3] = 3
    prompt_token_count_per_condition: Literal[899] = 899
    segment_count_per_condition: Literal[24] = 24
    fresh_worker_process_per_observation: Literal[True] = True
    zero_cached_prefix_baseline_required: Literal[True] = True
    teardown_required_between_observations: Literal[True] = True
    pre_request_token_identity_journal_required: Literal[True] = True
    prior_request_cache_carryover_permitted: Literal[False] = False
    condition_token_identity_required_before_request: Literal[True] = True
    condition_payload_identity_required_before_request: Literal[True] = True

    a_token_sha256: Literal["6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"] = (
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    )
    b_token_sha256: Literal["02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"] = (
        "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
    )
    c_token_sha256: Literal["612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4"] = (
        "612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4"
    )

    a_payload_sha256: Literal[
        "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    ] = "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    b_payload_sha256: Literal[
        "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
    ] = "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
    c_payload_sha256: Literal[
        "8a3d22f50f1956375cfd52f4f01e1843bfe4753da5c76359c47b8da6ecd46f72"
    ] = "8a3d22f50f1956375cfd52f4f01e1843bfe4753da5c76359c47b8da6ecd46f72"

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

    a_0_b_3_c_3: Literal["REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED"] = (
        "REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED"
    )
    a_0_b_0_c_3: Literal["HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"] = (
        "HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"
    )
    a_0_b_0_c_0: Literal["SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE"] = (
        "SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE"
    )
    a_0_b_3_c_0: Literal["DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED"] = (
        "DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED"
    )
    mixed_condition: Literal["UNSTABLE_NO_MECHANISTIC_CLAIM"] = "UNSTABLE_NO_MECHANISTIC_CLAIM"
    anchor_nonreproduction: Literal["ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE"] = (
        "ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE"
    )
    invariant_failure: Literal["DIAGNOSTIC_INVALID"] = "DIAGNOSTIC_INVALID"

    anchor_a_must_reproduce_zero_of_three: Literal[True] = True
    mixed_result_permits_mechanistic_claim: Literal[False] = False
    b_to_c_residual_lexical_novelty_bounded: Literal[True] = True
    exact_repetition_sole_cause_claim_permitted: Literal[False] = False
    semantic_amplification_sole_cause_claim_permitted: Literal[False] = False
    threshold_search_authorized: Literal[False] = False
    runtime_remediation_authorized: Literal[False] = False
    p5_p6_requalification_authorized: Literal[False] = False
    north_star_abc_effect_claim_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        expected = (
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
        if self.request_order != expected:
            raise ValueError("token-matched differential request order drifted")
        for condition_id in (self.condition_a_id, self.condition_b_id, self.condition_c_id):
            if self.request_order.count(condition_id) != self.observations_per_condition:
                raise ValueError("token-matched condition observation count drifted")
        if len({self.a_token_sha256, self.b_token_sha256, self.c_token_sha256}) != 3:
            raise ValueError("token-matched prompt-token identities collapsed")
        if len({self.a_payload_sha256, self.b_payload_sha256, self.c_payload_sha256}) != 3:
            raise ValueError("token-matched request-payload identities collapsed")
        return self


class EvidenceContract(FrozenModel):
    expected_evidence_zip: Literal[
        "ag-p4-p5-token-count-matched-context-structure-differential-evidence-v1.zip"
    ] = "ag-p4-p5-token-count-matched-context-structure-differential-evidence-v1.zip"
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
        "auragateway-p4-p5-token-count-matched-context-structure-differential-"
        "execution-authorization-design-v1"
    ]
    status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["019f3c406400f4ecb07b864349369981d4654513"]
    implementation_merge_commit: Literal["019f3c406400f4ecb07b864349369981d4654513"]
    authorization_architecture: Literal["TRANSACTION_BOUND_EXECUTION_ARTIFACT"]
    authorization_scope: Literal["P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"]
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
        "IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_"
        "EXECUTION_AUTHORIZATION_ISSUER_V1"
    ]

    @model_validator(mode="after")
    def validate_authority_roles(self) -> Self:
        roles = tuple(authority.role for authority in self.authorities)
        if roles != (
            "merged_successor_runtime",
            "implementation_review",
            "implementation_record",
        ):
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
) -> ArtifactAuthority:
    absolute = root / path

    if not absolute.is_file() or absolute.is_symlink():
        raise AuthorizationDesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORITY_MISSING",
            "required merged token-matched authority is missing or unsafe",
            path.as_posix(),
        )

    payload = absolute.read_bytes()
    observed = _sha256(payload)

    if observed != expected_sha256:
        raise AuthorizationDesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORITY_IDENTITY_DRIFT",
            "required merged token-matched authority identity drifted",
            path.as_posix(),
        )

    return ArtifactAuthority(
        role=role,
        path=path.as_posix(),
        sha256=observed,
        size_bytes=len(payload),
    )


def _require_base_ancestor(root: Path) -> None:
    completed = subprocess.run(
        (
            "git",
            "merge-base",
            "--is-ancestor",
            BASE_MAIN_COMMIT,
            "HEAD",
        ),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if completed.returncode != 0:
        raise AuthorizationDesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_ANCESTRY_DRIFT",
            "authorization-design base commit is not an ancestor of HEAD",
        )


def build_record(root: Path) -> AuthorizationDesignRecord:
    root = root.resolve()

    authorities = (
        _read_authority(
            root,
            "merged_successor_runtime",
            SUCCESSOR_RUNTIME_PATH,
            SUCCESSOR_RUNTIME_SHA256,
        ),
        _read_authority(
            root,
            "implementation_review",
            IMPLEMENTATION_REVIEW_PATH,
            IMPLEMENTATION_REVIEW_SHA256,
        ),
        _read_authority(
            root,
            "implementation_record",
            IMPLEMENTATION_RECORD_PATH,
            IMPLEMENTATION_RECORD_SHA256,
        ),
    )

    return AuthorizationDesignRecord(
        design_id=(
            "auragateway-p4-p5-token-count-matched-context-structure-differential-"
            "execution-authorization-design-v1"
        ),
        status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        authorization_architecture=AUTHORIZATION_ARCHITECTURE,
        authorization_scope=AUTHORIZATION_SCOPE,
        authorities=authorities,
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
        "status": "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_GENERATED",
        "design_record_sha256": _sha256(payload),
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
            "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_RECORD_MISSING",
            "authorization-design record is missing or unsafe",
            DESIGN_RECORD_PATH.as_posix(),
        )

    observed = path.read_bytes()

    if observed != expected:
        raise AuthorizationDesignError(
            "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_RECORD_DRIFT",
            "authorization-design record differs from deterministic contract",
            DESIGN_RECORD_PATH.as_posix(),
        )

    record = AuthorizationDesignRecord.model_validate_json(observed)

    return {
        "status": "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_VALID",
        "design_record_sha256": _sha256(observed),
        "authorization_architecture": record.authorization_architecture,
        "authorization_scope": record.authorization_scope,
        "maximum_model_requests": record.execution_budget.maximum_model_requests,
        "maximum_worker_starts": record.execution_budget.maximum_worker_starts,
        "maximum_model_loads": record.execution_budget.maximum_model_loads,
        "maximum_hidden_retries": record.execution_budget.maximum_hidden_retries,
        "durable_platform_observation_required": (
            record.platform_observation_receipt.durable_receipt_required
        ),
        "observation_precedes_save_and_run_all": (
            record.platform.observation_precedes_save_and_run_all
        ),
        "observations_per_condition": record.experiment.observations_per_condition,
        "prompt_token_count_per_condition": record.experiment.prompt_token_count_per_condition,
        "condition_count": 3,
        "fresh_worker_process_per_observation": (
            record.experiment.fresh_worker_process_per_observation
        ),
        "authorization_specific_kaggle_inputs": (
            record.transport_topology.authorization_specific_kaggle_inputs
        ),
        "authorization_producer_notebooks": (
            record.transport_topology.authorization_producer_notebooks
        ),
        "live_authorization_issued": record.live_authorization_issued,
        "runtime_execution_authorized": record.runtime_execution_authorized,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=("generate", "validate"),
    )
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
            code = "P4_P5_TOKEN_MATCHED_STRUCTURE_AUTHORIZATION_DESIGN_VALIDATION_FAILED"
            message = str(error)
            path = None

        print(
            json.dumps(
                {
                    "error_code": code,
                    "safe_message": message,
                    "path": path,
                },
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
