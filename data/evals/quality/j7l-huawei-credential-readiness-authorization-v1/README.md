# J7L Huawei Credential Readiness Authorization V1

Status: **active only after merge to `main`; single use**.

This tranche authorizes exactly one bounded Huawei ModelArts MaaS model-catalog readiness
observation using the already-merged credential-readiness activation machinery.

## Exact authority

- provider: `huawei_modelarts_maas`
- region: `ap-southeast-1`
- model: `glm-5.2`
- maximum provider HTTP requests: 1
- maximum catalog requests: 1
- maximum model inference requests: 0
- external spend ceiling: R0
- automatic retries: forbidden
- resume: forbidden
- rerun: forbidden
- J7L reference requests: forbidden
- Jev requests: forbidden
- binding freeze: forbidden

The authorization binds readiness plan SHA-256:

`2868b33d8a1a2f40c6e894fda7ea46dd156bee8aca2eee6f7996a6de45ba3d77`

and activation source SHA-256:

`5b7d9db850cc864b89bc169e07d448c24565f9d56bf171f2fc902a31f1e1a091`

Authorization artifact SHA-256:

`979931f350951798cf086171ffa02eb8b7c0259f25cdffee7b07862eecadb5a4`

## Execution guard

Live execution requires all of the following:

1. this authorization is merged to clean tracked `main`;
2. the exact confirmation phrase is supplied;
3. R0 external-spend status is explicitly confirmed;
4. `HUAWEI_MAAS_API_KEY` is present;
5. no prior readiness consumption marker exists;
6. no prior readiness result exists.

The authorization is consumed immediately before the first provider network attempt.
Once consumed, it cannot be resumed or rerun.

## Live request sequence

Exactly one authenticated model-catalog GET is permitted.

No inference request is permitted. No J7L case content, Jev content, or frozen reference
answer may be sent.

## Result boundary

`READY` may establish only observed catalog authentication plus exact `glm-5.2` visibility.

It does not establish:

- chat-completion entitlement;
- GLM-5.2 inference success;
- named-tool transport;
- disabled-thinking behavior;
- usage accounting;
- reference-judge quality;
- independent zero-spend proof;
- J7L, Jev, or binding execution authority.

## Confirmation phrase

`EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE`
