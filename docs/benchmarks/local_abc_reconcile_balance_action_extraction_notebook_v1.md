# Reconcile-Balance Action-Extraction Kaggle Notebook v1

## Artifact identity

- Notebook: `notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_canary_v1.ipynb`
- Notebook SHA-256: `b0d3f840e6d334c6b7631431228ef9ff50a7ea55f8eabceb65fcf4685a1ad5ab`
- Binding SHA-256: `3ccd5b038dc213b1a4468fd82003adae81a7d0b55bf627e75caa37bb46d1cc97`
- Notebook code-source SHA-256: `28fc0c68216a304e94767c66442d9123fdd160a05ca1737182ae69cc7ed828b8`
- Authorization fingerprint: `9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9`
- Authorization merge commit: `0619867a7acbee5e4c5b639963cf1046cbf36809`
- Authorized requests: `12`
- Cache measurement: out of scope
- Full measured benchmark: unauthorized

## Venv-bootstrap failure diagnosis

The PR #83 notebook passed artifact, repository-import, and source qualification.
Cell 05 then failed while executing the system Python command used to create the
isolated virtual environment. The notebook did not capture the subprocess
stderr, so the exact platform message was not retained. The failure is
classified conservatively as `PRE_EXECUTION_VENV_BOOTSTRAP_FAILURE`.

Python's standard `venv` command bootstraps pip through `ensurepip` unless
`--without-pip` is supplied. Kaggle's system Python returned exit status `1`
before any runtime packages, model assets, workers, or model requests existed.

## Resolution

Cell 05 now creates the isolated environment with:

`python -m venv --without-pip <runtime_env>`

The host pip then manages that pip-less environment through pip's supported
`--python <runtime_env>` interface. This avoids reliance on the target
interpreter's `ensurepip` bootstrap while preserving isolation.

The cell then:

1. verifies the isolated Python exists;
2. rejects system-site-package inheritance;
3. installs Torch `2.11.0`, torchvision `0.26.0`, and torchaudio `2.11.0`
   from the CUDA `12.9` PyTorch index;
4. installs the exact authorized vLLM wheel and its dependencies;
5. runs dependency validation through host pip targeting the isolated runtime;
6. emits bounded stdout/stderr tails on future setup failures.

Cell 06 still performs the decisive compiled-extension import probe. Cell 09
still launches the worker with the exact qualified isolated Python.

## Runtime contract

- environment policy: `isolated_venv_exact_torch_cu129_v2`;
- venv bootstrap policy: `without_pip_host_pip_python_v1`;
- default ensurepip used: `false`;
- host pip targeting required: `true`;
- system site packages inherited: `false`;
- Torch: `2.11.0+cu129`;
- Torch CUDA: `12.9`;
- torchvision: `0.26.0+cu129`;
- torchaudio: `2.11.0+cu129`;
- vLLM module: `0.25.1`;
- vLLM distribution: `0.25.1+cu129`;
- vLLM wheel SHA-256: `9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`;
- binary import probe: required;
- worker interpreter: qualified isolated runtime Python.

## Authorization impact

The venv-creation failure happened before model download, worker startup, or any
model request. The authorization remains unconsumed. The 12-request boundary,
zero-retry policy, privacy controls, cache non-claims, and full-benchmark block
remain unchanged.
