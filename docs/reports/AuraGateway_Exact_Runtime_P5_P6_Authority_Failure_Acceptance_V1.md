# AuraGateway Exact-Runtime P5/P6 Authority Failure Acceptance V1

## Result

Saved version `341454766` is accepted as a **diagnostic failure** at
the authorization-discovery boundary.

```text
failure_class=AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE
failure_depth=EARLY_CONTROL_PLANE
runtime_incompatibility_established=false
p5_p6_exact_runtime_requalified=false
authorization_reusable=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Failed-run evidence

The governed execution preserved the expected runtime-source identity and then
failed before runtime installation.

Evidence ZIP SHA-256:

`ca1cfada6a4c0ab7d8ed8fe446d3d6c281f246c4731ce20441884a998f82e6b6`

Terminal log SHA-256:

`3e0eeb9cb02faf7bc45ee72587fdf7d982e6030019b58f0e307ec123fa40c847`

Observed counters:

- runtime installation attempts: 0
- import-closure probes: 0
- model loads: 0
- worker starts: 0
- model requests: 0
- network requests: 0
- benchmark trajectory requests: 0

## Discriminating inspection

Inspection saved version `341466979` used no accelerator,
Internet Off, no secrets, no runtime installation, no model load, no workers,
and no requests.

Inspection ZIP SHA-256:

`387935b89f327945811900365eba69c4278919e49750337aef8d6daf93e7a5dc`

Inspection log SHA-256:

`fb1a93f75638256d5ced97709893b0560aa8dd1ebbed482810e79438acf77903`

Observed discovery:

```text
current_consumer_pattern=*/execution_authorization_v1.json
current_consumer_candidate_count=0
recursive_diagnostic_candidate_count=1
candidate_metadata_parity_count=1
finding_code=OBSERVED_SHALLOW_DISCOVERY_FALSE_NEGATIVE
```

Observed authorization path:

`datasets/kabomolefe/ag-p5-p6-execution-authorization-v1/execution_authorization_v1.json`

Authorization SHA-256:

`e9c1b58aedfccee3f36349bf063d5f1267721b8f395699a6c325304d32c20a2c`

The evidence therefore refutes missing-input, duplicate-candidate, and
authorization-metadata-drift explanations for the reproduced input set.

## Authorization lifecycle

The authorization is consumed:

```text
disposition=CONSUMED
execution_attempted=true
execution_outcome=FAILED
saved_version_id=341454766
authorization_reusable=false
```

Terminal receipt SHA-256:

`e3a3c0519fff010576f1674adf09c5dafa13b013b04e670b2510204c81f7e4b5`

The operational lifecycle files remain transient until exact copies are
preserved in the failure evidence vault. They are not reused.

## Engineering interpretation

This failure is meaningful as control-plane evidence but shallow as runtime
evidence. It proves the fail-closed authorization gate and exposes a consumer
path-contract defect. It does not exercise the exact runtime, model, workers,
P5 cache behavior, or P6 isolation.

The successor remediation should restore a producer/root-scoped authorization
transport/discovery boundary. It should not use an unscoped global filename
search as the sole fix.

## Next gate

`DESIGN_AND_MERGE_AUTHORIZATION_TRANSPORT_DISCOVERY_REMEDIATION_V1`
