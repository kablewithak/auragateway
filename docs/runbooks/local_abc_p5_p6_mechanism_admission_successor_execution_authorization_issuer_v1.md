# Runbook: P5/P6 Mechanism-Admission Successor Execution Authorization Issuer V1

## Repository implementation gate

Validate the issuer and transport on the implementation branch before staging:

1. verify all candidate files exist;
2. scan every candidate file for trailing whitespace;
3. run issuer deterministic `--check`;
4. run Ruff lint on both sources and both focused tests;
5. run Ruff format check on both sources and both focused tests;
6. run strict mypy on both sources and both focused tests;
7. run both focused pytest files;
8. confirm the index remains empty;
9. only then stage the exact candidate tranche.

`git diff --check` is not sufficient before staging because new candidate files are untracked.

## Static generation

The issuer source owns two generated repository artifacts: the issuer review and issuer record. Static generation must never write a live authorization or terminal receipt.

## Future issuance boundary

Live issuance is permitted only after this issuer is merged to synchronized `main`, a fresh T4 x2/internet-off platform observation exists, and the operator supplies the established human-only confirmation through the governed confirmation flow.

Do not substitute conversational approval for the explicit issuance confirmation.

## Future materialization boundary

After one live authorization exists, generate the CPU-only successor control notebook from the exact canonical authorization bytes. The saved control notebook must produce exactly three flat files and no nested archive.

The materializer itself performs no model request, GPU work, worker start, or runtime execution.

## Terminalization

Every execution attempt terminalizes the authorization. An unused authorization may be expired, cancelled, or abandoned, but never reused. Preserve the terminal receipt as evidence.

## Fail-stop

Any identity, freshness, cardinality, scope, time-window, transport, or terminalization ambiguity fails closed. Do not repair or reissue an authorization in place. Reconcile the cause and create a fresh lifecycle when governance permits it.
