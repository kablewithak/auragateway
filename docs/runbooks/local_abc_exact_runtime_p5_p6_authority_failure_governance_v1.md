# Runbook: Exact-Runtime P5/P6 Authority Failure Governance V1

## Purpose

Preserve and validate the governed failure from Kaggle saved version
`341454766` and the discriminating inspection from saved version
`341466979`.

This runbook does not authorize another execution.

## Lifecycle preservation

The local operational lifecycle files are expected at:

```text
benchmarks/local_abc/auragateway_p5_p6_exact_runtime_requalification_v1_execution_authorization.json
benchmarks/local_abc/auragateway_p5_p6_exact_runtime_requalification_v1_authorization_consumption.json
```

Preserve exact copies into the evidence vault:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_authority_failure_governance_v1 preserve-lifecycle --repo-root .
```

The command fails closed unless:

- authorization SHA-256 is `e9c1b58aedfccee3f36349bf063d5f1267721b8f395699a6c325304d32c20a2c`;
- authorization size is `3414` bytes;
- receipt SHA-256 is `e3a3c0519fff010576f1674adf09c5dafa13b013b04e670b2510204c81f7e4b5`;
- receipt size is `951` bytes.

Existing different vault bytes are never overwritten.

## Governance validation

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_authority_failure_governance_v1 validate --repo-root .
```

Validation proves:

- failed-run evidence identity and early failure depth;
- inspection identity and shallow-discovery false negative;
- exact lifecycle preservation;
- terminal receipt semantics;
- SFR classification;
- acceptance/review consistency;
- authorization remains non-reusable;
- runtime/P5/P6/pilot/final measured authority remains false.

## Validation order

For this governance tranche:

1. changed mutable Python Ruff fix/check/format;
2. focused mypy;
3. focused pytest;
4. governance validator;
5. repository regression gates;
6. exact staged-path and whitespace validation.

Immutable evidence under the evidence vault must not be formatted or rewritten.

## Hard boundaries

- do not rerun saved version `341454766`;
- do not reuse authorization `e9c1b58aedfccee3f36349bf063d5f1267721b8f395699a6c325304d32c20a2c`;
- do not issue a fresh authorization in this tranche;
- do not modify the P5/P6 runtime consumer in this tranche;
- do not relabel `NOT_RUN` capabilities as failed runtime capabilities;
- do not treat a global recursive filename search as an accepted remediation;
- do not authorize pilot or final measured A/B/C execution.

## Next gate

`DESIGN_AND_MERGE_AUTHORIZATION_TRANSPORT_DISCOVERY_REMEDIATION_V1`
