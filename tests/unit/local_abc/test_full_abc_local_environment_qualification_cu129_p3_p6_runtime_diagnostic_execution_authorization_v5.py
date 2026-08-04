from __future__ import annotations

import hashlib
import importlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

module: Any = importlib.import_module(
    "auragateway.local_abc."
    "full_abc_local_environment_qualification_cu129_"
    "p3_p6_runtime_diagnostic_execution_authorization_v5"
)

ROOT = Path(__file__).resolve().parents[3]
FIXED_NOW = datetime(2026, 8, 4, 20, 0, tzinfo=UTC)


def _confirmation(
    *,
    confirmed_at: datetime = FIXED_NOW,
    window_minutes: int = 120,
    scope: str = module.AUTHORIZATION_SCOPE,
    notebook_sha256: str = module.IMPLEMENTATION_NOTEBOOK_SHA256,
    runtime_script_sha256: str = module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
    wrapper_code_sha256: str = module.IMPLEMENTATION_WRAPPER_CODE_SHA256,
    model_snapshot_sha256: str = module.MODEL_SNAPSHOT_SHA256,
    backend: str = module.SELECTED_BACKEND,
) -> Any:
    return module.AuthorizationIssuanceConfirmation(
        confirmation_id=(
            "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-confirmation-v5"
        ),
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=window_minutes,
        confirmed_scope=scope,
        confirmed_notebook_sha256=notebook_sha256,
        confirmed_runtime_script_sha256=runtime_script_sha256,
        confirmed_wrapper_code_sha256=wrapper_code_sha256,
        confirmed_model_snapshot_sha256=model_snapshot_sha256,
        confirmed_backend=backend,
    )


def _authorization(
    *,
    issued_at: datetime = FIXED_NOW,
    expires_at: datetime = FIXED_NOW + timedelta(minutes=120),
) -> Any:
    return module.P3P6ExecutionAuthorization(
        authorization_id=module.AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=module.AuthorizationLifecycle.ISSUED,
        scope=module.AUTHORIZATION_SCOPE,
        source_main_merge_commit=module.SOURCE_MAIN_MERGE_COMMIT,
        implementation_feature_commit=module.IMPLEMENTATION_FEATURE_COMMIT,
        implementation_record_sha256=module.IMPLEMENTATION_RECORD_SHA256,
        request_sha256=module.IMPLEMENTATION_REQUEST_SHA256,
        notebook_sha256=module.IMPLEMENTATION_NOTEBOOK_SHA256,
        runtime_script_sha256=module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=module.IMPLEMENTATION_WRAPPER_CODE_SHA256,
        model_snapshot_sha256=module.MODEL_SNAPSHOT_SHA256,
        wheelhouse=module.WheelhouseAuthority(
            requirements_in_sha256=(
                "a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f"
            ),
            resolution_lock_sha256=(
                "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
            ),
            materialization_lock_sha256=(
                "d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d"
            ),
            requirements_lock_sha256=(
                "47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27"
            ),
            install_runtime_sha256=(
                "68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821"
            ),
            runtime_manifest_sha256=(
                "b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51"
            ),
            sha256_manifest_sha256=(
                "789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d"
            ),
            materialization_receipt_sha256=(
                "52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589"
            ),
        ),
        evidence_contract=module.EvidenceContractAuthority(),
        issued_from_main_commit="f" * 40,
        issued_at=issued_at,
        expires_at=expires_at,
        operator_confirmation_recorded=True,
        single_use=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        budget=module.AuthorizationBudget(),
        controls=module.AuthorizationControls(),
    )


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="exact merged repository bytes are unavailable in synthetic fixture",
)
def test_implementation_authority_binds_merged_assets() -> None:
    authority = module._implementation_authority(ROOT)

    assert authority.source_main_merge_commit == module.SOURCE_MAIN_MERGE_COMMIT
    assert authority.implementation_feature_commit == module.IMPLEMENTATION_FEATURE_COMMIT
    assert authority.implementation_record.sha256 == module.IMPLEMENTATION_RECORD_SHA256
    assert authority.notebook.sha256 == module.IMPLEMENTATION_NOTEBOOK_SHA256
    assert authority.request.sha256 == module.IMPLEMENTATION_REQUEST_SHA256
    assert authority.architecture_review.sha256 == module.IMPLEMENTATION_REVIEW_SHA256
    assert authority.template.sha256 == module.IMPLEMENTATION_TEMPLATE_SHA256
    assert authority.implementation_source.sha256 == module.IMPLEMENTATION_SOURCE_SHA256
    assert authority.runtime_script_sha256 == module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256
    assert authority.wrapper_code_sha256 == module.IMPLEMENTATION_WRAPPER_CODE_SHA256
    assert authority.evidence_contract == module.EvidenceContractAuthority()
    assert authority.model_snapshot_sha256 == module.MODEL_SNAPSHOT_SHA256
    assert authority.wheelhouse.wheel_entry_count == 176
    assert authority.wheelhouse.verified_entry_count == 182
    assert authority.runtime_execution_authorized_before_issuance is False
    assert authority.unchanged_v4_failure_replay_authorized is False


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="exact merged repository bytes are unavailable in synthetic fixture",
)
def test_review_preserves_pre_execution_boundary() -> None:
    review = module._build_review(ROOT)

    assert review.status == "APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"
    assert review.decision == "SEPARATE_TRANSIENT_SINGLE_USE_P3_P6_V5_AUTHORIZATION"
    assert review.authorization_issued_in_review is False
    assert review.runtime_execution_performed is False
    assert review.authorization_must_remain_untracked is True
    assert review.passed_failed_or_interrupted_attempt_consumes_authorization is True
    assert review.budget.maximum_kaggle_sessions == 1
    assert review.budget.maximum_runtime_install_attempts == 1
    assert review.budget.maximum_runtime_import_closure_probes == 1
    assert review.budget.maximum_model_loads == 3
    assert review.budget.maximum_worker_starts == 3
    assert review.budget.maximum_model_requests == 5
    assert review.budget.maximum_output_tokens_per_request == 32
    assert review.budget.maximum_benchmark_trajectory_requests == 0
    assert review.controls.loopback_http_permitted is True
    assert review.controls.external_network_access_permitted is False
    assert review.controls.raw_prompt_logging_permitted is False
    assert review.controls.raw_output_logging_permitted is False
    assert review.controls.explicit_backend_required == "TRITON_ATTN"
    assert review.controls.measured_abc_execution_authorized is False
    assert review.controls.runtime_install_report_required is True
    assert review.controls.bounded_install_diagnostics_required is True
    assert review.controls.runtime_import_closure_report_required is True
    assert review.controls.process_tree_import_closure_required is True
    assert review.controls.exact_target_site_pythonpath_required is True
    assert review.controls.nested_interpreter_probe_required is True
    assert review.controls.bounded_worker_failure_diagnostics_required is True
    assert review.controls.raw_worker_logs_in_evidence_zip_permitted is False
    assert review.controls.deterministic_not_run_reports_required is True
    assert review.controls.scratch_cleanup_report_required is True
    assert review.controls.evidence_zip_required is True
    assert review.controls.maximum_evidence_zip_bytes == 2097152
    assert review.controls.wheel_find_links_relative_path == "wheels"
    assert review.controls.runtime_source_identity_report_required is True
    assert review.controls.exact_line_local_backend_marker_required is True
    assert review.controls.combined_stream_substring_matching_permitted is False
    assert review.controls.cli_echo_as_backend_evidence_permitted is False
    assert review.controls.matched_stream_line_number_and_hash_required is True
    assert review.controls.capture_threads_finalized_before_failure_serialization is True
    assert review.controls.worker_teardown_report_required is True
    assert review.controls.process_tree_absence_proof_required is True
    assert review.controls.gpu_process_absence_proof_required is True
    assert review.controls.closed_port_proof_required is True
    assert review.controls.maximum_gpu_memory_return_tolerance_mib == 128
    assert review.controls.executed_runtime_script_hash_required is True
    assert review.controls.notebook_wrapper_hash_verification_required is True
    assert review.controls.atomic_checkpoint_serialization_required is True
    assert review.controls.request_attempt_checkpoint_required is True
    assert review.controls.transport_completion_checkpoint_required is True
    assert review.controls.partial_p6_evidence_preservation_required is True
    assert review.controls.per_worker_attempt_and_completion_counters_required is True
    assert review.controls.model_requests_performed_derived_from_counters is True
    assert review.controls.typed_route_acknowledgement_required is True
    assert review.controls.model_semantics_permitted_as_p6_route_proof is False
    assert review.controls.precise_p6_failure_taxonomy_required is True
    assert review.controls.runtime_native_origin_report_required is True
    assert review.controls.cuda_stub_origin_permitted is False


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="exact merged repository bytes are unavailable in synthetic fixture",
)
def test_review_is_deterministic() -> None:
    first = module._build_review(ROOT)
    second = module._build_review(ROOT)

    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


def test_confirmation_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _confirmation(confirmed_at=datetime(2026, 8, 2, 12, 0))


def test_confirmation_rejects_window_over_budget() -> None:
    with pytest.raises(ValidationError):
        _confirmation(window_minutes=241)


def test_confirmation_rejects_scope_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(scope="FULL_ABC_EXECUTION")


def test_confirmation_rejects_notebook_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(notebook_sha256="0" * 64)


def test_confirmation_rejects_runtime_script_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(runtime_script_sha256="0" * 64)


def test_confirmation_rejects_wrapper_code_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(wrapper_code_sha256="0" * 64)


def test_confirmation_rejects_model_snapshot_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(model_snapshot_sha256="0" * 64)


def test_confirmation_rejects_backend_drift() -> None:
    with pytest.raises(ValidationError):
        _confirmation(backend="AUTO")


def test_authorization_window_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceeds reviewed budget"):
        _authorization(expires_at=FIXED_NOW + timedelta(minutes=241))


def test_build_authorization_binds_exact_budget_and_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())

    authorization = module._build_authorization(
        repo_root=tmp_path,
        issuer_head="f" * 40,
        confirmation=_confirmation(window_minutes=30),
    )

    assert authorization.scope == module.AUTHORIZATION_SCOPE
    assert authorization.notebook_sha256 == module.IMPLEMENTATION_NOTEBOOK_SHA256
    assert authorization.runtime_script_sha256 == module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256
    assert authorization.wrapper_code_sha256 == module.IMPLEMENTATION_WRAPPER_CODE_SHA256
    assert authorization.evidence_contract == module.EvidenceContractAuthority()
    assert authorization.model_snapshot_sha256 == module.MODEL_SNAPSHOT_SHA256
    assert authorization.expires_at - authorization.issued_at == timedelta(minutes=30)
    assert authorization.budget.maximum_runtime_import_closure_probes == 1
    assert authorization.budget.maximum_model_loads == 3
    assert authorization.budget.maximum_worker_starts == 3
    assert authorization.budget.maximum_model_requests == 5
    assert authorization.budget.maximum_output_tokens_per_request == 32
    assert authorization.budget.maximum_benchmark_trajectory_requests == 0
    assert authorization.controls.explicit_backend_required == "TRITON_ATTN"
    assert authorization.controls.measured_abc_execution_authorized is False
    assert authorization.controls.runtime_install_report_required is True
    assert authorization.controls.bounded_install_diagnostics_required is True
    assert authorization.controls.deterministic_not_run_reports_required is True
    assert authorization.controls.maximum_evidence_zip_bytes == 2097152
    assert authorization.controls.wheel_find_links_relative_path == "wheels"


def test_non_overwriting_write_preserves_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    path.write_text("existing", encoding="utf-8")

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module._write_non_overwriting(path, b"replacement")

    assert caught.value.error_code == "P3_P6_AUTHORIZATION_ALREADY_EXISTS"
    assert path.read_text(encoding="utf-8") == "existing"


def test_non_overwriting_write_uses_exact_payload(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    payload = _authorization().canonical_json().encode("utf-8")

    module._write_non_overwriting(path, payload)

    assert path.read_bytes() == payload


def test_load_canonical_rejects_pretty_json(tmp_path: Path) -> None:
    authorization = _authorization()
    path = tmp_path / "authorization.json"
    path.write_text(
        json.dumps(authorization.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module._load_canonical(path, module.P3P6ExecutionAuthorization)

    assert caught.value.error_code == "P3_P6_AUTHORIZATION_PAYLOAD_NOT_CANONICAL"


def test_verify_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / module.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True)
    path.write_text(_authorization().canonical_json(), encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=121),
        )

    assert caught.value.error_code == "P3_P6_AUTHORIZATION_EXPIRED"


def test_verify_rejects_consumed_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(_authorization().canonical_json(), encoding="utf-8")
    consumption_path = tmp_path / module.CONSUMPTION_PATH
    consumption_path.write_text("consumed", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module.verify_authorization(repo_root=tmp_path, now=FIXED_NOW)

    assert caught.value.error_code == "P3_P6_AUTHORIZATION_ALREADY_CONSUMED"


def test_consume_creates_single_non_reusable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization = _authorization()
    authorization_path.write_text(authorization.canonical_json(), encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)

    summary = module.consume_authorization(
        repo_root=tmp_path,
        outcome=module.ExecutionOutcome.FAILED,
        saved_version_id=339300001,
        consumed_at=FIXED_NOW + timedelta(minutes=20),
    )

    path = tmp_path / module.CONSUMPTION_PATH
    receipt = module.P3P6AuthorizationConsumption.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    assert summary["status"] == ("P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_CONSUMED")
    assert receipt.consumption_id == (
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-consumption-v5"
    )
    assert receipt.outcome == module.ExecutionOutcome.FAILED
    assert receipt.saved_version_id == 339300001
    assert receipt.runtime_script_sha256 == module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256
    assert receipt.wrapper_code_sha256 == module.IMPLEMENTATION_WRAPPER_CODE_SHA256
    assert receipt.authorization_reusable is False
    assert receipt.authorization_sha256 == authorization.fingerprint()


def test_second_consumption_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(_authorization().canonical_json(), encoding="utf-8")
    consumption_path = tmp_path / module.CONSUMPTION_PATH
    consumption_path.write_text("existing", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(module, "_require_transient_paths_untracked", lambda repo_root: None)
    monkeypatch.setattr(module, "_require_source_authority", lambda repo_root: None)

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module.consume_authorization(
            repo_root=tmp_path,
            outcome=module.ExecutionOutcome.PASSED,
            saved_version_id=339300002,
        )

    assert caught.value.error_code == "P3_P6_AUTHORIZATION_ALREADY_CONSUMED"


def test_tracked_transient_authorization_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_run_git",
        lambda repo_root, arguments: module.AUTHORIZATION_PATH.as_posix(),
    )

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module._require_transient_paths_untracked(tmp_path)

    assert caught.value.error_code == "P3_P6_AUTHORIZATION_MUST_REMAIN_UNTRACKED"


def test_source_authority_requires_merged_and_feature_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    monkeypatch.setattr(
        module,
        "_require_ancestor",
        lambda repo_root, commit: observed.append(commit),
    )

    module._require_source_authority(tmp_path)

    assert observed == [
        module.SOURCE_MAIN_MERGE_COMMIT,
        module.IMPLEMENTATION_FEATURE_COMMIT,
    ]


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="exact merged repository bytes are unavailable in synthetic fixture",
)
def test_validate_implementation_preserves_absent_authority() -> None:
    summary = module.validate_implementation_package(ROOT)

    assert summary["status"] == ("P3_P6_RUNTIME_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V5_VALID")
    assert summary["authorization_issuer_implemented"] is True
    assert summary["authorization_issued"] is False
    assert summary["runtime_execution_performed"] is False
    assert summary["maximum_kaggle_sessions"] == 1
    assert summary["maximum_runtime_install_attempts"] == 1
    assert summary["maximum_runtime_import_closure_probes"] == 1
    assert summary["maximum_model_loads"] == 3
    assert summary["maximum_worker_starts"] == 3
    assert summary["maximum_model_requests"] == 5
    assert summary["maximum_output_tokens_per_request"] == 32
    assert summary["maximum_benchmark_trajectory_requests"] == 0
    assert summary["runtime_script_sha256"] == module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256
    assert summary["wrapper_code_sha256"] == module.IMPLEMENTATION_WRAPPER_CODE_SHA256


def test_v5_authorization_identity_and_terminal_gate() -> None:
    authorization = _authorization()

    assert authorization.scope == "P3_P6_RUNTIME_DIAGNOSTIC_V5"
    assert authorization.authorization_id.endswith("authorization-v5")
    assert module.ISSUED_NEXT_GATE == "execute_governed_p3_p6_runtime_diagnostic_v5"
    assert module.CONSUMED_NEXT_GATE == "preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v5"


def test_authorization_paths_are_v5_and_untracked_by_contract() -> None:
    assert module.AUTHORIZATION_PATH.name.endswith("authorization_v5.json")
    assert module.CONSUMPTION_PATH.name.endswith("consumption_v5.json")
    assert module._allowed_transient_status(True) == (
        f"?? {module.AUTHORIZATION_PATH.as_posix()}",
        f"?? {module.CONSUMPTION_PATH.as_posix()}",
    )


def test_implementation_source_receipt_normalizes_windows_newlines(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / module.IMPLEMENTATION_SOURCE_PATH
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b'print("bound")\r\n')

    receipt = module._artifact(
        tmp_path,
        module.IMPLEMENTATION_SOURCE_PATH,
    )

    assert receipt.sha256 == hashlib.sha256(b'print("bound")\n').hexdigest()


def test_v5_authorization_binds_import_closure_and_evidence_controls() -> None:
    authorization = _authorization()

    assert authorization.budget.maximum_runtime_import_closure_probes == 1
    assert authorization.controls.runtime_import_closure_report_required is True
    assert authorization.controls.exact_target_site_pythonpath_required is True
    assert authorization.controls.model_loads_on_import_probe_failure == 0
    assert authorization.controls.worker_starts_on_import_probe_failure == 0


def test_v5_terminal_gate_and_scope() -> None:
    authorization = _authorization()

    assert authorization.scope == "P3_P6_RUNTIME_DIAGNOSTIC_V5"
    assert module.ISSUED_NEXT_GATE == ("execute_governed_p3_p6_runtime_diagnostic_v5")
    assert module.CONSUMED_NEXT_GATE == ("preserve_and_accept_p3_p6_runtime_diagnostic_evidence_v5")


def test_v5_confirmation_identity_is_exact() -> None:
    confirmation = _confirmation()

    assert confirmation.confirmation_id == (
        "auragateway-cu129-p3-p6-runtime-diagnostic-execution-authorization-confirmation-v5"
    )


def test_v5_evidence_contract_is_exact_and_fail_closed() -> None:
    contract = module.EvidenceContractAuthority()

    assert contract.accepted_backend_marker == ("Using AttentionBackendEnum.TRITON_ATTN backend.")
    assert contract.exact_line_local_backend_marker_required is True
    assert contract.combined_stream_substring_matching_permitted is False
    assert contract.cli_echo_as_backend_evidence_permitted is False
    assert contract.matched_stream_line_number_and_hash_required is True
    assert contract.capture_threads_finalized_before_failure_serialization is True
    assert contract.structured_teardown_report_required is True
    assert contract.process_tree_absence_proof_required is True
    assert contract.gpu_process_absence_proof_required is True
    assert contract.closed_port_proof_required is True
    assert contract.maximum_gpu_memory_return_tolerance_mib == 128
    assert contract.executed_runtime_script_hash_required is True
    assert contract.notebook_wrapper_hash_verification_required is True
    assert contract.atomic_checkpoint_serialization_required is True
    assert contract.request_attempt_checkpoint_required is True
    assert contract.transport_completion_checkpoint_required is True
    assert contract.partial_p6_evidence_preservation_required is True
    assert contract.per_worker_attempt_and_completion_counters_required is True
    assert contract.model_requests_performed_derived_from_counters is True
    assert contract.typed_route_acknowledgement_required is True
    assert contract.model_semantics_permitted_as_p6_route_proof is False
    assert contract.precise_p6_failure_taxonomy_required is True
    assert contract.native_origin_closure_report_required is True


def test_v5_authorization_binds_runtime_source_and_wrapper() -> None:
    authorization = _authorization()

    assert authorization.runtime_script_sha256 == (
        "44ff2b6ec032c49b1b38dab3b0c919134f70345b5fe29f7359fcd7842759b996"
    )
    assert authorization.wrapper_code_sha256 == (
        "55ac4828fcc8a2a18bb60a939416f93f4c0b2d4f36d386ec009079ca6c4babb8"
    )


def test_build_authorization_rejects_confirmation_binding_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "_validate_static_package", lambda repo_root: object())
    confirmation = object.__new__(module.AuthorizationIssuanceConfirmation)
    object.__setattr__(confirmation, "confirmed_at", FIXED_NOW)
    object.__setattr__(confirmation, "authorization_window_minutes", 30)
    object.__setattr__(confirmation, "confirmed_scope", module.AUTHORIZATION_SCOPE)
    object.__setattr__(confirmation, "confirmed_notebook_sha256", "0" * 64)
    object.__setattr__(
        confirmation,
        "confirmed_runtime_script_sha256",
        module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
    )
    object.__setattr__(
        confirmation,
        "confirmed_wrapper_code_sha256",
        module.IMPLEMENTATION_WRAPPER_CODE_SHA256,
    )
    object.__setattr__(
        confirmation,
        "confirmed_model_snapshot_sha256",
        module.MODEL_SNAPSHOT_SHA256,
    )
    object.__setattr__(confirmation, "confirmed_backend", module.SELECTED_BACKEND)

    with pytest.raises(module.P3P6AuthorizationError) as caught:
        module._build_authorization(
            repo_root=tmp_path,
            issuer_head="f" * 40,
            confirmation=confirmation,
        )

    assert caught.value.error_code == ("P3_P6_AUTHORIZATION_CONFIRMATION_BINDING_DRIFT")
