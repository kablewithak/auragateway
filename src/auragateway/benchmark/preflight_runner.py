"""Validate and plan AuraGateway benchmark execution without provider calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.benchmark.preflight import (
    build_run_ledger,
    evaluate_preflight,
)
from auragateway.contracts.benchmark_preflight import (
    BenchmarkExecutionManifest,
    BenchmarkPreflightInput,
    BenchmarkPreflightReport,
    Gate9PreflightManifest,
    Gate9PreflightSummary,
    PlannedRunLedger,
)

_ASSET_ROOT: Final = Path("data/evals/benchmark/preflight-v1")
_INPUT_PATH: Final = _ASSET_ROOT / "input.json"
_EXECUTION_MANIFEST_PATH: Final = _ASSET_ROOT / "execution_manifest_draft.json"
_PLAN_PATH: Final = _ASSET_ROOT / "planned_run_ledger.json"
_REPORT_PATH: Final = _ASSET_ROOT / "preflight_report.json"
_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"
_CONSTITUTION_PATH: Final = Path("docs/benchmark/AuraGateway_Benchmark_Constitution.md")
_EXECUTION_REQUIREMENTS_PATH: Final = Path(
    "docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md"
)
_GATE8_MANIFEST_PATH: Final = Path("data/evals/evidence/gate8-v1/manifest.json")
_GATE7_MANIFEST_PATH: Final = Path("data/evals/feedback/efc-v1/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class BenchmarkPreflightAssetError(Exception):
    """Expected preflight asset failure with metadata-safe details."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class BenchmarkPreflightAssetErrorEnvelope(BaseModel):
    """Safe CLI failure without prompts, outputs, credentials, or payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _model_json_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2, exclude_none=False) + "\n").encode("utf-8")


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "asset"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, error_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BenchmarkPreflightAssetError(
            error_code=error_code,
            safe_message="Required benchmark preflight asset was not found.",
            path=str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BenchmarkPreflightAssetError(
            error_code="BENCHMARK_PREFLIGHT_ASSET_INVALID_JSON",
            safe_message="Benchmark preflight asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT], error_code: str) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path, error_code))
    except ValidationError as exc:
        raise BenchmarkPreflightAssetError(
            error_code="BENCHMARK_PREFLIGHT_ASSET_VALIDATION_FAILED",
            safe_message="Benchmark preflight asset failed typed validation.",
            path=str(path),
            details=_validation_messages(exc),
        ) from exc


def _require_file(repo_root: Path, path: Path, error_code: str) -> bytes:
    full_path = repo_root / path
    try:
        return full_path.read_bytes()
    except FileNotFoundError as exc:
        raise BenchmarkPreflightAssetError(
            error_code=error_code,
            safe_message="Required upstream benchmark asset was not found.",
            path=str(full_path),
        ) from exc


def _summary(
    input_asset: BenchmarkPreflightInput,
    plan: PlannedRunLedger,
    report: BenchmarkPreflightReport,
) -> Gate9PreflightSummary:
    return Gate9PreflightSummary(
        execution_manifest_status=(
            input_asset.execution_manifest.identity.execution_manifest_status
        ),
        functional_trajectory_count=plan.functional_trajectory_count,
        runtime_trajectory_count=plan.runtime_trajectory_count,
        total_trajectory_count=plan.total_trajectory_count,
        total_turn_count=plan.total_turn_count,
        maximum_request_attempt_count=plan.maximum_request_attempt_count,
        planning_ready=report.planning_ready,
        measured_execution_ready=report.measured_execution_ready,
        execution_enabled=report.execution_enabled,
        measured_execution_permitted=report.measured_execution_permitted,
        failure_codes=report.failure_codes,
    )


def build_assets(
    repo_root: Path,
) -> tuple[
    BenchmarkPreflightInput,
    BenchmarkExecutionManifest,
    PlannedRunLedger,
    BenchmarkPreflightReport,
    Gate9PreflightManifest,
    Gate9PreflightSummary,
]:
    """Build the deterministic non-executing plan and preflight evidence."""

    input_asset = _load_model(
        repo_root / _INPUT_PATH,
        BenchmarkPreflightInput,
        "BENCHMARK_PREFLIGHT_INPUT_NOT_FOUND",
    )
    plan = build_run_ledger(input_asset.plan_request)
    report = evaluate_preflight(
        manifest=input_asset.execution_manifest,
        provider=input_asset.provider_readiness,
        budget=input_asset.budget,
        vault=input_asset.evidence_vault,
        ledger=plan,
    )

    input_bytes = _model_json_bytes(input_asset)
    execution_manifest_bytes = _model_json_bytes(input_asset.execution_manifest)
    plan_bytes = _model_json_bytes(plan)
    report_bytes = _model_json_bytes(report)

    _require_file(
        repo_root,
        _CONSTITUTION_PATH,
        "BENCHMARK_CONSTITUTION_NOT_FOUND",
    )
    requirements_bytes = _require_file(
        repo_root,
        _EXECUTION_REQUIREMENTS_PATH,
        "EXECUTION_MANIFEST_REQUIREMENTS_NOT_FOUND",
    )
    gate8_bytes = _require_file(
        repo_root,
        _GATE8_MANIFEST_PATH,
        "GATE8_MANIFEST_NOT_FOUND",
    )
    gate7_bytes = _require_file(
        repo_root,
        _GATE7_MANIFEST_PATH,
        "GATE7_MANIFEST_NOT_FOUND",
    )

    constitution_sha = input_asset.execution_manifest.identity.benchmark_constitution_sha256

    manifest = Gate9PreflightManifest(
        input_path=_INPUT_PATH.as_posix(),
        input_sha256=_sha256_bytes(input_bytes),
        execution_manifest_path=_EXECUTION_MANIFEST_PATH.as_posix(),
        execution_manifest_sha256=_sha256_bytes(execution_manifest_bytes),
        plan_path=_PLAN_PATH.as_posix(),
        plan_sha256=_sha256_bytes(plan_bytes),
        report_path=_REPORT_PATH.as_posix(),
        report_sha256=_sha256_bytes(report_bytes),
        benchmark_constitution_path=_CONSTITUTION_PATH.as_posix(),
        benchmark_constitution_sha256=constitution_sha,
        execution_requirements_path=_EXECUTION_REQUIREMENTS_PATH.as_posix(),
        execution_requirements_sha256=_sha256_bytes(requirements_bytes),
        gate8_manifest_path=_GATE8_MANIFEST_PATH.as_posix(),
        gate8_manifest_sha256=_sha256_bytes(gate8_bytes),
        gate7_manifest_path=_GATE7_MANIFEST_PATH.as_posix(),
        gate7_manifest_sha256=_sha256_bytes(gate7_bytes),
        total_trajectory_count=plan.total_trajectory_count,
        total_turn_count=plan.total_turn_count,
        maximum_request_attempt_count=plan.maximum_request_attempt_count,
        planning_ready=report.planning_ready,
        measured_execution_ready=report.measured_execution_ready,
        execution_enabled=report.execution_enabled,
        measured_execution_permitted=report.measured_execution_permitted,
    )
    return (
        input_asset,
        input_asset.execution_manifest,
        plan,
        report,
        manifest,
        _summary(input_asset, plan, report),
    )


def write_assets(repo_root: Path) -> Gate9PreflightSummary:
    """Write the deterministic draft manifest, plan, report, and hash manifest."""

    input_asset, execution_manifest, plan, report, manifest, summary = build_assets(repo_root)
    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _INPUT_PATH).write_bytes(_model_json_bytes(input_asset))
    (repo_root / _EXECUTION_MANIFEST_PATH).write_bytes(_model_json_bytes(execution_manifest))
    (repo_root / _PLAN_PATH).write_bytes(_model_json_bytes(plan))
    (repo_root / _REPORT_PATH).write_bytes(_model_json_bytes(report))
    (repo_root / _MANIFEST_PATH).write_bytes(_model_json_bytes(manifest))
    return summary


def verify_assets(repo_root: Path) -> Gate9PreflightSummary:
    """Rebuild and compare persisted benchmark preflight evidence."""

    (
        expected_input,
        expected_execution_manifest,
        expected_plan,
        expected_report,
        expected_manifest,
        summary,
    ) = build_assets(repo_root)
    persisted_input = _load_model(
        repo_root / _INPUT_PATH,
        BenchmarkPreflightInput,
        "BENCHMARK_PREFLIGHT_INPUT_NOT_FOUND",
    )
    persisted_execution_manifest = _load_model(
        repo_root / _EXECUTION_MANIFEST_PATH,
        BenchmarkExecutionManifest,
        "EXECUTION_MANIFEST_DRAFT_NOT_FOUND",
    )
    persisted_plan = _load_model(
        repo_root / _PLAN_PATH,
        PlannedRunLedger,
        "BENCHMARK_PLAN_NOT_FOUND",
    )
    persisted_report = _load_model(
        repo_root / _REPORT_PATH,
        BenchmarkPreflightReport,
        "BENCHMARK_PREFLIGHT_REPORT_NOT_FOUND",
    )
    persisted_manifest = _load_model(
        repo_root / _MANIFEST_PATH,
        Gate9PreflightManifest,
        "BENCHMARK_PREFLIGHT_MANIFEST_NOT_FOUND",
    )
    comparisons = (
        (
            persisted_input,
            expected_input,
            "BENCHMARK_PREFLIGHT_INPUT_MISMATCH",
            _INPUT_PATH,
        ),
        (
            persisted_execution_manifest,
            expected_execution_manifest,
            "EXECUTION_MANIFEST_DRAFT_MISMATCH",
            _EXECUTION_MANIFEST_PATH,
        ),
        (persisted_plan, expected_plan, "BENCHMARK_PLAN_MISMATCH", _PLAN_PATH),
        (
            persisted_report,
            expected_report,
            "BENCHMARK_PREFLIGHT_REPORT_MISMATCH",
            _REPORT_PATH,
        ),
        (
            persisted_manifest,
            expected_manifest,
            "BENCHMARK_PREFLIGHT_MANIFEST_MISMATCH",
            _MANIFEST_PATH,
        ),
    )
    for observed, expected, error_code, path in comparisons:
        if observed != expected:
            raise BenchmarkPreflightAssetError(
                error_code=error_code,
                safe_message="Persisted benchmark preflight evidence is not reproducible.",
                path=str(repo_root / path),
            )
    return summary


def validate_config(repo_root: Path) -> Gate9PreflightSummary:
    """Validate typed configuration and prove deterministic plan expansion."""

    *_, summary = build_assets(repo_root)
    if not summary.planning_ready:
        raise BenchmarkPreflightAssetError(
            error_code="BENCHMARK_PLANNING_NOT_READY",
            safe_message="Benchmark configuration is not ready for deterministic planning.",
            details=tuple(code.value for code in summary.failure_codes),
        )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate-config", "plan", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; no command in this module executes provider calls."""

    args = _parse_args(argv)
    try:
        if args.command == "validate-config":
            summary = validate_config(args.repo_root)
        elif args.command == "plan":
            summary = write_assets(args.repo_root)
        else:
            summary = verify_assets(args.repo_root)
    except BenchmarkPreflightAssetError as exc:
        envelope = BenchmarkPreflightAssetErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
