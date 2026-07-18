from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization as authorization_module,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_contracts as auth_contracts,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_kaggle_runtime_adapter as adapter_module,
)
from auragateway.local_abc.full_abc_local_environment_qualification_artifact_identity import (
    directory_sha256,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution import (
    build_execution_request,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts import (
    DatasetManifestEntry,
    QualificationDatasetManifest,
    QualificationRuntimeAdapter,
)

AUTHORIZATION_REQUEST_PATH = auth_contracts.AUTHORIZATION_REQUEST_PATH
DATASET_MANIFEST_REQUEST_PATH = auth_contracts.DATASET_MANIFEST_REQUEST_PATH
EXPECTED_RUFF_VERSION = auth_contracts.EXPECTED_RUFF_VERSION
FINAL_AUTHORIZATION_PATH = auth_contracts.FINAL_AUTHORIZATION_PATH
MATERIALIZED_DATASET_MANIFEST_PATH = auth_contracts.MATERIALIZED_DATASET_MANIFEST_PATH
NEXT_GATE = auth_contracts.NEXT_GATE
RUNTIME_ADAPTER_PATH = auth_contracts.RUNTIME_ADAPTER_PATH
AuthorizationPackageError = auth_contracts.AuthorizationPackageError
DatasetArtifactFormat = auth_contracts.DatasetArtifactFormat
DatasetMaterializationState = auth_contracts.DatasetMaterializationState
DatasetRole = auth_contracts.DatasetRole
OfflineDatasetManifestRequest = auth_contracts.OfflineDatasetManifestRequest
QualificationAuthorizationRequest = auth_contracts.QualificationAuthorizationRequest

ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATHS = (
    ROOT
    / ("src/auragateway/local_abc/full_abc_local_environment_qualification_artifact_identity.py"),
    ROOT
    / (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization_contracts.py"
    ),
    ROOT
    / (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_execution_authorization.py"
    ),
    ROOT
    / (
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
    ),
    Path(__file__).resolve(),
)

EXPECTED_DATASET_REQUEST_SHA256 = "7171c340a6015d962375223d083f62196454ad0097aa7dd72aef402f4ed13e1e"
EXPECTED_AUTHORIZATION_REQUEST_SHA256 = (
    "671b593f90af0d4a8331764f90a61b090738fb39bd7026f39236ef7eb519496e"
)


class _FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


class _FakeOperations:
    def __init__(self) -> None:
        self.counters = {8001: self._zero_metrics(), 8002: self._zero_metrics()}
        self.model_calls = 0
        self.spawned_argv: list[tuple[str, ...]] = []

    @staticmethod
    def _zero_metrics() -> dict[str, float]:
        return {
            "vllm:prefix_cache_hits_total": 0.0,
            "vllm:request_prefill_kv_computed_tokens_sum": 0.0,
            "vllm:request_prefill_time_seconds_sum": 0.0,
            "vllm:request_prompt_tokens_sum": 0.0,
            "vllm:e2e_request_latency_seconds_sum": 0.0,
            "vllm:time_to_first_token_seconds_sum": 0.0,
        }

    def now(self) -> datetime:
        return datetime(2026, 7, 18, 12, 0, tzinfo=UTC)

    def sleep(self, seconds: float) -> None:
        del seconds

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> adapter_module.CommandResult:
        del env, timeout
        if argv[0] == "nvidia-smi":
            return adapter_module.CommandResult(
                returncode=0,
                stdout="0, Tesla T4, 15109, 7.5\n1, Tesla T4, 15109, 7.5\n",
                stderr="",
            )
        if "pip" in argv:
            return adapter_module.CommandResult(returncode=0, stdout="", stderr="")
        payload = {
            "python": "3.11.9",
            "torch": "2.7.0+cu126",
            "cuda": "12.6",
            "transformers": "4.51.0",
            "vllm_module": "0.25.1",
            "vllm_distribution": "0.25.1",
            "attention_backend": "auto",
        }
        return adapter_module.CommandResult(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    def spawn(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str],
    ) -> _FakeProcess:
        del env
        frozen = tuple(argv)
        self.spawned_argv.append(frozen)
        port_index = frozen.index("--port") + 1
        self.counters[int(frozen[port_index])] = self._zero_metrics()
        return _FakeProcess()

    def get_status(self, url: str, *, timeout: float) -> int:
        del url, timeout
        return 200

    def get_text(self, url: str, *, timeout: float) -> str:
        del timeout
        port = int(url.split(":")[2].split("/")[0])
        return "\n".join(f"{name} {value}" for name, value in self.counters[port].items())

    def get_json(self, url: str, *, timeout: float) -> dict[str, object]:
        del url, timeout
        return {"data": [{"id": "local-qwen2.5-0.5b-instruct"}]}

    def post_json(
        self,
        url: str,
        payload: Mapping[str, object],
        *,
        timeout: float,
    ) -> dict[str, object]:
        del payload, timeout
        port = int(url.split(":")[2].split("/")[0])
        self.model_calls += 1
        metrics = self.counters[port]
        metrics["vllm:prefix_cache_hits_total"] += 8.0 if self.model_calls in {2, 4} else 0.0
        metrics["vllm:request_prefill_kv_computed_tokens_sum"] += 24.0
        metrics["vllm:request_prefill_time_seconds_sum"] += 0.02
        metrics["vllm:request_prompt_tokens_sum"] += 32.0
        metrics["vllm:e2e_request_latency_seconds_sum"] += 0.05
        metrics["vllm:time_to_first_token_seconds_sum"] += 0.03
        return {"usage": {"completion_tokens": 4}}

    def port_open(self, host: str, port: int, *, timeout: float) -> bool:
        del host, port, timeout
        return False


class _FailingSpawnOperations(_FakeOperations):
    def __init__(self) -> None:
        super().__init__()
        self.processes: list[_FakeProcess] = []

    def spawn(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str],
    ) -> _FakeProcess:
        if self.processes:
            raise RuntimeError("second worker spawn failed")
        process = super().spawn(argv, env=env)
        self.processes.append(process)
        return process


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payload(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="python")


def _write_startup_plan(repo_root: Path) -> None:
    workers = []
    for index, port in enumerate((8001, 8002)):
        workers.append(
            {
                "worker_id": f"worker_{index + 1}",
                "gpu_index": index,
                "host": "127.0.0.1",
                "port": port,
                "command_argv": list(adapter_module._expected_worker_command(port)),
                "command_sha256": adapter_module._EXPECTED_COMMAND_SHA256[f"worker_{index + 1}"],
                "environment": [
                    {"name": "CUDA_VISIBLE_DEVICES", "value": str(index)},
                    {"name": "HF_HUB_OFFLINE", "value": "1"},
                ],
            }
        )
    path = repo_root / (
        "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"workers": workers}), encoding="utf-8")


def _write_model_archive(tmp_path: Path) -> Path:
    source = tmp_path / "model-source"
    snapshot = source / (
        "hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
    )
    snapshot.mkdir(parents=True)
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json"):
        (snapshot / name).write_text("{}", encoding="utf-8")
    archive = tmp_path / "model-artifacts.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(source / "hub", arcname="hub")
    return archive


def _write_model_snapshot_directory(tmp_path: Path) -> Path:
    snapshot = tmp_path / (
        "hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
        "snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
    )
    snapshot.mkdir(parents=True)
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json"):
        (snapshot / name).write_text("{}", encoding="utf-8")
    return snapshot


def _dataset_manifest(tmp_path: Path) -> QualificationDatasetManifest:
    harness = tmp_path / "harness"
    (harness / "src/auragateway").mkdir(parents=True)
    (harness / "src/auragateway/__init__.py").write_text("", encoding="utf-8")
    model = _write_model_snapshot_directory(tmp_path)
    wheel = tmp_path / "vllm-0.25.1.whl"
    wheel.write_bytes(b"wheel")
    return QualificationDatasetManifest(
        manifest_id="qualification-dataset-v1",
        entries=(
            DatasetManifestEntry(
                role="harness_source",
                artifact_format="source_tree_directory",
                mounted_path=str(harness.resolve()),
                sha256=directory_sha256(harness),
            ),
            DatasetManifestEntry(
                role="model_artifacts",
                artifact_format="hugging_face_snapshot_directory",
                mounted_path=str(model.resolve()),
                sha256=directory_sha256(model),
            ),
            DatasetManifestEntry(
                role="vllm_wheel",
                artifact_format="python_wheel",
                mounted_path=str(wheel.resolve()),
                sha256=_sha256(wheel),
            ),
        ),
    )


def _materialized_record() -> auth_contracts.MaterializedOfflineDatasetRecord:
    entries = (
        auth_contracts.MaterializedDatasetEntry(
            role=DatasetRole.HARNESS_SOURCE,
            artifact_format=DatasetArtifactFormat.SOURCE_TREE_DIRECTORY,
            kaggle_dataset_slug="kablewithak/auragateway-qualification-harness",
            kaggle_dataset_version=1,
            mounted_path="/kaggle/input/auragateway-qualification-harness/source",
            sha256="1" * 64,
        ),
        auth_contracts.MaterializedDatasetEntry(
            role=DatasetRole.MODEL_ARTIFACTS,
            artifact_format=DatasetArtifactFormat.HUGGING_FACE_SNAPSHOT_DIRECTORY,
            kaggle_dataset_slug="kablewithak/qwen25-05b-offline",
            kaggle_dataset_version=2,
            mounted_path=(
                "/kaggle/input/qwen25-05b-offline/hf_home/hub/"
                "models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/"
                "7ae557604adf67be50417f59c2c2f167def9a775"
            ),
            sha256="2" * 64,
        ),
        auth_contracts.MaterializedDatasetEntry(
            role=DatasetRole.VLLM_WHEEL,
            artifact_format=DatasetArtifactFormat.PYTHON_WHEEL,
            kaggle_dataset_slug="kablewithak/vllm-0251-wheel",
            kaggle_dataset_version=3,
            mounted_path="/kaggle/input/vllm-0251-wheel/vllm-0.25.1.whl",
            sha256="3" * 64,
        ),
    )
    manifest = auth_contracts.PortableQualificationDatasetManifest(
        manifest_id="auragateway-environment-qualification-offline-dataset-v1",
        entries=(
            auth_contracts.PortableDatasetManifestEntry(
                role="harness_source",
                artifact_format="source_tree_directory",
                mounted_path=entries[0].mounted_path,
                sha256=entries[0].sha256,
            ),
            auth_contracts.PortableDatasetManifestEntry(
                role="model_artifacts",
                artifact_format="hugging_face_snapshot_directory",
                mounted_path=entries[1].mounted_path,
                sha256=entries[1].sha256,
            ),
            auth_contracts.PortableDatasetManifestEntry(
                role="vllm_wheel",
                artifact_format="python_wheel",
                mounted_path=entries[2].mounted_path,
                sha256=entries[2].sha256,
            ),
        ),
    )
    return auth_contracts.MaterializedOfflineDatasetRecord(
        record_id="auragateway-offline-dataset-materialization-v1",
        harness_source_commit="a" * 40,
        entries=entries,
        runtime_manifest_path=(
            "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
        ),
        runtime_manifest_sha256=manifest.fingerprint(),
    )


def test_static_requests_are_deterministic() -> None:
    dataset_first = authorization_module.build_offline_dataset_manifest_request()
    dataset_second = authorization_module.build_offline_dataset_manifest_request()
    auth_first = authorization_module.build_qualification_authorization_request()
    auth_second = authorization_module.build_qualification_authorization_request()

    assert dataset_first == dataset_second
    assert auth_first == auth_second
    assert dataset_first.fingerprint() == EXPECTED_DATASET_REQUEST_SHA256
    assert auth_first.fingerprint() == EXPECTED_AUTHORIZATION_REQUEST_SHA256


def test_dataset_request_preserves_exact_offline_roles() -> None:
    request = authorization_module.build_offline_dataset_manifest_request()

    assert request.status is DatasetMaterializationState.REQUESTED_NOT_MATERIALIZED
    assert tuple(item.role for item in request.roles) == (
        DatasetRole.HARNESS_SOURCE,
        DatasetRole.MODEL_ARTIFACTS,
        DatasetRole.VLLM_WHEEL,
    )
    assert tuple(item.artifact_format for item in request.roles) == (
        DatasetArtifactFormat.SOURCE_TREE_DIRECTORY,
        DatasetArtifactFormat.HUGGING_FACE_SNAPSHOT_DIRECTORY,
        DatasetArtifactFormat.PYTHON_WHEEL,
    )
    assert request.roles[1].artifact_format is (
        DatasetArtifactFormat.HUGGING_FACE_SNAPSHOT_DIRECTORY
    )
    assert all(item.materialized is False for item in request.roles)
    assert request.network_fallback_permitted is False
    assert request.credentials_permitted is False
    assert request.customer_data_permitted is False


def test_authorization_request_remains_issuance_blocked() -> None:
    request = authorization_module.build_qualification_authorization_request()

    assert request.final_authorization_generated is False
    assert request.final_authorization_path == FINAL_AUTHORIZATION_PATH.as_posix()
    assert request.runtime_adapter.adapter_generated is True
    assert request.runtime_adapter.adapter_executed is False
    assert request.runtime_adapter.model_request_retries_permitted is False
    assert request.maximum_model_requests == 8
    assert request.benchmark_trajectory_requests_permitted == 0
    assert request.next_gate == NEXT_GATE


def test_dataset_role_order_drift_is_rejected() -> None:
    request = authorization_module.build_offline_dataset_manifest_request()
    payload = _payload(request)
    payload["roles"] = tuple(reversed(payload["roles"]))

    with pytest.raises(ValidationError, match="offline dataset roles drifted"):
        OfflineDatasetManifestRequest.model_validate(payload)


def test_dataset_materialization_claim_is_rejected() -> None:
    request = authorization_module.build_offline_dataset_manifest_request()
    payload = _payload(request)
    roles = list(payload["roles"])
    role = dict(roles[0])
    role["materialized"] = True
    roles[0] = role
    payload["roles"] = roles

    with pytest.raises(ValidationError):
        OfflineDatasetManifestRequest.model_validate(payload)


def test_nonzero_authorization_spend_is_rejected() -> None:
    request = authorization_module.build_qualification_authorization_request()
    payload = _payload(request)
    payload["external_spend"] = 1

    with pytest.raises(ValidationError):
        QualificationAuthorizationRequest.model_validate(payload)


def test_final_authorization_claim_is_rejected() -> None:
    request = authorization_module.build_qualification_authorization_request()
    payload = _payload(request)
    payload["final_authorization_generated"] = True

    with pytest.raises(ValidationError):
        QualificationAuthorizationRequest.model_validate(payload)


def test_runtime_adapter_factory_satisfies_protocol() -> None:
    adapter = adapter_module.create_runtime_adapter()

    assert isinstance(adapter, QualificationRuntimeAdapter)


def test_stdlib_operations_reject_non_loopback_urls() -> None:
    with pytest.raises(RuntimeError, match="loopback"):
        adapter_module.StdlibRuntimeOperations._loopback_url("https://example.com/metrics")


def test_runtime_adapter_static_audit_passes() -> None:
    authorization_module._audit_runtime_adapter(ROOT / RUNTIME_ADAPTER_PATH)


def test_worker_startup_plan_argv_drift_is_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_startup_plan(repo_root)
    path = repo_root / (
        "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["workers"][0]["command_argv"][-1] = "--enable-log-requests"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="startup argv drifted"):
        adapter_module.KaggleQualificationRuntimeAdapter._load_worker_plans(path)


def test_runtime_adapter_completes_six_probe_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_startup_plan(repo_root)
    monkeypatch.setenv("AURAGATEWAY_REPO_ROOT", str(repo_root))
    for name in adapter_module._CREDENTIAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    operations = _FakeOperations()
    adapter = adapter_module.KaggleQualificationRuntimeAdapter(operations)
    capture = adapter.capture(build_execution_request(), _dataset_manifest(tmp_path))

    assert capture.qualification_report.environment_qualified is True
    assert capture.qualification_report.model_request_count == 6
    assert len(capture.qualification_report.probes) == 6
    assert capture.metric_capability.all_required_metrics_available is True
    assert capture.reset_capability.reset_capability_verified is True
    assert operations.model_calls == 6
    assert len(operations.spawned_argv) == 4


def test_runtime_adapter_rejects_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_startup_plan(repo_root)
    monkeypatch.setenv("AURAGATEWAY_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("HF_TOKEN", "not-a-real-token")
    adapter = adapter_module.KaggleQualificationRuntimeAdapter(_FakeOperations())

    with pytest.raises(RuntimeError, match="credential-bearing"):
        adapter.capture(build_execution_request(), _dataset_manifest(tmp_path))


def test_runtime_adapter_rejects_missing_metric() -> None:
    before = _FakeOperations._zero_metrics()
    after = dict(before)
    after.pop("vllm:prefix_cache_hits_total")

    with pytest.raises(RuntimeError, match="cached_prefix_tokens"):
        adapter_module.KaggleQualificationRuntimeAdapter._metric_evidence(before, after)


def test_runtime_adapter_rejects_counter_regression() -> None:
    before = _FakeOperations._zero_metrics()
    after = dict(before)
    before["vllm:request_prompt_tokens_sum"] = 5.0

    with pytest.raises(RuntimeError, match="prompt_tokens"):
        adapter_module.KaggleQualificationRuntimeAdapter._metric_evidence(before, after)


def test_static_package_verifier_rejects_final_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(authorization_module, "_validate_repository_authorities", lambda _: None)
    monkeypatch.setattr(authorization_module, "_require_package_files", lambda _: None)
    monkeypatch.setattr(authorization_module, "_audit_runtime_adapter", lambda _: None)
    dataset_path = tmp_path / DATASET_MANIFEST_REQUEST_PATH
    authorization_path = tmp_path / AUTHORIZATION_REQUEST_PATH
    final_path = tmp_path / FINAL_AUTHORIZATION_PATH
    for path, payload in (
        (dataset_path, authorization_module.build_offline_dataset_manifest_request()),
        (
            authorization_path,
            authorization_module.build_qualification_authorization_request(),
        ),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload.canonical_json(), encoding="utf-8")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_text("{}", encoding="utf-8")

    with pytest.raises(AuthorizationPackageError) as caught:
        authorization_module.verify_static_authorization_package(tmp_path)

    assert caught.value.error_code == "OPERATIONAL_AUTHORITY_PREMATURE"


def test_materialization_record_retains_exact_kaggle_provenance() -> None:
    record = _materialized_record()
    first = record.entries[0]

    assert first.kaggle_dataset_slug == ("kablewithak/auragateway-qualification-harness")
    assert first.kaggle_dataset_version == 1
    assert first.mounted_path.startswith("/kaggle/input/")
    assert record.network_access_permitted is False


def test_portable_runtime_manifest_is_exact_projection() -> None:
    record = _materialized_record()
    manifest = authorization_module.build_portable_runtime_manifest(record)

    assert tuple(item.role for item in manifest.entries) == (
        "harness_source",
        "model_artifacts",
        "vllm_wheel",
    )
    assert tuple(item.artifact_format for item in manifest.entries) == (
        "source_tree_directory",
        "hugging_face_snapshot_directory",
        "python_wheel",
    )
    assert tuple(item.sha256 for item in manifest.entries) == tuple(
        item.sha256 for item in record.entries
    )
    assert manifest.fingerprint() == record.runtime_manifest_sha256


def test_materialized_dataset_duplicate_slug_is_rejected() -> None:
    record = _materialized_record()
    payload = _payload(record)
    entries = list(payload["entries"])
    second = dict(entries[1])
    second["kaggle_dataset_slug"] = entries[0]["kaggle_dataset_slug"]
    entries[1] = second
    payload["entries"] = tuple(entries)

    with pytest.raises(ValidationError, match="dataset slugs must be unique"):
        auth_contracts.MaterializedOfflineDatasetRecord.model_validate(payload)


def test_materialized_dataset_artifact_format_drift_is_rejected() -> None:
    record = _materialized_record()
    payload = _payload(record)
    entries = list(payload["entries"])
    first = dict(entries[0])
    first["artifact_format"] = "python_wheel"
    entries[0] = first
    payload["entries"] = tuple(entries)

    with pytest.raises(ValidationError, match="artifact formats drifted"):
        auth_contracts.MaterializedOfflineDatasetRecord.model_validate(payload)


def test_materialized_dataset_unsafe_mount_is_rejected() -> None:
    record = _materialized_record()
    payload = _payload(record)
    entries = list(payload["entries"])
    first = dict(entries[0])
    first["mounted_path"] = "/tmp/harness.zip"
    entries[0] = first
    payload["entries"] = tuple(entries)

    with pytest.raises(ValidationError, match="under /kaggle/input"):
        auth_contracts.MaterializedOfflineDatasetRecord.model_validate(payload)


def test_issuance_inputs_reject_runtime_manifest_drift(tmp_path: Path) -> None:
    record = _materialized_record()
    manifest = authorization_module.build_portable_runtime_manifest(record)
    payload = _payload(manifest)
    entries = list(payload["entries"])
    first = dict(entries[0])
    first["sha256"] = "f" * 64
    entries[0] = first
    payload["entries"] = tuple(entries)
    drifted = auth_contracts.PortableQualificationDatasetManifest.model_validate(payload)
    record_path = tmp_path / "record.json"
    manifest_path = tmp_path / "manifest.json"
    record_path.write_text(record.canonical_json(), encoding="utf-8")
    manifest_path.write_text(drifted.canonical_json(), encoding="utf-8")

    with pytest.raises(AuthorizationPackageError) as caught:
        authorization_module.validate_issuance_inputs(
            repo_root=tmp_path,
            materialization_record_path=record_path,
            runtime_manifest_path=manifest_path,
        )

    assert caught.value.error_code == "RUNTIME_DATASET_MANIFEST_DRIFT"


def test_issuance_inputs_validate_exact_hash_linkage(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    adapter_path = repo_root / RUNTIME_ADAPTER_PATH
    adapter_path.parent.mkdir(parents=True)
    adapter_path.write_text(
        (ROOT / RUNTIME_ADAPTER_PATH).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "AuraGateway Tests"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: freeze harness source"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    record = _materialized_record().model_copy(update={"harness_source_commit": commit})
    manifest = authorization_module.build_portable_runtime_manifest(record)
    record_path = tmp_path / "record.json"
    manifest_path = tmp_path / "manifest.json"
    record_path.write_text(record.canonical_json(), encoding="utf-8")
    manifest_path.write_text(manifest.canonical_json(), encoding="utf-8")

    summary = authorization_module.validate_issuance_inputs(
        repo_root=repo_root,
        materialization_record_path=record_path,
        runtime_manifest_path=manifest_path,
    )

    assert summary["exact_kaggle_dataset_count"] == 3
    assert summary["runtime_dataset_manifest_sha256"] == manifest.fingerprint()
    assert summary["final_authorization_generated"] is False


def test_expanded_model_snapshot_is_copied_into_writable_cache(tmp_path: Path) -> None:
    snapshot = _write_model_snapshot_directory(tmp_path)
    workspace = tmp_path / "workspace"
    adapter = adapter_module.KaggleQualificationRuntimeAdapter(_FakeOperations())

    cache_root, copied_snapshot = adapter._prepare_model_cache(snapshot, workspace)

    assert cache_root == workspace / "model-cache/hf_home"
    assert copied_snapshot == cache_root / (
        "hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
    )
    assert (copied_snapshot / "config.json").read_text(encoding="utf-8") == "{}"
    assert copied_snapshot != snapshot


def test_model_snapshot_directory_fingerprint_is_deterministic(tmp_path: Path) -> None:
    snapshot = _write_model_snapshot_directory(tmp_path)

    first = adapter_module.KaggleQualificationRuntimeAdapter._model_artifact_sha256(snapshot)
    second = adapter_module.KaggleQualificationRuntimeAdapter._model_artifact_sha256(snapshot)

    assert first == second
    assert len(first) == 64


def test_model_snapshot_requires_exact_hugging_face_cache_layout(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "7ae557604adf67be50417f59c2c2f167def9a775"
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="exact cache layout"):
        adapter_module.KaggleQualificationRuntimeAdapter._copy_snapshot_directory_safely(
            snapshot, tmp_path / "target"
        )


def test_model_tar_rejects_symbolic_links(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        member = tarfile.TarInfo("unsafe-link")
        member.type = tarfile.SYMTYPE
        member.linkname = "outside"
        handle.addfile(member)

    with pytest.raises(RuntimeError, match="unsafe member type"):
        adapter_module.KaggleQualificationRuntimeAdapter._extract_tar_safely(
            archive, tmp_path / "extract"
        )


def test_model_zip_rejects_symbolic_links(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        member = zipfile.ZipInfo("unsafe-link")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        handle.writestr(member, "outside")

    with pytest.raises(RuntimeError, match="unsafe member type"):
        adapter_module.KaggleQualificationRuntimeAdapter._extract_zip_safely(
            archive, tmp_path / "extract"
        )


def test_partial_worker_start_is_cleaned_up(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_startup_plan(repo_root)
    operations = _FailingSpawnOperations()
    adapter = adapter_module.KaggleQualificationRuntimeAdapter(operations)
    plans = adapter._load_worker_plans(
        repo_root / "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
    )

    with pytest.raises(RuntimeError, match="second worker spawn failed"):
        adapter._start_workers(plans, tmp_path / "model-cache")

    assert len(operations.processes) == 1
    assert operations.processes[0].poll() == 0


def test_expected_paths_are_stable() -> None:
    assert AUTHORIZATION_REQUEST_PATH.name == "qualification_authorization_request.json"
    assert DATASET_MANIFEST_REQUEST_PATH.name == "offline_dataset_manifest_request.json"
    assert MATERIALIZED_DATASET_MANIFEST_PATH.name == "offline_dataset_manifest.json"
    assert RUNTIME_ADAPTER_PATH.name.endswith("kaggle_runtime_adapter.py")


def test_expected_ruff_version_matches_local_tool() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == f"ruff {EXPECTED_RUFF_VERSION}"


def test_git_blob_identity_uses_exact_working_tree_bytes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test User"],
        check=True,
    )
    artifact = repo / "authority.txt"
    artifact.write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "authority.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "initial"],
        check=True,
    )
    committed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD:authority.txt"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    artifact.write_text("new\n", encoding="utf-8")
    expected = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "hash-object",
            "--path=authority.txt",
            str(artifact),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    observed = authorization_module._git_blob_sha(repo, Path("authority.txt"))

    assert observed == expected
    assert observed != committed


def test_changed_python_lines_do_not_exceed_100_characters() -> None:
    failures: list[str] = []
    for path in SOURCE_PATHS:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if len(line) > 100:
                failures.append(f"{path.as_posix()}:{line_number}:{len(line)}")

    assert failures == []


def test_committed_requests_match_builders() -> None:
    dataset_path = ROOT / DATASET_MANIFEST_REQUEST_PATH
    authorization_path = ROOT / AUTHORIZATION_REQUEST_PATH
    if not dataset_path.exists() or not authorization_path.exists():
        pytest.skip("full repository generated requests are unavailable")

    observed_dataset = OfflineDatasetManifestRequest.model_validate_json(
        dataset_path.read_text(encoding="utf-8")
    )
    observed_authorization = QualificationAuthorizationRequest.model_validate_json(
        authorization_path.read_text(encoding="utf-8")
    )
    assert observed_dataset == authorization_module.build_offline_dataset_manifest_request()
    assert (
        observed_authorization == authorization_module.build_qualification_authorization_request()
    )


def test_repository_package_matches_exact_pr_105_authorities() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("full Git checkout is unavailable")

    summary = authorization_module.verify_static_authorization_package(ROOT)

    assert summary["authorization_package_generated"] is True
    assert summary["runtime_adapter_generated"] is True
    assert summary["runtime_adapter_executed"] is False
    assert summary["final_authorization_generated"] is False
    assert summary["materialized_dataset_manifest_generated"] is False
    assert summary["kaggle_session_started"] is False
    assert summary["maximum_model_requests"] == 8
    assert summary["benchmark_trajectory_requests_permitted"] == 0
    assert summary["external_spend"] == 0


def test_authorization_error_is_metadata_safe() -> None:
    error = AuthorizationPackageError(
        "SAFE_CODE",
        "safe message",
        "safe/path.json",
        ("safe-detail",),
    )

    assert error.error_code == "SAFE_CODE"
    assert error.safe_message == "safe message"
    assert error.path == "safe/path.json"
