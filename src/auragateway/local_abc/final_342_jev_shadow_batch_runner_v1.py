"""Resumable serial runner for the frozen Final-342 Jev shadow batch.

The runner never mutates the frozen batch manifest. Each pending case gets:
1. a write-once attempt marker before any provider call;
2. one validated write-once execution record after a successful response.

An orphan attempt marker is terminal for automatic execution and requires
explicit reconciliation. This prevents blind retries after transport,
provider, validation, crash, or persistence uncertainty.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_batch_freeze_v1 as batch_freeze,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_runner_v1 as canary_runner,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as review_bridge,
)

ATTEMPT_ROOT = batch_freeze.BATCH_ROOT / "attempts"
EXECUTION_ROOT = batch_freeze.BATCH_ROOT / "executions"

PostJson = Callable[[str, dict[str, str], bytes], dict[str, Any]]


class JevBatchRunnerError(RuntimeError):
    """Fail-closed shadow-batch execution error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BatchAttemptMarker(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["PROVIDER_ATTEMPT_AUTHORIZED"] = "PROVIDER_ATTEMPT_AUTHORIZED"
    batch_index: int = Field(ge=1, le=34)
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_request_count_authorized: Literal[1] = 1
    automatic_retry_authorized: Literal[False] = False
    authoritative_adjudication_present: Literal[False] = False


class BatchCaseExecutionRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_SHADOW_CASE_PASS"] = (
        "FINAL_342_JEV_SHADOW_CASE_PASS"
    )
    batch_index: int = Field(ge=1, le=34)
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response: jev_contract.JevShadowResponse
    input_tokens: int = Field(ge=1)
    output_tokens: int = Field(ge=1)
    provider_request_performed: Literal[True] = True
    provider_request_count: Literal[1] = 1
    protected_final_342_data_sent: Literal[True] = True
    human_adjudication_seen_by_jev: Literal[False] = False
    authoritative_adjudication_created: Literal[False] = False
    effect_claims_permitted: Literal[False] = False


class BatchRunReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal[
        "FINAL_342_JEV_SHADOW_BATCH_COMPLETE",
        "FINAL_342_JEV_SHADOW_BATCH_PAUSED_BY_LIMIT",
    ]
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    batch_size: Literal[35] = 35
    executed_canary_count: Literal[1] = 1
    completed_pending_count: int = Field(ge=0, le=34)
    remaining_pending_count: int = Field(ge=0, le=34)
    provider_requests_this_invocation: int = Field(ge=0, le=34)
    reused_existing_execution_count: int = Field(ge=0, le=34)
    max_new_requests: int | None = Field(default=None, ge=1, le=34)
    request_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    serial_execution: Literal[True] = True
    max_in_flight_requests: Literal[1] = 1
    automatic_retries_performed: Literal[0] = 0
    failure_threshold_frozen: Literal[False] = False
    human_adjudication_seen_by_jev: Literal[False] = False
    authoritative_adjudication_created: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal[
        "J6_AUTHORITATIVE_HUMAN_ADJUDICATION",
        "J5C_CONTINUE_SHADOW_BATCH",
    ]


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_FILE_MISSING",
            f"required batch file is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_JSON_INVALID",
            f"batch file is not valid JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_JSON_SHAPE_INVALID",
            f"batch JSON root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise JevBatchRunnerError(
                "FINAL_342_JEV_BATCH_RUNNER_PATH_UNSAFE",
                f"batch output path is unsafe: {path.as_posix()}",
            )
        if path.read_bytes() != payload:
            raise JevBatchRunnerError(
                "FINAL_342_JEV_BATCH_RUNNER_APPEND_ONLY_CONFLICT",
                f"existing batch output differs: {path.as_posix()}",
            )
        return

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_TEMP_RESIDUE",
            f"temporary batch output already exists: {temporary.as_posix()}",
        )

    temporary.write_bytes(payload)
    temporary.replace(path)


def _entry_stem(entry: batch_freeze.FrozenBatchEntry) -> str:
    return f"{entry.batch_index:02d}-{entry.review_item_id}"


def _attempt_path(root: Path, entry: batch_freeze.FrozenBatchEntry) -> Path:
    return root / ATTEMPT_ROOT / f"{_entry_stem(entry)}.json"


def _execution_path(root: Path, entry: batch_freeze.FrozenBatchEntry) -> Path:
    return root / EXECUTION_ROOT / f"{_entry_stem(entry)}.json"


def _authoritative_adjudication_path(
    root: Path,
    review_item_id: str,
) -> Path:
    return (
        root
        / review_bridge.REVIEW_RESULT_ROOT
        / "adjudications"
        / f"{review_item_id}.json"
    )


def _resolve_request_path(
    root: Path,
    entry: batch_freeze.FrozenBatchEntry,
) -> Path:
    batch_root = (root / batch_freeze.BATCH_ROOT).resolve()
    request_path = (root / entry.request_relative_path).resolve()

    try:
        request_path.relative_to(batch_root)
    except ValueError as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_REQUEST_OUTSIDE_BATCH_ROOT",
            "frozen request path escapes the protected batch root",
        ) from error

    if not request_path.is_file() or request_path.is_symlink():
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_REQUEST_MISSING",
            "frozen batch request is missing or unsafe",
        )

    return request_path


def _load_manifest(root: Path) -> batch_freeze.FrozenBatchManifest:
    try:
        manifest = batch_freeze.FrozenBatchManifest.model_validate(
            _read_json_object(root / batch_freeze.BATCH_MANIFEST_PATH)
        )
    except ValidationError as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_MANIFEST_INVALID",
            "frozen batch manifest failed typed validation",
        ) from error

    if manifest.policy.execution_mode != "SERIAL_ONE_AT_A_TIME":
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_POLICY_DRIFT",
            "frozen batch execution mode is not serial",
        )
    if manifest.policy.max_in_flight_requests != 1:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_POLICY_DRIFT",
            "frozen batch max-in-flight policy is not one",
        )
    if manifest.policy.retry_policy != "NO_AUTOMATIC_RETRY":
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_POLICY_DRIFT",
            "frozen batch retry policy drifted",
        )

    return manifest


def _load_frozen_request(
    root: Path,
    entry: batch_freeze.FrozenBatchEntry,
) -> tuple[jev_contract.JevShadowRequest, bytes]:
    path = _resolve_request_path(root, entry)
    raw_bytes = path.read_bytes()

    if _sha256_bytes(raw_bytes) != entry.request_sha256:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_REQUEST_IDENTITY_DRIFT",
            f"frozen request digest drifted for batch index {entry.batch_index}",
        )

    try:
        request = jev_contract.JevShadowRequest.model_validate(
            json.loads(raw_bytes.decode("utf-8"))
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_REQUEST_INVALID",
            f"frozen request failed validation for batch index {entry.batch_index}",
        ) from error

    if request.model != jev_contract.JEV_MODEL_PIN:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_MODEL_DRIFT",
            f"request model drifted for batch index {entry.batch_index}",
        )

    return request, raw_bytes


def _validate_no_human_adjudication(
    root: Path,
    manifest: batch_freeze.FrozenBatchManifest,
) -> None:
    for entry in manifest.entries:
        if _authoritative_adjudication_path(root, entry.review_item_id).exists():
            raise JevBatchRunnerError(
                "FINAL_342_JEV_BATCH_RUNNER_AUTHORITATIVE_ADJUDICATION_PRESENT",
                (
                    "shadow execution is prohibited after human adjudication "
                    f"begins; batch_index={entry.batch_index}"
                ),
            )


def _validate_canary_lineage(
    root: Path,
    manifest: batch_freeze.FrozenBatchManifest,
) -> None:
    try:
        receipt = canary_runner.LiveCanaryReceipt.model_validate(
            _read_json_object(root / canary_runner.CANARY_RECEIPT_PATH)
        )
    except ValidationError as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_CANARY_RECEIPT_INVALID",
            "J4 canary receipt failed typed validation",
        ) from error

    if receipt.request_sha256 != manifest.canary_request_sha256:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_CANARY_REQUEST_DRIFT",
            "J4 canary request digest differs from frozen batch manifest",
        )
    if receipt.response_sha256 != manifest.canary_response_sha256:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_CANARY_RESPONSE_DRIFT",
            "J4 canary response digest differs from frozen batch manifest",
        )


def _load_existing_execution(
    root: Path,
    entry: batch_freeze.FrozenBatchEntry,
    request: jev_contract.JevShadowRequest,
) -> BatchCaseExecutionRecord | None:
    execution_path = _execution_path(root, entry)
    attempt_path = _attempt_path(root, entry)

    if not execution_path.exists():
        if attempt_path.exists():
            raise JevBatchRunnerError(
                "FINAL_342_JEV_BATCH_RUNNER_INCOMPLETE_PRIOR_ATTEMPT",
                (
                    "an earlier provider attempt has no validated execution "
                    f"record; manual reconciliation required for batch index "
                    f"{entry.batch_index}"
                ),
            )
        return None

    if not attempt_path.is_file() or attempt_path.is_symlink():
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_ATTEMPT_MARKER_MISSING",
            "validated execution record requires its write-once attempt marker",
        )

    try:
        marker = BatchAttemptMarker.model_validate(_read_json_object(attempt_path))
        record = BatchCaseExecutionRecord.model_validate(
            _read_json_object(execution_path)
        )
    except ValidationError as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_EXISTING_EXECUTION_INVALID",
            "existing case execution evidence failed typed validation",
        ) from error

    if (
        marker.batch_index != entry.batch_index
        or marker.review_item_id != entry.review_item_id
        or marker.request_sha256 != entry.request_sha256
    ):
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_ATTEMPT_IDENTITY_DRIFT",
            "attempt marker differs from frozen batch entry",
        )

    if (
        record.batch_index != entry.batch_index
        or record.review_item_id != entry.review_item_id
        or record.request_sha256 != entry.request_sha256
    ):
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_EXECUTION_IDENTITY_DRIFT",
            "execution record differs from frozen batch entry",
        )

    jev_contract.validate_response_against_request(request, record.response)
    jev_contract.project_response(request, record.response)

    response_bytes = _canonical_bytes(record.response.model_dump(mode="json"))
    if _sha256_bytes(response_bytes) != record.response_sha256:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_RESPONSE_IDENTITY_DRIFT",
            "persisted response digest differs from execution record",
        )

    return record


def _execute_one(
    root: Path,
    entry: batch_freeze.FrozenBatchEntry,
    request: jev_contract.JevShadowRequest,
    request_bytes: bytes,
    *,
    post_json: PostJson,
) -> BatchCaseExecutionRecord:
    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_API_KEY_MISSING",
            "TYPESAFE_API_KEY is missing from the current environment",
        )

    if _authoritative_adjudication_path(root, entry.review_item_id).exists():
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_AUTHORITATIVE_ADJUDICATION_PRESENT",
            f"human adjudication exists for batch index {entry.batch_index}",
        )

    marker = BatchAttemptMarker(
        batch_index=entry.batch_index,
        review_item_id=entry.review_item_id,
        episode_id=entry.episode_id,
        request_sha256=entry.request_sha256,
    )
    _write_once(
        _attempt_path(root, entry),
        _canonical_bytes(marker.model_dump(mode="json")),
    )

    try:
        response_payload = post_json(
            jev_contract.JEV_ENDPOINT,
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            request_bytes,
        )
    except canary_runner.JevCanaryExecutionError as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_PROVIDER_ATTEMPT_UNRESOLVED",
            (
                "provider attempt did not produce a validated execution record; "
                f"batch_index={entry.batch_index}; automatic retry prohibited"
            ),
        ) from error

    try:
        response = jev_contract.JevShadowResponse.model_validate(response_payload)
        jev_contract.validate_response_against_request(request, response)
        jev_contract.project_response(request, response)
    except (ValidationError, jev_contract.JevContractError) as error:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_PROVIDER_RESPONSE_INVALID",
            (
                "provider response failed the frozen typed contract; "
                f"batch_index={entry.batch_index}; automatic retry prohibited"
            ),
        ) from error

    response_bytes = _canonical_bytes(response.model_dump(mode="json"))
    record = BatchCaseExecutionRecord(
        batch_index=entry.batch_index,
        review_item_id=entry.review_item_id,
        episode_id=entry.episode_id,
        request_sha256=entry.request_sha256,
        response_sha256=_sha256_bytes(response_bytes),
        response=response,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

    _write_once(
        _execution_path(root, entry),
        _canonical_bytes(record.model_dump(mode="json")),
    )
    return record


def run_shadow_batch(
    repo_root: Path,
    *,
    max_new_requests: int | None = None,
    post_json: PostJson = canary_runner._stdlib_post_json,
) -> BatchRunReceipt:
    root = repo_root.resolve()

    if max_new_requests is not None and not 1 <= max_new_requests <= 34:
        raise JevBatchRunnerError(
            "FINAL_342_JEV_BATCH_RUNNER_LIMIT_INVALID",
            "max_new_requests must be between 1 and 34",
        )

    manifest = _load_manifest(root)
    _validate_canary_lineage(root, manifest)
    _validate_no_human_adjudication(root, manifest)

    completed = 0
    reused = 0
    new_requests = 0

    for entry in manifest.entries[1:]:
        request, request_bytes = _load_frozen_request(root, entry)
        existing = _load_existing_execution(root, entry, request)

        if existing is not None:
            completed += 1
            reused += 1
            continue

        if max_new_requests is not None and new_requests >= max_new_requests:
            break

        _execute_one(
            root,
            entry,
            request,
            request_bytes,
            post_json=post_json,
        )
        completed += 1
        new_requests += 1

    remaining = 34 - completed
    complete = remaining == 0

    return BatchRunReceipt(
        status=(
            "FINAL_342_JEV_SHADOW_BATCH_COMPLETE"
            if complete
            else "FINAL_342_JEV_SHADOW_BATCH_PAUSED_BY_LIMIT"
        ),
        completed_pending_count=completed,
        remaining_pending_count=remaining,
        provider_requests_this_invocation=new_requests,
        reused_existing_execution_count=reused,
        max_new_requests=max_new_requests,
        request_inventory_sha256=manifest.request_inventory_sha256,
        next_gate=(
            "J6_AUTHORITATIVE_HUMAN_ADJUDICATION"
            if complete
            else "J5C_CONTINUE_SHADOW_BATCH"
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final_342_jev_shadow_batch_runner_v1")
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--max-new-requests", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    receipt = run_shadow_batch(
        args.repo_root,
        max_new_requests=args.max_new_requests,
    )
    print(receipt.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
