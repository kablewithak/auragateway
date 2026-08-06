# AuraGateway P4 T4-x2 Execution Authorization V2

## Failure corrected

V1 encoded the unavailable Kaggle allocation `T4_X1`. Static tests proved internal
consistency but did not verify the current external platform option.

## Existing runtime isolation

The merged P4 runtime already:

- sets `CUDA_VISIBLE_DEVICES=0` in the worker environment;
- records `gpu_index=0`;
- increments one model-load counter;
- increments one worker-start counter.

No notebook, runtime template, or runtime-script change is required.

## V2 platform contract

- Kaggle allocation: `GPU_T4_X2`
- allocated GPU count: `2`
- worker-visible devices: `0`
- worker-visible GPU count: `1`
- worker GPU index: `0`
- GPU 1 model worker: prohibited
- Internet: disabled
- wheelhouse attachments: exactly `1`
- model snapshot attachments: exactly `1`

## Lifecycle

`V1 ISSUED -> V1 ABANDONED_BEFORE_EXECUTION`

`V2 IMPLEMENTED_NOT_ISSUED -> V2 ISSUED -> V2 CONSUMED`

The V1 abandonment requires operator attestation that no saved version or runtime
execution occurred. V2 issuance requires the abandonment receipt and a current
Kaggle capability observation.

## Non-claims

P4 has not been executed. No A-F case is selected. Structured-output reliability,
P5, P6, measured A/B/C, deployment, and production readiness are not established.
