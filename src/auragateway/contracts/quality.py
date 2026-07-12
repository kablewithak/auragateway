"""Typed deterministic quality-scoring contracts for Gate 6."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.contracts.retrieval_eval import TerminalDecision

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EPISODE_ID_PATTERN = re.compile(r"^ep-func-[0-9]{3}$")
_CASE_ID_PATTERN = re.compile(r"^quality-[a-z0-9-]{3,80}$")
_TRACE_ID_PATTERN = re.compile(r"^quality-trace-[a-z0-9-]{3,80}$")
_SOURCE_ID_PATTERN = re.compile(r"^NR-[A-Z][A-Z0-9-]*-[0-9]{3}$")


class QualityCheckStatus(StrEnum):
    """Outcome of one deterministic quality criterion."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class QualityCheckName(StrEnum):
    """Bounded deterministic checks evaluated before rubric review."""

    STRUCTURED_OUTPUT_VALID = "structured_output_valid"
    CONFIGURATION_FINGERPRINT_MATCH = "configuration_fingerprint_match"
    TERMINAL_DECISION_CORRECT = "terminal_decision_correct"
    RETRIEVED_SOURCE_IDS_VALID = "retrieved_source_ids_valid"
    REQUIRED_SOURCES_PRESENT = "required_sources_present"
    FORBIDDEN_SOURCES_ABSENT = "forbidden_sources_absent"
    UNSCOPED_STALE_SOURCES_ABSENT = "unscoped_stale_sources_absent"
    CITATION_IDS_VALID = "citation_ids_valid"
    CITATIONS_RETRIEVED = "citations_retrieved"
    REQUIRED_CITATIONS_PRESENT = "required_citations_present"
    REQUIRED_CLAIMS_PRESENT = "required_claims_present"
    FORBIDDEN_CLAIMS_ABSENT = "forbidden_claims_absent"
    CLAIM_CITATION_SUPPORT_VALID = "claim_citation_support_valid"
    TERMINAL_EXPECTATION_DETAILS_MATCH = "terminal_expectation_details_match"


class ClaimEvidence(BaseModel):
    """Metadata-only claim digest and the source IDs cited for it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_sha256: str
    citation_source_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("claim_sha256")
    @classmethod
    def validate_claim_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("claim_sha256 must be lowercase SHA-256")
        return value

    @field_validator("citation_source_ids")
    @classmethod
    def validate_citation_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("claim citation source IDs must be unique")
        for source_id in value:
            if _SOURCE_ID_PATTERN.fullmatch(source_id) is None:
                raise ValueError("claim citation source IDs must match NR-<AREA>-<NNN>")
        return value


class ClaimSupportEntry(BaseModel):
    """Frozen human-authored evidence mapping for one semantic claim digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_sha256: str
    supporting_source_ids: tuple[str, ...] = Field(min_length=1)
    contradicting_source_ids: tuple[str, ...] = ()

    @field_validator("claim_sha256")
    @classmethod
    def validate_claim_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("claim_sha256 must be lowercase SHA-256")
        return value

    @field_validator("supporting_source_ids", "contradicting_source_ids")
    @classmethod
    def validate_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("claim-support source IDs must be unique")
        for source_id in value:
            if _SOURCE_ID_PATTERN.fullmatch(source_id) is None:
                raise ValueError("claim-support source IDs must match NR-<AREA>-<NNN>")
        return value

    @model_validator(mode="after")
    def validate_support_groups(self) -> ClaimSupportEntry:
        if set(self.supporting_source_ids) & set(self.contradicting_source_ids):
            raise ValueError("supporting and contradicting source IDs must not overlap")
        return self


class EpisodeClaimSupportRegistry(BaseModel):
    """Frozen claim-to-source evidence mapping for one diagnostic episode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    episode_id: str
    entries: tuple[ClaimSupportEntry, ...] = ()

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @model_validator(mode="after")
    def validate_entries(self) -> EpisodeClaimSupportRegistry:
        claim_hashes = [entry.claim_sha256 for entry in self.entries]
        if len(claim_hashes) != len(set(claim_hashes)):
            raise ValueError("claim-support entries must have unique claim digests")
        return self


class QualityCandidateTrace(BaseModel):
    """Synthetic/private scoring input; persisted results retain only metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    trace_id: str
    episode_id: str
    output_sha256: str
    candidate_output: dict[str, JsonValue]
    retrieved_source_ids: tuple[str, ...]
    claim_evidence: tuple[ClaimEvidence, ...] = ()
    retrieval_configuration_fingerprint: str

    @field_validator("trace_id")
    @classmethod
    def validate_trace_id(cls, value: str) -> str:
        if _TRACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trace_id must use the quality-trace-<slug> form")
        return value

    @field_validator("episode_id")
    @classmethod
    def validate_episode_id(cls, value: str) -> str:
        if _EPISODE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("episode_id must match ep-func-<NNN>")
        return value

    @field_validator("output_sha256", "retrieval_configuration_fingerprint")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("quality trace digests must be lowercase SHA-256")
        return value

    @field_validator("retrieved_source_ids")
    @classmethod
    def validate_retrieved_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("retrieved source IDs must be unique")
        return value

    @model_validator(mode="after")
    def validate_claim_evidence(self) -> QualityCandidateTrace:
        claim_hashes = [item.claim_sha256 for item in self.claim_evidence]
        if len(claim_hashes) != len(set(claim_hashes)):
            raise ValueError("claim evidence must contain unique claim digests")
        return self


class QualityCheckResult(BaseModel):
    """One deterministic criterion result with bounded failure evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_name: QualityCheckName
    status: QualityCheckStatus
    failure_label: EpisodeFailureLabel | None = None
    details: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result_shape(self) -> QualityCheckResult:
        if self.status is QualityCheckStatus.FAILED and self.failure_label is None:
            raise ValueError("failed quality checks require a failure label")
        if self.status is not QualityCheckStatus.FAILED and self.failure_label is not None:
            raise ValueError("non-failed quality checks must not carry a failure label")
        return self


class DeterministicQualityResult(BaseModel):
    """Metadata-only deterministic scorecard for one candidate trajectory output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    trace_id: str
    episode_id: str
    output_sha256: str
    retrieval_configuration_fingerprint: str
    structured_output_valid: bool
    terminal_decision: TerminalDecision | None
    checks: tuple[QualityCheckResult, ...] = Field(min_length=1)
    failure_labels: tuple[EpisodeFailureLabel, ...]
    deterministic_quality_passed: bool

    @model_validator(mode="after")
    def validate_scorecard(self) -> DeterministicQualityResult:
        check_names = [check.check_name for check in self.checks]
        if len(check_names) != len(set(check_names)):
            raise ValueError("quality scorecard check names must be unique")
        expected_failures = tuple(
            dict.fromkeys(
                check.failure_label for check in self.checks if check.failure_label is not None
            )
        )
        if self.failure_labels != expected_failures:
            raise ValueError("failure_labels must match failed checks in check order")
        expected_pass = all(check.status is not QualityCheckStatus.FAILED for check in self.checks)
        if self.deterministic_quality_passed != expected_pass:
            raise ValueError("deterministic_quality_passed must match check outcomes")
        if not self.structured_output_valid and self.terminal_decision is not None:
            raise ValueError("invalid structured output must not expose a terminal decision")
        return self


class QualityFixtureCase(BaseModel):
    """One fixed deterministic quality-scoring case and expected result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    candidate: QualityCandidateTrace
    claim_support: EpisodeClaimSupportRegistry
    expected_pass: bool
    expected_failure_labels: tuple[EpisodeFailureLabel, ...]
    negative_control: bool

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if _CASE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("case_id must use the quality-<slug> form")
        return value

    @model_validator(mode="after")
    def validate_case(self) -> QualityFixtureCase:
        if self.claim_support.episode_id != self.candidate.episode_id:
            raise ValueError("claim-support episode must match candidate episode")
        if self.expected_pass and self.expected_failure_labels:
            raise ValueError("passing fixtures must not expect failure labels")
        if self.negative_control == self.expected_pass:
            raise ValueError("negative_control must be the inverse of expected_pass")
        return self


class QualityFixtureSet(BaseModel):
    """Fixed Gate 6 deterministic scorer fixtures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str = "auragateway-gate-6-deterministic-quality-v1"
    cases: tuple[QualityFixtureCase, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_fixture_set(self) -> QualityFixtureSet:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("quality fixture case IDs must be unique")
        if not any(case.expected_pass for case in self.cases):
            raise ValueError("quality fixtures require at least one passing case")
        if not any(case.negative_control for case in self.cases):
            raise ValueError("quality fixtures require negative controls")
        return self


class QualityFixtureResult(BaseModel):
    """One executed fixture and expectation comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    scorecard: DeterministicQualityResult
    expectation_matched: bool
    negative_control: bool


class Gate6DeterministicQualityReport(BaseModel):
    """Reproducible fixed-case report for the first Gate 6 scorer boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    fixture_set_id: str
    results: tuple[QualityFixtureResult, ...]
    fixture_count: int
    negative_control_count: int
    all_expectations_matched: bool
    deterministic_scorers_passed: bool
    measured_execution_permitted: bool = False

    @model_validator(mode="after")
    def validate_report(self) -> Gate6DeterministicQualityReport:
        if self.fixture_count != len(self.results):
            raise ValueError("fixture_count must match quality results")
        if self.negative_control_count != sum(result.negative_control for result in self.results):
            raise ValueError("negative_control_count must match quality results")
        expected_match = all(result.expectation_matched for result in self.results)
        if self.all_expectations_matched != expected_match:
            raise ValueError("all_expectations_matched must reconcile")
        if self.deterministic_scorers_passed != expected_match:
            raise ValueError("deterministic_scorers_passed must match fixture expectations")
        if self.measured_execution_permitted:
            raise ValueError("deterministic scorer fixtures do not permit measured execution")
        return self


class Gate6DeterministicQualityManifest(BaseModel):
    """Hash-bound inventory for deterministic quality fixtures and report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-gate-6-deterministic-quality-manifest-v1"
    fixture_path: str
    fixture_sha256: str
    report_path: str
    report_sha256: str
    episode_manifest_path: str
    episode_manifest_sha256: str
    retrieval_configuration_fingerprint: str
    fixture_count: int
    negative_control_count: int
    deterministic_scorers_passed: bool
    measured_execution_permitted: bool = False

    @field_validator(
        "fixture_sha256",
        "report_sha256",
        "episode_manifest_sha256",
        "retrieval_configuration_fingerprint",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("quality manifest digests must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> Gate6DeterministicQualityManifest:
        if not self.deterministic_scorers_passed:
            raise ValueError("quality manifest requires passed deterministic scorers")
        if self.measured_execution_permitted:
            raise ValueError("quality manifest does not permit measured execution")
        return self


class Gate6DeterministicQualitySummary(BaseModel):
    """Safe CLI output for deterministic quality build or verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_count: int
    negative_control_count: int
    deterministic_scorers_passed: bool
    measured_execution_permitted: bool
    fixture_sha256: str
    report_sha256: str
