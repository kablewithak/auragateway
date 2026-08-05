from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import p4_output_contract_diagnostic_v1 as diagnostic

ROOT = Path(__file__).resolve().parents[3]


def test_notebook_names_fit_kaggle_limit() -> None:
    assert len(diagnostic.NOTEBOOK_NAME) <= 50
    assert len(diagnostic.FAILED_NOTEBOOK_NAME) <= 50


def test_case_matrix_is_exact() -> None:
    cases = diagnostic.diagnostic_cases()
    assert tuple(item.case_id for item in cases) == ("A", "B", "C", "D", "E", "F")
    assert [(item.prompt_variant, item.repetition_penalty, item.output_mode) for item in cases] == [
        ("V4", 1.1, "UNCONSTRAINED"),
        ("V5", 1.1, "UNCONSTRAINED"),
        ("V4", 1.0, "UNCONSTRAINED"),
        ("V5", 1.0, "UNCONSTRAINED"),
        ("V4", 1.0, "JSON_SCHEMA"),
        ("V5", 1.0, "JSON_SCHEMA"),
    ]


def test_request_order_is_balanced() -> None:
    order = diagnostic.request_order()

    assert len(order) == 18
    assert order[:6] == (
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
    )
    assert order[6:12] == (
        "F",
        "E",
        "D",
        "C",
        "B",
        "A",
    )
    assert order[12:] == (
        "C",
        "D",
        "E",
        "F",
        "A",
        "B",
    )

    for case_id in (
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
    ):
        assert order.count(case_id) == 3


def test_execution_budget_is_bounded() -> None:
    budget = diagnostic.ExecutionBudget()
    assert budget.maximum_model_requests == 18
    assert budget.maximum_model_loads == 1
    assert budget.maximum_worker_starts == 1
    assert budget.hidden_retries_permitted == 0
    assert budget.benchmark_trajectory_requests_permitted == 0


def test_evidence_contract_excludes_raw_content() -> None:
    contract = diagnostic.EvidenceContract()
    assert contract.raw_prompt_retained is False
    assert contract.raw_output_retained is False
    assert contract.response_sha256_required is True
    assert contract.json_error_coordinates_required is True


def test_template_has_schema_only_for_e_and_f() -> None:
    text = (ROOT / diagnostic.TEMPLATE_PATH).read_text(encoding="utf-8")
    assert '"E": {"prompt_variant": "V4", "repetition_penalty": 1.0, "schema": True}' in text
    assert '"F": {"prompt_variant": "V5", "repetition_penalty": 1.0, "schema": True}' in text
    assert 'payload["response_format"]' in text
    assert '"repetition_penalty": case["repetition_penalty"]' in text


def test_template_does_not_log_raw_content() -> None:
    text = (ROOT / diagnostic.TEMPLATE_PATH).read_text(encoding="utf-8")
    assert '"raw_prompt_retained": False' in text
    assert '"raw_output_retained": False' in text
    assert "response_sha256" in text
    assert "response_length" in text


def test_request_contract_has_no_authority() -> None:
    authorities = _synthetic_authorities()
    request = diagnostic._request(authorities)
    assert request.runtime_execution_authorized is False
    assert request.authorization_issuer_included is False
    assert request.measured_abc_execution_authorized is False


def test_review_selects_separate_authorization_gate() -> None:
    review = diagnostic._review()
    assert review.next_gate == "implement_and_merge_p4_output_contract_diagnostic_v1"
    assert review.runtime_execution_authorized is False
    assert review.authorization_issuer_included is False


def test_notebook_is_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fixture_repo(
        tmp_path,
        monkeypatch,
    )

    first = diagnostic.build_generated(root)
    second = diagnostic.build_generated(root)

    assert first.notebook_bytes == second.notebook_bytes
    assert first.runtime_script_sha256 == second.runtime_script_sha256

    payload = json.loads(first.notebook_bytes)

    assert isinstance(payload, dict)

    cells = payload["cells"]

    assert isinstance(cells, list)

    code_cells = [
        item for item in cells if isinstance(item, dict) and item.get("cell_type") == "code"
    ]

    assert len(code_cells) == 1
    assert code_cells[0]["execution_count"] is None
    assert code_cells[0]["outputs"] == []


def test_generate_validate_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    generated = diagnostic.generate(root)
    validated = diagnostic.validate(root)
    assert generated.record == validated.record
    assert generated.record.status == "IMPLEMENTED_NOT_EXECUTED"
    assert generated.record.safety.model_requests_performed == 0
    assert generated.record.next_gate == (
        "merge_then_design_separate_p4_output_contract_execution_authorization_v1"
    )


def test_authority_drift_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_repo(tmp_path, monkeypatch)
    path = root / diagnostic.FAILURE_ACCEPTANCE_RECORD_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    payload["failed_probe"] = "P6"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(diagnostic.P4OutputContractImplementationError):
        diagnostic.build_generated(root)


def _synthetic_authorities() -> tuple[
    diagnostic.AcceptedAuthority,
    diagnostic.AcceptedAuthority,
    diagnostic.AcceptedAuthority,
]:
    return (
        diagnostic.AcceptedAuthority(
            authority_id="v5_failure_acceptance_record",
            path=diagnostic.FAILURE_ACCEPTANCE_RECORD_PATH.as_posix(),
            sha256="0" * 64,
            size_bytes=1,
            source_commit=diagnostic.SOURCE_MAIN_COMMIT,
            status="P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V5_VALID",
            next_gate="design_and_merge_p4_output_contract_diagnostic_v1",
        ),
        diagnostic.AcceptedAuthority(
            authority_id="v5_failure_acceptance_review",
            path=diagnostic.FAILURE_ACCEPTANCE_REVIEW_PATH.as_posix(),
            sha256="0" * 64,
            size_bytes=1,
            source_commit=diagnostic.SOURCE_MAIN_COMMIT,
            status="P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5_CLASSIFIED",
            next_gate="design_and_merge_p4_output_contract_diagnostic_v1",
        ),
        diagnostic.AcceptedAuthority(
            authority_id="v5_implementation_record",
            path=diagnostic.V5_IMPLEMENTATION_RECORD_PATH.as_posix(),
            sha256="0" * 64,
            size_bytes=1,
            source_commit=diagnostic.SOURCE_MAIN_COMMIT,
            status="IMPLEMENTED_NOT_EXECUTED",
            next_gate="merge_then_design_separate_p3_p6_execution_authorization_v5",
        ),
    )


def _fixture_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    destination = tmp_path / "repo"
    destination.mkdir()
    for relative in diagnostic.STATIC_PATHS:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    authorities: dict[Path, dict[str, object]] = {
        diagnostic.FAILURE_ACCEPTANCE_RECORD_PATH: {
            "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_ACCEPTANCE_V5_VALID",
            "next_gate": "design_and_merge_p4_output_contract_diagnostic_v1",
            "failed_probe": "P4",
            "first_divergence": "P4_MODEL_RESPONSE_NOT_VALID_JSON",
            "unchanged_replay_authorized": False,
        },
        diagnostic.FAILURE_ACCEPTANCE_REVIEW_PATH: {
            "status": "P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5_CLASSIFIED",
            "next_gate": "design_and_merge_p4_output_contract_diagnostic_v1",
            "evidence_disposition": "ACCEPTED_DIAGNOSTIC_FAILURE",
        },
        diagnostic.V5_IMPLEMENTATION_RECORD_PATH: {
            "status": "IMPLEMENTED_NOT_EXECUTED",
            "next_gate": "merge_then_design_separate_p3_p6_execution_authorization_v5",
            "record_id": "auragateway-cu129-p3-p6-runtime-diagnostic-v5-implementation",
        },
    }
    for relative, payload in authorities.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AURAGATEWAY_SYNTHETIC_FIXTURE", "1")
    return destination


def test_repetition_penalty_rejects_unsupported_value() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"repetition_penalty must be exactly "
            r"1\.0 or 1\.1"
        ),
    ):
        diagnostic.DiagnosticCase(
            case_id="A",
            prompt_variant="V4",
            repetition_penalty=1.05,
            output_mode="UNCONSTRAINED",
        )


def test_runtime_output_contract_is_canonical() -> None:
    assert (diagnostic._review().output_contract) == diagnostic.EXPECTED_RUNTIME_OUTPUTS
    assert len(diagnostic.EXPECTED_RUNTIME_OUTPUTS) == 16

    text = (ROOT / diagnostic.TEMPLATE_PATH).read_text(
        encoding="utf-8",
    )

    assert "__EXPECTED_RUNTIME_OUTPUTS_JSON__" in text


def test_failure_report_is_emitted_for_success_and_failure() -> None:
    text = (ROOT / diagnostic.TEMPLATE_PATH).read_text(
        encoding="utf-8",
    )

    assert '"status": "NOT_APPLICABLE"' in text
    assert '"status": "FAILED"' in text
    assert "failure_report = dict(terminal_error)" in text
    assert 'write_json("failure_report_v1.json", failure_report)' in text


def _runtime_namespace(tmp_path: Path) -> dict[str, Any]:
    source = diagnostic._template_bytes(ROOT).decode("utf-8")
    namespace: dict[str, Any] = {"__name__": "p4_runtime_test"}
    exec(
        compile(source, "<p4-runtime-test>", "exec"),
        namespace,
        namespace,
    )
    output_root = tmp_path / "output"
    scratch_root = output_root / "scratch"
    namespace["OUTPUT_ROOT"] = output_root
    namespace["SCRATCH_ROOT"] = scratch_root
    namespace["TARGET_SITE"] = scratch_root / "target_site"
    return namespace


def test_runtime_failure_path_emits_complete_output_contract(
    tmp_path: Path,
) -> None:
    namespace = _runtime_namespace(tmp_path)

    def fail_discovery() -> tuple[Path, Path]:
        raise RuntimeError("synthetic input discovery failure")

    namespace["discover_inputs"] = fail_discovery
    exit_code = namespace["main"]()

    assert exit_code == 2
    output_root = namespace["OUTPUT_ROOT"]
    observed = {path.name for path in output_root.iterdir() if path.is_file()}
    assert observed == set(diagnostic.EXPECTED_RUNTIME_OUTPUTS)

    failure_report = json.loads(
        (output_root / "failure_report_v1.json").read_text(
            encoding="utf-8",
        )
    )
    assert failure_report["status"] == "FAILED"
    assert failure_report["stage"] == "input_discovery"

    manifest = json.loads(
        (output_root / "bundle_manifest_v1.json").read_text(
            encoding="utf-8",
        )
    )
    assert manifest["member_count"] == 14
    assert {item["path"] for item in manifest["members"]} == (
        set(diagnostic.EXPECTED_RUNTIME_OUTPUTS)
        - {
            "bundle_manifest_v1.json",
            diagnostic.EVIDENCE_ZIP_NAME,
        }
    )


def test_runtime_teardown_reports_surviving_capture_thread_as_failure(
    tmp_path: Path,
) -> None:
    namespace = _runtime_namespace(tmp_path)

    class SurvivingThread:
        def join(self, timeout: int) -> None:
            assert timeout == 10

        def is_alive(self) -> bool:
            return True

    report = namespace["teardown"](
        None,
        [SurvivingThread()],
    )

    assert report["status"] == "FAILED"
    assert report["capture_threads_finalized"] is False
    assert report["process_absent"] is True


def test_runtime_bundle_rejects_incomplete_output_set(
    tmp_path: Path,
) -> None:
    namespace = _runtime_namespace(tmp_path)
    output_root = namespace["OUTPUT_ROOT"]
    output_root.mkdir(parents=True)
    (output_root / "failure_report_v1.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="incomplete before manifest",
    ):
        namespace["build_bundle"]()
