"""F0/F1 governance and fresh-case freeze for J7L human-first development V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Never

from pydantic import BaseModel, ValidationError

from auragateway.contracts.blinded_quality import ReviewVerdict, RubricCriterion
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.j7l_human_first_development_v2 import (
    EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256,
    EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256,
    EXPECTED_HISTORICAL_AUTHORING_CASE_SET_SHA256,
    EXPECTED_HUMAN_PROJECTION_SHA256,
    EXPECTED_MINIMUM_FAIL_COUNT,
    EXPECTED_MINIMUM_HIGH_SCORES_PER_CRITERION,
    EXPECTED_MINIMUM_LOW_SCORES_PER_CRITERION,
    EXPECTED_MINIMUM_NEAR_MISS_SUPPORT_PER_LABEL,
    EXPECTED_MINIMUM_PASS_COUNT,
    EXPECTED_MINIMUM_POSITIVE_SUPPORT_PER_LABEL,
    EXPECTED_MINIMUM_TERMINAL_MATERIAL_CASES,
    EXPECTED_SEMANTIC_REGISTRY_SHA256,
    FORBIDDEN_REVIEWER_SAFE_KEYS,
    J7LAuthoringCoverageReceiptV2,
    J7LCaseSetFreezeReceiptV2,
    J7LHistoricalDispositionV2,
    J7LHistoricalSimilarityProfileV2,
    J7LHumanFirstDevelopmentCaseSetV2,
    J7LNoveltyPolicyV2,
    J7LNoveltyReceiptV2,
    J7LReviewerExportV2,
    J7LReviewScheduleEntryV2,
    J7LReviewScheduleV2,
    J7LVisibleReviewItemV2,
)
from auragateway.contracts.quality_development_evaluation_v1 import (
    J7LCaseFamily,
    J7LDevelopmentCaseSetV1,
)
from auragateway.local_abc import (
    j7l_audited_adjudicated_development_reference_queue_v1 as contaminated_v1,
)
from auragateway.local_abc import j7l_reference_human_audit_comparison_v1 as predecessor
from auragateway.local_abc import quality_development_case_freeze_v1 as historical_freeze
from auragateway.local_abc import quality_semantic_projection_v1 as semantic_projection

ROOT = Path(".local/auragateway/j7l-human-first-development-v2")
GOVERNANCE_ROOT = ROOT / "governance"
HISTORICAL_DISPOSITION_PATH = GOVERNANCE_ROOT / "historical_disposition.json"
HISTORICAL_SIMILARITY_PROFILE_PATH = GOVERNANCE_ROOT / "historical_similarity_profile.json"
NOVELTY_POLICY_PATH = GOVERNANCE_ROOT / "novelty_policy.json"

AUTHORING_ROOT = ROOT / "authoring"
AUTHORING_CASE_SET_PATH = AUTHORING_ROOT / "case-set-v2.json"

REVIEW_ROOT = ROOT / "review"
REVIEW_SCHEDULE_PATH = REVIEW_ROOT / "review-schedule-v2.json"
PRIMARY_EXPORT_PATH = REVIEW_ROOT / "primary-reviewer-export-v2.json"

PUBLIC_FREEZE_PATH = Path(
    "data/evals/quality/j7l-human-first-development-v2/case-set-freeze-v2.json"
)

DISTINCT_HUMAN_REMEDIATION_ROOT = Path(".local/auragateway/j7l-human-review-remediation-v2")


_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_WHITESPACE_RE = re.compile(r"\s+")


class J7LHumanFirstV2Error(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise J7LHumanFirstV2Error("J7L_V2_ARGUMENT_ERROR", message)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise J7LHumanFirstV2Error(
            "J7L_V2_FILE_MISSING",
            f"required J7L V2 input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_JSON_INVALID",
            f"J7L V2 input is not valid UTF-8 JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise J7LHumanFirstV2Error(
            "J7L_V2_JSON_SHAPE_INVALID",
            f"J7L V2 input root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise J7LHumanFirstV2Error(
                "J7L_V2_OUTPUT_PATH_UNSAFE",
                "J7L V2 output path is unsafe",
            )
        if path.read_bytes() != payload:
            raise J7LHumanFirstV2Error(
                "J7L_V2_APPEND_ONLY_CONFLICT",
                "existing J7L V2 output differs from expected bytes",
            )
        return False

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise J7LHumanFirstV2Error(
            "J7L_V2_TEMP_RESIDUE",
            "J7L V2 temporary output already exists",
        )
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return True


def _verify_exact(path: Path, payload: bytes) -> None:
    if not path.is_file() or path.is_symlink():
        raise J7LHumanFirstV2Error(
            "J7L_V2_ARTIFACT_MISSING",
            f"required J7L V2 artifact is missing or unsafe: {path.as_posix()}",
        )
    if path.read_bytes() != payload:
        raise J7LHumanFirstV2Error(
            "J7L_V2_ARTIFACT_BYTES_DRIFT",
            f"J7L V2 artifact bytes drifted: {path.as_posix()}",
        )


def _walk_keys(value: object) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    if isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return tuple(keys)


def _assert_reviewer_safe(value: object) -> None:
    leaked = sorted(set(_walk_keys(value)) & FORBIDDEN_REVIEWER_SAFE_KEYS)
    if leaked:
        raise J7LHumanFirstV2Error(
            "J7L_V2_REVIEWER_EXPORT_AUTHORING_METADATA_LEAK",
            "reviewer-visible payload contains authoring-only keys: " + ",".join(leaked),
        )


def _historical_disposition(repo_root: Path) -> J7LHistoricalDispositionV2:
    root = repo_root.resolve()

    audit_path = root / predecessor.AUDIT_RESULT_PATH
    if _sha256_file(audit_path) != EXPECTED_FAILED_V3_AUDIT_RESULT_SHA256:
        raise J7LHumanFirstV2Error(
            "J7L_V2_FAILED_V3_AUDIT_IDENTITY_DRIFT",
            "failed V3 audit identity drifted",
        )

    try:
        _, freeze_sha256 = predecessor._load_and_validate_freeze(root)
    except predecessor.ReferenceAuditComparisonError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_HUMAN_FREEZE_INVALID",
            "historical 28-case human freeze no longer validates",
        ) from error
    if freeze_sha256 != EXPECTED_FAILED_V3_HUMAN_FREEZE_SHA256:
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_HUMAN_FREEZE_IDENTITY_DRIFT",
            "historical 28-case human-freeze identity drifted",
        )

    try:
        queue = contaminated_v1.status(root)
    except contaminated_v1.SuccessorQueueError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_CONTAMINATED_V1_STATUS_INVALID",
            "contaminated V1 successor status cannot be validated",
        ) from error

    if (
        queue.successor_completed_assessment_count != 8
        or queue.total_completed_human_assessment_count != 36
        or queue.pending_successor_assessment_count != 12
        or queue.next_case_id != "j7l-dev-011"
    ):
        raise J7LHumanFirstV2Error(
            "J7L_V2_CONTAMINATED_V1_STATE_DRIFT",
            "contaminated V1 successor is not at the frozen incident state",
        )

    distinct_root = root / DISTINCT_HUMAN_REMEDIATION_ROOT
    if distinct_root.exists():
        raise J7LHumanFirstV2Error(
            "J7L_V2_DISTINCT_HUMAN_REMEDIATION_ALREADY_INITIALIZED",
            "distinct-human remediation V2 local root exists; human-first V2 assumes it is dormant",
        )

    required_code = (
        root / "src/auragateway/contracts/j7l_human_review_remediation_v2.py",
        root / "src/auragateway/local_abc/j7l_human_review_remediation_queue_v2.py",
    )
    if any(not path.is_file() or path.is_symlink() for path in required_code):
        raise J7LHumanFirstV2Error(
            "J7L_V2_DISTINCT_HUMAN_REMEDIATION_CODE_MISSING",
            "merged distinct-human remediation V2 code is missing",
        )

    return J7LHistoricalDispositionV2()


def check_history(repo_root: Path) -> J7LHistoricalDispositionV2:
    return _historical_disposition(repo_root)


def lock_history(repo_root: Path) -> J7LHistoricalDispositionV2:
    root = repo_root.resolve()
    disposition = _historical_disposition(root)
    _write_once(
        root / HISTORICAL_DISPOSITION_PATH,
        _canonical_bytes(disposition.model_dump(mode="json")),
    )
    return disposition


def _normalize_string(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def _normalize_value(value: object) -> object:
    if isinstance(value, str):
        return _normalize_string(value)
    if isinstance(value, dict):
        return {
            _normalize_string(str(key)): _normalize_value(child) for key, child in value.items()
        }
    if isinstance(value, list):
        return [_normalize_value(child) for child in value]
    return value


def _normalized_state_text(value: object) -> str:
    return _canonical_json(_normalize_value(value))


def _token_jaccard(left: str, right: str) -> float:
    left_tokens = set(_TOKEN_RE.findall(left))
    right_tokens = set(_TOKEN_RE.findall(right))
    union = left_tokens | right_tokens
    if not union:
        return 1.0
    return len(left_tokens & right_tokens) / len(union)


def _pair_similarity(left: object, right: object) -> float:
    left_text = _normalized_state_text(left)
    right_text = _normalized_state_text(right)
    sequence = SequenceMatcher(None, left_text, right_text, autojunk=False).ratio()
    token = _token_jaccard(left_text, right_text)
    return max(sequence, token)


def _nearest_rank(values: tuple[float, ...], percentile: int) -> float:
    if not values:
        raise J7LHumanFirstV2Error(
            "J7L_V2_SIMILARITY_PROFILE_EMPTY",
            "cannot compute percentile over an empty similarity set",
        )
    rank = max(1, math.ceil((percentile / 100) * len(values)))
    return values[rank - 1]


def _load_historical_case_set(root: Path) -> J7LDevelopmentCaseSetV1:
    path = root / historical_freeze.PROTECTED_AUTHORING_CASE_SET_PATH
    if _sha256_file(path) != EXPECTED_HISTORICAL_AUTHORING_CASE_SET_SHA256:
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_CASE_SET_IDENTITY_DRIFT",
            "historical J7L authoring case-set identity drifted",
        )
    try:
        return J7LDevelopmentCaseSetV1.model_validate(_read_json(path))
    except ValidationError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_CASE_SET_TYPED_INVALID",
            "historical J7L authoring case set failed typed validation",
        ) from error


def build_historical_similarity_profile(
    repo_root: Path,
) -> J7LHistoricalSimilarityProfileV2:
    root = repo_root.resolve()
    disposition = _historical_disposition(root)

    if (root / AUTHORING_CASE_SET_PATH).exists():
        raise J7LHumanFirstV2Error(
            "J7L_V2_NEW_POPULATION_ALREADY_IMPORTED",
            "historical similarity profile must freeze before new population import",
        )

    disposition_path = root / HISTORICAL_DISPOSITION_PATH
    _verify_exact(
        disposition_path,
        _canonical_bytes(disposition.model_dump(mode="json")),
    )

    historical = _load_historical_case_set(root)
    values: list[float] = []
    states = tuple(case.reviewer_safe_state for case in historical.cases)
    for left_index in range(len(states)):
        for right_index in range(left_index + 1, len(states)):
            values.append(_pair_similarity(states[left_index], states[right_index]))

    ordered = tuple(sorted(values))
    if len(ordered) != 1128:
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_PAIR_COUNT_DRIFT",
            "historical similarity pair count is not exactly 1128",
        )

    return J7LHistoricalSimilarityProfileV2(
        minimum_similarity=ordered[0],
        p50_similarity=_nearest_rank(ordered, 50),
        p90_similarity=_nearest_rank(ordered, 90),
        p95_similarity=_nearest_rank(ordered, 95),
        p99_similarity=_nearest_rank(ordered, 99),
        maximum_similarity=ordered[-1],
    )


def profile_history(repo_root: Path) -> J7LHistoricalSimilarityProfileV2:
    root = repo_root.resolve()
    profile = build_historical_similarity_profile(root)
    _write_once(
        root / HISTORICAL_SIMILARITY_PROFILE_PATH,
        _canonical_bytes(profile.model_dump(mode="json")),
    )
    return profile


def freeze_novelty_policy(
    repo_root: Path,
    maximum_similarity: float,
) -> J7LNoveltyPolicyV2:
    root = repo_root.resolve()

    if (root / AUTHORING_CASE_SET_PATH).exists():
        raise J7LHumanFirstV2Error(
            "J7L_V2_NEW_POPULATION_ALREADY_IMPORTED",
            "novelty policy must freeze before new population import",
        )

    profile = build_historical_similarity_profile(root)
    profile_path = root / HISTORICAL_SIMILARITY_PROFILE_PATH
    _verify_exact(
        profile_path,
        _canonical_bytes(profile.model_dump(mode="json")),
    )

    try:
        policy = J7LNoveltyPolicyV2(
            historical_similarity_profile_sha256=_sha256_file(profile_path),
            maximum_pair_similarity_allowed=maximum_similarity,
        )
    except ValidationError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_NOVELTY_POLICY_INVALID",
            "novelty threshold failed typed validation",
        ) from error

    _write_once(
        root / NOVELTY_POLICY_PATH,
        _canonical_bytes(policy.model_dump(mode="json")),
    )
    return policy


def _load_novelty_policy(root: Path) -> J7LNoveltyPolicyV2:
    try:
        return J7LNoveltyPolicyV2.model_validate(_read_json(root / NOVELTY_POLICY_PATH))
    except ValidationError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_NOVELTY_POLICY_TYPED_INVALID",
            "frozen novelty policy failed typed validation",
        ) from error


def _authoring_coverage(
    case_set: J7LHumanFirstDevelopmentCaseSetV2,
) -> J7LAuthoringCoverageReceiptV2:
    family_counts = Counter(case.family for case in case_set.cases)
    verdict_counts = Counter(case.intended_verdict for case in case_set.cases)
    positive_counts = Counter(
        label for case in case_set.cases for label in case.intended_failure_labels
    )
    near_miss_counts = Counter(
        label for case in case_set.cases for label in case.near_miss_label_targets
    )

    minimum_positive = min(positive_counts[label] for label in EpisodeFailureLabel)
    minimum_near_miss = min(near_miss_counts[label] for label in EpisodeFailureLabel)

    distinct_counts: list[int] = []
    low_counts: list[int] = []
    high_counts: list[int] = []
    for criterion in RubricCriterion:
        scores = tuple(case.intended_criterion_scores[criterion] for case in case_set.cases)
        distinct_counts.append(len(set(scores)))
        low_counts.append(sum(score in {1, 2} for score in scores))
        high_counts.append(sum(score in {3, 4} for score in scores))

    terminal_material = sum(
        case.family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
        and case.terminal_action_evidence_material
        for case in case_set.cases
    )

    pass_count = verdict_counts[ReviewVerdict.PASS]
    fail_count = verdict_counts[ReviewVerdict.FAIL]

    if pass_count < EXPECTED_MINIMUM_PASS_COUNT:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_PASS_COVERAGE_INSUFFICIENT",
            "authoring population does not meet minimum intended PASS support",
        )
    if fail_count < EXPECTED_MINIMUM_FAIL_COUNT:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_FAIL_COVERAGE_INSUFFICIENT",
            "authoring population does not meet minimum intended FAIL support",
        )
    if minimum_positive < EXPECTED_MINIMUM_POSITIVE_SUPPORT_PER_LABEL:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_LABEL_POSITIVE_COVERAGE_INSUFFICIENT",
            "authoring population does not cover every failure label positively at least twice",
        )
    if minimum_near_miss < EXPECTED_MINIMUM_NEAR_MISS_SUPPORT_PER_LABEL:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_LABEL_NEAR_MISS_COVERAGE_INSUFFICIENT",
            "authoring population does not cover every failure label as a near miss at least twice",
        )
    if min(distinct_counts) < 3:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_CRITERION_DIVERSITY_INSUFFICIENT",
            "authoring population does not provide at least three score values per criterion",
        )
    if min(low_counts) < EXPECTED_MINIMUM_LOW_SCORES_PER_CRITERION:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_LOW_SCORE_COVERAGE_INSUFFICIENT",
            "authoring population does not provide enough low-score targets per criterion",
        )
    if min(high_counts) < EXPECTED_MINIMUM_HIGH_SCORES_PER_CRITERION:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_HIGH_SCORE_COVERAGE_INSUFFICIENT",
            "authoring population does not provide enough high-score targets per criterion",
        )
    if terminal_material < EXPECTED_MINIMUM_TERMINAL_MATERIAL_CASES:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_TERMINAL_EVIDENCE_COVERAGE_INSUFFICIENT",
            "authoring population does not provide enough terminal material-evidence cases",
        )

    return J7LAuthoringCoverageReceiptV2(
        family_counts={family: family_counts[family] for family in J7LCaseFamily},
        intended_pass_count=pass_count,
        intended_fail_count=fail_count,
        minimum_positive_support_observed=minimum_positive,
        minimum_near_miss_support_observed=minimum_near_miss,
        minimum_distinct_scores_observed=min(distinct_counts),
        minimum_low_scores_observed=min(low_counts),
        minimum_high_scores_observed=min(high_counts),
        terminal_material_evidence_case_count=terminal_material,
    )


def _novelty_receipt(
    root: Path,
    case_set: J7LHumanFirstDevelopmentCaseSetV2,
    policy: J7LNoveltyPolicyV2,
) -> J7LNoveltyReceiptV2:
    historical = _load_historical_case_set(root)

    historical_states = tuple(case.reviewer_safe_state for case in historical.cases)
    new_states = tuple(case.reviewer_safe_state for case in case_set.cases)

    historical_canonical = {_canonical_json(state) for state in historical_states}
    new_canonical = tuple(_canonical_json(state) for state in new_states)
    if len(new_canonical) != len(set(new_canonical)):
        raise J7LHumanFirstV2Error(
            "J7L_V2_WITHIN_NEW_EXACT_DUPLICATE",
            "new J7L V2 population contains exact duplicate reviewer-safe states",
        )
    if historical_canonical.intersection(new_canonical):
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_EXACT_DUPLICATE",
            "new J7L V2 population exactly reuses a historical reviewer-safe state",
        )

    historical_normalized = {_normalized_state_text(state) for state in historical_states}
    new_normalized = tuple(_normalized_state_text(state) for state in new_states)
    if len(new_normalized) != len(set(new_normalized)):
        raise J7LHumanFirstV2Error(
            "J7L_V2_WITHIN_NEW_NORMALIZED_DUPLICATE",
            "new J7L V2 population contains normalized duplicate reviewer-safe states",
        )
    if historical_normalized.intersection(new_normalized):
        raise J7LHumanFirstV2Error(
            "J7L_V2_HISTORICAL_NORMALIZED_DUPLICATE",
            "new J7L V2 population normalizes to a historical reviewer-safe state",
        )

    new_to_historical: list[float] = []
    for new_state in new_states:
        for historical_state in historical_states:
            new_to_historical.append(_pair_similarity(new_state, historical_state))

    within_new: list[float] = []
    for left_index in range(len(new_states)):
        for right_index in range(left_index + 1, len(new_states)):
            within_new.append(_pair_similarity(new_states[left_index], new_states[right_index]))

    maximum_new_to_historical = max(new_to_historical)
    maximum_within_new = max(within_new)
    maximum_observed = max(maximum_new_to_historical, maximum_within_new)

    if maximum_observed > policy.maximum_pair_similarity_allowed:
        raise J7LHumanFirstV2Error(
            "J7L_V2_NOVELTY_THRESHOLD_EXCEEDED",
            (
                "new J7L V2 population exceeds the pre-frozen similarity threshold; "
                f"observed={maximum_observed:.6f}"
            ),
        )

    return J7LNoveltyReceiptV2(
        maximum_new_to_historical_similarity=maximum_new_to_historical,
        maximum_within_new_similarity=maximum_within_new,
    )


def _load_external_authoring(path: Path) -> J7LHumanFirstDevelopmentCaseSetV2:
    try:
        return J7LHumanFirstDevelopmentCaseSetV2.model_validate(_read_json(path))
    except ValidationError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_CASE_SET_TYPED_INVALID",
            "sealed authoring population failed typed validation",
        ) from error


def import_authoring(
    repo_root: Path,
    input_file: Path,
) -> dict[str, object]:
    root = repo_root.resolve()
    _historical_disposition(root)

    profile = build_historical_similarity_profile(root)
    _verify_exact(
        root / HISTORICAL_SIMILARITY_PROFILE_PATH,
        _canonical_bytes(profile.model_dump(mode="json")),
    )

    policy = _load_novelty_policy(root)
    selected = input_file if input_file.is_absolute() else Path.cwd() / input_file
    selected = selected.resolve()

    if not selected.is_file() or selected.is_symlink():
        raise J7LHumanFirstV2Error(
            "J7L_V2_AUTHORING_IMPORT_MISSING",
            "sealed authoring JSON is missing or unsafe",
        )

    case_set = _load_external_authoring(selected)
    coverage = _authoring_coverage(case_set)
    novelty = _novelty_receipt(root, case_set, policy)

    payload = _canonical_bytes(case_set.model_dump(mode="json"))
    created = _write_once(root / AUTHORING_CASE_SET_PATH, payload)

    return {
        "status": "J7L_V2_SEALED_AUTHORING_IMPORTED",
        "created": created,
        "authoring_case_set_sha256": _sha256_bytes(payload),
        "authoring_coverage_status": coverage.status,
        "novelty_status": novelty.status,
        "maximum_new_to_historical_similarity": novelty.maximum_new_to_historical_similarity,
        "maximum_within_new_similarity": novelty.maximum_within_new_similarity,
        "human_reviewer_inspected_hidden_authoring_payload": False,
        "provider_requests_performed": 0,
        "jev_requests_performed": 0,
        "next_gate": "MATERIALIZE_REVIEWER_SAFE_EXPORT",
    }


def _load_imported_authoring(root: Path) -> J7LHumanFirstDevelopmentCaseSetV2:
    try:
        return J7LHumanFirstDevelopmentCaseSetV2.model_validate(
            _read_json(root / AUTHORING_CASE_SET_PATH)
        )
    except ValidationError as error:
        raise J7LHumanFirstV2Error(
            "J7L_V2_IMPORTED_AUTHORING_TYPED_INVALID",
            "imported authoring population failed typed validation",
        ) from error


def _review_item_id(state: object) -> str:
    return _sha256_bytes(_canonical_json(state).encode("utf-8"))


def _assignment_id(review_item_id: str) -> str:
    subject = f"auragateway-j7l-v2|primary|{review_item_id}".encode()
    return "review-" + _sha256_bytes(subject)[:24]


def _reviewer_instruction() -> str:
    return (
        "Use only the visible reviewer-safe state and the included J7K human semantic "
        "projection. Independently score all seven criteria and evaluate all failure labels "
        "from those semantics. Do not inspect the sealed authoring case set, hidden authoring "
        "targets, family metadata, historical J7L cases, model judgments, Jev outputs, or "
        "evaluator results. Do not ask an AI assistant to choose scores, labels, evidence, "
        "verdicts, or rationale before you have independently made the human judgment."
    )


def _build_review_artifacts(
    repo_root: Path,
) -> tuple[
    J7LReviewScheduleV2,
    J7LReviewerExportV2,
    J7LCaseSetFreezeReceiptV2,
]:
    root = repo_root.resolve()
    case_set = _load_imported_authoring(root)
    _authoring_coverage(case_set)
    policy = _load_novelty_policy(root)
    _novelty_receipt(root, case_set, policy)

    human_projection, _, parity = semantic_projection.build_projection_bundle(root)
    if not parity.canonical_semantic_parity:
        raise J7LHumanFirstV2Error(
            "J7L_V2_J7K_SEMANTIC_PARITY_MISSING",
            "J7K canonical semantic parity is not established",
        )
    if parity.human_projection_sha256 != EXPECTED_HUMAN_PROJECTION_SHA256:
        raise J7LHumanFirstV2Error(
            "J7L_V2_HUMAN_PROJECTION_IDENTITY_DRIFT",
            "J7K human semantic projection identity drifted",
        )
    if parity.source_registry_sha256 != EXPECTED_SEMANTIC_REGISTRY_SHA256:
        raise J7LHumanFirstV2Error(
            "J7L_V2_SEMANTIC_REGISTRY_IDENTITY_DRIFT",
            "J7K semantic registry identity drifted",
        )

    entries: list[J7LReviewScheduleEntryV2] = []
    visible: list[J7LVisibleReviewItemV2] = []
    inventory: list[dict[str, str]] = []

    for case in case_set.cases:
        safe_payload = case.reviewer_safe_state
        _assert_reviewer_safe(safe_payload)
        safe_bytes = _canonical_json(safe_payload).encode("utf-8")
        safe_sha256 = _sha256_bytes(safe_bytes)
        review_item_id = _review_item_id(safe_payload)
        assignment_id = _assignment_id(review_item_id)

        entries.append(
            J7LReviewScheduleEntryV2(
                case_id=case.case_id,
                case_index=case.case_index,
                family=case.family,
                review_item_id=review_item_id,
                reviewer_safe_state_sha256=safe_sha256,
                primary_assignment_id=assignment_id,
            )
        )
        visible.append(
            J7LVisibleReviewItemV2(
                assignment_id=assignment_id,
                review_item_id=review_item_id,
                reviewer_safe_state_sha256=safe_sha256,
                reviewer_safe_state=safe_payload,
            )
        )
        inventory.append(
            {
                "review_item_id": review_item_id,
                "reviewer_safe_state_sha256": safe_sha256,
            }
        )

    schedule = J7LReviewScheduleV2(entries=tuple(entries))
    export = J7LReviewerExportV2(
        semantic_projection=human_projection,
        reviewer_instruction=_reviewer_instruction(),
        items=tuple(visible),
    )
    _assert_reviewer_safe(export.model_dump(mode="json"))

    profile_path = root / HISTORICAL_SIMILARITY_PROFILE_PATH
    policy_path = root / NOVELTY_POLICY_PATH
    case_set_path = root / AUTHORING_CASE_SET_PATH

    receipt = J7LCaseSetFreezeReceiptV2(
        authoring_case_set_sha256=_sha256_file(case_set_path),
        historical_similarity_profile_sha256=_sha256_file(profile_path),
        novelty_policy_sha256=_sha256_file(policy_path),
        reviewer_safe_state_inventory_sha256=_sha256_bytes(
            _canonical_json(inventory).encode("utf-8")
        ),
        protected_schedule_sha256=_sha256_bytes(_canonical_bytes(schedule.model_dump(mode="json"))),
        protected_primary_export_sha256=_sha256_bytes(
            _canonical_bytes(export.model_dump(mode="json"))
        ),
        authoring_coverage_valid=True,
        novelty_valid=True,
    )
    return schedule, export, receipt


def materialize_review(repo_root: Path) -> J7LCaseSetFreezeReceiptV2:
    root = repo_root.resolve()
    schedule, export, receipt = _build_review_artifacts(root)

    _write_once(
        root / REVIEW_SCHEDULE_PATH,
        _canonical_bytes(schedule.model_dump(mode="json")),
    )
    _write_once(
        root / PRIMARY_EXPORT_PATH,
        _canonical_bytes(export.model_dump(mode="json")),
    )
    _write_once(
        root / PUBLIC_FREEZE_PATH,
        _canonical_bytes(receipt.model_dump(mode="json")),
    )
    return verify_review(root)


def verify_review(repo_root: Path) -> J7LCaseSetFreezeReceiptV2:
    root = repo_root.resolve()
    schedule, export, receipt = _build_review_artifacts(root)
    _verify_exact(
        root / REVIEW_SCHEDULE_PATH,
        _canonical_bytes(schedule.model_dump(mode="json")),
    )
    _verify_exact(
        root / PRIMARY_EXPORT_PATH,
        _canonical_bytes(export.model_dump(mode="json")),
    )
    _verify_exact(
        root / PUBLIC_FREEZE_PATH,
        _canonical_bytes(receipt.model_dump(mode="json")),
    )
    return receipt


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "check-history",
            "lock-history",
            "profile-history",
            "freeze-novelty",
            "import-authoring",
            "materialize-review",
            "verify-review",
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--maximum-similarity", type=float)
    parser.add_argument("--input-file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: BaseModel | dict[str, object]

    try:
        if args.command == "check-history":
            result = check_history(args.repo_root)
        elif args.command == "lock-history":
            result = lock_history(args.repo_root)
        elif args.command == "profile-history":
            result = profile_history(args.repo_root)
        elif args.command == "freeze-novelty":
            if args.maximum_similarity is None:
                raise J7LHumanFirstV2Error(
                    "J7L_V2_MAXIMUM_SIMILARITY_REQUIRED",
                    "freeze-novelty requires --maximum-similarity",
                )
            result = freeze_novelty_policy(
                args.repo_root,
                args.maximum_similarity,
            )
        elif args.command == "import-authoring":
            if args.input_file is None:
                raise J7LHumanFirstV2Error(
                    "J7L_V2_AUTHORING_INPUT_REQUIRED",
                    "import-authoring requires --input-file",
                )
            result = import_authoring(args.repo_root, args.input_file)
        elif args.command == "materialize-review":
            result = materialize_review(args.repo_root)
        else:
            result = verify_review(args.repo_root)
    except (
        J7LHumanFirstV2Error,
        predecessor.ReferenceAuditComparisonError,
        contaminated_v1.SuccessorQueueError,
        ValidationError,
        OSError,
    ) as error:
        if isinstance(error, J7LHumanFirstV2Error):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, predecessor.ReferenceAuditComparisonError):
            code = "J7L_V2_PREDECESSOR_AUDIT_INVALID"
            message = "historical predecessor audit evidence is invalid"
        elif isinstance(error, contaminated_v1.SuccessorQueueError):
            code = "J7L_V2_CONTAMINATED_PREDECESSOR_INVALID"
            message = "contaminated V1 predecessor evidence is invalid"
        elif isinstance(error, ValidationError):
            code = "J7L_V2_TYPED_VALIDATION_FAILED"
            message = "J7L human-first V2 typed validation failed"
        else:
            code = "J7L_V2_LOCAL_IO_FAILED"
            message = "J7L human-first V2 local I/O failed"

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

    output = result.model_dump(mode="json") if isinstance(result, BaseModel) else result

    print(
        json.dumps(
            output,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
