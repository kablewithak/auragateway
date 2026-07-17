# Local A/B/C Action-Extraction Requalification Notebook Qualification v2

**Version:** 2.0.0  
**Date:** 2026-07-17  
**State:** Qualified, not executed  
**Activation merge:** `639e21a63eb8a37d0221c2630b756203d1270f62`  
**External spend:** R0 / $0

## Notebook identity

```text
notebook=notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb
notebook_sha256=e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9
notebook_code_source_sha256=26f7f46475e2746e6e099210475b18b08a1abb90994759394cc2c11d39f1c499
notebook_code_cell_count=12
notebook_has_saved_execution_state=false
notebook_cells_compile=true
```

## Binding identity

```text
binding=benchmarks/local_abc/reconcile_balance_extraction_requalification_notebook_binding_v2.json
binding_sha256=476d3be54fc34cafacba4bcdef07eaa1213a426df0496e4908bc8078b7edac88
authorization_sha256=a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899
activation_manifest_sha256=42ce858a657afe0fd6d4eb7a5e0846fedf1b9c41ab883826acf08712a94b0526
```

## Source authority

```text
activation_source_blob=aa1afdf0acc52bd5bf2a3e0d7fb9c6b71f5fd342
authorization_json_blob=3f84ebc86450dc8e2e70c2d457593bf9b10136bf
activation_manifest_blob=142133a745dcc69d64ecae81811c8d2cb377b909
```

## Fixed execution constitution

```text
case_count=16
request_count=16
request_attempts_per_case=1
hidden_retry_count=0
repair_attempt_count=0
replacement_request_count=0
required_exact_operand_matches=16
required_exact_final_answer_matches=16
cache_measurement_in_scope=false
full_measured_rerun_authorized=false
```

## Notebook behavior

The notebook:

1. verifies the attached notebook and binding ZIP;
2. checks out the exact activation merge;
3. qualifies repository imports from that checkout;
4. loads the complete activation package and confirms the authorization is unused;
5. creates an isolated pip-less virtual environment;
6. installs the exact CUDA 12.9 Torch stack and authorized vLLM wheel;
7. performs a compiled vLLM import probe;
8. verifies the exact model snapshot;
9. freezes a hash-only 16-request schedule using remediation v2;
10. runs one request per case with no retry or repair;
11. scans retained evidence for forbidden keys and raw prompts;
12. packages a privacy-safe evidence archive.

## Validation performed

- notebook bytes match the binding;
- all code cells compile;
- no code cell has outputs or execution counts;
- activation, authorization, and manifest lineage match PR #88;
- v2 prompt normalization and response schema are used;
- the complete 16-case order is preserved;
- privacy, cache non-claims, and zero-spend controls remain enforced.

## Non-claims

- No model request has been made.
- No GPU execution has occurred.
- Neither historical semantic failure has been re-measured.
- No quality improvement is claimed.
- Cache reuse, latency, and cost savings remain unmeasured.
- The full A/B/C benchmark remains unauthorized.
- Production readiness is not claimed.
