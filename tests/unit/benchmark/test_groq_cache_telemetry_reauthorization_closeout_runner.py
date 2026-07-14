from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.groq_cache_telemetry_reauthorization_closeout_runner import (
    ReauthorizationCloseoutError,
    validate_reauthorization_closeout,
)

_CLOSEOUT_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-closeout-v1")
_EXECUTION_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Reauthorization_Closeout.md")
_REQUEST_SHA256 = "23cac23a165812ae8e9908e9d0609fb533359a30ed4386d76bcfb82e6a9d17c9"
_PROTECTED_RAW_SHA256 = "636f67735a5212ffdc3714204fa45279a79a880fbbe9c1afd756e18796724b0b"
_PROTECTED_PARSED_SHA256 = "dcfe790769270b53214293ca0cc0c7579e094fd2d815986723a73efea1ef9d26"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _records_payload() -> dict[str, object]:
    records = []
    for index, role, offset_seconds, offset_ms, raw_size, parsed_size in (
        (0, "cold_wire_probe", 0, 0, 698, 854),
        (1, "warm_wire_probe", 10, 10000, 699, 855),
    ):
        records.append(
            {
                "attempt_index": index,
                "request_role": role,
                "planned_offset_seconds": offset_seconds,
                "observed_offset_ms": offset_ms,
                "provider_request_sha256": _REQUEST_SHA256,
                "status": "succeeded",
                "provider_call_made": True,
                "provider_error_code": None,
                "http_status_code": 200,
                "raw_body_sha256": f"{index + 1:064x}",
                "raw_body_byte_count": raw_size,
                "parsed_response_sha256": f"{index + 11:064x}",
                "parsed_response_byte_count": parsed_size,
                "installed_sdk_version": "1.5.0",
                "raw_billing_observation_state": "field_absent",
                "raw_billing_field_present": False,
                "raw_billing_cached_tokens": None,
                "parsed_billing_observation_state": "field_absent",
                "parsed_billing_field_present": False,
                "parsed_billing_cached_tokens": None,
                "raw_parsed_numeric_values_match": None,
                "estimated_cost_microusd": 200,
            }
        )
    return {
        "schema_version": "1.0.0",
        "authorization_id": "groq-cache-telemetry-reauthorization-auth-v1",
        "execution_id": "groq-cache-telemetry-reauthorization-v1",
        "records": records,
    }


def _report_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "authorization_id": "groq-cache-telemetry-reauthorization-auth-v1",
        "execution_id": "groq-cache-telemetry-reauthorization-v1",
        "status": "completed",
        "outcome": "wire_field_absent",
        "planned_attempt_count": 2,
        "provider_call_count": 2,
        "successful_call_count": 2,
        "provider_error_count": 0,
        "observation_invalid_count": 0,
        "skipped_attempt_count": 0,
        "raw_numeric_sample_count": 0,
        "parsed_numeric_sample_count": 0,
        "raw_absent_sample_count": 2,
        "estimated_cost_microusd": 400,
        "live_provider_called": True,
        "execution_completed": True,
        "authorization_consumed": True,
        "rerun_permitted": False,
        "resume_permitted": False,
        "exact_provider_wire_omission_claim_permitted": True,
        "sdk_live_parse_defect_claim_permitted": False,
        "provider_cache_usage_claim_permitted_for_execution": False,
        "provider_cache_savings_claim_permitted": False,
        "benchmark_execution_permitted": False,
        "benchmark_claims_permitted": False,
        "comparison_eligible": False,
        "next_gate": "groq_cache_telemetry_reauthorization_closeout",
    }


def _rebind_closeout(repo_root: Path) -> None:
    closeout_path = repo_root / _CLOSEOUT_ROOT / "closeout.json"
    closeout = _json_object(closeout_path)
    bindings = closeout["execution_bindings"]
    assert isinstance(bindings, list)
    for binding in bindings:
        assert isinstance(binding, dict)
        path = binding["path"]
        assert isinstance(path, str)
        binding["sha256"] = _sha256(repo_root / path)
    _write_json(closeout_path, closeout)

    manifest_path = repo_root / _CLOSEOUT_ROOT / "manifest.json"
    manifest = _json_object(manifest_path)
    manifest["closeout_sha256"] = _sha256(closeout_path)
    manifest["report_sha256"] = _sha256(repo_root / _REPORT_PATH)
    manifest["execution_report_sha256"] = _sha256(repo_root / _EXECUTION_ROOT / "report.json")
    manifest["execution_manifest_sha256"] = _sha256(repo_root / _EXECUTION_ROOT / "manifest.json")
    _write_json(manifest_path, manifest)


def _write_execution_manifest(repo_root: Path) -> None:
    root = repo_root / _EXECUTION_ROOT
    manifest = {
        "schema_version": "1.0.0",
        "authorization_id": "groq-cache-telemetry-reauthorization-auth-v1",
        "authorization_sha256": _sha256(root / "authorization.json"),
        "runtime_policy_sha256": _sha256(root / "runtime_policy.json"),
        "activation_manifest_sha256": _sha256(root / "activation_manifest.json"),
        "journal_sha256": _sha256(root / "journal.jsonl"),
        "run_records_sha256": _sha256(root / "run_records.json"),
        "report_sha256": _sha256(root / "report.json"),
        "protected_raw_responses_sha256": _PROTECTED_RAW_SHA256,
        "protected_parsed_responses_sha256": _PROTECTED_PARSED_SHA256,
        "live_provider_called": True,
        "execution_completed": True,
    }
    _write_json(root / "manifest.json", manifest)


def _prepare_repo(repo_root: Path) -> None:
    for relative_path in (
        _CLOSEOUT_ROOT / "closeout.json",
        _CLOSEOUT_ROOT / "manifest.json",
        _REPORT_PATH,
    ):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)

    execution_root = repo_root / _EXECUTION_ROOT
    execution_root.mkdir(parents=True, exist_ok=True)
    for name in (
        "authorization.json",
        "runtime_policy.json",
        "activation_report.json",
        "activation_manifest.json",
    ):
        _write_json(execution_root / name, {"fixture": name})

    records = _records_payload()
    _write_json(execution_root / "run_records.json", records)
    journal_lines = [
        json.dumps(record, separators=(",", ":"))
        for record in cast(list[dict[str, object]], records["records"])
    ]
    (execution_root / "journal.jsonl").write_text(
        "\n".join(journal_lines) + "\n",
        encoding="utf-8",
    )
    _write_json(execution_root / "report.json", _report_payload())
    _write_execution_manifest(repo_root)
    _rebind_closeout(repo_root)


def _refresh_after_execution_change(repo_root: Path) -> None:
    _write_execution_manifest(repo_root)
    _rebind_closeout(repo_root)


def test_validator_accepts_terminal_closeout(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)

    summary = validate_reauthorization_closeout(tmp_path)

    assert summary.provider_call_count == 2
    assert summary.successful_call_count == 2
    assert summary.raw_billing_field_absent_count == 2
    assert summary.raw_billing_numeric_sample_count == 0
    assert summary.authorization_consumed is True
    assert summary.provider_calls_permitted is False
    assert summary.rerun_permitted is False


def test_validator_reads_no_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_repo(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_reauthorization_closeout(tmp_path)

    assert summary.provider_calls_permitted is False


def test_validator_rejects_bound_execution_report_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    report_path = tmp_path / _EXECUTION_ROOT / "report.json"
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="bound execution asset no longer matches",
    ):
        validate_reauthorization_closeout(tmp_path)


def test_validator_rejects_closeout_hash_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    closeout_path = tmp_path / _CLOSEOUT_ROOT / "closeout.json"
    closeout_path.write_text(
        closeout_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="closeout JSON no longer matches",
    ):
        validate_reauthorization_closeout(tmp_path)


def test_validator_rejects_report_content_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    report_path = tmp_path / _REPORT_PATH
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="closeout report no longer matches",
    ):
        validate_reauthorization_closeout(tmp_path)


def test_validator_rejects_sdk_version_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    records_path = tmp_path / _EXECUTION_ROOT / "run_records.json"
    payload = _json_object(records_path)
    records = payload["records"]
    assert isinstance(records, list)
    first = records[0]
    assert isinstance(first, dict)
    first["installed_sdk_version"] = "1.5.1"
    _write_json(records_path, payload)
    _refresh_after_execution_change(tmp_path)

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="successful execution attempt no longer matches",
    ):
        validate_reauthorization_closeout(tmp_path)


def test_validator_rejects_raw_field_state_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    records_path = tmp_path / _EXECUTION_ROOT / "run_records.json"
    payload = _json_object(records_path)
    records = payload["records"]
    assert isinstance(records, list)
    first = records[0]
    assert isinstance(first, dict)
    first["raw_billing_observation_state"] = "observed_zero"
    first["raw_billing_field_present"] = True
    first["raw_billing_cached_tokens"] = 0
    _write_json(records_path, payload)
    _refresh_after_execution_change(tmp_path)

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="Raw and parsed cache telemetry no longer match",
    ):
        validate_reauthorization_closeout(tmp_path)


def test_validator_rejects_execution_count_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    report_path = tmp_path / _EXECUTION_ROOT / "report.json"
    payload = _json_object(report_path)
    payload["successful_call_count"] = 1
    payload["provider_error_count"] = 1
    _write_json(report_path, payload)
    _refresh_after_execution_change(tmp_path)

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="Execution counts do not match",
    ):
        validate_reauthorization_closeout(tmp_path)


def test_validator_rejects_protected_hash_drift(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    manifest_path = tmp_path / _EXECUTION_ROOT / "manifest.json"
    payload = _json_object(manifest_path)
    payload["protected_raw_responses_sha256"] = "f" * 64
    _write_json(manifest_path, payload)
    _rebind_closeout(tmp_path)

    with pytest.raises(
        ReauthorizationCloseoutError,
        match="Execution manifest does not reconcile",
    ):
        validate_reauthorization_closeout(tmp_path)
