from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

module: Any = importlib.import_module(
    "auragateway.local_abc.p4_output_contract_diagnostic_execution_authorization_v3"
)

ROOT = Path(__file__).resolve().parents[3]
FIXED_NOW = datetime(2026, 8, 7, 1, 0, tzinfo=UTC)
ISSUER_HEAD = "f" * 40


def _platform(*, observed_at: datetime = FIXED_NOW) -> Any:
    return module.PlatformCapabilityConfirmation(
        observed_at=observed_at,
        capability_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
        observed_platform_accelerator="GPU_T4_X2",
        observed_allocated_gpu_count=2,
        observed_internet_enabled=False,
        observed_wheelhouse_attachment_count=1,
        observed_model_snapshot_attachment_count=1,
        confirmed_worker_cuda_visible_devices="0",
        confirmed_worker_visible_gpu_count=1,
        confirmed_worker_gpu_index=0,
    )


def _confirmation(
    *,
    issuer_head: str = ISSUER_HEAD,
    confirmed_at: datetime = FIXED_NOW,
    window_minutes: int = 120,
    platform: Any | None = None,
) -> Any:
    return module.IssuanceConfirmation(
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=window_minutes,
        confirmed_issuer_merge_commit=issuer_head,
        confirmed_scope=module.AUTHORIZATION_SCOPE,
        confirmed_implementation_merge_commit=module.IMPLEMENTATION_MERGE_COMMIT,
        confirmed_notebook_sha256=(
            "5efc4660dcfca451947189001fdf2c6efc86d2201faa91b9b145ef3219bca581"
        ),
        confirmed_runtime_script_sha256=(
            "bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"
        ),
        confirmed_wrapper_code_sha256=(
            "09e37eca21069c8ef5822711854307541ccfd7b158f2ccd902f58bba5fbd3402"
        ),
        confirmed_request_sha256=(
            "b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1"
        ),
        confirmed_implementation_record_sha256=(
            "9fbefc001af0a56995f903681c6afe251a2ce594fd21d760a26ee7783352f5c1"
        ),
        confirmed_model_snapshot_sha256=module.MODEL_SNAPSHOT_SHA256,
        confirmed_backend=module.SELECTED_BACKEND,
        confirmed_model_request_budget=18,
        confirmed_runtime_output_count=17,
        confirmed_notebook_unmodified=True,
        confirmed_single_saved_version=True,
        confirmed_no_hidden_retries=True,
        confirmed_consumption_required=True,
        platform=platform or _platform(observed_at=confirmed_at),
    )


def _patch_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    authority = module._implementation(ROOT)
    monkeypatch.setattr(
        module,
        "_require_main",
        lambda repo_root, allowed_transient_paths: ISSUER_HEAD,
    )
    monkeypatch.setattr(
        module,
        "_require_ancestor",
        lambda repo_root, commit: None,
    )
    monkeypatch.setattr(
        module,
        "_validate_static",
        lambda repo_root: object(),
    )
    monkeypatch.setattr(
        module,
        "_implementation",
        lambda repo_root: authority,
    )


def test_implementation_binds_exact_v2_and_terminalized_predecessor() -> None:
    authority = module._implementation(ROOT)

    assert authority.implementation_feature_commit == module.IMPLEMENTATION_FEATURE_COMMIT
    assert authority.implementation_merge_commit == module.IMPLEMENTATION_MERGE_COMMIT
    assert authority.implementation_status == "IMPLEMENTED_NOT_EXECUTED"
    assert authority.notebook.sha256 == (
        "5efc4660dcfca451947189001fdf2c6efc86d2201faa91b9b145ef3219bca581"
    )
    assert authority.runtime_script_sha256 == (
        "bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"
    )
    assert authority.prior_authorization_lineage.v2_saved_version_id == 340622392
    assert authority.prior_authorization_lineage.v2_outcome == "FAILED"
    assert authority.prior_authorization_lineage.v2_authorization_reusable is False


def test_v2_semantic_contract_is_exact() -> None:
    module._validate_v2_semantics(ROOT)


def test_generate_validate_round_trip() -> None:
    generated = module.generate(ROOT)
    validated = module.validate_implementation(ROOT)

    assert generated.status.endswith("AUTHORIZATION_V3_VALID")
    assert validated["implementation_merge_commit"] == module.IMPLEMENTATION_MERGE_COMMIT
    assert validated["maximum_saved_versions"] == 1
    assert validated["maximum_model_requests"] == 18
    assert validated["runtime_execution_authorized"] is False


def test_static_review_does_not_issue_authority() -> None:
    review = module._build_review(ROOT)

    assert review.runtime_execution_authorized_in_review is False
    assert review.single_use_required is True
    assert review.every_terminal_attempt_consumes_authorization is True
    assert not (ROOT / module.AUTHORIZATION_PATH).exists()
    assert not (ROOT / module.CONSUMPTION_PATH).exists()


def test_platform_and_budget_are_non_expandable() -> None:
    platform = module.PlatformControls()
    budget = module.ExecutionBudget()

    assert platform.platform_accelerator == "GPU_T4_X2"
    assert platform.worker_cuda_visible_devices == "0"
    assert platform.unused_allocated_gpu_indices == (1,)
    assert platform.gpu1_model_worker_permitted is False
    assert budget.maximum_saved_versions == 1
    assert budget.maximum_model_requests == 18
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_external_network_requests == 0


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("observed_platform_accelerator", "T4_X1"),
        ("observed_allocated_gpu_count", 1),
        ("observed_internet_enabled", True),
        ("observed_wheelhouse_attachment_count", 0),
        ("observed_model_snapshot_attachment_count", 2),
        ("confirmed_worker_cuda_visible_devices", "0,1"),
        ("confirmed_worker_visible_gpu_count", 2),
        ("confirmed_worker_gpu_index", 1),
    ],
)
def test_platform_confirmation_rejects_drift(
    field_name: str,
    value: object,
) -> None:
    payload = _platform().model_dump()
    payload[field_name] = value

    with pytest.raises(ValidationError):
        module.PlatformCapabilityConfirmation.model_validate(payload)


def test_confirmation_rejects_stale_platform_observation() -> None:
    stale = _platform(observed_at=FIXED_NOW - timedelta(minutes=16))

    with pytest.raises(ValidationError):
        _confirmation(platform=stale)


def test_confirmation_rejects_implementation_identity_drift() -> None:
    payload = _confirmation().model_dump()
    payload["confirmed_notebook_sha256"] = "0" * 64

    with pytest.raises(ValidationError):
        module.IssuanceConfirmation.model_validate(payload)


def test_issue_requires_fresh_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)

    with pytest.raises(module.AuthorizationError) as captured:
        module.issue_authorization(
            repo_root=tmp_path,
            confirmation=_confirmation(),
            now=FIXED_NOW + timedelta(minutes=16),
        )

    assert captured.value.error_code == "P4_AUTHORIZATION_V3_CONFIRMATION_STALE"
    assert not (tmp_path / module.AUTHORIZATION_PATH).exists()


def test_issue_verify_and_consume_single_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    confirmation = _confirmation()

    issued = module.issue_authorization(
        repo_root=tmp_path,
        confirmation=confirmation,
        now=FIXED_NOW,
    )
    verified = module.verify_authorization(
        repo_root=tmp_path,
        now=FIXED_NOW + timedelta(minutes=1),
    )
    consumed = module.consume_authorization(
        repo_root=tmp_path,
        outcome=module.ExecutionOutcome.FAILED,
        saved_version_id=341000001,
        consumed_at=FIXED_NOW + timedelta(minutes=2),
    )

    assert issued["runtime_execution_authorized"] is True
    assert verified["consumed"] is False
    assert consumed["runtime_execution_authorized"] is False
    assert consumed["authorization_reusable"] is False

    with pytest.raises(module.AuthorizationError) as captured:
        module.consume_authorization(
            repo_root=tmp_path,
            outcome=module.ExecutionOutcome.FAILED,
            saved_version_id=341000001,
            consumed_at=FIXED_NOW + timedelta(minutes=3),
        )

    assert captured.value.error_code == "P4_AUTHORIZATION_V3_ALREADY_CONSUMED"


def test_verify_rejects_expired_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    module.issue_authorization(
        repo_root=tmp_path,
        confirmation=_confirmation(window_minutes=1),
        now=FIXED_NOW,
    )

    with pytest.raises(module.AuthorizationError) as captured:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=2),
        )

    assert captured.value.error_code == "P4_AUTHORIZATION_V3_EXPIRED"


def test_issue_is_non_overwriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    confirmation = _confirmation()
    module.issue_authorization(
        repo_root=tmp_path,
        confirmation=confirmation,
        now=FIXED_NOW,
    )

    with pytest.raises(module.AuthorizationError) as captured:
        module.issue_authorization(
            repo_root=tmp_path,
            confirmation=confirmation,
            now=FIXED_NOW,
        )

    assert captured.value.error_code == "P4_AUTHORIZATION_V3_ALREADY_EXISTS"


def test_every_terminal_outcome_is_representable() -> None:
    assert {outcome.value for outcome in module.ExecutionOutcome} == {
        "PASSED",
        "FAILED",
        "INTERRUPTED",
        "TIMED_OUT",
        "KAGGLE_PLATFORM_TERMINATED",
    }


def test_confirmation_file_must_be_canonical(tmp_path: Path) -> None:
    path = tmp_path / "confirmation.json"
    payload = _confirmation().model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(module.AuthorizationError) as captured:
        module._load_confirmation(path)

    assert captured.value.error_code == "P4_AUTHORIZATION_V3_CONFIRMATION_NOT_CANONICAL"


def test_exact_artifact_mutation_is_detected(tmp_path: Path) -> None:
    relative = module.V2_REQUEST_PATH
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / relative).read_bytes() + b"\n")

    with pytest.raises(module.AuthorizationError) as captured:
        module._expected_artifact(tmp_path, relative)

    assert captured.value.error_code == ("P4_AUTHORIZATION_V3_IMPLEMENTATION_IDENTITY_DRIFT")


def test_transient_lifecycle_paths_are_not_static_outputs() -> None:
    static_paths = {
        module.SOURCE_PATH,
        module.TEST_PATH,
        module.ADR_PATH,
        module.REPORT_PATH,
        module.RUNBOOK_PATH,
        module.REVIEW_PATH,
        module.RECORD_PATH,
    }

    assert module.AUTHORIZATION_PATH not in static_paths
    assert module.CONSUMPTION_PATH not in static_paths
