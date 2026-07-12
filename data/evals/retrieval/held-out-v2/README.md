# Nimbus Relay Held-Out Retrieval v2

Held-out v2 is the protected post-remediation evaluation set for Gate 1.

Controls:

- 12 accepted cases and 5 rejected proposals;
- frozen before remediated candidate scoring;
- no exact query reuse from development v2 or held-out v1;
- unchanged selection thresholds and top-k five;
- authored metadata filters only;
- held-out v1 evidence remains immutable;
- candidate results, scorecards, decision, and retrieval freeze are hash-bound.

Gate 1 passed. The frozen retrieval configuration is recorded at:

```text
data/retrieval/frozen-v1/manifest.json
```

The retrieval freeze does not permit measured runtime execution.
