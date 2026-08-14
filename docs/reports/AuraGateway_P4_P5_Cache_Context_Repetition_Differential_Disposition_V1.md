# AuraGateway P4/P5 Cache-Context Repetition Differential Disposition V1

## Decision

Accept and preserve the governed cache-context repetition differential as:

`LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED`

The frozen comparison produced:

- `CONTROL_1X`: 3/3 exact-object responses
- `TREATMENT_24X`: 0/3 exact-object responses
- control valid JSON: 3/3
- treatment valid JSON: 0/3
- fresh worker process per observation: true
- worker identity cardinality: 6

This establishes that the frozen 24x long/repeated-context condition is necessary,
relative to the frozen 1x control, for reproducing the current C3 regression.

It does not establish an exact repetition threshold, repetition count alone as the
causal mechanism, context length alone as the causal mechanism, a prefix-cache
defect, or the exact root cause.

## Governed transaction

Transaction:

`83d0e5c74aa607cc4b48232070c2caa3980c2f9ca5c9d84bcababed1542e960e`

Kaggle saved version:

`342415694`

Issuer merge commit:

`28eac96bcf8e82dbe44e0a56460aed2c692d8518`

Terminal disposition:

`CONSUMED`

Execution outcome:

`PASSED`

Authorization reusable:

`false`

The successful diagnostic outcome means the experiment completed validly and
reached its predeclared positive decision state. It does not mean the 24x treatment
itself satisfied the output contract.

## Execution budget realized

Observed and authorized:

- Kaggle sessions: 1
- runtime installation attempts: 1
- runtime import-closure probes: 1
- model requests: 6
- model loads: 6
- worker starts: 6
- hidden retries: 0
- replacement workers: 0
- external network requests: 0
- benchmark-trajectory requests: 0
- external spend: 0

Worker teardown passed for all six observations.

Scratch cleanup passed.

## Runtime and identity boundary

Executed runtime SHA-256:

`dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b`

The governed evidence records:

- runtime source identity: passed
- runtime installation: passed
- process-tree import closure: passed
- critical module origins inside the target runtime: true
- model loads consumed by the import-closure probe: 0
- network requested by the import-closure probe: false

The import-closure stderr warning observed in the Kaggle log is retained as
diagnostic context. It does not override the governed `PASSED` closure decision
or create a new runtime-failure claim.

## Frozen treatment identity

The three treatment observations reproduce the historical failed 24x identity:

- token count: `899`
- token SHA-256:
  `6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`
- payload SHA-256:
  `b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e`

All three treatment observations also share response SHA-256:

`da4ae47e5a52cd6ce2aedb5e8c7257b5a998b42e5b8ea9118f0200bab0b2322f`

All three control observations share:

- token count: `117`
- token SHA-256:
  `32a570d63aaaeb9597a2b517315b052eae7308b7acba6f4a85d409e3c633edbb`
- payload SHA-256:
  `cb250709bd4c201743206b2c79995d9ad2ad0dee333b596747f7d75ca080438d`
- response SHA-256:
  `448fad3d3ac5c2f11f4c09b0df1e7e6237ce2a09185f99503946311875f5e113`

The control/treatment identity split is therefore stable under the frozen run.

## Evidence custody

Immutable evidence is preserved under:

`evidence_vault/local_abc/p4-p5-cache-context-repetition-differential-v1`

Custody manifest SHA-256:

`eb2bdf99fa6354f6dce9f966f306d2ea2471ad7d8eb8909345760aa18bc97a21`

Governed evidence ZIP SHA-256:

`24be27819b28a39df08b3a69bf1c168f6abef58aec5cd90883b8621f2e4aafca`

Executed notebook SHA-256:

`3a3e16defd1a9dff45c07a8343882c29249c0755e896b76503f6b75d31ef34db`

Terminal log SHA-256:

`5a3f3ece251d7cce91056931483f3f2a7e648d2d536584cb32a39be0a8d90b45`

Platform-observation receipt SHA-256:

`48fef6a1ca0d7f26dac1df385075a727cc4692bb7bc50a43d586aa9ba0ebdb57`

The custody set contains byte-identical copies of the live authorization,
execution-artifact manifest, durable platform-observation receipt, terminal
receipt, governed evidence ZIP, executed notebook, and terminal log.

## Privacy / evidence boundary

The governed evidence retains neither raw prompts nor raw model outputs.

Credentials and customer data were not used.

The evidence ZIP excludes scratch directories and worker-log directories.

## Claim boundary

Established:

`FROZEN_24X_CONDITION_NECESSARY_RELATIVE_TO_1X_FOR_CURRENT_C3_REGRESSION`

Not established:

- exact repetition threshold
- repetition count alone as causal
- context length alone as causal
- exact C3 root cause
- prefix-cache defect
- P5 requalification
- P6 requalification
- measured North-Star A/B/C support
- production readiness

No new runtime execution is authorized by this disposition.

The consumed authorization is not reusable and unchanged replay remains unauthorized.

## Next gate

`STATIC_LONG_REPEATED_CONTEXT_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1`

The next tranche is static. It should inspect the remaining factors inside the
now-supported long/repeated-context family and select the smallest next
counterfactual before any new authorization design or GPU execution.
