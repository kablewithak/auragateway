"""Freeze exact-runtime P5/P6 execution-authorization design V1.

This module is design-only control-plane infrastructure. It binds the future
single-use authorization issuer to the exact merged P5/P6 implementation and
freezes issuance, freshness, budget, lifecycle, terminalization, and non-claim
contracts. It does not issue live authority or execute model/runtime work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "9cc06c02c372fa2e7637c432759e7a1d4db56e9e"

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_requalification_design_v1.json"
)
DESIGN_RECORD_SHA256: Final = "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"

IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_record.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
)

IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
)

IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v1.py"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "e41c0c327eab743c01dad961d07204a041e64e0579936145b79a1c23a675d126"
)

IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v1.py.tmpl"
)
IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "bc512e45e7ac646045dda3f598ca2aa961a0c69c86b73117d66bb457710d0dfa"
)

IMPLEMENTATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v1.py"
)
IMPLEMENTATION_TEST_SHA256: Final = (
    "9d6151e387cd7b972696ffe982016831271288209a8a18cd6db1335343c137eb"
)

IMPLEMENTATION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_exact_runtime_requalification_v1.ipynb"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"
)

V5_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_record.json"
)
V5_ACCEPTANCE_RECORD_SHA256: Final = (
    "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
)

RUNTIME_SCRIPT_SHA256: Final = "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
WRAPPER_CODE_SHA256: Final = "55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_execution_authorization_design_v1.json"
)

AUTHORIZATION_FILENAME: Final = "execution_authorization_v1.json"
AUTHORIZATION_SCOPE: Final = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"
CONFIRMATION_PHRASE: Final = (
    "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
    "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION"
)
NEXT_GATE: Final = "implement_exact_runtime_p5_p6_execution_authorization_v1_issuer"


class AuthorizationDesignError(RuntimeError):
    """Fail-closed authorization-design error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    """Strict immutable persisted-contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TerminalDisposition(StrEnum):
    """Terminal authorization states visible to governance."""

    CONSUMED = "CONSUMED"
    EXPIRED_UNUSED = "EXPIRED_UNUSED"
    CANCELLED_UNUSED = "CANCELLED_UNUSED"
    ABANDONED_BEFORE_EXECUTION = "ABANDONED_BEFORE_EXECUTION"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class ExecutionOutcome(StrEnum):
    """Known execution outcomes after an attempt begins."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    INTERRUPTED = "INTERRUPTED"
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class ArtifactAuthority(FrozenModel):
    """Exact current repository authority bound by the design."""

    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    current_authority: Literal[True] = True


class ImplementationBinding(FrozenModel):
    """Exact merged implementation identity required by future authority."""

    implementation_merge_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    design_record_sha256: Literal[
        "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
    ]
    implementation_record_sha256: Literal[
        "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
    ]
    implementation_review_sha256: Literal[
        "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
    ]
    implementation_source_sha256: Literal[
        "e41c0c327eab743c01dad961d07204a041e64e0579936145b79a1c23a675d126"
    ]
    implementation_template_sha256: Literal[
        "bc512e45e7ac646045dda3f598ca2aa961a0c69c86b73117d66bb457710d0dfa"
    ]
    implementation_test_sha256: Literal[
        "9d6151e387cd7b972696ffe982016831271288209a8a18cd6db1335343c137eb"
    ]
    notebook_sha256: Literal["cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"]
    runtime_script_sha256: Literal[
        "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
    ]
    wrapper_code_sha256: Literal["55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c"]
    v5_acceptance_record_sha256: Literal[
        "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
    ]


class ExecutionBudget(FrozenModel):
    """Non-expandable ceiling for one governed execution."""

    maximum_kaggle_sessions: Literal[1] = 1
    maximum_saved_versions: Literal[1] = 1
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_workers: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class FreshnessContract(FrozenModel):
    """Freshness requirements for issuance."""

    maximum_platform_observation_age_minutes: Literal[15] = 15
    maximum_operator_confirmation_age_minutes: Literal[15] = 15
    maximum_authorization_window_minutes: Literal[240] = 240
    default_authorization_window_minutes: Literal[180] = 180
    timezone_aware_timestamps_required: Literal[True] = True


class PlatformContract(FrozenModel):
    """Fresh platform facts required before issue."""

    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    platform_observation_required: Literal[True] = True


class AuthorizationPayloadContract(FrozenModel):
    """Fields the future live authorization must bind."""

    authorization_filename: Literal["execution_authorization_v1.json"]
    scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1"]
    decision: Literal["AUTHORIZED"]
    lifecycle: Literal["ISSUED"]
    exact_confirmation_phrase: Literal[
        "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
        "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION"
    ]
    implementation_merge_commit_binding_required: Literal[True] = True
    design_record_sha256_binding_required: Literal[True] = True
    implementation_record_sha256_binding_required: Literal[True] = True
    implementation_review_sha256_binding_required: Literal[True] = True
    notebook_sha256_binding_required: Literal[True] = True
    runtime_script_sha256_binding_required: Literal[True] = True
    wrapper_code_sha256_binding_required: Literal[True] = True
    v5_acceptance_sha256_binding_required: Literal[True] = True
    issuer_merge_commit_binding_required: Literal[True] = True
    live_time_window_required: Literal[True] = True
    single_use_required: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False
    every_execution_attempt_terminalizes_authority: Literal[True] = True
    authorization_reusable: Literal[False] = False


class TerminalizationContract(FrozenModel):
    """Non-overwriting terminalization contract."""

    terminal_dispositions: tuple[TerminalDisposition, ...]
    known_execution_outcomes: tuple[ExecutionOutcome, ...]
    one_terminal_receipt_per_authorization: Literal[True] = True
    terminal_receipt_non_overwriting: Literal[True] = True
    consumed_requires_execution_attempt: Literal[True] = True
    expired_unused_requires_no_execution_attempt: Literal[True] = True
    cancelled_unused_requires_no_execution_attempt: Literal[True] = True
    abandoned_before_execution_requires_no_execution_attempt: Literal[True] = True
    outcome_unknown_reserved_for_uncertain_attempt_outcome: Literal[True] = True
    terminal_authority_reusable: Literal[False] = False

    @model_validator(mode="after")
    def require_complete_terminal_vocabulary(self) -> Self:
        expected_dispositions = tuple(TerminalDisposition)
        expected_outcomes = tuple(ExecutionOutcome)
        if self.terminal_dispositions != expected_dispositions:
            raise ValueError("terminal disposition vocabulary drifted")
        if self.known_execution_outcomes != expected_outcomes:
            raise ValueError("execution outcome vocabulary drifted")
        return self


class IssuancePreconditions(FrozenModel):
    """Preconditions required immediately before live authority issuance."""

    synchronized_main_required: Literal[True] = True
    clean_repository_required: Literal[True] = True
    merged_issuer_required: Literal[True] = True
    exact_issuer_merge_commit_confirmation_required: Literal[True] = True
    implementation_validation_required: Literal[True] = True
    implementation_identity_revalidation_required: Literal[True] = True
    semantic_boundary_revalidation_required: Literal[True] = True
    fresh_platform_observation_required: Literal[True] = True
    fresh_operator_confirmation_required: Literal[True] = True
    no_existing_live_authorization_required: Literal[True] = True
    no_conflicting_terminal_receipt_required: Literal[True] = True


class SafetyContract(FrozenModel):
    """Claims that remain false throughout the design tranche."""

    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    runtime_execution_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    worker_starts_performed: Literal[0] = 0
    model_loads_performed: Literal[0] = 0
    external_spend: Literal[0] = 0


class AuthorizationDesignRecord(FrozenModel):
    """Frozen design for the future single-use issuer."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-exact-runtime-p5-p6-execution-authorization-design-v1"]
    design_status: Literal["DESIGN_FROZEN_NOT_IMPLEMENTED"]
    base_main_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    authorities: tuple[ArtifactAuthority, ...] = Field(min_length=8, max_length=8)
    implementation: ImplementationBinding
    budget: ExecutionBudget
    freshness: FreshnessContract
    platform: PlatformContract
    authorization_payload: AuthorizationPayloadContract
    terminalization: TerminalizationContract
    issuance_preconditions: IssuancePreconditions
    safety: SafetyContract
    next_gate: Literal["implement_exact_runtime_p5_p6_execution_authorization_v1_issuer"]
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_authority_roles(self) -> Self:
        roles = tuple(item.role for item in self.authorities)
        expected = (
            "frozen_p5_p6_design",
            "merged_implementation_record",
            "merged_implementation_review",
            "merged_implementation_source",
            "merged_implementation_template",
            "merged_implementation_tests",
            "merged_implementation_notebook",
            "accepted_v5_capability_record",
        )
        if roles != expected:
            raise ValueError("authorization-design authority order drifted")
        return self


EXPECTED_AUTHORITIES: Final = (
    (
        "frozen_p5_p6_design",
        DESIGN_RECORD_PATH,
        DESIGN_RECORD_SHA256,
        13153,
    ),
    (
        "merged_implementation_record",
        IMPLEMENTATION_RECORD_PATH,
        IMPLEMENTATION_RECORD_SHA256,
        5269,
    ),
    (
        "merged_implementation_review",
        IMPLEMENTATION_REVIEW_PATH,
        IMPLEMENTATION_REVIEW_SHA256,
        8030,
    ),
    (
        "merged_implementation_source",
        IMPLEMENTATION_SOURCE_PATH,
        IMPLEMENTATION_SOURCE_SHA256,
        41675,
    ),
    (
        "merged_implementation_template",
        IMPLEMENTATION_TEMPLATE_PATH,
        IMPLEMENTATION_TEMPLATE_SHA256,
        150715,
    ),
    (
        "merged_implementation_tests",
        IMPLEMENTATION_TEST_PATH,
        IMPLEMENTATION_TEST_SHA256,
        16205,
    ),
    (
        "merged_implementation_notebook",
        IMPLEMENTATION_NOTEBOOK_PATH,
        IMPLEMENTATION_NOTEBOOK_SHA256,
        250380,
    ),
    (
        "accepted_v5_capability_record",
        V5_ACCEPTANCE_RECORD_PATH,
        V5_ACCEPTANCE_RECORD_SHA256,
        2819,
    ),
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _authority(
    repo_root: Path,
    role: str,
    path: Path,
    expected_sha256: str,
    expected_size: int,
) -> ArtifactAuthority:
    target = repo_root / path
    if not target.is_file() or target.is_symlink():
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_AUTHORITY_MISSING",
            "required authorization-design authority is missing or unsafe",
            path.as_posix(),
        )
    observed_sha256 = _sha256_file(target)
    observed_size = target.stat().st_size
    if observed_sha256 != expected_sha256 or observed_size != expected_size:
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_AUTHORITY_DRIFT",
            "required authorization-design authority identity drifted",
            path.as_posix(),
        )
    return ArtifactAuthority(
        role=role,
        path=path.as_posix(),
        sha256=observed_sha256,
        size_bytes=observed_size,
    )


def _authorities(repo_root: Path) -> tuple[ArtifactAuthority, ...]:
    return tuple(
        _authority(repo_root, role, path, sha256, size)
        for role, path, sha256, size in EXPECTED_AUTHORITIES
    )


def _read_json_object(repo_root: Path, path: Path) -> dict[str, object]:
    try:
        parsed = json.loads((repo_root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_JSON_INVALID",
            "required authorization-design authority is invalid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(parsed, dict):
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_JSON_INVALID",
            "required authorization-design authority is not a JSON object",
            path.as_posix(),
        )
    return cast(dict[str, object], parsed)


def _validate_implementation_semantics(repo_root: Path) -> None:
    record = _read_json_object(repo_root, IMPLEMENTATION_RECORD_PATH)
    expected = {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "next_gate": (
            "DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION_AUTHORIZATION_ISSUER"
        ),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise AuthorizationDesignError(
                "P5_P6_AUTHORIZATION_DESIGN_IMPLEMENTATION_SEMANTIC_DRIFT",
                f"merged implementation field drifted: {key}",
                IMPLEMENTATION_RECORD_PATH.as_posix(),
            )
    safety = record.get("safety")
    if not isinstance(safety, dict):
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_IMPLEMENTATION_SEMANTIC_DRIFT",
            "merged implementation safety contract is missing",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    required_false = (
        "runtime_execution_authorized",
        "pilot_execution_authorized",
        "final_measured_abc_execution_authorized",
    )
    for key in required_false:
        if safety.get(key) is not False:
            raise AuthorizationDesignError(
                "P5_P6_AUTHORIZATION_DESIGN_IMPLEMENTATION_SEMANTIC_DRIFT",
                f"merged implementation safety field drifted: {key}",
                IMPLEMENTATION_RECORD_PATH.as_posix(),
            )


def _require_base_commit(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        return
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_GIT_INSPECTION_FAILED",
            "unable to inspect repository HEAD",
        )
    if completed.stdout.strip() != BASE_MAIN_COMMIT:
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_BASE_DRIFT",
            "authorization design is not being validated against its base main",
        )


def build_record(repo_root: Path) -> AuthorizationDesignRecord:
    """Build the deterministic design record after validating current authority."""

    _require_base_commit(repo_root)
    _validate_implementation_semantics(repo_root)
    return AuthorizationDesignRecord(
        record_id="auragateway-exact-runtime-p5-p6-execution-authorization-design-v1",
        design_status="DESIGN_FROZEN_NOT_IMPLEMENTED",
        base_main_commit=BASE_MAIN_COMMIT,
        authorities=_authorities(repo_root),
        implementation=ImplementationBinding(
            implementation_merge_commit=BASE_MAIN_COMMIT,
            design_record_sha256=DESIGN_RECORD_SHA256,
            implementation_record_sha256=IMPLEMENTATION_RECORD_SHA256,
            implementation_review_sha256=IMPLEMENTATION_REVIEW_SHA256,
            implementation_source_sha256=IMPLEMENTATION_SOURCE_SHA256,
            implementation_template_sha256=IMPLEMENTATION_TEMPLATE_SHA256,
            implementation_test_sha256=IMPLEMENTATION_TEST_SHA256,
            notebook_sha256=IMPLEMENTATION_NOTEBOOK_SHA256,
            runtime_script_sha256=RUNTIME_SCRIPT_SHA256,
            wrapper_code_sha256=WRAPPER_CODE_SHA256,
            v5_acceptance_record_sha256=V5_ACCEPTANCE_RECORD_SHA256,
        ),
        budget=ExecutionBudget(),
        freshness=FreshnessContract(),
        platform=PlatformContract(),
        authorization_payload=AuthorizationPayloadContract(
            authorization_filename=AUTHORIZATION_FILENAME,
            scope=AUTHORIZATION_SCOPE,
            decision="AUTHORIZED",
            lifecycle="ISSUED",
            exact_confirmation_phrase=CONFIRMATION_PHRASE,
        ),
        terminalization=TerminalizationContract(
            terminal_dispositions=tuple(TerminalDisposition),
            known_execution_outcomes=tuple(ExecutionOutcome),
        ),
        issuance_preconditions=IssuancePreconditions(),
        safety=SafetyContract(),
        next_gate=NEXT_GATE,
        non_claims=(
            "No live P5/P6 execution authorization is issued by this design.",
            "No model or worker execution is performed by this design.",
            "No current exact-runtime P5 behavior is qualified by this design.",
            "No current exact-runtime P6 behavior is qualified by this design.",
            "No variance-pilot execution is authorized by this design.",
            "No final measured A/B/C execution is authorized by this design.",
            "Historical consumed authorizations remain non-reusable.",
            "The future issuer must be separately implemented, validated, and merged.",
        ),
    )


def _canonical_json(record: AuthorizationDesignRecord) -> bytes:
    return (
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def generate(repo_root: Path) -> dict[str, object]:
    """Generate the deterministic design record."""

    record = build_record(repo_root)
    target = repo_root / RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical_json(record)
    target.write_bytes(payload)
    return {
        "status": record.design_status,
        "record_path": RECORD_PATH.as_posix(),
        "record_sha256": hashlib.sha256(payload).hexdigest(),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "next_gate": record.next_gate,
    }


def validate(repo_root: Path) -> dict[str, object]:
    """Validate exact deterministic record bytes and design safety."""

    record = build_record(repo_root)
    expected = _canonical_json(record)
    target = repo_root / RECORD_PATH
    if not target.is_file() or target.is_symlink():
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_RECORD_MISSING",
            "authorization-design record is missing or unsafe",
            RECORD_PATH.as_posix(),
        )
    observed = target.read_bytes()
    if observed != expected:
        raise AuthorizationDesignError(
            "P5_P6_AUTHORIZATION_DESIGN_RECORD_NONDETERMINISTIC",
            "authorization-design record bytes differ from deterministic output",
            RECORD_PATH.as_posix(),
        )
    return {
        "status": "VALID",
        "record_sha256": hashlib.sha256(observed).hexdigest(),
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": record.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-p5-p6-exact-runtime-authorization-design-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one design-only command."""

    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        command = cast(str, arguments.command)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if command == "generate":
            result = generate(repo_root)
        elif command == "validate":
            result = validate(repo_root)
        else:
            raise AuthorizationDesignError(
                "P5_P6_AUTHORIZATION_DESIGN_COMMAND_INVALID",
                "authorization-design command is invalid",
            )
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except AuthorizationDesignError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
