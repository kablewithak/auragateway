"""Controlled, scripted A/B/C smoke execution with bounded terminal evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from auragateway.contracts.benchmark_smoke import (
    ControlledSmokeAuthorization,
    ControlledSmokeReport,
    EpisodeSetProjection,
    Gate10ManifestProjection,
    ScriptedRunScenario,
    ScriptedSmokeFixtureSet,
    SmokeAttemptOutcome,
    SmokeAttemptRecord,
    SmokeFailureCode,
    SmokePlanLedgerProjection,
    SmokePlanRunProjection,
    SmokeRunRecordSet,
    SmokeTerminalRecord,
    TerminalStatusCount,
)
from auragateway.contracts.evidence_bundle import RunTerminalStatus

_GATE10_MANIFEST_PATH = Path("data/evals/benchmark/freeze-v1/manifest.json")
_EXECUTION_MANIFEST_PATH = Path("data/evals/benchmark/freeze-v1/execution_manifest.json")
_GATE9_MANIFEST_PATH = Path("data/evals/benchmark/preflight-v1/manifest.json")
_PLAN_PATH = Path("data/evals/benchmark/preflight-v1/planned_run_ledger.json")
_EPISODE_SET_PATH = Path("data/evals/episodes/functional-v1/accepted_episodes.json")


class ControlledSmokeError(Exception):
    """Expected controlled-smoke failure with metadata-safe details."""

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


def model_json_bytes(model: BaseModel) -> bytes:
    """Serialize a typed artifact deterministically using field declaration order."""

    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_REQUIRED_ASSET_MISSING",
            "A required controlled-smoke asset was not found.",
            str(path),
        ) from exc


def execution_manifest_canonical_sha256(payload: dict[str, object]) -> str:
    """Reproduce the Gate 10 canonical digest without the self-hash field."""

    copied = json.loads(json.dumps(payload))
    identity = copied.get("identity")
    if not isinstance(identity, dict):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_MANIFEST_INVALID",
            "Frozen execution manifest identity is missing or invalid.",
        )
    identity.pop("execution_manifest_sha256", None)
    normalized = json.dumps(copied, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(normalized.encode("utf-8"))


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_REQUIRED_ASSET_MISSING",
            "A required controlled-smoke asset was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_INVALID_JSON",
            "A controlled-smoke asset is not valid JSON.",
            str(path),
        ) from exc


def _projection(path: Path, model_type: type[BaseModel]) -> BaseModel:
    try:
        return model_type.model_validate(_load_json(path))
    except Exception as exc:
        if isinstance(exc, ControlledSmokeError):
            raise
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_ASSET_VALIDATION_FAILED",
            "A controlled-smoke upstream asset failed typed projection.",
            str(path),
            (str(exc),),
        ) from exc


def validate_upstream(
    repo_root: Path,
    authorization: ControlledSmokeAuthorization,
) -> tuple[SmokePlanLedgerProjection, EpisodeSetProjection]:
    """Verify Gate 9, Gate 10, the frozen manifest, plan bytes, and episode split."""

    gate10_path = repo_root / _GATE10_MANIFEST_PATH
    if sha256_file(gate10_path) != authorization.gate10_manifest_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_GATE10_MANIFEST_MISMATCH",
            "Gate 10 manifest bytes do not match the smoke authorization.",
            str(gate10_path),
        )
    gate10 = Gate10ManifestProjection.model_validate(_load_json(gate10_path))
    if not gate10.gate_10_passed or gate10.execution_enabled:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_GATE10_NOT_ELIGIBLE",
            "Gate 10 must pass while measured execution remains disabled.",
            str(gate10_path),
        )
    if gate10.measured_execution_permitted:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_UNSAFE_GATE10_STATE",
            "Gate 10 may not authorize measured execution for this smoke.",
            str(gate10_path),
        )

    execution_path = repo_root / gate10.execution_manifest_path
    if sha256_file(execution_path) != gate10.execution_manifest_file_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_MANIFEST_FILE_MISMATCH",
            "Frozen execution-manifest file bytes do not match Gate 10.",
            str(execution_path),
        )
    execution_payload = _load_json(execution_path)
    if not isinstance(execution_payload, dict):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_MANIFEST_INVALID",
            "Frozen execution manifest must be a JSON object.",
            str(execution_path),
        )
    canonical = execution_manifest_canonical_sha256(execution_payload)
    if canonical != gate10.execution_manifest_canonical_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_MANIFEST_CANONICAL_MISMATCH",
            "Frozen execution-manifest canonical digest does not reproduce.",
            str(execution_path),
        )
    if canonical != authorization.execution_manifest_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_AUTHORIZATION_MANIFEST_MISMATCH",
            "Smoke authorization targets a different execution manifest.",
            str(execution_path),
        )
    identity = execution_payload.get("identity")
    if not isinstance(identity, dict):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_MANIFEST_INVALID",
            "Frozen execution manifest identity is missing.",
            str(execution_path),
        )
    if identity.get("execution_manifest_status") != "frozen":
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_MANIFEST_NOT_FROZEN",
            "Controlled smoke requires a frozen execution manifest.",
            str(execution_path),
        )
    if identity.get("execution_enabled") is not False:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EXECUTION_ENABLEMENT_UNSAFE",
            "Frozen benchmark execution must remain disabled during scripted smoke.",
            str(execution_path),
        )

    gate9_path = repo_root / gate10.gate9_manifest_path
    if sha256_file(gate9_path) != authorization.gate9_manifest_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_GATE9_MANIFEST_MISMATCH",
            "Gate 9 manifest bytes do not match the smoke authorization.",
            str(gate9_path),
        )
    gate9_payload = _load_json(gate9_path)
    from auragateway.contracts.benchmark_smoke import Gate9ManifestProjection

    gate9 = Gate9ManifestProjection.model_validate(gate9_payload)
    if not gate9.planning_ready or gate9.execution_enabled or gate9.measured_execution_permitted:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_GATE9_NOT_ELIGIBLE",
            "Gate 9 must remain planning-ready and non-executing.",
            str(gate9_path),
        )
    if gate9.plan_sha256 != authorization.planned_run_ledger_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_PLAN_AUTHORIZATION_MISMATCH",
            "Gate 9 plan identity does not match the smoke authorization.",
            str(gate9_path),
        )
    plan_path = repo_root / gate9.plan_path
    if sha256_file(plan_path) != authorization.planned_run_ledger_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_PLAN_FILE_MISMATCH",
            "Planned-run ledger bytes do not match the authorized Gate 9 plan.",
            str(plan_path),
        )
    plan = SmokePlanLedgerProjection.model_validate(_load_json(plan_path))

    episode_path = repo_root / _EPISODE_SET_PATH
    if sha256_file(episode_path) != authorization.functional_episode_set_sha256:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EPISODE_SET_MISMATCH",
            "Functional episode-set bytes do not match the authorization.",
            str(episode_path),
        )
    episodes = EpisodeSetProjection.model_validate(_load_json(episode_path))
    validate_authorized_projection(authorization, plan, episodes)
    return plan, episodes


def validate_authorized_projection(
    authorization: ControlledSmokeAuthorization,
    plan: SmokePlanLedgerProjection,
    episodes: EpisodeSetProjection,
) -> tuple[SmokePlanRunProjection, ...]:
    """Restrict the smoke to one development pair and all three conditions."""

    episode_splits = {item.episode_id: item.evaluation_split for item in episodes.episodes}
    for episode_id in authorization.allowed_episode_ids:
        if episode_splits.get(episode_id) != "development":
            raise ControlledSmokeError(
                "CONTROLLED_SMOKE_HELD_OUT_EPISODE_BLOCKED",
                "Controlled smoke may use development episodes only.",
                details=(episode_id,),
            )
    selected = tuple(item for item in plan.runs if item.run_id in authorization.allowed_run_ids)
    if len(selected) != authorization.maximum_run_count:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_AUTHORIZED_RUN_SET_INCOMPLETE",
            "Every authorized run must exist in the frozen plan exactly once.",
        )
    if tuple(item.run_id for item in selected) != authorization.allowed_run_ids:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_RUN_ORDER_MISMATCH",
            "Authorized runs must preserve frozen plan order.",
        )
    if any(item.workload != "functional" for item in selected):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_NONFUNCTIONAL_RUN_BLOCKED",
            "Controlled smoke permits functional development runs only.",
        )
    if any(item.episode_id not in authorization.allowed_episode_ids for item in selected):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_EPISODE_SCOPE_VIOLATION",
            "Selected runs must belong to the authorized development episode.",
        )
    if any(item.turn_count != authorization.turns_per_run for item in selected):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_TURN_COUNT_MISMATCH",
            "Selected runs must preserve the frozen four-turn workload.",
        )
    if {item.condition_id for item in selected} != set(authorization.allowed_conditions):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_CONDITION_COVERAGE_INVALID",
            "Selected runs must cover conditions A, B, and C exactly.",
        )
    pair_ids = {item.comparison_pair_id for item in selected}
    replication_ids = {item.replication_id for item in selected}
    if len(pair_ids) != 1 or replication_ids != {"replication-01"}:
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_PAIR_SCOPE_INVALID",
            "Controlled smoke must use one frozen replication-01 A/B/C pair.",
        )
    namespaces = [item.cache_namespace_id for item in selected]
    if len(namespaces) != len(set(namespaces)):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_CACHE_NAMESPACE_REUSE",
            "Controlled smoke requires distinct condition cache namespaces.",
        )
    return selected


def _opaque_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:24]}"


def _retry_authorized(
    scenario: ScriptedRunScenario,
    position: int,
) -> bool:
    attempt = scenario.attempts[position]
    if attempt.outcome is not SmokeAttemptOutcome.DEFINITE_RETRYABLE_FAILURE:
        return False
    if attempt.attempt_index != 1 or position + 1 >= len(scenario.attempts):
        return False
    following = scenario.attempts[position + 1]
    return (
        following.turn_index == attempt.turn_index
        and following.attempt_index == 2
        and following.logical_request_sha256 == attempt.logical_request_sha256
    )


def _terminal(
    run: SmokePlanRunProjection,
    trace_id: str,
    attempts: list[SmokeAttemptRecord],
    status: RunTerminalStatus,
    completed_turn_count: int,
    failure_code: SmokeFailureCode | None,
) -> SmokeTerminalRecord:
    return SmokeTerminalRecord(
        terminal_record_id=_opaque_id(
            "terminal",
            run.run_id,
            status.value,
            len(attempts),
            failure_code.value if failure_code is not None else "none",
        ),
        trace_id=trace_id,
        run_id=run.run_id,
        comparison_pair_id=run.comparison_pair_id,
        episode_id=run.episode_id,
        condition_id=run.condition_id,
        cache_namespace_id=run.cache_namespace_id,
        terminal_status=status,
        completed_turn_count=completed_turn_count,
        attempt_count=len(attempts),
        attempt_ids=tuple(item.attempt_id for item in attempts),
        failure_code=failure_code,
    )


def execute_controlled_smoke(
    authorization: ControlledSmokeAuthorization,
    fixtures: ScriptedSmokeFixtureSet,
    plan: SmokePlanLedgerProjection,
    episodes: EpisodeSetProjection,
    existing: SmokeRunRecordSet | None = None,
) -> tuple[SmokeRunRecordSet, int]:
    """Execute scripted attempts while preserving any existing terminal records."""

    selected = validate_authorized_projection(authorization, plan, episodes)
    scenarios = {item.run_id: item for item in fixtures.scenarios}
    if set(scenarios) != set(authorization.allowed_run_ids):
        raise ControlledSmokeError(
            "CONTROLLED_SMOKE_FIXTURE_SCOPE_MISMATCH",
            "Scripted fixtures must cover the authorized run set exactly.",
        )

    terminal_records = list(existing.terminal_records) if existing is not None else []
    attempt_records = list(existing.attempt_records) if existing is not None else []
    if existing is not None:
        if existing.authorization_id != authorization.authorization_id:
            raise ControlledSmokeError(
                "CONTROLLED_SMOKE_RESUME_AUTHORIZATION_MISMATCH",
                "Existing smoke evidence belongs to a different authorization.",
            )
        if existing.execution_manifest_sha256 != authorization.execution_manifest_sha256:
            raise ControlledSmokeError(
                "CONTROLLED_SMOKE_RESUME_MANIFEST_MISMATCH",
                "Existing smoke evidence belongs to a different execution manifest.",
            )
    existing_by_run = {item.run_id: item for item in terminal_records}
    reused = len(existing_by_run)
    total_cost = sum(item.estimated_cost_microusd for item in attempt_records)

    for run in selected:
        if run.run_id in existing_by_run:
            continue
        scenario = scenarios[run.run_id]
        trace_id = _opaque_id("trace", authorization.execution_manifest_sha256, run.run_id)
        run_attempts: list[SmokeAttemptRecord] = []
        completed_turns: set[int] = set()
        terminal: SmokeTerminalRecord | None = None
        for position, fixture in enumerate(scenario.attempts):
            if len(attempt_records) >= authorization.maximum_total_attempt_count:
                terminal = _terminal(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.BUDGET_EXHAUSTED,
                    len(completed_turns),
                    SmokeFailureCode.ATTEMPT_BUDGET_EXHAUSTED,
                )
                break
            next_cost = total_cost + fixture.estimated_cost_microusd
            if next_cost > authorization.maximum_total_cost_microusd:
                terminal = _terminal(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.BUDGET_EXHAUSTED,
                    len(completed_turns),
                    SmokeFailureCode.COST_BUDGET_EXHAUSTED,
                )
                break
            retry_authorized = _retry_authorized(scenario, position)
            attempt = SmokeAttemptRecord(
                attempt_id=_opaque_id(
                    "attempt",
                    run.run_id,
                    fixture.turn_index,
                    fixture.attempt_index,
                    fixture.provider_request_id_sha256,
                ),
                trace_id=trace_id,
                run_id=run.run_id,
                turn_index=fixture.turn_index,
                attempt_index=fixture.attempt_index,
                outcome=fixture.outcome,
                response_certainty=fixture.response_certainty,
                retry_authorized=retry_authorized,
                logical_request_sha256=fixture.logical_request_sha256,
                provider_request_id_sha256=fixture.provider_request_id_sha256,
                output_sha256=fixture.output_sha256,
                provider_error_code=fixture.provider_error_code,
                input_tokens=fixture.input_tokens,
                output_tokens=fixture.output_tokens,
                latency_ms=fixture.latency_ms,
                estimated_cost_microusd=fixture.estimated_cost_microusd,
            )
            run_attempts.append(attempt)
            attempt_records.append(attempt)
            total_cost = next_cost

            if fixture.outcome is SmokeAttemptOutcome.COMPLETED:
                completed_turns.add(fixture.turn_index)
                if len(completed_turns) == authorization.turns_per_run:
                    terminal = _terminal(
                        run,
                        trace_id,
                        run_attempts,
                        RunTerminalStatus.COMPLETED,
                        len(completed_turns),
                        None,
                    )
                    break
            elif fixture.outcome is SmokeAttemptOutcome.DEFINITE_RETRYABLE_FAILURE:
                if not retry_authorized:
                    terminal = _terminal(
                        run,
                        trace_id,
                        run_attempts,
                        RunTerminalStatus.PROVIDER_ERROR,
                        len(completed_turns),
                        SmokeFailureCode.RETRY_BUDGET_EXHAUSTED,
                    )
                    break
            elif fixture.outcome is SmokeAttemptOutcome.AMBIGUOUS_RESPONSE:
                terminal = _terminal(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.ABORTED_SAFETY_CONTROL,
                    len(completed_turns),
                    SmokeFailureCode.AMBIGUOUS_PROVIDER_RESPONSE,
                )
                break
            else:
                terminal = _terminal(
                    run,
                    trace_id,
                    run_attempts,
                    RunTerminalStatus.PROVIDER_ERROR,
                    len(completed_turns),
                    SmokeFailureCode.NONRETRYABLE_PROVIDER_FAILURE,
                )
                break
        if terminal is None:
            terminal = _terminal(
                run,
                trace_id,
                run_attempts,
                RunTerminalStatus.PROVIDER_ERROR,
                len(completed_turns),
                SmokeFailureCode.SCRIPT_INCOMPLETE,
            )
        terminal_records.append(terminal)

    order = {run_id: index for index, run_id in enumerate(authorization.allowed_run_ids)}
    terminal_records.sort(key=lambda item: order[item.run_id])
    attempt_records.sort(key=lambda item: (order[item.run_id], item.turn_index, item.attempt_index))
    return (
        SmokeRunRecordSet(
            smoke_id=authorization.smoke_id,
            authorization_id=authorization.authorization_id,
            execution_manifest_sha256=authorization.execution_manifest_sha256,
            terminal_records=tuple(terminal_records),
            attempt_records=tuple(attempt_records),
            total_attempt_count=len(attempt_records),
            total_estimated_cost_microusd=sum(
                item.estimated_cost_microusd for item in attempt_records
            ),
        ),
        reused,
    )


def build_smoke_report(
    authorization: ControlledSmokeAuthorization,
    fixtures: ScriptedSmokeFixtureSet,
    records: SmokeRunRecordSet,
    resume_preserved: bool,
) -> ControlledSmokeReport:
    """Evaluate the smoke against predeclared terminal and safety expectations."""

    expected = {item.run_id: item.expected_terminal_status for item in fixtures.scenarios}
    matched = all(
        expected.get(item.run_id) is item.terminal_status for item in records.terminal_records
    ) and set(expected) == {item.run_id for item in records.terminal_records}
    counts = Counter(item.terminal_status for item in records.terminal_records)
    ordered_statuses = tuple(
        TerminalStatusCount(terminal_status=status, count=counts.get(status, 0))
        for status in RunTerminalStatus
        if counts.get(status, 0) > 0
    )
    retry_count = sum(item.retry_authorized for item in records.attempt_records)
    ambiguous_blocked = sum(
        item.outcome is SmokeAttemptOutcome.AMBIGUOUS_RESPONSE and not item.retry_authorized
        for item in records.attempt_records
    )
    attempt_budget_respected = (
        records.total_attempt_count <= authorization.maximum_total_attempt_count
    )
    cost_budget_respected = (
        records.total_estimated_cost_microusd <= authorization.maximum_total_cost_microusd
    )
    smoke_passed = all(
        (
            len(records.terminal_records) == authorization.maximum_run_count,
            matched,
            attempt_budget_respected,
            cost_budget_respected,
            resume_preserved,
            retry_count == 1,
            ambiguous_blocked == 1,
        )
    )
    return ControlledSmokeReport(
        smoke_id=authorization.smoke_id,
        authorization_id=authorization.authorization_id,
        execution_manifest_sha256=authorization.execution_manifest_sha256,
        selected_episode_ids=authorization.allowed_episode_ids,
        selected_run_count=authorization.maximum_run_count,
        terminal_record_count=len(records.terminal_records),
        attempt_record_count=len(records.attempt_records),
        retry_authorized_count=retry_count,
        ambiguous_retry_blocked_count=ambiguous_blocked,
        terminal_status_counts=ordered_statuses,
        expected_terminal_statuses_matched=matched,
        attempt_budget_respected=attempt_budget_respected,
        cost_budget_respected=cost_budget_respected,
        resume_preserved_terminal_records=resume_preserved,
        development_only=True,
        live_provider_called=False,
        held_out_executed=False,
        full_benchmark_executed=False,
        benchmark_claims_permitted=False,
        smoke_passed=smoke_passed,
    )


def build_controlled_smoke(
    authorization: ControlledSmokeAuthorization,
    fixtures: ScriptedSmokeFixtureSet,
    plan: SmokePlanLedgerProjection,
    episodes: EpisodeSetProjection,
    existing: SmokeRunRecordSet | None = None,
) -> tuple[SmokeRunRecordSet, ControlledSmokeReport, int]:
    """Build records and prove that resume cannot overwrite terminal evidence."""

    records, reused = execute_controlled_smoke(
        authorization,
        fixtures,
        plan,
        episodes,
        existing,
    )
    resumed, resume_reused = execute_controlled_smoke(
        authorization,
        fixtures,
        plan,
        episodes,
        records,
    )
    resume_preserved = resumed == records and resume_reused == len(records.terminal_records)
    report = build_smoke_report(authorization, fixtures, records, resume_preserved)
    return records, report, reused
