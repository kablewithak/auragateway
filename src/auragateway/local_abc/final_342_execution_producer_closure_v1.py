"""Close the final-342 evidence-producer graph before implementation and manifest freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from enum import StrEnum
from pathlib import Path
from typing import Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_MAIN_COMMIT = "b49ab57c41bfd646a5d35f6fa2972f98989fa48e"
NEXT_GATE = "IMPLEMENT_FINAL_342_EXECUTION_PRODUCER_V1"

CONSTITUTION_PATH = Path("docs/benchmark/AuraGateway_Benchmark_Constitution.md")
G10_FREEZE_PATH = Path(
    "data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json"
)
G11_ARCHITECTURE_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_runtime_requalification_architecture_v1.json"
)
G11_3A_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_requirements_precedence_reconciliation_v1.json"
)
FINAL_CORE_PATH = Path("src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py")
FINAL_WRAPPER_PATH = Path("src/auragateway/local_abc/final_342_transaction_wrapper_rehearsal_v1.py")
P5_P6_RUNTIME_PATH = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
V2_RUNTIME_PATH = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_bound_runtime_v1.py"
)
V2_REQUEST_ADAPTER_PATH = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1.py"
)
PREFLIGHT_FINGERPRINTS_PATH = Path("data/evals/benchmark/preflight-v3/condition_fingerprints.json")
V2_CLASSIFICATION_PATH = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_345461230_classification_v1.json"
)
P5_P6_ACCEPTANCE_PATH = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v2.json"
)

RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_execution_producer_closure_v1.json")
ADR_PATH = Path("docs/adr/2026-08-29-local-abc-final-342-execution-producer-closure-v1.md")
REPORT_PATH = Path("docs/reports/AuraGateway_Final_342_Execution_Producer_Closure_V1.md")

OBLIGATION_IDS = (
    "final_request_transport_and_worker_startup",
    "final_runtime_trace_manifest_binding",
    "final_measured_evidence_bundle_writer",
    "final_attempt_action_reconciliation_persistence",
    "protected_measured_review_exporter",
    "primary_secondary_failure_persistence",
    "teardown_cleanup_evidence_writer",
    "local_runtime_provider_field_mapping",
    "pricing_scope_and_cost_claim_mapping",
    "final_execution_analysis_input_schema",
)

SOURCE_BINDING_SPECS = (
    ("benchmark_constitution", CONSTITUTION_PATH),
    ("g10_repetition_statistical_freeze", G10_FREEZE_PATH),
    ("g11_runtime_architecture", G11_ARCHITECTURE_PATH),
    ("g11_3a_requirements_precedence", G11_3A_PATH),
    ("final_non_authorizing_core", FINAL_CORE_PATH),
    ("final_transaction_wrapper_rehearsal", FINAL_WRAPPER_PATH),
    ("accepted_exact_runtime_mechanics", P5_P6_RUNTIME_PATH),
    ("accepted_v2_evidence_runtime", V2_RUNTIME_PATH),
    ("accepted_v2_request_adapter", V2_REQUEST_ADAPTER_PATH),
    ("preflight_v3_condition_fingerprints", PREFLIGHT_FINGERPRINTS_PATH),
    ("accepted_v2_classification", V2_CLASSIFICATION_PATH),
    ("accepted_p5_p6_execution", P5_P6_ACCEPTANCE_PATH),
)


class ProducerClosureError(RuntimeError):
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


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ProducerClosureError("FINAL_342_PRODUCER_CLOSURE_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ClosureDisposition(StrEnum):
    BOUNDED_SUCCESSOR_REQUIRED = "BOUNDED_SUCCESSOR_REQUIRED"
    EXPLICITLY_OUT_OF_SCOPE = "EXPLICITLY_OUT_OF_SCOPE"


class BoundaryId(StrEnum):
    EXECUTION_PRODUCER = "FINAL_342_EXECUTION_PRODUCER_V1"
    PROTECTED_REVIEW = "FINAL_342_PROTECTED_REVIEW_EXPORT_V1"
    ANALYSIS_CONTRACTS = "FINAL_342_ANALYSIS_CONTRACTS_V1"


class ArtifactBinding(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ObligationDecision(FrozenModel):
    obligation_id: str = Field(min_length=1)
    disposition: ClosureDisposition
    successor_boundary: BoundaryId | None
    exact_reuse_sufficient: Literal[False] = False
    reuse_sources: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=20)

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        bounded = self.disposition is ClosureDisposition.BOUNDED_SUCCESSOR_REQUIRED
        if bounded and self.successor_boundary is None:
            raise ValueError("bounded successor decision requires an owning boundary")
        if not bounded and self.successor_boundary is not None:
            raise ValueError("out-of-scope decision cannot have an owning boundary")
        return self


class ImplementationBoundary(FrozenModel):
    boundary_id: BoundaryId
    owns_obligations: tuple[str, ...] = Field(min_length=1)
    purpose: str = Field(min_length=20)
    constraints: tuple[str, ...] = Field(min_length=1)


class CostScopeDecision(FrozenModel):
    monetary_cost_comparison_in_scope: Literal[False] = False
    monetary_cost_effect_claims_permitted: Literal[False] = False
    external_spend_ceiling: Literal[0] = 0
    accepted_local_monetary_pricing_schedule_bound: Literal[False] = False
    mechanism_and_latency_reporting_unchanged: Literal[True] = True
    rationale: str = Field(min_length=20)


class PersistenceContract(FrozenModel):
    contract_id: Literal["MONOTONIC_PHASE_PERSISTENCE_V1"] = "MONOTONIC_PHASE_PERSISTENCE_V1"
    phases: tuple[str, ...]
    persist_phase_truth_before_next_fallible_phase: Literal[True] = True
    first_causal_failure_preserved: Literal[True] = True
    secondary_failure_may_mask_primary: Literal[False] = False
    later_enrichment_may_erase_prior_truth: Literal[False] = False

    @model_validator(mode="after")
    def validate_phases(self) -> Self:
        if self.phases != _persistence_phases():
            raise ValueError("monotonic persistence phase order drifted")
        return self


class ForestConstraint(FrozenModel):
    mission: Literal["one trustworthy governable final 342-trajectory A/B/C execution"] = (
        "one trustworthy governable final 342-trajectory A/B/C execution"
    )
    general_benchmark_platform_build_permitted: Literal[False] = False
    full_runtime_rewrite_required: Literal[False] = False
    direct_v2_runtime_copy_permitted: Literal[False] = False
    accepted_mechanics_reused_when_semantics_match: Literal[True] = True
    evidence_without_claim_or_acceptance_value_must_be_added: Literal[False] = False


class SafetyState(FrozenModel):
    producer_obligation_classification_complete: Literal[True] = True
    final_producer_implementation_complete: Literal[False] = False
    complete_offline_producer_rehearsal_established: Literal[False] = False
    manifest_freeze_permitted: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False


class ProducerClosureRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    closure_id: Literal["auragateway-final-342-execution-producer-closure-v1"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_bindings: tuple[ArtifactBinding, ...]
    obligation_decisions: tuple[ObligationDecision, ...]
    implementation_boundaries: tuple[ImplementationBoundary, ...]
    cost_scope: CostScopeDecision
    persistence_contract: PersistenceContract
    forest_constraint: ForestConstraint
    safety_state: SafetyState
    next_gate: Literal["IMPLEMENT_FINAL_342_EXECUTION_PRODUCER_V1"]

    @model_validator(mode="after")
    def validate_closure(self) -> Self:
        observed_ids = tuple(item.obligation_id for item in self.obligation_decisions)
        if observed_ids != OBLIGATION_IDS or len(set(observed_ids)) != 10:
            raise ValueError("producer obligation order or coverage drifted")

        bounded = tuple(
            item
            for item in self.obligation_decisions
            if item.disposition is ClosureDisposition.BOUNDED_SUCCESSOR_REQUIRED
        )
        excluded = tuple(
            item
            for item in self.obligation_decisions
            if item.disposition is ClosureDisposition.EXPLICITLY_OUT_OF_SCOPE
        )
        if len(bounded) != 9 or len(excluded) != 1:
            raise ValueError("G11.3B must classify nine successors and one exclusion")
        if excluded[0].obligation_id != "pricing_scope_and_cost_claim_mapping":
            raise ValueError("only monetary pricing scope may be explicitly out of scope")

        expected_boundaries = (
            BoundaryId.EXECUTION_PRODUCER,
            BoundaryId.PROTECTED_REVIEW,
            BoundaryId.ANALYSIS_CONTRACTS,
        )
        observed_boundaries = tuple(item.boundary_id for item in self.implementation_boundaries)
        if observed_boundaries != expected_boundaries:
            raise ValueError("implementation boundary set or order drifted")

        ownership = {
            obligation_id: boundary.boundary_id
            for boundary in self.implementation_boundaries
            for obligation_id in boundary.owns_obligations
        }
        if len(ownership) != 9:
            raise ValueError("implementation boundary ownership must be unique")
        if set(ownership) != {item.obligation_id for item in bounded}:
            raise ValueError("implementation boundaries do not own every successor obligation")
        if any(ownership[item.obligation_id] is not item.successor_boundary for item in bounded):
            raise ValueError("obligation decision disagrees with boundary ownership")
        return self


def _persistence_phases() -> tuple[str, ...]:
    return (
        "transaction_admission",
        "request_attempt_reservation",
        "transport_outcome",
        "telemetry_and_output_admission",
        "state_mutation_decision",
        "trajectory_terminal_state",
        "worker_teardown",
        "scratch_cleanup",
        "evidence_packaging",
        "authorization_terminalization",
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_SOURCE_MISSING",
            "required producer-closure source is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _read_object(root: Path, relative: Path) -> dict[str, object]:
    try:
        value = json.loads(_read_bytes(root, relative).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_SOURCE_JSON_INVALID",
            "producer-closure JSON source is invalid",
            relative,
        ) from error
    if not isinstance(value, dict):
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_SOURCE_SHAPE_INVALID",
            "producer-closure JSON source must contain one object",
            relative,
        )
    return cast(dict[str, object], value)


def _git_source_bytes(root: Path, relative: Path) -> bytes:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "show",
                f"{SOURCE_MAIN_COMMIT}:{relative.as_posix()}",
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_GIT_SOURCE_UNREADABLE",
            "unable to read bound source bytes from accepted main",
            relative,
        ) from error
    if completed.returncode != 0:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_GIT_SOURCE_MISSING",
            "bound source is absent from accepted source main",
            relative,
        )
    return completed.stdout


def _require_source_unchanged(root: Path, relative: Path) -> bytes:
    accepted = _git_source_bytes(root, relative)
    if _read_bytes(root, relative) != accepted:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_ACCEPTED_SOURCE_DRIFT",
            "accepted producer-closure source bytes drifted from source main",
            relative,
        )
    return accepted


def _require_source_head(root: Path, exact: bool) -> None:
    command = ["git", "-C", str(root), "rev-parse", "HEAD"]
    if not exact:
        command = [
            "git",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            SOURCE_MAIN_COMMIT,
            "HEAD",
        ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_GIT_STATE_UNREADABLE",
            "unable to validate G11.3B source Git state",
        ) from error
    if exact and (completed.returncode != 0 or completed.stdout.strip() != SOURCE_MAIN_COMMIT):
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_SOURCE_MAIN_DRIFT",
            "G11.3B materialization must begin from exact merged G11.3A main",
        )
    if not exact and completed.returncode != 0:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_SOURCE_MAIN_MISSING",
            "merged G11.3A source main is not an ancestor of HEAD",
        )


def _source_bindings(root: Path) -> tuple[ArtifactBinding, ...]:
    return tuple(
        ArtifactBinding(
            role=role,
            path=path.as_posix(),
            sha256=_sha256_bytes(_require_source_unchanged(root, path)),
        )
        for role, path in SOURCE_BINDING_SPECS
    )


def _require_markers(root: Path, relative: Path, markers: tuple[str, ...]) -> None:
    text = _read_bytes(root, relative).decode("utf-8")
    missing = tuple(marker for marker in markers if marker not in text)
    if missing:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_SOURCE_MARKER_MISSING",
            f"accepted source marker is missing: {missing[0]}",
            relative,
        )


def _validate_source_contracts(root: Path) -> None:
    for _, path in SOURCE_BINDING_SPECS:
        _require_source_unchanged(root, path)

    g11_3a = _read_object(root, G11_3A_PATH)
    obligations = g11_3a.get("producer_obligations")
    state = g11_3a.get("safety_state")
    if not isinstance(obligations, list) or len(obligations) != 10:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_G11_3A_DRIFT",
            "merged G11.3A must expose exactly ten producer obligations",
            G11_3A_PATH,
        )
    if not isinstance(state, dict) or state.get("manifest_freeze_permitted") is not False:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_G11_3A_AUTHORITY_DRIFT",
            "G11.3A must remain non-freezing",
            G11_3A_PATH,
        )

    g10 = _read_object(root, G10_FREEZE_PATH)
    endpoint = g10.get("primary_runtime_endpoint")
    if g10.get("total_scheduled_trajectory_count") != 342:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_G10_TRAJECTORY_DRIFT",
            "G10 final trajectory count drifted",
            G10_FREEZE_PATH,
        )
    if g10.get("total_scheduled_turn_count") != 1368:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_G10_TURN_DRIFT",
            "G10 final turn count drifted",
            G10_FREEZE_PATH,
        )
    if not isinstance(endpoint, dict) or endpoint.get("metric_id") != (
        "warm-eligible-newly-computed-prefill-tokens-v1"
    ):
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_G10_ENDPOINT_DRIFT",
            "G10 primary runtime endpoint drifted",
            G10_FREEZE_PATH,
        )

    architecture = _read_object(root, G11_ARCHITECTURE_PATH)
    north_star = architecture.get("north_star")
    channels = architecture.get("evidence_channels")
    if not isinstance(north_star, dict) or north_star.get("maximum_request_attempts") != 2736:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_ATTEMPT_CEILING_DRIFT",
            "G11.0 final attempt ceiling drifted",
            G11_ARCHITECTURE_PATH,
        )
    if (
        not isinstance(channels, dict)
        or channels.get("protected_measured_review_export_required") is not True
    ):
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_PROTECTED_REVIEW_DRIFT",
            "G11.0 protected measured-review requirement drifted",
            G11_ARCHITECTURE_PATH,
        )

    _require_markers(
        root,
        FINAL_CORE_PATH,
        (
            "class RuntimeTraceIdentity",
            "class RetryAttemptEvidence",
            "class ProtectedReviewPublicReceipt",
            "class FailureState",
            "EXPECTED_MAXIMUM_REQUEST_ATTEMPTS = 2736",
        ),
    )
    _require_markers(root, V2_REQUEST_ADAPTER_PATH, ("with no retry path",))
    _require_markers(
        root,
        P5_P6_RUNTIME_PATH,
        (
            'EXPECTED_VLLM_DISTRIBUTION_VERSION = "0.25.1+cu129"',
            'EXPECTED_BACKEND = "TRITON_ATTN"',
            "class Worker:",
        ),
    )
    _require_markers(
        root,
        CONSTITUTION_PATH,
        (
            "pricing schedule when cost is reported",
            "Every completed benchmark execution produces a typed evidence bundle.",
            "Protected blinded-review exports:",
        ),
    )

    fingerprints = _read_object(root, PREFLIGHT_FINGERPRINTS_PATH)
    if fingerprints.get("pricing_fields_present") is not False:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_PRICING_SCOPE_DRIFT",
            "preflight-v3 unexpectedly contains active pricing fields",
            PREFLIGHT_FINGERPRINTS_PATH,
        )
    if fingerprints.get("provider_fields_present") is not False:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_PROVIDER_SCOPE_DRIFT",
            "preflight-v3 unexpectedly contains active provider fields",
            PREFLIGHT_FINGERPRINTS_PATH,
        )


def _obligation_decisions() -> tuple[ObligationDecision, ...]:
    specs = (
        (
            OBLIGATION_IDS[0],
            BoundaryId.EXECUTION_PRODUCER,
            (P5_P6_RUNTIME_PATH, V2_REQUEST_ADAPTER_PATH, FINAL_CORE_PATH),
            "Accepted worker and transport mechanics are reusable, but V2 has no retry path "
            "and final authority requires the G11.1 retry contract and 2,736-attempt ceiling.",
        ),
        (
            OBLIGATION_IDS[1],
            BoundaryId.EXECUTION_PRODUCER,
            (FINAL_CORE_PATH,),
            "G11.1 defines the planning-to-final manifest trace contract, but no live final "
            "producer persists the frozen final-manifest SHA on every trace.",
        ),
        (
            OBLIGATION_IDS[2],
            BoundaryId.EXECUTION_PRODUCER,
            (V2_RUNTIME_PATH, P5_P6_RUNTIME_PATH),
            "V2 and P5/P6 prove bundle mechanics, but their schemas do not represent the final "
            "342-run evidence subject.",
        ),
        (
            OBLIGATION_IDS[3],
            BoundaryId.EXECUTION_PRODUCER,
            (V2_RUNTIME_PATH, FINAL_CORE_PATH),
            "V2 proves reconciliation and G11.1 defines final retry and counter semantics; the "
            "final producer must persist retry-aware attempt and state transitions.",
        ),
        (
            OBLIGATION_IDS[4],
            BoundaryId.PROTECTED_REVIEW,
            (G11_ARCHITECTURE_PATH, G10_FREEZE_PATH, FINAL_CORE_PATH),
            "The protected root, opaque IDs, review fractions, blindness rules, and safe receipt "
            "exist, but no measured protected-export writer exists.",
        ),
        (
            OBLIGATION_IDS[5],
            BoundaryId.EXECUTION_PRODUCER,
            (FINAL_CORE_PATH, P5_P6_RUNTIME_PATH),
            "G11.1 defines first-causal and secondary failure semantics and P5/P6 proves the "
            "masking risk, but final durable monotonic failure persistence is still required.",
        ),
        (
            OBLIGATION_IDS[6],
            BoundaryId.EXECUTION_PRODUCER,
            (P5_P6_RUNTIME_PATH, V2_RUNTIME_PATH),
            "Accepted runtimes prove teardown and cleanup mechanics, but final identities and "
            "terminal evidence need a thin successor rather than historical runtime copying.",
        ),
        (
            OBLIGATION_IDS[7],
            BoundaryId.EXECUTION_PRODUCER,
            (PREFLIGHT_FINGERPRINTS_PATH, G11_ARCHITECTURE_PATH, P5_P6_RUNTIME_PATH, G11_3A_PATH),
            "Preflight-v3 removes active hosted-provider authority and binds the local model "
            "alias, but the final producer must own the complete legacy-field compatibility map.",
        ),
        (
            OBLIGATION_IDS[9],
            BoundaryId.ANALYSIS_CONTRACTS,
            (G10_FREEZE_PATH, CONSTITUTION_PATH, FINAL_CORE_PATH),
            "G10 freezes eligibility, quality, warm/cold, paired statistics, and claim order, "
            "but exact final typed analysis inputs do not yet exist.",
        ),
    )
    bounded = {
        obligation_id: ObligationDecision(
            obligation_id=obligation_id,
            disposition=ClosureDisposition.BOUNDED_SUCCESSOR_REQUIRED,
            successor_boundary=boundary,
            reuse_sources=tuple(path.as_posix() for path in sources),
            rationale=rationale,
        )
        for obligation_id, boundary, sources, rationale in specs
    }
    cost = ObligationDecision(
        obligation_id=OBLIGATION_IDS[8],
        disposition=ClosureDisposition.EXPLICITLY_OUT_OF_SCOPE,
        successor_boundary=None,
        reuse_sources=(
            CONSTITUTION_PATH.as_posix(),
            PREFLIGHT_FINGERPRINTS_PATH.as_posix(),
            G11_3A_PATH.as_posix(),
        ),
        rationale=(
            "The Constitution requires pricing only when monetary cost is reported, external "
            "spend remains zero, and no accepted local-Qwen monetary pricing schedule exists."
        ),
    )
    return tuple(
        cost if obligation_id == OBLIGATION_IDS[8] else bounded[obligation_id]
        for obligation_id in OBLIGATION_IDS
    )


def _implementation_boundaries() -> tuple[ImplementationBoundary, ...]:
    return (
        ImplementationBoundary(
            boundary_id=BoundaryId.EXECUTION_PRODUCER,
            owns_obligations=(
                OBLIGATION_IDS[0],
                OBLIGATION_IDS[1],
                OBLIGATION_IDS[2],
                OBLIGATION_IDS[3],
                OBLIGATION_IDS[5],
                OBLIGATION_IDS[6],
                OBLIGATION_IDS[7],
            ),
            purpose=(
                "Compose accepted exact-runtime mechanics with G11.1 final control semantics and "
                "persist all public claim-critical execution evidence."
            ),
            constraints=(
                "do_not_rewrite_historical_executed_runtime",
                "do_not_copy_v2_no_retry_semantics",
                "consume_frozen_342_ledger_order_exactly",
                "persist_final_manifest_sha_on_every_trace",
                "enforce_2736_attempt_ceiling",
                "no_synthetic_prewarm_or_worker_qualification_requests",
            ),
        ),
        ImplementationBoundary(
            boundary_id=BoundaryId.PROTECTED_REVIEW,
            owns_obligations=(OBLIGATION_IDS[4],),
            purpose=(
                "Create isolated measured review material and expose only safe digest or metadata "
                "bindings to public evidence."
            ),
            constraints=(
                "git_ignored_local_root_only",
                "opaque_review_ids_only",
                "reviewers_blinded_to_condition_route_cost_latency_cache",
                "100_percent_primary_review",
                "25_percent_independent_double_review_seed_20260712",
                "retention_and_deletion_rule_bound_before_manifest_freeze",
            ),
        ),
        ImplementationBoundary(
            boundary_id=BoundaryId.ANALYSIS_CONTRACTS,
            owns_obligations=(OBLIGATION_IDS[9],),
            purpose=(
                "Define typed post-run inputs for eligibility, quality, paired analysis, "
                "denominator accounting, and claim classification before measured execution."
            ),
            constraints=(
                "no_post_run_log_reconstruction",
                "support_functional_and_runtime_four_turn_trajectories",
                "preserve_failure_accounted_denominators",
                "preserve_B_minus_A_C_minus_B_C_minus_A_orientation",
                "quality_gate_precedes_runtime_improvement_claim",
            ),
        ),
    )


def build_record(root: Path) -> ProducerClosureRecord:
    _validate_source_contracts(root)
    return ProducerClosureRecord(
        closure_id="auragateway-final-342-execution-producer-closure-v1",
        source_main_commit=SOURCE_MAIN_COMMIT,
        source_bindings=_source_bindings(root),
        obligation_decisions=_obligation_decisions(),
        implementation_boundaries=_implementation_boundaries(),
        cost_scope=CostScopeDecision(
            rationale=(
                "No accepted local-runtime monetary pricing schedule exists. Zero external spend "
                "remains binding while mechanism, latency, quality, and failure reporting remain "
                "in scope."
            )
        ),
        persistence_contract=PersistenceContract(phases=_persistence_phases()),
        forest_constraint=ForestConstraint(),
        safety_state=SafetyState(),
        next_gate=NEXT_GATE,
    )


def _canonical_bytes(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.g11-3b.tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    temporary.replace(path)


def write_record(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_source_head(root, exact=True)
    _write_bytes_atomic(root / RECORD_PATH, _canonical_bytes(build_record(root)))
    return validate_repository(root)


def validate_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_source_head(root, exact=False)
    expected = build_record(root)
    try:
        observed = ProducerClosureRecord.model_validate_json(_read_bytes(root, RECORD_PATH))
    except ValidationError as error:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_RECORD_INVALID",
            "producer-closure record failed typed validation",
            RECORD_PATH,
        ) from error
    if observed != expected:
        raise ProducerClosureError(
            "FINAL_342_PRODUCER_CLOSURE_RECORD_DRIFT",
            "producer-closure record differs from deterministic reconstruction",
            RECORD_PATH,
        )
    for path, marker in (
        (ADR_PATH, "FINAL_342_EXECUTION_PRODUCER_CLOSURE_V1"),
        (REPORT_PATH, NEXT_GATE),
    ):
        if marker not in _read_bytes(root, path).decode("utf-8"):
            raise ProducerClosureError(
                "FINAL_342_PRODUCER_CLOSURE_DOCUMENT_MARKER_MISSING",
                "required G11.3B document marker is missing",
                path,
            )

    bounded_count = sum(
        item.disposition is ClosureDisposition.BOUNDED_SUCCESSOR_REQUIRED
        for item in observed.obligation_decisions
    )
    excluded_count = sum(
        item.disposition is ClosureDisposition.EXPLICITLY_OUT_OF_SCOPE
        for item in observed.obligation_decisions
    )
    return {
        "status": "FINAL_342_EXECUTION_PRODUCER_CLOSURE_V1_VALID",
        "producer_obligation_count": len(observed.obligation_decisions),
        "bounded_successor_obligation_count": bounded_count,
        "out_of_scope_obligation_count": excluded_count,
        "implementation_boundary_count": len(observed.implementation_boundaries),
        "monetary_cost_comparison_in_scope": False,
        "external_spend_ceiling": 0,
        "producer_obligation_classification_complete": True,
        "final_producer_implementation_complete": False,
        "manifest_freeze_permitted": False,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _Parser:
    parser = _Parser()
    parser.add_argument("command", choices=("materialize", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = Path(cast(str, args.repo_root))
    try:
        result = write_record(root) if args.command == "materialize" else validate_repository(root)
    except (ProducerClosureError, OSError, UnicodeDecodeError, ValueError) as error:
        if isinstance(error, ProducerClosureError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path.as_posix() if error.path is not None else None,
            }
        else:
            payload = {
                "error_code": "FINAL_342_PRODUCER_CLOSURE_FAILED",
                "safe_message": str(error),
                "path": None,
            }
        print(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
