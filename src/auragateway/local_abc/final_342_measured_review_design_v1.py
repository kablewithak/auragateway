"""Validate the final-342 measured protected-review design decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_measured_review_design_v1.json")

EXPECTED_BASE_MAIN = "b2a67efa3abca65031090f52712ec87e816a911f"
EXPECTED_LEDGER_SHA256 = "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
EXPECTED_G10_SHA256 = "4c4345e57e7aae7453616bc90e405d6aa7aef9d2673e20bc060c99579a863b18"
EXPECTED_FUNCTIONAL_SET_SHA256 = "6229df94a6a426f815a2050172a79e115d9554031239043b397140ce13894285"
EXPECTED_EPISODE_MANIFEST_SHA256 = (
    "3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b"
)
EXPECTED_REVIEW_PROTOCOL_SHA256 = "925e614c3a81d7e438299436ddf3619fa462cd861e0b816f26937279506ab3af"
EXPECTED_RUBRIC_SHA256 = "7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"
EXPECTED_SOURCE_INVENTORY_SHA256 = (
    "25b34bbb646952f0b9345d25a9a958fcab9ca33e88696c474a41621e7f90a3be"
)

SECONDARY_REVIEW_SEED = 20260712
FUNCTIONAL_TRAJECTORY_COUNT = 162
SECONDARY_REVIEW_TARGET_COUNT = 41
EXPECTED_DECISION_COUNTS: dict[str, int] = {
    "answer": 10,
    "clarify": 3,
    "escalate": 3,
    "refuse": 2,
}
CONDITIONS = ("A", "B", "C")
REPETITIONS_PER_CONDITION = 3


class ReviewDesignError(RuntimeError):
    """Fail-closed measured-review design validation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReviewDesignError("FINAL_342_REVIEW_DESIGN_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceBinding(FrozenModel):
    role: str = Field(min_length=3)
    path: str = Field(min_length=3)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReviewPopulation(FrozenModel):
    planned_functional_trajectory_count: Literal[162]
    runtime_microbenchmark_trajectory_count: Literal[180]
    primary_assignment_slot_count: Literal[162]
    primary_review_fraction: Literal["1"]
    secondary_review_fraction: Literal["0.25"]
    secondary_review_target_count: Literal[41]
    review_unit: Literal["planned_functional_trajectory"]
    runtime_microbenchmark_human_review_required: Literal[False]
    post_result_case_selection_permitted: Literal[False]
    replacement_review_case_permitted: Literal[False]


class SamplingPolicy(FrozenModel):
    policy_id: Literal["final-342-measured-review-stratified-sampling-v1"]
    seed: Literal[20260712]
    target_rounding_rule: Literal["ceil_planned_functional_population_times_fraction"]
    stratum_fields: tuple[
        Literal["condition_id"],
        Literal["expected_terminal_decision"],
    ]
    observed_terminal_decision_used_for_sampling: Literal[False]
    allocation_method: Literal["hamilton_largest_remainder"]
    stratum_tie_break_domain: Literal[
        "auragateway-final-342-review-stratum-v1|{seed}|{condition_id}|{expected_terminal_decision}"
    ]
    within_stratum_rank_domain: Literal["auragateway-final-342-review-secondary-v1|{seed}|{run_id}"]
    ascending_sha256_rank: Literal[True]
    selected_nonreviewable_case_replacement_permitted: Literal[False]
    exact_schedule_materialized_before_manifest_freeze: Literal[True]
    final_manifest_binds_review_sample_schedule_sha256: Literal[True]


class IdentityPolicy(FrozenModel):
    review_item_identity_domain: Literal["auragateway-final-342-protected-review-v1|{run_id}"]
    review_item_id_is_lowercase_sha256: Literal[True]
    raw_run_id_reviewer_visible: Literal[False]
    role_assignment_identity_domain: Literal[
        "auragateway-final-342-measured-review-assignment-v1|{review_item_id}|{role}"
    ]
    role_assignment_public_shape: Literal["review-<first-24-lowercase-hex>"]
    primary_and_secondary_assignment_ids_distinct: Literal[True]
    protected_internal_linkage_required: Literal[True]
    internal_linkage_reviewer_visible: Literal[False]


class ReviewerPayload(FrozenModel):
    episode_id_visible: Literal[True]
    user_visible_conversation_required: Literal[True]
    candidate_assistant_outputs_required: Literal[True]
    terminal_decision_output_required: Literal[True]
    citation_and_retrieved_source_ids_permitted: Literal[True]
    frozen_source_evidence_permitted: Literal[True]
    deterministic_quality_summary_permitted: Literal[True]
    rubric_identity_required: Literal[True]
    internal_rendered_prompt_permitted: Literal[False]
    expected_answer_key_permitted: Literal[False]
    required_or_forbidden_claim_registry_visible: Literal[False]
    condition_id_visible: Literal[False]
    route_visible: Literal[False]
    worker_identity_visible: Literal[False]
    cache_namespace_visible: Literal[False]
    cache_telemetry_visible: Literal[False]
    latency_visible: Literal[False]
    cost_visible: Literal[False]
    planned_run_order_visible: Literal[False]
    condition_fingerprint_visible: Literal[False]


class CapturePolicy(FrozenModel):
    capture_boundary: Literal["successful_response_before_public_only_reduction"]
    protected_turn_capture_is_append_only: Literal[True]
    protected_capture_failure_changes_model_or_conversation_behavior: Literal[False]
    protected_capture_failure_is_model_quality_failure: Literal[False]
    protected_capture_failure_may_be_silent: Literal[False]
    candidate_exists_capture_failed_quality_state: Literal["EVIDENCE_INCOMPLETE"]
    no_candidate_due_execution_failure_review_state: Literal["NOT_REVIEWABLE_EXECUTION_FAILURE"]
    captured_candidate_review_state: Literal["REVIEWABLE"]
    quality_non_inferiority_permitted_with_capture_gap: Literal[False]
    runtime_improvement_claim_permitted_with_capture_gap: Literal[False]
    original_execution_evidence_preserved: Literal[True]
    rerun_requires_fresh_execution_authority: Literal[True]


class RetentionPolicy(FrozenModel):
    policy_id: Literal["final-342-protected-review-event-retention-v1"]
    arbitrary_calendar_retention_period_required: Literal[False]
    raw_protected_material_deletion_permitted_only_after_review_complete: Literal[True]
    raw_protected_material_deletion_permitted_only_after_adjudication_complete: Literal[True]
    raw_protected_material_deletion_permitted_only_after_analysis_inputs_materialized: Literal[True]
    raw_protected_material_deletion_permitted_only_after_public_receipt_verified: Literal[True]
    deletion_receipt_required: Literal[True]
    retained_after_deletion: tuple[
        Literal["hashes"],
        Literal["opaque_ids"],
        Literal["counts"],
        Literal["review_verdicts"],
        Literal["criterion_scores"],
        Literal["failure_labels"],
        Literal["adjudication_metadata"],
        Literal["deletion_receipt"],
    ]


class ReusePolicy(FrozenModel):
    frozen_rubric_reused: Literal[True]
    historical_disagreement_detection_reused: Literal[True]
    historical_adjudication_invariants_reused: Literal[True]
    frozen_corpus_and_source_inventory_reused: Literal[True]
    frozen_episode_definitions_reused: Literal[True]
    historical_episode_unique_assignment_manifest_reused_as_final_schedule: Literal[False]
    historical_unique_episode_assignment_builder_requires_successor: Literal[True]
    measured_reviewer_export_requires_thin_successor: Literal[True]
    final_execution_producer_redesign_authorized_by_this_decision: Literal[False]


class SafetyState(FrozenModel):
    source_mutation_authorized: Literal[False]
    rehearsal_files_authorized: Literal[False]
    execution_manifest_frozen: Literal[False]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]


class ReviewDesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    design_id: Literal["auragateway-final-342-measured-review-design-v1"]
    status: Literal["PROPOSED_FOR_FINAL_342_MEASURED_REVIEW_DESIGN_ACCEPTANCE"]
    base_main_commit: Literal["b2a67efa3abca65031090f52712ec87e816a911f"]
    decision: Literal["FINAL_342_MEASURED_PROTECTED_REVIEW_DESIGN_V1"]
    source_bindings: tuple[SourceBinding, ...]
    review_population: ReviewPopulation
    sampling_policy: SamplingPolicy
    identity_policy: IdentityPolicy
    reviewer_payload: ReviewerPayload
    capture_policy: CapturePolicy
    retention_policy: RetentionPolicy
    reuse_policy: ReusePolicy
    safety_state: SafetyState
    next_gate: Literal["DEFINE_FINAL_342_ANALYSIS_CONTRACTS_V1"]

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        roles = tuple(binding.role for binding in self.source_bindings)
        if len(roles) != len(set(roles)):
            raise ValueError("source binding roles must be unique")
        if self.review_population.secondary_review_target_count != secondary_review_target_count():
            raise ValueError("secondary review target count drifted")
        return self


def _read_bytes(repo_root: Path, relative: str) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_SOURCE_MISSING",
            f"required source is missing or symlinked: {relative}",
        )
    return path.read_bytes()


def _read_json(repo_root: Path, relative: str) -> object:
    try:
        return json.loads(_read_bytes(repo_root, relative).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_INVALID_JSON",
            f"required source is not valid JSON: {relative}",
        ) from exc


def _sha256_path(repo_root: Path, relative: str) -> str:
    return hashlib.sha256(_read_bytes(repo_root, relative)).hexdigest()


def _as_mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_SOURCE_SHAPE_INVALID",
            f"{name} must be a JSON object",
        )
    return value


def _require_sha(repo_root: Path, relative: str, expected: str) -> None:
    if _sha256_path(repo_root, relative) != expected:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_IDENTITY_DRIFT",
            f"measured-review source identity drifted: {relative}",
        )


def secondary_review_target_count() -> int:
    return math.ceil(FUNCTIONAL_TRAJECTORY_COUNT * 0.25)


def stratum_population_counts() -> dict[tuple[str, str], int]:
    return {
        (condition, decision): count * REPETITIONS_PER_CONDITION
        for condition in CONDITIONS
        for decision, count in EXPECTED_DECISION_COUNTS.items()
    }


def _stratum_tie_hash(condition: str, decision: str) -> str:
    material = (
        f"auragateway-final-342-review-stratum-v1|{SECONDARY_REVIEW_SEED}|{condition}|{decision}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def secondary_review_stratum_allocation() -> dict[tuple[str, str], int]:
    counts = stratum_population_counts()
    base = {key: value // 4 for key, value in counts.items()}
    remaining = SECONDARY_REVIEW_TARGET_COUNT - sum(base.values())
    ranked = sorted(
        counts,
        key=lambda key: (
            -(counts[key] % 4),
            _stratum_tie_hash(*key),
            key[0],
            key[1],
        ),
    )
    allocation = dict(base)
    for key in ranked[:remaining]:
        allocation[key] += 1
    return allocation


def review_item_id(run_id: str) -> str:
    material = f"auragateway-final-342-protected-review-v1|{run_id}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def role_assignment_id(item_id: str, role: Literal["primary", "secondary"]) -> str:
    material = f"auragateway-final-342-measured-review-assignment-v1|{item_id}|{role}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"review-{digest[:24]}"


def _validate_upstream(repo_root: Path, record: ReviewDesignRecord) -> None:
    expected = {
        "planned_run_ledger": EXPECTED_LEDGER_SHA256,
        "g10_repetition_statistical_freeze": EXPECTED_G10_SHA256,
        "functional_episode_set": EXPECTED_FUNCTIONAL_SET_SHA256,
        "episode_manifest": EXPECTED_EPISODE_MANIFEST_SHA256,
        "blinded_review_protocol": EXPECTED_REVIEW_PROTOCOL_SHA256,
        "quality_rubric": EXPECTED_RUBRIC_SHA256,
        "source_inventory": EXPECTED_SOURCE_INVENTORY_SHA256,
    }
    observed_roles = {binding.role for binding in record.source_bindings}
    if observed_roles != set(expected):
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_SOURCE_SET_DRIFT",
            "measured-review source binding roles drifted",
        )
    for binding in record.source_bindings:
        if binding.sha256 != expected[binding.role]:
            raise ReviewDesignError(
                "FINAL_342_REVIEW_DESIGN_RECORD_IDENTITY_DRIFT",
                f"recorded source identity drifted: {binding.role}",
            )
        _require_sha(repo_root, binding.path, binding.sha256)


def _validate_ledger(repo_root: Path) -> None:
    ledger = _as_mapping(
        _read_json(repo_root, "data/evals/benchmark/preflight-v3/planned_run_ledger.json"),
        "planned run ledger",
    )
    expected = {
        "functional_trajectory_count": 162,
        "runtime_trajectory_count": 180,
        "total_trajectory_count": 342,
        "total_turn_count": 1368,
        "maximum_request_attempt_count": 2736,
        "replacement_case_permitted": False,
        "execution_enabled": False,
    }
    for key, value in expected.items():
        if ledger.get(key) != value:
            raise ReviewDesignError(
                "FINAL_342_REVIEW_DESIGN_LEDGER_DRIFT",
                f"planned ledger field drifted: {key}",
            )
    runs = ledger.get("runs")
    if not isinstance(runs, list) or len(runs) != 342:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_LEDGER_RUNS_INVALID",
            "planned run ledger must contain exactly 342 trajectories",
        )
    functional = [
        _as_mapping(item, "planned run")
        for item in runs
        if isinstance(item, dict) and item.get("workload") == "functional"
    ]
    if len(functional) != 162:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_FUNCTIONAL_POPULATION_DRIFT",
            "planned ledger must contain exactly 162 functional trajectories",
        )
    run_ids = [item.get("run_id") for item in functional]
    if any(not isinstance(run_id, str) for run_id in run_ids):
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_RUN_ID_INVALID",
            "every functional trajectory requires a string run_id",
        )
    if len(run_ids) != len(set(run_ids)):
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_RUN_ID_DUPLICATE",
            "functional run IDs must remain unique",
        )


def _validate_quality_freeze(repo_root: Path) -> None:
    g10 = _as_mapping(
        _read_json(
            repo_root,
            "data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json",
        ),
        "G10 freeze",
    )
    quality = _as_mapping(g10.get("quality_non_inferiority"), "G10 quality contract")
    expected = {
        "primary_rubric_review_fraction": "1",
        "independent_double_review_fraction": "0.25",
        "double_review_seed": 20260712,
        "double_review_stratified_by_condition_and_terminal_decision": True,
        "reviewers_blinded_to_condition_route_cost_latency_and_cache": True,
    }
    for key, value in expected.items():
        if quality.get(key) != value:
            raise ReviewDesignError(
                "FINAL_342_REVIEW_DESIGN_G10_QUALITY_DRIFT",
                f"G10 quality field drifted: {key}",
            )
    accountability = _as_mapping(g10.get("run_accountability"), "G10 accountability")
    if accountability.get("replacement_cases_permitted") is not False:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_REPLACEMENT_POLICY_DRIFT",
            "replacement cases must remain prohibited",
        )


def _validate_episode_population(repo_root: Path) -> None:
    payload = _as_mapping(
        _read_json(repo_root, "data/evals/episodes/functional-v1/accepted_episodes.json"),
        "functional episode set",
    )
    if payload.get("episode_count") != 18 or payload.get("turns_per_episode") != 4:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_EPISODE_POPULATION_DRIFT",
            "functional episode count or turn count drifted",
        )
    episodes = payload.get("episodes")
    if not isinstance(episodes, list) or len(episodes) != 18:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_EPISODE_SET_INVALID",
            "functional episode set must contain exactly 18 episodes",
        )
    counts: dict[str, int] = {}
    for raw in episodes:
        episode = _as_mapping(raw, "functional episode")
        terminal = _as_mapping(
            episode.get("expected_terminal_decision"),
            "expected terminal decision",
        )
        decision = terminal.get("decision")
        if not isinstance(decision, str):
            raise ReviewDesignError(
                "FINAL_342_REVIEW_DESIGN_TERMINAL_DECISION_INVALID",
                "functional episode expected decision must be a string",
            )
        counts[decision] = counts.get(decision, 0) + 1
    if counts != EXPECTED_DECISION_COUNTS:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_TERMINAL_COUNTS_DRIFT",
            "functional expected terminal-decision counts drifted",
        )


def _validate_allocation() -> None:
    allocation = secondary_review_stratum_allocation()
    if sum(allocation.values()) != SECONDARY_REVIEW_TARGET_COUNT:
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_SAMPLE_ALLOCATION_INVALID",
            "secondary-review allocation does not total 41",
        )
    counts = stratum_population_counts()
    if set(allocation) != set(counts):
        raise ReviewDesignError(
            "FINAL_342_REVIEW_DESIGN_STRATA_INVALID",
            "secondary-review allocation must cover all 12 frozen strata",
        )
    for key, selected in allocation.items():
        if selected < counts[key] // 4 or selected > math.ceil(counts[key] / 4):
            raise ReviewDesignError(
                "FINAL_342_REVIEW_DESIGN_STRATUM_ALLOCATION_INVALID",
                f"stratum allocation is outside largest-remainder bounds: {key}",
            )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record = ReviewDesignRecord.model_validate(_read_json(root, RECORD_PATH.as_posix()))
    _validate_upstream(root, record)
    _validate_ledger(root)
    _validate_quality_freeze(root)
    _validate_episode_population(root)
    _validate_allocation()

    allocation = {
        f"{condition}:{decision}": count
        for (condition, decision), count in sorted(secondary_review_stratum_allocation().items())
    }
    return {
        "status": "FINAL_342_MEASURED_REVIEW_DESIGN_V1_VALID",
        "decision": record.decision,
        "functional_review_population": 162,
        "primary_assignment_slots": 162,
        "secondary_review_target_count": 41,
        "secondary_review_stratum_count": 12,
        "secondary_review_stratum_allocation": allocation,
        "review_unit": record.review_population.review_unit,
        "sampling_uses_expected_terminal_decision": True,
        "replacement_review_case_permitted": False,
        "protected_capture_failure_is_model_quality_failure": False,
        "quality_non_inferiority_permitted_with_capture_gap": False,
        "execution_manifest_frozen": record.safety_state.execution_manifest_frozen,
        "manifest_freeze_permitted": record.safety_state.manifest_freeze_permitted,
        "final_measured_abc_execution_authorized": (
            record.safety_state.final_measured_abc_execution_authorized
        ),
        "effect_claims_permitted": record.safety_state.effect_claims_permitted,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate(Path(args.repo_root))
    except (ReviewDesignError, UnicodeDecodeError, ValidationError, OSError) as error:
        if isinstance(error, ReviewDesignError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "FINAL_342_REVIEW_DESIGN_VALIDATION_FAILED"
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
