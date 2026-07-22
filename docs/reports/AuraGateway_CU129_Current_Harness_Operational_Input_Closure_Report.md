# AuraGateway CUDA 12.9 Current Harness Operational Input Closure Report

```text
operational_input_closure=PASSED
source_commit=426f57dd11dddc2fb8e5a703721c2189abc7a0ff
harness_directory_sha256=c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6
harness_file_count=1299
harness_total_bytes=11632357
runtime_package_count=176
manifest_sha256=f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a
materialization_record_sha256=284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a
runtime_adapter_sha256=aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba
launcher_source_sha256=7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16
launcher_notebook_sha256=7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9
inspection_evidence_zip_sha256=2d2f6afdd53787f6b3977e799dff441f9023a3c265ddf65d35855c5b62ad90d8
authorization_issued=false
model_requests_performed=0
```

## Materialization

Kaggle auto-expanded `ag-harness-426f57d-v1.zip`. The bounded recovery materializer validated every
expanded file against the frozen source inventory, reconstructed the deterministic ZIP, matched archive
SHA-256 `3be4a26c252eebb136b9bedfa15fc897070b3b59d14a775f536a8132fb6663df`,
and emitted the expected source tree plus sibling receipt.

Materializer saved version: `337034643`.

## Metadata-only inspection

Inspection saved version: `337035826`.

The inspection verified:

- the current harness and sibling receipt under one producer root;
- exact source commit, directory digest, file count, and byte count;
- current runtime adapter SHA-256 and explicit inequality from the historical adapter;
- exact 176-wheel CUDA 12.9 topology and 182-entry checksum manifest;
- exact runtime control identities and resolution lock;
- unchanged model snapshot authority without loading weights;
- source compilation for the current adapter, execution contracts, and CUDA runtime module;
- zero package installation, GPU execution, worker startup, model requests, and authorization.

Wheel payloads were not rehashed during this metadata gate. Filenames and sizes were checked against
the already consumed immutable checksum manifest. Full runtime execution remains a later authorized GPU
qualification boundary.

## Decision

The active harness may migrate from `be1bfadd` to the inspected `426f57d` source. The next gate is
`fresh_cu129_authorization_issuance_implementation`.
