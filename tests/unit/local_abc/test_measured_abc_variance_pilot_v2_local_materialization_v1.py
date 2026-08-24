from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import measured_abc_variance_pilot_v2_local_materialization_v1 as subject
from auragateway.local_abc.measured_abc_variance_pilot_v2 import (
    V1_PILOT_SCHEDULE_PATH,
)
from auragateway.local_abc.measured_abc_variance_pilot_v2_output_contract import (
    build_generation_contract,
    compile_standalone_admission_spec,
    sha256_json,
    strict_response_format,
)

ROOT = Path(__file__).resolve().parents[3]


def _repo(tmp_path: Path) -> Path:
    source = ROOT / V1_PILOT_SCHEDULE_PATH
    target = tmp_path / V1_PILOT_SCHEDULE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return tmp_path


def test_manifest_binds_all_deterministic_contract_artifacts(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    manifest = subject.build_manifest(repo_root)

    assert manifest.source_v1_schedule_sha256 == (
        "da8964631aa690e55e14b8b0e3cd484dc0f9d7fb90090bfad32241b117aa06b7"
    )
    assert manifest.strict_response_format_sha256 == sha256_json(strict_response_format())
    assert manifest.standalone_admission_spec_sha256 == sha256_json(
        compile_standalone_admission_spec().model_dump(mode="json")
    )
    assert manifest.generation_contract_sha256 == sha256_json(
        build_generation_contract().model_dump(mode="json")
    )
    assert manifest.pretreatment_request_count == 24
    assert manifest.pilot_request_count == 216
    assert manifest.maximum_total_model_requests == 240
    assert manifest.tokenizer_budget_proof_complete is False
    assert manifest.pilot_execution_authorized is False
    assert manifest.final_measured_abc_execution_authorized is False


def test_materialize_and_validate_are_deterministic_and_idempotent(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)

    first = subject.materialize(repo_root)
    assert first["materialized_path_count"] == 6

    expected_paths = (
        subject.PILOT_SCHEDULE_PATH,
        subject.NEUTRAL_PLAN_PATH,
        subject.STRICT_RESPONSE_FORMAT_PATH,
        subject.STANDALONE_ADMISSION_SPEC_PATH,
        subject.GENERATION_CONTRACT_PATH,
        subject.MATERIALIZATION_MANIFEST_PATH,
    )
    first_bytes = {path: (repo_root / path).read_bytes() for path in expected_paths}

    validation = subject.validate_materialization(repo_root)
    assert validation["status"] == ("VARIANCE_PILOT_SUCCESSOR_V2_LOCAL_MATERIALIZATION_VALID")
    assert validation["tokenizer_budget_proof_complete"] is False
    assert validation["pilot_execution_authorized"] is False

    subject.materialize(repo_root)
    second_bytes = {path: (repo_root / path).read_bytes() for path in expected_paths}
    assert second_bytes == first_bytes


def test_validation_rejects_materialized_artifact_drift(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    subject.materialize(repo_root)
    path = repo_root / subject.GENERATION_CONTRACT_PATH
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(subject.LocalMaterializationError) as observed:
        subject.validate_materialization(repo_root)

    assert observed.value.error_code == "V2_LOCAL_MATERIALIZATION_DRIFT"
    assert observed.value.path == subject.GENERATION_CONTRACT_PATH
