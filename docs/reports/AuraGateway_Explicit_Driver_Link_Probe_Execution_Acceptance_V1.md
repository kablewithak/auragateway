# AuraGateway explicit driver-link probe execution acceptance V1

## Executive verdict

Kaggle saved version `339127349` is valid positive evidence.

```text
status=PASSED
terminal_decision=EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED
```

## Causal result

The real driver library was already mounted and runtime-visible. The previous
failure occurred because default native linker search did not include the real
driver directory.

The successful intervention was command-local:

```text
-L/usr/local/nvidia/lib64
-Wl,-rpath,/usr/local/nvidia/lib64
-Wl,-t
-lcuda
```

## Verified chain

```text
P0 preflight passed
exact C source passed
syntax compilation passed
explicit link passed
real driver selected
ELF NEEDED passed
ELF RUNPATH passed
ldd real-driver resolution passed
cuInit(0) passed
```

## Platform identity

```text
Ubuntu 22.04.5 LTS
Python 3.12.13
Tesla T4 x2
compute capability 7.5
driver 580.159.04
base Torch 2.10.0+cu128
base Torch CUDA 12.8
```

## Safety

```text
P2 performed: 0
runtime installs: 0
kernel attempts: 0
model loads: 0
worker starts: 0
model requests: 0
benchmark requests: 0
network requests: 0
hidden retries: 0
environment mutations: 0
external spend: 0
```

## Engineering consequence

P0–P2 diagnostic V2 should replace the V1 default P1 link command with the
accepted explicit real-driver contract, retain strict stub rejection, and
permit P2 only after all P1 stages pass.

## Commercial translation

This is a concrete AI System Evaluation Audit proof asset:

```text
vague GPU failure
→ stage-specific evidence
→ minimal causal intervention
→ accepted runtime contract
→ bounded next implementation
```

A CTO pays because this prevents package churn, vendor blame, global
environment hacks and repeated GPU spend.

## Next gate

`DESIGN_AND_IMPLEMENT_P0_P2_PLATFORM_DIAGNOSTIC_V2`
