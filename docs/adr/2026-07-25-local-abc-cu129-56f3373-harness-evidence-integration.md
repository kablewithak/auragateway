# ADR: Integrate the 56f3373 CUDA 12.9 harness evidence

## Decision

`CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED`

Promote the exact harness materialized from `56f33739babb80d843fef1ad8f7f1223f3d10d14` as the active
qualification input.

## Bound authority

- directory SHA-256: `778333c57b02d74be2c18962d7e75b560d269fc9b6c6b611d043304c855e3477`
- file count: `1084`
- total bytes: `10970203`
- mounted path: `/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/ag_harness_materializer_cu129_v1_output/auragateway_qualification_harness_56f3373_v1`
- materializer saved version: `337848035`
- inspection saved version: `337858124`
- inspection evidence ZIP SHA-256: `c0832dde010835401dc11ff654b864c3db62e9c895c18265ea881d154eeaae1e`

## Controls

The materializer and inspection ran with Accelerator None, Internet Off,
zero package installation, zero model requests, and no authorization.

## Next gate

`fresh_cu129_authorization_issuance_implementation`

## Non-claims

CUDA/vLLM execution, worker health, model execution, A/B/C measurement,
cost reduction, and production readiness are not claimed.
