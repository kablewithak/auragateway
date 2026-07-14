# AuraGateway OpenRouter Hy3 Capability-Probe Closeout

## Terminal result

```text
terminal_outcome=closed_terminal_provider_failure
failure_stage=pre_inference_authentication
safe_error_code=PROVIDER_AUTHENTICATION_FAILED
http_status=401
attempt_count=1
provider_success_count=0
retained_success_count=0
replacement_count=0
warm_call_attempted=false
authorization_consumed=true
```

The retained provider error message was `Missing Authentication header`.

## Permitted claim

> The one-time OpenRouter Hy3 capability probe closed on its first cold-call attempt after an HTTP 401
> authentication failure; no completion, generation metadata, or cache telemetry was obtained.

## Evidence-accounting result

The harness behaved according to the frozen policy:

```text
cold attempt started
one completion HTTP response retained
failure classified as non-retryable authentication failure
no replacement attempt
no warm call
terminal receipt written
authorization consumed
```

## Non-claims

- No Hy3 model inference succeeded.
- No cache hit, miss, read, write, discount, saving, or latency result was observed.
- The result does not establish Hy3 route availability or privacy-routing behavior.
- The evidence does not establish whether credential validity, credential entry, surrounding
  whitespace, header delivery, or another authentication factor caused the 401 response.
- Post hoc local header construction does not prove what OpenRouter received.
- No A/B/C pilot or retained benchmark is authorized.
- The system is not deployed, customer-data tested, or production-ready.

## Harness finding

The run exposed a credential-continuity evidence gap. Future irreversible provider execution should
bind preflight and execution through a protected credential fingerprint, reject surrounding whitespace,
and retain non-sensitive authorization-header construction evidence. That remediation is future harness
hardening, not a basis to rerun this consumed authorization.

## Next gate

```text
terminal_review_and_continuity_update
```
