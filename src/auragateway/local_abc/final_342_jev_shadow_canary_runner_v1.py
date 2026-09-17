"""Execute exactly one real Final-342 Jev shadow-adjudication canary.

The request bytes must already be frozen by `final_342_jev_shadow_canary_v1`.
This runner is anti-replay: once a valid response/receipt exists, it returns
the existing receipt without another provider request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_v1 as canary,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as review_bridge,
)

CANARY_RESPONSE_PATH = canary.CANARY_ROOT / "response.json"
CANARY_RECEIPT_PATH = canary.CANARY_ROOT / "live-receipt.json"

PostJson = Callable[[str, dict[str, str], bytes], dict[str, Any]]


class JevCanaryExecutionError(RuntimeError):
    """Fail-closed one-canary execution error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LiveCanaryReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_REAL_SHADOW_CANARY_PASS"] = (
        "FINAL_342_JEV_REAL_SHADOW_CANARY_PASS"
    )
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    question_count: Literal[29]
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_tokens: int = Field(ge=1)
    output_tokens: int = Field(ge=1)
    provider_request_performed: bool
    provider_request_count_this_invocation: int = Field(ge=0, le=1)
    protected_final_342_data_sent: Literal[True] = True
    human_adjudication_seen_by_jev: Literal[False] = False
    authoritative_adjudication_created: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal["J5_FREEZE_35_CASE_SHADOW_BATCH"] = "J5_FREEZE_35_CASE_SHADOW_BATCH"


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_FILE_MISSING",
            f"required canary file is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_JSON_INVALID",
            f"canary file is not valid JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_JSON_SHAPE_INVALID",
            f"canary JSON root must be an object: {path.as_posix()}",
        )
    return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise JevCanaryExecutionError(
                "FINAL_342_JEV_CANARY_EXECUTION_PATH_UNSAFE",
                f"canary output path is unsafe: {path.as_posix()}",
            )
        if path.read_bytes() != payload:
            raise JevCanaryExecutionError(
                "FINAL_342_JEV_CANARY_EXECUTION_APPEND_ONLY_CONFLICT",
                f"existing canary output differs: {path.as_posix()}",
            )
        return

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_TEMP_RESIDUE",
            f"temporary canary output already exists: {temporary.as_posix()}",
        )

    temporary.write_bytes(payload)
    temporary.replace(path)


def _stdlib_post_json(
    url: str,
    headers: dict[str, str],
    body: bytes,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_HTTP_ERROR",
            f"Jev canary request returned HTTP {error.code}",
        ) from error
    except urllib.error.URLError as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_TRANSPORT_ERROR",
            "Jev canary request failed at the transport boundary",
        ) from error

    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_RESPONSE_INVALID",
            "Jev canary response was not valid UTF-8 JSON",
        ) from error

    if not isinstance(value, dict):
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_RESPONSE_SHAPE_INVALID",
            "Jev canary response JSON root must be an object",
        )

    return value


def _authoritative_adjudication_path(
    root: Path,
    review_item_id: str,
) -> Path:
    return root / review_bridge.REVIEW_RESULT_ROOT / "adjudications" / f"{review_item_id}.json"


def _load_frozen_request(
    root: Path,
) -> tuple[canary.JevCanaryManifest, jev_contract.JevShadowRequest, bytes]:
    manifest_path = root / canary.CANARY_MANIFEST_PATH
    request_path = root / canary.CANARY_REQUEST_PATH

    try:
        manifest = canary.JevCanaryManifest.model_validate(_read_json_object(manifest_path))
        request = jev_contract.JevShadowRequest.model_validate(_read_json_object(request_path))
    except ValidationError as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_INPUT_INVALID",
            "frozen canary input failed typed validation",
        ) from error

    request_bytes = request_path.read_bytes()
    if _sha256_bytes(request_bytes) != manifest.request_sha256:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_REQUEST_IDENTITY_DRIFT",
            "frozen canary request digest differs from manifest",
        )

    if request.model != jev_contract.JEV_MODEL_PIN:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_MODEL_DRIFT",
            "frozen canary request model differs from Jev pin",
        )

    return manifest, request, request_bytes


def _load_existing_receipt(
    root: Path,
) -> LiveCanaryReceipt | None:
    receipt_path = root / CANARY_RECEIPT_PATH
    response_path = root / CANARY_RESPONSE_PATH

    if not receipt_path.exists() and not response_path.exists():
        return None

    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_RECEIPT_STATE_INVALID",
            "existing live canary receipt is missing or unsafe",
        )

    if not response_path.is_file() or response_path.is_symlink():
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_RESPONSE_STATE_INVALID",
            "existing live canary response is missing or unsafe",
        )

    try:
        receipt = LiveCanaryReceipt.model_validate(_read_json_object(receipt_path))
        response = jev_contract.JevShadowResponse.model_validate(_read_json_object(response_path))
    except ValidationError as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_EXISTING_EVIDENCE_INVALID",
            "existing live canary evidence failed typed validation",
        ) from error

    response_bytes = response_path.read_bytes()
    if _sha256_bytes(response_bytes) != receipt.response_sha256:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_EXISTING_RESPONSE_DRIFT",
            "existing live canary response digest differs from receipt",
        )

    if response.model != receipt.model:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_EXISTING_MODEL_DRIFT",
            "existing response model differs from live canary receipt",
        )

    return receipt.model_copy(
        update={
            "provider_request_performed": False,
            "provider_request_count_this_invocation": 0,
        }
    )


def run_live_canary(
    repo_root: Path,
    *,
    post_json: PostJson = _stdlib_post_json,
) -> LiveCanaryReceipt:
    root = repo_root.resolve()

    existing = _load_existing_receipt(root)
    if existing is not None:
        return existing

    manifest, request, request_bytes = _load_frozen_request(root)

    adjudication_path = _authoritative_adjudication_path(
        root,
        manifest.review_item_id,
    )
    if adjudication_path.exists():
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_AUTHORITATIVE_ADJUDICATION_PRESENT",
            "live shadow canary is prohibited after authoritative adjudication",
        )

    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_API_KEY_MISSING",
            "TYPESAFE_API_KEY is missing from the current environment",
        )

    response_payload = post_json(
        jev_contract.JEV_ENDPOINT,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        request_bytes,
    )

    try:
        response = jev_contract.JevShadowResponse.model_validate(response_payload)
    except ValidationError as error:
        raise JevCanaryExecutionError(
            "FINAL_342_JEV_CANARY_EXECUTION_TYPED_RESPONSE_INVALID",
            "Jev canary response failed typed validation",
        ) from error

    jev_contract.validate_response_against_request(request, response)
    jev_contract.project_response(request, response)

    response_bytes = _canonical_bytes(response_payload)
    response_sha256 = _sha256_bytes(response_bytes)

    receipt = LiveCanaryReceipt(
        review_item_id=manifest.review_item_id,
        episode_id=manifest.episode_id,
        question_count=manifest.question_count,
        request_sha256=manifest.request_sha256,
        response_sha256=response_sha256,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        provider_request_performed=True,
        provider_request_count_this_invocation=1,
    )

    _write_once(root / CANARY_RESPONSE_PATH, response_bytes)
    _write_once(
        root / CANARY_RECEIPT_PATH,
        _canonical_bytes(receipt.model_dump(mode="json")),
    )

    return receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final_342_jev_shadow_canary_runner_v1")
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    receipt = run_live_canary(args.repo_root)
    print(receipt.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
