"""Typed, bounded, sanitized worker-startup diagnostics for qualification failures."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

WORKER_STARTUP_DIAGNOSTIC_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_diagnostic.json"
)
MAXIMUM_STREAM_CAPTURE_BYTES: Final = 32 * 1024
MAXIMUM_STREAM_OBSERVED_BYTES: Final = 2**63 - 1
MAXIMUM_DIAGNOSTIC_BYTES: Final = 256 * 1024
MAXIMUM_READINESS_POLLS: Final = 90

_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
_SECRET_ASSIGNMENT_PATTERN: Final = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|AUTHORIZATION|COOKIE)"
    r"[A-Z0-9_]*)\s*[:=]\s*([^\s,;]+)"
)
_BEARER_PATTERN: Final = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_JSON_CONTENT_PATTERN: Final = re.compile(r"(?i)([\"\']content[\"\']\s*:\s*[\"\'])(.*?)([\"\'])")
_KAGGLE_INPUT_PATTERN: Final = re.compile(r"/kaggle/input/[^\s\"']+")
_KAGGLE_WORKING_PATTERN: Final = re.compile(r"/kaggle/working/[^\s\"']+")
_WINDOWS_PATH_PATTERN: Final = re.compile(r"[A-Za-z]:\\[^\r\n\"']+")
_CONTROL_CHARACTER_PATTERN: Final = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class BoundedStreamCapture(LocalABCContract):
    """One sanitized bounded stream tail and its accounting metadata."""

    available: bool
    observed_bytes: int = Field(ge=0, le=MAXIMUM_STREAM_OBSERVED_BYTES)
    captured_bytes: int = Field(ge=0, le=MAXIMUM_STREAM_CAPTURE_BYTES)
    truncated: bool
    sha256: str
    text: str = Field(max_length=MAXIMUM_STREAM_CAPTURE_BYTES)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("stream digest must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_capture(self) -> Self:
        encoded = self.text.encode("utf-8")
        if len(encoded) != self.captured_bytes:
            raise ValueError("captured byte count does not match stream text")
        if hashlib.sha256(encoded).hexdigest() != self.sha256:
            raise ValueError("stream digest does not match stream text")
        if self.truncated != (self.observed_bytes > self.captured_bytes):
            raise ValueError("stream truncation flag does not match byte accounting")
        if not self.available and (self.observed_bytes != 0 or self.text):
            raise ValueError("unavailable streams cannot contain captured data")
        return self


class ReadinessPollObservation(LocalABCContract):
    """One bounded readiness poll without raw URL or environment disclosure."""

    poll_index: int = Field(ge=1, le=MAXIMUM_READINESS_POLLS)
    process_returncode: int | None
    http_status: int | None = Field(default=None, ge=100, le=599)
    error_type: str | None = Field(default=None, max_length=128)
    safe_error: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_result_shape(self) -> Self:
        outcome_count = sum(
            value is not None
            for value in (
                self.http_status,
                self.error_type,
                self.process_returncode,
            )
        )
        if outcome_count == 0:
            raise ValueError("readiness poll must retain one observable outcome")
        return self


class WorkerStartupObservation(LocalABCContract):
    """Diagnostic state for one governed worker process."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    host: Literal["127.0.0.1"]
    port: Literal[8001, 8002]
    command_sha256: str
    ready: bool
    process_returncode: int | None
    poll_count: int = Field(ge=0, le=MAXIMUM_READINESS_POLLS)
    final_error_type: str | None = Field(default=None, max_length=128)
    final_safe_error: str | None = Field(default=None, max_length=512)
    readiness_history: tuple[ReadinessPollObservation, ...]
    stdout: BoundedStreamCapture
    stderr: BoundedStreamCapture
    hidden_retry_count: Literal[0] = 0
    replacement_count: Literal[0] = 0

    @field_validator("command_sha256")
    @classmethod
    def validate_command_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("worker command identity must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_worker(self) -> Self:
        expected = {
            "worker_1": (0, 8001),
            "worker_2": (1, 8002),
        }
        if (self.gpu_index, self.port) != expected[self.worker_id]:
            raise ValueError("worker identity, GPU, and port binding drifted")
        if self.poll_count != len(self.readiness_history):
            raise ValueError("worker poll count does not match readiness history")
        if self.ready and self.final_error_type is not None:
            raise ValueError("ready worker cannot retain a terminal error")
        return self


class WorkerStartupDiagnostic(LocalABCContract):
    """Complete fail-closed worker-startup diagnostic artifact."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    diagnostic_id: Literal["auragateway-environment-qualification-worker-startup-diagnostic-v1"]
    status: Literal["FAILED"]
    phase: Literal["initial_startup", "post_reset_restart"]
    captured_at: str
    failed_worker_id: Literal["worker_1", "worker_2"]
    workers: tuple[WorkerStartupObservation, WorkerStartupObservation]
    raw_environment_included: Literal[False] = False
    authorization_payload_included: Literal[False] = False
    model_content_included: Literal[False] = False
    hidden_retries_performed: Literal[0] = 0
    workers_replaced: Literal[0] = 0
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_workers(self) -> Self:
        identities = tuple(worker.worker_id for worker in self.workers)
        if identities != ("worker_1", "worker_2"):
            raise ValueError("diagnostic worker order or set drifted")
        if self.failed_worker_id not in identities:
            raise ValueError("failed worker is absent from diagnostic")
        return self


def _tail_bytes(payload: bytes, maximum_bytes: int) -> bytes:
    if maximum_bytes < 1:
        raise ValueError("maximum_bytes must be positive")
    if len(payload) <= maximum_bytes:
        return payload
    return payload[-maximum_bytes:]


def sanitize_text(value: str) -> str:
    """Redact common secret, path, and model-content shapes from evidence text."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _CONTROL_CHARACTER_PATTERN.sub("?", normalized)
    normalized = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1=<redacted>", normalized)
    normalized = _BEARER_PATTERN.sub("Bearer <redacted>", normalized)
    normalized = _JSON_CONTENT_PATTERN.sub(r"\1<redacted>\3", normalized)
    normalized = _KAGGLE_INPUT_PATTERN.sub("<input-path>", normalized)
    normalized = _KAGGLE_WORKING_PATTERN.sub("<working-path>", normalized)
    normalized = _WINDOWS_PATH_PATTERN.sub("<local-path>", normalized)
    return normalized


def build_stream_capture(
    *,
    raw_tail: bytes,
    observed_bytes: int,
    available: bool,
) -> BoundedStreamCapture:
    """Build one byte-bounded sanitized stream capture."""

    if observed_bytes < 0:
        raise ValueError("observed stream bytes cannot be negative")
    if not available:
        encoded = b""
        return BoundedStreamCapture(
            available=False,
            observed_bytes=0,
            captured_bytes=0,
            truncated=False,
            sha256=hashlib.sha256(encoded).hexdigest(),
            text="",
        )

    bounded_raw = _tail_bytes(raw_tail, MAXIMUM_STREAM_CAPTURE_BYTES)
    decoded = bounded_raw.decode("utf-8", errors="replace")
    sanitized = sanitize_text(decoded)
    encoded = _tail_bytes(
        sanitized.encode("utf-8", errors="replace"),
        MAXIMUM_STREAM_CAPTURE_BYTES,
    )
    text = encoded.decode("utf-8", errors="replace")
    encoded = text.encode("utf-8")
    while len(encoded) > MAXIMUM_STREAM_CAPTURE_BYTES:
        text = text[1:]
        encoded = text.encode("utf-8")
    observed = max(observed_bytes, len(raw_tail))
    return BoundedStreamCapture(
        available=True,
        observed_bytes=observed,
        captured_bytes=len(encoded),
        truncated=observed > len(encoded),
        sha256=hashlib.sha256(encoded).hexdigest(),
        text=text,
    )


def canonical_diagnostic_bytes(diagnostic: WorkerStartupDiagnostic) -> bytes:
    return diagnostic.canonical_json().encode("utf-8")


def write_diagnostic_atomic(
    path: Path,
    diagnostic: WorkerStartupDiagnostic,
) -> str:
    """Write one canonical diagnostic atomically and reject overwrite."""

    payload = canonical_diagnostic_bytes(diagnostic)
    if len(payload) > MAXIMUM_DIAGNOSTIC_BYTES:
        raise RuntimeError("worker-startup diagnostic exceeds its byte budget")
    if path.exists():
        raise RuntimeError("worker-startup diagnostic already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        if path.exists():
            raise RuntimeError("worker-startup diagnostic appeared before commit")
        temporary_path.replace(path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload).hexdigest()


def validate_diagnostic_file(path: Path) -> WorkerStartupDiagnostic:
    """Validate canonical encoding, size, and typed diagnostic content."""

    if not path.is_file() or path.is_symlink():
        raise RuntimeError("worker-startup diagnostic must be one regular file")
    payload = path.read_bytes()
    if len(payload) > MAXIMUM_DIAGNOSTIC_BYTES:
        raise RuntimeError("worker-startup diagnostic exceeds its byte budget")
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("worker-startup diagnostic is invalid JSON") from exc
    diagnostic = WorkerStartupDiagnostic.model_validate(raw)
    if payload != canonical_diagnostic_bytes(diagnostic):
        raise RuntimeError("worker-startup diagnostic is not canonical JSON")
    return diagnostic
