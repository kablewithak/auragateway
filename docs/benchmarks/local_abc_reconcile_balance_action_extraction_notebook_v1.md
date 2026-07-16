# Reconcile-Balance Action-Extraction Kaggle Notebook v1

## Artifact identity

- Notebook: `notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_canary_v1.ipynb`
- Notebook SHA-256: `b5909d8c29230aa0dc28abb7f87c3a97d577375d9f303a33b4664f0915384e2d`
- Binding SHA-256: `4818fdfc2f63141da7ddd2dc98a87825551198e9d6505e9c2327f6cf135e4eea`
- Notebook code-source SHA-256: `09310bbd4f82665cb1ccf50eda0d356db092c1e5db65e5ca411feeeceec49413`
- Authorization fingerprint: `9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9`
- Authorization merge commit: `0619867a7acbee5e4c5b639963cf1046cbf36809`
- Authorized requests: `12`
- Cache measurement: out of scope
- Full measured benchmark: unauthorized

## Remediation decision

The predecessor notebook cloned the exact repository and accepted a successful
editable-install subprocess as evidence that the active Kaggle kernel could
import `auragateway`. Kaggle reproduced a deterministic boundary failure:
Cell 03 emitted `REPOSITORY_CHECKOUT_QUALIFIED`, while Cell 04 immediately
failed with `ModuleNotFoundError: No module named 'auragateway'`.

The predecessor failure is classified as
`PRE_EXECUTION_HARNESS_IMPORTABILITY_FAILURE`. It occurred before worker startup
and before any model request, so the bounded execution authorization remains
unconsumed.

This remediation removes the editable-install dependency from the qualification
gate. Cell 03 now:

1. checks out the exact authorization merge commit;
2. resolves the exact `<repository>/src` directory;
3. prepends that directory to the active kernel's `sys.path`;
4. invalidates import caches;
5. verifies `auragateway` discovery;
6. imports the required authorization, evaluation, and arithmetic modules;
7. verifies every imported module resolves beneath the exact checked-out source
   tree;
8. emits `REPOSITORY_IMPORT_QUALIFIED` only after those checks pass.

No kernel restart or hidden editable-install state is required.

## Design

The notebook remains a thin orchestration layer over repository contracts. It
does not reimplement action validation, deterministic execution, scoring,
aggregate metrics, or gate decisions.

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
- current-kernel source import qualification;
- exact vLLM wheel installation;
- model and runtime preflight;
- one worker lifecycle;
- one request per fixed case;
- safe evidence serialization;
- privacy scanning;
- evidence ZIP creation.

## Repository import qualification

Cell 03 must report:

`REPOSITORY_IMPORT_QUALIFIED`

The qualification evidence includes:

- repository identity;
- exact checked-out commit;
- source root relative to the repository;
- source-relative file identity for every required imported module.

The required modules are:

- `auragateway`;
- `auragateway.local_abc.action_extraction_authorization`;
- `auragateway.local_abc.action_extraction_eval`;
- `auragateway.local_abc.arithmetic_action`.

A successful Git checkout alone is insufficient. A successful pip subprocess is
also insufficient. Current-kernel importability from the exact checked-out source
tree is a mandatory pre-execution gate.

## Kaggle inputs

Attach the exact notebook package and the previously qualified vLLM wheel with
SHA-256:

`9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`

Internet access is required to clone the exact repository commit and obtain the
public Qwen model snapshot at revision
`7ae557604adf67be50417f59c2c2f167def9a775`, unless those assets are supplied
through attached private inputs.

## Execution protocol

1. Import the corrected notebook.
2. Attach the exact package ZIP as a notebook output or other input that retains
   the ZIP file itself.
3. Attach the exact qualified vLLM wheel input.
4. Select two Tesla T4 GPUs and enable internet access.
5. Run cells sequentially.
6. Stop immediately if any preflight cell fails.
7. Do not edit the notebook, binding, cases, prompt policy, model identity,
   runtime identity, decoding settings, or request count.
8. Run the 12-request execution cell once.
9. Download the generated evidence ZIP from `/kaggle/working`.

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
