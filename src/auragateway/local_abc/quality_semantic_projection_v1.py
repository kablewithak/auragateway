"""J7K deterministic human/model projections from the frozen quality registry v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Never, TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.contracts.quality_semantic_projection_v1 import (
    EXPECTED_REGISTRY_ARTIFACT_SHA256,
    EXPECTED_REGISTRY_SHA256,
    HumanCriterionSemanticProjectionV1,
    HumanFailureLabelSemanticProjectionV1,
    HumanSemanticProjectionV1,
    ModelCriterionSemanticQuestionV1,
    ModelFailureLabelSemanticQuestionV1,
    ModelSemanticProjectionV1,
    SemanticProjectionParityReceiptV1,
)
from auragateway.contracts.quality_semantic_registry_v2 import (
    CriterionSemanticDefinitionV2,
    FailureLabelSemanticDefinitionV2,
    QualitySemanticRegistryV2,
)
from auragateway.local_abc import quality_semantic_registry_v2_freeze as registry_freeze

REGISTRY_PATH = Path("data/evals/quality/semantic-registry-v2/registry.json")
PROJECTION_ROOT = Path("data/evals/quality/semantic-registry-v2/projection-v1")
HUMAN_PROJECTION_PATH = PROJECTION_ROOT / "human.json"
MODEL_PROJECTION_PATH = PROJECTION_ROOT / "model.json"
PARITY_RECEIPT_PATH = PROJECTION_ROOT / "parity-receipt.json"

HUMAN_PREFIX = "AuraGateway v2 semantic contract JSON: "
MODEL_PREFIX = "Use exactly this AuraGateway v2 semantic contract JSON: "

ModelT = TypeVar("ModelT", bound=BaseModel)


class SemanticProjectionError(RuntimeError):
    """Fail-closed J7K semantic projection error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_ARGUMENT_ERROR",
            message,
        )


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


def _artifact_bytes(model: BaseModel) -> bytes:
    return canonical_json_bytes(model.model_dump(mode="json")) + b"\n"


def _semantic_json(model: BaseModel) -> str:
    return canonical_json_bytes(model.model_dump(mode="json")).decode("utf-8")


def _parse_rendered_semantics(
    rendered: str,
    *,
    prefix: str,
    model_type: type[ModelT],
) -> ModelT:
    if not rendered.startswith(prefix):
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_RENDER_PREFIX_DRIFT",
            "rendered semantic projection prefix drifted",
        )

    payload_text = rendered[len(prefix) :]

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as error:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_RENDER_JSON_INVALID",
            "rendered semantic projection JSON is invalid",
        ) from error

    if not isinstance(payload, dict):
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_RENDER_SHAPE_INVALID",
            "rendered semantic projection payload must be an object",
        )

    return model_type.model_validate(payload)


def load_frozen_registry(repo_root: Path) -> QualitySemanticRegistryV2:
    """Load the exact registry bound by the already-accepted freeze."""

    root = repo_root.resolve()
    freeze_receipt = registry_freeze.verify_freeze(root)

    if freeze_receipt["registry_sha256"] != EXPECTED_REGISTRY_SHA256:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_FREEZE_SEMANTIC_DRIFT",
            "freeze no longer binds the expected semantic registry",
        )

    if (
        freeze_receipt["registry_artifact_file_sha256"]
        != EXPECTED_REGISTRY_ARTIFACT_SHA256
    ):
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_FREEZE_ARTIFACT_DRIFT",
            "freeze no longer binds the expected registry artifact",
        )

    path = root / REGISTRY_PATH

    if not path.is_file() or path.is_symlink():
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_REGISTRY_MISSING",
            "frozen registry artifact is missing or unsafe",
        )

    observed_bytes = path.read_bytes()

    if sha256_bytes(observed_bytes) != EXPECTED_REGISTRY_ARTIFACT_SHA256:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_REGISTRY_ARTIFACT_DRIFT",
            "registry artifact SHA-256 drifted",
        )

    try:
        payload = json.loads(observed_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_REGISTRY_JSON_INVALID",
            "frozen registry artifact is not valid UTF-8 JSON",
        ) from error

    registry = QualitySemanticRegistryV2.model_validate(payload)

    if registry.sha256() != EXPECTED_REGISTRY_SHA256:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_REGISTRY_SEMANTIC_DRIFT",
            "registry semantic SHA-256 drifted",
        )

    return registry


def build_human_projection(
    registry: QualitySemanticRegistryV2,
) -> HumanSemanticProjectionV1:
    """Render complete reviewer-facing semantics from the canonical registry."""

    return HumanSemanticProjectionV1(
        criteria=tuple(
            HumanCriterionSemanticProjectionV1(
                criterion=definition.criterion,
                guidance=HUMAN_PREFIX + _semantic_json(definition),
            )
            for definition in registry.criteria
        ),
        failure_labels=tuple(
            HumanFailureLabelSemanticProjectionV1(
                label=definition.label,
                guidance=HUMAN_PREFIX + _semantic_json(definition),
            )
            for definition in registry.failure_labels
        ),
    )


def _criterion_score_anchors(
    definition: CriterionSemanticDefinitionV2,
) -> dict[str, str]:
    return {
        "1": definition.score_1_anchor,
        "2": definition.score_2_anchor,
        "3": definition.score_3_anchor,
        "4": definition.score_4_anchor,
    }


def build_model_projection(
    registry: QualitySemanticRegistryV2,
) -> ModelSemanticProjectionV1:
    """Render complete Jev-compatible question semantics without making a request."""

    return ModelSemanticProjectionV1(
        criterion_questions=tuple(
            ModelCriterionSemanticQuestionV1(
                question_name=f"criterion__{definition.criterion.value}",
                criterion=definition.criterion,
                instructions=MODEL_PREFIX + _semantic_json(definition),
                criteria=_criterion_score_anchors(definition),
            )
            for definition in registry.criteria
        ),
        failure_questions=tuple(
            ModelFailureLabelSemanticQuestionV1(
                question_name=f"failure__{definition.label.value}",
                label=definition.label,
                instructions=MODEL_PREFIX + _semantic_json(definition),
            )
            for definition in registry.failure_labels
        ),
    )


def reconstruct_registry_from_human_projection(
    projection: HumanSemanticProjectionV1,
) -> QualitySemanticRegistryV2:
    """Recover the canonical registry semantics from the human-visible rendering."""

    criteria = tuple(
        _parse_rendered_semantics(
            item.guidance,
            prefix=HUMAN_PREFIX,
            model_type=CriterionSemanticDefinitionV2,
        )
        for item in projection.criteria
    )
    failure_labels = tuple(
        _parse_rendered_semantics(
            item.guidance,
            prefix=HUMAN_PREFIX,
            model_type=FailureLabelSemanticDefinitionV2,
        )
        for item in projection.failure_labels
    )

    for projected_criterion, reconstructed_criterion in zip(
        projection.criteria,
        criteria,
        strict=True,
    ):
        if projected_criterion.criterion != reconstructed_criterion.criterion:
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_HUMAN_CRITERION_DRIFT",
                "human projection criterion identity differs from rendered semantics",
            )

    for projected_label, reconstructed_label in zip(
        projection.failure_labels,
        failure_labels,
        strict=True,
    ):
        if projected_label.label != reconstructed_label.label:
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_HUMAN_LABEL_DRIFT",
                "human projection label identity differs from rendered semantics",
            )

    return QualitySemanticRegistryV2(
        criteria=criteria,
        failure_labels=failure_labels,
    )


def reconstruct_registry_from_model_projection(
    projection: ModelSemanticProjectionV1,
) -> QualitySemanticRegistryV2:
    """Recover the canonical registry semantics from the model-visible questions."""

    criteria = tuple(
        _parse_rendered_semantics(
            item.instructions,
            prefix=MODEL_PREFIX,
            model_type=CriterionSemanticDefinitionV2,
        )
        for item in projection.criterion_questions
    )
    failure_labels = tuple(
        _parse_rendered_semantics(
            item.instructions,
            prefix=MODEL_PREFIX,
            model_type=FailureLabelSemanticDefinitionV2,
        )
        for item in projection.failure_questions
    )

    for projected_question, reconstructed_criterion in zip(
        projection.criterion_questions,
        criteria,
        strict=True,
    ):
        if projected_question.criterion != reconstructed_criterion.criterion:
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_MODEL_CRITERION_DRIFT",
                "model question criterion differs from rendered semantics",
            )

        if projected_question.criteria != _criterion_score_anchors(reconstructed_criterion):
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_MODEL_ANCHOR_DRIFT",
                "model question score anchors differ from rendered semantics",
            )

    for projected_failure_question, reconstructed_label in zip(
        projection.failure_questions,
        failure_labels,
        strict=True,
    ):
        if projected_failure_question.label != reconstructed_label.label:
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_MODEL_LABEL_DRIFT",
                "model question label differs from rendered semantics",
            )

    return QualitySemanticRegistryV2(
        criteria=criteria,
        failure_labels=failure_labels,
    )


def build_parity_receipt(
    registry: QualitySemanticRegistryV2,
    human_projection: HumanSemanticProjectionV1,
    model_projection: ModelSemanticProjectionV1,
) -> SemanticProjectionParityReceiptV1:
    """Prove exact semantic parity across both deterministic consumer projections."""

    human_registry = reconstruct_registry_from_human_projection(human_projection)
    model_registry = reconstruct_registry_from_model_projection(model_projection)

    source_bytes = registry.canonical_bytes()
    human_bytes = human_registry.canonical_bytes()
    model_bytes = model_registry.canonical_bytes()

    if human_bytes != source_bytes:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_HUMAN_ELISION_OR_AUGMENTATION",
            "human projection does not reconstruct the exact frozen registry",
        )

    if model_bytes != source_bytes:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_MODEL_ELISION_OR_AUGMENTATION",
            "model projection does not reconstruct the exact frozen registry",
        )

    if human_bytes != model_bytes:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_PARITY_FAILED",
            "human and model projections reconstruct different semantics",
        )

    semantic_source_count = sum(
        len(item.semantic_sources) for item in registry.criteria
    ) + sum(len(item.semantic_sources) for item in registry.failure_labels)

    if semantic_source_count != 50:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_SOURCE_COUNT_DRIFT",
            "semantic source inventory drifted",
        )

    return SemanticProjectionParityReceiptV1(
        human_projection_sha256=sha256_bytes(_artifact_bytes(human_projection)),
        model_projection_sha256=sha256_bytes(_artifact_bytes(model_projection)),
    )


def build_projection_bundle(
    repo_root: Path,
) -> tuple[
    HumanSemanticProjectionV1,
    ModelSemanticProjectionV1,
    SemanticProjectionParityReceiptV1,
]:
    """Build the complete J7K deterministic projection subject."""

    registry = load_frozen_registry(repo_root)
    human_projection = build_human_projection(registry)
    model_projection = build_model_projection(registry)
    receipt = build_parity_receipt(
        registry,
        human_projection,
        model_projection,
    )
    return human_projection, model_projection, receipt


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_OUTPUT_UNSAFE",
                "projection output path is unsafe",
            )

        if path.read_bytes() != payload:
            raise SemanticProjectionError(
                "J7K_SHARED_SEMANTIC_PROJECTION_ARTIFACT_DRIFT",
                "existing generated projection artifact differs from expected bytes",
            )

        return

    temporary = path.with_name(f".{path.name}.tmp")

    if temporary.exists():
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_TEMP_RESIDUE",
            "projection temporary file already exists",
        )

    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)


def write_projection_artifacts(
    repo_root: Path,
    *,
    output_root: Path | None = None,
) -> SemanticProjectionParityReceiptV1:
    """Materialize producer-owned J7K evidence without provider execution."""

    root = repo_root.resolve()
    destination = root if output_root is None else output_root.resolve()

    human_projection, model_projection, receipt = build_projection_bundle(root)

    _write_once(
        destination / HUMAN_PROJECTION_PATH,
        _artifact_bytes(human_projection),
    )
    _write_once(
        destination / MODEL_PROJECTION_PATH,
        _artifact_bytes(model_projection),
    )
    _write_once(
        destination / PARITY_RECEIPT_PATH,
        _artifact_bytes(receipt),
    )

    return verify_materialized_projections(
        root,
        output_root=destination,
    )


def _load_exact_artifact(
    path: Path,
    *,
    model_type: type[ModelT],
    expected_bytes: bytes,
) -> ModelT:
    if not path.is_file() or path.is_symlink():
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_ARTIFACT_MISSING",
            "required generated projection artifact is missing or unsafe",
        )

    observed = path.read_bytes()

    if observed != expected_bytes:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_ARTIFACT_BYTES_DRIFT",
            "generated projection artifact bytes drifted",
        )

    try:
        payload = json.loads(observed.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_ARTIFACT_JSON_INVALID",
            "generated projection artifact is not valid UTF-8 JSON",
        ) from error

    return model_type.model_validate(payload)


def verify_materialized_projections(
    repo_root: Path,
    *,
    output_root: Path | None = None,
) -> SemanticProjectionParityReceiptV1:
    """Verify exact generated bytes and re-run semantic parity reconstruction."""

    root = repo_root.resolve()
    destination = root if output_root is None else output_root.resolve()

    expected_human, expected_model, expected_receipt = build_projection_bundle(root)

    observed_human = _load_exact_artifact(
        destination / HUMAN_PROJECTION_PATH,
        model_type=HumanSemanticProjectionV1,
        expected_bytes=_artifact_bytes(expected_human),
    )
    observed_model = _load_exact_artifact(
        destination / MODEL_PROJECTION_PATH,
        model_type=ModelSemanticProjectionV1,
        expected_bytes=_artifact_bytes(expected_model),
    )
    observed_receipt = _load_exact_artifact(
        destination / PARITY_RECEIPT_PATH,
        model_type=SemanticProjectionParityReceiptV1,
        expected_bytes=_artifact_bytes(expected_receipt),
    )

    registry = load_frozen_registry(root)
    rebuilt_receipt = build_parity_receipt(
        registry,
        observed_human,
        observed_model,
    )

    if observed_receipt != rebuilt_receipt:
        raise SemanticProjectionError(
            "J7K_SHARED_SEMANTIC_PROJECTION_RECEIPT_DRIFT",
            "materialized parity receipt differs from reconstructed parity proof",
        )

    return observed_receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    try:
        args = parser.parse_args()
        repo_root = args.repo_root.resolve()

        if args.command == "write":
            receipt = write_projection_artifacts(repo_root)
        else:
            receipt = verify_materialized_projections(repo_root)

    except SemanticProjectionError as error:
        print(
            json.dumps(
                {
                    "error_code": error.error_code,
                    "safe_message": error.safe_message,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except ValidationError:
        print(
            json.dumps(
                {
                    "error_code": "J7K_SHARED_SEMANTIC_PROJECTION_TYPED_VALIDATION_FAILED",
                    "safe_message": "J7K typed semantic projection validation failed",
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except OSError:
        print(
            json.dumps(
                {
                    "error_code": "J7K_SHARED_SEMANTIC_PROJECTION_IO_FAILED",
                    "safe_message": "J7K local projection I/O failed",
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            receipt.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
