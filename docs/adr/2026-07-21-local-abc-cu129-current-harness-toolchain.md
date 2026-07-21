# ADR: Build one complete current CUDA 12.9 harness rematerialization toolchain

- **Status:** Accepted for implementation
- **Date:** 2026-07-21
- **Review minimum ancestor:** `defe184d338b525e2f48104ef76e5d0d9a1329a8`
- **Final source-binding policy:** `POST_MERGE_CLEAN_MAIN_HEAD`
- **Decision:** `APPROVED_FOR_COMPLETE_CURRENT_CU129_HARNESS_TOOLCHAIN`

## Context

The active qualification launcher still consumes the immutable historical harness created from
`be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50`. That source tree predates the current CUDA 12.9
runtime contract and cannot realize the exact `vllm_runtime` wheelhouse boundary.

PR #133 approved rematerializing one complete current harness after its review merged. The PR #133
merge commit is a required ancestor, not the final package source. The final package source cannot
be known until this toolchain implementation merges and clean `main` advances beyond the review
commit.

A later Ruff-only edit also exposed a shared-authority defect: `pyproject.toml` was simultaneously
used as mutable lint configuration, historical Groq review evidence, and a preflight-v3 generator
input. The toolchain therefore preserves the historical `pyproject.toml` byte identity and moves the
immutable-notebook `SIM117` exception into a dedicated `ruff.toml` policy overlay.

## Decision

Implement one repository-owned toolchain that performs all pre-external-run work:

- validates the review commit as an ancestor of the final source;
- resolves the final source to exact clean `main` where `HEAD == origin/main`;
- rejects the review commit itself as the final package source;
- derives archive, dataset, and materialized-directory names from the final source commit;
- packages exact Git blob bytes through `git ls-tree` and `git cat-file --batch`;
- validates the current CUDA 12.9 source boundary before packaging;
- writes a deterministic ZIP archive twice and rejects byte divergence;
- emits a typed source inventory and canonical source-package receipt;
- verifies the archive against the inventory and receipt;
- generates one unexecuted Kaggle materializer notebook;
- generates one unexecuted metadata-only input-inspection notebook;
- emits one top-level toolchain receipt binding all generated identities.

The implementation PR does not claim or hard-code its future merge commit. Preparation is permitted
only after merge from a synchronized, clean `main` checkout.

## Tooling authority separation

`pyproject.toml` remains the stable project and dependency authority required by historical review
and preflight assets.

`ruff.toml` becomes the mutable lint-policy overlay and extends `pyproject.toml`. It permits only
`SIM117` for the exact immutable historical materializer notebook. The notebook remains byte-for-byte
unchanged.

## Source selection

Package the complete tracked Git tree at the exact post-merge source commit.

This is deliberate. A hand-maintained allowlist of transitive Python modules, fixtures, schemas,
generated notebooks, and authority records would be more brittle than the bounded Git tree. Git
objects already exclude untracked caches, virtual environments, local credentials, and temporary
outputs.

The packager rejects:

- symbolic links;
- submodules and non-blob Git entries;
- absolute, parent-traversal, backslash, or non-normalized paths;
- tracked nested archives including ZIP, TAR, compressed TAR, 7z, and wheel files;
- duplicate normalized paths;
- more than 5,000 files;
- more than 100 MiB of source bytes;
- missing required runtime, toolchain, or authority paths;
- drift in the reviewed current adapter, contracts, execution request, worker plan, or reviewed
  notebook identities;
- the historical runtime adapter as the current source boundary.

## Determinism contract

The source package is built from exact Git objects:

```text
git ls-tree -rz --full-tree <source-commit>
git cat-file --batch
```

Every blob payload is checked against its Git object identity. ZIP members are written in canonical
path order with:

- fixed timestamp `1980-01-01T00:00:00`;
- normalized regular-file modes;
- fixed DEFLATE level;
- no encrypted members;
- no generated timestamp inside the archive.

Two independent ZIP builds from the same in-memory Git payloads must be byte-identical.

## Generated materializer

The generated materializer requires exactly four source-dataset files:

- the exact generated ZIP archive;
- `source_inventory.json`;
- `source_packaging_receipt.json`;
- `sha256_manifest.json`.

It retains archive traversal, absolute-path, encryption, symbolic-link, non-regular-member,
nested-archive, file-count, byte-budget, required-path, directory-identity, and atomic-publication
controls. It performs no network access, package installation, GPU execution, model load, worker
start, authorization, or model request.

## Generated metadata inspection

The generated inspection notebook requires exactly one current materialized harness producer root,
one exact CUDA 12.9 wheelhouse root, and the unchanged model snapshot authority.

It verifies current source and adapter identities, typed manifest roles, exact 176-package runtime
metadata, historical active-manifest status pending evidence integration, model authority, syntax
compilation, and zero operational execution. It emits bounded success or failure evidence.

The active manifest remains historical until consumed immutable inspection evidence is integrated.

## Repeated-failure escalation

The same normalized failure class may receive one bounded evidence-backed remediation. If it appears
a second time, no third patch is attempted before a semi-formal reasoning certificate records both
occurrences, invariants, files, producers, consumers, authority flow, first divergence, why the
first remediation was insufficient, alternatives, selected resolution, rerun justification,
regressions, claims, and non-claims.

## Consequences

After this PR merges, one local preparation command binds the exact new merge commit and generates
the complete immutable source input and both Kaggle notebooks. Only successful metadata-only
inspection evidence can authorize a later manifest and launcher migration.

## Non-claims

This decision does not establish:

- generation of the current source archive;
- successful Kaggle materialization;
- successful metadata-only input inspection;
- active launcher or manifest migration;
- qualification authorization;
- model or tokenizer loading;
- worker startup;
- environment qualification;
- measured A/B/C authorization;
- production readiness.
