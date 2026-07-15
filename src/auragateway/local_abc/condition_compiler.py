"""Deterministic compiler for the controlled local A/B/C conditions."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import (
    ConditionDefinition,
    ConditionId,
    LocalABCContract,
    PrefixIdentity,
    PrefixPolicy,
    RouteSchedule,
    TokenizerIdentity,
    WorkerId,
)
from auragateway.local_abc.prefix_identity import (
    DEFAULT_PREFIX_SERIALIZER_VERSION,
    TokenEncoder,
    build_prefix_identity,
)

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
_MARKER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,95}$")


class StablePrefixMaterial(LocalABCContract):
    """Exact content allowed in the reusable prefix boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    template_id: str
    template_version: str = Field(min_length=1, max_length=80)
    segments: tuple[str, ...] = Field(min_length=1)
    tool_contracts: tuple[str, ...] = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    context_pack: str = Field(min_length=1)

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("template_id must use stable lowercase characters")
        return value

    @field_validator("segments", "tool_contracts")
    @classmethod
    def validate_ordered_content(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("stable prefix entries must not be blank")
        if len(value) != len(set(value)):
            raise ValueError("stable prefix entries must not contain duplicates")
        return value

    @field_validator("output_schema", "context_pack")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("stable prefix text must not be blank")
        return value


class VolatileTurnMaterial(LocalABCContract):
    """Per-turn material that must remain outside the reusable prefix."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str
    turn_index: Literal[1, 2]
    user_message: str = Field(min_length=1)
    retrieved_evidence: tuple[str, ...] = ()
    retained_feedback: tuple[str, ...] = ()

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use stable lowercase characters")
        return value

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_message must not be blank")
        return value

    @field_validator("retrieved_evidence", "retained_feedback")
    @classmethod
    def validate_volatile_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("volatile entries must not be blank")
        if len(value) != len(set(value)):
            raise ValueError("volatile entries must not contain duplicates")
        return value


class CacheHostileMutationFixture(LocalABCContract):
    """Synthetic deterministic marker that intentionally changes Condition A prefixes."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    fixture_id: str
    turn_index: Literal[1, 2]
    marker: str

    @field_validator("fixture_id")
    @classmethod
    def validate_fixture_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("fixture_id must use stable lowercase characters")
        return value

    @field_validator("marker")
    @classmethod
    def validate_marker(cls, value: str) -> str:
        if _MARKER_PATTERN.fullmatch(value) is None:
            raise ValueError("marker must be a stable synthetic identifier")
        return value


class CompiledTurn(LocalABCContract):
    """Exact compiled prefix/suffix pair for one condition turn."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    condition_id: ConditionId
    turn_index: Literal[1, 2]
    serialized_prefix: str = Field(min_length=1)
    serialized_suffix: str = Field(min_length=1)
    prefix_identity: PrefixIdentity


class CompiledCondition(LocalABCContract):
    """A validated condition definition plus its two compiled turns."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    definition: ConditionDefinition
    turns: tuple[CompiledTurn, CompiledTurn]

    @model_validator(mode="after")
    def validate_turns(self) -> Self:
        if tuple(turn.turn_index for turn in self.turns) != (1, 2):
            raise ValueError("compiled condition requires ordered turns 1 and 2")
        if any(turn.condition_id is not self.definition.condition_id for turn in self.turns):
            raise ValueError("compiled turns must match the condition definition")
        if self.definition.prefix_identity != self.turns[0].prefix_identity:
            raise ValueError("condition definition must bind the first-turn prefix identity")

        identities = tuple(turn.prefix_identity for turn in self.turns)
        if self.definition.condition_id is ConditionId.A:
            if identities[0] == identities[1]:
                raise ValueError("Condition A mutation fixtures must change prefix identity")
        elif identities[0] != identities[1]:
            raise ValueError("deterministic conditions require identical turn prefix identities")
        return self


class CompiledExperiment(LocalABCContract):
    """Machine-checked A/B/C compiler output before any worker execution."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    conditions: tuple[CompiledCondition, CompiledCondition, CompiledCondition]

    @model_validator(mode="after")
    def validate_causal_relations(self) -> Self:
        by_id = {item.definition.condition_id: item for item in self.conditions}
        if set(by_id) != set(ConditionId):
            raise ValueError("compiled experiment requires exactly A, B, and C")

        condition_a = by_id[ConditionId.A]
        condition_b = by_id[ConditionId.B]
        condition_c = by_id[ConditionId.C]

        if condition_a.definition.route_schedule != condition_b.definition.route_schedule:
            raise ValueError("A and B must use identical route schedules")
        if condition_b.definition.route_schedule == condition_c.definition.route_schedule:
            raise ValueError("B and C must differ only by worker affinity schedule")

        for turn_index in range(2):
            turn_a = condition_a.turns[turn_index]
            turn_b = condition_b.turns[turn_index]
            turn_c = condition_c.turns[turn_index]
            if turn_b.prefix_identity != turn_c.prefix_identity:
                raise ValueError("B and C must have identical token-level prefix identities")
            if not (
                turn_a.serialized_suffix == turn_b.serialized_suffix == turn_c.serialized_suffix
            ):
                raise ValueError("volatile suffix content must match across A, B, and C")
        return self

    def condition_for(self, condition_id: ConditionId) -> CompiledCondition:
        """Return one required compiled condition."""

        return next(
            item for item in self.conditions if item.definition.condition_id is condition_id
        )


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def serialize_stable_prefix(
    material: StablePrefixMaterial,
    mutation: CacheHostileMutationFixture | None = None,
) -> str:
    """Serialize only reusable material, plus an optional synthetic A-control marker."""

    payload: dict[str, object] = {
        "boundary": "stable_prefix",
        "schema_version": material.schema_version,
        "template": {
            "template_id": material.template_id,
            "template_version": material.template_version,
        },
        "segments": list(material.segments),
        "tool_contracts": list(material.tool_contracts),
        "output_schema": material.output_schema,
        "context_pack": material.context_pack,
    }
    if mutation is not None:
        payload["cache_hostile_mutation"] = {
            "fixture_id": mutation.fixture_id,
            "marker": mutation.marker,
            "turn_index": mutation.turn_index,
        }
    return _canonical_json(payload)


def serialize_volatile_suffix(material: VolatileTurnMaterial) -> str:
    """Serialize per-turn material outside the cache-reusable prefix boundary."""

    return _canonical_json(
        {
            "boundary": "volatile_suffix",
            "schema_version": material.schema_version,
            "case_id": material.case_id,
            "turn_index": material.turn_index,
            "user_message": material.user_message,
            "retrieved_evidence": list(material.retrieved_evidence),
            "retained_feedback": list(material.retained_feedback),
        }
    )


def frozen_route_schedule(condition_id: ConditionId) -> RouteSchedule:
    """Return the constitution-defined two-turn route for one condition."""

    schedules = {
        ConditionId.A: (WorkerId.WORKER_1, WorkerId.WORKER_2),
        ConditionId.B: (WorkerId.WORKER_1, WorkerId.WORKER_2),
        ConditionId.C: (WorkerId.WORKER_1, WorkerId.WORKER_1),
    }
    return RouteSchedule(workers=schedules[condition_id])


class ConditionCompiler:
    """Compile deterministic A/B/C conditions behind a tokenizer protocol seam."""

    def __init__(
        self,
        *,
        tokenizer: TokenizerIdentity,
        encoder: TokenEncoder,
        serializer_version: str = DEFAULT_PREFIX_SERIALIZER_VERSION,
    ) -> None:
        self._tokenizer = tokenizer
        self._encoder = encoder
        self._serializer_version = serializer_version

    def compile_condition(
        self,
        *,
        condition_id: ConditionId,
        stable_prefix: StablePrefixMaterial,
        turns: Sequence[VolatileTurnMaterial],
        mutations: Sequence[CacheHostileMutationFixture] = (),
    ) -> CompiledCondition:
        """Compile one condition and enforce its stable-prefix semantics."""

        ordered_turns = tuple(sorted(turns, key=lambda item: item.turn_index))
        if len(ordered_turns) != 2 or tuple(item.turn_index for item in ordered_turns) != (1, 2):
            raise ValueError("exactly one volatile turn for indexes 1 and 2 is required")
        if len({item.case_id for item in ordered_turns}) != 1:
            raise ValueError("both turns must belong to the same case")

        mutation_by_turn = self._validate_mutations(condition_id, mutations)
        compiled_turns: list[CompiledTurn] = []
        for turn in ordered_turns:
            serialized_prefix = serialize_stable_prefix(
                stable_prefix,
                mutation_by_turn.get(turn.turn_index),
            )
            compiled_turns.append(
                CompiledTurn(
                    condition_id=condition_id,
                    turn_index=turn.turn_index,
                    serialized_prefix=serialized_prefix,
                    serialized_suffix=serialize_volatile_suffix(turn),
                    prefix_identity=build_prefix_identity(
                        prefix_text=serialized_prefix,
                        tokenizer=self._tokenizer,
                        encoder=self._encoder,
                        serializer_version=self._serializer_version,
                    ),
                )
            )

        first_turn, second_turn = compiled_turns
        prefix_policy = (
            PrefixPolicy.CACHE_HOSTILE
            if condition_id is ConditionId.A
            else PrefixPolicy.DETERMINISTIC_EXACT
        )
        definition = ConditionDefinition(
            condition_id=condition_id,
            prefix_policy=prefix_policy,
            route_schedule=frozen_route_schedule(condition_id),
            prefix_identity=first_turn.prefix_identity,
        )
        return CompiledCondition(
            definition=definition,
            turns=(first_turn, second_turn),
        )

    def compile_experiment(
        self,
        *,
        stable_prefix: StablePrefixMaterial,
        turns: Sequence[VolatileTurnMaterial],
        condition_a_mutations: Sequence[CacheHostileMutationFixture],
    ) -> CompiledExperiment:
        """Compile all three conditions from one controlled stable/suffix input set."""

        condition_a = self.compile_condition(
            condition_id=ConditionId.A,
            stable_prefix=stable_prefix,
            turns=turns,
            mutations=condition_a_mutations,
        )
        condition_b = self.compile_condition(
            condition_id=ConditionId.B,
            stable_prefix=stable_prefix,
            turns=turns,
        )
        condition_c = self.compile_condition(
            condition_id=ConditionId.C,
            stable_prefix=stable_prefix,
            turns=turns,
        )
        return CompiledExperiment(conditions=(condition_a, condition_b, condition_c))

    @staticmethod
    def _validate_mutations(
        condition_id: ConditionId,
        mutations: Sequence[CacheHostileMutationFixture],
    ) -> dict[int, CacheHostileMutationFixture]:
        if condition_id is not ConditionId.A:
            if mutations:
                raise ValueError("mutation fixtures are permitted only for Condition A")
            return {}

        mutation_by_turn: dict[int, CacheHostileMutationFixture] = {
            item.turn_index: item for item in mutations
        }
        if len(mutations) != 2 or set(mutation_by_turn) != {1, 2}:
            raise ValueError("Condition A requires one mutation fixture for each turn")
        if len({item.fixture_id for item in mutations}) != 2:
            raise ValueError("Condition A mutation fixture IDs must be unique")
        if len({item.marker for item in mutations}) != 2:
            raise ValueError("Condition A mutation markers must be unique")
        return mutation_by_turn
