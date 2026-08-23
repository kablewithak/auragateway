# ADR: P5/P6 Target-Runtime Structural Symlink Policy and Install Durability V1

- Date: 2026-08-23
- Status: Accepted design, not implemented
- Evidence source: Kaggle saved Version `344436401`
- Execution authority created by this ADR: `false`

## Context

Saved Version `344436401` executed runtime
`f5ad407ef49a6d39a79d2b3fc60b88581960a5c6b2d37f70cc93a4a76575659e`
under transaction
`27b11c47f159a5f1a16b00521c1fcb1a166284aff4630149a34f86b9df7d8cf1`.

The prior lifecycle remediation changed venv construction to
`--without-pip --copies` and successfully prevented cleanup from masking the
primary failure. The governed run nevertheless failed when
`directory_snapshot(TARGET_ROOT)` rejected a symbolic link.

The exact offending Kaggle symlink pathname was not preserved.

Static inspection of CPython 3.12 `venv` establishes an important compatibility
fact: on 64-bit POSIX non-Darwin platforms,
`EnvBuilder.ensure_directories()` creates a structural `lib64 -> lib` symlink.
Executable copy mode does not remove this structural venv member.

A second defect is independent of the symlink path. `install_runtime()` obtains
the bounded subprocess result but does not write the install report until after
post-install filesystem snapshots. A snapshot exception can therefore erase
the subprocess outcome from durable evidence.

A third lifecycle fact is now settled: lifecycle R1 is terminal
`CONSUMED`, non-reusable, and its four live files must remain immutable.

## Decision

### 1. Keep symlink validation fail-closed by default

Do not remove symlink validation and do not permit arbitrary symlinks.

The only structural allowance is the exact target-runtime member:

```text
member absolute path = TARGET_ROOT / "lib64"
raw readlink target   = "lib"
resolved target       = TARGET_ROOT / "lib"
```

Additional invariants:

```text
TARGET_ROOT/lib exists
TARGET_ROOT/lib is a real directory
TARGET_ROOT/lib is not a symlink
resolved target remains within TARGET_ROOT
```

If any condition differs, reject the symlink.

The allowance is anchored to the absolute `TARGET_ROOT/lib64` member. This
means it can be recognized both when snapshotting `TARGET_ROOT` and when
snapshotting the enclosing `SCRATCH_ROOT`.

The structural symlink itself contributes no duplicate file count or size.

### 2. Separate pure policy from filesystem realization

Prefer a small deterministic policy helper for the path/target contract and a
filesystem validator that verifies the actual member and resolved target.

This keeps the allow/deny rule unit-testable without requiring privileged
symlink creation on Windows while retaining behavior-level tests around
`directory_snapshot()` through controlled seams.

### 3. Persist subprocess truth before post-install inspection

Immediately after `run_bounded_process()` returns, write
`runtime_install_report_v1.json` containing at minimum:

```text
process status
process_outcome
returncode
timed_out
stdout/stderr tails or existing metadata-safe excerpts
command role
network policy
hidden retry count
immutable wheelhouse/requirements identities
working_disk_before
post_install_snapshot_status=PENDING
```

No `disk_snapshot(WORK_ROOT)` after the process and no
`directory_snapshot(TARGET_ROOT)` may occur before this durable write.

Then evaluate process outcome:

```text
LAUNCH_ERROR  -> fail immediately
TIMEOUT       -> fail immediately
NONZERO_EXIT  -> fail immediately
PASSED        -> only state allowed to begin post-install filesystem inspection
```

This restores first-divergence precedence.

### 4. Make install-report enrichment monotonic

If the process passed, perform the post-install snapshots.

On snapshot success, rewrite the report with:

```text
process_outcome=PASSED
post_install_snapshot_status=PASSED
working_disk_after=<snapshot>
target_runtime_after=<snapshot>
```

On snapshot failure, rewrite the report with:

```text
process_outcome=PASSED
post_install_snapshot_status=FAILED
post_install_snapshot_error_type=<metadata-safe type>
post_install_snapshot_safe_message=<sanitized message>
```

and then fail closed.

The second write may add information but may not remove or change the already
persisted process outcome.

If even the enrichment write fails, the first durable process report remains.

### 5. Rotate consumed lifecycle R1 to fresh R2

The four consumed lifecycle R1 files become additional historical immutable
untracked paths.

Historical allowlist:

```text
8 previous historical paths
+ 4 consumed R1 paths
= 12
```

Future live namespace:

```text
lifecycle_r2_authorization_live
lifecycle_r2_artifact_live_manifest
lifecycle_r2_platform_observation_live
lifecycle_r2_authorization_terminal
```

Future notebook:

```text
ag-p5-p6-mechanism-tx-lifecycle-r2
```

Future evidence ZIP:

```text
ag-p5-p6-mechanism-successor-lifecycle-r2-evidence.zip
```

Fresh issuance remains forbidden until the implementation is merged, main is
synchronized, R2 is proven empty, and the operator performs a new dynamic
SHA-256 retype.

## Alternatives rejected

### Allow all symlinks

Rejected. This would weaken an integrity boundary far beyond the demonstrated
compatibility requirement.

### Delete `lib64` after venv creation

Rejected. This mutates standard venv structure to satisfy the checker instead
of modeling the one known legitimate structure and may create hidden runtime
assumptions.

### Disable directory snapshot symlink validation

Rejected. The validation still protects against unexpected link traversal and
uncontrolled filesystem members.

### Keep report persistence after all snapshots

Rejected by observed evidence. Version `344436401` demonstrated that this
ordering can lose an already-attempted install process from the durable report.

### Reuse lifecycle R1

Rejected. R1 is terminal, consumed, and non-reusable.

## Required regression evidence

Before another live authorization can be considered:

1. exact `TARGET_ROOT/lib64 -> lib` is the only allowed symlink;
2. any other path, raw target, absolute target, escaping target, missing real
   `lib`, or symlinked `lib` is rejected;
3. the same exact nested member is tolerated during `SCRATCH_ROOT` snapshot;
4. failed install processes are durably reported and post-install snapshots are
   not attempted;
5. a passed install process remains durably reported when post-install snapshot
   fails;
6. cleanup still cannot mask an earlier primary failure;
7. P5/P6 frozen mechanism ASTs are unchanged;
8. the historical lifecycle allowlist is exactly 12;
9. R2 live paths are disjoint from all historical paths;
10. the default output notebook is the R2 notebook;
11. focused Ruff, strict mypy, focused pytest, producer validation, repo pytest,
    and accepted-baseline repo mypy pass under the existing validation policy.

## Consequences

The next implementation is slightly broader than a one-line symlink fix, but
the breadth is bounded to three causally linked lifecycle concerns:

```text
filesystem compatibility
diagnostic durability
single-use lifecycle rollover
```

It does not change P5/P6 semantics or authorize another execution.

## Non-claims

This ADR does not claim that `TARGET_ROOT/lib64` was the exact offending Kaggle
member in Version `344436401`. It defines the narrow remediation candidate
supported by CPython 3.12 static semantics while preserving fail-closed behavior
for every other symlink.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TARGET_RUNTIME_SYMLINK_AND_INSTALL_DURABILITY_REMEDIATION_V1`
