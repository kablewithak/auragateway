# Diagnostic Episode Assets

This directory contains the frozen Nimbus Relay multi-turn diagnostic benchmark assets.

```text
functional-v1/accepted_episodes.json   18 accepted four-turn episodes
functional-v1/rejected_proposals.json  rejected proposals with retained reasons
runtime-v1/selection.json              six-episode runtime microbenchmark subset
blinded_review_protocol.json           prepared review and adjudication policy
manifest.json                          hash-bound asset inventory
freeze_record.json                     Gate 2 freeze decision
```

The accepted assets contain synthetic raw user messages. They may be used only inside protected benchmark execution and review boundaries. Public traces may retain episode IDs, decisions, validation outcomes, failure labels, and hashes, but not raw conversation content.

Build or verify the deterministic manifest:

```powershell
python -m auragateway.evals.episode_runner build --repo-root .
python -m auragateway.evals.episode_runner verify --repo-root .
```
