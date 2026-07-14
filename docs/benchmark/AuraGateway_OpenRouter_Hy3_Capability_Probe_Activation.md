# AuraGateway OpenRouter Hy3 Capability-Probe Activation

## Status

```text
active authorization created: true
protected local bundle prepared by repository artifact: false
credential accessed by repository artifact: false
network request performed by repository artifact: false
provider inference call performed: false
capability probe execution authorized: true
execution confirmation still required: true
pilot execution authorized: false
```

## Source boundary

```text
source commit:
c2b3f3ca67c5b9b40f47f6482e4ccc76ec3aac64

gateway provider:
openrouter

requested model:
tencent/hy3:free

telemetry authority:
openrouter_normalized_usage
```

The active authorization binds the merged authorization review, its integrity manifest, prompt
recipe, state-model report, transport report, generic OpenRouter contracts, adapter, and explicit-key
HTTP transport.

## Protected local preparation

The runner deterministically generates:

```text
.local/benchmark/openrouter-hy3-capability-probe-v1/prompt_bundle.json
.local/benchmark/openrouter-hy3-capability-probe-v1/preparation_receipt.json
.local/benchmark/openrouter-hy3-capability-probe-v1/journal.jsonl
.local/benchmark/openrouter-hy3-capability-probe-v1/raw_responses.jsonl
.local/benchmark/openrouter-hy3-capability-probe-v1/parsed_responses.jsonl
```

The prompt bundle contains the synthetic 53,080-byte stable prefix, two deterministic suffixes, and
one stable content-free session identity. The committed authorization binds the exact serialized
bundle hash and byte count without publishing the prompt body.

## Live preflight

The preflight checks:

```text
OPENROUTER_API_KEY is present
GET /api/v1/key returns typed metadata
per-key limit state is nonnegative or unlimited
the current model catalog contains tencent/hy3:free
protected prompt and session identities remain unchanged
no inference endpoint is called
```

A successful preflight writes only a protected receipt. It records response hashes, a key-label
hash, bounded usage metadata, route visibility, and zero inference calls.

## Runtime constitution

```text
cold probe must complete and be retained before warm probe
one stable session ID is required
manual provider order is prohibited
generation metadata is required for every successful completion
transport automatic retries are prohibited
one transient replacement is allowed per logical call
successful responses are never retried
resume is prohibited
rerun is prohibited
```

## Claims permitted by activation

- the one-time capability-probe authorization exists;
- the deterministic protected prompt bundle can be generated and verified locally;
- credential and route preflight can be performed without inference;
- the later execution must remain within the frozen state-machine limits.

## Claims blocked

- Hy3 free currently returns numeric cache telemetry;
- Hy3 free used prompt caching;
- a privacy-compatible inference request succeeded;
- Condition C improves cache retention;
- the A/B/C pilot is authorized;
- a successful preflight guarantees remaining free-model quota.

## Next gate

```text
protected_local_preparation_and_live_preflight
```

After both local preparation and live preflight pass, the next code slice may add the one-time
execution runner. It must still require the exact execution confirmation phrase before either Hy3
inference call.
