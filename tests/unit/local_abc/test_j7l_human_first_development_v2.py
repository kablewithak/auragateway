from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.j7l_human_first_development_v2 import (
    J7LHumanFirstDevelopmentCaseSetV2,
    J7LHumanFirstDevelopmentCaseV2,
    J7LHumanFirstDevelopmentPolicyV2,
    J7LNoveltyPolicyV2,
)
from auragateway.contracts.quality_development_evaluation_v1 import J7LCaseFamily
from auragateway.local_abc import j7l_human_first_development_v2 as subject


def _positive_labels_for_fail_case(fail_index: int) -> tuple[EpisodeFailureLabel, ...]:
    labels = tuple(EpisodeFailureLabel)
    first = labels[(fail_index * 2) % len(labels)]
    second = labels[(fail_index * 2 + 1) % len(labels)]
    return (first, second)


def _near_miss_map() -> dict[int, tuple[EpisodeFailureLabel, ...]]:
    labels = tuple(EpisodeFailureLabel)
    indices = tuple(range(36, 48))
    assigned: dict[int, list[EpisodeFailureLabel]] = defaultdict(list)

    for _ in range(2):
        for label_index, label in enumerate(labels):
            start = label_index % len(indices)
            for offset in range(len(indices)):
                case_index = indices[(start + offset) % len(indices)]
                if label in assigned[case_index]:
                    continue
                assigned[case_index].append(label)
                break
            else:
                raise AssertionError("unable to place near-miss label target")

    return {case_index: tuple(labels_) for case_index, labels_ in assigned.items()}


def _case_set() -> J7LHumanFirstDevelopmentCaseSetV2:
    near_miss = _near_miss_map()
    criteria = tuple(RubricCriterion)
    cases: list[J7LHumanFirstDevelopmentCaseV2] = []

    for case_index in range(48):
        family = tuple(J7LCaseFamily)[case_index // 12]

        intended_labels: tuple[EpisodeFailureLabel, ...] = ()
        if family is J7LCaseFamily.CLEAR_FAILURE:
            intended_labels = _positive_labels_for_fail_case(case_index - 12)
        if family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE and case_index < 35:
            intended_labels = _positive_labels_for_fail_case(case_index - 12)

        scores = {
            criterion: 2 + ((case_index + criterion_index) % 3)
            for criterion_index, criterion in enumerate(criteria)
        }

        if intended_labels:
            scores[RubricCriterion.TASK_CORRECTNESS] = 1

        if not intended_labels:
            while sum(scores.values()) < 21:
                for criterion in criteria:
                    if scores[criterion] < 4:
                        scores[criterion] += 1
                        break

        verdict = ReviewVerdict.FAIL if intended_labels else ReviewVerdict.PASS

        cases.append(
            J7LHumanFirstDevelopmentCaseV2(
                case_id=f"j7l-v2-dev-{case_index + 1:03d}",
                case_index=case_index,
                family=family,
                reviewer_safe_state={
                    "visible_case": {
                        "prompt": f"fresh independent request {case_index}",
                        "evidence": [
                            f"source alpha {case_index}",
                            f"source beta {case_index * 17}",
                        ],
                        "candidate": f"fresh candidate response {case_index * 31}",
                    }
                },
                intended_criterion_scores=scores,
                intended_failure_labels=intended_labels,
                near_miss_label_targets=near_miss.get(case_index, ()),
                intended_verdict=verdict,
                terminal_action_evidence_material=(
                    family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE and case_index < 32
                ),
                authoring_notes="Synthetic authoring note used only for deterministic unit tests.",
            )
        )

    return J7LHumanFirstDevelopmentCaseSetV2(cases=tuple(cases))


def test_policy_is_single_human_development_only() -> None:
    policy = J7LHumanFirstDevelopmentPolicyV2()

    assert policy.case_count == 48
    assert policy.family_case_count == 12
    assert policy.single_human_development_reference is True
    assert policy.independent_qualification_claim_permitted is False
    assert policy.distinct_human_remediation_v2_dormant is True
    assert policy.provider_requests_authorized is False
    assert policy.jev_requests_authorized is False
    assert policy.j7m_qualification_claim_permitted is False


def test_case_namespace_rejects_historical_id() -> None:
    case = _case_set().cases[0]
    payload = case.model_dump(mode="json")
    payload["case_id"] = "j7l-dev-001"

    with pytest.raises(ValidationError):
        J7LHumanFirstDevelopmentCaseV2.model_validate(payload)


def test_reviewer_safe_state_rejects_hidden_target_key() -> None:
    case = _case_set().cases[0]
    payload = case.model_dump(mode="json")
    payload["reviewer_safe_state"]["intended_verdict"] = "pass"

    with pytest.raises(ValidationError, match="forbidden keys"):
        J7LHumanFirstDevelopmentCaseV2.model_validate(payload)


def test_authoring_coverage_satisfies_frozen_requirements() -> None:
    receipt = subject._authoring_coverage(_case_set())

    assert receipt.case_count == 48
    assert receipt.intended_pass_count >= 16
    assert receipt.intended_fail_count >= 16
    assert receipt.minimum_positive_support_observed >= 2
    assert receipt.minimum_near_miss_support_observed >= 2
    assert receipt.minimum_distinct_scores_observed >= 3
    assert receipt.minimum_low_scores_observed >= 4
    assert receipt.minimum_high_scores_observed >= 4
    assert receipt.terminal_material_evidence_case_count >= 8


def test_similarity_is_one_for_identical_state() -> None:
    state = {"visible_case": {"prompt": "same", "candidate": "same"}}

    assert subject._pair_similarity(state, state) == 1.0


def test_similarity_normalization_ignores_case_and_whitespace() -> None:
    left = {"visible_case": {"prompt": "Alpha   Beta"}}
    right = {"VISIBLE_CASE": {"PROMPT": "alpha beta"}}

    assert subject._pair_similarity(left, right) == 1.0


def test_novelty_policy_requires_pre_population_threshold() -> None:
    policy = J7LNoveltyPolicyV2(
        historical_similarity_profile_sha256="a" * 64,
        maximum_pair_similarity_allowed=0.8,
    )

    assert policy.threshold_selected_before_new_population_read is True
    assert policy.new_population_read_at_policy_freeze is False


def test_write_once_rejects_mutation(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"

    assert subject._write_once(path, b'{"value":1}\n') is True
    assert subject._write_once(path, b'{"value":1}\n') is False

    with pytest.raises(subject.J7LHumanFirstV2Error, match="differs from expected bytes"):
        subject._write_once(path, b'{"value":2}\n')
