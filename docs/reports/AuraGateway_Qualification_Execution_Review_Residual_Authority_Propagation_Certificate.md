# AuraGateway Qualification Execution Review Residual Authority Propagation Certificate

**Certificate ID:** `auragateway-qualification-execution-review-residual-authority-propagation-v1`

**Status:** `TRANSITIVE_CURRENT_AUTHORITY_PROPAGATION_PROVEN_AFTER_LAUNCHER_REGENERATION`

**Scope:** Repository-local qualification review, execution package, and authorization-input identity propagation

## Incident

The merged CUDA 12.9 runtime integration passed its focused gates but the merged-main full suite exposed one historical execution-review validator that still compared old Git blob identities with current live files.

The first correction properly revision-bound that historical review to source commit `3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8`.

The next full-suite run then exposed a downstream current-package failure: the execution package still expected the pre-correction review-validator source blob.

## Premises

1. The execution-review JSON is historical evidence and must remain unchanged.
2. The execution-review validator source is current repository code and may legitimately change to preserve historical semantics.
3. The execution package binds the current validator source by Git blob identity.
4. The deterministic execution request embeds that source authority.
5. The execution notebook embeds the deterministic execution-request SHA-256.
6. The authorization-input package binds the current execution contracts, request, and notebook identities.
7. Historical PR 109 authorization-issuance evidence must continue to validate at its original revision and must not be rewritten.

## Execution trace

```text
historical execution-review validator corrected
    -> current review-validator source Git blob changes
    -> execution contracts must bind the new current source blob
    -> deterministic execution request changes
    -> deterministic notebook request binding changes
    -> authorization contracts must bind the new execution contracts, request, and notebook blobs
    -> offline dataset request changes
    -> qualification authorization request changes
```

## Rejected alternatives

### Update only the execution-review validator

Rejected because the execution package correctly fails when a current source authority no longer matches its frozen identity.

### Revision-bind the current execution package to its previous runner

Rejected because the execution package is a current deterministic producer, not historical evidence. Its downstream identities must be regenerated when a current authority changes.

### Update historical PR 109 review identities

Rejected because that would rewrite historical evidence instead of preserving revision-bound provenance.

### Disable exact Git identity checks

Rejected because it would weaken the repository harness and allow unreviewed source changes to alter generated operational inputs.

## Resolution

The remediation:

- preserves the historical execution-review JSON unchanged;
- resolves its five original authorities at `3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8`;
- binds the corrected current review-validator source blob in execution contracts;
- regenerates the deterministic execution request;
- regenerates the deterministic unexecuted notebook;
- propagates the resulting execution-contract, request, and notebook identities into authorization contracts;
- regenerates the offline dataset request and qualification authorization request;
- updates deterministic fingerprint assertions;
- retains the fresh CUDA 12.9 authorization-review requirement.

## Safety invariants

- no Kaggle session was started;
- no GPU was enabled;
- no worker was started;
- no model or tokenizer was loaded;
- no model request was performed;
- no customer data or credentials were used;
- no authorization was issued;
- no runtime evidence was generated;
- no historical evidence was rewritten;
- measured A/B/C execution remains unauthorized.

## Regression gates

The remediation requires:

- historical execution-review tests;
- execution-package generation and verification tests;
- authorization-input package tests;
- current authority-graph validation;
- full repository pytest;
- full repository mypy;
- repository-wide Ruff lint;
- changed-file Ruff format verification;
- canonical JSON and Git whitespace checks.

## Residual deterministic launcher propagation

The subsequent full repository suite exposed one additional generated-artifact
consumer. The reviewed qualification notebook is a direct input to the
deterministic Kaggle launcher generator. Changing the reviewed notebook changed
the embedded reviewed-core bytes and SHA-256 expected in the committed launcher.

The original ten-file remediation regenerated the reviewed notebook but omitted:

`notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb`

This produced four test failures sharing the same first divergence:

`MISSED_GENERATED_LAUNCHER_PROPAGATION`

The committed launcher was regenerated using the repository-owned deterministic
generator and independently verified against the current reviewed notebook.

No launcher execution, Kaggle session, GPU activity, worker start, model load,
authorization issuance, or model request occurred.

## Conclusion

The residual failure was not an independent runtime defect. It was an incomplete propagation of one legitimate current source-identity change through deterministic execution and authorization-input producers.

The corrected boundary preserves historical truth while maintaining exact current-package identity enforcement.
