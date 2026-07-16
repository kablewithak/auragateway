from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.contracts import ConditionId
from auragateway.local_abc.measured_authorization import (
    AuthorizationDecision,
    AuthorizationGateStatus,
    ConditionOrderPlan,
    DecodingPolicy,
    MeasuredAuthorizationPackage,
    MeasuredCaseManifest,
    MeasuredExecutionAuthorization,
    load_measured_authorization_package,
)

ROOT = Path(__file__).resolve().parents[3]
CASE_MANIFEST_PATH = ROOT / "benchmarks/local_abc/measured_case_manifest_v1.json"
AUTHORIZATION_PATH = ROOT / "benchmarks/local_abc/measured_execution_authorization_v1.json"
EXPECTED_CASE_MANIFEST_SHA256 = "8ca19d6bd48a50abc4bf5a0b932705be37f362e2be3f320d8f22a10090567ade"
EXPECTED_AUTHORIZATION_FINGERPRINT = (
    "64565dd6d34d7d9f9e55a4522b594ef95c458b0ff1af7994dfe81b39a8ba4e74"
)


def load_package() -> MeasuredAuthorizationPackage:
    return load_measured_authorization_package(
        case_manifest_path=CASE_MANIFEST_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )


def test_frozen_package_loads_and_authorizes_execution() -> None:
    package = load_package()

    assert package.authorization.decision is AuthorizationDecision.AUTHORIZED
    assert package.authorization.measured_execution_authorized is True


def test_case_manifest_fingerprint_is_frozen() -> None:
    package = load_package()

    assert package.case_manifest.fingerprint() == EXPECTED_CASE_MANIFEST_SHA256
    assert package.authorization.case_manifest_sha256 == EXPECTED_CASE_MANIFEST_SHA256


def test_authorization_fingerprint_is_frozen() -> None:
    package = load_package()

    assert package.authorization.fingerprint() == EXPECTED_AUTHORIZATION_FINGERPRINT


def test_frozen_design_has_eight_cases_and_three_conditions() -> None:
    package = load_package()

    assert len(package.case_manifest.cases) == 8
    assert package.authorization.case_count == 8
    assert package.authorization.condition_count == 3
    assert package.authorization.replication_count == 3


def test_frozen_design_has_seventy_two_trajectories_and_144_requests() -> None:
    authorization = load_package().authorization

    assert authorization.planned_trajectory_count == 72
    assert authorization.planned_request_count == 144


def test_condition_order_is_the_frozen_latin_square() -> None:
    order = load_package().authorization.condition_order.replications

    assert order == (
        (ConditionId.A, ConditionId.B, ConditionId.C),
        (ConditionId.B, ConditionId.C, ConditionId.A),
        (ConditionId.C, ConditionId.A, ConditionId.B),
    )


def test_every_case_has_two_ordered_turns_and_expectations() -> None:
    manifest = load_package().case_manifest

    for measured_case in manifest.cases:
        assert tuple(turn.turn_index for turn in measured_case.turns) == (1, 2)
        assert tuple(item.turn_index for item in measured_case.expected_outputs) == (1, 2)


def test_every_expected_payload_has_the_exact_quality_key_set() -> None:
    manifest = load_package().case_manifest
    expected_keys = {"answer", "case_id", "confidence", "turn_index"}

    for measured_case in manifest.cases:
        for expectation in measured_case.expected_outputs:
            payload = expectation.expected_payload(case_id=measured_case.case_id)
            assert set(payload) == expected_keys


def test_case_set_is_synthetic_and_disallows_raw_prompt_logging() -> None:
    manifest = load_package().case_manifest
    authorization = load_package().authorization

    assert manifest.customer_data_used is False
    assert manifest.private_client_artifacts_used is False
    assert manifest.raw_prompt_logging_permitted is False
    assert authorization.customer_data_used is False
    assert authorization.raw_prompt_logging_permitted is False


def test_all_four_predecessor_evidence_gates_are_passed() -> None:
    evidence = load_package().authorization.evidence

    assert len(evidence) == 4
    assert all(item.gate_status is AuthorizationGateStatus.PASSED for item in evidence)
    assert len({item.lifecycle_state for item in evidence}) == 4


def test_runtime_binding_is_exact_and_zero_spend() -> None:
    authorization = load_package().authorization

    assert authorization.runtime.kaggle_username == "kabomolefe"
    assert authorization.runtime.gpu_type == "Tesla T4"
    assert authorization.runtime.gpu_count == 2
    assert authorization.runtime.vllm_version == "0.25.1"
    assert authorization.runtime.cuda_version == "12.9"
    assert authorization.external_spend == Decimal("0")


def test_decoding_policy_is_deterministic() -> None:
    decoding = load_package().authorization.decoding

    assert decoding.temperature == Decimal("0")
    assert decoding.top_p == Decimal("1")
    assert decoding.seed == 7
    assert decoding.max_output_tokens == 64
    assert decoding.stream is False


def test_nonzero_temperature_is_rejected() -> None:
    with pytest.raises(ValidationError, match="temperature=0"):
        DecodingPolicy(temperature=Decimal("0.1"))


def test_wrong_condition_order_is_rejected() -> None:
    with pytest.raises(ValidationError, match="frozen Latin square"):
        ConditionOrderPlan(
            replications=(
                (ConditionId.A, ConditionId.B, ConditionId.C),
                (ConditionId.A, ConditionId.C, ConditionId.B),
                (ConditionId.C, ConditionId.B, ConditionId.A),
            )
        )


def test_failed_evidence_gate_cannot_authorize_execution() -> None:
    authorization = load_package().authorization
    payload = authorization.model_dump(mode="json")
    payload["evidence"][0]["gate_status"] = AuthorizationGateStatus.FAILED.value

    with pytest.raises(ValidationError, match="failed gate"):
        MeasuredExecutionAuthorization.model_validate(payload)


def test_authorization_boolean_must_match_decision() -> None:
    authorization = load_package().authorization
    payload = authorization.model_dump(mode="json")
    payload["measured_execution_authorized"] = False

    with pytest.raises(ValidationError, match="must match"):
        MeasuredExecutionAuthorization.model_validate(payload)


def test_planned_trajectory_count_is_derived_from_design() -> None:
    authorization = load_package().authorization
    payload = authorization.model_dump(mode="json")
    payload["planned_trajectory_count"] = 71

    with pytest.raises(ValidationError, match="trajectory count"):
        MeasuredExecutionAuthorization.model_validate(payload)


def test_planned_request_count_requires_two_turns_per_trajectory() -> None:
    authorization = load_package().authorization
    payload = authorization.model_dump(mode="json")
    payload["planned_request_count"] = 143

    with pytest.raises(ValidationError, match="two turns"):
        MeasuredExecutionAuthorization.model_validate(payload)


def test_tampered_case_manifest_is_rejected_by_cross_file_binding() -> None:
    package = load_package()
    payload = package.case_manifest.model_dump(mode="json")
    payload["cases"][0]["turns"][0]["user_message"] += " tampered"
    tampered_manifest = MeasuredCaseManifest.model_validate(payload)

    with pytest.raises(ValidationError, match="digest does not match"):
        MeasuredAuthorizationPackage(
            case_manifest=tampered_manifest,
            authorization=package.authorization,
        )


def test_duplicate_case_id_is_rejected() -> None:
    manifest = load_package().case_manifest
    payload = manifest.model_dump(mode="json")
    payload["cases"][1]["case_id"] = payload["cases"][0]["case_id"]

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        MeasuredCaseManifest.model_validate(payload)


def test_affinity_route_case_freezes_expected_worker_transition() -> None:
    manifest = load_package().case_manifest
    measured_case = next(item for item in manifest.cases if item.case_id == "affinity-route")

    assert measured_case.expected_outputs[0].answer == "worker_1"
    assert measured_case.expected_outputs[1].answer == "worker_2"


def test_json_artifacts_are_canonical_single_line_payloads() -> None:
    for path in (CASE_MANIFEST_PATH, AUTHORIZATION_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")
