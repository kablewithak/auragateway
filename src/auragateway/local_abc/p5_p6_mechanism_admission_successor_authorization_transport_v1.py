"""Materialize the successor authorization into the governed three-file control package."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

CONTROL_NOTEBOOK_NAME: Final = "ag-p5-p6-mechanism-auth-control-v1"
CONTROL_OUTPUT_DIRECTORY_NAME: Final = "ag_p5_p6_mechanism_auth_control_v1"
AUTHORIZATION_FILENAME: Final = "execution_authorization_v1.json"
CONTROL_MANIFEST_FILENAME: Final = "control_package_manifest.json"
MATERIALIZATION_RECEIPT_FILENAME: Final = "materialization_receipt.json"
AUTHORIZATION_SCOPE: Final = "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
AUTHORIZATION_ID: Final = (
    "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization"
)
CONTROL_PACKAGE_ID: Final = (
    "auragateway-p5-p6-mechanism-admission-successor-v1-authorization-control-v1"
)
TRANSPORT_CONTRACT: Final = "GOVERNED_ROOT_EXACT_FLAT_V1"
MAXIMUM_AUTHORIZATION_BYTES: Final = 64 * 1024
RUNTIME_SCRIPT_SHA256: Final = "a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958"
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330"
)
DESIGN_RECORD_SHA256: Final = "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
MECHANISM_CONTRACT_SHA256: Final = (
    "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
)
IMPLEMENTATION_ADDENDUM_SHA256: Final = (
    "395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239"
)
EXPECTED_CONTROL_FILENAMES: Final = frozenset(
    {
        AUTHORIZATION_FILENAME,
        CONTROL_MANIFEST_FILENAME,
        MATERIALIZATION_RECEIPT_FILENAME,
    }
)


class AuthorizationTransportError(RuntimeError):
    """Metadata-safe fail-closed transport error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class ControlPackageManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    control_package_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-authorization-control-v1"
    ]
    transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"]
    producer_notebook_name: Literal["ag-p5-p6-mechanism-auth-control-v1"]
    producer_output_directory: Literal["ag_p5_p6_mechanism_auth_control_v1"]
    authorization_file: Literal["execution_authorization_v1.json"]
    authorization_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_file_size_bytes: int = Field(gt=0, le=MAXIMUM_AUTHORIZATION_BYTES)
    authorization_scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"]
    authorization_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-execution-authorization"
    ]
    exact_flat_file_count: Literal[3] = 3
    runtime_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0


class MaterializationReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["MATERIALIZED"] = "MATERIALIZED"
    notebook_name: Literal["ag-p5-p6-mechanism-auth-control-v1"]
    output_directory: Literal["ag_p5_p6_mechanism_auth_control_v1"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_count: Literal[3] = 3
    nested_archives_present: Literal[False] = False
    runtime_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0


class AuthorizationTransportVerification(FrozenModel):
    root: str
    authorization_path: str
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_size_bytes: int = Field(gt=0)
    control_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    materialization_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    producer_notebook_name: Literal["ag-p5-p6-mechanism-auth-control-v1"]
    producer_output_directory: Literal["ag_p5_p6_mechanism_auth_control_v1"]
    exact_flat_file_count: Literal[3] = 3


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_time(raw: object, field_name: str) -> datetime:
    if not isinstance(raw, str):
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_TIME_INVALID",
            f"authorization timestamp is invalid: {field_name}",
        )
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_TIME_INVALID",
            f"authorization timestamp is invalid: {field_name}",
        ) from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_TIME_INVALID",
            f"authorization timestamp must be timezone-aware: {field_name}",
        )
    return value.astimezone(UTC)


def validate_authorization_bytes(
    authorization_bytes: bytes,
    *,
    require_live: bool,
    now: datetime | None = None,
) -> dict[str, object]:
    if not authorization_bytes or len(authorization_bytes) > MAXIMUM_AUTHORIZATION_BYTES:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_SIZE_INVALID",
            "authorization exceeds the bounded transport size",
        )
    try:
        payload = json.loads(authorization_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_JSON_INVALID",
            "authorization is not valid UTF-8 JSON",
        ) from error
    if not isinstance(payload, dict):
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_ROOT_INVALID",
            "authorization root must be a JSON object",
        )
    if authorization_bytes != canonical_json_bytes(payload):
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_NON_CANONICAL",
            "authorization transport requires canonical JSON bytes",
        )
    required = {
        "schema_version": "1.0.0",
        "authorization_id": AUTHORIZATION_ID,
        "authorization_filename": AUTHORIZATION_FILENAME,
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": AUTHORIZATION_SCOPE,
        "runtime_script_sha256": RUNTIME_SCRIPT_SHA256,
        "implementation_review_sha256": IMPLEMENTATION_REVIEW_SHA256,
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "mechanism_admission_contract_sha256": MECHANISM_CONTRACT_SHA256,
        "implementation_addendum_sha256": IMPLEMENTATION_ADDENDUM_SHA256,
        "runtime_execution_authorized": True,
        "single_use": True,
        "every_terminal_attempt_consumes_authorization": True,
        "unchanged_replay_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "maximum_model_requests": 6,
        "maximum_worker_starts": 3,
        "maximum_model_loads": 3,
        "hidden_retries_permitted": 0,
        "authorization_reusable": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise AuthorizationTransportError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_SEMANTIC_DRIFT",
                f"authorization transport envelope drifted: {key}",
            )
    issued_at = _parse_time(payload.get("issued_at"), "issued_at")
    expires_at = _parse_time(payload.get("expires_at"), "expires_at")
    if expires_at <= issued_at:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_TIME_INVALID",
            "authorization expiry does not follow issuance",
        )
    current = datetime.now(UTC) if now is None else now.astimezone(UTC)
    if require_live and (current < issued_at or current >= expires_at):
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_EXPIRED",
            "authorization is outside its live time window",
        )
    return cast(dict[str, object], payload)


def build_control_manifest(authorization_bytes: bytes) -> ControlPackageManifest:
    authorization = validate_authorization_bytes(
        authorization_bytes,
        require_live=False,
    )
    return ControlPackageManifest(
        control_package_id=CONTROL_PACKAGE_ID,
        transport_contract=TRANSPORT_CONTRACT,
        producer_notebook_name=CONTROL_NOTEBOOK_NAME,
        producer_output_directory=CONTROL_OUTPUT_DIRECTORY_NAME,
        authorization_file=AUTHORIZATION_FILENAME,
        authorization_file_sha256=sha256_bytes(authorization_bytes),
        authorization_file_size_bytes=len(authorization_bytes),
        authorization_scope=AUTHORIZATION_SCOPE,
        authorization_id=cast(str, authorization["authorization_id"]),
    )


def materialize_control_package(
    output_root: Path,
    authorization_bytes: bytes,
) -> MaterializationReceipt:
    if output_root.exists():
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_OUTPUT_EXISTS",
            "authorization control output already exists",
            output_root.as_posix(),
        )
    validate_authorization_bytes(authorization_bytes, require_live=False)
    manifest = build_control_manifest(authorization_bytes)
    output_root.mkdir(parents=True)
    authorization_path = output_root / AUTHORIZATION_FILENAME
    manifest_path = output_root / CONTROL_MANIFEST_FILENAME
    receipt_path = output_root / MATERIALIZATION_RECEIPT_FILENAME
    authorization_path.write_bytes(authorization_bytes)
    manifest_path.write_bytes(manifest.canonical_bytes())
    receipt = MaterializationReceipt(
        notebook_name=CONTROL_NOTEBOOK_NAME,
        output_directory=CONTROL_OUTPUT_DIRECTORY_NAME,
        authorization_sha256=sha256_bytes(authorization_bytes),
        control_manifest_sha256=sha256_bytes(manifest.canonical_bytes()),
    )
    receipt_path.write_bytes(receipt.canonical_bytes())
    observed_names = frozenset(path.name for path in output_root.iterdir())
    if observed_names != EXPECTED_CONTROL_FILENAMES:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_FILE_SET_DRIFT",
            "materialized authorization control file set drifted",
            output_root.as_posix(),
        )
    return receipt


def _load_canonical_model(path: Path, model: type[FrozenModel]) -> FrozenModel:
    if not path.is_file() or path.is_symlink():
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_MEMBER_UNSAFE",
            "authorization control member is missing or unsafe",
            path.as_posix(),
        )
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
        parsed = model.model_validate(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_MEMBER_INVALID",
            "authorization control member is invalid",
            path.as_posix(),
        ) from error
    if raw != parsed.canonical_bytes():
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_MEMBER_NON_CANONICAL",
            "authorization control member is not canonical",
            path.as_posix(),
        )
    return parsed


def resolve_governed_control_root(input_root: Path) -> Path:
    resolved_input = input_root.resolve()
    candidate_roots = tuple(
        sorted(
            {
                path.resolve()
                for path in resolved_input.rglob(CONTROL_OUTPUT_DIRECTORY_NAME)
                if path.is_dir()
                and not path.is_symlink()
                and CONTROL_NOTEBOOK_NAME in path.resolve().parts
            },
            key=lambda item: item.as_posix(),
        )
    )
    if len(candidate_roots) != 1:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_ROOT_CARDINALITY_INVALID",
            "expected exactly one governed authorization control root",
        )
    control_root = candidate_roots[0]
    if resolved_input not in control_root.parents:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_ROOT_ESCAPE",
            "authorization control root escaped the input boundary",
            control_root.as_posix(),
        )
    return control_root


def validate_control_package(
    input_root: Path,
    *,
    require_live_authorization: bool,
    now: datetime | None = None,
) -> AuthorizationTransportVerification:
    control_root = resolve_governed_control_root(input_root)
    members = tuple(sorted(control_root.iterdir(), key=lambda item: item.name))
    names = frozenset(path.name for path in members)
    if names != EXPECTED_CONTROL_FILENAMES:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_FILE_SET_DRIFT",
            "authorization control root does not contain the exact flat file set",
            control_root.as_posix(),
        )
    for path in members:
        if path.is_symlink() or not path.is_file():
            raise AuthorizationTransportError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_MEMBER_UNSAFE",
                "authorization control root contains an unsafe member",
                path.as_posix(),
            )
        if path.suffix.lower() in {".zip", ".tar", ".tgz", ".7z"}:
            raise AuthorizationTransportError(
                "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_NESTED_ARCHIVE",
                "authorization control root contains a nested archive",
                path.as_posix(),
            )
    authorization_path = control_root / AUTHORIZATION_FILENAME
    manifest_path = control_root / CONTROL_MANIFEST_FILENAME
    receipt_path = control_root / MATERIALIZATION_RECEIPT_FILENAME
    authorization_bytes = authorization_path.read_bytes()
    validate_authorization_bytes(
        authorization_bytes,
        require_live=require_live_authorization,
        now=now,
    )
    manifest = cast(
        ControlPackageManifest,
        _load_canonical_model(manifest_path, ControlPackageManifest),
    )
    receipt = cast(
        MaterializationReceipt,
        _load_canonical_model(receipt_path, MaterializationReceipt),
    )
    expected_manifest = build_control_manifest(authorization_bytes)
    if manifest != expected_manifest:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_MANIFEST_BINDING_DRIFT",
            "authorization control manifest does not bind authorization bytes",
            manifest_path.as_posix(),
        )
    authorization_sha = sha256_bytes(authorization_bytes)
    manifest_sha = file_sha256(manifest_path)
    if receipt.authorization_sha256 != authorization_sha:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_RECEIPT_BINDING_DRIFT",
            "materialization receipt authorization identity drifted",
            receipt_path.as_posix(),
        )
    if receipt.control_manifest_sha256 != manifest_sha:
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_RECEIPT_BINDING_DRIFT",
            "materialization receipt manifest identity drifted",
            receipt_path.as_posix(),
        )
    return AuthorizationTransportVerification(
        root=control_root.as_posix(),
        authorization_path=authorization_path.as_posix(),
        authorization_sha256=authorization_sha,
        authorization_size_bytes=len(authorization_bytes),
        control_manifest_sha256=manifest_sha,
        materialization_receipt_sha256=file_sha256(receipt_path),
        producer_notebook_name=CONTROL_NOTEBOOK_NAME,
        producer_output_directory=CONTROL_OUTPUT_DIRECTORY_NAME,
    )


def _base64_chunks(payload: bytes) -> list[str]:
    encoded = base64.b64encode(payload).decode("ascii")
    return [encoded[index : index + 76] for index in range(0, len(encoded), 76)]


def build_control_materializer_notebook(
    authorization_bytes: bytes,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    validate_authorization_bytes(
        authorization_bytes,
        require_live=True,
        now=now,
    )
    chunks = _base64_chunks(authorization_bytes)
    chunk_lines = "\n".join(f'    "{chunk}"' for chunk in chunks)
    expected_authorization_sha = sha256_bytes(authorization_bytes)
    source = f'''from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

NOTEBOOK_NAME = "{CONTROL_NOTEBOOK_NAME}"
OUTPUT_ROOT = Path("/kaggle/working/{CONTROL_OUTPUT_DIRECTORY_NAME}")
AUTHORIZATION_FILENAME = "{AUTHORIZATION_FILENAME}"
CONTROL_MANIFEST_FILENAME = "{CONTROL_MANIFEST_FILENAME}"
MATERIALIZATION_RECEIPT_FILENAME = "{MATERIALIZATION_RECEIPT_FILENAME}"
EXPECTED_AUTHORIZATION_SHA256 = "{expected_authorization_sha}"
AUTHORIZATION_B64 = (
{chunk_lines}
)


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


if OUTPUT_ROOT.exists():
    raise RuntimeError("authorization control output already exists")
OUTPUT_ROOT.mkdir(parents=True)
authorization_bytes = base64.b64decode("".join(AUTHORIZATION_B64))
if sha256_bytes(authorization_bytes) != EXPECTED_AUTHORIZATION_SHA256:
    raise RuntimeError("authorization identity drifted")
authorization = json.loads(authorization_bytes.decode("utf-8"))
manifest = {{
    "schema_version": "1.0.0",
    "control_package_id": "{CONTROL_PACKAGE_ID}",
    "transport_contract": "{TRANSPORT_CONTRACT}",
    "producer_notebook_name": NOTEBOOK_NAME,
    "producer_output_directory": OUTPUT_ROOT.name,
    "authorization_file": AUTHORIZATION_FILENAME,
    "authorization_file_sha256": EXPECTED_AUTHORIZATION_SHA256,
    "authorization_file_size_bytes": len(authorization_bytes),
    "authorization_scope": "{AUTHORIZATION_SCOPE}",
    "authorization_id": "{AUTHORIZATION_ID}",
    "exact_flat_file_count": 3,
    "runtime_execution_performed": False,
    "gpu_execution_performed": False,
    "model_loaded": False,
    "worker_started": False,
    "model_requests_performed": 0,
}}
manifest_bytes = canonical_json_bytes(manifest)
(OUTPUT_ROOT / AUTHORIZATION_FILENAME).write_bytes(authorization_bytes)
(OUTPUT_ROOT / CONTROL_MANIFEST_FILENAME).write_bytes(manifest_bytes)
receipt = {{
    "schema_version": "1.0.0",
    "status": "MATERIALIZED",
    "notebook_name": NOTEBOOK_NAME,
    "output_directory": OUTPUT_ROOT.name,
    "authorization_sha256": EXPECTED_AUTHORIZATION_SHA256,
    "control_manifest_sha256": sha256_bytes(manifest_bytes),
    "file_count": 3,
    "nested_archives_present": False,
    "runtime_execution_performed": False,
    "gpu_execution_performed": False,
    "model_loaded": False,
    "worker_started": False,
    "model_requests_performed": 0,
}}
(OUTPUT_ROOT / MATERIALIZATION_RECEIPT_FILENAME).write_bytes(canonical_json_bytes(receipt))
print("authorization_control_materialization=PASS")
print("runtime_execution_performed=false")
print("gpu_execution_performed=false")
print("model_loaded=false")
print("worker_started=false")
print("model_requests_performed=0")
print("save_this_notebook_output=true")
'''
    compile(source, "<p5-p6-mechanism-auth-control-v1>", "exec")
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# AuraGateway P5/P6 Mechanism Authorization Control V1\n",
                    "CPU-only authorization materialization. No model execution.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "accelerator": "none",
            "internet": False,
            "kaggle": {
                "accelerator": "none",
                "isGpuEnabled": False,
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_materializer_notebook(
    output_path: Path,
    authorization_path: Path,
) -> dict[str, object]:
    authorization_bytes = authorization_path.read_bytes()
    notebook = build_control_materializer_notebook(authorization_bytes)
    payload = (json.dumps(notebook, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    if output_path.exists():
        raise AuthorizationTransportError(
            "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_NOTEBOOK_EXISTS",
            "control materializer notebook already exists",
            output_path.as_posix(),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return {
        "status": "P5_P6_SUCCESSOR_AUTHORIZATION_CONTROL_NOTEBOOK_GENERATED",
        "notebook_sha256": sha256_bytes(payload),
        "runtime_execution_performed": False,
        "gpu_execution_performed": False,
        "model_requests_performed": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-notebook", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        result = write_materializer_notebook(
            arguments.output_notebook,
            arguments.authorization,
        )
    except (OSError, AuthorizationTransportError) as error:
        payload = {
            "error_code": "P5_P6_SUCCESSOR_AUTHORIZATION_TRANSPORT_IO_ERROR",
            "safe_message": "authorization transport I/O failed",
            "path": None,
        }
        if isinstance(error, AuthorizationTransportError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            }
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
