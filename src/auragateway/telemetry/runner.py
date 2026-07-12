"""Build and verify deterministic provider telemetry and Gate 4 sufficiency evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.telemetry import (
    CacheEvidenceLevel,
    ClaimKind,
    Gate4FixtureResult,
    Gate4TelemetryManifest,
    Gate4TelemetryReport,
    Gate4TelemetrySummary,
    NormalizedTelemetry,
    PricingSchedule,
    TelemetryFixtureCase,
    TelemetryFixtureSet,
    TelemetrySemanticFamily,
    UnavailableTelemetry,
)
from auragateway.providers.fake import FakeProviderAdapter, FakeProviderError
from auragateway.telemetry.normalize import normalize_telemetry
from auragateway.telemetry.sufficiency import assess_telemetry_sufficiency

_DEFAULT_FIXTURES = Path("data/provider_fixtures/telemetry/fixtures.json")
_DEFAULT_REPORT = Path("data/provider_fixtures/telemetry/report.json")
_DEFAULT_MANIFEST = Path("data/provider_fixtures/telemetry/manifest.json")


class TelemetryIntegrityError(Exception):
    """Expected Gate 4 failure with bounded, metadata-only diagnostics."""

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


class TelemetryIntegrityErrorEnvelope(BaseModel):
    """Safe CLI failure envelope that excludes raw provider payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


ModelT = TypeVar("ModelT", bound=BaseModel)


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, not_found_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TelemetryIntegrityError(
            not_found_code,
            "Required Gate 4 telemetry artifact was not found.",
            str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TelemetryIntegrityError(
            "TELEMETRY_ARTIFACT_INVALID_JSON",
            "Gate 4 telemetry artifact is not valid JSON.",
            str(path),
        ) from exc


def _load_model(path: Path, model_type: type[ModelT], code: str) -> ModelT:
    try:
        return model_type.model_validate(_load_json(path, f"{code}_NOT_FOUND"))
    except ValidationError as exc:
        raise TelemetryIntegrityError(
            f"{code}_VALIDATION_FAILED",
            "Gate 4 telemetry artifact failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        model.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pricing_for(
    case: TelemetryFixtureCase, schedules: dict[str, PricingSchedule]
) -> PricingSchedule | None:
    if case.pricing_schedule_id is None:
        return None
    return schedules[case.pricing_schedule_id]


def _expectations_match(case: TelemetryFixtureCase, report: object) -> bool:
    if not hasattr(report, "decision_for"):
        return False
    return all(
        (decision := report.decision_for(expectation.claim_kind)).decision is expectation.decision
        and decision.reason_code is expectation.reason_code
        for expectation in case.expectations
    )


def _unknown_values_preserved(case: TelemetryFixtureCase, normalized: NormalizedTelemetry) -> bool:
    if isinstance(case.telemetry, UnavailableTelemetry):
        measurable = (
            normalized.accounting_input_tokens,
            normalized.provider_input_tokens,
            normalized.provider_output_tokens,
            normalized.provider_cached_input_tokens,
            normalized.provider_uncached_input_tokens,
            normalized.provider_cache_creation_input_tokens,
            normalized.provider_cache_read_input_tokens,
            normalized.local_prompt_eval_count,
            normalized.local_prompt_eval_duration_ms,
            normalized.time_to_first_output_ms,
            normalized.total_duration_ms,
        )
        return all(value is None for value in measurable)
    if case.telemetry.semantic_family is TelemetrySemanticFamily.CACHED_INPUT_DETAIL:
        raw_cached = case.telemetry.cached_input_tokens
        return raw_cached is not None or normalized.provider_cached_input_tokens is None
    return True


def _semantics_preserved(normalized: NormalizedTelemetry) -> bool:
    if normalized.semantic_family is TelemetrySemanticFamily.CACHED_INPUT_DETAIL:
        return (
            normalized.denominator_kind.value == "provider_input_total"
            and normalized.provider_cache_creation_input_tokens is None
            and normalized.provider_cache_read_input_tokens is None
            and normalized.local_prompt_eval_count is None
        )
    if normalized.semantic_family is TelemetrySemanticFamily.CACHE_CREATION_READ:
        return (
            normalized.denominator_kind.value == "provider_component_sum"
            and normalized.provider_cached_input_tokens is None
            and normalized.local_prompt_eval_count is None
        )
    if normalized.semantic_family is TelemetrySemanticFamily.LOCAL_PROMPT_EVALUATION:
        return (
            normalized.evidence_level is CacheEvidenceLevel.INFERRED_LOCAL
            and normalized.provider_cached_input_tokens is None
            and normalized.provider_cache_creation_input_tokens is None
            and normalized.provider_cache_read_input_tokens is None
        )
    return normalized.evidence_level is CacheEvidenceLevel.UNAVAILABLE


def _build_report(fixtures: TelemetryFixtureSet) -> Gate4TelemetryReport:
    adapter = FakeProviderAdapter(fixtures)
    schedules = {schedule.schedule_id: schedule for schedule in fixtures.pricing_schedules}
    results: list[Gate4FixtureResult] = []
    unknowns_preserved = True
    semantics_preserved = True
    local_separation = True

    for case in fixtures.cases:
        try:
            call = adapter.invoke(case.request)
        except FakeProviderError as exc:
            raise TelemetryIntegrityError(
                exc.error_code.value,
                exc.safe_message,
                details=(case.case_id,),
            ) from exc
        if call.result.output_sha256 is None:
            raise TelemetryIntegrityError(
                "FAKE_PROVIDER_OUTPUT_DIGEST_MISSING",
                "Deterministic provider result did not contain an output digest.",
                details=(case.case_id,),
            )
        normalized = normalize_telemetry(call.telemetry)
        sufficiency = assess_telemetry_sufficiency(
            normalized,
            _pricing_for(case, schedules),
        )
        expectations_matched = _expectations_match(case, sufficiency)
        unknowns_preserved = unknowns_preserved and _unknown_values_preserved(case, normalized)
        semantics_preserved = semantics_preserved and _semantics_preserved(normalized)
        if normalized.evidence_level is CacheEvidenceLevel.INFERRED_LOCAL:
            cache_decision = sufficiency.decision_for(ClaimKind.CACHE_EFFICIENCY)
            local_separation = local_separation and cache_decision.decision.value == "blocked"
        results.append(
            Gate4FixtureResult(
                case_id=case.case_id,
                semantic_family=normalized.semantic_family,
                evidence_level=normalized.evidence_level,
                invocation_output_sha256=call.result.output_sha256,
                normalized_telemetry=normalized,
                sufficiency=sufficiency,
                expectations_matched=expectations_matched,
                negative_control=case.negative_control,
            )
        )

    all_expectations_matched = all(result.expectations_matched for result in results)
    gate_passed = (
        all_expectations_matched and semantics_preserved and unknowns_preserved and local_separation
    )
    return Gate4TelemetryReport(
        status="passed" if gate_passed else "failed",
        fixture_set_id=fixtures.fixture_set_id,
        results=tuple(results),
        fixture_count=len(results),
        negative_control_count=sum(result.negative_control for result in results),
        all_expectations_matched=all_expectations_matched,
        provider_semantics_preserved=semantics_preserved,
        unknown_values_remained_none=unknowns_preserved,
        local_timing_separated_from_provider_cache=local_separation,
        gate_4_passed=gate_passed,
    )


def _summary(
    fixtures_path: Path,
    report_path: Path,
    report: Gate4TelemetryReport,
) -> Gate4TelemetrySummary:
    return Gate4TelemetrySummary(
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        gate_4_passed=report.gate_4_passed,
        measured_execution_permitted=report.measured_execution_permitted,
        fixture_sha256=_sha256_path(fixtures_path),
        report_sha256=_sha256_path(report_path),
    )


def build_telemetry_integrity(repo_root: Path) -> Gate4TelemetrySummary:
    """Build deterministic Gate 4 report and frozen artifact manifest."""

    fixtures_path = repo_root / _DEFAULT_FIXTURES
    report_path = repo_root / _DEFAULT_REPORT
    manifest_path = repo_root / _DEFAULT_MANIFEST
    fixtures = _load_model(fixtures_path, TelemetryFixtureSet, "TELEMETRY_FIXTURE_SET")
    report = _build_report(fixtures)
    if not report.gate_4_passed:
        raise TelemetryIntegrityError(
            "GATE_4_TELEMETRY_INTEGRITY_FAILED",
            "Deterministic telemetry fixtures did not satisfy Gate 4.",
        )
    _write_model(report_path, report)
    manifest = Gate4TelemetryManifest(
        fixture_path=_DEFAULT_FIXTURES.as_posix(),
        fixture_sha256=_sha256_path(fixtures_path),
        report_path=_DEFAULT_REPORT.as_posix(),
        report_sha256=_sha256_path(report_path),
        fixture_count=report.fixture_count,
        negative_control_count=report.negative_control_count,
        gate_4_passed=report.gate_4_passed,
    )
    _write_model(manifest_path, manifest)
    return _summary(fixtures_path, report_path, report)


def verify_telemetry_integrity(repo_root: Path) -> Gate4TelemetrySummary:
    """Verify frozen Gate 4 hashes and deterministic report parity."""

    fixtures_path = repo_root / _DEFAULT_FIXTURES
    report_path = repo_root / _DEFAULT_REPORT
    manifest_path = repo_root / _DEFAULT_MANIFEST
    manifest = _load_model(manifest_path, Gate4TelemetryManifest, "TELEMETRY_MANIFEST")
    if _sha256_path(fixtures_path) != manifest.fixture_sha256:
        raise TelemetryIntegrityError(
            "TELEMETRY_FIXTURE_HASH_MISMATCH",
            "Telemetry fixture hash does not match the frozen manifest.",
            str(fixtures_path),
        )
    if _sha256_path(report_path) != manifest.report_sha256:
        raise TelemetryIntegrityError(
            "TELEMETRY_REPORT_HASH_MISMATCH",
            "Telemetry report hash does not match the frozen manifest.",
            str(report_path),
        )
    fixtures = _load_model(fixtures_path, TelemetryFixtureSet, "TELEMETRY_FIXTURE_SET")
    frozen_report = _load_model(report_path, Gate4TelemetryReport, "TELEMETRY_REPORT")
    rebuilt_report = _build_report(fixtures)
    if rebuilt_report != frozen_report:
        raise TelemetryIntegrityError(
            "TELEMETRY_REPORT_REPRODUCTION_MISMATCH",
            "Rebuilt telemetry report does not match the frozen report.",
            str(report_path),
        )
    if (
        manifest.fixture_count != frozen_report.fixture_count
        or manifest.negative_control_count != frozen_report.negative_control_count
        or manifest.gate_4_passed != frozen_report.gate_4_passed
    ):
        raise TelemetryIntegrityError(
            "TELEMETRY_MANIFEST_REPORT_MISMATCH",
            "Telemetry manifest does not match the frozen report summary.",
            str(manifest_path),
        )
    return _summary(fixtures_path, report_path, frozen_report)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the Gate 4 builder or verifier with safe JSON output."""

    args = _parse_args(argv)
    try:
        if args.command == "build":
            summary = build_telemetry_integrity(args.repo_root)
        else:
            summary = verify_telemetry_integrity(args.repo_root)
    except TelemetryIntegrityError as exc:
        envelope = TelemetryIntegrityErrorEnvelope(
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
