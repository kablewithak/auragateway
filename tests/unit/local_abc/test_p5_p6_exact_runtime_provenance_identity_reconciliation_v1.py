"""Tests for P5/P6 provenance identity reconciliation V1."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_provenance_identity_reconciliation_v1.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("p5_p6_provenance_reconciliation_v1", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_repo(tmp_path: Path, module: Any) -> Path:
    source_root = Path.cwd()
    repo_root = tmp_path / "repo"
    required = (
        module.IMPLEMENTATION_SOURCE_PATH,
        module.IMPLEMENTATION_TEMPLATE_PATH,
        module.IMPLEMENTATION_TEST_PATH,
        module.IMPLEMENTATION_ADR_PATH,
        module.IMPLEMENTATION_REPORT_PATH,
        module.IMPLEMENTATION_RUNBOOK_PATH,
        module.IMPLEMENTATION_REVIEW_PATH,
        module.IMPLEMENTATION_RECORD_PATH,
        module.IMPLEMENTATION_NOTEBOOK_PATH,
    )
    for relative in required:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def test_reconciliation_is_pre_execution_and_retains_runtime_identity(
    tmp_path: Path,
) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)

    generated = module.generate(repo_root)
    validated = module.validate(repo_root)

    assert generated["status"] == "RECONCILED_BEFORE_EXECUTION"
    assert validated["implementation_provenance_consistent"] is True
    assert validated["corrected_path_count"] == 2
    assert validated["historical_generated_artifacts_retained"] is True
    assert validated["executable_runtime_identity_changed"] is False
    assert validated["live_authorization_issued"] is False
    assert validated["runtime_execution_authorized"] is False
    assert validated["p5_p6_exact_runtime_requalified"] is False


def test_record_is_deterministic(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)

    first = module.generate(repo_root)
    first_bytes = (repo_root / module.RECORD_PATH).read_bytes()
    second = module.generate(repo_root)
    second_bytes = (repo_root / module.RECORD_PATH).read_bytes()

    assert first == second
    assert first_bytes == second_bytes
    assert module.validate(repo_root)["record_sha256"] == module._sha256_bytes(first_bytes)


def test_only_two_historical_static_claims_are_superseded(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)
    record = module.build_record(repo_root)

    assert tuple(item.role for item in record.corrections) == (
        "implementation_adr",
        "implementation_report",
    )
    assert record.corrections[0].stale_recorded_sha256 == (
        module.IMPLEMENTATION_ADR_STALE_RECORDED_SHA256
    )
    assert record.corrections[0].committed_sha256 == (module.IMPLEMENTATION_ADR_COMMITTED_SHA256)
    assert record.corrections[1].stale_recorded_sha256 == (
        module.IMPLEMENTATION_REPORT_STALE_RECORDED_SHA256
    )
    assert record.corrections[1].committed_sha256 == (module.IMPLEMENTATION_REPORT_COMMITTED_SHA256)
    assert len(record.unaffected_static_artifacts) == 4


def test_committed_document_drift_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)
    target = repo_root / module.IMPLEMENTATION_ADR_PATH
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(module.ReconciliationError) as caught:
        module.build_record(repo_root)

    assert caught.value.error_code == "P5_P6_PROVENANCE_ARTIFACT_IDENTITY_DRIFT"


def test_historical_generated_artifact_drift_fails_closed(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)
    target = repo_root / module.IMPLEMENTATION_REVIEW_PATH
    target.write_text("{}\n", encoding="utf-8")

    with pytest.raises(module.ReconciliationError) as caught:
        module.build_record(repo_root)

    assert caught.value.error_code == "P5_P6_PROVENANCE_ARTIFACT_IDENTITY_DRIFT"


def test_live_authorization_blocks_reconciliation(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)
    live = repo_root / module.LIVE_AUTHORIZATION_PATH
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text("{}\n", encoding="utf-8")

    with pytest.raises(module.ReconciliationError) as caught:
        module.build_record(repo_root)

    assert caught.value.error_code == "P5_P6_PROVENANCE_LIFECYCLE_ALREADY_STARTED"


def test_correction_record_rejects_mutation(tmp_path: Path) -> None:
    module = _load_module()
    repo_root = _fixture_repo(tmp_path, module)
    module.generate(repo_root)
    target = repo_root / module.RECORD_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["root_cause"] = "OTHER"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(module.ReconciliationError) as caught:
        module.validate(repo_root)

    assert caught.value.error_code == "P5_P6_PROVENANCE_RECONCILIATION_RECORD_DRIFT"
