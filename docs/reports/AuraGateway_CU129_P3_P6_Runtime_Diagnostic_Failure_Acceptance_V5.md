# AuraGateway CU129 P3-P6 Runtime Diagnostic Failure Acceptance V5

## Decision

Accept Kaggle saved version `340227787` as a valid governed diagnostic failure.

```text
evidence_disposition=ACCEPTED_DIAGNOSTIC_FAILURE
completed_probes=P3
failed_probe=P4
reported_failure_code=P3_P6_REQUEST_FAILED
first_divergence=P4_MODEL_RESPONSE_NOT_VALID_JSON
authorization_lifecycle=CONSUMED
authorization_reusable=false
unchanged_replay_authorized=false
measured_abc_authorized=false
```

## Established facts

- The exact governed runtime script identity passed.
- Offline installation and process-tree import closure passed.
- Qwen2.5-0.5B-Instruct revision
  `7ae557604adf67be50417f59c2c2f167def9a775` loaded.
- The exact `TRITON_ATTN` backend marker was observed.
- The chat-completion endpoint returned HTTP 200.
- Exactly one model request was counted.
- P3 passed.
- P4 failed at JSON parsing with safe message
  `model response is not valid JSON`.
- P5 and P6 were not run.
- Worker teardown and scratch cleanup passed.
- Raw prompts and raw model output were not retained.

## Layer 1 inspection

Saved version `340232886` performed no package installation, model load,
worker start, model request, or network request.

It verified:

- ten model-snapshot files and the governed model revision;
- chat-template SHA-256
  `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`;
- 176 wheel files and 15 critical-wheel receipts;
- all eight governed wheelhouse control hashes;
- model defaults including `repetition_penalty=1.1`;
- absence of `response_format` and guided JSON in the V5 request;
- the semantic difference between the V4 and V5 instructions.

## Causal classification

Primary:

`P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS`

Specific:

`V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION`

Contributing variables:

- prompt-only exact-JSON enforcement;
- inherited `repetition_penalty=1.1`;
- insufficient metadata-safe P4 failure evidence;
- online-serving reproducibility not established.

Rejected root causes:

- wheelhouse corruption;
- model-snapshot corruption;
- TRITON backend failure;
- CUDA ABI failure;
- HTTP transport failure;
- top-k filtering under temperature-zero greedy sampling.

## Evidence limitations

The exact model response is unknown. The failure evidence cannot distinguish
Markdown fences, prefacing prose, Python-style dictionaries, or truncation.
The causal classification is therefore strong but not experimentally isolated.

## Next diagnostic

Build a separate P4 output-contract diagnostic that compares:

1. V4 prompt, penalty 1.1, unconstrained.
2. V5 prompt, penalty 1.1, unconstrained.
3. V4 prompt, penalty 1.0, unconstrained.
4. V5 prompt, penalty 1.0, unconstrained.
5. V4 prompt, penalty 1.0, JSON schema.
6. V5 prompt, penalty 1.0, JSON schema.

Retain response hash, response length, finish reason, completion tokens, JSON
parser location, character classes, fence detection, and exact-object validity.
Do not retain raw model output.

## Non-claims

P4, P5, P6, measured A/B/C, deployment readiness, and production readiness
are not established.
