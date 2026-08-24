"""Deterministic local materialization for measured A/B/C variance-pilot V2."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final, Literal

from pydantic import Field, ValidationError

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.measured_abc_variance_pilot_v2 import (
    EXPECTED_PILOT_TURN_COUNT,
    MAXIMUM_TOTAL_MODEL_REQUESTS,
    PRETREATMENT_REQUEST_COUNT,
    V1_PILOT_SCHEDULE_SHA256,
    build_neutral_worker_plan,
    build_schedule,
)
from auragateway.local_abc.measured_abc_variance_pilot_v2_output_contract import (
    build_generation_contract,
    canonical_json,
    compile_standalone_admission_spec,
    sha256_json,
    strict_response_format,
)

MATERIALIZATION_DIR: Final = Path("data/evals/benchmark/variance-pilot-v2")
PILOT_SCHEDULE_PATH: Final = MATERIALIZATION_DIR / "pilot_schedule.json"
NEUTRAL_PLAN_PATH: Final = MATERIALIZATION_DIR / "neutral_worker_qualification_plan.json"
STRICT_RESPONSE_FORMAT_PATH: Final = MATERIALIZATION_DIR / "strict_response_format.json"
STANDALONE_ADMISSION_SPEC_PATH: Final = MATERIALIZATION_DIR / "standalone_admission_spec.json"
GENERATION_CONTRACT_PATH: Final = MATERIALIZATION_DIR / "generation_contract.json"
MATERIALIZATION_MANIFEST_PATH: Final = MATERIALIZATION_DIR / "local_materialization_manifest.json"


class LocalMaterializationError(RuntimeError):
    """Metadata-safe local materialization failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


class LocalMaterializationManifest(LocalABCContract):
    """Hashes and non-authorization state for deterministic V2 local artifacts."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    materialization_id: Literal["auragateway-variance-pilot-successor-v2-local-v1"] = (
        "auragateway-variance-pilot-successor-v2-local-v1"
    )
    source_v1_schedule_sha256: Literal[
        "da8964631aa690e55e14b8b0e3cd484dc0f9d7fb90090bfad32241b117aa06b7"
    ] = V1_PILOT_SCHEDULE_SHA256
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    neutral_worker_qualification_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    strict_response_format_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    standalone_admission_spec_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pretreatment_request_count: Literal[24] = PRETREATMENT_REQUEST_COUNT
    pilot_request_count: Literal[216] = EXPECTED_PILOT_TURN_COUNT
    maximum_total_model_requests: Literal[240] = MAXIMUM_TOTAL_MODEL_REQUESTS
    tokenizer_budget_proof_complete: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False


def _json_payload(model: LocalABCContract) -> dict[str, object]:
    return model.model_dump(mode="json")


def _build_payloads(repo_root: Path) -> dict[Path, object]:
    schedule = build_schedule(repo_root)
    neutral_plan = build_neutral_worker_plan()
    response_format = strict_response_format()
    admission_spec = compile_standalone_admission_spec()
    generation_contract = build_generation_contract()

    return {
        PILOT_SCHEDULE_PATH: _json_payload(schedule),
        NEUTRAL_PLAN_PATH: _json_payload(neutral_plan),
        STRICT_RESPONSE_FORMAT_PATH: response_format,
        STANDALONE_ADMISSION_SPEC_PATH: _json_payload(admission_spec),
        GENERATION_CONTRACT_PATH: _json_payload(generation_contract),
    }


def build_manifest(repo_root: Path) -> LocalMaterializationManifest:
    """Build the manifest from deterministic in-memory V2 artifacts."""

    payloads = _build_payloads(repo_root)
    return LocalMaterializationManifest(
        pilot_schedule_sha256=sha256_json(payloads[PILOT_SCHEDULE_PATH]),
        neutral_worker_qualification_plan_sha256=sha256_json(payloads[NEUTRAL_PLAN_PATH]),
        strict_response_format_sha256=sha256_json(payloads[STRICT_RESPONSE_FORMAT_PATH]),
        standalone_admission_spec_sha256=sha256_json(payloads[STANDALONE_ADMISSION_SPEC_PATH]),
        generation_contract_sha256=sha256_json(payloads[GENERATION_CONTRACT_PATH]),
    )


def _expected_payloads(repo_root: Path) -> dict[Path, object]:
    payloads = _build_payloads(repo_root)
    payloads[MATERIALIZATION_MANIFEST_PATH] = _json_payload(build_manifest(repo_root))
    return payloads


def _canonical_bytes(value: object) -> bytes:
    return canonical_json(value).encode("utf-8")


def materialize(repo_root: Path) -> dict[str, object]:
    """Write deterministic local artifacts without authorizing execution."""

    payloads = _expected_payloads(repo_root)
    for relative_path, payload in payloads.items():
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical_bytes(payload))
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_LOCAL_MATERIALIZATION_PASS",
        "materialized_path_count": len(payloads),
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }


def validate_materialization(repo_root: Path) -> dict[str, object]:
    """Require exact byte equality with regenerated deterministic artifacts."""

    expected = _expected_payloads(repo_root)
    for relative_path, payload in expected.items():
        path = repo_root / relative_path
        if not path.is_file():
            raise LocalMaterializationError(
                "V2_LOCAL_MATERIALIZATION_MISSING",
                "required V2 local materialization artifact is missing",
                relative_path,
            )
        if path.read_bytes() != _canonical_bytes(payload):
            raise LocalMaterializationError(
                "V2_LOCAL_MATERIALIZATION_DRIFT",
                "V2 local materialization artifact differs from deterministic source",
                relative_path,
            )

    manifest_path = repo_root / MATERIALIZATION_MANIFEST_PATH
    try:
        observed_manifest = LocalMaterializationManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise LocalMaterializationError(
            "V2_LOCAL_MATERIALIZATION_MANIFEST_INVALID",
            "V2 local materialization manifest is invalid",
            MATERIALIZATION_MANIFEST_PATH,
        ) from exc
    if observed_manifest != build_manifest(repo_root):
        raise LocalMaterializationError(
            "V2_LOCAL_MATERIALIZATION_MANIFEST_DRIFT",
            "V2 local materialization manifest identity drifted",
            MATERIALIZATION_MANIFEST_PATH,
        )

    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_LOCAL_MATERIALIZATION_VALID",
        "materialized_path_count": len(expected),
        "tokenizer_budget_proof_complete": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="measured-abc-variance-pilot-v2-local-materialization-v1")
    parser.add_argument("command", choices=("materialize", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        result = (
            materialize(repo_root)
            if args.command == "materialize"
            else validate_materialization(repo_root)
        )
    except LocalMaterializationError as exc:
        print(
            canonical_json(
                {
                    "status": "ERROR",
                    "error_code": exc.error_code,
                    "safe_message": exc.safe_message,
                    "path": exc.path.as_posix() if exc.path is not None else None,
                }
            )
        )
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
