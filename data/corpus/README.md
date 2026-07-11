# Nimbus Relay Corpus

This directory contains the typed source inventory for AuraGateway's synthetic Nimbus Relay API corpus.

## Current state

```text
Inventory: planned and locally validated
Authored documents: 0 / 30
Retrieval configuration: not started
Gate 1: not passed
```

`source_inventory.json` defines the 30 planned sources and diagnostic quotas before document authoring begins.

## Validation

```powershell
python -m auragateway.corpus.validate .\data\corpus\source_inventory.json
```

A valid inventory confirms the planned source set satisfies the PRD minimums. It does not confirm that the document files exist or that retrieval quality is acceptable.
