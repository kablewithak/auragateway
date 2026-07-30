# Runbook: P0-P2 Lineage Semantics Remediation V1

## Repository boundary

- Expected branch: `fix/local-abc-p0-p2-lineage-semantics-v1`
- Required base commit: `24914d79ef4b4d33285f111c8920d16c36244614`
- Live full-run authorization: absent
- Kaggle execution: prohibited during this tranche

## Apply order

1. Apply the standalone state-aware remediation package.
2. Run bounded Ruff fix and format only on the changed ordinary Python files.
3. Run source-materialization and execution-launcher generators from their producers.
4. Run focused Ruff, project-mode mypy, focused tests, semantic validators, and full
   repository gates.
5. Verify the exact candidate path boundary.
6. Stage and validate one tree, commit that tree, push, verify remote state, and open the
   pull request.

## Identity semantics

- `source_main_base_commit` means the clean merged-main ancestor used to create the
  remediation branch.
- `option_c_decision_merge_commit` means the accepted Option C architecture decision.
- `architecture_origin_branch` preserves the historical branch where the architecture
  contract originated.
- SHA-256 remains the exact-byte authority.

## Generated-artifact rule

Do not edit the materializer, inspection, or launcher notebooks directly. Do not edit the
generated toolchain or launcher records directly. Regenerate them through the two owning
Python modules.

## Static-analysis rule

Run mypy in project mode from the repository root:

```powershell
& $Python -m mypy --config-file pyproject.toml
```

Do not substitute positional single-file mypy.

## Post-merge gate

After merge and a clean-main cold start, execute only the corrected CPU materializer.
Preserve its new saved version and stop before metadata inspection.

## Prohibitions

- Do not reuse materializer version `338895141`.
- Do not reuse inspection version `338900497`.
- Do not reuse GPU version `338921762`.
- Do not create a standalone Kaggle Dataset merely for ceremony.
- Do not start a model or worker.
- Do not issue full-run authorization.
- Do not perform measured A/B/C.
