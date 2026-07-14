# ADR: Freeze the OpenRouter Hy3 Authentication-Failure Closeout

## Status

Accepted for the terminal capability-probe result.

## Context

The one-time OpenRouter Hy3 capability probe was executed from clean `main` after the reviewed
execution runner merged. The first cold-call attempt received one HTTP 401 response. The protected
journal classified the failure as `PROVIDER_AUTHENTICATION_FAILED`, prohibited retry, skipped the
warm call, consumed the authorization, and closed with `closed_terminal_provider_failure`.

No successful completion, generation metadata, parsed observation, or cache telemetry exists.

Post hoc local diagnostics show that the current urllib backend constructs a Bearer authorization
header and that no configured proxy was detected at diagnostic time. Those checks do not reconstruct
what the provider received and cannot prove the exact credential-level cause of the 401 response.

## Decision

Publish a separate sanitized closeout generated from the protected terminal receipt, journal, and raw
response. The closeout may publish:

- terminal outcome and attempt accounting;
- HTTP status and safe provider error fields;
- hashes and byte counts;
- the fact that no provider success or cache telemetry existed;
- explicit claims, non-claims, and residual harness gaps;
- a clearly labelled post hoc local authorization-path diagnostic.

The closeout must not publish the raw provider body, prompt bundle, session identity, API key, or any
header value.

The authorization remains consumed. No resume, rerun, pilot, or retained benchmark is permitted.

## Evidence interpretation

The permitted claim is limited to a pre-inference authentication failure. The result does not establish
Hy3 route availability, privacy-routing behavior, cache telemetry availability, cache use, latency, or
cost. It also does not establish whether credential validity, credential entry, surrounding whitespace,
header delivery, or another authentication factor caused the 401 response.

## Residual harness findings

1. Preflight and execution did not retain a protected credential fingerprint, so credential continuity
   cannot be proven.
2. Execution did not retain non-sensitive proof that the authorization header was constructed for the
   exact live request.
3. The runner checked `api_key.strip()` for non-emptiness but passed the original value to transport,
   leaving surrounding-whitespace risk unclosed.

These findings belong in future-provider-execution hardening. They do not reopen this experiment.

## Consequences

- The terminal negative result becomes inspectable and publishable without exposing protected data.
- The Groq and OpenRouter lineages remain independently immutable.
- The Hy3 A/B/C extension stops before its measurement channel was tested.
- The next project action is terminal review and continuity-document update, not another provider call.
