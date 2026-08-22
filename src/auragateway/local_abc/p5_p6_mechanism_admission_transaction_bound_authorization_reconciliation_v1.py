"""Design and validate P5/P6 mechanism-admission authorization reconciliation V1."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

BASE_MAIN_COMMIT: Final = "f33c835414b89dca15976e30877d7f0ebfa96e06"
ARCHITECTURE_MERGE_COMMIT: Final = "32b737a64133dbd8361ac3db871e4c02ff80ccf3"
TRANSACTION_BOUND_IMPLEMENTATION_MERGE_COMMIT: Final = "4afdcf9d840bc90ceb34af8dae098998f78de572"
TRANSACTION_BOUND_RUNTIME_INTEGRATION_MERGE_COMMIT: Final = (
    "3e1975fcbed7c19f8e943d9f2177e1b9264c9d3b"
)
C4_AUTHORIZATION_DESIGN_MERGE_COMMIT: Final = "79b8ae8c1c96ea3f296725daff09615767caaefa"
MECHANISM_SUCCESSOR_DESIGN_MERGE_COMMIT: Final = "68a2a36016a85661c820545fad67db925f84ffd0"
MECHANISM_SUCCESSOR_IMPLEMENTATION_MERGE_COMMIT: Final = "2b1841aee4397ae0c72bad6b2c9e7069835d8399"
SUPERSEDED_ISSUER_MERGE_COMMIT: Final = "f33c835414b89dca15976e30877d7f0ebfa96e06"

ARCHITECTURE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_transaction_bound_execution_authorization_architecture_v1.json"
)
ARCHITECTURE_RECORD_SHA256: Final = (
    "4fff25e4a6160dfcdd23294285689d0290b9ecf32930a90c737454878d2a3779"
)
TRANSACTION_BOUND_RUNTIME_INTEGRATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_v1.json"
)
MECHANISM_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json"
)
MECHANISM_DESIGN_SHA256: Final = "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
MECHANISM_IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_v1_implementation_review.json"
)
MECHANISM_IMPLEMENTATION_REVIEW_SHA256: Final = (
    "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
)
SUPERSEDED_ISSUER_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_execution_authorization_issuer_v1_record.json"
)
SUPERSEDED_ISSUER_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_successor_execution_authorization_issuer_v1_review.json"
)
C4_ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "canonical_synthetic_prefix_c4_single_use_execution_authorization_v1.py"
)
MECHANISM_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_v1.py"
)
MECHANISM_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_mechanism_admission_successor_v1.py.tmpl"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_reconciliation_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_"
    "reconciliation_v1_review.json"
)

NEXT_GATE: Final = (
    "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1"
)


class ReconciliationError(RuntimeError):
    """Fail-closed reconciliation validation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError("P5_P6_TX_RECONCILIATION_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Authority(FrozenModel):
    authority_id: str
    role: Literal[
        "AUTHORIZATION_ARCHITECTURE",
        "AUTHORIZATION_IMPLEMENTATION_PRECEDENT",
        "AUTHORIZATION_RUNTIME_INTEGRATION_PRECEDENT",
        "CURRENT_BEHAVIORAL_DESIGN",
        "CURRENT_BEHAVIORAL_IMPLEMENTATION",
        "CURRENT_SUPERSEDED_AUTHORIZATION_TOPOLOGY",
        "CURRENT_TRANSACTION_BOUND_PRECEDENT",
    ]
    merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")


class PreservedMechanismBoundary(FrozenModel):
    semantic_states: tuple[
        Literal["EXACT_MATCH"],
        Literal["VALID_JSON_MISMATCH"],
        Literal["NON_OBJECT_JSON"],
        Literal["INVALID_JSON"],
    ]
    semantic_mismatch_blocks_mechanism: Literal[False]
    invalid_json_blocks_mechanism: Literal[False]
    finish_reason_stop_required: Literal[True]
    response_content_digest_required: Literal[True]
    raw_output_logging_permitted: Literal[False]
    p5_uses_semantic_state: Literal[False]
    p6_uses_semantic_state: Literal[False]
    p5_acceptance_relaxed: Literal[False]
    p6_acceptance_relaxed: Literal[False]


class AuthorizationArchitecture(FrozenModel):
    decision: Literal["TRANSACTION_BOUND_EXECUTION_ARTIFACT"]
    fresh_human_authority_required: Literal[True]
    operator_confirmation_method: Literal["RETYPE_DYNAMIC_SHA256_CHALLENGE"]
    transaction_id_derivation: Literal["SHA256_CANONICAL_AUTHORIZATION_BYTES"]
    authorization_specific_kaggle_inputs: Literal[0]
    authorization_producer_notebooks: Literal[0]
    manual_confirmation_json_files: Literal[0]
    runtime_authorization_filename_discovery_permitted: Literal[False]
    preissuance_platform_observation_required: Literal[False]
    fresh_post_artifact_observation_required: Literal[True]
    durable_platform_observation_required: Literal[True]
    observation_mounted_as_runtime_input: Literal[False]
    maximum_kaggle_save_and_run_all_actions: Literal[1]
    permitted_kaggle_input_roles: tuple[Literal["durable_runtime"], Literal["model_snapshot"]]
    single_use_governance_required: Literal[True]
    terminal_disposition_required: Literal[True]
    runtime_anti_replay_established: Literal[False]


class ExecutionBudget(FrozenModel):
    maximum_model_requests: Literal[6]
    maximum_worker_starts: Literal[3]
    maximum_model_loads: Literal[3]
    maximum_hidden_retries: Literal[0]
    maximum_replacement_workers: Literal[0]
    maximum_external_network_requests: Literal[0]
    maximum_benchmark_trajectory_requests: Literal[0]
    maximum_external_spend: Literal[0]


class SupersededTopology(FrozenModel):
    merge_commit: Literal["f33c835414b89dca15976e30877d7f0ebfa96e06"]
    prior_transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"]
    prior_exact_flat_file_count: Literal[3]
    disposition: Literal["IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE"]
    historical_files_preserved: Literal[True]
    live_authorization_issued: Literal[False]
    runtime_execution_authorized: Literal[False]
    kaggle_execution_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_requests_performed: Literal[0]
    reuse_as_current_authority_permitted: Literal[False]


class ReconciliationRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal[
        "auragateway-p5-p6-mechanism-admission-transaction-bound-authorization-reconciliation-v1"
    ]
    status: Literal["DESIGN_RECONCILED_NOT_IMPLEMENTED"]
    base_main_commit: Literal["f33c835414b89dca15976e30877d7f0ebfa96e06"]
    decision: Literal["RESTORE_TRANSACTION_BOUND_AUTHORIZATION_FOR_MECHANISM_ADMISSION_SUCCESSOR"]
    behavioral_predecessor: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"]
    authorization_predecessor: Literal["TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1"]
    regression_origin: Literal[
        "MECHANISM_SUCCESSOR_DESIGN_INHERITED_V2_AUTHORIZATION_TRANSPORT_"
        "WITHOUT_SUPERSEDING_AUTHORITY_RECONCILIATION"
    ]
    authorities: tuple[Authority, ...]
    preserved_mechanism_boundary: PreservedMechanismBoundary
    authorization_architecture: AuthorizationArchitecture
    execution_budget: ExecutionBudget
    superseded_topology: SupersededTopology
    mechanism_successor_runtime_mutated: Literal[False]
    superseded_issuer_files_mutated: Literal[False]
    live_authorization_issued: Literal[False]
    runtime_execution_authorized: Literal[False]
    kaggle_execution_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_requests_performed: Literal[0]
    next_gate: Literal[
        "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1"
    ]

    @model_validator(mode="after")
    def validate_authority_split(self) -> Self:
        if self.authorization_architecture.permitted_kaggle_input_roles != (
            "durable_runtime",
            "model_snapshot",
        ):
            raise ValueError("transaction-bound Kaggle input roles drifted")
        if self.superseded_topology.reuse_as_current_authority_permitted:
            raise ValueError("superseded control transport cannot remain current authority")
        return self


class ReconciliationReview(FrozenModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal[
        "auragateway-p5-p6-mechanism-admission-transaction-bound-authorization-"
        "reconciliation-v1-review"
    ]
    status: Literal["APPROVED_FOR_DESIGN_RECONCILIATION"]
    design_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transaction_bound_architecture_valid: Literal[True]
    mechanism_semantics_preserved: Literal[True]
    superseded_transport_preserved_as_history: Literal[True]
    authorization_specific_kaggle_inputs: Literal[0]
    authorization_producer_notebooks: Literal[0]
    live_authorization_issued: Literal[False]
    runtime_execution_authorized: Literal[False]
    next_gate: Literal[
        "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1"
    ]


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_AUTHORITY_MISSING",
            f"required authority is missing: {relative.as_posix()}",
        )
    return path.read_bytes()


def _read_json(repo_root: Path, relative: Path) -> object:
    try:
        return json.loads(_read_bytes(repo_root, relative).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_AUTHORITY_INVALID_JSON",
            f"required authority is not canonical readable JSON: {relative.as_posix()}",
        ) from error


def build_record() -> ReconciliationRecord:
    return ReconciliationRecord(
        schema_version="1.0.0",
        record_id=(
            "auragateway-p5-p6-mechanism-admission-transaction-bound-"
            "authorization-reconciliation-v1"
        ),
        status="DESIGN_RECONCILED_NOT_IMPLEMENTED",
        base_main_commit=BASE_MAIN_COMMIT,
        decision=("RESTORE_TRANSACTION_BOUND_AUTHORIZATION_FOR_MECHANISM_ADMISSION_SUCCESSOR"),
        behavioral_predecessor="EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2",
        authorization_predecessor="TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1",
        regression_origin=(
            "MECHANISM_SUCCESSOR_DESIGN_INHERITED_V2_AUTHORIZATION_TRANSPORT_"
            "WITHOUT_SUPERSEDING_AUTHORITY_RECONCILIATION"
        ),
        authorities=(
            Authority(
                authority_id="transaction_bound_architecture",
                role="AUTHORIZATION_ARCHITECTURE",
                merge_commit=ARCHITECTURE_MERGE_COMMIT,
            ),
            Authority(
                authority_id="transaction_bound_implementation",
                role="AUTHORIZATION_IMPLEMENTATION_PRECEDENT",
                merge_commit=TRANSACTION_BOUND_IMPLEMENTATION_MERGE_COMMIT,
            ),
            Authority(
                authority_id="transaction_bound_p5_p6_runtime_integration",
                role="AUTHORIZATION_RUNTIME_INTEGRATION_PRECEDENT",
                merge_commit=TRANSACTION_BOUND_RUNTIME_INTEGRATION_MERGE_COMMIT,
            ),
            Authority(
                authority_id="c4_transaction_bound_authorization_design",
                role="CURRENT_TRANSACTION_BOUND_PRECEDENT",
                merge_commit=C4_AUTHORIZATION_DESIGN_MERGE_COMMIT,
            ),
            Authority(
                authority_id="mechanism_admission_successor_design",
                role="CURRENT_BEHAVIORAL_DESIGN",
                merge_commit=MECHANISM_SUCCESSOR_DESIGN_MERGE_COMMIT,
            ),
            Authority(
                authority_id="mechanism_admission_successor_implementation",
                role="CURRENT_BEHAVIORAL_IMPLEMENTATION",
                merge_commit=MECHANISM_SUCCESSOR_IMPLEMENTATION_MERGE_COMMIT,
            ),
            Authority(
                authority_id="mechanism_admission_exact_flat_issuer",
                role="CURRENT_SUPERSEDED_AUTHORIZATION_TOPOLOGY",
                merge_commit=SUPERSEDED_ISSUER_MERGE_COMMIT,
            ),
        ),
        preserved_mechanism_boundary=PreservedMechanismBoundary(
            semantic_states=(
                "EXACT_MATCH",
                "VALID_JSON_MISMATCH",
                "NON_OBJECT_JSON",
                "INVALID_JSON",
            ),
            semantic_mismatch_blocks_mechanism=False,
            invalid_json_blocks_mechanism=False,
            finish_reason_stop_required=True,
            response_content_digest_required=True,
            raw_output_logging_permitted=False,
            p5_uses_semantic_state=False,
            p6_uses_semantic_state=False,
            p5_acceptance_relaxed=False,
            p6_acceptance_relaxed=False,
        ),
        authorization_architecture=AuthorizationArchitecture(
            decision="TRANSACTION_BOUND_EXECUTION_ARTIFACT",
            fresh_human_authority_required=True,
            operator_confirmation_method="RETYPE_DYNAMIC_SHA256_CHALLENGE",
            transaction_id_derivation="SHA256_CANONICAL_AUTHORIZATION_BYTES",
            authorization_specific_kaggle_inputs=0,
            authorization_producer_notebooks=0,
            manual_confirmation_json_files=0,
            runtime_authorization_filename_discovery_permitted=False,
            preissuance_platform_observation_required=False,
            fresh_post_artifact_observation_required=True,
            durable_platform_observation_required=True,
            observation_mounted_as_runtime_input=False,
            maximum_kaggle_save_and_run_all_actions=1,
            permitted_kaggle_input_roles=("durable_runtime", "model_snapshot"),
            single_use_governance_required=True,
            terminal_disposition_required=True,
            runtime_anti_replay_established=False,
        ),
        execution_budget=ExecutionBudget(
            maximum_model_requests=6,
            maximum_worker_starts=3,
            maximum_model_loads=3,
            maximum_hidden_retries=0,
            maximum_replacement_workers=0,
            maximum_external_network_requests=0,
            maximum_benchmark_trajectory_requests=0,
            maximum_external_spend=0,
        ),
        superseded_topology=SupersededTopology(
            merge_commit=SUPERSEDED_ISSUER_MERGE_COMMIT,
            prior_transport_contract="GOVERNED_ROOT_EXACT_FLAT_V1",
            prior_exact_flat_file_count=3,
            disposition="IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE",
            historical_files_preserved=True,
            live_authorization_issued=False,
            runtime_execution_authorized=False,
            kaggle_execution_performed=False,
            gpu_execution_performed=False,
            model_requests_performed=0,
            reuse_as_current_authority_permitted=False,
        ),
        mechanism_successor_runtime_mutated=False,
        superseded_issuer_files_mutated=False,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        kaggle_execution_performed=False,
        gpu_execution_performed=False,
        model_requests_performed=0,
        next_gate=NEXT_GATE,
    )


def build_review(record: ReconciliationRecord) -> ReconciliationReview:
    record_bytes = _canonical_json_bytes(record.model_dump(mode="json"))
    return ReconciliationReview(
        schema_version="1.0.0",
        review_id=(
            "auragateway-p5-p6-mechanism-admission-transaction-bound-"
            "authorization-reconciliation-v1-review"
        ),
        status="APPROVED_FOR_DESIGN_RECONCILIATION",
        design_record_sha256=_sha256(record_bytes),
        transaction_bound_architecture_valid=True,
        mechanism_semantics_preserved=True,
        superseded_transport_preserved_as_history=True,
        authorization_specific_kaggle_inputs=0,
        authorization_producer_notebooks=0,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def _validate_current_authorities(repo_root: Path) -> None:
    root = repo_root.resolve()
    if _sha256(_read_bytes(root, ARCHITECTURE_RECORD_PATH)) != ARCHITECTURE_RECORD_SHA256:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_ARCHITECTURE_DRIFT",
            "transaction-bound authorization architecture identity drifted",
        )
    if _sha256(_read_bytes(root, MECHANISM_DESIGN_PATH)) != MECHANISM_DESIGN_SHA256:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_MECHANISM_DESIGN_DRIFT",
            "mechanism-admission successor design identity drifted",
        )
    if (
        _sha256(_read_bytes(root, MECHANISM_IMPLEMENTATION_REVIEW_PATH))
        != MECHANISM_IMPLEMENTATION_REVIEW_SHA256
    ):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_IMPLEMENTATION_REVIEW_DRIFT",
            "mechanism-admission implementation review identity drifted",
        )

    architecture = _read_json(root, ARCHITECTURE_RECORD_PATH)
    if not isinstance(architecture, dict):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_ARCHITECTURE_SHAPE_INVALID",
            "transaction-bound architecture record is not an object",
        )
    burden = architecture.get("operator_burden_budget")
    if not isinstance(burden, dict):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_ARCHITECTURE_BUDGET_MISSING",
            "transaction-bound architecture operator budget is missing",
        )
    if architecture.get("decision") != "TRANSACTION_BOUND_EXECUTION_ARTIFACT":
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_ARCHITECTURE_DECISION_DRIFT",
            "transaction-bound architecture decision drifted",
        )
    if burden.get("maximum_authorization_specific_kaggle_inputs") != 0:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_KAGGLE_INPUT_REGRESSION",
            "authorization-specific Kaggle inputs are prohibited",
        )
    if burden.get("maximum_authorization_producer_notebooks") != 0:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_PRODUCER_NOTEBOOK_REGRESSION",
            "authorization producer notebooks are prohibited",
        )

    runtime_integration = _read_json(root, TRANSACTION_BOUND_RUNTIME_INTEGRATION_PATH)
    if not isinstance(runtime_integration, dict):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_RUNTIME_INTEGRATION_INVALID",
            "transaction-bound runtime integration record is not an object",
        )
    if runtime_integration.get("authorization_specific_kaggle_inputs") != 0:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_RUNTIME_INTEGRATION_REGRESSION",
            "transaction-bound P5/P6 integration no longer proves zero auth inputs",
        )
    if runtime_integration.get("authorization_producer_notebooks") != 0:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_RUNTIME_PRODUCER_REGRESSION",
            "transaction-bound P5/P6 integration no longer proves zero auth producers",
        )

    issuer_record = _read_json(root, SUPERSEDED_ISSUER_RECORD_PATH)
    issuer_review = _read_json(root, SUPERSEDED_ISSUER_REVIEW_PATH)
    if not isinstance(issuer_record, dict) or not isinstance(issuer_review, dict):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_SUPERSEDED_ISSUER_INVALID",
            "superseded issuer governance artifacts are invalid",
        )
    if issuer_record.get("live_authorization_issued") is not False:
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_LIVE_AUTHORIZATION_PRESENT",
            "superseded issuer cannot be reconciled after live issuance without evidence intake",
        )
    if issuer_record.get("transport_contract") != "GOVERNED_ROOT_EXACT_FLAT_V1":
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_SUPERSEDED_TRANSPORT_DRIFT",
            "superseded issuer transport identity drifted",
        )

    c4_source = _read_bytes(root, C4_ISSUER_SOURCE_PATH).decode("utf-8")
    required_c4_markers = (
        "RETYPE_DYNAMIC_SHA256_CHALLENGE",
        "PLATFORM_OBSERVATION_RECEIPT_PATH",
        "observation_mounted_as_runtime_input",
    )
    if any(marker not in c4_source for marker in required_c4_markers):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_CURRENT_PRECEDENT_DRIFT",
            "current C4 transaction-bound issuer precedent drifted",
        )

    for path in (MECHANISM_RUNTIME_PATH, MECHANISM_TEMPLATE_PATH):
        _read_bytes(root, path)


def write_generated(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _validate_current_authorities(root)
    record = build_record()
    review = build_review(record)
    record_bytes = _canonical_json_bytes(record.model_dump(mode="json"))
    review_bytes = _canonical_json_bytes(review.model_dump(mode="json"))
    (root / RECORD_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / REVIEW_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / RECORD_PATH).write_bytes(record_bytes)
    (root / REVIEW_PATH).write_bytes(review_bytes)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_TX_AUTH_RECONCILIATION_WRITTEN",
        "record_sha256": _sha256(record_bytes),
        "review_sha256": _sha256(review_bytes),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _validate_current_authorities(root)
    expected_record = build_record()
    expected_review = build_review(expected_record)
    record_bytes = _read_bytes(root, RECORD_PATH)
    review_bytes = _read_bytes(root, REVIEW_PATH)
    if record_bytes != _canonical_json_bytes(expected_record.model_dump(mode="json")):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_RECORD_DRIFT",
            "generated reconciliation record drifted",
        )
    if review_bytes != _canonical_json_bytes(expected_review.model_dump(mode="json")):
        raise ReconciliationError(
            "P5_P6_TX_RECONCILIATION_REVIEW_DRIFT",
            "generated reconciliation review drifted",
        )
    record = ReconciliationRecord.model_validate_json(record_bytes)
    review = ReconciliationReview.model_validate_json(review_bytes)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_TX_AUTH_RECONCILIATION_VALID",
        "decision": record.decision,
        "behavioral_predecessor": record.behavioral_predecessor,
        "authorization_predecessor": record.authorization_predecessor,
        "superseded_topology_disposition": record.superseded_topology.disposition,
        "authorization_specific_kaggle_inputs": (
            record.authorization_architecture.authorization_specific_kaggle_inputs
        ),
        "authorization_producer_notebooks": (
            record.authorization_architecture.authorization_producer_notebooks
        ),
        "mechanism_semantics_preserved": review.mechanism_semantics_preserved,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("write", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "write":
            result = write_generated(Path(args.repo_root))
        else:
            result = validate(Path(args.repo_root))
    except (ReconciliationError, ValidationError, OSError) as error:
        if isinstance(error, ReconciliationError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "P5_P6_TX_RECONCILIATION_VALIDATION_FAILED"
            message = str(error)
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=__import__("sys").stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
