"""Validate the CUDA 12.9 worker-startup observability review boundary."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, model_validator

from auragateway.local_abc.contracts import LocalABCContract

BASE_COMMIT: Final = "d4558d44d57237fb2559f3cd6ddccfd22a31e07a"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_worker_startup_observability_review_v1.json"
)
EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/cu129-environment-qualification-attempt-5"
)
RUNTIME_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
LAUNCHER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
LAUNCHER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
IMPLEMENTATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_worker_startup_observability_implementation_v1.json"
)
DIAGNOSTICS_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_worker_startup_diagnostics.py"
)
HARNESS_TOOLCHAIN_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "worker_observability_harness_toolchain.py"
)
ADR_PATH: Final = Path("docs/adr/2026-07-22-local-abc-cu129-worker-startup-observability.md")
REPORT_PATH: Final = Path("docs/reports/AuraGateway_CU129_Worker_Startup_Failure_Review.md")

EXPECTED_REVIEW_SHA256: Final = "8d12f995bb05266a7480e3cb31580bab97aeaf860506a1af06d8c75410c0a3fc"
EXPECTED_ADR_SHA256: Final = "3cef63abe21b6d43c50b0425209cfa5481a2d8e76eaa676d89296cbdcf4baf78"
EXPECTED_REPORT_SHA256: Final = "0d119348a037657faf6745c4e4a28fa8ce29b4eb5a927608759c02b40e86bf5a"
EXPECTED_IDENTITY_SHA256: Final = "f415912c0bd97c24087540c85296d4856ad155e4eca91f523ab22c0caf14274e"
EXPECTED_EVIDENCE_MANIFEST_SHA256: Final = (
    "a72ecfe2a4b0448443c35871c68cd53f061eef57899098493bfe89d388336c3d"
)
EXPECTED_RUNTIME_ADAPTER_SHA256: Final = (
    "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
)
EXPECTED_LAUNCHER_SHA256: Final = "7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16"
EXPECTED_LAUNCHER_NOTEBOOK_SHA256: Final = (
    "7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9"
)
EXPECTED_SOURCE_ARTIFACT_SHA256: Final = (
    "7f926ef354678f2dcdd7bcc81854597aadfa3a1a125db4fd0dc2cd388948e92a"
)
EXPECTED_EXECUTION_LOG_SHA256: Final = (
    "f7d921aa13d4334d54a3d6313eca7934abc1235dfad8e3f4378dcc4c6de71d82"
)
EXPECTED_FAILURE_JSON_SHA256: Final = (
    "eb51ecfafac3c504f834fb76889cf435be253a4824a276f050b128f4fb41f91a"
)
EXPECTED_FAILURE_TRACE_SHA256: Final = (
    "0aff3131e04f669c8f2971c1498533bf15336b5847d09f55f3e2a3b1cbcdbc68"
)


class SourceEvidence(LocalABCContract):
    """Exact immutable Attempt 5 evidence identities."""

    evidence_directory: Literal[
        "evidence_vault/local_abc/cu129-environment-qualification-attempt-5"
    ]
    evidence_zip_sha256: Literal["7f926ef354678f2dcdd7bcc81854597aadfa3a1a125db4fd0dc2cd388948e92a"]
    execution_log_sha256: Literal[
        "f7d921aa13d4334d54a3d6313eca7934abc1235dfad8e3f4378dcc4c6de71d82"
    ]
    failure_record_sha256: Literal[
        "eb51ecfafac3c504f834fb76889cf435be253a4824a276f050b128f4fb41f91a"
    ]
    failure_trace_sha256: Literal[
        "0aff3131e04f669c8f2971c1498533bf15336b5847d09f55f3e2a3b1cbcdbc68"
    ]
    captured_version: Literal[1]


class ReportedResult(LocalABCContract):
    """Original terminal result without root-cause reinterpretation."""

    status: Literal["FAILED"]
    stage: Literal["reviewed_core_execution"]
    exception_type: Literal["RuntimeError"]
    safe_message: Literal["worker failed bounded readiness polling"]
    runtime_evidence_found: tuple[str, ...]
    ports_open_after_cleanup: tuple[int, ...]

    @model_validator(mode="after")
    def validate_empty_post_failure_sets(self) -> Self:
        if self.runtime_evidence_found or self.ports_open_after_cleanup:
            raise ValueError("reported post-failure evidence sets drifted")
        return self


class EvidenceBackedAssessment(LocalABCContract):
    """Claims supported by Attempt 5 and no stronger."""

    environment_qualification_status: Literal["FAILED"]
    first_divergence: Literal["worker_startup_readiness"]
    root_cause_status: Literal["UNRESOLVED"]
    failure_class: Literal["WORKER_STARTUP_FAILURE_OPAQUE_PROCESS_OUTPUT"]
    observability_gap: Literal["WORKER_STDOUT_STDERR_EXIT_STATE_AND_READINESS_HISTORY_DISCARDED"]
    worker_processes_attempted: Literal[2]
    healthy_workers_proven: Literal[0]
    model_inventory_validation_reached: Literal[False]
    qualification_probes_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    unchanged_rerun_justified: Literal[False]


class CurrentHarnessDefect(LocalABCContract):
    """Exact current source behavior that made the failure opaque."""

    runtime_adapter_sha256: Literal[
        "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
    ]
    launcher_source_sha256: Literal[
        "7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16"
    ]
    worker_stdout_sink: Literal["subprocess.DEVNULL"]
    worker_stderr_sink: Literal["subprocess.DEVNULL"]
    generic_terminal_error: Literal["worker failed bounded readiness polling"]
    worker_exit_state_retained: Literal[False]
    per_worker_readiness_history_retained: Literal[False]
    failure_bundle_embeds_runtime_diagnostics: Literal[False]


class AuthorityImpact(LocalABCContract):
    """Required identity propagation after the implementation changes executable code."""

    runtime_adapter_change_required: Literal[True]
    launcher_change_required: Literal[True]
    generated_launcher_regeneration_required: Literal[True]
    new_post_merge_harness_source_required: Literal[True]
    metadata_only_harness_inspection_required: Literal[True]
    active_manifest_migration_required: Literal[True]
    fresh_authorization_required_before_retry: Literal[True]
    historical_attempt_5_remains_immutable: Literal[True]


class ReviewSafety(LocalABCContract):
    """Hard stop after the review."""

    gpu_session_active: Literal[False]
    authorization_reuse_permitted: Literal[False]
    kaggle_retry_permitted: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]
    measured_execution_authorized: Literal[False]


class WorkerStartupObservabilityReview(LocalABCContract):
    """Decision contract for the next bounded implementation slice."""

    schema_version: Literal["1.0.0"]
    review_id: Literal["auragateway-cu129-worker-startup-observability-review-v1"]
    repository_base_commit: Literal["d4558d44d57237fb2559f3cd6ddccfd22a31e07a"]
    source_evidence: SourceEvidence
    reported_result: ReportedResult
    evidence_backed_assessment: EvidenceBackedAssessment
    current_harness_defect: CurrentHarnessDefect
    authority_impact: AuthorityImpact
    required_implementation: tuple[str, ...] = Field(min_length=12)
    required_negative_regressions: tuple[str, ...] = Field(min_length=12)
    decision: Literal["APPROVED_FOR_WORKER_STARTUP_OBSERVABILITY_IMPLEMENTATION"]
    next_gate: Literal["implement_worker_startup_observability_and_post_merge_harness_toolchain"]
    rerun_decision: Literal["UNCHANGED_RERUN_NOT_JUSTIFIED"]
    safety: ReviewSafety
    non_claims: tuple[str, ...] = Field(min_length=9)

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        implementation = "\n".join(self.required_implementation)
        regressions = "\n".join(self.required_negative_regressions)
        required_implementation = (
            "bounded per-worker stdout and stderr",
            "process exit state",
            "readiness poll count",
            "typed worker-startup diagnostic artifact",
            "launcher failure bundle",
            "zero hidden retries",
            "post-merge harness materialization lineage",
            "metadata-only input inspection",
            "new short-lived authorization",
        )
        if any(fragment not in implementation for fragment in required_implementation):
            raise ValueError("required observability implementation scope drifted")
        required_regressions = (
            "unbounded worker stdout",
            "raw environment serialization",
            "worker identity",
            "hidden worker restart",
            "Attempt 5 evidence",
            "426f57d harness",
            "stale launcher notebook",
            "authorization",
        )
        if any(fragment not in regressions for fragment in required_regressions):
            raise ValueError("required observability regressions drifted")
        return self


class SupersedingImplementationState(LocalABCContract):
    """Validated implementation that supersedes the reviewed live defect."""

    implementation_id: Literal["auragateway-cu129-worker-startup-observability-implementation-v1"]
    runtime_adapter_sha256: str
    launcher_source_sha256: str
    launcher_notebook_sha256: str
    next_gate: Literal["merge_then_build_post_merge_worker_observability_harness_source_package"]


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.as_posix()} must contain one JSON object")
    return cast(dict[str, object], payload)


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
            BASE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError("Attempt 5 base commit is not an ancestor of HEAD")


def _validate_evidence(repo_root: Path) -> dict[str, object]:
    directory = repo_root / EVIDENCE_DIRECTORY
    manifest_path = directory / "evidence_sha256.json"
    if _sha256(manifest_path) != EXPECTED_EVIDENCE_MANIFEST_SHA256:
        raise RuntimeError("Attempt 5 evidence manifest identity drifted")
    manifest = _load_json(manifest_path)
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 4:
        raise RuntimeError("Attempt 5 evidence manifest topology drifted")
    expected_names = {
        "launcher_failure.json",
        "launcher_failure_trace.txt",
        "execution.log",
        "source_evidence_identity.json",
    }
    observed_names: set[str] = set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise RuntimeError("Attempt 5 evidence manifest entry is invalid")
        entry = cast(dict[str, object], raw_entry)
        relative = entry.get("path")
        if not isinstance(relative, str) or relative not in expected_names:
            raise RuntimeError("Attempt 5 evidence path is invalid")
        path = directory / relative
        if (
            not path.is_file()
            or path.stat().st_size != entry.get("size_bytes")
            or _sha256(path) != entry.get("sha256")
        ):
            raise RuntimeError(f"Attempt 5 evidence identity drifted: {relative}")
        observed_names.add(relative)
    if observed_names != expected_names:
        raise RuntimeError("Attempt 5 evidence member set drifted")

    if _sha256(directory / "source_evidence_identity.json") != EXPECTED_IDENTITY_SHA256:
        raise RuntimeError("Attempt 5 source identity drifted")
    identity = _load_json(directory / "source_evidence_identity.json")
    expected_identity = {
        "source_artifact_sha256": EXPECTED_SOURCE_ARTIFACT_SHA256,
        "execution_log_sha256": EXPECTED_EXECUTION_LOG_SHA256,
        "qualification_status": "FAILED",
        "first_divergence": "worker_startup_readiness",
        "rerun_permitted": False,
        "provider_calls_performed": False,
        "benchmark_trajectory_requests_performed": 0,
    }
    drift = sorted(key for key, value in expected_identity.items() if identity.get(key) != value)
    if drift:
        raise RuntimeError("Attempt 5 source identity drifted: " + ", ".join(drift))

    failure = _load_json(directory / "launcher_failure.json")
    if (
        failure.get("status") != "FAILED"
        or failure.get("stage") != "reviewed_core_execution"
        or failure.get("exception_type") != "RuntimeError"
        or failure.get("safe_message") != "worker failed bounded readiness polling"
        or failure.get("runtime_evidence_found") != []
        or failure.get("ports_open") != []
        or failure.get("provider_calls_performed") is not False
    ):
        raise RuntimeError("Attempt 5 launcher failure record drifted")

    trace = (directory / "launcher_failure_trace.txt").read_text(encoding="utf-8")
    required_trace = (
        "execute_qualification",
        "adapter.capture",
        "self._wait_for_workers(plans)",
        'RuntimeError("worker failed bounded readiness polling")',
    )
    if any(fragment not in trace for fragment in required_trace):
        raise RuntimeError("Attempt 5 failure trace drifted")

    log = (directory / "execution.log").read_text(encoding="utf-8")
    required_log = (
        "qualification_status=FAILED",
        "sha256=7f926ef354678f2dcdd7bcc81854597aadfa3a1a125db4fd0dc2cd388948e92a",
        "worker failed bounded readiness polling",
        "upload_only_this_file=true",
    )
    if any(fragment not in log for fragment in required_log):
        raise RuntimeError("Attempt 5 execution log drifted")

    return {
        "evidence_files_verified": len(entries),
        "reported_status": failure["status"],
        "reported_stage": failure["stage"],
        "root_cause_status": "UNRESOLVED",
    }


def load_superseding_implementation_state(
    repo_root: Path,
) -> SupersedingImplementationState | None:
    """Validate a current implementation without reclassifying Attempt 5 evidence."""

    implementation_path = repo_root / IMPLEMENTATION_PATH
    if not implementation_path.exists():
        return None

    payload = _load_json(implementation_path)
    observed = implementation_path.read_text(encoding="utf-8")
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if observed != canonical:
        raise RuntimeError("worker-observability implementation record is not canonical")

    required_top_level = {
        "implementation_id": ("auragateway-cu129-worker-startup-observability-implementation-v1"),
        "review_id": "auragateway-cu129-worker-startup-observability-review-v1",
        "decision": "IMPLEMENTED_AWAITING_POST_MERGE_HARNESS_SOURCE_PACKAGE",
        "next_gate": ("merge_then_build_post_merge_worker_observability_harness_source_package"),
    }
    if any(payload.get(key) != value for key, value in required_top_level.items()):
        raise RuntimeError("worker-observability implementation identity drifted")

    artifacts_raw = payload.get("implemented_artifacts")
    if not isinstance(artifacts_raw, list):
        raise RuntimeError("worker-observability implementation artifacts are invalid")

    artifacts: list[dict[str, object]] = []
    for item in artifacts_raw:
        if not isinstance(item, dict):
            raise RuntimeError("worker-observability implementation artifact is invalid")
        artifacts.append(cast(dict[str, object], item))

    expected_roles = (
        "diagnostics",
        "runtime_adapter",
        "launcher_source",
        "launcher_notebook",
        "post_merge_harness_toolchain",
    )
    if tuple(item.get("role") for item in artifacts) != expected_roles:
        raise RuntimeError("worker-observability implementation artifact order drifted")

    expected_paths = {
        "diagnostics": DIAGNOSTICS_PATH,
        "runtime_adapter": RUNTIME_ADAPTER_PATH,
        "launcher_source": LAUNCHER_PATH,
        "launcher_notebook": LAUNCHER_NOTEBOOK_PATH,
        "post_merge_harness_toolchain": HARNESS_TOOLCHAIN_PATH,
    }
    artifacts_by_role = {cast(str, item["role"]): item for item in artifacts}
    observed_sha256: dict[str, str] = {}
    for role, relative_path in expected_paths.items():
        artifact = artifacts_by_role[role]
        digest = artifact.get("sha256")
        if artifact.get("path") != relative_path.as_posix():
            raise RuntimeError(f"worker-observability artifact path drifted: {role}")
        if not isinstance(digest, str):
            raise RuntimeError(f"worker-observability artifact digest is invalid: {role}")
        artifact_path = repo_root / relative_path
        if not artifact_path.is_file() or _sha256(artifact_path) != digest:
            raise RuntimeError(f"worker-observability artifact identity drifted: {role}")
        observed_sha256[role] = digest

    historical = payload.get("historical_active_authority")
    if not isinstance(historical, dict):
        raise RuntimeError("historical active authority is invalid")
    historical_record = cast(dict[str, object], historical)
    expected_historical = {
        "runtime_adapter_sha256": EXPECTED_RUNTIME_ADAPTER_SHA256,
        "launcher_source_sha256": EXPECTED_LAUNCHER_SHA256,
        "launcher_notebook_sha256": EXPECTED_LAUNCHER_NOTEBOOK_SHA256,
    }
    if any(historical_record.get(key) != value for key, value in expected_historical.items()):
        raise RuntimeError("historical reviewed source identities drifted")

    transition = payload.get("authority_transition")
    if not isinstance(transition, dict):
        raise RuntimeError("worker-observability authority transition is invalid")
    transition_record = cast(dict[str, object], transition)
    required_transition = {
        "active_manifest_promoted": False,
        "historical_harness_reused_as_remediated_lineage": False,
        "existing_authorization_issuer_usable": False,
        "post_merge_harness_source_package_required": True,
    }
    if any(transition_record.get(key) != value for key, value in required_transition.items()):
        raise RuntimeError("worker-observability authority transition drifted")

    safety = payload.get("safety")
    if not isinstance(safety, dict):
        raise RuntimeError("worker-observability safety envelope is invalid")
    safety_record = cast(dict[str, object], safety)
    required_safety = {
        "authorization_issued": False,
        "kaggle_execution_performed": False,
        "gpu_execution_performed": False,
        "model_loaded": False,
        "worker_started": False,
        "model_requests_performed": 0,
    }
    if any(safety_record.get(key) != value for key, value in required_safety.items()):
        raise RuntimeError("worker-observability implementation crossed a safety boundary")

    return SupersedingImplementationState(
        implementation_id=cast(str, payload["implementation_id"]),
        runtime_adapter_sha256=observed_sha256["runtime_adapter"],
        launcher_source_sha256=observed_sha256["launcher_source"],
        launcher_notebook_sha256=observed_sha256["launcher_notebook"],
        next_gate=cast(str, payload["next_gate"]),
    )


def _validate_current_defect(repo_root: Path) -> bool:
    adapter_path = repo_root / RUNTIME_ADAPTER_PATH
    launcher_path = repo_root / LAUNCHER_PATH
    notebook_path = repo_root / LAUNCHER_NOTEBOOK_PATH
    historical_identities = (
        _sha256(adapter_path) == EXPECTED_RUNTIME_ADAPTER_SHA256,
        _sha256(launcher_path) == EXPECTED_LAUNCHER_SHA256,
        _sha256(notebook_path) == EXPECTED_LAUNCHER_NOTEBOOK_SHA256,
    )
    if not all(historical_identities):
        implementation = load_superseding_implementation_state(repo_root)
        if implementation is None:
            raise RuntimeError(
                "current worker-startup sources drifted without a valid implementation"
            )
        return True

    adapter = adapter_path.read_text(encoding="utf-8")
    required_adapter = (
        "stdout=subprocess.DEVNULL",
        "stderr=subprocess.DEVNULL",
        'raise RuntimeError("worker failed bounded readiness polling")',
        "def _wait_for_workers",
    )
    if any(fragment not in adapter for fragment in required_adapter):
        raise RuntimeError("current worker-startup observability defect drifted")

    launcher = launcher_path.read_text(encoding="utf-8")
    required_launcher = (
        "def write_failure_bundle",
        '"launcher_failure.json"',
        '"launcher_failure_trace.txt"',
        '"runtime_evidence_found": sorted(evidence_found)',
    )
    if any(fragment not in launcher for fragment in required_launcher):
        raise RuntimeError("current launcher failure boundary drifted")
    prohibited = (
        "worker_startup_diagnostic.json",
        "worker_startup_diagnostics.json",
    )
    if any(fragment in launcher for fragment in prohibited):
        raise RuntimeError("worker-startup diagnostics already exist in the current launcher")

    source = inspect.getsource(_validate_current_defect)
    if "subprocess.DEVNULL" not in source:
        raise RuntimeError("review validator no longer binds the discarded-output defect")
    return False


def _validate_documentation(repo_root: Path) -> None:
    expected = {
        REVIEW_PATH: EXPECTED_REVIEW_SHA256,
        ADR_PATH: EXPECTED_ADR_SHA256,
        REPORT_PATH: EXPECTED_REPORT_SHA256,
    }
    for path, expected_sha256 in expected.items():
        if _sha256(repo_root / path) != expected_sha256:
            raise RuntimeError(f"review artifact identity drifted: {path.as_posix()}")


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    """Validate immutable failure evidence and the approved remediation boundary."""

    root = Path(repo_root).resolve()
    _require_base_ancestor(root)
    if _sha256(root / REVIEW_PATH) != EXPECTED_REVIEW_SHA256:
        raise RuntimeError("worker-startup observability review identity drifted")
    review = WorkerStartupObservabilityReview.model_validate(_load_json(root / REVIEW_PATH))
    evidence = _validate_evidence(root)
    implementation_present = _validate_current_defect(root)
    _validate_documentation(root)
    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise RuntimeError("consumed transient authorization must be absent from the review tree")

    return {
        "review_id": review.review_id,
        "decision": review.decision,
        "reported_status": evidence["reported_status"],
        "first_divergence": review.evidence_backed_assessment.first_divergence,
        "root_cause_status": evidence["root_cause_status"],
        "failure_class": review.evidence_backed_assessment.failure_class,
        "evidence_files_verified": evidence["evidence_files_verified"],
        "unchanged_rerun_permitted": False,
        "authorization_reuse_permitted": False,
        "model_requests_performed": 0,
        "observability_implementation_present": implementation_present,
        "next_gate": review.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-worker-startup-observability-review")
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = validate_repository_package(args.repo_root)
    for key, value in result.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
