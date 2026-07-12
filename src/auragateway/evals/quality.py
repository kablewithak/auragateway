"""Deterministic Gate 6 quality scorers over frozen diagnostic episodes."""

from __future__ import annotations

import hashlib

from pydantic import TypeAdapter, ValidationError

from auragateway.contracts.corpus import CorpusInventory
from auragateway.contracts.episodes import (
    AnswerDecisionOutput,
    AnswerExpectation,
    BenchmarkEpisode,
    ClarifyDecisionOutput,
    ClarifyExpectation,
    EpisodeFailureLabel,
    EscalateDecisionOutput,
    EscalateExpectation,
    RefuseDecisionOutput,
    RefuseExpectation,
    TerminalDecisionOutput,
)
from auragateway.contracts.quality import (
    DeterministicQualityResult,
    EpisodeClaimSupportRegistry,
    QualityCandidateTrace,
    QualityCheckName,
    QualityCheckResult,
    QualityCheckStatus,
)
from auragateway.contracts.retrieval_eval import TerminalDecision

_TERMINAL_OUTPUT_ADAPTER: TypeAdapter[TerminalDecisionOutput] = TypeAdapter(TerminalDecisionOutput)


def claim_sha256(claim: str) -> str:
    """Hash one normalized semantic claim without retaining raw claim text in results."""

    normalized = " ".join(claim.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _passed(check_name: QualityCheckName) -> QualityCheckResult:
    return QualityCheckResult(check_name=check_name, status=QualityCheckStatus.PASSED)


def _failed(
    check_name: QualityCheckName,
    failure_label: EpisodeFailureLabel,
    *details: str,
) -> QualityCheckResult:
    return QualityCheckResult(
        check_name=check_name,
        status=QualityCheckStatus.FAILED,
        failure_label=failure_label,
        details=tuple(details),
    )


def _not_applicable(check_name: QualityCheckName) -> QualityCheckResult:
    return QualityCheckResult(check_name=check_name, status=QualityCheckStatus.NOT_APPLICABLE)


def _validation_details(error: ValidationError) -> tuple[str, ...]:
    details: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "candidate_output"
        details.append(f"{location}: {item['msg']}")
    return tuple(details)


def _terminal_failure_label(expected: TerminalDecision) -> EpisodeFailureLabel:
    return {
        TerminalDecision.ANSWER: EpisodeFailureLabel.INVALID_TERMINAL_DECISION,
        TerminalDecision.CLARIFY: EpisodeFailureLabel.MISSING_CLARIFICATION,
        TerminalDecision.ESCALATE: EpisodeFailureLabel.ESCALATION_BYPASSED,
        TerminalDecision.REFUSE: EpisodeFailureLabel.REFUSAL_BYPASSED,
    }[expected]


def _output_citation_ids(output: TerminalDecisionOutput) -> tuple[str, ...]:
    if isinstance(output, AnswerDecisionOutput | ClarifyDecisionOutput):
        return output.citation_ids
    if isinstance(output, EscalateDecisionOutput):
        return output.evidence_source_ids
    return ()


def _terminal_details_check(
    episode: BenchmarkEpisode,
    output: TerminalDecisionOutput,
) -> QualityCheckResult:
    expected = episode.expected_terminal_decision
    check = QualityCheckName.TERMINAL_EXPECTATION_DETAILS_MATCH

    if isinstance(expected, AnswerExpectation):
        if not isinstance(output, AnswerDecisionOutput):
            return _not_applicable(check)
        return _passed(check)

    if isinstance(expected, ClarifyExpectation):
        if not isinstance(output, ClarifyDecisionOutput):
            return _not_applicable(check)
        required = set(expected.required_question_fields)
        missing = set(output.missing_fields)
        absent = sorted(required - missing)
        if absent:
            return _failed(check, EpisodeFailureLabel.MISSING_CLARIFICATION, *absent)
        return _passed(check)

    if isinstance(expected, EscalateExpectation):
        if not isinstance(output, EscalateDecisionOutput):
            return _not_applicable(check)
        if output.escalation_reason_code is not expected.escalation_reason_code:
            return _failed(
                check,
                EpisodeFailureLabel.ESCALATION_BYPASSED,
                "escalation_reason_code",
            )
        absent = sorted(
            set(expected.required_evidence_source_ids) - set(output.evidence_source_ids)
        )
        if absent:
            return _failed(check, EpisodeFailureLabel.CITATION_UNSUPPORTED, *absent)
        return _passed(check)

    if isinstance(expected, RefuseExpectation):
        if not isinstance(output, RefuseDecisionOutput):
            return _not_applicable(check)
        if output.refusal_reason_code is not expected.refusal_reason_code:
            return _failed(check, EpisodeFailureLabel.REFUSAL_BYPASSED, "refusal_reason_code")
        return _passed(check)

    return _not_applicable(check)


def _answer_checks(
    episode: BenchmarkEpisode,
    output: TerminalDecisionOutput,
    candidate: QualityCandidateTrace,
    claim_support: EpisodeClaimSupportRegistry,
) -> tuple[QualityCheckResult, ...]:
    check_names = (
        QualityCheckName.REQUIRED_CITATIONS_PRESENT,
        QualityCheckName.REQUIRED_CLAIMS_PRESENT,
        QualityCheckName.FORBIDDEN_CLAIMS_ABSENT,
        QualityCheckName.CLAIM_CITATION_SUPPORT_VALID,
    )
    expected = episode.expected_terminal_decision
    if not isinstance(expected, AnswerExpectation) or not isinstance(output, AnswerDecisionOutput):
        return tuple(_not_applicable(name) for name in check_names)

    output_citations = set(output.citation_ids)
    missing_citations = sorted(set(expected.required_citation_source_ids) - output_citations)
    citation_check = (
        _failed(
            QualityCheckName.REQUIRED_CITATIONS_PRESENT,
            EpisodeFailureLabel.CITATION_UNSUPPORTED,
            *missing_citations,
        )
        if missing_citations
        else _passed(QualityCheckName.REQUIRED_CITATIONS_PRESENT)
    )

    candidate_claims = {item.claim_sha256 for item in candidate.claim_evidence}
    required_claims = {claim_sha256(claim) for claim in expected.required_claims}
    missing_claims = sorted(required_claims - candidate_claims)
    required_claim_check = (
        _failed(
            QualityCheckName.REQUIRED_CLAIMS_PRESENT,
            EpisodeFailureLabel.UNSUPPORTED_CLAIM,
            *missing_claims,
        )
        if missing_claims
        else _passed(QualityCheckName.REQUIRED_CLAIMS_PRESENT)
    )

    forbidden_claims = {claim_sha256(claim) for claim in expected.forbidden_claims}
    present_forbidden = sorted(forbidden_claims & candidate_claims)
    forbidden_claim_check = (
        _failed(
            QualityCheckName.FORBIDDEN_CLAIMS_ABSENT,
            EpisodeFailureLabel.UNSUPPORTED_CLAIM,
            *present_forbidden,
        )
        if present_forbidden
        else _passed(QualityCheckName.FORBIDDEN_CLAIMS_ABSENT)
    )

    support_by_claim = {entry.claim_sha256: entry for entry in claim_support.entries}
    support_failures: list[str] = []
    for evidence in candidate.claim_evidence:
        support = support_by_claim.get(evidence.claim_sha256)
        cited = set(evidence.citation_source_ids)
        if support is None:
            support_failures.append(evidence.claim_sha256)
            continue
        if not cited & set(support.supporting_source_ids):
            support_failures.append(evidence.claim_sha256)
            continue
        if cited & set(support.contradicting_source_ids):
            support_failures.append(evidence.claim_sha256)
            continue
        if not cited.issubset(output_citations):
            support_failures.append(evidence.claim_sha256)

    support_check = (
        _failed(
            QualityCheckName.CLAIM_CITATION_SUPPORT_VALID,
            EpisodeFailureLabel.CITATION_UNSUPPORTED,
            *sorted(set(support_failures)),
        )
        if support_failures
        else _passed(QualityCheckName.CLAIM_CITATION_SUPPORT_VALID)
    )

    return (
        citation_check,
        required_claim_check,
        forbidden_claim_check,
        support_check,
    )


def score_deterministic_quality(
    episode: BenchmarkEpisode,
    inventory: CorpusInventory,
    candidate: QualityCandidateTrace,
    claim_support: EpisodeClaimSupportRegistry,
    expected_retrieval_configuration_fingerprint: str,
) -> DeterministicQualityResult:
    """Score deterministic quality criteria without model or rubric judgment."""

    if candidate.episode_id != episode.episode_id:
        raise ValueError("candidate episode_id must match the scored episode")
    if claim_support.episode_id != episode.episode_id:
        raise ValueError("claim-support episode_id must match the scored episode")

    try:
        output = _TERMINAL_OUTPUT_ADAPTER.validate_python(candidate.candidate_output)
    except ValidationError as error:
        invalid_checks = (
            _failed(
                QualityCheckName.STRUCTURED_OUTPUT_VALID,
                EpisodeFailureLabel.STRUCTURED_OUTPUT_INVALID,
                *_validation_details(error),
            ),
            *(
                _not_applicable(name)
                for name in QualityCheckName
                if name is not QualityCheckName.STRUCTURED_OUTPUT_VALID
            ),
        )
        failures = tuple(
            check.failure_label for check in invalid_checks if check.failure_label is not None
        )
        return DeterministicQualityResult(
            trace_id=candidate.trace_id,
            episode_id=candidate.episode_id,
            output_sha256=candidate.output_sha256,
            retrieval_configuration_fingerprint=candidate.retrieval_configuration_fingerprint,
            structured_output_valid=False,
            terminal_decision=None,
            checks=invalid_checks,
            failure_labels=failures,
            deterministic_quality_passed=False,
        )

    checks: list[QualityCheckResult] = [_passed(QualityCheckName.STRUCTURED_OUTPUT_VALID)]

    if (
        candidate.retrieval_configuration_fingerprint
        == expected_retrieval_configuration_fingerprint
    ):
        checks.append(_passed(QualityCheckName.CONFIGURATION_FINGERPRINT_MATCH))
    else:
        checks.append(
            _failed(
                QualityCheckName.CONFIGURATION_FINGERPRINT_MATCH,
                EpisodeFailureLabel.CONTRADICTORY_STATE,
                "retrieval_configuration_fingerprint",
            )
        )

    expected = episode.expected_terminal_decision
    if output.decision is expected.decision and output.reason_code is expected.reason_code:
        checks.append(_passed(QualityCheckName.TERMINAL_DECISION_CORRECT))
    else:
        checks.append(
            _failed(
                QualityCheckName.TERMINAL_DECISION_CORRECT,
                _terminal_failure_label(expected.decision),
                f"expected={expected.decision.value}",
                f"actual={output.decision.value}",
            )
        )

    inventory_by_id = {source.source_id: source for source in inventory.sources}
    retrieved = set(candidate.retrieved_source_ids)
    unknown_retrieved = sorted(retrieved - set(inventory_by_id))
    checks.append(
        _failed(
            QualityCheckName.RETRIEVED_SOURCE_IDS_VALID,
            EpisodeFailureLabel.INVALID_CITATION_ID,
            *unknown_retrieved,
        )
        if unknown_retrieved
        else _passed(QualityCheckName.RETRIEVED_SOURCE_IDS_VALID)
    )

    missing_required = sorted(set(episode.source_scope.required_source_ids) - retrieved)
    checks.append(
        _failed(
            QualityCheckName.REQUIRED_SOURCES_PRESENT,
            EpisodeFailureLabel.MISSING_REQUIRED_SOURCE,
            *missing_required,
        )
        if missing_required
        else _passed(QualityCheckName.REQUIRED_SOURCES_PRESENT)
    )

    used_forbidden = sorted(set(episode.source_scope.forbidden_source_ids) & retrieved)
    checks.append(
        _failed(
            QualityCheckName.FORBIDDEN_SOURCES_ABSENT,
            EpisodeFailureLabel.FORBIDDEN_SOURCE_USED,
            *used_forbidden,
        )
        if used_forbidden
        else _passed(QualityCheckName.FORBIDDEN_SOURCES_ABSENT)
    )

    scoped = set(episode.source_scope.required_source_ids) | set(
        episode.source_scope.optional_source_ids
    )
    unscoped_stale = sorted(
        source_id
        for source_id in retrieved
        if source_id in inventory_by_id
        and inventory_by_id[source_id].is_stale
        and source_id not in scoped
    )
    checks.append(
        _failed(
            QualityCheckName.UNSCOPED_STALE_SOURCES_ABSENT,
            EpisodeFailureLabel.STALE_SOURCE_SELECTED,
            *unscoped_stale,
        )
        if unscoped_stale
        else _passed(QualityCheckName.UNSCOPED_STALE_SOURCES_ABSENT)
    )

    citations = set(_output_citation_ids(output))
    unknown_citations = sorted(citations - set(inventory_by_id))
    checks.append(
        _failed(
            QualityCheckName.CITATION_IDS_VALID,
            EpisodeFailureLabel.INVALID_CITATION_ID,
            *unknown_citations,
        )
        if unknown_citations
        else _passed(QualityCheckName.CITATION_IDS_VALID)
    )

    unretrieved_citations = sorted(citations - retrieved)
    checks.append(
        _failed(
            QualityCheckName.CITATIONS_RETRIEVED,
            EpisodeFailureLabel.CITATION_UNSUPPORTED,
            *unretrieved_citations,
        )
        if unretrieved_citations
        else _passed(QualityCheckName.CITATIONS_RETRIEVED)
    )

    checks.extend(_answer_checks(episode, output, candidate, claim_support))
    checks.append(_terminal_details_check(episode, output))

    failures = tuple(
        dict.fromkeys(check.failure_label for check in checks if check.failure_label is not None)
    )
    passed = all(check.status is not QualityCheckStatus.FAILED for check in checks)
    return DeterministicQualityResult(
        trace_id=candidate.trace_id,
        episode_id=candidate.episode_id,
        output_sha256=candidate.output_sha256,
        retrieval_configuration_fingerprint=candidate.retrieval_configuration_fingerprint,
        structured_output_valid=True,
        terminal_decision=output.decision,
        checks=tuple(checks),
        failure_labels=failures,
        deterministic_quality_passed=passed,
    )
