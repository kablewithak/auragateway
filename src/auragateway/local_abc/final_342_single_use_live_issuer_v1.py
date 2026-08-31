"""Qualify and later issue one single-use final-342 live execution artifact.

Qualification is deterministic and non-issuing. Live issuance is intentionally gated to a
clean synchronized main after this tranche is merged and requires an exact dynamic operator
retype. The issued artifact is transaction-bound, repository-PYTHONPATH independent, and
retains the frozen final manifest, producer, prompt/context, HMAC-prefix, review, budget,
retry, and local-vLLM runtime contracts.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.benchmark import execution as benchmark_execution
from auragateway.context import compiler as context_compiler
from auragateway.contracts.context import StaticAnchorRegistry
from auragateway.contracts.prefix import StaticCompilerSpec
from auragateway.local_abc import final_342_execution_producer_v1 as producer
from auragateway.local_abc import final_342_measured_review_successor_v1 as review_successor
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core
from auragateway.local_abc import final_342_static_execution_authority_binding_v1 as static_binding

BASE_MAIN_COMMIT: Final = "9c11804e05ca2e37fae1116cfccf587670f50bdb"

SOURCE_PATH: Final = Path("src/auragateway/local_abc/final_342_single_use_live_issuer_v1.py")
TEST_PATH: Final = Path("tests/unit/local_abc/test_final_342_single_use_live_issuer_v1.py")
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/final_342_transaction_bound_live_execution_v1.py.tmpl"
)
QUALIFICATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_single_use_live_issuer_qualification_v1.json"
)

LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_single_use_live_issuer_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_single_use_live_issuer_v1_live_manifest.json"
)
PLATFORM_OBSERVATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_single_use_live_issuer_v1_platform_observation.json"
)
TERMINAL_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_single_use_live_issuer_v1_terminal.json"
)

STATIC_BINDING_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_static_execution_authority_binding_v1.json"
)
FINAL_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/freeze-v3/final_342_execution_manifest_v1.json"
)
CUSTODY_PATH: Final = Path(
    "data/evals/benchmark/freeze-v3/final_342_execution_manifest_post_commit_custody_v1.json"
)
PRODUCER_PATH: Final = Path("src/auragateway/local_abc/final_342_execution_producer_v1.py")
CORE_PATH: Final = Path("src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py")
P5_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
REQUEST_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1.py"
)
OUTPUT_ADMISSION_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_output_admission_runtime.py"
)
REVIEW_SUCCESSOR_PATH: Final = Path(
    "src/auragateway/local_abc/final_342_measured_review_successor_v1.py"
)
REVIEW_DESIGN_PATH: Final = Path("src/auragateway/local_abc/final_342_measured_review_design_v1.py")
SEAM_AUDIT_PATH: Final = Path(
    "src/auragateway/local_abc/final_342_producer_review_analysis_seam_audit_v1.py"
)

LEDGER_PATH: Final = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
EPISODES_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
RUNTIME_SELECTION_PATH: Final = Path("data/evals/episodes/runtime-v1/selection.json")
SOURCE_MANIFEST_PATH: Final = Path("data/corpus/source_manifest.json")
COMPILER_SPEC_PATH: Final = Path("data/context/compiler_spec.json")
STATIC_REGISTRY_PATH: Final = Path("data/context/static_anchor_registry.json")
GENERATION_CONTRACT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/generation_contract.json"
)
STRICT_RESPONSE_FORMAT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/strict_response_format.json"
)
ADMISSION_SPEC_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"
)

EXPECTED_GIT_BLOBS: Final[dict[str, str]] = {
    STATIC_BINDING_RECORD_PATH.as_posix(): "fe538777a19699fbcecbb4fa19cdf28264b5615c",
    FINAL_MANIFEST_PATH.as_posix(): "2c733e930b88bca5f8ad0730d6828a88f8655e14",
    CUSTODY_PATH.as_posix(): "b1dfbbdc81cc07bda94dda71ab6983d6d069b01c",
    PRODUCER_PATH.as_posix(): "9bedae7c7815e80d7c03ccc37b1e5261310056cf",
    CORE_PATH.as_posix(): "7edeb7cb3f6c2213868d23863c33a9a94669468c",
    P5_RUNTIME_PATH.as_posix(): "60aa9ee71eb1dfc6b92bf6b6b06ee5ad1386900c",
    REQUEST_ADAPTER_PATH.as_posix(): "ef3908396ebb3e7183c95a577bacffefcf17b696",
    OUTPUT_ADMISSION_PATH.as_posix(): "8d5a32bdd4da237f7554598ebe2d359c073d9cf1",
    REVIEW_SUCCESSOR_PATH.as_posix(): "aee9891d5fa5a23621d4e2c7fb20b575e6f43aaf",
    REVIEW_DESIGN_PATH.as_posix(): "673091128975b2fc33ba175649c8e82b2670a522",
    SEAM_AUDIT_PATH.as_posix(): "f271f2746effc77b03147a7c9929e30c8c563e2e",
    LEDGER_PATH.as_posix(): "553b23e24629bdca81d9fb9fdcbd90cc2081caf0",
    EPISODES_PATH.as_posix(): "b8e6a9c0a0097b0755acf9b47ac332792ffaaeac",
    RUNTIME_SELECTION_PATH.as_posix(): "3340765b2a2ad9f59bec69f0dbc3ba22944aaf81",
    SOURCE_MANIFEST_PATH.as_posix(): "e2bffea64a75bd79d1c57b636de7a0bae2486c1d",
    COMPILER_SPEC_PATH.as_posix(): "11bdcc3731bcd181288fd242ee864ffd11ef837a",
    STATIC_REGISTRY_PATH.as_posix(): "eaaae08f58c1d9156e338dbb5d580f11b315bc1c",
    GENERATION_CONTRACT_PATH.as_posix(): "f1e8e8afc06bea8e86f8616a26031c287bc3201b",
    STRICT_RESPONSE_FORMAT_PATH.as_posix(): "c786470fd0d8c4c12200f90a17d619387bad2b60",
    ADMISSION_SPEC_PATH.as_posix(): "2e720fa03b9092666693b6ce6a4eab72921139e2",
}

EXPECTED_MANIFEST_SEMANTIC_SHA256: Final = (
    "11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b"
)
EXPECTED_MANIFEST_FILE_SHA256: Final = (
    "74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c"
)
EXPECTED_REVIEW_SCHEDULE_SHA256: Final = (
    "9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c"
)

AUTHORIZATION_SCOPE: Final = "FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1"
EXPECTED_TRAJECTORIES: Final = 342
EXPECTED_TURNS: Final = 1368
EXPECTED_MAX_ATTEMPTS: Final = 2736
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240
QUALIFICATION_TRANSACTION_ID: Final = hashlib.sha256(
    b"auragateway-final-342-g1114-qualification-v1"
).hexdigest()

NEXT_GATE: Final = "FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY"
NEXT_GATE_AFTER_ISSUE: Final = "FRESH_PLATFORM_READINESS_BEFORE_ONE_GOVERNED_FINAL_342_EXECUTION"
NEXT_GATE_AFTER_OBSERVATION: Final = "ONE_GOVERNED_FINAL_342_EXECUTION"
NEXT_GATE_AFTER_TERMINAL: Final = "PRESERVE_REVIEW_ANALYZE_FINAL_342_MEASURED_EVIDENCE"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class IssuerError(RuntimeError):
    """Metadata-safe final-342 issuer failure."""

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


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise IssuerError("FINAL_342_ISSUER_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(FrozenModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class QualificationBoundary(FrozenModel):
    exact_static_authority_required: Literal[True] = True
    exact_frozen_manifest_required: Literal[True] = True
    exact_final_producer_required: Literal[True] = True
    exact_frozen_context_contract_required: Literal[True] = True
    canonical_hmac_prefix_contract_required: Literal[True] = True
    protected_review_capture_required: Literal[True] = True
    transaction_bound_execution_artifact_required: Literal[True] = True
    repository_pythonpath_required_at_execution: Literal[False] = False
    qualification_may_issue_live_authority: Literal[False] = False
    governed_execution_permitted_during_qualification: Literal[False] = False
    single_use_is_governance_invariant: Literal[True] = True
    authorization_reusable: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    fresh_platform_readiness_required_after_qualification: Literal[True] = True
    fresh_human_authority_required_after_qualification: Literal[True] = True


class QualificationSafety(FrozenModel):
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    network_transport_performed: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False


class QualificationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    qualification_id: Literal["auragateway-final-342-single-use-live-issuer-qualification-v1"]
    status: Literal["QUALIFIED_NOT_ISSUED"]
    source_main_commit: Literal["9c11804e05ca2e37fae1116cfccf587670f50bdb"]
    authorization_scope: Literal["FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1"]
    source: ArtifactReceipt
    test: ArtifactReceipt
    live_execution_template: ArtifactReceipt
    transaction_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_rendered_wrapper_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bootstrap_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_static_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_review_schedule_sha256: Literal[
        "9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c"
    ]
    planned_trajectory_count: Literal[342] = 342
    planned_turn_count: Literal[1368] = 1368
    maximum_request_attempt_count: Literal[2736] = 2736
    qualification_boundary: QualificationBoundary
    safety_state: QualificationSafety
    next_gate: Literal["FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY"]


class LiveAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str = Field(min_length=16)
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1"] = AUTHORIZATION_SCOPE
    issued_at: datetime
    expires_at: datetime
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    static_authority_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_manifest_semantic_sha256: Literal[
        "11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b"
    ]
    final_manifest_file_sha256: Literal[
        "74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c"
    ]
    live_execution_template_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transaction_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prefix_hmac_key_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prefix_hmac_key_id: str = Field(min_length=8, max_length=80)
    planned_trajectory_count: Literal[342] = 342
    planned_turn_count: Literal[1368] = 1368
    maximum_request_attempt_count: Literal[2736] = 2736
    maximum_retries_after_initial_attempt: Literal[1] = 1
    hidden_retries_permitted: Literal[False] = False
    replacement_cases_permitted: Literal[False] = False
    extra_authority_canary_requests_permitted: Literal[False] = False
    extra_worker_qualification_requests_permitted: Literal[False] = False
    external_spend_ceiling: Literal[0] = 0
    final_measured_abc_execution_authorized: Literal[True] = True
    new_execution_authorized: Literal[True] = True
    single_use: Literal[True] = True
    authorization_reusable: Literal[False] = False
    unchanged_replay_authorized: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    fresh_platform_observation_required_before_execution: Literal[True] = True
    platform_observation_runtime_input: Literal[False] = False

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        return self


def canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise IssuerError(
            "FINAL_342_ISSUER_REQUIRED_FILE_MISSING",
            "required issuer input is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _load_object(root: Path, relative: Path) -> dict[str, object]:
    try:
        value = json.loads(_read_required(root, relative))
    except json.JSONDecodeError as error:
        raise IssuerError(
            "FINAL_342_ISSUER_JSON_INVALID",
            "required issuer JSON is invalid",
            relative,
        ) from error
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise IssuerError(
            "FINAL_342_ISSUER_JSON_INVALID",
            "required issuer JSON root is invalid",
            relative,
        )
    return cast(dict[str, object], value)


def _git_text(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed.returncode != 0:
        raise IssuerError(
            "FINAL_342_ISSUER_GIT_FAILED",
            "required Git inspection failed",
        )
    return completed.stdout.strip()


def _git_bytes(root: Path, revision_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", revision_path],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise IssuerError(
            "FINAL_342_ISSUER_GIT_SHOW_FAILED",
            "required Git bytes could not be read",
        )
    return completed.stdout


def _require_base_ancestor(root: Path, *, exact: bool) -> None:
    head = _git_text(root, "rev-parse", "HEAD")
    if exact and head != BASE_MAIN_COMMIT:
        raise IssuerError(
            "FINAL_342_ISSUER_SOURCE_MAIN_DRIFT",
            "qualification materialization must begin from exact accepted main",
        )
    completed = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise IssuerError(
            "FINAL_342_ISSUER_BASE_NOT_ANCESTOR",
            "accepted G11.14 base main is not an ancestor",
        )


def _require_upstream_unchanged(root: Path) -> None:
    for path_text, expected_blob in EXPECTED_GIT_BLOBS.items():
        relative = Path(path_text)
        observed_blob = _git_text(
            root,
            "rev-parse",
            f"{BASE_MAIN_COMMIT}:{relative.as_posix()}",
        )
        if observed_blob != expected_blob:
            raise IssuerError(
                "FINAL_342_ISSUER_BASE_BLOB_DRIFT",
                "accepted upstream Git blob identity drifted",
                relative,
            )
        accepted = _git_bytes(root, f"{BASE_MAIN_COMMIT}:{relative.as_posix()}")
        if _read_required(root, relative) != accepted:
            raise IssuerError(
                "FINAL_342_ISSUER_UPSTREAM_WORKTREE_DRIFT",
                "accepted upstream bytes differ from G11.14 base main",
                relative,
            )


def _receipt(root: Path, relative: Path) -> ArtifactReceipt:
    payload = _read_required(root, relative)
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _validate_static_subject(root: Path) -> None:
    static_result = static_binding.validate(root)
    expected_static = {
        "static_authority_binding_complete": True,
        "repository_execution_manifest_frozen": True,
        "live_authorization_issued": False,
        "final_measured_abc_execution_authorized": False,
        "model_requests_performed": 0,
    }
    if any(static_result.get(key) != value for key, value in expected_static.items()):
        raise IssuerError(
            "FINAL_342_ISSUER_STATIC_AUTHORITY_DRIFT",
            "static execution-authority binding no longer matches the accepted subject",
            STATIC_BINDING_RECORD_PATH,
        )

    producer_result = producer.validate(root)
    expected_producer = {
        "status": "FINAL_342_EXECUTION_PRODUCER_V1_IMPLEMENTATION_VALID",
        "planned_trajectory_count": EXPECTED_TRAJECTORIES,
        "planned_turn_count": EXPECTED_TURNS,
        "maximum_request_attempt_count": EXPECTED_MAX_ATTEMPTS,
        "final_measured_abc_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
    }
    if any(producer_result.get(key) != value for key, value in expected_producer.items()):
        raise IssuerError(
            "FINAL_342_ISSUER_PRODUCER_DRIFT",
            "final execution producer no longer matches the accepted subject",
            PRODUCER_PATH,
        )


def _source_documents(root: Path) -> dict[str, dict[str, object]]:
    manifest = _load_object(root, SOURCE_MANIFEST_PATH)
    raw_artifacts = manifest.get("artifacts")
    if manifest.get("status") != "frozen" or not isinstance(raw_artifacts, list):
        raise IssuerError(
            "FINAL_342_ISSUER_SOURCE_MANIFEST_INVALID",
            "frozen source manifest is invalid",
            SOURCE_MANIFEST_PATH,
        )

    documents: dict[str, dict[str, object]] = {}
    for raw in raw_artifacts:
        if not isinstance(raw, dict):
            raise IssuerError(
                "FINAL_342_ISSUER_SOURCE_MANIFEST_INVALID",
                "source manifest artifact is invalid",
                SOURCE_MANIFEST_PATH,
            )
        source_id = raw.get("source_id")
        document_path = raw.get("document_path")
        expected_sha = raw.get("sha256")
        expected_bytes = raw.get("byte_count")
        if (
            not isinstance(source_id, str)
            or not isinstance(document_path, str)
            or not isinstance(expected_sha, str)
            or _SHA256.fullmatch(expected_sha) is None
            or not isinstance(expected_bytes, int)
        ):
            raise IssuerError(
                "FINAL_342_ISSUER_SOURCE_MANIFEST_INVALID",
                "source manifest artifact identity is invalid",
                SOURCE_MANIFEST_PATH,
            )
        payload = _read_required(root, Path(document_path))
        if sha256_bytes(payload) != expected_sha or len(payload) != expected_bytes:
            raise IssuerError(
                "FINAL_342_ISSUER_SOURCE_DOCUMENT_DRIFT",
                "frozen source document identity drifted",
                Path(document_path),
            )
        documents[source_id] = {
            "sha256": expected_sha,
            "byte_count": expected_bytes,
            "b64": base64.b64encode(payload).decode("ascii"),
        }
    return documents


def _canonical_static_payload(root: Path) -> bytes:
    spec = StaticCompilerSpec.model_validate_json(_read_required(root, COMPILER_SPEC_PATH))
    registry = StaticAnchorRegistry.model_validate_json(_read_required(root, STATIC_REGISTRY_PATH))
    payload = context_compiler.build_canonical_static_payload(root, spec, registry)
    return context_compiler.serialize_static_payload(payload)


def _frozen_static_prompt(root: Path) -> str:
    spec = StaticCompilerSpec.model_validate_json(_read_required(root, COMPILER_SPEC_PATH))
    reference = benchmark_execution._static_system_prompt(spec)
    payload = {
        "runtime_prompt_profile": "development-live-compact-v1",
        "serialization_version": spec.serialization_version,
        "template_id": spec.template_id,
        "template_version": spec.template_version,
        "segments": [item.model_dump(mode="json") for item in spec.segments],
        "tools": [item.model_dump(mode="json") for item in spec.tools],
        "output_schema": spec.output_schema.model_dump(mode="json"),
        "context_pack": spec.context_pack.model_dump(mode="json"),
        "response_rule": (
            "Return exactly one JSON object. Do not use Markdown fences, commentary, "
            "or fields outside the frozen terminal-decision schema."
        ),
    }
    observed = context_compiler.canonical_json_bytes(payload).decode("utf-8")
    if observed != reference:
        raise IssuerError(
            "FINAL_342_ISSUER_STATIC_PROMPT_PARITY_FAILED",
            "final static prompt no longer matches frozen v1 prompt realization",
            COMPILER_SPEC_PATH,
        )
    return observed


def _bootstrap_state(root: Path) -> producer.ProducerState:
    return producer.initial_state(
        root,
        transaction_id=QUALIFICATION_TRANSACTION_ID,
        final_execution_manifest_sha256=EXPECTED_MANIFEST_SEMANTIC_SHA256,
    )


def _bootstrap_sha(state: producer.ProducerState) -> str:
    payload = producer.canonical_json(state.model_dump(mode="json")).encode("utf-8")
    return sha256_bytes(payload)


def _module_entry(root: Path, relative: Path) -> dict[str, object]:
    payload = _read_required(root, relative)
    return {
        "sha256": sha256_bytes(payload),
        "b64": base64.b64encode(payload).decode("ascii"),
    }


def build_transaction_material(root: Path) -> bytes:
    _require_upstream_unchanged(root)
    _validate_static_subject(root)

    ledger = core.load_runtime_plan(root)
    if (
        len(ledger.runs) != EXPECTED_TRAJECTORIES
        or ledger.maximum_request_attempt_count != EXPECTED_MAX_ATTEMPTS
        or sum(len(core.realize_run(run)) for run in ledger.runs) != EXPECTED_TURNS
    ):
        raise IssuerError(
            "FINAL_342_ISSUER_PLAN_DRIFT",
            "frozen final-342 plan shape drifted",
            LEDGER_PATH,
        )

    bootstrap = _bootstrap_state(root)
    canonical_static = _canonical_static_payload(root)
    _frozen_static_prompt(root)

    test_key = b"\x42" * 32
    spec = StaticCompilerSpec.model_validate_json(_read_required(root, COMPILER_SPEC_PATH))
    registry = StaticAnchorRegistry.model_validate_json(_read_required(root, STATIC_REGISTRY_PATH))
    fingerprint = context_compiler.fingerprint_static_context(
        root,
        spec,
        registry,
        test_key,
        "g1114-qualification-key",
    )
    expected_hmac = hmac.new(test_key, canonical_static, hashlib.sha256).hexdigest()
    if fingerprint.prefix_fingerprint != expected_hmac:
        raise IssuerError(
            "FINAL_342_ISSUER_HMAC_PREFIX_PARITY_FAILED",
            "canonical HMAC prefix realization drifted",
            COMPILER_SPEC_PATH,
        )

    protected_schedule = review_successor.protected_schedule_bytes(root)
    if sha256_bytes(protected_schedule) != EXPECTED_REVIEW_SCHEDULE_SHA256:
        raise IssuerError(
            "FINAL_342_ISSUER_REVIEW_SCHEDULE_DRIFT",
            "protected final-342 review schedule digest drifted",
        )

    modules = {
        "core": _module_entry(root, CORE_PATH),
        "producer": _module_entry(root, PRODUCER_PATH),
        "p5_runtime": _module_entry(root, P5_RUNTIME_PATH),
        "request_adapter": _module_entry(root, REQUEST_ADAPTER_PATH),
        "output_admission": _module_entry(root, OUTPUT_ADMISSION_PATH),
        "review_design": _module_entry(root, REVIEW_DESIGN_PATH),
        "seam_audit": _module_entry(root, SEAM_AUDIT_PATH),
        "review_successor": _module_entry(root, REVIEW_SUCCESSOR_PATH),
    }

    assets = {
        "ledger": _module_entry(root, LEDGER_PATH),
        "episodes": _module_entry(root, EPISODES_PATH),
        "runtime_selection": _module_entry(root, RUNTIME_SELECTION_PATH),
        "source_manifest": _module_entry(root, SOURCE_MANIFEST_PATH),
        "compiler_spec": _module_entry(root, COMPILER_SPEC_PATH),
        "generation_contract": _module_entry(root, GENERATION_CONTRACT_PATH),
        "strict_response_format": _module_entry(root, STRICT_RESPONSE_FORMAT_PATH),
        "admission_spec": _module_entry(root, ADMISSION_SPEC_PATH),
        "final_manifest": _module_entry(root, FINAL_MANIFEST_PATH),
        "static_authority_binding": _module_entry(root, STATIC_BINDING_RECORD_PATH),
    }

    material = {
        "schema_version": "1.0.0",
        "material_id": "auragateway-final-342-transaction-material-v1",
        "modules": modules,
        "assets": assets,
        "source_documents": _source_documents(root),
        "source_bindings": [item.model_dump(mode="json") for item in bootstrap.source_bindings],
        "canonical_static_payload": {
            "sha256": sha256_bytes(canonical_static),
            "b64": base64.b64encode(canonical_static).decode("ascii"),
        },
        "protected_review_schedule": {
            "sha256": EXPECTED_REVIEW_SCHEDULE_SHA256,
            "b64": base64.b64encode(protected_schedule).decode("ascii"),
        },
        "qualification_transaction_id": QUALIFICATION_TRANSACTION_ID,
        "qualification_bootstrap_state_sha256": _bootstrap_sha(bootstrap),
        "final_manifest_semantic_sha256": EXPECTED_MANIFEST_SEMANTIC_SHA256,
        "final_manifest_file_sha256": EXPECTED_MANIFEST_FILE_SHA256,
        "planned_trajectory_count": EXPECTED_TRAJECTORIES,
        "planned_turn_count": EXPECTED_TURNS,
        "maximum_request_attempt_count": EXPECTED_MAX_ATTEMPTS,
        "frozen_prompt_profile": "development-live-compact-v1",
        "prefix_fingerprint_contract": "hmac-sha256-static-prefix-v1",
    }
    return canonical_bytes(material)


def _render_template(
    root: Path,
    *,
    material: bytes,
    live_enabled: bool,
    authorization_envelope: bytes,
    hmac_key: bytes,
) -> bytes:
    template = _read_required(root, TEMPLATE_PATH).decode("utf-8")
    replacements = {
        "__TRANSACTION_MATERIAL_B64__": base64.b64encode(material).decode("ascii"),
        "__TRANSACTION_MATERIAL_SHA256__": sha256_bytes(material),
        "__LIVE_EXECUTION_ENABLED__": "True" if live_enabled else "False",
        "__AUTHORIZATION_B64__": base64.b64encode(authorization_envelope).decode("ascii"),
        "__PREFIX_HMAC_KEY_B64__": base64.b64encode(hmac_key).decode("ascii"),
    }
    rendered = template
    for token, value in replacements.items():
        if token not in rendered:
            raise IssuerError(
                "FINAL_342_ISSUER_TEMPLATE_TOKEN_MISSING",
                "required live-execution template token is missing",
                TEMPLATE_PATH,
            )
        rendered = rendered.replace(token, value)
    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
    if unresolved:
        raise IssuerError(
            "FINAL_342_ISSUER_TEMPLATE_UNRESOLVED",
            "live-execution template retained unresolved governed tokens",
            TEMPLATE_PATH,
        )
    return rendered.encode("utf-8")


def _qualification_wrapper(root: Path, material: bytes) -> bytes:
    envelope = canonical_bytes(
        {
            "schema_version": "1.0.0",
            "decision": "QUALIFICATION_ONLY",
            "live_authorization_issued": False,
            "final_measured_abc_execution_authorized": False,
        }
    )
    return _render_template(
        root,
        material=material,
        live_enabled=False,
        authorization_envelope=envelope,
        hmac_key=b"\x00" * 32,
    )


def _exercise_qualification_wrapper(wrapper: bytes) -> dict[str, object]:
    with tempfile.TemporaryDirectory(
        prefix="auragateway-final-342-g1114-qualification-"
    ) as directory:
        path = Path(directory) / "final_342_qualification_wrapper.py"
        path.write_bytes(wrapper)
        env = {
            key: value
            for key, value in os.environ.items()
            if key != "PYTHONPATH" and not key.startswith("AURAGATEWAY_")
        }
        completed = subprocess.run(
            [sys.executable, str(path), "--qualify"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=120,
        )
        if completed.returncode != 0:
            raise IssuerError(
                "FINAL_342_ISSUER_WRAPPER_QUALIFICATION_FAILED",
                "transaction-bound wrapper qualification subprocess failed",
                TEMPLATE_PATH,
            )
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise IssuerError(
                "FINAL_342_ISSUER_WRAPPER_QUALIFICATION_INVALID",
                "transaction-bound wrapper qualification output is invalid",
                TEMPLATE_PATH,
            ) from error
        if not isinstance(value, dict):
            raise IssuerError(
                "FINAL_342_ISSUER_WRAPPER_QUALIFICATION_INVALID",
                "transaction-bound wrapper qualification output shape is invalid",
                TEMPLATE_PATH,
            )
        return cast(dict[str, object], value)


def build_qualification_record(root: Path) -> QualificationRecord:
    root = root.resolve()
    _require_base_ancestor(root, exact=False)
    material = build_transaction_material(root)
    wrapper = _qualification_wrapper(root, material)
    wrapper_result = _exercise_qualification_wrapper(wrapper)

    expected = {
        "status": "FINAL_342_TRANSACTION_BOUND_LIVE_EXECUTION_QUALIFICATION_PASS",
        "planned_trajectory_count": EXPECTED_TRAJECTORIES,
        "planned_turn_count": EXPECTED_TURNS,
        "maximum_request_attempt_count": EXPECTED_MAX_ATTEMPTS,
        "repository_pythonpath_required": False,
        "live_execution_enabled": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "network_transport_performed": False,
    }
    if any(wrapper_result.get(key) != value for key, value in expected.items()):
        raise IssuerError(
            "FINAL_342_ISSUER_WRAPPER_QUALIFICATION_DRIFT",
            "transaction-bound wrapper qualification semantics drifted",
            TEMPLATE_PATH,
        )

    bootstrap_sha = wrapper_result.get("bootstrap_state_sha256")
    static_sha = wrapper_result.get("canonical_static_payload_sha256")
    if (
        not isinstance(bootstrap_sha, str)
        or _SHA256.fullmatch(bootstrap_sha) is None
        or not isinstance(static_sha, str)
        or _SHA256.fullmatch(static_sha) is None
    ):
        raise IssuerError(
            "FINAL_342_ISSUER_WRAPPER_QUALIFICATION_INVALID",
            "transaction-bound wrapper qualification identities are invalid",
            TEMPLATE_PATH,
        )

    return QualificationRecord(
        qualification_id=("auragateway-final-342-single-use-live-issuer-qualification-v1"),
        status="QUALIFIED_NOT_ISSUED",
        source_main_commit=BASE_MAIN_COMMIT,
        authorization_scope=AUTHORIZATION_SCOPE,
        source=_receipt(root, SOURCE_PATH),
        test=_receipt(root, TEST_PATH),
        live_execution_template=_receipt(root, TEMPLATE_PATH),
        transaction_material_sha256=sha256_bytes(material),
        qualification_rendered_wrapper_sha256=sha256_bytes(wrapper),
        bootstrap_state_sha256=bootstrap_sha,
        canonical_static_payload_sha256=static_sha,
        protected_review_schedule_sha256=EXPECTED_REVIEW_SCHEDULE_SHA256,
        qualification_boundary=QualificationBoundary(),
        safety_state=QualificationSafety(),
        next_gate=NEXT_GATE,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.g1114.tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    temporary.replace(path)


def materialize_qualification(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _require_base_ancestor(root, exact=True)
    record = build_qualification_record(root)
    _write_atomic(
        root / QUALIFICATION_RECORD_PATH,
        canonical_bytes(record),
    )
    return validate_qualification(root)


def validate_qualification(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected = build_qualification_record(root)
    path = root / QUALIFICATION_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise IssuerError(
            "FINAL_342_ISSUER_QUALIFICATION_RECORD_MISSING",
            "G11.14 qualification record is missing or unsafe",
            QUALIFICATION_RECORD_PATH,
        )
    try:
        observed = QualificationRecord.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise IssuerError(
            "FINAL_342_ISSUER_QUALIFICATION_RECORD_INVALID",
            "G11.14 qualification record failed typed validation",
            QUALIFICATION_RECORD_PATH,
        ) from error
    if observed != expected:
        raise IssuerError(
            "FINAL_342_ISSUER_QUALIFICATION_RECORD_DRIFT",
            "G11.14 qualification record differs from deterministic reconstruction",
            QUALIFICATION_RECORD_PATH,
        )
    if path.read_bytes() != canonical_bytes(observed):
        raise IssuerError(
            "FINAL_342_ISSUER_QUALIFICATION_BYTES_DRIFT",
            "G11.14 qualification record bytes are not canonical",
            QUALIFICATION_RECORD_PATH,
        )
    return {
        "status": "FINAL_342_SINGLE_USE_LIVE_ISSUER_V1_QUALIFIED_NOT_ISSUED",
        "transaction_bound_execution_artifact_required": True,
        "repository_pythonpath_required_at_execution": False,
        "canonical_hmac_prefix_contract_bound": True,
        "protected_review_capture_bound": True,
        "planned_trajectory_count": EXPECTED_TRAJECTORIES,
        "planned_turn_count": EXPECTED_TURNS,
        "maximum_request_attempt_count": EXPECTED_MAX_ATTEMPTS,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "network_transport_performed": False,
        "live_authorization_issued": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": NEXT_GATE,
    }


def _require_clean_synchronized_main(root: Path) -> str:
    branch = _git_text(root, "branch", "--show-current")
    if branch != "main":
        raise IssuerError(
            "FINAL_342_ISSUER_REQUIRES_MAIN",
            "live issuance may only occur from main",
        )
    _git_text(root, "fetch", "origin", "main")
    head = _git_text(root, "rev-parse", "HEAD")
    origin = _git_text(root, "rev-parse", "origin/main")
    if head != origin:
        raise IssuerError(
            "FINAL_342_ISSUER_MAIN_NOT_SYNCHRONIZED",
            "local main must exactly match origin/main before live issuance",
        )
    if _git_text(root, "status", "--porcelain"):
        raise IssuerError(
            "FINAL_342_ISSUER_WORKTREE_NOT_CLEAN",
            "live issuance requires a clean synchronized main worktree",
        )
    return head


def issue_live(
    repo_root: Path,
    artifact_dir: Path,
    window_minutes: int,
) -> dict[str, object]:
    root = repo_root.resolve()
    if window_minutes < 1 or window_minutes > MAX_WINDOW_MINUTES:
        raise IssuerError(
            "FINAL_342_ISSUER_WINDOW_INVALID",
            "authorization window is outside the permitted bound",
        )

    issuer_commit = _require_clean_synchronized_main(root)
    validate_qualification(root)

    qualification_bytes = _read_required(root, QUALIFICATION_RECORD_PATH)
    source_bytes = _read_required(root, SOURCE_PATH)
    static_bytes = _read_required(root, STATIC_BINDING_RECORD_PATH)
    template_bytes = _read_required(root, TEMPLATE_PATH)
    material = build_transaction_material(root)

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=window_minutes)
    challenge = sha256_bytes(
        secrets.token_bytes(32)
        + issuer_commit.encode("ascii")
        + issued_at.isoformat().encode("ascii")
        + sha256_bytes(qualification_bytes).encode("ascii")
    )
    print("RETYPE_DYNAMIC_SHA256_CHALLENGE=" + challenge)
    confirmed = input("Retype the exact challenge to issue FINAL-342 live authority: ").strip()
    if confirmed != challenge:
        raise IssuerError(
            "FINAL_342_ISSUER_OPERATOR_CONFIRMATION_FAILED",
            "dynamic SHA-256 challenge confirmation failed",
        )

    hmac_key = secrets.token_bytes(32)
    hmac_key_id = "final-342-prefix-" + secrets.token_hex(8)
    authorization = LiveAuthorization(
        authorization_id="final-342-tx-" + secrets.token_hex(16),
        issued_at=issued_at,
        expires_at=expires_at,
        issuer_merge_commit=issuer_commit,
        issuer_source_sha256=sha256_bytes(source_bytes),
        qualification_record_sha256=sha256_bytes(qualification_bytes),
        static_authority_binding_sha256=sha256_bytes(static_bytes),
        final_manifest_semantic_sha256=EXPECTED_MANIFEST_SEMANTIC_SHA256,
        final_manifest_file_sha256=EXPECTED_MANIFEST_FILE_SHA256,
        live_execution_template_sha256=sha256_bytes(template_bytes),
        transaction_material_sha256=sha256_bytes(material),
        prefix_hmac_key_sha256=sha256_bytes(hmac_key),
        prefix_hmac_key_id=hmac_key_id,
    )
    authorization_bytes = canonical_bytes(authorization)
    transaction_id = sha256_bytes(authorization_bytes)
    envelope = canonical_bytes(
        {
            "transaction_id": transaction_id,
            "authorization": authorization.model_dump(mode="json"),
        }
    )
    wrapper = _render_template(
        root,
        material=material,
        live_enabled=True,
        authorization_envelope=envelope,
        hmac_key=hmac_key,
    )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    executable_path = artifact_dir / "auragateway_final_342_transaction_bound_v1.py"
    executable_path.write_bytes(wrapper)

    live_record = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "authorization": authorization.model_dump(mode="json"),
    }
    _write_atomic(root / LIVE_AUTHORIZATION_PATH, canonical_bytes(live_record))

    manifest = {
        "schema_version": "1.0.0",
        "status": "FINAL_342_TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        "transaction_id": transaction_id,
        "issuer_merge_commit": issuer_commit,
        "qualification_record_sha256": sha256_bytes(qualification_bytes),
        "static_authority_binding_sha256": sha256_bytes(static_bytes),
        "transaction_material_sha256": sha256_bytes(material),
        "live_execution_template_sha256": sha256_bytes(template_bytes),
        "executable_sha256": sha256_bytes(wrapper),
        "planned_trajectory_count": EXPECTED_TRAJECTORIES,
        "planned_turn_count": EXPECTED_TURNS,
        "maximum_request_attempt_count": EXPECTED_MAX_ATTEMPTS,
        "single_use_governance": True,
        "authorization_reusable": False,
        "runtime_anti_replay_established": False,
        "platform_observation_required_before_execution": True,
        "platform_observation_persisted": False,
        "model_requests_performed_during_issuance": 0,
        "gpu_execution_performed_during_issuance": False,
        "network_transport_performed_during_issuance": False,
        "final_measured_abc_execution_authorized": True,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }
    _write_atomic(root / LIVE_MANIFEST_PATH, canonical_bytes(manifest))
    return manifest


def record_platform_observation(
    repo_root: Path,
    transaction_id: str,
    observed_at: datetime,
) -> dict[str, object]:
    root = repo_root.resolve()
    live = _load_object(root, LIVE_AUTHORIZATION_PATH)
    manifest = _load_object(root, LIVE_MANIFEST_PATH)
    if (
        live.get("transaction_id") != transaction_id
        or manifest.get("transaction_id") != transaction_id
    ):
        raise IssuerError(
            "FINAL_342_ISSUER_TRANSACTION_MISMATCH",
            "platform observation transaction identity mismatch",
        )
    receipt = {
        "schema_version": "1.0.0",
        "control_id": "FINAL_342_FRESH_PLATFORM_READINESS_V1",
        "transaction_id": transaction_id,
        "platform_observed_at": observed_at.astimezone(UTC).isoformat(),
        "accelerator": "T4_X2",
        "allocated_gpu_count": 2,
        "internet_enabled": False,
        "authorization_specific_kaggle_input_count": 0,
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "persisted_before_governed_execution": True,
        "receipt_runtime_input": False,
    }
    _write_atomic(root / PLATFORM_OBSERVATION_PATH, canonical_bytes(receipt))
    return {
        "status": "FINAL_342_FRESH_PLATFORM_OBSERVATION_PERSISTED",
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
    live = _load_object(root, LIVE_AUTHORIZATION_PATH)
    if live.get("transaction_id") != transaction_id:
        raise IssuerError(
            "FINAL_342_ISSUER_TRANSACTION_MISMATCH",
            "terminalization transaction identity mismatch",
        )
    permitted = {"PASSED", "FAILED", "INTERRUPTED", "AMBIGUOUS"}
    if outcome not in permitted:
        raise IssuerError(
            "FINAL_342_ISSUER_TERMINAL_OUTCOME_INVALID",
            "terminal execution outcome is invalid",
        )
    if outcome == "PASSED" and (
        saved_version_id is None or evidence_zip_sha256 is None or terminal_log_sha256 is None
    ):
        raise IssuerError(
            "FINAL_342_ISSUER_PASS_EVIDENCE_REQUIRED",
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
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "runtime_anti_replay_established": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }
    _write_atomic(root / TERMINAL_PATH, canonical_bytes(record))
    return record


def _parser() -> _Parser:
    parser = _Parser(prog="final-342-single-use-live-issuer-v1")
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("materialize-qualification", "validate-qualification"):
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
        if args.command == "materialize-qualification":
            result = materialize_qualification(root)
        elif args.command == "validate-qualification":
            result = validate_qualification(root)
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
    except (
        IssuerError,
        OSError,
        ValueError,
        ValidationError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, IssuerError):
            payload = error.envelope()
        else:
            payload = {
                "error_code": "FINAL_342_ISSUER_FAILED",
                "safe_message": "final-342 issuer input or qualification failed",
                "path": None,
            }
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
