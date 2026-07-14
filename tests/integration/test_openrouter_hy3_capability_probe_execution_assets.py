from __future__ import annotations

from pathlib import Path

from auragateway.benchmark.openrouter_hy3_capability_probe_execution_runner import (
    _validate_execution_manifest,
)


def test_execution_design_manifest_matches_all_public_implementation_assets() -> None:
    policy = _validate_execution_manifest(Path("."))

    assert policy.policy_id == "openrouter-hy3-capability-probe-execution-policy-v1"
    assert policy.public_raw_payload_permitted is False
    assert policy.committed_authorization_mutation_permitted is False
