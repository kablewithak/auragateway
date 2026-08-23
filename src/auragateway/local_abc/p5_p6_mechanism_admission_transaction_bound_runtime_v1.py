from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Final

NOTEBOOK_NAME: Final = "ag-p5-p6-mechanism-tx-lifecycle-r2"
SOURCE_MAIN_COMMIT: Final = "f63fa24ddd5fab038e5676a2c5792adf63c95d6c"
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
)
DESIGN_RECORD_SHA256: Final = "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
MECHANISM_ADMISSION_CONTRACT_SHA256: Final = (
    "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
)
IMPLEMENTATION_ADDENDUM_SHA256: Final = (
    "395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239"
)
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
EXPECTED_BACKEND_LOG_MARKER: Final = (
    "Using AttentionBackendEnum.TRITON_ATTN backend."
)
BACKEND_MARKER_LOG_PREFIX_PATTERN: Final = re.compile(
    r"^(?:.*\bINFO\b.*)?Using AttentionBackendEnum\.TRITON_ATTN backend\.$"
)
BACKEND_MARKER_EXCLUDED_TOKENS: Final = (
    "--attention-backend",
    "expected_backend_log_marker",
    "return ",
    "assert ",
    "print(",
)
GPU_MEMORY_RETURN_TOLERANCE_MIB: Final = 128
MAX_TEARDOWN_POLLS: Final = 20
TEARDOWN_POLL_SECONDS: Final = 0.5

INPUT_ROOT = Path("/kaggle/input").resolve()
WORK_ROOT = Path("/kaggle/working").resolve()
OUTPUT_ROOT = WORK_ROOT / "p5_p6_mechanism_admission_successor_v1"
SCRATCH_ROOT = WORK_ROOT / "p5_p6_mechanism_admission_successor_v1_scratch"
TARGET_ROOT = SCRATCH_ROOT / "target_runtime"
TARGET_SITE = TARGET_ROOT / "lib" / "python3.12" / "site-packages"
TARGET_PYTHON = TARGET_ROOT / "bin" / "python"
LOG_ROOT = OUTPUT_ROOT / "worker_logs"
EVIDENCE_ZIP = WORK_ROOT / "ag-p5-p6-mechanism-successor-lifecycle-r2-evidence.zip"

RUNTIME_OUTPUT_DIRECTORY = "auragateway_preflight_v3_exact_runtime_wheelhouse_v1"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_REPOSITORY = "Qwen/Qwen2.5-0.5B-Instruct"
SERVED_MODEL_NAME = "local-qwen2.5-0.5b-instruct"
EXPECTED_VLLM_DISTRIBUTION_VERSION = "0.25.1+cu129"
EXPECTED_VLLM_MODULE_VERSION = "0.25.1"
EXPECTED_TORCH_VERSION = "2.11.0+cu129"
EXPECTED_TORCH_CUDA = "12.9"
EXPECTED_TRITON_VERSION = "3.6.0"
EXPECTED_TRANSFORMERS_VERSION = "5.14.1"
REQUIRED_NATIVE_MODULE = "vllm._C_stable_libtorch"
EXPECTED_GPU_NAME = "Tesla T4"
EXPECTED_COMPUTE_CAPABILITY = "7.5"
EXPECTED_BACKEND = "TRITON_ATTN"
EXPECTED_BACKEND_CLASS = (
    "vllm.v1.attention.backends.triton_attn.TritonAttentionBackend"
)
REAL_DRIVER_DIRECTORY = "/usr/local/nvidia/lib64"
EXPECTED_CHILD_PYTHON = TARGET_PYTHON
IMPORT_CLOSURE_MODULES = (
    "vllm",
    "torch",
    "triton",
    "transformers",
    "vllm.model_executor.models.registry",
)

MAX_HEALTH_POLLS = 90
HEALTH_POLL_SECONDS = 2.0
HTTP_TIMEOUT_SECONDS = 120.0
MAX_STREAM_BYTES = 131072
MAX_INSTALL_EXCERPT_CHARACTERS = 16000
MAX_EVIDENCE_ZIP_BYTES = 2 * 1024**2
MAX_MODEL_BYTES = 16 * 1024**3

EXPECTED_CONTROL_HASHES = {
    "resolution_lock.json": (
        "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
    ),
    "requirements.lock.txt": (
        "cf5d773ef5c26f2e42a7afd76f0e466c21847169986f14fe5a7ac9ad02f0a3c3"
    ),
    "materialization.lock.txt": (
        "774461508794d804244b2f0dbff05e52fdccc8efbe19af8cfb8d0faedcb25339"
    ),
    "runtime_manifest.json": (
        "cb9c62321ea1651deac260126db75c39525e4ba711ee3708fe5f7a5b50ffd6ed"
    ),
    "sha256_manifest.json": (
        "00dbda4fd734cf94b6f5dfde2619f83ed6a4db7761a4c3c5ace6b0f1ebe63b08"
    ),
    "materialization_receipt.json": (
        "55bc8d078af9960d5f6a60bf7d9638820be9fdda0ee76754a9462d46eb053fe0"
    ),
}

OUTPUT_NAMES = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "c1_model_construction_report_v1.json",
    "c2_worker_startup_report_v1.json",
    "c3_single_request_report_v1.json",
    "c4_output_contract_report_v1.json",
    "p5_cache_behavior_report_v1.json",
    "p5_post_restart_native_origin_report_v1.json",
    "p6_stage_checkpoint_report_v1.json",
    "p6_native_origin_report_v1.json",
    "p6_worker_state_isolation_report_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "p5_p6_exact_runtime_requalification_summary_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
)

CREDENTIAL_ENV_NAMES = (
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

SYSTEM_PROMPT = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
SYNTHETIC_CACHE_CONTEXT_A = (
    (
        "AuraGateway deterministic prefix-cache reliability probe variant A. "
        "This text is synthetic, contains no customer data, and must remain "
        "byte-identical whenever prefix variant A is requested. "
    )
    * 24
    + (
        "For structured probes, return only the exact JSON object supplied "
        "in the final user message."
    )
)
SYNTHETIC_CACHE_CONTEXT_B = (
    (
        "AuraGateway deliberately changed prefix-cache control variant B. "
        "This text is synthetic, contains no customer data, and intentionally "
        "diverges from variant A before the repeated control body. "
    )
    * 24
    + (
        "For structured probes, return only the exact JSON object supplied "
        "in the final user message."
    )
)
SYNTHETIC_ASSISTANT_ACK = "Synthetic deterministic context acknowledged."
EXPECTED_OBJECT = {"probe": "exact-runtime-p5-p6", "value": 1}
EXPECTED_OBJECT_CANONICAL = json.dumps(
    EXPECTED_OBJECT,
    ensure_ascii=True,
    separators=(",", ":"),
    sort_keys=True,
)
CACHE_BLOCK_SIZE = 16

ACTION_BUDGET_LIMITS = {
    "runtime_install_attempts": 1,
    "runtime_import_closure_probes": 1,
    "model_loads": 3,
    "worker_starts": 3,
    "model_requests": 6,
}

FAILURE_CODES = {
    "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH",
    "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
    "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
    "P3_P6_PLATFORM_IDENTITY_MISMATCH",
    "P3_P6_WHEELHOUSE_INVALID",
    "P3_P6_RUNTIME_INSTALL_FAILED",
    "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT",
    "P3_P6_RUNTIME_INSTALL_TIMEOUT",
    "P3_P6_RUNTIME_INSTALL_LAUNCH_FAILED",
    "P3_P6_MODEL_IDENTITY_MISMATCH",
    "P3_P6_EXPLICIT_BACKEND_NOT_REALIZED",
    "P3_P6_WORKER_STARTUP_FAILED",
    "P3_P6_MODEL_INVENTORY_MISMATCH",
    "P3_P6_REQUEST_FAILED",
    "P3_P6_METRIC_SEMANTIC_UNAVAILABLE",
    "P3_P6_CACHE_REUSE_NOT_OBSERVED",
    "P3_P6_RESET_NOT_PROVEN",
    "P6_WORKER_2_STARTUP_FAILED",
    "P6_PROCESS_ISOLATION_FAILED",
    "P6_GPU_ISOLATION_FAILED",
    "P6_PORT_ISOLATION_FAILED",
    "P6_WORKER_1_ROUTE_TRANSPORT_FAILED",
    "P6_WORKER_1_RESPONSE_ENVELOPE_INVALID",
    "P6_WORKER_1_METRIC_ATTRIBUTION_FAILED",
    "P6_WORKER_2_ROUTE_TRANSPORT_FAILED",
    "P6_WORKER_2_RESPONSE_ENVELOPE_INVALID",
    "P6_WORKER_2_METRIC_ATTRIBUTION_FAILED",
    "P6_REQUEST_COUNTER_RECONCILIATION_FAILED",
    "P6_CHECKPOINT_SERIALIZATION_FAILED",
    "P3_P6_ACTION_BUDGET_EXCEEDED",
    "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
    "P3_P6_WORKER_TEARDOWN_FAILED",
    "P3_P6_SCRATCH_CLEANUP_FAILED",
}

FAILURE_TAXONOMY = {
    "INPUT_IDENTITY_FAILURE",
    "MODEL_ARTIFACT_FAILURE",
    "TOKENIZER_ARTIFACT_FAILURE",
    "MODEL_CONSTRUCTION_FAILURE",
    "WORKER_STARTUP_FAILURE",
    "WORKER_IDENTITY_FAILURE",
    "DEVICE_REALIZATION_FAILURE",
    "REQUEST_EXECUTION_FAILURE",
    "OUTPUT_CONTRACT_FAILURE",
    "P5_CACHE_ENABLEMENT_FAILURE",
    "P5_STARTING_STATE_FAILURE",
    "P5_CACHE_OBSERVATION_FAILURE",
    "P5_BEHAVIOR_FAILURE",
    "P6_ROUTE_REALIZATION_FAILURE",
    "P6_WORKER_GENERATION_FAILURE",
    "P6_STATE_ISOLATION_FAILURE",
    "P6_BEHAVIOR_FAILURE",
    "METRIC_SEMANTIC_FAILURE",
    "METRIC_ATTRIBUTION_AMBIGUOUS",
    "REQUEST_RECONCILIATION_FAILURE",
    "TEARDOWN_FAILURE",
    "HARNESS_SEMANTIC_FAILURE",
    "EVIDENCE_PROJECTION_FAILURE",
    "AUTHORITY_FAILURE",
    "NON_DETERMINISTIC_FAILURE",
    "DIAGNOSTIC_INVALID",
}


def classify_failure_detail(detail_code: str) -> str:
    if detail_code in FAILURE_TAXONOMY:
        return detail_code
    explicit = {
        "MODEL_CONSTRUCTION_FAILURE": "MODEL_CONSTRUCTION_FAILURE",
        "REQUEST_EXECUTION_FAILURE": "REQUEST_EXECUTION_FAILURE",
    }
    if detail_code in explicit:
        return explicit[detail_code]
    if detail_code in {
        "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH",
        "P3_P6_WHEELHOUSE_INVALID",
        "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
    }:
        return "AUTHORITY_FAILURE"
    if detail_code in {
        "P3_P6_MODEL_IDENTITY_MISMATCH",
    }:
        return "MODEL_ARTIFACT_FAILURE"
    if detail_code in {
        "P3_P6_RUNTIME_INSTALL_FAILED",
        "P3_P6_RUNTIME_INSTALL_NONZERO_EXIT",
        "P3_P6_RUNTIME_INSTALL_TIMEOUT",
        "P3_P6_RUNTIME_INSTALL_LAUNCH_FAILED",
        "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
        "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
        "P3_P6_PLATFORM_IDENTITY_MISMATCH",
        "P3_P6_MODEL_INVENTORY_MISMATCH",
        "P3_P6_EXPLICIT_BACKEND_NOT_REALIZED",
    }:
        return "MODEL_CONSTRUCTION_FAILURE"
    if detail_code in {
        "P3_P6_WORKER_STARTUP_FAILED",
        "P6_WORKER_2_STARTUP_FAILED",
    }:
        return "WORKER_STARTUP_FAILURE"
    if detail_code in {
        "P3_P6_REQUEST_FAILED",
        "P6_WORKER_1_ROUTE_TRANSPORT_FAILED",
        "P6_WORKER_2_ROUTE_TRANSPORT_FAILED",
    }:
        return "REQUEST_EXECUTION_FAILURE"
    if detail_code in {
        "P6_WORKER_1_RESPONSE_ENVELOPE_INVALID",
        "P6_WORKER_2_RESPONSE_ENVELOPE_INVALID",
    }:
        return "OUTPUT_CONTRACT_FAILURE"
    if detail_code == "P3_P6_METRIC_SEMANTIC_UNAVAILABLE":
        return "METRIC_SEMANTIC_FAILURE"
    if detail_code == "P3_P6_CACHE_REUSE_NOT_OBSERVED":
        return "P5_BEHAVIOR_FAILURE"
    if detail_code == "P3_P6_RESET_NOT_PROVEN":
        return "P5_STARTING_STATE_FAILURE"
    if detail_code == "P6_PROCESS_ISOLATION_FAILED":
        return "WORKER_IDENTITY_FAILURE"
    if detail_code == "P6_GPU_ISOLATION_FAILED":
        return "DEVICE_REALIZATION_FAILURE"
    if detail_code == "P6_PORT_ISOLATION_FAILED":
        return "P6_ROUTE_REALIZATION_FAILURE"
    if detail_code in {
        "P6_WORKER_1_METRIC_ATTRIBUTION_FAILED",
        "P6_WORKER_2_METRIC_ATTRIBUTION_FAILED",
    }:
        return "METRIC_ATTRIBUTION_AMBIGUOUS"
    if detail_code == "P6_REQUEST_COUNTER_RECONCILIATION_FAILED":
        return "REQUEST_RECONCILIATION_FAILURE"
    if detail_code == "P6_CHECKPOINT_SERIALIZATION_FAILED":
        return "EVIDENCE_PROJECTION_FAILURE"
    if detail_code == "P3_P6_ACTION_BUDGET_EXCEEDED":
        return "AUTHORITY_FAILURE"
    if detail_code in {
        "P3_P6_WORKER_TEARDOWN_FAILED",
        "P3_P6_SCRATCH_CLEANUP_FAILED",
    }:
        return "TEARDOWN_FAILURE"
    return "DIAGNOSTIC_INVALID"


class BehaviorState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBIGUOUS = "AMBIGUOUS"


class ObservationState(StrEnum):
    NOT_EXPOSED = "NOT_EXPOSED"
    NOT_OBSERVED = "NOT_OBSERVED"
    ZERO = "ZERO"
    POSITIVE = "POSITIVE"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"


class SemanticState(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    VALID_JSON_MISMATCH = "VALID_JSON_MISMATCH"
    NON_OBJECT_JSON = "NON_OBJECT_JSON"
    INVALID_JSON = "INVALID_JSON"


@dataclass(frozen=True)
class SemanticObservation:
    state: SemanticState
    response_content_sha256: str
    parsed_json_sha256: str | None
    valid_json: bool
    object_root: bool
    exact_match: bool


@dataclass(frozen=True)
class RawMetricSample:
    name: str
    labels: tuple[tuple[str, str], ...]
    value: float


@dataclass(frozen=True)
class MetricSnapshotObservation:
    prefix_cache_queries: float
    prefix_cache_hits: float
    local_compute: float
    local_cache_hit: float
    external_kv_transfer: float
    cached_prompt_tokens: float
    newly_computed_prefill_tokens: float

    @property
    def total_prompt_tokens(self) -> float:
        return (
            self.local_compute
            + self.local_cache_hit
            + self.external_kv_transfer
        )


@dataclass(frozen=True)
class MetricDeltaObservation:
    prefix_cache_queries: float
    prefix_cache_hits: float
    local_compute: float
    local_cache_hit: float
    external_kv_transfer: float
    cached_prompt_tokens: float
    newly_computed_prefill_tokens: float

    @property
    def total_prompt_tokens(self) -> float:
        return (
            self.local_compute
            + self.local_cache_hit
            + self.external_kv_transfer
        )


@dataclass(frozen=True)
class TokenIdentityObservation:
    request_role: str
    prefix_variant: str
    token_count: int
    token_sha256: str
    token_ids: tuple[int, ...]


@dataclass(frozen=True)
class RouteObservation:
    request_id: str
    request_role: str
    intended_worker: str
    realized_worker: str
    worker_generation: int
    endpoint_port: int
    metric_endpoint_identity: str
    route_reason: str
    fallback_reason: str | None
    output_sha256: str


@dataclass(frozen=True)
class BehaviorDecision:
    capability: str
    state: BehaviorState
    failure_class: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceProjection:
    decision: BehaviorDecision
    public_summary: dict[str, object]


def observation_state(value: float | None) -> ObservationState:
    if value is None:
        return ObservationState.NOT_OBSERVED
    if value < 0:
        return ObservationState.INVALID
    if value == 0:
        return ObservationState.ZERO
    return ObservationState.POSITIVE


FAILURE_CODES |= FAILURE_TAXONOMY


class DiagnosticFailure(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        if error_code not in FAILURE_CODES:
            raise ValueError("unsupported exact-runtime P5/P6 failure code")
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class DiagnosticAmbiguity(RuntimeError):
    def __init__(self, failure_class: str, safe_message: str) -> None:
        if failure_class not in FAILURE_TAXONOMY:
            raise ValueError("unsupported ambiguity failure class")
        super().__init__(safe_message)
        self.failure_class = failure_class
        self.safe_message = safe_message



def require_transaction_bound_context(
) -> dict[str, object]:
    transaction_id = globals().get("AURAGATEWAY_TRANSACTION_ID")
    if (
        not isinstance(transaction_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", transaction_id) is None
    ):
        raise DiagnosticFailure(
            "AUTHORITY_FAILURE",
            "transaction-bound wrapper admission context is missing or invalid",
        )
    return {
        "transaction_id": transaction_id,
        "authorization_transport": "EMBEDDED_WRAPPER_ADMISSION",
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "runtime_execution_authorized": True,
    }

def consume_actions(
    counters: dict[str, int],
    *action_names: str,
) -> None:
    for name in action_names:
        limit = ACTION_BUDGET_LIMITS.get(name)
        if limit is None:
            raise DiagnosticFailure(
                "P3_P6_ACTION_BUDGET_EXCEEDED",
                f"unknown bounded action: {name}",
            )
        if counters[name] >= limit:
            raise DiagnosticFailure(
                "P3_P6_ACTION_BUDGET_EXCEEDED",
                f"action budget exhausted: {name}",
            )
    for name in action_names:
        counters[name] += 1


def canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise RuntimeError("temporary evidence path already exists")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path: Path, payload: object) -> None:
    write_bytes_atomic(path, canonical_json(payload).encode("utf-8"))


def write_text(path: Path, payload: str) -> None:
    write_bytes_atomic(path, payload.replace("\r\n", "\n").encode("utf-8"))


def runtime_source_identity() -> dict[str, object]:
    value = globals().get("EXECUTED_RUNTIME_SCRIPT_SHA256")
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH",
            "runtime source identity wrapper is missing or invalid",
        )
    return {
        "schema_version": "1.0.0",
        "report_id": "auragateway-p5-p6-exact-runtime-requalification-runtime-source-identity-v1",
        "status": "PASSED",
        "decision": "EXECUTED_RUNTIME_SCRIPT_IDENTITY_VERIFIED",
        "notebook_name": NOTEBOOK_NAME,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "executed_runtime_script_sha256": value,
        "wrapper_hash_verification_passed": True,
    }


def write_runtime_source_identity_report() -> dict[str, object]:
    report = runtime_source_identity()
    write_json(
        OUTPUT_ROOT / "runtime_source_identity_report_v1.json",
        report,
    )
    return report


def bounded_loopback(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http":
        raise RuntimeError("runtime HTTP must use plain loopback HTTP")
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("runtime HTTP is restricted to loopback")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("loopback URLs cannot contain credentials")
    if parsed.query or parsed.fragment:
        raise RuntimeError("loopback URLs cannot contain query or fragment")
    return url


def get_text(url: str, timeout: float = 10.0) -> str:
    request = urllib.request.Request(bounded_loopback(url), method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")  # type: ignore[no-any-return]


def get_json(url: str, timeout: float = 10.0) -> dict[str, object]:
    payload = json.loads(get_text(url, timeout=timeout))
    if not isinstance(payload, dict):
        raise RuntimeError("loopback response root must be one JSON object")
    return payload


def post_json(
    url: str,
    payload: dict[str, object],
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> dict[str, object]:
    encoded = canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        bounded_loopback(url),
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        observed = json.loads(response.read().decode("utf-8"))
    if not isinstance(observed, dict):
        raise RuntimeError("loopback response root must be one JSON object")
    return observed


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def require_private_environment() -> None:
    present = tuple(name for name in CREDENTIAL_ENV_NAMES if os.environ.get(name))
    if present:
        raise DiagnosticFailure(
            "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
            "credential-bearing environment variables are prohibited",
        )
    if os.environ.get("AURAGATEWAY_CUSTOMER_DATA_PRESENT") == "1":
        raise DiagnosticFailure(
            "P3_P6_PRIVACY_BOUNDARY_VIOLATION",
            "customer data is prohibited",
        )


def safe_directory_sha256(root: Path, maximum_bytes: int) -> str:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("expected one real directory")
    entries: list[dict[str, object]] = []
    total = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise RuntimeError("directory contains a symbolic link")
        if path.is_dir():
            continue
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode):
            raise RuntimeError("directory contains a non-regular member")
        total += path.stat().st_size
        if total > maximum_bytes:
            raise RuntimeError("directory exceeds the byte budget")
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if not entries:
        raise RuntimeError("directory is empty")
    envelope = {"schema_version": "1.0.0", "files": entries}
    return sha256_text(canonical_json(envelope))


def discover_one_directory(name: str) -> Path:
    matches = tuple(
        path.resolve()
        for path in INPUT_ROOT.rglob(name)
        if path.is_dir() and not path.is_symlink()
    )
    unique = tuple(dict.fromkeys(matches))
    if len(unique) != 1:
        raise RuntimeError(f"expected one {name} directory; observed {len(unique)}")
    return unique[0]


def discover_model_snapshot() -> Path:
    matches = tuple(
        path.parent.resolve()
        for path in INPUT_ROOT.rglob(f"snapshots/{MODEL_REVISION}/config.json")
        if path.is_file() and not path.is_symlink()
    )
    unique = tuple(dict.fromkeys(matches))
    if len(unique) != 1:
        raise RuntimeError(
            "expected one exact expanded model snapshot; "
            f"observed {len(unique)}"
        )
    snapshot = unique[0]
    if safe_directory_sha256(snapshot, MAX_MODEL_BYTES) != MODEL_SNAPSHOT_SHA256:
        raise RuntimeError("model snapshot identity drifted")
    return snapshot


def prepare_model_home(snapshot: Path) -> tuple[Path, Path]:
    model_home = SCRATCH_ROOT / "model_home"
    destination = (
        model_home
        / "hub"
        / "models--Qwen--Qwen2.5-0.5B-Instruct"
        / "snapshots"
        / MODEL_REVISION
    )
    if model_home.exists():
        raise RuntimeError("writable model home already exists")
    total = 0
    files: list[tuple[Path, Path]] = []
    for path in sorted(snapshot.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise RuntimeError("model snapshot contains a symbolic link")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            raise RuntimeError("model snapshot contains a non-regular member")
        total += path.stat().st_size
        if total > MAX_MODEL_BYTES:
            raise RuntimeError("model snapshot exceeds the copy budget")
        files.append((path, destination / path.relative_to(snapshot)))
    if not files:
        raise RuntimeError("model snapshot is empty")
    for source, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
    if safe_directory_sha256(destination, MAX_MODEL_BYTES) != MODEL_SNAPSHOT_SHA256:
        raise RuntimeError("writable model snapshot identity drifted")
    return model_home, destination


def validate_wheelhouse(root: Path) -> None:
    for name, expected in EXPECTED_CONTROL_HASHES.items():
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"wheelhouse control file missing: {name}")
        if file_sha256(path) != expected:
            raise RuntimeError(f"wheelhouse control identity drifted: {name}")
    manifest = json.loads((root / "sha256_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("wheelhouse checksum manifest is invalid")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 200:
        raise RuntimeError("wheelhouse manifest entry count drifted")
    verified = 0
    wheels = 0
    for raw in entries:
        if not isinstance(raw, dict):
            raise RuntimeError("wheelhouse manifest entry is invalid")
        name = raw.get("path")  # type: ignore[assignment]
        digest = raw.get("sha256")
        size = raw.get("size_bytes")
        if not isinstance(name, str):
            raise RuntimeError("wheelhouse manifest path is invalid")
        if not isinstance(digest, str) or not isinstance(size, int):
            raise RuntimeError("wheelhouse manifest identity is invalid")
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"wheelhouse member missing: {name}")
        if file_sha256(path) != digest or path.stat().st_size != size:
            raise RuntimeError(f"wheelhouse member drifted: {name}")
        verified += 1
        if path.suffix == ".whl":
            wheels += 1
    if verified != 200 or wheels != 196:
        raise RuntimeError("wheelhouse verification counts drifted")


class BoundedCapture:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.buffer = bytearray()
        self.observed = 0
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.finalized = False

    def start(self, source: object) -> None:
        if source is None:
            return
        if self.thread is not None:
            raise RuntimeError("capture has already been started")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(
            target=self.consume,
            args=(source,),
            daemon=True,
        )
        self.thread.start()

    def consume(self, source: object) -> None:
        try:
            while True:
                chunk = source.read(8192)  # type: ignore[attr-defined]
                if not chunk:
                    break
                with self.lock:
                    self.observed += len(chunk)
                    self.buffer.extend(chunk)
                    overflow = len(self.buffer) - MAX_STREAM_BYTES
                    if overflow > 0:
                        del self.buffer[:overflow]
                    self.path.write_bytes(bytes(self.buffer))
        finally:
            source.close()  # type: ignore[attr-defined]

    def finalize(self, timeout_seconds: float = 5.0) -> None:
        if self.thread is not None:
            self.thread.join(timeout=timeout_seconds)
            if self.thread.is_alive():
                raise RuntimeError("capture thread did not finalize")
        self.finalized = True

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            payload = bytes(self.buffer)
            thread_alive = (
                False if self.thread is None else self.thread.is_alive()
            )
            return {
                "observed_bytes": self.observed,
                "retained_bytes": len(payload),
                "tail_sha256": sha256_bytes(payload),
                "capture_finalized": self.finalized,
                "capture_thread_alive": thread_alive,
            }

    def text(self) -> str:
        with self.lock:
            return bytes(self.buffer).decode("utf-8", errors="replace")


def sanitize_excerpt(value: str) -> str:
    bounded = value[-MAX_INSTALL_EXCERPT_CHARACTERS:]
    replacements = {
        str(INPUT_ROOT): "<input>",
        str(WORK_ROOT): "<working>",
        os.environ.get("HOME", ""): "<home>",
    }
    for source, replacement in replacements.items():
        if source:
            bounded = bounded.replace(source, replacement)
    return bounded


def disk_snapshot(path: Path) -> dict[str, int]:
    usage = shutil.disk_usage(path)
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _structural_target_runtime_symlink_contract(
    member: Path,
    raw_target: str,
    resolved_target: Path,
    target_root_resolved: Path,
    target_is_real_directory: bool,
) -> bool:
    expected_member = TARGET_ROOT / "lib64"
    expected_target = target_root_resolved / "lib"
    if member != expected_member:
        return False
    if raw_target != "lib":
        return False
    if not target_is_real_directory:
        return False
    if resolved_target != expected_target:
        return False
    try:
        resolved_target.relative_to(target_root_resolved)
    except ValueError:
        return False
    return True


def _is_allowed_target_runtime_structural_symlink(member: Path) -> bool:
    expected_target = TARGET_ROOT / "lib"
    if member != TARGET_ROOT / "lib64":
        return False
    if not expected_target.is_dir() or expected_target.is_symlink():
        return False
    try:
        raw_target = os.readlink(member)
        target_root_resolved = TARGET_ROOT.resolve(strict=True)
        resolved_target = member.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    return _structural_target_runtime_symlink_contract(
        member,
        raw_target,
        resolved_target,
        target_root_resolved,
        True,
    )


def directory_snapshot(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "exists": False,
            "file_count": 0,
            "size_bytes": 0,
        }
    if not path.is_dir() or path.is_symlink():
        raise RuntimeError("target runtime path is not one real directory")
    file_count = 0
    size_bytes = 0
    for member in path.rglob("*"):
        if member.is_symlink():
            if _is_allowed_target_runtime_structural_symlink(member):
                continue
            raise RuntimeError("target runtime contains a symbolic link")
        if member.is_dir():
            continue
        if not stat.S_ISREG(member.stat().st_mode):
            raise RuntimeError("target runtime contains a non-regular member")
        file_count += 1
        size_bytes += member.stat().st_size
    return {
        "exists": True,
        "file_count": file_count,
        "size_bytes": size_bytes,
    }



def install_failure_signals(stdout_tail: str, stderr_tail: str) -> tuple[str, ...]:
    text = (stdout_tail + "\n" + stderr_tail).lower()
    signals: list[str] = []
    patterns = (
        ("no space left on device", "DISK_EXHAUSTION_SIGNAL"),
        ("these packages do not match the hashes", "HASH_MISMATCH_SIGNAL"),
        ("hashes are required", "HASH_REQUIREMENT_SIGNAL"),
        ("no matching distribution found", "DISTRIBUTION_UNAVAILABLE_SIGNAL"),
        ("could not find a version that satisfies", "DISTRIBUTION_UNAVAILABLE_SIGNAL"),
        ("not a supported wheel on this platform", "UNSUPPORTED_WHEEL_SIGNAL"),
        ("resolutionimpossible", "DEPENDENCY_RESOLUTION_SIGNAL"),
        ("conflicting dependencies", "DEPENDENCY_RESOLUTION_SIGNAL"),
    )
    for phrase, signal in patterns:
        if phrase in text and signal not in signals:
            signals.append(signal)
    return tuple(signals)


def run_bounded_process(
    role: str,
    argv: list[str],
    *,
    timeout_seconds: float,
    environment: dict[str, str],
    capture_root: Path,
) -> dict[str, object]:
    started_monotonic = time.monotonic()
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    stdout_capture = BoundedCapture(capture_root / f"{role}.stdout.log")
    stderr_capture = BoundedCapture(capture_root / f"{role}.stderr.log")
    process: subprocess.Popen[bytes] | None = None
    launch_error_type: str | None = None
    launch_error_message: str | None = None
    timed_out = False
    try:
        process = subprocess.Popen(
            argv,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
        )
        stdout_capture.start(process.stdout)
        stderr_capture.start(process.stderr)
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    except OSError as error:
        launch_error_type = type(error).__name__
        launch_error_message = sanitize_excerpt(str(error))
    finally:
        if stdout_capture.thread is not None:
            stdout_capture.thread.join(timeout=5)
        if stderr_capture.thread is not None:
            stderr_capture.thread.join(timeout=5)

    finished_at = datetime.now(UTC).isoformat(timespec="seconds")
    stdout_tail = sanitize_excerpt(stdout_capture.text())
    stderr_tail = sanitize_excerpt(stderr_capture.text())
    returncode = None if process is None else process.returncode
    if launch_error_type is not None:
        process_outcome = "LAUNCH_ERROR"
    elif timed_out:
        process_outcome = "TIMEOUT"
    elif returncode == 0:
        process_outcome = "PASSED"
    else:
        process_outcome = "NONZERO_EXIT"
    return {
        "schema_version": "1.0.0",
        "command_role": role,
        "status": "PASSED" if process_outcome == "PASSED" else "FAILED",
        "process_outcome": process_outcome,
        "argv": [sanitize_excerpt(item) for item in argv],
        "argv_sha256": sha256_text(canonical_json(argv)),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": int((time.monotonic() - started_monotonic) * 1000),
        "returncode": returncode,
        "timed_out": timed_out,
        "launch_error_type": launch_error_type,
        "launch_error_message": launch_error_message,
        "stdout_observed_bytes": stdout_capture.observed,
        "stderr_observed_bytes": stderr_capture.observed,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "failure_signals": install_failure_signals(stdout_tail, stderr_tail),
    }


def install_runtime(
    wheelhouse: Path,
    counters: dict[str, int],
) -> dict[str, object]:
    if TARGET_ROOT.exists():
        raise RuntimeError("target runtime already exists")
    wheels = wheelhouse / "wheels"
    if not wheels.is_dir() or wheels.is_symlink():
        raise RuntimeError("wheelhouse wheels directory is missing or unsafe")

    create_process = run_bounded_process(
        "target_environment_creation",
        [
            sys.executable,
            "-m",
            "venv",
            "--without-pip",
            "--copies",
            str(TARGET_ROOT),
        ],
        timeout_seconds=120.0,
        environment={**os.environ},
        capture_root=SCRATCH_ROOT / "target_environment_logs",
    )
    if create_process["process_outcome"] != "PASSED":
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "isolated target environment creation failed",
        )
    if not TARGET_PYTHON.is_file():
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "isolated target Python executable is unavailable",
        )

    argv = [
        sys.executable,
        "-m",
        "pip",
        "--isolated",
        "--disable-pip-version-check",
        "--python",
        str(TARGET_ROOT),
        "install",
        "--no-index",
        "--no-cache-dir",
        "--no-deps",
        "--find-links",
        str(wheels),
        "--require-hashes",
        "-r",
        str(wheelhouse / "requirements.lock.txt"),
    ]
    environment = {**os.environ}
    environment.pop("PIP_INDEX_URL", None)
    environment.pop("PIP_EXTRA_INDEX_URL", None)
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_CACHE_DIR": "1",
        }
    )

    requirements_lock_sha256 = file_sha256(
        wheelhouse / "requirements.lock.txt"
    )
    wheelhouse_manifest_sha256 = file_sha256(
        wheelhouse / "sha256_manifest.json"
    )
    before_disk = disk_snapshot(WORK_ROOT)
    consume_actions(counters, "runtime_install_attempts")
    process = run_bounded_process(
        "offline_target_runtime_install",
        argv,
        timeout_seconds=1800.0,
        environment=environment,
        capture_root=SCRATCH_ROOT / "install_logs",
    )

    report_path = OUTPUT_ROOT / "runtime_install_report_v1.json"
    report = {
        **process,
        "report_id": (
            "auragateway-p5-p6-exact-runtime-requalification-install-v1"
        ),
        "executor": "BASE_PYTHON_PIP_VENV_TARGET",
        "find_links_scope": "wheelhouse/wheels",
        "requirements_lock_sha256": requirements_lock_sha256,
        "wheelhouse_manifest_sha256": wheelhouse_manifest_sha256,
        "working_disk_before": before_disk,
        "working_disk_after": None,
        "target_runtime_after": None,
        "target_python": str(TARGET_PYTHON),
        "network_access_requested": False,
        "hidden_retry_count": 0,
        "root_cause_review_required": process["status"] != "PASSED",
        "post_install_snapshot_status": "PENDING",
        "post_install_snapshot_error_type": None,
        "post_install_snapshot_safe_message": None,
    }
    write_json(report_path, report)

    outcome = process["process_outcome"]
    if outcome != "PASSED":
        report = {
            **report,
            "post_install_snapshot_status": (
                "NOT_ATTEMPTED_PROCESS_FAILED"
            ),
        }
        write_json(report_path, report)

    if outcome == "LAUNCH_ERROR":
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "offline target-runtime installer could not be launched",
        )
    if outcome == "TIMEOUT":
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "offline target-runtime installation timed out",
        )
    if outcome == "NONZERO_EXIT":
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "offline target-runtime installation returned nonzero",
        )

    try:
        working_disk_after = disk_snapshot(WORK_ROOT)
        target_runtime_after = directory_snapshot(TARGET_ROOT)
    except (OSError, RuntimeError) as error:
        report = {
            **report,
            "status": "FAILED",
            "root_cause_review_required": True,
            "post_install_snapshot_status": "FAILED",
            "post_install_snapshot_error_type": type(error).__name__,
            "post_install_snapshot_safe_message": sanitize_excerpt(str(error)),
        }
        write_json(report_path, report)
        raise

    report = {
        **report,
        "working_disk_after": working_disk_after,
        "target_runtime_after": target_runtime_after,
        "post_install_snapshot_status": "PASSED",
        "post_install_snapshot_error_type": None,
        "post_install_snapshot_safe_message": None,
    }
    write_json(report_path, report)
    return report



def target_library_directories() -> tuple[Path, ...]:
    names = (
        "nvidia/cublas/lib",
        "nvidia/cuda_cupti/lib",
        "nvidia/cuda_nvrtc/lib",
        "nvidia/cuda_runtime/lib",
        "nvidia/cudnn/lib",
        "nvidia/cufft/lib",
        "nvidia/cufile/lib",
        "nvidia/curand/lib",
        "nvidia/cusolver/lib",
        "nvidia/cusparse/lib",
        "nvidia/nccl/lib",
        "nvidia/nvjitlink/lib",
        "nvidia/nvshmem/lib",
    )
    result = tuple(
        path
        for name in names
        if (path := TARGET_SITE / name).is_dir()
    )
    if not result:
        raise RuntimeError("target NVIDIA library directories are unavailable")
    return result


BOOTSTRAP = r"""
import runpy
import site
import sys
import types
from pathlib import Path

target_site = Path(sys.argv.pop(1)).resolve()
module_name = sys.argv.pop(1)

def sentinel(name):
    module = types.ModuleType(name)
    module.__file__ = f"<auragateway-suppressed-{name}>"
    return module

sys.modules["sitecustomize"] = sentinel("sitecustomize")
sys.modules["usercustomize"] = sentinel("usercustomize")
site.main()

cleaned = []
for value in sys.path:
    if not value:
        cleaned.append(value)
        continue
    path = Path(value).resolve()
    is_target = path == target_site or target_site in path.parents
    is_package_path = any(
        part in {"site-packages", "dist-packages"}
        for part in path.parts
    )
    if is_package_path and not is_target:
        continue
    cleaned.append(value)

if str(target_site) not in cleaned:
    cleaned.insert(0, str(target_site))
sys.path[:] = cleaned
sys.argv = [module_name, *sys.argv[1:]]
runpy.run_module(module_name, run_name="__main__")
"""


def controlled_python(module: str, *args: str) -> list[str]:
    if not TARGET_PYTHON.is_file():
        raise RuntimeError("target Python executable is unavailable")
    return [
        str(TARGET_PYTHON),
        "-S",
        "-c",
        BOOTSTRAP,
        str(TARGET_SITE),
        module,
        *args,
    ]


PROHIBITED_LIBRARY_PATH_MARKERS = (
    "/usr/local/cuda/lib64/stubs",
    "/usr/local/cuda/compat",
    "/cuda/lib64/stubs",
    "/cuda/compat",
)


def _is_prohibited_library_path(value: str) -> bool:
    normalized = value.replace("\\", "/").rstrip("/")
    return any(
        marker in normalized
        for marker in PROHIBITED_LIBRARY_PATH_MARKERS
    )


def process_tree_environment(
    gpu_index: int,
    model_home: Path,
) -> dict[str, str]:
    inherited = [
        item
        for item in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
        if item and not _is_prohibited_library_path(item)
    ]
    target_libraries = [str(path) for path in target_library_directories()]
    ordered: list[str] = []
    for item in [*target_libraries, *inherited, REAL_DRIVER_DIRECTORY]:
        if item not in ordered:
            ordered.append(item)
    environment = {**os.environ}
    environment.pop("PYTHONPATH", None)
    environment.pop("LD_PRELOAD", None)
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": str(gpu_index),
            "HF_HOME": str(model_home),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PIP_NO_INDEX": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(TARGET_SITE),
            "LIBRARY_PATH": REAL_DRIVER_DIRECTORY,
            "LDFLAGS": (
                "-L/usr/local/nvidia/lib64 "
                "-Wl,-rpath,/usr/local/nvidia/lib64"
            ),
            "LD_LIBRARY_PATH": os.pathsep.join(ordered),
            "VLLM_ATTENTION_BACKEND": EXPECTED_BACKEND,
        }
    )
    if any(_is_prohibited_library_path(item) for item in ordered):
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "prohibited CUDA stub path survived environment construction",
        )
    return environment


def runtime_environment_report(
    environment: dict[str, str],
) -> dict[str, object]:
    paths = environment["LD_LIBRARY_PATH"].split(os.pathsep)
    target_libraries = [str(path) for path in target_library_directories()]
    return {
        "schema_version": "1.0.0",
        "status": "PASSED",
        "pythonpath_exact_target_site": (
            environment.get("PYTHONPATH") == str(TARGET_SITE)
        ),
        "ld_preload_absent": "LD_PRELOAD" not in environment,
        "prohibited_stub_path_present": any(
            _is_prohibited_library_path(item) for item in paths
        ),
        "target_library_prefix_count": len(target_libraries),
        "target_libraries_precede_inherited": (
            paths[: len(target_libraries)] == target_libraries
        ),
        "real_driver_directory_present": REAL_DRIVER_DIRECTORY in paths,
        "library_path": environment.get("LIBRARY_PATH"),
        "attention_backend": environment.get("VLLM_ATTENTION_BACKEND"),
        "raw_environment_retained": False,
    }


def validate_target_runtime() -> dict[str, object]:
    program = r"""
import importlib
import importlib.metadata
import json
import torch
import transformers
import triton
import vllm

required_native = importlib.import_module("vllm._C_stable_libtorch")
print(json.dumps({
    "torch": torch.__version__,
    "cuda": torch.version.cuda,
    "transformers": importlib.metadata.version("transformers"),
    "triton": importlib.metadata.version("triton"),
    "vllm_distribution": importlib.metadata.version("vllm"),
    "vllm_module": vllm.__version__,
    "required_native_module": required_native.__name__,
    "required_native_module_file": getattr(required_native, "__file__", None),
    "cuda_available": torch.cuda.is_available(),
    "device_name": torch.cuda.get_device_name(0),
    "compute_capability": list(torch.cuda.get_device_capability(0)),
}, separators=(",", ":"), sort_keys=True))
"""
    argv = [
        str(TARGET_PYTHON),
        "-S",
        "-c",
        (
            "import site,sys,types;"
            f"target={str(TARGET_SITE)!r};"
            "sys.modules['sitecustomize']=types.ModuleType('sitecustomize');"
            "sys.modules['usercustomize']=types.ModuleType('usercustomize');"
            "site.main();"
            "sys.path[:]=[target]+[p for p in sys.path if "
            "('site-packages' not in p and 'dist-packages' not in p) or p==target];"
            + program
        ),
    ]
    result = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        env=process_tree_environment(0, OUTPUT_ROOT / "model_home"),
    )
    if result.returncode != 0:
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "target runtime identity validation failed",
        )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    expected = {
        "torch": EXPECTED_TORCH_VERSION,
        "cuda": EXPECTED_TORCH_CUDA,
        "transformers": EXPECTED_TRANSFORMERS_VERSION,
        "triton": EXPECTED_TRITON_VERSION,
        "vllm_distribution": EXPECTED_VLLM_DISTRIBUTION_VERSION,
        "vllm_module": EXPECTED_VLLM_MODULE_VERSION,
        "required_native_module": REQUIRED_NATIVE_MODULE,
        "cuda_available": True,
        "device_name": EXPECTED_GPU_NAME,
        "compute_capability": [7, 5],
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                f"target runtime identity drifted: {key}",
            )
    native_file = payload.get("required_native_module_file")
    if not isinstance(native_file, str) or not _path_within_target(native_file):
        raise DiagnosticFailure(
            "MODEL_CONSTRUCTION_FAILURE",
            "required vLLM native module resolved outside target runtime",
        )
    return payload  # type: ignore[no-any-return]


def _path_within_target(value: str) -> bool:
    path = Path(value).resolve()
    target = TARGET_SITE.resolve()
    return path == target or target in path.parents


def validate_import_closure_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    parent_executable = payload.get("parent_python_executable")
    parent_pythonpath = payload.get("parent_pythonpath")
    child_returncode = payload.get("child_returncode")
    child = payload.get("child")
    if not isinstance(parent_executable, str):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "import-closure parent executable is invalid",
        )
    if parent_pythonpath != str(TARGET_SITE):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "import-closure parent PYTHONPATH drifted",
        )
    if child_returncode != 0 or not isinstance(child, dict):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "nested import-closure child failed",
        )
    child_executable = child.get("python_executable")
    child_pythonpath = child.get("pythonpath")
    modules = child.get("modules")
    if not isinstance(child_executable, str):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "import-closure child executable is invalid",
        )
    if child_pythonpath != str(TARGET_SITE):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "import-closure child PYTHONPATH drifted",
        )
    if not isinstance(modules, dict):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "import-closure module inventory is invalid",
        )
    if set(modules) != set(IMPORT_CLOSURE_MODULES):
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "import-closure module inventory drifted",
        )
    origins: dict[str, str] = {}
    for name in IMPORT_CLOSURE_MODULES:
        item = modules.get(name)
        if not isinstance(item, dict):
            raise DiagnosticFailure(
                "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
                f"import-closure module record is invalid: {name}",
            )
        origin = item.get("origin")
        if not isinstance(origin, str) or not _path_within_target(origin):
            raise DiagnosticFailure(
                "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
                f"critical module resolved outside target site: {name}",
            )
        origins[name] = origin
    return {
        "parent_python_executable": parent_executable,
        "parent_pythonpath": parent_pythonpath,
        "child_python_executable": child_executable,
        "child_pythonpath": child_pythonpath,
        "critical_module_origins": origins,
        "all_critical_origins_within_target_site": True,
    }


def validate_process_tree_import_closure(
    counters: dict[str, int],
) -> dict[str, object]:
    if not EXPECTED_CHILD_PYTHON.is_file():
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "expected nested Python executable is unavailable",
        )
    child_program = r"""
import importlib
import json
import os
import sys

module_names = (
    "vllm",
    "torch",
    "triton",
    "transformers",
    "vllm.model_executor.models.registry",
)
modules = {}
for name in module_names:
    module = importlib.import_module(name)
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        raise RuntimeError(f"module origin is unavailable: {name}")
    modules[name] = {"origin": origin}
print(json.dumps({
    "python_executable": sys.executable,
    "pythonpath": os.environ.get("PYTHONPATH"),
    "modules": modules,
}, separators=(",", ":"), sort_keys=True))
"""
    parent_program = r"""
import json
import os
import subprocess
import sys

child_program = sys.argv[1]
child_executable = sys.argv[2]
completed = subprocess.run(
    [child_executable, "-c", child_program],
    check=False,
    capture_output=True,
    text=True,
    timeout=90,
)
child_payload = None
if completed.stdout.strip():
    child_payload = json.loads(completed.stdout.strip().splitlines()[-1])
print(json.dumps({
    "parent_python_executable": sys.executable,
    "parent_pythonpath": os.environ.get("PYTHONPATH"),
    "child_returncode": completed.returncode,
    "child": child_payload,
}, separators=(",", ":"), sort_keys=True))
if completed.stderr:
    print(completed.stderr[-16000:], file=sys.stderr)
raise SystemExit(0 if completed.returncode == 0 else 3)
"""
    environment = process_tree_environment(
        0,
        SCRATCH_ROOT / "import_closure_model_home",
    )
    capture_root = SCRATCH_ROOT / "import_closure_logs"
    consume_actions(counters, "runtime_import_closure_probes")
    process = run_bounded_process(
        "runtime_process_tree_import_closure",
        [
            str(EXPECTED_CHILD_PYTHON),
            "-c",
            parent_program,
            child_program,
            str(EXPECTED_CHILD_PYTHON),
        ],
        timeout_seconds=120.0,
        environment=environment,
        capture_root=capture_root,
    )
    stdout_path = (
        capture_root / "runtime_process_tree_import_closure.stdout.log"
    )
    payload: dict[str, object] | None = None
    if stdout_path.is_file():
        lines = tuple(
            line
            for line in stdout_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
            if line.strip()
        )
        if lines:
            raw = json.loads(lines[-1])
            if isinstance(raw, dict):
                payload = raw
    report = {
        **process,
        "report_id": (
            "auragateway-p5-p6-exact-runtime-requalification-runtime-import-closure-v1"
        ),
        "target_site": str(TARGET_SITE),
        "pythonpath_exact_target_site": (
            environment.get("PYTHONPATH") == str(TARGET_SITE)
        ),
        "inherited_pythonpath_replaced": True,
        "nested_interpreter_depth": 2,
        "critical_modules": list(IMPORT_CLOSURE_MODULES),
        "model_loads_consumed": 0,
        "worker_starts_consumed": 0,
        "network_access_requested": False,
        "hidden_retry_count": 0,
    }
    if process["status"] != "PASSED" or payload is None:
        write_json(
            OUTPUT_ROOT / "runtime_import_closure_report_v1.json",
            report,
        )
        raise DiagnosticFailure(
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED",
            "nested target-runtime import-closure probe failed",
        )
    validated = validate_import_closure_payload(payload)
    report.update(validated)
    report["status"] = "PASSED"
    report["decision"] = "PROCESS_TREE_IMPORT_CLOSURE_PASSED"
    write_json(
        OUTPUT_ROOT / "runtime_import_closure_report_v1.json",
        report,
    )
    return report

def backend_marker_evidence_from_texts(
    stdout_text: str,
    stderr_text: str,
) -> dict[str, object] | None:
    matches: list[dict[str, object]] = []
    for stream_name, payload in (
        ("stdout", stdout_text),
        ("stderr", stderr_text),
    ):
        for line_number, raw_line in enumerate(payload.splitlines(), start=1):
            normalized = raw_line.strip()
            if EXPECTED_BACKEND_LOG_MARKER not in normalized:
                continue
            lowered = normalized.lower()
            if any(token in lowered for token in BACKEND_MARKER_EXCLUDED_TOKENS):
                continue
            if BACKEND_MARKER_LOG_PREFIX_PATTERN.fullmatch(normalized) is None:
                continue
            matches.append(
                {
                    "stream": stream_name,
                    "line_number": line_number,
                    "marker": EXPECTED_BACKEND_LOG_MARKER,
                    "normalized_line_sha256": sha256_text(normalized),
                    "normalized_line_length": len(normalized),
                    "line_local_match": True,
                    "cli_echo_rejected": True,
                }
            )
    if len(matches) > 1:
        raise RuntimeError("backend marker evidence is ambiguous")
    return None if not matches else matches[0]


class Worker:
    def __init__(
        self,
        worker_id: str,
        gpu_index: int,
        port: int,
        model_home: Path,
        snapshot: Path,
        generation: int = 1,
    ) -> None:
        self.worker_id = worker_id
        self.gpu_index = gpu_index
        self.port = port
        self.model_home = model_home
        self.snapshot = snapshot
        self.generation = generation
        self.process: subprocess.Popen[bytes] | None = None
        self.backend_marker_poll_count = 0
        self.backend_evidence: dict[str, object] | None = None
        self.started_at: str | None = None
        self.parent_pid: int | None = None
        self.process_start_ticks: int | None = None
        self.gpu_identity: dict[str, object] | None = None
        self.memory_before_start_mib: int | None = None
        self.teardown_report: dict[str, object] | None = None
        self.stdout = BoundedCapture(
            LOG_ROOT / f"{worker_id}-g{generation}.stdout.log"
        )
        self.stderr = BoundedCapture(
            LOG_ROOT / f"{worker_id}-g{generation}.stderr.log"
        )
        self.argv = controlled_python(
            "vllm.entrypoints.openai.api_server",
            "--model",
            MODEL_REPOSITORY,
            "--revision",
            MODEL_REVISION,
            "--tokenizer",
            MODEL_REPOSITORY,
            "--tokenizer-revision",
            MODEL_REVISION,
            "--served-model-name",
            SERVED_MODEL_NAME,
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
            "--block-size",
            str(CACHE_BLOCK_SIZE),
            "--attention-backend",
            EXPECTED_BACKEND,
            "--no-enable-log-requests",
        )
        self.env = process_tree_environment(gpu_index, model_home)

    @property
    def instance_id(self) -> str:
        return f"{self.worker_id}-g{self.generation}"

    def start(self, counters: dict[str, int]) -> None:
        if self.process is not None:
            raise RuntimeError("worker has already been started")
        if port_open(self.port):
            raise RuntimeError(f"worker port already open: {self.port}")
        inventory = gpu_inventory()
        identity = inventory.get(self.gpu_index)
        if identity is None:
            raise RuntimeError("worker GPU identity is unavailable")
        consume_actions(counters, "worker_starts", "model_loads")
        self.memory_before_start_mib = int(  # type: ignore[call-overload]
            identity["memory_used_mib"]
        )
        self.gpu_identity = identity
        self.parent_pid = os.getpid()
        self.started_at = datetime.now(UTC).isoformat(timespec="milliseconds")
        self.process = subprocess.Popen(
            self.argv,
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
        )
        self.process_start_ticks = process_start_ticks(self.process.pid)
        self.stdout.start(self.process.stdout)
        self.stderr.start(self.process.stderr)

    def wait_ready(self) -> None:
        if self.process is None:
            raise RuntimeError("worker was not started")
        for index in range(MAX_HEALTH_POLLS):
            returncode = self.process.poll()
            if returncode is not None:
                raise RuntimeError(
                    f"{self.instance_id} exited before readiness: {returncode}"
                )
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/health",
                    method="GET",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                pass
            if index + 1 == MAX_HEALTH_POLLS:
                raise RuntimeError(
                    f"{self.instance_id} failed bounded readiness polling"
                )
            time.sleep(HEALTH_POLL_SECONDS)

    def validate_model(self) -> None:
        payload = get_json(f"http://127.0.0.1:{self.port}/v1/models")
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != 1:
            raise RuntimeError("served-model inventory is invalid")
        item = data[0]
        if not isinstance(item, dict) or item.get("id") != SERVED_MODEL_NAME:
            raise RuntimeError("served-model identity drifted")

    def backend_marker_evidence(self) -> dict[str, object] | None:
        return backend_marker_evidence_from_texts(
            self.stdout.text(),
            self.stderr.text(),
        )

    def backend_marker(self) -> bool:
        return self.backend_marker_evidence() is not None

    def wait_backend_marker(self) -> None:
        if self.process is None:
            raise RuntimeError("worker was not started")
        for index in range(20):
            evidence = self.backend_marker_evidence()
            if evidence is not None:
                self.backend_marker_poll_count = index + 1
                self.backend_evidence = evidence
                return
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"{self.instance_id} exited before backend realization"
                )
            time.sleep(0.25)
        raise RuntimeError(
            f"{self.instance_id} explicit backend marker was not observed"
        )

    def metric_snapshot(self) -> MetricSnapshotObservation:
        raw_metrics = get_text(
            f"http://127.0.0.1:{self.port}/metrics"
        )
        return metric_snapshot(raw_metrics)

    def report(self) -> dict[str, object]:
        if self.process is None:
            raise RuntimeError("worker was not started")
        if self.gpu_identity is None:
            raise RuntimeError("worker GPU identity was not captured")
        evidence = self.backend_evidence or self.backend_marker_evidence()
        return {
            "worker_id": self.worker_id,
            "worker_instance_id": self.instance_id,
            "generation": self.generation,
            "gpu_index": self.gpu_index,
            "gpu_identity": self.gpu_identity,
            "port": self.port,
            "pid": self.process.pid,
            "parent_pid": self.parent_pid,
            "process_start_ticks": self.process_start_ticks,
            "started_at": self.started_at,
            "argv_sha256": sha256_text(canonical_json(self.argv)),
            "explicit_attention_backend": EXPECTED_BACKEND,
            "backend_log_marker_observed": evidence is not None,
            "backend_marker_evidence": evidence,
            "backend_marker_poll_count": self.backend_marker_poll_count,
            "stdout": self.stdout.snapshot(),
            "stderr": self.stderr.snapshot(),
        }

    def stop_and_report(self, reason: str) -> dict[str, object]:
        if self.teardown_report is not None:
            return self.teardown_report
        if self.process is None:
            self.stdout.finalize()
            self.stderr.finalize()
            self.teardown_report = {
                "worker_instance_id": self.instance_id,
                "status": "NOT_STARTED",
                "reason": reason,
            }
            return self.teardown_report

        root_pid = self.process.pid
        tree_before: set[int] = {root_pid}
        gpu_pids_before: set[int] = set()
        teardown_error_type: str | None = None
        teardown_error_message: str | None = None
        try:
            tree_before = descendants(root_pid, process_parent_map())
            gpu_processes_before = compute_processes()
            gpu_pids_before = {
                pid for pid in tree_before if pid in gpu_processes_before
            }
        except (OSError, RuntimeError, ValueError) as error:
            teardown_error_type = type(error).__name__
            teardown_error_message = sanitize_excerpt(str(error))[:512]

        termination_method = "ALREADY_EXITED"
        if self.process.poll() is None:
            termination_method = "SIGTERM"
            self.process.terminate()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            termination_method = "SIGKILL"
            self.process.kill()
            self.process.wait(timeout=10)

        self.stdout.finalize()
        self.stderr.finalize()

        process_tree_absent = False
        gpu_processes_absent = False
        port_closed = False
        memory_returned = False
        memory_after_stop_mib: int | None = None
        polls = 0
        for index in range(MAX_TEARDOWN_POLLS):
            polls = index + 1
            current_parents = process_parent_map()
            current_gpu_processes = compute_processes()
            current_pids = set(current_parents)
            process_tree_absent = not bool(tree_before & current_pids)
            gpu_processes_absent = not bool(
                tree_before & set(current_gpu_processes)
            )
            port_closed = not port_open(self.port)
            if self.gpu_identity is not None:
                memory_after_stop_mib = gpu_memory_used_mib(
                    str(self.gpu_identity["uuid"])
                )
            if (
                self.memory_before_start_mib is not None
                and memory_after_stop_mib is not None
            ):
                memory_returned = (
                    memory_after_stop_mib
                    <= self.memory_before_start_mib
                    + GPU_MEMORY_RETURN_TOLERANCE_MIB
                )
            if (
                process_tree_absent
                and gpu_processes_absent
                and port_closed
                and memory_returned
            ):
                break
            time.sleep(TEARDOWN_POLL_SECONDS)

        captures_finalized = (
            bool(self.stdout.snapshot()["capture_finalized"])
            and bool(self.stderr.snapshot()["capture_finalized"])
            and not bool(self.stdout.snapshot()["capture_thread_alive"])
            and not bool(self.stderr.snapshot()["capture_thread_alive"])
        )
        status = (
            "PASSED"
            if (
                process_tree_absent
                and gpu_processes_absent
                and port_closed
                and memory_returned
                and captures_finalized
                and teardown_error_type is None
            )
            else "FAILED"
        )
        self.teardown_report = {
            "schema_version": "1.0.0",
            "report_id": "auragateway-p5-p6-exact-runtime-requalification-worker-teardown-v1",
            "worker_id": self.worker_id,
            "worker_instance_id": self.instance_id,
            "generation": self.generation,
            "reason": reason,
            "status": status,
            "root_pid": root_pid,
            "process_tree_pids_before": sorted(tree_before),
            "gpu_process_pids_before": sorted(gpu_pids_before),
            "returncode": self.process.returncode,
            "termination_method": termination_method,
            "process_tree_absent_after": process_tree_absent,
            "gpu_processes_absent_after": gpu_processes_absent,
            "port_closed_after": port_closed,
            "capture_threads_finalized": captures_finalized,
            "memory_before_start_mib": self.memory_before_start_mib,
            "memory_after_stop_mib": memory_after_stop_mib,
            "memory_return_tolerance_mib": GPU_MEMORY_RETURN_TOLERANCE_MIB,
            "memory_returned_within_tolerance": memory_returned,
            "bounded_poll_count": polls,
            "teardown_error_type": teardown_error_type,
            "teardown_error_message": teardown_error_message,
        }
        return self.teardown_report

    def failure_diagnostics(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "worker_instance_id": self.instance_id,
            "generation": self.generation,
            "gpu_index": self.gpu_index,
            "gpu_identity": self.gpu_identity,
            "port": self.port,
            "returncode": (
                None if self.process is None else self.process.poll()
            ),
            "pid": None if self.process is None else self.process.pid,
            "parent_pid": self.parent_pid,
            "process_start_ticks": self.process_start_ticks,
            "started_at": self.started_at,
            "argv_sha256": sha256_text(canonical_json(self.argv)),
            "pythonpath": self.env.get("PYTHONPATH"),
            "pythonpath_exact_target_site": (
                self.env.get("PYTHONPATH") == str(TARGET_SITE)
            ),
            "backend_marker_evidence": self.backend_evidence,
            "stdout": self.stdout.snapshot(),
            "stderr": self.stderr.snapshot(),
            "stdout_tail": sanitize_excerpt(self.stdout.text()),
            "stderr_tail": sanitize_excerpt(self.stderr.text()),
            "teardown": self.teardown_report,
        }


PROMETHEUS_LINE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{(?P<labels>.*)\})?\s+"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$"
)
PROMETHEUS_LABEL = re.compile(
    r'(?:^|,)(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)="(?P<value>(?:\\.|[^"])*)"'
)

METRIC_SAMPLE_NAMES = {
    "prefix_cache_queries": "vllm:prefix_cache_queries_total",
    "prefix_cache_hits": "vllm:prefix_cache_hits_total",
    "local_compute": "vllm:prompt_tokens_by_source_total",
    "local_cache_hit": "vllm:prompt_tokens_by_source_total",
    "external_kv_transfer": "vllm:prompt_tokens_by_source_total",
    "cached_prompt_tokens": "vllm:prompt_tokens_cached_total",
    "newly_computed_prefill_tokens": (
        "vllm:request_prefill_kv_computed_tokens_sum"
    ),
}

METRIC_SOURCE_LABELS = {
    "local_compute": "local_compute",
    "local_cache_hit": "local_cache_hit",
    "external_kv_transfer": "external_kv_transfer",
}


def _unescape_prometheus_label(value: str) -> str:
    return (
        value.replace(r"\\", "\\")
        .replace(r"\"", '"')
        .replace(r"\n", "\n")
    )


def _parse_prometheus_labels(payload: str) -> tuple[tuple[str, str], ...]:
    if not payload:
        return ()
    position = 0
    items: list[tuple[str, str]] = []
    while position < len(payload):
        match = PROMETHEUS_LABEL.match(payload, position)
        if match is None:
            raise DiagnosticAmbiguity(
                "METRIC_SEMANTIC_FAILURE",
                "Prometheus labels could not be parsed losslessly",
            )
        items.append(
            (
                match.group("key"),
                _unescape_prometheus_label(match.group("value")),
            )
        )
        position = match.end()
    return tuple(sorted(items))


def parse_metric_samples(payload: str) -> tuple[RawMetricSample, ...]:
    samples: list[RawMetricSample] = []
    for raw_line in payload.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = PROMETHEUS_LINE.fullmatch(stripped)
        if match is None:
            continue
        name = match.group("name")
        if name not in set(METRIC_SAMPLE_NAMES.values()):
            continue
        try:
            value = float(match.group("value"))
        except ValueError as error:
            raise DiagnosticAmbiguity(
                "METRIC_SEMANTIC_FAILURE",
                "relevant Prometheus metric value is invalid",
            ) from error
        if value < 0:
            raise DiagnosticAmbiguity(
                "METRIC_SEMANTIC_FAILURE",
                "relevant Prometheus counter or histogram sum is negative",
            )
        samples.append(
            RawMetricSample(
                name=name,
                labels=_parse_prometheus_labels(match.group("labels") or ""),
                value=value,
            )
        )
    return tuple(samples)


def _labels_dict(sample: RawMetricSample) -> dict[str, str]:
    return dict(sample.labels)


def _metric_value(
    samples: tuple[RawMetricSample, ...],
    semantic_role: str,
) -> float:
    name = METRIC_SAMPLE_NAMES[semantic_role]
    source = METRIC_SOURCE_LABELS.get(semantic_role)
    matches: list[RawMetricSample] = []
    for sample in samples:
        if sample.name != name:
            continue
        labels = _labels_dict(sample)
        if labels.get("model_name") != SERVED_MODEL_NAME:
            continue
        if labels.get("engine") != "0":
            continue
        if source is not None and labels.get("source") != source:
            continue
        if source is None and "source" in labels:
            continue
        matches.append(sample)
    if len(matches) != 1:
        raise DiagnosticAmbiguity(
            "METRIC_ATTRIBUTION_AMBIGUOUS",
            (
                f"expected exactly one metric series for {semantic_role}; "
                f"observed={len(matches)}"
            ),
        )
    return matches[0].value


def metric_snapshot(payload: str) -> MetricSnapshotObservation:
    samples = parse_metric_samples(payload)
    observation = MetricSnapshotObservation(
        prefix_cache_queries=_metric_value(samples, "prefix_cache_queries"),
        prefix_cache_hits=_metric_value(samples, "prefix_cache_hits"),
        local_compute=_metric_value(samples, "local_compute"),
        local_cache_hit=_metric_value(samples, "local_cache_hit"),
        external_kv_transfer=_metric_value(samples, "external_kv_transfer"),
        cached_prompt_tokens=_metric_value(samples, "cached_prompt_tokens"),
        newly_computed_prefill_tokens=_metric_value(
            samples,
            "newly_computed_prefill_tokens",
        ),
    )
    if abs(
        observation.cached_prompt_tokens
        - (
            observation.local_cache_hit
            + observation.external_kv_transfer
        )
    ) > 1e-9:
        raise DiagnosticAmbiguity(
            "METRIC_SEMANTIC_FAILURE",
            "cached-prompt-token source invariant is violated",
        )
    return observation


def metric_delta(
    before: MetricSnapshotObservation,
    after: MetricSnapshotObservation,
) -> MetricDeltaObservation:
    values: dict[str, float] = {}
    for field_name in (
        "prefix_cache_queries",
        "prefix_cache_hits",
        "local_compute",
        "local_cache_hit",
        "external_kv_transfer",
        "cached_prompt_tokens",
        "newly_computed_prefill_tokens",
    ):
        delta = float(getattr(after, field_name)) - float(
            getattr(before, field_name)
        )
        if delta < -1e-9:
            raise DiagnosticAmbiguity(
                "METRIC_SEMANTIC_FAILURE",
                f"metric counter regressed: {field_name}",
            )
        values[field_name] = 0.0 if abs(delta) <= 1e-9 else delta
    observation = MetricDeltaObservation(**values)
    if abs(
        observation.cached_prompt_tokens
        - (
            observation.local_cache_hit
            + observation.external_kv_transfer
        )
    ) > 1e-9:
        raise DiagnosticAmbiguity(
            "METRIC_SEMANTIC_FAILURE",
            "request metric-delta cached-source invariant is violated",
        )
    return observation


def _prefix_context(prefix_variant: str) -> str:
    if prefix_variant == "A":
        return SYNTHETIC_CACHE_CONTEXT_A
    if prefix_variant == "B":
        return SYNTHETIC_CACHE_CONTEXT_B
    raise RuntimeError("unknown prefix variant")


def request_messages(prefix_variant: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _prefix_context(prefix_variant)},
        {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
        {"role": "user", "content": EXPECTED_OBJECT_CANONICAL},
    ]


def request_payload(prefix_variant: str) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": request_messages(prefix_variant),
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def tokenize_payload(prefix_variant: str) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": request_messages(prefix_variant),
        "add_generation_prompt": True,
        "continue_final_message": False,
        "add_special_tokens": False,
        "return_token_strs": False,
    }


def tokenize_request(
    worker: Worker,
    request_role: str,
    prefix_variant: str,
) -> TokenIdentityObservation:
    response = post_json(
        f"http://127.0.0.1:{worker.port}/tokenize",
        tokenize_payload(prefix_variant),
    )
    raw_tokens = response.get("tokens")
    count = response.get("count")
    if (
        not isinstance(raw_tokens, list)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(raw_tokens)
    ):
        raise DiagnosticAmbiguity(
            "TOKENIZER_ARTIFACT_FAILURE",
            "server tokenization response shape is invalid",
        )
    tokens: list[int] = []
    for raw_token in raw_tokens:
        if isinstance(raw_token, bool) or not isinstance(raw_token, int):
            raise DiagnosticAmbiguity(
                "TOKENIZER_ARTIFACT_FAILURE",
                "server tokenization returned a non-integer token id",
            )
        if raw_token < 0:
            raise DiagnosticAmbiguity(
                "TOKENIZER_ARTIFACT_FAILURE",
                "server tokenization returned a negative token id",
            )
        tokens.append(raw_token)
    token_bytes = canonical_json(tokens).encode("utf-8")
    return TokenIdentityObservation(
        request_role=request_role,
        prefix_variant=prefix_variant,
        token_count=len(tokens),
        token_sha256=sha256_bytes(token_bytes),
        token_ids=tuple(tokens),
    )


def common_prefix_token_count(
    left: TokenIdentityObservation,
    right: TokenIdentityObservation,
) -> int:
    count = 0
    for left_token, right_token in zip(left.token_ids, right.token_ids, strict=False):
        if left_token != right_token:
            break
        count += 1
    return count


def cacheable_common_prefix_bound(
    left: TokenIdentityObservation,
    right: TokenIdentityObservation,
) -> int:
    common = common_prefix_token_count(left, right)
    return (common // CACHE_BLOCK_SIZE) * CACHE_BLOCK_SIZE


def token_identity_evidence(
    observation: TokenIdentityObservation,
) -> dict[str, object]:
    return {
        "request_role": observation.request_role,
        "prefix_variant": observation.prefix_variant,
        "token_count": observation.token_count,
        "token_sha256": observation.token_sha256,
        "token_ids": list(observation.token_ids),
    }


def observe_structured_response(
    content: str,
    expected_json: str,
) -> SemanticObservation:
    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError as error:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "expected semantic contract is invalid JSON",
        ) from error
    if not isinstance(expected, dict):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "expected semantic contract root must be one object",
        )

    response_sha = sha256_text(content)
    try:
        observed = json.loads(content)
    except json.JSONDecodeError:
        return SemanticObservation(
            state=SemanticState.INVALID_JSON,
            response_content_sha256=response_sha,
            parsed_json_sha256=None,
            valid_json=False,
            object_root=False,
            exact_match=False,
        )

    parsed_sha = sha256_text(canonical_json(observed))
    if not isinstance(observed, dict):
        return SemanticObservation(
            state=SemanticState.NON_OBJECT_JSON,
            response_content_sha256=response_sha,
            parsed_json_sha256=parsed_sha,
            valid_json=True,
            object_root=False,
            exact_match=False,
        )
    if observed != expected:
        return SemanticObservation(
            state=SemanticState.VALID_JSON_MISMATCH,
            response_content_sha256=response_sha,
            parsed_json_sha256=parsed_sha,
            valid_json=True,
            object_root=True,
            exact_match=False,
        )
    return SemanticObservation(
        state=SemanticState.EXACT_MATCH,
        response_content_sha256=response_sha,
        parsed_json_sha256=parsed_sha,
        valid_json=True,
        object_root=True,
        exact_match=True,
    )


def run_structured_request(
    worker: Worker,
    request_role: str,
    prefix_variant: str,
    counters: dict[str, int],
) -> dict[str, object]:
    token_identity = tokenize_request(
        worker,
        request_role=request_role,
        prefix_variant=prefix_variant,
    )
    before = worker.metric_snapshot()
    consume_actions(counters, "model_requests")
    request_id = (
        f"{request_role.lower()}-"
        f"{worker.worker_id}-g{worker.generation}-"
        f"{counters['model_requests']}"
    )
    response = post_json(
        f"http://127.0.0.1:{worker.port}/v1/chat/completions",
        request_payload(prefix_variant),
    )
    after = worker.metric_snapshot()
    delta = metric_delta(before, after)
    usage = response.get("usage")
    choices = response.get("choices")
    if not isinstance(usage, dict):
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            "response usage is missing",
        )
    if not isinstance(choices, list) or len(choices) != 1:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "response choices are invalid",
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "response choice is invalid",
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "response message is invalid",
        )
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "response content is empty",
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason != "stop":
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "response finish reason is not stop",
        )
    output_tokens = usage.get("completion_tokens")
    prompt_tokens = usage.get("prompt_tokens")
    if (
        isinstance(output_tokens, bool)
        or not isinstance(output_tokens, int)
        or not 1 <= output_tokens <= 32
    ):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "completion token budget drifted",
        )
    if (
        isinstance(prompt_tokens, bool)
        or not isinstance(prompt_tokens, int)
        or prompt_tokens <= 0
    ):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "prompt token count is invalid",
        )
    semantic = observe_structured_response(
        content,
        EXPECTED_OBJECT_CANONICAL,
    )
    route = RouteObservation(
        request_id=request_id,
        request_role=request_role,
        intended_worker=worker.worker_id,
        realized_worker=worker.worker_id,
        worker_generation=worker.generation,
        endpoint_port=worker.port,
        metric_endpoint_identity=sha256_text(
            f"http://127.0.0.1:{worker.port}/metrics"
        ),
        route_reason="DIRECT_LOOPBACK_ENDPOINT",
        fallback_reason=None,
        output_sha256=semantic.response_content_sha256,
    )
    return {
        "request_id": request_id,
        "request_role": request_role,
        "prefix_variant": prefix_variant,
        "token_identity": token_identity,
        "response_content_sha256": semantic.response_content_sha256,
        "parsed_json_sha256": semantic.parsed_json_sha256,
        "semantic_observation": semantic,
        "semantic_state": semantic.state.value,
        "semantic_exact_match": semantic.exact_match,
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": output_tokens,
        "metric_delta": delta,
        "route_observation": route,
    }


def gpu_inventory() -> dict[int, dict[str, object]]:
    result = subprocess.run(
        [
            "nvidia-smi",
            (
                "--query-gpu="
                "index,uuid,pci.bus_id,name,compute_cap,memory.used"
            ),
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("GPU identity command failed")
    inventory: dict[int, dict[str, object]] = {}
    for line in result.stdout.splitlines():
        parts = tuple(part.strip() for part in line.split(","))
        if len(parts) != 6:
            raise RuntimeError("GPU identity output is malformed")
        index = int(parts[0])
        name = "Tesla T4" if parts[3] == "NVIDIA T4" else parts[3]
        if index not in {0, 1}:
            raise RuntimeError("unexpected GPU index")
        if name != EXPECTED_GPU_NAME or parts[4] != EXPECTED_COMPUTE_CAPABILITY:
            raise RuntimeError("GPU identity drifted")
        inventory[index] = {
            "index": index,
            "uuid": parts[1],
            "pci_bus_id": parts[2],
            "name": name,
            "compute_capability": parts[4],
            "memory_used_mib": int(parts[5]),
        }
    if set(inventory) != {0, 1}:
        raise RuntimeError("expected exactly two GPUs")
    return inventory


def gpu_uuid_map() -> dict[int, str]:
    return {
        index: str(identity["uuid"])
        for index, identity in gpu_inventory().items()
    }


def gpu_memory_used_mib(gpu_uuid: str) -> int:
    for identity in gpu_inventory().values():
        if identity["uuid"] == gpu_uuid:
            return int(identity["memory_used_mib"])  # type: ignore[no-any-return, call-overload]
    raise RuntimeError("GPU UUID is unavailable")


def process_start_ticks(pid: int) -> int:
    stat_path = Path(f"/proc/{pid}/stat")
    payload = stat_path.read_text(encoding="utf-8")
    closing = payload.rfind(")")
    if closing < 0:
        raise RuntimeError("process stat record is malformed")
    fields = payload[closing + 2 :].split()
    if len(fields) <= 19:
        raise RuntimeError("process stat record is incomplete")
    return int(fields[19])


def process_parent_map() -> dict[int, int]:
    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid="],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError("process topology command failed")
    mapping: dict[int, int] = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2:
            mapping[int(fields[0])] = int(fields[1])
    return mapping


def descendants(root_pid: int, parents: dict[int, int]) -> set[int]:
    result = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in result and pid not in result:
                result.add(pid)
                changed = True
    return result


def compute_processes() -> dict[int, str]:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,gpu_uuid",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("GPU process command failed")
    mapping: dict[int, str] = {}
    for line in result.stdout.splitlines():
        parts = tuple(part.strip() for part in line.split(","))
        if len(parts) == 2 and parts[0].isdigit():
            mapping[int(parts[0])] = parts[1]
    return mapping


def validate_process_isolation(
    worker_1: Worker,
    worker_2: Worker,
) -> dict[str, object]:
    if worker_1.process is None or worker_2.process is None:
        raise DiagnosticFailure(
            "P6_PROCESS_ISOLATION_FAILED",
            "workers are not running",
        )
    parents = process_parent_map()
    worker_1_pids = descendants(worker_1.process.pid, parents)
    worker_2_pids = descendants(worker_2.process.pid, parents)
    overlap = worker_1_pids & worker_2_pids
    if overlap:
        raise DiagnosticFailure(
            "P6_PROCESS_ISOLATION_FAILED",
            "worker process trees overlap",
        )
    return {
        "worker_1_root_pid": worker_1.process.pid,
        "worker_2_root_pid": worker_2.process.pid,
        "worker_1_process_count": len(worker_1_pids),
        "worker_2_process_count": len(worker_2_pids),
        "worker_process_trees_disjoint": True,
    }


def validate_gpu_isolation(
    worker_1: Worker,
    worker_2: Worker,
) -> dict[str, object]:
    if worker_1.process is None or worker_2.process is None:
        raise DiagnosticFailure(
            "P6_GPU_ISOLATION_FAILED",
            "workers are not running",
        )
    uuids = gpu_uuid_map()
    parents = process_parent_map()
    gpu_processes = compute_processes()
    worker_1_pids = descendants(worker_1.process.pid, parents)
    worker_2_pids = descendants(worker_2.process.pid, parents)
    worker_1_gpu_pids = {
        pid for pid in worker_1_pids if gpu_processes.get(pid) == uuids[0]
    }
    worker_2_gpu_pids = {
        pid for pid in worker_2_pids if gpu_processes.get(pid) == uuids[1]
    }
    wrong_1 = {
        pid for pid in worker_1_pids if gpu_processes.get(pid) == uuids[1]
    }
    wrong_2 = {
        pid for pid in worker_2_pids if gpu_processes.get(pid) == uuids[0]
    }
    if not worker_1_gpu_pids or not worker_2_gpu_pids:
        raise DiagnosticFailure(
            "P6_GPU_ISOLATION_FAILED",
            "GPU process attribution is incomplete",
        )
    if wrong_1 or wrong_2:
        raise DiagnosticFailure(
            "P6_GPU_ISOLATION_FAILED",
            "worker GPU process isolation failed",
        )
    return {
        "worker_1_gpu_process_count": len(worker_1_gpu_pids),
        "worker_2_gpu_process_count": len(worker_2_gpu_pids),
        "worker_1_bound_to_gpu_0": True,
        "worker_2_bound_to_gpu_1": True,
    }


CRITICAL_NATIVE_TOKENS = (
    "libcuda",
    "libcudart",
    "libcublas",
    "libcusparse",
    "libnvjitlink",
    "libcudnn",
    "libnccl",
    "libnvrtc",
    "/torch/",
    "/triton/",
    "/vllm/",
)
TARGET_REQUIRED_NATIVE_TOKENS = ("libcusparse", "libnvjitlink")


def native_paths_for_process(pid: int) -> set[str]:
    maps_path = Path(f"/proc/{pid}/maps")
    if not maps_path.is_file():
        raise DiagnosticFailure(
            "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
            "process native-map evidence is unavailable",
        )
    paths: set[str] = set()
    for line in maps_path.read_text(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or not fields[5].startswith("/"):
            continue
        observed = fields[5].replace(" (deleted)", "")
        lowered = observed.lower()
        if any(token in lowered for token in CRITICAL_NATIVE_TOKENS):
            paths.add(observed)
    return paths


def classify_native_origin(path: str) -> str:
    normalized = str(Path(path).resolve()).replace("\\", "/")
    target_prefix = str(TARGET_ROOT.resolve()).replace("\\", "/").rstrip("/") + "/"
    real_driver_prefix = (
        str(Path(REAL_DRIVER_DIRECTORY).resolve()).replace("\\", "/").rstrip("/")
        + "/"
    )
    lowered = normalized.lower()
    if _is_prohibited_library_path(normalized):
        return "REJECTED_STUB"
    if normalized.startswith(target_prefix):
        return "TARGET_RUNTIME"
    if normalized.startswith(real_driver_prefix) and "libcuda" in lowered:
        return "REAL_NVIDIA_DRIVER"
    return "HOST_OR_AMBIENT_LIBRARY"


def sanitized_native_path(path: str) -> str:
    normalized = str(Path(path).resolve())
    target_prefix = str(TARGET_ROOT.resolve())
    driver_prefix = str(Path(REAL_DRIVER_DIRECTORY).resolve())
    if normalized.startswith(target_prefix):
        return "<target_runtime>" + normalized[len(target_prefix):]
    if normalized.startswith(driver_prefix):
        return "<real_driver>" + normalized[len(driver_prefix):]
    return sanitize_excerpt(normalized)


def validate_native_origin_closure(
    *workers: Worker,
) -> dict[str, object]:
    if not workers:
        raise DiagnosticFailure(
            "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
            "no workers were supplied for native-origin inspection",
        )
    parents = process_parent_map()
    reports: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    required: dict[str, list[dict[str, object]]] = {
        token: [] for token in TARGET_REQUIRED_NATIVE_TOKENS
    }
    for worker in workers:
        if worker.process is None:
            raise DiagnosticFailure(
                "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
                "worker process disappeared during native-origin inspection",
            )
        process_ids = sorted(descendants(worker.process.pid, parents))
        for pid in process_ids:
            for path in sorted(native_paths_for_process(pid)):
                classification = classify_native_origin(path)
                item = {
                    "worker_id": worker.worker_id,
                    "worker_instance_id": worker.instance_id,
                    "pid": pid,
                    "path": sanitized_native_path(path),
                    "classification": classification,
                }
                reports.append(item)
                if classification == "REJECTED_STUB":
                    rejected.append(item)
                lowered = Path(path).name.lower()
                for token in TARGET_REQUIRED_NATIVE_TOKENS:
                    if token in lowered:
                        required[token].append(item)
    if not reports:
        raise DiagnosticFailure(
            "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
            "no critical native origins were observed",
        )
    if rejected:
        raise DiagnosticFailure(
            "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
            "one or more prohibited CUDA stub origins were observed",
        )
    required_status: dict[str, dict[str, object]] = {}
    for token, observations in required.items():
        all_from_target = bool(observations) and all(
            item["classification"] == "TARGET_RUNTIME"
            for item in observations
        )
        required_status[token] = {
            "observed": bool(observations),
            "all_from_target": all_from_target,
            "observation_count": len(observations),
        }
        if not all_from_target:
            raise DiagnosticFailure(
                "P3_P6_NATIVE_ORIGIN_CLOSURE_FAILED",
                f"required target native origin failed: {token}",
            )
    return {
        "schema_version": "1.0.0",
        "report_id": (
            "auragateway-p5-p6-exact-runtime-requalification-runtime-native-origin-v1"
        ),
        "status": "PASSED",
        "decision": "RUNTIME_NATIVE_ORIGIN_CLOSURE_PASSED",
        "observations": reports,
        "required_target_origins": required_status,
        "rejected_origin_count": 0,
        "cuda_stub_origin_observed": False,
        "ambient_non_stub_origins_permitted": True,
    }


def new_p6_checkpoint(counters: dict[str, int]) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "probe_id": "P6",
        "status": "IN_PROGRESS",
        "current_stage": "P6_STARTED",
        "events": [],
        "worker_request_counters": {
            "worker_1": {"attempted": 0, "completed": 0},
            "worker_2": {"attempted": 0, "completed": 0},
        },
        "global_model_requests": counters["model_requests"],
        "starting_model_requests": counters["model_requests"],
        "raw_prompt_logged": False,
        "raw_output_logged": False,
    }


def persist_p6_checkpoint(
    checkpoint: dict[str, object],
    stage: str,
    counters: dict[str, int],
    details: dict[str, object] | None = None,
) -> None:
    events = checkpoint.get("events")
    if not isinstance(events, list):
        raise DiagnosticFailure(
            "P6_CHECKPOINT_SERIALIZATION_FAILED",
            "P6 checkpoint event ledger is invalid",
        )
    event = {
        "stage": stage,
        "observed_at": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "global_model_requests": counters["model_requests"],
        "details": details or {},
    }
    events.append(event)
    checkpoint["current_stage"] = stage
    checkpoint["global_model_requests"] = counters["model_requests"]
    try:
        write_json(
            OUTPUT_ROOT / "p6_stage_checkpoint_report_v1.json",
            checkpoint,
        )
    except Exception as error:
        raise DiagnosticFailure(
            "P6_CHECKPOINT_SERIALIZATION_FAILED",
            "P6 checkpoint serialization failed",
        ) from error


def request_counter(
    checkpoint: dict[str, object],
    worker_id: str,
) -> dict[str, int]:
    counters = checkpoint.get("worker_request_counters")
    if not isinstance(counters, dict):
        raise DiagnosticFailure(
            "P6_CHECKPOINT_SERIALIZATION_FAILED",
            "P6 worker request counter map is invalid",
        )
    item = counters.get(worker_id)
    if not isinstance(item, dict):
        raise DiagnosticFailure(
            "P6_CHECKPOINT_SERIALIZATION_FAILED",
            "P6 worker request counter is invalid",
        )
    attempted = item.get("attempted")
    completed = item.get("completed")
    if not isinstance(attempted, int) or not isinstance(completed, int):
        raise DiagnosticFailure(
            "P6_CHECKPOINT_SERIALIZATION_FAILED",
            "P6 worker request counter values are invalid",
        )
    return item


def validate_response_envelope(response: dict[str, object]) -> dict[str, object]:
    usage = response.get("usage")
    choices = response.get("choices")
    model = response.get("model")
    if model != SERVED_MODEL_NAME:
        raise RuntimeError("response model identity drifted")
    if not isinstance(usage, dict):
        raise RuntimeError("response usage is missing")
    if not isinstance(choices, list) or len(choices) != 1:
        raise RuntimeError("response choices are invalid")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise RuntimeError("response choice is invalid")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("response message is invalid")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise RuntimeError("response content is empty")
    output_tokens = usage.get("completion_tokens")
    prompt_tokens = usage.get("prompt_tokens")
    if not isinstance(output_tokens, int) or not 1 <= output_tokens <= 32:
        raise RuntimeError("completion token budget drifted")
    if not isinstance(prompt_tokens, int) or prompt_tokens <= 0:
        raise RuntimeError("prompt token count is invalid")
    return {
        "response_content_sha256": sha256_text(content),
        "response_content_length": len(content),
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": output_tokens,
        "model_identity_valid": True,
        "response_envelope_valid": True,
    }


def _all_metric_values_zero(delta: MetricDeltaObservation) -> bool:
    return all(
        abs(float(getattr(delta, name))) <= 1e-9
        for name in (
            "prefix_cache_queries",
            "prefix_cache_hits",
            "local_compute",
            "local_cache_hit",
            "external_kv_transfer",
            "cached_prompt_tokens",
            "newly_computed_prefill_tokens",
        )
    )


def run_attributed_request(
    target: Worker,
    non_target: Worker,
    request_role: str,
    prefix_variant: str,
    counters: dict[str, int],
    checkpoint: dict[str, object],
) -> dict[str, object]:
    if target.worker_id == non_target.worker_id:
        raise DiagnosticFailure(
            "P6_ROUTE_REALIZATION_FAILURE",
            "target and non-target workers must be distinct",
        )
    target_counter = request_counter(checkpoint, target.worker_id)
    target_counter["attempted"] += 1
    persist_p6_checkpoint(
        checkpoint,
        f"{request_role}_ATTEMPTED",
        counters,
        {
            "request_role": request_role,
            "intended_worker": target.worker_id,
            "worker_instance_id": target.instance_id,
            "port": target.port,
            "prefix_variant": prefix_variant,
        },
    )
    before_target = target.metric_snapshot()
    before_non_target = non_target.metric_snapshot()
    try:
        request = run_structured_request(
            target,
            request_role,
            prefix_variant,
            counters,
        )
    except DiagnosticAmbiguity:
        raise
    except Exception as error:
        raise DiagnosticFailure(
            "REQUEST_EXECUTION_FAILURE",
            sanitize_excerpt(str(error))[:512] or "route request failed",
        ) from error
    after_target = target.metric_snapshot()
    after_non_target = non_target.metric_snapshot()
    target_delta = metric_delta(before_target, after_target)
    non_target_delta = metric_delta(before_non_target, after_non_target)

    if target_delta.total_prompt_tokens <= 0:
        raise DiagnosticAmbiguity(
            "METRIC_ATTRIBUTION_AMBIGUOUS",
            f"{request_role} did not change target-worker prompt metrics",
        )
    if not _all_metric_values_zero(non_target_delta):
        raise DiagnosticAmbiguity(
            "METRIC_ATTRIBUTION_AMBIGUOUS",
            f"{request_role} changed non-target-worker request metrics",
        )
    target_counter["completed"] += 1
    request["target_metric_delta"] = asdict(target_delta)
    request["non_target_metric_delta"] = asdict(non_target_delta)
    request["route_acknowledged"] = True
    persist_p6_checkpoint(
        checkpoint,
        f"{request_role}_ATTRIBUTED",
        counters,
        {
            "request_role": request_role,
            "realized_worker": target.worker_id,
            "route_acknowledged": True,
        },
    )
    return request


def route_isolation(
    worker_1: Worker,
    worker_2: Worker,
    counters: dict[str, int],
    checkpoint: dict[str, object],
) -> dict[str, object]:
    cross_worker = run_attributed_request(
        worker_2,
        worker_1,
        "CROSS_WORKER_COLD",
        "A",
        counters,
        checkpoint,
    )
    retention = run_attributed_request(
        worker_1,
        worker_2,
        "WORKER1_RETENTION",
        "A",
        counters,
        checkpoint,
    )

    expected_total = sum(
        request_counter(checkpoint, worker_id)["attempted"]
        for worker_id in ("worker_1", "worker_2")
    )
    starting_model_requests = checkpoint.get("starting_model_requests")
    if not isinstance(starting_model_requests, int):
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "P6 starting request count is invalid",
        )
    p6_request_total = counters["model_requests"] - starting_model_requests
    if expected_total != 2 or p6_request_total != expected_total:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "P6 request counters do not reconcile",
        )
    for worker_id in ("worker_1", "worker_2"):
        item = request_counter(checkpoint, worker_id)
        if item["attempted"] != 1 or item["completed"] != 1:
            raise DiagnosticFailure(
                "REQUEST_RECONCILIATION_FAILURE",
                "per-worker P6 request counters do not reconcile",
            )
    persist_p6_checkpoint(
        checkpoint,
        "REQUEST_COUNTERS_RECONCILED",
        counters,
        {"p6_request_total": p6_request_total},
    )
    return {
        "cross_worker_request": cross_worker,
        "worker_1_retention_request": retention,
        "worker_1_route_isolated": True,
        "worker_2_route_isolated": True,
        "request_counters_reconciled": True,
    }



def _request_metric_delta(payload: dict[str, object]) -> MetricDeltaObservation:
    observation = payload.get("metric_delta")
    if not isinstance(observation, MetricDeltaObservation):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "request metric delta is not a typed observation",
        )
    return observation


def _request_token_identity(payload: dict[str, object]) -> TokenIdentityObservation:
    observation = payload.get("token_identity")
    if not isinstance(observation, TokenIdentityObservation):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "request token identity is not a typed observation",
        )
    return observation


def _request_route(payload: dict[str, object]) -> RouteObservation:
    observation = payload.get("route_observation")
    if not isinstance(observation, RouteObservation):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "request route is not a typed observation",
        )
    return observation


def _request_semantic_observation(
    payload: dict[str, object],
) -> SemanticObservation:
    observation = payload.get("semantic_observation")
    if not isinstance(observation, SemanticObservation):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "request semantic state is not a typed observation",
        )
    return observation


def _same_token_identity(
    left: TokenIdentityObservation,
    right: TokenIdentityObservation,
) -> bool:
    return (
        left.token_count == right.token_count
        and left.token_sha256 == right.token_sha256
        and left.token_ids == right.token_ids
    )


def decide_p5(
    cold: dict[str, object],
    warm: dict[str, object],
    negative_prefix: dict[str, object],
    post_reset_cold: dict[str, object],
    cross_worker_cold: dict[str, object],
) -> BehaviorDecision:
    cold_metric = _request_metric_delta(cold)
    warm_metric = _request_metric_delta(warm)
    negative_metric = _request_metric_delta(negative_prefix)
    reset_metric = _request_metric_delta(post_reset_cold)
    cross_metric = _request_metric_delta(cross_worker_cold)

    cold_tokens = _request_token_identity(cold)
    warm_tokens = _request_token_identity(warm)
    negative_tokens = _request_token_identity(negative_prefix)
    reset_tokens = _request_token_identity(post_reset_cold)
    cross_tokens = _request_token_identity(cross_worker_cold)

    reasons: list[str] = []
    failed = False

    for label, metric in (
        ("BASE_COLD", cold_metric),
        ("BASE_WARM", warm_metric),
        ("NEGATIVE_PREFIX", negative_metric),
        ("POST_RESET_COLD", reset_metric),
        ("CROSS_WORKER_COLD", cross_metric),
    ):
        if metric.external_kv_transfer != 0:
            failed = True
            reasons.append(f"{label} observed external KV transfer")

    if not (
        _same_token_identity(cold_tokens, warm_tokens)
        and _same_token_identity(cold_tokens, reset_tokens)
        and _same_token_identity(cold_tokens, cross_tokens)
    ):
        failed = True
        reasons.append("prefix A token identity drifted across P5 controls")

    if _same_token_identity(cold_tokens, negative_tokens):
        failed = True
        reasons.append("NEGATIVE_PREFIX did not diverge at token level")

    negative_bound = cacheable_common_prefix_bound(
        cold_tokens,
        negative_tokens,
    )

    if cold_metric.local_cache_hit != 0:
        failed = True
        reasons.append("BASE_COLD unexpectedly observed local cache-hit tokens")
    if cold_metric.local_compute <= 0:
        failed = True
        reasons.append("BASE_COLD did not observe local compute")

    if warm_metric.local_cache_hit <= 0:
        failed = True
        reasons.append("BASE_WARM did not observe local cache-hit tokens")
    if warm_metric.prefix_cache_hits <= 0:
        failed = True
        reasons.append("BASE_WARM did not observe prefix-cache hits")
    if warm_metric.newly_computed_prefill_tokens >= (
        cold_metric.newly_computed_prefill_tokens
    ):
        failed = True
        reasons.append("BASE_WARM did not reduce computed prefill tokens")

    if negative_metric.local_cache_hit > float(negative_bound):
        failed = True
        reasons.append(
            "NEGATIVE_PREFIX reuse exceeded its cacheable common-prefix bound"
        )
    if negative_metric.local_cache_hit >= warm_metric.local_cache_hit:
        failed = True
        reasons.append(
            "NEGATIVE_PREFIX reuse was not lower than BASE_WARM reuse"
        )

    if reset_metric.local_cache_hit != 0:
        failed = True
        reasons.append("POST_RESET_COLD inherited prohibited local cache state")
    if reset_metric.local_compute <= 0:
        failed = True
        reasons.append("POST_RESET_COLD did not recompute prompt tokens")

    if cross_metric.local_cache_hit != 0:
        failed = True
        reasons.append("CROSS_WORKER_COLD inherited prohibited local cache state")
    if cross_metric.local_compute <= 0:
        failed = True
        reasons.append("CROSS_WORKER_COLD did not compute prompt tokens")

    if failed:
        return BehaviorDecision(
            capability="P5_PREFIX_CACHE_BEHAVIOR",
            state=BehaviorState.FAIL,
            failure_class="P5_BEHAVIOR_FAILURE",
            reasons=tuple(reasons),
        )

    return BehaviorDecision(
        capability="P5_PREFIX_CACHE_BEHAVIOR",
        state=BehaviorState.PASS,
        failure_class=None,
        reasons=(
            "cache-specific token evidence satisfied all frozen P5 controls",
            f"negative_prefix_cacheable_common_prefix_bound={negative_bound}",
        ),
    )


def decide_p6(
    cross_worker_cold: dict[str, object],
    worker_1_retention: dict[str, object],
    process_isolation: dict[str, object],
    gpu_isolation: dict[str, object],
) -> BehaviorDecision:
    cross_route = _request_route(cross_worker_cold)
    retention_route = _request_route(worker_1_retention)
    cross_metric = _request_metric_delta(cross_worker_cold)
    retention_metric = _request_metric_delta(worker_1_retention)

    reasons: list[str] = []
    failed = False

    if process_isolation.get("worker_process_trees_disjoint") is not True:
        failed = True
        reasons.append("worker process trees are not disjoint")
    if gpu_isolation.get("worker_1_bound_to_gpu_0") is not True:
        failed = True
        reasons.append("worker 1 GPU realization is invalid")
    if gpu_isolation.get("worker_2_bound_to_gpu_1") is not True:
        failed = True
        reasons.append("worker 2 GPU realization is invalid")

    if (
        cross_route.intended_worker != "worker_2"
        or cross_route.realized_worker != "worker_2"
        or cross_route.worker_generation != 1
    ):
        failed = True
        reasons.append("CROSS_WORKER_COLD route realization drifted")
    if (
        retention_route.intended_worker != "worker_1"
        or retention_route.realized_worker != "worker_1"
        or retention_route.worker_generation != 2
    ):
        failed = True
        reasons.append("WORKER1_RETENTION route realization drifted")

    for route in (cross_route, retention_route):
        if route.route_reason != "DIRECT_LOOPBACK_ENDPOINT":
            failed = True
            reasons.append(f"{route.request_role} used an unexpected route reason")
        if route.fallback_reason is not None:
            failed = True
            reasons.append(f"{route.request_role} reported fallback")

    if cross_metric.local_cache_hit != 0:
        failed = True
        reasons.append("worker 2 inherited prohibited worker-1 local cache state")
    if retention_metric.local_cache_hit <= 0:
        failed = True
        reasons.append("worker 1 did not retain attributable local cache state")

    if failed:
        return BehaviorDecision(
            capability="P6_WORKER_STATE_ISOLATION",
            state=BehaviorState.FAIL,
            failure_class="P6_BEHAVIOR_FAILURE",
            reasons=tuple(reasons),
        )

    return BehaviorDecision(
        capability="P6_WORKER_STATE_ISOLATION",
        state=BehaviorState.PASS,
        failure_class=None,
        reasons=(
            "worker identity, route realization, state isolation, and retention passed",
        ),
    )


def evidence_projection(
    decision: BehaviorDecision,
    observations: dict[str, object],
) -> EvidenceProjection:
    return EvidenceProjection(
        decision=decision,
        public_summary={
            "capability": decision.capability,
            "state": decision.state.value,
            "failure_class": decision.failure_class,
            "reasons": list(decision.reasons),
            "observations": observations,
        },
    )


def decision_invariant_under_projection_policy(
    decision: BehaviorDecision,
) -> bool:
    first = evidence_projection(
        decision,
        {"display_path": "<working>", "excerpt_limit": 256},
    )
    second = evidence_projection(
        decision,
        {"display_path": "<redacted>", "excerpt_limit": 4096},
    )
    return first.decision == second.decision == decision


def request_public_evidence(payload: dict[str, object]) -> dict[str, object]:
    metric = _request_metric_delta(payload)
    token = _request_token_identity(payload)
    route = _request_route(payload)
    semantic = _request_semantic_observation(payload)
    return {
        "request_id": payload["request_id"],
        "request_role": payload["request_role"],
        "prefix_variant": payload["prefix_variant"],
        "token_identity": token_identity_evidence(token),
        "metric_delta": asdict(metric),
        "route_observation": asdict(route),
        "semantic_observation": asdict(semantic),
        "response_content_sha256": semantic.response_content_sha256,
        "parsed_json_sha256": semantic.parsed_json_sha256,
        "prompt_tokens": payload["prompt_tokens"],
        "completion_tokens": payload["completion_tokens"],
    }


def bundle_outputs() -> dict[str, object]:
    required_before_manifest = set(OUTPUT_NAMES) - {"bundle_manifest_v1.json"}
    observed_before_manifest = {
        path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()
    }
    missing = required_before_manifest - observed_before_manifest
    unexpected = observed_before_manifest - required_before_manifest
    if missing or unexpected:
        raise RuntimeError(
            "runtime evidence output contract drifted: "
            + canonical_json(
                {
                    "missing": sorted(missing),
                    "unexpected": sorted(unexpected),
                }
            )
        )
    entries = []
    for name in OUTPUT_NAMES:
        path = OUTPUT_ROOT / name
        if not path.is_file():
            continue
        entries.append(
            {
                "path": name,
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest_payload = {
        "schema_version": "1.0.0",
        "diagnostic_id": "auragateway-p5-p6-exact-runtime-requalification-runtime-qualification-v1",
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "members": [
            item for item in entries if item["path"] != "bundle_manifest_v1.json"
        ],
        "scratch_directories_included": False,
        "worker_log_directory_included": False,
    }
    write_json(OUTPUT_ROOT / "bundle_manifest_v1.json", manifest_payload)
    with zipfile.ZipFile(
        EVIDENCE_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in OUTPUT_NAMES:
            path = OUTPUT_ROOT / name
            if path.is_file():
                archive.write(path, arcname=name)
    if EVIDENCE_ZIP.stat().st_size > MAX_EVIDENCE_ZIP_BYTES:
        raise RuntimeError("runtime evidence ZIP exceeds the byte budget")
    return {
        "evidence_zip": str(EVIDENCE_ZIP),
        "evidence_zip_sha256": file_sha256(EVIDENCE_ZIP),
        "evidence_zip_size_bytes": EVIDENCE_ZIP.stat().st_size,
    }



def write_capability_terminal_reports(
    completed: list[str],
    failed_capability: str | None,
    failure_class: str | None,
    counters: dict[str, int],
) -> None:
    reports = (
        ("C1", "c1_model_construction_report_v1.json"),
        ("C2", "c2_worker_startup_report_v1.json"),
        ("C3", "c3_single_request_report_v1.json"),
        ("C4", "c4_output_contract_report_v1.json"),
        ("P5", "p5_cache_behavior_report_v1.json"),
        ("P6", "p6_worker_state_isolation_report_v1.json"),
    )
    for capability_id, name in reports:
        path = OUTPUT_ROOT / name
        if path.is_file():
            continue
        is_failed = failed_capability == capability_id
        blocked_by = None
        if not is_failed:
            blocked_by = (
                failed_capability
                or failure_class
                or "UPSTREAM_PRECONDITION"
            )
        write_json(
            path,
            {
                "schema_version": "1.0.0",
                "capability_id": capability_id,
                "status": "FAILED" if is_failed else "NOT_RUN",
                "decision_state": (
                    BehaviorState.FAIL.value if is_failed else None
                ),
                "blocked_by": blocked_by,
                "failure_class": failure_class,
                "completed_capabilities_before_terminal_state": completed,
                "global_model_request_count": counters["model_requests"],
                "raw_prompt_logged": False,
                "raw_output_logged": False,
                "public_evidence_used_as_semantic_input": False,
            },
        )

def ensure_runtime_source_identity_report(
    failure_code: str | None,
) -> None:
    path = OUTPUT_ROOT / "runtime_source_identity_report_v1.json"
    if path.is_file():
        return
    write_json(
        path,
        {
            "schema_version": "1.0.0",
            "report_id": (
                "auragateway-p5-p6-exact-runtime-requalification-"
                "runtime-source-identity-v1"
            ),
            "status": "FAILED",
            "decision": "EXECUTED_RUNTIME_SCRIPT_IDENTITY_UNVERIFIED",
            "notebook_name": NOTEBOOK_NAME,
            "source_main_commit": SOURCE_MAIN_COMMIT,
            "executed_runtime_script_sha256": None,
            "wrapper_hash_verification_passed": False,
            "failure_code": (
                failure_code
                or "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH"
            ),
        },
    )


def ensure_install_report(failure_code: str | None) -> None:
    path = OUTPUT_ROOT / "runtime_install_report_v1.json"
    if path.is_file():
        return
    write_json(
        path,
        {
            "schema_version": "1.0.0",
            "report_id": "auragateway-p5-p6-exact-runtime-requalification-runtime-install-v1",
            "command_role": "offline_target_runtime_install",
            "status": "NOT_RUN",
            "process_outcome": "NOT_RUN",
            "reason": failure_code or "runtime installation was not reached",
            "returncode": None,
            "timed_out": False,
            "stdout_tail": "",
            "stderr_tail": "",
            "failure_signals": [],
            "network_access_requested": False,
            "hidden_retry_count": 0,
            "model_copy_completed_before_install": False,
            "root_cause_review_required": False,
        },
    )


def ensure_import_closure_report(failure_code: str | None) -> None:
    path = OUTPUT_ROOT / "runtime_import_closure_report_v1.json"
    if path.is_file():
        return
    write_json(
        path,
        {
            "schema_version": "1.0.0",
            "report_id": (
                "auragateway-p5-p6-exact-runtime-requalification-runtime-import-closure-v1"
            ),
            "status": "NOT_RUN",
            "process_outcome": "NOT_RUN",
            "reason": (
                failure_code
                or "runtime import-closure probe was not reached"
            ),
            "target_site": str(TARGET_SITE),
            "pythonpath_exact_target_site": False,
            "nested_interpreter_depth": 2,
            "model_loads_consumed": 0,
            "worker_starts_consumed": 0,
            "network_access_requested": False,
            "hidden_retry_count": 0,
        },
    )

def cleanup_scratch() -> dict[str, object]:
    before: dict[str, object]
    status = "PASSED"
    error_type: str | None = None
    safe_message: str | None = None
    try:
        before = directory_snapshot(SCRATCH_ROOT)
    except (OSError, RuntimeError) as error:
        before = {
            "exists": True,
            "file_count": 0,
            "size_bytes": 0,
            "snapshot_failed": True,
        }
        status = "FAILED"
        error_type = type(error).__name__
        safe_message = sanitize_excerpt(str(error))
    try:
        if SCRATCH_ROOT.exists():
            shutil.rmtree(SCRATCH_ROOT)
    except OSError as error:
        status = "FAILED"
        if error_type is None:
            error_type = type(error).__name__
            safe_message = sanitize_excerpt(str(error))
    report = {
        "schema_version": "1.0.0",
        "report_id": "auragateway-p5-p6-exact-runtime-requalification-scratch-cleanup-v1",
        "status": status,
        "scratch_before": before,
        "scratch_exists_after": SCRATCH_ROOT.exists(),
        "error_type": error_type,
        "safe_message": safe_message,
    }
    write_json(OUTPUT_ROOT / "scratch_cleanup_report_v1.json", report)
    return report


def main() -> int:
    if OUTPUT_ROOT.exists() or SCRATCH_ROOT.exists() or EVIDENCE_ZIP.exists():
        raise RuntimeError(
            "P5/P6 mechanism-admission successor output or scratch path already exists"
        )
    OUTPUT_ROOT.mkdir(parents=True)
    LOG_ROOT.mkdir()
    SCRATCH_ROOT.mkdir()

    counters = {
        "kaggle_sessions": 1,
        "runtime_install_attempts": 0,
        "runtime_import_closure_probes": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "hidden_retries": 0,
        "external_spend": 0,
    }
    completed: list[str] = []
    teardown_reports: list[dict[str, object]] = []
    worker_1: Worker | None = None
    worker_2: Worker | None = None
    failure: dict[str, object] | None = None
    p6_checkpoint: dict[str, object] | None = None
    authorization: dict[str, object] | None = None
    terminal_state = "FAILED"
    active_failure_code = "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH"
    failed_capability: str | None = None
    p5_decision: BehaviorDecision | None = None
    p6_decision: BehaviorDecision | None = None

    try:
        source_identity = write_runtime_source_identity_report()

        active_failure_code = "P3_P6_PRIVACY_BOUNDARY_VIOLATION"
        require_private_environment()

        active_failure_code = "AUTHORITY_FAILURE"
        authorization = require_transaction_bound_context()

        active_failure_code = "P3_P6_WHEELHOUSE_INVALID"
        wheelhouse = discover_one_directory(RUNTIME_OUTPUT_DIRECTORY)
        validate_wheelhouse(wheelhouse)

        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        source_snapshot = discover_model_snapshot()

        active_failure_code = "P3_P6_RUNTIME_INSTALL_FAILED"
        install_runtime(wheelhouse, counters)

        active_failure_code = "P3_P6_PLATFORM_IDENTITY_MISMATCH"
        runtime_identity = validate_target_runtime()
        runtime_environment = process_tree_environment(
            0,
            SCRATCH_ROOT / "environment_report_model_home",
        )
        environment_report = runtime_environment_report(runtime_environment)
        if environment_report["prohibited_stub_path_present"] is not False:
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                "exact-runtime environment retained a CUDA stub path",
            )
        if environment_report["ld_preload_absent"] is not True:
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                "exact-runtime environment retained LD_PRELOAD",
            )
        write_json(
            OUTPUT_ROOT / "runtime_environment_report_v1.json",
            environment_report,
        )

        active_failure_code = (
            "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED"
        )
        import_closure = validate_process_tree_import_closure(counters)

        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        model_home, snapshot = prepare_model_home(source_snapshot)

        failed_capability = "C1"
        active_failure_code = "MODEL_CONSTRUCTION_FAILURE"
        worker_1 = Worker(
            "worker_1",
            0,
            8001,
            model_home,
            snapshot,
            generation=1,
        )
        worker_1.start(counters)
        worker_1.wait_ready()
        worker_1.validate_model()

        c1_decision = BehaviorDecision(
            capability="C1_MODEL_TOKENIZER_CONSTRUCTION",
            state=BehaviorState.PASS,
            failure_class=None,
            reasons=(
                "exact-runtime worker served the pinned model identity",
                "target runtime and model snapshot identities were validated",
            ),
        )
        if not decision_invariant_under_projection_policy(c1_decision):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C1 decision changed under evidence projection policy",
            )
        write_json(
            OUTPUT_ROOT / "c1_model_construction_report_v1.json",
            evidence_projection(
                c1_decision,
                {
                    "runtime_identity": runtime_identity,
                    "model_repository": MODEL_REPOSITORY,
                    "model_revision": MODEL_REVISION,
                    "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
                    "runtime_source_identity": source_identity,
                },
            ).public_summary,
        )
        completed.append("C1")

        failed_capability = "C2"
        active_failure_code = "WORKER_STARTUP_FAILURE"
        initial_native_origins = validate_native_origin_closure(worker_1)
        c2_decision = BehaviorDecision(
            capability="C2_WORKER_STARTUP",
            state=BehaviorState.PASS,
            failure_class=None,
            reasons=(
                "worker 1 generation 1 reached bounded readiness",
                "worker process identity and native provenance were captured",
            ),
        )
        if not decision_invariant_under_projection_policy(c2_decision):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C2 decision changed under evidence projection policy",
            )
        write_json(
            OUTPUT_ROOT / "c2_worker_startup_report_v1.json",
            evidence_projection(
                c2_decision,
                {
                    "worker": worker_1.report(),
                    "native_origin_closure": initial_native_origins,
                },
            ).public_summary,
        )
        completed.append("C2")

        failed_capability = "C3"
        active_failure_code = "REQUEST_EXECUTION_FAILURE"
        cold = run_structured_request(
            worker_1,
            "BASE_COLD",
            "A",
            counters,
        )
        c3_decision = BehaviorDecision(
            capability="C3_SINGLE_DETERMINISTIC_REQUEST",
            state=BehaviorState.PASS,
            failure_class=None,
            reasons=(
                "BASE_COLD completed exactly once on worker 1 generation 1",
            ),
        )
        if not decision_invariant_under_projection_policy(c3_decision):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C3 decision changed under evidence projection policy",
            )
        write_json(
            OUTPUT_ROOT / "c3_single_request_report_v1.json",
            evidence_projection(
                c3_decision,
                {"request": request_public_evidence(cold)},
            ).public_summary,
        )
        completed.append("C3")

        failed_capability = "C4"
        active_failure_code = "OUTPUT_CONTRACT_FAILURE"
        cold_semantic = _request_semantic_observation(cold)
        if cold_semantic.state is SemanticState.EXACT_MATCH:
            c4_decision = BehaviorDecision(
                capability="C4_OUTPUT_CONTRACT",
                state=BehaviorState.PASS,
                failure_class=None,
                reasons=(
                    "BASE_COLD returned the exact frozen structured object",
                    "completion token budget and output provenance were valid",
                ),
            )
        else:
            c4_decision = BehaviorDecision(
                capability="C4_OUTPUT_CONTRACT",
                state=BehaviorState.FAIL,
                failure_class="OUTPUT_CONTRACT_FAILURE",
                reasons=(
                    f"semantic_state={cold_semantic.state.value}",
                    "mechanism evidence remains admissible independently",
                ),
            )
        if not decision_invariant_under_projection_policy(c4_decision):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "C4 decision changed under evidence projection policy",
            )
        write_json(
            OUTPUT_ROOT / "c4_output_contract_report_v1.json",
            evidence_projection(
                c4_decision,
                {
                    "semantic_observation": asdict(cold_semantic),
                    "completion_tokens": cold["completion_tokens"],
                    "route_observation": asdict(_request_route(cold)),
                },
            ).public_summary,
        )
        completed.append("C4")

        failed_capability = "P5"
        active_failure_code = "P5_CACHE_OBSERVATION_FAILURE"
        warm = run_structured_request(
            worker_1,
            "BASE_WARM",
            "A",
            counters,
        )
        negative_prefix = run_structured_request(
            worker_1,
            "NEGATIVE_PREFIX",
            "B",
            counters,
        )

        active_failure_code = "P5_STARTING_STATE_FAILURE"
        old_process_identity = (
            None if worker_1.process is None else worker_1.process.pid,
            worker_1.process_start_ticks,
        )
        reset_teardown = worker_1.stop_and_report("P5_FULL_RESTART")
        teardown_reports.append(reset_teardown)
        if reset_teardown["status"] != "PASSED":
            raise DiagnosticFailure(
                "TEARDOWN_FAILURE",
                "P5 worker teardown proof failed",
            )

        worker_1 = Worker(
            "worker_1",
            0,
            8001,
            model_home,
            snapshot,
            generation=2,
        )
        worker_1.start(counters)
        worker_1.wait_ready()
        worker_1.validate_model()
        post_restart_native_origins = validate_native_origin_closure(worker_1)
        write_json(
            OUTPUT_ROOT / "p5_post_restart_native_origin_report_v1.json",
            post_restart_native_origins,
        )
        new_process_identity = (
            None if worker_1.process is None else worker_1.process.pid,
            worker_1.process_start_ticks,
        )
        if (
            old_process_identity[0] is None
            or old_process_identity[1] is None
            or new_process_identity[0] is None
            or new_process_identity[1] is None
            or old_process_identity == new_process_identity
        ):
            raise DiagnosticFailure(
                "P6_WORKER_GENERATION_FAILURE",
                "full-process reset did not establish a new worker generation",
            )

        post_reset_cold = run_structured_request(
            worker_1,
            "POST_RESET_COLD",
            "A",
            counters,
        )

        failed_capability = "P6"
        active_failure_code = "WORKER_STARTUP_FAILURE"
        p6_checkpoint = new_p6_checkpoint(counters)
        persist_p6_checkpoint(
            p6_checkpoint,
            "P6_STARTED",
            counters,
        )
        worker_2 = Worker(
            "worker_2",
            1,
            8002,
            model_home,
            snapshot,
            generation=1,
        )
        worker_2.start(counters)
        worker_2.wait_ready()
        worker_2.validate_model()
        persist_p6_checkpoint(
            p6_checkpoint,
            "WORKER_2_READY",
            counters,
            {"worker_instance_id": worker_2.instance_id},
        )

        if worker_1.port == worker_2.port:
            raise DiagnosticFailure(
                "P6_ROUTE_REALIZATION_FAILURE",
                "worker ports are not distinct",
            )

        active_failure_code = "P6_STATE_ISOLATION_FAILURE"
        process_isolation = validate_process_isolation(worker_1, worker_2)
        gpu_isolation = validate_gpu_isolation(worker_1, worker_2)
        native_origins = validate_native_origin_closure(worker_1, worker_2)
        write_json(
            OUTPUT_ROOT / "p6_native_origin_report_v1.json",
            native_origins,
        )

        routing = route_isolation(
            worker_1,
            worker_2,
            counters,
            p6_checkpoint,
        )
        cross_worker_cold = routing["cross_worker_request"]
        worker_1_retention = routing["worker_1_retention_request"]
        if not isinstance(cross_worker_cold, dict):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "CROSS_WORKER_COLD request evidence is invalid",
            )
        if not isinstance(worker_1_retention, dict):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "WORKER1_RETENTION request evidence is invalid",
            )

        failed_capability = "P5"
        active_failure_code = "P5_BEHAVIOR_FAILURE"
        p5_decision = decide_p5(
            cold,
            warm,
            negative_prefix,
            post_reset_cold,
            cross_worker_cold,
        )
        if not decision_invariant_under_projection_policy(p5_decision):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "P5 decision changed under evidence projection policy",
            )
        p5_observations: dict[str, object] = {
            "BASE_COLD": request_public_evidence(cold),
            "BASE_WARM": request_public_evidence(warm),
            "NEGATIVE_PREFIX": request_public_evidence(negative_prefix),
            "POST_RESET_COLD": request_public_evidence(post_reset_cold),
            "CROSS_WORKER_COLD": request_public_evidence(cross_worker_cold),
            "old_worker_process_identity": list(old_process_identity),
            "new_worker_process_identity": list(new_process_identity),
            "reset_teardown": reset_teardown,
        }
        write_json(
            OUTPUT_ROOT / "p5_cache_behavior_report_v1.json",
            evidence_projection(
                p5_decision,
                p5_observations,
            ).public_summary,
        )
        completed.append("P5")

        failed_capability = "P6"
        active_failure_code = "P6_BEHAVIOR_FAILURE"
        p6_decision = decide_p6(
            cross_worker_cold,
            worker_1_retention,
            process_isolation,
            gpu_isolation,
        )
        if not decision_invariant_under_projection_policy(p6_decision):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "P6 decision changed under evidence projection policy",
            )
        p6_checkpoint["status"] = p6_decision.state.value
        persist_p6_checkpoint(
            p6_checkpoint,
            "P6_COMPLETED",
            counters,
            {
                "p6_decision": p6_decision.state.value,
                "request_counters_reconciled": True,
            },
        )
        p6_observations = {
            "worker_1": worker_1.report(),
            "worker_2": worker_2.report(),
            "process_isolation": process_isolation,
            "gpu_isolation": gpu_isolation,
            "native_origin_closure": native_origins,
            "CROSS_WORKER_COLD": request_public_evidence(
                cross_worker_cold
            ),
            "WORKER1_RETENTION": request_public_evidence(
                worker_1_retention
            ),
            "request_counters_reconciled": True,
        }
        write_json(
            OUTPUT_ROOT / "p6_worker_state_isolation_report_v1.json",
            evidence_projection(
                p6_decision,
                p6_observations,
            ).public_summary,
        )
        completed.append("P6")
        failed_capability = None

        if p5_decision.state is BehaviorState.FAIL:
            raise DiagnosticFailure(
                p5_decision.failure_class or "P5_BEHAVIOR_FAILURE",
                "; ".join(p5_decision.reasons)[:512],
            )
        if p6_decision.state is BehaviorState.FAIL:
            raise DiagnosticFailure(
                p6_decision.failure_class or "P6_BEHAVIOR_FAILURE",
                "; ".join(p6_decision.reasons)[:512],
            )

        terminal_state = "PASSED_PENDING_REPOSITORY_ACCEPTANCE"

    except DiagnosticAmbiguity as error:
        terminal_state = "AMBIGUOUS_PENDING_REPOSITORY_DISPOSITION"
        failure = {
            "schema_version": "1.0.0",
            "status": "AMBIGUOUS",
            "failed_after": completed,
            "failed_capability": failed_capability,
            "failure_class": error.failure_class,
            "detail_code": None,
            "error_type": type(error).__name__,
            "safe_message": error.safe_message,
        }
    except Exception as error:
        terminal_state = "FAILED_PENDING_REPOSITORY_DISPOSITION"
        if isinstance(error, DiagnosticFailure):
            detail_code = error.error_code
            safe_message = error.safe_message
        else:
            detail_code = active_failure_code
            safe_message = (
                sanitize_excerpt(str(error))[:512]
                or type(error).__name__
            )
        failure = {
            "schema_version": "1.0.0",
            "status": "FAILED",
            "failed_after": completed,
            "failed_capability": failed_capability,
            "failure_class": classify_failure_detail(detail_code),
            "detail_code": detail_code,
            "error_type": type(error).__name__,
            "safe_message": safe_message,
        }
        if p6_checkpoint is not None:
            p6_checkpoint["status"] = "FAILED"
            p6_checkpoint["failure_class"] = failure["failure_class"]
            try:
                persist_p6_checkpoint(
                    p6_checkpoint,
                    "P6_FAILED",
                    counters,
                    {
                        "failure_class": failure["failure_class"],
                        "detail_code": detail_code,
                    },
                )
            except Exception:
                failure["secondary_checkpoint_failure"] = True
    finally:
        if worker_2 is not None:
            report = worker_2.stop_and_report("TERMINAL_FINALIZATION")
            if report not in teardown_reports:
                teardown_reports.append(report)
        if worker_1 is not None:
            report = worker_1.stop_and_report("TERMINAL_FINALIZATION")
            if report not in teardown_reports:
                teardown_reports.append(report)

    teardown_failures = tuple(
        item
        for item in teardown_reports
        if item.get("status") not in {"PASSED", "NOT_STARTED"}
    )
    teardown_status = (
        "NOT_RUN"
        if not teardown_reports
        else "FAILED"
        if teardown_failures
        else "PASSED"
    )
    write_json(
        OUTPUT_ROOT / "worker_teardown_report_v1.json",
        {
            "schema_version": "1.0.0",
            "report_id": (
                "auragateway-exact-runtime-p5-p6-worker-teardown-v1"
            ),
            "status": teardown_status,
            "worker_teardowns": teardown_reports,
            "all_capture_threads_finalized": (
                not teardown_failures
                and all(
                    bool(item.get("capture_threads_finalized", True))
                    for item in teardown_reports
                )
            ),
            "all_ports_closed": (
                not teardown_failures
                and all(
                    bool(item.get("port_closed_after", True))
                    for item in teardown_reports
                )
            ),
            "all_gpu_processes_absent": (
                not teardown_failures
                and all(
                    bool(item.get("gpu_processes_absent_after", True))
                    for item in teardown_reports
                )
            ),
        },
    )

    if teardown_failures:
        terminal_state = "FAILED_PENDING_REPOSITORY_DISPOSITION"
        if failure is None:
            failure = {
                "schema_version": "1.0.0",
                "status": "FAILED",
                "failed_after": completed,
                "failed_capability": None,
                "failure_class": "TEARDOWN_FAILURE",
                "detail_code": "TEARDOWN_FAILURE",
                "error_type": "WorkerTeardownFailure",
                "safe_message": "one or more worker teardown proofs failed",
            }
        else:
            failure["secondary_teardown_failure"] = True

    expected_counters = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 3,
        "worker_starts": 3,
        "model_requests": 6,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "hidden_retries": 0,
        "external_spend": 0,
    }
    all_capabilities_completed = completed == [
        "C1",
        "C2",
        "C3",
        "C4",
        "P5",
        "P6",
    ]
    passed = (
        all_capabilities_completed
        and failure is None
        and p5_decision is not None
        and p5_decision.state is BehaviorState.PASS
        and p6_decision is not None
        and p6_decision.state is BehaviorState.PASS
        and teardown_status == "PASSED"
    )
    if passed:
        for name, expected in expected_counters.items():
            if counters[name] != expected:
                passed = False
                terminal_state = "FAILED_PENDING_REPOSITORY_DISPOSITION"
                failure = {
                    "schema_version": "1.0.0",
                    "status": "FAILED",
                    "failed_after": completed,
                    "failed_capability": None,
                    "failure_class": "REQUEST_RECONCILIATION_FAILURE",
                    "detail_code": "P3_P6_ACTION_BUDGET_EXCEEDED",
                    "error_type": "ActionBudgetDrift",
                    "safe_message": (
                        f"{name} expected {expected}, "
                        f"observed {counters[name]}"
                    ),
                }
                break

    failure_class = (
        None
        if failure is None
        else str(failure.get("failure_class"))
    )
    ensure_runtime_source_identity_report(failure_class)
    ensure_install_report(failure_class)
    ensure_import_closure_report(failure_class)

    environment_path = OUTPUT_ROOT / "runtime_environment_report_v1.json"
    if not environment_path.is_file():
        write_json(
            environment_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
                "raw_environment_retained": False,
            },
        )

    post_restart_native_path = (
        OUTPUT_ROOT / "p5_post_restart_native_origin_report_v1.json"
    )
    if not post_restart_native_path.is_file():
        write_json(
            post_restart_native_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
                "observations": [],
                "rejected_origin_count": 0,
            },
        )

    p6_native_path = OUTPUT_ROOT / "p6_native_origin_report_v1.json"
    if not p6_native_path.is_file():
        write_json(
            p6_native_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
                "observations": [],
                "rejected_origin_count": 0,
            },
        )

    checkpoint_path = OUTPUT_ROOT / "p6_stage_checkpoint_report_v1.json"
    if not checkpoint_path.is_file():
        write_json(
            checkpoint_path,
            {
                "schema_version": "1.0.0",
                "probe_id": "P6",
                "status": "NOT_RUN",
                "current_stage": "P6_NOT_STARTED",
                "events": [],
                "worker_request_counters": {
                    "worker_1": {"attempted": 0, "completed": 0},
                    "worker_2": {"attempted": 0, "completed": 0},
                },
                "global_model_requests": counters["model_requests"],
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
                "raw_prompt_logged": False,
                "raw_output_logged": False,
            },
        )

    write_capability_terminal_reports(
        completed,
        failed_capability,
        failure_class,
        counters,
    )

    cleanup = cleanup_scratch()
    if cleanup["status"] != "PASSED":
        passed = False
        terminal_state = "FAILED_PENDING_REPOSITORY_DISPOSITION"
        if failure is None:
            failure = {
                "schema_version": "1.0.0",
                "status": "FAILED",
                "failed_after": completed,
                "failed_capability": None,
                "failure_class": "TEARDOWN_FAILURE",
                "detail_code": "P3_P6_SCRATCH_CLEANUP_FAILED",
                "error_type": cleanup["error_type"],
                "safe_message": cleanup["safe_message"],
            }
        else:
            failure["secondary_scratch_cleanup_failure"] = True

    if passed and failure is None:
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NOT_APPLICABLE",
                "failure_class": None,
                "detail_code": None,
                "error_type": None,
                "safe_message": None,
                "failed_after": completed,
                "failed_capability": None,
                "teardown_status": teardown_status,
            },
        )
    elif failure is not None:
        failure["teardown_status"] = teardown_status
        write_json(OUTPUT_ROOT / "failure_report_v1.json", failure)

    source_identity_report = json.loads(
        (
            OUTPUT_ROOT / "runtime_source_identity_report_v1.json"
        ).read_text(encoding="utf-8")
    )
    install_report = json.loads(
        (OUTPUT_ROOT / "runtime_install_report_v1.json").read_text(
            encoding="utf-8"
        )
    )
    import_closure_report = json.loads(
        (
            OUTPUT_ROOT / "runtime_import_closure_report_v1.json"
        ).read_text(encoding="utf-8")
    )

    summary_status = "PASSED" if passed else terminal_state.split("_", 1)[0]
    summary = {
        "schema_version": "1.0.0",
        "diagnostic_id": (
            "auragateway-p5-p6-mechanism-admission-successor-v1"
        ),
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "implementation_review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "mechanism_admission_contract_sha256": MECHANISM_ADMISSION_CONTRACT_SHA256,
        "implementation_addendum_sha256": IMPLEMENTATION_ADDENDUM_SHA256,
        "executed_runtime_script_sha256": source_identity_report.get(
            "executed_runtime_script_sha256"
        ),
        "authorization": authorization,
        "status": summary_status,
        "terminal_state": terminal_state,
        "completed_capabilities": completed,
        "failure_class": (
            None if failure is None else failure.get("failure_class")
        ),
        "failed_capability": (
            None if failure is None else failure.get("failed_capability")
        ),
        "c4_semantic_state": (
            None
            if "cold" not in locals()
            else _request_semantic_observation(cold).state.value
        ),
        "c4_semantic_qualified": (
            False
            if "cold" not in locals()
            else (
                _request_semantic_observation(cold).state
                is SemanticState.EXACT_MATCH
            )
        ),
        "p5_decision": (
            None if p5_decision is None else p5_decision.state.value
        ),
        "p6_decision": (
            None if p6_decision is None else p6_decision.state.value
        ),
        "runtime_install_status": install_report["status"],
        "runtime_install_process_outcome": install_report[
            "process_outcome"
        ],
        "runtime_import_closure_status": import_closure_report["status"],
        "runtime_import_closure_process_outcome": import_closure_report[
            "process_outcome"
        ],
        "worker_teardown_status": teardown_status,
        "counters": counters,
        "scratch_cleanup_status": cleanup["status"],
        "scratch_exists_after_cleanup": cleanup["scratch_exists_after"],
        "credentials_used": False,
        "customer_data_present": False,
        "network_access_permitted": False,
        "benchmark_trajectory_requests": 0,
        "pilot_execution_performed": False,
        "measured_abc_execution_performed": False,
        "public_evidence_used_as_semantic_input": False,
        "next_gate": (
            "PRESERVE_AND_DISPOSITION_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
        ),
    }
    write_json(
        OUTPUT_ROOT / "p5_p6_exact_runtime_requalification_summary_v1.json",
        summary,
    )

    human = (
        "# AuraGateway P5/P6 Mechanism-Admission Successor V1\n\n"
        f"- Status: {summary['status']}\n"
        f"- Terminal state: {terminal_state}\n"
        f"- C4 semantic state: {summary['c4_semantic_state']}\n"
        f"- P5 decision: {summary['p5_decision']}\n"
        f"- P6 decision: {summary['p6_decision']}\n"
        f"- Worker teardown: {summary['worker_teardown_status']}\n"
        f"- Completed capabilities: "
        f"{', '.join(completed) or 'none'}\n"
        f"- Model requests: {counters['model_requests']} / 6 maximum\n"
        "- Hidden retries: 0\n"
        "- No A/B/C benchmark trajectory was executed.\n"
        "- C4 semantic failure does not count as P5/P6 mechanism failure.\n"
        "- Pilot and final measured A/B/C remain unauthorized.\n"
        "- Production readiness is not claimed.\n"
    )
    write_text(OUTPUT_ROOT / "human_report_v1.md", human)

    bundle = bundle_outputs()
    terminal_payload = {**summary, **bundle}
    print(canonical_json(terminal_payload))
    return 0 if passed else 2

if __name__ == "__main__":
    raise SystemExit(main())
