# ADR: Close Groq Raw-Wire Cache Telemetry as Unavailable

## Status

Accepted.

## Decision

Close the Groq raw-wire cache-telemetry evidence path with terminal status:

```text
closed_provider_wire_field_unavailable
```

The two-call reauthorization completed successfully. Both raw HTTP responses and both parsed
SDK objects omitted `usage.prompt_tokens_details.cached_tokens`.

The closeout permits only the bounded conclusion that the field was absent on the wire for the
two observed calls. It does not convert absence to zero, infer a cache miss, infer cache usage,
or generalize the omission to all Groq responses.

## Evidence

The closeout binds the complete public execution set:

- authorization;
- runtime policy;
- activation report;
- activation manifest;
- write-through journal;
- run records;
- execution report;
- execution manifest.

Protected raw and parsed response files remain under `.local`. The closeout preserves only their
SHA-256 identities and does not read or commit their contents.

## Consequences

- The one-time authorization is consumed.
- Rerun and resume remain prohibited.
- No identical provider execution is justified.
- The existing adapter is retained.
- No SDK upgrade is selected.
- No request, routing, or cache-affinity change is selected.
- Provider cache usage and savings claims remain blocked.
- Gate 4 does not pass because required numeric provider cache evidence is unavailable.
- Benchmark execution and A/B/C comparison remain ineligible.
- The next gate is `auragateway_v2_terminal_evidence_review`.

## Alternatives rejected

### Treat the missing field as zero

Rejected. Field absence is unknown, not a measured zero.

### Treat the result as a cache miss

Rejected. The provider did not expose a cache-hit or cache-miss signal.

### Blame SDK parsing

Rejected. The field was absent in the raw provider body before SDK parsing.

### Repeat the same provider run

Rejected. The observation boundary is exhausted and another identical run has low information
gain while weakening one-time authorization discipline.

### Modify the adapter

Rejected. The adapter preserved the raw/parsed absence correctly and no extraction defect was
observed.
