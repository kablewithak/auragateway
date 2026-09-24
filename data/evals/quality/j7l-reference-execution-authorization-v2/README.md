# J7L Reference Execution Authorization V2

Status: **active only after merge to clean tracked `main`**.

Authorization SHA-256:

`0173e724458cd1078b3fa06e114caab2dd2d85bf6879d3c7eb4f2ace1c4bf025`

This artifact authorizes the already-frozen J7L Reference Judge Binding V2 and
inactive execution plan. It performs no provider call by itself.

## Exact authority

- provider: `huawei_modelarts_maas`
- exact model: `glm-5.2`
- maximum model inference requests: `48`
- maximum in-flight requests: `1`
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
- the frozen execution-plan SHA-256 remains exact;
- the protected J7L schedule/export identities remain exact;
- `HUAWEI_MAAS_API_KEY` is present in the current process;
- the operator confirms the execution remains within R0 / zero external spend;
- the exact confirmation phrase is supplied:

`EXECUTE_J7L_REFERENCE_SET_V2`

## Consumption and recovery

The logical authorization is consumed when execution begins.

Completed cases are append-only and are skipped on an authorized continuation.
A case with an attempted provider request but no valid judgment is ambiguous and
must not be retried under this authorization.

## Non-claims

This authorization does not itself establish:

- reference-judge quality;
- reference coverage;
- human-audit agreement;
- Jev performance;
- held-out qualification;
- final A/B/C effects;
- production readiness.

Next gate after merge:

`EXECUTE_J7L_REFERENCE_SET_V2`
