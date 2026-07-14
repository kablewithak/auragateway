"""Generate and validate a sanitized terminal closeout for the Hy3 probe."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
import urllib.request
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar, cast
from unittest.mock import patch

from pydantic import BaseModel, ValidationError

from auragateway.contracts.openrouter_hy3_capability_probe_closeout import (
    OpenRouterProbeCloseoutManifest,
    OpenRouterProbeCloseoutSummary,
    OpenRouterProbePosthocAuthDiagnostic,
    OpenRouterProbeSanitizedCloseout,
)
from auragateway.contracts.openrouter_hy3_capability_probe_execution import (
    OpenRouterProbeJournalEventType,
    OpenRouterProbeJournalRecord,
    OpenRouterProbeParsedObservationRecord,
    OpenRouterProbeRawResponseKind,
    OpenRouterProbeRawResponseRecord,
    OpenRouterProbeTerminalOutcome,
    OpenRouterProbeTerminalReceipt,
)
from auragateway.providers.openrouter_http import UrllibOpenRouterBackend

_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)


class OpenRouterProbeCloseoutError(RuntimeError):
    """Metadata-safe closeout validation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_FILE_READ_FAILED",
            f"Required closeout evidence could not be read: {path.as_posix()}",
        ) from exc


def _load_model(path: Path, model_type: type[_MODEL_T]) -> _MODEL_T:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_MODEL_INVALID",
            f"Required closeout model is missing or invalid: {path.as_posix()}",
        ) from exc


def _read_jsonl(path: Path, model_type: type[_MODEL_T]) -> list[_MODEL_T]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_JSONL_READ_FAILED",
            f"Required protected JSONL could not be read: {path.as_posix()}",
        ) from exc
    records: list[_MODEL_T] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append(model_type.model_validate_json(line))
        except ValidationError as exc:
            raise OpenRouterProbeCloseoutError(
                "OPENROUTER_HY3_CLOSEOUT_JSONL_INVALID",
                f"Protected JSONL validation failed at line {line_number}: {path.as_posix()}",
            ) from exc
    return records


def _paths(repo_root: Path) -> dict[str, Path]:
    local = repo_root / ".local/benchmark/openrouter-hy3-capability-probe-v1"
    public = repo_root / "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1"
    return {
        "terminal": local / "terminal_receipt.json",
        "journal": local / "journal.jsonl",
        "raw": local / "raw_responses.jsonl",
        "parsed": local / "parsed_responses.jsonl",
        "result": public / "closeout_result.json",
        "manifest": public / "closeout_manifest.json",
        "policy": public / "closeout_policy.json",
        "contract": repo_root
        / "src/auragateway/contracts/openrouter_hy3_capability_probe_closeout.py",
        "runner": repo_root
        / "src/auragateway/benchmark/openrouter_hy3_capability_probe_closeout_runner.py",
        "adr": repo_root / "docs/adr/openrouter-hy3-capability-probe-closeout.md",
        "report": repo_root
        / "docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Closeout.md",
    }


def _provider_error(raw: OpenRouterProbeRawResponseRecord) -> tuple[str, str]:
    payload = raw.json_payload
    if not isinstance(payload, dict):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_ERROR_PAYLOAD_UNAVAILABLE",
            "The terminal provider response does not contain a JSON error object.",
        )
    error = payload.get("error")
    if not isinstance(error, dict):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_ERROR_OBJECT_UNAVAILABLE",
            "The terminal provider response does not contain a typed error object.",
        )
    code = error.get("code")
    message = error.get("message")
    if code is None or not isinstance(message, str) or not message.strip():
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_ERROR_FIELDS_INVALID",
            "The terminal provider response lacks safe error classification fields.",
        )
    return str(code)[:80], message.strip()[:240]


def _posthoc_auth_diagnostic(recorded_at: datetime) -> OpenRouterProbePosthocAuthDiagnostic:
    captured: dict[str, object] = {}

    class _RequestCaptured(Exception):
        pass

    def _capture(request: urllib.request.Request, timeout: float) -> object:
        del timeout
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        raise _RequestCaptured

    with patch("urllib.request.urlopen", new=_capture):
        backend = UrllibOpenRouterBackend()
        with contextlib.suppress(_RequestCaptured):
            backend.request(
                method="POST",
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer fixture-only-not-a-real-key",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "AuraGateway/0.1",
                },
                body=b"{}",
                timeout_seconds=1,
            )

    headers = cast(dict[str, str], captured.get("headers", {}))
    authorization = headers.get("authorization")
    proxies = urllib.request.getproxies()
    return OpenRouterProbePosthocAuthDiagnostic(
        authorization_header_present=authorization is not None,
        authorization_scheme=(
            "Bearer" if authorization is not None and authorization.startswith("Bearer ") else None
        ),
        proxy_entry_count=len(proxies),
        proxy_detected=bool(proxies),
        diagnostic_recorded_at=recorded_at,
    )


def _validate_local(
    repo_root: Path,
) -> tuple[
    OpenRouterProbeTerminalReceipt,
    OpenRouterProbeRawResponseRecord,
    str,
    str,
]:
    paths = _paths(repo_root)
    receipt = _load_model(paths["terminal"], OpenRouterProbeTerminalReceipt)
    journal = _read_jsonl(paths["journal"], OpenRouterProbeJournalRecord)
    raw = _read_jsonl(paths["raw"], OpenRouterProbeRawResponseRecord)
    parsed = _read_jsonl(paths["parsed"], OpenRouterProbeParsedObservationRecord)

    if (
        receipt.terminal_outcome
        is not OpenRouterProbeTerminalOutcome.CLOSED_TERMINAL_PROVIDER_FAILURE
    ):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_OUTCOME_MISMATCH",
            "This closeout package is bound to the terminal provider-authentication failure.",
        )
    if (
        receipt.attempt_count,
        receipt.provider_success_count,
        receipt.retained_success_count,
        receipt.replacement_count,
    ) != (1, 0, 0, 0):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_COUNT_MISMATCH",
            "Terminal attempt accounting does not match the frozen closeout result.",
        )
    if parsed:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_PARSED_RESPONSE_UNEXPECTED",
            "Authentication failure closeout cannot contain a parsed provider observation.",
        )
    if len(raw) != 1:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_RAW_COUNT_MISMATCH",
            "Authentication failure closeout requires exactly one raw completion response.",
        )
    raw_record = raw[0]
    if (
        raw_record.response_kind is not OpenRouterProbeRawResponseKind.COMPLETION
        or raw_record.http_status != 401
        or raw_record.logical_call_role.value != "cold_probe"
        or raw_record.attempt_number != 1
    ):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_RAW_IDENTITY_MISMATCH",
            "The retained provider response does not match the frozen cold-call 401 result.",
        )
    terminal_failures = [
        record
        for record in journal
        if record.event_type is OpenRouterProbeJournalEventType.ATTEMPT_TERMINAL_FAILURE
    ]
    closed = [
        record
        for record in journal
        if record.event_type is OpenRouterProbeJournalEventType.EXECUTION_CLOSED
    ]
    if len(terminal_failures) != 1 or len(closed) != 1:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_JOURNAL_SHAPE_INVALID",
            "The protected journal does not contain one terminal failure and one close event.",
        )
    failure = terminal_failures[0]
    if failure.safe_error_code != "PROVIDER_AUTHENTICATION_FAILED" or failure.retry_permitted:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_FAILURE_CLASS_MISMATCH",
            "The protected journal does not classify the result as a non-retryable "
            "authentication failure.",
        )
    if closed[0].terminal_outcome is not receipt.terminal_outcome:
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_TERMINAL_MISMATCH",
            "Journal and terminal receipt outcomes do not reconcile.",
        )
    if receipt.raw_responses_sha256 != _sha256_file(paths["raw"]):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_RAW_HASH_MISMATCH",
            "Terminal receipt no longer matches protected raw responses.",
        )
    if receipt.parsed_responses_sha256 != _sha256_file(paths["parsed"]):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_PARSED_HASH_MISMATCH",
            "Terminal receipt no longer matches protected parsed responses.",
        )
    code, message = _provider_error(raw_record)
    return receipt, raw_record, code, message


def _summary(
    *,
    command: str,
    result_present: bool,
    manifest_present: bool,
    next_gate: str,
) -> OpenRouterProbeCloseoutSummary:
    return OpenRouterProbeCloseoutSummary(
        command=command,
        closeout_ready=True,
        closeout_result_present=result_present,
        closeout_manifest_present=manifest_present,
        terminal_outcome="closed_terminal_provider_failure",
        failure_class="provider_authentication_failed",
        attempt_count=1,
        provider_success_count=0,
        authorization_consumed=True,
        next_gate=next_gate,
    )


def validate_local(repo_root: Path) -> OpenRouterProbeCloseoutSummary:
    _validate_local(repo_root)
    paths = _paths(repo_root)
    return _summary(
        command="validate-local",
        result_present=paths["result"].exists(),
        manifest_present=paths["manifest"].exists(),
        next_gate="generate_sanitized_closeout",
    )


def generate_closeout(
    repo_root: Path,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> OpenRouterProbeCloseoutSummary:
    receipt, raw, provider_code, provider_message = _validate_local(repo_root)
    paths = _paths(repo_root)
    sanitized_at = clock()
    diagnostic = _posthoc_auth_diagnostic(sanitized_at)
    result = OpenRouterProbeSanitizedCloseout(
        closeout_id="openrouter-hy3-capability-probe-closeout-v1",
        authorization_id=receipt.authorization_id,
        execution_id=receipt.execution_id,
        source_commit=receipt.source_commit,
        terminal_outcome="closed_terminal_provider_failure",
        failure_stage="pre_inference_authentication",
        failure_class="provider_authentication_failed",
        attempt_count=1,
        provider_success_count=0,
        retained_success_count=0,
        replacement_count=0,
        network_request_count=1,
        response_kind="completion",
        http_status=401,
        safe_error_code="PROVIDER_AUTHENTICATION_FAILED",
        provider_error_code=provider_code,
        provider_error_message=provider_message,
        response_body_sha256=raw.body_sha256,
        response_body_bytes=raw.body_bytes,
        terminal_receipt_sha256=_sha256_file(paths["terminal"]),
        journal_sha256=_sha256_file(paths["journal"]),
        raw_responses_sha256=_sha256_file(paths["raw"]),
        parsed_responses_sha256=_sha256_file(paths["parsed"]),
        prompt_bundle_sha256=receipt.prompt_bundle_sha256,
        preflight_receipt_sha256=receipt.preflight_receipt_sha256,
        posthoc_auth_diagnostic=diagnostic,
        permitted_claim=(
            "The one-time OpenRouter Hy3 capability probe closed on its first cold-call "
            "attempt after an HTTP 401 authentication failure; no completion, generation "
            "metadata, or cache telemetry was obtained."
        ),
        non_claims=(
            "No Hy3 model inference succeeded.",
            "No cache hit, miss, read, write, discount, saving, or latency result was observed.",
            "The evidence does not establish whether credential validity, credential entry, "
            "header delivery, or another authentication factor caused the 401 response.",
            "No A/B/C pilot or retained benchmark is authorized.",
        ),
        residual_harness_gaps=(
            "Preflight and execution did not retain a protected credential fingerprint, so "
            "credential continuity cannot be proven.",
            "Execution did not retain non-sensitive proof that the authorization header was "
            "constructed for the exact live request.",
            "The runner validated a stripped key for non-emptiness but passed the original "
            "value to transport, leaving surrounding-whitespace risk unclosed.",
        ),
        next_gate="terminal_review_and_continuity_update",
        closed_at=receipt.closed_at,
        sanitized_at=sanitized_at,
    )
    paths["result"].parent.mkdir(parents=True, exist_ok=True)
    result_bytes = (result.model_dump_json(indent=2) + "\n").encode("utf-8")
    paths["result"].write_bytes(result_bytes)
    manifest = OpenRouterProbeCloseoutManifest(
        closeout_id="openrouter-hy3-capability-probe-closeout-v1",
        closeout_result_sha256=_sha256_bytes(result_bytes),
        closeout_policy_sha256=_sha256_file(paths["policy"]),
        closeout_contract_sha256=_sha256_file(paths["contract"]),
        closeout_runner_sha256=_sha256_file(paths["runner"]),
        adr_sha256=_sha256_file(paths["adr"]),
        benchmark_report_sha256=_sha256_file(paths["report"]),
        terminal_receipt_sha256=result.terminal_receipt_sha256,
        journal_sha256=result.journal_sha256,
        raw_responses_sha256=result.raw_responses_sha256,
        parsed_responses_sha256=result.parsed_responses_sha256,
        generated_at=sanitized_at,
    )
    paths["manifest"].write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return _summary(
        command="generate",
        result_present=True,
        manifest_present=True,
        next_gate="validate_and_commit_sanitized_closeout",
    )


def validate_public(repo_root: Path) -> OpenRouterProbeCloseoutSummary:
    paths = _paths(repo_root)
    result = _load_model(paths["result"], OpenRouterProbeSanitizedCloseout)
    manifest = _load_model(paths["manifest"], OpenRouterProbeCloseoutManifest)
    if manifest.closeout_result_sha256 != _sha256_file(paths["result"]):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_RESULT_HASH_MISMATCH",
            "Generated closeout result does not match its manifest.",
        )
    expected = {
        "closeout_policy_sha256": _sha256_file(paths["policy"]),
        "closeout_contract_sha256": _sha256_file(paths["contract"]),
        "closeout_runner_sha256": _sha256_file(paths["runner"]),
        "adr_sha256": _sha256_file(paths["adr"]),
        "benchmark_report_sha256": _sha256_file(paths["report"]),
        "terminal_receipt_sha256": result.terminal_receipt_sha256,
        "journal_sha256": result.journal_sha256,
        "raw_responses_sha256": result.raw_responses_sha256,
        "parsed_responses_sha256": result.parsed_responses_sha256,
    }
    for field, value in expected.items():
        if getattr(manifest, field) != value:
            raise OpenRouterProbeCloseoutError(
                "OPENROUTER_HY3_CLOSEOUT_MANIFEST_MISMATCH",
                f"Generated closeout manifest mismatch: {field}",
            )
    serialized = paths["result"].read_text(encoding="utf-8")
    forbidden = ("sk-or-v1-", "Bearer ", "stable_prefix", "system_prompt", "user_prompt")
    if any(token in serialized for token in forbidden):
        raise OpenRouterProbeCloseoutError(
            "OPENROUTER_HY3_CLOSEOUT_PUBLIC_CONTENT_FORBIDDEN",
            "Generated closeout contains forbidden protected content.",
        )
    return _summary(
        command="validate-public",
        result_present=True,
        manifest_present=True,
        next_gate="terminal_review_and_continuity_update",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sanitize the terminal OpenRouter Hy3 result.")
    parser.add_argument("command", choices=("validate-local", "generate", "validate-public"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-local":
            summary = validate_local(args.repo_root)
        elif args.command == "generate":
            summary = generate_closeout(args.repo_root)
        else:
            summary = validate_public(args.repo_root)
    except OpenRouterProbeCloseoutError as exc:
        print(
            json.dumps(
                {"error_code": exc.error_code, "safe_message": exc.safe_message},
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
