"""Build, verify, and later execute the bounded qualification package."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Never, cast

from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts import (
    AUTHORIZATION_PATH,
    EXECUTION_REQUEST_PATH,
    NEXT_GATE,
    NOTEBOOK_PATH,
    REQUIRED_METRIC_SEMANTICS,
    REQUIRED_RESET_STEPS,
    REQUIRED_RUNTIME_LOCK_FIELDS,
    REQUIRED_STOP_CONDITIONS,
    REVIEW_GIT_BLOB_SHA,
    REVIEW_PATH,
    REVIEW_SOURCE_GIT_BLOB_SHA,
    REVIEW_SOURCE_PATH,
    RUNBOOK_PATH,
    RUNTIME_EVIDENCE_PATHS,
    SOURCE_MAIN_MERGE_COMMIT,
    STATIC_REQUEST_GIT_BLOB_SHA,
    STATIC_REQUEST_PATH,
    WORKER_STARTUP_PLAN_GIT_BLOB_SHA,
    WORKER_STARTUP_PLAN_PATH,
    AuthorizationDecision,
    DatasetRoleRequirement,
    ExecutionPackageSafetyEnvelope,
    ExecutionPackageStatus,
    FullABCLocalEnvironmentQualificationExecutionError,
    FullABCLocalEnvironmentQualificationExecutionErrorEnvelope,
    ProbePhase,
    QualificationDatasetManifest,
    QualificationExecutionAuthorization,
    QualificationExecutionRequest,
    QualificationManifest,
    QualificationManifestEntry,
    QualificationProbeBudget,
    QualificationRuntimeAdapter,
    QualificationRuntimeCapture,
    RuntimeEvidenceRequirement,
    SourceAuthorityBinding,
    SyntheticProbeDefinition,
)

_RUNTIME_EVIDENCE_IDS = (
    "cache-metric-capability-report",
    "gpu-topology-report",
    "kaggle-runtime-dependency-lock",
    "qualification-manifest",
    "model-identity-report",
    "qualification-report",
    "reset-capability-report",
    "worker-health-report",
)

_EVIDENCE_SCHEMA_IDS = (
    "auragateway-cache-metric-capability-report-v1",
    "auragateway-gpu-topology-report-v1",
    "auragateway-kaggle-runtime-dependency-lock-v1",
    "auragateway-environment-qualification-manifest-v1",
    "auragateway-model-identity-report-v1",
    "auragateway-environment-qualification-report-v1",
    "auragateway-reset-capability-report-v1",
    "auragateway-worker-health-report-v1",
)

_PREFIX_TEMPLATE = (
    "Synthetic reliability probe. Preserve this exact prefix and answer only with JSON. "
)
_SUFFIX_TEMPLATES = {
    "cold": '{"probe":"cold","value":1}',
    "warm": '{"probe":"warm","value":2}',
    "post-reset": '{"probe":"post-reset","value":3}',
}


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "INVALID_COMMAND_ARGUMENTS",
            "qualification-execution command arguments are invalid",
            details=(message,),
        )


def _canonical_sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "ATOMIC_WRITE_FAILED",
            "a qualification artifact could not be written atomically",
            path.as_posix(),
        ) from exc


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "REQUIRED_ASSET_NOT_FOUND",
            "a required qualification-execution asset was not found",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "REQUIRED_ASSET_INVALID_JSON",
            "a required qualification-execution asset is not valid JSON",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "REQUIRED_ASSET_INVALID_ROOT",
            "a required qualification-execution asset must be one JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _git_blob_sha(repo_root: Path, relative_path: Path) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                f"HEAD:{relative_path.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required qualification-execution Git authority could not be resolved",
            relative_path.as_posix(),
        ) from exc
    identity = result.stdout.strip()
    if len(identity) != 40 or any(character not in "0123456789abcdef" for character in identity):
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required qualification-execution Git authority returned an invalid identity",
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
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 103 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def _validate_repository_authorities(repo_root: Path) -> None:
    _require_source_ancestor(repo_root)
    expected = {
        REVIEW_PATH: REVIEW_GIT_BLOB_SHA,
        REVIEW_SOURCE_PATH: REVIEW_SOURCE_GIT_BLOB_SHA,
        STATIC_REQUEST_PATH: STATIC_REQUEST_GIT_BLOB_SHA,
        WORKER_STARTUP_PLAN_PATH: WORKER_STARTUP_PLAN_GIT_BLOB_SHA,
    }
    drift = tuple(
        sorted(
            path.as_posix()
            for path, expected_sha in expected.items()
            if _git_blob_sha(repo_root, path) != expected_sha
        )
    )
    if drift:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "QUALIFICATION_EXECUTION_AUTHORITY_DRIFT",
            "one or more qualification-execution authorities drifted",
            details=drift,
        )

    review = _load_json_object(repo_root / REVIEW_PATH)
    required_review = {
        "decision": "APPROVED_FOR_QUALIFICATION_EXECUTION_IMPLEMENTATION",
        "next_gate": "full_abc_local_full_run_environment_qualification_execution_implementation",
        "source_main_merge_commit": "3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8",
    }
    if any(
        review.get(field) != expected_value for field, expected_value in required_review.items()
    ):
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "QUALIFICATION_EXECUTION_REVIEW_DRIFT",
            "the merged review no longer authorizes this implementation",
            REVIEW_PATH.as_posix(),
        )


def _source_authorities() -> tuple[SourceAuthorityBinding, ...]:
    return tuple(
        sorted(
            (
                SourceAuthorityBinding(
                    authority_id="execution-review",
                    path=REVIEW_PATH.as_posix(),
                    git_blob_sha=REVIEW_GIT_BLOB_SHA,
                ),
                SourceAuthorityBinding(
                    authority_id="execution-review-source",
                    path=REVIEW_SOURCE_PATH.as_posix(),
                    git_blob_sha=REVIEW_SOURCE_GIT_BLOB_SHA,
                ),
                SourceAuthorityBinding(
                    authority_id="qualification-request",
                    path=STATIC_REQUEST_PATH.as_posix(),
                    git_blob_sha=STATIC_REQUEST_GIT_BLOB_SHA,
                ),
                SourceAuthorityBinding(
                    authority_id="worker-startup-plan",
                    path=WORKER_STARTUP_PLAN_PATH.as_posix(),
                    git_blob_sha=WORKER_STARTUP_PLAN_GIT_BLOB_SHA,
                ),
            ),
            key=lambda item: item.authority_id,
        )
    )


def _synthetic_probes() -> tuple[SyntheticProbeDefinition, ...]:
    return (
        SyntheticProbeDefinition(
            probe_id="worker-1-cold-prefix",
            worker_id="worker_1",
            phase=ProbePhase.COLD_PREFIX,
            sequence_index=1,
            prefix_template_id="synthetic-cache-prefix-v1",
            suffix_template_id="synthetic-cold-suffix-v1",
        ),
        SyntheticProbeDefinition(
            probe_id="worker-1-warm-prefix",
            worker_id="worker_1",
            phase=ProbePhase.WARM_PREFIX,
            sequence_index=2,
            prefix_template_id="synthetic-cache-prefix-v1",
            suffix_template_id="synthetic-warm-suffix-v1",
            prior_probe_id="worker-1-cold-prefix",
        ),
        SyntheticProbeDefinition(
            probe_id="worker-2-cold-prefix",
            worker_id="worker_2",
            phase=ProbePhase.COLD_PREFIX,
            sequence_index=3,
            prefix_template_id="synthetic-cache-prefix-v1",
            suffix_template_id="synthetic-cold-suffix-v1",
        ),
        SyntheticProbeDefinition(
            probe_id="worker-2-warm-prefix",
            worker_id="worker_2",
            phase=ProbePhase.WARM_PREFIX,
            sequence_index=4,
            prefix_template_id="synthetic-cache-prefix-v1",
            suffix_template_id="synthetic-warm-suffix-v1",
            prior_probe_id="worker-2-cold-prefix",
        ),
        SyntheticProbeDefinition(
            probe_id="worker-1-post-reset-baseline",
            worker_id="worker_1",
            phase=ProbePhase.POST_RESET_BASELINE,
            sequence_index=5,
            prefix_template_id="synthetic-cache-prefix-v1",
            suffix_template_id="synthetic-post-reset-suffix-v1",
            prior_probe_id="worker-1-warm-prefix",
        ),
        SyntheticProbeDefinition(
            probe_id="worker-2-post-reset-baseline",
            worker_id="worker_2",
            phase=ProbePhase.POST_RESET_BASELINE,
            sequence_index=6,
            prefix_template_id="synthetic-cache-prefix-v1",
            suffix_template_id="synthetic-post-reset-suffix-v1",
            prior_probe_id="worker-2-warm-prefix",
        ),
    )


def synthetic_probe_payload(probe_id: str) -> tuple[str, str]:
    """Return fixed synthetic content without logging or customer data."""

    mapping = {
        "worker-1-cold-prefix": "cold",
        "worker-1-warm-prefix": "warm",
        "worker-2-cold-prefix": "cold",
        "worker-2-warm-prefix": "warm",
        "worker-1-post-reset-baseline": "post-reset",
        "worker-2-post-reset-baseline": "post-reset",
    }
    try:
        suffix_key = mapping[probe_id]
    except KeyError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "UNKNOWN_SYNTHETIC_PROBE",
            "requested synthetic qualification probe is not registered",
            details=(probe_id,),
        ) from exc
    return _PREFIX_TEMPLATE, _SUFFIX_TEMPLATES[suffix_key]


def _runtime_evidence_requirements() -> tuple[RuntimeEvidenceRequirement, ...]:
    return tuple(
        RuntimeEvidenceRequirement(
            evidence_id=evidence_id,
            path=path.as_posix(),
            schema_id=schema_id,
        )
        for evidence_id, path, schema_id in zip(
            _RUNTIME_EVIDENCE_IDS,
            RUNTIME_EVIDENCE_PATHS,
            _EVIDENCE_SCHEMA_IDS,
            strict=True,
        )
    )


def build_execution_request() -> QualificationExecutionRequest:
    """Build the deterministic static request with execution authority disabled."""

    return QualificationExecutionRequest(
        request_id=("auragateway-full-abc-local-environment-qualification-execution-request-v1"),
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        status=ExecutionPackageStatus.STATIC_PACKAGE_GENERATED_AUTHORIZATION_BLOCKED,
        source_authorities=_source_authorities(),
        probe_budget=QualificationProbeBudget(),
        synthetic_probes=_synthetic_probes(),
        dataset_roles=(
            DatasetRoleRequirement(role="harness_source"),
            DatasetRoleRequirement(role="model_artifacts"),
            DatasetRoleRequirement(role="vllm_wheel"),
        ),
        required_runtime_lock_fields=REQUIRED_RUNTIME_LOCK_FIELDS,
        required_metric_semantics=REQUIRED_METRIC_SEMANTICS,
        required_reset_steps=REQUIRED_RESET_STEPS,
        stop_conditions=REQUIRED_STOP_CONDITIONS,
        runtime_evidence=_runtime_evidence_requirements(),
        authorization_path=(
            "benchmarks/local_abc/"
            "auragateway_full_abc_local_full_run_environment_qualification_"
            "execution_authorization_v1.json"
        ),
        safety=ExecutionPackageSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def build_notebook_payload() -> dict[str, object]:
    """Build a deterministic unexecuted notebook that delegates to the typed runner."""

    markdown = (
        "# AuraGateway full-run environment qualification\n\n"
        "This notebook is an execution surface, not authorization. It must not be run "
        "until the exact authorization, dataset manifest, and runtime factory binding "
        "have been merged and supplied. No benchmark trajectory is permitted."
    )
    code = (
        "from auragateway.local_abc."
        "full_abc_local_environment_qualification_execution import (\n"
        "    execute_from_environment,\n"
        ")\n\n"
        "summary = execute_from_environment()\n"
        "summary\n"
    )
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [line + "\n" for line in markdown.splitlines()],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [line + "\n" for line in code.splitlines()],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
            "auragateway": {
                "execution_authorized": False,
                "maximum_model_requests": 8,
                "benchmark_trajectory_requests_permitted": 0,
                "next_gate": NEXT_GATE,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _canonical_notebook_json() -> str:
    return (
        json.dumps(
            build_notebook_payload(),
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    )


def generate_static_package(repo_root: Path) -> dict[str, object]:
    """Generate only the static request and notebook after source validation."""

    _validate_repository_authorities(repo_root)
    request = build_execution_request()
    _write_text_atomic(repo_root / EXECUTION_REQUEST_PATH, request.canonical_json())
    _write_text_atomic(repo_root / NOTEBOOK_PATH, _canonical_notebook_json())
    return verify_static_package(repo_root)


def _require_package_files(repo_root: Path) -> None:
    required = (
        EXECUTION_REQUEST_PATH,
        NOTEBOOK_PATH,
        RUNBOOK_PATH,
        Path(
            "src/auragateway/local_abc/"
            "full_abc_local_environment_qualification_execution_contracts.py"
        ),
        Path("src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py"),
        Path("tests/unit/local_abc/test_full_abc_local_environment_qualification_execution.py"),
    )
    missing = tuple(path.as_posix() for path in required if not (repo_root / path).is_file())
    if missing:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_PACKAGE_INCOMPLETE",
            "one or more qualification-execution package files are missing",
            details=missing,
        )


def verify_static_package(repo_root: Path) -> dict[str, object]:
    """Verify package determinism and prove that no runtime evidence exists."""

    _validate_repository_authorities(repo_root)
    _require_package_files(repo_root)
    expected_request = build_execution_request()
    try:
        observed_request = QualificationExecutionRequest.model_validate(
            _load_json_object(repo_root / EXECUTION_REQUEST_PATH)
        )
    except ValidationError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_REQUEST_INVALID",
            "the qualification execution request failed contract validation",
            EXECUTION_REQUEST_PATH.as_posix(),
        ) from exc
    if observed_request.canonical_json() != expected_request.canonical_json():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_REQUEST_DRIFT",
            "the qualification execution request drifted from deterministic output",
            EXECUTION_REQUEST_PATH.as_posix(),
        )

    notebook_path = repo_root / NOTEBOOK_PATH
    if notebook_path.read_text(encoding="utf-8") != _canonical_notebook_json():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_NOTEBOOK_DRIFT",
            "the qualification notebook drifted from deterministic output",
            NOTEBOOK_PATH.as_posix(),
        )

    unexpected = tuple(
        path.as_posix() for path in RUNTIME_EVIDENCE_PATHS if (repo_root / path).exists()
    )
    if unexpected:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_EVIDENCE_PREMATURE",
            "runtime evidence exists before execution authorization",
            details=unexpected,
        )
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "AUTHORIZATION_PREMATURE",
            "execution authorization exists before its review gate",
            AUTHORIZATION_PATH.as_posix(),
        )

    return {
        "request_sha256": expected_request.fingerprint(),
        "notebook_sha256": _file_sha256(notebook_path),
        "execution_package_generated": True,
        "runtime_evidence_generated": False,
        "execution_authorized": False,
        "kaggle_session_started": False,
        "gpu_execution_performed": False,
        "worker_started": False,
        "model_execution_performed": False,
        "maximum_model_requests": 8,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
        "next_gate": NEXT_GATE,
    }


def _load_authorization(path: Path) -> QualificationExecutionAuthorization:
    try:
        return QualificationExecutionAuthorization.model_validate(_load_json_object(path))
    except ValidationError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_AUTHORIZATION_INVALID",
            "the qualification execution authorization is invalid",
            path.as_posix(),
        ) from exc


def _load_dataset_manifest(path: Path) -> QualificationDatasetManifest:
    try:
        return QualificationDatasetManifest.model_validate(_load_json_object(path))
    except ValidationError as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "DATASET_MANIFEST_INVALID",
            "the offline qualification dataset manifest is invalid",
            path.as_posix(),
        ) from exc


def _validate_dataset_files(dataset_manifest: QualificationDatasetManifest) -> None:
    drift: list[str] = []
    for entry in dataset_manifest.entries:
        mounted_path = Path(entry.mounted_path)
        if not mounted_path.is_file():
            drift.append(f"{entry.role}:missing")
            continue
        if _file_sha256(mounted_path) != entry.sha256:
            drift.append(f"{entry.role}:sha256")
    if drift:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "DATASET_MANIFEST_DRIFT",
            "one or more offline dataset inputs do not match the authorized manifest",
            details=tuple(sorted(drift)),
        )


def _validate_authorized_inputs(
    request: QualificationExecutionRequest,
    authorization: QualificationExecutionAuthorization,
    dataset_manifest: QualificationDatasetManifest,
    *,
    now: datetime,
) -> None:
    _validate_dataset_files(dataset_manifest)
    if authorization.decision is not AuthorizationDecision.AUTHORIZED:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_NOT_AUTHORIZED",
            "qualification execution has not been authorized",
        )
    if now.tzinfo is None or now.utcoffset() is None:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_TIME_INVALID",
            "qualification execution time must be timezone-aware",
        )
    if not authorization.issued_at <= now < authorization.expires_at:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_AUTHORIZATION_EXPIRED",
            "qualification execution authorization is outside its validity window",
        )
    if authorization.request_sha256 != request.fingerprint():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_REQUEST_IDENTITY_MISMATCH",
            "authorization does not bind the current execution request",
        )
    if authorization.dataset_manifest_sha256 != dataset_manifest.fingerprint():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "DATASET_MANIFEST_IDENTITY_MISMATCH",
            "authorization does not bind the supplied dataset manifest",
        )
    adapter_path = Path(authorization.runtime_factory.artifact_path)
    if _file_sha256(adapter_path) != authorization.runtime_factory.artifact_sha256:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_ADAPTER_IDENTITY_MISMATCH",
            "runtime adapter identity does not match authorization",
            adapter_path.as_posix(),
        )


def _load_runtime_adapter(
    authorization: QualificationExecutionAuthorization,
) -> QualificationRuntimeAdapter:
    module_name, factory_name = authorization.runtime_factory.factory_path.split(":", maxsplit=1)
    artifact_path = Path(authorization.runtime_factory.artifact_path)
    spec = importlib.util.spec_from_file_location(module_name, artifact_path)
    if spec is None or spec.loader is None:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_ADAPTER_IMPORT_FAILED",
            "runtime adapter module could not be loaded",
            artifact_path.as_posix(),
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        factory = getattr(module, factory_name)
        adapter = factory()
    except (AttributeError, ImportError, TypeError) as exc:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_ADAPTER_IMPORT_FAILED",
            "runtime adapter factory could not be constructed",
            artifact_path.as_posix(),
        ) from exc
    if not isinstance(adapter, QualificationRuntimeAdapter):
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_ADAPTER_CONTRACT_INVALID",
            "runtime adapter does not satisfy the qualification protocol",
            artifact_path.as_posix(),
        )
    return adapter


def _manifest_entries(
    capture: QualificationRuntimeCapture,
) -> tuple[QualificationManifestEntry, ...]:
    models = (
        (RUNTIME_EVIDENCE_PATHS[0], capture.metric_capability),
        (RUNTIME_EVIDENCE_PATHS[1], capture.gpu_topology),
        (RUNTIME_EVIDENCE_PATHS[2], capture.dependency_lock),
        (RUNTIME_EVIDENCE_PATHS[4], capture.model_identity),
        (RUNTIME_EVIDENCE_PATHS[5], capture.qualification_report),
        (RUNTIME_EVIDENCE_PATHS[6], capture.reset_capability),
        (RUNTIME_EVIDENCE_PATHS[7], capture.worker_health),
    )
    entries: list[QualificationManifestEntry] = []
    for path, model in models:
        entries.append(
            QualificationManifestEntry(
                evidence_id=model.evidence_id,
                path=path.as_posix(),
                sha256=_canonical_sha256(model.canonical_json()),
            )
        )
    return tuple(entries)


def _commit_runtime_evidence(repo_root: Path, capture: QualificationRuntimeCapture) -> None:
    entries = _manifest_entries(capture)
    report = capture.qualification_report
    manifest = QualificationManifest(
        evidence_id="qualification-manifest",
        runtime_session_id=report.runtime_session_id,
        captured_at=report.captured_at,
        source_request_sha256=report.source_request_sha256,
        dataset_manifest_sha256=report.dataset_manifest_sha256,
        entries=entries,
    )
    models = {
        RUNTIME_EVIDENCE_PATHS[0]: capture.metric_capability,
        RUNTIME_EVIDENCE_PATHS[1]: capture.gpu_topology,
        RUNTIME_EVIDENCE_PATHS[2]: capture.dependency_lock,
        RUNTIME_EVIDENCE_PATHS[3]: manifest,
        RUNTIME_EVIDENCE_PATHS[4]: capture.model_identity,
        RUNTIME_EVIDENCE_PATHS[5]: capture.qualification_report,
        RUNTIME_EVIDENCE_PATHS[6]: capture.reset_capability,
        RUNTIME_EVIDENCE_PATHS[7]: capture.worker_health,
    }
    existing = tuple(path.as_posix() for path in models if (repo_root / path).exists())
    if existing:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_EVIDENCE_ALREADY_EXISTS",
            "runtime evidence paths must be empty before qualification execution",
            details=existing,
        )

    staged: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        for relative_path, model in models.items():
            target = repo_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(model.canonical_json())
                staged.append((Path(handle.name), target))
        for temporary, target in staged:
            temporary.replace(target)
            committed.append(target)
    except OSError as exc:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        for target in committed:
            target.unlink(missing_ok=True)
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_EVIDENCE_COMMIT_FAILED",
            "validated runtime evidence could not be committed transactionally",
        ) from exc


def execute_qualification(
    *,
    repo_root: Path,
    request: QualificationExecutionRequest,
    authorization: QualificationExecutionAuthorization,
    dataset_manifest: QualificationDatasetManifest,
    adapter: QualificationRuntimeAdapter,
    now: datetime,
) -> dict[str, object]:
    """Execute one authorized capture and commit evidence only after validation."""

    _validate_authorized_inputs(request, authorization, dataset_manifest, now=now)
    capture = adapter.capture(request, dataset_manifest)
    if capture.qualification_report.source_request_sha256 != request.fingerprint():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_CAPTURE_REQUEST_MISMATCH",
            "runtime capture does not bind the authorized request",
        )
    if capture.qualification_report.dataset_manifest_sha256 != dataset_manifest.fingerprint():
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "RUNTIME_CAPTURE_DATASET_MISMATCH",
            "runtime capture does not bind the authorized dataset manifest",
        )
    _commit_runtime_evidence(repo_root, capture)
    return {
        "runtime_session_id": capture.qualification_report.runtime_session_id,
        "model_request_count": capture.qualification_report.model_request_count,
        "runtime_evidence_generated": True,
        "runtime_evidence_count": 8,
        "environment_qualified": True,
        "measured_execution_authorized": False,
        "external_spend": 0,
        "next_gate": "full_abc_local_full_run_environment_qualification_evidence_review",
    }


def execute_from_paths(
    *,
    repo_root: Path,
    authorization_path: Path,
    dataset_manifest_path: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Load exact operational inputs and run through the typed adapter boundary."""

    request = QualificationExecutionRequest.model_validate(
        _load_json_object(repo_root / EXECUTION_REQUEST_PATH)
    )
    authorization = _load_authorization(authorization_path)
    dataset_manifest = _load_dataset_manifest(dataset_manifest_path)
    _validate_authorized_inputs(
        request,
        authorization,
        dataset_manifest,
        now=now or datetime.now(UTC),
    )
    adapter = _load_runtime_adapter(authorization)
    return execute_qualification(
        repo_root=repo_root,
        request=request,
        authorization=authorization,
        dataset_manifest=dataset_manifest,
        adapter=adapter,
        now=now or datetime.now(UTC),
    )


def execute_from_environment() -> dict[str, object]:
    """Notebook entrypoint requiring explicit environment-provided paths."""

    repo_root_raw = os.environ.get("AURAGATEWAY_REPO_ROOT")
    authorization_raw = os.environ.get("AURAGATEWAY_QUALIFICATION_AUTHORIZATION")
    dataset_manifest_raw = os.environ.get("AURAGATEWAY_QUALIFICATION_DATASET_MANIFEST")
    missing = tuple(
        name
        for name, value in (
            ("AURAGATEWAY_REPO_ROOT", repo_root_raw),
            ("AURAGATEWAY_QUALIFICATION_AUTHORIZATION", authorization_raw),
            ("AURAGATEWAY_QUALIFICATION_DATASET_MANIFEST", dataset_manifest_raw),
        )
        if value is None
    )
    if missing:
        raise FullABCLocalEnvironmentQualificationExecutionError(
            "EXECUTION_ENVIRONMENT_INCOMPLETE",
            "qualification execution environment is missing required path bindings",
            details=missing,
        )
    return execute_from_paths(
        repo_root=Path(cast(str, repo_root_raw)),
        authorization_path=Path(cast(str, authorization_raw)),
        dataset_manifest_path=Path(cast(str, dataset_manifest_raw)),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-environment-qualification-execution")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "verify"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--repo-root", type=Path, required=True)
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--repo-root", type=Path, required=True)
    execute_parser.add_argument("--authorization", type=Path, required=True)
    execute_parser.add_argument("--dataset-manifest", type=Path, required=True)
    return parser


def _error_envelope(
    error: FullABCLocalEnvironmentQualificationExecutionError,
) -> str:
    return FullABCLocalEnvironmentQualificationExecutionErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Run static package generation, verification, or authorized execution."""

    try:
        arguments = _build_parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            summary = generate_static_package(repo_root)
        elif arguments.command == "verify":
            summary = verify_static_package(repo_root)
        else:
            summary = execute_from_paths(
                repo_root=repo_root,
                authorization_path=cast(Path, arguments.authorization).resolve(),
                dataset_manifest_path=cast(Path, arguments.dataset_manifest).resolve(),
            )
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0
    except FullABCLocalEnvironmentQualificationExecutionError as error:
        print(_error_envelope(error), file=sys.stderr)
        return 2
    except (OSError, ValidationError) as error:
        envelope = FullABCLocalEnvironmentQualificationExecutionErrorEnvelope(
            error_code="UNEXPECTED_VALIDATION_FAILURE",
            safe_message="qualification execution failed at a typed validation boundary",
            details=(type(error).__name__,),
        )
        print(envelope.canonical_json(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
