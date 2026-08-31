"""Materialize the final-342 frozen execution-manifest subject without live authority.

This boundary freezes deterministic experiment/runtime identity bytes only. It performs no
model, GPU, Kaggle, network, issuer, or live execution work. Repository-level freeze promotion
remains blocked until a separate post-commit custody receipt binds the exact manifest bytes to
the first Git commit that contains them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_SUBJECT_COMMIT = "fcf403a1c31e26a2cdf3f682a8878db01338a13d"

MANIFEST_PATH = Path("data/evals/benchmark/freeze-v3/final_342_execution_manifest_v1.json")
ADR_PATH = Path("docs/adr/2026-08-31-local-abc-final-342-execution-manifest-freeze-v1.md")
REQUIREMENTS_PATH = Path("docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md")
CONSTITUTION_PATH = Path("docs/benchmark/AuraGateway_Benchmark_Constitution.md")
G10_PATH = Path("data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json")
PLANNED_LEDGER_PATH = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
PREFLIGHT_DRAFT_PATH = Path("data/evals/benchmark/preflight-v3/execution_manifest_draft.json")
CONDITION_FINGERPRINTS_PATH = Path("data/evals/benchmark/preflight-v3/condition_fingerprints.json")
G11_3A_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_requirements_precedence_reconciliation_v1.json"
)
PRODUCER_PATH = Path("src/auragateway/local_abc/final_342_execution_producer_v1.py")
REVIEW_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_measured_review_successor_v1.json"
)
QUALITY_PATH = Path("src/auragateway/local_abc/final_342_measured_quality_reducers_v1.py")
ANALYSIS_PATH = Path("src/auragateway/local_abc/final_342_analysis_engine_v1.py")
REHEARSAL_PATH = Path(
    "src/auragateway/local_abc/final_342_offline_orchestration_integration_rehearsal_v1.py"
)
REHEARSAL_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_offline_orchestration_integration_rehearsal_v1.json"
)
EXACT_RUNTIME_PATH = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
RUNTIME_LOCK_PATH = Path(
    "benchmarks/local_abc/evidence/"
    "preflight_v3_exact_runtime_wheelhouse_materialization_v1/requirements.lock.txt"
)
HISTORICAL_EXECUTION_MANIFEST_PATH = Path("data/evals/benchmark/freeze-v1/execution_manifest.json")
HISTORICAL_FREEZE_MANIFEST_PATH = Path("data/evals/benchmark/freeze-v1/manifest.json")

EXPECTED_RUNTIME_LOCK_SHA256 = "cf5d773ef5c26f2e42a7afd76f0e466c21847169986f14fe5a7ac9ad02f0a3c3"
EXPECTED_REVIEW_SCHEDULE_SHA256 = "9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c"
EXPECTED_PLANNING_MANIFEST_SHA256 = (
    "4bd822375390cf413718553313903679e78b650dfa798955e2f7c61ebd8b8678"
)

EXPECTED_GIT_BLOBS: dict[str, str] = {
    REQUIREMENTS_PATH.as_posix(): "da1e28f49b486a43dff97476ac35c74af495467b",
    CONSTITUTION_PATH.as_posix(): "dc25906298a611b71f3482da85c6aba763c474e7",
    G10_PATH.as_posix(): "9999eb0350a3d3e01a9f5f3451f54d7deaa35aef",
    PLANNED_LEDGER_PATH.as_posix(): "553b23e24629bdca81d9fb9fdcbd90cc2081caf0",
    CONDITION_FINGERPRINTS_PATH.as_posix(): "35be4e1f611ba58ea356eef4c2b6477dee95c73f",
    G11_3A_RECORD_PATH.as_posix(): "a39fcea33ae7474ac81ee13d669f87f96e446b2c",
    PRODUCER_PATH.as_posix(): "9bedae7c7815e80d7c03ccc37b1e5261310056cf",
    REVIEW_RECORD_PATH.as_posix(): "684d645daccb2357e886267154424e2533c6401c",
    QUALITY_PATH.as_posix(): "e84f47010f16f0340d38de71a22e1cc7c03b6252",
    ANALYSIS_PATH.as_posix(): "6385c01486885e3e21b90fb18765602eba3b083e",
    REHEARSAL_PATH.as_posix(): "13c10670639e579a984548193f9eeb9ed9ea81a6",
    REHEARSAL_RECORD_PATH.as_posix(): "239cd89f361734accbaa5117f79d12e05c96f515",
    EXACT_RUNTIME_PATH.as_posix(): "60aa9ee71eb1dfc6b92bf6b6b06ee5ad1386900c",
    RUNTIME_LOCK_PATH.as_posix(): "ec52f63cbef6de173d3b34696c2a19b8cada642d",
    HISTORICAL_EXECUTION_MANIFEST_PATH.as_posix(): ("791299bb0df45441f25ed8c1e030d84ca1a31ec3"),
    HISTORICAL_FREEZE_MANIFEST_PATH.as_posix(): ("857064310d5895e462e8a06069daa4a9678ac11f"),
}

REQUIRED_FIELD_NAMES = (
    "execution_manifest_version",
    "execution_manifest_hash",
    "benchmark_constitution_version",
    "benchmark_constitution_hash",
    "benchmark_runner_version",
    "comparison_eligibility_contract_version",
    "evidence_bundle_schema_version",
    "git_commit_hash",
    "python_version",
    "dependency_lock_hash",
    "corpus_manifest_hash",
    "chunking_strategy_id",
    "chunking_configuration_hash",
    "retrieval_implementation_id",
    "retrieval_configuration_hash",
    "retrieval_type",
    "top_k",
    "metadata_filter_policy_version",
    "development_retrieval_manifest_hash",
    "held_out_retrieval_manifest_hash",
    "retrieval_scorecard_hash",
    "prompt_template_id",
    "prompt_template_version",
    "static_context_pack_id",
    "static_context_pack_version",
    "serialization_version",
    "tool_contract_version",
    "output_schema_version",
    "prefix_fingerprint_contract_version",
    "primary_provider",
    "provider_model_alias",
    "exact_model_identifier",
    "provider_adapter_version",
    "provider_documentation_date_checked",
    "telemetry_rules_version",
    "telemetry_fixture_manifest_hash",
    "cache_ttl_assumption_seconds",
    "cache_ttl_source",
    "pricing_schedule_version",
    "pricing_source_date",
    "currency",
    "route_policy_version",
    "economy_model_alias",
    "capable_model_alias",
    "capability_calibration_report_hash",
    "route_ttl_policy_version",
    "provider_failure_policy_version",
    "diagnostic_episode_manifest_hash",
    "functional_benchmark_manifest_hash",
    "runtime_microbenchmark_manifest_hash",
    "quality_rubric_version",
    "quality_rubric_hash",
    "blinded_adjudication_protocol_version",
    "review_sample_schedule_hash",
    "feedback_evidence_contract_version",
    "negative_control_manifest_hash",
    "fault_injection_fixture_hash",
    "privacy_trace_contract_version",
    "privacy_verification_report_hash",
    "cross_condition_isolation_test_hash",
    "functional_run_order_schedule_id",
    "runtime_run_order_schedule_id",
    "timeout_policy_id",
    "retry_policy_id",
    "exclusion_policy_id",
    "rerun_policy_id",
    "denominator_policy_id",
    "statistical_reporting_configuration_id",
    "quality_non_inferiority_policy_id",
)

NEXT_GATE = "BIND_FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_V1"


class ManifestFreezeError(RuntimeError):
    """Metadata-safe manifest-freeze failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: Path | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ManifestFreezeError("FINAL_342_MANIFEST_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceBinding(FrozenModel):
    path: str
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class IdentityFields(FrozenModel):
    execution_manifest_version: Literal["1.0.0"]
    execution_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_constitution_version: Literal["1.0.0"]
    benchmark_constitution_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_runner_version: Literal["auragateway-final-342-execution-producer-v1"]
    comparison_eligibility_contract_version: Literal["comparison-eligibility-v1"]
    evidence_bundle_schema_version: Literal["1.0.0"]
    git_commit_hash: Literal["POST_COMMIT_CUSTODY_RECEIPT_REQUIRED"]
    python_version: Literal["CPython-3.12-cp312"]
    dependency_lock_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class CorpusRetrievalFields(FrozenModel):
    corpus_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    chunking_strategy_id: Literal["section-aware-v1"]
    chunking_configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_implementation_id: Literal["dense-hashed-tfidf-section-aware-remediated-v2"]
    retrieval_configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_type: Literal["dense_hashed_tfidf"]
    top_k: Literal[5]
    metadata_filter_policy_version: Literal["authored-case-filters-v1"]
    development_retrieval_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    held_out_retrieval_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_scorecard_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class ContextContractFields(FrozenModel):
    prompt_template_id: Literal["nimbus-relay-support-template-v1"]
    prompt_template_version: Literal["1.0.0"]
    static_context_pack_id: Literal["nimbus-relay-static-context-v1"]
    static_context_pack_version: Literal["1.0.0"]
    serialization_version: Literal["canonical-static-provider-v1"]
    tool_contract_version: Literal["tool-contract-v1"]
    output_schema_version: Literal["terminal-decision-v1"]
    prefix_fingerprint_contract_version: Literal["hmac-sha256-static-prefix-v1"]


class ProviderTelemetryFields(FrozenModel):
    primary_provider: Literal["local_vllm"]
    provider_model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    exact_model_identifier: Literal[
        "Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775"
    ]
    provider_adapter_version: Literal["final-342-loopback-vllm-transport-v1"]
    provider_documentation_date_checked: Literal["NOT_APPLICABLE_LOCAL_RUNTIME_ARTIFACT_BOUND"]
    telemetry_rules_version: Literal["final-342-turn-measurement-v1"]
    telemetry_fixture_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cache_ttl_assumption_seconds: Literal[300]
    cache_ttl_source: Literal["benchmark-assumption-v1"]
    pricing_schedule_version: Literal["NOT_APPLICABLE_MONETARY_COST_OUT_OF_SCOPE"]
    pricing_source_date: Literal["NOT_APPLICABLE_MONETARY_COST_OUT_OF_SCOPE"]
    currency: Literal["NONE"]


class RoutePolicyFields(FrozenModel):
    route_policy_version: Literal["final-342-worker-route-realization-v1"]
    economy_model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    capable_model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    capability_calibration_report_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    route_ttl_policy_version: Literal["final-342-warm-eligibility-v1"]
    provider_failure_policy_version: Literal["provider-request-policy-v1"]


class EvaluationAdjudicationFields(FrozenModel):
    diagnostic_episode_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    functional_benchmark_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_microbenchmark_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_rubric_version: Literal["auragateway-quality-rubric-v1"]
    quality_rubric_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    blinded_adjudication_protocol_version: Literal["blinded-adjudication-v1"]
    review_sample_schedule_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    feedback_evidence_contract_version: Literal["efc-evidence-v1"]


class FaultPrivacyFields(FrozenModel):
    negative_control_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    fault_injection_fixture_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    privacy_trace_contract_version: Literal["privacy-safe-observability-v1"]
    privacy_verification_report_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cross_condition_isolation_test_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenControls(FrozenModel):
    functional_run_order_schedule_id: Literal["functional-counterbalance-v1"]
    runtime_run_order_schedule_id: Literal["runtime-counterbalance-v1"]
    timeout_policy_id: Literal["provider-request-policy-v1"]
    retry_policy_id: Literal["provider-request-policy-v1"]
    exclusion_policy_id: Literal["exclusion-policy-v1"]
    rerun_policy_id: Literal["rerun-policy-v1"]
    denominator_policy_id: Literal["denominator-policy-v1"]
    statistical_reporting_configuration_id: Literal["paired-bootstrap-v1"]
    quality_non_inferiority_policy_id: Literal["quality-non-inferiority-v1"]


class RuntimeQualification(FrozenModel):
    environment: Literal["kaggle_t4_x2"]
    execution_backend: Literal["local_vllm"]
    python_abi: Literal["cp312"]
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    served_model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    vllm_distribution_version: Literal["0.25.1+cu129"]
    torch_version: Literal["2.11.0+cu129"]
    torch_cuda_version: Literal["12.9"]
    triton_version: Literal["3.6.0"]
    transformers_version: Literal["5.14.1"]
    gpu_model: Literal["Tesla T4"]
    compute_capability: Literal["7.5"]
    attention_backend: Literal["TRITON_ATTN"]
    transport_endpoint: Literal["/v1/chat/completions"]
    requirements_lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RouteCompatibilityResolution(FrozenModel):
    compatibility_id: Literal["final-342-local-worker-route-compatibility-v1"]
    historical_provider_model_routing_reused: Literal[False] = False
    single_local_model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    turn_local_route_schedule_id: Literal["turn-local-worker1-worker2-v1"]
    affinity_route_schedule_id: Literal["affinity-worker1-worker1-v1"]
    derive_route_from_condition_permitted: Literal[False] = False


class CostScope(FrozenModel):
    monetary_cost_comparison_in_scope: Literal[False] = False
    monetary_cost_effect_claims_permitted: Literal[False] = False
    external_spend_ceiling: Literal[0] = 0
    synthetic_price_per_request_permitted: Literal[False] = False


class CustodyPolicy(FrozenModel):
    source_subject_commit: Literal["fcf403a1c31e26a2cdf3f682a8878db01338a13d"]
    first_containing_commit_stored_inside_manifest: Literal[False] = False
    post_commit_custody_receipt_required: Literal[True] = True
    receipt_binds_manifest_semantic_sha256: Literal[True] = True
    receipt_binds_manifest_file_sha256: Literal[True] = True
    receipt_binds_source_subject_commit: Literal[True] = True
    receipt_binds_first_containing_commit: Literal[True] = True
    repository_freeze_gate_promoted_before_receipt: Literal[False] = False


class SafetyState(FrozenModel):
    manifest_subject_bytes_frozen: Literal[True] = True
    repository_execution_manifest_frozen: Literal[False] = False
    repository_freeze_gate_promoted: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    network_transport_performed: Literal[False] = False
    live_authorization_issued: Literal[False] = False


class Final342ExecutionManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-final-342-execution-manifest-v1"]
    manifest_status: Literal["FROZEN_SUBJECT_PENDING_POST_COMMIT_CUSTODY"]
    identity: IdentityFields
    corpus_retrieval: CorpusRetrievalFields
    context_contract: ContextContractFields
    provider_telemetry: ProviderTelemetryFields
    route_policy: RoutePolicyFields
    evaluation_adjudication: EvaluationAdjudicationFields
    fault_privacy: FaultPrivacyFields
    frozen_controls: FrozenControls
    runtime_qualification: RuntimeQualification
    route_compatibility: RouteCompatibilityResolution
    cost_scope: CostScope
    source_bindings: tuple[SourceBinding, ...]
    custody: CustodyPolicy
    safety_state: SafetyState
    next_gate: Literal["BIND_FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_V1"]

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        observed = required_field_names(self)
        if observed != REQUIRED_FIELD_NAMES:
            raise ValueError("final manifest required-field coverage or order drifted")
        expected_bindings = tuple(EXPECTED_GIT_BLOBS)
        observed_bindings = tuple(item.path for item in self.source_bindings)
        if observed_bindings != expected_bindings:
            raise ValueError("final manifest source-binding set or order drifted")
        if self.identity.execution_manifest_hash != semantic_manifest_sha256(self):
            raise ValueError("final manifest semantic SHA-256 does not match payload")
        expected_route_hash = sha256_bytes(
            canonical_json_bytes(self.route_compatibility.model_dump(mode="json"))
        )
        if self.route_policy.capability_calibration_report_hash != expected_route_hash:
            raise ValueError("route compatibility hash does not match embedded resolution")
        return self


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_semantic_payload(value: Final342ExecutionManifest) -> dict[str, object]:
    payload = value.model_dump(mode="json")
    identity = cast(dict[str, object], payload["identity"])
    identity.pop("execution_manifest_hash")
    return cast(dict[str, object], payload)


def semantic_manifest_sha256(value: Final342ExecutionManifest) -> str:
    return sha256_bytes(canonical_json_bytes(_manifest_semantic_payload(value)))


def _semantic_sha256_from_payload(payload: dict[str, object]) -> str:
    copied = json.loads(json.dumps(payload))
    identity = cast(dict[str, object], copied["identity"])
    identity.pop("execution_manifest_hash")
    return sha256_bytes(canonical_json_bytes(copied))


def required_field_names(value: Final342ExecutionManifest) -> tuple[str, ...]:
    sections = (
        value.identity,
        value.corpus_retrieval,
        value.context_contract,
        value.provider_telemetry,
        value.route_policy,
        value.evaluation_adjudication,
        value.fault_privacy,
        value.frozen_controls,
    )
    return tuple(field for section in sections for field in section.__class__.model_fields)


def _read_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_REQUIRED_FILE_MISSING",
            "required manifest-freeze input is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _read_object(root: Path, relative: Path) -> dict[str, object]:
    try:
        value = json.loads(_read_bytes(root, relative))
    except json.JSONDecodeError as error:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_JSON_INVALID",
            "required manifest-freeze JSON is invalid",
            relative,
        ) from error
    if not isinstance(value, dict):
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_JSON_ROOT_INVALID",
            "required manifest-freeze JSON root must be one object",
            relative,
        )
    return cast(dict[str, object], value)


def _git_blob_sha(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_BOUND_SOURCE_MISSING",
            "manifest-bound source is missing or unsafe",
            Path(relative),
        )
    completed = subprocess.run(
        ["git", "hash-object", "--", relative],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_GIT_HASH_FAILED",
            "unable to hash manifest-bound source",
            Path(relative),
        )
    return completed.stdout.strip()


def _require_source_subject(root: Path, *, exact: bool) -> None:
    command = ["git", "rev-parse", "HEAD"]
    if not exact:
        command = [
            "git",
            "merge-base",
            "--is-ancestor",
            SOURCE_SUBJECT_COMMIT,
            "HEAD",
        ]
    completed = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if exact:
        if completed.returncode != 0 or completed.stdout.strip() != SOURCE_SUBJECT_COMMIT:
            raise ManifestFreezeError(
                "FINAL_342_MANIFEST_SOURCE_SUBJECT_DRIFT",
                "manifest materialization must begin from exact accepted source subject",
            )
    elif completed.returncode != 0:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_SOURCE_SUBJECT_MISSING",
            "accepted source-subject commit is not an ancestor of HEAD",
        )


def _validate_source_bindings(root: Path) -> None:
    for relative, expected in EXPECTED_GIT_BLOBS.items():
        if _git_blob_sha(root, relative) != expected:
            raise ManifestFreezeError(
                "FINAL_342_MANIFEST_SOURCE_IDENTITY_DRIFT",
                f"manifest-bound source identity drifted: {relative}",
                Path(relative),
            )


def _require_mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_UPSTREAM_SHAPE_INVALID",
            f"required upstream section is invalid: {name}",
        )
    return cast(dict[str, object], value)


def _validate_requirements_inventory(root: Path) -> None:
    text = _read_bytes(root, REQUIREMENTS_PATH).decode("utf-8")
    missing = tuple(field for field in REQUIRED_FIELD_NAMES if field not in text)
    if missing:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_REQUIREMENT_FIELD_MISSING",
            f"execution-manifest requirement inventory drifted: {missing[0]}",
            REQUIREMENTS_PATH,
        )
    if len(REQUIRED_FIELD_NAMES) != 69 or len(set(REQUIRED_FIELD_NAMES)) != 69:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_REQUIREMENT_COUNT_INVALID",
            "final manifest must cover exactly 69 unique required fields",
        )


def _validate_precedence_and_custody(root: Path) -> None:
    record = _read_object(root, G11_3A_RECORD_PATH)
    commit_binding = _require_mapping(record.get("commit_binding"), "commit_binding")
    expected = {
        "first_containing_commit_stored_inside_same_manifest": False,
        "post_commit_custody_receipt_required": True,
        "receipt_binds_manifest_sha256": True,
        "receipt_binds_manifest_file_sha256": True,
        "receipt_binds_source_subject_commit": True,
        "receipt_binds_first_containing_commit": True,
        "g11_freeze_gate_promoted_before_receipt": False,
    }
    if any(commit_binding.get(key) != value for key, value in expected.items()):
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_GIT_CUSTODY_DRIFT",
            "accepted acyclic Git-custody contract drifted",
            G11_3A_RECORD_PATH,
        )


def _validate_final_runtime_inputs(root: Path) -> None:
    if sha256_bytes(_read_bytes(root, RUNTIME_LOCK_PATH)) != EXPECTED_RUNTIME_LOCK_SHA256:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_RUNTIME_LOCK_DRIFT",
            "exact-runtime dependency lock SHA-256 drifted",
            RUNTIME_LOCK_PATH,
        )

    runtime_source = _read_bytes(root, EXACT_RUNTIME_PATH).decode("utf-8")
    required_markers = (
        'MODEL_REPOSITORY = "Qwen/Qwen2.5-0.5B-Instruct"',
        'MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"',
        'EXPECTED_VLLM_DISTRIBUTION_VERSION = "0.25.1+cu129"',
        'EXPECTED_TORCH_VERSION = "2.11.0+cu129"',
        'EXPECTED_TORCH_CUDA = "12.9"',
        'EXPECTED_TRITON_VERSION = "3.6.0"',
        'EXPECTED_TRANSFORMERS_VERSION = "5.14.1"',
        'EXPECTED_GPU_NAME = "Tesla T4"',
        'EXPECTED_COMPUTE_CAPABILITY = "7.5"',
        'EXPECTED_BACKEND = "TRITON_ATTN"',
        'TARGET_SITE = TARGET_ROOT / "lib" / "python3.12" / "site-packages"',
    )
    missing = tuple(marker for marker in required_markers if marker not in runtime_source)
    if missing:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_RUNTIME_CONTRACT_DRIFT",
            f"exact-runtime contract marker drifted: {missing[0]}",
            EXACT_RUNTIME_PATH,
        )

    fingerprints = _read_object(root, CONDITION_FINGERPRINTS_PATH)
    if fingerprints.get("pricing_fields_present") is not False:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_PRICING_SCOPE_DRIFT",
            "preflight condition fingerprints unexpectedly contain pricing authority",
            CONDITION_FINGERPRINTS_PATH,
        )
    if fingerprints.get("provider_fields_present") is not False:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_PROVIDER_SCOPE_DRIFT",
            "preflight condition fingerprints unexpectedly contain hosted-provider authority",
            CONDITION_FINGERPRINTS_PATH,
        )
    records = fingerprints.get("records")
    if not isinstance(records, list) or len(records) != 3:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_CONDITION_FINGERPRINTS_INVALID",
            "condition fingerprints must contain exactly A/B/C records",
            CONDITION_FINGERPRINTS_PATH,
        )


def _validate_population_and_statistics(root: Path) -> None:
    ledger = _read_object(root, PLANNED_LEDGER_PATH)
    if ledger.get("total_trajectory_count") != 342:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_LEDGER_COUNT_DRIFT",
            "frozen planned-run trajectory count drifted",
            PLANNED_LEDGER_PATH,
        )
    if ledger.get("total_turn_count") != 1368:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_LEDGER_TURN_COUNT_DRIFT",
            "frozen planned-run turn count drifted",
            PLANNED_LEDGER_PATH,
        )
    if ledger.get("execution_enabled") is not False:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_LEDGER_AUTHORITY_DRIFT",
            "frozen planning ledger unexpectedly enables execution",
            PLANNED_LEDGER_PATH,
        )

    g10 = _read_object(root, G10_PATH)
    if g10.get("total_scheduled_trajectory_count") != 342:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_G10_COUNT_DRIFT",
            "G10 trajectory denominator drifted",
            G10_PATH,
        )
    if g10.get("total_scheduled_turn_count") != 1368:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_G10_TURN_DRIFT",
            "G10 turn denominator drifted",
            G10_PATH,
        )
    endpoint = _require_mapping(g10.get("primary_runtime_endpoint"), "primary_runtime_endpoint")
    if endpoint.get("metric_id") != "warm-eligible-newly-computed-prefill-tokens-v1":
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_G10_ENDPOINT_DRIFT",
            "G10 primary runtime endpoint drifted",
            G10_PATH,
        )


def _validate_offline_rehearsal(root: Path) -> None:
    record = _read_object(root, REHEARSAL_RECORD_PATH)
    safety = _require_mapping(record.get("safety_state"), "rehearsal.safety_state")
    if record.get("next_gate") != "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1":
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_REHEARSAL_GATE_DRIFT",
            "accepted offline rehearsal no longer points to manifest freeze",
            REHEARSAL_RECORD_PATH,
        )
    expected_false = (
        "model_requests_performed",
        "gpu_execution_performed",
        "kaggle_execution_performed",
        "network_transport_performed",
        "execution_manifest_frozen",
        "manifest_freeze_permitted",
        "live_authorization_issued",
        "final_measured_abc_execution_authorized",
        "new_execution_authorized",
        "effect_claims_permitted",
    )
    for key in expected_false:
        expected: object = 0 if key == "model_requests_performed" else False
        if safety.get(key) != expected:
            raise ManifestFreezeError(
                "FINAL_342_MANIFEST_REHEARSAL_SAFETY_DRIFT",
                f"offline rehearsal safety boundary drifted: {key}",
                REHEARSAL_RECORD_PATH,
            )


def _validate_review_schedule(root: Path) -> None:
    record = _read_object(root, REVIEW_RECORD_PATH)
    schedule = _require_mapping(record.get("secondary_schedule"), "secondary_schedule")
    if schedule.get("schedule_sha256") != EXPECTED_REVIEW_SCHEDULE_SHA256:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_REVIEW_SCHEDULE_DRIFT",
            "final protected review schedule identity drifted",
            REVIEW_RECORD_PATH,
        )
    if schedule.get("final_manifest_must_bind_schedule_sha256") is not True:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_REVIEW_BINDING_DRIFT",
            "review successor no longer requires final-manifest schedule binding",
            REVIEW_RECORD_PATH,
        )


def validate_preconditions(root: Path) -> None:
    _validate_source_bindings(root)
    _validate_requirements_inventory(root)
    _validate_precedence_and_custody(root)
    _validate_final_runtime_inputs(root)
    _validate_population_and_statistics(root)
    _validate_offline_rehearsal(root)
    _validate_review_schedule(root)


def _route_compatibility() -> RouteCompatibilityResolution:
    return RouteCompatibilityResolution(
        compatibility_id="final-342-local-worker-route-compatibility-v1",
        single_local_model_alias="local-qwen2.5-0.5b-instruct",
        turn_local_route_schedule_id="turn-local-worker1-worker2-v1",
        affinity_route_schedule_id="affinity-worker1-worker1-v1",
    )


def _base_payload() -> dict[str, object]:
    route_compatibility = _route_compatibility()
    route_compatibility_hash = sha256_bytes(
        canonical_json_bytes(route_compatibility.model_dump(mode="json"))
    )
    return {
        "schema_version": "1.0.0",
        "manifest_id": "auragateway-final-342-execution-manifest-v1",
        "manifest_status": "FROZEN_SUBJECT_PENDING_POST_COMMIT_CUSTODY",
        "identity": {
            "execution_manifest_version": "1.0.0",
            "execution_manifest_hash": "0" * 64,
            "benchmark_constitution_version": "1.0.0",
            "benchmark_constitution_hash": (
                "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
            ),
            "benchmark_runner_version": "auragateway-final-342-execution-producer-v1",
            "comparison_eligibility_contract_version": "comparison-eligibility-v1",
            "evidence_bundle_schema_version": "1.0.0",
            "git_commit_hash": "POST_COMMIT_CUSTODY_RECEIPT_REQUIRED",
            "python_version": "CPython-3.12-cp312",
            "dependency_lock_hash": EXPECTED_RUNTIME_LOCK_SHA256,
        },
        "corpus_retrieval": {
            "corpus_manifest_hash": (
                "c68212afd5381dec8bce49d0d5fee231a3b5589bf5460c0f72297e0c84422f55"
            ),
            "chunking_strategy_id": "section-aware-v1",
            "chunking_configuration_hash": (
                "bee67067af933b17a58b9221f8efdea10837bde1cd8b7969fe25ff92051601d2"
            ),
            "retrieval_implementation_id": ("dense-hashed-tfidf-section-aware-remediated-v2"),
            "retrieval_configuration_hash": (
                "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"
            ),
            "retrieval_type": "dense_hashed_tfidf",
            "top_k": 5,
            "metadata_filter_policy_version": "authored-case-filters-v1",
            "development_retrieval_manifest_hash": (
                "fce8d7ac8f6f11f3a48891040810b1c37a8b3c186eda85caec41f75791dc4dd5"
            ),
            "held_out_retrieval_manifest_hash": (
                "6d2c454a8e2b99cfef55f45c177944154aa09c76d4826cfd83035f0439a0820f"
            ),
            "retrieval_scorecard_hash": (
                "c10cc5025139f0118a9e07e9b1960f99c9c7ead4115e67d7ffa000c4817b9734"
            ),
        },
        "context_contract": {
            "prompt_template_id": "nimbus-relay-support-template-v1",
            "prompt_template_version": "1.0.0",
            "static_context_pack_id": "nimbus-relay-static-context-v1",
            "static_context_pack_version": "1.0.0",
            "serialization_version": "canonical-static-provider-v1",
            "tool_contract_version": "tool-contract-v1",
            "output_schema_version": "terminal-decision-v1",
            "prefix_fingerprint_contract_version": "hmac-sha256-static-prefix-v1",
        },
        "provider_telemetry": {
            "primary_provider": "local_vllm",
            "provider_model_alias": "local-qwen2.5-0.5b-instruct",
            "exact_model_identifier": (
                "Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775"
            ),
            "provider_adapter_version": "final-342-loopback-vllm-transport-v1",
            "provider_documentation_date_checked": ("NOT_APPLICABLE_LOCAL_RUNTIME_ARTIFACT_BOUND"),
            "telemetry_rules_version": "final-342-turn-measurement-v1",
            "telemetry_fixture_manifest_hash": (
                "3a3bcb5296cb23f65bf4399ea2723ecb67323a8f49d1d7b2389fd334f9397e8b"
            ),
            "cache_ttl_assumption_seconds": 300,
            "cache_ttl_source": "benchmark-assumption-v1",
            "pricing_schedule_version": "NOT_APPLICABLE_MONETARY_COST_OUT_OF_SCOPE",
            "pricing_source_date": "NOT_APPLICABLE_MONETARY_COST_OUT_OF_SCOPE",
            "currency": "NONE",
        },
        "route_policy": {
            "route_policy_version": "final-342-worker-route-realization-v1",
            "economy_model_alias": "local-qwen2.5-0.5b-instruct",
            "capable_model_alias": "local-qwen2.5-0.5b-instruct",
            "capability_calibration_report_hash": route_compatibility_hash,
            "route_ttl_policy_version": "final-342-warm-eligibility-v1",
            "provider_failure_policy_version": "provider-request-policy-v1",
        },
        "evaluation_adjudication": {
            "diagnostic_episode_manifest_hash": (
                "3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b"
            ),
            "functional_benchmark_manifest_hash": (
                "6229df94a6a426f815a2050172a79e115d9554031239043b397140ce13894285"
            ),
            "runtime_microbenchmark_manifest_hash": (
                "5ff912ad317fe09d97518e5b03178ebe3bb565dcf09719182bfffc80b67034e1"
            ),
            "quality_rubric_version": "auragateway-quality-rubric-v1",
            "quality_rubric_hash": (
                "7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"
            ),
            "blinded_adjudication_protocol_version": "blinded-adjudication-v1",
            "review_sample_schedule_hash": EXPECTED_REVIEW_SCHEDULE_SHA256,
            "feedback_evidence_contract_version": "efc-evidence-v1",
        },
        "fault_privacy": {
            "negative_control_manifest_hash": (
                "7e9da92957fdc04dfffeb423094e6a7b0868a7ffe3139509b27a7186c9b1ac86"
            ),
            "fault_injection_fixture_hash": (
                "257b6f8a142b103ebe22f53086e7674f13af80fa5a8e397737406cbacd3f65aa"
            ),
            "privacy_trace_contract_version": "privacy-safe-observability-v1",
            "privacy_verification_report_hash": (
                "de0025974cc9cbc0faaecbca13a419f7807b1870e9cd7a596460bb943736ab91"
            ),
            "cross_condition_isolation_test_hash": (
                "1804921fb379a458b9b034e27f7d791dbe6c62a3b0b9860bd97068e53be635b3"
            ),
        },
        "frozen_controls": {
            "functional_run_order_schedule_id": "functional-counterbalance-v1",
            "runtime_run_order_schedule_id": "runtime-counterbalance-v1",
            "timeout_policy_id": "provider-request-policy-v1",
            "retry_policy_id": "provider-request-policy-v1",
            "exclusion_policy_id": "exclusion-policy-v1",
            "rerun_policy_id": "rerun-policy-v1",
            "denominator_policy_id": "denominator-policy-v1",
            "statistical_reporting_configuration_id": "paired-bootstrap-v1",
            "quality_non_inferiority_policy_id": "quality-non-inferiority-v1",
        },
        "runtime_qualification": {
            "environment": "kaggle_t4_x2",
            "execution_backend": "local_vllm",
            "python_abi": "cp312",
            "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
            "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "served_model_alias": "local-qwen2.5-0.5b-instruct",
            "vllm_distribution_version": "0.25.1+cu129",
            "torch_version": "2.11.0+cu129",
            "torch_cuda_version": "12.9",
            "triton_version": "3.6.0",
            "transformers_version": "5.14.1",
            "gpu_model": "Tesla T4",
            "compute_capability": "7.5",
            "attention_backend": "TRITON_ATTN",
            "transport_endpoint": "/v1/chat/completions",
            "requirements_lock_sha256": EXPECTED_RUNTIME_LOCK_SHA256,
        },
        "route_compatibility": route_compatibility.model_dump(mode="json"),
        "cost_scope": CostScope().model_dump(mode="json"),
        "source_bindings": [
            {"path": path, "git_blob_sha": sha} for path, sha in EXPECTED_GIT_BLOBS.items()
        ],
        "custody": CustodyPolicy(source_subject_commit=SOURCE_SUBJECT_COMMIT).model_dump(
            mode="json"
        ),
        "safety_state": SafetyState().model_dump(mode="json"),
        "next_gate": NEXT_GATE,
    }


def build_manifest(root: Path) -> Final342ExecutionManifest:
    validate_preconditions(root.resolve())
    payload = _base_payload()
    identity = cast(dict[str, object], payload["identity"])
    identity["execution_manifest_hash"] = _semantic_sha256_from_payload(payload)
    return Final342ExecutionManifest.model_validate(payload)


def manifest_bytes(value: Final342ExecutionManifest) -> bytes:
    return canonical_json_bytes(value.model_dump(mode="json"))


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.final-342-freeze.tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    temporary.replace(path)


def materialize(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_source_subject(root, exact=True)
    manifest = build_manifest(root)
    _write_atomic(root / MANIFEST_PATH, manifest_bytes(manifest))
    return validate(root)


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_source_subject(root, exact=False)
    expected = build_manifest(root)
    try:
        observed = Final342ExecutionManifest.model_validate_json(_read_bytes(root, MANIFEST_PATH))
    except ValidationError as error:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_FILE_INVALID",
            "final execution manifest failed typed validation",
            MANIFEST_PATH,
        ) from error

    if observed != expected:
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_FILE_DRIFT",
            "final execution manifest differs from deterministic reconstruction",
            MANIFEST_PATH,
        )
    if manifest_bytes(observed) != _read_bytes(root, MANIFEST_PATH):
        raise ManifestFreezeError(
            "FINAL_342_MANIFEST_CANONICAL_BYTES_DRIFT",
            "final execution manifest bytes are not canonical",
            MANIFEST_PATH,
        )

    return {
        "status": "FINAL_342_EXECUTION_MANIFEST_FROZEN_SUBJECT_V1_VALID",
        "manifest_id": observed.manifest_id,
        "manifest_semantic_sha256": observed.identity.execution_manifest_hash,
        "manifest_file_sha256": sha256_bytes(_read_bytes(root, MANIFEST_PATH)),
        "required_field_count": len(REQUIRED_FIELD_NAMES),
        "source_subject_commit": SOURCE_SUBJECT_COMMIT,
        "manifest_subject_bytes_frozen": True,
        "post_commit_custody_receipt_required": True,
        "repository_execution_manifest_frozen": False,
        "repository_freeze_gate_promoted": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "network_transport_performed": False,
        "live_authorization_issued": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _Parser:
    parser = _Parser(prog="final-342-execution-manifest-freeze-v1")
    parser.add_argument("command", choices=("materialize", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = (
            materialize(args.repo_root)
            if args.command == "materialize"
            else validate(args.repo_root)
        )
    except (ManifestFreezeError, OSError, UnicodeDecodeError, ValueError) as error:
        if isinstance(error, ManifestFreezeError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path.as_posix() if error.path is not None else None,
            }
        else:
            payload = {
                "error_code": "FINAL_342_MANIFEST_FREEZE_FAILED",
                "safe_message": str(error),
                "path": None,
            }
        print(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
