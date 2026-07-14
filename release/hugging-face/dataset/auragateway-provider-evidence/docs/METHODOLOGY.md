# Methodology

AuraGateway evaluated whether its provider boundary could support a controlled cache-aware runtime
comparison. It separated adapter correctness, fixture semantics, live provider evidence, and claim
eligibility.

## Groq lineage

Two authorized raw-wire calls returned successful completions. The required nested cached-token
field was absent from both raw responses. The lineage closed because repeating identical calls
without a new hypothesis would have been evidence fishing.

## OpenRouter / Hy3 lineage

A metadata-only preflight passed. A one-time cold/warm capability probe was then authorized through
a bounded execution harness. The first cold completion request returned HTTP 401 before successful
model inference. No generation metadata, route identity, cache telemetry, or warm request followed.
The authorization was consumed and the lineage was not resumed or rerun.

## Comparison gate

The A/B/C benchmark required numeric cache telemetry and defensible controlled cache-use evidence.
Neither provider lineage satisfied that gate, so the measured comparison remained blocked.
