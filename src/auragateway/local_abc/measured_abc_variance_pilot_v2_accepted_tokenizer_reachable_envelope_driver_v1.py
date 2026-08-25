"""Tokenizer-only driver for the V2 accepted reachable-envelope observation."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

EXPECTED_TRANSFORMERS_VERSION = "5.14.1"
EXPECTED_TOKENIZER_CLASS = "Qwen2Tokenizer"
EXPECTED_CHAT_TEMPLATE_SHA256 = "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
EXPECTED_TOKENIZER_FILE_SHA256 = {
    "tokenizer.json": "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    "tokenizer_config.json": "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _normalize_ids(value: Any) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list):
        raise TypeError(f"unexpected token-id container: {type(value).__name__}")
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        raise TypeError("token-id container contains non-integer values")
    return value


def _require_snapshot_identity(snapshot: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for name, expected_sha in EXPECTED_TOKENIZER_FILE_SHA256.items():
        path = snapshot / name
        if not path.is_file():
            raise RuntimeError(f"required tokenizer file missing: {name}")
        observed_sha = _sha256_bytes(path.read_bytes())
        if observed_sha != expected_sha:
            raise RuntimeError(f"tokenizer file identity mismatch: {name}")
        observed[name] = observed_sha
    return observed


def _extract_direct_ids(direct: object) -> list[int]:
    if not hasattr(direct, "keys"):
        raise TypeError(f"direct result is not mapping-like: {type(direct).__name__}")
    if "input_ids" not in direct:  # type: ignore[operator]
        raise KeyError("direct result has no input_ids field")
    return _normalize_ids(direct["input_ids"])  # type: ignore[index]


def observe(snapshot: Path, raw_request: object) -> dict[str, object]:
    if not isinstance(raw_request, dict):
        raise TypeError("observation request root must be an object")
    rows = raw_request.get("rows")
    if not isinstance(rows, list):
        raise TypeError("observation request rows must be a list")

    transformers = importlib.import_module("transformers")
    version = getattr(transformers, "__version__", None)
    if version != EXPECTED_TRANSFORMERS_VERSION:
        raise RuntimeError("accepted transformers version mismatch")

    file_hashes = _require_snapshot_identity(snapshot)
    auto_tokenizer = transformers.AutoTokenizer
    tokenizer = auto_tokenizer.from_pretrained(snapshot, local_files_only=True)
    tokenizer_class = tokenizer.__class__.__name__
    if tokenizer_class != EXPECTED_TOKENIZER_CLASS:
        raise RuntimeError("accepted tokenizer class mismatch")
    chat_template = tokenizer.chat_template
    if not isinstance(chat_template, str):
        raise RuntimeError("accepted chat template is not a string")
    chat_template_sha = _sha256_text(chat_template)
    if chat_template_sha != EXPECTED_CHAT_TEMPLATE_SHA256:
        raise RuntimeError("accepted chat-template identity mismatch")

    observed_rows: list[dict[str, object]] = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise TypeError("observation request row must be an object")
        messages = raw_row.get("messages")
        if not isinstance(messages, list):
            raise TypeError("observation request messages must be a list")

        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        if not isinstance(rendered, str):
            raise TypeError("rendered chat template must be text")
        direct = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
        )
        direct_ids = _extract_direct_ids(direct)
        rendered_encoding = tokenizer(rendered, add_special_tokens=False)
        rendered_ids = _normalize_ids(rendered_encoding["input_ids"])
        if direct_ids != rendered_ids:
            raise RuntimeError("direct and rendered token IDs disagree")

        observed_rows.append(
            {
                "sequence_index": raw_row.get("sequence_index"),
                "request_id": raw_row.get("request_id"),
                "messages_sha256": raw_row.get("messages_sha256"),
                "rendered_prompt_sha256": _sha256_text(rendered),
                "prompt_token_count": len(direct_ids),
                "token_id_parity": True,
            }
        )

    return {
        "schema_version": "1.0.0",
        "transformers_version": version,
        "tokenizer_class": tokenizer_class,
        "chat_template_sha256": chat_template_sha,
        "tokenizer_file_sha256": file_hashes,
        "local_files_only": True,
        "model_loaded": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "external_network_requests_performed": 0,
        "rows": observed_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    try:
        request = json.loads(input())
        result = observe(args.snapshot.resolve(), request)
    except (ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(
            _canonical_json(
                {
                    "status": "ERROR",
                    "error_type": type(exc).__name__,
                    "safe_message": str(exc),
                }
            )
        )
        return 1
    print(_canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
