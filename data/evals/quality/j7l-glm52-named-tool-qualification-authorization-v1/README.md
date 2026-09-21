# J7L GLM-5.2 Named-Tool Qualification Authorization V1

Status: **active only after merge to `main`; single use**.

This tranche authorizes one bounded AuraGateway-specific Huawei MaaS qualification
of the previously merged GLM-5.2 named-tool design.

## Exact authority

- provider: `huawei_modelarts_maas`
- model: `glm-5.2`
- maximum provider HTTP requests: 2
- maximum catalog requests: 1
- maximum model inference requests: 1
- qualification token allowance: 20,000
- external spend ceiling: R0
- automatic retries: forbidden
- resume: forbidden
- rerun: forbidden
- paid fallback: forbidden
- J7L reference requests: forbidden
- Jev requests: forbidden
- final binding freeze: forbidden

The authorization binds qualification plan SHA-256:

`362cdbb9eb19901cf181526abc58eff11fcf54e392509fa74de1bab9cc8603ee`

and merged qualification design commit:

`2d457cb99f6ec62300f9e807f134dc7000a7670c`

Authorization artifact SHA-256:

`d5a606355cfb1f67104865c19d2657892aaef62c690f1bbad6d180f5463618a7`

## Execution guard

Live execution requires all of the following:

1. this authorization is merged;
2. execution runs from clean tracked `main`;
3. the exact confirmation phrase is supplied;
4. R0 external-spend status is explicitly confirmed;
5. `HUAWEI_MAAS_API_KEY` is present;
6. no prior consumption marker or execution evidence exists.

The authorization is consumed immediately before the first network attempt. Once
consumed, the same authorization cannot be resumed or rerun, including after a
provider or validation failure.

## Live request sequence

1. one authenticated model-catalog GET;
2. if and only if the exact model ID is present, one synthetic named-tool inference.

No frozen `j7l-dev-*` case, Jev output, or frozen reference answer is sent.

## Success boundary

A passing qualification proves only the observed transport properties required by
the frozen qualification plan: named-tool realization, disabled-thinking behavior,
and provider usage accounting for the synthetic request.

Operator confirmation that the request remains within the R0 entitlement is an
execution precondition; it is **not** independent zero-spend evidence for the final
J7L judge binding. Likewise, a successful qualification does not itself freeze or
authorize the 48-case reference run.

## Confirmation phrase

`EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE`
