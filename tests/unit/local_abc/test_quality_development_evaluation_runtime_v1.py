from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import (
    J7LAuthoritativeHumanTruthSetV1,
    J7LAuthoritativeHumanTruthV1,
    J7LCaseFamily,
    J7LDevelopmentCaseSetV1,
    J7LDevelopmentCaseV1,
    J7LHumanAuthority,
)
from auragateway.local_abc import quality_development_evaluation_v1 as subject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _positive_labels_for_fail_case(fail_index: int) -> tuple[EpisodeFailureLabel, ...]:
    labels = tuple(EpisodeFailureLabel)
    first = labels[(fail_index * 2) % len(labels)]
    second = labels[(fail_index * 2 + 1) % len(labels)]
    return (first, second)


def _near_miss_assignment_map(
    positive_by_case: dict[int, tuple[EpisodeFailureLabel, ...]],
) -> dict[int, tuple[EpisodeFailureLabel, ...]]:
    labels = tuple(EpisodeFailureLabel)
    near_case_indices = tuple(range(36, 48))
    assigned: dict[int, list[EpisodeFailureLabel]] = defaultdict(list)

    for _ in range(2):
        for label_index, label in enumerate(labels):
            initial_slot = label_index % len(near_case_indices)
            for offset in range(len(near_case_indices)):
                case_index = near_case_indices[(initial_slot + offset) % len(near_case_indices)]
                if label in positive_by_case[case_index]:
                    continue
                if label in assigned[case_index]:
                    continue
                assigned[case_index].append(label)
                break
            else:
                raise AssertionError("unable to place near-miss label target")

    return {case_index: tuple(assigned[case_index]) for case_index in near_case_indices}


def _case_and_truth_sets() -> tuple[
    J7LDevelopmentCaseSetV1,
    J7LAuthoritativeHumanTruthSetV1,
]:
    positive_by_case: dict[int, tuple[EpisodeFailureLabel, ...]] = {}

    for case_index in range(48):
        if case_index < 16:
            positive_by_case[case_index] = ()
        else:
            positive_by_case[case_index] = _positive_labels_for_fail_case(case_index - 16)

    near_miss_by_case = _near_miss_assignment_map(positive_by_case)

    cases: list[J7LDevelopmentCaseV1] = []
    truth: list[J7LAuthoritativeHumanTruthV1] = []

    families = tuple(J7LCaseFamily)
    criteria = tuple(RubricCriterion)

    for case_index in range(48):
        family = families[case_index // 12]
        secondary_required = family in {
            J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE,
            J7LCaseFamily.ONTOLOGY_NEAR_MISS,
        }

        cases.append(
            J7LDevelopmentCaseV1(
                case_id=f"j7l-dev-{case_index + 1:03d}",
                case_index=case_index,
                family=family,
                reviewer_safe_state={
                    "visible_case": {
                        "prompt": f"fresh synthetic case {case_index}",
                        "response": "fresh synthetic candidate response",
                    }
                },
                positive_label_targets=positive_by_case[case_index],
                near_miss_label_targets=near_miss_by_case.get(case_index, ()),
                terminal_action_evidence_material=(
                    family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE and case_index < 32
                ),
            )
        )

        truth.append(
            J7LAuthoritativeHumanTruthV1(
                case_id=f"j7l-dev-{case_index + 1:03d}",
                authority=J7LHumanAuthority.PRIMARY,
                criterion_scores={
                    criterion: 1 + ((case_index + criterion_index) % 4)
                    for criterion_index, criterion in enumerate(criteria)
                },
                failure_labels=positive_by_case[case_index],
                verdict=(ReviewVerdict.PASS if case_index < 16 else ReviewVerdict.FAIL),
                secondary_review_required=secondary_required,
                secondary_review_complete=secondary_required,
                material_disagreement=False,
                adjudication_complete=False,
            )
        )

    return (
        J7LDevelopmentCaseSetV1(cases=tuple(cases)),
        J7LAuthoritativeHumanTruthSetV1(cases=tuple(truth)),
    )


def test_prerequisites_bind_exact_j7k_semantics_and_constitution() -> None:
    receipt = subject.verify_prerequisites(_repo_root())

    assert receipt.status == "J7L_DEVELOPMENT_PREREQUISITES_PASS"
    assert receipt.jev_request_performed is False
    assert receipt.network_access_performed is False
    assert receipt.deployment_threshold_selected is False
    assert receipt.human_truth_frozen is False
    assert receipt.next_gate == "AUTHOR_J7L_48_CASE_DEVELOPMENT_SET"


def test_passing_case_set_returns_expected_metadata() -> None:
    case_set, _ = _case_and_truth_sets()
    receipt = subject.validate_case_set(case_set)

    assert receipt["case_count"] == 48
    assert receipt["family_counts"] == {
        "ordinary_clean": 12,
        "clear_failure": 12,
        "terminal_non_substantive": 12,
        "ontology_near_miss": 12,
    }
    assert receipt["terminal_material_evidence_case_count"] == 8
    assert receipt["provider_requests_performed"] == 0


def test_human_truth_coverage_passes_before_model_reveal() -> None:
    case_set, truth_set = _case_and_truth_sets()
    receipt = subject.validate_human_truth_coverage(case_set, truth_set)

    assert receipt.status == "J7L_HUMAN_TRUTH_COVERAGE_PASS"
    assert receipt.case_count == 48
    assert receipt.pass_count == 16
    assert receipt.fail_count == 32
    assert receipt.secondary_review_count == 24
    assert receipt.minimum_positive_support_observed >= 2
    assert receipt.minimum_near_miss_negative_support_observed >= 2
    assert receipt.minimum_distinct_scores_observed == 4
    assert receipt.terminal_material_evidence_case_count == 8
    assert receipt.provider_requests_performed_before_freeze == 0


def test_human_truth_rejects_secondary_schedule_drift() -> None:
    case_set, truth_set = _case_and_truth_sets()
    payload = truth_set.model_dump(mode="json")

    terminal_case = payload["cases"][24]
    terminal_case["secondary_review_required"] = False
    terminal_case["secondary_review_complete"] = False

    drifted = J7LAuthoritativeHumanTruthSetV1.model_validate(payload)

    with pytest.raises(
        subject.J7LDevelopmentEvaluationError,
        match="secondary schedule",
    ):
        subject.validate_human_truth_coverage(case_set, drifted)


def test_human_truth_rejects_near_miss_target_that_becomes_positive() -> None:
    case_set, truth_set = _case_and_truth_sets()
    case_payload = case_set.model_dump(mode="json")
    truth_payload = truth_set.model_dump(mode="json")

    near_case = case_payload["cases"][36]
    target = near_case["near_miss_label_targets"][0]
    truth_payload["cases"][36]["failure_labels"].append(target)

    drifted_truth = J7LAuthoritativeHumanTruthSetV1.model_validate(truth_payload)

    with pytest.raises(
        subject.J7LDevelopmentEvaluationError,
        match="near-miss target",
    ):
        subject.validate_human_truth_coverage(case_set, drifted_truth)
