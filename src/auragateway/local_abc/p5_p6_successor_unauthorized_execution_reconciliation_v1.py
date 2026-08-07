"""Preserve and reconcile one technically successful but ungoverned successor run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, cast

from pydantic import Field, ValidationError, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_COMMIT: Final = "a5a71181fd48965730d00e63f7bd456714fa4048"
IMPLEMENTATION_MERGE_COMMIT: Final = "6e424acb27e568bb7ce5000ea0732e175bf6b35a"
SAVED_VERSION_ID: Final = 340872949
NOTEBOOK_NAME: Final = "ag-p5-p6-successor-runtime-qual-v1"
RUNTIME_SCRIPT_SHA256: Final = "5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"
NOTEBOOK_SHA256: Final = "113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8"
WRAPPER_CODE_SHA256: Final = "f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"
EVIDENCE_ZIP_SHA256: Final = "7f14ab45aeb4abd858c9905ca06553bd325f21035d5d9d7533424fbadfa47583"
EVIDENCE_ZIP_SIZE_BYTES: Final = 22587
TERMINAL_LOG_SHA256: Final = "a3c7649351732b699433e97fc8e7da3076f0715c343ef709761ae60b0b252854"
TERMINAL_LOG_SIZE_BYTES: Final = 3552

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_unauthorized_execution_reconciliation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_successor_unauthorized_execution_reconciliation_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-08-local-abc-p5-p6-successor-unauthorized-execution-reconciliation-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Successor_Unauthorized_Execution_Reconciliation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_successor_unauthorized_execution_reconciliation_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_unauthorized_execution_reconciliation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_unauthorized_execution_reconciliation_v1_record.json"
)

AUTHORIZATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_v1_record.json"
)
AUTHORIZATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_authorization_v1_review.json"
)
RUNTIME_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_record.json"
)
RUNTIME_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_runtime_qualification_v1_implementation_review.json"
)
RUNTIME_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_runtime_qualification_v1_request.json"
)
AUTHORIZATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_execution_authorization_v1.py"
)
RUNTIME_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1.py"
)

EXPECTED_REPO_ARTIFACT_SHA256: Final = {
    AUTHORIZATION_RECORD_PATH: ("6d490e85fdd0b73dbe104bffdd4a82f3bc668b7307c8c92adec6c8e781e11f69"),
    AUTHORIZATION_REVIEW_PATH: ("3a30ccd7d3734ec90871bc66997c44e09e53e548a4c2c7296b063cbbbf6242b8"),
    RUNTIME_RECORD_PATH: ("386d2fa9b3695ba664316f05ad805e01cac74d317ff9568a813a03127dc86285"),
    RUNTIME_REVIEW_PATH: ("ddeb10a6c76f6187d8654dd8a02d4574fdbc428e9b99bd806178ea48da119cfb"),
    RUNTIME_REQUEST_PATH: ("a341d81489255c25c95a3fd70962e214c0841e9eee8ff5bd54faef02dd60d07a"),
    AUTHORIZATION_SOURCE_PATH: ("f14e3be01cdca6a90ae7c4ab0faff158163f547e64873d917e911dbf70afdfa2"),
    RUNTIME_SOURCE_PATH: ("a8c5741b6385a5f9393679a77b2c55b9d8bfbfeb32351c3d3708b21d6f4ebd82"),
}

EXPECTED_EVIDENCE_MEMBERS: Final = (
    (
        "runtime_source_identity_report_v1.json",
        "3824a067947268e0750713f879faf0b8b7d364c35377f6c0419f47b8227b1511",
        425,
    ),
    (
        "runtime_install_report_v1.json",
        "e8734b3b0cbd9ce8213832cd85e2fbcfb3f1f47f25654429074f5157d220c130",
        20636,
    ),
    (
        "runtime_environment_report_v1.json",
        "a627ba1e93982120fd8ee70700f7761e3d4069a165ebe249a578319be5fb73df",
        362,
    ),
    (
        "runtime_import_closure_report_v1.json",
        "f54897defb8c382243c045f73d3f772aff71824adab2bb12570854ed8c838426",
        4734,
    ),
    (
        "p3_worker_startup_report_v1.json",
        "1877521e50e7c507a1ff6cb6217a7ed24ab715f5318abb91dfb21be950255189",
        6555,
    ),
    (
        "p3_native_origin_report_v1.json",
        "f5cccecaa60d9e90330c6b2942d9b6eb9006c13f9c261aee0645bb0ef9ab9cb1",
        12248,
    ),
    (
        "p4_case_a_canary_report_v1.json",
        "b3e37915c5422a11109bad16f00712092580a8731ec863c8785ed5c223ede5ea",
        1069,
    ),
    (
        "p5_prefix_cache_reset_report_v1.json",
        "ec253b9f7f2f2d349f07d6dc58885a9719344e438473e16d4c7f41a3ca04cc1c",
        2817,
    ),
    (
        "p5_post_restart_native_origin_report_v1.json",
        "da8883bc0c30c05f8d821371083b389dd34a9a443d5436808c3eacf39b0f4afa",
        10617,
    ),
    (
        "p6_stage_checkpoint_report_v1.json",
        "10b0802aa2d6c21f8503a2b9fb0a983734ffd480a614aba50b5e45c01f908d5b",
        3462,
    ),
    (
        "p6_native_origin_report_v1.json",
        "2d21630f8bc7b03c0d7c6286bcf2f612171c2f8410cf30a634650f478c27185c",
        20771,
    ),
    (
        "p6_dual_worker_isolation_report_v1.json",
        "3aabf7a71e98b52bd06e1c9ecffb08edccf936c5bca4544fed7809601cf40751",
        25781,
    ),
    (
        "worker_teardown_report_v1.json",
        "0868d34f8dabf5436bebf74bf474e3681decac289321bf9bae9c3a66dc9d0cbb",
        2248,
    ),
    (
        "scratch_cleanup_report_v1.json",
        "7b462544dd425388927a203e2a12299b64338eec25a6824077be877734fe0380",
        249,
    ),
    (
        "p5_p6_successor_runtime_qualification_summary_v1.json",
        "8b9044caf723fea8028b083d05cbe8d82359f5431ab93953b9585ab0a818303b",
        1584,
    ),
    (
        "failure_report_v1.json",
        "4bf24b4633a4843e64109e5c4cf437201ed7cbf192c1d36e241491a9d8cde3b4",
        192,
    ),
    ("human_report_v1.md", "6ad6589ac6c8a541ae7ff48267ad31ba9a91a82e5cc5c01c0545c3a26128802c", 467),
    (
        "bundle_manifest_v1.json",
        "4956183f4a3075c0448e2278b28052aab1f4d25759e43da51ebf749ee70bc290",
        2620,
    ),
)

NEXT_GATE: Final = (
    "merge_then_observe_kaggle_issue_fresh_authorization_and_repeat_p5_p6_successor_once"
)


class ReconciliationError(RuntimeError):
    """Typed safe failure for reconciliation operations."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class ErrorEnvelope(LocalABCContract):
    """Machine-readable safe CLI error."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ArtifactReceipt(LocalABCContract):
    """Identity of one repository artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class EvidenceMemberReceipt(LocalABCContract):
    """Expected member identity inside the preserved evidence archive."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class TechnicalEvidence(LocalABCContract):
    """Evidence-supported technical result without governance promotion."""

    saved_version_id: Literal[340872949]
    notebook_name: Literal["ag-p5-p6-successor-runtime-qual-v1"]
    notebook_sha256: Literal["113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8"]
    executed_runtime_script_sha256: Literal[
        "5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737"
    ]
    wrapper_code_sha256: Literal["f65b8dba855fd503b415ccffa78dd3039fe4fdcc4145b077edc6fc4cb16747dd"]
    evidence_zip_sha256: Literal["7f14ab45aeb4abd858c9905ca06553bd325f21035d5d9d7533424fbadfa47583"]
    evidence_zip_size_bytes: Literal[22587]
    terminal_log_sha256: Literal["a3c7649351732b699433e97fc8e7da3076f0715c343ef709761ae60b0b252854"]
    terminal_log_size_bytes: Literal[3552]
    technical_status: Literal["PASSED"]
    completed_probes: tuple[Literal["P3", "P4", "P5", "P6"], ...]
    model_requests: Literal[5]
    model_loads: Literal[3]
    worker_starts: Literal[3]
    hidden_retries: Literal[0]
    benchmark_trajectory_requests: Literal[0]
    network_requests: Literal[0]
    external_spend: Literal[0]
    measured_abc_execution_performed: Literal[False]
    p5_cold_cached_prefix_tokens: Literal[0]
    p5_warm_cached_prefix_tokens: Literal[736]
    p5_post_restart_cached_prefix_tokens: Literal[0]
    p5_cold_new_prefill_tokens: Literal[747]
    p5_warm_new_prefill_tokens: Literal[11]
    p5_post_restart_new_prefill_tokens: Literal[747]
    p5_full_process_restart_proven: Literal[True]
    p6_worker_1_prompt_delta: Literal[747]
    p6_worker_1_non_target_prompt_delta: Literal[0]
    p6_worker_2_prompt_delta: Literal[747]
    p6_worker_2_non_target_prompt_delta: Literal[0]
    p6_model_semantics_used_as_route_proof: Literal[False]
    teardown_passed: Literal[True]
    scratch_cleanup_passed: Literal[True]
    evidence_members: tuple[EvidenceMemberReceipt, ...]

    @model_validator(mode="after")
    def require_exact_probe_order(self) -> TechnicalEvidence:
        if self.completed_probes != ("P3", "P4", "P5", "P6"):
            raise ValueError("completed probe order drifted")
        expected = tuple(
            EvidenceMemberReceipt(path=path, sha256=sha256, size_bytes=size)
            for path, sha256, size in EXPECTED_EVIDENCE_MEMBERS
        )
        if self.evidence_members != expected:
            raise ValueError("evidence member authority drifted")
        return self


class GovernanceDisposition(LocalABCContract):
    """Explicit non-promotion of an execution with unestablished authority lineage."""

    authorization_lineage_status: Literal["UNESTABLISHED_AT_EXECUTION"]
    technical_result_preserved: Literal[True]
    governed_acceptance_status: Literal["INVALID_UNGOVERNED_EXECUTION"]
    current_line_p5_pass_accepted: Literal[False]
    current_line_p6_pass_accepted: Literal[False]
    measured_abc_eligible: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    evidence_preserved: Literal[True]
    saved_version_replay_authorized: Literal[False]
    fresh_authorization_required: Literal[True]
    successor_repeat_required: Literal[True]
    retroactive_authorization_permitted: Literal[False]
    next_gate: Literal[
        "merge_then_observe_kaggle_issue_fresh_authorization_and_repeat_p5_p6_successor_once"
    ]


class ReconciliationReview(LocalABCContract):
    """Deterministic decision review before committing the reconciliation receipt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-p5-p6-successor-unauthorized-execution-reconciliation-v1-review"
    ]
    status: Literal["APPROVED_FOR_RECONCILIATION_IMPLEMENTATION"]
    decision: Literal["PRESERVE_TECHNICAL_PASS_QUARANTINE_GOVERNED_ACCEPTANCE"]
    source_main_commit: Literal["a5a71181fd48965730d00e63f7bd456714fa4048"]
    technical_evidence: TechnicalEvidence
    governance: GovernanceDisposition
    authorization_issuer_record: ArtifactReceipt
    authorization_issuer_review: ArtifactReceipt
    runtime_implementation_record: ArtifactReceipt
    runtime_implementation_review: ArtifactReceipt
    runtime_request: ArtifactReceipt
    authorization_source: ArtifactReceipt
    runtime_source: ArtifactReceipt
    non_claims: tuple[str, ...] = Field(min_length=8)


class ReconciliationRecord(LocalABCContract):
    """Repository receipt preserving the technical run without accepting it as governed."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-p5-p6-successor-unauthorized-execution-reconciliation-v1-record"
    ]
    status: Literal["P5_P6_SUCCESSOR_UNAUTHORIZED_EXECUTION_RECONCILIATION_V1_VALID"]
    source_main_commit: Literal["a5a71181fd48965730d00e63f7bd456714fa4048"]
    technical_evidence: TechnicalEvidence
    governance: GovernanceDisposition
    review: ArtifactReceipt
    source: ArtifactReceipt
    tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    runtime_execution_authorized: Literal[False]
    measured_abc_execution_authorized: Literal[False]
    next_gate: Literal[
        "merge_then_observe_kaggle_issue_fresh_authorization_and_repeat_p5_p6_successor_once"
    ]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact(repo_root: Path, path: Path) -> ArtifactReceipt:
    target = repo_root / path
    if not target.is_file() or target.is_symlink():
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_ARTIFACT_UNSAFE",
            "a required reconciliation artifact is missing or unsafe",
            path.as_posix(),
        )
    payload = target.read_bytes()
    return ArtifactReceipt(
        path=path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _require_expected_repo_authorities(repo_root: Path) -> None:
    for path, expected_sha256 in EXPECTED_REPO_ARTIFACT_SHA256.items():
        receipt = _artifact(repo_root, path)
        if receipt.sha256 != expected_sha256:
            raise ReconciliationError(
                "P5_P6_RECONCILIATION_SOURCE_AUTHORITY_DRIFT",
                "a bound repository authority no longer matches the inspected main",
                path.as_posix(),
                (expected_sha256, receipt.sha256),
            )


def _run_git(repo_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_GIT_FAILED",
            "a required Git inspection could not be completed",
            details=tuple(arguments),
        ) from error
    if result.returncode != 0:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_GIT_FAILED",
            "a required Git inspection failed",
            details=tuple(arguments),
        )
    return result.stdout.strip()


def _require_source_main_ancestor(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                SOURCE_MAIN_COMMIT,
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_ANCESTRY_UNREADABLE",
            "reconciliation source ancestry could not be inspected",
        ) from error
    if result.returncode != 0:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_SOURCE_MAIN_MISSING",
            "the inspected authorization-issuer main is not an ancestor of HEAD",
        )


def _technical_evidence() -> TechnicalEvidence:
    members = tuple(
        EvidenceMemberReceipt(path=path, sha256=sha256, size_bytes=size)
        for path, sha256, size in EXPECTED_EVIDENCE_MEMBERS
    )
    return TechnicalEvidence(
        saved_version_id=SAVED_VERSION_ID,
        notebook_name=NOTEBOOK_NAME,
        notebook_sha256=NOTEBOOK_SHA256,
        executed_runtime_script_sha256=RUNTIME_SCRIPT_SHA256,
        wrapper_code_sha256=WRAPPER_CODE_SHA256,
        evidence_zip_sha256=EVIDENCE_ZIP_SHA256,
        evidence_zip_size_bytes=EVIDENCE_ZIP_SIZE_BYTES,
        terminal_log_sha256=TERMINAL_LOG_SHA256,
        terminal_log_size_bytes=TERMINAL_LOG_SIZE_BYTES,
        technical_status="PASSED",
        completed_probes=("P3", "P4", "P5", "P6"),
        model_requests=5,
        model_loads=3,
        worker_starts=3,
        hidden_retries=0,
        benchmark_trajectory_requests=0,
        network_requests=0,
        external_spend=0,
        measured_abc_execution_performed=False,
        p5_cold_cached_prefix_tokens=0,
        p5_warm_cached_prefix_tokens=736,
        p5_post_restart_cached_prefix_tokens=0,
        p5_cold_new_prefill_tokens=747,
        p5_warm_new_prefill_tokens=11,
        p5_post_restart_new_prefill_tokens=747,
        p5_full_process_restart_proven=True,
        p6_worker_1_prompt_delta=747,
        p6_worker_1_non_target_prompt_delta=0,
        p6_worker_2_prompt_delta=747,
        p6_worker_2_non_target_prompt_delta=0,
        p6_model_semantics_used_as_route_proof=False,
        teardown_passed=True,
        scratch_cleanup_passed=True,
        evidence_members=members,
    )


def _governance() -> GovernanceDisposition:
    return GovernanceDisposition(
        authorization_lineage_status="UNESTABLISHED_AT_EXECUTION",
        technical_result_preserved=True,
        governed_acceptance_status="INVALID_UNGOVERNED_EXECUTION",
        current_line_p5_pass_accepted=False,
        current_line_p6_pass_accepted=False,
        measured_abc_eligible=False,
        measured_abc_execution_authorized=False,
        evidence_preserved=True,
        saved_version_replay_authorized=False,
        fresh_authorization_required=True,
        successor_repeat_required=True,
        retroactive_authorization_permitted=False,
        next_gate=NEXT_GATE,
    )


def _review(repo_root: Path) -> ReconciliationReview:
    _require_expected_repo_authorities(repo_root)
    return ReconciliationReview(
        review_id=("auragateway-p5-p6-successor-unauthorized-execution-reconciliation-v1-review"),
        status="APPROVED_FOR_RECONCILIATION_IMPLEMENTATION",
        decision="PRESERVE_TECHNICAL_PASS_QUARANTINE_GOVERNED_ACCEPTANCE",
        source_main_commit=SOURCE_MAIN_COMMIT,
        technical_evidence=_technical_evidence(),
        governance=_governance(),
        authorization_issuer_record=_artifact(repo_root, AUTHORIZATION_RECORD_PATH),
        authorization_issuer_review=_artifact(repo_root, AUTHORIZATION_REVIEW_PATH),
        runtime_implementation_record=_artifact(repo_root, RUNTIME_RECORD_PATH),
        runtime_implementation_review=_artifact(repo_root, RUNTIME_REVIEW_PATH),
        runtime_request=_artifact(repo_root, RUNTIME_REQUEST_PATH),
        authorization_source=_artifact(repo_root, AUTHORIZATION_SOURCE_PATH),
        runtime_source=_artifact(repo_root, RUNTIME_SOURCE_PATH),
        non_claims=(
            "The preserved technical PASS is not a governed current-line P5 acceptance.",
            "The preserved technical PASS is not a governed current-line P6 acceptance.",
            "No retroactive authorization is created by this reconciliation.",
            "Saved version 340872949 is not authorized for replay.",
            "Measured A/B/C is not eligible from this execution.",
            "Measured A/B/C execution remains unauthorized.",
            "The reconciliation does not establish production readiness.",
            "A fresh authorization and one fresh successor execution remain required.",
        ),
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    except OSError as error:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_ATOMIC_WRITE_FAILED",
            "a static reconciliation artifact could not be written atomically",
            path.as_posix(),
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _record(repo_root: Path, review: ReconciliationReview) -> ReconciliationRecord:
    return ReconciliationRecord(
        record_id=("auragateway-p5-p6-successor-unauthorized-execution-reconciliation-v1-record"),
        status="P5_P6_SUCCESSOR_UNAUTHORIZED_EXECUTION_RECONCILIATION_V1_VALID",
        source_main_commit=SOURCE_MAIN_COMMIT,
        technical_evidence=_technical_evidence(),
        governance=_governance(),
        review=ArtifactReceipt(
            path=REVIEW_PATH.as_posix(),
            sha256=_sha256_bytes(review.canonical_json().encode("utf-8")),
            size_bytes=len(review.canonical_json().encode("utf-8")),
        ),
        source=_artifact(repo_root, SOURCE_PATH),
        tests=_artifact(repo_root, TEST_PATH),
        adr=_artifact(repo_root, ADR_PATH),
        report=_artifact(repo_root, REPORT_PATH),
        runbook=_artifact(repo_root, RUNBOOK_PATH),
        runtime_execution_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> ReconciliationRecord:
    """Generate deterministic static review and reconciliation record."""

    root = repo_root.resolve()
    _require_source_main_ancestor(root)
    review = _review(root)
    record = _record(root, review)
    _write_atomic(
        root / REVIEW_PATH,
        review.canonical_json().encode("utf-8"),
    )
    _write_atomic(
        root / RECORD_PATH,
        record.canonical_json().encode("utf-8"),
    )
    return record


def _load_exact(path: Path, model: type[LocalABCContract]) -> LocalABCContract:
    try:
        observed = path.read_text(encoding="utf-8")
        parsed = model.model_validate_json(observed)
    except (OSError, ValidationError) as error:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_STATIC_ARTIFACT_INVALID",
            "a static reconciliation artifact is missing or invalid",
            path.as_posix(),
        ) from error
    if observed != parsed.canonical_json():
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_STATIC_ARTIFACT_NOT_CANONICAL",
            "a static reconciliation artifact is not canonical JSON",
            path.as_posix(),
        )
    return parsed


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the committed static reconciliation without external evidence files."""

    root = repo_root.resolve()
    _require_source_main_ancestor(root)
    expected_review = _review(root)
    review_path = root / REVIEW_PATH
    record_path = root / RECORD_PATH
    observed_review = cast(
        ReconciliationReview,
        _load_exact(review_path, ReconciliationReview),
    )
    if observed_review != expected_review:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_REVIEW_DRIFT",
            "the committed reconciliation review does not match current authorities",
            REVIEW_PATH.as_posix(),
        )
    expected_record = _record(root, expected_review)
    observed_record = cast(
        ReconciliationRecord,
        _load_exact(record_path, ReconciliationRecord),
    )
    if observed_record != expected_record:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_RECORD_DRIFT",
            "the committed reconciliation record does not match current authorities",
            RECORD_PATH.as_posix(),
        )
    return {
        "status": observed_record.status,
        "saved_version_id": observed_record.technical_evidence.saved_version_id,
        "technical_status": observed_record.technical_evidence.technical_status,
        "governed_acceptance_status": (observed_record.governance.governed_acceptance_status),
        "authorization_lineage_status": (observed_record.governance.authorization_lineage_status),
        "current_line_p5_pass_accepted": False,
        "current_line_p6_pass_accepted": False,
        "measured_abc_eligible": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "evidence_preserved": True,
        "fresh_authorization_required": True,
        "successor_repeat_required": True,
        "next_gate": observed_record.next_gate,
    }


def _safe_member_name(name: str) -> str:
    if "\\" in name or "\x00" in name:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
            "evidence ZIP contains an unsafe member name",
            name,
        )
    pure = PurePosixPath(name)
    unsafe_parts = any(part in ("", ".", "..") for part in pure.parts)
    if pure.is_absolute() or name.startswith("/") or unsafe_parts:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
            "evidence ZIP contains an unsafe member name",
            name,
        )
    normalized = pure.as_posix()
    if normalized != name:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
            "evidence ZIP member name is not canonical",
            name,
        )
    return normalized


def _require_exact_external_file(path: Path, expected_sha256: str, expected_size: int) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EXTERNAL_EVIDENCE_UNSAFE",
            "external evidence file is missing or unsafe",
            str(path),
        )
    payload = path.read_bytes()
    if len(payload) != expected_size or _sha256_bytes(payload) != expected_sha256:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EXTERNAL_EVIDENCE_IDENTITY_MISMATCH",
            "external evidence identity does not match the preserved authority",
            str(path),
        )
    return payload


def _load_json_member(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    try:
        loaded = json.loads(archive.read(name))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_MEMBER_INVALID",
            "required evidence member is missing or invalid JSON",
            name,
        ) from error
    if not isinstance(loaded, dict):
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_MEMBER_INVALID",
            "required evidence member must be a JSON object",
            name,
        )
    return cast(dict[str, object], loaded)


def _require_number(value: object, expected: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_SEMANTICS_MISMATCH",
            "evidence metric has an unexpected type",
            label,
        )
    if float(value) != expected:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_SEMANTICS_MISMATCH",
            "evidence metric does not match the preserved technical observation",
            label,
        )


def _dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_SEMANTICS_MISMATCH",
            "evidence field must be an object",
            label,
        )
    return cast(dict[str, object], value)


def _validate_summary(summary: dict[str, object]) -> None:
    expected_scalars: dict[str, object] = {
        "status": "PASSED",
        "terminal_decision": "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_PASSED",
        "executed_runtime_script_sha256": RUNTIME_SCRIPT_SHA256,
        "failed_probe": None,
        "failure_code": None,
        "measured_abc_execution_performed": False,
        "network_access_permitted": False,
        "worker_teardown_status": "PASSED",
        "scratch_cleanup_status": "PASSED",
        "scratch_exists_after_cleanup": False,
    }
    for key, expected in expected_scalars.items():
        if summary.get(key) != expected:
            raise ReconciliationError(
                "P5_P6_RECONCILIATION_SUMMARY_MISMATCH",
                "successor summary does not match the preserved technical result",
                key,
            )
    if summary.get("completed_probes") != ["P3", "P4", "P5", "P6"]:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_SUMMARY_MISMATCH",
            "successor completed-probe order drifted",
            "completed_probes",
        )
    counters = _dict(summary.get("counters"), "summary.counters")
    expected_counters = {
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
        "hidden_retries": 0,
        "kaggle_sessions": 1,
        "model_loads": 3,
        "model_requests": 5,
        "network_requests": 0,
        "runtime_import_closure_probes": 1,
        "runtime_install_attempts": 1,
        "worker_starts": 3,
    }
    if counters != expected_counters:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_SUMMARY_MISMATCH",
            "successor counters do not match the preserved five-request execution",
            "counters",
        )


def _validate_p5(report: dict[str, object]) -> None:
    if report.get("status") != "PASSED":
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_P5_MISMATCH",
            "P5 technical evidence is not PASSED",
            "p5.status",
        )
    if report.get("full_process_restart_reset_proven") is not True:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_P5_MISMATCH",
            "P5 full-process restart is not established",
            "p5.full_process_restart_reset_proven",
        )
    if report.get("namespace_only_reset_used") is not False:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_P5_MISMATCH",
            "P5 unexpectedly used namespace-only reset",
            "p5.namespace_only_reset_used",
        )
    cold = _dict(
        _dict(report.get("cold_request"), "p5.cold_request").get("metric_delta"),
        "p5.cold",
    )
    warm = _dict(
        _dict(report.get("warm_request"), "p5.warm_request").get("metric_delta"),
        "p5.warm",
    )
    post = _dict(
        _dict(report.get("post_reset_request"), "p5.post_reset_request").get("metric_delta"),
        "p5.post_reset",
    )
    _require_number(cold.get("cached_prefix_tokens"), 0.0, "p5.cold.cached_prefix_tokens")
    _require_number(warm.get("cached_prefix_tokens"), 736.0, "p5.warm.cached_prefix_tokens")
    _require_number(post.get("cached_prefix_tokens"), 0.0, "p5.post.cached_prefix_tokens")
    _require_number(cold.get("newly_computed_prefill_tokens"), 747.0, "p5.cold.new_prefill")
    _require_number(warm.get("newly_computed_prefill_tokens"), 11.0, "p5.warm.new_prefill")
    _require_number(post.get("newly_computed_prefill_tokens"), 747.0, "p5.post.new_prefill")


def _validate_p6(report: dict[str, object]) -> None:
    if report.get("status") != "PASSED":
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_P6_MISMATCH",
            "P6 technical evidence is not PASSED",
            "p6.status",
        )
    if report.get("model_semantics_used_as_route_proof") is not False:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_P6_MISMATCH",
            "P6 used model semantics as route proof",
            "p6.model_semantics_used_as_route_proof",
        )
    isolation = _dict(report.get("route_and_metric_isolation"), "p6.route_and_metric_isolation")
    if isolation.get("request_counters_reconciled") is not True:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_P6_MISMATCH",
            "P6 request counters were not reconciled",
            "p6.request_counters_reconciled",
        )
    worker_1 = _dict(isolation.get("worker_1_request"), "p6.worker_1_request")
    worker_2 = _dict(isolation.get("worker_2_request"), "p6.worker_2_request")
    w1_target = _dict(worker_1.get("target_metric_delta"), "p6.worker_1.target")
    w1_other = _dict(worker_1.get("non_target_metric_delta"), "p6.worker_1.non_target")
    w2_target = _dict(worker_2.get("target_metric_delta"), "p6.worker_2.target")
    w2_other = _dict(worker_2.get("non_target_metric_delta"), "p6.worker_2.non_target")
    _require_number(w1_target.get("prompt_tokens"), 747.0, "p6.worker_1.target.prompt_tokens")
    _require_number(w1_other.get("prompt_tokens"), 0.0, "p6.worker_1.non_target.prompt_tokens")
    _require_number(w2_target.get("prompt_tokens"), 747.0, "p6.worker_2.target.prompt_tokens")
    _require_number(w2_other.get("prompt_tokens"), 0.0, "p6.worker_2.non_target.prompt_tokens")
    for label, request in (("worker_1", worker_1), ("worker_2", worker_2)):
        if request.get("route_acknowledgement_source") != "HARNESS_TRANSPORT_AND_METRICS":
            raise ReconciliationError(
                "P5_P6_RECONCILIATION_P6_MISMATCH",
                "P6 route acknowledgement source drifted",
                f"p6.{label}.route_acknowledgement_source",
            )
        if request.get("route_acknowledged") is not True:
            raise ReconciliationError(
                "P5_P6_RECONCILIATION_P6_MISMATCH",
                "P6 route was not acknowledged",
                f"p6.{label}.route_acknowledged",
            )


def _validate_teardown(report: dict[str, object]) -> None:
    expected = {
        "status": "PASSED",
        "all_ports_closed": True,
        "all_gpu_processes_absent": True,
        "all_capture_threads_finalized": True,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ReconciliationError(
                "P5_P6_RECONCILIATION_TEARDOWN_MISMATCH",
                "teardown evidence does not match the preserved technical result",
                key,
            )


def verify_evidence(evidence_zip: Path, terminal_log: Path) -> dict[str, object]:
    """Verify the preserved external evidence without accepting it as governed."""

    _require_exact_external_file(
        evidence_zip,
        EVIDENCE_ZIP_SHA256,
        EVIDENCE_ZIP_SIZE_BYTES,
    )
    log_payload = _require_exact_external_file(
        terminal_log,
        TERMINAL_LOG_SHA256,
        TERMINAL_LOG_SIZE_BYTES,
    )
    expected_members = {path: (sha256, size) for path, sha256, size in EXPECTED_EVIDENCE_MEMBERS}
    try:
        with zipfile.ZipFile(evidence_zip, "r") as archive:
            observed_names: list[str] = []
            for info in archive.infolist():
                if info.is_dir():
                    raise ReconciliationError(
                        "P5_P6_RECONCILIATION_EVIDENCE_ZIP_MEMBER_UNSAFE",
                        "evidence ZIP contains an unexpected directory member",
                        info.filename,
                    )
                observed_names.append(_safe_member_name(info.filename))
            if len(observed_names) != len(set(observed_names)):
                raise ReconciliationError(
                    "P5_P6_RECONCILIATION_EVIDENCE_ZIP_DUPLICATE_MEMBER",
                    "evidence ZIP contains duplicate normalized member names",
                )
            if set(observed_names) != set(expected_members):
                raise ReconciliationError(
                    "P5_P6_RECONCILIATION_EVIDENCE_MEMBER_SET_MISMATCH",
                    "evidence ZIP member set does not match the preserved manifest",
                )
            for name in observed_names:
                payload = archive.read(name)
                expected_sha256, expected_size = expected_members[name]
                if len(payload) != expected_size or _sha256_bytes(payload) != expected_sha256:
                    raise ReconciliationError(
                        "P5_P6_RECONCILIATION_EVIDENCE_MEMBER_IDENTITY_MISMATCH",
                        "an evidence ZIP member does not match the preserved manifest",
                        name,
                    )
            _validate_summary(
                _load_json_member(
                    archive,
                    "p5_p6_successor_runtime_qualification_summary_v1.json",
                )
            )
            _validate_p5(_load_json_member(archive, "p5_prefix_cache_reset_report_v1.json"))
            _validate_p6(_load_json_member(archive, "p6_dual_worker_isolation_report_v1.json"))
            _validate_teardown(_load_json_member(archive, "worker_teardown_report_v1.json"))
    except zipfile.BadZipFile as error:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_EVIDENCE_ZIP_INVALID",
            "preserved evidence ZIP is invalid",
            str(evidence_zip),
        ) from error
    terminal_text = log_payload.decode("utf-8")
    required_fragments = (
        '"status":"PASSED"',
        '"model_requests":5',
        '"measured_abc_execution_performed":false',
        f'"executed_runtime_script_sha256":"{RUNTIME_SCRIPT_SHA256}"',
        '"terminal_decision":"P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_V1_PASSED"',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in terminal_text)
    if missing:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_TERMINAL_LOG_MISMATCH",
            "terminal log is exact by hash but lacks required successor terminal markers",
            details=missing,
        )
    return {
        "status": "TECHNICAL_EVIDENCE_VERIFIED_NOT_GOVERNED_ACCEPTED",
        "saved_version_id": SAVED_VERSION_ID,
        "evidence_zip_sha256": EVIDENCE_ZIP_SHA256,
        "terminal_log_sha256": TERMINAL_LOG_SHA256,
        "technical_status": "PASSED",
        "governed_acceptance_status": "INVALID_UNGOVERNED_EXECUTION",
        "authorization_lineage_status": "UNESTABLISHED_AT_EXECUTION",
        "measured_abc_eligible": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError(
            "P5_P6_RECONCILIATION_ARGUMENT_INVALID",
            "reconciliation command arguments are invalid",
            details=(message,),
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p5-p6-unauthorized-reconciliation-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)

    verify = subparsers.add_parser("verify-evidence")
    verify.add_argument("--evidence-zip", type=Path, required=True)
    verify.add_argument("--terminal-log", type=Path, required=True)
    return parser


def _error_json(error: ReconciliationError) -> str:
    return ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    ).canonical_json()


def main(argv: list[str] | None = None) -> int:
    """Run one reconciliation command."""

    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        command = cast(str, arguments.command)
        if command == "generate":
            record = generate(cast(Path, arguments.repo_root))
            result: dict[str, object] = {
                "status": record.status,
                "saved_version_id": SAVED_VERSION_ID,
                "technical_status": "PASSED",
                "governed_acceptance_status": "INVALID_UNGOVERNED_EXECUTION",
                "runtime_execution_authorized": False,
                "measured_abc_execution_authorized": False,
                "next_gate": NEXT_GATE,
            }
        elif command == "validate-implementation":
            result = validate_implementation(cast(Path, arguments.repo_root))
        elif command == "verify-evidence":
            result = verify_evidence(
                cast(Path, arguments.evidence_zip),
                cast(Path, arguments.terminal_log),
            )
        else:
            raise ReconciliationError(
                "P5_P6_RECONCILIATION_COMMAND_INVALID",
                "P5/P6 reconciliation command is invalid",
            )
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
        return 0
    except ReconciliationError as error:
        print(_error_json(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
