"""Activate and preflight the bounded OpenRouter Hy3 capability probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.benchmark.openrouter_hy3_probe_prompt import (
    derive_session_id,
    validate_stable_prefix,
)
from auragateway.contracts.openrouter_hy3_capability_probe_activation import (
    OpenRouterProbeActivationAuthorization,
    OpenRouterProbeActivationErrorEnvelope,
    OpenRouterProbeActivationManifest,
    OpenRouterProbeActivationReport,
    OpenRouterProbeActivationRuntimePolicy,
    OpenRouterProbeActivationSummary,
    OpenRouterProbeKeyStatusEnvelope,
    OpenRouterProbeLocalPreparationReceipt,
    OpenRouterProbeModelCatalog,
    OpenRouterProbePreflightReceipt,
    OpenRouterProbeProtectedCall,
    OpenRouterProbeProtectedPromptBundle,
)
from auragateway.contracts.openrouter_hy3_capability_probe_authorization import (
    OpenRouterProbePromptRecipe,
)
from auragateway.providers.openrouter_preflight import OpenRouterActivationPreflightClient

_ACTIVATION_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-v1")
_REVIEW_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1")
_ADR_PATH = Path("docs/adr/openrouter-hy3-capability-probe-activation.md")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Activation.md")
_CONTRACT_PATH = Path("src/auragateway/contracts/openrouter_hy3_capability_probe_activation.py")
_RUNNER_PATH = Path(
    "src/auragateway/benchmark/openrouter_hy3_capability_probe_activation_runner.py"
)
_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)


class OpenRouterProbeActivationError(Exception):
    """Expected metadata-safe activation failure."""

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


class _PreflightClient(Protocol):
    def get_key_status(self, *, timeout_seconds: float) -> Mapping[str, object]:
        """Return authenticated key metadata."""

    def get_models(self, *, timeout_seconds: float) -> Mapping[str, object]:
        """Return current OpenRouter model catalog metadata."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_FILE_READ_FAILED",
            "A required activation file could not be read.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _model_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_JSON_INVALID",
            "A required activation JSON asset could not be loaded.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _load_model(path: Path, model_type: type[_MODEL_T]) -> _MODEL_T:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_CONTRACT_INVALID",
            "An activation asset violates its typed contract.",
            path=str(path),
            details=details,
        ) from exc


def _write_bytes(path: Path, payload: bytes, *, refuse_drift: bool = True) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = path.read_bytes()
            if refuse_drift and existing != payload:
                raise OpenRouterProbeActivationError(
                    "OPENROUTER_HY3_LOCAL_ARTIFACT_DRIFT",
                    "A protected local artifact already exists with different content.",
                    path=str(path),
                )
            if existing == payload:
                return
        with path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OpenRouterProbeActivationError:
        raise
    except OSError as exc:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_LOCAL_WRITE_FAILED",
            "A protected local artifact could not be retained safely.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _build_prompt_bundle(
    authorization: OpenRouterProbeActivationAuthorization,
    recipe: OpenRouterProbePromptRecipe,
) -> OpenRouterProbeProtectedPromptBundle:
    stable_prefix = validate_stable_prefix(recipe)
    session_id = derive_session_id(recipe)
    return OpenRouterProbeProtectedPromptBundle(
        bundle_id="openrouter-hy3-capability-probe-prompt-bundle-v1",
        authorization_id=authorization.authorization_id,
        recipe_id=recipe.recipe_id,
        session_id=session_id,
        stable_prefix=stable_prefix,
        stable_prefix_sha256=recipe.generated_prefix_sha256,
        stable_prefix_bytes=recipe.generated_prefix_bytes,
        calls=(
            OpenRouterProbeProtectedCall(
                logical_call_index=0,
                request_role="cold_probe",
                request_id="openrouter-hy3-cold-probe-v1",
                fixture_id="openrouter-hy3-cold-probe-v1",
                user_suffix=recipe.cold_suffix,
                expected_output="COLD-PROBE-ACK",
            ),
            OpenRouterProbeProtectedCall(
                logical_call_index=1,
                request_role="warm_probe",
                request_id="openrouter-hy3-warm-probe-v1",
                fixture_id="openrouter-hy3-warm-probe-v1",
                user_suffix=recipe.warm_suffix,
                expected_output="WARM-PROBE-ACK",
            ),
        ),
    )


def _validate_manifest(
    repo_root: Path,
    manifest: OpenRouterProbeActivationManifest,
) -> None:
    expected = {
        "authorization_sha256": _ACTIVATION_ROOT / "authorization.json",
        "runtime_policy_sha256": _ACTIVATION_ROOT / "runtime_policy.json",
        "activation_report_sha256": _ACTIVATION_ROOT / "activation_report.json",
        "contract_sha256": _CONTRACT_PATH,
        "runner_sha256": _RUNNER_PATH,
        "adr_sha256": _ADR_PATH,
        "report_sha256": _REPORT_PATH,
    }
    mismatches = tuple(
        f"{field}: expected={getattr(manifest, field)} observed={_sha256_file(repo_root / path)}"
        for field, path in expected.items()
        if getattr(manifest, field) != _sha256_file(repo_root / path)
    )
    if mismatches:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_MANIFEST_MISMATCH",
            "The activation manifest no longer matches committed assets.",
            details=mismatches,
        )


def _load_activation(
    repo_root: Path,
) -> tuple[
    OpenRouterProbeActivationAuthorization,
    OpenRouterProbeActivationRuntimePolicy,
    OpenRouterProbeActivationReport,
]:
    root = repo_root / _ACTIVATION_ROOT
    authorization = _load_model(
        root / "authorization.json",
        OpenRouterProbeActivationAuthorization,
    )
    policy = _load_model(
        root / "runtime_policy.json",
        OpenRouterProbeActivationRuntimePolicy,
    )
    report = _load_model(
        root / "activation_report.json",
        OpenRouterProbeActivationReport,
    )
    manifest = _load_model(
        root / "activation_manifest.json",
        OpenRouterProbeActivationManifest,
    )
    if policy.authorization_id != authorization.authorization_id:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_ID_MISMATCH",
            "Runtime policy does not match the active authorization.",
        )
    if report.authorization_id != authorization.authorization_id:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_ID_MISMATCH",
            "Activation report does not match the active authorization.",
        )
    if manifest.authorization_id != authorization.authorization_id:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_ACTIVATION_ID_MISMATCH",
            "Activation manifest does not match the active authorization.",
        )
    for binding in authorization.bindings:
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise OpenRouterProbeActivationError(
                "OPENROUTER_HY3_ACTIVATION_BINDING_MISMATCH",
                "A reviewed activation source input no longer matches.",
                path=binding.path,
                details=(f"expected={binding.sha256}", f"observed={observed}"),
            )
    _validate_manifest(repo_root, manifest)
    recipe = _load_model(
        repo_root / _REVIEW_ROOT / "prompt_recipe.json",
        OpenRouterProbePromptRecipe,
    )
    expected_bundle = _build_prompt_bundle(authorization, recipe)
    expected_bytes = _model_bytes(expected_bundle)
    if _sha256_bytes(expected_bytes) != authorization.protected_prompt_bundle_sha256:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_PROMPT_BUNDLE_HASH_MISMATCH",
            "The active authorization does not match the deterministic prompt bundle.",
        )
    if len(expected_bytes) != authorization.protected_prompt_bundle_bytes:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_PROMPT_BUNDLE_SIZE_MISMATCH",
            "The active authorization does not match the prompt bundle byte count.",
        )
    return authorization, policy, report


def _local_paths(
    repo_root: Path,
    authorization: OpenRouterProbeActivationAuthorization,
) -> dict[str, Path]:
    paths = authorization.evidence_paths
    return {
        "bundle": repo_root / paths.protected_prompt_bundle_path,
        "preparation": repo_root / paths.protected_preparation_receipt_path,
        "preflight": repo_root / paths.protected_preflight_receipt_path,
        "journal": repo_root / paths.protected_journal_path,
        "raw": repo_root / paths.protected_raw_responses_path,
        "parsed": repo_root / paths.protected_parsed_responses_path,
    }


def _load_and_validate_local_bundle(
    repo_root: Path,
    authorization: OpenRouterProbeActivationAuthorization,
) -> tuple[OpenRouterProbeProtectedPromptBundle, OpenRouterProbeLocalPreparationReceipt]:
    paths = _local_paths(repo_root, authorization)
    bundle = _load_model(paths["bundle"], OpenRouterProbeProtectedPromptBundle)
    receipt = _load_model(paths["preparation"], OpenRouterProbeLocalPreparationReceipt)
    bundle_hash = _sha256_file(paths["bundle"])
    if bundle_hash != authorization.protected_prompt_bundle_sha256:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_LOCAL_BUNDLE_MISMATCH",
            "The protected prompt bundle does not match the active authorization.",
            path=str(paths["bundle"]),
        )
    if receipt.prompt_bundle_sha256 != bundle_hash:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_LOCAL_RECEIPT_MISMATCH",
            "The local preparation receipt does not match the prompt bundle.",
            path=str(paths["preparation"]),
        )
    session_hash = _sha256_bytes(bundle.session_id.encode("utf-8"))
    if receipt.session_id_sha256 != session_hash:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_LOCAL_SESSION_MISMATCH",
            "The local preparation receipt does not match the protected session.",
        )
    for name in ("journal", "raw", "parsed"):
        path = paths[name]
        if not path.is_file() or path.stat().st_size != 0:
            raise OpenRouterProbeActivationError(
                "OPENROUTER_HY3_LOCAL_BOUNDARY_INVALID",
                "Protected execution files must exist and remain empty before execution.",
                path=str(path),
            )
    return bundle, receipt


def validate_openrouter_probe_activation(repo_root: Path) -> OpenRouterProbeActivationSummary:
    """Validate the committed activation without reading credentials or using the network."""

    authorization, _, _ = _load_activation(repo_root)
    paths = _local_paths(repo_root, authorization)
    bundle_ready = paths["bundle"].is_file() and paths["preparation"].is_file()
    preflight_passed = paths["preflight"].is_file()
    return OpenRouterProbeActivationSummary(
        command="validate",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        protected_prompt_bundle_ready=bundle_ready,
        live_preflight_passed=preflight_passed,
        credential_accessed=False,
        network_request_count=0,
        next_gate=(
            "capability_probe_execution_confirmation"
            if preflight_passed
            else "protected_local_preparation"
        ),
    )


def prepare_openrouter_probe_local(repo_root: Path) -> OpenRouterProbeActivationSummary:
    """Generate the exact protected prompt bundle and empty execution sinks locally."""

    authorization, _, _ = _load_activation(repo_root)
    recipe = _load_model(
        repo_root / _REVIEW_ROOT / "prompt_recipe.json",
        OpenRouterProbePromptRecipe,
    )
    bundle = _build_prompt_bundle(authorization, recipe)
    bundle_bytes = _model_bytes(bundle)
    if _sha256_bytes(bundle_bytes) != authorization.protected_prompt_bundle_sha256:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_PROMPT_BUNDLE_HASH_MISMATCH",
            "Generated prompt bundle does not match the active authorization.",
        )
    paths = _local_paths(repo_root, authorization)
    _write_bytes(paths["bundle"], bundle_bytes)
    for name in ("journal", "raw", "parsed"):
        _write_bytes(paths[name], b"")
    receipt = OpenRouterProbeLocalPreparationReceipt(
        authorization_id=authorization.authorization_id,
        prompt_bundle_sha256=_sha256_bytes(bundle_bytes),
        prompt_bundle_bytes=len(bundle_bytes),
        session_id_sha256=_sha256_bytes(bundle.session_id.encode("utf-8")),
    )
    _write_bytes(paths["preparation"], _model_bytes(receipt))
    return OpenRouterProbeActivationSummary(
        command="prepare-local",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        protected_prompt_bundle_ready=True,
        live_preflight_passed=paths["preflight"].is_file(),
        credential_accessed=False,
        network_request_count=0,
        next_gate="live_key_and_route_preflight",
    )


def preflight_openrouter_probe(
    repo_root: Path,
    *,
    confirmation_phrase: str,
    client: _PreflightClient | None = None,
    environ: Mapping[str, str] | None = None,
) -> OpenRouterProbeActivationSummary:
    """Perform two non-inference preflight requests and retain a protected receipt."""

    authorization, _, _ = _load_activation(repo_root)
    if confirmation_phrase != authorization.preflight_confirmation_phrase:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_PREFLIGHT_CONFIRMATION_INVALID",
            "The exact one-time preflight confirmation phrase is required.",
        )
    paths = _local_paths(repo_root, authorization)
    bundle, _ = _load_and_validate_local_bundle(repo_root, authorization)
    if paths["preflight"].exists():
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_PREFLIGHT_ALREADY_COMPLETED",
            "A successful protected preflight receipt already exists.",
            path=str(paths["preflight"]),
        )
    if client is None:
        environment = os.environ if environ is None else environ
        api_key = environment.get(authorization.api_key_environment_name, "")
        if not api_key.strip():
            raise OpenRouterProbeActivationError(
                "OPENROUTER_HY3_CREDENTIAL_MISSING",
                "The OpenRouter API key environment variable is missing or empty.",
            )
        client = OpenRouterActivationPreflightClient(api_key=api_key)
    try:
        key_payload = client.get_key_status(timeout_seconds=authorization.timeout_seconds)
        model_payload = client.get_models(timeout_seconds=authorization.timeout_seconds)
        key_status = OpenRouterProbeKeyStatusEnvelope.model_validate(key_payload).data
        catalog = OpenRouterProbeModelCatalog.model_validate(model_payload)
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_PREFLIGHT_RESPONSE_INVALID",
            "OpenRouter preflight metadata failed typed validation.",
            details=details,
        ) from exc
    model_ids = {item.id for item in catalog.data}
    if authorization.exact_model_identifier not in model_ids:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_FREE_ROUTE_UNAVAILABLE",
            "The exact Hy3 free route is absent from the current model catalog.",
        )
    receipt = OpenRouterProbePreflightReceipt(
        authorization_id=authorization.authorization_id,
        prompt_bundle_sha256=_sha256_file(paths["bundle"]),
        key_status_response_sha256=_sha256_bytes(_canonical_bytes(key_payload)),
        model_catalog_response_sha256=_sha256_bytes(_canonical_bytes(model_payload)),
        key_label_sha256=_sha256_bytes(key_status.label.encode("utf-8")),
        limit=key_status.limit,
        limit_remaining=key_status.limit_remaining,
        usage=key_status.usage,
        usage_daily=key_status.usage_daily,
        is_free_tier=key_status.is_free_tier,
    )
    if receipt.prompt_bundle_sha256 != authorization.protected_prompt_bundle_sha256:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_LOCAL_BUNDLE_MISMATCH",
            "Protected prompt bundle changed before preflight.",
        )
    _write_bytes(paths["preflight"], _model_bytes(receipt))
    if _sha256_bytes(bundle.stable_prefix.encode("utf-8")) != bundle.stable_prefix_sha256:
        raise OpenRouterProbeActivationError(
            "OPENROUTER_HY3_LOCAL_PREFIX_MISMATCH",
            "Protected stable prefix changed before preflight.",
        )
    return OpenRouterProbeActivationSummary(
        command="preflight",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        protected_prompt_bundle_ready=True,
        live_preflight_passed=True,
        credential_accessed=True,
        network_request_count=2,
        next_gate="capability_probe_execution_confirmation",
    )


def verify_openrouter_probe_local(repo_root: Path) -> OpenRouterProbeActivationSummary:
    """Validate protected local preparation and any completed preflight receipt."""

    authorization, _, _ = _load_activation(repo_root)
    _load_and_validate_local_bundle(repo_root, authorization)
    paths = _local_paths(repo_root, authorization)
    preflight_passed = False
    if paths["preflight"].is_file():
        receipt = _load_model(paths["preflight"], OpenRouterProbePreflightReceipt)
        if receipt.prompt_bundle_sha256 != authorization.protected_prompt_bundle_sha256:
            raise OpenRouterProbeActivationError(
                "OPENROUTER_HY3_PREFLIGHT_RECEIPT_MISMATCH",
                "The protected preflight receipt does not match the active prompt bundle.",
            )
        preflight_passed = True
    return OpenRouterProbeActivationSummary(
        command="verify-local",
        authorization_id=authorization.authorization_id,
        authorization_status=authorization.status,
        protected_prompt_bundle_ready=True,
        live_preflight_passed=preflight_passed,
        credential_accessed=False,
        network_request_count=0,
        next_gate=(
            "capability_probe_execution_confirmation"
            if preflight_passed
            else "live_key_and_route_preflight"
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Activate and preflight the OpenRouter Hy3 capability probe."
    )
    parser.add_argument(
        "command",
        choices=("validate", "prepare-local", "preflight", "verify-local"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--confirm", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            summary = validate_openrouter_probe_activation(args.repo_root)
        elif args.command == "prepare-local":
            summary = prepare_openrouter_probe_local(args.repo_root)
        elif args.command == "preflight":
            summary = preflight_openrouter_probe(
                args.repo_root,
                confirmation_phrase=args.confirm,
            )
        else:
            summary = verify_openrouter_probe_local(args.repo_root)
    except OpenRouterProbeActivationError as exc:
        print(
            OpenRouterProbeActivationErrorEnvelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                path=exc.path,
                details=exc.details,
            ).model_dump_json(indent=2),
            file=sys.stderr,
        )
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
