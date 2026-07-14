from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import auragateway.benchmark.openrouter_hy3_capability_probe_execution_runner as runner
from auragateway.contracts.openrouter_hy3_capability_probe_activation import (
    OpenRouterProbeActivationAuthorization,
    OpenRouterProbeActivationRuntimePolicy,
    OpenRouterProbePreflightReceipt,
    OpenRouterProbeProtectedCall,
    OpenRouterProbeProtectedPromptBundle,
)
from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeAttemptContext,
    OpenRouterProbeExecutionPolicy,
    OpenRouterProbeExecutionSummary,
    OpenRouterProbeJournalEventType,
    OpenRouterProbeJournalRecord,
    OpenRouterProbeTerminalOutcome,
)
from auragateway.providers.openrouter_http import (
    OpenRouterHttpResponse,
)
from auragateway.providers.openrouter_recording import (
    OpenRouterRawResponseWriter,
    RecordingOpenRouterTransport,
)


class _Git:
    def inspect(self, repo_root: Path) -> tuple[str, str, bool]:
        del repo_root
        return "main", "a" * 40, True


class _Clock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 14, 10, tzinfo=UTC)

    def __call__(self) -> datetime:
        observed = self.current
        self.current += timedelta(seconds=1)
        return observed


class _Backend:
    def __init__(self, responses: list[OpenRouterHttpResponse]) -> None:
        self.responses = responses

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        del method, url, headers, body, timeout_seconds
        return self.responses.pop(0)


class _Factory:
    def __init__(self, scenarios: list[list[OpenRouterHttpResponse]]) -> None:
        self.scenarios = scenarios
        self.calls = 0

    def __call__(
        self,
        *,
        api_key: str,
        context: OpenRouterProbeAttemptContext,
        writer: OpenRouterRawResponseWriter,
        clock: Callable[[], datetime],
    ) -> RecordingOpenRouterTransport:
        self.calls += 1
        return RecordingOpenRouterTransport(
            api_key=api_key,
            context=context,
            writer=writer,
            backend=_Backend(self.scenarios.pop(0)),
            clock=clock,
        )


def _response(payload: object, status: int = 200) -> OpenRouterHttpResponse:
    return OpenRouterHttpResponse(
        status_code=status,
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
    )


def _completion(
    *,
    output: str,
    cached: int | None | str = 0,
    written: int | None | str = 0,
    include_details: bool = True,
    model: str = "tencent/hy3",
) -> OpenRouterHttpResponse:
    usage: dict[str, object] = {
        "prompt_tokens": 13000,
        "completion_tokens": 4,
    }
    if include_details:
        usage["prompt_tokens_details"] = {
            "cached_tokens": cached,
            "cache_write_tokens": written,
        }
    return _response(
        {
            "id": "gen-test",
            "model": model,
            "choices": [{"message": {"content": output}}],
            "usage": usage,
        }
    )


def _generation(
    *,
    native: int | None = 0,
    provider: str = "synthetic-provider",
    model: str = "tencent/hy3",
) -> OpenRouterHttpResponse:
    return _response(
        {
            "data": {
                "id": "gen-test",
                "model": model,
                "provider_name": provider,
                "session_id": "auragateway-session-test",
                "native_tokens_cached": native,
                "cache_discount": "0",
            }
        }
    )


def _loaded(tmp_path: Path) -> runner._LoadedExecution:
    authorization = OpenRouterProbeActivationAuthorization.model_validate_json(
        Path(
            "data/evals/benchmark/openrouter-hy3-capability-probe-v1/authorization.json"
        ).read_text(encoding="utf-8")
    )
    activation_policy = OpenRouterProbeActivationRuntimePolicy.model_validate_json(
        Path(
            "data/evals/benchmark/openrouter-hy3-capability-probe-v1/runtime_policy.json"
        ).read_text(encoding="utf-8")
    )
    execution_policy = OpenRouterProbeExecutionPolicy.model_validate_json(
        Path(
            "data/evals/benchmark/openrouter-hy3-capability-probe-execution-v1/"
            "execution_policy.json"
        ).read_text(encoding="utf-8")
    )
    stable_prefix = "stable-prefix-block\n" * 80
    bundle = OpenRouterProbeProtectedPromptBundle(
        bundle_id="openrouter-hy3-capability-probe-prompt-bundle-v1",
        authorization_id=authorization.authorization_id,
        recipe_id="openrouter-hy3-capability-probe-prompt-v1",
        session_id="auragateway-session-test",
        stable_prefix=stable_prefix,
        stable_prefix_sha256="b" * 64,
        stable_prefix_bytes=len(stable_prefix.encode("utf-8")),
        calls=(
            OpenRouterProbeProtectedCall(
                logical_call_index=0,
                request_role="cold_probe",
                request_id="openrouter-hy3-cold-probe-v1",
                fixture_id="openrouter-hy3-cold-probe-v1",
                user_suffix="Return the exact cold acknowledgement.",
                expected_output="COLD-PROBE-ACK",
            ),
            OpenRouterProbeProtectedCall(
                logical_call_index=1,
                request_role="warm_probe",
                request_id="openrouter-hy3-warm-probe-v1",
                fixture_id="openrouter-hy3-warm-probe-v1",
                user_suffix="Return the exact warm acknowledgement.",
                expected_output="WARM-PROBE-ACK",
            ),
        ),
    )
    preflight = OpenRouterProbePreflightReceipt(
        authorization_id=authorization.authorization_id,
        prompt_bundle_sha256="b" * 64,
        key_status_response_sha256="c" * 64,
        model_catalog_response_sha256="d" * 64,
        key_label_sha256="e" * 64,
        limit=Decimal("0"),
        limit_remaining=Decimal("0"),
        usage=Decimal("0"),
        usage_daily=Decimal("0"),
        is_free_tier=True,
    )
    local = tmp_path / ".local/benchmark/openrouter-hy3-capability-probe-v1"
    local.mkdir(parents=True)
    paths = runner._RuntimePaths(
        bundle=local / "prompt_bundle.json",
        preflight=local / "preflight_receipt.json",
        journal=local / "journal.jsonl",
        raw=local / "raw_responses.jsonl",
        parsed=local / "parsed_responses.jsonl",
        terminal=local / "terminal_receipt.json",
    )
    paths.bundle.write_text(bundle.model_dump_json(indent=2) + "\n", encoding="utf-8")
    paths.preflight.write_text(
        preflight.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    paths.journal.write_bytes(b"")
    paths.raw.write_bytes(b"")
    paths.parsed.write_bytes(b"")
    return runner._LoadedExecution(
        authorization=authorization,
        activation_policy=activation_policy,
        execution_policy=execution_policy,
        bundle=bundle,
        preflight=preflight,
        paths=paths,
    )


def _patch_loaded(monkeypatch: pytest.MonkeyPatch, loaded: runner._LoadedExecution) -> None:
    monkeypatch.setattr(runner, "_load_execution", lambda repo_root: loaded)
    monkeypatch.setattr(
        runner,
        "verify_openrouter_probe_local",
        lambda repo_root: SimpleNamespace(live_preflight_passed=True),
    )


def _execute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenarios: list[list[OpenRouterHttpResponse]],
) -> tuple[OpenRouterProbeExecutionSummary, runner._LoadedExecution, _Factory]:
    loaded = _loaded(tmp_path)
    _patch_loaded(monkeypatch, loaded)
    factory = _Factory(scenarios)
    summary = runner.execute_openrouter_probe(
        tmp_path,
        confirmation_phrase="EXECUTE_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
        environ={"OPENROUTER_API_KEY": "fixture-key"},
        transport_factory=factory,
        git_inspector=_Git(),
        clock=_Clock(),
    )
    return summary, loaded, factory


def test_execution_promotes_only_with_controlled_positive_cache_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, loaded, _ = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK", cached=0, written=100),
                _generation(native=0),
            ],
            [
                _completion(output="WARM-PROBE-ACK", cached=100, written=0),
                _generation(native=100),
            ],
        ],
    )

    assert summary.terminal_outcome is (
        OpenRouterProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW
    )
    assert summary.attempt_count == 2
    assert summary.retained_success_count == 2
    assert len(loaded.paths.raw.read_text(encoding="utf-8").splitlines()) == 4
    assert len(loaded.paths.parsed.read_text(encoding="utf-8").splitlines()) == 2
    assert loaded.paths.terminal.is_file()


def test_cold_positive_read_is_contamination_and_cannot_alone_promote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, loaded, _ = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK", cached=100, written=0),
                _generation(native=100),
            ],
            [
                _completion(output="WARM-PROBE-ACK", cached=0, written=0),
                _generation(native=0),
            ],
        ],
    )

    assert summary.terminal_outcome is OpenRouterProbeTerminalOutcome.CLOSED_NO_CACHE_USE
    receipt = json.loads(loaded.paths.terminal.read_text(encoding="utf-8"))
    assert receipt["cold_positive_cache_read_contamination"] is True
    assert receipt["controlled_positive_cache_use_observed"] is False


def test_exact_output_failure_is_terminal_and_is_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, factory = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK.", cached=0, written=100),
                _generation(native=0),
            ]
        ],
    )

    assert summary.terminal_outcome is (OpenRouterProbeTerminalOutcome.CLOSED_OBSERVATION_INVALID)
    assert summary.provider_success_count == 1
    assert summary.retained_success_count == 0
    assert factory.calls == 1


def test_one_transient_completion_replacement_is_permitted_before_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, factory = _execute(
        tmp_path,
        monkeypatch,
        [
            [_response({"error": {"message": "busy"}}, status=429)],
            [
                _completion(output="COLD-PROBE-ACK", cached=0, written=100),
                _generation(native=0),
            ],
            [
                _completion(output="WARM-PROBE-ACK", cached=100, written=0),
                _generation(native=100),
            ],
        ],
    )

    assert summary.terminal_outcome is (
        OpenRouterProbeTerminalOutcome.PROMOTED_TO_PILOT_AUTHORIZATION_REVIEW
    )
    assert summary.attempt_count == 3
    assert summary.replacement_count == 1
    assert summary.network_request_count == 5
    assert factory.calls == 3


def test_generation_failure_after_successful_completion_is_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, factory = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK", cached=0, written=100),
                _response({"error": {"message": "busy"}}, status=529),
            ]
        ],
    )

    assert summary.terminal_outcome is (
        OpenRouterProbeTerminalOutcome.CLOSED_TERMINAL_PROVIDER_FAILURE
    )
    assert summary.provider_success_count == 1
    assert summary.attempt_count == 1
    assert factory.calls == 1


def test_cross_call_route_change_blocks_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, _ = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK", cached=0, written=100),
                _generation(native=0, provider="provider-a"),
            ],
            [
                _completion(output="WARM-PROBE-ACK", cached=100, written=0),
                _generation(native=100, provider="provider-b"),
            ],
        ],
    )

    assert summary.terminal_outcome is (OpenRouterProbeTerminalOutcome.CLOSED_ROUTE_UNIDENTIFIABLE)


def test_absent_cache_fields_close_as_telemetry_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, _ = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(
                    output="COLD-PROBE-ACK",
                    include_details=False,
                ),
                _generation(native=None),
            ],
            [
                _completion(
                    output="WARM-PROBE-ACK",
                    include_details=False,
                ),
                _generation(native=None),
            ],
        ],
    )

    assert summary.terminal_outcome is (OpenRouterProbeTerminalOutcome.CLOSED_TELEMETRY_UNAVAILABLE)


def test_numeric_zero_closes_as_no_cache_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, _ = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK", cached=0, written=0),
                _generation(native=0),
            ],
            [
                _completion(output="WARM-PROBE-ACK", cached=0, written=0),
                _generation(native=0),
            ],
        ],
    )

    assert summary.terminal_outcome is OpenRouterProbeTerminalOutcome.CLOSED_NO_CACHE_USE


def test_incomplete_journal_is_closed_without_credential_or_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = _loaded(tmp_path)
    started = OpenRouterProbeJournalRecord(
        authorization_id=loaded.authorization.authorization_id,
        execution_id=loaded.authorization.execution_id,
        event_index=1,
        event_type=OpenRouterProbeJournalEventType.EXECUTION_STARTED,
        recorded_at=datetime(2026, 7, 14, 10, tzinfo=UTC),
        total_attempt_count=0,
        provider_success_count=0,
        retained_success_count=0,
        replacement_count=0,
    )
    loaded.paths.journal.write_text(started.model_dump_json() + "\n", encoding="utf-8")
    _patch_loaded(monkeypatch, loaded)

    class _ForbiddenFactory:
        def __call__(
            self,
            *,
            api_key: str,
            context: OpenRouterProbeAttemptContext,
            writer: OpenRouterRawResponseWriter,
            clock: Callable[[], datetime],
        ) -> RecordingOpenRouterTransport:
            del api_key, context, writer, clock
            raise AssertionError("interruption closeout must not create a transport")

    summary = runner.execute_openrouter_probe(
        tmp_path,
        confirmation_phrase="",
        environ={},
        transport_factory=_ForbiddenFactory(),
        git_inspector=_Git(),
        clock=_Clock(),
    )

    assert summary.terminal_outcome is (OpenRouterProbeTerminalOutcome.CLOSED_INTERRUPTED_EXECUTION)
    assert summary.credential_accessed is False
    assert summary.network_request_count == 0
    assert loaded.paths.terminal.is_file()


def test_existing_terminal_receipt_blocks_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, loaded, _ = _execute(
        tmp_path,
        monkeypatch,
        [
            [
                _completion(output="COLD-PROBE-ACK", cached=0, written=0),
                _generation(native=0),
            ],
            [
                _completion(output="WARM-PROBE-ACK", cached=0, written=0),
                _generation(native=0),
            ],
        ],
    )

    with pytest.raises(
        runner.OpenRouterProbeExecutionError,
        match="already consumes",
    ):
        runner.execute_openrouter_probe(
            tmp_path,
            confirmation_phrase="EXECUTE_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
            environ={"OPENROUTER_API_KEY": "fixture-key"},
            transport_factory=_Factory([]),
            git_inspector=_Git(),
            clock=_Clock(),
        )
    assert loaded.paths.terminal.is_file()


def test_second_transient_failure_exhausts_the_logical_call_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _, factory = _execute(
        tmp_path,
        monkeypatch,
        [
            [_response({"error": {"message": "busy"}}, status=429)],
            [_response({"error": {"message": "still busy"}}, status=529)],
        ],
    )

    assert summary.terminal_outcome is (
        OpenRouterProbeTerminalOutcome.CLOSED_TRANSIENT_BUDGET_EXHAUSTED
    )
    assert summary.attempt_count == 2
    assert summary.replacement_count == 1
    assert factory.calls == 2
