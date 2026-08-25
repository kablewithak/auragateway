"""Offline structural rehearsal for the variance-pilot V2 transaction wrapper.

This module deliberately performs no model, GPU, Kaggle, or live-authorization work.
It renders the exact committed runtime-module graph into an isolated standalone wrapper,
then executes that wrapper in a fresh Python subprocess with repository imports removed
from PYTHONPATH. The wrapper validates V2 material and module realization without
calling the transaction runtime main().
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
    "src/auragateway/local_abc/templates/"
    "measured_abc_variance_pilot_v2_transaction_bound_wrapper_v1.py.tmpl"
)
R2_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
OUTPUT_ADMISSION_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_output_admission_runtime.py"
)
STANDALONE_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_standalone_runtime_v2.py"
)
LIVE_SEMANTICS_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_live_semantics_runtime_v1.py"
)
REQUEST_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "measured_abc_variance_pilot_v2_accepted_runtime_request_adapter_v1.py"
)
TRANSACTION_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_bound_runtime_v1.py"
)

PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v2/pilot_schedule.json")
NEUTRAL_PLAN_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/neutral_worker_qualification_plan.json"
)
STRICT_RESPONSE_FORMAT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/strict_response_format.json"
)
STANDALONE_ADMISSION_SPEC_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/standalone_admission_spec.json"
)
GENERATION_CONTRACT_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/generation_contract.json"
)
LOCAL_MATERIALIZATION_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/local_materialization_manifest.json"
)
ACCEPTED_RUNTIME_INTEGRATION_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/accepted_runtime_integration_v1.json"
)
TOKENIZER_OBSERVATION_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/"
    "accepted_tokenizer_reachable_envelope_observation_v1.json"
)

ACCEPTED_EPISODES_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
RUNTIME_SELECTION_PATH: Final = Path("data/evals/episodes/runtime-v1/selection.json")
SOURCE_MANIFEST_PATH: Final = Path("data/corpus/source_manifest.json")
COMPILER_SPEC_PATH: Final = Path("data/context/compiler_spec.json")

EXPECTED_R2_RUNTIME_SHA256: Final = (
    "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
)
EXPECTED_PILOT_SCHEDULE_SHA256: Final = (
    "c6b967222626196303c42e01436dd90a492758ebff2524a98acd233345f8bc2c"
)
EXPECTED_NEUTRAL_PLAN_SHA256: Final = (
    "e5d6c5810200defec86dc2f63e1e4181bacc94cc3f8f14bc96de87cc44c5d2b5"
)
EXPECTED_RESPONSE_FORMAT_SHA256: Final = (
    "a720c25951286a1f5d0c8031c25bc9be236048c7dd1258e5b4d0cc926a6bebbd"
)
EXPECTED_ADMISSION_SPEC_SHA256: Final = (
    "63568079bc50679b70467b63130aeade5a7fd63ba4c79daef2c6db33eae04a45"
)
EXPECTED_GENERATION_CONTRACT_SHA256: Final = (
    "e31eeac243093d6bc0e4583fbe7568585412a146a8225fa9ff76b9b33d01c0fb"
)

EXPECTED_TRAJECTORY_COUNT: Final = 54
EXPECTED_PRETREATMENT_REQUEST_COUNT: Final = 24
EXPECTED_PILOT_REQUEST_COUNT: Final = 216
EXPECTED_TOTAL_MODEL_REQUESTS: Final = 240
EXPECTED_MAX_OUTPUT_TOKENS: Final = 256

NEXT_GATE: Final = "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_V1"


class WrapperRehearsalError(RuntimeError):
    """Metadata-safe offline wrapper-rehearsal failure."""

    def __init__(self, error_code: str, safe_message: str, path: Path | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_REQUIRED_FILE_MISSING",
            "required wrapper-rehearsal file is missing or unsafe",
            relative,
        )
    return path.read_bytes()


def _read_json(repo_root: Path, relative: Path) -> JsonObject:
    raw = _read_bytes(repo_root, relative)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_JSON_INVALID",
            "required wrapper-rehearsal JSON is invalid",
            relative,
        ) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_JSON_ROOT_INVALID",
            "required wrapper-rehearsal JSON root must be one object",
            relative,
        )
    return cast(JsonObject, value)


def _require_file_sha(repo_root: Path, relative: Path, expected_sha256: str) -> None:
    observed = sha256_bytes(_read_bytes(repo_root, relative))
    if observed != expected_sha256:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_IDENTITY_DRIFT",
            "required V2 artifact identity drifted",
            relative,
        )


def _validate_upstream_contracts(repo_root: Path) -> None:
    _require_file_sha(repo_root, R2_RUNTIME_PATH, EXPECTED_R2_RUNTIME_SHA256)
    _require_file_sha(repo_root, PILOT_SCHEDULE_PATH, EXPECTED_PILOT_SCHEDULE_SHA256)
    _require_file_sha(repo_root, NEUTRAL_PLAN_PATH, EXPECTED_NEUTRAL_PLAN_SHA256)
    _require_file_sha(repo_root, STRICT_RESPONSE_FORMAT_PATH, EXPECTED_RESPONSE_FORMAT_SHA256)
    _require_file_sha(repo_root, STANDALONE_ADMISSION_SPEC_PATH, EXPECTED_ADMISSION_SPEC_SHA256)
    _require_file_sha(repo_root, GENERATION_CONTRACT_PATH, EXPECTED_GENERATION_CONTRACT_SHA256)

    local_manifest = _read_json(repo_root, LOCAL_MATERIALIZATION_MANIFEST_PATH)
    if (
        local_manifest.get("maximum_total_model_requests") != EXPECTED_TOTAL_MODEL_REQUESTS
        or local_manifest.get("pretreatment_request_count") != EXPECTED_PRETREATMENT_REQUEST_COUNT
        or local_manifest.get("pilot_request_count") != EXPECTED_PILOT_REQUEST_COUNT
        or local_manifest.get("pilot_execution_authorized") is not False
        or local_manifest.get("final_measured_abc_execution_authorized") is not False
    ):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_LOCAL_MATERIALIZATION_DRIFT",
            "V2 local materialization contract drifted",
            LOCAL_MATERIALIZATION_MANIFEST_PATH,
        )

    runtime_integration = _read_json(repo_root, ACCEPTED_RUNTIME_INTEGRATION_PATH)
    request_budget = runtime_integration.get("request_budget")
    token_budget = runtime_integration.get("token_budget")
    reuse_boundary = runtime_integration.get("reuse_boundary")
    if (
        not isinstance(request_budget, dict)
        or request_budget.get("maximum_total_model_requests") != EXPECTED_TOTAL_MODEL_REQUESTS
        or request_budget.get("pretreatment_requests") != EXPECTED_PRETREATMENT_REQUEST_COUNT
        or request_budget.get("pilot_requests") != EXPECTED_PILOT_REQUEST_COUNT
        or request_budget.get("maximum_hidden_retries") != 0
        or request_budget.get("maximum_replacement_cases") != 0
        or not isinstance(token_budget, dict)
        or token_budget.get("max_output_tokens") != EXPECTED_MAX_OUTPUT_TOKENS
        or token_budget.get("runtime_budget_expression") != "prompt_tokens + 256 <= 4096"
        or not isinstance(reuse_boundary, dict)
        or reuse_boundary.get("reuse_v1_route_semantics") is not False
        or reuse_boundary.get("reuse_v1_retry_budget") is not False
        or reuse_boundary.get("reuse_v1_output_parsing") is not False
        or reuse_boundary.get("reuse_v1_output_token_budget") is not False
        or runtime_integration.get("pilot_execution_authorized") is not False
        or runtime_integration.get("new_execution_authorized") is not False
    ):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_RUNTIME_INTEGRATION_DRIFT",
            "accepted V2 runtime-integration contract drifted",
            ACCEPTED_RUNTIME_INTEGRATION_PATH,
        )

    tokenizer_observation = _read_json(repo_root, TOKENIZER_OBSERVATION_PATH)
    if (
        tokenizer_observation.get("accepted_tokenizer_surface_qualified") is not True
        or tokenizer_observation.get("history_independent_prompt_observation_complete") is not True
        or tokenizer_observation.get("observed_history_independent_request_count") != 78
        or tokenizer_observation.get("deferred_history_dependent_request_count") != 162
        or tokenizer_observation.get("all_240_future_prompt_counts_claimed") is not False
        or tokenizer_observation.get("history_dependent_prompt_counts_preobserved") is not False
        or tokenizer_observation.get("model_requests_performed") != 0
        or tokenizer_observation.get("gpu_execution_performed") is not False
        or tokenizer_observation.get("new_execution_authorized") is not False
    ):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_TOKENIZER_OBSERVATION_DRIFT",
            "accepted tokenizer observation contract drifted",
            TOKENIZER_OBSERVATION_PATH,
        )


def _selected_episode_material(
    repo_root: Path, schedule: JsonObject
) -> tuple[list[JsonObject], JsonObject]:
    cases = schedule.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_SCHEDULE_INVALID",
            "V2 schedule must contain exactly six cases",
            PILOT_SCHEDULE_PATH,
        )

    case_ids: list[str] = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_SCHEDULE_INVALID",
                "V2 schedule case row is invalid",
                PILOT_SCHEDULE_PATH,
            )
        episode_id = raw_case.get("episode_id")
        if not isinstance(episode_id, str):
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_SCHEDULE_INVALID",
                "V2 schedule episode identity is invalid",
                PILOT_SCHEDULE_PATH,
            )
        case_ids.append(episode_id)

    runtime_selection = _read_json(repo_root, RUNTIME_SELECTION_PATH)
    runtime_entries = runtime_selection.get("entries")
    if not isinstance(runtime_entries, list):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_RUNTIME_SELECTION_INVALID",
            "final runtime selection is invalid",
            RUNTIME_SELECTION_PATH,
        )
    final_runtime_ids = {
        raw.get("episode_id")
        for raw in runtime_entries
        if isinstance(raw, dict) and isinstance(raw.get("episode_id"), str)
    }
    if set(case_ids) & final_runtime_ids:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_FINAL_RUNTIME_LEAKAGE",
            "V2 rehearsal material overlaps final runtime-selected episodes",
            RUNTIME_SELECTION_PATH,
        )

    episodes_payload = _read_json(repo_root, ACCEPTED_EPISODES_PATH)
    raw_episodes = episodes_payload.get("episodes")
    if not isinstance(raw_episodes, list):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_EPISODES_INVALID",
            "accepted episode set is invalid",
            ACCEPTED_EPISODES_PATH,
        )

    episodes: list[JsonObject] = []
    required_source_ids: set[str] = set()
    for raw_episode in raw_episodes:
        if not isinstance(raw_episode, dict):
            continue
        episode_id = raw_episode.get("episode_id")
        if episode_id not in case_ids:
            continue
        if raw_episode.get("evaluation_split") != "development":
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_EPISODE_SPLIT_INVALID",
                "V2 rehearsal material may contain development episodes only",
                ACCEPTED_EPISODES_PATH,
            )
        scope = raw_episode.get("source_scope")
        if not isinstance(scope, dict):
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_EPISODES_INVALID",
                "V2 episode source scope is invalid",
                ACCEPTED_EPISODES_PATH,
            )
        source_ids = scope.get("required_source_ids")
        if not isinstance(source_ids, list) or any(
            not isinstance(item, str) for item in source_ids
        ):
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_EPISODES_INVALID",
                "V2 episode source identities are invalid",
                ACCEPTED_EPISODES_PATH,
            )
        required_source_ids.update(cast(list[str], source_ids))
        episodes.append(cast(JsonObject, raw_episode))

    if len(episodes) != 6 or {item.get("episode_id") for item in episodes} != set(case_ids):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_EPISODE_SET_INVALID",
            "V2 rehearsal episode set does not match the frozen six-case schedule",
            ACCEPTED_EPISODES_PATH,
        )

    source_manifest = _read_json(repo_root, SOURCE_MANIFEST_PATH)
    raw_artifacts = source_manifest.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_SOURCE_MANIFEST_INVALID",
            "source manifest artifact set is invalid",
            SOURCE_MANIFEST_PATH,
        )

    sources: JsonObject = {}
    for raw_artifact in raw_artifacts:
        if not isinstance(raw_artifact, dict):
            continue
        source_id = raw_artifact.get("source_id")
        if source_id not in required_source_ids:
            continue
        document_path = raw_artifact.get("document_path")
        expected_sha = raw_artifact.get("sha256")
        expected_bytes = raw_artifact.get("byte_count")
        if (
            not isinstance(source_id, str)
            or not isinstance(document_path, str)
            or not isinstance(expected_sha, str)
            or not isinstance(expected_bytes, int)
            or isinstance(expected_bytes, bool)
        ):
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_SOURCE_MANIFEST_INVALID",
                "required source manifest row is invalid",
                SOURCE_MANIFEST_PATH,
            )
        source_bytes = _read_bytes(repo_root, Path(document_path))
        if sha256_bytes(source_bytes) != expected_sha or len(source_bytes) != expected_bytes:
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_SOURCE_IDENTITY_DRIFT",
                "required V2 source-document identity drifted",
                Path(document_path),
            )
        sources[source_id] = {
            "sha256": expected_sha,
            "byte_count": expected_bytes,
            "text": source_bytes.decode("utf-8"),
        }

    if set(sources) != required_source_ids:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_SOURCE_SET_INCOMPLETE",
            "V2 rehearsal source set is incomplete",
            SOURCE_MANIFEST_PATH,
        )
    return episodes, sources


def build_transaction_material(repo_root: Path) -> JsonObject:
    """Build the exact inert V2 material consumed by transaction-runtime validation."""

    root = repo_root.resolve()
    _validate_upstream_contracts(root)

    schedule = _read_json(root, PILOT_SCHEDULE_PATH)
    neutral_plan = _read_json(root, NEUTRAL_PLAN_PATH)
    response_format = _read_json(root, STRICT_RESPONSE_FORMAT_PATH)
    admission_spec = _read_json(root, STANDALONE_ADMISSION_SPEC_PATH)
    generation_contract = _read_json(root, GENERATION_CONTRACT_PATH)
    compiler_spec = _read_json(root, COMPILER_SPEC_PATH)
    episodes, sources = _selected_episode_material(root, schedule)

    trajectories = schedule.get("trajectories")
    requests = neutral_plan.get("requests")
    if not isinstance(trajectories, list) or len(trajectories) != EXPECTED_TRAJECTORY_COUNT:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_SCHEDULE_INVALID",
            "V2 schedule must contain exactly 54 trajectories",
            PILOT_SCHEDULE_PATH,
        )
    if not isinstance(requests, list) or len(requests) != EXPECTED_PRETREATMENT_REQUEST_COUNT:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_NEUTRAL_PLAN_INVALID",
            "V2 neutral plan must contain exactly 24 requests",
            NEUTRAL_PLAN_PATH,
        )
    if generation_contract.get("max_tokens") != EXPECTED_MAX_OUTPUT_TOKENS:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_GENERATION_DRIFT",
            "V2 generation contract must remain max_tokens=256",
            GENERATION_CONTRACT_PATH,
        )

    return {
        "schema_version": "1.0.0",
        "material_id": "auragateway-variance-pilot-successor-v2-transaction-material-v1",
        "pilot_schedule": schedule,
        "neutral_worker_qualification_plan": neutral_plan,
        "strict_response_format": response_format,
        "standalone_admission_spec": admission_spec,
        "generation_contract": generation_contract,
        "compiler_spec": compiler_spec,
        "episodes": episodes,
        "sources": sources,
        "customer_data_used": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }


def _replacement_payloads(repo_root: Path, material: JsonObject) -> dict[str, str]:
    sources = {
        "__R2_RUNTIME_B64__": _read_bytes(repo_root, R2_RUNTIME_PATH),
        "__OUTPUT_ADMISSION_RUNTIME_B64__": _read_bytes(repo_root, OUTPUT_ADMISSION_RUNTIME_PATH),
        "__STANDALONE_RUNTIME_B64__": _read_bytes(repo_root, STANDALONE_RUNTIME_PATH),
        "__LIVE_SEMANTICS_RUNTIME_B64__": _read_bytes(repo_root, LIVE_SEMANTICS_RUNTIME_PATH),
        "__REQUEST_ADAPTER_B64__": _read_bytes(repo_root, REQUEST_ADAPTER_PATH),
        "__TRANSACTION_RUNTIME_B64__": _read_bytes(repo_root, TRANSACTION_RUNTIME_PATH),
        "__MATERIAL_B64__": canonical_json(material).encode("utf-8"),
    }
    replacements: dict[str, str] = {}
    for token, payload in sources.items():
        replacements[token] = base64.b64encode(payload).decode("ascii")
        replacements[token.replace("_B64__", "_SHA256__")] = sha256_bytes(payload)
    return replacements


def render_rehearsal_wrapper(repo_root: Path) -> bytes:
    """Render the exact standalone module-graph rehearsal wrapper."""

    root = repo_root.resolve()
    material = build_transaction_material(root)
    template = _read_bytes(root, WRAPPER_TEMPLATE_PATH).decode("utf-8")
    replacements = _replacement_payloads(root, material)

    rendered = template
    for token, value in replacements.items():
        if token not in rendered:
            raise WrapperRehearsalError(
                "V2_WRAPPER_REHEARSAL_TEMPLATE_TOKEN_MISSING",
                "V2 wrapper rehearsal template token is missing",
                WRAPPER_TEMPLATE_PATH,
            )
        rendered = rendered.replace(token, value)

    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
    if unresolved:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_TEMPLATE_UNRESOLVED",
            "V2 wrapper rehearsal template retained unresolved tokens",
            WRAPPER_TEMPLATE_PATH,
        )
    return rendered.encode("utf-8")


def rehearse(repo_root: Path) -> JsonObject:
    """Execute the rendered wrapper in an isolated subprocess without live execution."""

    root = repo_root.resolve()
    wrapper = render_rehearsal_wrapper(root)
    env = dict(os.environ)
    env["PYTHONPATH"] = ""
    env["PYTHONNOUSERSITE"] = "1"

    with tempfile.TemporaryDirectory(prefix="auragateway-v2-wrapper-rehearsal-") as directory:
        work = Path(directory)
        wrapper_path = work / "variance_pilot_v2_wrapper_rehearsal.py"
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
            "V2_WRAPPER_REHEARSAL_SUBPROCESS_FAILED",
            "isolated V2 wrapper structural rehearsal failed",
        )

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_OUTPUT_INVALID",
            "isolated V2 wrapper rehearsal emitted an unexpected output shape",
        )
    try:
        result = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_OUTPUT_INVALID",
            "isolated V2 wrapper rehearsal output is not valid JSON",
        ) from exc
    if not isinstance(result, dict) or any(not isinstance(key, str) for key in result):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_OUTPUT_INVALID",
            "isolated V2 wrapper rehearsal output root is invalid",
        )
    typed = cast(JsonObject, result)
    expected = {
        "status": "V2_TRANSACTION_WRAPPER_STRUCTURAL_REHEARSAL_PASS",
        "loaded_runtime_module_count": 6,
        "material_validated": True,
        "dataclass_module_identity_validated": True,
        "package_import_graph_validated": True,
        "request_budget_validated": True,
        "system_exit_zero_handled": True,
        "nonzero_system_exit_propagated": True,
        "bootstrap_failure_cleanup_validated": True,
        "live_execution_enabled": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "new_execution_authorized": False,
    }
    if any(typed.get(key) != value for key, value in expected.items()):
        raise WrapperRehearsalError(
            "V2_WRAPPER_REHEARSAL_RESULT_DRIFT",
            "isolated V2 wrapper rehearsal result drifted",
        )
    typed["rendered_wrapper_sha256"] = sha256_bytes(wrapper)
    typed["next_gate"] = NEXT_GATE
    return typed


def validate_implementation(repo_root: Path) -> JsonObject:
    """Validate the current structural rehearsal implementation and exact source graph."""

    result = rehearse(repo_root)
    return {
        "status": "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_WRAPPER_REHEARSAL_VALID",
        "rendered_wrapper_sha256": result["rendered_wrapper_sha256"],
        "loaded_runtime_module_count": result["loaded_runtime_module_count"],
        "material_validated": True,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-v2-transaction-wrapper-rehearsal-v1"
    )
    parser.add_argument("command", choices=("rehearse", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = (
            rehearse(args.repo_root)
            if args.command == "rehearse"
            else validate_implementation(args.repo_root)
        )
    except WrapperRehearsalError as exc:
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
