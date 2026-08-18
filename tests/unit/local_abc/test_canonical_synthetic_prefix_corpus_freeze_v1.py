from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auragateway.local_abc import canonical_synthetic_prefix_corpus_freeze_v1

freeze = canonical_synthetic_prefix_corpus_freeze_v1


@pytest.fixture
def candidate_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]

    for relative in (
        freeze.ADR_PATH,
        freeze.V1_CORPUS_PATH,
        freeze.V1_STATIC_RECEIPT_PATH,
        freeze.V2_CORPUS_PATH,
        freeze.V2_TUNING_RECEIPT_PATH,
        freeze.V2_STATIC_RECEIPT_PATH,
        freeze.HUMAN_REVIEW_PATH,
        freeze.FREEZE_RECORD_PATH,
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)

    return tmp_path


def test_exact_canonical_corpus_identity_and_static_contract(
    candidate_repo: Path,
) -> None:
    data, text = freeze.validate_corpus_bytes(candidate_repo)
    static_payload, _ = freeze.validate_v2_static(candidate_repo)
    candidate = freeze.mapping(
        static_payload.get("candidate"),
        "V2 candidate",
    )

    assert freeze.sha256_bytes(data) == freeze.EXPECTED_V2_CORPUS_SHA256
    assert len(text.split("\n\n")) == 10
    assert candidate["prompt_token_count"] == 899
    assert candidate["target_prompt_token_count_match"] is True
    assert candidate["duplicate_16gram_within_guardrail"] is True
    assert candidate["aligned_16_block_duplication_within_guardrail"] is True
    assert candidate["state"] == "STATIC_REPRESENTATION_ACCEPTANCE_CANDIDATE"


def test_v1_to_v2_deletion_only_lineage_is_bound(
    candidate_repo: Path,
) -> None:
    freeze.validate_v1_static(candidate_repo)
    tuning_payload, _ = freeze.validate_tuning(candidate_repo)

    intervention = freeze.mapping(
        tuning_payload.get("intervention"),
        "V2 tuning intervention",
    )

    assert intervention["method"] == "DELETION_ONLY_FULL_SENTENCE_BOUNDED_SEARCH"
    removed = freeze.integer_sequence(
        intervention.get("removed_sentence_ordinals"),
        "V2 removed sentence ordinals",
    )
    assert removed == (9, 29, 44, 49)
    assert intervention["new_text_added"] is False
    assert intervention["randomness_used"] is False


def test_human_review_user_acceptance_is_exact_byte_bound(
    candidate_repo: Path,
) -> None:
    _, tuning_sha256 = freeze.validate_tuning(candidate_repo)
    _, static_sha256 = freeze.validate_v2_static(candidate_repo)

    review = freeze.build_human_review(
        tuning_sha256,
        static_sha256,
    )

    rubric = freeze.mapping(review.get("rubric"), "human review rubric")
    acceptance = freeze.mapping(
        review.get("user_acceptance"),
        "human review acceptance",
    )
    claims = freeze.mapping(review.get("claims"), "human review claims")

    assert set(rubric.values()) == {"PASS"}
    assert acceptance["accepted"] is True
    assert acceptance["scope"] == "EXACT_CANDIDATE_V2_BYTES_ONLY"
    assert acceptance["accepted_sha256"] == freeze.EXPECTED_V2_CORPUS_SHA256
    assert claims["approved_for_corpus_freeze"] is True
    assert claims["c4_qualified"] is False
    assert claims["p5_requalified"] is False
    assert claims["p6_requalified"] is False
    assert claims["runtime_execution_authorized"] is False


def test_freeze_record_preserves_future_b_c_causal_contrast(
    candidate_repo: Path,
) -> None:
    tuning_payload, tuning_sha256 = freeze.validate_tuning(candidate_repo)
    static_payload, static_sha256 = freeze.validate_v2_static(candidate_repo)
    human_review = freeze.build_human_review(
        tuning_sha256,
        static_sha256,
    )
    human_sha256 = freeze.sha256_bytes(
        freeze.canonical_bytes(human_review),
    )

    record = freeze.build_freeze_record(
        tuning_payload,
        tuning_sha256,
        static_payload,
        static_sha256,
        human_sha256,
    )

    causal = freeze.mapping(
        record.get("future_causal_contract"),
        "future causal contract",
    )
    qualification = freeze.mapping(
        record.get("qualification_state"),
        "qualification state",
    )

    assert causal["b_and_c_must_share_canonical_corpus_identity"] is True
    assert causal["b_and_c_must_share_prefix_constructor_identity"] is True
    assert causal["worker_affinity_is_intended_b_to_c_intervention"] is True
    assert causal["control_plane_values_must_remain_outside_semantic_prefix"] is True
    assert qualification["canonical_corpus"] == "FROZEN"
    assert qualification["c4_behavioral_qualification"] == "NOT_QUALIFIED"
    assert qualification["p5"] == "NOT_REQUALIFIED"
    assert qualification["p6"] == "NOT_REQUALIFIED"


def test_freeze_record_is_execution_inert(
    candidate_repo: Path,
) -> None:
    tuning_payload, tuning_sha256 = freeze.validate_tuning(candidate_repo)
    static_payload, static_sha256 = freeze.validate_v2_static(candidate_repo)
    review = freeze.build_human_review(
        tuning_sha256,
        static_sha256,
    )

    record = freeze.build_freeze_record(
        tuning_payload,
        tuning_sha256,
        static_payload,
        static_sha256,
        freeze.sha256_bytes(freeze.canonical_bytes(review)),
    )
    authorization = freeze.mapping(
        record.get("authorization"),
        "authorization",
    )

    assert set(authorization.values()) == {False}


def test_generated_review_and_freeze_bytes_match_preserved_evidence(
    candidate_repo: Path,
) -> None:
    tuning_payload, tuning_sha256 = freeze.validate_tuning(candidate_repo)
    static_payload, static_sha256 = freeze.validate_v2_static(candidate_repo)

    review = freeze.build_human_review(
        tuning_sha256,
        static_sha256,
    )
    review_bytes = freeze.canonical_bytes(review)
    review_sha256 = freeze.sha256_bytes(review_bytes)

    record = freeze.build_freeze_record(
        tuning_payload,
        tuning_sha256,
        static_payload,
        static_sha256,
        review_sha256,
    )
    record_bytes = freeze.canonical_bytes(record)

    assert (candidate_repo / freeze.HUMAN_REVIEW_PATH).read_bytes() == review_bytes
    assert (candidate_repo / freeze.FREEZE_RECORD_PATH).read_bytes() == record_bytes


def test_corpus_byte_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    corpus = candidate_repo / freeze.V2_CORPUS_PATH
    corpus.write_bytes(corpus.read_bytes() + b"\n")

    with pytest.raises(freeze.FreezeError, match="identity drifted"):
        freeze.validate_corpus_bytes(candidate_repo)


def test_static_receipt_guardrail_drift_fails_closed(
    candidate_repo: Path,
) -> None:
    path = candidate_repo / freeze.V2_STATIC_RECEIPT_PATH
    payload = freeze.object_from(path)
    candidate = freeze.mapping(payload.get("candidate"), "candidate")
    candidate["duplicate_16gram_within_guardrail"] = False
    path.write_bytes(freeze.canonical_bytes(payload))

    with pytest.raises(freeze.FreezeError):
        freeze.validate_v2_static(candidate_repo)
