# ADR: Close AuraGateway v2 Core Scope With a Negative Provider-Telemetry Result

## Status

Accepted.

## Context

AuraGateway v2 was designed to run a controlled A/B/C benchmark only when provider cache telemetry
was sufficient to support measured cache-usage and savings claims.

Fixture-level telemetry contracts passed. The original live calibration returned successful responses
but no numeric billing cached-token samples. A later SDK compatibility review showed the installed
Groq SDK supported the nested schema. A materially different two-call reauthorization then captured
the raw HTTP body and parsed SDK object from the same response.

Both raw responses omitted `usage.prompt_tokens_details.cached_tokens`.

## Decision

Close the core runtime and evaluation-harness scope with status:

```text
closed_core_runtime_with_negative_provider_telemetry
```

Treat Gate 4 as two distinct layers:

```text
telemetry contract integrity: passed
live numeric evidence sufficiency for measured benchmark: closed unavailable
```

Do not run the measured A/B/C benchmark because its required provider-cache evidence is unavailable.

Do not authorize another identical provider execution.

Preserve the original A/B/C benchmark as historical design intent, not as completed evidence.

Create the Hugging Face publication layer as a separate, static presentation adapter consuming only
sanitized, precomputed artifacts.

## Consequences

Positive:

- unsupported cache and savings claims remain blocked;
- the negative result is retained as useful engineering evidence;
- the SDK and adapter are not changed without evidence of a defect;
- future readers can distinguish implemented runtime capability from measured benchmark outcome;
- publication concerns remain outside the runtime.

Negative:

- the original measured A/B/C outcome target is not completed;
- no numeric provider cache-savings claim is available;
- public presentation must explain the negative result clearly.

## Rejected alternatives

### Treat the missing field as zero

Rejected. Missing is not zero and does not establish a cache miss.

### Use latency alone as proof of caching

Rejected. Latency is confounded and cannot substitute for the frozen provider-cache evidence
requirement.

### Run more identical provider calls

Rejected. The one-time reauthorization was consumed and the evidence path is terminal.

### Change SDK or adapter

Rejected. The field was absent on the raw wire before SDK parsing.

### Fold Hugging Face into the runtime

Rejected. Publication is a separate static adapter and must not alter core evidence or runtime
architecture.
