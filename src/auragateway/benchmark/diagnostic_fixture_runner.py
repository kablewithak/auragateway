"""Materialize and verify privacy-safe Batch 06 diagnostic prompt fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.benchmark.diagnostic_plan_runner import (
    DiagnosticDesignError,
    validate_diagnostic_design,
)
from auragateway.contracts.diagnostic_fixtures import (
    DiagnosticCohortFixtureRecord,
    DiagnosticFixtureManifest,
    DiagnosticFixtureRecipe,
    DiagnosticFixtureValidationSummary,
    ProtectedDiagnosticPromptBundle,
    ProtectedDiagnosticPromptCohort,
)

_DEFAULT_FIXTURE_ROOT = Path("data/evals/benchmark/diagnostic-fixtures-v1")
_FORBIDDEN_SYNTHETIC_MARKERS = (
    "@",
    "api_key",
    "password",
    "secret",
    "gsk_",
    "sk-",
    "-----begin",
    "bearer ",
)
_SAFE_ASCII_PATTERN = re.compile(r"^[\x20-\x7e]+$")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class DiagnosticFixtureError(Exception):
    """Expected metadata-safe fixture materialization or verification failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_REQUIRED_ASSET_MISSING",
            "A required diagnostic fixture asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_INVALID_JSON",
            "A diagnostic fixture asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_VALIDATION_FAILED",
            "A diagnostic fixture asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _deterministic_word_stream(
    seed: str,
    vocabulary: tuple[str, ...],
) -> Iterator[str]:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{seed}|{counter}".encode()).digest()
        index = int.from_bytes(digest[:4], byteorder="big") % len(vocabulary)
        yield_word = vocabulary[index]
        counter += 1
        yield yield_word


def _fit_padding(
    *,
    seed: str,
    vocabulary: tuple[str, ...],
    target_byte_count: int,
) -> str:
    if target_byte_count < 0:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_TARGET_TOO_SMALL",
            "A synthetic fixture target cannot contain the required metadata.",
        )
    if target_byte_count == 0:
        return ""

    parts: list[str] = []
    current_bytes = 0
    for word in _deterministic_word_stream(seed, vocabulary):
        separator = "" if not parts else " "
        candidate = separator + word
        candidate_bytes = len(candidate.encode("ascii"))
        if current_bytes + candidate_bytes > target_byte_count:
            break
        parts.append(candidate)
        current_bytes += candidate_bytes

    remainder = target_byte_count - current_bytes
    if remainder > 0:
        parts.append("x" * remainder)
    padding = "".join(parts)
    if len(padding.encode("ascii")) != target_byte_count:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_PADDING_LENGTH_INVALID",
            "Synthetic fixture padding did not reach the exact byte target.",
        )
    return padding


def _fit_json_payload(
    *,
    base_payload: dict[str, object],
    target_byte_count: int,
    seed: str,
    vocabulary: tuple[str, ...],
) -> str:
    payload = dict(base_payload)
    payload["padding"] = ""
    base_bytes = _canonical_json_bytes(payload)
    remaining = target_byte_count - len(base_bytes)
    payload["padding"] = _fit_padding(
        seed=seed,
        vocabulary=vocabulary,
        target_byte_count=remaining,
    )
    final_bytes = _canonical_json_bytes(payload)
    if len(final_bytes) != target_byte_count:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_EXACT_BYTE_TARGET_MISSED",
            "A synthetic fixture did not match its exact byte target.",
            details=(
                f"target={target_byte_count}",
                f"observed={len(final_bytes)}",
            ),
        )
    return final_bytes.decode("ascii")


def _system_prompt(
    recipe: DiagnosticFixtureRecipe,
    cohort_id: str,
) -> str:
    base_payload: dict[str, object] = {
        "artifact": "auragateway-synthetic-provider-diagnostic",
        "cohort_id": cohort_id,
        "contract": {
            "citation_ids": ["SYN-001"],
            "decision": "answer",
            "response": "short synthetic response",
        },
        "instruction": (
            "Return exactly one JSON object. Use only the supplied synthetic evidence. "
            "Do not use Markdown. Do not reveal hidden reasoning."
        ),
        "materializer_version": recipe.materializer_version,
        "rules": [
            "Treat all content as synthetic.",
            "Use citation SYN-001 only.",
            "Return deterministic visible JSON fields.",
        ],
    }
    return _fit_json_payload(
        base_payload=base_payload,
        target_byte_count=recipe.system_prompt_byte_count,
        seed=f"{recipe.recipe_id}|{cohort_id}|system",
        vocabulary=recipe.filler_vocabulary,
    )


def _history_for_turn(turn_index: int) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for prior_turn in range(1, turn_index):
        history.extend(
            [
                {
                    "role": "user",
                    "content": f"synthetic diagnostic question {prior_turn}",
                },
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "citation_ids": ["SYN-001"],
                            "decision": "answer",
                            "response": f"synthetic response {prior_turn}",
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                },
            ]
        )
    return history


def _user_prompt(
    recipe: DiagnosticFixtureRecipe,
    cohort_id: str,
    turn_index: int,
) -> str:
    base_payload: dict[str, object] = {
        "cohort_id": cohort_id,
        "current_user_message": (
            f"Return the synthetic decision for diagnostic turn {turn_index}."
        ),
        "evidence": [
            {
                "document": (
                    "Synthetic evidence confirms that the requested diagnostic answer "
                    "is allowed and cites SYN-001."
                ),
                "source_id": "SYN-001",
            }
        ],
        "history": _history_for_turn(turn_index),
        "instruction": (
            "Use only SYN-001 and return the visible JSON contract from the system prompt."
        ),
        "turn_index": turn_index,
    }
    target = recipe.user_prompt_byte_counts_by_turn[turn_index - 1]
    return _fit_json_payload(
        base_payload=base_payload,
        target_byte_count=target,
        seed=f"{recipe.recipe_id}|{cohort_id}|user|{turn_index}",
        vocabulary=recipe.filler_vocabulary,
    )


def _provider_request_payload(
    *,
    condition_label: Literal["condition_b", "condition_c"],
    recipe: DiagnosticFixtureRecipe,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, object]:
    # The local label is deliberately excluded from the provider-visible payload.
    _ = condition_label
    return {
        "max_completion_tokens": recipe.maximum_completion_tokens,
        "messages": [
            {"content": system_prompt, "role": "system"},
            {"content": user_prompt, "role": "user"},
        ],
        "model": recipe.provider_model_alias,
        "reasoning_effort": recipe.reasoning_effort,
        "store": recipe.store_enabled,
        "stream": recipe.streaming,
        "temperature": recipe.temperature_milli / 1000,
    }


def _assert_synthetic_text(text: str) -> None:
    if _SAFE_ASCII_PATTERN.fullmatch(text) is None:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_NON_ASCII_CONTENT",
            "Synthetic fixture text must use bounded printable ASCII.",
        )
    lowered = text.casefold()
    matched = tuple(item for item in _FORBIDDEN_SYNTHETIC_MARKERS if item in lowered)
    if matched:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_FORBIDDEN_CONTENT",
            "Synthetic fixture text contains a forbidden sensitive-data marker.",
            details=matched,
        )


def build_protected_prompt_bundle(
    recipe: DiagnosticFixtureRecipe,
) -> ProtectedDiagnosticPromptBundle:
    """Build six deterministic raw prompt cohorts without provider access."""

    cohorts: list[ProtectedDiagnosticPromptCohort] = []
    for cohort_id in recipe.cohort_ids:
        system_prompt = _system_prompt(recipe, cohort_id)
        user_prompts = (
            _user_prompt(recipe, cohort_id, 1),
            _user_prompt(recipe, cohort_id, 2),
            _user_prompt(recipe, cohort_id, 3),
        )
        _assert_synthetic_text(system_prompt)
        for user_prompt in user_prompts:
            _assert_synthetic_text(user_prompt)
        cohorts.append(
            ProtectedDiagnosticPromptCohort(
                cohort_id=cohort_id,
                system_prompt=system_prompt,
                user_prompts_by_turn=user_prompts,
            )
        )
    return ProtectedDiagnosticPromptBundle(
        fixture_id="batch-06-diagnostic-prompt-fixtures-v1",
        design_id=recipe.design_id,
        materializer_version=recipe.materializer_version,
        cohorts=tuple(cohorts),
    )


def _bundle_bytes(bundle: ProtectedDiagnosticPromptBundle) -> bytes:
    return _canonical_json_bytes(bundle.model_dump(mode="json"))


def build_fixture_manifest(
    *,
    recipe: DiagnosticFixtureRecipe,
    bundle: ProtectedDiagnosticPromptBundle,
    design_plan_sha256: str,
    design_manifest_sha256: str,
    recipe_sha256: str,
) -> DiagnosticFixtureManifest:
    """Project raw local fixtures into a committed content-free manifest."""

    records: list[DiagnosticCohortFixtureRecord] = []
    for cohort in bundle.cohorts:
        system_bytes = cohort.system_prompt.encode("ascii")
        user_bytes = (
            cohort.user_prompts_by_turn[0].encode("ascii"),
            cohort.user_prompts_by_turn[1].encode("ascii"),
            cohort.user_prompts_by_turn[2].encode("ascii"),
        )
        observed_user_byte_counts = (
            len(user_bytes[0]),
            len(user_bytes[1]),
            len(user_bytes[2]),
        )
        observed_total_byte_counts = (
            len(system_bytes) + len(user_bytes[0]),
            len(system_bytes) + len(user_bytes[1]),
            len(system_bytes) + len(user_bytes[2]),
        )
        if len(system_bytes) != recipe.system_prompt_byte_count:
            raise DiagnosticFixtureError(
                "DIAGNOSTIC_FIXTURE_SYSTEM_BYTE_COUNT_MISMATCH",
                "A generated system prompt missed the frozen byte target.",
                details=(cohort.cohort_id,),
            )
        if observed_user_byte_counts != recipe.user_prompt_byte_counts_by_turn:
            raise DiagnosticFixtureError(
                "DIAGNOSTIC_FIXTURE_USER_BYTE_COUNT_MISMATCH",
                "A generated user prompt missed the frozen byte target.",
                details=(cohort.cohort_id,),
            )
        if observed_total_byte_counts != recipe.total_prompt_byte_counts_by_turn:
            raise DiagnosticFixtureError(
                "DIAGNOSTIC_FIXTURE_TOTAL_BYTE_COUNT_MISMATCH",
                "A generated provider prompt missed the frozen total-byte target.",
                details=(cohort.cohort_id,),
            )

        condition_b_payloads = (
            _provider_request_payload(
                condition_label="condition_b",
                recipe=recipe,
                system_prompt=cohort.system_prompt,
                user_prompt=cohort.user_prompts_by_turn[0],
            ),
            _provider_request_payload(
                condition_label="condition_b",
                recipe=recipe,
                system_prompt=cohort.system_prompt,
                user_prompt=cohort.user_prompts_by_turn[1],
            ),
            _provider_request_payload(
                condition_label="condition_b",
                recipe=recipe,
                system_prompt=cohort.system_prompt,
                user_prompt=cohort.user_prompts_by_turn[2],
            ),
        )
        condition_c_payloads = (
            _provider_request_payload(
                condition_label="condition_c",
                recipe=recipe,
                system_prompt=cohort.system_prompt,
                user_prompt=cohort.user_prompts_by_turn[0],
            ),
            _provider_request_payload(
                condition_label="condition_c",
                recipe=recipe,
                system_prompt=cohort.system_prompt,
                user_prompt=cohort.user_prompts_by_turn[1],
            ),
            _provider_request_payload(
                condition_label="condition_c",
                recipe=recipe,
                system_prompt=cohort.system_prompt,
                user_prompt=cohort.user_prompts_by_turn[2],
            ),
        )
        condition_b_hashes = (
            _sha256_bytes(_canonical_json_bytes(condition_b_payloads[0])),
            _sha256_bytes(_canonical_json_bytes(condition_b_payloads[1])),
            _sha256_bytes(_canonical_json_bytes(condition_b_payloads[2])),
        )
        condition_c_hashes = (
            _sha256_bytes(_canonical_json_bytes(condition_c_payloads[0])),
            _sha256_bytes(_canonical_json_bytes(condition_c_payloads[1])),
            _sha256_bytes(_canonical_json_bytes(condition_c_payloads[2])),
        )
        if condition_b_hashes != condition_c_hashes:
            raise DiagnosticFixtureError(
                "DIAGNOSTIC_FIXTURE_PROVIDER_REQUEST_EQUIVALENCE_FAILED",
                "Condition B and condition C provider-visible request bytes diverged.",
                details=(cohort.cohort_id,),
            )

        records.append(
            DiagnosticCohortFixtureRecord(
                cohort_id=cohort.cohort_id,
                system_prompt_sha256=_sha256_bytes(system_bytes),
                system_prompt_byte_count=recipe.system_prompt_byte_count,
                user_prompt_sha256_by_turn=(
                    _sha256_bytes(user_bytes[0]),
                    _sha256_bytes(user_bytes[1]),
                    _sha256_bytes(user_bytes[2]),
                ),
                user_prompt_byte_counts_by_turn=(recipe.user_prompt_byte_counts_by_turn),
                total_prompt_byte_counts_by_turn=(recipe.total_prompt_byte_counts_by_turn),
                input_token_estimates_by_turn=(recipe.input_token_estimates_by_turn),
                condition_b_request_sha256_by_turn=condition_b_hashes,
                condition_c_request_sha256_by_turn=condition_c_hashes,
            )
        )

    return DiagnosticFixtureManifest(
        fixture_id="batch-06-diagnostic-prompt-fixtures-v1",
        design_id=recipe.design_id,
        design_plan_path=("data/evals/benchmark/diagnostic-design-v1/experiment_plan.json"),
        design_plan_sha256=design_plan_sha256,
        design_manifest_path=("data/evals/benchmark/diagnostic-design-v1/manifest.json"),
        design_manifest_sha256=design_manifest_sha256,
        recipe_path=("data/evals/benchmark/diagnostic-fixtures-v1/fixture_recipe.json"),
        recipe_sha256=recipe_sha256,
        materializer_version=recipe.materializer_version,
        protected_prompt_bundle_path=(
            ".local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json"
        ),
        protected_prompt_bundle_sha256=_sha256_bytes(_bundle_bytes(bundle)),
        cohorts=tuple(records),
    )


def _load_public_assets(
    repo_root: Path,
    fixture_root: Path,
) -> tuple[DiagnosticFixtureRecipe, DiagnosticFixtureManifest]:
    validate_diagnostic_design(repo_root)

    resolved_root = repo_root / fixture_root
    recipe_path = resolved_root / "fixture_recipe.json"
    manifest_path = resolved_root / "fixture_manifest.json"
    recipe = _load_model(recipe_path, DiagnosticFixtureRecipe)
    manifest = _load_model(manifest_path, DiagnosticFixtureManifest)

    design_plan_path = repo_root / manifest.design_plan_path
    design_manifest_path = repo_root / manifest.design_manifest_path
    if _sha256_file(design_plan_path) != manifest.design_plan_sha256:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_DESIGN_PLAN_MISMATCH",
            "The fixture manifest targets different diagnostic design-plan bytes.",
            path=str(design_plan_path),
        )
    if _sha256_file(design_manifest_path) != manifest.design_manifest_sha256:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_DESIGN_MANIFEST_MISMATCH",
            "The fixture manifest targets different diagnostic design-manifest bytes.",
            path=str(design_manifest_path),
        )
    if _sha256_file(recipe_path) != manifest.recipe_sha256:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_RECIPE_MISMATCH",
            "The fixture recipe no longer matches its committed manifest.",
            path=str(recipe_path),
        )
    if recipe.design_id != manifest.design_id:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_DESIGN_ID_MISMATCH",
            "The recipe and fixture manifest identify different diagnostic designs.",
        )
    return recipe, manifest


def _expected_manifest(
    *,
    repo_root: Path,
    recipe: DiagnosticFixtureRecipe,
    bundle: ProtectedDiagnosticPromptBundle,
    manifest: DiagnosticFixtureManifest,
) -> DiagnosticFixtureManifest:
    return build_fixture_manifest(
        recipe=recipe,
        bundle=bundle,
        design_plan_sha256=_sha256_file(repo_root / manifest.design_plan_path),
        design_manifest_sha256=_sha256_file(repo_root / manifest.design_manifest_path),
        recipe_sha256=_sha256_file(repo_root / manifest.recipe_path),
    )


def _assert_manifest_matches(
    observed: DiagnosticFixtureManifest,
    expected: DiagnosticFixtureManifest,
) -> None:
    if observed.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_MANIFEST_REPRODUCTION_FAILED",
            "The committed fixture manifest does not reproduce from the frozen recipe.",
        )


def _protected_path(
    repo_root: Path,
    manifest: DiagnosticFixtureManifest,
    override: Path | None,
) -> Path:
    if override is not None:
        return override
    return repo_root / manifest.protected_prompt_bundle_path


def materialize_diagnostic_fixtures(
    repo_root: Path,
    *,
    fixture_root: Path = _DEFAULT_FIXTURE_ROOT,
    protected_path_override: Path | None = None,
) -> DiagnosticFixtureValidationSummary:
    """Materialize deterministic synthetic prompts beneath ignored local storage."""

    recipe, manifest = _load_public_assets(repo_root, fixture_root)
    bundle = build_protected_prompt_bundle(recipe)
    expected = _expected_manifest(
        repo_root=repo_root,
        recipe=recipe,
        bundle=bundle,
        manifest=manifest,
    )
    _assert_manifest_matches(manifest, expected)

    protected_path = _protected_path(
        repo_root,
        manifest,
        protected_path_override,
    )
    protected_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _bundle_bytes(bundle)
    with protected_path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    if _sha256_file(protected_path) != manifest.protected_prompt_bundle_sha256:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_PROTECTED_BUNDLE_WRITE_MISMATCH",
            "The protected prompt bundle does not match the committed identity.",
            path=str(protected_path),
        )

    return DiagnosticFixtureValidationSummary(
        command="materialize",
        fixture_id=manifest.fixture_id,
        protected_prompt_bundle_sha256=manifest.protected_prompt_bundle_sha256,
    )


def verify_diagnostic_fixtures(
    repo_root: Path,
    *,
    fixture_root: Path = _DEFAULT_FIXTURE_ROOT,
    protected_path_override: Path | None = None,
) -> DiagnosticFixtureValidationSummary:
    """Verify public identities and protected local prompt bytes."""

    recipe, manifest = _load_public_assets(repo_root, fixture_root)
    protected_path = _protected_path(
        repo_root,
        manifest,
        protected_path_override,
    )
    protected_bundle = _load_model(
        protected_path,
        ProtectedDiagnosticPromptBundle,
    )
    expected_bundle = build_protected_prompt_bundle(recipe)
    if protected_bundle.model_dump(mode="json") != expected_bundle.model_dump(mode="json"):
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_PROTECTED_BUNDLE_CONTENT_MISMATCH",
            "The protected prompt bundle does not reproduce from the frozen recipe.",
            path=str(protected_path),
        )
    if _sha256_file(protected_path) != manifest.protected_prompt_bundle_sha256:
        raise DiagnosticFixtureError(
            "DIAGNOSTIC_FIXTURE_PROTECTED_BUNDLE_HASH_MISMATCH",
            "The protected prompt bundle no longer matches the committed identity.",
            path=str(protected_path),
        )

    expected_manifest = _expected_manifest(
        repo_root=repo_root,
        recipe=recipe,
        bundle=protected_bundle,
        manifest=manifest,
    )
    _assert_manifest_matches(manifest, expected_manifest)

    return DiagnosticFixtureValidationSummary(
        command="verify",
        fixture_id=manifest.fixture_id,
        protected_prompt_bundle_sha256=manifest.protected_prompt_bundle_sha256,
    )


def _error_envelope(
    exc: DiagnosticFixtureError | DiagnosticDesignError,
) -> str:
    return json.dumps(
        {
            "error_code": exc.error_code,
            "safe_message": exc.safe_message,
            "path": exc.path,
            "details": exc.details,
        },
        indent=2,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Materialize or verify privacy-safe Batch 06 diagnostic prompt fixtures.")
    )
    parser.add_argument(
        "command",
        choices=("materialize", "verify"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=_DEFAULT_FIXTURE_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "materialize":
            summary = materialize_diagnostic_fixtures(
                repo_root,
                fixture_root=args.fixture_root,
            )
        else:
            summary = verify_diagnostic_fixtures(
                repo_root,
                fixture_root=args.fixture_root,
            )
    except (DiagnosticFixtureError, DiagnosticDesignError) as exc:
        print(_error_envelope(exc), file=sys.stderr)
        return 1

    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
