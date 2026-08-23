# AuraGateway P5/P6 Mechanism-Admission Successor 344436401 Reconciliation V1

## Governed transaction

- Kaggle saved version: `344436401`
- Transaction ID: `27b11c47f159a5f1a16b00521c1fcb1a166284aff4630149a34f86b9df7d8cf1`
- Issuer merge commit: `af765fd19d2a486b2fe35e9989715430bd1f9f8c`
- Runtime payload SHA-256: `f5ad407ef49a6d39a79d2b3fc60b88581960a5c6b2d37f70cc93a4a76575659e`
- Evidence ZIP SHA-256: `54b62507b30b6661ba949b29ccea855f8c1297f0d0d74341473157e69b3c3c37`
- Preservation manifest SHA-256: `ad6d16cb28c8366f0cf39b2ac06cdeaf7a2765f907c19014b228765c30d365b4`

## Repository disposition

`status=ACCEPTED_DIAGNOSTIC_FAILURE`

`transaction_bound_runtime_admission=PASSED`

`terminal_disposition=CONSUMED`

`terminal_execution_outcome=FAILED`

`runtime_install_attempts=1`

`runtime_install_process_outcome=NOT_DURABLY_PRESERVED`

`first_supported_divergence=POST_INSTALL_TARGET_RUNTIME_SNAPSHOT_SYMLINK_REJECTION`

`cleanup_primary_failure_preserved=true`

`authorization_reusable=false`

`new_execution_authorized=false`

## Semi-formal reasoning certificate

### Premises

1. The executed runtime SHA-256 equals the merged R1 runtime identity.
2. Exactly one runtime-install attempt was consumed.
3. The primary failure report records `P3_P6_RUNTIME_INSTALL_FAILED`,
   `MODEL_CONSTRUCTION_FAILURE`, and `RuntimeError: target runtime contains a symbolic link`.
4. `runtime_install_report_v1.json` is a terminal fallback report with
   `status=NOT_RUN` and `process_outcome=NOT_RUN`.
5. The executed source calls `run_bounded_process()` before constructing the
   install report, but constructs `working_disk_after` and
   `target_runtime_after=directory_snapshot(TARGET_ROOT)` before `write_json()`.
6. Cleanup records the same symlink message as a secondary cleanup failure but
   still removes scratch.
7. Model loads, worker starts, model requests, P5, and P6 are all zero/not reached.
8. CPython 3.12 statically creates a `lib64 -> lib` venv symlink on 64-bit
   POSIX non-Darwin platforms independently of executable copy mode.
9. The exact offending Kaggle member pathname was not preserved.

### Trace

```text
venv --without-pip --copies
        ↓
TARGET_ROOT created
        ↓
one offline install subprocess attempt
        ↓
run_bounded_process returns
        ↓
install report has not yet been written
        ↓
post-install directory_snapshot(TARGET_ROOT)
        ↓
symlink rejected
        ↓
install_runtime exits before write_json(runtime_install_report)
        ↓
terminal fallback creates NOT_RUN install report
        ↓
primary RuntimeError preserved
        ↓
cleanup snapshot also sees symlink
        ↓
cleanup failure kept secondary; scratch removed
```

### Conclusions

1. The first supported material divergence remains the target-runtime
   post-install snapshot.
2. `venv --copies` did not establish a symlink-free venv.
3. The exact Kaggle symlink pathname remains unproven.
4. CPython's structural `lib64 -> lib` member is a strongly supported static
   root-cause candidate, not an observed-path claim.
5. The blanket no-symlink invariant is too coarse for a standard POSIX venv;
   the correct direction is a narrowly bounded structural allowance, not a
   broad relaxation.
6. The install-process result must be durably written before any post-install
   filesystem inspection capable of throwing.
7. R1 authority is terminal and future issuance requires a fresh R2 namespace.

## Established execution depth

The transaction-bound wrapper and durable platform observation were valid.
The governed execution consumed one runtime-install attempt.

The runtime did not reach:

- target-runtime validation;
- runtime import closure;
- model construction;
- worker startup;
- model requests;
- P5;
- P6;
- pilot execution;
- final measured A/B/C.

Supported counters:

- runtime install attempts: `1`
- model loads: `0`
- worker starts: `0`
- model requests: `0`
- hidden retries: `0`

## Install-report durability defect

The current `install_runtime()` obtains the subprocess result and then builds
one report dictionary whose expressions include post-install filesystem
snapshots. The report is written only after those expressions all succeed.

Therefore the target-runtime snapshot exception prevents the already-obtained
process result from becoming durable. Terminal completion later sees no install
report and creates the fallback `NOT_RUN` report.

`NOT_RUN` in the retained install report must therefore not be interpreted as
proof that the install subprocess was never attempted. The counter establishes
one attempt; its subprocess outcome is not preserved.

## Symlink-source disposition

The exact offending symlink path remains unproven by Version `344436401`.

External static inspection of CPython 3.12
`Lib/venv/__init__.py:EnvBuilder.ensure_directories()` shows that a 64-bit
POSIX non-Darwin venv creates `lib64 -> lib`. This occurs independently of the
executable copy-versus-symlink choice.

Disposition:

`CPYTHON_3_12_POSIX_VENV_LIB64_TO_LIB=STRONGLY_SUPPORTED_STATIC_CANDIDATE_NOT_KAGGLE_PATH_PROVEN`

## Cleanup result

The R1 cleanup remediation worked in its principal role: cleanup did not
replace the primary runtime failure. It recorded its own failure separately and
still removed scratch.

However, because cleanup snapshots the entire scratch root, a legitimate
structural venv symlink would continue to make cleanup report failure even after
the install path is otherwise fixed. The same narrow structural policy must
therefore apply when the nested target-runtime member is encountered during the
scratch snapshot.

## Supported claims

- transaction-bound execution admission worked;
- durable platform observation preceded the single Save & Run All;
- exactly one runtime-install attempt was consumed;
- the executed runtime had the authorized SHA-256 identity;
- the first supported divergence is the post-install target-runtime snapshot;
- the primary failure was preserved through cleanup;
- scratch was removed;
- model requests were `0`;
- P5 and P6 were not executed.

## Non-claims

This reconciliation does not establish:

- the exact offending Kaggle symlink pathname;
- whether the offline pip subprocess passed or failed;
- target-runtime validation success;
- runtime import-closure success;
- model incompatibility;
- P5 failure;
- P6 failure;
- P5/P6 requalification;
- final A/B/C execution;
- production readiness;
- authority for another Kaggle execution.

## Next remediation boundary

The implementation tranche may change only the target-runtime lifecycle and
diagnostic-durability seams required to:

1. allow only the exact legitimate target-runtime structural venv symlink while
   keeping every other symlink fail-closed;
2. use the same exact allowance when the nested member is encountered during
   scratch cleanup;
3. durably persist the install-process result before risky post-install
   inspection and make later report enrichment monotonic;
4. preserve the existing primary-failure/cleanup separation;
5. roll consumed lifecycle R1 into the historical allowlist and create a fresh
   lifecycle R2 namespace.

Frozen:

- P5/P6 mechanism semantics;
- model and wheelhouse identities;
- six-request / three-worker / three-model-load budget;
- zero hidden retries;
- transaction-bound authorization architecture;
- human dynamic-SHA retype requirement.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TARGET_RUNTIME_SYMLINK_AND_INSTALL_DURABILITY_REMEDIATION_V1`
