from __future__ import annotations

import importlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

module: Any = importlib.import_module(
    "auragateway.local_abc.p4_output_contract_diagnostic_execution_authorization_v1"
)

ROOT = Path(__file__).resolve().parents[3]
FIXED_NOW = datetime(2026, 8, 5, 23, 0, tzinfo=UTC)
SYNTHETIC_FIXTURE = os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1"


def _confirmation(
    *,
    confirmed_at: datetime = FIXED_NOW,
    window_minutes: int = 120,
    scope: str = module.AUTHORIZATION_SCOPE,
    source_main_merge_commit: str = module.SOURCE_MAIN_MERGE_COMMIT,
    terminal_closure_feature_commit: str = module.TERMINAL_CLOSURE_FEATURE_COMMIT,
    notebook_sha256: str = module.IMPLEMENTATION_NOTEBOOK_SHA256,
    runtime_script_sha256: str = module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
    wrapper_code_sha256: str = module.IMPLEMENTATION_WRAPPER_CODE_SHA256,
    request_sha256: str = module.IMPLEMENTATION_REQUEST_SHA256,
    record_sha256: str = module.IMPLEMENTATION_RECORD_SHA256,
    model_snapshot_sha256: str = module.MODEL_SNAPSHOT_SHA256,
    backend: str = module.SELECTED_BACKEND,
    model_request_budget: int = 18,
    runtime_output_count: int = 16,
    terminal_path_output_contract_complete: bool = True,
) -> Any:
    return module.AuthorizationIssuanceConfirmation(
        confirmation_id=(
            "auragateway-p4-output-contract-diagnostic-execution-authorization-confirmation-v1"
        ),
        operator_confirmed=True,
        confirmed_at=confirmed_at,
        authorization_window_minutes=window_minutes,
        confirmed_scope=scope,
        confirmed_source_main_merge_commit=source_main_merge_commit,
        confirmed_terminal_closure_feature_commit=terminal_closure_feature_commit,
        confirmed_notebook_sha256=notebook_sha256,
        confirmed_runtime_script_sha256=runtime_script_sha256,
        confirmed_wrapper_code_sha256=wrapper_code_sha256,
        confirmed_request_sha256=request_sha256,
        confirmed_implementation_record_sha256=record_sha256,
        confirmed_model_snapshot_sha256=model_snapshot_sha256,
        confirmed_backend=backend,
        confirmed_model_request_budget=model_request_budget,
        confirmed_runtime_output_count=runtime_output_count,
        confirmed_terminal_path_output_contract_complete=(terminal_path_output_contract_complete),
    )


def _authorization(
    *,
    issued_at: datetime = FIXED_NOW,
    expires_at: datetime = FIXED_NOW + timedelta(minutes=120),
) -> Any:
    return module.P4ExecutionAuthorization(
        authorization_id=module.AUTHORIZATION_ID,
        decision="AUTHORIZED",
        lifecycle=module.AuthorizationLifecycle.ISSUED,
        scope=module.AUTHORIZATION_SCOPE,
        original_implementation_merge_commit=(module.ORIGINAL_IMPLEMENTATION_MERGE_COMMIT),
        evidence_contract_feature_commit=module.EVIDENCE_CONTRACT_FEATURE_COMMIT,
        evidence_contract_merge_commit=module.EVIDENCE_CONTRACT_MERGE_COMMIT,
        terminal_closure_feature_commit=module.TERMINAL_CLOSURE_FEATURE_COMMIT,
        terminal_closure_merge_commit=module.TERMINAL_CLOSURE_MERGE_COMMIT,
        source_main_merge_commit=module.SOURCE_MAIN_MERGE_COMMIT,
        implementation_record_sha256=module.IMPLEMENTATION_RECORD_SHA256,
        request_sha256=module.IMPLEMENTATION_REQUEST_SHA256,
        notebook_sha256=module.IMPLEMENTATION_NOTEBOOK_SHA256,
        runtime_script_sha256=module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=module.IMPLEMENTATION_WRAPPER_CODE_SHA256,
        model_snapshot_sha256=module.MODEL_SNAPSHOT_SHA256,
        wheelhouse=module._wheelhouse_authority(),
        expected_runtime_outputs=module.EXPECTED_RUNTIME_OUTPUTS,
        terminal_evidence=module.TerminalEvidenceAuthority(),
        issued_from_main_commit="f" * 40,
        issued_at=issued_at,
        expires_at=expires_at,
        operator_confirmation_recorded=True,
        single_use=True,
        passed_failed_or_interrupted_attempt_consumes_authorization=True,
        unchanged_replay_authorized=False,
        budget=module.ExecutionBudget(),
        controls=module.AuthorizationControls(),
    )


@pytest.mark.skipif(
    SYNTHETIC_FIXTURE,
    reason="exact merged repository bytes unavailable in synthetic fixture",
)
def test_implementation_authority_binds_merged_assets() -> None:
    authority = module._implementation_authority(ROOT)

    assert authority.source_main_merge_commit == module.SOURCE_MAIN_MERGE_COMMIT
    assert authority.evidence_contract_feature_commit == (module.EVIDENCE_CONTRACT_FEATURE_COMMIT)
    assert authority.evidence_contract_merge_commit == (module.EVIDENCE_CONTRACT_MERGE_COMMIT)
    assert authority.terminal_closure_feature_commit == (module.TERMINAL_CLOSURE_FEATURE_COMMIT)
    assert authority.terminal_closure_merge_commit == (module.TERMINAL_CLOSURE_MERGE_COMMIT)
    assert (
        authority.original_implementation_merge_commit
        == module.ORIGINAL_IMPLEMENTATION_MERGE_COMMIT
    )
    assert authority.implementation_record.sha256 == (module.IMPLEMENTATION_RECORD_SHA256)
    assert authority.notebook.sha256 == module.IMPLEMENTATION_NOTEBOOK_SHA256
    assert authority.request.sha256 == module.IMPLEMENTATION_REQUEST_SHA256
    assert authority.architecture_review.sha256 == (module.IMPLEMENTATION_REVIEW_SHA256)
    assert authority.implementation_source.sha256 == (module.IMPLEMENTATION_SOURCE_SHA256)
    assert authority.template.sha256 == module.IMPLEMENTATION_TEMPLATE_SHA256
    assert authority.implementation_tests.sha256 == (module.IMPLEMENTATION_TESTS_SHA256)
    assert authority.adr.sha256 == module.IMPLEMENTATION_ADR_SHA256
    assert authority.report.sha256 == module.IMPLEMENTATION_REPORT_SHA256
    assert authority.runbook.sha256 == module.IMPLEMENTATION_RUNBOOK_SHA256
    assert authority.runtime_script_sha256 == (module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256)
    assert authority.wrapper_code_sha256 == (module.IMPLEMENTATION_WRAPPER_CODE_SHA256)
    assert authority.expected_runtime_outputs == module.EXPECTED_RUNTIME_OUTPUTS
    assert authority.terminal_evidence == module.TerminalEvidenceAuthority()
    assert authority.execution_budget.maximum_model_requests == 18
    assert authority.controls.expected_runtime_output_count == 16
    assert authority.runtime_execution_authorized_before_issuance is False
    assert authority.authorization_issuer_included_before_issuance is False
    assert authority.measured_abc_execution_authorized is False


@pytest.mark.skipif(
    SYNTHETIC_FIXTURE,
    reason="exact merged repository bytes unavailable in synthetic fixture",
)
def test_review_preserves_pre_execution_boundary() -> None:
    review = module._build_review(ROOT)

    assert review.status == "APPROVED_FOR_AUTHORIZATION_IMPLEMENTATION"
    assert review.decision == ("SEPARATE_TRANSIENT_SINGLE_USE_P4_DIAGNOSTIC_AUTHORIZATION")
    assert review.authorization_issued_in_review is False
    assert review.runtime_execution_performed is False
    assert review.authorization_must_remain_untracked is True
    assert review.passed_failed_or_interrupted_attempt_consumes_authorization
    assert review.budget.maximum_kaggle_sessions == 1
    assert review.budget.maximum_model_loads == 1
    assert review.budget.maximum_worker_starts == 1
    assert review.budget.maximum_model_requests == 18
    assert review.budget.maximum_output_tokens_per_request == 32
    assert review.budget.maximum_benchmark_trajectory_requests == 0
    assert review.controls.accelerator == "T4_X1"
    assert review.controls.loopback_http_permitted is True
    assert review.controls.external_network_access_permitted is False
    assert review.controls.raw_prompt_logging_permitted is False
    assert review.controls.raw_output_logging_permitted is False
    assert review.controls.explicit_backend_required == "TRITON_ATTN"
    assert review.controls.content_invalid_request_is_fatal is False
    assert review.controls.infrastructure_or_transport_failure_is_fatal is True
    assert review.controls.success_failure_report_status == "NOT_APPLICABLE"
    assert review.controls.failed_failure_report_status == "FAILED"
    assert review.controls.expected_runtime_output_count == 16
    assert review.controls.expected_pre_manifest_output_count == 14
    assert review.controls.expected_pre_archive_output_count == 15
    assert review.controls.output_contract_parity_required is True
    assert review.controls.terminal_path_output_contract_required is True
    assert review.controls.not_run_stage_reports_required is True
    assert review.controls.partial_request_evidence_required is True
    assert review.controls.partial_evidence_selection_ineligible_required is True
    assert review.controls.startup_failure_teardown_required is True
    assert review.controls.surviving_capture_threads_are_fatal is True
    assert review.controls.residual_worker_process_is_fatal is True
    assert review.controls.scratch_cleanup_failure_is_fatal is True
    assert review.controls.pre_manifest_output_completeness_gate_required is True
    assert review.controls.pre_archive_output_completeness_gate_required is True
    assert review.controls.measured_abc_execution_authorized is False


@pytest.mark.skipif(
    SYNTHETIC_FIXTURE,
    reason="exact merged repository bytes unavailable in synthetic fixture",
)
def test_review_is_deterministic() -> None:
    first = module._build_review(ROOT)
    second = module._build_review(ROOT)

    assert first.canonical_json() == second.canonical_json()
    assert first.fingerprint() == second.fingerprint()


@pytest.mark.skipif(
    SYNTHETIC_FIXTURE,
    reason="exact merged repository bytes unavailable in synthetic fixture",
)
def test_generate_validate_round_trip() -> None:
    generated = module.generate(ROOT)
    validated = module.validate_implementation_package(ROOT)

    assert generated.status == ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_EXECUTION_AUTHORIZATION_V1_VALID")
    assert validated["authorization_issuer_implemented"] is True
    assert validated["authorization_issued"] is False
    assert validated["maximum_model_requests"] == 18
    assert validated["expected_runtime_output_count"] == 16
    assert validated["terminal_path_output_contract_complete"] is True
    assert validated["terminal_closure_feature_commit"] == (module.TERMINAL_CLOSURE_FEATURE_COMMIT)


def test_confirmation_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _confirmation(confirmed_at=datetime(2026, 8, 5, 21, 0))


@pytest.mark.parametrize(
    "confirmation_factory",
    [
        lambda: _confirmation(window_minutes=241),
        lambda: _confirmation(scope="FULL_ABC_EXECUTION"),
        lambda: _confirmation(source_main_merge_commit="0" * 40),
        lambda: _confirmation(terminal_closure_feature_commit="0" * 40),
        lambda: _confirmation(notebook_sha256="0" * 64),
        lambda: _confirmation(runtime_script_sha256="0" * 64),
        lambda: _confirmation(wrapper_code_sha256="0" * 64),
        lambda: _confirmation(request_sha256="0" * 64),
        lambda: _confirmation(record_sha256="0" * 64),
        lambda: _confirmation(model_snapshot_sha256="0" * 64),
        lambda: _confirmation(backend="AUTO"),
        lambda: _confirmation(model_request_budget=17),
        lambda: _confirmation(runtime_output_count=15),
        lambda: _confirmation(
            terminal_path_output_contract_complete=False,
        ),
    ],
)
def test_confirmation_rejects_binding_drift(
    confirmation_factory: Callable[[], object],
) -> None:
    with pytest.raises(ValidationError):
        confirmation_factory()


def test_authorization_window_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceeds reviewed budget"):
        _authorization(
            expires_at=FIXED_NOW + timedelta(minutes=241),
        )


def test_build_authorization_binds_exact_budget_and_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_validate_static_package",
        lambda repo_root: object(),
    )
    monkeypatch.setattr(
        module,
        "_terminal_evidence_authority",
        lambda repo_root: module.TerminalEvidenceAuthority(),
    )
    monkeypatch.setattr(
        module,
        "_terminal_evidence_authority",
        lambda repo_root: module.TerminalEvidenceAuthority(),
    )

    authorization = module._build_authorization(
        repo_root=tmp_path,
        issuer_head="f" * 40,
        confirmation=_confirmation(window_minutes=30),
    )

    assert authorization.scope == module.AUTHORIZATION_SCOPE
    assert authorization.notebook_sha256 == module.IMPLEMENTATION_NOTEBOOK_SHA256
    assert authorization.runtime_script_sha256 == (module.IMPLEMENTATION_RUNTIME_SCRIPT_SHA256)
    assert authorization.wrapper_code_sha256 == (module.IMPLEMENTATION_WRAPPER_CODE_SHA256)
    assert authorization.request_sha256 == module.IMPLEMENTATION_REQUEST_SHA256
    assert authorization.expected_runtime_outputs == module.EXPECTED_RUNTIME_OUTPUTS
    assert authorization.terminal_evidence == module.TerminalEvidenceAuthority()
    assert authorization.terminal_closure_feature_commit == (module.TERMINAL_CLOSURE_FEATURE_COMMIT)
    assert authorization.terminal_closure_merge_commit == (module.TERMINAL_CLOSURE_MERGE_COMMIT)
    assert authorization.expires_at - authorization.issued_at == timedelta(minutes=30)
    assert authorization.budget.maximum_model_loads == 1
    assert authorization.budget.maximum_worker_starts == 1
    assert authorization.budget.maximum_model_requests == 18
    assert authorization.controls.expected_runtime_output_count == 16
    assert authorization.controls.expected_pre_manifest_output_count == 14
    assert authorization.controls.expected_pre_archive_output_count == 15
    assert authorization.controls.terminal_path_output_contract_required is True
    assert authorization.controls.partial_request_evidence_required is True
    assert authorization.controls.scratch_cleanup_failure_is_fatal is True
    assert authorization.controls.measured_abc_execution_authorized is False


def test_non_overwriting_write_preserves_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    path.write_text("existing", encoding="utf-8")

    with pytest.raises(module.P4AuthorizationError) as caught:
        module._write_non_overwriting(path, b"replacement")

    assert caught.value.error_code == "P4_AUTHORIZATION_ALREADY_EXISTS"
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
        json.dumps(
            authorization.model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(module.P4AuthorizationError) as caught:
        module._load_canonical(
            path,
            module.P4ExecutionAuthorization,
        )

    assert caught.value.error_code == ("P4_AUTHORIZATION_PAYLOAD_NOT_CANONICAL")


def _patch_lifecycle_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_require_synchronized_main",
        lambda repo_root, allow_transient: "f" * 40,
    )
    monkeypatch.setattr(
        module,
        "_require_transient_paths_untracked",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        module,
        "_require_source_authority",
        lambda repo_root: None,
    )
    monkeypatch.setattr(
        module,
        "_validate_static_package",
        lambda repo_root: object(),
    )
    monkeypatch.setattr(
        module,
        "_terminal_evidence_authority",
        lambda repo_root: module.TerminalEvidenceAuthority(),
    )


def test_verify_rejects_expired_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / module.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        _authorization().canonical_json(),
        encoding="utf-8",
    )
    _patch_lifecycle_guards(monkeypatch)

    with pytest.raises(module.P4AuthorizationError) as caught:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=121),
        )

    assert caught.value.error_code == "P4_AUTHORIZATION_EXPIRED"


def test_verify_rejects_consumed_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / module.AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text(
        _authorization().canonical_json(),
        encoding="utf-8",
    )
    consumption_path = tmp_path / module.CONSUMPTION_PATH
    consumption_path.write_text("consumed", encoding="utf-8")
    _patch_lifecycle_guards(monkeypatch)

    with pytest.raises(module.P4AuthorizationError) as caught:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW,
        )

    assert caught.value.error_code == "P4_AUTHORIZATION_ALREADY_CONSUMED"


def test_issue_verify_consume_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lifecycle_guards(monkeypatch)

    issued = module.issue_authorization(
        repo_root=tmp_path,
        confirmation=_confirmation(window_minutes=30),
    )

    assert issued["maximum_model_requests"] == 18
    assert issued["expected_runtime_output_count"] == 16
    assert issued["terminal_path_output_contract_complete"] is True
    assert issued["terminal_closure_merge_commit"] == (module.TERMINAL_CLOSURE_MERGE_COMMIT)

    verified = module.verify_authorization(
        repo_root=tmp_path,
        now=FIXED_NOW + timedelta(minutes=1),
    )

    assert verified["consumed"] is False
    assert verified["single_use"] is True

    consumed = module.consume_authorization(
        repo_root=tmp_path,
        outcome=module.ExecutionOutcome.PASSED,
        saved_version_id=123456789,
        consumed_at=FIXED_NOW + timedelta(minutes=2),
    )

    assert consumed["outcome"] == "PASSED"
    assert consumed["saved_version_id"] == 123456789
    assert consumed["authorization_reusable"] is False

    with pytest.raises(module.P4AuthorizationError) as caught:
        module.verify_authorization(
            repo_root=tmp_path,
            now=FIXED_NOW + timedelta(minutes=3),
        )

    assert caught.value.error_code == "P4_AUTHORIZATION_ALREADY_CONSUMED"


def test_static_validation_rejects_transient_authority(tmp_path: Path) -> None:
    path = tmp_path / module.AUTHORIZATION_PATH
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(module.P4AuthorizationError) as caught:
        module.validate_implementation_package(tmp_path)

    assert caught.value.error_code == "P4_TRANSIENT_AUTHORITY_PRESENT"


def test_expected_runtime_output_contract_is_exact() -> None:
    assert len(module.EXPECTED_RUNTIME_OUTPUTS) == 16
    assert "model_snapshot_report_v1.json" in module.EXPECTED_RUNTIME_OUTPUTS
    assert "wheelhouse_report_v1.json" in module.EXPECTED_RUNTIME_OUTPUTS
    assert "failure_report_v1.json" in module.EXPECTED_RUNTIME_OUTPUTS
    assert module.EXPECTED_RUNTIME_OUTPUTS[-1] == ("ag-p4-output-contract-evidence-v1.zip")


def test_terminal_evidence_authority_is_exact() -> None:
    authority = module.TerminalEvidenceAuthority()

    assert authority.canonical_output_contract is True
    assert authority.initialize_not_run_reports is True
    assert authority.partial_request_evidence is True
    assert authority.partial_selection_ineligible is True
    assert authority.startup_failure_teardown is True
    assert authority.teardown_failure_terminalized is True
    assert authority.cleanup_failure_terminalized is True
    assert authority.pre_manifest_output_completeness_gate is True
    assert authority.pre_archive_output_completeness_gate is True
    assert authority.synthetic_failure_regression is True


def _write_terminal_evidence_fixture(root: Path) -> None:
    payloads = {
        module.IMPLEMENTATION_SOURCE_PATH: "EXPECTED_RUNTIME_OUTPUTS: Final = (",
        module.IMPLEMENTATION_TEMPLATE_PATH: "\n".join(
            (
                "initialize_not_run_reports",
                "write_request_evidence",
                "INELIGIBLE_PARTIAL_EVIDENCE",
                "startup_teardown",
                "P4_OUTPUT_CONTRACT_TEARDOWN_FAILED",
                "P4_OUTPUT_CONTRACT_SCRATCH_CLEANUP_FAILED",
                "runtime output set is incomplete before manifest creation",
                "runtime output set is incomplete before archive creation",
            )
        ),
        module.IMPLEMENTATION_TESTS_PATH: (
            "test_runtime_failure_path_emits_complete_output_contract"
        ),
        module.IMPLEMENTATION_ADR_PATH: ("## Terminal-path evidence closure amendment"),
        module.IMPLEMENTATION_REPORT_PATH: "## Terminal-path closure",
        module.IMPLEMENTATION_RUNBOOK_PATH: ("## Terminal-path completeness gate"),
    }
    for relative_path, payload in payloads.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")


def test_terminal_evidence_marker_validation(tmp_path: Path) -> None:
    _write_terminal_evidence_fixture(tmp_path)

    authority = module._terminal_evidence_authority(tmp_path)

    assert authority == module.TerminalEvidenceAuthority()


def test_terminal_evidence_marker_validation_fails_closed(
    tmp_path: Path,
) -> None:
    _write_terminal_evidence_fixture(tmp_path)
    template_path = tmp_path / module.IMPLEMENTATION_TEMPLATE_PATH
    template_path.write_text(
        template_path.read_text(encoding="utf-8").replace(
            "runtime output set is incomplete before archive creation",
            "",
        ),
        encoding="utf-8",
    )

    with pytest.raises(module.P4AuthorizationError) as caught:
        module._terminal_evidence_authority(tmp_path)

    assert caught.value.error_code == "P4_AUTHORIZATION_TERMINAL_EVIDENCE_DRIFT"
    assert "pre_archive_output_completeness_gate" in caught.value.details


def test_source_authority_requires_complete_lineage(
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
        module.ORIGINAL_IMPLEMENTATION_MERGE_COMMIT,
        module.EVIDENCE_CONTRACT_FEATURE_COMMIT,
        module.EVIDENCE_CONTRACT_MERGE_COMMIT,
        module.TERMINAL_CLOSURE_FEATURE_COMMIT,
        module.TERMINAL_CLOSURE_MERGE_COMMIT,
    ]


def test_transient_paths_are_outside_static_candidate() -> None:
    static_paths = {
        module.ISSUER_SOURCE_PATH,
        module.ISSUER_TEST_PATH,
        module.ADR_PATH,
        module.REPORT_PATH,
        module.RUNBOOK_PATH,
        module.REVIEW_PATH,
        module.RECORD_PATH,
    }

    assert module.AUTHORIZATION_PATH not in static_paths
    assert module.CONSUMPTION_PATH not in static_paths
