from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auragateway.local_abc import (
    p5_p6_successor_execution_acceptance_v1 as acceptance,
)

ROOT = Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_policy_is_hash_locked_and_valid() -> None:
    policy_path = ROOT / acceptance.POLICY_PATH
    assert sha256_file(policy_path) == acceptance.POLICY_SHA256
    policy = acceptance.AcceptancePolicy.model_validate_json(
        policy_path.read_text(encoding="utf-8")
    )
    assert policy.saved_version_id == 340976295
    assert policy.lifecycle_outcome == "PASSED"
    assert policy.current_line_p5_pass_accepted is True
    assert policy.current_line_p6_pass_accepted is True
    assert policy.measured_abc_eligible is True
    assert policy.measured_abc_execution_authorized is False


def test_preserved_authorization_is_exact() -> None:
    path = ROOT / acceptance.EVIDENCE_DIR / acceptance.AUTHORIZATION_NAME
    assert sha256_file(path) == "1567adabaf6ecd9a586c40c1f037914c54b24d1905a9553713e7c4ef1cab66ef"


def test_preserved_consumption_is_exact() -> None:
    path = ROOT / acceptance.EVIDENCE_DIR / acceptance.CONSUMPTION_NAME
    assert sha256_file(path) == "77c0d200010770fa4ff49b35d13678eccd07dea59ffc37b0f80567d5198026af"


def test_preserved_runtime_evidence_is_exact() -> None:
    zip_path = ROOT / acceptance.EVIDENCE_DIR / acceptance.EVIDENCE_ZIP_NAME
    log_path = ROOT / acceptance.EVIDENCE_DIR / acceptance.TERMINAL_LOG_NAME
    assert (
        sha256_file(zip_path) == "ed6a3c5b33b5a982a0793231db753a283c9d626f92d5eb8831a3fa1605ce88b6"
    )
    assert (
        sha256_file(log_path) == "223e4d2d17536a9d33d31b07ed11d374408d2c2d28456d430b9c835539b5c0e1"
    )


def test_lifecycle_is_consumed_pass() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._validate_lifecycle(ROOT, policy)


def test_runtime_evidence_semantics_pass() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._validate_runtime_evidence(ROOT, policy)


def test_intake_manifest_binds_preserved_evidence() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._validate_intake_manifest(ROOT, policy)


def test_operational_transients_are_retired() -> None:
    policy = acceptance._load_policy(ROOT)
    acceptance._require_transient_paths_retired(ROOT, policy)


def test_review_and_record_are_deterministic() -> None:
    review_a = acceptance.build_review(ROOT)
    review_b = acceptance.build_review(ROOT)
    assert review_a == review_b
    record_a = acceptance.build_record(ROOT, review_a)
    record_b = acceptance.build_record(ROOT, review_b)
    assert record_a == record_b


def test_validate_implementation_accepts_frozen_candidate() -> None:
    result = acceptance.validate_implementation(ROOT)
    assert result["status"] == "P5_P6_SUCCESSOR_EXECUTION_ACCEPTANCE_V1_VALID"
    assert result["current_line_p5_pass_accepted"] is True
    assert result["current_line_p6_pass_accepted"] is True
    assert result["measured_abc_eligible"] is True
    assert result["measured_abc_execution_authorized"] is False


def test_archive_normalizer_rejects_parent_escape() -> None:
    with pytest.raises(acceptance.AcceptanceError):
        acceptance._normalize_zip_name("../escape.json")


def test_record_does_not_authorize_measured_abc() -> None:
    payload = json.loads((ROOT / acceptance.RECORD_PATH).read_text(encoding="utf-8"))
    assert payload["measured_abc_eligible"] is True
    assert payload["measured_abc_execution_authorized"] is False
    assert payload["runtime_execution_authorized"] is False
