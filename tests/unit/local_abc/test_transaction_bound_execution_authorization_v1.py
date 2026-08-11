from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import transaction_bound_execution_authorization_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def _intent(runtime_payload: bytes) -> subject.AuthorizationIntent:
    return subject.build_intent(
        ROOT,
        runtime_payload,
        "1" * 40,
        prepared_at=datetime(2026, 8, 11, 0, 0, tzinfo=UTC),
        window_minutes=180,
        intent_id="2" * 32,
    )


def _authorization(runtime_payload: bytes) -> tuple[subject.ExecutionAuthorization, bytes]:
    intent = _intent(runtime_payload)
    challenge = subject.authorization_challenge(intent)
    return subject.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=datetime(2026, 8, 11, 0, 1, tzinfo=UTC),
    )


def _wrapper_namespace(runtime_payload: bytes) -> dict[str, object]:
    authorization, authorization_bytes = _authorization(runtime_payload)
    wrapper = subject.render_executable_payload(
        ROOT,
        authorization,
        authorization_bytes,
        runtime_payload,
    )
    namespace: dict[str, object] = {"__name__": "transaction_bound_test"}
    exec(compile(wrapper, "<wrapper-test>", "exec"), namespace, namespace)
    return namespace


def test_static_implementation_validates() -> None:
    result = subject.validate_static(ROOT)
    assert result["status"] == "TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1_VALID"
    assert result["authorization_specific_kaggle_inputs"] == 0
    assert result["authorization_producer_notebooks"] == 0
    assert result["manual_confirmation_json_files"] == 0
    assert result["runtime_anti_replay_established"] is False
    assert result["gpu_execution_authorized"] is False


def test_live_authorization_fails_closed_without_runtime_integration_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_record = Path(
        "benchmarks/local_abc/transaction_bound_runtime_integration_missing_for_test.json"
    )
    monkeypatch.setattr(
        subject,
        "RUNTIME_INTEGRATION_RECORD_PATH",
        missing_record,
    )

    with pytest.raises(
        subject.TransactionBoundError,
        match="required artifact is missing or unsafe",
    ):
        subject._require_runtime_integration(
            ROOT,
            ROOT / "src/auragateway/local_abc/not-yet-integrated.py",
        )


def test_transaction_identity_is_deterministic_preimage_hash() -> None:
    runtime_payload = b"print('bound')\n"
    first, first_bytes = _authorization(runtime_payload)
    second, second_bytes = _authorization(runtime_payload)
    assert first.transaction_id == second.transaction_id
    assert first_bytes == second_bytes
    parsed = json.loads(first_bytes)
    assert first.transaction_id == subject._sha256(
        subject._canonical_json_bytes(parsed["authorization"])
    )


def test_executable_generation_is_byte_deterministic() -> None:
    runtime_payload = b"VALUE = 7\n"
    authorization, authorization_bytes = _authorization(runtime_payload)
    first = subject.render_executable_payload(
        ROOT, authorization, authorization_bytes, runtime_payload
    )
    second = subject.render_executable_payload(
        ROOT, authorization, authorization_bytes, runtime_payload
    )
    assert first == second
    assert b"execution_authorization_v1.json" not in first
    assert b"ag-p5-p6-auth-control-v1" not in first
    assert b"/kaggle/input" not in first


def test_runtime_payload_change_changes_bound_identity() -> None:
    first, _ = _authorization(b"VALUE = 1\n")
    second, _ = _authorization(b"VALUE = 2\n")
    assert first.authorization.runtime_payload_sha256 != second.authorization.runtime_payload_sha256
    assert first.transaction_id != second.transaction_id


def test_expired_authorization_blocks_before_runtime_payload() -> None:
    runtime_payload = b"PAYLOAD_EXECUTED = True\n"
    namespace = _wrapper_namespace(runtime_payload)
    namespace["_observed_gpu_count"] = lambda: 2
    admit = cast(Callable[[datetime | None], dict[str, object]], namespace["admit"])
    with pytest.raises(RuntimeError, match="outside its live admission window"):
        admit(datetime(2026, 8, 11, 4, 0, tzinfo=UTC))
    assert "PAYLOAD_EXECUTED" not in namespace


def test_live_admission_verifies_bound_payload_and_gpu_topology() -> None:
    runtime_payload = b"VALUE = 9\n"
    namespace = _wrapper_namespace(runtime_payload)
    namespace["_observed_gpu_count"] = lambda: 2
    admit = cast(Callable[[datetime | None], dict[str, object]], namespace["admit"])
    result = admit(datetime(2026, 8, 11, 1, 0, tzinfo=UTC))
    assert result["status"] == "TRANSACTION_BOUND_RUNTIME_ADMISSION_VALID"
    assert result["observed_gpu_count"] == 2
    assert result["network_probe_performed"] is False


def test_manifest_separates_payload_and_notebook_identity() -> None:
    runtime_payload = b"VALUE = 11\n"
    authorization, authorization_bytes = _authorization(runtime_payload)
    executable = subject.render_executable_payload(
        ROOT, authorization, authorization_bytes, runtime_payload
    )
    notebook = subject.build_notebook(executable)
    manifest = subject.build_manifest(authorization, authorization_bytes, executable, notebook)
    assert manifest.executable_payload_sha256 == subject._sha256(executable)
    assert manifest.notebook_container_sha256 == subject._sha256(notebook)
    assert manifest.notebook_container_is_semantic_payload_identity is False
    assert manifest.authorization_specific_kaggle_inputs == 0


def test_primary_failure_reporting_error_does_not_replace_primary() -> None:
    runtime_payload = b"raise ValueError('primary-boom')\n"
    namespace = _wrapper_namespace(runtime_payload)
    namespace["admit"] = lambda: {"status": "TRANSACTION_BOUND_RUNTIME_ADMISSION_VALID"}
    writes = 0

    def fail_only_primary_report(*_args: object) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("secondary-boom")

    namespace["_write_json"] = fail_only_primary_report
    execute = cast(Callable[[], None], namespace["execute_bound_payload"])
    with pytest.raises(ValueError, match="primary-boom"):
        execute()


def test_terminal_receipt_requires_saved_version_for_attempted_disposition() -> None:
    with pytest.raises(ValueError):
        subject.TerminalReceipt(
            transaction_id="3" * 64,
            authorization_sha256="4" * 64,
            disposition=subject.TerminalDisposition.OUTCOME_UNKNOWN,
            execution_attempted=True,
            terminalized_at=datetime.now(UTC),
        )
