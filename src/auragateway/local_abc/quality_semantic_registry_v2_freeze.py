"""Freeze the audited quality semantic registry v2 without evaluator execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.local_abc import quality_semantic_registry_v2_population as population

REGISTRY_PATH = population.REGISTRY_PATH
FREEZE_PATH = Path("data/evals/quality/semantic-registry-v2/freeze.json")

EXPECTED_REGISTRY_SHA256: Literal[
    "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
EXPECTED_REGISTRY_ARTIFACT_SHA256 = (
    "0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c"
)
EXPECTED_CRITERION_COUNT: Literal[7] = 7
EXPECTED_FAILURE_LABEL_COUNT: Literal[22] = 22
EXPECTED_SEMANTIC_SOURCE_COUNT: Literal[50] = 50


class SemanticRegistryFreezeError(RuntimeError):
    """Fail-closed semantic-registry freeze error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SemanticRegistryFreezeError(
            "QUALITY_SEMANTIC_REGISTRY_FREEZE_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SharedProjectionPolicy(FrozenModel):
    policy_id: Literal["auragateway-quality-shared-semantic-projection-v1"] = (
        "auragateway-quality-shared-semantic-projection-v1"
    )

    source_registry_path: Literal["data/evals/quality/semantic-registry-v2/registry.json"] = (
        "data/evals/quality/semantic-registry-v2/registry.json"
    )

    source_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = EXPECTED_REGISTRY_SHA256

    human_projection_uses_registry: Literal[True] = True
    model_projection_uses_registry: Literal[True] = True

    human_projection_requires_all_criteria: Literal[True] = True
    model_projection_requires_all_criteria: Literal[True] = True

    human_projection_requires_all_failure_labels: Literal[True] = True
    model_projection_requires_all_failure_labels: Literal[True] = True

    private_human_semantic_augmentation_permitted: Literal[False] = False
    private_model_semantic_augmentation_permitted: Literal[False] = False

    semantic_elision_permitted: Literal[False] = False
    independent_private_ontology_permitted: Literal[False] = False

    rendering_may_differ: Literal[True] = True
    semantic_content_may_differ: Literal[False] = False


class HistoricalAuthorityPolicy(FrozenModel):
    final_342_human_authority_mutated: Literal[False] = False
    blinded_v1_rubric_mutated: Literal[False] = False

    final_342_remains_development_diagnostic: Literal[True] = True
    final_342_permitted_as_v2_qualification: Literal[False] = False

    fresh_v2_qualification_required: Literal[True] = True

    deployment_threshold_selected: Literal[False] = False
    deployment_threshold_validated: Literal[False] = False

    jev_request_performed_by_freeze: Literal[False] = False
    network_access_performed_by_freeze: Literal[False] = False


class QualitySemanticRegistryFreezeV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"

    freeze_id: Literal["auragateway-quality-semantic-registry-v2-freeze-v1"] = (
        "auragateway-quality-semantic-registry-v2-freeze-v1"
    )

    freeze_status: Literal["FROZEN"] = "FROZEN"

    registry_id: Literal["auragateway-quality-semantic-registry-v2"] = (
        "auragateway-quality-semantic-registry-v2"
    )

    registry_schema_version: Literal["2.0.0"] = "2.0.0"

    registry_path: Literal["data/evals/quality/semantic-registry-v2/registry.json"] = (
        "data/evals/quality/semantic-registry-v2/registry.json"
    )

    registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    registry_artifact_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    criterion_count: Literal[7] = EXPECTED_CRITERION_COUNT
    failure_label_count: Literal[22] = EXPECTED_FAILURE_LABEL_COUNT
    semantic_source_count: Literal[50] = EXPECTED_SEMANTIC_SOURCE_COUNT
    unresolved_semantic_entry_count: Literal[0] = 0

    registry_subject_frozen: Literal[True] = True
    registry_semantics_mutation_permitted: Literal[False] = False

    projection_policy: SharedProjectionPolicy
    historical_authority_policy: HistoricalAuthorityPolicy

    next_gate: Literal["J7K_SHARED_SEMANTIC_PROJECTION_V1"] = "J7K_SHARED_SEMANTIC_PROJECTION_V1"

    @model_validator(mode="after")
    def validate_freeze(self) -> Self:
        if self.registry_sha256 != EXPECTED_REGISTRY_SHA256:
            raise ValueError("registry semantic SHA-256 drifted")

        if self.registry_artifact_file_sha256 != EXPECTED_REGISTRY_ARTIFACT_SHA256:
            raise ValueError("registry artifact SHA-256 drifted")

        if self.projection_policy.source_registry_sha256 != self.registry_sha256:
            raise ValueError("projection policy must bind the frozen registry SHA-256")

        return self


def canonical_json_bytes(value: object) -> bytes:
    """Return deterministic JSON bytes without a trailing newline."""

    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(value).hexdigest()


def _artifact_bytes(
    freeze: QualitySemanticRegistryFreezeV1,
) -> bytes:
    return canonical_json_bytes(freeze.model_dump(mode="json")) + b"\n"


def _validate_population_receipt(
    receipt: dict[str, object],
) -> None:
    expected: dict[str, object] = {
        "registry_id": "auragateway-quality-semantic-registry-v2",
        "schema_version": "2.0.0",
        "criterion_count": EXPECTED_CRITERION_COUNT,
        "failure_label_count": EXPECTED_FAILURE_LABEL_COUNT,
        "semantic_source_count": EXPECTED_SEMANTIC_SOURCE_COUNT,
        "unresolved_semantic_entry_count": 0,
        "registry_sha256": EXPECTED_REGISTRY_SHA256,
        "artifact_file_sha256": EXPECTED_REGISTRY_ARTIFACT_SHA256,
        "final_342_mutated": False,
        "rubric_v1_mutated": False,
        "jev_request_performed": False,
        "deployment_threshold_selected": False,
    }

    drift = tuple(
        key for key, expected_value in expected.items() if receipt.get(key) != expected_value
    )

    if drift:
        raise SemanticRegistryFreezeError(
            "QUALITY_SEMANTIC_REGISTRY_FREEZE_INPUT_DRIFT",
            "registry population receipt drifted: " + ",".join(drift),
        )


def build_freeze(
    repo_root: Path,
) -> QualitySemanticRegistryFreezeV1:
    """Build a freeze only from the already-validated registry artifact."""

    receipt = population.verify_materialized_registry(repo_root)
    _validate_population_receipt(receipt)

    return QualitySemanticRegistryFreezeV1(
        registry_sha256=EXPECTED_REGISTRY_SHA256,
        registry_artifact_file_sha256=(EXPECTED_REGISTRY_ARTIFACT_SHA256),
        projection_policy=SharedProjectionPolicy(),
        historical_authority_policy=HistoricalAuthorityPolicy(),
    )


def write_freeze(repo_root: Path) -> Path:
    """Write the exact freeze artifact and refuse silent replacement."""

    freeze = build_freeze(repo_root)

    path = repo_root / FREEZE_PATH
    payload = _artifact_bytes(freeze)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SemanticRegistryFreezeError(
                "QUALITY_SEMANTIC_REGISTRY_FREEZE_OUTPUT_UNSAFE",
                "freeze output path is unsafe",
            )

        if path.read_bytes() != payload:
            raise SemanticRegistryFreezeError(
                "QUALITY_SEMANTIC_REGISTRY_FREEZE_ARTIFACT_DRIFT",
                "existing freeze artifact differs from the frozen payload",
            )

        return path

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise SemanticRegistryFreezeError(
            "QUALITY_SEMANTIC_REGISTRY_FREEZE_TEMP_RESIDUE",
            "temporary freeze artifact already exists",
        )

    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)

    return path


def verify_freeze(
    repo_root: Path,
) -> dict[str, object]:
    """Verify the frozen bytes and return a metadata-only receipt."""

    expected = build_freeze(repo_root)

    path = repo_root / FREEZE_PATH

    if not path.is_file() or path.is_symlink():
        raise SemanticRegistryFreezeError(
            "QUALITY_SEMANTIC_REGISTRY_FREEZE_MISSING",
            "semantic registry freeze artifact is missing or unsafe",
        )

    observed_bytes = path.read_bytes()
    expected_bytes = _artifact_bytes(expected)

    if observed_bytes != expected_bytes:
        raise SemanticRegistryFreezeError(
            "QUALITY_SEMANTIC_REGISTRY_FREEZE_BYTES_DRIFT",
            "semantic registry freeze artifact bytes drifted",
        )

    observed = QualitySemanticRegistryFreezeV1.model_validate(
        json.loads(observed_bytes.decode("utf-8"))
    )

    if observed != expected:
        raise SemanticRegistryFreezeError(
            "QUALITY_SEMANTIC_REGISTRY_FREEZE_TYPED_DRIFT",
            "typed semantic registry freeze differs from expected state",
        )

    return {
        "status": "QUALITY_SEMANTIC_REGISTRY_V2_FROZEN",
        "freeze_id": observed.freeze_id,
        "freeze_file_sha256": sha256_bytes(observed_bytes),
        "registry_sha256": observed.registry_sha256,
        "registry_artifact_file_sha256": (observed.registry_artifact_file_sha256),
        "criterion_count": observed.criterion_count,
        "failure_label_count": observed.failure_label_count,
        "semantic_source_count": observed.semantic_source_count,
        "unresolved_semantic_entry_count": (observed.unresolved_semantic_entry_count),
        "human_projection_uses_registry": (
            observed.projection_policy.human_projection_uses_registry
        ),
        "model_projection_uses_registry": (
            observed.projection_policy.model_projection_uses_registry
        ),
        "semantic_content_may_differ": (observed.projection_policy.semantic_content_may_differ),
        "private_semantic_augmentation_permitted": False,
        "final_342_mutated": False,
        "rubric_v1_mutated": False,
        "jev_request_performed": False,
        "network_access_performed": False,
        "deployment_threshold_selected": False,
        "registry_frozen": True,
        "next_gate": observed.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    for command in ("write", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument(
            "--repo-root",
            required=True,
            type=Path,
        )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()

    if args.command == "write":
        write_freeze(repo_root)

    receipt = verify_freeze(repo_root)

    print(
        json.dumps(
            receipt,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
