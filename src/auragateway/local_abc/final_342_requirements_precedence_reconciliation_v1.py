"""Reconcile final-342 manifest requirements and authority precedence before producer closure."""

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

SOURCE_MAIN_COMMIT = "ac187cf08643b53786f0c8c5e39d6be67ba61beb"
NEXT_GATE = "G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1"

CONSTITUTION_PATH = Path("docs/benchmark/AuraGateway_Benchmark_Constitution.md")
REQUIREMENTS_PATH = Path("docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md")
G10_FREEZE_PATH = Path(
    "data/evals/benchmark/freeze-v2/measured_abc_repetition_statistical_freeze_v1.json"
)
G11_ARCHITECTURE_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_runtime_requalification_architecture_v1.json"
)
PREFLIGHT_DRAFT_PATH = Path("data/evals/benchmark/preflight-v3/execution_manifest_draft.json")
HISTORICAL_FREEZE_PATH = Path("data/evals/benchmark/freeze-v1/execution_manifest.json")
TRANSACTION_ADR_PATH = Path(
    "docs/adr/2026-08-11-local-abc-transaction-bound-execution-authorization-architecture-v1.md"
)
RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_requirements_precedence_reconciliation_v1.json"
)
ADR_PATH = Path(
    "docs/adr/2026-08-29-local-abc-final-342-requirements-precedence-reconciliation-v1.md"
)
REPORT_PATH = Path(
    "docs/reports/AuraGateway_Final_342_Requirements_Precedence_Reconciliation_V1.md"
)

EXPECTED_CONSTITUTION_SHA256 = "c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1"
EXPECTED_REQUIREMENTS_SHA256 = "30799246e6fa8d91246a5277e613ed97f840a164331f1f04a3f17fd84aad20cf"
EXPECTED_G10_SHA256 = "4c4345e57e7aae7453616bc90e405d6aa7aef9d2673e20bc060c99579a863b18"
EXPECTED_G11_ARCHITECTURE_SHA256 = (
    "5c4896623978c4df4059370a48b995ae8526a26d912f92f439b91564e76d7232"
)
EXPECTED_PREFLIGHT_DRAFT_SHA256 = "b3102131c94be119ec1b1f6853df15535adb55ece599d6dd52e75e3444bdbce2"
EXPECTED_HISTORICAL_FREEZE_SHA256 = (
    "b63a464591b6f172fef779fd5e0fdf71fa094e22a5476fe3d1687bc7b8176a97"
)

REQUIRED_FIELD_FAMILIES: dict[str, tuple[str, ...]] = {
    "identity": (
        "execution_manifest_version",
        "execution_manifest_hash",
        "benchmark_constitution_version",
        "benchmark_constitution_hash",
        "benchmark_runner_version",
        "comparison_eligibility_contract_version",
        "evidence_bundle_schema_version",
        "git_commit_hash",
        "python_version",
        "dependency_lock_hash",
    ),
    "corpus_retrieval": (
        "corpus_manifest_hash",
        "chunking_strategy_id",
        "chunking_configuration_hash",
        "retrieval_implementation_id",
        "retrieval_configuration_hash",
        "retrieval_type",
        "top_k",
        "metadata_filter_policy_version",
        "development_retrieval_manifest_hash",
        "held_out_retrieval_manifest_hash",
        "retrieval_scorecard_hash",
    ),
    "context_contract": (
        "prompt_template_id",
        "prompt_template_version",
        "static_context_pack_id",
        "static_context_pack_version",
        "serialization_version",
        "tool_contract_version",
        "output_schema_version",
        "prefix_fingerprint_contract_version",
    ),
    "provider_telemetry": (
        "primary_provider",
        "provider_model_alias",
        "exact_model_identifier",
        "provider_adapter_version",
        "provider_documentation_date_checked",
        "telemetry_rules_version",
        "telemetry_fixture_manifest_hash",
        "cache_ttl_assumption_seconds",
        "cache_ttl_source",
        "pricing_schedule_version",
        "pricing_source_date",
        "currency",
    ),
    "route_policy": (
        "route_policy_version",
        "economy_model_alias",
        "capable_model_alias",
        "capability_calibration_report_hash",
        "route_ttl_policy_version",
        "provider_failure_policy_version",
    ),
    "evaluation_adjudication": (
        "diagnostic_episode_manifest_hash",
        "functional_benchmark_manifest_hash",
        "runtime_microbenchmark_manifest_hash",
        "quality_rubric_version",
        "quality_rubric_hash",
        "blinded_adjudication_protocol_version",
        "review_sample_schedule_hash",
        "feedback_evidence_contract_version",
    ),
    "fault_privacy": (
        "negative_control_manifest_hash",
        "fault_injection_fixture_hash",
        "privacy_trace_contract_version",
        "privacy_verification_report_hash",
        "cross_condition_isolation_test_hash",
    ),
    "frozen_controls": (
        "functional_run_order_schedule_id",
        "runtime_run_order_schedule_id",
        "timeout_policy_id",
        "retry_policy_id",
        "exclusion_policy_id",
        "rerun_policy_id",
        "denominator_policy_id",
        "statistical_reporting_configuration_id",
        "quality_non_inferiority_policy_id",
    ),
}


class ReconciliationError(RuntimeError):
    """Fail-closed requirements reconciliation error."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError("FINAL_342_RECONCILIATION_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Disposition(StrEnum):
    FINAL_MANIFEST_REQUIRED = "FINAL_MANIFEST_REQUIRED"
    EXISTING_UPSTREAM_BINDING_REQUIRED = "EXISTING_UPSTREAM_BINDING_REQUIRED"
    G11_3B_PRODUCER_CLOSURE_REQUIRED = "G11_3B_PRODUCER_CLOSURE_REQUIRED"
    G11_3B_COST_SCOPE_DECISION_REQUIRED = "G11_3B_COST_SCOPE_DECISION_REQUIRED"
    POST_COMMIT_CUSTODY_RECEIPT_REQUIRED = "POST_COMMIT_CUSTODY_RECEIPT_REQUIRED"
    SUPERSEDED_BY_ACCEPTED_SEQUENCE = "SUPERSEDED_BY_ACCEPTED_SEQUENCE"
    FRESH_PLATFORM_OBSERVATION_AFTER_ISSUANCE = "FRESH_PLATFORM_OBSERVATION_AFTER_ISSUANCE"


class ArtifactBinding(FrozenModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PrecedenceRule(FrozenModel):
    rank: int = Field(ge=1, le=10)
    authority: str = Field(min_length=1)
    rule: str = Field(min_length=20)


class RequirementGroup(FrozenModel):
    group_id: str = Field(min_length=1)
    source_section: str = Field(min_length=1)
    members: tuple[str, ...] = Field(min_length=1)
    disposition: Disposition
    owner: str = Field(min_length=1)
    blocking_before_manifest_freeze: bool
    rationale: str = Field(min_length=20)


class FreezeProcedureGroup(FrozenModel):
    group_id: str = Field(min_length=1)
    steps: tuple[int, ...] = Field(min_length=1)
    disposition: Disposition
    blocking_before_manifest_freeze: bool
    rationale: str = Field(min_length=20)


class ProducerObligation(FrozenModel):
    obligation_id: str = Field(min_length=1)
    required_before_manifest_freeze: Literal[True] = True
    rationale: str = Field(min_length=20)


class CommitBindingResolution(FrozenModel):
    historical_same_commit_self_reference_rejected: Literal[True] = True
    source_subject_commit_role: Literal[
        "predecessor_repository_state_from_which_manifest_bytes_are_materialized"
    ]
    first_containing_commit_role: Literal[
        "first_git_commit_whose_tree_contains_the_exact_manifest_bytes"
    ]
    first_containing_commit_stored_inside_same_manifest: Literal[False] = False
    post_commit_custody_receipt_required: Literal[True] = True
    receipt_binds_manifest_sha256: Literal[True] = True
    receipt_binds_manifest_file_sha256: Literal[True] = True
    receipt_binds_source_subject_commit: Literal[True] = True
    receipt_binds_first_containing_commit: Literal[True] = True
    g11_freeze_gate_promoted_before_receipt: Literal[False] = False


class SafetyState(FrozenModel):
    requirements_inventory_complete: Literal[True] = True
    requirements_precedence_established: Literal[True] = True
    producer_closure_required: Literal[True] = True
    manifest_freeze_permitted: Literal[False] = False
    execution_manifest_frozen: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    gpu_execution_performed: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False


class ReconciliationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reconciliation_id: Literal[
        "auragateway-final-342-requirements-precedence-reconciliation-v1"
    ]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_bindings: tuple[ArtifactBinding, ...]
    precedence: tuple[PrecedenceRule, ...]
    requirement_groups: tuple[RequirementGroup, ...]
    freeze_procedure_groups: tuple[FreezeProcedureGroup, ...]
    producer_obligations: tuple[ProducerObligation, ...]
    commit_binding: CommitBindingResolution
    safety_state: SafetyState
    next_gate: Literal["G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1"]

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        expected_fields = {
            field
            for members in REQUIRED_FIELD_FAMILIES.values()
            for field in members
        }
        observed_fields = [
            field for group in self.requirement_groups for field in group.members
        ]
        if len(observed_fields) != len(set(observed_fields)):
            raise ValueError("requirements reconciliation contains duplicate fields")
        if set(observed_fields) != expected_fields:
            raise ValueError("requirements reconciliation field coverage drifted")
        if len(observed_fields) != 69:
            raise ValueError("requirements reconciliation must cover exactly 69 fields")

        steps = [step for group in self.freeze_procedure_groups for step in group.steps]
        if len(steps) != len(set(steps)) or set(steps) != set(range(1, 14)):
            raise ValueError("freeze procedure reconciliation must cover steps 1 through 13")

        ranks = [item.rank for item in self.precedence]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("precedence ranks must be contiguous")

        blocker_groups = {
            group.group_id
            for group in self.requirement_groups
            if group.blocking_before_manifest_freeze
        }
        expected_blockers = {
            "identity.producer",
            "provider_telemetry.local_runtime_mapping",
            "provider_telemetry.pricing_scope",
            "route_policy.local_runtime_mapping",
        }
        if blocker_groups != expected_blockers:
            raise ValueError("pre-freeze blocker group set drifted")

        if len(self.producer_obligations) != 10:
            raise ValueError("G11.3B must close exactly ten producer obligations")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_SOURCE_MISSING",
            "required reconciliation source is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _require_sha(root: Path, relative: Path, expected: str) -> None:
    observed = _sha256_bytes(_read_bytes(root, relative))
    if observed != expected:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_SOURCE_IDENTITY_DRIFT",
            "requirements reconciliation source identity drifted",
            relative,
        )


def _read_object(root: Path, relative: Path) -> dict[str, object]:
    try:
        value = json.loads(_read_bytes(root, relative))
    except json.JSONDecodeError as error:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_SOURCE_JSON_INVALID",
            "requirements reconciliation source is invalid JSON",
            relative,
        ) from error
    if not isinstance(value, dict):
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_SOURCE_SHAPE_INVALID",
            "requirements reconciliation source must contain one JSON object",
            relative,
        )
    return cast(dict[str, object], value)


def _require_source_head(root: Path, exact: bool) -> None:
    if exact:
        command = ["git", "-C", str(root), "rev-parse", "HEAD"]
    else:
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
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_GIT_STATE_UNREADABLE",
            "unable to validate reconciliation source Git state",
        ) from error

    if exact and (
        completed.returncode != 0 or completed.stdout.strip() != SOURCE_MAIN_COMMIT
    ):
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_SOURCE_MAIN_DRIFT",
            "reconciliation materialization must start from exact merged G11.2 main",
        )
    if not exact and completed.returncode != 0:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_SOURCE_MAIN_MISSING",
            "merged G11.2 source main is not an ancestor of HEAD",
        )


def _validate_source_contracts(root: Path) -> None:
    _require_sha(root, CONSTITUTION_PATH, EXPECTED_CONSTITUTION_SHA256)
    _require_sha(root, REQUIREMENTS_PATH, EXPECTED_REQUIREMENTS_SHA256)
    _require_sha(root, G10_FREEZE_PATH, EXPECTED_G10_SHA256)
    _require_sha(root, G11_ARCHITECTURE_PATH, EXPECTED_G11_ARCHITECTURE_SHA256)
    _require_sha(root, PREFLIGHT_DRAFT_PATH, EXPECTED_PREFLIGHT_DRAFT_SHA256)
    _require_sha(root, HISTORICAL_FREEZE_PATH, EXPECTED_HISTORICAL_FREEZE_SHA256)

    architecture = _read_object(root, G11_ARCHITECTURE_PATH)
    sequence = architecture.get("implementation_sequence")
    expected_sequence = [
        "IMPLEMENT_FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1",
        "REHEARSE_FINAL_342_TRANSACTION_WRAPPER_V1",
        "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1",
        "BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1",
        "QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1",
        "FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY",
        "ONE_GOVERNED_FINAL_342_EXECUTION",
    ]
    if sequence != expected_sequence:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_G11_SEQUENCE_DRIFT",
            "accepted G11.0 sequence drifted",
            G11_ARCHITECTURE_PATH,
        )

    g10 = _read_object(root, G10_FREEZE_PATH)
    for field in (
        "repetition_freeze_established",
        "statistical_freeze_established",
        "primary_runtime_endpoint_frozen",
        "quality_contract_frozen",
        "warm_reset_policy_frozen",
    ):
        if g10.get(field) is not True:
            raise ReconciliationError(
                "FINAL_342_RECONCILIATION_G10_DRIFT",
                f"required G10 freeze field drifted: {field}",
                G10_FREEZE_PATH,
            )

    preflight = _read_object(root, PREFLIGHT_DRAFT_PATH)
    preflight_identity = preflight.get("identity")
    if not isinstance(preflight_identity, dict):
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_PREFLIGHT_IDENTITY_MISSING",
            "preflight-v3 planning identity is missing",
            PREFLIGHT_DRAFT_PATH,
        )
    expected_preflight_identity = {
        "execution_manifest_frozen": False,
        "execution_enabled": False,
        "execution_manifest_status": "planning_draft",
    }
    if any(
        preflight_identity.get(field) != expected
        for field, expected in expected_preflight_identity.items()
    ):
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_PREFLIGHT_STATE_DRIFT",
            "preflight-v3 identity must remain a non-frozen planning lineage",
            PREFLIGHT_DRAFT_PATH,
        )
    expected_preflight_safety = {
        "measured_execution_authorized": False,
        "gpu_execution_authorized": False,
        "provider_execution_authorized": False,
        "claim_generation_permitted": False,
    }
    if any(
        preflight.get(field) != expected
        for field, expected in expected_preflight_safety.items()
    ):
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_PREFLIGHT_AUTHORITY_DRIFT",
            "preflight-v3 planning lineage unexpectedly permits execution or claims",
            PREFLIGHT_DRAFT_PATH,
        )
    runtime_direction = preflight.get("runtime_direction")
    if not isinstance(runtime_direction, dict):
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_RUNTIME_DIRECTION_MISSING",
            "preflight-v3 runtime direction is missing",
            PREFLIGHT_DRAFT_PATH,
        )
    if runtime_direction.get("execution_backend") != "local_vllm":
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_RUNTIME_DIRECTION_DRIFT",
            "preflight-v3 runtime backend drifted",
            PREFLIGHT_DRAFT_PATH,
        )
    if runtime_direction.get("hosted_provider_required") is not False:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_PROVIDER_DIRECTION_DRIFT",
            "preflight-v3 unexpectedly requires a hosted provider",
            PREFLIGHT_DRAFT_PATH,
        )

    historical = _read_object(root, HISTORICAL_FREEZE_PATH)
    identity = historical.get("identity")
    if not isinstance(identity, dict) or identity.get("execution_enabled") is not False:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_HISTORICAL_FREEZE_DRIFT",
            "historical freeze-v1 identity drifted",
            HISTORICAL_FREEZE_PATH,
        )

    transaction_adr = _read_bytes(root, TRANSACTION_ADR_PATH).decode("utf-8")
    if "TRANSACTION_BOUND_EXECUTION_ARTIFACT" not in transaction_adr:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_TRANSACTION_ARCHITECTURE_DRIFT",
            "transaction-bound successor architecture marker is missing",
            TRANSACTION_ADR_PATH,
        )
    if "Platform observation is an execution-admission/acceptance condition" not in transaction_adr:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_PLATFORM_SEQUENCE_DRIFT",
            "transaction-bound platform-observation sequencing marker is missing",
            TRANSACTION_ADR_PATH,
        )


def _bindings(root: Path) -> tuple[ArtifactBinding, ...]:
    sources = (
        ("benchmark_constitution", CONSTITUTION_PATH),
        ("execution_manifest_requirements", REQUIREMENTS_PATH),
        ("g10_repetition_statistical_freeze", G10_FREEZE_PATH),
        ("g11_runtime_requalification_architecture", G11_ARCHITECTURE_PATH),
        ("preflight_v3_execution_manifest_draft", PREFLIGHT_DRAFT_PATH),
        ("historical_freeze_v1_lineage", HISTORICAL_FREEZE_PATH),
        ("transaction_bound_authorization_architecture", TRANSACTION_ADR_PATH),
    )
    return tuple(
        ArtifactBinding(
            role=role,
            path=path.as_posix(),
            sha256=_sha256_bytes(_read_bytes(root, path)),
        )
        for role, path in sources
    )


def _precedence() -> tuple[PrecedenceRule, ...]:
    return (
        PrecedenceRule(
            rank=1,
            authority="Benchmark Constitution 1.0.0",
            rule=(
                "The frozen scientific rules remain highest authority for conditions, contrasts, "
                "eligibility, retry/exclusion/rerun/denominator rules, quality, statistics, "
                "privacy, and claims."
            ),
        ),
        PrecedenceRule(
            rank=2,
            authority="G10 repetition/statistical freeze v1",
            rule=(
                "G10 owns the final 342-run repetition plan, primary runtime endpoint, "
                "statistical contract, "
                "quality non-inferiority contract, and warm/reset analysis policy."
            ),
        ),
        PrecedenceRule(
            rank=3,
            authority="G11.0 final-342 runtime requalification architecture v1",
            rule=(
                "G11.0 owns the current final-run local-vLLM runtime topology and successor "
                "sequencing where "
                "older generic manifest procedure language conflicts with the accepted final "
                "architecture."
            ),
        ),
        PrecedenceRule(
            rank=4,
            authority="Execution Manifest Requirements 1.1.0",
            rule=(
                "The requirements document remains the baseline field inventory and freeze "
                "intent except where "
                "this reconciliation explicitly specializes a field or procedure under "
                "higher-ranked authority."
            ),
        ),
        PrecedenceRule(
            rank=5,
            authority="Preflight-v3 planning lineage",
            rule=(
                "Preflight-v3 supplies current local planning identities and accepted asset "
                "hashes but is not itself "
                "the final execution manifest, live runtime authority, or final comparison "
                "authority."
            ),
        ),
        PrecedenceRule(
            rank=6,
            authority="Historical freeze-v1",
            rule=(
                "Historical freeze-v1 is immutable lineage evidence only; it may support "
                "explicitly retained values "
                "such as the benchmark TTL source but cannot template the current local-vLLM "
                "final manifest."
            ),
        ),
        PrecedenceRule(
            rank=7,
            authority="Unmerged candidate state",
            rule=(
                "Any unmerged final-manifest candidate is review evidence only and cannot "
                "establish repository state, "
                "execution-manifest freeze, live authority, or effect claims."
            ),
        ),
    )


def _requirement_groups() -> tuple[RequirementGroup, ...]:
    return (
        RequirementGroup(
            group_id="identity.core",
            source_section="Required identity fields",
            members=(
                "execution_manifest_version",
                "execution_manifest_hash",
                "benchmark_constitution_version",
                "benchmark_constitution_hash",
                "comparison_eligibility_contract_version",
            ),
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            owner="final execution manifest",
            blocking_before_manifest_freeze=False,
            rationale=(
                "These values are intrinsic final-manifest identity and scientific-eligibility "
                "bindings and must be "
                "present directly in the final frozen subject."
            ),
        ),
        RequirementGroup(
            group_id="identity.producer",
            source_section="Required identity fields",
            members=(
                "benchmark_runner_version",
                "evidence_bundle_schema_version",
                "python_version",
                "dependency_lock_hash",
            ),
            disposition=Disposition.G11_3B_PRODUCER_CLOSURE_REQUIRED,
            owner=NEXT_GATE,
            blocking_before_manifest_freeze=True,
            rationale=(
                "These identities cannot be frozen defensibly until the exact final "
                "evidence-producing executable "
                "graph and runtime environment ownership are closed."
            ),
        ),
        RequirementGroup(
            group_id="identity.git_custody",
            source_section="Required identity fields",
            members=("git_commit_hash",),
            disposition=Disposition.POST_COMMIT_CUSTODY_RECEIPT_REQUIRED,
            owner="G11 post-manifest freeze custody receipt",
            blocking_before_manifest_freeze=False,
            rationale=(
                "A manifest cannot safely embed the SHA of the same Git commit whose tree "
                "contains that manifest; "
                "the containing commit is therefore bound by a separate acyclic post-commit "
                "custody receipt."
            ),
        ),
        RequirementGroup(
            group_id="corpus_retrieval.existing_assets",
            source_section="Corpus and retrieval fields",
            members=REQUIRED_FIELD_FAMILIES["corpus_retrieval"],
            disposition=Disposition.EXISTING_UPSTREAM_BINDING_REQUIRED,
            owner="preflight-v3 frozen asset bindings and final manifest",
            blocking_before_manifest_freeze=False,
            rationale=(
                "Current planning lineage already identifies the accepted corpus and retrieval "
                "assets; the final "
                "manifest must carry or exactly bind those identities without regenerating "
                "experiment content."
            ),
        ),
        RequirementGroup(
            group_id="context_contract.existing_assets",
            source_section="Context and contract fields",
            members=REQUIRED_FIELD_FAMILIES["context_contract"],
            disposition=Disposition.EXISTING_UPSTREAM_BINDING_REQUIRED,
            owner="preflight-v3 context bindings and final manifest",
            blocking_before_manifest_freeze=False,
            rationale=(
                "Accepted prompt, static-context, serialization, tool, output-schema, and "
                "prefix-contract lineage must "
                "remain exactly bound in the final execution subject."
            ),
        ),
        RequirementGroup(
            group_id="provider_telemetry.local_runtime_mapping",
            source_section="Provider and telemetry fields",
            members=(
                "primary_provider",
                "provider_model_alias",
                "exact_model_identifier",
                "provider_adapter_version",
                "provider_documentation_date_checked",
                "telemetry_rules_version",
                "telemetry_fixture_manifest_hash",
            ),
            disposition=Disposition.G11_3B_PRODUCER_CLOSURE_REQUIRED,
            owner=NEXT_GATE,
            blocking_before_manifest_freeze=True,
            rationale=(
                "The historical field names are provider-oriented while the accepted current "
                "runtime is local vLLM; "
                "G11.3B must bind the exact local request transport, telemetry semantics, and "
                "compatibility mapping."
            ),
        ),
        RequirementGroup(
            group_id="provider_telemetry.cache_ttl",
            source_section="Provider and telemetry fields",
            members=("cache_ttl_assumption_seconds", "cache_ttl_source"),
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            owner="G11.0 warm eligibility and final manifest",
            blocking_before_manifest_freeze=False,
            rationale=(
                "The 300-second benchmark-assumption-v1 warm-eligibility window is already "
                "accepted and must remain "
                "explicitly distinguished from a vLLM cache-residency guarantee."
            ),
        ),
        RequirementGroup(
            group_id="provider_telemetry.pricing_scope",
            source_section="Provider and telemetry fields",
            members=("pricing_schedule_version", "pricing_source_date", "currency"),
            disposition=Disposition.G11_3B_COST_SCOPE_DECISION_REQUIRED,
            owner=NEXT_GATE,
            blocking_before_manifest_freeze=True,
            rationale=(
                "The current local runtime has zero external spend, but the benchmark "
                "constitution allows versioned "
                "estimated cost reporting; G11.3B must either bind a valid pricing model or "
                "explicitly exclude monetary cost claims."
            ),
        ),
        RequirementGroup(
            group_id="route_policy.local_runtime_mapping",
            source_section="Route-policy fields",
            members=REQUIRED_FIELD_FAMILIES["route_policy"],
            disposition=Disposition.G11_3B_PRODUCER_CLOSURE_REQUIRED,
            owner=NEXT_GATE,
            blocking_before_manifest_freeze=True,
            rationale=(
                "Historical economy/capable provider aliases no longer describe the final local "
                "worker-routing topology; "
                "the exact route-policy compatibility mapping must be owned by the final "
                "producer closure."
            ),
        ),
        RequirementGroup(
            group_id="evaluation_adjudication.existing_assets",
            source_section="Evaluation and adjudication fields",
            members=REQUIRED_FIELD_FAMILIES["evaluation_adjudication"],
            disposition=Disposition.EXISTING_UPSTREAM_BINDING_REQUIRED,
            owner="accepted evaluation assets, G10 quality freeze, and final manifest",
            blocking_before_manifest_freeze=False,
            rationale=(
                "Diagnostic, functional, runtime, rubric, blinded-review, review-sample, and "
                "feedback identities already "
                "exist and must be preserved while G11.3B closes the measured protected-review "
                "producer lifecycle."
            ),
        ),
        RequirementGroup(
            group_id="fault_privacy.existing_assets",
            source_section="Fault and privacy fields",
            members=REQUIRED_FIELD_FAMILIES["fault_privacy"],
            disposition=Disposition.EXISTING_UPSTREAM_BINDING_REQUIRED,
            owner="accepted fault/privacy assets and final manifest",
            blocking_before_manifest_freeze=False,
            rationale=(
                "Negative controls, fault fixtures, privacy contracts, verification, and "
                "isolation evidence must stay "
                "hash-bound and must not be replaced by post-result interpretation."
            ),
        ),
        RequirementGroup(
            group_id="frozen_controls.constitution_g10",
            source_section="Frozen execution controls",
            members=REQUIRED_FIELD_FAMILIES["frozen_controls"],
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            owner="Benchmark Constitution plus G10 freeze",
            blocking_before_manifest_freeze=False,
            rationale=(
                "Run order, timeout, retry, exclusion, rerun, denominator, statistics, and "
                "quality controls are already "
                "scientifically frozen and must be repeated or exactly bound in the final manifest."
            ),
        ),
    )


def _freeze_procedure_groups() -> tuple[FreezeProcedureGroup, ...]:
    return (
        FreezeProcedureGroup(
            group_id="procedure.static_validation",
            steps=(1, 2, 3, 4, 5, 6),
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            blocking_before_manifest_freeze=False,
            rationale=(
                "Required fields, unknowns, referenced artifacts, hashes, proof gates, and "
                "public/protected boundaries "
                "remain mandatory pre-freeze validation obligations."
            ),
        ),
        FreezeProcedureGroup(
            group_id="procedure.readiness_sequence",
            steps=(7,),
            disposition=Disposition.SUPERSEDED_BY_ACCEPTED_SEQUENCE,
            blocking_before_manifest_freeze=False,
            rationale=(
                "The old pre-freeze provider-readiness probe is superseded by accepted "
                "transaction-bound sequencing: "
                "manifest freeze precedes static authority and issuer qualification, while fresh "
                "platform observation "
                "occurs after issuance and before the one governed execution."
            ),
        ),
        FreezeProcedureGroup(
            group_id="procedure.budget_and_cost_scope",
            steps=(8,),
            disposition=Disposition.G11_3B_COST_SCOPE_DECISION_REQUIRED,
            blocking_before_manifest_freeze=True,
            rationale=(
                "The zero external-spend ceiling is known, but final monetary cost reporting "
                "remains a producer/analysis "
                "scope decision that must be explicit before manifest freeze."
            ),
        ),
        FreezeProcedureGroup(
            group_id="procedure.canonicalization",
            steps=(9, 10),
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            blocking_before_manifest_freeze=False,
            rationale=(
                "Canonical serialization and SHA-256 identity remain required for the final "
                "manifest bytes."
            ),
        ),
        FreezeProcedureGroup(
            group_id="procedure.git_custody",
            steps=(11,),
            disposition=Disposition.POST_COMMIT_CUSTODY_RECEIPT_REQUIRED,
            blocking_before_manifest_freeze=False,
            rationale=(
                "The intent to bind the repository commit containing the manifest is retained "
                "through a separate "
                "post-commit receipt, avoiding impossible same-commit self-reference."
            ),
        ),
        FreezeProcedureGroup(
            group_id="procedure.freeze_marker",
            steps=(12,),
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            blocking_before_manifest_freeze=False,
            rationale=(
                "The manifest bytes may carry frozen status once pre-freeze blockers close; the "
                "repository G11 freeze "
                "gate is promoted only after the custody receipt binds those exact bytes."
            ),
        ),
        FreezeProcedureGroup(
            group_id="procedure.change_prohibition",
            steps=(13,),
            disposition=Disposition.FINAL_MANIFEST_REQUIRED,
            blocking_before_manifest_freeze=False,
            rationale=(
                "The frozen manifest identity becomes immutable experiment input and later "
                "static authority binding must "
                "reject any manifest-controlled byte drift before measured execution."
            ),
        ),
    )


def _producer_obligations() -> tuple[ProducerObligation, ...]:
    obligations = (
        (
            "final_request_transport_and_worker_startup",
            "Identify the exact live request transport and local-vLLM worker startup "
            "implementation that will execute all final turns.",
        ),
        (
            "final_runtime_trace_manifest_binding",
            "Prove every final runtime trace binds the actual frozen execution-manifest SHA in "
            "addition to planning lineage.",
        ),
        (
            "final_measured_evidence_bundle_writer",
            "Identify the exact typed evidence producer and bundle schema used during the one "
            "governed final execution.",
        ),
        (
            "final_attempt_action_reconciliation_persistence",
            "Persist every request attempt and action/state transition needed for denominator "
            "and failure-accounted reporting.",
        ),
        (
            "protected_measured_review_exporter",
            "Close the non-public measured review export writer, opaque identity mapping, digest "
            "receipt, retention, and deletion lifecycle.",
        ),
        (
            "primary_secondary_failure_persistence",
            "Persist the first causal failure independently from teardown, cleanup, packaging, "
            "and authority-terminalization failures.",
        ),
        (
            "teardown_cleanup_evidence_writer",
            "Identify the exact worker teardown and scratch-cleanup evidence producer executed "
            "at terminalization.",
        ),
        (
            "local_runtime_provider_field_mapping",
            "Map provider-era manifest and trace names to exact local-vLLM model, transport, and "
            "telemetry identities without semantic ambiguity.",
        ),
        (
            "pricing_scope_and_cost_claim_mapping",
            "Decide whether final monetary cost comparison is in scope and bind a valid pricing "
            "schedule or explicitly prohibit that claim family.",
        ),
        (
            "final_execution_analysis_input_schema",
            "Prove the runtime outputs are sufficient typed inputs for post-run eligibility, "
            "quality, paired analysis, and claim classification without retrofitting logs.",
        ),
    )
    return tuple(
        ProducerObligation(obligation_id=obligation_id, rationale=rationale)
        for obligation_id, rationale in obligations
    )


def build_record(root: Path) -> ReconciliationRecord:
    _validate_source_contracts(root)
    return ReconciliationRecord(
        reconciliation_id="auragateway-final-342-requirements-precedence-reconciliation-v1",
        source_main_commit=SOURCE_MAIN_COMMIT,
        source_bindings=_bindings(root),
        precedence=_precedence(),
        requirement_groups=_requirement_groups(),
        freeze_procedure_groups=_freeze_procedure_groups(),
        producer_obligations=_producer_obligations(),
        commit_binding=CommitBindingResolution(
            source_subject_commit_role=(
                "predecessor_repository_state_from_which_manifest_bytes_are_materialized"
            ),
            first_containing_commit_role=(
                "first_git_commit_whose_tree_contains_the_exact_manifest_bytes"
            ),
        ),
        safety_state=SafetyState(),
        next_gate=NEXT_GATE,
    )


def _canonical_bytes(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def write_record(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_source_head(root, exact=True)
    record = build_record(root)
    path = root / RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(record))
    return validate_repository(root)


def validate_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    _require_source_head(root, exact=False)
    expected = build_record(root)
    try:
        observed = ReconciliationRecord.model_validate_json(_read_bytes(root, RECORD_PATH))
    except ValidationError as error:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_RECORD_INVALID",
            "requirements reconciliation record failed typed validation",
            RECORD_PATH,
        ) from error
    if observed != expected:
        raise ReconciliationError(
            "FINAL_342_RECONCILIATION_RECORD_DRIFT",
            "requirements reconciliation record differs from deterministic reconstruction",
            RECORD_PATH,
        )

    for path, marker in (
        (ADR_PATH, "FINAL_342_REQUIREMENTS_PRECEDENCE_RECONCILIATION_V1"),
        (REPORT_PATH, "G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1"),
    ):
        if marker not in _read_bytes(root, path).decode("utf-8"):
            raise ReconciliationError(
                "FINAL_342_RECONCILIATION_DOCUMENT_MARKER_MISSING",
                "required reconciliation document marker is missing",
                path,
            )

    blocking_groups = [
        group.group_id
        for group in observed.requirement_groups
        if group.blocking_before_manifest_freeze
    ]
    blocking_procedure_groups = [
        group.group_id
        for group in observed.freeze_procedure_groups
        if group.blocking_before_manifest_freeze
    ]
    return {
        "status": "FINAL_342_REQUIREMENTS_PRECEDENCE_RECONCILIATION_V1_VALID",
        "required_field_count": 69,
        "freeze_procedure_step_count": 13,
        "precedence_rule_count": len(observed.precedence),
        "blocking_requirement_group_count": len(blocking_groups),
        "blocking_freeze_procedure_group_count": len(blocking_procedure_groups),
        "producer_obligation_count": len(observed.producer_obligations),
        "post_commit_custody_receipt_required": (
            observed.commit_binding.post_commit_custody_receipt_required
        ),
        "requirements_inventory_complete": True,
        "requirements_precedence_established": True,
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
    except (ReconciliationError, OSError, UnicodeDecodeError, ValueError) as error:
        if isinstance(error, ReconciliationError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path.as_posix() if error.path is not None else None,
            }
        else:
            payload = {
                "error_code": "FINAL_342_RECONCILIATION_FAILED",
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
