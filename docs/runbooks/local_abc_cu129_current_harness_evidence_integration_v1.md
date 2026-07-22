# Current CUDA 12.9 harness evidence integration runbook v1

## Frozen external evidence

```text
materializer notebook: ag-harness-materializer-cu129-v1
materializer saved version: 337034643
inspection notebook: ag-harness-input-inspection-cu129-v1
inspection saved version: 337035826
inspection evidence ZIP SHA-256: 2d2f6afdd53787f6b3977e799dff441f9023a3c265ddf65d35855c5b62ad90d8
materialization receipt SHA-256: 07d81dbea5b5ed24d0786c0ee16782129e163834254c095262944baaf5c59db2
```

Do not rerun or overwrite either successful notebook version.

## Active current harness

```text
source commit: 426f57dd11dddc2fb8e5a703721c2189abc7a0ff
mounted path: /kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/ag_harness_materializer_cu129_v1_output/auragateway_qualification_harness_426f57d_v1
directory SHA-256: c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6
file count: 1299
total bytes: 11632357
active manifest SHA-256: f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a
materialization record SHA-256: 284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a
runtime adapter SHA-256: aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba
launcher source SHA-256: 7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16
launcher notebook SHA-256: 7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9
```

## Repository validation

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_harness_evidence_integration --repo-root .
python -m auragateway.local_abc.full_abc_local_environment_qualification_kaggle_launcher verify-launcher --repo-root .
```

Required output includes:

```text
status=CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED
operational_input_closure=PASSED
authorization_source_binding_policy=CONTROL_PACKAGE_AUTHORIZATION_PARITY
authorization_issued=false
model_requests_performed=0
next_gate=fresh_cu129_authorization_issuance_implementation
```

## Fresh authorization boundary

This integration does not issue authorization. The next implementation must bind the exact
post-integration merge commit, current manifest fingerprint, current materialization record, current
runtime adapter, current execution request, and dynamic launcher-control authorization-source parity.

The authorization remains one session, two workers, at most eight model requests, at most 32 output
tokens per request, zero benchmark trajectory requests, no network, no credentials, no customer data,
and zero external spend.
