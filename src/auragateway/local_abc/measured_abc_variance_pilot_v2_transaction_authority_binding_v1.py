"""Static authority binding for the variance-pilot successor V2 transaction.

This tranche is deliberately non-authorizing. It binds the exact merged V2 wrapper
rehearsal, runtime graph, material, runtime contract, and request budget into
deterministic review/record artifacts. It does not expose a live issuance command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Final, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_wrapper_rehearsal_v1 as rehearsal,
)

JsonObject: TypeAlias = dict[str, object]

BASE_MAIN_COMMIT: Final = "127695e8310dfe50c950c8946d6ca4568e95a07d"
EXPECTED_RENDERED_WRAPPER_SHA256: Final = (
    "5bc26b220c7b34da7d634686af97d67b0d2666f84ac6f8d9b1f214163c17cb41"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_authority_binding_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_v2_transaction_authority_binding_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_transaction_"
    "authority_binding_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_transaction_"
    "authority_binding_v1_record.json"
)

BOUND_UPSTREAM_PATHS: Final[tuple[Path, ...]] = (
    rehearsal.WRAPPER_TEMPLATE_PATH,
    rehearsal.R2_RUNTIME_PATH,
    rehearsal.OUTPUT_ADMISSION_RUNTIME_PATH,
    rehearsal.STANDALONE_RUNTIME_PATH,
    rehearsal.LIVE_SEMANTICS_RUNTIME_PATH,
    rehearsal.REQUEST_ADAPTER_PATH,
    rehearsal.TRANSACTION_RUNTIME_PATH,
    rehearsal.PILOT_SCHEDULE_PATH,
    rehearsal.NEUTRAL_PLAN_PATH,
    rehearsal.STRICT_RESPONSE_FORMAT_PATH,
    rehearsal.STANDALONE_ADMISSION_SPEC_PATH,
    rehearsal.GENERATION_CONTRACT_PATH,
    rehearsal.LOCAL_MATERIALIZATION_MANIFEST_PATH,
    rehearsal.ACCEPTED_RUNTIME_INTEGRATION_PATH,
    rehearsal.TOKENIZER_OBSERVATION_PATH,
    rehearsal.ACCEPTED_EPISODES_PATH,
    rehearsal.RUNTIME_SELECTION_PATH,
    rehearsal.SOURCE_MANIFEST_PATH,
    rehearsal.COMPILER_SPEC_PATH,
)
EXPECTED_BOUND_ARTIFACT_COUNT: Final = 19

NEXT_GATE: Final = (
    "MERGE_THEN_REHEARSE_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_V1"
)


class AuthorityBindingError(RuntimeError):
    """Metadata-safe V2 transaction authority-binding failure."""

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

    def envelope(self) -> JsonObject:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path.as_posix() if self.path is not None else None,
        }


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(FrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class RuntimeModelContract(FrozenModel):
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
    max_model_len: Literal[4096] = 4096


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_model_loads: Literal[2] = 2
    maximum_worker_starts: Literal[2] = 2
    maximum_worker_teardowns: Literal[2] = 2
    maximum_schema_canary_requests: Literal[2] = 2
    maximum_warmup_requests: Literal[2] = 2
    maximum_neutral_qualification_requests: Literal[20] = 20
    maximum_pretreatment_requests: Literal[24] = 24
    maximum_pilot_trajectory_count: Literal[54] = 54
    maximum_pilot_turn_count: Literal[216] = 216
    maximum_pilot_request_attempts: Literal[216] = 216
    maximum_total_model_requests: Literal[240] = 240
    maximum_output_tokens_per_request: Literal[256] = 256
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_cases: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class StructuralRehearsalContract(FrozenModel):
    status: Literal["VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_WRAPPER_REHEARSAL_VALID"] = (
        "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_WRAPPER_REHEARSAL_VALID"
    )
    rendered_wrapper_sha256: Literal[
        "5bc26b220c7b34da7d634686af97d67b0d2666f84ac6f8d9b1f214163c17cb41"
    ] = EXPECTED_RENDERED_WRAPPER_SHA256
    loaded_runtime_module_count: Literal[6] = 6
    material_validated: Literal[True] = True
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False


class StaticReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-measured-abc-variance-pilot-v2-transaction-authority-binding-v1-review"
    ]
    bound_upstream_main_commit: Literal["127695e8310dfe50c950c8946d6ca4568e95a07d"] = (
        BASE_MAIN_COMMIT
    )
    status: Literal["IMPLEMENTED_NOT_ISSUED"] = "IMPLEMENTED_NOT_ISSUED"
    runtime: RuntimeModelContract = RuntimeModelContract()
    budget: ExecutionBudget = ExecutionBudget()
    structural_rehearsal: StructuralRehearsalContract
    bound_artifact_count: Literal[19] = EXPECTED_BOUND_ARTIFACT_COUNT
    candidate_introduced_execution_authority: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    non_claims: tuple[str, ...]
    next_gate: str


class StaticRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-measured-abc-variance-pilot-v2-transaction-authority-binding-v1-record"
    ]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: ArtifactReceipt
    test: ArtifactReceipt
    bound_artifacts: tuple[ArtifactReceipt, ...]
    bound_artifact_count: Literal[19] = EXPECTED_BOUND_ARTIFACT_COUNT
    rendered_wrapper_sha256: Literal[
        "5bc26b220c7b34da7d634686af97d67b0d2666f84ac6f8d9b1f214163c17cb41"
    ] = EXPECTED_RENDERED_WRAPPER_SHA256
    candidate_introduced_execution_authority: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: str


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _artifact_bytes(value: object) -> bytes:
    return _canonical_bytes(value) + b"\n"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_REQUIRED_FILE_MISSING",
            "required authority-binding file is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    payload = _read_bytes(repo_root, relative)
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256(payload),
        size_bytes=len(payload),
    )


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_GIT_FAILED",
            "required git authority-binding inspection failed",
        )
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    try:
        return _git_bytes(repo_root, *args).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_GIT_OUTPUT_INVALID",
            "git authority-binding inspection returned invalid text",
        ) from exc


def _validate_base_lineage(repo_root: Path) -> None:
    resolved_base = _git_text(repo_root, "rev-parse", BASE_MAIN_COMMIT)
    if resolved_base != BASE_MAIN_COMMIT:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_BASE_COMMIT_MISSING",
            "bound upstream main commit is unavailable",
        )
    merge_base = _git_text(repo_root, "merge-base", BASE_MAIN_COMMIT, "HEAD")
    if merge_base != BASE_MAIN_COMMIT:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_BASE_NOT_ANCESTOR",
            "candidate HEAD does not descend from the bound upstream main commit",
        )


def _validate_upstream_unchanged(repo_root: Path) -> None:
    if len(BOUND_UPSTREAM_PATHS) != EXPECTED_BOUND_ARTIFACT_COUNT:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_BOUNDARY_COUNT_DRIFT",
            "authority-binding upstream path count drifted",
        )
    if len(set(BOUND_UPSTREAM_PATHS)) != EXPECTED_BOUND_ARTIFACT_COUNT:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_BOUNDARY_DUPLICATED",
            "authority-binding upstream path set contains duplicates",
        )

    for relative in BOUND_UPSTREAM_PATHS:
        working = _read_bytes(repo_root, relative)
        committed = _git_bytes(
            repo_root,
            "show",
            f"{BASE_MAIN_COMMIT}:{relative.as_posix()}",
        )
        if working != committed:
            raise AuthorityBindingError(
                "V2_TX_AUTH_BIND_UPSTREAM_DRIFT",
                "bound V2 upstream artifact differs from merged rehearsal main",
                relative,
            )


def _structural_rehearsal(repo_root: Path) -> StructuralRehearsalContract:
    result = rehearsal.validate_implementation(repo_root)
    expected: JsonObject = {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_WRAPPER_REHEARSAL_VALID",
        "rendered_wrapper_sha256": EXPECTED_RENDERED_WRAPPER_SHA256,
        "loaded_runtime_module_count": 6,
        "material_validated": True,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
    }
    if any(result.get(key) != value for key, value in expected.items()):
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_REHEARSAL_DRIFT",
            "merged V2 structural rehearsal no longer matches the bound acceptance",
        )
    return StructuralRehearsalContract.model_validate(expected)


def build_review(repo_root: Path) -> StaticReview:
    root = repo_root.resolve()
    _validate_base_lineage(root)
    _validate_upstream_unchanged(root)
    structural_rehearsal = _structural_rehearsal(root)
    return StaticReview(
        review_id=(
            "auragateway-measured-abc-variance-pilot-v2-transaction-authority-binding-v1-review"
        ),
        structural_rehearsal=structural_rehearsal,
        non_claims=(
            "This binding does not issue live V2 execution authorization.",
            "This binding does not perform model requests or GPU execution.",
            "This binding does not perform Kaggle execution.",
            "This binding does not establish successful variance-pilot execution.",
            "This binding does not authorize final measured A/B/C execution.",
            "This binding does not establish A/B/C effects or production readiness.",
        ),
        next_gate=NEXT_GATE,
    )


def build_record(repo_root: Path, review: StaticReview) -> StaticRecord:
    bound_artifacts = tuple(_receipt(repo_root, path) for path in BOUND_UPSTREAM_PATHS)
    return StaticRecord(
        record_id=(
            "auragateway-measured-abc-variance-pilot-v2-transaction-authority-binding-v1-record"
        ),
        review_sha256=_sha256(_canonical_bytes(review)),
        source=_receipt(repo_root, SOURCE_PATH),
        test=_receipt(repo_root, TEST_PATH),
        bound_artifacts=bound_artifacts,
        next_gate=NEXT_GATE,
    )


def _write_artifact(repo_root: Path, relative: Path, payload: bytes) -> None:
    path = repo_root / relative
    if path.exists() and path.is_symlink():
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_OUTPUT_SYMLINK_REJECTED",
            "authority-binding output path may not be a symlink",
            relative,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def generate(repo_root: Path) -> JsonObject:
    root = repo_root.resolve()
    review = build_review(root)
    record = build_record(root, review)
    _write_artifact(root, REVIEW_PATH, _artifact_bytes(review))
    _write_artifact(root, RECORD_PATH, _artifact_bytes(record))
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_MATERIALIZED",
        "review_path": REVIEW_PATH.as_posix(),
        "record_path": RECORD_PATH.as_posix(),
        "rendered_wrapper_sha256": EXPECTED_RENDERED_WRAPPER_SHA256,
        "bound_artifact_count": EXPECTED_BOUND_ARTIFACT_COUNT,
        "candidate_introduced_execution_authority": False,
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def validate_implementation(repo_root: Path) -> JsonObject:
    root = repo_root.resolve()
    expected_review = build_review(root)
    expected_record = build_record(root, expected_review)
    try:
        observed_review = StaticReview.model_validate_json((root / REVIEW_PATH).read_bytes())
        observed_record = StaticRecord.model_validate_json((root / RECORD_PATH).read_bytes())
    except (FileNotFoundError, ValidationError) as exc:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_GENERATED_OUTPUT_INVALID",
            "generated V2 transaction authority-binding output is invalid",
        ) from exc

    if observed_review != expected_review:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_REVIEW_DRIFT",
            "V2 transaction authority-binding review is not deterministic",
            REVIEW_PATH,
        )
    if observed_record != expected_record:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_RECORD_DRIFT",
            "V2 transaction authority-binding record is not deterministic",
            RECORD_PATH,
        )
    if len(observed_record.bound_artifacts) != EXPECTED_BOUND_ARTIFACT_COUNT:
        raise AuthorityBindingError(
            "V2_TX_AUTH_BIND_RECORD_BOUNDARY_DRIFT",
            "V2 transaction authority-binding record boundary drifted",
            RECORD_PATH,
        )

    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_VALID",
        "bound_upstream_main_commit": BASE_MAIN_COMMIT,
        "rendered_wrapper_sha256": EXPECTED_RENDERED_WRAPPER_SHA256,
        "bound_artifact_count": EXPECTED_BOUND_ARTIFACT_COUNT,
        "candidate_introduced_execution_authority": False,
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bind the exact merged variance-pilot V2 transaction boundary."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--repo-root", type=Path, default=Path("."))

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--repo-root", type=Path, default=Path("."))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "generate":
            result = generate(args.repo_root)
        else:
            result = validate_implementation(args.repo_root)
    except AuthorityBindingError as exc:
        print(json.dumps(exc.envelope(), sort_keys=True))
        return 2

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
