from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from auragateway.contracts.provider import ProtectedPromptSummary, ProviderName
from auragateway.contracts.telemetry import (
    CachedInputDetailTelemetry,
    ClaimDecision,
    ClaimKind,
    TelemetryReasonCode,
)
from auragateway.providers.calibration_runner import (
    CalibrationCallEvidence,
    ProviderCalibrationConfig,
    _report,
    main,
    validate_calibration,
)
from auragateway.telemetry.normalize import normalize_telemetry
from auragateway.telemetry.sufficiency import assess_telemetry_sufficiency


def test_deterministic_calibration_replays_both_provider_boundaries() -> None:
    summary = validate_calibration(Path("."))
    assert summary.calibration_passed is True
    assert summary.call_count == 4
    assert summary.provider_cached_tokens_observed is True
    assert summary.local_prompt_timing_observed is True
    assert summary.report_path is None
    assert summary.measured_execution_permitted is False


def test_validate_cli_emits_sanitized_summary(capsys: object) -> None:
    assert main(["validate", "--repo-root", "."]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert payload["calibration_passed"] is True
    assert "Nimbus Relay" not in captured.out
    assert "READY-1" not in captured.out


def test_config_rejects_paid_or_execution_enabled_mode() -> None:
    payload = json.loads(
        Path("data/provider_fixtures/live-calibration/config.json").read_text(encoding="utf-8")
    )
    payload["free_plan_only"] = False
    try:
        ProviderCalibrationConfig.model_validate(payload)
    except ValidationError as exc:
        assert "free-plan only" in str(exc)
    else:
        raise AssertionError("paid calibration mode was accepted")


def test_config_allows_measured_cpu_local_timeout_ceiling() -> None:
    payload = json.loads(
        Path("data/provider_fixtures/live-calibration/config.json").read_text(encoding="utf-8")
    )
    config = ProviderCalibrationConfig.model_validate(payload)
    assert config.groq_timeout_seconds == 60
    assert config.ollama_timeout_seconds == 300


def test_config_rejects_ollama_timeout_above_local_ceiling() -> None:
    payload = json.loads(
        Path("data/provider_fixtures/live-calibration/config.json").read_text(encoding="utf-8")
    )
    payload["ollama_timeout_seconds"] = 301
    try:
        ProviderCalibrationConfig.model_validate(payload)
    except ValidationError as exc:
        assert "less than or equal to 300" in str(exc)
    else:
        raise AssertionError("unbounded Ollama timeout was accepted")


def _config() -> ProviderCalibrationConfig:
    payload = json.loads(
        Path("data/provider_fixtures/live-calibration/config.json").read_text(encoding="utf-8")
    )
    return ProviderCalibrationConfig.model_validate(payload)


def _groq_evidence(
    fixture_id: str,
    *,
    input_tokens: int | None = 1_633,
    cached_tokens: int | None = None,
) -> CalibrationCallEvidence:
    telemetry = CachedInputDetailTelemetry(
        fixture_id=fixture_id,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=16,
        total_duration_ms=98,
    )
    normalized = normalize_telemetry(telemetry)
    return CalibrationCallEvidence(
        request_id=f"{fixture_id}-request",
        fixture_id=fixture_id,
        provider=ProviderName.GROQ,
        model_alias="groq-gpt-oss-20b",
        prompt_summary=ProtectedPromptSummary(
            system_sha256="a" * 64,
            user_sha256="b" * 64,
            total_bytes=8_756,
        ),
        output_sha256="c" * 64,
        telemetry=telemetry,
        normalized_telemetry=normalized,
        sufficiency=assess_telemetry_sufficiency(normalized),
    )


def test_groq_live_report_accepts_omitted_cache_detail_without_inventing_zero() -> None:
    report = _report(
        "groq_live",
        _config(),
        (
            _groq_evidence("groq-live-turn-1"),
            _groq_evidence("groq-live-turn-2"),
        ),
    )
    assert report.status == "passed"
    assert report.provider_cached_tokens_observed is False
    cache_decision = report.calls[0].sufficiency.decision_for(ClaimKind.CACHE_EFFICIENCY)
    assert cache_decision.decision is ClaimDecision.BLOCKED
    assert cache_decision.reason_code is TelemetryReasonCode.CACHE_EVIDENCE_UNAVAILABLE
    assert cache_decision.missing_fields == ("provider_cached_input_tokens",)


def test_groq_live_report_rejects_missing_prompt_token_accounting() -> None:
    report = _report(
        "groq_live",
        _config(),
        (
            _groq_evidence("groq-live-turn-1", input_tokens=None),
            _groq_evidence("groq-live-turn-2", input_tokens=None),
        ),
    )
    assert report.status == "failed"
