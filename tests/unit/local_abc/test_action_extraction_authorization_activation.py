"""Regression tests for the fresh action-extraction v2 authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_authorization_activation import (
    ActionExtractionAuthorizationActivationManifestV2,
    ActionExtractionAuthorizationActivationPackageV2,
    ActionExtractionAuthorizationActivationV2,
    canonical_json_file_sha256,
    load_action_extraction_authorization_activation_package_v2,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BENCHMARK_ROOT = _REPO_ROOT / "benchmarks" / "local_abc"
_PARENT_MANIFEST = _BENCHMARK_ROOT / "reconcile_balance_extraction_eval_cases_v1.json"
_PARENT_PLAN = _BENCHMARK_ROOT / "reconcile_balance_extraction_eval_plan_v1.json"
_REMEDIATION_MANIFEST = _BENCHMARK_ROOT / "reconcile_balance_extraction_remediation_cases_v2.json"
_REMEDIATION_PLAN = _BENCHMARK_ROOT / "reconcile_balance_extraction_remediation_plan_v2.json"
_REVIEW = _BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_review_v2.json"
_DRY_RUN = _BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_dry_run_v2.json"
_REVIEW_MANIFEST = (
    _BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_review_manifest_v2.json"
)
_AUTHORIZATION = (
    _BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_authorization_v2.json"
)
_ACTIVATION_MANIFEST = (
    _BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_activation_manifest_v2.json"
)
_EXPECTED_CASE_IDS = (
    "historical-turn-one",
    "turn-two-history-distractors",
    "reordered-narrative",
    "zero-boundary",
    "repeated-operands",
    "metadata-number-distractors",
    "formatted-currency-values",
    "key-value-layout",
    "same-answer-different-operands",
    "maximum-opening-boundary",
    "credits-first-description",
    "turn-two-feedback-separation",
    "formatted-currency-multi-group",
    "formatted-currency-spaced-symbol",
    "key-value-credits-first-layout",
    "key-value-mixed-delimiters",
)


def _load_package() -> ActionExtractionAuthorizationActivationPackageV2:
    return load_action_extraction_authorization_activation_package_v2(
        parent_manifest_path=_PARENT_MANIFEST,
        parent_plan_path=_PARENT_PLAN,
        remediation_manifest_path=_REMEDIATION_MANIFEST,
        remediation_plan_path=_REMEDIATION_PLAN,
        review_path=_REVIEW,
        dry_run_path=_DRY_RUN,
        review_manifest_path=_REVIEW_MANIFEST,
        authorization_path=_AUTHORIZATION,
        activation_manifest_path=_ACTIVATION_MANIFEST,
    )


def _authorization_payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_AUTHORIZATION.read_text(encoding="utf-8")))


def test_activation_package_loads_and_binds_all_parent_assets() -> None:
    package = _load_package()

    assert package.authorization.source_merge_commit == ("6038f7055e34c6c559b3c41cb919d0cb421b3e55")
    assert package.manifest.authorization_sha256 == package.authorization.fingerprint()


def test_activation_creates_one_unused_authorization() -> None:
    authorization = _load_package().authorization

    assert authorization.active_authorization_created is True
    assert authorization.execution_authorized is True
    assert authorization.authorization_consumed is False
    assert authorization.authorization_reuse_after_execution_permitted is False


def test_activation_does_not_perform_execution() -> None:
    authorization = _load_package().authorization

    assert authorization.execution_command_available is False
    assert authorization.provider_call_performed is False
    assert authorization.model_request_performed is False
    assert authorization.gpu_execution_performed is False
    assert authorization.credential_accessed is False


def test_notebook_binding_is_required_before_gpu_enablement() -> None:
    authorization = _load_package().authorization

    assert authorization.notebook_generation_permitted_after_merge is True
    assert authorization.notebook_sha256_binding_required is True
    assert authorization.notebook_execution_permitted_before_binding is False
    assert authorization.gpu_enablement_permitted_before_qualified_notebook is False
    assert authorization.bounded_gpu_execution_permitted_after_qualified_notebook is True


def test_activation_freezes_complete_sixteen_case_order() -> None:
    authorization = _load_package().authorization

    assert authorization.case_count == 16
    assert authorization.selected_case_ids == _EXPECTED_CASE_IDS
    assert authorization.complete_suite_required is True
    assert authorization.failed_case_only_execution_permitted is False


def test_activation_requires_exact_success_for_every_case() -> None:
    authorization = _load_package().authorization

    assert authorization.required_exact_operand_matches == 16
    assert authorization.required_exact_final_answer_matches == 16


def test_activation_preserves_one_attempt_stop_policy() -> None:
    policy = _load_package().authorization.stop_policy

    assert policy.required_request_count == 16
    assert policy.request_attempts_per_case == 1
    assert policy.hidden_retry_count == 0
    assert policy.repair_attempt_count == 0
    assert policy.replacement_request_count == 0
    assert policy.require_complete_sixteen_record_ledger is True


def test_activation_preserves_privacy_and_zero_spend() -> None:
    authorization = _load_package().authorization
    evidence = authorization.evidence

    assert evidence.raw_prompt_retention_permitted is False
    assert evidence.raw_output_retention_permitted is False
    assert evidence.raw_action_retention_permitted is False
    assert evidence.token_id_retention_permitted is False
    assert authorization.customer_data_used is False
    assert authorization.synthetic_data_only is True
    assert authorization.external_spend == 0


def test_activation_blocks_cache_and_full_benchmark_claims() -> None:
    authorization = _load_package().authorization

    assert authorization.cache_measurement_in_scope is False
    assert authorization.cache_claims_permitted is False
    assert authorization.full_measured_rerun_authorized is False


def test_activation_binds_exact_pr87_sources() -> None:
    bindings = _load_package().authorization.source_bindings

    assert tuple(binding.git_blob_sha for binding in bindings) == (
        "08a6dcd74ef6b569dc8e7de23cb1f7806e5350bc",
        "2982e1962825bf774cd092a3760d761d699b1ccf",
        "333ad82078a128eebf3b570636c08f7eaa45d6ef",
        "afd97a0d1acad659db8dacfce42f8a5eb16b8890",
    )


def test_activation_json_is_canonical_and_fingerprint_matches() -> None:
    authorization = _load_package().authorization

    assert canonical_json_file_sha256(_AUTHORIZATION) == authorization.fingerprint()


def test_activation_manifest_is_canonical() -> None:
    text = _ACTIVATION_MANIFEST.read_text(encoding="utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    assert text == f"{canonical}\n"


def test_case_order_mutation_fails_closed() -> None:
    payload = _authorization_payload()
    case_ids = list(cast(list[str], payload["selected_case_ids"]))
    case_ids[0], case_ids[1] = case_ids[1], case_ids[0]
    payload["selected_case_ids"] = case_ids

    authorization = ActionExtractionAuthorizationActivationV2.model_validate(payload)
    review_package = _load_package().review_package
    manifest = _load_package().manifest

    with pytest.raises(ValidationError, match="case order drifted"):
        ActionExtractionAuthorizationActivationPackageV2(
            review_package=review_package,
            authorization=authorization,
            manifest=manifest,
        )


def test_failed_case_only_enablement_is_rejected() -> None:
    payload = _authorization_payload()
    payload["failed_case_only_execution_permitted"] = True

    with pytest.raises(ValidationError):
        ActionExtractionAuthorizationActivationV2.model_validate(payload)


def test_premature_gpu_enablement_is_rejected() -> None:
    payload = _authorization_payload()
    payload["gpu_enablement_permitted_before_qualified_notebook"] = True

    with pytest.raises(ValidationError):
        ActionExtractionAuthorizationActivationV2.model_validate(payload)


def test_authorization_cannot_start_consumed() -> None:
    payload = _authorization_payload()
    payload["authorization_consumed"] = True

    with pytest.raises(ValidationError):
        ActionExtractionAuthorizationActivationV2.model_validate(payload)


def test_activation_manifest_rejects_wrong_authorization_hash() -> None:
    payload = json.loads(_ACTIVATION_MANIFEST.read_text(encoding="utf-8"))
    payload["authorization_sha256"] = "0" * 64

    manifest = ActionExtractionAuthorizationActivationManifestV2.model_validate(payload)
    package = _load_package()

    with pytest.raises(ValidationError, match="manifest must bind"):
        ActionExtractionAuthorizationActivationPackageV2(
            review_package=package.review_package,
            authorization=package.authorization,
            manifest=manifest,
        )


def test_activation_advances_only_to_notebook_generation() -> None:
    authorization = _load_package().authorization
    manifest = _load_package().manifest

    assert authorization.next_gate == "qualified_action_extraction_v2_notebook_generation"
    assert manifest.next_gate == "qualified_action_extraction_v2_notebook_generation"
