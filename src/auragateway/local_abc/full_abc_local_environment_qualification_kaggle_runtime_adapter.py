"""Concrete offline Kaggle adapter for bounded environment qualification."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, Protocol, cast
from uuid import uuid4

from auragateway.local_abc.full_abc_local_environment_qualification_artifact_identity import (
    directory_sha256,
    file_sha256,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution import (
    synthetic_probe_payload,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts import (
    REQUIRED_METRIC_SEMANTICS,
    REQUIRED_RESET_STEPS,
    CacheMetricCapabilityReport,
    GpuDeviceObservation,
    GpuTopologyReport,
    KaggleRuntimeDependencyLock,
    MetricAvailabilityState,
    MetricCapabilityObservation,
    ModelIdentityReport,
    ProbeObservation,
    QualificationDatasetManifest,
    QualificationDecision,
    QualificationExecutionRequest,
    QualificationReport,
    QualificationRuntimeCapture,
    ResetCapabilityReport,
    ResetStepObservation,
    SyntheticProbeDefinition,
    WorkerHealthObservation,
    WorkerHealthReport,
)

_STARTUP_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
_MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
_MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
_SERVED_MODEL_NAME: Final = "local-qwen2.5-0.5b-instruct"
_EXPECTED_VLLM_VERSION: Final = "0.25.1"
_MAX_HEALTH_POLLS: Final = 90
_HEALTH_POLL_SECONDS: Final = 2.0
_REQUEST_TIMEOUT_SECONDS: Final = 120.0
_MAX_MODEL_EXTRACT_BYTES: Final = 16 * 1024**3
_EXPECTED_COMMAND_SHA256: Final = {
    "worker_1": "b89bb09ac28407d1fb0e32c88f75422ce4e7e437d0d4db732bdc85a4982d0fda",
    "worker_2": "40ed11132c6e1106fba26339b7210f95effac37cf1ecebddb287754ad76c738d",
}


def _expected_worker_command(port: int) -> tuple[str, ...]:
    return (
        "python",
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        _MODEL_REPOSITORY,
        "--revision",
        _MODEL_REVISION,
        "--tokenizer",
        _MODEL_REPOSITORY,
        "--tokenizer-revision",
        _MODEL_REVISION,
        "--served-model-name",
        _SERVED_MODEL_NAME,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--dtype",
        "auto",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.85",
        "--max-num-seqs",
        "8",
        "--enable-prefix-caching",
        "--disable-log-requests",
    )


_CREDENTIAL_ENV_NAMES: Final = (
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)

_METRIC_SPECS: Final = {
    "cached_prefix_tokens": (
        ("vllm:prefix_cache_hits_total", "vllm:prompt_tokens_cached_total"),
        "tokens",
    ),
    "newly_computed_prefill_tokens": (
        ("vllm:request_prefill_kv_computed_tokens_sum",),
        "tokens",
    ),
    "prefill_duration_ms": (
        ("vllm:request_prefill_time_seconds_sum",),
        "seconds",
    ),
    "prompt_tokens": (("vllm:request_prompt_tokens_sum",), "tokens"),
    "request_latency_ms": (("vllm:e2e_request_latency_seconds_sum",), "seconds"),
    "time_to_first_token_ms": (
        ("vllm:time_to_first_token_seconds_sum",),
        "seconds",
    ),
}

_ADAPTER_SEMANTICS: Final = {
    "metric_availability_state": ("adapter:metric_validation", "state"),
    "realized_route": ("adapter:loopback_endpoint", "identity"),
    "reset_state": ("adapter:full_restart_sequence", "state"),
    "worker_id": ("adapter:frozen_worker_binding", "identity"),
}


class WorkerProcess(Protocol):
    """Minimal process boundary required for worker lifecycle control."""

    def poll(self) -> int | None:
        """Return process state without blocking."""

    def terminate(self) -> None:
        """Request graceful process termination."""

    def kill(self) -> None:
        """Force process termination after timeout."""

    def wait(self, timeout: float | None = None) -> int:
        """Wait for process exit."""


@dataclass(frozen=True)
class CommandResult:
    """Bounded command result without raw environment disclosure."""

    returncode: int
    stdout: str
    stderr: str


class RuntimeOperations(Protocol):
    """Injectable runtime side effects for deterministic local tests."""

    def now(self) -> datetime:
        """Return a timezone-aware current timestamp."""

    def sleep(self, seconds: float) -> None:
        """Pause between explicit readiness polls."""

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        """Run one bounded command without a shell."""

    def spawn(self, argv: Sequence[str], *, env: Mapping[str, str]) -> WorkerProcess:
        """Start one worker without shell interpretation."""

    def get_status(self, url: str, *, timeout: float) -> int:
        """Return one loopback HTTP response status."""

    def get_text(self, url: str, *, timeout: float) -> str:
        """Return one loopback text response."""

    def get_json(self, url: str, *, timeout: float) -> dict[str, object]:
        """Return one loopback JSON response."""

    def post_json(
        self,
        url: str,
        payload: Mapping[str, object],
        *,
        timeout: float,
    ) -> dict[str, object]:
        """Send one loopback JSON request with no retry."""

    def port_open(self, host: str, port: int, *, timeout: float) -> bool:
        """Return whether one loopback TCP port accepts a connection."""


class StdlibRuntimeOperations:
    """Production operations restricted to subprocess argv and loopback HTTP."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        result = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            env=dict(env) if env is not None else None,
            timeout=timeout,
        )
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def spawn(self, argv: Sequence[str], *, env: Mapping[str, str]) -> WorkerProcess:
        return subprocess.Popen(
            list(argv),
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def get_status(self, url: str, *, timeout: float) -> int:
        request = urllib.request.Request(self._loopback_url(url), method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return cast(int, response.status)

    def get_text(self, url: str, *, timeout: float) -> str:
        request = urllib.request.Request(self._loopback_url(url), method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return cast(str, response.read().decode("utf-8"))

    def get_json(self, url: str, *, timeout: float) -> dict[str, object]:
        payload = json.loads(self.get_text(url, timeout=timeout))
        if not isinstance(payload, dict):
            raise RuntimeError("loopback response root must be one JSON object")
        return cast(dict[str, object], payload)

    def post_json(
        self,
        url: str,
        payload: Mapping[str, object],
        *,
        timeout: float,
    ) -> dict[str, object]:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self._loopback_url(url),
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            observed = json.loads(response.read().decode("utf-8"))
        if not isinstance(observed, dict):
            raise RuntimeError("loopback response root must be one JSON object")
        return cast(dict[str, object], observed)

    def port_open(self, host: str, port: int, *, timeout: float) -> bool:
        if host not in {"127.0.0.1", "localhost"}:
            raise RuntimeError("port checks are restricted to loopback hosts")
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    @staticmethod
    def _loopback_url(url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise RuntimeError("runtime HTTP is restricted to loopback endpoints")
        if parsed.username is not None or parsed.password is not None:
            raise RuntimeError("runtime loopback URLs cannot contain credentials")
        if parsed.query or parsed.fragment:
            raise RuntimeError("runtime loopback URLs cannot contain query or fragment data")
        return url


@dataclass(frozen=True)
class WorkerPlan:
    """Validated static worker launch instruction."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    host: Literal["127.0.0.1"]
    port: Literal[8001, 8002]
    command_argv: tuple[str, ...]
    command_sha256: str
    environment: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ProbeMetricEvidence:
    """Per-request metric identities and observed nonnegative deltas."""

    raw_names: Mapping[str, str]
    deltas: Mapping[str, float]


class KaggleQualificationRuntimeAdapter:
    """Execute one authorized, offline, two-worker qualification capture."""

    def __init__(self, operations: RuntimeOperations | None = None) -> None:
        self._operations = operations or StdlibRuntimeOperations()

    def capture(
        self,
        request: QualificationExecutionRequest,
        dataset_manifest: QualificationDatasetManifest,
    ) -> QualificationRuntimeCapture:
        """Run six fixed probes and return one complete in-memory evidence bundle."""

        self._require_private_offline_environment()
        entries = {entry.role: Path(entry.mounted_path) for entry in dataset_manifest.entries}
        repo_root = self._repo_root()
        plans = self._load_worker_plans(repo_root / _STARTUP_PLAN_PATH)
        session_id = f"kaggle-qualification-{uuid4().hex}"
        request_sha256 = request.fingerprint()
        dataset_sha256 = dataset_manifest.fingerprint()
        captured_at = self._operations.now()
        processes: list[WorkerProcess] = []

        with tempfile.TemporaryDirectory(prefix="auragateway-qualification-") as raw_workspace:
            workspace = Path(raw_workspace)
            model_cache_root, snapshot_path = self._prepare_model_cache(
                entries["model_artifacts"],
                workspace,
            )
            self._install_local_vllm(entries["vllm_wheel"])
            gpu_topology = self._capture_gpu_topology(
                session_id,
                captured_at,
                request_sha256,
                dataset_sha256,
            )
            dependency_lock = self._capture_dependency_lock(
                entries["vllm_wheel"],
                plans,
                session_id,
                captured_at,
                request_sha256,
                dataset_sha256,
            )
            model_identity = self._capture_model_identity(
                entries["model_artifacts"],
                snapshot_path,
                session_id,
                captured_at,
                request_sha256,
                dataset_sha256,
            )

            probe_observations: list[ProbeObservation] = []
            metric_evidence: list[ProbeMetricEvidence] = []
            reset_step_payloads: dict[str, str] = {}
            try:
                processes = self._start_workers(plans, model_cache_root)
                self._wait_for_workers(plans)
                self._validate_models(plans)
                worker_health = self._build_worker_health_report(
                    plans,
                    session_id,
                    captured_at,
                    request_sha256,
                    dataset_sha256,
                )
                for probe in request.synthetic_probes[:4]:
                    observation, metrics = self._run_probe(probe, plans)
                    probe_observations.append(observation)
                    metric_evidence.append(metrics)

                self._stop_workers(processes)
                processes = []
                reset_step_payloads["confirm_worker_process_exit"] = "workers=exited"
                self._require_ports_closed(plans)
                reset_step_payloads["confirm_worker_ports_closed"] = "ports=8001,8002:closed"
                reset_step_payloads["record_reset_start"] = self._operations.now().isoformat()

                processes = self._start_workers(plans, model_cache_root)
                reset_step_payloads["restart_workers_from_bound_startup_plan"] = ",".join(
                    plan.command_sha256 for plan in plans
                )
                self._wait_for_workers(plans)
                self._validate_models(plans)
                reset_step_payloads["revalidate_model_tokenizer_and_worker_identity"] = (
                    model_identity.fingerprint()
                )
                baseline = tuple(self._metrics(plan) for plan in plans)
                reset_step_payloads["verify_fresh_health_and_metric_baseline"] = self._sha256(
                    json.dumps(baseline, sort_keys=True)
                )

                for probe in request.synthetic_probes[4:]:
                    observation, metrics = self._run_probe(probe, plans)
                    probe_observations.append(observation)
                    metric_evidence.append(metrics)
            finally:
                self._stop_workers(processes)

        metric_capability = self._build_metric_capability_report(
            metric_evidence,
            session_id,
            captured_at,
            request_sha256,
            dataset_sha256,
        )
        reset_capability = self._build_reset_capability_report(
            reset_step_payloads,
            session_id,
            captured_at,
            request_sha256,
            dataset_sha256,
        )
        qualification_report = QualificationReport(
            evidence_id="qualification-report",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            decision=QualificationDecision.QUALIFIED,
            model_request_count=len(probe_observations),
            probes=tuple(probe_observations),
            environment_qualified=True,
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

    @staticmethod
    def _repo_root() -> Path:
        raw = os.environ.get("AURAGATEWAY_REPO_ROOT")
        if raw is None:
            raise RuntimeError("AURAGATEWAY_REPO_ROOT is required by the runtime adapter")
        path = Path(raw).resolve()
        if not path.is_dir():
            raise RuntimeError("AURAGATEWAY_REPO_ROOT must resolve to a directory")
        return path

    @staticmethod
    def _require_private_offline_environment() -> None:
        present = tuple(name for name in _CREDENTIAL_ENV_NAMES if os.environ.get(name))
        if present:
            raise RuntimeError("credential-bearing environment variables are prohibited")
        if os.environ.get("AURAGATEWAY_CUSTOMER_DATA_PRESENT") == "1":
            raise RuntimeError("customer data is prohibited during environment qualification")

    def _prepare_model_cache(self, artifact: Path, workspace: Path) -> tuple[Path, Path]:
        target = workspace / "model-cache"
        target.mkdir(parents=True, exist_ok=True)
        if artifact.is_dir():
            self._copy_snapshot_directory_safely(artifact, target)
        elif artifact.name.endswith(".tar.gz") or artifact.suffix == ".tgz":
            self._extract_tar_safely(artifact, target)
        elif artifact.suffix == ".zip":
            self._extract_zip_safely(artifact, target)
        else:
            raise RuntimeError(
                "model artifacts must be an exact Hugging Face snapshot directory "
                "or a tar.gz, tgz, or zip archive"
            )

        matches = tuple(target.rglob(f"snapshots/{_MODEL_REVISION}/config.json"))
        if len(matches) != 1:
            raise RuntimeError("model artifacts must contain one exact Hugging Face snapshot")
        snapshot = matches[0].parent
        hub_parent = next((parent for parent in snapshot.parents if parent.name == "hub"), None)
        if hub_parent is None:
            raise RuntimeError("model artifacts must preserve the Hugging Face cache layout")
        return hub_parent.parent, snapshot

    @classmethod
    def _copy_snapshot_directory_safely(cls, snapshot: Path, target: Path) -> None:
        expected_tail = (
            "hub",
            "models--Qwen--Qwen2.5-0.5B-Instruct",
            "snapshots",
            _MODEL_REVISION,
        )
        if not snapshot.is_dir() or snapshot.is_symlink():
            raise RuntimeError("model snapshot input must be a real directory")
        if tuple(snapshot.parts[-len(expected_tail) :]) != expected_tail:
            raise RuntimeError("model snapshot path does not preserve the exact cache layout")

        destination = target.joinpath("hf_home", *expected_tail)
        cls._copy_directory_safely(snapshot, destination)

    @staticmethod
    def _copy_directory_safely(source: Path, destination: Path) -> None:
        total_size = 0
        files: list[tuple[Path, Path]] = []
        for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(source)
            if path.is_symlink():
                raise RuntimeError("model snapshot contains an unsafe member type")
            mode = path.stat().st_mode
            if path.is_dir():
                continue
            if not stat.S_ISREG(mode):
                raise RuntimeError("model snapshot contains an unsafe member type")
            total_size += path.stat().st_size
            if total_size > _MAX_MODEL_EXTRACT_BYTES:
                raise RuntimeError("model snapshot exceeds the copy budget")
            files.append((path, destination / relative))

        if not files:
            raise RuntimeError("model snapshot directory is empty")
        for source_file, destination_file in files:
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination_file, follow_symlinks=False)

    @staticmethod
    def _model_artifact_sha256(artifact: Path) -> str:
        if artifact.is_file():
            return file_sha256(artifact)
        return directory_sha256(
            artifact,
            maximum_bytes=_MAX_MODEL_EXTRACT_BYTES,
        )

    @staticmethod
    def _extract_tar_safely(archive: Path, target: Path) -> None:
        with tarfile.open(archive, mode="r:*") as handle:
            members = handle.getmembers()
            root = target.resolve()
            total_size = 0
            for member in members:
                resolved = (target / member.name).resolve()
                if root not in resolved.parents and resolved != root:
                    raise RuntimeError("model archive contains an unsafe path")
                if member.issym() or member.islnk() or member.isdev():
                    raise RuntimeError("model archive contains an unsafe member type")
                if member.isfile():
                    total_size += member.size
                    if total_size > _MAX_MODEL_EXTRACT_BYTES:
                        raise RuntimeError("model archive exceeds the extraction budget")
            handle.extractall(target, members=members, filter="data")

    @staticmethod
    def _extract_zip_safely(archive: Path, target: Path) -> None:
        with zipfile.ZipFile(archive) as handle:
            root = target.resolve()
            total_size = 0
            for member in handle.infolist():
                resolved = (target / member.filename).resolve()
                if root not in resolved.parents and resolved != root:
                    raise RuntimeError("model archive contains an unsafe path")
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise RuntimeError("model archive contains an unsafe member type")
                if member.flag_bits & 0x1:
                    raise RuntimeError("encrypted model archives are prohibited")
                total_size += member.file_size
                if total_size > _MAX_MODEL_EXTRACT_BYTES:
                    raise RuntimeError("model archive exceeds the extraction budget")
            handle.extractall(target)

    def _install_local_vllm(self, wheel_path: Path) -> None:
        env = dict(os.environ)
        env.update(
            {
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_INDEX": "1",
            }
        )
        result = self._operations.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                str(wheel_path),
            ],
            env=env,
            timeout=300.0,
        )
        if result.returncode != 0:
            raise RuntimeError("local vLLM wheel installation failed")

    def _capture_gpu_topology(
        self,
        session_id: str,
        captured_at: datetime,
        request_sha256: str,
        dataset_sha256: str,
    ) -> GpuTopologyReport:
        result = self._operations.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            timeout=30.0,
        )
        if result.returncode != 0:
            raise RuntimeError("GPU topology command failed")
        devices: list[GpuDeviceObservation] = []
        for line in result.stdout.splitlines():
            parts = tuple(part.strip() for part in line.split(","))
            if len(parts) != 4:
                raise RuntimeError("GPU topology output is malformed")
            index_raw, name_raw, memory_raw, capability_raw = parts
            index = int(index_raw)
            if index not in (0, 1):
                raise RuntimeError("GPU topology contains an unexpected device index")
            if name_raw not in {"Tesla T4", "NVIDIA T4"}:
                raise RuntimeError("GPU topology does not expose two Tesla T4 devices")
            if capability_raw != "7.5":
                raise RuntimeError("GPU compute capability does not match Tesla T4")
            devices.append(
                GpuDeviceObservation(
                    gpu_index=cast(Literal[0, 1], index),
                    name="Tesla T4",
                    compute_capability="7.5",
                    memory_total_mib=int(float(memory_raw)),
                )
            )
        return GpuTopologyReport(
            evidence_id="gpu-topology-report",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            devices=cast(tuple[GpuDeviceObservation, GpuDeviceObservation], tuple(devices)),
        )

    def _capture_dependency_lock(
        self,
        wheel_path: Path,
        plans: tuple[WorkerPlan, WorkerPlan],
        session_id: str,
        captured_at: datetime,
        request_sha256: str,
        dataset_sha256: str,
    ) -> KaggleRuntimeDependencyLock:
        script = (
            "import importlib.metadata,json,os,platform,torch,transformers,vllm;"
            "print(json.dumps({'python':platform.python_version(),"
            "'torch':torch.__version__,'cuda':torch.version.cuda or 'unavailable',"
            "'transformers':transformers.__version__,'vllm_module':vllm.__version__,"
            "'vllm_distribution':importlib.metadata.version('vllm'),"
            "'attention_backend':os.getenv('VLLM_ATTENTION_BACKEND','auto')}))"
        )
        result = self._operations.run([sys.executable, "-c", script], timeout=30.0)
        if result.returncode != 0:
            raise RuntimeError("runtime dependency lock capture failed")
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError("runtime dependency lock output is invalid")
        if payload.get("vllm_distribution") != _EXPECTED_VLLM_VERSION:
            raise RuntimeError("installed vLLM distribution version does not match 0.25.1")
        return KaggleRuntimeDependencyLock(
            evidence_id="kaggle-runtime-dependency-lock",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            python_version=str(payload["python"]),
            torch_version=str(payload["torch"]),
            cuda_version=str(payload["cuda"]),
            transformers_version=str(payload["transformers"]),
            vllm_module_version=str(payload["vllm_module"]),
            vllm_distribution_version=str(payload["vllm_distribution"]),
            vllm_wheel_sha256=self._file_sha256(wheel_path),
            attention_backend=str(payload["attention_backend"]),
            automatic_prefix_cache_configuration="enabled",
            dtype="auto",
            quantization="none",
            maximum_model_length=4096,
            output_token_budget=32,
            gpu_memory_utilization="0.85",
            gpu_model="Tesla T4",
            gpu_count=2,
            model_repository=_MODEL_REPOSITORY,
            model_revision=_MODEL_REVISION,
            tokenizer_revision=_MODEL_REVISION,
            worker_startup_command_sha256=(
                plans[0].command_sha256,
                plans[1].command_sha256,
            ),
        )

    def _capture_model_identity(
        self,
        model_artifact: Path,
        snapshot: Path,
        session_id: str,
        captured_at: datetime,
        request_sha256: str,
        dataset_sha256: str,
    ) -> ModelIdentityReport:
        required = {
            "config": snapshot / "config.json",
            "tokenizer_config": snapshot / "tokenizer_config.json",
            "tokenizer_json": snapshot / "tokenizer.json",
        }
        missing = tuple(name for name, path in required.items() if not path.is_file())
        if missing:
            raise RuntimeError("model snapshot is missing required identity files")
        return ModelIdentityReport(
            evidence_id="model-identity-report",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            model_repository=_MODEL_REPOSITORY,
            model_revision=_MODEL_REVISION,
            tokenizer_revision=_MODEL_REVISION,
            model_manifest_sha256=self._model_artifact_sha256(model_artifact),
            config_sha256=self._file_sha256(required["config"]),
            tokenizer_config_sha256=self._file_sha256(required["tokenizer_config"]),
            tokenizer_json_sha256=self._file_sha256(required["tokenizer_json"]),
        )

    @staticmethod
    def _load_worker_plans(path: Path) -> tuple[WorkerPlan, WorkerPlan]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        workers = payload.get("workers") if isinstance(payload, dict) else None
        if not isinstance(workers, list) or len(workers) != 2:
            raise RuntimeError("worker startup plan must contain exactly two workers")
        plans: list[WorkerPlan] = []
        for worker in workers:
            if not isinstance(worker, dict):
                raise RuntimeError("worker startup plan entry is invalid")
            environment_raw = worker.get("environment")
            if not isinstance(environment_raw, list):
                raise RuntimeError("worker startup environment is invalid")
            environment = tuple(
                (str(item["name"]), str(item["value"]))
                for item in environment_raw
                if isinstance(item, dict)
            )
            command_raw = worker.get("command_argv")
            if not isinstance(command_raw, list) or not all(
                isinstance(item, str) for item in command_raw
            ):
                raise RuntimeError("worker startup argv is invalid")
            worker_id = str(worker["worker_id"])
            gpu_index = int(worker["gpu_index"])
            host = str(worker["host"])
            port = int(worker["port"])
            if worker_id not in {"worker_1", "worker_2"}:
                raise RuntimeError("worker startup identity is invalid")
            expected_topology = {"worker_1": (0, 8001), "worker_2": (1, 8002)}
            if (gpu_index, port) != expected_topology[worker_id]:
                raise RuntimeError("worker startup topology is invalid")
            if host != "127.0.0.1":
                raise RuntimeError("worker startup host must remain loopback-only")
            if tuple(command_raw) != _expected_worker_command(port):
                raise RuntimeError("worker startup argv drifted")
            command_sha256 = str(worker["command_sha256"])
            if command_sha256 != _EXPECTED_COMMAND_SHA256[worker_id]:
                raise RuntimeError("worker startup command identity drifted")
            expected_environment = (
                ("CUDA_VISIBLE_DEVICES", str(gpu_index)),
                ("HF_HUB_OFFLINE", "1"),
            )
            if environment != expected_environment:
                raise RuntimeError("worker startup environment drifted")
            plans.append(
                WorkerPlan(
                    worker_id=cast(Literal["worker_1", "worker_2"], worker_id),
                    gpu_index=cast(Literal[0, 1], gpu_index),
                    host="127.0.0.1",
                    port=cast(Literal[8001, 8002], port),
                    command_argv=tuple(command_raw),
                    command_sha256=command_sha256,
                    environment=environment,
                )
            )
        if tuple(plan.worker_id for plan in plans) != ("worker_1", "worker_2"):
            raise RuntimeError("worker startup plan order drifted")
        return cast(tuple[WorkerPlan, WorkerPlan], tuple(plans))

    def _start_workers(
        self,
        plans: tuple[WorkerPlan, WorkerPlan],
        model_cache_root: Path,
    ) -> list[WorkerProcess]:
        processes: list[WorkerProcess] = []
        try:
            for plan in plans:
                env = dict(os.environ)
                env.update(dict(plan.environment))
                env.update(
                    {
                        "HF_HOME": str(model_cache_root),
                        "HF_HUB_OFFLINE": "1",
                        "TRANSFORMERS_OFFLINE": "1",
                    }
                )
                processes.append(self._operations.spawn(plan.command_argv, env=env))
        except Exception:
            self._stop_workers(processes)
            raise
        return processes

    def _wait_for_workers(self, plans: tuple[WorkerPlan, WorkerPlan]) -> None:
        for plan in plans:
            url = f"http://{plan.host}:{plan.port}/health"
            for poll_index in range(_MAX_HEALTH_POLLS):
                try:
                    if self._operations.get_status(url, timeout=2.0) == 200:
                        break
                except (OSError, RuntimeError, urllib.error.URLError):
                    pass
                if poll_index + 1 == _MAX_HEALTH_POLLS:
                    raise RuntimeError("worker failed bounded readiness polling")
                self._operations.sleep(_HEALTH_POLL_SECONDS)

    def _validate_models(self, plans: tuple[WorkerPlan, WorkerPlan]) -> None:
        for plan in plans:
            payload = self._operations.get_json(
                f"http://{plan.host}:{plan.port}/v1/models",
                timeout=10.0,
            )
            data = payload.get("data")
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                raise RuntimeError("worker model inventory response is invalid")
            if data[0].get("id") != _SERVED_MODEL_NAME:
                raise RuntimeError("worker served model identity drifted")

    def _build_worker_health_report(
        self,
        plans: tuple[WorkerPlan, WorkerPlan],
        session_id: str,
        captured_at: datetime,
        request_sha256: str,
        dataset_sha256: str,
    ) -> WorkerHealthReport:
        workers = tuple(
            WorkerHealthObservation(
                worker_id=plan.worker_id,
                gpu_index=plan.gpu_index,
                port=plan.port,
                health_status="healthy",
            )
            for plan in plans
        )
        return WorkerHealthReport(
            evidence_id="worker-health-report",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            workers=cast(
                tuple[WorkerHealthObservation, WorkerHealthObservation],
                workers,
            ),
        )

    def _run_probe(
        self,
        probe: SyntheticProbeDefinition,
        plans: tuple[WorkerPlan, WorkerPlan],
    ) -> tuple[ProbeObservation, ProbeMetricEvidence]:
        worker_id_raw = str(probe.worker_id)
        if worker_id_raw not in {"worker_1", "worker_2"}:
            raise RuntimeError("synthetic probe worker identity is invalid")
        worker_id = cast(Literal["worker_1", "worker_2"], worker_id_raw)
        probe_id = str(probe.probe_id)
        sequence_index = int(probe.sequence_index)
        plan = next(plan for plan in plans if plan.worker_id == worker_id)
        before = self._metrics(plan)
        prefix, suffix = synthetic_probe_payload(probe_id)
        payload = {
            "model": _SERVED_MODEL_NAME,
            "messages": [
                {"role": "system", "content": prefix},
                {"role": "user", "content": suffix},
            ],
            "max_tokens": 32,
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 7,
            "stream": False,
        }
        response = self._operations.post_json(
            f"http://{plan.host}:{plan.port}/v1/chat/completions",
            payload,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        after = self._metrics(plan)
        usage = response.get("usage")
        if not isinstance(usage, dict):
            raise RuntimeError("worker response usage metadata is missing")
        output_tokens = usage.get("completion_tokens")
        if not isinstance(output_tokens, int):
            raise RuntimeError("worker response completion token count is invalid")
        return (
            ProbeObservation(
                probe_id=probe_id,
                worker_id=worker_id,
                request_index=sequence_index,
                output_tokens=output_tokens,
            ),
            self._metric_evidence(before, after),
        )

    def _metrics(self, plan: WorkerPlan) -> dict[str, float]:
        payload = self._operations.get_text(
            f"http://{plan.host}:{plan.port}/metrics",
            timeout=10.0,
        )
        samples: dict[str, float] = {}
        for line in payload.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields = stripped.split()
            if len(fields) < 2:
                continue
            name = fields[0].split("{", maxsplit=1)[0]
            try:
                value = float(fields[-1])
            except ValueError:
                continue
            samples[name] = samples.get(name, 0.0) + value
        return samples

    @staticmethod
    def _metric_evidence(
        before: Mapping[str, float],
        after: Mapping[str, float],
    ) -> ProbeMetricEvidence:
        raw_names: dict[str, str] = {}
        deltas: dict[str, float] = {}
        for semantic, (candidates, _) in _METRIC_SPECS.items():
            name = next((candidate for candidate in candidates if candidate in after), None)
            if name is None or name not in before:
                raise RuntimeError(f"required runtime metric unavailable: {semantic}")
            delta = after[name] - before[name]
            if delta < 0:
                raise RuntimeError(f"runtime metric counter regressed: {semantic}")
            raw_names[semantic] = name
            deltas[semantic] = delta
        return ProbeMetricEvidence(raw_names=raw_names, deltas=deltas)

    def _build_metric_capability_report(
        self,
        evidence: Sequence[ProbeMetricEvidence],
        session_id: str,
        captured_at: datetime,
        request_sha256: str,
        dataset_sha256: str,
    ) -> CacheMetricCapabilityReport:
        if len(evidence) != 6:
            raise RuntimeError("metric capability requires all six probes")
        observations: list[MetricCapabilityObservation] = []
        for semantic in REQUIRED_METRIC_SEMANTICS:
            if semantic in _METRIC_SPECS:
                names = {item.raw_names[semantic] for item in evidence}
                if len(names) != 1:
                    raise RuntimeError("runtime metric identity drifted across probes")
                _, unit = _METRIC_SPECS[semantic]
                raw_name = next(iter(names))
            else:
                raw_name, unit = _ADAPTER_SEMANTICS[semantic]
            observations.append(
                MetricCapabilityObservation(
                    semantic=semantic,
                    availability_state=MetricAvailabilityState.AVAILABLE,
                    raw_metric_name=raw_name,
                    source_unit=unit,
                )
            )
        return CacheMetricCapabilityReport(
            evidence_id="cache-metric-capability-report",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            semantics=tuple(observations),
        )

    def _build_reset_capability_report(
        self,
        payloads: Mapping[str, str],
        session_id: str,
        captured_at: datetime,
        request_sha256: str,
        dataset_sha256: str,
    ) -> ResetCapabilityReport:
        if tuple(payloads) != REQUIRED_RESET_STEPS:
            raise RuntimeError("reset capability sequence is incomplete")
        steps = tuple(
            ResetStepObservation(
                step_id=step_id,
                evidence_sha256=self._sha256(payloads[step_id]),
            )
            for step_id in REQUIRED_RESET_STEPS
        )
        return ResetCapabilityReport(
            evidence_id="reset-capability-report",
            runtime_session_id=session_id,
            captured_at=captured_at,
            source_request_sha256=request_sha256,
            dataset_manifest_sha256=dataset_sha256,
            steps=steps,
        )

    def _require_ports_closed(self, plans: tuple[WorkerPlan, WorkerPlan]) -> None:
        open_ports = tuple(
            str(plan.port)
            for plan in plans
            if self._operations.port_open(plan.host, plan.port, timeout=1.0)
        )
        if open_ports:
            raise RuntimeError("worker ports remained open after process termination")

    @staticmethod
    def _stop_workers(processes: Sequence[WorkerProcess]) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=20.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10.0)

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _sha256(payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_runtime_adapter() -> KaggleQualificationRuntimeAdapter:
    """Return the concrete adapter loaded only after external authorization."""

    return KaggleQualificationRuntimeAdapter()
