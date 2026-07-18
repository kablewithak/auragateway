from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.full_abc_local_environment_qualification_execution import (
    build_execution_request,
    build_notebook_payload,
    execute_qualification,
    generate_static_package,
    synthetic_probe_payload,
    verify_static_package,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts import (
    EXECUTION_REQUEST_PATH,
    EXPECTED_RUFF_VERSION,
    NEXT_GATE,
    NOTEBOOK_PATH,
    REQUIRED_METRIC_SEMANTICS,
    REQUIRED_RESET_STEPS,
    RUNBOOK_PATH,
    RUNTIME_EVIDENCE_PATHS,
    SYNTHETIC_PROBE_IDS,
    AuthorizationDecision,
    CacheMetricCapabilityReport,
    DatasetManifestEntry,
    GpuDeviceObservation,
    GpuTopologyReport,
    KaggleRuntimeDependencyLock,
    MetricAvailabilityState,
    MetricCapabilityObservation,
    ModelIdentityReport,
    ProbeObservation,
    QualificationDatasetManifest,
    QualificationDecision,
    QualificationExecutionAuthorization,
    QualificationExecutionRequest,
    QualificationReport,
    QualificationRuntimeAdapter,
    QualificationRuntimeCapture,
    QualificationRuntimeFactoryBinding,
    ResetCapabilityReport,
    ResetStepObservation,
    WorkerHealthObservation,
    WorkerHealthReport,
)

_FIXED_NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_SHA_D = "d" * 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dataset_manifest(tmp_path: Path) -> QualificationDatasetManifest:
    entries: list[DatasetManifestEntry] = []
    for role, name in (
        ("harness_source", "harness"),
        ("model_artifacts", "model"),
        ("vllm_wheel", "wheel.whl"),
    ):
        mounted = tmp_path / name
        mounted.write_text(role, encoding="utf-8")
        entries.append(
            DatasetManifestEntry(
                role=cast(Literal["harness_source", "model_artifacts", "vllm_wheel"], role),
                mounted_path=str(mounted.resolve()),
                sha256=_sha256(mounted),
            )
        )
    return QualificationDatasetManifest(
        manifest_id="qualification-dataset-v1",
        entries=(entries[0], entries[1], entries[2]),
    )


def _authorization(
    tmp_path: Path,
    request: QualificationExecutionRequest,
    dataset_manifest: QualificationDatasetManifest,
) -> QualificationExecutionAuthorization:
    adapter_path = tmp_path / "runtime_adapter.py"
    adapter_path.write_text(
        "def build_runtime():\n    raise RuntimeError('test-only')\n", encoding="utf-8"
    )
    return QualificationExecutionAuthorization(
        authorization_id="qualification-execution-authorization-v1",
        decision=AuthorizationDecision.AUTHORIZED,
        request_sha256=request.fingerprint(),
        review_git_blob_sha="0b5fe5dc497080974b27e0720d0fab51baa77851",
        dataset_manifest_sha256=dataset_manifest.fingerprint(),
        runtime_factory=QualificationRuntimeFactoryBinding(
            factory_path="runtime_adapter:build_runtime",
            artifact_path=str(adapter_path.resolve()),
            artifact_sha256=_sha256(adapter_path),
        ),
        issued_at=_FIXED_NOW - timedelta(minutes=5),
        expires_at=_FIXED_NOW + timedelta(minutes=30),
    )


def _capture(
    request: QualificationExecutionRequest,
    dataset_manifest: QualificationDatasetManifest,
) -> QualificationRuntimeCapture:
    common = {
        "runtime_session_id": "qualification-session-v1",
        "captured_at": _FIXED_NOW,
        "source_request_sha256": request.fingerprint(),
        "dataset_manifest_sha256": dataset_manifest.fingerprint(),
    }
    dependency_lock = KaggleRuntimeDependencyLock.model_validate(
        {
            "evidence_id": "kaggle-runtime-dependency-lock",
            **common,
            "python_version": "3.11.9",
            "torch_version": "2.11.0+cu129",
            "cuda_version": "12.9",
            "transformers_version": "4.57.1",
            "vllm_module_version": "0.25.1",
            "vllm_distribution_version": "0.25.1+cu129",
            "vllm_wheel_sha256": _SHA_D,
            "attention_backend": "flashinfer",
            "automatic_prefix_cache_configuration": "enabled",
            "dtype": "auto",
            "quantization": "none",
            "maximum_model_length": 4096,
            "output_token_budget": 32,
            "gpu_memory_utilization": "0.85",
            "gpu_model": "Tesla T4",
            "gpu_count": 2,
            "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
            "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "tokenizer_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "worker_startup_command_sha256": (_SHA_A, _SHA_B),
        }
    )
    gpu_topology = GpuTopologyReport.model_validate(
        {
            "evidence_id": "gpu-topology-report",
            **common,
            "devices": (
                GpuDeviceObservation(
                    gpu_index=0,
                    name="Tesla T4",
                    compute_capability="7.5",
                    memory_total_mib=15360,
                ),
                GpuDeviceObservation(
                    gpu_index=1,
                    name="Tesla T4",
                    compute_capability="7.5",
                    memory_total_mib=15360,
                ),
            ),
        }
    )
    model_identity = ModelIdentityReport.model_validate(
        {
            "evidence_id": "model-identity-report",
            **common,
            "model_repository": "Qwen/Qwen2.5-0.5B-Instruct",
            "model_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "tokenizer_revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "model_manifest_sha256": _SHA_A,
            "config_sha256": _SHA_B,
            "tokenizer_config_sha256": _SHA_C,
            "tokenizer_json_sha256": _SHA_D,
        }
    )
    worker_health = WorkerHealthReport.model_validate(
        {
            "evidence_id": "worker-health-report",
            **common,
            "workers": (
                WorkerHealthObservation(
                    worker_id="worker_1",
                    gpu_index=0,
                    port=8001,
                    health_status="healthy",
                ),
                WorkerHealthObservation(
                    worker_id="worker_2",
                    gpu_index=1,
                    port=8002,
                    health_status="healthy",
                ),
            ),
        }
    )
    metric_capability = CacheMetricCapabilityReport.model_validate(
        {
            "evidence_id": "cache-metric-capability-report",
            **common,
            "semantics": tuple(
                MetricCapabilityObservation(
                    semantic=semantic,
                    availability_state=MetricAvailabilityState.AVAILABLE,
                    raw_metric_name=f"vllm:{semantic}",
                    source_unit="state" if semantic.endswith("state") else "value",
                )
                for semantic in REQUIRED_METRIC_SEMANTICS
            ),
        }
    )
    reset_capability = ResetCapabilityReport.model_validate(
        {
            "evidence_id": "reset-capability-report",
            **common,
            "steps": tuple(
                ResetStepObservation(
                    step_id=step,
                    evidence_sha256=hashlib.sha256(step.encode("utf-8")).hexdigest(),
                )
                for step in REQUIRED_RESET_STEPS
            ),
        }
    )
    probes = tuple(
        ProbeObservation(
            probe_id=probe_id,
            worker_id="worker_1" if "worker-1" in probe_id else "worker_2",
            request_index=index,
            output_tokens=8,
        )
        for index, probe_id in enumerate(SYNTHETIC_PROBE_IDS, start=1)
    )
    qualification_report = QualificationReport.model_validate(
        {
            "evidence_id": "qualification-report",
            **common,
            "decision": QualificationDecision.QUALIFIED,
            "model_request_count": 6,
            "probes": probes,
            "environment_qualified": True,
        }
    )
    return QualificationRuntimeCapture(
        dependency_lock=dependency_lock,
        gpu_topology=gpu_topology,
        model_identity=model_identity,
        worker_health=worker_health,
        metric_capability=metric_capability,
        reset_capability=reset_capability,
        qualification_report=qualification_report,
    )


class _FakeAdapter(QualificationRuntimeAdapter):
    def __init__(self, capture: QualificationRuntimeCapture) -> None:
        self._capture = capture
        self.calls = 0

    def capture(
        self,
        request: QualificationExecutionRequest,
        dataset_manifest: QualificationDatasetManifest,
    ) -> QualificationRuntimeCapture:
        self.calls += 1
        assert request.probe_budget.maximum_model_requests == 8
        assert dataset_manifest.network_access_permitted is False
        return self._capture


def test_request_is_deterministic_and_authorization_blocked() -> None:
    first = build_execution_request()
    second = build_execution_request()
    assert first == second
    assert first.fingerprint() == second.fingerprint()
    assert first.next_gate == NEXT_GATE
    assert first.safety.execution_package_generated is True
    assert first.safety.notebook_created is True
    assert first.safety.kaggle_session_started is False
    assert first.safety.gpu_execution_authorized is False
    assert first.safety.model_execution_performed is False
    assert first.safety.runtime_evidence_generated is False
    assert first.safety.measured_execution_authorized is False


def test_probe_budget_and_order_are_frozen() -> None:
    request = build_execution_request()
    assert tuple(item.probe_id for item in request.synthetic_probes) == SYNTHETIC_PROBE_IDS
    assert request.probe_budget.maximum_model_requests == 8
    assert request.probe_budget.maximum_output_tokens_per_request == 32
    assert request.probe_budget.benchmark_trajectory_requests_permitted == 0
    assert request.probe_budget.hidden_retries_permitted is False
    assert request.planned_trajectory_count == 342


def test_probe_payloads_are_public_safe_and_fixed() -> None:
    for probe_id in SYNTHETIC_PROBE_IDS:
        prefix, suffix = synthetic_probe_payload(probe_id)
        assert prefix.startswith("Synthetic reliability probe")
        assert suffix.startswith("{")
        assert "customer" not in prefix.lower()
        assert "credential" not in suffix.lower()


def test_unknown_probe_fails_closed() -> None:
    with pytest.raises(Exception, match="registered"):
        synthetic_probe_payload("unknown-probe")


def test_request_rejects_budget_weakening() -> None:
    payload = build_execution_request().model_dump(mode="python")
    payload["probe_budget"]["maximum_model_requests"] = 9
    with pytest.raises(ValidationError):
        QualificationExecutionRequest.model_validate(payload)


def test_request_rejects_benchmark_execution_permission() -> None:
    payload = build_execution_request().model_dump(mode="python")
    payload["probe_budget"]["benchmark_trajectory_requests_permitted"] = 1
    with pytest.raises(ValidationError):
        QualificationExecutionRequest.model_validate(payload)


def test_request_rejects_generated_runtime_evidence() -> None:
    payload = build_execution_request().model_dump(mode="python")
    payload["runtime_evidence"][0]["generated"] = True
    with pytest.raises(ValidationError):
        QualificationExecutionRequest.model_validate(payload)


def test_metric_unavailable_cannot_claim_source_mapping() -> None:
    with pytest.raises(ValidationError):
        MetricCapabilityObservation(
            semantic="cached_prefix_tokens",
            availability_state=MetricAvailabilityState.UNAVAILABLE_NOT_ZERO,
            raw_metric_name="vllm:cached_tokens",
            source_unit="tokens",
        )


def test_notebook_is_unexecuted_and_delegates_to_typed_runner() -> None:
    notebook = build_notebook_payload()
    cells = cast(list[dict[str, object]], notebook["cells"])
    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    assert len(code_cells) == 1
    assert code_cells[0]["execution_count"] is None
    assert code_cells[0]["outputs"] == []
    source = "".join(cast(list[str], code_cells[0]["source"]))
    assert "execute_from_environment" in source
    assert "pip install" not in source
    assert "curl" not in source
    assert all(len(line) <= 100 for line in source.splitlines())


def test_dataset_manifest_rejects_network_or_credentials(tmp_path: Path) -> None:
    manifest = _dataset_manifest(tmp_path)
    payload = manifest.model_dump(mode="python")
    payload["network_access_permitted"] = True
    with pytest.raises(ValidationError):
        QualificationDatasetManifest.model_validate(payload)
    payload = manifest.model_dump(mode="python")
    payload["credentials_present"] = True
    with pytest.raises(ValidationError):
        QualificationDatasetManifest.model_validate(payload)


def test_authorization_rejects_expired_window(tmp_path: Path) -> None:
    request = build_execution_request()
    manifest = _dataset_manifest(tmp_path)
    authorization = _authorization(tmp_path, request, manifest)
    payload = authorization.model_dump(mode="python")
    payload["expires_at"] = payload["issued_at"]
    with pytest.raises(ValidationError):
        QualificationExecutionAuthorization.model_validate(payload)


def test_valid_capture_writes_exact_complete_evidence_bundle(tmp_path: Path) -> None:
    request = build_execution_request()
    manifest = _dataset_manifest(tmp_path)
    authorization = _authorization(tmp_path, request, manifest)
    capture = _capture(request, manifest)
    adapter = _FakeAdapter(capture)

    summary = execute_qualification(
        repo_root=tmp_path,
        request=request,
        authorization=authorization,
        dataset_manifest=manifest,
        adapter=adapter,
        now=_FIXED_NOW,
    )

    assert adapter.calls == 1
    assert summary["runtime_evidence_count"] == 8
    assert summary["environment_qualified"] is True
    assert summary["measured_execution_authorized"] is False
    assert (
        tuple(path.exists() for path in (tmp_path / p for p in RUNTIME_EVIDENCE_PATHS))
        == (True,) * 8
    )
    manifest_payload = json.loads((tmp_path / RUNTIME_EVIDENCE_PATHS[3]).read_text())
    assert manifest_payload["evidence_bundle_complete"] is True
    assert len(manifest_payload["entries"]) == 7


def test_capture_failure_leaves_no_partial_evidence(tmp_path: Path) -> None:
    request = build_execution_request()
    manifest = _dataset_manifest(tmp_path)
    authorization = _authorization(tmp_path, request, manifest)

    class _FailingAdapter(QualificationRuntimeAdapter):
        def capture(
            self,
            request: QualificationExecutionRequest,
            dataset_manifest: QualificationDatasetManifest,
        ) -> QualificationRuntimeCapture:
            raise RuntimeError("synthetic adapter failure")

    with pytest.raises(RuntimeError, match="synthetic adapter failure"):
        execute_qualification(
            repo_root=tmp_path,
            request=request,
            authorization=authorization,
            dataset_manifest=manifest,
            adapter=_FailingAdapter(),
            now=_FIXED_NOW,
        )
    assert all(not (tmp_path / path).exists() for path in RUNTIME_EVIDENCE_PATHS)


def test_existing_runtime_evidence_blocks_overwrite(tmp_path: Path) -> None:
    request = build_execution_request()
    manifest = _dataset_manifest(tmp_path)
    authorization = _authorization(tmp_path, request, manifest)
    capture = _capture(request, manifest)
    existing = tmp_path / RUNTIME_EVIDENCE_PATHS[0]
    existing.parent.mkdir(parents=True)
    existing.write_text("{}", encoding="utf-8")

    with pytest.raises(Exception, match="empty"):
        execute_qualification(
            repo_root=tmp_path,
            request=request,
            authorization=authorization,
            dataset_manifest=manifest,
            adapter=_FakeAdapter(capture),
            now=_FIXED_NOW,
        )


def test_runtime_capture_rejects_cross_session_evidence(tmp_path: Path) -> None:
    request = build_execution_request()
    manifest = _dataset_manifest(tmp_path)
    capture = _capture(request, manifest)
    payload = capture.model_dump(mode="python")
    payload["gpu_topology"]["runtime_session_id"] = "different-session"
    with pytest.raises(ValidationError):
        QualificationRuntimeCapture.model_validate(payload)


def test_qualification_report_requires_all_six_probes(tmp_path: Path) -> None:
    request = build_execution_request()
    manifest = _dataset_manifest(tmp_path)
    capture = _capture(request, manifest)
    payload = capture.qualification_report.model_dump(mode="python")
    payload["model_request_count"] = 5
    payload["probes"] = payload["probes"][:5]
    with pytest.raises(ValidationError):
        QualificationReport.model_validate(payload)


def test_runtime_factory_binding_rejects_unsafe_import_path(tmp_path: Path) -> None:
    adapter_path = tmp_path / "adapter.py"
    adapter_path.write_text("pass\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        QualificationRuntimeFactoryBinding(
            factory_path="../adapter:build",
            artifact_path=str(adapter_path.resolve()),
            artifact_sha256=_sha256(adapter_path),
        )


def test_static_request_file_matches_builder() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    request_path = repo_root / EXECUTION_REQUEST_PATH
    if not request_path.exists():
        pytest.skip("static package is not present in this checkout")
    assert request_path.read_text(encoding="utf-8") == build_execution_request().canonical_json()


def test_static_notebook_file_matches_builder() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    notebook_path = repo_root / NOTEBOOK_PATH
    if not notebook_path.exists():
        pytest.skip("static package is not present in this checkout")
    observed = json.loads(notebook_path.read_text(encoding="utf-8"))
    assert observed == build_notebook_payload()


def test_runbook_preserves_authorization_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    runbook_path = repo_root / RUNBOOK_PATH
    if not runbook_path.exists():
        pytest.skip("static package is not present in this checkout")
    text = runbook_path.read_text(encoding="utf-8")
    assert "Hard stop before authorization" in text
    assert "benchmark_trajectory_requests_permitted=0" in text
    assert "UNAVAILABLE_NOT_ZERO" in text
    assert "does not authorize the 342-trajectory measured run" in text


def test_expected_ruff_version_matches_local_tool() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == f"ruff {EXPECTED_RUFF_VERSION}"


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    paths = (
        repo_root / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution.py",
        repo_root / "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_contracts.py",
        Path(__file__),
    )
    failures = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if len(line) > 100:
                failures.append(f"{path}:{line_number}:{len(line)}")
    assert failures == []


def test_repository_package_generation_and_verification() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip("full Git checkout is required for repository authority validation")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            "cab13a26fac319c9aac92a5b721b0206dc1791e8",
            "HEAD",
        ],
        check=False,
    )
    if ancestry.returncode != 0:
        pytest.skip("PR 103 merge is not present in the isolated checkout")
    generated = generate_static_package(repo_root)
    verified = verify_static_package(repo_root)
    assert generated == verified
    assert verified["runtime_evidence_generated"] is False
