"""Generate the canonical synthetic-prefix C4 behavioral qualification runtime V1.

This producer derives one execution-inert C4 successor from the accepted B-vs-D
exact-runtime substrate. It performs no Kaggle, GPU, model, worker, or model-request
execution and issues no execution authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCE_MAIN_COMMIT: Final = "7edfc0e321b22ce18c5972f3ed92d2240e82214a"

FORMATTER_VERSION: Final = "ruff 0.15.21"
FORMATTER_CONFIG_PATH: Final = Path("pyproject.toml")
FORMATTER_CONFIG_SHA256: Final = "5387ea09341bde18d73518e28a236f65865918dd406fcb13824c0c8156a57103"

QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "canonical_synthetic_prefix_c4_behavioral_qualification_v1_request.json"
)
ARCHITECTURE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_v1_review.json"
)
CANONICAL_CORPUS_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_corpus_candidate_v2.txt"
)
REUSABLE_PREFIX_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_reusable_prefix_identity_v1.json"
)
PREDECESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_runtime_v1.py"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "canonical_synthetic_prefix_c4_behavioral_qualification_implementation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_canonical_synthetic_prefix_c4_behavioral_qualification_implementation_v1.py"
)
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_runtime_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_behavioral_qualification_"
    "implementation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_behavioral_qualification_"
    "implementation_v1.json"
)

QUALIFICATION_ID: Final = "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
CANONICAL_CORPUS_VERSION: Final = "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1"
EXPECTED_CORPUS_SHA256: Final = "140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"
EXPECTED_FULL_PROMPT_TOKEN_COUNT: Final = 899
EXPECTED_FULL_PROMPT_TOKEN_SHA256: Final = (
    "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
)
EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT: Final = 880
EXPECTED_REUSABLE_PREFIX_TOKEN_SHA256: Final = (
    "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
)
EXPECTED_REQUEST_PAYLOAD_SHA256: Final = (
    "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
)
EXPECTED_REUSABLE_PREFIX_RECEIPT_SHA256: Final = (
    "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
)
EXPECTED_PREDECESSOR_RUNTIME_SHA256: Final = (
    "fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39"
)
EXPECTED_OBJECT_CANONICAL: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
EXPECTED_OBJECT_SHA256: Final = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
FINAL_USER_BOUNDARY_SENTINEL: Final = "__AURAGATEWAY_FINAL_USER_BOUNDARY_SENTINEL_V1__"

CHANGED_EXISTING_FUNCTIONS: Final = ("main",)
ADDED_FUNCTIONS: Final = (
    "c4_bundle_outputs",
    "c4_json_type",
    "c4_longest_common_prefix",
    "c4_object_pairs",
    "c4_public_observation",
    "c4_request_messages",
    "c4_request_payload",
    "c4_response_projection",
    "c4_token_identity",
    "c4_token_sequence",
    "c4_tokenize_payload",
    "decide_c4_qualification",
    "initialize_c4_journal",
    "persist_c4_pre_request_identity",
    "run_c4_fresh_worker_observation",
    "run_c4_observation",
    "write_c4_results",
)

C4_OUTPUT_NAMES: Final = (
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

NEXT_GATE: Final = (
    "MERGE_THEN_DESIGN_CANONICAL_SYNTHETIC_PREFIX_C4_SINGLE_USE_EXECUTION_AUTHORIZATION_V1"
)


class C4ImplementationError(RuntimeError):
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
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImplementationReview(FrozenModel):
    schema_version: str = "1.0.0"
    review_id: str
    status: str
    source_main_commit: str
    qualification_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    architecture_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reusable_prefix_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    focused_test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    formatter_version: str
    formatter_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_formatter_canonicalized: bool
    predecessor_formatter_canonical: bool
    formatter_idempotence_verified: bool
    changed_existing_functions: tuple[str, ...]
    added_functions: tuple[str, ...]
    unchanged_existing_function_count: int = Field(ge=1)
    full_prompt_token_count: int
    full_prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reusable_prefix_token_count: int
    reusable_prefix_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observations: int
    maximum_model_requests: int
    maximum_model_loads: int
    maximum_worker_starts: int
    maximum_hidden_retries: int
    maximum_replacement_requests: int
    strict_duplicate_key_rejection: bool
    strict_integer_value_validation: bool
    finish_reason_stop_required: bool
    behavioral_failure_completes_three_observations: bool
    execution_failure_stops_without_replacement: bool
    runtime_budget_attempt_semantics: bool
    platform_budget_deferred_to_authorization_wrapper: bool
    kaggle_session_budget_runtime_enforced: bool
    save_and_run_all_budget_runtime_enforced: bool
    evidence_schema_names_frozen: bool
    p5_p6_successor_lineage_parent: bool
    runtime_execution_authorized: bool
    authorization_issuer_included: bool
    p5_execution_authorized: bool
    p6_execution_authorized: bool
    next_gate: str

    @model_validator(mode="after")
    def exact(self) -> ImplementationReview:
        if self.status != "APPROVED_STATIC_C4_EXECUTION_HARNESS":
            raise ValueError("implementation review status drifted")
        if self.formatter_version != FORMATTER_VERSION:
            raise ValueError("formatter version drifted")
        if self.formatter_config_sha256 != FORMATTER_CONFIG_SHA256:
            raise ValueError("formatter config identity drifted")
        if not self.runtime_formatter_canonicalized:
            raise ValueError("generated runtime is not formatter-canonical")
        if not self.predecessor_formatter_canonical:
            raise ValueError("predecessor formatter identity drifted")
        if not self.formatter_idempotence_verified:
            raise ValueError("formatter idempotence was not verified")
        if self.changed_existing_functions != CHANGED_EXISTING_FUNCTIONS:
            raise ValueError("changed function inventory drifted")
        if self.added_functions != ADDED_FUNCTIONS:
            raise ValueError("added function inventory drifted")
        if (
            self.full_prompt_token_count,
            self.reusable_prefix_token_count,
            self.observations,
        ) != (899, 880, 3):
            raise ValueError("frozen identity or observation cardinality drifted")
        if (
            self.maximum_model_requests,
            self.maximum_model_loads,
            self.maximum_worker_starts,
        ) != (3, 3, 3):
            raise ValueError("runtime action budget drifted")
        if self.maximum_hidden_retries != 0:
            raise ValueError("hidden retry budget drifted")
        if self.maximum_replacement_requests != 0:
            raise ValueError("replacement request budget drifted")
        required_true = (
            self.strict_duplicate_key_rejection,
            self.strict_integer_value_validation,
            self.finish_reason_stop_required,
            self.behavioral_failure_completes_three_observations,
            self.execution_failure_stops_without_replacement,
            self.runtime_budget_attempt_semantics,
            self.platform_budget_deferred_to_authorization_wrapper,
            self.evidence_schema_names_frozen,
            self.p5_p6_successor_lineage_parent,
        )
        if not all(required_true):
            raise ValueError("required C4 implementation control is disabled")
        if self.kaggle_session_budget_runtime_enforced:
            raise ValueError("runtime cannot enforce Kaggle-session cardinality")
        if self.save_and_run_all_budget_runtime_enforced:
            raise ValueError("runtime cannot enforce Save & Run All cardinality")
        prohibited = (
            self.runtime_execution_authorized,
            self.authorization_issuer_included,
            self.p5_execution_authorized,
            self.p6_execution_authorized,
        )
        if any(prohibited):
            raise ValueError("static C4 implementation crossed authority boundary")
        return self


class ImplementationRecord(FrozenModel):
    schema_version: str = "1.0.0"
    record_id: str
    status: str
    source_main_commit: str
    qualification_id: str
    qualification_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    architecture_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_corpus_version: str
    canonical_corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reusable_prefix_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_runtime_path: str
    predecessor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_runtime_path: str
    successor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    formatter_version: str
    formatter_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_formatter_canonicalized: bool
    full_prompt_token_count: int
    full_prompt_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reusable_prefix_token_count: int
    reusable_prefix_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_requests_performed: int
    model_loads_performed: int
    worker_starts_performed: int
    kaggle_execution_performed: bool
    gpu_execution_performed: bool
    notebook_generated: bool
    live_authorization_issued: bool
    runtime_execution_authorized: bool
    c4_qualified: bool
    p5_requalified: bool
    p6_requalified: bool
    final_abc_measured: bool
    production_readiness_established: bool
    p5_p6_successor_must_derive_from_this_runtime: bool
    next_gate: str
    non_claims: tuple[str, ...] = Field(min_length=12)

    @model_validator(mode="after")
    def exact(self) -> ImplementationRecord:
        if self.status != "IMPLEMENTED_NOT_EXECUTED":
            raise ValueError("implementation record status drifted")
        if self.formatter_version != FORMATTER_VERSION:
            raise ValueError("implementation formatter version drifted")
        if self.formatter_config_sha256 != FORMATTER_CONFIG_SHA256:
            raise ValueError("implementation formatter config drifted")
        if not self.runtime_formatter_canonicalized:
            raise ValueError("implementation runtime is not formatter-canonical")
        if any(
            (
                self.model_requests_performed,
                self.model_loads_performed,
                self.worker_starts_performed,
            )
        ):
            raise ValueError("static producer recorded runtime execution")
        prohibited = (
            self.kaggle_execution_performed,
            self.gpu_execution_performed,
            self.notebook_generated,
            self.live_authorization_issued,
            self.runtime_execution_authorized,
            self.c4_qualified,
            self.p5_requalified,
            self.p6_requalified,
            self.final_abc_measured,
            self.production_readiness_established,
        )
        if any(prohibited):
            raise ValueError("static producer overclaimed state")
        if not self.p5_p6_successor_must_derive_from_this_runtime:
            raise ValueError("C4-to-P5/P6 lineage contract drifted")
        return self


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
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


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_ARTIFACT_MISSING",
            "required implementation artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _git_show(root: Path, commit: str, relative: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative.as_posix()}"],
        cwd=root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_GIT_AUTHORITY_UNAVAILABLE",
            "unable to read committed source authority",
            relative.as_posix(),
        )
    return completed.stdout


def require_source_main_ancestor(root: Path) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SOURCE_MAIN_COMMIT, "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_MAIN_DRIFT",
            "source main commit is not an ancestor of the candidate",
        )


def source_bound_authority(root: Path, relative: Path) -> bytes:
    worktree = _read_required(root, relative)
    committed = _git_show(root, SOURCE_MAIN_COMMIT, relative)
    if worktree != committed:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_AUTHORITY_DRIFT",
            "source authority drifted from bound main",
            relative.as_posix(),
        )
    return worktree


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_AUTHORITY_INVALID",
            f"{label} must be one object",
        )
    return cast(dict[str, object], value)


def _sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_AUTHORITY_INVALID",
            f"{label} must be one array",
        )
    return cast(list[object], value)


def _json_object(payload: bytes, label: str) -> dict[str, object]:
    try:
        parsed: object = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_AUTHORITY_INVALID",
            f"{label} is not valid UTF-8 JSON",
        ) from error
    return _mapping(parsed, label)


def _validate_request(payload: bytes) -> dict[str, object]:
    request = _json_object(payload, "qualification request")
    expected_scalars = {
        "schema_version": "1.0.0",
        "qualification_id": QUALIFICATION_ID,
        "runtime_execution_authorized": False,
        "authorization_issuer_included": False,
        "p5_execution_authorized": False,
        "p6_execution_authorized": False,
        "next_gate": "MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1",
    }
    for key, expected in expected_scalars.items():
        if request.get(key) != expected:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_REQUEST_DRIFT",
                "qualification request scalar drifted",
                key,
            )

    corpus = _mapping(request.get("canonical_corpus"), "canonical corpus")
    expected_corpus = {
        "version": CANONICAL_CORPUS_VERSION,
        "sha256": EXPECTED_CORPUS_SHA256,
        "rendered_prompt_token_count": EXPECTED_FULL_PROMPT_TOKEN_COUNT,
        "rendered_prompt_token_sha256": EXPECTED_FULL_PROMPT_TOKEN_SHA256,
        "final_object_canonical": EXPECTED_OBJECT_CANONICAL,
        "final_object_sha256": EXPECTED_OBJECT_SHA256,
    }
    for key, expected in expected_corpus.items():
        if corpus.get(key) != expected:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_REQUEST_DRIFT",
                "canonical corpus request identity drifted",
                key,
            )
    if corpus.get("message_roles") != ["system", "user", "assistant", "user"]:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REQUEST_DRIFT",
            "message-role topology drifted",
        )

    generation = _mapping(request.get("generation_contract"), "generation contract")
    if generation != {
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
        "response_format": None,
        "guided_decoding": None,
    }:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REQUEST_DRIFT",
            "generation contract drifted",
        )

    observation = _mapping(request.get("observation_contract"), "observation contract")
    if observation != {
        "case_count": 1,
        "observation_count": 3,
        "exact_pass_count_required": 3,
        "fresh_worker_per_observation": True,
        "zero_cached_prefix_baseline_required": True,
        "one_request_per_worker": True,
        "teardown_after_each_observation": True,
        "hidden_retries_permitted": 0,
        "replacement_requests_permitted": 0,
        "threshold_relaxation_permitted": False,
    }:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REQUEST_DRIFT",
            "observation contract drifted",
        )

    budget = _mapping(request.get("execution_budget"), "execution budget")
    expected_budget = {
        "maximum_kaggle_sessions": 1,
        "maximum_save_and_run_all_actions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 3,
        "maximum_worker_starts": 3,
        "maximum_model_requests": 3,
        "required_worker_teardowns": 3,
        "maximum_output_tokens_per_request": 32,
        "benchmark_trajectory_requests_permitted": 0,
        "external_network_requests_permitted": 0,
        "hidden_retries_permitted": 0,
        "replacement_requests_permitted": 0,
        "external_spend": 0,
    }
    if budget != expected_budget:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REQUEST_DRIFT",
            "execution budget drifted",
        )

    terminal_states = _sequence(request.get("terminal_states"), "terminal states")
    states = tuple(_mapping(item, "terminal state").get("state") for item in terminal_states)
    if states != ("QUALIFIED", "NOT_QUALIFIED", "INVALID_EXECUTION"):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REQUEST_DRIFT",
            "terminal state inventory drifted",
        )
    return request


def _validate_architecture_review(payload: bytes) -> dict[str, object]:
    review = _json_object(payload, "architecture review")
    expected = {
        "decision": "APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        "runtime_execution_authorized": False,
        "authorization_issuer_included": False,
        "next_gate": "MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1",
    }
    for key, value in expected.items():
        if review.get(key) != value:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_ARCHITECTURE_REVIEW_DRIFT",
                "architecture review drifted",
                key,
            )
    return review


def _validate_reusable_prefix_receipt(payload: bytes) -> dict[str, object]:
    if _sha256(payload) != EXPECTED_REUSABLE_PREFIX_RECEIPT_SHA256:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REUSABLE_PREFIX_RECEIPT_DRIFT",
            "reusable-prefix measurement receipt identity drifted",
            REUSABLE_PREFIX_RECEIPT_PATH.as_posix(),
        )
    receipt = _json_object(payload, "reusable-prefix receipt")
    measurement = _mapping(receipt.get("measurement"), "reusable-prefix measurement")
    expected = {
        "reusable_prefix_token_count": EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT,
        "reusable_prefix_token_sha256": EXPECTED_REUSABLE_PREFIX_TOKEN_SHA256,
        "full_prompt_token_count": EXPECTED_FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": EXPECTED_FULL_PROMPT_TOKEN_SHA256,
        "canonical_request_payload_sha256": EXPECTED_REQUEST_PAYLOAD_SHA256,
    }
    for key, value in expected.items():
        if measurement.get(key) != value:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_REUSABLE_PREFIX_RECEIPT_DRIFT",
                "reusable-prefix measurement drifted",
                key,
            )

    oracle = _mapping(receipt.get("oracle_boundary"), "oracle boundary")
    required_false = (
        "model_loaded",
        "model_request_executed",
        "gpu_execution_performed",
        "kaggle_execution_performed",
        "runtime_execution_authorized",
    )
    if any(oracle.get(key) is not False for key in required_false):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REUSABLE_PREFIX_RECEIPT_DRIFT",
            "reusable-prefix oracle crossed execution boundary",
        )
    if oracle.get("historical_b_calibration_passed") is not True:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REUSABLE_PREFIX_RECEIPT_DRIFT",
            "historical B tokenizer calibration was not preserved",
        )
    if oracle.get("historical_d_calibration_passed") is not True:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_REUSABLE_PREFIX_RECEIPT_DRIFT",
            "historical D tokenizer calibration was not preserved",
        )
    return receipt


def _validate_authorities(root: Path) -> tuple[bytes, bytes, bytes, bytes]:
    require_source_main_ancestor(root)

    request_payload = source_bound_authority(root, QUALIFICATION_REQUEST_PATH)
    architecture_payload = source_bound_authority(root, ARCHITECTURE_REVIEW_PATH)
    corpus_payload = source_bound_authority(root, CANONICAL_CORPUS_PATH)
    predecessor_payload = source_bound_authority(root, PREDECESSOR_RUNTIME_PATH)

    _validate_request(request_payload)
    _validate_architecture_review(architecture_payload)

    if _sha256(corpus_payload) != EXPECTED_CORPUS_SHA256:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_CORPUS_DRIFT",
            "canonical corpus identity drifted",
            CANONICAL_CORPUS_PATH.as_posix(),
        )
    if corpus_payload.endswith(b"\n") or b"\r" in corpus_payload:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_CORPUS_DRIFT",
            "canonical corpus byte boundary drifted",
            CANONICAL_CORPUS_PATH.as_posix(),
        )

    if _sha256(predecessor_payload) != EXPECTED_PREDECESSOR_RUNTIME_SHA256:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_PREDECESSOR_DRIFT",
            "B-vs-D exact-runtime predecessor identity drifted",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    receipt_payload = _read_required(root, REUSABLE_PREFIX_RECEIPT_PATH)
    _validate_reusable_prefix_receipt(receipt_payload)

    return (
        request_payload,
        architecture_payload,
        corpus_payload,
        predecessor_payload,
    )


def _validate_formatter_authority(root: Path) -> None:
    config_payload = source_bound_authority(root, FORMATTER_CONFIG_PATH)
    if _sha256(config_payload) != FORMATTER_CONFIG_SHA256:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FORMATTER_CONFIG_DRIFT",
            "repository Ruff configuration identity drifted",
            FORMATTER_CONFIG_PATH.as_posix(),
        )

    completed = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FORMATTER_UNAVAILABLE",
            "repository Ruff formatter is unavailable",
        )
    observed = completed.stdout.strip()
    if observed != FORMATTER_VERSION:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FORMATTER_VERSION_DRIFT",
            "repository Ruff formatter version drifted",
        )


def _ruff_canonicalize_source(
    root: Path,
    source: str,
    label: str,
) -> str:
    config = (root / FORMATTER_CONFIG_PATH).resolve()
    with tempfile.TemporaryDirectory(
        prefix="auragateway-c4-ruff-v1-",
    ) as temporary_directory:
        candidate = Path(temporary_directory) / f"{label}.py"
        candidate.write_text(
            source,
            encoding="utf-8",
            newline="\n",
        )

        format_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--config",
                str(config),
                str(candidate),
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if format_result.returncode != 0:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_FORMATTER_FAILED",
                "repository Ruff formatting failed",
                label,
            )

        check_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "--config",
                str(config),
                str(candidate),
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if check_result.returncode != 0:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_FORMATTER_NON_CANONICAL",
                "formatted runtime failed Ruff canonicality check",
                label,
            )

        payload = candidate.read_bytes()

    if b"\r" in payload:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FORMATTER_LINE_ENDING_DRIFT",
            "formatted runtime contains CR bytes",
            label,
        )
    try:
        formatted = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FORMATTER_ENCODING_DRIFT",
            "formatted runtime is not UTF-8",
            label,
        ) from error

    compile(formatted, label, "exec")
    return formatted


def _function_nodes(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    result: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in result:
                raise C4ImplementationError(
                    "C4_IMPLEMENTATION_SOURCE_AMBIGUOUS",
                    "duplicate top-level function",
                    node.name,
                )
            result[node.name] = node
    return result


def _function_segments(source: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, node in _function_nodes(source).items():
        segment = ast.get_source_segment(source, node)
        if segment is None:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "unable to recover top-level function source",
                name,
            )
        result[name] = segment
    return result


def _assignment_node(source: str, name: str) -> ast.Assign | ast.AnnAssign:
    matches: list[ast.Assign | ast.AnnAssign] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            matches.append(node)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            matches.append(node)
    if len(matches) != 1:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_AMBIGUOUS",
            "assignment cardinality drifted",
            name,
        )
    return matches[0]


def _replace_node(source: str, node: ast.AST, replacement: str) -> str:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if not isinstance(start, int) or not isinstance(end, int):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "source node boundary is unavailable",
        )
    lines = source.splitlines(keepends=True)
    lines[start - 1 : end] = [replacement.rstrip() + "\n"]
    return "".join(lines)


def _replace_assignment(source: str, name: str, replacement: str) -> str:
    return _replace_node(source, _assignment_node(source, name), replacement)


def _replace_function(source: str, name: str, replacement: str) -> str:
    node = _function_nodes(source).get(name)
    if node is None:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FUNCTION_MISSING",
            "required function is missing",
            name,
        )
    return _replace_node(source, node, replacement)


def _insert_before_function(source: str, name: str, block: str) -> str:
    node = _function_nodes(source).get(name)
    if node is None:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FUNCTION_MISSING",
            "required insertion anchor is missing",
            name,
        )
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1 : node.lineno - 1] = [block.rstrip() + "\n\n\n"]
    return "".join(lines)


def _literal_int_dict_assignment(source: str, name: str) -> dict[str, int]:
    node = _assignment_node(source, name)
    if node.value is None:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_INVALID",
            "bounded action assignment has no value",
            name,
        )
    value = ast.literal_eval(node.value)
    if not isinstance(value, dict):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_INVALID",
            "bounded action assignment is not a dictionary",
            name,
        )
    result: dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_SOURCE_INVALID",
                "bounded action key is not a string",
                name,
            )
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_SOURCE_INVALID",
                "bounded action value is not an integer",
                name,
            )
        result[key] = raw
    return result


def _render_int_dict_assignment(name: str, values: dict[str, int]) -> str:
    lines = [f"{name}: Final = {{"]
    for key, value in values.items():
        lines.append(f'    "{key}": {value},')
    lines.append("}")
    return "\n".join(lines)


def _string_chunks(value: str, limit: int = 72) -> tuple[str, ...]:
    if not value:
        return ("",)
    chunks: list[str] = []
    remaining = value
    while remaining:
        boundary = min(limit, len(remaining))
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary:]
    return tuple(chunks)


def _render_string_assignment(name: str, value: str) -> str:
    chunks = _string_chunks(value)
    lines = [f"{name}: Final = ("]
    for chunk in chunks:
        lines.append(f"    {json.dumps(chunk, ensure_ascii=True)}")
    lines.append(")")
    return "\n".join(lines)


def _render_string_tuple(name: str, values: tuple[str, ...]) -> str:
    lines = [f"{name}: Final = ("]
    for value in values:
        lines.append(f"    {json.dumps(value, ensure_ascii=True)},")
    lines.append(")")
    return "\n".join(lines)


def _function_segment(source: str, name: str) -> str:
    node = _function_nodes(source).get(name)
    if node is None:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FUNCTION_MISSING",
            "required predecessor function is missing",
            name,
        )
    observed = ast.get_source_segment(source, node)
    if observed is None:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "unable to recover predecessor function",
            name,
        )
    return observed


def _derive_function(
    source: str,
    old: str,
    new: str,
    replacements: tuple[tuple[str, str], ...] = (),
) -> str:
    observed = _function_segment(source, old)
    header = f"def {old}("
    if header not in observed:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "expected predecessor function header is unavailable",
            old,
        )
    observed = observed.replace(header, f"def {new}(", 1)
    for before, after in replacements:
        if before not in observed:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "expected predecessor function marker is unavailable",
                f"{old}:{before}",
            )
        observed = observed.replace(before, after)
    return observed


def _render_c4_helpers(
    corpus_text: str,
) -> tuple[str, str]:
    canonical_context = (
        corpus_text
        + " "
        + (
            "Return only the exact JSON object supplied in the final user message, "
            "with no markdown or additional text."
        )
    )

    constants = "\n".join(
        (
            _render_string_assignment("C4_QUALIFICATION_ID", QUALIFICATION_ID),
            _render_string_assignment(
                "C4_CANONICAL_CORPUS_VERSION",
                CANONICAL_CORPUS_VERSION,
            ),
            _render_string_assignment(
                "C4_CANONICAL_CORPUS_SHA256",
                EXPECTED_CORPUS_SHA256,
            ),
            _render_string_assignment(
                "C4_FULL_PROMPT_TOKEN_SHA256",
                EXPECTED_FULL_PROMPT_TOKEN_SHA256,
            ),
            _render_string_assignment(
                "C4_REUSABLE_PREFIX_TOKEN_SHA256",
                EXPECTED_REUSABLE_PREFIX_TOKEN_SHA256,
            ),
            _render_string_assignment(
                "C4_REQUEST_PAYLOAD_SHA256",
                EXPECTED_REQUEST_PAYLOAD_SHA256,
            ),
            _render_string_assignment(
                "C4_EXPECTED_OBJECT_SHA256",
                EXPECTED_OBJECT_SHA256,
            ),
            _render_string_assignment(
                "C4_FINAL_USER_BOUNDARY_SENTINEL",
                FINAL_USER_BOUNDARY_SENTINEL,
            ),
            _render_string_assignment(
                "C4_CANONICAL_CONTEXT",
                canonical_context,
            ),
            "C4_FULL_PROMPT_TOKEN_COUNT: Final = 899",
            "C4_REUSABLE_PREFIX_TOKEN_COUNT: Final = 880",
            "C4_OBSERVATION_COUNT: Final = 3",
            _render_string_tuple("C4_OUTPUT_NAMES", C4_OUTPUT_NAMES),
        )
    )

    c4_helpers = r"""
class C4DuplicateKeyError(ValueError):
    pass


def c4_request_messages(final_user_content: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": C4_CANONICAL_CONTEXT},
        {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
        {"role": "user", "content": final_user_content},
    ]


def c4_request_payload() -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": c4_request_messages(EXPECTED_OBJECT_CANONICAL),
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def c4_tokenize_payload(final_user_content: str) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": c4_request_messages(final_user_content),
        "add_generation_prompt": True,
        "continue_final_message": False,
        "add_special_tokens": False,
        "return_token_strs": False,
    }


def c4_token_sequence(
    worker: Worker,
    final_user_content: str,
) -> tuple[int, ...]:
    response = post_json(
        f"http://127.0.0.1:{worker.port}/tokenize",
        c4_tokenize_payload(final_user_content),
    )
    raw_tokens = response.get("tokens")
    count = response.get("count")
    if (
        not isinstance(raw_tokens, list)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(raw_tokens)
    ):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "C4 tokenization response shape is invalid",
        )
    tokens: list[int] = []
    for raw_token in raw_tokens:
        if isinstance(raw_token, bool) or not isinstance(raw_token, int):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C4 tokenization returned a non-integer token id",
            )
        if raw_token < 0:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C4 tokenization returned a negative token id",
            )
        tokens.append(raw_token)
    return tuple(tokens)


def c4_longest_common_prefix(
    left: tuple[int, ...],
    right: tuple[int, ...],
) -> tuple[int, ...]:
    count = 0
    limit = min(len(left), len(right))
    while count < limit and left[count] == right[count]:
        count += 1
    return left[:count]


def c4_token_identity(worker: Worker) -> dict[str, object]:
    canonical_tokens = c4_token_sequence(
        worker,
        EXPECTED_OBJECT_CANONICAL,
    )
    sentinel_tokens = c4_token_sequence(
        worker,
        C4_FINAL_USER_BOUNDARY_SENTINEL,
    )
    reusable_tokens = c4_longest_common_prefix(
        canonical_tokens,
        sentinel_tokens,
    )
    canonical_sha = sha256_bytes(
        canonical_json(list(canonical_tokens)).encode("utf-8")
    )
    reusable_sha = sha256_bytes(
        canonical_json(list(reusable_tokens)).encode("utf-8")
    )
    if (
        len(canonical_tokens) != C4_FULL_PROMPT_TOKEN_COUNT
        or canonical_sha != C4_FULL_PROMPT_TOKEN_SHA256
    ):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "C4 full-prompt token identity drifted before model request",
        )
    if (
        len(reusable_tokens) != C4_REUSABLE_PREFIX_TOKEN_COUNT
        or reusable_sha != C4_REUSABLE_PREFIX_TOKEN_SHA256
    ):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "C4 reusable-prefix token identity drifted before model request",
        )
    if len(reusable_tokens) >= len(canonical_tokens):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "C4 final-user boundary did not diverge",
        )
    return {
        "token_count": len(canonical_tokens),
        "token_sha256": canonical_sha,
        "reusable_prefix_token_count": len(reusable_tokens),
        "reusable_prefix_token_sha256": reusable_sha,
        "sentinel_prompt_token_count": len(sentinel_tokens),
        "sentinel_prompt_token_sha256": sha256_bytes(
            canonical_json(list(sentinel_tokens)).encode("utf-8")
        ),
        "first_divergent_token_index": len(reusable_tokens),
    }


def initialize_c4_journal() -> None:
    if PRE_REQUEST_TOKEN_IDENTITY_JOURNAL.exists():
        raise RuntimeError("pre-request token-identity journal already exists")
    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            "schema_version": "1.0.0",
            "journal_id": (
                "auragateway-canonical-synthetic-prefix-c4-"
                "pre-request-token-identity-v1"
            ),
            "qualification_id": C4_QUALIFICATION_ID,
            "entries": [],
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
        },
    )


def persist_c4_pre_request_identity(
    request_ordinal: int,
    token_identity: dict[str, object],
    payload_sha256: str,
) -> None:
    journal = _read_pre_request_token_identity_journal()
    entries = journal.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("pre-request token-identity journal entries are invalid")
    if request_ordinal != len(entries) + 1:
        raise RuntimeError("pre-request token-identity request ordinal drifted")
    if payload_sha256 != C4_REQUEST_PAYLOAD_SHA256:
        raise RuntimeError("C4 request payload identity drifted")
    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            **journal,
            "entries": [
                *entries,
                {
                    "request_ordinal": request_ordinal,
                    "observation_id": f"C4_OBSERVATION_{request_ordinal}",
                    "token_count": token_identity["token_count"],
                    "token_sha256": token_identity["token_sha256"],
                    "reusable_prefix_token_count": (
                        token_identity["reusable_prefix_token_count"]
                    ),
                    "reusable_prefix_token_sha256": (
                        token_identity["reusable_prefix_token_sha256"]
                    ),
                    "payload_sha256": payload_sha256,
                    "persisted_before_model_request": True,
                },
            ],
        },
    )


def c4_object_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise C4DuplicateKeyError(key)
        result[key] = value
    return result


def c4_json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if type(value) is int:
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def c4_response_projection(
    content: str,
    finish_reason: object,
) -> dict[str, object]:
    stripped = content.strip()
    first = stripped[0] if stripped else None
    last = stripped[-1] if stripped else None
    leading_content = first != "{"
    trailing_content = last != "}"
    markdown_fence = "```" in content

    valid_json = False
    duplicate_key_detected = False
    parsed: object = None
    json_error_line: int | None = None
    json_error_column: int | None = None
    json_error_position: int | None = None

    try:
        parsed = json.loads(
            content,
            object_pairs_hook=c4_object_pairs,
        )
        valid_json = True
    except C4DuplicateKeyError:
        duplicate_key_detected = True
    except json.JSONDecodeError as error:
        json_error_line = error.lineno
        json_error_column = error.colno
        json_error_position = error.pos

    parsed_key_set: list[str] = []
    probe_json_type: str | None = None
    value_json_type: str | None = None
    probe_exact = False
    value_exact = False
    canonical_parsed_object_sha256: str | None = None

    if valid_json:
        canonical_parsed_object_sha256 = sha256_text(
            canonical_json(parsed)
        )
        if isinstance(parsed, dict):
            parsed_key_set = sorted(
                key for key in parsed if isinstance(key, str)
            )
            probe = parsed.get("probe")
            value = parsed.get("value")
            probe_json_type = c4_json_type(probe)
            value_json_type = c4_json_type(value)
            probe_exact = (
                isinstance(probe, str)
                and probe == "exact-runtime-p5-p6"
            )
            value_exact = (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value == 1
            )

    response_complete = finish_reason == "stop"
    exact_key_set = parsed_key_set == ["probe", "value"]
    exact_object = (
        valid_json
        and not duplicate_key_detected
        and isinstance(parsed, dict)
        and exact_key_set
        and probe_exact
        and value_exact
        and not leading_content
        and not trailing_content
        and not markdown_fence
        and response_complete
    )

    return {
        "valid_json": valid_json,
        "duplicate_key_detected": duplicate_key_detected,
        "json_error_line": json_error_line,
        "json_error_column": json_error_column,
        "json_error_position": json_error_position,
        "json_root_type": c4_json_type(parsed) if valid_json else None,
        "parsed_key_set": parsed_key_set,
        "probe_json_type": probe_json_type,
        "value_json_type": value_json_type,
        "probe_exact": probe_exact,
        "value_exact": value_exact,
        "canonical_parsed_object_sha256": (
            canonical_parsed_object_sha256
        ),
        "canonical_expected_object_sha256": (
            C4_EXPECTED_OBJECT_SHA256
        ),
        "leading_non_whitespace_content_detected": leading_content,
        "trailing_non_whitespace_content_detected": trailing_content,
        "markdown_fence_detected": markdown_fence,
        "response_complete": response_complete,
        "exact_object": exact_object,
    }


def run_c4_observation(
    worker: Worker,
    sequence_index: int,
    counters: dict[str, int],
) -> dict[str, object]:
    token_identity = c4_token_identity(worker)
    payload = c4_request_payload()
    payload_sha256 = sha256_text(canonical_json(payload))

    if payload_sha256 != C4_REQUEST_PAYLOAD_SHA256:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "C4 request payload identity drifted before model request",
        )

    request_ordinal = counters["model_requests"] + 1
    if request_ordinal != sequence_index:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "C4 pre-request ordinal drifted",
        )

    persist_c4_pre_request_identity(
        request_ordinal,
        token_identity,
        payload_sha256,
    )

    baseline = validate_zero_cache_baseline(worker)
    zero_cache_receipt_sha256 = sha256_text(
        canonical_json(baseline)
    )
    before = worker.metric_snapshot()

    consume_actions(counters, "model_requests")
    encoded = canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        bounded_loopback(
            f"http://127.0.0.1:{worker.port}/v1/chat/completions"
        ),
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            status_code = response.status
            response_payload = response.read()
    except urllib.error.HTTPError as error:
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            f"C4 request HTTP failure: {error.code}",
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            "C4 request transport failed",
        ) from error

    if status_code != 200:
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            "C4 request returned an unexpected HTTP status",
        )

    try:
        envelope = json.loads(response_payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response envelope is not valid JSON",
        ) from error
    if not isinstance(envelope, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response envelope root is invalid",
        )

    usage = envelope.get("usage")
    choices = envelope.get("choices")
    if not isinstance(usage, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response usage is missing",
        )
    if not isinstance(choices, list) or len(choices) != 1:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response choices are invalid",
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response choice is invalid",
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response message is invalid",
        )
    content = message.get("content")
    if not isinstance(content, str):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response content is not a string",
        )

    completion_tokens = usage.get("completion_tokens")
    prompt_tokens = usage.get("prompt_tokens")
    if (
        isinstance(completion_tokens, bool)
        or not isinstance(completion_tokens, int)
        or not 1 <= completion_tokens <= 32
    ):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 completion-token budget drifted",
        )
    if (
        isinstance(prompt_tokens, bool)
        or not isinstance(prompt_tokens, int)
        or prompt_tokens != C4_FULL_PROMPT_TOKEN_COUNT
    ):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "C4 response prompt-token count drifted",
        )

    after = worker.metric_snapshot()
    delta = metric_delta(before, after)
    worker_health_after_request = True

    finish_reason = choice.get("finish_reason")
    projection = c4_response_projection(
        content,
        finish_reason,
    )

    worker_report = worker.report()
    pid = worker_report.get("pid")
    process_start_ticks_value = worker_report.get(
        "process_start_ticks"
    )
    process_identity_sha256 = sha256_text(
        canonical_json(
            {
                "pid": pid,
                "process_start_ticks": process_start_ticks_value,
            }
        )
    )

    return {
        "observation_id": f"C4_OBSERVATION_{sequence_index}",
        "request_ordinal": request_ordinal,
        "sequence_index": sequence_index,
        "worker_instance_id": worker.instance_id,
        "worker_process_identity_sha256": process_identity_sha256,
        "token_count": token_identity["token_count"],
        "token_sha256": token_identity["token_sha256"],
        "reusable_prefix_token_count": (
            token_identity["reusable_prefix_token_count"]
        ),
        "reusable_prefix_token_sha256": (
            token_identity["reusable_prefix_token_sha256"]
        ),
        "payload_sha256": payload_sha256,
        "zero_cache_baseline": True,
        "zero_cache_baseline_receipt_sha256": (
            zero_cache_receipt_sha256
        ),
        "http_status": status_code,
        "response_sha256": sha256_text(content),
        "response_length": len(content),
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        **projection,
        "worker_health_after_request": worker_health_after_request,
        "request_error": None,
        "transport_error": None,
        "metric_delta": asdict(delta),
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }


def c4_public_observation(
    observation: dict[str, object],
) -> dict[str, object]:
    permitted = (
        "observation_id",
        "request_ordinal",
        "sequence_index",
        "worker_instance_id",
        "worker_process_identity_sha256",
        "worker_start_receipt_sha256",
        "token_count",
        "token_sha256",
        "reusable_prefix_token_count",
        "reusable_prefix_token_sha256",
        "payload_sha256",
        "zero_cache_baseline",
        "zero_cache_baseline_receipt_sha256",
        "http_status",
        "response_sha256",
        "response_length",
        "finish_reason",
        "prompt_tokens",
        "completion_tokens",
        "valid_json",
        "duplicate_key_detected",
        "json_error_line",
        "json_error_column",
        "json_error_position",
        "json_root_type",
        "parsed_key_set",
        "probe_json_type",
        "value_json_type",
        "probe_exact",
        "value_exact",
        "canonical_parsed_object_sha256",
        "canonical_expected_object_sha256",
        "leading_non_whitespace_content_detected",
        "trailing_non_whitespace_content_detected",
        "markdown_fence_detected",
        "response_complete",
        "exact_object",
        "worker_health_after_request",
        "teardown_status",
        "request_error",
        "transport_error",
        "metric_delta",
        "raw_prompt_retained",
        "raw_output_retained",
    )
    return {name: observation.get(name) for name in permitted}


def run_c4_fresh_worker_observation(
    model_home: Path,
    snapshot: Path,
    sequence_index: int,
    counters: dict[str, int],
    worker_reports: list[dict[str, object]],
    teardown_reports: list[dict[str, object]],
) -> dict[str, object]:
    worker = Worker(
        "observation_worker",
        0,
        8001,
        model_home,
        snapshot,
        generation=sequence_index,
    )
    primary_error: Exception | None = None
    observation: dict[str, object] | None = None
    report: dict[str, object] | None = None

    try:
        worker.start(counters)
        worker.wait_ready()
        worker.validate_model()
        worker.wait_backend_marker()
        native_origins = validate_native_origin_closure(worker)
        report = {
            **worker.report(),
            "native_origin_closure": native_origins,
        }
        worker_reports.append(report)
        observation = run_c4_observation(
            worker,
            sequence_index,
            counters,
        )
    except Exception as error:
        primary_error = error
    finally:
        teardown = safe_worker_teardown(
            worker,
            f"C4_OBSERVATION_{sequence_index}_TERMINAL",
        )
        teardown_reports.append(teardown)

    teardown_status = teardown.get("status")
    if teardown_status not in {"PASSED", "NOT_STARTED"}:
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "fresh C4 observation worker teardown proof failed",
        )
    if primary_error is not None:
        raise primary_error
    if teardown_status != "PASSED":
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "completed C4 observation did not prove worker teardown",
        )
    if observation is None or report is None:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "fresh C4 observation did not produce complete evidence",
        )

    return {
        **observation,
        "worker_start_receipt_sha256": sha256_text(
            canonical_json(report)
        ),
        "teardown_status": teardown_status,
    }


def write_c4_results(
    results: list[dict[str, object]],
    status: str,
) -> None:
    write_json(
        OUTPUT_ROOT / "c4_request_results_v1.json",
        {
            "schema_version": "1.0.0",
            "qualification_id": C4_QUALIFICATION_ID,
            "status": status,
            "scheduled_request_count": C4_OBSERVATION_COUNT,
            "observed_request_count": len(results),
            "results": [
                c4_public_observation(item) for item in results
            ],
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        },
    )


def decide_c4_qualification(
    results: list[dict[str, object]],
    worker_reports: list[dict[str, object]],
    teardown_reports: list[dict[str, object]],
    counters: dict[str, int],
) -> dict[str, object]:
    if len(results) != C4_OBSERVATION_COUNT:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "C4 result count drifted",
        )
    expected_ordinals = tuple(range(1, C4_OBSERVATION_COUNT + 1))
    observed_ordinals = tuple(
        row.get("request_ordinal") for row in results
    )
    if observed_ordinals != expected_ordinals:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "C4 request chronology drifted",
        )
    if len(worker_reports) != 3 or len(teardown_reports) != 3:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "C4 fresh-worker evidence cardinality drifted",
        )
    if any(
        item.get("status") != "PASSED"
        for item in teardown_reports
    ):
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "one or more C4 observation teardowns failed",
        )

    worker_identities = {
        str(row.get("worker_process_identity_sha256"))
        for row in results
        if isinstance(
            row.get("worker_process_identity_sha256"),
            str,
        )
    }
    if len(worker_identities) != 3:
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "fresh worker process identity was reused",
        )

    expected_counters = {
        "model_requests": 3,
        "model_loads": 3,
        "worker_starts": 3,
        "hidden_retries": 0,
        "network_requests": 0,
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
    }
    for name, expected in expected_counters.items():
        if counters.get(name) != expected:
            raise DiagnosticFailure(
                "REQUEST_RECONCILIATION_FAILURE",
                f"{name} expected {expected}, "
                f"observed {counters.get(name)}",
            )

    required_fields = {
        "observation_id",
        "request_ordinal",
        "worker_start_receipt_sha256",
        "zero_cache_baseline_receipt_sha256",
        "response_sha256",
        "response_length",
        "finish_reason",
        "prompt_tokens",
        "completion_tokens",
        "valid_json",
        "duplicate_key_detected",
        "json_error_line",
        "json_error_column",
        "json_error_position",
        "markdown_fence_detected",
        "leading_non_whitespace_content_detected",
        "trailing_non_whitespace_content_detected",
        "parsed_key_set",
        "canonical_parsed_object_sha256",
        "response_complete",
        "exact_object",
        "canonical_expected_object_sha256",
        "request_error",
        "transport_error",
        "worker_health_after_request",
        "teardown_status",
    }

    for row in results:
        if required_fields - set(row):
            raise DiagnosticFailure(
                "EVIDENCE_PROJECTION_FAILURE",
                "C4 observation evidence field set is incomplete",
            )
        if row.get("zero_cache_baseline") is not True:
            raise DiagnosticFailure(
                "P5_STARTING_STATE_FAILURE",
                "C4 observation lacked zero cache baseline",
            )
        if (
            row.get("token_count") != C4_FULL_PROMPT_TOKEN_COUNT
            or row.get("token_sha256")
            != C4_FULL_PROMPT_TOKEN_SHA256
        ):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C4 full-prompt token identity failed reconciliation",
            )
        if (
            row.get("reusable_prefix_token_count")
            != C4_REUSABLE_PREFIX_TOKEN_COUNT
            or row.get("reusable_prefix_token_sha256")
            != C4_REUSABLE_PREFIX_TOKEN_SHA256
        ):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C4 reusable-prefix identity failed reconciliation",
            )
        if row.get("payload_sha256") != C4_REQUEST_PAYLOAD_SHA256:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C4 request payload identity failed reconciliation",
            )
        if row.get("worker_health_after_request") is not True:
            raise DiagnosticFailure(
                "WORKER_IDENTITY_FAILURE",
                "C4 worker was not healthy after its request",
            )
        if row.get("teardown_status") != "PASSED":
            raise DiagnosticFailure(
                "TEARDOWN_FAILURE",
                "C4 observation teardown status drifted",
            )
        if row.get("raw_prompt_retained") is not False:
            raise DiagnosticFailure(
                "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
                "C4 raw prompt retention boundary drifted",
            )
        if row.get("raw_output_retained") is not False:
            raise DiagnosticFailure(
                "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
                "C4 raw output retention boundary drifted",
            )

    exact_count = sum(
        row.get("exact_object") is True for row in results
    )
    state = "QUALIFIED" if exact_count == 3 else "NOT_QUALIFIED"

    return {
        "schema_version": "1.0.0",
        "status": "DECIDED",
        "qualification_id": C4_QUALIFICATION_ID,
        "observed_terminal_state": state,
        "exact_object_count": exact_count,
        "required_exact_object_count": 3,
        "observation_count": 3,
        "complete_behavioral_run": True,
        "fresh_worker_process_per_observation": True,
        "worker_identity_cardinality": len(worker_identities),
        "full_prompt_token_count": C4_FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": C4_FULL_PROMPT_TOKEN_SHA256,
        "reusable_prefix_token_count": (
            C4_REUSABLE_PREFIX_TOKEN_COUNT
        ),
        "reusable_prefix_token_sha256": (
            C4_REUSABLE_PREFIX_TOKEN_SHA256
        ),
        "canonical_request_payload_sha256": (
            C4_REQUEST_PAYLOAD_SHA256
        ),
        "strict_duplicate_key_rejection": True,
        "strict_integer_value_validation": True,
        "finish_reason_stop_required": True,
        "qualification_accepted_by_repository": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }


def c4_bundle_outputs() -> dict[str, object]:
    required_before_manifest = set(C4_OUTPUT_NAMES) - {
        "bundle_manifest_v1.json"
    }
    observed_before_manifest = {
        path.name
        for path in OUTPUT_ROOT.iterdir()
        if path.is_file()
    }
    missing = required_before_manifest - observed_before_manifest
    unexpected = observed_before_manifest - required_before_manifest
    if missing or unexpected:
        raise RuntimeError(
            "C4 evidence output contract drifted: "
            f"missing={sorted(missing)} "
            f"unexpected={sorted(unexpected)}"
        )

    entries: list[dict[str, object]] = []
    for name in C4_OUTPUT_NAMES:
        if name == "bundle_manifest_v1.json":
            continue
        path = OUTPUT_ROOT / name
        entries.append(
            {
                "path": name,
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": "1.0.0",
        "qualification_id": C4_QUALIFICATION_ID,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "members": entries,
        "scratch_directories_included": False,
        "worker_log_directory_included": False,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }
    write_json(
        OUTPUT_ROOT / "bundle_manifest_v1.json",
        manifest,
    )

    with zipfile.ZipFile(
        EVIDENCE_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for name in C4_OUTPUT_NAMES:
            path = OUTPUT_ROOT / name
            archive.write(path, arcname=name)

    if (
        not EVIDENCE_ZIP.is_file()
        or EVIDENCE_ZIP.stat().st_size > MAX_EVIDENCE_ZIP_BYTES
    ):
        raise RuntimeError("C4 evidence ZIP is unavailable or oversized")

    return {
        "bundle_status": "PASSED",
        "bundle_manifest_sha256": file_sha256(
            OUTPUT_ROOT / "bundle_manifest_v1.json"
        ),
        "evidence_zip_sha256": file_sha256(EVIDENCE_ZIP),
        "evidence_zip_size_bytes": EVIDENCE_ZIP.stat().st_size,
    }
""".strip()

    main = r"""
def main() -> int:
    if OUTPUT_ROOT.exists() or SCRATCH_ROOT.exists() or EVIDENCE_ZIP.exists():
        raise RuntimeError(
            "C4 output, scratch, or evidence path already exists"
        )

    OUTPUT_ROOT.mkdir(parents=True)
    LOG_ROOT.mkdir()
    SCRATCH_ROOT.mkdir()

    counters = {
        "runtime_install_attempts": 0,
        "runtime_import_closure_probes": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "hidden_retries": 0,
        "external_spend": 0,
    }
    results: list[dict[str, object]] = []
    worker_reports: list[dict[str, object]] = []
    teardown_reports: list[dict[str, object]] = []
    decision: dict[str, object] | None = None
    failure: dict[str, object] | None = None
    authorization: dict[str, object] | None = None
    cleanup: dict[str, object] = {
        "schema_version": "1.0.0",
        "status": "NOT_RUN",
    }
    active_failure_code = "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH"
    failed_stage = "RUNTIME_SOURCE_IDENTITY"

    try:
        failed_stage = "PRE_REQUEST_JOURNAL"
        active_failure_code = "EVIDENCE_PROJECTION_FAILURE"
        initialize_c4_journal()

        failed_stage = "RUNTIME_SOURCE_IDENTITY"
        active_failure_code = "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH"
        source_identity = write_runtime_source_identity_report()

        failed_stage = "PRIVACY_BOUNDARY"
        active_failure_code = "P3_P6_PRIVACY_BOUNDARY_VIOLATION"
        require_private_environment()

        failed_stage = "AUTHORIZATION"
        active_failure_code = "AUTHORITY_FAILURE"
        authorization = require_transaction_bound_context()

        failed_stage = "WHEELHOUSE"
        active_failure_code = "P3_P6_WHEELHOUSE_INVALID"
        wheelhouse = discover_one_directory(RUNTIME_OUTPUT_DIRECTORY)
        validate_wheelhouse(wheelhouse)

        failed_stage = "MODEL_SNAPSHOT"
        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        source_snapshot = discover_model_snapshot()

        failed_stage = "RUNTIME_INSTALL"
        active_failure_code = "P3_P6_RUNTIME_INSTALL_FAILED"
        install_runtime(wheelhouse, counters)

        failed_stage = "RUNTIME_IDENTITY"
        active_failure_code = "P3_P6_PLATFORM_IDENTITY_MISMATCH"
        runtime_identity = validate_target_runtime()
        runtime_environment = process_tree_environment(
            0,
            SCRATCH_ROOT / "environment_report_model_home",
        )
        environment_report = runtime_environment_report(
            runtime_environment
        )
        if (
            environment_report["prohibited_stub_path_present"]
            is not False
        ):
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                "exact-runtime environment retained a CUDA stub path",
            )
        if environment_report["ld_preload_absent"] is not True:
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                "exact-runtime environment retained LD_PRELOAD",
            )
        write_json(
            OUTPUT_ROOT / "runtime_environment_report_v1.json",
            environment_report,
        )

        failed_stage = "IMPORT_CLOSURE"
        active_failure_code = (
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED"
        )
        validate_process_tree_import_closure(counters)

        failed_stage = "MODEL_HOME"
        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        model_home, snapshot = prepare_model_home(source_snapshot)

        write_json(
            OUTPUT_ROOT / "c4_runtime_ready_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "PASSED",
                "decision": "STATIC_RUNTIME_PREREQUISITES_REALIZED",
                "qualification_id": C4_QUALIFICATION_ID,
                "runtime_identity": runtime_identity,
                "runtime_source_identity": source_identity,
                "model_repository": MODEL_REPOSITORY,
                "model_revision": MODEL_REVISION,
                "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
                "backend": EXPECTED_BACKEND,
                "prefix_cache_enabled": True,
                "cache_block_size": CACHE_BLOCK_SIZE,
                "scheduled_worker_starts": 3,
                "scheduled_model_loads": 3,
                "scheduled_model_requests": 3,
                "fresh_worker_process_per_observation": True,
                "full_prompt_token_count": (
                    C4_FULL_PROMPT_TOKEN_COUNT
                ),
                "full_prompt_token_sha256": (
                    C4_FULL_PROMPT_TOKEN_SHA256
                ),
                "reusable_prefix_token_count": (
                    C4_REUSABLE_PREFIX_TOKEN_COUNT
                ),
                "reusable_prefix_token_sha256": (
                    C4_REUSABLE_PREFIX_TOKEN_SHA256
                ),
                "request_payload_sha256": (
                    C4_REQUEST_PAYLOAD_SHA256
                ),
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

        for sequence_index in range(1, C4_OBSERVATION_COUNT + 1):
            failed_stage = f"OBSERVATION_{sequence_index}"
            active_failure_code = "WORKER_STARTUP_FAILURE"
            observation = run_c4_fresh_worker_observation(
                model_home,
                snapshot,
                sequence_index,
                counters,
                worker_reports,
                teardown_reports,
            )
            results.append(observation)
            write_c4_results(results, "IN_PROGRESS")

        failed_stage = "ACTION_RECONCILIATION"
        active_failure_code = "REQUEST_RECONCILIATION_FAILURE"
        expected_counters = {
            "runtime_install_attempts": 1,
            "runtime_import_closure_probes": 1,
            "model_loads": 3,
            "worker_starts": 3,
            "model_requests": 3,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "hidden_retries": 0,
            "external_spend": 0,
        }
        for name, expected in expected_counters.items():
            if counters[name] != expected:
                raise DiagnosticFailure(
                    "REQUEST_RECONCILIATION_FAILURE",
                    f"{name} expected {expected}, "
                    f"observed {counters[name]}",
                )

        failed_stage = "C4_DECISION"
        active_failure_code = "HARNESS_SEMANTIC_FAILURE"
        decision = decide_c4_qualification(
            results,
            worker_reports,
            teardown_reports,
            counters,
        )

    except Exception as error:
        if isinstance(error, DiagnosticAmbiguity):
            failure_class = error.failure_class
            detail_code = None
            safe_message = error.safe_message
        elif isinstance(error, DiagnosticFailure):
            detail_code = error.error_code
            failure_class = classify_failure_detail(detail_code)
            safe_message = error.safe_message
        else:
            detail_code = active_failure_code
            failure_class = classify_failure_detail(detail_code)
            safe_message = (
                sanitize_excerpt(str(error))[:512]
                or type(error).__name__
            )
        failure = {
            "schema_version": "1.0.0",
            "status": "INVALID_EXECUTION",
            "failed_stage": failed_stage,
            "completed_requests": len(results),
            "failure_class": failure_class,
            "detail_code": detail_code,
            "error_type": type(error).__name__,
            "safe_message": safe_message,
        }

    teardown_failures = tuple(
        item
        for item in teardown_reports
        if item.get("status") not in {"PASSED", "NOT_STARTED"}
    )
    teardown_status = "NOT_RUN"
    if teardown_reports:
        teardown_status = "PASSED"
    if teardown_failures:
        teardown_status = "FAILED"

    write_json(
        OUTPUT_ROOT / "worker_teardown_report_v1.json",
        {
            "schema_version": "1.0.0",
            "status": teardown_status,
            "scheduled_worker_count": 3,
            "observed_teardown_count": len(teardown_reports),
            "worker_teardowns": teardown_reports,
            "fresh_worker_process_per_observation": True,
            "all_completed_observations_torn_down": (
                not teardown_failures
                and len(teardown_reports) >= len(results)
            ),
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        },
    )

    if teardown_failures and failure is None:
        failure = {
            "schema_version": "1.0.0",
            "status": "INVALID_EXECUTION",
            "failed_stage": "WORKER_TEARDOWN",
            "completed_requests": len(results),
            "failure_class": "TEARDOWN_FAILURE",
            "detail_code": "TEARDOWN_FAILURE",
            "error_type": "WorkerTeardownFailure",
            "safe_message": "worker teardown proof failed",
        }

    try:
        cleanup = cleanup_scratch()
    except Exception as error:
        cleanup = {
            "schema_version": "1.0.0",
            "status": "FAILED",
            "scratch_exists_after": SCRATCH_ROOT.exists(),
            "error_type": type(error).__name__,
            "safe_message": (
                sanitize_excerpt(str(error))[:512]
                or type(error).__name__
            ),
        }
        write_json(
            OUTPUT_ROOT / "scratch_cleanup_report_v1.json",
            cleanup,
        )

    if cleanup.get("status") != "PASSED" and failure is None:
        failure = {
            "schema_version": "1.0.0",
            "status": "INVALID_EXECUTION",
            "failed_stage": "SCRATCH_CLEANUP",
            "completed_requests": len(results),
            "failure_class": "TEARDOWN_FAILURE",
            "detail_code": "P3_P6_SCRATCH_CLEANUP_FAILED",
            "error_type": str(cleanup.get("error_type")),
            "safe_message": str(cleanup.get("safe_message")),
        }

    result_status = "NOT_RUN"
    if results:
        result_status = "PARTIAL"
    if len(results) == 3 and failure is None:
        result_status = "COMPLETE"
    write_c4_results(results, result_status)

    if decision is not None and failure is None:
        write_json(
            OUTPUT_ROOT / "c4_decision_v1.json",
            decision,
        )
    else:
        write_json(
            OUTPUT_ROOT / "c4_decision_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NOT_EVALUATED",
                "qualification_id": C4_QUALIFICATION_ID,
                "observed_terminal_state": "INVALID_EXECUTION",
                "blocked_by": (
                    None
                    if failure is None
                    else failure.get("failure_class")
                ),
                "qualification_accepted_by_repository": False,
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

    terminal_failure_class: str | None = (
        None if failure is None else str(failure.get("failure_class"))
    )
    ensure_runtime_source_identity_report(terminal_failure_class)
    ensure_install_report(terminal_failure_class)
    ensure_import_closure_report(terminal_failure_class)

    environment_path = (
        OUTPUT_ROOT / "runtime_environment_report_v1.json"
    )
    if not environment_path.is_file():
        write_json(
            environment_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": (
                    terminal_failure_class or "UPSTREAM_PRECONDITION"
                ),
                "raw_environment_retained": False,
            },
        )

    ready_path = OUTPUT_ROOT / "c4_runtime_ready_v1.json"
    if not ready_path.is_file():
        write_json(
            ready_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "qualification_id": C4_QUALIFICATION_ID,
                "blocked_by": (
                    terminal_failure_class or "UPSTREAM_PRECONDITION"
                ),
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

    if failure is None:
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NOT_APPLICABLE",
                "failure_class": None,
                "detail_code": None,
                "error_type": None,
                "safe_message": None,
                "completed_requests": len(results),
                "teardown_status": teardown_status,
            },
        )
    else:
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                **failure,
                "teardown_status": teardown_status,
            },
        )

    execution_valid = decision is not None and failure is None
    observed_terminal_state: object = "INVALID_EXECUTION"
    if execution_valid and decision is not None:
        observed_terminal_state = decision.get(
            "observed_terminal_state"
        )

    summary = {
        "schema_version": "1.0.0",
        "qualification_id": C4_QUALIFICATION_ID,
        "status": (
            "QUALIFICATION_EXECUTION_COMPLETE"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "observed_terminal_state": observed_terminal_state,
        "qualification_accepted_by_repository": False,
        "authorization": authorization,
        "completed_requests": len(results),
        "scheduled_requests": 3,
        "fresh_worker_process_per_observation": True,
        "full_prompt_token_count": C4_FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": C4_FULL_PROMPT_TOKEN_SHA256,
        "reusable_prefix_token_count": (
            C4_REUSABLE_PREFIX_TOKEN_COUNT
        ),
        "reusable_prefix_token_sha256": (
            C4_REUSABLE_PREFIX_TOKEN_SHA256
        ),
        "canonical_request_payload_sha256": (
            C4_REQUEST_PAYLOAD_SHA256
        ),
        "worker_starts": counters["worker_starts"],
        "model_loads": counters["model_loads"],
        "model_requests": counters["model_requests"],
        "hidden_retries": counters["hidden_retries"],
        "external_network_requests": counters["network_requests"],
        "external_spend": counters["external_spend"],
        "teardown_status": teardown_status,
        "scratch_cleanup_status": cleanup.get("status"),
        "raw_prompt_retained": False,
        "raw_output_retained": False,
        "c4_repository_state_advanced": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "final_abc_measured": False,
        "production_readiness_established": False,
        "next_gate": (
            "PRESERVE_AND_RECONCILE_CANONICAL_SYNTHETIC_"
            "PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
        ),
    }
    write_json(
        OUTPUT_ROOT / "c4_summary_v1.json",
        summary,
    )

    human = (
        "# AuraGateway Canonical Synthetic Prefix C4 "
        "Behavioral Qualification V1\n\n"
        f"- Execution status: {summary['status']}\n"
        f"- Observed terminal state: "
        f"{summary['observed_terminal_state']}\n"
        f"- Completed requests: {len(results)} / 3\n"
        f"- Worker starts: {counters['worker_starts']} / 3\n"
        f"- Model loads: {counters['model_loads']} / 3\n"
        f"- Worker teardown: {teardown_status}\n"
        f"- Scratch cleanup: {cleanup.get('status')}\n"
        "- Qualification accepted by repository: false\n"
        "- Raw prompts retained: false\n"
        "- Raw model outputs retained: false\n"
        "- Hidden retries: 0\n"
        "- Replacement requests: 0\n"
        "- P5/P6 were not requalified by this execution.\n"
        "- Final A/B/C was not measured.\n"
        "- Production readiness is not established.\n"
    )
    write_text(
        OUTPUT_ROOT / "human_report_v1.md",
        human,
    )

    try:
        bundle = c4_bundle_outputs()
    except Exception as error:
        behavioral_observed_terminal_state = (
            summary["observed_terminal_state"]
        )
        packaging_failure = {
            "schema_version": "1.0.0",
            "status": "INVALID_EXECUTION",
            "failed_stage": "EVIDENCE_PACKAGING",
            "completed_requests": len(results),
            "failure_class": "EVIDENCE_PROJECTION_FAILURE",
            "detail_code": "EVIDENCE_PROJECTION_FAILURE",
            "error_type": type(error).__name__,
            "safe_message": (
                sanitize_excerpt(str(error))[:512]
                or type(error).__name__
            ),
            "teardown_status": teardown_status,
            "behavioral_observed_terminal_state": (
                behavioral_observed_terminal_state
            ),
        }
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            packaging_failure,
        )
        invalid_summary = {
            **summary,
            "status": "INVALID_EXECUTION",
            "observed_terminal_state": "INVALID_EXECUTION",
            "behavioral_observed_terminal_state": (
                behavioral_observed_terminal_state
            ),
            "evidence_packaging_status": "FAILED",
        }
        write_json(
            OUTPUT_ROOT / "c4_summary_v1.json",
            invalid_summary,
        )
        terminal = {
            **invalid_summary,
            "bundle_status": "FAILED",
            "bundle_error_type": type(error).__name__,
            "behavioral_decision_preserved_before_bundle": (
                decision is not None
            ),
        }
        print(canonical_json(terminal))
        return 2

    terminal = {
        **summary,
        **bundle,
    }
    print(canonical_json(terminal))
    return 0 if execution_valid else 2
""".strip()

    return "\n\n\n".join((constants, c4_helpers)), main


def _validate_change_surface(
    predecessor: str,
    successor: str,
) -> int:
    before = _function_segments(predecessor)
    after = _function_segments(successor)

    missing = set(before) - set(after)
    if missing:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_CHANGE_SURFACE_DRIFT",
            "predecessor function disappeared",
            ",".join(sorted(missing)),
        )

    changed = tuple(sorted(name for name, body in before.items() if after.get(name) != body))
    if changed != CHANGED_EXISTING_FUNCTIONS:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_CHANGE_SURFACE_DRIFT",
            "unexpected predecessor function changed",
            ",".join(changed),
        )

    added = tuple(sorted(set(after) - set(before)))
    if added != tuple(sorted(ADDED_FUNCTIONS)):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_CHANGE_SURFACE_DRIFT",
            "C4 helper inventory drifted",
            ",".join(added),
        )
    return len(before) - len(changed)


def _validate_successor_contract(source: str) -> None:
    functions = _function_segments(source)
    main = functions.get("main")
    if main is None:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SUCCESSOR_INVALID",
            "successor main is missing",
        )

    required_main_markers = (
        "run_c4_fresh_worker_observation(",
        "decide_c4_qualification(",
        "range(1, C4_OBSERVATION_COUNT + 1)",
        "return 0 if execution_valid else 2",
        "qualification_accepted_by_repository",
    )
    for marker in required_main_markers:
        if marker not in main:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_SUCCESSOR_INVALID",
                "C4 main contract marker is missing",
                marker,
            )

    prohibited_main_markers = (
        "B_VS_D_REQUEST_ORDER",
        "decide_marker_diversified_differential(",
        "decide_p5(",
        "decide_p6(",
    )
    for marker in prohibited_main_markers:
        if marker in main:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_SUCCESSOR_INVALID",
                "C4 main retained a prohibited predecessor trajectory",
                marker,
            )

    request_payload = functions["c4_request_payload"]
    request_markers = (
        '"temperature": 0',
        '"top_p": 1',
        '"repetition_penalty": 1.1',
        '"seed": 7',
        '"max_tokens": 32',
        '"stream": False',
    )
    for marker in request_markers:
        if marker not in request_payload:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_REQUEST_CONTRACT_DRIFT",
                "C4 request generation parameter drifted",
                marker,
            )
    for prohibited in ("response_format", "guided_decoding"):
        if prohibited in request_payload:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_REQUEST_CONTRACT_DRIFT",
                "prohibited constrained-decoding field entered request payload",
                prohibited,
            )

    projection = functions["c4_response_projection"]
    for marker in (
        "object_pairs_hook=c4_object_pairs",
        "and not isinstance(value, bool)",
        'finish_reason == "stop"',
        'parsed_key_set == ["probe", "value"]',
        "duplicate_key_detected",
    ):
        if marker not in projection:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_OUTPUT_VALIDATOR_DRIFT",
                "strict C4 response validator marker is missing",
                marker,
            )

    decision = functions["decide_c4_qualification"]
    for marker in (
        'state = "QUALIFIED" if exact_count == 3 else "NOT_QUALIFIED"',
        '"qualification_accepted_by_repository": False',
        '"p5_requalified": False',
        '"p6_requalified": False',
    ):
        if marker not in decision:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_DECISION_CONTRACT_DRIFT",
                "C4 decision contract marker is missing",
                marker,
            )

    expected_budget = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 3,
        "worker_starts": 3,
        "model_requests": 3,
    }
    if _literal_int_dict_assignment(source, "ACTION_BUDGET_LIMITS") != expected_budget:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_SUCCESSOR_BUDGET_DRIFT",
            "successor action budget drifted",
            "ACTION_BUDGET_LIMITS",
        )


def build_runtime_payload(root: Path) -> tuple[bytes, int]:
    (
        request_payload,
        architecture_payload,
        corpus_payload,
        predecessor_payload,
    ) = _validate_authorities(root)

    predecessor = predecessor_payload.decode("utf-8")
    _validate_formatter_authority(root)
    canonical_predecessor = _ruff_canonicalize_source(
        root,
        predecessor,
        "c4_predecessor_runtime_v1",
    )
    if canonical_predecessor != predecessor:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_PREDECESSOR_FORMAT_DRIFT",
            "immutable predecessor is not canonical under bound Ruff",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    expected_predecessor_budget = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 6,
        "worker_starts": 6,
        "model_requests": 6,
    }
    if (
        _literal_int_dict_assignment(
            predecessor,
            "ACTION_BUDGET_LIMITS",
        )
        != expected_predecessor_budget
    ):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_PREDECESSOR_BUDGET_DRIFT",
            "predecessor action budget drifted",
            "ACTION_BUDGET_LIMITS",
        )

    corpus_text = corpus_payload.decode("utf-8")
    source = predecessor

    source = _replace_assignment(
        source,
        "NOTEBOOK_NAME",
        'NOTEBOOK_NAME: Final = "ag-c4-canonical-prefix-qual-v1"',
    )
    source = _replace_assignment(
        source,
        "SOURCE_MAIN_COMMIT",
        f'SOURCE_MAIN_COMMIT: Final = "{SOURCE_MAIN_COMMIT}"',
    )
    source = _replace_assignment(
        source,
        "OUTPUT_ROOT",
        (
            "OUTPUT_ROOT: Final = (\n"
            '    WORK_ROOT / "canonical_synthetic_prefix_c4_'
            'behavioral_qualification_v1"\n'
            ")"
        ),
    )
    source = _replace_assignment(
        source,
        "SCRATCH_ROOT",
        (
            "SCRATCH_ROOT: Final = (\n"
            '    WORK_ROOT / "canonical_synthetic_prefix_c4_'
            'behavioral_qualification_v1_scratch"\n'
            ")"
        ),
    )
    source = _replace_assignment(
        source,
        "EVIDENCE_ZIP",
        (
            "EVIDENCE_ZIP: Final = (\n"
            '    WORK_ROOT / "ag-c4-canonical-prefix-qual-'
            'evidence-v1.zip"\n'
            ")"
        ),
    )
    source = _replace_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
        _render_int_dict_assignment(
            "ACTION_BUDGET_LIMITS",
            {
                "runtime_install_attempts": 1,
                "runtime_import_closure_probes": 1,
                "model_loads": 3,
                "worker_starts": 3,
                "model_requests": 3,
            },
        ),
    )

    helpers, c4_main = _render_c4_helpers(corpus_text)
    source = _insert_before_function(source, "main", helpers)
    source = _replace_function(source, "main", c4_main)

    compile(source, RUNTIME_PATH.as_posix(), "exec")

    canonical_source = _ruff_canonicalize_source(
        root,
        source,
        "c4_successor_runtime_v1",
    )
    canonical_again = _ruff_canonicalize_source(
        root,
        canonical_source,
        "c4_successor_runtime_idempotence_v1",
    )
    if canonical_again != canonical_source:
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_FORMATTER_NON_IDEMPOTENT",
            "bound Ruff formatter was not byte-idempotent",
            RUNTIME_PATH.as_posix(),
        )

    compile(canonical_source, RUNTIME_PATH.as_posix(), "exec")
    unchanged = _validate_change_surface(
        canonical_predecessor,
        canonical_source,
    )
    _validate_successor_contract(canonical_source)

    if _sha256(request_payload) == "":
        raise AssertionError("unreachable empty request SHA")
    if _sha256(architecture_payload) == "":
        raise AssertionError("unreachable empty review SHA")

    return canonical_source.encode("utf-8"), unchanged


def _candidate_sha(root: Path, relative: Path) -> str:
    return _sha256(_read_required(root, relative))


def _build_expected(root: Path) -> tuple[bytes, bytes, bytes]:
    (
        request_payload,
        architecture_payload,
        corpus_payload,
        predecessor_payload,
    ) = _validate_authorities(root)
    runtime_payload, unchanged = build_runtime_payload(root)

    review = ImplementationReview(
        review_id=(
            "auragateway-canonical-synthetic-prefix-c4-"
            "behavioral-qualification-implementation-v1-review"
        ),
        status="APPROVED_STATIC_C4_EXECUTION_HARNESS",
        source_main_commit=SOURCE_MAIN_COMMIT,
        qualification_request_sha256=_sha256(request_payload),
        architecture_review_sha256=_sha256(architecture_payload),
        canonical_corpus_sha256=_sha256(corpus_payload),
        reusable_prefix_receipt_sha256=(EXPECTED_REUSABLE_PREFIX_RECEIPT_SHA256),
        predecessor_runtime_sha256=_sha256(predecessor_payload),
        implementation_source_sha256=_candidate_sha(root, SOURCE_PATH),
        focused_test_sha256=_candidate_sha(root, TEST_PATH),
        runtime_payload_sha256=_sha256(runtime_payload),
        formatter_version=FORMATTER_VERSION,
        formatter_config_sha256=FORMATTER_CONFIG_SHA256,
        runtime_formatter_canonicalized=True,
        predecessor_formatter_canonical=True,
        formatter_idempotence_verified=True,
        changed_existing_functions=CHANGED_EXISTING_FUNCTIONS,
        added_functions=ADDED_FUNCTIONS,
        unchanged_existing_function_count=unchanged,
        full_prompt_token_count=EXPECTED_FULL_PROMPT_TOKEN_COUNT,
        full_prompt_token_sha256=EXPECTED_FULL_PROMPT_TOKEN_SHA256,
        reusable_prefix_token_count=EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT,
        reusable_prefix_token_sha256=EXPECTED_REUSABLE_PREFIX_TOKEN_SHA256,
        canonical_request_payload_sha256=EXPECTED_REQUEST_PAYLOAD_SHA256,
        observations=3,
        maximum_model_requests=3,
        maximum_model_loads=3,
        maximum_worker_starts=3,
        maximum_hidden_retries=0,
        maximum_replacement_requests=0,
        strict_duplicate_key_rejection=True,
        strict_integer_value_validation=True,
        finish_reason_stop_required=True,
        behavioral_failure_completes_three_observations=True,
        execution_failure_stops_without_replacement=True,
        runtime_budget_attempt_semantics=True,
        platform_budget_deferred_to_authorization_wrapper=True,
        kaggle_session_budget_runtime_enforced=False,
        save_and_run_all_budget_runtime_enforced=False,
        evidence_schema_names_frozen=True,
        p5_p6_successor_lineage_parent=True,
        runtime_execution_authorized=False,
        authorization_issuer_included=False,
        p5_execution_authorized=False,
        p6_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    review_bytes = _canonical_bytes(review)

    record = ImplementationRecord(
        record_id=(
            "auragateway-canonical-synthetic-prefix-c4-behavioral-qualification-implementation-v1"
        ),
        status="IMPLEMENTED_NOT_EXECUTED",
        source_main_commit=SOURCE_MAIN_COMMIT,
        qualification_id=QUALIFICATION_ID,
        qualification_request_sha256=_sha256(request_payload),
        architecture_review_sha256=_sha256(architecture_payload),
        canonical_corpus_version=CANONICAL_CORPUS_VERSION,
        canonical_corpus_sha256=_sha256(corpus_payload),
        reusable_prefix_receipt_sha256=(EXPECTED_REUSABLE_PREFIX_RECEIPT_SHA256),
        predecessor_runtime_path=PREDECESSOR_RUNTIME_PATH.as_posix(),
        predecessor_runtime_sha256=_sha256(predecessor_payload),
        successor_runtime_path=RUNTIME_PATH.as_posix(),
        successor_runtime_sha256=_sha256(runtime_payload),
        implementation_review_sha256=_sha256(review_bytes),
        formatter_version=FORMATTER_VERSION,
        formatter_config_sha256=FORMATTER_CONFIG_SHA256,
        runtime_formatter_canonicalized=True,
        full_prompt_token_count=EXPECTED_FULL_PROMPT_TOKEN_COUNT,
        full_prompt_token_sha256=EXPECTED_FULL_PROMPT_TOKEN_SHA256,
        reusable_prefix_token_count=EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT,
        reusable_prefix_token_sha256=EXPECTED_REUSABLE_PREFIX_TOKEN_SHA256,
        canonical_request_payload_sha256=EXPECTED_REQUEST_PAYLOAD_SHA256,
        model_requests_performed=0,
        model_loads_performed=0,
        worker_starts_performed=0,
        kaggle_execution_performed=False,
        gpu_execution_performed=False,
        notebook_generated=False,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        c4_qualified=False,
        p5_requalified=False,
        p6_requalified=False,
        final_abc_measured=False,
        production_readiness_established=False,
        p5_p6_successor_must_derive_from_this_runtime=True,
        next_gate=NEXT_GATE,
        non_claims=(
            "C4 has not been behaviorally executed.",
            "No model request was performed by this producer.",
            "No model was loaded by this producer.",
            "No worker was started by this producer.",
            "No GPU execution occurred in this tranche.",
            "No Kaggle execution occurred in this tranche.",
            "No notebook was generated in this tranche.",
            "No live execution authorization was issued.",
            "A C4 QUALIFIED observation state has not been accepted.",
            "P5 has not been requalified.",
            "P6 has not been requalified.",
            "Final A/B/C effects have not been measured.",
            "Prefix-cache correctness is not established.",
            "Historical root cause is not established.",
            "Long-run model reliability is not established.",
            "Production readiness is not established.",
            "The B-vs-D predecessor runtime remains immutable.",
        ),
    )
    return runtime_payload, review_bytes, _canonical_bytes(record)


def generate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)

    for relative, payload in (
        (RUNTIME_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    if (
        _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH))
        != EXPECTED_PREDECESSOR_RUNTIME_SHA256
    ):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "B-vs-D predecessor changed during generation",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    return {
        "status": "C4_IMPLEMENTATION_GENERATED",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "formatter_version": FORMATTER_VERSION,
        "formatter_config_sha256": FORMATTER_CONFIG_SHA256,
        "runtime_formatter_canonicalized": True,
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "full_prompt_token_count": EXPECTED_FULL_PROMPT_TOKEN_COUNT,
        "reusable_prefix_token_count": EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT,
        "canonical_request_payload_sha256": EXPECTED_REQUEST_PAYLOAD_SHA256,
        "model_requests_performed": 0,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)

    for relative, payload in (
        (RUNTIME_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        if _read_required(root, relative) != payload:
            raise C4ImplementationError(
                "C4_IMPLEMENTATION_GENERATED_ARTIFACT_DRIFT",
                "generated C4 implementation artifact drifted",
                relative.as_posix(),
            )

    if (
        _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH))
        != EXPECTED_PREDECESSOR_RUNTIME_SHA256
    ):
        raise C4ImplementationError(
            "C4_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "B-vs-D predecessor identity drifted",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    return {
        "status": "C4_IMPLEMENTATION_VALID",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "formatter_version": FORMATTER_VERSION,
        "formatter_config_sha256": FORMATTER_CONFIG_SHA256,
        "runtime_formatter_canonicalized": True,
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "full_prompt_token_count": EXPECTED_FULL_PROMPT_TOKEN_COUNT,
        "reusable_prefix_token_count": EXPECTED_REUSABLE_PREFIX_TOKEN_COUNT,
        "canonical_request_payload_sha256": EXPECTED_REQUEST_PAYLOAD_SHA256,
        "model_requests_performed": 0,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("generate", "validate"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        root = cast(Path, arguments.repo_root).resolve()
        result = generate(root) if arguments.command == "generate" else validate(root)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        C4ImplementationError,
        UnicodeDecodeError,
        ValueError,
        SyntaxError,
        json.JSONDecodeError,
    ) as error:
        payload = (
            error.envelope()
            if isinstance(error, C4ImplementationError)
            else {
                "error_code": "C4_IMPLEMENTATION_VALIDATION_ERROR",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(
            json.dumps(payload, sort_keys=True),
            file=__import__("sys").stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
