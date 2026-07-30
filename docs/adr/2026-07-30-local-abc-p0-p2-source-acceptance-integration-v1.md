# ADR: Bind Accepted P0-P2 Source Evidence to the Execution Launcher

## Status

Accepted for repository integration. GPU execution remains prohibited until this
integration is merged and synchronized to clean `main`.

## Context

Corrected source materialization and metadata-only inspection succeeded on Kaggle.
The current launcher producer still uses pending placeholders for both saved-version
identities, so its generated notebook cannot serve as current execution authority.

## Decision

1. Preserve the successful materializer and inspection evidence under an immutable
   repository evidence boundary.
2. Validate logs, ZIP member sets, canonical JSON, cross-archive byte equality, source
   identities, saved-version IDs, and zero-execution safety fields through a typed
   Pydantic contract.
3. Bind materializer saved version `339075357` and inspection saved version
   `339077364`.
4. Preserve the exact operator-supplied Kaggle saved-version locators and bind their numeric `scriptVersionId` values.
5. Make the launcher producer validate the acceptance record before generation.
6. Bind the acceptance-record SHA-256 into the generated launcher record and notebook
   metadata.
7. Regenerate the launcher notebook and launcher record through their owning producer.

## Consequences

The launcher notebook and launcher record identities change. The source materializer,
source inspection notebook, diagnostic notebook, diagnostic request, and diagnostic
implementation bytes remain unchanged.

## Safety

This integration performs no Kaggle execution, GPU execution, runtime installation,
diagnostic execution, model load, worker start, model request, benchmark trajectory,
credential use, customer-data use, authorization issuance, or external spend.

## Non-claims

This ADR does not prove CUDA linking, `cuInit(0)`, Triton compatibility, environment
qualification, worker readiness, cache behavior, inference, measured A/B/C effects,
deployment, or production readiness.
