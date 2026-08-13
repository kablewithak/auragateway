"""Freeze the P4/P5 cache-context repetition differential design V1.

Design-only reliability infrastructure. No Kaggle/GPU/model/worker execution or
runtime authority is created here.
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

BASE_MAIN_COMMIT: Final = "0b3c989fdbd60019fcdb1f22b9fe02cda2535e21"
NEXT_GATE: Final = "IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"

STATIC_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_remaining_composition_factor_inspection_v1.json"
)
STATIC_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_remaining_composition_factor_inspection_v1_review.json"
)
RUNTIME_PATH: Final = Path("src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py")
RUNTIME_SHA256: Final = "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
C3_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_remediation_c3_failure_reconciliation_v1.json"
)
C3_SHA256: Final = "f5863b0077b358397c31fdeb2dd63f9eedfefab84de516b6946a98fbc9142b06"
DIFF_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_differential_terminalization_reconciliation_v1.json"
)
DIFF_SHA256: Final = "c0aac246a4d05afc2a4742d51c2dce557bb7c07e3efa298b674bc34611887d82"
P5_ACCEPT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
)
P5_ACCEPT_SHA256: Final = "d0268386d8d934257d035c2f720276d39e94a9eb0daa7da51175cc2cda3c1539"
P5_RESET_PATH: Final = Path(
    "evidence_vault/local_abc/p5-p6-successor-runtime-qualification-pass-v1/"
    "p5_prefix_cache_reset_report_v1.json"
)
P5_RESET_SHA256: Final = "e75da04fc2ac3f20a07e36a5df391ef3ca6e922c31bbab9df1e3d7766071e33e"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_design_v1.json"
)

V4_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
FINAL_OBJECT: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
ROLES: Final = ("system", "user", "assistant", "user")
ORDER: Final = (
    "CONTROL_1X",
    "TREATMENT_24X",
    "TREATMENT_24X",
    "CONTROL_1X",
    "CONTROL_1X",
    "TREATMENT_24X",
)
FAILED_24X_TOKEN_COUNT: Final = 899
FAILED_24X_TOKEN_SHA256: Final = "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
FAILED_24X_PAYLOAD_SHA256: Final = (
    "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
)


class DesignError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
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
        raise DesignError("P4_P5_REPETITION_DIFF_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityScope(StrEnum):
    CURRENT_CAUSAL = "CURRENT_CAUSAL"
    CURRENT_REMEDIATION = "CURRENT_REMEDIATION"
    HISTORICAL_PRECEDENT = "HISTORICAL_PRECEDENT"


class ConditionId(StrEnum):
    CONTROL_1X = "CONTROL_1X"
    TREATMENT_24X = "TREATMENT_24X"


class DecisionState(StrEnum):
    LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED = "LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED"
    REPETITION_NOT_NECESSARY = "REPETITION_NOT_NECESSARY"
    REGRESSION_NOT_REPRODUCED = "REGRESSION_NOT_REPRODUCED"
    CONTROL_NOT_RELIABLE = "CONTROL_NOT_RELIABLE"
    NON_DETERMINISTIC_OR_AMBIGUOUS = "NON_DETERMINISTIC_OR_AMBIGUOUS"
    DIAGNOSTIC_INVALID = "DIAGNOSTIC_INVALID"


class AuthorityReceipt(FrozenModel):
    role: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: AuthorityScope


class GenerationControls(FrozenModel):
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    repetition_penalty: float = 1.1
    seed: Literal[7] = 7
    max_tokens: Literal[32] = 32
    stream: Literal[False] = False
    response_format_present: Literal[False] = False
    output_mode: Literal["UNCONSTRAINED"] = "UNCONSTRAINED"

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.repetition_penalty != 1.1:
            raise ValueError("repetition penalty drifted")
        return self


class RuntimeIdentity(FrozenModel):
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ]
    backend: Literal["TRITON_ATTN"]
    vllm_distribution: Literal["0.25.1+cu129"]
    torch: Literal["2.11.0+cu129"]
    torch_cuda: Literal["12.9"]
    triton: Literal["3.6.0"]
    transformers: Literal["5.14.1"]
    platform_topology: Literal["T4_x2"]
    worker_gpu_index: Literal[0]
    prefix_caching_enabled: Literal[True] = True
    cache_block_size: Literal[16] = 16
    max_model_len: Literal[4096] = 4096


class FrozenComposition(FrozenModel):
    prefix_variant: Literal["A"] = "A"
    message_roles: tuple[str, ...]
    system_instruction: str
    cache_context_tail: str
    assistant_ack: str
    final_object_canonical: str
    variable_under_test: Literal["CACHE_CONTEXT_REPETITION_COUNT"]
    no_schema_or_guided_decoding: Literal[True] = True
    parser_semantics_preserved: Literal[True] = True

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.message_roles != ROLES:
            raise ValueError("message roles drifted")
        if self.system_instruction != V4_INSTRUCTION:
            raise ValueError("system instruction drifted")
        if self.cache_context_tail != V4_INSTRUCTION:
            raise ValueError("cache-context tail drifted")
        if self.assistant_ack != ASSISTANT_ACK:
            raise ValueError("assistant acknowledgement drifted")
        if self.final_object_canonical != FINAL_OBJECT:
            raise ValueError("final object drifted")
        return self


class ConditionDefinition(FrozenModel):
    condition_id: ConditionId
    repetition_count: Literal[1, 24]
    repetitions: Literal[3] = 3
    fresh_worker_process_per_observation: Literal[True] = True

    @model_validator(mode="after")
    def exact(self) -> Self:
        expected = 1 if self.condition_id == ConditionId.CONTROL_1X else 24
        if self.repetition_count != expected:
            raise ValueError("condition repetition count drifted")
        return self


class StartingStateContract(FrozenModel):
    strategy: Literal["FRESH_WORKER_PROCESS_PER_OBSERVATION"]
    historical_reset_precedent_only: Literal[True] = True
    namespace_only_reset_permitted: Literal[False] = False
    prior_request_cache_carryover_permitted: Literal[False] = False
    require_fresh_worker_identity: Literal[True] = True
    require_zero_cached_prefix_baseline: Literal[True] = True
    teardown_required_between_observations: Literal[True] = True
    teardown_failure_invalidates_diagnostic: Literal[True] = True


class TokenIdentityContract(FrozenModel):
    prefix_variant: Literal["A"] = "A"
    pre_request_journal_required: Literal[True] = True
    journal_persisted_before_model_request: Literal[True] = True
    control_intra_condition_identity_required: Literal[True] = True
    treatment_intra_condition_identity_required: Literal[True] = True
    treatment_must_match_historical_failed_24x_identity: Literal[True] = True
    treatment_expected_token_count: Literal[899] = 899
    treatment_expected_token_sha256: str
    treatment_expected_payload_sha256: str
    control_must_differ_from_treatment_token_identity: Literal[True] = True
    raw_prompt_retained: Literal[False] = False


class RequestPlanItem(FrozenModel):
    ordinal: int = Field(ge=1, le=6)
    condition_id: ConditionId


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[6] = 6
    maximum_worker_starts: Literal[6] = 6
    maximum_model_requests: Literal[6] = 6
    maximum_output_tokens_per_request: Literal[32] = 32
    hidden_retries_permitted: Literal[0] = 0
    replacement_workers_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class DecisionRule(FrozenModel):
    state: DecisionState
    condition: str
    implication: str


class Safety(FrozenModel):
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    runtime_fix_authorized: Literal[False] = False
    threshold_search_authorized: Literal[False] = False
    assistant_topology_discriminator_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False


class DesignRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p4-p5-cache-context-repetition-differential-design-v1"]
    design_status: Literal["DESIGN_FROZEN_NOT_EXECUTED"]
    base_main_commit: Literal["0b3c989fdbd60019fcdb1f22b9fe02cda2535e21"]
    accepted_authorities: tuple[AuthorityReceipt, ...] = Field(min_length=7, max_length=7)
    runtime: RuntimeIdentity
    generation_controls: GenerationControls
    frozen_composition: FrozenComposition
    conditions: tuple[ConditionDefinition, ConditionDefinition]
    starting_state: StartingStateContract
    token_identity: TokenIdentityContract
    request_plan: tuple[RequestPlanItem, ...] = Field(min_length=6, max_length=6)
    execution_budget: ExecutionBudget
    decision_rules: tuple[DecisionRule, ...] = Field(min_length=6, max_length=6)
    safety: Safety
    next_gate: Literal["IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"]
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def exact(self) -> Self:
        if tuple(x.condition_id.value for x in self.request_plan) != ORDER:
            raise ValueError("request order drifted")
        if tuple(x.state for x in self.decision_rules) != tuple(DecisionState):
            raise ValueError("decision rule order drifted")
        return self


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _file(root: Path, path: Path) -> Path:
    absolute = root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise DesignError(
            "P4_P5_REPETITION_DIFF_AUTHORITY_MISSING",
            "required design authority is missing or unsafe",
            path.as_posix(),
        )
    return absolute


def _bytes(root: Path, path: Path, expected: str | None = None) -> bytes:
    data = _file(root, path).read_bytes()
    if expected is not None and _sha(data) != expected:
        raise DesignError(
            "P4_P5_REPETITION_DIFF_AUTHORITY_DRIFT",
            "required design authority identity drifted",
            path.as_posix(),
        )
    return data


def _object(root: Path, path: Path, expected: str | None = None) -> dict[str, object]:
    try:
        value: object = json.loads(_bytes(root, path, expected))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DesignError(
            "P4_P5_REPETITION_DIFF_AUTHORITY_INVALID",
            "required authority is not valid JSON",
            path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise DesignError(
            "P4_P5_REPETITION_DIFF_AUTHORITY_INVALID",
            "required authority root is not an object",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _main_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "main"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DesignError(
            "P4_P5_REPETITION_DIFF_GIT_STATE_INVALID",
            "unable to resolve local main",
        )
    return result.stdout.strip()


def _validate_semantics(root: Path) -> None:
    if _main_head(root) != BASE_MAIN_COMMIT:
        raise DesignError(
            "P4_P5_REPETITION_DIFF_BASE_MAIN_DRIFT",
            "local main no longer matches the frozen authority commit",
        )

    static = _object(root, STATIC_RECORD_PATH)
    if static.get("status") != "STATIC_INSPECTION_COMPLETE_EXECUTION_NOT_AUTHORIZED":
        raise DesignError("P4_P5_REPETITION_DIFF_STATIC_DRIFT", "static status drifted")
    if static.get("next_gate") != (
        "DESIGN_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"
    ):
        raise DesignError("P4_P5_REPETITION_DIFF_STATIC_DRIFT", "static next gate drifted")
    preferred = static.get("preferred_discriminator")
    if not isinstance(preferred, dict):
        raise DesignError(
            "P4_P5_REPETITION_DIFF_STATIC_DRIFT",
            "preferred discriminator is missing",
        )
    expected = {
        "test_id": "CACHE_CONTEXT_REPETITION_24_VS_1_WITH_COMPOSITION_FROZEN",
        "variable_under_test": "CACHE_CONTEXT_REPETITION_COUNT",
        "control_value": 1,
        "treatment_value": 24,
        "hidden_retries_permitted": 0,
        "execution_authorized_by_inspection": False,
    }
    for key, value in expected.items():
        if preferred.get(key) != value:
            raise DesignError(
                "P4_P5_REPETITION_DIFF_STATIC_DRIFT",
                "preferred discriminator drifted",
                key,
            )

    c3 = _object(root, C3_PATH, C3_SHA256)
    c3_expected = {
        "causal_classification": "REMEDIATION_INTERVENTION_INSUFFICIENT",
        "technical_first_divergence": "C3",
        "first_request_prefix_variant": "A",
        "first_request_token_count": FAILED_24X_TOKEN_COUNT,
        "first_request_token_sha256": FAILED_24X_TOKEN_SHA256,
        "first_request_payload_sha256": FAILED_24X_PAYLOAD_SHA256,
        "hidden_retries_performed": 0,
        "p5_reached": False,
        "p6_reached": False,
        "new_execution_authorized": False,
    }
    for key, value in c3_expected.items():
        if c3.get(key) != value:
            raise DesignError(
                "P4_P5_REPETITION_DIFF_C3_DRIFT",
                "C3 reconciliation drifted",
                key,
            )

    differential = _object(root, DIFF_PATH, DIFF_SHA256)
    diff_expected = {
        "variable_under_test": "MESSAGE_COMPOSITION_ONLY",
        "case_a_exact_successes": 3,
        "case_b_exact_successes": 0,
        "diagnostic_decision": "COMPOSITION_REGRESSION_SUPPORTED",
        "scientific_result_valid": True,
    }
    for key, value in diff_expected.items():
        if differential.get(key) != value:
            raise DesignError(
                "P4_P5_REPETITION_DIFF_BASELINE_DRIFT",
                "accepted composition differential drifted",
                key,
            )

    acceptance = _object(root, P5_ACCEPT_PATH, P5_ACCEPT_SHA256)
    if acceptance.get("governed_acceptance_status") != "ACCEPTED_GOVERNED_EXECUTION_PASS":
        raise DesignError(
            "P4_P5_REPETITION_DIFF_RESET_PRECEDENT_DRIFT",
            "historical P5/P6 acceptance drifted",
        )

    reset = _object(root, P5_RESET_PATH, P5_RESET_SHA256)
    if reset.get("status") != "PASSED":
        raise DesignError(
            "P4_P5_REPETITION_DIFF_RESET_PRECEDENT_DRIFT",
            "historical reset status drifted",
        )
    if reset.get("full_process_restart_reset_proven") is not True:
        raise DesignError(
            "P4_P5_REPETITION_DIFF_RESET_PRECEDENT_DRIFT",
            "full-process reset precedent is absent",
        )
    if reset.get("namespace_only_reset_used") is not False:
        raise DesignError(
            "P4_P5_REPETITION_DIFF_RESET_PRECEDENT_DRIFT",
            "namespace-only reset unexpectedly used",
        )


def validate_authorities(root: Path) -> tuple[AuthorityReceipt, ...]:
    _validate_semantics(root)
    specs = (
        ("static_inspection", STATIC_RECORD_PATH, None, AuthorityScope.CURRENT_CAUSAL),
        ("static_inspection_review", STATIC_REVIEW_PATH, None, AuthorityScope.CURRENT_CAUSAL),
        (
            "current_remediated_runtime",
            RUNTIME_PATH,
            RUNTIME_SHA256,
            AuthorityScope.CURRENT_REMEDIATION,
        ),
        ("c3_reconciliation", C3_PATH, C3_SHA256, AuthorityScope.CURRENT_REMEDIATION),
        ("composition_differential", DIFF_PATH, DIFF_SHA256, AuthorityScope.CURRENT_CAUSAL),
        (
            "historical_p5_p6_acceptance",
            P5_ACCEPT_PATH,
            P5_ACCEPT_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
        (
            "historical_full_process_reset",
            P5_RESET_PATH,
            P5_RESET_SHA256,
            AuthorityScope.HISTORICAL_PRECEDENT,
        ),
    )
    return tuple(
        AuthorityReceipt(
            role=role,
            path=path.as_posix(),
            sha256=_sha(_bytes(root, path, expected)),
            scope=scope,
        )
        for role, path, expected, scope in specs
    )


def build_design_record(root: Path) -> DesignRecord:
    return DesignRecord(
        record_id="auragateway-p4-p5-cache-context-repetition-differential-design-v1",
        design_status="DESIGN_FROZEN_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        accepted_authorities=validate_authorities(root),
        runtime=RuntimeIdentity(
            model_repository="Qwen/Qwen2.5-0.5B-Instruct",
            model_revision="7ae557604adf67be50417f59c2c2f167def9a775",
            tokenizer_revision="7ae557604adf67be50417f59c2c2f167def9a775",
            model_snapshot_sha256=(
                "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
            ),
            backend="TRITON_ATTN",
            vllm_distribution="0.25.1+cu129",
            torch="2.11.0+cu129",
            torch_cuda="12.9",
            triton="3.6.0",
            transformers="5.14.1",
            platform_topology="T4_x2",
            worker_gpu_index=0,
        ),
        generation_controls=GenerationControls(),
        frozen_composition=FrozenComposition(
            message_roles=ROLES,
            system_instruction=V4_INSTRUCTION,
            cache_context_tail=V4_INSTRUCTION,
            assistant_ack=ASSISTANT_ACK,
            final_object_canonical=FINAL_OBJECT,
            variable_under_test="CACHE_CONTEXT_REPETITION_COUNT",
        ),
        conditions=(
            ConditionDefinition(condition_id=ConditionId.CONTROL_1X, repetition_count=1),
            ConditionDefinition(condition_id=ConditionId.TREATMENT_24X, repetition_count=24),
        ),
        starting_state=StartingStateContract(strategy="FRESH_WORKER_PROCESS_PER_OBSERVATION"),
        token_identity=TokenIdentityContract(
            treatment_expected_token_sha256=FAILED_24X_TOKEN_SHA256,
            treatment_expected_payload_sha256=FAILED_24X_PAYLOAD_SHA256,
        ),
        request_plan=tuple(
            RequestPlanItem(ordinal=i, condition_id=ConditionId(value))
            for i, value in enumerate(ORDER, start=1)
        ),
        execution_budget=ExecutionBudget(),
        decision_rules=(
            DecisionRule(
                state=DecisionState.LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED,
                condition="1x is 3/3 exact-object and 24x is 0/3 exact-object.",
                implication=(
                    "Supports the 24x-vs-1x long/repeated-context condition as "
                    "necessary relative to the 1x control."
                ),
            ),
            DecisionRule(
                state=DecisionState.REPETITION_NOT_NECESSARY,
                condition="1x is 0/3 exact-object and 24x is 0/3 exact-object.",
                implication="The regression survives at 1x; 24x-vs-1x repetition is not necessary.",
            ),
            DecisionRule(
                state=DecisionState.REGRESSION_NOT_REPRODUCED,
                condition="1x is 3/3 exact-object and 24x is 3/3 exact-object.",
                implication=(
                    "The prior regression is not reproduced under the frozen fresh-worker design."
                ),
            ),
            DecisionRule(
                state=DecisionState.CONTROL_NOT_RELIABLE,
                condition="The 1x control is mixed or unstable.",
                implication="The control is not reliable enough to support a necessity claim.",
            ),
            DecisionRule(
                state=DecisionState.NON_DETERMINISTIC_OR_AMBIGUOUS,
                condition="1x is stable 3/3 exact-object while 24x is mixed.",
                implication=(
                    "The treatment is ambiguous; stop and reconcile without "
                    "adding another condition."
                ),
            ),
            DecisionRule(
                state=DecisionState.DIAGNOSTIC_INVALID,
                condition=(
                    "A required runtime, worker, token, cold-state, budget, "
                    "teardown, or cleanup invariant fails."
                ),
                implication="The experiment cannot support a behavioral conclusion.",
            ),
        ),
        safety=Safety(),
        next_gate=NEXT_GATE,
        non_claims=(
            "Exactly 24 repetitions are not established as the causal threshold.",
            "Context length alone is not established as the root cause.",
            "Prefix caching itself is not established as defective.",
            "The assistant acknowledgement is not established as causal.",
            "The four-role topology is not established as causal.",
            "A higher-order interaction is not established as causal.",
            "Historical reset evidence is precedent only, not current-runtime proof.",
            "P5 is not requalified by this design.",
            "P6 is not requalified by this design.",
            "No threshold search is authorized.",
            "No assistant/topology discriminator is authorized.",
            "No runtime/GPU/Kaggle/model execution is authorized.",
            "Measured A/B/C execution is not authorized.",
            "Production readiness is not established.",
        ),
    )


def generate(root: Path) -> DesignRecord:
    record = build_design_record(root)
    path = root / RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(record))
    return record


def validate_generated(root: Path) -> DesignRecord:
    expected = build_design_record(root)
    observed = _file(root, RECORD_PATH).read_bytes()
    if observed != _canonical(expected):
        raise DesignError(
            "P4_P5_REPETITION_DIFF_RECORD_DRIFT",
            "generated design record drifted",
            RECORD_PATH.as_posix(),
        )
    return DesignRecord.model_validate(json.loads(observed))


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Freeze/check repetition differential design V1")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.repo_root.resolve()
    try:
        record = generate(root) if args.write else validate_generated(root)
    except DesignError as error:
        print(json.dumps(error.envelope(), separators=(",", ":"), sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "design_status": record.design_status,
                "variable_under_test": record.frozen_composition.variable_under_test,
                "control": record.conditions[0].repetition_count,
                "treatment": record.conditions[1].repetition_count,
                "starting_state": record.starting_state.strategy,
                "maximum_model_requests": record.execution_budget.maximum_model_requests,
                "maximum_model_loads": record.execution_budget.maximum_model_loads,
                "maximum_worker_starts": record.execution_budget.maximum_worker_starts,
                "runtime_execution_authorized": record.safety.runtime_execution_authorized,
                "next_gate": record.next_gate,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
