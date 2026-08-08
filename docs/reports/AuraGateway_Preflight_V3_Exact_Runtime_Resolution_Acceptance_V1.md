# AuraGateway Preflight-v3 Exact Runtime Resolution Acceptance V1

## Decision

`ACCEPT_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_AND_FREEZE_LOCK`

## Identity chain

```text
main=cfd53cfa09b1b4dc11b399cee7c2c16397513915
repository_notebook_sha256=d184f9b8ab61554ceed1bd31a384fc2cb50322ca225644dab5a508c52ea0b78b
kaggle_script_version_id=341073810
executed_notebook_sha256=d9bdd69e3766204af47b5b77de0cad854776491d9a8d7be9afab7b85527ac8e6
code_cell_source_sha256=fe9650606705ed851049150ea1b6b528c247a3302b0bee616525fda02173244d
evidence_zip_sha256=144661d3bcf908ec3ca98c372b50c01234f98e660762f3ab361ed99ce6c9decd
execution_log_sha256=045e13bc03dbf9966189f385f4c39aaa0daae6e72a49a9bfdc190e4639507672
```

The executed markdown and code sources exactly match the committed notebook sources.

## Resolution result

```text
package_count=196
host_count=5
vllm=0.25.1+cu129
vllm_sha256=9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431
torch=2.11.0+cu129
```

Host counts:

```text
download-r2.pytorch.org   4
download.pytorch.org      3
files.pythonhosted.org  158
github.com                1
pypi.nvidia.com          30
```

All 196 records are unique normalized distributions, all artifacts are wheels, every artifact
has SHA-256, every host is explicit, no URL contains query or fragment state, and no host is
unclassified.

## Frozen lock

`benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json`

SHA-256:

`1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c`

## Current boundary

```text
exact_runtime_resolution_lock_frozen=true
exact_runtime_materialized=false
exact_runtime_offline_verified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`implement_preflight_v3_exact_runtime_wheelhouse_materializer_v1`
