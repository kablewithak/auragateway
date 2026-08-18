from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final

EXPECTED_ADR_SHA256: Final = "ebbcff62df620f4975a8b1e480ebc010ad15348a22f2ce62b69885e7ac28aa1a"
EXPECTED_V1_CORPUS_SHA256: Final = (
    "239e1d82373694d68493039a7ab39968610ea593b863d72331cd60315ef49841"
)
EXPECTED_V1_STATIC_RECEIPT_SHA256: Final = (
    "7ff91f7f7069754f5b39c29815b719792a83debd338a95c9a4626336e274de40"
)
EXPECTED_V2_CORPUS_SHA256: Final = (
    "140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9"
)
EXPECTED_REMOVED_SENTENCES: Final = (9, 29, 44, 49)
EXPECTED_PROMPT_TOKEN_COUNT: Final = 899

ADR_PATH: Final = Path(
    "docs/adr/"
    "2026-08-18-local-abc-deterministic-structurally-diverse-"
    "synthetic-prefix-construction-v1.md"
)
EVIDENCE_ROOT: Final = Path(
    "benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1"
)
V1_CORPUS_PATH: Final = EVIDENCE_ROOT / "canonical_synthetic_prefix_corpus_candidate_v1.txt"
V1_STATIC_RECEIPT_PATH: Final = EVIDENCE_ROOT / "candidate_v1_static_token_measurement.json"
V2_CORPUS_PATH: Final = EVIDENCE_ROOT / "canonical_synthetic_prefix_corpus_candidate_v2.txt"
V2_TUNING_RECEIPT_PATH: Final = EVIDENCE_ROOT / "candidate_v2_length_tuning_receipt.json"
V2_STATIC_RECEIPT_PATH: Final = EVIDENCE_ROOT / "candidate_v2_static_token_measurement.json"
HUMAN_REVIEW_PATH: Final = EVIDENCE_ROOT / "canonical_synthetic_prefix_corpus_human_review_v1.json"
FREEZE_RECORD_PATH: Final = EVIDENCE_ROOT / "canonical_synthetic_prefix_corpus_freeze_v1.json"

SYSTEM_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
ASSISTANT_ACK: Final = "Synthetic deterministic context acknowledged."
FINAL_OBJECT_CANONICAL: Final = '{"probe":"exact-runtime-p5-p6","value":1}'
MODEL_REPOSITORY: Final = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION: Final = "7ae557604adf67be50417f59c2c2f167def9a775"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class FreezeError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head_bytes(root: Path, relative: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise FreezeError(f"unable to read committed authority from HEAD: {relative.as_posix()}")
    return result.stdout


def require_committed_sha(root: Path, relative: Path, expected: str) -> None:
    observed = sha256_bytes(git_head_bytes(root, relative))
    if observed != expected:
        raise FreezeError(
            f"committed authority identity drifted: {relative.as_posix()} "
            f"expected={expected} observed={observed}"
        )


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


def object_from(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FreezeError(f"unable to read JSON authority: {path}") from error
    if not isinstance(value, dict):
        raise FreezeError(f"JSON authority is not one object: {path}")
    return value


def require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise FreezeError(f"required authority is missing or unsafe: {relative.as_posix()}")
    return path


def require_sha(root: Path, relative: Path, expected: str) -> Path:
    path = require_file(root, relative)
    observed = sha256_file(path)
    if observed != expected:
        raise FreezeError(
            f"authority identity drifted: {relative.as_posix()} "
            f"expected={expected} observed={observed}"
        )
    return path


def mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise FreezeError(f"{label} is not one object")
    return value


def sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise FreezeError(f"{label} is not one array")
    return value


def exact_false(mapping_value: dict[str, object], key: str, label: str) -> None:
    if mapping_value.get(key) is not False:
        raise FreezeError(f"{label}.{key} must remain false")


def integer_sequence(value: object, label: str) -> tuple[int, ...]:
    items = sequence(value, label)
    integers: list[int] = []
    for index, item in enumerate(items):
        if isinstance(item, bool) or not isinstance(item, int):
            raise FreezeError(f"{label}[{index}] must be an integer")
        integers.append(item)
    return tuple(integers)


def validate_v1_static(root: Path) -> dict[str, object]:
    path = require_sha(
        root,
        V1_STATIC_RECEIPT_PATH,
        EXPECTED_V1_STATIC_RECEIPT_SHA256,
    )
    payload = object_from(path)
    historical = mapping(payload.get("historical_calibration"), "V1 historical calibration")
    if historical.get("all_calibrations_passed") is not True:
        raise FreezeError("V1 historical B/D calibration is not established")

    candidate = mapping(payload.get("candidate"), "V1 candidate")
    if candidate.get("corpus_sha256") != EXPECTED_V1_CORPUS_SHA256:
        raise FreezeError("V1 static receipt corpus binding drifted")
    if candidate.get("prompt_token_count") != 985:
        raise FreezeError("V1 source prompt-token count drifted")
    if candidate.get("state") != "NEEDS_LENGTH_TUNING":
        raise FreezeError("V1 source state drifted")

    claims = mapping(payload.get("claims"), "V1 claims")
    for key in ("c4_qualified", "p5_requalified", "p6_requalified"):
        exact_false(claims, key, "V1 claims")

    boundary = mapping(payload.get("oracle_boundary"), "V1 oracle boundary")
    for key in (
        "model_loaded",
        "model_request_executed",
        "gpu_execution_performed",
        "kaggle_execution_performed",
        "runtime_execution_authorized",
    ):
        exact_false(boundary, key, "V1 oracle boundary")

    return payload


def validate_tuning(root: Path) -> tuple[dict[str, object], str]:
    path = require_file(root, V2_TUNING_RECEIPT_PATH)
    payload = object_from(path)

    source = mapping(payload.get("source"), "V2 tuning source")
    if source.get("corpus_sha256") != EXPECTED_V1_CORPUS_SHA256:
        raise FreezeError("V2 tuning source corpus identity drifted")
    if source.get("static_measurement_receipt_sha256") != EXPECTED_V1_STATIC_RECEIPT_SHA256:
        raise FreezeError("V2 tuning source receipt identity drifted")
    if source.get("prompt_token_count") != 985:
        raise FreezeError("V2 tuning source prompt-token count drifted")
    if source.get("state") != "NEEDS_LENGTH_TUNING":
        raise FreezeError("V2 tuning source state drifted")

    intervention = mapping(payload.get("intervention"), "V2 tuning intervention")
    if intervention.get("method") != "DELETION_ONLY_FULL_SENTENCE_BOUNDED_SEARCH":
        raise FreezeError("V2 tuning method drifted")
    if intervention.get("target_prompt_token_count") != EXPECTED_PROMPT_TOKEN_COUNT:
        raise FreezeError("V2 tuning target drifted")
    if intervention.get("new_text_added") is not False:
        raise FreezeError("V2 tuning added new text")
    if intervention.get("randomness_used") is not False:
        raise FreezeError("V2 tuning used randomness")

    removed = integer_sequence(
        intervention.get("removed_sentence_ordinals"),
        "V2 removed sentence ordinals",
    )
    if removed != EXPECTED_REMOVED_SENTENCES:
        raise FreezeError(
            f"V2 removed-sentence lineage drifted: expected={EXPECTED_REMOVED_SENTENCES} "
            f"observed={removed}"
        )

    candidate = mapping(payload.get("candidate_v2"), "V2 tuning candidate")
    if candidate.get("corpus_sha256") != EXPECTED_V2_CORPUS_SHA256:
        raise FreezeError("V2 tuning output corpus identity drifted")
    if candidate.get("prompt_token_count") != EXPECTED_PROMPT_TOKEN_COUNT:
        raise FreezeError("V2 tuning output prompt-token count drifted")

    claims = mapping(payload.get("claims"), "V2 tuning claims")
    if claims.get("static_length_target_met") is not True:
        raise FreezeError("V2 tuning length target is not established")
    if claims.get("representation_guardrails_revalidated") is not False:
        raise FreezeError("V2 tuning overclaims representation revalidation")
    for key in (
        "c4_qualified",
        "p5_requalified",
        "p6_requalified",
        "model_loaded",
        "model_request_executed",
        "runtime_execution_authorized",
    ):
        exact_false(claims, key, "V2 tuning claims")

    return payload, sha256_file(path)


def validate_v2_static(root: Path) -> tuple[dict[str, object], str]:
    path = require_file(root, V2_STATIC_RECEIPT_PATH)
    payload = object_from(path)

    historical = mapping(payload.get("historical_calibration"), "V2 historical calibration")
    if historical.get("all_calibrations_passed") is not True:
        raise FreezeError("V2 historical B/D calibration is not established")

    b = mapping(historical.get("B"), "V2 B calibration")
    d = mapping(historical.get("D"), "V2 D calibration")
    if b.get("calibration_passed") is not True:
        raise FreezeError("V2 B calibration failed")
    if d.get("calibration_passed") is not True:
        raise FreezeError("V2 D calibration failed")

    candidate = mapping(payload.get("candidate"), "V2 candidate")
    if candidate.get("corpus_sha256") != EXPECTED_V2_CORPUS_SHA256:
        raise FreezeError("V2 static receipt corpus identity drifted")
    if candidate.get("prompt_token_count") != EXPECTED_PROMPT_TOKEN_COUNT:
        raise FreezeError("V2 static receipt prompt-token count drifted")
    if candidate.get("target_prompt_token_count_match") is not True:
        raise FreezeError("V2 target prompt-token count is not established")
    if candidate.get("duplicate_16gram_within_guardrail") is not True:
        raise FreezeError("V2 duplicate 16-gram guardrail failed")
    if candidate.get("aligned_16_block_duplication_within_guardrail") is not True:
        raise FreezeError("V2 aligned 16-token block guardrail failed")
    if candidate.get("state") != "STATIC_REPRESENTATION_ACCEPTANCE_CANDIDATE":
        raise FreezeError("V2 static candidate state drifted")

    guardrails = mapping(payload.get("guardrails"), "V2 guardrails")
    expected_guardrails = {
        "target_prompt_token_count": 899,
        "maximum_duplicate_16gram_fraction": 0.4479638009049774,
        "maximum_duplicate_aligned_16_token_blocks_beyond_first": 15,
        "unique_token_ids_is_diagnostic_only": True,
        "shift_34_match_fraction_is_diagnostic_only": True,
    }
    for key, expected in expected_guardrails.items():
        if guardrails.get(key) != expected:
            raise FreezeError(f"V2 guardrail contract drifted: {key}")

    claims = mapping(payload.get("claims"), "V2 static claims")
    for key in ("c4_qualified", "p5_requalified", "p6_requalified"):
        exact_false(claims, key, "V2 static claims")
    if claims.get("static_representation_only") is not True:
        raise FreezeError("V2 static receipt lost its static-only boundary")

    boundary = mapping(payload.get("oracle_boundary"), "V2 oracle boundary")
    for key in (
        "model_loaded",
        "model_request_executed",
        "gpu_execution_performed",
        "kaggle_execution_performed",
        "runtime_execution_authorized",
    ):
        exact_false(boundary, key, "V2 oracle boundary")

    return payload, sha256_file(path)


def validate_corpus_bytes(root: Path) -> tuple[bytes, str]:
    require_sha(root, V1_CORPUS_PATH, EXPECTED_V1_CORPUS_SHA256)
    v2_path = require_sha(root, V2_CORPUS_PATH, EXPECTED_V2_CORPUS_SHA256)
    data = v2_path.read_bytes()

    if data.startswith(b"\xef\xbb\xbf"):
        raise FreezeError("V2 corpus contains a UTF-8 BOM")
    if b"\r" in data:
        raise FreezeError("V2 corpus contains CR bytes")
    if data.endswith(b"\n"):
        raise FreezeError("V2 corpus unexpectedly ends with a newline")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FreezeError("V2 corpus is not strict UTF-8") from error

    paragraphs = text.split("\n\n")
    if len(paragraphs) != 10:
        raise FreezeError(f"V2 paragraph count drifted: observed={len(paragraphs)}")

    forbidden_fragments = (
        '{"probe":"exact-runtime-p5-p6","value":1}',
        "return only the exact json object",
        "transaction_id",
        "authorization_id",
        "worker_id",
        "observation_ordinal",
        "request_id",
    )
    lowered = text.lower()
    for fragment in forbidden_fragments:
        if fragment in lowered:
            raise FreezeError(f"V2 corpus contains a prohibited semantic fragment: {fragment}")

    return data, text


def build_human_review(
    tuning_sha256: str,
    static_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "review_id": "auragateway-canonical-synthetic-prefix-corpus-human-review-v1",
        "status": "HUMAN_SEMANTIC_REVIEW_USER_ACCEPTED",
        "candidate": {
            "path": V2_CORPUS_PATH.as_posix(),
            "sha256": EXPECTED_V2_CORPUS_SHA256,
            "canonical_version_if_frozen": "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1",
            "prompt_token_count": EXPECTED_PROMPT_TOKEN_COUNT,
        },
        "source_evidence": {
            "architecture_adr_path": ADR_PATH.as_posix(),
            "architecture_adr_sha256": EXPECTED_ADR_SHA256,
            "v1_corpus_sha256": EXPECTED_V1_CORPUS_SHA256,
            "v1_static_measurement_sha256": EXPECTED_V1_STATIC_RECEIPT_SHA256,
            "v2_length_tuning_receipt_sha256": tuning_sha256,
            "v2_static_measurement_sha256": static_sha256,
        },
        "rubric": {
            "synthetic_content": "PASS",
            "customer_or_sensitive_data_absent": "PASS",
            "final_probe_semantic_neutrality": "PASS",
            "instruction_like_semantics_absent": "PASS",
            "control_plane_data_absent": "PASS",
            "request_specific_data_absent": "PASS",
            "naturalness_and_coherence": "PASS",
            "structural_diversity": "PASS",
            "pseudo_record_ontology_absent": "PASS",
            "numbered_section_ontology_absent": "PASS",
            "post_tuning_coherence": "PASS",
        },
        "review_notes": [
            (
                "The ten-paragraph corpus remains coherent after the deletion-only "
                "length-tuning intervention."
            ),
            (
                "The content is one continuous fictional landscape description rather "
                "than a disguised sequence of historical 24x pseudo-records."
            ),
            (
                "No final expected JSON object, output-format instruction, transaction "
                "identifier, worker identity, authorization state, timestamp, or other "
                "request-specific control-plane value is present."
            ),
            (
                "The corpus is semantically unrelated to the exact-object probe and "
                "contains no customer or sensitive payload."
            ),
        ],
        "bounded_residual": (
            "The corpus contains limited meta-descriptive statements about fictional "
            "and non-repetitive construction. These statements are non-operational and "
            "semantically unrelated to the final exact-object task. No claim is made "
            "that all construction-aware language has been eliminated."
        ),
        "user_acceptance": {
            "required": True,
            "accepted": True,
            "scope": "EXACT_CANDIDATE_V2_BYTES_ONLY",
            "accepted_sha256": EXPECTED_V2_CORPUS_SHA256,
        },
        "claims": {
            "approved_for_corpus_freeze": True,
            "c4_qualified": False,
            "p5_requalified": False,
            "p6_requalified": False,
            "production_prompt_architecture_validated": False,
            "runtime_execution_authorized": False,
        },
        "next_gate": "FREEZE_CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1",
    }


def build_freeze_record(
    tuning_payload: dict[str, object],
    tuning_sha256: str,
    static_payload: dict[str, object],
    static_sha256: str,
    human_review_sha256: str,
) -> dict[str, object]:
    static_candidate = mapping(static_payload.get("candidate"), "V2 static candidate")
    metrics = mapping(
        static_candidate.get("representation_metrics"),
        "V2 representation metrics",
    )
    tuning_candidate = mapping(tuning_payload.get("candidate_v2"), "V2 tuning candidate")

    return {
        "schema_version": "1.0.0",
        "design_id": "auragateway-canonical-synthetic-prefix-corpus-v1",
        "design_state": "FROZEN_USER_APPROVED_STATIC_ONLY",
        "canonical_corpus": {
            "version": "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1",
            "source_candidate_generation": "V2",
            "path": V2_CORPUS_PATH.as_posix(),
            "sha256": EXPECTED_V2_CORPUS_SHA256,
            "bytes": tuning_candidate.get("bytes"),
            "paragraph_count": tuning_candidate.get("paragraph_count"),
            "sentence_count": tuning_candidate.get("sentence_count"),
            "byte_mutation_after_freeze_permitted": False,
            "random_runtime_mutation_permitted": False,
            "request_specific_mutation_permitted": False,
        },
        "lineage": {
            "architecture_adr": {
                "path": ADR_PATH.as_posix(),
                "sha256": EXPECTED_ADR_SHA256,
            },
            "candidate_v1": {
                "path": V1_CORPUS_PATH.as_posix(),
                "sha256": EXPECTED_V1_CORPUS_SHA256,
                "prompt_token_count": 985,
                "state": "NEEDS_LENGTH_TUNING",
            },
            "candidate_v1_static_measurement": {
                "path": V1_STATIC_RECEIPT_PATH.as_posix(),
                "sha256": EXPECTED_V1_STATIC_RECEIPT_SHA256,
            },
            "candidate_v2_length_tuning": {
                "path": V2_TUNING_RECEIPT_PATH.as_posix(),
                "sha256": tuning_sha256,
                "method": "DELETION_ONLY_FULL_SENTENCE_BOUNDED_SEARCH",
                "removed_sentence_ordinals": list(EXPECTED_REMOVED_SENTENCES),
                "new_text_added": False,
                "randomness_used": False,
            },
            "candidate_v2_static_measurement": {
                "path": V2_STATIC_RECEIPT_PATH.as_posix(),
                "sha256": static_sha256,
            },
            "human_semantic_review": {
                "path": HUMAN_REVIEW_PATH.as_posix(),
                "sha256": human_review_sha256,
                "user_accepted": True,
            },
        },
        "rendered_request_static_contract": {
            "message_roles": ["system", "user", "assistant", "user"],
            "system_instruction": SYSTEM_INSTRUCTION,
            "cache_context_tail": SYSTEM_INSTRUCTION,
            "assistant_acknowledgement": ASSISTANT_ACK,
            "final_object_canonical": FINAL_OBJECT_CANONICAL,
            "prompt_token_count": EXPECTED_PROMPT_TOKEN_COUNT,
            "prompt_token_sha256": static_candidate.get("prompt_token_sha256"),
            "tokenization": {
                "model_repository": MODEL_REPOSITORY,
                "model_revision": MODEL_REVISION,
                "tokenizer_revision": MODEL_REVISION,
                "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
                "transformers": "5.14.1",
                "apply_chat_template": True,
                "tokenize": True,
                "add_generation_prompt": True,
                "continue_final_message": False,
                "return_dict": False,
                "candidate_tail_separator": "SINGLE_ASCII_SPACE",
            },
        },
        "static_representation": {
            "state": "STATIC_REPRESENTATION_ACCEPTANCE_CANDIDATE",
            "duplicate_16gram_fraction": metrics.get("duplicate_16gram_fraction"),
            "duplicate_aligned_16_token_blocks_beyond_first": metrics.get(
                "duplicate_aligned_16_token_blocks_beyond_first"
            ),
            "prompt_unique_token_ids": metrics.get("prompt_unique_token_ids"),
            "shift_34_match_fraction": metrics.get("shift_34_match_fraction"),
            "guardrails": {
                "maximum_duplicate_16gram_fraction": 0.4479638009049774,
                "maximum_duplicate_aligned_16_token_blocks_beyond_first": 15,
                "duplicate_16gram_pass": True,
                "aligned_16_block_duplication_pass": True,
                "prompt_unique_token_ids_diagnostic_only": True,
                "shift_34_match_fraction_diagnostic_only": True,
            },
            "historical_b_calibration": "PASS",
            "historical_d_calibration": "PASS",
            "behavioral_c4_evidence": False,
        },
        "future_causal_contract": {
            "b_and_c_must_share_canonical_corpus_identity": True,
            "b_and_c_must_share_prefix_constructor_identity": True,
            "worker_affinity_is_intended_b_to_c_intervention": True,
            "control_plane_values_must_remain_outside_semantic_prefix": True,
            "condition_a_output_contract_validity_must_be_established_separately": True,
        },
        "invalidation_matrix": {
            "corpus_byte_change": "NEW_CORPUS_VERSION_AND_NEW_QUALIFICATION_IDENTITY_REQUIRED",
            "message_role_topology_change": "NEW_C4_REQUEST_CONTRACT_REQUIRED",
            "system_instruction_change": "NEW_C4_REQUEST_CONTRACT_REQUIRED",
            "cache_context_tail_change": "NEW_C4_REQUEST_CONTRACT_REQUIRED",
            "assistant_acknowledgement_change": "NEW_C4_REQUEST_CONTRACT_REQUIRED",
            "final_probe_object_change": "NEW_C4_REQUEST_CONTRACT_REQUIRED",
            "tokenizer_revision_change": "STATIC_TOKEN_IDENTITY_REQUALIFICATION_REQUIRED",
            "chat_template_change": "STATIC_TOKEN_IDENTITY_REQUALIFICATION_REQUIRED",
            "transformers_version_change": "STATIC_TOKEN_IDENTITY_REQUALIFICATION_REQUIRED",
            "generation_contract_change": "NEW_C4_REQUEST_CONTRACT_REQUIRED",
        },
        "authorization": {
            "model_loaded": False,
            "model_request_executed": False,
            "worker_started": False,
            "gpu_execution_performed": False,
            "kaggle_execution_performed": False,
            "runtime_execution_authorized": False,
            "new_execution_authorized": False,
        },
        "qualification_state": {
            "architecture_decision": "ACCEPTED",
            "canonical_corpus": "FROZEN",
            "static_representation": "ACCEPTED_FOR_C4_DESIGN_INPUT",
            "c4_behavioral_qualification": "NOT_QUALIFIED",
            "p5": "NOT_REQUALIFIED",
            "p6": "NOT_REQUALIFIED",
            "final_measured_abc": "NOT_MEASURED",
            "production_readiness": "NOT_ESTABLISHED",
        },
        "non_claims": [
            "Exact repetition is not established as the sole or root cause.",
            "Aligned 16-token recurrence is not established as independently causal.",
            "Marker lexical novelty is not established as causal.",
            "Marker semantic novelty is not established as causal.",
            "An exact repetition threshold is not established.",
            "Context length alone is not established as causal.",
            "A prefix-cache defect is not established.",
            "Static representation acceptance does not qualify C4.",
            "P5 is not requalified.",
            "P6 is not requalified.",
            "The final North-Star A/B/C effect is not measured.",
            "Production readiness is not established.",
            "Production prompt architecture is not validated by this synthetic corpus.",
        ],
        "next_gate": "PRESERVE_AND_MERGE_CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1",
    }


def write_exact(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FreezeError(f"refusing to overwrite existing freeze artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise FreezeError(f"temporary output path already exists: {temporary}")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def check_exact(path: Path, payload: bytes) -> None:
    if not path.is_file() or path.is_symlink():
        raise FreezeError(f"freeze artifact is missing or unsafe: {path}")
    observed = path.read_bytes()
    if observed != payload:
        raise FreezeError(f"freeze artifact bytes drifted: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()

    if not root.is_dir() or root.is_symlink():
        raise FreezeError("repo root is unavailable or unsafe")

    require_committed_sha(root, ADR_PATH, EXPECTED_ADR_SHA256)
    validate_corpus_bytes(root)
    validate_v1_static(root)
    tuning_payload, tuning_sha256 = validate_tuning(root)
    static_payload, static_sha256 = validate_v2_static(root)

    human_review = build_human_review(tuning_sha256, static_sha256)
    human_bytes = canonical_bytes(human_review)
    human_sha256 = sha256_bytes(human_bytes)

    freeze_record = build_freeze_record(
        tuning_payload,
        tuning_sha256,
        static_payload,
        static_sha256,
        human_sha256,
    )
    freeze_bytes = canonical_bytes(freeze_record)
    freeze_sha256 = sha256_bytes(freeze_bytes)

    human_path = root / HUMAN_REVIEW_PATH
    freeze_path = root / FREEZE_RECORD_PATH

    if args.write:
        write_exact(human_path, human_bytes)
        write_exact(freeze_path, freeze_bytes)

    if args.check:
        check_exact(human_path, human_bytes)
        check_exact(freeze_path, freeze_bytes)

    print("CANONICAL_CORPUS_USER_ACCEPTANCE=BOUND")
    print(f"CANONICAL_CORPUS_SHA256={EXPECTED_V2_CORPUS_SHA256}")
    print(f"PROMPT_TOKEN_COUNT={EXPECTED_PROMPT_TOKEN_COUNT}")
    print(f"REMOVED_SENTENCE_ORDINALS={','.join(str(v) for v in EXPECTED_REMOVED_SENTENCES)}")
    print(f"HUMAN_REVIEW_SHA256={human_sha256}")
    print(f"FREEZE_RECORD_SHA256={freeze_sha256}")
    print("CANONICAL_CORPUS_STATE=FROZEN")
    print("C4_BEHAVIORAL_QUALIFICATION=NOT_QUALIFIED")
    print("P5=NOT_REQUALIFIED")
    print("P6=NOT_REQUALIFIED")
    print("MODEL_LOADED=false")
    print("MODEL_REQUEST_EXECUTED=false")
    print("RUNTIME_EXECUTION_AUTHORIZED=false")
    print("NEXT_GATE=PRESERVE_AND_MERGE_CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FreezeError as error:
        print(f"CANONICAL_CORPUS_FREEZE_ERROR={error}", file=sys.stderr)
        raise SystemExit(2) from None
