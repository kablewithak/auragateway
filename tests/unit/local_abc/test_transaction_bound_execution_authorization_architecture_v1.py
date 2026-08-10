from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    transaction_bound_execution_authorization_architecture_v1 as architecture,
)

ROOT = Path(__file__).resolve().parents[3]


def test_current_architecture_validates() -> None:
    result = architecture.validate(ROOT)

    assert result["status"] == ("TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE_V1_VALID")
    assert result["decision"] == "TRANSACTION_BOUND_EXECUTION_ARTIFACT"
    assert result["authorization_specific_kaggle_inputs"] == 0
    assert result["authorization_producer_notebooks"] == 0
    assert result["manual_confirmation_json_files"] == 0
    assert result["runtime_anti_replay_established"] is False
    assert result["gpu_execution_authorized"] is False
    assert result["next_gate"] == ("IMPLEMENT_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1")


def test_record_rejects_authorization_specific_kaggle_input() -> None:
    path = ROOT / architecture.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["operator_burden_budget"]["maximum_authorization_specific_kaggle_inputs"] = 1

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_record_rejects_runtime_antireplay_claim() -> None:
    path = ROOT / architecture.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["replay"]["runtime_anti_replay_established"] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)


def test_record_rejects_gpu_authority_claim() -> None:
    path = ROOT / architecture.RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["implementation_strategy"]["gpu_execution_authorized_by_this_architecture"] = True

    with pytest.raises(ValidationError):
        architecture.ArchitectureRecord.model_validate(payload)
