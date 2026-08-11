"""Reconcile the governed transaction-bound P5/P6 C3 failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "8ad4e628eaffbfc52d46bd958588529e940881937e09ade1c5c6064a755fc9aa"
SAVED_VERSION_ID: Final = 341728154
CUSTODY_MANIFEST_SHA256: Final = "3ca422790bdb6ff2a57c922e33f3fd7df01226d71e122f77234400a088c82103"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_transaction_bound_c3_failure_reconciliation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_transaction_bound_c3_failure_reconciliation_v1.py"
)

CUSTODY_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_transaction_bound_c3_failure_evidence_manifest_v1.json"
)
V5_ROOT_CAUSE_PATH: Final = Path(
    "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v5/"
    "root_cause_analysis_v5-340227787.json"
)
P4_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_acceptance_v1.json"
)
SUCCESSOR_ADR_PATH: Final = Path(
    "docs/adr/2026-08-07-local-abc-p5-p6-successor-runtime-qualification-v1-implementation.md"
)
CURRENT_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_transaction_bound_c3_failure_reconciliation_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_transaction_bound_c3_failure_reconciliation_v1_review.json"
)

NEXT_GATE: Final = "DESIGN_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1"


class ReconciliationError(RuntimeError):
    """Fail-closed reconciliation error."""

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
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactReceipt(StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class CustodyManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    manifest_id: Literal["auragateway-p5-p6-transaction-bound-c3-failure-evidence-manifest-v1"]
    transaction_id: Literal["8ad4e628eaffbfc52d46bd958588529e940881937e09ade1c5c6064a755fc9aa"]
    primary_saved_version_id: Literal[341728154]
    terminal_disposition: Literal["CONSUMED"]
    terminal_execution_outcome: Literal["DIAGNOSTIC_INVALID"]
    duplicate_saved_execution_observed: Literal[True]
    duplicate_ui_version_number: Literal[2]
    duplicate_saved_execution_status: Literal["CANCELLED"]
    duplicate_saved_execution_script_version_id: None
    single_use_acceptance_valid: Literal[False]
    technical_primary_execution_status: Literal["FAILED"]
    technical_completed_capabilities: tuple[str, ...]
    technical_first_divergence: Literal["C3"]
    technical_failure_class: Literal["REQUEST_EXECUTION_FAILURE"]
    safe_failure_message: Literal["model response is not valid JSON"]
    runtime_source_identity_passed: Literal[True]
    runtime_installation_passed: Literal[True]
    runtime_import_closure_passed: Literal[True]
    model_construction_passed: Literal[True]
    worker_startup_passed: Literal[True]
    model_requests_performed: Literal[1]
    hidden_retries_performed: Literal[0]
    network_requests_performed: Literal[0]
    p5_reached: Literal[False]
    p6_reached: Literal[False]
    authorization_reusable: Literal[False]
    runtime_execution_authorized: Literal[False]
    root_cause_established: Literal[False]
    member_count: Literal[9]
    members: tuple[ArtifactReceipt, ...]
    next_gate: Literal["BUILD_P4_P5_COMPOSITION_DIFFERENTIAL_RECONCILIATION_V1"]

    @model_validator(mode="after")
    def validate_fixed_boundary(self) -> Self:
        if self.technical_completed_capabilities != ("C1", "C2"):
            raise ValueError("completed capability sequence drifted")
        if len(self.members) != self.member_count:
            raise ValueError("custody member count drifted")
        return self


class HistoricalV5RootCause(ExternalModel):
    classification: Literal["VALID_GOVERNED_DIAGNOSTIC_FAILURE"]
    first_observed_divergence: Literal["P4_MODEL_RESPONSE_NOT_VALID_JSON"]
    primary_classification: Literal["P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS"]
    specific_classification: Literal["V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"]
    reported_failure_code: Literal["P3_P6_REQUEST_FAILED"]
    failure_scope: Literal["P4_OUTPUT_CONTRACT"]
    unchanged_replay_authorized: Literal[False]


class P4Acceptance(ExternalModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-p4-output-contract-diagnostic-execution-acceptance-v1"]
    status: Literal["P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_VALID"]
    saved_version_id: Literal[340775383]
    lifecycle_outcome: Literal["PASSED"]
    evidence_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    selected_case_id: Literal["A"]
    eligible_case_ids: tuple[str, ...]
    ineligible_case_ids: tuple[str, ...]
    model_requests: Literal[18]
    p4_output_contract_diagnostic_established: Literal[True]
    authorization_lifecycle_closed: Literal[True]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]

    @model_validator(mode="after")
    def validate_case_selection(self) -> Self:
        if self.eligible_case_ids != ("A", "C", "E", "F"):
            raise ValueError("P4 eligible-case identity drifted")
        if self.ineligible_case_ids != ("B", "D"):
            raise ValueError("P4 ineligible-case identity drifted")
        return self


class ReconciliationRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-p5-p6-transaction-bound-c3-failure-reconciliation-v1"]
    status: Literal["RECONCILED_DIAGNOSTIC_INVALID_TRANSACTION"]
    transaction_id: Literal["8ad4e628eaffbfc52d46bd958588529e940881937e09ade1c5c6064a755fc9aa"]
    primary_saved_version_id: Literal[341728154]
    governance_disposition: Literal["ACCEPTED_INVALID_SINGLE_USE_TRANSACTION"]
    technical_evidence_disposition: Literal["ACCEPTED_TECHNICAL_DIAGNOSTIC_FAILURE_EVIDENCE"]
    technical_first_divergence: Literal["C3"]
    technical_failure_class: Literal["REQUEST_EXECUTION_FAILURE"]
    safe_failure_message: Literal["model response is not valid JSON"]
    historical_failure_family_match: Literal[True]
    historical_v5_primary_classification: Literal["P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS"]
    historical_v5_specific_classification: Literal[
        "V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION"
    ]
    historical_p4_case_a_selected: Literal[True]
    historical_p4_case_a_qualified: Literal[True]
    current_composition_uses_v4_system_prompt: Literal[True]
    current_composition_uses_v5_derived_cache_context: Literal[True]
    material_message_context_change_established: Literal[True]
    primary_classification: Literal["P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION"]
    specific_classification: Literal[
        "QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE"
    ]
    causal_confidence: Literal["HIGH_ARCHITECTURAL_INFERENCE_NOT_COUNTERFACTUAL_PROOF"]
    exact_failed_model_output_known: Literal[False]
    runtime_incompatibility_established: Literal[False]
    model_construction_failure_established: Literal[False]
    worker_startup_failure_established: Literal[False]
    p5_failure_established: Literal[False]
    p6_failure_established: Literal[False]
    duplicate_saved_execution_observed: Literal[True]
    single_use_acceptance_valid: Literal[False]
    authorization_reusable: Literal[False]
    runtime_execution_authorized: Literal[False]
    unchanged_replay_authorized: Literal[False]
    runtime_fix_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    authorities: tuple[ArtifactReceipt, ...]
    next_gate: Literal["DESIGN_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_authority_count(self) -> Self:
        if len(self.authorities) != 5:
            raise ValueError("reconciliation authority count drifted")
        if len(self.non_claims) < 8:
            raise ValueError("reconciliation non-claim boundary is incomplete")
        return self


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_ARTIFACT_MISSING",
            "required reconciliation artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _load_json(root: Path, relative: Path) -> dict[str, object]:
    path = _require_file(root, relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_JSON_INVALID",
            "reconciliation JSON is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_JSON_INVALID",
            "reconciliation JSON root must be an object",
            relative.as_posix(),
        )
    return cast(dict[str, object], payload)


def _receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = _require_file(root, relative)
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _canonical_json_bytes(payload: BaseModel | dict[str, object]) -> bytes:
    if isinstance(payload, BaseModel):
        value: object = payload.model_dump(mode="json")
    else:
        value = payload
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def build_record(repo_root: Path) -> ReconciliationRecord:
    root = repo_root.resolve()

    custody_path = _require_file(root, CUSTODY_MANIFEST_PATH)
    if _sha256_file(custody_path) != CUSTODY_MANIFEST_SHA256:
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_CUSTODY_DRIFT",
            "custody manifest byte identity drifted",
            CUSTODY_MANIFEST_PATH.as_posix(),
        )

    custody = CustodyManifest.model_validate(_load_json(root, CUSTODY_MANIFEST_PATH))
    historical = HistoricalV5RootCause.model_validate(_load_json(root, V5_ROOT_CAUSE_PATH))
    p4 = P4Acceptance.model_validate(_load_json(root, P4_ACCEPTANCE_PATH))

    successor_adr = _require_file(root, SUCCESSOR_ADR_PATH).read_text(encoding="utf-8")
    runtime_source = _require_file(root, CURRENT_RUNTIME_PATH).read_text(encoding="utf-8")

    required_successor_markers = (
        "P4 V2 case A owns the successor P4 output contract.",
        "V5's long synthetic deterministic context is retained as the cacheable prefix.",
    )
    for marker in required_successor_markers:
        if marker not in successor_adr:
            raise ReconciliationError(
                "P5_P6_C3_RECONCILIATION_SUCCESSOR_AUTHORITY_DRIFT",
                "successor composition authority drifted",
                SUCCESSOR_ADR_PATH.as_posix(),
            )

    required_runtime_markers = (
        "Return only the exact JSON object supplied in the final user message, ",
        "with no markdown or additional text.",
        (
            "For structured probes, return only the exact JSON object supplied "
            "in the final user message."
        ),
        'EXPECTED_OBJECT = {"probe": "exact-runtime-p5-p6", "value": 1}',
    )
    for marker in required_runtime_markers:
        if marker not in runtime_source:
            raise ReconciliationError(
                "P5_P6_C3_RECONCILIATION_RUNTIME_COMPOSITION_DRIFT",
                "current runtime composition authority drifted",
                CURRENT_RUNTIME_PATH.as_posix(),
            )

    if custody.root_cause_established:
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_PREMATURE_ROOT_CAUSE",
            "custody evidence incorrectly claims established root cause",
            CUSTODY_MANIFEST_PATH.as_posix(),
        )

    if p4.selected_case_id != "A":
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_P4_AUTHORITY_DRIFT",
            "historical P4 selected case drifted",
            P4_ACCEPTANCE_PATH.as_posix(),
        )

    authorities = (
        _receipt(root, CUSTODY_MANIFEST_PATH),
        _receipt(root, V5_ROOT_CAUSE_PATH),
        _receipt(root, P4_ACCEPTANCE_PATH),
        _receipt(root, SUCCESSOR_ADR_PATH),
        _receipt(root, CURRENT_RUNTIME_PATH),
    )

    return ReconciliationRecord(
        schema_version="1.0.0",
        record_id=("auragateway-p5-p6-transaction-bound-c3-failure-reconciliation-v1"),
        status="RECONCILED_DIAGNOSTIC_INVALID_TRANSACTION",
        transaction_id=TRANSACTION_ID,
        primary_saved_version_id=SAVED_VERSION_ID,
        governance_disposition="ACCEPTED_INVALID_SINGLE_USE_TRANSACTION",
        technical_evidence_disposition=("ACCEPTED_TECHNICAL_DIAGNOSTIC_FAILURE_EVIDENCE"),
        technical_first_divergence="C3",
        technical_failure_class="REQUEST_EXECUTION_FAILURE",
        safe_failure_message="model response is not valid JSON",
        historical_failure_family_match=True,
        historical_v5_primary_classification=historical.primary_classification,
        historical_v5_specific_classification=historical.specific_classification,
        historical_p4_case_a_selected=True,
        historical_p4_case_a_qualified=p4.p4_output_contract_diagnostic_established,
        current_composition_uses_v4_system_prompt=True,
        current_composition_uses_v5_derived_cache_context=True,
        material_message_context_change_established=True,
        primary_classification="P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION",
        specific_classification=("QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE"),
        causal_confidence=("HIGH_ARCHITECTURAL_INFERENCE_NOT_COUNTERFACTUAL_PROOF"),
        exact_failed_model_output_known=False,
        runtime_incompatibility_established=False,
        model_construction_failure_established=False,
        worker_startup_failure_established=False,
        p5_failure_established=False,
        p6_failure_established=False,
        duplicate_saved_execution_observed=True,
        single_use_acceptance_valid=False,
        authorization_reusable=False,
        runtime_execution_authorized=False,
        unchanged_replay_authorized=False,
        runtime_fix_authorized=False,
        new_execution_authorized=False,
        authorities=authorities,
        next_gate=NEXT_GATE,
        non_claims=(
            "The invalid single-use transaction is not accepted as P5/P6 qualification.",
            "The exact failed model output is unknown.",
            "The composition classification is not counterfactual experimental proof.",
            "A general Qwen JSON reliability failure is not established.",
            "Runtime incompatibility is not established.",
            "Model construction failure is not established.",
            "Worker startup failure is not established.",
            "P5 failure is not established.",
            "P6 failure is not established.",
            "Measured A/B/C execution remains unauthorized.",
            "No unchanged replay is authorized.",
            "No runtime remediation is authorized by this reconciliation.",
        ),
    )


def expected_outputs(repo_root: Path) -> tuple[bytes, bytes]:
    root = repo_root.resolve()
    record = build_record(root)
    record_bytes = _canonical_json_bytes(record)

    source_receipt = _receipt(root, SOURCE_PATH)
    test_receipt = _receipt(root, TEST_PATH)

    review: dict[str, object] = {
        "schema_version": "1.0.0",
        "review_id": ("auragateway-p5-p6-transaction-bound-c3-failure-reconciliation-v1-review"),
        "decision": "APPROVED_RECONCILIATION_DECISION",
        "custody_manifest_sha256": CUSTODY_MANIFEST_SHA256,
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "source": source_receipt.model_dump(mode="json"),
        "tests": test_receipt.model_dump(mode="json"),
        "primary_classification": ("P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION"),
        "specific_classification": (
            "QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE"
        ),
        "causal_confidence": ("HIGH_ARCHITECTURAL_INFERENCE_NOT_COUNTERFACTUAL_PROOF"),
        "runtime_fix_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }
    review_bytes = _canonical_json_bytes(review)
    return record_bytes, review_bytes


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record_bytes, review_bytes = expected_outputs(root)

    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)

    record_path.write_bytes(record_bytes)
    review_path.write_bytes(review_bytes)

    return {
        "status": "P5_P6_C3_FAILURE_RECONCILIATION_GENERATED",
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "review_sha256": hashlib.sha256(review_bytes).hexdigest(),
        "runtime_fix_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_record, expected_review = expected_outputs(root)

    record_path = _require_file(root, RECORD_PATH)
    review_path = _require_file(root, REVIEW_PATH)

    if record_path.read_bytes() != expected_record:
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_RECORD_DRIFT",
            "generated reconciliation record drifted",
            RECORD_PATH.as_posix(),
        )

    if review_path.read_bytes() != expected_review:
        raise ReconciliationError(
            "P5_P6_C3_RECONCILIATION_REVIEW_DRIFT",
            "generated reconciliation review drifted",
            REVIEW_PATH.as_posix(),
        )

    ReconciliationRecord.model_validate(json.loads(record_path.read_text(encoding="utf-8")))

    return {
        "status": "P5_P6_C3_FAILURE_RECONCILIATION_VALID",
        "record_sha256": _sha256_file(record_path),
        "review_sha256": _sha256_file(review_path),
        "runtime_fix_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=("generate", "validate"),
    )
    parser.add_argument(
        "--repo-root",
        default=".",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = Path(args.repo_root)

    try:
        result: dict[str, object] | None = None

        if args.command == "generate":
            result = generate(root)

        if args.command == "validate":
            result = validate(root)

        if result is None:
            raise ReconciliationError(
                "P5_P6_C3_RECONCILIATION_COMMAND_INVALID",
                "reconciliation command was not handled",
            )

        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0

    except (ReconciliationError, ValidationError) as error:
        if isinstance(error, ReconciliationError):
            payload = error.envelope()

        if isinstance(error, ValidationError):
            payload = {
                "error_code": "P5_P6_C3_RECONCILIATION_SCHEMA_INVALID",
                "safe_message": "reconciliation schema validation failed",
                "path": None,
            }

        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
