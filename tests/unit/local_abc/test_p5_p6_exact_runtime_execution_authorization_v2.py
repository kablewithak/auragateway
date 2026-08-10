from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import p5_p6_exact_runtime_execution_authorization_v2 as issuer


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    paths = [
        issuer.AUTHORIZATION_DESIGN_RECORD_PATH,
        issuer.P5_P6_IMPLEMENTATION_REVIEW_PATH,
        issuer.P5_P6_IMPLEMENTATION_RECORD_PATH,
        issuer.P5_P6_IMPLEMENTATION_SOURCE_PATH,
        issuer.P5_P6_IMPLEMENTATION_TEMPLATE_PATH,
        issuer.P5_P6_IMPLEMENTATION_TEST_PATH,
        issuer.P5_P6_NOTEBOOK_PATH,
        issuer.TRANSPORT_DESIGN_RECORD_PATH,
        issuer.TRANSPORT_SOURCE_PATH,
        issuer.TRANSPORT_TEST_PATH,
        issuer.V5_ACCEPTANCE_RECORD_PATH,
        issuer.SOURCE_PATH,
        issuer.TEST_PATH,
        issuer.ADR_PATH,
        issuer.REPORT_PATH,
        issuer.RUNBOOK_PATH,
    ]
    for relative in paths:
        src = source_root / relative
        dst = tmp_path / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return tmp_path


def confirmation(now: datetime) -> issuer.IssuanceConfirmation:
    return issuer.IssuanceConfirmation(
        confirmation_id=("auragateway-exact-runtime-p5-p6-execution-authorization-confirmation-v2"),
        operator_confirmed=True,
        exact_confirmation_phrase=issuer.CONFIRMATION_PHRASE,
        confirmed_at=now,
        authorization_window_minutes=180,
        confirmed_issuer_merge_commit="a" * 40,
        confirmed_authorization_design_record_sha256=(issuer.AUTHORIZATION_DESIGN_RECORD_SHA256),
        confirmed_scope=issuer.AUTHORIZATION_SCOPE,
        confirmed_implementation_merge_commit=issuer.P5_P6_IMPLEMENTATION_MERGE_COMMIT,
        confirmed_implementation_record_sha256=issuer.P5_P6_IMPLEMENTATION_RECORD_SHA256,
        confirmed_implementation_review_sha256=issuer.P5_P6_IMPLEMENTATION_REVIEW_SHA256,
        confirmed_transport_design_sha256=issuer.TRANSPORT_DESIGN_RECORD_SHA256,
        confirmed_notebook_sha256=issuer.P5_P6_NOTEBOOK_SHA256,
        confirmed_runtime_script_sha256=issuer.P5_P6_RUNTIME_SCRIPT_SHA256,
        confirmed_wrapper_code_sha256=issuer.P5_P6_WRAPPER_CODE_SHA256,
        confirmed_v5_acceptance_sha256=issuer.V5_ACCEPTANCE_RECORD_SHA256,
        execution_limits=issuer.ExecutionLimits(),
        platform=issuer.PlatformObservation(
            observed_at=now - timedelta(minutes=1),
            capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
            accelerator="T4_X2",
            allocated_gpu_count=2,
            internet_enabled=False,
            external_network_access_permitted=False,
            credentials_permitted=False,
            customer_data_permitted=False,
        ),
    )


def test_generate_and_validate_are_inert(repo: Path) -> None:
    generated = issuer.generate(repo)
    validated = issuer.validate_implementation(repo)
    assert generated["live_authorization_issued"] is False
    assert validated["runtime_execution_authorized"] is False
    assert not (repo / issuer.AUTHORIZATION_PATH).exists()
    assert not (repo / issuer.TERMINAL_RECEIPT_PATH).exists()


def test_generated_record_binds_current_v2_and_transport(repo: Path) -> None:
    issuer.generate(repo)
    record = json.loads((repo / issuer.RECORD_PATH).read_text(encoding="utf-8"))
    roles = {item["role"]: item for item in record["bound_artifacts"]}
    assert roles["v2_implementation_review"]["sha256"] == issuer.P5_P6_IMPLEMENTATION_REVIEW_SHA256
    assert roles["transport_design"]["sha256"] == issuer.TRANSPORT_DESIGN_RECORD_SHA256
    assert record["transport_round_trip_required_at_issue"] is True
    assert record["transfer_filename"] == "execution_authorization_v1.json"


def test_candidate_authorization_round_trips_current_transport() -> None:
    now = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    auth = issuer._build_authorization(confirmation(now), "a" * 40, now)
    payload = issuer._transport_json_bytes(auth)
    result = issuer._require_transport_round_trip(payload, now)
    assert result["transport_contract"] == "GOVERNED_ROOT_EXACT_FLAT_V1"
    assert result["exact_flat_file_count"] == 3


def test_transport_rejects_pretty_authorization_json() -> None:
    now = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    auth = issuer._build_authorization(confirmation(now), "a" * 40, now)
    pretty = issuer._artifact_json_bytes(auth)
    with pytest.raises(issuer.AuthorizationIssuerError) as caught:
        issuer._require_transport_round_trip(pretty, now)
    assert caught.value.error_code == "P5_P6_V2_AUTHORIZATION_TRANSPORT_ROUND_TRIP_FAILED"


def test_stale_confirmation_fails_closed() -> None:
    now = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    stale = confirmation(now - timedelta(minutes=16))
    with pytest.raises(issuer.AuthorizationIssuerError) as caught:
        issuer._require_confirmation_fresh(stale, now)
    assert caught.value.error_code == "P5_P6_V2_AUTHORIZATION_CONFIRMATION_STALE"


def test_terminal_receipt_requires_evidence_for_known_failure() -> None:
    with pytest.raises(ValueError):
        issuer.AuthorizationTerminalReceipt(
            receipt_id=(
                "auragateway-exact-runtime-p5-p6-requalification-v2-authorization-terminal-v1"
            ),
            authorization_id=issuer.AUTHORIZATION_ID,
            authorization_sha256="a" * 64,
            issuer_merge_commit="b" * 40,
            disposition=issuer.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            execution_outcome=issuer.ExecutionOutcome.FAILED,
            terminalized_at=datetime(2026, 8, 10, 15, 0, tzinfo=UTC),
        )


def test_replay_contract_is_false() -> None:
    now = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    auth = issuer._build_authorization(confirmation(now), "a" * 40, now)
    assert auth.single_use is True
    assert auth.authorization_reusable is False
    assert auth.unchanged_replay_authorized is False
    assert auth.pilot_execution_authorized is False
    assert auth.final_measured_abc_execution_authorized is False


def test_current_v2_validator_satisfies_preexecution_contract() -> None:
    source_root = Path(__file__).resolve().parents[3]
    issuer._require_v2_preexecution_contract(source_root)
