# Reconcile-Balance Action-Extraction Kaggle Notebook v1

## Artifact identity

- Notebook: `notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_canary_v1.ipynb`
- Notebook SHA-256: `1557161e6f5f70e3eb4b2d8d69a0d50efec47d3d2449af7f2a3a6c1edfdf1b7c`
- Binding SHA-256: `c4384d475dc94897095f181895af748ff1a6c5db4311dfc7622c364569fadde0`
- Notebook code-source SHA-256: `fbcf0677ecd04e7a758d3714646126834ba489a6bdf232929a3eed6b476634d3`
- Authorization fingerprint: `9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9`
- Authorization merge commit: `0619867a7acbee5e4c5b639963cf1046cbf36809`
- Authorized requests: `12`
- Cache measurement: out of scope
- Full measured benchmark: unauthorized

## Runtime-drift diagnosis

The predecessor PR #82 notebook passed artifact, repository-import, and source
qualification. It then installed the exact authorized vLLM wheel into Kaggle's
base Python using `--no-deps`.

The observed Kaggle base runtime was:

- Python `3.12.13`;
- Torch `2.10.0+cu128`;
- Torch CUDA `12.8`;
- two Tesla T4 GPUs with compute capability `7.5`.

The authorized wheel declares `torch==2.11.0` and is compiled for CUDA `12.9`.
Its first binary import failed with an unresolved `torch_from_blob` symbol.

This is classified as
`PRE_EXECUTION_VLLM_ABI_RUNTIME_DRIFT`. The failure occurred before model
loading, worker startup, or any authorized model request. The authorization
remains unconsumed.

## Resolution

The notebook no longer mutates or trusts Kaggle's base Torch installation.

Cell 05 now:

1. locates the exact authorized wheel by SHA-256;
2. creates a clean virtual environment beneath the run workspace;
3. rejects system-site-package inheritance;
4. installs the exact Torch `2.11.0`, torchvision `0.26.0`, and torchaudio
   `2.11.0` stack from the CUDA `12.9` PyTorch index;
5. installs the exact vLLM wheel with its declared dependencies;
6. runs `pip check`.

Cell 06 runs a clean subprocess using the isolated runtime Python. The probe
must import both Torch and vLLM successfully, enumerate both T4 GPUs, verify
compute capability, report the exact authorized runtime versions, and prove the
Torch and vLLM module files resolve beneath the isolated environment.

Cell 09 starts the vLLM worker with the same qualified isolated runtime Python.
The active notebook kernel is used only for AuraGateway contracts, scoring,
evidence, and orchestration.

## Runtime contract

- environment policy: `isolated_venv_exact_torch_cu129_v1`;
- system site packages inherited: `false`;
- Torch: `2.11.0+cu129`;
- Torch CUDA: `12.9`;
- torchvision: `0.26.0+cu129`;
- torchaudio: `2.11.0+cu129`;
- vLLM module: `0.25.1`;
- vLLM distribution: `0.25.1+cu129`;
- vLLM wheel SHA-256: `9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`;
- GPU count: `2`;
- GPU model: `Tesla T4`;
- compute capability: `7.5`;
- binary import probe: required;
- worker interpreter: qualified isolated runtime Python.

## Execution protocol

1. Attach the exact notebook package and exact vLLM wheel inputs.
2. Enable two Tesla T4 GPUs and internet access.
3. Run cells sequentially.
4. Stop on any failed preflight.
5. Cell 05 may take several minutes while the isolated runtime is installed.
6. Cell 06 must report `RUNTIME_PREFLIGHT_QUALIFIED` and
   `binary_import_probe=passed`.
7. Run the 12-request Cell 10 exactly once only after Cells 01–09 pass.
8. Package and return the evidence ZIP.

## Failure behavior

The notebook remains fail-closed:

- no model request is sent before every preflight passes;
- no failed request is retried, repaired, or replaced;
- semantic failures are retained;
- infrastructure failures abort;
- cleanup is mandatory.

## Privacy and non-claims

The notebook retains hashes, counts, typed failure codes, metrics, lifecycle,
and cleanup evidence. It does not retain raw prompts, raw outputs, raw actions,
token IDs, PII, secrets, authorization headers, or customer data.

This remediation does not claim that the model passes the 12-case gate, that
cache behavior is qualified, that the full benchmark is authorized, or that
AuraGateway is production-ready.
