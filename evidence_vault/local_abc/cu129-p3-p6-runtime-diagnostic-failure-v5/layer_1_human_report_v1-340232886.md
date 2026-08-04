# AuraGateway P4 Output-Contract Inspection V1

## Boundary

- No model was loaded.
- No vLLM worker was started.
- No model request was made.
- No package was installed.
- No external network request was made.

## Mounted model

- repository: `Qwen/Qwen2.5-0.5B-Instruct`
- revision: `7ae557604adf67be50417f59c2c2f167def9a775`
- file count: `10`
- total bytes: `999604126`
- chat-template SHA-256: `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`

## Generation defaults

- do_sample: `True`
- temperature: `0.7`
- top_p: `0.8`
- top_k: `20`
- repetition_penalty: `1.1`

## Wheelhouse

- wheel count: `176`
- all expected control hashes valid: `True`
- critical wheel count: `15`

## Hypothesis checks

- V4/V5 prompt semantics differ: `True`
- response_format absent in V5 request: `True`
- top_k not explicitly neutralized: `True`
- repetition penalty not explicitly neutralized: `True`

## Environment

- Python: `3.12.13 (main, Mar  4 2026, 09:23:07) [GCC 11.4.0]`
- platform: `Linux-6.12.90+-x86_64-with-glibc2.35`
- nvidia-smi return code: `None`

## Next step

Upload the output ZIP for the second investigation layer. Do not run a model or repeat the failed V5 diagnostic.
