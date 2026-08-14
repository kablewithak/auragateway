# Runbook: P4/P5 Token-Count-Matched Context-Structure Differential Design V1

This runbook covers the design tranche only.

## Candidate boundary

1. `src/auragateway/local_abc/p4_p5_token_count_matched_context_structure_differential_design_v1.py`
2. `tests/unit/local_abc/test_p4_p5_token_count_matched_context_structure_differential_design_v1.py`
3. `benchmarks/local_abc/auragateway_p4_p5_token_count_matched_context_structure_differential_design_v1.json`
4. `benchmarks/local_abc/evidence/token_count_matched_context_structure_differential_design_v1/tokenizer_feasibility_receipt_v2.json`
5. `benchmarks/local_abc/evidence/token_count_matched_context_structure_differential_design_v1/comparator_feasibility_v2.json`
6. `benchmarks/local_abc/evidence/token_count_matched_context_structure_differential_design_v1/design_freeze_candidate_v1.json`
7. `docs/adr/2026-08-15-local-abc-p4-p5-token-count-matched-context-structure-differential-v1.md`
8. `docs/reports/AuraGateway_P4_P5_Token_Count_Matched_Context_Structure_Differential_Design_V1.md`
9. `docs/runbooks/local_abc_p4_p5_token_count_matched_context_structure_differential_design_v1.md`

## Ownership

The design JSON is producer-owned and must not be manually edited.

The three preserved offline evidence JSON files are immutable byte-for-byte
qualification evidence. They must be installed from the qualified candidate
bundle and must not be rewritten, reserialized, or normalized.

The producer, focused test, ADR, report, and runbook are authored complete files.
Do not patch or search/replace them after candidate binding.

## Permitted

Local static authority validation, deterministic design record generation/check,
candidate formatting/lint/type/test validation, full repository pytest, governed
immutable-lineage typecheck validation, exact candidate-boundary inspection,
exact staging, and staged byte-identity validation.

## Prohibited

Kaggle/GPU execution, model loading, worker startup, model requests, live
authorization, threshold search, P5/P6 requalification, measured North-Star A/B/C
execution, mutation of the preserved qualification evidence, and any reinterpretation
of mixed or anchor-nonreproducing results.

## Validation order

1. candidate Ruff format;
2. candidate Ruff lint;
3. producer compilation;
4. focused mypy for producer and focused test;
5. producer `--write`;
6. producer `--check`;
7. verify the generated design record is byte-stable across `--check`;
8. focused pytest;
9. full repository pytest;
10. immutable-lineage policy validation;
11. governed immutable-lineage typecheck run;
12. exact nine-path candidate boundary;
13. inspect diff and repository state;
14. exact staging;
15. staged diff and byte-identity validation.

Repository-wide Ruff is not the governed default tranche gate.

## Scientific gates

The implementation tranche must preserve:

- A/B/C at exactly 899 prompt tokens;
- the three frozen token SHA-256 identities;
- 24 segments per condition;
- A and B as one repeated segment each;
- C as 24 distinct neutral segments;
- the frozen four-message topology and suffix;
- fresh worker per observation;
- the nine-observation position-balanced order;
- zero hidden retries and zero replacement observations;
- the anchor validity rule;
- the predeclared interpretation matrix and non-claims.

No execution authorization may be inferred from design or implementation merge.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1`
