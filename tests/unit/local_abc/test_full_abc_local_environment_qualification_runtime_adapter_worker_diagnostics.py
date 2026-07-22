"""Worker-process observability regressions for the CUDA 12.9 runtime adapter."""

from __future__ import annotations

import os
import sys
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_kaggle_runtime_adapter as adapter,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_worker_startup_diagnostics as diagnostics,
)


class _DiagnosticProcess(Protocol):
    def diagnostic_snapshot(self) -> adapter.WorkerProcessSnapshot:
        """Return one bounded worker-process diagnostic snapshot."""


class _FakeProcess:
    def __init__(
        self,
        returncode: int | None,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return self.returncode or 0

    def diagnostic_snapshot(self) -> adapter.WorkerProcessSnapshot:
        return adapter.WorkerProcessSnapshot(
            returncode=self.returncode,
            stdout_available=True,
            stdout_observed_bytes=len(self.stdout),
            stdout_tail=self.stdout,
            stderr_available=True,
            stderr_observed_bytes=len(self.stderr),
            stderr_tail=self.stderr,
        )


class _FakeOperations:
    def __init__(self, *, status_error: BaseException | None = None) -> None:
        self.status_error = status_error
        self.status_calls = 0
        self.sleep_calls = 0

    def now(self) -> datetime:
        return datetime(2026, 7, 22, 13, 30, tzinfo=UTC)

    def sleep(self, seconds: float) -> None:
        assert seconds == adapter._HEALTH_POLL_SECONDS
        self.sleep_calls += 1

    def get_status(self, url: str, *, timeout: float) -> int:
        assert url.startswith("http://127.0.0.1:")
        assert timeout == 2.0
        self.status_calls += 1
        if self.status_error is not None:
            raise self.status_error
        return 503


def _plans() -> tuple[adapter.WorkerPlan, adapter.WorkerPlan]:
    return (
        adapter.WorkerPlan(
            worker_id="worker_1",
            gpu_index=0,
            host="127.0.0.1",
            port=8001,
            command_argv=("python", "worker-1"),
            command_sha256="a" * 64,
            environment=(),
        ),
        adapter.WorkerPlan(
            worker_id="worker_2",
            gpu_index=1,
            host="127.0.0.1",
            port=8002,
            command_argv=("python", "worker-2"),
            command_sha256="b" * 64,
            environment=(),
        ),
    )


def test_process_exit_writes_typed_diagnostic_before_raise(tmp_path: Path) -> None:
    operations = _FakeOperations()
    runtime_adapter = adapter.KaggleQualificationRuntimeAdapter(
        cast(adapter.RuntimeOperations, operations)
    )
    path = tmp_path / "worker_startup_diagnostic.json"
    processes = (
        _FakeProcess(
            1,
            stdout=b"OPENAI_API_KEY=secret",
            stderr=b"fatal startup error",
        ),
        _FakeProcess(None),
    )

    with pytest.raises(RuntimeError, match="worker_1 exited"):
        runtime_adapter._wait_for_workers(
            _plans(),
            processes,
            phase="initial_startup",
            diagnostic_path=path,
        )

    diagnostic = diagnostics.validate_diagnostic_file(path)
    assert diagnostic.failed_worker_id == "worker_1"
    assert diagnostic.workers[0].process_returncode == 1
    assert diagnostic.workers[0].poll_count == 1
    assert "secret" not in diagnostic.workers[0].stdout.text
    assert diagnostic.hidden_retries_performed == 0
    assert diagnostic.workers_replaced == 0
    assert operations.status_calls == 0


def test_readiness_timeout_retains_all_bounded_poll_history(tmp_path: Path) -> None:
    operations = _FakeOperations(status_error=urllib.error.URLError("connection refused"))
    runtime_adapter = adapter.KaggleQualificationRuntimeAdapter(
        cast(adapter.RuntimeOperations, operations)
    )
    path = tmp_path / "worker_startup_diagnostic.json"
    processes = (_FakeProcess(None), _FakeProcess(None))

    with pytest.raises(RuntimeError, match="worker_1 failed bounded"):
        runtime_adapter._wait_for_workers(
            _plans(),
            processes,
            phase="initial_startup",
            diagnostic_path=path,
        )

    diagnostic = diagnostics.validate_diagnostic_file(path)
    worker = diagnostic.workers[0]
    assert worker.poll_count == adapter._MAX_HEALTH_POLLS
    assert len(worker.readiness_history) == adapter._MAX_HEALTH_POLLS
    assert worker.final_error_type == "URLError"
    assert operations.status_calls == adapter._MAX_HEALTH_POLLS
    assert operations.sleep_calls == adapter._MAX_HEALTH_POLLS - 1


def test_stdlib_capture_keeps_workspace_files_byte_bounded(tmp_path: Path) -> None:
    operations = adapter.StdlibRuntimeOperations()
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    payload = diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES * 2
    process = operations.spawn_captured(
        (
            sys.executable,
            "-c",
            (f"import sys;sys.stdout.write('x'*{payload});sys.stderr.write('y'*{payload})"),
        ),
        env=os.environ,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    assert process.wait(timeout=30.0) == 0
    snapshot = cast(_DiagnosticProcess, process).diagnostic_snapshot()

    assert stdout_path.stat().st_size <= diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES
    assert stderr_path.stat().st_size <= diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES
    assert len(snapshot.stdout_tail) <= diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES
    assert len(snapshot.stderr_tail) <= diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES
    assert snapshot.stdout_observed_bytes == payload
    assert snapshot.stderr_observed_bytes == payload
