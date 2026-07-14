from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicationTarget(StrEnum):
    DATASET = "dataset"
    SPACE = "space"


class PublicationEvidenceClass(StrEnum):
    CONTROLLED_PROVIDER = "controlled_provider"
    FIXTURE_ONLY = "fixture_only"
    INFERRED_LOCAL = "inferred_local"


class ProviderLineageStatus(StrEnum):
    CLOSED_TELEMETRY_UNAVAILABLE = "closed_telemetry_unavailable"
    CLOSED_PRE_INFERENCE_AUTHENTICATION = "closed_pre_inference_authentication"


class ClaimDisposition(StrEnum):
    PERMITTED = "permitted"
    BLOCKED = "blocked"


class PublicationFileRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: int = Field(ge=0)


class ProviderLineageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lineage_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    requested_model: str | None = None
    evidence_class: PublicationEvidenceClass
    status: ProviderLineageStatus
    attempts: int = Field(ge=0)
    provider_successes: int = Field(ge=0)
    cache_telemetry_observed: bool
    comparison_eligible: bool
    summary: str = Field(min_length=1)
    permitted_claim: str = Field(min_length=1)
    blocked_claims: tuple[str, ...]
    source_paths: tuple[str, ...]

    @model_validator(mode="after")
    def validate_terminal_boundary(self) -> ProviderLineageRecord:
        if self.comparison_eligible:
            raise ValueError("terminal publication lineages must remain comparison-ineligible")
        if self.cache_telemetry_observed:
            raise ValueError("terminal publication lineages must not claim cache telemetry")
        return self


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str = Field(min_length=1)
    disposition: ClaimDisposition
    statement: str = Field(min_length=1)
    evidence_basis: tuple[str, ...]


class PublicationState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    publication_id: str
    project: str
    source_main_checkpoint: str
    core_prd_version: str
    hy3_mini_prd_version: str
    evidence_maturity: tuple[str, ...]
    provider_lineages: tuple[ProviderLineageRecord, ...]
    claims: tuple[ClaimRecord, ...]
    comparison_eligible: bool
    live_inference_included: bool
    credential_required: bool
    customer_data_included: bool
    raw_provider_payload_included: bool
    publication_license: str

    @model_validator(mode="after")
    def validate_publication_boundary(self) -> PublicationState:
        if self.comparison_eligible:
            raise ValueError("publication must not make the A/B/C comparison eligible")
        if self.live_inference_included:
            raise ValueError("static publication must not include live inference")
        if self.credential_required:
            raise ValueError("static publication must not require credentials")
        if self.customer_data_included:
            raise ValueError("publication must not include customer data")
        if self.raw_provider_payload_included:
            raise ValueError("publication must not include raw provider payloads")
        if len(self.provider_lineages) != 2:
            raise ValueError("publication must contain exactly the two terminal live lineages")
        return self


class SanitizationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    publication_id: str
    scanned_file_count: int = Field(ge=1)
    forbidden_path_match_count: int = Field(ge=0)
    secret_pattern_match_count: int = Field(ge=0)
    raw_payload_match_count: int = Field(ge=0)
    credential_value_included: bool
    raw_prompt_included: bool
    raw_provider_payload_included: bool
    customer_data_included: bool
    passed: bool

    @model_validator(mode="after")
    def validate_pass_state(self) -> SanitizationReport:
        expected = (
            self.forbidden_path_match_count == 0
            and self.secret_pattern_match_count == 0
            and self.raw_payload_match_count == 0
            and not self.credential_value_included
            and not self.raw_prompt_included
            and not self.raw_provider_payload_included
            and not self.customer_data_included
        )
        if self.passed != expected:
            raise ValueError("sanitization pass state does not match the scan result")
        return self


class PublicationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    publication_id: str
    source_main_checkpoint: str
    source_evidence: tuple[PublicationFileRecord, ...]
    dataset_files: tuple[PublicationFileRecord, ...]
    space_files: tuple[PublicationFileRecord, ...]
    publication_state_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sanitization_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    live_inference_included: bool
    credential_required: bool
    remote_publication_authorized: bool

    @model_validator(mode="after")
    def validate_release_state(self) -> PublicationManifest:
        if self.live_inference_included:
            raise ValueError("manifest cannot authorize live inference")
        if self.credential_required:
            raise ValueError("manifest cannot require credentials")
        if self.remote_publication_authorized:
            raise ValueError("local package must not authorize remote publication")
        return self
