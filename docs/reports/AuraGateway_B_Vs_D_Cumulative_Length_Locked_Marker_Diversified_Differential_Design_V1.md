# AuraGateway B-vs-D Cumulative-Length-Locked Marker-Diversified Differential Design V1

## Purpose

Freeze the smallest successor experiment that reduces B's exact lexical/token
repetition while preserving its sentence template and complete cumulative
prompt-token count trajectory.

## Accepted causal state

The prior governed 899-token diagnostic produced:

- A original repeated anchor: 0/3 exact-object;
- B neutral repeated: 0/3 exact-object;
- C neutral diverse: 3/3 exact-object.

Accepted classification:

`HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED`

This does not establish exact repetition as the sole or root cause.

## Conditions

### B — failure anchor

`B_NEUTRAL_REPEATED_24X`

- 899 prompt tokens;
- token SHA-256:
  `02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68`;
- request payload SHA-256:
  `1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb`;
- one neutral marker, `meadow`, repeated across all 24 segments;
- historical exact-object result: 0/3.

### D — intervention

`D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED`

- 899 prompt tokens;
- token SHA-256:
  `878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21`;
- request payload SHA-256:
  `0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010`;
- exact B sentence template;
- 24 reviewed neutral marker nouns;
- 24 unique segments;
- complete B cumulative prompt-token count profile preserved.

Markers:

`birch, grove, juniper, lagoon, meadow, prairie, spruce, umber, willow, acorn,
alder, beech, brook, caper, clover, cove, dune, finch, flint, glade, ivy,
larch, lily, orchid`

D has not been executed.

## Offline representational comparison

The corrected tokenizer analysis does not assume text joins are token boundaries.

Measured full-prompt properties:

- B duplicate 16-gram fraction: approximately 0.874434;
- D duplicate 16-gram fraction: approximately 0.447964;
- B 34-token shift-match fraction: approximately 0.904046;
- D 34-token shift-match fraction: approximately 0.852023;
- B duplicate aligned 16-token blocks beyond first: 33;
- D duplicate aligned 16-token blocks beyond first: 15;
- B prompt unique token IDs: 67;
- D prompt unique token IDs: 110.

Marker lexical/semantic novelty remains bounded rather than eliminated.

## Frozen composition

The predecessor runtime/model/generation/composition contract remains frozen:
Qwen/Qwen2.5-0.5B-Instruct at the bound revision, TRITON_ATTN, prefix caching
enabled, block size 16, max model length 4096, the four-message topology,
identical system instruction, context tail, assistant acknowledgement, final
canonical JSON object, temperature 0, top_p 1, repetition penalty 1.1, seed 7,
max_tokens 32, stream false, and unconstrained output.

## Starting state

Every observation requires a fresh worker process and a zero cached-prefix
baseline. Cross-observation cache carry-over is prohibited. Teardown is required
between observations.

## Request plan

`B, D, D, B, B, D`

Three observations per condition.

Future ceiling:

- six model requests;
- six model loads;
- six worker starts;
- zero hidden retries;
- zero replacement observations;
- zero benchmark trajectory requests;
- zero external network requests during governed requests;
- zero spend.

## Primary endpoint

`exact_object`

B must reproduce `0_OF_3_EXACT_OBJECT_TRUE` before D receives mechanistic
interpretation.

## Predeclared outcomes

- B 0/3, D 3/3:
  `MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK`
- B 0/3, D 0/3:
  `MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL`
- B 0/3, D mixed:
  `D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM`
- B not 0/3:
  `B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE`
- infrastructure/evidence invariant failure:
  `DIAGNOSTIC_INVALID`

## Non-claims

The design does not establish exact root cause, exact repetition threshold,
exact-repetition sole causality, aligned-block causality, elimination of marker
novelty, a prefix-cache defect, P5/P6 requalification, a North-Star measured
A/B/C effect, or production readiness.

No model, worker, GPU, Kaggle, or runtime execution is authorized.

## Next gate

`IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1`
