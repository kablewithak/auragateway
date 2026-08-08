# ADR: V1 false-negative acceptance and offline verifier V2 remediation

Date: 2026-08-08

## Status

Accepted for implementation.

## Evidence

```text
v1_script_version_id=341091805
repository_notebook_sha256=8ab387aa99dffc772f847d22e3fed066d5a01018f28b12553403f9f59d1253a4
executed_notebook_sha256=a7ce05e0ab4d886592ca96d45b38cb2bfc0e6d13ff05b8a9e85741b91dfd87f1
markdown_source_matches=true
code_source_matches=true
evidence_zip_sha256=9f24b6ec955aa3c3eb21a3010d775237eeb3abc98dddad39483fcff3fb668872
execution_log_sha256=57681697119b9e52568ef137d49f6cbc9bf26d6908bac6786555141e83208f2b
```

V1 validated the full 196-wheel input, completed the exact offline install,
matched the target inventory, passed `pip check`, passed T4 x2, passed the
torch/CUDA family, transformers, triton, and exact vLLM distribution identity.

The `vllm_module` subprocess returned code 0 and emitted
`{"vllm":"0.25.1"}`. The harness then converted that successful import into
FAILED because it compared `vllm.__version__` with distribution identity
`0.25.1+cu129`.

## First divergence

`VERIFIER_FALSE_NEGATIVE_VERSION_IDENTITY_COMPARATOR`

The exact wheel/distribution identity remains:

```text
0.25.1+cu129
```

The observed module semantic version is:

```text
0.25.1
```

Those are separate validation surfaces.

## Decision

Preserve V1 as immutable diagnostic evidence. Do not rerun it.

Implement V2 with the smallest semantic change:

- distribution gate remains exact `0.25.1+cu129`;
- module import must return code 0;
- `vllm.__version__` must equal explicit semantic version `0.25.1`;
- only after that gate may `vllm._C` execute.

No wheelhouse, lock, install process, GPU topology, or downstream authorization
is changed.

## Non-claims

V1 does not prove native-extension compatibility because that role was blocked.
V2 implementation does not prove compatibility until executed and accepted.
