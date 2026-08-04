# AuraGateway P3-P6 Runtime Diagnostic Execution Authorization V4

## Purpose

Implement the repository-only issuer for one governed P3-P6 Runtime Diagnostic
V4 attempt. The issuer is separate from the V4 runtime implementation and from
live authorization issuance.

## Bound implementation

- merge commit: `603f11bf10336222d289d56d29a18d3e9c705c68`;
- implementation feature commit: `6c3d1865f563af3dae60c0f79345ffe18e21e092`;
- notebook SHA-256:
  `92984ab474d495a443ab504f400c38782df1ee0c1d1b65646e9444b311a46dd7`;
- runtime-script SHA-256:
  `72e1daad1883e4bd1456ada15e073dbb252753b166b4cc250f591f71171679a3`;
- wrapper-code SHA-256:
  `cfef877ff8698f40aec1a0a4c7a6ac94e762085dfdfde88994d6da341438cd4f`;
- model snapshot SHA-256:
  `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`.

## Authorization controls

The issuer requires synchronized clean `main`, exact implementation bindings,
explicit operator confirmation, a maximum 240-minute validity window,
non-overwriting issuance, untracked transient artifacts, single use, and
mandatory terminal consumption.

The authorization binds the V4 line-local backend-marker contract, capture
finalization, worker/GPU identity, structured teardown, runtime-source
identity, privacy controls, zero network access, zero hidden retries, zero A/B/C
trajectories, and zero external spend.

## Action ceiling

- Kaggle sessions: 1;
- runtime installations: 1;
- import-closure probes: 1;
- model loads: 3;
- worker starts: 3;
- model requests: 5;
- output tokens per request: 32;
- benchmark trajectories: 0;
- external network requests: 0;
- hidden retries: 0;
- external spend: 0.

## Non-claims

This implementation does not issue live authority, execute Kaggle, prove P3-P6
runtime success, establish request-level attention execution, prove cache or
worker isolation, or establish deployment or production readiness.
