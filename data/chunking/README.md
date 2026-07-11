# Nimbus Relay Chunking Candidates

This directory contains deterministic candidate outputs derived from the frozen Nimbus Relay 1.0.0 corpus.

## Candidates

```text
fixed-window-v1/
  chunks.jsonl
  manifest.json

section-aware-v1/
  chunks.jsonl
  manifest.json
```

Both candidates use:

```text
Tokenizer: lexical-whitespace-v1
Target: 96 lexical tokens
Overlap: 16 lexical tokens
Minimum fallback window: 24 lexical tokens
```

The minimum applies only when splitting an oversized body or section. Naturally short source documents and semantic sections remain short rather than being padded or merged across unrelated boundaries.

## Commands

Build both candidates deterministically:

```powershell
python -m auragateway.chunking.runner build --repo-root .
```

Verify persisted outputs against the frozen corpus:

```powershell
python -m auragateway.chunking.runner verify --repo-root .
```

## Evidence boundary

These files prove deterministic candidate construction and hash stability. They do not prove retrieval quality or select a final chunking strategy.
