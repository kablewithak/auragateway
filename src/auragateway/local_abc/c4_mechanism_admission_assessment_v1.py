"""Assess C4 mechanism admission independently from semantic qualification.

This is static reliability infrastructure. It binds existing governed C4
disposition evidence to pre-existing P5/P6 proof obligations, freezes a
mechanism-admission contract, and emits a deterministic assessment. It performs
no model, GPU, Kaggle, network, or authorization action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

BASE_MAIN_COMMIT: Final = "fbff1324ecf35d7aa53600b76fde41c21f9b349e"
EXPECTED_OBSERVATIONS: Final = 3
EXPECTED_FULL_PROMPT_TOKENS: Final = 899
EXPECTED_REUSABLE_PREFIX_TOKENS: Final = 880
EXPECTED_CACHE_BLOCK_SIZE: Final = 16
EXPECTED_REUSABLE_CACHE_BLOCKS: Final = 55

C4_DISPOSITION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_not_qualified_disposition_v1.json"
)
C4_DISPOSITION_SHA256: Final = (
    "5d6dd611bf2d54778f86e43aac019c86648decb0aa9eb5121105e52928328cb3"
)
C4_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_canonical_synthetic_prefix_c4_not_qualified_disposition_v1_review.json"
)
C4_REVIEW_SHA256: Final = (
    "96ffcdfffc7ff5c176ed0315b79ac59e4c15407e2ed742988b86550658ae6dc5"
)
P5_P6_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_design_v1.json"
)
P5_P6_DESIGN_SHA256: Final = (
    "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
)

EXPECTED_RUNTIME_PAYLOAD_SHA256: Final = (
    "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
)
EXPECTED_QUALIFICATION_REQUEST_SHA256: Final = (
    "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884"
)
EXPECTED_PREFIX_RECEIPT_SHA256: Final = (
    "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835"
)
EXPECTED_EVIDENCE_ZIP_SHA256: Final = (
    "94ce021d8c208e5f4d4a39ac9f7c9e4fcb6db6fd25717b1eaa8d7772f6190ce4"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/c4_mechanism_admission_assessment_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_c4_mechanism_admission_assessment_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-22-local-abc-c4-mechanism-admission-contract-v2.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_C4_Mechanism_Admission_Assessment_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_c4_mechanism_admission_assessment_v1.md"
)

CONTRACT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_contract_v2.json"
)
ASSESSMENT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_assessment_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_mechanism_admission_assessment_v1_review.json"
)

GENERATED_PATHS: Final = (CONTRACT_PATH, ASSESSMENT_PATH, REVIEW_PATH)
STATIC_PATHS: Final = (SOURCE_PATH, TEST_PATH, ADR_PATH, REPORT_PATH, RUNBOOK_PATH)

QUALIFIED_NEXT_GATE: Final = "DESIGN_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
UNRESOLVED_NEXT_GATE: Final = "RECONCILE_C4_MECHANISM_ADMISSION_EVIDENCE_V1"


class AssessmentError(RuntimeError):
    """Metadata-safe fail-closed assessment error."""

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
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MechanismAdmissionState(StrEnum):
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    AMBIGUOUS = "AMBIGUOUS"


class RequirementClass(StrEnum):
    MECHANISM_BLOCKING = "MECHANISM_BLOCKING"
    SEMANTIC_DIAGNOSTIC_ONLY = "SEMANTIC_DIAGNOSTIC_ONLY"
    DOWNSTREAM_P5_MEASUREMENT = "DOWNSTREAM_P5_MEASUREMENT"
    DOWNSTREAM_P6_MEASUREMENT = "DOWNSTREAM_P6_MEASUREMENT"


class Receipt(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class C4DispositionRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal[
        "auragateway-canonical-synthetic-prefix-c4-not-qualified-disposition-v1"
    ]
    status: Literal["DISPOSITIONED_VALID_GOVERNED_C4_NOT_QUALIFIED_EXECUTION"]
    transaction_id: Literal[
        "70ef982013fd5ed97dcec8542fab075d3daa9a249ca80a11238e31926085c945"
    ]
    saved_version_id: Literal[343536641]
    execution_valid: bool
    observed_c4_state: Literal["NOT_QUALIFIED"]
    observation_count: int
    exact_object_count: int
    required_exact_object_count: int
    valid_json_count: int
    finish_reason_stop_count: int
    http_200_count: int
    zero_cache_baseline_count: int
    worker_identity_cardinality: int
    identical_nonqualifying_response_identity: bool
    canonical_parsed_object_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    full_prompt_token_count: int
    reusable_prefix_token_count: int
    hidden_retries: int
    external_network_requests: int
    external_spend: int
    teardown_passed: bool
    scratch_cleanup_passed: bool
    failure_report_not_applicable: bool
    raw_prompt_retained: bool
    raw_output_retained: bool
    p5_requalified: bool
    p6_requalified: bool
    final_abc_measured: bool
    production_readiness_established: bool
    new_execution_authorized: bool
    authorization_reusable: bool
    custody_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outer_results_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorities: tuple[Receipt, ...]
    non_claims: tuple[str, ...]
    next_gate: str


class C4DispositionReview(FrozenModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal[
        "auragateway-canonical-synthetic-prefix-c4-not-qualified-disposition-v1-review"
    ]
    status: Literal["APPROVED_GOVERNED_C4_NOT_QUALIFIED_DISPOSITION"]
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runbook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_valid: bool
    c4_qualified_claimed: bool
    root_cause_claimed: bool
    new_execution_authorized: bool
    next_gate: str


class ProofBasis(FrozenModel):
    source_path: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    p5_capability: str
    p5_pass_criteria: tuple[str, ...]
    p5_latency_as_primary_proof_permitted: Literal[False]
    p6_capability: str
    p6_pass_criteria: tuple[str, ...]
    p6_model_semantics_as_route_proof_permitted: Literal[False]


class Requirement(FrozenModel):
    requirement_id: str
    requirement_class: RequirementClass
    blocking_for_mechanism_admission: bool
    evidence_field: str
    expected_state: str
    provenance: str
    protects: tuple[str, ...]
    rationale: str


class MechanismObservation(FrozenModel):
    execution_valid: bool | None
    observation_count: int | None
    http_200_count: int | None
    finish_reason_stop_count: int | None
    zero_cache_baseline_count: int | None
    worker_identity_cardinality: int | None
    full_prompt_token_count: int | None
    reusable_prefix_token_count: int | None
    hidden_retries: int | None
    teardown_passed: bool | None
    scratch_cleanup_passed: bool | None
    failure_report_not_applicable: bool | None
    runtime_identity_bound: bool | None
    request_identity_bound: bool | None
    evidence_identity_bound: bool | None
    output_provenance_present: bool | None


class SemanticObservation(FrozenModel):
    state: Literal["NOT_QUALIFIED"]
    exact_object_count: int
    required_exact_object_count: int
    valid_json_count: int
    canonical_parsed_object_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identical_nonqualifying_response_identity: bool


class MechanismDecision(FrozenModel):
    state: MechanismAdmissionState
    blocking_failures: tuple[str, ...]
    ambiguous_reasons: tuple[str, ...]


class QualificationContract(FrozenModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    contract_id: Literal["auragateway-c4-mechanism-admission-contract-v2"]
    base_main_commit: Literal[
        "fbff1324ecf35d7aa53600b76fde41c21f9b349e"
    ]
    design_principle: Literal[
        "SEMANTIC_CANARY_AND_MECHANISM_ADMISSION_ARE_INDEPENDENT_OBSERVATIONS"
    ]
    criteria_provenance: Literal["PREEXISTING_P5_P6_PROOF_OBLIGATIONS"]
    post_hoc_semantic_relaxation_permitted: Literal[False] = False
    semantic_exact_object_blocking: Literal[False] = False
    valid_json_blocking: Literal[False] = False
    model_semantics_permitted_as_p6_route_proof: Literal[False] = False
    mechanism_states: tuple[
        Literal["QUALIFIED"],
        Literal["NOT_QUALIFIED"],
        Literal["AMBIGUOUS"],
    ]
    reusable_prefix_tokens: Literal[880]
    cache_block_size_tokens: Literal[16]
    reusable_cache_blocks: Literal[55]
    proof_basis: ProofBasis
    requirements: tuple[Requirement, ...]
    non_claims: tuple[str, ...]
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False


class AssessmentRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-c4-mechanism-admission-assessment-v1"]
    contract_id: Literal["auragateway-c4-mechanism-admission-contract-v2"]
    source_main_commit: Literal[
        "fbff1324ecf35d7aa53600b76fde41c21f9b349e"
    ]
    c4_disposition_sha256: Literal[
        "5d6dd611bf2d54778f86e43aac019c86648decb0aa9eb5121105e52928328cb3"
    ]
    c4_review_sha256: Literal[
        "96ffcdfffc7ff5c176ed0315b79ac59e4c15407e2ed742988b86550658ae6dc5"
    ]
    p5_p6_design_sha256: Literal[
        "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
    ]
    semantic_observation: SemanticObservation
    mechanism_observation: MechanismObservation
    mechanism_decision: MechanismDecision
    semantic_c4_relabelled: Literal[False] = False
    p5_requalified: Literal[False] = False
    p6_requalified: Literal[False] = False
    final_abc_measured: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    next_gate: str
    non_claims: tuple[str, ...]


class AssessmentReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-c4-mechanism-admission-assessment-v1-review"]
    status: Literal["APPROVED_STATIC_ASSESSMENT_FOR_REPOSITORY_INTEGRATION"]
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    adr_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runbook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_c4_state: Literal["NOT_QUALIFIED"]
    mechanism_admission_state: MechanismAdmissionState
    p5_requalified_claimed: Literal[False] = False
    p6_requalified_claimed: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: str


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (encoded + "\n").encode()


def read_bytes(repo_root: Path, path: Path) -> bytes:
    target = repo_root / path
    if not target.is_file():
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_REQUIRED_ARTIFACT_MISSING",
            "required artifact missing",
            path.as_posix(),
        )
    return target.read_bytes()


def require_sha(repo_root: Path, path: Path, expected: str) -> bytes:
    payload = read_bytes(repo_root, path)
    observed = sha256(payload)
    if observed != expected:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_IDENTITY_MISMATCH",
            f"expected {expected}; observed {observed}",
            path.as_posix(),
        )
    return payload


def json_object(payload: bytes, path: Path) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_JSON_INVALID",
            "required JSON artifact is invalid",
            path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_JSON_ROOT_INVALID",
            "required JSON root must be an object",
            path.as_posix(),
        )
    return value


def validate_required_authorities(record: C4DispositionRecord) -> None:
    by_role = {receipt.role: receipt for receipt in record.authorities}
    expected = {
        "runtime_payload": EXPECTED_RUNTIME_PAYLOAD_SHA256,
        "qualification_request": EXPECTED_QUALIFICATION_REQUEST_SHA256,
        "reusable_prefix_receipt": EXPECTED_PREFIX_RECEIPT_SHA256,
    }
    for role, expected_sha in expected.items():
        receipt = by_role.get(role)
        if receipt is None:
            raise AssessmentError(
                "C4_MECHANISM_ADMISSION_AUTHORITY_MISSING",
                f"required authority role missing: {role}",
            )
        if receipt.sha256 != expected_sha:
            raise AssessmentError(
                "C4_MECHANISM_ADMISSION_AUTHORITY_DRIFT",
                f"required authority role drifted: {role}",
                receipt.path,
            )
    if record.evidence_zip_sha256 != EXPECTED_EVIDENCE_ZIP_SHA256:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_EVIDENCE_IDENTITY_DRIFT",
            "governed evidence ZIP identity drifted",
        )


def proof_basis(repo_root: Path) -> ProofBasis:
    payload = require_sha(repo_root, P5_P6_DESIGN_PATH, P5_P6_DESIGN_SHA256)
    data = json_object(payload, P5_P6_DESIGN_PATH)

    p5 = data.get("p5")
    p6 = data.get("p6")
    if not isinstance(p5, dict) or not isinstance(p6, dict):
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_PROOF_BASIS_INVALID",
            "P5/P6 design structure is invalid",
            P5_P6_DESIGN_PATH.as_posix(),
        )

    p5_pass = p5.get("pass_criteria")
    p6_pass = p6.get("pass_criteria")
    if not isinstance(p5_pass, list) or not all(
        isinstance(item, str) for item in p5_pass
    ):
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_P5_CRITERIA_INVALID",
            "P5 pass criteria are invalid",
            P5_P6_DESIGN_PATH.as_posix(),
        )
    if not isinstance(p6_pass, list) or not all(
        isinstance(item, str) for item in p6_pass
    ):
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_P6_CRITERIA_INVALID",
            "P6 pass criteria are invalid",
            P5_P6_DESIGN_PATH.as_posix(),
        )

    p5_capability = p5.get("capability")
    p6_capability = p6.get("capability")
    if not isinstance(p5_capability, str) or not isinstance(p6_capability, str):
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_CAPABILITY_INVALID",
            "P5/P6 capability text is invalid",
            P5_P6_DESIGN_PATH.as_posix(),
        )

    if p5.get("latency_as_primary_proof_permitted") is not False:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_P5_PROOF_DRIFT",
            "P5 latency proof boundary drifted",
            P5_P6_DESIGN_PATH.as_posix(),
        )
    if p6.get("model_semantics_as_route_proof_permitted") is not False:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_P6_PROOF_DRIFT",
            "P6 semantic route-proof boundary drifted",
            P5_P6_DESIGN_PATH.as_posix(),
        )

    return ProofBasis(
        source_path=P5_P6_DESIGN_PATH.as_posix(),
        source_sha256=P5_P6_DESIGN_SHA256,
        p5_capability=p5_capability,
        p5_pass_criteria=tuple(p5_pass),
        p5_latency_as_primary_proof_permitted=False,
        p6_capability=p6_capability,
        p6_pass_criteria=tuple(p6_pass),
        p6_model_semantics_as_route_proof_permitted=False,
    )


def requirements() -> tuple[Requirement, ...]:
    return (
        Requirement(
            requirement_id="MA-01",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="execution_valid",
            expected_state="true",
            provenance="P5/P6 require trustworthy current-runtime observations.",
            protects=("P5", "P6"),
            rationale="Invalid execution cannot support mechanism inference.",
        ),
        Requirement(
            requirement_id="MA-02",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="request_accounting_and_hidden_retries",
            expected_state="3 observations; hidden_retries=0",
            provenance="P6 request reconciliation; frozen hidden-retry budget.",
            protects=("P5", "P6"),
            rationale="Duplicate or missing requests destroy metric attribution.",
        ),
        Requirement(
            requirement_id="MA-03",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="http_200_and_finish_reason_stop",
            expected_state="3/3 HTTP 200 and 3/3 stop",
            provenance="Governed request realization precedes P5/P6 measurement.",
            protects=("P5", "P6"),
            rationale="Transport or terminal failure makes the request window invalid.",
        ),
        Requirement(
            requirement_id="MA-04",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="worker_identity_and_zero_cache_baseline",
            expected_state="3 workers; 3 zero-cache baselines",
            provenance="P5 starting-state and P6 worker-identity obligations.",
            protects=("P5", "P6"),
            rationale="Unknown worker or starting state admits confounded reuse.",
        ),
        Requirement(
            requirement_id="MA-05",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="prompt_and_reusable_prefix_geometry",
            expected_state="899 full; 880 reusable; 55 x 16-token blocks",
            provenance="P5 token identity and cacheable-prefix bound obligations.",
            protects=("P5",),
            rationale=(
                "Unresolved token geometry prevents bounded cache interpretation."
            ),
        ),
        Requirement(
            requirement_id="MA-06",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="bound_runtime_request_prefix_and_evidence_identities",
            expected_state="exact governed identities",
            provenance="Exact-runtime and request-identity proof obligations.",
            protects=("P5", "P6"),
            rationale="Identity drift changes the subject of the qualification.",
        ),
        Requirement(
            requirement_id="MA-07",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="output_provenance_present",
            expected_state="true",
            provenance="P6 requires output provenance and request reconciliation.",
            protects=("P6",),
            rationale=(
                "The response must remain attributable even when semantically wrong."
            ),
        ),
        Requirement(
            requirement_id="MA-08",
            requirement_class=RequirementClass.MECHANISM_BLOCKING,
            blocking_for_mechanism_admission=True,
            evidence_field="teardown_and_cleanup",
            expected_state="PASS",
            provenance="Frozen governed teardown and lifecycle obligations.",
            protects=("P5", "P6"),
            rationale="Uncontrolled terminal state weakens execution validity.",
        ),
        Requirement(
            requirement_id="SC-01",
            requirement_class=RequirementClass.SEMANTIC_DIAGNOSTIC_ONLY,
            blocking_for_mechanism_admission=False,
            evidence_field="exact_object_count",
            expected_state="independently recorded",
            provenance="C4 semantic canary, not P5/P6 mechanism proof.",
            protects=("SEMANTIC_CANARY",),
            rationale=(
                "Semantic disagreement is retained without becoming route/cache proof."
            ),
        ),
        Requirement(
            requirement_id="SC-02",
            requirement_class=RequirementClass.SEMANTIC_DIAGNOSTIC_ONLY,
            blocking_for_mechanism_admission=False,
            evidence_field="valid_json_count",
            expected_state="independently recorded",
            provenance="Output-format diagnostic, not frozen P5/P6 pass criterion.",
            protects=("SEMANTIC_CANARY",),
            rationale="JSON validity must not silently become cache or route evidence.",
        ),
        Requirement(
            requirement_id="P5-OBS",
            requirement_class=RequirementClass.DOWNSTREAM_P5_MEASUREMENT,
            blocking_for_mechanism_admission=False,
            evidence_field="positive_local_cache_reuse",
            expected_state="measured by P5, not admission",
            provenance="Frozen P5 pass criteria.",
            protects=("P5",),
            rationale="Admission must not pre-prove the capability it enables.",
        ),
        Requirement(
            requirement_id="P6-OBS",
            requirement_class=RequirementClass.DOWNSTREAM_P6_MEASUREMENT,
            blocking_for_mechanism_admission=False,
            evidence_field="worker_local_metric_movement_and_state_isolation",
            expected_state="measured by P6, not admission",
            provenance="Frozen P6 pass criteria.",
            protects=("P6",),
            rationale="Admission must not pre-prove the capability it enables.",
        ),
    )


def contract(repo_root: Path) -> QualificationContract:
    return QualificationContract(
        contract_id="auragateway-c4-mechanism-admission-contract-v2",
        base_main_commit=BASE_MAIN_COMMIT,
        design_principle=(
            "SEMANTIC_CANARY_AND_MECHANISM_ADMISSION_ARE_INDEPENDENT_OBSERVATIONS"
        ),
        criteria_provenance="PREEXISTING_P5_P6_PROOF_OBLIGATIONS",
        mechanism_states=("QUALIFIED", "NOT_QUALIFIED", "AMBIGUOUS"),
        reusable_prefix_tokens=EXPECTED_REUSABLE_PREFIX_TOKENS,
        cache_block_size_tokens=EXPECTED_CACHE_BLOCK_SIZE,
        reusable_cache_blocks=EXPECTED_REUSABLE_CACHE_BLOCKS,
        proof_basis=proof_basis(repo_root),
        requirements=requirements(),
        non_claims=(
            "Semantic C4 qualification is not changed by this contract.",
            "Mechanism admission is not P5 cache proof.",
            "Mechanism admission is not P6 route/state-isolation proof.",
            "No variance-pilot result is established.",
            "No final measured A/B/C result is established.",
            "No quality non-inferiority result is established.",
            "No production-readiness claim is established.",
            "No execution authorization is created.",
        ),
    )


def authority_bound(record: C4DispositionRecord, role: str, expected: str) -> bool:
    for receipt in record.authorities:
        if receipt.role == role:
            return receipt.sha256 == expected
    return False


def mechanism_observation(record: C4DispositionRecord) -> MechanismObservation:
    return MechanismObservation(
        execution_valid=record.execution_valid,
        observation_count=record.observation_count,
        http_200_count=record.http_200_count,
        finish_reason_stop_count=record.finish_reason_stop_count,
        zero_cache_baseline_count=record.zero_cache_baseline_count,
        worker_identity_cardinality=record.worker_identity_cardinality,
        full_prompt_token_count=record.full_prompt_token_count,
        reusable_prefix_token_count=record.reusable_prefix_token_count,
        hidden_retries=record.hidden_retries,
        teardown_passed=record.teardown_passed,
        scratch_cleanup_passed=record.scratch_cleanup_passed,
        failure_report_not_applicable=record.failure_report_not_applicable,
        runtime_identity_bound=authority_bound(
            record,
            "runtime_payload",
            EXPECTED_RUNTIME_PAYLOAD_SHA256,
        ),
        request_identity_bound=(
            authority_bound(
                record,
                "qualification_request",
                EXPECTED_QUALIFICATION_REQUEST_SHA256,
            )
            and authority_bound(
                record,
                "reusable_prefix_receipt",
                EXPECTED_PREFIX_RECEIPT_SHA256,
            )
        ),
        evidence_identity_bound=(
            record.evidence_zip_sha256 == EXPECTED_EVIDENCE_ZIP_SHA256
        ),
        output_provenance_present=bool(
            record.canonical_parsed_object_sha256
            and record.worker_identity_cardinality == record.observation_count
        ),
    )


def semantic_observation(record: C4DispositionRecord) -> SemanticObservation:
    return SemanticObservation(
        state="NOT_QUALIFIED",
        exact_object_count=record.exact_object_count,
        required_exact_object_count=record.required_exact_object_count,
        valid_json_count=record.valid_json_count,
        canonical_parsed_object_sha256=record.canonical_parsed_object_sha256,
        identical_nonqualifying_response_identity=(
            record.identical_nonqualifying_response_identity
        ),
    )


def assess_mechanism(observation: MechanismObservation) -> MechanismDecision:
    ambiguous: list[str] = []
    failures: list[str] = []

    required_values = {
        "execution_valid": observation.execution_valid,
        "observation_count": observation.observation_count,
        "http_200_count": observation.http_200_count,
        "finish_reason_stop_count": observation.finish_reason_stop_count,
        "zero_cache_baseline_count": observation.zero_cache_baseline_count,
        "worker_identity_cardinality": observation.worker_identity_cardinality,
        "full_prompt_token_count": observation.full_prompt_token_count,
        "reusable_prefix_token_count": observation.reusable_prefix_token_count,
        "hidden_retries": observation.hidden_retries,
        "teardown_passed": observation.teardown_passed,
        "scratch_cleanup_passed": observation.scratch_cleanup_passed,
        "failure_report_not_applicable": observation.failure_report_not_applicable,
        "runtime_identity_bound": observation.runtime_identity_bound,
        "request_identity_bound": observation.request_identity_bound,
        "evidence_identity_bound": observation.evidence_identity_bound,
        "output_provenance_present": observation.output_provenance_present,
    }
    for name, value in required_values.items():
        if value is None:
            ambiguous.append(f"{name}=NOT_OBSERVED")

    if observation.execution_valid is False:
        failures.append("execution_valid=false")
    if (
        observation.observation_count is not None
        and observation.observation_count != EXPECTED_OBSERVATIONS
    ):
        failures.append("observation_count_mismatch")
    if (
        observation.http_200_count is not None
        and observation.http_200_count != EXPECTED_OBSERVATIONS
    ):
        failures.append("http_200_count_mismatch")
    if (
        observation.finish_reason_stop_count is not None
        and observation.finish_reason_stop_count != EXPECTED_OBSERVATIONS
    ):
        failures.append("finish_reason_stop_count_mismatch")
    if (
        observation.zero_cache_baseline_count is not None
        and observation.zero_cache_baseline_count != EXPECTED_OBSERVATIONS
    ):
        failures.append("zero_cache_baseline_count_mismatch")
    if (
        observation.worker_identity_cardinality is not None
        and observation.worker_identity_cardinality != EXPECTED_OBSERVATIONS
    ):
        failures.append("worker_identity_cardinality_mismatch")
    if (
        observation.full_prompt_token_count is not None
        and observation.full_prompt_token_count != EXPECTED_FULL_PROMPT_TOKENS
    ):
        failures.append("full_prompt_token_count_mismatch")
    if (
        observation.reusable_prefix_token_count is not None
        and observation.reusable_prefix_token_count != EXPECTED_REUSABLE_PREFIX_TOKENS
    ):
        failures.append("reusable_prefix_token_count_mismatch")
    if observation.hidden_retries is not None and observation.hidden_retries != 0:
        failures.append("hidden_retries_nonzero")
    if observation.teardown_passed is False:
        failures.append("teardown_failed")
    if observation.scratch_cleanup_passed is False:
        failures.append("scratch_cleanup_failed")
    if observation.failure_report_not_applicable is False:
        failures.append("failure_report_present")
    if observation.runtime_identity_bound is False:
        failures.append("runtime_identity_unbound")
    if observation.request_identity_bound is False:
        failures.append("request_identity_unbound")
    if observation.evidence_identity_bound is False:
        failures.append("evidence_identity_unbound")
    if observation.output_provenance_present is False:
        failures.append("output_provenance_absent")

    if failures:
        state = MechanismAdmissionState.NOT_QUALIFIED
    elif ambiguous:
        state = MechanismAdmissionState.AMBIGUOUS
    else:
        state = MechanismAdmissionState.QUALIFIED

    return MechanismDecision(
        state=state,
        blocking_failures=tuple(failures),
        ambiguous_reasons=tuple(ambiguous),
    )


def load_inputs(
    repo_root: Path,
) -> tuple[C4DispositionRecord, C4DispositionReview]:
    record_payload = require_sha(
        repo_root,
        C4_DISPOSITION_PATH,
        C4_DISPOSITION_SHA256,
    )
    review_payload = require_sha(
        repo_root,
        C4_REVIEW_PATH,
        C4_REVIEW_SHA256,
    )

    try:
        record = C4DispositionRecord.model_validate_json(record_payload)
        review = C4DispositionReview.model_validate_json(review_payload)
    except ValidationError as error:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_INPUT_SCHEMA_INVALID",
            "governed C4 disposition schema validation failed",
        ) from error

    if review.record_sha256 != C4_DISPOSITION_SHA256:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_REVIEW_BINDING_INVALID",
            "C4 disposition review does not bind the expected record",
            C4_REVIEW_PATH.as_posix(),
        )
    if not review.execution_valid:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_REVIEW_EXECUTION_INVALID",
            "C4 disposition review does not accept execution validity",
            C4_REVIEW_PATH.as_posix(),
        )
    if review.c4_qualified_claimed:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_SEMANTIC_HISTORY_DRIFT",
            "C4 review unexpectedly claims semantic qualification",
            C4_REVIEW_PATH.as_posix(),
        )
    if review.new_execution_authorized:
        raise AssessmentError(
            "C4_MECHANISM_ADMISSION_AUTHORITY_DRIFT",
            "C4 review unexpectedly authorizes new execution",
            C4_REVIEW_PATH.as_posix(),
        )

    validate_required_authorities(record)
    return record, review


def assessment_record(
    repo_root: Path,
    frozen_contract: QualificationContract,
) -> AssessmentRecord:
    record, _ = load_inputs(repo_root)
    mechanism = mechanism_observation(record)
    decision = assess_mechanism(mechanism)
    next_gate = (
        QUALIFIED_NEXT_GATE
        if decision.state == MechanismAdmissionState.QUALIFIED
        else UNRESOLVED_NEXT_GATE
    )

    return AssessmentRecord(
        record_id="auragateway-c4-mechanism-admission-assessment-v1",
        contract_id=frozen_contract.contract_id,
        source_main_commit=BASE_MAIN_COMMIT,
        c4_disposition_sha256=C4_DISPOSITION_SHA256,
        c4_review_sha256=C4_REVIEW_SHA256,
        p5_p6_design_sha256=P5_P6_DESIGN_SHA256,
        semantic_observation=semantic_observation(record),
        mechanism_observation=mechanism,
        mechanism_decision=decision,
        next_gate=next_gate,
        non_claims=(
            "C4 semantic qualification remains NOT_QUALIFIED.",
            "Mechanism admission does not requalify P5.",
            "Mechanism admission does not requalify P6.",
            "No model request was performed by this assessment.",
            "No GPU or Kaggle execution was performed by this assessment.",
            "No new execution authorization is created.",
            "Final measured A/B/C remains unexecuted.",
            "Quality non-inferiority remains unestablished.",
            "Production readiness remains unestablished.",
        ),
    )


def static_hashes(repo_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in STATIC_PATHS:
        result[path.as_posix()] = sha256(read_bytes(repo_root, path))
    return result


def build_all(repo_root: Path) -> tuple[bytes, bytes, bytes]:
    frozen_contract = contract(repo_root)
    assessment = assessment_record(repo_root, frozen_contract)

    contract_payload = canonical_bytes(frozen_contract)
    assessment_payload = canonical_bytes(assessment)
    hashes = static_hashes(repo_root)

    review = AssessmentReview(
        review_id="auragateway-c4-mechanism-admission-assessment-v1-review",
        status="APPROVED_STATIC_ASSESSMENT_FOR_REPOSITORY_INTEGRATION",
        contract_sha256=sha256(contract_payload),
        assessment_sha256=sha256(assessment_payload),
        source_sha256=hashes[SOURCE_PATH.as_posix()],
        test_sha256=hashes[TEST_PATH.as_posix()],
        adr_sha256=hashes[ADR_PATH.as_posix()],
        report_sha256=hashes[REPORT_PATH.as_posix()],
        runbook_sha256=hashes[RUNBOOK_PATH.as_posix()],
        semantic_c4_state="NOT_QUALIFIED",
        mechanism_admission_state=assessment.mechanism_decision.state,
        next_gate=assessment.next_gate,
    )
    return contract_payload, assessment_payload, canonical_bytes(review)


def write_generated(repo_root: Path) -> None:
    payloads = build_all(repo_root)
    for path, payload in zip(GENERATED_PATHS, payloads, strict=True):
        target = repo_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def check_generated(repo_root: Path) -> None:
    payloads = build_all(repo_root)
    for path, expected in zip(GENERATED_PATHS, payloads, strict=True):
        observed = read_bytes(repo_root, path)
        if observed != expected:
            raise AssessmentError(
                "C4_MECHANISM_ADMISSION_GENERATED_ARTIFACT_DRIFT",
                "generated artifact differs from producer output",
                path.as_posix(),
            )


def parser() -> argparse.ArgumentParser:
    result = _ArgumentParser()
    result.add_argument("--repo-root", type=Path, default=Path.cwd())
    action = result.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repo_root = args.repo_root.resolve()

    try:
        if args.write:
            write_generated(repo_root)
        if args.check:
            check_generated(repo_root)
    except AssessmentError as error:
        print(json.dumps(error.envelope(), sort_keys=True), file=sys.stderr)
        return 1

    contract_payload, assessment_payload, review_payload = build_all(repo_root)
    assessment = AssessmentRecord.model_validate_json(assessment_payload)
    print(
        json.dumps(
            {
                "contract_sha256": sha256(contract_payload),
                "assessment_sha256": sha256(assessment_payload),
                "review_sha256": sha256(review_payload),
                "semantic_c4_state": assessment.semantic_observation.state,
                "mechanism_admission_state": assessment.mechanism_decision.state,
                "p5_requalified": assessment.p5_requalified,
                "p6_requalified": assessment.p6_requalified,
                "model_requests_performed": assessment.model_requests_performed,
                "gpu_execution_performed": assessment.gpu_execution_performed,
                "kaggle_execution_performed": assessment.kaggle_execution_performed,
                "new_execution_authorized": assessment.new_execution_authorized,
                "next_gate": assessment.next_gate,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
