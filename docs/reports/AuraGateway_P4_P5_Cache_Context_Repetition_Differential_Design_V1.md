# AuraGateway P4/P5 Cache-Context Repetition Differential Design V1

## Purpose

Freeze the smallest current-runtime counterfactual for determining whether the
long/repeated cache-context condition represented by 24 repetitions is necessary,
relative to a 1-repetition control, for reproducing the C3 output-contract
regression.

## Variable

`CACHE_CONTEXT_REPETITION_COUNT`

Control: `1`

Treatment: `24`

## Frozen composition

Both conditions preserve prefix variant A, `system,user,assistant,user`, the
accepted V4 instruction and cache-context tail, the exact assistant
acknowledgement, final canonical JSON object, current runtime/model/tokenizer
identities, TRITON_ATTN, prefix caching, block size 16, max-model-len 4096,
temperature 0, top_p 1, repetition penalty 1.1, seed 7, max_tokens 32, stream
false, unconstrained output, parser semantics, zero hidden retries, and no schema
or guided decoding.

## Starting-state contract

Every observation uses a fresh worker process and requires a zero cached-prefix
baseline. Teardown is mandatory between observations. Historical reset evidence
is design precedent only.

## Request plan

`CONTROL_1X, TREATMENT_24X, TREATMENT_24X, CONTROL_1X, CONTROL_1X, TREATMENT_24X`

Three observations per condition.

Future ceiling: six model requests, six worker starts, six model loads, zero
hidden retries, zero replacement workers, zero benchmark trajectory requests,
and zero external network requests.

## Historical 24x identity

Prefix variant: A

Token count: 899

Token SHA-256:
`6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`

Payload SHA-256:
`b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e`

All three treatment observations must match this identity. The three 1x
observations must be internally identical and different from the treatment.

## Decision contract

- 1x 3/3, 24x 0/3: `LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED`
- 1x 0/3, 24x 0/3: `REPETITION_NOT_NECESSARY`
- 1x 3/3, 24x 3/3: `REGRESSION_NOT_REPRODUCED`
- unstable 1x: `CONTROL_NOT_RELIABLE`
- stable 1x 3/3 with mixed 24x: `NON_DETERMINISTIC_OR_AMBIGUOUS`
- required infrastructure/evidence invariant failure: `DIAGNOSTIC_INVALID`

## Non-claims

No threshold, sole context-length cause, prefix-cache defect, assistant/topology
cause, current P5/P6 qualification, measured A/B/C effect, runtime execution
authority, or production readiness is established.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1`
