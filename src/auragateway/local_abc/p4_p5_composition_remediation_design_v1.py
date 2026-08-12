"""Freeze the P4/P5 composition remediation design V1.

This module is design-only reliability infrastructure. It binds the accepted
P4 output-contract evidence, the current P5/P6 predecessor runtime, the
successful P4/P5 composition differential, and its terminalization
reconciliation into one deterministic remediation contract.

It does not modify the predecessor runtime, generate a successor runtime,
authorize execution, execute Kaggle, load a model, start a worker, or issue a
model request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "4ec7e612f601cda077053227ac8d829f98d08feb"

P4_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_acceptance_v1.json"
)
P4_ACCEPTANCE_SHA256: Final = "21290fc0aaccb53dccfaba728db50fe412af81fda945d41d413a5b13b10537db"
P4_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_v2_record.json"
)
P4_IMPLEMENTATION_RECORD_SHA256: Final = (
    "9fbefc001af0a56995f903681c6afe251a2ce594fd21d760a26ee7783352f5c1"
)
P4_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"
)
P4_TEMPLATE_SHA256: Final = "93bdcf4a2ab3f4b4a07b688b8d6f9dc295ba3edcbb0b9bd63da8967393811441"
P5_RUNTIME_PATH: Final = Path("src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py")
P5_RUNTIME_SHA256: Final = "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
C3_RECONCILIATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_transaction_bound_c3_failure_reconciliation_v1.json"
)
C3_RECONCILIATION_SHA256: Final = "21c92d4b8adaa7157a9a4f24ff2cb9fa08c5c154224889e36d88e5e41444dbbc"
DIFFERENTIAL_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_differential_design_v1.json"
)
DIFFERENTIAL_DESIGN_SHA256: Final = (
    "5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1"
)
DIFFERENTIAL_IMPLEMENTATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_differential_implementation_v1.json"
)
DIFFERENTIAL_IMPLEMENTATION_SHA256: Final = (
    "8b2b11f367b60272323cb9e6269cbb09e597063d03467207798c96b25e79b1b1"
)
DIFFERENTIAL_RECONCILIATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_differential_"
    "terminalization_reconciliation_v1.json"
)
DIFFERENTIAL_RECONCILIATION_SHA256: Final = (
    "c0aac246a4d05afc2a4742d51c2dce557bb7c07e3efa298b674bc34611887d82"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_design_v1.json"
)
NEXT_GATE: Final = "IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"

V4_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
V5_INSTRUCTION: Final = (
    "For structured probes, return only the exact JSON object supplied in the final user message."
)
FINAL_OBJECT_CANONICAL: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
CURRENT_MESSAGE_ROLES: Final = ("system", "user", "assistant", "user")
FULL_RUNTIME_REQUEST_ROLES: Final = (
    "BASE_COLD",
    "BASE_WARM",
    "NEGATIVE_PREFIX",
    "POST_RESET_COLD",
    "CROSS_WORKER_COLD",
    "WORKER1_RETENTION",
)
PRE_REQUEST_EVIDENCE_FIELDS: Final = (
    "request_ordinal",
    "request_role",
    "prefix_variant",
    "token_count",
    "token_sha256",
    "token_ids",
    "payload_sha256",
    "persisted_before_model_request",
)
FUTURE_PLATFORM_FIELDS: Final = (
    "transaction_id",
    "platform_observed_at",
    "accelerator",
    "allocated_gpu_count",
    "internet_enabled",
    "capability_source",
)


class DesignError(RuntimeError):
    """Fail-closed P4/P5 composition remediation design error."""

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
        raise DesignError("P4_P5_REMEDIATION_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityScope(StrEnum):
    CURRENT = "CURRENT"
    HISTORICAL_PRECEDENT = "HISTORICAL_PRECEDENT"
    CONTROLLED_EXPERIMENT = "CONTROLLED_EXPERIMENT"


class InterventionId(StrEnum):
    REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION = (
        "REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION"
    )


class AuthorityReceipt(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: AuthorityScope


class RuntimeIdentity(FrozenModel):
    predecessor_runtime_path: Literal[
        "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
    ]
    predecessor_runtime_sha256: Literal[
        "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
    ]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
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
    prefix_caching_enabled: Literal[True] = True
    cache_block_size: Literal[16] = 16


class InterventionContract(FrozenModel):
    intervention_id: InterventionId
    target_constants: tuple[
        Literal["SYNTHETIC_CACHE_CONTEXT_A"],
        Literal["SYNTHETIC_CACHE_CONTEXT_B"],
    ]
    replacement_scope: Literal["CACHE_CONTEXT_INSTRUCTION_TAIL_ONLY"]
    before_instruction: Literal[
        "For structured probes, return only the exact JSON object supplied in "
        "the final user message."
    ]
    after_instruction: Literal[
        "Return only the exact JSON object supplied in the final user message, "
        "with no markdown or additional text."
    ]
    expected_predecessor_occurrences: Literal[2] = 2
    expected_successor_occurrences_of_before: Literal[0] = 0
    expected_successor_occurrences_of_after_in_cache_contexts: Literal[2] = 2


class CompositionInvariants(FrozenModel):
    message_roles: tuple[
        Literal["system"],
        Literal["user"],
        Literal["assistant"],
        Literal["user"],
    ]
    synthetic_assistant_ack: Literal["Synthetic deterministic context acknowledged."]
    synthetic_assistant_ack_preserved: Literal[True] = True
    cache_context_repetition_count: Literal[24] = 24
    prefix_variants_preserved: tuple[Literal["A"], Literal["B"]]
    final_object_canonical: Literal['{"probe":"exact-runtime-p5-p6","value":1}']
    system_prompt_remains_v4: Literal[True] = True
    long_cache_context_preserved: Literal[True] = True
    prefix_caching_preserved: Literal[True] = True
    cache_block_size_preserved: Literal[16] = 16
    request_order_semantics_preserved: Literal[True] = True
    p5_decision_semantics_preserved: Literal[True] = True
    p6_decision_semantics_preserved: Literal[True] = True


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
    def validate_exact_controls(self) -> Self:
        if self.repetition_penalty != 1.1:
            raise ValueError("repetition penalty drifted")
        return self


class PreRequestEvidenceControl(FrozenModel):
    artifact_name: Literal["pre_request_token_identity_journal_v1.json"]
    retained_fields: tuple[str, ...]
    persist_after_tokenization: Literal[True] = True
    persist_before_metric_snapshot: Literal[True] = True
    persist_before_model_request_budget_consumption: Literal[True] = True
    persist_before_chat_completion_request: Literal[True] = True
    atomic_write_required: Literal[True] = True
    raw_prompt_retained: Literal[False] = False
    raw_model_output_retained: Literal[False] = False
    payload_hash_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        if self.retained_fields != PRE_REQUEST_EVIDENCE_FIELDS:
            raise ValueError("pre-request evidence field contract drifted")
        return self


class FullRuntimeAcceptance(FrozenModel):
    request_roles: tuple[
        Literal["BASE_COLD"],
        Literal["BASE_WARM"],
        Literal["NEGATIVE_PREFIX"],
        Literal["POST_RESET_COLD"],
        Literal["CROSS_WORKER_COLD"],
        Literal["WORKER1_RETENTION"],
    ]
    maximum_model_requests: Literal[6] = 6
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    hidden_retries_permitted: Literal[0] = 0
    exact_structured_output_required_for_all_requests: Literal[True] = True
    p5_required_state: Literal["PASS"]
    p6_required_state: Literal["PASS"]
    teardown_required_state: Literal["PASSED"]
    scratch_cleanup_required_state: Literal["PASSED"]
    prefix_a_token_identity_stable_across_controls: Literal[True] = True
    negative_prefix_token_identity_must_diverge: Literal[True] = True
    warm_cache_reuse_required: Literal[True] = True
    reset_cold_state_required: Literal[True] = True
    cross_worker_cold_state_required: Literal[True] = True
    worker_1_retention_required: Literal[True] = True


class FutureAuthorizationControl(FrozenModel):
    control_id: Literal["PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"]
    deferred_to_authorization_tranche: Literal[True] = True
    required_fields: tuple[str, ...]
    must_bind_transaction_id: Literal[True] = True
    must_be_persisted_before_save_and_run_all: Literal[True] = True
    console_only_observation_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        if self.required_fields != FUTURE_PLATFORM_FIELDS:
            raise ValueError("future platform observation field contract drifted")
        return self


class DesignSafety(FrozenModel):
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    remediation_implemented: Literal[False] = False
    successor_runtime_generated: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    case_c_authorized: Literal[False] = False


class DesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p4-p5-composition-remediation-design-v1"]
    design_status: Literal["DESIGN_FROZEN_NOT_IMPLEMENTED"]
    base_main_commit: Literal["4ec7e612f601cda077053227ac8d829f98d08feb"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(
        min_length=8,
        max_length=8,
    )
    runtime: RuntimeIdentity
    intervention: InterventionContract
    composition_invariants: CompositionInvariants
    generation_controls: GenerationControls
    pre_request_evidence_control: PreRequestEvidenceControl
    full_runtime_acceptance: FullRuntimeAcceptance
    future_authorization_control: FutureAuthorizationControl
    non_interventions: tuple[str, ...] = Field(min_length=10)
    safety: DesignSafety
    next_gate: Literal["IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_design_shape(self) -> Self:
        if self.composition_invariants.message_roles != CURRENT_MESSAGE_ROLES:
            raise ValueError("message-role invariant drifted")

        if self.composition_invariants.prefix_variants_preserved != ("A", "B"):
            raise ValueError("prefix-variant invariant drifted")

        if self.full_runtime_acceptance.request_roles != FULL_RUNTIME_REQUEST_ROLES:
            raise ValueError("full-runtime request-role contract drifted")

        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _read_exact_bytes(
    repo_root: Path,
    path: Path,
    expected_sha256: str,
) -> bytes:
    absolute = repo_root / path

    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "P4_P5_REMEDIATION_AUTHORITY_MISSING",
            "required remediation authority is missing or unsafe",
            path.as_posix(),
        )

    payload = absolute.read_bytes()

    if _sha256_bytes(payload) != expected_sha256:
        raise DesignError(
            "P4_P5_REMEDIATION_AUTHORITY_DRIFT",
            "required remediation authority identity drifted",
            path.as_posix(),
        )

    return payload


def _read_exact_object(
    repo_root: Path,
    path: Path,
    expected_sha256: str,
) -> dict[str, object]:
    payload = _read_exact_bytes(
        repo_root,
        path,
        expected_sha256,
    )

    try:
        observed: object = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DesignError(
            "P4_P5_REMEDIATION_AUTHORITY_INVALID",
            "required remediation authority is not valid JSON",
            path.as_posix(),
        ) from error

    if not isinstance(observed, dict):
        raise DesignError(
            "P4_P5_REMEDIATION_AUTHORITY_INVALID",
            "required remediation authority root is not one object",
            path.as_posix(),
        )

    return cast(dict[str, object], observed)


def _authority(
    role: str,
    path: Path,
    sha256: str,
    scope: AuthorityScope,
) -> AuthorityReceipt:
    return AuthorityReceipt(
        role=role,
        path=path.as_posix(),
        sha256=sha256,
        scope=scope,
    )


def _find_dict_by_path(
    rows: object,
    expected_path: str,
) -> dict[str, object] | None:
    if not isinstance(rows, list):
        return None

    for row in rows:
        if isinstance(row, dict) and row.get("path") == expected_path:
            return cast(dict[str, object], row)

    return None


def validate_authorities(
    repo_root: Path,
) -> tuple[AuthorityReceipt, ...]:
    p4_acceptance = _read_exact_object(
        repo_root,
        P4_ACCEPTANCE_PATH,
        P4_ACCEPTANCE_SHA256,
    )

    request_results = _find_dict_by_path(
        p4_acceptance.get("evidence"),
        (
            "evidence_vault/local_abc/p4-output-contract-diagnostic-pass-v2/"
            "request_results_v2-340775383.json"
        ),
    )

    if request_results is None:
        raise DesignError(
            "P4_P5_REMEDIATION_P4_EVIDENCE_MISSING",
            "historical P4 request-result evidence receipt is missing",
            P4_ACCEPTANCE_PATH.as_posix(),
        )

    if (
        p4_acceptance.get("status")
        != "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_VALID"
        or p4_acceptance.get("lifecycle_outcome") != "PASSED"
        or p4_acceptance.get("selected_case_id") != "A"
        or p4_acceptance.get("p4_output_contract_diagnostic_established") is not True
        or p4_acceptance.get("eligible_case_ids") != ["A", "C", "E", "F"]
        or p4_acceptance.get("ineligible_case_ids") != ["B", "D"]
        or request_results.get("sha256")
        != "03dfdce769369070e97857d2ddd2e5313deeddeb4b0b14cec1c59552bacca82f"
        or p4_acceptance.get("runtime_execution_authorized") is not False
        or p4_acceptance.get("measured_abc_execution_authorized") is not False
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_P4_ACCEPTANCE_DRIFT",
            "historical P4 acceptance no longer supports the remediation premise",
            P4_ACCEPTANCE_PATH.as_posix(),
        )

    p4_record = _read_exact_object(
        repo_root,
        P4_IMPLEMENTATION_RECORD_PATH,
        P4_IMPLEMENTATION_RECORD_SHA256,
    )

    request_receipt = p4_record.get("request")
    template_receipt = p4_record.get("template")

    if not isinstance(request_receipt, dict) or not isinstance(
        template_receipt,
        dict,
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_P4_IMPLEMENTATION_DRIFT",
            "historical P4 implementation receipts are unavailable",
            P4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    if (
        p4_record.get("status") != "IMPLEMENTED_NOT_EXECUTED"
        or request_receipt.get("sha256")
        != "b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1"
        or template_receipt.get("sha256") != P4_TEMPLATE_SHA256
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_P4_IMPLEMENTATION_DRIFT",
            "historical P4 implementation no longer binds the accepted matrix",
            P4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    p4_template = _read_exact_bytes(
        repo_root,
        P4_TEMPLATE_PATH,
        P4_TEMPLATE_SHA256,
    ).decode("utf-8")

    required_p4_markers = (
        "V4_PROMPT = (",
        '"Return only the exact JSON object supplied in the final user message, "',
        '"with no markdown or additional text."',
        "V5_PROMPT = (",
        '"For structured probes, return only the exact JSON object supplied in "',
        '"the final user message."',
        '"A": {"prompt_variant": "V4", "repetition_penalty": 1.1, "schema": False}',
        '"B": {"prompt_variant": "V5", "repetition_penalty": 1.1, "schema": False}',
        '"C": {"prompt_variant": "V4", "repetition_penalty": 1.0, "schema": False}',
        '"D": {"prompt_variant": "V5", "repetition_penalty": 1.0, "schema": False}',
        '"E": {"prompt_variant": "V4", "repetition_penalty": 1.0, "schema": True}',
        '"F": {"prompt_variant": "V5", "repetition_penalty": 1.0, "schema": True}',
    )

    if any(marker not in p4_template for marker in required_p4_markers):
        raise DesignError(
            "P4_P5_REMEDIATION_P4_MATRIX_DRIFT",
            "historical P4 V4/V5 matrix markers drifted",
            P4_TEMPLATE_PATH.as_posix(),
        )

    c3_reconciliation = _read_exact_object(
        repo_root,
        C3_RECONCILIATION_PATH,
        C3_RECONCILIATION_SHA256,
    )

    if (
        c3_reconciliation.get("status") != "RECONCILED_DIAGNOSTIC_INVALID_TRANSACTION"
        or c3_reconciliation.get("primary_classification")
        != "P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION"
        or c3_reconciliation.get("specific_classification")
        != "QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE"
        or c3_reconciliation.get("current_composition_uses_v4_system_prompt") is not True
        or c3_reconciliation.get("current_composition_uses_v5_derived_cache_context") is not True
        or c3_reconciliation.get("historical_v5_specific_classification")
        != "V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"
        or c3_reconciliation.get("new_execution_authorized") is not False
        or c3_reconciliation.get("runtime_fix_authorized") is not False
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_DRIFT",
            "C3 reconciliation no longer supports the remediation premise",
            C3_RECONCILIATION_PATH.as_posix(),
        )

    p5_runtime = _read_exact_bytes(
        repo_root,
        P5_RUNTIME_PATH,
        P5_RUNTIME_SHA256,
    ).decode("utf-8")

    if p5_runtime.count(V5_INSTRUCTION) != 2:
        raise DesignError(
            "P4_P5_REMEDIATION_V5_OCCURRENCE_DRIFT",
            "predecessor runtime no longer has exactly two V5 cache-context tails",
            P5_RUNTIME_PATH.as_posix(),
        )

    required_p5_markers = (
        "SYSTEM_PROMPT = (",
        "SYNTHETIC_CACHE_CONTEXT_A = (",
        "SYNTHETIC_CACHE_CONTEXT_B = (",
        f'SYNTHETIC_ASSISTANT_ACK = "{ASSISTANT_ACK}"',
        "CACHE_BLOCK_SIZE = 16",
        '"--enable-prefix-caching"',
        "def request_messages(prefix_variant: str) -> list[dict[str, str]]:",
        '{"role": "system", "content": SYSTEM_PROMPT}',
        '{"role": "user", "content": _prefix_context(prefix_variant)}',
        '{"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK}',
        '{"role": "user", "content": EXPECTED_OBJECT_CANONICAL}',
        "def tokenize_request(",
        "def decide_p5(",
        "def decide_p6(",
    )

    if any(marker not in p5_runtime for marker in required_p5_markers):
        raise DesignError(
            "P4_P5_REMEDIATION_PREDECESSOR_DRIFT",
            "predecessor P5/P6 composition or cache semantics drifted",
            P5_RUNTIME_PATH.as_posix(),
        )

    differential_design = _read_exact_object(
        repo_root,
        DIFFERENTIAL_DESIGN_PATH,
        DIFFERENTIAL_DESIGN_SHA256,
    )

    cases = differential_design.get("cases")

    if not isinstance(cases, list) or len(cases) != 2:
        raise DesignError(
            "P4_P5_REMEDIATION_DIFFERENTIAL_DESIGN_DRIFT",
            "accepted differential case contract is unavailable",
            DIFFERENTIAL_DESIGN_PATH.as_posix(),
        )

    case_a = cases[0]
    case_b = cases[1]

    if not isinstance(case_a, dict) or not isinstance(case_b, dict):
        raise DesignError(
            "P4_P5_REMEDIATION_DIFFERENTIAL_DESIGN_DRIFT",
            "accepted differential cases are invalid",
            DIFFERENTIAL_DESIGN_PATH.as_posix(),
        )

    if (
        case_a.get("name") != "SIMPLE_CONTROL"
        or case_a.get("message_roles") != ["system", "user"]
        or case_b.get("name") != "COMPOSED_P5"
        or case_b.get("message_roles") != ["system", "user", "assistant", "user"]
        or case_b.get("synthetic_cache_context_present") is not True
        or case_b.get("synthetic_assistant_ack_present") is not True
        or case_a.get("variable_under_test") != "MESSAGE_COMPOSITION_ONLY"
        or case_b.get("variable_under_test") != "MESSAGE_COMPOSITION_ONLY"
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_DIFFERENTIAL_DESIGN_DRIFT",
            "accepted differential no longer binds the intended composition contrast",
            DIFFERENTIAL_DESIGN_PATH.as_posix(),
        )

    differential_implementation = _read_exact_object(
        repo_root,
        DIFFERENTIAL_IMPLEMENTATION_PATH,
        DIFFERENTIAL_IMPLEMENTATION_SHA256,
    )

    if (
        differential_implementation.get("status") != "IMPLEMENTED_NOT_EXECUTED"
        or differential_implementation.get("predecessor_runtime_sha256") != P5_RUNTIME_SHA256
        or differential_implementation.get("successor_runtime_sha256")
        != "4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7"
        or differential_implementation.get("new_execution_authorized") is not False
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_DIFFERENTIAL_IMPLEMENTATION_DRIFT",
            "accepted differential implementation authority drifted",
            DIFFERENTIAL_IMPLEMENTATION_PATH.as_posix(),
        )

    differential_reconciliation = _read_exact_object(
        repo_root,
        DIFFERENTIAL_RECONCILIATION_PATH,
        DIFFERENTIAL_RECONCILIATION_SHA256,
    )

    if (
        differential_reconciliation.get("status")
        != ("RECONCILED_EXECUTED_SINGLE_USE_AUTHORITY_WITH_TERMINALIZATION_PROVENANCE_GAP")
        or differential_reconciliation.get("diagnostic_decision")
        != "COMPOSITION_REGRESSION_SUPPORTED"
        or differential_reconciliation.get("case_a_exact_successes") != 3
        or differential_reconciliation.get("case_b_exact_successes") != 0
        or differential_reconciliation.get("controlled_differential_evidence_established")
        is not True
        or differential_reconciliation.get("scientific_result_valid") is not True
        or differential_reconciliation.get("diagnostic_result_invalidated") is not False
        or differential_reconciliation.get("authorization_reuse_permitted") is not False
        or differential_reconciliation.get("new_execution_authorized") is not False
        or differential_reconciliation.get("runtime_remediation_authorized") is not False
        or differential_reconciliation.get("next_gate")
        != "DESIGN_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"
    ):
        raise DesignError(
            "P4_P5_REMEDIATION_DIFFERENTIAL_RESULT_DRIFT",
            "accepted A/B result no longer supports remediation design",
            DIFFERENTIAL_RECONCILIATION_PATH.as_posix(),
        )

    return (
        _authority(
            "historical_p4_execution_acceptance",
            P4_ACCEPTANCE_PATH,
            P4_ACCEPTANCE_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
        _authority(
            "historical_p4_implementation_record",
            P4_IMPLEMENTATION_RECORD_PATH,
            P4_IMPLEMENTATION_RECORD_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
        _authority(
            "historical_p4_v4_v5_message_matrix",
            P4_TEMPLATE_PATH,
            P4_TEMPLATE_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
        _authority(
            "current_p5_p6_predecessor_runtime",
            P5_RUNTIME_PATH,
            P5_RUNTIME_SHA256,
            AuthorityScope.CURRENT,
        ),
        _authority(
            "current_c3_failure_reconciliation",
            C3_RECONCILIATION_PATH,
            C3_RECONCILIATION_SHA256,
            AuthorityScope.CURRENT,
        ),
        _authority(
            "controlled_composition_differential_design",
            DIFFERENTIAL_DESIGN_PATH,
            DIFFERENTIAL_DESIGN_SHA256,
            AuthorityScope.CONTROLLED_EXPERIMENT,
        ),
        _authority(
            "controlled_composition_differential_implementation",
            DIFFERENTIAL_IMPLEMENTATION_PATH,
            DIFFERENTIAL_IMPLEMENTATION_SHA256,
            AuthorityScope.CONTROLLED_EXPERIMENT,
        ),
        _authority(
            "accepted_composition_differential_result",
            DIFFERENTIAL_RECONCILIATION_PATH,
            DIFFERENTIAL_RECONCILIATION_SHA256,
            AuthorityScope.CONTROLLED_EXPERIMENT,
        ),
    )


def build_design_record(
    repo_root: Path,
) -> DesignRecord:
    authorities = validate_authorities(repo_root)

    return DesignRecord(
        record_id="auragateway-p4-p5-composition-remediation-design-v1",
        design_status="DESIGN_FROZEN_NOT_IMPLEMENTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=authorities,
        runtime=RuntimeIdentity(
            predecessor_runtime_path=P5_RUNTIME_PATH.as_posix(),
            predecessor_runtime_sha256=P5_RUNTIME_SHA256,
            model_repository="Qwen/Qwen2.5-0.5B-Instruct",
            model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
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
        ),
        intervention=InterventionContract(
            intervention_id=(
                InterventionId.REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION
            ),
            target_constants=(
                "SYNTHETIC_CACHE_CONTEXT_A",
                "SYNTHETIC_CACHE_CONTEXT_B",
            ),
            replacement_scope="CACHE_CONTEXT_INSTRUCTION_TAIL_ONLY",
            before_instruction=V5_INSTRUCTION,
            after_instruction=V4_INSTRUCTION,
        ),
        composition_invariants=CompositionInvariants(
            message_roles=CURRENT_MESSAGE_ROLES,
            synthetic_assistant_ack=ASSISTANT_ACK,
            prefix_variants_preserved=("A", "B"),
            final_object_canonical=FINAL_OBJECT_CANONICAL,
        ),
        generation_controls=GenerationControls(),
        pre_request_evidence_control=PreRequestEvidenceControl(
            artifact_name="pre_request_token_identity_journal_v1.json",
            retained_fields=PRE_REQUEST_EVIDENCE_FIELDS,
        ),
        full_runtime_acceptance=FullRuntimeAcceptance(
            request_roles=FULL_RUNTIME_REQUEST_ROLES,
            p5_required_state="PASS",
            p6_required_state="PASS",
            teardown_required_state="PASSED",
            scratch_cleanup_required_state="PASSED",
        ),
        future_authorization_control=FutureAuthorizationControl(
            control_id="PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL",
            required_fields=FUTURE_PLATFORM_FIELDS,
        ),
        non_interventions=(
            "Do not remove the synthetic assistant acknowledgement.",
            "Do not change message-role order.",
            "Do not shorten either synthetic cache-context body.",
            "Do not change the 24x cache-context repetition count.",
            "Do not change the final canonical object.",
            "Do not change temperature, top_p, seed, max_tokens, or repetition penalty.",
            "Do not introduce response_format, guided decoding, or JSON-schema decoding.",
            "Do not relax structured-output validation or parser semantics.",
            "Do not add hidden retries or replacement requests.",
            "Do not change the model, revision, tokenizer, CUDA, torch, Triton, or vLLM.",
            "Do not change prefix-cache enablement, block size, or P5 cache metrics.",
            "Do not change P6 route, worker, process, GPU, or state-isolation semantics.",
            "Do not mutate accepted historical evidence or the predecessor runtime.",
            "Do not opportunistically repair stale predecessor metadata in this tranche.",
        ),
        safety=DesignSafety(),
        next_gate=NEXT_GATE,
        non_claims=(
            "This design does not implement the remediation.",
            "This design does not generate a remediated successor runtime.",
            "This design does not authorize runtime execution.",
            "This design does not execute Kaggle.",
            "This design does not load a model or start a worker.",
            "This design does not perform a model request.",
            "This design does not claim the V5 cache-context tail is the sole current cause.",
            (
                "The current A/B differential establishes the composed bundle as "
                "discriminating, not each subcomponent independently."
            ),
            (
                "Historical V5 evidence makes the V5 tail the evidence-backed first "
                "intervention, not unique causal proof."
            ),
            "This design does not claim P5 or P6 remediation success.",
            "This design does not authorize Case C.",
            "This design does not authorize an unchanged replay of prior transactions.",
            (
                "Future execution requires a separately merged execution-authorization "
                "design and fresh human authorization."
            ),
            "Production readiness is not established.",
        ),
    )


def generate(
    repo_root: Path,
) -> DesignRecord:
    record = build_design_record(repo_root)
    output = repo_root / RECORD_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        _canonical_json_bytes(
            record.model_dump(mode="json"),
        )
    )
    return record


def validate_generated(
    repo_root: Path,
) -> DesignRecord:
    expected = build_design_record(repo_root)
    output = repo_root / RECORD_PATH

    if not output.is_file() or output.is_symlink():
        raise DesignError(
            "P4_P5_REMEDIATION_RECORD_MISSING",
            "generated remediation design record is missing or unsafe",
            RECORD_PATH.as_posix(),
        )

    expected_bytes = _canonical_json_bytes(
        expected.model_dump(mode="json"),
    )
    observed_bytes = output.read_bytes()

    if observed_bytes != expected_bytes:
        raise DesignError(
            "P4_P5_REMEDIATION_RECORD_DRIFT",
            "generated remediation design record drifted",
            RECORD_PATH.as_posix(),
        )

    return expected


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser(
        description="Freeze or validate the P4/P5 composition remediation design V1."
    )
    parser.add_argument(
        "action",
        choices=("generate", "validate"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    try:
        record = generate(repo_root) if args.action == "generate" else validate_generated(repo_root)
    except DesignError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "status": record.design_status,
                "record_id": record.record_id,
                "record_sha256": _sha256_bytes(
                    _canonical_json_bytes(
                        record.model_dump(mode="json"),
                    )
                ),
                "runtime_execution_authorized": (record.safety.runtime_execution_authorized),
                "remediation_implemented": record.safety.remediation_implemented,
                "next_gate": record.next_gate,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
