"""Build and verify the static qualification authorization input package."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Never, cast

from pydantic import ValidationError

from .full_abc_local_environment_qualification_execution_authorization_contracts import (
    ARTIFACT_IDENTITY_GIT_BLOB_SHA,
    ARTIFACT_IDENTITY_PATH,
    AUTHORIZATION_REQUEST_PATH,
    DATASET_MANIFEST_REQUEST_PATH,
    EXECUTION_CONTRACTS_GIT_BLOB_SHA,
    EXECUTION_CONTRACTS_PATH,
    EXECUTION_NOTEBOOK_GIT_BLOB_SHA,
    EXECUTION_NOTEBOOK_PATH,
    EXECUTION_REQUEST_GIT_BLOB_SHA,
    EXECUTION_REQUEST_PATH,
    EXECUTION_REQUEST_SHA256,
    EXECUTION_RUNBOOK_GIT_BLOB_SHA,
    EXECUTION_RUNBOOK_PATH,
    EXECUTION_RUNNER_GIT_BLOB_SHA,
    EXECUTION_RUNNER_PATH,
    FINAL_AUTHORIZATION_PATH,
    MATERIALIZATION_RECORD_PATH,
    MATERIALIZED_DATASET_MANIFEST_PATH,
    NEXT_GATE,
    REVIEW_GIT_BLOB_SHA,
    REVIEW_PATH,
    REVIEW_SOURCE_GIT_BLOB_SHA,
    REVIEW_SOURCE_PATH,
    RUNTIME_ADAPTER_PATH,
    RUNTIME_EVIDENCE_PATHS,
    RUNTIME_FACTORY_PATH,
    SOURCE_MAIN_MERGE_COMMIT,
    WORKER_STARTUP_PLAN_GIT_BLOB_SHA,
    WORKER_STARTUP_PLAN_PATH,
    AuthorizationPackageError,
    AuthorizationPackageErrorEnvelope,
    AuthorizationPackageSafetyEnvelope,
    AuthorizationPackageStatus,
    DatasetArtifactFormat,
    DatasetMaterializationState,
    DatasetRole,
    DatasetRoleMaterializationRequest,
    MaterializedOfflineDatasetRecord,
    OfflineDatasetManifestRequest,
    PortableDatasetManifestEntry,
    PortableQualificationDatasetManifest,
    QualificationAuthorizationRequest,
    RuntimeAdapterImplementationBinding,
    SourceAuthorityBinding,
)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationPackageError(
            "INVALID_COMMAND_ARGUMENTS",
            "authorization-package command arguments are invalid",
            details=(message,),
        )


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuthorizationPackageError(
            "REQUIRED_ASSET_NOT_FOUND",
            "a required authorization-package asset was not found",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise AuthorizationPackageError(
            "REQUIRED_ASSET_INVALID_JSON",
            "a required authorization-package asset is not valid JSON",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationPackageError(
            "REQUIRED_ASSET_INVALID_ROOT",
            "a required authorization-package asset must be one JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _write_text_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise AuthorizationPackageError(
            "ATOMIC_WRITE_FAILED",
            "an authorization-package artifact could not be written atomically",
            path.as_posix(),
        ) from exc


def _git_blob_sha(repo_root: Path, relative_path: Path) -> str:
    artifact_path = repo_root / relative_path
    if not artifact_path.is_file():
        raise AuthorizationPackageError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required authorization-package Git authority could not be resolved",
            relative_path.as_posix(),
        )
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "hash-object",
                f"--path={relative_path.as_posix()}",
                str(artifact_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationPackageError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required authorization-package Git authority could not be resolved",
            relative_path.as_posix(),
        ) from exc
    identity = result.stdout.strip()
    if len(identity) != 40 or any(character not in "0123456789abcdef" for character in identity):
        raise AuthorizationPackageError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required authorization-package Git authority returned an invalid identity",
            relative_path.as_posix(),
        )
    return identity


def _require_source_ancestor(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_MERGE_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationPackageError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise AuthorizationPackageError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 105 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def _source_authority_specs() -> tuple[tuple[str, Path, str], ...]:
    return (
        ("authorization-review", REVIEW_PATH, REVIEW_GIT_BLOB_SHA),
        ("authorization-review-source", REVIEW_SOURCE_PATH, REVIEW_SOURCE_GIT_BLOB_SHA),
        (
            "artifact-identity",
            ARTIFACT_IDENTITY_PATH,
            ARTIFACT_IDENTITY_GIT_BLOB_SHA,
        ),
        (
            "execution-contracts",
            EXECUTION_CONTRACTS_PATH,
            EXECUTION_CONTRACTS_GIT_BLOB_SHA,
        ),
        (
            "execution-notebook",
            EXECUTION_NOTEBOOK_PATH,
            EXECUTION_NOTEBOOK_GIT_BLOB_SHA,
        ),
        ("execution-request", EXECUTION_REQUEST_PATH, EXECUTION_REQUEST_GIT_BLOB_SHA),
        ("execution-runner", EXECUTION_RUNNER_PATH, EXECUTION_RUNNER_GIT_BLOB_SHA),
        ("execution-runbook", EXECUTION_RUNBOOK_PATH, EXECUTION_RUNBOOK_GIT_BLOB_SHA),
        (
            "worker-startup-plan",
            WORKER_STARTUP_PLAN_PATH,
            WORKER_STARTUP_PLAN_GIT_BLOB_SHA,
        ),
    )


def _validate_repository_authorities(repo_root: Path) -> None:
    _require_source_ancestor(repo_root)
    drift = tuple(
        sorted(
            path.as_posix()
            for _, path, expected_sha in _source_authority_specs()
            if _git_blob_sha(repo_root, path) != expected_sha
        )
    )
    if drift:
        raise AuthorizationPackageError(
            "AUTHORIZATION_PACKAGE_AUTHORITY_DRIFT",
            "one or more authorization-package authorities drifted",
            details=drift,
        )

    review = _load_json_object(repo_root / REVIEW_PATH)
    expected_review = {
        "decision": "APPROVED_FOR_AUTHORIZATION_PACKAGE_IMPLEMENTATION",
        "next_gate": (
            "full_abc_local_full_run_environment_qualification_execution_"
            "authorization_implementation"
        ),
        "source_main_merge_commit": "768e0535d8d373385440acc2dc18952b4fc42325",
    }
    if any(review.get(field) != expected for field, expected in expected_review.items()):
        raise AuthorizationPackageError(
            "AUTHORIZATION_REVIEW_DRIFT",
            "the merged review no longer authorizes this implementation",
            REVIEW_PATH.as_posix(),
        )


def _source_authorities() -> tuple[SourceAuthorityBinding, ...]:
    return tuple(
        SourceAuthorityBinding(
            authority_id=authority_id,
            path=path.as_posix(),
            git_blob_sha=blob_sha,
        )
        for authority_id, path, blob_sha in sorted(_source_authority_specs())
    )


def build_offline_dataset_manifest_request() -> OfflineDatasetManifestRequest:
    """Build the deterministic materialization request without inventing dataset identities."""

    return OfflineDatasetManifestRequest(
        request_id=(
            "auragateway-full-abc-local-environment-qualification-offline-dataset-request-v1"
        ),
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        status=DatasetMaterializationState.REQUESTED_NOT_MATERIALIZED,
        source_authorities=_source_authorities(),
        roles=(
            DatasetRoleMaterializationRequest(
                role=DatasetRole.HARNESS_SOURCE,
                artifact_format=DatasetArtifactFormat.SOURCE_TREE_DIRECTORY,
                required_content=(
                    "Exact post-implementation AuraGateway source tree, lock files, "
                    "notebook, runtime adapter, and authorization tooling."
                ),
            ),
            DatasetRoleMaterializationRequest(
                role=DatasetRole.MODEL_ARTIFACTS,
                artifact_format=DatasetArtifactFormat.HUGGING_FACE_SNAPSHOT_DIRECTORY,
                required_content=(
                    "Exact expanded Hugging Face snapshot directory for "
                    "Qwen/Qwen2.5-0.5B-Instruct at revision "
                    "7ae557604adf67be50417f59c2c2f167def9a775."
                ),
            ),
            DatasetRoleMaterializationRequest(
                role=DatasetRole.VLLM_WHEEL,
                artifact_format=DatasetArtifactFormat.PYTHON_WHEEL,
                required_content=(
                    "Exact locally installable vLLM 0.25.1 wheel compatible with the "
                    "authorized Kaggle Python and CUDA runtime."
                ),
            ),
        ),
        materialized_manifest_path=(
            "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
        ),
        next_gate=NEXT_GATE,
    )


def build_qualification_authorization_request() -> QualificationAuthorizationRequest:
    """Build the issuance request while leaving final authority absent."""

    dataset_request = build_offline_dataset_manifest_request()
    return QualificationAuthorizationRequest(
        request_id=(
            "auragateway-full-abc-local-environment-qualification-authorization-request-v1"
        ),
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        status=AuthorizationPackageStatus.INPUT_PACKAGE_GENERATED_ISSUANCE_BLOCKED,
        source_authorities=_source_authorities(),
        execution_request_path=(
            "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
        ),
        execution_request_sha256=EXECUTION_REQUEST_SHA256,
        dataset_manifest_request_path=(
            "data/evals/benchmark/environment-qualification-v1/"
            "offline_dataset_manifest_request.json"
        ),
        dataset_manifest_request_sha256=dataset_request.fingerprint(),
        materialization_record_path=(
            "data/evals/benchmark/environment-qualification-v1/"
            "offline_dataset_materialization_record.json"
        ),
        runtime_dataset_manifest_path=(
            "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
        ),
        runtime_adapter=RuntimeAdapterImplementationBinding(
            artifact_path=(
                "src/auragateway/local_abc/"
                "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
            ),
            factory_path=RUNTIME_FACTORY_PATH,
            protocol_path=(
                "auragateway.local_abc."
                "full_abc_local_environment_qualification_execution_contracts:"
                "QualificationRuntimeAdapter"
            ),
            startup_plan_path=(
                "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
            ),
        ),
        final_authorization_path=(
            "benchmarks/local_abc/"
            "auragateway_full_abc_local_full_run_environment_qualification_"
            "execution_authorization_v1.json"
        ),
        safety=AuthorizationPackageSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def _require_package_files(repo_root: Path) -> None:
    required = (
        Path(
            "src/auragateway/local_abc/"
            "full_abc_local_environment_qualification_execution_authorization_contracts.py"
        ),
        Path(
            "src/auragateway/local_abc/"
            "full_abc_local_environment_qualification_execution_authorization.py"
        ),
        RUNTIME_ADAPTER_PATH,
        Path(
            "tests/unit/local_abc/"
            "test_full_abc_local_environment_qualification_execution_authorization.py"
        ),
        AUTHORIZATION_REQUEST_PATH,
        DATASET_MANIFEST_REQUEST_PATH,
        Path("docs/runbooks/local_abc_full_run_environment_qualification_authorization_v1.md"),
    )
    missing = tuple(path.as_posix() for path in required if not (repo_root / path).is_file())
    if missing:
        raise AuthorizationPackageError(
            "AUTHORIZATION_PACKAGE_INCOMPLETE",
            "one or more authorization-package files are missing",
            details=missing,
        )


def _audit_runtime_adapter(path: Path) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    except (OSError, SyntaxError) as exc:
        raise AuthorizationPackageError(
            "RUNTIME_ADAPTER_STATIC_AUDIT_FAILED",
            "runtime adapter could not be parsed for static safety review",
            path.as_posix(),
        ) from exc

    factory_found = False
    unsafe: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            factory_found = factory_found or node.name == "create_runtime_adapter"
        if (
            isinstance(node, ast.keyword)
            and node.arg == "shell"
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
        ):
            unsafe.append("shell_true")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.lower()
            if (
                value.startswith(("http://", "https://"))
                and value not in {"http://", "https://"}
                and not value.startswith(("http://127.0.0.1", "http://localhost"))
            ):
                unsafe.append("non_loopback_url")
    if not factory_found:
        unsafe.append("factory_missing")
    if unsafe:
        raise AuthorizationPackageError(
            "RUNTIME_ADAPTER_STATIC_AUDIT_FAILED",
            "runtime adapter violates one or more static safety constraints",
            path.as_posix(),
            tuple(sorted(set(unsafe))),
        )


def generate_static_authorization_package(repo_root: Path) -> dict[str, object]:
    """Generate only static requests after exact authority validation."""

    _validate_repository_authorities(repo_root)
    dataset_request = build_offline_dataset_manifest_request()
    authorization_request = build_qualification_authorization_request()
    _write_text_atomic(
        repo_root / DATASET_MANIFEST_REQUEST_PATH,
        dataset_request.canonical_json(),
    )
    _write_text_atomic(
        repo_root / AUTHORIZATION_REQUEST_PATH,
        authorization_request.canonical_json(),
    )
    return verify_static_authorization_package(repo_root)


def verify_static_authorization_package(repo_root: Path) -> dict[str, object]:
    """Verify deterministic inputs and prove operational authority remains absent."""

    _validate_repository_authorities(repo_root)
    _require_package_files(repo_root)
    expected_dataset = build_offline_dataset_manifest_request()
    expected_authorization = build_qualification_authorization_request()
    try:
        observed_dataset = OfflineDatasetManifestRequest.model_validate_json(
            (repo_root / DATASET_MANIFEST_REQUEST_PATH).read_text(encoding="utf-8")
        )
        observed_authorization = QualificationAuthorizationRequest.model_validate_json(
            (repo_root / AUTHORIZATION_REQUEST_PATH).read_text(encoding="utf-8")
        )
    except ValidationError as exc:
        raise AuthorizationPackageError(
            "AUTHORIZATION_PACKAGE_REQUEST_INVALID",
            "an authorization-package request failed contract validation",
        ) from exc

    if observed_dataset.canonical_json() != expected_dataset.canonical_json():
        raise AuthorizationPackageError(
            "DATASET_MANIFEST_REQUEST_DRIFT",
            "offline dataset manifest request drifted from deterministic output",
            DATASET_MANIFEST_REQUEST_PATH.as_posix(),
        )
    if observed_authorization.canonical_json() != expected_authorization.canonical_json():
        raise AuthorizationPackageError(
            "AUTHORIZATION_REQUEST_DRIFT",
            "qualification authorization request drifted from deterministic output",
            AUTHORIZATION_REQUEST_PATH.as_posix(),
        )

    _audit_runtime_adapter(repo_root / RUNTIME_ADAPTER_PATH)
    prohibited = (
        FINAL_AUTHORIZATION_PATH,
        MATERIALIZATION_RECORD_PATH,
        MATERIALIZED_DATASET_MANIFEST_PATH,
    )
    premature = tuple(path.as_posix() for path in prohibited if (repo_root / path).exists())
    premature += tuple(
        path.as_posix() for path in RUNTIME_EVIDENCE_PATHS if (repo_root / path).exists()
    )
    if premature:
        raise AuthorizationPackageError(
            "OPERATIONAL_AUTHORITY_PREMATURE",
            "operational authorization or runtime evidence exists before issuance review",
            details=tuple(sorted(premature)),
        )

    return {
        "authorization_request_sha256": expected_authorization.fingerprint(),
        "dataset_manifest_request_sha256": expected_dataset.fingerprint(),
        "authorization_package_generated": True,
        "runtime_adapter_generated": True,
        "runtime_adapter_executed": False,
        "final_authorization_generated": False,
        "materialized_dataset_manifest_generated": False,
        "kaggle_session_started": False,
        "gpu_execution_authorized": False,
        "worker_started": False,
        "model_execution_performed": False,
        "runtime_evidence_generated": False,
        "maximum_model_requests": 8,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
        "next_gate": NEXT_GATE,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_portable_runtime_manifest(
    record: MaterializedOfflineDatasetRecord,
) -> PortableQualificationDatasetManifest:
    """Project exact Kaggle provenance into the existing runtime manifest shape."""

    entries = tuple(
        PortableDatasetManifestEntry(
            role=item.role.value,
            artifact_format=item.artifact_format.value,
            mounted_path=item.mounted_path,
            sha256=item.sha256,
        )
        for item in record.entries
    )
    return PortableQualificationDatasetManifest(
        manifest_id="auragateway-environment-qualification-offline-dataset-v1",
        entries=(entries[0], entries[1], entries[2]),
    )


def validate_issuance_inputs(
    *,
    repo_root: Path,
    materialization_record_path: Path,
    runtime_manifest_path: Path,
) -> dict[str, object]:
    """Validate exact issuance inputs without creating operational authority."""

    try:
        record = MaterializedOfflineDatasetRecord.model_validate_json(
            materialization_record_path.read_text(encoding="utf-8")
        )
        observed_manifest = PortableQualificationDatasetManifest.model_validate_json(
            runtime_manifest_path.read_text(encoding="utf-8")
        )
    except ValidationError as exc:
        raise AuthorizationPackageError(
            "ISSUANCE_INPUT_INVALID",
            "one or more authorization issuance inputs failed contract validation",
        ) from exc

    expected_manifest = build_portable_runtime_manifest(record)
    if observed_manifest.canonical_json() != expected_manifest.canonical_json():
        raise AuthorizationPackageError(
            "RUNTIME_DATASET_MANIFEST_DRIFT",
            "runtime dataset manifest does not match the materialization record",
            runtime_manifest_path.as_posix(),
        )
    if record.runtime_manifest_sha256 != observed_manifest.fingerprint():
        raise AuthorizationPackageError(
            "RUNTIME_DATASET_MANIFEST_IDENTITY_MISMATCH",
            "materialization record does not bind the runtime dataset manifest",
            runtime_manifest_path.as_posix(),
        )

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                record.harness_source_commit,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationPackageError(
            "HARNESS_SOURCE_ANCESTRY_UNREADABLE",
            "materialized harness source ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise AuthorizationPackageError(
            "HARNESS_SOURCE_COMMIT_MISSING",
            "materialized harness source commit must be an ancestor of current HEAD",
            details=(record.harness_source_commit,),
        )

    adapter_path = repo_root / RUNTIME_ADAPTER_PATH
    if not adapter_path.is_file():
        raise AuthorizationPackageError(
            "RUNTIME_ADAPTER_NOT_FOUND",
            "runtime adapter is missing before authorization issuance review",
            RUNTIME_ADAPTER_PATH.as_posix(),
        )
    _audit_runtime_adapter(adapter_path)
    return {
        "materialization_record_sha256": record.fingerprint(),
        "runtime_dataset_manifest_sha256": observed_manifest.fingerprint(),
        "runtime_adapter_sha256": _file_sha256(adapter_path),
        "harness_source_commit": record.harness_source_commit,
        "exact_kaggle_dataset_count": 3,
        "final_authorization_generated": False,
        "kaggle_session_started": False,
        "next_gate": NEXT_GATE,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-qualification-authorization-package")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    inspect_parser = subparsers.add_parser("inspect-issuance-inputs")
    inspect_parser.add_argument("--repo-root", type=Path, required=True)
    inspect_parser.add_argument("--materialization-record", type=Path, required=True)
    inspect_parser.add_argument("--runtime-manifest", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the deterministic authorization-package command surface."""

    try:
        arguments = _build_parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            summary = generate_static_authorization_package(repo_root)
        elif arguments.command == "verify":
            summary = verify_static_authorization_package(repo_root)
        else:
            summary = validate_issuance_inputs(
                repo_root=repo_root,
                materialization_record_path=cast(Path, arguments.materialization_record),
                runtime_manifest_path=cast(Path, arguments.runtime_manifest),
            )
    except AuthorizationPackageError as exc:
        print(
            AuthorizationPackageErrorEnvelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                path=exc.path,
                details=exc.details,
            ).canonical_json(),
            end="",
        )
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
