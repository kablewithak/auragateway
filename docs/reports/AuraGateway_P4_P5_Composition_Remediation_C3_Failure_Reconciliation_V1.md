# AuraGateway P4/P5 Composition Remediation C3 Failure Reconciliation V1

## Decision

The governed P4/P5 composition remediation confirmation for transaction
`c984a77f3de24f986a9d9f255c25d83e375f552951b256c6e8f44c79c96e3542`
is accepted as a valid governed execution failure and is terminalized as
`CONSUMED / FAILED`.

The Kaggle saved version is `341956898`.

The execution does not confirm the P4/P5 composition remediation. It establishes
that replacing the historical V5 cache-context instruction with the accepted V4
instruction was **not sufficient** to restore the full composed C3 structured
output contract.

## Observed execution boundary

The governed run observed:

- exact remediated runtime SHA-256
  `aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff`;
- runtime installation: PASS;
- runtime import closure: PASS;
- C1 model/tokenizer construction: PASS;
- C2 worker startup: PASS;
- first structured request: `BASE_COLD`;
- first prefix variant: `A`;
- C3: FAIL;
- failure class: `REQUEST_EXECUTION_FAILURE`;
- safe message: `model response is not valid JSON`;
- model requests: 1;
- model loads: 1;
- worker starts: 1;
- hidden retries: 0;
- external network requests: 0;
- teardown: PASS;
- scratch cleanup: PASS;
- P5: NOT REACHED;
- P6: NOT REACHED.

The request reached the model-response parsing boundary. This is not evidence of
a failed HTTP transport, failed runtime installation, failed model construction,
or failed worker startup.

## Pre-request identity evidence

The new pre-request token journal persisted request identity before inference:

- request ordinal: `1`;
- request role: `BASE_COLD`;
- prefix variant: `A`;
- token count: `899`;
- token SHA-256:
  `6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`;
- request-payload SHA-256:
  `b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e`;
- `persisted_before_model_request=true`.

Raw prompts and raw model outputs were not retained.

## Remediation result

The executed successor runtime contains the accepted V4 wording at the system
prompt and both cache-context instruction seams, and the historical V5
cache-context tail is absent.

Therefore:

`REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION`

is rejected as a **sufficient** remediation for the full composed request
contract.

This does not erase the earlier controlled differential result that message
composition was the discriminating variable under the frozen A/B diagnostic.
It narrows the conclusion: the remaining causal subfactor inside the preserved
composition bundle is unresolved.

The current evidence does not identify whether the remaining factor is the long
cacheable context, assistant acknowledgement, role topology, an interaction
among those dimensions, or another preserved composed-request property.

## Runtime metadata boundary

The remediated runtime intentionally retained predecessor metadata fields that
were outside the remediation changed surface. Current authority is established
by the executed runtime SHA-256 and transaction-bound wrapper, not by those
stale predecessor labels. They are preserved metadata debt, not the observed C3
cause.

## Evidence custody

Repository custody is bound by:

- custody manifest SHA-256:
  `9338d50ea9b2f83084edc3322f481d07fe92373ac77bcafd61f3b82e319f063a`;
- governed evidence ZIP SHA-256:
  `784b7c4a7f0ac03afec018b24f40cb19d3db0e8ecb0ada2f930b0fd1c66e5397`;
- terminal log SHA-256:
  `39cd32a1914262530823f73ba5197ed425befe85606a42344d8c70f6c1edef80`;
- saved notebook SHA-256:
  `1ae90a9ae7708346a15ad001af61f6a8b3a2cdb0ddb25d90c33deefca29a472a`.

Two downloaded terminal-log copies were observed and were byte-identical. One
canonical copy is preserved in the evidence vault; this does not represent two
executions.

The durable platform-observation receipt and terminal receipt are preserved
with the transaction lifecycle.

## Governance

The single-use authorization is consumed.

- authorization reusable: false;
- unchanged replay authorized: false;
- new execution authorized: false;
- guided decoding fix authorized: false;
- runtime execution authorized by this reconciliation: false.

No rerun is permitted under the consumed transaction.

## Non-claims

This reconciliation does not claim that P5 failed or that P6 failed. Neither
probe ran. It does not claim the exact malformed model output because raw model
output retention was prohibited. It does not establish generic Qwen
unreliability, runtime incompatibility, model-construction failure, worker-
startup failure, or failure of V4 prompting in general.

It does not identify the remaining composition subfactor and does not authorize
JSON schema, guided decoding, or any other runtime change as the next fix.

## Next gate

`STATIC_REMAINING_COMPOSITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1`

Before any new GPU experiment is designed or authorized, compare the exact
current `BASE_COLD` request construction against the accepted simple V4 control
and the prior composition differential. Decompose only the still-preserved
composition dimensions and choose the smallest discriminating next test.
