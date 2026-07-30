# Runbook: CUDA 12.9 P1 Probe Taxonomy Remediation V1

## Repository phase

1. Apply the reviewed remediation package on
   `fix/local-abc-cu129-p1-probe-taxonomy-v1`.
2. Run bounded Ruff remediation only on changed `.py` files.
3. Do not format `.ipynb` or `.tmpl` files directly.
4. Run diagnostic, source-materialization, and launcher validators.
5. Run focused tests, then full repository gates.
6. Commit, push, review, and merge.

## Static typing invocation contract

Run mypy from the repository root without positional file arguments:

```powershell
& $Python -m mypy --config-file pyproject.toml
```

The project uses a `src` layout and configures `files = ["src", "tests"]`.
Passing only a test path overrides those roots and may cause the local
`auragateway` package to be classified as an installed untyped dependency.

Do not remediate that invocation artifact with `py.typed`,
`ignore_missing_imports`, `MYPYPATH`, or per-import suppressions in this tranche.

## Diagnostic module import contract

The P0-P2 diagnostic implementation is a concrete submodule, not an attribute
exported by `auragateway.local_abc.__init__`.

Typed tests must import the concrete module directly. Do not restore
`from auragateway.local_abc import <diagnostic-module>`, add the generator module
to the package public surface, add `py.typed`, widen the import to `Any`, or add
a mypy suppression for this boundary.

Python cannot parenthesize or naturally wrap a dotted `import ... as ...`
statement. The concrete module path is longer than the repository line-width
limit, so this test uses one localized `# noqa: E501` on that import only.
No broader Ruff suppression, typing suppression, package-root export, or
public-surface expansion is permitted.

## Post-merge corrected lineage

1. Export the regenerated source materializer notebook.
2. Run it CPU-only with Internet Off and no secrets.
3. Attach that successful notebook output to the regenerated inspection notebook.
4. Run metadata-only inspection.
5. Attach the corrected source materializer output and governed wheelhouse output
   to the regenerated execution launcher.
6. Run one T4 x2 saved version.
7. Preserve the first corrected terminal decision.

## Prohibitions

- Do not rerun Kaggle version `338921762`.
- Do not reuse the old materializer output.
- Do not require a standalone Kaggle Dataset.
- Do not edit generated notebooks manually.
- Do not start a model or worker.
- Do not perform benchmark trajectories.
