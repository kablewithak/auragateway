# AuraGateway CUDA 12.9 P1 Probe Taxonomy Remediation V1

## Evidence diagnosis

- Invalid Kaggle version: `338921762`
- Invalid evidence SHA-256:
  `dc8b5404a4182decd5e600ec4bb3f28d36f9ece836a336e72cd89f2b6bf90728`
- Confirmed defect: literal backslash-`n` bytes in generated C source
- Platform linker failure proven: **no**
- Corrected unchanged replay authorized: **no**

## Corrected P1 source contract

```c
extern int cuInit(unsigned int);
int main(void) { return cuInit(0); }
```

- Exact source SHA-256: `263bf5cec15f224add6e80041cfb026725df52135623224c22f79f901bd9b2f2`
- LF byte count: `2`
- Literal backslash-`n` present: `false`

## Staged diagnostic behavior

The P1 probe now separates source materialization, C syntax compilation, CUDA
driver linking, dynamic loader resolution, and driver initialization. The terminal
summary uses the decision emitted by P1 instead of forcing every P1 failure into
a linker-failure label.

## Deterministic identity rebuild

```text
diagnostic notebook:
2f62c6ebfebba148db6f5f9192a474f22ec7599099c397a4169f811849db8603

source bundle:
8c90a0f294cd33a74b5e90da6b9f5671f2fab5bf1dcc0359f275664fce51f00c

source inventory:
855b1e77900cd5e022255d12189fce4207bf93f74671fed9ec0d74caaf29d505

source materializer notebook:
2796eeb1301fa1a7fd7f88038e7672f3988394d40c467483c2bca6443ce4cf46

source inspection notebook:
8167f7d016fe698a15877fd94dac824343dae39a335702dd6bece7884206059d

execution launcher notebook:
e3ae7d2de56a3183a5ea2e2c2b50ef9382dcef94757d74c9071ea3c1d136a0dc
```

## Evaluation

Fixed taxonomy cases:

1. C syntax failure -> `DIAGNOSTIC_INVALID`
2. CUDA link failure -> `CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED`
3. loader resolution failure -> `CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED`
4. `cuInit` nonzero -> `CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED`
5. all stages pass -> `CUDA_DRIVER_LINKER_CONTRACT_PASSED`

Focused local suite: `39 passed`.

## Maintainability

The change makes stage attribution explicit, keeps one attempt per stage, emits
machine-readable evidence, and prevents malformed probe source from being blamed
on the platform.

## Commercial proof angle

This is a concrete **AI System Evaluation Audit** artifact: the harness originally
misclassified its own malformed probe as an infrastructure failure. The remediation
adds byte-level fixtures, stage-specific gates, and evidence-backed taxonomy.

## Next gate

```text
merge_then_execute_corrected_cpu_materialization_lineage
```
