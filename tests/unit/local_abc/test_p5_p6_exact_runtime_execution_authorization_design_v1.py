"""Tests for exact-runtime P5/P6 authorization design V1."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

MODULE_PATH = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_execution_authorization_design_v1.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("authorization_design_v1", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_design_is_not_live_authority() -> None:
    module = _load_module()
    record = module.build_record(Path("."))
    assert record.design_status == "DESIGN_FROZEN_NOT_IMPLEMENTED"
    assert record.safety.live_authorization_issued is False
    assert record.safety.runtime_execution_authorized is False


def test_exact_merged_implementation_is_bound() -> None:
    module = _load_module()
    record = module.build_record(Path("."))
    assert record.implementation.implementation_merge_commit == (
        "9cc06c02c372fa2e7637c432759e7a1d4db56e9e"
    )
    assert record.implementation.runtime_script_sha256 == (
        "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
    )
    assert record.implementation.notebook_sha256 == (
        "cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"
    )


def test_budget_matches_implementation_ceiling() -> None:
    module = _load_module()
    budget = module.ExecutionBudget()
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0


def test_platform_and_freshness_fail_closed() -> None:
    module = _load_module()
    platform = module.PlatformContract()
    freshness = module.FreshnessContract()
    assert platform.accelerator == "T4_X2"
    assert platform.allocated_gpu_count == 2
    assert platform.internet_enabled is False
    assert freshness.maximum_platform_observation_age_minutes == 15
    assert freshness.maximum_operator_confirmation_age_minutes == 15


def test_authorization_payload_matches_runtime_consumer() -> None:
    module = _load_module()
    payload = module.build_record(Path(".")).authorization_payload
    assert payload.authorization_filename == "execution_authorization_v1.json"
    assert payload.scope == "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"
    assert payload.decision == "AUTHORIZED"
    assert payload.lifecycle == "ISSUED"
    assert payload.single_use_required is True


def test_terminal_vocabulary_is_complete() -> None:
    module = _load_module()
    terminal = module.build_record(Path(".")).terminalization
    assert terminal.terminal_dispositions == tuple(module.TerminalDisposition)
    assert terminal.known_execution_outcomes == tuple(module.ExecutionOutcome)
    assert module.TerminalDisposition.OUTCOME_UNKNOWN in terminal.terminal_dispositions


def test_terminal_authority_is_never_reusable() -> None:
    module = _load_module()
    terminal = module.TerminalizationContract(
        terminal_dispositions=tuple(module.TerminalDisposition),
        known_execution_outcomes=tuple(module.ExecutionOutcome),
    )
    assert terminal.terminal_authority_reusable is False
    assert terminal.terminal_receipt_non_overwriting is True


def test_pilot_and_final_authority_remain_false() -> None:
    module = _load_module()
    safety = module.build_record(Path(".")).safety
    assert safety.pilot_execution_authorized is False
    assert safety.final_measured_abc_execution_authorized is False


def test_exact_confirmation_phrase_is_frozen() -> None:
    module = _load_module()
    assert module.CONFIRMATION_PHRASE == (
        "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
        "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION"
    )


def test_expected_authorities_have_exact_identities() -> None:
    module = _load_module()
    record = module.build_record(Path("."))
    assert len(record.authorities) == 8
    for authority in record.authorities:
        path = Path(authority.path)
        assert path.is_file()
        assert authority.sha256 == module._sha256_file(path)
        assert authority.size_bytes == path.stat().st_size


def test_generated_record_is_deterministic(tmp_path: Path) -> None:
    module = _load_module()
    record = module.build_record(Path("."))
    payload_a = module._canonical_json(record)
    payload_b = module._canonical_json(record)
    assert payload_a == payload_b
    parsed = json.loads(payload_a)
    assert parsed["safety"]["runtime_execution_authorized"] is False


def test_extra_fields_are_rejected() -> None:
    module = _load_module()
    with pytest.raises(ValidationError):
        module.ExecutionBudget.model_validate(
            {
                "maximum_kaggle_sessions": 1,
                "maximum_saved_versions": 1,
                "maximum_model_requests": 6,
                "maximum_worker_starts": 3,
                "maximum_model_loads": 3,
                "maximum_hidden_retries": 0,
                "maximum_replacement_workers": 0,
                "maximum_external_network_requests": 0,
                "maximum_benchmark_trajectory_requests": 0,
                "maximum_external_spend": 0,
                "unexpected": True,
            }
        )
