from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    full_abc_local_environment_qualification_authorization_source_authority_parity as parity,
)

ROOT = Path(__file__).resolve().parents[3]
_FIXED_NOW = datetime(2026, 7, 19, 20, 0, tzinfo=UTC)


def _payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "authorization_id": (
            "auragateway-full-abc-local-environment-qualification-execution-authorization-v1"
        ),
        "decision": "AUTHORIZED",
        "source_main_merge_commit": parity.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT,
        "request_sha256": "a" * 64,
        "review_git_blob_sha": parity.FROZEN_REVIEW_GIT_BLOB_SHA,
        "authorization_issuance_review_sha256": "b" * 64,
        "materialization_record_sha256": "c" * 64,
        "dataset_manifest_sha256": "d" * 64,
        "runtime_factory": {
            "factory_path": "auragateway.runtime:create_runtime",
            "artifact_path": "src/auragateway/runtime.py",
            "artifact_sha256": "e" * 64,
        },
        "issued_at": _FIXED_NOW.isoformat(),
        "expires_at": (_FIXED_NOW + timedelta(minutes=240)).isoformat(),
        "maximum_workers": 2,
        "maximum_kaggle_sessions": 1,
        "maximum_model_requests": 8,
        "maximum_output_tokens_per_request": 32,
        "benchmark_trajectory_requests_permitted": 0,
        "customer_data_permitted": False,
        "credentials_permitted": False,
        "network_access_permitted": False,
        "external_spend": 0,
        "operator_confirmation_recorded": True,
        "measured_execution_authorized": False,
    }


def test_frozen_loader_accepts_current_authorization_source_authority() -> None:
    authorization = parity.validate_authorization_payload(_payload())

    assert authorization.source_main_merge_commit == "211a10757999b1b110cb1d9df172938cf6ed7969"


def test_frozen_loader_rejects_harness_source_commit_in_authorization_field() -> None:
    payload = _payload()
    payload["source_main_merge_commit"] = parity.HARNESS_SOURCE_COMMIT

    with pytest.raises(
        parity.FrozenLoaderParityError,
        match="incompatible with the frozen runtime loader",
    ) as exc_info:
        parity.validate_authorization_payload(payload)

    assert exc_info.value.details == ("source_main_merge_commit",)


def test_frozen_loader_rejects_extra_authorization_fields() -> None:
    payload = _payload()
    payload["unexpected"] = True

    with pytest.raises(parity.FrozenLoaderParityError) as exc_info:
        parity.validate_authorization_payload(payload)

    assert exc_info.value.details == ("unexpected",)


def test_repository_authority_parity_package_validates() -> None:
    summary = parity.validate_repository_package(ROOT)

    assert summary["status"] == ("AUTHORIZATION_SOURCE_AUTHORITY_PARITY_PACKAGE_VALID")
    assert summary["authorization_source_main_merge_commit"] == (
        parity.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT
    )
    assert summary["historical_harness_source_commit"] == parity.HARNESS_SOURCE_COMMIT
    assert summary["active_launcher_harness_source_commit"] == (
        "dceda98989386de7a4d57616f9f8a8023f866f10"
    )
    assert summary["authorization_source_binding_policy"] == (
        "CONTROL_PACKAGE_AUTHORIZATION_PARITY"
    )
    assert summary["evidence_zip_sha256"] == parity.EXPECTED_EVIDENCE_ZIP_SHA256
    assert summary["authorization_issued"] is False
    assert summary["model_requests_performed"] == 0


def test_record_preserves_distinct_authority_semantics() -> None:
    record = json.loads((ROOT / parity.RECORD_PATH).read_text(encoding="utf-8"))
    authority = record["authority_semantics"]

    assert authority["authorization_source_main_merge_commit"] == (
        parity.AUTHORIZATION_SOURCE_MAIN_MERGE_COMMIT
    )
    assert authority["harness_source_commit"] == parity.HARNESS_SOURCE_COMMIT
    assert (
        authority["authorization_source_main_merge_commit"] != (authority["harness_source_commit"])
    )
