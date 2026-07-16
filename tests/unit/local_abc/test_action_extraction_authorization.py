from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_authorization import (
    ActionExtractionAuthorizationPackage,
    ActionExtractionCanaryAuthorization,
    ActionExtractionModelBinding,
    ActionExtractionRuntimeBinding,
    build_action_extraction_notebook_binding,
    fixed_action_extraction_case_ids,
    load_action_extraction_authorization_package,
)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_cases_v1.json"
PLAN_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_plan_v1.json"
AUTHORIZATION_PATH = (
    ROOT / "benchmarks/local_abc/" / "reconcile_balance_extraction_canary_authorization_v1.json"
)
EXPECTED_AUTHORIZATION_FINGERPRINT = (
    "9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9"
)
AUTHORIZATION_MERGE_COMMIT = "a" * 40
NOTEBOOK_SHA256 = "b" * 64


def load_package() -> ActionExtractionAuthorizationPackage:
    return load_action_extraction_authorization_package(
        manifest_path=MANIFEST_PATH,
        plan_path=PLAN_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )


def test_authorization_package_loads_and_cross_binds() -> None:
    package = load_package()

    assert package.authorization.fingerprint() == EXPECTED_AUTHORIZATION_FINGERPRINT
    assert package.authorization.case_manifest_sha256 == package.evaluation.manifest.fingerprint()
    assert package.authorization.evaluation_plan_sha256 == package.evaluation.plan.fingerprint()


def test_authorization_preserves_exact_twelve_case_order() -> None:
    package = load_package()
    case_ids = fixed_action_extraction_case_ids(package.evaluation.manifest)

    assert len(case_ids) == 12
    assert case_ids == package.authorization.selected_case_ids
    assert case_ids[0] == "historical-turn-one"
    assert case_ids[-1] == "turn-two-feedback-separation"


def test_model_and_runtime_bindings_are_exact() -> None:
    authorization = load_package().authorization

    assert authorization.model.repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert authorization.model.revision == ("7ae557604adf67be50417f59c2c2f167def9a775")
    assert authorization.runtime.gpu_count == 2
    assert authorization.runtime.gpu_name == "Tesla T4"
    assert authorization.runtime.torch_version == "2.11.0+cu129"
    assert authorization.runtime.vllm_distribution_version == "0.25.1+cu129"


def test_stop_policy_runs_semantic_failures_once_and_retains_them() -> None:
    policy = load_package().authorization.stop_policy

    assert policy.required_request_count == 12
    assert policy.request_attempts_per_case == 1
    assert policy.max_retained_semantic_failures == 12
    assert policy.max_infrastructure_failures == 0
    assert policy.hidden_retry_count == 0
    assert policy.repair_attempt_count == 0
    assert policy.replacement_request_count == 0
    assert policy.require_complete_twelve_record_ledger is True


def test_infrastructure_failures_abort_and_full_run_stays_blocked() -> None:
    authorization = load_package().authorization
    policy = authorization.stop_policy

    assert policy.abort_on_source_binding_failure is True
    assert policy.abort_on_model_identity_failure is True
    assert policy.abort_on_runtime_identity_failure is True
    assert policy.abort_on_worker_start_failure is True
    assert policy.abort_on_transport_failure is True
    assert policy.abort_on_cleanup_failure is True
    assert authorization.full_measured_rerun_authorized is False
    assert authorization.cache_measurement_in_scope is False
    assert authorization.cache_claims_permitted is False


def test_evidence_contract_prohibits_raw_retention() -> None:
    evidence = load_package().authorization.evidence

    assert evidence.raw_prompt_retention_permitted is False
    assert evidence.raw_output_retention_permitted is False
    assert evidence.raw_action_retention_permitted is False
    assert evidence.token_id_retention_permitted is False
    assert evidence.retain_prompt_hashes is True
    assert evidence.retain_output_hashes is True
    assert evidence.retain_failure_codes is True


def test_notebook_binding_qualifies_exact_authorized_identity() -> None:
    package = load_package()

    binding = build_action_extraction_notebook_binding(
        package=package,
        authorization_merge_commit=AUTHORIZATION_MERGE_COMMIT,
        notebook_sha256=NOTEBOOK_SHA256,
        observed_model=package.authorization.model,
        observed_runtime=package.authorization.runtime,
    )

    assert binding.authorization_sha256 == EXPECTED_AUTHORIZATION_FINGERPRINT
    assert binding.authorization_merge_commit == AUTHORIZATION_MERGE_COMMIT
    assert binding.notebook_sha256 == NOTEBOOK_SHA256
    assert binding.bounded_gpu_execution_authorized is True
    assert binding.full_measured_rerun_authorized is False


def test_notebook_binding_rejects_model_drift() -> None:
    package = load_package()
    model_payload = package.authorization.model.model_dump(mode="json")
    model_payload["revision"] = "0" * 40

    with pytest.raises(ValidationError):
        drifted_model = ActionExtractionModelBinding.model_validate(model_payload)
        build_action_extraction_notebook_binding(
            package=package,
            authorization_merge_commit=AUTHORIZATION_MERGE_COMMIT,
            notebook_sha256=NOTEBOOK_SHA256,
            observed_model=drifted_model,
            observed_runtime=package.authorization.runtime,
        )


def test_notebook_binding_rejects_runtime_drift() -> None:
    package = load_package()
    runtime_payload = package.authorization.runtime.model_dump(mode="json")
    runtime_payload["gpu_count"] = 1

    with pytest.raises(ValidationError):
        drifted_runtime = ActionExtractionRuntimeBinding.model_validate(runtime_payload)
        build_action_extraction_notebook_binding(
            package=package,
            authorization_merge_commit=AUTHORIZATION_MERGE_COMMIT,
            notebook_sha256=NOTEBOOK_SHA256,
            observed_model=package.authorization.model,
            observed_runtime=drifted_runtime,
        )


def test_notebook_binding_rejects_harness_commit_as_authorization_merge() -> None:
    package = load_package()

    with pytest.raises(
        ValidationError,
        match="later authorization merge commit",
    ):
        build_action_extraction_notebook_binding(
            package=package,
            authorization_merge_commit=package.authorization.harness_merge_commit,
            notebook_sha256=NOTEBOOK_SHA256,
            observed_model=package.authorization.model,
            observed_runtime=package.authorization.runtime,
        )


def test_authorization_rejects_case_order_drift() -> None:
    payload = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    payload["selected_case_ids"] = list(reversed(payload["selected_case_ids"]))

    with pytest.raises(
        ValidationError,
        match="fixed case order",
    ):
        ActionExtractionCanaryAuthorization.model_validate(payload)


def test_authorization_rejects_retry_enablement() -> None:
    payload = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    payload["stop_policy"]["hidden_retry_count"] = 1

    with pytest.raises(ValidationError):
        ActionExtractionCanaryAuthorization.model_validate(payload)


def test_authorization_rejects_full_measured_execution() -> None:
    payload = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    payload["full_measured_rerun_authorized"] = True

    with pytest.raises(ValidationError):
        ActionExtractionCanaryAuthorization.model_validate(payload)


def test_authorization_json_is_canonical() -> None:
    text = AUTHORIZATION_PATH.read_text(encoding="utf-8")

    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert json.dumps(
        json.loads(text),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ) == text.rstrip("\n")
