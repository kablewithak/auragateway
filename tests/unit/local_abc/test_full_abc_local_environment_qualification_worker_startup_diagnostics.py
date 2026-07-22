"""Regression tests for bounded worker-startup diagnostic contracts."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_worker_startup_diagnostics as diagnostics,
)


def _stream(text: str) -> diagnostics.BoundedStreamCapture:
    encoded = text.encode("utf-8")
    return diagnostics.build_stream_capture(
        raw_tail=encoded,
        observed_bytes=len(encoded),
        available=True,
    )


def _worker(worker_id: str) -> diagnostics.WorkerStartupObservation:
    gpu_index, port = {
        "worker_1": (0, 8001),
        "worker_2": (1, 8002),
    }[worker_id]
    return diagnostics.WorkerStartupObservation(
        worker_id=worker_id,
        gpu_index=gpu_index,
        host="127.0.0.1",
        port=port,
        command_sha256=hashlib.sha256(worker_id.encode("utf-8")).hexdigest(),
        ready=False,
        process_returncode=1,
        poll_count=1,
        final_error_type="WorkerProcessExited",
        final_safe_error="worker process exited before health readiness",
        readiness_history=(
            diagnostics.ReadinessPollObservation(
                poll_index=1,
                process_returncode=1,
                error_type="WorkerProcessExited",
                safe_error="worker process exited before health readiness",
            ),
        ),
        stdout=_stream("stdout"),
        stderr=_stream("stderr"),
    )


def _diagnostic() -> diagnostics.WorkerStartupDiagnostic:
    return diagnostics.WorkerStartupDiagnostic(
        diagnostic_id=("auragateway-environment-qualification-worker-startup-diagnostic-v1"),
        status="FAILED",
        phase="initial_startup",
        captured_at="2026-07-22T13:30:00+00:00",
        failed_worker_id="worker_1",
        workers=(
            _worker("worker_1"),
            _worker("worker_2"),
        ),
    )


def test_stream_capture_is_bounded_and_sanitized() -> None:
    raw = (
        b"OPENAI_API_KEY=secret-value\n"
        b"Authorization: Bearer abc.def.ghi\n"
        b'/kaggle/input/model/config.json {"content":"private prompt"}\n'
        + (b"x" * (diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES * 2))
    )

    capture = diagnostics.build_stream_capture(
        raw_tail=raw,
        observed_bytes=len(raw),
        available=True,
    )

    assert capture.captured_bytes <= diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES
    assert capture.observed_bytes == len(raw)
    assert capture.truncated is True
    assert "secret-value" not in capture.text
    assert "private prompt" not in capture.text
    assert "/kaggle/input/" not in capture.text


def test_sanitize_text_redacts_secret_shapes_and_paths() -> None:
    observed = diagnostics.sanitize_text(
        "HF_TOKEN=abc /kaggle/working/model.bin "
        'Authorization: Bearer token {"content":"raw prompt"}'
    )

    assert "abc" not in observed
    assert "Bearer token" not in observed
    assert "Authorization: Bearer token" not in observed
    assert "/kaggle/working/" not in observed
    assert "raw prompt" not in observed


def test_diagnostic_rejects_worker_identity_drift() -> None:
    payload = _worker("worker_1").model_dump(mode="json")
    payload["gpu_index"] = 1

    with pytest.raises(ValidationError, match="GPU"):
        diagnostics.WorkerStartupObservation.model_validate(payload)


def test_multibyte_tail_remains_within_byte_budget() -> None:
    raw = ("é" * (diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES + 1)).encode("utf-8")

    capture = diagnostics.build_stream_capture(
        raw_tail=raw,
        observed_bytes=len(raw),
        available=True,
    )

    assert capture.captured_bytes <= diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES
    assert len(capture.text.encode("utf-8")) == capture.captured_bytes
    assert capture.truncated is True


def test_atomic_write_rejects_overwrite_and_preserves_canonical_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "diagnostic.json"
    diagnostic = _diagnostic()

    digest = diagnostics.write_diagnostic_atomic(path, diagnostic)

    assert path.read_bytes() == diagnostics.canonical_diagnostic_bytes(diagnostic)
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert diagnostics.validate_diagnostic_file(path) == diagnostic

    with pytest.raises(RuntimeError, match="already exists"):
        diagnostics.write_diagnostic_atomic(path, diagnostic)


def test_diagnostic_safety_envelope_is_fail_closed() -> None:
    diagnostic = _diagnostic()

    assert diagnostic.raw_environment_included is False
    assert diagnostic.authorization_payload_included is False
    assert diagnostic.model_content_included is False
    assert diagnostic.hidden_retries_performed == 0
    assert diagnostic.workers_replaced == 0
    assert diagnostic.model_requests_performed == 0
    assert diagnostic.benchmark_trajectory_requests_performed == 0
