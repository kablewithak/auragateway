from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCE_MAIN_COMMIT: Final = "85ecc02001e934fc419f7e1801e72d0e92678678"

CANONICAL_CORPUS_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_corpus_candidate_v2.txt"
)
STATIC_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "candidate_v2_static_token_measurement.json"
)
HUMAN_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_corpus_human_review_v1.json"
)
FREEZE_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1/"
    "canonical_synthetic_prefix_corpus_freeze_v1.json"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-18-local-abc-canonical-synthetic-prefix-c4-behavioral-qualification-v1.md"
)
REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "canonical_synthetic_prefix_c4_behavioral_qualification_v1_request.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_v1_review.json"
)

EXPECTED_CORPUS_SHA256: Final = "140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"
EXPECTED_PROMPT_TOKEN_COUNT: Final = 899
EXPECTED_PROMPT_TOKEN_SHA256: Final = (
    "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
)
EXPECTED_OBJECT_CANONICAL: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
EXPECTED_OBJECT_SHA256: Final = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
SYSTEM_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class QualificationDesignError(RuntimeError):
    """Fail-closed C4 qualification-design error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise QualificationDesignError(message)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class CanonicalCorpusContract(_StrictModel):
    version: Literal["CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1"]
    path: str
    sha256: Literal["140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"]
    rendered_prompt_token_count: Literal[899]
    rendered_prompt_token_sha256: Literal[
        "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
    ]
    message_roles: tuple[
        Literal["system"],
        Literal["user"],
        Literal["assistant"],
        Literal["user"],
    ]
    system_instruction: str
    assistant_acknowledgement: str
    final_object_canonical: str
    final_object_sha256: Literal["448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"]


class GenerationContract(_StrictModel):
    temperature: Literal[0] = 0
    top_p: Literal[1] = 1
    repetition_penalty: float = Field(default=1.1, ge=1.1, le=1.1)
    seed: Literal[7] = 7
    max_tokens: Literal[32] = 32
    stream: Literal[False] = False
    response_format: Literal[None] = None
    guided_decoding: Literal[None] = None


class RuntimeContract(_StrictModel):
    python: Literal["3.12"] = "3.12"
    cuda_runtime: Literal["12.9"] = "12.9"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public: Literal["0.25.1"] = "0.25.1"
    native_extension: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    attention_backend: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    gpu_topology: Literal["T4_X2"] = "T4_X2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class ObservationContract(_StrictModel):
    case_count: Literal[1] = 1
    observation_count: Literal[3] = 3
    exact_pass_count_required: Literal[3] = 3
    fresh_worker_per_observation: Literal[True] = True
    zero_cached_prefix_baseline_required: Literal[True] = True
    one_request_per_worker: Literal[True] = True
    teardown_after_each_observation: Literal[True] = True
    hidden_retries_permitted: Literal[0] = 0
    replacement_requests_permitted: Literal[0] = 0
    threshold_relaxation_permitted: Literal[False] = False


class ExecutionBudget(_StrictModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[3] = 3
    maximum_worker_starts: Literal[3] = 3
    maximum_model_requests: Literal[3] = 3
    required_worker_teardowns: Literal[3] = 3
    maximum_output_tokens_per_request: Literal[32] = 32
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    external_network_requests_permitted: Literal[0] = 0
    hidden_retries_permitted: Literal[0] = 0
    replacement_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class AcceptanceContract(_StrictModel):
    transport_success_required: Literal[True] = True
    worker_health_required: Literal[True] = True
    response_completion_required: Literal[True] = True
    markdown_fence_forbidden: Literal[True] = True
    leading_non_whitespace_content_forbidden: Literal[True] = True
    trailing_non_whitespace_content_forbidden: Literal[True] = True
    json_root_object_required: Literal[True] = True
    exact_key_set: tuple[Literal["probe"], Literal["value"]] = ("probe", "value")
    probe_value: Literal["exact-runtime-p5-p6"] = "exact-runtime-p5-p6"
    integer_value: Literal[1] = 1
    extra_keys_forbidden: Literal[True] = True
    canonical_object_sha256: Literal[
        "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"
    ] = "448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113"


class EvidenceContract(_StrictModel):
    raw_prompt_retained: Literal[False] = False
    raw_model_output_retained: Literal[False] = False
    observation_id_required: Literal[True] = True
    request_ordinal_required: Literal[True] = True
    worker_start_receipt_required: Literal[True] = True
    zero_cache_baseline_receipt_required: Literal[True] = True
    response_sha256_required: Literal[True] = True
    response_length_required: Literal[True] = True
    finish_reason_required: Literal[True] = True
    token_usage_required: Literal[True] = True
    json_validity_required: Literal[True] = True
    json_error_coordinates_required: Literal[True] = True
    markdown_fence_detection_required: Literal[True] = True
    boundary_content_detection_required: Literal[True] = True
    parsed_key_set_required: Literal[True] = True
    exact_object_validation_required: Literal[True] = True
    canonical_object_sha256_required: Literal[True] = True
    request_error_required: Literal[True] = True
    transport_error_required: Literal[True] = True
    worker_health_after_request_required: Literal[True] = True
    teardown_status_required: Literal[True] = True


class TerminalState(_StrictModel):
    state: Literal["QUALIFIED", "NOT_QUALIFIED", "INVALID_EXECUTION"]
    condition: str


class QualificationRequest(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    qualification_id: Literal["CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"]
    source_main_commit: Literal["85ecc02001e934fc419f7e1801e72d0e92678678"]
    canonical_corpus: CanonicalCorpusContract
    generation_contract: GenerationContract
    runtime_contract: RuntimeContract
    observation_contract: ObservationContract
    execution_budget: ExecutionBudget
    acceptance_contract: AcceptanceContract
    evidence_contract: EvidenceContract
    terminal_states: tuple[TerminalState, TerminalState, TerminalState]
    prohibited_adaptations: tuple[str, ...] = Field(min_length=8)
    non_claims: tuple[str, ...] = Field(min_length=8)
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    p5_execution_authorized: Literal[False] = False
    p6_execution_authorized: Literal[False] = False
    next_gate: Literal["MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1"]

    @model_validator(mode="after")
    def validate_terminal_states(self) -> QualificationRequest:
        states = tuple(item.state for item in self.terminal_states)
        if states != ("QUALIFIED", "NOT_QUALIFIED", "INVALID_EXECUTION"):
            raise ValueError("terminal-state order drifted")
        return self


class ArchitectureReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-canonical-synthetic-prefix-c4-behavioral-qualification-v1-review"
    ]
    decision: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    source_main_commit: Literal["85ecc02001e934fc419f7e1801e72d0e92678678"]
    architecture_adr: ArtifactReceipt
    canonical_freeze_record: ArtifactReceipt
    request: ArtifactReceipt
    architecture: tuple[str, ...] = Field(min_length=10)
    rejected_alternatives: tuple[str, ...] = Field(min_length=8)
    qualification_rule: tuple[str, ...] = Field(min_length=8)
    runtime_execution_authorized: Literal[False] = False
    authorization_issuer_included: Literal[False] = False
    next_gate: Literal["MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1"]


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def receipt(path: Path, payload: bytes) -> ArtifactReceipt:
    return ArtifactReceipt(
        path=path.as_posix(),
        sha256=sha256_bytes(payload),
        size_bytes=len(payload),
    )


def mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise QualificationDesignError(f"{label} is not one object")
    return value


def sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise QualificationDesignError(f"{label} is not one array")
    return value


def json_object(payload: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QualificationDesignError(f"{label} is not valid UTF-8 JSON") from error
    return mapping(value, label)


def git_show(repo_root: Path, commit: str, path: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise QualificationDesignError(
            f"unable to read committed authority: {commit}:{path.as_posix()}"
        )
    return result.stdout


def require_source_main_ancestor(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SOURCE_MAIN_COMMIT, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise QualificationDesignError(
            "source main commit is not an ancestor of the current candidate"
        )


def source_bound_authority(repo_root: Path, path: Path) -> bytes:
    absolute = repo_root / path
    if not absolute.is_file() or absolute.is_symlink():
        raise QualificationDesignError(
            f"required authority is missing or unsafe: {path.as_posix()}"
        )
    worktree = absolute.read_bytes()
    committed = git_show(repo_root, SOURCE_MAIN_COMMIT, path)
    if worktree != committed:
        raise QualificationDesignError(
            f"source authority drifted from bound main: {path.as_posix()}"
        )
    return worktree


def validate_freeze_record(payload: dict[str, object]) -> None:
    if payload.get("design_state") != "FROZEN_USER_APPROVED_STATIC_ONLY":
        raise QualificationDesignError("canonical corpus design is not frozen")

    corpus = mapping(payload.get("canonical_corpus"), "canonical corpus")
    expected_corpus = {
        "version": "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1",
        "path": CANONICAL_CORPUS_PATH.as_posix(),
        "sha256": EXPECTED_CORPUS_SHA256,
        "bytes": 4347,
        "paragraph_count": 10,
        "sentence_count": 45,
        "source_candidate_generation": "V2",
        "byte_mutation_after_freeze_permitted": False,
        "random_runtime_mutation_permitted": False,
        "request_specific_mutation_permitted": False,
    }
    for key, expected in expected_corpus.items():
        if corpus.get(key) != expected:
            raise QualificationDesignError(f"canonical corpus contract drifted: {key}")

    qualification = mapping(payload.get("qualification_state"), "qualification state")
    expected_qualification = {
        "canonical_corpus": "FROZEN",
        "static_representation": "ACCEPTED_FOR_C4_DESIGN_INPUT",
        "c4_behavioral_qualification": "NOT_QUALIFIED",
        "p5": "NOT_REQUALIFIED",
        "p6": "NOT_REQUALIFIED",
        "final_measured_abc": "NOT_MEASURED",
        "production_readiness": "NOT_ESTABLISHED",
    }
    for key, expected in expected_qualification.items():
        if qualification.get(key) != expected:
            raise QualificationDesignError(f"qualification state drifted: {key}")

    rendered = mapping(
        payload.get("rendered_request_static_contract"),
        "rendered request static contract",
    )
    expected_rendered = {
        "prompt_token_count": EXPECTED_PROMPT_TOKEN_COUNT,
        "prompt_token_sha256": EXPECTED_PROMPT_TOKEN_SHA256,
        "system_instruction": SYSTEM_INSTRUCTION,
        "cache_context_tail": SYSTEM_INSTRUCTION,
        "assistant_acknowledgement": ASSISTANT_ACK,
        "final_object_canonical": EXPECTED_OBJECT_CANONICAL,
    }
    for key, expected in expected_rendered.items():
        if rendered.get(key) != expected:
            raise QualificationDesignError(f"rendered request contract drifted: {key}")

    roles = sequence(rendered.get("message_roles"), "message roles")
    if tuple(roles) != ("system", "user", "assistant", "user"):
        raise QualificationDesignError("message-role topology drifted")

    tokenization = mapping(rendered.get("tokenization"), "tokenization contract")
    expected_tokenization = {
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
        "tokenizer_revision": MODEL_REVISION,
        "transformers": "5.14.1",
        "apply_chat_template": True,
        "add_generation_prompt": True,
        "continue_final_message": False,
        "return_dict": False,
        "tokenize": True,
        "candidate_tail_separator": "SINGLE_ASCII_SPACE",
    }
    for key, expected in expected_tokenization.items():
        if tokenization.get(key) != expected:
            raise QualificationDesignError(f"tokenization contract drifted: {key}")

    authorization = mapping(payload.get("authorization"), "freeze authorization")
    for key, value in authorization.items():
        if value is not False:
            raise QualificationDesignError(
                f"freeze record unexpectedly authorizes execution: {key}"
            )


def validate_static_receipt(payload: dict[str, object]) -> None:
    candidate = mapping(payload.get("candidate"), "static candidate")
    expected = {
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "prompt_token_count": EXPECTED_PROMPT_TOKEN_COUNT,
        "prompt_token_sha256": EXPECTED_PROMPT_TOKEN_SHA256,
        "target_prompt_token_count_match": True,
        "duplicate_16gram_within_guardrail": True,
        "aligned_16_block_duplication_within_guardrail": True,
        "state": "STATIC_REPRESENTATION_ACCEPTANCE_CANDIDATE",
    }
    for key, value in expected.items():
        if candidate.get(key) != value:
            raise QualificationDesignError(f"static candidate drifted: {key}")


def validate_human_review(payload: dict[str, object]) -> None:
    if payload.get("status") != "HUMAN_SEMANTIC_REVIEW_USER_ACCEPTED":
        raise QualificationDesignError("human semantic review is not user accepted")
    candidate = mapping(payload.get("candidate"), "human review candidate")
    if candidate.get("sha256") != EXPECTED_CORPUS_SHA256:
        raise QualificationDesignError("human review corpus identity drifted")


def build_request() -> QualificationRequest:
    return QualificationRequest(
        qualification_id="CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1",
        source_main_commit=SOURCE_MAIN_COMMIT,
        canonical_corpus=CanonicalCorpusContract(
            version="CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1",
            path=CANONICAL_CORPUS_PATH.as_posix(),
            sha256=EXPECTED_CORPUS_SHA256,
            rendered_prompt_token_count=EXPECTED_PROMPT_TOKEN_COUNT,
            rendered_prompt_token_sha256=EXPECTED_PROMPT_TOKEN_SHA256,
            message_roles=("system", "user", "assistant", "user"),
            system_instruction=SYSTEM_INSTRUCTION,
            assistant_acknowledgement=ASSISTANT_ACK,
            final_object_canonical=EXPECTED_OBJECT_CANONICAL,
            final_object_sha256=EXPECTED_OBJECT_SHA256,
        ),
        generation_contract=GenerationContract(),
        runtime_contract=RuntimeContract(),
        observation_contract=ObservationContract(),
        execution_budget=ExecutionBudget(),
        acceptance_contract=AcceptanceContract(),
        evidence_contract=EvidenceContract(),
        terminal_states=(
            TerminalState(
                state="QUALIFIED",
                condition=(
                    "Complete interpretable evidence exists and all three independent "
                    "observations satisfy the exact-object contract."
                ),
            ),
            TerminalState(
                state="NOT_QUALIFIED",
                condition=(
                    "Complete interpretable execution exists and at least one healthy "
                    "model response violates the exact-object contract."
                ),
            ),
            TerminalState(
                state="INVALID_EXECUTION",
                condition=(
                    "Setup, authority, runtime, worker, transport, evidence-custody, "
                    "budget, teardown, or cleanup failure prevents valid qualification."
                ),
            ),
        ),
        prohibited_adaptations=(
            "Do not add schema or guided decoding.",
            "Do not relax parser or exact-object validation.",
            "Do not add hidden retries or replacement requests.",
            "Do not remove the assistant acknowledgement turn.",
            "Do not reduce or shorten canonical context.",
            "Do not restructure message roles.",
            "Do not change generation parameters.",
            "Do not replace model, revision, tokenizer, runtime, backend, or GPU topology.",
            "Do not relax the 3/3 threshold after execution begins.",
        ),
        non_claims=(
            "Three observations do not establish general model reliability.",
            "Production readiness is not established.",
            "The historical exact-repetition root cause is not established.",
            "Prefix-cache correctness is not established by C4.",
            "P5 success is not established.",
            "P6 success is not established.",
            "The final A/B/C effect is not measured.",
            "Long-run reliability is not established.",
            "A successful C4 does not establish a prefix-cache defect.",
        ),
        next_gate="MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1",
    )


def build_review(
    adr_receipt: ArtifactReceipt,
    freeze_receipt: ArtifactReceipt,
    request_receipt: ArtifactReceipt,
) -> ArchitectureReview:
    return ArchitectureReview(
        review_id=("auragateway-canonical-synthetic-prefix-c4-behavioral-qualification-v1-review"),
        decision="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        source_main_commit=SOURCE_MAIN_COMMIT,
        architecture_adr=adr_receipt,
        canonical_freeze_record=freeze_receipt,
        request=request_receipt,
        architecture=(
            "Qualify one exact full composed request rather than another diagnostic matrix.",
            (
                "Bind the request to Canonical Synthetic Prefix Corpus V1 and its "
                "frozen token identity."
            ),
            "Run exactly three independent observations.",
            "Start a fresh worker for each observation.",
            "Require a zero cached-prefix baseline before each observation.",
            "Issue exactly one model request per worker.",
            "Tear down the worker after every observation.",
            "Require three of three exact-object responses.",
            "Separate behavioral failure from invalid execution.",
            "Retain hashes and diagnostics rather than raw prompt or model output.",
            "Keep runtime authorization outside this design tranche.",
            "Keep P5 and P6 blocked until C4 is accepted.",
        ),
        rejected_alternatives=(
            "Do not run a six-case causal diagnostic matrix.",
            "Do not accept two of three observations.",
            "Do not reuse one worker across all observations.",
            "Do not retry failed observations.",
            "Do not add JSON schema or guided decoding.",
            "Do not shorten the canonical corpus.",
            "Do not change the assistant acknowledgement or message-role topology.",
            "Do not combine C4 qualification with P5 or P6 execution.",
            "Do not issue runtime authority from this design producer.",
        ),
        qualification_rule=(
            "QUALIFIED requires complete interpretable evidence.",
            "QUALIFIED requires exactly three observations.",
            "QUALIFIED requires three of three exact-object responses.",
            (
                "NOT_QUALIFIED requires interpretable execution with at least one "
                "output-contract failure."
            ),
            "INVALID_EXECUTION is reserved for invalid authority/runtime/evidence execution.",
            "No threshold relaxation is permitted post hoc.",
            "No hidden retry or replacement request is permitted.",
            "A C4 pass authorizes only the controlled-local P5/P6 successor gate.",
        ),
        next_gate="MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1",
    )


def generated_bytes(repo_root: Path) -> tuple[bytes, bytes]:
    require_source_main_ancestor(repo_root)

    corpus_bytes = source_bound_authority(repo_root, CANONICAL_CORPUS_PATH)
    if sha256_bytes(corpus_bytes) != EXPECTED_CORPUS_SHA256:
        raise QualificationDesignError("canonical corpus SHA-256 drifted")

    static_bytes = source_bound_authority(repo_root, STATIC_RECEIPT_PATH)
    human_bytes = source_bound_authority(repo_root, HUMAN_REVIEW_PATH)
    freeze_bytes = source_bound_authority(repo_root, FREEZE_RECORD_PATH)

    validate_static_receipt(json_object(static_bytes, "static receipt"))
    validate_human_review(json_object(human_bytes, "human review"))
    validate_freeze_record(json_object(freeze_bytes, "freeze record"))

    adr = repo_root / ADR_PATH
    if not adr.is_file() or adr.is_symlink():
        raise QualificationDesignError("qualification ADR is missing or unsafe")
    adr_bytes = adr.read_bytes()

    request = build_request()
    request_bytes = canonical_bytes(request.model_dump(mode="json"))

    review = build_review(
        receipt(ADR_PATH, adr_bytes),
        receipt(FREEZE_RECORD_PATH, freeze_bytes),
        receipt(REQUEST_PATH, request_bytes),
    )
    review_bytes = canonical_bytes(review.model_dump(mode="json"))
    return request_bytes, review_bytes


def write_generated(repo_root: Path) -> None:
    request_bytes, review_bytes = generated_bytes(repo_root)
    for relative, payload in (
        (REQUEST_PATH, request_bytes),
        (REVIEW_PATH, review_bytes),
    ):
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def check_generated(repo_root: Path) -> None:
    request_bytes, review_bytes = generated_bytes(repo_root)
    for relative, expected in (
        (REQUEST_PATH, request_bytes),
        (REVIEW_PATH, review_bytes),
    ):
        target = repo_root / relative
        if not target.is_file() or target.is_symlink():
            raise QualificationDesignError(
                f"generated artifact is missing or unsafe: {relative.as_posix()}"
            )
        observed = target.read_bytes()
        if observed != expected:
            raise QualificationDesignError(
                f"generated artifact bytes drifted: {relative.as_posix()}"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = _ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        repo_root = args.repo_root.resolve()
        if args.write:
            write_generated(repo_root)
        if args.check:
            check_generated(repo_root)
    except QualificationDesignError as error:
        print(
            canonical_bytes(
                {
                    "error_code": "C4_BEHAVIORAL_QUALIFICATION_DESIGN_INVALID",
                    "safe_message": str(error),
                }
            )
            .decode("utf-8")
            .strip(),
            file=sys.stderr,
        )
        return 2

    print(
        canonical_bytes(
            {
                "qualification_id": ("CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"),
                "runtime_execution_authorized": False,
                "status": "DESIGN_CONTRACT_VALID",
            }
        )
        .decode("utf-8")
        .strip()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
