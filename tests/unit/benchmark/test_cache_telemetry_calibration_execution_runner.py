from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.cache_telemetry_calibration_execution_runner import (
    CalibrationExecutionError,
    execute_calibration,
    live_preflight_calibration_execution,
    validate_calibration_execution,
    verify_calibration_execution,
)
from auragateway.benchmark.cache_telemetry_calibration_review_runner import (
    _protected_bundle_bytes,
)
from auragateway.contracts.cache_telemetry_capture import (
    GroqCacheTelemetryCapture,
)
from auragateway.contracts.provider import (
    ProviderInvocationResult,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.providers.base import (
    LiveProviderInvocation,
    ProtectedProviderOutput,
    ProviderCall,
)

_EXECUTION_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-v1")
_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-review-v1")


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


class _FakeAdapter:
    def __init__(
        self,
        cache_values: tuple[int | None, int | None, int | None],
        *,
        field_present: bool = True,
    ) -> None:
        self._cache_values = cache_values
        self._field_present = field_present
        self.call_count = 0

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        index = self.call_count
        self.call_count += 1
        value = self._cache_values[index]
        request = invocation.request
        output = ProtectedProviderOutput(f"CACHE_TELEMETRY_OK_{index}")
        shape = GroqCacheTelemetryCapture(
            fixture_id=request.fixture_id,
            model_alias=request.model_alias,
            installed_sdk_version="1.6.0",
            usage_present=True,
            prompt_tokens_details_present=self._field_present,
            billing_cached_tokens_field_present=self._field_present,
            billing_cached_input_tokens=value,
            x_groq_present=False,
            x_groq_usage_present=False,
            dram_cached_tokens_field_present=False,
            sram_cached_tokens_field_present=False,
        )
        telemetry = CachedInputDetailTelemetry(
            fixture_id=request.fixture_id,
            provider=ProviderName.GROQ,
            model_alias=request.model_alias,
            input_tokens=2112,
            cached_input_tokens=value,
            output_tokens=4,
            total_duration_ms=150,
        )
        result = ProviderInvocationResult(
            request_id=request.request_id,
            provider=ProviderName.GROQ,
            model_alias=request.model_alias,
            status=ProviderInvocationStatus.SUCCEEDED,
            output_sha256=output.sha256,
        )
        return ProviderCall(
            result=result,
            telemetry=telemetry,
            protected_output=output,
            success_telemetry_shape=shape,
        )


def _copy_review_assets(repo_root: Path) -> None:
    for name in (
        "prompt_recipe.json",
        "review.json",
        "dry_run_report.json",
        "manifest.json",
    ):
        source = _REVIEW_ROOT / name
        destination = repo_root / _REVIEW_ROOT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def _copy_execution_assets(repo_root: Path) -> None:
    for name in ("authorization.json", "runtime_policy.json"):
        source = _EXECUTION_ROOT / name
        destination = repo_root / _EXECUTION_ROOT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def _repo_fixture(tmp_path: Path) -> Path:
    _copy_review_assets(tmp_path)
    _copy_execution_assets(tmp_path)
    protected = tmp_path / ".local/benchmark/cache-telemetry-calibration-v1/prompt_bundle.json"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_bytes(_protected_bundle_bytes())
    return tmp_path


def test_validate_accepts_active_authorization(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    summary = validate_calibration_execution(repo_root)

    assert summary.command == "validate"
    assert summary.provider_call_count == 0
    assert summary.execution_completed is False
    assert summary.credential_checked is False
    assert summary.provider_calls_permitted is False


def test_live_preflight_requires_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(
        CalibrationExecutionError,
        match="not available",
    ):
        live_preflight_calibration_execution(repo_root)


def test_live_preflight_performs_no_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-key")

    summary = live_preflight_calibration_execution(repo_root)

    assert summary.provider_call_count == 0
    assert summary.live_provider_called is False
    assert summary.credential_checked is True


def test_execute_classifies_observed_cache_hit(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter((0, 1024, 1024))
    clock = _Clock()

    summary = execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=adapter,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    assert summary.provider_call_count == 3
    assert summary.execution_completed is True
    report = cast(
        dict[str, object],
        json.loads((repo_root / _EXECUTION_ROOT / "report.json").read_text(encoding="utf-8")),
    )
    assert report["outcome"] == "telemetry_observed_with_cache_hit"
    assert report["warm_positive_cache_sample_count"] == 2


def test_execute_classifies_measured_zero(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter((0, 0, 0))
    clock = _Clock()

    execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=adapter,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    report = json.loads((repo_root / _EXECUTION_ROOT / "report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == ("telemetry_observed_without_cache_hit")


def test_execute_classifies_unavailable_field(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter(
        (None, None, None),
        field_present=False,
    )
    clock = _Clock()

    execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=adapter,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    report = json.loads((repo_root / _EXECUTION_ROOT / "report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == "billing_cache_field_unavailable"
    assert report["provider_cache_usage_claim_permitted_for_calibration"] is False


def test_execute_requires_exact_confirmation(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    with pytest.raises(
        CalibrationExecutionError,
        match="exact one-time execution confirmation",
    ):
        execute_calibration(
            repo_root,
            authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
            confirmation="WRONG",
            adapter=_FakeAdapter((0, 0, 0)),
        )


def test_execute_blocks_rerun(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    clock = _Clock()
    adapter = _FakeAdapter((0, 0, 0))

    execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=adapter,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    with pytest.raises(
        CalibrationExecutionError,
        match="rerun and resume are forbidden",
    ):
        execute_calibration(
            repo_root,
            authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
            confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
            adapter=adapter,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )


def test_verify_reconciles_journal_hashes_and_report(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    clock = _Clock()

    execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=_FakeAdapter((0, 512, 512)),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    summary = verify_calibration_execution(repo_root)

    assert summary.command == "verify"
    assert summary.provider_call_count == 3
    assert summary.provider_calls_permitted is False


def test_verify_rejects_journal_drift(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    clock = _Clock()

    execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=_FakeAdapter((0, 0, 0)),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    journal = repo_root / _EXECUTION_ROOT / "journal.jsonl"
    journal.write_text(
        journal.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CalibrationExecutionError,
        match="exactly three records",
    ):
        verify_calibration_execution(repo_root)


def test_protected_outputs_are_not_public_evidence(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    clock = _Clock()

    execute_calibration(
        repo_root,
        authorization_id=("groq-cache-telemetry-calibration-auth-v1"),
        confirmation=("EXECUTE_GROQ_CACHE_TELEMETRY_CALIBRATION_ONCE"),
        adapter=_FakeAdapter((0, 0, 0)),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    public_text = "\n".join(
        (repo_root / _EXECUTION_ROOT / name).read_text(encoding="utf-8")
        for name in (
            "journal.jsonl",
            "run_records.json",
            "report.json",
            "manifest.json",
        )
    )
    assert "CACHE_TELEMETRY_OK" not in public_text
    protected = repo_root / ".local/benchmark/cache-telemetry-calibration-v1/provider_outputs.jsonl"
    assert "CACHE_TELEMETRY_OK" in protected.read_text(encoding="utf-8")
