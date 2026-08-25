"""Single-use live issuer for the measured A/B/C variance-pilot successor V2.

Static generation and validation are inert. Live issuance is permitted only from a
clean synchronized main after merge and an exact operator retype of a fresh dynamic
SHA-256 challenge. The issuer reuses the already-bound V2 rehearsal template as the
single owner of the six-module embedded runtime graph.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_authority_binding_v1 as binding,
)
from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_wrapper_rehearsal_v1 as rehearsal,
)

BASE_MAIN_COMMIT: Final = "9a2480582e57ddeb8e08962dd1f5671e7ab76be7"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_single_use_live_issuer_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_v2_single_use_live_issuer_v1.py"
)
REHEARSAL_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_wrapper_rehearsal_v1.py"
)

REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_single_use_live_issuer_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_single_use_live_issuer_v1_record.json"
)
LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_single_use_live_issuer_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_single_use_live_issuer_v1_live_manifest.json"
)
PLATFORM_OBSERVATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_single_use_live_issuer_v1_platform_observation.json"
)
TERMINAL_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_single_use_live_issuer_v1_terminal.json"
)

AUTHORIZATION_SCOPE: Final = "MEASURED_ABC_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_BOUND_V1"
NOTEBOOK_NAME: Final = "ag-variance-pilot-successor-v2-transaction-bound-v1"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240

NEXT_GATE: Final = "MERGE_THEN_REQUALIFY_V2_SINGLE_USE_LIVE_ISSUER_V1"
NEXT_GATE_AFTER_ISSUE: Final = "PERSIST_V2_PLATFORM_OBSERVATION_BEFORE_ONE_SAVE_AND_RUN_ALL"
NEXT_GATE_AFTER_OBSERVATION: Final = (
    "ONE_SAVE_AND_RUN_ALL_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_BOUND_V1"
)
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_CLASSIFY_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_BOUND_V1"
)

_REQUIRED_TEMPLATE_DOCSTRING: Final = (
    '"""Inert structural-rehearsal wrapper for variance-pilot successor V2.\n\n'
    "This template is not a live authorization or execution wrapper. It exists to prove the\n"
    "exact embedded Python module graph, dataclass realization, package import path, V2 material\n"
    "validation, and SystemExit boundary before a future authority tranche can issue execution.\n"
    '"""'
)
_LIVE_WRAPPER_DOCSTRING: Final = (
    '''"""Generated AuraGateway variance-pilot successor V2 transaction-bound wrapper."""'''
)
_REQUIRED_IMPORT_BLOCK: Final = """import base64
import hashlib
import json
import sys
import types
from typing import Any
"""
_LIVE_IMPORT_BLOCK: Final = """import base64
import hashlib
import json
import subprocess
import sys
import types
from datetime import UTC, datetime
from typing import Any
"""
_REQUIRED_TRANSACTION_SEED: Final = '"AURAGATEWAY_TRANSACTION_ID": _REHEARSAL_TRANSACTION_ID,'
_LIVE_MAIN_MARKER: Final = """if __name__ == "__main__":
    raise SystemExit(main())
"""


class IssuerError(RuntimeError):
    """Metadata-safe successor V2 live-issuer failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: Path | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path.as_posix() if self.path is not None else None,
        }


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RequiredPlatform(FrozenModel):
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    fresh_post_artifact_observation_required: Literal[True] = True
    observation_precedes_save_and_run_all: Literal[True] = True
    observation_runtime_input: Literal[False] = False


class StaticReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-measured-abc-variance-pilot-v2-single-use-live-issuer-v1-review"
    ]
    base_main_commit: Literal["9a2480582e57ddeb8e08962dd1f5671e7ab76be7"] = BASE_MAIN_COMMIT
    status: Literal["IMPLEMENTED_NOT_ISSUED"] = "IMPLEMENTED_NOT_ISSUED"
    authority_binding_status: Literal[
        "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_VALID"
    ] = "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_VALID"
    rendered_wrapper_sha256: Literal[
        "5bc26b220c7b34da7d634686af97d67b0d2666f84ac6f8d9b1f214163c17cb41"
    ] = binding.EXPECTED_RENDERED_WRAPPER_SHA256
    bound_artifact_count: Literal[19] = binding.EXPECTED_BOUND_ARTIFACT_COUNT
    runtime: binding.RuntimeModelContract = binding.RuntimeModelContract()
    budget: binding.ExecutionBudget = binding.ExecutionBudget()
    required_platform: RequiredPlatform = RequiredPlatform()
    live_authorization_issued: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    candidate_introduced_live_authority: Literal[False] = False
    non_claims: tuple[str, ...]
    next_gate: str


class ArtifactReceipt(FrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class StaticRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-measured-abc-variance-pilot-v2-single-use-live-issuer-v1-record"
    ]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: ArtifactReceipt
    test: ArtifactReceipt
    authority_binding_source: ArtifactReceipt
    authority_binding_review: ArtifactReceipt
    authority_binding_record: ArtifactReceipt
    rehearsal_source: ArtifactReceipt
    rehearsal_template: ArtifactReceipt
    rendered_wrapper_sha256: Literal[
        "5bc26b220c7b34da7d634686af97d67b0d2666f84ac6f8d9b1f214163c17cb41"
    ] = binding.EXPECTED_RENDERED_WRAPPER_SHA256
    bound_artifact_count: Literal[19] = binding.EXPECTED_BOUND_ARTIFACT_COUNT
    live_authorization_issued: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: str


class LiveAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["MEASURED_ABC_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_BOUND_V1"] = (
        AUTHORIZATION_SCOPE
    )
    issued_at: datetime
    expires_at: datetime
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    static_authority_binding_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rendered_wrapper_sha256: Literal[
        "5bc26b220c7b34da7d634686af97d67b0d2666f84ac6f8d9b1f214163c17cb41"
    ] = binding.EXPECTED_RENDERED_WRAPPER_SHA256
    bound_artifact_count: Literal[19] = binding.EXPECTED_BOUND_ARTIFACT_COUNT
    transaction_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime: binding.RuntimeModelContract = binding.RuntimeModelContract()
    budget: binding.ExecutionBudget = binding.ExecutionBudget()
    required_platform: RequiredPlatform = RequiredPlatform()
    pilot_execution_authorized: Literal[True] = True
    final_measured_abc_execution_authorized: Literal[False] = False
    single_use: Literal[True] = True
    authorization_reusable: Literal[False] = False
    unchanged_replay_authorized: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    authorization_specific_kaggle_inputs: Literal[0] = 0
    authorization_producer_notebooks: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    fresh_post_artifact_platform_observation_required: Literal[True] = True
    platform_observation_runtime_input: Literal[False] = False

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        return self


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _artifact_bytes(value: object) -> bytes:
    return _canonical_bytes(value) + b"\n"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise IssuerError(
            "V2_LIVE_ISSUER_REQUIRED_FILE_MISSING",
            "required live-issuer file is missing or unsafe",
            relative,
        )
    payload = path.read_bytes()
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256(payload),
        size_bytes=len(payload),
    )


def _git(
    repo_root: Path,
    *args: str,
    binary: bool = False,
) -> str | bytes:
    if binary:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise IssuerError(
                "V2_LIVE_ISSUER_GIT_FAILED",
                "required Git inspection failed",
            )
        return completed.stdout

    completed_text = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed_text.returncode != 0:
        raise IssuerError(
            "V2_LIVE_ISSUER_GIT_FAILED",
            "required Git inspection failed",
        )
    return completed_text.stdout.strip()


def _head_bytes(repo_root: Path, relative: Path) -> bytes:
    return cast(
        bytes,
        _git(
            repo_root,
            "show",
            f"HEAD:{relative.as_posix()}",
            binary=True,
        ),
    )


def _validate_base_lineage(repo_root: Path) -> None:
    resolved = cast(str, _git(repo_root, "rev-parse", BASE_MAIN_COMMIT))
    if resolved != BASE_MAIN_COMMIT:
        raise IssuerError(
            "V2_LIVE_ISSUER_BASE_COMMIT_MISSING",
            "required PR #314 base commit is unavailable",
        )
    merge_base = cast(str, _git(repo_root, "merge-base", BASE_MAIN_COMMIT, "HEAD"))
    if merge_base != BASE_MAIN_COMMIT:
        raise IssuerError(
            "V2_LIVE_ISSUER_BASE_NOT_ANCESTOR",
            "candidate HEAD does not descend from the requalified PR #314 subject",
        )


def _validate_static_subject(repo_root: Path) -> None:
    _validate_base_lineage(repo_root)
    binding_result = binding.validate_implementation(repo_root)
    if binding_result.get("status") != (
        "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_VALID"
    ):
        raise IssuerError(
            "V2_LIVE_ISSUER_BINDING_INVALID",
            "static V2 authority binding is not valid",
        )
    rehearsal_result = rehearsal.validate_implementation(repo_root)
    if (
        rehearsal_result.get("status")
        != "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_WRAPPER_REHEARSAL_VALID"
        or rehearsal_result.get("rendered_wrapper_sha256")
        != binding.EXPECTED_RENDERED_WRAPPER_SHA256
    ):
        raise IssuerError(
            "V2_LIVE_ISSUER_REHEARSAL_INVALID",
            "V2 structural rehearsal no longer matches the accepted subject",
        )


def build_review(repo_root: Path) -> StaticReview:
    root = repo_root.resolve()
    _validate_static_subject(root)
    return StaticReview(
        review_id=("auragateway-measured-abc-variance-pilot-v2-single-use-live-issuer-v1-review"),
        non_claims=(
            "This implementation does not issue live V2 execution authorization.",
            "This implementation performs no model, GPU, or Kaggle execution.",
            "This implementation does not establish successful V2 pilot execution.",
            "This implementation does not establish V2 pilot repository acceptance.",
            "This implementation does not authorize final measured A/B/C execution.",
            "This implementation does not establish A/B/C effects or production readiness.",
        ),
        next_gate=NEXT_GATE,
    )


def build_record(repo_root: Path, review: StaticReview) -> StaticRecord:
    return StaticRecord(
        record_id=("auragateway-measured-abc-variance-pilot-v2-single-use-live-issuer-v1-record"),
        review_sha256=_sha256(_canonical_bytes(review)),
        source=_receipt(repo_root, SOURCE_PATH),
        test=_receipt(repo_root, TEST_PATH),
        authority_binding_source=_receipt(repo_root, binding.SOURCE_PATH),
        authority_binding_review=_receipt(repo_root, binding.REVIEW_PATH),
        authority_binding_record=_receipt(repo_root, binding.RECORD_PATH),
        rehearsal_source=_receipt(repo_root, REHEARSAL_SOURCE_PATH),
        rehearsal_template=_receipt(repo_root, rehearsal.WRAPPER_TEMPLATE_PATH),
        next_gate=NEXT_GATE,
    )


def _write_json(path: Path, value: object) -> None:
    if path.exists() and path.is_symlink():
        raise IssuerError(
            "V2_LIVE_ISSUER_OUTPUT_SYMLINK_REJECTED",
            "live-issuer output path may not be a symlink",
            path,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_artifact_bytes(value))


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    review = build_review(root)
    record = build_record(root, review)
    _write_json(root / REVIEW_PATH, review)
    _write_json(root / RECORD_PATH, record)
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_SINGLE_USE_LIVE_ISSUER_MATERIALIZED",
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_review = build_review(root)
    expected_record = build_record(root, expected_review)
    try:
        observed_review = StaticReview.model_validate_json((root / REVIEW_PATH).read_bytes())
        observed_record = StaticRecord.model_validate_json((root / RECORD_PATH).read_bytes())
    except (FileNotFoundError, ValidationError) as error:
        raise IssuerError(
            "V2_LIVE_ISSUER_GENERATED_OUTPUT_INVALID",
            "generated V2 live-issuer output is invalid",
        ) from error

    if observed_review != expected_review:
        raise IssuerError(
            "V2_LIVE_ISSUER_REVIEW_DRIFT",
            "V2 live-issuer review is not deterministic",
            REVIEW_PATH,
        )
    if observed_record != expected_record:
        raise IssuerError(
            "V2_LIVE_ISSUER_RECORD_DRIFT",
            "V2 live-issuer record is not deterministic",
            RECORD_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_SINGLE_USE_LIVE_ISSUER_VALID",
        "candidate_introduced_live_authority": False,
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _require_clean_synchronized_main(repo_root: Path) -> str:
    branch = cast(str, _git(repo_root, "branch", "--show-current"))
    if branch != "main":
        raise IssuerError(
            "V2_LIVE_ISSUER_REQUIRES_MAIN",
            "live authorization may only be issued from main",
        )
    _git(repo_root, "fetch", "origin", "main")
    head = cast(str, _git(repo_root, "rev-parse", "HEAD"))
    origin = cast(str, _git(repo_root, "rev-parse", "origin/main"))
    if head != origin:
        raise IssuerError(
            "V2_LIVE_ISSUER_MAIN_NOT_SYNCHRONIZED",
            "local main must exactly match origin/main before live issuance",
        )
    status = cast(str, _git(repo_root, "status", "--porcelain"))
    if status:
        raise IssuerError(
            "V2_LIVE_ISSUER_WORKTREE_NOT_CLEAN",
            "live issuance requires a clean synchronized main worktree",
        )
    return head


def _base_wrapper(repo_root: Path, material: bytes) -> str:
    sources = {
        "__R2_RUNTIME_B64__": _head_bytes(repo_root, rehearsal.R2_RUNTIME_PATH),
        "__OUTPUT_ADMISSION_RUNTIME_B64__": _head_bytes(
            repo_root, rehearsal.OUTPUT_ADMISSION_RUNTIME_PATH
        ),
        "__STANDALONE_RUNTIME_B64__": _head_bytes(repo_root, rehearsal.STANDALONE_RUNTIME_PATH),
        "__LIVE_SEMANTICS_RUNTIME_B64__": _head_bytes(
            repo_root, rehearsal.LIVE_SEMANTICS_RUNTIME_PATH
        ),
        "__REQUEST_ADAPTER_B64__": _head_bytes(repo_root, rehearsal.REQUEST_ADAPTER_PATH),
        "__TRANSACTION_RUNTIME_B64__": _head_bytes(repo_root, rehearsal.TRANSACTION_RUNTIME_PATH),
        "__MATERIAL_B64__": material,
    }
    template = _head_bytes(repo_root, rehearsal.WRAPPER_TEMPLATE_PATH).decode("utf-8")
    rendered = template
    for token, payload in sources.items():
        replacements = {
            token: base64.b64encode(payload).decode("ascii"),
            token.replace("_B64__", "_SHA256__"): _sha256(payload),
        }
        for replacement_token, value in replacements.items():
            if replacement_token not in rendered:
                raise IssuerError(
                    "V2_LIVE_ISSUER_TEMPLATE_TOKEN_MISSING",
                    "required V2 rehearsal-template token is missing",
                    rehearsal.WRAPPER_TEMPLATE_PATH,
                )
            rendered = rendered.replace(replacement_token, value)

    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
    if unresolved:
        raise IssuerError(
            "V2_LIVE_ISSUER_TEMPLATE_UNRESOLVED",
            "V2 rehearsal template retained unresolved governed tokens",
            rehearsal.WRAPPER_TEMPLATE_PATH,
        )
    return rendered


def _replace_once(value: str, old: str, new: str, label: str) -> str:
    if value.count(old) != 1:
        raise IssuerError(
            "V2_LIVE_ISSUER_TEMPLATE_SHAPE_DRIFT",
            f"expected exactly one live-wrapper transform marker: {label}",
            rehearsal.WRAPPER_TEMPLATE_PATH,
        )
    return value.replace(old, new, 1)


def _live_admission_block(
    *,
    authorization_b64: str,
    transaction_id: str,
    issuer_commit: str,
    issuer_sha256: str,
    binding_record_sha256: str,
    expected_runtime_b64: str,
    expected_budget_b64: str,
    expected_platform_b64: str,
) -> str:
    return f'''_LIVE_EXECUTION_ENABLED = True
_AUTHORIZATION_B64 = "{authorization_b64}"
_TRANSACTION_ID = "{transaction_id}"
_ISSUER_MERGE_COMMIT = "{issuer_commit}"
_ISSUER_SOURCE_SHA256 = "{issuer_sha256}"
_STATIC_BINDING_RECORD_SHA256 = "{binding_record_sha256}"
_EXPECTED_RUNTIME_B64 = "{expected_runtime_b64}"
_EXPECTED_BUDGET_B64 = "{expected_budget_b64}"
_EXPECTED_PLATFORM_B64 = "{expected_platform_b64}"


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError("authorization timestamp is invalid")
    observed = datetime.fromisoformat(value)
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise RuntimeError("authorization timestamp must be timezone-aware")
    return observed.astimezone(UTC)


def _gpu_count() -> int:
    completed = subprocess.run(
        ["nvidia-smi", "-L"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("unable to observe GPU topology")
    return sum(line.strip().startswith("GPU ") for line in completed.stdout.splitlines())


def admit(now: datetime | None = None) -> dict[str, object]:
    envelope = json.loads(_decode(_AUTHORIZATION_B64))
    if not isinstance(envelope, dict):
        raise RuntimeError("embedded authorization envelope is invalid")
    authorization = envelope.get("authorization")
    if envelope.get("transaction_id") != _TRANSACTION_ID or not isinstance(
        authorization, dict
    ):
        raise RuntimeError("embedded transaction identity drifted")
    if _sha256(_canonical_json(authorization).encode("utf-8")) != _TRANSACTION_ID:
        raise RuntimeError("inner authorization transaction identity mismatch")

    required = {{
        "schema_version": "1.0.0",
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": "{AUTHORIZATION_SCOPE}",
        "issuer_merge_commit": _ISSUER_MERGE_COMMIT,
        "issuer_source_sha256": _ISSUER_SOURCE_SHA256,
        "static_authority_binding_record_sha256": _STATIC_BINDING_RECORD_SHA256,
        "rendered_wrapper_sha256": "{binding.EXPECTED_RENDERED_WRAPPER_SHA256}",
        "bound_artifact_count": 19,
        "transaction_runtime_sha256": _TRANSACTION_RUNTIME_SHA256,
        "material_sha256": _MATERIAL_SHA256,
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "single_use": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "runtime_anti_replay_established": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "fresh_post_artifact_platform_observation_required": True,
        "platform_observation_runtime_input": False,
    }}
    drift = [
        key for key, expected in required.items() if authorization.get(key) != expected
    ]
    if drift:
        raise RuntimeError("embedded V2 authorization drift: " + ",".join(drift))

    expected_runtime = json.loads(_decode(_EXPECTED_RUNTIME_B64))
    expected_budget = json.loads(_decode(_EXPECTED_BUDGET_B64))
    expected_platform = json.loads(_decode(_EXPECTED_PLATFORM_B64))
    if authorization.get("runtime") != expected_runtime:
        raise RuntimeError("embedded V2 runtime contract drifted")
    if authorization.get("budget") != expected_budget:
        raise RuntimeError("embedded V2 execution budget drifted")
    if authorization.get("required_platform") != expected_platform:
        raise RuntimeError("embedded V2 platform contract drifted")

    observed = (now or datetime.now(UTC)).astimezone(UTC)
    issued = _parse_time(authorization.get("issued_at"))
    expires = _parse_time(authorization.get("expires_at"))
    if observed < issued or observed >= expires:
        raise RuntimeError("authorization is outside its live window")
    if _gpu_count() != 2:
        raise RuntimeError("machine-observable GPU topology is not T4 x2")

    return {{
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_BOUND_RUNTIME_ADMISSION_VALID",
        "transaction_id": _TRANSACTION_ID,
        "issuer_merge_commit": _ISSUER_MERGE_COMMIT,
        "static_authority_binding_record_sha256": _STATIC_BINDING_RECORD_SHA256,
        "rendered_wrapper_sha256": "{binding.EXPECTED_RENDERED_WRAPPER_SHA256}",
        "bound_artifact_count": 19,
        "observed_gpu_count": 2,
        "network_probe_performed": False,
        "platform_observation_receipt_runtime_input": False,
        "live_execution_enabled": True,
    }}
'''


def render_live_wrapper(
    repo_root: Path,
    authorization: LiveAuthorization,
    transaction_id: str,
    issuer_commit: str,
    issuer_source_sha256: str,
    binding_record_sha256: str,
    material: bytes,
) -> bytes:
    rendered = _base_wrapper(repo_root, material)

    envelope = _canonical_bytes(
        {
            "transaction_id": transaction_id,
            "authorization": authorization.model_dump(mode="json"),
        }
    )
    expected_runtime = _canonical_bytes(authorization.runtime)
    expected_budget = _canonical_bytes(authorization.budget)
    expected_platform = _canonical_bytes(authorization.required_platform)

    rendered = _replace_once(
        rendered,
        _REQUIRED_TEMPLATE_DOCSTRING,
        _LIVE_WRAPPER_DOCSTRING,
        "docstring",
    )
    rendered = _replace_once(
        rendered,
        _REQUIRED_IMPORT_BLOCK,
        _LIVE_IMPORT_BLOCK,
        "imports",
    )
    seed = '_LIVE_EXECUTION_ENABLED = False\n_REHEARSAL_TRANSACTION_ID = "0" * 64'
    admission_block = _live_admission_block(
        authorization_b64=base64.b64encode(envelope).decode("ascii"),
        transaction_id=transaction_id,
        issuer_commit=issuer_commit,
        issuer_sha256=issuer_source_sha256,
        binding_record_sha256=binding_record_sha256,
        expected_runtime_b64=base64.b64encode(expected_runtime).decode("ascii"),
        expected_budget_b64=base64.b64encode(expected_budget).decode("ascii"),
        expected_platform_b64=base64.b64encode(expected_platform).decode("ascii"),
    ).rstrip()
    rendered = _replace_once(rendered, seed, admission_block, "transaction constants")
    rendered = _replace_once(
        rendered,
        _REQUIRED_TRANSACTION_SEED,
        '"AURAGATEWAY_TRANSACTION_ID": _TRANSACTION_ID,',
        "transaction injection",
    )

    live_main = """def execute() -> int:
    admission = admit()
    print(_canonical_json(admission))
    modules, created, _material = _realize_graph()
    try:
        result = modules["transaction"].__dict__["main"]()
        if result not in (None, 0):
            raise SystemExit(result)
        return 0
    finally:
        _cleanup(created)


if __name__ == "__main__":
    raise SystemExit(execute())
"""
    rendered = _replace_once(rendered, _LIVE_MAIN_MARKER, live_main, "main")
    return rendered.encode("utf-8")


def _write_notebook(path: Path, wrapper: bytes) -> bytes:
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": wrapper.decode("utf-8").splitlines(keepends=True),
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    payload = _artifact_bytes(notebook)
    path.write_bytes(payload)
    return payload


def issue_live(
    repo_root: Path,
    artifact_dir: Path,
    window_minutes: int,
) -> dict[str, object]:
    root = repo_root.resolve()
    if window_minutes < 1 or window_minutes > MAX_WINDOW_MINUTES:
        raise IssuerError(
            "V2_LIVE_ISSUER_WINDOW_INVALID",
            "authorization window is outside permitted bounds",
        )

    issuer_commit = _require_clean_synchronized_main(root)
    validate_implementation(root)
    binding.validate_implementation(root)

    issuer_source = _head_bytes(root, SOURCE_PATH)
    binding_record = _head_bytes(root, binding.RECORD_PATH)
    transaction_runtime = _head_bytes(root, rehearsal.TRANSACTION_RUNTIME_PATH)
    material = _canonical_bytes(rehearsal.build_transaction_material(root))

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=window_minutes)
    challenge = _sha256(
        secrets.token_bytes(32)
        + issuer_commit.encode("ascii")
        + issued_at.isoformat().encode("ascii")
        + _sha256(binding_record).encode("ascii")
    )
    print("RETYPE_DYNAMIC_SHA256_CHALLENGE=" + challenge)
    confirmed = input("Retype the exact challenge to issue live authority: ").strip()
    if confirmed != challenge:
        raise IssuerError(
            "V2_LIVE_ISSUER_OPERATOR_CONFIRMATION_FAILED",
            "dynamic SHA-256 challenge confirmation failed",
        )

    authorization = LiveAuthorization(
        authorization_id="variance-pilot-v2-tx-" + secrets.token_hex(16),
        issued_at=issued_at,
        expires_at=expires_at,
        issuer_merge_commit=issuer_commit,
        issuer_source_sha256=_sha256(issuer_source),
        static_authority_binding_record_sha256=_sha256(binding_record),
        transaction_runtime_sha256=_sha256(transaction_runtime),
        material_sha256=_sha256(material),
    )
    authorization_bytes = _canonical_bytes(authorization)
    transaction_id = _sha256(authorization_bytes)
    wrapper = render_live_wrapper(
        root,
        authorization,
        transaction_id,
        issuer_commit,
        _sha256(issuer_source),
        _sha256(binding_record),
        material,
    )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    executable_path = artifact_dir / f"{NOTEBOOK_NAME}.py"
    notebook_path = artifact_dir / f"{NOTEBOOK_NAME}.ipynb"
    executable_path.write_bytes(wrapper)
    notebook_bytes = _write_notebook(notebook_path, wrapper)

    _write_json(
        root / LIVE_AUTHORIZATION_PATH,
        {
            "transaction_id": transaction_id,
            "authorization": authorization.model_dump(mode="json"),
        },
    )
    manifest = {
        "schema_version": "1.0.0",
        "status": "V2_TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        "transaction_id": transaction_id,
        "issuer_merge_commit": issuer_commit,
        "issuer_source_sha256": _sha256(issuer_source),
        "static_authority_binding_record_sha256": _sha256(binding_record),
        "rendered_rehearsal_wrapper_sha256": binding.EXPECTED_RENDERED_WRAPPER_SHA256,
        "bound_artifact_count": binding.EXPECTED_BOUND_ARTIFACT_COUNT,
        "transaction_runtime_sha256": _sha256(transaction_runtime),
        "material_sha256": _sha256(material),
        "executable_sha256": _sha256(wrapper),
        "notebook_container_sha256": _sha256(notebook_bytes),
        "notebook_container_is_semantic_payload_identity": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "permitted_kaggle_input_roles": [
            "durable_runtime",
            "model_snapshot",
        ],
        "platform_observation_required_before_save_and_run_all": True,
        "platform_observation_persisted": False,
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "single_use_governance": True,
        "runtime_anti_replay_established": False,
        "model_requests_performed_during_issuance": 0,
        "gpu_execution_performed_during_issuance": False,
        "kaggle_execution_performed_during_issuance": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }
    _write_json(root / LIVE_MANIFEST_PATH, manifest)
    return manifest


def record_platform_observation(
    repo_root: Path,
    transaction_id: str,
    observed_at: datetime,
) -> dict[str, object]:
    root = repo_root.resolve()
    live = json.loads((root / LIVE_AUTHORIZATION_PATH).read_text(encoding="utf-8"))
    manifest = json.loads((root / LIVE_MANIFEST_PATH).read_text(encoding="utf-8"))
    if not isinstance(live, dict) or live.get("transaction_id") != transaction_id:
        raise IssuerError(
            "V2_LIVE_ISSUER_TRANSACTION_MISMATCH",
            "live authorization transaction identity mismatch",
        )
    if not isinstance(manifest, dict) or manifest.get("transaction_id") != transaction_id:
        raise IssuerError(
            "V2_LIVE_ISSUER_TRANSACTION_MISMATCH",
            "live manifest transaction identity mismatch",
        )

    receipt = {
        "schema_version": "1.0.0",
        "control_id": "PERSIST_V2_PLATFORM_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL",
        "transaction_id": transaction_id,
        "platform_observed_at": observed_at.astimezone(UTC).isoformat(),
        "accelerator": "T4_X2",
        "allocated_gpu_count": 2,
        "internet_enabled": False,
        "wheelhouse_input_count": 1,
        "model_snapshot_input_count": 1,
        "authorization_specific_kaggle_input_count": 0,
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "persisted_before_save_and_run_all": True,
        "receipt_runtime_input": False,
    }
    _write_json(root / PLATFORM_OBSERVATION_PATH, receipt)
    return {
        "status": "V2_PLATFORM_OBSERVATION_PERSISTED",
        "transaction_id": transaction_id,
        "next_gate": NEXT_GATE_AFTER_OBSERVATION,
    }


def terminalize(
    repo_root: Path,
    transaction_id: str,
    outcome: str,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    terminal_log_sha256: str | None,
) -> dict[str, object]:
    root = repo_root.resolve()
    live = json.loads((root / LIVE_AUTHORIZATION_PATH).read_text(encoding="utf-8"))
    if not isinstance(live, dict) or live.get("transaction_id") != transaction_id:
        raise IssuerError(
            "V2_LIVE_ISSUER_TRANSACTION_MISMATCH",
            "terminalization transaction identity mismatch",
        )
    permitted = {"PASSED", "FAILED", "INTERRUPTED", "AMBIGUOUS"}
    if outcome not in permitted:
        raise IssuerError(
            "V2_LIVE_ISSUER_TERMINAL_OUTCOME_INVALID",
            "terminal execution outcome is invalid",
        )
    if outcome == "PASSED" and (
        saved_version_id is None or evidence_zip_sha256 is None or terminal_log_sha256 is None
    ):
        raise IssuerError(
            "V2_LIVE_ISSUER_PASS_EVIDENCE_REQUIRED",
            "PASSED terminalization requires saved version and evidence identities",
        )

    record = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "disposition": "CONSUMED",
        "execution_attempted": True,
        "execution_outcome": outcome,
        "terminalized_at": datetime.now(UTC).isoformat(),
        "saved_version_id": saved_version_id,
        "evidence_zip_sha256": evidence_zip_sha256,
        "terminal_log_sha256": terminal_log_sha256,
        "authorization_reusable": False,
        "pilot_execution_authorized": False,
        "pilot_repository_acceptance_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }
    _write_json(root / TERMINAL_PATH, record)
    return record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-v2-single-use-live-issuer-v1"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation"):
        item = sub.add_parser(command)
        item.add_argument("--repo-root", type=Path, default=Path("."))

    issue = sub.add_parser("issue-live")
    issue.add_argument("--repo-root", type=Path, default=Path("."))
    issue.add_argument("--artifact-dir", type=Path, required=True)
    issue.add_argument("--window-minutes", type=int, default=DEFAULT_WINDOW_MINUTES)

    observe = sub.add_parser("record-platform-observation")
    observe.add_argument("--repo-root", type=Path, default=Path("."))
    observe.add_argument("--transaction-id", required=True)
    observe.add_argument("--observed-at", required=True)

    terminal = sub.add_parser("terminalize")
    terminal.add_argument("--repo-root", type=Path, default=Path("."))
    terminal.add_argument("--transaction-id", required=True)
    terminal.add_argument("--outcome", required=True)
    terminal.add_argument("--saved-version-id", type=int)
    terminal.add_argument("--evidence-zip-sha256")
    terminal.add_argument("--terminal-log-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        root = args.repo_root.resolve()
        if args.command == "generate":
            result = generate(root)
        elif args.command == "validate-implementation":
            result = validate_implementation(root)
        elif args.command == "issue-live":
            result = issue_live(root, args.artifact_dir, args.window_minutes)
        elif args.command == "record-platform-observation":
            result = record_platform_observation(
                root,
                args.transaction_id,
                datetime.fromisoformat(args.observed_at),
            )
        else:
            result = terminalize(
                root,
                args.transaction_id,
                args.outcome,
                args.saved_version_id,
                args.evidence_zip_sha256,
                args.terminal_log_sha256,
            )
    except (IssuerError, ValueError, json.JSONDecodeError) as error:
        if isinstance(error, IssuerError):
            payload = error.envelope()
        else:
            payload = {
                "error_code": "V2_LIVE_ISSUER_INPUT_INVALID",
                "safe_message": "live-issuer input is invalid",
                "path": None,
            }
        print(json.dumps(payload, sort_keys=True))
        return 2

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
