# AuraGateway Groq Cache Telemetry Reauthorization Closeout

## Executive conclusion

AuraGateway completed the authorized two-call Groq raw-wire telemetry run and observed a terminal
negative telemetry result:

```text
outcome: wire_field_absent
successful calls: 2
provider errors: 0
invalid observations: 0
raw numeric cache samples: 0
parsed numeric cache samples: 0
```

Both successful raw HTTP responses omitted:

```text
usage.prompt_tokens_details.cached_tokens
```

The same field was absent in both parsed SDK objects.

## Permitted claim

For the two successful calls bound to this execution, Groq omitted the billing cached-token field
from the raw HTTP response.

## Blocked claims

This evidence does not establish:

- universal Groq omission behaviour;
- a provider cache hit or cache miss;
- cached tokens equal to zero;
- provider cache usage;
- provider cache savings;
- a live SDK parsing defect;
- benchmark execution eligibility;
- A/B/C comparison eligibility;
- production readiness.

Missing telemetry remains unknown.

## Execution reconciliation

| Field | Result |
|---|---:|
| Planned attempts | 2 |
| Provider calls | 2 |
| Successful calls | 2 |
| Provider errors | 0 |
| Invalid observations | 0 |
| Skipped attempts | 0 |
| Planned bounded cost | 400 micro-USD |
| Installed Groq SDK | 1.5.0 |
| Raw field absences | 2 |
| Parsed field absences | 2 |

Both attempts used the exact same provider request hash:

```text
23cac23a165812ae8e9908e9d0609fb533359a30ed4386d76bcfb82e6a9d17c9
```

The cold probe ran at 0 ms and the warm probe at 10,000 ms. Both returned HTTP 200.

## Failure-boundary conclusion

The SDK is not the observed failure boundary. The required field was absent in the raw response
before parsing. The existing adapter therefore remains unchanged.

## Privacy and integrity

The public closeout binds all eight public execution assets by SHA-256.

Protected raw and parsed response bodies remain under:

```text
.local/benchmark/groq-cache-telemetry-reauthorization-v1/
```

Their contents are not committed or read by the closeout validator. Their SHA-256 identities remain
bound through the public execution manifest and closeout.

## Authorization state

```text
authorization consumed: true
rerun permitted: false
resume permitted: false
additional provider execution permitted: false
execution evidence mutation permitted: false
```

The authorization document remains historically `active`, but the execution lineage is terminal.

## Gate 4 decision

```text
status: closed_required_provider_cache_evidence_unavailable
gate_4_passed: false
negative_result_accepted: true
benchmark_execution_permitted: false
benchmark_claims_permitted: false
comparison_eligible: false
```

The negative result is accepted as valid evidence. It does not satisfy the telemetry requirement
needed to start measured A/B/C comparison.

## Engineering resolution

- retain the current adapter;
- do not upgrade the SDK for this issue;
- do not change request construction;
- do not change routing;
- do not change cache affinity;
- prohibit an identical provider rerun;
- close this provider evidence path.

## Next gate

```text
auragateway_v2_terminal_evidence_review
```

That review should consolidate the project-level result, update the governing documentation, and
separate the future Hugging Face publication layer from the closed core runtime experiment.
