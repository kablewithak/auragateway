from __future__ import annotations

import ast
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    c4_paragraph_order_behavioral_differential_execution_authorization_v1 as issuer,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _copy(root: Path, relative: Path) -> None:
    source = REPO_ROOT / relative
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _fixture_root(tmp_path: Path) -> Path:
    for relative in (
        issuer.DESIGN_RECORD_PATH,
        issuer.IMPLEMENTATION_REVIEW_PATH,
        issuer.IMPLEMENTATION_RECORD_PATH,
        issuer.SUCCESSOR_RUNTIME_PATH,
        issuer.SOURCE_PATH,
        issuer.TEMPLATE_PATH,
        issuer.TEST_PATH,
        issuer.REPORT_PATH,
        issuer.RUNBOOK_PATH,
    ):
        _copy(tmp_path, relative)
    return tmp_path


def _no_ancestry_check(_: Path) -> None:
    return None


def test_static_generate_and_validate_are_execution_inert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_root(tmp_path)
    monkeypatch.setattr(issuer, "_require_design_ancestor", _no_ancestry_check)

    generated = issuer.generate_static(root)
    validated = issuer.validate_static(root)

    assert generated["live_authorization_issued"] is False
    assert generated["runtime_execution_authorized"] is False
    assert validated["status"] == "C4_PARAGRAPH_ORDER_EXECUTION_AUTHORIZATION_V1_VALID"
    assert validated["maximum_model_requests"] == 6
    assert validated["maximum_worker_teardowns"] == 6
    assert validated["request_order"] == list(issuer.REQUEST_ORDER)

    for relative in (
        issuer.LIVE_AUTHORIZATION_PATH,
        issuer.LIVE_MANIFEST_PATH,
        issuer.PLATFORM_OBSERVATION_RECEIPT_PATH,
        issuer.TERMINAL_RECEIPT_PATH,
    ):
        assert not (root / relative).exists()


def test_design_identity_drift_is_rejected(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    (root / issuer.DESIGN_RECORD_PATH).write_text("{}", encoding="utf-8")

    with pytest.raises(issuer.AuthorizationIssuerError) as raised:
        issuer._validate_design(root)

    assert raised.value.error_code == "C4_PARAGRAPH_ORDER_AUTHORIZATION_IDENTITY_DRIFT"


def test_intent_challenge_and_authorization_are_deterministically_bound(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    prepared_at = datetime(2026, 8, 20, 21, 0, tzinfo=UTC)
    intent = issuer.build_intent(
        root,
        "f" * 40,
        prepared_at=prepared_at,
        window_minutes=180,
        intent_id="a" * 32,
    )

    challenge = issuer.authorization_challenge(intent)
    authorization, authorization_bytes = issuer.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=prepared_at + timedelta(minutes=1),
    )

    assert len(challenge) == 64
    assert authorization.transaction_id == issuer._sha256(
        issuer._canonical_json_bytes(authorization.authorization)
    )
    assert authorization.authorization.runtime_execution_authorized is True
    assert authorization.authorization.paragraph_order_root_cause_claim_authorized is False
    assert json.loads(authorization_bytes)["transaction_id"] == authorization.transaction_id


def test_stale_confirmation_is_rejected(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    prepared_at = datetime(2026, 8, 20, 21, 0, tzinfo=UTC)
    intent = issuer.build_intent(
        root,
        "f" * 40,
        prepared_at=prepared_at,
        window_minutes=180,
        intent_id="b" * 32,
    )

    with pytest.raises(issuer.AuthorizationIssuerError) as raised:
        issuer.build_authorization(
            intent,
            challenge=issuer.authorization_challenge(intent),
            confirmed_at=prepared_at + timedelta(minutes=16),
        )

    assert raised.value.error_code == "C4_PARAGRAPH_ORDER_AUTHORIZATION_CONFIRMATION_STALE"


def test_generated_wrapper_is_marker_free_compilable_and_handles_systemexit_zero(
    tmp_path: Path,
) -> None:
    root = _fixture_root(tmp_path)
    prepared_at = datetime(2026, 8, 20, 21, 0, tzinfo=UTC)
    intent = issuer.build_intent(
        root,
        "f" * 40,
        prepared_at=prepared_at,
        window_minutes=180,
        intent_id="c" * 32,
    )
    authorization, authorization_bytes = issuer.build_authorization(
        intent,
        challenge=issuer.authorization_challenge(intent),
        confirmed_at=prepared_at + timedelta(minutes=1),
    )
    runtime_payload = (root / issuer.SUCCESSOR_RUNTIME_PATH).read_bytes()
    executable = issuer.render_executable_payload(
        root,
        authorization,
        authorization_bytes,
        runtime_payload,
    )
    text = executable.decode("utf-8")

    assert "__AUTHORIZATION_B64__" not in text
    assert "__RUNTIME_PAYLOAD_B64__" not in text
    assert "_AUTHORIZATION_B64 = (\n" in text
    assert "_RUNTIME_PAYLOAD_B64 = (\n" in text
    assert max(len(line) for line in text.splitlines()) <= 100
    assert "except SystemExit as signal:" in text
    assert "if signal.code in (None, 0):" in text
    ast.parse(text)
    compile(text, "<generated-wrapper>", "exec")

    notebook = json.loads(issuer.build_notebook(executable))
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) == 1


def test_manifest_binds_executable_and_contract_identities(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    prepared_at = datetime(2026, 8, 20, 21, 0, tzinfo=UTC)
    intent = issuer.build_intent(
        root,
        "f" * 40,
        prepared_at=prepared_at,
        window_minutes=180,
        intent_id="d" * 32,
    )
    authorization, authorization_bytes = issuer.build_authorization(
        intent,
        challenge=issuer.authorization_challenge(intent),
        confirmed_at=prepared_at + timedelta(minutes=1),
    )
    runtime_payload = (root / issuer.SUCCESSOR_RUNTIME_PATH).read_bytes()
    executable = issuer.render_executable_payload(
        root,
        authorization,
        authorization_bytes,
        runtime_payload,
    )
    notebook = issuer.build_notebook(executable)
    manifest = issuer.build_manifest(
        authorization,
        authorization_bytes,
        executable,
        notebook,
    )

    assert manifest.transaction_id == authorization.transaction_id
    assert manifest.executable_payload_sha256 == issuer._sha256(executable)
    assert manifest.experiment_contract_sha256 == intent.experiment_contract_sha256
    assert manifest.platform_observation_persisted is False


def test_terminal_receipt_rejects_pass_without_platform_observation() -> None:
    with pytest.raises(ValueError, match="durable platform observation"):
        issuer.TerminalReceipt(
            transaction_id="1" * 64,
            authorization_sha256="2" * 64,
            manifest_sha256="3" * 64,
            disposition=issuer.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            execution_outcome=issuer.ExecutionOutcome.PASSED,
            terminalized_at=datetime(2026, 8, 20, 22, 0, tzinfo=UTC),
            saved_version_id=123,
        )


def test_unused_terminal_disposition_cannot_contain_execution_evidence() -> None:
    with pytest.raises(ValueError, match="unused disposition"):
        issuer.TerminalReceipt(
            transaction_id="1" * 64,
            authorization_sha256="2" * 64,
            manifest_sha256="3" * 64,
            disposition=issuer.TerminalDisposition.EXPIRED_UNUSED,
            execution_attempted=True,
            terminalized_at=datetime(2026, 8, 20, 22, 0, tzinfo=UTC),
            saved_version_id=123,
        )
