"""Reconcile variance-pilot authorities after current-line P5/P6 Acceptance V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

BASE_MAIN_COMMIT: Final = "9d59d417c92f79a4540b01b7292f5bf6e655e0d2"

PILOT_SOURCE_PATH: Final = Path("src/auragateway/local_abc/measured_abc_variance_pilot_v1.py")
PILOT_SOURCE_GIT_BLOB: Final = "df2f00112144845bb60b2a9d7a84c9037f28aa4b"

PILOT_AUTHORIZATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_execution_authorization_v1.py"
)
PILOT_AUTHORIZATION_SOURCE_GIT_BLOB: Final = "f9cacfc7ceb285af700e51bd97a74bc76e5369ca"

PILOT_POLICY_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v1/variance_pilot_v1_policy.json"
)
PILOT_POLICY_GIT_BLOB: Final = "593ce135e505eeefd8afcc166580a4ba359cfaff"

PILOT_MANIFEST_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_manifest.json")
PILOT_MANIFEST_GIT_BLOB: Final = "a5f0194f21378b15c7093b5fc43b442e36e7ebfd"

PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_schedule.json")

PILOT_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_v1_design.json"
)
PILOT_DESIGN_GIT_BLOB: Final = "80a543ce73e2fc1405531b231afc58ab12b4e949"

CURRENT_P5_P6_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v2.json"
)
CURRENT_P5_P6_ACCEPTANCE_GIT_BLOB: Final = "2ac3e8f810568eb668467c631880cbd289159a3a"

HISTORICAL_P5_P6_ACCEPTANCE_PATH: Final = (
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
)
HISTORICAL_P5_P6_ACCEPTANCE_GIT_BLOB: Final = "2cac406ed4e8f2d5c50795d104d2db425abfcbac"

TRANSACTION_BOUND_ADR_PATH: Final = Path(
    "docs/adr/2026-08-11-local-abc-transaction-bound-execution-authorization-architecture-v1.md"
)
TRANSACTION_BOUND_ADR_GIT_BLOB: Final = "1a2761c123819d5ca52b6936d8c132dff78b2acc"

REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_current_line_reconciliation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_current_line_reconciliation_v1.json"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_current_line_reconciliation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_current_line_reconciliation_v1.py"
)

NEXT_GATE: Final = (
    "IMPLEMENT_VARIANCE_PILOT_TRANSACTION_BOUND_RUNTIME_LAUNCHER_AND_AUTHORIZATION_SUCCESSOR_V1"
)


class ReconciliationError(RuntimeError):
    """Metadata-safe current-line reconciliation failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
            "details": self.details,
        }


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactAuthority(StrictModel):
    path: str
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class CurrentRuntimeContract(StrictModel):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    required_native_module: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    attention_backend: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    gpu_topology: Literal["T4_X2"] = "T4_X2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class ReconciliationReview(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-measured-abc-variance-pilot-current-line-reconciliation-v1-review"
    ]
    base_main_commit: Literal["9d59d417c92f79a4540b01b7292f5bf6e655e0d2"] = BASE_MAIN_COMMIT
    decision: Literal["RECONCILE_BEFORE_RUNTIME_LAUNCHER_READINESS"] = (
        "RECONCILE_BEFORE_RUNTIME_LAUNCHER_READINESS"
    )
    current_p5_p6_acceptance: ArtifactAuthority
    historical_p5_p6_acceptance_binding_stale: Literal[True] = True
    historical_pilot_authorization_status: Literal[
        "IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE"
    ] = "IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE"
    transaction_bound_authorization_required: Literal[True] = True
    authorization_specific_kaggle_inputs_permitted: Literal[False] = False
    manual_confirmation_json_permitted: Literal[False] = False
    preissuance_platform_observation_required: Literal[False] = False
    post_artifact_platform_observation_required: Literal[True] = True
    current_runtime: CurrentRuntimeContract = CurrentRuntimeContract()
    pilot_case_count: Literal[6] = 6
    pilot_trajectory_count: Literal[54] = 54
    pilot_turn_count: Literal[216] = 216
    maximum_request_attempt_count: Literal[432] = 432
    hidden_retries_permitted: Literal[False] = False
    replacement_cases_permitted: Literal[False] = False
    current_timing_telemetry_qualification_established: Literal[False] = False
    timing_telemetry_must_fail_closed_before_pilot_requests: Literal[True] = True
    runtime_launcher_readiness_committed: Literal[False] = False
    variance_pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    non_claims: tuple[str, ...]
    next_gate: str


class ReconciliationRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-measured-abc-variance-pilot-current-line-reconciliation-v1"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    base_main_commit: Literal["9d59d417c92f79a4540b01b7292f5bf6e655e0d2"] = BASE_MAIN_COMMIT
    authorities: tuple[ArtifactAuthority, ...]
    p5_requalified: Literal[True] = True
    p6_requalified: Literal[True] = True
    c4_mechanism_qualified: Literal[True] = True
    c4_semantic_qualified: Literal[False] = False
    c4_semantic_state: Literal["INVALID_JSON"] = "INVALID_JSON"
    pilot_schedule_preserved: Literal[True] = True
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_manifest_binds_schedule: Literal[True] = True
    old_pilot_authorization_superseded: Literal[True] = True
    transaction_bound_successor_required: Literal[True] = True
    timing_telemetry_preflight_required: Literal[True] = True
    runtime_launcher_readiness_committed: Literal[False] = False
    variance_pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: str


def _canonical(payload: object) -> str:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if result.returncode != 0:
        raise ReconciliationError(
            "VARIANCE_PILOT_RECONCILIATION_GIT_FAILED",
            "required Git operation failed",
            details=(" ".join(args), result.stderr.strip()),
        )
    return result.stdout.strip()


def _require(condition: bool, code: str, message: str, path: Path | None = None) -> None:
    if condition:
        return
    raise ReconciliationError(
        code,
        message,
        path=None if path is None else path.as_posix(),
    )


def _validate_blob(repo_root: Path, relative: Path, expected: str) -> ArtifactAuthority:
    observed = _run_git(repo_root, "rev-parse", f"HEAD:{relative.as_posix()}")
    _require(
        observed == expected,
        "VARIANCE_PILOT_RECONCILIATION_AUTHORITY_DRIFT",
        "a reconciliation authority Git blob drifted",
        relative,
    )
    return ArtifactAuthority(path=relative.as_posix(), git_blob_sha=observed)


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ReconciliationError(
            "VARIANCE_PILOT_RECONCILIATION_FILE_MISSING",
            "required reconciliation file is missing",
            path=path.as_posix(),
        ) from error
    except json.JSONDecodeError as error:
        raise ReconciliationError(
            "VARIANCE_PILOT_RECONCILIATION_JSON_INVALID",
            "required reconciliation JSON is invalid",
            path=path.as_posix(),
        ) from error
    _require(
        isinstance(payload, dict),
        "VARIANCE_PILOT_RECONCILIATION_JSON_ROOT_INVALID",
        "required reconciliation JSON root must be one object",
        path,
    )
    return cast(dict[str, object], payload)


def _validate_current_acceptance(repo_root: Path) -> ArtifactAuthority:
    authority = _validate_blob(
        repo_root,
        CURRENT_P5_P6_ACCEPTANCE_PATH,
        CURRENT_P5_P6_ACCEPTANCE_GIT_BLOB,
    )
    payload = _load_json_object(repo_root / CURRENT_P5_P6_ACCEPTANCE_PATH)
    required = {
        "governed_acceptance_status": "ACCEPTED_GOVERNED_EXECUTION_PASS",
        "p5_requalified": True,
        "p6_requalified": True,
        "c4_mechanism_qualified": True,
        "c4_semantic_qualified": False,
        "c4_semantic_state": "INVALID_JSON",
        "variance_pilot_p5_p6_prerequisite_satisfied": True,
        "variance_pilot_authority_reconciliation_required": True,
        "variance_pilot_runtime_launcher_readiness_committed": False,
        "variance_pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, expected in required.items():
        _require(
            payload.get(key) == expected,
            "VARIANCE_PILOT_RECONCILIATION_ACCEPTANCE_STATE_DRIFT",
            f"current P5/P6 acceptance field drifted: {key}",
            CURRENT_P5_P6_ACCEPTANCE_PATH,
        )
    return authority


def _validate_stale_pilot_binding(repo_root: Path) -> tuple[ArtifactAuthority, ...]:
    pilot_source = _validate_blob(
        repo_root,
        PILOT_SOURCE_PATH,
        PILOT_SOURCE_GIT_BLOB,
    )
    policy = _validate_blob(
        repo_root,
        PILOT_POLICY_PATH,
        PILOT_POLICY_GIT_BLOB,
    )
    source_text = (repo_root / PILOT_SOURCE_PATH).read_text(encoding="utf-8")
    _require(
        HISTORICAL_P5_P6_ACCEPTANCE_PATH in source_text,
        "VARIANCE_PILOT_RECONCILIATION_STALE_BINDING_NOT_FOUND",
        "expected historical P5/P6 acceptance binding is absent",
        PILOT_SOURCE_PATH,
    )
    _require(
        HISTORICAL_P5_P6_ACCEPTANCE_GIT_BLOB in source_text,
        "VARIANCE_PILOT_RECONCILIATION_STALE_BLOB_NOT_FOUND",
        "expected historical P5/P6 acceptance blob is absent",
        PILOT_SOURCE_PATH,
    )
    policy_payload = _load_json_object(repo_root / PILOT_POLICY_PATH)
    bindings = policy_payload.get("authority_bindings")
    _require(
        isinstance(bindings, dict),
        "VARIANCE_PILOT_RECONCILIATION_POLICY_BINDINGS_INVALID",
        "variance-pilot policy authority bindings are invalid",
        PILOT_POLICY_PATH,
    )
    governed = cast(dict[str, object], bindings).get("governed_p5_p6_acceptance")
    _require(
        isinstance(governed, dict),
        "VARIANCE_PILOT_RECONCILIATION_POLICY_BINDING_MISSING",
        "variance-pilot policy P5/P6 authority binding is missing",
        PILOT_POLICY_PATH,
    )
    governed_dict = cast(dict[str, object], governed)
    _require(
        governed_dict.get("path") == HISTORICAL_P5_P6_ACCEPTANCE_PATH
        and governed_dict.get("git_blob_sha") == HISTORICAL_P5_P6_ACCEPTANCE_GIT_BLOB,
        "VARIANCE_PILOT_RECONCILIATION_POLICY_BINDING_DRIFT",
        "variance-pilot policy no longer has the expected historical binding",
        PILOT_POLICY_PATH,
    )
    return pilot_source, policy


def _validate_authorization_architecture(
    repo_root: Path,
) -> tuple[ArtifactAuthority, ArtifactAuthority]:
    authorization = _validate_blob(
        repo_root,
        PILOT_AUTHORIZATION_SOURCE_PATH,
        PILOT_AUTHORIZATION_SOURCE_GIT_BLOB,
    )
    adr = _validate_blob(
        repo_root,
        TRANSACTION_BOUND_ADR_PATH,
        TRANSACTION_BOUND_ADR_GIT_BLOB,
    )
    authorization_text = (repo_root / PILOT_AUTHORIZATION_SOURCE_PATH).read_text(encoding="utf-8")
    _require(
        "--confirmation-json" in authorization_text,
        "VARIANCE_PILOT_RECONCILIATION_OLD_CONFIRMATION_SEAM_ABSENT",
        "expected historical manual confirmation JSON seam is absent",
        PILOT_AUTHORIZATION_SOURCE_PATH,
    )
    _require(
        "PlatformCapabilityObservation" in authorization_text
        and "_fresh(confirmation" in authorization_text,
        "VARIANCE_PILOT_RECONCILIATION_OLD_PLATFORM_SEAM_ABSENT",
        "expected historical pre-issuance platform observation seam is absent",
        PILOT_AUTHORIZATION_SOURCE_PATH,
    )
    adr_text = (repo_root / TRANSACTION_BOUND_ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "TRANSACTION_BOUND_EXECUTION_ARTIFACT",
        "a manually authored confirmation JSON file",
        "Pre-issuance platform observation is removed",
        "zero authorization-specific Kaggle inputs",
    )
    for fragment in required_adr_fragments:
        _require(
            fragment in adr_text,
            "VARIANCE_PILOT_RECONCILIATION_ADR_CONTRACT_DRIFT",
            "transaction-bound authorization ADR contract drifted",
            TRANSACTION_BOUND_ADR_PATH,
        )
    return authorization, adr


def _validate_schedule(repo_root: Path) -> str:
    manifest_authority = _validate_blob(
        repo_root,
        PILOT_MANIFEST_PATH,
        PILOT_MANIFEST_GIT_BLOB,
    )
    _ = manifest_authority
    manifest = _load_json_object(repo_root / PILOT_MANIFEST_PATH)
    schedule = _load_json_object(repo_root / PILOT_SCHEDULE_PATH)
    schedule_sha = _sha256_file(repo_root / PILOT_SCHEDULE_PATH)
    _require(
        manifest.get("pilot_schedule_sha256") == schedule_sha,
        "VARIANCE_PILOT_RECONCILIATION_SCHEDULE_BINDING_DRIFT",
        "pilot manifest does not bind the current pilot schedule bytes",
        PILOT_MANIFEST_PATH,
    )
    required_schedule = {
        "case_count": 6,
        "trajectory_count": 54,
        "turn_count": 216,
        "maximum_request_attempt_count": 432,
        "hidden_retries_permitted": False,
        "replacement_cases_permitted": False,
        "final_benchmark_effect_claims_permitted": False,
    }
    for key, expected in required_schedule.items():
        _require(
            schedule.get(key) == expected,
            "VARIANCE_PILOT_RECONCILIATION_SCHEDULE_DRIFT",
            f"pilot schedule field drifted: {key}",
            PILOT_SCHEDULE_PATH,
        )
    trajectories = schedule.get("trajectories")
    _require(
        isinstance(trajectories, list) and len(trajectories) == 54,
        "VARIANCE_PILOT_RECONCILIATION_TRAJECTORY_COUNT_DRIFT",
        "pilot schedule must retain exactly 54 trajectories",
        PILOT_SCHEDULE_PATH,
    )
    indexes = [
        cast(dict[str, object], item).get("schedule_index")
        for item in cast(list[object], trajectories)
        if isinstance(item, dict)
    ]
    _require(
        indexes == list(range(54)),
        "VARIANCE_PILOT_RECONCILIATION_SCHEDULE_ORDER_DRIFT",
        "pilot schedule indexes must remain contiguous and ordered",
        PILOT_SCHEDULE_PATH,
    )
    return schedule_sha


def _validate_current_main_ancestry(repo_root: Path) -> None:
    merge_base = _run_git(repo_root, "merge-base", BASE_MAIN_COMMIT, "HEAD")
    _require(
        merge_base == BASE_MAIN_COMMIT,
        "VARIANCE_PILOT_RECONCILIATION_BASE_MISSING",
        "Acceptance V2 main authority is not an ancestor of HEAD",
    )


def build_review(repo_root: Path) -> ReconciliationReview:
    root = repo_root.resolve()
    _validate_current_main_ancestry(root)
    current_acceptance = _validate_current_acceptance(root)
    _validate_stale_pilot_binding(root)
    _validate_authorization_architecture(root)
    _validate_schedule(root)
    _validate_blob(root, PILOT_DESIGN_PATH, PILOT_DESIGN_GIT_BLOB)

    return ReconciliationReview(
        review_id=("auragateway-measured-abc-variance-pilot-current-line-reconciliation-v1-review"),
        current_p5_p6_acceptance=current_acceptance,
        non_claims=(
            "This reconciliation does not authorize variance-pilot execution.",
            "This reconciliation does not authorize final measured A/B/C execution.",
            "This reconciliation does not establish current timing telemetry availability.",
            "This reconciliation does not freeze final repetition counts.",
            "This reconciliation does not establish an A/B/C effect.",
            "This reconciliation does not establish production readiness.",
        ),
        next_gate=NEXT_GATE,
    )


def build_record(repo_root: Path, review: ReconciliationReview) -> ReconciliationRecord:
    root = repo_root.resolve()
    schedule_sha = _validate_schedule(root)
    authorities = (
        _validate_blob(root, PILOT_SOURCE_PATH, PILOT_SOURCE_GIT_BLOB),
        _validate_blob(
            root,
            PILOT_AUTHORIZATION_SOURCE_PATH,
            PILOT_AUTHORIZATION_SOURCE_GIT_BLOB,
        ),
        _validate_blob(root, PILOT_POLICY_PATH, PILOT_POLICY_GIT_BLOB),
        _validate_blob(root, PILOT_MANIFEST_PATH, PILOT_MANIFEST_GIT_BLOB),
        _validate_blob(root, PILOT_DESIGN_PATH, PILOT_DESIGN_GIT_BLOB),
        _validate_blob(
            root,
            CURRENT_P5_P6_ACCEPTANCE_PATH,
            CURRENT_P5_P6_ACCEPTANCE_GIT_BLOB,
        ),
        _validate_blob(
            root,
            TRANSACTION_BOUND_ADR_PATH,
            TRANSACTION_BOUND_ADR_GIT_BLOB,
        ),
    )
    review_sha = _sha256_bytes(_canonical(review.model_dump(mode="json")).encode("utf-8"))
    return ReconciliationRecord(
        record_id=("auragateway-measured-abc-variance-pilot-current-line-reconciliation-v1"),
        review_sha256=review_sha,
        authorities=authorities,
        pilot_schedule_sha256=schedule_sha,
        next_gate=NEXT_GATE,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical(payload), encoding="utf-8", newline="\n")


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    review = build_review(root)
    record = build_record(root, review)
    _write_json(root / REVIEW_PATH, review.model_dump(mode="json"))
    _write_json(root / RECORD_PATH, record.model_dump(mode="json"))
    return {
        "status": "VARIANCE_PILOT_CURRENT_LINE_RECONCILIATION_V1_GENERATED",
        "current_p5_p6_acceptance": CURRENT_P5_P6_ACCEPTANCE_PATH.as_posix(),
        "old_pilot_authorization_superseded": True,
        "transaction_bound_successor_required": True,
        "timing_telemetry_preflight_required": True,
        "runtime_launcher_readiness_committed": False,
        "variance_pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    review = build_review(root)
    record = build_record(root, review)
    try:
        observed_review = ReconciliationReview.model_validate_json(
            (root / REVIEW_PATH).read_text(encoding="utf-8")
        )
        observed_record = ReconciliationRecord.model_validate_json(
            (root / RECORD_PATH).read_text(encoding="utf-8")
        )
    except FileNotFoundError as error:
        raise ReconciliationError(
            "VARIANCE_PILOT_RECONCILIATION_OUTPUT_MISSING",
            "generated reconciliation output is missing",
        ) from error
    except ValidationError as error:
        raise ReconciliationError(
            "VARIANCE_PILOT_RECONCILIATION_OUTPUT_INVALID",
            "generated reconciliation output failed typed validation",
            details=tuple(
                item["msg"] for item in error.errors(include_url=False, include_input=False)
            ),
        ) from error

    _require(
        observed_review == review,
        "VARIANCE_PILOT_RECONCILIATION_REVIEW_DRIFT",
        "reconciliation review is not deterministic",
        REVIEW_PATH,
    )
    _require(
        observed_record == record,
        "VARIANCE_PILOT_RECONCILIATION_RECORD_DRIFT",
        "reconciliation record is not deterministic",
        RECORD_PATH,
    )
    return {
        "status": "VARIANCE_PILOT_CURRENT_LINE_RECONCILIATION_V1_VALID",
        "candidate_introduced_execution_authority": False,
        "runtime_launcher_readiness_committed": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-current-line-reconciliation-v1"
    )
    parser.add_argument(
        "command",
        choices=("generate", "validate-implementation"),
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "generate":
            result = generate(args.repo_root)
        else:
            result = validate_implementation(args.repo_root)
        print(_canonical(result), end="")
        return 0
    except ReconciliationError as error:
        print(_canonical(error.envelope()), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
