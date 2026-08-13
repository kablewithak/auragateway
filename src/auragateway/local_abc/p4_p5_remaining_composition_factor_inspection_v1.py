"""Freeze the post-PR #254 remaining-composition-factor static inspection.

This producer is static-only reliability infrastructure. It validates the exact
repository authorities that establish the current P4/P5 composition frontier,
inspects bounded Python semantics in the current remediated runtime and the
historical accepted predecessor runtime, and deterministically writes the
inspection record, review, and human report.

It does not authorize or perform runtime execution, Kaggle execution, model
loading, worker startup, model requests, P5, P6, or measured A/B/C work.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "ade6cb6fe3c4aaba6c99524d4cd347ee21546951"
STAGE_ID: Final = "STATIC_REMAINING_COMPOSITION_FACTOR_INSPECTION_V1"
NEXT_GATE: Final = "DESIGN_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_remaining_composition_factor_inspection_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_remaining_composition_factor_inspection_v1.py"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_remaining_composition_factor_inspection_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_remaining_composition_factor_inspection_v1_review.json"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_P5_Remaining_Composition_Factor_Inspection_V1.md"
)

CURRENT_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py"
)
CURRENT_RUNTIME_SHA256: Final = "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
HISTORICAL_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_successor_runtime_qualification_v1.py.tmpl"
)
HISTORICAL_RUNTIME_SHA256: Final = (
    "fd67c6377835b097be3b9b68a6c8abe4685a391250dc532fcdfa393bcc04f672"
)

V4_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
V5_INSTRUCTION: Final = (
    "For structured probes, return only the exact JSON object supplied in the final user message."
)
ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
EXPECTED_ROLES: Final = ("system", "user", "assistant", "user")
EXPECTED_REPETITION_COUNT: Final = 24


class AuthorityScope(StrEnum):
    CURRENT_ACCEPTED = "CURRENT_ACCEPTED"
    CURRENT_CAUSAL = "CURRENT_CAUSAL"
    CURRENT_REMEDIATION = "CURRENT_REMEDIATION"
    HISTORICAL_PRECEDENT = "HISTORICAL_PRECEDENT"


class HypothesisStatus(StrEnum):
    LIVE_UNRESOLVED = "LIVE_UNRESOLVED"
    INTERACTION_ONLY = "INTERACTION_ONLY"
    ELIMINATED_AS_SOLE_CAUSE = "ELIMINATED_AS_SOLE_CAUSE"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class InspectionError(RuntimeError):
    """Fail-closed static inspection error."""

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
        raise InspectionError("P4_P5_STATIC_INSPECTION_ARGUMENT_INVALID", message)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityReceipt(StrictModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: AuthorityScope


class RuntimeCompositionObservation(StrictModel):
    role: Literal["CURRENT_REMEDIATED_RUNTIME", "HISTORICAL_ACCEPTED_PREDECESSOR"]
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    message_roles: tuple[str, ...]
    assistant_ack: str
    cache_context_repetition_count: int = Field(gt=0)
    system_instruction: str
    cache_context_tail: str
    temperature: int
    top_p: int
    repetition_penalty: float
    seed: int
    max_tokens: int
    stream: bool
    accepted_behavioral_precedent: bool

    @model_validator(mode="after")
    def validate_frozen_shape(self) -> Self:
        if self.message_roles != EXPECTED_ROLES:
            raise ValueError("message-role topology drifted")
        if self.assistant_ack != ASSISTANT_ACK:
            raise ValueError("assistant acknowledgement drifted")
        if self.cache_context_repetition_count != EXPECTED_REPETITION_COUNT:
            raise ValueError("cache-context repetition count drifted")
        if (
            self.temperature != 0
            or self.top_p != 1
            or self.repetition_penalty != 1.1
            or self.seed != 7
            or self.max_tokens != 32
            or self.stream is not False
        ):
            raise ValueError("generation control drifted")
        return self


class HypothesisAssessment(StrictModel):
    rank: int = Field(ge=1)
    hypothesis_id: str = Field(min_length=1)
    status: HypothesisStatus
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    static_conclusion: str = Field(min_length=1)


class RecommendedDiscriminator(StrictModel):
    test_id: Literal["CACHE_CONTEXT_REPETITION_24_VS_1_WITH_COMPOSITION_FROZEN"]
    variable_under_test: Literal["CACHE_CONTEXT_REPETITION_COUNT"]
    control_value: Literal[1]
    treatment_value: Literal[24]
    frozen_message_roles: tuple[str, ...]
    assistant_ack_preserved: Literal[True]
    accepted_v4_instruction_preserved: Literal[True]
    final_json_object_preserved: Literal[True]
    runtime_model_identity_preserved: Literal[True]
    generation_controls_preserved: Literal[True]
    hidden_retries_permitted: Literal[0]
    reason: str = Field(min_length=1)
    execution_required_to_resolve: Literal[True]
    execution_authorized_by_inspection: Literal[False]

    @model_validator(mode="after")
    def validate_discriminator(self) -> Self:
        if self.frozen_message_roles != EXPECTED_ROLES:
            raise ValueError("recommended discriminator role topology drifted")
        return self


class InspectionRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-p4-p5-remaining-composition-factor-inspection-v1"]
    stage_id: Literal["STATIC_REMAINING_COMPOSITION_FACTOR_INSPECTION_V1"]
    status: Literal["STATIC_INSPECTION_COMPLETE_EXECUTION_NOT_AUTHORIZED"]
    base_main_commit: Literal["ade6cb6fe3c4aaba6c99524d4cd347ee21546951"]
    current_first_material_divergence: Literal["C3_COMPOSED_REQUEST_OUTPUT_CONTRACT"]
    current_composition_differential: Literal["COMPOSITION_REGRESSION_SUPPORTED"]
    first_remediation_result: Literal["REMEDIATION_INTERVENTION_INSUFFICIENT"]
    authorities: tuple[AuthorityReceipt, ...]
    current_runtime: RuntimeCompositionObservation
    historical_predecessor: RuntimeCompositionObservation
    hypotheses: tuple[HypothesisAssessment, ...]
    preferred_discriminator: RecommendedDiscriminator
    remaining_composition_subfactor_identified: Literal[False]
    root_cause_established: Literal[False]
    p5_reached: Literal[False]
    p6_reached: Literal[False]
    p5_failure_established: Literal[False]
    p6_failure_established: Literal[False]
    runtime_execution_authorized: Literal[False]
    gpu_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    guided_decoding_fix_authorized: Literal[False]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    non_claims: tuple[str, ...]
    next_gate: Literal["DESIGN_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"]

    @model_validator(mode="after")
    def validate_record_boundary(self) -> Self:
        if len(self.authorities) < 10:
            raise ValueError("static inspection authority set is incomplete")
        if tuple(item.rank for item in self.hypotheses) != tuple(
            range(1, len(self.hypotheses) + 1)
        ):
            raise ValueError("hypothesis ranks are not contiguous")
        if len(self.non_claims) < 10:
            raise ValueError("static inspection non-claim boundary is incomplete")
        return self


class InspectionReview(StrictModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal["auragateway-p4-p5-remaining-composition-factor-inspection-v1-review"]
    status: Literal["APPROVED_STATIC_INSPECTION_FOR_DIFFERENTIAL_DESIGN_ONLY"]
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    root_cause_claimed: Literal[False]
    remaining_subfactor_claimed_identified: Literal[False]
    runtime_execution_authorized: Literal[False]
    gpu_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    next_gate: Literal["DESIGN_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1"]


AUTHORITY_SPECS: Final = (
    (
        "historical_p4_acceptance",
        Path(
            "benchmarks/local_abc/"
            "auragateway_p4_output_contract_diagnostic_execution_acceptance_v1.json"
        ),
        "21290fc0aaccb53dccfaba728db50fe412af81fda945d41d413a5b13b10537db",
        AuthorityScope.HISTORICAL_PRECEDENT,
    ),
    (
        "historical_p4_template",
        Path("src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"),
        "93bdcf4a2ab3f4b4a07b688b8d6f9dc295ba3edcbb0b9bd63da8967393811441",
        AuthorityScope.HISTORICAL_PRECEDENT,
    ),
    (
        "composition_differential_design",
        Path("benchmarks/local_abc/auragateway_p4_p5_composition_differential_design_v1.json"),
        "5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1",
        AuthorityScope.CURRENT_CAUSAL,
    ),
    (
        "composition_differential_implementation",
        Path(
            "benchmarks/local_abc/auragateway_p4_p5_composition_differential_implementation_v1.json"
        ),
        "8b2b11f367b60272323cb9e6269cbb09e597063d03467207798c96b25e79b1b1",
        AuthorityScope.CURRENT_CAUSAL,
    ),
    (
        "composition_differential_reconciliation",
        Path(
            "benchmarks/local_abc/"
            "auragateway_p4_p5_composition_differential_"
            "terminalization_reconciliation_v1.json"
        ),
        "c0aac246a4d05afc2a4742d51c2dce557bb7c07e3efa298b674bc34611887d82",
        AuthorityScope.CURRENT_CAUSAL,
    ),
    (
        "composition_remediation_design",
        Path("benchmarks/local_abc/auragateway_p4_p5_composition_remediation_design_v1.json"),
        "ac737bccf6459951877b6695a6a6d368a81cba9318d6cee2656af48b6711c5ea",
        AuthorityScope.CURRENT_REMEDIATION,
    ),
    (
        "composition_remediation_implementation",
        Path(
            "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1.json"
        ),
        "681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8",
        AuthorityScope.CURRENT_REMEDIATION,
    ),
    (
        "composition_remediation_c3_reconciliation",
        Path(
            "benchmarks/local_abc/"
            "auragateway_p4_p5_composition_remediation_c3_"
            "failure_reconciliation_v1.json"
        ),
        "f5863b0077b358397c31fdeb2dd63f9eedfefab84de516b6946a98fbc9142b06",
        AuthorityScope.CURRENT_REMEDIATION,
    ),
    (
        "composition_remediation_c3_review",
        Path(
            "benchmarks/local_abc/"
            "auragateway_p4_p5_composition_remediation_c3_"
            "failure_reconciliation_v1_review.json"
        ),
        "67b8995ef42d208e6cb9aa25d8aac7d8764d6b23614982c0b25b3f6c73b6b984",
        AuthorityScope.CURRENT_REMEDIATION,
    ),
    (
        "current_remediated_runtime",
        CURRENT_RUNTIME_PATH,
        CURRENT_RUNTIME_SHA256,
        AuthorityScope.CURRENT_ACCEPTED,
    ),
    (
        "historical_predecessor_acceptance",
        Path("benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"),
        "d0268386d8d934257d035c2f720276d39e94a9eb0daa7da51175cc2cda3c1539",
        AuthorityScope.HISTORICAL_PRECEDENT,
    ),
    (
        "historical_predecessor_acceptance_review",
        Path(
            "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1_review.json"
        ),
        "8cbd4b94b47d7f167fee5523f660244acb54adfe6a2826da46fa85c38e8ba762",
        AuthorityScope.HISTORICAL_PRECEDENT,
    ),
    (
        "historical_predecessor_runtime_template",
        HISTORICAL_RUNTIME_PATH,
        HISTORICAL_RUNTIME_SHA256,
        AuthorityScope.HISTORICAL_PRECEDENT,
    ),
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_ARTIFACT_MISSING",
            "required static-inspection artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _require_hash(root: Path, relative: Path, expected: str) -> Path:
    path = _require_file(root, relative)
    observed = _sha256_file(path)
    if observed != expected:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_IDENTITY_DRIFT",
            "static-inspection authority byte identity drifted",
            relative.as_posix(),
        )
    return path


def _load_json(root: Path, relative: Path) -> dict[str, object]:
    path = _require_file(root, relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_JSON_INVALID",
            "static-inspection JSON authority is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_JSON_INVALID",
            "static-inspection JSON root must be an object",
            relative.as_posix(),
        )
    return cast(dict[str, object], payload)


def _canonical_json_bytes(payload: BaseModel | dict[str, object]) -> bytes:
    value: object = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_TEMP_PATH_EXISTS",
            "temporary output path already exists",
            str(temporary),
        )
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _assignment(tree: ast.Module, name: str) -> ast.expr:
    matches: list[ast.expr] = []
    for statement in tree.body:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id == name
        ):
            matches.append(statement.value)
        if (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == name
            and statement.value is not None
        ):
            matches.append(statement.value)
    if len(matches) != 1:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_RUNTIME_CONSTANT_CARDINALITY",
            "required runtime constant cardinality drifted",
            name,
        )
    return matches[0]


def _static_value(node: ast.expr) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_value(node.left)
        right = _static_value(node.right)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        left = _static_value(node.left)
        right = _static_value(node.right)
        if isinstance(left, str) and isinstance(right, int) and not isinstance(right, bool):
            return left * right
        if isinstance(right, str) and isinstance(left, int) and not isinstance(left, bool):
            return right * left
    raise InspectionError(
        "P4_P5_STATIC_INSPECTION_RUNTIME_EXPRESSION_UNSAFE",
        "runtime expression is outside the bounded static subset",
    )


def _string_assignment(tree: ast.Module, name: str) -> str:
    value = _static_value(_assignment(tree, name))
    if not isinstance(value, str):
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_RUNTIME_CONSTANT_TYPE",
            "required runtime constant is not a string",
            name,
        )
    return value


def _repetition_count(tree: ast.Module, name: str) -> int:
    node = _assignment(tree, name)
    counts: list[int] = []
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.BinOp) or not isinstance(candidate.op, ast.Mult):
            continue
        if (
            isinstance(candidate.left, ast.Constant)
            and isinstance(candidate.left.value, str)
            and isinstance(candidate.right, ast.Constant)
            and isinstance(candidate.right.value, int)
            and not isinstance(candidate.right.value, bool)
        ):
            counts.append(candidate.right.value)
        if (
            isinstance(candidate.right, ast.Constant)
            and isinstance(candidate.right.value, str)
            and isinstance(candidate.left, ast.Constant)
            and isinstance(candidate.left.value, int)
            and not isinstance(candidate.left.value, bool)
        ):
            counts.append(candidate.left.value)
    if len(counts) != 1:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_REPETITION_CARDINALITY",
            "cache-context repetition expression cardinality drifted",
            name,
        )
    return counts[0]


def _roles_from_static_lists(tree: ast.Module) -> tuple[str, ...]:
    for candidate in ast.walk(tree):
        if not isinstance(candidate, ast.List):
            continue
        roles: list[str] = []
        valid = True
        for element in candidate.elts:
            if not isinstance(element, ast.Dict):
                valid = False
                break
            role: str | None = None
            for key, value in zip(element.keys, element.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "role"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    role = value.value
            if role is None:
                valid = False
                break
            roles.append(role)
        if valid and tuple(roles) == EXPECTED_ROLES:
            return EXPECTED_ROLES
    raise InspectionError(
        "P4_P5_STATIC_INSPECTION_MESSAGE_ROLE_TOPOLOGY_DRIFT",
        "expected four-role request topology was not found",
    )


def _generation_controls(tree: ast.Module) -> dict[str, object]:
    required: dict[str, object] = {
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }
    for candidate in ast.walk(tree):
        if not isinstance(candidate, ast.Dict):
            continue
        values: dict[str, object] = {}
        safe = True
        for key, value in zip(candidate.keys, candidate.values, strict=True):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if key.value not in required:
                continue
            try:
                values[key.value] = _static_value(value)
            except InspectionError:
                safe = False
                break
        if safe and values == required:
            return required
    raise InspectionError(
        "P4_P5_STATIC_INSPECTION_GENERATION_CONTROL_DRIFT",
        "exact frozen generation controls were not found",
    )


def _tail(value: str) -> str:
    if value.endswith(V4_INSTRUCTION):
        return V4_INSTRUCTION
    if value.endswith(V5_INSTRUCTION):
        return V5_INSTRUCTION
    raise InspectionError(
        "P4_P5_STATIC_INSPECTION_CACHE_CONTEXT_TAIL_UNKNOWN",
        "cache-context instruction tail is not recognized",
    )


def _inspect_runtime(
    root: Path,
    *,
    path: Path,
    sha256: str,
    role: Literal["CURRENT_REMEDIATED_RUNTIME", "HISTORICAL_ACCEPTED_PREDECESSOR"],
) -> RuntimeCompositionObservation:
    source_path = _require_hash(root, path, sha256)
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_RUNTIME_AST_INVALID",
            "runtime source cannot be parsed for static inspection",
            path.as_posix(),
        ) from error

    if role == "CURRENT_REMEDIATED_RUNTIME":
        system_name = "SYSTEM_PROMPT"
        context_name = "SYNTHETIC_CACHE_CONTEXT_A"
    else:
        system_name = "V4_PROMPT"
        context_name = "V5_SYNTHETIC_CACHE_CONTEXT"

    context = _string_assignment(tree, context_name)
    controls = _generation_controls(tree)
    return RuntimeCompositionObservation(
        role=role,
        path=path.as_posix(),
        sha256=sha256,
        message_roles=_roles_from_static_lists(tree),
        assistant_ack=_string_assignment(tree, "SYNTHETIC_ASSISTANT_ACK"),
        cache_context_repetition_count=_repetition_count(tree, context_name),
        system_instruction=_string_assignment(tree, system_name),
        cache_context_tail=_tail(context),
        temperature=cast(int, controls["temperature"]),
        top_p=cast(int, controls["top_p"]),
        repetition_penalty=cast(float, controls["repetition_penalty"]),
        seed=cast(int, controls["seed"]),
        max_tokens=cast(int, controls["max_tokens"]),
        stream=cast(bool, controls["stream"]),
        accepted_behavioral_precedent=role == "HISTORICAL_ACCEPTED_PREDECESSOR",
    )


def _validate_semantic_authorities(root: Path) -> None:
    differential = _load_json(
        root,
        Path(
            "benchmarks/local_abc/"
            "auragateway_p4_p5_composition_differential_terminalization_reconciliation_v1.json"
        ),
    )
    expected_differential = {
        "variable_under_test": "MESSAGE_COMPOSITION_ONLY",
        "case_a_exact_successes": 3,
        "case_b_exact_successes": 0,
        "diagnostic_decision": "COMPOSITION_REGRESSION_SUPPORTED",
        "scientific_result_valid": True,
        "new_execution_authorized": False,
    }
    for key, expected in expected_differential.items():
        if differential.get(key) != expected:
            raise InspectionError(
                "P4_P5_STATIC_INSPECTION_DIFFERENTIAL_SEMANTIC_DRIFT",
                "accepted composition differential semantic contract drifted",
                key,
            )

    remediation = _load_json(
        root,
        Path(
            "benchmarks/local_abc/"
            "auragateway_p4_p5_composition_remediation_c3_failure_reconciliation_v1.json"
        ),
    )
    expected_remediation = {
        "causal_classification": "REMEDIATION_INTERVENTION_INSUFFICIENT",
        "v5_tail_replacement_sufficient_remediation": False,
        "composition_regression_family_remains_unresolved": True,
        "remaining_composition_subfactor_identified": False,
        "p5_reached": False,
        "p6_reached": False,
        "new_execution_authorized": False,
    }
    for key, expected in expected_remediation.items():
        if remediation.get(key) != expected:
            raise InspectionError(
                "P4_P5_STATIC_INSPECTION_REMEDIATION_SEMANTIC_DRIFT",
                "accepted remediation reconciliation semantic contract drifted",
                key,
            )

    predecessor = _load_json(
        root,
        Path("benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"),
    )
    if predecessor.get("governed_acceptance_status") != "ACCEPTED_GOVERNED_EXECUTION_PASS":
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_HISTORICAL_PRECEDENT_DRIFT",
            "historical predecessor acceptance status drifted",
        )
    if predecessor.get("current_line_p5_pass_accepted") is not True:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_HISTORICAL_PRECEDENT_DRIFT",
            "historical predecessor P5 acceptance drifted",
        )
    if predecessor.get("current_line_p6_pass_accepted") is not True:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_HISTORICAL_PRECEDENT_DRIFT",
            "historical predecessor P6 acceptance drifted",
        )


def _authority_receipts(root: Path) -> tuple[AuthorityReceipt, ...]:
    receipts: list[AuthorityReceipt] = []
    for role, path, sha256, scope in AUTHORITY_SPECS:
        _require_hash(root, path, sha256)
        receipts.append(
            AuthorityReceipt(role=role, path=path.as_posix(), sha256=sha256, scope=scope)
        )
    return tuple(receipts)


def build_record(root: Path) -> InspectionRecord:
    authorities = _authority_receipts(root)
    _validate_semantic_authorities(root)
    current = _inspect_runtime(
        root,
        path=CURRENT_RUNTIME_PATH,
        sha256=CURRENT_RUNTIME_SHA256,
        role="CURRENT_REMEDIATED_RUNTIME",
    )
    historical = _inspect_runtime(
        root,
        path=HISTORICAL_RUNTIME_PATH,
        sha256=HISTORICAL_RUNTIME_SHA256,
        role="HISTORICAL_ACCEPTED_PREDECESSOR",
    )

    if current.system_instruction != V4_INSTRUCTION:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_CURRENT_SYSTEM_INSTRUCTION_DRIFT",
            "current remediated runtime no longer uses the accepted V4 system instruction",
        )
    if current.cache_context_tail != V4_INSTRUCTION:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_CURRENT_CACHE_TAIL_DRIFT",
            "current remediated runtime cache-context tail drifted from accepted V4 instruction",
        )
    if historical.system_instruction != V4_INSTRUCTION:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_HISTORICAL_SYSTEM_INSTRUCTION_DRIFT",
            "historical predecessor system instruction drifted",
        )
    if historical.cache_context_tail != V5_INSTRUCTION:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_HISTORICAL_CACHE_TAIL_DRIFT",
            "historical predecessor cache-context tail drifted",
        )

    hypotheses = (
        HypothesisAssessment(
            rank=1,
            hypothesis_id="CURRENT_RUNTIME_X_LONG_REPEATED_CACHE_CONTEXT",
            status=HypothesisStatus.LIVE_UNRESOLVED,
            evidence_for=(
                (
                    "The current simple control succeeds 3/3 while the current full "
                    "composed request fails 0/3."
                ),
                "The V5-to-V4 instruction-tail replacement was executed and remained insufficient.",
                (
                    "The current composed request still contains a 24x repeated "
                    "synthetic cache context."
                ),
            ),
            evidence_against=(
                (
                    "The historical accepted predecessor used the same 24x repeated-context "
                    "shape and completed governed P5/P6 under an older runtime lineage."
                ),
                "No current governed 24-vs-1 counterfactual has been executed.",
            ),
            static_conclusion=(
                "The long repeated cache context remains a live current-runtime "
                "interaction candidate, not an established cause."
            ),
        ),
        HypothesisAssessment(
            rank=2,
            hypothesis_id="CURRENT_RUNTIME_X_ASSISTANT_ACK_AND_FOUR_ROLE_TOPOLOGY",
            status=HypothesisStatus.LIVE_UNRESOLVED,
            evidence_for=(
                (
                    "The current simple control omits both the assistant acknowledgement and "
                    "four-role topology while the failing composed request contains them."
                ),
            ),
            evidence_against=(
                (
                    "The historical accepted predecessor used the same four-role topology "
                    "and assistant acknowledgement."
                ),
                (
                    "Removing the assistant turn would also change role topology, making it "
                    "a less isolated first discriminator."
                ),
            ),
            static_conclusion=(
                "Assistant acknowledgement and role topology remain live only as "
                "current-runtime interaction candidates."
            ),
        ),
        HypothesisAssessment(
            rank=3,
            hypothesis_id="CURRENT_RUNTIME_X_HIGHER_ORDER_COMPOSITION_INTERACTION",
            status=HypothesisStatus.INTERACTION_ONLY,
            evidence_for=(
                (
                    "The accepted differential isolates the composition family but not an "
                    "individual subfactor."
                ),
                "The first single-factor remediation was insufficient.",
            ),
            evidence_against=(
                (
                    "No existing static evidence identifies which interaction term is "
                    "necessary or sufficient."
                ),
            ),
            static_conclusion=(
                "A higher-order interaction remains plausible and should be revisited "
                "only if simpler one-variable discriminators fail."
            ),
        ),
        HypothesisAssessment(
            rank=4,
            hypothesis_id="HISTORICAL_V5_CACHE_CONTEXT_TAIL_AS_SOLE_CAUSE",
            status=HypothesisStatus.ELIMINATED_AS_SOLE_CAUSE,
            evidence_for=(
                (
                    "Historical P4 evidence independently showed the V5 instruction was "
                    "defective in the earlier simple-output environment."
                ),
            ),
            evidence_against=(
                (
                    "The governed V5-to-V4 replacement was present in the exact remediated "
                    "runtime and the first composed C3 request still failed."
                ),
            ),
            static_conclusion=(
                "The V5 cache-context tail is not sufficient as the sole explanation of "
                "the current composed C3 regression."
            ),
        ),
        HypothesisAssessment(
            rank=5,
            hypothesis_id="GENERIC_MODEL_OR_BASIC_RUNTIME_UNRELIABILITY",
            status=HypothesisStatus.NOT_SUPPORTED,
            evidence_for=(),
            evidence_against=(
                (
                    "Current runtime installation, import closure, model construction, and "
                    "worker startup passed."
                ),
                "The current simple-control condition produced 3/3 exact-object successes.",
            ),
            static_conclusion=(
                "The available evidence does not support generic Qwen unreliability or "
                "basic runtime incompatibility as the current explanation."
            ),
        ),
    )

    source_sha256 = _sha256_file(_require_file(root, SOURCE_PATH))
    return InspectionRecord(
        schema_version="1.0.0",
        record_id="auragateway-p4-p5-remaining-composition-factor-inspection-v1",
        stage_id=STAGE_ID,
        status="STATIC_INSPECTION_COMPLETE_EXECUTION_NOT_AUTHORIZED",
        base_main_commit=BASE_MAIN_COMMIT,
        current_first_material_divergence="C3_COMPOSED_REQUEST_OUTPUT_CONTRACT",
        current_composition_differential="COMPOSITION_REGRESSION_SUPPORTED",
        first_remediation_result="REMEDIATION_INTERVENTION_INSUFFICIENT",
        authorities=authorities,
        current_runtime=current,
        historical_predecessor=historical,
        hypotheses=hypotheses,
        preferred_discriminator=RecommendedDiscriminator(
            test_id="CACHE_CONTEXT_REPETITION_24_VS_1_WITH_COMPOSITION_FROZEN",
            variable_under_test="CACHE_CONTEXT_REPETITION_COUNT",
            control_value=1,
            treatment_value=24,
            frozen_message_roles=EXPECTED_ROLES,
            assistant_ack_preserved=True,
            accepted_v4_instruction_preserved=True,
            final_json_object_preserved=True,
            runtime_model_identity_preserved=True,
            generation_controls_preserved=True,
            hidden_retries_permitted=0,
            reason=(
                "Changing only cache-context repetition from 24 to 1 preserves the "
                "four-role topology and assistant acknowledgement, giving a cleaner "
                "first discriminator than removing the assistant turn, which would "
                "change two structural properties at once."
            ),
            execution_required_to_resolve=True,
            execution_authorized_by_inspection=False,
        ),
        remaining_composition_subfactor_identified=False,
        root_cause_established=False,
        p5_reached=False,
        p6_reached=False,
        p5_failure_established=False,
        p6_failure_established=False,
        runtime_execution_authorized=False,
        gpu_execution_authorized=False,
        new_execution_authorized=False,
        guided_decoding_fix_authorized=False,
        source_sha256=source_sha256,
        non_claims=(
            "The remaining composition subfactor is not identified.",
            "Cache-context repetition count is not established as the root cause.",
            "The assistant acknowledgement is not established as the root cause.",
            "The four-role topology is not established as the root cause.",
            "A higher-order composition interaction is not established as the root cause.",
            "Generic Qwen unreliability is not established.",
            "Basic runtime incompatibility is not established.",
            "P5 was not reached and no P5 failure is established.",
            "P6 was not reached and no P6 failure is established.",
            "Guided decoding or schema forcing is not authorized by this inspection.",
            "No runtime, GPU, Kaggle, worker, or model-request execution is authorized.",
            (
                "Historical predecessor behavior is precedent only and does not qualify "
                "the current runtime lineage."
            ),
        ),
        next_gate=NEXT_GATE,
    )


def _report(record: InspectionRecord, record_sha256: str) -> str:
    hypothesis_lines = "\n".join(
        f"{item.rank}. `{item.hypothesis_id}` — `{item.status}` — {item.static_conclusion}"
        for item in record.hypotheses
    )
    non_claim_lines = "\n".join(f"- {item}" for item in record.non_claims)
    return f"""# AuraGateway P4/P5 Remaining Composition Factor Inspection V1

## Decision

`{record.status}`

The accepted composition family remains causally implicated, but the exact remaining
subfactor is not identified. The historical V5 cache-context instruction tail is
eliminated as a sufficient sole explanation because the governed V5-to-V4 remediation
was present and the first composed C3 request still failed.

## Current static observations

- Current first material divergence: `{record.current_first_material_divergence}`
- Accepted differential: `{record.current_composition_differential}`
- First remediation result: `{record.first_remediation_result}`
- Current request roles: `{",".join(record.current_runtime.message_roles)}`
- Current cache-context repetition count: `{record.current_runtime.cache_context_repetition_count}`
- Historical predecessor request roles: `{",".join(record.historical_predecessor.message_roles)}`
- Historical predecessor cache-context repetition count:
  `{record.historical_predecessor.cache_context_repetition_count}`
- Historical predecessor authority: precedent only; not current-runtime qualification

## Ranked remaining hypotheses

{hypothesis_lines}

## Smallest discriminating next design

`{record.preferred_discriminator.test_id}`

Freeze all current message/runtime/model/generation properties and vary only
cache-context repetition count from 1 to 24. This is the preferred first discriminator
because removing the assistant acknowledgement would also change the role topology.

This report **does not authorize execution**. The next legal gate is design and merge
of that differential only.

## Non-claims

{non_claim_lines}

## Identity

- Base main: `{record.base_main_commit}`
- Producer source SHA-256: `{record.source_sha256}`
- Record SHA-256: `{record_sha256}`
- Next gate: `{record.next_gate}`
"""


def write_outputs(root: Path) -> tuple[InspectionRecord, InspectionReview]:
    record = build_record(root)
    record_bytes = _canonical_json_bytes(record)
    record_sha256 = _sha256_bytes(record_bytes)
    report_bytes = _report(record, record_sha256).encode("utf-8")
    report_sha256 = _sha256_bytes(report_bytes)
    review = InspectionReview(
        schema_version="1.0.0",
        review_id="auragateway-p4-p5-remaining-composition-factor-inspection-v1-review",
        status="APPROVED_STATIC_INSPECTION_FOR_DIFFERENTIAL_DESIGN_ONLY",
        record_sha256=record_sha256,
        report_sha256=report_sha256,
        source_sha256=record.source_sha256,
        root_cause_claimed=False,
        remaining_subfactor_claimed_identified=False,
        runtime_execution_authorized=False,
        gpu_execution_authorized=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    _write_bytes_atomic(root / RECORD_PATH, record_bytes)
    _write_bytes_atomic(root / REPORT_PATH, report_bytes)
    _write_bytes_atomic(root / REVIEW_PATH, _canonical_json_bytes(review))
    return record, review


def check_outputs(root: Path) -> tuple[InspectionRecord, InspectionReview]:
    expected_record = build_record(root)
    record_path = _require_file(root, RECORD_PATH)
    review_path = _require_file(root, REVIEW_PATH)
    report_path = _require_file(root, REPORT_PATH)
    observed_record = InspectionRecord.model_validate(_load_json(root, RECORD_PATH))
    observed_review = InspectionReview.model_validate(_load_json(root, REVIEW_PATH))
    if observed_record != expected_record:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_RECORD_DRIFT",
            "static inspection record is not deterministic from current authorities",
            RECORD_PATH.as_posix(),
        )
    expected_record_bytes = _canonical_json_bytes(expected_record)
    if record_path.read_bytes() != expected_record_bytes:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_RECORD_BYTES_DRIFT",
            "static inspection record bytes are not canonical",
            RECORD_PATH.as_posix(),
        )
    record_sha256 = _sha256_bytes(expected_record_bytes)
    expected_report = _report(expected_record, record_sha256).encode("utf-8")
    if report_path.read_bytes() != expected_report:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_REPORT_DRIFT",
            "static inspection report bytes drifted",
            REPORT_PATH.as_posix(),
        )
    expected_review = InspectionReview(
        schema_version="1.0.0",
        review_id="auragateway-p4-p5-remaining-composition-factor-inspection-v1-review",
        status="APPROVED_STATIC_INSPECTION_FOR_DIFFERENTIAL_DESIGN_ONLY",
        record_sha256=record_sha256,
        report_sha256=_sha256_bytes(expected_report),
        source_sha256=expected_record.source_sha256,
        root_cause_claimed=False,
        remaining_subfactor_claimed_identified=False,
        runtime_execution_authorized=False,
        gpu_execution_authorized=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    if observed_review != expected_review:
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_REVIEW_DRIFT",
            "static inspection review drifted",
            REVIEW_PATH.as_posix(),
        )
    if review_path.read_bytes() != _canonical_json_bytes(expected_review):
        raise InspectionError(
            "P4_P5_STATIC_INSPECTION_REVIEW_BYTES_DRIFT",
            "static inspection review bytes are not canonical",
            REVIEW_PATH.as_posix(),
        )
    return observed_record, observed_review


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        description="Freeze/check remaining P4/P5 composition-factor inspection"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    try:
        if args.write:
            record, review = write_outputs(root)
        else:
            record, review = check_outputs(root)
    except InspectionError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "stage_id": record.stage_id,
                "status": record.status,
                "review_status": review.status,
                "next_gate": record.next_gate,
                "new_execution_authorized": record.new_execution_authorized,
                "runtime_execution_authorized": record.runtime_execution_authorized,
                "gpu_execution_authorized": record.gpu_execution_authorized,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
