from __future__ import annotations

import pytest

from auragateway.local_abc.condition_compiler import (
    CacheHostileMutationFixture,
    ConditionCompiler,
    StablePrefixMaterial,
    VolatileTurnMaterial,
    frozen_route_schedule,
    serialize_stable_prefix,
    serialize_volatile_suffix,
)
from auragateway.local_abc.contracts import ConditionId, TokenizerIdentity, WorkerId


class Utf8TokenEncoder:
    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(text.encode("utf-8"))


def compiler() -> ConditionCompiler:
    tokenizer = TokenizerIdentity(
        repository="synthetic/tokenizer",
        revision="abcdef1234567",
        config_sha256="1" * 64,
    )
    return ConditionCompiler(tokenizer=tokenizer, encoder=Utf8TokenEncoder())


def stable_prefix() -> StablePrefixMaterial:
    return StablePrefixMaterial(
        template_id="nimbus-relay-template-v1",
        template_version="1.0.0",
        segments=(
            "Act as the synthetic Nimbus Relay support agent.",
            "Use only approved retrieval evidence.",
        ),
        tool_contracts=("retrieve-nimbus-docs-v1", "record-terminal-decision-v1"),
        output_schema="assistant-terminal-decision-v1",
        context_pack="nimbus-relay-support-constraints-v1",
    )


def turns() -> tuple[VolatileTurnMaterial, VolatileTurnMaterial]:
    return (
        VolatileTurnMaterial(
            case_id="case-001",
            turn_index=1,
            user_message="How do I verify my relay account?",
            retrieved_evidence=("source-001",),
        ),
        VolatileTurnMaterial(
            case_id="case-001",
            turn_index=2,
            user_message="What should I do when verification fails?",
            retrieved_evidence=("source-002",),
            retained_feedback=("account scope is still required",),
        ),
    )


def mutations() -> tuple[CacheHostileMutationFixture, CacheHostileMutationFixture]:
    return (
        CacheHostileMutationFixture(
            fixture_id="mutation-turn-1",
            turn_index=1,
            marker="cache-hostile-turn-1",
        ),
        CacheHostileMutationFixture(
            fixture_id="mutation-turn-2",
            turn_index=2,
            marker="cache-hostile-turn-2",
        ),
    )


def test_serializers_are_deterministic() -> None:
    assert serialize_stable_prefix(stable_prefix()) == serialize_stable_prefix(stable_prefix())
    assert serialize_volatile_suffix(turns()[0]) == serialize_volatile_suffix(turns()[0])


def test_stable_and_volatile_boundaries_are_separate() -> None:
    original_turn = turns()[0]
    changed_turn = original_turn.model_copy(update={"user_message": "A different user message"})

    assert serialize_stable_prefix(stable_prefix()) == serialize_stable_prefix(stable_prefix())
    assert serialize_volatile_suffix(original_turn) != serialize_volatile_suffix(changed_turn)


def test_volatile_change_does_not_change_deterministic_prefix_identity() -> None:
    original = compiler().compile_condition(
        condition_id=ConditionId.B,
        stable_prefix=stable_prefix(),
        turns=turns(),
    )
    changed_turns = (
        turns()[0].model_copy(update={"user_message": "A different user message"}),
        turns()[1],
    )
    changed = compiler().compile_condition(
        condition_id=ConditionId.B,
        stable_prefix=stable_prefix(),
        turns=changed_turns,
    )

    assert original.turns[0].prefix_identity == changed.turns[0].prefix_identity
    assert original.turns[0].serialized_suffix != changed.turns[0].serialized_suffix


def test_stable_change_changes_prefix_identity() -> None:
    original = compiler().compile_condition(
        condition_id=ConditionId.B,
        stable_prefix=stable_prefix(),
        turns=turns(),
    )
    changed_stable = stable_prefix().model_copy(update={"context_pack": "changed-context-pack"})
    changed = compiler().compile_condition(
        condition_id=ConditionId.B,
        stable_prefix=changed_stable,
        turns=turns(),
    )

    assert original.turns[0].prefix_identity != changed.turns[0].prefix_identity


def test_condition_a_mutates_prefix_identity_between_turns() -> None:
    compiled = compiler().compile_condition(
        condition_id=ConditionId.A,
        stable_prefix=stable_prefix(),
        turns=turns(),
        mutations=mutations(),
    )

    assert compiled.turns[0].prefix_identity != compiled.turns[1].prefix_identity


def test_conditions_b_and_c_preserve_exact_prefix_between_turns() -> None:
    for condition_id in (ConditionId.B, ConditionId.C):
        compiled = compiler().compile_condition(
            condition_id=condition_id,
            stable_prefix=stable_prefix(),
            turns=turns(),
        )
        assert compiled.turns[0].prefix_identity == compiled.turns[1].prefix_identity


def test_compile_experiment_enforces_b_c_prefix_identity() -> None:
    compiled = compiler().compile_experiment(
        stable_prefix=stable_prefix(),
        turns=turns(),
        condition_a_mutations=mutations(),
    )

    condition_b = compiled.condition_for(ConditionId.B)
    condition_c = compiled.condition_for(ConditionId.C)
    assert condition_b.turns[0].prefix_identity == condition_c.turns[0].prefix_identity
    assert condition_b.turns[1].prefix_identity == condition_c.turns[1].prefix_identity


def test_compile_experiment_preserves_suffix_content_across_conditions() -> None:
    compiled = compiler().compile_experiment(
        stable_prefix=stable_prefix(),
        turns=turns(),
        condition_a_mutations=mutations(),
    )

    for turn_index in range(2):
        suffixes = {
            condition.turns[turn_index].serialized_suffix for condition in compiled.conditions
        }
        assert len(suffixes) == 1


def test_frozen_route_schedules_preserve_causal_contrasts() -> None:
    route_a = frozen_route_schedule(ConditionId.A)
    route_b = frozen_route_schedule(ConditionId.B)
    route_c = frozen_route_schedule(ConditionId.C)

    assert route_a == route_b
    assert route_b != route_c
    assert route_a.workers == (WorkerId.WORKER_1, WorkerId.WORKER_2)
    assert route_c.workers == (WorkerId.WORKER_1, WorkerId.WORKER_1)


def test_non_a_condition_rejects_mutation_fixtures() -> None:
    with pytest.raises(ValueError, match="only for Condition A"):
        compiler().compile_condition(
            condition_id=ConditionId.B,
            stable_prefix=stable_prefix(),
            turns=turns(),
            mutations=mutations(),
        )


@pytest.mark.parametrize(
    "invalid_mutations",
    [
        (),
        (mutations()[0],),
        (mutations()[0], mutations()[0]),
        (
            mutations()[0],
            mutations()[1].model_copy(update={"marker": mutations()[0].marker}),
        ),
    ],
)
def test_condition_a_rejects_incomplete_or_duplicate_mutations(
    invalid_mutations: tuple[CacheHostileMutationFixture, ...],
) -> None:
    with pytest.raises(ValueError):
        compiler().compile_condition(
            condition_id=ConditionId.A,
            stable_prefix=stable_prefix(),
            turns=turns(),
            mutations=invalid_mutations,
        )


def test_compile_condition_rejects_missing_turn() -> None:
    with pytest.raises(ValueError, match="indexes 1 and 2"):
        compiler().compile_condition(
            condition_id=ConditionId.B,
            stable_prefix=stable_prefix(),
            turns=(turns()[0],),
        )


def test_compile_condition_rejects_cross_case_turns() -> None:
    cross_case_turns = (
        turns()[0],
        turns()[1].model_copy(update={"case_id": "case-002"}),
    )

    with pytest.raises(ValueError, match="same case"):
        compiler().compile_condition(
            condition_id=ConditionId.B,
            stable_prefix=stable_prefix(),
            turns=cross_case_turns,
        )
