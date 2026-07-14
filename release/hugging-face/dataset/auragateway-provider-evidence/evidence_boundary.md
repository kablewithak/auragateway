# Evidence Boundary

## Included

- sanitized provider-lineage summaries;
- numeric attempt and success accounting;
- safe HTTP status and failure labels;
- source paths and SHA-256 manifests;
- explicit permitted and blocked claims.

## Excluded

- API keys and authorization-header values;
- raw prompts and protected prompt bundles;
- raw provider response bodies;
- protected journals, parsed responses, and terminal receipts;
- customer data and private documents;
- live inference, remote API calls, or credential loading.

## Interpretation rule

An implemented adapter is not live provider evidence. A successful provider response is not
necessarily cache evidence. An HTTP error is not a model-quality or cache-performance result.
