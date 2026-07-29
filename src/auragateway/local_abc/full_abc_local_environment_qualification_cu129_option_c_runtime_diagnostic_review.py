"""Validate the approved Option C two-stage runtime diagnostic decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, model_validator

from auragateway.local_abc.contracts import LocalABCContract

REPOSITORY_BASE_COMMIT: Final = "49f2cc61f77337d8879981c15291ea394d56df78"
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_option_c_runtime_diagnostic_decision_v1.json"
)
RECORD_SHA256: Final = "6297b48f64811dbd1b86c850b0fbd66a4142d174d69897b673eb5748663cc418"
PREVIOUS_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_flashinfer_link_failure_remediation_review_v1.json"
)
PREVIOUS_REVIEW_SHA256: Final = "064585697baab971a216709592dda8e3a23c30151340e23a352190aa502635fb"
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
ADR_PATH: Final = Path("docs/adr/2026-07-29-local-abc-cu129-option-c-runtime-diagnostic.md")
REPORT_PATH: Final = Path("docs/reports/AuraGateway_CU129_Option_C_Runtime_Diagnostic_Decision.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_cu129_option_c_runtime_diagnostic_v1.md")
DECISION: Final = "APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC"
NEXT_GATE: Final = "implement_p0_p2_platform_diagnostic_assets"


class OptionCRuntimeDiagnosticDecisionError(RuntimeError):
    """Fail-closed decision-package validation error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise OptionCRuntimeDiagnosticDecisionError(message)


class ProbeDefinition(LocalABCContract):
    """One fixed diagnostic probe and its decision transition."""

    probe_id: Literal["P0", "P1", "P2", "P3", "P4", "P5", "P6"]
    name: str = Field(min_length=3, max_length=96)
    question: str = Field(min_length=20, max_length=240)
    pass_decision: str = Field(min_length=3, max_length=96)
    fail_decision: str = Field(min_length=3, max_length=96)


class SupersededOperationalNextGate(LocalABCContract):
    """Prior operational gate replaced by the accepted Option C sequence."""

    record_id: Literal["auragateway-cu129-flashinfer-link-failure-remediation-review-v1"]
    previous_next_gate: Literal["merge_then_implement_deterministic_t4_attention_backend"]
    replacement_sequence: Literal[
        "P0_P2_PLATFORM_DIAGNOSTIC_THEN_TRITON_IMPLEMENTATION_THEN_P3_P6_RUNTIME_DIAGNOSTIC"
    ]


class SelectedStrategy(LocalABCContract):
    """Accepted two-stage compatibility strategy."""

    strategy_id: Literal["OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC"]
    selected_backend: Literal["TRITON_ATTN"]
    backend_decision_changed: Literal[False]
    platform_diagnostic_precedes_backend_implementation: Literal[True]
    runtime_diagnostic_follows_merged_backend_implementation: Literal[True]
    full_qualification_attempt_consumed_by_p0_p2: Literal[False]


class PlatformDiagnosticBoundary(LocalABCContract):
    """P0-P2 platform-only boundary."""

    mode: Literal["KAGGLE_DIAGNOSTIC"]
    probes: tuple[ProbeDefinition, ProbeDefinition, ProbeDefinition]
    model_load_permitted: Literal[False]
    worker_start_permitted: Literal[False]
    model_requests_permitted: Literal[0]
    benchmark_trajectory_requests_permitted: Literal[0]
    network_access_permitted: Literal[False]
    credentials_permitted: Literal[False]
    customer_data_permitted: Literal[False]
    external_spend: Literal[0]
    kaggle_specific_libcuda_symlink_permitted: Literal[False]
    system_library_copy_permitted: Literal[False]
    silent_environment_mutation_permitted: Literal[False]
    maximum_sessions: Literal[1]

    @model_validator(mode="after")
    def validate_probe_order(self) -> Self:
        expected = (
            (
                "P0",
                "KAGGLE_IMAGE_AND_RUNTIME_IDENTITY",
                "PLATFORM_IDENTITY_CAPTURED",
                "DIAGNOSTIC_INVALID",
            ),
            (
                "P1",
                "CUDA_DRIVER_LINKER_VISIBILITY",
                "CUDA_DRIVER_LINKER_CONTRACT_PASSED",
                "CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED",
            ),
            (
                "P2",
                "MINIMAL_TRITON_KERNEL",
                "CURRENT_STACK_TRITON_PRIMITIVE_PASSED",
                "CURRENT_STACK_TRITON_INCOMPATIBLE",
            ),
        )
        observed = tuple(
            (probe.probe_id, probe.name, probe.pass_decision, probe.fail_decision)
            for probe in self.probes
        )
        if observed != expected:
            raise ValueError("P0-P2 probe order or decision transitions drifted")
        return self


class RuntimeDiagnosticBoundary(LocalABCContract):
    """P3-P6 runtime boundary reserved for a later authorized tranche."""

    mode: Literal["KAGGLE_DIAGNOSTIC"]
    prerequisite: Literal["EXPLICIT_TRITON_IMPLEMENTATION_MERGED"]
    probes: tuple[
        ProbeDefinition,
        ProbeDefinition,
        ProbeDefinition,
        ProbeDefinition,
    ]
    separate_future_authorization_required: Literal[True]
    model_request_budget_status: Literal["TO_BE_FROZEN_IN_P3_P6_IMPLEMENTATION"]
    benchmark_trajectory_requests_permitted: Literal[0]
    measured_execution_permitted: Literal[False]
    hidden_retries_permitted: Literal[False]
    replacement_workers_permitted: Literal[False]
    silent_backend_fallback_permitted: Literal[False]

    @model_validator(mode="after")
    def validate_probe_order(self) -> Self:
        expected = (
            (
                "P3",
                "ONE_WORKER_EXPLICIT_TRITON_STARTUP",
                "ONE_WORKER_TRITON_STARTUP_PASSED",
                "CURRENT_VLLM_TRITON_RUNTIME_FAILED",
            ),
            (
                "P4",
                "ONE_DETERMINISTIC_REQUEST",
                "ONE_REQUEST_RUNTIME_COMPATIBILITY_PASSED",
                "CURRENT_VLLM_TRITON_RUNTIME_FAILED",
            ),
            (
                "P5",
                "PREFIX_CACHE_SMOKE_AND_RESET",
                "CACHE_SMOKE_AND_RESET_PASSED",
                "RUNTIME_WORKS_BUT_PRD_OBSERVABILITY_CONTRACT_FAILED",
            ),
            (
                "P6",
                "DUAL_PROCESS_FEASIBILITY",
                "DUAL_WORKER_DIAGNOSTIC_PASSED",
                "SINGLE_WORKER_COMPATIBLE_DUAL_WORKER_CONTRACT_FAILED",
            ),
        )
        observed = tuple(
            (probe.probe_id, probe.name, probe.pass_decision, probe.fail_decision)
            for probe in self.probes
        )
        if observed != expected:
            raise ValueError("P3-P6 probe order or decision transitions drifted")
        return self


class FailureBudget(LocalABCContract):
    """Frozen compatibility circuit breaker."""

    platform_diagnostic_sessions: Literal[1]
    explicit_triton_full_qualification_attempts: Literal[1]
    compatibility_spike_candidates_maximum: Literal[3]
    fourth_blind_vllm_repair_cycle_permitted: Literal[False]


class ReviewSafety(LocalABCContract):
    """Decision-only safety state."""

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


class OptionCRuntimeDiagnosticDecisionRecord(LocalABCContract):
    """Canonical decision contract for the accepted Option C sequence."""

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-cu129-option-c-runtime-diagnostic-decision-v1"]
    repository_base_commit: Literal["49f2cc61f77337d8879981c15291ea394d56df78"]
    decision: Literal["APPROVED_FOR_OPTION_C_TWO_STAGE_RUNTIME_DIAGNOSTIC"]
    supersedes_operational_next_gate: SupersededOperationalNextGate
    selected_strategy: SelectedStrategy
    platform_diagnostic: PlatformDiagnosticBoundary
    runtime_diagnostic: RuntimeDiagnosticBoundary
    failure_budget: FailureBudget
    safety: ReviewSafety
    next_gate: Literal["implement_p0_p2_platform_diagnostic_assets"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def validate_non_claims(self) -> Self:
        required_fragments = (
            "P0-P2 have not been implemented.",
            "P0-P2 have not been executed.",
            "Linker-visible libcuda has not been proven.",
            "TRITON_ATTN has not been added to canonical worker argv.",
            "Measured A/B/C execution has not occurred.",
            "production readiness",
        )
        joined = "\n".join(self.non_claims)
        if any(fragment not in joined for fragment in required_fragments):
            raise ValueError("Option C non-claims are incomplete")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OptionCRuntimeDiagnosticDecisionError(
            f"required JSON is unreadable: {path.as_posix()}"
        ) from exc
    if not isinstance(payload, dict):
        raise OptionCRuntimeDiagnosticDecisionError(
            f"required JSON must contain one object: {path.as_posix()}"
        )
    return cast(dict[str, object], payload)


def _load_record(path: Path) -> OptionCRuntimeDiagnosticDecisionRecord:
    try:
        observed = path.read_text(encoding="utf-8")
        record = OptionCRuntimeDiagnosticDecisionRecord.model_validate_json(observed)
    except OSError as exc:
        raise OptionCRuntimeDiagnosticDecisionError(
            "Option C decision record is unreadable"
        ) from exc
    if observed != record.canonical_json():
        raise OptionCRuntimeDiagnosticDecisionError(
            "Option C decision record is not canonical JSON"
        )
    if _sha256(path) != RECORD_SHA256:
        raise OptionCRuntimeDiagnosticDecisionError("Option C decision record identity drifted")
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
        raise OptionCRuntimeDiagnosticDecisionError(
            "the Option C repository base is not an ancestor of HEAD"
        )


def _require_authorization_absent(repo_root: Path) -> None:
    if (repo_root / FINAL_AUTHORIZATION_PATH).exists():
        raise OptionCRuntimeDiagnosticDecisionError("a live transient authorization is prohibited")


def _require_previous_decision(repo_root: Path) -> None:
    path = repo_root / PREVIOUS_REVIEW_PATH
    if not path.is_file() or _sha256(path) != PREVIOUS_REVIEW_SHA256:
        raise OptionCRuntimeDiagnosticDecisionError(
            "the merged FlashInfer remediation review identity drifted"
        )
    payload = _load_json_object(path)
    implementation = payload.get("implementation_boundary")
    if (
        payload.get("decision") != "APPROVED_FOR_DETERMINISTIC_T4_ATTENTION_BACKEND_IMPLEMENTATION"
        or not isinstance(implementation, dict)
        or implementation.get("selected_backend") != "TRITON_ATTN"
    ):
        raise OptionCRuntimeDiagnosticDecisionError(
            "the prior deterministic-backend decision drifted"
        )


def _require_runtime_implementation_absent(repo_root: Path) -> None:
    payload = _load_json_object(repo_root / WORKER_PLAN_PATH)
    workers = payload.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise OptionCRuntimeDiagnosticDecisionError("current worker plan is invalid")
    for worker in workers:
        argv = worker.get("command_argv") if isinstance(worker, dict) else None
        if not isinstance(argv, list):
            raise OptionCRuntimeDiagnosticDecisionError("current worker command is invalid")
        if "--attention-backend" in argv or "TRITON_ATTN" in argv:
            raise OptionCRuntimeDiagnosticDecisionError(
                "runtime implementation was mixed into the Option C decision tranche"
            )


def _require_document_markers(repo_root: Path) -> None:
    required = (
        (
            ADR_PATH,
            (
                "Option C",
                "P0-P2",
                "P3-P6",
                "TRITON_ATTN",
                "do not consume the full qualification attempt",
            ),
        ),
        (
            REPORT_PATH,
            (
                "85 paths",
                "historical evidence",
                "true mutable boundary",
                "implement P0-P2",
            ),
        ),
        (
            RUNBOOK_PATH,
            (
                "P0",
                "P1",
                "P2",
                "model load: 0",
                "stop at the first failed probe",
            ),
        ),
    )
    for relative_path, markers in required:
        path = repo_root / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OptionCRuntimeDiagnosticDecisionError(
                f"required Option C document is unreadable: {relative_path.as_posix()}"
            ) from exc
        normalized = content.casefold()
        if any(marker.casefold() not in normalized for marker in markers):
            raise OptionCRuntimeDiagnosticDecisionError(
                f"required Option C document markers drifted: {relative_path.as_posix()}"
            )


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    """Validate the accepted Option C decision and prove runtime changes remain deferred."""

    root = Path(repo_root).resolve()
    _require_base_ancestor(root)
    _require_authorization_absent(root)
    _require_previous_decision(root)
    record = _load_record(root / RECORD_PATH)
    _require_runtime_implementation_absent(root)
    _require_document_markers(root)
    return {
        "status": "OPTION_C_RUNTIME_DIAGNOSTIC_DECISION_VALID",
        "record_id": record.record_id,
        "decision": record.decision,
        "repository_base_commit": record.repository_base_commit,
        "selected_backend": record.selected_strategy.selected_backend,
        "platform_probe_count": len(record.platform_diagnostic.probes),
        "runtime_probe_count": len(record.runtime_diagnostic.probes),
        "runtime_source_changed": record.safety.runtime_source_changed,
        "authorization_issued": record.safety.authorization_issued,
        "kaggle_execution_performed": record.safety.kaggle_execution_performed,
        "full_qualification_attempt_consumed_by_p0_p2": (
            record.selected_strategy.full_qualification_attempt_consumed_by_p0_p2
        ),
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
    except OptionCRuntimeDiagnosticDecisionError as error:
        print(
            json.dumps(
                {
                    "error_code": "OPTION_C_RUNTIME_DIAGNOSTIC_DECISION_INVALID",
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
