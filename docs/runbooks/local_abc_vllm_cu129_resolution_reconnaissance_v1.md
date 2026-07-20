# AuraGateway CUDA 12.9 resolution reconnaissance

## Purpose

Run one bounded resolution-only diagnostic before any further wheelhouse materialization attempt.

The notebook must collect all policy violations in one execution rather than fail on the first unknown
artifact host.

## Current state

```text
materializer_state=PAUSED
next_gate=run_cu129_resolution_reconnaissance
qualification_authorization=ABSENT
model_requests_performed=0
```

Preserved third failure:

```text
classification=MATERIALIZER_ACQUISITION_POLICY_FAILURE
code=NVIDIA_PACKAGE_HOST_NOT_ALLOWED
historical_kaggle_title=auragateway-cu129-wheelhouse-nvidia-host-mismatch-v1
execution_log_sha256=f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4
observed_distribution=nvidia-cublas-cu12
observed_host=pypi.nvidia.com
dependency_resolution_completed=true
wheel_downloads_performed=0
model_requests_performed=0
qualification_claimed=false
```

Known latent materializer defect:

```text
code=MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT
bound_materializer_sha256=a3e043ba6c2caf982a0ebe14ddd1d102e0b5066a46ff17f6fdbf7e0bf876cf79
```

Do not run the materializer until the complete source-authority inventory is reviewed and the prefix drift is
repaired.

## Repository notebook

```text
notebooks/auragateway_vllm_cu129_resolution_reconnaissance_v1.ipynb
```

Requested Kaggle title:

```text
auragateway-cu129-resolution-reconnaissance-v1
```

Output directory:

```text
auragateway_vllm_cu129_resolution_reconnaissance_v1
```

## Kaggle settings

```text
Accelerator: None
Internet: On
Secrets: None
Inputs: none
```

Do not attach historical notebook outputs, wheels, models, harnesses, authorization artifacts, or customer
data. Historical evidence is embedded only as bounded identities and diagnostic observations.

## Execution

Use exactly:

```text
Save Version
→ Save & Run All
```

Do not run cells individually first. Do not edit the notebook in Kaggle.

## Required outputs

The saved output must contain:

```text
auragateway_vllm_cu129_resolution_reconnaissance_v1/
├── requirements.in
├── historical_context.json
├── resolution_command_evidence.json
├── resolution_report.sanitized.json
├── resolved_artifacts.json
├── host_inventory.json
├── authority_inventory.json
├── policy_evaluation.json
├── reconnaissance_receipt.json
└── output_sha256_manifest.json
```

If pip resolution itself fails, the notebook may emit only the bounded command evidence and blocked receipt.
That is a diagnostic failure, not materialization success.

## Required terminal fields

A completed resolution should print:

```text
status=RESOLUTION_RECONNAISSANCE_REVIEW_REQUIRED
or
status=RESOLUTION_RECONNAISSANCE_POLICY_COMPLETE

resolved_distribution_count=<integer>
host_count=<integer>
policy_violation_count=<integer>
wheel_files_written=0
package_installation_performed=false
model_requests_performed=0
qualification_claimed=false
save_this_notebook_output=true
```

`REVIEW_REQUIRED` is expected when candidate or unknown authorities remain. The notebook must collect all
policy violations before returning.

## Output inspection

After Version 1 completes:

1. open the immutable saved version;
2. record the actual Kaggle slug;
3. download the complete saved output;
4. download the full execution log;
5. do not rerun the notebook;
6. close the Kaggle session;
7. stop before materialization.

## Review procedure

The downloaded output must be used to build:

- one complete exact-host inventory;
- one package-family-to-authority map;
- one approved/rejected decision for each candidate source;
- one local replay fixture;
- one aggregated materializer remediation.

The next remediation must address the full source policy and
`MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT` together.

## Stop policy

Do not:

- add `pypi.nvidia.com` directly to the active materializer before review;
- use wildcard domains;
- run `pip download`;
- create a wheelhouse;
- install packages;
- enable a GPU;
- run the offline verifier;
- load a model;
- start workers;
- issue an authorization;
- run qualification;
- execute A/B/C trajectories.


## Completed Version 1 result

```text
status=RESOLUTION_RECONNAISSANCE_REVIEW_REQUIRED
resolved_distribution_count=176
host_count=5
policy_violation_count=26
results_zip_sha256=a035b21fe5795816e888886003c3dd6c73dbda162370805be687b28f8cef4399
execution_log_sha256=3455a8e631157a0c4e4c66e3e5e23c0e4cb41236e6b7d1016811b357488a2269
```

All 26 findings were reviewed together and converted into the exact artifact lock:

```text
resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
review_decision=APPROVED_AS_EXACT_LOCKED_CLOSURE
```

The historical notebook must not be rerun. The next gate is the fresh exact-lock materializer.
