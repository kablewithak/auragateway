from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

from auragateway.local_abc import (
    p4_output_contract_diagnostic_execution_acceptance_v1 as subject,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_runtime(name: str) -> dict[str, Any]:
    policy = subject._load_policy(repo_root())
    path = repo_root() / subject._runtime_target(policy, name)
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_governed_evidence_validates() -> None:
    observed = subject.validate_evidence(repo_root())
    assert observed["status"] == ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_EVIDENCE_VALID")
    assert observed["saved_version_id"] == 340775383
    assert observed["lifecycle_outcome"] == "PASSED"
    assert observed["selected_case_id"] == "A"
    assert observed["model_requests"] == 18


def test_execution_is_closed_and_not_replayable() -> None:
    observed = subject.validate_evidence(repo_root())
    assert observed["authorization_reusable"] is False
    assert observed["runtime_execution_authorized"] is False
    assert observed["measured_abc_execution_established"] is False
    assert observed["measured_abc_execution_authorized"] is False


def test_selection_is_exact_and_least_constraining() -> None:
    selection = load_runtime("selection_report_v2.json")
    assert selection["status"] == "SELECTED"
    assert selection["selected_case_id"] == "A"
    assert selection["eligible_case_ids"] == ["A", "C", "E", "F"]
    assert "least constraining" in str(selection["selection_rule"])


def test_case_metrics_preserve_diagnostic_separation() -> None:
    metrics = load_runtime("case_metrics_v2.json")
    cases = {item["case_id"]: item for item in metrics["cases"]}
    for case_id in ("A", "C", "E", "F"):
        assert cases[case_id]["exact_object_count"] == 3
        assert cases[case_id]["valid_json_count"] == 3
        assert cases[case_id]["request_error_count"] == 0
    for case_id in ("B", "D"):
        assert cases[case_id]["exact_object_count"] == 0
        assert cases[case_id]["valid_json_count"] == 0
        assert cases[case_id]["failure_category_distribution"] == {
            "REQUEST_COMPLETED_OUTPUT_INVALID_JSON": 3
        }


def test_request_order_and_privacy_controls_are_exact() -> None:
    results = load_runtime("request_results_v2.json")
    assert results["scheduled_request_count"] == 18
    assert results["observed_request_count"] == 18
    observed = tuple(item["case_id"] for item in results["results"])
    assert observed == subject.REQUEST_ORDER
    assert all(item["raw_prompt_retained"] is False for item in results["results"])
    assert all(item["raw_output_retained"] is False for item in results["results"])


def test_b_and_d_are_markdown_fenced_invalid_json() -> None:
    results = load_runtime("request_results_v2.json")
    failures = [item for item in results["results"] if item["case_id"] in {"B", "D"}]
    assert len(failures) == 6
    assert all(item["markdown_fence_detected"] is True for item in failures)
    assert all(
        item["failure_category"] == "REQUEST_COMPLETED_OUTPUT_INVALID_JSON" for item in failures
    )


def test_summary_has_no_divergence_and_exact_budget() -> None:
    summary = load_runtime("p4_output_contract_diagnostic_summary_v2.json")
    assert summary["status"] == "PASSED"
    assert summary["first_divergence"] is None
    assert summary["reported_failure_code"] is None
    assert summary["selected_case_id"] == "A"
    assert summary["counters"] == {
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
        "hidden_retries": 0,
        "kaggle_sessions": 1,
        "model_loads": 1,
        "model_requests": 18,
        "network_requests": 0,
        "runtime_import_closure_probes": 1,
        "runtime_install_attempts": 1,
        "worker_starts": 1,
    }


def test_runtime_source_and_model_identity_are_exact() -> None:
    source = load_runtime("runtime_source_identity_report_v2.json")
    model = load_runtime("model_snapshot_report_v2.json")
    assert source["executed_runtime_script_sha256"] == (
        "bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"
    )
    assert model["governed_model_snapshot_sha256"] == (
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    )


def test_runtime_install_and_import_closure_passed_offline() -> None:
    install = load_runtime("runtime_install_report_v2.json")
    closure = load_runtime("runtime_import_closure_report_v2.json")
    assert install["status"] == "PASSED"
    assert install["network_access_requested"] is False
    assert install["raw_install_output_retained"] is False
    assert closure["status"] == "PASSED"
    assert closure["decision"] == "NATIVE_HARDENED_IMPORT_CLOSURE_PASSED"
    assert closure["network_access_requested"] is False


def test_governed_native_origins_pass_without_overclaiming() -> None:
    origin = load_runtime("runtime_native_origin_report_v2.json")
    assert origin["status"] == "PASSED"
    assert origin["prohibited_origin_count"] == 0
    required = origin["required_target_origins"]
    assert required["libcusparse"] == {
        "all_from_target": True,
        "observed": True,
    }
    assert required["libnvJitLink"] == {
        "all_from_target": True,
        "observed": True,
    }
    ambient = [
        item
        for item in origin["observations"]
        if item["classification"] == "HOST_OR_AMBIENT_LIBRARY"
    ]
    assert any(item["library_name"].startswith("libcudart") for item in ambient)


def test_worker_realized_triton_backend_and_privacy_controls() -> None:
    startup = load_runtime("worker_startup_report_v2.json")
    assert startup["status"] == "PASSED"
    assert "TRITON_ATTN" in startup["backend_marker"]
    assert startup["gpu_index"] == 0
    assert startup["request_logging_disabled"] is True
    assert startup["raw_worker_logs_retained"] is False
    assert startup["environment"]["prohibited_stub_path_present"] is False


def test_teardown_and_cleanup_are_complete() -> None:
    teardown = load_runtime("worker_teardown_report_v2.json")
    cleanup = load_runtime("scratch_cleanup_report_v2.json")
    assert teardown["status"] == "PASSED"
    assert teardown["process_absent"] is True
    assert teardown["port_closed"] is True
    assert teardown["capture_threads_finalized"] is True
    assert teardown["surviving_descendant_pids"] == []
    assert cleanup["status"] == "PASSED"
    assert cleanup["scratch_absent"] is True


def test_failure_report_is_not_applicable() -> None:
    failure = load_runtime("failure_report_v2.json")
    assert failure == {
        "error_code": None,
        "schema_version": "1.0.0",
        "status": "NOT_APPLICABLE",
    }


def test_bundle_manifest_excludes_raw_output() -> None:
    manifest = load_runtime("bundle_manifest_v2.json")
    assert manifest["member_count"] == 15
    assert manifest["raw_output_included"] is False


def test_authorization_consumption_is_bound_to_pass_evidence() -> None:
    policy = subject._load_policy(repo_root())
    auth_path = repo_root() / subject._evidence_path(
        policy,
        "execution_authorization_v3-340775383.json",
    )
    consumption_path = repo_root() / subject._evidence_path(
        policy,
        "execution_authorization_consumption_v3-340775383.json",
    )
    authorization = json.loads(auth_path.read_text(encoding="utf-8"))
    consumption = json.loads(consumption_path.read_text(encoding="utf-8"))
    assert authorization["lifecycle"] == "ISSUED"
    assert authorization["single_use"] is True
    assert authorization["measured_abc_execution_authorized"] is False
    assert consumption["lifecycle"] == "CONSUMED"
    assert consumption["outcome"] == "PASSED"
    assert consumption["saved_version_id"] == 340775383
    assert consumption["authorization_reusable"] is False


def test_intake_archive_and_nested_evidence_validate() -> None:
    policy = subject._load_policy(repo_root())
    members = subject._validate_intake_archive(repo_root(), policy)
    subject._validate_intake_manifest(repo_root(), policy, members)
    subject._validate_runtime_evidence_zip(repo_root(), policy)


def test_live_lifecycle_paths_are_absent() -> None:
    policy = subject._load_policy(repo_root())
    for relative in policy.operational_transient_paths:
        assert not (repo_root() / relative).exists()


def test_unsafe_zip_path_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../escape.json", "{}")
    with pytest.raises(subject.AcceptanceError) as error:
        subject._safe_zip_members(path)
    assert error.value.error_code == "P4_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE"


def test_duplicate_normalized_zip_member_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("a/b.json", "{}")
        archive.writestr("a\\b.json", "{}")
    with pytest.raises(subject.AcceptanceError) as error:
        subject._safe_zip_members(path)
    assert error.value.error_code == "P4_EXECUTION_ACCEPTANCE_ARCHIVE_DUPLICATE"


def test_zip_symlink_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, "target")
    with pytest.raises(subject.AcceptanceError) as error:
        subject._safe_zip_members(path)
    assert error.value.error_code == "P4_EXECUTION_ACCEPTANCE_ARCHIVE_UNSAFE"


def test_generate_is_deterministic() -> None:
    root = repo_root()
    subject.generate(root)
    review_before = (root / subject.REVIEW_PATH).read_bytes()
    record_before = (root / subject.RECORD_PATH).read_bytes()
    subject.generate(root)
    assert (root / subject.REVIEW_PATH).read_bytes() == review_before
    assert (root / subject.RECORD_PATH).read_bytes() == record_before


def test_package_validates_and_next_gate_is_non_execution() -> None:
    observed = subject.validate_package(repo_root())
    assert observed["status"] == ("P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2_EXECUTION_ACCEPTANCE_V1_VALID")
    assert observed["p4_output_contract_diagnostic_established"] is True
    assert observed["runtime_execution_authorized"] is False
    assert observed["measured_abc_execution_authorized"] is False
    assert observed["next_gate"] == ("design_and_merge_measured_abc_execution_authorization_v1")
