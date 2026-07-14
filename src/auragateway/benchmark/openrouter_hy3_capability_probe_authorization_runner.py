"""Validate the inactive OpenRouter Hy3 capability-probe authorization review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.benchmark.openrouter_hy3_probe_prompt import validate_stable_prefix
from auragateway.benchmark.openrouter_hy3_probe_state_model import explore_state_space
from auragateway.contracts.auragateway_v2_terminal_evidence_review import (
    OpenRouterHy3TerminalEvidenceReviewManifest,
)
from auragateway.contracts.openrouter_hy3_capability_probe_authorization import (
    OpenRouterProbeAuthorizationManifest,
    OpenRouterProbeAuthorizationReview,
    OpenRouterProbeAuthorizationSummary,
    OpenRouterProbePromptRecipe,
    OpenRouterProbeStateModelEvidence,
    OpenRouterProbeTransportDryRunReport,
)
from auragateway.contracts.openrouter_hy3_review_supersession import (
    OpenRouterHy3HistoricalReviewSupersession,
    OpenRouterHy3SupersessionScope,
    superseding_hash,
)
from auragateway.contracts.provider import ProviderErrorCode
from auragateway.providers.base import LiveProviderError
from auragateway.providers.openrouter_http import (
    OpenRouterHttpResponse,
    OpenRouterHttpTransport,
)

_ROOT = Path(
    "data/evals/benchmark/openrouter-hy3-capability-probe-authorization-review-v1"
)
_REVIEW_PATH = _ROOT / "review.json"
_PROMPT_RECIPE_PATH = _ROOT / "prompt_recipe.json"
_STATE_MODEL_REPORT_PATH = _ROOT / "state_model_report.json"
_TRANSPORT_REPORT_PATH = _ROOT / "transport_report.json"
_MANIFEST_PATH = _ROOT / "manifest.json"
_SUPERSESSION_ROOT = Path(
    "data/evals/benchmark/openrouter-hy3-historical-review-supersession-v1"
)
_SUPERSESSION_PATH = _SUPERSESSION_ROOT / "supersession.json"
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class OpenRouterProbeAuthorizationError(Exception):
    """Expected metadata-safe authorization-review failure."""

    def __init__(
        self, error_code: str, safe_message: str, *, path: str | None = None
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class OpenRouterProbeAuthorizationErrorEnvelope(BaseModel):
    """Public-safe CLI error response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_ASSET_MISSING",
            "A required authorization-review asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_INVALID_JSON",
            "An authorization-review asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_CONTRACT_INVALID",
            "An authorization-review asset failed typed validation.",
            path=str(path),
        ) from exc


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_ASSET_MISSING",
            "A bound authorization-review asset was not found.",
            path=str(path),
        ) from exc


class _FixtureBackend:
    def __init__(self, response: OpenRouterHttpResponse) -> None:
        self._response = response
        self.requests: list[
            tuple[str, str, Mapping[str, str], bytes | None, float]
        ] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenRouterHttpResponse:
        self.requests.append((method, url, headers, body, timeout_seconds))
        return self._response


def _json_response(
    payload: object, *, status_code: int = 200
) -> OpenRouterHttpResponse:
    return OpenRouterHttpResponse(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload, sort_keys=True).encode("utf-8"),
    )


def _expect_status(
    status_code: int, *, retryable: bool, error_code: ProviderErrorCode
) -> None:
    backend = _FixtureBackend(
        _json_response({"error": {"code": status_code}}, status_code=status_code)
    )
    transport = OpenRouterHttpTransport(api_key="fixture-key", backend=backend)
    try:
        transport.create_chat(payload={"model": "tencent/hy3:free"}, timeout_seconds=30)
    except LiveProviderError as exc:
        if exc.retryable is not retryable or exc.error_code is not error_code:
            raise OpenRouterProbeAuthorizationError(
                "OPENROUTER_PROBE_AUTH_STATUS_MAPPING_MISMATCH",
                "The HTTP transport produced an unexpected safe error mapping.",
            ) from exc
    else:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_STATUS_ACCEPTED",
            "The HTTP transport accepted a non-success status.",
        )


def _replay_transport() -> OpenRouterProbeTransportDryRunReport:
    chat_backend = _FixtureBackend(_json_response({"id": "gen-chat", "choices": []}))
    chat_transport = OpenRouterHttpTransport(
        api_key="fixture-key", backend=chat_backend
    )
    chat_transport.create_chat(
        payload={"model": "tencent/hy3:free"}, timeout_seconds=30
    )
    chat_request = chat_backend.requests[0]
    if chat_request[0] != "POST" or not chat_request[1].endswith("/chat/completions"):
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_CHAT_REQUEST_MISMATCH",
            "The HTTP transport emitted an unexpected chat request.",
        )
    if chat_request[2].get("Authorization") != "Bearer fixture-key":
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_HEADER_MISMATCH",
            "The HTTP transport did not use the explicit API key.",
        )

    generation_backend = _FixtureBackend(_json_response({"data": {"id": "gen-a/b"}}))
    generation_transport = OpenRouterHttpTransport(
        api_key="fixture-key",
        backend=generation_backend,
    )
    generation_transport.get_generation(generation_id="gen-a/b", timeout_seconds=30)
    generation_url = generation_backend.requests[0][1]
    if not generation_url.endswith("/generation?id=gen-a%2Fb"):
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_GENERATION_QUERY_MISMATCH",
            "The HTTP transport did not encode the generation identifier.",
        )

    key_backend = _FixtureBackend(_json_response({"data": {"is_free_tier": True}}))
    key_transport = OpenRouterHttpTransport(api_key="fixture-key", backend=key_backend)
    key_transport.get_key_status(timeout_seconds=30)
    if not key_backend.requests[0][1].endswith("/key"):
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_KEY_REQUEST_MISMATCH",
            "The HTTP transport emitted an unexpected key-status request.",
        )

    _expect_status(429, retryable=True, error_code=ProviderErrorCode.RATE_LIMITED)
    for status in (502, 524, 529):
        _expect_status(status, retryable=True, error_code=ProviderErrorCode.UNAVAILABLE)
    _expect_status(
        401, retryable=False, error_code=ProviderErrorCode.AUTHENTICATION_FAILED
    )
    _expect_status(402, retryable=False, error_code=ProviderErrorCode.PERMISSION_DENIED)
    _expect_status(500, retryable=False, error_code=ProviderErrorCode.REQUEST_REJECTED)

    invalid_backend = _FixtureBackend(
        OpenRouterHttpResponse(status_code=200, headers={}, body=b"{")
    )
    invalid_transport = OpenRouterHttpTransport(
        api_key="fixture-key", backend=invalid_backend
    )
    try:
        invalid_transport.create_chat(
            payload={"model": "tencent/hy3:free"}, timeout_seconds=30
        )
    except LiveProviderError as exc:
        if exc.error_code is not ProviderErrorCode.INVALID_RESPONSE or exc.retryable:
            raise OpenRouterProbeAuthorizationError(
                "OPENROUTER_PROBE_AUTH_INVALID_JSON_MAPPING_MISMATCH",
                "Invalid JSON did not fail closed with the expected error.",
            ) from exc
    else:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_INVALID_JSON_ACCEPTED",
            "The HTTP transport accepted invalid JSON.",
        )

    return OpenRouterProbeTransportDryRunReport(
        report_id="openrouter-hy3-http-transport-dry-run-v1",
        transient_statuses=(429, 502, 524, 529),
        nonretryable_statuses=(401, 402, 500),
    )


def _load_supersession(
    repo_root: Path,
) -> tuple[
    OpenRouterHy3HistoricalReviewSupersession,
    OpenRouterHy3TerminalEvidenceReviewManifest,
]:
    supersession = _load_model(
        repo_root / _SUPERSESSION_PATH,
        OpenRouterHy3HistoricalReviewSupersession,
    )
    lineage = {
        supersession.identifiability_review_path: (
            supersession.identifiability_review_sha256
        ),
        supersession.identifiability_manifest_path: (
            supersession.identifiability_manifest_sha256
        ),
        supersession.authorization_review_path: supersession.authorization_review_sha256,
        supersession.authorization_manifest_path: (
            supersession.authorization_manifest_sha256
        ),
        supersession.superseding_manifest_path: supersession.superseding_manifest_sha256,
    }
    for relative_path, expected_hash in lineage.items():
        if _sha256(repo_root / relative_path) != expected_hash:
            raise OpenRouterProbeAuthorizationError(
                "OPENROUTER_PROBE_AUTH_SUPERSESSION_LINEAGE_MISMATCH",
                "A historical or superseding review asset no longer matches its supersession.",
                path=relative_path,
            )
    superseding_manifest = _load_model(
        repo_root / supersession.superseding_manifest_path,
        OpenRouterHy3TerminalEvidenceReviewManifest,
    )
    return supersession, superseding_manifest


def _validate_source_bindings(
    repo_root: Path,
    review: OpenRouterProbeAuthorizationReview,
    supersession: OpenRouterHy3HistoricalReviewSupersession,
    superseding_manifest: OpenRouterHy3TerminalEvidenceReviewManifest,
) -> None:
    for binding in review.source_bindings:
        expected_hash = binding.sha256
        for delegation in supersession.bindings:
            if (
                delegation.scope
                is OpenRouterHy3SupersessionScope.AUTHORIZATION_REVIEW_SOURCE
                and delegation.path.value == binding.path
            ):
                if delegation.historical_sha256 != binding.sha256:
                    raise OpenRouterProbeAuthorizationError(
                        "OPENROUTER_PROBE_AUTH_SUPERSESSION_HISTORICAL_HASH_MISMATCH",
                        "A delegated historical hash no longer matches the frozen review.",
                        path=binding.path,
                    )
                expected_hash = superseding_hash(
                    superseding_manifest,
                    delegation.superseding_hash_field,
                )
                break
        if _sha256(repo_root / binding.path) != expected_hash:
            raise OpenRouterProbeAuthorizationError(
                "OPENROUTER_PROBE_AUTH_SOURCE_BINDING_MISMATCH",
                "A reviewed source input no longer matches its frozen hash.",
                path=binding.path,
            )


def _validate_manifest(
    repo_root: Path,
    manifest: OpenRouterProbeAuthorizationManifest,
    supersession: OpenRouterHy3HistoricalReviewSupersession,
) -> None:
    for binding in manifest.bindings:
        expected_hash = binding.sha256
        if binding.path == supersession.authorization_runner_path:
            if binding.sha256 != supersession.authorization_runner_historical_sha256:
                raise OpenRouterProbeAuthorizationError(
                    "OPENROUTER_PROBE_AUTH_RUNNER_HISTORICAL_HASH_MISMATCH",
                    "The historical authorization-runner hash no longer matches the manifest.",
                    path=binding.path,
                )
            expected_hash = supersession.authorization_runner_superseding_sha256
        if _sha256(repo_root / binding.path) != expected_hash:
            raise OpenRouterProbeAuthorizationError(
                "OPENROUTER_PROBE_AUTH_MANIFEST_MISMATCH",
                "An authorization-review output no longer matches its manifest.",
                path=binding.path,
            )


def validate_openrouter_probe_authorization(
    repo_root: Path,
) -> OpenRouterProbeAuthorizationSummary:
    """Validate all inactive review, transport, prompt, and state-model evidence."""

    review = _load_model(repo_root / _REVIEW_PATH, OpenRouterProbeAuthorizationReview)
    recipe = _load_model(repo_root / _PROMPT_RECIPE_PATH, OpenRouterProbePromptRecipe)
    frozen_state_report = _load_model(
        repo_root / _STATE_MODEL_REPORT_PATH,
        OpenRouterProbeStateModelEvidence,
    )
    frozen_transport_report = _load_model(
        repo_root / _TRANSPORT_REPORT_PATH,
        OpenRouterProbeTransportDryRunReport,
    )
    manifest = _load_model(
        repo_root / _MANIFEST_PATH, OpenRouterProbeAuthorizationManifest
    )

    supersession, superseding_manifest = _load_supersession(repo_root)
    _validate_source_bindings(
        repo_root,
        review,
        supersession,
        superseding_manifest,
    )
    validate_stable_prefix(recipe)

    observed_state = explore_state_space()
    observed_state_report = OpenRouterProbeStateModelEvidence(
        model_id="openrouter-hy3-capability-probe-state-model-v1",
        reachable_state_count=observed_state.reachable_state_count,
        terminal_state_count=observed_state.terminal_state_count,
        terminal_outcome_counts=dict(observed_state.terminal_outcome_counts),
        invariants_checked=observed_state.invariants_checked,
        invariant_violations=observed_state.invariant_violations,
    )
    if observed_state_report != frozen_state_report:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_STATE_MODEL_MISMATCH",
            "The executable state model no longer matches its frozen report.",
        )

    observed_transport_report = _replay_transport()
    if observed_transport_report != frozen_transport_report:
        raise OpenRouterProbeAuthorizationError(
            "OPENROUTER_PROBE_AUTH_TRANSPORT_REPORT_MISMATCH",
            "The HTTP transport replay no longer matches its frozen report.",
        )

    _validate_manifest(repo_root, manifest, supersession)
    return OpenRouterProbeAuthorizationSummary(
        review_id=review.review_id,
        status=review.status,
        state_model_reachable_states=frozen_state_report.reachable_state_count,
        state_model_terminal_states=frozen_state_report.terminal_state_count,
        next_gate=review.next_gate,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        summary = validate_openrouter_probe_authorization(args.repo_root.resolve())
    except OpenRouterProbeAuthorizationError as exc:
        print(
            OpenRouterProbeAuthorizationErrorEnvelope(
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
