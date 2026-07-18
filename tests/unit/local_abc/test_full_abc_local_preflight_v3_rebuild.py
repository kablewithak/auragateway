from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import auragateway.local_abc.full_abc_local_preflight_v3_rebuild as rebuild
from auragateway.local_abc.contracts import ConditionId
from auragateway.local_abc.full_abc_local_preflight_v3_rebuild import (
    build_condition_fingerprints,
    build_developer_dependency_lock,
    build_planned_run_ledger,
    build_preflight_v3_bundle,
    generate_preflight_v3,
    load_preflight_v3_implementation_plan,
    validate_written_preflight_v3_bundle,
    verify_preflight_v3,
)
from auragateway.local_abc.full_abc_local_preflight_v3_rebuild_contracts import (
    _BENCHMARK_CONSTITUTION_SHA256,
    _EXECUTION_REQUIREMENTS_SHA256,
    CONDITION_FINGERPRINTS_PATH,
    DEVELOPER_LOCK_PATH,
    DRAFT_PATH,
    IMPLEMENTATION_ID,
    IMPLEMENTATION_PLAN_PATH,
    INPUT_PATH,
    LEDGER_PATH,
    MANIFEST_PATH,
    NEXT_GATE,
    REPORT_PATH,
    REVIEW_SHA256,
    SOURCE_MAIN_MERGE_COMMIT,
    ConditionFingerprintManifest,
    DeveloperDependencyLock,
    DeveloperDependencyPackage,
    DeveloperDependencyRole,
    ExecutionManifestDraft,
    ExecutionManifestPlanningIdentity,
    FullABCLocalPreflightV3RebuildError,
    GeneratedPreflightV3Bundle,
    PlannedRunLedger,
    PreflightV3Manifest,
)
from auragateway.local_abc.full_abc_local_preflight_v3_rebuild_review import (
    build_default_review,
)

ROOT = Path(__file__).resolve().parents[3]

FAKE_VERSIONS = {
    "groq": "1.5.0",
    "pydantic": "2.13.4",
    "mypy": "1.20.2",
    "pytest": "9.1.1",
    "ruff": "0.15.21",
    "setuptools": "80.9.0",
}


def fake_version_resolver(name: str) -> str:
    return FAKE_VERSIONS[name]


def write_pyproject(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "auragateway"
version = "0.1.0"
dependencies = ["groq>=1.5,<2", "pydantic>=2.12,<3"]

[project.optional-dependencies]
dev = ["mypy>=1.15,<2", "pytest>=8,<10", "ruff>=0.15,<0.16"]
""",
        encoding="utf-8",
    )


def build_lock(tmp_path: Path) -> DeveloperDependencyLock:
    write_pyproject(tmp_path)
    return build_developer_dependency_lock(
        repo_root=tmp_path,
        version_resolver=fake_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
    )


def patch_synthetic_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rebuild,
        "load_full_abc_local_preflight_v3_rebuild_review",
        lambda _path: build_default_review(),
    )
    monkeypatch.setattr(
        rebuild,
        "_require_expected_digest",
        lambda _path, expected, *, asset_id: expected,
    )

    def load_object(path: Path) -> dict[str, object]:
        name = path.name
        if name == "auragateway_full_abc_local_runtime_lineage_correction_v1.json":
            return {
                "groq_in_full_abc_scope": False,
                "openrouter_in_full_abc_scope": False,
                "pricing_schedule_required": False,
                "measured_execution_authorized": False,
            }
        if name == "hosted_provider_lineage_supersession_v1.json":
            return {
                "preflight_v2_reuse_permitted": False,
                "execution_authorized": False,
            }
        if name == "accepted_episodes.json":
            return {"episodes": [{"episode_id": f"ep-func-{index:03d}"} for index in range(1, 19)]}
        if name == "selection.json":
            return {
                "entries": [
                    {"episode_id": episode_id}
                    for episode_id in (
                        "ep-func-001",
                        "ep-func-002",
                        "ep-func-005",
                        "ep-func-006",
                        "ep-func-010",
                        "ep-func-012",
                    )
                ]
            }
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        return {}

    monkeypatch.setattr(rebuild, "_load_json_object", load_object)


def build_synthetic_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> GeneratedPreflightV3Bundle:
    patch_synthetic_sources(monkeypatch)
    write_pyproject(tmp_path)
    return build_preflight_v3_bundle(
        repo_root=tmp_path,
        version_resolver=fake_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_ancestry=False,
    )


def test_source_digest_uses_exact_file_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text('{\n  "value": 1\n}\n', encoding="utf-8")
    expected_raw_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    canonical_sha256 = hashlib.sha256(
        json.dumps(
            {"value": 1},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    assert expected_raw_sha256 != canonical_sha256
    assert (
        rebuild._require_expected_digest(
            source,
            expected_raw_sha256,
            asset_id="source-fixture",
        )
        == expected_raw_sha256
    )


def test_developer_lock_separates_groq_from_active_runtime(tmp_path: Path) -> None:
    lock = build_lock(tmp_path)
    packages = {item.distribution_name: item for item in lock.packages}

    assert packages["groq"].role is DeveloperDependencyRole.HISTORICAL_HOSTED_PROVIDER
    assert packages["groq"].active_full_abc_runtime_dependency is False
    assert packages["pydantic"].role is DeveloperDependencyRole.ACTIVE_RUNTIME
    assert packages["pydantic"].active_full_abc_runtime_dependency is True
    assert lock.hosted_provider_packages_active_for_full_abc is False
    assert lock.kaggle_runtime_lock_generated is False


def test_developer_lock_captures_auragateway_ruff_version(tmp_path: Path) -> None:
    lock = build_lock(tmp_path)
    versions = {item.distribution_name: item.version for item in lock.packages}

    assert versions["ruff"] == "0.15.21"
    assert lock.python_version == "3.12.10"


def test_non_cpython_generation_fails_closed(tmp_path: Path) -> None:
    write_pyproject(tmp_path)

    with pytest.raises(
        FullABCLocalPreflightV3RebuildError,
        match="requires CPython",
    ):
        build_developer_dependency_lock(
            repo_root=tmp_path,
            version_resolver=fake_version_resolver,
            python_version="3.12.10",
            python_implementation="PyPy",
        )


def test_groq_cannot_be_promoted_to_active_runtime() -> None:
    with pytest.raises(ValidationError, match="active runtime flag"):
        DeveloperDependencyPackage(
            distribution_name="groq",
            version="1.5.0",
            role=DeveloperDependencyRole.HISTORICAL_HOSTED_PROVIDER,
            active_full_abc_runtime_dependency=True,
        )


def test_condition_fingerprints_preserve_causal_invariants(tmp_path: Path) -> None:
    manifest, placeholder, metric_plan, runtime = build_condition_fingerprints(
        developer_lock=build_lock(tmp_path)
    )
    by_id = {record.payload.condition_id: record.payload for record in manifest.records}

    assert by_id[ConditionId.A].route_schedule == by_id[ConditionId.B].route_schedule
    assert by_id[ConditionId.B].prefix_token_hash == by_id[ConditionId.C].prefix_token_hash
    assert by_id[ConditionId.A].prefix_token_hash != by_id[ConditionId.B].prefix_token_hash
    assert by_id[ConditionId.A].shared == by_id[ConditionId.B].shared
    assert by_id[ConditionId.B].shared == by_id[ConditionId.C].shared
    assert placeholder.values_guessed is False
    assert metric_plan.missing_field_becomes_zero is False
    assert runtime.current_full_run_environment_requalification_required is True


def test_condition_fingerprints_exclude_provider_pricing_and_budget(
    tmp_path: Path,
) -> None:
    manifest, _placeholder, _metric_plan, _runtime = build_condition_fingerprints(
        developer_lock=build_lock(tmp_path)
    )
    payload = manifest.canonical_json()

    assert "pricing_schedule" not in payload
    assert "provider_adapter" not in payload
    assert "provider_readiness" not in payload
    assert "cost_budget" not in payload
    assert manifest.trace_compatibility.field_name == "provider_model_alias"
    assert manifest.trace_compatibility.field_value == "local-qwen2.5-0.5b-instruct"


def test_b_c_prefix_drift_fails_closed(tmp_path: Path) -> None:
    manifest, _placeholder, _metric_plan, _runtime = build_condition_fingerprints(
        developer_lock=build_lock(tmp_path)
    )
    payload = manifest.model_dump(mode="json")
    payload["records"][2]["payload"]["prefix_token_hash"] = "0" * 64
    payload["records"][2]["configuration_fingerprint"] = "0" * 64

    with pytest.raises(ValidationError):
        ConditionFingerprintManifest.model_validate(payload)


def test_planned_ledger_contains_exact_342_trajectories(tmp_path: Path) -> None:
    manifest, _placeholder, _metric_plan, _runtime = build_condition_fingerprints(
        developer_lock=build_lock(tmp_path)
    )
    identity = ExecutionManifestPlanningIdentity(
        execution_manifest_id="execution-manifest-auragateway-local-abc-v3-draft",
        execution_manifest_version="0.3.0-planning-draft",
        execution_manifest_status="planning_draft",
        source_main_merge_commit=SOURCE_MAIN_MERGE_COMMIT,
        review_sha256=REVIEW_SHA256,
        developer_dependency_lock_sha256=manifest.developer_dependency_lock_sha256,
        condition_fingerprints_sha256=manifest.fingerprint(),
        benchmark_constitution_sha256=_BENCHMARK_CONSTITUTION_SHA256,
        execution_requirements_sha256=_EXECUTION_REQUIREMENTS_SHA256,
    )
    ledger = build_planned_run_ledger(
        functional_episode_ids=tuple(f"ep-func-{index:03d}" for index in range(1, 19)),
        runtime_episode_ids=(
            "ep-func-001",
            "ep-func-002",
            "ep-func-005",
            "ep-func-006",
            "ep-func-010",
            "ep-func-012",
        ),
        fingerprints=manifest,
        planning_identity=identity,
    )

    assert len(ledger.runs) == 342
    assert ledger.functional_trajectory_count == 162
    assert ledger.runtime_trajectory_count == 180
    assert ledger.total_turn_count == 1368
    assert ledger.maximum_request_attempt_count == 2736
    assert len({run.run_id for run in ledger.runs}) == 342
    assert len({run.trace_id for run in ledger.runs}) == 342
    assert len({run.cache_namespace_id for run in ledger.runs}) == 342


def test_ledger_never_reuses_preflight_v2_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)
    serialized = bundle.planned_run_ledger.canonical_json()

    assert bundle.planned_run_ledger.reuse_preflight_v2_hash_bindings is False
    assert "6af3b45b8495ad41ef93b71db156305b78f9b72bf0de0ce04637f013c09ef6d0" not in serialized
    assert "44c69022985216f88fff5186a563724d8cb9b715577d47bfe1629a8ea19edd88" not in serialized


def test_bundle_keeps_execution_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)

    assert bundle.execution_manifest_draft.identity.execution_enabled is False
    assert bundle.execution_manifest_draft.identity.execution_manifest_frozen is False
    assert bundle.execution_manifest_draft.measured_execution_authorized is False
    assert bundle.execution_manifest_draft.gpu_execution_authorized is False
    assert bundle.execution_manifest_draft.provider_execution_authorized is False
    assert bundle.execution_manifest_draft.external_spend == 0
    assert bundle.preflight_report.decision == "PLANNING_ASSETS_GENERATED_EXECUTION_BLOCKED"
    assert bundle.preflight_report.next_gate == NEXT_GATE


def test_draft_retains_every_later_gate_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)
    unresolved = set(bundle.execution_manifest_draft.unresolved_assets)

    assert "current-environment-report" in unresolved
    assert "kaggle-runtime-dependency-lock" in unresolved
    assert "cache-observability-qualification" in unresolved
    assert "variance-pilot" in unresolved
    assert "execution-manifest-freeze" in unresolved
    assert "measured-execution-authorization" in unresolved


def test_generated_manifest_cross_binds_six_non_self_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)

    assert len(bundle.manifest.artifacts) == 6
    assert tuple(item.artifact_id for item in bundle.manifest.artifacts) == (
        "condition-fingerprints",
        "developer-dependency-lock",
        "execution-manifest-draft",
        "input",
        "planned-run-ledger",
        "preflight-report",
    )
    assert bundle.manifest.planning_lineage_complete is True
    assert bundle.manifest.execution_enabled is False


def test_manifest_cannot_bind_itself() -> None:
    payload = {
        "manifest_id": "auragateway-full-abc-local-preflight-v3-manifest-v1",
        "source_main_merge_commit": SOURCE_MAIN_MERGE_COMMIT,
        "implementation_id": IMPLEMENTATION_ID,
        "artifacts": [
            {"artifact_id": "manifest", "path": "manifest.json", "sha256": "0" * 64}
            for _ in range(6)
        ],
        "next_gate": NEXT_GATE,
    }

    with pytest.raises(ValidationError):
        PreflightV3Manifest.model_validate(payload)


def test_write_and_verify_are_byte_for_byte_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)
    rebuild.write_preflight_v3_bundle(tmp_path, bundle)

    summary = validate_written_preflight_v3_bundle(tmp_path, bundle)

    assert summary["total_trajectories"] == 342
    assert summary["execution_enabled"] is False
    assert summary["external_spend"] == 0
    for path in (
        DEVELOPER_LOCK_PATH,
        CONDITION_FINGERPRINTS_PATH,
        INPUT_PATH,
        DRAFT_PATH,
        LEDGER_PATH,
        REPORT_PATH,
        MANIFEST_PATH,
    ):
        text = (tmp_path / path).read_text(encoding="utf-8")
        assert text == json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def test_tampered_generated_asset_fails_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)
    rebuild.write_preflight_v3_bundle(tmp_path, bundle)
    (tmp_path / REPORT_PATH).write_text("{}", encoding="utf-8")

    with pytest.raises(
        FullABCLocalPreflightV3RebuildError,
        match="assets drifted",
    ):
        validate_written_preflight_v3_bundle(tmp_path, bundle)


def test_wrong_episode_count_fails_closed() -> None:
    with pytest.raises(
        FullABCLocalPreflightV3RebuildError,
        match="18 unique sorted",
    ):
        rebuild._extract_functional_episode_ids({"episodes": [{"episode_id": "ep-func-001"}]})


def test_missing_telemetry_is_never_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)

    assert bundle.execution_manifest_draft.missing_telemetry_becomes_zero is False
    condition = bundle.condition_fingerprints.records[0].payload.shared
    assert condition.metric_mapping_sha256 == rebuild._metric_mapping_plan().fingerprint()


def test_task_and_comparison_status_remain_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)

    assert bundle.execution_manifest_draft.task_status_separate_from_comparison_status is True


def test_review_approval_is_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_synthetic_sources(monkeypatch)
    write_pyproject(tmp_path)
    review = build_default_review().model_copy(
        update={"decision": "APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION"}
    )
    monkeypatch.setattr(
        rebuild,
        "load_full_abc_local_preflight_v3_rebuild_review",
        lambda _path: review.model_copy(update={"review_id": "wrong-review"}),
    )

    with pytest.raises(FullABCLocalPreflightV3RebuildError):
        build_preflight_v3_bundle(
            repo_root=tmp_path,
            version_resolver=fake_version_resolver,
            python_version="3.12.10",
            python_implementation="CPython",
            verify_git_ancestry=False,
        )


def test_implementation_plan_is_canonical_and_safe() -> None:
    path = ROOT / IMPLEMENTATION_PLAN_PATH
    plan = load_preflight_v3_implementation_plan(path)
    text = path.read_text(encoding="utf-8")

    assert plan.execution_enabled is False
    assert plan.external_spend == 0
    assert plan.next_gate == NEXT_GATE
    assert "kaggle-runtime-dependency-lock" in plan.later_gate_assets
    assert text == plan.canonical_json()


def test_repository_bundle_generation_and_committed_assets_match() -> None:
    try:
        rebuild._git_merge_is_ancestor(ROOT, SOURCE_MAIN_MERGE_COMMIT)
    except FullABCLocalPreflightV3RebuildError:
        pytest.skip("isolated validation tree does not contain the PR 99 Git ancestry")
    bundle = build_preflight_v3_bundle(repo_root=ROOT)
    summary = validate_written_preflight_v3_bundle(ROOT, bundle)

    assert summary["total_trajectories"] == 342
    assert summary["execution_enabled"] is False
    assert summary["measured_execution_authorized"] is False
    assert summary["next_gate"] == NEXT_GATE


def test_generate_then_verify_commands_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_synthetic_sources(monkeypatch)
    write_pyproject(tmp_path)
    plan_source = ROOT / IMPLEMENTATION_PLAN_PATH
    plan_target = tmp_path / IMPLEMENTATION_PLAN_PATH
    plan_target.parent.mkdir(parents=True, exist_ok=True)
    plan_target.write_text(plan_source.read_text(encoding="utf-8"), encoding="utf-8")

    generated = generate_preflight_v3(
        repo_root=tmp_path,
        version_resolver=fake_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_ancestry=False,
    )
    verified = verify_preflight_v3(
        repo_root=tmp_path,
        version_resolver=fake_version_resolver,
        python_version="3.12.10",
        python_implementation="CPython",
        verify_git_ancestry=False,
    )

    assert generated == verified
    assert generated["total_trajectories"] == 342


def test_model_types_reject_execution_enablement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)
    payload = bundle.execution_manifest_draft.model_dump(mode="json")
    payload["measured_execution_authorized"] = True

    with pytest.raises(ValidationError):
        ExecutionManifestDraft.model_validate(payload)


def test_ledger_rejects_missing_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = build_synthetic_bundle(tmp_path, monkeypatch)
    payload = bundle.planned_run_ledger.model_dump(mode="json")
    payload["runs"] = payload["runs"][:-1]

    with pytest.raises(ValidationError, match="exactly 342"):
        PlannedRunLedger.model_validate(payload)


def test_condition_manifest_rejects_duplicate_condition_order(tmp_path: Path) -> None:
    manifest, _placeholder, _metric_plan, _runtime = build_condition_fingerprints(
        developer_lock=build_lock(tmp_path)
    )
    payload = manifest.model_dump(mode="json")
    payload["records"][1] = payload["records"][0]

    with pytest.raises(ValidationError):
        ConditionFingerprintManifest.model_validate(payload)
