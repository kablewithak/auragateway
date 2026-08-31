"""Bind the frozen final-342 execution subject to a static authority contract.

This boundary is deliberately non-authorizing. It binds the exact repository-frozen
execution manifest, post-commit custody receipt, transaction wrapper, runtime core, and
final evidence producer into the subject a later single-use issuer must qualify against.
It performs no model, GPU, Kaggle, network, live issuance, or measured execution work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import final_342_execution_manifest_freeze_v1 as manifest_freeze
from auragateway.local_abc import (
    final_342_execution_manifest_post_commit_custody_v1 as custody,
)
from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_transaction_wrapper_rehearsal_v1 as wrapper

BASE_MAIN_COMMIT = "12a57d5ee101336d1716671cb2d7c8a016f33d2e"

RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_static_execution_authority_binding_v1.json"
)
MANIFEST_PATH = Path("data/evals/benchmark/freeze-v3/final_342_execution_manifest_v1.json")
CUSTODY_PATH = Path(
    "data/evals/benchmark/freeze-v3/final_342_execution_manifest_post_commit_custody_v1.json"
)
ARCHITECTURE_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_runtime_requalification_architecture_v1.json"
)
RUNTIME_CORE_PATH = Path("src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py")
WRAPPER_REHEARSAL_PATH = Path(
    "src/auragateway/local_abc/final_342_transaction_wrapper_rehearsal_v1.py"
)
WRAPPER_TEMPLATE_PATH = Path(
    "src/auragateway/local_abc/templates/final_342_transaction_bound_wrapper_v1.py.tmpl"
)
PRODUCER_PATH = Path("src/auragateway/local_abc/final_342_execution_producer_v1.py")

EXPECTED_GIT_BLOBS: dict[str, str] = {
    MANIFEST_PATH.as_posix(): "2c733e930b88bca5f8ad0730d6828a88f8655e14",
    CUSTODY_PATH.as_posix(): "b1dfbbdc81cc07bda94dda71ab6983d6d069b01c",
    ARCHITECTURE_PATH.as_posix(): "9e88bf8536f2afdfb5f4f2812df06eab61ddb02c",
    RUNTIME_CORE_PATH.as_posix(): "7edeb7cb3f6c2213868d23863c33a9a94669468c",
    WRAPPER_REHEARSAL_PATH.as_posix(): "81470c097a23374b7495f1a058765c6c10718bd2",
    WRAPPER_TEMPLATE_PATH.as_posix(): "9901e2d7e6f3fb011e66b406d32b53f1dfe84a68",
    PRODUCER_PATH.as_posix(): "9bedae7c7815e80d7c03ccc37b1e5261310056cf",
}

EXPECTED_MANIFEST_SEMANTIC_SHA256 = (
    "11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b"
)
EXPECTED_MANIFEST_FILE_SHA256 = "74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c"
EXPECTED_FIRST_CONTAINING_COMMIT = "078c1da32fe7c1ee8ff5a8661e5f38e588782abc"
EXPECTED_CUSTODY_COMMIT = "3746be6a912e7d2f30a88d829a9cff7dbda53c87"

EXPECTED_TRAJECTORY_COUNT: Literal[342] = 342
EXPECTED_TURN_COUNT: Literal[1368] = 1368
EXPECTED_MAXIMUM_REQUEST_ATTEMPTS: Literal[2736] = 2736

AUTHORIZATION_SCOPE = "FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1"
NEXT_GATE = "QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1"


class StaticAuthorityBindingError(RuntimeError):
    """Metadata-safe static authority-binding failure."""

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
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactBinding(FrozenModel):
    path: str
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenManifestBinding(FrozenModel):
    manifest_id: Literal["auragateway-final-342-execution-manifest-v1"]
    manifest_semantic_sha256: Literal[
        "11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b"
    ]
    manifest_file_sha256: Literal[
        "74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c"
    ]
    first_containing_commit: Literal["078c1da32fe7c1ee8ff5a8661e5f38e588782abc"]
    custody_commit: Literal["3746be6a912e7d2f30a88d829a9cff7dbda53c87"]
    post_commit_custody_complete: Literal[True] = True
    repository_execution_manifest_frozen: Literal[True] = True
    repository_freeze_gate_promoted: Literal[True] = True


class ExecutionBudget(FrozenModel):
    planned_trajectory_count: Literal[342] = EXPECTED_TRAJECTORY_COUNT
    planned_turn_count: Literal[1368] = EXPECTED_TURN_COUNT
    maximum_request_attempt_count: Literal[2736] = EXPECTED_MAXIMUM_REQUEST_ATTEMPTS
    maximum_retries_after_initial_attempt: Literal[1] = 1
    hidden_retries_permitted: Literal[False] = False
    replacement_cases_permitted: Literal[False] = False
    extra_authority_canary_requests_permitted: Literal[False] = False
    extra_worker_qualification_requests_permitted: Literal[False] = False
    external_spend_ceiling: Literal[0] = 0


class ExecutionSubjectContract(FrozenModel):
    authorization_scope: Literal["FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1"]
    final_manifest_identity_required_on_every_trace: Literal[True] = True
    transaction_bound_execution_artifact_required: Literal[True] = True
    runtime_payload_identity_bound: Literal[True] = True
    route_derived_from_planned_run_only: Literal[True] = True
    same_single_local_model_alias_for_both_route_families: Literal[True] = True
    loopback_vllm_transport_only: Literal[True] = True
    single_use_is_governance_invariant: Literal[True] = True
    multiple_observed_executions_for_one_transaction_invalidate_acceptance: Literal[True] = True
    runtime_anti_replay_established: Literal[False] = False


class AuthorityBoundary(FrozenModel):
    static_authority_binding_complete: Literal[True] = True
    execution_manifest_freeze_is_live_authority: Literal[False] = False
    static_binding_is_live_issuance: Literal[False] = False
    issuer_capability_is_live_issuance: Literal[False] = False
    old_authorization_reusable_true_semantics_permitted: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False


class IssuerQualificationBoundary(FrozenModel):
    exact_static_binding_required: Literal[True] = True
    exact_frozen_manifest_required: Literal[True] = True
    exact_custody_receipt_required: Literal[True] = True
    qualification_may_issue_live_authority: Literal[False] = False
    fresh_platform_readiness_required_after_qualification: Literal[True] = True
    fresh_human_authority_required_after_qualification: Literal[True] = True
    governed_execution_permitted_during_qualification: Literal[False] = False


class SafetyState(FrozenModel):
    effect_claims_permitted: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    network_transport_performed: Literal[False] = False


class Final342StaticExecutionAuthorityBinding(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    binding_id: Literal["auragateway-final-342-static-execution-authority-binding-v1"]
    status: Literal["BOUND_NOT_ISSUED"]
    source_main_commit: Literal["12a57d5ee101336d1716671cb2d7c8a016f33d2e"]
    frozen_manifest: FrozenManifestBinding
    execution_budget: ExecutionBudget
    execution_subject: ExecutionSubjectContract
    authority_boundary: AuthorityBoundary
    issuer_qualification_boundary: IssuerQualificationBoundary
    bound_artifacts: tuple[ArtifactBinding, ...]
    safety_state: SafetyState
    next_gate: Literal["QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1"]

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if len(self.bound_artifacts) != len(EXPECTED_GIT_BLOBS):
            raise ValueError("static authority artifact boundary count drifted")
        observed = {item.path: item.git_blob_sha for item in self.bound_artifacts}
        if observed != EXPECTED_GIT_BLOBS:
            raise ValueError("static authority artifact boundary identity drifted")
        return self


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_text(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_GIT_FAILED",
            "required Git authority-binding inspection failed",
        )
    return completed.stdout.strip()


def _git_bytes(root: Path, revision_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", revision_path],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_GIT_SHOW_FAILED",
            "required Git artifact bytes could not be read",
        )
    return completed.stdout


def _require_base_main(root: Path, *, exact: bool) -> None:
    head = _git_text(root, "rev-parse", "HEAD")
    if exact and head != BASE_MAIN_COMMIT:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_SOURCE_MAIN_DRIFT",
            "static authority materialization must begin from exact accepted main",
        )

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_SOURCE_MAIN_NOT_ANCESTOR",
            "accepted static-authority source main is not an ancestor",
        )


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_REQUIRED_FILE_MISSING",
            "required static-authority artifact is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _artifact_binding(root: Path, relative: Path) -> ArtifactBinding:
    expected_blob = EXPECTED_GIT_BLOBS[relative.as_posix()]
    committed_blob = _git_text(
        root,
        "rev-parse",
        f"{BASE_MAIN_COMMIT}:{relative.as_posix()}",
    )
    if committed_blob != expected_blob:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_BASE_BLOB_DRIFT",
            "accepted main artifact Git identity drifted",
            relative,
        )

    committed = _git_bytes(root, f"{BASE_MAIN_COMMIT}:{relative.as_posix()}")
    working = _read_required(root, relative)
    if working != committed:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_UPSTREAM_DRIFT",
            "bound execution artifact differs from accepted main",
            relative,
        )

    return ArtifactBinding(
        path=relative.as_posix(),
        git_blob_sha=committed_blob,
        sha256=sha256_bytes(committed),
    )


def _validate_architecture(root: Path) -> None:
    raw = _read_required(root, ARCHITECTURE_PATH)
    try:
        architecture = json.loads(raw)
    except json.JSONDecodeError as error:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_ARCHITECTURE_INVALID",
            "runtime architecture JSON is invalid",
            ARCHITECTURE_PATH,
        ) from error
    if not isinstance(architecture, dict):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_ARCHITECTURE_INVALID",
            "runtime architecture root is invalid",
            ARCHITECTURE_PATH,
        )

    expected_sequence = [
        "IMPLEMENT_FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1",
        "REHEARSE_FINAL_342_TRANSACTION_WRAPPER_V1",
        "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1",
        "BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1",
        "QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1",
        "FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY",
        "ONE_GOVERNED_FINAL_342_EXECUTION",
    ]
    if architecture.get("implementation_sequence") != expected_sequence:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_SEQUENCE_DRIFT",
            "accepted final-342 implementation sequence drifted",
            ARCHITECTURE_PATH,
        )

    authorization = architecture.get("authorization_boundary")
    if not isinstance(authorization, dict):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_BOUNDARY_INVALID",
            "runtime authorization boundary is invalid",
            ARCHITECTURE_PATH,
        )

    expected_authorization = {
        "execution_manifest_freeze_is_authority": False,
        "final_measured_abc_execution_authorized": False,
        "issuer_capability_is_live_issuance": False,
        "multiple_observed_executions_for_one_transaction_invalidate_acceptance": True,
        "new_execution_authorized": False,
        "old_authorization_reusable_true_semantics_permitted_in_successor": False,
        "runner_implementation_is_authority": False,
        "runtime_anti_replay_established": False,
        "single_use_is_governance_invariant": True,
    }
    if any(authorization.get(key) != value for key, value in expected_authorization.items()):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_BOUNDARY_DRIFT",
            "accepted final-342 authorization boundary drifted",
            ARCHITECTURE_PATH,
        )


def _validate_frozen_subject(root: Path) -> None:
    manifest_result = manifest_freeze.validate(root)
    if (
        manifest_result.get("manifest_semantic_sha256") != EXPECTED_MANIFEST_SEMANTIC_SHA256
        or manifest_result.get("manifest_file_sha256") != EXPECTED_MANIFEST_FILE_SHA256
        or manifest_result.get("manifest_subject_bytes_frozen") is not True
        or manifest_result.get("final_measured_abc_execution_authorized") is not False
    ):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_MANIFEST_DRIFT",
            "frozen execution manifest validation drifted",
            MANIFEST_PATH,
        )

    custody_result = custody.validate(root)
    if (
        custody_result.get("first_containing_commit") != EXPECTED_FIRST_CONTAINING_COMMIT
        or custody_result.get("post_commit_custody_complete") is not True
        or custody_result.get("repository_execution_manifest_frozen") is not True
        or custody_result.get("repository_freeze_gate_promoted") is not True
        or custody_result.get("final_measured_abc_execution_authorized") is not False
    ):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_CUSTODY_DRIFT",
            "post-commit manifest custody validation drifted",
            CUSTODY_PATH,
        )

    if _git_text(root, "rev-parse", f"{EXPECTED_CUSTODY_COMMIT}^") != (
        EXPECTED_FIRST_CONTAINING_COMMIT
    ):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_CUSTODY_LINEAGE_DRIFT",
            "custody commit no longer directly follows first-containing commit",
        )


def _validate_execution_subject(root: Path) -> None:
    wrapper_result = wrapper.validate_implementation(root)
    expected_wrapper = {
        "status": "FINAL_342_TRANSACTION_WRAPPER_REHEARSAL_V1_VALID",
        "planned_trajectories": EXPECTED_TRAJECTORY_COUNT,
        "realized_turns": EXPECTED_TURN_COUNT,
        "maximum_request_attempts": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "runtime_payload_identity_bound": True,
        "real_module_graph_structural_rehearsal": True,
        "authorization_producer_notebooks_permitted": False,
        "authorization_specific_kaggle_inputs_permitted": False,
        "manual_confirmation_json_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "live_authorization_issued": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
    }
    if any(wrapper_result.get(key) != value for key, value in expected_wrapper.items()):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_WRAPPER_DRIFT",
            "transaction-wrapper rehearsal no longer matches accepted subject",
            WRAPPER_REHEARSAL_PATH,
        )

    producer_result = producer.validate(root)
    expected_producer = {
        "status": "FINAL_342_EXECUTION_PRODUCER_V1_IMPLEMENTATION_VALID",
        "planned_trajectory_count": EXPECTED_TRAJECTORY_COUNT,
        "planned_turn_count": EXPECTED_TURN_COUNT,
        "maximum_request_attempt_count": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "per_trace_final_manifest_binding_implemented": True,
        "worker_startup_composition_implemented": True,
        "request_transport_composition_implemented": True,
        "typed_turn_measurement_persistence_implemented": True,
        "attempt_reconciliation_persistence_implemented": True,
        "primary_secondary_failure_persistence_implemented": True,
        "teardown_cleanup_evidence_implemented": True,
        "measured_evidence_bundle_writer_implemented": True,
        "local_runtime_provider_field_mapping_implemented": True,
        "one_shot_v2_adapter_permitted": False,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
    }
    if any(producer_result.get(key) != value for key, value in expected_producer.items()):
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_PRODUCER_DRIFT",
            "final execution producer no longer matches accepted subject",
            PRODUCER_PATH,
        )


def build_binding(root: Path) -> Final342StaticExecutionAuthorityBinding:
    root = root.resolve()
    _require_base_main(root, exact=False)
    _validate_architecture(root)
    _validate_frozen_subject(root)
    _validate_execution_subject(root)

    paths = tuple(Path(path) for path in EXPECTED_GIT_BLOBS)
    artifacts = tuple(_artifact_binding(root, path) for path in paths)

    return Final342StaticExecutionAuthorityBinding(
        binding_id="auragateway-final-342-static-execution-authority-binding-v1",
        status="BOUND_NOT_ISSUED",
        source_main_commit=BASE_MAIN_COMMIT,
        frozen_manifest=FrozenManifestBinding(
            manifest_id="auragateway-final-342-execution-manifest-v1",
            manifest_semantic_sha256=EXPECTED_MANIFEST_SEMANTIC_SHA256,
            manifest_file_sha256=EXPECTED_MANIFEST_FILE_SHA256,
            first_containing_commit=EXPECTED_FIRST_CONTAINING_COMMIT,
            custody_commit=EXPECTED_CUSTODY_COMMIT,
        ),
        execution_budget=ExecutionBudget(),
        execution_subject=ExecutionSubjectContract(
            authorization_scope=AUTHORIZATION_SCOPE,
        ),
        authority_boundary=AuthorityBoundary(),
        issuer_qualification_boundary=IssuerQualificationBoundary(),
        bound_artifacts=artifacts,
        safety_state=SafetyState(),
        next_gate=NEXT_GATE,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.final-342-static-authority.tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    temporary.replace(path)


def materialize(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_base_main(root, exact=True)
    binding = build_binding(root)
    _write_atomic(
        root / RECORD_PATH,
        canonical_json_bytes(binding.model_dump(mode="json")),
    )
    return validate(root)


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected = build_binding(root)
    path = root / RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_RECORD_MISSING",
            "static execution-authority binding record is missing or unsafe",
            RECORD_PATH,
        )

    try:
        observed = Final342StaticExecutionAuthorityBinding.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_RECORD_INVALID",
            "static execution-authority binding failed typed validation",
            RECORD_PATH,
        ) from error

    if observed != expected:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_RECORD_DRIFT",
            "static execution-authority binding differs from reconstruction",
            RECORD_PATH,
        )
    canonical = canonical_json_bytes(observed.model_dump(mode="json"))
    if path.read_bytes() != canonical:
        raise StaticAuthorityBindingError(
            "FINAL_342_STATIC_AUTHORITY_RECORD_BYTES_DRIFT",
            "static execution-authority binding bytes are not canonical",
            RECORD_PATH,
        )

    return {
        "status": "FINAL_342_STATIC_EXECUTION_AUTHORITY_BINDING_V1_VALID",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "manifest_semantic_sha256": EXPECTED_MANIFEST_SEMANTIC_SHA256,
        "manifest_file_sha256": EXPECTED_MANIFEST_FILE_SHA256,
        "first_containing_commit": EXPECTED_FIRST_CONTAINING_COMMIT,
        "custody_commit": EXPECTED_CUSTODY_COMMIT,
        "static_authority_binding_complete": True,
        "repository_execution_manifest_frozen": True,
        "live_authorization_issued": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "network_transport_performed": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _Parser:
    parser = _Parser(prog="final-342-static-execution-authority-binding-v1")
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
    except (
        StaticAuthorityBindingError,
        OSError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        if isinstance(error, StaticAuthorityBindingError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path.as_posix() if error.path is not None else None,
            }
        else:
            payload = {
                "error_code": "FINAL_342_STATIC_AUTHORITY_BINDING_FAILED",
                "safe_message": str(error),
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
