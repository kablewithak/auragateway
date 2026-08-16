# Runbook: B-vs-D Cumulative-Length-Locked Marker-Diversified Differential Design V1

This runbook covers the design tranche only.

## Candidate boundary

1. `.gitattributes`
2. `src/auragateway/local_abc/b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1.py`
3. `tests/unit/local_abc/test_b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1.py`
4. `benchmarks/local_abc/auragateway_b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1.json`
5. `benchmarks/local_abc/evidence/b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1/comparator_feasibility_v2.json`
6. `benchmarks/local_abc/evidence/b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1/semantic_review_candidate_v1.json`
7. `benchmarks/local_abc/evidence/b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1/design_freeze_candidate_v1.json`
8. `docs/adr/2026-08-16-local-abc-b-vs-d-cumulative-length-locked-marker-diversified-differential-v1.md`
9. `docs/reports/AuraGateway_B_Vs_D_Cumulative_Length_Locked_Marker_Diversified_Differential_Design_V1.md`
10. `docs/runbooks/local_abc_b_vs_d_cumulative_length_locked_marker_diversified_differential_design_v1.md`

## Ownership

The design JSON is producer-owned and must not be manually edited.

The three offline evidence JSON files are immutable byte-for-byte qualification
evidence. They must be installed from the bound candidate bundle and must not be
rewritten, reserialized, normalized, or manually edited.

`.gitattributes` is a complete-file governed replacement built from the exact
inspected predecessor bytes plus the frozen B-vs-D preservation stanza.

The producer, focused test, ADR, report, and runbook are authored complete files.
Do not patch or search/replace them after candidate binding.

## Permitted

Local static authority validation, deterministic design-record generation/check,
candidate formatting/lint/type/test validation, full repository pytest, governed
immutable-lineage typecheck validation, exact candidate-boundary inspection,
exact staging, staged byte-identity validation, commit, push, PR review, and merge.

## Prohibited

Kaggle/GPU execution, model loading, worker startup, model requests, live
authorization, threshold search, P5/P6 requalification, measured North-Star A/B/C
execution, mutation of preserved qualification evidence, and reinterpretation of
mixed or B-anchor-nonreproducing results.

## Validation order

1. governed Ruff format on changed mutable Python;
2. governed Ruff lint on changed mutable Python;
3. producer compilation;
4. focused mypy for producer and focused test;
5. producer `--write`;
6. producer `--check`;
7. verify generated design record is byte-stable across `--check`;
8. focused pytest;
9. full repository pytest;
10. immutable-lineage policy validation;
11. governed immutable-lineage typecheck run;
12. exact ten-path candidate boundary;
13. inspect diff and repository state;
14. exact staging;
15. staged diff and byte-identity validation.

Repository-wide Ruff is not the governed default tranche gate.

## Scientific gates

The implementation tranche must preserve:

- B and D at exactly 899 prompt tokens;
- exact B and D token SHA-256 identities;
- exact B and D request-payload SHA-256 identities;
- 24 segments per condition;
- the exact B sentence template;
- D as 24 reviewed marker-only variants;
- the complete 25-point cumulative prompt-token profile;
- +34 prompt tokens per segment addition;
- no text-segment-boundary/token-boundary assumption;
- the frozen runtime/model/generation/composition contract;
- fresh worker per observation;
- order `B,D,D,B,B,D`;
- three observations per condition;
- zero hidden retries and zero replacements;
- B anchor validity before D interpretation;
- the predeclared interpretation matrix and non-claims.

No execution authorization may be inferred from design or implementation merge.

## Next gate

`IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1`
