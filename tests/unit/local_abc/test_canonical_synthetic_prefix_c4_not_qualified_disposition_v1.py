from __future__ import annotations

import copy
import zipfile
from pathlib import Path

import pytest

from auragateway.local_abc import (
    canonical_synthetic_prefix_c4_not_qualified_disposition_v1 as disposition,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_build_all_accepts_governed_not_qualified_custody() -> None:
    custody, record, review = disposition.build_all(REPO_ROOT)

    assert custody
    assert record
    assert review

    record_payload = disposition.as_object(record, "record")
    assert record_payload["execution_valid"] is True
    assert record_payload["observed_c4_state"] == "NOT_QUALIFIED"
    assert record_payload["exact_object_count"] == 0
    assert record_payload["valid_json_count"] == 3
    assert record_payload["new_execution_authorized"] is False
    assert record_payload["next_gate"] == disposition.NEXT_GATE


def test_request_validator_rejects_false_qualification_projection() -> None:
    evidence_path = REPO_ROOT / disposition.CUSTODY[-1][1]
    with zipfile.ZipFile(evidence_path) as archive:
        payload = disposition.zip_object(archive, "c4_request_results_v1.json")

    mutated = copy.deepcopy(payload)
    results = mutated["results"]
    assert isinstance(results, list)
    first = results[0]
    assert isinstance(first, dict)
    first["exact_object"] = True

    with pytest.raises(
        disposition.DispositionError,
        match="request\\[1\\]\\.exact_object drifted",
    ):
        disposition.validate_requests(mutated)


def test_require_hash_rejects_byte_drift(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"drift")

    with pytest.raises(disposition.DispositionError):
        disposition.require(tmp_path, Path("artifact.bin"), "0" * 64)
