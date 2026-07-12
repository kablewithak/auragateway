# Nimbus Relay held-out retrieval set v1

This directory contains the frozen Gate 1 held-out retrieval evidence.

## Inputs frozen before scoring

- `accepted_cases.json`: 12 accepted diagnostic cases
- `rejected_cases.json`: 5 rejected proposals with reasons
- `freeze_record.json`: content hashes and authoring-order declaration
- `policy.json`: two finalists and the held-out decision rule

## Generated evidence

- `<retriever-config-id>/case_results.jsonl`
- `<retriever-config-id>/scorecard.json`
- `decision.json`

The current decision is blocked. Therefore `data/retrieval/frozen-v1/manifest.json` must not exist.

## Verification

```powershell
python -m auragateway.evals.heldout_runner verify --repo-root .
```

Do not edit held-out v1 after seeing candidate results. Remediation requires a new held-out version.
