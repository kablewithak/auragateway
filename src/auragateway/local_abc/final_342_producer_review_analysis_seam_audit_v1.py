"""Validate the final-342 producer -> review -> analysis seam audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from enum import StrEnum
from pathlib import Path
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import final_342_measured_review_design_v1 as review_design

AUDIT_ID = "auragateway-final-342-producer-review-analysis-seam-audit-v1"
EXPECTED_BASE_MAIN = "6320f1e636897c8cf90bcd3094eaae93b5cd5530"
RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_producer_review_analysis_seam_audit_v1.json"
)
LEDGER_PATH = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
EPISODES_PATH = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
PRODUCER_PATH = Path("src/auragateway/local_abc/final_342_execution_producer_v1.py")
REVIEW_SOURCE_PATH = Path("src/auragateway/local_abc/final_342_measured_review_design_v1.py")
REVIEW_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_measured_review_design_v1.json"
)
ANALYSIS_SOURCE_PATH = Path("src/auragateway/local_abc/final_342_analysis_contracts_v1.py")
ANALYSIS_RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_analysis_contracts_v1.json")
QUALITY_PATH = Path("src/auragateway/contracts/quality.py")
BLINDED_QUALITY_PATH = Path("src/auragateway/contracts/blinded_quality.py")
FEEDBACK_PATH = Path("src/auragateway/contracts/feedback.py")

EXPECTED_SOURCE_BLOBS = {
    PRODUCER_PATH.as_posix(): "9bedae7c7815e80d7c03ccc37b1e5261310056cf",
    REVIEW_SOURCE_PATH.as_posix(): "673091128975b2fc33ba175649c8e82b2670a522",
    REVIEW_RECORD_PATH.as_posix(): "e667cf734e6fdeec1acf4a5b254beebb78754fb7",
    ANALYSIS_SOURCE_PATH.as_posix(): "e5ff63b8a1f148dee42bbf1e39504b26657a6d75",
    ANALYSIS_RECORD_PATH.as_posix(): "0e7f654a5e8562f93ada988bba51f4e3ed5b5b1f",
    LEDGER_PATH.as_posix(): "553b23e24629bdca81d9fb9fdcbd90cc2081caf0",
    EPISODES_PATH.as_posix(): "b8e6a9c0a0097b0755acf9b47ac332792ffaaeac",
    QUALITY_PATH.as_posix(): "f25d94de7ad0f5ed2bc4c961a6aaa16e32dd9a09",
    BLINDED_QUALITY_PATH.as_posix(): "14a3cdf2463ed980913e7c3c8a37ad037ea84a4d",
    FEEDBACK_PATH.as_posix(): "4375eff8e45ed2cc7bf6ff788200b67e39a07ae1",
}

FUNCTIONAL_POPULATION = 162
SECONDARY_TARGET = 41
SECONDARY_SEED = 20260712


class AuditError(RuntimeError):
    """Fail-closed, metadata-safe seam-audit failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuditError("FINAL_342_SEAM_AUDIT_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SeamStatus(StrEnum):
    EXISTING_TRANSIENT_RESPONSE_HOOK_SUFFICIENT = "EXISTING_TRANSIENT_RESPONSE_HOOK_SUFFICIENT"
    THIN_SUCCESSOR_REQUIRED = "THIN_SUCCESSOR_REQUIRED"
    SUCCESSOR_REQUIRED = "SUCCESSOR_REQUIRED"
    DEFERRED_UNTIL_INPUT_SUCCESSORS_EXIST = "DEFERRED_UNTIL_INPUT_SUCCESSORS_EXIST"


class SourceBinding(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class ProducerSeam(FrozenModel):
    classification: Literal["EXISTING_TRANSIENT_RESPONSE_HOOK_SUFFICIENT"]
    execute_transport_attempt_returns_transient_response_object: Literal[True]
    response_json_validity_flag_available: Literal[True]
    transport_outcome_persisted_before_response_object_returned: Literal[True]
    response_object_persisted_in_public_producer_state: Literal[False]
    raw_output_persisted_in_public_bundle: Literal[False]
    public_attempt_action_ledger_available: Literal[True]
    public_turn_measurements_available: Literal[True]
    public_request_reconciliation_available: Literal[True]
    public_failure_report_available: Literal[True]
    public_trajectory_terminal_ledger_available: Literal[True]
    producer_modification_required: Literal[False]
    producer_modification_authorized: Literal[False]


class SecondaryScheduleSeam(FrozenModel):
    status: Literal["THIN_SUCCESSOR_REQUIRED"]
    population: Literal[162]
    target: Literal[41]
    stratum_count: Literal[12]
    seed: Literal[20260712]
    allocation_method: Literal["hamilton_largest_remainder"]
    within_stratum_rank_domain: Literal["auragateway-final-342-review-secondary-v1|{seed}|{run_id}"]
    derivable_from_frozen_inputs_without_execution_results: Literal[True]
    materialized: Literal[False]
    must_be_hash_bound_before_manifest_freeze: Literal[True]


class ProtectedExporterSeam(FrozenModel):
    status: Literal["THIN_SUCCESSOR_REQUIRED"]
    producer_redesign_required: Literal[False]
    consume_transient_response_object: Literal[True]
    append_only_protected_turn_capture_required: Literal[True]
    reviewer_payload_must_remain_blinded: Literal[True]
    public_receipt_digest_only: Literal[True]
    post_result_replacement_permitted: Literal[False]


class ReviewSeams(FrozenModel):
    protected_capture_boundary: Literal["successful_response_before_public_only_reduction"]
    protected_capture_hook_source: Literal[
        "execute_transport_attempt.return.TransportExecutionResult"
    ]
    exact_secondary_schedule: SecondaryScheduleSeam
    measured_protected_review_exporter: ProtectedExporterSeam


class TaskSuccessSeam(FrozenModel):
    status: Literal["SUCCESSOR_REQUIRED"]
    historical_synthetic_direct_reuse_permitted: Literal[False]
    runtime_completion_alone_sufficient: Literal[False]
    structured_validity_alone_sufficient: Literal[False]


class UnsafeBehaviorSeam(FrozenModel):
    status: Literal["SUCCESSOR_REQUIRED"]
    must_cover_route_retry_escalation_refusal_regression: Literal[True]
    post_hoc_human_override_permitted: Literal[False]


class QualitySeams(FrozenModel):
    measured_task_success_reducer: TaskSuccessSeam
    unsafe_behavior_regression_reducer: UnsafeBehaviorSeam


class FeedbackSeam(FrozenModel):
    status: Literal["SUCCESSOR_REQUIRED"]
    historical_synthetic_direct_reuse_permitted: Literal[False]
    required_dimensions: tuple[
        Literal["validity"],
        Literal["novelty"],
        Literal["retention"],
        Literal["later_action_change"],
        Literal["task_sufficiency"],
    ]
    universal_efc_score_permitted: Literal[False]


class AnalysisEngineSeam(FrozenModel):
    status: Literal["DEFERRED_UNTIL_INPUT_SUCCESSORS_EXIST"]
    implementation_authorized_by_current_accepted_design: Literal[False]
    quality_gate_must_precede_runtime_improvement_claim: Literal[True]
    producer_mutation_prerequisite: Literal[False]


class AuditConclusion(FrozenModel):
    producer_change_is_first_missing_boundary: Literal[False]
    first_missing_boundary: Literal["FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1"]
    producer_modification_permitted_only_if_successor_integration_proves_missing_hook: Literal[True]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class SafetyState(FrozenModel):
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    source_mutation_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class SeamAuditRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    audit_id: Literal["auragateway-final-342-producer-review-analysis-seam-audit-v1"]
    status: Literal["PROPOSED_FOR_FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAM_AUDIT_ACCEPTANCE"]
    base_main_commit: Literal["6320f1e636897c8cf90bcd3094eaae93b5cd5530"]
    decision: Literal["FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAM_AUDIT_V1"]
    source_bindings: tuple[SourceBinding, ...] = Field(min_length=10, max_length=10)
    producer_seam: ProducerSeam
    review_seams: ReviewSeams
    quality_seams: QualitySeams
    feedback_seam: FeedbackSeam
    analysis_engine_seam: AnalysisEngineSeam
    implementation_sequence: tuple[
        Literal["FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1"],
        Literal["FINAL_342_MEASURED_QUALITY_REDUCERS_V1"],
        Literal["FINAL_342_MEASURED_FEEDBACK_SUCCESSOR_V1"],
        Literal["FINAL_342_ANALYSIS_ENGINE_V1"],
        Literal["FINAL_342_OFFLINE_ORCHESTRATION_AND_INTEGRATION_REHEARSAL_V1"],
    ]
    audit_conclusion: AuditConclusion
    safety_state: SafetyState
    next_gate: Literal["AUTHOR_FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1"]

    @model_validator(mode="after")
    def validate_source_set(self) -> SeamAuditRecord:
        observed = {item.path: item.git_blob_sha for item in self.source_bindings}
        if observed != EXPECTED_SOURCE_BLOBS:
            raise ValueError("seam audit source binding set drifted")
        return self


def _read_json(root: Path, relative: Path) -> dict[str, object]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_JSON_READ_FAILED",
            f"unable to read required JSON: {relative.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_JSON_SHAPE_INVALID",
            f"required JSON must be an object: {relative.as_posix()}",
        )
    return value


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_GIT_FAILED",
            f"git inspection failed: {' '.join(args[:2])}",
        )
    return completed.stdout.strip()


def _validate_base(root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", EXPECTED_BASE_MAIN, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_BASE_MAIN_MISSING",
            "accepted G11.6 merge is not an ancestor of current HEAD",
        )


def _validate_source_bindings(root: Path, record: SeamAuditRecord) -> None:
    for binding in record.source_bindings:
        observed = _git(root, "hash-object", "--", binding.path)
        if observed != binding.git_blob_sha:
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_SOURCE_DRIFT",
                f"bound seam-audit source drifted: {binding.path}",
            )


def _validate_producer_seam(root: Path) -> None:
    text = (root / PRODUCER_PATH).read_text(encoding="utf-8")
    required_markers = (
        "class TransportExecutionResult:",
        "response_object: dict[str, object] | None",
        "response_json_object_valid: bool",
        "def execute_transport_attempt(",
        "result = transport.send(",
        "persisted = record_transport_outcome(reserved, result.record)",
        "store.persist(persisted)",
        "return persisted, result",
        '"attempt_action_ledger_v1.json"',
        '"turn_measurements_v1.json"',
        '"request_reconciliation_v1.json"',
        '"failure_report_v1.json"',
        '"trajectory_terminal_ledger_v1.json"',
        '"raw_outputs_included": False',
    )
    missing = tuple(marker for marker in required_markers if marker not in text)
    if missing:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_PRODUCER_HOOK_MISSING",
            f"producer seam marker missing: {missing[0]}",
        )

    persist_index = text.index("store.persist(persisted)")
    return_index = text.index("return persisted, result", persist_index)
    if persist_index >= return_index:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_PRODUCER_ORDER_INVALID",
            "transport evidence must persist before transient response return",
        )


def _episode_terminal_decisions(root: Path) -> dict[str, str]:
    payload = _read_json(root, EPISODES_PATH)
    episodes = payload.get("episodes")
    if not isinstance(episodes, list) or len(episodes) != 18:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_EPISODE_SET_INVALID",
            "functional episode set must contain exactly 18 episodes",
        )
    result: dict[str, str] = {}
    for item in episodes:
        if not isinstance(item, dict):
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_EPISODE_ROW_INVALID",
                "functional episode row must be an object",
            )
        episode_id = item.get("episode_id")
        terminal = item.get("expected_terminal_decision")
        if not isinstance(episode_id, str) or not isinstance(terminal, dict):
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_EPISODE_TERMINAL_MISSING",
                "functional episode terminal decision is incomplete",
            )
        decision = terminal.get("decision")
        if decision not in {"answer", "clarify", "escalate", "refuse"}:
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_EPISODE_DECISION_INVALID",
                "functional episode terminal decision drifted",
            )
        result[episode_id] = decision
    return result


def derive_secondary_schedule(root: Path) -> tuple[dict[str, object], ...]:
    ledger = _read_json(root, LEDGER_PATH)
    runs = ledger.get("runs")
    if not isinstance(runs, list):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_LEDGER_INVALID",
            "planned-run ledger runs must be an array",
        )
    functional = [
        item for item in runs if isinstance(item, dict) and item.get("workload") == "functional"
    ]
    if len(functional) != FUNCTIONAL_POPULATION:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_FUNCTIONAL_POPULATION_DRIFT",
            "planned functional trajectory count must remain 162",
        )

    terminal_by_episode = _episode_terminal_decisions(root)
    allocation = review_design.secondary_review_stratum_allocation()

    by_stratum: dict[tuple[str, str], list[dict[str, object]]] = {}
    for run in functional:
        run_id = run.get("run_id")
        episode_id = run.get("episode_id")
        condition_id = run.get("condition_id")
        if (
            not isinstance(run_id, str)
            or not isinstance(episode_id, str)
            or condition_id not in {"A", "B", "C"}
        ):
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_FUNCTIONAL_RUN_INVALID",
                "functional planned-run identity is incomplete",
            )
        decision = terminal_by_episode.get(episode_id)
        if decision is None:
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_EPISODE_LINKAGE_INVALID",
                "functional run references unknown episode",
            )
        by_stratum.setdefault((condition_id, decision), []).append(run)

    if set(by_stratum) != set(allocation):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_STRATUM_SET_DRIFT",
            "functional schedule strata differ from review design",
        )

    selected: list[dict[str, object]] = []
    for key, count in allocation.items():
        ranked = sorted(
            by_stratum[key],
            key=lambda run: hashlib.sha256(
                (
                    f"auragateway-final-342-review-secondary-v1|{SECONDARY_SEED}|{run['run_id']}"
                ).encode()
            ).hexdigest(),
        )
        selected.extend(ranked[:count])

    def planned_order_index(run: dict[str, object]) -> int:
        value = run.get("planned_order_index")
        if not isinstance(value, int) or isinstance(value, bool):
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_PLANNED_ORDER_INDEX_INVALID",
                "functional planned-order index must be an integer",
            )
        return value

    selected = sorted(selected, key=planned_order_index)
    if len(selected) != SECONDARY_TARGET:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_SECONDARY_TARGET_DRIFT",
            "derived secondary-review schedule must contain exactly 41 runs",
        )
    run_ids = [str(item["run_id"]) for item in selected]
    if len(run_ids) != len(set(run_ids)):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_SECONDARY_DUPLICATE",
            "derived secondary-review schedule contains duplicate run IDs",
        )

    rows: list[dict[str, object]] = []
    for run in selected:
        run_id = str(run["run_id"])
        episode_id = str(run["episode_id"])
        condition_id = str(run["condition_id"])
        decision = terminal_by_episode[episode_id]
        item_id = review_design.review_item_id(run_id)
        rows.append(
            {
                "run_id": run_id,
                "episode_id": episode_id,
                "condition_id": condition_id,
                "expected_terminal_decision": decision,
                "review_item_id": item_id,
                "secondary_assignment_id": review_design.role_assignment_id(item_id, "secondary"),
            }
        )
    return tuple(rows)


def _validate_review_and_analysis_contracts(root: Path) -> None:
    review = _read_json(root, REVIEW_RECORD_PATH)
    analysis = _read_json(root, ANALYSIS_RECORD_PATH)

    capture = review.get("capture_policy")
    reuse = review.get("reuse_policy")
    sampling = review.get("sampling_policy")
    population = review.get("review_population")
    if not all(isinstance(item, dict) for item in (capture, reuse, sampling, population)):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_REVIEW_DESIGN_INVALID",
            "measured-review design sections are incomplete",
        )
    assert isinstance(capture, dict)
    assert isinstance(reuse, dict)
    assert isinstance(sampling, dict)
    assert isinstance(population, dict)

    if capture.get("capture_boundary") != "successful_response_before_public_only_reduction":
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_CAPTURE_BOUNDARY_DRIFT",
            "protected capture boundary drifted",
        )
    if reuse.get("measured_reviewer_export_requires_thin_successor") is not True:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_EXPORTER_REQUIREMENT_DRIFT",
            "measured reviewer exporter successor requirement drifted",
        )
    if sampling.get("exact_schedule_materialized_before_manifest_freeze") is not True:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_SCHEDULE_REQUIREMENT_DRIFT",
            "secondary schedule pre-freeze requirement drifted",
        )
    if population.get("secondary_review_target_count") != SECONDARY_TARGET:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_REVIEW_TARGET_DRIFT",
            "secondary-review target drifted",
        )

    boundary = analysis.get("implementation_boundary")
    quality = analysis.get("quality_analysis")
    feedback = analysis.get("feedback_analysis")
    if not all(isinstance(item, dict) for item in (boundary, quality, feedback)):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_ANALYSIS_CONTRACT_INVALID",
            "analysis implementation-boundary sections are incomplete",
        )
    assert isinstance(boundary, dict)
    assert isinstance(quality, dict)
    assert isinstance(feedback, dict)

    required_true = (
        "exact_secondary_review_schedule_implementation_still_required",
        "measured_protected_review_exporter_implementation_still_required",
        "measured_task_success_reducer_implementation_still_required",
        "unsafe_behavior_regression_reducer_implementation_still_required",
        "measured_feedback_successor_implementation_still_required",
        "producer_review_analysis_seam_audit_required_next",
    )
    for key in required_true:
        if boundary.get(key) is not True:
            raise AuditError(
                "FINAL_342_SEAM_AUDIT_REQUIRED_SUCCESSOR_DRIFT",
                f"analysis successor requirement drifted: {key}",
            )
    if boundary.get("producer_modification_authorized_by_this_decision") is not False:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_PRODUCER_AUTHORITY_DRIFT",
            "analysis design unexpectedly authorizes producer modification",
        )
    if boundary.get("analysis_engine_implementation_authorized_by_this_decision") is not False:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_ANALYSIS_AUTHORITY_DRIFT",
            "analysis engine is prematurely authorized",
        )
    if (
        quality.get("historical_synthetic_quality_gate_direct_measured_reuse_permitted")
        is not False
    ):
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_QUALITY_REUSE_DRIFT",
            "historical synthetic quality gate cannot be direct measured input",
        )
    if feedback.get("historical_synthetic_feedback_direct_measured_reuse_permitted") is not False:
        raise AuditError(
            "FINAL_342_SEAM_AUDIT_FEEDBACK_REUSE_DRIFT",
            "historical synthetic feedback cannot be direct measured input",
        )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record = SeamAuditRecord.model_validate(_read_json(root, RECORD_PATH))
    _validate_base(root)
    _validate_source_bindings(root, record)
    _validate_producer_seam(root)
    _validate_review_and_analysis_contracts(root)
    schedule = derive_secondary_schedule(root)

    return {
        "status": "FINAL_342_PRODUCER_REVIEW_ANALYSIS_SEAM_AUDIT_V1_VALID",
        "producer_modification_required": False,
        "existing_transient_response_hook": True,
        "secondary_schedule_derivable": True,
        "secondary_schedule_count": len(schedule),
        "missing_review_successor_count": 2,
        "missing_quality_successor_count": 2,
        "missing_feedback_successor_count": 1,
        "analysis_engine_deferred": True,
        "manifest_freeze_permitted": False,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate(Path(args.repo_root))
    except (AuditError, ValidationError, OSError, UnicodeDecodeError) as error:
        if isinstance(error, AuditError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "FINAL_342_SEAM_AUDIT_VALIDATION_FAILED"
            message = str(error)
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
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
