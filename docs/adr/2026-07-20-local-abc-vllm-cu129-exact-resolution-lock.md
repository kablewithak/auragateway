# ADR: Bind CUDA 12.9 materialization to the reviewed exact resolution lock

- Status: Accepted
- Date: 2026-07-20
- Scope: AuraGateway local A/B/C vLLM runtime acquisition
- Lifecycle claim: production-shaped acquisition control, not runtime qualification

## Context

Three fail-fast materializer attempts exposed one source-policy defect per run. A resolution-only diagnostic
then resolved the complete closure in one pass: 176 unique distributions, five exact hosts, and 26 review
findings. The diagnostic installed no packages and retained no wheel files, but pip did transfer temporary
artifacts while creating its dry-run report.

## Decision

Use `benchmarks/local_abc/auragateway_vllm_cu129_resolution_lock_v1.json` as the sole approved closure.

```text
resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
package_count=176
host_count=5
wildcard_domains_permitted=false
```

Each record binds:

- normalized distribution name;
- exact version;
- exact hostname;
- source authority label;
- artifact filename;
- sanitized URL;
- raw URL SHA-256;
- artifact SHA-256.

The materializer must recompute the live resolution and compare every record against the lock before executing
`pip download`. Missing, unexpected, or changed records block the run with an aggregated mismatch envelope.

## Exact host decisions

The reviewed closure uses only:

```text
download-r2.pytorch.org
download.pytorch.org
files.pythonhosted.org
github.com
pypi.nvidia.com
```

These hosts are approved only for the exact locked artifacts. This is not wildcard or future-package trust.

## Additional remediation

The materializer's stale `cu128` filename checks are replaced with:

```text
vllm-0.19.1-
torch-2.10.0+cu129-
torchaudio-2.10.0+cu129-
torchvision-0.25.0+cu129-
transformers-5.5.3-
```

## Rejected alternatives

### Continue patching one hostname per run

Rejected because it produces low-information feedback and repeated Kaggle executions.

### Approve package families by name prefix

Rejected because the reconnaissance proved that package names do not reliably identify the serving index.

### Trust any artifact from the five observed hosts

Rejected. Approval is constrained to exact locked artifact identities.

## Consequences

- Dependency drift becomes a pre-download failure.
- Review evidence is replayable locally.
- Network transfer, retained wheel output, and package installation are reported separately.
- Materialization remains distinct from offline compatibility verification and model qualification.
