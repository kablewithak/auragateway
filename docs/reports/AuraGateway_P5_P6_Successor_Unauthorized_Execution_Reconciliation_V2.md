# AuraGateway P5/P6 Successor Unauthorized Execution Reconciliation V2

## Decision

Preserve Kaggle saved version `340962890` as technically successful but governance-invalid.

```text
technical_status=PASSED
governed_acceptance_status=INVALID_UNGOVERNED_EXECUTION
authorization_lineage_status=UNESTABLISHED_AT_EXECUTION
evidence_preserved=true
current_line_p5_pass_accepted=false
current_line_p6_pass_accepted=false
measured_abc_eligible=false
```

## Preserved evidence authority

- saved version: `340962890`
- notebook: `ag-p5-p6-successor-runtime-qual-v1`
- notebook SHA-256:
  `113197f104f36fd11a9471e46c5a5bb1de939a5669373250694b11359f405fb8`
- executed runtime SHA-256:
  `5d6b5594cfb85f5ec52c4e4a7db43f029dc18f2aeadc38648f1d7c4b4c422737`
- evidence ZIP SHA-256:
  `fead0bbdcb7cbe62ef9c5df8467cd818152b05d259c3f656f2d4d7217b2d996f`
- terminal log SHA-256:
  `4eb48005682a5743094c466b29d3f6494c83d02909d62aa923c3bbca17781db3`

The static reconciliation records member-level evidence identities without committing
the raw external evidence archive or terminal log.

Audit chain: Reconciliation V1 remains unchanged and continues to preserve saved
version `340872949`. This V2 record is a separate immutable receipt for saved version
`340962890`.

## Technical observations preserved

P5:

- cold cached prefix: `0`
- warm cached prefix: `736`
- post-restart cached prefix: `0`
- cold newly computed prefill: `747`
- warm newly computed prefill: `11`
- post-restart newly computed prefill: `747`
- full-process restart: proven
- namespace-only reset: not used

P6:

- worker 1 target prompt-token delta: `747`
- worker 1 non-target prompt-token delta: `0`
- worker 2 target prompt-token delta: `747`
- worker 2 non-target prompt-token delta: `0`
- route acknowledgement source: harness transport plus worker-local metrics
- model semantics used as route proof: `false`

The run also reports successful teardown and scratch cleanup.

## Governance disposition

The technical result is not promoted because pre-execution single-use authorization
lineage is unestablished for this attempt. Reconciliation is deliberately asymmetric:
it preserves what the runtime evidence proves while refusing claims the control plane
cannot prove.

No retroactive authorization is permitted.

## Next gate

After merge and clean-main synchronization:

1. observe fresh Kaggle T4 x2 capability;
2. issue one fresh transient single-use authorization;
3. verify the authorization;
4. stop;
5. execute one fresh successor attempt separately;
6. consume the authority terminally;
7. accept or classify that governed attempt.

Measured A/B/C remains blocked.
