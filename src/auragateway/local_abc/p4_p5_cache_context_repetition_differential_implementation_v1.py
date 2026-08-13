"""Generate the P4/P5 cache-context repetition differential runtime V1.

The current composition-remediated runtime is immutable input authority.
This producer emits a separate successor runtime implementing the frozen 1x
versus 24x repetition differential with one fresh worker process per observation.

This module performs no Kaggle, GPU, model, or request execution and issues no
execution authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "e3c42969a83b01aadcf989fd806004feea78f3c5"

DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_design_v1.json"
)
DESIGN_SHA256: Final = "1dc00c0bc36a1979291078b16c7b54ed502385bb62a53c6043d255c5fcf4fa00"

PREDECESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py"
)
PREDECESSOR_RUNTIME_SHA256: Final = (
    "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_implementation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_cache_context_repetition_differential_implementation_v1.py"
)
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_runtime_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_cache_context_repetition_differential_implementation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_cache_context_repetition_differential_implementation_v1.json"
)

NEXT_GATE: Final = (
    "MERGE_THEN_DESIGN_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
)

REQUEST_ORDER: Final = (
    "CONTROL_1X",
    "TREATMENT_24X",
    "TREATMENT_24X",
    "CONTROL_1X",
    "CONTROL_1X",
    "TREATMENT_24X",
)
CONTROL_REPETITION_COUNT: Final = 1
TREATMENT_REPETITION_COUNT: Final = 24
TREATMENT_EXPECTED_TOKEN_COUNT: Final = 899
TREATMENT_EXPECTED_TOKEN_SHA256: Final = (
    "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
)
TREATMENT_EXPECTED_PAYLOAD_SHA256: Final = (
    "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
)

CHANGED_EXISTING_FUNCTIONS: Final = ("main",)
ADDED_FUNCTIONS: Final = (
    "decide_repetition_differential",
    "initialize_repetition_journal",
    "persist_repetition_pre_request_identity",
    "repetition_bundle_outputs",
    "repetition_context",
    "repetition_edge_class",
    "repetition_failure_record",
    "repetition_public_observation",
    "repetition_request_messages",
    "repetition_request_payload",
    "repetition_token_identity",
    "repetition_tokenize_payload",
    "run_fresh_worker_observation",
    "run_repetition_observation",
    "validate_zero_cache_baseline",
    "write_repetition_results",
)


class ImplementationError(RuntimeError):
    """Fail-closed static successor implementation error."""

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
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImplementationReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-p4-p5-cache-context-repetition-differential-implementation-v1-review"
    ]
    status: Literal["APPROVED_STATIC_SUCCESSOR_IMPLEMENTATION"]
    base_main_commit: Literal["e3c42969a83b01aadcf989fd806004feea78f3c5"]
    design_record_sha256: Literal[
        "1dc00c0bc36a1979291078b16c7b54ed502385bb62a53c6043d255c5fcf4fa00"
    ]
    predecessor_runtime_sha256: Literal[
        "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
    ]
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    focused_test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_order: tuple[str, ...]
    control_repetition_count: Literal[1] = 1
    treatment_repetition_count: Literal[24] = 24
    treatment_expected_token_count: Literal[899] = 899
    treatment_expected_token_sha256: Literal[
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    ]
    treatment_expected_payload_sha256: Literal[
        "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    ]
    maximum_model_requests: Literal[6] = 6
    maximum_model_loads: Literal[6] = 6
    maximum_worker_starts: Literal[6] = 6
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    fresh_worker_process_per_observation: Literal[True] = True
    teardown_required_between_observations: Literal[True] = True
    zero_cached_prefix_baseline_required: Literal[True] = True
    pre_request_journal_required: Literal[True] = True
    changed_existing_functions: tuple[str, ...]
    added_functions: tuple[str, ...]
    unchanged_existing_function_count: int = Field(ge=1)
    predecessor_runtime_preserved: Literal[True] = True
    current_generation_controls_preserved: Literal[True] = True
    invalid_json_retained_as_observation: Literal[True] = True
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    p5_p6_trajectory_reachable_from_successor_main: Literal[False] = False
    differential_notebook_generated: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "MERGE_THEN_DESIGN_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
    ]

    @model_validator(mode="after")
    def validate_review(self) -> ImplementationReview:
        if self.request_order != REQUEST_ORDER:
            raise ValueError("request order drifted")
        if self.changed_existing_functions != CHANGED_EXISTING_FUNCTIONS:
            raise ValueError("changed existing function inventory drifted")
        if self.added_functions != ADDED_FUNCTIONS:
            raise ValueError("added function inventory drifted")
        return self


class ImplementationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p4-p5-cache-context-repetition-differential-implementation-v1"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    base_main_commit: Literal["e3c42969a83b01aadcf989fd806004feea78f3c5"]
    design_record_sha256: Literal[
        "1dc00c0bc36a1979291078b16c7b54ed502385bb62a53c6043d255c5fcf4fa00"
    ]
    predecessor_runtime_path: Literal[
        "src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py"
    ]
    predecessor_runtime_sha256: Literal[
        "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
    ]
    successor_runtime_path: Literal[
        "src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_runtime_v1.py"
    ]
    successor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_requests_performed: Literal[0] = 0
    model_loads_performed: Literal[0] = 0
    worker_starts_performed: Literal[0] = 0
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    differential_notebook_generated: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    runtime_fix_authorized: Literal[False] = False
    threshold_search_authorized: Literal[False] = False
    assistant_topology_discriminator_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "MERGE_THEN_DESIGN_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
    ]
    non_claims: tuple[str, ...] = Field(min_length=10)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
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
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_ARTIFACT_MISSING",
            "required implementation artifact is missing or unsafe",
            relative.as_posix(),
        )

    return path.read_bytes()


def _read_exact(
    root: Path,
    relative: Path,
    expected_sha256: str,
) -> bytes:
    payload = _read_required(root, relative)

    if _sha256(payload) != expected_sha256:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_AUTHORITY_DRIFT",
            "required implementation authority identity drifted",
            relative.as_posix(),
        )

    return payload


def _read_object(
    root: Path,
    relative: Path,
    expected_sha256: str,
) -> dict[str, object]:
    payload = _read_exact(root, relative, expected_sha256)

    try:
        observed: object = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_AUTHORITY_INVALID",
            "required implementation authority is not valid JSON",
            relative.as_posix(),
        ) from error

    if not isinstance(observed, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_AUTHORITY_INVALID",
            "required implementation authority must be one object",
            relative.as_posix(),
        )

    return cast(dict[str, object], observed)


def _validate_design(root: Path) -> None:
    design = _read_object(root, DESIGN_PATH, DESIGN_SHA256)

    if design.get("design_status") != "DESIGN_FROZEN_NOT_EXECUTED":
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design status drifted",
            DESIGN_PATH.as_posix(),
        )

    if design.get("next_gate") != (
        "IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"
    ):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design next gate drifted",
            DESIGN_PATH.as_posix(),
        )

    frozen = design.get("frozen_composition")
    conditions = design.get("conditions")
    starting = design.get("starting_state")
    token_identity = design.get("token_identity")
    request_plan = design.get("request_plan")
    budget = design.get("execution_budget")
    safety = design.get("safety")
    runtime = design.get("runtime")
    generation = design.get("generation_controls")
    authorities = design.get("accepted_authorities")

    if not isinstance(frozen, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design frozen_composition contract is unavailable",
            DESIGN_PATH.as_posix(),
        )
    if not isinstance(starting, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design starting_state contract is unavailable",
            DESIGN_PATH.as_posix(),
        )
    if not isinstance(token_identity, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design token_identity contract is unavailable",
            DESIGN_PATH.as_posix(),
        )
    if not isinstance(budget, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design execution_budget contract is unavailable",
            DESIGN_PATH.as_posix(),
        )
    if not isinstance(safety, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design safety contract is unavailable",
            DESIGN_PATH.as_posix(),
        )
    if not isinstance(runtime, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design runtime contract is unavailable",
            DESIGN_PATH.as_posix(),
        )
    if not isinstance(generation, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design generation_controls contract is unavailable",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(conditions, list) or len(conditions) != 2:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design condition inventory drifted",
            DESIGN_PATH.as_posix(),
        )

    expected_conditions = (
        ("CONTROL_1X", CONTROL_REPETITION_COUNT),
        ("TREATMENT_24X", TREATMENT_REPETITION_COUNT),
    )
    observed_conditions: list[tuple[str, int]] = []
    for item in conditions:
        if not isinstance(item, dict):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "design condition object drifted",
                DESIGN_PATH.as_posix(),
            )
        condition_id = item.get("condition_id")
        repetition_count = item.get("repetition_count")
        if (
            not isinstance(condition_id, str)
            or isinstance(repetition_count, bool)
            or not isinstance(repetition_count, int)
        ):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "design condition fields drifted",
                DESIGN_PATH.as_posix(),
            )
        observed_conditions.append((condition_id, repetition_count))

    if tuple(observed_conditions) != expected_conditions:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design condition values drifted",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(request_plan, list) or len(request_plan) != 6:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design request plan drifted",
            DESIGN_PATH.as_posix(),
        )

    observed_order: list[str] = []
    observed_ordinals: list[int] = []
    for item in request_plan:
        if not isinstance(item, dict):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "design request-plan item drifted",
                DESIGN_PATH.as_posix(),
            )
        condition_id = item.get("condition_id")
        ordinal = item.get("ordinal")
        if not isinstance(condition_id, str):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "design request-plan condition drifted",
                DESIGN_PATH.as_posix(),
            )
        if isinstance(ordinal, bool) or not isinstance(ordinal, int):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "design request-plan ordinal drifted",
                DESIGN_PATH.as_posix(),
            )
        observed_order.append(condition_id)
        observed_ordinals.append(ordinal)

    if tuple(observed_order) != REQUEST_ORDER or tuple(observed_ordinals) != tuple(range(1, 7)):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design request-plan chronology drifted",
            DESIGN_PATH.as_posix(),
        )

    frozen_expected = {
        "message_roles": ["system", "user", "assistant", "user"],
        "system_instruction": (
            "Return only the exact JSON object supplied in the final user message, "
            "with no markdown or additional text."
        ),
        "cache_context_tail": (
            "Return only the exact JSON object supplied in the final user message, "
            "with no markdown or additional text."
        ),
        "assistant_ack": "Synthetic deterministic context acknowledged.",
        "final_object_canonical": '{"probe":"exact-runtime-p5-p6","value":1}',
        "variable_under_test": "CACHE_CONTEXT_REPETITION_COUNT",
        "prefix_variant": "A",
        "no_schema_or_guided_decoding": True,
        "parser_semantics_preserved": True,
    }
    for key, expected in frozen_expected.items():
        if frozen.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "frozen composition drifted",
                key,
            )

    starting_expected = {
        "strategy": "FRESH_WORKER_PROCESS_PER_OBSERVATION",
        "prior_request_cache_carryover_permitted": False,
        "namespace_only_reset_permitted": False,
        "require_fresh_worker_identity": True,
        "require_zero_cached_prefix_baseline": True,
        "teardown_required_between_observations": True,
        "teardown_failure_invalidates_diagnostic": True,
        "historical_reset_precedent_only": True,
    }
    for key, expected in starting_expected.items():
        if starting.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "starting-state contract drifted",
                key,
            )

    token_expected = {
        "prefix_variant": "A",
        "treatment_expected_token_count": TREATMENT_EXPECTED_TOKEN_COUNT,
        "treatment_expected_token_sha256": TREATMENT_EXPECTED_TOKEN_SHA256,
        "treatment_expected_payload_sha256": TREATMENT_EXPECTED_PAYLOAD_SHA256,
        "treatment_must_match_historical_failed_24x_identity": True,
        "treatment_intra_condition_identity_required": True,
        "control_intra_condition_identity_required": True,
        "control_must_differ_from_treatment_token_identity": True,
        "pre_request_journal_required": True,
        "journal_persisted_before_model_request": True,
        "raw_prompt_retained": False,
    }
    for key, expected in token_expected.items():
        if token_identity.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "token-identity contract drifted",
                key,
            )

    budget_expected = {
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "hidden_retries_permitted": 0,
        "replacement_workers_permitted": 0,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "external_network_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
    }
    for key, expected in budget_expected.items():
        if budget.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "execution budget drifted",
                key,
            )

    runtime_expected = {
        "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "tokenizer_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "model_snapshot_sha256": (
            "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
        ),
        "backend": "TRITON_ATTN",
        "vllm_distribution": "0.25.1+cu129",
        "torch": "2.11.0+cu129",
        "torch_cuda": "12.9",
        "triton": "3.6.0",
        "transformers": "5.14.1",
        "platform_topology": "T4_x2",
        "worker_gpu_index": 0,
        "prefix_caching_enabled": True,
        "cache_block_size": 16,
        "max_model_len": 4096,
    }
    for key, expected in runtime_expected.items():
        if runtime.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "runtime identity drifted",
                key,
            )

    generation_expected = {
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
        "response_format_present": False,
        "output_mode": "UNCONSTRAINED",
    }
    for key, expected in generation_expected.items():
        if generation.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "generation controls drifted",
                key,
            )

    for key in (
        "runtime_execution_authorized",
        "new_execution_authorized",
        "kaggle_execution_performed",
        "gpu_execution_performed",
        "model_loaded",
        "worker_started",
        "runtime_fix_authorized",
        "threshold_search_authorized",
        "assistant_topology_discriminator_authorized",
        "measured_abc_execution_authorized",
    ):
        if safety.get(key) is not False:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
                "design safety boundary drifted",
                key,
            )

    if safety.get("model_requests_performed") != 0:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design unexpectedly records model requests",
            "model_requests_performed",
        )

    if not isinstance(authorities, list):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "design authority inventory is unavailable",
            DESIGN_PATH.as_posix(),
        )

    runtime_receipts = [
        item
        for item in authorities
        if isinstance(item, dict) and item.get("role") == "current_remediated_runtime"
    ]
    if len(runtime_receipts) != 1:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "current runtime authority cardinality drifted",
            DESIGN_PATH.as_posix(),
        )
    receipt = runtime_receipts[0]
    if receipt.get("path") != PREDECESSOR_RUNTIME_PATH.as_posix():
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "current runtime authority path drifted",
            DESIGN_PATH.as_posix(),
        )
    if receipt.get("sha256") != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_DESIGN_DRIFT",
            "current runtime authority SHA drifted",
            DESIGN_PATH.as_posix(),
        )


def _validate_predecessor_contract(root: Path) -> None:
    source = _read_exact(
        root,
        PREDECESSOR_RUNTIME_PATH,
        PREDECESSOR_RUNTIME_SHA256,
    ).decode("utf-8")

    required_markers = (
        "SYSTEM_PROMPT = (",
        "SYNTHETIC_CACHE_CONTEXT_A = (",
        '"AuraGateway deterministic prefix-cache reliability probe variant A. "',
        '"Return only the exact JSON object supplied in the final user message, "',
        'SYNTHETIC_ASSISTANT_ACK = "Synthetic deterministic context acknowledged."',
        'EXPECTED_OBJECT = {"probe": "exact-runtime-p5-p6", "value": 1}',
        '"temperature": 0,',
        '"top_p": 1,',
        '"repetition_penalty": 1.1,',
        '"seed": 7,',
        '"max_tokens": 32,',
        '"stream": False,',
        '"--enable-prefix-caching",',
        '"--block-size",',
        "str(CACHE_BLOCK_SIZE),",
        '"--attention-backend",',
        "EXPECTED_BACKEND,",
    )
    for marker in required_markers:
        if marker not in source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_PREDECESSOR_DRIFT",
                "predecessor runtime contract drifted",
                marker,
            )


def _function_nodes(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    result: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in result:
                raise ImplementationError(
                    "P4_P5_REPETITION_IMPLEMENTATION_SOURCE_AMBIGUOUS",
                    "duplicate top-level function name",
                    node.name,
                )
            result[node.name] = node

    return result


def _class_nodes(source: str) -> dict[str, ast.ClassDef]:
    tree = ast.parse(source)
    result: dict[str, ast.ClassDef] = {}

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if node.name in result:
                raise ImplementationError(
                    "P4_P5_REPETITION_IMPLEMENTATION_SOURCE_AMBIGUOUS",
                    "duplicate top-level class name",
                    node.name,
                )
            result[node.name] = node

    return result


def _assignment_node(
    source: str,
    name: str,
) -> ast.Assign | ast.AnnAssign:
    tree = ast.parse(source)
    matches: list[ast.Assign | ast.AnnAssign] = []

    for node in tree.body:
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
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_SOURCE_AMBIGUOUS",
            "required top-level assignment cardinality drifted",
            name,
        )

    return matches[0]


def _segment(source: str, node: ast.AST) -> str:
    observed = ast.get_source_segment(source, node)

    if observed is None:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "unable to recover source segment",
        )

    return observed


def _replace_node(
    source: str,
    node: ast.AST,
    replacement: str,
) -> str:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)

    if not isinstance(start, int) or not isinstance(end, int):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "source node line boundary is unavailable",
        )

    lines = source.splitlines(keepends=True)
    normalized = replacement.rstrip() + "\n"
    lines[start - 1 : end] = [normalized]
    return "".join(lines)


def _replace_function(
    source: str,
    name: str,
    replacement: str,
) -> str:
    functions = _function_nodes(source)
    node = functions.get(name)

    if node is None:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_FUNCTION_MISSING",
            "required predecessor function is missing",
            name,
        )

    return _replace_node(
        source,
        node,
        textwrap.dedent(replacement).strip(),
    )


def _replace_assignment(
    source: str,
    name: str,
    replacement: str,
) -> str:
    node = _assignment_node(source, name)
    return _replace_node(source, node, replacement)


def _literal_int_dict_assignment(
    source: str,
    name: str,
) -> dict[str, int]:
    node = _assignment_node(source, name)

    value_node: ast.expr | None = None

    if isinstance(node, ast.Assign):
        value_node = node.value

    if isinstance(node, ast.AnnAssign):
        value_node = node.value

    if value_node is None:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_BUDGET_INVALID",
            "action-budget assignment has no value",
            name,
        )

    raw: object = ast.literal_eval(value_node)

    if not isinstance(raw, dict):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_BUDGET_INVALID",
            "action-budget assignment is not one dictionary",
            name,
        )

    result: dict[str, int] = {}

    for raw_key, raw_value in raw.items():
        if not isinstance(raw_key, str):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_BUDGET_INVALID",
                "action-budget key is not a string",
                name,
            )

        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_BUDGET_INVALID",
                "action-budget value is not an integer",
                name,
            )

        result[raw_key] = raw_value

    return result


def _render_int_dict_assignment(
    name: str,
    values: dict[str, int],
) -> str:
    lines = [f"{name}: Final = {{"]

    for key, value in values.items():
        lines.append(f'    "{key}": {value},')

    lines.append("}")
    return "\n".join(lines)


def _insert_before_function(
    source: str,
    function_name: str,
    block: str,
) -> str:
    functions = _function_nodes(source)
    node = functions.get(function_name)

    if node is None:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_FUNCTION_MISSING",
            "required insertion anchor is missing",
            function_name,
        )

    lines = source.splitlines(keepends=True)
    normalized = textwrap.dedent(block).strip() + "\n\n\n"
    lines[node.lineno - 1 : node.lineno - 1] = [normalized]
    return "".join(lines)


REPETITION_HELPERS: Final = r"""
REPETITION_IMPLEMENTATION_BASE_COMMIT: Final = "e3c42969a83b01aadcf989fd806004feea78f3c5"
REPETITION_DESIGN_RECORD_SHA256: Final = (
    "1dc00c0bc36a1979291078b16c7b54ed502385bb62a53c6043d255c5fcf4fa00"
)
REPETITION_REQUEST_ORDER: Final = (
    "CONTROL_1X",
    "TREATMENT_24X",
    "TREATMENT_24X",
    "CONTROL_1X",
    "CONTROL_1X",
    "TREATMENT_24X",
)
REPETITION_CONTROL_COUNT: Final = 1
REPETITION_TREATMENT_COUNT: Final = 24
REPETITION_TREATMENT_TOKEN_COUNT: Final = 899
REPETITION_TREATMENT_TOKEN_SHA256: Final = (
    "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
)
REPETITION_TREATMENT_PAYLOAD_SHA256: Final = (
    "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
)
REPETITION_CONTEXT_BODY: Final = (
    "AuraGateway deterministic prefix-cache reliability probe variant A. "
    "This text is synthetic, contains no customer data, and must remain "
    "byte-identical whenever prefix variant A is requested. "
)
REPETITION_OUTPUT_NAMES: Final = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "p4_p5_repetition_runtime_ready_v1.json",
    "pre_request_token_identity_journal_v1.json",
    "p4_p5_repetition_request_results_v1.json",
    "p4_p5_repetition_decision_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "failure_report_v1.json",
    "p4_p5_repetition_summary_v1.json",
    "human_report_v1.md",
    "bundle_manifest_v1.json",
)


def repetition_context(repetition_count: int) -> str:
    if repetition_count not in {
        REPETITION_CONTROL_COUNT,
        REPETITION_TREATMENT_COUNT,
    }:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "unsupported cache-context repetition count",
        )
    observed = REPETITION_CONTEXT_BODY * repetition_count + SYSTEM_PROMPT
    if repetition_count == REPETITION_TREATMENT_COUNT and observed != SYNTHETIC_CACHE_CONTEXT_A:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "24x treatment context no longer matches the historical prefix-A payload",
        )
    return observed


def repetition_request_messages(
    condition_id: str,
) -> list[dict[str, str]]:
    if condition_id == "CONTROL_1X":
        repetition_count = REPETITION_CONTROL_COUNT
    elif condition_id == "TREATMENT_24X":
        repetition_count = REPETITION_TREATMENT_COUNT
    else:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "unsupported repetition-differential condition",
        )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": repetition_context(repetition_count)},
        {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
        {"role": "user", "content": EXPECTED_OBJECT_CANONICAL},
    ]


def repetition_request_payload(
    condition_id: str,
) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": repetition_request_messages(condition_id),
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def repetition_tokenize_payload(
    condition_id: str,
) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": repetition_request_messages(condition_id),
        "add_generation_prompt": True,
        "continue_final_message": False,
        "add_special_tokens": False,
        "return_token_strs": False,
    }


def repetition_token_identity(
    worker: Worker,
    condition_id: str,
) -> dict[str, object]:
    response = post_json(
        f"http://127.0.0.1:{worker.port}/tokenize",
        repetition_tokenize_payload(condition_id),
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
            "repetition tokenization response shape is invalid",
        )
    tokens: list[int] = []
    for raw_token in raw_tokens:
        if isinstance(raw_token, bool) or not isinstance(raw_token, int):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "repetition tokenization returned a non-integer token id",
            )
        if raw_token < 0:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "repetition tokenization returned a negative token id",
            )
        tokens.append(raw_token)
    return {
        "token_count": len(tokens),
        "token_sha256": sha256_bytes(canonical_json(tokens).encode("utf-8")),
    }


def initialize_repetition_journal() -> None:
    if PRE_REQUEST_TOKEN_IDENTITY_JOURNAL.exists():
        raise RuntimeError("pre-request token-identity journal already exists")
    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            "schema_version": "1.0.0",
            "journal_id": (
                "auragateway-p4-p5-cache-context-repetition-differential-"
                "pre-request-token-identity-v1"
            ),
            "entries": [],
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
        },
    )


def persist_repetition_pre_request_identity(
    request_ordinal: int,
    condition_id: str,
    repetition_count: int,
    token_identity: dict[str, object],
    payload_sha256: str,
) -> None:
    journal = _read_pre_request_token_identity_journal()
    entries = journal.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("pre-request token-identity journal entries are invalid")
    if request_ordinal != len(entries) + 1:
        raise RuntimeError("pre-request token-identity request ordinal drifted")
    token_count = token_identity.get("token_count")
    token_sha256 = token_identity.get("token_sha256")
    if (
        isinstance(token_count, bool)
        or not isinstance(token_count, int)
        or not isinstance(token_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", token_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", payload_sha256) is None
    ):
        raise RuntimeError("pre-request token identity is invalid")
    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            **journal,
            "entries": [
                *entries,
                {
                    "request_ordinal": request_ordinal,
                    "condition_id": condition_id,
                    "prefix_variant": "A",
                    "repetition_count": repetition_count,
                    "token_count": token_count,
                    "token_sha256": token_sha256,
                    "payload_sha256": payload_sha256,
                    "persisted_before_model_request": True,
                },
            ],
        },
    )


def validate_zero_cache_baseline(
    worker: Worker,
) -> dict[str, float]:
    baseline = worker.metric_snapshot()
    values = {
        "prefix_cache_queries": baseline.prefix_cache_queries,
        "prefix_cache_hits": baseline.prefix_cache_hits,
        "local_compute": baseline.local_compute,
        "local_cache_hit": baseline.local_cache_hit,
        "external_kv_transfer": baseline.external_kv_transfer,
        "cached_prompt_tokens": baseline.cached_prompt_tokens,
        "newly_computed_prefill_tokens": baseline.newly_computed_prefill_tokens,
    }
    if any(abs(float(value)) > 1e-9 for value in values.values()):
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "fresh observation worker did not begin at a zero request/cache metric baseline",
        )
    return values


def repetition_edge_class(character: str | None) -> str:
    if character is None:
        return "NONE"
    if character in "{[":
        return "JSON_OPEN"
    if character in "]}":
        return "JSON_CLOSE"
    if character == "`":
        return "BACKTICK"
    if character.isspace():
        return "WHITESPACE"
    if character.isalpha():
        return "ALPHA"
    if character.isdigit():
        return "DIGIT"
    return "OTHER"


def run_repetition_observation(
    worker: Worker,
    condition_id: str,
    sequence_index: int,
    counters: dict[str, int],
) -> dict[str, object]:
    repetition_count = (
        REPETITION_CONTROL_COUNT
        if condition_id == "CONTROL_1X"
        else REPETITION_TREATMENT_COUNT
        if condition_id == "TREATMENT_24X"
        else None
    )
    if repetition_count is None:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "unsupported repetition-differential condition",
        )

    token_identity = repetition_token_identity(worker, condition_id)
    payload = repetition_request_payload(condition_id)
    payload_sha256 = sha256_text(canonical_json(payload))

    if condition_id == "TREATMENT_24X":
        if token_identity.get("token_count") != REPETITION_TREATMENT_TOKEN_COUNT:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "24x treatment token count drifted before model request",
            )
        if token_identity.get("token_sha256") != REPETITION_TREATMENT_TOKEN_SHA256:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "24x treatment token identity drifted before model request",
            )
        if payload_sha256 != REPETITION_TREATMENT_PAYLOAD_SHA256:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "24x treatment payload identity drifted before model request",
            )

    request_ordinal = counters["model_requests"] + 1
    if request_ordinal != sequence_index:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "pre-request ordinal does not match the frozen chronology",
        )

    persist_repetition_pre_request_identity(
        request_ordinal,
        condition_id,
        repetition_count,
        token_identity,
        payload_sha256,
    )

    baseline = validate_zero_cache_baseline(worker)
    before = worker.metric_snapshot()

    consume_actions(counters, "model_requests")
    encoded = canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        bounded_loopback(f"http://127.0.0.1:{worker.port}/v1/chat/completions"),
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
            f"repetition request HTTP failure: {error.code}",
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            "repetition request transport failed",
        ) from error

    if status_code != 200:
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            "repetition request returned an unexpected HTTP status",
        )

    try:
        envelope = json.loads(response_payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response envelope is not valid JSON",
        ) from error
    if not isinstance(envelope, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response envelope root is invalid",
        )

    usage = envelope.get("usage")
    choices = envelope.get("choices")
    if not isinstance(usage, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response usage is missing",
        )
    if not isinstance(choices, list) or len(choices) != 1:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response choices are invalid",
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response choice is invalid",
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response message is invalid",
        )
    content = message.get("content")
    if not isinstance(content, str):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition response content is not a string",
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
            "repetition completion-token budget drifted",
        )
    if isinstance(prompt_tokens, bool) or not isinstance(prompt_tokens, int) or prompt_tokens <= 0:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "repetition prompt-token count is invalid",
        )

    after = worker.metric_snapshot()
    delta = metric_delta(before, after)

    stripped = content.strip()
    first = stripped[0] if stripped else None
    last = stripped[-1] if stripped else None
    valid_json = False
    exact_object = False
    json_error_line: int | None = None
    json_error_column: int | None = None
    json_error_position: int | None = None
    try:
        parsed = json.loads(content)
        expected = json.loads(EXPECTED_OBJECT_CANONICAL)
        valid_json = True
        exact_object = parsed == expected
    except json.JSONDecodeError as error:
        json_error_line = error.lineno
        json_error_column = error.colno
        json_error_position = error.pos

    worker_report = worker.report()
    pid = worker_report.get("pid")
    process_start_ticks_value = worker_report.get("process_start_ticks")
    process_identity_sha256 = sha256_text(
        canonical_json(
            {
                "pid": pid,
                "process_start_ticks": process_start_ticks_value,
            }
        )
    )

    return {
        "condition_id": condition_id,
        "sequence_index": sequence_index,
        "prefix_variant": "A",
        "repetition_count": repetition_count,
        "worker_instance_id": worker.instance_id,
        "worker_process_identity_sha256": process_identity_sha256,
        "token_count": token_identity["token_count"],
        "token_sha256": token_identity["token_sha256"],
        "payload_sha256": payload_sha256,
        "zero_cache_baseline": True,
        "baseline_metrics": baseline,
        "http_status": status_code,
        "response_sha256": sha256_text(content),
        "response_length": len(content),
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "valid_json": valid_json,
        "exact_object": exact_object,
        "json_error_line": json_error_line,
        "json_error_column": json_error_column,
        "json_error_position": json_error_position,
        "first_non_whitespace_class": repetition_edge_class(first),
        "last_non_whitespace_class": repetition_edge_class(last),
        "markdown_fence_detected": "```" in content,
        "metric_delta": asdict(delta),
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }


def repetition_public_observation(
    observation: dict[str, object],
) -> dict[str, object]:
    permitted = (
        "condition_id",
        "sequence_index",
        "prefix_variant",
        "repetition_count",
        "worker_instance_id",
        "worker_process_identity_sha256",
        "token_count",
        "token_sha256",
        "payload_sha256",
        "zero_cache_baseline",
        "baseline_metrics",
        "http_status",
        "response_sha256",
        "response_length",
        "finish_reason",
        "prompt_tokens",
        "completion_tokens",
        "valid_json",
        "exact_object",
        "json_error_line",
        "json_error_column",
        "json_error_position",
        "first_non_whitespace_class",
        "last_non_whitespace_class",
        "markdown_fence_detected",
        "metric_delta",
        "raw_prompt_retained",
        "raw_output_retained",
    )
    return {name: observation.get(name) for name in permitted}


def run_fresh_worker_observation(
    model_home: Path,
    snapshot: Path,
    condition_id: str,
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
        observation = run_repetition_observation(
            worker,
            condition_id,
            sequence_index,
            counters,
        )
    except Exception as error:
        primary_error = error
    finally:
        teardown = safe_worker_teardown(
            worker,
            f"REPETITION_OBSERVATION_{sequence_index}_TERMINAL",
        )
        teardown_reports.append(teardown)

    teardown_status = teardown.get("status")
    if teardown_status not in {"PASSED", "NOT_STARTED"}:
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "fresh observation worker teardown proof failed",
        )
    if primary_error is not None:
        raise primary_error
    if teardown_status != "PASSED":
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "completed observation did not prove worker teardown",
        )
    if observation is None or report is None:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "fresh observation did not produce complete evidence",
        )
    return observation


def write_repetition_results(
    results: list[dict[str, object]],
    status: str,
) -> None:
    write_json(
        OUTPUT_ROOT / "p4_p5_repetition_request_results_v1.json",
        {
            "schema_version": "1.0.0",
            "status": status,
            "scheduled_request_count": len(REPETITION_REQUEST_ORDER),
            "observed_request_count": len(results),
            "request_order": list(REPETITION_REQUEST_ORDER),
            "results": [repetition_public_observation(item) for item in results],
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        },
    )


def decide_repetition_differential(
    results: list[dict[str, object]],
    worker_reports: list[dict[str, object]],
    teardown_reports: list[dict[str, object]],
    counters: dict[str, int],
) -> dict[str, object]:
    if len(results) != 6:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "repetition differential result count drifted",
        )
    observed_order = tuple(str(row.get("condition_id")) for row in results)
    if observed_order != REPETITION_REQUEST_ORDER:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "repetition differential chronology drifted",
        )
    observed_indexes = tuple(row.get("sequence_index") for row in results)
    if observed_indexes != tuple(range(1, 7)):
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "repetition differential sequence indexes drifted",
        )
    if len(worker_reports) != 6 or len(teardown_reports) != 6:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "fresh-worker evidence cardinality drifted",
        )
    if any(item.get("status") != "PASSED" for item in teardown_reports):
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "one or more observation teardowns failed",
        )
    worker_identities = {
        str(row.get("worker_process_identity_sha256"))
        for row in results
        if isinstance(row.get("worker_process_identity_sha256"), str)
    }
    if len(worker_identities) != 6:
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "fresh worker process identity was reused across observations",
        )
    if any(row.get("zero_cache_baseline") is not True for row in results):
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "one or more observations lacked a zero cache baseline",
        )

    expected_counters = {
        "model_requests": 6,
        "model_loads": 6,
        "worker_starts": 6,
        "hidden_retries": 0,
        "network_requests": 0,
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
    }
    for name, expected in expected_counters.items():
        if counters.get(name) != expected:
            raise DiagnosticFailure(
                "REQUEST_RECONCILIATION_FAILURE",
                f"{name} expected {expected}, observed {counters.get(name)}",
            )

    control = [row for row in results if row.get("condition_id") == "CONTROL_1X"]
    treatment = [row for row in results if row.get("condition_id") == "TREATMENT_24X"]
    if len(control) != 3 or len(treatment) != 3:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "condition cardinality drifted",
        )

    treatment_token_pairs = {(row.get("token_count"), row.get("token_sha256")) for row in treatment}
    treatment_payloads = {row.get("payload_sha256") for row in treatment}
    if treatment_token_pairs != {
        (REPETITION_TREATMENT_TOKEN_COUNT, REPETITION_TREATMENT_TOKEN_SHA256)
    }:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "24x treatment token identity failed reconciliation",
        )
    if treatment_payloads != {REPETITION_TREATMENT_PAYLOAD_SHA256}:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "24x treatment payload identity failed reconciliation",
        )

    control_token_pairs = {(row.get("token_count"), row.get("token_sha256")) for row in control}
    control_payloads = {row.get("payload_sha256") for row in control}
    if len(control_token_pairs) != 1 or len(control_payloads) != 1:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "1x control identity is not internally stable",
        )
    if control_token_pairs == treatment_token_pairs:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "1x control token identity does not differ from 24x treatment",
        )
    if control_payloads == treatment_payloads:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "1x control payload identity does not differ from 24x treatment",
        )

    control_exact = sum(row.get("exact_object") is True for row in control)
    treatment_exact = sum(row.get("exact_object") is True for row in treatment)
    control_valid_json = sum(row.get("valid_json") is True for row in control)
    treatment_valid_json = sum(row.get("valid_json") is True for row in treatment)

    if control_exact in {1, 2}:
        state = "CONTROL_NOT_RELIABLE"
    elif control_exact == 3 and treatment_exact == 0:
        state = "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"
    elif control_exact == 0 and treatment_exact == 0:
        state = "REPETITION_NOT_NECESSARY"
    elif control_exact == 3 and treatment_exact == 3:
        state = "REGRESSION_NOT_REPRODUCED"
    elif control_exact == 3 and treatment_exact in {1, 2}:
        state = "NON_DETERMINISTIC_OR_AMBIGUOUS"
    else:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "observed behavioral combination is not covered by the frozen decision contract",
        )

    return {
        "schema_version": "1.0.0",
        "status": "DECIDED",
        "decision_state": state,
        "variable_under_test": "CACHE_CONTEXT_REPETITION_COUNT",
        "control_repetition_count": REPETITION_CONTROL_COUNT,
        "treatment_repetition_count": REPETITION_TREATMENT_COUNT,
        "control_exact_object_count": control_exact,
        "treatment_exact_object_count": treatment_exact,
        "control_valid_json_count": control_valid_json,
        "treatment_valid_json_count": treatment_valid_json,
        "fresh_worker_process_per_observation": True,
        "worker_identity_cardinality": len(worker_identities),
        "treatment_historical_identity_matched": True,
        "control_intra_condition_identity_matched": True,
        "treatment_intra_condition_identity_matched": True,
        "cache_telemetry_is_diagnostic_only": True,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }


def repetition_failure_record(
    error: Exception,
    active_failure_code: str,
    failed_stage: str,
    completed_requests: int,
) -> dict[str, object]:
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
        safe_message = sanitize_excerpt(str(error))[:512] or type(error).__name__
    return {
        "schema_version": "1.0.0",
        "status": "DIAGNOSTIC_INVALID",
        "failed_stage": failed_stage,
        "completed_requests": completed_requests,
        "failure_class": failure_class,
        "detail_code": detail_code,
        "error_type": type(error).__name__,
        "safe_message": safe_message,
    }


def repetition_bundle_outputs() -> dict[str, object]:
    required_before_manifest = set(REPETITION_OUTPUT_NAMES) - {"bundle_manifest_v1.json"}
    observed_before_manifest = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    missing = required_before_manifest - observed_before_manifest
    unexpected = observed_before_manifest - required_before_manifest
    if missing or unexpected:
        raise RuntimeError(
            "repetition evidence output contract drifted: "
            + canonical_json(
                {
                    "missing": sorted(missing),
                    "unexpected": sorted(unexpected),
                }
            )
        )
    entries = []
    for name in REPETITION_OUTPUT_NAMES:
        path = OUTPUT_ROOT / name
        if not path.is_file():
            continue
        entries.append(
            {
                "path": name,
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "diagnostic_id": ("auragateway-p4-p5-cache-context-repetition-differential-v1"),
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "members": [item for item in entries if item["path"] != "bundle_manifest_v1.json"],
        "scratch_directories_included": False,
        "worker_log_directory_included": False,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }
    write_json(OUTPUT_ROOT / "bundle_manifest_v1.json", manifest)
    with zipfile.ZipFile(
        EVIDENCE_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in REPETITION_OUTPUT_NAMES:
            path = OUTPUT_ROOT / name
            if path.is_file():
                archive.write(path, arcname=name)
    if EVIDENCE_ZIP.stat().st_size > MAX_EVIDENCE_ZIP_BYTES:
        raise RuntimeError("repetition evidence ZIP exceeds the byte budget")
    return {
        "evidence_zip": str(EVIDENCE_ZIP),
        "evidence_zip_sha256": file_sha256(EVIDENCE_ZIP),
        "evidence_zip_size_bytes": EVIDENCE_ZIP.stat().st_size,
    }
"""


REPETITION_MAIN: Final = r"""def main() -> int:
    if OUTPUT_ROOT.exists() or SCRATCH_ROOT.exists() or EVIDENCE_ZIP.exists():
        raise RuntimeError(
            "repetition differential output, scratch, or evidence path already exists"
        )
    OUTPUT_ROOT.mkdir(parents=True)
    LOG_ROOT.mkdir()
    SCRATCH_ROOT.mkdir()
    initialize_repetition_journal()

    counters = {
        "kaggle_sessions": 1,
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
    failure: dict[str, object] | None = None
    decision: dict[str, object] | None = None
    authorization: dict[str, object] | None = None
    active_failure_code = "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH"
    failed_stage = "RUNTIME_SOURCE_IDENTITY"

    try:
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
        environment_report = runtime_environment_report(runtime_environment)
        if environment_report["prohibited_stub_path_present"] is not False:
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
        active_failure_code = "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED"
        validate_process_tree_import_closure(counters)

        failed_stage = "MODEL_HOME"
        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        model_home, snapshot = prepare_model_home(source_snapshot)

        write_json(
            OUTPUT_ROOT / "p4_p5_repetition_runtime_ready_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "PASSED",
                "decision": "STATIC_RUNTIME_PREREQUISITES_REALIZED",
                "runtime_identity": runtime_identity,
                "runtime_source_identity": source_identity,
                "model_repository": MODEL_REPOSITORY,
                "model_revision": MODEL_REVISION,
                "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
                "backend": EXPECTED_BACKEND,
                "prefix_cache_enabled": True,
                "cache_block_size": CACHE_BLOCK_SIZE,
                "scheduled_worker_starts": 6,
                "scheduled_model_loads": 6,
                "scheduled_model_requests": 6,
                "fresh_worker_process_per_observation": True,
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

        for sequence_index, condition_id in enumerate(
            REPETITION_REQUEST_ORDER,
            start=1,
        ):
            failed_stage = f"OBSERVATION_{sequence_index}_{condition_id}"
            active_failure_code = "WORKER_STARTUP_FAILURE"
            observation = run_fresh_worker_observation(
                model_home,
                snapshot,
                condition_id,
                sequence_index,
                counters,
                worker_reports,
                teardown_reports,
            )
            results.append(observation)
            write_repetition_results(results, "IN_PROGRESS")

        failed_stage = "ACTION_RECONCILIATION"
        active_failure_code = "REQUEST_RECONCILIATION_FAILURE"
        expected_counters = {
            "kaggle_sessions": 1,
            "runtime_install_attempts": 1,
            "runtime_import_closure_probes": 1,
            "model_loads": 6,
            "worker_starts": 6,
            "model_requests": 6,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "hidden_retries": 0,
            "external_spend": 0,
        }
        for name, expected in expected_counters.items():
            if counters[name] != expected:
                raise DiagnosticFailure(
                    "REQUEST_RECONCILIATION_FAILURE",
                    f"{name} expected {expected}, observed {counters[name]}",
                )

        failed_stage = "DIFFERENTIAL_DECISION"
        active_failure_code = "HARNESS_SEMANTIC_FAILURE"
        decision = decide_repetition_differential(
            results,
            worker_reports,
            teardown_reports,
            counters,
        )

    except Exception as error:
        failure = repetition_failure_record(
            error,
            active_failure_code,
            failed_stage,
            len(results),
        )

    teardown_failures = tuple(
        item for item in teardown_reports if item.get("status") not in {"PASSED", "NOT_STARTED"}
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
            "scheduled_worker_count": 6,
            "observed_teardown_count": len(teardown_reports),
            "worker_teardowns": teardown_reports,
            "fresh_worker_process_per_observation": True,
            "all_completed_observations_torn_down": (
                not teardown_failures and len(teardown_reports) >= len(results)
            ),
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        },
    )

    if teardown_failures and failure is None:
        failure = {
            "schema_version": "1.0.0",
            "status": "DIAGNOSTIC_INVALID",
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
            "safe_message": (sanitize_excerpt(str(error))[:512] or type(error).__name__),
        }
        write_json(
            OUTPUT_ROOT / "scratch_cleanup_report_v1.json",
            cleanup,
        )

    if cleanup.get("status") != "PASSED" and failure is None:
        failure = {
            "schema_version": "1.0.0",
            "status": "DIAGNOSTIC_INVALID",
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
    if len(results) == 6 and failure is None:
        result_status = "COMPLETE"
    write_repetition_results(results, result_status)

    if decision is not None and failure is None:
        write_json(
            OUTPUT_ROOT / "p4_p5_repetition_decision_v1.json",
            decision,
        )
    else:
        write_json(
            OUTPUT_ROOT / "p4_p5_repetition_decision_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NOT_EVALUATED",
                "decision_state": None,
                "blocked_by": (None if failure is None else failure.get("failure_class")),
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

    failure_class = None if failure is None else str(failure.get("failure_class"))
    ensure_runtime_source_identity_report(failure_class)
    ensure_install_report(failure_class)
    ensure_import_closure_report(failure_class)

    environment_path = OUTPUT_ROOT / "runtime_environment_report_v1.json"
    if not environment_path.is_file():
        write_json(
            environment_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
                "raw_environment_retained": False,
            },
        )

    ready_path = OUTPUT_ROOT / "p4_p5_repetition_runtime_ready_v1.json"
    if not ready_path.is_file():
        write_json(
            ready_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
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

    diagnostic_valid = decision is not None and failure is None
    decision_state: object = None
    if diagnostic_valid and decision is not None:
        decision_state = decision.get("decision_state")

    summary = {
        "schema_version": "1.0.0",
        "diagnostic_id": ("auragateway-p4-p5-cache-context-repetition-differential-v1"),
        "implementation_base_commit": REPETITION_IMPLEMENTATION_BASE_COMMIT,
        "design_record_sha256": REPETITION_DESIGN_RECORD_SHA256,
        "authorization": authorization,
        "status": ("DIAGNOSTIC_COMPLETE" if diagnostic_valid else "DIAGNOSTIC_INVALID"),
        "decision_state": decision_state,
        "variable_under_test": "CACHE_CONTEXT_REPETITION_COUNT",
        "control_repetition_count": REPETITION_CONTROL_COUNT,
        "treatment_repetition_count": REPETITION_TREATMENT_COUNT,
        "scheduled_request_count": 6,
        "completed_request_count": len(results),
        "scheduled_worker_starts": 6,
        "observed_worker_starts": counters["worker_starts"],
        "scheduled_model_loads": 6,
        "observed_model_loads": counters["model_loads"],
        "request_order": list(REPETITION_REQUEST_ORDER),
        "counters": counters,
        "worker_teardown_status": teardown_status,
        "scratch_cleanup_status": cleanup.get("status"),
        "failure_class": failure_class,
        "fresh_worker_process_per_observation": True,
        "cache_telemetry_is_diagnostic_only": True,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
        "credentials_used": False,
        "customer_data_present": False,
        "external_network_requests": 0,
        "hidden_retries": 0,
        "p5_requalified": False,
        "p6_requalified": False,
        "pilot_execution_performed": False,
        "measured_abc_execution_performed": False,
        "next_gate": ("PRESERVE_AND_DISPOSITION_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"),
    }
    write_json(
        OUTPUT_ROOT / "p4_p5_repetition_summary_v1.json",
        summary,
    )

    human = (
        "# AuraGateway P4/P5 Cache-Context Repetition Differential V1\n\n"
        f"- Status: {summary['status']}\n"
        f"- Decision: {summary['decision_state']}\n"
        f"- Completed requests: {len(results)} / 6\n"
        f"- Worker starts: {counters['worker_starts']} / 6\n"
        f"- Model loads: {counters['model_loads']} / 6\n"
        f"- Worker teardown: {teardown_status}\n"
        f"- Scratch cleanup: {cleanup.get('status')}\n"
        "- Variable under test: CACHE_CONTEXT_REPETITION_COUNT\n"
        "- Conditions: CONTROL_1X versus TREATMENT_24X\n"
        "- Fresh worker process per observation: true\n"
        "- Cache telemetry is diagnostic only.\n"
        "- Raw prompts retained: false\n"
        "- Raw model outputs retained: false\n"
        "- Hidden retries: 0\n"
        "- P5/P6 were not requalified by this diagnostic.\n"
        "- No measured A/B/C benchmark trajectory was executed.\n"
        "- Production readiness is not claimed.\n"
    )
    write_text(
        OUTPUT_ROOT / "human_report_v1.md",
        human,
    )

    try:
        bundle = repetition_bundle_outputs()
    except Exception as error:
        terminal = {
            **summary,
            "status": "DIAGNOSTIC_INVALID",
            "decision_state": None,
            "bundle_status": "FAILED",
            "bundle_error_type": type(error).__name__,
        }
        print(canonical_json(terminal))
        return 2

    terminal = {
        **summary,
        **bundle,
    }
    print(canonical_json(terminal))
    return 0 if diagnostic_valid else 2
"""


def _validate_predecessor_budget(source: str) -> dict[str, int]:
    budget = _literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    )
    required = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 3,
        "worker_starts": 3,
        "model_requests": 6,
    }
    if set(budget) != set(required):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_PREDECESSOR_BUDGET_DRIFT",
            "predecessor action budget keyset drifted",
            "ACTION_BUDGET_LIMITS",
        )
    for key, expected in required.items():
        if budget.get(key) != expected:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_PREDECESSOR_BUDGET_DRIFT",
                "predecessor action budget drifted",
                key,
            )
    return budget


def _function_segments(source: str) -> dict[str, str]:
    return {name: _segment(source, node) for name, node in _function_nodes(source).items()}


def _class_segments(source: str) -> dict[str, str]:
    return {name: _segment(source, node) for name, node in _class_nodes(source).items()}


def _validate_change_surface(
    predecessor: str,
    successor: str,
) -> int:
    predecessor_functions = _function_segments(predecessor)
    successor_functions = _function_segments(successor)

    expected_successor_names = set(predecessor_functions) | set(ADDED_FUNCTIONS)

    if set(successor_functions) != expected_successor_names:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
            "successor top-level function inventory drifted",
            RUNTIME_PATH.as_posix(),
        )

    changed: list[str] = []
    unchanged = 0

    for name, original in predecessor_functions.items():
        observed = successor_functions[name]

        if observed == original:
            unchanged += 1

        if observed != original:
            changed.append(name)

    if tuple(sorted(changed)) != tuple(sorted(CHANGED_EXISTING_FUNCTIONS)):
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
            "unexpected predecessor function changed",
            ",".join(sorted(changed)),
        )

    predecessor_classes = _class_segments(predecessor)
    successor_classes = _class_segments(successor)

    if predecessor_classes != successor_classes:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_CLASS_SURFACE_DRIFT",
            "predecessor class implementation drifted",
            RUNTIME_PATH.as_posix(),
        )

    return unchanged


def _validate_successor_contract(source: str) -> None:
    functions = _function_nodes(source)
    main_source = _segment(source, functions["main"])

    prohibited_main_markers = (
        "decide_p5(",
        "decide_p6(",
        "route_isolation(",
        "run_structured_request(",
        "run_attributed_request(",
        "worker_2",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
        "BASE_WARM",
        "NEGATIVE_PREFIX",
    )
    for marker in prohibited_main_markers:
        if marker in main_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_P5_P6_REACHABILITY_DRIFT",
                "successor main retained a prohibited predecessor trajectory seam",
                marker,
            )

    required_main_markers = (
        "REPETITION_REQUEST_ORDER",
        "run_fresh_worker_observation(",
        "decide_repetition_differential(",
        "cleanup_scratch()",
        '"model_loads": 6',
        '"worker_starts": 6',
        '"model_requests": 6',
    )
    for marker in required_main_markers:
        if marker not in main_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_MAIN_CONTRACT_DRIFT",
                "successor main is missing a required repetition seam",
                marker,
            )

    for helper_name in ADDED_FUNCTIONS:
        if helper_name not in functions:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
                "required repetition helper is missing",
                helper_name,
            )

    context_source = _segment(source, functions["repetition_context"])
    messages_source = _segment(source, functions["repetition_request_messages"])
    runner_source = _segment(source, functions["run_repetition_observation"])
    fresh_worker_source = _segment(source, functions["run_fresh_worker_observation"])
    decision_source = _segment(source, functions["decide_repetition_differential"])

    required_context_markers = (
        "REPETITION_CONTEXT_BODY * repetition_count + SYSTEM_PROMPT",
        "observed != SYNTHETIC_CACHE_CONTEXT_A",
    )
    for marker in required_context_markers:
        if marker not in context_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_MESSAGE_CONTRACT_DRIFT",
                "repetition context construction drifted",
                marker,
            )

    required_message_markers = (
        '"CONTROL_1X"',
        '"TREATMENT_24X"',
        '{"role": "system", "content": SYSTEM_PROMPT}',
        '{"role": "user", "content": repetition_context(repetition_count)}',
        '{"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK}',
        '{"role": "user", "content": EXPECTED_OBJECT_CANONICAL}',
    )
    for marker in required_message_markers:
        if marker not in messages_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_MESSAGE_CONTRACT_DRIFT",
                "frozen four-role composition drifted",
                marker,
            )

    runner_markers = (
        "persist_repetition_pre_request_identity(",
        "validate_zero_cache_baseline(worker)",
        'consume_actions(counters, "model_requests")',
        "REPETITION_TREATMENT_TOKEN_COUNT",
        "REPETITION_TREATMENT_TOKEN_SHA256",
        "REPETITION_TREATMENT_PAYLOAD_SHA256",
        '"valid_json": valid_json',
        '"exact_object": exact_object',
        '"raw_prompt_retained": False',
        '"raw_output_retained": False',
    )
    for marker in runner_markers:
        if marker not in runner_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_OBSERVATION_CONTRACT_DRIFT",
                "repetition observation contract drifted",
                marker,
            )
    if "validate_structured_response(" in runner_source:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_OBSERVATION_CONTRACT_DRIFT",
            "invalid JSON would still abort instead of remaining an observation",
            "validate_structured_response",
        )

    fresh_worker_markers = (
        "Worker(",
        "generation=sequence_index",
        "safe_worker_teardown(",
        "teardown_reports.append(teardown)",
        'teardown_status != "PASSED"',
    )
    for marker in fresh_worker_markers:
        if marker not in fresh_worker_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_STARTING_STATE_DRIFT",
                "fresh-worker observation lifecycle drifted",
                marker,
            )

    decision_markers = (
        '"LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"',
        '"REPETITION_NOT_NECESSARY"',
        '"REGRESSION_NOT_REPRODUCED"',
        '"CONTROL_NOT_RELIABLE"',
        '"NON_DETERMINISTIC_OR_AMBIGUOUS"',
        "worker_identity_cardinality",
        "treatment_historical_identity_matched",
    )
    for marker in decision_markers:
        if marker not in decision_source:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_DECISION_CONTRACT_DRIFT",
                "frozen decision contract drifted",
                marker,
            )

    budget = _literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    )
    expected_budget = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 6,
        "worker_starts": 6,
        "model_requests": 6,
    }
    if budget != expected_budget:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_SUCCESSOR_BUDGET_DRIFT",
            "successor action budget drifted",
            "ACTION_BUDGET_LIMITS",
        )


def build_runtime_payload(
    root: Path,
) -> tuple[bytes, int]:
    _validate_design(root)
    _validate_predecessor_contract(root)

    predecessor_bytes = _read_exact(
        root,
        PREDECESSOR_RUNTIME_PATH,
        PREDECESSOR_RUNTIME_SHA256,
    )
    predecessor = predecessor_bytes.decode("utf-8")

    budget = _validate_predecessor_budget(predecessor)
    successor_budget = dict(budget)
    successor_budget["model_loads"] = 6
    successor_budget["worker_starts"] = 6

    source = predecessor

    source = _replace_assignment(
        source,
        "NOTEBOOK_NAME",
        'NOTEBOOK_NAME: Final = "ag-p4-p5-repetition-diff-v1"',
    )
    source = _replace_assignment(
        source,
        "SOURCE_MAIN_COMMIT",
        f'SOURCE_MAIN_COMMIT: Final = "{BASE_MAIN_COMMIT}"',
    )
    source = _replace_assignment(
        source,
        "OUTPUT_ROOT",
        ('OUTPUT_ROOT: Final = WORK_ROOT / "p4_p5_cache_context_repetition_differential_v1"'),
    )
    source = _replace_assignment(
        source,
        "SCRATCH_ROOT",
        (
            "SCRATCH_ROOT: Final = WORK_ROOT / "
            '"p4_p5_cache_context_repetition_differential_v1_scratch"'
        ),
    )
    source = _replace_assignment(
        source,
        "EVIDENCE_ZIP",
        (
            "EVIDENCE_ZIP: Final = WORK_ROOT / "
            '"ag-p4-p5-cache-context-repetition-differential-evidence-v1.zip"'
        ),
    )
    source = _replace_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
        _render_int_dict_assignment(
            "ACTION_BUDGET_LIMITS",
            successor_budget,
        ),
    )
    source = _insert_before_function(
        source,
        "main",
        REPETITION_HELPERS,
    )
    source = _replace_function(
        source,
        "main",
        REPETITION_MAIN,
    )

    compile(
        source,
        RUNTIME_PATH.as_posix(),
        "exec",
    )

    unchanged = _validate_change_surface(
        predecessor,
        source,
    )
    _validate_successor_contract(source)

    return source.encode("utf-8"), unchanged


def _candidate_sha(root: Path, relative: Path) -> str:
    return _sha256(_read_required(root, relative))


def _build_expected(
    root: Path,
) -> tuple[bytes, bytes, bytes]:
    runtime_payload, unchanged_count = build_runtime_payload(root)

    review = ImplementationReview(
        review_id=(
            "auragateway-p4-p5-cache-context-repetition-differential-implementation-v1-review"
        ),
        status="APPROVED_STATIC_SUCCESSOR_IMPLEMENTATION",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        implementation_source_sha256=_candidate_sha(root, SOURCE_PATH),
        focused_test_sha256=_candidate_sha(root, TEST_PATH),
        runtime_payload_sha256=_sha256(runtime_payload),
        request_order=REQUEST_ORDER,
        treatment_expected_token_sha256=TREATMENT_EXPECTED_TOKEN_SHA256,
        treatment_expected_payload_sha256=TREATMENT_EXPECTED_PAYLOAD_SHA256,
        changed_existing_functions=CHANGED_EXISTING_FUNCTIONS,
        added_functions=ADDED_FUNCTIONS,
        unchanged_existing_function_count=unchanged_count,
        next_gate=NEXT_GATE,
    )
    review_bytes = _canonical_bytes(review.model_dump(mode="json"))

    record = ImplementationRecord(
        record_id=("auragateway-p4-p5-cache-context-repetition-differential-implementation-v1"),
        status="IMPLEMENTED_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_path=PREDECESSOR_RUNTIME_PATH.as_posix(),
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        successor_runtime_path=RUNTIME_PATH.as_posix(),
        successor_runtime_sha256=_sha256(runtime_payload),
        review_sha256=_sha256(review_bytes),
        next_gate=NEXT_GATE,
        non_claims=(
            "The 24x-vs-1x behavioral result has not been observed.",
            "Exactly 24 repetitions are not established as a causal threshold.",
            "Context length alone is not established as the root cause.",
            "Prefix caching itself is not established as defective.",
            "The assistant acknowledgement is not established as causal.",
            "The four-role topology is not established as causal.",
            "No Kaggle execution occurred in this implementation tranche.",
            "No GPU execution occurred in this implementation tranche.",
            "No model was loaded by this implementation producer.",
            "No model request was performed by this implementation producer.",
            "No live execution authorization was issued.",
            "The predecessor remediated runtime was not modified.",
            "P5 was not requalified.",
            "P6 was not requalified.",
            "No threshold search is authorized.",
            "No measured A/B/C execution is authorized.",
            "Production readiness is not established.",
        ),
    )
    return (
        runtime_payload,
        review_bytes,
        _canonical_bytes(record.model_dump(mode="json")),
    )


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

    if _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH)) != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "predecessor runtime changed during successor generation",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    return {
        "status": "P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_IMPLEMENTATION_GENERATED",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "predecessor_runtime_preserved": True,
        "fresh_worker_process_per_observation": True,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "model_requests_performed": 0,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)
    expected = (
        (RUNTIME_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    )
    for relative, payload in expected:
        observed = _read_required(root, relative)
        if observed != payload:
            raise ImplementationError(
                "P4_P5_REPETITION_IMPLEMENTATION_GENERATED_ARTIFACT_DRIFT",
                "generated successor implementation artifact drifted",
                relative.as_posix(),
            )

    if _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH)) != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "P4_P5_REPETITION_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "predecessor runtime identity drifted",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    return {
        "status": "P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_IMPLEMENTATION_VALID",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "predecessor_runtime_preserved": True,
        "fresh_worker_process_per_observation": True,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "model_requests_performed": 0,
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

        print(
            json.dumps(
                result,
                sort_keys=True,
            )
        )
        return 0

    except (
        ImplementationError,
        ValueError,
        SyntaxError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, ImplementationError):
            payload = error.envelope()

        if not isinstance(error, ImplementationError):
            payload = {
                "error_code": ("P4_P5_REPETITION_IMPLEMENTATION_VALIDATION_ERROR"),
                "safe_message": str(error),
                "path": None,
            }

        print(
            json.dumps(
                payload,
                sort_keys=True,
            ),
            file=__import__("sys").stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
