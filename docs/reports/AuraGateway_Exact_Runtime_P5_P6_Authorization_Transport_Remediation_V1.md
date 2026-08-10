# AuraGateway Exact-Runtime P5/P6 Authorization Transport Remediation V1

## Determination

The failed governed run did not test P5/P6 capability. It failed at an early
control-plane boundary because the V1 authorization consumer encoded a
one-level Kaggle input-depth assumption.

Accepted failure:

```text
saved_version_id=341454766
failure_class=AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE
failure_depth=EARLY_CONTROL_PLANE
runtime_incompatibility_established=false
runtime_installation_performed=false
model_loaded=false
worker_started=false
model_requests_performed=0
```

Discriminating CPU-only inspection:

```text
inspection_saved_version_id=341466979
current_consumer_candidate_count=0
recursive_diagnostic_candidate_count=1
candidate_metadata_parity_count=1
```

Observed canonical authorization path:

```text
datasets/kabomolefe/ag-p5-p6-execution-authorization-v1/
execution_authorization_v1.json
```

## Historical evidence used

The remediation intentionally reuses mechanisms, not historical runtime claims.

PR #112 established authorization-specific control materialization through a
saved CPU-only notebook output.

PR #114 established the critical discovery rule:

```text
resolve governed producer/root
-> validate exact bounded members inside that root
```

It also proved why global filename uniqueness across all attached inputs is not
safe.

PR #115 established current-producer/current-consumer parity as a pre-execution
requirement.

PR #222 established producer-owned versus consumer-owned fact separation.

PR #224 established successor implementation rather than mutation of an executed
diagnostic harness.

## V2 implementation shape

V1 remains byte-identical. V2 is generated as a sibling notebook and runtime
template.

Behavioral controls remain:

1. `BASE_COLD`
2. `BASE_WARM`
3. `NEGATIVE_PREFIX`
4. `POST_RESET_COLD`
5. `CROSS_WORKER_COLD`
6. `WORKER1_RETENTION`

The exact runtime remains:

```text
Python 3.12
Torch 2.11.0+cu129
CUDA 12.9
Transformers 5.14.1
Triton 3.6.0
vLLM distribution 0.25.1+cu129
vLLM semantic module version 0.25.1
Qwen/Qwen2.5-0.5B-Instruct
revision 7ae557604adf67be50417f59c2c2f167def9a775
T4 x2
Internet Off
```

The permanent semantic boundary remains:

```text
RawRuntimeObservation
-> TypedSemanticObservation
-> BehaviorDecision
-> EvidenceProjection
```

## Authorization transport contract

The future V2 authorization is materialized in a CPU-only notebook:

```text
ag-p5-p6-auth-control-v1
```

Saved output directory:

```text
ag_p5_p6_auth_control_v1
```

Exact flat contents:

```text
control_package_manifest.json
execution_authorization_v1.json
materialization_receipt.json
```

The V2 runtime discovers only directories with the exact output name under a path
containing the exact producer notebook token. Exactly one governed root must
exist.

The consumer then validates:

- exact three-file allowlist;
- regular non-symlink members;
- no nested archive members;
- canonical JSON;
- authorization SHA-256 and byte size;
- manifest-to-authorization binding;
- receipt-to-authorization binding;
- receipt-to-manifest binding;
- V2 authorization semantics and time window;
- V2 runtime-script identity.

Only after this boundary passes may wheelhouse/model discovery and runtime
installation begin.

## Measured regression contract

The remediation tests the actual failure mode rather than a simplified toy case.

Required fixed cases:

```text
direct_dataset_shallow_false_negative
governed_root_positive
unrelated_filename_collision
multiple_governed_roots
extra_control_member
missing_control_member
authorization_identity_drift
receipt_binding_drift
```

The V2 implementation also AST-compares all unchanged top-level runtime
functions against the V1 runtime template. Only the approved transport and
lineage functions may differ.

## Safety

This tranche performs no:

- Kaggle execution;
- GPU execution;
- package installation;
- model load;
- worker start;
- model request;
- network request;
- benchmark trajectory;
- pilot;
- measured A/B/C execution.

It does not create or issue a V2 execution authorization.

## Non-claims

The remediation does not prove current V2 model construction, worker startup,
P5, or P6. It does not authorize a pilot, measured A/B/C execution, or
production use.

## Next gate

`DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION_AUTHORIZATION_ISSUER`
