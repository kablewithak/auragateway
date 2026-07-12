from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.evidence_bundle import (
    ComparisonEligibilityContract,
    EvidenceBundleCandidate,
    EvidenceBundleFixtureSet,
    MetricComparisonRule,
    MetricFamily,
    RunEvidenceRecord,
)

_FIXTURE_PATH = Path("data/evals/evidence/gate8-v1/fixtures.json")


def _fixtures() -> EvidenceBundleFixtureSet:
    return EvidenceBundleFixtureSet.model_validate_json(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_set_is_typed_and_contains_negative_controls() -> None:
    fixtures = _fixtures()

    assert len(fixtures.cases) == 11
    assert sum(case.negative_control for case in fixtures.cases) == 8


def test_bundle_contract_forbids_unknown_fields() -> None:
    candidate = _fixtures().cases[0].candidate
    payload = candidate.model_dump(mode="json")
    payload["raw_prompt"] = "must-not-enter-contract"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EvidenceBundleCandidate.model_validate(payload)


def test_provider_error_requires_failure_code() -> None:
    record = _fixtures().cases[0].candidate.runs[0]
    payload = record.model_dump(mode="json")
    payload.update(
        {
            "terminal_status": "provider_error",
            "result_artifact_sha256": None,
            "failure_code": None,
        }
    )

    with pytest.raises(ValidationError, match="failed terminal statuses require failure_code"):
        RunEvidenceRecord.model_validate(payload)


def test_comparison_contract_rejects_unknown_configuration_field() -> None:
    contract = _fixtures().cases[0].candidate.comparison_contract
    payload = contract.model_dump(mode="json")
    payload["rules"][0]["allowed_mismatch_fields"].append("unknown_field")

    with pytest.raises(ValidationError, match="unknown configuration fields"):
        ComparisonEligibilityContract.model_validate(payload)


def test_comparison_contract_requires_all_metric_families() -> None:
    rules = tuple(
        MetricComparisonRule(metric_family=family)
        for family in (MetricFamily.COST, MetricFamily.LATENCY, MetricFamily.QUALITY)
    )

    with pytest.raises(ValidationError):
        ComparisonEligibilityContract(rules=rules)


def test_fixture_json_contains_no_raw_prompt_or_provider_payload_fields() -> None:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

    def collect_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            keys = {str(key).lower() for key in value}
            for item in value.values():
                keys.update(collect_keys(item))
            return keys
        if isinstance(value, list):
            list_keys: set[str] = set()
            for item in value:
                list_keys.update(collect_keys(item))
            return list_keys
        return set()

    keys = collect_keys(payload)
    assert "raw_prompt" not in keys
    assert "raw_prompts" not in keys
    assert "provider_payload" not in keys
