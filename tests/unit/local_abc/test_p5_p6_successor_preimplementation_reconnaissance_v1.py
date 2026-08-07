from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    p5_p6_successor_preimplementation_reconnaissance_v1 as subject,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _rows_by_seam() -> dict[str, subject.CompatibilityRow]:
    return {row.seam: row for row in subject.EXPECTED_REVIEW_MODEL.compatibility_rows}


def test_review_is_fail_closed() -> None:
    review = subject.EXPECTED_REVIEW_MODEL
    assert review.runtime_execution_authorized is False
    assert review.measured_abc_execution_authorized is False
    assert review.benchmark_trajectory_requests_permitted == 0
    assert review.unresolved_compatibility_rows == ()


def test_matrix_has_no_unresolved_rows() -> None:
    rows = subject.EXPECTED_REVIEW_MODEL.compatibility_rows
    assert not [row for row in rows if row.classification in {"UNRESOLVED", "UNKNOWN"}]


def test_p4_environment_hardening_is_frozen() -> None:
    rows = _rows_by_seam()
    assert rows["ld_library_path_inheritance"].classification == "MUST_ADOPT_P4_V2"
    assert rows["ld_preload"].classification == "MUST_ADOPT_P4_V2"
    assert rows["linker_boundary"].classification == "MUST_ADOPT_P4_V2"


def test_v5_behavior_is_frozen() -> None:
    rows = _rows_by_seam()
    assert rows["worker_resource_envelope"].classification == "MUST_PRESERVE_V5"
    assert rows["p5_cache_evidence"].classification == "MUST_PRESERVE_V5"
    assert rows["p6_checkpointing"].classification == "MUST_PRESERVE_V5"


def test_case_a_is_frozen() -> None:
    row = _rows_by_seam()["output_contract"]
    assert row.classification == "MUST_ADOPT_P4_V2_CASE_A"
    assert "repetition_penalty=1.1" in row.resolution
    assert "no A-F reselection" in row.resolution


def test_p5_requires_full_process_restart() -> None:
    row = _rows_by_seam()["p5_reset"]
    assert row.classification == "FULL_PROCESS_RESTART_REQUIRED"


def test_metrics_guard_is_explicit() -> None:
    row = _rows_by_seam()["metrics_label_handling"]
    assert row.classification == "ACCEPT_WITH_GUARD"
    assert "both ports" in row.resolution


def test_external_vllm_authorities_are_pinned() -> None:
    external = subject.EXPECTED_POLICY_MODEL.external_authorities
    assert {item.ref for item in external} == {"v0.19.1"}
    assert all(len(item.git_blob_sha) == 40 for item in external)


def test_notebook_is_unexecuted() -> None:
    raw = json.loads(subject._notebook_bytes())
    assert isinstance(raw, dict)
    payload = cast(dict[str, object], raw)
    cells = payload["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 1
    cell = cells[0]
    assert isinstance(cell, dict)
    assert cell["execution_count"] is None
    assert cell["outputs"] == []


def test_review_rejects_unresolved_rows() -> None:
    payload = subject.EXPECTED_REVIEW_MODEL.model_dump(mode="json")
    payload["unresolved_compatibility_rows"] = [{"seam": "unknown"}]
    with pytest.raises(ValidationError):
        subject.ReviewModel.model_validate(payload)


def test_real_repository_authorities() -> None:
    subject.validate_authorities(REPO_ROOT)
