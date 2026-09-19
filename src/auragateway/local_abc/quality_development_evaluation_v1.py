"""Deterministic J7L development-evaluation prerequisite and coverage validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Never

from pydantic import ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality_development_evaluation_v1 import (
    EXPECTED_CONSTITUTION_SHA256,
    EXPECTED_HUMAN_PROJECTION_SHA256,
    EXPECTED_MODEL_PROJECTION_SHA256,
    J7LAuthoritativeHumanTruthSetV1,
    J7LCaseFamily,
    J7LCoverageReceiptV1,
    J7LDevelopmentCaseSetV1,
    J7LDevelopmentConstitutionV1,
    J7LPrerequisiteReceiptV1,
)
from auragateway.local_abc import quality_semantic_projection_v1 as projection

CONSTITUTION_PATH = Path("docs/benchmark/AuraGateway_J7L_Development_Evaluation_Constitution_v1.md")


class J7LDevelopmentEvaluationError(RuntimeError):
    """Fail-closed J7L development-evaluation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise J7LDevelopmentEvaluationError(
            "J7L_DEVELOPMENT_EVALUATION_ARGUMENT_ERROR",
            message,
        )


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_constitution() -> J7LDevelopmentConstitutionV1:
    """Build the machine-readable J7L development constitution."""

    return J7LDevelopmentConstitutionV1()


def verify_prerequisites(repo_root: Path) -> J7LPrerequisiteReceiptV1:
    """Verify the accepted J7K semantic boundary and exact J7L constitution."""

    root = repo_root.resolve()
    constitution_path = root / CONSTITUTION_PATH

    if not constitution_path.is_file() or constitution_path.is_symlink():
        raise J7LDevelopmentEvaluationError(
            "J7L_CONSTITUTION_MISSING",
            "J7L development constitution is missing or unsafe",
        )

    constitution_sha256 = sha256_bytes(constitution_path.read_bytes())
    if constitution_sha256 != EXPECTED_CONSTITUTION_SHA256:
        raise J7LDevelopmentEvaluationError(
            "J7L_CONSTITUTION_BYTES_DRIFT",
            "J7L development constitution bytes drifted",
        )

    parity = projection.verify_materialized_projections(root)

    if parity.human_projection_sha256 != EXPECTED_HUMAN_PROJECTION_SHA256:
        raise J7LDevelopmentEvaluationError(
            "J7L_HUMAN_PROJECTION_IDENTITY_DRIFT",
            "J7K human semantic projection identity drifted",
        )

    if parity.model_projection_sha256 != EXPECTED_MODEL_PROJECTION_SHA256:
        raise J7LDevelopmentEvaluationError(
            "J7L_MODEL_PROJECTION_IDENTITY_DRIFT",
            "J7K model semantic projection identity drifted",
        )

    if not parity.canonical_semantic_parity:
        raise J7LDevelopmentEvaluationError(
            "J7L_J7K_SEMANTIC_PARITY_MISSING",
            "J7K canonical semantic parity is not established",
        )

    parity_path = root / projection.PARITY_RECEIPT_PATH
    parity_receipt_file_sha256 = sha256_bytes(parity_path.read_bytes())

    return J7LPrerequisiteReceiptV1(
        j7k_parity_receipt_file_sha256=parity_receipt_file_sha256,
    )


def validate_case_set(case_set: J7LDevelopmentCaseSetV1) -> dict[str, object]:
    """Return a deterministic metadata-only receipt for a frozen 48-case set."""

    family_counts = Counter(case.family.value for case in case_set.cases)
    return {
        "status": "J7L_DEVELOPMENT_CASE_SET_VALID",
        "case_count": len(case_set.cases),
        "family_counts": {family.value: family_counts[family.value] for family in J7LCaseFamily},
        "terminal_material_evidence_case_count": sum(
            case.family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
            and case.terminal_action_evidence_material
            for case in case_set.cases
        ),
        "provider_requests_performed": 0,
        "model_reveal_performed": False,
        "next_gate": "COMPLETE_AND_FREEZE_J7L_HUMAN_AUTHORITY",
    }


def validate_human_truth_coverage(
    case_set: J7LDevelopmentCaseSetV1,
    truth_set: J7LAuthoritativeHumanTruthSetV1,
) -> J7LCoverageReceiptV1:
    """Verify pre-model human truth completeness and required development coverage."""

    cases_by_id = {case.case_id: case for case in case_set.cases}
    truth_by_id = {case.case_id: case for case in truth_set.cases}

    if set(cases_by_id) != set(truth_by_id):
        raise J7LDevelopmentEvaluationError(
            "J7L_HUMAN_TRUTH_CASE_IDENTITY_DRIFT",
            "J7L human truth does not cover the exact frozen case set",
        )

    secondary_count = 0
    positive_support = Counter({label: 0 for label in EpisodeFailureLabel})
    near_miss_negative_support = Counter({label: 0 for label in EpisodeFailureLabel})
    criterion_values: dict[RubricCriterion, list[int]] = {
        criterion: [] for criterion in RubricCriterion
    }

    for case_id in sorted(cases_by_id):
        case = cases_by_id[case_id]
        truth = truth_by_id[case_id]

        expected_secondary = case.family in {
            J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE,
            J7LCaseFamily.ONTOLOGY_NEAR_MISS,
        }
        if truth.secondary_review_required != expected_secondary:
            raise J7LDevelopmentEvaluationError(
                "J7L_SECONDARY_SCHEDULE_DRIFT",
                "J7L human truth differs from the frozen 24-case secondary schedule",
            )

        secondary_count += int(truth.secondary_review_required)

        authoritative_labels = set(truth.failure_labels)
        for label in authoritative_labels:
            positive_support[label] += 1

        for label in case.near_miss_label_targets:
            if label in authoritative_labels:
                raise J7LDevelopmentEvaluationError(
                    "J7L_NEAR_MISS_TARGET_BECAME_POSITIVE",
                    "authored J7L near-miss target is positive in authoritative human truth",
                )
            near_miss_negative_support[label] += 1

        for criterion in RubricCriterion:
            criterion_values[criterion].append(truth.criterion_scores[criterion])

    if secondary_count != 24:
        raise J7LDevelopmentEvaluationError(
            "J7L_SECONDARY_REVIEW_COUNT_DRIFT",
            "J7L secondary-review count must be exactly 24",
        )

    pass_count = sum(case.verdict is ReviewVerdict.PASS for case in truth_set.cases)
    fail_count = sum(case.verdict is ReviewVerdict.FAIL for case in truth_set.cases)

    if pass_count < 16 or fail_count < 16:
        raise J7LDevelopmentEvaluationError(
            "J7L_VERDICT_COVERAGE_INSUFFICIENT",
            "J7L requires at least 16 PASS and 16 FAIL authoritative cases",
        )

    minimum_positive_support = min(positive_support.values())
    if minimum_positive_support < 2:
        raise J7LDevelopmentEvaluationError(
            "J7L_FAILURE_LABEL_POSITIVE_SUPPORT_INSUFFICIENT",
            "every J7L failure label requires authoritative positive support >= 2",
        )

    minimum_near_miss_support = min(near_miss_negative_support.values())
    if minimum_near_miss_support < 2:
        raise J7LDevelopmentEvaluationError(
            "J7L_FAILURE_LABEL_NEAR_MISS_SUPPORT_INSUFFICIENT",
            "every J7L failure label requires explicit near-miss negative support >= 2",
        )

    distinct_counts = {
        criterion: len(set(scores)) for criterion, scores in criterion_values.items()
    }
    low_counts = {
        criterion: sum(score in {1, 2} for score in scores)
        for criterion, scores in criterion_values.items()
    }
    high_counts = {
        criterion: sum(score in {3, 4} for score in scores)
        for criterion, scores in criterion_values.items()
    }

    minimum_distinct_scores = min(distinct_counts.values())
    minimum_low_scores = min(low_counts.values())
    minimum_high_scores = min(high_counts.values())

    if minimum_distinct_scores < 3:
        raise J7LDevelopmentEvaluationError(
            "J7L_CRITERION_SCORE_VARIATION_INSUFFICIENT",
            "every J7L criterion requires at least three authoritative score values",
        )

    if minimum_low_scores < 4 or minimum_high_scores < 4:
        raise J7LDevelopmentEvaluationError(
            "J7L_CRITERION_SCORE_RANGE_SUPPORT_INSUFFICIENT",
            "every J7L criterion requires at least four low and four high observations",
        )

    terminal_material_count = sum(
        case.family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
        and case.terminal_action_evidence_material
        for case in case_set.cases
    )
    if terminal_material_count < 8:
        raise J7LDevelopmentEvaluationError(
            "J7L_TERMINAL_MATERIAL_EVIDENCE_SUPPORT_INSUFFICIENT",
            "J7L requires at least eight terminal cases with material evidence",
        )

    return J7LCoverageReceiptV1(
        pass_count=pass_count,
        fail_count=fail_count,
        secondary_review_count=secondary_count,
        minimum_positive_support_observed=minimum_positive_support,
        minimum_near_miss_negative_support_observed=minimum_near_miss_support,
        minimum_distinct_scores_observed=minimum_distinct_scores,
        minimum_low_score_count_observed=minimum_low_scores,
        minimum_high_score_count_observed=minimum_high_scores,
        terminal_material_evidence_case_count=terminal_material_count,
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise J7LDevelopmentEvaluationError(
            "J7L_INPUT_FILE_MISSING",
            "required J7L input is missing or unsafe",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise J7LDevelopmentEvaluationError(
            "J7L_INPUT_JSON_INVALID",
            "required J7L input is not valid UTF-8 JSON",
        ) from error
    if not isinstance(value, dict):
        raise J7LDevelopmentEvaluationError(
            "J7L_INPUT_JSON_SHAPE_INVALID",
            "required J7L JSON root must be an object",
        )
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prerequisite = subparsers.add_parser("verify-prerequisites")
    prerequisite.add_argument("--repo-root", type=Path, required=True)

    cases = subparsers.add_parser("verify-cases")
    cases.add_argument("--case-set", type=Path, required=True)

    truth = subparsers.add_parser("verify-human-truth")
    truth.add_argument("--case-set", type=Path, required=True)
    truth.add_argument("--truth-set", type=Path, required=True)

    return parser


def main() -> int:
    args = _build_parser().parse_args()

    try:
        if args.command == "verify-prerequisites":
            result: object = verify_prerequisites(args.repo_root)
        elif args.command == "verify-cases":
            case_set = J7LDevelopmentCaseSetV1.model_validate(_read_json_object(args.case_set))
            result = validate_case_set(case_set)
        else:
            case_set = J7LDevelopmentCaseSetV1.model_validate(_read_json_object(args.case_set))
            truth_set = J7LAuthoritativeHumanTruthSetV1.model_validate(
                _read_json_object(args.truth_set)
            )
            result = validate_human_truth_coverage(case_set, truth_set)
    except (
        J7LDevelopmentEvaluationError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, J7LDevelopmentEvaluationError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "J7L_TYPED_VALIDATION_FAILED"
            message = "J7L typed development-evaluation validation failed"
        else:
            code = "J7L_LOCAL_IO_FAILED"
            message = "J7L local development-evaluation I/O failed"

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

    payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
