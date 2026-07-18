from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_runtime_lineage_correction import (
    CORRECTION_PATH,
    NEXT_GATE,
    SOURCE_MERGE_COMMIT,
    SUPERSESSION_PATH,
    FullABCLocalRuntimeCorrectionPackage,
    FullABCLocalRuntimeDirectionCorrection,
    FullABCLocalRuntimeIdentity,
    FullABCLocalRuntimeLineageCorrectionError,
    FullABCPreflightV2SupersessionRecord,
    FullABCWorkerBinding,
    assert_preflight_v2_not_execution_eligible,
    build_default_correction,
    build_default_supersession,
    load_full_abc_local_runtime_correction_package,
    load_full_abc_local_runtime_direction_correction,
    load_full_abc_preflight_v2_supersession,
    validate_repository_correction_package,
)

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_CORRECTION_SHA256 = "1927239e919741f96b6c8017b241413b42d9528de109db1cd7df7a0dfd9b0fe7"
EXPECTED_SUPERSESSION_SHA256 = "df39761f7f6c73787bffacb5e933b4ea4d35f4079e86ff94ec846f63e2ae1cd6"


def load_correction() -> FullABCLocalRuntimeDirectionCorrection:
    return load_full_abc_local_runtime_direction_correction(ROOT / CORRECTION_PATH)


def load_supersession() -> FullABCPreflightV2SupersessionRecord:
    return load_full_abc_preflight_v2_supersession(ROOT / SUPERSESSION_PATH)


def test_correction_has_expected_identity() -> None:
    correction = load_correction()

    assert correction.fingerprint() == EXPECTED_CORRECTION_SHA256
    assert correction.source_merge_commit == SOURCE_MERGE_COMMIT
    assert correction.next_gate == NEXT_GATE


def test_supersession_has_expected_identity() -> None:
    supersession = load_supersession()

    assert supersession.fingerprint() == EXPECTED_SUPERSESSION_SHA256
    assert supersession.correction_sha256 == EXPECTED_CORRECTION_SHA256
    assert supersession.next_gate == NEXT_GATE


def test_default_builders_reproduce_repository_artifacts() -> None:
    correction = build_default_correction()
    supersession = build_default_supersession(correction)

    assert correction == load_correction()
    assert supersession == load_supersession()


def test_package_cross_binding_passes() -> None:
    package = load_full_abc_local_runtime_correction_package(ROOT)

    assert package.correction.fingerprint() == package.supersession.correction_sha256


def test_preflight_v2_is_invalidated_for_every_downstream_use() -> None:
    correction = load_correction()

    assert correction.preflight_v2_planning_authoritative is False
    assert correction.preflight_v2_execution_eligible is False
    assert correction.preflight_v2_comparison_eligible is False
    assert correction.disposition == "PREFLIGHT_V2_INVALIDATED_NON_EXECUTABLE"


def test_hosted_provider_and_budget_paths_are_out_of_scope() -> None:
    correction = load_correction()

    assert correction.groq_in_full_abc_scope is False
    assert correction.openrouter_in_full_abc_scope is False
    assert correction.hosted_provider_probe_required is False
    assert correction.cost_budget_required is False
    assert correction.pricing_schedule_required is False


def test_local_runtime_identity_is_exact() -> None:
    runtime = load_correction().local_runtime

    assert runtime.execution_backend == "local_vllm"
    assert runtime.environment == "kaggle_t4_x2"
    assert runtime.transport_endpoint == "/v1/chat/completions"
    assert runtime.gpu_count == 2
    assert runtime.gpu_model == "Tesla T4"
    assert runtime.vllm_distribution_version == "0.25.1+cu129"


def test_local_model_identity_is_exact() -> None:
    model = load_correction().local_runtime.model

    assert model.model_alias == "local-qwen2.5-0.5b-instruct"
    assert model.repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert model.revision == "7ae557604adf67be50417f59c2c2f167def9a775"
    assert (
        model.model_manifest_sha256
        == "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
    )


def test_two_worker_topology_is_exact() -> None:
    workers = load_correction().local_runtime.workers

    assert tuple((item.worker_id, item.gpu_index, item.port) for item in workers) == (
        ("worker_1", 0, 8001),
        ("worker_2", 1, 8002),
    )


def test_runtime_preserves_zero_spend_and_no_credentials() -> None:
    runtime = load_correction().local_runtime

    assert runtime.hosted_provider_required is False
    assert runtime.provider_credentials_required is False
    assert runtime.pricing_in_scope is False
    assert runtime.paid_fallback_permitted is False
    assert runtime.external_spend == 0
    assert runtime.customer_data_used is False


def test_full_run_environment_requalification_remains_required() -> None:
    assert (
        load_correction().local_runtime.current_full_run_environment_requalification_required
        is True
    )


def test_evidence_bindings_cover_environment_model_execution_and_consumption() -> None:
    bindings = load_correction().evidence_bindings

    assert tuple(item.evidence_role for item in bindings) == (
        "two_worker_environment",
        "model_runtime_authorization",
        "successful_model_execution_audit",
        "authorization_consumption",
    )


def test_invalidated_field_set_includes_every_hosted_provider_contamination() -> None:
    invalidated = set(load_correction().invalidated_fields)

    assert "dependency_lock.packages.groq" in invalidated
    assert "condition_fingerprints.records[*].payload.provider_model_alias" in invalidated
    assert "execution_manifest_draft.assets.pricing_schedule_id" in invalidated
    assert "preflight_report.checks.provider_readiness_pending" in invalidated
    assert "preflight_report.checks.cost_approval_pending" in invalidated


def test_supersession_blocks_review_probe_reuse_and_execution() -> None:
    supersession = load_supersession()

    assert supersession.provider_budget_review_permitted is False
    assert supersession.provider_probe_permitted is False
    assert supersession.preflight_v2_reuse_permitted is False
    assert supersession.execution_authorized is False


def test_repository_assertion_passes() -> None:
    assert_preflight_v2_not_execution_eligible(ROOT)


def test_validation_summary_is_safe_and_directionally_correct() -> None:
    summary = validate_repository_correction_package(ROOT)

    assert summary == {
        "correction_sha256": EXPECTED_CORRECTION_SHA256,
        "supersession_sha256": EXPECTED_SUPERSESSION_SHA256,
        "preflight_v2_execution_eligible": False,
        "execution_backend": "local_vllm",
        "model_alias": "local-qwen2.5-0.5b-instruct",
        "hosted_provider_required": False,
        "pricing_in_scope": False,
        "external_spend": 0,
        "next_gate": NEXT_GATE,
    }


def test_wrong_worker_binding_fails_closed() -> None:
    with pytest.raises(ValidationError, match="fixed local A/B/C topology"):
        FullABCWorkerBinding(worker_id="worker_1", gpu_index=1, port=8001)


def test_hosted_provider_permission_cannot_be_enabled() -> None:
    payload = load_correction().model_dump(mode="json")
    payload["hosted_provider_probe_required"] = True

    with pytest.raises(ValidationError):
        FullABCLocalRuntimeDirectionCorrection.model_validate(payload)


def test_runtime_paid_fallback_cannot_be_enabled() -> None:
    payload = load_correction().local_runtime.model_dump(mode="json")
    payload["paid_fallback_permitted"] = True

    with pytest.raises(ValidationError):
        FullABCLocalRuntimeIdentity.model_validate(payload)


def test_modified_correction_breaks_package_binding() -> None:
    correction = load_correction()
    supersession = load_supersession().model_copy(update={"correction_sha256": "0" * 64})

    with pytest.raises(ValidationError, match="exact correction fingerprint"):
        FullABCLocalRuntimeCorrectionPackage(
            correction=correction,
            supersession=supersession,
        )


def test_missing_artifact_returns_metadata_safe_error(tmp_path: Path) -> None:
    with pytest.raises(
        FullABCLocalRuntimeLineageCorrectionError,
        match="required local-runtime correction artifact",
    ):
        load_full_abc_local_runtime_direction_correction(tmp_path / "missing.json")


def test_json_artifacts_are_canonical_single_line() -> None:
    for relative_path in (CORRECTION_PATH, SUPERSESSION_PATH):
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        expected = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        assert text == expected
