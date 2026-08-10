"""Govern Exact-Runtime P5/P6 authorization transport materialization V1."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

CONTROL_NOTEBOOK_NAME: Final = "ag-p5-p6-auth-control-v1"
CONTROL_OUTPUT_DIRECTORY_NAME: Final = "ag_p5_p6_auth_control_v1"
AUTHORIZATION_FILENAME: Final = "execution_authorization_v1.json"
CONTROL_MANIFEST_FILENAME: Final = "control_package_manifest.json"
MATERIALIZATION_RECEIPT_FILENAME: Final = "materialization_receipt.json"
AUTHORIZATION_SCOPE: Final = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
AUTHORIZATION_ID: Final = (
    "auragateway-exact-runtime-p5-p6-requalification-v2-execution-authorization"
)
CONTROL_PACKAGE_ID: Final = "auragateway-exact-runtime-p5-p6-authorization-control-v1"
TRANSPORT_CONTRACT: Final = "GOVERNED_ROOT_EXACT_FLAT_V1"
MAXIMUM_AUTHORIZATION_BYTES: Final = 64 * 1024

EXPECTED_CONTROL_FILENAMES: Final = frozenset(
    {
        AUTHORIZATION_FILENAME,
        CONTROL_MANIFEST_FILENAME,
        MATERIALIZATION_RECEIPT_FILENAME,
    }
)


class AuthorizationTransportError(RuntimeError):
    """Metadata-safe transport-boundary error."""

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

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_ARGUMENT_INVALID",
            message,
        )


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class ControlPackageManifest(_FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    control_package_id: Literal["auragateway-exact-runtime-p5-p6-authorization-control-v1"]
    transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"]
    producer_notebook_name: Literal["ag-p5-p6-auth-control-v1"]
    producer_output_directory: Literal["ag_p5_p6_auth_control_v1"]
    authorization_file: Literal["execution_authorization_v1.json"]
    authorization_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_file_size_bytes: int = Field(
        gt=0,
        le=MAXIMUM_AUTHORIZATION_BYTES,
    )
    authorization_scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"]
    authorization_id: Literal[
        "auragateway-exact-runtime-p5-p6-requalification-v2-execution-authorization"
    ]
    exact_flat_file_count: Literal[3] = 3
    runtime_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0


class MaterializationReceipt(_FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["MATERIALIZED"] = "MATERIALIZED"
    notebook_name: Literal["ag-p5-p6-auth-control-v1"]
    output_directory: Literal["ag_p5_p6_auth_control_v1"]
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_count: Literal[3] = 3
    nested_archives_present: Literal[False] = False
    runtime_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0


class AuthorizationTransportVerification(_FrozenModel):
    root: str
    authorization_path: str
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_size_bytes: int = Field(gt=0)
    control_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    materialization_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    producer_notebook_name: Literal["ag-p5-p6-auth-control-v1"]
    producer_output_directory: Literal["ag_p5_p6_auth_control_v1"]
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
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
            f"authorization timestamp is invalid: {field_name}",
        )
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
            f"authorization timestamp is invalid: {field_name}",
        ) from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
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
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_SIZE_INVALID",
            "authorization exceeds the bounded transport size",
        )
    try:
        payload = json.loads(authorization_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
            "authorization is not valid UTF-8 JSON",
        ) from error
    if not isinstance(payload, dict):
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
            "authorization root must be a JSON object",
        )
    canonical = canonical_json_bytes(payload)
    if authorization_bytes != canonical:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_NON_CANONICAL",
            "authorization transport requires canonical JSON bytes",
        )
    required = {
        "schema_version": "1.0.0",
        "authorization_id": AUTHORIZATION_ID,
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "scope": AUTHORIZATION_SCOPE,
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
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise AuthorizationTransportError(
                "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
                f"authorization transport envelope drifted: {key}",
            )
    issued_at = _parse_time(payload.get("issued_at"), "issued_at")
    expires_at = _parse_time(payload.get("expires_at"), "expires_at")
    if expires_at <= issued_at:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
            "authorization expiry does not follow issuance",
        )
    current = datetime.now(UTC) if now is None else now.astimezone(UTC)
    if require_live and (current < issued_at or current >= expires_at):
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_EXPIRED",
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
            "P5_P6_AUTHORIZATION_TRANSPORT_OUTPUT_EXISTS",
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
            "P5_P6_AUTHORIZATION_TRANSPORT_FILE_SET_DRIFT",
            "materialized authorization control file set drifted",
            output_root.as_posix(),
        )
    return receipt


def _load_canonical_model(path: Path, model: type[_FrozenModel]) -> _FrozenModel:
    if not path.is_file() or path.is_symlink():
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_MEMBER_UNSAFE",
            "authorization control member is missing or unsafe",
            path.as_posix(),
        )
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
        parsed = model.model_validate(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_MEMBER_INVALID",
            "authorization control member is invalid",
            path.as_posix(),
        ) from error
    if raw != parsed.canonical_bytes():
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_MEMBER_NON_CANONICAL",
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
            "P5_P6_AUTHORIZATION_TRANSPORT_ROOT_CARDINALITY_INVALID",
            "expected exactly one governed authorization control root",
        )
    control_root = candidate_roots[0]
    if resolved_input not in control_root.parents:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_ROOT_ESCAPE",
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
            "P5_P6_AUTHORIZATION_TRANSPORT_FILE_SET_DRIFT",
            "authorization control root does not contain the exact flat file set",
            control_root.as_posix(),
        )
    for path in members:
        if path.is_symlink() or not path.is_file():
            raise AuthorizationTransportError(
                "P5_P6_AUTHORIZATION_TRANSPORT_MEMBER_UNSAFE",
                "authorization control root contains an unsafe member",
                path.as_posix(),
            )
        if path.suffix.lower() in {".zip", ".tar", ".tgz", ".7z"}:
            raise AuthorizationTransportError(
                "P5_P6_AUTHORIZATION_TRANSPORT_NESTED_ARCHIVE",
                "authorization control root contains a nested archive",
                path.as_posix(),
            )

    authorization_path = control_root / AUTHORIZATION_FILENAME
    manifest_path = control_root / CONTROL_MANIFEST_FILENAME
    receipt_path = control_root / MATERIALIZATION_RECEIPT_FILENAME
    authorization_bytes = authorization_path.read_bytes()
    authorization = validate_authorization_bytes(
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
    authorization_sha = sha256_bytes(authorization_bytes)
    manifest_sha = file_sha256(manifest_path)

    expected_manifest = build_control_manifest(authorization_bytes)
    if manifest != expected_manifest:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_MANIFEST_BINDING_DRIFT",
            "authorization control manifest does not bind the authorization bytes",
            manifest_path.as_posix(),
        )
    if receipt.authorization_sha256 != authorization_sha:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_RECEIPT_BINDING_DRIFT",
            "materialization receipt authorization identity drifted",
            receipt_path.as_posix(),
        )
    if receipt.control_manifest_sha256 != manifest_sha:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_RECEIPT_BINDING_DRIFT",
            "materialization receipt manifest identity drifted",
            receipt_path.as_posix(),
        )
    if authorization.get("scope") != AUTHORIZATION_SCOPE:
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_INVALID",
            "authorization scope drifted after transport validation",
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


def _base64_string_literal(value: str) -> str:
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    chunks = tuple(encoded[index : index + 76] for index in range(0, len(encoded), 76))
    lines = ["base64.b64decode(", "    ("]
    lines.extend(f'        "{chunk}"' for chunk in chunks)
    lines.extend(
        [
            '    ).encode("ascii"),',
            "    validate=True,",
            ').decode("utf-8")',
        ]
    )
    return "\n".join(lines)


def build_control_materializer_notebook(
    authorization_bytes: bytes,
) -> dict[str, object]:
    authorization = validate_authorization_bytes(
        authorization_bytes,
        require_live=True,
    )
    authorization_b64 = base64.b64encode(authorization_bytes).decode("ascii")
    expected_sha = sha256_bytes(authorization_bytes)
    encoded_literal = _base64_string_literal(authorization_b64)
    source = f"""from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

NOTEBOOK_NAME = "{CONTROL_NOTEBOOK_NAME}"
WORK_ROOT = Path("/kaggle/working").resolve()
OUTPUT_ROOT = WORK_ROOT / "{CONTROL_OUTPUT_DIRECTORY_NAME}"
AUTHORIZATION_FILENAME = "{AUTHORIZATION_FILENAME}"
CONTROL_MANIFEST_FILENAME = "{CONTROL_MANIFEST_FILENAME}"
MATERIALIZATION_RECEIPT_FILENAME = "{MATERIALIZATION_RECEIPT_FILENAME}"
EXPECTED_AUTHORIZATION_SHA256 = "{expected_sha}"
AUTHORIZATION_B64 = (
{encoded_literal}
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


loaded_runtime_modules = sorted(
    name
    for name in sys.modules
    if name == "vllm"
    or name.startswith("vllm.")
    or name == "torch"
    or name.startswith("torch.")
)
if loaded_runtime_modules:
    raise RuntimeError("control materializer requires a fresh CPU-only kernel")
if OUTPUT_ROOT.exists():
    raise RuntimeError("control output directory already exists")

authorization_bytes = base64.b64decode(
    AUTHORIZATION_B64.encode("ascii"),
    validate=True,
)
if sha256_bytes(authorization_bytes) != EXPECTED_AUTHORIZATION_SHA256:
    raise RuntimeError("embedded authorization identity drifted")

authorization = json.loads(authorization_bytes.decode("utf-8"))
if not isinstance(authorization, dict):
    raise RuntimeError("embedded authorization root must be an object")
if canonical_json_bytes(authorization) != authorization_bytes:
    raise RuntimeError("embedded authorization is not canonical")

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
    "authorization_id": (
        "auragateway-exact-runtime-p5-p6-requalification-v2-"
        "execution-authorization"
    ),
    "exact_flat_file_count": 3,
    "runtime_execution_performed": False,
    "gpu_execution_performed": False,
    "model_loaded": False,
    "worker_started": False,
    "model_requests_performed": 0,
}}

OUTPUT_ROOT.mkdir(parents=True)
authorization_path = OUTPUT_ROOT / AUTHORIZATION_FILENAME
manifest_path = OUTPUT_ROOT / CONTROL_MANIFEST_FILENAME
receipt_path = OUTPUT_ROOT / MATERIALIZATION_RECEIPT_FILENAME

authorization_path.write_bytes(authorization_bytes)
manifest_bytes = canonical_json_bytes(manifest)
manifest_path.write_bytes(manifest_bytes)

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
receipt_path.write_bytes(canonical_json_bytes(receipt))

expected_names = {{
    AUTHORIZATION_FILENAME,
    CONTROL_MANIFEST_FILENAME,
    MATERIALIZATION_RECEIPT_FILENAME,
}}
observed_names = {{path.name for path in OUTPUT_ROOT.iterdir()}}
if observed_names != expected_names:
    raise RuntimeError("control output file set drifted")

print(f"output_directory={{OUTPUT_ROOT}}")
print("file_count=3")
print(f"authorization_sha256={{EXPECTED_AUTHORIZATION_SHA256}}")
print(f"control_manifest_sha256={{sha256_bytes(manifest_bytes)}}")
print("runtime_execution_performed=false")
print("gpu_execution_performed=false")
print("model_loaded=false")
print("worker_started=false")
print("model_requests_performed=0")
print("save_this_notebook_output=true")
"""
    compile(source, "<p5-p6-auth-control-v1>", "exec")
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "p5-p6-auth-control-introduction",
                "metadata": {},
                "source": [
                    "# AuraGateway P5/P6 authorization control materializer v1\n",
                    "\n",
                    "Materializes one canonical single-use authorization into a "
                    "flat governed control output. Accelerator None, Internet Off, "
                    "no secrets, Save Version -> Save & Run All.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "p5-p6-auth-control-materializer",
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "auragateway": {
                "authorization_sha256": sha256_bytes(authorization_bytes),
                "authorization_scope": cast(str, authorization["scope"]),
                "control_output_directory": CONTROL_OUTPUT_DIRECTORY_NAME,
                "notebook_name": CONTROL_NOTEBOOK_NAME,
            },
            "kaggle": {
                "accelerator": "none",
                "dataSources": [],
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_control_materializer_notebook(
    authorization_path: Path,
    output_path: Path,
) -> dict[str, object]:
    if not authorization_path.is_file():
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_AUTHORIZATION_MISSING",
            "authorization file is missing",
            authorization_path.as_posix(),
        )
    notebook = build_control_materializer_notebook(authorization_path.read_bytes())
    payload = (
        json.dumps(
            notebook,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise AuthorizationTransportError(
            "P5_P6_AUTHORIZATION_TRANSPORT_NOTEBOOK_EXISTS",
            "control materializer output notebook already exists",
            output_path.as_posix(),
        )
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        temporary.replace(output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "status": "P5_P6_AUTHORIZATION_CONTROL_MATERIALIZER_GENERATED",
        "notebook_path": output_path.as_posix(),
        "notebook_name": CONTROL_NOTEBOOK_NAME,
        "notebook_sha256": sha256_bytes(payload),
        "authorization_sha256": sha256_bytes(authorization_path.read_bytes()),
        "runtime_execution_performed": False,
        "gpu_execution_performed": False,
        "model_requests_performed": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate-control-materializer")
    generate.add_argument("--authorization-path", required=True)
    generate.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = write_control_materializer_notebook(
            Path(cast(str, args.authorization_path)).resolve(),
            Path(cast(str, args.output)).resolve(),
        )
    except AuthorizationTransportError as error:
        print(json.dumps(error.envelope(), sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
