"""Freeze C4 single-use execution-authorization design V1.

Design-only control-plane infrastructure. This module binds a future
transaction-bound single-use authorization issuer to the exact merged C4
qualification request, reusable-prefix identity, and governed execution
harness. It issues no live authority and performs no runtime execution.
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

BASE_MAIN_COMMIT: Final = "9785f9f931bfa5bdd2d0bd97881759b5610eafa6"
IMPLEMENTATION_MERGE_COMMIT: Final = BASE_MAIN_COMMIT

QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "canonical_synthetic_prefix_c4_behavioral_qualification_v1_request.json"
)
QUALIFICATION_REQUEST_SHA256: Final = (
    "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
)
QUALIFICATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_v1_review.json"
)
QUALIFICATION_REVIEW_SHA256: Final = (
    "ff1ecb531db85cfacab26db9f546fdc981292dd3feb2da6934a3e74c712286bc"
)
REUSABLE_PREFIX_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_reusable_prefix_identity_v1.json"
)
REUSABLE_PREFIX_RECEIPT_SHA256: Final = (
    "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
)
SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_behavioral_qualification_"
    "implementation_v1_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "d5bbb90fbf171ad3c38e713b9aa71e2fd6dbc39254236933dcdf446e824d9452"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_behavioral_qualification_"
    "implementation_v1.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "7e5d102ed485279f0d8efd344529ec92b96e97a858b68652518a0472aeb9665a"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "233a38bdbe6631547811bcf135ba0e40470d9e04b1e71268aef11c6e34a788f4"
)
IMPLEMENTATION_TEST_SHA256: Final = (
    "8c27d55ed3464c9214c28603aa4e9f733fcafe6830b8b44efbe5e97d6a432c61"
)

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_single_use_execution_"
    "authorization_design_v1.json"
)

AUTHORIZATION_ARCHITECTURE: Final = "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
AUTHORIZATION_SCOPE: Final = "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
NEXT_GATE: Final = (
    "IMPLEMENT_AND_MERGE_CANONICAL_SYNTHETIC_PREFIX_C4_SINGLE_USE_EXECUTION_AUTHORIZATION_ISSUER_V1"
)

CANONICAL_CORPUS_VERSION: Final = "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1"
CANONICAL_CORPUS_SHA256: Final = "140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"
FULL_PROMPT_TOKEN_COUNT: Final = 899
FULL_PROMPT_TOKEN_SHA256: Final = "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
REUSABLE_PREFIX_TOKEN_COUNT: Final = 880
REUSABLE_PREFIX_TOKEN_SHA256: Final = (
    "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
)
CANONICAL_REQUEST_PAYLOAD_SHA256: Final = (
    "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
)
CANONICAL_OBJECT_SHA256: Final = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
CANONICAL_FINAL_OBJECT: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
ASSISTANT_ACKNOWLEDGEMENT: Final = "Synthetic deterministic context acknowledged."


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
        raise AuthorizationDesignError("C4_AUTHORIZATION_DESIGN_ARGUMENT_ERROR", message)


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
    maximum_model_requests: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    maximum_worker_teardowns: Literal[3] = 3
    maximum_output_tokens_per_request: Literal[32] = 32
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_requests: Literal[0] = 0
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
    canonical_request_payload_sha256_bound: Literal[True] = True
    reusable_prefix_token_sha256_bound: Literal[True] = True
    generator_contract_sha256_bound: Literal[True] = True
    deterministic_artifact_generation_required: Literal[True] = True
    whole_notebook_sha256_is_semantic_payload_identity: Literal[False] = False
    nonidentical_regeneration_requires_fresh_authority: Literal[True] = True


class AuthorizationPayloadBindingContract(FrozenModel):
    authorization_scope_bound: Literal[True] = True
    authorization_design_record_sha256_bound: Literal[True] = True
    issuer_merge_commit_bound: Literal[True] = True
    implementation_merge_commit_bound: Literal[True] = True
    qualification_request_authority_bound: Literal[True] = True
    reusable_prefix_identity_authority_bound: Literal[True] = True
    implementation_authority_hashes_bound: Literal[True] = True
    runtime_model_contract_bound: Literal[True] = True
    execution_budget_bound: Literal[True] = True
    qualification_contract_bound: Literal[True] = True
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


class QualificationContract(FrozenModel):
    qualification_id: Literal["CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"] = (
        "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
    )
    canonical_corpus_version: Literal["CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1"] = (
        CANONICAL_CORPUS_VERSION
    )
    canonical_corpus_sha256: Literal[
        "140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"
    ] = CANONICAL_CORPUS_SHA256
    full_prompt_token_count: Literal[899] = FULL_PROMPT_TOKEN_COUNT
    full_prompt_token_sha256: Literal[
        "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
    ] = FULL_PROMPT_TOKEN_SHA256
    reusable_prefix_token_count: Literal[880] = REUSABLE_PREFIX_TOKEN_COUNT
    reusable_prefix_token_sha256: Literal[
        "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
    ] = REUSABLE_PREFIX_TOKEN_SHA256
    canonical_request_payload_sha256: Literal[
        "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
    ] = CANONICAL_REQUEST_PAYLOAD_SHA256
    canonical_object_sha256: Literal[
        "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
    ] = CANONICAL_OBJECT_SHA256
    canonical_final_object: Literal['{"probe":"exact-runtime-p5-p6","value":1}'] = (
        CANONICAL_FINAL_OBJECT
    )
    assistant_acknowledgement: Literal["Synthetic deterministic context acknowledged."] = (
        ASSISTANT_ACKNOWLEDGEMENT
    )
    message_roles: tuple[str, ...] = ("system", "user", "assistant", "user")
    observation_count: Literal[3] = 3
    exact_pass_count_required: Literal[3] = 3
    one_request_per_worker: Literal[True] = True
    fresh_worker_per_observation: Literal[True] = True
    zero_cached_prefix_baseline_required: Literal[True] = True
    teardown_after_each_observation: Literal[True] = True
    healthy_behavioral_failure_completes_all_observations: Literal[True] = True
    execution_invalidating_failure_stops_without_replacement: Literal[True] = True
    strict_duplicate_key_rejection: Literal[True] = True
    strict_integer_value_validation: Literal[True] = True
    finish_reason_stop_required: Literal[True] = True
    response_completion_required: Literal[True] = True
    exact_key_set_required: Literal[True] = True
    extra_keys_forbidden: Literal[True] = True
    markdown_fence_forbidden: Literal[True] = True
    surrounding_non_whitespace_forbidden: Literal[True] = True
    maximum_output_tokens: Literal[32] = 32
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    repetition_penalty: float = Field(default=1.1, ge=1.1, le=1.1, strict=True)
    seed: Literal[7] = 7
    stream: Literal[False] = False
    response_format_present: Literal[False] = False
    guided_decoding_present: Literal[False] = False
    schema_enforcement_present: Literal[False] = False
    threshold_relaxation_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[0] = 0
    replacement_requests_permitted: Literal[0] = 0
    terminal_states: tuple[str, ...] = ("QUALIFIED", "NOT_QUALIFIED", "INVALID_EXECUTION")
    p5_execution_authorized: Literal[False] = False
    p6_execution_authorized: Literal[False] = False
    final_abc_effect_claim_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.message_roles != ("system", "user", "assistant", "user"):
            raise ValueError("C4 message-role contract drifted")
        if self.terminal_states != ("QUALIFIED", "NOT_QUALIFIED", "INVALID_EXECUTION"):
            raise ValueError("C4 terminal-state contract drifted")
        return self


class EvidenceContract(FrozenModel):
    expected_evidence_zip: Literal["ag-c4-canonical-prefix-qual-evidence-v1.zip"] = (
        "ag-c4-canonical-prefix-qual-evidence-v1.zip"
    )
    required_output_names: tuple[str, ...] = (
        "runtime_source_identity_report_v1.json",
        "runtime_install_report_v1.json",
        "runtime_environment_report_v1.json",
        "runtime_import_closure_report_v1.json",
        "c4_runtime_ready_v1.json",
        "pre_request_token_identity_journal_v1.json",
        "c4_request_results_v1.json",
        "c4_decision_v1.json",
        "worker_teardown_report_v1.json",
        "scratch_cleanup_report_v1.json",
        "failure_report_v1.json",
        "c4_summary_v1.json",
        "human_report_v1.md",
        "bundle_manifest_v1.json",
    )
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    platform_observation_bound_to_transaction: Literal[True] = True
    saved_version_bound_to_transaction: Literal[True] = True
    evidence_identity_bound_to_terminal_receipt: Literal[True] = True
    behavioral_observation_persisted_before_bundle_custody: Literal[True] = True
    custody_failure_invalidates_governed_execution: Literal[True] = True
    terminalizable_without_expected_evidence_zip: Literal[True] = True


class RepositoryAcceptanceContract(FrozenModel):
    runtime_decision_is_repository_acceptance: Literal[False] = False
    separate_acceptance_reconciliation_required: Literal[True] = True
    authorization_lifecycle_must_be_verified: Literal[True] = True
    evidence_identity_must_be_verified: Literal[True] = True
    saved_version_identity_must_be_verified: Literal[True] = True
    platform_budget_must_be_verified: Literal[True] = True
    runtime_identity_must_be_verified: Literal[True] = True
    c4_acceptance_required_before_p5_p6_successor: Literal[True] = True
    p5_p6_successor_must_derive_from_this_runtime: Literal[True] = True


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
        "auragateway-canonical-synthetic-prefix-c4-single-use-execution-authorization-design-v1"
    ]
    status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["9785f9f931bfa5bdd2d0bd97881759b5610eafa6"] = BASE_MAIN_COMMIT
    implementation_merge_commit: Literal["9785f9f931bfa5bdd2d0bd97881759b5610eafa6"] = (
        IMPLEMENTATION_MERGE_COMMIT
    )
    authorization_architecture: Literal["TRANSACTION_BOUND_EXECUTION_ARTIFACT"]
    authorization_scope: Literal["CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"]
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
    qualification: QualificationContract
    evidence: EvidenceContract
    repository_acceptance: RepositoryAcceptanceContract
    terminalization: TerminalizationContract
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    model_loads_performed: Literal[0] = 0
    worker_starts_performed: Literal[0] = 0
    kaggle_execution_performed: Literal[False] = False
    governed_executable_generated: Literal[False] = False
    platform_observation_persisted: Literal[False] = False
    c4_qualified: Literal[False] = False
    p5_requalified: Literal[False] = False
    p6_requalified: Literal[False] = False
    next_gate: Literal[
        "IMPLEMENT_AND_MERGE_CANONICAL_SYNTHETIC_PREFIX_C4_SINGLE_USE_"
        "EXECUTION_AUTHORIZATION_ISSUER_V1"
    ] = NEXT_GATE

    @model_validator(mode="after")
    def validate_authority_roles(self) -> Self:
        roles = tuple(authority.role for authority in self.authorities)
        expected = (
            "frozen_qualification_request",
            "frozen_qualification_review",
            "reusable_prefix_identity_receipt",
            "merged_successor_runtime",
            "implementation_review",
            "implementation_record",
        )
        if roles != expected:
            raise ValueError("C4 authorization authority roles drifted")
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
            "C4_AUTHORIZATION_DESIGN_AUTHORITY_MISSING",
            "required merged C4 authority is missing or unsafe",
            path.as_posix(),
        )
    payload = absolute.read_bytes()
    observed = _sha256(payload)
    if observed != expected_sha256:
        raise AuthorizationDesignError(
            "C4_AUTHORIZATION_DESIGN_AUTHORITY_IDENTITY_DRIFT",
            "required merged C4 authority identity drifted",
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
            "C4_AUTHORIZATION_DESIGN_ANCESTRY_DRIFT",
            "authorization-design base commit is not an ancestor of HEAD",
        )


def _mapping(payload: bytes, path: Path) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise AuthorizationDesignError(
            "C4_AUTHORIZATION_DESIGN_JSON_INVALID",
            "bound C4 authority is not valid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise AuthorizationDesignError(
            "C4_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            "bound C4 authority is not a JSON object",
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
            "C4_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            f"bound C4 authority field drifted: {field}",
            path.as_posix(),
        )


def _nested_mapping(
    value: dict[str, object],
    field: str,
    path: Path,
) -> dict[str, object]:
    nested = value.get(field)
    if not isinstance(nested, dict):
        raise AuthorizationDesignError(
            "C4_AUTHORIZATION_DESIGN_SEMANTIC_DRIFT",
            f"bound C4 authority field is not an object: {field}",
            path.as_posix(),
        )
    return cast(dict[str, object], nested)


def _validate_qualification_request(payload: bytes) -> None:
    value = _mapping(payload, QUALIFICATION_REQUEST_PATH)
    _require_equal(
        value.get("qualification_id"),
        AUTHORIZATION_SCOPE,
        "qualification_id",
        QUALIFICATION_REQUEST_PATH,
    )
    _require_equal(
        value.get("runtime_execution_authorized"),
        False,
        "runtime_execution_authorized",
        QUALIFICATION_REQUEST_PATH,
    )
    observation = _nested_mapping(
        value,
        "observation_contract",
        QUALIFICATION_REQUEST_PATH,
    )
    _require_equal(
        observation.get("observation_count"),
        3,
        "observation_count",
        QUALIFICATION_REQUEST_PATH,
    )
    _require_equal(
        observation.get("exact_pass_count_required"),
        3,
        "exact_pass_count_required",
        QUALIFICATION_REQUEST_PATH,
    )
    _require_equal(
        observation.get("hidden_retries_permitted"),
        0,
        "hidden_retries_permitted",
        QUALIFICATION_REQUEST_PATH,
    )
    _require_equal(
        observation.get("replacement_requests_permitted"),
        0,
        "replacement_requests_permitted",
        QUALIFICATION_REQUEST_PATH,
    )
    budget = _nested_mapping(value, "execution_budget", QUALIFICATION_REQUEST_PATH)
    expected_budget = {
        "maximum_model_requests": 3,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_kaggle_sessions": 1,
        "maximum_save_and_run_all_actions": 1,
        "hidden_retries_permitted": 0,
        "replacement_requests_permitted": 0,
        "external_network_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
        "required_worker_teardowns": 3,
        "maximum_output_tokens_per_request": 32,
    }
    for field, expected in expected_budget.items():
        _require_equal(budget.get(field), expected, field, QUALIFICATION_REQUEST_PATH)


def _validate_reusable_prefix_receipt(payload: bytes) -> None:
    value = _mapping(payload, REUSABLE_PREFIX_RECEIPT_PATH)
    claims = _nested_mapping(value, "claims", REUSABLE_PREFIX_RECEIPT_PATH)
    measurement = _nested_mapping(value, "measurement", REUSABLE_PREFIX_RECEIPT_PATH)
    _require_equal(
        claims.get("runtime_execution_authorized"),
        False,
        "claims.runtime_execution_authorized",
        REUSABLE_PREFIX_RECEIPT_PATH,
    )
    expected_measurement = {
        "full_prompt_token_count": FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": FULL_PROMPT_TOKEN_SHA256,
        "reusable_prefix_token_count": REUSABLE_PREFIX_TOKEN_COUNT,
        "reusable_prefix_token_sha256": REUSABLE_PREFIX_TOKEN_SHA256,
        "canonical_request_payload_sha256": CANONICAL_REQUEST_PAYLOAD_SHA256,
    }
    for field, expected in expected_measurement.items():
        _require_equal(
            measurement.get(field),
            expected,
            f"measurement.{field}",
            REUSABLE_PREFIX_RECEIPT_PATH,
        )


def _validate_implementation_review(payload: bytes) -> None:
    value = _mapping(payload, IMPLEMENTATION_REVIEW_PATH)
    expected = {
        "status": "APPROVED_STATIC_C4_EXECUTION_HARNESS",
        "runtime_payload_sha256": SUCCESSOR_RUNTIME_SHA256,
        "architecture_review_sha256": QUALIFICATION_REVIEW_SHA256,
        "reusable_prefix_receipt_sha256": REUSABLE_PREFIX_RECEIPT_SHA256,
        "implementation_source_sha256": IMPLEMENTATION_SOURCE_SHA256,
        "focused_test_sha256": IMPLEMENTATION_TEST_SHA256,
        "full_prompt_token_count": FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": FULL_PROMPT_TOKEN_SHA256,
        "reusable_prefix_token_count": REUSABLE_PREFIX_TOKEN_COUNT,
        "reusable_prefix_token_sha256": REUSABLE_PREFIX_TOKEN_SHA256,
        "canonical_request_payload_sha256": CANONICAL_REQUEST_PAYLOAD_SHA256,
        "maximum_model_requests": 3,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_hidden_retries": 0,
        "runtime_execution_authorized": False,
        "strict_duplicate_key_rejection": True,
        "strict_integer_value_validation": True,
        "finish_reason_stop_required": True,
        "runtime_budget_attempt_semantics": True,
        "platform_budget_deferred_to_authorization_wrapper": True,
        "p5_p6_successor_lineage_parent": True,
    }
    for field, expected_value in expected.items():
        _require_equal(
            value.get(field),
            expected_value,
            field,
            IMPLEMENTATION_REVIEW_PATH,
        )


def _validate_implementation_record(payload: bytes) -> None:
    value = _mapping(payload, IMPLEMENTATION_RECORD_PATH)
    expected = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "implementation_review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "qualification_request_sha256": QUALIFICATION_REQUEST_SHA256,
        "reusable_prefix_receipt_sha256": REUSABLE_PREFIX_RECEIPT_SHA256,
        "model_requests_performed": 0,
        "model_loads_performed": 0,
        "worker_starts_performed": 0,
        "runtime_execution_authorized": False,
        "live_authorization_issued": False,
        "c4_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "p5_p6_successor_must_derive_from_this_runtime": True,
    }
    for field, expected_value in expected.items():
        _require_equal(
            value.get(field),
            expected_value,
            field,
            IMPLEMENTATION_RECORD_PATH,
        )


def build_record(root: Path) -> AuthorizationDesignRecord:
    root = root.resolve()
    _require_base_ancestor(root)
    authority_specs = (
        (
            "frozen_qualification_request",
            QUALIFICATION_REQUEST_PATH,
            QUALIFICATION_REQUEST_SHA256,
        ),
        (
            "frozen_qualification_review",
            QUALIFICATION_REVIEW_PATH,
            QUALIFICATION_REVIEW_SHA256,
        ),
        (
            "reusable_prefix_identity_receipt",
            REUSABLE_PREFIX_RECEIPT_PATH,
            REUSABLE_PREFIX_RECEIPT_SHA256,
        ),
        (
            "merged_successor_runtime",
            SUCCESSOR_RUNTIME_PATH,
            SUCCESSOR_RUNTIME_SHA256,
        ),
        (
            "implementation_review",
            IMPLEMENTATION_REVIEW_PATH,
            IMPLEMENTATION_REVIEW_SHA256,
        ),
        (
            "implementation_record",
            IMPLEMENTATION_RECORD_PATH,
            IMPLEMENTATION_RECORD_SHA256,
        ),
    )
    authorities: list[ArtifactAuthority] = []
    payloads: dict[str, bytes] = {}
    for role, path, expected_sha256 in authority_specs:
        authority, payload = _read_authority(root, role, path, expected_sha256)
        authorities.append(authority)
        payloads[role] = payload

    _validate_qualification_request(payloads["frozen_qualification_request"])
    _validate_reusable_prefix_receipt(payloads["reusable_prefix_identity_receipt"])
    _validate_implementation_review(payloads["implementation_review"])
    _validate_implementation_record(payloads["implementation_record"])

    return AuthorizationDesignRecord(
        design_id=(
            "auragateway-canonical-synthetic-prefix-c4-single-use-execution-authorization-design-v1"
        ),
        status="DESIGN_FROZEN_NOT_EXECUTED",
        authorization_architecture=AUTHORIZATION_ARCHITECTURE,
        authorization_scope=AUTHORIZATION_SCOPE,
        authorities=tuple(authorities),
        runtime_model=RuntimeModelContract(),
        execution_budget=ExecutionBudget(),
        human_authorization=HumanAuthorizationContract(),
        platform=PlatformContract(),
        platform_observation_receipt=PlatformObservationReceiptContract(),
        transport_topology=TransportTopology(),
        transaction_identity=TransactionIdentityContract(),
        authorization_payload_binding=AuthorizationPayloadBindingContract(),
        runtime_admission=RuntimeAdmissionContract(),
        qualification=QualificationContract(),
        evidence=EvidenceContract(),
        repository_acceptance=RepositoryAcceptanceContract(),
        terminalization=TerminalizationContract(),
    )


def render_record(root: Path) -> bytes:
    return _canonical_json_bytes(build_record(root))


def write_record(root: Path) -> Path:
    target = root.resolve() / DESIGN_RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(render_record(root))
    return target


def validate_record(root: Path) -> None:
    target = root.resolve() / DESIGN_RECORD_PATH
    if not target.is_file() or target.is_symlink():
        raise AuthorizationDesignError(
            "C4_AUTHORIZATION_DESIGN_RECORD_MISSING",
            "authorization-design record is missing or unsafe",
            DESIGN_RECORD_PATH.as_posix(),
        )
    observed = target.read_bytes()
    expected = render_record(root)
    if observed != expected:
        raise AuthorizationDesignError(
            "C4_AUTHORIZATION_DESIGN_RECORD_DRIFT",
            "authorization-design record differs from deterministic rendering",
            DESIGN_RECORD_PATH.as_posix(),
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("write", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = cast(Path, args.repo_root)
    if args.command == "write":
        target = write_record(root)
        payload = target.read_bytes()
        print(
            json.dumps(
                {
                    "status": "DESIGN_RECORD_WRITTEN",
                    "path": DESIGN_RECORD_PATH.as_posix(),
                    "sha256": _sha256(payload),
                    "size_bytes": len(payload),
                    "runtime_execution_authorized": False,
                    "next_gate": NEXT_GATE,
                },
                sort_keys=True,
            )
        )
        return 0
    validate_record(root)
    payload = (root.resolve() / DESIGN_RECORD_PATH).read_bytes()
    print(
        json.dumps(
            {
                "status": "DESIGN_RECORD_VALID",
                "path": DESIGN_RECORD_PATH.as_posix(),
                "sha256": _sha256(payload),
                "size_bytes": len(payload),
                "runtime_execution_authorized": False,
                "next_gate": NEXT_GATE,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
