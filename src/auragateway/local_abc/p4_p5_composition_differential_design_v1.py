"""Freeze the P4/P5 composition differential design V1.

This module is design-only reliability infrastructure. It binds the accepted
historical P4 Case-A contract, the current P5/P6 composition, and the reconciled
C3 failure into one deterministic A/B differential. It does not execute Kaggle,
load a model, start a worker, issue a model request, or authorize execution.
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

BASE_MAIN_COMMIT: Final = "6ce990c44d8d9f3b96ad3b9b6e7e9479e5f24922"

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
P4_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p4_output_contract_diagnostic_v2_request.json"
)
P4_REQUEST_SHA256: Final = "b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1"
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

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_differential_design_v1.json"
)
NEXT_GATE: Final = "IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1"

MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
BACKEND: Final = "TRITON_ATTN"
FINAL_OBJECT_CANONICAL: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
REQUEST_ORDER: Final = ("A", "B", "B", "A", "A", "B")


class DesignError(RuntimeError):
    """Fail-closed composition differential design error."""

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
        raise DesignError("P4_P5_DIFF_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityScope(StrEnum):
    CURRENT = "CURRENT"
    HISTORICAL_PRECEDENT = "HISTORICAL_PRECEDENT"


class CaseId(StrEnum):
    A = "A"
    B = "B"


class DecisionState(StrEnum):
    COMPOSITION_REGRESSION_SUPPORTED = "COMPOSITION_REGRESSION_SUPPORTED"
    COMPOSITION_HYPOTHESIS_NOT_REPRODUCED = "COMPOSITION_HYPOTHESIS_NOT_REPRODUCED"
    SIMPLE_CONTROL_NOT_RELIABLE = "SIMPLE_CONTROL_NOT_RELIABLE"
    NON_DETERMINISTIC_OR_AMBIGUOUS = "NON_DETERMINISTIC_OR_AMBIGUOUS"


class AuthorityReceipt(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
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
    def validate_exact_controls(self) -> Self:
        if self.repetition_penalty != 1.1:
            raise ValueError("repetition penalty drifted")
        return self


class RuntimeIdentity(FrozenModel):
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
    worker_gpu_index: Literal[0]
    current_runtime_source_path: Literal[
        "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
    ]
    current_runtime_source_sha256: Literal[
        "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
    ]


class CaseDefinition(FrozenModel):
    case_id: CaseId
    name: str = Field(min_length=3)
    message_roles: tuple[Literal["system", "user", "assistant"], ...]
    system_prompt_source: Literal["CURRENT_P5_SYSTEM_PROMPT"]
    final_object_canonical: Literal['{"probe":"exact-runtime-p5-p6","value":1}']
    synthetic_cache_context_present: bool
    synthetic_assistant_ack_present: bool
    variable_under_test: Literal["MESSAGE_COMPOSITION_ONLY"]
    repetitions: Literal[3] = 3

    @model_validator(mode="after")
    def validate_case_shape(self) -> Self:
        if self.case_id == CaseId.A:
            if self.message_roles != ("system", "user"):
                raise ValueError("Case A message roles drifted")
            if self.synthetic_cache_context_present:
                raise ValueError("Case A cannot contain cache context")
            if self.synthetic_assistant_ack_present:
                raise ValueError("Case A cannot contain assistant acknowledgement")
        if self.case_id == CaseId.B:
            if self.message_roles != (
                "system",
                "user",
                "assistant",
                "user",
            ):
                raise ValueError("Case B message roles drifted")
            if not self.synthetic_cache_context_present:
                raise ValueError("Case B requires cache context")
            if not self.synthetic_assistant_ack_present:
                raise ValueError("Case B requires assistant acknowledgement")
        return self


class RequestPlanItem(FrozenModel):
    ordinal: int = Field(ge=1, le=6)
    case_id: CaseId


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[1] = 1
    maximum_worker_starts: Literal[1] = 1
    maximum_model_requests: Literal[6] = 6
    maximum_output_tokens_per_request: Literal[32] = 32
    hidden_retries_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class DiagnosticContract(FrozenModel):
    retained_fields: tuple[str, ...]
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        expected = (
            "case_id",
            "sequence_index",
            "http_status",
            "response_sha256",
            "response_length",
            "finish_reason",
            "completion_tokens",
            "valid_json",
            "exact_object",
            "json_error_line",
            "json_error_column",
            "json_error_position",
            "first_non_whitespace_class",
            "last_non_whitespace_class",
            "markdown_fence_detected",
        )
        if self.retained_fields != expected:
            raise ValueError("diagnostic field contract drifted")
        return self


class DecisionRule(FrozenModel):
    state: DecisionState
    condition: str = Field(min_length=20)
    implication: str = Field(min_length=20)


class DesignSafety(FrozenModel):
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    runtime_fix_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False


class DesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p4-p5-composition-differential-design-v1"]
    design_status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["6ce990c44d8d9f3b96ad3b9b6e7e9479e5f24922"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(
        min_length=6,
        max_length=6,
    )
    runtime: RuntimeIdentity
    generation_controls: GenerationControls
    cases: tuple[CaseDefinition, CaseDefinition]
    request_plan: tuple[
        RequestPlanItem,
        RequestPlanItem,
        RequestPlanItem,
        RequestPlanItem,
        RequestPlanItem,
        RequestPlanItem,
    ]
    execution_budget: ExecutionBudget
    diagnostics: DiagnosticContract
    decision_rules: tuple[DecisionRule, ...] = Field(
        min_length=4,
        max_length=4,
    )
    safety: DesignSafety
    next_gate: Literal["IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_design_shape(self) -> Self:
        if tuple(item.case_id for item in self.cases) != (
            CaseId.A,
            CaseId.B,
        ):
            raise ValueError("case order must be A then B")

        if tuple(item.ordinal for item in self.request_plan) != (
            1,
            2,
            3,
            4,
            5,
            6,
        ):
            raise ValueError("request ordinals must be exactly 1..6")

        if tuple(item.case_id.value for item in self.request_plan) != REQUEST_ORDER:
            raise ValueError("request order drifted")

        if tuple(rule.state for rule in self.decision_rules) != tuple(DecisionState):
            raise ValueError("decision rule order drifted")

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
            "P4_P5_DIFF_AUTHORITY_MISSING",
            "required differential authority is missing or unsafe",
            path.as_posix(),
        )

    payload = absolute.read_bytes()

    if _sha256_bytes(payload) != expected_sha256:
        raise DesignError(
            "P4_P5_DIFF_AUTHORITY_DRIFT",
            "required differential authority identity drifted",
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
            "P4_P5_DIFF_AUTHORITY_INVALID",
            "required differential authority is not valid JSON",
            path.as_posix(),
        ) from error

    if not isinstance(observed, dict):
        raise DesignError(
            "P4_P5_DIFF_AUTHORITY_INVALID",
            "required differential authority root is not one object",
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


def _find_dict_by_value(
    rows: object,
    key: str,
    expected_value: object,
) -> dict[str, object] | None:
    if not isinstance(rows, list):
        return None

    for row in rows:
        if isinstance(row, dict) and row.get(key) == expected_value:
            return cast(dict[str, object], row)

    return None


def validate_authorities(
    repo_root: Path,
) -> tuple[AuthorityReceipt, ...]:
    acceptance = _read_exact_object(
        repo_root,
        P4_ACCEPTANCE_PATH,
        P4_ACCEPTANCE_SHA256,
    )

    if (
        acceptance.get("status") != "P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_VALID"
        or acceptance.get("lifecycle_outcome") != "PASSED"
        or acceptance.get("selected_case_id") != "A"
        or acceptance.get("p4_output_contract_diagnostic_established") is not True
        or acceptance.get("runtime_execution_authorized") is not False
        or acceptance.get("measured_abc_execution_authorized") is not False
    ):
        raise DesignError(
            "P4_P5_DIFF_P4_ACCEPTANCE_DRIFT",
            "P4 acceptance no longer supports Case A as design precedent",
            P4_ACCEPTANCE_PATH.as_posix(),
        )

    implementation = _read_exact_object(
        repo_root,
        P4_IMPLEMENTATION_RECORD_PATH,
        P4_IMPLEMENTATION_RECORD_SHA256,
    )

    request_receipt = implementation.get("request")
    template_receipt = implementation.get("template")
    safety = implementation.get("safety")

    if not isinstance(request_receipt, dict):
        raise DesignError(
            "P4_P5_DIFF_P4_IMPLEMENTATION_DRIFT",
            "P4 request receipt is unavailable",
            P4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    if not isinstance(template_receipt, dict):
        raise DesignError(
            "P4_P5_DIFF_P4_IMPLEMENTATION_DRIFT",
            "P4 template receipt is unavailable",
            P4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    if not isinstance(safety, dict):
        raise DesignError(
            "P4_P5_DIFF_P4_IMPLEMENTATION_DRIFT",
            "P4 implementation safety boundary is unavailable",
            P4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    if (
        implementation.get("status") != "IMPLEMENTED_NOT_EXECUTED"
        or request_receipt.get("sha256") != P4_REQUEST_SHA256
        or template_receipt.get("sha256") != P4_TEMPLATE_SHA256
        or safety.get("runtime_execution_authorized") is not False
        or safety.get("model_requests_performed") != 0
    ):
        raise DesignError(
            "P4_P5_DIFF_P4_IMPLEMENTATION_DRIFT",
            "P4 implementation no longer binds accepted inputs",
            P4_IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    request = _read_exact_object(
        repo_root,
        P4_REQUEST_PATH,
        P4_REQUEST_SHA256,
    )

    case_a = _find_dict_by_value(
        request.get("cases"),
        "case_id",
        "A",
    )

    if case_a is None:
        raise DesignError(
            "P4_P5_DIFF_CASE_A_MISSING",
            "historical P4 Case A is missing",
            P4_REQUEST_PATH.as_posix(),
        )

    if (
        request.get("model_repository") != MODEL_REPOSITORY
        or request.get("model_revision") != MODEL_REVISION
        or request.get("model_snapshot_sha256") != MODEL_SNAPSHOT_SHA256
        or request.get("selected_backend") != BACKEND
        or case_a.get("output_mode") != "UNCONSTRAINED"
        or case_a.get("prompt_variant") != "V4"
        or case_a.get("repetition_penalty") != 1.1
        or case_a.get("repetitions") != 3
        or request.get("runtime_execution_authorized") is not False
    ):
        raise DesignError(
            "P4_P5_DIFF_CASE_A_DRIFT",
            "historical P4 Case A contract drifted",
            P4_REQUEST_PATH.as_posix(),
        )

    p4_template = _read_exact_bytes(
        repo_root,
        P4_TEMPLATE_PATH,
        P4_TEMPLATE_SHA256,
    )
    p4_text = p4_template.decode("utf-8")

    p4_markers = (
        '{"role": "system", "content": prompt}',
        '{"role": "user", "content": EXPECTED_OBJECT_CANONICAL}',
        '"temperature": 0',
        '"top_p": 1',
        '"seed": 7',
        '"max_tokens": 32',
    )

    if any(marker not in p4_text for marker in p4_markers):
        raise DesignError(
            "P4_P5_DIFF_P4_MESSAGE_SHAPE_DRIFT",
            "historical P4 message-shape precedent drifted",
            P4_TEMPLATE_PATH.as_posix(),
        )

    reconciliation = _read_exact_object(
        repo_root,
        C3_RECONCILIATION_PATH,
        C3_RECONCILIATION_SHA256,
    )

    p5_receipt = _find_dict_by_value(
        reconciliation.get("authorities"),
        "path",
        P5_RUNTIME_PATH.as_posix(),
    )

    if p5_receipt is None:
        raise DesignError(
            "P4_P5_DIFF_P5_AUTHORITY_MISSING",
            "reconciliation no longer binds the current P5 runtime",
            C3_RECONCILIATION_PATH.as_posix(),
        )

    if (
        reconciliation.get("status") != "RECONCILED_DIAGNOSTIC_INVALID_TRANSACTION"
        or reconciliation.get("primary_classification")
        != "P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION"
        or reconciliation.get("specific_classification")
        != "QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE"
        or reconciliation.get("material_message_context_change_established") is not True
        or reconciliation.get("current_composition_uses_v4_system_prompt") is not True
        or reconciliation.get("current_composition_uses_v5_derived_cache_context") is not True
        or reconciliation.get("new_execution_authorized") is not False
        or reconciliation.get("runtime_fix_authorized") is not False
        or p5_receipt.get("sha256") != P5_RUNTIME_SHA256
    ):
        raise DesignError(
            "P4_P5_DIFF_RECONCILIATION_DRIFT",
            "C3 reconciliation no longer supports this differential",
            C3_RECONCILIATION_PATH.as_posix(),
        )

    p5_runtime = _read_exact_bytes(
        repo_root,
        P5_RUNTIME_PATH,
        P5_RUNTIME_SHA256,
    )
    p5_text = p5_runtime.decode("utf-8")

    p5_markers = (
        "SYSTEM_PROMPT = (",
        "SYNTHETIC_CACHE_CONTEXT_A = (",
        "SYNTHETIC_ASSISTANT_ACK = ",
        'EXPECTED_OBJECT = {"probe": "exact-runtime-p5-p6", "value": 1}',
        '"temperature": 0',
        '"top_p": 1',
        '"seed": 7',
        '"max_tokens": 32',
    )

    if any(marker not in p5_text for marker in p5_markers):
        raise DesignError(
            "P4_P5_DIFF_P5_COMPOSITION_DRIFT",
            "current P5 composition or generation controls drifted",
            P5_RUNTIME_PATH.as_posix(),
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
            "historical_p4_case_matrix",
            P4_REQUEST_PATH,
            P4_REQUEST_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
        _authority(
            "historical_p4_message_shape",
            P4_TEMPLATE_PATH,
            P4_TEMPLATE_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
        _authority(
            "current_p5_runtime_composition",
            P5_RUNTIME_PATH,
            P5_RUNTIME_SHA256,
            AuthorityScope.CURRENT,
        ),
        _authority(
            "current_c3_reconciliation",
            C3_RECONCILIATION_PATH,
            C3_RECONCILIATION_SHA256,
            AuthorityScope.CURRENT,
        ),
    )


def _cases() -> tuple[CaseDefinition, CaseDefinition]:
    return (
        CaseDefinition(
            case_id=CaseId.A,
            name="SIMPLE_CONTROL",
            message_roles=("system", "user"),
            system_prompt_source="CURRENT_P5_SYSTEM_PROMPT",
            final_object_canonical=FINAL_OBJECT_CANONICAL,
            synthetic_cache_context_present=False,
            synthetic_assistant_ack_present=False,
            variable_under_test="MESSAGE_COMPOSITION_ONLY",
        ),
        CaseDefinition(
            case_id=CaseId.B,
            name="COMPOSED_P5",
            message_roles=(
                "system",
                "user",
                "assistant",
                "user",
            ),
            system_prompt_source="CURRENT_P5_SYSTEM_PROMPT",
            final_object_canonical=FINAL_OBJECT_CANONICAL,
            synthetic_cache_context_present=True,
            synthetic_assistant_ack_present=True,
            variable_under_test="MESSAGE_COMPOSITION_ONLY",
        ),
    )


def _request_plan() -> tuple[
    RequestPlanItem,
    RequestPlanItem,
    RequestPlanItem,
    RequestPlanItem,
    RequestPlanItem,
    RequestPlanItem,
]:
    return (
        RequestPlanItem(ordinal=1, case_id=CaseId.A),
        RequestPlanItem(ordinal=2, case_id=CaseId.B),
        RequestPlanItem(ordinal=3, case_id=CaseId.B),
        RequestPlanItem(ordinal=4, case_id=CaseId.A),
        RequestPlanItem(ordinal=5, case_id=CaseId.A),
        RequestPlanItem(ordinal=6, case_id=CaseId.B),
    )


def _diagnostics() -> DiagnosticContract:
    return DiagnosticContract(
        retained_fields=(
            "case_id",
            "sequence_index",
            "http_status",
            "response_sha256",
            "response_length",
            "finish_reason",
            "completion_tokens",
            "valid_json",
            "exact_object",
            "json_error_line",
            "json_error_column",
            "json_error_position",
            "first_non_whitespace_class",
            "last_non_whitespace_class",
            "markdown_fence_detected",
        )
    )


def _decision_rules() -> tuple[DecisionRule, ...]:
    return (
        DecisionRule(
            state=DecisionState.COMPOSITION_REGRESSION_SUPPORTED,
            condition=("Case A is 3/3 exact-object and Case B is 0/3 exact-object."),
            implication=(
                "The current message-composition seam is experimentally "
                "supported as the discriminating factor under the fixed "
                "runtime and generation controls."
            ),
        ),
        DecisionRule(
            state=(DecisionState.COMPOSITION_HYPOTHESIS_NOT_REPRODUCED),
            condition=("Case A is 3/3 exact-object and Case B is 3/3 exact-object."),
            implication=(
                "The prior C3 failure is not reproduced by the frozen "
                "composition contrast and no composition remediation is "
                "justified by this run."
            ),
        ),
        DecisionRule(
            state=DecisionState.SIMPLE_CONTROL_NOT_RELIABLE,
            condition=("Case A is not 3/3 exact-object regardless of the Case B outcome."),
            implication=(
                "The current runtime cannot establish a reliable simple "
                "control, so the composition seam cannot be assigned "
                "causal responsibility."
            ),
        ),
        DecisionRule(
            state=DecisionState.NON_DETERMINISTIC_OR_AMBIGUOUS,
            condition=("Any remaining mixed A/B result pattern is observed."),
            implication=(
                "The A/B differential is nondiscriminating or variable; "
                "stop and design a bounded Case C before any causal or "
                "remediation claim."
            ),
        ),
    )


def build_design_record(repo_root: Path) -> DesignRecord:
    authorities = validate_authorities(repo_root.resolve())

    return DesignRecord(
        record_id=("auragateway-p4-p5-composition-differential-design-v1"),
        design_status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=authorities,
        runtime=RuntimeIdentity(
            model_repository=MODEL_REPOSITORY,
            model_revision=MODEL_REVISION,
            model_snapshot_sha256=MODEL_SNAPSHOT_SHA256,
            backend=BACKEND,
            vllm_distribution="0.25.1+cu129",
            torch="2.11.0+cu129",
            torch_cuda="12.9",
            triton="3.6.0",
            transformers="5.14.1",
            platform_topology="T4_x2",
            worker_gpu_index=0,
            current_runtime_source_path=P5_RUNTIME_PATH.as_posix(),
            current_runtime_source_sha256=P5_RUNTIME_SHA256,
        ),
        generation_controls=GenerationControls(),
        cases=_cases(),
        request_plan=_request_plan(),
        execution_budget=ExecutionBudget(),
        diagnostics=_diagnostics(),
        decision_rules=_decision_rules(),
        safety=DesignSafety(),
        next_gate=NEXT_GATE,
        non_claims=(
            "This design does not execute Kaggle.",
            "This design does not authorize a new runtime execution.",
            ("This design does not establish that the composition hypothesis is true."),
            ("Historical P4 Case A is design precedent, not a current-runtime result."),
            ("The exact malformed output from saved version 341728154 remains unknown."),
            "P5 failure is not established because P5 was not reached.",
            "P6 failure is not established because P6 was not reached.",
            "A generic Qwen JSON reliability failure is not established.",
            "No runtime remediation is authorized by this design.",
            "Measured A/B/C execution is not authorized by this design.",
        ),
    )


def generate(repo_root: Path) -> DesignRecord:
    root = repo_root.resolve()
    record = build_design_record(root)
    target = root / RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_canonical_json_bytes(record.model_dump(mode="json")))
    return record


def validate_generated(repo_root: Path) -> DesignRecord:
    root = repo_root.resolve()
    expected = build_design_record(root)
    target = root / RECORD_PATH

    if not target.is_file() or target.is_symlink():
        raise DesignError(
            "P4_P5_DIFF_RECORD_MISSING",
            "generated composition differential record is missing or unsafe",
            RECORD_PATH.as_posix(),
        )

    expected_bytes = _canonical_json_bytes(expected.model_dump(mode="json"))

    if target.read_bytes() != expected_bytes:
        raise DesignError(
            "P4_P5_DIFF_RECORD_DRIFT",
            "generated composition differential record bytes drifted",
            RECORD_PATH.as_posix(),
        )

    observed = DesignRecord.model_validate_json(target.read_text(encoding="utf-8"))

    if observed != expected:
        raise DesignError(
            "P4_P5_DIFF_RECORD_SEMANTIC_DRIFT",
            "generated composition differential semantics drifted",
            RECORD_PATH.as_posix(),
        )

    return observed


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--repo-root",
            type=Path,
            required=True,
        )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()

        if arguments.command == "generate":
            record = generate(repo_root)

        elif arguments.command == "validate":
            record = validate_generated(repo_root)

        else:
            raise DesignError(
                "P4_P5_DIFF_COMMAND_UNSUPPORTED",
                f"unsupported command: {arguments.command}",
            )

        print(
            json.dumps(
                {
                    "status": record.design_status,
                    "runtime_execution_authorized": (record.safety.runtime_execution_authorized),
                    "new_execution_authorized": (record.safety.new_execution_authorized),
                    "model_requests_performed": (record.safety.model_requests_performed),
                    "next_gate": record.next_gate,
                },
                sort_keys=True,
            )
        )
        return 0

    except DesignError as error:
        print(json.dumps(error.envelope(), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
