from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.local_abc.p5_p6_exact_runtime_authority_failure_governance_v1 import (
    AUTHORIZATION_SHA256,
    GovernanceError,
    reject_authorization_reuse,
    validate_governance,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_failure_governance_package_validates() -> None:
    result = validate_governance(REPO_ROOT)

    assert result["status"] == "EXACT_RUNTIME_P5_P6_AUTHORITY_FAILURE_GOVERNANCE_V1_VALID"
    assert result["saved_version_id"] == 341454766
    assert result["inspection_saved_version_id"] == 341466979
    assert result["failure_class"] == "AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE"
    assert result["failure_depth"] == "EARLY_CONTROL_PLANE"
    assert result["runtime_incompatibility_established"] is False
    assert result["authorization_reusable"] is False
    assert result["runtime_execution_authorized"] is False
    assert result["p5_p6_exact_runtime_requalified"] is False


def test_consumed_authorization_reuse_fails_closed() -> None:
    with pytest.raises(GovernanceError) as captured:
        reject_authorization_reuse(AUTHORIZATION_SHA256)

    assert captured.value.code == "P5_P6_FAILURE_GOVERNANCE_AUTHORIZATION_CONSUMED"


def test_unknown_authorization_identity_is_not_rewritten_as_consumed() -> None:
    with pytest.raises(GovernanceError) as captured:
        reject_authorization_reuse("0" * 64)

    assert captured.value.code == "P5_P6_FAILURE_GOVERNANCE_AUTHORIZATION_IDENTITY_UNKNOWN"
