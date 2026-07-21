# Semi-Formal Reasoning Certificate: Shared tooling authority propagation failure

## Certificate identity

```text
certificate_id=AURAGATEWAY-SFRC-REPEATED-AUTHORITY-PROPAGATION-001
normalized_failure_class=INCOMPLETE_TRANSITIVE_AUTHORITY_PROPAGATION
status=RESOLUTION_SELECTED
```

## Trigger

The same normalized failure class appeared repeatedly across the current qualification lineage:

1. PR #131 recorded `INCOMPLETE_TRANSITIVE_AUTHORITY_GRAPH_MIGRATION`.
2. PR #132 recorded `MISSED_GENERATED_LAUNCHER_PROPAGATION`.
3. PR #133 appended a Ruff exception to `pyproject.toml` without reconciling every exact-hash and
   generated-asset consumer.

The surface errors differed, but each occurrence changed an upstream authority without traversing
all dependent validators, generators, generated artifacts, and historical evidence bindings.

## Intended behavior

- Historical evidence remains byte-for-byte immutable.
- A lint-policy exception changes lint behavior only.
- Groq compatibility review provenance remains valid.
- Preflight-v3 generated planning assets remain reproducible.
- A current harness is packaged only from a clean, green, merged source commit.
- The implementation PR does not guess its future merge identity.

## Observed behavior

`pyproject.toml` served four roles simultaneously:

1. project metadata;
2. dependency authority;
3. Ruff configuration;
4. exact-hash input to historical Groq and preflight-v3 authority graphs.

Appending one `SIM117` exception changed its SHA-256. The Groq validator then failed at source
binding before reaching SDK-version validation. The preflight-v3 generator produced new canonical
assets because the developer dependency-lock fingerprint changed. The initial toolchain also
hard-coded PR #133's merge commit as the final package source, even though the final source must be
the later toolchain merge commit.

## Premises

- `pyproject.toml` historical SHA-256 is
  `5387ea09341bde18d73518e28a236f65865918dd406fcb13824c0c8156a57103`.
- The historical materializer notebook SHA-256 is
  `91f9ccc30883341af4cfd24d11c780ee136b9f7ccf9316b77b9d72ba559312c2`.
- PR #133 merge commit
  `defe184d338b525e2f48104ef76e5d0d9a1329a8` is the minimum reviewed ancestor.
- The final source commit is unknown until the corrected toolchain PR merges.
- Active harness migration and authorization remain blocked.

## First divergence

```text
pyproject.toml was used as both stable shared authority and mutable lint-policy storage.
```

The process failure followed: a late configuration change was treated as local remediation instead
of invalidating all previous repository gates.

## Why the first remediation was insufficient

The per-file Ruff exception made `python -m ruff check .` pass, but the remediation did not inspect
transitive consumers of `pyproject.toml`. Full pytest was not rerun after the late change. This
allowed a red baseline to merge and made the hard-coded `defe184` package source unsafe.

## Alternatives rejected

### Rewrite historical Groq evidence

Rejected. Historical review bytes must not be changed to absorb an unrelated future lint policy.

### Weaken source-binding validation

Rejected. The mismatch was real and provenance-sensitive.

### Change the SDK-version test regex

Rejected. The test never reached SDK-version validation; changing the regex would normalize the
wrong failure path.

### Regenerate all preflight-v3 assets

Rejected. Their behavior did not change. Regeneration would create unnecessary identity churn.

### Edit the historical notebook

Rejected. That destroys consumed evidence identity.

### Package PR #133 merge commit

Rejected. It is a known red commit and cannot contain the corrected toolchain implementation.

## Selected resolution

1. Restore `pyproject.toml` to its historical exact byte identity.
2. Add root `ruff.toml` extending `pyproject.toml` and containing the single exact notebook
   `SIM117` exception.
3. Preserve the historical notebook unchanged.
4. Treat PR #133 as a required minimum ancestor, not the final source.
5. Resolve the final source during post-merge preparation from clean `main` where
   `HEAD == origin/main`.
6. Reject preparation when `HEAD` is still the PR #133 review commit.
7. Derive archive, dataset, and materialized-directory names from the exact final commit.
8. Rerun all validation gates after any late source, configuration, generated-asset, or authority
   change.

## Regression gates

The repository must prove:

- historical `pyproject.toml` SHA-256 parity;
- dedicated `ruff.toml` identity and plain repository-wide Ruff success;
- historical notebook SHA-256 parity;
- Groq compatibility success and SDK-version branch reachability;
- preflight-v3 byte-for-byte regeneration parity;
- final source strictly advances beyond the review commit;
- final source equals synchronized clean `main`;
- deterministic commit-derived output naming;
- no authorization, GPU execution, model load, worker start, or model request.

## Claims

```text
root_cause_sufficiency=SUFFICIENT
resolution_scope=BASELINE_REPAIR_AND_SOURCE_BINDING_REDESIGN
historical_evidence_rewrite_required=false
preflight_asset_regeneration_required=false
```

## Non-claims

- The current harness has not been packaged.
- Kaggle materialization has not run.
- Metadata-only input inspection has not run.
- Authorization has not been issued.
- GPU qualification has not run.
- No model request has been performed.
