"""Canonical Synthetic Prefix C4 single-use execution authorization issuer V1.

Static generation and validation are inert. Live authority can only be issued
from synchronized, clean main after this issuer has been merged and after the
operator exactly retypes a fresh dynamic SHA-256 challenge.

The issuer generates one transaction-bound notebook, persists the required
post-artifact platform observation before Save & Run All, and terminalizes the
single-use authority. It does not execute Kaggle itself.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

DESIGN_MERGE_COMMIT: Final = "79b8ae8c1c96ea3f296725daff09615767caaefa"
IMPLEMENTATION_MERGE_COMMIT: Final = "9785f9f931bfa5bdd2d0bd97881759b5610eafa6"

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_single_use_execution_"
    "authorization_design_v1.json"
)
DESIGN_RECORD_SHA256: Final = "191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463"
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
SUCCESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_runtime_v1.py"
)
SUCCESSOR_RUNTIME_SHA256: Final = "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "canonical_synthetic_prefix_c4_behavioral_qualification_v1_request.json"
)
QUALIFICATION_REQUEST_SHA256: Final = (
    "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
)
REUSABLE_PREFIX_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_reusable_prefix_identity_v1.json"
)
REUSABLE_PREFIX_RECEIPT_SHA256: Final = (
    "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "canonical_synthetic_prefix_c4_single_use_execution_authorization_v1.py"
)
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "canonical_synthetic_prefix_c4_transaction_bound_wrapper_v1.py.tmpl"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_canonical_synthetic_prefix_c4_single_use_execution_authorization_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/"
    "AuraGateway_Canonical_Synthetic_Prefix_C4_Single_Use_Execution_"
    "Authorization_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_canonical_synthetic_prefix_c4_single_use_execution_authorization_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_single_use_execution_"
    "authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_single_use_execution_"
    "authorization_v1_record.json"
)

LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_single_use_execution_"
    "authorization_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_execution_artifact_v1_live_manifest.json"
)
PLATFORM_OBSERVATION_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_platform_observation_v1_live.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_single_use_execution_"
    "authorization_v1_terminal.json"
)

AUTHORIZATION_SCOPE: Final = "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240
MAX_CONFIRMATION_AGE_MINUTES: Final = 15
PLATFORM_CONTROL_ID: Final = "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"

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
EXPECTED_EVIDENCE_ZIP: Final = "ag-c4-canonical-prefix-qual-evidence-v1.zip"
NOTEBOOK_NAME: Final = "ag-c4-canonical-prefix-qual-v1"

NEXT_GATE: Final = (
    "MERGE_THEN_ISSUE_FRESH_CANONICAL_SYNTHETIC_PREFIX_C4_SINGLE_USE_EXECUTION_AUTHORIZATION_V1"
)
NEXT_GATE_AFTER_ISSUE: Final = "PERSIST_DURABLE_PLATFORM_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
NEXT_GATE_AFTER_OBSERVATION: Final = (
    "ONE_SAVE_AND_RUN_ALL_CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
)
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_RECONCILE_CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_EVIDENCE_V1"
)


class AuthorizationIssuerError(RuntimeError):
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
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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


class RequiredPlatform(FrozenModel):
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


class QualificationContract(FrozenModel):
    qualification_id: Literal["CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"] = (
        AUTHORIZATION_SCOPE
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
        '{"probe":"exact-runtime-p5-p6","value":1}'
    )
    assistant_acknowledgement: Literal["Synthetic deterministic context acknowledged."] = (
        "Synthetic deterministic context acknowledged."
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
    repetition_penalty: float = Field(
        default=1.1,
        ge=1.1,
        le=1.1,
        strict=True,
    )
    seed: Literal[7] = 7
    stream: Literal[False] = False
    response_format_present: Literal[False] = False
    guided_decoding_present: Literal[False] = False
    schema_enforcement_present: Literal[False] = False
    threshold_relaxation_permitted: Literal[False] = False
    hidden_retries_permitted: Literal[0] = 0
    replacement_requests_permitted: Literal[0] = 0
    terminal_states: tuple[str, ...] = (
        "QUALIFIED",
        "NOT_QUALIFIED",
        "INVALID_EXECUTION",
    )
    p5_execution_authorized: Literal[False] = False
    p6_execution_authorized: Literal[False] = False
    final_abc_effect_claim_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.message_roles != ("system", "user", "assistant", "user"):
            raise ValueError("C4 message-role contract drifted")
        if self.terminal_states != (
            "QUALIFIED",
            "NOT_QUALIFIED",
            "INVALID_EXECUTION",
        ):
            raise ValueError("C4 terminal-state contract drifted")
        return self


class EvidenceContract(FrozenModel):
    expected_evidence_zip: Literal["ag-c4-canonical-prefix-qual-evidence-v1.zip"] = (
        EXPECTED_EVIDENCE_ZIP
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


class AuthorizationIntent(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intent_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: Literal["CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"] = (
        AUTHORIZATION_SCOPE
    )
    prepared_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAX_WINDOW_MINUTES,
    )
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463"
    ] = DESIGN_RECORD_SHA256
    implementation_merge_commit: Literal["9785f9f931bfa5bdd2d0bd97881759b5610eafa6"] = (
        IMPLEMENTATION_MERGE_COMMIT
    )
    implementation_review_sha256: Literal[
        "d5bbb90fbf171ad3c38e713b9aa71e2fd6dbc39254236933dcdf446e824d9452"
    ] = IMPLEMENTATION_REVIEW_SHA256
    implementation_record_sha256: Literal[
        "7e5d102ed485279f0d8efd344529ec92b96e97a858b68652518a0472aeb9665a"
    ] = IMPLEMENTATION_RECORD_SHA256
    qualification_request_sha256: Literal[
        "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
    ] = QUALIFICATION_REQUEST_SHA256
    reusable_prefix_receipt_sha256: Literal[
        "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
    ] = REUSABLE_PREFIX_RECEIPT_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
    ] = SUCCESSOR_RUNTIME_SHA256
    canonical_request_payload_sha256: Literal[
        "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
    ] = CANONICAL_REQUEST_PAYLOAD_SHA256
    reusable_prefix_token_sha256: Literal[
        "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
    ] = REUSABLE_PREFIX_TOKEN_SHA256
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    qualification: QualificationContract
    evidence: EvidenceContract
    required_platform: RequiredPlatform
    platform_observation_control_id: Literal[
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    ] = PLATFORM_CONTROL_ID

    @field_validator("prepared_at")
    @classmethod
    def normalize_prepared_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "prepared_at")


class AuthorizationBody(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str = Field(pattern=r"^c4qual-[0-9a-f]{32}$")
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"] = (
        AUTHORIZATION_SCOPE
    )
    authorization_challenge_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"] = (
        "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    )
    operator_confirmation_recorded: Literal[True] = True
    operator_confirmed_at: datetime
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(
        ge=1,
        le=MAX_WINDOW_MINUTES,
    )
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463"
    ] = DESIGN_RECORD_SHA256
    implementation_merge_commit: Literal["9785f9f931bfa5bdd2d0bd97881759b5610eafa6"] = (
        IMPLEMENTATION_MERGE_COMMIT
    )
    implementation_review_sha256: Literal[
        "d5bbb90fbf171ad3c38e713b9aa71e2fd6dbc39254236933dcdf446e824d9452"
    ] = IMPLEMENTATION_REVIEW_SHA256
    implementation_record_sha256: Literal[
        "7e5d102ed485279f0d8efd344529ec92b96e97a858b68652518a0472aeb9665a"
    ] = IMPLEMENTATION_RECORD_SHA256
    qualification_request_sha256: Literal[
        "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
    ] = QUALIFICATION_REQUEST_SHA256
    reusable_prefix_receipt_sha256: Literal[
        "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
    ] = REUSABLE_PREFIX_RECEIPT_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
    ] = SUCCESSOR_RUNTIME_SHA256
    canonical_request_payload_sha256: Literal[
        "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
    ] = CANONICAL_REQUEST_PAYLOAD_SHA256
    reusable_prefix_token_sha256: Literal[
        "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
    ] = REUSABLE_PREFIX_TOKEN_SHA256
    runtime: RuntimeModelContract
    budget: ExecutionBudget
    qualification: QualificationContract
    evidence: EvidenceContract
    required_platform: RequiredPlatform
    platform_observation_control_id: Literal[
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    ] = PLATFORM_CONTROL_ID
    durable_platform_observation_required: Literal[True] = True
    runtime_execution_authorized: Literal[True] = True
    c4_qualification_execution_authorized: Literal[True] = True
    single_use: Literal[True] = True
    every_terminal_attempt_consumes_authorization: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False
    authorization_reusable: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    repository_acceptance_established: Literal[False] = False
    p5_execution_authorized: Literal[False] = False
    p6_execution_authorized: Literal[False] = False
    final_abc_effect_claim_authorized: Literal[False] = False

    @field_validator("operator_confirmed_at", "issued_at", "expires_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _normalize_time(value, "authorization timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.issued_at != self.operator_confirmed_at:
            raise ValueError("issuance must coincide with interactive confirmation")
        expected_expiry = self.issued_at + timedelta(minutes=self.authorization_window_minutes)
        if self.expires_at != expected_expiry:
            raise ValueError("authorization expiry does not match governed window")
        return self


class ExecutionAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization: AuthorizationBody

    @model_validator(mode="after")
    def validate_transaction_identity(self) -> Self:
        expected = _sha256(_canonical_json_bytes(self.authorization))
        if self.transaction_id != expected:
            raise ValueError("transaction ID does not match canonical authorization bytes")
        return self


class ExecutionArtifactManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["TRANSACTION_BOUND_EXECUTABLE_GENERATED"] = (
        "TRANSACTION_BOUND_EXECUTABLE_GENERATED"
    )
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorization_design_record_sha256: Literal[
        "191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463"
    ] = DESIGN_RECORD_SHA256
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: Literal[
        "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
    ] = SUCCESSOR_RUNTIME_SHA256
    generator_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    executable_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notebook_container_is_semantic_payload_identity: Literal[False] = False
    authorization_specific_kaggle_inputs: Literal[0] = 0
    authorization_producer_notebooks: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    permitted_kaggle_input_roles: tuple[
        Literal["durable_runtime"],
        Literal["model_snapshot"],
    ] = ("durable_runtime", "model_snapshot")
    platform_observation_required_before_save_and_run_all: Literal[True] = True
    platform_observation_persisted: Literal[False] = False
    runtime_execution_authorized: Literal[True] = True
    single_use_governance: Literal[True] = True
    runtime_anti_replay_established: Literal[False] = False


class PlatformObservationReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    control_id: Literal["PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"] = PLATFORM_CONTROL_ID
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    platform_observed_at: datetime
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    capability_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"] = "KAGGLE_NOTEBOOK_SETTINGS_UI"
    persisted_before_save_and_run_all: Literal[True] = True
    receipt_runtime_input: Literal[False] = False

    @field_validator("platform_observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "platform_observed_at")


class TerminalDisposition(StrEnum):
    CONSUMED = "CONSUMED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    EXPIRED_UNUSED = "EXPIRED_UNUSED"
    CANCELLED_UNUSED = "CANCELLED_UNUSED"
    ABANDONED_BEFORE_EXECUTION = "ABANDONED_BEFORE_EXECUTION"


class ObservedC4State(StrEnum):
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    INVALID_EXECUTION = "INVALID_EXECUTION"


class TerminalReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    transaction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: TerminalDisposition
    execution_attempted: bool
    observed_c4_state: ObservedC4State | None = None
    terminalized_at: datetime
    saved_version_id: int | None = Field(default=None, ge=1)
    platform_observation_receipt_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    evidence_zip_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    terminal_log_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    authorization_reusable: Literal[False] = False
    repository_acceptance_established: Literal[False] = False
    p5_requalified: Literal[False] = False
    p6_requalified: Literal[False] = False

    @field_validator("terminalized_at")
    @classmethod
    def normalize_terminalized_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "terminalized_at")

    @model_validator(mode="after")
    def validate_terminal_semantics(self) -> Self:
        unused = self.disposition in {
            TerminalDisposition.EXPIRED_UNUSED,
            TerminalDisposition.CANCELLED_UNUSED,
            TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
        }
        if unused and self.execution_attempted:
            raise ValueError("unused terminal disposition cannot report execution attempted")
        if unused and self.observed_c4_state is not None:
            raise ValueError("unused terminal disposition cannot carry a C4 observation")
        if self.disposition is TerminalDisposition.CONSUMED:
            if not self.execution_attempted:
                raise ValueError("CONSUMED requires execution attempted")
            if self.observed_c4_state is None:
                raise ValueError("CONSUMED requires observed C4 state")
        if self.observed_c4_state is ObservedC4State.QUALIFIED:
            if self.platform_observation_receipt_sha256 is None:
                raise ValueError("QUALIFIED observation requires platform receipt identity")
            if self.evidence_zip_sha256 is None:
                raise ValueError("QUALIFIED observation requires evidence ZIP identity")
            if self.saved_version_id is None:
                raise ValueError("QUALIFIED observation requires saved version identity")
        return self


def _normalize_time(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def _canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _artifact_json_bytes(value: object) -> bytes:
    return _canonical_json_bytes(value) + b"\n"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ARTIFACT_MISSING",
            "required artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _read_json_object(
    root: Path,
    relative: Path,
) -> dict[str, object]:
    try:
        parsed: object = json.loads(_read_required(root, relative))
    except json.JSONDecodeError as error:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_JSON_INVALID",
            "required JSON artifact is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(parsed, dict):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_JSON_INVALID",
            "required JSON artifact must contain one object",
            relative.as_posix(),
        )
    return cast(dict[str, object], parsed)


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return (
        completed.returncode,
        completed.stdout.strip(),
        completed.stderr.strip(),
    )


def _require_git(root: Path, *arguments: str) -> str:
    code, stdout, _ = _git(root, *arguments)
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_GIT_STATE_FAILED",
            "unable to inspect repository state",
        )
    return stdout


def _require_design_ancestor(root: Path) -> None:
    code, _, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        DESIGN_MERGE_COMMIT,
        "HEAD",
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_DESIGN_NOT_ANCESTOR",
            "merged authorization design is not an ancestor of HEAD",
        )


def _verify_hash(
    root: Path,
    relative: Path,
    expected_sha256: str,
) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected_sha256:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_IDENTITY_DRIFT",
            "bound authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _nested_mapping(
    record: dict[str, object],
    key: str,
    path: Path,
) -> dict[str, object]:
    value = record.get(key)
    if not isinstance(value, dict):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_DESIGN_CONTRACT_DRIFT",
            f"authorization design field is not an object: {key}",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _validate_design(root: Path) -> None:
    payload = _verify_hash(
        root,
        DESIGN_RECORD_PATH,
        DESIGN_RECORD_SHA256,
    )
    record = _read_json_object(root, DESIGN_RECORD_PATH)
    required = {
        "status": "DESIGN_FROZEN_NOT_EXECUTED",
        "authorization_architecture": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "c4_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
    }
    drift = tuple(key for key, expected in required.items() if record.get(key) != expected)
    if drift:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_DESIGN_CONTRACT_DRIFT",
            "authorization design contract drifted: " + ",".join(drift),
            DESIGN_RECORD_PATH.as_posix(),
        )

    if _nested_mapping(
        record,
        "execution_budget",
        DESIGN_RECORD_PATH,
    ) != ExecutionBudget().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_BUDGET_DRIFT",
            "authorization design execution budget drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    if _nested_mapping(
        record,
        "runtime_model",
        DESIGN_RECORD_PATH,
    ) != RuntimeModelContract().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_RUNTIME_CONTRACT_DRIFT",
            "authorization design runtime/model contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    if _nested_mapping(
        record,
        "qualification",
        DESIGN_RECORD_PATH,
    ) != QualificationContract().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_QUALIFICATION_DRIFT",
            "authorization design qualification contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    if _nested_mapping(
        record,
        "evidence",
        DESIGN_RECORD_PATH,
    ) != EvidenceContract().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_EVIDENCE_CONTRACT_DRIFT",
            "authorization design evidence contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    if _nested_mapping(
        record,
        "platform",
        DESIGN_RECORD_PATH,
    ) != RequiredPlatform().model_dump(mode="json"):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_PLATFORM_DRIFT",
            "authorization design required platform contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    human = _nested_mapping(
        record,
        "human_authorization",
        DESIGN_RECORD_PATH,
    )
    required_human = {
        "fresh_human_authority_required": True,
        "confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "challenge_must_be_dynamic": True,
        "exact_challenge_retype_required": True,
        "confirmation_binds_exact_authorization_intent": True,
        "challenge_synthesis_by_runtime_prohibited": True,
        "challenge_synthesis_by_assistant_prohibited": True,
        "challenge_synthesis_by_model_prohibited": True,
        "challenge_synthesis_by_issuer_prohibited": True,
        "maximum_confirmation_age_minutes": MAX_CONFIRMATION_AGE_MINUTES,
        "default_authorization_window_minutes": DEFAULT_WINDOW_MINUTES,
        "maximum_authorization_window_minutes": MAX_WINDOW_MINUTES,
    }
    if any(human.get(key) != value for key, value in required_human.items()):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_HUMAN_CONTROL_DRIFT",
            "human authorization contract drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    observation = _nested_mapping(
        record,
        "platform_observation_receipt",
        DESIGN_RECORD_PATH,
    )
    if observation.get("control_id") != PLATFORM_CONTROL_ID:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
            "durable platform observation control drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if observation.get("durable_receipt_required") is not True:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
            "durable platform observation receipt requirement drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if observation.get("receipt_must_exist_before_save_and_run_all") is not True:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_PLATFORM_CONTROL_DRIFT",
            "platform observation ordering drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )

    if _sha256(payload) != DESIGN_RECORD_SHA256:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_DESIGN_IDENTITY_DRIFT",
            "authorization design bytes drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )


def _validate_implementation_authorities(root: Path) -> bytes:
    _verify_hash(
        root,
        IMPLEMENTATION_REVIEW_PATH,
        IMPLEMENTATION_REVIEW_SHA256,
    )
    _verify_hash(
        root,
        IMPLEMENTATION_RECORD_PATH,
        IMPLEMENTATION_RECORD_SHA256,
    )
    _verify_hash(
        root,
        QUALIFICATION_REQUEST_PATH,
        QUALIFICATION_REQUEST_SHA256,
    )
    _verify_hash(
        root,
        REUSABLE_PREFIX_RECEIPT_PATH,
        REUSABLE_PREFIX_RECEIPT_SHA256,
    )
    return _verify_hash(
        root,
        SUCCESSOR_RUNTIME_PATH,
        SUCCESSOR_RUNTIME_SHA256,
    )


def _static_review(root: Path) -> dict[str, object]:
    _validate_design(root)
    _validate_implementation_authorities(root)
    source = _read_required(root, SOURCE_PATH)
    template = _read_required(root, TEMPLATE_PATH)
    test = _read_required(root, TEST_PATH)
    report = _read_required(root, REPORT_PATH)
    runbook = _read_required(root, RUNBOOK_PATH)
    return {
        "schema_version": "1.0.0",
        "review_id": (
            "auragateway-canonical-synthetic-prefix-c4-single-use-execution-authorization-v1-review"
        ),
        "status": "APPROVED_STATIC_ISSUER_IMPLEMENTATION",
        "design_merge_commit": DESIGN_MERGE_COMMIT,
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "implementation_review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "implementation_record_sha256": IMPLEMENTATION_RECORD_SHA256,
        "qualification_request_sha256": QUALIFICATION_REQUEST_SHA256,
        "reusable_prefix_receipt_sha256": REUSABLE_PREFIX_RECEIPT_SHA256,
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "source_sha256": _sha256(source),
        "generator_contract_sha256": _sha256(template),
        "test_sha256": _sha256(test),
        "report_sha256": _sha256(report),
        "runbook_sha256": _sha256(runbook),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "authorization_architecture": "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "transaction_id_derivation": "SHA256_CANONICAL_AUTHORIZATION_BYTES",
        "canonical_request_payload_sha256": CANONICAL_REQUEST_PAYLOAD_SHA256,
        "full_prompt_token_count": FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": FULL_PROMPT_TOKEN_SHA256,
        "reusable_prefix_token_count": REUSABLE_PREFIX_TOKEN_COUNT,
        "reusable_prefix_token_sha256": REUSABLE_PREFIX_TOKEN_SHA256,
        "maximum_model_requests": 3,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_worker_teardowns": 3,
        "maximum_hidden_retries": 0,
        "maximum_replacement_requests": 0,
        "exact_pass_count_required": 3,
        "strict_duplicate_key_rejection": True,
        "strict_integer_value_validation": True,
        "finish_reason_stop_required": True,
        "durable_platform_observation_required": True,
        "platform_observation_control_id": PLATFORM_CONTROL_ID,
        "platform_observation_receipt_runtime_input": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "runtime_decision_is_repository_acceptance": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "c4_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "next_gate": NEXT_GATE,
    }


def _static_record(
    root: Path,
    review_bytes: bytes,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_id": (
            "auragateway-canonical-synthetic-prefix-c4-single-use-execution-authorization-v1"
        ),
        "status": "IMPLEMENTED_NOT_ISSUED",
        "design_merge_commit": DESIGN_MERGE_COMMIT,
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "successor_runtime_sha256": SUCCESSOR_RUNTIME_SHA256,
        "review_sha256": _sha256(review_bytes),
        "source_path": SOURCE_PATH.as_posix(),
        "template_path": TEMPLATE_PATH.as_posix(),
        "authorization_scope": AUTHORIZATION_SCOPE,
        "canonical_request_payload_sha256": CANONICAL_REQUEST_PAYLOAD_SHA256,
        "reusable_prefix_token_sha256": REUSABLE_PREFIX_TOKEN_SHA256,
        "maximum_model_requests": 3,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_worker_teardowns": 3,
        "maximum_hidden_retries": 0,
        "maximum_replacement_requests": 0,
        "exact_pass_count_required": 3,
        "runtime_decision_is_repository_acceptance": False,
        "durable_platform_observation_required": True,
        "platform_observation_control_id": PLATFORM_CONTROL_ID,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_anti_replay_established": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "model_loads_performed": 0,
        "worker_starts_performed": 0,
        "c4_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "next_gate": NEXT_GATE,
    }


def generate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    review_bytes = _artifact_json_bytes(_static_review(root))
    record_bytes = _artifact_json_bytes(_static_record(root, review_bytes))
    for relative, payload in (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return {
        "status": "C4_AUTHORIZATION_STATIC_ARTIFACTS_GENERATED",
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "platform_observation_persisted": False,
        "next_gate": NEXT_GATE,
    }


def validate_static(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_design_ancestor(root)
    review_bytes = _artifact_json_bytes(_static_review(root))
    record_bytes = _artifact_json_bytes(_static_record(root, review_bytes))
    for relative, expected in (
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        if _read_required(root, relative) != expected:
            raise AuthorizationIssuerError(
                "C4_AUTHORIZATION_STATIC_ARTIFACT_DRIFT",
                "generated static issuer artifact drifted",
                relative.as_posix(),
            )
    for relative in (
        LIVE_AUTHORIZATION_PATH,
        LIVE_MANIFEST_PATH,
        PLATFORM_OBSERVATION_RECEIPT_PATH,
        TERMINAL_RECEIPT_PATH,
    ):
        if (root / relative).exists():
            raise AuthorizationIssuerError(
                "C4_AUTHORIZATION_LIVE_LIFECYCLE_PRESENT",
                "static validation requires no live lifecycle artifact",
                relative.as_posix(),
            )
    return {
        "status": "C4_EXECUTION_AUTHORIZATION_V1_VALID",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "maximum_model_requests": 3,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "maximum_worker_teardowns": 3,
        "maximum_hidden_retries": 0,
        "maximum_replacement_requests": 0,
        "full_prompt_token_count": FULL_PROMPT_TOKEN_COUNT,
        "reusable_prefix_token_count": REUSABLE_PREFIX_TOKEN_COUNT,
        "exact_pass_count_required": 3,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "governed_executable_generated": False,
        "platform_observation_persisted": False,
        "kaggle_execution_performed": False,
        "c4_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "next_gate": NEXT_GATE,
    }


def _require_merged_clean_main(root: Path) -> tuple[str, str]:
    branch = _require_git(root, "branch", "--show-current")
    if branch != "main":
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_NOT_ON_MAIN",
            "live authorization requires synchronized main",
        )
    head = _require_git(root, "rev-parse", "HEAD")
    origin_main = _require_git(root, "rev-parse", "origin/main")
    if head != origin_main:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "HEAD must equal origin/main before live authorization",
        )
    status = _require_git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "repository must be clean before live authorization",
        )
    code, _, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        DESIGN_MERGE_COMMIT,
        head,
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_DESIGN_NOT_MERGED",
            "authorization design is not contained in current main",
        )

    issuer_merge_commit = _require_git(
        root,
        "log",
        "--first-parent",
        "--format=%H",
        "--max-count=1",
        "--",
        SOURCE_PATH.as_posix(),
    )
    if len(issuer_merge_commit) != 40:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ISSUER_NOT_MERGED",
            "unable to resolve issuer merge commit on main",
        )
    code, _, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        issuer_merge_commit,
        head,
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ISSUER_NOT_MERGED",
            "issuer merge commit is not an ancestor of synchronized main",
        )

    governed_paths = (
        SOURCE_PATH,
        TEMPLATE_PATH,
        REVIEW_PATH,
        RECORD_PATH,
    )
    code, _, _ = _git(
        root,
        "diff",
        "--quiet",
        issuer_merge_commit,
        "HEAD",
        "--",
        *(path.as_posix() for path in governed_paths),
    )
    if code != 0:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ISSUER_POSTMERGE_DRIFT",
            "issuer identities changed after issuer merge",
        )
    return head, issuer_merge_commit


def build_intent(
    root: Path,
    issuer_merge_commit: str,
    *,
    prepared_at: datetime,
    window_minutes: int,
    intent_id: str,
) -> AuthorizationIntent:
    root = root.resolve()
    _validate_design(root)
    runtime_payload = _validate_implementation_authorities(root)
    return AuthorizationIntent(
        intent_id=intent_id,
        prepared_at=prepared_at,
        authorization_window_minutes=window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        issuer_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        generator_contract_sha256=_sha256(_read_required(root, TEMPLATE_PATH)),
        runtime_payload_sha256=_sha256(runtime_payload),
        runtime=RuntimeModelContract(),
        budget=ExecutionBudget(),
        qualification=QualificationContract(),
        evidence=EvidenceContract(),
        required_platform=RequiredPlatform(),
    )


def authorization_challenge(intent: AuthorizationIntent) -> str:
    return _sha256(_canonical_json_bytes(intent))


def build_authorization(
    intent: AuthorizationIntent,
    *,
    challenge: str,
    confirmed_at: datetime,
) -> tuple[ExecutionAuthorization, bytes]:
    expected_challenge = authorization_challenge(intent)
    if challenge != expected_challenge:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_CHALLENGE_DRIFT",
            "authorization challenge does not bind exact intent",
        )
    confirmed = _normalize_time(confirmed_at, "confirmed_at")
    if confirmed < intent.prepared_at:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_CONFIRMATION_TIME_INVALID",
            "operator confirmation precedes authorization intent",
        )
    if confirmed - intent.prepared_at > timedelta(minutes=MAX_CONFIRMATION_AGE_MINUTES):
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_CONFIRMATION_STALE",
            "operator confirmation exceeded freshness window",
        )

    body = AuthorizationBody(
        authorization_id="c4qual-" + intent.intent_id,
        authorization_challenge_sha256=challenge,
        operator_confirmed_at=confirmed,
        issued_at=confirmed,
        expires_at=confirmed + timedelta(minutes=intent.authorization_window_minutes),
        authorization_window_minutes=intent.authorization_window_minutes,
        issuer_merge_commit=intent.issuer_merge_commit,
        issuer_source_sha256=intent.issuer_source_sha256,
        generator_contract_sha256=intent.generator_contract_sha256,
        runtime=RuntimeModelContract(),
        budget=ExecutionBudget(),
        qualification=QualificationContract(),
        evidence=EvidenceContract(),
        required_platform=RequiredPlatform(),
    )
    transaction_id = _sha256(_canonical_json_bytes(body))
    authorization = ExecutionAuthorization(
        transaction_id=transaction_id,
        authorization=body,
    )
    return authorization, _canonical_json_bytes(authorization)


def _render_wrapper(
    root: Path,
    authorization: ExecutionAuthorization,
    authorization_bytes: bytes,
) -> tuple[bytes, str]:
    template = _read_required(root, TEMPLATE_PATH).decode("utf-8")
    runtime_payload = _read_required(root, SUCCESSOR_RUNTIME_PATH)
    replacements = {
        "__AUTHORIZATION_B64__": base64.b64encode(authorization_bytes).decode("ascii"),
        "__RUNTIME_PAYLOAD_B64__": base64.b64encode(runtime_payload).decode("ascii"),
        "__TRANSACTION_ID__": authorization.transaction_id,
        "__ISSUER_MERGE_COMMIT__": (authorization.authorization.issuer_merge_commit),
        "__ISSUER_SOURCE_SHA256__": (authorization.authorization.issuer_source_sha256),
        "__RUNTIME_PAYLOAD_SHA256__": SUCCESSOR_RUNTIME_SHA256,
        "__GENERATOR_CONTRACT_SHA256__": (authorization.authorization.generator_contract_sha256),
    }
    rendered = template
    for marker, value in replacements.items():
        if rendered.count(marker) != 1:
            raise AuthorizationIssuerError(
                "C4_AUTHORIZATION_TEMPLATE_MARKER_DRIFT",
                f"wrapper marker cardinality drifted: {marker}",
                TEMPLATE_PATH.as_posix(),
            )
        rendered = rendered.replace(marker, value, 1)
    if "__" + "AUTHORIZATION_B64__" in rendered:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_TEMPLATE_RENDER_INCOMPLETE",
            "wrapper rendering left unresolved markers",
        )
    payload = rendered.encode("utf-8")
    compile(
        payload,
        "<c4-transaction-bound-wrapper>",
        "exec",
    )
    return payload, _sha256(payload)


def _notebook_bytes(wrapper_payload: bytes) -> bytes:
    source = wrapper_payload.decode("utf-8").splitlines(keepends=True)
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source,
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
            },
            "auragateway": {
                "notebook_name": NOTEBOOK_NAME,
                "authorization_specific_kaggle_inputs": 0,
                "manual_confirmation_json_files": 0,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return _artifact_json_bytes(notebook)


def authorize_generate(
    root: Path,
    output: Path,
    *,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    if not 1 <= window_minutes <= MAX_WINDOW_MINUTES:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_WINDOW_INVALID",
            "authorization window is outside governed bounds",
        )

    _, issuer_merge_commit = _require_merged_clean_main(root)
    validate_static(root)

    for relative in (
        LIVE_AUTHORIZATION_PATH,
        LIVE_MANIFEST_PATH,
        PLATFORM_OBSERVATION_RECEIPT_PATH,
        TERMINAL_RECEIPT_PATH,
    ):
        if (root / relative).exists():
            raise AuthorizationIssuerError(
                "C4_AUTHORIZATION_LIVE_LIFECYCLE_PRESENT",
                "fresh issuance requires no existing live lifecycle artifact",
                relative.as_posix(),
            )
    if output.exists():
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_OUTPUT_ALREADY_EXISTS",
            "governed notebook output already exists",
            str(output),
        )

    prepared_at = datetime.now(UTC)
    intent = build_intent(
        root,
        issuer_merge_commit,
        prepared_at=prepared_at,
        window_minutes=window_minutes,
        intent_id=secrets.token_hex(16),
    )
    challenge = authorization_challenge(intent)

    print("")
    print("=== FRESH HUMAN AUTHORIZATION REQUIRED ===")
    print("Retype this exact dynamic SHA-256 challenge:")
    print(challenge)
    confirmation = input("CONFIRMATION> ").strip()

    if confirmation != challenge:
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_HUMAN_CONFIRMATION_MISMATCH",
            "operator confirmation did not exactly match dynamic challenge",
        )

    confirmed_at = datetime.now(UTC)
    authorization, authorization_bytes = build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=confirmed_at,
    )
    wrapper_payload, wrapper_sha256 = _render_wrapper(
        root,
        authorization,
        authorization_bytes,
    )
    notebook_bytes = _notebook_bytes(wrapper_payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(notebook_bytes)

    live_authorization_path = root / LIVE_AUTHORIZATION_PATH
    live_authorization_path.parent.mkdir(parents=True, exist_ok=True)
    live_authorization_path.write_bytes(_artifact_json_bytes(authorization))

    manifest = ExecutionArtifactManifest(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(authorization_bytes),
        issuer_merge_commit=issuer_merge_commit,
        issuer_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        generator_contract_sha256=_sha256(_read_required(root, TEMPLATE_PATH)),
        executable_payload_sha256=wrapper_sha256,
        notebook_container_sha256=_sha256(notebook_bytes),
    )
    (root / LIVE_MANIFEST_PATH).write_bytes(_artifact_json_bytes(manifest))

    return {
        "status": "C4_TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        "transaction_id": authorization.transaction_id,
        "authorization_sha256": _sha256(authorization_bytes),
        "issuer_merge_commit": issuer_merge_commit,
        "runtime_payload_sha256": SUCCESSOR_RUNTIME_SHA256,
        "generator_contract_sha256": (authorization.authorization.generator_contract_sha256),
        "executable_payload_sha256": wrapper_sha256,
        "notebook_container_sha256": _sha256(notebook_bytes),
        "notebook_path": str(output),
        "notebook_name": NOTEBOOK_NAME,
        "platform_observation_persisted": False,
        "runtime_execution_authorized": True,
        "authorization_reusable": False,
        "c4_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }


def record_platform_observation(
    root: Path,
    *,
    observed_at: datetime,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ALREADY_TERMINAL",
            "terminal authority cannot accept a platform observation",
        )
    if (root / PLATFORM_OBSERVATION_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "C4_PLATFORM_OBSERVATION_ALREADY_EXISTS",
            "platform observation is single-write",
        )

    authorization_bytes = _read_required(
        root,
        LIVE_AUTHORIZATION_PATH,
    )
    manifest_bytes = _read_required(
        root,
        LIVE_MANIFEST_PATH,
    )
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)
    canonical_authorization = _canonical_json_bytes(authorization)
    if manifest.transaction_id != authorization.transaction_id:
        raise AuthorizationIssuerError(
            "C4_PLATFORM_TRANSACTION_DRIFT",
            "live manifest transaction identity drifted",
        )
    if manifest.authorization_sha256 != _sha256(canonical_authorization):
        raise AuthorizationIssuerError(
            "C4_PLATFORM_AUTHORIZATION_DRIFT",
            "live manifest no longer binds live authorization",
        )

    observed = _normalize_time(
        observed_at,
        "platform_observed_at",
    )
    if observed < authorization.authorization.issued_at:
        raise AuthorizationIssuerError(
            "C4_PLATFORM_OBSERVATION_TIME_INVALID",
            "platform observation predates authorization issuance",
        )

    receipt = PlatformObservationReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        manifest_sha256=_sha256(manifest_bytes),
        platform_observed_at=observed,
    )
    receipt_bytes = _artifact_json_bytes(receipt)
    (root / PLATFORM_OBSERVATION_RECEIPT_PATH).write_bytes(receipt_bytes)
    return {
        "status": "C4_DURABLE_PLATFORM_OBSERVATION_PERSISTED",
        "transaction_id": receipt.transaction_id,
        "receipt_sha256": _sha256(receipt_bytes),
        "accelerator": receipt.accelerator,
        "allocated_gpu_count": receipt.allocated_gpu_count,
        "internet_enabled": receipt.internet_enabled,
        "persisted_before_save_and_run_all": True,
        "runtime_execution_authorized": True,
        "authorization_reusable": False,
        "next_gate": NEXT_GATE_AFTER_OBSERVATION,
    }


def terminalize(
    root: Path,
    *,
    disposition: TerminalDisposition,
    observed_c4_state: ObservedC4State | None,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    terminal_log_sha256: str | None,
) -> dict[str, object]:
    root = root.resolve()
    if (root / TERMINAL_RECEIPT_PATH).exists():
        raise AuthorizationIssuerError(
            "C4_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization terminal receipt already exists",
        )

    authorization_bytes = _read_required(
        root,
        LIVE_AUTHORIZATION_PATH,
    )
    manifest_bytes = _read_required(
        root,
        LIVE_MANIFEST_PATH,
    )
    authorization = ExecutionAuthorization.model_validate_json(authorization_bytes)
    manifest = ExecutionArtifactManifest.model_validate_json(manifest_bytes)

    canonical_authorization = _canonical_json_bytes(authorization)
    if manifest.authorization_sha256 != _sha256(canonical_authorization):
        raise AuthorizationIssuerError(
            "C4_LIFECYCLE_IDENTITY_DRIFT",
            "live manifest no longer binds live authorization",
        )

    platform_sha: str | None = None
    if (root / PLATFORM_OBSERVATION_RECEIPT_PATH).is_file():
        platform_bytes = _read_required(
            root,
            PLATFORM_OBSERVATION_RECEIPT_PATH,
        )
        platform = PlatformObservationReceipt.model_validate_json(platform_bytes)
        if platform.transaction_id != authorization.transaction_id:
            raise AuthorizationIssuerError(
                "C4_PLATFORM_TRANSACTION_DRIFT",
                "platform observation transaction identity drifted",
            )
        platform_sha = _sha256(platform_bytes)

    unused = disposition in {
        TerminalDisposition.EXPIRED_UNUSED,
        TerminalDisposition.CANCELLED_UNUSED,
        TerminalDisposition.ABANDONED_BEFORE_EXECUTION,
    }
    receipt = TerminalReceipt(
        transaction_id=authorization.transaction_id,
        authorization_sha256=_sha256(canonical_authorization),
        manifest_sha256=_sha256(manifest_bytes),
        disposition=disposition,
        execution_attempted=not unused,
        observed_c4_state=observed_c4_state,
        terminalized_at=datetime.now(UTC),
        saved_version_id=saved_version_id,
        platform_observation_receipt_sha256=platform_sha,
        evidence_zip_sha256=evidence_zip_sha256,
        terminal_log_sha256=terminal_log_sha256,
    )
    (root / TERMINAL_RECEIPT_PATH).write_bytes(_artifact_json_bytes(receipt))
    return {
        "status": "C4_EXECUTION_AUTHORIZATION_TERMINAL",
        "transaction_id": receipt.transaction_id,
        "disposition": receipt.disposition.value,
        "execution_attempted": receipt.execution_attempted,
        "observed_c4_state": (
            None if receipt.observed_c4_state is None else receipt.observed_c4_state.value
        ),
        "platform_observation_receipt_bound": platform_sha is not None,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "repository_acceptance_established": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }


def _default_output() -> Path:
    return Path.home() / "Desktop" / "ag-c4-canonical-prefix-qual-v1.ipynb"


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "generate",
            "validate",
            "authorize-generate",
            "record-platform-observation",
            "terminalize",
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=DEFAULT_WINDOW_MINUTES,
    )
    parser.add_argument("--platform-observed-at")
    parser.add_argument(
        "--disposition",
        choices=tuple(item.value for item in TerminalDisposition),
    )
    parser.add_argument(
        "--c4-state",
        choices=tuple(item.value for item in ObservedC4State),
    )
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip-sha256")
    parser.add_argument("--terminal-log-sha256")
    return parser


def _print_error(error: AuthorizationIssuerError) -> None:
    print(
        _canonical_json_bytes(
            {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            }
        ).decode("utf-8"),
        file=sys.stderr,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        result: dict[str, object]
        if args.command == "generate":
            result = generate_static(root)
        elif args.command == "validate":
            result = validate_static(root)
        elif args.command == "authorize-generate":
            output = Path(args.output).resolve() if args.output else _default_output()
            result = authorize_generate(
                root,
                output,
                window_minutes=args.window_minutes,
            )
        elif args.command == "record-platform-observation":
            if args.platform_observed_at is None:
                raise AuthorizationIssuerError(
                    "C4_AUTHORIZATION_ARGUMENT_MISSING",
                    "--platform-observed-at is required",
                )
            result = record_platform_observation(
                root,
                observed_at=datetime.fromisoformat(args.platform_observed_at),
            )
        else:
            if args.disposition is None:
                raise AuthorizationIssuerError(
                    "C4_AUTHORIZATION_ARGUMENT_MISSING",
                    "--disposition is required",
                )
            result = terminalize(
                root,
                disposition=TerminalDisposition(args.disposition),
                observed_c4_state=(
                    None if args.c4_state is None else ObservedC4State(args.c4_state)
                ),
                saved_version_id=args.saved_version_id,
                evidence_zip_sha256=args.evidence_zip_sha256,
                terminal_log_sha256=args.terminal_log_sha256,
            )
    except (
        AuthorizationIssuerError,
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, AuthorizationIssuerError):
            _print_error(error)
        else:
            _print_error(
                AuthorizationIssuerError(
                    "C4_AUTHORIZATION_VALIDATION_FAILED",
                    str(error),
                )
            )
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
