"""Regression tests for inactive action-extraction authorization review v2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_authorization_review import (
    ActionExtractionAuthorizationReviewDecision,
    ActionExtractionAuthorizationReviewPackageV2,
    ActionExtractionAuthorizationReviewStatus,
    ActionExtractionAuthorizationReviewV2,
    build_action_extraction_authorization_dry_run_v2,
    load_action_extraction_authorization_review_package_v2,
)
from auragateway.local_abc.action_extraction_remediation import (
    ActionExtractionRemediationControl,
    load_action_extraction_remediation_package,
)

ROOT = Path(__file__).resolve().parents[3]
PARENT_MANIFEST_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_cases_v1.json"
PARENT_PLAN_PATH = ROOT / "benchmarks/local_abc/reconcile_balance_extraction_eval_plan_v1.json"
REMEDIATION_MANIFEST_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_remediation_cases_v2.json"
)
REMEDIATION_PLAN_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_remediation_plan_v2.json"
)
REVIEW_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_authorization_review_v2.json"
)
DRY_RUN_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_authorization_dry_run_v2.json"
)
REVIEW_MANIFEST_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_authorization_review_manifest_v2.json"
)

EXPECTED_REVIEW_FINGERPRINT = "66539ccadbebee9ad6227b8d861da8bfa1f0e89fdd69883e91f49b15819c99a9"
EXPECTED_DRY_RUN_FINGERPRINT = "207abb6746277b1f6bc4ca79d537de3623f06d66ca5fa8600ee391af45acf508"
EXPECTED_MANIFEST_FINGERPRINT = "8299da7aaba1ed886d5bf85b9ee59c2471e79f735b1f37d66b9b8c3c806eee2d"
EXPECTED_SOURCE_COMMIT = "bb732bf88020cb031f534bb0b67d74b8f8f05483"


def load_package() -> ActionExtractionAuthorizationReviewPackageV2:
    return load_action_extraction_authorization_review_package_v2(
        parent_manifest_path=PARENT_MANIFEST_PATH,
        parent_plan_path=PARENT_PLAN_PATH,
        remediation_manifest_path=REMEDIATION_MANIFEST_PATH,
        remediation_plan_path=REMEDIATION_PLAN_PATH,
        review_path=REVIEW_PATH,
        dry_run_path=DRY_RUN_PATH,
        review_manifest_path=REVIEW_MANIFEST_PATH,
    )


def test_review_package_binds_all_inactive_assets() -> None:
    package = load_package()

    assert package.review.fingerprint() == EXPECTED_REVIEW_FINGERPRINT
    assert package.dry_run.fingerprint() == EXPECTED_DRY_RUN_FINGERPRINT
    assert package.manifest.fingerprint() == EXPECTED_MANIFEST_FINGERPRINT


def test_review_binds_pr86_merge_commit_and_three_sources() -> None:
    review = load_package().review

    assert review.source_merge_commit == EXPECTED_SOURCE_COMMIT
    assert len(review.source_bindings) == 3
    assert tuple(binding.path for binding in review.source_bindings) == (
        "src/auragateway/local_abc/action_extraction_remediation.py",
        "benchmarks/local_abc/reconcile_balance_extraction_remediation_cases_v2.json",
        "benchmarks/local_abc/reconcile_balance_extraction_remediation_plan_v2.json",
    )


def test_review_is_ready_but_inactive() -> None:
    review = load_package().review

    assert review.status is ActionExtractionAuthorizationReviewStatus.REVIEW_READY_INACTIVE
    assert review.decision is (
        ActionExtractionAuthorizationReviewDecision.APPROVED_FOR_SEPARATE_ACTIVATION
    )
    assert review.active_authorization_created is False
    assert review.execution_command_available is False
    assert review.notebook_generation_permitted is False
    assert review.execution_authorized is False
    assert review.gpu_execution_authorized is False


def test_material_difference_is_exactly_the_three_versioned_controls() -> None:
    review = load_package().review

    assert review.controls == (
        ActionExtractionRemediationControl.DETERMINISTIC_INTEGER_LEXICAL_NORMALIZATION,
        ActionExtractionRemediationControl.SEMANTIC_ROLE_BOUND_INSTRUCTION,
        ActionExtractionRemediationControl.ROLE_DESCRIBED_RESPONSE_SCHEMA,
    )


def test_review_preserves_failed_baseline_and_requires_sixteen_of_sixteen() -> None:
    review = load_package().review

    assert review.baseline_case_count == 12
    assert review.baseline_exact_operand_matches == 10
    assert review.baseline_exact_final_answer_matches == 10
    assert review.total_case_count == 16
    assert review.required_exact_operand_matches == 16
    assert review.required_exact_final_answer_matches == 16
    assert review.complete_suite_required is True


def test_review_preserves_model_runtime_and_deterministic_decoding() -> None:
    review = load_package().review

    assert review.model.repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert review.model.revision == "7ae557604adf67be50417f59c2c2f167def9a775"
    assert review.runtime.gpu_count == 2
    assert review.runtime.gpu_name == "Tesla T4"
    assert review.runtime.vllm_module_version == "0.25.1"
    assert str(review.decoding.temperature) == "0"
    assert str(review.decoding.top_p) == "1"
    assert review.decoding.seed == 7


def test_stop_policy_forbids_retry_repair_replacement_and_fallback() -> None:
    policy = load_package().review.stop_policy

    assert policy.required_request_count == 16
    assert policy.request_attempts_per_case == 1
    assert policy.hidden_retry_count == 0
    assert policy.repair_attempt_count == 0
    assert policy.replacement_request_count == 0
    assert policy.failed_case_only_execution_permitted is False
    assert policy.direct_model_arithmetic_fallback_permitted is False
    assert policy.deterministic_semantic_parser_fallback_permitted is False


def test_evidence_contract_is_privacy_safe_and_versioned() -> None:
    evidence = load_package().review.evidence

    assert evidence.schedule_filename.endswith("_v2.json")
    assert evidence.ledger_filename.endswith("_v2.jsonl")
    assert evidence.raw_prompt_retention_permitted is False
    assert evidence.raw_output_retention_permitted is False
    assert evidence.raw_action_retention_permitted is False
    assert evidence.token_id_retention_permitted is False
    assert evidence.retain_normalized_prompt_hashes is True
    assert evidence.retain_normalization_counts is True


def test_dry_run_contains_exact_complete_case_order() -> None:
    package = load_package()
    manifest = package.remediation.remediation_manifest
    expected_ids = tuple(
        case.eval_case_id for case in (*manifest.historical_cases, *manifest.added_diagnostic_cases)
    )

    assert tuple(attempt.eval_case_id for attempt in package.dry_run.attempts) == expected_ids
    assert tuple(attempt.sequence_index for attempt in package.dry_run.attempts) == tuple(range(16))


def test_dry_run_has_no_model_or_credential_path() -> None:
    dry_run = load_package().dry_run

    assert dry_run.planned_request_count == 16
    assert dry_run.model_request_performed is False
    assert dry_run.credential_accessed is False
    assert dry_run.execution_command_available is False
    assert dry_run.execution_authorized is False
    assert dry_run.gpu_execution_authorized is False
    assert all(attempt.model_request_permitted is False for attempt in dry_run.attempts)


def test_dry_run_retains_hashes_without_raw_prompts() -> None:
    dry_run = load_package().dry_run
    serialized = dry_run.canonical_json()

    assert all(attempt.raw_prompt_retained is False for attempt in dry_run.attempts)
    assert "SYNTHETIC CASE" not in serialized
    assert "opening balance R1,200" not in serialized


def test_formatted_cases_have_distinct_source_and_normalized_hashes() -> None:
    dry_run = load_package().dry_run
    formatted_ids = {
        "formatted-currency-values",
        "maximum-opening-boundary",
        "formatted-currency-multi-group",
        "formatted-currency-spaced-symbol",
    }
    attempts = tuple(item for item in dry_run.attempts if item.eval_case_id in formatted_ids)

    assert len(attempts) == 4
    assert all(item.source_prompt_sha256 != item.normalized_prompt_sha256 for item in attempts)


def test_key_value_cases_remain_distinct_prompt_identities() -> None:
    dry_run = load_package().dry_run
    ids = {
        "key-value-layout",
        "key-value-credits-first-layout",
        "key-value-mixed-delimiters",
    }
    attempts = tuple(item for item in dry_run.attempts if item.eval_case_id in ids)

    assert len(attempts) == 3
    assert len({item.rendered_prompt_sha256 for item in attempts}) == 3


def test_review_allows_only_separate_activation_as_next_gate() -> None:
    package = load_package()

    assert package.review.next_gate == "bounded_action_extraction_v2_authorization_activation"
    assert package.manifest.next_gate == "bounded_action_extraction_v2_authorization_activation"
    assert package.review.full_measured_rerun_authorized is False
    assert package.dry_run.full_measured_rerun_authorized is False


def test_dry_run_builder_reproduces_frozen_artifact() -> None:
    remediation = load_action_extraction_remediation_package(
        parent_manifest_path=PARENT_MANIFEST_PATH,
        parent_plan_path=PARENT_PLAN_PATH,
        remediation_manifest_path=REMEDIATION_MANIFEST_PATH,
        remediation_plan_path=REMEDIATION_PLAN_PATH,
    )

    assert build_action_extraction_authorization_dry_run_v2(remediation).canonical_json() == (
        load_package().dry_run.canonical_json()
    )


def test_review_rejects_source_binding_drift() -> None:
    payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    payload["source_bindings"][0]["git_blob_sha"] = "0" * 40

    with pytest.raises(ValidationError, match="source bindings drifted"):
        ActionExtractionAuthorizationReviewV2.model_validate(payload)


def test_review_rejects_case_order_drift() -> None:
    payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    payload["selected_case_ids"] = list(reversed(payload["selected_case_ids"]))
    drifted = ActionExtractionAuthorizationReviewV2.model_validate(payload)

    manifest_payload = json.loads(REVIEW_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_payload["review_sha256"] = drifted.fingerprint()
    drifted_review_path = REVIEW_PATH.parent / "temporary-drifted-review.json"
    drifted_manifest_path = REVIEW_PATH.parent / "temporary-drifted-manifest.json"
    try:
        drifted_review_path.write_text(drifted.canonical_json() + "\n", encoding="utf-8")
        drifted_manifest_path.write_text(
            json.dumps(
                manifest_payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValidationError, match="selected cases drifted"):
            load_action_extraction_authorization_review_package_v2(
                parent_manifest_path=PARENT_MANIFEST_PATH,
                parent_plan_path=PARENT_PLAN_PATH,
                remediation_manifest_path=REMEDIATION_MANIFEST_PATH,
                remediation_plan_path=REMEDIATION_PLAN_PATH,
                review_path=drifted_review_path,
                dry_run_path=DRY_RUN_PATH,
                review_manifest_path=drifted_manifest_path,
            )
    finally:
        drifted_review_path.unlink(missing_ok=True)
        drifted_manifest_path.unlink(missing_ok=True)


def test_review_rejects_execution_enablement() -> None:
    payload = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    payload["execution_authorized"] = True

    with pytest.raises(ValidationError):
        ActionExtractionAuthorizationReviewV2.model_validate(payload)


def test_review_artifacts_are_canonical_one_line_json() -> None:
    for path in (REVIEW_PATH, DRY_RUN_PATH, REVIEW_MANIFEST_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")
