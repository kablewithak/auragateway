# AuraGateway P4/P5 Composition Differential Terminalization Reconciliation V1

## Decision

The governed P4/P5 composition differential execution is accepted as valid diagnostic evidence with an explicit terminalization provenance gap.

The saved Kaggle execution is scriptVersionId `341807938` for transaction `14c4249a5663cf7f94674fab924d5fc334c835f44836347ce13634eb505cc22e`.

The diagnostic completed all six frozen requests and decided `COMPOSITION_REGRESSION_SUPPORTED` under the predeclared rule: Case A passed 3/3 and Case B passed 0/3. The variable under test was `MESSAGE_COMPOSITION_ONLY`.

## Governance reconciliation

The operator performed the required Kaggle settings observation before Save & Run All, but the exact `platform_observed_at` timestamp was printed only to the local console and was not durably persisted. Later console-buffer recovery failed. The timestamp is therefore unrecoverable.

The original issuer terminal receipt must not be fabricated. Its `terminalize` command cannot truthfully be completed because it requires the exact platform-observation timestamp. The preserved original issuer lifecycle therefore remains `ISSUED` as observed, while this reconciliation closes operational authority: the single-use authorization is consumed by the observed execution, is non-reusable, and permits no rerun.

This provenance defect does not invalidate the controlled scientific result because the execution evidence independently establishes the transaction, exact runtime identity, six-request completion, action budgets, A/B outcomes, teardown, cleanup, and absence of hidden retries or external network requests.

## Evidence

Repository custody preserves:

- governed evidence ZIP SHA-256 `128d9e0d76c1d55608b862bb4604ed654667cbeda821c8de8ec103445803cd3c`;
- executed notebook SHA-256 `a3ec983ac7d49b5ecbb15d0ca2921710cc60d25515fd7ad8cb0cc2e8fab65685`;
- terminal log SHA-256 `9ea37ed7747f756d48a957afcef91149c834b8d7c080990232f93ebc415eb421`;
- reconciliation input ZIP SHA-256 `10433e527f0901299b4a94cfd915e1f8b257826b569eb797d3a70bf00dad0d2f`;
- byte-preserved live authorization and transaction manifest captured before transient cleanup.

The evidence bundle retains neither raw prompts nor raw model outputs.

## Runtime metadata debt

The runtime source identity report correctly verifies executed runtime SHA-256 `4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7`, but still carries predecessor metadata `notebook_name=ag-p5-p6-transaction-bound-v1` and `source_main_commit=4afdcf9d840bc90ceb34af8dae098998f78de572`.

This is recorded as metadata debt, not a runtime identity failure. Future successor execution artifacts must remove stale predecessor labels before execution authority is issued.

## Forward control

Any future execution-authorization workflow that requires a platform observation must persist that observation atomically to a durable local artifact before Save & Run All. Terminalization must consume the persisted observation artifact, not console history. Printing the timestamp may remain a convenience but cannot be the sole custody mechanism.

## Non-claims

This reconciliation does not claim that the original issuer lifecycle was closed by its canonical terminal receipt. It does not reconstruct the missing timestamp. It does not authorize Case C, a rerun, runtime remediation, or a new execution. It does not establish generic Qwen unreliability. The differential conclusion is scoped to the frozen runtime, model, request contract, and message-composition variable.

## Next gate

`DESIGN_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1`
