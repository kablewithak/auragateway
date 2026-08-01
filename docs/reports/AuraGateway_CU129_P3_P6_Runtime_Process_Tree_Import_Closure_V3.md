# AuraGateway CUDA 12.9 P3-P6 Import Closure V3

## Buyer-visible failure

A target-installed AI runtime can work in a parent process and still fail
when the framework launches internal Python subprocesses. This creates
opaque worker-startup failures and wastes governed GPU attempts.

## V3 control

V3 turns package visibility into a process-tree environment contract:

- inherited `PYTHONPATH` is replaced with the exact target site;
- one nested-interpreter probe is bounded and recorded;
- critical module origins must resolve inside the target runtime;
- probe failure consumes no model-load or worker-start action;
- bounded worker failure diagnostics are retained;
- raw worker logs remain outside the evidence ZIP.

## Acceptance boundary

This tranche is implemented but not executed. It does not prove worker
readiness, Qwen architecture compatibility, Triton realization, inference,
cache behavior, dual-worker isolation or production readiness.

## Commercial translation

This is an Agent Harness Hardening proof asset. A CTO pays for it because
it converts a hidden third-party subprocess failure into an explicit,
testable runtime invariant with bounded failure evidence and replay control.
