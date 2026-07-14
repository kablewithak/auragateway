from __future__ import annotations

import argparse
import json
from pathlib import Path

from auragateway.publication.hugging_face import build_publication, validate_publication


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or validate the static AuraGateway Hugging Face publication package."
    )
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> None:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    manifest = (
        build_publication(repo_root) if args.command == "build" else validate_publication(repo_root)
    )
    result = {
        "command": args.command,
        "publication_id": manifest.publication_id,
        "source_main_checkpoint": manifest.source_main_checkpoint,
        "dataset_file_count": len(manifest.dataset_files),
        "space_file_count": len(manifest.space_files),
        "live_inference_included": manifest.live_inference_included,
        "credential_required": manifest.credential_required,
        "remote_publication_authorized": manifest.remote_publication_authorized,
        "next_gate": "remote_publication_authorization_review",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
