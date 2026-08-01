# AuraGateway P3-P6 Runtime Diagnostic Execution Authorization V2

## Decision

Implement a repository-native, single-use authorization issuer for the merged V2 runtime diagnostic.

## Bound implementation

- merged main: `87f2d4e08043c0c6ec5dee93d14c0523f531e8fe`
- implementation feature: `d6837f057790279727fbb71177a615a0a12928ef`
- implementation record SHA-256: `e6761fa50f06989d0cfaa5e509669b0776a5d3e494990d6d89219c232c79a140`
- notebook SHA-256: `912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd`
- model snapshot SHA-256: `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`
- backend: `TRITON_ATTN`
- scope: `P3_P6_RUNTIME_DIAGNOSTIC_V2`

## Budget

One Kaggle session, one runtime installation attempt, three model loads, three worker starts, five model requests, and at most 32 output tokens per request. Benchmark trajectories, external network requests, hidden retries and external spend remain zero.

## V2 evidence obligations

The governed attempt must retain the runtime installation report, bounded subprocess diagnostics, deterministic terminal reports for P3-P6, scratch cleanup evidence and an allowlisted evidence archive no larger than 2 MiB.

## Lifecycle

The issuer supports static generation, implementation validation, explicit issuance, live verification and terminal consumption. PASSED, FAILED and INTERRUPTED all consume the authority. Unchanged replay is not authorized.

## Non-claims

This implementation does not authorize or perform runtime execution. It does not confirm the historical V1 pip root cause, successful V2 installation, P3 startup, P4 inference, P5 cache behavior, P6 isolation, deployment readiness or production readiness.
