# Local A/B/C Action-Extraction Kaggle Execution Package v2

**Version:** 2.0.0
**Date:** 2026-07-17
**State:** Ready for one governed Kaggle execution
**Execution performed:** False
**Authorization consumed:** False

## Package identity

```text
package_filename=auragateway-local-abc-action-extraction-requalification-notebook-v2.zip
package_sha256=deb7d803819ec489218f78ecc4466ae1402eef30a63ba7b93d293ea872677451
package_size_bytes=76893
archive_policy=zip_stored_fixed_metadata_v1
member_count=2
execution_package_manifest_sha256=47e47014e225d3372619568f43f1b139c650b58bfd4773d20089fbc88b07ec0b
```

## Source authority

```text
PR #89 merge=1cbb01e72fc624b71be1faef9da199a1556d2f0c
qualification source blob=97a5756d3a95defccdff90811ff1318f863456b7
notebook blob=237c344330d63b803f94265dbdc24c20ae379dcd
notebook binding blob=9e88e7ac87b0452839b25c540f4e50f3282e72a1
```

## Member constitution

```text
benchmarks/local_abc/reconcile_balance_extraction_requalification_notebook_binding_v2.json
  sha256=f1ed0f27d8073f806b59317aca22424335df4d71c37068ee5efa1493779f77c6
  size_bytes=4097

notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb
  sha256=e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9
  size_bytes=72258
```

## Qualification lineage

```text
notebook_binding_sha256=476d3be54fc34cafacba4bcdef07eaa1213a426df0496e4908bc8078b7edac88
notebook_code_source_sha256=26f7f46475e2746e6e099210475b18b08a1abb90994759394cc2c11d39f1c499
authorization_sha256=a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899
authorization_consumed=false
```

## Fixed execution constitution

```text
execution_attempt_limit=1
request_count=16
request_attempts_per_case=1
complete_suite_required=true
failed_case_only_execution_permitted=false
hidden_retry_count=0
repair_attempt_count=0
replacement_request_count=0
required_exact_operand_matches=16
required_exact_final_answer_matches=16
```

## Kaggle boundary

```text
accelerator=GPU T4 x2
internet_required=true
secrets_required=false
package_attachment_required=true
restart_and_rerun_permitted=false
failed_cell_only_rerun_permitted=false
```

The package must not be executed until the package PR is merged and the operator confirms that the
local `main` branch is synchronized with `origin/main`.

## Packaging validation

- deterministic rebuild reproduces the exact archive SHA-256;
- ZIP integrity passes;
- exactly two members are present in canonical order;
- both member byte streams match the merged repository;
- member timestamps, compression, permissions, and platform metadata are fixed;
- notebook qualification lineage remains valid;
- authorization remains unused;
- no model request or GPU execution occurs during package generation.

## Evidence obligation

A successful or failed governed execution must produce and download:

```text
auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip
```

No rerun is permitted before that archive is preserved and audited.

## Non-claims

- Packaging does not prove measured quality improvement.
- Packaging does not prove that either historical failure is resolved.
- Packaging does not consume the authorization.
- Packaging does not measure cache reuse, latency, or cost savings.
- Packaging does not authorize the full measured A/B/C benchmark.
- Packaging does not establish production readiness.
