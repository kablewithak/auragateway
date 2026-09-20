# ADR: J7L Groq Strict-Schema Token Accounting Probe V1

**Status:** Proposed for activation only after non-live review acceptance
**Date:** 2026-09-20
**Decision ID:** `j7l-groq-schema-accounting-probe-v1`

## Context

AuraGateway's model-derived J7L successor requires a zero-spend reference judge. The current
Groq candidate is `openai/gpt-oss-20b`. Local GPT-OSS tokenization measured the largest exact
candidate message at 7,448 tokens. A conservative representation that also serializes the strict
JSON Schema measured 7,916 tokens; reserving 384 output tokens produces an 8,300-token envelope.
The observed organization limit is 8,000 tokens per minute.

The unresolved question is narrower than model capability: whether Groq's strict
`response_format` contributes to provider-reported prompt-token usage and therefore creates
evidence that the current J7L request shape cannot fit the observed R0 token boundary.

## Decision

Before any J7L reference request, run a separately activated two-call synthetic accounting probe.

Both calls use byte-identical synthetic messages. Call A omits `response_format`. Call B adds the
frozen strict JSON Schema. The experiment observes `usage.prompt_tokens`, completion usage, and
rate-limit headers when returned.

The non-live review does not authorize those calls. Activation and execution remain separate.

## Interpretation

If Call B reports more prompt tokens than Call A, structured-output machinery is visible in
provider-reported prompt usage. That is sufficient to reject the current Groq J7L request shape
under the observed 8,000 TPM organization boundary.

If both prompt-token counts are equal, the result does not prove that the schema is free for rate
limiting. It only shows that the schema is not reflected in `usage.prompt_tokens`; a separate
full-size synthetic qualification is then required.

A negative prompt-token delta is invalid for interpretation and requires investigation.

## Alternatives rejected

1. Run a frozen J7L case directly: rejected because provider accounting is unresolved and a
   development case must not be consumed for infrastructure qualification.
2. Assume serialized schema bytes count exactly like message tokens: rejected because provider
   documentation does not establish that accounting rule.
3. Assume schema bytes are free because `response_format` is separate: rejected for the same
   reason.
4. Upgrade or pay for more quota: rejected because the governing resource posture remains R0.

## Consequences

This probe adds at most two synthetic provider calls after separate activation, no automatic
retry, no resume, no rerun, and no paid fallback. A conclusive positive delta can close the Groq
fork early; an equal delta narrows the uncertainty without authorizing J7L.
