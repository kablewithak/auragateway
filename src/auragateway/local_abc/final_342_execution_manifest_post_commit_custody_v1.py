"""Bind post-commit custody for the frozen final-342 execution manifest.

This boundary proves that the exact frozen manifest bytes are carried by the first Git commit
that contains them and promotes repository-level manifest freeze without issuing execution
authority. It performs no model, GPU, Kaggle, network, issuer, or measured execution work.
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
FIRST_CONTAINING_COMMIT = "078c1da32fe7c1ee8ff5a8661e5f38e588782abc"

MANIFEST_PATH = Path("data/evals/benchmark/freeze-v3/final_342_execution_manifest_v1.json")
RECEIPT_PATH = Path(
    "data/evals/benchmark/freeze-v3/final_342_execution_manifest_post_commit_custody_v1.json"
)
MANIFEST_SOURCE_PATH = Path("src/auragateway/local_abc/final_342_execution_manifest_freeze_v1.py")

EXPECTED_MANIFEST_ID = "auragateway-final-342-execution-manifest-v1"
EXPECTED_MANIFEST_SEMANTIC_SHA256 = (
    "11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b"
)
EXPECTED_MANIFEST_FILE_SHA256 = "74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c"
EXPECTED_MANIFEST_GIT_BLOB_SHA = "2c733e930b88bca5f8ad0730d6828a88f8655e14"
EXPECTED_FIRST_CONTAINING_TREE_SHA = "64750c2ef4ee19add4d38ba916d3d0832e844bef"

NEXT_GATE = "BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1"


class CustodyError(RuntimeError):
    """Metadata-safe post-commit custody failure."""

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
        raise CustodyError("FINAL_342_CUSTODY_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ManifestIdentity(FrozenModel):
    manifest_id: Literal["auragateway-final-342-execution-manifest-v1"]
    manifest_path: Literal["data/evals/benchmark/freeze-v3/final_342_execution_manifest_v1.json"]
    manifest_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class CommitCustody(FrozenModel):
    source_subject_commit: Literal["fcf403a1c31e26a2cdf3f682a8878db01338a13d"]
    first_containing_commit: Literal["078c1da32fe7c1ee8ff5a8661e5f38e588782abc"]
    first_containing_tree_sha: Literal["64750c2ef4ee19add4d38ba916d3d0832e844bef"]
    source_subject_manifest_absent: Literal[True] = True
    first_containing_parent_is_source_subject: Literal[True] = True
    first_containing_commit_contains_exact_manifest_bytes: Literal[True] = True
    current_manifest_matches_first_containing_commit: Literal[True] = True
    first_containing_commit_is_ancestor_of_validation_head: Literal[True] = True
    merge_commit_preserving_feature_commits_required: Literal[True] = True
    squash_merge_permitted: Literal[False] = False
    rebase_merge_permitted: Literal[False] = False


class FreezePromotion(FrozenModel):
    manifest_subject_bytes_frozen: Literal[True] = True
    post_commit_custody_complete: Literal[True] = True
    repository_execution_manifest_frozen: Literal[True] = True
    repository_freeze_gate_promoted: Literal[True] = True
    execution_manifest_itself_is_execution_authority: Literal[False] = False


class SafetyState(FrozenModel):
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    network_transport_performed: Literal[False] = False
    live_authorization_issued: Literal[False] = False


class Final342ManifestCustodyReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal["auragateway-final-342-execution-manifest-post-commit-custody-v1"]
    status: Literal["FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_BOUND_V1"]
    manifest_identity: ManifestIdentity
    commit_custody: CommitCustody
    freeze_promotion: FreezePromotion
    safety_state: SafetyState
    next_gate: Literal["BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1"]

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        if self.manifest_identity.manifest_semantic_sha256 != EXPECTED_MANIFEST_SEMANTIC_SHA256:
            raise ValueError("manifest semantic identity drifted")
        if self.manifest_identity.manifest_file_sha256 != EXPECTED_MANIFEST_FILE_SHA256:
            raise ValueError("manifest file identity drifted")
        if self.manifest_identity.manifest_git_blob_sha != EXPECTED_MANIFEST_GIT_BLOB_SHA:
            raise ValueError("manifest Git blob identity drifted")
        return self


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(
    root: Path,
    args: list[str],
    *,
    expected_returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != expected_returncode:
        raise CustodyError(
            "FINAL_342_CUSTODY_GIT_COMMAND_FAILED",
            f"Git custody command failed: {' '.join(args)}",
        )
    return completed


def _git_bytes(root: Path, revision_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", revision_path],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise CustodyError(
            "FINAL_342_CUSTODY_GIT_SHOW_FAILED",
            "unable to read manifest bytes from required Git commit",
            MANIFEST_PATH,
        )
    return completed.stdout


def _read_manifest(root: Path) -> tuple[bytes, dict[str, object]]:
    path = root / MANIFEST_PATH
    if not path.is_file() or path.is_symlink():
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_MISSING",
            "frozen manifest is missing or unsafe",
            MANIFEST_PATH,
        )
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_JSON_INVALID",
            "frozen manifest JSON is invalid",
            MANIFEST_PATH,
        ) from error
    if not isinstance(value, dict):
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_ROOT_INVALID",
            "frozen manifest root must be one object",
            MANIFEST_PATH,
        )
    return raw, cast(dict[str, object], value)


def _semantic_sha256(payload: dict[str, object]) -> str:
    copied = json.loads(json.dumps(payload))
    identity = copied.get("identity")
    if not isinstance(identity, dict):
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_IDENTITY_INVALID",
            "frozen manifest identity section is invalid",
            MANIFEST_PATH,
        )
    identity.pop("execution_manifest_hash", None)
    return sha256_bytes(canonical_json_bytes(copied))


def _verify_commit_graph(root: Path, *, materialization: bool) -> None:
    head = _git(root, ["rev-parse", "HEAD"]).stdout.strip()
    if materialization and head != FIRST_CONTAINING_COMMIT:
        raise CustodyError(
            "FINAL_342_CUSTODY_MATERIALIZATION_HEAD_DRIFT",
            "custody receipt must be materialized from exact first-containing commit",
        )

    parent = _git(
        root,
        ["rev-parse", f"{FIRST_CONTAINING_COMMIT}^"],
    ).stdout.strip()
    if parent != SOURCE_SUBJECT_COMMIT:
        raise CustodyError(
            "FINAL_342_CUSTODY_PARENT_DRIFT",
            "first-containing commit is not directly based on source subject",
        )

    tree = _git(
        root,
        ["rev-parse", f"{FIRST_CONTAINING_COMMIT}^{{tree}}"],
    ).stdout.strip()
    if tree != EXPECTED_FIRST_CONTAINING_TREE_SHA:
        raise CustodyError(
            "FINAL_342_CUSTODY_TREE_DRIFT",
            "first-containing commit tree identity drifted",
        )

    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            FIRST_CONTAINING_COMMIT,
            "HEAD",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        raise CustodyError(
            "FINAL_342_CUSTODY_ANCESTRY_DRIFT",
            "first-containing commit is not an ancestor of validation HEAD",
        )


def _verify_source_subject_absence(root: Path) -> None:
    completed = subprocess.run(
        [
            "git",
            "cat-file",
            "-e",
            f"{SOURCE_SUBJECT_COMMIT}:{MANIFEST_PATH.as_posix()}",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        raise CustodyError(
            "FINAL_342_CUSTODY_SOURCE_ALREADY_CONTAINED_MANIFEST",
            "source-subject commit unexpectedly already contains final manifest",
            MANIFEST_PATH,
        )


def _verify_manifest_identity(root: Path) -> ManifestIdentity:
    worktree_raw, payload = _read_manifest(root)
    committed_raw = _git_bytes(
        root,
        f"{FIRST_CONTAINING_COMMIT}:{MANIFEST_PATH.as_posix()}",
    )

    if worktree_raw != committed_raw:
        raise CustodyError(
            "FINAL_342_CUSTODY_WORKTREE_MANIFEST_DRIFT",
            "current manifest bytes differ from first-containing commit",
            MANIFEST_PATH,
        )

    file_sha256 = sha256_bytes(committed_raw)
    if file_sha256 != EXPECTED_MANIFEST_FILE_SHA256:
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_FILE_SHA_DRIFT",
            "frozen manifest file SHA-256 drifted",
            MANIFEST_PATH,
        )

    semantic_sha256 = _semantic_sha256(payload)
    if semantic_sha256 != EXPECTED_MANIFEST_SEMANTIC_SHA256:
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_SEMANTIC_SHA_DRIFT",
            "frozen manifest semantic SHA-256 drifted",
            MANIFEST_PATH,
        )

    identity = payload.get("identity")
    custody = payload.get("custody")
    if not isinstance(identity, dict) or not isinstance(custody, dict):
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_SHAPE_INVALID",
            "frozen manifest custody/identity sections are invalid",
            MANIFEST_PATH,
        )
    if payload.get("manifest_id") != EXPECTED_MANIFEST_ID:
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_ID_DRIFT",
            "frozen manifest ID drifted",
            MANIFEST_PATH,
        )
    if identity.get("execution_manifest_hash") != semantic_sha256:
        raise CustodyError(
            "FINAL_342_CUSTODY_STORED_SEMANTIC_HASH_DRIFT",
            "stored manifest semantic hash does not match recomputation",
            MANIFEST_PATH,
        )
    if custody.get("source_subject_commit") != SOURCE_SUBJECT_COMMIT:
        raise CustodyError(
            "FINAL_342_CUSTODY_SOURCE_SUBJECT_DRIFT",
            "manifest source-subject custody identity drifted",
            MANIFEST_PATH,
        )
    if payload.get("next_gate") != ("BIND_FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_V1"):
        raise CustodyError(
            "FINAL_342_CUSTODY_PREDECESSOR_GATE_DRIFT",
            "frozen manifest does not point to post-commit custody",
            MANIFEST_PATH,
        )

    blob_sha = _git(
        root,
        [
            "rev-parse",
            f"{FIRST_CONTAINING_COMMIT}:{MANIFEST_PATH.as_posix()}",
        ],
    ).stdout.strip()
    if blob_sha != EXPECTED_MANIFEST_GIT_BLOB_SHA:
        raise CustodyError(
            "FINAL_342_CUSTODY_MANIFEST_BLOB_DRIFT",
            "frozen manifest Git blob identity drifted",
            MANIFEST_PATH,
        )

    return ManifestIdentity(
        manifest_id=EXPECTED_MANIFEST_ID,
        manifest_path=MANIFEST_PATH.as_posix(),
        manifest_semantic_sha256=semantic_sha256,
        manifest_file_sha256=file_sha256,
        manifest_git_blob_sha=blob_sha,
    )


def build_receipt(
    repo_root: Path,
    *,
    materialization: bool = False,
) -> Final342ManifestCustodyReceipt:
    root = repo_root.resolve()
    _verify_commit_graph(root, materialization=materialization)
    _verify_source_subject_absence(root)
    manifest_identity = _verify_manifest_identity(root)

    return Final342ManifestCustodyReceipt(
        receipt_id="auragateway-final-342-execution-manifest-post-commit-custody-v1",
        status="FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_BOUND_V1",
        manifest_identity=manifest_identity,
        commit_custody=CommitCustody(
            source_subject_commit=SOURCE_SUBJECT_COMMIT,
            first_containing_commit=FIRST_CONTAINING_COMMIT,
            first_containing_tree_sha=EXPECTED_FIRST_CONTAINING_TREE_SHA,
        ),
        freeze_promotion=FreezePromotion(),
        safety_state=SafetyState(),
        next_gate=NEXT_GATE,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.final-342-custody.tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    temporary.replace(path)


def materialize(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    receipt = build_receipt(root, materialization=True)
    _write_atomic(
        root / RECEIPT_PATH,
        canonical_json_bytes(receipt.model_dump(mode="json")),
    )
    return validate(root)


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected = build_receipt(root)
    path = root / RECEIPT_PATH
    if not path.is_file() or path.is_symlink():
        raise CustodyError(
            "FINAL_342_CUSTODY_RECEIPT_MISSING",
            "post-commit custody receipt is missing or unsafe",
            RECEIPT_PATH,
        )

    try:
        observed = Final342ManifestCustodyReceipt.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise CustodyError(
            "FINAL_342_CUSTODY_RECEIPT_INVALID",
            "post-commit custody receipt failed typed validation",
            RECEIPT_PATH,
        ) from error

    if observed != expected:
        raise CustodyError(
            "FINAL_342_CUSTODY_RECEIPT_DRIFT",
            "post-commit custody receipt differs from deterministic reconstruction",
            RECEIPT_PATH,
        )
    canonical = canonical_json_bytes(observed.model_dump(mode="json"))
    if path.read_bytes() != canonical:
        raise CustodyError(
            "FINAL_342_CUSTODY_RECEIPT_BYTES_DRIFT",
            "post-commit custody receipt bytes are not canonical",
            RECEIPT_PATH,
        )

    return {
        "status": observed.status,
        "manifest_semantic_sha256": (observed.manifest_identity.manifest_semantic_sha256),
        "manifest_file_sha256": observed.manifest_identity.manifest_file_sha256,
        "manifest_git_blob_sha": observed.manifest_identity.manifest_git_blob_sha,
        "source_subject_commit": SOURCE_SUBJECT_COMMIT,
        "first_containing_commit": FIRST_CONTAINING_COMMIT,
        "post_commit_custody_complete": True,
        "repository_execution_manifest_frozen": True,
        "repository_freeze_gate_promoted": True,
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
    parser = _Parser(prog="final-342-execution-manifest-post-commit-custody-v1")
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
    except (CustodyError, OSError, UnicodeDecodeError, ValueError) as error:
        if isinstance(error, CustodyError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path.as_posix() if error.path is not None else None,
            }
        else:
            payload = {
                "error_code": "FINAL_342_POST_COMMIT_CUSTODY_FAILED",
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
