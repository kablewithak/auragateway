"""Validate the deterministic T4 attention-backend remediation review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

REPOSITORY_BASE_COMMIT: Final = "431b5854037504b2ce3b2362bf37d8762ce2d227"
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_flashinfer_link_failure_remediation_review_v1.json"
)
RECORD_SHA256: Final = "064585697baab971a216709592dda8e3a23c30151340e23a352190aa502635fb"
FAILURE_EVIDENCE_PATH: Final = Path(
    "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/ag-qualification-evidence-v1.zip"
)
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
DECISION: Final = "APPROVED_FOR_DETERMINISTIC_T4_ATTENTION_BACKEND_IMPLEMENTATION"
NEXT_GATE: Final = "merge_then_implement_deterministic_t4_attention_backend"
EXPECTED_EVIDENCE: Final = (
    (
        "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/"
        "consumed_environment_qualification_authorization_v1.json",
        "1990a0e5862dfcbb3706a88a3f2c5a075386a85a37a6525416f5742249f3b5cf",
        1429,
    ),
    (
        "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/"
        "ag-qualification-control-materializer-v1.log",
        "730ff137f55ff1de076b559a812732a390e0deded4ba0e17e43d7321835eecbd",
        1655,
    ),
    (
        "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/"
        "ag-qualification-control-materializer-v1-results.zip",
        "436383faa79e48a7f10e36862cfe539430b99223258d71132c5055dafdc5a059",
        4722,
    ),
    (
        "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/"
        "ag-full-abc-env-qualification-v1.log",
        "05f302f70ec190ed8a87524599b4252753f9484aaef39b29ff858f5665b01020",
        5324,
    ),
    (
        "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/"
        "ag-qualification-evidence-v1.zip",
        "d8c3f034efb262440f42bcdfdaa382601ac0dd937106e13bf999e8e2028d3118",
        11221,
    ),
    (
        "evidence_vault/local_abc/cu129-flashinfer-link-failure-v1/"
        "fresh_qualification_preparation.json",
        "1a7d6a93ec0d38960ff7364c8784d46f5040ec4ec1c76f22ac113211eb8fd47e",
        3606,
    ),
)
EXPECTED_FAILURE_MEMBERS: Final = frozenset(
    {
        "launcher_failure.json",
        "launcher_failure_trace.txt",
        "worker_startup_diagnostic.json",
    }
)


class AttentionBackendRemediationReviewError(RuntimeError):
    """Fail-closed review validation error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AttentionBackendRemediationReviewError(message)


class EvidenceArtifact(LocalABCContract):
    """One immutable failure-evidence artifact."""

    path: str
    sha256: str
    size_bytes: int = Field(ge=1)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("evidence digest must be lowercase SHA-256")
        return value


class FailureObservation(LocalABCContract):
    """Bounded facts from the failed governed qualification."""

    status: Literal["FAILED_CLOSED"]
    stage: Literal["initial_worker_startup"]
    root_cause: Literal["FLASHINFER_JIT_CUDA_DRIVER_LINK_LIBRARY_UNAVAILABLE"]
    root_cause_confidence: Literal["CONFIRMED"]
    failed_attention_backend: Literal["FLASHINFER"]
    linker_error: Literal["/usr/bin/ld: cannot find -lcuda: No such file or directory"]
    pinned_vllm_version: Literal["0.19.1"]
    runtime_installation_reached: Literal[True]
    model_weights_loaded: Literal[True]
    workers_started: Literal[2]
    workers_ready: Literal[0]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    hidden_retries_performed: Literal[0]
    workers_replaced: Literal[0]
    identity_mismatch: Literal[False]


class WorkerObservation(LocalABCContract):
    """One governed worker startup observation."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    port: Literal[8001, 8002]
    process_returncode: Literal[1]
    ready: Literal[False]
    command_sha256: str
    linker_failure: Literal["cannot find -lcuda"]
    model_weights_loaded_before_failure: Literal[True]

    @field_validator("command_sha256")
    @classmethod
    def validate_command_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("command digest must be lowercase SHA-256")
        return value


class ImplementationBoundary(LocalABCContract):
    """Authorized implementation behavior after merge."""

    selected_backend: Literal["TRITON_ATTN"]
    selection_interface: Literal["vllm_api_server_cli_--attention-backend"]
    automatic_backend_selection_permitted: Literal[False]
    flashinfer_fallback_permitted: Literal[False]
    required_changes: tuple[str, ...] = Field(min_length=7)
    runtime_wheelhouse_change_expected: Literal[False]
    model_snapshot_change_expected: Literal[False]
    kaggle_specific_libcuda_symlink_permitted: Literal[False]
    precompiled_flashinfer_artifact_permitted: Literal[False]


class AuthorityTransition(LocalABCContract):
    """Authority migration required before a future retry."""

    current_harness_unchanged: Literal[True]
    current_harness_reusable_for_retry: Literal[False]
    consumed_authorization_reusable: Literal[False]
    fresh_issuer_usable: Literal[False]
    post_merge_harness_source_package_required: Literal[True]
    cpu_only_materialization_required: Literal[True]
    metadata_only_inspection_required: Literal[True]
    new_harness_integration_required: Literal[True]
    fresh_authorization_required_before_retry: Literal[True]


class CircuitBreaker(LocalABCContract):
    """Prevent silent fallback and unchanged reruns."""

    trigger: Literal["triton_backend_worker_startup_or_runtime_contract_failure"]
    required_action: Literal["preserve_new_evidence_and_reassess_runtime_backend_contract"]
    silent_backend_fallback_permitted: Literal[False]
    unchanged_rerun_permitted: Literal[False]


class ReviewSafety(LocalABCContract):
    """Review-only safety state."""

    authorization_issued: Literal[False]
    kaggle_execution_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    runtime_source_changed: Literal[False]
    model_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]
    measured_execution_authorized: Literal[False]


class AttentionBackendRemediationReviewRecord(LocalABCContract):
    """Canonical evidence and implementation-authorization contract."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-cu129-flashinfer-link-failure-remediation-review-v1"]
    repository_base_commit: Literal["431b5854037504b2ce3b2362bf37d8762ce2d227"]
    decision: Literal["APPROVED_FOR_DETERMINISTIC_T4_ATTENTION_BACKEND_IMPLEMENTATION"]
    failure: FailureObservation
    workers: tuple[WorkerObservation, WorkerObservation]
    evidence: tuple[EvidenceArtifact, ...] = Field(
        min_length=6,
        max_length=6,
    )
    implementation_boundary: ImplementationBoundary
    authority_transition: AuthorityTransition
    circuit_breaker: CircuitBreaker
    safety: ReviewSafety
    next_gate: Literal["merge_then_implement_deterministic_t4_attention_backend"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_fixed_order(self) -> Self:
        observed_evidence = tuple(
            (item.path, item.sha256, item.size_bytes) for item in self.evidence
        )
        if observed_evidence != EXPECTED_EVIDENCE:
            raise ValueError("review evidence identity or order drifted")
        observed_workers = tuple(
            (
                worker.worker_id,
                worker.gpu_index,
                worker.port,
                worker.command_sha256,
            )
            for worker in self.workers
        )
        expected_workers = (
            (
                "worker_1",
                0,
                8001,
                "fe37b6f369b4d83b4aea467f3e4d06f32bd62a8b44b4568665255ec35552958f",
            ),
            (
                "worker_2",
                1,
                8002,
                "c28cea7cdfd6d5034a94ac34f090973949bbd401c5179493ddca44b17899fd06",
            ),
        )
        if observed_workers != expected_workers:
            raise ValueError("review worker observations drifted")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_record(
    path: Path,
) -> AttentionBackendRemediationReviewRecord:
    try:
        observed = path.read_text(encoding="utf-8")
        record = AttentionBackendRemediationReviewRecord.model_validate_json(observed)
    except OSError as exc:
        raise AttentionBackendRemediationReviewError(
            "attention-backend review record is unreadable"
        ) from exc
    if observed != record.canonical_json():
        raise AttentionBackendRemediationReviewError(
            "attention-backend review record is not canonical JSON"
        )
    if _sha256(path) != RECORD_SHA256:
        raise AttentionBackendRemediationReviewError(
            "attention-backend review record identity drifted"
        )
    return record


def _require_base_ancestor(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        return
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            REPOSITORY_BASE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise AttentionBackendRemediationReviewError(
            "the failed-attempt repository base is not an ancestor of HEAD"
        )


def _require_authorization_absent(repo_root: Path) -> None:
    if (repo_root / FINAL_AUTHORIZATION_PATH).exists():
        raise AttentionBackendRemediationReviewError("a live transient authorization is prohibited")


def _require_evidence(
    repo_root: Path,
    record: AttentionBackendRemediationReviewRecord,
) -> None:
    for artifact in record.evidence:
        path = repo_root / artifact.path
        if not path.is_file():
            raise AttentionBackendRemediationReviewError(
                f"review evidence is missing: {artifact.path}"
            )
        if path.stat().st_size != artifact.size_bytes or _sha256(path) != artifact.sha256:
            raise AttentionBackendRemediationReviewError(
                f"review evidence identity drifted: {artifact.path}"
            )


def _json_object(raw: bytes, label: str) -> dict[str, object]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AttentionBackendRemediationReviewError(f"{label} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise AttentionBackendRemediationReviewError(f"{label} must contain one object")
    return cast(dict[str, object], payload)


def _require_failure_evidence(repo_root: Path) -> None:
    path = repo_root / FAILURE_EVIDENCE_PATH
    try:
        with zipfile.ZipFile(path) as archive:
            if frozenset(archive.namelist()) != EXPECTED_FAILURE_MEMBERS:
                raise AttentionBackendRemediationReviewError("failure evidence member set drifted")
            launcher_failure = _json_object(
                archive.read("launcher_failure.json"),
                "launcher failure",
            )
            diagnostic = _json_object(
                archive.read("worker_startup_diagnostic.json"),
                "worker startup diagnostic",
            )
    except (OSError, zipfile.BadZipFile) as exc:
        raise AttentionBackendRemediationReviewError("failure evidence ZIP is unreadable") from exc

    workers = diagnostic.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise AttentionBackendRemediationReviewError("failure diagnostic must contain two workers")

    aggregate: list[str] = []
    for worker in workers:
        if not isinstance(worker, dict):
            raise AttentionBackendRemediationReviewError("worker diagnostic record is invalid")
        stdout = worker.get("stdout")
        stderr = worker.get("stderr")
        if not isinstance(stdout, dict) or not isinstance(stderr, dict):
            raise AttentionBackendRemediationReviewError("worker diagnostic streams are invalid")
        aggregate.append(str(stdout.get("text", "")) + "\n" + str(stderr.get("text", "")))
        if (
            worker.get("process_returncode") != 1
            or worker.get("ready") is not False
            or worker.get("hidden_retry_count") != 0
            or worker.get("replacement_count") != 0
        ):
            raise AttentionBackendRemediationReviewError("worker terminal state drifted")

    aggregate_text = "\n".join(aggregate)
    required = (
        "Using FLASHINFER attention backend",
        "Loading safetensors checkpoint shards: 100% Completed",
        "/usr/bin/ld: cannot find -lcuda: No such file or directory",
        "Ninja build failed",
        "Engine core initialization failed",
    )
    if any(marker not in aggregate_text for marker in required):
        raise AttentionBackendRemediationReviewError("failure root-cause markers drifted")

    checks = (
        launcher_failure.get("status") == "FAILED",
        launcher_failure.get("stage") == "reviewed_core_execution",
        launcher_failure.get("worker_startup_diagnostic_included") is True,
        launcher_failure.get("benchmark_trajectory_requests_permitted") == 0,
        diagnostic.get("model_requests_performed") == 0,
        diagnostic.get("benchmark_trajectory_requests_performed") == 0,
        diagnostic.get("hidden_retries_performed") == 0,
        diagnostic.get("workers_replaced") == 0,
    )
    if not all(checks):
        raise AttentionBackendRemediationReviewError("failure evidence conclusion drifted")


def _require_review_only_boundary(repo_root: Path) -> None:
    payload = json.loads((repo_root / WORKER_PLAN_PATH).read_text(encoding="utf-8"))
    workers = payload.get("workers") if isinstance(payload, dict) else None
    if not isinstance(workers, list) or len(workers) != 2:
        raise AttentionBackendRemediationReviewError("current worker plan is invalid")
    for worker in workers:
        argv = worker.get("command_argv") if isinstance(worker, dict) else None
        if not isinstance(argv, list):
            raise AttentionBackendRemediationReviewError("current worker command is invalid")
        if "--attention-backend" in argv:
            raise AttentionBackendRemediationReviewError(
                "runtime remediation was mixed into the review tranche"
            )


def validate_repository_package(
    repo_root: str | Path,
) -> dict[str, object]:
    """Validate evidence and prove implementation remains deferred."""

    root = Path(repo_root).resolve()
    _require_base_ancestor(root)
    _require_authorization_absent(root)
    record = _load_record(root / RECORD_PATH)
    _require_evidence(root, record)
    _require_failure_evidence(root)
    _require_review_only_boundary(root)
    return {
        "status": "T4_ATTENTION_BACKEND_REMEDIATION_REVIEW_VALID",
        "record_id": record.record_id,
        "decision": record.decision,
        "repository_base_commit": record.repository_base_commit,
        "root_cause": record.failure.root_cause,
        "selected_backend": record.implementation_boundary.selected_backend,
        "evidence_count": len(record.evidence),
        "runtime_source_changed": record.safety.runtime_source_changed,
        "authorization_issued": record.safety.authorization_issued,
        "model_requests_performed": record.safety.model_requests_performed,
        "rerun_permitted": False,
        "next_gate": record.next_gate,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        summary = validate_repository_package(arguments.repo_root)
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0
    except AttentionBackendRemediationReviewError as error:
        print(
            json.dumps(
                {
                    "error_code": ("ATTENTION_BACKEND_REMEDIATION_REVIEW_INVALID"),
                    "safe_message": str(error),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
