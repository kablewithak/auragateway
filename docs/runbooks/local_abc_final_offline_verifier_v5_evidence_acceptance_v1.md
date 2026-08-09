# Runbook: Final Offline Verifier V5 Evidence Acceptance V1

This tranche is local-only. It performs no Kaggle execution and issues no runtime authorization.

## Preconditions

- branch: `feat/local-abc-preflight-v5-evidence-acceptance-v1`
- base main: `23f74af3da1d61ef6a3f9f375617847d7aecef47`
- saved version: `341257985`
- consumed authorization outcome: `PASSED`
- downloaded notebook/log/evidence ZIP identities match the acceptance policy

## Preserve

Run the acceptance module `preserve` command with the downloaded executed notebook, terminal log, and V5 evidence ZIP. The command validates all external identities, the lifecycle binding, archive safety, exact four-member boundary, V5 role statuses, semantic-boundary invariants, and governed non-claims before copying evidence into the repository vault.

Only after preservation is complete does it retire the operational authorization and consumption transients.

## Generate and validate

Run `generate`, then `validate-implementation`. The deterministic review and record must promote only `exact_runtime_offline_verified=true`.

## Safety boundary

No Kaggle execution. No model load. No worker startup. No model request. No P5/P6 execution. No pilot. No measured A/B/C. No credentials. No customer data.

## Next gate

`design_exact_runtime_p5_p6_requalification_v1`
