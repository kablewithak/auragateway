"""Validate the bounded vLLM CLI contract-hardening implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.full_abc_local_environment_qualification_cu129_runtime import (
    VLLM_API_SERVER_REQUIRED_OPTIONS,
    VLLM_REQUEST_LOGGING_DISABLED_OPTION,
    canonical_command_sha256,
    worker_command_options,
    worker_command_template,
)

REPOSITORY_BASE_COMMIT: Final = "ab0ba1efdaa4d30957fb7e57e1424493ac7b1f09"
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_vllm_cli_contract_hardening_v1.json"
)
RECORD_SHA256: Final = "36dd5153867bbb6334733e7bb87ff0a6839ec93badf76360c30a393ffb83ccf6"
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_cu129_runtime.py"
)
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
DECISION: Final = "IMPLEMENTED_AWAITING_POST_MERGE_HARNESS_REMATERIALIZATION"
NEXT_GATE: Final = "merge_then_prepare_vllm_cli_hardened_harness_source_package"
REQUIRED_PRELAUNCH_CHECK: Final = "vllm_api_server_cli_capability_verified"
REJECTED_OPTION: Final = "--disable-log-requests"
EXPECTED_COMMAND_SHA256: Final = {
    "worker_1": "fe37b6f369b4d83b4aea467f3e4d06f32bd62a8b44b4568665255ec35552958f",
    "worker_2": "c28cea7cdfd6d5034a94ac34f090973949bbd401c5179493ddca44b17899fd06",
}


class VllmCliContractHardeningError(RuntimeError):
    """Fail-closed hardening validation error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise VllmCliContractHardeningError(message)


class EvidenceArtifact(LocalABCContract):
    """One immutable failed-attempt evidence artifact."""

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
    """Bounded runtime failure facts."""

    status: Literal["FAILED_CLOSED"]
    stage: Literal["initial_worker_startup"]
    failed_worker_id: Literal["worker_1"]
    worker_process_returncode: Literal[2]
    observed_error: Literal["unrecognized_argument"]
    rejected_option: Literal["--disable-log-requests"]
    pinned_vllm_version: Literal["0.19.1"]
    identity_mismatch: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]


class HardeningImplementation(LocalABCContract):
    """Implemented worker-command and preflight controls."""

    request_logging_disabled_option: Literal["--no-enable-log-requests"]
    pre_worker_cli_capability_gate: Literal[True]
    capability_source: Literal["pinned_vllm_api_server_help"]
    capability_failure_mode: Literal["fail_before_worker_spawn"]
    worker_command_identity_regenerated: Literal[True]
    hidden_flag_translation: Literal[False]


class AuthorityTransition(LocalABCContract):
    """Required authority migration before another qualification attempt."""

    active_harness_unchanged: Literal[True]
    active_harness_reusable_for_retry: Literal[False]
    consumed_authorization_reusable: Literal[False]
    fresh_issuer_usable: Literal[False]
    post_merge_harness_source_package_required: Literal[True]
    cpu_only_materialization_required: Literal[True]
    metadata_only_inspection_required: Literal[True]
    fresh_authorization_required_before_retry: Literal[True]


class CircuitBreaker(LocalABCContract):
    """Escalate rather than stack another per-flag patch."""

    trigger: Literal["another_cli_or_worker_command_contract_failure"]
    required_action: Literal["redesign_complete_worker_cli_capability_contract"]
    additional_per_flag_patch_permitted: Literal[False]


class HardeningSafety(LocalABCContract):
    """Prohibited actions remain absent in the implementation tranche."""

    authorization_issued: Literal[False]
    kaggle_execution_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]
    measured_execution_authorized: Literal[False]


class VllmCliContractHardeningRecord(LocalABCContract):
    """Canonical decision and evidence contract for the hardening tranche."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-cu129-vllm-cli-contract-hardening-v1"]
    repository_base_commit: Literal["ab0ba1efdaa4d30957fb7e57e1424493ac7b1f09"]
    decision: Literal["IMPLEMENTED_AWAITING_POST_MERGE_HARNESS_REMATERIALIZATION"]
    failure: FailureObservation
    implementation: HardeningImplementation
    evidence: tuple[EvidenceArtifact, ...] = Field(min_length=4, max_length=4)
    authority_transition: AuthorityTransition
    circuit_breaker: CircuitBreaker
    safety: HardeningSafety
    next_gate: Literal["merge_then_prepare_vllm_cli_hardened_harness_source_package"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_evidence_paths(self) -> Self:
        expected = (
            "evidence_vault/local_abc/cu129-vllm-cli-contract-failure-v1/"
            "ag-full-abc-env-qualification-v1.log",
            "evidence_vault/local_abc/cu129-vllm-cli-contract-failure-v1/"
            "ag-qualification-control-materializer-v1.log",
            "evidence_vault/local_abc/cu129-vllm-cli-contract-failure-v1/"
            "ag-qualification-evidence-v1.zip",
            "evidence_vault/local_abc/cu129-vllm-cli-contract-failure-v1/"
            "consumed_environment_qualification_authorization_v1.json",
        )
        if tuple(artifact.path for artifact in self.evidence) != expected:
            raise ValueError("hardening evidence path order or set drifted")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_record(path: Path) -> VllmCliContractHardeningRecord:
    try:
        observed = path.read_text(encoding="utf-8")
        record = VllmCliContractHardeningRecord.model_validate_json(observed)
    except OSError as exc:
        raise VllmCliContractHardeningError("hardening record is unreadable") from exc
    if observed != record.canonical_json():
        raise VllmCliContractHardeningError("hardening record is not canonical JSON")
    if _sha256(path) != RECORD_SHA256:
        raise VllmCliContractHardeningError("hardening record identity drifted")
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
        raise VllmCliContractHardeningError(
            "the failed-attempt repository base is not an ancestor of HEAD"
        )


def _require_evidence(repo_root: Path, record: VllmCliContractHardeningRecord) -> None:
    for artifact in record.evidence:
        path = repo_root / artifact.path
        if not path.is_file():
            raise VllmCliContractHardeningError(f"hardening evidence is missing: {artifact.path}")
        if path.stat().st_size != artifact.size_bytes or _sha256(path) != artifact.sha256:
            raise VllmCliContractHardeningError(
                f"hardening evidence identity drifted: {artifact.path}"
            )


def _load_worker_plan(path: Path) -> dict[str, object]:
    try:
        observed = path.read_text(encoding="utf-8")
        payload = json.loads(observed)
    except (OSError, json.JSONDecodeError) as exc:
        raise VllmCliContractHardeningError("worker startup plan is unreadable") from exc
    if not isinstance(payload, dict):
        raise VllmCliContractHardeningError("worker startup plan must contain one object")
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if observed != canonical:
        raise VllmCliContractHardeningError("worker startup plan is not canonical JSON")
    return cast(dict[str, object], payload)


def _require_worker_plan(repo_root: Path) -> None:
    payload = _load_worker_plan(repo_root / WORKER_PLAN_PATH)
    checks = payload.get("required_prelaunch_checks")
    if not isinstance(checks, list) or REQUIRED_PRELAUNCH_CHECK not in checks:
        raise VllmCliContractHardeningError("worker plan lacks the CLI capability gate")
    workers = payload.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise VllmCliContractHardeningError("worker plan must contain two workers")
    for expected_id, expected_port in (("worker_1", 8001), ("worker_2", 8002)):
        matching = [
            worker
            for worker in workers
            if isinstance(worker, dict) and worker.get("worker_id") == expected_id
        ]
        if len(matching) != 1:
            raise VllmCliContractHardeningError(f"worker plan identity drifted: {expected_id}")
        worker = cast(dict[str, object], matching[0])
        argv_raw = worker.get("command_argv")
        if not isinstance(argv_raw, list) or not all(isinstance(item, str) for item in argv_raw):
            raise VllmCliContractHardeningError(f"worker command is invalid: {expected_id}")
        argv = tuple(cast(list[str], argv_raw))
        expected = worker_command_template(expected_port)
        if argv != expected:
            raise VllmCliContractHardeningError(
                f"worker command differs from its canonical builder: {expected_id}"
            )
        command_sha256 = canonical_command_sha256(argv)
        if (
            worker.get("command_sha256") != command_sha256
            or command_sha256 != EXPECTED_COMMAND_SHA256[expected_id]
        ):
            raise VllmCliContractHardeningError(f"worker command identity drifted: {expected_id}")
        options = worker_command_options(argv)
        if options != frozenset(VLLM_API_SERVER_REQUIRED_OPTIONS):
            raise VllmCliContractHardeningError(f"worker option set drifted: {expected_id}")
        if VLLM_REQUEST_LOGGING_DISABLED_OPTION not in options or REJECTED_OPTION in options:
            raise VllmCliContractHardeningError(f"worker logging option drifted: {expected_id}")


def _require_runtime_source(repo_root: Path) -> None:
    source = (repo_root / RUNTIME_PATH).read_text(encoding="utf-8")
    required = (
        'VLLM_REQUEST_LOGGING_DISABLED_OPTION: Final = "--no-enable-log-requests"',
        "VLLM_API_SERVER_REQUIRED_OPTIONS",
        "vllm_api_server_cli_capability",
        "pinned vLLM CLI does not support governed worker options",
        "worker_command_options",
    )
    if any(fragment not in source for fragment in required):
        raise VllmCliContractHardeningError("runtime CLI capability controls drifted")
    command_owner = source[source.index("def worker_command_template") :]
    if REJECTED_OPTION in command_owner:
        raise VllmCliContractHardeningError(
            "the canonical worker command still emits the rejected option"
        )


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    """Validate the hardening tranche without activating a new harness."""

    root = Path(repo_root).resolve()
    _require_base_ancestor(root)
    record = _load_record(root / RECORD_PATH)
    _require_evidence(root, record)
    _require_runtime_source(root)
    _require_worker_plan(root)
    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise VllmCliContractHardeningError("transient operational authorization must be absent")
    return {
        "status": "VLLM_CLI_CONTRACT_HARDENING_IMPLEMENTED",
        "record_id": record.record_id,
        "decision": record.decision,
        "repository_base_commit": record.repository_base_commit,
        "pinned_vllm_version": record.failure.pinned_vllm_version,
        "rejected_option": record.failure.rejected_option,
        "replacement_option": record.implementation.request_logging_disabled_option,
        "pre_worker_cli_capability_gate": (record.implementation.pre_worker_cli_capability_gate),
        "capability_failure_mode": record.implementation.capability_failure_mode,
        "active_harness_unchanged": record.authority_transition.active_harness_unchanged,
        "active_harness_reusable_for_retry": (
            record.authority_transition.active_harness_reusable_for_retry
        ),
        "fresh_issuer_usable": record.authority_transition.fresh_issuer_usable,
        "consumed_authorization_reusable": (
            record.authority_transition.consumed_authorization_reusable
        ),
        "evidence_artifact_count": len(record.evidence),
        "authorization_issued": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": record.next_gate,
    }


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-vllm-cli-contract-hardening")
    parser.add_argument("--repo-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    summary = validate_repository_package(arguments.repo_root)
    for key, value in summary.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
