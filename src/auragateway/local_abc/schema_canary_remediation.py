"""Canonical rendered-token extraction and schema-canary rerun authorization."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from numbers import Integral
from pathlib import Path
from typing import Any, Literal, Protocol, Self, TypeGuard, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_EXPECTED_LOCAL_EVIDENCE_FILENAME = (
    "auragateway-schema-constrained-quality-cache-canary-evidence-v1 (1).zip"
)
_EXPECTED_CASE_IDS: tuple[
    Literal["incident-severity"],
    Literal["payment-reconciliation"],
    Literal["data-sharing-policy"],
] = (
    "incident-severity",
    "payment-reconciliation",
    "data-sharing-policy",
)
_EXPECTED_QUALITY_CHECKS: tuple[
    Literal["json_parse_success"],
    Literal["exact_key_set_match"],
    Literal["exact_answer_match"],
    Literal["exact_case_id_match"],
    Literal["exact_turn_index_match"],
    Literal["exact_confidence_match"],
    Literal["no_extra_text"],
] = (
    "json_parse_success",
    "exact_key_set_match",
    "exact_answer_match",
    "exact_case_id_match",
    "exact_turn_index_match",
    "exact_confidence_match",
    "no_extra_text",
)


def _token_counts_contradict(*, planned: int, observed: int) -> bool:
    """Return whether planned and observed prompt-token counts disagree."""

    return planned != observed


class RenderedTokenNormalizationFailureCode(StrEnum):
    """Machine-readable failures for canonical token extraction."""

    RENDERED_TEXT_INVALID = "RENDERED_TEXT_INVALID"
    INPUT_IDS_MISSING = "INPUT_IDS_MISSING"
    INPUT_IDS_EMPTY = "INPUT_IDS_EMPTY"
    INPUT_IDS_AMBIGUOUS_BATCH = "INPUT_IDS_AMBIGUOUS_BATCH"
    INPUT_ID_INVALID = "INPUT_ID_INVALID"
    TOKENIZED_OUTPUT_UNSUPPORTED = "TOKENIZED_OUTPUT_UNSUPPORTED"


class SchemaCanaryV1DefectCode(StrEnum):
    """Root cause frozen from the failed schema-cache canary."""

    CHAT_TEMPLATE_TOKEN_CONTAINER_COUNTED_AS_TOKEN_SEQUENCE = (
        "CHAT_TEMPLATE_TOKEN_CONTAINER_COUNTED_AS_TOKEN_SEQUENCE"
    )


class SchemaCanaryEvidenceClassification(StrEnum):
    """Evidence-bounded classification for the consumed failed run."""

    FAILED_DIAGNOSTIC = "failed_diagnostic"


class TurnTwoCacheConclusion(StrEnum):
    """Latest turn-two cache conclusion without inventing a zero."""

    NOT_OBSERVED = "not_observed"


class RenderedTokenNormalizationError(ValueError):
    """Typed normalization failure carrying a stable machine-readable code."""

    def __init__(
        self,
        code: RenderedTokenNormalizationFailureCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


class ChatTemplateTokenizer(Protocol):
    """Minimal tokenizer boundary used by the thin notebook orchestrator."""

    def apply_chat_template(
        self,
        conversation: Sequence[Mapping[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> object: ...

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
    ) -> object: ...


class RenderedTokenNormalizationPolicy(LocalABCContract):
    """Frozen policy defining the canonical rendered-token seam."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["canonical-rendered-token-extraction-v1"] = (
        "canonical-rendered-token-extraction-v1"
    )
    render_chat_template_with_tokenize_false: Literal[True] = True
    tokenize_exact_rendered_text_explicitly: Literal[True] = True
    add_special_tokens_during_explicit_tokenization: Literal[False] = False
    accepted_input_id_shapes: tuple[
        Literal["flat_sequence"],
        Literal["single_batch_sequence"],
        Literal["rank_1_array_like"],
        Literal["single_batch_rank_2_array_like"],
        Literal["mapping_input_ids"],
    ] = (
        "flat_sequence",
        "single_batch_sequence",
        "rank_1_array_like",
        "single_batch_rank_2_array_like",
        "mapping_input_ids",
    )
    reject_mapping_iteration_as_token_sequence: Literal[True] = True
    reject_multi_batch_input_ids: Literal[True] = True
    reject_empty_input_ids: Literal[True] = True
    reject_boolean_token_ids: Literal[True] = True
    retain_raw_rendered_text: Literal[False] = False
    retain_raw_token_ids_in_evidence: Literal[False] = False


CANONICAL_RENDERED_TOKEN_POLICY = RenderedTokenNormalizationPolicy()


class RenderedTokenIdentity(LocalABCContract):
    """Transient token IDs plus evidence-safe hashes and counts."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_sha256: str
    rendered_text_sha256: str
    rendered_text_character_count: int = Field(ge=1)
    token_ids: tuple[int, ...] = Field(min_length=1, exclude=True, repr=False)
    token_ids_sha256: str
    token_count: int = Field(ge=1)

    @field_validator(
        "policy_sha256",
        "rendered_text_sha256",
        "token_ids_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("rendered-token digests must be lowercase SHA-256")
        return value

    @field_validator("token_ids")
    @classmethod
    def validate_token_ids(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(isinstance(token_id, bool) or token_id < 0 for token_id in value):
            raise ValueError("token_ids must contain non-negative integers")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.policy_sha256 != CANONICAL_RENDERED_TOKEN_POLICY.fingerprint():
            raise ValueError("rendered-token identity must bind the canonical policy")
        if self.token_count != len(self.token_ids):
            raise ValueError("token_count must equal normalized token sequence length")
        if self.token_ids_sha256 != token_ids_sha256(self.token_ids):
            raise ValueError("token_ids_sha256 must match normalized token IDs")
        return self


class SchemaQualityCacheCanaryV1EvidenceAudit(LocalABCContract):
    """Immutable audit over the failed schema-constrained cache canary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit_id: str
    audited_at: datetime
    local_evidence_filename: Literal[
        "auragateway-schema-constrained-quality-cache-canary-evidence-v1 (1).zip"
    ]
    evidence_archive_sha256: str
    evidence_report_sha256: str
    evidence_ledger_sha256: str
    consumed_authorization_sha256: str
    consumed_authorization_reusable: Literal[False] = False
    reported_status: Literal["SCHEMA_CONSTRAINED_QUALITY_CACHE_CANARY_FAILED"] = (
        "SCHEMA_CONSTRAINED_QUALITY_CACHE_CANARY_FAILED"
    )
    classification: Literal[SchemaCanaryEvidenceClassification.FAILED_DIAGNOSTIC] = (
        SchemaCanaryEvidenceClassification.FAILED_DIAGNOSTIC
    )
    root_cause: Literal[
        SchemaCanaryV1DefectCode.CHAT_TEMPLATE_TOKEN_CONTAINER_COUNTED_AS_TOKEN_SEQUENCE
    ] = SchemaCanaryV1DefectCode.CHAT_TEMPLATE_TOKEN_CONTAINER_COUNTED_AS_TOKEN_SEQUENCE
    notebook_planned_prompt_tokens: Literal[2] = 2
    api_prompt_tokens: Literal[282] = 282
    vllm_prompt_tokens: Literal[282] = 282
    first_request_http_status: Literal[200] = 200
    turn_one_quality_passed: Literal[True] = True
    turn_one_schema_passed: Literal[True] = True
    turn_one_semantic_answer: Literal["sev3"] = "sev3"
    completed_trajectory_count: Literal[1] = 1
    completed_request_count: Literal[1] = 1
    failure_count: Literal[1] = 1
    abort_reason: Literal["TURN_FAILED"] = "TURN_FAILED"
    checkpoint_status: Literal["failed"] = "failed"
    cleanup_status: Literal["clean"] = "clean"
    hidden_retry_count: Literal[0] = 0
    replacement_trajectory_count: Literal[0] = 0
    turn_two_reached: Literal[False] = False
    turn_two_cache: Literal[TurnTwoCacheConclusion.NOT_OBSERVED] = (
        TurnTwoCacheConclusion.NOT_OBSERVED
    )
    model_boundary_defect: Literal[False] = False
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    corrected_canary_rerun_authorization_permitted: Literal[True] = True
    full_measured_rerun_authorized: Literal[False] = False
    next_gate: Literal["schema_constrained_quality_cache_canary_rerun_v2"] = (
        "schema_constrained_quality_cache_canary_rerun_v2"
    )

    @field_validator("audit_id")
    @classmethod
    def validate_audit_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("audit_id must use stable lowercase characters")
        return value

    @field_validator("audited_at")
    @classmethod
    def validate_audited_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("audited_at must be timezone-aware")
        return value

    @field_validator(
        "evidence_archive_sha256",
        "evidence_report_sha256",
        "evidence_ledger_sha256",
        "consumed_authorization_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("canary audit digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_diagnostic_boundary(self) -> Self:
        if self.local_evidence_filename != _EXPECTED_LOCAL_EVIDENCE_FILENAME:
            raise ValueError("audit must preserve the user's exact local evidence filename")
        if self.api_prompt_tokens != self.vllm_prompt_tokens:
            raise ValueError("API and vLLM prompt-token counts must agree")
        if not _token_counts_contradict(
            planned=self.notebook_planned_prompt_tokens,
            observed=self.api_prompt_tokens,
        ):
            raise ValueError("audit must preserve the notebook token-count contradiction")
        if self.turn_two_reached or self.turn_two_cache is not TurnTwoCacheConclusion.NOT_OBSERVED:
            raise ValueError("turn-two cache must remain not_observed")
        return self


class SchemaConstrainedQualityCanaryRerunAuthorization(LocalABCContract):
    """Fresh authorization for the unchanged six-request canary rerun."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    canary_id: str
    issued_at: datetime
    decision: Literal["authorized"] = "authorized"
    execution_authorized: Literal[True] = True
    requires_merged_commit_binding: Literal[True] = True
    merge_commit_binding_state: Literal["required_at_corrected_notebook_generation"] = (
        "required_at_corrected_notebook_generation"
    )
    failed_canary_audit_sha256: str
    consumed_authorization_sha256: str
    token_normalization_policy_sha256: str
    preserved_scope_sha256: str
    endpoint: Literal["/v1/chat/completions"] = "/v1/chat/completions"
    response_format_type: Literal["json_schema"] = "json_schema"
    selected_case_ids: tuple[
        Literal["incident-severity"],
        Literal["payment-reconciliation"],
        Literal["data-sharing-policy"],
    ] = _EXPECTED_CASE_IDS
    condition_id: Literal["C"] = "C"
    intended_route: tuple[Literal["worker_1"], Literal["worker_1"]] = (
        "worker_1",
        "worker_1",
    )
    trajectory_count: Literal[3] = 3
    request_count: Literal[6] = 6
    turns_per_trajectory: Literal[2] = 2
    full_worker_restart_before_each_trajectory: Literal[True] = True
    temperature: Decimal = Decimal("0")
    top_p: Decimal = Decimal("1")
    seed: Literal[7] = 7
    max_output_tokens: Literal[128] = 128
    stream: Literal[False] = False
    required_quality_checks: tuple[
        Literal["json_parse_success"],
        Literal["exact_key_set_match"],
        Literal["exact_answer_match"],
        Literal["exact_case_id_match"],
        Literal["exact_turn_index_match"],
        Literal["exact_confidence_match"],
        Literal["no_extra_text"],
    ] = _EXPECTED_QUALITY_CHECKS
    required_quality_pass_rate: Literal["1.0"] = "1.0"
    required_output_shape: Literal["json_object"] = "json_object"
    require_turn_one_cold: Literal[True] = True
    require_positive_turn_two_cached_tokens: Literal[True] = True
    require_planned_api_metric_prompt_token_match: Literal[True] = True
    compute_shared_prefix_from_normalized_token_ids: Literal[True] = True
    retain_rendered_text_sha256: Literal[True] = True
    retain_normalized_token_ids_sha256: Literal[True] = True
    cache_reuse_evaluation_permitted: Literal[True] = True
    max_trajectory_failures: Literal[0] = 0
    hidden_retries_permitted: Literal[False] = False
    replacement_trajectories_permitted: Literal[False] = False
    historical_notebook_rerun_permitted: Literal[False] = False
    corrected_notebook_generation_permitted_after_merge: Literal[True] = True
    gpu_enablement_permitted_before_corrected_notebook: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Decimal = Decimal("0")
    customer_data_used: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False

    @field_validator("canary_id")
    @classmethod
    def validate_canary_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("canary_id must use stable lowercase characters")
        return value

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator(
        "failed_canary_audit_sha256",
        "consumed_authorization_sha256",
        "token_normalization_policy_sha256",
        "preserved_scope_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("rerun authorization digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_frozen_scope(self) -> Self:
        if self.selected_case_ids != _EXPECTED_CASE_IDS:
            raise ValueError("rerun must preserve the frozen case order")
        if self.required_quality_checks != _EXPECTED_QUALITY_CHECKS:
            raise ValueError("rerun must preserve all seven deterministic quality checks")
        if self.token_normalization_policy_sha256 != (
            CANONICAL_RENDERED_TOKEN_POLICY.fingerprint()
        ):
            raise ValueError("authorization must bind the canonical token policy")
        if self.preserved_scope_sha256 != schema_canary_scope_sha256():
            raise ValueError("authorization must preserve the exact six-request scope")
        if self.external_spend != Decimal("0"):
            raise ValueError("schema canary external_spend must remain zero")
        return self


class SchemaCanaryRemediationPackage(LocalABCContract):
    """Cross-file binding for failed evidence and fresh rerun authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    audit: SchemaQualityCacheCanaryV1EvidenceAudit
    authorization: SchemaConstrainedQualityCanaryRerunAuthorization

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if self.audit.fingerprint() != self.authorization.failed_canary_audit_sha256:
            raise ValueError("rerun authorization does not bind the failed-canary audit")
        if (
            self.audit.consumed_authorization_sha256
            != self.authorization.consumed_authorization_sha256
        ):
            raise ValueError("rerun package must bind the consumed PR #74 authorization")
        if self.audit.consumed_authorization_reusable:
            raise ValueError("consumed authorization cannot be reused")
        if not self.audit.corrected_canary_rerun_authorization_permitted:
            raise ValueError("failed evidence does not permit the bounded rerun")
        if self.audit.full_measured_rerun_authorized:
            raise ValueError("failed audit cannot authorize full measured execution")
        if self.authorization.full_measured_rerun_authorized:
            raise ValueError("rerun authorization cannot authorize full measured execution")
        return self


def _coerce_array_like(value: object) -> object:
    tolist_method = getattr(value, "tolist", None)
    if callable(tolist_method):
        return cast(Callable[[], object], tolist_method)()
    return value


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _validate_flat_token_ids(values: Sequence[object]) -> tuple[int, ...]:
    if not values:
        raise RenderedTokenNormalizationError(
            RenderedTokenNormalizationFailureCode.INPUT_IDS_EMPTY,
            "input_ids must not be empty",
        )

    normalized: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise RenderedTokenNormalizationError(
                RenderedTokenNormalizationFailureCode.INPUT_ID_INVALID,
                "each input_id must be a non-negative integer",
            )
        token_id = int(value)
        if token_id < 0:
            raise RenderedTokenNormalizationError(
                RenderedTokenNormalizationFailureCode.INPUT_ID_INVALID,
                "each input_id must be a non-negative integer",
            )
        normalized.append(token_id)
    return tuple(normalized)


def normalize_rendered_token_ids(tokenized_output: object) -> tuple[int, ...]:
    """Extract one canonical token sequence without iterating mapping keys."""

    raw_input_ids: object = tokenized_output
    if isinstance(tokenized_output, Mapping):
        if "input_ids" not in tokenized_output:
            raise RenderedTokenNormalizationError(
                RenderedTokenNormalizationFailureCode.INPUT_IDS_MISSING,
                "tokenized mapping must contain input_ids",
            )
        raw_input_ids = tokenized_output["input_ids"]

    raw_input_ids = _coerce_array_like(raw_input_ids)
    if not _is_sequence(raw_input_ids):
        raise RenderedTokenNormalizationError(
            RenderedTokenNormalizationFailureCode.TOKENIZED_OUTPUT_UNSUPPORTED,
            "input_ids must be a sequence or array-like object",
        )

    sequence = list(raw_input_ids)
    if not sequence:
        raise RenderedTokenNormalizationError(
            RenderedTokenNormalizationFailureCode.INPUT_IDS_EMPTY,
            "input_ids must not be empty",
        )

    coerced_items = [_coerce_array_like(item) for item in sequence]
    nested_flags = [_is_sequence(item) for item in coerced_items]
    if not any(nested_flags):
        return _validate_flat_token_ids(coerced_items)

    first_item = coerced_items[0]
    if len(coerced_items) != 1 or not _is_sequence(first_item):
        raise RenderedTokenNormalizationError(
            RenderedTokenNormalizationFailureCode.INPUT_IDS_AMBIGUOUS_BATCH,
            "input_ids must contain exactly one token sequence",
        )

    nested_sequence = list(first_item)
    nested_sequence = [_coerce_array_like(item) for item in nested_sequence]
    if any(_is_sequence(item) for item in nested_sequence):
        raise RenderedTokenNormalizationError(
            RenderedTokenNormalizationFailureCode.INPUT_IDS_AMBIGUOUS_BATCH,
            "input_ids rank must be one or a single-batch rank two",
        )
    return _validate_flat_token_ids(nested_sequence)


def token_ids_sha256(token_ids: tuple[int, ...]) -> str:
    """Hash normalized token IDs through canonical JSON."""

    payload = json.dumps(
        list(token_ids),
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_rendered_token_identity(
    *,
    tokenizer: ChatTemplateTokenizer,
    messages: Sequence[Mapping[str, str]],
    add_generation_prompt: bool = True,
) -> RenderedTokenIdentity:
    """Render once, explicitly tokenize that exact text, and return safe identity."""

    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
    )
    if not isinstance(rendered, str) or not rendered:
        raise RenderedTokenNormalizationError(
            RenderedTokenNormalizationFailureCode.RENDERED_TEXT_INVALID,
            "chat template must return non-empty rendered text",
        )

    tokenized = tokenizer(
        rendered,
        add_special_tokens=False,
    )
    token_ids = normalize_rendered_token_ids(tokenized)
    return RenderedTokenIdentity(
        policy_sha256=CANONICAL_RENDERED_TOKEN_POLICY.fingerprint(),
        rendered_text_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        rendered_text_character_count=len(rendered),
        token_ids=token_ids,
        token_ids_sha256=token_ids_sha256(token_ids),
        token_count=len(token_ids),
    )


def common_prefix_token_count(
    left_token_ids: tuple[int, ...],
    right_token_ids: tuple[int, ...],
) -> int:
    """Count the exact common prefix over canonical normalized token IDs."""

    count = 0
    for left, right in zip(left_token_ids, right_token_ids, strict=False):
        if left != right:
            break
        count += 1
    return count


def schema_canary_scope_payload() -> dict[str, Any]:
    """Return the exact immutable scope inherited from PR #74."""

    return {
        "endpoint": "/v1/chat/completions",
        "response_format_type": "json_schema",
        "selected_case_ids": list(_EXPECTED_CASE_IDS),
        "condition_id": "C",
        "intended_route": ["worker_1", "worker_1"],
        "trajectory_count": 3,
        "request_count": 6,
        "turns_per_trajectory": 2,
        "full_worker_restart_before_each_trajectory": True,
        "temperature": "0",
        "top_p": "1",
        "seed": 7,
        "max_output_tokens": 128,
        "stream": False,
        "required_quality_checks": list(_EXPECTED_QUALITY_CHECKS),
        "required_quality_pass_rate": "1.0",
        "required_output_shape": "json_object",
        "require_turn_one_cold": True,
        "require_positive_turn_two_cached_tokens": True,
        "max_trajectory_failures": 0,
        "hidden_retries_permitted": False,
        "replacement_trajectories_permitted": False,
        "external_spend": "0",
        "customer_data_used": False,
        "raw_prompt_logging_permitted": False,
        "raw_output_logging_permitted": False,
        "full_measured_rerun_authorized": False,
    }


def schema_canary_scope_sha256() -> str:
    """Hash the exact inherited six-request scope."""

    payload = json.dumps(
        schema_canary_scope_payload(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_schema_canary_remediation_package(
    *,
    audit_path: Path,
    authorization_path: Path,
) -> SchemaCanaryRemediationPackage:
    """Load and cross-validate the failed audit and fresh rerun authorization."""

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    authorization_payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    return SchemaCanaryRemediationPackage(
        audit=SchemaQualityCacheCanaryV1EvidenceAudit.model_validate(audit_payload),
        authorization=SchemaConstrainedQualityCanaryRerunAuthorization.model_validate(
            authorization_payload
        ),
    )
