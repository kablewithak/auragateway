# AuraGateway C4 Paragraph-Order Behavioral Differential Disposition V1

## Status

`DISPOSITIONED_VALID_GOVERNED_C4_PARAGRAPH_ORDER_DIFFERENTIAL`

## Purpose

Preserve the completed governed C4 paragraph-order behavioral differential,
reconcile its immutable evidence, and freeze only the bounded conclusion supported
by the execution.

This disposition does not authorize another execution.

## Governed execution identity

- Transaction: `19fc03a6b4ca74a025f8d9b8cd21be7e1cb14a4e776995760c679a581340f122`
- Kaggle saved version: `343909652`
- Terminal authority: `CONSUMED`
- Execution outcome: `PASSED`
- Authorization reusable: `false`
- Governed evidence ZIP SHA-256:
  `20e209c0a73f817b774065081ebed3e142405db1dca4e96847f5cc802650ca18`
- Outer Kaggle results ZIP SHA-256:
  `dfdfc7dbaed1e0387e4022505424a34ee806ae146e5d73167d813a650720c5c3`
- Custody manifest SHA-256:
  `5de191716f788ab0345b74a1446252e95bf3793a3685c4fb4d498ead794aa549`

## Frozen question

Holding prompt-token count, token inventory, local tail, message topology, final
instruction, output contract, generation parameters, fresh-worker isolation, and
zero-cache baseline fixed, does changing only global paragraph order alter the
deterministic C4 failure phenotype?

The treatment preserved paragraph 1 and paragraph 10 and reversed the middle
eight paragraphs.

Request order remained:

`CONTROL,TREATMENT,TREATMENT,CONTROL,CONTROL,TREATMENT`

## Observed result

| Condition | Exact object | Valid JSON | Stable parsed-object identity |
| --- | ---: | ---: | --- |
| `CONTROL_ORIGINAL_C4` | 0/3 | 3/3 | `fb8cbfde...256aba` |
| `TREATMENT_REVERSED_MIDDLE_EIGHT` | 0/3 | 3/3 | `fb8cbfde...256aba` |

The control anchor reproduced the historical deterministic failure phenotype.
All six observations produced the same canonical parsed-object SHA-256:

`fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba`

The frozen decision is therefore:

`ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE`

Bounded interpretation:

> This paragraph-order intervention did not change the observed deterministic
> failure phenotype.

## Execution invariants

- prompt tokens: 899 for both conditions
- final user boundary: 880 for both conditions
- control token SHA-256:
  `f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c`
- treatment token SHA-256:
  `14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce`
- control payload SHA-256:
  `a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788`
- treatment payload SHA-256:
  `47c519c24efd40e3bab4bfa2eaec1cf3d62c91a648870e631721625567f20b5e`
- model requests: 6/6
- model loads: 6/6
- worker starts: 6/6
- fresh worker process per observation: true
- hidden retries: 0
- replacement observations: 0
- external network requests: 0
- benchmark trajectory requests: 0
- external spend: 0
- teardown: PASS
- scratch cleanup: PASS
- failure report: NOT_APPLICABLE
- raw prompts retained: false
- raw model outputs retained: false

## Wrapper/control-plane disposition

The current transaction-bound wrapper line completed normally.

- saved notebook error outputs: none
- outer-results primary-failure artifact: none
- `SystemExit(0)` false-positive reporting defect: not observed in this execution

This is materially different from the historical B-vs-D wrapper defect and does
not require another wrapper repair.

## Repository state implication

This execution narrows the C4 failure search but does not qualify C4.

- C4 qualification accepted by repository: false
- paragraph-order repository state advanced: false
- paragraph-order root cause established: false
- P5 requalified: false
- P6 requalified: false
- final North-Star A/B/C measured: false
- production readiness established: false
- new execution authorized: false
- unchanged replay authorized: false

## Non-claims

This disposition does not establish that:

- global paragraph order is the sole or root cause;
- exact repetition has a known threshold;
- any specific n-gram or periodicity effect is individually causal;
- prefix caching is defective;
- C4 is qualified;
- P5 or P6 is requalified;
- the North-Star A/B/C effects are measured;
- the system is production-ready.

The static token-ID multiset premise was part of the frozen design and was not
re-executed as a runtime measurement in this governed run.

## Next gate

`ANALYZE_C4_PARAGRAPH_ORDER_NO_CHANGE_BEFORE_NEW_EXECUTION_V1`

The next action is analysis and bounded discriminator selection from the preserved
evidence. No new Kaggle/model/GPU execution is released by this disposition.
