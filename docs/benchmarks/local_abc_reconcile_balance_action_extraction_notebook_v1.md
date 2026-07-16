# Reconcile-Balance Action-Extraction Kaggle Notebook v1

## Artifact identity

- Notebook: `notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_canary_v1.ipynb`
- Notebook SHA-256: `5635bc04c7ffa7a78f9f9eeeef197976a09fd9294c9716b4c87d94ee212e6e74`
- Binding SHA-256: `e8cbca20fb7572cba11f4b2886880a4f2763d1d4a1059310b7cd11ac15065ac6`
- Authorization fingerprint: `9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9`
- Authorization merge commit: `0619867a7acbee5e4c5b639963cf1046cbf36809`
- Authorized requests: `12`
- Cache measurement: out of scope
- Full measured benchmark: unauthorized

## Design

The notebook is a thin orchestration layer over the repository contracts merged
through PR #80. It does not reimplement action validation, deterministic
execution, scoring, aggregate metrics, or gate decisions.

Repository code owns:

- fixed case and evaluation-plan loading;
- authorization cross-binding;
- prompt rendering;
- JSON Schema response format;
- action validation;
- deterministic reconciliation execution;
- per-case scoring;
- aggregate evaluation reporting;
- notebook runtime binding.

The notebook owns:

- exact artifact and repository checkout;
- exact vLLM wheel installation;
- model and runtime preflight;
- one worker lifecycle;
- one request per fixed case;
- safe evidence serialization;
- privacy scanning;
- evidence ZIP creation.

## Kaggle inputs

Attach this exact ZIP as a private Kaggle dataset:

`auragateway-local-abc-action-extraction-notebook-v1.zip`

Also attach the previously qualified vLLM wheel containing SHA-256:

`9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`

Internet access is required to clone the exact repository commit and download the
public Qwen model snapshot at revision `7ae557604adf67be50417f59c2c2f167def9a775` unless those assets are
provided through an attached private dataset.

## Execution protocol

1. Import the notebook from the package.
2. Attach the same package ZIP as a private dataset.
3. Select two Tesla T4 GPUs.
4. Run cells sequentially.
5. Stop immediately if any preflight cell fails.
6. Do not edit the notebook, binding, case files, prompt policy, model identity,
   runtime identity, decoding settings, or request count.
7. Run the 12-request cell once.
8. Download the generated evidence ZIP from `/kaggle/working`.

The notebook starts no model worker and sends no request before artifact, source,
wheel, runtime, model, and notebook-binding preflight qualify.

## Failure behavior

Semantic extraction failures are retained and execution continues through all 12
fixed cases. Infrastructure failures abort immediately. No failed case is
retried, repaired, or replaced.

## Evidence retention

Evidence retains hashes, counts, finish reasons, typed failure codes, aggregate
metrics, worker lifecycle, and cleanup status.

Evidence does not retain raw prompts, raw model outputs, raw actions, token IDs,
PII, secrets, authorization headers, or customer data.

## Non-claims

This artifact does not claim:

- the model passes the action-extraction gate;
- payment reconciliation is remediated before execution;
- cache behavior is measured or comparable;
- the six rejected candidates are solved;
- the 72-trajectory benchmark is authorized;
- AuraGateway is production-ready.
