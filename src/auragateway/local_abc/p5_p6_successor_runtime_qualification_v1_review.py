"""Review the successor P5/P6 runtime qualification boundary after P4 acceptance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CURRENT_MAIN_COMMIT: Final = "3f2b9851359bef2e4b9eaef20a16d5e95756d8f4"

OPTION_C_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_option_c_runtime_diagnostic_decision_v1.json"
)
OPTION_C_BLOB: Final = "a736e471a608a476b1e2fcd91ba06da9d7c77696"
V4_ACCEPTANCE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v4_review.json"
)
V4_ACCEPTANCE_REVIEW_BLOB: Final = "0ae0ff7ddc64ba98fda2150e64d06891f343a288"
V5_IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v5_record.json"
)
V5_IMPLEMENTATION_RECORD_BLOB: Final = "65bdcd73d59e527f0c7d5b60e4eeadbe9e4229dd"
V5_FAILURE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_cu129_p3_p6_runtime_diagnostic_failure_acceptance_v5_review.json"
)
V5_FAILURE_REVIEW_BLOB: Final = "7f43e62d5ddceef461e10d1345fa34ecfa8f341a"
P4_ACCEPTANCE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_output_contract_diagnostic_execution_acceptance_v1.json"
)
P4_ACCEPTANCE_RECORD_BLOB: Final = "c735a212fa1b3e56cbf18b3216451a18b193a956"
P4_ACCEPTANCE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_output_contract_diagnostic_execution_acceptance_v1_review.json"
)
P4_ACCEPTANCE_REVIEW_BLOB: Final = "13bf6d266ae026a7f7b3127d81fb5ea7929aaa7f"

REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_review.json"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1_review.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_successor_runtime_qualification_v1_review.py"
)
ADR_PATH: Final = Path("docs/adr/2026-08-07-local-abc-p5-p6-successor-runtime-qualification-v1.md")
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Successor_Runtime_Qualification_V1_Review.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_successor_runtime_qualification_v1_review.md"
)

CANDIDATE_PATHS: Final = tuple(
    sorted((REVIEW_PATH, SOURCE_PATH, TEST_PATH, ADR_PATH, REPORT_PATH, RUNBOOK_PATH))
)


class SuccessorQualificationReviewError(RuntimeError):
    """Fail-closed successor qualification review error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
            "details": self.details,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SuccessorQualificationReviewError(
            "P5_P6_SUCCESSOR_REVIEW_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return (
            json.dumps(
                self.model_dump(mode="json"),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        )


class Authority(StrictModel):
    authority_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    purpose: str = Field(min_length=20)


class SelectedP4Contract(StrictModel):
    case_id: Literal["A"] = "A"
    prompt_variant: Literal["V4"] = "V4"
    repetition_penalty: float = Field(
        default=1.1,
        ge=1.1,
        le=1.1,
        strict=True,
    )
    output_mode: Literal["UNCONSTRAINED"] = "UNCONSTRAINED"
    exact_object_required: Literal[True] = True
    reselection_permitted: Literal[False] = False
    json_schema_required: Literal[False] = False


class ExecutionBudget(StrictModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[5] = 5
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    hidden_retries_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class Probe(StrictModel):
    probe_id: Literal["P3_CANARY", "P4_CANARY", "P5", "P6"]
    purpose: str = Field(min_length=20)
    maximum_model_requests: int = Field(ge=0, le=5)
    claim_on_pass: str = Field(min_length=20)


class ReviewArtifact(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p5-p6-successor-runtime-qualification-v1-review"]
    status: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    decision: Literal["IMPLEMENT_SUCCESSOR_P5_P6_QUALIFICATION_BEFORE_MEASURED_ABC_AUTHORIZATION"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorities: tuple[Authority, ...]
    gate_correction_reason: str = Field(min_length=80)
    selected_p4_contract: SelectedP4Contract
    execution_budget: ExecutionBudget
    probes: tuple[Probe, Probe, Probe, Probe]
    p5_requirements: tuple[str, ...] = Field(min_length=7)
    p6_requirements: tuple[str, ...] = Field(min_length=9)
    evidence_requirements: tuple[str, ...] = Field(min_length=10)
    prohibited_actions: tuple[str, ...] = Field(min_length=8)
    non_claims: tuple[str, ...] = Field(min_length=9)
    runtime_execution_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    execution_manifest_freeze_authorized: Literal[False] = False
    next_gate: Literal["implement_and_merge_p5_p6_successor_runtime_qualification_v1"]

    @model_validator(mode="after")
    def validate_probe_plan(self) -> Self:
        if tuple(probe.probe_id for probe in self.probes) != (
            "P3_CANARY",
            "P4_CANARY",
            "P5",
            "P6",
        ):
            raise ValueError("successor probe order drifted")
        if sum(probe.maximum_model_requests for probe in self.probes) > 5:
            raise ValueError("successor model-request budget drifted")
        return self


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SuccessorQualificationReviewError(
            "P5_P6_SUCCESSOR_REVIEW_GIT_FAILED",
            "Git authority inspection failed",
            details=(result.stderr.strip(),),
        )
    return result.stdout.strip()


def _load_json(root: Path, relative: Path) -> dict[str, object]:
    path = root / relative
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SuccessorQualificationReviewError(
            "P5_P6_SUCCESSOR_REVIEW_JSON_INVALID",
            "Required authority JSON could not be loaded",
            path=relative.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise SuccessorQualificationReviewError(
            "P5_P6_SUCCESSOR_REVIEW_JSON_ROOT_INVALID",
            "Required authority JSON must contain one object",
            path=relative.as_posix(),
        )
    return cast(dict[str, object], value)


def _require(condition: bool, code: str, message: str, path: Path | None = None) -> None:
    if condition:
        return
    raise SuccessorQualificationReviewError(
        code,
        message,
        path=path.as_posix() if path is not None else None,
    )


def _validate_blob(root: Path, relative: Path, expected: str) -> None:
    observed = _run_git(root, "rev-parse", f"HEAD:{relative.as_posix()}")
    _require(
        observed == expected,
        "P5_P6_SUCCESSOR_REVIEW_AUTHORITY_BLOB_DRIFT",
        "A predecessor authority Git blob drifted",
        relative,
    )


def _validate_current_main(root: Path) -> None:
    branch = _run_git(root, "branch", "--show-current")
    _require(
        branch == "main" or branch.startswith(("feat/", "fix/", "review/")),
        "P5_P6_SUCCESSOR_REVIEW_BRANCH_INVALID",
        "Review validation requires main or a bounded review feature branch",
    )
    merge_base = _run_git(root, "merge-base", CURRENT_MAIN_COMMIT, "HEAD")
    _require(
        merge_base == CURRENT_MAIN_COMMIT,
        "P5_P6_SUCCESSOR_REVIEW_BASE_MISSING",
        "Current P4 acceptance main authority is not an ancestor of HEAD",
    )


def validate_authorities(root: Path) -> dict[str, object]:
    root = root.resolve()
    _validate_current_main(root)
    expected = (
        (OPTION_C_PATH, OPTION_C_BLOB),
        (V4_ACCEPTANCE_REVIEW_PATH, V4_ACCEPTANCE_REVIEW_BLOB),
        (V5_IMPLEMENTATION_RECORD_PATH, V5_IMPLEMENTATION_RECORD_BLOB),
        (V5_FAILURE_REVIEW_PATH, V5_FAILURE_REVIEW_BLOB),
        (P4_ACCEPTANCE_RECORD_PATH, P4_ACCEPTANCE_RECORD_BLOB),
        (P4_ACCEPTANCE_REVIEW_PATH, P4_ACCEPTANCE_REVIEW_BLOB),
    )
    for relative, blob in expected:
        _validate_blob(root, relative, blob)

    option_c = _load_json(root, OPTION_C_PATH)
    runtime = cast(dict[str, object], option_c["runtime_diagnostic"])
    probes = cast(list[dict[str, object]], runtime["probes"])
    by_id = {str(item["probe_id"]): item for item in probes}
    _require(
        runtime["measured_execution_permitted"] is False,
        "P5_P6_SUCCESSOR_REVIEW_OPTION_C_MEASURED_DRIFT",
        "Option C measured-execution boundary drifted",
        OPTION_C_PATH,
    )
    _require(
        by_id["P5"]["pass_decision"] == "CACHE_SMOKE_AND_RESET_PASSED",
        "P5_P6_SUCCESSOR_REVIEW_OPTION_C_P5_DRIFT",
        "Option C P5 decision drifted",
        OPTION_C_PATH,
    )
    _require(
        by_id["P6"]["pass_decision"] == "DUAL_WORKER_DIAGNOSTIC_PASSED",
        "P5_P6_SUCCESSOR_REVIEW_OPTION_C_P6_DRIFT",
        "Option C P6 decision drifted",
        OPTION_C_PATH,
    )

    v4 = _load_json(root, V4_ACCEPTANCE_REVIEW_PATH)
    _require(
        v4["p5_prefix_cache_reuse_established"] is True
        and v4["p5_full_process_reset_established"] is True
        and v4["p6_full_route_and_metric_isolation_established"] is False,
        "P5_P6_SUCCESSOR_REVIEW_V4_SEMANTIC_DRIFT",
        "V4 P5/P6 evidence semantics drifted",
        V4_ACCEPTANCE_REVIEW_PATH,
    )

    v5_record = _load_json(root, V5_IMPLEMENTATION_RECORD_PATH)
    budget = cast(dict[str, object], v5_record["execution_budget"])
    _require(
        v5_record["status"] == "IMPLEMENTED_NOT_EXECUTED"
        and budget["maximum_model_requests"] == 5
        and budget["benchmark_trajectory_requests_permitted"] == 0,
        "P5_P6_SUCCESSOR_REVIEW_V5_IMPLEMENTATION_DRIFT",
        "V5 diagnostic harness contract drifted",
        V5_IMPLEMENTATION_RECORD_PATH,
    )

    v5_failure = _load_json(root, V5_FAILURE_REVIEW_PATH)
    _require(
        v5_failure["failed_probe"] == "P4"
        and v5_failure["p5_prefix_cache_reuse_established"] is False
        and v5_failure["p6_route_and_metric_isolation_established"] is False,
        "P5_P6_SUCCESSOR_REVIEW_V5_FAILURE_DRIFT",
        "V5 terminal evidence no longer supports the successor gap",
        V5_FAILURE_REVIEW_PATH,
    )

    p4_record = _load_json(root, P4_ACCEPTANCE_RECORD_PATH)
    _require(
        p4_record["p4_output_contract_diagnostic_established"] is True
        and p4_record["selected_case_id"] == "A"
        and p4_record["measured_abc_execution_authorized"] is False,
        "P5_P6_SUCCESSOR_REVIEW_P4_ACCEPTANCE_DRIFT",
        "P4 acceptance contract drifted",
        P4_ACCEPTANCE_RECORD_PATH,
    )

    p4_review = _load_json(root, P4_ACCEPTANCE_REVIEW_PATH)
    selected = cast(dict[str, object], p4_review["selected_case"])
    _require(
        p4_review["selected_case_id"] == "A"
        and selected["prompt_variant"] == "V4"
        and selected["repetition_penalty"] == 1.1
        and selected["output_mode"] == "UNCONSTRAINED"
        and p4_review["measured_abc_execution_authorized"] is False,
        "P5_P6_SUCCESSOR_REVIEW_P4_SELECTION_DRIFT",
        "Selected P4 output contract drifted",
        P4_ACCEPTANCE_REVIEW_PATH,
    )

    return {
        "status": "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_AUTHORITIES_VALID",
        "source_main_commit": CURRENT_MAIN_COMMIT,
        "selected_case_id": "A",
        "p5_successor_qualification_established": False,
        "p6_successor_qualification_established": False,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
    }


def build_review() -> ReviewArtifact:
    authorities = (
        Authority(
            authority_id="option_c_runtime_diagnostic_decision_v1",
            path=OPTION_C_PATH.as_posix(),
            git_blob_sha=OPTION_C_BLOB,
            purpose=(
                "Requires P3-P6 runtime proof before successor qualification and measured A/B/C."
            ),
        ),
        Authority(
            authority_id="p3_p6_v4_failure_acceptance_review",
            path=V4_ACCEPTANCE_REVIEW_PATH.as_posix(),
            git_blob_sha=V4_ACCEPTANCE_REVIEW_BLOB,
            purpose=(
                "Proves P5 reuse and full-process reset while leaving complete "
                "P6 isolation unresolved."
            ),
        ),
        Authority(
            authority_id="p3_p6_v5_implementation_record",
            path=V5_IMPLEMENTATION_RECORD_PATH.as_posix(),
            git_blob_sha=V5_IMPLEMENTATION_RECORD_BLOB,
            purpose=(
                "Provides the hardened P6 checkpoint, route acknowledgement, "
                "counter, and teardown design."
            ),
        ),
        Authority(
            authority_id="p3_p6_v5_failure_acceptance_review",
            path=V5_FAILURE_REVIEW_PATH.as_posix(),
            git_blob_sha=V5_FAILURE_REVIEW_BLOB,
            purpose=(
                "Proves V5 stopped at P4 before P5 or P6 and therefore did not "
                "close the successor gap."
            ),
        ),
        Authority(
            authority_id="p4_v2_execution_acceptance_record",
            path=P4_ACCEPTANCE_RECORD_PATH.as_posix(),
            git_blob_sha=P4_ACCEPTANCE_RECORD_BLOB,
            purpose="Proves the governed P4 V2 pass and binds selected output-contract case A.",
        ),
        Authority(
            authority_id="p4_v2_execution_acceptance_review",
            path=P4_ACCEPTANCE_REVIEW_PATH.as_posix(),
            git_blob_sha=P4_ACCEPTANCE_REVIEW_BLOB,
            purpose=(
                "Binds V4 prompt, repetition penalty 1.1, unconstrained output, "
                "and measured-execution prohibition."
            ),
        ),
    )
    return ReviewArtifact(
        review_id="auragateway-p5-p6-successor-runtime-qualification-v1-review",
        status="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        decision=("IMPLEMENT_SUCCESSOR_P5_P6_QUALIFICATION_BEFORE_MEASURED_ABC_AUTHORIZATION"),
        source_main_commit=CURRENT_MAIN_COMMIT,
        authorities=authorities,
        gate_correction_reason=(
            "P4 V2 is formally accepted, but the accepted successor lineage still lacks current P5 "
            "prefix-cache/reset proof and complete P6 route/metric isolation. The earlier Option C "
            "decision makes those runtime proofs prerequisites to successor "
            "qualification and measured "
            "A/B/C. The historical 72-trajectory authorization is not reusable "
            "for the 342-trajectory line."
        ),
        selected_p4_contract=SelectedP4Contract(),
        execution_budget=ExecutionBudget(),
        probes=(
            Probe(
                probe_id="P3_CANARY",
                purpose=(
                    "Re-establish one current worker, explicit TRITON_ATTN "
                    "realization, and native-origin preconditions."
                ),
                maximum_model_requests=0,
                claim_on_pass=(
                    "Current successor session is ready to exercise the bound "
                    "output and cache contracts."
                ),
            ),
            Probe(
                probe_id="P4_CANARY",
                purpose=(
                    "Run one case-A exact-object canary without repeating the "
                    "A-F selection experiment."
                ),
                maximum_model_requests=1,
                claim_on_pass=(
                    "The accepted P4 case-A output contract is realized in the successor session."
                ),
            ),
            Probe(
                probe_id="P5",
                purpose=(
                    "Prove same-worker prefix reuse, attributable cache telemetry, "
                    "and a full-process reset baseline."
                ),
                maximum_model_requests=2,
                claim_on_pass=(
                    "Successor-line prefix-cache reuse and full-process reset are "
                    "established for this governed run."
                ),
            ),
            Probe(
                probe_id="P6",
                purpose=(
                    "Prove two-worker process, GPU, port, route, and metric "
                    "isolation with typed route acknowledgements."
                ),
                maximum_model_requests=2,
                claim_on_pass=(
                    "Successor-line dual-worker route and metric isolation are "
                    "established for this governed run."
                ),
            ),
        ),
        p5_requirements=(
            "same-worker cold and warm requests use one byte-identical eligible prefix",
            "cache reuse is proven by explicit request-attributable token telemetry, "
            "not latency alone",
            "warm request shows positive cached-prefix evidence",
            "warm prefill work is lower than the cold request under the governed metric mapping",
            "reset performs full worker-process termination and restart rather than "
            "namespace-only mutation",
            "post-reset worker identity includes a fresh process identity and a "
            "revalidated backend",
            "ports, process tree, and cache baseline are proven clean before "
            "successor continuation",
        ),
        p6_requirements=(
            "exactly two workers use GPU 0/port 8001 and GPU 1/port 8002",
            "both workers prove explicit TRITON_ATTN realization",
            "worker process trees are disjoint and carry stable PID/start identities",
            "GPU UUID and PCI bus identities bind each worker to its assigned GPU",
            "route proof uses harness routing acknowledgement rather than "
            "model-generated route semantics",
            "each routed request records attempted and transport-completed counters",
            "worker 1 request changes only worker 1 request-attributable metric evidence",
            "worker 2 request changes only worker 2 request-attributable metric evidence",
            "partial stage checkpoints survive failure and teardown proves ports, "
            "processes, and GPU allocations released",
        ),
        evidence_requirements=(
            "executed runtime script and notebook-wrapper SHA-256 identities",
            "runtime installation and import-closure reports",
            "native-origin closure for required CUDA libraries",
            "P3 worker-startup and backend-realization report",
            "P4 case-A canary report",
            "P5 prefix-cache and full-process reset report",
            "P6 stage-checkpoint and dual-worker isolation reports",
            "per-worker request attempted and completion counters",
            "structured teardown and scratch-cleanup reports",
            "terminal summary, bounded failure report, manifest, human report, and evidence ZIP",
        ),
        prohibited_actions=(
            "no A-F output-contract reselection",
            "no benchmark trajectory execution",
            "no hidden retries or replacement workers",
            "no network fallback or external provider calls",
            "no raw prompt or raw model-output retention",
            "no customer data, credentials, or private client artifacts",
            "no live runtime authorization in the implementation PR",
            "no measured A/B/C authorization in this review or implementation tranche",
        ),
        non_claims=(
            "P5 successor-line qualification is not yet established.",
            "P6 successor-line qualification is not yet established.",
            "The current 342-trajectory benchmark is not authorized.",
            "Pressure and eviction behavior are not established by this review.",
            "Fault-recovery behavior is not established by this review.",
            "Variance adequacy and repetition count are not frozen.",
            "The execution manifest is not frozen.",
            "Measured A/B/C effects are not established.",
            "Deployment and production readiness are not established.",
        ),
        next_gate="implement_and_merge_p5_p6_successor_runtime_qualification_v1",
    )


def generate(root: Path) -> dict[str, object]:
    validate_authorities(root)
    review = build_review()
    path = root.resolve() / REVIEW_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.canonical_json(), encoding="utf-8", newline="\n")
    return {
        "status": "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_REVIEW_GENERATED",
        "review_path": REVIEW_PATH.as_posix(),
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": review.next_gate,
    }


def validate_package(root: Path) -> dict[str, object]:
    authority_result = validate_authorities(root)
    path = root.resolve() / REVIEW_PATH
    try:
        stored = ReviewArtifact.model_validate(_load_json(root.resolve(), REVIEW_PATH))
    except ValidationError as error:
        raise SuccessorQualificationReviewError(
            "P5_P6_SUCCESSOR_REVIEW_SCHEMA_INVALID",
            "Stored successor review failed typed validation",
            path=REVIEW_PATH.as_posix(),
        ) from error
    expected = build_review()
    _require(
        stored == expected and path.read_text(encoding="utf-8") == expected.canonical_json(),
        "P5_P6_SUCCESSOR_REVIEW_DRIFT",
        "Stored successor review drifted from deterministic generation",
        REVIEW_PATH,
    )
    return {
        **authority_result,
        "status": "P5_P6_SUCCESSOR_RUNTIME_QUALIFICATION_REVIEW_VALID",
        "decision": stored.decision,
        "maximum_model_requests": stored.execution_budget.maximum_model_requests,
        "benchmark_trajectory_requests_permitted": 0,
        "runtime_execution_authorized": False,
        "measured_abc_execution_authorized": False,
        "next_gate": stored.next_gate,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="p5-p6-successor-runtime-qualification-v1-review")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate-authorities", "generate", "validate-package"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        root = cast(Path, args.repo_root)
        if args.command == "validate-authorities":
            result = validate_authorities(root)
        elif args.command == "generate":
            result = generate(root)
        else:
            result = validate_package(root)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except SuccessorQualificationReviewError as error:
        print(
            json.dumps(error.envelope(), sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
