# Runbook: P4/P5 Cache-Context Repetition Differential Design V1

This runbook covers the design tranche only.

## Candidate boundary

1. `src/auragateway/local_abc/p4_p5_cache_context_repetition_differential_design_v1.py`
2. `tests/unit/local_abc/test_p4_p5_cache_context_repetition_differential_design_v1.py`
3. `benchmarks/local_abc/auragateway_p4_p5_cache_context_repetition_differential_design_v1.json`
4. `docs/adr/2026-08-13-local-abc-p4-p5-cache-context-repetition-differential-v1.md`
5. `docs/reports/AuraGateway_P4_P5_Cache_Context_Repetition_Differential_Design_V1.md`
6. `docs/runbooks/local_abc_p4_p5_cache_context_repetition_differential_design_v1.md`

## Permitted

Local static authority validation, deterministic record generation/check,
candidate formatting/lint/type/test validation, full repository pytest, governed
immutable-lineage typecheck validation, exact staging, and staged byte-identity
validation.

## Prohibited

Kaggle/GPU execution, model loading, worker startup, model requests, live
authorization, threshold search, assistant/topology experiment, P5/P6
requalification, and measured A/B/C execution.

## Validation order

1. candidate Ruff format;
2. candidate Ruff lint;
3. producer compilation;
4. focused mypy;
5. producer `--write`;
6. producer `--check`;
7. focused pytest;
8. full repository pytest;
9. governed immutable-lineage typecheck gate;
10. exact six-path candidate boundary;
11. exact staging;
12. staged diff and byte-identity validation.

Repository-wide Ruff is not the governed default tranche gate.

Generated JSON is producer-owned and must not be manually edited.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1`
