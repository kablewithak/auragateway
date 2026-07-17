from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from auragateway.local_abc.contracts import ConditionId
from auragateway.local_abc.full_abc_execution_manifest_draft_reconciliation import (
    build_condition_fingerprints,
    build_dependency_lock,
    build_reconciled_ledger,
    build_reconciliation_assets,
    load_full_abc_reconciliation_spec,
    verify_reconciliation_assets,
    write_reconciliation_assets,
)
from auragateway.local_abc.full_abc_execution_manifest_draft_reconciliation_contracts import (
    _CONDITION_FINGERPRINTS_PATH,
    _DEPENDENCY_LOCK_PATH,
    _DRAFT_PATH,
    _INPUT_PATH,
    _LEDGER_PATH,
    _MANIFEST_PATH,
    _REPORT_PATH,
    FullABCConditionFingerprintManifest,
    FullABCDependencyLock,
    FullABCReconciledExecutionManifestDraft,
    FullABCReconciledPlannedRunLedger,
    FullABCReconciliationCheckName,
    FullABCReconciliationCheckStatus,
    FullABCReconciliationError,
    FullABCReconciliationInput,
    FullABCReconciliationManifest,
    FullABCReconciliationReport,
    FullABCReconciliationSummary,
)

ROOT = Path(__file__).resolve().parents[3]
SPEC_RELATIVE = Path(
    "benchmarks/local_abc/auragateway_full_abc_execution_manifest_draft_reconciliation_v2.json"
)
SOURCE_COMMIT = "d6531fdc0b27892dcc299598f9f251fa157434dc"
VERSIONS = {
    "groq": "1.5.0",
    "pydantic": "2.12.5",
    "mypy": "1.19.1",
    "pytest": "9.0.2",
    "ruff": "0.15.21",
    "setuptools": "82.0.1",
}


def _version_resolver(name: str) -> str:
    return VERSIONS[name]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _legacy_input() -> dict[str, object]:
    functional = [f"ep-func-{index:03d}" for index in range(1, 19)]
    runtime = [
        "ep-func-001",
        "ep-func-002",
        "ep-func-005",
        "ep-func-006",
        "ep-func-010",
        "ep-func-012",
    ]
    return {
        "execution_manifest": {
            "assets": {
                "corpus_manifest_sha256": "a" * 64,
                "chunking_configuration_sha256": "b" * 64,
                "retrieval_configuration_sha256": "c" * 64,
                "development_retrieval_manifest_sha256": "d" * 64,
                "held_out_retrieval_manifest_sha256": "e" * 64,
                "retrieval_scorecard_sha256": "f" * 64,
                "diagnostic_episode_manifest_sha256": "1" * 64,
                "functional_benchmark_manifest_sha256": "2" * 64,
                "runtime_microbenchmark_manifest_sha256": "3" * 64,
                "quality_rubric_sha256": "4" * 64,
                "review_sample_schedule_sha256": "5" * 64,
                "telemetry_fixture_manifest_sha256": "6" * 64,
                "provider_model_alias": "groq-gpt-oss-20b",
                "provider_adapter_version": "groq-chat-completions-v1",
            },
            "controls": {
                "functional_run_order_schedule_id": "functional-counterbalance-v1",
                "runtime_run_order_schedule_id": "runtime-counterbalance-v1",
                "timeout_policy_id": "provider-request-policy-v1",
                "retry_policy_id": "provider-request-policy-v1",
                "exclusion_policy_id": "exclusion-policy-v1",
                "rerun_policy_id": "rerun-policy-v1",
                "denominator_policy_id": "denominator-policy-v1",
                "statistical_reporting_configuration_id": "paired-bootstrap-v1",
                "quality_non_inferiority_policy_id": "quality-non-inferiority-v1",
            },
        },
        "plan_request": {
            "plan_id": "benchmark-plan-auragateway-abc-v1",
            "functional_episode_ids": functional,
            "runtime_episode_ids": runtime,
            "turns_per_episode": 4,
            "maximum_retries_after_initial_attempt": 1,
        },
    }


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    copies = (
        "pyproject.toml",
        "docs/benchmark/AuraGateway_Benchmark_Constitution.md",
        "docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md",
        "benchmarks/local_abc/auragateway_full_abc_harness_integration_design_v1.json",
        "benchmarks/local_abc/auragateway_full_abc_harness_integration_implementation_v1.json",
        "benchmarks/local_abc/auragateway_full_abc_execution_manifest_asset_inventory_v1.json",
        SPEC_RELATIVE.as_posix(),
    )
    for relative in copies:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)

    _write_json(
        tmp_path / "data/evals/benchmark/preflight-v1/input.json",
        _legacy_input(),
    )
    _write_json(
        tmp_path / "data/evals/feedback/efc-v1/manifest.json",
        {"manifest_id": "gate7-fixture"},
    )
    _write_json(
        tmp_path / "data/evals/evidence/gate8-v1/manifest.json",
        {"manifest_id": "gate8-fixture"},
    )
    _write_json(
        tmp_path / "data/evals/benchmark/freeze-v1/pricing_schedule.json",
        {
            "pricing_schedule_id": "groq-openai-gpt-oss-20b-ondemand-2026-07-13",
            "source_date": "2026-07-13",
            "currency": "USD",
        },
    )
    _write_json(
        tmp_path / "data/evals/benchmark/freeze-v1/negative_control_manifest.json",
        {"manifest_id": "negative-controls-v1"},
    )
    _write_json(
        tmp_path / "data/evals/benchmark/freeze-v1/fault_injection_fixtures.json",
        {"fixture_set_id": "fault-fixtures-v1"},
    )
    _write_json(
        tmp_path / "data/evals/benchmark/freeze-v1/privacy_verification.json",
        {"privacy_verification_passed": True},
    )
    return tmp_path


def _build(
    fixture_repo: Path,
) -> tuple[
    FullABCDependencyLock,
    FullABCConditionFingerprintManifest,
    FullABCReconciliationInput,
    FullABCReconciledExecutionManifestDraft,
    FullABCReconciledPlannedRunLedger,
    FullABCReconciliationReport,
    FullABCReconciliationManifest,
    FullABCReconciliationSummary,
]:
    return build_reconciliation_assets(
        repo_root=fixture_repo,
        spec_path=SPEC_RELATIVE,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_head=False,
    )


def test_spec_binds_exact_pr96_lineage() -> None:
    spec = load_full_abc_reconciliation_spec(ROOT / SPEC_RELATIVE)

    assert spec.source_merge_commit == SOURCE_COMMIT
    assert spec.expected_integration_design_sha256.startswith("5ee5bc86")
    assert spec.expected_integration_implementation_sha256.startswith("758da13f")
    assert spec.expected_asset_inventory_sha256.startswith("900b3b80")
    assert spec.execution_enabled is False
    assert spec.measured_execution_authorized is False


def test_dependency_lock_captures_exact_environment(fixture_repo: Path) -> None:
    lock = build_dependency_lock(
        repo_root=fixture_repo,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
    )

    assert lock.project_name == "auragateway"
    assert lock.project_version == "0.1.0"
    assert lock.python_version == "3.12.10"
    assert tuple(package.distribution_name for package in lock.packages) == tuple(VERSIONS)
    assert tuple(package.version for package in lock.packages) == tuple(VERSIONS.values())
    assert len(lock.fingerprint()) == 64


def test_dependency_lock_fails_when_distribution_is_missing(fixture_repo: Path) -> None:
    def missing(name: str) -> str:
        if name == "groq":
            from importlib.metadata import PackageNotFoundError

            raise PackageNotFoundError(name)
        return VERSIONS[name]

    with pytest.raises(FullABCReconciliationError, match="required AuraGateway distribution"):
        build_dependency_lock(
            repo_root=fixture_repo,
            version_resolver=missing,
            python_version="3.12.10",
            python_implementation="CPython",
        )


def test_condition_fingerprints_are_distinct_and_current(fixture_repo: Path) -> None:
    spec = load_full_abc_reconciliation_spec(fixture_repo / SPEC_RELATIVE)
    lock = build_dependency_lock(
        repo_root=fixture_repo,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
    )
    manifest = build_condition_fingerprints(
        repo_root=fixture_repo,
        spec=spec,
        dependency_lock=lock,
        legacy_input=_legacy_input(),
    )

    assert tuple(record.payload.condition_id for record in manifest.records) == tuple(ConditionId)
    assert len({record.configuration_fingerprint for record in manifest.records}) == 3
    assert all(record.payload.source_merge_commit == SOURCE_COMMIT for record in manifest.records)
    assert all(
        record.payload.dependency_lock_sha256 == lock.fingerprint() for record in manifest.records
    )


def test_reconciled_ledger_has_exact_suite_counts(fixture_repo: Path) -> None:
    _, fingerprints, _, _, ledger, _, _, _ = _build(fixture_repo)

    assert ledger.functional_trajectory_count == 162
    assert ledger.runtime_trajectory_count == 180
    assert ledger.total_trajectory_count == 342
    assert ledger.total_turn_count == 1368
    assert ledger.maximum_request_attempt_count == 2736
    assert len(ledger.runs) == 342
    assert ledger.condition_fingerprints_sha256 == fingerprints.fingerprint()


def test_reconciled_ledger_preserves_counterbalance_order(fixture_repo: Path) -> None:
    *_, ledger, _, _, _ = _build(fixture_repo)

    assert [run.condition_id for run in ledger.runs[:9]] == [
        ConditionId.A,
        ConditionId.B,
        ConditionId.C,
        ConditionId.B,
        ConditionId.C,
        ConditionId.A,
        ConditionId.C,
        ConditionId.A,
        ConditionId.B,
    ]
    assert ledger.runs[0].run_id == "run-functional-ep-func-001-r01-condition-a"
    assert ledger.runs[-1].run_id == "run-runtime-ep-func-012-r10-condition-a"


def test_every_run_binds_its_condition_fingerprint(fixture_repo: Path) -> None:
    _, fingerprints, _, _, ledger, _, _, _ = _build(fixture_repo)

    expected = {condition: fingerprints.fingerprint_for(condition) for condition in ConditionId}
    assert all(run.configuration_fingerprint == expected[run.condition_id] for run in ledger.runs)


def test_reconciled_draft_binds_current_lineage(fixture_repo: Path) -> None:
    lock, fingerprints, _, draft, _, _, _, _ = _build(fixture_repo)

    assert draft.identity.git_commit_sha == SOURCE_COMMIT
    assert draft.identity.dependency_lock_sha256 == lock.fingerprint()
    assert draft.identity.condition_fingerprints_sha256 == fingerprints.fingerprint()
    assert draft.identity.execution_enabled is False
    assert draft.assets.pricing_schedule_id.endswith("2026-07-13")
    assert draft.assets.cross_condition_isolation_test_sha256 is None
    assert draft.assets.provider_readiness_record_sha256 is None


def test_reconciled_draft_resolves_static_freeze_inputs(fixture_repo: Path) -> None:
    *_, draft, _, _, _, _ = _build(fixture_repo)

    assert len(draft.assets.pricing_schedule_sha256) == 64
    assert len(draft.assets.negative_control_manifest_sha256) == 64
    assert len(draft.assets.fault_injection_fixture_sha256) == 64
    assert len(draft.assets.privacy_verification_report_sha256) == 64
    assert draft.assets.currency == "USD"


def test_reconciled_draft_keeps_freeze_outputs_unresolved(fixture_repo: Path) -> None:
    *_, draft, _, _, _, _ = _build(fixture_repo)

    assert draft.unresolved_freeze_assets == (
        "cost_budget_approval",
        "cross_condition_isolation_report",
        "final_execution_manifest",
        "freeze_report",
        "gate10_manifest",
        "provider_readiness_record",
    )
    assert draft.measured_execution_authorized is False
    assert draft.provider_execution_authorized is False
    assert draft.gpu_execution_authorized is False


def test_reconciliation_report_separates_local_and_external_gates(fixture_repo: Path) -> None:
    *_, report, _, _ = _build(fixture_repo)

    by_name = {check.check_name: check.status for check in report.checks}
    assert by_name[FullABCReconciliationCheckName.DEPENDENCY_LOCK_RESOLVED] is (
        FullABCReconciliationCheckStatus.PASSED
    )
    assert by_name[FullABCReconciliationCheckName.PROVIDER_READINESS_PENDING] is (
        FullABCReconciliationCheckStatus.BLOCKED_EXTERNAL
    )
    assert by_name[FullABCReconciliationCheckName.FREEZE_OUTPUTS_PENDING] is (
        FullABCReconciliationCheckStatus.PENDING_FREEZE
    )
    assert report.planning_ready is True
    assert report.measured_execution_ready is False


def test_reconciliation_manifest_binds_every_generated_artifact(fixture_repo: Path) -> None:
    lock, fingerprints, input_asset, draft, ledger, report, manifest, summary = _build(fixture_repo)

    assert manifest.dependency_lock_sha256 == lock.fingerprint()
    assert manifest.condition_fingerprints_sha256 == fingerprints.fingerprint()
    assert manifest.input_sha256 == input_asset.fingerprint()
    assert manifest.execution_manifest_sha256 == draft.fingerprint()
    assert manifest.plan_sha256 == ledger.fingerprint()
    assert manifest.report_sha256 == report.fingerprint()
    assert summary.reconciliation_manifest_sha256 == manifest.fingerprint()


def test_build_is_deterministic(fixture_repo: Path) -> None:
    first = _build(fixture_repo)
    second = _build(fixture_repo)

    assert tuple(model.canonical_json() for model in first) == tuple(
        model.canonical_json() for model in second
    )


def test_generate_and_verify_round_trip(fixture_repo: Path) -> None:
    written = write_reconciliation_assets(
        repo_root=fixture_repo,
        spec_path=SPEC_RELATIVE,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_head=False,
    )
    verified = verify_reconciliation_assets(
        repo_root=fixture_repo,
        spec_path=SPEC_RELATIVE,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_head=False,
    )

    assert written == verified
    for relative in (
        _DEPENDENCY_LOCK_PATH,
        _CONDITION_FINGERPRINTS_PATH,
        _INPUT_PATH,
        _DRAFT_PATH,
        _LEDGER_PATH,
        _REPORT_PATH,
        _MANIFEST_PATH,
    ):
        assert (fixture_repo / relative).is_file()
        assert (fixture_repo / relative).read_bytes().endswith(b"}")


def test_verify_detects_modified_output(fixture_repo: Path) -> None:
    write_reconciliation_assets(
        repo_root=fixture_repo,
        spec_path=SPEC_RELATIVE,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_head=False,
    )
    (fixture_repo / _REPORT_PATH).write_text("{}", encoding="utf-8")

    with pytest.raises(FullABCReconciliationError, match="not reproducible"):
        verify_reconciliation_assets(
            repo_root=fixture_repo,
            spec_path=SPEC_RELATIVE,
            version_resolver=_version_resolver,
            python_version="3.12.10",
            python_implementation="CPython",
            verify_git_head=False,
        )


def test_legacy_plan_drift_fails_closed(fixture_repo: Path) -> None:
    spec = load_full_abc_reconciliation_spec(fixture_repo / SPEC_RELATIVE)
    lock = build_dependency_lock(
        repo_root=fixture_repo,
        version_resolver=_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
    )
    legacy = _legacy_input()
    fingerprints = build_condition_fingerprints(
        repo_root=fixture_repo,
        spec=spec,
        dependency_lock=lock,
        legacy_input=legacy,
    )
    plan_request = legacy["plan_request"]
    assert isinstance(plan_request, dict)
    plan_request["turns_per_episode"] = 5

    with pytest.raises(FullABCReconciliationError, match="no longer matches"):
        build_reconciled_ledger(
            legacy_input=legacy,
            source_path=fixture_repo / spec.legacy_input_path,
            condition_fingerprints=fingerprints,
        )


def test_summary_grants_no_execution_authority(fixture_repo: Path) -> None:
    *_, summary = _build(fixture_repo)

    assert summary.total_trajectory_count == 342
    assert summary.planning_ready is True
    assert summary.draft_current is True
    assert summary.measured_execution_ready is False
    assert summary.execution_enabled is False
    assert summary.measured_execution_permitted is False
    assert summary.next_gate == "full_abc_provider_readiness_and_budget_review"


def test_reconciliation_docs_preserve_execution_boundary() -> None:
    adr = (
        ROOT / "docs/adr/2026-07-18-local-abc-full-abc-execution-manifest-draft-reconciliation.md"
    ).read_text(encoding="utf-8")
    report = (
        ROOT / "docs/benchmarks/"
        "local_abc_auragateway_full_abc_execution_manifest_draft_reconciliation_v2.md"
    ).read_text(encoding="utf-8")

    assert "execution_enabled=false" in adr
    assert "measured_execution_permitted=false" in adr
    assert "full_abc_provider_readiness_and_budget_review" in adr
    assert "provider_readiness_record" in report
    assert "cost_budget_approval" in report
    assert "Gate 10" in report


def test_reconciliation_spec_is_canonical_single_line_json() -> None:
    raw = (ROOT / SPEC_RELATIVE).read_text(encoding="utf-8")
    spec = load_full_abc_reconciliation_spec(ROOT / SPEC_RELATIVE)

    assert raw == spec.canonical_json() + "\n"
    assert spec.fingerprint() == (
        "e7bd972fe11f055b21fe66ae1d5deb362db37ad35b7c593327ef103afbda5678"
    )
