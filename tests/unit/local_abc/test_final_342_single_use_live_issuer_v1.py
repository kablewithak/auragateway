"""Focused tests for G11.14C final-342 live orchestration reliability."""

from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import final_342_single_use_live_issuer_v1 as subject

ROOT = Path(__file__).resolve().parents[3]


def _record() -> subject.QualificationRecord:
    return subject.QualificationRecord.model_validate_json(
        (ROOT / subject.QUALIFICATION_RECORD_PATH).read_bytes()
    )


def test_qualification_is_non_issuing_and_non_executing() -> None:
    record = _record()

    assert record.status == "QUALIFIED_NOT_ISSUED"
    assert record.qualification_boundary.qualification_may_issue_live_authority is False
    assert record.qualification_boundary.governed_execution_permitted_during_qualification is False
    assert record.safety_state.model_requests_performed == 0
    assert record.safety_state.gpu_execution_performed is False
    assert record.safety_state.network_transport_performed is False
    assert record.safety_state.live_authorization_issued is False
    assert record.safety_state.final_measured_abc_execution_authorized is False


def test_qualification_closes_exact_transaction_bound_execution_seam() -> None:
    record = _record()

    boundary = record.qualification_boundary
    assert boundary.exact_static_authority_required is True
    assert boundary.exact_frozen_manifest_required is True
    assert boundary.exact_final_producer_required is True
    assert boundary.exact_frozen_context_contract_required is True
    assert boundary.canonical_hmac_prefix_contract_required is True
    assert boundary.protected_review_capture_required is True
    assert boundary.transaction_bound_execution_artifact_required is True
    assert boundary.repository_pythonpath_required_at_execution is False
    assert record.planned_trajectory_count == 342
    assert record.planned_turn_count == 1368
    assert record.maximum_request_attempt_count == 2736
    assert record.notebook_container_encoding == "zlib-level-9+base64"
    assert record.notebook_container_reconstructs_exact_wrapper_bytes is True
    assert (
        record.qualification_notebook_launcher_source_bytes
        < subject.KAGGLE_NOTEBOOK_SOURCE_BUDGET_BYTES
    )


def test_single_use_governance_does_not_claim_runtime_anti_replay() -> None:
    boundary = _record().qualification_boundary

    assert boundary.single_use_is_governance_invariant is True
    assert boundary.authorization_reusable is False
    assert boundary.runtime_anti_replay_established is False
    assert boundary.fresh_platform_readiness_required_after_qualification is True
    assert boundary.fresh_human_authority_required_after_qualification is True


def test_qualification_record_reconstructs_deterministically() -> None:
    result = subject.validate_qualification(ROOT)

    assert result["status"] == ("FINAL_342_SINGLE_USE_LIVE_ISSUER_V1_QUALIFIED_NOT_ISSUED")
    assert result["canonical_hmac_prefix_contract_bound"] is True
    assert result["protected_review_capture_bound"] is True
    assert result["repository_pythonpath_required_at_execution"] is False
    assert result["live_authorization_issued"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["next_gate"] == "FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY"


def test_live_authorization_contract_is_single_use() -> None:
    fields = subject.LiveAuthorization.model_fields

    assert "single_use" in fields
    assert "authorization_reusable" in fields
    assert "runtime_anti_replay_established" in fields
    assert "prefix_hmac_key_sha256" in fields
    assert "transaction_material_sha256" in fields


def test_compressed_notebook_container_executes_exact_wrapper_with_normalized_argv(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "wrapper-executed.json"
    wrapper = (
        "from __future__ import annotations\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(json.dumps(sys.argv), encoding='utf-8')\n"
    ).encode()
    notebook_path = tmp_path / f"{subject.NOTEBOOK_NAME}.ipynb"

    notebook_bytes = subject._write_notebook(notebook_path, wrapper)
    payload = json.loads(notebook_bytes)
    source = "".join(payload["cells"][0]["source"])
    original_argv = sys.argv[:]

    exec(compile(source, "generated_notebook_cell.py", "exec"), {"__name__": "__main__"})

    assert sys.argv == original_argv
    assert json.loads(marker.read_text(encoding="utf-8")) == [f"{subject.NOTEBOOK_NAME}.py"]
    assert notebook_path.read_bytes() == notebook_bytes
    assert payload["nbformat"] == 4
    assert payload["nbformat_minor"] == 5
    assert len(payload["cells"]) == 1
    assert payload["cells"][0]["cell_type"] == "code"
    assert source.encode("utf-8") != wrapper
    assert len(source.encode("utf-8")) < subject.KAGGLE_NOTEBOOK_SOURCE_BUDGET_BYTES
    assert (
        payload["metadata"]["auragateway"]["semantic_wrapper_sha256"]
        == hashlib.sha256(wrapper).hexdigest()
    )
    assert payload["metadata"]["auragateway"]["notebook_container_encoding"] == (
        "zlib-level-9+base64"
    )
    assert (
        payload["metadata"]["auragateway"]["notebook_container_is_semantic_payload_identity"]
        is False
    )
    assert (
        payload["metadata"]["auragateway"]["semantic_execution_identity"] == "python_wrapper_bytes"
    )


def test_compressed_notebook_container_keeps_large_source_under_budget(
    tmp_path: Path,
) -> None:
    wrapper = b"print('final-342-governed')\n" * 60_000
    assert len(wrapper) > 1_000_000

    notebook_path = tmp_path / f"{subject.NOTEBOOK_NAME}.ipynb"
    notebook_bytes = subject._write_notebook(notebook_path, wrapper)
    payload = json.loads(notebook_bytes)
    source = "".join(payload["cells"][0]["source"])

    assert len(source.encode("utf-8")) < subject.KAGGLE_NOTEBOOK_SOURCE_BUDGET_BYTES
    assert payload["metadata"]["auragateway"]["launcher_source_bytes"] == len(
        source.encode("utf-8")
    )


def test_compressed_notebook_container_fails_closed_over_source_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "KAGGLE_NOTEBOOK_SOURCE_BUDGET_BYTES", 128)

    with pytest.raises(subject.IssuerError) as error:
        subject._notebook_launcher_source(b"print('final-342')\n")

    assert error.value.error_code == "FINAL_342_ISSUER_KAGGLE_SOURCE_BUDGET_EXCEEDED"


@pytest.fixture(scope="module")
def rendered_live_wrapper_namespace() -> dict[str, Any]:
    material = subject.build_transaction_material(ROOT)
    wrapper = subject._qualification_wrapper(ROOT, material)
    namespace: dict[str, Any] = {
        "__name__": "auragateway_g1114c_live_seam_test",
        "__file__": "<auragateway-g1114c-live-seam-test>",
    }
    exec(
        compile(
            wrapper,
            "<auragateway-g1114c-rendered-wrapper>",
            "exec",
        ),
        namespace,
        namespace,
    )
    return namespace


def test_live_workspace_initialization_owns_output_root_before_store_persist(
    tmp_path: Path,
    rendered_live_wrapper_namespace: dict[str, Any],
) -> None:
    namespace = rendered_live_wrapper_namespace
    output_root = tmp_path / "final_342_transaction_bound_v1"
    producer_store_root = output_root / "producer_state"
    consumption_path = output_root / "authorization_consumption_v1.json"
    transaction_id = "a" * 64
    persisted_state = object()

    namespace["_OUTPUT_ROOT"] = output_root
    namespace["_PRODUCER_STORE_ROOT"] = producer_store_root
    namespace["_AUTHORIZATION_CONSUMPTION_PATH"] = consumption_path

    class FakeMonotonicEvidenceStore:
        def __init__(self, root: Path) -> None:
            self.root = Path(root)

        def persist(self, state: object) -> None:
            assert state is persisted_state
            assert output_root.is_dir()
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / "producer_state_v1.json").write_text(
                "persisted\n",
                encoding="utf-8",
            )

    fake_producer = types.ModuleType("auragateway_g1114c_fake_producer")
    fake_producer.__dict__["MonotonicEvidenceStore"] = FakeMonotonicEvidenceStore

    store = namespace["_initialize_transaction_workspace"](
        fake_producer,
        persisted_state,
        transaction_id,
    )

    assert isinstance(store, FakeMonotonicEvidenceStore)
    assert output_root.is_dir()
    assert (producer_store_root / "producer_state_v1.json").read_text(
        encoding="utf-8"
    ) == "persisted\n"

    consumption = json.loads(consumption_path.read_text(encoding="utf-8"))
    assert consumption["transaction_id"] == transaction_id
    assert consumption["disposition"] == "EXECUTION_STARTED_SINGLE_USE_GOVERNANCE"
    assert consumption["authorization_reusable"] is False
    assert consumption["runtime_anti_replay_established"] is False


@pytest.mark.parametrize("exit_code", [None, 0])
def test_compressed_notebook_launcher_treats_zero_exit_as_success(
    exit_code: int | None,
) -> None:
    wrapper = f"raise SystemExit({exit_code!r})\n".encode()
    source = subject._notebook_launcher_source(wrapper)
    original_argv = sys.argv[:]

    exec(
        compile(
            source,
            "<auragateway-g1114c-zero-exit-launcher>",
            "exec",
        ),
        {"__name__": "__main__"},
    )

    assert sys.argv == original_argv


def test_compressed_notebook_launcher_propagates_nonzero_exit() -> None:
    wrapper = b"raise SystemExit(3)\n"
    source = subject._notebook_launcher_source(wrapper)
    original_argv = sys.argv[:]

    with pytest.raises(SystemExit) as error:
        exec(
            compile(
                source,
                "<auragateway-g1114c-nonzero-exit-launcher>",
                "exec",
            ),
            {"__name__": "__main__"},
        )

    assert error.value.code == 3
    assert sys.argv == original_argv


def test_live_terminal_failure_precedence_preserves_primary_failure(
    rendered_live_wrapper_namespace: dict[str, Any],
) -> None:
    raise_terminal_failure = rendered_live_wrapper_namespace["_raise_terminal_failure"]
    primary = RuntimeError("primary execution failure")
    bundle = RuntimeError("evidence bundle failure")

    with pytest.raises(RuntimeError) as error:
        raise_terminal_failure(primary, bundle)

    assert error.value is primary

    with pytest.raises(RuntimeError) as bundle_only_error:
        raise_terminal_failure(None, bundle)

    assert bundle_only_error.value is bundle


def test_live_teardown_adapter_maps_actual_p5_p6_report_schema(
    rendered_live_wrapper_namespace: dict[str, Any],
) -> None:
    namespace = rendered_live_wrapper_namespace
    template = (ROOT / subject.TEMPLATE_PATH).read_text(encoding="utf-8")

    assert "_teardown_workers_view(workers)" in template

    adapter_type = namespace["_TeardownReportAdapter"]

    class ActualP5P6RuntimeWorker:
        worker_id = "worker-1"
        generation = 7

        def stop_and_report(self, reason: str) -> dict[str, object]:
            assert reason == "final-342-transaction-terminalization"
            return {
                "schema_version": "1.0.0",
                "worker_id": self.worker_id,
                "generation": self.generation,
                "reason": reason,
                "status": "PASSED",
                "process_tree_absent_after": True,
                "gpu_processes_absent_after": True,
                "port_closed_after": True,
                "memory_returned_within_tolerance": True,
            }

    adapter = adapter_type(ActualP5P6RuntimeWorker())

    report = adapter.stop_and_report("final-342-transaction-terminalization")

    assert adapter.worker_id == "worker-1"
    assert adapter.generation == 7
    assert report["status"] == "PASSED"
    assert report["process_tree_absent"] is True
    assert report["gpu_processes_absent"] is True
    assert report["port_closed"] is True
    assert report["memory_returned"] is True

    assert report["process_tree_absent_after"] is True
    assert report["gpu_processes_absent_after"] is True
    assert report["port_closed_after"] is True
    assert report["memory_returned_within_tolerance"] is True
