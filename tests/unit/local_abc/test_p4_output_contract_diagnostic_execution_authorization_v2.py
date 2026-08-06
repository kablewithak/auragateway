from __future__ import annotations

import hashlib
import importlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

module: Any = importlib.import_module(
    "auragateway.local_abc.p4_output_contract_diagnostic_execution_authorization_v2"
)
legacy: Any = importlib.import_module(
    "auragateway.local_abc.p4_output_contract_diagnostic_execution_authorization_v1"
)

ROOT = Path(__file__).resolve().parents[3]
FIXED_NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
SYNTHETIC = os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1"


def _receipt(name: str) -> Any:
    return module.ArtifactReceipt(
        repository_path=name,
        sha256="a" * 64,
    )


def _implementation_stub() -> Any:
    return module.ImplementationAuthority(
        original_implementation_merge_commit="a" * 40,
        evidence_contract_feature_commit="b" * 40,
        evidence_contract_merge_commit="c" * 40,
        terminal_closure_feature_commit="d" * 40,
        terminal_closure_merge_commit="e" * 40,
        previous_issuer_feature_commit=(module.PREVIOUS_ISSUER_FEATURE_COMMIT),
        previous_issuer_merge_commit=(module.PREVIOUS_ISSUER_MERGE_COMMIT),
        implementation_record=_receipt("record.json"),
        notebook=_receipt("notebook.ipynb"),
        request=_receipt("request.json"),
        architecture_review=_receipt("review.json"),
        implementation_source=_receipt("source.py"),
        template=_receipt("template.py.tmpl"),
        implementation_tests=_receipt("tests.py"),
        implementation_adr=_receipt("adr.md"),
        implementation_report=_receipt("report.md"),
        implementation_runbook=_receipt("runbook.md"),
        runtime_script_sha256="b" * 64,
        wrapper_code_sha256="c" * 64,
        model_snapshot_sha256="d" * 64,
        wheelhouse=legacy._wheelhouse_authority(),
        expected_runtime_outputs=legacy.EXPECTED_RUNTIME_OUTPUTS,
        terminal_evidence=legacy.TerminalEvidenceAuthority(),
        execution_budget=legacy.ExecutionBudget(),
        runtime_gpu_isolation=module.RuntimeGpuIsolationAuthority(),
    )


def _platform(
    *,
    observed_at: datetime = FIXED_NOW,
) -> Any:
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
    issuer_merge_commit: str = "f" * 40,
    confirmed_at: datetime = FIXED_NOW,
    window_minutes: int = 120,
    platform: Any | None = None,
) -> Any:
    return module.IssuanceConfirmation(
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=window_minutes,
        confirmed_issuer_merge_commit=issuer_merge_commit,
        confirmed_scope=module.AUTHORIZATION_SCOPE,
        confirmed_backend=module.SELECTED_BACKEND,
        confirmed_notebook_sha256=legacy.IMPLEMENTATION_NOTEBOOK_SHA256,
        confirmed_runtime_script_sha256=(legacy.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256),
        confirmed_wrapper_code_sha256=(legacy.IMPLEMENTATION_WRAPPER_CODE_SHA256),
        confirmed_request_sha256=legacy.IMPLEMENTATION_REQUEST_SHA256,
        confirmed_implementation_record_sha256=(legacy.IMPLEMENTATION_RECORD_SHA256),
        confirmed_model_snapshot_sha256=legacy.MODEL_SNAPSHOT_SHA256,
        confirmed_model_request_budget=18,
        confirmed_runtime_output_count=16,
        platform=platform or _platform(observed_at=confirmed_at),
    )


def _authorization(
    *,
    issued_at: datetime = FIXED_NOW,
    expires_at: datetime = FIXED_NOW + timedelta(minutes=120),
) -> Any:
    return module.ExecutionAuthorization(
        authorization_id=module.AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=module.AuthorizationLifecycle.ISSUED,
        scope=module.AUTHORIZATION_SCOPE,
        issued_from_main_commit="f" * 40,
        issued_at=issued_at,
        expires_at=expires_at,
        implementation=_implementation_stub(),
        platform=module.PlatformAllocationControls(),
        capability_observation=_platform(observed_at=issued_at),
        operator_confirmation_recorded=True,
        single_use=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        measured_abc_execution_authorized=False,
    )


def _patch_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_require_main",
        lambda repo_root, allowed_transient_paths: "f" * 40,
    )
    monkeypatch.setattr(
        module,
        "_require_ancestor",
        lambda repo_root, commit: None,
    )
    monkeypatch.setattr(
        module,
        "_require_transient_untracked",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        module,
        "_validate_static",
        lambda repo_root: object(),
    )
    monkeypatch.setattr(
        module,
        "_implementation",
        lambda repo_root: _implementation_stub(),
    )


def _abandonment() -> Any:
    return module.LegacyAuthorizationAbandonment(
        abandonment_id=(
            "auragateway-p4-output-contract-diagnostic-execution-authorization-abandonment-v1"
        ),
        status="ABANDONED_BEFORE_EXECUTION",
        legacy_authorization_id=legacy.AUTHORIZATION_ID,
        legacy_authorization_sha256=module.LEGACY_AUTHORIZATION_SHA256,
        legacy_issued_from_main_commit=module.PREVIOUS_ISSUER_MERGE_COMMIT,
        legacy_required_accelerator="T4_X1",
        observed_platform_accelerator="GPU_T4_X2",
        reason="KAGGLE_PLATFORM_ACCELERATOR_UNAVAILABLE",
        abandoned_at=FIXED_NOW,
        no_saved_version_created=True,
        runtime_execution_performed=False,
        runtime_install_attempts=0,
        model_loads=0,
        worker_starts=0,
        model_requests=0,
        authorization_reusable=False,
        operator_attested=True,
        next_gate=("issue_p4_output_contract_diagnostic_execution_authorization_v2"),
    )


def _write_abandonment(root: Path) -> None:
    path = root / module.LEGACY_ABANDONMENT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _abandonment().canonical_json(),
        encoding="utf-8",
    )


@pytest.mark.skipif(
    SYNTHETIC,
    reason="merged repository artifacts unavailable",
)
def test_runtime_gpu_isolation_is_explicit() -> None:
    authority = module._runtime_gpu_isolation(ROOT)
    assert authority.cuda_visible_devices_value == "0"
    assert authority.worker_startup_report_gpu_index_zero is True
    assert authority.one_model_load_counter is True
    assert authority.one_worker_start_counter is True


@pytest.mark.skipif(
    SYNTHETIC,
    reason="merged repository artifacts unavailable",
)
def test_implementation_binds_previous_issuer_and_runtime() -> None:
    authority = module._implementation(ROOT)
    assert authority.previous_issuer_feature_commit == (module.PREVIOUS_ISSUER_FEATURE_COMMIT)
    assert authority.previous_issuer_merge_commit == (module.PREVIOUS_ISSUER_MERGE_COMMIT)
    assert authority.runtime_gpu_isolation.cuda_visible_devices_value == "0"
    assert authority.execution_budget.maximum_model_requests == 18


@pytest.mark.skipif(
    SYNTHETIC,
    reason="merged repository artifacts unavailable",
)
def test_generate_validate_round_trip() -> None:
    generated = module.generate(ROOT)
    validated = module.validate_implementation(ROOT)
    assert generated.status.endswith("AUTHORIZATION_V2_VALID")
    assert validated["platform_accelerator"] == "GPU_T4_X2"
    assert validated["worker_cuda_visible_devices"] == "0"
    assert validated["gpu1_model_worker_permitted"] is False


def test_platform_allocation_contract_is_exact() -> None:
    controls = module.PlatformAllocationControls()
    assert controls.platform_accelerator == "GPU_T4_X2"
    assert controls.allocated_gpu_count == 2
    assert controls.worker_cuda_visible_devices == "0"
    assert controls.worker_visible_gpu_count == 1
    assert controls.worker_gpu_index == 0
    assert controls.unused_allocated_gpu_indices == (1,)
    assert controls.gpu1_model_worker_permitted is False


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
    platform = _platform(observed_at=FIXED_NOW - timedelta(minutes=16))
    with pytest.raises(ValidationError, match="older than 15 minutes"):
        _confirmation(platform=platform)


def test_authorization_window_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceeds reviewed budget"):
        _authorization(
            expires_at=FIXED_NOW + timedelta(minutes=241),
        )


def test_non_overwriting_write_preserves_existing_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text("existing", encoding="utf-8")
    with pytest.raises(module.AuthorizationError):
        module._write_non_overwriting(path, b"replacement")
    assert path.read_text(encoding="utf-8") == "existing"


def test_non_overwriting_write_uses_exact_payload(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receipt.json"
    module._write_non_overwriting(path, b"payload")
    assert path.read_bytes() == b"payload"


def test_issue_requires_legacy_abandonment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    with pytest.raises(module.AuthorizationError):
        module.issue_authorization(
            repo_root=tmp_path,
            confirmation=_confirmation(),
        )


def test_issue_verify_consume_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    _write_abandonment(tmp_path)

    issued = module.issue_authorization(
        repo_root=tmp_path,
        confirmation=_confirmation(),
    )
    assert issued["platform_accelerator"] == "GPU_T4_X2"
    assert issued["allocated_gpu_count"] == 2
    assert issued["worker_cuda_visible_devices"] == "0"

    verified = module.verify_authorization(
        repo_root=tmp_path,
        now=FIXED_NOW + timedelta(minutes=1),
    )
    assert verified["consumed"] is False
    assert verified["worker_visible_gpu_count"] == 1

    consumed = module.consume_authorization(
        repo_root=tmp_path,
        outcome=module.ExecutionOutcome.PASSED,
        saved_version_id=123456789,
        consumed_at=FIXED_NOW + timedelta(minutes=2),
    )
    assert consumed["outcome"] == "PASSED"
    assert consumed["authorization_reusable"] is False


def test_verify_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    _write_abandonment(tmp_path)
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True, exist_ok=True)
    authorization_path.write_text(
        _authorization().canonical_json(),
        encoding="utf-8",
    )
    with pytest.raises(module.AuthorizationError) as caught:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=121),
        )
    assert caught.value.error_code == "P4_AUTHORIZATION_V2_EXPIRED"


def test_legacy_abandonment_rejects_invalid_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle(monkeypatch)
    path = tmp_path.parent / "legacy-invalid.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(module.AuthorizationError):
        module.abandon_legacy_authorization(
            repo_root=tmp_path,
            archived_authorization_path=path,
            operator_confirmed=True,
            no_saved_version_created=True,
            runtime_execution_performed=False,
            abandoned_at=FIXED_NOW,
        )


def test_abandonment_receipt_is_non_reusable() -> None:
    receipt = _abandonment()
    assert receipt.status == "ABANDONED_BEFORE_EXECUTION"
    assert receipt.no_saved_version_created is True
    assert receipt.runtime_execution_performed is False
    assert receipt.authorization_reusable is False
    assert receipt.model_requests == 0


def test_transient_paths_are_outside_static_candidate() -> None:
    static = {
        module.SOURCE_PATH,
        module.TEST_PATH,
        module.ADR_PATH,
        module.REPORT_PATH,
        module.RUNBOOK_PATH,
        module.REVIEW_PATH,
        module.RECORD_PATH,
    }
    assert module.LEGACY_ABANDONMENT_PATH not in static
    assert module.AUTHORIZATION_PATH not in static
    assert module.CONSUMPTION_PATH not in static


def test_authorization_fingerprint_is_stable() -> None:
    first = _authorization()
    second = _authorization()
    assert first.fingerprint() == second.fingerprint()
    assert hashlib.sha256(first.canonical_json().encode("utf-8")).hexdigest() == first.fingerprint()
