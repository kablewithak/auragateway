# Local ABC Transaction-Bound Execution Authorization V1 Runbook

## Static tranche

Before merge, only `generate` and `validate` are used. They are inert and must report no live authorization and no GPU authority.

## Live workflow after runtime-integration merge

Merging this static boundary alone does not enable live issuance. `authorize-generate` fails closed until the successor runtime integration record is present and binds the exact payload identity. After that integration is merged, the implementation must be on synchronized clean `main` and the merged architecture must be an ancestor of HEAD.

The first local control command is `authorize-generate`. It receives the already reviewed runtime payload path, prints the exact bound scope, implementation/runtime identities, hard request budget, required T4 x2 / Internet Off policy, and a dynamic SHA-256 authorization challenge. The operator personally retypes the displayed challenge. No fixed confirmation phrase and no manually constructed confirmation JSON are used.

Successful confirmation writes the live authorization and executable manifest locally and writes the generated notebook to the Desktop by default. Those lifecycle files are not Kaggle inputs.

Kaggle receives only the generated notebook plus durable runtime/model inputs. A fresh platform observation is made after notebook generation and before the single Save & Run All action.

The second local control command is `terminalize`. Every attempted execution consumes the authority. `OUTCOME_UNKNOWN` remains available when terminal evidence packaging is incomplete. Unused authority must be terminalized as expired, cancelled, or abandoned as applicable.

## Non-claims

Single-use is a governance invariant. Runtime anti-replay and malicious-operator resistance are not established. More than one observed execution for a transaction requires reconciliation.

This static tranche does not itself authorize a GPU run.
