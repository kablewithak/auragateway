# AuraGateway Batch 06 Diagnostic Prompt Cohort Materialization

**Fixture ID:** `batch-06-diagnostic-prompt-fixtures-v1`  
**Status:** `fixture_ready`  
**Provider calls permitted:** No  
**Execution authorization created:** No  
**Next gate:** `execution_authorization_review`

---

## 1. Purpose

The Batch 06 diagnostic experiment design froze six prompt-cohort roles but intentionally left them pending.

This slice materializes those roles into deterministic synthetic provider requests without changing the original design artifact.

The design remains immutable. A separate fixture manifest now binds:

- the original design-plan bytes;
- the original design-manifest bytes;
- the deterministic fixture recipe;
- six unique stable-prefix cohorts;
- three exact request sizes per cohort;
- privacy-safe hashes and byte counts;
- one ignored local protected prompt bundle.

No live provider call is made.

---

## 2. Why the fixtures are an overlay

The original experiment plan remains the preregistered design snapshot.

Rewriting that plan from `pending` to `materialized` would erase the distinction between:

1. what was designed before fixture construction; and
2. what was actually produced and verified later.

The committed fixture manifest therefore acts as an immutable materialization overlay.

A future authorization must bind to both the design manifest and the fixture manifest.

---

## 3. Materialized cohort set

The fixture set contains exactly:

- `cohort-alpha`
- `cohort-beta`
- `cohort-gamma`
- `cohort-delta`
- `cohort-epsilon`
- `cohort-zeta`

Every cohort has:

- one unique 6,000-byte system prompt;
- three user prompts of 1,365, 1,737, and 2,109 bytes;
- total provider-visible prompt sizes of 7,365, 7,737, and 8,109 bytes;
- source-anchored input-token estimates of 1,732, 1,809, and 1,884;
- three condition B request hashes;
- three condition C request hashes;
- exact B/C request-hash equality by turn.

The 8,109-byte third request matches the Batch 06 C3/B3 request-size anchor.

---

## 4. Deterministic synthetic generation

The public recipe commits only:

- cohort IDs;
- target byte counts;
- source-anchored token estimates;
- fixed provider request parameters;
- a bounded synthetic filler vocabulary;
- the materializer version;
- privacy and claim restrictions.

It does not commit a complete prompt.

The materializer constructs canonical ASCII JSON prompts from the recipe and writes the full prompt bundle only to:

`.local/benchmark/diagnostic-fixtures-v1/prompt_cohorts.json`

That path is ignored by Git.

The protected bundle is deterministic. Its SHA-256 is committed in the public fixture manifest.

---

## 5. Provider-visible B/C equivalence

For each cohort and turn, the materializer creates one provider request payload containing only:

- the system message;
- the user message;
- model alias;
- completion-token budget;
- temperature;
- streaming flag;
- storage flag;
- reasoning effort.

The local condition label is deliberately absent from the provider request.

The materializer computes the provider request independently for condition B and condition C and requires the SHA-256 values to match exactly.

This proves local-label equivalence at the serialized provider-request boundary. It does not prove that a provider routes both calls through identical internal infrastructure.

---

## 6. Token estimate boundary

The fixture estimates reuse the observed Batch 06 token counts at the same exact total prompt byte targets.

This is a bounded preflight estimate, not a provider-tokenizer proof.

Future authorized execution must retain actual provider telemetry and compare it with the preflight estimate. No token-count or cost claim is permitted from materialization alone.

---

## 7. Privacy controls

Generated prompt content is:

- synthetic only;
- printable ASCII only;
- deterministic;
- scanned for forbidden secret and credential markers;
- stored only beneath ignored local storage.

Public artifacts retain only:

- hashes;
- byte counts;
- bounded estimates;
- recipe identity;
- model request profile;
- verification booleans.

Public artifacts do not retain:

- raw prompts;
- user messages;
- credentials;
- headers;
- raw provider errors;
- provider outputs;
- customer or personal data.

---

## 8. Validation and stop conditions

Materialization fails closed when:

- design-plan or design-manifest bytes drift;
- recipe bytes drift;
- exact prompt byte targets are missed;
- stable-prefix hashes are not unique;
- B/C request hashes diverge;
- public fixture evidence does not reproduce;
- protected bundle bytes do not match the committed hash;
- generated content contains a forbidden sensitive-data marker;
- an execution authorization or Batch 07 asset is introduced in this slice.

---

## 9. Non-claims

This slice does not:

- call Groq;
- authorize execution;
- identify the Batch 06 root cause;
- prove a provider cache defect;
- prove spacing or order causation;
- establish cache savings;
- establish latency, cost, or quality improvement;
- produce an accepted A/B/C result.

It creates the deterministic, inspectable request fixtures needed for a separately reviewed diagnostic execution authorization.
