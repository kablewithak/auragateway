"""Offline structural rehearsal for the final 342 transaction wrapper.

This module performs no model, GPU, Kaggle, manifest-freeze, issuer, or live-authority
work. It renders the exact final non-authorizing runtime core and frozen 342-run ledger
into an isolated standalone wrapper, clears repository PYTHONPATH dependence, realizes
the real ModuleType/sys.modules package graph, and validates transaction/runtime identity
seeding without calling a live runtime entry point.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final, TypeAlias, cast

JsonObject: TypeAlias = dict[str, object]

WRAPPER_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/final_342_transaction_bound_wrapper_v1.py.tmpl"
)
RUNTIME_CORE_PATH: Final = Path(
    "src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py"
)
PLANNED_RUN_LEDGER_PATH: Final = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
ARCHITECTURE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_runtime_requalification_architecture_v1.json"
)

EXPECTED_LEDGER_SHA256: Final = "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
EXPECTED_PLANNING_MANIFEST_SHA256: Final = (
    "4bd822375390cf413718553313903679e78b650dfa798955e2f7c61ebd8b8678"
)
EXPECTED_TRAJECTORY_COUNT: Final = 342
EXPECTED_TURN_COUNT: Final = 1368
EXPECTED_MAXIMUM_REQUEST_ATTEMPTS: Final = 2736

NEXT_GATE: Final = "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1"


class WrapperRehearsalError(RuntimeError):
    """Metadata-safe final-wrapper rehearsal failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: Path | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_REQUIRED_FILE_MISSING",
            "required final-wrapper rehearsal file is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _read_json(repo_root: Path, relative: Path) -> JsonObject:
    raw = _read_bytes(repo_root, relative)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_JSON_INVALID",
            "required final-wrapper rehearsal JSON is invalid",
            relative,
        ) from error
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_JSON_ROOT_INVALID",
            "required final-wrapper rehearsal JSON root must be one object",
            relative,
        )
    return cast(JsonObject, value)


def _require_exact_ledger_identity(repo_root: Path) -> bytes:
    ledger_raw = _read_bytes(repo_root, PLANNED_RUN_LEDGER_PATH)
    if sha256_bytes(ledger_raw) != EXPECTED_LEDGER_SHA256:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_LEDGER_IDENTITY_DRIFT",
            "frozen 342-run ledger identity drifted",
            PLANNED_RUN_LEDGER_PATH,
        )
    return ledger_raw


def _validate_architecture_boundary(repo_root: Path) -> None:
    architecture = _read_json(repo_root, ARCHITECTURE_PATH)
    transaction_wrapper = architecture.get("transaction_wrapper")
    authorization = architecture.get("authorization_boundary")
    sequence = architecture.get("implementation_sequence")
    safety = architecture.get("safety_state")

    if not isinstance(transaction_wrapper, dict):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "transaction-wrapper architecture section is invalid",
            ARCHITECTURE_PATH,
        )
    if not isinstance(authorization, dict):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "authorization-boundary architecture section is invalid",
            ARCHITECTURE_PATH,
        )
    if not isinstance(sequence, list):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "implementation sequence is invalid",
            ARCHITECTURE_PATH,
        )
    if not isinstance(safety, dict):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "safety-state architecture section is invalid",
            ARCHITECTURE_PATH,
        )

    expected_sequence = [
        "IMPLEMENT_FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1",
        "REHEARSE_FINAL_342_TRANSACTION_WRAPPER_V1",
        "REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1",
        "BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1",
        "QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1",
        "FRESH_PLATFORM_READINESS_AND_HUMAN_AUTHORITY",
        "ONE_GOVERNED_FINAL_342_EXECUTION",
    ]
    if sequence != expected_sequence:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "final runtime implementation sequence drifted",
            ARCHITECTURE_PATH,
        )

    expected_wrapper_controls = {
        "authorization_producer_notebooks_permitted": False,
        "authorization_specific_kaggle_inputs_permitted": False,
        "manual_confirmation_json_permitted": False,
        "production_module_graph_clobber_guard_may_be_weakened_for_tests": False,
        "real_module_graph_structural_rehearsal_required": True,
        "repository_pythonpath_dependency_permitted_in_rehearsal": False,
        "runtime_payload_identity_bound": True,
        "transaction_bound_execution_artifact_required": True,
        "whole_notebook_sha256_is_semantic_execution_identity": False,
    }
    if any(
        transaction_wrapper.get(key) != value for key, value in expected_wrapper_controls.items()
    ):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "final transaction-wrapper controls drifted",
            ARCHITECTURE_PATH,
        )

    expected_authorization_controls = {
        "execution_manifest_freeze_is_authority": False,
        "final_measured_abc_execution_authorized": False,
        "issuer_capability_is_live_issuance": False,
        "new_execution_authorized": False,
        "runner_implementation_is_authority": False,
        "runtime_anti_replay_established": False,
        "single_use_is_governance_invariant": True,
    }
    if any(
        authorization.get(key) != value for key, value in expected_authorization_controls.items()
    ):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "final authorization boundary drifted",
            ARCHITECTURE_PATH,
        )

    expected_safety = {
        "effect_claims_permitted": False,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "new_execution_authorized": False,
    }
    if any(safety.get(key) != value for key, value in expected_safety.items()):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_ARCHITECTURE_DRIFT",
            "final runtime safety state drifted",
            ARCHITECTURE_PATH,
        )


def validate_subject(repo_root: Path) -> JsonObject:
    """Validate exact predecessor identities without authorizing execution."""

    root = repo_root.resolve()
    _validate_architecture_boundary(root)
    ledger_raw = _require_exact_ledger_identity(root)
    ledger = _read_json(root, PLANNED_RUN_LEDGER_PATH)
    runtime_core = _read_bytes(root, RUNTIME_CORE_PATH)

    runs = ledger.get("runs")
    if (
        ledger.get("total_trajectory_count") != EXPECTED_TRAJECTORY_COUNT
        or ledger.get("total_turn_count") != EXPECTED_TURN_COUNT
        or ledger.get("maximum_request_attempt_count") != EXPECTED_MAXIMUM_REQUEST_ATTEMPTS
        or ledger.get("execution_enabled") is not False
        or ledger.get("execution_manifest_planning_identity_sha256")
        != EXPECTED_PLANNING_MANIFEST_SHA256
        or not isinstance(runs, list)
        or len(runs) != EXPECTED_TRAJECTORY_COUNT
    ):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_LEDGER_CONTRACT_DRIFT",
            "frozen final-run ledger contract drifted",
            PLANNED_RUN_LEDGER_PATH,
        )

    return {
        "runtime_core_sha256": sha256_bytes(runtime_core),
        "planned_run_ledger_sha256": sha256_bytes(ledger_raw),
        "planned_trajectories": EXPECTED_TRAJECTORY_COUNT,
        "planned_turns": EXPECTED_TURN_COUNT,
        "maximum_request_attempts": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
    }


def _replacement_payloads(repo_root: Path) -> dict[str, str]:
    runtime_core = _read_bytes(repo_root, RUNTIME_CORE_PATH)
    ledger = _require_exact_ledger_identity(repo_root)
    payloads = {
        "__RUNTIME_CORE_B64__": runtime_core,
        "__PLANNED_RUN_LEDGER_B64__": ledger,
    }
    replacements: dict[str, str] = {}
    for token, payload in payloads.items():
        replacements[token] = base64.b64encode(payload).decode("ascii")
        replacements[token.replace("_B64__", "_SHA256__")] = sha256_bytes(payload)
    return replacements


def render_rehearsal_wrapper(repo_root: Path) -> bytes:
    """Render the exact standalone final runtime-core wrapper rehearsal."""

    root = repo_root.resolve()
    validate_subject(root)
    template = _read_bytes(root, WRAPPER_TEMPLATE_PATH).decode("utf-8")
    replacements = _replacement_payloads(root)

    rendered = template
    for token, value in replacements.items():
        if token not in rendered:
            raise WrapperRehearsalError(
                "FINAL_342_WRAPPER_TEMPLATE_TOKEN_MISSING",
                "final wrapper rehearsal template token is missing",
                WRAPPER_TEMPLATE_PATH,
            )
        rendered = rendered.replace(token, value)

    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
    if unresolved:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_TEMPLATE_UNRESOLVED",
            "final wrapper rehearsal template retained unresolved tokens",
            WRAPPER_TEMPLATE_PATH,
        )
    return rendered.encode("utf-8")


def rehearse(repo_root: Path) -> JsonObject:
    """Execute the rendered wrapper in an isolated non-authorizing subprocess."""

    root = repo_root.resolve()
    subject = validate_subject(root)
    wrapper = render_rehearsal_wrapper(root)

    env = {key: value for key, value in os.environ.items() if not key.startswith("AURAGATEWAY_")}
    env["PYTHONPATH"] = ""
    env["PYTHONNOUSERSITE"] = "1"

    with tempfile.TemporaryDirectory(
        prefix="auragateway-final-342-wrapper-rehearsal-"
    ) as directory:
        work = Path(directory)
        wrapper_path = work / "final_342_wrapper_rehearsal.py"
        wrapper_path.write_bytes(wrapper)
        completed = subprocess.run(
            [sys.executable, str(wrapper_path)],
            cwd=work,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    if completed.returncode != 0:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_SUBPROCESS_FAILED",
            "isolated final transaction-wrapper rehearsal failed",
        )

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_OUTPUT_INVALID",
            "isolated final wrapper emitted an unexpected output shape",
        )
    try:
        result = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_OUTPUT_INVALID",
            "isolated final wrapper output is not valid JSON",
        ) from error
    if not isinstance(result, dict) or any(not isinstance(key, str) for key in result):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_OUTPUT_INVALID",
            "isolated final wrapper output root is invalid",
        )

    typed = cast(JsonObject, result)
    expected = {
        "status": "FINAL_342_TRANSACTION_WRAPPER_STRUCTURAL_REHEARSAL_PASS",
        "loaded_runtime_module_count": 1,
        "created_module_graph_entry_count": 3,
        "runtime_core_validated": True,
        "planned_trajectories": EXPECTED_TRAJECTORY_COUNT,
        "realized_turns": EXPECTED_TURN_COUNT,
        "maximum_request_attempts": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "runtime_payload_identity_bound": True,
        "transaction_identity_seeded": True,
        "dataclass_module_identity_validated": True,
        "package_import_graph_validated": True,
        "pythonpath_cleared": True,
        "auragateway_environment_cleared": True,
        "system_exit_zero_handled": True,
        "nonzero_system_exit_propagated": True,
        "bootstrap_failure_cleanup_validated": True,
        "live_execution_enabled": False,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "new_execution_authorized": False,
    }
    if any(typed.get(key) != value for key, value in expected.items()):
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_RESULT_DRIFT",
            "isolated final wrapper rehearsal result drifted",
        )
    if typed.get("runtime_core_sha256") != subject["runtime_core_sha256"]:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_RUNTIME_IDENTITY_DRIFT",
            "rendered wrapper runtime-core identity drifted",
        )
    if typed.get("planned_run_ledger_sha256") != subject["planned_run_ledger_sha256"]:
        raise WrapperRehearsalError(
            "FINAL_342_WRAPPER_LEDGER_IDENTITY_DRIFT",
            "rendered wrapper ledger identity drifted",
        )

    typed["rendered_wrapper_sha256"] = sha256_bytes(wrapper)
    typed["next_gate"] = NEXT_GATE
    return typed


def validate_implementation(repo_root: Path) -> JsonObject:
    """Validate the final wrapper rehearsal and preserve non-authority."""

    result = rehearse(repo_root)
    return {
        "status": "FINAL_342_TRANSACTION_WRAPPER_REHEARSAL_V1_VALID",
        "runtime_core_sha256": result["runtime_core_sha256"],
        "planned_run_ledger_sha256": result["planned_run_ledger_sha256"],
        "rendered_wrapper_sha256": result["rendered_wrapper_sha256"],
        "planned_trajectories": EXPECTED_TRAJECTORY_COUNT,
        "realized_turns": EXPECTED_TURN_COUNT,
        "maximum_request_attempts": EXPECTED_MAXIMUM_REQUEST_ATTEMPTS,
        "runtime_payload_identity_bound": True,
        "real_module_graph_structural_rehearsal": True,
        "repository_pythonpath_dependency_permitted": False,
        "authorization_producer_notebooks_permitted": False,
        "authorization_specific_kaggle_inputs_permitted": False,
        "manual_confirmation_json_permitted": False,
        "whole_notebook_sha256_is_semantic_execution_identity": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "live_authorization_issued": False,
        "execution_manifest_frozen": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="final-342-transaction-wrapper-rehearsal-v1")
    parser.add_argument("command", choices=("rehearse", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "rehearse":
            result = rehearse(args.repo_root)
        else:
            result = validate_implementation(args.repo_root)
    except WrapperRehearsalError as error:
        print(
            canonical_json(
                {
                    "status": "ERROR",
                    "error_code": error.error_code,
                    "safe_message": error.safe_message,
                    "path": (error.path.as_posix() if error.path is not None else None),
                }
            )
        )
        return 1

    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
