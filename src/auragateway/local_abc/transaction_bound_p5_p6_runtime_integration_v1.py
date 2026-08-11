"""Generate and validate the transaction-bound P5/P6 runtime integration V1."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never

from pydantic import BaseModel, ConfigDict, Field

BASE_MAIN_COMMIT: Final = "4afdcf9d840bc90ceb34af8dae098998f78de572"

DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_design_v1.json"
)
AUTHORIZATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_v1_record.json"
)
AUTHORIZATION_RECORD_SHA256: Final = (
    "0d1ab1c39914e57546e4a42e312a1ee8b26c69366bb2ac0d44392df67e47b037"
)
AUTHORIZATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_execution_authorization_v1_review.json"
)
AUTHORIZATION_REVIEW_SHA256: Final = (
    "ce14481086f3ee820deebc38dcc0aaaf4879e3690b38436e2e5b1d44eabc8766"
)
V2_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v2.py.tmpl"
)
V2_OUTCOME_UNKNOWN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_v2_outcome_unknown_acceptance_v1.json"
)
V2_OUTCOME_UNKNOWN_SHA256: Final = (
    "66603d034a229b8ee623a6f5c93e3a7f5045da474443c9693c2f7629acf2fc07"
)
WRAPPER_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/transaction_bound_execution_wrapper_v1.py.tmpl"
)

RUNTIME_PAYLOAD_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_v1.json"
)

NOTEBOOK_NAME: Final = "ag-p5-p6-transaction-bound-v1"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
EVIDENCE_ZIP_NAME: Final = "ag-p5-p6-transaction-bound-evidence-v1.zip"
NEXT_GATE: Final = "CPU_OR_MANUAL_KAGGLE_TOPOLOGY_REHEARSAL_V1"

REQUEST_ROLES: Final = (
    "BASE_COLD",
    "BASE_WARM",
    "NEGATIVE_PREFIX",
    "POST_RESET_COLD",
    "CROSS_WORKER_COLD",
    "WORKER1_RETENTION",
)

REMOVED_AUTHORIZATION_FUNCTIONS: Final = {
    "_parse_authorization_time",
    "_load_canonical_control_json",
    "resolve_authorization_control_output",
    "require_execution_authorization",
}
ALLOWED_CHANGED_FUNCTIONS: Final = {
    *REMOVED_AUTHORIZATION_FUNCTIONS,
    "run_bounded_process",
    "directory_snapshot",
    "cleanup_scratch",
    "common_prefix_token_count",
    "tokenize_request",
    "main",
}
ALLOWED_ADDED_FUNCTIONS: Final = {
    "require_transaction_bound_context",
    "safe_worker_teardown",
}


class RuntimeIntegrationError(RuntimeError):
    """Fail-closed runtime-integration generation error."""

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
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IntegrationReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-transaction-bound-p5-p6-runtime-integration-v1-review"]
    status: Literal["APPROVED_FOR_TRANSACTION_BOUND_RUNTIME_INTEGRATION"]
    base_main_commit: Literal["4afdcf9d840bc90ceb34af8dae098998f78de572"]
    authorization_record_sha256: Literal[
        "0d1ab1c39914e57546e4a42e312a1ee8b26c69366bb2ac0d44392df67e47b037"
    ]
    authorization_review_sha256: Literal[
        "ce14481086f3ee820deebc38dcc0aaaf4879e3690b38436e2e5b1d44eabc8766"
    ]
    predecessor_v2_template_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_outcome_unknown_sha256: Literal[
        "66603d034a229b8ee623a6f5c93e3a7f5045da474443c9693c2f7629acf2fc07"
    ]
    wrapper_template_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    unchanged_behavioral_function_count: int = Field(ge=1)
    authorization_transport_removed: Literal[True]
    six_request_contract_preserved: Literal[True]
    process_success_semantics_zero_exit: Literal[True]
    symlink_regression_covered: Literal[True]
    cleanup_failure_cannot_mask_primary: Literal[True]
    worker_teardown_failure_cannot_mask_primary: Literal[True]
    evidence_packaging_failure_cannot_mask_primary: Literal[True]
    live_authorization_issued: Literal[False]
    gpu_execution_authorized: Literal[False]
    next_gate: Literal["CPU_OR_MANUAL_KAGGLE_TOPOLOGY_REHEARSAL_V1"]


class IntegrationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-transaction-bound-p5-p6-runtime-integration-v1"]
    status: Literal["TRANSACTION_BOUND_P5_P6_RUNTIME_INTEGRATION_VALID"]
    base_main_commit: Literal["4afdcf9d840bc90ceb34af8dae098998f78de572"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_path: Literal["src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"]
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    live_authorization_boundary_ready: Literal[True]
    symlink_regression_covered: Literal[True]
    authorization_specific_kaggle_inputs: Literal[0]
    authorization_producer_notebooks: Literal[0]
    manual_confirmation_json_files: Literal[0]
    primary_failure_preserved_separately: Literal[True]
    process_success_semantics_zero_exit: Literal[True]
    current_runtime_p5_p6_requalified: Literal[False]
    runtime_anti_replay_established: Literal[False]
    live_authorization_issued: Literal[False]
    gpu_execution_authorized: Literal[False]
    next_gate: Literal["CPU_OR_MANUAL_KAGGLE_TOPOLOGY_REHEARSAL_V1"]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_REQUIRED_ARTIFACT_MISSING",
            "required runtime-integration artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _git(root: Path, *arguments: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip()


def _require_base_ancestor(root: Path) -> None:
    code, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        BASE_MAIN_COMMIT,
        "HEAD",
    )
    if code != 0:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_BASE_MISSING",
            "merged transaction-bound authorization implementation is not an ancestor",
        )


def _validate_authorities(root: Path) -> None:
    expected = (
        (AUTHORIZATION_RECORD_PATH, AUTHORIZATION_RECORD_SHA256),
        (AUTHORIZATION_REVIEW_PATH, AUTHORIZATION_REVIEW_SHA256),
        (V2_OUTCOME_UNKNOWN_PATH, V2_OUTCOME_UNKNOWN_SHA256),
    )
    for relative, expected_sha in expected:
        observed = _sha256(_read_required(root, relative))
        if observed != expected_sha:
            raise RuntimeIntegrationError(
                "TRANSACTION_BOUND_RUNTIME_INTEGRATION_AUTHORITY_DRIFT",
                "required predecessor authority identity drifted",
                relative.as_posix(),
            )

    acceptance = json.loads(_read_required(root, V2_OUTCOME_UNKNOWN_PATH))
    if not isinstance(acceptance, dict):
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_PREDECESSOR_INVALID",
            "V2 outcome-unknown acceptance must be one object",
            V2_OUTCOME_UNKNOWN_PATH.as_posix(),
        )
    required = {
        "status": "ACCEPTED_DIAGNOSTIC_OUTCOME_UNKNOWN",
        "saved_version_id": 341548056,
        "governed_execution_outcome": "OUTCOME_UNKNOWN",
        "diagnostic_masking_established": True,
        "earliest_precleanup_exception_recovered": False,
        "symbolic_link_regression_case_required_for_successor": True,
        "runtime_incompatibility_established": False,
        "p5_failure_established": False,
        "p6_failure_established": False,
    }
    drift = tuple(
        key for key, expected_value in required.items() if acceptance.get(key) != expected_value
    )
    if drift:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_PREDECESSOR_DRIFT",
            "V2 outcome-unknown governance contract drifted",
            V2_OUTCOME_UNKNOWN_PATH.as_posix(),
        )


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_TRANSFORM_DRIFT",
            f"{label} expected one transform target; observed {count}",
            V2_TEMPLATE_PATH.as_posix(),
        )
    return source.replace(old, new)


def _replace_between(
    source: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start_count = source.count(start_marker)
    end_count = source.count(end_marker)
    if start_count != 1 or end_count != 1:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_TRANSFORM_DRIFT",
            (f"{label} marker cardinality drifted: start={start_count}, end={end_count}"),
            V2_TEMPLATE_PATH.as_posix(),
        )
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[:start] + replacement + source[end:]


def _materialize_placeholders(root: Path, source: str) -> str:
    design_sha = _sha256(_read_required(root, DESIGN_PATH))
    replacements = {
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__SOURCE_MAIN_COMMIT__": BASE_MAIN_COMMIT,
        "__IMPLEMENTATION_REVIEW_SHA256__": AUTHORIZATION_REVIEW_SHA256,
        "__DESIGN_RECORD_SHA256__": design_sha,
        "__V5_ACCEPTANCE_SHA256__": (
            "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
        ),
        "__MODEL_SNAPSHOT_SHA256__": MODEL_SNAPSHOT_SHA256,
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
    }
    for marker, value in replacements.items():
        count = source.count(marker)
        if count < 1:
            raise RuntimeIntegrationError(
                "TRANSACTION_BOUND_RUNTIME_INTEGRATION_TEMPLATE_MARKER_MISSING",
                f"required predecessor marker is missing: {marker}",
                V2_TEMPLATE_PATH.as_posix(),
            )
        source = source.replace(marker, value)

    source = _replace_once(
        source,
        'OUTPUT_ROOT = WORK_ROOT / "p5_p6_exact_runtime_requalification_v2"',
        'OUTPUT_ROOT = WORK_ROOT / "p5_p6_transaction_bound_runtime_v1"',
        "output root",
    )
    source = _replace_once(
        source,
        'SCRATCH_ROOT = WORK_ROOT / "p5_p6_exact_runtime_requalification_v2_scratch"',
        'SCRATCH_ROOT = WORK_ROOT / "p5_p6_transaction_bound_runtime_v1_scratch"',
        "scratch root",
    )
    return source


TRANSACTION_CONTEXT_FUNCTION = r"""def require_transaction_bound_context() -> dict[str, object]:
    transaction_id = globals().get("AURAGATEWAY_TRANSACTION_ID")
    if (
        not isinstance(transaction_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", transaction_id) is None
    ):
        raise DiagnosticFailure(
            "AUTHORITY_FAILURE",
            "transaction-bound wrapper admission context is missing or invalid",
        )
    return {
        "transaction_id": transaction_id,
        "authorization_transport": "EMBEDDED_WRAPPER_ADMISSION",
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "runtime_execution_authorized": True,
    }
"""


DIRECTORY_SNAPSHOT_FUNCTION = r"""def directory_snapshot(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "exists": False,
            "file_count": 0,
            "symlink_count": 0,
            "size_bytes": 0,
        }
    if not path.is_dir() or path.is_symlink():
        raise RuntimeError("target runtime path is not one real directory")
    file_count = 0
    symlink_count = 0
    size_bytes = 0
    for member in path.rglob("*"):
        if member.is_symlink():
            symlink_count += 1
            continue
        if member.is_dir():
            continue
        if not stat.S_ISREG(member.stat().st_mode):
            raise RuntimeError("target runtime contains a non-regular member")
        file_count += 1
        size_bytes += member.stat().st_size
    return {
        "exists": True,
        "file_count": file_count,
        "symlink_count": symlink_count,
        "size_bytes": size_bytes,
    }
"""


CLEANUP_AND_TEARDOWN_FUNCTIONS = r"""def cleanup_scratch() -> dict[str, object]:
    snapshot_error_type = None
    snapshot_safe_message = None
    try:
        before = directory_snapshot(SCRATCH_ROOT)
    except (OSError, RuntimeError, ValueError) as error:
        snapshot_error_type = type(error).__name__
        snapshot_safe_message = sanitize_excerpt(str(error))
        before = {
            "exists": SCRATCH_ROOT.exists(),
            "snapshot_available": False,
        }

    delete_error_type = None
    delete_safe_message = None
    try:
        if SCRATCH_ROOT.exists():
            shutil.rmtree(SCRATCH_ROOT)
    except OSError as error:
        delete_error_type = type(error).__name__
        delete_safe_message = sanitize_excerpt(str(error))

    status = (
        "PASSED"
        if (
            snapshot_error_type is None
            and delete_error_type is None
            and not SCRATCH_ROOT.exists()
        )
        else "FAILED"
    )
    report = {
        "schema_version": "1.0.0",
        "report_id": (
            "auragateway-p5-p6-exact-runtime-requalification-"
            "scratch-cleanup-v1"
        ),
        "status": status,
        "scratch_before": before,
        "scratch_exists_after": SCRATCH_ROOT.exists(),
        "snapshot_error_type": snapshot_error_type,
        "snapshot_safe_message": snapshot_safe_message,
        "delete_error_type": delete_error_type,
        "delete_safe_message": delete_safe_message,
        "secondary_failure_only": True,
    }
    try:
        write_json(OUTPUT_ROOT / "scratch_cleanup_report_v1.json", report)
        report["report_persisted"] = True
    except OSError:
        report["report_persisted"] = False
        if report["status"] == "PASSED":
            report["status"] = "FAILED"
    return report


def safe_worker_teardown(worker: Worker, reason: str) -> dict[str, object]:
    try:
        return worker.stop_and_report(reason)
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        return {
            "worker_id": worker.worker_id,
            "worker_instance_id": worker.instance_id,
            "status": "FAILED",
            "reason": reason,
            "teardown_error_type": type(error).__name__,
            "teardown_error_message": sanitize_excerpt(str(error))[:512],
            "secondary_failure_only": True,
        }
"""


def _build_runtime_payload(root: Path) -> tuple[bytes, int]:
    predecessor_bytes = _read_required(root, V2_TEMPLATE_PATH)
    source = _materialize_placeholders(root, predecessor_bytes.decode("utf-8"))

    source = _replace_once(
        source,
        ('IMPLEMENTATION_REVIEW_SHA256: Final = "' + AUTHORIZATION_REVIEW_SHA256 + '"'),
        (f'IMPLEMENTATION_REVIEW_SHA256: Final = (\n    "{AUTHORIZATION_REVIEW_SHA256}"\n)'),
        "materialized implementation review identity formatting",
    )

    source = _replace_once(
        source,
        '    worker: "Worker",',
        "    worker: Worker,",
        "Worker forward annotation",
    )

    source = _replace_once(
        source,
        "zip(left.token_ids, right.token_ids)",
        "zip(left.token_ids, right.token_ids, strict=False)",
        "explicit zip truncation semantics",
    )

    source = _replace_once(
        source,
        "        import_closure = validate_process_tree_import_closure(counters)",
        "        validate_process_tree_import_closure(counters)",
        "unused import-closure assignment",
    )

    source = _replace_between(
        source,
        "\nAUTHORIZATION_FILENAME = ",
        "\n\ndef consume_actions(",
        "\n" + TRANSACTION_CONTEXT_FUNCTION.rstrip(),
        "authorization transport removal",
    )

    source = _replace_once(
        source,
        '    elif returncode == 0:\n        process_outcome = "PASSED"',
        '    elif returncode == 0:\n        process_outcome = "ZERO_EXIT"',
        "successful bounded-process outcome",
    )
    source = _replace_once(
        source,
        ('        "status": "PASSED" if process_outcome == "PASSED" else "FAILED",'),
        ('        "status": "PASSED" if process_outcome == "ZERO_EXIT" else "FAILED",'),
        "bounded-process status mapping",
    )

    source = _replace_between(
        source,
        "def directory_snapshot(path: Path) -> dict[str, object]:",
        "\n\ndef install_failure_signals(",
        DIRECTORY_SNAPSHOT_FUNCTION.rstrip(),
        "symlink-aware scratch snapshot",
    )

    source = _replace_between(
        source,
        "def cleanup_scratch() -> dict[str, object]:",
        "\n\ndef main() -> int:",
        CLEANUP_AND_TEARDOWN_FUNCTIONS.rstrip(),
        "cleanup and teardown hardening",
    )

    source = _replace_once(
        source,
        (
            '        active_failure_code = "AUTHORITY_FAILURE"\n'
            "        authorization = require_execution_authorization()"
        ),
        (
            '        active_failure_code = "AUTHORITY_FAILURE"\n'
            "        authorization = require_transaction_bound_context()"
        ),
        "transaction-bound runtime context",
    )

    source = _replace_once(
        source,
        (
            "    finally:\n"
            "        if worker_2 is not None:\n"
            '            report = worker_2.stop_and_report("TERMINAL_FINALIZATION")\n'
            "            if report not in teardown_reports:\n"
            "                teardown_reports.append(report)\n"
            "        if worker_1 is not None:\n"
            '            report = worker_1.stop_and_report("TERMINAL_FINALIZATION")\n'
            "            if report not in teardown_reports:\n"
            "                teardown_reports.append(report)"
        ),
        (
            "    finally:\n"
            "        if worker_2 is not None:\n"
            '            report = safe_worker_teardown(worker_2, "TERMINAL_FINALIZATION")\n'
            "            if report not in teardown_reports:\n"
            "                teardown_reports.append(report)\n"
            "        if worker_1 is not None:\n"
            '            report = safe_worker_teardown(worker_1, "TERMINAL_FINALIZATION")\n'
            "            if report not in teardown_reports:\n"
            "                teardown_reports.append(report)"
        ),
        "secondary-only worker finalization",
    )

    source = _replace_once(
        source,
        (
            "    bundle = bundle_outputs()\n"
            "    terminal_payload = {**summary, **bundle}\n"
            "    print(canonical_json(terminal_payload))\n"
            "    return 0 if passed else 2"
        ),
        (
            "    try:\n"
            "        bundle = bundle_outputs()\n"
            "    except (\n"
            "        OSError,\n"
            "        RuntimeError,\n"
            "        ValueError,\n"
            "        KeyError,\n"
            "        zipfile.BadZipFile,\n"
            "    ) as error:\n"
            '        terminal_state = "FAILED_PENDING_REPOSITORY_DISPOSITION"\n'
            "        packaging_failure = {\n"
            '            "schema_version": "1.0.0",\n'
            '            "status": "FAILED",\n'
            '            "failed_after": completed,\n'
            '            "failed_capability": None,\n'
            '            "failure_class": "EVIDENCE_PROJECTION_FAILURE",\n'
            '            "detail_code": "EVIDENCE_PROJECTION_FAILURE",\n'
            '            "error_type": type(error).__name__,\n'
            '            "safe_message": sanitize_excerpt(str(error))[:512],\n'
            "        }\n"
            "        if failure is None:\n"
            "            failure = packaging_failure\n"
            "        else:\n"
            '            failure["secondary_evidence_packaging_failure"] = True\n'
            "            failure[\n"
            '                "secondary_evidence_packaging_error_type"\n'
            "            ] = type(error).__name__\n"
            '        write_json(OUTPUT_ROOT / "failure_report_v1.json", failure)\n'
            '        summary["status"] = "FAILED"\n'
            '        summary["terminal_state"] = terminal_state\n'
            '        summary["failure_class"] = failure.get("failure_class")\n'
            "        write_json(\n"
            '            OUTPUT_ROOT / "p5_p6_exact_runtime_requalification_summary_v1.json",\n'
            "            summary,\n"
            "        )\n"
            "        terminal_payload = {\n"
            "            **summary,\n"
            '            "bundle_status": "FAILED",\n'
            '            "secondary_evidence_packaging_failure": (\n'
            '                failure.get("secondary_evidence_packaging_failure", False)\n'
            "            ),\n"
            "        }\n"
            "        print(canonical_json(terminal_payload))\n"
            "        return 2\n"
            "    terminal_payload = {**summary, **bundle}\n"
            "    print(canonical_json(terminal_payload))\n"
            "    return 0 if passed else 2"
        ),
        "evidence packaging primary preservation",
    )

    source = _replace_once(
        source,
        '        return response.read().decode("utf-8")',
        ('        return response.read().decode("utf-8")  # type: ignore[no-any-return]'),
        "inherited get_text typing",
    )
    source = _replace_once(
        source,
        '        name = raw.get("path")',
        '        name = raw.get("path")  # type: ignore[assignment]',
        "inherited wheelhouse manifest typing",
    )
    source = _replace_once(
        source,
        "                chunk = source.read(8192)",
        ("                chunk = source.read(8192)  # type: ignore[attr-defined]"),
        "inherited capture read protocol typing",
    )
    source = _replace_once(
        source,
        "            source.close()",
        "            source.close()  # type: ignore[attr-defined]",
        "inherited capture close protocol typing",
    )
    source = _replace_once(
        source,
        "    return payload\n\n\ndef _path_within_target",
        ("    return payload  # type: ignore[no-any-return]\n\n\ndef _path_within_target"),
        "inherited target-runtime JSON typing",
    )
    source = _replace_once(
        source,
        ('        self.memory_before_start_mib = int(identity["memory_used_mib"])'),
        (
            "        self.memory_before_start_mib = "
            'int(identity["memory_used_mib"])'
            "  # type: ignore[call-overload]"
        ),
        "inherited worker GPU-memory typing",
    )
    source = _replace_once(
        source,
        '            return int(identity["memory_used_mib"])',
        (
            '            return int(identity["memory_used_mib"])'
            "  # type: ignore[no-any-return, call-overload]"
        ),
        "inherited GPU-memory helper typing",
    )
    source = _replace_once(
        source,
        "        p5_observations = {",
        "        p5_observations: dict[str, object] = {",
        "P5 observation dictionary typing",
    )
    source = _replace_once(
        source,
        "        packaging_failure = {",
        "        packaging_failure: dict[str, object] = {",
        "evidence packaging failure typing",
    )

    tree = ast.parse(source)
    compile(tree, RUNTIME_PAYLOAD_PATH.as_posix(), "exec")

    predecessor_tree = ast.parse(_materialize_placeholders(root, predecessor_bytes.decode("utf-8")))
    predecessor_functions = {
        node.name: node
        for node in predecessor_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    successor_functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    unexpected_removed = (
        set(predecessor_functions) - set(successor_functions) - REMOVED_AUTHORIZATION_FUNCTIONS
    )
    unexpected_added = (
        set(successor_functions) - set(predecessor_functions) - ALLOWED_ADDED_FUNCTIONS
    )
    if unexpected_removed or unexpected_added:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_FUNCTION_SET_DRIFT",
            "successor runtime function inventory drifted outside the approved seam",
        )

    compared = 0
    comparable = set(predecessor_functions) & set(successor_functions) - ALLOWED_CHANGED_FUNCTIONS
    for name in sorted(comparable):
        before = ast.dump(
            predecessor_functions[name],
            annotate_fields=True,
            include_attributes=False,
        )
        after = ast.dump(
            successor_functions[name],
            annotate_fields=True,
            include_attributes=False,
        )
        if before != after:
            raise RuntimeIntegrationError(
                "TRANSACTION_BOUND_RUNTIME_INTEGRATION_BEHAVIOR_DRIFT",
                f"unapproved predecessor runtime function changed: {name}",
            )
        compared += 1

    forbidden = (
        "ag-p5-p6-auth-control-v1",
        "ag_p5_p6_auth_control_v1",
        "execution_authorization_v1.json",
        "AUTHORIZATION_CONTROL_",
        "resolve_authorization_control_output",
        "require_execution_authorization",
    )
    if any(token in source for token in forbidden):
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_AUTH_TRANSPORT_RETAINED",
            "authorization-specific runtime transport survived successor generation",
        )

    for role in REQUEST_ROLES:
        if role not in source:
            raise RuntimeIntegrationError(
                "TRANSACTION_BOUND_RUNTIME_INTEGRATION_REQUEST_CONTRACT_DRIFT",
                f"required P5/P6 request role is missing: {role}",
            )

    required_markers = (
        'process_outcome = "ZERO_EXIT"',
        'if process_outcome == "ZERO_EXIT"',
        '"symlink_count": symlink_count',
        "safe_worker_teardown(worker_2",
        "safe_worker_teardown(worker_1",
        'failure["secondary_evidence_packaging_failure"] = True',
        "require_transaction_bound_context()",
    )
    if any(marker not in source for marker in required_markers):
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_REMEDIATION_MISSING",
            "required successor remediation marker is missing",
        )

    if 'raise RuntimeError("target runtime contains a symbolic link")' in source:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_SYMLINK_REJECTION_RETAINED",
            "scratch runtime snapshot still rejects venv symlink members",
        )

    unformatted_payload = source.encode("utf-8")
    formatted = subprocess.run(
        [
            "ruff",
            "format",
            "--stdin-filename",
            RUNTIME_PAYLOAD_PATH.as_posix(),
            "-",
        ],
        input=unformatted_payload,
        check=False,
        capture_output=True,
    )
    if formatted.returncode != 0:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_FORMATTER_FAILED",
            "Ruff could not normalize the generated runtime payload",
        )

    formatted_payload = formatted.stdout
    formatted_tree = ast.parse(formatted_payload.decode("utf-8"))

    before_format = ast.dump(
        tree,
        annotate_fields=True,
        include_attributes=False,
    )
    after_format = ast.dump(
        formatted_tree,
        annotate_fields=True,
        include_attributes=False,
    )

    if before_format != after_format:
        raise RuntimeIntegrationError(
            "TRANSACTION_BOUND_RUNTIME_INTEGRATION_FORMATTER_SEMANTIC_DRIFT",
            "runtime formatting changed the generated semantic AST",
        )

    return formatted_payload, compared


def _build_expected(root: Path) -> tuple[bytes, bytes, bytes]:
    _require_base_ancestor(root)
    _validate_authorities(root)
    runtime_payload, compared = _build_runtime_payload(root)
    review = IntegrationReview(
        review_id="auragateway-transaction-bound-p5-p6-runtime-integration-v1-review",
        status="APPROVED_FOR_TRANSACTION_BOUND_RUNTIME_INTEGRATION",
        base_main_commit=BASE_MAIN_COMMIT,
        authorization_record_sha256=AUTHORIZATION_RECORD_SHA256,
        authorization_review_sha256=AUTHORIZATION_REVIEW_SHA256,
        predecessor_v2_template_sha256=_sha256(_read_required(root, V2_TEMPLATE_PATH)),
        predecessor_outcome_unknown_sha256=V2_OUTCOME_UNKNOWN_SHA256,
        wrapper_template_sha256=_sha256(_read_required(root, WRAPPER_TEMPLATE_PATH)),
        runtime_payload_sha256=_sha256(runtime_payload),
        unchanged_behavioral_function_count=compared,
        authorization_transport_removed=True,
        six_request_contract_preserved=True,
        process_success_semantics_zero_exit=True,
        symlink_regression_covered=True,
        cleanup_failure_cannot_mask_primary=True,
        worker_teardown_failure_cannot_mask_primary=True,
        evidence_packaging_failure_cannot_mask_primary=True,
        live_authorization_issued=False,
        gpu_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    review_bytes = _canonical_bytes(review)
    record = IntegrationRecord(
        record_id="auragateway-transaction-bound-p5-p6-runtime-integration-v1",
        status="TRANSACTION_BOUND_P5_P6_RUNTIME_INTEGRATION_VALID",
        base_main_commit=BASE_MAIN_COMMIT,
        review_sha256=_sha256(review_bytes),
        runtime_payload_path=RUNTIME_PAYLOAD_PATH.as_posix(),
        runtime_payload_sha256=_sha256(runtime_payload),
        live_authorization_boundary_ready=True,
        symlink_regression_covered=True,
        authorization_specific_kaggle_inputs=0,
        authorization_producer_notebooks=0,
        manual_confirmation_json_files=0,
        primary_failure_preserved_separately=True,
        process_success_semantics_zero_exit=True,
        current_runtime_p5_p6_requalified=False,
        runtime_anti_replay_established=False,
        live_authorization_issued=False,
        gpu_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    return runtime_payload, review_bytes, _canonical_bytes(record)


def generate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)
    for relative, payload in (
        (RUNTIME_PAYLOAD_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        _write(root / relative, payload)
    return {
        "status": "TRANSACTION_BOUND_P5_P6_RUNTIME_INTEGRATION_GENERATED",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "live_authorization_boundary_ready": True,
        "live_authorization_issued": False,
        "gpu_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)
    expected = (
        (RUNTIME_PAYLOAD_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    )
    for relative, payload in expected:
        if _read_required(root, relative) != payload:
            raise RuntimeIntegrationError(
                "TRANSACTION_BOUND_RUNTIME_INTEGRATION_GENERATED_ARTIFACT_DRIFT",
                "generated runtime-integration artifact drifted",
                relative.as_posix(),
            )
    return {
        "status": "TRANSACTION_BOUND_P5_P6_RUNTIME_INTEGRATION_VALID",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "symlink_regression_covered": True,
        "primary_failure_preserved_separately": True,
        "current_runtime_p5_p6_requalified": False,
        "runtime_anti_replay_established": False,
        "live_authorization_issued": False,
        "gpu_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    root = Path(args.repo_root)
    try:
        result = generate(root) if args.command == "generate" else validate(root)
    except (RuntimeIntegrationError, ValueError, json.JSONDecodeError) as error:
        if isinstance(error, RuntimeIntegrationError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            }
        else:
            payload = {
                "error_code": ("TRANSACTION_BOUND_RUNTIME_INTEGRATION_VALIDATION_ERROR"),
                "safe_message": str(error),
                "path": None,
            }
        print(json.dumps(payload, sort_keys=True), file=__import__("sys").stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
