"""Execution-manifest freeze controls for the AuraGateway benchmark."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any, Final, TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.contracts.benchmark_preflight import (
    BenchmarkExecutionManifest,
    BenchmarkPreflightInput,
    PlannedRunLedger,
)
from auragateway.contracts.execution_freeze import (
    CostBudgetDecision,
    CrossConditionIsolationReport,
    ExecutionFreezeSummary,
    ExecutionManifestFreezeReport,
    FaultInjectionFixtureSet,
    FreezeCheckResult,
    FreezeCheckStatus,
    Gate10ExecutionFreezeManifest,
    NegativeControlManifest,
    PricingSchedule,
    PrivacyVerificationReport,
    ProviderReadinessRecord,
)

_ASSET_ROOT: Final = Path("data/evals/benchmark/freeze-v1")
_PRICING_PATH: Final = _ASSET_ROOT / "pricing_schedule.json"
_NEGATIVE_CONTROLS_PATH: Final = _ASSET_ROOT / "negative_control_manifest.json"
_FAULT_FIXTURES_PATH: Final = _ASSET_ROOT / "fault_injection_fixtures.json"
_PRIVACY_REPORT_PATH: Final = _ASSET_ROOT / "privacy_verification.json"
_PROVIDER_READINESS_PATH: Final = _ASSET_ROOT / "provider_readiness.json"
_ISOLATION_REPORT_PATH: Final = _ASSET_ROOT / "cross_condition_isolation.json"
_COST_BUDGET_PATH: Final = _ASSET_ROOT / "cost_budget_decision.json"
_EXECUTION_MANIFEST_PATH: Final = _ASSET_ROOT / "execution_manifest.json"
_FREEZE_REPORT_PATH: Final = _ASSET_ROOT / "freeze_report.json"
_GATE10_MANIFEST_PATH: Final = _ASSET_ROOT / "manifest.json"

_GATE9_INPUT_PATH: Final = Path("data/evals/benchmark/preflight-v1/input.json")
_GATE9_PLAN_PATH: Final = Path("data/evals/benchmark/preflight-v1/planned_run_ledger.json")
_GATE9_MANIFEST_PATH: Final = Path("data/evals/benchmark/preflight-v1/manifest.json")

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ExecutionFreezeError(Exception):
    """Expected freeze failure with bounded metadata-safe diagnostics."""

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


def sha256_bytes(payload: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(payload).hexdigest()


def model_json_bytes(model: BaseModel) -> bytes:
    """Serialize one typed artifact using repository JSON formatting."""

    return (model.model_dump_json(indent=2, exclude_none=False) + "\n").encode("utf-8")


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "asset"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def load_json(path: Path) -> object:
    """Load JSON with a bounded error envelope."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExecutionFreezeError(
            "EXECUTION_FREEZE_ASSET_NOT_FOUND",
            "A required execution-freeze asset was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise ExecutionFreezeError(
            "EXECUTION_FREEZE_ASSET_INVALID_JSON",
            "An execution-freeze asset is not valid JSON.",
            str(path),
        ) from exc


def load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    """Load and validate one typed JSON artifact."""

    try:
        return model_type.model_validate(load_json(path))
    except ValidationError as exc:
        raise ExecutionFreezeError(
            "EXECUTION_FREEZE_ASSET_VALIDATION_FAILED",
            "An execution-freeze asset failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def canonical_execution_manifest_sha256(manifest: BenchmarkExecutionManifest) -> str:
    """Hash a frozen execution manifest without its self-hash field."""

    payload = manifest.model_dump(mode="json", exclude_none=True)
    identity = dict(payload["identity"])
    identity.pop("execution_manifest_sha256", None)
    payload["identity"] = identity
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(normalized.encode("utf-8"))


def _static_assets(
    repo_root: Path,
) -> tuple[
    PricingSchedule,
    NegativeControlManifest,
    FaultInjectionFixtureSet,
    PrivacyVerificationReport,
]:
    pricing = load_model(repo_root / _PRICING_PATH, PricingSchedule)
    controls = load_model(repo_root / _NEGATIVE_CONTROLS_PATH, NegativeControlManifest)
    faults = load_model(repo_root / _FAULT_FIXTURES_PATH, FaultInjectionFixtureSet)
    privacy = load_model(repo_root / _PRIVACY_REPORT_PATH, PrivacyVerificationReport)
    if not privacy.privacy_verification_passed:
        raise ExecutionFreezeError(
            "PRIVACY_VERIFICATION_FAILED",
            "The public-evidence privacy verification did not pass.",
            str(repo_root / _PRIVACY_REPORT_PATH),
        )
    return pricing, controls, faults, privacy


def validate_static_assets(repo_root: Path) -> ExecutionFreezeSummary:
    """Validate deterministic freeze inputs without provider calls."""

    _static_assets(repo_root)
    gate9_manifest = load_json(repo_root / _GATE9_MANIFEST_PATH)
    if not isinstance(gate9_manifest, dict) or gate9_manifest.get("planning_ready") is not True:
        raise ExecutionFreezeError(
            "GATE9_PREFLIGHT_INVALID",
            "Gate 9 preflight evidence is not planning-ready.",
            str(repo_root / _GATE9_MANIFEST_PATH),
        )
    return ExecutionFreezeSummary(
        command="validate",
        provider_probe_passed=(repo_root / _PROVIDER_READINESS_PATH).exists(),
        execution_manifest_frozen=(repo_root / _EXECUTION_MANIFEST_PATH).exists(),
        gate_10_passed=(repo_root / _GATE10_MANIFEST_PATH).exists(),
    )


def _run_json_command(command: list[str], *, error_code: str, safe_message: str) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise ExecutionFreezeError(
            error_code,
            safe_message,
            details=(f"return_code={completed.returncode}",),
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExecutionFreezeError(
            error_code,
            "A required subprocess returned non-JSON output.",
        ) from exc
    if not isinstance(payload, dict):
        raise ExecutionFreezeError(
            error_code,
            "A required subprocess returned an invalid envelope.",
        )
    return payload


def verify_gate9_preflight(repo_root: Path) -> None:
    """Require reproducible Gate 9 evidence before freeze."""

    payload = _run_json_command(
        [
            sys.executable,
            "-m",
            "auragateway.benchmark.preflight_runner",
            "verify",
            "--repo-root",
            str(repo_root),
        ],
        error_code="GATE9_PREFLIGHT_INVALID",
        safe_message="Gate 9 preflight verification failed.",
    )
    if payload.get("planning_ready") is not True:
        raise ExecutionFreezeError(
            "GATE9_PREFLIGHT_INVALID",
            "Gate 9 preflight is not planning-ready.",
        )


def _protected_report_path(repo_root: Path, report_path: str) -> tuple[Path, str]:
    candidate = Path(report_path)
    full_path = candidate if candidate.is_absolute() else repo_root / candidate
    try:
        relative = full_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ExecutionFreezeError(
            "PROVIDER_PROBE_FAILED",
            "Provider probe report escaped the repository boundary.",
        ) from exc
    return full_path, relative


def _report_is_public_safe(payload: object) -> bool:
    serialized = json.dumps(payload, sort_keys=True).casefold()
    forbidden_markers = (
        '"raw_payload"',
        '"output_text"',
        '"prompt_text"',
        '"messages"',
        '"api_key"',
        '"credentials"',
        '"secret"',
    )
    return not any(marker in serialized for marker in forbidden_markers)


def _validated_probe_calls(payload: object, path: str) -> list[object]:
    if not isinstance(payload, dict):
        raise ExecutionFreezeError(
            "PROVIDER_PROBE_FAILED",
            "The bounded provider report has an invalid root type.",
            path,
        )
    calls = payload.get("calls")
    if not isinstance(calls, list):
        raise ExecutionFreezeError(
            "PROVIDER_PROBE_FAILED",
            "The bounded provider report does not contain a typed call list.",
            path,
        )
    report_valid = all(
        (
            payload.get("mode") == "groq_live",
            payload.get("status") == "passed",
            payload.get("raw_payload_persisted") is False,
            payload.get("measured_execution_permitted") is False,
            1 <= len(calls) <= 2,
            _report_is_public_safe(payload),
        )
    )
    if not report_valid:
        raise ExecutionFreezeError(
            "PROVIDER_PROBE_FAILED",
            "The bounded provider report failed safety or evidence validation.",
            path,
        )
    return calls


def probe_provider(repo_root: Path) -> ExecutionFreezeSummary:
    """Run the existing two-call Groq smoke probe and persist a sanitized record."""

    if not os.environ.get("GROQ_API_KEY", "").strip():
        raise ExecutionFreezeError(
            "PROVIDER_CONFIGURATION_NOT_READY",
            "GROQ_API_KEY is not configured in the current environment.",
        )
    summary = _run_json_command(
        [
            sys.executable,
            "-m",
            "auragateway.providers.calibration_runner",
            "groq-smoke",
            "--repo-root",
            str(repo_root),
        ],
        error_code="PROVIDER_PROBE_FAILED",
        safe_message="The bounded Groq provider probe failed.",
    )
    report_path_value = summary.get("report_path")
    if summary.get("calibration_passed") is not True or not isinstance(report_path_value, str):
        raise ExecutionFreezeError(
            "PROVIDER_PROBE_FAILED",
            "The bounded Groq provider probe did not produce passing evidence.",
        )
    full_path, relative_path = _protected_report_path(repo_root, report_path_value)
    report_payload = load_json(full_path)
    calls = _validated_probe_calls(report_payload, relative_path)
    report_bytes = full_path.read_bytes()
    record = ProviderReadinessRecord(
        record_id="groq-gpt-oss-20b-readiness-v1",
        provider_name="groq",
        provider_model_alias="groq-gpt-oss-20b",
        provider_adapter_version="groq-chat-completions-v1",
        probe_mode="groq_live",
        credentials_configured=True,
        probe_performed=True,
        probe_passed=True,
        call_count=len(calls),
        protected_report_path=relative_path,
        protected_report_sha256=sha256_bytes(report_bytes),
        raw_payload_persisted=False,
        measured_execution_permitted=False,
        observed_at=datetime.now(UTC),
    )
    destination = repo_root / _PROVIDER_READINESS_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(model_json_bytes(record))
    return ExecutionFreezeSummary(
        command="probe-provider",
        provider_probe_passed=True,
        execution_manifest_frozen=False,
        gate_10_passed=False,
    )


def build_isolation_report(ledger: PlannedRunLedger) -> CrossConditionIsolationReport:
    """Derive trace IDs and verify cache namespace isolation across the frozen plan."""

    run_ids = [item.run_id for item in ledger.runs]
    trace_ids = [f"trace-{sha256_bytes(item.run_id.encode('utf-8'))[:24]}" for item in ledger.runs]
    namespaces = [item.cache_namespace_id for item in ledger.runs]
    pair_conditions: dict[str, set[str]] = {}
    namespace_conditions: dict[str, set[str]] = {}
    for item in ledger.runs:
        pair_conditions.setdefault(item.comparison_pair_id, set()).add(item.condition_id.value)
        namespace_conditions.setdefault(item.cache_namespace_id, set()).add(item.condition_id.value)
    required_conditions = {"condition_a", "condition_b", "condition_c"}
    complete_pairs = sum(values == required_conditions for values in pair_conditions.values())
    cross_condition_reuse = sum(len(values) > 1 for values in namespace_conditions.values())
    duplicate_run_ids = len(run_ids) - len(set(run_ids))
    duplicate_trace_ids = len(trace_ids) - len(set(trace_ids))
    duplicate_namespaces = len(namespaces) - len(set(namespaces))
    isolation_passed = all(
        value == 0
        for value in (
            duplicate_run_ids,
            duplicate_trace_ids,
            duplicate_namespaces,
            cross_condition_reuse,
        )
    ) and complete_pairs == len(pair_conditions)
    return CrossConditionIsolationReport(
        report_id="auragateway-cross-condition-isolation-v1",
        total_trajectory_count=len(ledger.runs),
        unique_run_id_count=len(set(run_ids)),
        unique_trace_id_count=len(set(trace_ids)),
        unique_cache_namespace_count=len(set(namespaces)),
        comparison_pair_count=len(pair_conditions),
        complete_abc_pair_count=complete_pairs,
        duplicate_run_id_count=duplicate_run_ids,
        duplicate_trace_id_count=duplicate_trace_ids,
        duplicate_cache_namespace_count=duplicate_namespaces,
        cross_condition_namespace_reuse_count=cross_condition_reuse,
        isolation_passed=isolation_passed,
    )


def estimate_cost_budget(
    *,
    pricing: PricingSchedule,
    maximum_request_attempt_count: int,
    approved_cost_budget_minor_units: int,
) -> CostBudgetDecision:
    """Calculate a worst-case uncached-input estimate and compare it with the ceiling."""

    million = Decimal(1_000_000)
    attempts = Decimal(maximum_request_attempt_count)
    input_cost = (
        attempts
        * Decimal(pricing.maximum_input_tokens_per_attempt)
        * pricing.uncached_input_usd_per_million_tokens
        / million
    )
    output_cost = (
        attempts
        * Decimal(pricing.maximum_output_tokens_per_attempt)
        * pricing.output_usd_per_million_tokens
        / million
    )
    estimated_minor_units = int(
        ((input_cost + output_cost) * 100).to_integral_value(rounding=ROUND_CEILING)
    )
    return CostBudgetDecision(
        decision_id="auragateway-groq-cost-budget-v1",
        pricing_schedule_id=pricing.pricing_schedule_id,
        maximum_request_attempt_count=maximum_request_attempt_count,
        maximum_input_tokens_per_attempt=pricing.maximum_input_tokens_per_attempt,
        maximum_output_tokens_per_attempt=pricing.maximum_output_tokens_per_attempt,
        estimated_upper_bound_minor_units=estimated_minor_units,
        approved_cost_budget_minor_units=approved_cost_budget_minor_units,
        currency=pricing.currency,
        estimate_uses_uncached_input_price=True,
        budget_sufficient=approved_cost_budget_minor_units >= estimated_minor_units,
        estimate_status=pricing.estimate_status,
    )


def _frozen_manifest(
    *,
    draft_input: BenchmarkPreflightInput,
    pricing: PricingSchedule,
    controls_sha256: str,
    faults_sha256: str,
    privacy_sha256: str,
    isolation_sha256: str,
    implementation_git_sha: str,
) -> BenchmarkExecutionManifest:
    payload = draft_input.execution_manifest.model_dump(mode="json", exclude_none=False)
    identity = dict(payload["identity"])
    identity.update(
        {
            "execution_manifest_id": "execution-manifest-auragateway-v1",
            "execution_manifest_version": "1.0.0",
            "execution_manifest_status": "frozen",
            "execution_manifest_sha256": "0" * 64,
            "git_commit_sha": implementation_git_sha,
            "execution_enabled": False,
        }
    )
    assets = dict(payload["assets"])
    assets.update(
        {
            "provider_documentation_date_checked": pricing.source_date.isoformat(),
            "pricing_schedule_version": pricing.pricing_schedule_id,
            "pricing_source_date": pricing.source_date.isoformat(),
            "currency": pricing.currency,
            "negative_control_manifest_sha256": controls_sha256,
            "fault_injection_fixture_sha256": faults_sha256,
            "privacy_verification_report_sha256": privacy_sha256,
            "cross_condition_isolation_test_sha256": isolation_sha256,
        }
    )
    payload["identity"] = identity
    payload["assets"] = assets
    preliminary = BenchmarkExecutionManifest.model_validate(payload)
    digest = canonical_execution_manifest_sha256(preliminary)
    identity["execution_manifest_sha256"] = digest
    payload["identity"] = identity
    return BenchmarkExecutionManifest.model_validate(payload)


def _passed_check(name: str, *details: str) -> FreezeCheckResult:
    return FreezeCheckResult(
        check_name=name,
        status=FreezeCheckStatus.PASSED,
        details=tuple(details),
    )


def _freeze_report(
    *,
    manifest: BenchmarkExecutionManifest,
    provider: ProviderReadinessRecord,
    budget: CostBudgetDecision,
    privacy: PrivacyVerificationReport,
    isolation: CrossConditionIsolationReport,
    implementation_git_sha: str,
) -> ExecutionManifestFreezeReport:
    canonical_sha = canonical_execution_manifest_sha256(manifest)
    checks = (
        _passed_check("gate9_preflight_verified", "Gate 9 artifacts reproduce"),
        _passed_check("pricing_schedule_verified", "official source and token rates pinned"),
        _passed_check("negative_controls_verified", "predeclared controls are frozen"),
        _passed_check("fault_fixtures_verified", "fault fixtures are frozen"),
        _passed_check(
            "privacy_verification_passed",
            "public and protected evidence remain separated",
        ),
        _passed_check(
            "cross_condition_isolation_passed",
            "cache namespaces are condition-isolated",
        ),
        _passed_check(
            "provider_configuration_ready",
            "credential presence retained as boolean only",
        ),
        _passed_check("provider_live_probe_passed", f"bounded calls={provider.call_count}"),
        _passed_check(
            "cost_budget_sufficient",
            f"estimated_minor_units={budget.estimated_upper_bound_minor_units}",
        ),
        _passed_check("execution_manifest_frozen", "status=frozen"),
        _passed_check("execution_manifest_hash_valid", f"sha256={canonical_sha}"),
        _passed_check("execution_disabled_pending_runner", "execution_enabled=false"),
    )
    return ExecutionManifestFreezeReport(
        report_id="auragateway-gate-10-execution-freeze-report-v1",
        execution_manifest_id=manifest.identity.execution_manifest_id,
        execution_manifest_sha256=canonical_sha,
        implementation_git_sha=implementation_git_sha,
        checks=checks,
        failure_codes=(),
        execution_manifest_frozen=True,
        provider_probe_passed=provider.probe_passed,
        cost_budget_sufficient=budget.budget_sufficient,
        privacy_verification_passed=privacy.privacy_verification_passed,
        cross_condition_isolation_passed=isolation.isolation_passed,
        gate_10_passed=True,
    )


def _file_sha256(repo_root: Path, relative_path: Path) -> str:
    try:
        return sha256_bytes((repo_root / relative_path).read_bytes())
    except FileNotFoundError as exc:
        raise ExecutionFreezeError(
            "EXECUTION_FREEZE_ASSET_NOT_FOUND",
            "A required execution-freeze artifact was not found.",
            str(repo_root / relative_path),
        ) from exc


def freeze_execution_manifest(
    *,
    repo_root: Path,
    implementation_git_sha: str,
    approved_cost_budget_minor_units: int,
) -> ExecutionFreezeSummary:
    """Resolve all freeze blockers and write the non-executing frozen manifest."""

    if len(implementation_git_sha) != 40 or any(
        character not in "0123456789abcdef" for character in implementation_git_sha
    ):
        raise ExecutionFreezeError(
            "IMPLEMENTATION_GIT_SHA_INVALID",
            "The implementation Git SHA must be lowercase 40-character hex.",
        )
    verify_gate9_preflight(repo_root)
    pricing, _controls, _faults, privacy = _static_assets(repo_root)
    provider = load_model(repo_root / _PROVIDER_READINESS_PATH, ProviderReadinessRecord)
    protected_report = repo_root / provider.protected_report_path
    if not protected_report.exists() or sha256_bytes(protected_report.read_bytes()) != (
        provider.protected_report_sha256
    ):
        raise ExecutionFreezeError(
            "PROVIDER_PROBE_FAILED",
            "Protected provider probe evidence is missing or changed.",
            provider.protected_report_path,
        )
    _validated_probe_calls(
        load_json(protected_report),
        provider.protected_report_path,
    )
    draft_input = load_model(repo_root / _GATE9_INPUT_PATH, BenchmarkPreflightInput)
    ledger = load_model(repo_root / _GATE9_PLAN_PATH, PlannedRunLedger)
    isolation = build_isolation_report(ledger)
    if not isolation.isolation_passed:
        raise ExecutionFreezeError(
            "CROSS_CONDITION_ISOLATION_FAILED",
            "Cross-condition isolation evidence did not pass.",
        )
    budget = estimate_cost_budget(
        pricing=pricing,
        maximum_request_attempt_count=ledger.maximum_request_attempt_count,
        approved_cost_budget_minor_units=approved_cost_budget_minor_units,
    )
    if not budget.budget_sufficient:
        raise ExecutionFreezeError(
            "COST_BUDGET_INSUFFICIENT",
            "The approved cost ceiling is below the conservative upper-bound estimate.",
            details=(
                f"estimated_minor_units={budget.estimated_upper_bound_minor_units}",
                f"approved_minor_units={budget.approved_cost_budget_minor_units}",
            ),
        )

    asset_root = repo_root / _ASSET_ROOT
    asset_root.mkdir(parents=True, exist_ok=True)
    (repo_root / _ISOLATION_REPORT_PATH).write_bytes(model_json_bytes(isolation))
    (repo_root / _COST_BUDGET_PATH).write_bytes(model_json_bytes(budget))

    controls_sha = _file_sha256(repo_root, _NEGATIVE_CONTROLS_PATH)
    faults_sha = _file_sha256(repo_root, _FAULT_FIXTURES_PATH)
    privacy_sha = _file_sha256(repo_root, _PRIVACY_REPORT_PATH)
    isolation_sha = _file_sha256(repo_root, _ISOLATION_REPORT_PATH)
    execution_manifest = _frozen_manifest(
        draft_input=draft_input,
        pricing=pricing,
        controls_sha256=controls_sha,
        faults_sha256=faults_sha,
        privacy_sha256=privacy_sha,
        isolation_sha256=isolation_sha,
        implementation_git_sha=implementation_git_sha,
    )
    (repo_root / _EXECUTION_MANIFEST_PATH).write_bytes(model_json_bytes(execution_manifest))
    report = _freeze_report(
        manifest=execution_manifest,
        provider=provider,
        budget=budget,
        privacy=privacy,
        isolation=isolation,
        implementation_git_sha=implementation_git_sha,
    )
    (repo_root / _FREEZE_REPORT_PATH).write_bytes(model_json_bytes(report))

    gate10_manifest = Gate10ExecutionFreezeManifest(
        gate9_manifest_path=_GATE9_MANIFEST_PATH.as_posix(),
        gate9_manifest_sha256=_file_sha256(repo_root, _GATE9_MANIFEST_PATH),
        pricing_schedule_path=_PRICING_PATH.as_posix(),
        pricing_schedule_sha256=_file_sha256(repo_root, _PRICING_PATH),
        negative_control_manifest_path=_NEGATIVE_CONTROLS_PATH.as_posix(),
        negative_control_manifest_sha256=controls_sha,
        fault_injection_fixture_path=_FAULT_FIXTURES_PATH.as_posix(),
        fault_injection_fixture_sha256=faults_sha,
        privacy_verification_report_path=_PRIVACY_REPORT_PATH.as_posix(),
        privacy_verification_report_sha256=privacy_sha,
        provider_readiness_path=_PROVIDER_READINESS_PATH.as_posix(),
        provider_readiness_sha256=_file_sha256(repo_root, _PROVIDER_READINESS_PATH),
        cross_condition_isolation_path=_ISOLATION_REPORT_PATH.as_posix(),
        cross_condition_isolation_sha256=isolation_sha,
        cost_budget_decision_path=_COST_BUDGET_PATH.as_posix(),
        cost_budget_decision_sha256=_file_sha256(repo_root, _COST_BUDGET_PATH),
        execution_manifest_path=_EXECUTION_MANIFEST_PATH.as_posix(),
        execution_manifest_file_sha256=_file_sha256(repo_root, _EXECUTION_MANIFEST_PATH),
        execution_manifest_canonical_sha256=(
            execution_manifest.identity.execution_manifest_sha256 or ""
        ),
        freeze_report_path=_FREEZE_REPORT_PATH.as_posix(),
        freeze_report_sha256=_file_sha256(repo_root, _FREEZE_REPORT_PATH),
        implementation_git_sha=implementation_git_sha,
        gate_10_passed=True,
        execution_enabled=False,
        measured_execution_permitted=False,
    )
    (repo_root / _GATE10_MANIFEST_PATH).write_bytes(model_json_bytes(gate10_manifest))
    return ExecutionFreezeSummary(
        command="freeze",
        provider_probe_passed=True,
        execution_manifest_frozen=True,
        gate_10_passed=True,
        approved_cost_budget_minor_units=budget.approved_cost_budget_minor_units,
        estimated_upper_bound_minor_units=budget.estimated_upper_bound_minor_units,
        currency=budget.currency,
        execution_manifest_sha256=execution_manifest.identity.execution_manifest_sha256,
        implementation_git_sha=implementation_git_sha,
    )


def verify_frozen_assets(repo_root: Path) -> ExecutionFreezeSummary:
    """Verify the complete frozen manifest and Gate 10 artifact inventory."""

    pricing, _controls, _faults, privacy = _static_assets(repo_root)
    provider = load_model(repo_root / _PROVIDER_READINESS_PATH, ProviderReadinessRecord)
    isolation = load_model(repo_root / _ISOLATION_REPORT_PATH, CrossConditionIsolationReport)
    budget = load_model(repo_root / _COST_BUDGET_PATH, CostBudgetDecision)
    execution_manifest = load_model(
        repo_root / _EXECUTION_MANIFEST_PATH,
        BenchmarkExecutionManifest,
    )
    report = load_model(repo_root / _FREEZE_REPORT_PATH, ExecutionManifestFreezeReport)
    gate10 = load_model(
        repo_root / _GATE10_MANIFEST_PATH,
        Gate10ExecutionFreezeManifest,
    )
    ledger = load_model(repo_root / _GATE9_PLAN_PATH, PlannedRunLedger)
    expected_isolation = build_isolation_report(ledger)
    expected_budget = estimate_cost_budget(
        pricing=pricing,
        maximum_request_attempt_count=ledger.maximum_request_attempt_count,
        approved_cost_budget_minor_units=budget.approved_cost_budget_minor_units,
    )
    if isolation != expected_isolation or budget != expected_budget:
        raise ExecutionFreezeError(
            "FREEZE_ARTIFACT_MISMATCH",
            "Derived isolation or cost evidence is not reproducible.",
        )
    canonical_sha = canonical_execution_manifest_sha256(execution_manifest)
    if canonical_sha != execution_manifest.identity.execution_manifest_sha256:
        raise ExecutionFreezeError(
            "EXECUTION_MANIFEST_HASH_MISMATCH",
            "The frozen execution-manifest self-hash does not reproduce.",
        )
    expected_hashes = {
        gate10.gate9_manifest_path: gate10.gate9_manifest_sha256,
        gate10.pricing_schedule_path: gate10.pricing_schedule_sha256,
        gate10.negative_control_manifest_path: gate10.negative_control_manifest_sha256,
        gate10.fault_injection_fixture_path: gate10.fault_injection_fixture_sha256,
        gate10.privacy_verification_report_path: gate10.privacy_verification_report_sha256,
        gate10.provider_readiness_path: gate10.provider_readiness_sha256,
        gate10.cross_condition_isolation_path: gate10.cross_condition_isolation_sha256,
        gate10.cost_budget_decision_path: gate10.cost_budget_decision_sha256,
        gate10.execution_manifest_path: gate10.execution_manifest_file_sha256,
        gate10.freeze_report_path: gate10.freeze_report_sha256,
    }
    mismatches = tuple(
        path
        for path, expected_sha in expected_hashes.items()
        if _file_sha256(repo_root, Path(path)) != expected_sha
    )
    if mismatches:
        raise ExecutionFreezeError(
            "FREEZE_ARTIFACT_MISMATCH",
            "One or more frozen execution artifacts changed.",
            details=mismatches,
        )
    if gate10.execution_manifest_canonical_sha256 != canonical_sha:
        raise ExecutionFreezeError(
            "EXECUTION_MANIFEST_HASH_MISMATCH",
            "Gate 10 and execution-manifest canonical digests differ.",
        )
    if report.execution_manifest_sha256 != canonical_sha or not report.gate_10_passed:
        raise ExecutionFreezeError(
            "FREEZE_ARTIFACT_MISMATCH",
            "The persisted freeze report does not match the frozen manifest.",
        )
    if not provider.probe_passed or not privacy.privacy_verification_passed:
        raise ExecutionFreezeError(
            "FREEZE_ARTIFACT_MISMATCH",
            "Provider or privacy readiness evidence no longer passes.",
        )
    return ExecutionFreezeSummary(
        command="verify",
        provider_probe_passed=True,
        execution_manifest_frozen=True,
        gate_10_passed=True,
        approved_cost_budget_minor_units=budget.approved_cost_budget_minor_units,
        estimated_upper_bound_minor_units=budget.estimated_upper_bound_minor_units,
        currency=budget.currency,
        execution_manifest_sha256=canonical_sha,
        implementation_git_sha=gate10.implementation_git_sha,
    )
