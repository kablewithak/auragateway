# J7L Reference Execution Authorization V3

Status: **active only after merge to clean tracked `main`**.

Authorization SHA-256:

`623c7619aa36a851e87cc7b5ebb0a2c5145b524c8479b164a96773a32dd5cc76`

This artifact authorizes the separately merged J7L Reference Execution Protocol V3.
It performs no provider call by itself.

## Exact authority

- provider: `huawei_modelarts_maas`
- exact model: `glm-5.2`
- frozen binding SHA-256: `7c87832c697b66414921fef76f80466ef3b0c89421969d53acc6d35aa3906b1f`
- frozen V3 execution-plan SHA-256: `09ed20aa41df2a495f36affb47fe94c6344fcf0d667d67f9b5f9eaa8be5097ec`
- frozen V3 reference-audit-schedule SHA-256: `02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109`
- audit actor SHA-256: `a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82`
- resolution owner SHA-256: `a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82`
- maximum model inference requests: `48`
- maximum in-flight requests: `1`
- cumulative logical-execution token ceiling: `960000`
- automatic retries: forbidden
- completed-case replay: forbidden
- retry after an ambiguous attempt: forbidden
- resume across already completed cases in the same logical authorization: permitted
- external spend ceiling: `R0`
- paid fallback: forbidden
- Jev requests: forbidden

## Required live preconditions

Live execution remains blocked until:

- this authorization is merged to clean tracked `main`;
- the frozen Binding V2 SHA-256 remains exact;
- the frozen V3 execution-plan SHA-256 remains exact;
- the protected J7L schedule/export identities remain exact;
- the runtime-produced audit schedule validates through `J7LReferenceAuditScheduleV1`;
- the runtime-produced audit-schedule SHA-256 remains exactly
  `02a71acbe5ff1461ff91cdc874ae35453d21f156bcaf10928f8922cbedd60109`;
- the audit actor and resolution owner identities remain exactly bound;
- cumulative completed-case usage can be reconstructed before any resumed request;
- the cumulative 960,000-token ceiling can still reserve the next request;
- `HUAWEI_MAAS_API_KEY` is present in the current process;
- the operator confirms the execution remains within R0 / zero external spend;
- the exact confirmation phrase is supplied:

`EXECUTE_J7L_REFERENCE_SET_V3`

## Consumption and recovery

The logical authorization is consumed when execution begins.

Completed cases are append-only and may be reused only through the V3 resume path.
Their usage is reconstructed from preserved attempt, raw-response, and judgment
evidence before any additional request is permitted.

A case with incomplete or inconsistent prior execution evidence is ambiguous and
must not be retried under this authorization.

The authorization is single-use for the one logical 48-case replacement reference
execution lineage. It does not authorize a second independent replacement run.

## Governance boundary

The V2 48/48 result remains preserved historical technical evidence and is not
retrofitted into this V3 lineage.

The V3 human audit schedule is frozen before model reveal. The audit may not rewrite
reference judgments. Material human-audit disagreement invalidates the candidate
reference set rather than creating a hybrid truth set.

Jev remains forbidden by this authorization.

## Non-claims

This authorization does not itself establish:

- an authoritative J7L reference set;
- human-audit agreement;
- reference coverage;
- Jev performance;
- held-out qualification;
- final A/B/C effects;
- production readiness.

Next gate after merge:

`EXECUTE_J7L_REFERENCE_SET_V3`
