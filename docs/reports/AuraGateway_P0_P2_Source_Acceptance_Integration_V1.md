# AuraGateway P0-P2 Source Acceptance Integration V1

## Accepted saved versions

```yaml
materializer:
  notebook: ag-cu129-p0-p2-source-materializer-v2
  saved_version_id: 339075357
  supplied_saved_version_url: https://www.kaggle.com/code/kabomolefe/ag-cu129-p0-p2-source-materializer-v2?scriptVersionId=339075357
  log_sha256: 36d805036fadf9c366e7927bcae8c574b3a6e5aa83f20cd8bf9cc027daf3f288
  results_zip_sha256: eb4319319d2a13536aabdad2c644c15728277e1d3265c51ac87e37e6ffd2be97

inspection:
  notebook: ag-cu129-p0-p2-source-inspection-v2
  saved_version_id: 339077364
  supplied_saved_version_url: https://www.kaggle.com/code/kabomolefe/ag-cu129-p0-p2-source-inspection-v2/log?scriptVersionId=339077364
  log_sha256: 1fbfe999bebb3808b5c4cadb832736d0efd599e062288363c401a6772c6a21d7
  evidence_zip_sha256: cc04c6e287c50d3c2ba6187523174167c7e14219f1d3c96d8c7bec56eefcb21f
```

## Source identities

```yaml
source_main_base_commit: 24914d79ef4b4d33285f111c8920d16c36244614
acceptance_base_main_commit: 0257678b9b6c0afc89927dd24b45cebfe1ab311f
source_bundle_sha256: 49cba1ecdf8e754792fefc05a668e81a75371dd5bef35ac7807ba7e0f2259a53
bundle_manifest_sha256: 463b58b32d34f39d8c189e69cb9614cd7ca2ad2124f73e239c29b96a97f1728f
source_inventory_sha256: 855b1e77900cd5e022255d12189fce4207bf93f74671fed9ec0d74caaf29d505
sha256_manifest_sha256: 503be20c477257200436a4e80db468e9b67323d3e638c2b229c13f83e9f49b1e
materialization_receipt_sha256: f03199b9b5c97f70173ad167841f064f8e18ddb95265f17711113025f18919ae
inspection_report_sha256: 26909d06defd68f7386e404d255f6840d0f01db404995b95e389647679042339
```

## Accepted claim

The corrected P0-P2 source bundle was materialized by saved version `339075357`,
and saved version `339077364` passed metadata-only inspection of the exact materialized
bytes with zero model, worker, network, benchmark, credential, customer-data, and spend
activity.

## Next gate

Regenerate and validate the dedicated P0-P2 execution launcher with the accepted
saved-version identities. After merge and clean-main synchronization, execute one
bounded GPU diagnostic session with the corrected source materializer output and the
governed CUDA 12.9 wheelhouse output.

## Non-claims

No current CUDA linker, driver initialization, Triton execution, model load, worker
startup, inference, cache qualification, measured A/B/C effect, deployment, or
production-readiness claim is made.
