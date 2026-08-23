# P5/P6 Mechanism-Admission Transaction-Bound Authorization V1 Runbook

## Purpose

Generate and validate the static transaction-bound authorization implementation
for the current P5/P6 Mechanism-Admission Successor. This runbook does not grant
live execution authority.

## Static implementation commands

From the AuraGateway repository root with the project virtual environment
active:

```powershell
$Producer = (
    "src/auragateway/local_abc/" +
    "p5_p6_mechanism_admission_transaction_bound_authorization_v1.py"
)

python $Producer generate --repo-root .
python $Producer validate --repo-root .
```

`generate` owns the versioned runtime payload plus the static review and record.
`validate` reconstructs those bytes, validates the merged authority identities,
checks the narrow runtime transform, and requires that no current-scope live
lifecycle artifacts exist.

## Required static result

The validated implementation must report:

```text
candidate_path_count=8
generated_path_count=3
authorization_specific_kaggle_inputs=0
authorization_producer_notebooks=0
manual_confirmation_json_files=0
mechanism_semantics_preserved=true
live_authorization_issued=false
runtime_execution_authorized=false
kaggle_execution_performed=false
```

## What must not be created during this tranche

Do not create or attach:

- `ag-p5-p6-mechanism-auth-control-v1`;
- an authorization-specific Kaggle dataset/input;
- an authorization control/materializer notebook;
- a manually authored confirmation JSON file;
- a live authorization file;
- a transaction-bound notebook intended for execution.

No Kaggle, GPU, model-load, worker-start, or model-request action belongs to the
static implementation tranche.

## Live commands are post-merge only

After this implementation is merged and synchronized to `main`, the producer
supports the later governed lifecycle commands:

```text
authorize-generate
record-platform-observation
terminalize
```

Do not run `authorize-generate` during implementation/review. It requires a
fresh dynamic SHA-256 challenge and exact manual retype. `record-platform-observation`
is permitted only after the governed artifact exists and before Save & Run All.
The platform observation is a durable local lifecycle receipt, not a Kaggle
runtime input.

## Kaggle topology after future live issuance

The transaction-bound execution topology permits only these Kaggle input roles:

1. durable runtime/wheelhouse;
2. model snapshot.

The exact current input identities and notebook settings must be revalidated at
the future live boundary. Do not infer or reuse stale setup instructions from
PR #291.

## Failure handling

If generation or validation fails, stop before staging and preserve the complete
failure surface. Do not hand-edit generated artifacts.

If the same failure family recurs at the same gate, use the semi-formal
reasoning certificate before another remediation: premises, exact code/data
flow, competing hypotheses, refutation/counterexample, and a bounded formal
conclusion.

## Next gate after merge

`MERGE_THEN_ISSUE_FRESH_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1`
