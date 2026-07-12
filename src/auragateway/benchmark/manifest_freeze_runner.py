"""Validate, probe, freeze, and verify AuraGateway execution-manifest evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from auragateway.benchmark.manifest_freeze import (
    ExecutionFreezeError,
    freeze_execution_manifest,
    probe_provider,
    validate_static_assets,
    verify_frozen_assets,
)


class ExecutionFreezeErrorEnvelope(BaseModel):
    """Safe CLI error without prompts, payloads, credentials, or provider output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate", "probe-provider", "freeze", "verify"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--implementation-git-sha")
    parser.add_argument("--approved-cost-budget-usd")
    return parser.parse_args(argv)


def _minor_units(value: str | None) -> int:
    if value is None:
        raise ExecutionFreezeError(
            "COST_BUDGET_NOT_DECLARED",
            "freeze requires --approved-cost-budget-usd.",
        )
    try:
        amount = float(value)
    except ValueError as exc:
        raise ExecutionFreezeError(
            "COST_BUDGET_NOT_DECLARED",
            "The approved cost budget must be a decimal USD value.",
        ) from exc
    minor_units = round(amount * 100)
    if amount <= 0 or abs((minor_units / 100) - amount) > 1e-9:
        raise ExecutionFreezeError(
            "COST_BUDGET_NOT_DECLARED",
            "The approved cost budget must be positive with at most two decimals.",
        )
    return minor_units


def main(argv: list[str] | None = None) -> int:
    """Run one bounded execution-freeze command."""

    args = _parse_args(argv)
    try:
        if args.command == "validate":
            summary = validate_static_assets(args.repo_root)
        elif args.command == "probe-provider":
            summary = probe_provider(args.repo_root)
        elif args.command == "freeze":
            if args.implementation_git_sha is None:
                raise ExecutionFreezeError(
                    "IMPLEMENTATION_GIT_SHA_INVALID",
                    "freeze requires --implementation-git-sha.",
                )
            summary = freeze_execution_manifest(
                repo_root=args.repo_root,
                implementation_git_sha=args.implementation_git_sha,
                approved_cost_budget_minor_units=_minor_units(args.approved_cost_budget_usd),
            )
        else:
            summary = verify_frozen_assets(args.repo_root)
    except ExecutionFreezeError as exc:
        envelope = ExecutionFreezeErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
