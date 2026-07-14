"""Validate the Groq SDK cache-schema compatibility review without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from collections.abc import Mapping, Sequence
from importlib import metadata
from pathlib import Path
from typing import TypeVar

from groq.types.chat.chat_completion import ChatCompletion
from pydantic import BaseModel, ValidationError

from auragateway.contracts.cache_telemetry_capture import (
    GroqCacheTelemetryCapture,
)
from auragateway.contracts.groq_sdk_cache_schema_compatibility import (
    GroqSdkCacheSchemaCompatibilityManifest,
    GroqSdkCacheSchemaCompatibilityReview,
    GroqSdkCacheSchemaCompatibilitySummary,
    GroqSdkProbeCaseId,
    GroqSdkProbeExpectation,
)
from auragateway.contracts.provider import ProviderInvocationRequest, ProviderName
from auragateway.providers.base import LiveProviderInvocation, ProtectedProviderPrompt
from auragateway.providers.groq import GroqProviderAdapter

_DEFAULT_REVIEW_ROOT = Path("data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1")
_EXPECTED_GROQ_VERSION = "1.5.0"
_EXPECTED_DEPENDENCY = "groq>=1.5,<2"
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class GroqSdkCacheSchemaCompatibilityError(Exception):
    """Expected metadata-safe compatibility review failure."""

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


class _SyntheticCompletionClient:
    """Return one real SDK response object without performing external I/O."""

    def __init__(self, response: ChatCompletion) -> None:
        self._response = response
        self.call_count = 0

    def create(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        model: str,
        max_completion_tokens: int,
        temperature: float,
        stream: bool,
        store: bool,
        reasoning_effort: str,
    ) -> ChatCompletion:
        self.call_count += 1
        return self._response


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_ASSET_MISSING",
            "A required Groq SDK compatibility asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_ASSET_MISSING",
            "A required Groq SDK compatibility asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_INVALID_JSON",
            "A Groq SDK compatibility asset is not valid JSON.",
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
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_VALIDATION_FAILED",
            "A Groq SDK compatibility asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _validate_manifest(
    repo_root: Path,
    review: GroqSdkCacheSchemaCompatibilityReview,
    manifest: GroqSdkCacheSchemaCompatibilityManifest,
) -> None:
    if manifest.review_id != review.review_id:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_ID_MISMATCH",
            "The compatibility review and manifest identify different reviews.",
        )
    checks = (
        (repo_root / manifest.review_path, manifest.review_sha256, "review"),
        (repo_root / manifest.adr_path, manifest.adr_sha256, "ADR"),
        (repo_root / manifest.report_path, manifest.report_sha256, "report"),
    )
    for path, expected, label in checks:
        observed = _sha256_file(path)
        if observed != expected:
            raise GroqSdkCacheSchemaCompatibilityError(
                "GROQ_SDK_COMPATIBILITY_HASH_MISMATCH",
                f"The Groq SDK compatibility {label} no longer matches its manifest.",
                path=str(path),
                details=(f"expected={expected}", f"observed={observed}"),
            )


def _validate_source_bindings(
    repo_root: Path,
    review: GroqSdkCacheSchemaCompatibilityReview,
) -> None:
    for binding in review.source_bindings:
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise GroqSdkCacheSchemaCompatibilityError(
                "GROQ_SDK_COMPATIBILITY_SOURCE_BINDING_MISMATCH",
                "A reviewed Groq compatibility source no longer matches.",
                path=binding.path,
                details=(f"expected={binding.sha256}", f"observed={observed}"),
            )


def _validate_dependency(repo_root: Path, review: GroqSdkCacheSchemaCompatibilityReview) -> None:
    path = repo_root / "pyproject.toml"
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_PYPROJECT_MISSING",
            "The project dependency declaration could not be found.",
            path=str(path),
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_PYPROJECT_INVALID",
            "The project dependency declaration is not valid TOML.",
            path=str(path),
        ) from exc

    project = payload.get("project")
    dependencies = project.get("dependencies") if isinstance(project, dict) else None
    if not isinstance(dependencies, list) or _EXPECTED_DEPENDENCY not in dependencies:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_DEPENDENCY_MISMATCH",
            "The reviewed Groq dependency requirement is not declared.",
            path=str(path),
            details=(f"expected={_EXPECTED_DEPENDENCY}",),
        )
    if review.declared_sdk_requirement != _EXPECTED_DEPENDENCY:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_REVIEW_DEPENDENCY_MISMATCH",
            "The review records a different Groq dependency requirement.",
        )


def _installed_sdk_version() -> str:
    try:
        return metadata.version("groq")
    except metadata.PackageNotFoundError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_SDK_UNAVAILABLE",
            "The Groq SDK is not installed in the active environment.",
        ) from exc


def _payload(
    case_id: GroqSdkProbeCaseId,
) -> dict[str, object]:
    usage: dict[str, object] = {
        "prompt_tokens": 1000,
        "completion_tokens": 12,
        "total_tokens": 1012,
        "total_time": 0.15,
    }
    x_groq: dict[str, object] | None = None
    if case_id is GroqSdkProbeCaseId.DETAILS_EXPLICIT_NULL:
        usage["prompt_tokens_details"] = None
    elif case_id is GroqSdkProbeCaseId.CACHED_TOKENS_ZERO:
        usage["prompt_tokens_details"] = {"cached_tokens": 0}
    elif case_id is GroqSdkProbeCaseId.CACHED_TOKENS_POSITIVE:
        usage["prompt_tokens_details"] = {"cached_tokens": 600}
        x_groq = {
            "id": "req_synthetic_cache_schema_probe",
            "usage": {
                "dram_cached_tokens": 800,
                "sram_cached_tokens": 200,
            },
        }

    payload: dict[str, object] = {
        "id": f"chatcmpl-synthetic-{case_id.value}",
        "choices": [
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": (
                        '{"decision":"answer","response":"synthetic","citation_ids":["SYN-001"]}'
                    ),
                    "role": "assistant",
                },
            }
        ],
        "created": 0,
        "model": "openai/gpt-oss-20b",
        "object": "chat.completion",
        "usage": usage,
    }
    if x_groq is not None:
        payload["x_groq"] = x_groq
    return payload


def _invocation(case_id: GroqSdkProbeCaseId) -> LiveProviderInvocation:
    fixture_id = f"groq-sdk-{case_id.value.replace('_', '-')}"
    return LiveProviderInvocation(
        request=ProviderInvocationRequest(
            request_id=f"{fixture_id}-request",
            fixture_id=fixture_id,
            provider=ProviderName.GROQ,
            model_alias="groq-gpt-oss-20b",
            static_prefix_fingerprint="a" * 64,
            input_token_count=1000,
            output_token_budget=32,
        ),
        prompt=ProtectedProviderPrompt(
            system_prompt="synthetic stable system prompt",
            user_prompt="synthetic user request",
        ),
        timeout_seconds=30.0,
    )


def _probe_real_sdk_case(
    case_id: GroqSdkProbeCaseId,
    installed_sdk_version: str,
) -> tuple[GroqSdkProbeExpectation, int]:
    try:
        sdk_response = ChatCompletion.model_validate(_payload(case_id))
    except ValidationError as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_SYNTHETIC_RESPONSE_INVALID",
            "A required synthetic Groq SDK response failed validation.",
            details=tuple(
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in exc.errors(include_url=False, include_input=False)
            ),
        ) from exc

    usage = sdk_response.usage
    if usage is None:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_USAGE_MISSING",
            "The synthetic Groq SDK response did not retain usage.",
        )
    details = usage.prompt_tokens_details
    sdk_details_present = "prompt_tokens_details" in usage.model_fields_set
    sdk_cached_present = details is not None and "cached_tokens" in details.model_fields_set
    sdk_cached_value = details.cached_tokens if details is not None else None

    dumped = sdk_response.model_dump()
    dumped_usage = dumped.get("usage")
    if not isinstance(dumped_usage, dict):
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_MODEL_DUMP_USAGE_INVALID",
            "The Groq SDK model dump did not retain a usage mapping.",
        )
    dumped_details = dumped_usage.get("prompt_tokens_details")
    expected_dump_value: int | None = None
    if isinstance(dumped_details, dict):
        raw_value = dumped_details.get("cached_tokens")
        if isinstance(raw_value, int) and not isinstance(raw_value, bool):
            expected_dump_value = raw_value
    if expected_dump_value != sdk_cached_value:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_MODEL_DUMP_VALUE_MISMATCH",
            "The Groq SDK model dump changed the cached-token value.",
            details=(f"case={case_id.value}",),
        )

    client = _SyntheticCompletionClient(sdk_response)
    adapter = GroqProviderAdapter(
        client,
        installed_sdk_version=installed_sdk_version,
    )
    call = adapter.invoke(_invocation(case_id))
    capture = call.success_telemetry_shape
    if not isinstance(capture, GroqCacheTelemetryCapture):
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_ADAPTER_CAPTURE_MISSING",
            "The Groq adapter did not emit its typed cache telemetry capture.",
            details=(f"case={case_id.value}",),
        )

    return (
        GroqSdkProbeExpectation(
            case_id=case_id,
            sdk_prompt_tokens_details_field_present=sdk_details_present,
            sdk_cached_tokens_field_present=sdk_cached_present,
            sdk_cached_tokens_value=sdk_cached_value,
            adapter_prompt_tokens_details_present=capture.prompt_tokens_details_present,
            adapter_billing_cached_tokens_field_present=(
                capture.billing_cached_tokens_field_present
            ),
            adapter_billing_cached_input_tokens=capture.billing_cached_input_tokens,
            adapter_billing_observation_state=capture.billing_observation_state,
        ),
        client.call_count,
    )


def _validate_nested_null_rejection() -> None:
    payload = _payload(GroqSdkProbeCaseId.CACHED_TOKENS_ZERO)
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        raise AssertionError("synthetic usage fixture must be a mapping")
    usage["prompt_tokens_details"] = {"cached_tokens": None}

    try:
        ChatCompletion.model_validate(payload)
    except ValidationError:
        return
    raise GroqSdkCacheSchemaCompatibilityError(
        "GROQ_SDK_COMPATIBILITY_NULLABILITY_DRIFT",
        "The Groq SDK unexpectedly accepted a null nested cached-token value.",
    )


def _validate_probe_expectations(
    review: GroqSdkCacheSchemaCompatibilityReview,
    installed_sdk_version: str,
) -> int:
    synthetic_adapter_probe_count = 0
    for case_id in GroqSdkProbeCaseId:
        observed, adapter_calls = _probe_real_sdk_case(case_id, installed_sdk_version)
        expected = review.expectation_for(case_id)
        if observed != expected:
            raise GroqSdkCacheSchemaCompatibilityError(
                "GROQ_SDK_COMPATIBILITY_PROBE_MISMATCH",
                "A real Groq SDK object no longer matches the frozen adapter expectation.",
                details=(
                    f"case={case_id.value}",
                    f"expected={expected.model_dump_json()}",
                    f"observed={observed.model_dump_json()}",
                ),
            )
        synthetic_adapter_probe_count += adapter_calls
    _validate_nested_null_rejection()
    return synthetic_adapter_probe_count


def _validate_git_state(repo_root: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_GIT_STATE_UNAVAILABLE",
            "The repository Git state could not be inspected.",
        ) from exc
    if result.stdout.strip():
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_WORKTREE_NOT_CLEAN",
            "Compatibility validation requires a clean working tree.",
        )


def validate_groq_sdk_cache_schema_compatibility(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
    require_clean_worktree: bool = False,
) -> GroqSdkCacheSchemaCompatibilitySummary:
    """Validate frozen sources and real SDK-object adapter parity without external I/O."""

    resolved_root = repo_root / review_root
    review = _load_model(
        resolved_root / "review.json",
        GroqSdkCacheSchemaCompatibilityReview,
    )
    manifest = _load_model(
        resolved_root / "manifest.json",
        GroqSdkCacheSchemaCompatibilityManifest,
    )

    _validate_manifest(repo_root, review, manifest)
    _validate_source_bindings(repo_root, review)
    _validate_dependency(repo_root, review)

    installed_sdk_version = _installed_sdk_version()
    if installed_sdk_version != _EXPECTED_GROQ_VERSION:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_VERSION_MISMATCH",
            "The active Groq SDK version differs from the reviewed version.",
            details=(
                f"expected={_EXPECTED_GROQ_VERSION}",
                f"observed={installed_sdk_version}",
            ),
        )
    if review.installed_sdk_version != installed_sdk_version:
        raise GroqSdkCacheSchemaCompatibilityError(
            "GROQ_SDK_COMPATIBILITY_REVIEW_VERSION_MISMATCH",
            "The compatibility review records a different installed SDK version.",
        )

    synthetic_adapter_probe_count = _validate_probe_expectations(
        review,
        installed_sdk_version,
    )
    if require_clean_worktree:
        _validate_git_state(repo_root)

    return GroqSdkCacheSchemaCompatibilitySummary(
        review_id=review.review_id,
        status=review.status,
        installed_sdk_version=installed_sdk_version,
        primary_classification=review.primary_classification,
        exact_provider_omission_cause_resolved=review.exact_provider_omission_cause_resolved,
        probe_case_count=len(review.probe_expectations),
        synthetic_adapter_probe_count=synthetic_adapter_probe_count,
        sdk_upgrade_required=review.sdk_upgrade_required,
        adapter_change_required=review.adapter_change_required,
        provider_call_authorized=review.provider_call_authorized,
        calibration_rerun_authorized=review.calibration_rerun_authorized,
        benchmark_execution_authorized=review.benchmark_execution_authorized,
        next_gate=review.next_gate,
    )


def _error_envelope(exc: GroqSdkCacheSchemaCompatibilityError) -> str:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--review-root", type=Path, default=_DEFAULT_REVIEW_ROOT)
    parser.add_argument("--require-clean-worktree", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = validate_groq_sdk_cache_schema_compatibility(
            args.repo_root.resolve(),
            review_root=args.review_root,
            require_clean_worktree=args.require_clean_worktree,
        )
    except GroqSdkCacheSchemaCompatibilityError as exc:
        print(_error_envelope(exc), file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
