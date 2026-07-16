"""Bounded execution authorization for reconcile-balance action extraction."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import field_validator, model_validator

from auragateway.local_abc.action_extraction_eval import (
    RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY,
    ActionExtractionEvaluationPackage,
    ReconcileBalanceExtractionManifest,
    load_action_extraction_evaluation_package,
)
from auragateway.local_abc.arithmetic_action import (
    DeterministicCapabilityId,
    reconcile_balance_action_schema_sha256,
)
from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")

_HARNESS_MERGE_COMMIT: Final[Literal["42ef2e6e7d268d0213c2f3a4a48aa536c04eba59"]] = (
    "42ef2e6e7d268d0213c2f3a4a48aa536c04eba59"
)
_IMPLEMENTATION_COMMIT: Final[Literal["0e4f761de11c85ccf40d234e93a5b2d974590612"]] = (
    "0e4f761de11c85ccf40d234e93a5b2d974590612"
)
_MANIFEST_SHA256: Final[
    Literal["babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5"]
] = "babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5"
_PLAN_SHA256: Final[Literal["53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62"]] = (
    "53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62"
)
_PROMPT_POLICY_SHA256: Final[
    Literal["5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"]
] = "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
_ACTION_SCHEMA_SHA256: Final[
    Literal["923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"]
] = "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
_CASE_MANIFEST_GIT_BLOB_SHA: Final[Literal["e2fe9721c1639a73ed5f806e29cd1d6de9115196"]] = (
    "e2fe9721c1639a73ed5f806e29cd1d6de9115196"
)
_EVAL_PLAN_GIT_BLOB_SHA: Final[Literal["1c6b936835db9a1bbd7d739918d78a83b7cff8ef"]] = (
    "1c6b936835db9a1bbd7d739918d78a83b7cff8ef"
)

_EXPECTED_CASE_IDS: Final = (
    "historical-turn-one",
    "turn-two-history-distractors",
    "reordered-narrative",
    "zero-boundary",
    "repeated-operands",
    "metadata-number-distractors",
    "formatted-currency-values",
    "key-value-layout",
    "same-answer-different-operands",
    "maximum-opening-boundary",
    "credits-first-description",
    "turn-two-feedback-separation",
)


class ActionExtractionAuthorizationDecision(StrEnum):
    """Review decision for the bounded action-extraction canary."""

    AUTHORIZED = "authorized"


class SemanticFailureDisposition(StrEnum):
    """How a first-attempt model-quality failure affects the run."""

    RETAIN_AND_CONTINUE = "retain_and_continue"


class InfrastructureFailureDisposition(StrEnum):
    """How an infrastructure or source-binding failure affects the run."""

    ABORT_RUN = "abort_run"


class ActionExtractionModelBinding(LocalABCContract):
    """Exact model and tokenizer snapshot permitted by this authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_manifest_sha256: Literal[
        "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
    ] = "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
    config_sha256: Literal["18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"] = (
        "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"
    )
    generation_config_sha256: Literal[
        "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"
    ] = "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"
    tokenizer_json_sha256: Literal[
        "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
    ] = "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
    tokenizer_config_sha256: Literal[
        "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"
    ] = "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"

    @field_validator(
        "model_manifest_sha256",
        "config_sha256",
        "generation_config_sha256",
        "tokenizer_json_sha256",
        "tokenizer_config_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("model-binding digests must be lowercase SHA-256")
        return value


class ActionExtractionRuntimeBinding(LocalABCContract):
    """Exact local Kaggle runtime permitted by this authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    gpu_count: Literal[2] = 2
    gpu_name: Literal["Tesla T4"] = "Tesla T4"
    compute_capability: Literal["7.5"] = "7.5"
    torch_version: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    vllm_module_version: Literal["0.25.1"] = "0.25.1"
    vllm_distribution_version: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_wheel_sha256: Literal[
        "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
    ] = "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"

    @field_validator("vllm_wheel_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("vLLM wheel digest must be lowercase SHA-256")
        return value


class ActionExtractionDecodingPolicy(LocalABCContract):
    """Deterministic request settings for every fixed extraction case."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    endpoint: Literal["/v1/chat/completions"] = "/v1/chat/completions"
    response_format_type: Literal["json_schema"] = "json_schema"
    temperature: Decimal = Decimal("0")
    top_p: Decimal = Decimal("1")
    seed: Literal[7] = 7
    max_output_tokens: Literal[128] = 128
    stream: Literal[False] = False
    permitted_finish_reasons: tuple[Literal["stop"], ...] = ("stop",)

    @model_validator(mode="after")
    def validate_deterministic_settings(self) -> Self:
        if self.temperature != Decimal("0") or self.top_p != Decimal("1"):
            raise ValueError("action extraction decoding must remain deterministic")
        return self


class ActionExtractionStopPolicy(LocalABCContract):
    """Continue through semantic failures but abort infrastructure failures."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    required_request_count: Literal[12] = 12
    request_attempts_per_case: Literal[1] = 1
    semantic_failure_disposition: Literal[SemanticFailureDisposition.RETAIN_AND_CONTINUE] = (
        SemanticFailureDisposition.RETAIN_AND_CONTINUE
    )
    infrastructure_failure_disposition: Literal[InfrastructureFailureDisposition.ABORT_RUN] = (
        InfrastructureFailureDisposition.ABORT_RUN
    )
    max_retained_semantic_failures: Literal[12] = 12
    max_infrastructure_failures: Literal[0] = 0
    hidden_retry_count: Literal[0] = 0
    repair_attempt_count: Literal[0] = 0
    replacement_request_count: Literal[0] = 0
    direct_model_arithmetic_fallback_permitted: Literal[False] = False
    require_complete_twelve_record_ledger: Literal[True] = True
    abort_on_source_binding_failure: Literal[True] = True
    abort_on_model_identity_failure: Literal[True] = True
    abort_on_runtime_identity_failure: Literal[True] = True
    abort_on_worker_start_failure: Literal[True] = True
    abort_on_transport_failure: Literal[True] = True
    abort_on_cleanup_failure: Literal[True] = True


class ActionExtractionEvidenceContract(LocalABCContract):
    """Exact output filenames and privacy restrictions for the bounded run."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    schedule_filename: Literal["reconcile_balance_extraction_canary_schedule_v1.json"] = (
        "reconcile_balance_extraction_canary_schedule_v1.json"
    )
    ledger_filename: Literal["reconcile_balance_extraction_canary_ledger_v1.jsonl"] = (
        "reconcile_balance_extraction_canary_ledger_v1.jsonl"
    )
    checkpoint_filename: Literal["reconcile_balance_extraction_canary_checkpoint_v1.json"] = (
        "reconcile_balance_extraction_canary_checkpoint_v1.json"
    )
    evaluation_filename: Literal["reconcile_balance_extraction_canary_evaluation_v1.json"] = (
        "reconcile_balance_extraction_canary_evaluation_v1.json"
    )
    report_filename: Literal["reconcile_balance_extraction_canary_report_v1.json"] = (
        "reconcile_balance_extraction_canary_report_v1.json"
    )
    summary_filename: Literal["RECONCILE_BALANCE_EXTRACTION_CANARY_SUMMARY.txt"] = (
        "RECONCILE_BALANCE_EXTRACTION_CANARY_SUMMARY.txt"
    )
    model_snapshot_filename: Literal["model_snapshot_manifest_v1.json"] = (
        "model_snapshot_manifest_v1.json"
    )
    worker_log_filename: Literal["worker_1.log"] = "worker_1.log"
    raw_prompt_retention_permitted: Literal[False] = False
    raw_output_retention_permitted: Literal[False] = False
    raw_action_retention_permitted: Literal[False] = False
    token_id_retention_permitted: Literal[False] = False
    retain_prompt_hashes: Literal[True] = True
    retain_output_hashes: Literal[True] = True
    retain_action_hashes: Literal[True] = True
    retain_result_hashes: Literal[True] = True
    retain_failure_codes: Literal[True] = True
    retain_completion_token_counts: Literal[True] = True

    @model_validator(mode="after")
    def validate_filenames(self) -> Self:
        filenames = (
            self.schedule_filename,
            self.ledger_filename,
            self.checkpoint_filename,
            self.evaluation_filename,
            self.report_filename,
            self.summary_filename,
            self.model_snapshot_filename,
            self.worker_log_filename,
        )
        if len(filenames) != len(set(filenames)):
            raise ValueError("evidence filenames must be unique")
        return self


class ActionExtractionCanaryAuthorization(LocalABCContract):
    """One bounded 12-request authorization for action extraction."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: Literal["reconcile-balance-action-extraction-canary-authorization-v1"] = (
        "reconcile-balance-action-extraction-canary-authorization-v1"
    )
    issued_at: datetime
    decision: Literal[ActionExtractionAuthorizationDecision.AUTHORIZED] = (
        ActionExtractionAuthorizationDecision.AUTHORIZED
    )
    repository: Literal["kablewithak/auragateway"] = "kablewithak/auragateway"
    harness_merge_commit: Literal["42ef2e6e7d268d0213c2f3a4a48aa536c04eba59"] = (
        _HARNESS_MERGE_COMMIT
    )
    implementation_commit: Literal["0e4f761de11c85ccf40d234e93a5b2d974590612"] = (
        _IMPLEMENTATION_COMMIT
    )
    case_manifest_repository_path: Literal[
        "benchmarks/local_abc/reconcile_balance_extraction_eval_cases_v1.json"
    ]
    case_manifest_git_blob_sha: Literal["e2fe9721c1639a73ed5f806e29cd1d6de9115196"] = (
        _CASE_MANIFEST_GIT_BLOB_SHA
    )
    evaluation_plan_repository_path: Literal[
        "benchmarks/local_abc/reconcile_balance_extraction_eval_plan_v1.json"
    ]
    evaluation_plan_git_blob_sha: Literal["1c6b936835db9a1bbd7d739918d78a83b7cff8ef"] = (
        _EVAL_PLAN_GIT_BLOB_SHA
    )
    case_manifest_sha256: Literal[
        "babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5"
    ] = _MANIFEST_SHA256
    evaluation_plan_sha256: Literal[
        "53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62"
    ] = _PLAN_SHA256
    prompt_policy_sha256: Literal[
        "5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9"
    ] = _PROMPT_POLICY_SHA256
    action_schema_sha256: Literal[
        "923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7"
    ] = _ACTION_SCHEMA_SHA256
    capability: Literal[DeterministicCapabilityId.RECONCILE_BALANCE] = (
        DeterministicCapabilityId.RECONCILE_BALANCE
    )
    selected_case_ids: tuple[str, ...] = _EXPECTED_CASE_IDS
    case_count: Literal[12] = 12
    worker_id: Literal["worker_1"] = "worker_1"
    full_worker_restart_before_run: Literal[True] = True
    cache_measurement_in_scope: Literal[False] = False
    cache_claims_permitted: Literal[False] = False
    model: ActionExtractionModelBinding = ActionExtractionModelBinding()
    runtime: ActionExtractionRuntimeBinding = ActionExtractionRuntimeBinding()
    decoding: ActionExtractionDecodingPolicy = ActionExtractionDecodingPolicy()
    stop_policy: ActionExtractionStopPolicy = ActionExtractionStopPolicy()
    evidence: ActionExtractionEvidenceContract = ActionExtractionEvidenceContract()
    execution_authorized: Literal[True] = True
    bounded_gpu_execution_permitted_after_preflight: Literal[True] = True
    notebook_generation_permitted_after_merge: Literal[True] = True
    authorization_merge_commit_binding_required: Literal[True] = True
    notebook_sha256_binding_required: Literal[True] = True
    gpu_enablement_permitted_before_qualified_notebook: Literal[False] = False
    full_measured_rerun_authorized: Literal[False] = False
    external_spend: Decimal = Decimal("0")
    customer_data_used: Literal[False] = False
    synthetic_data_only: Literal[True] = True
    next_gate: Literal["qualified_action_extraction_notebook_generation"] = (
        "qualified_action_extraction_notebook_generation"
    )

    @field_validator("authorization_id")
    @classmethod
    def validate_authorization_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization ID must use stable lowercase characters")
        return value

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value

    @field_validator(
        "case_manifest_sha256",
        "evaluation_plan_sha256",
        "prompt_policy_sha256",
        "action_schema_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("authorization digests must be lowercase SHA-256")
        return value

    @field_validator(
        "harness_merge_commit",
        "implementation_commit",
        "case_manifest_git_blob_sha",
        "evaluation_plan_git_blob_sha",
    )
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("source bindings must be lowercase Git SHA-1")
        return value

    @model_validator(mode="after")
    def validate_authorized_boundary(self) -> Self:
        if self.selected_case_ids != _EXPECTED_CASE_IDS:
            raise ValueError("authorization must preserve the fixed case order")
        if self.case_count != len(self.selected_case_ids):
            raise ValueError("authorization case count must match selected cases")
        if self.external_spend != Decimal("0"):
            raise ValueError("external spend must remain zero")
        if self.prompt_policy_sha256 != (RECONCILE_BALANCE_EXTRACTION_PROMPT_POLICY.fingerprint()):
            raise ValueError("authorization prompt-policy binding drifted")
        if self.action_schema_sha256 != reconcile_balance_action_schema_sha256():
            raise ValueError("authorization action-schema binding drifted")
        return self


class ActionExtractionAuthorizationPackage(LocalABCContract):
    """Cross-file package for evaluation assets and execution authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    evaluation: ActionExtractionEvaluationPackage
    authorization: ActionExtractionCanaryAuthorization

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        manifest = self.evaluation.manifest
        plan = self.evaluation.plan
        authorization = self.authorization
        if manifest.fingerprint() != authorization.case_manifest_sha256:
            raise ValueError("authorization must bind the fixed case manifest")
        if plan.fingerprint() != authorization.evaluation_plan_sha256:
            raise ValueError("authorization must bind the fixed evaluation plan")
        if manifest.implementation_commit != authorization.implementation_commit:
            raise ValueError("authorization implementation commit drifted")
        if authorization.harness_merge_commit != _HARNESS_MERGE_COMMIT:
            raise ValueError("authorization must bind the PR #79 merge commit")
        manifest_ids = tuple(case.eval_case_id for case in manifest.accepted_cases)
        if manifest_ids != authorization.selected_case_ids:
            raise ValueError("authorization selected cases drifted from the manifest")
        if manifest.execution_authorized or plan.execution_authorized:
            raise ValueError("historical planning assets must remain non-executable")
        if manifest.gpu_execution_authorized or plan.gpu_execution_authorized:
            raise ValueError("planning assets must not gain GPU authorization")
        if (
            manifest.full_measured_rerun_authorized
            or plan.full_measured_rerun_authorized
            or authorization.full_measured_rerun_authorized
        ):
            raise ValueError("full measured execution must remain blocked")
        return self


class ActionExtractionNotebookBinding(LocalABCContract):
    """Qualified notebook identity derived after the authorization PR merges."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_sha256: str
    authorization_merge_commit: str
    notebook_sha256: str
    repository: Literal["kablewithak/auragateway"] = "kablewithak/auragateway"
    harness_merge_commit: Literal["42ef2e6e7d268d0213c2f3a4a48aa536c04eba59"] = (
        _HARNESS_MERGE_COMMIT
    )
    model: ActionExtractionModelBinding
    runtime: ActionExtractionRuntimeBinding
    case_count: Literal[12] = 12
    request_count: Literal[12] = 12
    execution_decision: Literal["authorized"] = "authorized"
    bounded_gpu_execution_authorized: Literal[True] = True
    full_measured_rerun_authorized: Literal[False] = False
    raw_prompt_retention_permitted: Literal[False] = False
    raw_output_retention_permitted: Literal[False] = False

    @field_validator("authorization_sha256", "notebook_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook bindings must use lowercase SHA-256")
        return value

    @field_validator("authorization_merge_commit", "harness_merge_commit")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if _GIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("notebook bindings must use lowercase Git SHA-1")
        return value

    @model_validator(mode="after")
    def validate_merge_boundary(self) -> Self:
        if self.authorization_merge_commit == self.harness_merge_commit:
            raise ValueError("notebook must bind the later authorization merge commit")
        return self


def load_action_extraction_authorization(
    path: Path,
) -> ActionExtractionCanaryAuthorization:
    """Load and validate the bounded execution authorization."""

    return ActionExtractionCanaryAuthorization.model_validate_json(path.read_text(encoding="utf-8"))


def load_action_extraction_authorization_package(
    *,
    manifest_path: Path,
    plan_path: Path,
    authorization_path: Path,
) -> ActionExtractionAuthorizationPackage:
    """Load and cross-validate planning assets with the authorization."""

    return ActionExtractionAuthorizationPackage(
        evaluation=load_action_extraction_evaluation_package(
            manifest_path=manifest_path,
            plan_path=plan_path,
        ),
        authorization=load_action_extraction_authorization(authorization_path),
    )


def build_action_extraction_notebook_binding(
    *,
    package: ActionExtractionAuthorizationPackage,
    authorization_merge_commit: str,
    notebook_sha256: str,
    observed_model: ActionExtractionModelBinding,
    observed_runtime: ActionExtractionRuntimeBinding,
) -> ActionExtractionNotebookBinding:
    """Fail closed unless the generated notebook binds the authorized runtime."""

    authorization = package.authorization
    if observed_model != authorization.model:
        raise ValueError("observed model identity does not match authorization")
    if observed_runtime != authorization.runtime:
        raise ValueError("observed runtime identity does not match authorization")
    return ActionExtractionNotebookBinding(
        authorization_sha256=authorization.fingerprint(),
        authorization_merge_commit=authorization_merge_commit,
        notebook_sha256=notebook_sha256,
        model=observed_model,
        runtime=observed_runtime,
    )


def fixed_action_extraction_case_ids(
    manifest: ReconcileBalanceExtractionManifest,
) -> tuple[str, ...]:
    """Return the exact accepted case order used by authorization tests."""

    return tuple(case.eval_case_id for case in manifest.accepted_cases)
