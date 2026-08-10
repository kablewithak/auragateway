# AuraGateway P5/P6 Provenance Identity Reconciliation V1

**Checkpoint:** 2026-08-10
**Base main:** `49d853a25a783767c3fc9062145f2b751053a78f`
**Status:** `RECONCILED_BEFORE_EXECUTION`

## Root cause

`PRE_COMMIT_PROVENANCE_IDENTITY_DEFECT`

Two documentation identities in the historical P5/P6 implementation review and
record were generated from transient pre-commit bytes. The bytes committed to
Git were different by four bytes for each document and have remained unchanged
since the implementation merge.

## Corrected current authority

```text
implementation ADR
sha256=020e77ba1550ea66342cd41b7c99ab6783d596f7bf9dc926681e959e0eda27a7
bytes=4181

implementation report
sha256=af6e0173aad2b1e9b0faa5facefb9e2271372399fa6b932b3780c5490c7d1fdb
bytes=3541
```

## Historical executable identities retained

```text
implementation review=151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d
implementation record=6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d
notebook=cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7
runtime script=d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67
wrapper=55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c
```

The correction does not regenerate or mutate these artifacts.

## Safety state

```text
implementation_provenance_consistent=true
executable_runtime_identity_changed=false
live_authorization_issued=false
runtime_execution_authorized=false
p5_p6_exact_runtime_requalified=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Acceptance criteria

The tranche passes only if the reconciliation record is deterministic, the two
committed documentation identities match exactly, every retained historical
artifact matches its frozen identity, the embedded historical runtime passes the
semantic-boundary audit, the issuer binds the reconciliation authority, focused
tests pass, and full repository regression returns only the accepted historical
mypy baseline.

## Next gate

`REVALIDATE_EXACT_RUNTIME_P5_P6_EXECUTION_PRECONDITIONS_V1`
