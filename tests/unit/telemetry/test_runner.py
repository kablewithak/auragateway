from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.telemetry.runner import (
    TelemetryIntegrityError,
    build_telemetry_integrity,
    verify_telemetry_integrity,
)


def _copy_fixture(tmp_path: Path) -> Path:
    source = Path("data/provider_fixtures/telemetry/fixtures.json")
    target = tmp_path / source
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def test_build_and_verify_gate_four_evidence(tmp_path: Path) -> None:
    _copy_fixture(tmp_path)
    built = build_telemetry_integrity(tmp_path)
    verified = verify_telemetry_integrity(tmp_path)
    assert built == verified
    assert built.fixture_count == 8
    assert built.negative_control_count == 6
    assert built.gate_4_passed is True
    assert built.measured_execution_permitted is False


def test_verifier_rejects_fixture_drift(tmp_path: Path) -> None:
    fixture_path = _copy_fixture(tmp_path)
    build_telemetry_integrity(tmp_path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["cases"][0]["telemetry"]["cached_input_tokens"] = 699
    fixture_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(TelemetryIntegrityError, match="hash does not match"):
        verify_telemetry_integrity(tmp_path)


def test_frozen_repo_evidence_verifies() -> None:
    summary = verify_telemetry_integrity(Path("."))
    assert summary.gate_4_passed is True
