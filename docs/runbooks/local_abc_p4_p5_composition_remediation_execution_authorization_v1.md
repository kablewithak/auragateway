# Local ABC P4/P5 Composition Remediation Execution Authorization V1

## Purpose

Statically validate and merge the issuer before any live authority exists.
After merge, the live workflow is intentionally split into distinct state
transitions so the platform observation cannot remain console-only.

## Static implementation validation

1. Ruff format/check the issuer source and focused test.
2. mypy the issuer source and focused test.
3. Compile/check the generator template through focused tests.
4. Deterministically generate static review and record.
5. Deterministically validate static review and record.
6. Run focused pytest.
7. Run full repository pytest.
8. Verify the exact eight-path candidate boundary, including the LF identity control in `.gitattributes`.

No `authorize-generate`, platform-observation, terminalization, Kaggle, model,
worker, or request action is permitted during this implementation tranche.

## Live workflow after merge

1. Synchronize clean `main`.
2. Run `authorize-generate`; exactly retype the fresh challenge.
3. The issuer generates one transaction-bound notebook on Desktop and persists
   live authorization + manifest. Do not press Save & Run All yet.
4. Inspect Kaggle notebook settings: T4 x2, two GPUs, Internet Off.
5. Immediately run `record-platform-observation --platform-observed-at <ISO8601>`.
   The durable receipt must be written successfully.
6. Only after the receipt passes may the operator perform the single Save & Run
   All.
7. Preserve the saved-version ID, runtime evidence ZIP, terminal log, and
   terminalize the authorization exactly once.

## Failure rule

If platform observation cannot be durably persisted, do not Save & Run All.
If execution was nevertheless attempted, terminalize it as failed,
interrupted, diagnostic-invalid, or outcome-unknown as supported by evidence;
do not fabricate a passing receipt.
