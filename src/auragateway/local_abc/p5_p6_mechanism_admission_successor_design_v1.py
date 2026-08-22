"""Design the exact-runtime P5/P6 mechanism-admission successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "f534a27d3e07fc699c7fb1e4e257730cc71590f4"

V2_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_implementation_record.json"
)
V2_SOURCE_PATH: Final = Path("src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v2.py")
V2_SOURCE_SHA256: Final = "5a91268ff616bf925bba5e0eafc80be4353f40e97ed5d5b01ea5c0a8feed50d6"
V2_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v2.py.tmpl"
)
V2_TEMPLATE_SHA256: Final = "5af0c62de986c332a95ed5a97be14e35418448d9ad1427bc6321749765a2d48c"
V2_TEST_PATH: Final = Path("tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v2.py")
V2_TEST_SHA256: Final = "71091e28c2a3130f06e561625cb422e239f91fb0d4213c26908d3b4e1f9be827"

C4_CONTRACT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_contract_v2.json"
)
C4_CONTRACT_SHA256: Final = "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
C4_ASSESSMENT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_assessment_v1.json"
)
C4_ASSESSMENT_SHA256: Final = "19e0ea9033151336df6534e87d9e75aa50649aec5a833d5d5d9307550836bd06"
C4_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_assessment_v1_review.json"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_design_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_design_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-design-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Successor_Design_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_mechanism_admission_successor_design_v1.md"
)
DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1_review.json"
)

STATIC_PATHS: Final = (
    SOURCE_PATH,
    TEST_PATH,
    ADR_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
)
GENERATED_PATHS: Final = (
    DESIGN_PATH,
    REVIEW_PATH,
)
CANDIDATE_PATHS: Final = tuple(sorted((*STATIC_PATHS, *GENERATED_PATHS)))

NEXT_GATE: Final = "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
NEW_AUTHORIZATION_SCOPE: Final = "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"


class DesignError(RuntimeError):
    """Fail-closed design-generation error."""

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
        raise DesignError("P5_P6_MECHANISM_DESIGN_ARGUMENT_ERROR", message)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.model_dump(mode="json"))


class SemanticObservationState(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    VALID_JSON_MISMATCH = "VALID_JSON_MISMATCH"
    NON_OBJECT_JSON = "NON_OBJECT_JSON"
    INVALID_JSON = "INVALID_JSON"


class AuthorityBinding(_StrictModel):
    authority_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    identity_kind: Literal["SHA256"]
    identity: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
    role: Literal["CURRENT", "PREDECESSOR"]


class RuntimeLineage(_StrictModel):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
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


class SemanticBoundary(_StrictModel):
    states: tuple[
        Literal["EXACT_MATCH"],
        Literal["VALID_JSON_MISMATCH"],
        Literal["NON_OBJECT_JSON"],
        Literal["INVALID_JSON"],
    ] = (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    exact_object_match_blocks_mechanism: Literal[False] = False
    valid_json_blocks_mechanism: Literal[False] = False
    semantic_parser_may_raise_on_model_content: Literal[False] = False
    raw_output_logging_permitted: Literal[False] = False
    output_digest_required: Literal[True] = True
    semantic_state_required: Literal[True] = True


class MechanismAdmissionBoundary(_StrictModel):
    http_success_required: Literal[True] = True
    response_envelope_required: Literal[True] = True
    finish_reason_stop_required: Literal[True] = True
    prompt_token_count_required: Literal[True] = True
    completion_token_budget_required: Literal[True] = True
    request_identity_required: Literal[True] = True
    token_identity_required: Literal[True] = True
    metric_window_required: Literal[True] = True
    output_provenance_required: Literal[True] = True
    hidden_retries_required_zero: Literal[True] = True
    worker_identity_required: Literal[True] = True
    teardown_required: Literal[True] = True


class P5ProofBoundary(_StrictModel):
    semantic_state_used_as_cache_proof: Literal[False] = False
    latency_as_primary_proof_permitted: Literal[False] = False
    cold_zero_local_cache_hit_required: Literal[True] = True
    warm_positive_local_cache_hit_required: Literal[True] = True
    warm_positive_prefix_cache_hit_required: Literal[True] = True
    warm_less_local_compute_than_cold_required: Literal[True] = True
    negative_prefix_bound_required: Literal[True] = True
    post_reset_zero_local_cache_hit_required: Literal[True] = True
    cross_worker_zero_inherited_cache_required: Literal[True] = True
    external_kv_transfer_zero_required: Literal[True] = True


class P6ProofBoundary(_StrictModel):
    model_semantics_used_as_route_proof: Literal[False] = False
    disjoint_process_trees_required: Literal[True] = True
    intended_gpu_realization_required: Literal[True] = True
    route_metric_window_attribution_required: Literal[True] = True
    no_hidden_fallback_required: Literal[True] = True
    cross_worker_cold_state_required: Literal[True] = True
    worker_1_retention_required: Literal[True] = True
    request_count_reconciliation_required: Literal[True] = True
    teardown_required: Literal[True] = True


class ImplementationChange(_StrictModel):
    change_id: str = Field(min_length=1)
    target: str = Field(min_length=1)
    change_type: Literal["REPLACE_FUNCTION", "ADD_TYPED_MODEL", "UPDATE_CALL_FLOW"]
    requirement: str = Field(min_length=20)
    downstream_effects: tuple[str, ...] = Field(min_length=1)


class AuthorizationBoundary(_StrictModel):
    predecessor_v2_authorization_reusable: Literal[False] = False
    new_scope_required: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"] = (
        "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
    )
    implementation_issues_authorization: Literal[False] = False
    design_issues_authorization: Literal[False] = False
    single_use_required: Literal[True] = True
    hidden_retries_permitted: Literal[0] = 0


class SuccessorDesign(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    design_id: Literal["auragateway-p5-p6-mechanism-admission-successor-design-v1"]
    base_main_commit: Literal["f534a27d3e07fc699c7fb1e4e257730cc71590f4"]
    decision: Literal["IMPLEMENT_V3_FROM_EXACT_RUNTIME_V2_WITH_SEMANTIC_MECHANISM_SEPARATION"]
    authorities: tuple[AuthorityBinding, ...]
    runtime: RuntimeLineage
    semantic_boundary: SemanticBoundary
    mechanism_boundary: MechanismAdmissionBoundary
    p5_boundary: P5ProofBoundary
    p6_boundary: P6ProofBoundary
    implementation_changes: tuple[ImplementationChange, ...]
    authorization: AuthorizationBoundary
    c4_semantic_state: Literal["NOT_QUALIFIED"] = "NOT_QUALIFIED"
    c4_mechanism_admission: Literal["QUALIFIED"] = "QUALIFIED"
    p5_requalified: Literal[False] = False
    p6_requalified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    next_gate: Literal["IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_boundary_separation(self) -> Self:
        if self.semantic_boundary.exact_object_match_blocks_mechanism:
            raise ValueError("semantic equality cannot block mechanism evidence")
        if self.semantic_boundary.valid_json_blocks_mechanism:
            raise ValueError("JSON validity cannot block mechanism evidence")
        if self.p5_boundary.semantic_state_used_as_cache_proof:
            raise ValueError("semantic state cannot become P5 cache proof")
        if self.p6_boundary.model_semantics_used_as_route_proof:
            raise ValueError("model semantics cannot become P6 route proof")
        return self


class StaticReceipt(_StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class DesignReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p5-p6-mechanism-admission-successor-design-v1-review"]
    status: Literal["APPROVED_FOR_IMPLEMENTATION"]
    design_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    static_artifacts: tuple[StaticReceipt, ...]
    predecessor_v2_identity_valid: Literal[True]
    c4_mechanism_authority_valid: Literal[True]
    semantic_mechanism_boundary_separated: Literal[True]
    p5_acceptance_relaxed: Literal[False] = False
    p6_acceptance_relaxed: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal["IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]


class GeneratedArtifacts(_StrictModel):
    design: SuccessorDesign
    review: DesignReview


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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(repo_root: Path, path: Path) -> bytes:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_INPUT_MISSING",
            "required design input is missing or unsafe",
            path.as_posix(),
        )
    return absolute.read_bytes()


def _read_json(repo_root: Path, path: Path) -> dict[str, object]:
    payload = json.loads(_read_bytes(repo_root, path))
    if not isinstance(payload, dict):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_INPUT_INVALID",
            "required design input root is not one object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _require_sha256(repo_root: Path, path: Path, expected: str) -> bytes:
    payload = _read_bytes(repo_root, path)
    if _sha256_bytes(payload) != expected:
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_IDENTITY_DRIFT",
            "required SHA-256 authority identity drifted",
            path.as_posix(),
        )
    return payload


def _validate_v2_predecessor(repo_root: Path) -> None:
    record = _read_json(repo_root, V2_RECORD_PATH)
    if not isinstance(record, dict):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_V2_RECORD_INVALID",
            "V2 implementation record root is invalid",
            V2_RECORD_PATH.as_posix(),
        )
    if record.get("status") != "IMPLEMENTED_NOT_EXECUTED":
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_V2_RECORD_DRIFT",
            "V2 implementation status drifted",
            V2_RECORD_PATH.as_posix(),
        )
    if record.get("behavioral_core_preserved") is not True:
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_V2_RECORD_DRIFT",
            "V2 behavioral-core preservation is not established",
            V2_RECORD_PATH.as_posix(),
        )
    safety = record.get("safety")
    if not isinstance(safety, dict):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_V2_RECORD_INVALID",
            "V2 safety record is invalid",
            V2_RECORD_PATH.as_posix(),
        )
    if (
        safety.get("runtime_execution_authorized") is not False
        or safety.get("model_requests_performed") != 0
        or safety.get("gpu_execution_performed") is not False
        or safety.get("kaggle_execution_performed") is not False
    ):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_V2_SAFETY_DRIFT",
            "V2 implementation safety boundary drifted",
            V2_RECORD_PATH.as_posix(),
        )
    runtime = record.get("runtime")
    expected_runtime = RuntimeLineage().model_dump(mode="json")
    if not isinstance(runtime, dict):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_V2_RUNTIME_INVALID",
            "V2 runtime record is invalid",
            V2_RECORD_PATH.as_posix(),
        )
    for key, value in expected_runtime.items():
        if runtime.get(key) != value:
            raise DesignError(
                "P5_P6_MECHANISM_DESIGN_V2_RUNTIME_DRIFT",
                f"V2 runtime identity drifted: {key}",
                V2_RECORD_PATH.as_posix(),
            )
    for path, expected_sha in (
        (V2_SOURCE_PATH, V2_SOURCE_SHA256),
        (V2_TEMPLATE_PATH, V2_TEMPLATE_SHA256),
        (V2_TEST_PATH, V2_TEST_SHA256),
    ):
        _require_sha256(repo_root, path, expected_sha)


def _validate_c4_mechanism_authority(repo_root: Path) -> None:
    contract_bytes = _require_sha256(
        repo_root,
        C4_CONTRACT_PATH,
        C4_CONTRACT_SHA256,
    )
    assessment_bytes = _require_sha256(
        repo_root,
        C4_ASSESSMENT_PATH,
        C4_ASSESSMENT_SHA256,
    )
    review = _read_json(repo_root, C4_REVIEW_PATH)
    contract = json.loads(contract_bytes)
    assessment = json.loads(assessment_bytes)
    if not all(isinstance(item, dict) for item in (contract, assessment, review)):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_C4_AUTHORITY_INVALID",
            "C4 mechanism authority root is invalid",
        )
    contract = cast(dict[str, object], contract)
    assessment = cast(dict[str, object], assessment)
    if (
        contract.get("semantic_exact_object_blocking") is not False
        or contract.get("valid_json_blocking") is not False
        or contract.get("model_semantics_permitted_as_p6_route_proof") is not False
        or contract.get("new_execution_authorized") is not False
    ):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_C4_CONTRACT_DRIFT",
            "C4 mechanism-admission contract drifted",
            C4_CONTRACT_PATH.as_posix(),
        )
    semantic = assessment.get("semantic_observation")
    mechanism = assessment.get("mechanism_decision")
    if not isinstance(semantic, dict) or not isinstance(mechanism, dict):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_C4_ASSESSMENT_INVALID",
            "C4 assessment boundary is invalid",
            C4_ASSESSMENT_PATH.as_posix(),
        )
    if (
        semantic.get("state") != "NOT_QUALIFIED"
        or mechanism.get("state") != "QUALIFIED"
        or assessment.get("p5_requalified") is not False
        or assessment.get("p6_requalified") is not False
        or assessment.get("new_execution_authorized") is not False
    ):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_C4_ASSESSMENT_DRIFT",
            "C4 assessment scientific state drifted",
            C4_ASSESSMENT_PATH.as_posix(),
        )
    if (
        review.get("contract_sha256") != C4_CONTRACT_SHA256
        or review.get("assessment_sha256") != C4_ASSESSMENT_SHA256
        or review.get("semantic_c4_state") != "NOT_QUALIFIED"
        or review.get("mechanism_admission_state") != "QUALIFIED"
        or review.get("new_execution_authorized") is not False
    ):
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_C4_REVIEW_DRIFT",
            "C4 mechanism-admission review binding drifted",
            C4_REVIEW_PATH.as_posix(),
        )


def _authorities() -> tuple[AuthorityBinding, ...]:
    return (
        AuthorityBinding(
            authority_id="exact_runtime_p5_p6_v2_source",
            path=V2_SOURCE_PATH.as_posix(),
            identity_kind="SHA256",
            identity=V2_SOURCE_SHA256,
            role="PREDECESSOR",
        ),
        AuthorityBinding(
            authority_id="exact_runtime_p5_p6_v2_template",
            path=V2_TEMPLATE_PATH.as_posix(),
            identity_kind="SHA256",
            identity=V2_TEMPLATE_SHA256,
            role="PREDECESSOR",
        ),
        AuthorityBinding(
            authority_id="exact_runtime_p5_p6_v2_tests",
            path=V2_TEST_PATH.as_posix(),
            identity_kind="SHA256",
            identity=V2_TEST_SHA256,
            role="PREDECESSOR",
        ),
        AuthorityBinding(
            authority_id="c4_mechanism_admission_contract_v2",
            path=C4_CONTRACT_PATH.as_posix(),
            identity_kind="SHA256",
            identity=C4_CONTRACT_SHA256,
            role="CURRENT",
        ),
        AuthorityBinding(
            authority_id="c4_mechanism_admission_assessment_v1",
            path=C4_ASSESSMENT_PATH.as_posix(),
            identity_kind="SHA256",
            identity=C4_ASSESSMENT_SHA256,
            role="CURRENT",
        ),
    )


def _implementation_changes() -> tuple[ImplementationChange, ...]:
    return (
        ImplementationChange(
            change_id="MC-01",
            target="runtime semantic observation model",
            change_type="ADD_TYPED_MODEL",
            requirement=(
                "Represent exact match, valid JSON mismatch, non-object JSON, and invalid JSON "
                "without raising solely because model semantics differ."
            ),
            downstream_effects=(
                "runtime template hash changes",
                "generated notebook hash changes",
                "implementation review and record hashes change",
                "focused semantic-boundary tests become mandatory",
            ),
        ),
        ImplementationChange(
            change_id="MC-02",
            target="validate_structured_response",
            change_type="REPLACE_FUNCTION",
            requirement=(
                "Replace exception-driven exact-object validation with a total semantic observer "
                "that always returns a typed semantic state for non-empty envelope content."
            ),
            downstream_effects=(
                "run_structured_request no longer aborts on semantic mismatch",
                "C4 semantic result remains independently recordable",
                "P5 metric evidence can survive a semantic negative",
            ),
        ),
        ImplementationChange(
            change_id="MC-03",
            target="run_structured_request",
            change_type="UPDATE_CALL_FLOW",
            requirement=(
                "Keep transport, token identity, usage, finish reason, output provenance, "
                "and metric "
                "window validation blocking while making semantic state diagnostic-only."
            ),
            downstream_effects=(
                "P5 receives mechanism evidence after a semantic mismatch",
                "response finish_reason must be stop before mechanism evidence is admitted",
                "output digest remains retained without raw output logging",
            ),
        ),
        ImplementationChange(
            change_id="MC-04",
            target="P5 and P6 acceptance evaluators",
            change_type="UPDATE_CALL_FLOW",
            requirement=(
                "Prove P5 and P6 decisions consume only their frozen mechanism criteria and never "
                "promote semantic state into cache or route evidence."
            ),
            downstream_effects=(
                "existing cache and route proof criteria remain unchanged",
                "regression tests must inject wrong semantic output with healthy "
                "mechanism evidence",
                "transport and metric ambiguity continue to fail closed",
            ),
        ),
        ImplementationChange(
            change_id="MC-05",
            target="execution authorization boundary",
            change_type="UPDATE_CALL_FLOW",
            requirement=(
                "Require a fresh V3 authorization scope and reject reuse of any V2 authorization "
                "for the successor runtime."
            ),
            downstream_effects=(
                "V3 implementation remains non-executable until a separate issuer is designed",
                "V2 single-use authority cannot silently authorize changed runtime bytes",
            ),
        ),
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "The successor runtime has not been implemented by this design tranche.",
        "The successor runtime has not been executed.",
        "C4 semantic qualification remains NOT_QUALIFIED.",
        "Mechanism admission does not establish P5 cache reuse.",
        "Mechanism admission does not establish P6 route or state isolation.",
        "No variance-pilot result is established.",
        "No final measured A/B/C result is established.",
        "No quality non-inferiority result is established.",
        "No execution authorization is created.",
        "No production-readiness claim is established.",
    )


def build_design(repo_root: Path) -> SuccessorDesign:
    _validate_v2_predecessor(repo_root)
    _validate_c4_mechanism_authority(repo_root)
    return SuccessorDesign(
        design_id="auragateway-p5-p6-mechanism-admission-successor-design-v1",
        base_main_commit=BASE_MAIN_COMMIT,
        decision=("IMPLEMENT_V3_FROM_EXACT_RUNTIME_V2_WITH_SEMANTIC_MECHANISM_SEPARATION"),
        authorities=_authorities(),
        runtime=RuntimeLineage(),
        semantic_boundary=SemanticBoundary(),
        mechanism_boundary=MechanismAdmissionBoundary(),
        p5_boundary=P5ProofBoundary(),
        p6_boundary=P6ProofBoundary(),
        implementation_changes=_implementation_changes(),
        authorization=AuthorizationBoundary(),
        next_gate=NEXT_GATE,
        non_claims=_non_claims(),
    )


def _static_receipt(repo_root: Path, path: Path) -> StaticReceipt:
    payload = _read_bytes(repo_root, path)
    return StaticReceipt(
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def build_generated(repo_root: Path) -> GeneratedArtifacts:
    design = build_design(repo_root)
    design_bytes = design.canonical_bytes()
    receipts = tuple(_static_receipt(repo_root, path) for path in STATIC_PATHS)
    review = DesignReview(
        review_id=("auragateway-p5-p6-mechanism-admission-successor-design-v1-review"),
        status="APPROVED_FOR_IMPLEMENTATION",
        design_sha256=_sha256_bytes(design_bytes),
        static_artifacts=receipts,
        predecessor_v2_identity_valid=True,
        c4_mechanism_authority_valid=True,
        semantic_mechanism_boundary_separated=True,
        next_gate=NEXT_GATE,
    )
    return GeneratedArtifacts(design=design, review=review)


def _generated_bytes(generated: GeneratedArtifacts) -> dict[Path, bytes]:
    return {
        DESIGN_PATH: generated.design.canonical_bytes(),
        REVIEW_PATH: generated.review.canonical_bytes(),
    }


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise DesignError(
            "P5_P6_MECHANISM_DESIGN_TEMPORARY_PATH_EXISTS",
            "temporary generated-artifact path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    temporary.replace(path)


def generate(repo_root: Path) -> GeneratedArtifacts:
    generated = build_generated(repo_root)
    for relative, payload in _generated_bytes(generated).items():
        _write_atomic(repo_root / relative, payload)
    return generated


def validate(repo_root: Path) -> GeneratedArtifacts:
    generated = build_generated(repo_root)
    for relative, expected in _generated_bytes(generated).items():
        observed = _read_bytes(repo_root, relative)
        if observed != expected:
            raise DesignError(
                "P5_P6_MECHANISM_DESIGN_GENERATED_DRIFT",
                "generated design artifact differs from fresh rebuild",
                relative.as_posix(),
            )
    return generated


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    if arguments.write:
        generated = generate(repo_root)
        print("P5_P6_MECHANISM_ADMISSION_SUCCESSOR_DESIGN_GENERATION=PASS")
        print(f"DESIGN_SHA256={_sha256_bytes(generated.design.canonical_bytes())}")
        print("NEW_EXECUTION_AUTHORIZED=false")
        print(f"NEXT_GATE={NEXT_GATE}")
        return 0
    validate(repo_root)
    print("P5_P6_MECHANISM_ADMISSION_SUCCESSOR_DESIGN_CHECK=PASS")
    print("NEW_EXECUTION_AUTHORIZED=false")
    print(f"NEXT_GATE={NEXT_GATE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
