from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p5_p6_exact_runtime_authorization_transport_v1 as transport,
)


def _authorization_bytes(now: datetime | None = None) -> bytes:
    current = datetime.now(UTC) if now is None else now
    payload = {
        "schema_version": "1.0.0",
        "authorization_id": transport.AUTHORIZATION_ID,
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": transport.AUTHORIZATION_SCOPE,
        "issued_at": (current - timedelta(minutes=1)).isoformat(timespec="seconds"),
        "expires_at": (current + timedelta(minutes=179)).isoformat(timespec="seconds"),
        "runtime_script_sha256": "0" * 64,
        "implementation_review_sha256": "1" * 64,
        "design_record_sha256": "2" * 64,
        "v5_acceptance_sha256": "3" * 64,
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
    }
    return transport.canonical_json_bytes(payload)


def _governed_root(input_root: Path, suffix: str = "") -> Path:
    token = transport.CONTROL_NOTEBOOK_NAME + suffix
    return input_root / "notebooks" / "kabomolefe" / token / transport.CONTROL_OUTPUT_DIRECTORY_NAME


def test_materialized_control_package_validates(tmp_path: Path) -> None:
    authorization_bytes = _authorization_bytes()
    root = _governed_root(tmp_path)

    receipt = transport.materialize_control_package(
        root,
        authorization_bytes,
    )
    verification = transport.validate_control_package(
        tmp_path,
        require_live_authorization=True,
    )

    assert receipt.status == "MATERIALIZED"
    assert verification.authorization_sha256 == transport.sha256_bytes(authorization_bytes)
    assert verification.exact_flat_file_count == 3
    assert verification.producer_notebook_name == transport.CONTROL_NOTEBOOK_NAME


def test_observed_direct_dataset_topology_is_not_a_governed_root(
    tmp_path: Path,
) -> None:
    authorization_bytes = _authorization_bytes()
    historical = tmp_path / "datasets" / "kabomolefe" / "ag-p5-p6-execution-authorization-v1"
    historical.mkdir(parents=True)
    (historical / transport.AUTHORIZATION_FILENAME).write_bytes(authorization_bytes)

    old_candidates = tuple(tmp_path.glob(f"*/{transport.AUTHORIZATION_FILENAME}"))
    assert old_candidates == ()

    with pytest.raises(transport.AuthorizationTransportError) as captured:
        transport.resolve_governed_control_root(tmp_path)

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_TRANSPORT_ROOT_CARDINALITY_INVALID"


def test_unrelated_authorization_filename_collision_is_ignored(
    tmp_path: Path,
) -> None:
    authorization_bytes = _authorization_bytes()
    root = _governed_root(tmp_path)
    transport.materialize_control_package(root, authorization_bytes)

    unrelated = tmp_path / "datasets" / "kabomolefe" / "unrelated-expanded-input" / "nested"
    unrelated.mkdir(parents=True)
    (unrelated / transport.AUTHORIZATION_FILENAME).write_bytes(authorization_bytes)

    verification = transport.validate_control_package(
        tmp_path,
        require_live_authorization=True,
    )

    assert verification.root == root.resolve().as_posix()


def test_multiple_governed_roots_fail_closed(tmp_path: Path) -> None:
    authorization_bytes = _authorization_bytes()
    transport.materialize_control_package(
        _governed_root(tmp_path),
        authorization_bytes,
    )
    second = (
        tmp_path
        / "notebooks"
        / "other-owner"
        / transport.CONTROL_NOTEBOOK_NAME
        / transport.CONTROL_OUTPUT_DIRECTORY_NAME
    )
    transport.materialize_control_package(second, authorization_bytes)

    with pytest.raises(transport.AuthorizationTransportError) as captured:
        transport.validate_control_package(
            tmp_path,
            require_live_authorization=True,
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_TRANSPORT_ROOT_CARDINALITY_INVALID"


def test_extra_control_member_fails_closed(tmp_path: Path) -> None:
    root = _governed_root(tmp_path)
    transport.materialize_control_package(root, _authorization_bytes())
    (root / "unexpected.json").write_text("{}", encoding="utf-8")

    with pytest.raises(transport.AuthorizationTransportError) as captured:
        transport.validate_control_package(
            tmp_path,
            require_live_authorization=True,
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_TRANSPORT_FILE_SET_DRIFT"


def test_receipt_binding_drift_fails_closed(tmp_path: Path) -> None:
    root = _governed_root(tmp_path)
    transport.materialize_control_package(root, _authorization_bytes())
    receipt_path = root / transport.MATERIALIZATION_RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert isinstance(receipt, dict)
    receipt["authorization_sha256"] = "f" * 64
    receipt_path.write_bytes(transport.canonical_json_bytes(receipt))

    with pytest.raises(transport.AuthorizationTransportError) as captured:
        transport.validate_control_package(
            tmp_path,
            require_live_authorization=True,
        )

    assert captured.value.error_code == "P5_P6_AUTHORIZATION_TRANSPORT_RECEIPT_BINDING_DRIFT"


def test_control_materializer_notebook_is_cpu_only_and_unexecuted() -> None:
    notebook = transport.build_control_materializer_notebook(_authorization_bytes())

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
