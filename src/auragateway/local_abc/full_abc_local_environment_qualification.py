"""Generate and verify static full-run environment-qualification assets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, Never, TypeVar, cast

from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_environment_qualification_contracts import (
    _REQUIRED_METRIC_SEMANTICS,
    _REQUIRED_RESET_STEPS,
    _REQUIRED_RUNTIME_LOCK_FIELDS,
    _REQUIRED_STOP_CONDITIONS,
    _RUNTIME_EVIDENCE_PATHS,
    IMPLEMENTATION_PLAN_PATH,
    NEXT_GATE,
    QUALIFICATION_REQUEST_PATH,
    REVIEW_GIT_BLOB_SHA,
    REVIEW_PATH,
    REVIEW_SOURCE_GIT_BLOB_SHA,
    REVIEW_SOURCE_PATH,
    SOURCE_MAIN_MERGE_COMMIT,
    WORKER_STARTUP_PLAN_PATH,
    EnvironmentBinding,
    EnvironmentQualificationImplementationPlan,
    EnvironmentQualificationStaticBundle,
    FullABCLocalEnvironmentQualificationErrorEnvelope,
    FullABCLocalEnvironmentQualificationImplementationError,
    MetricRequirement,
    QualificationRequest,
    QualificationSafetyEnvelope,
    RuntimeEvidenceRequirement,
    StaticQualificationStatus,
    WorkerStartupCommand,
    WorkerStartupPlan,
    canonical_command_sha256,
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

_METRIC_UNITS = {
    "cached_prefix_tokens": ("tokens", "runtime_metric"),
    "metric_availability_state": ("state", "runtime_metadata"),
    "newly_computed_prefill_tokens": ("tokens", "runtime_metric"),
    "prefill_duration_ms": ("milliseconds", "runtime_metric"),
    "prompt_tokens": ("tokens", "runtime_metric"),
    "realized_route": ("route", "runtime_metadata"),
    "request_latency_ms": ("milliseconds", "runtime_metric"),
    "reset_state": ("state", "runtime_metadata"),
    "time_to_first_token_ms": ("milliseconds", "runtime_metric"),
    "worker_id": ("worker", "runtime_metadata"),
}


ModelT = TypeVar("ModelT", QualificationRequest, WorkerStartupPlan)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "INVALID_COMMAND_ARGUMENTS",
            "environment-qualification command arguments are invalid",
            details=(message,),
        )


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REQUIRED_ASSET_NOT_FOUND",
            "a required environment-qualification asset was not found",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REQUIRED_ASSET_INVALID_JSON",
            "a required environment-qualification asset is not valid JSON",
            path.as_posix(),
        ) from exc
    if not isinstance(payload, dict):
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REQUIRED_ASSET_INVALID_ROOT",
            "a required environment-qualification asset must be one JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _write_canonical(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")


def _git_index_blob_sha(repo_root: Path, relative_path: Path) -> str:
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
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REQUIRED_GIT_AUTHORITY_UNREADABLE",
            "required environment-qualification Git authority could not be resolved",
            relative_path.as_posix(),
        ) from exc
    identity = result.stdout.strip()
    if len(identity) != 40 or any(character not in "0123456789abcdef" for character in identity):
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REQUIRED_GIT_AUTHORITY_INVALID",
            "required environment-qualification Git authority returned an invalid identity",
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
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "SOURCE_MAIN_ANCESTRY_UNREADABLE",
            "source main ancestry could not be evaluated",
        ) from exc
    if result.returncode != 0:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "SOURCE_MAIN_MERGE_MISSING",
            "PR 101 merge must be an ancestor of the current HEAD",
            details=(SOURCE_MAIN_MERGE_COMMIT,),
        )


def _require_dict(mapping: dict[str, object], field: str, path: Path) -> dict[str, object]:
    value = mapping.get(field)
    if not isinstance(value, dict):
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_FIELD_INVALID",
            "the environment-qualification review contains an invalid object field",
            path.as_posix(),
            (field,),
        )
    return cast(dict[str, object], value)


def _validate_review_boundary(review: dict[str, object], path: Path) -> None:
    expected_scalars = {
        "review_id": ("auragateway-full-abc-local-full-run-environment-qualification-review-v1"),
        "source_main_merge_commit": "1bbc11e72880bc5b6fa88da3ba8b180420c9abf5",
        "decision": "APPROVED_FOR_QUALIFICATION_TOOLING_IMPLEMENTATION",
        "next_gate": "full_abc_local_full_run_environment_qualification_implementation",
    }
    drift = tuple(
        sorted(
            field for field, expected in expected_scalars.items() if review.get(field) != expected
        )
    )
    if drift:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_BOUNDARY_DRIFT",
            "the environment-qualification review no longer authorizes this implementation",
            path.as_posix(),
            drift,
        )

    safety = _require_dict(review, "safety", path)
    required_false = (
        "gpu_execution_authorized",
        "gpu_execution_performed",
        "worker_start_authorized",
        "worker_started",
        "model_execution_performed",
        "credential_accessed",
        "provider_call_performed",
        "customer_data_used",
        "measured_execution_authorized",
        "claim_generation_permitted",
    )
    if any(safety.get(field) is not False for field in required_false):
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_SAFETY_BOUNDARY_INVALID",
            "the review safety boundary no longer fails closed",
            path.as_posix(),
        )
    if safety.get("external_spend") != 0:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_EXTERNAL_SPEND_INVALID",
            "the review no longer preserves zero external spend",
            path.as_posix(),
        )

    runtime = _require_dict(review, "runtime_identity", path)
    runtime_checks = {
        "status": "HISTORICAL_BASELINE_REQUIRES_FRESH_CAPTURE",
        "environment": "kaggle_t4_x2",
        "execution_backend": "local_vllm",
        "gpu_count": 2,
        "gpu_model": "Tesla T4",
        "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "tokenizer_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "fresh_values_must_share_one_runtime_session": True,
        "inherited_versions_permitted": False,
    }
    if any(runtime.get(field) != expected for field, expected in runtime_checks.items()):
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_RUNTIME_IDENTITY_INVALID",
            "the review runtime identity no longer supports fresh qualification",
            path.as_posix(),
        )

    metric_capability = _require_dict(review, "metric_capability", path)
    if metric_capability.get("missing_metric_state") != "UNAVAILABLE_NOT_ZERO":
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_METRIC_SEMANTICS_INVALID",
            "the review no longer preserves explicit missing metric semantics",
            path.as_posix(),
        )
    if metric_capability.get("zero_fill_for_missing_metrics_permitted") is not False:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "REVIEW_METRIC_ZERO_FILL_INVALID",
            "the review no longer prohibits zero-filled missing metrics",
            path.as_posix(),
        )


def _worker_command_argv(port: int) -> tuple[str, ...]:
    return (
        "python",
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--revision",
        "7ae557604adf67be50417f59c2c2f167def9a775",
        "--tokenizer",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--tokenizer-revision",
        "7ae557604adf67be50417f59c2c2f167def9a775",
        "--served-model-name",
        "local-qwen2.5-0.5b-instruct",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--dtype",
        "auto",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.85",
        "--max-num-seqs",
        "8",
        "--enable-prefix-caching",
        "--disable-log-requests",
    )


def _build_worker(worker_id: str, gpu_index: int, port: int) -> WorkerStartupCommand:
    environment = (
        EnvironmentBinding(name="CUDA_VISIBLE_DEVICES", value=str(gpu_index)),
        EnvironmentBinding(name="HF_HUB_OFFLINE", value="1"),
    )
    command_argv = _worker_command_argv(port)
    return WorkerStartupCommand(
        worker_id=cast(Literal["worker_1", "worker_2"], worker_id),
        gpu_index=cast(Literal[0, 1], gpu_index),
        port=cast(Literal[8001, 8002], port),
        environment=environment,
        command_argv=command_argv,
        command_sha256=canonical_command_sha256(command_argv, environment),
    )


def build_worker_startup_plan() -> WorkerStartupPlan:
    """Build the deterministic two-worker startup plan without launching it."""

    return WorkerStartupPlan(
        plan_id="auragateway-full-abc-worker-startup-plan-v1",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        source_review_path=REVIEW_PATH.as_posix(),
        source_review_git_blob_sha=REVIEW_GIT_BLOB_SHA,
        status=StaticQualificationStatus.STATIC_PLAN_NOT_EXECUTED,
        runtime_entrypoint="vllm.entrypoints.openai.api_server",
        model_repository="Qwen/Qwen2.5-0.5B-Instruct",
        model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        tokenizer_revision="7ae557604adf67be50417f59c2c2f167def9a775",
        workers=(
            _build_worker("worker_1", 0, 8001),
            _build_worker("worker_2", 1, 8002),
        ),
        required_prelaunch_checks=(
            "credential_absence_verified",
            "customer_data_absence_verified",
            "gpu_topology_matches_plan",
            "model_and_tokenizer_identity_available",
            "ports_8001_and_8002_closed",
            "runtime_dependency_lock_captured",
            "vllm_wheel_sha256_captured",
        ),
        next_gate=NEXT_GATE,
    )


def _runtime_evidence_requirements() -> tuple[RuntimeEvidenceRequirement, ...]:
    return tuple(
        RuntimeEvidenceRequirement(
            artifact_id=artifact_id,
            path=path.as_posix(),
        )
        for artifact_id, path in zip(
            _RUNTIME_EVIDENCE_IDS,
            _RUNTIME_EVIDENCE_PATHS,
            strict=True,
        )
    )


def _metric_requirements() -> tuple[MetricRequirement, ...]:
    requirements: list[MetricRequirement] = []
    for semantic in _REQUIRED_METRIC_SEMANTICS:
        unit, source_kind = _METRIC_UNITS[semantic]
        requirements.append(
            MetricRequirement(
                semantic=semantic,
                expected_unit=unit,
                source_kind=cast(Literal["runtime_metric", "runtime_metadata"], source_kind),
            )
        )
    return tuple(requirements)


def build_qualification_request() -> QualificationRequest:
    """Build the static request for a later authorized qualification session."""

    return QualificationRequest(
        request_id="auragateway-full-abc-environment-qualification-request-v1",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        source_review_path=REVIEW_PATH.as_posix(),
        source_review_git_blob_sha=REVIEW_GIT_BLOB_SHA,
        status=StaticQualificationStatus.STATIC_ASSETS_GENERATED_EXECUTION_BLOCKED,
        target_environment="kaggle_t4_x2",
        execution_backend="local_vllm",
        required_runtime_lock_fields=_REQUIRED_RUNTIME_LOCK_FIELDS,
        runtime_evidence_requirements=_runtime_evidence_requirements(),
        metric_requirements=_metric_requirements(),
        required_reset_steps=_REQUIRED_RESET_STEPS,
        stop_conditions=_REQUIRED_STOP_CONDITIONS,
        worker_startup_plan_path=WORKER_STARTUP_PLAN_PATH.as_posix(),
        safety=QualificationSafetyEnvelope(),
        next_gate=NEXT_GATE,
    )


def build_static_bundle() -> EnvironmentQualificationStaticBundle:
    """Build both implementation-stage assets without runtime activity."""

    return EnvironmentQualificationStaticBundle(
        qualification_request=build_qualification_request(),
        worker_startup_plan=build_worker_startup_plan(),
    )


def build_implementation_plan() -> EnvironmentQualificationImplementationPlan:
    """Build the canonical implementation decision for repository review."""

    return EnvironmentQualificationImplementationPlan(
        implementation_id=(
            "auragateway-full-abc-local-environment-qualification-implementation-v1"
        ),
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        review_path=REVIEW_PATH.as_posix(),
        review_git_blob_sha=REVIEW_GIT_BLOB_SHA,
        review_source_git_blob_sha=REVIEW_SOURCE_GIT_BLOB_SHA,
        generated_static_assets=(
            QUALIFICATION_REQUEST_PATH.as_posix(),
            WORKER_STARTUP_PLAN_PATH.as_posix(),
        ),
        deferred_runtime_evidence=tuple(path.as_posix() for path in _RUNTIME_EVIDENCE_PATHS),
        next_gate=NEXT_GATE,
    )


def validate_repository_authorities(repo_root: Path) -> dict[str, object]:
    """Validate PR 101 review authorities before writing static assets."""

    _require_source_ancestor(repo_root)
    expected_blobs = {
        REVIEW_PATH: REVIEW_GIT_BLOB_SHA,
        REVIEW_SOURCE_PATH: REVIEW_SOURCE_GIT_BLOB_SHA,
    }
    drift = tuple(
        sorted(
            path.as_posix()
            for path, expected in expected_blobs.items()
            if _git_index_blob_sha(repo_root, path) != expected
        )
    )
    if drift:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "ENVIRONMENT_QUALIFICATION_AUTHORITY_DRIFT",
            "one or more qualification implementation authorities drifted",
            details=drift,
        )
    review = _load_json_object(repo_root / REVIEW_PATH)
    _validate_review_boundary(review, repo_root / REVIEW_PATH)
    return {
        "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
        "review_git_blob_sha": REVIEW_GIT_BLOB_SHA,
        "review_source_git_blob_sha": REVIEW_SOURCE_GIT_BLOB_SHA,
        "review_boundary_valid": True,
    }


def write_static_bundle(
    repo_root: Path,
    *,
    validate_repository: bool = True,
) -> EnvironmentQualificationStaticBundle:
    """Write only the two implementation-stage assets."""

    if validate_repository:
        validate_repository_authorities(repo_root)
    bundle = build_static_bundle()
    _write_canonical(
        repo_root / QUALIFICATION_REQUEST_PATH,
        bundle.qualification_request.canonical_json(),
    )
    _write_canonical(
        repo_root / WORKER_STARTUP_PLAN_PATH,
        bundle.worker_startup_plan.canonical_json(),
    )
    return bundle


def _load_model(path: Path, model_type: type[ModelT]) -> ModelT:
    payload = _load_json_object(path)
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "STATIC_ASSET_VALIDATION_FAILED",
            "a generated static qualification asset failed typed validation",
            path.as_posix(),
        ) from exc


def verify_static_bundle(
    repo_root: Path,
    *,
    validate_repository: bool = True,
) -> dict[str, object]:
    """Verify canonical static assets and prove runtime evidence is absent."""

    if validate_repository:
        validate_repository_authorities(repo_root)
    expected = build_static_bundle()
    request = _load_model(
        repo_root / QUALIFICATION_REQUEST_PATH,
        QualificationRequest,
    )
    startup = _load_model(
        repo_root / WORKER_STARTUP_PLAN_PATH,
        WorkerStartupPlan,
    )
    drift: list[str] = []
    if request.canonical_json() != expected.qualification_request.canonical_json():
        drift.append(QUALIFICATION_REQUEST_PATH.as_posix())
    if startup.canonical_json() != expected.worker_startup_plan.canonical_json():
        drift.append(WORKER_STARTUP_PLAN_PATH.as_posix())
    runtime_evidence_present = tuple(
        path.as_posix() for path in _RUNTIME_EVIDENCE_PATHS if (repo_root / path).exists()
    )
    if runtime_evidence_present:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "RUNTIME_EVIDENCE_GENERATED_TOO_EARLY",
            "runtime qualification evidence exists before its authorized gate",
            details=runtime_evidence_present,
        )
    if drift:
        raise FullABCLocalEnvironmentQualificationImplementationError(
            "STATIC_QUALIFICATION_ASSET_DRIFT",
            "one or more static qualification assets drifted",
            details=tuple(sorted(drift)),
        )

    implementation_plan_path = repo_root / IMPLEMENTATION_PLAN_PATH
    if implementation_plan_path.exists():
        plan_payload = _load_json_object(implementation_plan_path)
        try:
            plan = EnvironmentQualificationImplementationPlan.model_validate(plan_payload)
        except ValidationError as exc:
            raise FullABCLocalEnvironmentQualificationImplementationError(
                "IMPLEMENTATION_PLAN_INVALID",
                "the qualification implementation plan failed typed validation",
                implementation_plan_path.as_posix(),
            ) from exc
        if plan.canonical_json() != build_implementation_plan().canonical_json():
            raise FullABCLocalEnvironmentQualificationImplementationError(
                "IMPLEMENTATION_PLAN_DRIFT",
                "the qualification implementation plan drifted",
                implementation_plan_path.as_posix(),
            )

    return {
        "static_assets_generated": True,
        "static_asset_count": 2,
        "runtime_evidence_generated": False,
        "runtime_evidence_required_count": len(_RUNTIME_EVIDENCE_PATHS),
        "planned_trajectory_count": request.planned_trajectory_count,
        "worker_count": len(startup.workers),
        "launch_authorized": startup.launch_authorized,
        "gpu_execution_authorized": request.safety.gpu_execution_authorized,
        "measured_execution_authorized": request.safety.measured_execution_authorized,
        "external_spend": request.safety.external_spend,
        "next_gate": request.next_gate,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run deterministic static generation or verification."""

    try:
        args = _parser().parse_args(argv)
        repo_root = args.repo_root.resolve()
        if args.command == "generate":
            write_static_bundle(repo_root)
        summary = verify_static_bundle(repo_root)
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0
    except FullABCLocalEnvironmentQualificationImplementationError as exc:
        envelope = FullABCLocalEnvironmentQualificationErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.canonical_json(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
