# AuraGateway P4 Layer 2 Causal Investigation

## Certificate

```text
LAYER_1_SAVED_VERSION_ID=340232886
FAILED_V5_SAVED_VERSION_ID=340227787
STATUS=COMPLETED
PRIMARY_CLASSIFICATION=P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS
SPECIFIC_CLASSIFICATION=V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION
MODEL_SNAPSHOT_CORRUPTION=REJECTED
WHEELHOUSE_CORRUPTION=REJECTED
TOP_K_PRIMARY_CAUSE=REJECTED
REPETITION_PENALTY=LIVE_CONFOUNDER
UNCHANGED_REPLAY_AUTHORIZED=false
MEASURED_ABC_AUTHORIZED=false
NEXT_GATE=PRESERVE_AND_ACCEPT_P3_P6_RUNTIME_DIAGNOSTIC_FAILURE_V5
```

## Evidence integrity

- Layer 1 ZIP SHA-256: `2f302488aff12ec25cbc55384bf53e8d3d558681b4c79c76fd9dad6ff2d593fa`
- Layer 1 manifest: valid, seven members
- V5 failure intake SHA-256: `8d4dc64cc29a3aa9f0e5a9f2d222b38009b290569f4fde6d98e602a9b15ca4de`
- V5 evidence ZIP SHA-256: `e7b483196e0f017e0f0bb29562f8f1422951129fda785c89da055c374a31c328`
- V5 terminal log SHA-256: `ed3b5159666b1551ccde5213fa96f0892dca3879f6b215e6664993f049d7ed79`
- Authorization lifecycle: consumed, non-reusable

## Controlled-artifact conclusion

V4 and V5 bind the same model-snapshot authority and the same wheelhouse
authority. Layer 1 independently verified all eight wheelhouse controls, 176
wheels, and 15 critical wheel receipts. The mounted Qwen weight hash is:

`fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`

This matches the official Qwen artifact.

Therefore model corruption, wheelhouse corruption, ABI closure, installation,
TRITON realization, and transport are not credible root causes.

## Corrected sampling analysis

The mounted model generation defaults are:

```json
{
  "do_sample": true,
  "temperature": 0.7,
  "top_p": 0.8,
  "top_k": 20,
  "repetition_penalty": 1.1
}
```

The request explicitly set `temperature=0` and `top_p=1`.

Under vLLM 0.19.1, temperature zero switches to greedy sampling and neutralizes
top-k/top-p filtering. `top_k=20` is therefore not a credible primary cause.

The inherited `repetition_penalty=1.1` remains active. vLLM applies repetition
penalties before greedy token selection. This matters because P4 asks the model
to copy JSON tokens already present in the prompt.

## Ranked causal findings

| Rank | Hypothesis | Decision |
|---|---|---|
| 1 | V5 prompt semantic regression | High confidence |
| 2 | Prompt-only exact JSON contract | High-confidence design defect |
| 3 | Inherited repetition penalty interacting with copy task | Medium-high |
| 4 | Markdown/prose/truncation response | Medium, unobservable |
| 5 | Online vLLM numerical/scheduling variation | Low-medium |
| 6 | Model or wheelhouse corruption | Rejected |
| 7 | Top-k filtering under temperature zero | Rejected |

## Primary causal chain

```text
V4 explicit no-markdown/no-extra-text instruction
→ changed in V5 to conditional "For structured probes"
→ ordinary unconstrained chat generation
→ inherited repetition penalty discouraging prompt-token copying
→ non-JSON response
→ json.loads failure
→ insufficient metadata to distinguish fences, prose, invalid syntax, or truncation
```

## Why this is not yet experimental proof

There is one V4 pass and one V5 failure. The prompt change is the strongest
direct difference, but the exact failed output was not retained. The conclusion
is therefore a high-confidence causal classification, not a measured
counterfactual.

## Required next diagnostic

Build `P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1` with six cases:

1. V4 prompt, penalty 1.1, unconstrained.
2. V5 prompt, penalty 1.1, unconstrained.
3. V4 prompt, penalty 1.0, unconstrained.
4. V5 prompt, penalty 1.0, unconstrained.
5. V4 prompt, penalty 1.0, JSON schema.
6. V5 prompt, penalty 1.0, JSON schema.

Every case must retain metadata-safe failure evidence without retaining raw
model output.

## Immediate workflow gate

Before building that diagnostic, preserve and merge acceptance of saved version
`340227787` as a valid governed V5 diagnostic failure. No unchanged replay is
authorized.
