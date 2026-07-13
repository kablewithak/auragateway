# AuraGateway Batch 03 Failure Autopsy

## Decision

```text
classification=verified_provider_boundary_failure
exact_external_cause=recoverability_lost
batch_03_rerun=prohibited
batch_03_resume=prohibited
batch_04_authorization=blocked
next_gate=metadata_safe_provider_failure_diagnostics
```

## Evidence inspected

The inspection bundle contained:

```text
public-evidence/authorization.json
public-evidence/runtime_policy.json
public-evidence/journal.jsonl
public-evidence/run_records.json
public-evidence/report.json
public-evidence/manifest.json
protected/protected_outputs.jsonl
protected/provider_raw_outputs.jsonl
SHA256SUMS.json
```

No likely Groq credential or HMAC environment assignment was detected in the uploaded inspection bundle.

## Trace reconstruction

### Condition A

Condition A completed four of four turns with four successful attempts.

Every output:

- reached the provider-facing adapter;
- was retained in the raw-output ledger;
- normalized through `compiler_schema_v1`;
- was retained in canonical protected output;
- passed structured-output validation;
- passed citation-scope validation.

### Conditions B and C

Conditions B and C produced the same successful behavior for turns 1 and 2:

```text
decision=clarify
missing_field=account_scope
normalization_path=compiler_schema_v1
structured_output_valid=true
citation_scope_valid=true
```

Both failed on turn 3, attempt 1.

The failed attempt fingerprints were equivalent across B and C at the transmitted prompt boundary:

```text
system_prompt_sha256=920108586c416aa130404de114d144aca3586a212fb87966db5ec01a2ed3bbcd
user_prompt_sha256=0afb78b0bdec5243e8f3cf15a9166cb670827e04df6a34ccf97700991a1e0155
static_prefix_fingerprint=f67b7fb147a9a103681e628d154996aa49daedaf781e377b44061e6e9582a6b0
prompt_byte_count=8109
model_alias=groq-gpt-oss-20b
```

The run IDs, trace IDs, logical request IDs, and route reasons differed as expected. The prompt hashes and
provider/model configuration did not.

## What the inspection disproves

The earlier refusal-normalization hypothesis is not supported.

There are eight successful provider raw-output records and eight canonical protected-output records. The
two failed turn-3 attempts have neither a raw-output record nor a canonical protected-output record.

Therefore, the failures occurred before `ContractAlignedPacedAdapter` received a usable
`ProtectedProviderOutput`. The compiler-to-terminal normalizer did not reject a retained refusal or any
other retained JSON output for these two attempts.

The failures were also not caused by:

- rate limiting;
- retry exhaustion;
- cost exhaustion;
- attempt exhaustion;
- structured-output validation after normalization;
- citation-scope validation;
- Condition C route thrashing.

## Divergence point

The inner Groq adapter emitted:

```text
provider_error_code=PROVIDER_RESPONSE_INVALID
response_certainty=definite_failure
retryable=false
```

No provider telemetry was retained for either failed call.

The current Groq adapter maps every exception not explicitly recognized as timeout, rate limit,
authentication, permission, model absence, connection failure, or provider-side 5xx availability failure
to the single `PROVIDER_RESPONSE_INVALID` code.

That fallback includes materially different possibilities such as:

- an HTTP 400 request rejection;
- an SDK response-model incompatibility;
- a provider validation error;
- another unsupported SDK exception.

The original exception class, HTTP status, whitelisted provider error type/code, and request identifier
were not retained. The exact external cause is therefore not recoverable from Batch 03.

## Smallest maintainable fix

The next implementation must add a metadata-safe provider failure diagnostic boundary before another live
authorization.

Required retained fields:

```text
schema_version
provider
model_alias
request_id_sha256
exception_family
exception_class_allowlisted
http_status_code
provider_error_type_allowlisted
provider_error_code_allowlisted
provider_error_param_allowlisted
provider_request_id_sha256
retryable
mapped_provider_error_code
```

Prohibited retained fields:

```text
raw exception message
raw provider error body
failed_generation
raw prompt
raw user content
raw retrieved document text
raw model output
headers other than a hashed request identifier
credential or secret values
```

The adapter must distinguish at least:

```text
request_rejected
response_schema_invalid
assistant_content_missing
rate_limited
authentication_failed
permission_denied
model_unavailable
connection_failed
provider_unavailable
unknown_provider_exception
```

A local append-only diagnostic file should be written under:

```text
.local/benchmark/live-development-v4/provider_failure_diagnostics.jsonl
```

The public attempt record should continue to expose only the bounded provider-neutral error code.

## Evaluation gate for the fix

Before Batch 04:

1. Add fixed fake-SDK cases for each diagnostic family.
2. Prove raw bodies and exception messages are never retained.
3. Prove provider request IDs are hashed before persistence.
4. Prove HTTP 400 is not collapsed into generic response-invalid evidence.
5. Prove malformed successful SDK payloads remain separate from request rejection.
6. Prove empty assistant content remains an ambiguous response.
7. Prove diagnostic write failure blocks execution as an ambiguous evidence failure.
8. Run full Ruff, mypy, pytest, diff, and privacy-marker gates.
9. Commit Batch 03 failed evidence before authorizing Batch 04.
10. Create a new Batch 04 authorization; never mutate or rerun Batch 03.

## Commercial translation

This is a concrete AI System Evaluation Audit finding:

> The model-facing system reported a generic invalid-response failure, but the harness had collapsed
> several distinct provider failure classes into one code and discarded the safe metadata needed for
> diagnosis.

The proof asset is not a claimed model improvement. It is the verified failed trajectory, the evidence
receipt that blocked false acceptance, and the next provider-boundary hardening gate.
