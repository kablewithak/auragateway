# ADR: Harden the pinned vLLM worker CLI contract

## Status

Accepted for implementation; runtime retry remains blocked.

## Context

The governed post-PR #149 qualification reached initial worker startup and
failed closed before health readiness. Both worker processes returned code 2.
The pinned vLLM 0.19.1 `api_server` rejected `--disable-log-requests` and
advertised `--no-enable-log-requests`.

The failure produced no model requests, benchmark trajectories, provider
calls, credential use, customer-data use, or external spend.

## Decision

1. Emit `--no-enable-log-requests` in the canonical worker command.
2. Before worker spawn, execute the pinned target-runtime
   `vllm.entrypoints.openai.api_server --help` boundary.
3. Extract the available long options and fail closed if any governed worker
   option is unsupported.
4. Regenerate the worker startup plan and command identities.
5. Preserve the active materialized harness as historical failed-attempt
   authority; it is not reusable for retry.
6. Block fresh authorization issuance until a post-merge source package is
   materialized, inspected, integrated, and rebound.
7. If a later attempt exposes another CLI or command-construction mismatch,
   stop per-flag remediation and redesign the complete worker CLI capability
   contract.

## Consequences

This is a Gate 2 reliability correction. It does not qualify the environment,
workers, model loading, cache metrics, cache reset, or measured A/B/C.
