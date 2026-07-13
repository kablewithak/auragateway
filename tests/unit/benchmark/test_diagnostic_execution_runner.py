from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.diagnostic_execution_runner import (
    DiagnosticExecutionError,
    execute_authorized_diagnostic,
    live_preflight,
    validate_activation,
    verify_execution,
)
from auragateway.benchmark.diagnostic_fixture_runner import (
    materialize_diagnostic_fixtures,
)
from auragateway.contracts.provider import (
    ProviderErrorCode,
    ProviderInvocationResult,
    ProviderInvocationStatus,
    ProviderName,
)
from auragateway.contracts.telemetry import CachedInputDetailTelemetry
from auragateway.providers.base import (
    LiveProviderError,
    LiveProviderInvocation,
    ProtectedProviderOutput,
    ProviderCall,
)

_DESIGN_ROOT = Path("data/evals/benchmark/diagnostic-design-v1")
_FIXTURE_ROOT = Path("data/evals/benchmark/diagnostic-fixtures-v1")
_REVIEW_ROOT = Path("data/evals/benchmark/diagnostic-authorization-review-v1")
_EXECUTION_ROOT = Path("data/evals/benchmark/diagnostic-execution-v1")
_BATCH06_ROOT = Path("data/evals/benchmark/live-development-v6")


class _FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class _FakeAdapter:
    def __init__(
        self,
        *,
        error_call_index: int | None = None,
        error_code: ProviderErrorCode = ProviderErrorCode.REQUEST_REJECTED,
    ) -> None:
        self.error_call_index = error_call_index
        self.error_code = error_code
        self.calls: list[LiveProviderInvocation] = []

    def invoke(self, invocation: LiveProviderInvocation) -> ProviderCall:
        call_index = len(self.calls)
        self.calls.append(invocation)
        if call_index == self.error_call_index:
            raise LiveProviderError(
                self.error_code,
                "synthetic bounded provider error",
                retryable=False,
            )

        protected_output = ProtectedProviderOutput(
            text=('{"citation_ids":["SYN-001"],"decision":"answer","response":"synthetic"}')
        )
        result = ProviderInvocationResult(
            request_id=invocation.request.request_id,
            provider=ProviderName.GROQ,
            model_alias=invocation.request.model_alias,
            status=ProviderInvocationStatus.SUCCEEDED,
            output_sha256=protected_output.sha256,
        )
        telemetry = CachedInputDetailTelemetry(
            fixture_id=invocation.request.fixture_id,
            provider=ProviderName.GROQ,
            model_alias=invocation.request.model_alias,
            input_tokens=invocation.request.input_token_count,
            cached_input_tokens=0,
            output_tokens=8,
            total_duration_ms=10,
        )
        return ProviderCall(
            result=result,
            telemetry=telemetry,
            protected_output=protected_output,
        )


def _copy_file(repo_root: Path, relative_path: Path) -> None:
    destination = repo_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(relative_path, destination)


def _repo_fixture(tmp_path: Path) -> Path:
    for relative_path in (
        _DESIGN_ROOT / "experiment_plan.json",
        _DESIGN_ROOT / "manifest.json",
        _FIXTURE_ROOT / "fixture_recipe.json",
        _FIXTURE_ROOT / "fixture_manifest.json",
        _REVIEW_ROOT / "review_package.json",
        _REVIEW_ROOT / "dry_run_report.json",
        _REVIEW_ROOT / "manifest.json",
        _EXECUTION_ROOT / "authorization.json",
        _EXECUTION_ROOT / "runtime_policy.json",
        _BATCH06_ROOT / "manifest.json",
        _BATCH06_ROOT / "report.json",
    ):
        _copy_file(tmp_path, relative_path)

    materialize_diagnostic_fixtures(tmp_path)
    return tmp_path


def _load_json(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_validate_activation_is_non_live(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    summary = validate_activation(repo_root)

    assert summary.command == "validate"
    assert summary.authorization_status.value == "active"
    assert summary.provider_call_count == 0
    assert summary.credential_checked is False
    assert summary.provider_calls_permitted is False
    assert summary.execution_completed is False


def test_live_preflight_requires_deliberate_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(
        DiagnosticExecutionError,
        match="must be loaded deliberately",
    ):
        live_preflight(repo_root)


def test_live_preflight_checks_credential_without_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-only")

    summary = live_preflight(repo_root)

    assert summary.command == "live-preflight"
    assert summary.credential_checked is True
    assert summary.provider_call_count == 0
    assert summary.live_provider_called is False


def test_all_success_execution_accounts_for_24_calls(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter()
    clock = _FakeClock()

    summary = execute_authorized_diagnostic(
        repo_root,
        adapter=adapter,
        confirmation_phrase="EXECUTE_BATCH_06_DIAGNOSTIC_ONCE",
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    verified = verify_execution(repo_root)

    assert summary.command == "run"
    assert summary.provider_call_count == 24
    assert len(adapter.calls) == 24
    assert clock.value == 2220
    assert verified.command == "verify"

    report = _load_json(repo_root / _EXECUTION_ROOT / "report.json")
    assert report["completed_sequence_count"] == 8
    assert report["provider_error_count"] == 0
    assert report["estimated_cost_microusd"] == 4992


def test_request_rejection_stops_sequence_and_continues_plan(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter(
        error_call_index=1,
        error_code=ProviderErrorCode.REQUEST_REJECTED,
    )
    clock = _FakeClock()

    summary = execute_authorized_diagnostic(
        repo_root,
        adapter=adapter,
        confirmation_phrase="EXECUTE_BATCH_06_DIAGNOSTIC_ONCE",
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    assert summary.provider_call_count == 23
    report = _load_json(repo_root / _EXECUTION_ROOT / "report.json")
    assert report["request_rejected_sequence_count"] == 1
    assert report["completed_sequence_count"] == 7
    assert report["skipped_attempt_count"] == 1


def test_systemic_error_stops_experiment_without_retry(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter(
        error_call_index=0,
        error_code=ProviderErrorCode.UNAVAILABLE,
    )
    clock = _FakeClock()

    summary = execute_authorized_diagnostic(
        repo_root,
        adapter=adapter,
        confirmation_phrase="EXECUTE_BATCH_06_DIAGNOSTIC_ONCE",
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    assert summary.provider_call_count == 1
    assert len(adapter.calls) == 1
    report = _load_json(repo_root / _EXECUTION_ROOT / "report.json")
    assert report["experiment_stopped_sequence_count"] == 1
    assert report["not_started_sequence_count"] == 7
    assert report["skipped_attempt_count"] == 23


def test_exact_confirmation_phrase_is_required(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    with pytest.raises(
        DiagnosticExecutionError,
        match="exact one-time",
    ):
        execute_authorized_diagnostic(
            repo_root,
            adapter=_FakeAdapter(),
            confirmation_phrase="execute",
        )


def test_existing_journal_blocks_second_execution(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    adapter = _FakeAdapter()
    clock = _FakeClock()
    execute_authorized_diagnostic(
        repo_root,
        adapter=adapter,
        confirmation_phrase="EXECUTE_BATCH_06_DIAGNOSTIC_ONCE",
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    with pytest.raises(
        DiagnosticExecutionError,
        match="fresh evidence boundary",
    ):
        execute_authorized_diagnostic(
            repo_root,
            adapter=_FakeAdapter(),
            confirmation_phrase="EXECUTE_BATCH_06_DIAGNOSTIC_ONCE",
        )


def test_public_evidence_excludes_protected_output_text(
    tmp_path: Path,
) -> None:
    repo_root = _repo_fixture(tmp_path)
    clock = _FakeClock()
    execute_authorized_diagnostic(
        repo_root,
        adapter=_FakeAdapter(),
        confirmation_phrase="EXECUTE_BATCH_06_DIAGNOSTIC_ONCE",
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    public_text = "\n".join(
        (
            (repo_root / _EXECUTION_ROOT / "journal.jsonl").read_text(encoding="utf-8"),
            (repo_root / _EXECUTION_ROOT / "run_records.json").read_text(encoding="utf-8"),
            (repo_root / _EXECUTION_ROOT / "report.json").read_text(encoding="utf-8"),
            (repo_root / _EXECUTION_ROOT / "manifest.json").read_text(encoding="utf-8"),
        )
    )
    assert '"response":"synthetic"' not in public_text
    assert '"output_text":' not in public_text

    protected_text = (
        repo_root / ".local/benchmark/diagnostic-execution-v1/provider_raw_outputs.jsonl"
    ).read_text(encoding="utf-8")
    assert '"output_text":' in protected_text
