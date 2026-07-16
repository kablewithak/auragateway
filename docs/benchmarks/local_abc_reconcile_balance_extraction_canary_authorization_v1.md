# Reconcile-Balance Action-Extraction Canary Authorization v1

## Decision

This artifact authorizes one bounded synthetic action-extraction canary after the
authorization PR merges and a separately generated notebook passes source,
model, runtime, and notebook-hash preflight.

**Authorization fingerprint:** `9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9`  
**Harness merge commit:** `42ef2e6e7d268d0213c2f3a4a48aa536c04eba59`  
**Fixed case count:** `12`  
**External spend:** `R0 / $0`  
**Full measured benchmark authorized:** `No`

## Authorized question

Can the pinned `Qwen/Qwen2.5-0.5B-Instruct` model emit the exact typed
`arithmetic.reconcile_balance.v1` action for all 12 fixed cases on the first
attempt, after which the repository executor calculates the final result
deterministically?

This is an action-extraction capability canary. Cache measurement is not in
scope, and this authorization permits no cache-performance claim.

## Source bindings

- repository: `kablewithak/auragateway`;
- harness merge commit:
  `42ef2e6e7d268d0213c2f3a4a48aa536c04eba59`;
- arithmetic implementation commit:
  `0e4f761de11c85ccf40d234e93a5b2d974590612`;
- case-manifest fingerprint:
  `babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5`;
- evaluation-plan fingerprint:
  `53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62`;
- prompt-policy fingerprint:
  `5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9`;
- action-schema fingerprint:
  `923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7`.

## Model and runtime binding

The authorized model snapshot is:

- repository: `Qwen/Qwen2.5-0.5B-Instruct`;
- revision: `7ae557604adf67be50417f59c2c2f167def9a775`;
- model manifest SHA-256:
  `b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa`;
- config SHA-256:
  `18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45`;
- tokenizer JSON SHA-256:
  `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`;
- tokenizer config SHA-256:
  `5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583`.

The authorized runtime is:

- two Tesla T4 GPUs;
- compute capability `7.5`;
- PyTorch `2.11.0+cu129`;
- CUDA `12.9`;
- vLLM module `0.25.1`;
- vLLM distribution `0.25.1+cu129`;
- wheel SHA-256:
  `9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`.

Any mismatch fails preflight. The notebook may not silently substitute a model,
tokenizer, wheel, GPU type, or runtime version.

## Execution scope

- 12 accepted cases;
- exactly one request per case;
- worker `worker_1`;
- one full worker restart before the run;
- endpoint `/v1/chat/completions`;
- JSON Schema response format;
- temperature `0`;
- top-p `1`;
- seed `7`;
- maximum output tokens `128`;
- streaming disabled;
- permitted finish reason: `stop`.

The rejected candidate cases remain constitution evidence only. They are not
executed by this authorization.

## Failure and continuation policy

A first-attempt action extraction failure is retained and the run continues to
the next fixed case. This produces a complete 12-record diagnostic ledger.

The following failures abort the run immediately:

- source or fingerprint mismatch;
- model or tokenizer identity mismatch;
- runtime or vLLM wheel mismatch;
- worker-start failure;
- transport failure;
- cleanup failure.

No request may be retried, repaired, or replaced. The model may not generate a
direct arithmetic answer as a fallback.

## Evidence contract

The evidence package must contain:

- `reconcile_balance_extraction_canary_schedule_v1.json`;
- `reconcile_balance_extraction_canary_ledger_v1.jsonl`;
- `reconcile_balance_extraction_canary_checkpoint_v1.json`;
- `reconcile_balance_extraction_canary_evaluation_v1.json`;
- `reconcile_balance_extraction_canary_report_v1.json`;
- `RECONCILE_BALANCE_EXTRACTION_CANARY_SUMMARY.txt`;
- `model_snapshot_manifest_v1.json`;
- `worker_1.log`.

Evidence may retain hashes, counts, finish reasons, typed failure codes, and
aggregate metrics. It must not retain raw prompts, raw model outputs, raw actions,
token IDs, PII, secrets, authorization headers, or customer data.

## Notebook and GPU boundary

This PR does not contain or execute a notebook.

After merge, the notebook must bind:

1. this authorization fingerprint;
2. the authorization PR merge commit;
3. its own SHA-256;
4. the exact model snapshot;
5. the exact runtime identity.

GPU enablement before that preflight is prohibited. Once the notebook binding
qualifies, this authorization permits only the bounded 12-request canary.

## Acceptance gate

All 12 cases must independently achieve:

- valid JSON;
- valid action schema;
- exact case identity;
- exact turn identity;
- exact operand extraction;
- deterministic execution success;
- exact final answer;
- `finish_reason=stop`;
- complete first-attempt task success.

Semantic failures remain valid diagnostic evidence but cause the final
all-or-nothing evaluation gate to fail.

## Non-claims

This authorization does not claim:

- the model will pass the 12 cases;
- the payment case is remediated before execution;
- cache behavior is comparable to the historical canary;
- the rejected candidate cases have been solved;
- the 72-trajectory benchmark is authorized;
- the system is deployed or production-ready.
