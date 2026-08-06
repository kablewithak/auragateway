# AuraGateway P4 Import Differential Inspection V1

- Inspection ID: `auragateway-p4-import-differential-inspection-v1`
- Primary classification: `NATIVE_LIBRARY_SEARCH_PATH_SUPPORTED`
- Supported classifications: `NATIVE_LIBRARY_SEARCH_PATH_SUPPORTED`
- Exact P4 probes failed: `cumulative:p4_order, cumulative:v5_order, individual:torch, individual:vllm, individual:vllm.model_executor.models.registry`
- Python: `3.12.13` at `/usr/bin/python3`
- T4 x2 realized: `True`
- Exact wheelhouse manifest closure: `True`
- P4-style install status: `PASSED`
- P4 target exactly matches lock: `True`

## Safety boundary

- No model was loaded.
- No worker was started.
- No inference or benchmark request was made.
- No external network access was permitted.
- No customer data or credentials were used.
- No solution is authorized by this notebook.

## Next gate

`review_inspection_evidence_then_select_smallest_fix`
