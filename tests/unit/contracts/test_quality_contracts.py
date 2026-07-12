from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.quality import (
    ClaimEvidence,
    DeterministicQualityResult,
    QualityCheckName,
    QualityCheckResult,
    QualityCheckStatus,
)

_SHA = "a" * 64


def test_claim_evidence_is_frozen_and_rejects_duplicate_citations() -> None:
    evidence = ClaimEvidence(
        claim_sha256=_SHA,
        citation_source_ids=("NR-AUTH-001",),
    )
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, evidence).claim_sha256 = "b" * 64

    with pytest.raises(ValidationError, match="must be unique"):
        ClaimEvidence(
            claim_sha256=_SHA,
            citation_source_ids=("NR-AUTH-001", "NR-AUTH-001"),
        )


def test_failed_check_requires_failure_label() -> None:
    with pytest.raises(ValidationError, match="require a failure label"):
        QualityCheckResult(
            check_name=QualityCheckName.STRUCTURED_OUTPUT_VALID,
            status=QualityCheckStatus.FAILED,
        )


def test_scorecard_reconciles_failure_labels_and_pass_status() -> None:
    failed = QualityCheckResult(
        check_name=QualityCheckName.STRUCTURED_OUTPUT_VALID,
        status=QualityCheckStatus.FAILED,
        failure_label=EpisodeFailureLabel.STRUCTURED_OUTPUT_INVALID,
    )
    with pytest.raises(ValidationError, match="failure_labels must match"):
        DeterministicQualityResult(
            trace_id="quality-trace-contract-case",
            episode_id="ep-func-001",
            output_sha256=_SHA,
            retrieval_configuration_fingerprint="b" * 64,
            structured_output_valid=False,
            terminal_decision=None,
            checks=(failed,),
            failure_labels=(),
            deterministic_quality_passed=False,
        )
