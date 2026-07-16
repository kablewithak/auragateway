# AuraGateway Schema-Constrained Quality Cache Canary Authorization v1

## Decision

The one-request schema-constrained output capability probe passed.

This slice authorizes one new bounded canary:

- three condition-C trajectories;
- six schema-constrained chat-completion requests;
- worker 1 to worker 1 for both turns;
- full worker restart before each trajectory;
- 100% deterministic output-quality pass rate;
- cold turn one;
- positive cached-prefix tokens on turn two;
- zero trajectory failures;
- no retries or replacement trajectories.

The full 72-trajectory measured benchmark remains unauthorized.

## Successful probe evidence

- Archive SHA-256:
  `ae5e37e3d2bdf91c3644b268a792f6215d4de456055be5fd5bea4a50424f73e2`
- Canonical report SHA-256:
  `d7c8697b02494d3bef46d957167944ea20b32a03db466c98788a050cb869fff8`
- Result SHA-256:
  `440957fbc2d4fa2bc29c6e2ea981749adb36605b564b590bbd760e39015e38af`
- Evaluation SHA-256:
  `773e905efb2a06ca73896254a6d1a31283dfc3d94376a342ebecaaf1baa7cb49`
- Checkpoint SHA-256:
  `f4e4c767e3cfce8bab4bea205d101db9215c9088570b6515564034e73b904946`
- Probe audit fingerprint:
  `8e2c2e432957a7a618397165e2613739572870181caf7363243f16a941be9f6f`

The probe returned one exact JSON object, passed all seven deterministic checks,
passed Pydantic validation, selected the correct `sev3` answer, reconciled 282
prompt tokens, wrote a terminal `passed` checkpoint, and closed both worker ports
cleanly.

Cache reuse was not evaluated by that probe.

## Structural schemas

The new canary constrains structure without hard-coding expected answers:

- incident severity allows `sev1`, `sev2`, `sev3`, or `sev4`;
- payment reconciliation allows an unsigned integer string;
- data-sharing policy allows `allow` or `block`;
- case ID, confidence, and turn index remain exact schema constants;
- additional properties are forbidden.

Deterministic scoring must still verify each expected answer.

## Canary execution contract

- Endpoint: `/v1/chat/completions`
- Response format: `json_schema`
- Condition: C
- Route: `worker_1 -> worker_1`
- Cases:
  1. `incident-severity`
  2. `payment-reconciliation`
  3. `data-sharing-policy`
- Trajectories: 3
- Requests: 6
- Temperature: 0
- Top-p: 1
- Seed: 7
- Maximum output tokens: 128
- External spend: 0
- Customer data: none
- Raw prompts and outputs in evidence: prohibited

## Promotion rule

Passing this canary still does not authorize the full measured benchmark.

A separate measured-execution authorization package must bind:

- successful canary evidence;
- the schema-constrained endpoint;
- response-schema identities for every case and turn;
- corrected checkpoint behavior;
- exact quality-gated trajectory eligibility;
- a token-length-matched negative control;
- cases, condition order, isolation, abort policy, and analysis plan.

## Non-claims

This slice does not claim:

- that the six-request canary has executed;
- that all selected cases remain semantically correct;
- that turn-two cache reuse survives schema-constrained chat serving;
- that the 72-trajectory measured benchmark is authorized;
- production readiness;
- hosted-provider behavior;
- concurrency, load, or customer-data performance.

## Authorization fingerprint

`6af80f33302e2b6eebf2e4d61efd6b198d9c7706a8a6bfe686b849faad6e5b14`
