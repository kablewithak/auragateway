"""Validate the transaction-bound execution authorization architecture V1."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RECORD_PATH = Path(
    "benchmarks/local_abc/"
    "auragateway_transaction_bound_execution_authorization_architecture_v1.json"
)

EXPECTED_BASE_MAIN = "a9c6632b29e9b470de0497ca6d72a2e2c2c91f62"


class ArchitectureError(RuntimeError):
    """Fail-closed architecture validation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ArchitectureError("TRANSACTION_BOUND_ARCH_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Problem(FrozenModel):
    authorization_required: Literal[True]
    current_authorization_specific_kaggle_input: Literal[True]
    current_authorization_control_producer: Literal[True]
    current_transport_schema_surface: Literal[True]
    current_manual_confirmation_json_required: Literal[True]


class RequiredInvariants(FrozenModel):
    fresh_human_authority: Literal[True]
    static_implementation_identity_bound: Literal[True]
    runtime_model_contract_bound: Literal[True]
    hard_execution_budget_bound: Literal[True]
    authorization_expiry_bound: Literal[True]
    single_use_governance_required: Literal[True]
    terminal_disposition_required_for_attempt: Literal[True]
    immutable_evidence_traceability_required: Literal[True]


class RejectedSuccessorTopology(FrozenModel):
    authorization_specific_kaggle_input_permitted: Literal[False]
    authorization_control_producer_notebook_permitted: Literal[False]
    runtime_authorization_filename_discovery_permitted: Literal[False]
    manual_confirmation_json_construction_permitted: Literal[False]


class TransactionIdentity(FrozenModel):
    transaction_id_derivation: Literal["SHA256_CANONICAL_AUTHORIZATION_BYTES"]
    whole_notebook_sha256_is_semantic_payload_identity: Literal[False]
    runtime_payload_sha256_bound: Literal[True]
    generator_contract_sha256_bound: Literal[True]
    canonical_authorization_bytes_bound: Literal[True]
    deterministic_generation_required: Literal[True]
    nonidentical_regeneration_requires_fresh_authority: Literal[True]


class RuntimeAdmission(FrozenModel):
    static_repository_artifact_governed_execution_permitted: Literal[False]
    transaction_bound_artifact_required: Literal[True]
    authorization_admission_precedes_runtime_installation: Literal[True]
    authorization_must_be_live_at_admission: Literal[True]
    completion_after_expiry_if_admitted_in_window_permitted: Literal[True]
    machine_observable_topology_check_required: Literal[True]


class PlatformObservation(FrozenModel):
    preissuance_observation_required: Literal[False]
    required_platform_policy_bound_by_authority: Literal[True]
    fresh_observation_after_artifact_generation_required: Literal[True]
    observation_precedes_save_and_run_all: Literal[True]
    observation_mounted_as_runtime_input: Literal[False]
    acceptance_binds_observation_to_transaction_and_saved_version: Literal[True]


class Replay(FrozenModel):
    single_use_is_governance_invariant: Literal[True]
    runtime_anti_replay_established: Literal[False]
    multiple_observed_executions_invalidate_acceptance: Literal[True]
    malicious_operator_resistance_established: Literal[False]


class FailureHandling(FrozenModel):
    primary_failure_preserved_separately: Literal[True]
    secondary_failure_may_mask_primary: Literal[False]
    terminalizable_without_governed_evidence_zip: Literal[True]


class OperatorBurden(FrozenModel):
    maximum_authorization_specific_kaggle_inputs: Literal[0]
    maximum_authorization_producer_notebooks: Literal[0]
    maximum_manual_confirmation_json_files: Literal[0]
    maximum_local_control_commands_after_merge: int = Field(ge=1, le=2)
    maximum_kaggle_save_and_run_all_actions: Literal[1]
    permitted_kaggle_input_roles: tuple[
        Literal["durable_runtime"],
        Literal["model_snapshot"],
    ]


class SourceMarkers(FrozenModel):
    issuer_path: str
    runtime_path: str
    issuer_transport_round_trip_marker: str
    issuer_post_issue_transport_marker: str
    runtime_authorization_consumer_marker: str
    runtime_control_producer_marker: str


class ImplementationStrategy(FrozenModel):
    immutable_v2_artifacts_rewritten: Literal[False]
    versioned_successor_required: Literal[True]
    cpu_or_manual_topology_rehearsal_before_gpu: Literal[True]
    gpu_execution_authorized_by_this_architecture: Literal[False]


class ArchitectureRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    architecture_id: Literal["auragateway-transaction-bound-execution-authorization-v1"]
    status: Literal["PROPOSED_FOR_ARCHITECTURE_ACCEPTANCE"]
    base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision: Literal["TRANSACTION_BOUND_EXECUTION_ARTIFACT"]
    problem: Problem
    required_invariants: RequiredInvariants
    rejected_successor_topology: RejectedSuccessorTopology
    transaction_identity: TransactionIdentity
    runtime_admission: RuntimeAdmission
    platform_observation: PlatformObservation
    replay: Replay
    failure_handling: FailureHandling
    operator_burden_budget: OperatorBurden
    current_v2_source_markers: SourceMarkers
    implementation_strategy: ImplementationStrategy
    next_gate: Literal["IMPLEMENT_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1"]

    @model_validator(mode="after")
    def validate_architecture_boundary(self) -> Self:
        if self.base_main_commit != EXPECTED_BASE_MAIN:
            raise ValueError("architecture base main drifted")
        if self.operator_burden_budget.permitted_kaggle_input_roles != (
            "durable_runtime",
            "model_snapshot",
        ):
            raise ValueError("permitted Kaggle input roles drifted")
        return self


def _read_text(repo_root: Path, relative: str) -> str:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise ArchitectureError(
            "TRANSACTION_BOUND_ARCH_SOURCE_MISSING",
            f"required architecture source is missing: {relative}",
        )
    return path.read_text(encoding="utf-8")


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    payload = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    record = ArchitectureRecord.model_validate(payload)

    markers = record.current_v2_source_markers
    issuer = _read_text(root, markers.issuer_path)
    runtime = _read_text(root, markers.runtime_path)

    required_issuer = (
        markers.issuer_transport_round_trip_marker,
        markers.issuer_post_issue_transport_marker,
    )
    required_runtime = (
        markers.runtime_authorization_consumer_marker,
        markers.runtime_control_producer_marker,
    )

    missing_issuer = tuple(marker for marker in required_issuer if marker not in issuer)
    missing_runtime = tuple(marker for marker in required_runtime if marker not in runtime)

    if missing_issuer or missing_runtime:
        raise ArchitectureError(
            "TRANSACTION_BOUND_ARCH_CURRENT_V2_COUPLING_DRIFT",
            "current V2 authorization coupling no longer matches architecture premise",
        )

    return {
        "status": "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE_V1_VALID",
        "decision": record.decision,
        "authorization_specific_kaggle_inputs": (
            record.operator_burden_budget.maximum_authorization_specific_kaggle_inputs
        ),
        "authorization_producer_notebooks": (
            record.operator_burden_budget.maximum_authorization_producer_notebooks
        ),
        "manual_confirmation_json_files": (
            record.operator_burden_budget.maximum_manual_confirmation_json_files
        ),
        "runtime_anti_replay_established": record.replay.runtime_anti_replay_established,
        "gpu_execution_authorized": (
            record.implementation_strategy.gpu_execution_authorized_by_this_architecture
        ),
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate(Path(args.repo_root))
    except (ArchitectureError, ValidationError, json.JSONDecodeError, OSError) as error:
        if isinstance(error, ArchitectureError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "TRANSACTION_BOUND_ARCH_VALIDATION_FAILED"
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

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
