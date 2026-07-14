"""Replay and validate the fixture-only OpenRouter Hy3 adapter dry run."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.openrouter import OpenRouterInvocationRequest
from auragateway.contracts.openrouter_hy3_adapter_dry_run import (
    OpenRouterDryRunCaseResult,
    OpenRouterDryRunCaseStatus,
    OpenRouterDryRunFixtureSet,
    OpenRouterDryRunManifest,
    OpenRouterDryRunReport,
    OpenRouterDryRunSummary,
)
from auragateway.providers.base import LiveProviderError, ProtectedProviderPrompt
from auragateway.providers.openrouter import (
    OpenRouterLiveInvocation,
    OpenRouterProviderAdapter,
)

_DEFAULT_FIXTURE_PATH = Path("data/provider_fixtures/openrouter-hy3-adapter-v1/fixtures.json")
_DEFAULT_REPORT_PATH = Path("data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/report.json")
_DEFAULT_MANIFEST_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-adapter-dry-run-v1/manifest.json"
)
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class OpenRouterDryRunError(Exception):
    """Expected metadata-safe validation failure."""

    def __init__(self, error_code: str, safe_message: str, *, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class OpenRouterDryRunErrorEnvelope(BaseModel):
    """Public-safe CLI error."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_ASSET_MISSING",
            "A required dry-run asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_INVALID_JSON",
            "A dry-run asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_VALIDATION_FAILED",
            "A dry-run asset failed typed validation.",
            path=str(path),
        ) from exc


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_ASSET_MISSING",
            "A required dry-run asset was not found.",
            path=str(path),
        ) from exc


class _FixtureTransport:
    def __init__(
        self,
        completion_payload: Mapping[str, object],
        generation_payload: Mapping[str, object],
    ) -> None:
        self._completion_payload = completion_payload
        self._generation_payload = generation_payload
        self.request_payload: Mapping[str, object] | None = None
        self.generation_id: str | None = None

    def create_chat(
        self,
        *,
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        assert timeout_seconds == 30
        self.request_payload = payload
        return self._completion_payload

    def get_generation(
        self,
        *,
        generation_id: str,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        assert timeout_seconds == 30
        self.generation_id = generation_id
        return self._generation_payload


def _invocation(case_id: str, session_id: str) -> OpenRouterLiveInvocation:
    request = OpenRouterInvocationRequest(
        request_id=f"{case_id}-request",
        fixture_id=case_id,
        static_prefix_fingerprint=hashlib.sha256(b"synthetic-stable-prefix").hexdigest(),
        input_token_count=12000,
        output_token_budget=32,
    )
    return OpenRouterLiveInvocation(
        request=request,
        prompt=ProtectedProviderPrompt(
            system_prompt="SYNTHETIC STABLE PREFIX " + ("alpha " * 64),
            user_prompt=f"SYNTHETIC SUFFIX {case_id}",
        ),
        session_id=session_id,
        timeout_seconds=30,
    )


def _replay_case(case: object) -> OpenRouterDryRunCaseResult:
    from auragateway.contracts.openrouter_hy3_adapter_dry_run import (
        OpenRouterDryRunFixtureCase,
    )

    fixture = cast(OpenRouterDryRunFixtureCase, case)
    transport = _FixtureTransport(fixture.completion_payload, fixture.generation_payload)
    invocation = _invocation(fixture.case_id, fixture.session_id)
    try:
        observed = OpenRouterProviderAdapter(transport).invoke(invocation)
    except LiveProviderError as exc:
        if fixture.expected_status is not OpenRouterDryRunCaseStatus.REJECTED:
            raise OpenRouterDryRunError(
                "OPENROUTER_DRY_RUN_UNEXPECTED_REJECTION",
                "A success fixture was rejected by the adapter.",
            ) from exc
        if exc.error_code is not fixture.expected_error_code:
            raise OpenRouterDryRunError(
                "OPENROUTER_DRY_RUN_ERROR_MISMATCH",
                "A rejected fixture produced the wrong safe error code.",
            ) from exc
        return OpenRouterDryRunCaseResult(
            case_id=fixture.case_id,
            status=OpenRouterDryRunCaseStatus.REJECTED,
            error_code=exc.error_code,
            session_id_sha256=invocation.session_id_sha256,
        )

    if fixture.expected_status is not OpenRouterDryRunCaseStatus.SUCCEEDED:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_EXPECTED_REJECTION_MISSING",
            "A rejection fixture was accepted by the adapter.",
        )
    read = observed.observation.read.state
    write = observed.observation.write.state
    if read is not fixture.expected_read_state or write is not fixture.expected_write_state:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_OBSERVATION_MISMATCH",
            "A fixture produced an unexpected cache observation state.",
        )
    request_payload = transport.request_payload
    if request_payload is None:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_REQUEST_MISSING",
            "The adapter did not emit a request payload.",
        )
    provider_policy = request_payload.get("provider")
    if provider_policy != {"data_collection": "deny", "zdr": True}:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_PRIVACY_MISMATCH",
            "The adapter request did not retain required privacy controls.",
        )
    route = observed.observation.route
    return OpenRouterDryRunCaseResult(
        case_id=fixture.case_id,
        status=OpenRouterDryRunCaseStatus.SUCCEEDED,
        read_state=read,
        write_state=write,
        resolved_model_sha256=hashlib.sha256(route.resolved_model.encode("utf-8")).hexdigest(),
        upstream_provider_sha256=hashlib.sha256(
            route.upstream_provider.encode("utf-8")
        ).hexdigest(),
        session_id_sha256=invocation.session_id_sha256,
    )


def _validate_manifest(repo_root: Path, manifest: OpenRouterDryRunManifest) -> None:
    for binding in manifest.bindings:
        path = str(binding["path"])
        expected = str(binding["sha256"])
        if _sha256(repo_root / path) != expected:
            raise OpenRouterDryRunError(
                "OPENROUTER_DRY_RUN_BINDING_MISMATCH",
                "A bound dry-run asset no longer matches.",
                path=path,
            )


def validate_openrouter_dry_run(repo_root: Path) -> OpenRouterDryRunSummary:
    """Replay every fixture and validate frozen report and manifest evidence."""

    fixtures = _load_model(repo_root / _DEFAULT_FIXTURE_PATH, OpenRouterDryRunFixtureSet)
    report = _load_model(repo_root / _DEFAULT_REPORT_PATH, OpenRouterDryRunReport)
    manifest = _load_model(repo_root / _DEFAULT_MANIFEST_PATH, OpenRouterDryRunManifest)
    results = tuple(_replay_case(case) for case in fixtures.cases)
    if results != report.results:
        raise OpenRouterDryRunError(
            "OPENROUTER_DRY_RUN_REPORT_MISMATCH",
            "Replayed adapter results do not match the frozen report.",
        )
    _validate_manifest(repo_root, manifest)
    return OpenRouterDryRunSummary(
        report_id=report.report_id,
        next_gate=report.next_gate,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        summary = validate_openrouter_dry_run(args.repo_root.resolve())
    except OpenRouterDryRunError as exc:
        print(
            OpenRouterDryRunErrorEnvelope(
                error_code=exc.error_code,
                safe_message=exc.safe_message,
                path=exc.path,
            ).model_dump_json(indent=2),
            file=sys.stderr,
        )
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
