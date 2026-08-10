# Exact-Runtime P5/P6 Requalification V2 Authorization Issuer

## Purpose

Provide a production-shaped, single-use authorization boundary for one governed
V2 execution without changing the V2 behavioral harness.

## Current authority

- V2 merge commit: `f81fa4209efbd4ea7fbffc130705c6b1189c61d5`
- V2 review: `550dc3dbf78e12e951cb68774321731702f1e22734588508b246a7c18c5d39b2`
- V2 record: `f814ad36d81eef259abd9374be4bf9100cac4579bfd3004d906ce69fc86cc635`
- V2 notebook: `ecf8adf4c5b2bcf557c2e10caa319f0d4b707fd7a24bd36c31525ee60b9d548a`
- V2 runtime script: `599b0395952abb0666e48890d4f25ad9050260837134a4c53716943a3d391df0`
- transport design: `679c11a020e7381417f9f2fe0087f72ee10e9a454703609a1ab48c70da57d3bb`

## Key control

The issuer does not write live authority until the candidate authorization bytes
round-trip through the current CPU-only control-package producer and validator.
This closes the exact producer/consumer parity gap that caused V1 to consume an
authorization before runtime installation.

## Static tranche non-claims

No live authorization is issued. No Kaggle, runtime, model, worker, P5, or P6
execution is performed. Pilot and final measured A/B/C authority remain false.
