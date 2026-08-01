# ADR: P3-P6 Runtime Process-Tree Import Closure V3

## Status

Approved for repository implementation. Runtime execution is not authorized.

## Context

Kaggle saved version `339387641` proved that the governed CUDA 12.9
wheelhouse installed successfully. The vLLM API-server parent imported
vLLM, but its fresh `/usr/bin/python3` model-registry subprocess could not
import `vllm`.

The first divergence is process-tree import closure, not wheelhouse
installation, model compatibility or Triton realization.

## Decision

V3 will replace any inherited `PYTHONPATH` with the exact target
site-packages directory in the controlled worker environment. Before model
copying, model-load accounting or worker-start accounting, one bounded
nested-interpreter probe must import the critical runtime modules and prove
that every module origin resolves inside the target site.

The probe is a precondition, not a substitute for P3. P3 must still prove
worker readiness, model inventory and explicit `TRITON_ATTN` realization.

## Rejected alternatives

- Rebuilding the wheelhouse: V2 installation passed.
- Relying on parent `sys.path`: it is not inherited by a fresh interpreter.
- Appending unknown inherited package roots: this permits mixed runtimes.
- Treating a successful import probe as proof of P3-P6 success.

## Consequences

The known failure is detected before expensive model or worker actions.
The new evidence identifies executable, environment and module origins.
A later, separate authorization is still required for any Kaggle execution.
