# ADR: Accept preflight-v3 exact-runtime resolution reconnaissance and freeze lock V1

Date: 2026-08-08

## Status

Accepted candidate for merge.

## Evidence

Kaggle saved version `341073810` completed with:

- status `COMPLETED_PENDING_REVIEW`;
- 196 resolved distributions;
- five explicit hosts;
- exact vLLM `0.25.1+cu129`;
- exact preflight-v3 vLLM SHA `9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`;
- torch `2.11.0+cu129`;
- zero package installation;
- zero retained wheel files;
- zero model loads and requests;
- zero benchmark trajectories;
- zero credentials/customer data/external spend.

The saved executed notebook has a different whole-file SHA because Kaggle added execution
outputs and papermill metadata. Its markdown source and executable code source are byte-for-byte
equal to the committed repository notebook source.

Repository notebook SHA:

`d184f9b8ab61554ceed1bd31a384fc2cb50322ca225644dab5a508c52ea0b78b`

Executed notebook SHA:

`d9bdd69e3766204af47b5b77de0cad854776491d9a8d7be9afab7b85527ac8e6`

Executable code-cell source SHA:

`fe9650606705ed851049150ea1b6b528c247a3302b0bee616525fda02173244d`

Evidence ZIP SHA:

`144661d3bcf908ec3ca98c372b50c01234f98e660762f3ab361ed99ce6c9decd`

Execution log SHA:

`045e13bc03dbf9966189f385f4c39aaa0daae6e72a49a9bfdc190e4639507672`

## Decision

`ACCEPT_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_AND_FREEZE_LOCK`

Freeze the 196 exact wheel identities and the five explicit host boundaries into a new
preflight-v3 resolution lock.

This lock is independent of and does not replace historical evidence for the older 0.19.1
runtime.

## Consequence

The next engineering gate is to implement a new exact-runtime wheelhouse materializer driven
only by this lock. The materializer must not re-resolve dependencies.

## Non-claims

The runtime is not yet materialized, offline verified, P5/P6 requalified, or authorized for
variance-pilot/final measured execution.
