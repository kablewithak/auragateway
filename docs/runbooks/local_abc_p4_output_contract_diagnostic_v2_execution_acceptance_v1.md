# Runbook: P4 Output-Contract Diagnostic V2 Execution Acceptance V1

## Preconditions

1. Start from clean synchronized `main` at
   `426992050f7112818a83a4db094346d155718933`.
2. Verify the live V3 authorization and consumption files against the uploaded intake.
3. Preserve their exact bytes inside the acceptance evidence vault.
4. Remove the two live lifecycle files from their operational benchmark paths.
5. Create the bounded execution-acceptance branch.
6. Do not execute Kaggle, load a model, start a worker, or issue new runtime authority.

## Evidence intake

Preserve saved version `340775383` evidence byte-for-byte. Validate:

- intake archive identity and complete member boundary;
- outer Kaggle results ZIP identity;
- governed evidence ZIP identity and member bytes;
- runtime bundle manifest receipts;
- terminal certificate tokens;
- V3 authorization-to-consumption binding;
- runtime script and model snapshot identities;
- all 18 request results and exact A-F order;
- case metrics and least-constraining selection;
- native-origin, worker-startup, teardown, and cleanup gates;
- absence of raw prompts, raw model output, and unrestricted worker logs.

The exact terminal log contains historical trailing whitespace. Preserve its bytes and
use one path-scoped Git whitespace attribute rather than rewriting evidence.

## Classification

Accept:

- outcome `PASSED`;
- selected case `A`;
- eligible cases `A,C,E,F`;
- B/D as completed requests with `REQUEST_COMPLETED_OUTPUT_INVALID_JSON`;
- P4 V2 diagnostic as established for this pinned governed run.

Do not claim measured A/B/C, general reliability, deployment readiness, or production
readiness.

## Repository gates

Run focused Ruff, mypy, pytest, `validate-evidence`, deterministic generation,
`validate-package`, repository Ruff, full pytest, exact path-boundary checks, and
`git diff --cached --check`.

## Next gate

After merge, design a separate measured A/B/C execution authorization. This acceptance
does not itself authorize execution.
