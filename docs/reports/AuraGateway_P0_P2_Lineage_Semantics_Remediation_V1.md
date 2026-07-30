# AuraGateway P0-P2 Lineage Semantics Remediation V1

## Defect

The corrected source lineage carried exact PR #160 artifact bytes while declaring the
pre-remediation PR #159 merge `831b4ad4e8eb4139b51af927eb721989be197cbc` as `source_repository_commit`.
A successful materializer and inspection could therefore emit a green but false
repository-provenance assertion.

## Resolution

```text
source_repository_commit            -> source_main_base_commit
source_main_merge_commit             -> source_main_base_commit
diagnostic_source_main_merge_commit  -> option_c_decision_merge_commit
branch_name                          -> architecture_origin_branch
```

- Source main base: `24914d79ef4b4d33285f111c8920d16c36244614`
- Option C decision merge: `f4f08eda4b4d4747514b4646fe53664d8a78ca6d`
- Architecture origin branch: `fix/local-abc-cu129-p1-probe-taxonomy-v1`
- Exact-byte authority: SHA-256

## Regenerated identities

```text
source bundle:
49cba1ecdf8e754792fefc05a668e81a75371dd5bef35ac7807ba7e0f2259a53

bundle manifest:
463b58b32d34f39d8c189e69cb9614cd7ca2ad2124f73e239c29b96a97f1728f

source inventory:
855b1e77900cd5e022255d12189fce4207bf93f74671fed9ec0d74caaf29d505

source materializer notebook:
210d94fb92112c4221697aa053522652287f5a41c0b0710e1e5ce3134fd1ec4b

source inspection notebook:
b4fe539c760c7277368c9b691410deac322ecd292e5fee9a2ed8541beec97ab9

execution launcher notebook:
bf851f463526e829536e3f3f908f617d114e52dbbb30ba8b9e9145451665d0f7
```

## Preserved identities

The diagnostic notebook, diagnostic request, and diagnostic implementation record are
unchanged. Their existing SHA-256 bindings remain authoritative.

## Evaluation additions

- Base-commit semantics are asserted in the source bundle manifest.
- Option C decision provenance is named explicitly.
- Generated materializer and inspection code reject the legacy receipt key.
- Generated launcher metadata and runtime validation use the base-commit contract.
- Historical architecture-origin branch provenance is preserved without pretending it is
  the current generation branch.

## Safety

Repository-only remediation. No Kaggle run, GPU activity, package installation, model
load, worker start, model request, benchmark trajectory, credentials, customer data, or
external spend.

## Next gate

```text
merge_then_execute_corrected_cpu_only_p0_p2_source_materializer_v2
```

The materializer and metadata inspection remain separate operator gates.
