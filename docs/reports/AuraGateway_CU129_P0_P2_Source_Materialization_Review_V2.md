# AuraGateway P0-P2 Source Materialization Review V2

## Proof state

```text
decision: CLEAN_GLOBAL_REBUILD
previous candidate: REJECTED_LOCAL_UNCOMMITTED
implementation: PRODUCTION_SHAPED_LOCAL_TOOLCHAIN
runtime execution: NOT PERFORMED
Kaggle execution: NOT PERFORMED
```

## Failure diagnosis

The V1 candidate treated executable notebook programs as collections of quoted
source fragments. Repairing generated notebook lint failures moved the same
failure into the producer, where physical lines grew to hundreds of characters.
This was a local-minimum loop, not a sequence of independent defects.

The V2 design removes that representation entirely.

## V2 architecture

```text
exact merged source artifacts
        |
        v
deterministic fixed-metadata ZIP bundle
        |
        v
fixed-width base64 chunks
        |
        v
ordinary materializer template
        |
        v
unexecuted CPU-only materializer notebook

successful notebook output dataset
        |
        v
ordinary metadata-inspection template
        |
        v
unexecuted input-inspection notebook
```

## Authored repository files

```text
benchmarks/local_abc/
  auragateway_cu129_p0_p2_source_materialization_review_v2.json

docs/adr/
  2026-07-29-local-abc-cu129-p0-p2-source-materialization-v2.md

docs/reports/
  AuraGateway_CU129_P0_P2_Source_Materialization_Review_V2.md

docs/runbooks/
  local_abc_cu129_p0_p2_source_materialization_v2.md

src/auragateway/local_abc/
  full_abc_local_environment_qualification_
  cu129_p0_p2_source_materialization_v2.py

src/auragateway/local_abc/templates/
  p0_p2_source_materializer_v2.py.tmpl
  p0_p2_source_input_inspection_v2.py.tmpl

tests/unit/local_abc/
  test_full_abc_local_environment_qualification_
  cu129_p0_p2_source_materialization_v2.py
```

## Generated repository files

```text
benchmarks/local_abc/
  auragateway_cu129_p0_p2_source_materialization_toolchain_v2.json

notebooks/
  auragateway_cu129_p0_p2_source_materializer_v2.ipynb
  auragateway_cu129_p0_p2_source_input_inspection_v2.ipynb
```

## Source bundle contract

The in-memory bundle contains one canonical manifest and exactly three source
artifacts. The bundle is not committed as a separate repository file because its
bytes are embedded in the generated materializer notebook and bound by the
toolchain record.

The generator validates:

- exact repository paths;
- exact output basenames;
- exact byte sizes;
- exact SHA-256 identities;
- safe ZIP member names;
- fixed timestamps;
- fixed regular-file modes;
- sorted member order;
- two-build byte equality.

## Generated-code contract

Both code cells are generated from ordinary template files.

Required gates:

```text
Python compile: pass
maximum line length: <= 100
nested lines.extend program construction: absent
subprocess/model/worker execution source: absent
outputs: absent
execution counts: absent
two-generation byte parity: pass
```

## Materializer contract

The CPU-only materializer:

1. decodes the fixed-width embedded bundle;
2. validates the outer bundle SHA-256;
3. validates safe ZIP members;
4. validates the canonical bundle manifest;
5. validates all source sizes and identities;
6. writes exact source files to a staging directory;
7. writes canonical inventory and checksum controls;
8. writes a typed receipt-shaped JSON record;
9. atomically promotes the staging directory.

It refuses to overwrite an existing output or staging directory.

## Inspection contract

The metadata-only inspection notebook:

1. discovers exactly one identity-shaped materializer output;
2. validates receipt authority;
3. validates the exact source inventory hash;
4. validates each mounted source file;
5. verifies the reviewed diagnostic notebook is unexecuted;
6. emits one report and one bounded evidence ZIP.

## Regression suite

The focused suite covers:

- Kaggle resource-name limits;
- deterministic source-bundle bytes;
- fixed ZIP members and timestamps;
- generated-source compilation;
- generated-source line-length policy;
- no notebook outputs or execution counts;
- fixed-width base64 chunks;
- source identity drift rejection;
- unsafe output-name rejection;
- deterministic notebook generation;
- review-contract completeness;
- end-to-end generate and validate parity.

Local isolated result:

```text
11 passed
```

## Maintainability assessment

The redesign is easier after the next three requirements because data,
materializer behavior, inspection behavior, and generator behavior now have
separate files and contracts.

No whitespace-sensitive source surgery is required.

## Commercial translation

This is a strong proof asset for an **AI System Evaluation Audit** or
**Agent Harness Hardening Sprint**.

Buyer pain:

```text
generated AI infrastructure passes once but cannot be safely regenerated
```

Failure mode:

```text
hidden representation coupling between source, generator, formatter, and output
```

Proof asset:

```text
deterministic source bundle
typed identity contract
safe extraction
generated-code gates
byte-parity validation
failure-budget discipline
```

Acceptance criterion:

```text
the same source commit deterministically regenerates the same inspected
materialization notebooks without manual repair
```

## Non-claims

This tranche does not establish:

- successful Kaggle materialization;
- successful mounted-input inspection;
- a published Kaggle Dataset version;
- P0, P1, or P2 execution;
- linker viability;
- Triton viability;
- explicit `TRITON_ATTN` realization;
- model inference;
- cache telemetry;
- environment qualification;
- measured A/B/C effects;
- deployment;
- production readiness.

## Next gate

```text
execute_cpu_only_p0_p2_source_materializer_v2
```
