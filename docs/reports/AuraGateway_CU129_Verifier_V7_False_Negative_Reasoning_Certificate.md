# AuraGateway CUDA 12.9 Verifier V7 False-Negative Reasoning Certificate

**Result:** `REASONING_CHAIN_CONSISTENT`  
**Evidence sufficiency:** `SUFFICIENT_FOR_REPOSITORY_RECONCILIATION`  
**Rerun decision:** `NOT_JUSTIFIED`

## Premises

1. Verifier v7 Version 1 is consumed and immutable.
2. Raw command records outrank the aggregate summary when the summary logic is defective.
3. Historical evidence must remain byte-preserved, including the original `FAILED` result.
4. Target resolution must be checked structurally from the active runtime root and target library inventory, never from a duplicated `v5`, `v6`, or `v7` directory literal.

## Source evidence

- Verifier notebook SHA-256: `66fe0df31e49c035d858865749eca1755d5d09ce863b378a9f01fb55ac8bf7fd`
- Evidence ZIP SHA-256: `8db01f1dd47a01ce2a1cd180c177af8c12826acdba8694d16893b2119e8633e7`
- Internal manifest SHA-256: `51588c414216e65fa3db8edf3afa388349c5bbcde1d05277fdafb534a170f997`
- Canonical execution-log SHA-256: `0e82fca90fbc68688c1a8fbc41dbf42d8cb8bc868786dfa5952f47f7f5107261`

## Observed facts

- The aggregate summary reported `FAILED` with first divergence `canonical_nvjitlink_resolution`.
- The canonical `ldd` command returned `0`, did not time out, and emitted no stderr.
- `ldd` resolved `libnvJitLink.so.12` to the exact path recorded by the target CUDA inventory under the active `VENV_ROOT`.
- The selected target `libnvJitLink.so.12` has SHA-256 `02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f` and exposes `__nvJitLinkGetErrorLogSize_12_9`.
- Direct target cuSPARSE loading passed.
- Torch `2.10.0+cu129` initialized CUDA `12.9` with two T4 devices.
- Transformers `5.5.3`, vLLM `0.19.1`, and `vllm._C` imported successfully.
- Base distribution metadata was unchanged.
- No model request, qualification request, customer data, credential, or paid resource was used.

## First divergence

The verifier compared the resolved path with the stale literal:

```text
<working>/auragateway_vllm_runtime_cu129_v6/
```

The executed target root was structurally valid but used the consumed v7 runtime directory. The semantic check therefore changed a successful raw command record into a failed derived role.

## Competing explanations

1. **CUDA or loader failure:** rejected because `ldd`, symbol inspection, direct cuSPARSE loading, Torch CUDA, vLLM, and `vllm._C` all passed.
2. **Evidence corruption:** rejected because the ZIP and internal manifest are hash-valid with zero mismatches.
3. **Harness semantic false negative:** accepted because the only failed role contains a successful raw command plus a stale version-specific assertion.

Classification: `HARNESS_SEMANTIC_FALSE_NEGATIVE`.

## Selected resolution

Preserve the original evidence and summary unchanged. Re-evaluate target resolution with a structural invariant:

```text
resolved nvJitLink path
== target CUDA inventory nvJitLink path
and
resolved path is beneath VENV_ROOT
and
relative suffix is lib/pythonX.Y/site-packages/nvidia/nvjitlink/lib/libnvJitLink.so.12
```

The active reconciliation logic must contain no version-specific runtime-directory token.

## Regression requirements

- The real v7 path must pass even when the historical notebook contains the stale v6 literal.
- `/usr/local/cuda/lib64/libnvJitLink.so.12` must fail.
- A sibling runtime root must fail.
- The original `FAILED` summary and failed role must remain unchanged in the evidence vault.

## Claims

`RUNTIME_PREREQUISITE_TECHNICALLY_PASSED` is supported for the exact captured CUDA 12.9 environment.

## Non-claims

This does not prove model loading, worker health, cache telemetry, cache reuse, reset correctness, measured A/B/C improvement, customer-data readiness, or production readiness.
