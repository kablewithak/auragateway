# ADR: One-Time OpenRouter Hy3 Capability-Probe Execution Boundary

## Status

Accepted for implementation. Inactive at rest. No live provider call is performed by this change.

## Context

The active authorization permits one bounded cold/warm Hy3 capability probe after protected prompt
preparation and metadata-only preflight. Historical OpenRouter adapter, transport, activation, and
authorization-review files are hash-bound evidence and must remain unchanged.

The irreversible execution must preserve:

```text
cold before warm
same protected stable prefix
same protected session identity
maximum four inference attempts
maximum one transient replacement per logical call
no retry after a successful completion
raw response retention before typed interpretation
exact output acknowledgements
no resume
no rerun
local-only authorization consumption
```

The historical finite-state model treated a positive cache observation on either call as abstract
positive cache use. Execution uses a stricter operational rule:

```text
cold cache_write_tokens > 0
or
warm cached_tokens > 0
```

A positive cold cached-token read remains evidence that a numeric measurement channel exists, but it
is classified as cold-state contamination and cannot alone permit promotion.

## Decision

Add an execution-specific contract, a recording OpenRouter transport, and a one-time runner without
editing the hash-bound adapter or HTTP transport.

The recording layer wraps the existing HTTP transport backend and persists one protected JSONL record
for every returned HTTP response:

```text
completion response
generation metadata response
```

The full decoded JSON value is retained under `.local`. Invalid JSON is retained as UTF-8 or base64.
Public release remains prohibited.

The runner:

1. validates the additive execution manifest;
2. validates the historical activation boundary;
3. verifies the protected prompt and preflight receipts;
4. requires clean `main` for live execution;
5. requires the exact confirmation phrase;
6. loads the key only from `OPENROUTER_API_KEY`;
7. journals before each inference attempt;
8. executes cold before warm;
9. permits one replacement only after a transient completion failure before success;
10. records raw HTTP responses before the existing adapter parses them;
11. validates `output.strip()` against the exact expected acknowledgement;
12. retains typed parsed observations;
13. evaluates route consistency and the stricter promotion rule;
14. writes one protected terminal receipt that consumes authorization locally;
15. refuses resume and rerun.

The committed authorization remains immutable. Effective runtime state is:

```text
committed authorization grant
+
protected local terminal overlay
```

## Interruption semantics

An incomplete non-empty journal with no terminal receipt is not resumable. A later `execute` or
`close-interrupted` invocation performs zero provider calls and writes:

```text
closed_interrupted_execution
```

This is distinct from an invalid provider observation.

## Consequences

### Positive

- Historical evidence hashes remain valid.
- Provider responses are retained before typed interpretation.
- Transient retries cannot occur after a successful completion.
- Exact task validity is deterministic.
- Cold-state contamination cannot manufacture promotion.
- Process interruption has a typed, terminal, zero-network recovery path.
- Authorization consumption is inspectable without mutating Git evidence.

### Negative

- The protected raw file contains complete provider response bodies and requires strict local handling.
- A hard process interruption permanently closes the one-time path rather than resuming.
- The execution runner is provider-specific at the harness edge, although the existing adapter remains
  generic for OpenRouter models.

## Publication boundary

Live execution occurs only after this implementation merges to clean `main`. Raw and parsed evidence
remain under `.local`. A later closeout PR may publish only sanitized hashes, numeric telemetry,
observation states, route identities, attempt accounting, terminal outcome, claims, and non-claims.
