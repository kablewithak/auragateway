"""Tests for successor P5/P6 authorization transport V1."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

MODULE_PATH = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_successor_authorization_transport_v1.py"
)


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("successor_auth_transport_v1", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _authorization_bytes(module: Any, now: datetime) -> bytes:
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": module.AUTHORIZATION_ID,
        "authorization_filename": module.AUTHORIZATION_FILENAME,
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": module.AUTHORIZATION_SCOPE,
        "successor_merge_commit": "2b1841aee4397ae0c72bad6b2c9e7069835d8399",
        "issuer_merge_commit": "a" * 40,
        "issued_at": (now - timedelta(minutes=1)).isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(minutes=179)).isoformat(timespec="seconds"),
        "runtime_script_sha256": module.RUNTIME_SCRIPT_SHA256,
        "implementation_review_sha256": module.IMPLEMENTATION_REVIEW_SHA256,
        "design_record_sha256": module.DESIGN_RECORD_SHA256,
        "mechanism_admission_contract_sha256": module.MECHANISM_CONTRACT_SHA256,
        "implementation_addendum_sha256": module.IMPLEMENTATION_ADDENDUM_SHA256,
        "runtime_execution_authorized": True,
        "single_use": True,
        "every_terminal_attempt_consumes_authorization": True,
        "unchanged_replay_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "hidden_retries_permitted": 0,
        "authorization_reusable": False,
    }
    return cast(bytes, module.canonical_json_bytes(payload))


def _governed_root(module: Any, input_root: Path, suffix: str = "") -> Path:
    notebook_name = module.CONTROL_NOTEBOOK_NAME + suffix
    return cast(
        Path,
        input_root
        / "notebooks"
        / "kabomolefe"
        / notebook_name
        / module.CONTROL_OUTPUT_DIRECTORY_NAME,
    )


def test_materialized_control_package_validates(tmp_path: Path) -> None:
    module = _module()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    authorization_bytes = _authorization_bytes(module, now)
    root = _governed_root(module, tmp_path)
    receipt = module.materialize_control_package(root, authorization_bytes)
    verification = module.validate_control_package(
        tmp_path,
        require_live_authorization=True,
        now=now,
    )
    assert receipt.status == "MATERIALIZED"
    assert verification.exact_flat_file_count == 3
    assert verification.authorization_sha256 == module.sha256_bytes(authorization_bytes)
    assert verification.producer_notebook_name == module.CONTROL_NOTEBOOK_NAME


def test_multiple_governed_roots_fail_closed(tmp_path: Path) -> None:
    module = _module()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    authorization_bytes = _authorization_bytes(module, now)
    module.materialize_control_package(
        _governed_root(module, tmp_path),
        authorization_bytes,
    )
    second = (
        tmp_path
        / "notebooks"
        / "other-owner"
        / module.CONTROL_NOTEBOOK_NAME
        / module.CONTROL_OUTPUT_DIRECTORY_NAME
    )
    module.materialize_control_package(second, authorization_bytes)
    with pytest.raises(module.AuthorizationTransportError) as captured:
        module.validate_control_package(
            tmp_path,
            require_live_authorization=True,
            now=now,
        )
    assert captured.value.error_code == (
        "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_ROOT_CARDINALITY_INVALID"
    )


def test_extra_control_member_fails_closed(tmp_path: Path) -> None:
    module = _module()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    root = _governed_root(module, tmp_path)
    module.materialize_control_package(root, _authorization_bytes(module, now))
    (root / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(module.AuthorizationTransportError) as captured:
        module.validate_control_package(
            tmp_path,
            require_live_authorization=True,
            now=now,
        )
    assert captured.value.error_code == ("P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_FILE_SET_DRIFT")


def test_receipt_binding_drift_fails_closed(tmp_path: Path) -> None:
    module = _module()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    root = _governed_root(module, tmp_path)
    module.materialize_control_package(root, _authorization_bytes(module, now))
    receipt_path = root / module.MATERIALIZATION_RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert isinstance(receipt, dict)
    receipt["authorization_sha256"] = "f" * 64
    receipt_path.write_bytes(module.canonical_json_bytes(receipt))
    with pytest.raises(module.AuthorizationTransportError) as captured:
        module.validate_control_package(
            tmp_path,
            require_live_authorization=True,
            now=now,
        )
    assert captured.value.error_code == (
        "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_RECEIPT_BINDING_DRIFT"
    )


def test_control_notebook_is_cpu_only_and_unexecuted() -> None:
    module = _module()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    notebook = module.build_control_materializer_notebook(
        _authorization_bytes(module, now),
        now=now,
    )
    cells = notebook["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 2
    code = cells[1]
    assert isinstance(code, dict)
    assert code["execution_count"] is None
    assert code["outputs"] == []
    source = "".join(code["source"])
    assert "import torch" not in source
    assert "import vllm" not in source
    assert "runtime_execution_performed=false" in source
    assert "gpu_execution_performed=false" in source
    metadata = notebook["metadata"]
    assert isinstance(metadata, dict)
    kaggle = metadata["kaggle"]
    assert isinstance(kaggle, dict)
    assert kaggle["accelerator"] == "none"
    assert kaggle["isInternetEnabled"] is False


def test_authorization_noncanonical_bytes_are_rejected() -> None:
    module = _module()
    now = datetime(2026, 8, 22, 20, 0, 0, tzinfo=UTC)
    payload = json.loads(_authorization_bytes(module, now))
    noncanonical = json.dumps(payload, indent=2).encode("utf-8")
    with pytest.raises(module.AuthorizationTransportError) as captured:
        module.validate_authorization_bytes(
            noncanonical,
            require_live=True,
            now=now,
        )
    assert captured.value.error_code == ("P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_NON_CANONICAL")


def test_transport_constants_match_merged_runtime_consumer() -> None:
    module = _module()
    runtime_template = Path(
        "src/auragateway/local_abc/templates/p5_p6_mechanism_admission_successor_v1.py.tmpl"
    )
    if not runtime_template.is_file():
        pytest.skip("merged successor runtime template is not present in isolated candidate tree")
    source = runtime_template.read_text(encoding="utf-8")
    expected_literals = (
        f'AUTHORIZATION_SCOPE = "{module.AUTHORIZATION_SCOPE}"',
        f'AUTHORIZATION_CONTROL_NOTEBOOK_NAME = "{module.CONTROL_NOTEBOOK_NAME}"',
        (f'AUTHORIZATION_CONTROL_OUTPUT_DIRECTORY = "{module.CONTROL_OUTPUT_DIRECTORY_NAME}"'),
        f'AUTHORIZATION_CONTROL_PACKAGE_ID = (\n    "{module.CONTROL_PACKAGE_ID}"\n)',
        f'AUTHORIZATION_TRANSPORT_CONTRACT = "{module.TRANSPORT_CONTRACT}"',
        "MAXIMUM_AUTHORIZATION_BYTES = 64 * 1024",
        '"maximum_model_requests": 6',
        '"maximum_worker_starts": 3',
        '"maximum_model_loads": 3',
        '"hidden_retries_permitted": 0',
    )
    for literal in expected_literals:
        assert literal in source
