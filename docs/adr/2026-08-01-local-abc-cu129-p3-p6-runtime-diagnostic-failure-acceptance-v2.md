# ADR: Accept P3-P6 Runtime Diagnostic Failure V2

## Status

Accepted for repository implementation after saved version `339387641`.

## Context

The governed V2 run used one T4 x2 Kaggle session with Internet disabled. Offline target-runtime installation passed. P3 then failed because vLLM launched `/usr/bin/python3 -m vllm.model_executor.models.registry`, and that fresh interpreter could not import the target-installed `vllm` package.

## Decision

Preserve the exact authorization, FAILED consumption receipt, bounded runtime archive, queryable archive members, Kaggle log, and worker logs. Classify the first divergence as `TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS` and the violated invariant as `TARGET_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE`.

Do not rebuild the wheelhouse. Do not replay V2. Do not claim that setting `PYTHONPATH` is proven until V3 passes a nested-interpreter import-closure gate and the real P3 startup gate.

## Consequences

V3 must construct an explicit worker-child environment, replace inherited `PYTHONPATH` with the exact target site, run one bounded nested Python import-closure probe before model copying or worker-start budget consumption, retain resolved module origins, and preserve bounded worker diagnostics.
