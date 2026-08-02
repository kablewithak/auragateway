# AuraGateway P3-P6 Execution Authorization V3

## Purpose

Govern one diagnostic attempt that tests the V3 process-tree
import-closure remediation and, only if that precondition passes, the P3
through P6 runtime sequence.

## Hard ceiling

```text
authorization window: <= 240 minutes
Kaggle sessions: 1
runtime installation attempts: 1
runtime import-closure probes: 1
model loads: 3
worker starts: 3
model requests: 5
output tokens per request: 32
benchmark trajectory requests: 0
external network requests: 0
hidden retries: 0
external spend: 0
```

## Additional V3 controls

- exact target-site `PYTHONPATH` is mandatory;
- inherited `PYTHONPATH` replacement is mandatory;
- the nested-interpreter probe is mandatory;
- the import-closure report is mandatory;
- probe failure must consume zero model-load and worker-start actions;
- bounded worker failure diagnostics are mandatory;
- raw worker logs remain outside the evidence ZIP;
- stop on first failure.

## Commercial proof

This is an Agent Harness Hardening artifact. It demonstrates that an AI
runtime change is not merely shipped: it is identity-bound, action-bounded,
single-use, terminally consumed and supported by queryable evidence.

## Non-claims

The issuer implementation does not execute the notebook, issue live
authority, prove the import-closure remediation or establish P3-P6
success.
