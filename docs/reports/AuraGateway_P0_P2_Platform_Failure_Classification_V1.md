# AuraGateway P0-P2 Platform Failure Classification V1

## Executive verdict

The corrected GPU replay is valid negative evidence.

```text
saved_version_id=339111200
launcher_status=P0_P2_EXECUTION_LAUNCHER_COMPLETED_V2
terminal_decision=CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
first_divergence=cuda_driver_link
```

The real CUDA driver library existed and was runtime-visible, but the default
native linker search path did not resolve `-lcuda`.

## Evidence identities

```text
launcher_log_sha256=
82af9fbe23113d1586b02cce3c2c15a73912ae8f3b23afc7df83f797fc5f71cc

launcher_evidence_zip_sha256=
bc962deb82bbb6e009bfd1e10bb41622af3e77cf5e4a70cc7c329b991beba219

platform_evidence_zip_sha256=
5a80b63da417456d2bc328fb91a97d4a3b8b2768a9b054012d42d92f35633a1b
```

## P0

```text
Ubuntu 22.04.5 LTS
Python 3.12.13
Tesla T4 x2
compute capability 7.5
driver 580.159.04
nvidia-smi passed
base torch 2.10.0+cu128
torch CUDA available true
ctypes find_library("cuda") = libcuda.so.1
real driver link path = /usr/local/nvidia/lib64/libcuda.so
resolved driver file = /usr/local/nvidia/lib64/libcuda.so.580.159.04
```

P0 passed.

## P1

The governed C source was byte-exact and object compilation succeeded.

The link command used `-lcuda` but no explicit `-L` path. GNU ld returned:

```text
/usr/bin/ld: cannot find -lcuda: No such file or directory
```

No CUDA library was selected. `ldd` and executable execution were not reached.

## P2

```text
status=NOT_RUN_DUE_TO_PRIOR_FAILURE
attempts=0
```

No Triton conclusion is permitted.

## Causal classification

```text
real driver mount present
+ runtime CUDA visible
+ governed C source valid
+ syntax/object compilation passed
+ default -lcuda link failed
+ no explicit real-driver link directory supplied
=
CUDA_DRIVER_LIBRARY_PRESENT_RUNTIME_VISIBLE_BUT_DEFAULT_LINKER_SEARCH_PATH_UNBOUND
```

## Next gate

```text
design_and_validate_explicit_cuda_driver_link_path_probe_v2
```

No replay is authorized by this classification tranche.

## Reliability consultancy translation

Buyer pain:

AI teams routinely collapse driver presence, linker search, loader resolution,
driver initialization, and kernel compilation into one vague "GPU issue."

Proof asset:

```text
immutable runtime evidence
→ stage-specific diagnosis
→ bounded causal classification
→ explicit next experiment
→ prohibited overclaims
```

Offer mapping:

- AI System Evaluation Audit
- Agent Harness Hardening Sprint
- AI Reliability Pilot
- AI Reliability Retainer

A CTO pays because this prevents repeated GPU spend, incorrect vendor
conclusions, blind package churn, and model-level remediation for a harness or
native-toolchain boundary.
