# AuraGateway P4 Output-Contract Diagnostic V2

## Purpose

P4 V2 preserves the V1 A-F output-contract experiment while correcting the native-library search-path boundary proven by Kaggle inspection saved version `340657269`.

## Proven diagnosis

- Exact wheelhouse manifest: verified.
- P4 target distribution closure: identical to the governed lock.
- Ambient and path-isolated Torch/vLLM imports: failed.
- Native-hardened imports: passed.
- Full V5-profile imports: passed.
- Classification: `NATIVE_LIBRARY_SEARCH_PATH_SUPPORTED`.

## V2 harness changes

- One shared native runtime environment for import closure and worker startup.
- Target NVIDIA libraries precede inherited loader paths.
- CUDA stub paths are prohibited.
- `/usr/local/nvidia/lib64` is retained as the real driver boundary.
- Full hash-locked offline installation.
- Fail-fast worker-exit detection.
- Bounded sanitized stream capture.
- Explicit request logging disablement.
- Post-readiness native-origin closure for `libcusparse` and `libnvJitLink`.
- Stronger process, descendant, port, and capture teardown checks.

## Preserved experiment

The V4/V5 prompt variants, repetition penalties, unconstrained/JSON-schema modes, three repetitions per case, 18-request order, and selection rule are unchanged.

## Non-claims

V2 is implemented but not executed. Worker startup, Triton compilation, JSON-schema compatibility, selection success, measured A/B/C execution, and production readiness are not established.
