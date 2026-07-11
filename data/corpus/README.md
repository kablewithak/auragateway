# Nimbus Relay Synthetic Corpus

This directory contains the frozen synthetic documentation corpus used by AuraGateway.

## Controls

- `source_inventory.json` defines the typed source inventory and diagnostic labels.
- `source_manifest.json` records the SHA-256 and byte count of every source document.
- `corpus_freeze_record.json` records the inventory and manifest fingerprints.
- `documents/` contains exactly 30 authored Markdown and JSON sources.

The corpus includes deliberate stale, conflicting, incomplete, near-duplicate, and version-sensitive evidence. These are diagnostic fixtures, not authoring defects to normalize away.

## Verification

```powershell
python -m auragateway.corpus.freeze verify --repo-root .
```

A changed document, metadata mismatch, missing or extra file, malformed JSON source, stale-source warning omission, incomplete-source gap omission, or hash mismatch fails verification.

The corpus is synthetic. Customer data, production logs, secrets, and direct personal identifiers are prohibited.
